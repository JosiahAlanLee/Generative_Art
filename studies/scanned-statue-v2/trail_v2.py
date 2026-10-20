#!/usr/bin/env python3
"""Trail First at plate resolution.

The vendor sampler (vendor/primitive_growth.py, unchanged) works in grid
cells: sensors 6-8 cells, steps of 1.25 cells, a 3x3 diffusion. v1 fixed the
grid at 384 px wide and halved it for the swarm, so on the full plate one cell
was 7.8 plate units and the network's mesh was larger than the head; the crop
brought it to 2.45. Here the grid cell is set in plate units (--cell), agent
numbers scale with the statue's area in cells, and mark sizes are set in mm,
so a finer grid shrinks the network without shrinking the marks.

Food comes from the v2 engraving's statue-only light image (object-space
shading, 2x2 supersampled at plate resolution), not the 750x950 v1 buffer.

--mode picks the food and swarm settings (original: darkness, sensors 6/7/8,
trail weight 1.8; guided: v1's contrast-guided extension). --sampling picks
where marks go (original: on the grown trails; guided: food-weighted with a
trail boost, which reads as stippling). Guided food with original sampling is
new here: the trails follow edges, and the marks follow the trails.
"""
import argparse, hashlib, json, math, sys
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import cairosvg

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
from primitive_growth import Swarm, weighted_indices, vertices, KINDS  # noqa: E402

SVG = 'http://www.w3.org/2000/svg'
PAPER = '#f3eddf'; INK = '#29261f'
W, H = 1500, 1900


def area_resample(a, cell):
    """Box-filter an image down so that one grid cell spans `cell` plate units."""
    h, w = a.shape
    gw, gh = max(8, int(round(w / cell))), max(8, int(round(h / cell)))
    im = Image.fromarray(a.astype(np.float32), mode='F')
    return np.asarray(im.resize((gw, gh), Image.Resampling.BOX), dtype=np.float64)


def run(food_png, mask_png, out, mode='original', cell=1.25, agents_per_cell=.05, count=7200,
        radius_mm=(.08, .2), plate_mm=148., seed=23, pad=40, steps=(35, 8), sampling=None):
    sampling = sampling or mode
    rng = np.random.default_rng(seed)
    light = np.asarray(Image.open(food_png).convert('L'), float) / 255
    mask_full = np.asarray(Image.open(mask_png).convert('L'), float) / 255 > .5
    b = Image.fromarray(np.uint8(mask_full) * 255).getbbox()
    bbox = (max(0, b[0] - pad), max(0, b[1] - pad), min(W, b[2] + pad), min(H, b[3] + pad))
    crop = light[bbox[1]:bbox[3], bbox[0]:bbox[2]]
    mcrop = mask_full[bbox[1]:bbox[3], bbox[0]:bbox[2]].astype(float)
    gray = area_resample(crop, cell); dom = area_resample(mcrop, cell)
    gh, gw = gray.shape
    sx = (bbox[2] - bbox[0]) / gw; sy = (bbox[3] - bbox[1]) / gh
    dark = np.clip(1 - gray, 0, 1)
    if mode == 'original':
        # v1 trail_study: darkness relative to the paper, light blur, 99th-pct normalisation.
        food = gaussian_filter(dark, .8)
        sensors = (6, 7, 8); trail_weight = 1.8
    else:
        # v1 contrast-guided extension: 65% darkness + 35% gradient, gated by the scan mask.
        gy, gx = np.gradient(gaussian_filter(gray, .65)); edge = np.hypot(gx, gy)
        edge = np.clip(edge / max(float(np.percentile(edge[edge > 0], 94)), 1e-8), 0, 1)
        food = gaussian_filter((.65 * dark + .35 * edge) * dom, .6)
        sensors = (3, 4, 5); trail_weight = .35
    food /= max(float(np.percentile(food, 99)), 1e-8)
    gate = dom > .5
    statue_cells = int(gate.sum())
    agents = max(200, int(round(agents_per_cell * statue_cells)))
    allocations = [round(count * .60), round(count * .20)]; allocations.append(count - sum(allocations))
    units_per_mm = W / plate_mm
    r0, r1 = radius_mm[0] * units_per_mm, radius_mm[1] * units_per_mm
    shapes = []; fields = []
    for ink, n in enumerate(allocations):
        colony = Swarm(food, rng, agents=agents, trail_weight=trail_weight, sensor=sensors[ink])
        acc = np.zeros_like(food)
        for _ in range(steps[1]):
            colony.advance(food, steps[0]); acc += colony.trail
        field = .65 * colony.trail + .35 * acc / steps[1]
        if sampling == 'original':
            # v1 Trail First rule: marks follow the grown trails.
            weights = np.maximum(field, 0) ** 1.25 * (.08 + food) ** .55 * (gate if mode == 'guided' else 1)
        else:
            norm = np.clip(field / max(float(np.percentile(field[gate], 97)), 1e-8), 0, 3)
            weights = (.45 + .55 * np.sqrt(norm)) * np.maximum(food, 0) ** .85 * gate
        ids = weighted_indices(rng, weights, n); ys, xs = ids // gw, ids % gw
        gy_, gx_ = np.gradient(gaussian_filter(field, 1))
        angles = np.degrees(np.arctan2(gy_[ys, xs], gx_[ys, xs])) + 90
        for j in range(n):
            shapes.append(dict(kind=KINDS[j % 3], x=bbox[0] + (xs[j] + rng.random()) * sx,
                               y=bbox[1] + (ys[j] + rng.random()) * sy, radius=float(rng.uniform(r0, r1)),
                               angle=int(round(angles[j] / 5) * 5), opacity=round(float(rng.uniform(.65, .95)), 4)))
        fields.append(field)
    rng.shuffle(shapes)
    meta = dict(method=f'trail-first-plate-scaled (food/swarm: {mode}; mark sampling: {sampling})', vendor_sampler='primitive_growth.Swarm, unmodified',
                food_source=Path(food_png).name, food_sha256=hashlib.sha256(Path(food_png).read_bytes()).hexdigest(),
                crop_bbox=list(bbox), grid=[gw, gh], cell_plate_units=cell, cell_mm=cell / units_per_mm,
                statue_cells=statue_cells, agents_per_colony=agents, steps_per_colony=steps[0] * steps[1],
                sensors_cells=list(sensors), sensors_mm=[s * cell / units_per_mm for s in sensors],
                trail_weight=trail_weight, primitives=len(shapes), ink_allocations=allocations,
                radius_mm=list(radius_mm), plate_mm=plate_mm, seed=seed,
                shape_counts=dict(Counter(s['kind'] for s in shapes)))
    trail = np.clip(sum(fields) / max(float(np.percentile(sum(fields), 99)), 1e-8), 0, 1)
    return shapes, meta, trail


def shape_elements(shapes):
    out = []
    for s in shapes:
        x, y, r, a = s['x'], s['y'], s['radius'], s['angle']
        st = f'fill="{INK}" fill-opacity="{s["opacity"]:.4f}"'
        if s['kind'] == 'circle':
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.3f}" {st}/>')
        elif s['kind'] == 'square':
            side = math.sqrt(math.pi) * r
            out.append(f'<rect x="{x - side / 2:.2f}" y="{y - side / 2:.2f}" width="{side:.3f}" height="{side:.3f}" '
                       f'transform="rotate({a} {x:.2f} {y:.2f})" {st}/>')
        else:
            pts = ' '.join(f'{px + x:.2f},{py + y:.2f}' for px, py in vertices('triangle', r, a))
            out.append(f'<polygon points="{pts}" {st}/>')
    return out


def write_plate(path, shapes, meta, plate_mm, support_svg=None, support_opacity=.72):
    parts = [f'<svg xmlns="{SVG}" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{plate_mm:.2f}mm" height="{plate_mm * H / W:.2f}mm" viewBox="0 0 {W} {H}">',
             '<title>Trail First at plate resolution - second statue angle</title>',
             f'<metadata>{json.dumps(meta, sort_keys=True)}</metadata>',
             f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    if support_svg:
        # The engraving's own layers, nested under one display layer at reduced opacity.
        text = Path(support_svg).read_text()
        inner = text[text.index('<g '):text.rindex('</svg>')]
        parts.append(f'<g id="surface-hatch-support" inkscape:groupmode="layer" inkscape:label="2 surface hatch" '
                     f'opacity="{support_opacity}">{inner}</g>')
    parts.append('<g id="trail-first-primitives" inkscape:groupmode="layer" inkscape:label="1 marks">'
                 + ''.join(shape_elements(shapes)) + '</g></svg>')
    svg = ''.join(parts)
    Path(path).write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(Path(path).with_suffix('.png')), output_width=W, output_height=H)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--food', default=str(ROOT / 'output/second-statue-food.png'))
    ap.add_argument('--mask', default=str(ROOT / 'output/second-statue-mask.png'))
    ap.add_argument('--support', default=str(ROOT / 'output/second-cross.svg'))
    ap.add_argument('--mode', choices=('original', 'guided'), default='original')
    ap.add_argument('--sampling', choices=('original', 'guided'), default=None,
                    help='mark placement rule (default: same as --mode). original = follow trails')
    ap.add_argument('--cell', type=float, default=1.25, help='grid cell in plate units (v1: 7.81 full frame, 2.45 crop)')
    ap.add_argument('--agents-per-cell', type=float, default=.05, help='agents per statue grid cell, per colony')
    ap.add_argument('--count', type=int, default=7200)
    ap.add_argument('--radius-mm', type=float, nargs=2, default=(.08, .2), help='v1 crop runs: ~0.08-0.21 mm')
    ap.add_argument('--plate-mm', type=float, default=148.)
    ap.add_argument('--seed', type=int, default=23)
    ap.add_argument('--name', default=None)
    ap.add_argument('--out', default=str(ROOT / 'output'))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    name = a.name or f'trail-{a.mode}-cell{a.cell:g}-n{a.count}'
    shapes, meta, trail = run(a.food, a.mask, out, a.mode, a.cell, a.agents_per_cell, a.count,
                              tuple(a.radius_mm), a.plate_mm, a.seed, sampling=a.sampling)
    write_plate(out / f'{name}.svg', shapes, meta, a.plate_mm)
    write_plate(out / f'{name}-supported.svg', shapes, dict(meta, surface_hatch_opacity=.72), a.plate_mm, a.support)
    Image.fromarray(np.uint8(255 - trail * 200)).save(out / f'{name}-trail.png')
    (out / f'{name}.json').write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta[k] for k in ('grid', 'cell_mm', 'agents_per_colony', 'sensors_mm', 'primitives')}))


if __name__ == '__main__':
    main()
