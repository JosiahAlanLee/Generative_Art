"""Surfaces as flat grids in scene units, so the mould's cell is the same size in the
scene wherever it grows. Each surface maps grid (u, v) to world points, normals and a
tangent frame; the camera, not the simulation, makes far things small."""
import math

import numpy as np
from scipy.ndimage import map_coordinates, binary_erosion


class Surface:
    material_albedo = 0.72

    def __init__(self, name, u0, u1, v0, v1, cell):
        self.name, self.cell = name, float(cell)
        self.u0, self.v0 = u0, v0
        self.nu = int(math.ceil((u1 - u0) / cell))
        self.nv = int(math.ceil((v1 - v0) / cell))
        self.u1, self.v1 = u0 + self.nu * cell, v0 + self.nv * cell

    def centers(self, step=1):
        u = self.u0 + (np.arange(0, self.nu, step) + 0.5 * step) * self.cell
        v = self.v0 + (np.arange(0, self.nv, step) + 0.5 * step) * self.cell
        return np.meshgrid(u, v)

    def cell_uv(self, col, row):
        return self.u0 + (np.asarray(col) + 0.5) * self.cell, self.v0 + (np.asarray(row) + 0.5) * self.cell

    def uv_cell(self, u, v):
        return (np.asarray(u) - self.u0) / self.cell - 0.5, (np.asarray(v) - self.v0) / self.cell - 0.5

    def domain(self, u, v):
        return np.ones(np.shape(u), bool)


class Plane(Surface):
    def __init__(self, name, u0, u1, v0, v1, origin, eu, ev, normal, cell, domain=None, albedo=0.72):
        super().__init__(name, u0, u1, v0, v1, cell)
        self.origin, self.eu, self.ev, self.n = (np.array(a, float) for a in (origin, eu, ev, normal))
        self._domain = domain
        self.material_albedo = albedo

    def world(self, u, v):
        return self.origin + np.asarray(u)[..., None] * self.eu + np.asarray(v)[..., None] * self.ev

    def normal(self, u, v):
        return np.broadcast_to(self.n, np.shape(u) + (3,)).copy()

    def frame(self, u, v):
        s = np.shape(u) + (3,)
        return np.broadcast_to(self.eu, s), np.broadcast_to(self.ev, s)

    def to_uv(self, P):
        d = np.asarray(P) - self.origin
        return d @ self.eu, d @ self.ev

    def domain(self, u, v):
        return np.ones(np.shape(u), bool) if self._domain is None else self._domain(np.asarray(u), np.asarray(v))


class Lathe(Surface):
    """Surface of revolution about a vertical axis through (x0, y0); u = angle x mean
    radius (a length), v = height. The seam sits behind the object, away from the eye."""

    def __init__(self, name, x0, y0, z0, z1, radius, rmean, eye, cell, albedo=0.72):
        circ = 2 * math.pi * rmean
        super().__init__(name, 0.0, circ, z0, z1, cell)
        self.x0, self.y0, self.r, self.rmean = x0, y0, radius, rmean
        self.theta_front = math.atan2(eye[1] - y0, eye[0] - x0)
        self.material_albedo = albedo

    def _theta(self, u):
        return self.theta_front + math.pi + np.asarray(u) / self.rmean     # seam behind

    def _dr(self, z, h=1e-4):
        return (self.r(np.asarray(z) + h) - self.r(np.asarray(z) - h)) / (2 * h)

    def world(self, u, v):
        th, r = self._theta(u), self.r(np.asarray(v, float))
        return np.stack([self.x0 + r * np.cos(th), self.y0 + r * np.sin(th), np.broadcast_to(v, np.shape(th))], -1)

    def normal(self, u, v):
        th, dr = self._theta(u), self._dr(v)
        n = np.stack([np.cos(th), np.sin(th), -np.broadcast_to(dr, np.shape(th))], -1)
        return n / np.linalg.norm(n, axis=-1, keepdims=True)

    def frame(self, u, v):
        th, dr = self._theta(u), self._dr(v)
        eu = np.stack([-np.sin(th), np.cos(th), np.zeros_like(th)], -1)
        ev = np.stack([dr * np.cos(th), dr * np.sin(th), np.ones_like(th)], -1)
        return eu, ev / np.linalg.norm(ev, axis=-1, keepdims=True)


class Radial(Surface):
    """A closed object seen mostly from one side, mapped by the Lambert equal-area
    projection about the direction toward the camera. Each grid cell is a direction
    from `center`; its surface point is the outermost hit of a ray cast inward along it
    (an object-only BVH), so cavities open to the outside are reached at their floor."""

    def __init__(self, name, center, toward, rbar, theta_max, cell, bvh_cast, normal_fn=None, albedo=0.72,
                 right_hint=(1.0, 0.0, 0.0), far=2.5):
        ext = rbar * 2 * math.sin(theta_max / 2)
        super().__init__(name, -ext, ext, -ext, ext, cell)
        self.center = np.asarray(center, float)
        v = np.asarray(toward, float) - self.center
        self.vdir = v / np.linalg.norm(v)
        a = np.asarray(right_hint, float) - np.dot(right_hint, self.vdir) * self.vdir
        self.a = a / np.linalg.norm(a)
        self.b = np.cross(self.vdir, self.a)
        self.rbar, self.theta_max = rbar, theta_max
        self.material_albedo = albedo
        uu, vv = self.centers(1)
        rho = np.hypot(uu, vv) / rbar
        inside = rho < 2 * math.sin(theta_max / 2)
        th = 2 * np.arcsin(np.clip(rho / 2, 0, 1))
        ph = np.arctan2(vv, uu)
        d = (np.cos(th)[..., None] * self.vdir + np.sin(th)[..., None] *
             (np.cos(ph)[..., None] * self.a + np.sin(ph)[..., None] * self.b))
        origins = self.center + d * far
        dist, hit, normals = bvh_cast(np.ascontiguousarray(origins.reshape(-1, 3)),
                                      np.ascontiguousarray((-d).reshape(-1, 3)), 2 * far)
        dist, hit = dist.reshape(uu.shape), hit.reshape(uu.shape)
        valid = inside & (hit >= 0)
        P = origins - d * np.where(np.isfinite(dist), dist, 0)[..., None]
        N = normals.reshape(uu.shape + (3,))
        N = np.where((np.sum(N * d, -1) < 0)[..., None], -N, N)        # outward, toward the ray's origin
        if normal_fn is not None:
            Ns = normal_fn(P)
            N = np.where(valid[..., None], Ns, N)
        self.P, self.N = P, N
        self.valid = binary_erosion(valid, iterations=1)
        dPu = np.gradient(P, axis=1) / cell
        dPv = np.gradient(P, axis=0) / cell
        self.dPu, self.dPv = dPu, dPv
        area = np.linalg.norm(np.cross(dPu, dPv), axis=-1)
        self.area_scale = area                                     # surface area per map area

    def _interp(self, grid, u, v):
        c, r = self.uv_cell(u, v)
        c = np.asarray(c, float)
        r = np.asarray(r, float)
        return np.stack([map_coordinates(grid[..., k], [r.ravel(), c.ravel()], order=1, mode='nearest').reshape(c.shape)
                         for k in range(grid.shape[-1])], -1)

    def world(self, u, v):
        return self._interp(self.P, u, v)

    def normal(self, u, v):
        n = self._interp(self.N, u, v)
        return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)

    def frame(self, u, v):
        eu = self._interp(self.dPu, u, v)
        ev = self._interp(self.dPv, u, v)
        return (eu / np.maximum(np.linalg.norm(eu, axis=-1, keepdims=True), 1e-9),
                ev / np.maximum(np.linalg.norm(ev, axis=-1, keepdims=True), 1e-9))

    def domain(self, u, v):
        c, r = self.uv_cell(u, v)
        ci = np.clip(np.rint(c).astype(int), 0, self.nu - 1)
        ri = np.clip(np.rint(r).astype(int), 0, self.nv - 1)
        return self.valid[ri, ci]
