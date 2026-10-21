"""Prairie savanna: evaluated Blender bluffs, Driftless oaks, four process inks."""
import json,time,hashlib
import numpy as np
import contourpy
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter
import build as B
import occlusion as M
import cmyk

O=B.OUT
def dense(p,step=.012):
    p=np.asarray(p,float);l=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    if l[-1]<1e-10:return p[:1]
    t=np.linspace(0,l[-1],max(2,int(np.ceil(l[-1]/step))+1))
    return np.column_stack([np.interp(t,l,p[:,i]) for i in range(p.shape[1])])

def ground():
    rng=np.random.default_rng(4201);specs=[]
    for k in range(4200):
        x,y=rng.uniform(-29,29),rng.uniform(-10,49)
        if rng.random()>.48+.30*np.sin(x*.34+y*.11)**2:continue
        length=rng.uniform(.18,.95)*(1+max(y,0)*.009)
        t=np.linspace(0,1,6)
        xy=np.column_stack([x+t*length,y+.035*np.sin(t*np.pi)+t*.055*np.sin(x*.1)])
        specs.append(('prairie',xy))
    gx=np.asarray(B.D['source_grid']['x']);gy=np.asarray(B.D['source_grid']['y'])
    zz=B.V[:len(gx)*len(gy),2].reshape(len(gy),len(gx))
    con=contourpy.contour_generator(x=gx,y=gy,z=zz)
    for level in np.arange(1.0,7.8,.23):
        for xy in con.lines(level):
            if len(xy)>3:specs.append(('strata',xy))
    paths={'prairie':[],'strata':[]};audit=[];stats={}
    for kind,xy in specs:
        xy=dense(xy);p,ok,hit=B.drape(xy)
        nz=B.TBVH[7][np.maximum(hit,0),2]
        ok &= (nz<.88) if kind=='strata' else (nz>.88)
        x,y,z=B.project(np.nan_to_num(p))
        candidate=ok&(x>14)&(x<B.W-14)&(y>14)&(y<B.H-14)&(z>B.NEAR)
        seen=np.zeros(len(p),bool)
        if candidate.any():seen[candidate]=B.visible(p[candidate],*B.BVH[:6])
        keep=candidate&seen
        paths[kind].extend((q,.70 if kind=='strata' else .72) for q in B.split_paths(np.column_stack([x,y]),keep))
        audit.append(p[keep])
        a=stats.setdefault(kind,{'candidates':0,'hidden':0,'visible':0})
        a['candidates']+=int(candidate.sum());a['hidden']+=int((candidate&~seen).sum());a['visible']+=int(keep.sum())
    np.savez_compressed(O/f'surface-audit-{B.VIEW_NAME}.npz',world=np.vstack(audit))
    return [('prairie wind grain',paths['prairie'],(.02,.12,.83,0)),
            ('limestone strata',paths['strata'],(.73,.22,.15,.10))],stats

def silhouette():
    n=np.asarray(B.D['normals']);centers=np.array([f['p'].mean(0) for f in B.FACES])
    front=np.einsum('ij,ij->i',n,B.EYE-centers)>0
    edges={}
    for k,f in enumerate(B.D['faces']):
        for a,b in zip(f,f[1:]+f[:1]):edges.setdefault(tuple(sorted([a,b])),[]).append(k)
    paths=[]
    for (a,b),owners in edges.items():
        if len(owners)==2 and front[owners[0]]!=front[owners[1]]:
            paths.extend((q,.90) for q in B.stroke_project(B.V[[a,b]]))
    return paths

def hatch(field,edges):
    CH=B.CH;CH.FAMILIES=((.68,.067,.82),(-.72,.085,.70))
    CH.C_MAX=.52;CH.C_SPLIT=.17;CH.MIN_GAP=2.0
    st=CH.Strokes();CH.hatch_on_surface(st,B.terrain,.58);st.finish()
    print('Hatch candidates',len(st.world),flush=True)
    normals=B.terrain.normal(st.world[:,0],st.world[:,1]);rock=normals[:,2]<.88
    x,y=st.xy.T;framed=(x>14)&(x<B.W-14)&(y>14)&(y<B.H-14)&(st.z>B.NEAR)
    seen=np.zeros(len(x),bool);seen[framed]=B.visible(st.world[framed],*B.BVH[:6])
    shade=np.zeros(len(x));shade[seen]=1-B.light(st.world[seen],normals[seen],*B.BVH[:6])
    shade[seen&~rock]=np.minimum(shade[seen&~rock]+.10,.72)
    used=Image.new('L',(B.W//5,B.H//5));draw=ImageDraw.Draw(used)
    for paths in [edges]+[p for _,p,_ in field]:
        for q,w in paths:draw.line([tuple(v/5) for v in q],fill=170,width=1)
    used=gaussian_filter(np.asarray(used,float)/255,.65)*.20
    keep=CH.allocate_hatch(st,shade,used,seen)
    np.savez_compressed(O/f'hatch-audit-{B.VIEW_NAME}.npz',world=st.world[keep][::4])
    families=[]
    colors={('stone',0):(.76,.26,.10,.12),('stone',1):(.35,.42,.20,.28),
            ('grass',0):(.04,.14,.86,.02),('grass',1):(.32,.16,.66,.13)}
    for r,label in [(True,'stone'),(False,'grass')]:
        for f in [0,1]:
            selected=keep&(rock==r)&(st.attr['fam']==f)
            p=[(q,.82 if f==0 else .70) for q in B.split_paths(st.xy,selected,st.sid)]
            families.append((label+' hatch '+str(f),p,colors[(label,f)]))
    return families+[('bluff crests',edges,(.30,.18,.16,.63))]

def place(patch):
    trees=[];plants=[];rng=np.random.default_rng(2741)
    def add(out,p,x,y,h,w):
        z=float(B.height(x,y))+.015
        out.append(M.Instance(p,p.get('origin',[20,40]),[x,y,z],h/p.get('height',p.get('h',20)),w))
    for k,(x,y,h) in enumerate([(-10.7,2.7,6.6),(16,3.5,5.5),(-3,13,4.5),(-20,19,3.5),
                              (10,23,3.1),(17,25,2.3),(-16,31,3.3),(-2,35,2.3),(4,36,2.0)]):
        add(trees,patch['oaks'][k%6],x,y,h,.94 if y<8 else .72)
    for _ in range(1700):
        x,y=rng.uniform(-25,25),rng.uniform(-9,38)
        p,ok,hit=B.drape([[x,y]],0)
        if not ok[0] or B.TBVH[7][hit[0],2]<.91:continue
        chance=.88 if y<6 else .65 if y<17 else .35
        chance*=.55+.45*np.sin(x*.30+y*.23)**2
        if rng.random()>chance:continue
        i=int(rng.integers(92));h=rng.uniform(.42,1.05)*max(.35,1-y*.017)
        add(plants,patch['plants'][i],x,y,h,.76 if y<6 else .62)
    return trees,plants

if __name__=='__main__':
    start=time.time();patch=json.loads((O/'driftless-meadow-patches.json').read_text())
    field,stats=ground();edges=silhouette();groups=hatch(field,edges)+field
    trees,plants=place(patch);instances=trees+plants
    print('Placed',len(trees),'oaks and',len(plants),'prairie symbols',flush=True)
    buf=np.full((B.H*M.K,B.W*M.K),np.inf)
    for inst in instances:M.stamp(buf,inst)
    depth=M.model_depth(buf)
    treepens,ta=M.plant_strokes(trees,buf,return_audit=True)
    grasspens,ga=M.plant_strokes(plants,buf,return_audit=True)
    groups=[(label,M.clip_screen_paths(paths,buf,depth),values) for label,paths,values in groups]
    for k,values in enumerate([(.58,.35,.66,.65),(.75,.12,.90,.14),(.20,.30,.70,.1),(.40,.05,.72,0)]):
        groups.append(('oak pen '+str(k),treepens[k],values))
    for k,values in enumerate([(.12,.23,.78,.22),(.10,.08,.92,.02),(0,.82,.32,.04),(.04,.10,.65,0)]):
        groups.append(('prairie pen '+str(k),grasspens[k],values))
    audits=[]
    for a in [ta,ga]:
        keep=a['survives'];audits.append((a['xy'][keep],a['owner_depth'][keep],M.lookup(buf,a['xy'][keep])))
    xy=np.vstack([a[0] for a in audits]);owner=np.concatenate([a[1] for a in audits]);nearest=np.concatenate([a[2] for a in audits])
    np.savez_compressed(O/f'plants-audit-{B.VIEW_NAME}.npz',xy=xy,owner_depth=owner,nearest_depth=nearest)
    name='Prairie_CMYK' if B.VIEW_NAME=='main' else 'Prairie_CMYK_Low'
    color=cmyk.write(O,name,groups,B.W,B.H)
    if B.VIEW_NAME=='main':cmyk.sheet(O,name)
    info={'title':'Prairie bluffs and oaks','view':B.VIEW_NAME,'camera':B.CAM,'blender':B.D['blender'],
          'faces':len(B.FACES),'surface':stats,'oaks':len(trees),'grass_symbols':len(plants),
          'plant_samples':len(owner),'plant_owner_depth_violations':int((nearest<owner-M.EPS_PLANT).sum()),
          'cmyk':color,'seconds':round(time.time()-start,1)}
    (O/f'manifest-{B.VIEW_NAME}.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2),flush=True)
