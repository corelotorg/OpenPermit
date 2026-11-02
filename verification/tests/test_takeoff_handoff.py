# SPDX-License-Identifier: Apache-2.0
"""Reopened IFC checks for source identity, exclusions and coordinate handoffs."""
import copy
import hashlib
import json

import ifcopenshell
import ifcopenshell.util.element as uel
import ifcopenshell.util.placement as placement
import pytest

from ori_takeoff import sample_plan as S
from ori_takeoff import to_ifc as T

@pytest.fixture
def doc(tmp_path):
    pdf = S.write_pdf(tmp_path / 'source.pdf', S.floors()[:1])
    return S.ground_truth(pdf, fl=S.floors()[:1])

def export(doc, tmp_path, filename='model.ifc'):
    path = tmp_path / filename
    summary = T.overlay_to_ifc(doc, path)
    return summary, ifcopenshell.open(str(path))

@pytest.mark.parametrize('cls', ['IfcWall', 'IfcDoor', 'IfcWindow', 'IfcOpeningElement', 'IfcSpace', 'IfcStair'])
def test_rejected_elements_never_export(doc, tmp_path, cls):
    candidates = [e for e in doc['pages'][0]['elements'] if e['ifc_class'] == cls]
    if not candidates and cls == 'IfcOpeningElement':
        element = copy.deepcopy(next(e for e in doc['pages'][0]['elements'] if e['ifc_class'] == 'IfcDoor'))
        element.update(id='rejected-gap', ifc_class=cls)
        doc['pages'][0]['elements'].append(element)
    else:
        assert candidates
        element = candidates[0]
    element['provenance']['review_status'] = 'rejected'
    original = copy.deepcopy(doc)
    summary, model = export(doc, tmp_path)
    assert doc == original
    assert not any(e['overlay_element_id'] == element['id'] for e in summary['elements'])
    assert any(e['element_id'] == element['id'] and e['reason'] == 'review_rejected' for e in summary['excluded_elements'])
    assert not any(uel.get_pset(e, 'Pset_ORI_Takeoff').get('OverlayElementId') == element['id'] for e in model.by_type('IfcElement') if uel.get_pset(e, 'Pset_ORI_Takeoff'))

def test_rejected_host_excludes_its_openings(doc, tmp_path):
    page = doc['pages'][0]
    opening = next(e for e in page['elements'] if e['ifc_class'] == 'IfcDoor')
    wall = next(e for e in page['elements'] if e['id'] == opening['relations']['host_wall'])
    wall['provenance']['review_status'] = 'rejected'
    summary, _ = export(doc, tmp_path)
    assert any(e['element_id'] == opening['id'] and e['reason'] == 'host_wall_not_exported' for e in summary['excluded_elements'])

def test_identity_is_repeatable_and_revision_is_distinct(doc, tmp_path):
    first, _ = export(doc, tmp_path, 'first.ifc')
    second, _ = export(doc, tmp_path, 'second.ifc')
    assert first['elements'] == second['elements']
    assert first['overlay_sha256'] == second['overlay_sha256']
    ids = [e['ifc_guid'] for e in first['elements']]
    assert len(ids) == len(set(ids))
    doc['pages'][0]['elements'][0]['name'] = 'reviewed revision'
    changed, model = export(doc, tmp_path, 'changed.ifc')
    assert changed['overlay_sha256'] != first['overlay_sha256']
    assert [e['ifc_guid'] for e in changed['elements']] == ids
    assert changed['ifc_sha256'] == hashlib.sha256((tmp_path/'changed.ifc').read_bytes()).hexdigest()
    for e in changed['elements']:
        props = uel.get_pset(model.by_guid(e['ifc_guid']), 'Pset_ORI_Takeoff')
        assert props['SourceArtifactId'] == doc['source']['artifact_id']
        assert props['OverlaySha256'] == changed['overlay_sha256']
        assert props['OverlayElementId'] == e['overlay_element_id']

def test_page_transform_matches_reopened_ifc_vertices(doc, tmp_path):
    doc['pages'][0]['storey']['elevation_in'] = 42
    summary, model = export(doc, tmp_path)
    matrix = summary['coordinate_transforms'][0]['page_xy_to_ifc_world_mm']
    element = next(e for e in doc['pages'][0]['elements'] if e['ifc_class']=='IfcWall')
    entry = next(e for e in summary['elements'] if e['overlay_element_id']==element['id'])
    wall = model.by_guid(entry['ifc_guid'])
    point = wall.Representation.Representations[0].Items[0].SweptArea.OuterCurve.Points[0].Coordinates
    world = placement.get_local_placement(wall.ObjectPlacement) @ [*point, 0, 1]
    x,y = element['geometry_page']['coordinates'][0][0]
    expected = [row[0]*x + row[1]*y + row[2] for row in matrix]
    assert list(world[:3]) == pytest.approx(expected, abs=.03)
    assert summary['coordinate_transforms'][0]['viewer_metres_per_ifc_unit'] == .001
    assert summary['coordinate_transforms'][0]['cross_page_registration'] == 'unverified'

def test_duplicate_ids_fail_before_output(doc, tmp_path):
    doc['pages'][0]['elements'].append(copy.deepcopy(doc['pages'][0]['elements'][0]))
    with pytest.raises(ValueError, match='duplicate overlay'):
        export(doc,tmp_path)
    assert not (tmp_path/'model.ifc').exists()

def test_unreviewed_human_trace_cannot_produce_pass(doc, tmp_path):
    for e in doc['pages'][0]['elements']:
        e['provenance'].update(method='human_traced', review_status='unreviewed')
    export(doc,tmp_path)
    report = T.check_ifc(tmp_path/'model.ifc')
    assert report['counts']['pass'] == 0
    assert report['counts']['unknown'] > 0

@pytest.mark.parametrize('status', ['unknown', 'conflict', 'not_to_scale'])
def test_unusable_scale_cannot_export_even_with_stale_numeric_scale(doc,tmp_path,status):
    doc['pages'][0]['scale']['status']=status
    summary,model=export(doc,tmp_path)
    assert not summary['elements']
    assert not model.by_type('IfcWall')

@pytest.mark.parametrize('factor', [-1, 0, True, float('nan'), float('inf')])
def test_invalid_scale_refused(doc,tmp_path,factor):
    doc['pages'][0]['scale']['real_in_per_page_unit']=factor
    with pytest.raises(ValueError):
        export(doc,tmp_path)
    assert not (tmp_path/'model.ifc').exists()

def test_duplicate_page_refused(doc,tmp_path):
    doc['pages'].append(copy.deepcopy(doc['pages'][0]))
    with pytest.raises(ValueError,match='duplicate overlay page'):
        export(doc,tmp_path)

def test_different_source_does_not_reuse_element_identity(doc,tmp_path):
    first,_=export(doc,tmp_path,'first.ifc')
    doc['source']['artifact_id']='urn:ori:artifact:sha256:'+'a'*64
    second,_=export(doc,tmp_path,'second.ifc')
    assert {e['ifc_guid'] for e in first['elements']}.isdisjoint({e['ifc_guid'] for e in second['elements']})

def test_placeholder_heights_remain_explicit_in_handoff(doc,tmp_path):
    doc['pages'][0]['storey']={}
    summary,_=export(doc,tmp_path)
    assert summary['coordinate_transforms'][0]['elevation_known'] is False
    assert all(e['height_source']=='placeholder_not_from_plan' for e in summary['elements'] if e['ifc_class'] in ('IfcWall','IfcSpace','IfcWindow','IfcDoor','IfcOpeningElement'))
    report=T.check_ifc(tmp_path/'model.ifc')
    heights=[r for r in report['records'] if r['metadata'].get('section')=='R305.1']
    assert heights and all(r['metadata']['result_state'] in ('unknown','not_applicable') for r in heights)
    assert report['counts']['pass']>0  # confirmed plan areas remain usable
