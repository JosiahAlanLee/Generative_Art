"""Process invariants and compatibility checks, rather than image snapshots."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import random
import sys

import numpy as np

from lib.process_art.models import drainage, flood, catchment, gray_scott, recurrence, space_colonize
from lib.process_art.drawing import Plate

ROOT = Path(__file__).resolve().parents[3]


class DrainageTests(unittest.TestCase):
    def test_outlets_conserve_runoff_and_routes_descend(self):
        rng = np.random.default_rng(7)
        z = flood(rng.random((25, 25)))
        rec, area, _ = drainage(z)
        r, a, h = rec.ravel(), area.ravel(), z.ravel()
        valid = r >= 0
        self.assertTrue(np.all(h[r[valid]] < h[valid]))
        self.assertAlmostEqual(float(a[~valid].sum()), z.size)
        self.assertFalse(np.any(rec[1:-1, 1:-1] < 0))

    def test_incision_changes_the_terrain(self):
        evolved = catchment(3, n=28, steps=5)
        self.assertGreater(float(evolved["incision_history"].sum()), 0)
        self.assertFalse(np.array_equal(evolved["initial"], evolved["height"]))
        self.assertTrue(np.isfinite(evolved["height"]).all())


class GrowthTests(unittest.TestCase):
    def test_chemistry_repeatable_and_bounded(self):
        a = gray_scott(3, n=28, steps=60)
        b = gray_scott(3, n=28, steps=60)
        np.testing.assert_array_equal(a["v"], b["v"])
        for key in ("u", "v"):
            self.assertTrue(np.isfinite(a[key]).all())
            self.assertGreaterEqual(a[key].min(), 0)
            self.assertLessEqual(a[key].max(), 1.1)

    def test_genealogy_and_growth_step(self):
        rng = np.random.default_rng(3)
        a = rng.uniform(.2, .8, size=(200, 2))
        state = space_colonize(a, [[.5, .5]], iterations=45)
        self.assertGreater(len(state["nodes"]), 10)
        for i, parent in enumerate(state["parents"]):
            if parent >= 0:
                self.assertLess(parent, i)
                length = np.linalg.norm(state["nodes"][i]-state["nodes"][parent])
                self.assertAlmostEqual(length, .012)
                self.assertGreater(state["mass"][parent], state["mass"][i])


class RecurrenceTests(unittest.TestCase):
    def test_known_repeats_and_theiler_exclusion(self):
        state = recurrence([0, 1, 2, 0, 1, 2, 0, 1, 2], dimension=1, epsilon=.01, theiler=1)
        self.assertTrue(state["matrix"][0, 3])
        self.assertFalse(state["matrix"][0, 1])
        self.assertFalse(np.diag(state["matrix"]).any())
        np.testing.assert_array_equal(state["matrix"], state["matrix"].T)
        self.assertEqual(state["pair_count"], 9)

    def test_missing_windows_keep_original_row_numbers(self):
        state = recurrence([0, 1, np.nan, 0, 1, 0, 1, 0], dimension=2, delay=1)
        np.testing.assert_array_equal(state["indices"], [0, 3, 4, 5, 6])
        self.assertTrue(np.isfinite(state["features"]).all())

    def test_constant_series_and_invalid_inputs(self):
        state = recurrence(np.ones(16))
        self.assertTrue((state["features"] == 0).all())
        with self.assertRaises(ValueError):
            recurrence([1, 2])
        with self.assertRaises(ValueError):
            recurrence([np.nan]*20)


class ExportTests(unittest.TestCase):
    def test_real_book_ink_and_cornmeal_hands(self):
        sys.path.insert(0, str(ROOT/"sources/codex-intervallorum/common/geometry"))
        import core
        import marks
        plate = Plate("material adapter")
        plate.add([[10, 10], [15, 15], [20, 10]])
        for mode in ("ink", "grain"):
            doc = core.Doc(170, 220, {})
            hand = marks.Hand(doc, random.Random(7), mode=mode, amp=0,
                              grain={"hair": (8, .08), "stray": 0})
            # The native Doc buckets must exist before a Hand writes to them.
            for color in ("ink", "red"):
                for suffix in ("core", "orn", "hair", "gs", "gm", "gl"):
                    doc.d[f"{color}_{suffix}"] = []
            plate.draw(hand)
            total = sum(map(len, doc.d.values()))
            self.assertGreater(total, 0)
            if mode == "grain":
                self.assertGreater(total, 20)

    def test_existing_book_svg_importer_preserves_all_strokes(self):
        importer = ROOT/"sources/codex-intervallorum/common/plot/svgimport.py"
        spec = importlib.util.spec_from_file_location("book_svgimport", importer)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        p = Plate("A < B & C")
        p.add([[10, 10], [20, 20], [30, 18]])
        p.ring(40, 40, 3, color="#a32b24")
        ET.fromstring(p.svg())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"plate.svg"
            path.write_text(p.svg())
            imported = module.strokes_from_svg(path)
        self.assertEqual(len(imported), len(p.strokes))
        for (color, width, points), original in zip(imported, p.strokes):
            self.assertEqual(color, original.color)
            self.assertAlmostEqual(width, original.width)
            np.testing.assert_allclose(points, original.points, atol=.00051)

    def test_hand_adapter_uses_existing_call_contract(self):
        class Hand:
            def __init__(self):
                self.paths = []

            def stroke(self, points, weight, color, amp):
                self.paths.append((points, weight, color, amp))

        p, hand = Plate("adapter"), Hand()
        p.add([[10, 11], [12, 13]])
        p.draw(hand, origin=(1, 2), scale=2)
        self.assertEqual(hand.paths[0][0], [[21, 24], [25, 28]])


if __name__ == "__main__":
    unittest.main()
