"""The plot masters read cleanly through the books' own SVG importer (common/plot/svgimport.py),
which is how a plate generator would place one. Standard library only.

    python -m unittest discover -s common/lattice/tests -v
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LATTICE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(LATTICE))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
from svgimport import strokes_from_svg  # noqa: E402

INK, RED = "#161918", "#a32b24"


class SamplesImport(unittest.TestCase):
    def test_every_sample_imports_stroke_for_stroke(self):
        manifest = json.load(open(os.path.join(LATTICE, "out", "manifest.json"), encoding="utf-8"))
        for rec in manifest["samples"]:
            path = os.path.join(LATTICE, rec["file"])
            svg = open(path, encoding="utf-8").read()
            strokes = strokes_from_svg(path)
            self.assertEqual(len(strokes), len(re.findall(r"<path ", svg)), rec["name"])
            self.assertEqual(len(strokes), rec["paths"], rec["name"])
            self.assertTrue({c for c, w, p in strokes} <= {INK, RED}, rec["name"])
            self.assertTrue({w for c, w, p in strokes} <= {0.12, 0.17, 0.22}, rec["name"])
            for c, w, poly in strokes:
                for x, y in poly:
                    self.assertTrue(15 - 0.01 <= x <= 195 + 0.01 and 13.5 - 0.01 <= y <= 283.5 + 0.01, (rec["name"], x, y))


if __name__ == "__main__":
    unittest.main()
