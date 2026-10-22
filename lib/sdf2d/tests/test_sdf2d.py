"""Invariants for the 2-D distance-field package: exact primitives, operator algebra, grids."""
import unittest

import numpy as np

from lib.sdf2d import (annular, band, box, circle, contours, ellipse, hatch_by_sign, intersect,
                       intersect_round, levels, mirror_x, offset, polygon, polyline, repeat, repeat_mirror,
                       repeat_polar, rotate, rounded_box, sample, scale, segment, subtract, subtract_chamfer,
                       subtract_steps, translate, union, union_chamfer, union_round, union_smooth, union_steps)
from lib.sdf2d.studies import apparatus_plate, tiling_plate


def _points(seed=0, n=400, extent=20):
    return np.random.default_rng(seed).uniform(-extent, extent, (n, 2))


class PrimitiveTests(unittest.TestCase):
    def test_circle_and_box_are_exact(self):
        c = circle(5, (1, 2))
        np.testing.assert_allclose(c([(1, 2), (6, 2), (1, 9)]), [-5, 0, 2])
        b = box(4, 2)
        np.testing.assert_allclose(b([(0, 0), (4, 0), (7, 0), (7, 6), (3, 1)]), [-2, 0, 3, 5, -1])
        rb = rounded_box(4, 2, 1)
        self.assertAlmostEqual(float(rb([(4, 2)])[0]), np.sqrt(2) - 1)
        self.assertAlmostEqual(float(rb([(0, 0)])[0]), -2)

    def test_segment_polyline_and_polygon(self):
        s = segment((0, 0), (10, 0))
        np.testing.assert_allclose(s([(5, 3), (-4, 0), (13, 4)]), [3, 4, 5])
        pl = polyline([(0, 0), (10, 0), (10, 10)])
        np.testing.assert_allclose(pl([(5, 1), (11, 5)]), [1, 1])
        square = polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        np.testing.assert_allclose(square([(5, 5), (5, 0), (5, -3), (12, 5), (1, 1)]), [-5, 0, 3, 2, -1])
        # The polygon distance agrees with the box distance everywhere, including the sign.
        p = _points(1)
        np.testing.assert_allclose(square(p), box(5, 5, (5, 5))(p), atol=1e-9)
        concave = polygon([(0, 0), (10, 0), (10, 10), (5, 5), (0, 10)])
        self.assertGreater(float(concave([(5, 8)])[0]), 0)
        self.assertLess(float(concave([(2, 3)])[0]), 0)

    def test_ellipse_is_exact_on_its_axes(self):
        e = ellipse(6, 3)
        np.testing.assert_allclose(e([(6, 0), (0, 3), (9, 0), (0, 0)]), [0, 0, 3, -3], atol=1e-9)


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.a = circle(6, (-3, 0))
        self.b = circle(6, (3, 0))
        self.p = _points(2)

    def test_plain_booleans_are_min_max(self):
        np.testing.assert_allclose(union(self.a, self.b)(self.p), np.minimum(self.a(self.p), self.b(self.p)))
        np.testing.assert_allclose(intersect(self.a, self.b)(self.p), np.maximum(self.a(self.p), self.b(self.p)))
        np.testing.assert_allclose(subtract(self.a, self.b)(self.p), np.maximum(self.a(self.p), -self.b(self.p)))

    def test_blended_unions_fill_the_crease_and_match_far_away(self):
        plain = union(self.a, self.b)(self.p)
        for blended in (union_chamfer(self.a, self.b, 2), union_round(self.a, self.b, 2),
                        union_smooth(self.a, self.b, 2), union_steps(self.a, self.b, 2, 3)):
            v = blended(self.p)
            self.assertTrue((v <= plain + 1e-9).all())              # never smaller a shape than the union
            far = np.abs(self.a(self.p) - self.b(self.p)) > 6       # one shape dominates
            np.testing.assert_allclose(v[far], plain[far], atol=1e-9)
        crease = np.array([(0.0, 5.2)])                              # just outside both circles, in the notch
        self.assertGreater(float(union(self.a, self.b)(crease)[0]), 0)
        self.assertLess(float(union_round(self.a, self.b, 3)(crease)[0]), 0)

    def test_de_morgan_variants(self):
        p = self.p
        np.testing.assert_allclose(intersect_round(self.a, self.b, 2)(p),
                                   -union_round(lambda q: -self.a(q), lambda q: -self.b(q), 2)(p))
        np.testing.assert_allclose(subtract_chamfer(self.a, self.b, 2)(p),
                                   -union_chamfer(lambda q: -self.a(q), self.b, 2)(p))
        stepped = subtract_steps(box(10, 10), box(4, 4, (10, 0)), 4, 2)(p)
        self.assertTrue(np.isfinite(stepped).all())

    def test_domain_operators(self):
        c = circle(2)
        np.testing.assert_allclose(translate(c, (5, 5))([(5, 5)]), [-2])
        bar = box(4, 1)
        np.testing.assert_allclose(rotate(bar, 90)([(0, 3), (3, 0)]), [-1, 2])
        np.testing.assert_allclose(rotate(box(4, 1, (10, 0)), 90, center=(10, 0))([(10, 3), (13, 0)]), [-1, 2])
        np.testing.assert_allclose(rotate(bar, 90, center=(10, 0))([(10, -10), (10, -6)]), [-1, 0], atol=1e-9)
        np.testing.assert_allclose(scale(c, 3)([(0, 0), (9, 0)]), [-6, 3])
        half = box(2, 2, (3, 0))
        np.testing.assert_allclose(mirror_x(half)([(-3, 0), (3, 0)]), [-2, -2])
        tiled = repeat(c, 10)
        np.testing.assert_allclose(tiled(self.p), tiled(self.p + [10, -20]), atol=1e-9)
        np.testing.assert_allclose(tiled([(0, 0), (10, 10), (5, 5)]), [-2, -2, np.hypot(5, 5) - 2])
        mirrored = repeat_mirror(translate(c, (3, 0)), 10)
        # Cells alternate: the circle sits at 3, then mirrored at 7, then at 23; 13 and 17 are empty.
        np.testing.assert_allclose(mirrored([(3, 0), (7, 0), (23, 0), (13, 0), (17, 0)]), [-2, -2, -2, 4, 4])
        polar = repeat_polar(translate(c, (8, 0)), 6)
        angles = np.radians(np.arange(6) * 60)
        np.testing.assert_allclose(polar(np.column_stack([8 * np.cos(angles), 8 * np.sin(angles)])), -2, atol=1e-9)
        np.testing.assert_allclose(offset(c, 1)([(0, 0)]), [-3])
        np.testing.assert_allclose(annular(c, .5)([(0, 0), (2, 0), (3, 0)]), [1.5, -.5, .5])
        np.testing.assert_allclose(band(c, 0, 1)([(2, 0), (1.5, 0), (0, 0)]), [0, -.5, 1])
        with self.assertRaises(ValueError):
            band(c, 2, 1)


class GridTests(unittest.TestCase):
    def test_contours_of_a_circle_lie_on_the_circle(self):
        values, xs, ys = sample(circle(10, (15, 15)), (0, 0, 30, 30), .25)
        self.assertEqual(values.shape, (121, 121))
        lines = contours(values, xs, ys, 0.0)
        self.assertEqual(len(lines), 1)
        r = np.hypot(*(lines[0] - [15, 15]).T)
        np.testing.assert_allclose(r, 10, atol=.02)
        inner = levels(values, xs, ys, [-2, -4])
        np.testing.assert_allclose(np.hypot(*(inner[-4.0][0] - [15, 15]).T), 6, atol=.02)
        simplified = contours(values, xs, ys, 0.0, simplify=.1)
        self.assertLess(len(simplified[0]), len(lines[0]))
        with self.assertRaises(ValueError):
            sample(circle(1), (0, 0, 1, 1), 0)

    def test_hatch_by_sign_stays_inside_and_is_spaced(self):
        f = circle(10, (15, 15))
        lines = hatch_by_sign(f, (0, 0, 30, 30), 1.0, 0.0, step=.1)
        self.assertEqual(len(lines), 19)
        for line in lines:
            self.assertEqual(len(line), 2)
            self.assertTrue((f(line) <= .06).all())                  # ends land on the boundary
            self.assertAlmostEqual(line[0, 1], line[1, 1])
        ys = sorted(float(l[0, 1]) for l in lines)
        np.testing.assert_allclose(np.diff(ys), 1.0, atol=1e-9)
        longest = max(lines, key=lambda l: abs(l[1, 0] - l[0, 0]))
        self.assertAlmostEqual(abs(longest[1, 0] - longest[0, 0]), 20, delta=.05)
        angled = hatch_by_sign(f, (0, 0, 30, 30), 1.5, 60.0, step=.1)
        d = np.array([np.cos(np.radians(60)), np.sin(np.radians(60))])
        for line in angled:
            v = line[1] - line[0]
            self.assertAlmostEqual(abs(v @ d) / np.linalg.norm(v), 1, places=6)
        ring = hatch_by_sign(annular(f, 2), (0, 0, 30, 30), 1.0, 0.0, step=.1)
        self.assertGreater(len(ring), len(lines))                      # the hole splits runs in two


class PlateTests(unittest.TestCase):
    def test_plates_build_and_stay_inside(self):
        for fn, variants in ((apparatus_plate, (0, 1)), (tiling_plate, (0, 1))):
            for variant in variants:
                plate, state = fn(0, variant, resolution=.5)
                self.assertGreater(len(plate.strokes), 10)
                self.assertEqual(plate.metadata["variant"], variant)
                for s in plate.strokes:
                    self.assertTrue((s.points >= 0).all())
                    self.assertTrue((s.points[:, 0] <= 170).all() and (s.points[:, 1] <= 220).all())
            with self.assertRaises(ValueError):
                fn(0, 7)
        a, b = apparatus_plate(0, 1, resolution=.5)[0], apparatus_plate(0, 1, resolution=.5)[0]
        self.assertEqual(a.svg(), b.svg())


if __name__ == "__main__":
    unittest.main()
