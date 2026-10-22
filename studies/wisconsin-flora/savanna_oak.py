"""Specimen sheet for the open-grown bur oak (lib/flora/oak.py, crown.py).

Three seeds, and the first again turned 90 degrees, each drawn on its own by
lib/flora/oak_render.py and fitted to its cell: foliage masses as scalloped
rows and outlines, limbs as smooth silhouettes, bark as furrows kept by light
and spacing.

Run from any directory: python studies/wisconsin-flora/savanna_oak.py
"""
from pathlib import Path
import json
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lib.flora.oak import savanna_oak          # noqa: E402
from lib.flora.oak_render import render_oak     # noqa: E402
from lib.flora.render import Drawing            # noqa: E402

OUT = Path(__file__).resolve().parent / 'output'
FONT = ROOT / 'studies/infernal-landscape/vendor/fonts/IBMPlexMono-Regular.ttf'
SPECIMENS = [(371, 20.), (521, 20.), (900, 20.), (371, 110.)]     # seed, azimuth
CELL = (110, 96)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cols = 2; rows = (len(SPECIMENS) + cols - 1) // cols
    sheet = Drawing(CELL[0] * cols, CELL[1] * rows + 16)
    k = 8
    im = Image.new('RGB', (round(sheet.width * k), round(sheet.height * k)), '#f6f2e8')
    pen = ImageDraw.Draw(im)
    title = ImageFont.truetype(str(FONT), 34); body = ImageFont.truetype(str(FONT), 21)
    pen.text((7 * k, 4 * k), 'DRIFTLESS / OPEN-GROWN BUR OAK, Quercus macrocarpa', font=title, fill='#202b24')
    record = []
    for i, (seed, azimuth) in enumerate(SPECIMENS):
        oak = savanna_oak(seed, 6.7, detail=3)
        d = render_oak(oak, *CELL, azimuth=azimuth, elevation=6)
        x, y = (i % cols) * CELL[0], (i // cols) * CELL[1] + 14
        for role, p in d.paths:
            q = p + [x, y]; sheet.paths.append((role, q))
            pen.line([tuple(v * k) for v in q], fill='#202b24', width=max(1, round(d.widths.get(role, .16) * k)))
        pen.text(((x + 6) * k, (y + CELL[1] - 9) * k), f'seed {seed} / azimuth {azimuth:g} deg', font=body,
                 fill='#202b24')
        record.append(dict(seed=seed, azimuth=azimuth, **d.stats(), **oak.summary(),
                           crown=d.metadata['crown'], scale_mm_per_metre=d.metadata['scale_mm_per_metre']))
        print(seed, azimuth, d.stats(), flush=True)
        sheet.widths.update(d.widths)
    sheet.metadata = dict(title='Open-grown bur oak', specimens=record, labels='PNG only; SVG holds art paths only')
    (OUT / 'savanna_oak.svg').write_text(sheet.svg())
    im.resize((im.width // 2, im.height // 2), Image.Resampling.LANCZOS).save(OUT / 'savanna_oak.png')
    (OUT / 'savanna_oak.json').write_text(json.dumps(record, indent=1, default=float))


if __name__ == '__main__':
    main()
