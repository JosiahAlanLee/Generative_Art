import json
import unittest
import numpy as np
from lib.farm_objects import KINDS,make_object
from lib.farm_objects.objects import G


class FarmTests(unittest.TestCase):
    def test_repeatable_and_varied(self):
        for kind in KINDS:
            a=make_object(kind,22,.6).record();b=make_object(kind,22,.6).record()
            self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))
            self.assertNotEqual(a['vertices'],make_object(kind,23,.6).record()['vertices'])

    def test_finite_faces_and_ground(self):
        for kind in KINDS:
            for d in (0.,.5,1.):
                a=make_object(kind,22,d).record();v=np.asarray(a['vertices'])
                self.assertTrue(np.isfinite(v).all());self.assertGreaterEqual(v[:,2].min(),-.03)
                self.assertEqual(len(a['faces']),len(a['materials']))
                for f in a['faces']:
                    self.assertTrue(all(0<=i<len(v) for i in f))
                    self.assertGreater(G.polygon_area(v[f]),1e-10)

    def test_barn_decay_preserves_dimensions_and_removes_boards(self):
        assets=[make_object('barn',22,d) for d in (0,.3,.6,1)]
        for key in ('width','length','height','roof'):
            self.assertEqual(len({a.parameters[key] for a in assets}),1)
        for key in ('missing_boards','missing_roof_sheets'):
            counts=[a.parameters[key] for a in assets]
            self.assertEqual(counts,sorted(counts));self.assertGreater(counts[-1],counts[0])

    def test_all_families_decay_preserves_shape_parameters(self):
        for kind in KINDS:
            p=make_object(kind,22,0).parameters;q=make_object(kind,22,1).parameters
            for key in p:
                if not key.startswith('missing') and key!='max_sag':self.assertEqual(p[key],q[key])

    def test_transform_preserves_stroke_attachments(self):
        a=make_object('tractor',4,.8);target=G.SceneBuilder({'seed':4},lambda x,y:0.)
        a.add_to(target,(5,7,2),np.pi/2,2)
        p=np.asarray(a.builder.objects[0]['verts']);q=np.asarray(target.objects[0]['verts'])
        np.testing.assert_allclose(q,np.c_[-p[:,1]*2+5,p[:,0]*2+7,p[:,2]*2+2],atol=1e-12)
        p=np.asarray(a.builder.strokes[0]['pts']);q=np.asarray(target.strokes[0]['pts'])
        np.testing.assert_allclose(q,np.c_[-p[:,1]*2+5,p[:,0]*2+7,p[:,2]*2+2],atol=1e-12)

    def test_invalid_controls(self):
        for d in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError):make_object(decay=d)
        with self.assertRaises(ValueError):make_object('combine')
        with self.assertRaises(ValueError):make_object(seed=-1)
        with self.assertRaises(ValueError):make_object(seed=1.2)

if __name__=='__main__':unittest.main()
