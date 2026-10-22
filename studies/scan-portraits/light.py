"""Portrait light: a soft key, an open fill and ambient occlusion, ray traced.

The rig is the studio one an engraver's sitter would have had: a large key
window high to one side, a weak fill from near the viewer, and the room's
ambient light, reduced wherever the form closes over itself (eye sockets,
nostrils, the corners of the mouth, under the chin). Each term is stored
separately per vertex, so the tone curve can be changed without re-tracing.

Ray queries use Scanned Statue v2's BVH kernels (raycore.trace), unchanged.
"""
import math
import sys
from pathlib import Path

import numpy as np
from numba import njit, prange

STATUE = Path(__file__).resolve().parents[1] / 'scanned-statue-v2'
if str(STATUE) not in sys.path:
    sys.path.append(str(STATUE))
import raycore  # noqa: E402


def frame(direction):
    d = np.asarray(direction, float); d = d / np.linalg.norm(d)
    a = np.array([0., 0., 1.]) if abs(d[2]) < .9 else np.array([1., 0., 0.])
    t = np.cross(a, d); t /= np.linalg.norm(t)
    return d, t, np.cross(d, t)


def direction(azimuth, elevation):
    """Unit vector from the sitter toward a light or camera. Azimuth 0 is in
    front of the sitter (-y); positive azimuth swings toward +x."""
    a, e = math.radians(azimuth), math.radians(elevation)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])


def area_samples(center, toward, distance, size, k):
    """k x k cell-centred points on a square light of side `size`, facing the head."""
    d, t, b = frame(toward)
    c = np.asarray(center, float) + d * distance
    u = ((np.arange(k) + .5) / k - .5) * size
    return np.array([c + x * t + y * b for x in u for y in u])


def hemisphere(k):
    """Deterministic stratified (u, v) pairs for cosine-weighted directions,
    as raycore.hemi_pattern, with a second golden-ratio stride for the angle."""
    return np.column_stack([(np.arange(k) + .5) / k, (np.arange(k) * .61803398875) % 1])


@njit(cache=True)
def _basis(n):
    ax = np.array([0., 0., 1.])
    if abs(n[2]) > .9:
        ax = np.array([1., 0., 0.])
    t = np.cross(ax, n); t /= math.sqrt(t[0] ** 2 + t[1] ** 2 + t[2] ** 2)
    return t, np.cross(n, t)


@njit(cache=True, parallel=True)
def shade(P, N, key_points, key_center, fill_dir, ao_uv, ao_radius, lift, blo, bhi, nodes, v0, e1, e2):
    """Per point: (key, fill, occlusion).

    key: mean over the key light's samples of cos(theta), zero when the sample
    is shadowed, scaled by (distance to the light's centre / sample distance)^2
    so the fall-off across the head is physical but the head itself reads 1.0.
    fill: cos(theta) to the fill direction, unshadowed (a large, near source).
    occlusion: mean of (1 - d / ao_radius) over cosine-weighted rays that hit
    within ao_radius; 0 is open, 1 is closed.
    """
    n = len(P)
    out = np.zeros((n, 3))
    for i in prange(n):
        p = P[i]; nn = N[i]
        org = p + nn * lift
        ref = math.sqrt(((key_center - p) ** 2).sum())
        k = 0.0
        for j in range(len(key_points)):
            d = key_points[j] - org
            dist = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]); d = d / dist
            c = nn[0] * d[0] + nn[1] * d[1] + nn[2] * d[2]
            if c <= 0.0:
                continue
            _, h = raycore.trace(org, d, 1e-6, dist, True, blo, bhi, nodes, v0, e1, e2)
            if h < 0:
                k += c * (ref / dist) ** 2
        out[i, 0] = k / len(key_points)
        out[i, 1] = max(0.0, nn[0] * fill_dir[0] + nn[1] * fill_dir[1] + nn[2] * fill_dir[2])
        t, b = _basis(nn)
        occ = 0.0
        for j in range(len(ao_uv)):
            r = math.sqrt(ao_uv[j, 0]); th = 2 * math.pi * ao_uv[j, 1]
            hd = r * math.cos(th) * t + r * math.sin(th) * b + math.sqrt(1 - ao_uv[j, 0]) * nn
            dd, hh = raycore.trace(org, hd, 1e-6, ao_radius, False, blo, bhi, nodes, v0, e1, e2)
            if hh >= 0:
                occ += 1 - dd / ao_radius
        out[i, 2] = occ / len(ao_uv)
    return out


def combine(terms, rig):
    """Illumination in [0, 1] from the stored terms and the rig's weights."""
    key, fill, occ = terms[..., 0], terms[..., 1], terms[..., 2]
    open_ = 1 - rig['occlusion'] * occ
    return np.clip(rig['ambient'] * open_ + rig['key'] * key + rig['fill'] * fill * open_, 0, 1)
