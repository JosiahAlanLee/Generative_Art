"""Build individual objects, a wear comparison and a composed farmyard."""
from pathlib import Path
import sys, argparse, json
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from lib.farm_objects import KINDS,make_object,write_obj
from lib.farm_objects.objects import G
from lib.farm_objects.render import render_svg
import numpy as np


def yard(seed=22,decay=.72):
    b=G.SceneBuilder(dict(seed=seed),lambda x,y:np.zeros(np.broadcast(x,y).shape))
    specs=[('barn',seed,(-2,3,0),-.12,1.),('tractor',seed+1,(3.6,-2,0),.26,1.),
           ('disk_harrow',seed+2,(5.3,1.1,0),-.2,1.),('hay_rake',seed+3,(-3.8,-3.5,0),-.6,1.),
           ('wagon',seed+4,(4.4,5.5,0),.5,1.)]
    for kind,s,pos,rot,scale in specs:make_object(kind,s,decay).add_to(b,pos,rot,scale)
    rng=np.random.default_rng(seed+90)
    # Detached dry grass/tussocks; deliberately sparse so the mechanisms read.
    for _ in range(140):
        x,y=rng.uniform([-7,-5],[7,9])
        if -5.2<x<1.0 and -2<y<8:continue
        for j in range(int(rng.integers(3,7))):
            h=rng.uniform(.12,.53);dx,dy=rng.normal(0,.10,2)
            b.ink('dry grass',[(x,y,.015),(x+dx*.4,y+dy*.4,h*.6),(x+dx,y+dy,h)],.10)
    for _ in range(95):
        x,y=rng.uniform([-7,-5],[7,9]);length=rng.uniform(.12,.6)
        if -5.2<x<1.0 and -2<y<8:continue
        b.ink('ground scratch',[(x,y,.004),(x+length,y+.04,.004)],.09)
    return dict(b.evaluate(),strokes=b.strokes,colors=b.colors,metadata=dict(kind='farmyard',seed=seed,decay=decay))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path(__file__).parent/'output')
    ap.add_argument('--seed',type=int,default=22);ap.add_argument('--decay',type=float,default=.72)
    ap.add_argument('--only',choices=(*KINDS,'farmyard','comparison'));ap.add_argument('--no-png',action='store_true')
    args=ap.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True);report={}
    cases=[(k,args.seed+i,args.decay) for i,k in enumerate(KINDS) if args.only in (None,k)]
    if args.only in (None,'comparison'):cases += [('barn',args.seed,d) for d in (0.,.38,.9)]
    for kind,seed,d in cases:
        asset=make_object(kind,seed,d);name=f'{kind}-{seed}-d{int(round(d*100)):02d}'
        rec=asset.record();(out/f'{name}.json').write_text(json.dumps(rec,separators=(',',':')))
        write_obj(asset,out/f'{name}.obj');report[name]=render_svg(rec,out/f'{name}.svg')
        print(name,report[name]['layers'],flush=True)
    if args.only in (None,'farmyard'):
        rec=yard(args.seed,args.decay);name='farmyard'
        (out/f'{name}.json').write_text(json.dumps(rec,separators=(',',':')))
        report[name]=render_svg(rec,out/f'{name}.svg',280,210,view=(1,-1.55,1.05),margin_mm=12)
        print(name,report[name]['layers'],flush=True)
    if not args.no_png:
        import cairosvg
        for name in report:
            (out/f'{name}.png').write_bytes(cairosvg.svg2png(url=str(out/f'{name}.svg'),output_width=1800,background_color='#f7f2e8'))
    (out/'metrics.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
