"""Render The Three Gates using the common model, hatch functions and plant depth buffer."""
from pathlib import Path
import hashlib,json,subprocess,time
import numpy as np
import build as B
import occlusion as M

def place(patch):
 instances=[];rng=np.random.default_rng(1926);patchiness=M.noise2(86,.32)
 def add(p,x,y,height,width=.7,root_z=None):
  z=float(B.height(x,y))+.02 if root_z is None else root_z
  s=height/p.get('height',30)
  instances.append(M.Instance(p,p['origin'],[x,y,z],s,width))
 add(patch['willow'],7.35,4.30,7.6,.82)
 add(patch['pine'],-8.4,7.1,5.7,.75)
 # A distant tree band, rooted on the extended terrain rather than a floating backdrop.
 for x,y,h in [(-21,23,3.2),(-18,25,3.9),(-15,23,3.1),(-12,26,4.1),(-9,25,3.3),(12,26,3.2),(15,24,4.2),(18,27,3.6),(21,26,3.8),(24,25,3.2)]:
  add(patch['pine'],x,y,h,.51)
 # Reed beds are local clusters beside the channel, rather than a continuous border.
 for cx,cy,rx,ry in [(-4.65,-3.6,1.1,1.0),(4.9,-5.9,1.2,1.6),(5.0,6.5,.6,1.8),(-4.8,9.0,.6,1.1)]:
  for _ in range(100):
   x,y=cx+rng.normal(0,rx*.45),cy+rng.normal(0,ry*.45)
   if not(4.35<abs(x)<6.1 and -7.6<y<10):continue
   if abs(y-1.6)<2.1:continue
   h=float(B.height(x,y));gx=abs(float(B.height(x+.1,y)-B.height(x-.1,y)))/.2;gy=abs(float(B.height(x,y+.1)-B.height(x,y-.1)))/.2
   if max(gx,gy)>1.1:continue
   i=int(rng.integers(24));add(patch['plants'][i],x,y,rng.uniform(.65,1.05),.60)
 # Uneven grass and occasional umbels on the higher banks, with a winding path excluded.
 for _ in range(1200):
  x,y=rng.uniform(-10.5,10.5),rng.uniform(-7.8,10.0)
  if abs(x)<5.1:continue
  if abs(y-1.6)<1.6 and abs(x)<7.4:continue
  if -7.3<x<-5.1 and -3<y<.9:continue
  if y>2.8 and abs(x-(6.15+1.1*np.sin((y-2.8)*.48)))<.60:continue
  # Smoothly clustered planting with open foreground and gaps between patches.
  value=float(patchiness(x,y))
  chance=np.clip(.24+.9*value,0,.77)
  chance*=min(1.,max(0.,(10.6-abs(x))/.9))*min(1.,max(0.,(y+8.1)/1.6))
  if rng.random()>chance:continue
  gx=abs(float(B.height(x+.1,y)-B.height(x-.1,y)))/.2;gy=abs(float(B.height(x,y+.1)-B.height(x,y-.1)))/.2
  if max(gx,gy)>.95:continue
  i=int(rng.integers(24,48));add(patch['plants'][i],x,y,rng.uniform(.29,.56),.56)
 return instances

def compose(groups,instances):
 buf=np.full((B.H*M.K,B.W*M.K),np.inf)
 for inst in instances:M.stamp(buf,inst)
 D=M.model_depth(buf)
 pens,audit=M.plant_strokes(instances,buf,return_audit=True)
 # This assertion compares each surviving sample's OWN plane depth with the nearest silhouette.
 inside=audit['survives'];bad=M.lookup(buf,audit['xy'][inside])<audit['owner_depth'][inside]-M.EPS_PLANT
 assert not bad.any()
 clipped=[(label,M.clip_screen_paths(paths,buf,D),col) for label,paths,col in groups]
 flora=[('5 willow and reeds',pens[0],'#303c32'),('6 foliage',pens[1],'#53634c'),('7 seedheads',pens[2],'#a0523d'),('8 foliage tint',pens[3],'#87927b')]
 B.svg_write('03-three-gates',clipped+flora)
 B.svg_write('04-landscape',flora)
 np.savez_compressed(B.OUT/'occlusion-audit.npz',xy=audit['xy'][inside],owner_depth=audit['owner_depth'][inside],nearest_depth=M.lookup(buf,audit['xy'][inside]))
 return {'instances':len(instances),'plant_paths':sum(map(len,pens)),'owner_depth_samples_checked':int(inside.sum()),'owner_depth_violations':int(bad.sum())}

if __name__=='__main__':
 t=time.time();B.model_export();B.clay();g=B.engrave()
 subprocess.run(['node',str(B.ROOT/'plants.cjs')],check=True)
 p=json.loads((B.OUT/'plants.json').read_text());inst=place(p);info=compose(g,inst)
 manifest={'title':'The Three Gates - lower perspective','date':'2026-10-20','frame':[B.W,B.H],'triangles':len(B.TRIS),'faces':len(B.FACES),'landscape':info,
  'camera':{'kind':'perspective','eye':B.EYE.tolist(),'target':B.TARGET.tolist(),'focal_px':B.FOCAL,'principal_point':[B.CX,B.CY],'horizontal_fov_degrees':float(np.degrees(2*np.arctan(B.W/(2*B.FOCAL))))},
  'plant_placements':[{'kind':i.patch['kind'],'root':i.root.tolist(),'scale':i.s} for i in inst],
  'engine_sha256':hashlib.sha256((B.ROOT/'vendor/driftless-engine.js').read_bytes()).hexdigest(),
  'source_snapshot':'JosiahAlanLee/Generative_Art 5bf920e3a7babef8085f67682f9e5212207f487c',
  'limits':['Artistic sluice study; not an engineering design.','Vegetation occupies parallel vertical drawing planes and casts no shadows.','Blender reconstruction provided but not executed.'],
  'seconds':round(time.time()-t,1)}
 (B.OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='plant_placements'},indent=2),flush=True)
