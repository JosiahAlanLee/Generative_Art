#!/usr/bin/env python3
"""The serif reading edition of the nine plates for the bound book.

Runs tabulae.py with GRADUUM_READING=1, so that the lettering is IM Fell English outlines in place
of the EMS Nixish stroke face (as the Graduum and Notoria reading editions do), validates each
plate with the shared validator, renders each on the series ground as a one-page PDF and a PNG
preview, and records what was built. The plot masters in plates/out are untouched.

    python reading.py            -> plates/reading/<stem>-reading.pdf, .png, reading-edition.json
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reading")
PAPER = "#ede6d4"
ORDER = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix"]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    import cairosvg
    tmp = os.path.join(OUT, "_build")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    env = dict(os.environ, GRADUUM_READING="1")
    subprocess.run([sys.executable, os.path.join(HERE, "tabulae.py"), "all", tmp], check=True, env=env,
                   stdout=subprocess.DEVNULL)
    summary = []
    for n in ORDER:
        d = os.path.join(tmp, n)
        meta = json.load(open(os.path.join(d, "build-meta.json")))
        val = json.load(open(os.path.join(d, "validation.json")))
        stem = meta["stem"]
        svg = os.path.join(d, f"{stem}.svg")
        pdf = os.path.join(OUT, f"{stem}.pdf")
        png = os.path.join(OUT, f"{stem}.png")
        cairosvg.svg2pdf(url=svg, write_to=pdf, background_color=PAPER)
        cairosvg.svg2png(url=svg, write_to=png, output_width=1240, background_color=PAPER)
        summary.append({"plate": meta["plate"], "title": meta["title"], "stem": stem,
                        "carries_data": meta["carries_data"], "data_source": meta["data_source"],
                        "seed": meta["seed"], "caption": meta["caption_normalized"], "hidden": meta["hidden"]["message"],
                        "all_passed": val["all_passed"], "caption_round_trip": val["caption_round_trip"],
                        "hidden_round_trip": val["hidden_round_trip"], "svg_sha256": sha(svg), "pdf": os.path.basename(pdf)})
    shutil.rmtree(tmp)
    with open(os.path.join(OUT, "reading-edition.json"), "w") as f:
        json.dump({"edition": "serif reading edition", "font": "IM Fell English (OFL), outlines", "ground": PAPER,
                   "plates": summary}, f, indent=1)
    for s in summary:
        print(s["plate"], s["stem"], "passed" if s["all_passed"] else "FAILED")
    if not all(s["all_passed"] for s in summary):
        sys.exit(1)


if __name__ == "__main__":
    main()
