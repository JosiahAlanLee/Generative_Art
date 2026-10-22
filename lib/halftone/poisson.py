"""Variable-density Poisson-disc and stratified sampling, after thi.ng's ``poisson``.

``poisson_sample`` throws darts: a random candidate is accepted when no
accepted point lies within the exclusion radius *at the candidate*; a rejected
candidate takes a few random-walk steps of up to ``jitter`` radii before it is
given up. Sampling stops after ``quality`` consecutive failures or at
``max_points``. Because the radius is evaluated per candidate, a function of
position (for instance the tone of an image) gives dense dots in dark areas
and sparse dots in light ones. This is not Bridson's active-list algorithm:
it is slower for uniform radii but handles any radius function and any
mask without a grid of the smallest radius everywhere.

``stratified_grid`` places one point per cell, uniformly inside a centred
sub-square whose side is ``separation`` × the cell, so neighbouring points keep
a guaranteed gap without the blue-noise cost.
"""
from math import ceil

import numpy as np


class _Grid:
    """Hash grid with cells of the smallest radius; queries scan ``ceil(r / cell)`` rings."""

    def __init__(self, cell):
        self.cell = float(cell)
        self.cells = {}
        self.points = []

    def add(self, p):
        key = (int(p[0] // self.cell), int(p[1] // self.cell))
        self.cells.setdefault(key, []).append(len(self.points))
        self.points.append((float(p[0]), float(p[1])))

    def has_within(self, p, r):
        reach = int(ceil(r / self.cell))
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        rr = r * r
        for ix in range(cx - reach, cx + reach + 1):
            for iy in range(cy - reach, cy + reach + 1):
                for index in self.cells.get((ix, iy), ()):
                    q = self.points[index]
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < rr:
                        return True
        return False


def _radius_fn(radius):
    if callable(radius):
        return radius
    r = float(radius)
    if r <= 0:
        raise ValueError("radius must be positive")
    return lambda p: r


def poisson_sample(bounds, radius, rng, *, max_points=None, jitter=1.0, iterations=2, quality=500,
                   mask=None, min_radius=None, seed_points=()):
    """Sample ``bounds = (x0, y0, x1, y1)`` with exclusion ``radius`` (number or ``f(p) -> r``).

    ``mask(p) -> bool`` restricts candidates. ``min_radius`` sizes the hash
    grid; it is required when ``radius`` is a function and defaults to the
    constant radius otherwise. ``seed_points`` are inserted first and count
    toward exclusion. Returns an ``(N, 2)`` array in candidate order.
    """
    x0, y0, x1, y1 = (float(v) for v in bounds)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("empty bounds")
    rfn = _radius_fn(radius)
    cell = min_radius if min_radius is not None else (None if callable(radius) else float(radius))
    if cell is None:
        raise ValueError("min_radius is required with a radius function")
    if cell <= 0 or quality < 1 or iterations < 0 or jitter < 0:
        raise ValueError("min_radius, quality, iterations and jitter must be positive")
    grid = _Grid(cell)
    accepted = []
    for p in seed_points:
        grid.add(p)
        accepted.append((float(p[0]), float(p[1])))
    failures = 0
    while failures < quality and (max_points is None or len(accepted) < max_points):
        p = np.array([rng.uniform(x0, x1), rng.uniform(y0, y1)])
        placed = False
        for step in range(iterations + 1):
            inside = x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and (mask is None or mask(p))
            if inside:
                r = float(rfn(p))
                if r < cell:
                    raise ValueError("radius function returned less than min_radius")
                if not grid.has_within(p, r):
                    grid.add(p)
                    accepted.append((float(p[0]), float(p[1])))
                    placed = True
                    break
            else:
                r = cell
            if step < iterations:
                angle = rng.uniform(0, 2 * np.pi)
                p = p + rng.uniform(0, r * jitter) * np.array([np.cos(angle), np.sin(angle)])
        failures = 0 if placed else failures + 1
    return np.array(accepted, dtype=float).reshape(-1, 2)


def stratified_grid(bounds, cell, rng, separation=.7, mask=None):
    """One jittered point per ``cell`` × ``cell`` square over ``bounds``."""
    x0, y0, x1, y1 = (float(v) for v in bounds)
    if cell <= 0 or not 0 <= separation <= 1:
        raise ValueError("cell must be positive and separation in [0, 1]")
    nx, ny = int(ceil((x1 - x0) / cell)), int(ceil((y1 - y0) / cell))
    gx, gy = np.meshgrid(np.arange(nx), np.arange(ny))
    centres = np.column_stack([x0 + (gx.ravel() + .5) * cell, y0 + (gy.ravel() + .5) * cell])
    offsets = (rng.uniform(-.5, .5, centres.shape)) * separation * cell
    p = centres + offsets
    keep = (p[:, 0] <= x1) & (p[:, 1] <= y1)
    if mask is not None:
        keep &= np.array([bool(mask(q)) for q in p])
    return p[keep]


def tone_radius(image, bounds, r_min, r_max, gamma=1.0):
    """Radius function from a tone array (0 black … 1 white) stretched over ``bounds``.

    Dark pixels give ``r_min``, white gives ``r_max``; ``gamma`` bends the
    mapping (above 1 keeps mid-tones sparse). Returns ``(fn, r_min)`` for use
    as ``poisson_sample(bounds, fn, rng, min_radius=r_min)``.
    """
    z = np.asarray(image, dtype=float)
    h, w = z.shape
    x0, y0, x1, y1 = (float(v) for v in bounds)

    def fn(p):
        u = (p[0] - x0) / (x1 - x0) * (w - 1)
        v = (p[1] - y0) / (y1 - y0) * (h - 1)
        i, j = int(np.clip(round(v), 0, h - 1)), int(np.clip(round(u), 0, w - 1))
        t = z[i, j] ** gamma
        return r_min + (r_max - r_min) * t

    return fn, r_min
