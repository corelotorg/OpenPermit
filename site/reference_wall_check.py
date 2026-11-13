# SPDX-License-Identifier: Apache-2.0
"""Independent synthetic geometry oracle. No viewer generator code is imported.

Uses fixed, separately specified box/center tables, then compares actual exports
and projected SVG faces. Results cover software geometry, not engineering approval.
"""
import argparse
import copy
import hashlib
import html
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / 'model-verification/stud-wall.html'
ASSEMBLY = r'(<script type="application/json" id="assembly">)([\s\S]*?)(</script>)'
CASES = {
    'baseline': {'revision': 'reference-wall-r1', 'width': 96, 'height': 96,
        'stud_centers': [.75, 16, 32, 48, 64, 80, 95.25], 'stud_height': 91.5,
        'top_y': [94.5, 93], 'panel_x': [0, 48], 'panel_width': 48},
    'changed': {'revision': 'reference-wall-r1-change-120x108', 'width': 120, 'height': 108,
        'stud_centers': [.75, 24, 48, 72, 96, 119.25], 'stud_height': 103.5,
        'top_y': [106.5, 105], 'panel_x': [0, 40, 80], 'panel_width': 40},
}
ROWS = [10, 22, 34, 46, 58, 70, 82, 90]
KEYS = ('x', 'y', 'z', 'width', 'height', 'depth')


def case_source(name, page):
    source = json.loads(re.search(ASSEMBLY, page)[2])
    if name == 'changed':
        source = copy.deepcopy(source)
        source['revision'] = CASES[name]['revision']
        source['wall'].update(width=120, height=108)
        source['framing']['stud_centers'] = [.75, 24, 48, 72, 96, 119.25]
        source['sheathing'].update(panels=3, width=40, height=108)
    return source


def case_page(source, page):
    return re.sub(ASSEMBLY, lambda m: m[1] + '\n' + json.dumps(source, indent=2) + '\n' + m[3], page)


def expected_boxes(name):
    c = CASES[name]
    boxes = [('plate-bottom', 'framing', (0, 0, 0, c['width'], 1.5, 3.5))]
    boxes += [(f'plate-top-{i+1}', 'framing', (0, y, 0, c['width'], 1.5, 3.5)) for i, y in enumerate(c['top_y'])]
    boxes += [(f'stud-{i+1:02}', 'framing', (x-.75, 1.5, 0, 1.5, c['stud_height'], 3.5)) for i, x in enumerate(c['stud_centers'])]
    boxes += [(f'sheathing-{i+1}', 'sheathing', (x, 0, 3.5, c['panel_width'], c['height'], .4375)) for i, x in enumerate(c['panel_x'])]
    boxes += [(f'fastener-{i+1}-{j+1}', 'fasteners', (x-.16, y-.16, 3.9375, .32, .32, .08))
              for i, x in enumerate(c['stud_centers']) for j, y in enumerate(ROWS)]
    return {f"urn:ori:synthetic:{c['revision']}:{ident}": {'group': group, 'geometry': dict(zip(KEYS, box))}
            for ident, group, box in boxes}


def compare(name, probe):
    expected = expected_boxes(name)
    actual = probe['states'][0]['artifact']['elements']
    checks = []
    def check(label, want, got):
        checks.append({'check': label, 'expected': want, 'actual': got, 'status': 'pass' if want == got else 'fail'})
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    ids = [e['id'] for e in actual]
    check('required unique observation states', ['front', 'isometric', 'framing-hidden', 'markers-visible', 'reset'],
          [s['label'] for s in probe['states']])
    check('unique element identities', len(ids), len(set(ids)))
    check('complete identities', sorted(expected), sorted(ids))
    for e in actual:
        if e['id'] not in expected:
            continue
        oracle = expected[e['id']]
        check(e['id'] + ' type', oracle['group'], e['group'])
        for key, value in oracle['geometry'].items():
            got = e['geometry'].get(key)
            valid = isinstance(got, (int, float)) and not isinstance(got, bool) and math.isfinite(got) and math.isclose(value, got, abs_tol=1e-9, rel_tol=0)
            checks.append({'check': e['id'] + ' ' + key, 'expected': value, 'actual': got, 'status': 'pass' if valid else 'fail'})
        check(e['id'] + ' verification', 'unknown', e['verification'])
    for state in probe['states']:
        check(state['label'] + ' assembly and exported elements SHA-256 unchanged', digest(probe['states'][0]['artifact']), digest(state['artifact']))
        check(state['label'] + ' selectable identities', sorted(expected), sorted(state['partIds']))
        if state['label'] in ('front', 'isometric', 'framing-hidden', 'markers-visible', 'reset'):
            is_front = state['label'] in ('front', 'reset')
            check(state['label'] + ' dimension/view label',
                  f"FRONT ELEVATION · {CASES[name]['width']} in × {CASES[name]['height']} in" if is_front else 'ISOMETRIC · SYNTHETIC', state['view'])
            check(state['label'] + ' width annotation', f"{CASES[name]['width']} in modeled width",
                  next(s['text'] for s in state['shapes'] if s['text']))
            check(state['label'] + ' percentage', '0%' if is_front else '100%', state['percentage'])
            shapes = [s for s in state['shapes'] if 'points' in s['attrs']]
            solids = [e for e in actual if e['group'] != 'fasteners' and
                      (state['label'] != 'framing-hidden' or e['group'] != 'framing')]
            check(state['label'] + ' face count', len(solids)*(1 if is_front else 4), len(shapes))
            # Independent vector projection of the exported boxes; validate every SVG face.
            wanted = []
            for e in solids:
                b = expected.get(e['id'], {}).get('geometry')
                if not b:
                    continue
                x,y,z,dx,dy,dz = (b[k] for k in KEYS)
                vertices = [(x,y,z),(x+dx,y,z),(x+dx,y+dy,z),(x,y+dy,z),
                            (x,y,z+dz),(x+dx,y,z+dz),(x+dx,y+dy,z+dz),(x,y+dy,z+dz)]
                faces = [(4,5,6,7)] if is_front else [(0,1,5,4),(3,2,6,7),(1,2,6,5),(4,5,6,7)]
                for face in faces:
                    wanted.append([coord for i in face for coord in
                        ((vertices[i][0], -vertices[i][1]) if is_front else
                         (sum(a*b for a,b in zip(vertices[i], (.92,0,-.68))), sum(a*b for a,b in zip(vertices[i], (.20,-.88,.44)))))])
            parsed = [[float(n) for n in s['attrs']['points'].replace(',', ' ').split()] for s in shapes]
            max_error = max((abs(a-b) for ws,gs in zip(wanted,parsed) for a,b in zip(ws,gs)), default=0)
            check(state['label'] + ' projected vertices within 1e-9 in', True,
                  len(wanted)==len(parsed) and all(len(x)==len(y) for x,y in zip(wanted,parsed))
                  and all(math.isfinite(n) for points in parsed for n in points) and max_error <= 1e-9)
            markers = [s['attrs'] for s in state['shapes'] if 'r' in s['attrs']]
            expected_markers = [(x, -y) if is_front else (.92*x-.68*4.0175, .20*x-.88*y+.44*4.0175)
                                for x in CASES[name]['stud_centers'] for y in ROWS] if state['label'] in ('markers-visible', 'reset') else []
            check(state['label'] + ' marker count', len(expected_markers), len(markers))
            marker_error = max((abs(a-float(b)) for point, marker in zip(expected_markers, markers)
                                for a,b in zip(point, (marker['cx'], marker['cy']))), default=0)
            check(state['label'] + ' marker centers within 1e-9 in', True,
                  len(expected_markers)==len(markers) and all(math.isfinite(float(m[k])) for m in markers for k in ('cx','cy'))
                  and marker_error <= 1e-9)
        if state['label'] == 'framing-hidden':
            check('framing layer hidden face count', len(CASES[name]['panel_x'])*4,
                  sum('points' in s['attrs'] for s in state['shapes']))
        if state['label'] == 'markers-visible':
            check('illustrative marker count', len(CASES[name]['stud_centers'])*8,
                  sum('r' in s['attrs'] for s in state['shapes']))
    detail = probe['detail']
    check('selected element metadata', expected[detail['id']]['geometry'], detail['geometry_in'])
    check('reviewer decision remains empty', None, detail['reviewer_decision'])
    check('all element types inspected', ['fastener-', 'plate-', 'sheathing-', 'stud-'], sorted(probe['details']))
    for prefix, selected in probe['details'].items():
        check(prefix + ' selected identity type', True, selected['id'].split(':')[-1].startswith(prefix))
        check(prefix + ' selected group', {'plate-':'framing','stud-':'framing','sheathing-':'sheathing','fastener-':'fasteners'}[prefix], selected['type'])
        check(prefix + ' selectable geometry', expected[selected['id']]['geometry'], selected['geometry_in'])
        check(prefix + ' selection revision', CASES[name]['revision'], selected['assembly_revision'])
        check(prefix + ' selection evidence empty', [], selected['evidence'])
        check(prefix + ' selection reviewer decision empty', None, selected['reviewer_decision'])
    check('source verification remains unknown', 'unknown', probe['states'][0]['artifact']['source']['verification']['status'])
    check('source reviewer decision remains empty', None, probe['states'][0]['artifact']['source']['reviewer_decision'])
    return {'case': name, 'revision': CASES[name]['revision'], 'status': 'pass' if all(c['status']=='pass' for c in checks) else 'fail',
            'counts': {g: sum(e['group']==g for e in actual) for g in ('framing','sheathing','fasteners')}, 'checks': checks}


def run_case(name, page):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'viewer.html'
        path.write_text(case_page(case_source(name, page), page), encoding='utf-8', newline='\n')
        result = subprocess.run(['node', str(ROOT/'site/reference_wall_probe.cjs'), str(path)], capture_output=True, text=True, encoding='utf-8', check=True, timeout=15)
        probe = json.loads(result.stdout)
    return compare(name, probe), probe


def generate(out):
    page = VIEWER.read_text(encoding='utf-8')
    results = [run_case(name, page)[0] for name in CASES]
    if any(r['status'] != 'pass' for r in results):
        failures = [c for r in results for c in r['checks'] if c['status'] != 'pass']
        raise AssertionError('Reference wall numerical verification failed: ' + json.dumps(failures))
    out.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'synthetic viewer geometry and software behavior only',
        'viewer_sha256': hashlib.sha256(page.encode()).hexdigest(),
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'probe_sha256': hashlib.sha256((ROOT/'site/reference_wall_probe.cjs').read_bytes()).hexdigest(),
        'tolerance_in': 1e-9, 'cases': results, 'reviewer_decision': None,
        'outstanding': ['fastening specification', 'IFC/STEP fidelity', 'code applicability', 'human review']}
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    for name in CASES:
        source = case_source(name, page)
        (out/f'{name}.json').write_text(json.dumps(source, indent=2)+'\n', encoding='utf-8', newline='\n')
        variant = case_page(source, page)
        # Keep relative links correct in the nested review directory.
        variant = variant.replace('href="../"', 'href="../../"').replace('href="../docs/', 'href="../../docs/')
        (out/f'{name}.html').write_text(variant, encoding='utf-8', newline='\n')
    total = sum(len(r['checks']) for r in results)
    (out/'index.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reference wall verification review</title><style>body{{background:#10151b;color:#e8edf2;font:18px/1.6 system-ui;max-width:960px;margin:4vh auto;padding:24px}}a{{color:#8dccff}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;border:1px solid #456}}code{{overflow-wrap:anywhere}}</style>
<a href="../stud-wall.html">Reference wall viewer</a><h1>Reference wall verification review</h1>
<p>{total} numerical and behavior checks passed across two synthetic cases. This is software geometry evidence. Human review is pending.</p>
<table><tr><th>Case</th><th>Modeled size</th><th>Studs / plates / panels / markers</th><th>Inspect</th></tr>
<tr><td>Baseline</td><td>96 × 96 in</td><td>7 / 3 / 2 / 56</td><td><a href="baseline.html">Open viewer</a> · <a href="baseline.json">Parameters</a></td></tr>
<tr><td>Controlled change</td><td>120 × 108 in</td><td>6 / 3 / 3 / 48</td><td><a href="changed.html">Open viewer</a> · <a href="changed.json">Parameters</a></td></tr></table>
<p><a href="report.json">Every expected/actual comparison and source hashes</a></p>
<p>Browser captures: <a href="screenshots/checked-baseline-2d.jpg">baseline 2D</a> · <a href="screenshots/checked-baseline-3d.jpg">baseline 3D</a> · <a href="screenshots/checked-changed-2d.jpg">changed 2D</a> · <a href="screenshots/checked-changed-3d.jpg">changed 3D</a>. <a href="browser-evidence.json">Capture provenance</a>. Captures are dated observations; compare their source hashes before applying them to another revision.</p>
<h2>Visual review</h2><p>In each viewer, move the slider from 0% to 100%. Inspect a stud, plate, panel and illustrative fastener. Toggle layers. Compare the visible layout with the dimensions and counts above. Note any discrepancy and the case/revision.</p>
<p>The controlled change uses six stud centers at 0.75, 24, 48, 72, 96 and 119.25 in, and three 40 in panels. Stud length grows from 91.5 to 103.5 in. The layout is a test fixture, not a code-compliant design claim.</p>
<p>Viewer SHA-256: <code>{html.escape(report['viewer_sha256'])}</code></p>
<p>Verification in the assembly remains UNKNOWN; reviewer decision remains empty. Fastening specification, IFC/STEP fidelity and code applicability are outstanding. No permit approval or construction authorization is established.</p>
<p><a href="https://github.com/corelotorg/OpenPermit/issues/132">Acceptance tracker #132</a></p></html>''', encoding='utf-8', newline='\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = generate(args.out)
    print(f"PASS: {sum(len(r['checks']) for r in report['cases'])} checks; human review pending")
