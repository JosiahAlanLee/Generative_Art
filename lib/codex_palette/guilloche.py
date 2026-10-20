"""Guilloché: rose-engine rosettes, trochoids, reeded rims and wave bands.

Security engravers turned these patterns on rose engines and geometric chucks
so that a note, bond or seal could not be copied by hand. The constructions are
the standard ones (see Holtzapffel, Turning and Mechanical Manipulation, vol. V,
1884, and R. Craig, "The Mechanical Drawing of Cycloids, the Geometric Chuck",
Bridges 2006):

    rose-engine pass:  r(t) = r0 + a * cos(n t + phase)
    hypotrochoid:      x = (R - r) cos t + d cos((R - r) t / r),  y = (R - r) sin t - d sin((R - r) t / r)
    epitrochoid:       x = (R + r) cos t - d cos((R + r) t / r),  y = (R + r) sin t - d sin((R + r) t / r)

A trochoid closes after ``r / gcd(R, r)`` turns for integer radii. A wave band
winds ``strands`` phase-shifted sine waves between two envelopes along a path.
Every function returns closed or open millimetre polylines; nothing is filled.
"""
from math import gcd

import numpy as np

__all__ = ["rose_pass", "rosette", "trochoid", "reeded_rim", "band", "path_band"]


def _samples(length_mm, per_mm=4, minimum=180):
    return max(minimum, int(length_mm * per_mm))


def rose_pass(c, r0, amp, lobes, phase=0.0):
    t = np.linspace(0, 2 * np.pi, _samples(2 * np.pi * (r0 + amp) * (1 + lobes / 20)) + 1)
    r = r0 + amp * np.cos(lobes * t + phase)
    return np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])


def rosette(c, r_inner, r_outer, passes, lobes, amp, twist):
    """``passes`` rose-engine passes stepped outward, each turned by ``twist`` radians."""
    out = []
    for k in range(passes):
        f = k / max(passes - 1, 1)
        out.append(rose_pass(c, r_inner + f * (r_outer - r_inner), amp, lobes, k * twist))
    return out


def trochoid(c, R, r, d, kind="hypo", scale=1.0):
    """Closed integer-radius trochoid scaled to ``scale`` millimetres per unit."""
    turns = r // gcd(R, r)
    t = np.linspace(0, 2 * np.pi * turns, _samples(2 * np.pi * (R + d) * scale * turns, 3) + 1)
    if kind == "hypo":
        k = (R - r) / r
        x = (R - r) * np.cos(t) + d * np.cos(k * t)
        y = (R - r) * np.sin(t) - d * np.sin(k * t)
    else:
        k = (R + r) / r
        x = (R + r) * np.cos(t) - d * np.cos(k * t)
        y = (R + r) * np.sin(t) - d * np.sin(k * t)
    return np.column_stack([c[0] + scale * x, c[1] + scale * y])


def reeded_rim(c, r, count, depth=.9):
    """A coin's milled edge: ``count`` radial reeds just inside radius ``r``."""
    a = np.linspace(0, 2 * np.pi, count, endpoint=False) + np.pi / 2
    return [np.array([[c[0] + (r - depth) * np.cos(t), c[1] + (r - depth) * np.sin(t)],
                      [c[0] + r * np.cos(t), c[1] + r * np.sin(t)]]) for t in a]


def band(spine, half_width, crests, strands, phase0=0.0, envelope=.18):
    """Sine strands between envelopes along ``spine`` (N×2); ``crests`` waves end to end."""
    p = np.asarray(spine, float)
    seg = np.hypot(*np.diff(p, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    u = s / s[-1]
    tangent = np.gradient(p, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-9)
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    # Taper to the ends so a band leaves its station cleanly.
    taper = np.sin(np.pi * np.clip(u, 0, 1)) ** .35
    width = half_width * taper * (1 + envelope * np.cos(2 * np.pi * crests * u / 2))
    out = []
    for k in range(strands):
        ph = phase0 + 2 * np.pi * k / strands
        out.append(p + (width * np.sin(2 * np.pi * crests * u + ph))[:, None] * normal)
    return out


def path_band(a, b, bow, half_width, crests, strands, phase0=0.0, samples=None):
    """A band on a quadratic curve from ``a`` to ``b`` bowed toward ``bow``."""
    a, b, bow = (np.asarray(v, float) for v in (a, b, bow))
    n = samples or _samples(np.hypot(*(b - a)) * 1.3, 8)
    t = np.linspace(0, 1, n)[:, None]
    spine = (1 - t) ** 2 * a + 2 * (1 - t) * t * bow + t ** 2 * b
    return band(spine, half_width, crests, strands, phase0)
