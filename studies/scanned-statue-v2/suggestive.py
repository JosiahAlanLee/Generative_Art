"""Suggestive contours (DeCarlo, Finkelstein, Rusinkiewicz & Santella 2003).

Zero crossings of radial curvature k_r, kept where its derivative along the
projected view direction is positive and strong. They draw the folds a contour
would show from a nearby viewpoint: eye sockets, the line of the lips, the
crease under a chin. Per-face shape operators follow Rusinkiewicz (2004),
estimated from smoothed vertex normals because the scan is noisy at the
triangle scale.
"""
import numpy as np
import meshlines


def face_shape_operators(V, F, vn):
    """Least-squares symmetric shape operator per face, in a face-local 2D frame."""
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n0, n1, n2 = vn[F[:, 0]], vn[F[:, 1]], vn[F[:, 2]]
    fn = np.cross(p1 - p0, p2 - p0); area = np.linalg.norm(fn, axis=1) / 2
    fn /= np.maximum(2 * area[:, None], 1e-15)
    e1 = p1 - p0; e1 /= np.maximum(np.linalg.norm(e1, axis=1)[:, None], 1e-15)
    e2 = np.cross(fn, e1)
    edges = [(p1 - p0, n1 - n0), (p2 - p1, n2 - n1), (p0 - p2, n0 - n2)]
    A = np.zeros((len(F), 3, 3)); b = np.zeros((len(F), 3))
    for de, dn in edges:
        u = (de * e1).sum(1); v = (de * e2).sum(1)
        nu = (dn * e1).sum(1); nv = (dn * e2).sum(1)
        # [u v 0; 0 u v] [a b c]^T = [nu nv]^T
        rows = [(np.stack([u, v, 0 * u], 1), nu), (np.stack([0 * u, u, v], 1), nv)]
        for r, rhs in rows:
            A += r[:, :, None] * r[:, None, :]; b += r * rhs[:, None]
    A += np.eye(3)[None] * 1e-12
    abc = np.linalg.solve(A, b[:, :, None])[:, :, 0]
    return abc, e1, e2, fn, area


def suggestive_contours(mesh, eye, vn, min_strength=.3, max_cos=.94):
    """Return list of (points, normals, strength) chains on the mesh.

    min_strength: threshold on D_w k_r / |w| scaled by the mesh's median edge
    length squared (unitless). max_cos: drop points whose view direction is within
    acos(max_cos) of the normal (DeCarlo's theta_c), where k_r is unstable.
    """
    V, F = mesh.vertices, mesh.faces
    abc, e1, e2, fn, area = face_shape_operators(V, F, vn)
    c = V[F].mean(1); view = eye - c; view /= np.linalg.norm(view, axis=1)[:, None]
    ndotv = (view * fn).sum(1)
    w = view - ndotv[:, None] * fn
    wu = (w * e1).sum(1); wv = (w * e2).sum(1); wl = np.hypot(wu, wv)
    hu = wu / np.maximum(wl, 1e-12); hv = wv / np.maximum(wl, 1e-12)
    # dn = S dp with outward normals: convex (sphere-like) curvature is positive,
    # DeCarlo's convention, under which D_w(n.v) = k_r |w|^2.
    kr_face = abc[:, 0] * hu * hu + 2 * abc[:, 1] * hu * hv + abc[:, 2] * hv * hv
    nv = len(V)
    wsum = np.bincount(F.ravel(), np.repeat(area, 3), nv)
    kr = np.bincount(F.ravel(), np.repeat(kr_face * area, 3), nv) / np.maximum(wsum, 1e-15)
    # Gradient of the piecewise-linear vertex k_r on each face, dotted with w.
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    g = np.zeros_like(p0)
    for (i, a, b) in ((0, p1, p2), (1, p2, p0), (2, p0, p1)):
        g += kr[F[:, i]][:, None] * np.cross(fn, b - a)
    g /= np.maximum(2 * area[:, None], 1e-15)
    dwkr_face = (g * w).sum(1) / np.maximum(wl, 1e-12)
    dwkr = np.bincount(F.ravel(), np.repeat(dwkr_face * area, 3), nv) / np.maximum(wsum, 1e-15)
    vview = eye - V; vview /= np.linalg.norm(vview, axis=1)[:, None]
    vndotv = (vview * vn).sum(1)
    edge = np.median(np.linalg.norm(p1 - p0, axis=1))
    res = meshlines.level_set(F, kr, nv)
    if res is None:
        return [], dict(edge=edge)
    ea, eb, t, chains = res
    P = V[ea] + t[:, None] * (V[eb] - V[ea])
    N = vn[ea] + t[:, None] * (vn[eb] - vn[ea]); N /= np.linalg.norm(N, axis=1)[:, None]
    D = dwkr[ea] + t * (dwkr[eb] - dwkr[ea])
    C = vndotv[ea] + t * (vndotv[eb] - vndotv[ea])
    strength = D * edge * edge
    ok = (strength > min_strength * 1e-3) & (C > 0) & (C < max_cos)
    out = []
    for ch in chains:
        out.append((P[ch], N[ch], ok[ch].astype(float), strength[ch]))
    return out, dict(edge=edge, kr_range=(float(np.percentile(kr, 5)), float(np.percentile(kr, 95))),
                     strength_pct=[float(np.percentile(strength[C > 0], q)) for q in (50, 90, 99)])
