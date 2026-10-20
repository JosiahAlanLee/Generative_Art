#!/usr/bin/env python3
"""A fixed-scene engraving experiment. Real 3D projection and depth-tested paths.

No image-generation model or traced reference image is used. The vector base is
drawn from meshes and procedural 3D marks; treatments reuse the Codex code.
"""
from pathlib import Path
from dataclasses import dataclass
import argparse, hashlib, json, math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter, binary_dilation
import cairosvg

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'vendor'))
import figure_growth as growth

W,H=1800,1250
RNG=np.random.default_rng(1943)
EYE=np.array([8.5,-25.,9.0]); TARGET=np.array([0.,6.,3.2])
FORWARD=(TARGET-EYE); FORWARD/=np.linalg.norm(FORWARD)
RIGHT=np.cross(FORWARD,[0,0,1.]); RIGHT/=np.linalg.norm(RIGHT)
UP=np.cross(RIGHT,FORWARD)
FOCAL=1680.
LIGHT=np.array([-0.6,-0.5,1.]); LIGHT/=np.linalg.norm(LIGHT)
INK='#29261f'

def proj(p):
    q=np.asarray(p,float)-EYE
    z=q@FORWARD
    return np.stack([W/2+FOCAL*(q@RIGHT)/z,H*.53-FOCAL*(q@UP)/z,z],axis=-1)

@dataclass
class Face:
    p: np.ndarray
    mat: str
    strength: float=1.

FACES=[]; LINES=[]
def face(p,mat='stone',strength=1.):
    FACES.append(Face(np.array(p,float),mat,strength))

def line(p,width=.85,kind='structure',opacity=1.):
    p=np.asarray(p,float)
    if len(p)>1: LINES.append((p,width,kind,opacity))

def box(x0,y0,z0,x1,y1,z1,mat='stone',edges=True):
    p=np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
                [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]])
    for ix in [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]:
        face(p[list(ix)],mat)
    if edges:
        for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]:
            line(p[[a,b]],1.15)

def revolve(cx,cy,profile,mat='stone',n=52,rails=True):
    rings=[]
    for r,z in profile:
        t=np.linspace(0,2*np.pi,n,endpoint=False)
        rings.append(np.column_stack([cx+r*np.cos(t),cy+r*np.sin(t),np.full(n,z)]))
    for a,b in zip(rings,rings[1:]):
        for i in range(n): face([a[i],a[(i+1)%n],b[(i+1)%n],b[i]],mat)
    if rails:
        for r in rings: line(np.vstack([r,r[0]]),1.05)

def ellipsoid(c,r,mat='leaf',n=22,m=12):
    c=np.array(c); r=np.array(r)
    def rough(q):
        if mat!='leaf':return np.ones(np.asarray(q).shape[:-1])
        return 1+.055*np.sin(q[...,0]*14+q[...,2]*9)+.035*np.cos(q[...,1]*17-q[...,2]*11)
    rings=[]
    for phi in np.linspace(-np.pi/2+.008,np.pi/2-.008,m):
        t=np.linspace(0,2*np.pi,n,endpoint=False)
        q=np.column_stack([np.cos(t)*np.cos(phi),np.sin(t)*np.cos(phi),np.full(n,np.sin(phi))])
        rings.append(c+q*r*rough(q)[...,None])
    for a,b in zip(rings,rings[1:]):
        for i in range(n): face([a[i],a[(i+1)%n],b[(i+1)%n],b[i]],mat)
    # Perspective silhouette in scaled sphere coordinates.
    v=(EYE-c)/r; v/=np.linalg.norm(v)
    a=np.cross(v,[0,0,1.]); a/=max(np.linalg.norm(a),1e-9); b=np.cross(v,a)
    t=np.linspace(0,2*np.pi,110)
    q=np.cos(t)[:,None]*a+np.sin(t)[:,None]*b
    line(c+q*r*rough(q)[...,None],1.25,'foliage')
    # Hooked leaf marks sit on the actual visible ellipsoid surface.
    for _ in range(2300 if mat=='leaf' else 150):
        q=RNG.normal(size=3); q/=np.linalg.norm(q)
        if np.dot(q,v)<.08: continue
        shade=np.clip(.55-.55*np.dot(q,LIGHT),.08,.98)
        if mat=='leaf' and RNG.random()>shade+.12:continue
        tang=np.cross(q,[0,0,1.]); tang/=max(np.linalg.norm(tang),1e-9)
        t=np.linspace(-.08,.08,7)
        qq=q+t[:,None]*tang+(np.cos(t*22)-1)[:,None]*np.cross(q,tang)*.06
        qq/=np.linalg.norm(qq,axis=1)[:,None]
        line(c+qq*r*rough(qq)[...,None]*1.014,.9 if mat=='leaf' else .6,'leaf',.87)

def branch(points,radii):
    p=np.array(points,float)
    rings=[]
    for i,(pt,r) in enumerate(zip(p,radii)):
        d=p[min(i+1,len(p)-1)]-p[max(0,i-1)]
        d/=np.linalg.norm(d)
        u=np.cross(d,[0,1.,0]); u/=np.linalg.norm(u); v=np.cross(d,u)
        t=np.linspace(0,2*np.pi,10,endpoint=False)
        rings.append(pt+r*(np.cos(t)[:,None]*u+np.sin(t)[:,None]*v))
    for a,b in zip(rings,rings[1:]):
        for i in range(10): face([a[i],a[(i+1)%10],b[(i+1)%10],b[i]],'bark')
    for j in range(10): line([r[j] for r in rings],.85,'bark')

def masonry(x0,x1,y,z0,z1,course=.48,block=1.2):
    for k,z in enumerate(np.arange(z0+course,z1,course)):
        line([[x0,y-.012,z],[x1,y-.012,z]],.68,'joint',.8)
        for x in np.arange(x0+(k%2)*block*.5,x1,block):
            if x>x0+.1:
                line([[x,y-.02,z-course+.035],[x+RNG.normal(0,.025),y-.02,z-.03]],.62,'joint',.8)
    for _ in range(int((x1-x0)*(z1-z0)*3)):
        x=RNG.uniform(x0,x1); z=RNG.uniform(z0,z1)
        line([[x,y-.025,z],[x+.04,y-.025,z+.02],[x+.10,y-.025,z+.012]],.5,'stone',.7)

def scene():
    # Courtyard, raised beds and rear enclosure.
    face([[-10,-7,0],[10,-7,0],[10,12,0],[-10,12,0]],'earth')
    box(-10,10.5,0,-.55,11.05,6.25)
    box(3.35,10.5,0,10,11.05,6.25)
    box(-.55,10.5,0,3.35,11.05,1.60)
    # Filled upper arch region. The opening itself has no front surface.
    cx,r,cz=1.4,1.95,3.45
    t=np.linspace(0,np.pi,34)
    xs=cx+r*np.cos(t); zs=cz+r*np.sin(t)
    for i in range(len(t)-1):
        face([[xs[i],10.5,zs[i]],[xs[i+1],10.5,zs[i+1]],[xs[i+1],10.5,6.25],[xs[i],10.5,6.25]],'stone')
    # Deep recess and stone reveals, not a black decal over the wall.
    opening=[[-.55,11.6,1.6],[3.35,11.6,1.6],[3.35,11.6,3.45]]
    opening += [[cx+r*math.cos(a),11.6,cz+r*math.sin(a)] for a in t]
    face(opening,'black')
    box(-.85,10.15,1.55,-.55,10.55,3.45)
    box(3.35,10.15,1.55,3.65,10.55,3.45)
    for i in range(15):
        a,b=i*np.pi/15,(i+1)*np.pi/15
        q=[[cx+rr*math.cos(th),10.12,cz+rr*math.sin(th)] for rr,th in [(r,a),(r,b),(r+.34,b),(r+.34,a)]]
        face(q,'stone'); line(q+[q[0]],1.0)
    # Wall caps and posts.
    for x0,x1 in [(-10,-.85),(3.65,10)]:
        masonry(x0,x1,10.5,.04,6.15)
    for x in np.arange(-10,10,1.08): box(x,10.25,6.25,x+1.06,11.18,6.48)
    # Left side wall steps down toward the viewer.
    box(-10,-5,0,-9.4,10.5,2.0)
    for y in np.arange(-5,10.5,1.1): box(-10.12,y,2.,-9.3,min(y+1.07,10.5),2.18)
    # The broad stair meets the raised doorway threshold.
    for i in range(9):
        y=5.1+i*.60; z=(i+1)*1.6/9
        box(-.4,y,0,3.2,10.5,z)
        line([[-.4,y-.012,z-.035],[3.2,y-.012,z-.035]],1.15)
    # Stone garden beds.
    for x0,x1 in [(-8.8,-4.0),(4.9,8.7)]:
        for y0,y1 in [(3.,6.),(7.0,9.4)]:
            box(x0,y0,0,x1,y0+.24,.34)
            box(x0,y1-.24,0,x1,y1,.34)
            box(x0,y0,.0,x0+.24,y1,.34)
            box(x1-.24,y0,0,x1,y1,.34)
            face([[x0+.25,y0+.25,.12],[x1-.25,y0+.25,.12],[x1-.25,y1-.25,.12],[x0+.25,y1-.25,.12]],'soil')
            for _ in range(130):
                x=RNG.uniform(x0+.3,x1-.3); y=RNG.uniform(y0+.3,y1-.3); h=RNG.uniform(.08,.33)
                line([[x-.06,y,.13],[x,y,.13+h],[x+.08,y+.03,.15]],.7,'grass')
    # Dry fountain: base, curved basin, inner bowl, stem, finial.
    fx,fy=-2.3,.25
    revolve(fx,fy,[(2.1,.03),(2.1,.20),(1.94,.26),(1.75,.26)],n=60)
    revolve(fx,fy,[(.85,.26),(.85,.39),(.50,.48),(.40,.88),(.63,1.05),
                      (1.65,1.28),(1.81,1.53),(1.83,1.65),(1.65,1.67),
                      (1.51,1.35),(.35,1.18)],n=60)
    revolve(fx,fy,[(.25,1.19),(.23,2.0),(.35,2.08),(.35,2.18),(.18,2.28)],n=32)
    ellipsoid([fx,fy,2.46],[.24,.24,.25],'stone',n=20,m=9)
    # Flagstones describe a route through the garden rather than a flat grid.
    for j in range(9):
        y=-5+j*1.06; center=1.5-.15*math.sin(y*.7)
        for i in range(3):
            x=center+(i-1)*.90+(j%2)*.18
            q=np.array([[x-.40,y-.42,.025],[x+.42,y-.40,.025],[x+.39,y+.43,.025],[x-.43,y+.40,.025]])
            line(np.vstack([q,q[0]]),.77,'paving')
    # Low foreground debris and grasses break the geometrical floor plane.
    for _ in range(160):
        x=RNG.uniform(-9,9); y=RNG.uniform(-6,4)
        if -.6<x<3.6 or (x-fx)**2+(y-fy)**2<5: continue
        z=RNG.uniform(.06,.22)
        line([[x-.05,y,.015],[x,y,.015+z],[x+.06,y,.02]],.65,'grass')
    # Gnarled tree on the right. Branches are tapered solids.
    branch([[6.9,-.7,0],[6.7,-.55,1.2],[6.85,-.38,2.5],[6.48,-.2,3.6],[6.6,.1,5.2]], [.35,.3,.25,.18,.06])
    branch([[6.8,-.4,2.2],[5.9,-.3,3.1],[5.5,-.1,4.0],[4.7,.1,4.6]],[.21,.15,.10,.025])
    branch([[6.6,-.2,3.6],[7.6,-.15,4.1],[8.1,.1,5.1]],[.17,.10,.025])
    for x,y,z,rx,ry,rz in [(5.1,.1,4.8,1.2,.8,.85),(6.2,.3,5.4,1.35,1.,.95),
                          (7.5,.3,5.4,1.2,.85,1.0),(6.8,.3,6.3,1.1,.8,.8),
                          (8.0,.3,4.6,.9,.7,.7)]: ellipsoid([x,y,z],[rx,ry,rz])
    for j in range(9):
        a=j*2*np.pi/9
        line([[6.9,-.7,.12],[6.9+.6*np.cos(a),-.7+.6*np.sin(a),.04],
              [6.9+1.1*np.cos(a),-.7+1.1*np.sin(a),.025]],.95,'root')
    # Two cypresses, with long marks following the volume.
    for x,y,h in [(-7.5,5.8,6.2),(-8.0,8.7,5.5)]:
        branch([[x,y,.12],[x+.06,y,h*.8]],[.15,.045])
        ellipsoid([x,y,h*.58],[.70,.65,h*.43])
    # Tower beyond the enclosure, sparse distant lines.
    box(-6.9,20,0,-3.8,23,10.,'distant')
    for z in [6.7,8.9]: box(-7.,19.9,z,-3.7,23.1,z+.14,'distant')
    for x in [-6.9,-5.75,-4.6]: box(x,20,10.,x+.6,23,10.7,'distant')
    # Narrow slits on the visible facade.
    for x in [-6.2,-4.8]: box(x,19.96,7.6,x+.28,19.98,8.4,'black')
    # Mountains are distant 3D profiles; they still use the same camera.
    xs=np.linspace(-35,34,190)
    zz=3.8+1.6*np.sin(xs*.18)+.6*np.sin(xs*.60)+.28*np.sin(xs*1.8)
    for y,delta in [(37,2.6),(31,0)]:
        line(np.column_stack([xs,np.full(len(xs),y),zz+delta]),.72,'distant',.55)
        for i in range(0,len(xs)-2,2):
            x=xs[i]; z=zz[i]+delta
            line([[x,y,z],[x+.25,y,z-.30],[x+.5,y,z-.52]],.50,'distant',.45)
    # Cloud ribbons occupy world space, with deliberately sparse cuts.
    for cx,cz,rr in [(-7,12.8,5),(12,12.1,4.5)]:
        for j in range(6):
            t=np.linspace(-1,1,90); x=cx+t*rr
            z=cz+.4*np.sin(t*4)+.16*np.sin(t*11)-j*.13
            line(np.column_stack([x,np.full(len(x),33),z]),.54,'sky',.6)

def depth_map():
    zbuf=np.full((H,W),np.inf,np.float32)
    for f in FACES:
        p=proj(f.p)
        for i in range(1,len(p)-1):
            a,b,c=p[[0,i,i+1]]
            if min(a[2],b[2],c[2])<1: continue
            x0=max(0,int(np.floor(min(a[0],b[0],c[0])))); x1=min(W-1,int(np.ceil(max(a[0],b[0],c[0]))))
            y0=max(0,int(np.floor(min(a[1],b[1],c[1])))); y1=min(H-1,int(np.ceil(max(a[1],b[1],c[1]))))
            if x1<x0 or y1<y0: continue
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-9: continue
            yy,xx=np.mgrid[y0:y1+1,x0:x1+1]
            u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
            w=1-u-v
            mask=(u>=-.001)&(v>=-.001)&(w>=-.001)
            iz=u/a[2]+v/b[2]+w/c[2]
            z=np.divide(1.,iz,out=np.full_like(iz,np.inf),where=iz>0)
            region=zbuf[y0:y1+1,x0:x1+1]
            np.minimum(region,np.where(mask,z,np.inf),out=region)
    return zbuf

def hatch_faces():
    for f in FACES:
        if f.mat in ('leaf','black'): continue
        p=f.p
        u=p[1]-p[0]; un=np.linalg.norm(u)
        if un<1e-8: continue
        u/=un
        n=np.cross(u,p[-1]-p[0]); nn=np.linalg.norm(n)
        if nn<1e-8: continue
        n/=nn
        if np.dot(n,EYE-p.mean(0))<0: n=-n
        v=np.cross(n,u)
        uv=np.column_stack([(p-p[0])@u,(p-p[0])@v])
        light=max(0,float(n@LIGHT))
        shade=.30+.70*(1-light)
        distance=np.linalg.norm(p.mean(0)-EYE)
        if f.mat=='distant': spacing=.26; alpha=.56
        elif f.mat=='earth': spacing=.24; alpha=.55
        elif f.mat=='soil': spacing=.12; alpha=.8
        elif f.mat=='bark': spacing=.17; alpha=.70
        else: spacing=.105+.13*light; alpha=.78
        # Material coordinates, clipped to each surface before projection.
        angles=[.30] if f.mat=='earth' else [.88]
        if shade>.89 and f.mat not in ('earth','distant','stone'): angles.append(-.68)
        for angle in angles:
            d=np.array([np.cos(angle),np.sin(angle)]); perp=np.array([-d[1],d[0]])
            vals=uv@perp
            for k in np.arange(vals.min()+spacing*.4,vals.max(),spacing):
                hits=[]
                for a,b,va,vb in zip(uv,np.roll(uv,-1,axis=0),vals,np.roll(vals,-1)):
                    if (va<=k<vb) or (vb<=k<va): hits.append(a+(b-a)*(k-va)/(vb-va))
                if len(hits)<2: continue
                hits=sorted(hits,key=lambda x:x@d)
                a,b=hits[0],hits[-1]
                length=np.linalg.norm(b-a)
                if length<.025: continue
                # Small irregularity and broken endpoints, in surface units.
                trim=min(.07,length*.13)
                a+=d*RNG.uniform(0,trim); b-=d*RNG.uniform(0,trim)
                ts=np.linspace(0,1,max(3,int(length/.15)+1))
                q=a[None,:]+ts[:,None]*(b-a)
                q+=RNG.normal(0,.007,(len(ts),1))*perp
                points=p[0]+q[:,0,None]*u+q[:,1,None]*v+n*.007
                if f.mat=='stone':
                    # The stone is cut in patches. Preserve irregular white
                    # intervals instead of covering every plane in a lattice.
                    if abs(n[2])<.35 and length>.65:
                        steps=max(2,int(length/.25))
                        ts=np.linspace(0,1,steps)
                        samples=points[0]+ts[:,None]*(points[-1]-points[0])
                        run=[]
                        for pt in samples:
                            x,y,z=pt
                            mottled=.5+.5*np.sin(x*2.1+np.sin(z*3))*np.cos(z*1.7+y*.4)
                            base=np.exp(-abs(z)/.6)
                            coping=np.exp(-abs(z-6.2)/.32)
                            keep=mottled>(.66-.25*base-.14*coping)
                            if keep:run.append(pt)
                            else:
                                if len(run)>1:line(run,.68,'hatch',alpha)
                                run=[]
                        if len(run)>1:line(run,.68,'hatch',alpha)
                        continue
                    if RNG.random()<.48:continue
                # Interrupted ground scratches and distant cuts.
                if f.mat=='earth':
                    if RNG.random()<.40: continue
                    j=int(RNG.integers(0,max(1,len(points)-3))); points=points[j:j+max(3,int(len(points)*.17))]
                line(points,.68 if len(angles)==1 else .60,'hatch',alpha)

def visible_paths(p,zbuf):
    # Sample in world coordinates, then compare with perspective-correct depth.
    out=[]; run=[]
    for a,b in zip(p,p[1:]):
        pa,pb=proj([a,b]); length=np.linalg.norm(pa[:2]-pb[:2])
        n=max(2,min(2500,int(length/1.1)+2))
        q=proj(a+np.linspace(0,1,n)[:,None]*(b-a))
        for x,y,z in q:
            ix,iy=int(round(x)),int(round(y))
            ok=1<=ix<W-1 and 1<=iy<H-1 and z>1
            if ok:
                depth=np.max(zbuf[iy-1:iy+2,ix-1:ix+2])
                ok=z<=depth+.045
            if ok:
                if not run or np.hypot(run[-1][0]-x,run[-1][1]-y)>.6: run.append((x,y))
            elif len(run)>1: out.append(run); run=[]
            else: run=[]
    if len(run)>1: out.append(run)
    return out

def simplify(p,tolerance=.18):
    if len(p)<3:return list(p)
    # Ramer-Douglas-Peucker, preserving genuinely curved marks.
    p=np.asarray(p); a,b=p[0],p[-1]; ab=b-a
    if np.dot(ab,ab)<1e-12:
        j=int(np.argmax(np.sum((p-a)**2,axis=1)))
        if j in (0,len(p)-1):return [p[0],p[-1]]
        return simplify(p[:j+1],tolerance)[:-1]+simplify(p[j:],tolerance)
    dist=np.abs(ab[0]*(p[:,1]-a[1])-ab[1]*(p[:,0]-a[0]))/np.linalg.norm(ab)
    j=int(np.argmax(dist))
    if dist[j]<=tolerance:return [p[0],p[-1]]
    return simplify(p[:j+1],tolerance)[:-1]+simplify(p[j:],tolerance)

def render():
    print('Building the 3D scene',flush=True); scene()
    print(f'{len(FACES)} surfaces; computing depth',flush=True)
    zbuf=depth_map()
    print('Drawing material hatches',flush=True); hatch_faces()
    # Projected ground shadows: attached to the modeled forms.
    for x,y,r,z in [(-2.3,.25,1.8,1.5),(6.9,-.7,1.4,4.5),(-7.5,5.8,.6,4)]:
        dx,dy=-LIGHT[0]*z/LIGHT[2],-LIGHT[1]*z/LIGHT[2]
        for j in np.arange(-r,r,.075):
            half=np.sqrt(max(0,r*r-j*j))
            line([[x+j,y-.1,.03],[x+j+dx,y+half+dy,.03]],.62,'shadow',.72)
    print(f'{len(LINES)} candidate paths; resolving visibility',flush=True)
    body=[]; counts={}
    # Flat paper fills hide distant recesses behind nearer solids. All surface
    # tone still comes from strokes; polygon edges are never printed as a mesh.
    for f in sorted(FACES,key=lambda f:float(proj(f.p)[:,2].mean()),reverse=True):
        q=proj(f.p); pts=' '.join(f'{x:.2f},{y:.2f}' for x,y,z in q)
        fill=INK if f.mat=='black' else 'white'
        body.append(f'<polygon points="{pts}" fill="{fill}" stroke="none"/>')
    for p,width,kind,alpha in LINES:
        for run in visible_paths(p,zbuf):
            q=simplify(run)
            if len(q)<2:continue
            d='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in q)
            body.append(f'<path d="{d}" stroke-width="{width:.2f}" opacity="{alpha:.2f}"/>')
            counts[kind]=counts.get(kind,0)+1
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<title>Hortus Intervallorum: fixed-camera modeled engraving study</title>
<desc>Procedural 3D scene, perspective projection, depth-tested surface marks. Seed 1943.</desc>
<rect width="100%" height="100%" fill="white"/>
<g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">{''.join(body)}</g></svg>'''
    (OUT/'01-garden-engraved.svg').write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/'01-garden-engraved.png'),output_width=W,output_height=H)
    np.savez_compressed(OUT/'scene-depth.npz',depth=zbuf)
    metadata=dict(seed=1943,camera=dict(eye=EYE.tolist(),target=TARGET.tolist(),focal=FOCAL),
                  resolution=[W,H],faces=len(FACES),candidate_paths=len(LINES),visible_paths=counts,
                  method='Perspective 3D meshes, reciprocal-depth rasterization, depth-tested vector paths, per-surface hatching')
    (OUT/'scene.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata),flush=True)

def export_mesh():
    chunks=['# Hortus Intervallorum / editable construction mesh',
            '# Units arbitrary; Z up. Camera is recorded in output/scene.json.']
    count=0
    for f in FACES:
        chunks.append('g '+f.mat)
        for p in f.p:chunks.append('v '+' '.join(f'{v:.6f}' for v in p))
        chunks.append('f '+' '.join(str(count+i+1) for i in range(len(f.p))))
        count+=len(f.p)
    (OUT/'garden-construction.obj').write_text('\n'.join(chunks)+'\n')

def treatments():
    print('Applying the existing Codex treatments',flush=True)
    rgb=np.asarray(Image.open(OUT/'01-garden-engraved.png').convert('RGB'))
    tone=1-rgb.mean(2)/255
    yy,xx=np.mgrid[:H,:W]; xn=xx/W; yn=yy/H
    # The mask deliberately avoids the central fountain, stair and doorway.
    edge=(np.clip((np.abs(xn-.50)-.13)/.21,0,1)*np.clip((yn-.25)/.35,0,1))
    foot=np.clip((yn-.66)/.20,0,1)*.85
    patch=np.maximum(edge,foot)
    support=gaussian_filter(binary_dilation(tone>.15,iterations=10).astype(float),5)
    mask=np.clip(patch*support,0,1)
    guard=np.maximum.reduce([
        (((xn-.39)/.145)**2+((yn-.68)/.14)**2<1),
        (((xn-.575)/.115)**2+((yn-.52)/.19)**2<1),
    ])
    shoulder=gaussian_filter(guard.astype(float),14)
    mask*=1-np.clip(shoulder*1.3,0,1)
    mask[guard]=0
    field=growth.simulate(tone,1943)
    variants=[('02-garden-flow',.18,.65),('03-garden-edge-grain',.82,.90)]
    stats=[]
    for name,cornmeal,amount in variants:
        m=mask*amount
        material,counts=growth.render_material(rgb,field,m,1943,cornmeal,display_width=360)
        replacement=.20*rgb+.80*material
        result=np.uint8(np.clip(np.rint(rgb*(1-m[...,None])+replacement*m[...,None]),0,255))
        # Exact zero-mask preservation, checked before any page scaling.
        assert np.array_equal(result[mask==0],rgb[mask==0])
        Image.fromarray(result).save(OUT/f'{name}.png',optimize=True)
        stats.append(dict(name=name,cornmeal=cornmeal,amount=amount,**counts,
                          protected_pixels=int((mask==0).sum()),protected_pixels_identical=True))
    Image.fromarray(np.uint8(mask*255)).save(OUT/'treatment-mask.png')
    (OUT/'treatments.json').write_text(json.dumps(stats,indent=2))
    print(json.dumps(stats),flush=True)

def pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    import io
    fp=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')
    if fp.exists():pdfmetrics.registerFont(TTFont('StudySerif',str(fp)))
    serif='StudySerif' if fp.exists() else 'Times-Roman'
    # All pages are the same 7 x 10 inch reading format.
    pw,ph=504,720
    c=canvas.Canvas(str(OUT/'Garden_Engraving_Study.pdf'),pagesize=(pw,ph),pageCompression=1)
    c.setTitle('Hortus Intervallorum - Modeled scenery study')
    c.setAuthor('Josiah Alan-Lee / ChatGPT-Codex')
    variants=[('01-garden-engraved','I. Engraved construction','Projected geometry and material hatches.'),
              ('02-garden-flow','II. Restrained flow','Existing image-guided Physarum strokes at selected margins.'),
              ('03-garden-edge-grain','III. Developing sketch','Physarum and cornmeal at the same margins.')]
    for index,(name,title,caption) in enumerate(variants):
        c.setFillColor(HexColor('#ede6d4'));c.rect(0,0,pw,ph,fill=1,stroke=0)
        c.setFillColor(HexColor('#332d24'));c.setFont(serif,10)
        c.drawCentredString(pw/2,ph-55,'HORTUS INTERVALLORUM')
        c.setFont(serif,18);c.drawCentredString(pw/2,ph-89,title)
        # 5.9 inch plate, matching a plausible inset illustration in the book.
        im=Image.open(OUT/f'{name}.png').convert('RGB')
        a=np.asarray(im,dtype=float)/255
        paper=np.array([237,230,212]); tinted=np.uint8(np.clip(a*paper,0,255))
        bio=io.BytesIO();Image.fromarray(tinted).save(bio,format='PNG')
        iw=426;ih=iw*H/W;iy=ph-145-ih
        c.drawImage(ImageReader(bio),39,iy,width=iw,height=ih)
        c.setStrokeColor(HexColor('#665a42'));c.setLineWidth(.35);c.rect(39,iy,iw,ih)
        c.setFont(serif,10);c.drawCentredString(pw/2,iy-28,caption)
        c.setFont(serif,8)
        c.drawCentredString(pw/2,69,'Standalone scenery proof / same camera, geometry, and seed throughout')
        c.drawCentredString(pw/2,49,f'{index+1} / 4')
        c.showPage()
    # Crops expose the mark behavior at a readable size.
    c.setFillColor(HexColor('#ede6d4'));c.rect(0,0,pw,ph,fill=1,stroke=0)
    c.setFillColor(HexColor('#332d24'));c.setFont(serif,17);c.drawString(39,665,'Construction and treatment details')
    for i,(name,title,_) in enumerate(variants):
        im=Image.open(OUT/f'{name}.png').convert('RGB')
        crop=im.crop((900,540,1530,960))
        a=np.array(crop)/255; tinted=np.uint8(a*np.array([237,230,212]))
        bio=io.BytesIO();Image.fromarray(tinted).save(bio,format='PNG')
        y=445-i*165
        c.setFont(serif,10);c.drawString(39,y+148,title)
        c.drawImage(ImageReader(bio),39,y,width=201.6,height=134.4)
        c.setFont(serif,9)
        txt=c.beginText(261,y+114);txt.setLeading(14)
        notes=[['Depth-tested vector base.', 'Stone, bark, soil, and leaves', 'use distinct drawing rules.'],
               ['Flow replaces a restrained', 'fraction of peripheral marks.', 'The central subjects are guarded.'],
               ['More interrupted strokes', 'and grain at the same edge.', 'The focal objects stay intact.']][i]
        for s in notes:txt.textLine(s)
        c.drawText(txt)
    c.setFont(serif,8);c.drawCentredString(pw/2,49,'4 / 4');c.save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--treatments-only',action='store_true');args=p.parse_args()
    if not args.treatments_only:render();export_mesh()
    treatments();pdf()
