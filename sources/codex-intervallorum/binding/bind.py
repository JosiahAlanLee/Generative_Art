"""Bind the active books into one 7 x 10 in PDF with front matter and an outline.

Books that are already 504 x 720 pt are merged as they are. The active opening
is the consolidated Matricis et Intervallorum. The generic scaler remains for
other trims, including archived source editions when selected explicitly.
The active edition typesets one bibliography and production section at the end.
Retained reading leaves keep their physical parity. The older relocation-only
path remains for archival components; source PDFs are never overwritten.

    python binding/bind.py            -> binding/out/Codex_Intervallorum_reading.pdf
"""
import io
import hashlib
import json
import os
import re
import sys

import fitz
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
PW, PH = 504.0, 720.0            # 7 x 10 in
PAPER = "#ede6d4"          # Intervallorum/Escalationum paper
MATRICIS_PAPER = "#ebe1c7"  # sampled from the e-reader edition
INK = "#161918"
RED = "#8b2a22"

# The parable is unnumbered, like the Clavis, and follows it in both bindings.
ACCUSATOR = ("Accusator", "De Officio Accusatoris", "A parable of the adversary, who did not fall",
             "books/00_accusator/out/De_Officio_Accusatoris_reading.pdf", "Claude (text and setting); plates ChatGPT")
# The second parable is unnumbered too, and stands before Book VI in both bindings. It was
# placed to introduce the Tarot of Intervals, which De Potestate et Accusatione replaced.
MATRES = ("Matres", "De Matribus Noctis", "A parable of the night mother, who was never one",
          "books/00_matres/out/De_Matribus_Noctis_reading.pdf", "Claude (text and setting)")
# Book VI in both bindings since 19 October 2026; the Tarot is kept as a separate volume.
POTESTATE = ("VI", "De Potestate et Accusatione", "Power, accusation and the obligations of participation, in eleven sections",
             "books/06_disputationes/out/De_Potestate_et_Accusatione_reading.pdf",
             "ChatGPT/Codex (second draft); Claude (third draft, plates and setting)")
# The sealed gathering closes Book VII, after its seventy-two seals; unnumbered, like the Clavis.
CLAUSA = ("Clausa", "Nota Clausa", "Seven fields grown by a printed rule, closing Book VII; the key is not printed",
          "books/07_septimus/clausa/out/Nota_Clausa_reading.pdf", "Claude (text, rule, plates and reading edition)")

BOOKS = [
    ("Clavis", "Clavis", "A way into the several books, in plain prose",
     "books/07_septimus/out/Clavis_Septimus_reading.pdf", "ChatGPT/Codex (reading text), from Claude's brief and research"),
    ACCUSATOR,
    ("I-II", "Clavicula Matricis et Intervallorum", "Correction, maintenance and contested purpose, in seventeen tables",
     "books/01_matricis_intervallorum/out/Clavicula_Matricis_et_Intervallorum.pdf", "Claude and ChatGPT/Codex; consolidated by ChatGPT/Codex"),
    ("III", "Pseudomonarchia Escalationum", "Seven offices and twenty-one handoff demons",
     "books/03_escalationum/output/Pseudomonarchia_Escalationum.pdf", "ChatGPT/Codex"),
    ("IV", "Clavicula Graduum", "A little key to the steps: twelve tables with the manuscript in draft",
     "books/04_graduum/output/Clavicula_Graduum.pdf", "Claude, with ChatGPT/Codex proofs for IX-XI"),
    ("V", "Ars Notoria Stigmatum", "Three divinatory arts and five computed notae, in a developmental reading edition",
     "books/05_notoria/manuscript/out/Ars_Notoria_Stigmatum_reading.pdf", "Claude and ChatGPT/Codex"),
    MATRES,
    POTESTATE,
    ("VII", "De Vinculis", "Compulsion, judgment and service, in seven operations",
     "books/07_septimus/out/De_Vinculis_reading.pdf", "ChatGPT/Codex, from Claude's brief and research"),
    CLAUSA,
]


def fonts():
    fd = os.path.join(REPO, "common", "fonts")
    pdfmetrics.registerFont(TTFont("Fell", os.path.join(fd, "IMFeENrm28P.ttf")))
    pdfmetrics.registerFont(TTFont("FellIt", os.path.join(fd, "IMFeENit28P.ttf")))
    pdfmetrics.registerFont(TTFont("FellSC", os.path.join(fd, "IMFeENsc28P.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", os.path.join(fd, "IBMPlexMono-Regular.ttf")))


def paper(c):
    c.setFillColor(HexColor(PAPER))
    c.rect(0, 0, PW, PH, stroke=0, fill=1)


def wrapped_lines(text, font, size, width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and pdfmetrics.stringWidth(candidate, font, size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + ([line] if line else [])


def front_matter(present, bibliography=None):
    """Title, contents, binding note, blank verso; the first book starts recto."""
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(PW, PH), invariant=1, pageCompression=1)
    c.setTitle("Codex Intervallorum — Libri Septem (reading draft)")
    c.setAuthor("Josiah Alan-Lee")
    # title
    paper(c)
    c.setFillColor(HexColor(INK))
    c.setFont("FellSC", 30)
    c.drawCentredString(PW / 2, 470, "CODEX INTERVALLORUM")
    c.setFont("FellIt", 13)
    c.drawCentredString(PW / 2, 440, "Libri Septem")
    c.setFont("Fell", 11)
    c.drawCentredString(PW / 2, 300, "Josiah Alan-Lee")
    c.setFont("FellIt", 10)
    c.drawCentredString(PW / 2, 282, "with several hands, named in the colophon")
    c.setFillColor(HexColor(RED))
    c.setFont("FellSC", 9)
    c.drawCentredString(PW / 2, 120, "DRAFT BINDING")
    c.showPage()
    # contents
    paper(c)
    c.setFillColor(HexColor(INK))
    c.setFont("FellSC", 16)
    c.drawCentredString(PW / 2, 640, "The Books")
    y = 590
    for num, title, sub, path, hand in BOOKS:
        c.setFont("FellSC", 12)
        c.drawString(72, y, numeral(num))
        c.drawString(110, y, title if num != "Companion" else f"{num}: {title}")
        c.setFont("FellIt", 10)
        c.drawString(110, y - 15, sub)
        c.setFont("Fell", 8.5)
        credit = f"hand: {hand}" if len(hand) < 55 else "hands: see colophon"
        c.drawString(110, y - 28, credit)
        c.setFont("Mono", 7.5)
        pg = present.get(num)
        c.drawString(110, y - 40, f"pages {pg[0]}–{pg[1]}" if pg else "not bound in this draft")
        y -= 64
    if bibliography:
        c.setFont("FellSC", 12)
        c.drawString(110, 198, "Bibliography and Source Registers")
        c.setFont("Mono", 7.5)
        c.drawString(110, 184, f"pages {bibliography['start_page']}–{bibliography['end_page']}")
    c.setFont("FellIt", 9)
    c.drawCentredString(PW / 2, 150, "Original folios are retained; source registers are gathered at the end.")
    c.drawCentredString(PW / 2, 136, "The binding adds front matter, alignment blanks, and a colophon.")
    c.showPage()
    # note on the binding
    paper(c)
    c.setFillColor(HexColor(INK))
    c.setFont("FellSC", 12)
    c.drawCentredString(PW / 2, 640, "Of the Binding")
    c.setFont("Fell", 10.5)
    lines = [
        "The Clavis opens the volume as a plain-prose entrance to the books.",
        "The opening pair is joined as Clavicula Matricis et Intervallorum, a new",
        "reading edition at the common trim. Its seventeen tables replace both",
        "earlier components. Their source editions remain in the repository.",
        "The identifiers I-II, III, IV, V and VI preserve the books' references",
        "while the series develops. Book VI is De Potestate et Accusatione.",
        "The hands are recorded in the contents and again in the colophon, which",
        "precedes the collected bibliography. Source keys and inspection limits",
        "remain grouped by book. Blank leaves preserve the retained pages' parity.",
    ]
    yy = 600
    for ln in lines:
        c.drawCentredString(PW / 2, yy, ln)
        yy -= 16
    c.showPage()
    paper(c)
    c.showPage()  # keep the first component's local odd pages on physical rectos
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def numeral(num):
    """The contents numeral for a book; unnumbered components (the Clavis) carry none."""
    return f"{num}." if re.fullmatch(r"[IVX]+(?:-[IVX]+)?", num) else ""


def label(num, title):
    return f"{num}. {title}" if numeral(num) else title


def colophon():
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(PW, PH), invariant=1, pageCompression=1)
    paper(c)
    c.setFillColor(HexColor(INK))
    c.setFont("FellSC", 16)
    c.drawCentredString(PW / 2, 640, "Colophon")
    y = 595
    for num, title, sub, path, hand in BOOKS:
        c.setFont("FellSC", 11)
        c.drawString(72, y, label(num, title))
        y -= 18
        c.setFont("Fell", 10)
        for line in wrapped_lines(f"Hand: {hand}", "Fell", 10, PW - 144):
            c.drawString(72, y, line)
            y -= 14
        y -= 20
    c.setFont("FellIt", 10)
    c.drawString(72, y - 8, "Binding and editorial revision: ChatGPT/Codex, 17 October 2026.")
    c.drawString(72, y - 24, "Source registers follow, with their original inspection limits.")
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def blank_leaf(color=PAPER):
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(PW, PH), invariant=1)
    c.setFillColor(HexColor(color))
    c.rect(0, 0, PW, PH, stroke=0, fill=1)
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def bibliography_pages(title, source):
    """Locate dedicated register leaves, leaving workshop/colophon prose in place.

    Selectors are deliberately book-specific. A known book without its expected
    register fails rather than silently publishing a partial bibliography.
    """
    tail_markers = {"Clavicula Matricis": "debts", "Clavicula Graduum": "register of debts"}
    if title in ("Clavis", "De Vinculis", "De Officio Accusatoris", "De Matribus Noctis", "De Potestate et Accusatione"):
        # The shared renderer heads its register leaves BIBLIOGRAPHY; the preparation
        # leaf that follows moves with the production notes (unified.MOVE_HEADINGS).
        with fitz.open(source) as document:
            selected = [i + 1 for i, p in enumerate(document)
                        if "bibliography" in [" ".join(l.split()).casefold() for l in p.get_text().splitlines()]]
        if not selected:
            raise ValueError(f"Cannot locate the {title} bibliography; update the selector before binding")
        return selected
    if title == "Ars Notoria Stigmatum":
        with fitz.open(source) as document:
            lines = [" ".join(p.get_text().split()).casefold() for p in document]
        starts = [i for i, text in enumerate(lines) if "source trail" in text[:200]]
        if not starts:
            raise ValueError("Cannot locate Book V's source trail")
        return [i + 1 for i in range(starts[0], len(lines)) if lines[i]]
    if title not in tail_markers and title not in ("Clavicula Intervallorum", "Clavicula Matricis et Intervallorum", "Pseudomonarchia Escalationum"):
        return []
    with fitz.open(source) as document:
        lines = [[" ".join(line.split()).casefold() for line in p.get_text().splitlines()]
                 for p in document]
    if title in tail_markers:
        starts = [i for i, page in enumerate(lines) if tail_markers[title] in page]
        selected = [i + 1 for i in range(starts[0], len(lines)) if any(lines[i])] if starts else []
    elif title in ("Clavicula Intervallorum", "Clavicula Matricis et Intervallorum"):
        selected = [i + 1 for i, page in enumerate(lines) if "reference register" in page or (
            title == "Clavicula Matricis et Intervallorum" and ("bibliography" in page or "production notes" in page))]
    elif title == "Pseudomonarchia Escalationum":
        selected = [i + 1 for i, page in enumerate(lines)
                    if any(re.fullmatch(r"a register of debts / [ivx]+", line) for line in page)]
    else:
        return []
    if not selected:
        raise ValueError(f"Cannot locate bibliography in {title}; update the selector before binding")
    return selected


def add_source_page(writer, page, num):
    pw, ph = float(page.mediabox.width), float(page.mediabox.height)
    if abs(pw - PW) < 1 and abs(ph - PH) < 1:
        writer.add_page(page)
        return
    s = min(PW / pw, PH / ph)
    leaf = blank_leaf(MATRICIS_PAPER if num == "I" else PAPER)
    tx, ty = (PW - pw * s) / 2, (PH - ph * s) / 2
    leaf.merge_transformed_page(page, Transformation().scale(s, s).translate(tx, ty))
    writer.add_page(leaf)


def bibliography_cover(sections):
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(PW, PH), invariant=1, pageCompression=1)
    paper(c)
    c.setFillColor(HexColor(INK))
    c.setFont("FellSC", 20)
    c.drawCentredString(PW / 2, 640, "Bibliography")
    c.setFont("FellIt", 12)
    c.drawCentredString(PW / 2, 616, "and registers of debts")
    y = 568
    c.setFont("Fell", 10.5)
    intro = ("The source leaves of the included books are collected here. Each keeps its "
             "citation keys, acknowledgments, inspection notes and original folios. Keys are "
             "local to their book: I-II/B1 and IV/B1 identify different entries. Repeated authors "
             "retain the editions and inspection limits recorded by each book.")
    for line in wrapped_lines(intro, "Fell", 10.5, PW - 144):
        c.drawString(72, y, line)
        y -= 15
    y -= 25
    for section in sections:
        c.setFont("FellSC", 12)
        c.drawString(72, y, f"{section['book']}. {section['title']}")
        c.setFont("Mono", 8)
        c.drawString(72, y - 18, f"pages {section['start_page']}–{section['end_page']}")
        y -= 60
    c.setFont("FellIt", 10)
    c.drawString(72, y - 8, "Body citations remain beside the claims they support.")
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def main(out=None):
    if any(title == "Clavicula Matricis et Intervallorum" for _, title, _, _, _ in BOOKS):
        if HERE not in sys.path:sys.path.insert(0,HERE)
        import unified
        return unified.main(sys.modules[__name__],out or os.path.join(HERE,"out","Codex_Intervallorum_reading.pdf"))
    fonts()
    out = out or os.path.join(HERE, "out", "Codex_Intervallorum_reading.pdf")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    w = PdfWriter()
    present = {}
    # placeholder for front matter page numbers: build books first, then prepend
    body = PdfWriter()
    front_count = len(front_matter({}).pages)
    page_no = front_count + 1
    log = {}
    registers = []
    for num, title, sub, path, hand in BOOKS:
        if not path:
            continue
        r = PdfReader(os.path.join(REPO, path))
        if not r.pages:
            raise ValueError(f"Empty component: {path}")
        moved = bibliography_pages(title, os.path.join(REPO, path))
        moved_set = set(moved)
        body_map, body_blanks = {}, []
        blank_before = page_no % 2 == 0
        if blank_before:
            body.add_page(blank_leaf())
            page_no += 1
        start = page_no
        for source_no, p in enumerate(r.pages, 1):
            if source_no in moved_set:
                continue
            # A register can precede workshop prose. Removing an odd number of
            # leaves must not flip that surviving prose to the other page side.
            if page_no % 2 != source_no % 2:
                body.add_page(blank_leaf())
                body_blanks.append(page_no)
                page_no += 1
            add_source_page(body, p, num)
            body_map[str(source_no)] = page_no
            page_no += 1
        if moved:
            registers.append((num, title, r, moved))
        present[num] = (start, page_no - 1)
        with open(os.path.join(REPO, path), "rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        pw, ph = float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)
        log[title] = {"source": path, "source_sha256": digest,
                      "pages": page_no - start, "source_pages": len(r.pages),
                      "body_page_map": body_map, "body_blank_pages": body_blanks,
                      "bibliography_source_pages": moved,
                      "start_page": start, "end_page": page_no - 1,
                      "blank_before": blank_before,
                      "trim_mm": [round(pw / 72 * 25.4), round(ph / 72 * 25.4)],
                      "scaled": not (abs(pw - PW) < 1 and abs(ph - PH) < 1)}
    colophon_page = page_no
    page_no += len(colophon().pages)
    bibliography = None
    appendix = PdfWriter()
    if registers:
        if page_no % 2 == 0:
            appendix.add_page(blank_leaf())
            page_no += 1
        bib_start = page_no
        page_no += 1  # cover, filled after the source ranges are known
        register_body = PdfWriter()
        sections, blank_pages = [], []
        for num, title, reader, moved in registers:
            mapping = []
            for source_no in moved:
                if page_no % 2 != source_no % 2:
                    register_body.add_page(blank_leaf())
                    blank_pages.append(page_no)
                    page_no += 1
                add_source_page(register_body, reader.pages[source_no - 1], num)
                mapping.append({"source_page": source_no, "bound_page": page_no})
                page_no += 1
            sections.append({"book": num, "title": title, "page_map": mapping,
                             "start_page": mapping[0]["bound_page"], "end_page": mapping[-1]["bound_page"]})
        bibliography = {"start_page": bib_start, "end_page": page_no - 1,
                        "sections": sections, "blank_pages": blank_pages,
                        "source_pages": sum(len(s[3]) for s in registers)}
        for p in bibliography_cover(sections).pages:
            appendix.add_page(p)
        for p in register_body.pages:
            appendix.add_page(p)
    fm = front_matter(present, bibliography)
    for p in fm.pages:
        w.add_page(p)
    for p in body.pages:
        w.add_page(p)
    for p in colophon().pages:
        w.add_page(p)
    for p in appendix.pages:
        w.add_page(p)
    # outline: one entry per book
    w.add_outline_item("Title", 0)
    w.add_outline_item("The Books", 1)
    for num, title, sub, path, hand in BOOKS:
        if num in present:
            w.add_outline_item(f"{num}. {title}", present[num][0] - 1)
    w.add_outline_item("Colophon", colophon_page - 1)
    if bibliography:
        parent = w.add_outline_item("Bibliography and Source Registers", bibliography["start_page"] - 1)
        for section in bibliography["sections"]:
            w.add_outline_item(f"{section['book']}. {section['title']}", section["start_page"] - 1, parent=parent)
    w.add_metadata({"/Title": "Codex Intervallorum — Libri Septem (reading draft)", "/Author": "Josiah Alan-Lee"})
    with open(out, "wb") as f:
        w.write(f)
    log["total_pages"] = len(w.pages)
    log["front_matter_pages"] = front_count
    log["colophon_page"] = colophon_page
    log["bibliography"] = bibliography
    with open(os.path.join(os.path.dirname(out), "binding-log.json"), "w") as f:
        json.dump(log, f, indent=1)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

