"""Check that results.csv regenerates from manifest.json and that REPORT.md follows it.

    python books/01_matricis_intervallorum/models/gate_window/validate.py [--dir DIR] [--every K]

Regenerates every K-th cell (default 50) with the manifest's seed and sample size and
compares the stored rows; checks the stored digests; confirms verdict.json is the file
the sweep ran under; and re-applies the rule to confirm the report's outcome. Exit
code 1 on any failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verdict  # noqa: E402
from run import run_cells  # noqa: E402
from report import render_report  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=HERE)
    ap.add_argument("--every", type=int, default=50)
    args = ap.parse_args()
    failures = []

    manifest = json.loads((args.dir / "manifest.json").read_text())
    results = args.dir / "results.csv"
    rows = verdict.read_results(results)

    if manifest.get("partial"):
        failures.append("manifest marks a partial run; a sweep must run every cell")
    if manifest["cells"] != len(rows):
        failures.append(f"manifest says {manifest['cells']} cells, results has {len(rows)}")
    if manifest["grid"] != verdict.GRID:
        failures.append("the grid in verdict.py differs from the grid the sweep used")
    digest = hashlib.sha256(results.read_bytes()).hexdigest()
    if digest != manifest["results_sha256"]:
        failures.append("results.csv digest differs from the manifest")
    if verdict.sha256_file(HERE / "verdict.json") != manifest["verdict_json_sha256"]:
        failures.append("verdict.json changed after the sweep ran")
    if verdict.sha256_file(HERE / "model.py") != manifest["model_py_sha256"]:
        failures.append("model.py changed after the sweep ran; results no longer describe this model")
    if verdict.sha256_file(HERE / "verdict.py") != manifest.get("verdict_py_sha256"):
        failures.append("verdict.py differs from the executable rule recorded in the manifest")
    if np.__version__ != manifest["numpy"]:
        print(f"note: numpy {np.__version__} here, {manifest['numpy']} at the sweep; regenerated draws may differ")

    # Regenerate a sample of cells.
    by_index = {r["index"]: r for r in rows}
    sample = verdict.cells()[:: args.every]
    regen = run_cells(sample, manifest["n_samples_per_cell"], manifest["seed"], manifest["max_rounds"])
    mismatched = 0
    for r in regen:
        stored = by_index[r["index"]]
        for k, v in r.items():
            if k == "index":
                continue
            if not np.isclose(float(v), float(stored[k]), rtol=1e-9, atol=1e-12):
                mismatched += 1
                break
    if mismatched:
        failures.append(f"{mismatched} of {len(regen)} regenerated cells differ from results.csv")
    print(f"regenerated {len(regen)} cells; {mismatched} differ")

    # The report must carry the outcome the rule gives.
    out = verdict.apply(rows, verdict.load_rule())
    report = (args.dir / "REPORT.md").read_text()
    if report != render_report(rows, verdict.load_rule(), manifest):
        failures.append("REPORT.md differs from the complete generated report")
    m = re.search(r"\*\*Outcome (\S+)\.\*\*", report)
    if not m:
        failures.append("REPORT.md has no outcome line")
    elif m.group(1) != out["outcome"]:
        failures.append(f"REPORT.md says {m.group(1)}, the rule gives {out['outcome']}")
    if out["max_truncated_fraction"] > 1e-4:
        failures.append(f"truncated fraction {out['max_truncated_fraction']} exceeds 1e-4")
    print(f"outcome {out['outcome']}; assumed scenario {out['frac_anchored_C_beats_A']:.3f}; gate home held by A {out['frac_gate_home_A_holds']:.3f}")

    for f in failures:
        print("FAIL:", f)
    print("validated" if not failures else f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
