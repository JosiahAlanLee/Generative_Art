#!/usr/bin/env python3
"""Rebuild the committed plates, preview.jpg, detail.jpg and manifest.json.

    python build.py            # three A4 plates, about three minutes on two cores
    python build.py --no-png   # SVG and reports only; the previews need the PNGs
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import portrait

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
PLATES = (
    dict(subject='washington', view='bust'),
    dict(subject='washington', view='front'),
    dict(subject='lps', view='bust'),
)
# Detail crops for detail.jpg: (plate, square side in mm, offset of its centre from the head point in mm)
DETAILS = (('washington-bust', 60, (-14, 14)), ('washington-front', 66, (0, 25)), ('lps-bust', 64, (9, 4)))
MOUNT = '#cdc7b8'


def font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def contact_sheet(names, path, width=600, gap=24, pad=28):
    tiles = [Image.open(OUT / f'{n}.png').convert('RGB') for n in names]
    tiles = [t.resize((width, round(width * t.height / t.width)), Image.Resampling.LANCZOS) for t in tiles]
    h = max(t.height for t in tiles)
    sheet = Image.new('RGB', (2 * pad + len(tiles) * width + (len(tiles) - 1) * gap, 2 * pad + h), MOUNT)
    for i, t in enumerate(tiles):
        sheet.paste(t, (pad + i * (width + gap), pad))
    sheet.save(path, quality=86, optimize=True)


def detail_sheet(path, px_per_mm=14, size=620, gap=24, pad=28):
    import cairosvg
    f = font(18); tiles = []
    for name, side, (dx, dy) in DETAILS:
        hx, hy = json.loads((OUT / f'{name}-report.json').read_text())['head_xy_mm']
        x0, y0 = hx + dx - side / 2, hy + dy - side / 2; x1, y1 = x0 + side, y0 + side
        svg = (OUT / f'{name}.svg').read_text().replace(
            '<title>', f'<rect width="100%" height="100%" fill="{portrait.PAPER}"/><title>', 1)
        w, h = portrait.SHEETS['a4']['size']
        tmp = OUT / f'.{name}-detail.png'
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(tmp), output_width=int(w * px_per_mm),
                         output_height=int(h * px_per_mm))
        box = tuple(int(round(v * px_per_mm)) for v in (x0, y0, x1, y1))
        im = Image.open(tmp).convert('RGB').crop(box)
        tmp.unlink()
        tiles.append((name, im.resize((size, size), Image.Resampling.LANCZOS), side))
    sheet = Image.new('RGB', (2 * pad + len(tiles) * size + (len(tiles) - 1) * gap, 2 * pad + size + 34), MOUNT)
    d = ImageDraw.Draw(sheet)
    for i, (name, im, mm) in enumerate(tiles):
        x = pad + i * (size + gap)
        sheet.paste(im, (x, pad))
        d.text((x, pad + size + 8), f'{name}: {mm} mm square of the A4 sheet', fill='#252a23', font=f)
    sheet.save(path, quality=88, optimize=True)


def manifest():
    """sha256 of every committed file, and of the outputs build.py regenerates but Git ignores."""
    ignored = ('output/cache/', '__pycache__/')
    files, regenerated = {}, {}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in ('manifest.json', 'output/checks.json') or any(rel.startswith(i) or f'/{i}' in f'/{rel}' for i in ignored):
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        (regenerated if rel.endswith('.png') else files)[rel] = digest
    (ROOT / 'manifest.json').write_text(json.dumps(dict(files=files, regenerated=regenerated), indent=1) + '\n')
    print(f'manifest.json: {len(files)} committed files, {len(regenerated)} regenerated')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--no-png', action='store_true')
    a = ap.parse_args()
    for spec in PLATES:
        portrait.run(spec['subject'], spec['view'], png=not a.no_png)
    if not a.no_png:
        contact_sheet([f"{s['subject']}-{s['view']}" for s in PLATES], ROOT / 'preview.jpg')
        detail_sheet(ROOT / 'detail.jpg')
    manifest()


if __name__ == '__main__':
    main()
