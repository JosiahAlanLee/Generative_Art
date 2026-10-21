"""Caller-supplied terrain and protected-site invariants."""
import unittest
import numpy as np
from lib.process_art.terrain import erode_heightfield


class TerrainTests(unittest.TestCase):
    def setUp(self):
        y,x=np.mgrid[:25,:25]
        self.h=3-.05*y+.4*np.sin(x*.31)+.08*np.random.default_rng(4).normal(size=x.shape)

    def test_zero_steps_preserves_physical_surface_and_input(self):
        before=self.h.copy();s=erode_heightfield(self.h,steps=0)
        np.testing.assert_array_equal(s['height'],before)
        np.testing.assert_array_equal(self.h,before)

    def test_protected_sites_and_edges_do_not_move(self):
        fixed=np.zeros(self.h.shape,bool);fixed[9:15,10:16]=True
        s=erode_heightfield(self.h,steps=12,fixed_mask=fixed)
        np.testing.assert_array_equal(s['height'][s['fixed_mask']],self.h[s['fixed_mask']])
        self.assertGreater(np.max(abs(s['height']-self.h)),.01)
        self.assertGreater(s['incision_history'].sum(),0)

    def test_routing_descends_and_conserves_runoff(self):
        s=erode_heightfield(self.h,steps=10);r=s['receiver'].ravel();a=s['area'].ravel();h=s['routed_height'].ravel()
        ok=r>=0
        self.assertTrue(np.all(h[r[ok]]<h[ok]))
        self.assertAlmostEqual(float(a[~ok].sum()),self.h.size)

    def test_seeded_surface_repeats_and_invalid_mask_fails(self):
        a=erode_heightfield(self.h,steps=4);b=erode_heightfield(self.h,steps=4)
        np.testing.assert_array_equal(a['height'],b['height'])
        with self.assertRaises(ValueError):erode_heightfield(self.h,fixed_mask=np.zeros((8,8)))


if __name__=='__main__':unittest.main()
