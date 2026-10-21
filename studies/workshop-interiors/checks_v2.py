"""Independent 600 dpi binary print checks, measured on the delivered SVG."""
from pathlib import Path
from io import BytesIO
import ast,hashlib,json,math,re,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_erosion,distance_transform_edt
from scipy.spatial.distance import pdist
import cairosvg
import render_v2 as E

O=E.OUT;NS='{http://www.w3.org/2000/svg}';INK='{http://www.inkscape.org/namespaces/inkscape}'
root=ET.parse(O/(E.KEY+'.svg')).getroot();groups=root.findall(NS+'g');tests={};metrics={}
DPI=600;PPM=DPI/25.4;PW=round(E.PRINT['width_mm']*PPM);PH=round(E.PRINT['height_mm']*PPM)
def record(name,passed,**extra):tests[name]={'passed':bool(passed),**extra}
def raster(indices):
    copy=ET.fromstring(ET.tostring(root));gg=copy.findall(NS+'g')
    for i,g in enumerate(gg):
        if i not in indices:copy.remove(g)
    png=cairosvg.svg2png(bytestring=ET.tostring(copy),output_width=PW,output_height=PH,background_color='white')
    return np.asarray(Image.open(BytesIO(png)).convert('L'))<128

manifest=json.loads((O/'manifest.json').read_text())
scene_hash=hashlib.sha256((O/'scene.json').read_bytes()).hexdigest();cache=O/'owner-map-600dpi.npz'
if cache.exists():
    a=np.load(cache);owner=a['owner'] if str(a['scene_sha256'])==scene_hash else None
else:owner=None
if owner is None:
    owner=E.owner_map(PW,PH);np.savez_compressed(cache,owner=owner.astype(np.int16),scene_sha256=scene_hash)
allink=raster({0,1,2,3});hatch=raster({0});black=raster({0,1,2});red=raster({3})
Image.fromarray(~allink).convert('1').save(O/'print-600dpi.png')
Image.fromarray(~hatch).convert('1').save(O/'hatch-600dpi.png')
print('rasterized',PW,PH,flush=True)
valid=owner>=0;zone_names=['']+sorted(set(E.ZONES)-{''});region_names=['']+sorted(set(E.RESERVED)-{''})
zone_lut=np.array([zone_names.index(x) for x in E.ZONES],np.uint8);region_lut=np.array([region_names.index(x) for x in E.RESERVED],np.uint8)
zone=np.zeros(owner.shape,np.uint8);region=np.zeros(owner.shape,np.uint8)
zone[valid]=zone_lut[owner[valid]];region[valid]=region_lut[owner[valid]]
def zm(name):return zone==zone_names.index(name) if name in zone_names else np.zeros(owner.shape,bool)
def rm(name):return region==region_names.index(name) if name in region_names else np.zeros(owner.shape,bool)
yy,xx=np.indices(owner.shape,dtype=np.uint16);margin=E.MARGIN/E.PX_PER_MM*PPM
inside=(xx>margin)&(xx<PW-margin)&(yy>margin)&(yy<PH-margin)
zone[~inside]=0;region[~inside]=0

def coverage(name,mask):
    n=int(mask.sum());value=float(hatch[mask].mean()) if n else None
    # Each statistic is a ratio of real ink pixels to visible zone pixels,
    # accumulated in 4 mm cells. Partial cells remain explicit and area-weighted.
    step=round(4*PPM);cell=(yy//step)*(PW//step+1)+xx//step
    counts=np.bincount(cell[mask],minlength=int(cell.max())+1)
    inks=np.bincount(cell[mask],weights=hatch[mask],minlength=len(counts))
    sel=counts>=round(.5*PPM*PPM);ratios=inks[sel]/counts[sel]
    return {'mean_hatch_coverage':value,'all_ink_coverage':float(allink[mask].mean()) if n else None,'area_mm2':n/(PPM*PPM),'cell_mm':4,'cells':int(sel.sum()),'cell_p10':float(np.quantile(ratios,.10)) if len(ratios) else None,'cell_p90':float(np.quantile(ratios,.90)) if len(ratios) else None}

zones={}
for name in E.CFG['tone_targets']:
    if name!='reserved':zones[name]=coverage(name,zm(name))
if E.KEY=='maintained-workshop':
    rad=np.hypot((xx-PW*.5)/(PW*.55),(yy-PH*.44)/(PH*.7))
    zones['rear-wall-centre']=coverage('rear-wall-centre',zm('rear-wall')&(rad<.65))
halo=np.asarray(Image.open(O/'halo-mask.png').resize((PW,PH),Image.Resampling.NEAREST))>127
if E.KEY=='office-without-a-seal':zones['halo']=coverage('halo',halo&(~rm('recess')))
metrics['zones']=zones
hierarchy=E.CFG['hierarchy'];values=[zones.get(n,{}).get('mean_hatch_coverage') for n in hierarchy]
record('measured_hatch_hierarchy',all(v is not None for v in values) and all(a>b for a,b in zip(values,values[1:])) if all(v is not None for v in values) else False,order=hierarchy,coverage=values)

reserved_results={}
for name in sorted(set(E.RESERVED)-{''}):
    mask=rm(name);mask=distance_transform_edt(mask)>.22*PPM
    # The briefs allow rules, cage lines, filaments and one clerk hand within
    # named reserved regions. Exclude those authorised marks, not other ink.
    allowed=Image.new('L',(PW,PH),0);draw=ImageDraw.Draw(allowed)
    for s in E.D['strokes']:
        if s.get('reserved_content')!=name:continue
        sx,sy,_=E.project(np.array(s['pts']));scale=PW/E.W
        width=E.WEIGHTS[s['role']]*PPM+.15*PPM
        draw.line(list(zip(sx*scale,sy*scale)),fill=255,width=max(1,round(width)))
    authorised=np.asarray(allowed)>0;n=int(mask.sum())
    forbidden=float((allink&~authorised)[mask].mean()) if n else None
    value=float(hatch[mask].mean()) if n else None
    reserved_results[name]={'area_mm2':n/PPM**2,'hatch_coverage':value,'unallowed_ink_coverage':forbidden,'all_ink_coverage':float(allink[mask].mean()) if n else None}
    limit=.01 if name=='recess' else .02
    record('reserved_'+name,n>0 and value<limit and forbidden<limit,limit=limit,**reserved_results[name])
metrics['reserved_regions']=reserved_results

widths=[float(p.attrib['stroke-width'])/E.PX_PER_MM for g in groups[:3] for p in g.findall(NS+'path')]
red_widths=[float(p.attrib['stroke-width'])/E.PX_PER_MM for p in groups[3].findall(NS+'path')]
record('red_is_heaviest_line',bool(red_widths) and max(widths)<min(red_widths),maximum_black_mm=max(widths),minimum_red_mm=min(red_widths) if red_widths else None)
record('printed_size_and_weights',float(root.attrib['width'][:-2])==E.PRINT['width_mm'] and float(root.attrib['height'][:-2])==E.PRINT['height_mm'] and all(abs(float(p.attrib['stroke-width'])/E.PX_PER_MM-.10)<1e-6 for p in groups[0].findall(NS+'path')),width_mm=E.PRINT['width_mm'],height_mm=E.PRINT['height_mm'],dpi=DPI)
record('two_inks_four_path_layers',len(groups)==4 and {g.attrib['stroke'] for g in groups}==set(E.PRINT['inks'].values()) and all(x.tag in [NS+'svg',NS+'title',NS+'g',NS+'path'] for x in root.iter()))
points=[]
for p in root.iter(NS+'path'):
    q=np.array([float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',p.attrib['d'])]).reshape(-1,2);points.append(q)
p=np.vstack(points);record('finite_coordinates_and_page_margins',np.isfinite(p).all() and p[:,0].min()>=E.mm(1.95) and p[:,0].max()<=E.W-E.mm(1.95) and p[:,1].min()>=E.mm(1.95) and p[:,1].max()<=E.H-E.mm(1.95))

audit=json.loads((O/'stroke-audit.json').read_text());reds=[s for s in audit if s['role'].startswith('red')]
metrics['vermilion']={'source_routes':len(reds),'delivered_paths':len(groups[3]),'length_mm':sum(s['visible_length_mm'] for s in reds),'maximum_hidden_run_mm':max(s['maximum_hidden_run_mm'] for s in reds)}
if E.KEY=='maintained-workshop':
    record('one_red_route_with_short_occlusions',len(reds)==1 and reds[0]['visible_length_mm']>=60 and reds[0]['maximum_hidden_run_mm']<=3,**metrics['vermilion'])
    wheel=[s for s in audit if s['name']=='Wheel calibration tick'];ruler=[s for s in audit if s['name']=='Ruler tick']
    record('wheel_and_ruler_ticks_have_visible_printed_lengths',sum(s['visible_length_mm']>=.4 for s in wheel)>=60 and sum(s['visible_length_mm']>=.4 for s in ruler)>=20,wheel_ticks_visible=sum(s['visible_length_mm']>=.4 for s in wheel),wheel_ticks_total=len(wheel),ruler_ticks_visible=sum(s['visible_length_mm']>=.4 for s in ruler),minimum_visible_mark_mm=.4)
if E.KEY=='office-without-a-seal':
    record('two_visible_four_mm_red_terminals',len(reds)==2 and len(groups[3])==2 and min(s['visible_length_mm'] for s in reds)>=4 and all(s['hidden_samples']==0 for s in reds),**metrics['vermilion'])
    record('recess_halo_below_eight_percent',zones['halo']['mean_hatch_coverage'] is not None and zones['halo']['mean_hatch_coverage']<.08,hatch_coverage=zones['halo']['mean_hatch_coverage'],all_ink_coverage=zones['halo']['all_ink_coverage'])
if E.KEY=='empty-cabinet':
    p=np.array(E.D['parts']['crank']);x,y,_=E.project(p);span=max(np.ptp(x),np.ptp(y))/E.PX_PER_MM
    record('crank_spans_six_mm',span>=6,span_mm=span)
    crank_faces=np.array([n.startswith('Cabinet crank') for n in E.D['names']]);crank_mask=np.zeros(owner.shape,bool);crank_mask[valid]=crank_faces[owner[valid]];cy,cx=np.where(crank_mask)
    visible_span=max(np.ptp(cx),np.ptp(cy))/PPM if len(cx) else 0
    record('crank_is_visible_at_six_mm',visible_span>=6,visible_span_mm=float(visible_span))
    v=E.D['parts']['cabinet_clear_volume']
    # A through-view traverses both end caps of the clear volume. Its convex
    # silhouette alone would include rays that hit its roof or side panels.
    caps=[]
    for depth in [v[0][1],v[1][1]]:
        cap=np.array([[v[0][0],depth,v[0][2]],[v[1][0],depth,v[0][2]],[v[1][0],depth,v[1][2]],[v[0][0],depth,v[1][2]]]);fx,fy,_=E.project(cap)
        im=Image.new('L',(PW,PH),0);ImageDraw.Draw(im).polygon(list(zip(fx*PW/E.W,fy*PH/E.H)),fill=255);caps.append(np.asarray(im)>0)
    void=distance_transform_edt(caps[0]&caps[1])>.4*PPM
    void_coverage=float(allink[void].mean());window_through=int((void&rm('window')).sum())
    record('full_depth_inspection_corridor_is_clear_and_reveals_window',void_coverage<.08 and window_through>0,coverage=void_coverage,window_through_mm2=window_through/PPM**2)
    # Inspect the window-backed region, excluding the cabinet's physical rims.
    mask=rm('window');visible=mask.any();cov=float(allink[mask].mean()) if visible else 1
    record('window_panes_are_visible_and_clear',visible and cov<.08,coverage=cov,area_mm2=float(mask.sum()/PPM**2))
if E.KEY=='extraction-of-the-hand':
    strands=[s for s in audit if s['name'].startswith('Ledger strand ')]
    record('all_twenty_three_strands_unoccluded',len(strands)==23 and all(s['hidden_samples']==0 for s in strands),strands=len(strands),hidden_samples=sum(s['hidden_samples'] for s in strands))
    parts=E.D['parts']['ledger_strands'];blackparts=[s for s in parts if not s['red']]
    landing=np.array([s['landing'] for s in blackparts]);x,y,_=E.project(landing);spacing=float(pdist(np.column_stack([x,y])).min()/E.PX_PER_MM)
    record('twenty_two_distinct_ledger_landings',len(blackparts)==22 and len({s['rule_id'] for s in blackparts})==22 and spacing>=.35,minimum_spacing_mm=spacing)
    curves=[]
    for part in parts:
        source=next(s for s in E.D['strokes'] if s['name']==part['source_name'])
        sx,sy,_=E.project(np.array(source['pts'][:part.get('approach_samples',70)]));curves.append((source['name'],np.c_[sx,sy]))
    crossings=[]
    def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
    for i,(an,a) in enumerate(curves):
        for bn,b in curves[i+1:]:
            p=a[:-1,None];r=a[1:,None]-p;q=b[None,:-1];u=b[None,1:]-q;den=cross(r,u);safe=np.where(abs(den)>1e-9,den,1.)
            t=cross(q-p,u)/safe;v=cross(q-p,r)/safe
            if ((abs(den)>1e-9)&(t>1e-7)&(t<1-1e-7)&(v>1e-7)&(v<1-1e-7)).any():crossings.append([an,bn])
    record('strand_approaches_have_no_projected_crossings',not crossings,crossing_pairs=crossings)

    free=[s for s in parts if s['red']][0];x,y,_=E.project(np.array([free['end']]));point=np.array([x[0],y[0]])/E.PX_PER_MM
    pages=np.flatnonzero(E.RESERVED=='ledger-pages');v=np.unique(np.concatenate([E.F[k] for k in pages]));px,py,_=E.project(E.V[v]);vertices=np.c_[px,py]/E.PX_PER_MM
    # Distance to every projected edge, including all internal rule segments.
    segments=[]
    for k in pages:
        f=E.F[k]
        for a,b in zip(f,f[1:]+f[:1]):
            sx,sy,_=E.project(E.V[[a,b]]);segments.append(np.c_[sx,sy]/E.PX_PER_MM)
    for s in E.D['strokes']:
        if s.get('reserved_content')=='ledger-pages' and not s['name'].startswith('Ledger strand '):
            sx,sy,_=E.project(np.array(s['pts']));q=np.c_[sx,sy]/E.PX_PER_MM;segments.extend(np.stack([q[:-1],q[1:]],1))
    seg=np.asarray(segments);a=seg[:,0];d=seg[:,1]-a;t=np.clip(np.einsum('ij,ij->i',point-a,d)/np.maximum(1e-15,np.einsum('ij,ij->i',d,d)),0,1);clearance=float(np.linalg.norm(point-a-t[:,None]*d,axis=1).min())
    record('red_strand_stops_three_mm_from_page_and_rules',clearance>=3,clearance_mm=clearance)
    # Exclude the strands themselves; the halo test concerns competing hatch.
    bench=zm('bench-top');halo_value=float(hatch[halo&bench].mean()) if (halo&bench).any() else 0
    record('strand_halo_below_six_percent',halo_value<.06,hatch_coverage=halo_value)

extract=json.loads((E.ROOT/'vendor/extraction.json').read_text());source=(E.ROOT/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest() for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('nine_upstream_bodies_unchanged',all(hashes[x['name']]==x['sha256'] for x in extract['functions']),bodies=len(extract['functions']))
native=O/'blender-checks.json'
record('independent_native_blender_checks',native.exists() and json.loads(native.read_text())['all_passed'])
baseline=json.loads((E.ROOT/'baseline-v1.json').read_text())
record('vendored_raycore_and_all_extracted_files_unchanged',all(hashlib.sha256((E.ROOT/p).read_bytes()).hexdigest()==digest for p,digest in baseline['unchanged_vendor_files'].items()))
result={'plate':E.KEY,'revision':2,'all_passed':all(t['passed'] for t in tests.values()),'raster':{'dpi':DPI,'width_px':PW,'height_px':PH,'binary_threshold':128},'checks':tests,'metrics':metrics}
(O/'checks.json').write_text(json.dumps(result,indent=2));print(json.dumps({'plate':E.KEY,'all_passed':result['all_passed'],'failed':{k:v for k,v in tests.items() if not v['passed']},'zones':{k:round(v['mean_hatch_coverage'],4) if v['mean_hatch_coverage'] is not None else None for k,v in zones.items()}},indent=2),flush=True)
if not result['all_passed']:raise SystemExit(1)
