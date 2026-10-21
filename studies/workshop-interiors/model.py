"""Four workshop interiors, rebuilt from the book's recorded briefs.

Run with Blender 4.5 LTS or its official bpy wheel. PLATE selects a scene;
RENDER=0 skips the Cycles proof, never the .blend or evaluated-mesh export.
"""
from pathlib import Path
import json, math, os, random
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parent
KEY = os.environ.get('PLATE', 'empty-cabinet')
OUT = ROOT / 'output' / KEY
OUT.mkdir(parents=True, exist_ok=True)
TITLES = {
    'maintained-workshop': 'The Maintained Workshop',
    'empty-cabinet': 'The Empty Cabinet',
    'extraction-of-the-hand': 'The Extraction of the Hand',
    'office-without-a-seal': 'The Office Without a Seal',
}
if KEY not in TITLES:
    raise SystemExit(f'Unknown PLATE: {KEY}')
random.seed(271)
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
SC.name = TITLES[KEY]
W, H = 1800, (2400 if KEY in ['maintained-workshop', 'empty-cabinet'] else 2250)
STROKES, PARTS, MATERIALS = [], {}, []
PALETTE = ['#c9c0aa', '#a48a65', '#af8d4c', '#e5d7ba', '#4e6268', '#a32b24', '#adc0b7']
for name, col in zip(['Lime plaster', 'Oak', 'Brass', 'Paper', 'Slate iron', 'Vermilion', 'Reserve glass'], PALETTE):
    m = bpy.data.materials.new(name)
    m.diffuse_color = tuple(int(col[k:k+2], 16) / 255 for k in (1, 3, 5)) + (1,)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Roughness'].default_value = .72
    p.inputs['Metallic'].default_value = .55 if name == 'Brass' else 0
    if name == 'Reserve glass':
        p.inputs['Transmission Weight'].default_value = 1
        p.inputs['Roughness'].default_value = .12
        p.inputs['IOR'].default_value = 1.45
    MATERIALS.append(m)


def mesh(name, verts, faces, mat=1, hatch=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    SC.collection.objects.link(o)
    me.materials.append(MATERIALS[mat]); o['hatch'] = hatch
    return o


def cube(name, loc, size, mat=1):
    # Direct data construction keeps repeated shelves/books quick to rebuild.
    pts = [(x*size[0]/2, y*size[1]/2, z*size[2]/2)
           for x, y, z in [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
                           (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
    o = mesh(name, pts, [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)], mat)
    o.location = loc
    return o


def cylinder(name, a, b, radius, mat=2, n=12, hatch=True):
    a, b = Vector(a), Vector(b)
    d = (b-a).normalized()
    u = d.cross(Vector((0,0,1)))
    if u.length < .01: u = d.cross(Vector((0,1,0)))
    u.normalize(); v = d.cross(u)
    verts = [list(c + radius*(math.cos(t)*u + math.sin(t)*v))
             for c in [a,b] for t in np.linspace(0, math.tau, n, endpoint=False)]
    faces = [tuple(range(n-1,-1,-1)), tuple(range(n,2*n))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    return mesh(name, verts, faces, mat, hatch)


def beam(name, a, b, width=.06, mat=1, depth=None):
    a, b = Vector(a), Vector(b)
    o = cube(name, (a+b)/2, (width, depth or width, (b-a).length), mat)
    o.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return o


def curve(name, points, mat=4, radius=.006, width=.65, opaque=False):
    points = [tuple(p) for p in points]
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius; cu.bevel_resolution = 0
    sp = cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for p, v in zip(sp.points, points): p.co = (*v, 1)
    o = bpy.data.objects.new(name, cu); SC.collection.objects.link(o)
    cu.materials.append(MATERIALS[mat]); o['hatch'] = False; o['ink_only'] = not opaque
    STROKES.append({'name': name, 'pts': points, 'mat': mat, 'width': width})
    return o


def ring(name, c, rx, rz=None, mat=2, plane='XZ', radius=.009, width=.65, n=40):
    rz = rx if rz is None else rz
    pts = []
    for t in np.linspace(0, math.tau, n+1):
        d = (rx*math.cos(t), 0, rz*math.sin(t)) if plane == 'XZ' else (rx*math.cos(t), rz*math.sin(t), 0)
        pts.append(Vector(c)+Vector(d))
    return curve(name, pts, mat, radius, width)


def arch(name, cx, y, base, width, height, mat=2, radius=.02, width_px=.8):
    # Smooth pointed arch, with tangent-continuous paired Bezier shoulders.
    left, peak, right = np.array([cx-width/2,y,base]), np.array([cx,y,base+height]), np.array([cx+width/2,y,base])
    pts = []
    for a,b,c in [(left, [cx-width/2,y,base+height*.68], peak), (peak, [cx+width/2,y,base+height*.68], right)]:
        for t in np.linspace(0,1,25): pts.append((1-t)**2*a + 2*t*(1-t)*np.array(b) + t*t*c)
    return curve(name, pts, mat, radius, width_px)


def shelf_bank(cx, y, width, z0, z1, levels=5, seed=0):
    rng = random.Random(430+seed)
    for x in [cx-width/2,cx+width/2]: cube('Bookcase stile', (x,y,(z0+z1)/2), (.13,.56,z1-z0+.12))
    cube('Bookcase backing',(cx,y+.24,(z0+z1)/2),(width,.07,z1-z0),0)
    for z in np.linspace(z0,z1,levels+1): cube('Bookcase shelf',(cx,y,z),(width,.62,.085))
    for z in np.linspace(z0,z1,levels+1)[:-1]:
        x = cx-width/2+.15
        while x < cx+width/2-.22:
            w = rng.uniform(.11,.23); h = rng.uniform(.43,.76)*(z1-z0)/levels
            cube('Closed unlettered volume',(x+w/2,y-.06,z+.08+h/2),(w,.37,h),3)
            for dz in [.08,h+.08]: cube('Volume cover',(x+w/2,y-.06,z+dz),(w+.025,.40,.025))
            for dz in [h*.24,h*.78]: curve('Unlettered spine band',[(x,y-.253,z+.08+dz),(x+w,y-.253,z+.08+dz)],2,.003,.5)
            x += w+.035


def floor(width=10, back=10, near=-3, mat=0):
    mesh('Joined floor',[(-width/2,near,0),(width/2,near,0),(width/2,back,0),(-width/2,back,0)],[(0,1,2,3)],mat)
    for x in np.arange(-width/2+.2,width/2,.9): curve('Floor joint',[(x,near,.009),(x,back,.009)],0,.003,.45)
    for y in np.arange(near,back,.9): curve('Floor joint',[(-width/2,y,.01),(width/2,y,.01)],0,.003,.45)


def bench(cx, cy, width=3.8, depth=2., top=1.85, drawers=False):
    cube('Joined bench top',(cx,cy,top-.10),(width,depth,.20))
    for x in [cx-width/2+.18,cx+width/2-.18]:
        for y in [cy-depth/2+.18,cy+depth/2-.18]:
            beam('Bench leg',(x,y,0),(x,y,top-.15),.18)
        beam('Bench end stretcher',(x,cy-depth/2+.18,.42),(x,cy+depth/2-.18,.42),.10)
    beam('Bench longitudinal stretcher',(cx-width/2+.18,cy+depth/2-.18,.42),(cx+width/2-.18,cy+depth/2-.18,.42),.12)
    if drawers:
        for x in np.linspace(cx-width*.32,cx+width*.32,3):
            cube('Bench drawer',(x,cy-depth/2+.10,top-.45),(width*.28,.17,.42))
            ring('Drawer pull',(x,cy-depth/2+.005,top-.45),.055,mat=2,n=16)
    for y in np.arange(cy-depth/2+.05,cy+depth/2,.23):
        curve('Bench board join',[(cx-width/2+.02,y,top+.006),(cx+width/2-.02,y,top+.006)],1,.003,.5)
        for d in [.065,.125]:
            curve('Oak grain',[(x,y+d+.014*math.sin(x*6+y),top+.008) for x in np.linspace(cx-width/2+.05,cx+width/2-.05,30)],1,.002,.4)
    return top


def stool(cx, cy, height=1.05):
    cylinder('Stool seat',(cx,cy,height),(cx,cy,height+.12),.47,1,24)
    legs=[]
    for i,(x,y) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
        a=[cx+x*.38,cy+y*.34,0];b=[cx+x*.29,cy+y*.25,height+.02]
        beam('Stool leg '+str(i+1),a,b,.075); legs.append({'bottom':a,'top':b})
    for y in [-1,1]: beam('Stool stretcher',(cx-.35,cy+y*.31,.34),(cx+.35,cy+y*.31,.34),.055)
    for x in [-1,1]: beam('Stool stretcher',(cx+x*.35,cy-.31,.34),(cx+x*.35,cy+.31,.34),.055)
    PARTS['stool_legs']=legs


def folio(cx, cy, z, width=2.2, depth=1.55, tilt=0, rows=16):
    # Tilt about its front edge, so the ruled page is physically supported.
    a=math.radians(tilt)
    def P(x,y,h): return np.array([cx+x,cy+y*math.cos(a)-h*math.sin(a),z+y*math.sin(a)+h*math.cos(a)])
    covers=[]
    for side in [-1,1]:
        verts=[P(side*x,y,.05+.13*math.sin(math.pi*x/(width/2+.08))) for y in [0,depth] for x in np.linspace(.015,width/2,13)]
        mesh('Open folio leaf',verts,[(i,i+1,i+14,i+13) for i in range(12)],3)
        for y in np.linspace(.12,depth-.12,rows):
            curve('Blank ledger rule',[P(side*x,y,.058+.13*math.sin(math.pi*x/(width/2+.08))) for x in np.linspace(.10,width/2-.07,16)],4,.002,.45)
        curve('Folio cover edge',[P(side*.02,0,0),P(side*(width/2+.06),0,0),P(side*(width/2+.06),depth,0),P(side*.02,depth,0)],1,.014,.8)
        covers.append([P(side*.03,depth,0),P(side*(width/2+.03),depth,0)])
        for layer in range(4): curve('Page block edge',[P(side*.03,0,.015+layer*.009),P(side*(width/2+.01),0,.015+layer*.009)],3,.003,.5)
    curve('Folio binding gutter',[P(0,0,.055),P(0,depth,.055)],1,.01,.7)
    # Solid wedge lectern reaches the underside at the raised rear edge.
    if tilt:
        mesh('Folio supported wedge',[P(-width/2,.1,-.01),P(width/2,.1,-.01),P(width/2,depth-.08,-.01),P(-width/2,depth-.08,-.01),
                                      [cx-width/2,cy+.1,z-.05],[cx+width/2,cy+.1,z-.05],[cx+width/2,cy+depth*math.cos(a)-.08,z-.05],[cx-width/2,cy+depth*math.cos(a)-.08,z-.05]],
             [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(0,3,7,4),(1,5,6,2)],1)
    return P


def filigree_column(cx,y,z0,z1,width=.5):
    for dx in [-width/2,width/2]: beam('Filigree load-bearing upright',(cx+dx,y,z0),(cx+dx,y,z1),.035,2)
    levels=np.linspace(z0+.08,z1-.08,max(3,int((z1-z0)*4)))
    for i,z in enumerate(levels):
        rx=width*(.27+.09*math.sin(i*1.7));rz=min(.22,(z1-z0)/(len(levels)+1)*.65)
        ring('Cellular brass tracery',(cx,y-.01,z),rx,rz,2,radius=.005,width=.55,n=18)
        if i%3==1: cylinder('Slate tracery stud',(cx,y-.025,z),(cx,y-.065,z),rx*.34,4,8,False)


def branch(name, root, height, spread, mat=2, seed=0, plane='XZ', width=.55):
    rng=random.Random(seed)
    def grow(p, direction, length, depth):
        q=np.array(p)+np.array(direction)*length
        curve(name,[p,(np.array(p)+q)/2+np.array([.02,0,0]),q],mat,.003,width)
        if depth<=0:return
        for side in [-1,1]:
            t=side*rng.uniform(.3,.65);d=np.array([math.sin(t)*spread,0,math.cos(t)])
            grow(q,d,length*rng.uniform(.53,.70),depth-1)
    grow(np.array(root),[0,0,1],height*.30,4)


def base_room(width=10, back=8, height=7):
    floor(width,back)
    cube('Rear plaster',(0,back,(height)/2),(width,.24,height),0)
    for x in [-width/2+.1,width/2-.1]: cube('Side wall',(x,(back+1)/2,height/2),(.20,back-1,height),0)
    for x in [-width/2+.4,width/2-.4]: filigree_column(x,back-.27,.1,height-.15,.5)
    for y in [2,5,back-.4]:
        beam('Overhead cross timber',(-width/2+.2,y,height),(width/2-.2,y,height),.18)
    for x in [-width/2+.2,width/2-.2]: beam('Overhead rail',(x,1,height),(x,back,height),.16)


def observation_wheel(cx, cy, z, radius=1.35):
    for x in [cx-radius-.18,cx+radius+.18]:
        cube('Observation instrument foot',(x,cy,z+.08),(.44,.60,.16),4)
        cylinder('Observation instrument pillar',(x,cy,z+.10),(x,cy,z+radius+1.02),.07,2)
        beam('Wheel bolted bracket',(x,cy,z+radius+.23),(cx+math.copysign(radius,x-cx),cy,z+radius+.23),.07,2)
    c=(cx,cy,z+radius+.23)
    verts=[]
    for t in np.linspace(0,math.tau,64,endpoint=False):
        for dy,r in [(-.065,radius-.075),(-.065,radius+.075),(.065,radius-.075),(.065,radius+.075)]:
            verts.append((cx+r*math.cos(t),cy+dy,c[2]+r*math.sin(t)))
    faces=[]
    for i in range(64):
        a=i*4;b=((i+1)%64)*4
        faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
    mesh('Solid annular observation wheel',verts,faces,2)
    for dr in [-.07,0,.07]:ring('Open-centre observation wheel',c,radius+dr,mat=2,radius=.02,width=.9,n=80)
    for t in np.linspace(0,math.tau,72,endpoint=False):
        curve('Wheel calibration tick',[(cx+(radius-.06)*math.cos(t),cy-.03,c[2]+(radius-.06)*math.sin(t)),(cx+(radius+.08)*math.cos(t),cy-.03,c[2]+(radius+.08)*math.sin(t))],4,.004,.55)
    # A removable ruler rests on a bracket rather than floating in the wheel.
    beam('Removable ruler',(cx-radius-.1,cy-.14,c[2]-.65),(cx+radius+.1,cy-.14,c[2]-.65),.055,2,depth=.10)
    for x in np.linspace(cx-radius,cx+radius,25): curve('Ruler tick',[(x,cy-.2,c[2]-.68),(x,cy-.2,c[2]-.61)],4,.003,.45)
    return c


def maintained():
    base_room(10.4,9.8,8.8)
    # A raised cutaway work gallery, with a clearly accessible lower service bay.
    for x in [-4.7,-.1,4.7]:
        beam('Gallery support',(x,4.6,0),(x,4.6,2.05),.23,0)
        arch('Lower service arch',x/2,4.55,.45,3.6,1.45,0,.05,.9)
    cube('Raised workshop gallery',(0,5.4,2.15),(9.5,5.1,.22))
    for x in np.arange(-4.4,4.5,.48): beam('Front gallery baluster',(x,2.88,2.27),(x,2.88,3.18),.035,2)
    beam('Front gallery rail',(-4.6,2.88,3.21),(4.6,2.88,3.21),.065,2)
    # Intentional broad gap in the front balusters for stair access.
    for ob in list(SC.objects):
        if ob.name.startswith('Front gallery baluster') and ob.location.x>2.5: bpy.data.objects.remove(ob,do_unlink=True)
    for i in range(10): cube('Access stair tread',(3.5,-.4+i*.34,(i+1)*.216),(1.4,.38,.12))
    for x in [2.85,4.15]:beam('Stair stringer',(x,-.65,.04),(x,3.05,2.24),.12)
    z=bench(-2.65,5.,3.95,2.2,4.0,True)
    # Bench legs extend to the raised deck, not through it.
    for ob in list(SC.objects):
        if ob.name.startswith('Bench leg') or ob.name.startswith('Bench end stretcher') or ob.name.startswith('Bench longitudinal stretcher'):
            if ob.location.x<0: bpy.data.objects.remove(ob,do_unlink=True)
    for x in [-4.43,-.88]:
        for y in [4.08,5.92]:beam('Upper bench leg',(x,y,2.26),(x,y,3.85),.17)
    c=observation_wheel(-2.65,5.05,z,1.40)
    shelf_bank(-3.10,9.49,2.7,2.35,8.35,5)
    shelf_bank(3.05,9.49,2.7,2.35,8.35,5,4)
    # Stove is maintained from the raised floor; its flue has a connected route.
    cube('Tended stove',(2.55,5.6,2.75),(1.24,1.18,.98),4)
    cube('Stove door',(2.55,4.98,2.78),(.82,.08,.64),4)
    ring('Stove door rim',(2.55,4.922,2.79),.32,.23,2,radius=.015,width=.85)
    for x in [2.20,2.88]:beam('Stove foot',(x,5.3,2.25),(x,5.3,2.42),.10,4)
    cylinder('Stove flue',(2.90,5.95,3.23),(2.90,5.95,4.30),.12,4,12)
    cylinder('Flue return',(2.90,5.95,4.30),(4.60,5.95,4.60),.12,4,12)
    cylinder('Flue riser',(4.60,5.95,4.60),(4.60,5.95,8.65),.12,4,12)
    # Cycles uses glass. The engraving reserves paper within the glass silhouette
    # so the shelf texture cannot overwhelm the vessel's contour and filaments.
    cx,cy,cz=2.55,5.60,5.47
    prof=[(0,-1.26),(.36,-1.18),(.79,-.88),(1.00,-.35),(1.03,.12),(.91,.58),(.60,.94),(.22,1.15),(.17,1.38)]
    verts=[(cx+r*math.cos(a),cy+r*math.sin(a),cz+z) for r,z in prof for a in np.linspace(0,math.tau,40,endpoint=False)]
    faces=[(i*40+j,i*40+(j+1)%40,(i+1)*40+(j+1)%40,(i+1)*40+j) for i in range(len(prof)-1) for j in range(40)]
    glass=mesh('Reserve glass silhouette',verts,faces,6,False)
    for r,z0 in prof[1:]: ring('Reserve vessel contour',(cx,cy,cz+z0),r,r,4,'XY',.004,.55,64)
    for a in np.linspace(0,math.tau,8,endpoint=False):
        curve('Vessel supporting brass cage',[(cx+(r+.065)*math.cos(a),cy+(r+.065)*math.sin(a),cz+z0) for r,z0 in prof[1:]],2,.018,.85)
    for x in [cx-.75,cx+.75]:
        cylinder('Vessel ceiling suspension',(x,cy,cz+.78),(x,cy,8.72),.014,2,8,False)
        beam('Vessel suspension yoke',(x,cy,cz+.78),(cx,cy,cz+1.37),.025,2)
    # Fine branching filaments are drawn on plaster, not substituted for geometry.
    for x in [-.65,.65]:branch('Plaster branching trace',(x,9.64,2.5),5.3,.9,2,int(x*100+200))
    for r in range(3):branch('Glass filament',(cx-.5+r*.4,cy-.95,cz-.75),1.2,.7,4,r+30,.45)
    cube('Unfinished shelf board',(.3,6.35,3.9),(1.75,.72,.12))
    for x in [-.38,.98]:beam('Shelf trestle',(x,6.35,2.27),(x,6.35,3.84),.10)
    # Open gate, made from two jambs, with its gate leaf swung outward.
    for x in [-.40,.45]:beam('Open gate jamb',(x,4.45,4.0),(x,4.45,5.18),.045,2)
    curve('Swung instrument gate',[(-.40,4.45,4.03),(-1.0,4.10,4.03),(-1.0,4.10,5.15),(-.4,4.45,5.15)],2,.015,.85)
    cord=[(-4.25,5.05,c[2]),(-1.05,5.05,c[2]),(-.18,4.45,4.72),(.15,5.05,4.25),(.30,6.10,3.99),(.80,6.1,3.99)]
    curve('Vermilion route',cord,5,.012,1.05)
    PARTS.update({'characters_omitted':True,'vector_glass_convention':'paper-reserving silhouette','continuous_cord':cord,'gallery_floor_z':2.26})
    return (.1,-10.4,6.8),(0,5.1,4.65),2220


def cabinet():
    base_room(9.4,7.8,7.3)
    shelf_bank(-3.20,7.50,2.15,.12,6.9,6)
    shelf_bank(3.20,7.50,2.15,.12,6.9,6,4)
    # Open cabinet frame: absolutely no central box or concealed operator.
    cx,cy=0,3.7;hw,hd=1.62,.84;z0,z1=.62,5.05
    for x in [-hw,hw]:
        for y in [cy-hd,cy+hd]:
            beam('Cabinet load-bearing corner',(x,y,z0),(x,y,z1),.15)
            for z in [z0,z1]:cube('Cabinet corner boss',(x,y,z),(.25,.25,.20),2)
    for z in [z0,z1]:
        for y in [cy-hd,cy+hd]:beam('Cabinet cross rail',(-hw,y,z),(hw,y,z),.14)
        for x in [-hw,hw]:beam('Cabinet depth rail',(x,cy-hd,z),(x,cy+hd,z),.14)
    cube('Cabinet lower platform',(0,cy,z0),(3.26,1.75,.18))
    cube('Cabinet top',(0,cy,z1+.10),(3.64,2.0,.20))
    for x in [-1.42,1.42]:
        for y in [cy-.65,cy+.65]:
            cylinder('Cabinet turned foot',(x,y,.05),(x,y,.53),.105,1,12)
            ring('Cabinet foot ring',(x,y,.18),.125,mat=2,plane='XY',n=16)
    # Both front doors swing outside the cabinet. Hatches are separate hinged leaves.
    door_polys=[]
    for side in [-1,1]:
        hinge=np.array([side*hw,cy-hd-.04,0.]);angle=side*math.radians(116)
        # Left leaf's local direction is inward before the outward hinge rotation.
        direction=np.array([-side*math.cos(angle),-side*math.sin(angle),0])
        if direction[1]>0: direction[1]*=-1
        for zz in [z0+.16,z1-.16]:
            beam('Opened door horizontal',hinge+np.array([0,0,zz]),hinge+direction*1.44+np.array([0,0,zz]),.115)
        for dd in [0,1.44]: beam('Opened door stile',hinge+direction*dd+np.array([0,0,z0+.16]),hinge+direction*dd+np.array([0,0,z1-.16]),.115)
        # Six small inspection windows in each swung door; no opaque central panels.
        for zz in np.linspace(z0+.78,z1-.78,4):
            beam('Door inspection divider',hinge+np.array([0,0,zz]),hinge+direction*1.44+np.array([0,0,zz]),.055,2)
        for zz in np.linspace(z0+.53,z1-.53,7):
            points=[hinge+direction*(.72+.46*math.cos(t))+np.array([0,-.015,zz+.17*math.sin(t)]) for t in np.linspace(0,math.tau,32)]
            curve('Opened door cellular edging',points,2,.005,.70)
        door_polys.append([list(hinge+direction*dd+np.array([0,0,zz])) for dd,zz in [(0,z0),(1.44,z0),(1.44,z1),(0,z1)]])
        for zz in [1.3,2.8,4.3]:cylinder('Door hinge pin',(side*hw,cy-hd-.04,zz-.15),(side*hw,cy-hd-.04,zz+.15),.045,2,10)
    # Two side inspection hatches lie open horizontally above empty apertures.
    for side in [-1,1]:
        x=side*hw
        for zz in [1.65,3.65]:
            cube('Side hatch raised leaf',(x+side*.44,cy,zz+.42),(.88,1.36,.08))
            for y in [cy-.7,cy+.7]:beam('Side aperture frame',(x,y,zz-.42),(x,y,zz+.42),.055,2)
            beam('Side aperture sill',(x,cy-.7,zz-.42),(x,cy+.7,zz-.42),.055,2)
    for x in [-hw,hw]:
        filigree_column(x,cy-hd-.10,z0+.2,z1-.2,.24)
        cylinder('Cabinet crown finial',(x,cy-hd,z1+.20),(x,cy-hd,z1+.52),.045,2,12)
        ring('Cabinet crown terminal',(x,cy-hd,z1+.46),.075,mat=2,radius=.012,width=.8,n=24)
    # Perimeter mechanics sit beside the void, with axles held in bearing blocks.
    for side in [-1,1]:
        x=side*1.46
        for z in [1.20,2.30,3.40,4.50]:
            for r in [.17,.25]:ring('Perimeter pulley',(x,cy+.60,z),r,mat=2,radius=.014,width=.72,n=28)
            cylinder('Pulley axle',(x,cy+.48,z),(x,cy+.79,z),.038,4,10)
            cube('Pulley bearing',(x,cy+.84,z),(.20,.13,.20),4)
        curve('Perimeter drive belt',[(x-.22,cy+.63,1.15),(x-.22,cy+.63,4.55),(x+.22,cy+.63,4.55),(x+.22,cy+.63,1.15),(x-.22,cy+.63,1.15)],4,.008,.7)
    crank=[(hw+.05,cy-.35,1.0),(hw+.52,cy-.35,1.0),(hw+.52,cy-.35,1.28),(hw+.72,cy-.35,1.28)]
    for a,b in zip(crank,crank[1:]):cylinder('Connected cabinet crank',a,b,.035,2,10)
    # A folded chessboard, shut: closed halves, hinge and small visible grid on the outer top.
    board=cube('Folded chessboard',(0,cy,5.33),(2.1,1.1,.18))
    for x in np.linspace(-1.,1.,9):curve('Folded board grid',[(x,cy-.51,5.427),(x,cy+.51,5.427)],4,.003,.5)
    for y in np.linspace(cy-.51,cy+.51,5):curve('Folded board grid',[(-1.,y,5.427),(1.,y,5.427)],4,.003,.5)
    for x in [-.65,.65]:cube('Chessboard hinge',(x,cy+.56,5.33),(.18,.08,.10),2)
    # Front worktable deliberately leaves the cabinet sightline open above it.
    z=bench(-.9,-.65,4.1,1.65,1.25,True)
    folio(-1.45,-1.30,z+.015,2.05,1.20,5,15)
    cylinder('Thread spool core',(.68,-.65,z),(.68,-.65,z+.33),.10,1,12)
    for zz in [z+.02,z+.32]:cylinder('Thread spool flange',(.68,-.65,zz),(.68,-.65,zz+.035),.19,2,16,False)
    for zz in np.linspace(z+.075,z+.28,12):ring('Vermilion thread on spool',(.68,-.65,zz),.125,mat=5,plane='XY',radius=.005,width=.8,n=24)
    curve('Loose spool end',[(.80,-.65,z+.08),(.95,-.86,z+.009),(1.02,-1.05,z+.009),(.78,-1.26,z+.009)],5,.009,1.)
    cylinder('Ledger pencil',(-.20,-.42,z+.025),(.36,-.12,z+.025),.016,1,8,False)
    curve('Disconnected drive belt',[(1.70+.60*math.cos(t),1.65+.32*math.sin(t),.025) for t in np.linspace(0,5.6,60)],4,.024,.9)
    # Unoccupied four-leg chair at the left of the cabinet.
    cx,cy=-2.73,2.3
    cube('Unoccupied chair seat',(cx,cy,.99),(1.0,.94,.12))
    legs=[]
    for x in [-.4,.4]:
        for y in [-.37,.37]:
            a=[cx+x,cy+y,0];b=[cx+x*.88,cy+y*.88,.97]
            beam('Chair leg',a,b,.08);legs.append({'bottom':a,'top':b})
    for x in [-.43,.43]:beam('Chair back post',(cx+x,cy+.37,1.03),(cx+x,cy+.37,2.14),.065)
    for zc in [1.46,2.12]:beam('Chair back rail',(cx-.43,cy+.37,zc),(cx+.43,cy+.37,zc),.065)
    for dx in [-.25,0,.25]:beam('Chair back spindle',(cx+dx,cy+.37,1.46),(cx+dx,cy+.37,2.12),.025,2)
    PARTS.update({'chair_legs':legs,'cabinet_clear_volume':[[-1.1,2.95,.85],[1.1,4.2,4.80]],'open_front_doors':door_polys,'folded_board_closed':True})
    return (7.9,-12.9,7.0),(0,3.2,3.15),2300


def extraction():
    # Partial room fades into the margin through absent walls, not bitmap masks.
    floor(8,5.8,-2.6)
    shelf_bank(2.85,5.5,1.6,.08,5.1,5,9)
    for x in [-3.5,3.7]:filigree_column(x,5.30,.02,5.5,.6)
    arch('Repair-bay crown',.1,5.32,3.3,7.2,2.6,2,.018,.8)
    z=bench(0,1.7,6.5,2.35,1.90,True)
    # Finely pierced instrument framework tied to the rear of the workbench.
    for x in [-2.96,2.96]:filigree_column(x,2.58,z,4.15,.37)
    for x in [-1.98,0,1.98]:arch('Bench lace arcade',x,.55,.75,1.94,1.03,2,.008,.65)
    folioP=folio(1.38,1.00,z+.025,2.55,1.75,21,23)
    # Wrist clamp and flat wooden hand-shaped jig, with five distinct splayed fingers.
    cx,cy=-1.95,2.1
    cube('Hand jig plinth',(cx,cy,z+.10),(1.22,.85,.20),4)
    cube('Wrist clamp',(cx,cy,z+.34),(.68,.46,.48),2)
    palm=[(-.37,.0),(.35,.0),(.44,.54),(.30,.98),(-.26,.97),(-.43,.58)]
    py=cy-.025;pz=z+.48
    # Plane is XZ; wooden thickness is explicit, not a detached hand character.
    pts=[(cx+x,py+dy,pz+h) for dy in [-.07,.07] for x,h in palm]
    faces=[tuple(range(5,-1,-1)),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)]
    mesh('Wooden repair jig palm',pts,faces,1)
    fingers=[(-.30,.84,-.57,2.01,.082),(-.13,.98,-.18,2.32,.078),(.06,.99,.26,2.27,.073),(.25,.88,.64,1.96,.068),(-.37,.42,-.93,1.12,.095)]
    tips=[]
    for i,(x0,h0,x1,h1,r) in enumerate(fingers):
        a=np.array([cx+x0,py,pz+h0]);b=np.array([cx+x1,py,pz+h1]);m=a*.48+b*.52
        cylinder('Jig finger '+str(i+1)+' lower',a,m,r,1,8)
        cylinder('Jig finger '+str(i+1)+' upper',m,b,r*.82,1,8)
        ring('Jig finger hinge',m+np.array([0,-.09,0]),r*.65,mat=2,n=18)
        tips.append(b.tolist())
    # Multiple strands emerge at the jig and become exact blank ruled rows.
    strands=[]
    for i in range(23):
        f=i%5;start=np.array(tips[f])+np.array([.02*(i//5-2),-.09,-.06*(i//5)])
        y=.12+(1.75-.24)*i/22
        end=folioP(-1.22,y,.058+.13*math.sin(math.pi*1.22/(2.55/2+.08)))
        p=[]
        for t in np.linspace(0,1,45):
            q=start*(1-t)+end*t;q[2]-=.52*math.sin(math.pi*t);q[1]-=.10*math.sin(math.pi*t);p.append(q)
        curve('Jig strand continuing into ledger rule',p,4,.0028,.53)
        # Continue through the same page parameterization as the folio's rules.
        continuation=[folioP(-x,y,.058+.13*math.sin(math.pi*x/(2.55/2+.08))) for x in np.linspace(1.22,.10,22)]
        curve('Strand becomes ledger row',continuation,4,.0028,.53)
        strands.append({'start':list(start),'end':list(end),'finger':f})
    stool(.05,-.15,1.08)
    # Hanging terminal dots are attached to the bench apron, not anonymous floating parts.
    for i,x in enumerate(np.linspace(-2.8,2.8,21)):
        length=.13+.35*(.5+.5*math.sin(i*2.3))
        curve('Apron pendant',[(x,.53,1.61),(x,.53,1.61-length)],2,.003,.5)
        cylinder('Apron terminal',(x,.53,1.59-length),(x,.53,1.63-length),.026,4,8,False)
    curve('Vermilion route',[(-2.96,1.0,z+.012),(-2.25,.88,z+.012),(-1.15,.78,z+.012),(.10,.72,z+.012),(.58,.91,z+.012)],5,.009,1.)
    PARTS.update({'jig_fingers':5,'jig_tips':tips,'ledger_strands':strands,'blank_ruled_ledger':True})
    return (6.1,-11.7,6.6),(-.15,1.9,2.45),2380


def office():
    # A shallow, tall alcove; all side detail bends around an untouched recess.
    floor(7.4,5.8,-2)
    cube('Alcove rear plaster',(0,5.55,3.9),(7.4,.20,7.8),0)
    for x in [-3.60,3.60]:cube('Alcove return',(x,3.5,3.9),(.18,4.1,7.8),0)
    # Real empty framed niche with its blank back set deeper than the frame.
    xmin,xmax=-1.23,1.23;zmin,zmax=2.65,5.62
    blank=cube('Untouched recess back',(0,5.40,(zmin+zmax)/2),(2.46,.08,zmax-zmin),3);blank['hatch']=False
    for x in [xmin-.06,xmax+.06]:cube('Recess side frame',(x,5.20,(zmin+zmax)/2),(.095,.32,zmax-zmin+.20),0)
    for zc in [zmin-.06,zmax+.06]:cube('Recess lintel sill',(0,5.20,zc),(2.68,.32,.095),0)
    # Width-limited filigree bays never cross the central reserved rectangle.
    for x in [-2.90,-1.80,1.80,2.90]:
        filigree_column(x,4.84,.06,7.40,.48)
        for zc in [1.12,2.75,4.38,6.01]:
            arch('Side cellular arcade',x,4.80,zc,.9,.79,2,.008,.65)
            cylinder('Side inspection inset',(x,4.77,zc+.24),(x,4.69,zc+.24),.10,4,12,False)
    for side in [-1,1]:
        for zc in [1.18,3.56,5.95]:
            cube('Cantilevered instrument shelf',(side*2.39,4.63,zc),(1.62,1.05,.10))
            for x in [side*1.84,side*2.93]:beam('Shelf bracket',(x,5.18,zc-.35),(x,4.17,zc-.05),.04,2)
    # An upper bracket is visually attached to both sides of the crown.
    arch('Crown outer tracery',0,4.86,5.98,6.40,1.40,2,.023,1.0)
    arch('Crown inner tracery',0,4.85,6.12,5.8,.99,4,.014,.75)
    for i,x in enumerate(np.linspace(-2.7,2.7,17)):
        zc=6.25+1.02*math.sqrt(max(0,1-(x/3.0)**2))
        ring('Crown cellular joint',(x,4.83,zc),.12,.15,2,radius=.007,width=.65,n=20)
    beam('Bracket cross member',(-.78,5.02,6.33),(.78,5.02,6.33),.055,2)
    for x in [-.78,.78]:beam('Bracket upright',(x,5.02,6.33),(x,5.02,6.85),.045,2)
    ring('Upper cord attachment',(0,5.00,6.32),.085,mat=2,radius=.012,width=.8,n=24)
    # The two disconnected cords end outside the recess, with no bridge across it.
    upper=[(0,4.98,6.24),(0,4.98,5.94)]
    lower=[(0,4.98,2.30),(0,4.98,1.45)]
    curve('Upper disconnected cord',upper,4,.009,.85)
    curve('Lower disconnected cord',lower,4,.009,.85)
    for zc in [5.94,2.30]:
        cylinder('Vermilion cord end',(0,4.98,zc-.025),(0,4.98,zc+.025),.026,5,10,False)
        curve('Vermilion cord end accent',[(0,4.95,zc-.025),(0,4.95,zc+.025)],5,.012,1.5)
    ring('Hand-height pull ring',(0,4.98,1.18),.20,.26,2,radius=.018,width=1.0,n=48)
    beam('Lower ring mounting peg',(0,5.35,1.18),(0,5.02,1.18),.04,4)
    for s in [-1,1]:
        curve('Lower curved alcove rail',[(s*(.35+2.85*t),4.80, .55+1.15*t*t) for t in np.linspace(0,1,45)],2,.012,.8)
        for x in np.linspace(.6,3.0,12):
            ring('Lower lace cell',(s*x,4.78,.25+.14*x*x),.12,.17,2,radius=.005,width=.55,n=18)
    PARTS.update({'reserved_recess':{'xmin':xmin,'xmax':xmax,'zmin':zmin,'zmax':zmax,'y':5.40},'upper_cord':upper,'lower_cord':lower,'cord_gap_z':[2.30,5.94]})
    return (3.0,-11.6,5.5),(0,4.9,3.95),2550


EYE, TARGET, FOCAL = {'maintained-workshop':maintained,'empty-cabinet':cabinet,'extraction-of-the-hand':extraction,'office-without-a-seal':office}[KEY]()
EYE, TARGET = Vector(EYE), Vector(TARGET)
bpy.ops.object.camera_add(location=EYE)
cam = bpy.context.object;cam.name='Engraving perspective camera'
cam.rotation_euler=(TARGET-EYE).to_track_quat('-Z','Y').to_euler()
cam.data.type='PERSP';cam.data.sensor_fit='HORIZONTAL';cam.data.sensor_width=36;cam.data.lens=FOCAL/W*36
cam.data.shift_y={'maintained-workshop':-.13,'empty-cabinet':-.12,'extraction-of-the-hand':-.12,'office-without-a-seal':-.08}[KEY]
SC.camera=cam
world=bpy.data.worlds.new('Soft workshop ambient');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.72,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.35;SC.world=world
for name,loc,power,size in [('Large window',(-4,-1,8),1800,5),('Room fill',(4,-6,6),700,5)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name
    o.data.energy=power;o.data.size=size;o.rotation_euler=(TARGET-o.location).to_track_quat('-Z','Y').to_euler()
SC.render.engine='CYCLES';SC.cycles.device='CPU';SC.cycles.samples=12;SC.cycles.use_denoising=True
SC.render.threads_mode='FIXED';SC.render.threads=4
SC.render.resolution_x=W;SC.render.resolution_y=H;SC.render.resolution_percentage=100
SC.render.image_settings.file_format='PNG';SC.view_settings.view_transform='AgX'
SC['brief_file']='briefs/'+KEY+'.txt'
SC['source_book_commit']='02e1155ca3e33aa339436263c4d3b1f4992392ab'
SC['generation_seed']=271
SC['vector_render_note']='Run engrave.py after rebuilding. The separate renderer uses these evaluated polygons; it is not a raster tracer.'

deps=bpy.context.evaluated_depsgraph_get()
vertices,faces,normals,mats,names,hatch=[],[],[],[],[],[]
for ob in sorted(SC.objects,key=lambda o:o.name):
    if ob.type not in ['MESH','CURVE'] or ob.get('ink_only',False):continue
    ev=ob.evaluated_get(deps);me=ev.to_mesh()
    if not me:continue
    start=len(vertices);vertices.extend([list(ev.matrix_world@v.co) for v in me.vertices])
    for p in me.polygons:
        faces.append([start+i for i in p.vertices]);material=me.materials[p.material_index]
        mats.append(next(i for i,m in enumerate(MATERIALS) if m.name==material.name));names.append(ob.name);hatch.append(bool(ob.get('hatch',True)))
        normals.append(list((ev.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized()))
    ev.to_mesh_clear()
data={'key':KEY,'title':TITLES[KEY],'vertices':vertices,'faces':faces,'normals':normals,'mats':mats,'names':names,'hatch':hatch,'strokes':STROKES,'palette':PALETTE,'parts':PARTS,
      'camera':{'eye':list(EYE),'target':list(TARGET),'focal_px':FOCAL,'principal_point':[W/2,H/2+cam.data.shift_y*W],'resolution':[W,H]},'blender':bpy.app.version_string,
      'generator':{'type':'procedural mesh and stroke construction','seed':271,'script':'model.py','brief':KEY+'.txt'}}
(OUT/'scene.json').write_text(json.dumps(data,separators=(',',':')))
# Compare the exported perspective directly with Blender before saving.
eye=np.array(EYE);fwd=np.array(TARGET)-eye;fwd/=np.linalg.norm(fwd)
right=np.cross(fwd,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,fwd)
p=np.array(vertices)[::37];q=p-eye;z=q@fwd;sel=z>.5;p=p[sel];q=q[sel];z=z[sel]
cpu=np.column_stack([W/2+FOCAL*(q@right)/z,H/2+cam.data.shift_y*W-FOCAL*(q@up)/z])
native=np.array([(v.x*W,(1-v.y)*H) for v in [world_to_camera_view(SC,cam,Vector(t)) for t in p]])
error=float(np.max(abs(cpu-native)))
assert error<.003, error
(OUT/'camera-check.json').write_text(json.dumps({'passed':True,'samples':len(p),'maximum_pixel_error':error},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(KEY+'.blend')),compress=True)
if os.environ.get('RENDER','1')!='0':
    SC.render.resolution_percentage=40;SC.render.filepath=str(OUT/'blender-proof.png')
    bpy.ops.render.render(write_still=True)
    SC.render.resolution_percentage=100;SC.render.filepath='//blender-proof.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(KEY+'.blend')),compress=True)
print(json.dumps({'plate':KEY,'objects':len(SC.objects),'faces':len(faces),'camera_error_px':error}),flush=True)
