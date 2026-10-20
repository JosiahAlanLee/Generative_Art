"""The corridor's rough surfaces as flat atlases in world units, and the traced light on them.

Every culture runs on one of these grids, so a cell is the same size in the scene
wherever it is; the camera, not the simulation, makes the far end small. The light is
Sol's model (hallway_sol.py) evaluated at each surface cell instead of each pixel.
"""
from __future__ import annotations

import os

os.environ.setdefault('NUMBA_NUM_THREADS', '4')   # hallway_sol calls set_num_threads(4)

import math

import numpy as np
from numba import njit, prange
from scipy.ndimage import median_filter, zoom

import hallway_sol as hs

hs.scene()
BVH = hs.build_bvh()
CHECKS = hs.validate_queries(BVH)
BLO, BHI, NODES, TRIS, MATS, NORMALS = BVH
cast, direct, hemisphere = hs.cast, hs.direct, hs.hemisphere

EYE, F, R, U = hs.EYE, hs.F, hs.R, hs.U
FOCAL, CX, CY, W, H = hs.FOCAL, hs.CX, hs.CY, hs.W, hs.H
CELL = 0.0125                      # culture cell, scene units (80 cells per unit)
VAULT_R, VAULT_Z, VAULT_N = 2.6, 3.6, 28
DTH = math.pi / VAULT_N
Y0, Y1 = -0.5, 21.7                # corridor floor/walls/vault run to the rear wall's face


def project(P):
    """World points (..., 3) -> screen x, y and camera depth."""
    q = np.asarray(P) - EYE
    z = q @ F
    return CX + FOCAL * (q @ R) / z, CY - FOCAL * (q @ U) / z, z


def screen_jacobian(P, e_u, e_v):
    """d(screen)/d(u, v) at world points P for surface directions e_u, e_v: (..., 2, 2),
    columns = screen motion per unit u and per unit v."""
    q = np.asarray(P) - EYE
    z = (q @ F)[..., None]
    qr, qu = (q @ R)[..., None], (q @ U)[..., None]
    dsx = FOCAL * (R * z - qr * F) / z ** 2          # (..., 3)
    dsy = -FOCAL * (U * z - qu * F) / z ** 2
    J = np.empty(q.shape[:-1] + (2, 2))
    J[..., 0, 0] = (dsx * e_u).sum(-1); J[..., 0, 1] = (dsx * e_v).sum(-1)
    J[..., 1, 0] = (dsy * e_u).sum(-1); J[..., 1, 1] = (dsy * e_v).sum(-1)
    return J


class Surface:
    """A rectangle (u0..u1, v0..v1) in scene units mapped onto part of the corridor."""
    kind = 'plane'

    def __init__(self, name, u0, u1, v0, v1):
        self.name = name
        self.u0, self.v0 = u0, v0
        self.nu = int(math.ceil((u1 - u0) / CELL))
        self.nv = int(math.ceil((v1 - v0) / CELL))
        self.u1, self.v1 = u0 + self.nu * CELL, v0 + self.nv * CELL

    def centers(self, step=1):
        u = self.u0 + (np.arange(0, self.nu, step) + 0.5 * step) * CELL
        v = self.v0 + (np.arange(0, self.nv, step) + 0.5 * step) * CELL
        return np.meshgrid(u, v)                       # (nv', nu') each

    def cell_uv(self, col, row):
        return self.u0 + (np.asarray(col) + 0.5) * CELL, self.v0 + (np.asarray(row) + 0.5) * CELL

    def uv_cell(self, u, v):
        return (np.asarray(u) - self.u0) / CELL - 0.5, (np.asarray(v) - self.v0) / CELL - 0.5

    def domain(self, u, v):
        return np.ones(np.shape(u), bool)


class Plane(Surface):
    def __init__(self, name, u0, u1, v0, v1, origin, eu, ev, normal):
        super().__init__(name, u0, u1, v0, v1)
        self.origin, self.eu, self.ev, self.n = (np.array(a, float) for a in (origin, eu, ev, normal))

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


class Floor(Plane):
    def __init__(self):
        super().__init__('floor', -2.6, 2.6, Y0, Y1, (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))


class WallLeft(Plane):
    def __init__(self):
        super().__init__('wall_left', Y0, Y1, 0.0, 3.6, (-2.6, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))

    def domain(self, u, v):
        # the side doorway: jambs 4.8..7.2, semicircular head on z = 2.1, radius 1.2
        head = 2.1 + np.sqrt(np.maximum(0, 1.2 ** 2 - (np.asarray(u) - 6.0) ** 2))
        return ~((u > 4.8) & (u < 7.2) & (v < head))


class WallRight(Plane):
    def __init__(self):
        super().__init__('wall_right', Y0, Y1, 0.0, 3.6, (2.6, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0))


class Rear(Plane):
    def __init__(self):
        super().__init__('rear_wall', -2.6, 2.6, 0.0, 6.2, (0, 21.7, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))

    def domain(self, u, v):
        u, v = np.asarray(u), np.asarray(v)
        under_vault = v <= VAULT_Z + np.sqrt(np.maximum(0, VAULT_R ** 2 - u ** 2))
        door = (np.abs(u) < 0.88) & (v < 2.0 + np.sqrt(np.maximum(0, 0.88 ** 2 - u ** 2)))
        return under_vault & ~door


class Vault(Surface):
    """Barrel vault, u = y along the corridor, v = arc length from the right springing.
    Points are placed on Sol's 28 facets exactly, so they sit on the drawn surface."""
    kind = 'vault'

    def __init__(self):
        super().__init__('vault', Y0, Y1, 0.0, math.pi * VAULT_R)

    def _facet(self, v):
        th = np.clip(np.asarray(v) / VAULT_R, 0, math.pi - 1e-9)
        k = np.clip((th // DTH).astype(int), 0, VAULT_N - 1)
        return k, th / DTH - k

    def world(self, u, v):
        k, t = self._facet(v)
        a, b = k * DTH, (k + 1) * DTH
        x = (1 - t) * np.cos(a) + t * np.cos(b)
        z = (1 - t) * np.sin(a) + t * np.sin(b)
        return np.stack([VAULT_R * x, np.broadcast_to(u, np.shape(x)), VAULT_Z + VAULT_R * z], -1)

    def normal(self, u, v):
        k, _ = self._facet(v)
        m = (k + 0.5) * DTH
        return np.stack([-np.cos(m), np.zeros_like(m), -np.sin(m)], -1)

    def frame(self, u, v):
        k, _ = self._facet(v)
        a, b = k * DTH, (k + 1) * DTH
        ev = np.stack([np.cos(b) - np.cos(a), np.zeros_like(a), np.sin(b) - np.sin(a)], -1)
        ev /= np.linalg.norm(ev, axis=-1, keepdims=True)
        return np.broadcast_to(np.array([0., 1., 0.]), ev.shape), ev

    def to_uv(self, P):
        P = np.asarray(P)
        th = np.arctan2(P[..., 2] - VAULT_Z, P[..., 0])
        return P[..., 1], np.clip(th, 0, math.pi) * VAULT_R


SURFACES = [Floor(), WallLeft(), WallRight(), Vault(), Rear()]


# ----------------------------------------------------------------------------
# Sol's light model at arbitrary surface points
# ----------------------------------------------------------------------------
@njit(cache=True, parallel=True)
def _light_points(P, Nrm, light, samples, hemis, blo, bhi, nodes, tris, mats, normals):
    n = P.shape[0]
    out = np.zeros((n, 4))
    for i in prange(n):
        p = P[i]
        nn = Nrm[i]
        flat = direct(p, nn, light, blo, bhi, nodes, tris, False)
        dl = 0.
        for j in range(samples.shape[0]):
            dl += direct(p, nn, samples[j], blo, bhi, nodes, tris, True) / samples.shape[0]
        ao = 0.
        bounce = 0.
        for j in range(hemis.shape[0]):
            hdir = hemisphere(nn, hemis[j, 0], hemis[j, 1])
            dd, hh = cast(p + nn * .003, hdir, 1.10, blo, bhi, nodes, tris)
            if hh >= 0:
                ao += 1 - dd / 1.10
            if j < 4:
                dd, hh = cast(p + nn * .003, hdir, 18., blo, bhi, nodes, tris)
                if hh >= 0 and mats[hh] != 3:
                    q = p + nn * .003 + hdir * dd
                    n2 = normals[hh].copy()
                    if np.dot(n2, hdir) > 0:
                        n2 = -n2
                    albedo = .73 if mats[hh] == 0 else .36
                    bounce += direct(q, n2, light, blo, bhi, nodes, tris, True) * albedo / 4
        out[i, 0] = dl
        out[i, 1] = flat
        out[i, 2] = ao / hemis.shape[0]
        out[i, 3] = bounce
    return out


def light_samples():
    samples = np.array([hs.LIGHT + [0, dy, dz] for dy, dz in [(-.55, -.65), (-.55, .65), (.55, -.65), (.55, .65)]])
    hemis = np.column_stack([(np.arange(16) + .5) / 16, ((np.arange(16) * .61803398875) % 1)])
    return samples, hemis


def traced_from(ch, albedo=.72):
    """Sol's exposure: ambient floor with contact shading, plus direct and one bounce."""
    dl, ao, bounce = ch[..., 0], ch[..., 2], ch[..., 3]
    return np.clip(.14 * (1 - .70 * ao) + (dl + .70 * bounce) * albedo * 2.4, 0, 1)


def surface_light(s, step=2):
    """Light channels on a coarse grid (every `step` cells), upsampled to the culture grid.
    Returns dict(darkness, direct) at culture resolution."""
    uu, vv = s.centers(step)
    P = s.world(uu, vv) + s.normal(uu, vv) * .002
    Nn = s.normal(uu, vv)
    samples, hemis = light_samples()
    ch = _light_points(np.ascontiguousarray(P.reshape(-1, 3)), np.ascontiguousarray(Nn.reshape(-1, 3)),
                       hs.LIGHT.astype(float), samples, hemis, BLO, BHI, NODES, TRIS, MATS, NORMALS)
    ch = ch.reshape(uu.shape + (4,))
    traced = median_filter(traced_from(ch), size=3)
    maps = {'darkness': 1 - np.sqrt(traced), 'direct': ch[..., 0], 'flat': ch[..., 1],
            'ao': ch[..., 2], 'bounce': ch[..., 3]}
    out = {}
    for name, a in maps.items():
        if name != 'darkness':
            a = median_filter(a, size=3)
        big = zoom(a, step, order=1)[:s.nv, :s.nu]
        if big.shape != (s.nv, s.nu):                                 # pad if the zoom came up short
            big = np.pad(big, ((0, s.nv - big.shape[0]), (0, s.nu - big.shape[1])), mode='edge')
        out[name] = big.astype(np.float32)
    return out


def darkness_from(light, direct):
    """Sol's darkness for a surface with a given direct-light field (stone albedo)."""
    traced = np.clip(.14 * (1 - .70 * light['ao']) + (direct + .70 * light['bounce']) * .72 * 2.4, 0, 1)
    return 1 - np.sqrt(traced)
