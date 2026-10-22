"""From a distance field to pen paths: sampling, iso-contours and sign-tested hatching."""
from math import cos, radians, sin

import contourpy
import numpy as np
from shapely.geometry import LineString

from .sdf import field

__all__ = ["sample", "contours", "levels", "hatch_by_sign", "band_count"]


def sample(f, bounds, resolution):
    """Evaluate ``f`` on a grid over ``bounds = (x0, y0, x1, y1)`` at ``resolution`` units per cell.

    Returns ``(values, xs, ys)`` with ``values`` shaped ``(len(ys), len(xs))``.
    """
    x0, y0, x1, y1 = (float(v) for v in bounds)
    if resolution <= 0 or x1 <= x0 or y1 <= y0:
        raise ValueError("positive resolution and non-empty bounds are required")
    xs = np.linspace(x0, x1, int(round((x1 - x0) / resolution)) + 1)
    ys = np.linspace(y0, y1, int(round((y1 - y0) / resolution)) + 1)
    return field(f, xs, ys), xs, ys


def contours(values, xs, ys, iso=0.0, simplify=0.0):
    """Marching-squares contour polylines of ``values`` at ``iso``, in the grid's units."""
    cg = contourpy.contour_generator(x=xs, y=ys, z=np.asarray(values, dtype=float), name="serial",
                                     corner_mask=False)
    lines = []
    for pts in cg.lines(float(iso)):
        if len(pts) < 2:
            continue
        if simplify and len(pts) > 3:
            pts = np.asarray(LineString(pts).simplify(simplify).coords)
        lines.append(np.asarray(pts, dtype=float))
    return lines


def levels(values, xs, ys, isos, simplify=0.0):
    """Contours at several iso values; returns ``{iso: [polylines]}`` in the order given."""
    return {float(iso): contours(values, xs, ys, iso, simplify) for iso in isos}


def band_count(f, bounds, resolution, step, limit=None):
    """How many offset bands of width ``step`` fit inside the shape (for nested inner contours)."""
    values, _, _ = sample(f, bounds, resolution)
    deepest = -float(values.min())
    n = int(deepest // step)
    return n if limit is None else min(n, limit)


def hatch_by_sign(f, bounds, spacing, angle=45.0, step=.25, level=0.0, phase=0.0, alternate=True):
    """Hatch where ``f(p) < level`` by sampling along parallel lines and keeping the negative runs.

    No polygon is built: each line is walked at ``step`` and split where the
    field changes sign, with the crossing refined by linear interpolation. The
    result is a list of polylines of two points each (longer when a run bends
    nowhere, which for straight hatching it never does).
    """
    x0, y0, x1, y1 = (float(v) for v in bounds)
    if spacing <= 0 or step <= 0:
        raise ValueError("spacing and step must be positive")
    cx, cy = .5 * (x0 + x1), .5 * (y0 + y1)
    a = radians(angle)
    d = np.array([cos(a), sin(a)])
    n = np.array([-sin(a), cos(a)])
    radius = .5 * np.hypot(x1 - x0, y1 - y0)
    k = int(np.ceil(radius / spacing))
    t = np.arange(-radius, radius + step, step)
    runs = []
    for i in range(-k, k + 1):
        centre = np.array([cx, cy]) + n * (i + phase) * spacing
        pts = centre + t[:, None] * d
        inside_bounds = (pts[:, 0] >= x0) & (pts[:, 0] <= x1) & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
        if not inside_bounds.any():
            continue
        v = np.where(inside_bounds, f(pts) - level, np.inf)
        neg = v < 0
        padded = np.concatenate(([False], neg, [False]))
        starts = np.flatnonzero(~padded[:-1] & padded[1:])
        ends = np.flatnonzero(padded[:-1] & ~padded[1:])
        for s, e in zip(starts, ends):
            # Refine both crossings between the last outside sample and the first inside one.
            p_start = pts[s]
            if s > 0 and np.isfinite(v[s - 1]):
                w = v[s - 1] / (v[s - 1] - v[s])
                p_start = pts[s - 1] + w * (pts[s] - pts[s - 1])
            p_end = pts[e - 1]
            if e < len(pts) and np.isfinite(v[e]):
                w = v[e - 1] / (v[e - 1] - v[e])
                p_end = pts[e - 1] + w * (pts[e] - pts[e - 1])
            line = np.vstack([p_start, p_end])
            if alternate and i % 2:
                line = line[::-1]
            if np.linalg.norm(line[1] - line[0]) > 1e-9:
                runs.append(line)
    return runs
