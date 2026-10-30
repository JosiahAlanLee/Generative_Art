"""Axonometric line-drawing previews of girders scenes (no Blender).

Renders a scene to PNG with matplotlib: blocks as filled prisms (top face
plus silhouette), beams as lines coloured by material, so a structure can be
judged before the Blender builder runs.  Uses the Agg backend and a single
LineCollection, so medium scenes (~10k beams) render in a few seconds.
"""

from __future__ import annotations

import numpy as np


def axonometric(points, theta=20.0, phi=58.0):
    """Project 3D points to 2D: yaw about Z by theta, tilt by phi, drop depth.

    Returns (screen_x, screen_y) with screen_y up, in metres.  theta and phi
    are degrees.
    """
    t, f = np.radians(theta), np.radians(phi)
    ct, st, cf, sf = np.cos(t), np.sin(t), np.cos(f), np.sin(f)
    x = points[:, 0] * ct - points[:, 1] * st
    y = points[:, 0] * st + points[:, 1] * ct
    y2 = y * cf - points[:, 2] * sf
    return x, -y2


def _material_color(mat):
    return {
        "concrete": "#b9b2a4",
        "steel": "#6f7d8c",
        "steel_painted": "#c96f4a",
        "rust": "#a35c34",
        "glass": "#a8c4d4",
        "grating": "#4e5a63",
        "accent": "#d8a13c",
    }.get(mat, "#8899aa")


def _depth_shade(color, z, zmin, zmax):
    """Darken lower members a touch for a soft ambient-occlusion cue."""
    if zmax <= zmin:
        return color
    f = 0.55 + 0.45 * (z - zmin) / (zmax - zmin)
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r * f):02x}{int(g * f):02x}{int(b * f):02x}"


def render(scene, path, width_px=2200, theta=20.0, phi=58.0, dpi=150):
    """Draw the scene as an axonometric line drawing and save a PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PolyCollection

    beams = scene["beams"]
    blocks = scene["blocks"]
    bounds = scene["bounds"]

    fig = plt.figure(figsize=(width_px / dpi, width_px / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#f4f1ea")

    # ---- blocks: top face + silhouette
    if blocks:
        bc = np.array([b["center"] for b in blocks])
        bs = np.array([b["size"] for b in blocks])
        zs = bc[:, 2]
        tops, polys, cols = [], [], []
        for i, b in enumerate(blocks):
            x, y, z = bc[i]
            sx, sy, sz = bs[i]
            yaw = b.get("yaw", 0.0)
            cy, syw = np.cos(yaw), np.sin(yaw)
            corners = []
            for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                lx, ly = dx * sx / 2.0, dy * sy / 2.0
                corners.append([x + lx * cy - ly * syw, y + lx * syw + ly * cy, z + sz / 2.0])
            corners = np.array(corners)
            px, py = axonometric(corners, theta, phi)
            tops.append(px)
            tops.append(py)
            polys.append(np.column_stack([px, py]))
            cols.append(_material_color(b.get("material", "concrete")))
        if polys:
            pc = PolyCollection(polys, facecolors=cols, edgecolors="#8a8374",
                                linewidths=0.3, alpha=0.85)
            ax.add_collection(pc)

    # ---- beams as one line collection, shaded by height
    if beams:
        ba = np.array([b["a"] for b in beams])
        bb = np.array([b["b"] for b in beams])
        zmin, zmax = float(bounds["min"][2]), float(bounds["max"][2])
        segs = []
        colors = []
        for i in range(len(beams)):
            a = ba[i]
            c = bb[i]
            p1 = axonometric(a[None, :], theta, phi)
            p2 = axonometric(c[None, :], theta, phi)
            segs.append([(p1[0][0], p1[1][0]), (p2[0][0], p2[1][0])])
            mat = beams[i].get("material", "steel")
            base = _material_color(mat)
            colors.append(_depth_shade(base, (a[2] + c[2]) / 2.0, zmin, zmax))
        lc = LineCollection(segs, colors=colors, linewidths=0.45, alpha=0.9)
        ax.add_collection(lc)

    mn = np.array(bounds["min"])
    mx = np.array(bounds["max"])
    corners = np.array([[mn[0], mn[1], mn[2]], [mn[0], mn[1], mx[2]],
                        [mx[0], mn[1], mn[2]], [mx[0], mn[1], mx[2]],
                        [mn[0], mx[1], mn[2]], [mn[0], mx[1], mx[2]],
                        [mx[0], mx[1], mn[2]], [mx[0], mx[1], mx[2]]])
    px, py = axonometric(corners, theta, phi)
    pad = max(px.max() - px.min(), py.max() - py.min()) * 0.03
    ax.set_xlim(px.min() - pad, px.max() + pad)
    ax.set_ylim(py.min() - pad, py.max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")

    path = str(path)
    fig.savefig(path, dpi=dpi, facecolor="#f4f1ea")
    plt.close(fig)
    return path
