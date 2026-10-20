#!/usr/bin/env python3
"""Clavicula Graduum, illustrated edition: the same manuscript and pagination as build_book.py,
with each chapter opened by its illustrated plate (illustrated/plates.py), the reading-the-plate
caption replaced where the illustrated plate differs from the plot master (captions.json), and
Book I's paper under every leaf. IX and XI set the illustrator's proofs in the plate furniture.

Run plates.py first. Output: illustrated/out/Clavicula_Graduum_illustrated.pdf
"""
import io
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(BOOK, "..", ".."))
sys.path.insert(0, BOOK)
sys.path.insert(0, os.path.join(REPO, "common", "illum"))

import build_book as bb  # noqa: E402
import furniture as fu  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from pypdf import PdfReader, PdfWriter, Transformation  # noqa: E402

PLATES = os.path.join(HERE, "out", "plates")
CAPTIONS = json.load(open(os.path.join(HERE, "captions.json")))
ILLUSTRATED = {n: os.path.join(PLATES, f"tabula-{n.lower()}-illustrated.pdf")
               for n in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")}

_count = [0]


def paper(c):
    """the series ground with Book I's specks"""
    _count[0] += 1
    fu.ground(c, bb.PW, bb.PH)
    fu.specks(c, bb.PW, bb.PH, f"graduum-text-{_count[0]}", n=30)


bb.paper = paper


VIGNETTES = {
    "I": ("cut-keeper", "The Cut Keeper."),
    "II": ("shouting-tiers", "The quiet one is marked red."),
}


def render(name):
    import glob
    return sorted(glob.glob(os.path.join(REPO, "references", "raster", "batch-*", f"{name}-raster-reference-v*.png")))[-1]


class IllBook(bb.Book):
    def part_leaf(self, name, number):
        """the part title, with the figure reference that was filed for this part and not drawn
        into its plates set beneath it as a vignette"""
        if self.n % 2 == 0:
            self.new_page(blank=True)
        c = self.c
        paper(c)                      # the part leaf carries no running folio
        self.running = name.lower()
        self.outline.append((f"Book {number}: {name}", self.n))
        top = bb.PH * 0.74
        c.setFillColorRGB(*bb.INK)
        c.setFont("FellSC", 11)
        c.drawCentredString(bb.PW / 2, top + 30, f"BOOK {number}")
        c.setFont("FellTitle", 26)
        c.drawCentredString(bb.PW / 2, top, name)
        bb.bp.flow_rule(c, bb.PW / 2 - 35 * bb.MM, top - 24, 70, name, n=2)
        if number in VIGNETTES:
            import raster
            import figure_growth
            figure_growth.configure(c, "IV", 0 if number == "I" else 4, 12)
            key, caption = VIGNETTES[number]
            raster.place_fit_figure(c, render(key), bb.PW / 2 - 130, 118, 260, top - 60 - 118, anchor="bottom")
            c.setFont("FellIt", 9)
            c.setFillColorRGB(*bb.INK)
            c.drawCentredString(bb.PW / 2, 96, caption)
            self.vignettes = getattr(self, "vignettes", []) + [key]
        else:
            h = fu.Hand(c, random.Random(number), amp=0.15)
            yd = fu.YDown(h, bb.PW / 2, top - 160, 1.0)
            import marks
            marks.sig_mark(yd, 0, 0, 30, "red", "core")
        self.new_page(blank=True)

    def plate_leaf(self, ch):
        num = ch["number"]
        if num not in ILLUSTRATED:
            return super().plate_leaf(ch)
        if self.n % 2 == 0:
            self.new_page(blank=True)
        self.plates[self.n] = ("illustrated", ILLUSTRATED[num])
        self.folios = getattr(self, "folios", {})
        self.folios[self.n] = num
        self.new_page()

    def chapter(self, ch):
        if ch["number"] in CAPTIONS:
            ch = dict(ch, caption=CAPTIONS[ch["number"]])
        return super().chapter(ch)

    def build(self, out):
        self.d = dict(self.d, edition=self.d["edition"] + " / illustrated edition")
        paper(self.c)
        self.title_leaf()
        self.key_leaf()
        self.proem()
        num = {"Of Orders": "I", "Of Passages": "II", "Of Keys": "III"}
        chapters = {c["number"]: c for c in self.d["chapters"]}
        for part in self.d["parts"]:
            self.part_leaf(part["name"], num[part["name"]])
            for cn in part["chapters"]:
                self.chapter(chapters[cn])
        self.back_matter()
        self.c.save()
        self.buf.seek(0)
        text = PdfReader(self.buf)
        w = PdfWriter()
        import cairosvg
        for i, page in enumerate(text.pages, start=1):
            if i in self.plates:
                kind, src = self.plates[i]
                if kind == "illustrated":
                    pl = PdfReader(src).pages[0]
                    # the illustrated leaf is the whole page; its folio is stamped over it
                    ov = io.BytesIO()
                    oc = canvas.Canvas(ov, pagesize=(bb.PW, bb.PH))
                    oc.setFont("FellSC", 7.5)
                    oc.setFillColorRGB(*bb.INK)
                    oc.drawRightString(bb.PW - bb.OUTER, bb.BOTTOM - 26, str(i))
                    oc.drawRightString(bb.PW - bb.OUTER - 28, bb.BOTTOM - 26, f"TABULA {self.folios[i]}")
                    oc.save()
                    ov.seek(0)
                    pl.merge_page(PdfReader(ov).pages[0])
                    w.add_page(pl)
                    continue
                if kind == "reading":
                    pl = PdfReader(src).pages[0]
                else:
                    pb = io.BytesIO(cairosvg.svg2pdf(url=src, background_color="#ede6d4"))
                    pl = PdfReader(pb).pages[0]
                pw, ph = float(pl.mediabox.width), float(pl.mediabox.height)
                s = min((bb.PW - 0.6 * 72) / pw, (bb.PH - 0.9 * 72) / ph)
                tx, ty = (bb.PW - pw * s) / 2, (bb.PH - ph * s) / 2 + 6
                page.merge_transformed_page(pl, Transformation().scale(s, s).translate(tx, ty))
            w.add_page(page)
        for title, pg in self.outline:
            w.add_outline_item(title, pg - 1)
        w.add_metadata({"/Title": self.d["title"] + " (illustrated edition)", "/Author": self.d["author"]})
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            w.write(f)
        import platekit
        platekit.compact(out)
        print("pages", len(w.pages), "plates", len(self.plates), "illustrated", sum(1 for k, _ in self.plates.values() if k == "illustrated"))


if __name__ == "__main__":
    bb.bp.fonts()
    fu.fonts()
    data = json.load(open(os.path.join(BOOK, "manuscript", "book.json")))
    for n, p in ILLUSTRATED.items():
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}: run illustrated/plates.py first")
    IllBook(data).build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out", "Clavicula_Graduum_illustrated.pdf"))
