import json
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from lib.flora.species import generate, SPECIES, WOODLAND
from lib.flora.foliage import Config, generate_scene
from lib.flora.model import Plant
from lib.flora.render import render, camera

@pytest.mark.parametrize('key',list(WOODLAND))
def test_species(key):
    for stage in SPECIES[key]['stages']:
        a=generate(key,71,stage=stage);b=generate(key,71,stage=stage)
        assert np.array_equal(a.points(),b.points())
        assert np.isfinite(a.points()).all() and np.ptp(a.points(),axis=0).min()>0
        for s in a.surfaces:
            assert len(s.triangles)>0
            q=s.vertices[s.triangles]
            assert (np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)>1e-15).all()
    assert not np.array_equal(generate(key,71).points(),generate(key,72).points())


def test_layers_cache_determinism(tmp_path):
    c=Config(species=('wild_ginger',),count=3,pixels_per_mm=1)
    a,b,hit=generate_scene(c,tmp_path/'a'); assert not hit
    x,y,hit=generate_scene(c,tmp_path/'a'); assert hit
    d,e,_=generate_scene(c,tmp_path/'b')
    assert a.read_bytes()==d.read_bytes() and b.read_bytes()==e.read_bytes()
    groups=[g for g in ET.parse(a).getroot() if g.tag.endswith('g')]
    depths=[float(g.attrib['data-depth']) for g in groups]
    assert depths==sorted(depths) and sum(len(g) for g in groups)>0
    assert len(json.loads(b.read_text())['plants'])==3


def test_occlusion_removes_strokes():
    basis=camera(0,0);p=Plant()
    p.line(np.array([[-1,0,0],[1,0,0]])@basis,'line')
    quad=np.array([[-.5,-.5,1],[.5,-.5,1],[.5,.5,1],[-.5,.5,1]])@basis
    p.surface(quad,[[0,1,2],[0,2,3]],'host','leaf')
    visible=render(p,100,100,azimuth=0,elevation=0,pixels_per_mm=2)
    p.surfaces[0].vertices[:,1]*=-1
    clear=render(p,100,100,azimuth=0,elevation=0,pixels_per_mm=2)
    length=lambda d:sum(np.linalg.norm(np.diff(q,axis=0),axis=1).sum() for _,q in d.paths)
    assert length(visible)<length(clear)*.65


def test_accelerated_depth_buffer_matches_numpy():
    from lib.flora.render import raster_triangle, raster_triangle_numpy
    rng=np.random.default_rng(92)
    a=np.full((32,40),-np.inf);b=a.copy()
    oa=np.full(a.shape,-1,np.int32);ob=oa.copy()
    for i in range(30):
        tri=rng.uniform(-8,45,(3,3))
        raster_triangle(a,oa,tri,i);raster_triangle_numpy(b,ob,tri,i)
    assert np.array_equal(oa,ob)
    assert np.allclose(a,b)
