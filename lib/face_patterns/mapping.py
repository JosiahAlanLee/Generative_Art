"""Put two-dimensional line generators on the planar faces of a 3D scene.

A planar face has an exact 2D frame, so any generator that draws in a plane can
draw on it; no curvature field is involved. The frame is anchored to world
coordinates, not to the face: (u, v) = (P . U, P . V), with U horizontal and V
up the plane's steepest slope. Coplanar faces therefore share coordinates and a
pattern continues across their shared edges, and a course drawn at a fixed v
meets itself at the same height around a corner. Two kinds of pattern are
supported:

- a *solid field* f(P), evaluated on each face and contoured, so its level
  lines are continuous wherever the field is (`contour_on_face`);
- a *motif*, 2D polylines and filled regions placed at one position on one
  plane (`hatch_polygon`, `clip_polylines`, `lift`).

Screen density is the caller's: `stride_for_spacing` and `world_spacing` take a
camera Jacobian (2x2 per point, columns d(screen)/du and d(screen)/dv) and keep
line spacing on the page above a minimum. NumPy only; `contour_on_face` also
needs contourpy.
"""
from typing import NamedTuple

import numpy as np

UP = np.array([0., 0., 1.])
EAST = np.array([1., 0., 0.])


class Frame(NamedTuple):
    """World-anchored frame of a plane: U right and V up seen from outside."""
    U: np.ndarray
    V: np.ndarray
    N: np.ndarray
    offset: float  # N . P for every point P of the plane


def newell_normal(points):
    """Unit normal of a planar polygon from its winding (Newell's method)."""
    p = np.asarray(points, float); q = np.roll(p, -1, axis=0)
    n = np.array([((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])).sum(),
                  ((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])).sum(),
                  ((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1])).sum()])
    length = np.linalg.norm(n)
    if length < 1e-12:
        raise ValueError('degenerate polygon has no normal')
    return n / length


def plane_frame(points, normal=None):
    """Frame of the plane through `points` (outward normal from the winding).

    V is world up projected into the plane; on a horizontal plane, where that
    projection vanishes, U is world east instead. U = V x N in both cases, so
    the frame is right-handed when the face is seen from its outward side.
    """
    p = np.asarray(points, float)
    n = newell_normal(p) if normal is None else np.asarray(normal, float) / np.linalg.norm(normal)
    v = UP - n * (n @ UP)
    if np.linalg.norm(v) > 1e-6:
        V = v / np.linalg.norm(v); U = np.cross(V, n)
    else:
        u = EAST - n * (n @ EAST); U = u / np.linalg.norm(u); V = np.cross(n, U)
    return Frame(U, V, n, float(n @ p.mean(0)))


def to_uv(points, frame):
    p = np.asarray(points, float)
    return np.column_stack([p @ frame.U, p @ frame.V])


def lift(uv, frame, height=0.):
    """3D points of plane coordinates, raised `height` along the normal."""
    uv = np.asarray(uv, float).reshape(-1, 2)
    return uv[:, :1] * frame.U + uv[:, 1:] * frame.V + (frame.offset + height) * frame.N


def inside(points, polygon):
    """Even-odd containment of 2D points in a polygon (no holes)."""
    pts = np.asarray(points, float).reshape(-1, 2); poly = np.asarray(polygon, float)
    a = poly[None]; b = np.roll(poly, -1, axis=0)[None]
    x = pts[:, :1]; y = pts[:, 1:]
    crosses = (a[..., 1] > y) != (b[..., 1] > y)
    dy = np.where(np.abs(b[..., 1] - a[..., 1]) < 1e-300, 1e-300, b[..., 1] - a[..., 1])
    x_at = a[..., 0] + (y - a[..., 1]) * (b[..., 0] - a[..., 0]) / dy
    return (crosses & (x < x_at)).sum(1) % 2 == 1


def _cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def clip_polyline(line, polygon, eps=1e-9):
    """The pieces of a polyline inside a simple polygon, convex or not."""
    L = np.asarray(line, float).reshape(-1, 2); poly = np.asarray(polygon, float)
    if len(L) < 2:
        return []
    A, d = L[:-1], np.diff(L, axis=0)
    E0 = poly; e = np.roll(poly, -1, axis=0) - poly
    denom = _cross(d[:, None, :], e[None])
    w = E0[None] - A[:, None, :]
    safe = np.where(np.abs(denom) < eps, 1., denom)
    t = _cross(w, e[None]) / safe; s = _cross(w, d[:, None, :]) / safe
    hit = (np.abs(denom) >= eps) & (t > eps) & (t < 1 - eps) & (s >= -eps) & (s <= 1 + eps)
    whole = inside(A + d / 2, poly)
    pieces, cur = [], []

    def flush():
        if len(cur) >= 2:
            pieces.append(np.asarray(cur))
        cur.clear()

    for i in range(len(d)):
        if not hit[i].any():
            if whole[i]:
                if not cur:
                    cur.append(L[i])
                cur.append(L[i + 1])
            else:
                flush()
            continue
        ts = np.r_[0., np.sort(t[i, hit[i]]), 1.]
        mids = A[i] + d[i] * ((ts[:-1] + ts[1:]) / 2)[:, None]
        for (t0, t1), keep in zip(zip(ts[:-1], ts[1:]), inside(mids, poly)):
            if not keep or t1 - t0 < eps:
                if not keep:
                    flush()
                continue
            p0, p1 = A[i] + d[i] * t0, A[i] + d[i] * t1
            if cur and np.linalg.norm(cur[-1] - p0) > 1e-9:
                flush()
            if not cur:
                cur.append(p0)
            cur.append(p1)
    flush()
    return pieces


def clip_polylines(lines, polygon):
    return [q for line in lines for q in clip_polyline(line, polygon)]


def hatch_polygon(polygon, spacing, angle_deg, phase=0.):
    """Parallel lines `spacing` apart, clipped to a polygon.

    Line offsets are multiples of `spacing` (plus `phase`) measured from the
    plane's origin, not from the polygon, so neighbouring polygons on the same
    plane receive one continuous family.
    """
    if not spacing > 0:
        raise ValueError('spacing must be positive')
    poly = np.asarray(polygon, float); a = np.radians(angle_deg)
    along = np.array([np.cos(a), np.sin(a)]); across = np.array([-along[1], along[0]])
    s, r = poly @ across, poly @ along
    lo, hi = r.min() - 1., r.max() + 1.
    out = []
    for k in range(int(np.ceil((s.min() - phase) / spacing)), int(np.floor((s.max() - phase) / spacing)) + 1):
        c = across * (k * spacing + phase)
        out.extend(clip_polyline(np.array([c + along * lo, c + along * hi]), poly))
    return out


def contour_on_face(field, polygon_uv, frame, step, cell):
    """Level lines of a solid field f(P) on one face, clipped to the face.

    `field` maps (n, 3) world points to values; NaN marks a blank (a fault
    seam, say), where the contourer must not bridge. Levels are integer
    multiples k * step; returns [(k, uv_polyline), ...].
    """
    import contourpy
    poly = np.asarray(polygon_uv, float); lo, hi = poly.min(0), poly.max(0)
    us = np.linspace(lo[0], hi[0], max(2, int(np.ceil((hi[0] - lo[0]) / cell)) + 1))
    vs = np.linspace(lo[1], hi[1], max(2, int(np.ceil((hi[1] - lo[1]) / cell)) + 1))
    uu, vv = np.meshgrid(us, vs)
    z = np.asarray(field(lift(np.column_stack([uu.ravel(), vv.ravel()]), frame)), float).reshape(uu.shape)
    finite = np.isfinite(z)
    if finite.sum() < 4:
        return []
    gen = contourpy.contour_generator(x=us, y=vs, z=np.ma.masked_invalid(z))
    out = []
    for k in range(int(np.ceil(np.nanmin(z) / step)), int(np.floor(np.nanmax(z) / step)) + 1):
        for line in gen.lines(k * step):
            out.extend((k, q) for q in clip_polyline(line, poly))
    return out


def level_spacing_px(field, polygon_uv, frame, step, cell, jacobian):
    """Screen distance between neighbouring levels of a field on a face.

    Returns the 10th percentile over grid points inside the face, or inf
    when the field is constant there. `jacobian(P, U, V)` -> (n, 2, 2).
    """
    poly = np.asarray(polygon_uv, float); lo, hi = poly.min(0), poly.max(0)
    us = np.linspace(lo[0], hi[0], max(3, int(np.ceil((hi[0] - lo[0]) / cell)) + 1))
    vs = np.linspace(lo[1], hi[1], max(3, int(np.ceil((hi[1] - lo[1]) / cell)) + 1))
    uu, vv = np.meshgrid(us, vs)
    pts = np.column_stack([uu.ravel(), vv.ravel()])
    z = np.asarray(field(lift(pts, frame)), float).reshape(uu.shape)
    gv, gu = np.gradient(z, vs, us)
    g = np.column_stack([gu.ravel(), gv.ravel()]); mag = np.linalg.norm(g, axis=1)
    ok = np.isfinite(mag) & (mag > 1e-12) & inside(pts, poly)
    if not ok.any():
        return float('inf')
    n = g[ok] / mag[ok, None]; t = np.column_stack([-n[:, 1], n[:, 0]])
    J = jacobian(lift(pts[ok], frame), frame.U, frame.V)
    jn = np.einsum('kij,kj->ki', J, n); jt = np.einsum('kij,kj->ki', J, t)
    across = np.abs(_cross(jn, jt)) / np.maximum(np.linalg.norm(jt, axis=1), 1e-12)
    return float(np.percentile(across * step / mag[ok], 10))


def stride_for_spacing(spacing_px, min_gap_px):
    """Smallest power-of-two stride that keeps every kept level min_gap apart.

    Dropping odd levels first keeps the levels nested: a coarser plate keeps
    a subset of a finer plate's lines, never new ones.
    """
    stride = 1
    while spacing_px * stride < min_gap_px and stride < 1 << 16:
        stride *= 2
    return stride


def world_spacing(target_px, frame, uv, angle_deg, jacobian):
    """World spacing whose hatch lines land `target_px` apart on the page,
    measured at the worst (most foreshortened) of the given points."""
    a = np.radians(angle_deg); across = np.array([-np.sin(a), np.cos(a)])
    J = jacobian(lift(uv, frame), frame.U, frame.V)
    along = np.array([np.cos(a), np.sin(a)])
    jn = J @ across; jt = J @ along
    per_unit = np.abs(_cross(jn, jt)) / np.maximum(np.linalg.norm(jt, axis=1), 1e-12)
    return float(target_px / max(per_unit.min(), 1e-12))
