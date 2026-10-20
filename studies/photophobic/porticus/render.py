"""Ink for the corridor: every stroke lives on a surface; how many survive is set on screen.

Tone target per point = f(darkness).  Strokes are added in a fixed order:
structure (always) -> colonies (strongest veins first) -> hatching (nested rank
order, primary family then crossing), each taking only what the screen-space
budget still allows. Because the hatch families are nested (bit-reversed rank),
keeping ranks below phi leaves evenly spaced lines at spacing delta/phi, so the
printed density follows the light instead of the perspective.
"""
from __future__ import annotations

import os

os.environ.setdefault('NUMBA_NUM_THREADS', '4')   # hallway_sol calls set_num_threads(4)

import math
import sys
import time
from pathlib import Path

import numpy as np
from numba import njit, prange
from scipy.ndimage import gaussian_filter, map_coordinates
from skimage.filters import gaussian

import surfaces as S          # first: sets NUMBA_NUM_THREADS before numba loads
import physarum_plot as pp
import cultures as C

hs = S.hs
OUT = Path(__file__).resolve().parent / 'output'
W, H = S.W, S.H
INK, COLONY = '#29261f', '#8a3b22'
COLONY_WEIGHT = 0.7               # the colony pen is lighter than the ink: its share of darkness
C_MAX, GAMMA, C_SPLIT = 0.75, 1.6, 0.14
MIN_GAP = 2.0                     # px: hatch lines never closer than this on screen
FAMILIES = ((0.65, 0.065 / 12, 0.90), (-0.68, 0.095 / 12, 0.80))   # angle in (u, v), candidate spacing, width px
BREAK_KEEP = 0.795                 # share of a stroke the interruptions keep: sin(x) > -0.8
BITS = 8
BITREV = np.array([int(f'{i:0{BITS}b}'[::-1], 2) for i in range(1 << BITS)]) / (1 << BITS)


def coverage_target(d):
    return C_MAX * np.clip(d, 0, 1) ** GAMMA


# ----------------------------------------------------------------------------
# geometry helpers
# ----------------------------------------------------------------------------
def face_normal(p):
    n = np.cross(p[1] - p[0], p[-1] - p[0])
    return n / (np.linalg.norm(n) + 1e-12)


def classify_faces():
    """Each of Sol's faces -> which atlas surface it belongs to, or 'rib' / 'dressed' / 'skip'."""
    out = []
    ri_chord = S.VAULT_R * math.cos(S.DTH / 2)
    for f in hs.FACES:
        p, c = f.p, f.p.mean(0)
        n = face_normal(p)
        if f.mat == 3:
            k = 'skip'
        elif abs(c[2]) < 1e-9 and abs(n[2]) > .99 and abs(c[0]) < 1e-9 and np.ptp(p[:, 0]) > 5.8:
            k = 'floor'
        elif abs(c[0] + 2.6) < 1e-9 and abs(n[0]) > .99:
            k = 'wall_left'
        elif abs(c[0] - 2.6) < 1e-9 and abs(n[0]) > .99:
            k = 'wall_right'
        elif abs(c[1] - 21.7) < 1e-9 and abs(n[1]) > .99:
            k = 'rear_wall'
        elif c[2] > 3.6 and abs(math.hypot(c[0], c[2] - S.VAULT_Z) - ri_chord) < 2e-3 and np.ptp(p[:, 1]) > 20:
            k = 'vault'
        elif (abs(n[1]) > .99 and c[2] > 3.62 and 2.3 < math.hypot(c[0], c[2] - 3.6) < 2.65) or abs(c[0] + 2.53) < 1e-9:
            k = 'rib'                      # voussoir faces of the transverse arches and the side portal
        else:
            k = 'dressed'
        out.append(k)
    return out


@njit(cache=True, parallel=True)
def _primary(PW, PH, scale, blo, bhi, nodes, tris, eye, f, r, u, focal, cx, cy):
    hit = np.full((PH, PW), -1, np.int64)
    dist = np.zeros((PH, PW))
    for idx in prange(PW * PH):
        iy, ix = idx // PW, idx % PW
        px, py = (ix + .5) * scale, (iy + .5) * scale
        d = f + (px - cx) / focal * r - (py - cy) / focal * u
        d /= np.sqrt(np.dot(d, d))
        t, h = hs.cast(eye, d, 100., blo, bhi, nodes, tris)
        hit[iy, ix] = h
        dist[iy, ix] = t
    return hit, dist


def primary_raster(scale=2):
    PW, PH = W // scale, H // scale
    hit, dist = _primary(PW, PH, float(scale), S.BLO, S.BHI, S.NODES, S.TRIS, S.EYE, S.F, S.R, S.U,
                         S.FOCAL, S.CX, S.CY)
    iy, ix = np.mgrid[0:PH, 0:PW]
    px, py = (ix + .5) * scale, (iy + .5) * scale
    d = S.F + ((px - S.CX) / S.FOCAL)[..., None] * S.R - ((py - S.CY) / S.FOCAL)[..., None] * S.U
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return hit, S.EYE + d * dist[..., None], dist


def tri_faces():
    """Face index for each triangle in BVH order (Sol's build_bvh drops it)."""
    key = {}
    for k, f in enumerate(hs.FACES):
        for i in range(1, len(f.p) - 1):
            t = f.p[[0, i, i + 1]]
            if np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) > 1e-9:
                key[t.tobytes()] = k
    return np.array([key[t.tobytes()] for t in S.TRIS])


# ----------------------------------------------------------------------------
# stroke sets: points with per-stroke metadata
# ----------------------------------------------------------------------------
class Strokes:
    """Concatenated polylines. pts: screen xy; world: xyz; stroke id per point;
    per-point attrs live in dicts."""

    def __init__(self):
        self.world, self.sid, self.attr = [], [], {}
        self.meta = []
        self.n = 0

    def add(self, world, **attr):
        if len(world) < 2:
            return
        self.world.append(np.asarray(world, float))
        self.sid.append(np.full(len(world), len(self.meta)))
        for k, v in attr.items():
            self.attr.setdefault(k, []).append(np.broadcast_to(np.asarray(v), (len(world),) + np.shape(v)[1:])
                                              if np.ndim(v) else np.full(len(world), v))
        self.meta.append(len(world))

    def finish(self):
        self.world = np.concatenate(self.world) if self.world else np.zeros((0, 3))
        self.sid = np.concatenate(self.sid) if self.sid else np.zeros(0, int)
        self.attr = {k: np.concatenate(v) for k, v in self.attr.items()}
        sx, sy, z = S.project(self.world)
        self.xy = np.stack([sx, sy], 1)
        self.z = z
        return self


def resample_screen(world_fn, t0, t1, n_coarse, step_px=1.6, min_pts=2):
    """Sample a curve world_fn(t) at ~equal screen arc length."""
    t = np.linspace(t0, t1, n_coarse)
    P = world_fn(t)
    sx, sy, _ = S.project(P)
    seg = np.hypot(np.diff(sx), np.diff(sy))
    cum = np.r_[0, np.cumsum(seg)]
    n = max(min_pts, int(math.ceil(cum[-1] / step_px)) + 1)
    tf = np.interp(np.linspace(0, cum[-1], n), cum, t)
    return tf


def spacing_px(P, e_u, e_v, angle, delta):
    """Screen distance between neighbouring hatch lines of one family at points P."""
    J = S.screen_jacobian(P, e_u, e_v)
    nu, nv = -math.sin(angle), math.cos(angle)
    det = J[..., 0, 0] * J[..., 1, 1] - J[..., 0, 1] * J[..., 1, 0]
    gx = (J[..., 1, 1] * nu - J[..., 1, 0] * nv) / det
    gy = (-J[..., 0, 1] * nu + J[..., 0, 0] * nv) / det
    return delta / np.maximum(np.hypot(gx, gy), 1e-9)


def hatch_on_surface(st, s, c_cap):
    """Both families across one atlas surface, continuous over the whole surface."""
    corners = np.array([[s.u0, s.v0], [s.u1, s.v0], [s.u1, s.v1], [s.u0, s.v1]])
    for fam, (angle, delta, width) in enumerate(FAMILIES):
        dv = np.array([math.cos(angle), math.sin(angle)])
        nv = np.array([-dv[1], dv[0]])
        offs = corners @ nv
        ks = np.arange(math.floor(offs.min() / delta), math.ceil(offs.max() / delta) + 1)
        along = corners @ dv
        for k in ks:
            r = BITREV[k % (1 << BITS)]
            o = k * delta
            # clip the infinite line o*nv + t*dv to the rectangle
            lo, hi = along.min() - 1, along.max() + 1
            for axis, (a0, a1) in enumerate(((s.u0, s.u1), (s.v0, s.v1))):
                if abs(dv[axis]) < 1e-12:
                    if not (a0 <= o * nv[axis] <= a1):
                        lo, hi = 1, 0
                    continue
                ta, tb = (a0 - o * nv[axis]) / dv[axis], (a1 - o * nv[axis]) / dv[axis]
                lo, hi = max(lo, min(ta, tb)), min(hi, max(ta, tb))
            if hi - lo < 0.02:
                continue
            uvf = lambda t: o * nv[None] + np.asarray(t)[:, None] * dv[None]
            wf = lambda t: (lambda q: s.world(q[:, 0], q[:, 1]))(uvf(t))
            # cheap rejection: can this rank ever be needed on this line?
            tc = np.linspace(lo, hi, max(3, int((hi - lo) / 0.08) + 1))
            qc = uvf(tc)
            Pc = s.world(qc[:, 0], qc[:, 1])
            eu, ev = s.frame(qc[:, 0], qc[:, 1])
            sp = spacing_px(Pc, eu, ev, angle, delta)
            phi_max = np.minimum(1, c_cap * sp / width)
            if r >= phi_max.max():
                continue
            tf = resample_screen(wf, lo, hi, len(tc))
            q = uvf(tf)
            keep = s.domain(q[:, 0], q[:, 1])
            P = s.world(q[:, 0], q[:, 1])
            eu, ev = s.frame(q[:, 0], q[:, 1])
            sp = spacing_px(P, eu, ev, angle, delta)
            keep &= r < np.minimum(1, c_cap * sp / width)
            if keep.sum() < 2:
                continue
            spA, spB = (spacing_px(P, eu, ev, a_, d_) for a_, d_, _ in FAMILIES)
            P = P + s.normal(q[:, 0], q[:, 1]) * .006
            st.add(P, kind=0, fam=fam, rank=r, width=width, spA=spA, spB=spB, surf=S.SURFACES.index(s),
                   u=q[:, 0], v=q[:, 1], alive=keep)


def hatch_on_face(st, p, n, c_cap, face_id):
    """Sol-style per-face frame, both families, nested ranks; two-sided."""
    if np.dot(n, S.EYE - p.mean(0)) < 0:
        n = -n
    u = np.array([1., 0., 0.]) if (abs(n[2]) > .95 or abs(n[1]) > .95) else np.array([0., 1., 0.])
    u = u - n * np.dot(n, u)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    uv = np.column_stack([(p - p[0]) @ u, (p - p[0]) @ v])
    for fam, (angle, delta, width) in enumerate(FAMILIES):
        dv = np.array([math.cos(angle), math.sin(angle)])
        nv = np.array([-dv[1], dv[0]])
        vals = uv @ nv
        for k in range(math.floor(vals.min() / delta), math.ceil(vals.max() / delta) + 1):
            off = k * delta
            hits = []
            for a, b, va, vb in zip(uv, np.roll(uv, -1, 0), vals, np.roll(vals, -1)):
                if (va <= off < vb) or (vb <= off < va):
                    hits.append(a + (b - a) * (off - va) / (vb - va))
            if len(hits) < 2:
                continue
            hits = sorted(hits, key=lambda q: q @ dv)
            a, b = hits[0], hits[-1]
            if np.linalg.norm(b - a) < 0.01:
                continue
            r = BITREV[k % (1 << BITS)]
            wf = lambda t: p[0] + (a[None] + np.asarray(t)[:, None] * (b - a)[None]) @ np.stack([u, v])
            Pc = wf(np.linspace(0, 1, 3))
            sp = spacing_px(Pc, np.broadcast_to(u, Pc.shape), np.broadcast_to(v, Pc.shape), angle, delta)
            if r >= min(1, c_cap * sp.max() / width):
                continue
            tf = resample_screen(wf, 0., 1., 5)
            P = wf(tf)
            sp = spacing_px(P, np.broadcast_to(u, P.shape), np.broadcast_to(v, P.shape), angle, delta)
            keep = r < np.minimum(1, c_cap * sp / width)
            if keep.sum() < 2:
                continue
            uu_, vv_ = np.broadcast_to(u, P.shape), np.broadcast_to(v, P.shape)
            spA, spB = (spacing_px(P, uu_, vv_, a_, d_) for a_, d_, _ in FAMILIES)
            st.add(P + n * .006, kind=0, fam=fam, rank=r, width=width, spA=spA, spB=spB, surf=-1 - face_id,
                   u=np.zeros(len(P)), v=np.zeros(len(P)), alive=keep)


CURVED = ('arch', 'arch joints', 'portal', 'portal joints', 'rear arch')


def structure_strokes():
    """Sol's structural lines (tested with visible_lines(), not visible())."""
    st = Strokes()
    for p, width, kind in hs.LINES:
        pieces = []
        for a, b in zip(p, p[1:]):
            L = np.linalg.norm(b - a)
            pieces.append(a + np.linspace(0, 1, max(2, int(L / .02) + 1))[:, None] * (b - a))
        P = np.concatenate(pieces)
        st.add(P, width=width, alive=True, curved=kind in CURVED)
    return st.finish()


def transport_network(T, D, thr=0.12, min_spur=12.0, min_len=4.0, max_link=20.0):
    """The trail's skeleton as a graph. Each branch is weighted by how much of the
    colony lies downstream of it on the shortest-path tree from that piece's densest
    point (its inoculation site): Physarum tubes thicken with the flux through them
    (Tero et al. 2007, 2010), so trunks near the source come out heavy and the mesh
    at the front stays fine. Returns [(xy cells (col,row), flow, piece total)]."""
    import networkx as nx
    Tn = pp.norm_trail(np.asarray([T]))[0]
    Sk, df = pp._skeleton_paths(pp._drop_small(Tn > thr, 12))
    if Sk is None:
        return []
    Hh, Ww = Tn.shape
    G = nx.MultiGraph()
    pos, keep = {}, []
    for i in range(Sk.n_paths):
        bt, bl = int(df['branch_type'][i]), float(df['branch_distance'][i])
        if (bt == 1 and bl < min_spur) or bl < min_len:
            continue
        a, b = int(df['node_id_src'][i]), int(df['node_id_dst'][i])
        G.add_edge(a, b, key=i, w=bl)
        pos[a] = (df['image_coord_src_0'][i], df['image_coord_src_1'][i])
        pos[b] = (df['image_coord_dst_0'][i], df['image_coord_dst_1'][i])
        keep.append(i)
    dens = lambda n: D[int(np.clip(pos[n][0], 0, Hh - 1)), int(np.clip(pos[n][1], 0, Ww - 1))]
    flow = {}
    for comp in nx.connected_components(G):
        sub = G.subgraph(comp)
        total = sum(d['w'] for _, _, d in sub.edges(data=True))
        src = max(comp, key=dens)
        dist, paths = nx.single_source_dijkstra(sub, src, weight='w')
        parent = {n: q[-2] for n, q in paths.items() if len(q) > 1}
        acc = dict.fromkeys(comp, 0.0)
        tree = {}
        for n, par in parent.items():
            ks = sub[par][n]
            k = min(ks, key=lambda kk: ks[kk]['w'])
            tree[n] = (k, ks[k]['w'])
        for n in sorted(parent, key=lambda n: -dist[n]):
            acc[parent[n]] += acc[n] + tree[n][1]
        for n, (k, w) in tree.items():
            flow[k] = (acc[n] + w, total)
        for _, _, k, d in sub.edges(keys=True, data=True):
            if k not in flow and d['w'] <= max_link:      # loops: only short cross-links survive
                flow[k] = (d['w'], total)
    out = []
    for i in keep:
        if i not in flow:
            continue
        f, total = flow[i]
        rc = Sk.path_coordinates(i)
        out.append((pp._smooth(rc[:, ::-1].astype(float), 5), f, total))
    return out


def vein_level(f, total):
    """Number of extra strokes either side of a vein, from its flow (cells)."""
    lv = 0
    for j, (a, frac) in enumerate(((250, .03), (900, .12), (2500, .35)), 1):
        if f > max(a, frac * total):
            lv = j
    return lv


def colony_strokes(cult, lens_gap=1.05):
    """Both cultures on every surface -> world polylines. rank 0 = the heaviest vein,
    kept first when the colony is far away; lens strokes also need room on screen."""
    st = Strokes()
    for si, s in enumerate(S.SURFACES):
        D = cult[f'{s.name}__colony']
        for culture, key in ((0, 'light_trail'), (1, 'shadow_trail')):
            T = cult[f'{s.name}__{key}']
            if T.max() <= 0:
                continue
            net = transport_network(T, D)
            if not net:
                continue
            flows = np.array([f for _, f, _ in net])
            lens_ = np.array([max(_plen(c), 1e-6) for c, _, _ in net])
            order = np.argsort(-flows)
            cum = np.cumsum(lens_[order]) / lens_.sum()
            rank = np.empty(len(net))
            rank[order] = cum - lens_[order] / lens_.sum()
            for (c, f, total), r in zip(net, rank):
                lv = vein_level(f, total)
                n = len(c)
                strokes = [(c, 0)]
                if lv and n >= 8:
                    t = np.arange(n)
                    taper = np.clip(np.minimum(t, n - 1 - t) / 6.0, 0, 1)
                    taper = taper * taper * (3 - 2 * taper)
                    for j in range(1, lv + 1):
                        d = j * lens_gap * taper
                        strokes.append((np.vstack([pp._offset(c, d), pp._offset(c, -d)[::-1]]), j))
                for xy, j in strokes:
                    u, v = s.cell_uv(xy[:, 0], xy[:, 1])
                    m = len(u)
                    fu = lambda tt: np.interp(tt, np.arange(m), u)
                    fv = lambda tt: np.interp(tt, np.arange(m), v)
                    tf = resample_screen(lambda tt: s.world(fu(tt), fv(tt)), 0., m - 1., m)
                    uu, vv = fu(tf), fv(tf)
                    P = s.world(uu, vv)
                    eu, ev = s.frame(uu, vv)
                    J = S.screen_jacobian(P, eu, ev)
                    scale = np.sqrt(np.abs(J[..., 0, 0] * J[..., 1, 1] - J[..., 0, 1] * J[..., 1, 0]))
                    minpx = np.full(len(uu), 99.0) if j == 0 else j * lens_gap * S.CELL * scale
                    st.add(P + s.normal(uu, vv) * .004, rank=float(r), width=1.35 if j == 0 else 0.95, culture=culture,
                           level=j, minpx=minpx, surf=si, u=uu, v=vv, alive=s.domain(uu, vv))
    return st.finish()


def _plen(c):
    return float(np.hypot(*np.diff(c, axis=0).T).sum()) if len(c) > 1 else 0.0


# ----------------------------------------------------------------------------
# darkness per point
# ----------------------------------------------------------------------------
class Tone:
    """Darkness lookups: atlas surfaces from their own maps (true light or the
    colony-held light), dressed stone from Sol's bake through the camera."""

    def __init__(self, light, cult=None, held_light=False):
        data = hs.lighting(S.BVH)
        from scipy.ndimage import median_filter
        self.bake = 1 - np.sqrt(np.clip(median_filter(data[:, :, 1], size=3), 0, 1))
        self.maps = []
        for s in S.SURFACES:
            L = light[s.name]
            if held_light and cult is not None:
                held = cult[f'{s.name}__held']            # shadow culture's ground, 0..1
                lit = np.clip(1 - held, 0, 1)
                lit = lit * lit * (3 - 2 * lit)
                d = S.darkness_from(L, lit * L['flat'])
            else:
                d = L['darkness']
            self.maps.append(d.astype(np.float32))

    def at(self, st):
        d = np.empty(len(st.world))
        surf = st.attr['surf']
        for si, s in enumerate(S.SURFACES):
            m = surf == si
            if m.any():
                c, r = s.uv_cell(st.attr['u'][m], st.attr['v'][m])
                d[m] = map_coordinates(self.maps[si], [r, c], order=1, mode='nearest')
        m = surf < 0
        if m.any():
            gx = st.xy[m, 0] / W * self.bake.shape[1] - .5
            gy = st.xy[m, 1] / H * self.bake.shape[0] - .5
            d[m] = map_coordinates(self.bake, [gy, gx], order=1, mode='nearest')
        return d


# ----------------------------------------------------------------------------
# screen budget
# ----------------------------------------------------------------------------
GRID = 2                                   # coverage grid: 2 px cells


@njit(cache=True)
def _splat(xy, sid, keep, width, weight, out):
    Hc, Wc = out.shape
    for i in range(xy.shape[0] - 1):
        if sid[i] != sid[i + 1] or not keep[i] or not keep[i + 1]:
            continue
        L = math.hypot(xy[i + 1, 0] - xy[i, 0], xy[i + 1, 1] - xy[i, 1])
        cx = int(0.5 * (xy[i, 0] + xy[i + 1, 0]) / 2.0)
        cy = int(0.5 * (xy[i, 1] + xy[i + 1, 1]) / 2.0)
        if 0 <= cx < Wc and 0 <= cy < Hc:
            out[cy, cx] += L * width[i] * weight[i] / 4.0


def coverage_map(st, keep, weight):
    out = np.zeros((H // GRID, W // GRID))
    _splat(st.xy, st.sid, keep, st.attr['width'].astype(float), np.broadcast_to(weight, len(keep)).astype(float), out)
    return gaussian_filter(out, 3.0)


def sample(grid, xy):
    return map_coordinates(grid, [xy[:, 1] / GRID - .5, xy[:, 0] / GRID - .5], order=1, mode='nearest')


def runs(st, keep, min_px=2.5, tol=0.25):
    """Kept points -> polylines (split at gaps and stroke ends), RDP-simplified."""
    out, widths, idx = [], [], np.flatnonzero(keep)
    if not len(idx):
        return out, widths
    brk = np.flatnonzero((np.diff(idx) != 1) | (np.diff(st.sid[idx]) != 0)) + 1
    for g in np.split(idx, brk):
        if len(g) < 2:
            continue
        q = st.xy[g]
        if np.hypot(*np.diff(q, axis=0).T).sum() < min_px:
            continue
        out.append(hs.rdp(q, tol) if len(q) > 2 else list(q))
        widths.append(float(st.attr['width'][g[0]]))
    return out, widths


def halo(st, keep, xy, radius):
    """True where a point lies within `radius` px of a kept stroke (engravers leave
    paper around a line they want read)."""
    from PIL import Image, ImageDraw
    img = Image.new('1', (W, H), 0)
    dr = ImageDraw.Draw(img)
    for q, _ in zip(*runs(st, keep, min_px=0)):
        dr.line([tuple(map(float, a)) for a in q], fill=1, width=int(round(2 * radius)))
    m = np.asarray(img, bool)
    ix = np.clip(xy[:, 0].astype(int), 0, W - 1)
    iy = np.clip(xy[:, 1].astype(int), 0, H - 1)
    return m[iy, ix]


@njit(cache=True, parallel=True)
def _visible_skip(points, skip, blo, bhi, nodes, tris, eye):
    vis = np.zeros(points.shape[0], np.bool_)
    for i in prange(points.shape[0]):
        d = eye - points[i]
        dist = np.sqrt(np.dot(d, d))
        d /= dist
        if dist <= 2 * skip:
            vis[i] = True
            continue
        _, hit = hs.cast(points[i] + d * skip, d, dist - skip - .01, blo, bhi, nodes, tris)
        vis[i] = hit < 0
    return vis


def visible_lines(st, skip=0.05, skip_flat=0.008):
    """Visibility for Sol's structural lines. Several of them lie exactly on a surface
    (each arch's extrados is on the vault) or are true circles drawn over 25- and
    28-sided faceting (sagitta up to 0.0047), so a ray started at the point grazes the
    facet it belongs to and the line breaks into dashes. Occluders closer than `skip`
    along the ray are ignored for the arcs; real occluders here (ribs, piers, the
    bench) are further away than that. Straight lines only skip `skip_flat`."""
    inside = (st.z > .15) & (st.xy[:, 0] > 2) & (st.xy[:, 0] < W - 2) & (st.xy[:, 1] > 2) & (st.xy[:, 1] < H - 2)
    vis = np.zeros(len(st.world), bool)
    for m, sk in ((inside & st.attr['curved'], skip), (inside & ~st.attr['curved'], skip_flat)):
        vis[m] = _visible_skip(np.ascontiguousarray(st.world[m]), sk, S.BLO, S.BHI, S.NODES, S.TRIS, S.EYE)
    return vis


def visible(st):
    inside = (st.z > .15) & (st.xy[:, 0] > 2) & (st.xy[:, 0] < W - 2) & (st.xy[:, 1] > 2) & (st.xy[:, 1] < H - 2)
    todo = inside & st.attr['alive'].astype(bool)
    vis = np.zeros(len(st.world), bool)
    vis[todo] = hs.point_visibility(np.ascontiguousarray(st.world[todo]), S.BLO, S.BHI, S.NODES, S.TRIS)
    return vis


def interruptions(st, d):
    """Sparse breaks so the screen does not look mechanical (after Sol's)."""
    i = np.arange(len(st.sid))
    start = np.r_[0, np.flatnonzero(np.diff(st.sid)) + 1]
    first = np.repeat(start, np.diff(np.r_[start, len(st.sid)]))
    phase = (np.sin(st.sid * 12.9898) * 43758.5453) % 1 * 2 * math.pi
    return (np.sin((i - first) * 0.21 + phase) > -0.8) | (d > 0.72)   # keeps BREAK_KEEP of each stroke


# ----------------------------------------------------------------------------
# plates
# ----------------------------------------------------------------------------
def build_hatch(c_cap=C_MAX):
    t = time.time()
    st = Strokes()
    for s in S.SURFACES:
        hatch_on_surface(st, s, c_cap)
    classes = classify_faces()
    hit, _, _ = primary_raster(2)
    seen = set(np.unique(tri_faces()[hit[hit >= 0]]).tolist())
    for k, (f, cls) in enumerate(zip(hs.FACES, classes)):
        if cls == 'dressed' and k in seen:
            hatch_on_face(st, f.p, face_normal(f.p), c_cap, k)
    st.finish()
    print(f'hatch candidates: {len(st.meta)} lines, {len(st.world)} points, {time.time() - t:.0f}s', flush=True)
    return st


def allocate_hatch(st, d, used, vis):
    """Keep hatch points so each family supplies its share of the remaining tone."""
    target = np.maximum(0, coverage_target(d) - sample(used, st.xy))
    target = np.where(d > 0.72, target, target / BREAK_KEEP)      # the breaks remove ink; ask for that much more
    fam, rank = st.attr['fam'], st.attr['rank']
    wA, wB = FAMILIES[0][2], FAMILIES[1][2]
    fullA, fullB = wA / st.attr['spA'], wB / st.attr['spB']     # ink if every candidate line were kept
    cA = np.minimum(target, C_SPLIT) + 0.5 * np.maximum(0, target - C_SPLIT)
    capA = np.minimum(fullA, wA / MIN_GAP)
    phiA = np.minimum(1, np.minimum(cA, capA) / fullA)
    cB = target - phiA * fullA
    capB = np.minimum(fullB, wB / MIN_GAP)
    phiB = np.minimum(1, np.clip(cB, 0, None).clip(max=capB) / fullB)
    phi = np.where(fam == 0, phiA, phiB)
    return st.attr['alive'] & vis & (rank < phi) & interruptions(st, d)


def allocate_colony(st, vis, cap):
    """The colonies are things in the corridor, not tone: heaviest veins first, until
    the colony's own ink reaches `cap` coverage on screen. Lens strokes are dropped
    where they would sit closer than a pen width to their vein."""
    alive = st.attr['alive'] & vis & ((st.attr['level'] == 0) | (st.attr['minpx'] >= 1.1))
    full = coverage_map(st, alive, COLONY_WEIGHT)
    phi = np.minimum(1, cap / np.maximum(sample(full, st.xy), 1e-4))
    return alive & (st.attr['rank'] < phi)


def plate(name, tone, hatch_st, struct_st, colony_st=None, cap=0.10, hatch=True):
    t = time.time()
    layers = {}
    keep_s = struct_st.vis
    layers['ink'] = [runs(struct_st, keep_s, min_px=1.4)]
    used = coverage_map(struct_st, keep_s, 1.0)
    if colony_st is not None:
        keep_c = allocate_colony(colony_st, colony_st.vis, cap)
        layers['colony'] = [runs(colony_st, keep_c, min_px=3.0)]
        used = used + coverage_map(colony_st, keep_c, COLONY_WEIGHT)
    if hatch:
        d_h = tone.at(hatch_st)
        keep_h = allocate_hatch(hatch_st, d_h, used, hatch_st.vis)
        if colony_st is not None:
            keep_h &= ~halo(colony_st, keep_c, hatch_st.xy, 2.4)
        layers['ink'].append(runs(hatch_st, keep_h))
    n = {k: sum(len(r[0]) for r in v) for k, v in layers.items()}
    print(f'{name}: strokes {n}, {time.time() - t:.0f}s', flush=True)
    write_svg(OUT / f'{name}.svg', layers, name)
    return layers


def write_svg(path, layers, title):
    pens = {'ink': INK, 'colony': COLONY}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{W}" height="{H}" viewBox="0 0 {W} {H}"><title>Porticus: {title}</title>'
             f'<rect width="100%" height="100%" fill="white"/>']
    for li, (lname, groups) in enumerate(layers.items(), 1):
        parts.append(f'<g inkscape:groupmode="layer" inkscape:label="{li} {lname}" fill="none" stroke="{pens[lname]}" '
                     f'stroke-linecap="round" stroke-linejoin="round">')
        for lines, widths in groups:
            for q, w in zip(lines, widths):
                d = 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in q)
                parts.append(f'<path d="{d}" stroke-width="{w:.2f}"/>')
        parts.append('</g>')
    parts.append('</svg>')
    path.write_text(''.join(parts))
    import cairosvg
    cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix('.png')), output_width=W, output_height=H)


def main():
    light = C.load_light()
    cult = np.load(OUT / 'cultures.npz')
    struct_st = structure_strokes()
    struct_st.vis = visible_lines(struct_st)
    hatch_st = build_hatch()
    t = time.time()
    hatch_st.vis = visible(hatch_st)
    print(f'hatch visibility {time.time() - t:.0f}s', flush=True)
    colony_st = colony_strokes(cult)
    colony_st.vis = visible(colony_st)
    print(f'colony points {len(colony_st.world)}', flush=True)
    true_tone = Tone(light)
    held_tone = Tone(light, cult, held_light=True)
    plate('A-screen-spaced', true_tone, hatch_st, struct_st)
    plate('B-shadow-held', held_tone, hatch_st, struct_st, colony_st, cap=0.13)
    plate('C-colonies-alone', held_tone, hatch_st, struct_st, colony_st, cap=0.18, hatch=False)


if __name__ == '__main__':
    main()
