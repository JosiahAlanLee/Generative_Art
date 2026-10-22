#!/usr/bin/env python3
"""Build the thi.ng port studies: halftone runs, stipples, fuzzy passes, fills, subdivision, distance fields.

Every study is self-contained: the raster input is a synthetic specimen, so no
image is needed and nothing is read from the network.

    python examples/make_thing_ports.py                       # all twelve plates
    python examples/make_thing_ports.py --study halftone --kernels atkinson stucki
    python examples/make_thing_ports.py --study stipple --variants 0 1 2
    python examples/make_thing_ports.py --package             # refresh examples/previews/thing-ports
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
from lib.fuzz.studies import fills_plate, passes_plate, subdivision_plate  # noqa: E402
from lib.halftone.studies import (  # noqa: E402
    KERNEL_CELLS, STIPPLE_VARIANTS, halftone_plate, kernels_plate, stipple_plate)
from lib.sdf2d.studies import APPARATUS_VARIANTS, TILING_VARIANTS, apparatus_plate, tiling_plate  # noqa: E402

PREVIEWS = ROOT / "examples/previews/thing-ports"
STUDIES = ["halftone", "kernels", "stipple", "passes", "fills", "subdivision", "apparatus", "tiling"]
# Plates whose SVG is kept in the preview folder; the heavy halftone plates ship as the contact sheet only.
KEEP_SVG = {"passes", "fills", "subdivision", "apparatus-v0", "apparatus-v1", "tiling-v0", "tiling-v1"}


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
    plate.metadata["svg_bytes"] = len(svg.encode())
    (out / f"{stem}.json").write_text(json.dumps(plate.metadata, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "examples/out/thing-ports")
    ap.add_argument("--study", choices=["all"] + STUDIES, default="all")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--kernels", nargs="+", default=["floyd-steinberg"], help="halftone study kernels")
    ap.add_argument("--cell", type=float, default=.38, help="halftone pixel pitch in mm")
    ap.add_argument("--variants", nargs="+", type=int, help="stipple / apparatus / tiling variants")
    ap.add_argument("--pixels", type=int, default=2000)
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--package", action="store_true",
                    help="after building, copy the selected plates, manifest and contact sheet "
                         "into examples/previews/thing-ports")
    args = ap.parse_args()
    if not 200 <= args.pixels <= 6000:
        ap.error("pixels must be between 200 and 6000")
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = STUDIES if args.study == "all" else [args.study]
    for name in jobs:
        start = time.monotonic()
        stems = []
        if name == "halftone":
            for kernel in args.kernels:
                plate, state = halftone_plate(args.seed, kernel, cell=args.cell)
                stem = f"halftone-{kernel}"
                write(args.out, stem, plate, state, args.pixels, args.transparent)
                stems.append(stem)
        elif name == "kernels":
            plate, state = kernels_plate(args.seed)
            write(args.out, "kernels", plate, state, args.pixels, args.transparent)
            stems.append("kernels")
        elif name in ("stipple", "apparatus", "tiling"):
            table = {"stipple": STIPPLE_VARIANTS, "apparatus": APPARATUS_VARIANTS, "tiling": TILING_VARIANTS}[name]
            fn = {"stipple": stipple_plate, "apparatus": apparatus_plate, "tiling": tiling_plate}[name]
            for variant in (args.variants or sorted(table)):
                if variant not in table:
                    ap.error(f"{name} variants are {sorted(table)}")
                plate, state = fn(args.seed, variant)
                stem = f"{name}-v{variant}"
                write(args.out, stem, plate, state, args.pixels, args.transparent)
                stems.append(stem)
        else:
            fn = {"passes": passes_plate, "fills": fills_plate, "subdivision": subdivision_plate}[name]
            plate, state = fn(args.seed)
            write(args.out, name, plate, state, args.pixels, args.transparent)
            stems.append(name)
        print(f"{name}: {', '.join(stems)} in {time.monotonic() - start:.1f} s")
    if args.package:
        package(args.out)


SELECTION = [
    ("halftone-floyd-steinberg", "Two-ink halftone runs",
     "Three tones from serpentine Floyd–Steinberg at 0.38 mm; black traced in ink, mid in red. Run "
     "direction follows the dither's grain, so the sphere's shadow turns to short dashes."),
    ("kernels", "Six dithers on one crop",
     "Floyd–Steinberg, Atkinson, Jarvis–Judice–Ninke, Stucki, Sierra-lite and an 8 × 8 Bayer screen, "
     "traced identically. Atkinson keeps the highlight open; Bayer gives the regular screen."),
    ("stipple-v1", "Tone-driven Poisson stipples",
     "Exclusion radius 0.5–2.8 mm from the tone; dots are spirals at pen pitch. Chosen over the uniform "
     "and stratified variants because the density alone carries the sphere."),
    ("stipple-v2", "Stratified screen with sized dots",
     "One dot per 1.6 mm cell, radius from tone: the halftone screen's logic with a pen."),
    ("passes", "Fuzzy passes",
     "Rows: exact, one, two and three passes; straight on the left, curved through the jittered "
     "vertices on the right. The curved rectangle shows what break-point tangents do to a corner."),
    ("fills", "Composable fills",
     "Hatch at any angle, inset, jittered, crossed in two passes, a dot screen, and hatch and dots "
     "composed; each outline is a two-pass fuzzy edge in red."),
    ("subdivision", "Subdivision schemes",
     "Chaikin, Lane–Riesenfeld cubic, Dyn–Levin–Gregory and midpoint displacement on one rough "
     "octagon, one to four iterations. DLG stays on the red control points; the others pull inside."),
    ("apparatus-v0", "Distance-field apparatus, contours",
     "A vessel from smooth, rounded, chamfered and stepped booleans drawn as 2 mm inner contours and "
     "two red outer offsets. The stairs of the notch run inward because the field carries them."),
    ("apparatus-v1", "Distance-field apparatus, hatched bands",
     "The same field hatched by sign in 4 mm depth bands, alternating 45° and 135°: a hatched solid "
     "without a polygon."),
    ("tiling-v0", "Mirrored tiling",
     "A stepped glyph repeated with mirroring every 15 mm and clipped to a rounded frame."),
    ("tiling-v1", "Nine-fold rosette",
     "A polar repeat smoothly joined to an annular ring, with five inner offsets; the seams of the "
     "polar repeat show as spikes, a known limit of sector folding."),
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
        if stem in KEEP_SVG:
            shutil.copyfile(out / f"{stem}.svg", previews / f"{stem}.svg")
        items.append({"study": meta["study"], "stem": stem, "label": label, "reason": reason,
                      "svg_in_previews": stem in KEEP_SVG, "settings": meta})
        with Image.open(out / f"{stem}.png") as image:
            im = image.convert("RGB")
        thumbs.append(im.resize((600, round(im.height * 600 / im.width)), Image.Resampling.LANCZOS))
    gap, cols = 20, 4
    rows = (len(thumbs) + cols - 1) // cols
    th = max(t.height for t in thumbs)
    sheet = Image.new("RGB", (cols * 600 + (cols + 1) * gap, rows * th + (rows + 1) * gap), "#ffffff")
    for k, t in enumerate(thumbs):
        sheet.paste(t, (gap + (k % cols) * (600 + gap), gap + (k // cols) * (th + gap)))
    sheet.save(previews / "contact-sheet.jpg", quality=84, optimize=True)
    widths = sorted({item["settings"]["preview_width_px"] for item in items})
    manifest = {"title": "thi.ng ports — selected demonstrations", "date": "2026-10-22",
                "preview_widths_px": widths,
                "svg_policy": "SVGs under about 700 kB are committed beside this manifest; the halftone "
                              "and stipple plates are heavier and are recorded here by hash and size only. "
                              "Rebuild them with examples/make_thing_ports.py.",
                "selection_basis": "One or two plates per study, chosen after rendering every variant and "
                                   "reviewing them individually and on the contact sheet. No numeric "
                                   "beauty ranking.",
                "items": items}
    (previews / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                            encoding="utf-8")
    print(f"packaged {len(items)} plates into {previews}")
    return manifest


if __name__ == "__main__":
    main()
