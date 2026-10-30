"""Scene accumulation and small geometry helpers for the girders generator."""

from __future__ import annotations

import math

import numpy as np

from .profiles import MATERIALS, PROFILES


def _v(*args):
    return np.asarray(args, dtype=float)


def normalize(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def frame(p, x, z):
    """Column-major 4x4 transform: origin p, local +X along x, local Z z-ish.

    The 16 floats are returned in column-major order (SCHEMA.md), i.e.
    columns 0..3 of the 4x4 matrix.
    """
    x = normalize(np.asarray(x, dtype=float))
    z = np.asarray(z, dtype=float)
    z = z - np.dot(z, x) * x
    z = normalize(z)
    y = np.cross(z, x)
    return [
        x[0], x[1], x[2], 0.0,
        y[0], y[1], y[2], 0.0,
        z[0], z[1], z[2], 0.0,
        p[0], p[1], p[2], 1.0,
    ]


def beam_local(a, b):
    """Local frame for a beam running a->b; local Z stays world-up-ish."""
    x = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    n = np.linalg.norm(x)
    if n < 1e-12:
        return None, 0.0
    x = x / n
    # For vertical beams roll 0 puts the web along world X (SCHEMA.md), which
    # this frame already does: z is derived from world up.
    return frame(a, x, _v(0.0, 0.0, 1.0)), n


class SceneBuilder:
    """Accumulates blocks, beams, details and groups, then emits a scene dict."""

    def __init__(self, seed, preset, params):
        self.seed = int(seed)
        self.preset = preset
        self.params = params
        self.blocks = []
        self.beams = []
        self.details = []
        self.groups = [{"id": 0, "name": "site", "parent": None}]
        self._group_ids = [0]

    # ---------------------------------------------------------------- groups
    def group(self, name, parent=0):
        gid = self._group_ids[-1] + 1
        self._group_ids.append(gid)
        self.groups.append({"id": gid, "name": name, "parent": parent})
        return gid

    # ----------------------------------------------------------------- parts
    def add_block(self, center, size, material="concrete", tags=None, group=0, yaw=0.0):
        self.blocks.append({
            "id": len(self.blocks),
            "center": [float(c) for c in center],
            "size": [float(s) for s in size],
            "yaw": float(yaw),
            "material": material,
            "tags": list(tags or []),
            "group": group,
        })
        return len(self.blocks) - 1

    def add_beam(self, a, b, profile, material="steel", tags=None, group=0, roll=0.0):
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        self.beams.append({
            "id": len(self.beams),
            "a": [float(v) for v in a],
            "b": [float(v) for v in b],
            "profile": profile,
            "roll": float(roll),
            "material": material,
            "tags": list(tags or []),
            "group": group,
        })
        return len(self.beams) - 1

    def add_detail(self, kind, transform, size, material="steel", group=0):
        self.details.append({
            "kind": kind,
            "transform": [float(v) for v in transform],
            "size": [float(s) for s in size],
            "material": material,
            "group": group,
        })
        return len(self.details) - 1

    def add_detail_at(self, kind, p, x, z, size, material="steel", group=0):
        return self.add_detail(kind, frame(p, x, z), size, material, group)

    # ---------------------------------------------------------------- stats
    def bounds(self, pad=2.0):
        if not self.blocks and not self.beams:
            mn = _v(-10.0, -10.0, 0.0)
            mx = _v(10.0, 10.0, 10.0)
        else:
            pts = []
            for blk in self.blocks:
                c = np.asarray(blk["center"])
                s = np.asarray(blk["size"]) / 2.0
                pts.append(c - s)
                pts.append(c + s)
            for bm in self.beams:
                pts.append(np.asarray(bm["a"]))
                pts.append(np.asarray(bm["b"]))
            allp = np.asarray(pts)
            mn, mx = allp.min(axis=0), allp.max(axis=0)
        mn = mn - pad
        mx = mx + pad
        mn[2] = min(mn[2], 0.0)
        return mn, mx

    def camera_hints(self, mn, mx):
        """A worm's-eye, an orthographic axon and a mid-span detail view."""
        center = (np.asarray(mn) + np.asarray(mx)) / 2.0
        extent = np.asarray(mx) - np.asarray(mn)
        ground = 0.0
        if self.preset == "bridge-field":
            worm_location = [
                float(center[0] + max(55.0, extent[1] * 0.82)),
                float(mn[1] + extent[1] * .20),
                float(ground + 1.9),
            ]
            worm_target = [
                float(center[0]), float(center[1]), float(mx[2] * 0.48),
            ]
            worm_lens = 42
        else:
            worm_location = [
                float(center[0] + 3.0), float(mn[1] - 5.0),
                float(ground + 1.9),
            ]
            worm_target = [
                float(center[0]), float(center[1]), float(mx[2] * 0.55),
            ]
            worm_lens = 26
        if extent[0] >= extent[1]:
            axon_location = [
                float(center[0] - extent[0] * 0.45),
                float(center[1] - extent[1] * 1.15),
                float(mx[2] + extent[2] * 0.72),
            ]
        else:
            axon_location = [
                float(center[0] + extent[0] * 1.15),
                float(center[1] - extent[1] * 0.45),
                float(mx[2] + extent[2] * 0.72),
            ]
        hints = [
            {
                "name": "worm",
                "location": worm_location,
                "target": worm_target,
                "lens_mm": worm_lens,
            },
            {
                "name": "axon",
                "location": axon_location,
                "target": [float(center[0]), float(center[1]), float(mx[2] * 0.42)],
                "lens_mm": 70,
                "ortho_scale": float(max(extent[0], extent[1], extent[2] * 1.55) * 1.18),
            },
            {
                "name": "detail",
                "location": [float(center[0] + 10.0), float(center[1] - 14.0), float(mx[2] * 0.5)],
                "target": [float(center[0]), float(center[1]), float(mx[2] * 0.45)],
                "lens_mm": 85,
            },
        ]
        return hints

    def scene(self, version="0.1.0"):
        mn, mx = self.bounds()
        return {
            "format": "girders-scene-1",
            "seed": self.seed,
            "generator": {
                "name": "girders",
                "version": version,
                "params": self.params,
            },
            "bounds": {
                "min": [float(v) for v in mn],
                "max": [float(v) for v in mx],
            },
            "profiles": PROFILES,
            "materials": MATERIALS,
            "blocks": self.blocks,
            "beams": self.beams,
            "details": self.details,
            "groups": self.groups,
            "camera_hints": self.camera_hints(mn, mx),
            "stats": {
                "blocks": len(self.blocks),
                "beams": len(self.beams),
                "details": len(self.details),
            },
        }


def polar(theta, r, z=0.0):
    return _v(r * math.cos(theta), r * math.sin(theta), z)
