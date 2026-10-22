"""Frames, clipping, hatching, contouring, screen spacing and the two sources.

Run from the repository root:
    python -m unittest discover -s lib/face_patterns/tests -v
"""
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.face_patterns import (clip_polyline, contour_on_face, cut_discs, hatch_polygon, inside,  # noqa: E402
                               keep_where, level_spacing_px, lift, plane_frame, stride_for_spacing, to_uv,
                               world_spacing)
from lib.face_patterns.sources import Strata, quilt  # noqa: E402


def wall(x0, y0, x1, y1, z0, z1):
    """A vertical quad wound so that its outward normal points to the right of a->b."""
    return np.array([(x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)], float)


def length(lines):
    return sum(np.linalg.norm(np.diff(q, axis=0), axis=1).sum() for q in lines)


def orthographic(scale):
    return lambda P, U, V: np.broadcast_to(np.eye(2) * scale, (len(P), 2, 2)).copy()


class FrameTests(unittest.TestCase):
    def test_walls_read_right_and_up_from_outside(self):
        front = plane_frame(wall(0, 0, 4, 0, 0, 3))   # faces -y
        side = plane_frame(wall(4, 0, 4, 3, 0, 3))    # faces +x
        top = plane_frame([(0, 0, 3), (4, 0, 3), (4, 3, 3), (0, 3, 3)])
        np.testing.assert_allclose(front.N, (0, -1, 0), atol=1e-12)
        np.testing.assert_allclose(front.U, (1, 0, 0), atol=1e-12)
        np.testing.assert_allclose(side.N, (1, 0, 0), atol=1e-12)
        np.testing.assert_allclose(side.U, (0, 1, 0), atol=1e-12)
        np.testing.assert_allclose(top.U, (1, 0, 0), atol=1e-12)
        for f in (front, side, top):
            np.testing.assert_allclose(np.cross(f.U, f.V), f.N, atol=1e-12)
            self.assertAlmostEqual(f.U @ f.V, 0.)

    def test_coplanar_faces_share_coordinates(self):
        a, b = wall(0, 0, 2, 0, 0, 3), wall(2, 0, 5, 0, 0, 3)
        fa, fb = plane_frame(a), plane_frame(b)
        np.testing.assert_allclose(to_uv(a[1:3], fa), to_uv(b[[0, 3]], fb))

    def test_lift_inverts_to_uv_on_the_plane(self):
        q = wall(1, 2, 4, 6, -1, 2); f = plane_frame(q)
        pts = q[0] + np.random.default_rng(3).random((20, 2)) @ np.array([q[1] - q[0], q[3] - q[0]])
        np.testing.assert_allclose(lift(to_uv(pts, f), f), pts, atol=1e-9)
        np.testing.assert_allclose((lift(to_uv(pts, f), f, .01) - pts) @ f.N, .01, atol=1e-9)

    def test_a_course_meets_itself_around_a_corner(self):
        front, side = plane_frame(wall(0, 0, 4, 0, 0, 3)), plane_frame(wall(4, 0, 4, 3, 0, 3))
        corner = np.array([[4., 0., 1.7]])
        self.assertAlmostEqual(to_uv(corner, front)[0, 1], to_uv(corner, side)[0, 1])


class ClipTests(unittest.TestCase):
    L_SHAPE = np.array([(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (0, 3)], float)

    def test_convex_clip_is_exact(self):
        sq = np.array([(0, 0), (2, 0), (2, 2), (0, 2)], float)
        pieces = clip_polyline([(-1, 1), (3, 1)], sq)
        self.assertEqual(len(pieces), 1)
        np.testing.assert_allclose(pieces[0], [(0, 1), (2, 1)], atol=1e-9)

    def test_concave_polygon_splits_a_line(self):
        pieces = clip_polyline([(-1, .5), (5, .5)], self.L_SHAPE)
        self.assertEqual(len(pieces), 1)
        self.assertAlmostEqual(length(pieces), 4.)
        # Through the upright and across the notch: one piece, the notch is outside.
        pieces = clip_polyline([(-1, 2), (5, 2)], self.L_SHAPE)
        self.assertEqual(len(pieces), 1)
        self.assertAlmostEqual(length(pieces), 1.)
        # Up the upright and out through its side, then back into the foot:
        # (.5,0)-(.5,2)-(1,2) and (3,1)-(3,.5)-(4,.5).
        zig = clip_polyline([(.5, -1), (.5, 2), (3, 2), (3, .5), (5, .5)], self.L_SHAPE)
        self.assertEqual(len(zig), 2)
        self.assertAlmostEqual(length(zig), 2.5 + 1.5, places=9)
        for q in zig:
            mids = (q[1:] + q[:-1]) / 2
            self.assertTrue(inside(mids, self.L_SHAPE).all())

    def test_hatching_is_inside_evenly_spaced_and_continuous(self):
        lines = hatch_polygon(self.L_SHAPE, .25, 0., phase=.125)
        for q in lines:
            self.assertTrue(inside((q[1:] + q[:-1]) / 2, self.L_SHAPE).all())
        ys = sorted({round(q[0, 1], 9) for q in lines})
        self.assertEqual(len(ys), 12)
        np.testing.assert_allclose(np.diff(ys), .25)
        self.assertAlmostEqual(length(lines), 4 * 4. + 8 * 1.)
        left = hatch_polygon([(0, 0), (1, 0), (1, 1), (0, 1)], .3, 30.)
        right = hatch_polygon([(1, 0), (2, 0), (2, 1), (1, 1)], .3, 30.)
        offsets = lambda lines: {round(float(q[0] @ np.array([-.5, np.sqrt(3) / 2])), 9) for q in lines}
        self.assertTrue(offsets(left) & offsets(right))
        for k in offsets(left) | offsets(right):
            self.assertAlmostEqual(k / .3, round(k / .3))


class ContourTests(unittest.TestCase):
    def test_level_lines_of_height_are_courses(self):
        q = wall(0, 0, 4, 0, .1, 2.1); f = plane_frame(q); poly = to_uv(q, f)
        lines = contour_on_face(lambda P: P[:, 2], poly, f, .25, .05)
        self.assertEqual(sorted(k for k, _ in lines), list(range(1, 9)))
        for k, line in lines:
            np.testing.assert_allclose(lift(line, f)[:, 2], k * .25, atol=1e-6)
        self.assertAlmostEqual(length([line for _, line in lines]), 8 * 4., places=5)

    def test_a_blank_seam_is_not_bridged(self):
        q = wall(0, 0, 4, 0, 0, 2); f = plane_frame(q); poly = to_uv(q, f)

        def faulted(P):
            z = P[:, 2] + .3 * (P[:, 0] > 2)
            z[np.abs(P[:, 0] - 2) < .06] = np.nan
            return z
        for k, line in contour_on_face(faulted, poly, f, .25, .02):
            P = lift(line, f)
            self.assertFalse((P[:, 0].min() < 1.9) and (P[:, 0].max() > 2.1), f'level {k} crosses the fault')

    def test_screen_spacing_and_nested_stride(self):
        q = wall(0, 0, 4, 0, 0, 2); f = plane_frame(q); poly = to_uv(q, f)
        px = level_spacing_px(lambda P: P[:, 2], poly, f, .25, .1, orthographic(20.))
        self.assertAlmostEqual(px, 5.)
        self.assertEqual(stride_for_spacing(px, 4.4), 1)
        self.assertEqual(stride_for_spacing(px, 9.), 2)
        self.assertEqual(stride_for_spacing(px, 18.), 4)
        self.assertAlmostEqual(world_spacing(5., f, poly, 45., orthographic(20.)), .25)


class CutTests(unittest.TestCase):
    def test_cut_discs_leaves_nothing_inside_and_everything_outside(self):
        line = np.array([(-2., 0.), (2., 0.)])
        pieces = cut_discs([line], [((0, 0), .5)], step=.01)
        self.assertEqual(len(pieces), 2)
        pts = np.vstack(pieces)
        self.assertTrue((np.hypot(*pts.T) > .5).all())
        self.assertAlmostEqual(length(pieces), 3.0, delta=.03)   # 4 minus the 1.0 diameter
        self.assertAlmostEqual(length(cut_discs([line], [])), 4.0)

    def test_keep_where_reports_the_kept_fraction(self):
        lines = [np.array([(0., y), (10., y)]) for y in (0., 1.)]
        kept, fraction = keep_where(lines, lambda x, y: x < 2.5, step=.05)
        self.assertAlmostEqual(fraction, .25, delta=.01)
        self.assertTrue(all((q[:, 0] < 2.5).all() for q in kept))
        none, zero = keep_where(lines, lambda x, y: np.zeros(len(x), bool), step=.05)
        self.assertEqual((none, zero), ([], 0.))


class SourceTests(unittest.TestCase):
    def test_strata_lines_meet_at_a_corner_and_lie_level_across_the_axis(self):
        s = Strata(origin=(0, 0, 3), axis=(1, 0, 0), scale=3.5, seed=11, n=160)
        front, side = wall(-1.65, -1.5, 1.65, -1.5, .2, 5.8), wall(1.65, -1.5, 1.65, 1.5, .2, 5.8)
        on_edge = lambda P: abs(P[0] - 1.65) < 1e-6 and abs(P[1] + 1.5) < 1e-6
        ends = {}
        for q in (front, side):
            f = plane_frame(q)
            for k, line in contour_on_face(s, to_uv(q, f), f, .07, .01):
                for end in lift(line, f)[[0, -1]]:
                    if on_edge(end):
                        ends.setdefault(k, []).append(end[2])
        met = [k for k, zs in ends.items() if len(zs) == 2]
        self.assertGreater(len(met), 12)
        for k in met:
            self.assertAlmostEqual(ends[k][0], ends[k][1], delta=1e-6)
        side = np.array([[1.65, y, 2.4] for y in np.linspace(-1.5, 1.5, 9)])
        values = s(side)
        self.assertTrue(np.isfinite(values).all())
        np.testing.assert_allclose(values, values[0])
        front = np.array([[x, -1.5, 2.4] for x in np.linspace(-1.6, 1.6, 33)])
        self.assertGreater(np.nanstd(s(front)), 1e-3)

    def test_strata_blank_their_fault_seams_and_repeat(self):
        s = Strata(origin=(0, 0, 0), axis=(1, 0, 0), scale=1., seed=11, n=320)
        x = np.linspace(-.95, .95, 4001)
        values = s(np.column_stack([x, np.zeros_like(x), np.zeros_like(x)]))
        self.assertTrue(np.isnan(values).any() and np.isfinite(values).mean() > .95)
        again = Strata(origin=(0, 0, 0), axis=(1, 0, 0), scale=1., seed=11, n=320)
        np.testing.assert_array_equal(values, again(np.column_stack([x, 0 * x, 0 * x])))

    def test_quilt_regions_tile_the_unit_square(self):
        q = quilt('ohio-star')
        area = lambda p: abs(np.dot(p[:, 0], np.roll(p[:, 1], 1)) - np.dot(p[:, 1], np.roll(p[:, 0], 1))) / 2
        self.assertAlmostEqual(sum(area(p) for p, _ in q['regions']), 1.)
        self.assertEqual({r for _, r in q['regions']}, {0, 1, 2})
        for e in q['edges']:
            self.assertTrue(((e >= -1e-12) & (e <= 1 + 1e-12)).all())


if __name__ == '__main__':
    unittest.main()
