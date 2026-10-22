from pathlib import Path
import argparse
from . import SPECIES, generate
from .render import render


def main():
    ap=argparse.ArgumentParser(description='Seeded southwest Wisconsin plant studies')
    ap.add_argument('species', choices=SPECIES)
    ap.add_argument('--seed', type=int, default=22)
    ap.add_argument('--stage')
    ap.add_argument('--wind', type=float, default=0)
    ap.add_argument('--vigor', type=float, default=1)
    ap.add_argument('--azimuth', type=float, default=18)
    ap.add_argument('--elevation', type=float, default=10)
    ap.add_argument('--detail', type=int, choices=(0,1,2), default=1)
    ap.add_argument('--width', type=float, default=100)
    ap.add_argument('--height', type=float, default=140)
    ap.add_argument('--out', type=Path, default=Path('examples/out/flora'))
    ap.add_argument('--model', action='store_true', help='also write 3D JSON and OBJ')
    a=ap.parse_args()
    try:
        plant=generate(a.species, a.seed, stage=a.stage, wind=a.wind, vigor=a.vigor)
        d=render(plant, a.width, a.height, azimuth=a.azimuth, elevation=a.elevation, detail=a.detail)
    except ValueError as e:
        ap.error(str(e))
    a.out.mkdir(parents=True, exist_ok=True)
    stem=f'{a.species}-{a.seed}-{plant.metadata["stage"]}'
    (a.out/(stem+'.svg')).write_text(d.svg()); d.png(a.out/(stem+'.png'))
    if a.model:
        plant.save(a.out/(stem+'.model.json')); plant.obj(a.out/(stem+'.obj'))
    print(a.out/(stem+'.svg')); print(d.stats())


if __name__ == '__main__':
    main()
