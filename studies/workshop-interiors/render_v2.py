"""Caller-side print engraving; sole content input is the exported scene.json.

The nine upstream hatching bodies and the ray core are not modified.
"""
from pathlib import Path
from types import SimpleNamespace
import os,sys,json,math,time,hashlib
os.environ.setdefault('NUMBA_NUM_THREADS','4')
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter,distance_transform_edt
from numba import njit,prange
import cairosvg

ROOT=Path(__file__).resolve().parent;KEY=os.environ.get('PLATE','empty-cabinet');OUT=ROOT/'output/v2'/KEY
sys.path.insert(0,str(ROOT/'vendor'))
import raycore as rc
import claude_hatching as CH
D=json.loads((OUT/'scene.json').read_text());V=np.asarray(D['vertices']);F=D['faces'];N=np.asarray(D['normals']);M=np.asarray(D['mats']);HATCH=np.asarray(D['hatch']);ZONES=np.array(D['zones']);RESERVED=np.array(D['reserved'])
W,H=D['camera']['resolution'];EYE=np.array(D['camera']['eye']);TARGET=np.array(D['camera']['target']);FOCAL=D['camera']['focal_px'];CX,CY=D['camera']['principal_point']
PRINT=D['print'];CFG=D['engraving'];PX_PER_MM=PRINT['px_per_mm'];mm=lambda v:v*PX_PER_MM
WEIGHTS=PRINT['weights_mm'];NEAR=.25;MARGIN=mm(3.1);GRID=5
def unit(p):return np.asarray(p)/np.linalg.norm(p)
FWD=unit(TARGET-EYE);RIGHT=unit(np.cross(FWD,[0,0,1]));UP=np.cross(RIGHT,FWD)
def project(p):
    p=np.asarray(p);q=p-EYE;z=q@FWD;safe=np.maximum(z,NEAR)
    return CX+FOCAL*(q@RIGHT)/safe,CY-FOCAL*(q@UP)/safe,z
def jac(P,u,v):
    q=P-EYE;z=np.maximum(q@FWD,NEAR);x=q@RIGHT;y=q@UP;a=np.empty((*P.shape[:-1],2,2))
    for i,d in enumerate([u,v]):
        a[...,0,i]=FOCAL*((d@RIGHT)*z-x*(d@FWD))/z**2
        a[...,1,i]=-FOCAL*((d@UP)*z-y*(d@FWD))/z**2
    return a
def rays(xy):
    d=FWD+((xy[:,0]-CX)/FOCAL)[:,None]*RIGHT-((xy[:,1]-CY)/FOCAL)[:,None]*UP;d/=np.linalg.norm(d,axis=1)[:,None]
    return np.broadcast_to(EYE,d.shape).copy(),d
TRIS=[];OWN=[]
for k,f in enumerate(F):
    for j in range(1,len(f)-1):
        t=V[np.array(f)[[0,j,j+1]]]
        if np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))>1e-10:TRIS.append(t);OWN.append(k)
TRIS=np.asarray(TRIS);OWN=np.array(OWN);BVH=rc.build_bvh(TRIS,M[OWN]);TRI_OWNER=OWN[BVH[8]]

@njit(cache=True,parallel=True)
def visible(P,eye,blo,bhi,nodes,v0,e1,e2):
    out=np.zeros(len(P),np.bool_)
    for i in prange(len(P)):
        d=eye-P[i];t=np.linalg.norm(d);d/=max(1e-12,t)
        _,hit=rc.trace(P[i]+d*.006,d,1e-5,t-.012,True,blo,bhi,nodes,v0,e1,e2);out[i]=hit<0
    return out
@njit(cache=True,parallel=True)
def light(P,N,eye,sun,right,local_pos,local_strength,blo,bhi,nodes,v0,e1,e2):
    out=np.zeros(len(P))
    for i in prange(len(P)):
        n=N[i].copy()
        if np.dot(n,eye-P[i])<0:n=-n
        cos=max(0.,np.dot(n,sun));_,hit=rc.trace(P[i]+n*.012,sun,1e-5,100.,True,blo,bhi,nodes,v0,e1,e2)
        direct=cos*(1 if hit<0 else .05);ao=0.
        for sign in [-1.,1.]:
            d=n+sign*.5*right;d/=np.linalg.norm(d);t,h=rc.trace(P[i]+n*.015,d,1e-5,1.2,False,blo,bhi,nodes,v0,e1,e2)
            if h>=0:ao+=.5*(1-t/1.2)
        ambient=max(.11,.26-.008*max(0.,P[i,1]));local=0.
        if local_strength>0:
            d=local_pos-P[i];distance=np.linalg.norm(d);d/=max(distance,.001)
            _,h=rc.trace(P[i]+n*.012,d,1e-5,max(.001,distance-.03),True,blo,bhi,nodes,v0,e1,e2)
            local=local_strength*max(0.,np.dot(n,d))/(1+(distance/2.5)**2)*(.05 if h>=0 else 1)
        out[i]=min(1.,max(.06,ambient*(1-.55*ao)+.8*direct+local))
    return out

def owner_map(width,height):
    result=np.full((height,width),-1,np.int32)
    for row in range(0,height,48):
        yy,xx=np.mgrid[row:min(row+48,height),:width]
        xy=np.column_stack([(xx.ravel()+.5)*W/width,(yy.ravel()+.5)*H/height]);o,d=rays(xy)
        _,hit=rc.first_hits(o,d,200.,*BVH[:6]);valid=hit>=0;face=np.full(len(hit),-1,np.int32);face[valid]=TRI_OWNER[hit[valid]]
        result[row:row+len(yy)]=face.reshape(yy.shape)
    return result

def frame_clip(p,margin=MARGIN):
    planes=[(RIGHT+(CX-margin)/FOCAL*FWD,0),(-RIGHT+(W-margin-CX)/FOCAL*FWD,0),(-UP+(CY-margin)/FOCAL*FWD,0),(UP+(H-margin-CY)/FOCAL*FWD,0),(FWD,NEAR)]
    q=np.asarray(p,float)
    for n,off in planes:
        if len(q)<3:return np.zeros((0,3))
        out=[]
        for a,b in zip(q,np.roll(q,-1,axis=0)):
            da=(a-EYE)@n-off;db=(b-EYE)@n-off
            if da>=0:out.append(a)
            if (da>=0)!=(db>=0):out.append(a+(b-a)*da/(da-db))
        q=np.asarray(out)
    return q
def split(xy,keep,sid=None):
    ids=np.flatnonzero(keep)
    if len(ids)<2:return []
    breaks=np.diff(ids)!=1
    if sid is not None:breaks|=np.diff(sid[ids])!=0
    return [xy[g] for g in np.split(ids,np.flatnonzero(breaks)+1) if len(g)>1 and np.linalg.norm(np.diff(xy[g],axis=0),axis=1).sum()>.45]
def simplify(p,tol=.06):
    if len(p)<3:return p
    keep=np.zeros(len(p),bool);keep[[0,-1]]=True;todo=[(0,len(p)-1)]
    while todo:
        a,b=todo.pop()
        if b-a<2:continue
        d=p[b]-p[a];v=p[a+1:b]-p[a];den=d@d;t=np.clip(v@d/den,0,1) if den>1e-20 else np.zeros(len(v))
        err=np.sum((v-t[:,None]*d)**2,axis=1);j=int(np.argmax(err))
        if err[j]>tol*tol:k=a+1+j;keep[k]=True;todo.extend([(a,k),(k,b)])
    return p[keep]

STROKE_AUDIT=[]
def stroke(points,metadata=None):
    samples=[]
    for a,b in zip(points[:-1],points[1:]):
        sx,sy,z=project(np.array([a,b]))
        if min(z)<=NEAR:continue
        length=np.hypot(np.diff(sx)[0],np.diff(sy)[0])
        if length>20000:continue
        samples.extend(np.linspace(a,b,max(2,int(length/1.0)+1))[:-1])
    if not samples:return []
    samples.append(points[-1]);p=np.asarray(samples);x,y,z=project(p);xy=np.column_stack([x,y]);framed=(x>MARGIN)&(x<W-MARGIN)&(y>MARGIN)&(y<H-MARGIN)&(z>NEAR)
    seen=np.zeros(len(p),bool);seen[framed]=visible(p[framed],EYE,*BVH[:6])
    if metadata:
        lengths=np.linalg.norm(np.diff(xy,axis=0),axis=1)/PX_PER_MM
        hidden=~(seen[:-1]&seen[1:]);runs=np.split(np.arange(len(lengths)),np.flatnonzero(np.diff(hidden.astype(int)))+1)
        maxgap=max([float(lengths[r].sum()) for r in runs if len(r) and hidden[r[0]]] or [0])
        STROKE_AUDIT.append({**metadata,'source_samples':len(p),'hidden_samples':int((~seen).sum()),'length_mm':float(lengths.sum()),'visible_length_mm':float(lengths[~hidden].sum()),'maximum_hidden_run_mm':maxgap,'visible_paths':len(split(xy,seen)),'first_xy':list(xy[0]),'last_xy':list(xy[-1])})
    return split(xy,seen)

def paint(paths,scale=1):
    im=Image.new('L',(max(1,int(W/scale)),max(1,int(H/scale))),0);draw=ImageDraw.Draw(im)
    for p,w in paths:draw.line([tuple(q/scale) for q in p],fill=255,width=max(1,round(w/scale)))
    return im
def down(im):return np.asarray(im.resize((W//GRID,H//GRID),Image.Resampling.BOX))/255.
def svg_text(groups):
    items=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{PRINT["width_mm"]}mm" height="{PRINT["height_mm"]}mm" viewBox="0 0 {W} {H}"><title>{D["title"]} / second pass / printed-size engraving</title>']
    for label,paths,col in groups:
        items.append(f'<g inkscape:groupmode="layer" inkscape:label="{label}" id="{label[:2]}" fill="none" stroke="{col}" stroke-linecap="round" stroke-linejoin="round">')
        for p,w in paths:
            q=simplify(p);data='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in q);items.append(f'<path stroke-width="{w:.4f}" d="{data}"/>')
        items.append('</g>')
    return '\n'.join(items+['</svg>'])

def main():
    start=time.time();centres=np.array([V[f].mean(0) for f in F]);front=np.einsum('ij,ij->i',N,EYE-centres)>1e-8
    zref=float((TARGET-EYE)@FWD);edges={};structure=[];ornament=[];red=[]
    for k,f in enumerate(F):
        for a,b in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted([a,b])),[]).append(k)
    for (a,b),adj in edges.items():
        if not any(front[adj]):continue
        name=D['names'][adj[0]];reg=RESERVED[adj[0]]
        if name in ['Joined floor','Floor shadow receiver']:continue
        silhouette=len(adj)==1 or not all(front[adj]);crease=HATCH[adj[0]] and len(adj)>1 and N[adj[0]]@N[adj[1]]<.82
        if not(silhouette or crease):continue
        zc=max(NEAR,(V[[a,b]].mean(0)-EYE)@FWD);factor=float(np.clip(zref/zc,.80,1.30))
        backdrop=ZONES[adj[0]] in ['rear-wall','back-wall','floor','bookcases']
        w=WEIGHTS['reserved_outline'] if reg else WEIGHTS['backdrop'] if backdrop else min(.30,(WEIGHTS['silhouette'] if silhouette else WEIGHTS['crease'])*factor)
        structure.extend((q,mm(w)) for q in stroke(V[[a,b]]))
    for s in D['strokes']:
        role=s.get('role','ornament');w=mm(WEIGHTS[role]);p=np.array(s['pts'])
        paths=stroke(p,{'name':s['name'],'role':role,'reserved_content':s.get('reserved_content')})
        (red if s['mat']==5 else structure if role in ['strand','cord','backdrop'] else ornament).extend((q,w) for q in paths)
    if KEY in ['maintained-workshop','empty-cabinet']:
        b=mm(2.0);gap=mm(1.5)
        structure.append((np.array([[W-b,H-b-gap],[W-b,b],[b,b],[b,H-b],[W-b-gap,H-b]]),mm(.12)))
    print('structure',len(structure),'ornament',len(ornament),'red',len(red),flush=True)
    coarse=owner_map(W//GRID,H//GRID);coarse_reg=np.full(coarse.shape,'',dtype=RESERVED.dtype);ok=coarse>=0;coarse_reg[ok]=RESERVED[coarse[ok]]
    halo=np.zeros(coarse.shape)
    if KEY=='office-without-a-seal':
        halo=(distance_transform_edt(coarse_reg!='recess')<=mm(CFG['halos_mm']['recess'])/GRID).astype(float)
        coarse_zones=np.full(coarse.shape,'',dtype=ZONES.dtype);coarse_zones[ok]=ZONES[coarse[ok]]
        halo[coarse_zones=='reveal']=0
    if KEY=='extraction-of-the-hand':
        im=Image.new('L',(W,H),0);draw=ImageDraw.Draw(im)
        for s in D['strokes']:
            if s['name'].startswith('Ledger strand '):
                x,y,_=project(np.array(s['pts']));draw.line(list(zip(x,y)),fill=255,width=round(mm(2*CFG['halos_mm']['strands'])))
        halo=(down(im)>.1).astype(float)
        coarse_zones=np.full(coarse.shape,'',dtype=ZONES.dtype);coarse_zones[ok]=ZONES[coarse[ok]]
        halo*=np.isin(coarse_zones,['bench-top','reserved'])
    Image.fromarray((halo*255).astype('uint8')).save(OUT/'halo-mask.png')
    used=gaussian_filter(down(paint(structure+ornament)),.7)*.32+halo
    CH.S=SimpleNamespace(EYE=EYE,project=project,screen_jacobian=jac,SURFACES=[])
    CH.BITS=8;CH.BITREV=np.array([int(f'{i:08b}'[::-1],2) for i in range(256)])/256
    CH.C_MAX=CFG['coverage_cap'];CH.GAMMA=CFG['gamma'];CH.C_SPLIT=CFG['split'];CH.MIN_GAP=mm(CFG['minimum_gap_mm']);CH.BREAK_KEEP=.795;CH.GRID=GRID
    delta=CH.MIN_GAP*zref/FOCAL
    families=((.64,delta,mm(WEIGHTS['hatch'])),(-.72,delta*1.06,mm(WEIGHTS['hatch'])))
    probes=visible(centres+N*.006,EYE,*BVH[:6]);faces=[]
    for k,f in enumerate(F):
        if not HATCH[k] or not front[k]:continue
        p=frame_clip(V[f])
        if len(p)<3:continue
        if not probes[k] and not visible(p*.92+p.mean(0)*.08+N[k]*.006,EYE,*BVH[:6]).any():continue
        faces.append((k,p))
    sun=unit(CFG['sun']);local=np.array(CFG['stove_light']);strength=.9 if KEY=='maintained-workshop' else 0.
    def prepare(families,deep=False):
        CH.FAMILIES=families;st=CH.Strokes()
        for k,p in faces:
            if deep and CFG['tone_targets'].get(ZONES[k],.35)<.66:continue
            CH.hatch_on_face(st,p,N[k],.82,k)
        st.finish();owner=-1-st.attr['surf'];sx,sy=st.xy.T
        framed=(sx>MARGIN)&(sx<W-MARGIN)&(sy>MARGIN)&(sy<H-MARGIN)&(st.z>NEAR)
        seen=np.zeros(len(st.world),bool);seen[framed]=visible(st.world[framed],EYE,*BVH[:6])
        raw=np.zeros(len(st.world));raw[seen]=1-light(st.world[seen],N[owner[seen]],EYE,sun,RIGHT,local,strength,*BVH[:6])
        target=np.zeros(len(raw))
        for name,base in CFG['tone_targets'].items():
            ix=(ZONES[owner]==name)&seen
            if not ix.any():continue
            target[ix]=base+.08*(raw[ix]-float(raw[ix].mean()))
        if KEY=='maintained-workshop':
            ix=(ZONES[owner]=='rear-wall')&seen;r=np.hypot((sx[ix]-W*.50)/(W*.55),(sy[ix]-H*.44)/(H*.7)).clip(0,1)
            target[ix]=.15+.25*r*r+.04*(raw[ix]-.6)
        ground=ZONES[owner]=='floor'
        if ground.any():
            if KEY in ['office-without-a-seal','extraction-of-the-hand']:
                # A 2-D projected footprint supplies the falloff, not world y.
                footprint=np.array(D['parts']['floor_footprint']);pts=np.array([[footprint[0,0],footprint[0,1],0],[footprint[1,0],footprint[0,1],0],[footprint[1,0],footprint[1,1],0],[footprint[0,0],footprint[1,1],0]])
                xx,yy,_=project(pts);mask=Image.new('L',(W//GRID,H//GRID),0);ImageDraw.Draw(mask).polygon(list(zip(xx/GRID,yy/GRID)),fill=255)
                dist=distance_transform_edt(np.asarray(mask)==0)*GRID/PX_PER_MM
                gx=np.clip((sx[ground]/GRID).astype(int),0,dist.shape[1]-1);gy=np.clip((sy[ground]/GRID).astype(int),0,dist.shape[0]-1)
                target[ground]=.25*np.clip(1-dist[gy,gx]/25,0,1)**2
                if KEY=='office-without-a-seal':target[ground]*=np.exp(-np.abs(st.world[ground,1]-5.5)*2.5)
            else:target[ground]*=np.clip((sy.max()-sy[ground])/(H*.35),0,1)
        # Compensate the union of crossing strokes, not just their summed widths.
        linear=2*(1-np.sqrt(1-np.clip(target,0,.82)))
        for name,multiplier in CFG.get('allocation_multipliers',{}).items():linear[ZONES[owner]==name]*=multiplier
        d=np.clip(linear/CH.C_MAX,0,1)**(1/CH.GAMMA)
        return st,owner,seen,d
    st,owner,seen,d=prepare(families)
    keep=CH.allocate_hatch(st,d,used,seen);hatches=split(st.xy,keep,st.sid)
    print('first hatch',len(st.world),'samples',len(hatches),'paths',flush=True)
    kept_world=[st.world[keep][::7]];kept_owner=[owner[keep][::7]]
    hatch_paths=[(q,mm(WEIGHTS['hatch'])) for q in hatches]
    # The allocator subtracts used ink itself. Supply the full target again;
    # supplying only residual darkness here would subtract the first pass twice.
    deep_counts=[];second=None
    for angle in CFG.get('deep_pass_angles',[CFG['deep_pass_angle']]):
        second=((families[0][0]+angle,delta*1.03,mm(.10)),(families[1][0]+angle,delta*1.09,mm(.10)))
        st2,own2,seen2,d2=prepare(second,True)
        used2=used+gaussian_filter(down(paint(hatch_paths)),.35)
        keep2=CH.allocate_hatch(st2,d2,used2,seen2);more=split(st2.xy,keep2,st2.sid);hatch_paths.extend((q,mm(.10)) for q in more)
        kept_world.append(st2.world[keep2][::7]);kept_owner.append(own2[keep2][::7]);deep_counts.append(len(more))
        print('deep hatch',angle,len(st2.world),'samples',len(more),'paths',flush=True)
    groups=[('01 hatching',hatch_paths,PRINT['inks']['black']),('02 structure',structure,PRINT['inks']['black']),('03 ornament and tracery',ornament,PRINT['inks']['black']),('04 vermilion',red,PRINT['inks']['red'])]
    text=svg_text(groups);(OUT/(KEY+'.svg')).write_text(text)
    (OUT/(KEY+'.png')).write_bytes(cairosvg.svg2png(bytestring=text.encode(),output_width=W,output_height=H,background_color='#f0e9da'))
    np.savez_compressed(OUT/'hatch-audit.npz',world=np.vstack(kept_world),owner=np.concatenate(kept_owner))
    (OUT/'stroke-audit.json').write_text(json.dumps(STROKE_AUDIT,indent=2))
    record={'title':D['title'],'revision':2,'blender':D['blender'],'resolution':[W,H],'PRINT_WIDTH_MM':PRINT['width_mm'],'PRINT_HEIGHT_MM':PRINT['height_mm'],'PX_PER_MM':PX_PER_MM,'weights_mm':WEIGHTS,'ink_count':2,'inks':PRINT['inks'],'coverage_cap':CH.C_MAX,'gamma':CH.GAMMA,'families':families,'deep_families':second,'z_reference':zref,'tone_targets':CFG['tone_targets'],'allocation_multipliers':CFG.get('allocation_multipliers',{}),'scene_sha256':hashlib.sha256((OUT/'scene.json').read_bytes()).hexdigest(),'svg_sha256':hashlib.sha256(text.encode()).hexdigest(),'hatch_paths':len(hatch_paths),'deep_paths':sum(deep_counts),'deep_pass_counts':deep_counts,'structure_paths':len(structure),'ornament_paths':len(ornament),'red_paths':len(red),'maximum_black_contour_mm':.30,'generator':D['generator'],'limits':CFG['limits'],'seconds':round(time.time()-start,1)}
    (OUT/'manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)

if __name__=='__main__':main()
