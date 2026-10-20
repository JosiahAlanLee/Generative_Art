"""Tarot of Intervals: a reading edition in book form. Each card on a recto, its commentary on the
facing verso. The commentary text is ChatGPT/Codex's from the deck records (symbolism, opening,
snag, question), set verbatim; the "In the books" line is derived from each card's recorded source
figure. The flourish on each verso is generated from the card's own hash in the Matricis stroke
vocabulary. The Major Arcana carry their keywords in the twelve-mark hand at a shift equal to the
card's number; the pips carry nothing hidden.

7 x 10 in, to match the master binding. Build: python3 make_book.py [out.pdf]
"""
import argparse
import hashlib
import json
import math
import os
import random
import sys

from reportlab.lib.pagesizes import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TAROT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(REPO, "common", "geometry"))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
from core import Wobble, catmull, arc_pts, curl_pts  # noqa: E402
import marks  # noqa: E402
import tx  # noqa: E402

PW, PH = 7 * inch, 10 * inch
PAPER = (0xED / 255, 0xE6 / 255, 0xD4 / 255)
INK = (0x16 / 255, 0x19 / 255, 0x18 / 255)
RED = (0xA3 / 255, 0x2B / 255, 0x24 / 255)
MM = 72 / 25.4
FONTS = os.path.join(REPO, "common", "fonts")
OUTER, INNER, TOP, BOTTOM = 0.95 * inch, 1.0 * inch, 1.15 * inch, 0.9 * inch


def fonts():
    pdfmetrics.registerFont(TTFont("Fell", os.path.join(FONTS, "IMFeENrm28P.ttf")))
    pdfmetrics.registerFont(TTFont("FellIt", os.path.join(FONTS, "IMFeENit28P.ttf")))
    pdfmetrics.registerFont(TTFont("FellSC", os.path.join(FONTS, "IMFeENsc28P.ttf")))
    pdfmetrics.registerFont(TTFont("FellTitle", os.path.join(FONTS, "IMFellEnglish-Regular.ttf")))


# ------------------------------------------------------------- a hand on the page --

class PageHand:
    """the Matricis Hand interface drawn straight onto a ReportLab canvas. Coordinates in mm from an
    origin at the top-left of a box; y runs down, as on the plates."""
    W = {"core": 0.8, "orn": 0.5, "hair": 0.28, "cip": 0.5}

    def __init__(self, c, ox, oy, rng, amp=0.07):
        self.c, self.ox, self.oy, self.rng = c, ox, oy, rng
        self.wob = Wobble(rng, amp, wl=(22 * 0.157, 61 * 0.157))
        self.amp = amp
        self.colors = {"ink": INK, "red": RED}

    def _p(self, x, y):
        return self.ox + x * MM, self.oy - y * MM

    def _poly(self, pts, weight, color):
        self.c.setStrokeColorRGB(*self.colors[color])
        self.c.setLineWidth(self.W[weight])
        self.c.setLineCap(1)
        self.c.setLineJoin(1)
        p = self.c.beginPath()
        p.moveTo(*self._p(*pts[0]))
        for q in pts[1:]:
            p.lineTo(*self._p(*q))
        self.c.drawPath(p, stroke=1, fill=0)

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None, attrs=""):
        pts = list(pts)
        if len(pts) < 2:
            return
        if closed:
            pts = pts + [pts[0]]
        a = self.amp if amp is None else self.amp * amp / 0.5
        self._poly(self.wob(pts, a, step=0.5), weight, color)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs=""):
        pts = list(pts)
        if closed:
            pts = pts + [pts[0]]
        self._poly(pts, weight, color)

    def dot(self, x, y, r, color="ink"):
        self.c.setFillColorRGB(*self.colors[color])
        X, Y = self._p(x, y)
        self.c.circle(X, Y, max(0.25, r) * MM, stroke=0, fill=1)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.stroke(arc_pts(x, y, r, 0, 360, max(24, int(r * 14))), weight, color, amp=0.2)

    def fill_poly(self, pts, color="ink", step=0.45, ang=45):
        from core import hatch_lines
        from shapely.geometry import Polygon
        for ln in hatch_lines(Polygon(pts), step, ang):
            self.stroke(ln, "hair", color, amp=0.05)
        self.stroke(pts, "orn", color, closed=True)


# --------------------------------------------------------------------- flourish --

def flourish(c, x0, y_top, width_mm, seed, kind):
    """a band under the title: a few lines that drift across and end in Book I's terminals,
    from the card's own hash. kind picks the vocabulary: 'major' gets a sigil at the right end,
    'swords' straight-ish lines with cut terminals, 'cups' slow curves with pooled dots, 'extra'
    a dispersal."""
    rng = random.Random(seed)
    h = PageHand(c, x0, y_top, rng)
    n = 3 if kind != "extra" else 5
    for i in range(n):
        y = 2.0 + i * 2.1 + rng.uniform(-0.3, 0.3)
        pts = [(0.0, y)]
        x = 0.0
        while x < width_mm - 14:
            x += rng.uniform(9, 16)
            drift = rng.uniform(-1.4, 1.4) if kind != "swords" else rng.uniform(-0.3, 0.3)
            pts.append((min(x, width_mm - 14), y + drift))
        end_x = width_mm - 14 + rng.uniform(0, 6)
        pts.append((end_x, y + rng.uniform(-0.6, 0.6)))
        cpts = catmull(pts, 6)
        h.stroke(cpts, "hair", "ink", amp=0.35)
        ex, ey = cpts[-1]
        if kind == "cups":
            h.dot(ex + 0.6, ey, 0.42, "ink")
        elif kind == "swords":
            h.stroke([(ex, ey - 0.9), (ex + 1.6, ey + 0.9)], "hair", "ink", amp=0.1)
        elif kind == "wands":
            h.stroke([(ex, ey), (ex + 1.4, ey - 1.6), (ex + 2.6, ey - 0.2)], "hair", "ink", amp=0.3)
            h.dot(ex + 1.4, ey - 1.6, 0.3, "ink")
        elif kind == "pentacles":
            h.ring(ex + 1.0, ey, 0.75, "hair", "ink")
            h.dot(ex + 1.0, ey, 0.22, "ink")
        elif kind == "extra":
            for k in range(3):
                h.stroke([(ex, ey), (ex + rng.uniform(1, 4), ey + rng.uniform(-2.5, 2.5))], "hair", "ink", amp=0.4)
        else:
            pts2 = curl_pts(ex, ey, 0, 1.2, 1.1, 1.25, hand=1 if i % 2 else -1)
            h.stroke(pts2, "hair", "ink", amp=0.2)
            h.dot(pts2[-1][0], pts2[-1][1], 0.3, "ink")
    # the hanging lines of the series, a few, from the band's underside
    for k in range(rng.randint(2, 4)):
        x = rng.uniform(4, width_mm - 20)
        y0 = 2.0 + (n - 1) * 2.1 + 0.4
        y1 = y0 + rng.uniform(2.5, 7.0)
        h.straight([(x, y0), (x, y1)], "hair", "ink")
        h.dot(x, y1 + 0.3, 0.3, "ink")
    if kind == "major":
        marks.asterisk(h, width_mm - 3.0, 4.0, 1.4, 8, weight="hair")
    return 2.0 + (n - 1) * 2.1 + 8.0


def margin_threads(c, x_mm, y_top, seed, n=5):
    rng = random.Random(seed + "threads")
    h = PageHand(c, x_mm, y_top, rng)
    for k in range(n):
        x = k * 2.6 + rng.uniform(-0.4, 0.4)
        L = rng.uniform(4, 16)
        col = "red" if k == n // 2 and rng.random() < 0.5 else "ink"
        h.straight([(x, 0), (x, L)], "hair", col)
        h.dot(x, L + 0.35, 0.3, col)


def cipher_strip(c, x0, y_base, width_pt, text, shift, s=2.4):
    """the keywords in the twelve-mark hand, base marks advanced by `shift`"""
    rng = random.Random(shift)
    wdt = tx.width(text, s) * MM
    x = x0 + (width_pt - wdt) / 2
    h = PageHand(c, x, y_base, rng, amp=0.03)
    cx = 0.0
    for wi, w in enumerate(tx.encode(text)):
        if wi:
            cx += 0.55 * s
        for (b, t) in w:
            tx.mark(h, (b - 1 + shift) % 12 + 1, cx, 0, s, "orn", "ink")
            tx.tally(h, t, cx, 0, s, "ink")
            cx += tx.token_width(t, s)


# ------------------------------------------------------------------------- text --

def wrap(text, font, size, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(c, x, y, width, text, font="Fell", size=12, lead=16.5, color=INK):
    c.setFillColorRGB(*color)
    c.setFont(font, size)
    for ln in wrap(text, font, size, width):
        c.drawString(x, y, ln)
        y -= lead
    return y


def labelled(c, x, y, width, label, text, color=INK):
    c.setFont("FellSC", 9.5)
    c.setFillColorRGB(*INK)
    c.drawString(x, y, label.upper())
    return para(c, x + 84, y, width - 84, text, color=color)


# ------------------------------------------------------------------------ pages --

def paper(c):
    c.setFillColorRGB(*PAPER)
    c.rect(0, 0, PW, PH, stroke=0, fill=1)


def folio(c, n, running):
    c.setFont("FellSC", 7.5)
    c.setFillColorRGB(*INK)
    if n % 2 == 0:
        c.drawString(OUTER, BOTTOM - 24, str(n))
        c.drawString(OUTER + 30, BOTTOM - 24, running.upper())
    else:
        c.drawRightString(PW - OUTER, BOTTOM - 24, str(n))
        c.drawRightString(PW - OUTER - 30, BOTTOM - 24, running.upper())


def verso(c, card, n, running):
    paper(c)
    x0 = OUTER
    width = PW - OUTER - INNER
    y = PH - TOP
    # numeral and archetype
    c.setFillColorRGB(*INK)
    c.setFont("FellTitle", 30)
    c.drawString(x0, y - 8, card["numeral"])
    archetype_x = x0 + max(56, pdfmetrics.stringWidth(card["numeral"], "FellTitle", 30) + 12)
    c.setFont("FellSC", 10.5)
    c.drawString(archetype_x, y - 8, card["archetype"].upper())
    y -= 42
    c.setFont("FellTitle", 24)
    c.drawString(x0, y, card["title"])
    y -= 19
    c.setFont("FellSC", 9.5)
    c.setFillColorRGB(*RED)
    c.drawString(x0, y, card["keywords"].upper())
    c.setFillColorRGB(*INK)
    y -= 6
    band = flourish(c, x0, y, width / MM, card["seed"], card["kind"])
    y -= band * MM + 4
    y = para(c, x0, y, width, card["symbolism"])
    y -= 12
    y = labelled(c, x0, y, width, "Opening", card["upright"])
    y -= 4
    y = labelled(c, x0, y, width, "Snag", card["reversed"])
    y -= 14
    c.setFont("FellIt", 13.5)
    c.setFillColorRGB(*RED)
    for ln in wrap(card["question"], "FellIt", 13.5, width):
        c.drawString(x0, y, ln)
        y -= 18
    c.setFillColorRGB(*INK)
    if card.get("in_books"):
        y -= 14
        y = labelled(c, x0, y, width, "In the books", card["in_books"])
    if card.get("will_note"):
        c.setFont("FellSC", 8.5)
        c.setFillColorRGB(*INK)
        c.drawString(x0, BOTTOM + 44, "ON THE WILL")
        c.setFont("FellIt", 10.5)
        yy = BOTTOM + 30
        for ln in wrap(card["will_note"], "FellIt", 10.5, width):
            c.drawString(x0, yy, ln)
            yy -= 14
    margin_threads(c, OUTER * 0.38, PH - TOP + 2, card["seed"])
    if card["kind"] == "major":
        cipher_strip(c, x0, BOTTOM + 4, width, card["keywords"].replace("/", " "), card["number"] % 12, s=2.8)
    folio(c, n, running)


def light_image(path, width=1100):
    """a resampled JPEG for the mockup, so the PDF stays mailable; the archive keeps the PNGs"""
    from PIL import Image
    import io
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    buf.seek(0)
    return ImageReader(buf)


def recto(c, card, n, running):
    paper(c)
    img = light_image(card["image"])
    iw, ih = img.getSize()
    target_h = PH - TOP - BOTTOM + 10
    s = target_h / ih
    w, h_ = iw * s, ih * s
    if w > PW - OUTER - INNER + 10:
        s = (PW - OUTER - INNER + 10) / iw
        w, h_ = iw * s, ih * s
    x = INNER + (PW - INNER - OUTER - w) / 2
    y = BOTTOM - 5 + (target_h - h_) / 2
    c.drawImage(img, x, y, w, h_, mask=None)
    folio(c, n, running)


def title_pages(c, n, edition="full"):
    paper(c)
    c.setFillColorRGB(*INK)
    c.setFont("FellTitle", 30)
    c.drawCentredString(PW / 2, PH * 0.6, "Tarot of Intervals")
    c.setFont("FellSC", 10)
    c.drawCentredString(PW / 2, PH * 0.6 - 26, "A READING EDITION IN BOOK FORM")
    c.setFont("Fell", 10.5)
    c.drawCentredString(PW / 2, PH * 0.6 - 60,
                         "Twenty-two Majors, Swords, Cups, and two Choronzon studies" if edition == "initial"
                         else "Twenty-two Major Arcana, four suits of fourteen, and one extra arcanum")
    c.drawCentredString(PW / 2, PH * 0.6 - 76, "from Codex Intervallorum")
    rng = random.Random("title")
    h = PageHand(c, PW / 2 - 30 * MM, PH * 0.6 - 100, rng)
    marks.sig_boundary(h, 30, 6, 4.0, orn=0)
    c.setFont("FellSC", 8)
    c.drawCentredString(PW / 2, BOTTOM, "JOSIAH ALAN-LEE  ·  MOCKUP, 17 OCTOBER 2026")
    c.showPage()
    n += 1
    paper(c)
    x0, width = OUTER, PW - OUTER - INNER
    y = PH - TOP
    c.setFont("FellTitle", 16)
    c.setFillColorRGB(*INK)
    c.drawString(x0, y, "Of this edition")
    y -= 26
    notes = [
        "The cards are the concept editions made with ChatGPT/Codex and archived in the Codex Intervallorum repository: the Major Arcana (eighteen figures reused from the series' references, four new), the Swords, the Cups, the Wands and the Pentacles (new illustrations in the series' hand, the last two drawing their figures from the Goetia), and Choronzon, an extra unnumbered arcanum in two studies. Seventy-nine cards. They are set here at the size they would take on a seven-by-ten leaf, one to a recto.",
        "The commentary on each facing verso is the deck's own: the symbolism, the Opening and Snag readings, and the question, as recorded in the deck files, set verbatim and unedited. The lower names belong to this deck; the upper names identify the conventional correspondence. The meanings are editorial choices made for the art pack and claim no lineage and no predictive method.",
        "The Wands were drafted as text first and illustrated to the draft; the illustrator kept three cards as written and re-titled eleven, and its key is the text printed here. Four Wands carry a line headed On the will from the draft, where the image still shows what the line says. The line headed In the books is otherwise this edition's only addition to the text. It gives, where the deck records one, the figure or office the card was drawn from and the book and plate it belongs to.",
        "The flourish under each title is generated from the card's own hash in the stroke vocabulary of the first book, and is different for every card. It carries nothing. The Major Arcana carry one thing more: a strip in the twelve-mark hand along the foot of the verso, which is the card's keywords with every base mark advanced by the card's number; the pips carry nothing hidden. Black records an arrangement; red marks an intervention, a question or a consequence.",
        "Known matters: the Queen of Cups and the fourteenth Major share the lower name The Second Neck; the Ace of Wands and the Ace of Cups are both 'first' cards under different names. The Empty Seat's ground is lighter than its neighbours'. Choronzon is shown in both studies; the second is the one whose centre is empty, and the title is true of that one.",
    ]
    if edition == "initial":
        notes[0] = "This initial reading mockup contains 52 illustrations: twenty-two Major Arcana, fourteen Swords, fourteen Cups, and two Choronzon studies. It preserves the selection introduced in commit cb8ed54. Wands and Pentacles, added to the wider project later, are excluded from this edition. Each archived raster card is resampled for this mockup and placed whole on a right-hand recto, facing its commentary on the left. The archive images remain the masters; this is not a final print edition."
        notes[2] = "The line headed In the books gives, where the deck records one, the figure or office the card was drawn from and the book and plate it belongs to. Choronzon's question and source note are editorial additions. A blank third page aligns the 52 facing spreads on pages 4 through 107."
        notes[4] = "Known matters: the Queen of Cups and the fourteenth Major share the lower name The Second Neck. The Empty Seat's ground is lighter than its neighbours'. Choronzon is shown in both studies; the second is the one whose centre is empty, and the title is true of that one."
    for t in notes:
        y = para(c, x0, y, width, t, size=10, lead=13.5)
        y -= 9
    folio(c, n, "of this edition")
    c.showPage()
    return n + 1


# ------------------------------------------------------------------------- data --

def load_cards(edition="full"):
    cards = []
    d = json.load(open(os.path.join(TAROT, "major-arcana", "deck.json")))
    for m in d["cards"]:
        sa = m.get("source_art") or {}
        inb = None
        if isinstance(sa, dict):
            bits = []
            if sa.get("office"):
                bits.append(sa["office"])
            elif sa.get("subject") and sa.get("book"):
                bits.append(sa["subject"].title() if sa["subject"].isupper() else sa["subject"])
            if sa.get("book"):
                b = sa["book"]
                if sa.get("plate"):
                    b += f", plate {sa['plate']}"
                bits.append(b)
            if bits:
                inb = "; ".join(bits) + "."
            elif sa.get("subject") and not sa.get("book"):
                inb = f"New for the deck: {sa['subject']}."
        cards.append({"kind": "major", "number": m["number"], "numeral": m["numeral"], "archetype": m["archetype"],
                      "title": m["title"], "keywords": m["keywords"], "symbolism": m["symbolism"], "upright": m["upright"],
                      "reversed": m["reversed"], "question": m["question"], "in_books": inb,
                      "image": os.path.join(TAROT, "major-arcana", m["card_file"]), "seed": m["card_sha256"],
                      "running": "major arcana"})
    for suit, fn in (("swords", "swords.json"), ("cups", "cups.json")):
        d = json.load(open(os.path.join(TAROT, suit, fn)))
        for m in d["cards"]:
            cards.append({"kind": suit, "number": None, "numeral": m["numeral"], "archetype": m["archetype"],
                          "title": m["title"], "keywords": m["keywords"], "symbolism": m["symbolism"], "upright": m["upright"],
                          "reversed": m["reversed"], "question": m["question"], "in_books": None,
                          "image": os.path.join(TAROT, suit, m["card_file"]), "seed": m["card_sha256"], "running": suit})
    if edition == "full":
        wd = json.load(open(os.path.join(TAROT, "wands", "delivered", "wands-delivered.json")))
        draft = {c["index"]: c for c in json.load(open(os.path.join(TAROT, "wands", "draft", "wands.json")))["cards"]}
        for m in wd["cards"]:
            dr = draft.get(m["index"], {})
            will = dr.get("will_note") if m["index"] in (6, 9, 11, 13) else None     # the images still carry these
            cards.append({"kind": "wands", "number": None, "numeral": m["numeral"], "archetype": m["archetype"],
                          "title": m["title"], "keywords": m["keywords"], "symbolism": m["symbolism"], "upright": m["upright"],
                          "reversed": m["reversed"], "question": m["question"],
                          "in_books": f"After {m['spirit']}, as the suit's key gives it; a creative adaptation of the draft's Goetic figure, not a historical portrait.",
                          "will_note": will,
                          "image": os.path.join(TAROT, "wands", m["card_file"]), "seed": m["card_file"], "running": "wands"})
        pd = json.load(open(os.path.join(TAROT, "pentacles", "delivered", "pentacles-delivered.json")))
        for m in pd["cards"]:
            cards.append({"kind": "pentacles", "number": None, "numeral": m["numeral"], "archetype": m["archetype"],
                          "title": m["title"], "keywords": m["keywords"], "symbolism": m["symbolism"], "upright": m["upright"],
                          "reversed": m["reversed"], "question": m["question"],
                          "in_books": f"After {m['spirit']}, as the suit's key gives it; a creative association, not a historical portrait.",
                          "image": os.path.join(TAROT, "pentacles", m["card_file"]), "seed": m["card_file"], "running": "pentacles"})
    x = json.load(open(os.path.join(TAROT, "extras", "choronzon", "choronzon.json")))
    for v in x["versions"]:
        cards.append({"kind": "extra", "number": None, "numeral": "·", "archetype": f"Choronzon, study {v['version']}",
                      "title": "The Dispersal", "keywords": "MULTIPLICITY / FALSE CENTRE", "symbolism": x["interpretation"],
                      "upright": "Not assigned: an extra arcanum outside the twenty-two.", "reversed": "Not assigned.",
                      "question": "Which of these faces would answer if the centre were asked?",
                      "in_books": "Not drawn from the books; after The Vision and the Voice, Tenth Aethyr, as the deck's source trail records. The question on this page is this edition's, not the deck's.",
                      "image": os.path.join(TAROT, "extras", "choronzon", v["file"]), "seed": v["sha256"], "running": "extra arcanum"})
    return cards


def validate_initial_sources(cards):
    """Fail before rendering if this edition's selection or archived sources drift."""
    from collections import Counter
    expected = {"major": 22, "swords": 14, "cups": 14, "extra": 2}
    if Counter(c["kind"] for c in cards) != expected:
        raise ValueError("Initial edition requires 22 Majors, 14 Swords, 14 Cups, 2 studies")
    for card in cards:
        for key in ("title", "archetype", "keywords", "symbolism", "upright", "reversed", "question"):
            if not isinstance(card.get(key), str) or not card[key].strip():
                raise ValueError(f"Missing {key}: {card.get('title')}")
        with open(card["image"], "rb") as source:
            if hashlib.sha256(source.read()).hexdigest() != card["seed"]:
                raise ValueError(f"Artwork hash mismatch: {card['image']}")


def main(out, edition="full"):
    fonts()
    cards = load_cards(edition)
    if edition == "initial":
        validate_initial_sources(cards)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    c = canvas.Canvas(out, pagesize=(PW, PH), invariant=1)
    c.setTitle("Tarot of Intervals: a reading edition (mockup)")
    c.setAuthor("Josiah Alan-Lee")
    n = title_pages(c, 1, edition)
    if n % 2 == 1:
        paper(c)
        c.showPage()
        n += 1
    log = []
    for card in cards:
        verso(c, card, n, card["running"])
        c.showPage()
        recto(c, card, n + 1, card["running"])
        c.showPage()
        log.append({"verso": n, "recto": n + 1, "title": card["title"], "kind": card["kind"]})
        n += 2
    c.save()
    json.dump({"pages": n - 1, "cards": log}, open(os.path.splitext(out)[0] + "-log.json", "w"), indent=1)
    print("pages", n - 1, "cards", len(cards))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", nargs="?", default=os.path.join(HERE, "out", "Tarot_of_Intervals_reading_mockup.pdf"))
    parser.add_argument("--edition", choices=("initial", "full"), default="full",
                        help="initial: the 52-illustration / 107-page mockup; full: current binding companion")
    args = parser.parse_args()
    main(args.out, args.edition)


