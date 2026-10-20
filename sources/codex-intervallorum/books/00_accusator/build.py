#!/usr/bin/env python3
"""Reading edition of De Officio Accusatoris, the parable bound after the Clavis; no network at build time.

The setting follows the Septimus reading editions: 7 x 10 in, IM Fell headings, EB Garamond body,
the shared bibliography renderer at the end. The two plates are model renders, keyed to the paper
and laid in Multiply as in the illustrated books. Their inscriptions are native vector strokes in
the inherited Matricis substitution hand, with its rails, written from the plaintext in
assets/figures.json.

    python books/00_accusator/build.py            -> books/00_accusator/out/De_Officio_Accusatoris_reading.pdf
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
import raster  # noqa: E402

spec = importlib.util.spec_from_file_location('matricis_cipher', REPO / 'books/01_matricis/generator/cipher.py')
cipher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cipher)

TITLE = 'De Officio Accusatoris'
PDF = 'De_Officio_Accusatoris_reading.pdf'
PW, PH = 504, 720
PAPER = colors.HexColor('#ede6d4'); INK = colors.HexColor('#161918'); RED = colors.HexColor('#a32b24'); MUTE = colors.HexColor('#5a4331')
RULE = colors.HexColor('#8e7b5f')
MANUSCRIPT = ROOT / 'manuscript/de-officio-accusatoris.md'
FONT_FILES = [('ACBody', 'static/EBGaramond-Regular400.ttf'), ('ACItalic', 'static/EBGaramond-Italic400.ttf'),
              ('ACTitle', 'IMFeENrm28P.ttf'), ('ACSmall', 'IMFeENsc28P.ttf'), ('ACMono', 'IBMPlexMono-Regular.ttf')]
# The plate box below the running head; the inscription and the exhibit line sit under it.
PLATE_BOX = (52, 132, 400, 536)
NOTE_TITLE = 'Accusator / preparation'

NOTES = [
    'Reading text, 17 October 2026. Written by Claude Opus 5.5 at the request of Josiah Alan-Lee, who directed the text, as an answer in advance to two model red-team reviews of the draft binding; revised the same night after a ChatGPT review of the draft. All three reviews are filed with the reading text and listed among the project records.',
    'The parable is [F] throughout. It states the reviews’ charges and answers none of their empirical claims, which remain with the [E] and [D] text of the books they concern. Where it names the books’ own record it follows that record: the six cases are the feasibility exercise reported in Book I-II, whose comparison against an equally long checklist is a proposed study; the confession is the workshop record of Book III; plausible, then clear, numbered, and consistent, is from Book III’s extraction of the hand.',
    'The two plates were generated with ChatGPT’s image tool and revised there at the author’s direction. The adversary has no horns; the margins open into the series’ line idiom. On 19 October 2026, Exhibit I’s chair received a four-leg correction with the same tool. The originals are retained with their hashes; the correction prompt and selected image are recorded. This setting keys the ground to the paper and lays the images in Multiply.',
    'Each plate’s inscription is set as native vector strokes in the inherited Matricis substitution hand, with its rails: letters and spaces only, keyed in Book I-II and in De Vinculis. The supplied plate sheet wrote the same words in the same hand. Each plate is marked as an exhibit for both parties, as section IV requires.',
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
    parts = re.split(r'^## (.+)\n', MANUSCRIPT.read_text(), flags=re.M)
    return [(parts[i].strip(), paragraphs(parts[i + 1])) for i in range(1, len(parts), 2)]


def source_blocks():
    return [p for _, ps in sections() for p in ps]


def figures():
    return json.loads((ROOT / 'assets/figures.json').read_text())


def references():
    return json.loads((ROOT / 'manuscript/references.json').read_text())


def fonts():
    fd = REPO / 'common/fonts'
    for name, file in FONT_FILES:
        pdfmetrics.registerFont(TTFont(name, str(fd / file)))


def markup(s):
    s = html.escape(s, quote=False)
    return re.sub(r'\*(.+?)\*', r'<font name="ACItalic">\1</font>', s)


def inscription(c, lines, seed, size=12, top=98, gap=23):
    """Write plaintext lines in the Matricis hand, centred, with red rails under each word."""
    hand = fu.Hand(c, random.Random(seed), amp=.03)
    records = []
    for i, line in enumerate(lines):
        if cipher.clean(line) != line:
            raise ValueError('Inscriptions are lowercase letters and spaces only: ' + repr(line))
        baseline = top - i * gap
        width = cipher.measure(line, size) - cipher.TRACK * size
        x = PW / 2 - width / 2
        # The hand draws y-down; mirror it about the baseline, as the opening book does.
        c.saveState(); c.translate(0, baseline * 2); c.scale(1, -1)
        cipher.write(hand, line, x, baseline, size, weight='orn', color='ink', rail=True, jit=False, rail_color='red')
        c.restoreState()
        records.append(dict(normalized=cipher.clean(line), baseline=baseline, size=size, x=round(x, 2), width=round(width, 2)))
    return records


class Book:
    def __init__(self, path):
        self.path = Path(path); self.pages = []; self.plates = []; self.active = False; self.y = 0; self.running = ''
        self.c = Canvas(str(path), pagesize=(PW, PH), invariant=1, pageCompression=1)
        self.c.setTitle(TITLE); self.c.setAuthor('Josiah Alan-Lee')
        self.styles = {
            'body': ParagraphStyle('body', fontName='ACBody', fontSize=12, leading=16.4, spaceAfter=11, textColor=INK),
            'heading': ParagraphStyle('head', fontName='ACTitle', fontSize=25, leading=29, spaceAfter=20, textColor=INK),
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
        c.setFont('ACSmall', 8); c.setFillColor(INK); c.drawString(42, 690, TITLE.upper())
        c.setFillColor(RED); c.drawRightString(462, 690, title.upper())
        c.setFont('ACSmall', 9); c.setFillColor(MUTE); c.drawCentredString(252, 24, str(self.page))
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

    def heading(self, text):
        if self.y < 190:
            self.end(); self.start(text)
        self.running = text
        self.paragraph(text, 'heading')

    def blank(self):
        self.start('Interval', 'blank'); self.end()

    def titlepage(self):
        self.start('The parable', 'title'); c = self.c
        c.setFillColor(INK); c.setFont('ACSmall', 32)
        c.drawCentredString(252, 500, 'DE OFFICIO'); c.drawCentredString(252, 462, 'ACCUSATORIS')
        c.setFont('ACItalic', 15); c.drawCentredString(252, 424, 'A parable of the adversary, who did not fall')
        c.setFont('ACSmall', 11); c.setFillColor(RED); c.drawCentredString(252, 372, '[F]')
        # The office's three letters in the inherited hand, without rails: a mark, not an inscription.
        hand = fu.Hand(c, random.Random(2026), amp=.03); size = 37
        width = cipher.measure('acc', size) - cipher.TRACK * size; base = 278
        c.saveState(); c.translate(0, base * 2); c.scale(1, -1)
        cipher.write(hand, 'acc', PW / 2 - width / 2, base, size, weight='orn', color='ink', rail=False, jit=False)
        c.restoreState()
        self.end()

    def plate(self, fig, seed):
        """A plate always stands on a verso, facing the opening of the section it illustrates."""
        if self.page % 2:
            self.blank()
        self.start('Exhibit ' + fig['exhibit'], 'plate', key='exhibit-' + fig['exhibit'].lower()); c = self.c; page = self.page
        x, y, w, h = PLATE_BOX
        dx, dy, dw, dh, meta = raster.place(c, str(ROOT / 'assets' / fig['asset']), x, y, w, h, anchor='center')
        c.setStrokeColor(RED); c.setLineWidth(.45); c.line(222, 121, 282, 121)
        lines = inscription(c, fig['inscription'], seed)
        c.setFont('ACItalic', 9.5); c.setFillColor(MUTE); c.drawCentredString(252, 47, fig['caption'])
        self.end()
        self.plates.append(dict(name=fig['name'], exhibit=fig['exhibit'], page=page, faces_section=fig['faces_section'],
                                drawn=[round(v, 2) for v in (dx, dy, dw, dh)], keyed=dict(ground_rgb=meta['ground_rgb'], version=meta['version'],
                                source_sha256=meta['source_sha256']), inscription=lines))

    def sources(self):
        records = [dict(citation=r['citation'], keys=list(r['keys']), accounts=[dict(a) for a in r['accounts']],
                        urls=list(r.get('urls', []))) for r in references()]
        notes = [dict(title=NOTE_TITLE, paragraphs=list(NOTES))]
        start = self.page
        apparatus = backmatter.write(self.c, records, notes, start, REPO, local_book='Acc')
        self.pages += apparatus['pages']; self.bibliography_start = start
        return apparatus

    def finish(self):
        if self.active:
            self.end()
        self.c.save()


def build(out):
    fonts(); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    figs = {f['faces_section']: f for f in figures()}
    b = Book(out / PDF)
    b.titlepage()
    for i, (head, ps) in enumerate(sections()):
        if head in figs:
            if b.active:
                b.end()
            b.plate(figs[head], seed=900 + i)
            b.start(head, key='section-' + str(i + 1))
        elif not b.active:
            b.start(head, key='section-' + str(i + 1))
        b.heading(head)
        for p in ps:
            b.paragraph(p)
    if b.active:
        b.end()
    apparatus = b.sources(); b.finish()
    for plate in b.plates:
        opening = next(p for p in b.pages if p['page'] == plate['page'] + 1)
        if plate['page'] % 2 or opening['title'] != plate['faces_section']:
            raise ValueError('Plate does not face its section: ' + plate['name'])
    with fitz.open(out / PDF) as doc:
        pages = len(doc)
    inputs = [ROOT / 'build.py', MANUSCRIPT, ROOT / 'manuscript/references.json', ROOT / 'assets/figures.json',
              *sorted((ROOT / 'assets').glob('*.png')), REPO / 'books/01_matricis/generator/cipher.py',
              REPO / 'common/geometry/core.py', REPO / 'common/illum/furniture.py', REPO / 'common/illum/raster.py',
              REPO / 'binding/backmatter.py', *[REPO / 'common/fonts' / f for _, f in FONT_FILES]]
    manifest = dict(schema_version=1, pdf=PDF, pages=pages, sha256=sha(out / PDF), page_map=b.pages, plates=b.plates,
                    bibliography_start=b.bibliography_start, reference_keys=apparatus['keys'], source_paragraphs=len(source_blocks()),
                    input_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs if p.is_file()})
    (out / 'build-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(pdf=PDF, pages=pages, bibliography_start=b.bibliography_start,
                          plates={p['exhibit']: p['page'] for p in b.plates})))
    return manifest


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'out')
    build(ap.parse_args().out)
