"""Truss expansion: Warren / Pratt / Howe / Vierendeel / lattice bridges.

A bridge is built in local coordinates (span along local +X, deck at local
z = 0 at deck level, two side trusses at y = +- deck_w/2) and mapped into the
world through an origin + yaw rotation, so the same code serves X- and
Y-aligned spans.  Everything is expanded into individual beams (the schema
carries no aggregate objects); chords are split per panel so the Blender
builder can instance unit members along their lengths.
"""

from __future__ import annotations

import math

import numpy as np

from .scene import frame, normalize


class TrussBridge:
    def __init__(self, sb, origin, direction, deck_z, span, deck_w, depth,
                 kind, rng, group, material="steel", density=1.0,
                 density2=1.0, panels=None, panel_min=3.2, panel_max=4.6,
                 catwalk=False, cable_mast=None, sag=0.0):
        self.sb = sb
        self.origin = np.asarray(origin, dtype=float)
        self.dir = normalize(np.asarray(direction, dtype=float))
        self.deck_z = float(deck_z)
        self.span = float(span)
        self.deck_w = float(deck_w)
        self.depth = float(depth)
        self.kind = kind
        self.rng = rng
        self.group = group
        self.material = material
        self.density = density
        self.density2 = density2
        self.catwalk = catwalk
        self.cable_mast = cable_mast
        self.sag = sag

        if panels is None:
            panels = int(round(span / self.rng.uniform(panel_min, panel_max)))
        self.panels = max(4, int(panels))
        self.panel = self.span / self.panels

        # local X -> world: a rotation about world Z.
        ang = math.atan2(self.dir[1], self.dir[0])
        self.ca, self.sa = math.cos(ang), math.sin(ang)

    # ------------------------------------------------------------------ map
    def W(self, x, y, z):
        """Map local (x along span, y across, z up from deck) to world."""
        wx = self.origin[0] + x * self.ca - y * self.sa
        wy = self.origin[1] + x * self.sa + y * self.ca
        return np.array([wx, wy, self.origin[2] + z], dtype=float)

    def beam(self, l1, l2, profile, tags, roll=0.0):
        return self.sb.add_beam(self.W(*l1), self.W(*l2), profile,
                                material=self.material, tags=["bridge"] + tags,
                                group=self.group, roll=roll)

    def block(self, lc, ls, material, tags, yaw=None):
        c = self.W(*lc)
        if yaw is None:
            yaw = math.atan2(self.dir[1], self.dir[0])
        return self.sb.add_block(c, ls, material=material,
                                 tags=["bridge"] + tags, group=self.group, yaw=yaw)

    def _dir(self, v):
        v = np.asarray(v, dtype=float)
        return np.array([v[0] * self.ca - v[1] * self.sa,
                         v[0] * self.sa + v[1] * self.ca,
                         v[2]], dtype=float)

    def detail(self, kind, l, x_local, z_local, size, material="steel"):
        p = self.W(*l)
        return self.sb.add_detail(kind, frame(p, self._dir(x_local), self._dir(z_local)),
                                  size, material, self.group)

    # --------------------------------------------------------------- truss
    def chord_points(self):
        d = self.depth
        z = 0.0
        return z, d

    def _web_geometry(self):
        """Return (diagonals, verticals, end_vertical_extra) as local pairs."""
        n = self.panels
        p = self.panel
        z0, z1 = 0.0, self.depth
        diags, verts = [], []
        for k in range(n):
            b0, b1, t0, t1 = (k * p, z0), ((k + 1) * p, z0), (k * p, z1), ((k + 1) * p, z1)
            if self.kind == "warren":
                if k % 2 == 0:
                    diags.append((t0, b1))
                else:
                    diags.append((b0, t1))
            elif self.kind == "pratt":
                if k < n / 2.0:
                    diags.append((b0, t1))
                else:
                    diags.append((t0, b1))
                verts.append((b0, t0))
            elif self.kind == "howe":
                if k < n / 2.0:
                    diags.append((t0, b1))
                else:
                    diags.append((b0, t1))
                verts.append((b0, t0))
            elif self.kind == "vierendeel":
                verts.append((b0, t0))
            elif self.kind == "lattice":
                diags.append((t0, b1))
                diags.append((b0, t1))
                if k % 2 == 0:
                    verts.append((b0, t0))
            else:
                raise ValueError(f"unknown truss kind {self.kind!r}")
        # end posts so both truss ends are closed
        verts.append(((n * p, z0), (n * p, z1)))
        return diags, verts

    def build(self):
        sb = self.sb
        n = self.panels
        p = self.panel
        hw = self.deck_w / 2.0
        z0, z1 = 0.0, self.depth
        d = self.density
        d2 = self.density * self.density2
        rng = self.rng

        chord_p = "I600" if self.depth >= 4.5 else "I450"
        web_p = "C250" if self.kind == "vierendeel" else ("L120" if self.kind == "lattice" else "C250")
        diags, verts = self._web_geometry()

        for side in (-hw, hw):
            # bottom and top chords, split per panel (always present: webs
            # must meet nodes, and ruins drop members, not structure)
            for k in range(n):
                self.beam((k * p, side, z0), ((k + 1) * p, side, z0), chord_p, ["truss", "chord"])
                self.beam((k * p, side, z1), ((k + 1) * p, side, z1),
                          chord_p if self.kind != "vierendeel" else "I700", ["truss", "chord"])
            for (a, b) in diags:
                if rng.random() < d:
                    self.beam((a[0], side, a[1]), (b[0], side, b[1]),
                              web_p, ["truss", "web"], roll=math.radians(90.0))
            for (a, b) in verts:
                # the end posts always close the truss
                if (a[0] == 0.0 and b[0] == 0.0) or (a[0] == n * p and b[0] == n * p) \
                        or rng.random() < d:
                    self.beam((a[0], side, a[1]), (b[0], side, b[1]), "I300", ["truss", "vertical"])
            # handrail along the top chord, on posts at the panel nodes
            if rng.random() < d2 * 0.7:
                for k in range(0, n + 1, 2):
                    self.beam((k * p, side, z1), (k * p, side, z1 + 0.55),
                              "TUBE50", ["truss", "handrail"])
                self.beam((0.0, side, z1 + 0.55), (n * p, side, z1 + 0.55), "TUBE50",
                          ["truss", "handrail"])

        # lateral system: bottom cross beams at every panel point (the deck
        # stringers land on them), top crosses gated
        for k in range(n + 1):
            x = k * p
            self.beam((x, -hw, z0), (x, hw, z0), "I240", ["truss", "cross"])
            if rng.random() < d2:
                self.beam((x, -hw, z1), (x, hw, z1), "C180", ["truss", "cross"])
        for k in range(n):
            x0, x1 = k * p, (k + 1) * p
            if rng.random() < d2 * 0.8:
                self.beam((x0, -hw, z0), (x1, hw, z0), "L70", ["truss", "lace"])
            if rng.random() < d2 * 0.8:
                self.beam((x0, hw, z1), (x1, -hw, z1), "L70", ["truss", "lace"])

        # deck stringers across, plus deck (split into segments so ruins can
        # drop a span; each segment still rests on the bottom chords)
        nstr = max(2, int(self.deck_w / 1.6))
        for k in range(1, nstr):
            y = -hw + self.deck_w * k / nstr
            for j in range(0, n, max(1, int(2.4 / p))):
                if rng.random() < d2:
                    self.beam((j * p, y, z0), ((j + 1) * p, y, z0), "C160", ["truss", "stringer"])
        deck_mat = "grating" if self.catwalk else "concrete"
        nseg = max(2, int(self.span / 12.0))
        for s in range(nseg):
            if rng.random() < d2 * 0.98:
                self.block((self.span * (2 * s + 1) / (2 * nseg), 0.0, 0.10),
                           (self.span / nseg, self.deck_w, 0.18), deck_mat, ["deck"])

        # bolt plates / rivets at bottom-chord joints
        for k in range(0, n + 1, 2):
            if rng.random() < d2 * 0.6:
                self.detail("bolt_plate", (k * p, hw, z0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                            [0.9, 0.5, 0.02])
            if rng.random() < d2 * 0.4:
                self.detail("rivet_row", (k * p, -hw, z0 + 0.2), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                            [p * 0.8, 0.12, 0.12])

        # cable-stayed option: mast at the far end, stays to deck nodes
        if self.cable_mast:
            mh = self.cable_mast
            mast_end = n * p
            self.beam((mast_end, 0.0, z0), (mast_end, 0.0, z0 + mh), "TUBE300", ["truss", "mast"])
            for k in range(2, n - 1, 2):
                if rng.random() < d:
                    self.beam((mast_end, 0.0, z0 + mh), (k * p, -hw, z0 + 0.1),
                              "ROD30", ["truss", "cable"])
                    self.beam((mast_end, 0.0, z0 + mh), (k * p, hw, z0 + 0.1),
                              "ROD30", ["truss", "cable"])
        return self
