"""A mill across an incised coulee, seen from a real masonry aperture.

The window, mill, waterwheel and bridge all participate in Blender's evaluated
geometry and the shared ray model. No screen-space window mask is used.
"""
import numpy as np

CAMERAS=[('main',(0,-13,7.8),(0,15,5),2300.),
         ('low',(.45,-13.3,7.5),(0,15,5),2300.)]
DOOR_X=1.0
WHEEL_X,WHEEL_Y=-3.2,14.05

def river_y(x):
    x=np.asarray(x)
    return 8.8+5.25*np.exp(-((x+3.2)/4.3)**2)+.6*np.sin((x+3.2)*.2)

def water_z(x):return 2.55-.020*(np.asarray(x)+3.2)

def river_width(x):return 1.55+.70*(1-np.exp(-((np.asarray(x)+3.2)/6)**2))

PLANAR_TREES=[(-9,13,6.5),(11,22,5.8),(-16,24,5.2),(16,29,5)]


def prepare(out):
    from pathlib import Path
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    from scipy.ndimage import gaussian_filter
    from lib.process_art.terrain import erode_heightfield
    x=np.linspace(-30,30,145);y=np.linspace(-20,44,153);xx,yy=np.meshgrid(x,y)
    rng=np.random.default_rng(615)
    # Declared initial valley; the D8 process adds tributary incision.
    axis=river_y(xx)
    h=3.1+.030*yy+.18*np.sin(xx*.29+yy*.14)
    h+=2.9*np.exp(-((yy-29-.10*xx)/4.8)**2)
    distance=abs(yy-axis)
    bed=water_z(xx)-.42
    blend=np.clip((2.5-distance)/1.1,0,1)
    h=h*(1-blend)+np.minimum(h,bed)*blend
    h+=gaussian_filter(rng.normal(0,.20,xx.shape),.7)
    # Protect the wet channel and its shoulders, plus the actual mill pad.
    # The water level is a composed illustration datum, not a fluid solver.
    fixed=(abs(xx-1)<3.8)&(yy>14.3)&(yy<20)
    wet=distance<river_width(xx)+.55
    h[wet]=np.minimum(h[wet],np.broadcast_to(water_z(xx)-.42,h.shape)[wet])
    shoulder=(distance>=river_width(xx)+.55)&(distance<river_width(xx)+2.)
    bench=water_z(xx)+.10+.35*(distance-river_width(xx)-.55)
    h[shoulder]=np.minimum(h[shoulder],bench[shoulder])
    fixed|=distance<river_width(xx)+2.1
    fixed|=(abs(xx)<5)&(yy< -4)
    state=erode_heightfield(h,steps=70,incision=.12,diffusion=.028,fixed_mask=fixed)
    state.update(x=x,y=y,steps=np.asarray(70),seed=np.asarray(615))
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'terrain-state.npz',**state)


def build_scene(A,T):
    box,beam,ink,mesh,arch,ground,roof=T.box,T.beam,T.ink,T.mesh,T.arch,T.terrain_z,T.roof
    # One task: duration repeats complete storeys in the mill body.
    x,y=1.,17.;z=float(ground(x,y))+.1;w,d=7.,5.
    box('mill foundation',(x-w/2-.25,y-d/2-.25,z-1.8),(x+w/2+.25,y+d/2+.25,z))
    h=T.story_nodes('mill',x,y,z,w,d,A['nodes'][0]['bays'])
    for floor in range(A['nodes'][0]['bays']):
        for dx in (-1.5,0,1.5):
            if floor<2 and dx==0:continue
            Z=z+floor*1.04
            box('mill inner window',(x+dx-.20,y-d/2-.045,Z+.24),(x+dx+.20,y-d/2-.028,Z+.69),2)
            box('mill window sill',(x+dx-.25,y-d/2-.10,Z+.19),(x+dx+.25,y-d/2-.015,Z+.25))
    roof('mill roof',x,y,z+h,w+.7,d+.7,1.45)
    arch('mill door',DOOR_X,y-d/2-.14,z,1.25,1.9)
    # Slate loading canopy, held by timber columns, projects from the right.
    box('mill loading deck',(4.6,14.2,z-.20),(7.6,18.5,z))
    for X in (4.8,7.3):
        for Y in (14.4,18.2):beam('mill porch post',(X,Y,z-.1),(X,Y,z+2.4),.09)
    roof('mill porch roof',6.1,16.4,z+2.4,3.5,4.9,.8)
    beam('mill chimney',(-1.1,18.1,z+h-.4),(-1.1,18.1,z+h+2.6),.33,3,8)
    # A wheel in the XZ plane, with axle and pedestal. Rings are solid meshes.
    cx,cy=WHEEL_X,WHEEL_Y
    cz=float(water_z(cx))+1.73
    for r in (1.5,1.78):
        ts=np.linspace(0,2*np.pi,49)
        for a,b in zip(ts,ts[1:]):
            beam('mill wheel rim',(cx+r*np.cos(a),cy,cz+r*np.sin(a)),(cx+r*np.cos(b),cy,cz+r*np.sin(b)),.055,2,4)
    beam('mill wheel axle',(cx,cy-.4,cz),(cx,15.4,cz),.13)
    beam('mill wheel bearing bracket',(cx,15.4,cz),(-2.2,15.4,cz),.16)
    beam('mill wheel bearing pier',(cx,15.4,float(ground(cx,15.4))-.3),(cx,15.4,cz),.15,1,6)
    for a in np.arange(12)*np.pi/6:
        beam('mill wheel spoke',(cx,cy,cz),(cx+1.7*np.cos(a),cy,cz+1.7*np.sin(a)),.045)
        p=np.array([cx+1.65*np.cos(a),cy,cz+1.65*np.sin(a)])
        beam('mill wheel paddle',p+[0,-.4,0],p+[0,.4,0],.11,2,4)
    # Footbridge crosses the actual lowered channel; supports reach ground.
    for X in (DOOR_X-.75,DOOR_X+.75):
        beam('Bridge stringer',(X,-5.3,3.4),(X,11.2,3.4),.10)
        beam('Bridge railing',(X,-5.3,4.35),(X,11.2,4.35),.045)
        for Y in (-5.3,-2,1.4,4.5,8,11):
            beam('Bridge upright',(X,Y,float(ground(X,Y))-.25),(X,Y,4.4),.055)
    for Y in np.arange(-5.3,11.2,.27):beam('Bridge plank',(DOOR_X-.9,Y,3.47),(DOOR_X+.9,Y,3.47),.09,2,4)
    # Supported approach steps continue the bridge to the entrance.
    for i,Y in enumerate(np.arange(11.2,14.5,.45)):
        top=3.52+(z-3.52)*i/7
        box('mill approach step',(DOOR_X-.9,Y,float(ground(DOOR_X,Y))-.3),(DOOR_X+.9,Y+.46,max(top,float(ground(DOOR_X,Y))+.08)))
    # Deep stone opening, with the interior timber sash removed.
    # Wall and sill extend outside the frame; each is solid, ray-tested masonry.
    for label,lo,hi in [
        ('left jamb',(-7,-6.8,1),(-3.65,-5.55,12)),
        ('right jamb',(3.65,-6.8,1),(7,-5.55,12)),
        ('head',(-3.65,-6.8,9.8),(3.65,-5.55,13)),
        ('sill',(-3.9,-7.3,3.6),(3.9,-5.3,4.05))]:
        box('Window '+label,lo,hi,1)
    # Coarse stone courses belong only to the window reveal, not to the view.
    for Z in np.arange(4.3,9.7,.47):
        ink('Window left mortar',[(-3.66,-6.78,Z),(-3.66,-5.56,Z)],.10)
        ink('Window right mortar',[(3.66,-6.78,Z),(3.66,-5.56,Z)],.10)
    # A continuous water surface occupies the cut channel, occludes ground
    # marks and carries broken, flow-aligned engraving strokes.
    water=T.material('Stream water','#385f6b',roughness=.3)
    xs=np.linspace(-26,25,221);ys=river_y(xs);zs=water_z(xs);ws=river_width(xs)
    verts=np.vstack([np.c_[xs,ys-ws,zs],np.c_[xs,ys+ws,zs]])
    mesh('Stream water surface',verts,[(i,i+1,i+222,i+221) for i in range(220)],water,False)
    rng=np.random.default_rng(611)
    for off in np.linspace(-.86,.86,17):
        start=-25.+rng.uniform(0,1)
        while start<24:
            end=min(24,start+rng.uniform(.35,1.25));q=np.linspace(start,end,12)
            ink('Stream flow ripple',np.c_[q,river_y(q)+off*river_width(q)+.025*np.sin(q*4+off*7),water_z(q)+.025],.085)
            start=end+rng.uniform(.25,.8)
    for side in (-1,1):
        ink('Stream bank waterline',np.c_[xs,ys+side*ws,zs+.025],.12)
    # Small broken arcs at the immersed lower paddles indicate the wheel's contact.
    for j in range(5):
        q=np.linspace(-.35,.35,24)
        ink('Wheel wake',np.c_[cx+.3+j*.23+q,cy-.45-j*.07+.06*np.cos(q*8),water_z(cx+.3+j*.23+q)+.032],.10)
    T.oak('Volume oak west',-11,19,6.7,614)
    T.oak('Volume oak east',9.8,24,5.8,617)
    return {'mill':z+h},{'mill':(x,y,z)},[[-3,13.9,7.9,20.4]],[]


if __name__=='__main__':
    from scene import output_dir
    prepare(output_dir('window','incised'))
