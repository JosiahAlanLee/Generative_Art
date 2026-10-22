"""Rebuild specimen sheets and a seeded prairie-edge composition.

Run from any directory: python studies/wisconsin-flora/build.py
"""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lib.flora import SPECIES, Plant, generate
from lib.flora.render import Drawing, render

OUT = Path(__file__).resolve().parent/'output'
FONT = ROOT/'studies/infernal-landscape/vendor/fonts/IBMPlexMono-Regular.ttf'


def sheet(drawings, names, file, *, cols=3, cell=(100, 143), title='DRIFTLESS / PLANT STUDIES'):
    rows = (len(drawings)+cols-1)//cols
    combined = Drawing(cell[0]*cols, cell[1]*rows+22)
    k = 6
    im = Image.new('RGB', (round(combined.width*k), round(combined.height*k)), '#f6f2e8')
    pen = ImageDraw.Draw(im)
    titlefont = ImageFont.truetype(str(FONT), 27)
    bodyfont = ImageFont.truetype(str(FONT), 17)
    smallfont = ImageFont.truetype(str(FONT), 14)
    pen.text((9*k, 6*k), title, font=titlefont, fill='#202b24')
    for i, (drawing, name) in enumerate(zip(drawings, names)):
        x, y = (i%cols)*cell[0], (i//cols)*cell[1]+20
        dx = (cell[0]-drawing.width)/2; dy = 0
        for role, p in drawing.paths:
            pp = p+[x+dx, y+dy]; combined.paths.append((role, pp))
            pen.line([tuple(q*k) for q in pp], fill='#202b24', width=max(1, round(.16*k)))
        lines = name.split('\n')
        for j, line in enumerate(lines):
            pen.text(((x+7)*k, (y+cell[1]-15+j*4)*k), line,
                     font=bodyfont if j == 0 else smallfont, fill='#202b24')
    combined.metadata = dict(title=title, specimens=[d.metadata for d in drawings],
                             labels='PNG only; SVG contains art paths only')
    (OUT/(file+'.svg')).write_text(combined.svg())
    im.save(OUT/(file+'.png'))
    return combined.stats()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='six main specimens only')
    parser.add_argument('--models', action='store_true', help='also write large JSON/OBJ models')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    drawings=[]; names=[]; manifest=[]
    for i, (key, info) in enumerate(SPECIES.items()):
        p = generate(key, 22+i*11)
        d = render(p, 96, 122, detail=2, pixels_per_mm=7)
        (OUT/(key+'.svg')).write_text(d.svg())
        d.png(OUT/(key+'.png'), 960)
        if args.models:
            p.save(OUT/(key+'.model.json')); p.obj(OUT/(key+'.obj'))
        drawings.append(d)
        names.append(info['common']+'\n'+info['latin']+' / '+p.metadata['stage'])
        manifest.append(dict(species=key, seed=p.metadata['seed'], stage=p.metadata['stage'],
                             **d.stats(), surfaces=len(p.surfaces), organs=len(p.organs)))
        print(key, d.stats(), flush=True)
    sheet(drawings, names, 'specimens')
    if not args.quick:
        variants=[]; labels=[]
        for key, info in SPECIES.items():
            for seed in (7, 31, 83):
                p = generate(key, seed, wind=(seed%3-1)*.35)
                variants.append(render(p, 84, 86, detail=0, pixels_per_mm=4))
                labels.append(info['common']+'\nseed '+str(seed))
            print('variants', key, flush=True)
        sheet(variants, labels, 'variation', cols=3, cell=(92, 105), title='ONE GRAMMAR / THREE SEEDS')
        seasonal=[]; labels=[]
        for key in ('prairie_smoke', 'wild_bergamot', 'bur_oak'):
            stages=('flowering', 'seed') if key != 'bur_oak' else ('leafy', 'bare')
            for stage in stages:
                p=generate(key, 22, stage=stage)
                seasonal.append(render(p, 96, 122, detail=1, pixels_per_mm=5))
                labels.append(SPECIES[key]['common']+' / '+stage+'\nsame seed 22; discrete organ states')
        sheet(seasonal, labels, 'stages', cols=2, title='LEAVES / FLOWERS / FRUIT')
    (OUT/'manifest.json').write_text(json.dumps(dict(generator='0.1.0', specimens=manifest,
        note='Illustrative grammars. No physical plot test. Each specimen fitted independently.'), indent=2)+'\n')


if __name__ == '__main__':
    main()
