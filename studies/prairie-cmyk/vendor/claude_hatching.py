"""Functions extracted unchanged from Claude's porticus renderer.
Source: Generative_Art 5bf920e, studies/photophobic/porticus/render.py.
The caller supplies S (camera/surfaces) and the declared rendering constants.
"""
import math
import time
import numpy as np
from scipy.ndimage import map_coordinates
def coverage_target(d):
    return C_MAX * np.clip(d, 0, 1) ** GAMMA

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

def sample(grid, xy):
    return map_coordinates(grid, [xy[:, 1] / GRID - .5, xy[:, 0] / GRID - .5], order=1, mode='nearest')

def interruptions(st, d):
    """Sparse breaks so the screen does not look mechanical (after Sol's)."""
    i = np.arange(len(st.sid))
    start = np.r_[0, np.flatnonzero(np.diff(st.sid)) + 1]
    first = np.repeat(start, np.diff(np.r_[start, len(st.sid)]))
    phase = (np.sin(st.sid * 12.9898) * 43758.5453) % 1 * 2 * math.pi
    return (np.sin((i - first) * 0.21 + phase) > -0.8) | (d > 0.72)

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
