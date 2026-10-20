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
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'vendor'))
import raycore as rc
import claude_hatching as CH
W,H=2100,1575
FACES=[];LINES=[]
COLORS=['#b6ad95','#c5b99d','#3c4741','#8f352a','#7a776b','#8b9a94']
def unit(x):
 x=np.asarray(x,float);return x/max(1e-12,np.linalg.norm(x))
def face(p,mat=1,hatch=True,name='stone'):
 p=np.asarray(p,float)
 if len(p)<3 or np.linalg.norm(np.cross(p[1]-p[0],p[-1]-p[0]))<1e-9:return
 FACES.append(dict(p=p,mat=mat,hatch=hatch,name=name))
def line(p,width=1.,ink=0):LINES.append((np.asarray(p,float),width,ink))
def box(a,b,mat=1,name='masonry',edges=True):
 x,y,z=a;X,Y,Z=b
 points=[[(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],[(X,Y,z),(x,Y,z),(x,Y,Z),(X,Y,Z)],
  [(x,Y,z),(x,y,z),(x,y,Z),(x,Y,Z)],[(X,y,z),(X,Y,z),(X,Y,Z),(X,y,Z)],
  [(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],[(x,Y,z),(X,Y,z),(X,y,z),(x,y,z)]]
 for p in points:face(p,mat,True,name)
 if edges:
  for p in points[:5]:line(p+[p[0]],1.0)
def tube(path,r=.25,mat=3,sides=12,name='pipe',ring=True):
 P=np.asarray(path,float)
 tangent=unit(P[-1]-P[0]);axis=unit(np.cross(tangent,[0,0,1]))
 if np.linalg.norm(axis)<.1:axis=np.array([1.,0,0])
 bit=unit(np.cross(tangent,axis))
 a=np.arange(sides)*2*np.pi/sides
 circles=[p+r*(np.cos(a)[:,None]*axis+np.sin(a)[:,None]*bit) for p in P]
 for a,b in zip(circles,circles[1:]):
  for k in range(sides):face([a[k],a[(k+1)%sides],b[(k+1)%sides],b[k]],mat,True,name)
 for q in (circles[0],circles[-1]):line(np.vstack([q,q[0]]),1.,1 if mat==3 else 0)
 for k in range(0,sides,3):line([q[k] for q in circles],.75,1 if mat==3 else 0)
 return circles


# Scene construction shares the helpers above and installs height(), terrain arrays and geometry.
exec(compile((ROOT/'geometry.py').read_text(),str(ROOT/'geometry.py'),'exec'),globals())

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
EYE=np.array([14.,-36.,12.0]);TARGET=np.array([0.,1.5,3.6])
FWD=unit(TARGET-EYE);VIEW=-FWD;RIGHT=unit(np.cross(FWD,[0,0,1]));UP=np.cross(RIGHT,FWD)
FOCAL=3300.;CX=W*.50;CY=H*.54;NEAR=.5
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
class Terrain:
 u0,u1,v0,v1=-16.,16.,-10.,23.
 def world(self,u,v):return np.column_stack([u,v,height(u,v)])
 def frame(self,u,v):
  u,v=np.asarray(u),np.asarray(v);hx=(height(u+.002,v)-height(u-.002,v))/.004;hy=(height(u,v+.002)-height(u,v-.002))/.004
  return np.column_stack([np.ones_like(u),u*0,hx]),np.column_stack([u*0,np.ones_like(u),hy])
 def normal(self,u,v):
  a,b=self.frame(u,v);n=np.cross(a,b);return n/np.linalg.norm(n,axis=1)[:,None]
 def domain(self,u,v):return (u>=self.u0)&(u<=self.u1)&(v>=self.v0)&(v<=self.v1)
terrain=Terrain()
CH.S=SimpleNamespace(EYE=EYE,project=project,screen_jacobian=jac,SURFACES=[terrain])
CH.FAMILIES=((.65,.064,1.0),(-.68,.082,.85))
CH.BITS=8;CH.BITREV=np.array([int(f'{i:08b}'[::-1],2) for i in range(256)])/256
CH.C_MAX=.53;CH.GAMMA=1.45;CH.C_SPLIT=.14;CH.MIN_GAP=2.1;CH.BREAK_KEEP=.795;CH.GRID=5
LIGHT=unit([-8,-12,20])

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

def stroke_project(P):
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
 if not parts:return []
 parts.append(P[-1]);p=np.asarray(parts);x,y,z=project(p)
 keep=visible(p,*BVH[:6]);keep&=(z>NEAR)&(x>4)&(x<W-4)&(y>4)&(y<H-4)
 return split_paths(np.column_stack([x,y]),keep)

def svg_write(name,groups):
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="240mm" height="{240*H/W:.3f}mm" viewBox="0 0 {W} {H}">',
    '<title>The Three Gates - shared 3D scene</title>']
 for label,paths,col in groups:
  s.append(f'<g inkscape:groupmode="layer" inkscape:label="{label}" fill="none" stroke="{col}" stroke-linecap="round" stroke-linejoin="round">')
  for P,width in paths:
   d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in P);s.append(f'<path stroke-width="{width:.3f}" d="{d}"/>')
  s.append('</g>')
 s.append('</svg>');(OUT/f'{name}.svg').write_text('\n'.join(s))
 import cairosvg
 cairosvg.svg2png(bytestring='\n'.join(s).encode(),write_to=str(OUT/f'{name}.png'),output_width=W,background_color='#eee7d6')

def model_export():
 vs=[];fs=[];mi=[];names=[]
 for f in FACES:
  start=len(vs);vs.extend(f['p'].tolist());fs.append(list(range(start,start+len(f['p']))));mi.append(f['mat']);names.append(f['name'])
 data=dict(vertices=vs,faces=fs,materials=mi,names=names,colors=COLORS,
  camera=dict(kind='perspective',eye=EYE.tolist(),target=TARGET.tolist(),focal_px=FOCAL,principal_point=[CX,CY],horizontal_fov_degrees=float(np.degrees(2*np.arctan(W/(2*FOCAL)))),resolution=[W,H]),
  light_direction=LIGHT.tolist())
 (OUT/'scene.json').write_text(json.dumps(data,separators=(',',':')))
 with (OUT/'three-gates.obj').open('w') as f:
  f.write('mtllib three-gates.mtl\n')
  for v in vs:f.write('v '+' '.join(f'{x:.6f}' for x in v)+'\n')
  last=None
  for face_,mat,name in zip(fs,mi,names):
   if last!=(mat,name):f.write(f'g {name.replace(" ","_")}\nusemtl mat{mat}\n');last=(mat,name)
   f.write('f '+' '.join(str(i+1) for i in face_)+'\n')
 with (OUT/'three-gates.mtl').open('w') as f:
  for i,c in enumerate(COLORS):
   rgb=[int(c[k:k+2],16)/255 for k in [1,3,5]]
   f.write(f'newmtl mat{i}\nKd '+' '.join(map(str,rgb))+'\nKa 0.1 0.1 0.1\n\n')

def clay():
 w,h=W//2,H//2;ys,xs=np.mgrid[:h,:w]
 origins,dirs=primary_rays(np.column_stack([(xs.ravel()+.5)*2,(ys.ravel()+.5)*2]))
 dist,hit=rc.first_hits(origins,dirs,200.,*BVH[:6])
 ok=hit>=0;P=origins[ok]+dirs[ok]*dist[ok,None];N=BVH[7][hit[ok]]
 lum=light(P,N,*BVH[:6]);m=BVH[6][hit[ok]]
 rgb=np.array([[int(c[k:k+2],16) for k in [1,3,5]] for c in COLORS])/255
 a=np.tile(np.array([238,231,214],np.uint8),(len(origins),1))
 a[ok]=np.clip((rgb[m]*lum[:,None]**.7*.95+.08)*255,0,255)
 im=Image.fromarray(a.reshape(h,w,3));im.resize((W,H),Image.Resampling.LANCZOS).save(OUT/'01-massing.png')
 print('Clay render complete',flush=True)

def engrave():
 structure=[[],[],[]]
 for p,w,k in LINES:
  structure[k].extend((q,w) for q in stroke_project(p))
 print('Structure strokes',sum(map(len,structure)),flush=True)
 st=CH.Strokes()
 CH.hatch_on_surface(st,terrain,.36)
 for i,f in enumerate(FACES):
  if not f['hatch']:continue
  n=unit(np.cross(f['p'][1]-f['p'][0],f['p'][-1]-f['p'][0]))
  # The extracted routine handles both face orientations; visibility removes
  # hidden candidates, rather than relying on imported polygon winding.
  if np.linalg.norm(np.cross(f['p'][1]-f['p'][0],f['p'][-1]-f['p'][0]))<.05:continue
  CH.hatch_on_face(st,f['p'],n,.58,i)
 st.finish();print('Hatch candidates',len(st.meta),'points',len(st.sid),flush=True)
 normals=np.empty_like(st.world);albedo=np.ones(len(st.world))
 for k in np.unique(st.attr['surf']):
  mask=st.attr['surf']==k
  if k==0:normals[mask]=terrain.normal(st.world[mask,0],st.world[mask,1])
  else:
   f=FACES[-1-int(k)];normals[mask]=unit(np.cross(f['p'][1]-f['p'][0],f['p'][-1]-f['p'][0]))
   albedo[mask]=.52 if f['mat']==2 else .86 if f['mat']==4 else 1.
 vis=visible(st.world,*BVH[:6]);d=1-light(st.world,normals,*BVH[:6])*albedo
 used=Image.new('L',(W//5,H//5),0);draw=ImageDraw.Draw(used)
 for paths in structure:
  for q,w in paths:draw.line([tuple(p/5) for p in q],fill=190,width=1)
 used=gaussian_filter(np.array(used,float)/255,.7)*.35
 keep=CH.allocate_hatch(st,d,used,vis)
 hpaths=[(q,.85) for q in split_paths(st.xy,keep,st.sid)]
 groups=[('1 crosshatch',hpaths,'#37362f'),('2 structure',structure[0],'#242920'),('3 intervention',structure[1],'#9e392d'),('4 water',structure[2],'#6b8b85')]
 svg_write('02-engraved',groups)
 print('Engraved paths',len(hpaths),flush=True)
 return groups
