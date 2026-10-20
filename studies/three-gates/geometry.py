"""Scene construction for The Three Gates; executed by build.py before BVH creation."""

def beam(a,b,width=.10,depth=None,mat=2,name='ironwork'):
 a,b=np.asarray(a,float),np.asarray(b,float);v=unit(b-a)
 u=unit(np.cross(v,[0,0,1]))
 if np.linalg.norm(u)<.1:u=np.array([1.,0,0])
 q=unit(np.cross(v,u));depth=width if depth is None else depth
 rings=[p+np.array([u*width/2+q*depth/2,-u*width/2+q*depth/2,-u*width/2-q*depth/2,u*width/2-q*depth/2]) for p in [a,b]]
 for k in range(4):face([rings[0][k],rings[0][(k+1)%4],rings[1][(k+1)%4],rings[1][k]],mat,True,name)
 face(rings[0][::-1],mat,True,name);face(rings[1],mat,True,name)
 for k in range(4):line([rings[0][k],rings[1][k]],.7,1 if mat==3 else 0)

def wheel(cx,y,cz,r=.45):
 # A real torus, hub, axle and six spokes, rather than a floating wheel symbol.
 n,m=40,8;a=np.arange(n)*2*np.pi/n;b=np.arange(m)*2*np.pi/m
 pts=np.array([[[cx+(r+.034*np.cos(t))*np.cos(s),y+.034*np.sin(t),cz+(r+.034*np.cos(t))*np.sin(s)] for t in b] for s in a])
 for i in range(n):
  for j in range(m):face([pts[i,j],pts[(i+1)%n,j],pts[(i+1)%n,(j+1)%m],pts[i,(j+1)%m]],3,False,'handwheel rim')
 for rr in [r-.033,r+.033]:
  line([[cx+rr*np.cos(s),y-.036,cz+rr*np.sin(s)] for s in np.linspace(0,2*np.pi,81)],.85,1)
 for s in a[::7]:
  tube([[cx+.08*np.cos(s),y,cz+.08*np.sin(s)],[cx+(r-.025)*np.cos(s),y,cz+(r-.025)*np.sin(s)]],.022,3,6,'wheel spoke')
 tube([[cx,y-.12,cz],[cx,y+.35,cz]],.085,3,12,'wheel axle')

# The channel bed is actually excavated; water is a separate mesh surface.
GX=np.r_[[-40.,-30.,-22.,-16.,-12.],np.linspace(-11,11,89),[12.,16.,22.,30.,40.]]
GY=np.r_[[-30.,-20.,-13.,-10.],np.linspace(-8.5,10.8,79),[12.,16.,22.,30.,40.,55.]]
xx,yy=np.meshgrid(GX,GY)
ZZ=1.45+.065*(yy+3)+.30*np.sin(xx*.43+yy*.18)+.16*np.cos(yy*.65-xx*.2)
ZZ+=.6*np.exp(-((xx+7.8)**2+(yy-7.5)**2)/19)
ZZ+=1.5*np.exp(-((yy-26)/10)**2)*(.7+.3*np.sin(xx*.15))
ZZ=np.maximum(ZZ,.65)
channel_width=3.55+np.maximum(yy-11,0)*.08
ZZ[abs(xx)<channel_width]=-.25
approach=(abs(xx)>4.2)&(abs(xx)<7.2)&(yy>.55)&(yy<2.65)
ZZ[approach]=3.78
def height(x,y):
 x,y=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float))
 x,y=np.clip(x,GX[0],GX[-1]),np.clip(y,GY[0],GY[-1])
 ix=np.clip(np.searchsorted(GX,x,side='right')-1,0,len(GX)-2)
 iy=np.clip(np.searchsorted(GY,y,side='right')-1,0,len(GY)-2)
 u=(x-GX[ix])/(GX[ix+1]-GX[ix]);v=(y-GY[iy])/(GY[iy+1]-GY[iy])
 a,b,c,d=ZZ[iy,ix],ZZ[iy,ix+1],ZZ[iy+1,ix+1],ZZ[iy+1,ix]
 return np.where(u>=v,a+u*(b-a)+v*(c-b),a+v*(d-a)+u*(c-d))
for j in range(len(GY)-1):
 for i in range(len(GX)-1):
  p=[[GX[i],GY[j],ZZ[j,i]],[GX[i+1],GY[j],ZZ[j,i+1]],[GX[i+1],GY[j+1],ZZ[j+1,i+1]],[GX[i],GY[j+1],ZZ[j+1,i]]]
  face([p[0],p[1],p[2]],0,False,'terrain');face([p[0],p[2],p[3]],0,False,'terrain')

def water_height(y):
 y=np.asarray(y,float)
 return np.where(y>=.7,2.18,np.where(y<=-1.9,.36,.36+(y+1.9)/2.6*1.82))
for a,b in [(-30.,-1.9),(-1.9,.7),(.7,55.)]:
 wa=3.48+max(a-11,0)*.08;wb=3.48+max(b-11,0)*.08
 face([[-wa,a,float(water_height(a))],[wa,a,float(water_height(a))],[wb,b,float(water_height(b))],[-wb,b,float(water_height(b))]],5,False,'water')
# Open downstream water has long broken current lines; the upper pool has short ripples.
rng=np.random.default_rng(43)
for x in np.arange(-3.4,3.4,.125):
 for a,b in [(-18.0,rng.uniform(-5.3,-3.4)),(rng.uniform(-4.3,-3.2),.55)]:
  y=np.linspace(a,b,100);px=x+.035*np.sin(y*2.1+x*3.7)
  line(np.column_stack([px,y,water_height(y)+.018]),rng.uniform(.42,.68),2)
for y in np.arange(2.95,45.,.34):
 for _ in range(2):
  x=rng.uniform(-3.25,2.5);L=rng.uniform(.35,1.3);t=np.linspace(0,1,20)
  line(np.column_stack([x+t*L,y+.025*np.sin(t*np.pi),np.full(len(t),2.198)]),.55,2)
# Small foam arcs just beyond the foot of the apron.
for _ in range(90):
 x,y=rng.uniform(-3.35,3.35),rng.uniform(-2.65,-1.98);r=rng.uniform(.05,.18);t=np.linspace(.1,np.pi-.1,12)
 line(np.column_stack([x+r*np.cos(t),y+r*.45*np.sin(t),np.full(len(t),.382)]),.6,2)

# Retaining walls and four masonry piers support the bridge and divide three gates.
for s in [-1,1]:
 lo,hi=sorted([s*3.48,s*4.25]);box((lo,-.65,-.35),(hi,6.6,3.57),1,'retaining wall')
 box((lo-.12,-.8,3.57),(hi+.12,6.7,3.77),1,'wall coping')
 for z in np.arange(.15,3.5,.34):
  line([[s*3.475,-.64,z],[s*3.475,6.58,z]],.55)
  for y in np.arange(-.5,6.5,.7):
   off=.35 if int(round(z/.34))%2 else 0
   line([[s*3.474,y+off,z],[s*3.474,y+off,z+.30]],.42)
for x in [-3.55,-1.18,1.18,3.55]:
 w=.33 if abs(x)<2 else .68
 box((x-w/2,.50,-.3),(x+w/2,2.8,3.68),1,'gate pier')
 box((x-w/2-.09,.40,3.43),(x+w/2+.09,2.9,3.69),1,'pier cap')
 for z in np.arange(.1,3.4,.33):
  line([[x-w/2,.492,z],[x+w/2,.492,z]],.6)
  line([[x+w/2+.006,.51,z],[x+w/2+.006,2.78,z]],.5)

# Timber footbridge, continuous girders, open rails and restrained diagonal bracing.
box((-7.12,.42,3.68),(7.12,2.85,3.91),4,'timber footbridge')
for y in [.60,2.65]:box((-7.15,y-.09,3.38),(7.15,y+.09,3.69),2,'bridge girder')
for x in np.arange(-7,7.1,.27):line([[x,.45,3.918],[x,2.82,3.918]],.52)
for y in [.43,2.84]:
 posts=np.arange(-7,7.01,1.0)
 for x in posts:beam([x,y,3.90],[x,y,4.96],.065,mat=2,name='rail post')
 for z in [4.35,4.96]:beam([-7.02,y,z],[7.02,y,z],.055,mat=2,name='handrail')
 for k in range(len(posts)-1):
  if k%3==0:beam([posts[k],y,4.05],[posts[k+1],y,4.88],.035,mat=2,name='rail brace')

# Three raised timber gates, guides and connected handwheel mechanisms.
GATE_CENTERS=[-2.36,0.,2.36];GATE_BOTTOMS=[1.82,2.30,1.45]
for cx,bottom in zip(GATE_CENTERS,GATE_BOTTOMS):
 top=bottom+1.6
 box((cx-.99,.72,bottom),(cx+.99,.94,top),4,'sluice leaf')
 for z in np.arange(bottom+.1,top,.20):line([[cx-.96,.711,z],[cx+.96,.711,z]],.55)
 for dx in [-.97,.97]:
  beam([cx+dx,.68,bottom-.04],[cx+dx,.68,top+.06],.075,mat=3,name='gate edge')
  beam([cx+dx,1.06,.05],[cx+dx,1.06,5.1],.085,mat=2,name='gate guide')
 for z in [bottom+.13,top-.13]:beam([cx-.97,.67,z],[cx+.97,.67,z],.085,mat=3,name='gate strap')
 beam([cx-.88,.64,bottom+.22],[cx+.88,.64,top-.22],.055,mat=3,name='gate brace')
 for dx in [-.65,.65]:
  box((cx+dx-.14,.8,3.90),(cx+dx+.14,1.27,4.02),2,'hoist footing')
  beam([cx+dx,1.02,3.98],[cx+dx,1.02,6.00],.09,mat=2,name='hoist upright')
 beam([cx-.73,1.02,6.00],[cx+.73,1.02,6.00],.12,mat=2,name='hoist crosshead')
 beam([cx,1.03,top-.04],[cx,1.03,6.30],.065,mat=3,name='lifting rack')
 for z in np.arange(max(top,4.0),6.2,.12):line([[cx-.065,.983,z],[cx+.065,.983,z]],.7,1)
 box((cx-.17,.95,5.65),(cx+.17,1.32,6.13),2,'hoist gearbox')
 wheel(cx,.82,5.95,.43)

# Stone steps land at bridge level; their bases intersect the land, not empty air.
for k in range(10):
 y=-2.7+k*.32;z=1.80+k*.211
 box((-6.94,y,.20),(-5.43,y+.34,z),1,'bank stair')
box((-6.94,.50,.2),(-5.43,.90,3.91),1,'stair landing')

# A winding bank path and an old split rail fence give the scene a different scale.
path_y=np.linspace(2.8,10.1,150);path_x=6.15+1.1*np.sin((path_y-2.8)*.48)
for dx in [-.42,.42]:
 x=path_x+dx;line(np.column_stack([x,path_y,height(x,path_y)+.024]),.62)
fence=[]
for x in np.linspace(-10,-4.9,8):
 y=6.8+.35*np.sin(x*.7);z=float(height(x,y));fence.append((x,y,z))
 beam([x,y,z-.08],[x+.03,y,z+1.0],.095,mat=4,name='fence post')
for a,b in zip(fence,fence[1:]):
 for dz in [.4,.82]:beam(np.array(a)+[0,0,dz],np.array(b)+[0,0,dz],.065,mat=4,name='split rail')

# Two grounded mooring posts and their sagging rope.
bollards=[]
for y in [-4.8,-6.6]:
 x=-4.65;z=float(height(x,y));bollards.append(np.array([x,y,z+.60]))
 tube([[x,y,z-.1],[x,y,z+.68]],.12,2,12,'mooring post')
 tube([[x,y,z+.64],[x,y,z+.72]],.18,2,12,'mooring cap')
t=np.linspace(0,1,60);a,b=bollards
p=(1-t[:,None])*a+t[:,None]*b;p[:,2]-=.25*np.sin(t*np.pi);line(p,1.05)

# Exposed river stones, with actual polygon surfaces above the downstream water.
ROCKS=[]
for x,y,r,h in [(-2.9,-3.4,.37,.29),(3.12,-4.4,.32,.22),(-3.16,-6.3,.40,.34),(2.9,-7.3,.47,.27)]:
 n=7;aa=np.arange(n)*2*np.pi/n;radii=rng.uniform(.8,1.15,n)*r
 q=np.column_stack([x+radii*np.cos(aa),y+radii*np.sin(aa),np.full(n,.29)])
 top=np.array([x+.06,y-.03,.36+h]);ROCKS.append(top.tolist())
 for k in range(n):
  face([q[k],q[(k+1)%n],top],1,True,'river stone');line([q[k],top,q[(k+1)%n]],.65)

# Sparse contour marks; leave the approach and open water legible.
con=contourpy.contour_generator(x=GX,y=GY,z=ZZ)
for z in np.arange(.9,4.6,.36):
 for p in con.lines(z):
  if len(p)<4:continue
  dense=[]
  for a,b in zip(p[:-1],p[1:]):dense.extend(np.linspace(a,b,max(2,int(np.linalg.norm(a-b)/.035)+1))[:-1])
  dense=np.vstack([dense,p[-1]]);keep=(abs(dense[:,0])>4.45)&(abs(dense[:,0])<17)&(dense[:,1]>-10)&(dense[:,1]<24)
  for ids in np.split(np.flatnonzero(keep),np.flatnonzero(np.diff(np.flatnonzero(keep))!=1)+1):
   if len(ids)>2:
    q=dense[ids];line(np.column_stack([q,height(q[:,0],q[:,1])+.018]),.48)
# Sparse distant ridge courses continue behind the main structure.
for yy0 in [20,24,28,32]:
 x=np.linspace(-32,32,350);y=yy0+1.3*np.sin(x*.12+yy0*.4)
 line(np.column_stack([x,y,height(x,y)+.028]),.43)
