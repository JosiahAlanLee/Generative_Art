"""Behavioral contracts: repeatable variation, hidden strokes, portable geometry."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
from lib.flora import SPECIES, Plant, generate
from lib.flora.render import render
from lib.flora.adapters import add_to_scene_builder


class FloraTests(unittest.TestCase):
    def test_repeatability_and_structural_variation(self):
        for species in SPECIES:
            a=generate(species, 7); b=generate(species, 7); c=generate(species, 31)
            self.assertEqual(a.as_dict(), b.as_dict(), species)
            # Counts/organ placement change, not a re-used mesh transformed in space.
            self.assertNotEqual(a.organs, c.organs, species)
            for s in a.surfaces:
                self.assertTrue(np.isfinite(s.vertices).all())
                self.assertGreaterEqual(s.triangles.min(), 0)
                self.assertLess(s.triangles.max(), len(s.vertices))
                q=s.vertices[s.triangles]
                self.assertTrue((np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)>0).all())

    def test_species_stages_change_organs(self):
        bloom=generate('prairie_smoke', 3, stage='flowering')
        fruit=generate('prairie_smoke', 3, stage='seed')
        self.assertTrue(any(o['type']=='nodding_flower' for o in bloom.organs))
        self.assertFalse(any(o['type']=='upright_plumes' for o in bloom.organs))
        self.assertTrue(any(o['type']=='upright_plumes' for o in fruit.organs))
        self.assertFalse(any(o['type']=='leaf' for o in generate('bur_oak',3,stage='bare').organs))

    def test_stage_and_parameter_rejection(self):
        for kw in ({'stage':'winter'}, {'vigor':0}, {'wind':float('nan')}):
            with self.assertRaises(ValueError):
                generate('prairie_smoke', **kw)

    def test_wind_keeps_root_and_topology(self):
        a=generate('wild_bergamot',12); b=generate('wild_bergamot',12,wind=.8)
        self.assertEqual(len(a.surfaces), len(b.surfaces))
        aa=a.points(); bb=b.points()
        self.assertTrue(np.allclose(aa[:,2],bb[:,2]))
        roots=np.isclose(aa[:,2],0)
        self.assertTrue(np.allclose(aa[roots],bb[roots]))
        self.assertFalse(np.allclose(aa,bb))

    def test_true_three_dimensional_rotation(self):
        p=generate('prairie_smoke',1)
        self.assertGreater(np.ptp(p.points()[:,1]), .1)
        a=render(p,60,80,azimuth=0,pixels_per_mm=3,detail=0)
        b=render(p,60,80,azimuth=75,pixels_per_mm=3,detail=0)
        self.assertNotEqual(a.svg(),b.svg())

    def test_occluder_splits_stroke_without_cover_shapes(self):
        p=Plant()
        p.surface([[-.3,-1,0],[.3,-1,0],[.3,-1,1],[-.3,-1,1]],
                  [[0,1,2],[0,2,3]],'leaf','test')
        p.line([[-1,0,.5],[1,0,.5]])
        d=render(p,100,80,azimuth=0,elevation=0,pixels_per_mm=6)
        self.assertEqual(len(d.paths),2)
        for _, q in d.paths:
            self.assertTrue((q[:,0]<49).all() or (q[:,0]>51).all())
        root=ET.fromstring(d.svg())
        self.assertFalse(any(e.tag.rsplit('}',1)[-1] in ('image','rect','mask','clipPath','text') for e in root.iter()))

    def test_foreground_stroke_survives(self):
        p=Plant()
        p.surface([[-1,0,0],[1,0,0],[1,0,1],[-1,0,1]],[[0,1,2],[0,2,3]],'leaf','test')
        p.line([[-.5,-1,.5],[.5,-1,.5]])
        d=render(p,100,80,azimuth=0,elevation=0,pixels_per_mm=4)
        self.assertEqual(len(d.paths),1)

    def test_existing_scene_builder_adapter(self):
        root=Path(__file__).resolve().parents[3]
        spec=importlib.util.spec_from_file_location('flora_test_geometry', root/'studies/infernal-landscape/geometry.py')
        g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
        builder=g.SceneBuilder({},lambda x,y: 0)
        p=Plant(); p.leaf([0,0,0],[1,0,1],.2,.1)
        records=add_to_scene_builder(p,builder)
        self.assertEqual(len(records),len(p.surfaces))
        self.assertEqual(len(builder.strokes),2)
        self.assertTrue(all(not r['hatch'] for r in records))

    def test_portable_model_round_trip(self):
        p=Plant(); p.leaf([0,0,0],[1,1,1],.2,.06)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'plant.json'; p.save(path); data=json.loads(path.read_text())
            self.assertEqual(data['units'],'metres')
            self.assertEqual(data['surfaces'][0]['triangles'],p.surfaces[0].triangles.tolist())
            obj=Path(td)/'plant.obj'; p.obj(obj)
            self.assertEqual(sum(line.startswith('f ') for line in obj.read_text().splitlines()),len(p.surfaces[0].triangles))


if __name__=='__main__':
    unittest.main()
