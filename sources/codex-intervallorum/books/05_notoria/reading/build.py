"""The serif reading edition of the Notoria plates: the five notae rebuilt with
GRADUUM_READING=1 (IM Fell English outlines in place of the EMS Nixish stroke face, as the
Graduum reading edition does), rendered on the series ground, gathered into one PDF, and
checked by the plates' validator including field regeneration. The plot masters in
plates/out are untouched; the manuscript builder takes these pages for the plate leaves."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PLATES = os.path.join(HERE, "..", "plates")
OUT = os.path.join(HERE, "out")
ORDER = ["i", "ii", "iii", "iv", "v"]
PAPER = "#ede6d4"


def main():
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, GRADUUM_READING="1")
    tmp = os.path.join(OUT, "_build")
    subprocess.run([sys.executable, os.path.join(PLATES, "notae.py"), "all", tmp], check=True, env=env, cwd=PLATES,
                   stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, os.path.join(PLATES, "validate.py"), tmp], check=True, env=env, cwd=PLATES,
                   stdout=subprocess.DEVNULL)
    import cairosvg
    from pypdf import PdfReader, PdfWriter
    pages, summary = [], []
    for d in sorted(os.listdir(tmp)):
        meta = json.load(open(os.path.join(tmp, d, "build-meta.json")))
        val = json.load(open(os.path.join(tmp, d, "validation.json")))
        stem = meta["stem"]
        svg = os.path.join(tmp, d, f"{stem}.svg")
        png = os.path.join(OUT, f"{stem}.png")
        pdf = os.path.join(OUT, f"{stem}.pdf")
        cairosvg.svg2png(url=svg, write_to=png, output_width=1654, background_color=PAPER)      # 200 dpi
        # Materialize complete PDF bytes before the next step opens the file.
        with open(pdf, 'wb') as stream:
            stream.write(cairosvg.svg2pdf(url=svg, background_color=PAPER))
        os.replace(svg, os.path.join(OUT, f"{stem}.svg"))
        os.replace(os.path.join(tmp, d, "run-manifest.json"), os.path.join(OUT, f"{stem}-run-manifest.json"))
        pages.append(pdf)
        summary.append({"plate": meta["plate"], "stem": stem, "manifest_id": meta["manifest_id"],
                        "caption_round_trip": val["caption_round_trip"], "hidden_round_trip": val["hidden_round_trip"],
                        "hidden_decoded": val["hidden_decoded"], "field": val["field"], "all_passed": val["all_passed"]})
    w = PdfWriter()
    for p in pages:
        for pg in PdfReader(p).pages:
            w.add_page(pg)
    with open(os.path.join(OUT, "Ars_Notoria_Stigmatum_plates_reading.pdf"), "wb") as f:
        w.write(f)
    json.dump({"edition": "serif reading edition", "font": "IM Fell English (OFL)", "ground": PAPER, "plates": summary},
              open(os.path.join(OUT, "reading-edition.json"), "w"), indent=1)
    for s in summary:
        print(s["plate"], s["stem"], s["manifest_id"], "passed" if s["all_passed"] else "FAILED", s["hidden_decoded"])
    if not all(s["all_passed"] for s in summary):
        sys.exit(1)


if __name__ == "__main__":
    main()
