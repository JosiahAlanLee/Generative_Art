"""Second-pass constructions. Geometry and reserved paper follow the new briefs."""
from contextlib import contextmanager
import math
import numpy as np
from mathutils import Vector, Matrix

@contextmanager
def zone(A,name):
    previous=A.SC.get('tone_zone','structure');A.SC['tone_zone']=name
    try:yield
    finally:A.SC['tone_zone']=previous

def reserved(o,name,top_only=False):
    o['reserve_top' if top_only else 'reserved']=name
    if not top_only:o['hatch']=False
    return o

def paper(A,name,points,region,render=True):
    o=reserved(A.mesh(name,points,[tuple(range(len(points)))],3,False),region)
    o.hide_render=not render
    return o

def table(A,cx,cy,width,depth,top,floorz=0,zone_top='bench-top',zone_frame='apron'):
    with zone(A,zone_top):A.cube('Bench top',(cx,cy,top-.10),(width,depth,.20))
    with zone(A,zone_frame):
        for x in [cx-width/2+.16,cx+width/2-.16]:
            for y in [cy-depth/2+.16,cy+depth/2-.16]:A.beam('Bench leg',(x,y,floorz),(x,y,top-.18),.15)
            A.beam('Bench end stretcher',(x,cy-depth/2+.16,floorz+.35),(x,cy+depth/2-.16,floorz+.35),.08)
        A.cube('Bench apron',(cx,cy-depth/2+.10,top-.33),(width-.10,.12,.35))
    with zone(A,zone_top):
        for y in np.arange(cy-depth/2+.05,cy+depth/2,.42):
            A.curve('Bench board seam',[(cx-width/2+.03,y,top+.008),(cx+width/2-.03,y,top+.008)],1,role='backdrop')
    return top

def sidecase(A,x,y,width,z0,z1,side,levels=5):
    before={o.name for o in A.SC.objects};n=len(A.STROKES)
    with zone(A,'bookcases'):A.shelf_bank(0,0,width,z0,z1,levels,int(abs(y)*10))
    A.bpy.context.view_layer.update()
    angle=math.pi/2 if side<0 else -math.pi/2
    R=Matrix.Rotation(angle,4,'Z');T=Matrix.Translation((x,y,0))@R
    for o in A.SC.objects:
        if o.name not in before:o.matrix_world=T@o.matrix_world
    for s in A.STROKES[n:]:s['pts']=[list(T@Vector(p)) for p in s['pts']]

def sphere(A,name,c,r,mat=4):
    pts=[];nr,ns=8,16
    for i in range(nr+1):
        phi=math.pi*i/nr
        for j in range(ns):
            t=math.tau*j/ns;pts.append((c[0]+r*math.sin(phi)*math.cos(t),c[1]+r*math.sin(phi)*math.sin(t),c[2]+r*math.cos(phi)))
    return A.mesh(name,pts,[(i*ns+j,i*ns+(j+1)%ns,(i+1)*ns+(j+1)%ns,(i+1)*ns+j) for i in range(nr) for j in range(ns)],mat)

def clerk(A,cx,cy,base,hand_target,label):
    # A reserved hood and robe are one closed silhouette, without face strokes.
    profile=[(-.40,0),(.44,0),(.25,1.25),(.23,1.82),(.35,2.14),(0,2.73),(-.34,2.14),(-.22,1.8),(-.25,1.1)]
    p=[(cx+x,cy,base+z) for x,z in profile]
    paper(A,'Clerk silhouette '+label,p,'clerk-'+label)
    start=np.array([cx+(.18 if hand_target[0]>cx else -.18),cy-.03,base+1.62]);end=np.array(hand_target)
    d=end-start;u=np.array([.025,0,.025])
    # One hand stroke group, including the forearm and a small articulated outline.
    pts=[start,start+d*.7,end-u,end+u,end+np.array([.04,0,-.02]),end+np.array([.065,0,.015]),end+np.array([.025,0,.045]),end,start+d*.7+np.array([0,0,-.06])]
    A.curve('Clerk hand '+label,pts,4,role='strand',reserved_content='clerk-'+label)
    return label

def workshop(A):
    gallery=3.3;top=5.0;roof=10.1
    with zone(A,'floor'):A.floor(9.2,8.7,-.5)
    with zone(A,'rear-wall'):
        A.cube('Rear plaster',(0,8.65,roof/2),(9.2,.20,roof),0)
        A.cube('Night right return',(4.55,6.0,roof/2),(.16,5.1,roof),0)
        A.cube('Night left rear return',(-4.55,7.65,roof/2),(.16,2.0,roof),0)
    with zone(A,'service-bay'):
        # A recessed inner back and returns, not an unsupported patch of tone.
        A.cube('Service bay rear',(0,7.3,1.55),(8.35,.14,2.95),0)
        for x in [-4.05,4.05]:A.cube('Service bay inner return',(x,5.45,1.55),(.13,3.7,2.95),0)
    with zone(A,'structure'):
        for x in [-4.15,0,4.15]:A.beam('Gallery support',(x,3.85,0),(x,3.85,gallery-.10),.24)
        for x in [-2.08,2.08]:A.arch('Service bay arch',x,3.85,.60,4.0,2.5,4,.028)
        for x in [-4.4,4.4]:A.beam('Ceiling longitudinal rail',(x,2.1,roof),(x,8.55,roof),.18)
        for y in [3.7,6.4,8.4]:A.beam('Ceiling cross timber',(-4.5,y,roof),(4.5,y,roof),.19)
    with zone(A,'deck'):
        deck=A.cube('Gallery deck',(0,5.8,gallery-.12),(8.9,4.5,.24));deck['underside_zone']='underside'
    with zone(A,'bookcases'):
        # The left bank is shifted toward the side; the wheel hub sees plain plaster.
        A.shelf_bank(-3.75,8.35,1.35,3.45,9.65,5,1)
        A.shelf_bank(3.50,8.35,1.80,3.45,9.65,5,3)
        for i in range(3):
            o=A.cube('Lower sloped record shelf',(-2.7,6.8,.6+i*.72),(2.1,1.0,.09));o.rotation_euler.x=math.radians(14)
            for j in range(6):
                p=A.cube('Blank folded record',(-3.5+j*.31,6.6,.75+i*.72),(.22,.52,.06),3);p.rotation_euler.x=math.radians(14)
    with zone(A,'structure'):
        for i in range(12):A.cube('Access stair tread',(3.55,.1+i*.32,(i+1)*gallery/12),(1.25,.36,.12))
        for x in [2.98,4.12]:A.beam('Stair stringer',(x,-.12,.04),(x,3.95,gallery),.13)
        A.beam('Stair handrail',(2.94,-.12,1.0),(2.94,3.95,gallery+1.0),.045,4)
    for o in A.SC.objects:
        if o.name.startswith(('Access stair','Stair ')):o.location.y+=.90
    table(A,-2.15,5.2,3.55,1.9,top,gallery,'deck','underside')
    with zone(A,'wheel'):c=A.observation_wheel(-2.15,5.2,top,1.43)
    # Reserve only the open disk; its ruler remains an explicitly allowed stroke.
    disk=[(-2.15+1.345*math.cos(t),5.19,c[2]+1.345*math.sin(t)) for t in np.linspace(0,math.tau,96,endpoint=False)]
    paper(A,'Wheel open-centre paper reservation',disk,'wheel-centre',False)
    with zone(A,'wheel'):
        A.curve('Removable ruler face',[(-3.55,5.02,c[2]-.65),(-.75,5.02,c[2]-.65)],4,role='cord',reserved_content='wheel-centre')
    with zone(A,'stove'):
        A.cube('Stove body',(2.15,5.45,gallery+.55),(1.35,1.2,1.1),4)
        for x in [1.68,2.61]:A.cylinder('Stove foot',(x,5.15,gallery),(x,5.15,gallery+.15),.085,4)
        A.cylinder('Stove flue',(2.66,5.75,gallery+1.07),(2.66,5.75,5.6),.13,4)
        A.cylinder('Flue bend',(2.66,5.75,5.6),(3.95,5.75,5.95),.13,4)
        A.cylinder('Flue riser',(3.95,5.75,5.95),(3.95,5.75,roof-.12),.13,4)
        door=A.cube('Open stove door',(1.24,4.60,gallery+.53),(.85,.10,.82),4);door.rotation_euler.z=-.65
        A.beam('Stove hinge',(1.50,4.84,gallery+.12),(1.50,4.84,gallery+.96),.045,4)
    paper(A,'Reserved stove mouth',[(1.64,4.838,gallery+.22),(2.65,4.838,gallery+.22),(2.65,4.838,gallery+.93),(1.64,4.838,gallery+.93)],'stove-mouth')
    cx,cy,cz=2.15,5.45,6.48
    prof=[(.18,-1.28),(.55,-1.1),(.90,-.67),(1.04,-.05),(.97,.50),(.65,.95),(.20,1.22),(.17,1.43)]
    verts=[(cx+r*math.cos(t),cy+r*math.sin(t),cz+z) for r,z in prof for t in np.linspace(0,math.tau,48,endpoint=False)]
    glass=reserved(A.mesh('Reserve vessel',verts,[(i*48+j,i*48+(j+1)%48,(i+1)*48+(j+1)%48,(i+1)*48+j) for i in range(len(prof)-1) for j in range(48)],6,False),'vessel')
    for r,z in prof[1:]:A.ring('Vessel contour',(cx,cy,cz+z),r,r,4,'XY',.004,role='ornament',reserved_content='vessel')
    for t in np.linspace(0,math.tau,6,endpoint=False):
        A.curve('Vessel cage',[(cx+(r+.045)*math.cos(t),cy+(r+.045)*math.sin(t),cz+z) for r,z in prof],4,role='ornament',reserved_content='vessel')
    with zone(A,'structure'):
        for x in [cx-.65,cx+.65]:
            A.cylinder('Vessel suspension',(x,cy,cz+.98),(x,cy,roof-.1),.018,4,8,False)
            A.beam('Vessel yoke',(x,cy,cz+.98),(cx,cy,cz+1.43),.025,4)
    for x in [-.55,.4]:A.branch('Plaster filament',(x,8.52,4.1),4.2,.55,4,int(x*100+200))
    for i in range(2):
        n=len(A.STROKES);A.branch('Glass filament',(cx-.3+i*.5,cy-1.035,cz-.55),1.1,.4,4,50+i)
        for s in A.STROKES[n:]:s['reserved_content']='vessel'
    with zone(A,'structure'):
        for x in [-.27,.50]:A.beam('Gate jamb',(x,4.35,top),(x,4.35,6.10),.045,4)
        A.curve('Swung gate',[(-.27,4.35,top),(-.9,4.0,top),(-.9,4.,6.10),(-.27,4.35,6.1)],4)
        A.cube('Unfinished shelf board',(.50,6.0,4.58),(1.85,.70,.12))
        # One trestle; the far end of the board has no second support.
        for yy in [5.78,6.20]:A.beam('Single shelf trestle',(-.03,yy,gallery),(-.03,yy,4.53),.09)
    route=[(-2.15,5.02,c[2]),(-.60,4.95,c[2]-.06),(.10,4.35,5.60),(.18,4.90,5.16),(.53,5.70,4.67),(1.42,5.70,4.67)]
    A.curve('Vermilion route',route,5,role='red_route')
    clerk(A,-3.85,4.05,gallery,(-3.27,5.0,c[2]-.65),'left')
    clerk(A,3.28,4.10,gallery,(1.18,4.54,gallery+.70),'right')
    A.PARTS.update({'continuous_cord':route,'clerk_silhouettes':['left','right'],'stove_light':[2.15,4.55,gallery+.58],'floor_footprint':[[-4.4,3.55],[4.4,8.05]],'decisions':['Reserved clerks retained to agree with the caption.','Night lighting and one-trestle unfinished shelf.']})
    return (-5.8,-9.7,gallery+1.6),(0,5.45,5.10),40,-.035

def cabinet(A):
    with zone(A,'floor'):A.floor(9.2,9.,-.2)
    with zone(A,'rear-wall'):
        # A real opening in the rear wall, not a bright panel pasted over shelves.
        for x in [-3.65,3.65]:A.cube('Rear plaster pier',(x,8.80,4.4),(1.9,.20,8.8),0)
        A.cube('Rear wall below window',(0,8.80,.25),(5.4,.20,.50),0)
        A.cube('Rear wall above window',(0,8.80,7.95),(5.4,.20,1.70),0)
        for x in [-4.5,4.5]:A.cube('Side wall',(x,5.7,4.4),(.18,6.4,8.8),0)
    for i,x in enumerate([-2.025,-.675,.675,2.025]):
        for j,z in enumerate([1.325,2.975,4.625,6.275]):
            paper(A,f'Window pane {i}-{j}',[(x-.635,8.72,z-.785),(x+.635,8.72,z-.785),(x+.635,8.72,z+.785),(x-.635,8.72,z+.785)],'window')
    with zone(A,'rear-wall'):
        for x in np.linspace(-2.7,2.7,5):A.beam('Window mullion',(x,8.65,.50),(x,8.65,7.10),.040,4)
        for z in np.linspace(.50,7.10,5):A.beam('Window transom',(-2.7,8.65,z),(2.7,8.65,z),.040,4)
    sidecase(A,-4.25,5.5,3.7,.12,7.5,-1,6);sidecase(A,4.25,5.5,3.7,.12,7.5,1,6)
    cx,cy=0,4.2;hw,hd=1.64,.92;z0,z1=.62,6.30
    with zone(A,'exterior-panels'):
        base=A.cube('Cabinet solid base',(0,cy,z0),(3.47,2.04,.20))
        lid=A.cube('Cabinet solid top',(0,cy,z1),(3.55,2.10,.22));lid['underside_zone']='top-underside'
        for side in [-1,1]:
            x=side*hw
            # Solid panel pieces surround two real apertures.
            for yy in [cy-hd+.10,cy+hd-.10]:
                o=A.cube('Cabinet side panel stile',(x,yy,(z0+z1)/2),(.18,.20,z1-z0));o['interior_side']=side
            intervals=[(z0,1.35),(2.57,3.70),(4.92,z1)]
            for a,b in intervals:
                o=A.cube('Cabinet side panel solid',(x,cy,(a+b)/2),(.18,1.50,b-a));o['interior_side']=side
            for a,b in [(1.35,2.57),(3.70,4.92)]:
                leaf=A.cube('Raised inspection hatch',(x+side*.60,cy,b+.07),(1.20,1.49,.10))
                for yy in [cy-.54,cy+.54]:A.beam('Inspection hatch prop',(x,yy,a-.04),(x+side*1.04,yy,b+.02),.045,4)
        for x in [-1.43,1.43]:
            for y in [cy-.72,cy+.72]:A.cylinder('Cabinet foot',(x,y,.02),(x,y,z0-.10),.10,1,12)
    doors=[]
    for side in [-1,1]:
        hinge=np.array([side*hw,cy-hd-.10,0]);d=np.array([side*.36,-.933,0]);normal=np.array([.933,side*.36,0])
        with zone(A,'doors'):
            pts=[hinge+d*t+normal*q+np.array([0,0,z]) for z in [z0+.08,z1-.08] for t,q in [(0,-.055),(1.49,-.055),(1.49,.055),(0,.055)]]
            A.mesh('Solid opened cabinet door',pts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
            doors.append([list(hinge+d*t+np.array([0,0,z])) for t,z in [(0,z0),(1.49,z0),(1.49,z1),(0,z1)]])
            for sign in [-1,1]:
                for z in np.linspace(z0+.55,z1-.55,6):
                    A.curve('Door outer-face ornament',[hinge+d*(.75+.46*math.cos(t))+normal*(sign*.062)+np.array([0,0,z+.22*math.sin(t)]) for t in np.linspace(0,math.tau,28)],4)
    with zone(A,'mechanics'):
        for side in [-1,1]:
            x=side*1.47
            for z in [1.22,3.15,5.45]:
                for r in [.27,.36]:A.ring('Enlarged perimeter pulley',(x,cy+.72,z),r,mat=4,radius=.014)
                A.cylinder('Pulley axle',(x,cy+.57,z),(x,cy+.91,z),.055,4)
                A.cube('Pulley bearing',(x,cy+.95,z),(.22,.14,.22),4)
        crank=[(hw+.05,cy-hd+.10,2.12),(hw+.96,cy-hd+.10,2.12),(hw+.96,1.85,2.12),(hw+.96,1.85,2.64),(hw+1.28,1.85,2.64)]
        A.cube('Crank bearing block',(hw+.14,cy-hd+.10,2.12),(.24,.24,.24),4)
        A.beam('Crank shaft bracket',(hw,cy-hd+.10,1.90),(hw+.96,cy-hd+.10,1.90),.045,4)
        A.beam('Crank bearing support',(hw+.96,cy-hd+.10,1.90),(hw+.96,cy-hd+.10,2.12),.045,4)
        for a,b in zip(crank,crank[1:]):A.cylinder('Cabinet crank',a,b,.048,4)
    # A folded-shut board rests on a tilted support; no playing pieces.
    with zone(A,'exterior-panels'):
        A.cube('Board support',(0,cy+.15,z1+.19),(1.65,.75,.16))
        A.beam('Closed folded board spine',(-.95,cy-.35,z1+.21),(.95,cy-.35,z1+.21),.12)
    p0=np.array([0,cy-.36,z1+.25]);u=np.array([1,0,0]);v=np.array([0,.45,.89])
    paper(A,'Folded chessboard top',[p0-.94*u,p0+.94*u,p0+.94*u+v,p0-.94*u+v],'chessboard')
    for x in np.linspace(-.94,.94,9):A.curve('Closed board grid',[p0+x*u-.005*np.array([0,1,0]),p0+x*u+v-.005*np.array([0,1,0])],4,reserved_content='chessboard')
    for t in np.linspace(0,1,5):A.curve('Closed board grid',[p0-.94*u+t*v-.005*np.array([0,1,0]),p0+.94*u+t*v-.005*np.array([0,1,0])],4,reserved_content='chessboard')
    bench_before={o.name for o in A.SC.objects};bench_strokes=len(A.STROKES)
    z=table(A,2.4,.55,2.70,1.55,1.52,0,'bench','bench')
    before={o.name for o in A.SC.objects};P=A.folio(1.93,-.05,z+.01,1.64,1.15,0,11)
    for o in A.SC.objects:
        if o.name not in before and o.name.startswith('Open folio leaf'):reserved(o,'ledger-pages')
    for s in A.STROKES:
        if s['name']=='Blank ledger rule':s['role']='strand';s['reserved_content']='ledger-pages'
    with zone(A,'bench'):
        A.cylinder('Thread spool core',(3.35,.40,z),(3.35,.40,z+.31),.11,1)
        for zz in [z+.02,z+.30]:A.cylinder('Spool flange',(3.35,.40,zz),(3.35,.40,zz+.025),.18,1,16)
        A.cylinder('Ledger pencil',(2.85,.65,z+.024),(3.35,.95,z+.024),.018,1,8,False)
    # One helix and its loose end: one connected red source path.
    thread=[(3.35+.13*math.cos(t),.40+.13*math.sin(t),z+.07+.20*t/(math.tau*7)) for t in np.linspace(0,math.tau*7,160)]
    thread += [(3.55,.35,z+.03),(3.65,.10,z+.012),(3.4,-.05,z+.012)]
    A.curve('Vermilion spool and loose end',thread,5,role='red_route')
    A.curve('Detached belt on workbench',[(2.85+.43*math.cos(t),.25+.24*math.sin(t),z+.012) for t in np.linspace(0,5.65,55)],4,role='cord')
    # Place the foreground table within the field while leaving the void open.
    A.bpy.context.view_layer.update();shift=Vector((-.6,1.55,0))
    for o in A.SC.objects:
        if o.name not in bench_before:o.location+=shift
    for s in A.STROKES[bench_strokes:]:s['pts']=[list(Vector(p)+shift) for p in s['pts']]
    with zone(A,'bench'):
        cx,yy=-2.55,3.05;A.cube('Unoccupied chair seat',(cx,yy,1.02),(.95,.95,.13));legs=[]
        for x in [-.36,.36]:
            for y in [-.36,.36]:
                a=[cx+x,yy+y,0];b=[cx+x,yy+y,.96];A.beam('Chair leg',a,b,.085);legs.append({'bottom':a,'top':b})
        for x in [-.40,.40]:A.beam('Chair back post',(cx+x,yy-.35,1.05),(cx+x,yy-.35,2.06),.06)
        for zz in [1.50,2.05]:A.beam('Chair back rail',(cx-.40,yy-.35,zz),(cx+.40,yy-.35,zz),.06)
    A.PARTS.update({'chair_legs':legs,'cabinet_clear_volume':[[-1.05,3.15,1.0],[1.05,5.22,6.02]],'open_front_doors':doors,'folded_board_closed':True,'crank':crank,'floor_footprint':[[-3.2,2.0],[3.4,5.2]],'decisions':['Rear window retained; chair faces the cabinet.','Folded-shut chessboard rests on a tilted support for visibility.']})
    return (-4.10,-9.7,3.20),(0,4.20,3.20),38,0

def extraction(A):
    with zone(A,'floor'):
        # A shadow receiver only; no grid and no perimeter line.
        A.mesh('Floor shadow receiver',[(-4,-2,0),(4,-2,0),(4,5.0,0),(-4,5.0,0)],[(0,1,2,3)],0)
    z=table(A,0,1.72,5.05,1.90,1.90,0,'bench-top','apron')
    with zone(A,'under-bench'):A.cube('Under-bench inner back',(0,2.55,.93),(4.55,.09,1.58))
    with zone(A,'bookcases'):A.shelf_bank(2.2,3.35,1.16,.06,4.18,4,8)
    cx,cy=-1.28,1.90
    with zone(A,'plinth'):
        A.cube('Jig plinth',(cx,cy,z+.10),(.99,.72,.20),4)
        A.cube('Wrist clamp',(cx,cy-.02,z+.32),(.55,.34,.44),4)
    palm=[(-.29,0),(.30,0),(.38,.52),(.23,.89),(-.23,.88),(-.34,.48)];py=cy-.07;pz=z+.47
    with zone(A,'jig'):
        pts=[(cx+x,py+dy,pz+h) for dy in [-.06,.06] for x,h in palm]
        A.mesh('Wooden repair jig palm',pts,[tuple(range(5,-1,-1)),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)],1)
        fingers=[(-.25,.80,-.43,1.83,.068),(-.10,.88,-.08,2.08,.065),(.06,.88,.21,1.95,.062),(.22,.78,.50,1.65,.055),(-.29,.38,-.73,1.04,.077)]
        tips=[]
        for i,(x0,h0,x1,h1,r) in enumerate(fingers):
            a=np.array([cx+x0,py,pz+h0]);b=np.array([cx+x1,py,pz+h1]);m=(a+b)/2
            A.cylinder('Jig finger '+str(i+1)+' lower',a,m,r,1,10)
            A.cylinder('Jig finger '+str(i+1)+' upper',m,b,r*.83,1,10)
            A.ring('Jig hinge',m+np.array([0,-.075,0]),r*.63,mat=4,n=16)
            tips.append(b.tolist())
    before={o.name for o in A.SC.objects};P=A.folio(.94,.64,z+.012,2.12,1.73,0,0)
    for o in A.SC.objects:
        if o.name not in before and o.name.startswith('Open folio leaf'):reserved(o,'ledger-pages')
    # Construct a noncrossing sheaf in the engraving camera, then lift it back
    # into editable 3D curves. Endpoints remain exactly on the ruled page.
    eye=np.array([-4.65,-6.65,3.18]);target=np.array([-.05,1.7,2.08]);fwd=target-eye;fwd/=np.linalg.norm(fwd)
    right=np.cross(fwd,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,fwd)
    f=A.W/(2*math.tan(math.radians(36)/2))
    def project(p):
        q=np.array(p)-eye;zz=q@fwd
        return np.array([A.W/2+f*(q@right)/zz,A.H/2-f*(q@up)/zz]),zz
    def world(xy,zz):return eye+fwd*zz+right*((xy[0]-A.W/2)*zz/f)-up*((xy[1]-A.H/2)*zz/f)
    start=[]
    for finger,count in enumerate([5,5,5,4,4]):
        for j in range(count):
            p=np.array(tips[finger]);toward=eye-p;toward/=np.linalg.norm(toward);p=p+toward*.12+np.array([0,0,-.025*j]);xy,zz=project(p);start.append((xy,zz,p,finger))
    start.sort(key=lambda t:t[0][1])
    rows=[]
    for j,y in enumerate(np.linspace(.10,1.63,23)):
        # Left page, all rules have exactly one identity and endpoint.
        points=[P(-x,y,.058+.018*math.sin(math.pi*x/(2.12/2+.08))) for x in np.linspace(.99,.10,28)]
        rows.append((project(points[0])[0],points,j))
    rows.sort(key=lambda t:t[0][1]);strands=[]
    corners=np.array([project(P(x,y,.05))[0] for x in [-1.06,1.06] for y in [0,1.73]])
    targets=[]
    for j,(exy,rule,rid) in enumerate(rows):
        ep=np.array(rule[0]);_,ez=project(ep)
        if j==22:
            exy=np.array([corners[:,0].min()-A.PX_PER_MM*4.2,corners[:,1].min()-A.PX_PER_MM*3.2]);ez-=.20
        targets.append((exy,ez,ep,rule,rid,j==22))
    # A global invertible parabolic shear gives the sheaf its curvature.
    # Two-exchange optimal matching in the inverse plane cannot retain a
    # crossing: uncrossing two Euclidean segments strictly shortens them.
    bend=.00115
    def inverse(q):return np.array([q[0],q[1]-bend*(q[0]-A.W*.5)**2])
    def forward(q):return np.array([q[0],q[1]+bend*(q[0]-A.W*.5)**2])
    ss=np.array([inverse(x[0]) for x in start]);ee=np.array([inverse(x[0]) for x in targets])
    costs=np.linalg.norm(ss[:,None]-ee[None],axis=2);assignment=np.arange(23)
    for iteration in range(1000):
        changed=False
        for i in range(23):
            for j in range(i+1,23):
                a,b=assignment[i],assignment[j]
                if costs[i,b]+costs[j,a]<costs[i,a]+costs[j,b]-1e-8:
                    assignment[i],assignment[j]=b,a;changed=True
        if not changed:break
    black_number=0
    for j,(sxy,sz,sp,finger) in enumerate(start):
        destination=assignment[j];exy,ez,ep,rule,rid,is_red=targets[destination];pts=[]
        for t in np.linspace(0,1,100):
            xy=forward(ss[j]*(1-t)+ee[destination]*t)
            pts.append(world(xy,sz*(1-t)+ez*t-.75*math.sin(math.pi*t)))
        if not is_red:pts.extend(rule[1:])
        if not is_red:black_number+=1
        number=23 if is_red else black_number
        A.curve('Ledger strand '+str(number),pts,5 if is_red else 4,role='red_route' if is_red else 'strand',reserved_content='ledger-pages')
        if is_red:A.curve('Unreached last ledger rule',rule,4,role='strand',reserved_content='ledger-pages')
        strands.append({'finger':finger,'start':list(sp),'end':list(pts[-1]),'landing':list(ep),'rule_id':rid,'red':is_red,'source_name':'Ledger strand '+str(number),'approach_samples':100})
    # The right page retains blank rules but no false heading or writing.
    for y in np.linspace(.10,1.63,23):A.curve('Right page blank rule',[P(x,y,.058+.018*math.sin(math.pi*x/(2.12/2+.08))) for x in np.linspace(.10,.99,28)],4,role='strand',reserved_content='ledger-pages')
    with zone(A,'apron'):A.stool(-.12,.10,1.04)
    for o in A.SC.objects:
        if o.name=='Stool seat':reserved(o,'stool-seat',True)
    A.PARTS.update({'jig_fingers':5,'jig_tips':tips,'ledger_strands':strands,'blank_ruled_ledger':True,'floor_footprint':[[-2.50,.05],[2.55,2.7]],'decisions':['The twenty-third strand is red and stops short; no separate red desk thread.','No ledger heading strip.']})
    return tuple(eye),tuple(target),36,0

def office(A):
    with zone(A,'floor'):A.mesh('Floor shadow receiver',[(-3.7,3.7,0),(3.7,3.7,0),(3.7,5.7,0),(-3.7,5.7,0)],[(0,1,2,3)],0)
    with zone(A,'back-wall'):A.cube('Alcove back wall',(0,5.60,4.05),(7.3,.18,8.1),0)
    with zone(A,'corners'):
        for x in [-3.53,3.53]:A.cube('Alcove inner corner',(x,5.12,4.05),(.16,.94,8.1),0)
    r={'xmin':-1.20,'xmax':1.20,'zmin':2.85,'zmax':5.82,'y':5.25}
    paper(A,'Reserved recess',[(r['xmin'],5.25,r['zmin']),(r['xmax'],5.25,r['zmin']),(r['xmax'],5.25,r['zmax']),(r['xmin'],5.25,r['zmax'])],'recess')
    with zone(A,'reveal'):
        for x in [-1.28,1.28]:A.cube('Recess reveal',(x,5.15,4.335),(.11,.27,3.13),0)
        for z in [2.77,5.90]:A.cube('Recess reveal',(0,5.15,z),(2.66,.27,.11),0)
    with zone(A,'lattice'):
        # These side bands have volume and a measured midtone behind the tracery.
        for x in [-2.30,2.30]:
            A.cube('Lattice side bay',(x,5.31,4.0),(1.30,.14,7.7),0)
            for xx in [x-.4,x+.4]:A.filigree_column(xx,5.18,.12,7.78,.30)
        A.arch('Crown outer rail',0,5.10,6.35,6.7,1.35,4,.018)
        A.arch('Crown inner rail',0,5.08,6.55,5.8,.95,4,.012)
        for x in np.linspace(-2.5,2.5,7):A.ring('Sparse crown cell',(x,5.06,7.27-.10*x*x),.11,.15,4,n=20)
    with zone(A,'shelf-undersides'):
        for side in [-1,1]:
            for z in [1.3,3.9,6.4]:A.cube('Cantilevered instrument shelf',(side*2.43,4.92,z),(1.48,.88,.12))
    with zone(A,'instruments'):
        # Four simple instruments, all supported on a named shelf.
        A.cube('Ring instrument foot',(-2.40,4.86,4.05),(.55,.38,.15),4)
        A.cylinder('Ring instrument upright',(-2.40,4.86,4.12),(-2.40,4.86,4.63),.025,4)
        A.ring('Ring on stand',(-2.40,4.86,4.89),.28,.28,4,radius=.015)
        A.cylinder('Shelf rod',(2.05,4.83,4.0),(2.85,4.83,4.0),.045,4)
        sphere(A,'Shelf sphere',(2.40,4.88,1.60),.23)
        for i in range(4):A.cube('Stack of rules',(-2.42,4.85,1.40+i*.075),(.83,.33,.055),1)
    with zone(A,'structure'):
        A.beam('Upper bracket',(-.64,5.05,6.70),(.64,5.05,6.70),.05,4)
        for x in [-.64,.64]:A.beam('Bracket upright',(x,5.05,6.7),(x,5.05,7.05),.04,4)
        A.ring('Bare seal mounting ring',(0,5.02,6.70),.085,mat=4,radius=.01)
        A.ring('Pull ring',(0,5.03,1.40),.20,.25,4,radius=.017)
        A.beam('Pull ring peg',(0,5.40,1.4),(0,5.02,1.4),.035,4)
    upper=[(0,4.99,6.61),(0,4.99,6.50)]
    lower=[(0,4.99,1.66),(0,4.99,2.14)]
    A.curve('Upper black cord',upper,4,role='cord');A.curve('Lower black cord',lower,4,role='cord')
    A.curve('Upper red terminal',[(0,4.99,6.50),(0,4.99,6.14)],5,role='red_terminal')
    A.curve('Lower red terminal',[(0,4.99,2.14),(0,4.99,2.50)],5,role='red_terminal')
    A.PARTS.update({'reserved_recess':r,'upper_cord':upper+[(0,4.99,6.14)],'lower_cord':lower+[(0,4.99,2.50)],'cord_gap_z':[2.50,6.14],'floor_footprint':[[-3.5,4.7],[3.5,5.7]],'decisions':['Black cords with two red free-end terminals.','Bare black seal-mount retained.','The explicit gap-clearance check governs the contradictory sentence about the recess being larger than the gap.']})
    return (0,-13.7,4.335),(0,5.25,4.335),24,0

def construct(A,key):
    return {'maintained-workshop':workshop,'empty-cabinet':cabinet,'extraction-of-the-hand':extraction,'office-without-a-seal':office}[key](A)
