"""Seeded woodland drawing grammars. Metres, Z up; illustrative, not growth simulations."""
import random, math
import numpy as np
from .model import Plant, bezier, unit
from .species import axis, radial
SPECIES={
 'maidenhair':('Northern maidenhair fern','Adiantum pedatum'),
 'wild_ginger':('Wild ginger','Asarum canadense'),
 'bloodroot':('Bloodroot','Sanguinaria canadensis'),
 'dutchmans_breeches':("Dutchman's breeches",'Dicentra cucullaria'),
 'solomons_seal':("Solomon's seal",'Polygonatum biflorum')}

def blade(p,base,angle,length,width,kind='heart',tilt=.15):
    """Radial, gently cupped leaf host; explicit margin and palmate veins."""
    b=np.array(base); u=radial(angle); v=radial(angle+math.pi/2)
    n=112; theta=np.linspace(-math.pi+.09,math.pi-.09,n)
    if kind=='heart':
        # Deep basal sinus, two shoulders, pointed distal tip.
        rr=(.68+.32*np.cos(theta))*(1-.87*np.exp(-((abs(theta)-math.pi)/.35)**2))
    elif kind=='lobed':
        rr=(.78+.22*np.cos(theta))*(.77+.23*np.cos(7*theta))
        rr*=1-.85*np.exp(-((abs(theta)-math.pi)/.27)**2)
    else: # asymmetric fan pinna: narrow petiolule and scalloped distal margin
        theta=np.linspace(-1.35,1.35,n)
        rr=(.85+.15*np.cos(9*theta))
    outline=np.array([b+u*(length*r*math.cos(t))+v*(width*r*math.sin(t))+
                      [0,0,tilt*length*r*math.cos(t)-.08*length*r*r] for t,r in zip(theta,rr)])
    verts=[b];rings=5
    for k in range(1,rings+1):
        f=k/rings
        verts.extend(b+(outline-b)*f+np.array([0,0,.025*length*math.sin(math.pi*f)]))
    faces=[]
    for j in range(n-1):faces.append((0,1+j,2+j))
    for k in range(rings-1):
        a=1+k*n;c=a+n
        for j in range(n-1):faces.extend([(a+j,c+j,c+j+1),(a+j,c+j+1,a+j+1)])
    owner=p.surface(verts,faces,'leaf',kind)
    p.line(np.vstack([b,outline,b]),'leaf',owner=owner)
    for j in range(8,n-5,12):
        path=[verts[0]]+[verts[1+(k-1)*n+j] for k in range(1,rings+1)]
        p.line(path,'vein',1,owner)
        for k in (2,3,4):
            for sign in (-1,1):
                jj=max(0,min(n-1,j+sign*4))
                p.line([verts[1+(k-1)*n+j],verts[1+k*n+jj]],'vein',2,owner)
    p.organs.append({'type':kind+'_leaf','base':b.tolist()})

def bell(p,top,length=.021,radius=.004,role='flower'):
    top=np.array(top);n=16;verts=[]
    for i,t in enumerate(np.linspace(0,1,9)):
        r=radius*(.55+.45*math.sin(t*math.pi*.85))
        for j in range(n):
            a=j*2*math.pi/n;z=-length*t
            if i==8:z+=.0015*math.cos(6*a)
            verts.append(top+[r*math.cos(a),r*math.sin(a),z])
    faces=[]
    for i in range(8):
        for j in range(n):
            a=i*n+j;b=i*n+(j+1)%n
            faces.extend([(a,b,b+n),(a,b+n,a+n)])
    own=p.surface(verts,faces,role,'tubular_flower')
    for j in (0,4,8,12):p.line(np.array(verts)[j::n],role,1,own)
    p.line(np.array(verts)[-n:].tolist()+[verts[-n]],role,0,own)

def maidenhair(p,rng,stage):
    for f in range(4):
        a=f*2.4+rng.uniform(-.3,.3);h=rng.uniform(.28,.44)
        root=radial(a)*rng.uniform(.005,.025);fork=root+radial(a)*.04+[0,0,h]
        axis(p,root,fork,.0011,fork*.55)
        # A bifurcating horseshoe rachis with pinnae along its outside.
        for sign in (-1,1):
            ts=np.linspace(0,1,25)
            rach=np.array([fork+radial(a)*( .13*math.sin(t*2.1))+
                radial(a+math.pi/2)*sign*.15*(1-math.cos(t*2.1))+[0,0,.025*math.sin(t*math.pi)] for t in ts])
            p.stem(rach,.0008,end_radius=.0003)
            for j,t in enumerate(np.linspace(.15,.96,6)):
                q=rach[round(t*24)];phi=a+sign*(.15+t*1.8)
                L=(.09+.045*math.sin(t*math.pi))*rng.uniform(.92,1.08)
                end=q+radial(phi)*L+[0,0,.012]
                axis(p,q,end,.00038)
                for k in range(7):
                    tt=.13+k*.115;pt=q+(end-q)*tt
                    for ss in (-1,1):
                        blade(p,pt,phi+ss*1.15,.014*(1-.45*tt),.0075,'fan',.08)
        p.organs.append({'type':'forked_pedate_frond','position':fork.tolist()})

def wild_ginger(p,rng,stage):
    for shoot in range(3):
        a=shoot*2.4+rng.uniform(-.25,.25);root=radial(a)*.035
        for side in (-1,1):
            phi=a+side*.8;tip=root+radial(phi)*.035+[0,0,rng.uniform(.10,.16)]
            axis(p,root,tip,.0018)
            blade(p,tip,phi,.09*rng.uniform(.9,1.1),.075,'heart',rng.uniform(.1,.4))
        if stage=='flowering':
            c=root+[0,0,.018];bell(p,c,.014,.006,'calyx')
            for j in range(3):p.leaf(c-[0,0,.013],radial(j*2*math.pi/3,.25),.015,.008,role='calyx',veins=False)

def bloodroot(p,rng,stage):
    for i in range(3):
        a=i*2.4+rng.uniform(-.28,.28);root=radial(a)*.025;tip=root+radial(a)*.04+[0,0,rng.uniform(.10,.16)]
        axis(p,root,tip,.0018)
        blade(p,tip,a,.065 if stage=='flowering' else .11,.065 if stage=='flowering' else .11,'lobed',.5)
        if stage=='flowering':
            c=root+radial(a+.8)*.025+[0,0,rng.uniform(.21,.27)]
            axis(p,root,c,.0018)
            for j in range(8):
                phi=j*math.pi/4;p.leaf(c,radial(phi,.15),.024 if j%2 else .029,.011,role='flower',veins=False,bend=.1)
            for j in range(22):
                phi=j*2.4;pt=c+radial(phi)*(.003+.003*(j%3)/2)
                axis(p,pt,pt+[0,0,.006],.00045)
                p.leaf(pt+[0,0,.006],radial(phi,.3),.0025,.002,role='pollen',veins=False)

def dissect(p,q,phi,L,depth):
    q=np.array(q);end=q+radial(phi)*L+[0,0,.012]
    axis(p,q,end,.0005 if depth else .00025)
    if depth:
        for t in (.35,.62,.85):
            for sign in (-1,1):dissect(p,q+(end-q)*t,phi+sign*.85,L*.43*(1-.3*t),depth-1)
    else:
        for sign in (-1,0,1):p.leaf(end,radial(phi+sign*.55,.3),.018,.006,shape='fern',bend=-.1)

def breeches_flower(p,c,phi):
    # Two inflated, upward-pointing spurs meet a lower yellow mouth.
    c=np.array(c);side=radial(phi);normal=radial(phi+math.pi/2)
    outline=np.array([(-.002,0),(-.009,.003),(-.014,.012),(-.013,.027),(-.008,.030),(-.004,.014),(0,.010),(.004,.014),(.008,.030),(.013,.027),(.014,.012),(.009,.003),(.002,0)])
    verts=[];N=len(outline)
    for sign in (-1,1):
        verts.append(c+normal*sign*.004+[0,0,.011])
        verts.extend(c+side*x+[0,0,z] for x,z in outline)
    faces=[]
    for j in range(N):
        k=(j+1)%N;faces.extend([(0,1+j,1+k),(N+1,N+2+k,N+2+j)])
    own=p.surface(verts,faces,'flower','paired_spurs')
    rim=[c+side*x+[0,0,z] for x,z in outline];p.line(rim+[rim[0]],'flower',owner=own)
    p.leaf(c,side,.005,.005,role='pollen',veins=False)

def dutchmans_breeches(p,rng,stage):
    for j in range(5):
        a=j*2.4+rng.uniform(-.18,.18);tip=radial(a)*.04+[0,0,rng.uniform(.055,.085)]
        axis(p,[0,0,0],tip,.0012)
        for s in (-1,0,1):dissect(p,tip,a+s*.9,.08,1)
    if stage=='flowering':
        for a in (.1,2.6):
            end=radial(a)*.15+[0,0,rng.uniform(.22,.28)]
            stem=bezier([0,0,0],[0,0,.39],end,45);p.stem(stem,.0012)
            for idx in (18,22,26,30,34,38,42):
                q=stem[idx];c=q+radial(a)*.008-[0,0,.048]
                axis(p,q,c+[0,0,.022],.0005)
                breeches_flower(p,c,a+math.pi/2)

def solomons_seal(p,rng,stage):
    for k in range(3):
        phi=k*2.4+rng.uniform(-.18,.18);root=radial(phi)*.025
        stem=bezier(root,root+[0,0,.92],root+radial(phi)*rng.uniform(.38,.47)+[0,0,.48],61)
        p.stem(stem,.003,end_radius=.0008)
        for j,t in enumerate(np.linspace(.30,.97,11)):
            q=stem[round(t*60)];a=phi+(-1 if j%2 else 1)*1.05
            L=.14*(1-.35*t)*rng.uniform(.9,1.1)
            p.leaf(q,radial(a,.25),L,L*.40,roll=.1,bend=-.12,veins=False)
            # Parallel curved veins lie on same generated blade host.
            surf=p.surfaces[-1];v=surf.vertices.reshape(-1,3,3)
            own=len(p.surfaces)-1
            for u in (.25,.5,.75):
                for edge in (0,2):p.line(v[:,1]*(1-u)+v[:,edge]*u,'vein',1,own)
            if stage=='flowering' and j<9:
                for side in (-1,1):
                    top=q+radial(phi+math.pi/2)*side*.009-[0,0,.023]
                    axis(p,q,top,.0005);bell(p,top)
