# SPDX-License-Identifier: Apache-2.0
"""Synthetic reference-wall acceptance smoke tests, not engineering verification."""
import json
import copy
import re
import shutil
import subprocess
import unittest
from pathlib import Path
import reference_wall_check as independent

HTML = Path(__file__).resolve().parents[1] / "model-verification" / "stud-wall.html"


class ReferenceWall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = HTML.read_text(encoding="utf-8")
        match = re.search(r'<script type="application/json" id="assembly">([\s\S]*?)</script>', cls.page)
        if not match:
            raise AssertionError("missing embedded, versioned assembly source")
        cls.assembly = json.loads(match.group(1))

    def test_stud_layout_and_panel_coverage(self):
        src = self.assembly
        self.assertEqual(src["units"], "in")
        wall, framing, panels = src["wall"], src["framing"], src["sheathing"]
        self.assertEqual((wall["width"], wall["height"]), (96, 96))
        centers = framing["stud_centers"]
        self.assertEqual(len(centers), 7)
        self.assertEqual(centers, sorted(set(centers)))
        self.assertEqual(centers[0] - framing["stud_width"] / 2, 0)
        self.assertEqual(centers[-1] + framing["stud_width"] / 2, wall["width"])
        self.assertGreater(wall["height"] - framing["bottom_plate_height"] -
                           framing["top_plate_count"] * framing["top_plate_height"], 0)
        self.assertEqual(panels["width"] * panels["panels"], wall["width"])
        self.assertEqual(panels["height"], wall["height"])
        self.assertGreater(panels["thickness"], 0)

    def test_stable_part_identity_and_known_counts(self):
        src = self.assembly
        n_studs = len(src["framing"]["stud_centers"])
        n_plates = src["framing"]["top_plate_count"] + 1
        n_panels = src["sheathing"]["panels"]
        n_markers = n_studs * len(src["fasteners"]["row_heights"])
        self.assertEqual((n_studs, n_plates, n_panels, n_markers), (7, 3, 2, 56))
        self.assertEqual(len(set(src["fasteners"]["row_heights"])),
                         len(src["fasteners"]["row_heights"]))
        self.assertIn("revision", src)
        self.assertIn("urn:ori:synthetic:", self.page)
        self.assertIn("e.id===selected", self.page)
        self.assertIn("elements.filter", self.page)
        self.assertIn("project(", self.page)

    def test_unverified_not_approved(self):
        self.assertEqual(self.assembly["verification"]["status"], "unknown")
        self.assertIsNone(self.assembly["reviewer_decision"])
        self.assertIn("not a building-code check", self.page)
        self.assertIn("fastening schedule", self.page)
        self.assertNotIn('verification:"pass"', self.page)
        self.assertNotIn("https://cdn.", self.page)

    @unittest.skipUnless(shutil.which("node"), "node executable not installed")
    def test_inline_javascript_syntax(self):
        scripts = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>", self.page)
        self.assertEqual(len(scripts), 2)
        result = subprocess.run(
            ["node", "--check", "-"], input=scripts[-1], text=True,
            capture_output=True, timeout=15, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_independent_export_geometry_and_parameter_regeneration(self):
        self.assertTrue(shutil.which("node"), "Node is required for executable viewer verification")
        for name in independent.CASES:
            with self.subTest(case=name):
                report, _ = independent.run_case(name, self.page)
                failures = [c for c in report['checks'] if c['status'] != 'pass']
                self.assertEqual(failures, [])

    def test_independent_checker_rejects_corrupted_geometry_identity_and_state(self):
        _, probe = independent.run_case('baseline', self.page)
        for fault in ('dimension', 'missing', 'duplicate', 'view-change', 'approval'):
            with self.subTest(fault=fault):
                bad = copy.deepcopy(probe)
                elements = bad['states'][0]['artifact']['elements']
                if fault == 'dimension':
                    elements[3]['geometry']['height'] += 1
                elif fault == 'missing':
                    elements.pop()
                elif fault == 'duplicate':
                    elements.append(copy.deepcopy(elements[0]))
                elif fault == 'view-change':
                    bad['states'][1]['artifact']['elements'][3]['geometry']['width'] += .25
                else:
                    bad['detail']['reviewer_decision'] = 'approved'
                self.assertEqual(independent.compare('baseline', bad)['status'], 'fail')

    def test_checker_rejects_incorrect_projection(self):
        _, probe = independent.run_case('baseline', self.page)
        shape = probe['states'][1]['shapes'][0]
        shape['attrs']['points'] = '0,0 0,0 0,0 0,0'
        self.assertEqual(independent.compare('baseline', probe)['status'], 'fail')

    def test_checker_rejects_missing_states_marker_position_and_filtered_geometry(self):
        _, probe = independent.run_case('baseline', self.page)
        for fault in ('missing-state', 'marker-position', 'hidden-layer-projection'):
            with self.subTest(fault=fault):
                bad = copy.deepcopy(probe)
                if fault == 'missing-state':
                    bad['states'].pop(1)
                elif fault == 'marker-position':
                    marker = next(s for s in bad['states'][3]['shapes'] if 'r' in s['attrs'])
                    marker['attrs'].update(cx='999', cy='999')
                else:
                    bad['states'][2]['shapes'][0]['attrs']['points'] = '0,0 0,0 0,0 0,0'
                self.assertEqual(independent.compare('baseline', bad)['status'], 'fail')

    def test_checker_rejects_wrong_selection_type_and_nonfinite_projections(self):
        _, probe = independent.run_case('baseline', self.page)
        for fault in ('selection-type', 'nan-face', 'nan-marker'):
            with self.subTest(fault=fault):
                bad = copy.deepcopy(probe)
                if fault == 'selection-type':
                    bad['details'] = {k: bad['details']['plate-'] for k in bad['details']}
                elif fault == 'nan-face':
                    shape = bad['states'][1]['shapes'][1]
                    shape['attrs']['points'] = shape['attrs']['points'].split(' ')[0] + ' NaN,0 NaN,0 NaN,0'
                else:
                    markers = [s for s in bad['states'][3]['shapes'] if 'r' in s['attrs']]
                    markers[1]['attrs']['cx'] = 'NaN'
                self.assertEqual(independent.compare('baseline', bad)['status'], 'fail')


if __name__ == "__main__":
    unittest.main()
