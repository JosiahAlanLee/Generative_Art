"""Run the sweep once and write results.csv and manifest.json.

    python books/01_matricis_intervallorum/models/gate_window/run.py [--out DIR] [--n N] [--seed S] [--every K]

The manifest records the grid, the seed, the sample size, the numpy version, the
SHA-256 of verdict.json as it stood when the sweep ran, and the SHA-256 of the
results. --every K runs every K-th cell only (for checks); a partial run is marked
as such in its manifest and is not a sweep.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from model import ARRANGEMENTS, Params, cell_rng, simulate_cell  # noqa: E402
from verdict import GRID, GRID_KEYS, STAT_KEYS, cells, sha256_file  # noqa: E402

DEFAULT_N = 6000
DEFAULT_SEED = 20261018
MAX_ROUNDS = 80


def run_cells(selected: list[dict], n: int, seed: int, max_rounds: int = MAX_ROUNDS) -> list[dict]:
    rows = []
    for cell in selected:
        p = Params(**{k: cell[k] for k in GRID_KEYS})
        stats = simulate_cell(p, n, cell_rng(seed, cell["index"]), max_rounds=max_rounds)
        row = {"index": cell["index"], **{k: cell[k] for k in GRID_KEYS}}
        for arr in ARRANGEMENTS:
            for s in STAT_KEYS:
                row[f"{s}_{arr}"] = getattr(stats[arr], s)
        rows.append(row)
    return rows


def write_results(rows: list[dict], path: Path) -> None:
    fields = ["index", *GRID_KEYS, *[f"{s}_{a}" for a in ARRANGEMENTS for s in STAT_KEYS]]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r[k] if k == "index" else repr(float(r[k]))) for k in fields})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--every", type=int, default=1)
    args = ap.parse_args()

    all_cells = cells()
    selected = all_cells[:: args.every]
    t0 = time.time()
    rows = run_cells(selected, args.n, args.seed)
    elapsed = time.time() - t0

    args.out.mkdir(parents=True, exist_ok=True)
    results = args.out / "results.csv"
    write_results(rows, results)

    manifest = {
        "model": "gate_window",
        "run": date.today().isoformat(),
        "partial": args.every != 1,
        "every": args.every,
        "cells": len(rows),
        "grid": GRID,
        "n_samples_per_cell": args.n,
        "seed": args.seed,
        "max_rounds": MAX_ROUNDS,
        "rng": "numpy default_rng(PCG64) seeded with [seed, cell index]; lognormal and uniform draws shared across arrangements within a round",
        "numpy": np.__version__,
        "python": platform.python_version(),
        "verdict_json_sha256": sha256_file(HERE / "verdict.json"),
        "model_py_sha256": sha256_file(HERE / "model.py"),
        "verdict_py_sha256": sha256_file(HERE / "verdict.py"),
        "interpretation": "Supplementary illustration under assumed parameters; no empirical calibration or comparative validation.",
        "results_sha256": hashlib.sha256(results.read_bytes()).hexdigest(),
        "elapsed_seconds": round(elapsed, 1),
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(rows)} cells, {args.n} samples each, {elapsed:.0f}s -> {results}")


if __name__ == "__main__":
    main()
