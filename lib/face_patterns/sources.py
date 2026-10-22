"""This collection's own 2D generators, adapted for planar faces.

`Strata` turns the process-art `stratigraphy` section into a solid field, so
its bedding is continuous across the walls of a building. `quilt` returns a
barn-quilt block as outlines and value-coded regions in the unit square.
Neither changes the generator it wraps.
"""
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from lib.barn_quilts import block, unique_edges
from lib.process_art.models import stratigraphy

from .mapping import inside


class Strata:
    """The `stratigraphy` section extruded along a horizontal axis.

    The model's folded, faulted age field over [-1, 1]^2 is placed in the
    vertical plane through `origin` that contains `axis`; a point P reads the
    section at x = (P - origin) . axis / (scale * stretch) and
    y = -(P_z - origin_z) / scale, so age increases downward. A `stretch`
    above 1 lengthens the folds horizontally, flattening their dips (a
    geological section's vertical exaggeration, undone). A wall parallel to `axis` shows the folds and
    the fault offsets; a wall across it shows level beds, and the two meet at
    the corner. The fault seams the model blanks stay blank (NaN), so no
    contour bridges a fault. The model's specimen outline is not applied: a
    wall is cut from inside the body. Outside the section the field is NaN.
    """

    def __init__(self, origin, axis, scale, *, stretch=1., seed=11, n=320, throw=.24, fold=.24):
        if not (scale > 0 and stretch > 0):
            raise ValueError('scale and stretch must be positive')
        m = stratigraphy(seed=seed, n=n, throw=throw, fold=fold)
        x, y = m['x'][0], m['y'][:, 0]
        seams = (np.abs(m['x'] - m['fault1']) > .012) & (np.abs(m['x'] - m['fault2']) > .009)
        self._age = RegularGridInterpolator((y, x), m['age'], bounds_error=False, fill_value=np.nan)
        self._open = RegularGridInterpolator((y, x), seams.astype(float), method='nearest',
                                             bounds_error=False, fill_value=0.)
        a = np.asarray(axis, float); a[2] = 0
        self.origin = np.asarray(origin, float); self.axis = a / np.linalg.norm(a)
        self.scale, self.stretch = float(scale), float(stretch)
        self.params = dict(seed=seed, n=n, throw=throw, fold=fold, scale=self.scale, stretch=self.stretch,
                           origin=self.origin.tolist(), axis=self.axis.tolist())

    def section(self, points):
        q = np.asarray(points, float).reshape(-1, 3) - self.origin
        return np.column_stack([-q[:, 2] / self.scale, q @ self.axis / (self.scale * self.stretch)])

    def __call__(self, points):
        yx = self.section(points)
        age = self._age(yx)
        age[self._open(yx) < .5] = np.nan
        return age


def quilt(pattern='ohio-star', seed=23, detail=4):
    """A block as regions by paint role, its piecing seams and its paint edges.

    `edges` are every piecing seam once (`unique_edges`); `boundaries` keeps
    only the interior seams between different paint roles, the edges a painted
    quilt shows. Coordinates are flipped to y-up (the generator draws SVG
    y-down), so a point (x, y) sits at (u0 + x * size, v0 + y * size) on a wall.
    Roles: 0 light ground, 1 main paint, 2 contrasting paint, 3 secondary.
    """
    patches = block(pattern, seed=seed, detail=detail)
    flip = lambda pts: np.array([(x, 1 - y) for x, y in pts], float)
    regions = [(flip(p.points), p.role) for p in patches]
    edges = [flip(e) for e in unique_edges(patches)]

    def role_at(point):
        for poly, role in regions:
            if inside([point], poly)[0]:
                return role
        return None
    boundaries = []
    for e in edges:
        mid, d = e.mean(0), e[1] - e[0]
        normal = np.array([-d[1], d[0]]) / np.linalg.norm(d) * 1e-6
        a, b = role_at(mid + normal), role_at(mid - normal)
        if a is not None and b is not None and a != b:
            boundaries.append(e)
    return dict(pattern=pattern, seed=seed, regions=regions, edges=edges, boundaries=boundaries)
