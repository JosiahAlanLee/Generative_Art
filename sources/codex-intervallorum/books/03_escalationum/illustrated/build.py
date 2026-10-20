#!/usr/bin/env python3
"""Pseudomonarchia Escalationum, illustrated edition.

The same catalogue, page order and text as generator/build.py, with the figure renders filed
under references/raster/ (and Foras from the tarot art) brought into the book: each of the
seven offices stands in a Book I plate in place of the line portrait, and every one of the
twenty-one handoff spirits stands beside its own entry. The seals, the matrix, the interludes
and the register are unchanged. Not a plot master; the plot masters stay in output/.

Output: illustrated/out/Pseudomonarchia_Escalationum_illustrated.pdf and figures.json (which
render went where, with its hash and the keying applied).
"""
import argparse
import glob
import hashlib
import json
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent
REPO = BOOK.parents[1]
sys.path.insert(0, str(BOOK))
sys.path.insert(0, str(REPO / "common" / "illum"))

import generator.build as eb  # noqa: E402
from generator.art import build_art, INK, RED  # noqa: E402
import raster  # noqa: E402
import figure_growth  # noqa: E402
import furniture as fu  # noqa: E402
from reportlab.lib import colors  # noqa: E402

SERIES_PAPER = "#ede6d4"
eb.PAPER = SERIES_PAPER
INTERLUDES = {
    "runbook": ("extraction-of-the-hand-v01.jpg", "COPY / ORDER / REMOVE"),
    "cord": ("office-without-a-seal-v01.jpg", "STOP WORK AUTHORITY / UNISSUED"),
}


def render_for(name):
    n = name.lower()
    if n == "foras":
        return str(REPO / "books" / "06_tarot" / "major-arcana" / "art" / "foras-raster-reference-v02.png")
    hits = sorted(glob.glob(str(REPO / "references" / "raster" / "batch-*" / f"{n}-raster-reference-v*.png")))
    if not hits:
        raise FileNotFoundError(f"no render filed for {name}")
    return hits[-1]          # the selected attempt is the only one outside attempts/


def wrap_hand(text, width, size=10.5):
    return fu.wrap(text, "Hand", size, width)


class IllBook(eb.Book):
    def __init__(self, path, book):
        super().__init__(path, book)
        self.placed = []

    def start(self, p, n):
        # as eb.Book.start, with Book I's specks laid on the paper before anything is drawn
        c = self.c
        c.setFillColor(colors.HexColor(eb.PAPER))
        c.rect(0, 0, eb.PW, eb.PH, stroke=0, fill=1)
        fu.specks(c, eb.PW, eb.PH, f"esc-{n}", n=34, color=(237, 230, 212))
        c.setStrokeColor(colors.HexColor(eb.MUTE))
        c.setLineWidth(.4)
        c.line(34, 680, 470, 680)
        c.setFillColor(colors.HexColor(INK))
        c.setFont("Small", 8.5)
        c.drawString(35, 692, "PSEUDOMONARCHIA ESCALATIONUM")
        c.setFillColor(colors.HexColor(RED))
        c.setFont("Mono", 7)
        c.drawRightString(469, 692, f"INC-0001 / {n:02d}")
        c.setFillColor(colors.HexColor(eb.MUTE))
        c.setFont("Body", 9)
        c.drawCentredString(252, 22, str(n))
        c.bookmarkPage(p["id"])
        c.addOutlineEntry(p["title"], p["id"], 0, False)

    def svg(self, path, x, y, w, h):
        self.art(path, x, y, w, h)

    def record(self, name, src, drawn, where):
        m = drawn[4]
        self.placed.append({"page": self.c.getPageNumber(), "subject": name, "where": where,
                            "source": m["source"], "source_sha256": m["source_sha256"],
                            "figure_growth": m.get("figure_growth"),
                            "keying": {k: m[k] for k in ("ground_rgb", "white_point", "feather", "red_remap", "version")}})


# ---------------------------------------------------------------- portrait --

# The red note on each office plate: a line from the catalogue and what its leader touches.
# "red" = the render's own red (seal or thread), else a point as a fraction of the figure's extent.
NOTES = {
    "FORAS": ("appearance", "five occupied in proving that the sixth is idle.", "red"),
    "VASSAGO": ("seal", None, "red"),
    "GREMORY": ("appearance", "Rain may be heard above it but is not visible from her chair.", (0.52, 0.035)),
    "BUNE": ("seal", None, "red"),
    "OROBAS": ("appearance", "The hind half reporteth elsewhere.", (0.06, 0.40), "left"),
    "PAIMON": ("seal", None, "red"),
    "BAEL": ("seal", None, "red"),
}


def portrait_plate(b, t, arts, caption):
    c = b.c
    rng = random.Random(f"esc-portrait-{t['id']}")
    h = fu.Hand(c, rng, amp=0.16)
    PW = eb.PW
    # title block
    c.setFillColor(colors.HexColor(INK))
    c.setFont("FellTitle", 30)
    c.drawCentredString(PW / 2, 638, t["name"].title() if False else t["name"])
    fu.spaced(c, f"{t['office'].upper()}   ·   STATION {t['id']}   ·   {t['legions']} LEGION{'S' if t['legions'] != 1 else ''}",
              PW / 2, 620, "FellSC", 8.6, 1.1, "center", fu.RED)
    fu.orn_rule(h, PW / 2, 606, 150)

    x0, y0, x1, y1 = 64, 112, 440, 590
    # a faint umber wash under the figure field, as Book I's tinted grounds
    fu.wash(h, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fu.OCHRE, alpha=0.07)
    fu.rope_frame(h, x0, y0, x1, y1)
    gy = y0 + 34
    fu.ground_line(h, x0 + 10, x1 - 10, gy, 9)

    src = render_for(t["name"])
    drawn = raster.place_fit_figure(c, src, x0 + 26, gy - 3, x1 - x0 - 52, y1 - gy - 22, anchor="bottom")
    b.record(t["name"], src, drawn, "office plate")
    fx0, fy0, fx1, fy1 = raster.figure_extent(drawn)

    # the office seal in a cartouche, top left inside the frame
    cx0, cy1 = x0 + 12, y1 - 12
    cw, ch = 58, 66
    h.stroke([(cx0, cy1 - ch), (cx0 + cw, cy1 - ch), (cx0 + cw, cy1), (cx0, cy1)], "hair", "ink", closed=True, amp=0.1)
    b.svg(arts[f"office-seal-{t['id']}"], cx0 + 3, cy1 - ch + 3, cw - 6, ch - 6)

    # the red note; its leader finds the render's own red, or the part of the figure it names
    field, text, target, *side = NOTES[t["name"]] + ("right",)
    side = side[0]
    text = text or t[field]
    assert text in t[field], (t["name"], "note must quote the catalogue")
    if target == "red":
        rp = raster.red_point(drawn)
    else:
        rp = (fx0 + target[0] * (fx1 - fx0), fy1 - target[1] * (fy1 - fy0))
    note = wrap_hand(text, 104)
    nw = max(c.stringWidth(ln, "Hand", 10.5) for ln in note)
    if side == "right":
        nx, ny = x1 - 14, y1 - 30
        fu.hand_note(h, note, nx, ny, 10.5, "red", align="right")
        lx = nx - nw / 2
    else:
        nx, ny = x0 + 14, y1 - 12 - 66 - 22
        fu.hand_note(h, note, nx, ny, 10.5, "red", align="left")
        lx = nx + nw / 2
    if rp:
        ly = ny - (len(note) - 1) * 11 - 6
        mid = ((lx + rp[0]) / 2 + (18 if side == "right" else -10), (ly + rp[1]) / 2 + 6)
        h.stroke(fu.catmull([(lx, ly), mid, (rp[0] + 3, rp[1] + 3)], 10), "hair", "red", amp=0.3)
        h.ring(rp[0] + 1.6, rp[1] + 1.6, 1.3, "hair", "red")

    # glyph bands: the actual effect up the left edge, the binding down the right, at the station's shift
    fu.glyph_band(h, t["actual_effect"], x0 - 13, y0 + 6, y1 - y0 - 12, size=4.4, shift=t["id"], angle=90)
    fu.glyph_band(h, t["binding"], x1 + 13, y1 - 6, y1 - y0 - 12, size=4.4, shift=t["id"], angle=-90)
    fu.register(h, x0 - 16, y1 + 15)
    fu.register(h, x1 + 16, y0 - 15)

    fu.stars(h, (x0 + 12, gy + 12, x1 - 12, y1 - 12), 16, f"esc-{t['id']}",
             avoid=[(fx0 - 6, fy0, fx1 + 6, fy1 + 6), (cx0, cy1 - ch, cx0 + cw, cy1),
                    ((nx - nw - 4) if side == "right" else nx - 4, ny - len(note) * 11 - 4, (nx + 4) if side == "right" else nx + nw + 4, ny + 12),
                    (x0 + 10, gy + 6, x0 + 50, gy + 120)])
    station_ladder(h, x0 + 22, gy + 16, t["id"], (fx0, fy0, fx1, fy1))
    c.setFillColor(colors.HexColor(eb.MUTE))
    lines = fu.wrap(caption, "Italic", 12.5, 340)
    for i, ln in enumerate(lines):
        c.setFont("Italic", 12.5)
        c.drawCentredString(eb.PW / 2, y0 - 26 - i * 16, ln)


def station_ladder(h, x, y, k, fig):
    """the seven stations of the descent as rings on a cord, this office's ring red and filled;
    Book I's standing-uncertain asterisk on the station nobody escalates to"""
    step = 15.5
    pts = [(x, y + (6 - i) * step) for i in range(7)]
    h.stroke(pts, "hair", "ink", amp=0.2)
    for i, (px, py) in enumerate(pts):
        if i == k:
            h.dot(px, py, 3.1, "red")
            h.ring(px, py, 5.2, "hair", "red")
        else:
            h.ring(px, py, 2.6, "orn", "ink")
        h.c.setFont("FellSC", 6.5)
        h.c.setFillColorRGB(*fu.rgb(fu.RED if i == k else fu.UMBER))
        h.c.drawString(px + 7.5, py - 2.2, str(i))
    h.c.setFont("FellSC", 6.2)
    h.c.setFillColorRGB(*fu.rgb(fu.UMBER))
    h.c.drawString(x - 4, y + 6 * step + 11, "STATIONS")


# ---------------------------------------------------------------- handoffs --

def illustrated_interlude(b, p):
    """A composed scene replaces the old diagram; typeset prose remains outside it."""
    c = b.c
    h = fu.Hand(c, random.Random(f"interlude-{p['id']}"), amp=0.14)
    fu.wash(h, [(56, 264), (448, 264), (448, 676), (56, 676)], fu.OCHRE, alpha=0.07)
    fu.rope_frame(h, 56, 264, 448, 676, gap=3.6, corner=6.5, hatch=2.0)
    c.setFillColor(colors.HexColor(INK))
    c.setFont("FellSC", 14)
    c.drawCentredString(252, 650, p["title"])
    filename, strap = INTERLUDES[p["id"]]
    fu.spaced(c, strap, 252, 632, "Mono", 6.3, 0.6, "center", fu.UMBER)
    src = str(REPO / "references" / "raster" / "integrated-01" / filename)
    drawn = raster.place(c, src, 70, 278, 364, 338)
    b.record(p["title"], src, drawn, "composed interlude")
    y = b.text(p["caption"], 52, 248, 400, "label")
    for para in p["paragraphs"]:
        y = b.text(para, 52, y, 400, "note")


def illustrated_workshop(book):
    """The workshop describes the edition actually being read, keeping its source history."""
    paragraphs = book["back"][0]["paragraphs"]
    paragraphs[-2] = (
        "The illustrated edition develops the references into cellular lattices, obscured apertures, "
        "paired anchors, boundary marks, and returns. New interlude scenes bind the workbench to its "
        "ledger and the unissued stop to its empty mounting place. The seals and their keys remain "
        "drawn separately from the raster artwork. No existing sacred seal is reproduced."
    )
    paragraphs[-1] = (
        "The seven office portraits and twenty-one handoff spirits are raster illustrations in this "
        "edition; their procedural predecessors remain in the plot masters. Their authority is a "
        "quantity of ornament. This is a rule for an artwork. The machine has not measured anyone's "
        "competence."
    )
    return book

def entry_compact(b, e, arts, top):
    """one handoff in a two-entry page: the spirit in the left column, the seal at its feet"""
    c = b.c
    y = b.text(e["name"] + " / " + e["office"], 152, top, 300, "small")
    y = b.text(f"{e['source']} > {e['target']} / {e['legions']} LEGIONS", 152, y + 2, 300, "label")
    for f, s in eb.fields(e):
        y = b.text(f + ". " + s, 152, y, 300, "small")
    y = b.text("ACTUAL EFFECT. " + e["actual_effect"], 152, y, 300, "small-red")
    bottom = min(y, top - 236)
    src = render_for(e["name"])
    drawn = raster.place_fit_figure(c, src, 34, bottom + 40, 110, top - bottom - 34, anchor="bottom")
    b.record(e["name"], src, drawn, "handoff entry")
    b.svg(arts["seal-" + e["id"]], 52, bottom - 2, 74, 44)
    return bottom


def entry_single(b, e, arts):
    """a station with one incoming passage: an upright spirit stands at the right of the entry;
    a wide one (Promissor's ribbon, Absentiel's keys) is set full width beneath the text"""
    c = b.c
    b.heading(e["name"])
    top = 608
    src = render_for(e["name"])
    _, m = raster.key(src)
    bx0, by0, bx1, by1 = m["figure_bbox_px"]
    wide = (bx1 - bx0) / (by1 - by0) > 0.85
    y = b.text(e["office"], 52, top, 400 if wide else 250, "red")
    y = b.text(f"{e['legions']} LEGIONS / PASSAGE {e['source']} > {e['target']}", 52, y, 400 if wide else 250, "label")
    b.svg(arts["seal-" + e["id"]], 380, 612, 72, 56)
    if wide:
        for f, s_ in eb.fields(e):
            y = b.text(f.upper(), 52, y - 6, 400, "label")
            y = b.text(s_, 52, y, 400)
        floor = 150
        drawn = raster.place_fit_figure(c, src, 52, floor, 400, y - 18 - floor, anchor="center")
        b.record(e["name"], src, drawn, "handoff page, beneath the text")
        y = floor - 6
    else:
        fig_bottom = top - 330
        drawn = raster.place_fit_figure(c, src, 300, fig_bottom, 156, 322, anchor="bottom")
        b.record(e["name"], src, drawn, "handoff page")
        for f, s_ in eb.fields(e):
            y = b.text(f.upper(), 52, y - 6, 236, "label")
            y = b.text(s_, 52, y, 236 if y > fig_bottom else 400)
        y = min(y, fig_bottom - 8)
    b.rule(y - 3)
    y = b.text("WHAT THIS OFFICE ACTUALLY DID", 52, y - 17, 400, "label")
    b.text(e["actual_effect"], 52, y, 400, "red")


def pages(book):
    pp = eb.pages(book)
    out = []
    by_station = {}
    for p in pp:
        if p["kind"] == "handoffs":
            st = p["id"].split("-")[1]
            by_station.setdefault(st, []).extend(p["entries"])
    seen = set()
    for p in pp:
        if p["kind"] != "handoffs":
            out.append(p)
            continue
        st = p["id"].split("-")[1]
        if st in seen:
            continue
        seen.add(st)
        es = by_station[st]
        chunks = [es] if len(es) == 1 else [es[i:i + 2] for i in range(0, len(es), 2)]
        for n, ch in enumerate(chunks):
            out.append(dict(kind="handoffs", title=f"Passages to station {st}", entries=ch, id=f"passages-{st}-{n}"))
    return out


def build_pdf(book, pp, arts, out):
    b = IllBook(out / "Pseudomonarchia_Escalationum_illustrated.pdf", book)
    count = sum(1 if (p["kind"] == "plate" and p.get("art", "").startswith("station-"))
                or p["id"] in INTERLUDES else len(p.get("entries", [])) for p in pp)
    figure_growth.configure(b.c, "III", 0, count)
    b.c.setSubject("A satirical demonology of incident escalation; third divergent grimoire; illustrated edition")
    for n, p in enumerate(pp, 1):
        b.start(p, n)
        c = b.c
        k = p["kind"]
        if k == "plate" and p["art"].startswith("station-"):
            t = book["tiers"][int(p["art"].split("-")[1])]
            portrait_plate(b, t, arts, p["caption"])
        elif k == "handoffs":
            es = p["entries"]
            if len(es) == 1:
                entry_single(b, es[0], arts)
            else:
                b.text(p["title"].upper(), 52, 651, 400, "label")
                y = 622
                for e in es:
                    y = entry_compact(b, e, arts, y)
                    y -= 12
                    c.setStrokeColor(colors.HexColor(eb.MUTE))
                    c.setLineWidth(.35)
                    c.line(52, y, 452, y)
                    y -= 20
        else:
            # every other leaf as the plot-master book draws it
            draw_plain(b, book, p, arts)
        b.end()
    b.finish()
    return b


def draw_plain(b, book, p, arts):
    c = b.c
    k = p["kind"]
    if k == "cover":
        c.setFillColor(colors.HexColor(INK))
        c.setFont("Title", 40)
        c.drawCentredString(252, 614, "Pseudomonarchia")
        c.drawCentredString(252, 566, "Escalationum")
        c.setFont("TitleItalic", 17)
        c.setFillColor(colors.HexColor(RED))
        c.drawCentredString(252, 528, book["subtitle"])
        b.art(arts["office-seal-6"], 149, 210, 206, 260)
        b.text(book["strap"], 120, 181, 264, "note")
        c.setFont("Small", 12)
        c.setFillColor(colors.HexColor(INK))
        c.drawCentredString(252, 130, book["author"])
        c.setFont("Mono", 8)
        c.drawCentredString(252, 102, "THIRD DIVERGENT GRIMOIRE / 2026 / ILLUSTRATED EDITION")
        c.setFont("Italic", 12)
        c.drawCentredString(252, 62, "Please begin with the original fault.")
    elif k == "plate":
        h = fu.Hand(c, random.Random(f"plate-{p['id']}"), amp=0.14)
        fu.wash(h, [(40, 100), (464, 100), (464, 664), (40, 664)], fu.OCHRE, alpha=0.07)
        fu.rope_frame(h, 40, 100, 464, 664, gap=3.6, corner=6.5, hatch=2.0)
        b.art(arts[p["art"]], 50, 110, 404, 544)
        b.text(p["caption"], 52, 86, 400, "note")
    elif k == "office":
        b.heading(p["entry"]["name"])
        eb.pdf_entry(b, p["entry"], arts["office-seal-" + str(p["entry"]["id"])])
    elif k == "journey":
        b.text("DESCENT / " + str(p["station"]), 52, 650, 400, "label")
        y = b.heading(p["title"], 626)
        for para in p["paragraphs"]:
            y = b.text(para, 52, y, 400)
        b.rule(y - 13)
        b.text(p["parable"], 70, y - 33, 363, "note")
        c.setFillColor(colors.HexColor(RED))
        c.setFont("Mono", 8)
        c.drawRightString(450, 71, "STATUS: ESCALATED")
    elif k == "interlude":
        if p["id"] in INTERLUDES:
            illustrated_interlude(b, p)
            return
        h = fu.Hand(c, random.Random(f"interlude-{p['id']}"), amp=0.14)
        fu.wash(h, [(56, 264), (448, 264), (448, 676), (56, 676)], fu.OCHRE, alpha=0.07)
        fu.rope_frame(h, 56, 264, 448, 676, gap=3.6, corner=6.5, hatch=2.0)
        b.art(arts[p["art"]], 68, 276, 368, 388)
        y = b.text(p["caption"], 52, 248, 400, "label")
        for para in p["paragraphs"]:
            y = b.text(para, 52, y, 400, "note")
    else:
        y = b.heading(p["title"])
        for para in p["paragraphs"]:
            y = b.text(para, 52, y, 400, p.get("style", "body"))
        if p.get("sample"):
            b.art(arts[p["sample"]], 182, 49, 140, 146)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=HERE / "out")
    a = ap.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    eb.register()
    fu.fonts()
    book = illustrated_workshop(json.loads((BOOK / "manuscript" / "catalogue.json").read_text()))
    pp = pages(book)
    arts = build_art(book, REPO / "build" / "escalationum-art")
    b = build_pdf(book, pp, arts, out)
    pdf = out / "Pseudomonarchia_Escalationum_illustrated.pdf"
    import platekit
    platekit.compact(str(pdf))
    rec = {"title": book["title"] + " (illustrated edition)", "pages": len(pp),
           "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
           "figures": b.placed,
           "note": "Renders keyed to a white ground and laid in Multiply; red pulled toward #a32b24. "
                   "See common/illum/raster.py. Native renders unmodified."}
    (out / "figures.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"pages": len(pp), "figures": len(b.placed), "output": str(pdf)}))


if __name__ == "__main__":
    main()
