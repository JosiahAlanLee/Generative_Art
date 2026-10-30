"""Seeded scene assembly, shared surface visibility, layered plotter SVG and cache.

Run: python -m lib.flora.foliage --layout band --count 12 --output samples
Depth layers are plant anchor bins; individual organs retain true geometric depth.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import numpy as np
from .species import generate, SPECIES
from .model import Plant, Stroke
from .render import render, camera

VERSION = 'foliage-2'
@dataclass(frozen=True)
class Config:
    species: tuple = ('maidenhair', 'wild_ginger', 'bloodroot', 'dutchmans_breeches', 'solomons_seal')
    seed: int = 101
    count: int = 12
    layout: str = 'band'
    width: float = 240
    height: float = 135
    azimuth: float = 0
    elevation: float = 8
    layers: int = 3
    pixels_per_mm: float = 3
    detail: int = 1

    def validate(self):
        if self.layout not in ('band','clump','border','field','specimen'):
            raise ValueError('unknown layout')
        if not self.species or any(k not in SPECIES for k in self.species):
            raise ValueError('unknown/empty species mix')
        if not 1 <= self.count <= 200 or not 1 <= self.layers <= 8:
            raise ValueError('count 1..200, layers 1..8')
        if not all(np.isfinite(v) for v in (self.width,self.height,self.azimuth,self.elevation,self.pixels_per_mm)):
            raise ValueError('finite camera and size required')
        if min(self.width,self.height) <= 16 or not .5 <= self.pixels_per_mm <= 12:
            raise ValueError('size >16mm; pixels_per_mm .5..12')
        if self.detail not in (0,1,2): raise ValueError('detail 0..2')


def assemble(c):
    c.validate()
    rng = np.random.default_rng(c.seed)
    basis = camera(c.azimuth,c.elevation)
    scene = Plant({'generator':VERSION})
    records=[]
    n=1 if c.layout=='specimen' else c.count
    for i in range(n):
        key=c.species[i%len(c.species)]; seed=int(rng.integers(0,2**31))
        p=generate(key,seed)
        # Work in camera coordinates to preserve composition at every azimuth.
        projected=p.points()@basis.T
        h=max(np.ptp(projected[:,1]),.01)
        scale=rng.uniform(.36,.58)/h
        if c.layout=='band': x=(i+.5)/n*3.4-1.7; y=.45
        elif c.layout=='clump': x=rng.normal(0,.32); y=rng.normal(.3,.06)
        elif c.layout=='field': x=rng.uniform(-1.6,1.6); y=rng.uniform(-.5,.5)
        elif c.layout=='border':
            edge=i%4;t=(i//4+.5)/max(1,np.ceil(n/4))
            x,y=((-1.6+3.2*t,.62),(-1.6+3.2*t,-.62),(-1.6,-.6+1.2*t),(1.6,-.6+1.2*t))[edge]
        else: x=0;y=.4
        depth=int(rng.integers(c.layers)); z=(depth-(c.layers-1)/2)*.5
        # Ground the lowest projected point at the layout anchor.
        qoff=np.array([x,y-projected[:,1].max()*scale,z])
        p=p.transform(lambda v: (v@basis.T*scale+qoff)@basis)
        offset=len(scene.surfaces)
        scene.surfaces.extend(p.surfaces)
        for s in p.strokes:
            scene.strokes.append(Stroke(s.points,f'layer-{depth}',s.detail,s.owner+offset if s.owner>=0 else -1))
        for surface in p.surfaces: surface.role=f'layer-{depth}'
        records.append(dict(id=f'plant-{i}',species=key,seed=seed,layer=depth,depth=z,
            bounds=[p.points().min(0).tolist(),p.points().max(0).tolist()]))
    return scene,records


def generate_scene(c, output):
    c.validate()
    parameters=json.loads(json.dumps(asdict(c)))
    digest=hashlib.sha256(json.dumps(dict(version=VERSION,parameters=parameters),sort_keys=True).encode()).hexdigest()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    svg=output/(digest+'.svg'); side=svg.with_suffix('.json')
    if svg.exists() and side.exists(): return svg,side,True
    scene,plants=assemble(c)
    drawing=render(scene,c.width,c.height,azimuth=c.azimuth,elevation=c.elevation,
        pixels_per_mm=c.pixels_per_mm,detail=c.detail,margin=8)
    if c.layout == 'band' and drawing.paths:
        bottom=max(q[:,1].max() for _,q in drawing.paths)
        drawing.paths=[(role,q+np.array([0,c.height-8-bottom])) for role,q in drawing.paths]
    root=ET.fromstring(drawing.svg())
    layers=[]
    for group in list(root):
        if not group.tag.endswith('g'): continue
        j=int(group.attrib['id'].split('-')[-1]); depth=(j-(c.layers-1)/2)*.5
        group.set('data-depth',str(depth));group.set('stroke-width',str(round(.12+.05*j,3)))
        group.set('opacity',str(round(.55+.45*(j+1)/c.layers,3)))
        layers.append(dict(id=group.attrib['id'],depth=depth,plants=[p['id'] for p in plants if p['layer']==j],paths=len(group)))
    bounds=np.concatenate([p for _,p in drawing.paths]) if drawing.paths else np.zeros((1,2))
    metadata=dict(hash=digest,version=VERSION,parameters=parameters,layers=layers,plants=plants,
        bounds=[bounds.min(0).tolist(),bounds.max(0).tolist()],plot=drawing.stats(),
        visibility='shared sampled surface depth; surviving strokes only')
    svg.write_text(ET.tostring(root,encoding='unicode'))
    side.write_text(json.dumps(metadata,sort_keys=True,indent=2)+'\n')
    return svg,side,False


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--layout',default='band');ap.add_argument('--count',type=int,default=12)
    ap.add_argument('--seed',type=int,default=101);ap.add_argument('--species',default=','.join(Config.species))
    ap.add_argument('--azimuth',type=float,default=0);ap.add_argument('--elevation',type=float,default=8)
    ap.add_argument('--width',type=float,default=240);ap.add_argument('--height',type=float,default=135)
    ap.add_argument('--output',required=True)
    a=ap.parse_args();args=vars(a);out=args.pop('output');args['species']=tuple(args['species'].split(','))
    svg,side,cached=generate_scene(Config(**args),out)
    print(json.dumps(dict(svg=str(svg),json=str(side),cached=cached)))
if __name__=='__main__':main()
