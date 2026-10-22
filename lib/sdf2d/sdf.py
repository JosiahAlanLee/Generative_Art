"""Two-dimensional signed distance fields as composable functions.

An SDF here is a function ``f(p)`` taking an N×2 array of points and
returning N signed distances: negative inside, zero on the boundary, positive
outside, in the same units as the points. Primitives follow the published
formulas of Inigo Quilez ("2D distance functions") and the combination and
domain operators follow Mercury's hg_sdf (union, intersection and
subtraction with chamfered, rounded, smooth and stepped variants; repetition
in a grid, with mirroring, and in polar sectors), the same sources thi.ng's
``geom-sdf`` cites. Nothing here is a mesh or a polygon: shapes stay
analytic until ``grid.sample`` evaluates them.
"""
from math import atan2, cos, pi, sin

import numpy as np

__all__ = ["circle", "box", "rounded_box", "segment", "polyline", "polygon", "ellipse", "triangle",
           "union", "intersect", "subtract", "union_chamfer", "intersect_chamfer", "subtract_chamfer",
           "union_round", "intersect_round", "subtract_round", "union_smooth", "intersect_smooth",
           "subtract_smooth", "union_steps", "intersect_steps", "subtract_steps",
           "translate", "rotate", "scale", "mirror_x", "mirror_y", "repeat", "repeat_mirror", "repeat_polar",
           "offset", "annular", "band", "field"]


def _pts(p):
    p = np.asarray(p, dtype=float)
    if p.ndim == 1:
        p = p[None, :]
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError("an N×2 array of points is required")
    return p


# --- primitives ---------------------------------------------------------------

def circle(r, center=(0.0, 0.0)):
    c = np.asarray(center, dtype=float)

    def f(p):
        return np.linalg.norm(_pts(p) - c, axis=1) - r
    return f


def box(half_w, half_h, center=(0.0, 0.0)):
    """An axis-aligned box of half extents ``half_w`` × ``half_h``."""
    c, b = np.asarray(center, dtype=float), np.array([half_w, half_h], dtype=float)

    def f(p):
        d = np.abs(_pts(p) - c) - b
        return np.linalg.norm(np.maximum(d, 0), axis=1) + np.minimum(np.maximum(d[:, 0], d[:, 1]), 0)
    return f


def rounded_box(half_w, half_h, r, center=(0.0, 0.0)):
    return offset(box(half_w - r, half_h - r, center), r)


def segment(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    ab = b - a
    ab2 = float(ab @ ab) or 1.0

    def f(p):
        pa = _pts(p) - a
        h = np.clip((pa @ ab) / ab2, 0, 1)
        return np.linalg.norm(pa - h[:, None] * ab, axis=1)
    return f


def polyline(points):
    """Unsigned distance to an open polyline (the thickness comes from ``offset``)."""
    pts = _pts(points)
    segs = [segment(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]

    def f(p):
        return np.min(np.column_stack([s(p) for s in segs]), axis=1)
    return f


def polygon(points):
    """Exact signed distance to a simple polygon (Quilez's winding formulation)."""
    v = _pts(points)
    if len(v) < 3:
        raise ValueError("a polygon needs at least three vertices")
    if np.allclose(v[0], v[-1]):
        v = v[:-1]
    n = len(v)

    def f(p):
        p = _pts(p)
        d = np.full(len(p), np.inf)
        s = np.ones(len(p))
        for i in range(n):
            j = (i - 1) % n
            e = v[j] - v[i]
            w = p - v[i]
            h = np.clip((w @ e) / float(e @ e), 0, 1)
            b = w - h[:, None] * e
            d = np.minimum(d, np.einsum("ij,ij->i", b, b))
            c1 = p[:, 1] >= v[i, 1]
            c2 = p[:, 1] < v[j, 1]
            c3 = e[0] * w[:, 1] > e[1] * w[:, 0]
            flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            s = np.where(flip, -s, s)
        return s * np.sqrt(d)
    return f


def ellipse(a, b, center=(0.0, 0.0)):
    """Approximate signed distance to an ellipse (exact on the axes, slightly short elsewhere)."""
    c, r = np.asarray(center, dtype=float), np.array([a, b], dtype=float)

    def f(p):
        q = (_pts(p) - c) / r
        k0 = np.linalg.norm(q, axis=1)
        k1 = np.linalg.norm(q / r, axis=1)
        return np.where(k1 > 0, k0 * (k0 - 1) / np.where(k1 == 0, 1, k1), -min(a, b))
    return f


def triangle(a, b, c):
    return polygon([a, b, c])


# --- combinations (hg_sdf) ---------------------------------------------------

def union(*fs):
    def f(p):
        return np.min(np.column_stack([g(p) for g in fs]), axis=1)
    return f


def intersect(*fs):
    def f(p):
        return np.max(np.column_stack([g(p) for g in fs]), axis=1)
    return f


def subtract(a, b):
    """``a`` minus ``b``."""
    def f(p):
        return np.maximum(a(p), -b(p))
    return f


def _binary(op):
    """Lift a two-field operator into the union / intersect / subtract trio."""
    def make_union(a, b, *args):
        return lambda p: op(a(p), b(p), *args)

    def make_intersect(a, b, *args):
        return lambda p: -op(-a(p), -b(p), *args)

    def make_subtract(a, b, *args):
        return lambda p: -op(-a(p), b(p), *args)
    return make_union, make_intersect, make_subtract


def _chamfer(a, b, r):
    return np.minimum(np.minimum(a, b), (a - r + b) * np.sqrt(.5))


def _round(a, b, r):
    u = np.maximum(np.column_stack([r - a, r - b]), 0)
    return np.maximum(r, np.minimum(a, b)) - np.linalg.norm(u, axis=1)


def _smooth(a, b, k):
    h = np.clip(.5 + .5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def _steps(a, b, r, n):
    s = r / n
    u = b - r
    return np.minimum(np.minimum(a, b), .5 * (u + a + np.abs(np.mod(u - a + s, 2 * s) - s)))


union_chamfer, intersect_chamfer, subtract_chamfer = _binary(_chamfer)
union_round, intersect_round, subtract_round = _binary(_round)
union_smooth, intersect_smooth, subtract_smooth = _binary(_smooth)
union_steps, intersect_steps, subtract_steps = _binary(_steps)


# --- domain operators ----------------------------------------------------------

def translate(f, v):
    v = np.asarray(v, dtype=float)
    return lambda p: f(_pts(p) - v)


def rotate(f, degrees, center=(0.0, 0.0)):
    """Rotate the shape by ``degrees`` counter-clockwise about ``center``."""
    a = np.radians(degrees)
    m = np.array([[cos(a), sin(a)], [-sin(a), cos(a)]])   # inverse rotation applied to the points
    c = np.asarray(center, dtype=float)
    return lambda p: f((_pts(p) - c) @ m.T + c)


def scale(f, s):
    """Uniform scale about the origin; distances are rescaled so the field stays a distance."""
    return lambda p: f(_pts(p) / s) * s


def mirror_x(f):
    """Mirror the x > 0 half across the y axis (``|x|``)."""
    def g(p):
        q = _pts(p).copy()
        q[:, 0] = np.abs(q[:, 0])
        return f(q)
    return g


def mirror_y(f):
    def g(p):
        q = _pts(p).copy()
        q[:, 1] = np.abs(q[:, 1])
        return f(q)
    return g


def repeat(f, period):
    """Tile the shape on a grid with ``period = (px, py)`` (a scalar repeats both axes); 0 disables an axis."""
    c = np.broadcast_to(np.asarray(period, dtype=float), (2,)).copy()

    def g(p):
        q = _pts(p).copy()
        for k in range(2):
            if c[k] > 0:
                q[:, k] = np.mod(q[:, k] + .5 * c[k], c[k]) - .5 * c[k]
        return f(q)
    return g


def repeat_mirror(f, period):
    """Like ``repeat`` but every second cell is mirrored, so edges meet."""
    c = np.broadcast_to(np.asarray(period, dtype=float), (2,)).copy()

    def g(p):
        q = _pts(p).copy()
        for k in range(2):
            if c[k] > 0:
                cell = np.floor((q[:, k] + .5 * c[k]) / c[k])
                q[:, k] = np.mod(q[:, k] + .5 * c[k], c[k]) - .5 * c[k]
                q[:, k] *= np.where(np.mod(cell, 2) == 0, 1, -1)
        return f(q)
    return g


def repeat_polar(f, n, center=(0.0, 0.0)):
    """Repeat the shape ``n`` times around ``center``; the shape is defined in the sector around +x."""
    c = np.asarray(center, dtype=float)
    sector = 2 * pi / n

    def g(p):
        q = _pts(p) - c
        a = np.arctan2(q[:, 1], q[:, 0]) + sector / 2
        r = np.linalg.norm(q, axis=1)
        a = np.mod(a, sector) - sector / 2
        return f(np.column_stack([r * np.cos(a), r * np.sin(a)]) + c)
    return g


def offset(f, d):
    """Grow the shape by ``d`` (shrink with negative ``d``)."""
    return lambda p: f(p) - d


def annular(f, d):
    """A ring of half-width ``d`` around the boundary (an outline as a shape)."""
    return lambda p: np.abs(f(p)) - d


def band(f, lo, hi):
    """The part of the shape at depth between ``lo`` and ``hi`` inside the boundary (``0 <= lo < hi``)."""
    if not 0 <= lo < hi:
        raise ValueError("0 <= lo < hi is required")

    def g(p):
        v = f(p)
        return np.maximum(v + lo, -(v + hi))
    return g


def field(f, xs, ys):
    """Evaluate ``f`` on the grid given by 1-D ``xs`` and ``ys``; returns ``(len(ys), len(xs))``."""
    gx, gy = np.meshgrid(xs, ys)
    return f(np.column_stack([gx.ravel(), gy.ravel()])).reshape(len(ys), len(xs))
