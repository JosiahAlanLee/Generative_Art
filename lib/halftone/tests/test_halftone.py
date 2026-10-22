"""Invariants for the halftone package: kernels, screens, run tracing and sampling."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
from scipy.spatial import cKDTree

from lib.halftone import (KERNELS, bayer, error_diffuse, masks, ordered_dither, poisson_sample,
                          specimen, stratified_grid, threshold, to_mm, tone_radius, trace_runs)
from lib.halftone.studies import halftone_plate, kernels_plate, stipple_plate
from lib.halftone.trace import pixel_counts

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "sources/codex-intervallorum"


class DitherTests(unittest.TestCase):
    def test_kernel_weights_sum_to_their_divisor_except_atkinson(self):
        for name, (taps, divisor) in KERNELS.items():
            total = sum(t[2] for t in taps)
            if name == "atkinson":
                self.assertEqual((total, divisor), (6, 8))
            else:
                self.assertEqual(total, divisor, name)
            # Error only travels forward: to the right on this row, or to later rows.
            for dx, dy, _ in taps:
                self.assertTrue(dy > 0 or (dy == 0 and dx > 0), name)

    def test_mid_grey_diffuses_to_half_black(self):
        z = np.full((48, 64), .5)
        for name in ("floyd-steinberg", "jarvis-judice-ninke", "stucki", "burkes", "sierra", "sierra-lite"):
            q = error_diffuse(z, name)
            self.assertEqual(set(np.unique(q)), {0., 1.}, name)
            self.assertAlmostEqual(q.mean(), .5, delta=.02, msg=name)

    def test_atkinson_drops_error_and_lightens(self):
        z = np.full((48, 64), .8)
        fs = error_diffuse(z, "floyd-steinberg").mean()
        self.assertAlmostEqual(fs, .8, delta=.02)
        self.assertGreater(error_diffuse(z, "atkinson").mean(), fs + .03)

    def test_levels_bleed_and_serpentine(self):
        z = specimen(40, 50, 3)
        q3 = error_diffuse(z, "floyd-steinberg", 3, serpentine=True)
        self.assertTrue(set(np.unique(q3)) <= {0., .5, 1.})
        self.assertAlmostEqual(q3.mean(), z.mean(), delta=.02)
        self.assertEqual(len(masks(q3, 3)), 2)
        self.assertEqual(sum(int(m.sum()) for m in masks(q3, 3)) + int((q3 == 1).sum()), z.size)
        np.testing.assert_array_equal(error_diffuse(z, "floyd-steinberg", bleed=0), threshold(z))
        with self.assertRaises(ValueError):
            error_diffuse(z, "floyd-steinberg", levels=1)
        with self.assertRaises(ValueError):
            error_diffuse(z * 2, "floyd-steinberg")

    def test_bayer_matrix_is_a_permutation(self):
        for size in (1, 2, 4, 8, 16):
            m = bayer(size)
            self.assertEqual(sorted(m.ravel().tolist()), list(range(size * size)))
        np.testing.assert_array_equal(bayer(2), [[0, 2], [3, 1]])
        with self.assertRaises(ValueError):
            bayer(6)

    def test_ordered_dither_keeps_the_mean_tone(self):
        z = np.full((32, 32), .25)
        q = ordered_dither(z, 4)
        self.assertEqual(set(np.unique(q)), {0., 1.})
        self.assertAlmostEqual(q.mean(), .25, delta=.01)
        q3 = ordered_dither(specimen(32, 32, 1), 8, 3)
        self.assertTrue(set(np.unique(q3)) <= {0., .5, 1.})

    def test_specimen_is_deterministic_and_in_range(self):
        a, b = specimen(60, 80, 5), specimen(60, 80, 5)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(a.shape, (80, 60))
        self.assertTrue(0 <= a.min() and a.max() <= 1)
        self.assertFalse(np.array_equal(a, specimen(60, 80, 6)))


class TraceTests(unittest.TestCase):
    def test_every_pixel_is_consumed_once(self):
        rng = np.random.default_rng(0)
        mask = rng.random((37, 53)) < .45
        traced = trace_runs(mask)
        covered, points = pixel_counts(traced)
        self.assertEqual(covered + points, int(mask.sum()))
        self.assertFalse(traced["remaining"].any())
        # Rebuild the mask from the output and compare exactly.
        rebuilt = np.zeros_like(mask)
        for (x0, y0), (x1, y1) in traced["segments"]:
            n = max(abs(x1 - x0), abs(y1 - y0)) + 1
            xs = np.linspace(x0, x1, n).round().astype(int)
            ys = np.linspace(y0, y1, n).round().astype(int)
            self.assertFalse(rebuilt[ys, xs].any())      # no overlap between runs
            rebuilt[ys, xs] = True
        for x, y in traced["points"]:
            self.assertFalse(rebuilt[y, x])
            rebuilt[y, x] = True
        np.testing.assert_array_equal(rebuilt, mask)

    def test_direction_order_and_run_limits(self):
        mask = np.zeros((6, 9), dtype=bool)
        mask[2, 1:8] = True                       # a horizontal run of 7
        mask[0:6, 4] = True                       # a vertical run crossing it
        h_first = trace_runs(mask, ("h", "v", "p"), min_len=2)
        self.assertEqual(h_first["segments"][0], ((1, 2), (7, 2)))
        self.assertEqual([s for s in h_first["segments"][1:]], [((4, 0), (4, 1)), ((4, 3), (4, 5))])
        v_first = trace_runs(mask, ("v", "h", "p"), min_len=2)
        self.assertEqual(v_first["segments"][0], ((4, 0), (4, 5)))
        self.assertEqual(sorted(v_first["segments"][1:]), [((1, 2), (3, 2)), ((5, 2), (7, 2))])
        split = trace_runs(mask, ("h",), min_len=2, max_len=3)
        self.assertEqual(split["segments"], [((1, 2), (3, 2)), ((4, 2), (6, 2))])
        self.assertTrue(split["remaining"][2, 7])      # the tail of 1 pixel is shorter than min_len

    def test_diagonals_map_to_pixel_coordinates(self):
        mask = np.zeros((5, 7), dtype=bool)
        for i in range(4):
            mask[i, 2 + i] = True                  # down-right from (2, 0)
            mask[i, 6 - i] = True                  # down-left from (6, 0)
        d2 = trace_runs(mask, ("d2",), min_len=2)
        self.assertIn(((2, 0), (5, 3)), d2["segments"])
        d1 = trace_runs(mask, ("d1",), min_len=2)
        self.assertIn(((6, 0), (3, 3)), d1["segments"])
        both = trace_runs(mask, ("d1", "d2", "p"), min_len=2)
        covered, points = pixel_counts(both)
        self.assertEqual(covered + points, int(mask.sum()))

    def test_to_mm_places_pixel_centres(self):
        traced = {"segments": [((0, 0), (3, 0))], "points": np.array([[1, 2]])}
        segments, points = to_mm(traced, .5, (10, 20))
        np.testing.assert_allclose(segments[0], [[10.25, 20.25], [11.75, 20.25]])
        np.testing.assert_allclose(points, [[10.75, 21.25]])
        segments, _ = to_mm(traced, 1, (0, 0), flip_y=True, height_px=4)
        np.testing.assert_allclose(segments[0], [[.5, 3.5], [3.5, 3.5]])


class SamplingTests(unittest.TestCase):
    def test_uniform_poisson_respects_the_radius_and_the_bounds(self):
        rng = np.random.default_rng(2)
        pts = poisson_sample((0, 0, 60, 40), 2.0, rng, quality=300)
        self.assertGreater(len(pts), 300)
        self.assertTrue((pts >= 0).all() and (pts[:, 0] <= 60).all() and (pts[:, 1] <= 40).all())
        d, _ = cKDTree(pts).query(pts, 2)
        self.assertGreaterEqual(d[:, 1].min(), 2.0)
        again = poisson_sample((0, 0, 60, 40), 2.0, np.random.default_rng(2), quality=300)
        np.testing.assert_array_equal(pts, again)

    def test_tone_radius_makes_dark_areas_denser(self):
        tone = np.ones((20, 40))
        tone[:, :20] = 0.                          # left half black
        fn, r_min = tone_radius(tone, (0, 0, 80, 40), 1.0, 4.0)
        rng = np.random.default_rng(3)
        pts = poisson_sample((0, 0, 80, 40), fn, rng, min_radius=r_min, quality=400)
        left, right = (pts[:, 0] < 40).sum(), (pts[:, 0] >= 40).sum()
        self.assertGreater(left, 4 * right)
        # Each point was accepted with its own radius clear of every earlier point
        # (a later, smaller-radius point may still sit inside an earlier point's radius).
        for i in range(1, len(pts)):
            gaps = np.hypot(*(pts[:i] - pts[i]).T)
            self.assertGreaterEqual(gaps.min(), fn(pts[i]) - 1e-9)

    def test_mask_seed_points_and_max_points(self):
        rng = np.random.default_rng(4)
        pts = poisson_sample((0, 0, 30, 30), 1.5, rng, mask=lambda p: p[0] < 15, max_points=50,
                             seed_points=[(2, 2)])
        self.assertEqual(len(pts), 50)
        self.assertTrue((pts[:, 0] < 15).all())
        np.testing.assert_array_equal(pts[0], [2, 2])
        with self.assertRaises(ValueError):
            poisson_sample((0, 0, 10, 10), lambda p: 1.0, rng)

    def test_stratified_grid_has_one_point_per_cell(self):
        rng = np.random.default_rng(5)
        pts = stratified_grid((0, 0, 20, 10), 2.0, rng, separation=.5)
        self.assertEqual(len(pts), 50)
        cells = {(int(x // 2), int(y // 2)) for x, y in pts}
        self.assertEqual(len(cells), 50)
        offsets = np.abs((pts % 2) - 1)            # distance from the cell centre
        self.assertLessEqual(offsets.max(), .5 + 1e-9)


class PlateTests(unittest.TestCase):
    def test_plates_build_inside_their_box_and_record_counts(self):
        tone = specimen(60, 75, 1)
        plate, state = halftone_plate(1, cell=1.0, tone=tone)
        self.assertEqual(plate.metadata["pixels"], [140, 174])
        self.assertGreater(plate.metadata["counts"]["tone_0"]["segments"], 0)
        for s in plate.strokes:
            self.assertTrue((s.points[:, 0] >= 0).all() and (s.points[:, 0] <= 170).all())
        plate, _ = kernels_plate(1, cell=1.0, tone=tone)
        self.assertEqual(len(plate.metadata["cells"]), 6)
        self.assertEqual(plate.metadata["cells"][-1]["kernel"], "bayer-8")
        for variant in (0, 1, 2):
            plate, state = stipple_plate(1, variant, tone=tone)
            self.assertEqual(plate.metadata["dots"], len(state["points"]))
            self.assertGreater(plate.metadata["dots"], 100)
        with self.assertRaises(ValueError):
            stipple_plate(1, 9, tone=tone)

    def test_book_importer_reads_a_halftone_svg(self):
        importer = SNAPSHOT / "common/plot/svgimport.py"
        spec = importlib.util.spec_from_file_location("book_svgimport", importer)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plate = halftone_plate(1, cell=1.2, tone=specimen(40, 50, 1))[0]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "plate.svg"
            path.write_text(plate.svg())
            imported = module.strokes_from_svg(path)
        from lib.process_art.drawing import INK, RED
        expected = [s for s in plate.strokes if s.color == INK] + [s for s in plate.strokes if s.color == RED]
        self.assertEqual(len(imported), len(expected))
        for (color, width, points), original in zip(imported, expected):
            self.assertEqual(color, original.color)
            np.testing.assert_allclose(points, original.points, atol=.00051)


if __name__ == "__main__":
    unittest.main()
