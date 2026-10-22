"""Bur oak geometry (oak.py) and its engraving marks (crown.py).

Run from the repository root:
    python -m unittest discover -s lib/flora/tests -v
"""
import unittest

import numpy as np

from lib.flora.oak import Oak, icosphere, savanna_oak, tube
from lib.flora import crown as C


def signed_volume(verts, faces):
    v = np.asarray(verts, float); vol = 0.
    for f in faces:
        for j in range(1, len(f) - 1):
            a, b, c = v[f[0]], v[f[j]], v[f[j + 1]]
            vol += a @ np.cross(b, c) / 6
    return vol


def edge_uses(faces):
    uses = {}
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            key = (min(a, b), max(a, b)); uses[key] = uses.get(key, 0) + 1
    return uses


def nearest_on(points, q):
    d = np.linalg.norm(points - q, axis=1); i = int(np.argmin(d))
    return i, float(d[i])


def polyline_distance(points, q):
    a, b = points[:-1], points[1:]; d = b - a
    t = np.clip(((q - a) * d).sum(1) / np.maximum((d * d).sum(1), 1e-18), 0, 1)
    return float(np.linalg.norm(a + t[:, None] * d - q, axis=1).min())


class OakTests(unittest.TestCase):
    def test_repeatable_and_seed_dependent(self):
        a, b, c = savanna_oak(5, 6.7), savanna_oak(5, 6.7), savanna_oak(6, 6.7)
        for la, lb in zip(a.limbs, b.limbs):
            np.testing.assert_array_equal(la.points, lb.points); np.testing.assert_array_equal(la.radii, lb.radii)
        np.testing.assert_array_equal([m.centre for m in a.clumps], [m.centre for m in b.clumps])
        self.assertFalse(np.allclose(a.limbs[1].points[-1], c.limbs[1].points[-1]))

    def test_open_grown_habit(self):
        for seed in (1, 371, 900):
            for H in (4.6, 6.7):
                oak = savanna_oak(seed, H)
                V = np.vstack([v for part, v, _ in oak.meshes() if part == 'crown'])
                self.assertTrue(.9 * H <= V[:, 2].max() <= 1.1 * H, (seed, H, V[:, 2].max()))
                reach = np.hypot(V[:, 0], V[:, 1]).max()
                self.assertTrue(.75 * oak.metadata['spread'] <= reach <= 1.2 * oak.metadata['spread'], (seed, reach))
                trunk = oak.limbs[0]
                self.assertLess(trunk.points[0, 2], 0)                       # set into the ground
                self.assertGreater(trunk.radii[0], trunk.radii[-1])           # flared at the foot
                self.assertGreater(V[:, 2].min(), .15 * H)                    # foliage clears the trunk
                self.assertTrue(4 <= sum(l.order == 1 for l in oak.limbs) <= 6)

    def test_limbs_taper_and_start_inside_their_parent(self):
        oak = savanna_oak(371, 6.7)
        for limb in oak.limbs:
            self.assertTrue((np.diff(limb.radii[3:]) <= 1e-12).all())
            if limb.parent < 0:
                continue
            parent = oak.limbs[limb.parent]
            i, d = nearest_on(parent.points, limb.points[0])
            self.assertLessEqual(d, parent.radii[i] + 1e-9)
            self.assertLessEqual(limb.radii[0], parent.radii[i] + 1e-9)

    def test_meshes_are_closed_and_wound_outward(self):
        oak = savanna_oak(371, 6.7, detail=1)
        for part, v, f in oak.meshes():
            uses = edge_uses(f)
            self.assertTrue(all(n == 2 for n in uses.values()), part)
            self.assertGreater(signed_volume(v, f), 0, part)
        v, f = icosphere(2)
        self.assertEqual(len(f), 320); self.assertGreater(signed_volume(v, f), 0)

    def test_tube_follows_its_centreline(self):
        p = np.array([[0, 0, 0], [0, 0, 1], [1, 0, 2.]]); r = np.array([.2, .15, .1])
        v, f = tube(p, r, 8)
        rings = v.reshape(3, 8, 3)
        for k in range(3):
            np.testing.assert_allclose(np.linalg.norm(rings[k] - p[k], axis=1), r[k], atol=1e-9)
        self.assertGreater(signed_volume(v, f), 0)

    def test_bare_stage_and_detail(self):
        leafy, bare = savanna_oak(9, 6.), savanna_oak(9, 6., stage='bare')
        self.assertEqual(bare.clumps, []); self.assertTrue(leafy.clumps)
        # The same tree, limb for limb (bare twigs reach a little further out), plus winter spurs.
        self.assertGreater(len(bare.limbs), len(leafy.limbs) + 20)
        for a, b in zip(leafy.limbs, bare.limbs):
            self.assertEqual((a.order, a.parent), (b.order, b.parent))
            if a.order < 3:
                np.testing.assert_array_equal(a.points, b.points)
        far, near = savanna_oak(9, 6., detail=1), savanna_oak(9, 6., detail=3)
        np.testing.assert_array_equal(far.limbs[2].points, near.limbs[2].points)
        np.testing.assert_array_equal([m.centre for m in far.clumps], [m.centre for m in near.clumps])
        count = lambda o: sum(len(f) for _, _, f in o.meshes())
        self.assertLess(count(far), count(near))

    def test_furrows_ride_the_bark(self):
        oak = savanna_oak(371, 6.7)
        furrows = oak.furrows()
        self.assertGreater(len(furrows), 100)
        for f in furrows[::25]:
            limb = oak.limbs[f.limb]
            for p, n in zip(f.points[::3], f.normals[::3]):
                self.assertAlmostEqual(np.linalg.norm(n), 1, places=9)
                # on the bark, just outside it: the limb's radius plus the lift
                self.assertLess(polyline_distance(limb.points, p), limb.radii.max() + .01)
                self.assertGreater(polyline_distance(limb.points, p), limb.radii.min() * .5)
            self.assertTrue((f.spacing > 0).all()); self.assertTrue(0 <= f.k < f.count)

    def test_placed_moves_and_turns(self):
        oak = savanna_oak(4, 5.)
        moved = oak.placed((10, 20, 1.5), np.pi / 2)
        np.testing.assert_allclose(moved.limbs[0].points[0], oak.limbs[0].points[0] @ [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
                                   + [10, 20, 1.5], atol=1e-9)
        self.assertEqual(moved.metadata['placement']['root'], [10., 20., 1.5])
        self.assertIsInstance(moved, Oak)

    def test_rejections(self):
        for kw in (dict(stage='winter'), dict(detail=4), dict(height=.5), dict(spread=20.), dict(seed=1.5)):
            args = dict(seed=1, height=6.)
            args.update(kw)
            with self.assertRaises(ValueError):
                savanna_oak(args.pop('seed'), **args)


def spheres(occluder=True):
    """Three overlapping masses seen side-on, lit from the upper left, and a
    nearer post across them: a CrownRaster built analytically."""
    w, h, k = 360, 260, 60.
    jj, ii = np.meshgrid(np.arange(w), np.arange(h))
    X = (jj - w / 2) / k; Z = -(ii - h / 2) / k
    owner = np.full((h, w), C.SKY); depth = np.full((h, w), np.inf)
    height = np.full((h, w), np.nan); tone = np.zeros((h, w))
    sun = np.array([-.55, -.5, .65]); sun /= np.linalg.norm(sun)
    for idx, ((cx, cz, cy), r) in enumerate([((-.9, 0, 0), 1.), ((1., .25, -.3), .85), ((.1, -.9, .6), .75)]):
        d2 = (X - cx) ** 2 + (Z - cz) ** 2
        yfront = cy - np.sqrt(np.maximum(r * r - d2, 0)); dist = yfront + 10
        better = (d2 < r * r) & (dist < depth)
        n = np.stack([(X - cx) / r, (yfront - cy) / r, (Z - cz) / r], -1)
        owner[better] = idx; depth[better] = dist[better]; height[better] = Z[better]
        tone[better] = np.clip(1 - np.clip(n @ sun, 0, 1), 0, 1)[better]
    post = (np.abs(X - .55) < .08) & (Z < .4)
    if occluder:
        owner[post] = C.OTHER; depth[post] = 5.
    return C.CrownRaster(owner, depth, height, tone, 0., 0., 2., 20.), post


class CrownTests(unittest.TestCase):
    def test_scallop_keeps_ends_and_bulges_to_its_side(self):
        rng = np.random.default_rng(1)
        line = np.array([[0., 0.], [100., 0.]])
        arc = C.scallop(line, 10., .3, (0., -1.), rng)
        np.testing.assert_allclose(arc[0], line[0], atol=1e-9); np.testing.assert_allclose(arc[-1], line[-1], atol=1e-9)
        self.assertTrue((arc[:, 1] <= 1e-9).all()); self.assertLess(arc[:, 1].min(), -2.)
        self.assertTrue((np.diff(arc[:, 0]) > -1e-9).all())

    def test_marks_stay_on_their_masses_and_off_the_post(self):
        r, post = spheres()
        out = C.draw_masses(r, np.random.default_rng(3), dz=.32 / 6)
        self.assertTrue(out['rows'] and out['outlines'])
        pts = np.vstack(out['rows'] + out['outlines']) / r.step
        ij = np.rint(pts).astype(int)
        i, j = np.clip(ij[:, 1], 0, post.shape[0] - 1), np.clip(ij[:, 0], 0, post.shape[1] - 1)
        # Nothing is drawn across the nearer post (a pixel of slack for the pen's rounding).
        from scipy.ndimage import binary_erosion
        self.assertFalse(binary_erosion(post, iterations=1)[i, j].any())
        # Every mark lies on a mass or within a scallop's bulge of one: at most
        # bulge x 1.3 pitches x 1.35, here 0.38 x 1.3 x 1.1 mm x 1.35 = 7.3 raster px.
        from scipy.ndimage import distance_transform_edt
        gap = distance_transform_edt(r.owner < 0)
        self.assertLess(gap[i, j].max(), 7.3 + 1.5)

    def test_shade_draws_more_than_light(self):
        r, _ = spheres(occluder=False)
        out = C.draw_masses(r, np.random.default_rng(4), dz=.32 / 6)
        tone_at = lambda q: r.tone[np.clip(np.rint(q[:, 1] / r.step).astype(int), 0, r.tone.shape[0] - 1),
                                   np.clip(np.rint(q[:, 0] / r.step).astype(int), 0, r.tone.shape[1] - 1)]
        length = {'dark': 0., 'light': 0.}
        for q in out['rows']:
            seg = np.linalg.norm(np.diff(q, axis=0), axis=1); tone = tone_at(q[:-1])
            length['dark'] += seg[tone > .65].sum(); length['light'] += seg[tone < .35].sum()
        mass = r.owner >= 0
        dark, light = (mass & (r.tone > .65)).sum(), (mass & (r.tone < .35)).sum()
        self.assertGreater(length['dark'] / dark, 2 * length['light'] / light)

    def test_outlines_follow_the_silhouettes(self):
        r, _ = spheres(occluder=False)
        out = C.draw_masses(r, np.random.default_rng(5), dz=.32 / 6)
        from scipy.ndimage import distance_transform_edt
        mass = r.owner >= 0
        o = r.owner; edge = np.zeros_like(mass)
        edge[:-1] |= o[:-1] != o[1:]; edge[1:] |= o[1:] != o[:-1]
        edge[:, :-1] |= o[:, :-1] != o[:, 1:]; edge[:, 1:] |= o[:, 1:] != o[:, :-1]
        edge &= mass                    # every mass's own boundary, against sky or another mass
        d = distance_transform_edt(~edge)
        pts = np.vstack(out['outlines']) / r.step
        ij = np.clip(np.rint(pts).astype(int), 0, [mass.shape[1] - 1, mass.shape[0] - 1])
        # within a scallop's height (0.38 x 1.1 mm x 1.35 = 0.56 mm = 5.6 raster px) of an edge
        self.assertLess(np.percentile(d[ij[:, 1], ij[:, 0]], 95), 6.5)

    def test_contact_shadow_darkens_behind_nearer_things(self):
        r, post = spheres()
        tone = C.contact_tone(r, C.Style())
        from scipy.ndimage import binary_dilation
        near = binary_dilation(post, iterations=3) & ~post & (r.owner >= 0)
        self.assertTrue(near.any())
        self.assertTrue((tone[near] >= np.nan_to_num(r.tone)[near] - 1e-12).all())
        self.assertGreater((tone - np.nan_to_num(r.tone))[near].mean(), .1)

    def test_limb_outline_is_tangent_to_the_view(self):
        p = np.array([[0, 0, 0], [0, 0, 2.]]); r = np.array([.3, .2]); eye = np.array([0, -10., 1.])
        left, right = C.limb_outline(p, r, eye)
        for line in (left, right):
            for s in line[::5]:
                c = np.array([0, 0, s[2]]); n = (s - c) / np.linalg.norm(s - c)
                self.assertAlmostEqual(n @ (s - eye), 0, places=9)
        width = np.linalg.norm(left[0] - right[0])
        self.assertAlmostEqual(width, 2 * .3 * np.sqrt(1 - (.3 / 10) ** 2), places=6)

    def test_furrow_keep(self):
        spacing = np.full(5, 1.)
        dark = np.array([0, .25, .5, .75, 1.])
        kept = C.furrow_keep(0, 16, dark, spacing, .085)
        self.assertEqual(kept.tolist(), [False, True, True, True, True])   # rank 0: anything but full light
        self.assertFalse(C.furrow_keep(1, 16, np.full(5, .4), spacing, .085).any())    # rank 0.5
        self.assertFalse(C.furrow_keep(0, 16, np.ones(5), np.zeros(5), .085).any())    # no room on the page


if __name__ == '__main__':
    unittest.main()
