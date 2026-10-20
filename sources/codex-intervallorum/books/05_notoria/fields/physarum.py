"""Deterministic trace fields for the Notoria: a multi-agent model after Jones (2010),
"Characteristics of pattern formation and evolution in approximations of Physarum transport
networks", Artificial Life 16(2).

Each agent has a position and a heading. At every step it senses the trail field at three
points (ahead, ahead-left, ahead-right) at a sensor offset, turns toward the strongest, moves
one step, and deposits. The field diffuses (3 x 3 mean) and evaporates each step. Food nodes,
when present, deposit at a fixed rate and make the Nota Generalis.

Everything is a function of the run specification and this file: numpy only, an explicit
Generator seed, no global state. The manifest records the specification, the hash of this
file, and the hash of the outputs, so a plate's hidden identifier can be checked by
regenerating the field.

Nothing here is a biological or institutional claim. It is the rule by which the plates
were computed, stated so that the computation can be repeated.
"""
import hashlib
import json
import math
import os

import numpy as np

CODE_VERSION = "notoria-fields-1"


def code_hash():
    with open(os.path.abspath(__file__), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


DEFAULT = {
    "model": "jones-2010-agent",
    "grid": [160, 160],          # cells (x, y)
    "agents": 2600,
    "steps": 320,
    "sensor_angle_deg": 45.0,    # SA
    "rotation_angle_deg": 45.0,  # RA
    "sensor_offset": 9.0,        # SO, cells
    "step_size": 1.0,            # SS, cells
    "deposit": 5.0,              # depT
    "evaporation": 0.08,         # fraction of the field lost per step
    "diffusion": 1,              # 3x3 mean filter passes per step
    "spawn": "uniform",          # "disc" | "uniform" | "ring"
    "spawn_radius": 0.42,        # fraction of the half-width (disc, ring)
    "exclusion": True,           # one agent per cell: a move into an occupied cell is refused (Jones)
    "arena": "disc",             # "disc" | "square": the boundary agents cannot cross
    "arena_radius": 0.47,        # fraction of the grid width (disc)
    "stop_deposit_at": None,     # step after which agents deposit nothing (the Decay nota)
    "nodes": [],                 # [[x, y, rate], ...] food sources in cells, for the Generalis
    "snapshots": [320],          # steps at which the field is recorded
    "record_paths": True,
    "seed": 1,
}


def spec_with(**over):
    s = json.loads(json.dumps(DEFAULT))
    s.update(over)
    return s


def _diffuse(F):
    """3 x 3 mean with zero outside the field (the edge is a sink, not a mirror)"""
    P = np.pad(F, 1)
    out = np.zeros_like(F)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            out += P[1 + dy:1 + dy + F.shape[0], 1 + dx:1 + dx + F.shape[1]]
    return out / 9.0


def run(spec):
    """returns {"spec", "field": {step: array(y, x)}, "paths": array(agents, steps+1, 2) or None,
    "alive": array(agents, steps+1) bool}"""
    s = spec_with(**spec)
    W, H = s["grid"]
    rng = np.random.default_rng(s["seed"])
    n = s["agents"]
    cx, cy = W / 2.0, H / 2.0
    if s["spawn"] == "disc":
        r = s["spawn_radius"] * min(W, H) / 2.0 * np.sqrt(rng.random(n))
        a = rng.random(n) * 2 * np.pi
        x, y = cx + r * np.cos(a), cy + r * np.sin(a)
    elif s["spawn"] == "ring":
        r = s["spawn_radius"] * min(W, H) / 2.0 * (0.9 + 0.1 * rng.random(n))
        a = rng.random(n) * 2 * np.pi
        x, y = cx + r * np.cos(a), cy + r * np.sin(a)
    else:
        x, y = rng.random(n) * (W - 2) + 1, rng.random(n) * (H - 2) + 1
    AR = s["arena_radius"] * W if s["arena"] == "disc" else None
    if AR is not None:   # keep the initial population inside the arena
        for _ in range(8):
            outside = (x - cx) ** 2 + (y - cy) ** 2 > (AR - 1) ** 2
            if not outside.any():
                break
            k = int(outside.sum())
            x = np.where(outside, cx + (rng.random(n) - 0.5) * 2 * AR, x)
            y = np.where(outside, cy + (rng.random(n) - 0.5) * 2 * AR, y)
        x = np.where((x - cx) ** 2 + (y - cy) ** 2 > (AR - 1) ** 2, cx, x)
        y = np.where((x - cx) ** 2 + (y - cy) ** 2 > (AR - 1) ** 2, cy, y)
    heading = rng.random(n) * 2 * np.pi
    F = np.zeros((H, W), dtype=np.float64)
    SA, RA = math.radians(s["sensor_angle_deg"]), math.radians(s["rotation_angle_deg"])
    SO, SS, dep, ev = s["sensor_offset"], s["step_size"], s["deposit"], s["evaporation"]
    nodes = s["nodes"]
    snaps = set(int(t) for t in s["snapshots"])
    T = s["steps"]
    paths = np.zeros((n, T + 1, 2)) if s["record_paths"] else None
    alive = np.ones((n, T + 1), dtype=bool)
    if paths is not None:
        paths[:, 0, 0], paths[:, 0, 1] = x, y
    out = {}

    def sample(px, py):
        ix = np.clip(np.rint(px).astype(int), 0, W - 1)
        iy = np.clip(np.rint(py).astype(int), 0, H - 1)
        inside = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        return np.where(inside, F[iy, ix], 0.0)

    for t in range(1, T + 1):
        # sense
        fl = sample(x + SO * np.cos(heading - SA), y + SO * np.sin(heading - SA))
        ff = sample(x + SO * np.cos(heading), y + SO * np.sin(heading))
        fr = sample(x + SO * np.cos(heading + SA), y + SO * np.sin(heading + SA))
        # turn (Jones' rule, with his random choice when both sides beat the front)
        both = (fl > ff) & (fr > ff)
        coin = rng.random(n) < 0.5
        turn = np.where(both, np.where(coin, -RA, RA),
                        np.where(fl > fr, -RA, np.where(fr > fl, RA, 0.0)))
        turn = np.where((fl > ff) | (fr > ff), turn, 0.0)
        heading = heading + turn
        # move; an agent that would leave the field, or enter an occupied cell, keeps its place
        # and takes a new heading (Jones' collision rule, resolved in a random order each step)
        nx_, ny_ = x + SS * np.cos(heading), y + SS * np.sin(heading)
        ok = (nx_ >= 1) & (nx_ < W - 1) & (ny_ >= 1) & (ny_ < H - 1)
        if AR is not None:
            ok &= (nx_ - cx) ** 2 + (ny_ - cy) ** 2 < (AR - 1) ** 2
        if s["exclusion"]:
            occ = np.zeros((H, W), dtype=bool)
            occ[np.clip(np.rint(y).astype(int), 0, H - 1), np.clip(np.rint(x).astype(int), 0, W - 1)] = True
            order = rng.permutation(n)
            tx_ = np.clip(np.rint(nx_).astype(int), 0, W - 1)
            ty_ = np.clip(np.rint(ny_).astype(int), 0, H - 1)
            cx_ = np.clip(np.rint(x).astype(int), 0, W - 1)
            cy_ = np.clip(np.rint(y).astype(int), 0, H - 1)
            for i in order:
                if not ok[i]:
                    continue
                if (tx_[i] != cx_[i] or ty_[i] != cy_[i]) and occ[ty_[i], tx_[i]]:
                    ok[i] = False
                else:
                    occ[cy_[i], cx_[i]] = False
                    occ[ty_[i], tx_[i]] = True
        x = np.where(ok, nx_, x)
        y = np.where(ok, ny_, y)
        heading = np.where(ok, heading, rng.random(n) * 2 * np.pi)
        # deposit
        depositing = s["stop_deposit_at"] is None or t <= int(s["stop_deposit_at"])
        if depositing:
            ix = np.clip(np.rint(x).astype(int), 0, W - 1)
            iy = np.clip(np.rint(y).astype(int), 0, H - 1)
            np.add.at(F, (iy, ix), dep)
        for (nx0, ny0, rate) in nodes:
            F[int(ny0), int(nx0)] += rate
        # diffuse, evaporate
        for _ in range(int(s["diffusion"])):
            F = _diffuse(F)
        F *= (1.0 - ev)
        if paths is not None:
            paths[:, t, 0], paths[:, t, 1] = x, y
        if t in snaps:
            out[t] = F.copy()
    return {"spec": s, "field": out, "paths": paths, "alive": alive}


def output_hash(result):
    h = hashlib.sha256()
    for t in sorted(result["field"]):
        h.update(str(t).encode())
        h.update(np.round(result["field"][t], 6).tobytes())
    if result["paths"] is not None:
        h.update(np.round(result["paths"], 4).tobytes())
    return h.hexdigest()


def manifest(result):
    """the complete run record: what to feed `run` to get the same field, and what came out"""
    spec = result["spec"]
    m = {"code": CODE_VERSION, "code_sha256": code_hash(), "spec": spec, "output_sha256": output_hash(result)}
    m["id"] = manifest_id(m)
    return m


def manifest_id(m):
    """twelve letters A-Z from the hash of code + spec: what the plate carries in its frame"""
    key = json.dumps({"code_sha256": m["code_sha256"], "spec": m["spec"]}, sort_keys=True).encode()
    d = hashlib.sha256(key).digest()
    return "".join(chr(ord("A") + (b % 26)) for b in d[:12])


def regenerate_and_check(m):
    """rerun from a manifest; True when the outputs hash identically"""
    r = run(m["spec"])
    return output_hash(r) == m["output_sha256"], r


if __name__ == "__main__":
    import sys
    r = run({})
    m = manifest(r)
    print(json.dumps({k: m[k] for k in ("code", "id", "output_sha256")}, indent=1))
    ok, _ = regenerate_and_check(m)
    print("regenerates identically:", ok)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            json.dump(m, f, indent=1)
