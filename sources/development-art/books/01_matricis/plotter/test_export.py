"""Release checks for the committed plot files, including two-pass registration."""
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import build


class PlotExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = Path(__file__).resolve().parent / "a4"
        cls.stats = json.loads((cls.folder / "plot-stats.json").read_text())

    def test_source_fingerprint(self):
        self.assertEqual(hashlib.sha256(build.SOURCE.read_bytes()).hexdigest(), self.stats["source_sha256"])

    def test_all_outputs_have_safe_geometry(self):
        paths = list(self.folder.glob("*.svg"))
        self.assertEqual(len(paths), 6)
        for path in paths:
            with self.subTest(path=path.name):
                build.validate(path, build.Layout(210,297,12))

    def test_pass_coordinates_match_combined_and_each_other(self):
        def layers(file):
            root = ET.parse(file).getroot()
            self.assertEqual(root.get("width"), "210mm")
            self.assertEqual(root.get("height"), "297mm")
            return {e.get("id"): [p.get("d") for p in e]
                    for e in root if e.tag == f"{{{build.SVG}}}g"}
        for prefix in ("closed-neck","pen-test"):
            with self.subTest(prefix=prefix):
                black = layers(self.folder/f"{prefix}-black.svg")
                red = layers(self.folder/f"{prefix}-red.svg")
                combined = layers(self.folder/f"{prefix}-combined.svg")
                self.assertEqual(black["black"],combined["black"])
                self.assertEqual(red["red"],combined["red"])
                self.assertEqual(black["registration"],red["registration"])
                self.assertEqual(black["registration"],combined["registration"])
                self.assertEqual(len(red["registration"]),8)

    def test_optimization_does_not_bridge_separate_strokes(self):
        strokes = [[(1,1),(2,1)],[(5,1),(6,1)],[(2,1),(1,1)]]
        result = build.optimize(strokes)
        self.assertEqual(len(result),2)
        self.assertAlmostEqual(sum(build.LineString(s).length for s in result),2)

    def test_unsupported_letter_is_not_silently_omitted(self):
        with self.assertRaises(ValueError):
            build.monoline("?",0,0,3)


if __name__ == "__main__":
    unittest.main()
