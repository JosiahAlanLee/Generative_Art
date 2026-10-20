#!/usr/bin/env python3
"""Shared ray-query and projection core for the scanned statue engraving study."""
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
from numba import njit,prange,set_num_threads,config as _nbconfig
set_num_threads(min(4,_nbconfig.NUMBA_NUM_THREADS))

OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
W,H=1500,1900;GW,GH=600,760
EYE=np.array([-3.0,-8.,3.2]);TARGET=np.array([0.,0.,2.35])
F=(TARGET-EYE);F/=np.linalg.norm(F)
R=np.cross(F,[0.,0.,1.]);R/=np.linalg.norm(R)
U=np.cross(R,F)
FOCAL=3000.;CX=W*.5;CY=H*.51
LIGHT=np.array([-3.8,-3.0,6.3]);LIGHT_SIZE=np.array([1.8,0.,2.0])
INK='#29261f';SEED=1618
RNG=np.random.default_rng(SEED)
FACES=[];LINES=[]

HATCHES=[]

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

def silhouette_edges(verts,triangles):
    centers=verts[triangles].mean(1)
    normals=np.cross(verts[triangles[:,1]]-verts[triangles[:,0]],verts[triangles[:,2]]-verts[triangles[:,0]])
    visible=np.sum(normals*(EYE-centers),1)>0
    edges={}
    for f,front in zip(triangles,visible):
        for a,b in zip(f,np.roll(f,-1)):
            key=tuple(sorted((int(a),int(b))))
            if key in edges:
                if edges[key]!=bool(front):edges[key]=None
            else:edges[key]=bool(front)
    contour=[key for key,v in edges.items() if v is None]
    adj={}
    for a,b in contour:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    unused=set(contour)
    while unused:
        a,b=unused.pop();path=[a,b]
        while True:
            options=[q for q in adj[path[-1]] if tuple(sorted((path[-1],q))) in unused]
            if not options:break
            q=options[0];unused.remove(tuple(sorted((path[-1],q))));path.append(q)
            if q==path[0]:break
        line(verts[path],1.08,'scan silhouette')

def projection(p):
    q=np.asarray(p)-EYE;z=q@F
    return np.stack([CX+FOCAL*(q@R)/z,CY-FOCAL*(q@U)/z,z],-1)

def build_bvh():
    tris=[];mats=[]
    for f in FACES:
        if f.mat==7:continue
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
        _,hit=cast(p+n*.001,d,dist-.003,blo,bhi,nodes,tris)
        if hit>=0:return 0.
    return 20.*cos/(dist*dist)

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
            dd,hh=cast(p+n*.0015,hdir,.35,blo,bhi,nodes,tris)
            if hh>=0:ao+=1-dd/.35
            if j<4:
                dd,hh=cast(p+n*.0015,hdir,8.,blo,bhi,nodes,tris)
                if hh>=0 and mats[hh]!=3:
                    q=p+n*.0015+hdir*dd;nn=normals[hh].copy()
                    if np.dot(nn,hdir)>0:nn=-nn
                    albedo=.70 if mats[hh] in (0,6,8,9) else (.52 if mats[hh] in (4,10) else .36)
                    bounce+=direct(q,nn,LIGHT,blo,bhi,nodes,tris,True)*albedo/4
        ao/=len(hemis)
        alb=.72 if mats[hit] in (0,6,9) else (.78 if mats[hit]==8 else (.52 if mats[hit] in (4,10) else (.42 if mats[hit]==1 else .25)))
        # Exposure is an artistic mapping; secondary transport is one diffuse bounce.
        result[iy,ix,0]=min(1.,max(0.,.10+flat*alb*1.6))
        result[iy,ix,1]=min(1.,max(0.,.10*(1-.95*ao)+(dl+.70*bounce)*alb*1.6))
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
        _,hit=cast(points[i]+d*.0015,d,dist-.004,blo,bhi,nodes,tris)
        vis[i]=hit<0
    return vis

def lighting(bvh):
    rng=np.random.default_rng(SEED)
    samples=np.array([LIGHT+[dy,0,dz] for dy,dz in [(-.45,-.5),(-.45,.5),(.45,-.5),(.45,.5)]])
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
    with open(str(cache)+'.writing','wb') as out:np.savez_compressed(out,data=data,key=key)
    Path(str(cache)+'.writing').replace(cache)
    return data


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
