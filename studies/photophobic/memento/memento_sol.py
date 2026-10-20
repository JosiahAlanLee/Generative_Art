#!/usr/bin/env python3
"""Windowsill memento mori: BVH ray queries -> baked illumination -> vector hatching."""
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
W,H=1500,1900;GW,GH=450,570
EYE=np.array([.65,-5.15,2.20]);TARGET=np.array([0.,.15,1.25])
F=(TARGET-EYE);F/=np.linalg.norm(F)
R=np.cross(F,[0.,0.,1.]);R/=np.linalg.norm(R)
U=np.cross(R,F)
FOCAL=1800.;CX=W*.5;CY=H*.51
LIGHT=np.array([-2.4,3.8,4.5]);LIGHT_SIZE=np.array([1.8,0.,2.0])
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

# The skull is an illustrative implicit sculpture, not an anatomical scan.
HATCHES=[]
SKULL_ORIGIN=np.array([-.53,-.07,.08])

def ellipsoid_field(p,c,r):
    return (np.sqrt(np.sum(((p-np.asarray(c))/np.asarray(r))**2,axis=-1))-1)*min(r)

def smin(a,b,k=.065):
    h=np.clip(.5+.5*(b-a)/k,0,1)
    return b*(1-h)+a*h-k*h*(1-h)

def skull_field(p):
    x,y,z=np.moveaxis(np.asarray(p),-1,0)
    a=ellipsoid_field(p,[0,.10,1.10],[.49,.43,.58])
    for c,r in [([0,.12,.77],[.43,.38,.29]),([0,-.10,.70],[.32,.28,.27]),
                ([-.36,-.015,.76],[.135,.26,.105]),([.36,-.015,.76],[.135,.26,.105]),
                ([-.205,-.24,1.135],[.21,.11,.075]),([.205,-.24,1.135],[.21,.11,.075]),
                ([-.30,.14,.47],[.080,.15,.24]),([.30,.14,.47],[.080,.15,.24]),
                ([0,-.28,.23],[.15,.11,.09])]:
        a=smin(a,ellipsoid_field(p,c,r))
    rr=np.sqrt((x/.32)**2+((y-.08)/.36)**2)
    jaw=np.maximum(np.sqrt(((rr-1)*.32)**2+(z-.24)**2)-.065,y-.12)
    a=smin(a,jaw,.04)
    # Open orbital cavities, nasal aperture, and the two small mandibular gaps.
    for c,r in [([-.205,-.225,.96],[.162,.31,.195]),([.205,-.225,.96],[.162,.31,.195]),
                ([0,-.255,.70],[.087,.25,.14]),([0,-.24,.78],[.046,.25,.15]),
                ([-.17,-.04,.405],[.10,.18,.07]),([.17,-.04,.405],[.10,.18,.07])]:
        a=np.maximum(a,-ellipsoid_field(p,c,r))
    return a

def skull_normal(p):
    e=.0007;axes=np.eye(3)*e
    g=np.stack([(skull_field(p+a)-skull_field(p-a))/(2*e) for a in axes],-1)
    return g/np.maximum(np.linalg.norm(g,axis=-1,keepdims=True),1e-10)

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
        line(verts[path],1.08,'bone contour')

def skull():
    from skimage.measure import marching_cubes,find_contours
    lo=np.array([-.66,-.67,.08]);hi=np.array([.66,.67,1.78]);step=.012
    axes=[np.linspace(a,b,int(np.ceil((b-a)/step))+1) for a,b in zip(lo,hi)]
    grid=np.stack(np.meshgrid(*axes,indexing='ij'),-1)
    field=skull_field(grid).astype(np.float32)
    spacing=[a[1]-a[0] for a in axes]
    verts,tri,_,_=marching_cubes(field,0,spacing=spacing,allow_degenerate=False)
    verts+=lo
    n=np.cross(verts[tri[:,1]]-verts[tri[:,0]],verts[tri[:,2]]-verts[tri[:,0]])
    reverse=np.sum(n*skull_normal(verts[tri].mean(1)),1)<0
    tri[reverse]=tri[reverse][:,::-1]
    verts+=SKULL_ORIGIN
    for t in tri:face(verts[t],6)
    silhouette_edges(verts,tri)
    # Oblique planar sections intersect the sculpture in continuous curved strokes.
    for family in range(3):
        if family in (0,2):
            aa=np.linspace(-.66,.66,145);bb=np.linspace(-.67,.67,145)
            A,B=np.meshgrid(aa,bb,indexing='ij');offsets=np.arange(.05,1.95,.017) if family==0 else np.arange(.48,1.35,.0035)
        else:
            aa=np.linspace(-.67,.67,145);bb=np.linspace(.08,1.78,175)
            A,B=np.meshgrid(aa,bb,indexing='ij');offsets=np.arange(-1.12,.85,.027)
        for k,off in enumerate(offsets):
            if family in (0,2):points=np.stack([A,B,off+.30*A+.14*B],-1)
            else:points=np.stack([off+.25*B-.12*A,A,B],-1)
            sf=skull_field(points)
            for c in find_contours(sf,0):
                u=np.interp(c[:,0],np.arange(len(aa)),aa);v=np.interp(c[:,1],np.arange(len(bb)),bb)
                q=np.stack([u,v,off+.30*u+.14*v],-1) if family in (0,2) else np.stack([off+.25*v-.12*u,u,v],-1)
                if family==2:
                    inner=np.zeros(len(q),bool)
                    for cc,rr in [([-.205,-.225,.96],[.162,.31,.195]),([.205,-.225,.96],[.162,.31,.195]),([0,-.255,.70],[.087,.25,.14]),([0,-.24,.78],[.046,.25,.15])]:
                        inner|=(np.abs(ellipsoid_field(q,cc,rr))<.0035)&(q[:,1]>-.37)
                    cuts=np.diff(np.r_[0,inner.astype(np.int8),0])
                    for ia,ib in zip(np.flatnonzero(cuts==1),np.flatnonzero(cuts==-1)):
                        if ib-ia<3:continue
                        qq=q[ia:ib];qq=qq+skull_normal(qq)*.0016
                        HATCHES.append((qq+SKULL_ORIGIN,.88,.56+(k%4)*.035,2,'cavity hatch'))
                    continue
                q+=skull_normal(q)*.0015
                threshold=(.12+(k%4)*.13) if family==0 else (.48+(k%3)*.105)
                HATCHES.append((q+SKULL_ORIGIN,.82 if family==0 else .69,threshold,family,'bone hatch'))
    # A broken sagittal suture over the crown.
    yy=np.linspace(-.18,.47,130);xx=.006*np.sin(np.arange(len(yy))*1.7)
    zz=1.10+.58*np.sqrt(np.maximum(0,1-(xx/.49)**2-((yy-.10)/.43)**2))
    line(np.column_stack([xx,yy,zz+.002])+SKULL_ORIGIN,.75,'cranial suture')
    # Separate upper and lower teeth, with real gaps between them.
    for row,z in enumerate((.445,.322)):
        for i,t in enumerate(np.linspace(np.pi+.15,2*np.pi-.15,12)):
            center=np.array([.255*np.cos(t),-.01+.245*np.sin(t),z])+SKULL_ORIGIN
            ellipsoid(center,[.032 if i not in (4,5,6,7) else .038,.048,.064],0,24,12,teeth=True)
    print('Implicit skull triangles',len(tri),flush=True)

def ellipsoid(center,radii,mat=0,nu=48,nv=24,teeth=False):
    center=np.asarray(center);radii=np.asarray(radii)
    us=np.linspace(0,2*np.pi,nu+1);vs=np.linspace(-np.pi/2,np.pi/2,nv+1)
    rings=[center+np.stack([radii[0]*np.cos(v)*np.cos(us[:-1]),radii[1]*np.cos(v)*np.sin(us[:-1]),np.full(nu,radii[2]*np.sin(v))],-1) for v in vs]
    for a,b in zip(rings,rings[1:]):
        for i in range(nu):face([a[i],a[(i+1)%nu],b[(i+1)%nu],b[i]],9 if teeth else mat)
    # Curved meridians carry the tone without exposing the polygon tessellation.
    for k,u in enumerate(np.linspace(0,2*np.pi,22,endpoint=False)):
        vv=np.linspace(-np.pi/2,np.pi/2,65)
        q=center+np.stack([radii[0]*np.cos(vv)*np.cos(u),radii[1]*np.cos(vv)*np.sin(u),radii[2]*np.sin(vv)],-1)
        q+=(q-center)/radii*.001
        HATCHES.append((q,.70,.20+(k%4)*.13,0,'tooth hatch'))
    # Small individual contours keep the dentition legible.
    fakeverts=np.array(rings).reshape(-1,3);tri=[]
    for j in range(nv):
        for i in range(nu):
            a=j*nu+i;b=j*nu+(i+1)%nu;c=(j+1)*nu+(i+1)%nu;d=(j+1)*nu+i
            tri.extend([[a,b,c],[a,c,d]])
    silhouette_edges(fakeverts,np.array(tri))

def lathe(x,y,profile,mat=1,n=48,curves=True):
    profile=np.asarray(profile,float);ts=np.linspace(0,2*np.pi,n,endpoint=False)
    rings=[np.column_stack([x+r*np.cos(ts),y+r*np.sin(ts),np.full(n,z)]) for z,r in profile]
    for a,b in zip(rings,rings[1:]):
        for i in range(n):face([a[i],a[(i+1)%n],b[(i+1)%n],b[i]],mat)
    if mat!=7:
        face(rings[0][::-1],mat);face(rings[-1],mat)
    for j in (0,len(rings)-1):line(np.vstack([rings[j],rings[j][0]]),.95,'turned rim' if mat!=7 else 'glass rim')
    # Silhouette meridians. Glass is drawn as contours and omitted from opaque rays.
    angle=math.atan2(EYE[1]-y,EYE[0]-x);distance=math.hypot(EYE[1]-y,EYE[0]-x)
    for side in (-1,1):
        p=[]
        for z,r in profile:
            a=angle+side*math.acos(min(.999,r/distance));p.append([x+r*np.cos(a),y+r*np.sin(a),z])
        line(p,1.0 if mat!=7 else .90,'glass contour' if mat==7 else 'turned contour')
    if curves:
        zz=np.linspace(profile[0,0],profile[-1,0],max(30,int((profile[-1,0]-profile[0,0])/.008)))
        rr=np.interp(zz,profile[:,0],profile[:,1])
        for k,a in enumerate(np.linspace(0,2*np.pi,70,endpoint=False)):
            theta=a+.06*np.sin(zz*9)
            q=np.column_stack([x+(rr+.0014)*np.cos(theta),y+(rr+.0014)*np.sin(theta),zz])
            HATCHES.append((q,.73,.14+(k%4)*.135,0,'turned hatch'))

def candle():
    x,y=-1.43,.20
    lathe(x,y,[(.01,.25),(.045,.28),(.085,.24),(.11,.16),(.17,.09),(.22,.085),(.25,.16),(.28,.19),(.305,.18)],2)
    z=np.linspace(.29,1.80,100);r=.125+.006*np.sin(z*11)+.003*np.sin(z*23)
    lathe(x,y,list(zip(z,r)),8,72)
    # A scalloped, extinguished wax rim and thin wick.
    theta=np.linspace(0,2*np.pi,80)
    rim=np.column_stack([x+.127*np.cos(theta),y+.127*np.sin(theta),1.80+.018*np.sin(5*theta)+.01*np.sin(8*theta)])
    line(rim,1.0,'melted wax')
    for angle,height in [(3.8,.38),(4.6,.23),(5.7,.17),(2.6,.28)]:
        zz=np.linspace(1.79-height,1.79,35);rr=np.interp(zz,z,r)+.006
        q=np.column_stack([x+rr*np.cos(angle+.015*np.sin(zz*35)),y+rr*np.sin(angle+.015*np.sin(zz*35)),zz])
        line(q,.85,'wax drip')
    lathe(x,y,[(1.795,.014),(1.86,.010)],2,12,False)

def hourglass():
    x,y=1.00,.20
    lathe(x,y,[(.0,.34),(.045,.36),(.09,.34),(.12,.28)],1)
    lathe(x,y,[(1.23,.28),(1.26,.34),(1.31,.36),(1.35,.34)],1)
    for a in (7*np.pi/6,11*np.pi/6):
        xx=x+.285*np.cos(a);yy=y+.285*np.sin(a)
        lathe(xx,yy,[(.12,.043),(.20,.045),(.25,.026),(1.10,.026),(1.16,.045),(1.23,.043)],1,16)
    glass=[(.14,.21),(.18,.245),(.27,.25),(.39,.21),(.51,.13),(.59,.061),(.65,.032),(.70,.032),(.77,.061),(.87,.14),(.98,.215),(1.08,.25),(1.17,.23),(1.21,.21)]
    lathe(x,y,glass,7,72,False)
    # Only two unobstructed highlight curves are drawn on the glass.
    for a in (4.15,4.55):
        q=[[x+r*np.cos(a),y+r*np.sin(a),z] for z,r in glass]
        line(q,.44,'glass highlight')
    lathe(x,y,[(.14,.215),(.20,.19),(.27,.14),(.34,.085),(.41,.012)],10,48)
    lathe(x,y,[(.69,.012),(.74,.039),(.79,.072),(.85,.115),(.90,.15)],10,48)
    lathe(x,y,[(.41,.006),(.69,.006)],10,12,False)

def book():
    first=len(FACES);li=len(LINES)
    box(-1.35,-.57,0,.22,.65,.035,1)
    box(-1.30,-.53,.035,.17,.61,.185,4)
    box(-1.35,-.57,.185,.22,.65,.22,1)
    box(-1.35,.58,.025,.22,.65,.195,1)
    # Irregular page edges belong to the exposed paper block.
    for j,z in enumerate(np.linspace(.052,.176,15)):
        line([[-1.29,-.534,z],[.16,-.534,z+.001*np.sin(j)]],.50,'page edge')
        line([[.174,-.52,z],[.174,.59,z]],.47,'page edge')
    for x in (-1.15,-.85,-.55,-.25,.05):
        line([[x,.574,.04],[x,.586,.181]],1.0,'raised spine band')
    # Slightly turned book, with the skull still resting within its cover.
    a=-.075;c,s=np.cos(a),np.sin(a);rotation=np.array([[c,-s,0],[s,c,0],[0,0,1.]])
    origin=np.array([-.55,.05,0.])
    for f in FACES[first:]:f.p=(f.p-origin)@rotation.T+origin
    for i in range(li,len(LINES)):
        q,w,k=LINES[i];LINES[i]=((q-origin)@rotation.T+origin,w,k)

def window():
    ri,ro,spring=1.63,1.84,2.02;y0,y1=1.03,1.41
    for xa,xb in ((-2.20,-ri),(ri,2.20)):
        box(xa,y0,-.28,xb,y1,4.1,0,False)
    ts=np.linspace(0,np.pi,45)
    for a,b in zip(ts,ts[1:]):
        q=[[ri*np.cos(a),y0,spring+ri*np.sin(a)],[ri*np.cos(b),y0,spring+ri*np.sin(b)],
           [ri*np.cos(b),y0,4.1],[ri*np.cos(a),y0,4.1]]
        face(q);face([[x,y1,z] for x,_,z in q][::-1]);face([q[0],q[1],[q[1][0],y1,q[1][2]],[q[0][0],y1,q[0][2]]])
    # The sill has a visible front edge and two moulding steps.
    box(-2.15,-1.0,-.20,2.15,1.42,0,0)
    box(-2.09,-.95,-.29,2.09,1.41,-.20,0)
    box(-2.03,-.90,-.35,2.03,1.40,-.29,0)
    for x in (-ri,ri):
        face([[x,y0,0],[x,y1,0],[x,y1,spring],[x,y0,spring]])
        line([[x,y0-.004,0],[x,y0-.004,spring]],1.6,'window jamb')
    for r in (ri,ro):line([[r*np.cos(t),y0-.006,spring+r*np.sin(t)] for t in np.linspace(0,np.pi,100)],1.65,'window arch')
    for t in np.linspace(0,np.pi,15):line([[ri*np.cos(t),y0-.007,spring+ri*np.sin(t)],[ro*np.cos(t),y0-.007,spring+ro*np.sin(t)]],.85,'voussoir joint')
    # Slender leaded bars cast real shadows onto the sill and objects.
    box(-.035,1.25,.0,.035,1.29,3.64,2)
    box(-1.62,1.25,1.98,1.62,1.29,2.05,2)
    for z in np.arange(.44,3.3,.44):
        width=ri if z<spring else np.sqrt(max(0,ri*ri-(z-spring)**2))
        line([[-width,1.255,z],[width,1.255,z]],.58,'leaded glass seam')
    face([[-6,4.05,0],[4,4.05,0],[4,4.05,7],[-6,4.05,7]],3)
    # A few worn stone nicks, with no drawn landscape behind the objects.
    for i in range(45):
        x=RNG.uniform(-2.0,2.0);y=RNG.uniform(-.85,1.0)
        if -.95<x<.05 and -.5<y<.55:continue
        line([[x,y,.003],[x+.035,y+.012,.003],[x+.075,y+.006,.003]],.45,'sill nick')

def scene():
    window();book();skull();candle();hourglass()


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
        result[iy,ix,0]=min(1.,max(0.,.14+flat*alb*2.4))
        result[iy,ix,1]=min(1.,max(0.,.14*(1-.95*ao)+(dl+.70*bounce)*alb*2.4))
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

def validate_queries(bvh):
    blo,bhi,nodes,tris,_,_=bvh
    def hit(a,b):
        a=np.array(a,float);d=np.array(b,float)-a;dist=np.linalg.norm(d);d/=dist
        return cast(a,d,dist-.01,blo,bhi,nodes,tris)[1]
    assert hit([-.8,.5,1.1],LIGHT)<0,'The light ray must pass through the window opening'
    assert hit([2.1,.8,.5],LIGHT)>=0,'The right masonry jamb must block this ray'
    d,h=cast(np.array([1.65,-.6,1.]),np.array([0.,0.,-1.]),10.,blo,bhi,nodes,tris)
    assert h>=0 and abs(d-1)<1e-7,'Known sill height must be zero'
    assert skull_field(np.array([-.205,-.225,.96]))>0,'The left orbital center must be empty'
    assert skull_field(np.array([.205,-.225,.96]))>0,'The right orbital center must be empty'
    assert skull_field(np.array([0.,.10,1.25]))<0,'The cranial vault must be solid'
    return ['window passes light ray','stone jamb blocks light ray','known sill intersection','two empty eye sockets','solid cranial vault']

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

def hatch_candidates():
    candidates=list(HATCHES)
    for face_index,f in enumerate(FACES):
        if f.mat in (3,6,7,8,9):continue
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
        for family,angle in enumerate((1.40,) if f.mat in (4,5) else (.65,-.68)):
            d=np.array([np.cos(angle),np.sin(angle)]);perp=np.array([-d[1],d[0]])
            vals=uv@perp;spacing=.027 if family==0 else .039
            if f.mat==1:spacing*=.8
            if f.mat in (4,5):spacing=.026
            for k,off in enumerate(np.arange(vals.min()+.009,vals.max(),spacing)):
                hits=[]
                for a,b,va,vb in zip(uv,np.roll(uv,-1,axis=0),vals,np.roll(vals,-1)):
                    if (va<=off<vb) or (vb<=off<va):hits.append(a+(b-a)*(off-va)/(vb-va))
                if len(hits)<2:continue
                hits=sorted(hits,key=lambda q:q@d);a,b=hits[0],hits[-1];length=np.linalg.norm(b-a)
                if length<.012:continue
                ts=np.linspace(0,1,max(3,int(length/.012)+1))
                q=a+(b-a)*ts[:,None]
                q+=RNG.normal(0,.0006,(len(q),1))*perp
                pts=p[0]+q[:,0,None]*u+q[:,1,None]*v+n*.0015
                # All versions use the same candidate paths and threshold ranks.
                threshold=(.10+(k%4)*.145) if family==0 else (.48+(k%3)*.12)
                candidates.append((pts,.80 if family==0 else .70,threshold,family,'hatch'))
    for p,width,kind in LINES:
        pieces=[]
        for a,b in zip(p,p[1:]):
            length=np.linalg.norm(b-a);pieces.extend(a+np.linspace(0,1,max(2,int(length/.008)+1))[:,None]*(b-a))
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
            if kind in ('hatch','bone hatch','turned hatch','tooth hatch'):
                indices=np.arange(size)
                phase=((math.sin(start*12.9898)*43758.5453)%1)*2*math.pi
                keep&=(np.sin(indices*.25+phase)>-.90) | (density>.73)
            changes=np.diff(np.r_[0,keep.astype(np.int8),0])
            for a,b in zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1)):
                if b-a<2:continue
                q=rdp(xy[a:b]);length=np.linalg.norm(q[-1]-q[0])
                if length<1.4:continue
                d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in q)
                output.append(f'<path d="{d}" stroke-width="{width:.2f}"/>')
                counts[kind]=counts.get(kind,0)+1
            start+=size
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><title>Memento: {name}</title><rect width="100%" height="100%" fill="white"/><g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">'+''.join(output)+'</g></svg>'
        (OUT/f'{name}.svg.writing').write_text(svg)
        (OUT/f'{name}.svg.writing').replace(OUT/f'{name}.svg')
        cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/f'{name}.png.writing'),output_width=W,output_height=H)
        (OUT/f'{name}.png.writing').replace(OUT/f'{name}.png')
        stats.append(dict(name=name,paths=counts))
    return stats,dict(flat=flat,traced=traced,modulated=mod,physarum=ratio)

def export_mesh():
    lines=['# Memento / Z up / camera and lighting in scene.json'];v=0
    for f in FACES:
        lines.append(f'g material_{f.mat}')
        for p in f.p:lines.append('v '+' '.join(f'{x:.7f}' for x in p))
        lines.append('f '+' '.join(str(v+i+1) for i in range(len(f.p))));v+=len(f.p)
    (OUT/'memento.obj').write_text('\n'.join(lines)+'\n')

def proof(data,maps):
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fp=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
    if fp.exists():pdfmetrics.registerFont(TTFont('StudySerif',str(fp)))
    serif='StudySerif' if fp.exists() else 'Times-Roman'
    c=Canvas(str(OUT/'Memento_Mori_Study.pdf'),pagesize=(504,720),pageCompression=1)
    c.setTitle('Memento mori - a windowsill study');c.setAuthor('Josiah Alan-Lee / ChatGPT-Codex / Claude culture engine')
    def page(title,num):
        c.setFillColor(HexColor('#ede6d4'));c.rect(0,0,504,720,stroke=0,fill=1)
        c.setFillColor(HexColor('#332d24'));c.setFont(serif,9);c.drawCentredString(252,683,'MEMENTO MORI')
        c.setFont(serif,17);c.drawCentredString(252,655,title)
        c.setFont(serif,8);c.drawCentredString(252,26,f'{num} / 5')
    def draw(im,x,y,w,h,tint=True):
        a=np.asarray(im.convert('RGB'),dtype=float)/255
        if tint:a=a*np.array([237,230,212])
        else:a=a*255
        b=io.BytesIO();Image.fromarray(np.uint8(a)).save(b,format='PNG');c.drawImage(ImageReader(b),x,y,width=w,height=h)
    variants=[('01-surface-light','I. Surface light only','Surface response, with light visibility disabled.'),
              ('02-ray-lit','II. Light through the casement','Shadow rays, contact occlusion, and one diffuse bounce.'),
              ('03-ray-lit-physarum','III. A trace of dissolution','Traced light, with restrained Physarum hatch modulation.')]
    for i,(name,title,caption) in enumerate(variants):
        page(title,i+1);iw=420;ih=iw*H/W
        c.setFont(serif,9);c.drawCentredString(252,74,caption);c.showPage()
    page('The light, before it becomes ink',4)
    diagnostic=[('Direct illumination',data[:,:,3]),('Contact occlusion',np.where(data[:,:,6]>0,1-data[:,:,2],1.)),
                ('One diffuse bounce',data[:,:,4]),('Final hatch density',1-maps['traced'])]
    for i,(title,a) in enumerate(diagnostic):
        x=42+(i%2)*220;y=340-(i//2)*270
        if i in (0,2):a=np.clip(a/max(np.percentile(a[a>0],97) if np.any(a>0) else 1,.001),0,1)
        im=Image.fromarray(np.uint8(np.clip(a,0,1)*255)).convert('RGB')
        draw(im,x,y,200,253.3);c.setFont(serif,9);c.drawString(x,y-14,title)
    c.setFont(serif,8);c.drawString(42,44,'Diagnostic maps have separate display scales. Final plates contain vector strokes.');c.showPage()
    page('Bone, wax, and sand, closer',5)
    for i,(name,title,_) in enumerate(variants):
        y=452-i*195;im=Image.open(OUT/f'{name}.png')
        c.setFont(serif,10);c.drawString(42,y+178,title)
        crop=im.crop((60,720,875,1355));draw(crop,42,y,211,164.5)
        # A second crop isolates the hourglass and the sand.
        crop=im.crop((850,900,1480,1450));draw(crop,312,y+18,150,131)
    c.save()
    # Embed the full-scene vector paths directly into the first three PDF pages.
    import fitz
    pdf=OUT/'Memento_Mori_Study.pdf';doc=fitz.open(pdf)
    for i,(name,_,_) in enumerate(variants):
        svg=(OUT/f'{name}.svg').read_text().replace('fill="white"','fill="#ede6d4"').replace(INK,'#26221a')
        plate=fitz.open(stream=cairosvg.svg2pdf(bytestring=svg.encode()),filetype='pdf')
        doc[i].show_pdf_page(fitz.Rect(42,720-(100+420*H/W),462,620),plate,0)
        plate.close()
    target=pdf.with_suffix('.writing.pdf');doc.save(target,garbage=4,deflate=True);doc.close();target.replace(pdf)

def main():
    scene();export_mesh();bvh=build_bvh();checks=validate_queries(bvh)
    print('Mesh triangles',len(bvh[3]),'BVH nodes',len(bvh[0]),flush=True)
    data=lighting(bvh);stats,maps=draw_variants(bvh,data)
    for name,a in maps.items():Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(OUT/f'map-{name}.png')
    proof(data,maps)
    report=dict(seed=SEED,eye=EYE.tolist(),target=TARGET.tolist(),focal=FOCAL,image=[W,H],bake=[GW,GH],
        cx=CX,cy=CY,right=R.tolist(),up=U.tolist(),forward=F.tolist(),source=LIGHT.tolist(),area_source_size=LIGHT_SIZE.tolist(),primary_shadow_samples=4,glass='contours only; no refraction or glass shadow',
        ao_samples=16,ao_distance=.35,diffuse_bounce_samples=4,bounces=1,ambient_floor=.14,
        triangles=len(bvh[3]),bvh_nodes=len(bvh[0]),ray_checks=checks,variants=stats,
        note='Single low-sample diffuse bounce estimate and explicit ambient floor; no caustics. Exposure and ink mapping are artistic controls.')
    (OUT/'scene.json').write_text(json.dumps(report,indent=2));print('Proof ready',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--proof-only',action='store_true');args=ap.parse_args()
    if args.proof_only:
        data=np.load(OUT/'lighting.npz')['data']
        proof(data,dict(traced=1-np.sqrt(np.clip(median_filter(data[:,:,1],size=3),0,1))))
    else:main()
