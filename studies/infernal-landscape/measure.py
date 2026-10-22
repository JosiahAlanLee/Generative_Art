"""Measure what a reader sees: ink coverage by zone, the tone hierarchy and
how much of the red is actually on the page.

The geometry checks say the drawing was delivered; these say whether it can be
read. Zones come from the scene record itself: every face is projected through
the plate's camera in painter's order, so each pixel knows which named object
it shows. Ink is the rasterised SVG at the master resolution, measured in 4 mm
cells at the declared print size. Red is compared route by route against its
projected length, so a dependency hidden behind a building is reported as
hidden, not as delivered.
"""
from io import BytesIO
import json,re
import numpy as np
from PIL import Image,ImageDraw
import cairosvg

CELL_MM=4
# Pixel values of the zone image; the first six are the original estate zones,
# the window plate adds its masonry reveal and the stream it looks out on.
ZONES=('sky','terrain','building','oak','furniture','other','aperture','water')


def _camera(scene,view):
    cam=scene['cameras'][view];eye=np.asarray(cam['eye'],float);target=np.asarray(cam['target'],float)
    unit=lambda v:np.asarray(v,float)/np.linalg.norm(v)
    fwd=unit(target-eye);right=unit(np.cross(fwd,[0,0,1]));up=np.cross(right,fwd)
    focal=cam['focal_px'];cx,cy=cam['principal_point']
    def project(P):
        q=np.asarray(P)-eye;z=q@fwd;safe=np.maximum(z,.25)
        return cx+focal*(q@right)/safe,cy-focal*(q@up)/safe,z
    return project


def zone_of(name,terrain,index,nodes):
    if index in terrain:return 'terrain'
    low=name.lower()
    if any(low.startswith(n+' ') or low.startswith(n+'|') for n in nodes):return 'building'
    if low.startswith(('release lift','unavailable portcullis')):return 'building'
    if 'oak' in low:return 'oak'
    if low.startswith(('meadow fence','service support','service tray','entry pier','open approach arch','bridge ')):return 'furniture'
    if low.startswith('window '):return 'aperture'
    if low.startswith('stream water'):return 'water'
    return 'other'


def zone_image(scene,view,W,H):
    """Painter's-order rasterisation of face zones; 0 is sky (no face)."""
    V=np.asarray(scene['vertices']);project=_camera(scene,view)
    terrain=set(scene['terrain_faces']);nodes=[n['id'] for n in scene['architecture']['nodes']]
    items=[]
    for i,f in enumerate(scene['faces']):
        x,y,z=project(V[f])
        if (z<=.25).any():continue
        items.append((float(z.max()),ZONES.index(zone_of(scene['names'][i],terrain,i,nodes)),list(zip(x,y))))
    items.sort(key=lambda t:-t[0])
    im=Image.new('L',(W,H),0);d=ImageDraw.Draw(im)
    for _,zi,poly in items:d.polygon(poly,fill=zi)
    return np.asarray(im).copy()


def ink_image(svg_text,W,paper='#ede6d4'):
    png=cairosvg.svg2png(bytestring=svg_text.encode(),output_width=W,background_color=paper)
    g=np.asarray(Image.open(BytesIO(png)).convert('L')).astype(float)
    white=np.percentile(g,99.5)
    return np.clip((white-g)/white,0,1)


def layer_paths(svg_text,label_fragment):
    for layer in re.split(r'(?=<g inkscape:groupmode="layer")',svg_text)[1:]:
        if label_fragment in re.search(r'inkscape:label="([^"]+)"',layer).group(1):
            return [np.array([tuple(map(float,p.split(','))) for p in re.findall(r'[-\d.]+,[-\d.]+',d)])
                    for d in re.findall(r' d="([^"]+)"',layer)]
    return []


def red_visibility(scene,view,svg_text,px_per_mm,red_edges):
    """Per red route: projected length, visible fraction, longest hidden run (mm)."""
    project=_camera(scene,view);pieces=layer_paths(svg_text,'dependency')
    out={}
    for s in scene['strokes']:
        m=re.match(r'Dependency (\S+) to (\S+)$',s['name'])
        wait=re.match(r'Release wait (\S+)$',s['name'])
        wait_active=wait and any(n['id']==wait.group(1) and n.get('release_mark') for n in scene['architecture']['nodes'])
        if not ((m and [m.group(1),m.group(2)] in red_edges) or wait_active):continue
        label=f'{m.group(1)} to {m.group(2)}' if m else 'release wait '+wait.group(1)
        x,y,_=project(np.asarray(s['pts']));xy=np.column_stack([x,y]);dense=[]
        for a,b in zip(xy,xy[1:]):
            n=max(2,int(np.linalg.norm(b-a)/2));dense.extend(np.linspace(a,b,n)[:-1])
        dense=np.asarray(dense);seen=np.zeros(len(dense),bool)
        for pc in pieces:
            for a,b in zip(pc,pc[1:]):
                d=b-a;L2=max(float(d@d),1e-9);t=np.clip(((dense-a)@d)/L2,0,1)
                seen|=np.linalg.norm(dense-(a+t[:,None]*d),axis=1)<3
        run=longest=0
        for v in seen:
            run=0 if v else run+1;longest=max(longest,run)
        out[label]=dict(projected_mm=round(len(dense)*2/px_per_mm,1),
            visible_fraction=round(float(seen.mean()),3),longest_hidden_mm=round(longest*2/px_per_mm,1))
    return out


def measure(scene,view,svg_text,W,H,px_per_mm,red_edges,tree_zone=None):
    Z=zone_image(scene,view,W,H);ink=ink_image(svg_text,W)
    if tree_zone is not None:Z[tree_zone]=ZONES.index('oak')
    c=int(round(CELL_MM*px_per_mm));Hc,Wc=H//c,W//c
    cells=ink[:Hc*c,:Wc*c].reshape(Hc,c,Wc,c).mean(axis=(1,3))
    zones={}
    for zi,name in enumerate(ZONES):
        px=Z==zi
        if not px.any():continue
        frac=(Z[:Hc*c,:Wc*c]==zi).reshape(Hc,c,Wc,c).mean(axis=(1,3));zc=cells[frac>=.7]
        zones[name]=dict(area_fraction=round(float(px.mean()),4),mean_ink=round(float(ink[px].mean()),3),
                         cells=int(len(zc)),cell_median=round(float(np.median(zc)),3) if len(zc) else None,
                         cell_p90=round(float(np.percentile(zc,90)),3) if len(zc) else None,
                         cell_max=round(float(zc.max()),3) if len(zc) else None)
    return dict(cell_mm=CELL_MM,plate_mean_ink=round(float(ink.mean()),4),cell_max=round(float(cells.max()),3),
                cell_p90=round(float(np.percentile(cells,90)),3),zones=zones,
                red=red_visibility(scene,view,svg_text,px_per_mm,red_edges))


if __name__=='__main__':
    import sys
    from pathlib import Path
    out=Path(sys.argv[1]);view=sys.argv[2] if len(sys.argv)>2 else 'main'
    scene=json.loads((out/'scene.json').read_text());manifest=json.loads((out/f'manifest-{view}.json').read_text())
    case=manifest['case']
    svg=(out/f'Infernal_{case}_{view}.svg').read_text();W,H=map(int,re.search(r'viewBox="0 0 (\d+) (\d+)"',svg).groups())
    tree_file=out/f'tree-zones-{view}.npz'
    tree_zone=np.load(tree_file)['oak'] if tree_file.exists() else None
    print(json.dumps(measure(scene,view,svg,W,H,manifest['px_per_mm'],manifest.get('red_edges',[]),tree_zone),indent=2))
