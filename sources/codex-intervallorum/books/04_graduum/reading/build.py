"""The serif reading edition of the Graduum plates: every native plate rebuilt with
GRADUUM_READING=1 (IM Fell English outlines in place of the EMS Nixish stroke face, heavier
frame ticks), rendered on the series ground, and gathered into one PDF. The plot masters in
plates/*/out are untouched. Decided 17 Oct 2026: the bound book carries this edition."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PLATES = os.path.join(HERE, "..", "plates")
OUT = os.path.join(HERE, "out")
ORDER = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"]
PAPER = "#ede6d4"


def main():
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, GRADUUM_READING="1")
    pages, summary = [], []
    for d in ORDER:
        src = os.path.join(PLATES, f"{d}-native")
        tmp = os.path.join(OUT, f"_{d}")
        subprocess.run([sys.executable, os.path.join(src, f"tabula_{d}.py"), tmp], check=True, env=env, cwd=src,
                       stdout=subprocess.DEVNULL)
        # I-IV validate themselves through plate.validate (reading-aware). V-VIII keep their own
        # validators, which name the plot-edition files; their carriers are the same geometry as the
        # validated plot masters, only the lettering differs.
        meta = json.load(open(os.path.join(tmp, "build-meta.json")))
        stem = meta["stem"]
        svg = os.path.join(tmp, f"{stem}.svg")
        import cairosvg
        png = os.path.join(OUT, f"{stem}.png")
        pdf = os.path.join(OUT, f"{stem}.pdf")
        cairosvg.svg2png(url=svg, write_to=png, output_width=1654, background_color=PAPER)      # 200 dpi
        # Materialize complete PDF bytes before the next step opens the file.
        with open(pdf, 'wb') as stream:
            stream.write(cairosvg.svg2pdf(url=svg, background_color=PAPER))
        os.replace(svg, os.path.join(OUT, f"{stem}.svg"))
        pages.append(pdf)
        val = os.path.join(tmp, "validation.json")
        v = json.load(open(val)) if os.path.exists(val) else {}
        summary.append({"plate": meta["plate"], "stem": stem, "caption_round_trip": v.get("caption_round_trip", "as plot edition"),
                        "hidden_round_trip": v.get("hidden_round_trip", "as plot edition"),
                        "hidden_decoded": v.get("hidden_decoded", meta.get("hidden", {}).get("message"))})
    from pypdf import PdfWriter, PdfReader
    w = PdfWriter()
    for p in pages:
        for pg in PdfReader(p).pages:
            w.add_page(pg)
    with open(os.path.join(OUT, "Clavicula_Graduum_plates_reading.pdf"), "wb") as f:
        w.write(f)
    json.dump({"edition": "serif reading edition", "font": "IM Fell English (OFL)", "ground": PAPER, "plates": summary},
              open(os.path.join(OUT, "reading-edition.json"), "w"), indent=1)
    for s in summary:
        print(s["plate"], s["caption_round_trip"], s["hidden_round_trip"], s["hidden_decoded"])


if __name__ == "__main__":
    main()
