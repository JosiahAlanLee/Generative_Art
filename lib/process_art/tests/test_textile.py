"""Shared-port, transport, impermeable-wall and dissolution invariants."""
import unittest

import numpy as np
from shapely.geometry import Polygon, LineString

from lib.process_art.drawing import Plate
from lib.process_art.textile import (grammar, graph_veins, flux_laplacian,
                                    compartment_chemistry, dissolve, draw_component)


class TextileTests(unittest.TestCase):
    def test_internal_tile_ports_have_no_open_seams(self):
        g = grammar(17)
        degree = np.bincount(g.edges.ravel(), minlength=len(g.nodes))
        for i, (x, y) in enumerate(g.nodes):
            on_port = abs(x-round(x)) < 1e-6 or abs(y-round(y)) < 1e-6
            if on_port and .001 < x < g.nx-.001 and .001 < y < g.ny-.001:
                self.assertGreaterEqual(degree[i], 2)
        self.assertTrue(np.all(g.length > 0))

    def test_pressure_solve_conserves_interior_flow(self):
        g = grammar(17)
        state = graph_veins(g, steps=15)
        self.assertLess(np.abs(state["kirchhoff_residual"][state["free_nodes"]]).max(), 1e-9)
        self.assertTrue(np.isfinite(state["flow"]).all())
        self.assertTrue(np.isfinite(state["pressure"]).all())
        self.assertEqual(state["pressure"][state["sources"]][0], 0)
        np.testing.assert_allclose(state["kirchhoff_residual"], state["prescribed_injection"], atol=1e-9)
        self.assertGreater(state["kirchhoff_residual"][state["sources"]].sum(), 0)
        self.assertTrue((state["conductance"][state["active_edges"]] > 0).all())

    def test_flux_is_conservative_and_does_not_cross_closed_wall(self):
        rng = np.random.default_rng(7)
        f = rng.random((21, 21))
        p = np.ones_like(f)
        self.assertAlmostEqual(float(flux_laplacian(f, p).sum()), 0)
        p[:, 10] = 0
        f[:] = 0
        f[:, :10] = 1
        self.assertFalse(np.any(flux_laplacian(f, p)))

    def test_chemistry_respects_material(self):
        solid = grammar(17, 3, 4).raster(12)
        a = compartment_chemistry(solid, 7, steps=60)
        b = compartment_chemistry(solid, 7, steps=60)
        np.testing.assert_array_equal(a["v"], b["v"])
        self.assertFalse(np.any(a["v"][solid]))
        self.assertTrue(np.isfinite(a["v"]).all())
        self.assertGreaterEqual(a["v"].min(), 0)

    def test_dissolution_is_irreversible_and_bounded(self):
        solid = grammar(17, 3, 4).raster(16)
        state = dissolve(solid, 7, steps=160)
        self.assertTrue((state["material"] <= state["initial"]).all())
        self.assertGreaterEqual(state["material"].min(), 0)
        self.assertTrue((np.diff(state["loss_history"]) >= 0).all())
        self.assertTrue((state["material"][~solid] == 0).all())
        self.assertGreater(float((state["initial"]-state["material"]).sum()), 0)

    def test_portable_component_clips_geometry(self):
        g = grammar(17, 3, 4)
        p = Plate("small fragment")
        clip = Polygon([(20, 20), (60, 20), (60, 90), (20, 90)])
        draw_component(p, g, box=(10, 10, 80, 120), clip=clip)
        self.assertTrue(p.strokes)
        for s in p.strokes:
            self.assertTrue(clip.buffer(.026).covers(LineString(s.points)))

    def test_seed_changes_whole_motifs_deterministically(self):
        a, b, c = grammar(17), grammar(17), grammar(41)
        for p, q in zip(a.paths, b.paths):
            np.testing.assert_array_equal(p, q)
        self.assertTrue(any(not np.array_equal(p, q) for p, q in zip(a.paths, c.paths)))


if __name__ == "__main__":
    unittest.main()
