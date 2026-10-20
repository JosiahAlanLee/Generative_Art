#!/usr/bin/env python3
"""Memento Mori: the photophobic mould on Sol's windowsill.

Sol's scene, BVH, light model and hatching (memento_sol.py) are imported unchanged.
New here: surface grids for the sill, wall, book, skull and candle; Sol's light
evaluated on them; two strains grown in the shadow; and Sol's plate II redrawn with
paper reserved around the veins.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('NUMBA_NUM_THREADS', '4')        # memento_sol calls set_num_threads(4)
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'common')]

import numpy as np
from numba import njit, prange
from scipy.ndimage import median_filter

import memento_sol as ms                                 # Sol's file, unchanged
import atlas
import bvh as B
import mould
from camera import Camera

OUT = HERE / 'output'
CELL = 0.008               # finer than the corridor's 0.0125: these objects are small
NOISE_SCALE = 0.25          # this scene is about a fifth the size of the corridor
SEED = 2026
HATCH_KINDS = ('hatch', 'bone hatch', 'turned hatch', 'tooth hatch', 'cavity hatch')
SK = ms.SKULL_ORIGIN


def skull_point(local):
    return tuple(np.asarray(local, float) + SK)


SITES_A = [('left orbit', skull_point((-.205, -.30, .93)), .58),
           ('left jamb base', (-1.95, 1.03, 0.0), 1.5),
           ('sill, front left', (-1.25, -0.82, 0.0), 1.3)]
SITES_B = [('right orbit', skull_point((.205, -.30, .93)), .58),
           ('right jamb base', (1.95, 1.03, 0.0), 1.5),
           ('sill, front right', (1.55, -0.70, 0.0), 1.3),
           ('candle, front', (-1.43, 0.07, 0.55), .8)]


# ----------------------------------------------------------------------------
# Sol's light model at arbitrary surface points (mirrors memento_sol.bake)
# ----------------------------------------------------------------------------
@njit(cache=True, parallel=True)
def _light_points(P, Nrm, alb, light, samples, hemis, blo, bhi, nodes, tris, mats, normals):
    n = P.shape[0]
    out = np.zeros((n, 5))
    for i in prange(n):
        p = P[i]
        nn = Nrm[i]
        flat = ms.direct(p, nn, light, blo, bhi, nodes, tris, False)
        dl = 0.
        for j in range(samples.shape[0]):
            dl += ms.direct(p, nn, samples[j], blo, bhi, nodes, tris, True) / samples.shape[0]
        ao = 0.
        bounce = 0.
        for j in range(hemis.shape[0]):
            hdir = ms.hemisphere(nn, hemis[j, 0], hemis[j, 1])
            dd, hh = ms.cast(p + nn * .0015, hdir, .35, blo, bhi, nodes, tris)
            if hh >= 0:
                ao += 1 - dd / .35
            if j < 4:
                dd, hh = ms.cast(p + nn * .0015, hdir, 8., blo, bhi, nodes, tris)
                if hh >= 0 and mats[hh] != 3:
                    q = p + nn * .0015 + hdir * dd
                    n2 = normals[hh].copy()
                    if np.dot(n2, hdir) > 0:
                        n2 = -n2
                    m = mats[hh]
                    albedo = .70 if (m == 0 or m == 6 or m == 8 or m == 9) else (.52 if (m == 4 or m == 10) else .36)
                    bounce += ms.direct(q, n2, light, blo, bhi, nodes, tris, True) * albedo / 4
        ao /= hemis.shape[0]
        out[i, 0] = dl
        out[i, 1] = flat
        out[i, 2] = ao
        out[i, 3] = bounce
        out[i, 4] = min(1., max(0., .14 * (1 - .95 * ao) + (dl + .70 * bounce) * alb * 2.4))
    return out


class Scene:
    def __init__(self):
        t = time.time()
        ms.scene()
        self.candidates = ms.hatch_candidates()          # straight after scene(): same RNG draws as Sol's run
        self.bvh = ms.build_bvh()
        self.checks = ms.validate_queries(self.bvh)
        self.data = ms.lighting(self.bvh)
        self.cam = Camera(ms.EYE, ms.F, ms.R, ms.U, ms.FOCAL, ms.CX, ms.CY, ms.W, ms.H)
        self.samples = np.array([ms.LIGHT + [dy, 0, dz] for dy, dz in [(-.45, -.5), (-.45, .5), (.45, -.5), (.45, .5)]])
        self.hemis = np.column_stack([(np.arange(16) + .5) / 16, ((np.arange(16) * .61803398875) % 1)])
        self.surfaces = self._surfaces()
        print(f'memento scene ready in {time.time() - t:.0f}s', flush=True)

    def light_fn(self, P, N, alb):
        blo, bhi, nodes, tris, mats, normals = self.bvh
        ch = _light_points(P, N, float(alb), ms.LIGHT.astype(float), self.samples, self.hemis,
                           blo, bhi, nodes, tris, mats, normals)
        traced = ch[:, 4]
        return dict(direct=ch[:, 0], flat=ch[:, 1], ao=ch[:, 2], bounce=ch[:, 3], traced=traced,
                    darkness=1 - np.sqrt(traced), excess=mould.excess_from(ch[:, 0], ch[:, 3], alb))

    def visible(self, pts):
        return ms.point_visibility(np.ascontiguousarray(pts), *self.bvh[:4])

    def _surfaces(self):
        ri, spring = 1.63, 2.02

        def outside_window(u, v):
            opening = (np.abs(u) < ri) & ((v < spring) | (u ** 2 + (v - spring) ** 2 < ri ** 2))
            return ~opening

        def sill_domain(u, v):
            return ~((np.abs(u) > ri) & (v > 1.03))

        a = -.075
        c, s = math.cos(a), math.sin(a)
        Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])
        o = np.array([-.55, .05, 0.])
        book_at = lambda local: o + Rz @ (np.asarray(local, float) - o)
        # Thin strips (the sill's front face, the book's fore-edge) are left out: on a
        # band a few dozen cells tall the network collapses into one long vein.
        surfaces = [
            atlas.Plane('sill top', -2.15, 2.15, -1.0, 1.25, (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), CELL, sill_domain),
            atlas.Plane('wall', -2.2, 2.2, 0.0, 4.1, (0, 1.03, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0), CELL, outside_window),
            atlas.Plane('book cover', -1.35, .22, -.57, .65, book_at((0, 0, .22)), Rz[:, 0], Rz[:, 1], (0, 0, 1), CELL,
                        albedo=.42),
        ]
        # The skull (and teeth) by an equal-area map about the direction to the camera.
        sk = [k for k, f in enumerate(ms.FACES) if f.mat in (6, 9)]
        tris = []
        for k in sk:
            p = ms.FACES[k].p
            for i in range(1, len(p) - 1):
                t = p[[0, i, i + 1]]
                if np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) > 1e-12:
                    tris.append(t)
        blo, bhi, nodes, ot, _, nrm = B.build(np.array(tris))

        def cast(origins, dirs, tmax):
            dist, hit = B.first_hits(origins, dirs, tmax, blo, bhi, nodes, ot)
            return dist, hit, nrm[np.clip(hit, 0, None)]

        skull = atlas.Radial('skull', SK + np.array([0, .05, .95]), ms.EYE, .55, math.radians(118), CELL, cast,
                             right_hint=ms.R)
        candle = atlas.Lathe('candle', -1.43, .20, .30, 1.78,
                             lambda z: .125 + .006 * np.sin(z * 11) + .003 * np.sin(z * 23), .125, ms.EYE, CELL,
                             albedo=.78)
        surfaces += [skull, candle]
        return surfaces

    # ------------------------------------------------------------------
    def base_ink(self):
        """Sol's plate II, redrawn from his candidates and rules, with each mark labelled."""
        cands = self.candidates
        sizes = [len(p) for p, *_ in cands]
        pts = np.concatenate([p for p, *_ in cands])
        blo, bhi, nodes, tris = self.bvh[:4]
        vis = ms.point_visibility(pts, blo, bhi, nodes, tris)
        pp_ = ms.projection(pts)
        vis &= (pp_[:, 2] > .15) & (pp_[:, 0] > 2) & (pp_[:, 0] < ms.W - 2) & (pp_[:, 1] > 2) & (pp_[:, 1] < ms.H - 2)
        ix = np.clip((pp_[:, 0] / ms.W * ms.GW).astype(int), 0, ms.GW - 1)
        iy = np.clip((pp_[:, 1] / ms.H * ms.GH).astype(int), 0, ms.GH - 1)
        dark = 1 - np.sqrt(np.clip(median_filter(self.data[:, :, 1], size=3), 0, 1))
        out, start = [], 0
        for (p, width, threshold, family, kind), size in zip(cands, sizes):
            sl = slice(start, start + size)
            keep = vis[sl].copy()
            xy = pp_[sl, :2]
            density = dark[iy[sl], ix[sl]]
            if threshold >= 0:
                keep &= density > threshold
            if kind in ('hatch', 'bone hatch', 'turned hatch', 'tooth hatch'):
                indices = np.arange(size)
                phase = ((math.sin(start * 12.9898) * 43758.5453) % 1) * 2 * math.pi
                keep &= (np.sin(indices * .25 + phase) > -.90) | (density > .73)
            changes = np.diff(np.r_[0, keep.astype(np.int8), 0])
            for a, b in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)):
                if b - a < 2:
                    continue
                q = ms.rdp(xy[a:b])
                if np.linalg.norm(q[-1] - q[0]) < 1.4:
                    continue
                out.append((np.array(q), width, 1.0, kind in HATCH_KINDS))
            start += size
        return out


def svg_body(lines):
    return ''.join('<path d="M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in q) + f'" stroke-width="{w:.2f}"/>'
                   for q, w, _, _ in lines)


def main():
    OUT.mkdir(exist_ok=True)
    sc = Scene()
    t = time.time()
    base = sc.base_ink()
    sol = (HERE / 'inputs' / '02-ray-lit.svg').read_text()
    same = svg_body(base) in sol
    print(f'base ink: {len(base)} marks, {time.time() - t:.0f}s; identical to Sol\'s plate II: {same}', flush=True)
    light, results, stats = {}, {}, {}
    for s in sc.surfaces:
        t = time.time()
        L = mould.surface_light(s, sc.light_fn)
        light[s.name] = L
        r = mould.run_strains(s, L, SITES_A, SITES_B, SEED + len(results), noise_scale=NOISE_SCALE,
                              params=dict(mould.PARAMS, density=0.2))
        results[s.name] = r
        moved, in_light = mould.contest(r)
        stats[s.name] = dict(grid=[s.nu, s.nv], lit_share=float((L['excess'][r['domain']] > .5).mean()),
                             changed_strain=moved, trail_on_lit_ground=in_light)
        print(f'{s.name}: grid {s.nu}x{s.nv}, lit {100 * stats[s.name]["lit_share"]:.1f}%, '
              f'changed strain {100 * moved:.1f}%, trail on lit ground {100 * in_light:.2f}%, {time.time() - t:.0f}s',
              flush=True)
    import pickle
    np.savez_compressed(OUT / 'mould.npz', **{f'{k}__{c}': v for k, r in results.items() for c, v in r.items()},
                        **{f'{k}__light_{c}': v for k, L in light.items() for c, v in L.items()})
    colony = mould.colony_strokes(sc.surfaces, results, sc.cam)
    vis = np.zeros(len(colony.world), bool)
    alive = colony.attr['alive'].astype(bool) & sc.cam.inside(colony.xy[:, 0], colony.xy[:, 1], colony.z)
    vis[alive] = sc.visible(colony.world[alive])
    V = mould.veins(colony, vis, sc.cam, cap=0.16)
    layers, alone, cstats = mould.compose(base, V)
    mould.write_svg(OUT / 'M1-mould-in-shadow.svg', layers, 'Memento mori: the mould in the shadow', sc.cam)
    mould.write_svg(OUT / 'M2-mould-alone.svg', alone, 'Memento mori: the mould alone', sc.cam)
    stats['plate'] = cstats
    stats['plate']['ink_near_mould'] = mould.local_ink(HERE / 'inputs' / '02-ray-lit.png', OUT / 'M1-mould-in-shadow.png',
                                                       V, sc.cam)
    stats['base_identical_to_sol'] = same
    (OUT / 'veins.pkl').write_bytes(pickle.dumps(dict(lines=V['lines'], strains=V['strains'])))
    import diagnostics
    diagnostics.who_holds_the_shade(sc.surfaces, results, sc.cam, sc.visible, SITES_A, SITES_B, OUT / 'shade-map.png', lift=0.002, lines_png=OUT / 'M2-mould-alone.png')
    stats['scene'] = diagnostics.scene_totals(results)
    stats['checks'] = sc.checks
    (OUT / 'stats.json').write_text(json.dumps(stats, indent=1))
    print(json.dumps(cstats), flush=True)


if __name__ == '__main__':
    main()
