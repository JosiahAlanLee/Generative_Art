"""Bind the consolidated opening, illustrated Books III-IV, Notoria, and De Potestate et Accusatione as Book VI.

The binder is binding/bind.py, unchanged; this script gives it the illustrated components, a
source-register selector for Book V, and front matter and a colophon that describe this
binding. Run the illustrated builds and Book VI first:

    python books/07_septimus/build.py
    python books/01_matricis_intervallorum/build.py
    python books/03_escalationum/illustrated/build.py
    python books/04_graduum/illustrated/plates.py
    python books/04_graduum/illustrated/build.py
    python books/06_disputationes/build.py
    python books/00_matres/build.py
    python books/07_septimus/clausa/build.py
    python binding/bind_illustrated.py          -> binding/out/illustrated/Codex_Intervallorum_illustrated.pdf
    python binding/validate.py binding/out/illustrated/Codex_Intervallorum_illustrated.pdf
"""
import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "common", "illum"))

import fitz  # noqa: E402
import bind  # noqa: E402
from pypdf import PdfReader  # noqa: E402
from reportlab.lib.colors import HexColor  # noqa: E402
from reportlab.pdfgen.canvas import Canvas  # noqa: E402

bind.BOOKS = [
    ("Clavis", "Clavis", "A way into the several books, in plain prose",
     "books/07_septimus/out/Clavis_Septimus_reading.pdf", "ChatGPT/Codex (reading text), from Claude's brief and research"),
    bind.ACCUSATOR,
    ("I-II", "Clavicula Matricis et Intervallorum", "Correction, maintenance and contested purpose, in seventeen tables",
     "books/01_matricis_intervallorum/out/Clavicula_Matricis_et_Intervallorum.pdf",
     "Claude and ChatGPT/Codex; consolidated setting and frontispiece ChatGPT/Codex"),
    ("III", "Pseudomonarchia Escalationum", "Seven offices and twenty-one handoff spirits, each drawn",
     "books/03_escalationum/illustrated/out/Pseudomonarchia_Escalationum_illustrated.pdf",
     "ChatGPT/Codex; illustrated edition Claude, with ChatGPT figure renders"),
    ("IV", "Clavicula Graduum", "A little key to the steps: twelve tables with the manuscript in draft",
     "books/04_graduum/illustrated/out/Clavicula_Graduum_illustrated.pdf",
     "Claude and ChatGPT/Codex; illustrated plates Claude, with ChatGPT figure renders and proofs for IX-XI"),
    ("V", "Ars Notoria Stigmatum", "Three divinatory arts and five computed notae, in a developmental reading edition",
     "books/05_notoria/manuscript/out/Ars_Notoria_Stigmatum_reading.pdf",
     "Claude (brief, research, computed notae), ChatGPT/Codex (manuscript)"),
    bind.MATRES,
    bind.POTESTATE,
    ("VII", "De Vinculis", "Compulsion, judgment and service, in seven operations",
     "books/07_septimus/out/De_Vinculis_reading.pdf",
     "ChatGPT/Codex, from Claude's brief and research"),
    bind.CLAUSA,
]

_bibliography_pages = bind.bibliography_pages


def bibliography_pages(title, source):
    """Book V's source trail is its closing register"""
    if title == "Ars Notoria Stigmatum":
        with fitz.open(source) as document:
            lines = [" ".join(p.get_text().split()).casefold() for p in document]
        starts = [i for i, t in enumerate(lines) if "source trail" in t[:200]]
        if not starts:
            raise ValueError("Cannot locate Book V's source trail; update the selector before binding")
        return [i + 1 for i in range(starts[0], len(lines)) if lines[i]]
    return _bibliography_pages(title, source)


bind.bibliography_pages = bibliography_pages

NOTE = [
    "The opening pair is joined as Clavicula Matricis et Intervallorum, a new",
    "reading edition at the common trim. Its seventeen tables replace both",
    "earlier components, with a shared setting and a new workshop frontispiece.",
    "The earlier books remain as source editions. The later identifiers stay",
    "III, IV and V while the series develops. III and IV are illustrated.",
    "Every office and handoff spirit of Book III is drawn.",
    "None of the illustrated plates is a plot master. The plotter files remain",
    "separate. Book V is a developmental reading",
    "edition. Book VI is De Potestate et Accusatione.",
    "Source keys and inspection limits remain grouped by book at the end.",
]
_front_matter = bind.front_matter


def front_matter(present, bibliography=None):
    """bind.front_matter with this binding's note and title"""
    r = _front_matter(present, bibliography)
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(bind.PW, bind.PH), invariant=1, pageCompression=1)
    bind.paper(c)
    c.setFillColor(HexColor(bind.INK))
    c.setFont("FellSC", 12)
    c.drawCentredString(bind.PW / 2, 640, "Of the Binding")
    c.setFont("Fell", 10.5)
    y = 600
    for ln in NOTE:
        c.drawCentredString(bind.PW / 2, y, ln)
        y -= 16
    c.showPage()
    c.save()
    buf.seek(0)
    note = PdfReader(buf).pages[0]
    title = r.pages[0]
    from pypdf import PdfWriter
    w = PdfWriter()
    for i, p in enumerate(r.pages):
        w.add_page(note if i == 2 else p)
    w.add_metadata({"/Title": "Codex Intervallorum — Libri Septem (illustrated draft)"})
    out = io.BytesIO()
    w.write(out)
    out.seek(0)
    return PdfReader(out)


bind.front_matter = front_matter
_colophon = bind.colophon


def colophon():
    r = _colophon()
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(bind.PW, bind.PH), invariant=1)
    c.setFillColor(HexColor(bind.INK))
    c.setFont("FellIt", 9)
    c.drawString(72, 92, "Illustrated setting: Claude. Art and spot revision: ChatGPT/Codex, 17 October 2026.")
    c.drawString(72, 78, "Renders and prompts: references/raster; Foras from the Tarot. Nothing here is a plot master.")
    c.showPage()
    c.save()
    buf.seek(0)
    page = r.pages[0]
    page.merge_page(PdfReader(buf).pages[0])
    return r


bind.colophon = colophon


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', default=os.path.join(HERE, "out", "illustrated", "Codex_Intervallorum_illustrated.pdf"))
    parser.add_argument('--vellum-profile', choices=['light', 'full'], default='light')
    args = parser.parse_args()
    out = args.output
    bind.main(out)
    import platekit
    print("bytes", platekit.compact(out))
    import scribal
    scribal.apply(out)
    import vellum
    vellum.apply(out, profile=args.vellum_profile)


