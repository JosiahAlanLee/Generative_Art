#!/usr/bin/env python3
"""Build three composition studies without touching Blender or Driftless.

python examples/make_combination_studies.py --out examples/out/combinations
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.codex_palette.combinations import (quilt_chemistry, marbled_credentials,
                                           revision_loom)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "examples/out/combinations")
    parser.add_argument("--pixels", type=int, default=1800)
    args = parser.parse_args()
    if not 300 <= args.pixels <= 5000:
        parser.error("pixels must be between 300 and 5000")
    args.out.mkdir(parents=True, exist_ok=True)
    inputs = ROOT / "examples/previews/codex-palette"
    catalogue = json.loads((inputs / "guilloche-input.json").read_text())
    history = json.loads((inputs / "history-input.json").read_text())
    jobs = [
        ("partitioned-star", "Partitioned star", "Quilt geometry bounds chemical growth",
         lambda: quilt_chemistry()),
        ("credentials-current", "Credentials in a current", "Catalogue engraving deformed by marbling combs",
         lambda: marbled_credentials(catalogue)),
        ("revision-loom", "Revision loom", "Recorded edits drive textile dissolution",
         lambda: revision_loom(history)),
    ]
    manifest, thumbs = [], []
    for stem, title, caption, build in jobs:
        plate, state = build()
        svg = plate.svg()
        (args.out / f"{stem}.svg").write_text(svg, encoding="utf-8")
        plate.png(args.out / f"{stem}.png", args.pixels)
        plate.png(args.out / f"{stem}-alpha.png", args.pixels, True)
        np.savez_compressed(args.out / f"{stem}.npz", **state)
        plate.metadata.update({"stroke_count": len(plate.strokes), "svg_sha256": hashlib.sha256(svg.encode()).hexdigest(),
                               "size_mm": [plate.width, plate.height], "preview_width_px": args.pixels})
        (args.out / f"{stem}.json").write_text(json.dumps(plate.metadata, ensure_ascii=False, indent=2) + "\n")
        manifest.append({"stem": stem, "title": title, "caption": caption, **plate.metadata})
        with Image.open(args.out / f"{stem}.png") as image:
            thumbs.append(image.convert("RGB").resize((680, 880), Image.Resampling.LANCZOS))
        print(f"{stem}: {len(plate.strokes)} strokes", flush=True)
    sheet = Image.new("RGB", (3 * 680 + 4 * 22, 980), "#e4e1d7")
    pen = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        caption_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    except OSError:
        title_font = caption_font = ImageFont.load_default()
    for k, (image, item) in enumerate(zip(thumbs, manifest)):
        x = 22 + k * 702
        sheet.paste(image, (x, 18))
        pen.text((x + 8, 913), item["title"], font=title_font, fill="#161918")
        pen.text((x + 8, 948), item["caption"], font=caption_font, fill="#4b4840")
    sheet.save(args.out / "Combination_Studies.png")
    sheet.save(args.out / "contact-sheet.jpg", quality=90, optimize=True)
    (args.out / "manifest.json").write_text(json.dumps({"studies": manifest,
        "input_files": {name: hashlib.sha256((inputs / name).read_bytes()).hexdigest()
                        for name in ("history-input.json", "guilloche-input.json")}}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
