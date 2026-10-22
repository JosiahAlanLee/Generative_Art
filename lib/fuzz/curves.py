"""Subdivision curves and polygon-to-cubic conversion.

``subdivide`` applies one of six schemes, after thi.ng ``geom-subdiv-curve``:

- ``chaikin``: corner cutting at 1/4 and 3/4 (Chaikin 1974); open curves keep
  their end points.
- ``cubic``: Lane–Riesenfeld cubic B-spline refinement (edge midpoints, vertex
  points at (p−1 + 6p + p+1)/8). Open curves keep their end points.
- ``dlg``: the Dyn–Levin–Gregory four-point interpolating scheme (1987): a new
  point between p1 and p2 at 9/16 (p1 + p2) − 1/16 (p0 + p3). The original
  points stay on the curve. Open curves clamp their ends.
- ``midpoint`` and ``thirds``: insert points without moving the vertices.
- ``displace``: midpoint displacement along the edge normal by a random amount
  scaled by ``amplitude`` × edge length, halving each iteration by ``decay``;
  the rough-coast or torn-edge scheme.

``polygon_to_cubic`` turns a polygon (or an open polyline) into cubic Bézier
segments in two modes, after thi.ng ``geom-splines``:

- ``break``: vertices lie on the curve; the tangent at each vertex is the
  chord between its neighbours and handles are ``tightness`` × the edge
  length (or × the mean edge length with ``uniform``).
- ``midpoint``: vertices are control points and the curve passes through the
  edge midpoints, with handles pulled toward the vertex by ``tightness``
  (2/3 reproduces the degree-elevated quadratic through the midpoints).
"""
import numpy as np

SCHEMES = ("chaikin", "cubic", "dlg", "midpoint", "thirds", "displace")


def _ring(p, closed):
    return np.vstack([p, p[:1]]) if closed else p


def _normals(p):
    d = np.diff(p, axis=0)
    n = np.column_stack([-d[:, 1], d[:, 0]])
    length = np.linalg.norm(n, axis=1)
    return n / np.where(length == 0, 1, length)[:, None], length


def subdivide(points, scheme="chaikin", iterations=1, closed=False, rng=None, amplitude=.25, decay=.5):
    """Refine ``points`` (N×2) ``iterations`` times with ``scheme``."""
    if scheme not in SCHEMES:
        raise ValueError(f"scheme must be one of {SCHEMES}")
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2:
        raise ValueError("at least two 2-D points are required")
    if closed and len(p) < 3:
        raise ValueError("a closed curve needs at least three points")
    if scheme == "displace" and rng is None:
        raise ValueError("displace needs a random generator")
    for _ in range(iterations):
        if scheme == "chaikin":
            r = _ring(p, closed)
            a, b = r[:-1], r[1:]
            new = np.empty((2 * len(a), 2))
            new[0::2], new[1::2] = .75 * a + .25 * b, .25 * a + .75 * b
            p = new if closed else np.vstack([p[:1], new, p[-1:]])
        elif scheme == "cubic":
            r = _ring(p, closed)
            edge = .5 * (r[:-1] + r[1:])
            if closed:
                prev, nxt = np.roll(p, 1, axis=0), np.roll(p, -1, axis=0)
                vertex = (prev + 6 * p + nxt) / 8
                new = np.empty((2 * len(p), 2))
                new[0::2], new[1::2] = vertex, edge
                p = new
            else:
                vertex = p.copy()
                vertex[1:-1] = (p[:-2] + 6 * p[1:-1] + p[2:]) / 8
                new = np.empty((2 * len(p) - 1, 2))
                new[0::2], new[1::2] = vertex, edge
                p = new
        elif scheme == "dlg":
            if closed:
                p0, p1, p2, p3 = np.roll(p, 1, axis=0), p, np.roll(p, -1, axis=0), np.roll(p, -2, axis=0)
                mid = 9 / 16 * (p1 + p2) - 1 / 16 * (p0 + p3)
                new = np.empty((2 * len(p), 2))
                new[0::2], new[1::2] = p, mid
                p = new
            else:
                ext = np.vstack([p[:1], p, p[-1:]])      # clamped ends
                p0, p1, p2, p3 = ext[:-3], ext[1:-2], ext[2:-1], ext[3:]
                mid = 9 / 16 * (p1 + p2) - 1 / 16 * (p0 + p3)
                new = np.empty((2 * len(p) - 1, 2))
                new[0::2], new[1::2] = p, mid
                p = new
        elif scheme in ("midpoint", "thirds", "displace"):
            r = _ring(p, closed)
            a, b = r[:-1], r[1:]
            if scheme == "thirds":
                new = np.empty((3 * len(a), 2))
                new[0::3], new[1::3], new[2::3] = a, (2 * a + b) / 3, (a + 2 * b) / 3
            else:
                mid = .5 * (a + b)
                if scheme == "displace":
                    normal, length = _normals(r)
                    mid = mid + normal * (rng.uniform(-1, 1, len(a)) * amplitude * length)[:, None]
                new = np.empty((2 * len(a), 2))
                new[0::2], new[1::2] = a, mid
            p = new if closed else np.vstack([new, p[-1:]])
            if scheme == "displace":
                amplitude *= decay
    return p


def polygon_to_cubic(points, mode="break", tightness=1 / 3, closed=True, uniform=False):
    """Cubic Bézier segments ``(p0, c1, c2, p3)`` through or around ``points``."""
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3:
        raise ValueError("at least three 2-D points are required")
    if mode not in ("break", "midpoint"):
        raise ValueError("mode must be 'break' or 'midpoint'")
    if not 0 < tightness <= 1:
        raise ValueError("tightness must lie in (0, 1]")
    n = len(p)
    segments = []
    if mode == "break":
        if closed:
            prev, nxt = np.roll(p, 1, axis=0), np.roll(p, -1, axis=0)
        else:
            prev, nxt = np.vstack([p[:1], p[:-1]]), np.vstack([p[1:], p[-1:]])
        tangent = nxt - prev
        norm = np.linalg.norm(tangent, axis=1)
        tangent /= np.where(norm == 0, 1, norm)[:, None]
        edges = range(n) if closed else range(n - 1)
        mean_edge = np.mean([np.linalg.norm(p[(i + 1) % n] - p[i]) for i in edges]) if uniform else None
        for i in edges:
            j = (i + 1) % n
            length = mean_edge if uniform else np.linalg.norm(p[j] - p[i])
            segments.append((p[i], p[i] + tangent[i] * tightness * length,
                             p[j] - tangent[j] * tightness * length, p[j]))
    else:
        if closed:
            prev, nxt = np.roll(p, 1, axis=0), np.roll(p, -1, axis=0)
            verts = range(n)
        else:
            prev, nxt = np.vstack([p[:1], p[:-1]]), np.vstack([p[1:], p[-1:]])
            verts = range(1, n - 1)
        for i in verts:
            m0, m1 = .5 * (prev[i] + p[i]), .5 * (p[i] + nxt[i])
            segments.append((m0, m0 + tightness * (p[i] - m0), m1 + tightness * (p[i] - m1), m1))
        if not closed:
            # Straight (degenerate cubic) legs join the end points to the first and last midpoints.
            m_first, m_last = .5 * (p[0] + p[1]), .5 * (p[-2] + p[-1])
            segments.insert(0, (p[0], p[0], m_first, m_first))
            segments.append((m_last, m_last, p[-1], p[-1]))
    return segments


def cubic_points(segment, n=12, include_end=True):
    """Sample one cubic segment at ``n`` parameter values."""
    p0, c1, c2, p3 = (np.asarray(v, dtype=float) for v in segment)
    t = np.linspace(0, 1, n, endpoint=include_end)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p3


def cubics_to_polyline(segments, n=12, closed=True):
    """Join sampled segments into one polyline (closing it when ``closed``)."""
    parts = [cubic_points(s, n, include_end=False) for s in segments]
    poly = np.vstack(parts)
    end = np.asarray(segments[-1][3], dtype=float)
    return np.vstack([poly, poly[:1] if closed else end[None]])
