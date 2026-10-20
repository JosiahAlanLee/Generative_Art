#!/usr/bin/env python3
"""Rebuild the curated selection, contact sheet, raw fields and demonstration ZIP."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.process_art.studies import STUDIES  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contact_sheet(items, out, destination):
    width, height = 430, 610
    sheet = Image.new("RGB", (width*4, height*2), "#e6e1d7")
    d = ImageDraw.Draw(sheet)
    # Pillow's bundled font avoids a system-font dependency in the generator.
    font = ImageFont.load_default(size=17)
    small = ImageFont.load_default(size=13)
    for i, item in enumerate(items):
        im = Image.open(out/"png"/(item["stem"]+".png")).convert("RGB")
        im.thumbnail((420, 548), Image.Resampling.LANCZOS)
        x, y = i % 4*width, i // 4*height
        sheet.paste(im, (x+(width-im.width)//2, y))
        d.text((x+13, y+553), item["label"], font=font, fill="#161918")
        d.text((x+13, y+579), f'{item["study"]} / seed {item["seed"]} / variant {item["variant"]}', font=small, fill="#5b554c")
    sheet.save(destination, quality=88, optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT/"examples/out/process-art-selected")
    ap.add_argument("--zip", type=Path)
    ap.add_argument("--update-preview", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name in ["png", "transparent", "svg", "fields", "settings", "data"]:
        (args.out/name).mkdir(exist_ok=True)
    selection = json.loads((ROOT/"examples/previews/process-art/selection.json").read_text())
    manifest = {**selection, "items": []}
    code = list((ROOT/"lib/process_art").glob("*.py")) + [Path(__file__).resolve()]
    manifest["code_sha256"] = {str(p.relative_to(ROOT)): digest(p) for p in code}
    for item in selection["items"]:
        name, seed, variant = item["study"], item["seed"], item["variant"]
        stem = f"{name}-s{seed}-v{variant}"
        plate, state = STUDIES[name](seed, variant)
        (args.out/"svg"/(stem+".svg")).write_text(plate.svg())
        plate.png(args.out/"png"/(stem+".png"), selection["pixels"])
        plate.png(args.out/"transparent"/(stem+".png"), selection["pixels"], transparent=True)
        np.savez_compressed(args.out/"fields"/(stem+".npz"), **state)
        metadata = {**plate.metadata, "stroke_count": len(plate.strokes),
                    "size_mm": [plate.width, plate.height],
                    "svg_sha256": digest(args.out/"svg"/(stem+".svg"))}
        (args.out/"settings"/(stem+".json")).write_text(json.dumps(metadata, indent=2)+"\n")
        if name == "recurrence":
            with (args.out/"data"/(stem+"-synthetic.csv")).open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["row", "value"])
                w.writerows(enumerate(state["values"]))
        manifest["items"].append({**item, "stem": stem, "settings": metadata})
        print(f"Selected {stem}: {len(plate.strokes)} strokes", flush=True)
    contact_sheet(manifest["items"], args.out, args.out/"contact-sheet.jpg")
    (args.out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (args.out/"README.txt").write_text(
        "PROCESS ART — SELECTED DEMONSTRATIONS\n\n"
        "Eight algorithmic plates selected by contour rhythm, negative space, ink hierarchy and variety.\n"
        "png/: paper previews, 2000 x 2588 pixels (about 299 ppi at 170 x 220 mm).\n"
        "transparent/: the same paths on alpha for compositing.\n"
        "svg/: editable millimetre strokes, two inks, no paper or text.\n"
        "fields/: model arrays, readable with numpy.load(..., allow_pickle=False).\n"
        "settings/: process parameters, scope, data keys and SVG hashes.\n"
        "data/: exact synthetic recurrence inputs; these are not real incident records.\n"
        "manifest.json: editorial selection reasons, settings and code fingerprints.\n\n"
        "Generator and primary-source research: JosiahAlanLee/Generative_Art, techniques/12-process-art.\n"
        "Prepared with ChatGPT/Codex, 20 October 2026, for Josiah Alan-Lee.\n"
        "The catchment is dimensionless, strata are kinematic, chemistry/veins are a one-way hybrid.\n"
        "Physical plotting and full book binding were not tested. See the guide for integration.\n"
    )
    if args.update_preview:
        preview = ROOT/"examples/previews/process-art"
        (preview/"contact-sheet.jpg").write_bytes((args.out/"contact-sheet.jpg").read_bytes())
        (preview/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    zip_path = args.zip or args.out.with_suffix(".zip")
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(args.out.rglob("*")):
            if path.is_file() and path.resolve() != zip_path.resolve():
                archive.write(path, path.relative_to(args.out))
    print(f"Wrote {zip_path}: {zip_path.stat().st_size:,} bytes", flush=True)


if __name__ == "__main__":
    main()
