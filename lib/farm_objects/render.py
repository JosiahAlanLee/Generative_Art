"""Orthographic specimen engraving with the existing repository BVH ray kernel.

Visibility is sampled at <=0.14 mm on the page. SVGs contain explicit paths,
not paint masks: the same file can be routed to an actual pen plotter.
"""
from pathlib import Path
from collections import defaultdict
import importlib.util
import json
import math
from xml.sax.saxutils import escape
import numpy as np
from .objects import G

_PATH=Path(__file__).resolve().parents[2]/'studies/infernal-landscape/vendor/raycore.py'
# Numba caches the compiled kernel beside its source and records the name of
# the module that compiled it; a later process loading that cache imports the
# module by that name. The Infernal Landscape study imports this file as
# `raycore`, so it is loaded under the same name here: under a second name,
# whichever of the two ran second failed on the other's cache ("No module
# named 'raycore'"). `_farm_raycore`, the name used before, stays as an alias
# so caches written under it still load.
import sys
rc=sys.modules.get('raycore')
if rc is None or Path(getattr(rc,'__file__','') or '').resolve()!=_PATH:
    # Another `raycore` already loaded in this process keeps its name.
    _SPEC=importlib.util.spec_from_file_location('raycore' if rc is None else '_farm_raycore',_PATH)
    rc=importlib.util.module_from_spec(_SPEC)
    sys.modules[_SPEC.name]=rc
    _SPEC.loader.exec_module(rc)
sys.modules.setdefault('_farm_raycore',rc)


def _unit(x):
    x=np.asarray(x,float);return x/np.linalg.norm(x)


def _hatch(p,normal,gap):
    """Clip parallel world-space hatches to one convex planar face."""
    u=_unit(p[1]-p[0]);v=np.cross(normal,u)
    # Rotate the face frame so the surface grain is not an arbitrary image fill.
    a=.56*u+.83*v;a=_unit(a);q=np.cross(normal,a)
    uv=np.c_[(p-p[0])@a,(p-p[0])@q]
    for y in np.arange(uv[:,1].min()+gap*.4,uv[:,1].max(),gap):
        xs=[]
        for A,B in zip(uv,np.roll(uv,-1,axis=0)):
            if (A[1]<=y<B[1]) or (B[1]<=y<A[1]):xs.append(A[0]+(B[0]-A[0])*(y-A[1])/(B[1]-A[1]))
        if len(xs)>=2:
            xs.sort();yield np.array([p[0]+a*xs[0]+q*y,p[0]+a*xs[-1]+q*y])+normal*.002


def render_svg(record,path,width_mm=190,height_mm=140,view=(1.,-1.7,1.0),rust_color='#8b4935',margin_mm=9):
    if not (width_mm>2*margin_mm and height_mm>2*margin_mm):raise ValueError('page must exceed margins')
    V=np.asarray(record['vertices'],float);faces=record['faces'];normals=np.asarray(record['normals'],float)
    view=np.asarray(view,float)
    if view.shape!=(3,) or not np.isfinite(view).all() or np.linalg.norm(view[:2])<1e-8:raise ValueError('view needs a finite nonvertical XYZ direction')
    D=_unit(view);R=_unit(np.cross([0,0,1],D));U=np.cross(D,R)
    # Include detached strokes (teeth, grass, etc.) in framing.
    allp=np.vstack([V]+[np.asarray(s['pts']) for s in record['strokes']])
    xy=np.c_[allp@R,-allp@U];lo=xy.min(0);hi=xy.max(0)
    scale=min((width_mm-2*margin_mm)/(hi[0]-lo[0]),(height_mm-2*margin_mm)/(hi[1]-lo[1]))
    center=(lo+hi)/2;page=np.array([width_mm/2,height_mm/2])
    def project(p):return (np.c_[p@R,-p@U]-center)*scale+page
    tris=[]
    for f in faces:
        for j in range(1,len(f)-1):
            t=V[[f[0],f[j],f[j+1]]]
            if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-10:tris.append(t)
    bvh=rc.build_bvh(np.asarray(tris),np.zeros(len(tris),np.int32))
    candidates=[]
    def add(p,layer,width):
        p=np.asarray(p,float)
        if len(p)>=2:candidates.append((p,layer,width))
    edges=defaultdict(list)
    for i,f in enumerate(faces):
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))].append(i)
    front=normals@D>1e-8
    for (a,b),ids in edges.items():
        silhouette=len(ids)==1 or (np.any(front[ids]) and not np.all(front[ids]))
        crease=(np.any(front[ids]) and len(ids)>1 and normals[ids[0]]@normals[ids[-1]]<.72)
        if silhouette or crease:add(V[[a,b]],'01 structure',.20 if silhouette else .14)
    sun=_unit([-1.,-1.4,2.3])
    for i,f in enumerate(faces):
        if not front[i] or not record['hatch'][i]:continue
        n=normals[i];dark=1-max(0,float(n@sun))
        if dark<.12:continue
        gap=(.52+1.0*(1-dark))/scale
        for p in _hatch(V[f],n,gap):add(p,'02 shade',.10)
    for s in record['strokes']:
        layer='04 rust' if s['ink']==1 else '03 material'
        add(s['pts'],layer,s['width']/G.PX_PER_MM)
    # Batch all rays once. Grouping preserves source polyline discontinuities.
    samples=[];sizes=[]
    for p,layer,width in candidates:
        segments=[]
        for a,b in zip(p[:-1],p[1:]):
            n=max(1,int(np.ceil(np.linalg.norm(project(np.array([a,b]))[1]-project(np.array([a,b]))[0])/.14)))
            segments.append(np.linspace(a,b,n+1)[:-1])
        dense=np.vstack(segments+[p[-1:]])
        sizes.append(len(dense));samples.append(dense)
    P=np.vstack(samples);dirs=np.broadcast_to(D,P.shape).copy()
    _,hit=rc.first_hits(P+dirs*.0015,dirs,1000.,*bvh[:6]);keep=hit<0
    XY=project(P);layers=defaultdict(list);offset=0
    for (_,layer,width),size in zip(candidates,sizes):
        mask=keep[offset:offset+size];xy=XY[offset:offset+size];offset+=size
        ids=np.flatnonzero(mask)
        if not len(ids):continue
        for run in np.split(ids,np.flatnonzero(np.diff(ids)!=1)+1):
            if len(run)<2:continue
            q=xy[run]
            if np.linalg.norm(np.diff(q,axis=0),axis=1).sum()<.24:continue
            # Collapse straight intermediate points, preserving bends and ray cuts.
            if len(q)>2:
                a=q[1:-1]-q[:-2];b=q[2:]-q[1:-1]
                cross=abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])
                q=q[np.r_[True,cross>1e-6,True]]
            layers[layer].append((q,width))
    meta=dict(record.get('metadata',{}),projection='orthographic',view=list(view),units='mm',visibility_sample_mm=.14)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{width_mm}mm" height="{height_mm}mm" viewBox="0 0 {width_mm} {height_mm}">',
         '<title>Farm remnants — procedural object study</title>','<metadata>'+escape(json.dumps(meta,sort_keys=True))+'</metadata>']
    stats={}
    for layer,paths in sorted(layers.items()):
        color=rust_color if layer=='04 rust' else '#24251f'
        svg.append(f'<g id="{layer.replace(" ","-")}" inkscape:groupmode="layer" inkscape:label="{layer}" fill="none" stroke="{color}" stroke-linecap="round" stroke-linejoin="round">')
        for q,width in paths:
            d='M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in q)
            svg.append(f'<path stroke-width="{width:.3f}" d="{d}"/>')
        svg.append('</g>')
        stats[layer]=dict(paths=len(paths),pen_down_m=round(sum(np.linalg.norm(np.diff(q,axis=0),axis=1).sum() for q,_ in paths)/1000,3))
    svg.append('</svg>');path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(svg)+'\n')
    return dict(layers=stats,faces=len(faces),rays=len(P),hidden_samples=int((~keep).sum()),page_mm=[width_mm,height_mm],view=list(view),world_to_mm=scale)
