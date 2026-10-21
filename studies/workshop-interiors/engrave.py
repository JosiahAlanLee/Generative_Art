"""Vector hatching of evaluated Blender geometry; no raster edge tracing."""
from pathlib import Path
from types import SimpleNamespace
import sys,json,math,time,os
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter
from numba import njit,prange
ROOT=Path(__file__).resolve().parent;KEY=os.environ.get('PLATE','empty-cabinet');OUT=ROOT/'output'/KEY
sys.path.insert(0,str(ROOT/'vendor'))
import raycore as rc
import claude_hatching as CH
D=json.loads((OUT/'scene.json').read_text());V=np.asarray(D['vertices']);F=D['faces'];N=np.asarray(D['normals']);M=np.asarray(D['mats']);HATCH=np.asarray(D['hatch'])
W,H=D['camera']['resolution'];EYE=np.asarray(D['camera']['eye']);TARGET=np.asarray(D['camera']['target']);FOCAL=D['camera']['focal_px'];CX,CY=D['camera']['principal_point'];NEAR=.25
def unit(p):return np.asarray(p)/np.linalg.norm(p)
FWD=unit(TARGET-EYE);RIGHT=unit(np.cross(FWD,[0,0,1]));UP=np.cross(RIGHT,FWD)
def project(p):
 p=np.asarray(p);q=p-EYE;z=q@FWD;safe=np.maximum(z,NEAR)
 return CX+FOCAL*(q@RIGHT)/safe,CY-FOCAL*(q@UP)/safe,z
def jac(P,u,v):
 q=P-EYE;z=np.maximum(q@FWD,NEAR);x=q@RIGHT;y=q@UP;a=np.empty((*P.shape[:-1],2,2))
 for i,d in enumerate([u,v]):
  a[...,0,i]=FOCAL*((d@RIGHT)*z-x*(d@FWD))/z**2
  a[...,1,i]=-FOCAL*((d@UP)*z-y*(d@FWD))/z**2
 return a
def rays(xy):
 d=FWD+((xy[:,0]-CX)/FOCAL)[:,None]*RIGHT-((xy[:,1]-CY)/FOCAL)[:,None]*UP
 d/=np.linalg.norm(d,axis=1)[:,None];return np.broadcast_to(EYE,d.shape).copy(),d

TRIS=[];MATS=[];OWN=[]
for k,f in enumerate(F):
 for j in range(1,len(f)-1):
  t=V[np.asarray(f)[[0,j,j+1]]]
  if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-10:TRIS.append(t);MATS.append(M[k]);OWN.append(k)
TRIS=np.asarray(TRIS);BVH=rc.build_bvh(TRIS,MATS)
not_cord=np.array([not D['names'][k].startswith('Vermilion cord end') for k in OWN])
CORD_BVH=rc.build_bvh(TRIS[not_cord],np.asarray(MATS)[not_cord])
SUN=unit([-8,-3,12])
@njit(cache=True,parallel=True)
def visible(P,eye,blo,bhi,nodes,v0,e1,e2):
 out=np.zeros(len(P),np.bool_)
 for i in prange(len(P)):
  d=eye-P[i];t=np.linalg.norm(d);d/=max(1e-12,t)
  _,hit=rc.trace(P[i]+d*.006,d,1e-5,t-.012,True,blo,bhi,nodes,v0,e1,e2);out[i]=hit<0
 return out
@njit(cache=True,parallel=True)
def light(P,N,eye,sun,right,blo,bhi,nodes,v0,e1,e2):
 out=np.zeros(len(P))
 for i in prange(len(P)):
  n=N[i].copy()
  if np.dot(n,eye-P[i])<0:n=-n
  cos=max(0.,np.dot(n,sun));_,hit=rc.trace(P[i]+n*.012,sun,1e-5,100.,True,blo,bhi,nodes,v0,e1,e2)
  direct=cos*(1 if hit<0 else .05);ao=0.
  for s in [-1.,1.]:
   d=n+s*.5*right;d/=np.linalg.norm(d);t,h=rc.trace(P[i]+n*.015,d,1e-5,1.2,False,blo,bhi,nodes,v0,e1,e2)
   if h>=0:ao+=.5*(1-t/1.2)
  ambient=max(.13,.29-.011*max(0.,P[i,1]))
  out[i]=min(1.,max(.06,ambient*(1-.55*ao)+.8*direct))
 return out

def frame_clip(p,margin=65):
 planes=[(RIGHT+(CX-margin)/FOCAL*FWD,0),(-RIGHT+(W-margin-CX)/FOCAL*FWD,0),(-UP+(CY-margin)/FOCAL*FWD,0),(UP+(H-margin-CY)/FOCAL*FWD,0),(FWD,NEAR)]
 q=np.asarray(p,float)
 for n,off in planes:
  if len(q)<3:return np.zeros((0,3))
  out=[]
  for a,b in zip(q,np.roll(q,-1,axis=0)):
   da=(a-EYE)@n-off;db=(b-EYE)@n-off
   if da>=0:out.append(a)
   if (da>=0)!=(db>=0):out.append(a+(b-a)*da/(da-db))
  q=np.asarray(out)
 return q
def split(xy,keep,sid=None):
 ids=np.flatnonzero(keep)
 if len(ids)<2:return []
 breaks=np.diff(ids)!=1
 if sid is not None:breaks|=np.diff(sid[ids])!=0
 return [xy[g] for g in np.split(ids,np.flatnonzero(breaks)+1) if len(g)>1 and np.linalg.norm(np.diff(xy[g],axis=0),axis=1).sum()>1.15]
def stroke(p,bvh=None):
 if bvh is None:bvh=BVH
 samples=[]
 for a,b in zip(p[:-1],p[1:]):
  sx,sy,z=project(np.vstack([a,b]))
  if min(z)<=NEAR:continue
  length=np.hypot(*(np.diff(q)[0] for q in [sx,sy]))
  if length>16000:continue
  samples.extend(np.linspace(a,b,max(2,int(length/.9)+1))[:-1])
 if not samples:return []
 samples.append(p[-1]);q=np.asarray(samples);x,y,z=project(q)
 ok=(x>65)&(x<W-65)&(y>65)&(y<H-65)&(z>NEAR)
 seen=np.zeros(len(q),bool);seen[ok]=visible(q[ok],EYE,*bvh[:6]);return split(np.column_stack([x,y]),seen)
def simplify(p,tol=.07):
 if len(p)<3:return p
 keep=np.zeros(len(p),bool);keep[[0,-1]]=True;todo=[(0,len(p)-1)]
 while todo:
  a,b=todo.pop()
  if b-a<2:continue
  d=p[b]-p[a];v=p[a+1:b]-p[a];den=d@d;t=np.clip(v@d/den,0,1) if den>1e-20 else np.zeros(len(v))
  err=np.sum((v-t[:,None]*d)**2,axis=1);j=int(np.argmax(err))
  if err[j]>tol*tol:k=a+1+j;keep[k]=True;todo.extend([(a,k),(k,b)])
 return p[keep]
def write(name,groups):
 import cairosvg
 s=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="180mm" height="{H/W*180:g}mm" viewBox="0 0 {W} {H}"><title>{D['title']} - evaluated Blender geometry and vector hatching</title>']
 for label,paths,col in groups:
  s.append(f'<g inkscape:groupmode="layer" inkscape:label="{label}" fill="none" stroke="{col}" stroke-linecap="round" stroke-linejoin="round">')
  for p,w in paths:
   q=simplify(p);d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in q);s.append(f'<path stroke-width="{w:.3f}" d="{d}"/>')
  s.append('</g>')
 s.append('</svg>');svg='\n'.join(s);(OUT/f'{name}.svg').write_text(svg)
 (OUT/f'{name}.png').write_bytes(cairosvg.svg2png(bytestring=svg.encode(),output_width=W,background_color='#f0e9da'))

if __name__=='__main__':
 start=time.time();print('Blender mesh',len(F),'faces,',len(TRIS),'triangles',flush=True)
 centers=np.array([V[f].mean(0) for f in F]);front=np.einsum('ij,ij->i',N,EYE-centers)>1e-8
 edges={}
 for k,f in enumerate(F):
  for a,b in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted([a,b])),[]).append(k)
 lines=[[],[],[],[]]
 for (a,b),adj in edges.items():
  if not any(front[adj]):continue
  if D['names'][adj[0]]=='Joined floor':continue
  if D['names'][adj[0]].startswith('Vermilion cord end'):continue
  silhouette=len(adj)==1 or not all(front[adj])
  crease=HATCH[adj[0]] and len(adj)>1 and N[adj[0]]@N[adj[1]]<.82
  if not(silhouette or crease):continue
  m=M[adj[0]];pen=1 if m==2 else 0
  name=D['names'][adj[0]]
  backdrop=any(name.startswith(s) for s in ['Rear plaster','Side wall','Alcove rear','Alcove return','Bookcase backing'])
  width=.70 if backdrop else 1.25 if pen==0 else 1.02
  lines[pen].extend((q,width) for q in stroke(V[[a,b]]))
 for s in D['strokes']:
  m=s['mat'];pen=2 if m==5 else 1 if m==2 else 0
  p=np.asarray(s['pts'],float)
  weight=1.35 if m in [2,5] else 1.15
  lines[pen].extend((q,s['width']*weight) for q in stroke(p,CORD_BVH if m==5 else BVH))
 print('Visible structure paths',sum(map(len,lines)),flush=True)
 CH.S=SimpleNamespace(EYE=EYE,project=project,screen_jacobian=jac,SURFACES=[])
 CH.BITS=8;CH.BITREV=np.array([int(f'{i:08b}'[::-1],2) for i in range(256)])/256
 CH.C_MAX=.44 if KEY=='office-without-a-seal' else .50;CH.GAMMA=1.45;CH.C_SPLIT=.17;CH.MIN_GAP=2.10;CH.BREAK_KEEP=.795;CH.GRID=5
 CH.FAMILIES=((.64,.020,.72),(-.72,.028,.60))
 st=CH.Strokes();count=0
 # A coarse visibility pass rejects fully buried faces before constructing hatch candidates.
 probes=visible(centers+N*.006,EYE,*BVH[:6])
 for k,f in enumerate(F):
  if not HATCH[k] or not front[k]:continue
  p=frame_clip(V[f])
  if len(p)<3:continue
  if not probes[k]:
   sample=p*.92+p.mean(0)*.08
   if not visible(sample+N[k]*.006,EYE,*BVH[:6]).any():continue
  CH.hatch_on_face(st,p,N[k],.64,k);count+=1
 st.finish();print('Hatching',count,'faces;',len(st.world),'samples',flush=True)
 owner=-1-st.attr['surf'];normals=N[owner];sx,sy=st.xy.T
 framed=(sx>65)&(sx<W-65)&(sy>65)&(sy<H-65)&(st.z>NEAR)
 seen=np.zeros(len(st.world),bool);seen[framed]=visible(st.world[framed],EYE,*BVH[:6])
 shade=np.zeros(len(st.world));albedo=np.array([.98,.83,.94,1.,.72,.93,.94])[M[owner]]
 shade[seen]=1-light(st.world[seen],normals[seen],EYE,SUN,RIGHT,*BVH[:6])*albedo[seen]
 # Large room surfaces recede; apparatus contours retain the strongest ink.
 gains=[]
 for k in owner:
  name=D['names'][k]
  gain=.30 if any(name.startswith(s) for s in ['Rear plaster','Side wall','Alcove rear','Alcove return']) else .48 if name.startswith('Bookcase backing') else .75 if M[k]==2 else 1.
  gains.append(gain)
 shade*=np.asarray(gains)
 ground=np.array([D['names'][k]=='Joined floor' for k in owner])
 if ground.any():
  # Ink thins geometrically toward the front cutaway; no raster fade or mask.
  shade[ground]*=.65*np.clip((st.world[ground,1]+2.6)/3.8,0,1)**1.4
 used=Image.new('L',(W//5,H//5),0);draw=ImageDraw.Draw(used)
 for group in lines:
  for q,w in group:draw.line([tuple(p/5) for p in q],fill=160,width=1)
 used=gaussian_filter(np.asarray(used)/255.,.7)*.32
 keep=CH.allocate_hatch(st,shade,used,seen);hatches=split(st.xy,keep,st.sid)
 # An intentionally unclosed printer's rule, kept outside the artwork margin.
 border=[(np.array([[W-61,H-45],[45,H-45],[45,45],[W-45,45],[W-45,H-61]],float),.7)]
 groups=[('01 light crosshatching',[(q,.78) for q in hatches],'#423e35'),('02 modeled edges and grain',lines[0],'#242820'),('03 brass instruments and cellular tracery',lines[1],'#7b5a2b'),('04 vermilion threads and endpoints',lines[2],'#a32b24'),('05 printer rule',border if KEY in ['maintained-workshop','empty-cabinet'] else [],'#615446')]
 write(KEY,groups)
 np.savez_compressed(OUT/'hatch-audit.npz',world=st.world[keep][::7],owner=owner[keep][::7])
 info={'title':D['title'],'blender':D['blender'],'resolution':[W,H],'faces':len(F),'triangles':len(TRIS),'candidate_hatch_samples':len(st.world),'hatch_paths':len(hatches),'structure_paths':sum(map(len,lines)),'coverage_cap':CH.C_MAX,'minimum_gap_pixels':CH.MIN_GAP,'hatch_width_pixels':.78,'generator':D['generator'],'seconds':round(time.time()-start,1),'limits':['The procedural Blender model was built, saved and rendered.','The final vector engraving uses evaluated Blender polygons with CPU ray visibility and Claude hatching functions.','It is an interpretation of the book scene, not an exact reconstruction or a mechanical working model.']}
 (OUT/'manifest.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2),flush=True)
