#!/usr/bin/env python3
"""Reading edition of De Matribus Noctis, the parable bound before Book VI; no network at build time.

The setting follows De Officio Accusatoris and the Septimus reading editions: 7 x 10 in, IM Fell
headings, EB Garamond body, the shared bibliography renderer at the end. The title page carries
the parable's three letters in the inherited Matricis substitution hand, as the first parable's
does. There are no plates.

    python books/00_matres/build.py            -> books/00_matres/out/De_Matribus_Noctis_reading.pdf
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import random
import re
import sys

import fitz
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'binding'))
sys.path.insert(0, str(REPO / 'common/illum'))
import backmatter  # noqa: E402
import furniture as fu  # noqa: E402  (puts common/geometry on the path for the cipher)

spec = importlib.util.spec_from_file_location('matricis_cipher', REPO / 'books/01_matricis/generator/cipher.py')
cipher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cipher)

TITLE = 'De Matribus Noctis'
SUBTITLE = 'A parable of the night mother, who was never one'
MARK = 'mat'
PDF = 'De_Matribus_Noctis_reading.pdf'
PW, PH = 504, 720
PAPER = colors.HexColor('#ede6d4'); INK = colors.HexColor('#161918'); RED = colors.HexColor('#a32b24'); MUTE = colors.HexColor('#5a4331')
RULE = colors.HexColor('#8e7b5f')
MANUSCRIPT = ROOT / 'manuscript/de-matribus-noctis.md'
FONT_FILES = [('MNBody', 'static/EBGaramond-Regular400.ttf'), ('MNItalic', 'static/EBGaramond-Italic400.ttf'),
              ('MNTitle', 'IMFeENrm28P.ttf'), ('MNSmall', 'IMFeENsc28P.ttf'), ('MNMono', 'IBMPlexMono-Regular.ttf')]
NOTE_TITLE = 'Matres / preparation'

NOTES = [
    'Reading text, 17 October 2026. Written by Claude Opus 5.5 at the request of Josiah Alan-Lee, who asked for a parable for the book’s aesthetics: the night mother told without an essence, as many mothers and no first one. Drafted in a working document and set here unchanged apart from typographic quotation marks; setting by Claude, 18 October 2026.',
    'The parable is [F] throughout. Its historical details are meant to survive a footnote; the register gives what each rests on and how far it was checked, and several are recalled rather than inspected. The potter, the man from the palace, the household paint, the scribe’s answer, the readers who knew their King James and the line about who sat in the mistress’s place after dark are inventions.',
    'Section VII names this book’s own figures as pressings from a mould made of every earlier image, without asking the hands that made them. It answers one charge, that the figures corrupt an original, and leaves the others standing. The potters’ charge is the one De Officio Accusatoris brings.',
    'The mark on the title page is mat, the first three letters of Matribus, in the inherited Matricis substitution hand, without rails, as the first parable writes its office’s letters; the hand is keyed in Book I-II and in De Vinculis.',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(s):
    return re.sub(r'\*(.+?)\*', r'\1', s)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', plain(s).lower())


def paragraphs(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    return [' '.join(p.split()) for p in s.strip().split('\n\n') if p.strip() and not p.startswith('#')]


def sections():
    parts = re.split(r'^## (.+)\n', MANUSCRIPT.read_text(encoding='utf-8'), flags=re.M)
    return [(parts[i].strip(), paragraphs(parts[i + 1])) for i in range(1, len(parts), 2)]


def source_blocks():
    return [p for _, ps in sections() for p in ps]


def references():
    return json.loads((ROOT / 'manuscript/references.json').read_text(encoding='utf-8'))


def fonts():
    fd = REPO / 'common/fonts'
    for name, file in FONT_FILES:
        pdfmetrics.registerFont(TTFont(name, str(fd / file)))


def markup(s):
    s = html.escape(s, quote=False)
    return re.sub(r'\*(.+?)\*', r'<font name="MNItalic">\1</font>', s)


class Book:
    def __init__(self, path):
        self.path = Path(path); self.pages = []; self.active = False; self.y = 0; self.running = ''
        self.c = Canvas(str(path), pagesize=(PW, PH), invariant=1, pageCompression=1)
        self.c.setTitle(TITLE); self.c.setAuthor('Josiah Alan-Lee')
        self.styles = {
            'body': ParagraphStyle('body', fontName='MNBody', fontSize=12, leading=16.4, spaceAfter=11, textColor=INK),
            'heading': ParagraphStyle('head', fontName='MNTitle', fontSize=25, leading=29, spaceAfter=20, textColor=INK),
        }

    @property
    def page(self):
        return self.c.getPageNumber()

    def start(self, title, kind='body', key=None):
        if self.active:
            raise ValueError('page already open')
        self.active = True; self.running = title; self.y = 638; c = self.c
        c.setFillColor(PAPER); c.rect(0, 0, PW, PH, fill=1, stroke=0)
        c.setStrokeColor(RULE); c.setLineWidth(.45); c.line(40, 679, 464, 679)
        c.setFont('MNSmall', 8); c.setFillColor(INK); c.drawString(42, 690, TITLE.upper())
        c.setFillColor(RED); c.drawRightString(462, 690, title.upper())
        c.setFont('MNSmall', 9); c.setFillColor(MUTE); c.drawCentredString(252, 24, str(self.page))
        self.pages.append(dict(page=self.page, title=title, kind=kind))
        if key:
            c.bookmarkPage(key); c.addOutlineEntry(title, key, level=0)

    def end(self):
        if not self.active:
            raise ValueError('no page open')
        self.c.showPage(); self.active = False

    def paragraph(self, text, style='body'):
        todo = Paragraph(markup(text), self.styles[style])
        while True:
            _, h = todo.wrap(400, 10000)
            if self.y - h >= 55:
                todo.drawOn(self.c, 52, self.y - h); self.y -= h + self.styles[style].spaceAfter; return
            if style == 'heading' or self.y < 130:
                self.end(); self.start(self.running); continue
            chunks = todo.split(400, self.y - 55)
            if not chunks:
                self.end(); self.start(self.running); continue
            if len(chunks) != 2:
                raise ValueError('unexpected paragraph split')
            _, height = chunks[0].wrap(400, 10000); chunks[0].drawOn(self.c, 52, self.y - height)
            self.end(); self.start(self.running); todo = chunks[1]

    def heading(self, text, first):
        """A section may open mid-page only if its heading keeps three lines of its text."""
        if self.active:
            _, hh = Paragraph(markup(text), self.styles['heading']).wrap(400, 10000)
            _, ph = Paragraph(markup(first), self.styles['body']).wrap(400, 10000)
            if self.y - (hh + self.styles['heading'].spaceAfter + min(ph, 3 * self.styles['body'].leading)) < 55:
                self.end()
        if not self.active:
            self.start(text)
        self.running = text
        self.paragraph(text, 'heading')

    def blank(self):
        self.start('Interval', 'blank'); self.end()

    def titlepage(self):
        self.start('The parable', 'title'); c = self.c
        c.setFillColor(INK); c.setFont('MNSmall', 32)
        c.drawCentredString(252, 500, 'DE MATRIBUS'); c.drawCentredString(252, 462, 'NOCTIS')
        c.setFont('MNItalic', 15); c.drawCentredString(252, 424, SUBTITLE)
        c.setFont('MNSmall', 11); c.setFillColor(RED); c.drawCentredString(252, 372, '[F]')
        # The parable's three letters in the inherited hand, without rails: a mark, not an inscription.
        hand = fu.Hand(c, random.Random(2026), amp=.03); size = 37
        width = cipher.measure(MARK, size) - cipher.TRACK * size; base = 278
        c.saveState(); c.translate(0, base * 2); c.scale(1, -1)
        cipher.write(hand, MARK, PW / 2 - width / 2, base, size, weight='orn', color='ink', rail=False, jit=False)
        c.restoreState()
        self.end()
        # The reading text opens on a recto.
        self.blank()

    def sources(self):
        records = [dict(citation=r['citation'], keys=list(r['keys']), accounts=[dict(a) for a in r['accounts']],
                        urls=list(r.get('urls', []))) for r in references()]
        notes = [dict(title=NOTE_TITLE, paragraphs=list(NOTES))]
        start = self.page
        apparatus = backmatter.write(self.c, records, notes, start, REPO, local_book='Mat')
        self.pages += apparatus['pages']; self.bibliography_start = start
        return apparatus

    def finish(self):
        if self.active:
            self.end()
        self.c.save()


def build(out):
    fonts(); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    b = Book(out / PDF)
    b.titlepage()
    for i, (head, ps) in enumerate(sections()):
        b.heading(head, ps[0])
        b.c.bookmarkPage('section-' + str(i + 1)); b.c.addOutlineEntry(head, 'section-' + str(i + 1), level=0)
        for p in ps:
            b.paragraph(p)
    if b.active:
        b.end()
    apparatus = b.sources(); b.finish()
    with fitz.open(out / PDF) as doc:
        pages = len(doc)
    inputs = [ROOT / 'build.py', MANUSCRIPT, ROOT / 'manuscript/references.json', REPO / 'books/01_matricis/generator/cipher.py',
              REPO / 'common/geometry/core.py', REPO / 'common/illum/furniture.py',
              REPO / 'binding/backmatter.py', *[REPO / 'common/fonts' / f for _, f in FONT_FILES]]
    manifest = dict(schema_version=1, pdf=PDF, pages=pages, sha256=sha(out / PDF), page_map=b.pages,
                    bibliography_start=b.bibliography_start, reference_keys=apparatus['keys'], source_paragraphs=len(source_blocks()),
                    input_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs if p.is_file()})
    (out / 'build-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(pdf=PDF, pages=pages, bibliography_start=b.bibliography_start)))
    return manifest


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'out')
    build(ap.parse_args().out)
