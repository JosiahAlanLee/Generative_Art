#!/usr/bin/env python3
"""Porticus Intervallorum: the photophobic mould in Sol's corridor.

Sol's scene, BVH and light model (hallway_sol.py) and the previous package's
surface grids and screen-spaced hatching (surfaces.py, render.py, cultures.py, from
Porticus_Cultures) are imported unchanged. The light culture is gone: two strains
of one mould share the shadow, and the doorway's light repels them.
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time
from pathlib import Path

os.environ.setdefault('NUMBA_NUM_THREADS', '4')
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'common')]

import numpy as np

import surfaces as S                 # Porticus_Cultures, unchanged (imports hallway_sol)
import render as Rn                  # Porticus_Cultures, unchanged
import cultures as C                 # Porticus_Cultures, unchanged
import mould
from camera import Camera

OUT = HERE / 'output'
SITES = {name: (c, R) for name, c, R in C.INOCULA}
SITES_A = [(n, *SITES[n]) for n in ('left wall base, near', 'under the bench', 'seep in the vault')]
SITES_B = [(n, *SITES[n]) for n in ('right wall base, near', 'left wall base, far', 'rear door')]


def light_fn(P, N, alb):
    samples, hemis = S.light_samples()
    ch = S._light_points(P, N, S.hs.LIGHT.astype(float), samples, hemis, S.BLO, S.BHI, S.NODES, S.TRIS,
                         S.MATS, S.NORMALS)
    dl, flat, ao, bounce = ch[:, 0], ch[:, 1], ch[:, 2], ch[:, 3]
    traced = np.clip(.14 * (1 - .70 * ao) + (dl + .70 * bounce) * alb * 2.4, 0, 1)
    return dict(direct=dl, flat=flat, ao=ao, bounce=bounce, traced=traced, darkness=1 - np.sqrt(traced),
                excess=mould.excess_from(dl, bounce, alb))


def visible(pts):
    return S.hs.point_visibility(np.ascontiguousarray(pts), S.BLO, S.BHI, S.NODES, S.TRIS)


def base_ink(tone, hatch_st, struct_st, share=None):
    """The previous package's plate II (ink by screen spacing). With `share`, the
    hatching is allocated to hold the local tone around the paper the white line
    will reserve: each point asks for coverage / (1 - share)."""
    keep_s = struct_st.vis
    lines_s, widths_s = Rn.runs(struct_st, keep_s, min_px=1.4)
    used = Rn.coverage_map(struct_st, keep_s, 1.0)
    d = tone.at(hatch_st)
    if share is not None:
        f = mould.sample(share[::mould.GRID, ::mould.GRID], hatch_st.xy)
        d = np.clip(d * (1 / (1 - f)) ** (1 / Rn.GAMMA), 0, 1)
    keep_h = Rn.allocate_hatch(hatch_st, d, used, hatch_st.vis)
    lines_h, widths_h = Rn.runs(hatch_st, keep_h)
    return ([(np.asarray(q), w, 1.0, False) for q, w in zip(lines_s, widths_s)] +
            [(np.asarray(q), w, 1.0, True) for q, w in zip(lines_h, widths_h)])


def main():
    OUT.mkdir(exist_ok=True)
    cam = Camera(S.EYE, S.F, S.R, S.U, S.FOCAL, S.CX, S.CY, S.W, S.H)
    for s in S.SURFACES:
        s.material_albedo, s.cell = .72, S.CELL
    light, results, stats = {}, {}, {}
    for s in S.SURFACES:
        t = time.time()
        L = mould.surface_light(s, light_fn)
        light[s.name] = L
        r = mould.run_strains(s, L, SITES_A, SITES_B, C.SEEDS[s.name], joints=C.joints_raster(s))
        results[s.name] = r
        moved, in_light = mould.contest(r)
        stats[s.name] = dict(grid=[s.nu, s.nv], lit_share=float((L['excess'][r['domain']] > .5).mean()),
                             changed_strain=moved, trail_on_lit_ground=in_light)
        print(f'{s.name}: grid {s.nu}x{s.nv}, lit {100 * stats[s.name]["lit_share"]:.1f}%, '
              f'changed strain {100 * moved:.1f}%, trail on lit ground {100 * in_light:.2f}%, {time.time() - t:.0f}s',
              flush=True)
    np.savez_compressed(OUT / 'mould.npz', **{f'{k}__{c}': v for k, r in results.items() for c, v in r.items()},
                        **{f'{k}__light_{c}': v for k, L in light.items() for c, v in L.items()})
    colony = mould.colony_strokes(S.SURFACES, results, cam)
    vis = np.zeros(len(colony.world), bool)
    alive = colony.attr['alive'].astype(bool) & cam.inside(colony.xy[:, 0], colony.xy[:, 1], colony.z)
    vis[alive] = visible(colony.world[alive])
    V = mould.veins(colony, vis, cam, cap=0.16)

    t = time.time()
    struct_st = Rn.structure_strokes()
    struct_st.vis = Rn.visible_lines(struct_st)
    hatch_st = Rn.build_hatch()
    hatch_st.vis = Rn.visible(hatch_st)
    tone = Rn.Tone(light)
    print(f'hatching ready in {time.time() - t:.0f}s', flush=True)
    plain = base_ink(tone, hatch_st, struct_st)
    mould.write_svg(OUT / 'P0-screen-spaced.svg', {'ink': [(q, w, a) for q, w, a, _ in plain]},
                    'Porticus: ink by screen spacing', cam)
    held = base_ink(tone, hatch_st, struct_st, share=mould.paper_share(V))
    layers, alone, cstats = mould.compose(held, V)
    mould.write_svg(OUT / 'P1-mould-in-shadow.svg', layers, 'Porticus: the mould in the shadow', cam)
    mould.write_svg(OUT / 'P2-mould-alone.svg', alone, 'Porticus: the mould alone', cam)
    cstats['ink_near_mould'] = mould.local_ink(OUT / 'P0-screen-spaced.png', OUT / 'P1-mould-in-shadow.png', V, cam)
    stats['plate'] = cstats
    (OUT / 'stats.json').write_text(json.dumps(stats, indent=1))
    (OUT / 'veins.pkl').write_bytes(pickle.dumps(dict(lines=V['lines'], strains=V['strains'])))
    import diagnostics
    diagnostics.who_holds_the_shade(S.SURFACES, results, cam, visible, SITES_A, SITES_B, OUT / 'shade-map.png', lift=0.004, lines_png=OUT / 'P2-mould-alone.png')
    stats['scene'] = diagnostics.scene_totals(results)
    (OUT / 'stats.json').write_text(json.dumps(stats, indent=1))
    print(json.dumps(cstats), flush=True)


if __name__ == '__main__':
    main()
