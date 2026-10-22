#!/usr/bin/env python3
"""Scan portraits: a CC head scan drawn as a ray-lit engraving for the pen plotter.

    python portrait.py --subject washington --view bust
    python portrait.py --subject lps --view bust
    python portrait.py --subject washington --view front --pen-mm .1

The engine is Scanned Statue v2's, set for a head that fills the sheet:
  1. load and weld the scan, and Loop-subdivide it (once for Washington,
     twice for Lee Perry-Smith);
  2. light every vertex: a soft key, an open fill, ambient occlusion;
  3. candidate strokes: three families of plane sections set against the
     camera (one to hatch, two mirror-image cross-hatch candidates),
     interpolated contours (n.v = 0), suggestive contours, and ridge and
     valley lines;
  4. visibility of every stroke sample by a ray to the eye;
  5. tone: a section stays on where the light asks for ink, in a nested
     64-step order, so darker passages fill in between lighter ones; past a
     threshold, part of the tone goes to whichever cross family crosses the
     first at the wider angle on paper;
  6. a ruled ground behind the head, held off it by a halo, and a vignette;
  7. the drawing centred on the sheet and written as millimetre SVG, one
     Inkscape/AxiDraw layer per stroke class, each layer ordered to shorten
     pen-up travel and clipped to the sheet's plotting extent.

Hatch candidates are spaced in pen widths on paper, so a finer pen or a larger
plate gets proportionally more lines. Nothing here is fitted to one picture:
the subject sets the scan, rig and tone; the view sets the camera.
"""
import argparse
import hashlib
import inspect
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numba import njit
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent
STATUE = ROOT.parent / 'scanned-statue-v2'
if str(STATUE) not in sys.path:
    sys.path.append(str(STATUE))
import raycore      # noqa: E402  Scanned Statue v2, unchanged: BVH and ray queries
import meshlines    # noqa: E402  Scanned Statue v2, unchanged: level sets chained by edge
import suggestive   # noqa: E402  Scanned Statue v2, unchanged: suggestive contours
import creases      # noqa: E402
import light        # noqa: E402
import ground       # noqa: E402
import stipple      # noqa: E402
import subjects     # noqa: E402

INK = '#161918'      # Codex ink (common/plot/plotkit.py INK)
PAPER = '#ede6d4'    # Codex paper (common/plot/plate.py PAPER), previews only
SHEETS = {
    # Codex plot master: common/plot/plate.py, W, H = 210, 297 and its 8-202 x 10-288 mm check.
    'a4': dict(size=(210., 297.), extent=(8., 10., 202., 288.), label='Codex plot master, A4'),
    # The book's 7 x 10 in trim (binding/bind.py), 6 mm clear of the trim on every side.
    'codex': dict(size=(177.8, 254.), extent=(6., 6., 171.8, 248.), label='Codex 7 x 10 in page'),
}
# Section planes are set against the camera: (right, up, toward the viewer) components of each
# family's normal. Planes nearly edge-on to the eye (Scanned Statue v2's, which suit a full figure
# seen from afar) section a head into almost straight lines; tilting them makes each section bow
# over the form, the engraver's cross-contour. The main family leans away from the viewer, so its
# sections are tangent to the head out of sight: tilted toward the viewer, they ring a bald crown
# like contour lines on a hilltop. Families two and three are mirror-image cross-hatch candidates;
# at each point the drawing uses whichever crosses the first family at the wider angle on paper
# (see crossing()), because no single family of planes crosses it well everywhere: near a
# silhouette every section runs nearly parallel to the edge.
FAMILIES = ((.18, 1., -.45), (1., .75, .40), (-1., .75, .40))
LAYERS = (('ground', '1 ground'), ('hatch', '2 hatch'), ('cross', '3 cross-hatch'), ('dots', '4 stipple'),
          ('folds', '5 fold lines'), ('outlines', '6 outlines'))
REL = dict(hatch=1.0, cross=.9, dots=1.0, folds=1.0, outlines=1.25, ground=.9)   # stroke width, in pens


def log(*a):
    print(*a, flush=True)


def rank_of(k, bits=6):
    """Bit-reversed position of section k in a 64-step nested order."""
    n = 1 << bits
    return int(f'{k % n:0{bits}b}'[::-1], 2) / n + .5 / n


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ camera
class Camera:
    """Perspective camera whose image plane is the sheet, in millimetres.

    `scale` is millimetres on paper per scene unit at the look-at point, so a
    head of a given height is drawn at a given size whatever the distance."""

    def __init__(self, eye, target, scale, center):
        self.eye = np.asarray(eye, float); self.target = np.asarray(target, float)
        F = self.target - self.eye; self.dist = np.linalg.norm(F); self.F = F / self.dist
        R = np.cross(self.F, [0., 0., 1.]); self.R = R / np.linalg.norm(R)
        self.U = np.cross(self.R, self.F)
        self.focal = scale * self.dist; self.cx, self.cy = center

    def project(self, p):
        q = np.asarray(p) - self.eye; z = q @ self.F
        return np.stack([self.cx + self.focal * (q @ self.R) / z, self.cy - self.focal * (q @ self.U) / z, z], -1)

    def mm_per_unit(self, p):
        return self.focal / ((np.asarray(p) - self.eye) @ self.F)

    def jacobian(self, p):
        q = p - self.eye; z = q @ self.F
        jx = self.focal * (self.R[None, :] / z[:, None] - (q @ self.R)[:, None] * self.F[None, :] / z[:, None] ** 2)
        jy = -self.focal * (self.U[None, :] / z[:, None] - (q @ self.U)[:, None] * self.F[None, :] / z[:, None] ** 2)
        return jx, jy

    def rays(self, x, y):
        d = self.F[None, :] + ((x - self.cx) / self.focal)[:, None] * self.R[None, :] \
            - ((y - self.cy) / self.focal)[:, None] * self.U[None, :]
        return d / np.linalg.norm(d, axis=1)[:, None]


def make_camera(subject, view, sheet):
    head = np.asarray(subject.head, float) + np.asarray(view.get('offset', (0, 0, 0)), float)
    eye = head + light.direction(view['azimuth'], view['elevation']) * view['distance']
    x0, y0, x1, y1 = sheet['extent']
    center = (x0 + (x1 - x0) * view['center'][0], y0 + (y1 - y0) * view['center'][1])
    scale = view['head_mm'] / subject.head_height
    return Camera(eye, head, scale, center)


# -------------------------------------------------------------- mesh helpers
def vertex_normals(V, F, smooth=0):
    """Area-weighted vertex normals, optionally averaged over 1-rings `smooth` times."""
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1)[:, None], 1e-15)
    if smooth:
        import scipy.sparse as sp
        ed = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        A = sp.coo_matrix((np.ones(len(ed)), (ed[:, 0], ed[:, 1])), shape=(len(V), len(V))).tocsr()
        A = ((A + A.T) > 0).astype(float)
        for _ in range(smooth):
            vn = vn + A @ vn
            vn /= np.maximum(np.linalg.norm(vn, axis=1)[:, None], 1e-15)
    return vn


class EdgeUV:
    """UV at a point on a welded edge, read from a triangle that owns the edge,
    so an edge on a texture seam takes one side's coordinates, not a blend of both."""

    def __init__(self, scan):
        F = scan.F.astype(np.int64); Fu = scan.Fu.astype(np.int64); self.n = len(scan.V); self.UV = scan.UV
        a = F; b = np.roll(F, -1, axis=1); au = Fu; bu = np.roll(Fu, -1, axis=1)
        key = (np.minimum(a, b) * self.n + np.maximum(a, b)).ravel()
        order = np.argsort(key, kind='stable')
        self.keys = key[order]
        self.lo = np.where(a <= b, au, bu).ravel()[order]
        self.hi = np.where(a <= b, bu, au).ravel()[order]

    def __call__(self, ea, eb, t):
        k = np.minimum(ea, eb) * self.n + np.maximum(ea, eb)
        i = np.searchsorted(self.keys, k)
        ulo = self.UV[self.lo[i]]; uhi = self.UV[self.hi[i]]
        s = np.where(ea <= eb, t, 1 - t)
        return ulo + s[:, None] * (uhi - ulo)


class MeshView:
    """The two attributes suggestive.suggestive_contours reads."""

    def __init__(self, V, F):
        self.vertices, self.faces = V, F


# -------------------------------------------------------------------- light
def light_pass(scan, vn, bvh, rig, subject_head, cache_dir, lift):
    """Key, fill and occlusion per vertex, cached by geometry, rig and kernel source."""
    key_dir = light.direction(rig['key_azimuth'], rig['key_elevation'])
    fill_dir = light.direction(rig['fill_azimuth'], rig['fill_elevation'])
    head = np.asarray(subject_head, float)
    pts = light.area_samples(head, key_dir, rig['key_distance'], rig['key_size'], rig['key_samples'])
    ao = light.hemisphere(rig['ao_samples'])
    h = hashlib.sha256()
    for arr in (scan.V, scan.F, pts, fill_dir, ao, np.array([rig['ao_radius'], lift])):
        h.update(np.ascontiguousarray(arr).tobytes())
    h.update(inspect.getsource(light.shade.py_func).encode())
    path = cache_dir / f'light-{h.hexdigest()[:16]}.npy'
    if path.exists():
        return np.load(path)
    log(f'  lighting {len(scan.V)} vertices ({len(pts)} key samples, {len(ao)} occlusion rays)')
    t = time.time()
    terms = light.shade(scan.V, vn, pts, head + key_dir * rig['key_distance'], fill_dir, ao, rig['ao_radius'],
                        lift, *bvh[:3], *bvh[3:6])
    log('  light seconds', round(time.time() - t, 1))
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(path, terms)
    return terms


# ------------------------------------------------------------------ strokes
def family_normals(cam, spec):
    out = []
    for a, b, c in spec:
        n = a * cam.R + b * cam.U - c * cam.F
        out.append(n / np.linalg.norm(n))
    return out


def section_strokes(scan, vn, vlight, albedo_at, step, sample, eye, normals):
    V, F = scan.V, scan.F; NV = len(V)
    out = []
    for family, normal in enumerate(normals):
        dots = V @ normal; fd = dots[F]; fmin = fd.min(1); fmax = fd.max(1)
        order = np.argsort(fmin); fmin_sorted = fmin[order]
        offsets = np.arange(math.floor(dots.min() / step) * step, dots.max(), step)
        for k, off in enumerate(offsets):
            idx = order[:np.searchsorted(fmin_sorted, off, 'right')]
            idx = idx[fmax[idx] >= off]
            if len(idx) == 0:
                continue
            res = meshlines.level_set(F[idx], dots - off, NV)
            if res is None:
                continue
            ea, eb, t, chains = res
            P = V[ea] + t[:, None] * (V[eb] - V[ea])
            N = vn[ea] + t[:, None] * (vn[eb] - vn[ea])
            S = vlight[ea] + t * (vlight[eb] - vlight[ea])
            A = albedo_at(ea, eb, t)
            facing = ((eye - P) * N).sum(1) > 0
            for c in chains:
                if len(c) < 2 or not facing[c].any():
                    continue
                r = meshlines.resample(P[c], [N[c], S[c], A[c]], sample)
                if r is None:
                    continue
                q, (nn, ss, aa) = r
                nn /= np.maximum(np.linalg.norm(nn, axis=1)[:, None], 1e-12)
                out.append(dict(p=q, n=nn, light=ss, albedo=aa, family=family, rank=rank_of(k),
                                normal=normal, step=step, kind='hatch'))
        log(f'  section family {family}: {len(offsets)} planes, {len(out)} curves so far')
    return out


def contour_strokes(scan, eye, sample, smooth):
    V, F = scan.V, scan.F
    vn = vertex_normals(V, F, smooth)
    view = eye - V; view /= np.linalg.norm(view, axis=1)[:, None]
    ea, eb, t, chains = meshlines.level_set(F, (vn * view).sum(1), len(V))
    P = V[ea] + t[:, None] * (V[eb] - V[ea])
    N = vn[ea] + t[:, None] * (vn[eb] - vn[ea]); N /= np.linalg.norm(N, axis=1)[:, None]
    out = []
    for c in chains:
        r = meshlines.resample(P[c], [N[c]], sample)
        if r is not None:
            out.append(dict(p=r[0], n=r[1][0], kind='outline'))
    log(f'  outlines: {len(out)} chains from {len(P)} edge crossings')
    return out


def fold_strokes(scan, eye, sample, smooth, threshold):
    vn = vertex_normals(scan.V, scan.F, smooth)
    chains, info = suggestive.suggestive_contours(MeshView(scan.V, scan.F), eye, vn, threshold)
    out = []
    for P, N, ok, strength in chains:
        if len(P) < 2:
            continue
        r = meshlines.resample(P, [N, ok], sample)
        if r is not None:
            out.append(dict(p=r[0], n=r[1][0], ok=r[1][1] > .5, kind='fold'))
    log(f'  fold lines: {len(out)} chains')
    return out, info


def crease_strokes(scan, sample, smooth, head_height, valley, ridge, tensor_smooth, vlight):
    vn = vertex_normals(scan.V, scan.F, smooth)
    out = []; info = {}
    for kind, threshold in (('valley', valley), ('ridge', ridge)):
        if not threshold:
            continue
        chains, info[kind] = creases.crease_lines(scan.V, scan.F, vn, kind, threshold, head_height, tensor_smooth,
                                                  vlight)
        for P, N, K, L in chains:
            r = meshlines.resample(P, [N, K, L], sample)
            if r is not None:
                out.append(dict(p=r[0], n=r[1][0], strength=r[1][1] / threshold, light=r[1][2], kind='crease'))
    log(f'  ridge and valley lines: {len(out)} chains')
    return out, info


def projected_spacing(cam, p, n, normal, step):
    """Paper distance between adjacent sections (Scanned Statue v2's perspective Jacobian)."""
    jx, jy = cam.jacobian(p)
    grad = normal[None, :] - n * (n @ normal)[:, None]; g = np.linalg.norm(grad, axis=1)
    across = grad / np.maximum(g[:, None], 1e-8); tangent = np.cross(n, across)
    tx = (jx * tangent).sum(1); ty = (jy * tangent).sum(1)
    ax = (jx * across).sum(1); ay = (jy * across).sum(1)
    return step / np.maximum(g, 1e-8) * np.abs(tx * ay - ty * ax) / np.maximum(np.hypot(tx, ty), 1e-8)


# --------------------------------------------------------------- visibility
def visibility(cands, cam, bvh, lift):
    pts = np.concatenate([c['p'] for c in cands]); offs = np.zeros_like(pts)
    start = 0
    for c in cands:
        k = len(c['p']); sl = slice(start, start + k); start += k
        to_eye = cam.eye - c['p']; to_eye /= np.linalg.norm(to_eye, axis=1)[:, None]
        if c['kind'] in ('outline', 'crease'):
            offs[sl] = c['n'] * np.sign((c['n'] * to_eye).sum(1) + 1e-9)[:, None] * 2 * lift
        else:
            offs[sl] = c['n'] * np.sign((c['n'] * to_eye).sum(1))[:, None] * lift
    log(f'  visibility rays: {len(pts)}')
    vis = raycore.visible_from(pts, offs, cam.eye, *bvh[:3], *bvh[3:6])
    pp = cam.project(pts)
    return vis & (pp[:, 2] > 0), pp


# --------------------------------------------------------------------- draw
def runs(mask):
    ch = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return np.flatnonzero(ch == 1), np.flatnonzero(ch == -1)


def clean(keep, xy, gap, minimum):
    """Close gaps shorter than `gap` mm between kept runs; drop runs shorter than `minimum` mm."""
    keep = keep.copy()
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    a, b = runs(keep)
    for i in range(len(a) - 1):
        if seg[a[i + 1]] - seg[b[i] - 1] <= gap:
            keep[b[i]:a[i + 1]] = True
    a, b = runs(keep)
    for s, t in zip(a, b):
        if seg[t - 1] - seg[s] < minimum:
            keep[s:t] = False
    return keep


@njit(cache=True)
def _rdp_mask(xy, eps):
    n = len(xy); keep = np.zeros(n, np.bool_); keep[0] = True; keep[n - 1] = True
    stack = np.empty((n, 2), np.int64); sp = 1; stack[0, 0] = 0; stack[0, 1] = n - 1
    while sp > 0:
        sp -= 1; i0 = stack[sp, 0]; i1 = stack[sp, 1]
        ax, ay = xy[i0, 0], xy[i0, 1]; bx, by = xy[i1, 0], xy[i1, 1]
        dx, dy = bx - ax, by - ay; L = math.sqrt(dx * dx + dy * dy)
        best = -1.0; bi = -1
        for i in range(i0 + 1, i1):
            px, py = xy[i, 0] - ax, xy[i, 1] - ay
            d = abs(px * dy - py * dx) / L if L > 1e-12 else math.sqrt(px * px + py * py)
            if d > best:
                best = d; bi = i
        if bi >= 0 and best > eps:
            keep[bi] = True
            stack[sp, 0] = i0; stack[sp, 1] = bi; sp += 1
            stack[sp, 0] = bi; stack[sp, 1] = i1; sp += 1
    return keep


def rdp(xy, eps):
    xy = np.ascontiguousarray(xy, float)
    return xy if len(xy) < 3 else xy[_rdp_mask(xy, eps)]


def fade_at(xy, fade):
    """Oval vignette on the sheet: 1 inside, 0 outside, soft over `fade['soft']` of the radius."""
    if not fade:
        return np.ones(len(xy))
    cx, cy, rx, ry = fade['cx'], fade['cy'], fade['rx'], fade['ry']
    r = np.hypot((xy[:, 0] - cx) / rx, np.maximum(xy[:, 1] - cy, 0) / ry if fade.get('below_only') else (xy[:, 1] - cy) / ry)
    return 1 - smoothstep(1 - fade['soft'], 1, r)


def image_direction(cam, p, t):
    """Unit paper direction of 3D tangents t at points p, and the length before normalising."""
    jx, jy = cam.jacobian(p)
    d = np.stack([(jx * t).sum(1), (jy * t).sum(1)], 1)
    L = np.linalg.norm(d, axis=1)
    return d / np.maximum(L, 1e-12)[:, None], L


def crossing(cam, p, n, normals, min_deg, full_deg):
    """How well each cross family crosses the first family at these surface points.

    A section's tangent is n x N for plane normal N. Returns q (points x families),
    0 where the family's lines would run within min_deg of the first family's on paper
    or where its planes are nearly tangent to the surface, 1 beyond full_deg, and the
    index of the better cross family at each point."""
    d0, _ = image_direction(cam, p, np.cross(n, normals[0]))
    q = np.zeros((len(p), len(normals)))
    lo, hi = math.sin(math.radians(min_deg)), math.sin(math.radians(full_deg))
    for k in range(1, len(normals)):
        t = np.cross(n, normals[k]); tl = np.linalg.norm(t, axis=1)
        dk, _ = image_direction(cam, p, t)
        sin = np.abs(d0[:, 0] * dk[:, 1] - d0[:, 1] * dk[:, 0])
        q[:, k] = smoothstep(lo, hi, sin) * smoothstep(.2, .4, tl)
    best = 1 + np.argmax(q[:, 1:], axis=1)
    return q, best


def darkness(light_, albedo, tone):
    """Darkness d in [0, 1] after the paper threshold, and the ink coverage it asks for (before any fade)."""
    lit = np.clip(light_ * np.power(np.clip(albedo, .05, 2), tone['albedo_gamma']), 0, 1)
    d = 1 - np.power(lit, tone['light_gamma'])
    d = np.clip((d - tone['paper']) / (1 - tone['paper']), 0, 1)     # the lights stay paper
    return d, tone['scale'] * np.power(d, tone['gamma'])


def draw(cands, vis, pp, cam, pen, tone, fade, normals):
    paths = {k: [] for k, _ in LAYERS}
    start = 0
    for c in cands:
        k = len(c['p']); sl = slice(start, start + k); start += k
        xy = pp[sl, :2]; keep = vis[sl].copy(); kind = c['kind']
        f = fade_at(xy, fade)
        if kind == 'hatch':
            d, desired = darkness(c['light'], c['albedo'], tone)
            desired = desired * f * (1 - stipple.dot_share(d, tone))       # the lights' share goes to dots
            spacing = projected_spacing(cam, c['p'], c['n'], c['normal'], c['step'])   # mm on paper
            split = tone['cross'] * np.clip((d - tone['cross_from']) / tone['cross_ramp'], 0, 1)
            nn = c['n'] * np.sign((c['n'] * (cam.eye - c['p'])).sum(1))[:, None]
            q, best = crossing(cam, c['p'], nn, normals, tone['cross_min_deg'], tone['cross_full_deg'])
            if c['family'] == 0:
                coverage = desired * (1 - split * q[:, 1:].max(1))        # no good crossing: the first family carries it
            else:
                coverage = desired * split * q[:, c['family']] * (best == c['family'])
            prob = np.clip(coverage * spacing / pen, 0, 1)
            if k > 4:
                prob = gaussian_filter1d(prob, tone['smooth_samples'], mode='nearest')
            keep &= prob > c['rank']
            keep = clean(keep, xy, .8 * pen, 3 * pen)
            layer = 'hatch' if c['family'] == 0 else 'cross'
        elif kind == 'outline':
            keep &= f > .5
            keep = clean(keep, xy, 2.5 * pen, 5 * pen)
            layer = 'outlines'
        elif kind == 'fold':
            keep &= c['ok'] & (f > .5)
            keep = clean(keep, xy, 1.5 * pen, tone['fold_min_pens'] * pen)
            layer = 'folds'
        else:
            keep &= f > .5
            # A crease is drawn where it is strong, or where the form around it is in shade; a mild
            # crease across a lit plane would read as a crack, which an engraver models with tone.
            keep &= (c['strength'] > tone['crease_strong']) | (c['light'] < tone['crease_light'])
            keep = clean(keep, xy, 1.5 * pen, tone['crease_min_pens'] * pen)
            layer = 'folds'
        for a, b in zip(*runs(keep)):
            if b - a < 2:
                continue
            if f[a:b].mean() < .98:
                # In the vignette, short pieces read as noise: the fainter the place, the longer a piece must be.
                if np.linalg.norm(np.diff(xy[a:b], axis=0), axis=1).sum() < pen * (3 + 40 * (1 - f[a:b].mean())):
                    continue
            seg = xy[a:b]
            if kind != 'hatch' and b - a > 4:
                seg = gaussian_filter1d(seg, 1.0, axis=0, mode='nearest')   # ease scan noise out of feature lines
            q = rdp(seg, .15 * pen)
            if np.linalg.norm(np.diff(q, axis=0), axis=1).sum() >= 2 * pen:
                paths[layer].append(q)
    return paths


# ---------------------------------------------------------------- the sheet
def clip_to(paths, extent):
    """Split paths at the plotting extent, keeping only what is inside."""
    x0, y0, x1, y1 = extent
    out = []
    for p in paths:
        inside = (p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
        if inside.all():
            out.append(p); continue
        for a, b in zip(*runs(inside)):
            if b - a >= 2:
                out.append(p[a:b])
    return out


def place(paths, sheet, mode, optical=.46):
    """Offset that centres the drawing on the sheet: its bounding box centred across, and its
    middle at `optical` of the plotting extent's height (a little above centre, as a print is hung).
    'camera' keeps the camera's own placement."""
    if mode == 'camera':
        return np.zeros(2)
    pts = np.concatenate([p for k in paths for p in paths[k]])
    lo, hi = pts.min(0), pts.max(0)
    x0, y0, x1, y1 = sheet['extent']
    return np.array([(x0 + x1) / 2 - (lo[0] + hi[0]) / 2, y0 + optical * (y1 - y0) - (lo[1] + hi[1]) / 2])


def order_paths(paths, start=(0., 0.)):
    """Greedy nearest end-point order, reversing paths where that is shorter."""
    if len(paths) < 2:
        return list(paths)
    n = len(paths)
    ends = np.array([p[0] for p in paths] + [p[-1] for p in paths])
    alive = np.ones(n, bool); remaining = n
    ids = np.arange(2 * n); tree = cKDTree(ends); out = []; cur = np.asarray(start, float)
    while remaining:
        found = None
        for k in (8, 64):
            d, j = tree.query(cur, k=min(k, len(ids)))
            for jj in np.atleast_1d(j):
                if jj < len(ids) and alive[ids[jj] % n]:
                    found = ids[jj]; break
            if found is not None:
                break
        if found is None:
            ids = np.flatnonzero(np.r_[alive, alive]); tree = cKDTree(ends[ids])
            continue
        i = found % n; alive[i] = False; remaining -= 1
        p = paths[i][::-1] if found >= n else paths[i]
        out.append(p); cur = p[-1]
    return out


def travel(paths, start=(0., 0.)):
    t = 0.; cur = np.asarray(start, float)
    for p in paths:
        t += np.linalg.norm(p[0] - cur); cur = p[-1]
    return t


def length(paths):
    return sum(float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) for p in paths)


def svg_text(paths, sheet, pen, title, desc):
    w, h = sheet['size']
    fmt = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{fmt(w)}mm" height="{fmt(h)}mm" viewBox="0 0 {fmt(w)} {fmt(h)}">',
             f'<title>{title}</title><desc>{desc}</desc>']
    for key, label in LAYERS:
        if not paths[key]:
            continue
        parts.append(f'<g id="{key}" inkscape:groupmode="layer" inkscape:label="{label}" fill="none" stroke="{INK}" '
                     f'stroke-width="{fmt(pen * REL[key])}" stroke-linecap="round" stroke-linejoin="round">')
        for p in paths[key]:
            parts.append('<path d="M' + ' L'.join(f'{fmt(x)},{fmt(y)}' for x, y in p) + '"/>')
        parts.append('</g>')
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def write_png(svg, path, sheet, px_per_mm=6):
    import cairosvg
    w, h = sheet['size']
    tinted = svg.replace('<title>', f'<rect width="100%" height="100%" fill="{PAPER}"/><title>', 1)
    cairosvg.svg2png(bytestring=tinted.encode(), write_to=str(path), output_width=int(w * px_per_mm),
                     output_height=int(h * px_per_mm))


# --------------------------------------------------------------------- main
def run(subject_key, view_key, sheet_key='a4', pen_mm=.15, spacing=1.75, out=None, prefix=None, overrides=None,
        png=True):
    t0 = time.time()
    subject = subjects.SUBJECTS[subject_key]
    view = dict(subject.views[view_key]); rig = dict(subject.light); tone = dict(subjects.TONE)
    tone.update(subject.tone)
    rig.update({k: v for k, v in view.items() if k in rig})      # a view may move the key and fill
    for k, v in (overrides or {}).items():      # a light or tone key goes to its rig; anything else is a view key
        (rig if k in rig else tone if k in tone else view)[k] = v
    sheet = SHEETS[sheet_key]
    out = Path(out or ROOT / 'output'); out.mkdir(parents=True, exist_ok=True)
    name = prefix or f'{subject_key}-{view_key}'
    log(f'{subject.title}: view {view_key}, {sheet["label"]}, pen {pen_mm} mm, candidates {spacing} pens apart')

    scan = subjects.load(subject_key)
    log(f'  scan: {scan.source_triangles} source triangles, {len(scan.F)} drawn, {len(scan.V)} vertices')
    cam = make_camera(subject, view, sheet)
    edges = np.linalg.norm(scan.V[scan.F[:, 1]] - scan.V[scan.F[:, 0]], axis=1)
    lift = .25 * float(np.median(edges))
    bvh = raycore.build_bvh(scan.V[scan.F], np.zeros(len(scan.F), int))
    vn = vertex_normals(scan.V, scan.F, view.get('light_smooth', 0))
    terms = light_pass(scan, vn, bvh, rig, subject.head, out / 'cache', lift)
    vlight = light.combine(terms, rig)

    mm = cam.mm_per_unit(cam.target)
    step = spacing * pen_mm / mm
    sample = max(.7 * spacing * pen_mm, .25) / mm
    if scan.albedo is not None:
        uv_at = EdgeUV(scan)
        albedo_at = lambda ea, eb, t: subjects.sample_albedo(scan.albedo, uv_at(ea, eb, t))
    else:
        albedo_at = lambda ea, eb, t: np.ones(len(ea))
    log(f'  {mm:.1f} mm per scene unit at the head; sections {step:.5f} units apart')
    normals = family_normals(cam, view.get('families', FAMILIES))
    cands = section_strokes(scan, vn, vlight, albedo_at, step, sample, cam.eye, normals)
    cands += contour_strokes(scan, cam.eye, sample, view.get('outline_smooth', 0))
    folds, fold_info = fold_strokes(scan, cam.eye, sample, view.get('fold_smooth', 2), tone['fold_threshold'])
    cands += folds
    lines, crease_info = crease_strokes(scan, sample, view.get('crease_normal_smooth', 2), subject.head_height,
                                        tone['valley_threshold'], tone['ridge_threshold'], tone['crease_smooth'],
                                        vlight)
    cands += lines
    vis, pp = visibility(cands, cam, bvh, lift)

    fade = dict(subject.fade); fade.update(view.get('fade', {}))
    x0, y0, x1, y1 = sheet['extent']
    head_xy = cam.project(cam.target)
    fade = dict(cx=head_xy[0] + fade['dx'], cy=head_xy[1] + fade['dy'], rx=fade['rx'] * view['head_mm'],
                ry=fade['ry'] * view['head_mm'], soft=fade['soft'], below_only=fade.get('below_only', False))
    paths = draw(cands, vis, pp, cam, pen_mm, tone, fade, normals)
    dot_info = dict(dots=0)
    if tone['dots'] > 0:
        seen = pp[vis, :2]
        region = (*(seen.min(0) - 1), *(seen.max(0) + 1))
        head = [p for k in ('hatch', 'cross', 'folds', 'outlines') for p in paths[k]]
        albedo_uv = (lambda uv: subjects.sample_albedo(scan.albedo, uv)) if scan.albedo is not None else None
        pts, dot_info = stipple.dots(cam, bvh, scan, vlight, albedo_uv, head, region, lambda xy: fade_at(xy, fade),
                                     lambda L, a: darkness(L, a, tone), pen_mm, tone, f'{subject_key}-{view_key}-{sheet_key}')
        paths['dots'] = [stipple.ring(x, y, tone['dot_ring_mm']) for x, y in pts]
        log(f"  stipple: {dot_info['dots']} dots ({dot_info['asked']} asked for)")

    gspec = dict(subject.ground); gspec.update(view.get('ground', {}))
    if gspec.get('dark_side', 'auto') == 'auto':
        # The ground is darkest behind the lit side of the head, so the lit edge carries against it.
        key_dir = light.direction(rig['key_azimuth'], rig['key_elevation'])
        gspec['dark_side'] = -1. if key_dir @ cam.R < 0 else 1.
    paths['ground'], ground_info = ground.ruled(cam, bvh, sheet, pen_mm * REL['ground'], head_xy, view['head_mm'],
                                                gspec, fade)
    shift = place(paths, sheet, view.get('place', 'auto'))
    for k in paths:
        paths[k] = order_paths(clip_to([p + shift for p in paths[k]], sheet['extent']), start=(x0, y0))
    desc = (f'{subject.credit} Stroke-only plot: view {view_key}, pen {pen_mm} mm, '
            f'sheet {sheet["label"]}. Layers: ' + ', '.join(label for _, label in LAYERS) + '.')
    svg = svg_text(paths, sheet, pen_mm, f'{subject.title}: scan portrait ({view_key})', desc)
    (out / f'{name}.svg').write_text(svg)
    if png:
        write_png(svg, out / f'{name}.png', sheet)

    allp = [p for k in paths for p in paths[k]]
    down = sum(length(paths[k]) for k in paths)
    up = sum(travel(paths[k], (x0, y0)) for k in paths)
    pts = np.concatenate(allp) if allp else np.zeros((0, 2))
    report = dict(
        version='scan-portraits-1', subject=subject_key, view=view_key, sheet=sheet_key, pen_mm=pen_mm,
        spacing_pen_widths=spacing, candidate_spacing_mm=spacing * pen_mm, credit=subject.credit,
        licence=subject.licence, source_triangles=scan.source_triangles, drawn_triangles=int(len(scan.F)),
        loop_subdivisions=scan.subdivisions, eye=[round(float(v), 6) for v in cam.eye],
        section_normals=[[round(float(v), 6) for v in n] for n in normals],
        head_mm=view['head_mm'], view_settings=view, light=rig, tone=tone,
        paths_by_layer={k: len(paths[k]) for k in paths},
        line_m_by_layer={k: round(length(paths[k]) / 1000, 2) for k in paths},
        pen_down_m=round(down / 1000, 2), pen_up_m=round(up / 1000, 2),
        plot_hours_at_25mm_s=round((down / 25 + up / 50 + .25 * len(allp)) / 3600, 2),
        extent_mm=sheet['extent'], placement_shift_mm=[round(float(v), 3) for v in shift],
        head_xy_mm=[round(float(v), 3) for v in (head_xy[:2] + shift)],
        bounds_mm=[round(float(v), 3) for v in (pts.min(0).tolist() + pts.max(0).tolist())] if len(pts) else None,
        fold_info={k: (v if not isinstance(v, tuple) else list(v)) for k, v in fold_info.items()},
        ground=ground_info, creases=crease_info, stipple=dot_info,
    )
    (out / f'{name}-report.json').write_text(json.dumps(report, indent=1, default=float) + '\n')
    log(f'  {sum(len(v) for v in paths.values())} paths, {down / 1000:.1f} m pen down, {up / 1000:.1f} m travel; '
        f'{time.time() - t0:.0f} s')
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--subject', choices=sorted(subjects.SUBJECTS), default='washington')
    ap.add_argument('--view', default='bust')
    ap.add_argument('--sheet', choices=sorted(SHEETS), default='a4')
    ap.add_argument('--pen-mm', type=float, default=.15, help='pen line width in mm')
    ap.add_argument('--spacing', type=float, default=1.75, help='closest hatch spacing, in pen widths')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='override a view, light or tone setting, e.g. --set key_azimuth=-60 --set gamma=1.1')
    ap.add_argument('--prefix', default=None); ap.add_argument('--out', default=None)
    ap.add_argument('--no-png', action='store_true')
    a = ap.parse_args()
    overrides = {}
    for kv in a.set:
        k, v = kv.split('=', 1)
        try:
            overrides[k] = json.loads(v)
        except json.JSONDecodeError:
            try:
                overrides[k] = float(v)      # .85 as well as 0.85
            except ValueError:
                overrides[k] = v
    run(a.subject, a.view, a.sheet, a.pen_mm, a.spacing, a.out, a.prefix, overrides, not a.no_png)


if __name__ == '__main__':
    main()
