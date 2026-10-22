"""Invariants for the fuzz package: subdivision, splines, passes and fills."""
import unittest

import numpy as np
from shapely.geometry import LineString, Point, Polygon

from lib.fuzz import (SCHEMES, compose, cubic_points, cubics_to_polyline, dot_fill, dot_pen, dots_as_rings,
                      fuzzy_line, fuzzy_polygon, hatch_fill, hatch_pen, polygon_to_cubic, subdivide, union)
from lib.fuzz.studies import fills_plate, passes_plate, subdivision_plate

SQUARE = np.array([(0., 0.), (10., 0.), (10., 10.), (0., 10.)])
OPEN = np.array([(0., 0.), (4., 3.), (8., 0.), (12., 3.)])


class SubdivisionTests(unittest.TestCase):
    def test_point_counts_and_end_points(self):
        for scheme in ("chaikin", "cubic", "dlg", "midpoint", "thirds", "displace"):
            rng = np.random.default_rng(0)
            closed = subdivide(SQUARE, scheme, 1, closed=True, rng=rng)
            self.assertEqual(len(closed), 12 if scheme == "thirds" else 8, scheme)
            open_ = subdivide(OPEN, scheme, 1, closed=False, rng=rng)
            np.testing.assert_allclose(open_[0], OPEN[0], err_msg=scheme)
            np.testing.assert_allclose(open_[-1], OPEN[-1], err_msg=scheme)
        self.assertEqual(len(subdivide(SQUARE, "chaikin", 3, closed=True)), 32)
        with self.assertRaises(ValueError):
            subdivide(SQUARE, "unknown")
        with self.assertRaises(ValueError):
            subdivide(SQUARE, "displace")

    def test_chaikin_cuts_corners_and_converges_inside(self):
        p = subdivide(SQUARE, "chaikin", 4, closed=True)
        self.assertTrue(Polygon(SQUARE).buffer(1e-9).contains(Polygon(p)))
        # The limit curve is the uniform quadratic B-spline, whose area is 5/6 of the square's.
        self.assertAlmostEqual(Polygon(p).area, Polygon(SQUARE).area * 5 / 6, delta=.5)
        one = subdivide(SQUARE, "chaikin", 1, closed=True)
        np.testing.assert_allclose(one[:2], [[2.5, 0], [7.5, 0]])   # the first edge is cut at 1/4 and 3/4

    def test_dlg_interpolates_the_control_points(self):
        p = subdivide(SQUARE, "dlg", 3, closed=True)
        for v in SQUARE:
            self.assertLess(np.linalg.norm(p - v, axis=1).min(), 1e-9)
        # A new midpoint bulges outward from the edge for a convex square: 9/16 (p1+p2) - 1/16 (p0+p3).
        one = subdivide(SQUARE, "dlg", 1, closed=True)
        np.testing.assert_allclose(one[1], [5, -1.25])

    def test_cubic_is_lane_riesenfeld(self):
        one = subdivide(SQUARE, "cubic", 1, closed=True)
        np.testing.assert_allclose(one[0], (SQUARE[3] + 6 * SQUARE[0] + SQUARE[1]) / 8)
        np.testing.assert_allclose(one[1], (SQUARE[0] + SQUARE[1]) / 2)

    def test_displace_with_zero_amplitude_is_midpoint(self):
        rng = np.random.default_rng(1)
        a = subdivide(OPEN, "displace", 2, closed=False, rng=rng, amplitude=0)
        b = subdivide(OPEN, "midpoint", 2, closed=False)
        np.testing.assert_allclose(a, b)
        rough = subdivide(OPEN, "displace", 2, closed=False, rng=np.random.default_rng(1), amplitude=.3)
        self.assertFalse(np.allclose(rough, b))
        again = subdivide(OPEN, "displace", 2, closed=False, rng=np.random.default_rng(1), amplitude=.3)
        np.testing.assert_allclose(rough, again)


class SplineTests(unittest.TestCase):
    def test_break_mode_passes_through_the_vertices(self):
        segments = polygon_to_cubic(SQUARE, "break", 1 / 3, closed=True)
        self.assertEqual(len(segments), 4)
        for i, (p0, c1, c2, p3) in enumerate(segments):
            np.testing.assert_allclose(p0, SQUARE[i])
            np.testing.assert_allclose(p3, SQUARE[(i + 1) % 4])
            self.assertAlmostEqual(np.linalg.norm(c1 - p0), 10 / 3)
        open_segments = polygon_to_cubic(OPEN, "break", closed=False)
        self.assertEqual(len(open_segments), 3)
        np.testing.assert_allclose(open_segments[0][0], OPEN[0])
        np.testing.assert_allclose(open_segments[-1][3], OPEN[-1])

    def test_midpoint_mode_passes_through_edge_midpoints(self):
        segments = polygon_to_cubic(SQUARE, "midpoint", 2 / 3, closed=True)
        self.assertEqual(len(segments), 4)
        np.testing.assert_allclose(segments[0][0], [0, 5])
        np.testing.assert_allclose(segments[0][3], [5, 0])
        # Tightness 2/3 reproduces the quadratic through the midpoints with the vertex as control.
        mid = cubic_points(segments[0], 3)[1]
        np.testing.assert_allclose(mid, .25 * np.array([0, 5]) + .5 * SQUARE[0] + .25 * np.array([5, 0]))
        open_segments = polygon_to_cubic(OPEN, "midpoint", closed=False)
        np.testing.assert_allclose(open_segments[0][0], OPEN[0])
        np.testing.assert_allclose(open_segments[-1][3], OPEN[-1])

    def test_uniform_handles_and_validation(self):
        rect = np.array([(0., 0.), (20., 0.), (20., 5.), (0., 5.)])
        prop = polygon_to_cubic(rect, "break", .5, uniform=False)
        uni = polygon_to_cubic(rect, "break", .5, uniform=True)
        self.assertAlmostEqual(np.linalg.norm(prop[0][1] - prop[0][0]), 10)
        self.assertAlmostEqual(np.linalg.norm(uni[0][1] - uni[0][0]), 6.25)
        with self.assertRaises(ValueError):
            polygon_to_cubic(rect, "other")
        with self.assertRaises(ValueError):
            polygon_to_cubic(rect, "break", 0)

    def test_polyline_sampling_closes(self):
        poly = cubics_to_polyline(polygon_to_cubic(SQUARE, "break"), 6, closed=True)
        self.assertEqual(len(poly), 4 * 6 + 1)
        np.testing.assert_allclose(poly[0], poly[-1])


class FuzzTests(unittest.TestCase):
    def test_passes_jitter_and_repeat(self):
        rng = np.random.default_rng(2)
        lines = fuzzy_polygon(SQUARE, rng, passes=3, jitter=.3, curve=False)
        self.assertEqual(len(lines), 3)
        for line in lines:
            np.testing.assert_allclose(line[0], line[-1])
            self.assertLess(np.abs(line[:-1] - SQUARE).max(), 1.5)
        self.assertFalse(np.allclose(lines[0], lines[1]))
        exact = fuzzy_polygon(SQUARE, rng, passes=1, jitter=0, curve=False)[0]
        np.testing.assert_allclose(exact[:-1], SQUARE)
        curved = fuzzy_polygon(SQUARE, np.random.default_rng(3), passes=1, jitter=0, curve=True, samples=8)[0]
        for v in SQUARE:                            # a jitter-free curve still passes through the vertices
            self.assertLess(np.linalg.norm(curved - v, axis=1).min(), 1e-9)
        a = fuzzy_polygon(SQUARE, np.random.default_rng(4), 2, .2)
        b = fuzzy_polygon(SQUARE, np.random.default_rng(4), 2, .2)
        for x, y in zip(a, b):
            np.testing.assert_allclose(x, y)

    def test_fuzzy_line_resamples_then_jitters(self):
        line = fuzzy_line([(0, 0), (10, 0)], np.random.default_rng(5), jitter=.1, resample=1.0)[0]
        self.assertEqual(len(line), 11)
        self.assertLess(np.abs(line[:, 1]).max(), .6)
        self.assertEqual(len(fuzzy_line([(0, 0), (10, 0)], np.random.default_rng(5), passes=3)), 3)

    def test_hatch_lines_lie_inside_and_follow_the_angle(self):
        poly = Polygon(SQUARE)
        for angle in (0, 30, 45, 90, 160):
            lines = hatch_fill(poly, 1.0, angle)
            self.assertGreater(len(lines), 5)
            d = np.array([np.cos(np.radians(angle)), np.sin(np.radians(angle))])
            for line in lines:
                self.assertTrue(poly.buffer(1e-6).contains(LineString(line)))
                v = line[-1] - line[0]
                self.assertAlmostEqual(abs(np.dot(v, d)) / np.linalg.norm(v), 1, places=6)
        horizontal = hatch_fill(poly, 1.0, 0)
        ys = sorted(float(l[0, 1]) for l in horizontal)
        np.testing.assert_allclose(np.diff(ys), 1.0, atol=1e-6)
        alternating = [np.sign(l[-1, 0] - l[0, 0]) for l in sorted(horizontal, key=lambda l: l[0, 1])]
        self.assertTrue(all(a != b for a, b in zip(alternating, alternating[1:])))
        inset = hatch_fill(poly, 1.0, 0, inset=2)
        self.assertTrue(all(poly.buffer(-2 + 1e-6).contains(LineString(l)) for l in inset))
        self.assertEqual(hatch_fill(poly, 1.0, 0, inset=6), [])
        with self.assertRaises(ValueError):
            hatch_fill(poly, 0, 0)

    def test_jittered_hatch_stays_inside_and_varies(self):
        poly = Polygon(SQUARE)
        a = hatch_fill(poly, 1.0, 30, np.random.default_rng(6), jitter=.2)
        b = hatch_fill(poly, 1.0, 30, np.random.default_rng(7), jitter=.2)
        self.assertFalse(np.allclose(a[3], b[3]))
        for line in a:
            self.assertTrue(poly.buffer(.3).contains(LineString(line)))

    def test_dots_fall_inside_and_compose(self):
        poly = Polygon(SQUARE)
        pts = dot_fill(poly, 1.0, np.random.default_rng(8), jitter=.3)
        self.assertGreater(len(pts), 80)
        for p in pts:
            self.assertTrue(poly.contains(Point(p)))
        rings = dots_as_rings(pts[:3], .2)
        self.assertEqual(len(rings), 3)
        np.testing.assert_allclose(rings[0][0], rings[0][-1])
        both = compose(hatch_pen(1.5, 45), dot_pen(2.0))(poly, np.random.default_rng(9))
        self.assertEqual(len(both), len(hatch_pen(1.5, 45)(poly, np.random.default_rng(9)))
                         + len(dot_pen(2.0)(poly, np.random.default_rng(9))))
        merged = union([SQUARE, SQUARE + [5, 5]])
        self.assertAlmostEqual(merged.area, 175)


class PlateTests(unittest.TestCase):
    def test_plates_build_and_stay_inside(self):
        for fn, cells in ((passes_plate, 8), (fills_plate, 6), (subdivision_plate, 4)):
            plate, state = fn(0)
            self.assertEqual(len(plate.metadata["cells"]), cells)
            self.assertGreater(len(plate.strokes), 20)
            for s in plate.strokes:
                self.assertTrue((s.points >= 0).all())
                self.assertTrue((s.points[:, 0] <= 170).all() and (s.points[:, 1] <= 220).all())
        a, b = passes_plate(3)[0], passes_plate(3)[0]
        self.assertEqual(a.svg(), b.svg())


if __name__ == "__main__":
    unittest.main()
