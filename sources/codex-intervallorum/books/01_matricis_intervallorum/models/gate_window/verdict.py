"""The sweep grid and the verdict rule, applied to a results table.

The numerical rule is data in verdict.json. run.py records both that file and this
implementation in the manifest. Digests establish consistency, not preregistration.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The grid. Every value is a multiple of the window H = 1, except the probabilities.
GRID = {
    "eps": [0.05, 0.15, 0.30, 0.45, 0.60],
    "delta": [0.0, 0.10, 0.25, 0.50, 0.75, 0.95],
    "phi": [0.0, 0.25],
    "lam": [0.01, 0.03, 0.10, 0.30, 1.0, 3.0, 10.0],
    "sigma": [0.75],
    "d": [0.10],
    "h_wrong": [0.1, 0.5, 1.0, 3.0, 10.0],
    "h_window": [1.0, 3.0, 10.0],
}
GRID_KEYS = tuple(GRID)
STAT_KEYS = ("harm", "booked", "T", "p_late", "n_wrong", "truncated")


def cells() -> list[dict]:
    """Every grid cell in a fixed order, with its index."""
    out = []
    for i, values in enumerate(itertools.product(*(GRID[k] for k in GRID_KEYS))):
        cell = dict(zip(GRID_KEYS, values))
        cell["index"] = i
        out.append(cell)
    return out


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rule(path: Path = HERE / "verdict.json") -> dict:
    return json.loads(path.read_text())


def read_results(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append({k: (int(v) if k == "index" else float(v)) for k, v in r.items()})
    return rows


def c_beats_a(row: dict, margin: float) -> bool:
    return row["harm_C"] <= (1.0 - margin) * row["harm_A"]


def a_beats_c_booked(row: dict) -> bool:
    return row["booked_A"] < row["booked_C"]


def _in(v: float, lo_hi: list[float]) -> bool:
    lo, hi = lo_hi
    return lo - 1e-12 <= v <= hi + 1e-12


def in_anchored(row: dict, rule: dict) -> bool:
    a = rule["anchored_region"]
    return _in(row["delta"], a["delta"]) and _in(row["lam"], a["lam"]) and _in(row["eps"], a["eps"])


def in_gate_home(row: dict, rule: dict) -> bool:
    g = rule["gate_home"]
    return row["delta"] >= g["delta_min"] - 1e-12 and row["lam"] <= g["lam_max"] + 1e-12


def _frac(rows: list[dict], pred) -> float:
    return sum(1 for r in rows if pred(r)) / len(rows) if rows else float("nan")


def apply(rows: list[dict], rule: dict) -> dict:
    """Apply the three-outcome rule. Returns the counts and the outcome."""
    m = rule["margin"]
    anchored = [r for r in rows if in_anchored(r, rule)]
    eps_min = min(r["eps"] for r in rows)
    anchored_no_min = [r for r in anchored if r["eps"] > eps_min + 1e-12]
    home = [r for r in rows if in_gate_home(r, rule)]

    f_all = _frac(rows, lambda r: c_beats_a(r, m))
    f_anch = _frac(anchored, lambda r: c_beats_a(r, m))
    f_anch_no_min = _frac(anchored_no_min, lambda r: c_beats_a(r, m))
    f_home_c = _frac(home, lambda r: c_beats_a(r, m))
    f_home_a = _frac(home, lambda r: not c_beats_a(r, m))
    f_booked = _frac([r for r in rows if r["delta"] > 0], a_beats_c_booked)
    max_trunc = max(max(r["truncated_A"], r["truncated_B"], r["truncated_C"]) for r in rows)

    thresholds = rule["thresholds"]
    if f_all >= thresholds["rigged_all_c"] or f_home_c >= thresholds["rigged_home_c"]:
        outcome = "1_rigged"
    elif (f_anch >= thresholds["region_anchored_c"]
          and f_anch_no_min >= thresholds["region_without_lowest_eps_c"]
          and f_home_a >= thresholds["region_home_a_holds"]):
        outcome = "2_region"
    else:
        outcome = "3_fails"

    return {
        "outcome": outcome,
        "cells": len(rows),
        "anchored_cells": len(anchored),
        "gate_home_cells": len(home),
        "frac_all_C_beats_A": f_all,
        "frac_anchored_C_beats_A": f_anch,
        "frac_anchored_C_beats_A_without_lowest_eps": f_anch_no_min,
        "frac_gate_home_C_beats_A": f_home_c,
        "frac_gate_home_A_holds": f_home_a,
        "frac_A_beats_C_on_booked_harm_where_delta_positive": f_booked,
        "max_truncated_fraction": max_trunc,
    }
