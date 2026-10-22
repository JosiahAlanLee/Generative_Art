"""Variant builds keep their own output folders, so they never overwrite the
delivered plates (scene.output_dir, mirrored by patches.cjs and run.py).

Run from the repository root:
    python -m unittest discover -s studies/infernal-landscape/tests -v
"""
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from scene import output_dir  # noqa: E402


class OutputDirTests(unittest.TestCase):
    def test_dry_run_face_patterns_and_plates_each_add_a_suffix(self):
        expected = {(): 'recorded_route', ('INFERNAL_DRYRUN',): 'recorded_route-dryrun',
                    ('INFERNAL_FACE_PATTERNS',): 'recorded_route-face-patterns',
                    ('INFERNAL_FACE_PATTERNS', 'INFERNAL_DRYRUN'): 'recorded_route-face-patterns-dryrun',
                    ('INFERNAL_PLATES',): 'recorded_route-plates',
                    ('INFERNAL_PLATES', 'INFERNAL_DRYRUN'): 'recorded_route-plates-dryrun',
                    # The plates include the face patterns; their folder is the plates'.
                    ('INFERNAL_PLATES', 'INFERNAL_FACE_PATTERNS'): 'recorded_route-plates'}
        flags_all = ('INFERNAL_DRYRUN', 'INFERNAL_FACE_PATTERNS', 'INFERNAL_PLATES')
        for flags, name in expected.items():
            env = {k: '1' if k in flags else '0' for k in flags_all}
            with mock.patch.dict(os.environ, env):
                self.assertEqual(output_dir('recorded_route', 'original').name, name)
                self.assertEqual(output_dir('late_opening', 'incised').name,
                                 name.replace('recorded_route', 'late_opening-incised'))

    def test_patches_and_runner_follow_the_same_rule(self):
        cjs = (STUDY / 'patches.cjs').read_text()
        self.assertRegex(cjs, r"INFERNAL_PLATES==='1'\?'-plates':\(process\.env\.INFERNAL_FACE_PATTERNS==='1'\?'-face-patterns'")
        self.assertRegex(cjs, r"\+variant\+\(process\.env\.INFERNAL_DRYRUN==='1'\?'-dryrun'")
        run = (STUDY / 'run.py').read_text()
        self.assertTrue(re.search(r"variant='-plates' if a\.plates else '-face-patterns' if a\.face_patterns else ''", run))
        self.assertTrue(re.search(r"case\+variant\+\('-dryrun' if a\.dry_run else ''\)", run))


if __name__ == '__main__':
    unittest.main()
