#!/usr/bin/env python3
"""Checks for the scan portraits.

    python checks.py            # everything, including one plate rebuilt from scratch (about a minute)
    python checks.py --quick    # skip the rebuild

1. Each model file is byte-identical to its pinned upstream copy, and its licence travels with it.
2. Each committed plate is stroke-only, inside the Codex plot-master extent, and its report's
   line totals match the SVG.
3. Drawn lines sit where the camera sees the scan: every head-layer point lies on the scan's
   silhouette (to within a line's smoothing), every ground point clear of it. Stipple dots sit
   between the lines, and their count matches what the light asks for.
4. Loop subdivision keeps a flat sheet flat and its UV layout aligned with the positions.
5. Ridge and valley lines on a corrugated sheet land on its crests and troughs.
6. The key light on a sphere is the cosine law, and a convex sphere has no occlusion.
7. A plate rebuilt from scratch is byte-identical to the committed one.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion

import creases
import ground
import light
import portrait
import raycore
import subdivide
import subjects

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print(('ok   ' if ok else 'FAIL ') + name + (f': {detail}' if detail and not ok else (f' ({detail})' if detail else '')))


def svg_paths(text):
    """{layer id: [N x 2 arrays]} from a plate SVG, and every element name used."""
    layers = {}
    for m in re.finditer(r'<g id="([a-z]+)"[^>]*>(.*?)</g>', text, re.S):
        layers[m.group(1)] = [np.array([[float(v) for v in xy.split(',')] for xy in d[1:].split(' L')])
                              for d in re.findall(r'<path d="([^"]+)"/>', m.group(2))]
    return layers, set(re.findall(r'<([a-zA-Z]+)[\s>/]', text))


# ------------------------------------------------------------------ 1. models
def models():
    for key in subjects.SUBJECTS:
        for name, ok in subjects.verify(key).items():
            check(f'{key}: {name} matches its pinned upstream copy', ok)
    lic = (subjects.MODELS / 'washington-bust' / 'LICENSE').read_text()
    check('washington: CC0 licence file present', 'CC0' in lic and 'NPG.70.4' in lic)
    lic = (subjects.MODELS / 'lee-perry-smith' / 'LeePerrySmith_License.txt').read_text()
    check('lps: CC BY 3.0 licence file present', 'Creative Commons Attribution 3.0' in lic and 'Lee Perry-Smith' in lic)


# ------------------------------------------------------------------ 2. plates
def plates():
    for svg in sorted(OUT.glob('*.svg')):
        rep = json.loads(svg.with_name(svg.stem + '-report.json').read_text())
        text = svg.read_text()
        layers, tags = svg_paths(text)
        x0, y0, x1, y1 = rep['extent_mm']
        pts = np.concatenate([p for ps in layers.values() for p in ps])
        inside = (pts[:, 0] >= x0) & (pts[:, 0] <= x1) & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
        check(f'{svg.name}: every point inside {x0:g}-{x1:g} x {y0:g}-{y1:g} mm', inside.all(),
              f'{(~inside).sum()} outside')
        fills = set(re.findall(r'fill="([^"]+)"', text))
        check(f'{svg.name}: stroke-only (paths in layers, no fills)', tags <= {'svg', 'title', 'desc', 'g', 'path'}
              and fills <= {'none'}, f'tags {sorted(tags)}, fills {sorted(fills)}')
        down = sum(float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) for p in pts_split(layers)) / 1000
        check(f'{svg.name}: report line total matches the SVG', abs(down - rep['pen_down_m']) < .02,
              f'{down:.2f} m against {rep["pen_down_m"]} m')
        counts = {k: len(v) for k, v in layers.items()}
        check(f'{svg.name}: report path counts match the SVG',
              counts == {k: v for k, v in rep['paths_by_layer'].items() if v}, f'{counts}')
        check(f'{svg.name}: credit carried in the SVG', subjects.SUBJECTS[rep['subject']].credit in text)


def pts_split(layers):
    return [p for ps in layers.values() for p in ps]


# ---------------------------------------------------------------- 3. coverage
def placement():
    for svg in sorted(OUT.glob('*.svg')):
        rep = json.loads(svg.with_name(svg.stem + '-report.json').read_text())
        subject = subjects.SUBJECTS[rep['subject']]
        scan = subjects.load(rep['subject'])
        cam = portrait.make_camera(subject, rep['view_settings'], portrait.SHEETS[rep['sheet']])
        check(f'{svg.name}: camera rebuilt from the report', np.allclose(cam.eye, rep['eye'], atol=1e-6))
        bvh = raycore.build_bvh(scan.V[scan.F], np.zeros(len(scan.F), int))
        res = .1
        layers, _ = svg_paths(svg.read_text())
        shift = np.array(rep['placement_shift_mm'])
        allp = np.concatenate([p for ps in layers.values() for p in ps]) - shift
        lo, hi = allp.min(0) - 3, allp.max(0) + 3
        region = (lo[0], lo[1], hi[0], hi[1])
        mask = ground.subject_mask(cam, bvh, region, res)

        def cells(ps):
            q = np.concatenate([densify(p) for p in ps]) - shift
            return (np.clip(((q[:, 1] - region[1]) / res).astype(int), 0, mask.shape[0] - 1),
                    np.clip(((q[:, 0] - region[0]) / res).astype(int), 0, mask.shape[1] - 1))

        tol = int(math.ceil(.6 / res))   # 0.6 mm: the Gaussian easing of feature lines and RDP simplification
        grown = binary_dilation(mask, iterations=tol)
        head = [p for k in ('hatch', 'cross', 'dots', 'folds', 'outlines') for p in layers.get(k, [])]
        r, c = cells(head)
        frac = grown[r, c].mean()
        check(f'{svg.name}: head lines lie on the scan as the camera sees it', frac > .999, f'{frac:.5f} of points')
        if layers.get('ground'):
            r, c = cells(layers['ground'])
            shrunk = binary_erosion(mask, iterations=int(math.ceil(.3 / res)))
            frac = (~shrunk[r, c]).mean()
            check(f'{svg.name}: the ground stays off the head', frac > .9999, f'{frac:.5f} of points')


def densify(p, step=.2):
    out = [p[:1]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        out.append(a + (b - a) * (np.arange(1, n + 1) / n)[:, None])
    return np.concatenate(out)


def stipple_checks():
    from scipy.spatial import cKDTree
    for svg in sorted(OUT.glob('*.svg')):
        rep = json.loads(svg.with_name(svg.stem + '-report.json').read_text())
        layers, _ = svg_paths(svg.read_text())
        dots = np.array([p[:-1].mean(0) for p in layers.get('dots', [])])
        info = rep['stipple']
        if not len(dots):
            check(f'{svg.name}: no stipple asked for', info['dots'] == 0)
            continue
        check(f'{svg.name}: stipple count within 5 % of what the light asks for',
              abs(info['dots'] / info['asked'] - 1) <= .05, f"{info['dots']} dots, {info['asked']} asked")
        lines = np.concatenate([densify(p, .05) for k in ('hatch', 'cross', 'folds', 'outlines') for p in layers.get(k, [])])
        gap, _ = cKDTree(lines).query(dots)
        need = rep['pen_mm'] / 2 + info['ink_radius_mm']        # line edge to dot edge just touching
        check(f'{svg.name}: dots sit between the lines, not on them', gap.min() >= need,
              f'closest {gap.min():.3f} mm centre to line, touching at {need:.3f} mm')


def packing():
    import stipple
    from lib.halftone import poisson_sample
    rng = np.random.default_rng(1)
    r = .6
    pts = poisson_sample((0, 0, 30, 30), lambda p: r, rng, min_radius=r, quality=600, iterations=3)
    inner = ((pts > 3) & (pts < 27)).all(1).sum()
    k = inner * r * r / 24 ** 2
    check('Poisson stipple packs as stipple.PACKING assumes on a uniform field', abs(k - stipple.PACKING) < .02,
          f'{k:.3f} against {stipple.PACKING}')


# ------------------------------------------------------------- 4-6. geometry
def grid(n, size=1.):
    u = np.linspace(0, size, n)
    X, Y = np.meshgrid(u, u, indexing='ij')
    V = np.stack([X.ravel(), Y.ravel(), np.zeros(n * n)], 1)
    idx = np.arange(n * n).reshape(n, n)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    F = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    return V, F


def subdivision():
    V, F = grid(9)
    # A UV seam down the middle: records right of x = .5 are duplicated, as a texture atlas splits them.
    UV = V[:, :2].copy(); Fu = F.copy()
    right = np.flatnonzero(V[:, 0] >= .5 - 1e-9)
    dup = {int(i): len(UV) + k for k, i in enumerate(right)}
    UV = np.concatenate([UV, UV[right] * [1., 1.] + [.25, 0.]])   # shifted half of the atlas
    face_right = V[F].mean(1)[:, 0] > .5
    Fu[face_right] = np.vectorize(lambda i: dup.get(int(i), i))(F[face_right])
    V2, F2, Fu2, UV2 = subdivide.loop(V, F, 2, Fu, UV)
    check('subdivision keeps a flat sheet flat', np.abs(V2[:, 2]).max() < 1e-12)
    check('subdivision gives each triangle four children', len(F2) == 16 * len(F) and len(Fu2) == len(F2))
    # Positions and UVs are both linear in a flat sheet's interior, so a child triangle's UV must be
    # its positions (plus the atlas shift on the right half) wherever the boundary rule did not act.
    P = V2[F2][:, :, :2]; Q = UV2[Fu2]
    shift = np.where(P.mean(1)[:, :1] > .5, .25, 0.)
    interior = (P.min((1, 2)) > .2) & (P.max((1, 2)) < .8)
    err = np.abs(Q[interior] - P[interior] - np.stack([shift[interior], np.zeros_like(shift[interior])], -1)).max()
    check('subdivision keeps the UV layout on its triangles, across a seam', err < 1e-9, f'max error {err:.2e}')


def corrugated():
    n, lam, amp = 240, .25, .02          # 240 points: no crest or trough falls exactly on a vertex
    V, F = grid(n)
    V[:, 2] = amp * np.cos(2 * np.pi * V[:, 0] / lam)
    vn = portrait.vertex_normals(V, F)
    ok = True; detail = []
    for kind, phase in (('valley', .5), ('ridge', 0.)):
        chains, info = creases.crease_lines(V, F, vn, kind, 2., 1.)
        pts = np.concatenate([c[0] for c in chains]) if chains else np.zeros((0, 3))
        core = pts[(pts[:, 0] > .1) & (pts[:, 0] < .9) & (pts[:, 1] > .1) & (pts[:, 1] < .9)]
        off = np.abs(((core[:, 0] / lam - phase + .5) % 1) - .5) * lam if len(core) else np.array([1.])
        expected = sum(1 for k in range(-2, 8) if .1 < (k + phase) * lam < .9)
        lines = len({round((x / lam - phase)) for x in core[:, 0]}) if len(core) else 0
        ok &= off.max() < .004 and lines == expected
        detail.append(f'{kind}: {lines} of {expected} lines, worst offset {100 * off.max() / lam:.2f}% of the wavelength')
    check('ridge and valley lines fall on the crests and troughs', ok, '; '.join(detail))


def sphere_light():
    m = __import__('trimesh').creation.icosphere(subdivisions=5, radius=.2)
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces)
    vn = portrait.vertex_normals(V, F)
    bvh = raycore.build_bvh(V[F], np.zeros(len(F), int))
    d = light.direction(-40., 30.)
    pts = light.area_samples(np.zeros(3), d, 50., .01, 2)          # a small, distant key
    terms = light.shade(V, vn, pts, d * 50., d, light.hemisphere(32), .06, 1e-4, *bvh[:3], *bvh[3:6])
    cos = np.clip(vn @ d, 0, 1)
    lit = cos > .1
    err = np.abs(terms[lit, 0] - cos[lit]).max()
    check('key light on a sphere follows the cosine law', err < .02, f'max error {err:.4f}')
    check('a convex sphere has no occlusion', terms[:, 2].max() < 1e-9, f'max {terms[:, 2].max():.2e}')


def ordering():
    rng = np.random.default_rng(3)
    paths = [rng.uniform(0, 200, (2, 2)) for _ in range(400)]
    ordered = portrait.order_paths(paths)
    same = sorted(map(lambda p: tuple(np.round(np.sort(p, 0).ravel(), 9)), paths)) == \
        sorted(map(lambda p: tuple(np.round(np.sort(p, 0).ravel(), 9)), ordered))
    check('path ordering keeps every path and shortens pen-up travel',
          same and portrait.travel(ordered) < .3 * portrait.travel(paths),
          f'{portrait.travel(paths) / 1000:.1f} m to {portrait.travel(ordered) / 1000:.1f} m')


# ------------------------------------------------------------- 7. rebuild
def rebuild(name='lps-bust'):
    rep = json.loads((OUT / f'{name}-report.json').read_text())
    with tempfile.TemporaryDirectory() as tmp:
        portrait.run(rep['subject'], rep['view'], rep['sheet'], rep['pen_mm'], rep['spacing_pen_widths'], out=tmp,
                     png=False)
        for suffix in ('.svg', '-report.json'):
            a = hashlib.sha256((OUT / f'{name}{suffix}').read_bytes()).hexdigest()
            b = hashlib.sha256((Path(tmp) / f'{name}{suffix}').read_bytes()).hexdigest()
            check(f'{name}{suffix} rebuilds byte for byte', a == b)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quick', action='store_true', help='skip the from-scratch rebuild')
    a = ap.parse_args()
    models(); plates(); placement(); stipple_checks(); packing(); subdivision(); corrugated(); sphere_light(); ordering()
    if not a.quick:
        rebuild()
    failed = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed')
    (ROOT / 'output' / 'checks.json').write_text(json.dumps(dict(passed=len(RESULTS) - len(failed), failed=failed,
                                                                 checks=[dict(name=n, ok=ok) for n, ok in RESULTS]),
                                                            indent=1) + '\n')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
