"""Clavicula Graduum: the book. Manuscript text from manuscript/book.json set on 7 x 10 in leaves,
each chapter opened by its plate (the serif reading edition for I-VIII; the illustrator's proofs
for IX-XI, marked as proofs; a withheld leaf for XII). Front matter, the five claims, Practical
Applications, the Clavis, the register of debts. Output: output/Clavicula_Graduum.pdf.

Build: python3 build_book.py   (needs reading/out/*.pdf; run reading/build.py first)
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
import bookpage as bp  # noqa: E402
from bookpage import PW, PH, INK, RED, MM, paper, wrap  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from pypdf import PdfReader, PdfWriter, Transformation  # noqa: E402

OUTER, INNER, TOP, BOTTOM = 0.9 * 72, 1.0 * 72, 1.05 * 72, 0.9 * 72
BODY, LEAD = 11.5, 15.5
READING = os.path.join(HERE, "reading", "out")
PROOFS = {"IX": os.path.join(HERE, "proofs", "ix-gpt", "ix-square-table.svg"),
          "X": os.path.join(HERE, "proofs", "x-xi-v-gpt", "x-prayer-of-the-office.svg"),
          "XI": os.path.join(HERE, "proofs", "x-xi-v-gpt", "xi-lifted-pen.svg")}
STEMS = {"I": "i-nine-and-seven", "II": "ii-two-watchmakers", "III": "iii-the-cut", "IV": "iv-observers-ladder",
         "V": "v-dial-of-seven-keepers", "VI": "vi-feudal-register", "VII": "vii-cord-without-a-mount", "VIII": "viii-council-of-the-loudest"}
TAG = re.compile(r"^\[([EDHVF])\]\s*")


class Book:
    def __init__(self, data):
        self.d = data
        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=(PW, PH), pageCompression=1)
        self.c.setTitle(data["title"])
        self.c.setAuthor(data["author"])
        self.n = 1
        self.plates = {}          # page index -> (plate pdf path, page no) to merge afterwards
        self.outline = []
        self.running = ""

    # --------------------------------------------------------------- page --
    def folio(self):
        c = self.c
        c.setFont("FellSC", 7.5)
        c.setFillColorRGB(*INK)
        if self.n % 2 == 0:
            c.drawString(OUTER, BOTTOM - 26, str(self.n))
            c.drawString(OUTER + 28, BOTTOM - 26, "CLAVICULA GRADUUM")
        else:
            c.drawRightString(PW - OUTER, BOTTOM - 26, str(self.n))
            c.drawRightString(PW - OUTER - 28, BOTTOM - 26, self.running.upper())

    def new_page(self, blank=False):
        self.c.showPage()
        self.n += 1
        paper(self.c)
        if not blank:
            self.folio()

    def x0(self):
        return OUTER if self.n % 2 == 0 else INNER

    def width(self):
        return PW - OUTER - INNER

    def ensure(self, y, need):
        if y - need < BOTTOM:
            self.new_page()
            return PH - TOP
        return y

    # --------------------------------------------------------------- text --
    def para(self, y, text, font="Fell", size=BODY, lead=LEAD, color=INK, indent=0, closing=False):
        c = self.c
        m = TAG.match(text)
        tag = m.group(1) if m else None
        body = text[m.end():] if m else text
        lines = wrap(body, font, size, self.width() - indent - (22 if tag else 0))
        for i, ln in enumerate(lines):
            # A closing paragraph's last line runs the page one line long rather than
            # turn alone onto a leaf of its own.
            if not (closing and i == len(lines) - 1 and y >= BOTTOM):
                y = self.ensure(y, lead)
            if i == 0 and tag:
                c.setFont("FellSC", 8)
                c.setFillColorRGB(*RED)
                c.drawString(self.x0() + indent, y, f"[{tag}]")
            c.setFont(font, size)
            c.setFillColorRGB(*color)
            c.drawString(self.x0() + indent + (22 if tag else 0), y, ln)
            y -= lead
        return y

    def heading(self, y, text, size=19, font="FellTitle", gap=10):
        y = self.ensure(y, size + gap + 40)
        self.c.setFont(font, size)
        self.c.setFillColorRGB(*INK)
        self.c.drawString(self.x0(), y, text)
        return y - size - gap

    def small_caps(self, y, text, color=INK, size=9):
        y = self.ensure(y, 14)
        self.c.setFont("FellSC", size)
        self.c.setFillColorRGB(*color)
        self.c.drawString(self.x0(), y, text.upper())
        return y - 14

    # ------------------------------------------------------------ sections --
    def title_leaf(self):
        d, c = self.d, self.c
        paper(c)
        c.setFillColorRGB(*INK)
        c.setFont("FellTitle", 32)
        c.drawCentredString(PW / 2, PH * 0.62, d["title"])
        c.setFont("FellIt", 13)
        c.drawCentredString(PW / 2, PH * 0.62 - 28, d["subtitle"])
        c.setFont("Fell", 10.5)
        for i, ln in enumerate(wrap(d["strap"], "Fell", 10.5, PW - 2.4 * 72)):
            c.drawCentredString(PW / 2, PH * 0.62 - 60 - i * 15, ln)
        bp.flow_rule(c, PW / 2 - 40 * MM, PH * 0.62 - 100, 80, "graduum-title", n=3)
        c.setFont("Fell", 10.5)
        c.drawCentredString(PW / 2, PH * 0.3, d["author"])
        c.setFillColorRGB(*RED)
        c.setFont("FellSC", 9)
        c.drawCentredString(PW / 2, BOTTOM, d["edition"].upper())
        self.outline.append(("Title", self.n))
        self.new_page(blank=True)

    def key_leaf(self):
        d = self.d
        self.running = "the evidence key"
        y = self.heading(PH - TOP, "The evidence key", 16)
        for k, v in d["evidence_key"].items():
            y = self.para(y, f"[{k}] {v}", size=10.5, lead=14)
            y -= 3
        y -= 12
        y = self.para(y, d["status"], font="FellIt", size=10, lead=13.5)
        self.new_page()

    def proem(self):
        d = self.d
        self.running = "proem"
        self.outline.append(("Proem", self.n))
        y = self.heading(PH - TOP, "Proem", 22)
        band = bp.flow_rule(self.c, self.x0(), y + 8, self.width() / MM, "proem", n=3)
        y -= band * MM
        for p in d["front"]["proem"]:
            y = self.para(y, p)
            y -= 7
        self.new_page()
        self.running = "the five claims"
        self.outline.append(("The five claims", self.n))
        y = self.heading(PH - TOP, "The five claims", 18)
        for cl in d["front"]["claims"]:
            y = self.ensure(y, 90)
            y = self.small_caps(y, f"{cl['id']} [{cl.get('kind', 'H')}]  ·  {cl['name']}", color=RED)
            y = self.para(y, cl["claim"], size=11, lead=14.5)
            y -= 3
            y = self.para(y, "Measure. " + cl["measure"], size=10, lead=13.5, indent=14)
            y = self.para(y, "Counts against it. " + cl["counts_against"], size=10, lead=13.5, indent=14)
            y -= 10
        self.new_page()

    def part_leaf(self, name, number):
        if self.n % 2 == 0:
            self.new_page(blank=True)
        c = self.c
        self.running = name.lower()
        self.outline.append((f"Book {number}: {name}", self.n))
        c.setFillColorRGB(*INK)
        c.setFont("FellSC", 11)
        c.drawCentredString(PW / 2, PH * 0.58 + 30, f"BOOK {number}")
        c.setFont("FellTitle", 26)
        c.drawCentredString(PW / 2, PH * 0.58, name)
        bp.flow_rule(c, PW / 2 - 35 * MM, PH * 0.58 - 24, 70, name, n=2)
        self.new_page(blank=True)

    def plate_leaf(self, ch):
        """the plate on a recto; text follows on the verso. Returns nothing; merge happens later."""
        if self.n % 2 == 0:
            self.new_page(blank=True)
        paper(self.c)            # wipe any folio already drawn on this leaf; the plate has its own
        num = ch["number"]
        c = self.c
        if num in STEMS:
            self.plates[self.n] = ("reading", os.path.join(READING, f"{STEMS[num]}-reading.pdf"))
        elif num in PROOFS:
            self.plates[self.n] = ("proof", PROOFS[num])
            c.setFont("FellSC", 7.5)
            c.setFillColorRGB(*RED)
            c.drawCentredString(PW / 2, BOTTOM - 26, "ILLUSTRATOR'S PROOF (CHATGPT/CODEX); NATIVE PLATE PENDING")
        else:
            # XII: the withheld key is the plate
            c.setFillColorRGB(*INK)
            c.setFont("FellSC", 9)
            c.drawCentredString(PW / 2, PH * 0.56 + 20, "TABULA XII")
            c.setFont("FellTitle", 20)
            c.drawCentredString(PW / 2, PH * 0.56 - 6, ch["title"])
            c.setFont("FellIt", 11)
            c.drawCentredString(PW / 2, PH * 0.56 - 34, "The key to this plate is not supplied in this edition.")
            bp.flow_rule(c, PW / 2 - 30 * MM, PH * 0.56 - 50, 60, "xii", n=2, red_dot=True)
        self.folio_plate(num)
        self.new_page()

    def folio_plate(self, num):
        c = self.c
        c.setFont("FellSC", 7.5)
        c.setFillColorRGB(*INK)
        c.drawRightString(PW - OUTER, BOTTOM - 26, str(self.n))
        c.drawRightString(PW - OUTER - 28, BOTTOM - 26, f"TABULA {num}")

    def chapter(self, ch):
        self.plate_leaf(ch)
        self.running = f"tabula {ch['number']}"
        self.outline.append((f"{ch['number']}. {ch['title']}", self.n))
        y = PH - TOP
        self.c.setFont("FellSC", 10)
        self.c.setFillColorRGB(*INK)
        self.c.drawString(self.x0(), y, f"TABULA {ch['number']}")
        y -= 24
        y = self.heading(y, ch["title"], 22)
        y = self.para(y, ch["deck"], font="FellIt", size=11.5, lead=15)
        y -= 4
        band = bp.flow_rule(self.c, self.x0(), y + 6, self.width() / MM, ch["number"], n=3, red_dot=True)
        y -= band * MM
        y = self.para(y, ch["fiction"], font="FellIt", size=10.5, lead=14)
        y -= 10
        for pg in ch["pages"]:
            y = self.small_caps(y, pg["title"])
            y -= 2
            for p in pg["paragraphs"]:
                y = self.para(y, p)
                y -= 6
        y -= 6
        y = self.small_caps(y, "reading the plate")
        y = self.para(y, ch["caption"], size=10, lead=13.5, closing=True)
        self.new_page()

    def back_matter(self):
        d = self.d
        b = d["back"]
        if self.n % 2 == 0:
            self.new_page(blank=True)
        self.running = "practical applications"
        self.outline.append((b["applications_title"], self.n))
        y = self.heading(PH - TOP, b["applications_title"], 22)
        y = self.para(y, b["applications_deck"], font="FellIt", size=11.5, lead=15)
        y -= 8
        for p in b["applications"]:
            # Keep each short trial instruction with its claim tag on one leaf.
            body = TAG.sub("", p)
            lines = wrap(body, "Fell", BODY, self.width() - (22 if TAG.match(p) else 0))
            if len(lines) * LEAD <= PH - TOP - BOTTOM:
                y = self.ensure(y, len(lines) * LEAD)
            y = self.para(y, p)
            y -= 6
        self.new_page()
        self.running = "clavis"
        self.outline.append(("Clavis", self.n))
        y = self.heading(PH - TOP, "Clavis", 20)
        for p in b["clavis"]:
            y = self.para(y, p)
            y -= 6
        y -= 8
        y = self.small_caps(y, "of the hands")
        y = self.para(y, b["hands"])
        self.new_page()
        self.running = "register of debts"
        self.outline.append(("Register of debts", self.n))
        y = self.heading(PH - TOP, "Register of debts", 20)
        for r in d["references"]:
            y = self.ensure(y, 60)
            self.c.setFont("FellSC", 9)
            self.c.setFillColorRGB(*INK)
            self.c.drawString(self.x0(), y, r["id"])
            y = self.para(y, r["citation"], size=10, lead=13.5, indent=30)
            y = self.para(y, "Inspection: " + r["status"], font="FellIt", size=9.5, lead=13, indent=30)
            y = self.para(y, "Use: " + r["use"], size=9.5, lead=13, indent=30)
            if r.get("url"):
                y = self.para(y, r["url"], font="Mono", size=7.5, lead=11, indent=30)
            y -= 6
        self.new_page(blank=True)

    # --------------------------------------------------------------- build --
    def build(self, out):
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
        for i, page in enumerate(text.pages, start=1):
            if i in self.plates:
                kind, src = self.plates[i]
                if kind == "reading":
                    pl = PdfReader(src).pages[0]
                else:
                    import cairosvg
                    pb = io.BytesIO(cairosvg.svg2pdf(url=src, background_color="#ede6d4"))
                    pl = PdfReader(pb).pages[0]
                pw, ph = float(pl.mediabox.width), float(pl.mediabox.height)
                s = min((PW - 0.6 * 72) / pw, (PH - 0.9 * 72) / ph)
                tx, ty = (PW - pw * s) / 2, (PH - ph * s) / 2 + 6
                page.merge_transformed_page(pl, Transformation().scale(s, s).translate(tx, ty))
            w.add_page(page)
        for title, pg in self.outline:
            w.add_outline_item(title, pg - 1)
        w.add_metadata({"/Title": self.d["title"], "/Author": self.d["author"]})
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            w.write(f)
        print("pages", len(w.pages), "plates merged", len(self.plates))


if __name__ == "__main__":
    bp.fonts()
    data = json.load(open(os.path.join(HERE, "manuscript", "book.json")))
    Book(data).build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "output", "Clavicula_Graduum.pdf"))
