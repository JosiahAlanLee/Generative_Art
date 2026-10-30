"""Top-level generator and CLI for girders scenes.

    python -m lib.girders generate --preset dense-core --seed 1 --scale medium --out scene.json.gz
    python -m lib.girders preview  --preset ruin --seed 7 --out preview.png

Run ``python -m girders.generate`` with the same flags from inside ``lib/``
(or anywhere with ``lib`` on PYTHONPATH).
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np

from .presets import PRESETS, resolve_params

SCALES = ("small", "medium", "large")
from .scene import SceneBuilder
from .site import (Ctx, bridge_between, build_tower, catwalk_between, floor_schedule,
                   gantry_between, pipe_rack_between)

VERSION = "0.1.0"


def generate(seed, preset="dense-core", scale="medium"):
    """Build a girders scene dict deterministically from a seed."""
    params = resolve_params(preset, scale)
    rng = np.random.default_rng(seed)
    sb = SceneBuilder(seed, preset, params)
    ctx = Ctx(sb, params, rng)

    # ---- v2 megastructures have their own builders (site_v2.py)
    if params.get("v2"):
        from .site_v2 import build as build_v2
        return build_v2(ctx)

    # ---- site layout: towers on a jittered grid
    nx, ny = params["grid"]
    sx_sp, sy_sp = params["spacing"]
    towers = []
    for i in range(nx):
        for j in range(ny):
            g = sb.group(f"tower-{i * ny + j + 1:02d}")
            tx = (i - (nx - 1) / 2.0) * sx_sp + rng.uniform(-params["jitter"], params["jitter"])
            ty = (j - (ny - 1) / 2.0) * sy_sp + rng.uniform(-params["jitter"], params["jitter"])
            fx, fy = rng.uniform(*params["footprint"]), rng.uniform(*params["footprint"])
            storeys = int(rng.integers(*[s + 1 for s in params["storeys"]]))
            ba = params.get("bays_add", 0)
            towers.append({
                "i": i, "j": j, "x": tx, "y": ty, "sx": fx, "sy": fy,
                "storeys": storeys,
                "floors": floor_schedule(storeys, rng.uniform(*params["floor_h"]), rng),
                "bays": (int(rng.integers(*[b + 1 + ba for b in params["bays"]])),
                         int(rng.integers(*[b + 1 + ba for b in params["bays"]]))),
                "core_frac": rng.uniform(*params["core_frac"]),
                "bracing": params["bracing"],
                "floor_h": params["floor_h"][1],
                "antenna": rng.uniform(8.0, 14.0) if rng.random() < params["antenna"] else None,
                "group": g,
            })

    # A finite site apron supplies ground contact, cast shadows and an edge to
    # the complex. Structural plinths sit exactly on its top at z=0.
    margin = 18.0
    min_x = min(t["x"] - t["sx"] / 2.0 for t in towers) - margin
    max_x = max(t["x"] + t["sx"] / 2.0 for t in towers) + margin
    min_y = min(t["y"] - t["sy"] / 2.0 for t in towers) - margin
    max_y = max(t["y"] + t["sy"] / 2.0 for t in towers) + margin
    sb.add_block(
        ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, -0.8),
        (max_x - min_x, max_y - min_y, 1.6),
        "concrete", ["site", "ground"], 0,
    )

    for t in towers:
        build_tower(ctx, t)

    # ---- spans between adjacent towers
    by_key = {(t["i"], t["j"]): t for t in towers}
    br = params["bridge"]
    gan = params["gantry"]
    for t in towers:
        for (di, dj) in ((1, 0), (0, 1)):
            u = by_key.get((t["i"] + di, t["j"] + dj))
            if u is None:
                continue
            if rng.random() < br["chance"] * params["bridge_mul"]:
                for lv in range(br["levels"]):
                    frac = (lv + 1) / (br["levels"] + 1) if br["levels"] > 1 else None
                    bridge_between(ctx, t, u, level_frac=frac)
            if rng.random() < gan["chance"]:
                for lv in range(gan["levels"]):
                    gantry_between(ctx, t, u, level_frac=1.0 - lv * 0.28)
            if rng.random() < params["catwalk"] * params["catwalk_mul"]:
                catwalk_between(ctx, t, u, level_frac=rng.uniform(0.35, 0.85))
            if rng.random() < params.get("pipe", 1.0) * (0.9 if ctx.p.get("pipe_racks") else 0.0):
                pipe_rack_between(ctx, t, u)
            if ctx.ruin and rng.random() < 0.5:
                _sag_cable(ctx, t, u)

    # ---- ruin extras: toppled pipes, collapsed roof stubs, fallen spans
    if ctx.ruin:
        for t in towers:
            if rng.random() < 0.5:
                _toppled_pipe(ctx, t)
            if rng.random() < 0.25:
                _collapsed_corner(ctx, t)
        for t in towers:
            u = by_key.get((t["i"] + 1, t["j"]))
            if u is not None and rng.random() < 0.35:
                _fallen_span(ctx, t, u)

    return sb.scene(VERSION)


# ---------------------------------------------------------------- ruin props

def _sag_cable(ctx, ta, tb):
    """A slack cable hanging between two tower roofs, drooping at mid-span."""
    sb, rng = ctx.sb, ctx.rng
    a = (ta["x"] - ta["sx"] / 2.0, ta["y"] - ta["sy"] / 2.0, ta["floors"][-1] + 0.05)
    b = (tb["x"] + tb["sx"] / 2.0, tb["y"] + tb["sy"] / 2.0, tb["floors"][-1] + 0.05)
    m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, (a[2] + b[2]) / 2.0 - rng.uniform(1.5, 3.5))
    g = sb.group("ruin-cable", 0)
    sb.add_beam(a, m, "ROD16", "rust", ["ruin", "cable"], g)
    sb.add_beam(m, b, "ROD16", "rust", ["ruin", "cable"], g)


def _toppled_pipe(ctx, t):
    """A fallen pipe leaning from the plinth against a first-floor column."""
    sb, rng = ctx.sb, ctx.rng
    x, y, sx, sy = t["x"], t["y"], t["sx"], t["sy"]
    face_y = y - sy / 2.0
    x0 = x - sx / 2.0 + sx * int(rng.integers(t["bays"][0] + 1)) / t["bays"][0]
    bottom = (x - sx / 2.0 - 1.5, face_y + 2.0, 0.4)
    top = (x0, face_y, t["floors"][0])
    g = sb.group("ruin-pipe", 0)
    sb.add_beam(bottom, top, "TUBE90", "rust", ["ruin", "pipe"], g)
    sb.add_detail_at("pipe_run", top, (1, 0, 0), (0, 0, 1), [0.5, 0.5, 0.5], "rust", g)


def _collapsed_corner(ctx, t):
    """A stub of a roof beam cantilevering from the parapet, free end out."""
    sb, rng = ctx.sb, ctx.rng
    x, y, sx, sy = t["x"], t["y"], t["sx"], t["sy"]
    roof = t["floors"][-1]
    corner = (x - sx / 2.0, y - sy / 2.0, roof + 0.1)
    out = (x - sx / 2.0 - rng.uniform(2.0, 4.0), y - sy / 2.0, roof + 0.05)
    g = sb.group("ruin-stub", 0)
    sb.add_beam(corner, out, "I240", "rust", ["ruin", "stub", "free"], g)


def _fallen_span(ctx, ta, tb):
    """A truss bridge that has fallen: lying on the plinths, partly stripped."""
    from .trusses import TrussBridge
    sb, rng = ctx.sb, ctx.rng
    (ax, ay, asx, asy), (bx, by, bsx, bsy) = (
        (ta["x"], ta["y"], ta["sx"], ta["sy"]), (tb["x"], tb["y"], tb["sx"], tb["sy"]))
    if abs(ax - bx) >= abs(ay - by):
        fa = (ax + asx / 2.0, ay) if ax < bx else (ax - asx / 2.0, ay)
        fb = (bx - bsx / 2.0, by) if ax < bx else (bx + bsx / 2.0, by)
    else:
        fa = (ax, ay + asy / 2.0) if ay < by else (ax, ay - asy / 2.0)
        fb = (bx, by - bsy / 2.0) if ay < by else (bx, by + bsy / 2.0)
    origin = np.array([fa[0], fa[1], 0.0])
    direction = np.array([fb[0] - fa[0], fb[1] - fa[1], 0.0])
    span = float(np.linalg.norm(direction))
    if span < 10.0:
        return None
    g = sb.group("ruin-fall", 0)
    deck_z = rng.uniform(2.2, 3.6)
    br = ctx.p["bridge"]
    kind = br["kinds"][int(rng.integers(len(br["kinds"])))]
    bw = TrussBridge(sb, origin, direction, deck_z, span,
                     rng.uniform(*br["width"]), rng.uniform(*br["depth"]), kind,
                     rng, g, material="rust", density=0.8, density2=0.25,
                     panel_min=br["panel"][0], panel_max=br["panel"][1])
    bw.build()
    return g


# ------------------------------------------------------------------ file I/O

def save_scene(scene, path):
    """Write the scene as JSON, gzipped for .json.gz paths."""
    path = Path(path)
    data = json.dumps(scene, separators=(",", ":"))
    if str(path).endswith(".gz"):
        # deterministic bytes: no filename, no timestamp in the gzip header
        with open(path, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=3) as fh:
                fh.write(data.encode("utf-8"))
    else:
        path.write_text(data, encoding="utf-8")
    return path


def load_scene(path):
    path = Path(path)
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="girders.generate",
        description="Generate girders-scene-1 megastructure scenes (seeded, deterministic).")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="dense-core")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--scale", choices=sorted(SCALES), default="medium")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--validate", action="store_true", help="run the schema validator first")
    args = ap.parse_args(argv)

    scene = generate(args.seed, args.preset, args.scale)
    if args.validate:
        from .schema import validate
        errs = validate(scene)
        if errs:
            for e in errs[:20]:
                print(f"INVALID: {e}", file=sys.stderr)
            sys.exit(2)
        print("validator: OK")
    save_scene(scene, args.out)
    st = scene["stats"]
    print(f"wrote {args.out}: {st['blocks']} blocks, {st['beams']} beams, "
          f"{st['details']} details")
    return 0


if __name__ == "__main__":
    sys.exit(main())
