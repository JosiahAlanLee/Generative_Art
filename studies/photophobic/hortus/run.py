#!/usr/bin/env python3
"""Hortus Intervallorum: the photophobic mould in Sol's garden.

Sol's scene, mesh and drawing (render_garden_sol.py) are imported unchanged. The
garden has no light pass of its own: its hatching shades each face by Lambert
against a sun vector, and three hand-placed fans stand in for cast shadows. The
mould needs real shadow, so this adds one: Sol's own sun vector, ray-traced against
his mesh (soft sun, contact occlusion, one bounce, in the form of the hallway and
Memento models). The fans are replaced by a cast-shadow hatch drawn from that
pass, so the shadow the mould lives in is in the ink.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault('NUMBA_NUM_THREADS', '4')
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'common')]

import numpy as np
from numba import njit, prange

import render_garden_sol as gs                         # Sol's file, unchanged
import atlas
import bvh as B
import mould
from camera import Camera

OUT = HERE / 'output'
CELL = 0.025                # ~1.5-3 px per cell at the garden's distances: its shadows are small
SEED = 3031
CUT_KINDS = ('hatch', 'stone', 'grass', 'leaf', 'cast shadow')
ALBEDO = {'stone': .70, 'earth': .50, 'soil': .40, 'leaf': .30, 'bark': .30, 'black': .05, 'distant': .60}
SUN_STRENGTH = 0.6          # lit ground prints near Sol's paper; the exposure form is the other scenes'

# Inoculation sites, placed in traced shadow.
SITES_A = [('left wall, near', (-9.4, 0.5, 0.6), 4.5),
           ('behind the cypresses', (-5.0, 10.5, 0.5), 3.0),
           ("fountain's shadow", (-0.9, 1.4, 0.0), 2.0)]
SITES_B = [("tree's shadow", (8.6, 2.0, 0.0), 3.5),
           ("stair's shadow", (3.5, 8.8, 0.0), 2.2),
           ('left wall, far', (-9.4, 8.5, 0.6), 3.5)]
BITS = 8
BITREV = np.array([int(f'{i:0{BITS}b}'[::-1], 2) for i in range(1 << BITS)]) / (1 << BITS)


@njit(cache=True)
def _cone(d, u, v):
    """A unit direction tilted from d by small offsets (u, v) in d's tangent plane."""
    a = np.array([0., 0., 1.])
    if abs(d[2]) > .9:
        a = np.array([1., 0., 0.])
    t = np.cross(a, d)
    t /= np.sqrt(np.dot(t, t))
    b = np.cross(d, t)
    out = d + u * t + v * b
    return out / np.sqrt(np.dot(out, out))


@njit(cache=True)
def _hemi(n, u, v):
    a = np.array([0., 0., 1.])
    if abs(n[2]) > .9:
        a = np.array([1., 0., 0.])
    t = np.cross(a, n)
    t /= np.sqrt(np.dot(t, t))
    b = np.cross(n, t)
    rr = math.sqrt(u)
    th = 2 * math.pi * v
    return rr * math.cos(th) * t + rr * math.sin(th) * b + math.sqrt(1 - u) * n


@njit(cache=True)
def _sun(p, n, sun, offsets, strength, blo, bhi, nodes, tris):
    c = np.dot(n, sun)
    if c <= 0:
        return 0.
    seen = 0.
    for j in range(offsets.shape[0]):
        d = _cone(sun, offsets[j, 0], offsets[j, 1])
        _, h = B.cast(p + n * .01, d, 200., blo, bhi, nodes, tris)
        if h < 0:
            seen += 1.
    return strength * c * seen / offsets.shape[0]


@njit(cache=True, parallel=True)
def _light_points(P, Nrm, alb, sun, offsets, strength, hemis, ao_dist, blo, bhi, nodes, tris, tri_albedo, normals):
    n = P.shape[0]
    out = np.zeros((n, 5))
    for i in prange(n):
        p = P[i]
        nn = Nrm[i]
        flat = strength * max(0., np.dot(nn, sun))
        dl = _sun(p, nn, sun, offsets, strength, blo, bhi, nodes, tris)
        ao = 0.
        bounce = 0.
        for j in range(hemis.shape[0]):
            hdir = _hemi(nn, hemis[j, 0], hemis[j, 1])
            dd, hh = B.cast(p + nn * .01, hdir, ao_dist, blo, bhi, nodes, tris)
            if hh >= 0:
                ao += 1 - dd / ao_dist
            dd, hh = B.cast(p + nn * .01, hdir, 40., blo, bhi, nodes, tris)
            if hh >= 0:
                q = p + nn * .01 + hdir * dd
                n2 = normals[hh].copy()
                if np.dot(n2, hdir) > 0:
                    n2 = -n2
                bounce += _sun(q, n2, sun, offsets[:1], strength, blo, bhi, nodes, tris) * tri_albedo[hh] / hemis.shape[0]
        ao /= hemis.shape[0]
        out[i, 0] = dl
        out[i, 1] = flat
        out[i, 2] = ao
        out[i, 3] = bounce
        out[i, 4] = min(1., max(0., .14 * (1 - .70 * ao) + (dl + .70 * bounce) * alb * 2.4))
    return out


class Scene:
    def __init__(self):
        t = time.time()
        gs.scene()
        self.zbuf = gs.depth_map()
        gs.hatch_faces()
        n_before = len(gs.LINES)
        # Sol's three projected shadow fans (render_garden.render), labelled so they can be swapped out.
        for x, y, r, z in [(-2.3, .25, 1.8, 1.5), (6.9, -.7, 1.4, 4.5), (-7.5, 5.8, .6, 4)]:
            dx, dy = -gs.LIGHT[0] * z / gs.LIGHT[2], -gs.LIGHT[1] * z / gs.LIGHT[2]
            for j in np.arange(-r, r, .075):
                half = np.sqrt(max(0, r * r - j * j))
                gs.line([[x + j, y - .1, .03], [x + j + dx, y + half + dy, .03]], .62, 'shadow', .72)
        self.n_fans = len(gs.LINES) - n_before
        self.cam = Camera(gs.EYE, gs.FORWARD, gs.RIGHT, gs.UP, gs.FOCAL, gs.W / 2, gs.H * .53, gs.W, gs.H)
        tris, alb = [], []
        for f in gs.FACES:
            for i in range(1, len(f.p) - 1):
                tt = f.p[[0, i, i + 1]]
                if np.linalg.norm(np.cross(tt[1] - tt[0], tt[2] - tt[0])) > 1e-10:
                    tris.append(tt)
                    alb.append(ALBEDO.get(f.mat, .5))
        self.blo, self.bhi, self.nodes, self.tris, order, self.normals = B.build(np.array(tris))
        self.tri_albedo = np.array(alb)[order]
        self.sun = gs.LIGHT / np.linalg.norm(gs.LIGHT)
        k = math.radians(0.75)
        self.offsets = np.array([[0., 0.], [-k, -k], [-k, k], [k, -k], [k, k]])[1:]
        self.hemis = np.column_stack([(np.arange(16) + .5) / 16, ((np.arange(16) * .61803398875) % 1)])
        self.surfaces = self._surfaces()
        print(f'garden scene ready in {time.time() - t:.0f}s ({len(self.tris)} triangles)', flush=True)

    def light_fn(self, P, N, alb):
        ch = _light_points(P, N, float(alb), self.sun, self.offsets, SUN_STRENGTH, self.hemis, 1.5,
                           self.blo, self.bhi, self.nodes, self.tris, self.tri_albedo, self.normals)
        traced = ch[:, 4]
        return dict(direct=ch[:, 0], flat=ch[:, 1], ao=ch[:, 2], bounce=ch[:, 3], traced=traced,
                    darkness=1 - np.sqrt(traced), excess=mould.excess_from(ch[:, 0], ch[:, 3], alb))

    def visible(self, pts, skip=0.03):
        return B.visibility(np.ascontiguousarray(pts), self.cam.eye, skip, self.blo, self.bhi, self.nodes, self.tris)

    def _surfaces(self):
        beds = [(x0, x1, y0, y1) for x0, x1 in [(-8.8, -4.0), (4.9, 8.7)] for y0, y1 in [(3., 6.), (7.0, 9.4)]]
        fx, fy = -2.3, .25

        def ground_domain(u, v):
            ok = ~((u > -.4) & (u < 3.2) & (v > 5.1))                     # under the stair
            ok &= (u - fx) ** 2 + (v - fy) ** 2 > 2.1 ** 2                  # under the fountain base
            for x0, x1, y0, y1 in beds:
                ok &= ~((u > x0) & (u < x1) & (v > y0) & (v < y1))
            return ok

        def wall_domain(u, v):
            return ~((u > -.9) & (u < 3.7) & (v < 5.8))                     # doorway, reveals, stair

        surfaces = [
            atlas.Plane('ground', -9.4, 10.0, -7.0, 10.5, (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), CELL,
                        ground_domain, albedo=ALBEDO['earth']),
            atlas.Plane('rear wall', -10.0, 10.0, 0.0, 6.25, (0, 10.5, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0), CELL,
                        wall_domain, albedo=ALBEDO['stone']),
            atlas.Plane('left wall', -5.0, 10.5, 0.0, 2.0, (-9.4, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0), CELL,
                        albedo=ALBEDO['stone']),
        ]
        for k, (x0, x1, y0, y1) in enumerate(beds):
            surfaces.append(atlas.Plane(f'bed {k + 1}', x0 + .25, x1 - .25, y0 + .25, y1 - .25, (0, 0, .12),
                                        (1, 0, 0), (0, 1, 0), (0, 0, 1), CELL, albedo=ALBEDO['soil']))
        return surfaces

    # ------------------------------------------------------------------
    def sol_marks(self):
        """Sol's paths, depth-tested and simplified exactly as render_garden.render does,
        each labelled with its kind. Returns [(polyline, width, opacity, kind)] and the
        paper-fill underlay."""
        marks = []
        for p, width, kind, alpha in gs.LINES:
            for run in gs.visible_paths(p, self.zbuf):
                q = gs.simplify(run)
                if len(q) < 2:
                    continue
                marks.append((np.array(q, float), width, alpha, kind))
        body = []
        for f in sorted(gs.FACES, key=lambda f: float(gs.proj(f.p)[:, 2].mean()), reverse=True):
            q = gs.proj(f.p)
            pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y, z in q)
            fill = gs.INK if f.mat == 'black' else 'white'
            body.append(f'<polygon points="{pts}" fill="{fill}" stroke="none"/>')
        return marks, ''.join(body)


def cast_shadow_hatch(sc, s, L, angle, delta=0.012, width=0.62, c_max=0.22, min_px=2.5, share=None):
    """Hatching for the traced cast shadow on one plane, in the plane's own coordinates,
    thinned by screen spacing (nested bit-reversed ranks, as in the corridor) so the
    printed density follows the shade, not the distance. With `share` (a screen map of
    the paper the white line reserves) each point asks for coverage / (1 - share)."""
    from scipy.ndimage import map_coordinates
    shade = np.clip(1 - L['excess'], 0, 1) * (L['excess'] < 0.6)

    def target(u, v):
        t = c_max * map_coordinates(shade, [s.uv_cell(u, v)[1], s.uv_cell(u, v)[0]], order=1, mode='nearest')
        if share is not None:
            sx, sy, _ = sc.cam.project(s.world(u, v))
            f = map_coordinates(share, [sy, sx], order=1, mode='nearest')
            t = t / (1 - f)
        return t
    dv = np.array([math.cos(angle), math.sin(angle)])
    nv = np.array([-dv[1], dv[0]])
    corners = np.array([[s.u0, s.v0], [s.u1, s.v0], [s.u1, s.v1], [s.u0, s.v1]])
    offs = corners @ nv
    out = []
    for k in range(math.floor(offs.min() / delta), math.ceil(offs.max() / delta) + 1):
        r = BITREV[k % (1 << BITS)]
        o = k * delta
        lo, hi = -1e9, 1e9
        for axis, (a0, a1) in enumerate(((s.u0, s.u1), (s.v0, s.v1))):
            if abs(dv[axis]) < 1e-12:
                if not (a0 <= o * nv[axis] <= a1):
                    lo, hi = 1, 0
                continue
            ta, tb = (a0 - o * nv[axis]) / dv[axis], (a1 - o * nv[axis]) / dv[axis]
            lo, hi = max(lo, min(ta, tb)), min(hi, max(ta, tb))
        if hi - lo < 0.05:
            continue
        uvf = lambda t: o * nv[None] + np.asarray(t)[:, None] * dv[None]
        tc = np.linspace(lo, hi, max(3, int((hi - lo) / 0.15) + 1))
        q = uvf(tc)
        P = s.world(q[:, 0], q[:, 1])
        eu, ev = s.frame(q[:, 0], q[:, 1])
        sp = mould_spacing(sc.cam, P, eu, ev, angle, delta)
        if r >= np.max(np.minimum(1, target(q[:, 0], q[:, 1]) * sp / width)):
            continue
        tf = mould.resample_screen(sc.cam, lambda t: (lambda qq: s.world(qq[:, 0], qq[:, 1]))(uvf(t)), lo, hi, len(tc))
        q = uvf(tf)
        P = s.world(q[:, 0], q[:, 1])
        eu, ev = s.frame(q[:, 0], q[:, 1])
        sp = mould_spacing(sc.cam, P, eu, ev, angle, delta)
        keep = (r < np.minimum(1, target(q[:, 0], q[:, 1]) * sp / width)) & s.domain(q[:, 0], q[:, 1])
        sx, sy, z = sc.cam.project(P)
        keep &= sc.cam.inside(sx, sy, z)
        if keep.sum() < 2:
            continue
        idx = np.flatnonzero(keep)
        vis = sc.visible(P[idx] + s.normal(q[idx, 0], q[idx, 1]) * .01)
        keep[idx[~vis]] = False
        d = np.diff(np.r_[0, keep.astype(np.int8), 0])
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            pts = np.stack([sx[a:b], sy[a:b]], 1)
            if len(pts) >= 2 and np.hypot(*np.diff(pts, axis=0).T).sum() >= min_px:
                out.append((np.array(mould.rdp(pts, .18)), width, .72, 'cast shadow'))
    return out


def mould_spacing(cam, P, eu, ev, angle, delta):
    J = cam.jacobian(P, eu, ev)
    nu, nv = -math.sin(angle), math.cos(angle)
    det = J[..., 0, 0] * J[..., 1, 1] - J[..., 0, 1] * J[..., 1, 0]
    gx = (J[..., 1, 1] * nu - J[..., 1, 0] * nv) / det
    gy = (-J[..., 0, 1] * nu + J[..., 0, 0] * nv) / det
    return delta / np.maximum(np.hypot(gx, gy), 1e-9)


def sol_body(marks):
    return ''.join('<path d="M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in q) + f'" stroke-width="{w:.2f}" opacity="{a:.2f}"/>'
                   for q, w, a, _ in marks)


SHADOW_ANGLE = {'ground': math.atan2(.5, .6), 'rear wall': math.radians(62)}


def main():
    OUT.mkdir(exist_ok=True)
    sc = Scene()
    t = time.time()
    marks, underlay = sc.sol_marks()
    sol = (HERE / 'inputs' / '01-garden-engraved.svg').read_text()
    same = sol_body(marks) in sol and underlay in sol
    print(f'Sol marks: {len(marks)}, {time.time() - t:.0f}s; identical to Sol: {same}', flush=True)
    light, results, stats = {}, {}, {}
    for s in sc.surfaces:
        t = time.time()
        L = mould.surface_light(s, sc.light_fn)
        light[s.name] = L
        r = mould.run_strains(s, L, SITES_A, SITES_B, SEED + len(results), params=dict(mould.PARAMS, density=0.25))
        results[s.name] = r
        moved, in_light = mould.contest(r)
        stats[s.name] = dict(grid=[s.nu, s.nv], lit_share=float((L['excess'][r['domain']] > .5).mean()),
                             changed_strain=moved, trail_on_lit_ground=in_light)
        print(f'{s.name}: grid {s.nu}x{s.nv}, lit {100 * stats[s.name]["lit_share"]:.1f}%, '
              f'changed strain {100 * moved:.1f}%, trail on lit ground {100 * in_light:.2f}%, {time.time() - t:.0f}s',
              flush=True)
    np.savez_compressed(OUT / 'mould.npz', **{f'{k}__{c}': v for k, r in results.items() for c, v in r.items()},
                        **{f'{k}__light_{c}': v for k, L in light.items() for c, v in L.items()})
    colony = mould.colony_strokes(sc.surfaces, results, sc.cam)
    vis = np.zeros(len(colony.world), bool)
    alive = colony.attr['alive'].astype(bool) & sc.cam.inside(colony.xy[:, 0], colony.xy[:, 1], colony.z)
    vis[alive] = sc.visible(colony.world[alive])
    V = mould.veins(colony, vis, sc.cam, cap=0.16)
    share = mould.paper_share(V)

    def shade_hatch(share=None):
        out = []
        for s in sc.surfaces:
            if s.name != 'left wall':                # Sol already shades that self-shadowed face
                out += cast_shadow_hatch(sc, s, light[s.name], SHADOW_ANGLE.get(s.name, math.atan2(.5, .6)), share=share)
        return out

    sol_kept = [m for m in marks if m[3] != 'shadow']
    plain = [(q, w, a, kind in CUT_KINDS) for q, w, a, kind in sol_kept + shade_hatch()]
    mould.write_svg(OUT / 'H0-traced-shade.svg', {'ink': [(q, w, a) for q, w, a, _ in plain]},
                    'Hortus: traced cast shadow in place of the fans', sc.cam, underlay=underlay)
    shadow = shade_hatch(share)
    held = [(q, w, a, kind in CUT_KINDS) for q, w, a, kind in sol_kept + shadow]
    layers, alone, cstats = mould.compose(held, V)
    mould.write_svg(OUT / 'H1-mould-in-shadow.svg', layers, 'Hortus: the mould in the shadow', sc.cam, underlay=underlay)
    mould.write_svg(OUT / 'H2-mould-alone.svg', alone, 'Hortus: the mould alone', sc.cam, underlay=underlay)
    cstats['ink_near_mould'] = mould.local_ink(OUT / 'H0-traced-shade.png', OUT / 'H1-mould-in-shadow.png', V, sc.cam)
    stats['plate'] = dict(cstats, sol_fans_removed=sum(m[3] == 'shadow' for m in marks), cast_shadow_marks=len(shadow))
    import pickle
    (OUT / 'veins.pkl').write_bytes(pickle.dumps(dict(lines=V['lines'], strains=V['strains'])))
    import diagnostics
    diagnostics.who_holds_the_shade(sc.surfaces, results, sc.cam, sc.visible, SITES_A, SITES_B, OUT / 'shade-map.png', lift=0.02, lines_png=OUT / 'H2-mould-alone.png')
    stats['scene'] = diagnostics.scene_totals(results)

    stats['base_identical_to_sol'] = same
    (OUT / 'stats.json').write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats['plate']), flush=True)
    print(json.dumps(stats['scene']), flush=True)


if __name__ == '__main__' and '--check' not in sys.argv:
    main()

if __name__ == '__main__' and '--check' in sys.argv:
    sc = Scene()
    t = time.time()
    marks, underlay = sc.sol_marks()
    sol = (HERE / 'inputs' / '01-garden-engraved.svg').read_text()
    print(f'{len(marks)} marks in {time.time() - t:.0f}s; identical to Sol: {sol_body(marks) in sol and underlay in sol}')
    import pickle
    (OUT / 'sol_marks.pkl').write_bytes(pickle.dumps((marks, underlay)))
