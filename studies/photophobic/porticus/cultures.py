"""Two cultures on each corridor surface, their ground divided by the traced light.

The shadow culture (fine, organic mesh) holds the ground the doorway light does not
reach; the light culture (the engine's feral look: coarse honeycomb) holds the lit
ground. Ground is marked, so the border starts on the light's edge and afterwards
moves only by competition. Each surface is its own grid in scene units.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

import surfaces as S          # first: it sets NUMBA_NUM_THREADS before numba loads
import physarum_plot as pp

OUT = Path(__file__).resolve().parent / 'output'
CHANNELS = ('darkness', 'direct', 'flat', 'ao', 'bounce')
SHADOW_LOOK = dict(wfood=6.0, flow=0.15, so=8.0, edge=1.0)
LIGHT_LOOK = pp.LOOKS['feral']
PARAMS = dict(repel=0.5, mark=0.5, steps=900, density=0.12, held_sigma=8.0, avg_last=150)

# Where the colonies start (scene coordinates) and how far each reaches. The shadow
# culture is inoculated where a slime mould would plausibly be: damp wall bases,
# under the wooden bench, at the wooden rear door, and a seep in the vault. The
# light culture starts at the side doorway's threshold and can only hold lit ground.
INOCULA = [('left wall base, near', (-2.6, 1.2, 0.0), 2.6),
           ('right wall base, near', (2.6, 0.2, 0.0), 2.0),
           ('under the bench', (2.1, 10.7, 0.0), 3.2),
           ('left wall base, far', (-2.6, 16.0, 0.0), 2.8),
           ('rear door', (0.0, 21.7, 0.8), 3.4),
           ('seep in the vault', (-1.3, 12.6, 5.85), 2.3)]
THRESHOLD = ('side doorway threshold', (-2.6, 6.0, 0.0), 6.5)
SEEDS = {'floor': 1618, 'wall_left': 1619, 'wall_right': 1620, 'vault': 1621, 'rear_wall': 1622}


def compute_light():
    res = {}
    for s in S.SURFACES:
        t = time.time()
        L = S.surface_light(s)
        res.update({f'{s.name}__{c}': L[c] for c in CHANNELS})
        print(f'light {s.name}: {time.time() - t:.0f}s', flush=True)
    np.savez_compressed(OUT / 'surface_light.npz', **res)


def load_light():
    z = np.load(OUT / 'surface_light.npz')
    return {s.name: {c: z[f'{s.name}__{c}'] for c in CHANNELS} for s in S.SURFACES}


def lit_ground(L):
    """Where the doorway light actually arrives: most of the source visible."""
    return (L['direct'] > 0.4 * L['flat']) & (L['direct'] > 0.02)


def joints_raster(s):
    """Sol's mortar and flagstone joints that lie on this surface, rasterized at cell size."""
    img = Image.new('F', (s.nu, s.nv), 0.0)
    dr = ImageDraw.Draw(img)
    if isinstance(s, S.Plane):
        for p, _, kind in S.hs.LINES:
            if kind in ('mortar', 'flagstone') and np.all(np.abs((p - s.origin) @ s.n) < 0.02):
                c, r = s.uv_cell(*s.to_uv(p))
                dr.line(list(zip(c.tolist(), r.tolist())), fill=1.0, width=1)
    a = gaussian_filter(np.asarray(img, np.float32), 1.0)
    return (a / (a.max() + 1e-9)).astype(np.float32)


def noise3(P, seed=11, octaves=4, base=0.45):
    """Smooth world-space noise in about [-1, 1] (sums of random plane waves), so a
    colony's front stays continuous across the seam between floor and wall."""
    rng = np.random.default_rng(seed)
    acc, norm = np.zeros(P.shape[:-1]), 0.0
    for i in range(octaves):
        amp, f = 0.55 ** i, base * 2.0 ** i
        for _ in range(3):
            k = rng.normal(size=3)
            k /= np.linalg.norm(k)
            acc += amp * np.sin(2 * np.pi * f * (P @ k) + rng.uniform(0, 2 * np.pi))
            norm += amp
    return acc / norm * 2.2


def reach(P, sites, wobble=0.35, seed=11):
    """1 at an inoculation point, falling to 0 at its (noisy) reach."""
    n = noise3(P, seed)
    out = np.zeros(P.shape[:-1])
    for _, c, R in sites:
        x = np.linalg.norm(P - np.array(c), axis=-1) / (R * (1 + wobble * n))
        out = np.maximum(out, np.clip(1 - x, 0, 1) ** 0.6)
    return out


def colony_density(s, L):
    """Where each culture lives on this surface: shadow colonies around the inocula,
    the light colony around the threshold, each only on its own ground."""
    uu, vv = s.centers(1)
    P = s.world(uu, vv)
    lit = gaussian_filter(lit_ground(L).astype(float), 3)
    shadow = reach(P, INOCULA) * (1 - lit)
    light = reach(P, [THRESHOLD], wobble=0.2, seed=5) * lit
    return shadow.astype(np.float32), light.astype(np.float32)


def fields_for(s, L):
    uu, vv = s.centers(1)
    dom = s.domain(uu, vv)
    dark = L['darkness']
    joints = joints_raster(s)
    ds, dl = colony_density(s, L)
    phi, fstr = pp.structure_flow([dark])
    near_s = 0.35 + 0.65 * gaussian_filter(ds, 4)
    near_l = 0.35 + 0.65 * gaussian_filter(dl, 4)
    fields = dict(dark=(np.maximum(ds, dl) * dom).astype(np.float32), phi=phi, fstr=fstr, home=None, accents=[],
                  foods=[((0.6 * gaussian_filter(dark, 2) + 0.15 * joints) * near_s).astype(np.float32),  # shadow
                         (0.6 * gaussian_filter(1 - dark, 2) * near_l).astype(np.float32)])              # light
    return fields, dom


def run(s, L, verbose=True):
    fields, dom = fields_for(s, L)
    shadow_ground = ~lit_ground(L) & dom
    t = time.time()
    sim = pp.simulate_cultures(fields, (SHADOW_LOOK, LIGHT_LOOK), 0.5, territories=0, seed=SEEDS[s.name],
                               verbose=False, territory_map=shadow_ground, domain=dom, **PARAMS)
    held = sim['held']
    if verbose:
        moved = ((held > 0.5) != shadow_ground)[dom].mean()
        print(f'cultures {s.name}: {time.time() - t:.0f}s, lit ground at seed {100 * (~shadow_ground[dom]).mean():.1f}%, '
              f'changed hands {100 * moved:.1f}%', flush=True)
    return dict(light_trail=sim['trail'][0], shadow_trail=sim['trail'][1], held=held,
                seed_ground=shadow_ground, domain=dom, colony=fields['dark'])


def main():
    if '--light' in sys.argv or not (OUT / 'surface_light.npz').exists():
        compute_light()
    light = load_light()
    res = {}
    for s in S.SURFACES:
        for k, v in run(s, light[s.name]).items():
            res[f'{s.name}__{k}'] = v
    np.savez_compressed(OUT / 'cultures.npz', **res)
    print('saved', OUT / 'cultures.npz')


if __name__ == '__main__':
    main()
