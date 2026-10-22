"""The plate studies' scene-time farmstead and their render-time helpers.

Everything here runs without a built scene: the farmstead goes into a NumPy
SceneBuilder over flat ground, the flora drawings come from lib/flora, and
the seal is evaluated as a field. Run from the repository root:
    python -m unittest discover -s studies/infernal-landscape/tests -v
"""
import sys
import unittest
from pathlib import Path

import numpy as np

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY)); sys.path.insert(0, str(STUDY.parents[1]))
import geometry as G  # noqa: E402
import plates  # noqa: E402
from lib.farm_objects import make_object  # noqa: E402


def barn_spec():
    return next(s for s in plates.FARM if s['kind'] == 'barn')


class QuiltPlacementTests(unittest.TestCase):
    def setUp(self):
        spec = barn_spec()
        self.record = make_object('barn', seed=spec['seed'], decay=spec['decay']).record()
        self.fit = plates.front_quilt(self.record)

    def test_board_fits_the_front_wall_clear_of_door_and_rail(self):
        f = self.fit
        self.assertIsNotNone(f)
        self.assertIn(f['size'], plates.QUILT_SIZES)
        half = f['size'] / 2
        V = np.asarray(self.record['vertices'])
        front = [V[q] for q, n in zip(self.record['faces'], self.record['names'])
                 if n.split('.')[0] == 'end board' and V[q][:, 1].max() < f['front_y'] + .2]
        wall_left = min(p[:, 0].min() for p in front)
        if f['place'] == 'gable':
            self.assertGreaterEqual(f['bottom_z'], f['eave'] + .5)
        else:
            self.assertGreaterEqual(f['centre_x'] - half, wall_left)
            self.assertLessEqual(f['centre_x'] + half, -plates.DOOR_JAMB)
            self.assertLessEqual(f['bottom_z'] + f['size'], plates.DOOR_RAIL)
            self.assertGreaterEqual(f['bottom_z'], .45)

    def test_this_barns_loft_leaves_too_little_gable(self):
        # Seed 22's loft opening reaches within 0.92 m of its gable roof line,
        # so the board goes beside the door (PLATES.md records the choice).
        self.assertEqual(self.fit['place'], 'wall left of the door')
        self.assertEqual(self.fit['size'], .92)


class FarmsteadTests(unittest.TestCase):
    def setUp(self):
        self.T = G.SceneBuilder(dict(seed=7), lambda x, y: .2 + 0 * np.asarray(x, float))
        self.footprints, self.record = plates.add_farmstead(self.T)

    def test_objects_board_and_footprints(self):
        names = {o['name'].split('/')[0] for o in self.T.objects}
        self.assertTrue({'Farm barn', 'Farm tractor', 'Farm hay rake', 'Barn quilt board'} <= names)
        self.assertEqual(len(self.footprints), len(plates.FARM))
        for spec, (x0, y0, x1, y1) in zip(plates.FARM, self.footprints):
            self.assertTrue(x0 < spec['at'][0] < x1 and y0 < spec['at'][1] < y1, spec['kind'])

    def test_board_hangs_in_front_of_the_siding(self):
        board = next(o for o in self.T.objects if o['name'] == 'Barn quilt board')
        siding = [o for o in self.T.objects if o['name'].startswith('Farm barn/end board')]
        front_y = min(o['verts'][:, 1].min() for o in siding)
        self.assertLess(board['verts'][:, 1].max(), front_y - .05)
        lo, hi = board['verts'].min(0), board['verts'].max(0)
        self.assertAlmostEqual(hi[0] - lo[0], self.record['objects'][0]['quilt_board']['size'], places=6)

    def test_bases_sit_into_the_ground(self):
        for entry in self.record['objects']:
            self.assertAlmostEqual(entry['z'], .2 - plates.SINK, places=6)


class FloraTests(unittest.TestCase):
    def test_zone_points_respect_zone_footprints_track_and_spacing(self):
        zone = plates.ZONES[0]
        footprints = [[15., 5., 18., 12.]]
        pts, dist = plates.zone_points(zone, footprints, np.random.default_rng(3))
        again, _ = plates.zone_points(zone, footprints, np.random.default_rng(3))
        np.testing.assert_array_equal(pts, again)
        self.assertGreater(len(pts), 50)
        from lib.face_patterns import inside
        self.assertTrue(inside(pts, zone['polygon']).all())
        self.assertFalse(((pts[:, 0] > 15) & (pts[:, 0] < 18) & (pts[:, 1] > 5) & (pts[:, 1] < 12)).any())
        track = np.array([plates._segment_distance(p, zone['track']) for p in pts])
        self.assertTrue((track >= zone['track_half_width']).all())
        d = np.linalg.norm(pts[:, None] - pts[None], axis=2) + np.eye(len(pts)) * 9
        self.assertGreaterEqual(d.min(), zone['r'][0] - 1e-9)
        # Denser near the edges than in the open yard.
        near, far = dist < .8, dist > 1.6
        self.assertTrue(near.any() and far.any())

    def test_patch_root_and_scale_are_plate_millimetres(self):
        from lib.flora.model import Plant
        # A leaning stem: lib/flora needs a drawing wider than its margins.
        plant = Plant({}); plant.line([(0, 0, 0), (.05, 0, .5), (.1, 0, 1.)], role='stem')
        scale, elevation = 12., 30.
        patch = plates._patch(plant, 0., elevation, scale, 0)
        pts = np.asarray(patch['strokes'][0]['pts']).reshape(-1, 2)
        ox, oy = patch['origin']
        bottom, top = pts[np.argmax(pts[:, 1])], pts[np.argmin(pts[:, 1])]
        np.testing.assert_allclose(bottom, (ox, oy), atol=.05)
        np.testing.assert_allclose(top, (ox + .1 * scale, oy - scale * np.cos(np.radians(elevation))), atol=.05)
        self.assertEqual(patch['mm_per_metre'], scale)

    def test_thinning_keeps_every_other_seed_and_all_leaves(self):
        from lib.flora.model import Plant
        plant = Plant({})
        for k in range(10):
            plant.line([(k, 0, 0), (k, 0, 1)], role='seed')
        plant.line([(0, 1, 0), (0, 1, 1)], role='leaf')
        thin = plates._thinned(plant, 2)
        self.assertEqual(sum(s.role == 'seed' for s in thin.strokes), 5)
        self.assertEqual(sum(s.role == 'leaf' for s in thin.strokes), 1)
        self.assertEqual(len(plant.strokes), 11)        # the original is untouched


class HatchDomainTests(unittest.TestCase):
    """Where the plates build hatches the terrain (render.engrave)."""

    class Atlas:      # build.Terrain's bounds and rectangle domain, without a scene
        u0, u1, v0, v1 = -20., 20., -11., 35.

        def domain(self, u, v):
            return (u >= self.u0) & (u <= self.u1) & (v >= self.v0) & (v <= self.v1)

    def test_main_view_atlas_takes_in_the_farmyard_and_nothing_else(self):
        t = self.Atlas(); record = plates.yard_atlas(t)
        self.assertEqual(record['atlas'], [-20., 20., -11., 35.])
        self.assertEqual(t.u1, plates.YARD[2])
        u, v = np.array([0., 22., 22., 22., 21.]), np.array([30., 0., 10., -8., 5.])
        np.testing.assert_array_equal(t.domain(u, v), [True, True, False, False, True])

    def test_every_farmyard_plant_and_the_farmstead_stand_on_hatched_ground(self):
        t = self.Atlas(); plates.yard_atlas(t)
        T = G.SceneBuilder(dict(seed=7), lambda x, y: .2 + 0 * np.asarray(x, float))
        footprints, _ = plates.add_farmstead(T)
        zone = next(z for z in plates.ZONES if z['name'] == 'farmyard')
        pts, _ = plates.zone_points(zone, footprints, np.random.default_rng([plates.FLORA_SEED, 0]))
        self.assertTrue(t.domain(pts[:, 0], pts[:, 1]).all())
        for x0, y0, x1, y1 in footprints:      # with their .4 m margins
            corners = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
            self.assertTrue(t.domain(corners[:, 0], corners[:, 1]).all())

    def test_close_views_hatch_what_they_see_inside_the_mesh(self):
        from types import SimpleNamespace
        B = SimpleNamespace(TBVH=(np.array([[-30., -20., -1.]]), np.array([[30., 44., 5.]])), terrain=self.Atlas())
        seen, saved = (4., -25., 31., 29.), plates.visible_ground
        plates.visible_ground = lambda B: seen
        try:
            mesh = plates.close_atlas(B)
        finally:
            plates.visible_ground = saved
        np.testing.assert_allclose(mesh, (-29.9, -19.9, 29.9, 43.9))
        t = B.terrain
        np.testing.assert_allclose((t.u0, t.v0, t.u1, t.v1), (4., -19.9, 29.9, 29.))

    def test_edge_fade_eases_from_the_mesh_edge(self):
        mesh, w = (-29.9, -19.9, 29.9, 43.9), plates.EDGE_FADE
        x = np.array([29.9, 29.9 - w / 2, 29.9 - w, 0.])
        f = plates.edge_fade(np.c_[x, np.full(4, 10.)], mesh)
        np.testing.assert_allclose(f, [0., .5, 1., 1.], atol=1e-12)
        g = plates.edge_fade(np.c_[np.linspace(0, 29.9, 300), np.full(300, 10.)], mesh)
        self.assertTrue((np.diff(g) <= 1e-12).all())


class SealTests(unittest.TestCase):
    def test_seal_core_ring_slot_and_ninefold_symmetry(self):
        c, R = np.array([2., 3.]), .36
        f = plates.seal_shape(c, R)
        self.assertLess(f((c + (0, .08))[None])[0], 0)       # the core disc, beside its slot
        self.assertGreater(f(c[None])[0], 0)                  # the stepped bar cuts through the centre
        self.assertLess(f((c + (0, R))[None])[0], 0)          # on the ring band
        far = c + np.array([[R + .1, 0], [0, -(R + .1)]])
        self.assertTrue((f(far) > 0).all())
        a = np.radians(np.arange(0, 360, 7.5)); r = R * .64
        ring = c + r * np.column_stack([np.cos(a), np.sin(a)])
        turned = c + r * np.column_stack([np.cos(a + np.radians(40)), np.sin(a + np.radians(40))])
        np.testing.assert_allclose(f(ring), f(turned), atol=1e-9)


if __name__ == '__main__':
    unittest.main()
