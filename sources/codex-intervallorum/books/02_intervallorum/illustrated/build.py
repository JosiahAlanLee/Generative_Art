#!/usr/bin/env python3
"""Clavicula Intervallorum, illustrated edition.

The same manuscript, pagination and plate drawers as generator/build.py, with the five figure
renders filed for this book (references/raster/batch-04, batch-05) brought into their plates:

  III   the Fed Vessel stands where the boxed reserve was; renewal enters at its lid, loss,
        upkeep and restart leave below.
  VI    the Second Neck replaces the two drawn gates: its own red thread bypasses the first
        neck, and the proposed bypass of the second is drawn dashed, untried.
  VII   the House Kept in Abeyance stands over its four supports.
  VIII  the Keeper of Intervals, original, stands beside the four retention windows.
  XII   the Open Inventory, a paper vignette on the night plate, with the twelve seals round it.

The other seven plates are unchanged. Book I's specks are laid on every leaf. Not a plot master.

Output: illustrated/out/Clavicula_Intervallorum_illustrated.pdf and figures.json
"""
import glob
import hashlib
import io
import json
import math
import os
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent
REPO = BOOK.parents[1]
sys.path.insert(0, str(BOOK))
sys.path.insert(0, str(REPO / "common" / "illum"))

import generator.build as ib  # noqa: E402
import generator.plates as ip  # noqa: E402
from generator.plates import bezier, sig_mark, ROMAN  # noqa: E402
import raster  # noqa: E402
import furniture as fu  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.graphics import renderPDF  # noqa: E402
from svglib.svglib import svg2rlg  # noqa: E402


def R(name):
    return sorted(glob.glob(str(REPO / "references" / "raster" / "batch-*" / f"{name}-raster-reference-v*.png")))[-1]


# Each figure: plate number -> (render, plate-unit box x0, y0, x1, y1 the figure's extent is
# fitted into (y down, 1000 x 1400), vignette?)
FIGURES = {}
placed = []


def fit(n, name, box, vignette=None, subject=None, where=None):
    FIGURES[n] = dict(src=R(name), box=box, vignette=vignette, subject=subject or name, where=where or "")


# ------------------------------------------------------------------- plates --

def plate_3(p):
    """the Fed Vessel stands where the boxed reserve was"""
    fit(3, "fed-vessel", (322, 262, 678, 742), subject="The Fed Vessel", where="the reserve, between renewal and its three exits")
    p.arrow([(500, 215), (500, 262)], color="red")
    p.text(250, 250, "renewal q", 22, color="red")
    p.text(735, 545, "R(t)", 40, "italic", align="left")
    for x, word in [(380, "loss"), (500, "upkeep"), (620, "restart")]:
        p.arrow([(x, 752), (x, 810)])
        p.text(x, 850, word, 20, align="center")
    p.lines(150, 400, ["internal", "reserve"], 23, align="center")
    p.lines(850, 400, ["external", "shelter"], 23, align="center")
    p.dash([(240, 300), (240, 780), (760, 780), (760, 300)], "sep")
    x0, y0 = 130, 1120
    p.arrow([(x0, y0), (890, y0)])
    p.arrow([(x0, y0), (x0, 895)])
    p.text(150, 910, "illustrative reserve", 19)
    pts = [(130, 960), (310, 1030), (310, 950), (490, 1020), (490, 940), (670, 1010), (670, 930), (850, 1000)]
    p.path(pts, "red", "core")
    p.dash([(130, 1048), (850, 1048)])
    p.text(860, 1054, "restart", 17, align="right")
    p.dash([(130, 1088), (850, 1088)], "sep")
    p.text(860, 1110, "storage", 17, align="right")


NECK = dict(px_top=23, px_bot=1218, neck_a=515, neck_b=770, cx_px=627)


def plate_6(p):
    """the Second Neck in place of the two drawn gates"""
    for x in (300, 700):
        p.seal(x, 310, 34, 1)
    p.arrow([(300, 346), (300, 390), (500, 440)])
    p.arrow([(700, 346), (700, 390), (500, 440)])
    p.dot(500, 445)
    y0, y1 = 452, 1122
    s = (y1 - y0) / (NECK["px_bot"] - NECK["px_top"])
    ya = y0 + (NECK["neck_a"] - NECK["px_top"]) * s
    yb = y0 + (NECK["neck_b"] - NECK["px_top"]) * s
    fit(6, "second-neck", (360, y0, 640, y1), subject="The Second Neck", where="the two necks are the gates A and B")
    p.text(625, ya + 8, "A", 24, "small")
    p.text(625, yb + 8, "B", 24, "small")
    # the render's own red thread is the bypass of A; the bypass of B is proposed, untried
    p.text(845, ya - 64, "bypasses A", 21, "hand", "red", align="center")
    p.text(845, ya - 32, "retains B", 21, "hand", "red", align="center")
    p.path(bezier((780, ya - 58), (720, ya - 70), (650, ya - 120), (590, ya - 150), 20), "red", "hair")
    p.dash(bezier((432, (ya + yb) / 2), (215, (ya + yb) / 2 + 20), (215, y1 + 8), (488, y1 + 10), 45), "red")
    p.text(150, 985, "proposed", 20, "hand", "red", align="center")
    p.text(150, 1017, "untried", 20, "hand", "red", align="center")
    p.box(90, 1110, 120, 60)
    p.text(150, 1150, "TRIAL", 17, "small", align="center")
    p.text(650, 1168, "THE BLANK IS NOT A SUCCESS", 18, "small", align="center")


def plate_7(p):
    """the House Kept in Abeyance over its four supports"""
    fit(7, "house-kept-in-abeyance", (282, 262, 718, 820), subject="The House Kept in Abeyance", where="over its four supports")
    p.line(150, 838, 850, 838, weight="core")
    p.line(150, 844, 850, 844, weight="hair")
    for i, (word, mark, support, base) in enumerate([("RECORDS", 1, "read / verify", "premises"), ("SKILLS", 5, "practice / teach", "income"),
                                                     ("RELATIONS", 11, "contact / repair", "care"), ("RULES", 4, "review / amend", "standing")]):
        x = 230 + i * 180
        p.line(x, 846, x, 868, weight="hair")
        p.seal(x, 905, 34, mark)
        p.text(x, 970, word, 18, "small", align="center")
        p.text(x, 998, support, 16, align="center")
        p.line(x, 1008, x, 1035, weight="hair")
        p.text(x, 1062, base, 20, align="center")
        p.arrow([(x, 1102), (x, 1074)], "red")
    p.dash([(95, 245), (95, 1115), (905, 1115), (905, 245)], "sep")
    p.text(500, 1160, "WHO MAINTAINS THE REFUGE?", 26, "small", align="center")


def plate_8(p):
    """the Keeper of Intervals beside the four retention windows"""
    fit(8, "keeper-of-intervals-original", (70, 330, 330, 1060), subject="The Keeper of Intervals (original)",
        where="beside the four windows, holding the thread")
    rows = [("PUBLIC TRACE", .27, "visibility"), ("RETAINED LESSON", .8, "usable description"),
            ("IDENTITY LINK", .45, "re-identification"), ("ACTING CAPACITY", .62, "resources / access")]
    X0, X1 = 365, 900
    L = X1 - X0
    for i, (label, end, sub) in enumerate(rows):
        y = 340 + i * 180
        p.text(X0, y, label, 21, "small")
        p.text(X1, y, sub, 19, "italic", align="right")
        p.line(X0, y + 50, X1, y + 50, weight="hair")
        p.line(X0, y + 50, X0 + L * end, y + 50, "red", "core")
        p.circle(X0 + L * end, y + 50, 12, "red")
        for j in range(9):
            p.line(X0 + j * L / 8, y + 44, X0 + j * L / 8, y + 56, weight="hair")
        p.circle(930, y + 50, 18)
        p.line(916, y + 63, 944, y + 37)
        p.text(X0, y + 98, "keeper / renewal rule / residual copies", 17, "mono")
    p.box(100, 1095, 800, 73, double=True)
    p.text(500, 1140, "ILLUSTRATIVE WINDOWS: NO COMMON UNIT", 21, "small", align="center")


def plate_12(p):
    """the Open Inventory as a paper vignette on the night plate, the twelve seals round it"""
    fit(12, "open-inventory", (282, 318, 718, 852), vignette=(250, 296, 750, 874), subject="The Open Inventory",
        where="a paper vignette on the night plate")
    labels = ["STATE", "FUNCTION", "REPERTOIRE", "CLOCK", "RESERVE", "CARRIER",
              "PREREQUISITE", "OPENING", "KEEPER", "TRIAL", "STANDING", "REVISION"]
    pos = [(145, 395), (145, 585), (145, 775)]
    pos += [(165 + k * 134, 960) for k in range(6)]
    pos += [(855, 775), (855, 585), (855, 395)]
    for i, (label, (x, y)) in enumerate(zip(labels, pos)):
        p.seal(x, y, 44, i + 1)
        p.text(x, y + 76, label, 15, "small", align="center")
        p.text(x, y - 58, ROMAN[i], 15, "small", align="center")
    sig_mark(p.hand, 500, 1118, 46, "red", "core")
    p.text(185, 1118, "AN INVENTED KEY", 20, "small")
    p.text(835, 1118, "NO FINAL SEAL", 20, "small", align="right")


ip.DRAWERS[2], ip.DRAWERS[5], ip.DRAWERS[6], ip.DRAWERS[7], ip.DRAWERS[11] = plate_3, plate_6, plate_7, plate_8, plate_12


# ---------------------------------------------------------------- rendering --

def render_plate(b, path):
    """generator/build.py's render_plate, then the plate's figure in the same transform"""
    root = ET.fromstring(path.read_text())
    ns = "{http://www.w3.org/2000/svg}"
    labels = json.loads(root.find(ns + "metadata").text)
    for child in list(root):
        if child.get("id") == "lettering":
            root.remove(child)
    d = svg2rlg(io.BytesIO(ET.tostring(root)))
    viewport = [float(v) for v in root.get("viewBox").split()]
    stp = d.width / viewport[2]
    s = min(486 / d.width, 680 / d.height)
    d.scale(s, s)
    d.width *= s
    d.height *= s
    x, y = (ib.PW - d.width) / 2, (ib.PH - d.height) / 2 - 2
    renderPDF.draw(d, b.c, x, y)
    c = b.c
    k = s * stp
    n = int(path.stem.split("-")[1])
    P = lambda px, py: (x + px * k, y + (viewport[3] - py) * k)
    if n in FIGURES:
        f = FIGURES[n]
        if f["vignette"]:
            vx0, vy0, vx1, vy1 = f["vignette"]
            (X0, Y1), (X1, Y0) = P(vx0, vy0), P(vx1, vy1)
            c.setFillColorRGB(*fu.rgb((237, 230, 212)))
            c.roundRect(X0, Y0, X1 - X0, Y1 - Y0, 4, stroke=0, fill=1)
            h = fu.Hand(c, random.Random(n), amp=0.12)
            h.colors["gold"] = (205, 189, 147)
            fu.rope_frame(h, X0 + 6, Y0 + 6, X1 - 6, Y1 - 6, gap=3.0, corner=5.5, hatch=1.8, color="ink", corners=True)
        bx0, by0, bx1, by1 = f["box"]
        (X0, Y1), (X1, Y0) = P(bx0, by0), P(bx1, by1)
        drawn = raster.place_fit_figure(c, f["src"], X0, Y0, X1 - X0, Y1 - Y0, anchor="center")
        m = drawn[4]
        placed.append({"plate": ROMAN[n - 1], "subject": f["subject"], "where": f["where"], "source": m["source"],
                       "source_sha256": m["source_sha256"]})
    c.saveState()
    c.translate(x, y)
    c.scale(k, k)
    faces = {"roman": "Title", "italic": "TitleItalic", "small": "Small", "mono": "Mono", "hand": "Hand"}
    for label in labels:
        c.setFillColor(colors.HexColor(label["color"]))
        c.setFont(faces[label["face"]], label["size"])
        c.drawString(label["x"], viewport[3] - label["y"], label["text"])
    c.restoreState()


ib.render_plate = render_plate
_start = ib.Book.start


def start(self, title, key=None, outline=None, level=0):
    _start(self, title, key, outline, level)
    fu.specks(self.c, ib.PW, ib.PH, f"intervallorum-{self.c.getPageNumber()}", n=32, color=(238, 230, 212))


ib.Book.start = start


def main():
    out = HERE / "out"
    out.mkdir(parents=True, exist_ok=True)
    book = json.loads((BOOK / "manuscript" / "book.json").read_text())
    book["edition"] = book["edition"] + " / illustrated edition"
    caps = json.loads((HERE / "captions.json").read_text())
    for ch in book["chapters"]:
        if str(ch["number"]) in caps:
            ch["caption"] = caps[str(ch["number"])]
    ib.register_fonts()
    fu.fonts()
    paths = ip.build_plates(book, REPO / "build" / "intervallorum-plates")
    pages, hp = ib.build_pdf(book, paths, out)
    src = out / "Clavicula_Intervallorum.pdf"
    dst = out / "Clavicula_Intervallorum_illustrated.pdf"
    src.replace(dst)
    import platekit
    platekit.compact(str(dst))
    rec = {"title": book["title"] + " (illustrated edition)", "pages": len(pages),
           "pdf_sha256": hashlib.sha256(dst.read_bytes()).hexdigest(), "figures": placed}
    (out / "figures.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"pages": len(pages), "figures": len(placed), "pdf": str(dst)}))


if __name__ == "__main__":
    main()
