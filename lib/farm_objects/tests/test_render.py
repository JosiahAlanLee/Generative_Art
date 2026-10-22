import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from lib.farm_objects.objects import G
from lib.farm_objects.render import render_svg


class VisibilityTests(unittest.TestCase):
    def test_hidden_stroke_does_not_reach_plot(self):
        b=G.SceneBuilder({'seed':1},lambda x,y:0.)
        b.box('block',(-1,-.3,-1),(1,.3,1),1)
        # Seen from Y negative: a rear red line is wholly hidden, the front
        # black line survives. This tests pen paths, not SVG paint-over masks.
        b.ink('behind',[(-.6,.7,0),(.6,.7,0)],.15,1)
        b.ink('in front',[(-.6,-.7,0),(.6,-.7,0)],.15,0)
        rec=dict(b.evaluate(),strokes=b.strokes)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'proof.svg';result=render_svg(rec,path,view=(0,-1,0))
            self.assertNotIn('04 rust',result['layers']);self.assertIn('03 material',result['layers'])
            root=ET.parse(path).getroot()
            self.assertFalse(any(e.tag.split('}')[-1] in ('image','mask','clipPath','text','rect') for e in root.iter()))
            self.assertTrue(all(e.attrib.get('fill')=='none' for e in root if e.tag.endswith('}g')))

    def test_reject_vertical_camera(self):
        b=G.SceneBuilder({'seed':1},lambda x,y:0.);b.box('block',(0,0,0),(1,1,1))
        with self.assertRaises(ValueError):render_svg(dict(b.evaluate(),strokes=[]),'unused.svg',view=(0,0,1))

if __name__=='__main__':unittest.main()
