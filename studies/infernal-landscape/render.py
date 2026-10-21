"""Print-sized crosshatching, terrain draping, volume and planar vegetation.

The nine extracted hatch bodies and the Driftless engine remain unchanged.
All choices about spacing, lighting, tone, ink, and composition live here.
"""
from pathlib import Path
import hashlib,json,re,time
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter
import build as B
import occlusion as M
from compile import classify_routes

OUT=B.OUT
PX_PER_MM=20
PRINT_WIDTH_MM=156
MM=dict(hatch=.10,gap=.22,silhouette=.25,crease=.16,ornament=.12,
        foliage=.08,branch=.10,field=.085,vermilion=.32)
INK='#242820';RED='#a32b24'
# Tone hierarchy (measured in checks.py): buildings lead; fence, service
# supports and piers are furniture at crease weight; foliage is lighter than
# masonry; a plinth is lighter than the storeys it carries; open ground is the
# lightest drawn surface. Gains multiply the lit darkness before allocation.
FURNITURE=('Meadow fence','Service support','Service tray','Entry pier')
PLINTH=(' foundation',' entrance base','Release lift landing',' waiting passage')
GAIN=dict(terrain=.28,plinth=.62,furniture=.55)


def densify(p,step):
    p=np.asarray(p,float);a=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    if a[-1]<1e-10:return p[:1]
    t=np.linspace(0,a[-1],max(2,int(np.ceil(a[-1]/step))+1))
    return np.column_stack([np.interp(t,a,p[:,i]) for i in range(p.shape[1])])


def surface_paths(patches):
    sources=[]
    for s in patches['farm']['strokes']:
        q=np.asarray(s['pts']).reshape(-1,2)
        if len(q)>1:sources.append(('field',np.c_[-19+q[:,0]*38/200,-9+q[:,1]*39/160],0))
    if B.TERRAIN_MODE=='original':
        for y in np.arange(21,31,.42):
            x=np.linspace(-26,24,301)
            sources.append(('contour',np.c_[x,y+.24*np.sin(x*.22)],0))
    else:
        import contourpy
        from erosion import channels
        state={k:np.asarray(v) for k,v in B.D['terrain_state'].items()}
        cg=contourpy.contour_generator(x=state['x'],y=state['y'],z=state['height'])
        for level in np.arange(float(state['height'].min()),float(state['height'].max()),.19):
            sources.extend(('contour',p,0) for p in cg.lines(level) if len(p)>4)
        sources.extend(('channel',p,0) for p in channels(state))
    pens=[[],[],[],[]];audit=[];stats={};saved=[]
    for kind,xy,pen in sources:
        if B.TERRAIN_MODE!='original' and kind in ('channel','contour'):
            from scipy.ndimage import gaussian_filter1d
            # Cartographic smoothing changes only drawing paths, not the
            # physical height field or recorded receiver graph.
            xy=gaussian_filter1d(xy,.9,axis=0,mode='nearest')
        xy=densify(xy,.018);world,ok,host_hit=B.drape(xy)
        ok&=(abs(xy[:,0])<27)&(xy[:,1]>-9)&(xy[:,1]<32)
        if B.TERRAIN_MODE!='original' and kind in ('channel','contour'):
            ok&=(abs(xy[:,0])<21)&(xy[:,1]>-7.5)&(xy[:,1]<30)
        # Two trails bend to the gate, giving the foreground room to breathe.
        if kind=='field':
            lane=.5*np.sin(xy[:,1]*.2)
            ok&=(abs(xy[:,0]-lane)>1.0)|(xy[:,1]>-.5)
            for x0,y0,x1,y1 in B.D['footprints']:
                ok&=~((xy[:,0]>x0)&(xy[:,0]<x1)&(xy[:,1]>y0)&(xy[:,1]<y1))
            if B.TERRAIN_MODE!='original':
                # Cultivated marks retreat from steep banks, rather than being
                # drawn across the new ravines as another uniform wallpaper.
                ok &= B.TBVH[7][np.maximum(host_hit,0),2]>.965
                # Leave a white channel corridor at large actual accumulations.
                from scipy.ndimage import map_coordinates
                u=(xy[:,0]-state['x'][0])/(state['x'][-1]-state['x'][0])*(len(state['x'])-1)
                v=(xy[:,1]-state['y'][0])/(state['y'][-1]-state['y'][0])*(len(state['y'])-1)
                ok &= map_coordinates(state['area'],[v,u],order=1,mode='nearest')<65
        safe=np.nan_to_num(world);x,y,z=B.project(safe)
        framed=(x>14)&(x<B.W-14)&(y>14)&(y<B.H-14)&(z>B.NEAR)
        candidate=ok&framed;seen=np.zeros(len(world),bool)
        if candidate.any():seen[candidate]=B.visible(world[candidate],*B.BVH[:6])
        keep=candidate&seen
        width=(MM['field'] if B.TERRAIN_MODE=='original' else
               .16 if kind=='channel' else MM['field'] if kind=='field' else .095)
        pens[pen].extend((q,width*20) for q in B.split_paths(np.c_[x,y],keep))
        audit.append(world[keep])
        st=stats.setdefault(kind,dict(candidates=0,hidden_by_model=0,survives=0))
        st['candidates']+=int(candidate.sum());st['hidden_by_model']+=int((candidate&~seen).sum());st['survives']+=int(keep.sum())
    np.savez_compressed(OUT/f'surface-audit-{B.VIEW_NAME}.npz',world=np.vstack(audit))
    label='03 Driftless field and contour' if B.TERRAIN_MODE=='original' else '03 Driftless field and terrain traces'
    return [(label,pens[0],INK)],stats


def structure():
    n=np.asarray(B.D['normals']);centers=np.array([f['p'].mean(0) for f in B.FACES])
    front=np.einsum('ij,ij->i',n,B.EYE-centers)>0
    edges={};terrain=set(B.D['terrain_faces']);paths=[];detail=[]
    for k,f in enumerate(B.D['faces']):
        if k in terrain:continue
        # Leaf faces are two-sided drawing geometry; their silhouettes must
        # survive even when the outward normal happens to face away.
        leaf=B.FACES[k]['mat']==6
        for a,b in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted([a,b])),[]).append(k)
    for (a,b),owners in edges.items():
        leaf=any(B.FACES[k]['mat']==6 for k in owners)
        # Leaf polygons are two-sided drawing geometry; the crown's outline is
        # carried by the front-facing ones, so back-facing leaves are not inked.
        if not any(front[owners]):continue
        silhouette=len(owners)==1 or not all(front[owners])
        if silhouette or leaf or n[owners[0]]@n[owners[-1]]<.85:
            p=B.V[[a,b]];zc=max(.25,(p.mean(0)-B.EYE)@B.FWD)
            # Cap at 1.24 so 0.25 mm silhouettes stay below the 0.32 mm route.
            depth=np.clip(np.linalg.norm(B.TARGET-B.EYE)/zc,.80,1.24)
            name=B.FACES[owners[0]]['name']
            if leaf:width=MM['foliage']*20
            elif 'branch' in name:width=MM['branch']*20
            elif name.startswith(FURNITURE):width=MM['crease']*20*depth
            else:width=(MM['silhouette'] if silhouette else MM['crease'])*20*depth
            paths.extend((q,width) for q in B.stroke_project(p))
    # Black records an arrangement; red marks what happened. Every dependency
    # tray is drawn; only the edges classify_routes puts on the critical path
    # keep the red centerline. The rest become black lines at crease weight.
    arch=classify_routes(json.loads(json.dumps(B.D['architecture'])))
    red_edges={(e['source'],e['target']) for e in arch['edges'] if e['red']}
    red=[]
    for s in B.D['strokes']:
        projected=[(q,s['width']) for q in B.stroke_project(np.asarray(s['pts']))]
        if s['ink']!=2:detail.extend(projected);continue
        m=re.match(r'Dependency (\S+) to (\S+)$',s['name'])
        wait=re.match(r'Release wait (\S+)$',s['name'])
        wait_active=wait and any(n['id']==wait.group(1) and n.get('release_mark') for n in arch['nodes'])
        if (m and (m.group(1),m.group(2)) not in red_edges) or (wait and not wait_active):
            detail.extend((q,MM['crease']*20) for q,_ in projected)
        else:red.extend(projected)
    if arch.get('scene_profile')!='spillway':red.extend(release_marks(arch))
    return paths+detail,red,arch


def release_marks(arch):
    """A red mark on the lift of a node whose start was set by its release.

    The lift already exists in the model; the mark is an ink-only vertical on
    the upright nearest the camera, from the ground to the landing, so that the
    thing that set the finish is the thing drawn in red.
    """
    marks=[]
    for n in arch['nodes']:
        if not n.get('release_mark'):continue
        ups=[f['p'] for f in B.FACES if f['name'].startswith('Release lift upright')]
        landing=[f['p'] for f in B.FACES if f['name'].startswith('Release lift landing')]
        if not ups:continue
        cols={}
        for p in ups:
            key=(round(float(p[:,0].mean()),1),round(float(p[:,1].mean()),1))
            cols.setdefault(key,[]).append(p)
        def dist(key):return np.linalg.norm(np.array([key[0],key[1],0])-B.EYE*np.array([1,1,0]))
        key=min(cols,key=dist);pts=np.vstack(cols[key])
        z0=float(pts[:,2].min());z1=float(np.vstack(landing)[:,2].max()) if landing else float(pts[:,2].max())
        x,y=key;toward=(B.EYE[:2]-np.array([x,y]));toward/=np.linalg.norm(toward)
        x,y=x+toward[0]*.12,y+toward[1]*.12
        marks.extend((q,MM['vermilion']*20) for q in B.stroke_project(np.array([[x,y,z0],[x,y,z1]])))
    return marks


def engrave(field,edges):
    ch=B.CH;w=MM['hatch']*20;gap=MM['gap']*20
    depth=np.linalg.norm(B.TARGET-B.EYE);delta=gap*depth/B.FOCAL
    ch.FAMILIES=((.64,delta,w),(-.72,delta*1.08,w))
    ch.C_MAX=.82;ch.GAMMA=1.05;ch.C_SPLIT=.20;ch.MIN_GAP=gap
    st=ch.Strokes()
    # Continuous terrain hatching; field ink reserves much of its local tone.
    ch.hatch_on_surface(st,B.terrain,.48)
    for i,f in enumerate(B.FACES):
        if not f['hatch']:continue
        n=np.asarray(B.D['normals'][i])
        if n@(B.EYE-f['p'].mean(0))<=0:continue
        ch.hatch_on_face(st,f['p'],n,.82,i)
    st.finish();print('Hatch samples',len(st.world),flush=True)
    normals=np.empty_like(st.world);gain=np.ones(len(st.world));albedo=np.ones(len(st.world))
    for k in np.unique(st.attr['surf']):
        m=st.attr['surf']==k
        if k==0:
            normals[m]=B.terrain.normal(st.world[m,0],st.world[m,1]);gain[m]=GAIN['terrain']
            if B.TERRAIN_MODE!='original':
                gain[m]=(.24+.20*np.clip((1-normals[m,2])/.30,0,1) if B.D['architecture'].get('scene_profile')=='spillway'
                         else .42+.42*np.clip((1-normals[m,2])/.30,0,1))
        else:
            f=B.FACES[-1-int(k)];normals[m]=B.D['normals'][-1-int(k)]
            albedo[m]=.64 if f['mat']==2 else .77 if f['mat'] in (3,4) else 1.
            name=f['name']
            if any(name.endswith(t) or t in name for t in PLINTH):gain[m]=GAIN['plinth']
            elif name.startswith(FURNITURE):gain[m]=GAIN['furniture']
    x,y=st.xy.T;frame=(x>14)&(x<B.W-14)&(y>14)&(y<B.H-14)&(st.z>B.NEAR)
    seen=np.zeros(len(st.world),bool);seen[frame]=B.visible(st.world[frame],*B.BVH[:6])
    d=np.zeros(len(st.world));d[seen]=np.clip(1-B.light(st.world[seen],normals[seen],*B.BVH[:6])*albedo[seen],0,1)*gain[seen]
    used=Image.new('L',(B.W//5,B.H//5),0);draw=ImageDraw.Draw(used)
    for paths in [edges]+[p for _,p,_ in field]:
        for q,width in paths:draw.line([tuple(p/5) for p in q],fill=255,width=max(1,round(width/5)))
    used=gaussian_filter(np.asarray(used,float)/255,.7)*.32
    keep=ch.allocate_hatch(st,d,used,seen)
    np.savez_compressed(OUT/f'hatch-audit-{B.VIEW_NAME}.npz',world=st.world[keep][::3],shade=d[keep][::3])
    # All emitted hatches have exactly the width budgeted above.
    return [('01 crosshatching',[(q,w) for q in B.split_paths(st.xy,keep,st.sid)],INK),('02 architecture and volume foliage',edges,INK)]


def place(patches):
    rng=np.random.default_rng(int(B.D['architecture']['seed']));out=[]
    def add(p,x,y,h):
        z=float(B.height(x,y))+.015
        out.append(M.Instance(p,p.get('origin',[20,40]),[x,y,z],h/p.get('height',p.get('h',20)),MM['foliage']*20))
    # A foreground engraved oak remains a drawing-plane symbol. Volumetric
    # trees at the building interfaces are in Blender, cast shadows, and turn.
    for x,y,h in B.D.get('planar_trees',[(-12.5,-.6,7.0)]):add(patches['oak'],x,y,h)
    for _ in range(290):
        x,y=rng.uniform(-18,18),rng.uniform(-8,13)
        if abs(x)<2.3 or (y>0 and abs(x)<8):continue
        if rng.random()<.22:continue
        if any(x0-.3<x<x1+.3 and y0-.3<y<y1+.3 for x0,y0,x1,y1 in B.D['footprints']):continue
        add(patches['plants'][int(rng.integers(len(patches['plants'])))],x,y,rng.uniform(.35,.9))
    return out


if __name__=='__main__':
    start=time.time();patches=json.loads((OUT/'driftless-meadow-patches.json').read_text())
    field,stats=surface_paths(patches);print('Terrain',stats,flush=True)
    edges,red,arch=structure();print('Architecture paths',len(edges),'route paths',len(red),flush=True)
    groups=engrave(field,edges)+field
    instances=place(patches);buf=np.full((B.H*M.K,B.W*M.K),np.inf)
    for inst in instances:M.stamp(buf,inst)
    depth=M.model_depth(buf);pens,audit=M.plant_strokes(instances,buf,return_audit=True)
    # A raster zone mask is measurement metadata, never SVG content. Include
    # the actual owner-aware planar silhouettes in oak coverage measurements.
    treebuf=np.full_like(buf,np.inf)
    for inst in instances[:len(B.D.get('planar_trees',[None]))]:M.stamp(treebuf,inst)
    tree_zone=(np.isfinite(treebuf)&(treebuf<=depth+M.EPS_MODEL)).reshape(B.H,M.K,B.W,M.K).any(axis=(1,3))
    np.savez_compressed(OUT/f'tree-zones-{B.VIEW_NAME}.npz',oak=tree_zone)
    clipped=[(label,M.clip_screen_paths(paths,buf,depth),col) for label,paths,col in groups]
    # The source Driftless pens collapse to one black plotting pen. The
    # dependency centerline is the sole red ink and is drawn last.
    flora=[('04 Driftless foreground',sum(pens,[]),INK)]
    red=M.clip_screen_paths(red,buf,depth)
    final=clipped+flora+[('05 dependency routes',red,RED)]
    B.svg_write('Infernal_'+B.CASE+'_'+B.VIEW_NAME,final)
    inside=audit['survives'];np.savez_compressed(OUT/f'plants-audit-{B.VIEW_NAME}.npz',xy=audit['xy'][inside],owner_depth=audit['owner_depth'][inside],nearest_depth=M.lookup(buf,audit['xy'][inside]))
    widths=[w for _,p,_ in final[:-1] for q,w in p]
    manifest=dict(case=B.CASE,view=B.VIEW_NAME,blender=B.D['blender'],print_width_mm=PRINT_WIDTH_MM,
                  px_per_mm=PX_PER_MM,mm=MM,faces=len(B.FACES),paths=sum(len(p) for _,p,_ in final),
                  plants=len(instances),volume_leaf_faces=sum(m==6 for m in B.D['materials']),surface=stats,
                  red_heavier_than_black=bool(max(widths,default=0)<MM['vermilion']*20),
                  architecture=arch,red_edges=[[e['source'],e['target']] for e in arch['edges'] if e['red']],
                  release_marks=[n['id'] for n in arch['nodes'] if n.get('release_mark')],
                  gains={**GAIN,'eroded_terrain':'.24 + .20 × slope' if arch.get('scene_profile')=='spillway' else '.42 + .42 × slope'},elapsed_seconds=round(time.time()-start,2),
                  driftless_sha256=hashlib.sha256((B.ROOT/'vendor/driftless-engine.js').read_bytes()).hexdigest())
    manifest['terrain_mode']=B.TERRAIN_MODE
    (OUT/f'manifest-{B.VIEW_NAME}.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest),flush=True)
