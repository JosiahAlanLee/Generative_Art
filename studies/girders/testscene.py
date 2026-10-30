#!/usr/bin/env python3
"""Emit deterministic girders-scene-1 fixtures. This is test geometry, not the art generator."""

from __future__ import annotations

import argparse
import gzip
import json
import math
import random
from pathlib import Path


MATERIALS = [
    "concrete", "steel", "steel_painted", "rust",
    "glass", "grating", "accent",
]
PROFILES = {
    "I300": {"kind": "I", "h": 0.30, "w": 0.15, "tw": 0.008, "tf": 0.012},
    "C200": {"kind": "C", "h": 0.20, "w": 0.075, "tw": 0.006, "tf": 0.010},
    "L80": {"kind": "L", "h": 0.08, "w": 0.08, "t": 0.008},
    "BOX250": {"kind": "box", "h": 0.25, "w": 0.25, "t": 0.010},
    "TUBE120": {"kind": "tube", "d": 0.12, "t": 0.006},
    "ROD30": {"kind": "rod", "d": 0.03},
}


class Scene:
    def __init__(self, seed: int = 1237):
        self.rng = random.Random(seed)
        self.seed = seed
        self.blocks: list[dict] = []
        self.beams: list[dict] = []
        self.details: list[dict] = []
        self.groups: list[dict] = [{"id": 0, "name": "complex"}]

    def block(self, center, size, material="concrete", yaw=0.0, tags=(), group=0):
        self.blocks.append({
            "id": len(self.blocks), "center": list(center), "size": list(size),
            "yaw": float(yaw), "material": material, "tags": list(tags),
            "group": group,
        })

    def beam(self, a, b, profile="I300", material="steel", roll=0.0,
             tags=(), group=0):
        if tuple(a) == tuple(b):
            return
        self.beams.append({
            "id": len(self.beams), "a": list(a), "b": list(b),
            "profile": profile, "roll": float(roll), "material": material,
            "tags": list(tags), "group": group,
        })

    def detail(self, kind, center, size, rotation=(0.0, 0.0, 0.0),
               material="steel", group=0):
        self.details.append({
            "kind": kind, "transform": euler_matrix(rotation, center),
            "size": list(size), "material": material, "group": group,
        })

    def record(self, bounds):
        return {
            "format": "girders-scene-1", "seed": self.seed,
            "generator": {"name": "girders-fixture", "version": "1.0.0",
                          "params": {"seed": self.seed}},
            "bounds": {"min": list(bounds[0]), "max": list(bounds[1])},
            "profiles": PROFILES, "materials": MATERIALS,
            "blocks": self.blocks, "beams": self.beams,
            "details": self.details, "groups": self.groups,
            "camera_hints": [
                {"name": "worm", "location": [58, -83, 2.1],
                 "target": [-4, 2, 31], "lens_mm": 27},
                {"name": "tele", "location": [164, -262, 58],
                 "target": [1, 3, 30], "lens_mm": 135},
                {"name": "axon", "location": [104, -126, 105],
                 "target": [1, 2, 27], "lens_mm": 70},
            ],
            "stats": {
                "blocks": len(self.blocks), "beams": len(self.beams),
                "details": len(self.details),
            },
        }


def euler_matrix(rotation, location=(0.0, 0.0, 0.0)):
    """Column-major XYZ Euler transform."""
    rx, ry, rz = rotation
    cx, sx, cy, sy, cz, sz = (
        math.cos(rx), math.sin(rx), math.cos(ry),
        math.sin(ry), math.cos(rz), math.sin(rz),
    )
    # R = Rz * Ry * Rx; columns are the transformed local axes.
    c = [
        cz * cy, sz * cy, -sy,
        cz * sy * sx - sz * cx, sz * sy * sx + cz * cx, cy * sx,
        cz * sy * cx + sz * sx, sz * sy * cx - cz * sx, cy * cx,
    ]
    return [
        c[0], c[1], c[2], 0.0,
        c[3], c[4], c[5], 0.0,
        c[6], c[7], c[8], 0.0,
        float(location[0]), float(location[1]), float(location[2]), 1.0,
    ]


def add_vec(a, b):
    return tuple(x + y for x, y in zip(a, b))


def between(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def tower(s: Scene, cx: float, cy: float, width: float, depth: float,
          height: float, group: int, bays: int = 11):
    # A solid core reads through the dense exterior steel instead of competing
    # with it. Each slab projects to make a strong horizontal rhythm.
    s.block((cx, cy, height * .5), (width, depth, height), tags=("core",), group=group)
    for level in range(bays + 1):
        z = level * height / bays
        s.block((cx, cy, z), (width + 2.2, depth + 2.2, .32),
                tags=("slab",), group=group)
        if 0 < level < bays:
            s.block((cx + width * .51, cy, z - height / bays * .5),
                    (.16, depth * .82, height / bays * .72),
                    material="glass", tags=("lift_core",), group=group)
    x0, x1 = cx - width * .5 - 1.1, cx + width * .5 + 1.1
    y0, y1 = cy - depth * .5 - 1.1, cy + depth * .5 + 1.1
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for x, y in corners:
        steps = bays
        for level in range(steps):
            za, zb = level * height / steps, (level + 1) * height / steps
            s.beam((x, y, za), (x, y, zb), "BOX250", "steel",
                   tags=("frame", "column"), group=group)
    for level in range(bays + 1):
        z = level * height / bays
        for a, b in zip(corners, corners[1:] + corners[:1]):
            s.beam((*a, z), (*b, z), "I300", "steel_painted" if level % 3 else "steel",
                   tags=("frame", "ring"), group=group)
        for i, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1])):
            if level == bays:
                continue
            nxt = corners[(i + 1) % 4]
            up_a = (*a, z)
            up_nxt = (*b, (level + 1) * height / bays)
            up_b = (*b, z)
            up_a2 = (*a, (level + 1) * height / bays)
            if (level + i) % 2 and level < 3:
                s.beam(up_a, up_nxt, "L80", "steel", tags=("bracing",), group=group)
            elif level % 2 == 0:
                s.beam(up_b, up_a2, "L80", "steel", tags=("bracing",), group=group)
    # Secondary facade: a deep outrigger and edge-bolt language every floor.
    for level in range(1, bays, 2):
        z = level * height / bays
        for side, (ax, ay, bx, by) in enumerate([
            (x0, y0, x0, y1), (x1, y0, x1, y1),
            (x0, y0, x1, y0), (x0, y1, x1, y1),
        ]):
            s.beam((ax, ay, z), (bx, by, z), "C200", "rust" if side == 1 else "steel",
                   tags=("outrigger", "secondary"), group=group)
    for z in [height * .28, height * .63, height * .87]:
        for x in (x0, x1):
            s.detail("ladder", (x, cy, z), (.85, .12, 5.6),
                     rotation=(math.pi / 2 if x == x1 else -math.pi / 2, 0, 0),
                     material="steel", group=group)
        s.detail("vent", (cx, y0 - .06, z + 1.1), (2.6, .15, 1.0),
                 material="grating", group=group)
        s.detail("light", (cx - 2.2, y0 - .15, z), (.55, .18, .22),
                 material="accent", group=group)
    # A paired service riser runs the whole height with frequent collars.
    for x in (cx - 1.15, cx + 1.15):
        s.detail("pipe_run", (x, y1 + .25, height * .5), (.18, .18, height * .86),
                 material="steel_painted", group=group)
        for z in range(3, int(height), 4):
            s.detail("bolt_plate", (x, y1 + .08, z), (.38, .38, .08),
                     rotation=(math.pi / 2, 0, 0), material="rust", group=group)


def bridge(s: Scene, x0: float, x1: float, y: float, z: float, group: int,
           width: float = 8.0, depth: float = 7.0):
    xs = [x0 + i * (x1 - x0) / 12 for i in range(13)]
    y0, y1 = y - width * .5, y + width * .5
    top = z + depth
    for yy in (y0, y1):
        for a, b in zip(xs, xs[1:]):
            s.beam((a, yy, z), (b, yy, z), "BOX250", "steel",
                   tags=("bridge", "bottom_chord"), group=group)
            s.beam((a, yy, top), (b, yy, top), "BOX250", "steel_painted",
                   tags=("bridge", "top_chord"), group=group)
        for i, x in enumerate(xs):
            s.beam((x, yy, z), (x, yy, top), "I300", "steel",
                   tags=("bridge", "vertical"), group=group)
            if i < len(xs) - 1:
                if i % 2:
                    s.beam((x, yy, z), (xs[i + 1], yy, top), "L80", "steel",
                           tags=("bridge", "diagonal"), group=group)
                else:
                    s.beam((x, yy, top), (xs[i + 1], yy, z), "L80", "steel",
                           tags=("bridge", "diagonal"), group=group)
        for i, x in enumerate(xs):
            if i % 2 == 0:
                s.detail("rivet_row", (x + .7, yy, z + .18), (1.1, .09, .18),
                         rotation=(math.pi / 2, 0, 0), material="rust", group=group)
    for x in xs:
        s.beam((x, y0, z), (x, y1, z), "C200", "steel",
               tags=("bridge", "floor_beam"), group=group)
        s.beam((x, y0, top), (x, y1, top), "L80", "steel_painted",
               tags=("bridge", "cross_brace"), group=group)
    # Deck plate and deep transverse ribs.
    s.block(((x0 + x1) * .5, y, z + .18), (x1 - x0, width - .25, .26),
            material="grating", tags=("bridge", "deck"), group=group)
    for i, a in enumerate(xs[:-1]):
        b = xs[i + 1]
        if i % 2 == 0:
            s.detail("railing", ((a + b) * .5, y1, z + .55),
                     (b - a + .05, .12, 1.15), material="steel", group=group)
            s.detail("railing", ((a + b) * .5, y0, z + .55),
                     (b - a + .05, .12, 1.15), material="steel", group=group)
    # Hanger cables are separate small members, useful to the scale test.
    for i in range(1, 12, 2):
        x = xs[i]
        s.detail("cable", (x, y0, (z + top) * .5), (.035, .035, depth),
                 material="steel", group=group)
        s.detail("cable", (x, y1, (z + top) * .5), (.035, .035, depth),
                 material="steel", group=group)


def gantry(s: Scene, center, group: int):
    x, y, z = center
    height, width = 20.0, 18.0
    for xx in (x - width * .5, x + width * .5):
        for yy in (y - 2.2, y + 2.2):
            for level in range(5):
                s.beam((xx, yy, level * height / 5),
                       (xx, yy, (level + 1) * height / 5), "BOX250",
                       "steel_painted", tags=("gantry",), group=group)
    for level in range(6):
        zz = level * height / 5
        s.beam((x - width * .5, y - 2.2, zz),
               (x - width * .5, y + 2.2, zz), "I300", "steel",
               tags=("gantry",), group=group)
        s.beam((x + width * .5, y - 2.2, zz),
               (x + width * .5, y + 2.2, zz), "I300", "steel",
               tags=("gantry",), group=group)
        if level:
            s.beam((x - width * .5, y - 2.2, zz),
                   (x + width * .5, y - 2.2, zz), "BOX250", "steel",
                   tags=("gantry", "header"), group=group)
            s.beam((x - width * .5, y + 2.2, zz),
                   (x + width * .5, y + 2.2, zz), "BOX250", "steel",
                   tags=("gantry", "header"), group=group)
    for i in range(9):
        xx = x - width * .5 + i * width / 8
        s.beam((xx, y - 2.2, height), (xx, y + 2.2, height),
               "I300", "steel", tags=("gantry", "top"), group=group)
        s.detail("light", (xx, y - 2.35, height - .3), (.45, .16, .2),
                 material="accent", group=group)
    s.detail("ladder", (x + width * .5 + .12, y + 2.2, 8),
             (.9, .12, 13), rotation=(math.pi / 2, 0, 0),
             material="steel", group=group)


def catwalk(s: Scene, a, b, group: int):
    ax, ay, az = a
    bx, by, bz = b
    length = math.dist(a, b)
    s.beam(a, b, "BOX250", "steel_painted", tags=("catwalk",), group=group)
    # A light grating ribbon under each spine is made from two edge rails.
    s.beam(add_vec(a, (0, -.55, -.15)), add_vec(b, (0, -.55, -.15)),
           "L80", "steel", tags=("catwalk", "edge"), group=group)
    s.beam(add_vec(a, (0, .55, -.15)), add_vec(b, (0, .55, -.15)),
           "L80", "steel", tags=("catwalk", "edge"), group=group)
    segs = max(1, int(length / 2.2))
    dx, dy, dz = (bx - ax) / segs, (by - ay) / segs, (bz - az) / segs
    yaw = math.atan2(dy, dx)
    for i in range(segs):
        t = (i + .5) / segs
        p = (ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t)
        s.detail("railing", add_vec(p, (0, .58, .42)),
                 (length / segs + .02, .1, 1.05),
                 rotation=(0, 0, yaw), material="steel", group=group)
        if i % 3 == 0:
            s.detail("bolt_plate", add_vec(p, (.7, 0, .15)),
                     (.38, .38, .08), material="rust", group=group)


def fixture() -> dict:
    s = Scene()
    # Distant plinths and the site apron establish a horizon below the frames.
    s.block((2, 8, -1.4), (108, 82, 2.5), tags=("ground",))
    s.block((-49, 23, 3.2), (14, 19, 6), tags=("mass",))
    s.block((58, 37, 5.5), (22, 11, 10), tags=("mass",))
    tower(s, -13, 0, 12, 15, 43, 1, bays=11)
    tower(s, 21, 6, 10, 12, 56, 2, bays=14)
    bridge(s, -6.9, 15.9, 2.0, 24.2, 3)
    gantry(s, (3, -19, 0), 4)
    catwalk(s, (-19, -8, 15), (-43, -16, 22), 5)
    catwalk(s, (20, 13, 35), (48, 26, 24), 5)
    # Continuous pipe banks visually tie the towers and low plant together.
    for i, y in enumerate((-4.2, -3.7, -3.2)):
        s.detail("pipe_run", (35, y, 5), (.16, .16, 26),
                 material="rust" if i == 1 else "steel_painted", group=6)
    for x in range(-5, 6):
        for z in (-0.2, .12):
            s.detail("pipe_run", (x * 4, -29, z), (.11, .11, 17),
                     rotation=(0, math.pi / 2, 0),
                     material="steel_painted", group=6)
    # Cables sag in short segments so the detail instancer remains general.
    for side in (-1, 1):
        prev = (2, side * 6, 33)
        for i in range(1, 13):
            x = 2 + i * 2.4
            z = 33 - 3.5 * math.sin(math.pi * i / 13)
            p = (x, side * 6, z)
            s.detail("cable", between(prev, p, .5),
                     (.045, .045, math.dist(prev, p)),
                     rotation=(0, math.pi / 2, 0),
                     material="steel", group=7)
            prev = p
    # Small repeated modules make 4K crops legible while remaining attached to
    # tower facades; floating equipment would read as an authoring error.
    for i in range(48):
        tower_x, tower_y, tower_depth, height = (
            (-13, 0, 15, 43) if i % 2 else (21, 6, 12, 56)
        )
        bay = i % 8
        level = i // 8
        x = tower_x - 3.5 + bay * 1.18
        z = 2.1 + level * height / 9
        s.detail("vent", (x, tower_y - tower_depth * .5 - .09, z),
                 (s.rng.uniform(.55, .82), .15, s.rng.uniform(.35, .7)),
                 material="grating", group=8)
        if i % 2:
            s.detail("bolt_plate", (x + .55, tower_y - tower_depth * .5 - .08, z),
                     (.24, .24, .06), rotation=(math.pi / 2, 0, 0),
                     material="rust", group=8)
    return s.record(((-70, -50, -3), (75, 47, 62)))


def stress(beam_count: int, seed: int = 817) -> dict:
    rng = random.Random(seed)
    beams = []
    profile_names = list(PROFILES)
    materials = ["steel", "steel_painted", "rust", "accent"]
    for i in range(beam_count):
        x, y = rng.uniform(-90, 90), rng.uniform(-90, 90)
        z = rng.uniform(0, 75)
        length = rng.uniform(.2, 3.2)
        axis = rng.randrange(3)
        b = [x, y, z]
        b[axis] += length
        beams.append({
            "id": i, "a": [x, y, z], "b": b,
            "profile": profile_names[rng.randrange(len(profile_names))],
            "roll": rng.uniform(-math.pi, math.pi),
            "material": materials[rng.randrange(len(materials))],
            "tags": ["stress"], "group": i % 16,
        })
    return {
        "format": "girders-scene-1", "seed": seed,
        "generator": {"name": "girders-stress-fixture", "version": "1.0.0",
                      "params": {"beams": beam_count}},
        "bounds": {"min": [-90, -90, 0], "max": [90, 90, 78]},
        "profiles": PROFILES, "materials": MATERIALS,
        "blocks": [
            {"id": 0, "center": [0, 0, -1], "size": [200, 200, 2],
             "yaw": 0, "material": "concrete", "tags": ["ground"], "group": 0}
        ],
        "beams": beams, "details": [],
        "groups": [{"id": i, "name": f"stress-{i}"} for i in range(16)],
        "camera_hints": [
            {"name": "stress", "location": [170, -220, 90],
             "target": [0, 0, 35], "lens_mm": 70}
        ],
        "stats": {"blocks": 1, "beams": beam_count, "details": 0},
    }


def write_scene(record: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(record, separators=(",", ":")).encode()
    if path.suffix == ".gz":
        with gzip.open(path, "wb", compresslevel=4) as f:
            f.write(raw)
    else:
        path.write_bytes(raw)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kind", choices=("fixture", "stress"), default="fixture")
    p.add_argument("--beams", type=int, default=500_000)
    p.add_argument("--seed", type=int, default=817)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    record = stress(a.beams, a.seed) if a.kind == "stress" else fixture()
    write_scene(record, a.out)
    print(json.dumps({"path": str(a.out), **record["stats"]}))


if __name__ == "__main__":
    main()
