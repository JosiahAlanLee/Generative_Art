#!/usr/bin/env python3
"""Physarum figures for two Escalationum office plates: Gremory (station 2) and Orobas (station 4).

Everything is computed from files in this repository:
  references/raster/batch-01/{gremory,orobas}-raster-reference-v01.png      the figure renders
  books/03_escalationum/illustrated/out/Pseudomonarchia_Escalationum_illustrated.pdf
      pages 15 and 25, the two office plates, used as the page for the proofs (render removed)
  books/05_notoria/plates/out/nota-v-generalis/nota-v-generalis.png and
  books/07_septimus/clausa/plates/nota-clausa-1.svg       details for the hatching-sources sheet

Writes every run to out/work/ (git-ignored), then the committed selection:
  out/plot/<run>/   SVG plot masters (one Inkscape/AxiDraw layer per pen), run.json, stats.json
  out/proofs/       the office plate pages with the computed figure in place of the render
  out/sheets/       comparison sheets
  out/manifest.json sources and their hashes, settings, code hashes, output hashes

  python study.py               # all 28 runs (about 20 minutes on two cores), then the rest
  python study.py --jobs 4
  python study.py --skip-runs   # rebuild proofs, sheets, selection and manifest from out/work/

Runs are seeded and repeat exactly on the same machine and library versions; another CPU or
another numba / numpy version can change the trajectories, though not the character.
"""
import argparse
import hashlib
import json
import platform
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent
import os
REPO = Path(os.environ.get("GENART_BOOK_SOURCE", BOOK.parents[1]))
sys.path.insert(0, str(HERE))
import physarum_plot as pp  # noqa: E402

OUT = HERE / "out"
WORK = OUT / "work"
RENDERS = "references/raster/batch-01/{}-raster-reference-v01.png"
ILLUSTRATED = "books/03_escalationum/illustrated/out/Pseudomonarchia_Escalationum_illustrated.pdf"
NOTA_V = "books/05_notoria/plates/out/nota-v-generalis/nota-v-generalis.png"
CLAUSA_I = "books/07_septimus/clausa/plates/nota-clausa-1.svg"
FONT = "common/fonts/IBMPlexMono-Regular.ttf"

PAPER = "#eae3d1"
PENS4 = [("ochre", "#a8854a"), ("steel", "#3d5e6e"), ("slate", "#1f2b30"), ("rust", "#a32b24")]  # light -> dark
PENS3 = [("ochre", "#a8854a"), ("slate", "#1f2b30"), ("rust", "#a32b24")]   # feral, faithful, accent
FLOORS = {"rust": 0.3}
GRID, STEPS, DENSITY, WIDTH_MM, PEN_MM = 720, 1200, 0.3, 180.0, 0.3
SPIRITS = {   # home ground (cx, cy, rx, ry) as fractions of the render
    "gremory": dict(station=2, page=15, anchors=[(0.53, 0.225, 0.045, 0.040),    # face
                                                 (0.79, 0.31, 0.075, 0.060),     # letter and hand
                                                 (0.225, 0.28, 0.045, 0.030)]),  # cup
    "orobas": dict(station=4, page=25, anchors=[(0.68, 0.18, 0.075, 0.075),      # eye and bridle
                                                (0.62, 0.43, 0.050, 0.035)]),    # chest spiral
}
VARIANTS = {   # cultures: repel > 0 competes, < 0 attracts; territories = marked regions
    "perpen": None,                                  # one population per pen, station sets the look
    "woven": dict(repel=1.0),                        # competing, interleaved
    "fight": dict(repel=2.0, territories=24),        # competing over marked territories
    "home": dict(repel=2.0, territories=24),         # ... with home ground for the faithful culture
    "symb": dict(repel=-1.0),                        # symbiotic: shared cords
}
SWEEP = (0, 2, 4, 6)
ALL_STYLES = ("topo", "network", "fibers", "hatch", "marks")
COMMIT = {"perpen": ("network",), "home": ("network", "hatch", "marks"), "symb": ("network", "hatch", "marks")}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).resolve().relative_to(REPO).as_posix()


def balance(station):
    """feral share of the agents: 15% at station 0 ... 85% at station 6"""
    return 0.15 + 0.7 * min(max(station / 6, 0), 1)


def plan():
    runs = []
    for s, cfg in SPIRITS.items():
        own = cfg["station"]
        for v in ("perpen", "home", "symb"):
            for st in SWEEP:
                styles = ALL_STYLES if st == own else (("hatch",) if v == "symb" else ("network",))
                runs.append((s, st, v, styles))
        for v in ("fight", "woven"):
            runs.append((s, own, v, ("network",)))
    return sorted(runs, key=lambda r: (r[1] != SPIRITS[r[0]]["station"], r[2], r[0], r[1]))


def plate_rgba(Tn, pens, paper, gamma=0.8):
    """trail map as RGBA that reproduces 'ink multiplied onto this paper' over that paper"""
    alphas = [np.clip(t, 0, 1) ** gamma for t in Tn]
    C = pp.composite(alphas, pens, "#ffffff", opacity=0.95).astype(float) / 255
    P = pp.hex2rgb(paper)
    a = 1 - C.min(-1)
    K = (C * P - (1 - a)[..., None] * P) / np.maximum(a[..., None], 1e-6)
    return Image.fromarray((np.dstack([np.clip(K, 0, 1), a]) * 255).round().astype(np.uint8), "RGBA")


def run_one(spirit, station, variant, styles):
    name = f"{spirit}_s{station}_{variant}"
    src = REPO / RENDERS.format(spirit)
    img = pp.load_image(str(src))
    t0 = time.time()
    if variant == "perpen":
        look = pp.station_look(station)
        prep = pp.prepare(img, GRID, PENS4, PAPER, edge_w=look["edge"], floors=FLOORS)
        sim = pp.simulate(prep, steps=STEPS, density=DENSITY, SO=look["so"], wfood=look["wfood"],
                          kflow=look["flow"], avg_last=150, record_last=160, record_frac=0.08,
                          seed=station + 1, verbose=False)
        pens, settings = PENS4, dict(mode="per pen", look={k: round(v, 4) for k, v in look.items()},
                                     seed=station + 1)
    else:
        looks = (pp.LOOKS["faithful"], pp.LOOKS["feral"])
        anchors = SPIRITS[spirit]["anchors"] if variant == "home" else None
        fields = pp.prepare_cultures(img, GRID, PENS3, PAPER, looks, floors=FLOORS, anchors=anchors)
        kw = VARIANTS[variant]
        sim = pp.simulate_cultures(fields, looks, balance(station), steps=STEPS, density=DENSITY,
                                   avg_last=150, record_last=160, record_frac=0.08, seed=3,
                                   verbose=False, **kw)
        pens, settings = PENS3, dict(mode="cultures", faithful=looks[0], feral=looks[1],
                                     feral_share=round(balance(station), 4), home=anchors, seed=3, **kw)
    sim_s = time.time() - t0
    d = WORK / name
    if d.exists():
        shutil.rmtree(d)
    pp.export(sim, pens, PAPER, d, styles=styles, width_mm=WIDTH_MM, pen_mm=PEN_MM, verbose=False)
    plate_rgba(pp.norm_trail(sim["trail"]), pens, PAPER).save(d / "plate_rgba.png")
    m = sim["trail"].sum((1, 2))
    record = dict(run=name, spirit=spirit, station=station, variant=variant, source=RENDERS.format(spirit),
                  source_sha256=sha(src), grid=GRID, steps=STEPS, density=DENSITY, paper=PAPER,
                  pens=[list(p) for p in pens], floors=FLOORS, settings=settings,
                  width_mm=WIDTH_MM, pen_mm=PEN_MM, styles=list(styles),
                  trail_share=dict(zip([n for n, _ in pens], [round(float(v / m.sum()), 4) for v in m])),
                  seconds=dict(simulate=round(sim_s, 1), total=round(time.time() - t0, 1)))
    (d / "run.json").write_text(json.dumps(record, indent=1) + "\n")
    return name, record["seconds"]


# ------------------------------------------------------------------------------- proofs --

def office_page(spirit):
    """the illustrated edition's plate page for this office, with its render removed"""
    doc = fitz.open(REPO / ILLUSTRATED)
    doc.select([SPIRITS[spirit]["page"] - 1])
    page = doc[0]
    hit = [i for i in page.get_image_info(xrefs=True) if i["width"] >= 512]
    assert len(hit) == 1, hit
    page.delete_image(hit[0]["xref"])
    return doc, fitz.Rect(hit[0]["bbox"])


def build_proof(spirit):
    st = SPIRITS[spirit]["station"]
    pages = [("perpen", "network"), ("home", "plate"), ("home", "hatch"),
             ("symb", "plate"), ("symb", "hatch"), ("symb", "marks")]
    out = fitz.open()
    for variant, style in pages:
        base, box = office_page(spirit)
        page = out.new_page(width=base[0].rect.width, height=base[0].rect.height)
        page.show_pdf_page(page.rect, base, 0)
        d = WORK / f"{spirit}_s{st}_{variant}"
        if style == "plate":
            page.insert_image(box, filename=str(d / "plate_rgba.png"))
        else:
            fig = fitz.open("pdf", fitz.open(str(d / f"{style}.svg")).convert_to_pdf())
            page.show_pdf_page(box, fig, 0)
    path = OUT / "proofs" / f"{spirit.capitalize()}_Physarum_Proofs.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(path), garbage=3, deflate=True)
    return path


# ------------------------------------------------------------------------------- sheets --

def share(run, style, pen="slate", other="ochre"):
    s = json.loads((WORK / run / "stats.json").read_text())[style]
    return s[pen]["draw_m"] / (s[pen]["draw_m"] + s[other]["draw_m"])


def grid(cells, cols, w=420, pad=12, lab_h=34):
    font = ImageFont.truetype(str(REPO / FONT), 19)
    ims = [(im.convert("RGB").resize((w, round(im.height * w / im.width)), Image.LANCZOS), lab) for im, lab in cells]
    H = max(im.height for im, _ in ims)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * (H + lab_h) + (rows + 1) * pad), (246, 243, 236))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(ims):
        r, c = divmod(i, cols)
        x, y = pad + c * (w + pad), pad + r * (H + lab_h + pad)
        d.text((x + 2, y + 6), lab, fill=(35, 35, 35), font=font)
        sheet.paste(im, (x, y + lab_h))
    return sheet


def save_sheet(sheets, name, pad=16):
    W = max(s.width for s in sheets)
    o = Image.new("RGB", (W, sum(s.height for s in sheets) + pad * (len(sheets) - 1)), (246, 243, 236))
    y = 0
    for s in sheets:
        o.paste(s, (0, y))
        y += s.height + pad
    path = OUT / "sheets" / f"{name}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    o.save(path, quality=88, optimize=True)
    return path


def sweep_sheet(variant, second, label2):
    rows = []
    for s, cfg in SPIRITS.items():
        cells = []
        for fname in ("plate.png", f"{second}_preview.png"):
            for st in SWEEP:
                run = f"{s}_s{st}_{variant}"
                tag = {0: ", faithful", 6: ", feral"}.get(st, "") + (" (own)" if st == cfg["station"] else "")
                lab = f"{s} station {st}{tag}" if fname == "plate.png" else label2(run)
                cells.append((Image.open(WORK / run / fname), lab))
        rows.append(grid(cells, 4))
    return rows


def crop(im, box):
    W, H = im.size
    return im.crop((int(W * box[0]), int(H * box[1]), int(W * box[2]), int(H * box[3])))


def build_sheets():
    paths = [save_sheet(sweep_sheet("perpen", "network", lambda r: "network"), "station-dial-one-culture-per-pen"),
             save_sheet(sweep_sheet("home", "network", lambda r: f"network: faithful {share(r, 'network'):.0%}"),
                        "cultures-competing-station-sweep"),
             save_sheet(sweep_sheet("symb", "hatch", lambda r: f"hatch: faithful {share(r, 'hatch'):.0%}"),
                        "cultures-symbiotic-station-sweep")]
    rows = []
    for s, cfg in SPIRITS.items():
        st = cfg["station"]
        cols = [("perpen", "one culture per pen"), ("woven", "two cultures, woven"),
                ("fight", "territories"), ("home", "territories + home")]
        cells = []
        for fname in ("plate.png", "network_preview.png"):
            for v, lab in cols:
                run = f"{s}_s{st}_{v}"
                if fname == "network_preview.png":
                    lab = "network" if v == "perpen" else f"network: faithful {share(run, 'network'):.0%}"
                else:
                    lab = f"{s} s{st}: {lab}"
                cells.append((Image.open(WORK / run / fname), lab))
        rows.append(grid(cells, 4))
    paths.append(save_sheet(rows, "cultures-compared"))
    rows = []
    for s, cfg in SPIRITS.items():
        st = cfg["station"]
        cells = []
        for v, lab in (("home", "competing"), ("symb", "symbiotic")):
            for fname, sl in (("plate.png", f"{s} s{st}: {lab}"), ("hatch_preview.png", "hatch"),
                              ("network_preview.png", "network")):
                cells.append((Image.open(WORK / f"{s}_s{st}_{v}" / fname), sl))
        rows.append(grid(cells, 3))
    paths.append(save_sheet(rows, "competing-vs-symbiotic"))
    pix = fitz.open(str(REPO / CLAUSA_I))[0].get_pixmap(dpi=360, alpha=True)
    rgba = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
    clausa = Image.new("RGB", rgba.size, (237, 230, 212))     # the plate's paper, #ede6d4
    clausa.paste(rgba, mask=rgba.split()[3])
    run = WORK / f"gremory_s{SPIRITS['gremory']['station']}_symb"
    cells = [(crop(Image.open(REPO / NOTA_V), (0.36, 0.33, 0.52, 0.43)), "Book V nota V: contour + crosshatch"),
             (crop(Image.open(run / "hatch_preview.png"), (0.36, 0.38, 0.62, 0.52)), "port: hatch"),
             (crop(clausa, (0.40, 0.42, 0.56, 0.52)), "Nota Clausa I: one dash per agent"),
             (crop(Image.open(run / "marks_preview.png"), (0.36, 0.38, 0.62, 0.52)), "port: marks")]
    paths.append(save_sheet([grid(cells, 2, w=640)], "hatching-sources"))
    return paths


# ------------------------------------------------------------------- selection + manifest --

def select():
    dest = OUT / "plot"
    if dest.exists():
        shutil.rmtree(dest)
    files = []
    for s, cfg in SPIRITS.items():
        for v, styles in COMMIT.items():
            run = f"{s}_s{cfg['station']}_{v}"
            (dest / run).mkdir(parents=True)
            for f in [f"{st}.svg" for st in styles] + ["run.json", "stats.json"]:
                shutil.copy2(WORK / run / f, dest / run / f)
                files.append(dest / run / f)
    return files


def manifest(committed):
    import numba
    import scipy
    import skan
    import skimage
    import PIL
    runs = [json.loads((WORK / r / "run.json").read_text()) for r in sorted(p.name for p in WORK.iterdir() if p.is_dir())]
    m = dict(
        study="Physarum figures for the Escalationum office plates (Gremory, Orobas)",
        derived_from_raster=True,
        note=("Computed from the batch-01 raster renders, so these figures trace a reference, unlike "
              "the book's native plot masters. A study, not part of the book's build."),
        code={rel(HERE / "physarum_plot.py"): sha(HERE / "physarum_plot.py"), rel(__file__): sha(__file__)},
        environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                         scikit_image=skimage.__version__, pillow=PIL.__version__, numba=numba.__version__,
                         skan=skan.__version__, pymupdf=fitz.VersionBind),
        sources={p: sha(REPO / p) for p in [RENDERS.format(s) for s in SPIRITS] + [ILLUSTRATED, NOTA_V, CLAUSA_I]},
        runs=runs,
        outputs={rel(p): sha(p) for p in sorted(committed)},
    )
    (OUT / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--skip-runs", action="store_true")
    a = ap.parse_args()
    if not a.skip_runs:
        jobs = plan()
        t0 = time.time()
        with ProcessPoolExecutor(a.jobs) as ex:
            futs = [ex.submit(run_one, *j) for j in jobs]
            for f in futs:
                name, secs = f.result()
                print(f"{name:20s} {secs}  ({time.time() - t0:.0f}s elapsed)", flush=True)
    committed = select()
    committed += [build_proof(s) for s in SPIRITS]
    committed += build_sheets()
    manifest(committed)
    print("wrote", len(committed), "committed files and out/manifest.json")


if __name__ == "__main__":
    main()
