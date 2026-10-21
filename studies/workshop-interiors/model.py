"""Four workshop interiors, rebuilt from the book's recorded briefs.

Run with Blender 4.5 LTS or its official bpy wheel. PLATE selects a scene;
RENDER=0 skips the Cycles proof, never the .blend or evaluated-mesh export.
"""
from pathlib import Path
import json, math, os, random, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from types import SimpleNamespace
from settings_v2 import SIZES, PX_PER_MM, WEIGHTS_MM, TONE, HIERARCHY, INKS, CAPTIONS, LIMITS, ALLOCATION_MULTIPLIERS
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parent
KEY = os.environ.get('PLATE', 'empty-cabinet')
OUT = ROOT / 'output' / 'v2' / KEY
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
PRINT_WIDTH_MM, PRINT_HEIGHT_MM = SIZES[KEY]
W, H = int(PRINT_WIDTH_MM*PX_PER_MM), int(PRINT_HEIGHT_MM*PX_PER_MM)
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
    bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    SC.collection.objects.link(o)
    me.materials.append(MATERIALS[mat]); o['hatch'] = hatch; o['tone_zone']=SC.get('tone_zone','structure')
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


def curve(name, points, mat=4, radius=.006, width=.65, opaque=False, role=None, reserved_content=None):
    points = [tuple(p) for p in points]
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius; cu.bevel_resolution = 0
    sp = cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for p, v in zip(sp.points, points): p.co = (*v, 1)
    o = bpy.data.objects.new(name, cu); SC.collection.objects.link(o)
    cu.materials.append(MATERIALS[mat]); o['hatch'] = False; o['ink_only'] = not opaque
    STROKES.append({'name': name, 'pts': points, 'mat': mat, 'width': width, 'role':role or ('red_route' if mat==5 else 'backdrop' if name in ['Floor joint','Bench board seam'] else 'ornament'), 'reserved_content':reserved_content, 'zone':SC.get('tone_zone','structure')})
    return o


def ring(name, c, rx, rz=None, mat=2, plane='XZ', radius=.009, width=.65, n=40, role=None, reserved_content=None):
    rz = rx if rz is None else rz
    pts = []
    for t in np.linspace(0, math.tau, n+1):
        d = (rx*math.cos(t), 0, rz*math.sin(t)) if plane == 'XZ' else (rx*math.cos(t), rz*math.sin(t), 0)
        pts.append(Vector(c)+Vector(d))
    return curve(name, pts, mat, radius, width, role=role, reserved_content=reserved_content)


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
        verts=[P(side*x,y,.05+.018*math.sin(math.pi*x/(width/2+.08))) for y in [0,depth] for x in np.linspace(.015,width/2,13)]
        mesh('Open folio leaf',verts,[(i,i+1,i+14,i+13) for i in range(12)],3)
        for y in np.linspace(.12,depth-.12,rows):
            curve('Blank ledger rule',[P(side*x,y,.058+.018*math.sin(math.pi*x/(width/2+.08))) for x in np.linspace(.10,width/2-.07,16)],4,.002,.45)
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
    levels=np.linspace(z0+.08,z1-.08,max(3,int((z1-z0)*2)))
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
        curve('Wheel calibration tick',[(cx+(radius-.06)*math.cos(t),cy-.09,c[2]+(radius-.06)*math.sin(t)),(cx+(radius+.08)*math.cos(t),cy-.09,c[2]+(radius+.08)*math.sin(t))],4,.004,.55)
    # A removable ruler rests on a bracket rather than floating in the wheel.
    beam('Removable ruler',(cx-radius-.1,cy-.14,c[2]-.65),(cx+radius+.1,cy-.14,c[2]-.65),.055,2,depth=.10)
    for x in np.linspace(cx-radius,cx+radius,25): curve('Ruler tick',[(x,cy-.2,c[2]-.68),(x,cy-.2,c[2]-.61)],4,.003,.45)
    return c


from scenes_v2 import construct
EYE, TARGET, FOV, SHIFT = construct(SimpleNamespace(**globals()), KEY)
FOCAL=W/(2*math.tan(math.radians(FOV)/2))

EYE, TARGET = Vector(EYE), Vector(TARGET)
bpy.ops.object.camera_add(location=EYE)
cam = bpy.context.object;cam.name='Engraving perspective camera'
cam.rotation_euler=(TARGET-EYE).to_track_quat('-Z','Y').to_euler()
cam.data.type='PERSP';cam.data.sensor_fit='HORIZONTAL';cam.data.sensor_width=36;cam.data.lens=FOCAL/W*36
cam.data.shift_y=SHIFT
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
SC['brief_file']='briefs/v2/'+KEY+'.txt'
SC['print_width_mm']=PRINT_WIDTH_MM;SC['print_height_mm']=PRINT_HEIGHT_MM;SC['px_per_mm']=PX_PER_MM;SC['engraving_revision']=2
SC['source_book_commit']='02e1155ca3e33aa339436263c4d3b1f4992392ab'
SC['generation_seed']=271
SC['vector_render_note']='Run engrave.py after rebuilding. The separate renderer uses these evaluated polygons; it is not a raster tracer.'

deps=bpy.context.evaluated_depsgraph_get()
vertices,faces,normals,mats,names,hatch,zones,reserves=[],[],[],[],[],[],[],[]
for ob in sorted(SC.objects,key=lambda o:o.name):
    if ob.type not in ['MESH','CURVE'] or ob.get('ink_only',False):continue
    ev=ob.evaluated_get(deps);me=ev.to_mesh()
    if not me:continue
    start=len(vertices);vertices.extend([list(ev.matrix_world@v.co) for v in me.vertices])
    for p in me.polygons:
        faces.append([start+i for i in p.vertices]);material=me.materials[p.material_index]
        mats.append(next(i for i,m in enumerate(MATERIALS) if m.name==material.name));names.append(ob.name)
        normal=(ev.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized();normals.append(list(normal))
        region=ob.get('reserved','') or (ob.get('reserve_top','') if normal.z>.9 else '')
        tone=ob.get('tone_zone','structure')
        if ob.get('interior_side') is not None and normal.x*ob['interior_side']<-.5:tone='interior-panels'
        if ob.get('underside_zone') and normal.z<-.9:tone=ob['underside_zone']
        zones.append('reserved' if region else tone);reserves.append(region);hatch.append(bool(ob.get('hatch',True)) and not region)
    ev.to_mesh_clear()
data={'key':KEY,'title':TITLES[KEY],'vertices':vertices,'faces':faces,'normals':normals,'mats':mats,'names':names,'hatch':hatch,'zones':zones,'reserved':reserves,'strokes':STROKES,'palette':PALETTE,'parts':PARTS,
      'camera':{'eye':list(EYE),'target':list(TARGET),'focal_px':FOCAL,'principal_point':[W/2,H/2+cam.data.shift_y*W],'resolution':[W,H]},'blender':bpy.app.version_string,
      'generator':{'type':'procedural mesh and stroke construction','seed':271,'script':'model.py / scenes_v2.py','brief':'briefs/v2/'+KEY+'.txt'},
      'revision':2,'print':{'width_mm':PRINT_WIDTH_MM,'height_mm':PRINT_HEIGHT_MM,'px_per_mm':PX_PER_MM,'weights_mm':WEIGHTS_MM,'inks':INKS,'caption':CAPTIONS[KEY]},
      'engraving':{'coverage_cap':.82,'gamma':1.05,'split':.20,'minimum_gap_mm':.22,'tone_targets':TONE[KEY],'hierarchy':HIERARCHY[KEY],'sun':[-.819,-.33,.574],'stove_light':PARTS.get('stove_light',[0,0,0]),'deep_pass_angle':.85,'deep_pass_angles':[.85,1.32],'allocation_multipliers':ALLOCATION_MULTIPLIERS,'halos_mm':{'strands':4.0,'recess':8.0},'reserved_paper_policy':'Unhatched geometry occludes marks behind; named internal content remains allowed.','limits':LIMITS}}
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
    SC.render.resolution_percentage=26;SC.render.filepath=str(OUT/'blender-proof.png')
    bpy.ops.render.render(write_still=True)
    SC.render.resolution_percentage=100;SC.render.filepath='//blender-proof.png'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(KEY+'.blend')),compress=True)
print(json.dumps({'plate':KEY,'objects':len(SC.objects),'faces':len(faces),'camera_error_px':error}),flush=True)
