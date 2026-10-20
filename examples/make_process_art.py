#!/usr/bin/env python3
"""Generate candidate plates or one CSV-driven recurrence plate. No network I/O."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.process_art.studies import STUDIES  # noqa: E402


def read_csv(path, column):
    """Keep row order and explicit missing values; never impute or sort."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"CSV must have a {column!r} column")
        values = []
        for line, row in enumerate(reader, 2):
            value = (row[column] or "").strip()
            if value.lower() in {"", "na", "nan", "null"}:
                values.append(float("nan"))
                continue
            try:
                v = float(value)
            except ValueError as e:
                raise ValueError(f"non-numeric value on CSV line {line}") from e
            if not np.isfinite(v):
                raise ValueError(f"non-finite value on CSV line {line}")
            values.append(v)
    if len(values) > 600:
        raise ValueError("at most 600 CSV rows; aggregate explicitly before drawing")
    return np.asarray(values)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT/"examples/out/process-art")
    ap.add_argument("--study", choices=["all", *STUDIES], default="all")
    ap.add_argument("--seeds", nargs="+", type=int, default=[11, 37, 83])
    ap.add_argument("--variants", nargs="+", type=int, choices=[0, 1], default=[0, 1])
    ap.add_argument("--pixels", type=int, default=1800)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--column", default="value")
    ap.add_argument("--transparent", action="store_true")
    args = ap.parse_args()
    if not 200 <= args.pixels <= 6000:
        ap.error("pixels must be between 200 and 6000")
    if args.csv and args.study != "recurrence":
        ap.error("--csv requires --study recurrence")
    values = read_csv(args.csv, args.column) if args.csv else None
    args.out.mkdir(parents=True, exist_ok=True)
    names = STUDIES if args.study == "all" else [args.study]
    for name in names:
        for seed in args.seeds:
            for variant in args.variants:
                start = time.monotonic()
                kw = {}
                if args.csv:
                    kw = {"values": values, "source": args.csv.name}
                plate, state = STUDIES[name](seed, variant, **kw)
                stem = f"{name}-s{seed}-v{variant}"
                svg = plate.svg()
                (args.out/f"{stem}.svg").write_text(svg, encoding="utf-8")
                plate.png(args.out/f"{stem}.png", args.pixels, args.transparent)
                np.savez_compressed(args.out/f"{stem}.npz", **state)
                if args.csv:
                    plate.metadata["input_sha256"] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
                    plate.metadata["column"] = args.column
                elif name == "recurrence":
                    with (args.out/f"{stem}-input.csv").open("w", newline="") as f:
                        w = csv.writer(f)
                        w.writerow(["row", "value"])
                        w.writerows(enumerate(state["values"]))
                plate.metadata["svg_sha256"] = hashlib.sha256(svg.encode()).hexdigest()
                plate.metadata["stroke_count"] = len(plate.strokes)
                plate.metadata["size_mm"] = [plate.width, plate.height]
                (args.out/f"{stem}.json").write_text(json.dumps(plate.metadata, indent=2)+"\n")
                print(f"{stem}: {len(plate.strokes)} strokes, {time.monotonic()-start:.1f}s", flush=True)


if __name__ == "__main__":
    main()
