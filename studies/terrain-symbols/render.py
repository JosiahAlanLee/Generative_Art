"""Drape local Driftless strokes onto evaluated Blender terrain, then engrave.

Field paths and upright symbol planes have separate 3D mappings. Neither is a
screen overlay: both are clipped against the same evaluated model and camera.
"""
from pathlib import Path
import json, time, subprocess, hashlib
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
import build as B
import occlusion as M

OUT=B.OUT
def densify(p, step):
    p=np.asarray(p,float);length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    if length[-1]<1e-10:return p[:1]
    t=np.linspace(0,length[-1],max(2,int(np.ceil(length[-1]/step))+1))
    return np.column_stack([np.interp(t,length,p[:,i]) for i in range(p.shape[1])])

def surface_paths(patches):
    """Local 2D -> world XY -> downward ray hit on the terrain-only BVH.

    Endpoints alone are insufficient: sample BEFORE projecting onto the curved
    mesh, or a long symbol segment can tunnel through a ridge.
    """
    sources=[]
    for s in patches['farm']['strokes']:
        p=np.asarray(s['pts']).reshape(-1,2)
        if len(p)<2:continue
        xy=np.column_stack([-17+p[:,0]*34/200, -8+p[:,1]*39/160])
        sources.append(('field',xy,s['pen']))
    # An invented, unkeyed rosette: clear enough to reveal folding / hiding.
    center=np.array([-2.8,10.0]);radius=5.8
    for r in [radius,radius*.84]:
        t=np.linspace(0,2*np.pi,241)
        sources.append(('rosette',center+np.column_stack([np.cos(t),np.sin(t)])*r,2))
    t=np.arange(13)*2*np.pi/12
    ring=center+radius*.76*np.column_stack([np.cos(t),np.sin(t)])
    for i in range(12):sources.append(('rosette',ring[[i,(i+5)%12]],2))
    for i in range(12):
        a=t[i];d=np.array([np.cos(a),np.sin(a)])
        sources.append(('rosette',center+d[None]*np.array([[radius*.92],[radius*1.09]]),2))
    pens=[[],[],[],[]];all_world=[];all_kind=[];stats={}
    mapped=[]
    for kind,xy,pen in sources:
        # Explicit host bounds reject any part outside the atlas. A missing
        # terrain ray produces a gap, never a bridge to the next valid hit.
        xy=densify(xy,.010)
        p,hit,_=B.drape(xy)
        valid=hit&(abs(xy[:,0])<18)&(xy[:,1]>-9)&(xy[:,1]<32)
        # The path remains an open track; field texture stays out of its width.
        if kind=='field':
            lane=4.4+.65*np.sin((xy[:,1]-6)*.19)
            valid &= (abs(xy[:,0]-lane)>.65)|(xy[:,1]>6)
        mapped.append({'kind':kind,'pen':pen,'world':p.tolist(),'valid':valid.tolist()})
        safe=np.where(np.isfinite(p),p,0)
        sx,sy,z=B.project(safe)
        framed=(sx>12)&(sx<B.W-12)&(sy>12)&(sy<B.H-12)&(z>B.NEAR)
        seen=np.zeros(len(p),bool);idx=valid&framed
        if idx.any():seen[idx]=B.visible(p[idx],*B.BVH[:6])
        keep=seen&valid&framed
        width=1.0 if kind=='rosette' else .60
        paths=B.split_paths(np.column_stack([sx,sy]),keep)
        pens[pen].extend((q,width) for q in paths)
        all_world.append(p[keep]);all_kind.extend([kind]*int(keep.sum()))
        d=stats.setdefault(kind,{'candidates':0,'hidden_by_model':0,'survives':0,'paths':0})
        d['candidates']+=int(idx.sum());d['hidden_by_model']+=int((idx&~seen).sum())
        d['survives']+=int(keep.sum());d['paths']+=len(paths)
    # Keep the mapped coordinates for editable Blender curves; source points
    # are full 3D, with host holes recorded separately.
    if B.VIEW_NAME=='main':(OUT/'mapped-ground.json').write_text(json.dumps(mapped,separators=(',',':')))
    np.savez_compressed(OUT/f'surface-audit-{B.VIEW_NAME}.npz',world=np.vstack(all_world),kind=np.asarray(all_kind))
    return [('03 draped field key',pens[0],'#615d48'),('04 draped field vegetation',pens[1],'#728064'),
            ('05 draped rosette and field accent',pens[2],'#a4563e'),('06 distant field tint',pens[3],'#9d9b7e')],stats

def place(patch):
    rng=np.random.default_rng(271);out=[]
    def add(p,x,y,h,w=.68):
        z=float(B.height(x,y))+.015
        out.append(M.Instance(p,p.get('origin',[20,40]),[x,y,z],h/p.get('height',p.get('h',20)),w))
    add(patch['oak'],-10,1.3,7.4,.8)
    add(patch['oak'],11,14.4,4.8,.64)
    for x,y,h in [(-16,25,3.4),(-12,26,2.9),(-8,26,3.5),(-4,28,3.4),(2,29,3.9),(8,27,3.2),(13,29,3.6),(18,25,3.9)]:
        add(patch['pine'],x,y,h,.5)
    for _ in range(380):
        x,y=rng.uniform(-14,14),rng.uniform(-7,7)
        # Patchy verge and meadows; leave the central draped symbol readable.
        if abs(x)<4.5 and y>-.5:continue
        if abs(x-(4.4+.65*np.sin((y-6)*.19)))<.8:continue
        if rng.random()>.70-.02*max(y,0):continue
        i=int(rng.integers(len(patch['plants'])))
        add(patch['plants'][i],x,y,rng.uniform(.28,.70),.57)
    return out

def structure():
    normals=np.asarray(B.D['normals']);centers=np.array([f['p'].mean(0) for f in B.FACES])
    front=np.einsum('ij,ij->i',normals,B.EYE-centers)>0
    # Shared mesh indices let internal triangulation edges disappear while
    # genuine silhouettes and corners remain. Terrain folds come from hatches.
    edges={};terrain_ids=set(B.D['terrain_faces'])
    for k,f in enumerate(B.D['faces']):
        if k in terrain_ids:continue
        for a,b in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted([a,b])),[]).append(k)
    paths=[]
    for (a,b),owners in edges.items():
        if not any(front[owners]):continue
        if len(owners)==1 or not all(front[owners]) or normals[owners[0]]@normals[owners[-1]]<.85:
            paths.extend((q,.85) for q in B.stroke_project(B.V[[a,b]]))
    for p,w,ink in B.LINES:paths.extend((q,w) for q in B.stroke_project(p))
    return paths

def engrave(field,edges):
    CH=B.CH
    CH.FAMILIES=((.68,.060,.8),(-.72,.078,.68))
    CH.C_MAX=.38;CH.C_SPLIT=.12;CH.MIN_GAP=2.35
    st=CH.Strokes();CH.hatch_on_surface(st,B.terrain,.40)
    for i,f in enumerate(B.FACES):
        if not f['hatch']:continue
        n=np.asarray(B.D['normals'][i])
        if n@(B.EYE-f['p'].mean(0))<=0:continue
        CH.hatch_on_face(st,f['p'],n,.56,i)
    st.finish();print('Hatch samples',len(st.world),flush=True)
    normals=np.empty_like(st.world);albedo=np.ones(len(st.world))
    for k in np.unique(st.attr['surf']):
        mask=st.attr['surf']==k
        if k==0:
            normals[mask]=B.terrain.normal(st.world[mask,0],st.world[mask,1])
            albedo[mask]=1.05
        else:
            f=B.FACES[-1-int(k)];normals[mask]=B.D['normals'][-1-int(k)]
            albedo[mask]=.62 if f['mat']==2 else .84 if f['mat'] in [3,4] else 1.
    x,y=st.xy.T
    frame=(x>12)&(x<B.W-12)&(y>12)&(y<B.H-12)&(st.z>B.NEAR)
    seen=np.zeros(len(st.world),bool);seen[frame]=B.visible(st.world[frame],*B.BVH[:6])
    d=np.zeros(len(st.world));d[seen]=1-B.light(st.world[seen],normals[seen],*B.BVH[:6])*albedo[seen]
    # Reserve tone for the actual projected field and architecture before the
    # two hatch families compete. More marks means less hatch ink.
    used=Image.new('L',(B.W//5,B.H//5),0);draw=ImageDraw.Draw(used)
    for paths in [edges]+[p for _,p,_ in field]:
        for q,w in paths:draw.line([tuple(p/5) for p in q],fill=220,width=1)
    used=gaussian_filter(np.asarray(used,float)/255,.65)*.42
    keep=CH.allocate_hatch(st,d,used,seen)
    np.savez_compressed(OUT/f'hatch-audit-{B.VIEW_NAME}.npz',world=st.world[keep][::4])
    paths=[(q,.72) for q in B.split_paths(st.xy,keep,st.sid)]
    return [('01 shared-light crosshatching',paths,'#66604d'),('02 modeled structure',edges,'#46463a')]

if __name__=='__main__':
    start=time.time()
    patch=json.loads((OUT/'driftless-meadow-patches.json').read_text())
    field,stats=surface_paths(patch);print('Draped marks',stats,flush=True)
    edges=structure();groups=engrave(field,edges)+field
    B.svg_write(f'Terrain_{B.VIEW_NAME}_unplanted',groups)
    instances=place(patch);buf=np.full((B.H*M.K,B.W*M.K),np.inf)
    for inst in instances:M.stamp(buf,inst)
    depth=M.model_depth(buf);pens,audit=M.plant_strokes(instances,buf,return_audit=True)
    clipped=[(label,M.clip_screen_paths(paths,buf,depth),col) for label,paths,col in groups]
    flora=[('07 upright symbol key',pens[0],'#414b37'),('08 upright foliage',pens[1],'#637351'),
           ('09 flowers',pens[2],'#ac624a'),('10 foliage tint',pens[3],'#929877')]
    B.svg_write(f'Terrain_{B.VIEW_NAME}',clipped+flora)
    B.svg_write(f'Terrain_{B.VIEW_NAME}_plants',flora)
    inside=audit['survives'];nearest=M.lookup(buf,audit['xy'][inside])
    np.savez_compressed(OUT/f'plants-audit-{B.VIEW_NAME}.npz',xy=audit['xy'][inside],owner_depth=audit['owner_depth'][inside],nearest_depth=nearest)
    if B.VIEW_NAME=='main':
        plants=[{'kind':i.patch.get('kind','plant'),'root':i.root.tolist(),'scale':i.s,
                 'strokes':[i.world(np.asarray(s['pts']).reshape(-1,2)).tolist() for s in i.patch['strokes']]} for i in instances]
        (OUT/'mapped-plants.json').write_text(json.dumps(plants,separators=(',',':')))
    info={'title':'Driftless terrain symbols','view':B.VIEW_NAME,'camera':B.CAM,'blender':B.D['blender'],
          'faces':len(B.FACES),'surface':stats,'plants':len(instances),'plant_samples':int(inside.sum()),
          'plant_owner_depth_violations':int((nearest<audit['owner_depth'][inside]-M.EPS_PLANT).sum()),
          'engine_sha256':hashlib.sha256((B.ROOT/'vendor/driftless-engine.js').read_bytes()).hexdigest(),
          'seconds':round(time.time()-start,1)}
    (OUT/f'manifest-{B.VIEW_NAME}.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2),flush=True)
