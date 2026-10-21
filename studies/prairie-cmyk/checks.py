"""Native Blender ray audit, process-ink round trip, and inherited source checks."""
from pathlib import Path
import ast,hashlib,json,os,subprocess
import numpy as np
from PIL import Image
import build as B
import occlusion as M
R=Path(__file__).resolve().parent;O=R/'output';tests={}
def record(k,ok,**kw):tests[k]={'passed':bool(ok),**kw}
native=json.loads((O/'blender-checks.json').read_text())
record('camera_matches_native_blender',native['native_camera_max_error_px']<.002,max_error_px=native['native_camera_max_error_px'])
record('scene_is_prairie_terrain',len(B.FACES)>10000 and all(n=='Host terrain' for n in B.D['names']))
record('limestone_faces_exist',int((np.asarray(B.D['materials'])==1).sum())>100,stone_faces=int((np.asarray(B.D['materials'])==1).sum()))
for kind in ['surface','hatch']:
    p=np.load(O/f'{kind}-audit-{B.VIEW_NAME}.npz')['world'];seen=B.visible(p,*B.BVH[:6])
    record(kind+'_samples_visible',seen.all(),samples=len(p),violations=int((~seen).sum()))
p=np.load(O/f'plants-audit-{B.VIEW_NAME}.npz');bad=p['nearest_depth']<p['owner_depth']-M.EPS_PLANT
record('plant_owner_depth',not bad.any(),samples=len(bad),violations=int(bad.sum()))
manifest=json.loads((O/f'manifest-{B.VIEW_NAME}.json').read_text())
record('oak_and_grass_population',manifest['oaks']==9 and manifest['grass_symbols']>300)
record('real_hidden_strata_exercised',manifest['surface']['strata']['hidden']>100,hidden=manifest['surface']['strata']['hidden'])
name='Prairie_CMYK' if B.VIEW_NAME=='main' else 'Prairie_CMYK_Low'
im=Image.open(O/f'{name}.tif');im.load()
record('four_channel_cmyk_tiff',im.mode=='CMYK' and im.size==(B.W,B.H),mode=im.mode,size=list(im.size))
arr=np.asarray(im)
for k,letter in enumerate('CMYK'):
    plate=Image.open(O/f'{name}_{letter}.png').convert('L')
    error=np.max(abs(arr[...,k].astype(int)-(255-np.asarray(plate)).astype(int)))
    record(letter+'_separation_exact_in_tiff',error==0,max_error=int(error))
    text=(O/f'{name}_{letter}.svg').read_text()
    record(letter+'_vector_has_no_raster_or_mask','<path' in text and not any(s in text for s in ['<image','<mask','<clipPath']))
record('four_svg_ink_layers',(O/f'{name}.svg').read_text().count('inkscape:groupmode="layer"')==4)
ex=json.loads((R/'vendor/extraction.json').read_text());src=(R/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(src,n).encode()).hexdigest() for n in ast.parse(src).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('unchanged_claude_hatch_bodies',all(hashes[f['name']]==f['sha256'] for f in ex['functions']))
record('unchanged_driftless_engine',hashlib.sha256((R/'vendor/driftless-engine.js').read_bytes()).hexdigest()=='8ba687057284e68faf66521ec6eb543d27495fe8290095324f15201578a40020')
independent=json.loads((O/'blender-visibility.json').read_text())
record('native_blender_visibility',independent['violations']==0 and independent['buried_point_blocked'],**independent)
out={'view':B.VIEW_NAME,'all_passed':all(t['passed'] for t in tests.values()),'checks':tests}
(O/f'checks-{B.VIEW_NAME}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if not out['all_passed']:raise SystemExit(1)
