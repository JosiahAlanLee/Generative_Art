"""True 3D scene -> shared ray visibility -> Claude hatching + Driftless strokes.
Run with the supplied Python requirements; Node is used for the Driftless patches.
"""
from pathlib import Path
from types import SimpleNamespace
import sys,math,json,time,hashlib,subprocess,argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from scipy.ndimage import gaussian_filter,map_coordinates
from scipy.interpolate import RegularGridInterpolator
from numba import njit,prange
import contourpy
import os
ROOT=Path(__file__).resolve().parent
CASE=os.environ.get('INFERNAL_CASE','recorded_route')
TERRAIN_MODE=os.environ.get('INFERNAL_TERRAIN','original')
from scene import output_dir
OUT=output_dir(CASE,TERRAIN_MODE)
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'vendor'))
import raycore as rc
import claude_hatching as CH
W,H=3120,2340
D=json.loads((OUT/'scene.json').read_text())
V=np.asarray(D['vertices']);FACES=[dict(p=V[f],mat=m,hatch=h,name=n) for f,m,h,n in zip(D['faces'],D['materials'],D['hatch'],D['names'])]
LINES=[(np.asarray(s['pts']),s['width'],s['ink']) for s in D['strokes']]
COLORS=D['colors']
def unit(x):
 x=np.asarray(x,float);return x/max(1e-12,np.linalg.norm(x))
# BVH from the same polygons used for the exported model.
TRIS=[];MATS=[];OWNER=[]
for i,f in enumerate(FACES):
 for j in range(1,len(f['p'])-1):
  t=f['p'][[0,j,j+1]]
  if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-9:
   TRIS.append(t);MATS.append(f['mat']);OWNER.append(i)
TRIS=np.array(TRIS);MATS=np.array(MATS)
print('Model:',len(FACES),'faces,',len(TRIS),'triangles',flush=True)
BVH=rc.build_bvh(TRIS,MATS)
import os
VIEW_NAME=os.environ.get('TERRAIN_VIEW','main')
CAM=D['cameras'][VIEW_NAME]
EYE=np.asarray(CAM['eye']);TARGET=np.asarray(CAM['target'])
FWD=unit(TARGET-EYE);VIEW=-FWD;RIGHT=unit(np.cross(FWD,[0,0,1]));UP=np.cross(RIGHT,FWD)
FOCAL=CAM['focal_px'];CX,CY=CAM['principal_point'];NEAR=.25
SCALE=FOCAL/np.linalg.norm(TARGET-EYE)  # target-plane scale, for stroke sampling only
def project(P):
 P=np.asarray(P);q=P-EYE;z=q@FWD;safe=np.maximum(z,NEAR)
 return CX+FOCAL*(q@RIGHT)/safe,CY-FOCAL*(q@UP)/safe,z
def jac(P,u,v):
 P=np.asarray(P);q=P-EYE;z=np.maximum(q@FWD,NEAR);x=q@RIGHT;y=q@UP
 shape=P.shape[:-1];a=np.empty((*shape,2,2))
 a[...,0,0]=FOCAL*((u@RIGHT)*z-x*(u@FWD))/z**2
 a[...,0,1]=FOCAL*((v@RIGHT)*z-x*(v@FWD))/z**2
 a[...,1,0]=-FOCAL*((u@UP)*z-y*(u@FWD))/z**2
 a[...,1,1]=-FOCAL*((v@UP)*z-y*(v@FWD))/z**2
 return a
def primary_rays(xy):
 xy=np.asarray(xy,float).reshape(-1,2)
 dirs=FWD+((xy[:,0]-CX)/FOCAL)[:,None]*RIGHT-((xy[:,1]-CY)/FOCAL)[:,None]*UP
 dirs/=np.linalg.norm(dirs,axis=1)[:,None]
 return np.broadcast_to(EYE,dirs.shape).copy(),dirs
def pixels_per_world(P):
 return FOCAL/np.maximum((np.asarray(P)-EYE)@FWD,NEAR)
# A terrain-only BVH is the host for all downward projections. Architecture
# belongs to the visibility BVH, never to the host. This avoids drawing field
# marks onto a roof when a barn happens to cover their coordinates.
TERRAIN_IDS=np.asarray(np.flatnonzero(np.isin(OWNER,D['terrain_faces'])))
TBVH=rc.build_bvh(TRIS[TERRAIN_IDS],np.zeros(len(TERRAIN_IDS),np.int32))
def drape(xy,lift=.006):
 xy=np.asarray(xy,float).reshape(-1,2)
 origins=np.column_stack([xy,np.full(len(xy),45.)]);dirs=np.tile([0.,0.,-1.],(len(xy),1))
 distance,hit=rc.first_hits(origins,dirs,100.,*TBVH[:6])
 ok=hit>=0;P=origins+dirs*distance[:,None]
 P[ok]+=TBVH[7][hit[ok]]*lift
 P[~ok]=np.nan
 return P,ok,hit
def height(x,y):
 x,y=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float));shape=x.shape
 return drape(np.column_stack([x.ravel(),y.ravel()]),0)[0][:,2].reshape(shape)
class Terrain:
 u0,u1,v0,v1=-20.,20.,-11.,35.
 def world(self,u,v):return drape(np.column_stack([u,v]),0)[0]
 def frame(self,u,v):
  p,ok,hit=drape(np.column_stack([u,v]),0);n=TBVH[7][hit];nz=np.maximum(n[:,2],1e-8)
  return np.column_stack([np.ones(len(n)),np.zeros(len(n)),-n[:,0]/nz]),np.column_stack([np.zeros(len(n)),np.ones(len(n)),-n[:,1]/nz])
 def normal(self,u,v):return TBVH[7][drape(np.column_stack([u,v]),0)[2]]
 def domain(self,u,v):return (u>=self.u0)&(u<=self.u1)&(v>=self.v0)&(v<=self.v1)
terrain=Terrain()
CH.S=SimpleNamespace(EYE=EYE,project=project,screen_jacobian=jac,SURFACES=[terrain])
CH.FAMILIES=((.65,.064,1.0),(-.68,.082,.85))
CH.BITS=8;CH.BITREV=np.array([int(f'{i:08b}'[::-1],2) for i in range(256)])/256
CH.C_MAX=.39;CH.GAMMA=1.45;CH.C_SPLIT=.14;CH.MIN_GAP=2.35;CH.BREAK_KEEP=.795;CH.GRID=5
LIGHT=unit([-10,-8,9])

@njit(cache=True,parallel=True)
def visible_kernel(P,eye,blo,bhi,nodes,v0,e1,e2):
 out=np.zeros(len(P),np.bool_)
 for i in prange(len(P)):
  view=eye-P[i];distance=np.linalg.norm(view);view/=max(distance,1e-9)
  o=P[i]+view*.006
  _,hit=rc.trace(o,view,1e-5,max(1e-4,distance-.012),True,blo,bhi,nodes,v0,e1,e2);out[i]=hit<0
 return out
@njit(cache=True,parallel=True)
def light_kernel(P,N,eye,sun,right,blo,bhi,nodes,v0,e1,e2):
 out=np.zeros(len(P))
 for i in prange(len(P)):
  n=N[i].copy()
  if np.dot(n,eye-P[i])<0:n=-n
  cos=max(0.,np.dot(n,sun))
  _,hit=rc.trace(P[i]+n*.012,sun,1e-5,100.,True,blo,bhi,nodes,v0,e1,e2)
  direct=cos*(1. if hit<0 else .06)
  # Two short contact rays; directional sun is common to clay and ink.
  ao=0.
  for s in [-1.,1.]:
   d=n+s*.55*right;d=d/np.linalg.norm(d)
   t,h=rc.trace(P[i]+n*.015,d,1e-5,1.4,False,blo,bhi,nodes,v0,e1,e2)
   if h>=0:ao+=.5*(1.-t/1.4)
  out[i]=min(1.,max(.08,.28*(1-.65*ao)+.85*direct))
 return out

def visible(P,*bvh):return visible_kernel(P,EYE,*bvh)
def light(P,N,*bvh):return light_kernel(P,N,EYE,LIGHT,RIGHT,*bvh)

def split_paths(xy,keep,sid=None):
 ids=np.flatnonzero(keep)
 if not len(ids):return []
 br=(np.diff(ids)!=1)
 if sid is not None:br|=np.diff(sid[ids])!=0
 return [q for g in np.split(ids,np.flatnonzero(br)+1) if len(g)>1 for q in [xy[g]] if np.linalg.norm(np.diff(q,axis=0),axis=1).sum()>1.5]

def stroke_project(P,return_world=False):
 """Visible screen paths of a 3D polyline; with return_world, also the kept world samples."""
 P=np.asarray(P,float);parts=[]
 for a,b in zip(P[:-1],P[1:]):
  # Clip before resampling, so points behind the perspective camera cannot create huge paths.
  za,zb=(a-EYE)@FWD,(b-EYE)@FWD
  if max(za,zb)<=NEAR:continue
  if za<NEAR:a=a+(b-a)*(NEAR-za)/(zb-za)
  if zb<NEAR:b=b+(a-b)*(NEAR-zb)/(max(za,NEAR)-zb)
  pa=project(np.vstack([a,b]));length=np.hypot(np.diff(pa[0])[0],np.diff(pa[1])[0])
  if length>20000:continue
  n=max(2,int(length/1.2)+1);parts.extend(np.linspace(a,b,n)[:-1])
 if not parts:return ([],np.zeros((0,3))) if return_world else []
 parts.append(P[-1]);p=np.asarray(parts);x,y,z=project(p)
 keep=visible(p,*BVH[:6]);keep&=(z>NEAR)&(x>4)&(x<W-4)&(y>4)&(y<H-4)
 paths=split_paths(np.column_stack([x,y]),keep)
 return (paths,p[keep]) if return_world else paths

def svg_write(name,groups):
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="156mm" height="{156*H/W:.3f}mm" viewBox="0 0 {W} {H}">',
    '<title>Infernal Engine - architecture from the reachability specimen</title>']
 for label,paths,col in groups:
  s.append(f'<g inkscape:groupmode="layer" inkscape:label="{label}" fill="none" stroke="{col}" stroke-linecap="round" stroke-linejoin="round">')
  for P,width in paths:
   d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in P);s.append(f'<path stroke-width="{width:.3f}" d="{d}"/>')
  s.append('</g>')
 s.append('</svg>');(OUT/f'{name}.svg').write_text('\n'.join(s))
 import cairosvg
 cairosvg.svg2png(bytestring='\n'.join(s).encode(),write_to=str(OUT/f'{name}.png'),output_width=W,background_color='#ede6d4')
