"""Hand-drawn passes and composable fills, after thi.ng ``geom-fuzz``.

A fuzzy polygon is drawn several times, each pass from a freshly jittered copy
of the vertices, optionally smoothed into a curve through those vertices. Fills
are functions ``fill(polygon, rng) -> list of polylines``; ``compose`` joins
several so one shape can carry a hatch and a dot screen together. Hatching
clips lines at any angle to the polygon with shapely, so there is no need to
rotate the shape itself. Dots are returned as point arrays by ``dot_fill`` and
wrapped as tiny rings by ``dots_as_rings`` for the plate.

The book already has ``core.Wobble`` (a stable tremor along one pass) and the
Driftless print hand (skips, overshoot, misregistration). This module adds the
multi-pass sketch and the composable fills that neither provides.
"""
from math import cos, radians, sin

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from .curves import cubics_to_polyline, polygon_to_cubic

__all__ = ["fuzzy_polygon", "fuzzy_line", "hatch_fill", "dot_fill", "dots_as_rings", "compose",
           "hatch_pen", "dot_pen", "union", "as_polygon"]


def as_polygon(shape):
    """Accept a shapely polygon or an N×2 array of vertices."""
    if isinstance(shape, Polygon):
        return shape
    p = np.asarray(shape, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3:
        raise ValueError("a polygon needs at least three 2-D points")
    poly = Polygon(p)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def _jitter(points, rng, amount, closed):
    p = np.asarray(points, dtype=float)
    if amount <= 0:
        return p.copy()
    j = p + rng.normal(0, amount, p.shape)
    if closed and np.allclose(p[0], p[-1]):
        j[-1] = j[0]
    return j


def fuzzy_polygon(points, rng, passes=2, jitter=.3, curve=True, closed=True, samples=10, tightness=1 / 3):
    """``passes`` outlines of ``points``, each from an independently jittered copy.

    With ``curve`` the jittered vertices become break points of a cubic spline
    (``polygon_to_cubic`` in ``break`` mode) sampled ``samples`` times per
    edge; otherwise each pass is the jittered polyline itself. Returns a list
    of N×2 polylines (closed ones repeat their first point).
    """
    p = np.asarray(points, dtype=float)
    if closed and np.allclose(p[0], p[-1]):
        p = p[:-1]
    if len(p) < (3 if closed or curve else 2):
        raise ValueError("not enough points")
    if passes < 1:
        raise ValueError("passes must be at least 1")
    out = []
    for _ in range(passes):
        q = _jitter(p, rng, jitter, False)
        if curve:
            out.append(cubics_to_polyline(polygon_to_cubic(q, "break", tightness, closed), samples, closed))
        else:
            out.append(np.vstack([q, q[:1]]) if closed else q)
    return out


def fuzzy_line(points, rng, jitter=.2, resample=None, passes=1):
    """Jittered polyline(s); with ``resample`` (mm) the line is first resampled so the jitter is per step."""
    p = np.asarray(points, dtype=float)
    if len(p) < 2:
        raise ValueError("a line needs two points")
    if resample:
        line = LineString(p)
        n = max(2, int(np.ceil(line.length / resample)) + 1)
        p = np.array([line.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, n)])
    return [_jitter(p, rng, jitter, False) for _ in range(passes)]


def _clip(lines, polygon):
    out = []
    for line in lines:
        g = LineString(line).intersection(polygon)
        if g.is_empty:
            continue
        parts = list(g.geoms) if hasattr(g, "geoms") else [g]
        for part in parts:
            if part.geom_type == "LineString" and part.length > 1e-9:
                out.append(np.asarray(part.coords))
    return out


def hatch_fill(polygon, spacing, angle=45.0, rng=None, jitter=0.0, phase=0.0, alternate=True, inset=0.0):
    """Parallel lines at ``angle`` degrees, ``spacing`` apart, clipped to ``polygon``.

    ``jitter`` shifts each line's offset by a normal deviate (mm) and, when an
    ``rng`` is given, wobbles the end points; ``phase`` slides the whole set;
    ``alternate`` reverses every second line so the pen travels back and
    forth; ``inset`` shrinks the polygon first so lines stop short of the edge.
    """
    poly = as_polygon(polygon)
    if inset:
        poly = poly.buffer(-inset)
        if poly.is_empty:
            return []
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    cx, cy = poly.centroid.x, poly.centroid.y
    minx, miny, maxx, maxy = poly.bounds
    radius = .5 * np.hypot(maxx - minx, maxy - miny) + spacing
    a = radians(angle)
    d = np.array([cos(a), sin(a)])          # along the line
    n = np.array([-sin(a), cos(a)])         # across the lines
    k = int(np.ceil(radius / spacing))
    lines = []
    for i in range(-k, k + 1):
        offset = (i + phase) * spacing
        if jitter and rng is not None:
            offset += rng.normal(0, jitter)
        centre = np.array([cx, cy]) + n * offset
        line = np.vstack([centre - d * radius, centre + d * radius])
        if alternate and i % 2:
            line = line[::-1]
        lines.append(line)
    clipped = _clip(lines, poly)
    if jitter and rng is not None:
        clipped = [np.vstack([l[0] + rng.normal(0, jitter * .5, 2), l[1:-1], l[-1] + rng.normal(0, jitter * .5, 2)])
                   if len(l) > 2 else l + rng.normal(0, jitter * .5, l.shape) for l in clipped]
    return clipped


def dot_fill(polygon, spacing, rng=None, jitter=.35, stagger=True, inset=0.0):
    """Points on a (staggered) grid inside ``polygon``, each moved by ``jitter`` × spacing."""
    poly = as_polygon(polygon)
    if inset:
        poly = poly.buffer(-inset)
        if poly.is_empty:
            return np.zeros((0, 2))
    if spacing <= 0:
        raise ValueError("spacing must be positive")
    minx, miny, maxx, maxy = poly.bounds
    rows = np.arange(miny, maxy + spacing, spacing * (np.sqrt(3) / 2 if stagger else 1))
    pts = []
    for r, y in enumerate(rows):
        x0 = minx + (spacing / 2 if stagger and r % 2 else 0)
        xs = np.arange(x0, maxx + spacing, spacing)
        pts.append(np.column_stack([xs, np.full(len(xs), y)]))
    pts = np.vstack(pts)
    if jitter and rng is not None:
        pts = pts + rng.uniform(-.5, .5, pts.shape) * jitter * spacing
    from shapely import contains_xy
    keep = contains_xy(poly, pts[:, 0], pts[:, 1])
    return pts[keep]


def dots_as_rings(points, radius=.12, n=12):
    """Tiny closed rings (polylines) for a plate, one per point."""
    t = np.linspace(0, 2 * np.pi, n + 1)
    ring = np.column_stack([np.cos(t), np.sin(t)]) * radius
    return [p + ring for p in np.asarray(points, dtype=float)]


def compose(*fills):
    """A fill that runs each fill in turn and concatenates their polylines."""
    def fill(polygon, rng):
        out = []
        for f in fills:
            out.extend(f(polygon, rng))
        return out
    return fill


def hatch_pen(spacing, angle=45.0, passes=1, jitter=.08, inset=0.0, cross=False):
    """Preset: a jittered hatch (optionally crossed at +90°) drawn ``passes`` times."""
    def fill(polygon, rng):
        out = []
        for k in range(passes):
            phase = k / passes
            out.extend(hatch_fill(polygon, spacing, angle, rng, jitter, phase, inset=inset))
            if cross:
                out.extend(hatch_fill(polygon, spacing, angle + 90, rng, jitter, phase, inset=inset))
        return out
    return fill


def dot_pen(spacing, radius=.12, jitter=.35, inset=0.0):
    """Preset: a staggered dot screen as rings."""
    def fill(polygon, rng):
        return dots_as_rings(dot_fill(polygon, spacing, rng, jitter, inset=inset), radius)
    return fill


def union(polygons):
    """Merge several shapes into one (for fills across overlapping forms)."""
    return unary_union([as_polygon(p) for p in polygons])
