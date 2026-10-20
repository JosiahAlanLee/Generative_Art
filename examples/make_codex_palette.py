#!/usr/bin/env python3
"""Build the Codex palette studies: History Flow, Tero tubes, marbling, guilloché.

History Flow and the guilloché credentials read the public book repository:
pass a local clone with --codex, or the recorded inputs committed under
examples/previews/codex-palette/. The other two studies need no input. No
network I/O; History Flow runs the local ``git`` executable on the clone.

    git clone https://github.com/JosiahAlanLee/Codex-Intervallorum
    python examples/make_codex_palette.py --codex Codex-Intervallorum
    python examples/make_codex_palette.py --study tubes --variants 0 1 2
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.codex_palette import historyflow  # noqa: E402
from lib.codex_palette.studies import (  # noqa: E402
    MARBLING_STAGES, TUBE_PRESETS, guilloche_plate, history_plate, marbling_plate, tubes_plate)

PREVIEWS = ROOT / "examples/previews/codex-palette"
PINNED = "b789e03f30034bc8403f8a40aaf83842885aaad5"

# Reading order of the bound book (README manuscript table of the public repository).
MANUSCRIPTS = [
    "books/07_septimus/manuscript/clavis.md",
    "books/00_accusator/manuscript/de-officio-accusatoris.md",
    "books/01_matricis_intervallorum/manuscript/reading-edition.md",
    "books/03_escalationum/manuscript/catalogue.json",
    "books/04_graduum/manuscript/reading-edition.md",
    "books/05_notoria/manuscript/reading-edition.md",
    "books/00_matres/manuscript/de-matribus-noctis.md",
    "books/06_disputationes/manuscript/de-potestate-et-accusatione.md",
    "books/07_septimus/manuscript/de-vinculis.md",
]
CATALOGUE = "books/03_escalationum/manuscript/catalogue.json"


def history_record(args):
    if args.codex:
        record = historyflow.extract(args.codex, MANUSCRIPTS, args.rev)
        record["repository"] = "https://github.com/JosiahAlanLee/Codex-Intervallorum"
        return record
    return json.loads((PREVIEWS / "history-input.json").read_text(encoding="utf-8"))


def catalogue(args):
    """Only the identifiers and numbers the plate uses; no catalogue prose."""
    if args.codex:
        import subprocess
        revision = subprocess.run(["git", "-C", str(args.codex), "rev-parse", f"{args.rev}^{{commit}}"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        text = subprocess.run(["git", "-C", str(args.codex), "show", f"{revision}:{CATALOGUE}"],
                              check=True, capture_output=True, text=True).stdout
        c = json.loads(text)
        return {
            "source": f"JosiahAlanLee/Codex-Intervallorum@{revision}:{CATALOGUE}",
            "book_revision": revision,
            "tiers": [{k: t[k] for k in ("id", "name", "office", "legions", "authority", "competence",
                                          "liability")} for t in c["tiers"]],
            "handoffs": [{k: h[k] for k in ("id", "source", "target", "name", "office", "legions", "mark")}
                         for h in c["handoffs"]],
        }
    return json.loads((PREVIEWS / "guilloche-input.json").read_text(encoding="utf-8"))


def write(out, stem, plate, state, pixels, transparent):
    svg = plate.svg()
    (out / f"{stem}.svg").write_text(svg, encoding="utf-8")
    plate.png(out / f"{stem}.png", pixels, transparent)
    np.savez_compressed(out / f"{stem}.npz", **state)
    plate.metadata["stroke_count"] = len(plate.strokes)
    plate.metadata["pen_down_m"] = round(sum(
        float(np.hypot(*np.diff(s.points, axis=0).T).sum()) for s in plate.strokes) / 1000, 2)
    plate.metadata["size_mm"] = [plate.width, plate.height]
    plate.metadata["preview_width_px"] = pixels
    plate.metadata["transparent_preview"] = transparent
    plate.metadata["svg_sha256"] = hashlib.sha256(svg.encode()).hexdigest()
    (out / f"{stem}.json").write_text(json.dumps(plate.metadata, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "examples/out/codex-palette")
    ap.add_argument("--study", choices=["all", "history", "tubes", "marbling", "guilloche"], default="all")
    ap.add_argument("--codex", type=Path, help="local clone of JosiahAlanLee/Codex-Intervallorum")
    ap.add_argument("--rev", default=PINNED, help="book revision to read (default: the pinned snapshot)")
    ap.add_argument("--spacing", choices=["version", "time"], default="version")
    ap.add_argument("--seeds", nargs="+", type=int)
    ap.add_argument("--variants", nargs="+", type=int)
    ap.add_argument("--steps", type=int, default=2400, help="tube adaptation steps")
    ap.add_argument("--pixels", type=int, default=2000)
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--package", action="store_true",
                    help="after building, copy the selected plates, inputs, manifest and contact sheet "
                         "into examples/previews/codex-palette")
    args = ap.parse_args()
    if not 200 <= args.pixels <= 6000:
        ap.error("pixels must be between 200 and 6000")
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = ["history", "tubes", "marbling", "guilloche"] if args.study == "all" else [args.study]
    for name in jobs:
        start = time.monotonic()
        if name == "history":
            record = history_record(args)
            (args.out / "history-input.json").write_text(json.dumps(record, ensure_ascii=False) + "\n",
                                                          encoding="utf-8")
            plate, state = history_plate(record, args.spacing)
            plate.metadata["book_revision"] = record["rev"]
            write(args.out, f"history-{args.spacing}", plate, state, args.pixels, args.transparent)
            stems = [f"history-{args.spacing}"]
        elif name == "guilloche":
            data = catalogue(args)
            (args.out / "guilloche-input.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n",
                                                            encoding="utf-8")
            plate, state = guilloche_plate(data["tiers"], data["handoffs"])
            plate.metadata["source"] = data["source"]
            plate.metadata["book_revision"] = data.get("book_revision") or data["source"].split("@", 1)[1].split(":", 1)[0]
            write(args.out, "guilloche", plate, state, args.pixels, args.transparent)
            stems = ["guilloche"]
        else:
            stems = []
            seeds = args.seeds or ([53] if name == "tubes" else [7])
            variants = args.variants or ([1] if name == "tubes" else [1])
            valid = TUBE_PRESETS if name == "tubes" else MARBLING_STAGES
            for seed in seeds:
                for variant in variants:
                    if variant not in valid:
                        ap.error(f"{name} variants are {sorted(valid)}")
                    if name == "tubes":
                        plate, state = tubes_plate(seed, variant, steps=args.steps)
                        # These nodes come from the pinned art snapshot, even
                        # when --rev selects a newer history/catalogue input.
                        plate.metadata["book_revision"] = PINNED
                    else:
                        plate, state = marbling_plate(seed, variant)
                    stem = f"{name}-s{seed}-v{variant}"
                    write(args.out, stem, plate, state, args.pixels, args.transparent)
                    stems.append(stem)
        print(f"{name}: {', '.join(stems)} in {time.monotonic() - start:.1f} s")
    if args.package:
        package(args.out)


SELECTION = [
    ("history-version", "History Flow of the public manuscripts",
     "The five first-parent revisions that changed a manuscript, evenly spaced. Book VI's arrival "
     "is the red block; everything else is threads carried forward from the import."),
    ("tubes-s53-v1", "Tubes between Nota V's seven nodes",
     "Gamma 1.15 keeps loops and the centre node's cross-links; gamma 1.8 (variant 0) collapses "
     "to a single loop and reads as a diagram rather than an organism."),
    ("marbling-s7-v1", "Marbled sheet, gel-git",
     "The back-and-forth stroke gives the heart and flame rows; the nonpareil comb (variant 2) is "
     "denser and its fine teeth crowd a 0.3 mm pen."),
    ("guilloche", "Credentials of the seven offices",
     "Rank reads as ornament density, legions as reeds on the rim, competence as red rings; the "
     "twenty-one passage bands make the matrix a single engraved field."),
]


def package(out, preview_dir=None):
    """Copy the selected plates into the committed preview folder."""
    import shutil
    from PIL import Image
    previews = PREVIEWS if preview_dir is None else Path(preview_dir)
    previews.mkdir(parents=True, exist_ok=True)
    items, thumbs = [], []
    for stem, label, reason in SELECTION:
        meta = json.loads((out / f"{stem}.json").read_text(encoding="utf-8"))
        shutil.copyfile(out / f"{stem}.svg", previews / f"{stem}.svg")
        items.append({"study": meta["study"], "stem": stem, "label": label, "reason": reason,
                      "settings": meta})
        with Image.open(out / f"{stem}.png") as image:
            im = image.convert("RGB")
        thumbs.append(im.resize((900, round(im.height * 900 / im.width)), Image.Resampling.LANCZOS))
    for name in ("history-input.json", "guilloche-input.json"):
        shutil.copyfile(out / name, previews / name)
    gap = 24
    sheet = Image.new("RGB", (len(thumbs) * 900 + (len(thumbs) + 1) * gap,
                              max(t.height for t in thumbs) + 2 * gap), "#ffffff")
    for k, t in enumerate(thumbs):
        sheet.paste(t, (gap + k * (900 + gap), gap))
    sheet.save(previews / "contact-sheet.jpg", quality=88, optimize=True)
    revisions = sorted({item["settings"]["book_revision"] for item in items
                        if item["settings"].get("book_revision")})
    widths = sorted({item["settings"]["preview_width_px"] for item in items})
    manifest = {"title": "Codex palette — selected demonstrations", "date": "2026-10-20",
                "book_revision": revisions[0] if len(revisions) == 1 else None,
                "book_revisions": revisions, "preview_widths_px": widths,
                "selection_basis": "One plate per study, chosen after rendering each study's variants "
                                   "and reviewing them individually and side by side. No numeric "
                                   "beauty ranking.",
                "items": items}
    (previews / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                            encoding="utf-8")
    print(f"packaged {len(items)} plates into {previews}")
    return manifest


if __name__ == "__main__":
    main()
