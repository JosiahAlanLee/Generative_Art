#!/usr/bin/env python3
"""Static corridor: BVH ray queries -> baked illumination -> vector hatching."""
from pathlib import Path
from dataclasses import dataclass
import sys,math,json,time,hashlib,io,argparse,inspect
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter,median_filter
import cairosvg
ROOT=Path(__file__).resolve().parent
LOCAL_DEPS=ROOT.parent/'garden-study/culture-deps'
if LOCAL_DEPS.exists():sys.path.insert(0,str(LOCAL_DEPS))
from numba import njit,prange,set_num_threads
set_num_threads(4)

OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
W,H=1500,1900;GW,GH=300,380
EYE=np.array([.42,-2.4,2.25]);TARGET=np.array([-.10,13.,2.95])
F=(TARGET-EYE);F/=np.linalg.norm(F)
R=np.cross(F,[0.,0.,1.]);R/=np.linalg.norm(R)
U=np.cross(R,F)
FOCAL=1130.;CX=W*.5;CY=H*.51
LIGHT=np.array([-6.6,6.,4.0]);LIGHT_SIZE=np.array([0.,2.2,2.6])
INK='#29261f';SEED=1618
RNG=np.random.default_rng(SEED)
FACES=[];LINES=[]

@dataclass
class Face:
    p:np.ndarray
    mat:int=0

def face(p,mat=0):FACES.append(Face(np.asarray(p,float),mat))
def line(p,width=1.,kind='structure'):
    if len(p)>1:LINES.append((np.asarray(p,float),width,kind))
def box(x0,y0,z0,x1,y1,z1,mat=0,edges=True):
    p=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
                [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
    for q in [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:face(p[list(q)],mat)
    if edges:
        for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:line(p[[a,b]],1.3)

def arch_x(y,ri=2.37,ro=2.60,z=3.6,depth=.26,n=25):
    """A transverse, solid voussoir arch, supported by piers."""
    ts=np.linspace(0,np.pi,n+1)
    def point(r,t,yy):return [r*np.cos(t),yy,z+r*np.sin(t)]
    for i,(a,b) in enumerate(zip(ts,ts[1:])):
        q=[point(ri,a,y),point(ri,b,y),point(ro,b,y),point(ro,a,y)]
        back=[[x,y+depth,zz] for x,_,zz in q]
        face(q);face(back[::-1])
        for j in range(4):face([q[j],back[j],back[(j+1)%4],q[(j+1)%4]])
        line(q+[q[0]],1.10,'arch joints')
    for yy in (y,y+depth):
        for rr in (ri,ro):line([point(rr,t,yy) for t in np.linspace(0,np.pi,100)],1.5,'arch')
    for a,b in [(-2.6,-2.37),(2.37,2.6)]:
        box(a,y,0,b,y+depth,3.6)
        box(a-.045,y-.065,3.38,b+.045,y+depth+.065,3.61)
        box(a-.035,y-.04,0,b+.035,y+depth+.04,.22)

def doorway_left():
    cy,cz,ri,ro=6.,2.1,1.2,1.41
    box(-2.94,-.5,0,-2.6,4.8,3.6)
    box(-2.94,7.2,0,-2.6,22,3.6)
    ts=np.linspace(0,np.pi,31)
    for a,b in zip(ts,ts[1:]):
        ya,yb=cy+ri*np.cos(a),cy+ri*np.cos(b)
        za,zb=cz+ri*np.sin(a),cz+ri*np.sin(b)
        q=[[-2.6,ya,za],[-2.6,yb,zb],[-2.6,yb,3.6],[-2.6,ya,3.6]]
        back=[[-2.94,y,z] for _,y,z in q]
        face(q);face(back[::-1]);face([q[0],q[1],back[1],back[0]])
    def point(r,t,x):return [x,cy+r*np.cos(t),cz+r*np.sin(t)]
    for a,b in zip(np.linspace(0,np.pi,15),np.linspace(0,np.pi,15)[1:]):
        q=[point(ri,a,-2.53),point(ri,b,-2.53),point(ro,b,-2.53),point(ro,a,-2.53)]
        face(q);line(q+[q[0]],1.2,'portal joints')
    for r in (ri,ro):line([point(r,t,-2.53) for t in np.linspace(0,np.pi,100)],1.65,'portal')
    for a,b in [(4.58,4.8),(7.2,7.42)]:box(-2.94,a,0,-2.52,b,2.1)
    # Real reveals around the opening, across the wall's thickness.
    for y in (4.8,7.2):face([[-2.94,y,0],[-2.6,y,0],[-2.6,y,2.1],[-2.94,y,2.1]])
    box(-3.05,4.55,-.02,-2.42,7.45,.12)
    face([[-6.8,3.,0],[-2.94,3.,0],[-2.94,9.,0],[-6.8,9.,0]],0)
    face([[-6.65,2.,0],[-6.65,10.,0],[-6.65,10.,7.],[-6.65,2.,7.]],3)

def scene():
    face([[-2.94,-.5,0],[2.94,-.5,0],[2.94,22,0],[-2.94,22,0]])
    box(2.6,-.5,0,2.94,22,3.6)
    doorway_left()
    ts=np.linspace(0,np.pi,29)
    for a,b in zip(ts,ts[1:]):
        face([[2.6*np.cos(a),-.5,3.6+2.6*np.sin(a)],
              [2.6*np.cos(b),-.5,3.6+2.6*np.sin(b)],
              [2.6*np.cos(b),22,3.6+2.6*np.sin(b)],
              [2.6*np.cos(a),22,3.6+2.6*np.sin(a)]])
    for y in (1.0,4.0,8.3,12.3,16.3,20.3):arch_x(y)
    # Rear wall and deep wooden door.
    box(-2.6,21.7,0,-.88,22.,6.2)
    box(.88,21.7,0,2.6,22.,6.2)
    ri,cz=.88,2.0
    ts=np.linspace(0,np.pi,26)
    for a,b in zip(ts,ts[1:]):
        xa,xb=ri*np.cos(a),ri*np.cos(b);za,zb=cz+ri*np.sin(a),cz+ri*np.sin(b)
        face([[xa,21.7,za],[xb,21.7,zb],[xb,21.7,6.2],[xa,21.7,6.2]])
    box(-.88,22.5,0,.88,22.58,2.95,1)
    for x in np.arange(-.85,.9,.20):line([[x,22.49,.04],[x,22.49,2.8]],.85,'wood grain')
    for z in (.5,1.9):box(-.78,22.46,z,.78,22.49,z+.095,2)
    line([[ri*np.cos(t),21.68,cz+ri*np.sin(t)] for t in ts],1.4,'rear arch')
    for x in (-.88,.88):line([[x,21.68,0],[x,21.68,2]],1.4,'rear jamb')
    # A bench with two solid trestles and a continuous plank seat.
    box(1.83,9.2,.72,2.40,12.1,.85,1)
    for y in (9.45,11.65):box(1.9,y,0,2.30,y+.22,.72,0)
    for x in (2.0,2.20):line([[x,9.22,.856],[x,12.08,.856]],.8,'plank joint')
    # Floor joints follow real ground coordinates.
    for y in np.arange(0,22,1.1):
        line([[-2.6,y,.004],[2.6,y,.004]],.72,'flagstone')
        for x in np.arange(-2.6+(int(y/1.1)%2)*.65,2.6,1.3):
            line([[x,y,.005],[x,min(y+1.1,22),.005]],.70,'flagstone')
    # Masonry is sparse and irregular; it remains independent of illumination.
    for x in (-2.594,2.594):
        for j,z in enumerate(np.arange(.48,3.6,.48)):
            for y0,y1 in [(0.,4.55),(7.5,21.6)]:
                line([[x,y0,z],[x,y1,z]],.63,'mortar')
                for y in np.arange(y0+(j%2)*.55,y1,1.1):
                    line([[x,y,z-.46],[x,y,z-.025]],.57,'mortar')
        for _ in range(100):
            y=RNG.uniform(0,21);z=RNG.uniform(.1,3.5)
            if x<0 and 4.5<y<7.5:continue
            line([[x,y,z],[x,y+.05,z+.025],[x,y+.13,z+.02]],.55,'stone nick')

def projection(p):
    q=np.asarray(p)-EYE;z=q@F
    return np.stack([CX+FOCAL*(q@R)/z,CY-FOCAL*(q@U)/z,z],-1)

def build_bvh():
    tris=[];mats=[]
    for f in FACES:
        for i in range(1,len(f.p)-1):
            t=f.p[[0,i,i+1]]
            if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-9:tris.append(t);mats.append(f.mat)
    tris=np.array(tris);mats=np.array(mats,np.int32)
    lo=tris.min(1);hi=tris.max(1);cent=(lo+hi)/2
    nodes=[];order=[]
    def build(ix):
        index=len(nodes);node=[lo[ix].min(0),hi[ix].max(0),-1,-1,0,0];nodes.append(node)
        if len(ix)<=8:
            node[4]=len(order);node[5]=len(ix);order.extend(ix.tolist())
        else:
            axis=int(np.argmax(np.ptp(cent[ix],axis=0)));ix=ix[np.argsort(cent[ix,axis],kind='stable')]
            mid=len(ix)//2;node[2]=build(ix[:mid]);node[3]=build(ix[mid:])
        return index
    build(np.arange(len(tris)))
    t=tris[order];normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
    return (np.array([n[0] for n in nodes]),np.array([n[1] for n in nodes]),
            np.array([n[2:] for n in nodes],np.int32),t,mats[order],normal)

@njit(cache=True)
def cast(o,d,tmax,blo,bhi,nodes,tris):
    stack=np.empty(80,np.int32);stack[0]=0;sp=1;best=tmax;hit=-1
    while sp:
        sp-=1;ni=stack[sp];tn=.0001;tf=best;ok=True
        for k in range(3):
            if abs(d[k])<1e-12:
                if o[k]<blo[ni,k] or o[k]>bhi[ni,k]:ok=False;break
            else:
                a=(blo[ni,k]-o[k])/d[k];b=(bhi[ni,k]-o[k])/d[k]
                if a>b:a,b=b,a
                tn=max(tn,a);tf=min(tf,b)
                if tn>tf:ok=False;break
        if not ok:continue
        if nodes[ni,3]>0:
            start,count=nodes[ni,2],nodes[ni,3]
            for j in range(start,start+count):
                v0=tris[j,0];e1=tris[j,1]-v0;e2=tris[j,2]-v0
                pv=np.cross(d,e2);det=np.dot(e1,pv)
                if abs(det)<1e-10:continue
                inv=1/det;tv=o-v0;u=np.dot(tv,pv)*inv
                if u<0 or u>1:continue
                qv=np.cross(tv,e1);v=np.dot(d,qv)*inv
                if v<0 or u+v>1:continue
                tt=np.dot(e2,qv)*inv
                if .0001<tt<best:best=tt;hit=j
        else:
            stack[sp]=nodes[ni,0];stack[sp+1]=nodes[ni,1];sp+=2
    return best,hit

@njit(cache=True)
def direct(p,n,light,blo,bhi,nodes,tris,shadow=True):
    d=light-p;dist=np.sqrt(np.dot(d,d));d/=dist;cos=max(0.,np.dot(n,d))
    if cos==0:return 0.
    if shadow:
        _,hit=cast(p+n*.002,d,dist-.006,blo,bhi,nodes,tris)
        if hit>=0:return 0.
    return 24.*cos/(dist*dist)

@njit(cache=True)
def hemisphere(n,u,v):
    a=np.array([0.,0.,1.])
    if abs(n[2])>.9:a=np.array([1.,0.,0.])
    t=np.cross(a,n);t/=np.sqrt(np.dot(t,t));b=np.cross(n,t)
    rr=math.sqrt(u);theta=2*math.pi*v
    return rr*math.cos(theta)*t+rr*math.sin(theta)*b+math.sqrt(1-u)*n

@njit(cache=True,parallel=True)
def bake(blo,bhi,nodes,tris,mats,normals,light_samples,hemis):
    result=np.zeros((GH,GW,8),np.float64)
    for index in prange(GW*GH):
        iy,ix=index//GW,index%GW
        px=(ix+.5)*W/GW;py=(iy+.5)*H/GH
        d=F+(px-CX)/FOCAL*R-(py-CY)/FOCAL*U;d/=np.sqrt(np.dot(d,d))
        dist,hit=cast(EYE,d,100.,blo,bhi,nodes,tris)
        if hit<0:result[iy,ix,0]=1.;result[iy,ix,1]=1.;result[iy,ix,2]=1.;continue
        p=EYE+d*dist;n=normals[hit].copy()
        if np.dot(n,d)>0:n=-n
        result[iy,ix,7]=hit+1
        if mats[hit]==3:
            result[iy,ix,0]=1.;result[iy,ix,1]=1.;result[iy,ix,2]=1.;result[iy,ix,3]=1.;continue
        flat=direct(p,n,LIGHT,blo,bhi,nodes,tris,False)
        dl=0.
        for j in range(len(light_samples)):dl+=direct(p,n,light_samples[j],blo,bhi,nodes,tris,True)/len(light_samples)
        ao=0.;bounce=0.
        for j in range(len(hemis)):
            hdir=hemisphere(n,hemis[j,0],hemis[j,1])
            dd,hh=cast(p+n*.003,hdir,1.10,blo,bhi,nodes,tris)
            if hh>=0:ao+=1-dd/1.10
            if j<4:
                dd,hh=cast(p+n*.003,hdir,18.,blo,bhi,nodes,tris)
                if hh>=0 and mats[hh]!=3:
                    q=p+n*.003+hdir*dd;nn=normals[hh].copy()
                    if np.dot(nn,hdir)>0:nn=-nn
                    albedo=.73 if mats[hh]==0 else .36
                    bounce+=direct(q,nn,LIGHT,blo,bhi,nodes,tris,True)*albedo/4
        ao/=len(hemis)
        alb=.72 if mats[hit]==0 else (.38 if mats[hit]==1 else .25)
        # Exposure is an artistic mapping; secondary transport is one diffuse bounce.
        result[iy,ix,0]=min(1.,max(0.,.14+flat*alb*2.4))
        result[iy,ix,1]=min(1.,max(0.,.14*(1-.70*ao)+(dl+.70*bounce)*alb*2.4))
        result[iy,ix,2]=min(1.,max(0.,ao))
        result[iy,ix,3]=dl
        result[iy,ix,4]=bounce
        result[iy,ix,5]=flat
        result[iy,ix,6]=dist
    return result

@njit(cache=True,parallel=True)
def point_visibility(points,blo,bhi,nodes,tris):
    vis=np.zeros(len(points),np.bool_)
    for i in prange(len(points)):
        d=EYE-points[i];dist=np.sqrt(np.dot(d,d));d/=dist
        _,hit=cast(points[i]+d*.004,d,dist-.01,blo,bhi,nodes,tris)
        vis[i]=hit<0
    return vis

def validate_queries(bvh):
    blo,bhi,nodes,tris,_,_=bvh
    def hit(a,b):
        a=np.array(a,float);d=np.array(b,float)-a;dist=np.linalg.norm(d);d/=dist
        return cast(a,d,dist-.01,blo,bhi,nodes,tris)[1]
    assert hit([0,6,1],LIGHT)<0,'The side doorway should pass this ray'
    assert hit([0,11,1],LIGHT)>=0,'The solid side wall must block this ray'
    d,h=cast(np.array([0.,3.,1.]),np.array([0.,0.,-1.]),10.,blo,bhi,nodes,tris)
    assert h>=0 and abs(d-1)<1e-7,'The floor intersection should be exactly one unit below'
    return ['portal passes light ray','solid wall blocks light ray','known floor intersection distance']

def lighting(bvh):
    rng=np.random.default_rng(SEED)
    samples=np.array([LIGHT+[0,dy,dz] for dy,dz in [(-.55,-.65),(-.55,.65),(.55,-.65),(.55,.65)]])
    hemis=np.column_stack([(np.arange(16)+.5)/16,((np.arange(16)*.61803398875)%1)])
    config=dict(eye=EYE.tolist(),target=TARGET.tolist(),light=LIGHT.tolist(),focal=FOCAL,
                image=[W,H],bake=[GW,GH],cx=CX,cy=CY)
    ray_code=''.join(inspect.getsource(fn.py_func) for fn in (cast,direct,hemisphere,bake))
    key=hashlib.sha256(np.asarray(bvh[3]).tobytes()+np.asarray(bvh[4]).tobytes()+
        json.dumps(config,sort_keys=True).encode()+samples.tobytes()+hemis.tobytes()+ray_code.encode()).hexdigest()
    cache=OUT/'lighting.npz'
    if cache.exists():
        z=np.load(cache)
        if str(z['key'])==key:return z['data']
    print('Tracing direct light, contact rays, and one diffuse bounce',flush=True)
    t=time.time();data=bake(*bvh,samples,hemis);print('Lighting bake seconds',round(time.time()-t,2),flush=True)
    np.savez_compressed(cache,data=data,key=key)
    return data

def hatch_candidates():
    candidates=[]
    for face_index,f in enumerate(FACES):
        if f.mat==3:continue
        p=f.p;u=p[1]-p[0];un=np.linalg.norm(u)
        if un<1e-8:continue
        n=np.cross(u,p[-1]-p[0]);nn=np.linalg.norm(n)
        if nn<1e-8:continue
        n/=nn
        if np.dot(n,EYE-p.mean(0))<-.0001:continue
        if abs(n[2])>.95 or abs(n[1])>.95:u=np.array([1.,0.,0.])
        else:u=np.array([0.,1.,0.])
        u-=n*np.dot(n,u);u/=np.linalg.norm(u);v=np.cross(n,u)
        uv=np.column_stack([(p-p[0])@u,(p-p[0])@v])
        for family,angle in enumerate((.65,-.68)):
            d=np.array([np.cos(angle),np.sin(angle)]);perp=np.array([-d[1],d[0]])
            vals=uv@perp;spacing=.065 if family==0 else .095
            if f.mat==1:spacing*=.8
            for k,off in enumerate(np.arange(vals.min()+.02,vals.max(),spacing)):
                hits=[]
                for a,b,va,vb in zip(uv,np.roll(uv,-1,axis=0),vals,np.roll(vals,-1)):
                    if (va<=off<vb) or (vb<=off<va):hits.append(a+(b-a)*(off-va)/(vb-va))
                if len(hits)<2:continue
                hits=sorted(hits,key=lambda q:q@d);a,b=hits[0],hits[-1];length=np.linalg.norm(b-a)
                if length<.03:continue
                ts=np.linspace(0,1,max(3,int(length/.055)+1))
                q=a+(b-a)*ts[:,None]
                q+=RNG.normal(0,.004,(len(q),1))*perp
                pts=p[0]+q[:,0,None]*u+q[:,1,None]*v+n*.006
                # All versions use the same candidate paths and threshold ranks.
                threshold=(.10+(k%4)*.145) if family==0 else (.48+(k%3)*.12)
                candidates.append((pts,.94 if family==0 else .82,threshold,family,'hatch'))
    for p,width,kind in LINES:
        pieces=[]
        for a,b in zip(p,p[1:]):
            length=np.linalg.norm(b-a);pieces.extend(a+np.linspace(0,1,max(2,int(length/.035)+1))[:,None]*(b-a))
        candidates.append((np.array(pieces),width,-1.,0,kind))
    return candidates

def rdp(p,tol=.25):
    p=np.asarray(p)
    if len(p)<3:return list(p)
    a,b=p[0],p[-1];ab=b-a;length=np.linalg.norm(ab)
    if length<1e-8:
        j=np.argmax(np.sum((p-a)**2,1))
        if j==0:return [p[0],p[-1]]
        return rdp(p[:j+1],tol)[:-1]+rdp(p[j:],tol)
    dist=np.abs(ab[0]*(p[:,1]-a[1])-ab[1]*(p[:,0]-a[0]))/length;j=int(np.argmax(dist))
    if dist[j]<tol:return [p[0],p[-1]]
    return rdp(p[:j+1],tol)[:-1]+rdp(p[j:],tol)

def physarum_density(dark):
    sys.path.insert(0,str(ROOT/'vendor'))
    import claude_physarum_plot as pp
    img=np.repeat((1-dark)[...,None],3,axis=2)
    looks=(pp.LOOKS['faithful'],pp.LOOKS['feral'])
    fields=pp.prepare_cultures(img,220,[('feral','#625444'),('faithful','#29261f')],'#ffffff',looks)
    sim=pp.simulate_cultures(fields,looks,.45,repel=2.,territories=12,steps=600,density=.22,
                              avg_last=100,seed=SEED,verbose=False)
    a=pp.norm_trail(sim['trail']);ratio=(a[0]-a[1])/(a[0]+a[1]+.18)
    ratio=np.asarray(Image.fromarray(ratio.astype(np.float32),'F').resize((GW,GH),Image.Resampling.BILINEAR))
    # The colony affects mark thresholds only, inside an intermediate shadow band.
    band=np.clip((dark-.35)/.15,0,1)*np.clip((.92-dark)/.12,0,1)
    return np.clip(dark+.075*ratio*band,0,1),ratio

def draw_variants(bvh,data):
    print('Generating surface-aligned candidate strokes',flush=True)
    candidates=hatch_candidates();sizes=[len(p) for p,*_ in candidates]
    pts=np.concatenate([p for p,*_ in candidates]);print('Visibility queries',len(pts),flush=True)
    vis=point_visibility(pts,*bvh[:4]);pp=projection(pts)
    inside=(pp[:,2]>.15)&(pp[:,0]>2)&(pp[:,0]<W-2)&(pp[:,1]>2)&(pp[:,1]<H-2)
    vis&=inside
    ix=np.clip((pp[:,0]/W*GW).astype(int),0,GW-1);iy=np.clip((pp[:,1]/H*GH).astype(int),0,GH-1)
    flat=1-np.sqrt(np.clip(median_filter(data[:,:,0],size=3),0,1))
    traced=1-np.sqrt(np.clip(median_filter(data[:,:,1],size=3),0,1))
    mod,ratio=physarum_density(traced)
    maps=[('01-surface-light',flat),('02-ray-lit',traced),('03-ray-lit-physarum',mod)]
    stats=[]
    for name,dark in maps:
        output=[];counts={};start=0
        for c,size in zip(candidates,sizes):
            p,width,threshold,family,kind=c;sl=slice(start,start+size)
            keep=vis[sl].copy();xy=pp[sl,:2]
            density=dark[iy[sl],ix[sl]]
            if threshold>=0:keep&=density>threshold
            # Sparse, physical interruptions avoid a mechanically perfect screen.
            if kind=='hatch':
                indices=np.arange(size)
                phase=((math.sin(start*12.9898)*43758.5453)%1)*2*math.pi
                keep&=(np.sin(indices*.34+phase)>-.75) | (density>.73)
            changes=np.diff(np.r_[0,keep.astype(np.int8),0])
            for a,b in zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1)):
                if b-a<2:continue
                q=rdp(xy[a:b]);length=np.linalg.norm(q[-1]-q[0])
                if length<1.4:continue
                d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in q)
                output.append(f'<path d="{d}" stroke-width="{width:.2f}"/>')
                counts[kind]=counts.get(kind,0)+1
            start+=size
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><title>Porticus: {name}</title><rect width="100%" height="100%" fill="white"/><g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">'+''.join(output)+'</g></svg>'
        (OUT/f'{name}.svg').write_text(svg)
        cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/f'{name}.png'),output_width=W,output_height=H)
        stats.append(dict(name=name,paths=counts))
    return stats,dict(flat=flat,traced=traced,modulated=mod,physarum=ratio)

def export_mesh():
    lines=['# Porticus / Z up / camera and lighting in scene.json'];v=0
    for f in FACES:
        lines.append(f'g material_{f.mat}')
        for p in f.p:lines.append('v '+' '.join(f'{x:.7f}' for x in p))
        lines.append('f '+' '.join(str(v+i+1) for i in range(len(f.p))));v+=len(f.p)
    (OUT/'corridor.obj').write_text('\n'.join(lines)+'\n')

def proof(data,maps):
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fp=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
    if fp.exists():pdfmetrics.registerFont(TTFont('StudySerif',str(fp)))
    serif='StudySerif' if fp.exists() else 'Times-Roman'
    c=Canvas(str(OUT/'Hallway_Light_and_Hatching.pdf'),pagesize=(504,720),pageCompression=1)
    c.setTitle('Porticus - hallway light and hatching');c.setAuthor('Josiah Alan-Lee / ChatGPT-Codex / Claude culture engine')
    def page(title,num):
        c.setFillColor(HexColor('#ede6d4'));c.rect(0,0,504,720,stroke=0,fill=1)
        c.setFillColor(HexColor('#332d24'));c.setFont(serif,9);c.drawCentredString(252,683,'PORTICUS INTERVALLORUM')
        c.setFont(serif,17);c.drawCentredString(252,655,title)
        c.setFont(serif,8);c.drawCentredString(252,26,f'{num} / 5')
    def draw(im,x,y,w,h,tint=True):
        a=np.asarray(im.convert('RGB'),dtype=float)/255
        if tint:a=a*np.array([237,230,212])
        else:a=a*255
        b=io.BytesIO();Image.fromarray(np.uint8(a)).save(b,format='PNG');c.drawImage(ImageReader(b),x,y,width=w,height=h)
    variants=[('01-surface-light','I. Surface light only','Surface response, with light visibility disabled.'),
              ('02-ray-lit','II. Light through the doorway','Shadow rays, contact occlusion, and one diffuse bounce.'),
              ('03-ray-lit-physarum','III. A little growth in the stone','Same traced light, with restrained Physarum modulation.')]
    for i,(name,title,caption) in enumerate(variants):
        page(title,i+1);iw=420;ih=iw*H/W;draw(Image.open(OUT/f'{name}.png'),42,100,iw,ih)
        c.setFont(serif,9);c.drawCentredString(252,74,caption);c.showPage()
    page('The light, before it becomes ink',4)
    diagnostic=[('Direct illumination',data[:,:,3]),('Contact occlusion',1-data[:,:,2]),
                ('One diffuse bounce',data[:,:,4]),('Final hatch density',1-maps['traced'])]
    for i,(title,a) in enumerate(diagnostic):
        x=42+(i%2)*220;y=340-(i//2)*270
        if i in (0,2):a=np.clip(a/max(np.percentile(a[a>0],97) if np.any(a>0) else 1,.001),0,1)
        im=Image.fromarray(np.uint8(np.clip(a,0,1)*255)).convert('RGB')
        draw(im,x,y,200,253.3);c.setFont(serif,9);c.drawString(x,y-14,title)
    c.setFont(serif,8);c.drawString(42,44,'Diagnostic maps have separate display scales. Final plates contain vector strokes.');c.showPage()
    page('Doorway and floor, closer',5)
    for i,(name,title,_) in enumerate(variants):
        y=452-i*195;im=Image.open(OUT/f'{name}.png')
        c.setFont(serif,10);c.drawString(42,y+178,title)
        crop=im.crop((90,750,850,1250));draw(crop,42,y,250,164.5)
        # A second, smaller crop isolates the cast light on the floor.
        crop=im.crop((480,1110,1110,1660));draw(crop,312,y+18,150,131)
    c.save()

def main():
    scene();export_mesh();bvh=build_bvh();checks=validate_queries(bvh)
    print('Mesh triangles',len(bvh[3]),'BVH nodes',len(bvh[0]),flush=True)
    data=lighting(bvh);stats,maps=draw_variants(bvh,data)
    for name,a in maps.items():Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(OUT/f'map-{name}.png')
    proof(data,maps)
    report=dict(seed=SEED,eye=EYE.tolist(),target=TARGET.tolist(),focal=FOCAL,image=[W,H],bake=[GW,GH],
        source=LIGHT.tolist(),area_source_size=LIGHT_SIZE.tolist(),primary_shadow_samples=4,
        ao_samples=16,ao_distance=1.10,diffuse_bounce_samples=4,bounces=1,ambient_floor=.14,
        triangles=len(bvh[3]),bvh_nodes=len(bvh[0]),ray_checks=checks,variants=stats,
        note='Single low-sample diffuse bounce estimate and explicit ambient floor; no caustics. Exposure and ink mapping are artistic controls.')
    (OUT/'scene.json').write_text(json.dumps(report,indent=2));print('Proof ready',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--proof-only',action='store_true');args=ap.parse_args()
    if args.proof_only:
        data=np.load(OUT/'lighting.npz')['data']
        proof(data,dict(traced=1-np.sqrt(np.clip(median_filter(data[:,:,1],size=3),0,1))))
    else:main()
