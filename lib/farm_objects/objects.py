"""Seeded farm remnants: real mesh gaps plus surface-attached pen marks.

Object proportions are invented composites, not reconstructions of a manufacturer.
Coordinates are metres, Z up. A tractor/wagon faces +X; a barn's door faces -Y.
"""
from __future__ import annotations
from dataclasses import dataclass
import importlib.util
import math
from pathlib import Path
import numpy as np

# Reuse the repository's maintained primitives; do not fork their winding fixes.
_PATH = Path(__file__).resolve().parents[2] / 'studies/infernal-landscape/geometry.py'
_SPEC = importlib.util.spec_from_file_location('_farm_shared_geometry', _PATH)
G = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(G)
KINDS = ('barn', 'tractor', 'disk_harrow', 'hay_rake', 'wagon')


def _rng(seed, component):
    """Stable independent streams: increased wear does not change the chassis."""
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(component)]))


@dataclass
class FarmObject:
    kind: str
    seed: int
    decay: float
    builder: object
    parameters: dict

    def record(self):
        return dict(self.builder.evaluate(), strokes=self.builder.strokes,
                    colors=self.builder.colors, metadata=dict(kind=self.kind, seed=self.seed,
                    decay=self.decay, parameters=self.parameters, units='metres', up='Z'))

    def add_to(self, builder, location=(0, 0, 0), rotation=0., scale=1., name=None):
        """Place in a SceneBuilder (NumPy or Blender), sharing its visibility.

        rotation is radians about Z. Scale is positive and uniform. Materials
        use the existing SceneBuilder slots; stroke widths stay in page mm.
        """
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError('scale must be positive and finite')
        location = np.asarray(location, float)
        if location.shape != (3,) or not np.isfinite(location).all() or not np.isfinite(rotation):
            raise ValueError('finite XYZ location and rotation required')
        c, s = np.cos(rotation), np.sin(rotation)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        transform = lambda p: np.asarray(p) @ R.T * scale + location
        prefix = name or f'{self.kind}-{self.seed}'
        for ob in self.builder.objects:
            builder.mesh(prefix + '/' + ob['name'], transform(ob['verts']), ob['faces'],
                         ob['mat'], hatch=ob['hatch'], kind=ob['kind'])
        for stroke in self.builder.strokes:
            builder.ink(prefix + '/' + stroke['name'], transform(stroke['pts']),
                        mm=stroke['width'] / G.PX_PER_MM, pen=stroke['ink'])


def _solid(b, name, vertices, faces, mat=3, hatch=True):
    v = np.asarray(vertices, float)
    # Generated closed solids are consistently wound; correct global reversal.
    volume = sum(np.dot(v[f[0]], np.cross(v[f[j]], v[f[j+1]]))
                 for f in faces for j in range(1, len(f)-1)) / 6
    if volume < 0:
        faces = [tuple(reversed(f)) for f in faces]
    return b.mesh(name, v, faces, mat, hatch=hatch, kind='sheet')


def _rust(b, name, origin, u, v, rng, decay, density=16):
    """Clustered pit loops and flaking arcs on a planar metal surface (pen 1)."""
    origin, u, v = map(lambda x: np.asarray(x, float), (origin, u, v))
    n = np.cross(u, v); n /= max(np.linalg.norm(n), 1e-9)
    clusters = rng.uniform(.1, .9, (4, 2))
    for i in range(density):
        uv = np.clip(clusters[i % 4] + rng.normal(0, .09, 2), .035, .965)
        threshold = rng.random()
        radius = rng.uniform(.012, .035)
        angle = rng.uniform(0, 2*np.pi)
        ts = np.linspace(angle, angle + rng.uniform(3.6, 6.28), 7)
        rr = radius * rng.uniform(.65, 1.35, len(ts))
        if threshold > decay:
            continue
        p = origin + (uv[0] + rr*np.cos(ts))[:, None]*u + (uv[1]+rr*np.sin(ts))[:, None]*v + n*.003
        b.ink(name + ' flake', p, .12, 1)


def _plank(b, name, origin, across, up, rng, decay, mat=2):
    """Separate warped board, ragged rot at its foot; no opaque backing wall."""
    o, u, v = map(lambda x: np.asarray(x, float), (origin, across, up))
    n = np.cross(u, v); n /= np.linalg.norm(n)
    loss = rng.uniform(.0, .18) * decay
    warp = n * rng.uniform(-.035, .035) * decay
    across_pos=(0.,.34,.63,1.)
    feet=(loss,loss*.45,loss+.025*decay,loss*.6)
    front=[o+u*x+(v+warp)*z for x,z in zip(across_pos,feet)]
    front += [o+u*x+v+warp for x in reversed(across_pos)]
    thick = .035
    verts = front + [p-n*thick for p in front]
    # Three coplanar quads exactly represent the ragged boundary. A fan over
    # the concave whole board would incorrectly occlude its missing slivers.
    panels=[(0,1,6,7),(1,2,5,6),(2,3,4,5)]
    faces=panels+[tuple(i+8 for i in reversed(f)) for f in panels]
    faces += [(i,i+8,(i+1)%8+8,(i+1)%8) for i in range(8)]
    _solid(b, name, verts, faces, mat, False)
    for j in range(3):
        x = (j+1)/4 + rng.uniform(-.055, .055)
        ts = np.linspace(loss+.025, .97, 14)
        xx = x + .025*np.sin(ts*15+rng.uniform(0,6)) + .01*np.sin(ts*39)
        p = o + xx[:,None]*u + ts[:,None]*v + ts[:,None]*warp + n*.004
        b.ink(name+' grain', p, .09)
    if rng.random() < decay*.75:
        ts = np.linspace(loss, min(.85, loss+rng.uniform(.15,.48)), 9)
        x = .5 + np.cumsum(rng.uniform(-.035,.035,len(ts)))
        b.ink(name+' split', o+x[:,None]*u+ts[:,None]*v+n*.005, .13)
    for t in (.16, .87):
        p=o+u*.5+v*t+n*.006
        b.ink(name+' nail', [p-u*.018, p+u*.018], .13)


def _wheel(b, name, x, y, radius, width, rng, decay, rubber=True):
    """Hollow wheel with 3D hub/spokes. Tire flattening keeps its foot on Z=0."""
    z = radius * (1-.13*decay) if rubber else radius
    count = 36
    if rubber:
        profile = [(-.45,.54),(-.55,.73),(-.44,.94),(-.24,1.),(.24,1.),(.44,.94),(.55,.73),(.45,.54)]
    else:
        profile = [(-.5,.88),(-.5,1.),(.5,1.),(.5,.88)]
    vs=[]
    for yy, rr in profile:
        for t in np.arange(count)*2*np.pi/count:
            vs.append((x+radius*rr*np.cos(t), y+width*yy, max(0., z+radius*rr*np.sin(t))))
    fs=[]
    for j in range(len(profile)):
        for i in range(count):
            fs.append((j*count+i,j*count+(i+1)%count,((j+1)%len(profile))*count+(i+1)%count,((j+1)%len(profile))*count+i))
    _solid(b,name+' tire' if rubber else name+' rim',vs,fs,2 if rubber else 3,False)
    b.beam(name+' hub',(x,y-width*.58,z),(x,y+width*.58,z),radius*.17,3,12)
    if rubber:
        # Surface curves rather than dozens of boxes: legible tractor chevrons.
        for t in np.arange(28)*2*np.pi/28:
            for side in (-1,1):
                pts=[]
                for q in np.linspace(0,1,5):
                    a=t+.16*q
                    rr=radius*(1.004-.055*q*q)
                    pts.append((x+rr*np.cos(a),y+side*width*.43*q,max(.003,z+rr*np.sin(a))))
                b.ink(name+' tread',pts,.16)
    for side in (-1,1):
        yy = y+side*width*.46
        for r in ([.56,.70] if rubber else [.91]):
            ts=np.linspace(0,2*np.pi,73)
            b.ink(name+' sidewall',np.c_[x+radius*r*np.cos(ts),np.full(len(ts),yy),np.maximum(.004,z+radius*r*np.sin(ts))],.12)
        if rubber:
            for i,t in enumerate(np.arange(42)*2*np.pi/42):
                # Sidewall's actual lathe profile rises from .54R at .45W
                # through .73R at .55W to .94R at .44W.
                rr=np.linspace(.57,.91,9)
                lateral=np.interp(rr,[.54,.73,.94],[.45,.55,.44])*width+.003
                bend=t+.012*np.sin(rr*19+i)*decay
                p=np.c_[x+radius*rr*np.cos(bend),y+side*lateral,np.maximum(.004,z+radius*rr*np.sin(bend))]
                b.ink(name+' rubber checking',p,.10)
        for t in np.arange(10)*2*np.pi/10:
            # The spokes are actual occluders visible through the wheel opening.
            a=(x+radius*.17*np.cos(t),y,z+radius*.17*np.sin(t))
            c=(x+radius*(.56 if rubber else .91)*np.cos(t),yy,z+radius*(.56 if rubber else .91)*np.sin(t))
            b.beam(name+' spoke',a,c,.018 if rubber else .014,3,4,False)
    return z


def _barn(b, shape, wear, d):
    w=shape.uniform(4.6,5.7); length=shape.uniform(6.4,8.8); h=shape.uniform(3.,3.6)
    gambrel=bool(shape.integers(2)); rise=shape.uniform(1.8,2.4)
    # Same smooth sag field affects roof covering AND rafters/purlins.
    sag=lambda y: d*.50*np.sin(np.pi*(y/length+.5))**2
    profile=[(-w/2,h),(0,h+rise),(w/2,h)]
    if gambrel: profile=[(-w/2,h),(-w*.32,h+rise*.72),(0,h+rise),(w*.32,h+rise*.72),(w/2,h)]
    for y in np.linspace(-length/2,length/2,6):
        for x in (-w/2,w/2):
            b.beam('post',(x,y,.12),(x,y,h-sag(y)),.11,2,4,False)
            b.beam('knee brace',(x,y,h-1.),(x,y+.65 if y<length/2-.7 else y-.65,h-sag(y)),.075,2,4,False)
        for (x,z),(X,Z) in zip(profile[:-1],profile[1:]):
            b.beam('rafter',(x,y,z-sag(y)),(X,y,Z-sag(y)),.085,2,4,False)
        b.beam('tie',( -w/2,y,h-sag(y)),(w/2,y,h-sag(y)),.08,2,4,False)
    for x,z in profile:
        ys=np.linspace(-length/2,length/2,10)
        for a,c in zip(ys[:-1],ys[1:]): b.beam('purlin',(x,a,z-sag(a)),(x,c,z-sag(c)),.055,2,4,False)
    # Board thresholds are fixed by seed. Decay removes a nested subset.
    missing=0; total=0
    for side in (-1,1):
        n=int(length/.23)
        for i in range(n):
            y=-length/2+i*length/n; total+=1
            threshold=wear.random()
            # Side-specific outward normal by choosing board orientation.
            if threshold < d*.37: missing+=1; continue
            origin=(side*w/2,y if side>0 else y+length/n*.93,.12)
            across=(0,side*length/n*.93,0)
            _plank(b,'siding',origin,across,(0,0,h-.15-sag(y)),_rng(991+i+(0 if side>0 else 500)+int(b.A['seed']),4),d)
    for end in (-1,1):
        n=int(w/.23)
        for i in range(n):
            x=-w/2+i*w/n; xc=x+w/n/2
            roofz=np.interp(xc,[p[0] for p in profile],[p[1] for p in profile])
            bottom=2.45 if abs(xc)<1.05 and end==-1 else .12
            if end==-1 and abs(xc)<.36: bottom=max(bottom,h+.5) # loft opening
            total+=1
            if wear.random()<d*.18: missing+=1;continue
            if bottom>=roofz-.03:continue
            _plank(b,'end board',(x if end<0 else x+w/n*.94,end*length/2,bottom),
                   (-end*w/n*.94,0,0),(0,0,roofz-bottom),_rng(int(b.A['seed'])+1000+i+100*(end+1),5),d)
    # The open doorway has no white/black masking polygon.
    for x in (-1.09,1.09): b.beam('door jamb',(x,-length/2-.04,.1),(x,-length/2-.04,2.55),.075,2,4,False)
    b.beam('door rail',(-1.5,-length/2-.10,2.63),(1.5,-length/2-.10,2.63),.035,3,6)
    # A remaining sliding door panel, pushed partly aside.
    for i in range(5):
        x=1.08+i*.22
        _plank(b,'sliding door',(x,-length/2-.12,.13),(.20,0,0),(0,0,2.3),_rng(int(b.A['seed'])+i,9),d)
    holes=0
    for section,((x,z),(X,Z)) in enumerate(zip(profile[:-1],profile[1:])):
        segments=14
        for i in range(segments):
            y=-length/2+i*length/segments; Y=y+length/segments*.97
            if wear.random()<d*.30: holes+=1; continue
            # Four corners remain coplanar even while the roof sags along Y.
            p=[(x,y,z-sag(y)+.06),(X,y,Z-sag(y)+.06),(X,Y,Z-sag(Y)+.06),(x,Y,z-sag(Y)+.06)]
            # Upper normal points into the sky.
            if G.newell_normal(p)[2]<0: p=p[::-1]
            b.mesh('roof sheet',p,[(0,1,2,3)],4,False)
            p=np.asarray(p)
            for t in (.12,.38,.65,.88):
                b.ink('roof rib',[p[0]*(1-t)+p[3]*t+np.array([0,0,.005]),p[1]*(1-t)+p[2]*t+np.array([0,0,.005])],.10)
            _rust(b,'roof rust',p[0],p[1]-p[0],p[3]-p[0],_rng(int(b.A['seed'])+section*99+i,6),d,10)
    # Fallen boards follow the same seed, but become longer/more numerous with wear.
    for i in range(12):
        x=wear.uniform(-w*.7,w*.7); y=wear.uniform(-length*.7,length*.65); t=wear.uniform(0,6.28)
        if i/12>d: continue
        a=np.array([x,y,.08]); u=np.array([np.cos(t),np.sin(t),0])*.17
        v=np.array([-np.sin(t),np.cos(t),.015])*wear.uniform(.6,1.8)
        _plank(b,'fallen plank',a,u,v,_rng(int(b.A['seed'])+i,19),d)
    return dict(width=round(w,3),length=round(length,3),height=round(h+rise,3),roof='gambrel' if gambrel else 'gable',missing_boards=missing,board_slots=total,missing_roof_sheets=holes,max_sag=round(d*.50,3))


def _tractor(b,shape,wear,d):
    wheelbase=shape.uniform(1.85,2.35); track=shape.uniform(1.42,1.7); r=shape.uniform(.76,.9)
    rear=-wheelbase*.48; front=wheelbase*.52; hoodz=r+shape.uniform(.38,.53)
    for side in (-1,1):
        rz=_wheel(b,'rear wheel',rear,side*track/2,r,.38,wear,d)
        fz=_wheel(b,'front wheel',front,side*track*.42,r*.49,.19,wear,d)
    b.beam('rear axle',(rear,-track/2,rz),(rear,track/2,rz),.10,3,10)
    b.beam('front axle',(front,-track*.42,fz),(front,track*.42,fz),.07,3,8)
    b.box('chassis',(rear-.28,-.25,.45),(front+.25,.25,.65),3)
    b.box('engine',(rear+.58,-.29,.65),(front+.07,.29,hoodz-.15),3)
    # Rounded hood cross-section, extruded along X; no branded tractor grille.
    section=[(-.35,.82),(-.35,hoodz-.12),(-.25,hoodz),(.25,hoodz),(.35,hoodz-.12),(.35,.82)]
    verts=[(x,y,z) for x in (rear+.60,front+.3) for y,z in section]
    n=len(section); faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    _solid(b,'hood',verts,faces,3,True)
    for side in (-1,1):
        _rust(b,'hood corrosion',(rear+.64,side*.355,.85 if side<0 else hoodz-.13),(wheelbase-.38,0,0),(0,0,(hoodz-.98)*(-side)),wear,d,100)
        for x in np.linspace(rear+.72,front-.15,7):
            b.ink('engine vent',[(x,side*.357,.88),(x+.04,side*.357,hoodz-.2)],.16)
        # Curved fender follows tire top, missing fragments at greater decay.
        ts=np.linspace(.15,np.pi-.1,12); yy=side*(track/2-.13)
        for i,(a,c) in enumerate(zip(ts[:-1],ts[1:])):
            if wear.random()<d*.13:continue
            pts=[(rear+(r+.10)*np.cos(t),y,rz+(r+.10)*np.sin(t)) for y,t in [(yy,a),(yy,c),(yy+side*.34,c),(yy+side*.34,a)]]
            if G.newell_normal(pts)[2]<0:pts=pts[::-1]
            b.mesh('fender',pts,[(0,1,2,3)],3,False)
    # Grill is an open-looking set of bars over a recessed dark assembly.
    for yy in np.linspace(-.26,.26,12): b.ink('radiator grille',[(front+.304,yy,.86),(front+.304,yy,hoodz-.15)],.16)
    b.beam('exhaust',(front-.43,.16,hoodz),(front-.43+d*.07,.16,hoodz+.69),.045,3,10)
    b.beam('seat pedestal',(rear,0,.64),(rear,0,1.22),.055,3,8)
    seat=[(rear-.25,-.22,1.24),(rear+.17,-.22,1.24),(rear+.17,.22,1.24),(rear-.25,.22,1.24)]
    b.mesh('seat pan',seat,[(0,1,2,3)],3,True)
    for yy in (-.1,0,.1):b.ink('seat slots',[(rear-.1,yy,1.245),(rear+.08,yy,1.245)],.12)
    stem=np.array([rear+.32,0,1.48]);b.beam('steering column',(rear+.55,0,.75),stem,.025,3,8)
    u=np.array([.13,0,.12]);v=np.array([0,.18,0]);ts=np.linspace(0,2*np.pi,37)
    b.ink('steering wheel',stem+np.cos(ts)[:,None]*u+np.sin(ts)[:,None]*v,.20)
    for t in (0,2.094,4.189):b.ink('steering spoke',[stem,stem+np.cos(t)*u+np.sin(t)*v],.13)
    b.beam('drawbar',(rear-.22,0,.48),(rear-.65,0,.30),.06,3,4)
    for side in (-1,1):
        b.beam('headlamp',(front+.22,side*.42,hoodz-.22),(front+.32,side*.42,hoodz-.22),.09,3,12)
        b.box('footplate',(rear-.15,side*.55-.09,.61),(rear+.38,side*.55+.09,.66),3)
    return dict(wheelbase=round(wheelbase,3),track=round(track,3),rear_radius=round(r,3),hood_height=round(hoodz,3),type='open-seat composite')


def _disk(b,name,center,r,angle):
    # Shallow concave steel disk, complete triangles with no filled SVG disk.
    c=np.asarray(center);u=np.array([np.cos(angle),np.sin(angle),0]);v=np.array([0,0,1]);n=np.cross(u,v)
    ts=np.arange(28)*2*np.pi/28
    vs=[c+n*r*.16]+[c+r*np.cos(t)*u+r*np.sin(t)*v for t in ts]
    b.mesh(name,vs,[(0,i+1,(i+1)%28+1) for i in range(28)],3,False)
    for q in (.72,.91):b.ink(name+' scoring ring',[c+n*r*.16*(1-q)+q*r*np.cos(t)*u+q*r*np.sin(t)*v for t in np.linspace(0,2*np.pi,57)],.11)


def _harrow(b,shape,wear,d):
    count=int(shape.integers(6,10));width=count*.25
    for y in (-.43,.43):b.beam('gang frame',(-width/2,y,.62),(width/2,y,.62),.06,3,4)
    for x in (-width*.39,0,width*.39):b.beam('frame crossbar',(x,-.43,.62),(x,.43,.62),.055,3,4)
    missing=0
    for side in (-1,1):
        for i,x in enumerate(np.linspace(-width/2,width/2,count)):
            if wear.random()<d*.09:missing+=1;continue
            y=side*.44+.14*x;angle=side*.42
            _disk(b,'concave disk',(x,y,.32),.31,angle)
            b.beam('bearing hanger',(x,y,.60),(x,y,.32),.03,3,6)
    b.beam('tongue',(0,0,.62),(width/2+1.3,0,.18),.07,3,4)
    b.ink('hitch eye',[(width/2+1.3+.09*np.cos(t),.09*np.sin(t),.18) for t in np.linspace(0,2*np.pi,25)],.16)
    return dict(disks_per_gang=count,missing_disks=missing,width=round(width,3))


def _rake(b,shape,wear,d):
    width=shape.uniform(2.8,3.5); r=shape.uniform(.58,.74)
    for side in (-1,1):_wheel(b,'rake wheel',0,side*width/2,r,.07,wear,d,False)
    b.beam('rake axle',(0,-width/2,r),(0,width/2,r),.055,3,8)
    b.beam('tooth carrier',(.3,-width/2+.1,.57),(.3,width/2-.1,.57),.045,3,6)
    missing=0
    for i,y in enumerate(np.linspace(-width/2+.14,width/2-.14,24)):
        bend=wear.uniform(-.08,.08)*d
        if wear.random()<d*.15:missing+=1;continue
        ts=np.linspace(-.2,2.05,20)
        pts=np.c_[.15+.72*np.cos(ts),y+bend*np.sin(ts*1.5),.64-.58*np.sin(ts)]
        b.ink('curved spring tooth',pts,.18)
    b.beam('rake tongue',(0,0,r),(2.4,0,.12),.055,2,4)
    b.beam('dump lever',(.15,.15,.65),(-.35,.15,1.25),.025,3,6)
    return dict(width=round(width,3),wheel_radius=round(r,3),missing_teeth=missing)


def _wagon(b,shape,wear,d):
    length=shape.uniform(2.5,3.25);width=shape.uniform(1.25,1.6)
    for x in (-length*.33,length*.33):
        for side in (-1,1):_wheel(b,'wagon wheel',x,side*(width/2+.12),.44,.14,wear,d,False)
        b.beam('wagon axle',(x,-width/2-.12,.44),(x,width/2+.12,.44),.065,3,8)
    for y in (-width*.32,width*.32):b.beam('wagon chassis',(-length/2,y,.58),(length/2,y,.58),.08,3,4)
    missing=0
    for i,x in enumerate(np.linspace(-length/2,length/2,16)):
        if wear.random()<d*.21:missing+=1;continue
        _plank(b,'deck board',(x,-width/2,.69),(length/17,0,0),(0,width,0),_rng(int(b.A['seed'])+i,22),d)
    for side in (-1,1):
        for x in (-length/2,0,length/2):b.beam('wagon stake',(x,side*width/2,.67),(x+d*.04,side*(width/2+d*.05),1.55),.035,2,4,False)
        for i,z in enumerate((.86,1.12,1.38)):
            if wear.random()<d*.22:missing+=1;continue
            _plank(b,'side slat',(-side*length/2,side*(width/2+.02),z),(0,0,.14),(side*length,0,0),_rng(int(b.A['seed'])+i+side+10,21),d)
    b.beam('wagon drawbar',(length/2,0,.55),(length/2+1.3,.2,.13),.055,2,4)
    return dict(length=round(length,3),width=round(width,3),missing_boards=missing)


def make_object(kind='barn', seed=22, decay=.65):
    if kind not in KINDS:raise ValueError(f'kind must be one of {KINDS}')
    if isinstance(seed,bool) or not isinstance(seed,(int,np.integer)) or seed<0:raise ValueError('seed must be a nonnegative integer')
    if not np.isfinite(decay) or not 0<=decay<=1:raise ValueError('decay must be between 0 and 1')
    b=G.SceneBuilder(dict(seed=int(seed)),lambda x,y:np.zeros(np.broadcast(x,y).shape))
    fn=dict(barn=_barn,tractor=_tractor,disk_harrow=_harrow,hay_rake=_rake,wagon=_wagon)[kind]
    params=fn(b,_rng(seed,1),_rng(seed,2),float(decay))
    # Each exposed steel face gets its own seed-stable corrosion stream.
    rust_rng=_rng(seed,777)
    for ob in b.objects:
        if ob['mat']!=3:continue
        for f in ob['faces']:
            if len(f)!=4:continue
            p=ob['verts'][list(f)];area=G.polygon_area(p)
            if area>.018:
                _rust(b,'steel corrosion',p[0],p[1]-p[0],p[3]-p[0],rust_rng,float(decay),max(4,min(24,int(area*32))))
    return FarmObject(kind,int(seed),float(decay),b,params)


def write_obj(asset,path):
    """Portable mesh companion; SVG-only surface marks are not OBJ geometry."""
    rec=asset.record();out=['# Farm remnants; metres, Z up; surface strokes in JSON']
    out += ['v %.6f %.6f %.6f'%tuple(v) for v in rec['vertices']]
    last=None
    for name,f in zip(rec['names'],rec['faces']):
        if name!=last:out.append('g '+name.replace(' ','_'));last=name
        out.append('f '+' '.join(str(i+1) for i in f))
    Path(path).write_text('\n'.join(out)+'\n')
