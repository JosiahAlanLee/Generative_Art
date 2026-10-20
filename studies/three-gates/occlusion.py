"""Claude's parallel-plane meadow compositor, reused for this scene.
Adaptation: perspective camera rays and local scale; optional owner-depth audit.
Original implementation: Receiving_Works_Meadow.zip, supplied 20 October 2026.
"""
import json, subprocess, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import minimum_filter, binary_dilation

import build as B

ROOT, OUT, W, H = B.ROOT, B.OUT, B.W, B.H
ZUP = np.array([0., 0., 1.])
NORMAL = B.unit(B.FWD - (B.FWD @ ZUP) * ZUP)  # common normal of the plant planes, pointing away from the camera
K = 2                                          # buffer supersampling
SAMPLE_PX = 0.9                                # stroke sampling for the occlusion tests
EPS_PLANT, EPS_MODEL = 1e-6, 0.02
HALO_PX = 1.8                                  # smallest halo a plant stroke cuts into what lies behind it


def noise2(seed, freq):
    """Smooth value noise in [-1, 1] over world x, y."""
    g = np.random.default_rng(seed).uniform(-1, 1, (96, 96))

    def f(x, y):
        u, v = (np.asarray(x) + 60) * freq, (np.asarray(y) + 60) * freq
        i, j = np.floor(u).astype(int), np.floor(v).astype(int)
        a, b = u - i, v - j
        a, b = a * a * (3 - 2 * a), b * b * (3 - 2 * b)
        i, j = i % 95, j % 95
        return (g[j, i] * (1 - a) + g[j, i + 1] * a) * (1 - b) + (g[j + 1, i] * (1 - a) + g[j + 1, i + 1] * a) * b
    return f


class Instance:
    """One patch placed on a view-facing plane: local (x, y) -> root + (x-ox) s RIGHT + (oy-y) s Z."""

    def __init__(self, patch, origin, root, s, width):
        self.patch, self.root, self.s, self.width = patch, np.asarray(root, float), float(s), width
        self.ox, self.oy = origin
        self.c = float(self.root @ NORMAL)

    def world(self, pts):
        pts = np.asarray(pts, float).reshape(-1, 2)
        return self.root + (pts[:, 0:1] - self.ox) * self.s * B.RIGHT + (self.oy - pts[:, 1:2]) * self.s * ZUP

    def screen(self, pts):
        x, y, _ = B.project(self.world(pts))
        return np.column_stack([x, y])


def stamp(buf, inst):
    """Rasterise one instance's recorded occluders into the min-c buffer."""
    px_per = inst.s * float(B.pixels_per_world(inst.root)) * K
    shapes = []
    for op in inst.patch['occluders']:
        if op['t'] == 'rings':
            for ring in op['rings']:
                if len(ring) >= 6:
                    shapes.append(('poly', inst.screen(ring) * K, 0))
        elif op['t'] == 'stamp':
            shapes.append(('line', inst.screen(op['pts']) * K, max(op['w'] * px_per, HALO_PX * K)))
        elif op['t'] == 'var':
            pts, ws = inst.screen(op['pts']) * K, np.asarray(op['ws']) * px_per
            for q in range(len(pts) - 1):
                shapes.append(('line', pts[q:q + 2], max(HALO_PX * K, (ws[q] + ws[q + 1]) / 2)))
        elif op['t'] == 'disc':
            shapes.append(('disc', inst.screen([[op['cx'], op['cy']]]) * K, op['r'] * px_per))
    if not shapes:
        return
    allp = np.vstack([s[1] for s in shapes])
    pad = 2 + max(s[2] for s in shapes)
    x0, y0 = np.floor(allp.min(0) - pad).astype(int)
    x1, y1 = np.ceil(allp.max(0) + pad).astype(int)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W * K, x1), min(H * K, y1)
    if x1 <= x0 or y1 <= y0:
        return
    im = Image.new('L', (x1 - x0, y1 - y0), 0)
    d = ImageDraw.Draw(im)
    off = np.array([x0, y0])
    for kind, p, w in shapes:
        q = [tuple(v) for v in (p - off)]
        if kind == 'poly':
            d.polygon(q, fill=255)
        elif kind == 'line':
            wi = max(1, int(round(w)))
            if len(q) > 1:
                d.line(q, fill=255, width=wi, joint='curve')
            for v in (q[0], q[-1]):
                d.ellipse([v[0] - w / 2, v[1] - w / 2, v[0] + w / 2, v[1] + w / 2], fill=255)
        else:
            v = q[0]
            d.ellipse([v[0] - w, v[1] - w, v[0] + w, v[1] + w], fill=255)
    m = np.asarray(im) > 0
    view = buf[y0:y1, x0:x1]
    np.minimum(view, np.where(m, inst.c, np.inf), out=view)


def resample(xy, step):
    """Points every `step` px along a screen polyline."""
    xy = np.asarray(xy, float)
    seg = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    if L[-1] <= 0:
        return xy[:1]
    t = np.linspace(0, L[-1], max(2, int(L[-1] / step) + 1))
    return np.column_stack([np.interp(t, L, xy[:, 0]), np.interp(t, L, xy[:, 1])])


def lookup(buf, xy):
    i = np.clip((xy[:, 0] * K).astype(int), 0, W * K - 1)
    j = np.clip((xy[:, 1] * K).astype(int), 0, H * K - 1)
    return buf[j, i]


def runs(xy, keep, min_len=1.5):
    ids = np.flatnonzero(keep)
    if not len(ids):
        return []
    out = []
    for g in np.split(ids, np.flatnonzero(np.diff(ids) != 1) + 1):
        if len(g) > 1:
            q = xy[g]
            if np.linalg.norm(np.diff(q, axis=0), axis=1).sum() > min_len:
                out.append(q)
    return out


def model_depth(buf):
    """First-hit c (= P . n) of the model at every covered buffer pixel, min-filtered so edges stay in front."""
    covered = binary_dilation(np.isfinite(buf), iterations=3)
    jj, ii = np.nonzero(covered)
    sx, sy = (ii + 0.5) / K, (jj + 0.5) / K
    origins,dirs = B.primary_rays(np.column_stack([sx,sy]))
    dist, hit = B.rc.first_hits(origins, dirs, 150., *B.BVH[:6])
    D = np.full(buf.shape, np.inf)
    ok = hit >= 0
    P = origins[ok] + dirs[ok] * dist[ok, None]
    D[jj[ok], ii[ok]] = P @ NORMAL
    return minimum_filter(D, size=5)


def plant_strokes(instances, buf, return_audit=False):
    """Each instance's strokes, sampled, ray-tested against the model and depth-tested against plants."""
    pens = [[], [], [], []]
    pts, owner = [], []
    for k, inst in enumerate(instances):
        step_local = SAMPLE_PX / (inst.s * float(B.pixels_per_world(inst.root)))
        for s in inst.patch['strokes']:
            a = np.asarray(s['pts'], float).reshape(-1, 2)
            if len(a) < 2:
                continue
            seg = np.linalg.norm(np.diff(a, axis=0), axis=1)
            L = np.concatenate([[0], np.cumsum(seg)])
            t = np.linspace(0, L[-1], max(2, int(L[-1] / step_local) + 1))
            dense = np.column_stack([np.interp(t, L, a[:, 0]), np.interp(t, L, a[:, 1])])
            pts.append(dense)
            owner.append((k, s['pen']))
    sizes = np.array([len(p) for p in pts])
    world = np.vstack([instances[k].world(p) for (k, _), p in zip(owner, pts)])
    seen = B.visible(world, *B.BVH[:6])
    x, y, depth = B.project(world)
    xy = np.column_stack([x, y])
    c = np.repeat([instances[k].c for k, _ in owner], sizes)
    keep = seen & (depth > B.NEAR) & (lookup(buf, xy) >= c - EPS_PLANT) & (x > 4) & (x < W - 4) & (y > 4) & (y < H - 4)
    start = 0
    for (k, pen), n in zip(owner, sizes):
        sl = slice(start, start + n)
        pens[pen].extend((q, instances[k].width) for q in runs(xy[sl], keep[sl]))
        start += n
    if return_audit:
        return pens, {'xy': xy, 'owner_depth': c, 'survives': keep, 'model_visible': seen}
    return pens


def clip_screen_paths(paths, buf, D):
    """Model or field strokes, kept where no plant is nearer than the model surface at that pixel."""
    out = []
    for q, w in paths:
        xy = resample(q, SAMPLE_PX)
        keep = ~(lookup(buf, xy) < lookup(D, xy) - EPS_MODEL)
        out.extend((r, w) for r in runs(xy, keep))
    return out
