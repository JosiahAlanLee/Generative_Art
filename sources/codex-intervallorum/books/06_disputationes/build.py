#!/usr/bin/env python3
"""De Potestate et Accusatione: reading edition of Book VI; no network at build time.

Third discussion draft. The setting follows the series: 7 x 10 in on the series ground, IM Fell
English for headings and labels, EB Garamond for the text, the five evidence tags hung in the
margin, the shared bibliography renderer at the end. The nine plates are the serif reading edition
built by plates/reading.py; each stands alone on a verso facing the opening of its section. The
title leaf carries the book's three letters, pot, in the inherited Matricis substitution hand.

    python books/06_disputationes/plates/reading.py      (the plates, first)
    python books/06_disputationes/build.py               -> books/06_disputationes/out/De_Potestate_et_Accusatione_reading.pdf
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import io
import json
from pathlib import Path
import random
import re
import sys

from pypdf import PdfReader, PdfWriter, Transformation
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
sys.path.insert(0, str(REPO / 'common/plot'))
import backmatter  # noqa: E402
import furniture as fu  # noqa: E402  (puts common/geometry on the path for the cipher)
import bookpage as bp  # noqa: E402

spec = importlib.util.spec_from_file_location('matricis_cipher', REPO / 'books/01_matricis/generator/cipher.py')
cipher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cipher)

MANUSCRIPT = ROOT / 'manuscript/de-potestate-et-accusatione.md'
REFERENCES = ROOT / 'manuscript/references.json'
PLATES = ROOT / 'plates/reading'
PDF = 'De_Potestate_et_Accusatione_reading.pdf'
PW, PH = 504, 720
PAPER = colors.HexColor('#ede6d4'); INK = colors.HexColor('#161918'); RED = colors.HexColor('#a32b24')
MUTE = colors.HexColor('#5a4331'); RULE = colors.HexColor('#8e7b5f')
FONT_FILES = [('VIBody', 'static/EBGaramond-Regular400.ttf'), ('VIItalic', 'static/EBGaramond-Italic400.ttf'),
              ('VITitle', 'IMFeENrm28P.ttf'), ('VITitleIt', 'IMFeENit28P.ttf'), ('VISmall', 'IMFeENsc28P.ttf')]
KEY = {
    'E': 'Empirical or textual evidence, with a source and an inspection limit.',
    'D': 'Definition, conditional deduction, or worked consequence within stated assumptions.',
    'H': 'Hypothesis, proposed instrument, or interpretive extension requiring tests.',
    'V': 'Adopted value; no scientific derivation claimed.',
    'F': 'Fiction, invented device, or an instruction belonging to the artwork.',
}
X0, X1, TAGX = 66.0, 452.0, 59.0          # text block; the tags hang right-aligned at TAGX
TOP, BOTTOM = 650.0, 58.0
NOTE_TITLE = 'VI / preparation'
NOTES = [
    'Third discussion draft, 18 October 2026. Developed by Claude Opus 5.5 at Josiah Alan-Lee’s request from the second draft that ChatGPT/Codex filed the same day, which is kept with its source ledger in the development repository. Claude restructured the text into the series’ tagged form, stated five claims (D15–D19, continuing the series’ numbering) with what would count against each, recomputed the gate-and-window ledgers from the committed results, and added the Wells Fargo figures, the Mitsubishi judgment, the Metz procedure from the project’s case study, and Elish. Claude also drew the plates and set the book.',
    'Read for this draft: the Mitsubishi judgment in English translation, paragraphs 28 and 30–31 of the Wells Fargo statement of facts, Elish’s article record and abstract, the AI Control abstract, Freeman’s principles in a reproduction, the gate-and-window results, the refusal specimen at its pinned commit, the case record and the project’s scapegoating research. Every other source carries the second draft’s inspection account, which names who read it. An agent that had not seen the drafting then checked the dated, counted and quoted statements against their sources; its corrections, to the account of the 1999 report, the dating of the hub counts, the summary of the dissent, one plate’s reading and several smaller phrasings, are in this text.',
    'The nine plates were drawn by procedural code written by Claude for this book, in the series’ plotter conventions: A4, stroke-only, two layers, two inks, a drawn reserved blank, the plate’s sentence in the twelve-mark hand, and its frame scale carrying in the biliteral cipher the sentence that would count against the plate’s claim. No image-generation model was used. Four carry no data; five are drawn from the records they name. The plot masters letter in the EMS Nixish stroke face; this edition in IM Fell English outlines. None has been tested on a physical plotter.',
    'Bound as Book VI in both bindings by Claude at the author’s request, in place of the Tarot of Intervals, which is kept as a separate volume: on 18 October 2026 in the development repository, and on 19 October in this edition. The title, the claim numbers and the tag [V] on unadopted proposals remain proposals for his review. In the volume, the register joins the one end bibliography under the VI prefix, set in the series’ citation form, and the bracketed keys link to its entries there.',
]


# ----------------------------------------------------------------- manuscript --

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def norm(s):
    s = re.sub(r'\*', '', s)
    return re.sub(r'[^a-z0-9]', '', s.lower())


def paragraphs(s):
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    return [' '.join(p.split()) for p in s.strip().split('\n\n') if p.strip()]


def parse(path=MANUSCRIPT):
    text = path.read_text(encoding='utf-8')
    title = re.match(r'# (.+)\n', text).group(1).strip()
    meta = dict(re.findall(r'^(\w+): (.+)$', re.search(r'<!-- book\n(.*?)-->', text, re.S).group(1), re.M))
    parts = re.split(r'^## (.+)\n', text, flags=re.M)
    book = dict(title=title, meta=meta, status=[], proem=[], claims=[], divisions=[])
    for i in range(1, len(parts), 2):
        head, body = parts[i].strip(), parts[i + 1]
        plate = re.search(r'<!-- plate: (\w+) -->', body)
        ps = paragraphs(body)
        if head == 'Status':
            book['status'] = ps
        elif head == 'Proem':
            book['proem'] = ps
        elif head == 'The five claims':
            claim = None
            for p in ps:
                m = re.match(r'### (D\d+) \[([EDHVF])\] (.+)', p)
                if m:
                    claim = dict(id=m.group(1), kind=m.group(2), name=m.group(3), parts=[])
                    book['claims'].append(claim)
                else:
                    lead = re.match(r'\*\*(.+?)\*\*\s*(.*)', p)
                    claim['parts'].append((lead.group(1), lead.group(2)))
        elif head.startswith('Part '):
            book['divisions'].append(dict(kind='part', head=head))
        else:
            blocks = []
            for p in ps:
                if p.startswith('### '):
                    blocks.append(('sub', p[4:]))
                elif p.startswith('> '):
                    blocks.append(('fiction', p[2:]))
                elif p.startswith('**Reading the plate.**'):
                    blocks.append(('reading', p[len('**Reading the plate.**'):].strip()))
                elif p.startswith('*') and p.endswith('*') and not blocks:
                    blocks.append(('deck', p[1:-1]))
                else:
                    m = re.match(r'\[([EDHVF])\]\s*(.*)', p)
                    if not m:
                        raise ValueError(f'untagged paragraph in {head}: {p[:60]}')
                    blocks.append(('para', m.group(1), m.group(2)))
            book['divisions'].append(dict(kind='section', head=head, plate=plate.group(1) if plate else None, blocks=blocks))
    return book


def source_blocks(book=None):
    """Every paragraph of running text the edition must carry, as written in the manuscript."""
    book = book or parse()
    out = list(book['status']) + [re.sub(r'^\[[EDHVF]\]\s*', '', p) for p in book['proem']]
    for c in book['claims']:
        out += [t for _, t in c['parts']]
    for d in book['divisions']:
        if d['kind'] == 'section':
            for b in d['blocks']:
                out.append(b[-1])
    return out


def references():
    return json.loads(REFERENCES.read_text(encoding='utf-8'))


def plates_meta():
    return {p['plate']: p for p in json.loads((PLATES / 'reading-edition.json').read_text())['plates']}


# -------------------------------------------------------------------- setting --

def fonts():
    fd = REPO / 'common/fonts'
    for name, file in FONT_FILES:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fd / file)))
    bp.fonts()


KEYS = re.compile(r'\[((?:[A-Z]\d+)(?:, [A-Z]\d+)*)\]')


def markup(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*(.+?)\*', r'<font name="VIItalic">\1</font>', s)

    def link(m):
        keys = [k.strip() for k in m.group(1).split(',')]
        return '[' + ', '.join(f'<a href="#ref-{k}" color="#5a4331">{k}</a>' for k in keys) + ']'
    return KEYS.sub(link, s)


class Book:
    def __init__(self, path, book):
        self.path = Path(path); self.book = book; self.pages = []; self.plates = {}; self.active = False
        self.y = 0; self.running = ''
        self.c = Canvas(str(path), pagesize=(PW, PH), invariant=1, pageCompression=1)
        self.c.setTitle(book['title']); self.c.setAuthor(book['meta']['author'])
        self.c.setSubject(book['meta']['subtitle'])
        self.styles = {
            'body': ParagraphStyle('body', fontName='VIBody', fontSize=11.4, leading=15.3, spaceAfter=7.2, textColor=INK),
            'reading': ParagraphStyle('reading', fontName='VIBody', fontSize=10.4, leading=14.0, spaceAfter=6, textColor=INK),
            'deck': ParagraphStyle('deck', fontName='VIItalic', fontSize=12.6, leading=16.4, spaceAfter=4, textColor=INK),
            'fiction': ParagraphStyle('fiction', fontName='VIItalic', fontSize=10.8, leading=14.6, spaceAfter=10, textColor=MUTE),
            'status': ParagraphStyle('status', fontName='VIItalic', fontSize=10.6, leading=14.4, spaceAfter=7, textColor=INK),
            'claim': ParagraphStyle('claim', fontName='VIBody', fontSize=11.0, leading=14.6, spaceAfter=4, textColor=INK),
            'measure': ParagraphStyle('measure', fontName='VIBody', fontSize=10.2, leading=13.6, spaceAfter=3, textColor=INK),
            'key': ParagraphStyle('key', fontName='VIBody', fontSize=10.8, leading=14.2, spaceAfter=4, textColor=INK),
        }

    @property
    def page(self):
        return self.c.getPageNumber()

    # ------------------------------------------------------------ pages --
    def start(self, running, kind='body', key=None, title=None, level=0, head=True):
        if self.active:
            raise ValueError('page already open')
        self.active = True; self.running = running; self.y = TOP; c = self.c
        c.setFillColor(PAPER); c.rect(0, 0, PW, PH, fill=1, stroke=0)
        if head:
            c.setStrokeColor(RULE); c.setLineWidth(.45); c.line(40, 679, 464, 679)
            c.setFont('VISmall', 8); c.setFillColor(INK); c.drawString(42, 690, self.book['title'].upper())
            c.setFillColor(RED); c.drawRightString(462, 690, running.upper())
            c.setFont('VISmall', 9); c.setFillColor(MUTE); c.drawCentredString(252, 24, str(self.page))
        self.pages.append(dict(page=self.page, title=running, kind=kind))
        if key:
            c.bookmarkPage(key); c.addOutlineEntry(title or running, key, level=level)

    def end(self):
        if not self.active:
            raise ValueError('no page open')
        self.c.showPage(); self.active = False

    def blank(self):
        self.start('Interval', 'blank', head=False); self.end()

    def to_parity(self, odd):
        """make the next page a recto (odd) or a verso (even)"""
        if self.active:
            self.end()
        if (self.page % 2 == 1) != odd:
            self.blank()

    def room(self, need):
        if self.y - need < BOTTOM:
            self.end(); self.start(self.running)

    # ------------------------------------------------------------ text --
    def flow(self, text, style, x=X0, width=None, tag=None, link=True, prepared=False):
        width = width or X1 - x
        st = self.styles[style]
        todo = Paragraph(text if prepared else (markup(text) if link else html.escape(text)), st)
        first = True
        while True:
            _, h = todo.wrap(width, 10000)
            if self.y - h >= BOTTOM:
                if tag and first:
                    self.tag(tag, self.y - st.fontSize)      # drawn first, so it reads before its paragraph
                todo.drawOn(self.c, x, self.y - h)
                self.y -= h + st.spaceAfter
                return
            if self.y - BOTTOM < 2.2 * st.leading:
                self.end(); self.start(self.running); continue
            chunks = todo.split(width, self.y - BOTTOM)
            if len(chunks) != 2:
                self.end(); self.start(self.running); continue
            _, h0 = chunks[0].wrap(width, 10000)
            if tag and first:
                self.tag(tag, self.y - st.fontSize)
            chunks[0].drawOn(self.c, x, self.y - h0)
            first = False
            self.end(); self.start(self.running); todo = chunks[1]

    def tag(self, t, baseline):
        self.c.setFont('VISmall', 8.2); self.c.setFillColor(RED)
        self.c.drawRightString(TAGX, baseline + 0.6, f'[{t}]')

    def small(self, text, color=INK, size=9.4, gap=15.0, x=X0):
        self.room(gap + 40)
        self.c.setFont('VISmall', size); self.c.setFillColor(color)
        self.c.drawString(x, self.y - size, text.upper())
        self.y -= gap

    def rule(self, seed, red=False):
        band = bp.flow_rule(self.c, X0, self.y - 2, (X1 - X0) / bp.MM, seed, n=3, red_dot=red)
        self.y -= band * bp.MM + 6

    # ------------------------------------------------------------ leaves --
    def titlepage(self):
        m = self.book['meta']
        self.start('Title', 'title', key='title', title=self.book['title'], head=False); c = self.c
        c.setFillColor(RED); c.setFont('VISmall', 10.5)
        c.drawCentredString(PW / 2, 548, 'BOOK VI')
        c.setFillColor(INK); c.setFont('VITitle', 33)
        c.drawCentredString(PW / 2, 506, 'De Potestate')
        c.drawCentredString(PW / 2, 468, 'et Accusatione')
        c.setFont('VIItalic', 14.5); c.drawCentredString(PW / 2, 430, m['subtitle'])
        p = Paragraph(html.escape(m['strap']), ParagraphStyle('strap', fontName='VIBody', fontSize=11, leading=15,
                                                             alignment=1, textColor=INK))
        _, h = p.wrap(300, 200); p.drawOn(c, PW / 2 - 150, 404 - h)
        # the book's three letters in the inherited hand, without rails: a mark, not an inscription
        hand = fu.Hand(c, random.Random(2026), amp=.03); size = 37
        width = cipher.measure(m['mark'], size) - cipher.TRACK * size; base = 290
        c.saveState(); c.translate(0, base * 2); c.scale(1, -1)
        cipher.write(hand, m['mark'], PW / 2 - width / 2, base, size, weight='orn', color='ink', rail=False, jit=False)
        c.restoreState()
        c.setFillColor(INK); c.setFont('VIBody', 11); c.drawCentredString(PW / 2, 170, m['author'])
        c.setFillColor(RED); c.setFont('VISmall', 9); c.drawCentredString(PW / 2, 70, m['edition'].upper())
        self.end()

    def keypage(self):
        self.start('The evidence key', key='key', title='The evidence key')
        self.heading('The evidence key', size=19)
        for k, v in KEY.items():
            self.flow(v, 'key', link=False, tag=k)
        self.y -= 14
        for p in self.book['status']:
            self.flow(p, 'status')
        self.end()

    def heading(self, text, size=22, gap=12):
        p = Paragraph(html.escape(text), ParagraphStyle('h', fontName='VITitle', fontSize=size, leading=size * 1.14, textColor=INK))
        _, h = p.wrap(X1 - X0, 400)
        self.room(h + 80)
        p.drawOn(self.c, X0, self.y - h); self.y -= h + gap

    def proem(self):
        self.start('Proem', key='proem', title='Proem')
        self.heading('Proem', 23)
        self.rule('proem')
        for p in self.book['proem']:
            m = re.match(r'\[([EDHVF])\]\s*(.*)', p)
            self.flow(m.group(2), 'body', tag=m.group(1))
        self.end()

    def claims(self):
        self.start('The five claims', key='claims', title='The five claims')
        self.heading('The five claims', 21)
        for cl in self.book['claims']:
            self.room(118)
            self.small(f"{cl['id']}  [{cl['kind']}]  ·  {cl['name']}", RED, 9.6, 15.5)
            for lead, text in cl['parts']:
                if lead == 'Claim.':
                    self.flow(text, 'claim')
                else:
                    self.flow(f'<font name="VIItalic">{html.escape(lead)}</font> ' + markup(text), 'measure', x=X0 + 14, prepared=True)
            self.y -= 9
        self.end()

    def part(self, head):
        self.to_parity(odd=True)
        num, name = re.match(r'Part (\w+): (.+)', head).groups()
        self.start(name, 'part', key='part-' + num, title=f'Part {num}: {name}', head=False); c = self.c
        c.setFillColor(INK); c.setFont('VISmall', 11.5); c.drawCentredString(PW / 2, 440, f'PART {num}')
        c.setFont('VITitle', 27); c.drawCentredString(PW / 2, 406, name)
        bp.flow_rule(c, PW / 2 - 34 * bp.MM, 386, 68, 'part-' + num, n=2)
        c.setFont('VISmall', 9); c.setFillColor(MUTE); c.drawCentredString(252, 24, str(self.page))
        self.end()

    def plate(self, numeral, meta):
        """A plate always stands alone on a verso, facing the opening of its section."""
        self.to_parity(odd=False)
        key = 'tabula-' + numeral.lower()
        self.start('Tabula ' + numeral, 'plate', key=key, title=f"Tabula {numeral}: {meta['title']}", level=1, head=False)
        c = self.c
        c.setFont('VISmall', 7.8); c.setFillColor(MUTE)
        c.drawCentredString(PW / 2, 24, f'TABULA {numeral}  ·  {self.page}')
        self.plates[self.page] = dict(numeral=numeral, stem=meta['stem'], pdf=str(PLATES / meta['pdf']))
        self.end()

    def section(self, d, numeral_of_plate=None):
        num, name = re.match(r'([IVXL]+)\. (.+)', d['head']).groups()
        if d['plate']:
            self.plate(numeral_of_plate, self.platemeta[numeral_of_plate])
        elif self.active:
            self.end()
        self.start(name, key='section-' + num, title=f'{num}. {name}')
        c = self.c
        c.setFont('VISmall', 11); c.setFillColor(RED); c.drawString(X0, self.y - 11, num)
        if d['plate']:
            c.setFillColor(MUTE); c.setFont('VISmall', 8.6)
            c.drawRightString(X1, self.y - 11, f'FACING  ·  TABULA {numeral_of_plate}')
        self.y -= 26
        self.heading(name, 22, gap=8)
        for b in d['blocks']:
            kind = b[0]
            if kind == 'deck':
                self.flow(b[1], 'deck')
                self.rule(num, red=bool(d['plate']))
            elif kind == 'fiction':
                self.flow(b[1], 'fiction')
            elif kind == 'sub':
                self.room(70)
                self.y -= 3
                self.small(b[1], INK, 9.4, 14.5)
            elif kind == 'para':
                self.flow(b[2], 'body', tag=b[1])
            elif kind == 'reading':
                self.room(80)
                self.y -= 6
                self.small(f'Reading Tabula {numeral_of_plate}', RED, 9.0, 14.0)
                self.flow(b[1], 'reading')

    def register(self):
        if self.active:
            self.end()
        records = [dict(citation=r['citation'], keys=list(r['keys']), accounts=[dict(a) for a in r['accounts']],
                        urls=list(r.get('urls', []))) for r in references()]
        notes = [dict(title=NOTE_TITLE, paragraphs=list(NOTES))]
        start = self.page
        self.c.bookmarkPage('register'); self.c.addOutlineEntry('Register', 'register', level=0)
        apparatus = backmatter.write(self.c, records, notes, start, REPO, local_book='VI')
        self.pages += apparatus['pages']; self.bibliography_start = start
        return apparatus

    def save(self):
        if self.active:
            self.end()
        self.c.save()


def build(out):
    fonts(); out = Path(out); out.mkdir(parents=True, exist_ok=True)
    book = parse()
    platemeta = plates_meta()
    tmp = out / ('_text_' + PDF)
    b = Book(tmp, book); b.platemeta = platemeta
    b.titlepage()
    b.keypage()
    b.proem()
    b.claims()
    order = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']
    k = 0
    for d in book['divisions']:
        if d['kind'] == 'part':
            b.part(d['head'])
        else:
            numeral = None
            if d['plate']:
                numeral = order[k]; k += 1
                if numeral.lower() != d['plate']:
                    raise ValueError(f"plate order: {d['head']} expects {d['plate']}, got {numeral}")
            b.section(d, numeral)
    apparatus = b.register(); b.save()
    final = out / PDF
    merge_with_outline(tmp, b.plates, final)
    tmp.unlink()
    import fitz
    with fitz.open(final) as doc:
        pages = len(doc)
    inputs = [ROOT / 'build.py', MANUSCRIPT, REFERENCES, PLATES / 'reading-edition.json',
              *[PLATES / p['pdf'] for p in platemeta.values()],
              REPO / 'books/01_matricis/generator/cipher.py', REPO / 'common/geometry/core.py',
              REPO / 'common/illum/furniture.py', REPO / 'common/plot/bookpage.py', REPO / 'binding/backmatter.py',
              *[REPO / 'common/fonts' / f for _, f in FONT_FILES]]
    manifest = dict(schema_version=1, pdf=PDF, pages=pages, sha256=sha(final), page_map=b.pages,
                    plates=[dict(page=p, **v) for p, v in sorted(b.plates.items())],
                    bibliography_start=b.bibliography_start, reference_keys=apparatus['keys'],
                    source_paragraphs=len(source_blocks(book)),
                    input_sha256={str(p.relative_to(REPO)): sha(p) for p in inputs if p.is_file()})
    for p in manifest['plates']:
        p['pdf'] = str(Path(p['pdf']).relative_to(REPO))
    (out / 'build-manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(pdf=PDF, pages=pages, bibliography_start=b.bibliography_start,
                          plates={v['numeral']: p for p, v in sorted(b.plates.items())})))
    return manifest


def merge_with_outline(text_pdf, plates, out_pdf):
    """Merge each plate onto its leaf; pypdf's writer keeps the canvas's outline when cloned."""
    w = PdfWriter(clone_from=str(text_pdf))
    for i, page in enumerate(w.pages, start=1):
        if i in plates:
            pl = PdfReader(plates[i]['pdf']).pages[0]
            pw, ph = float(pl.mediabox.width), float(pl.mediabox.height)
            s = min((PW - 0.42 * 72) / pw, (PH - 0.78 * 72) / ph)
            tx, ty = (PW - pw * s) / 2, (PH - ph * s) / 2 + 9
            page.merge_transformed_page(pl, Transformation().scale(s, s).translate(tx, ty))
            page.compress_content_streams()
            plates[i]['scale'] = round(s, 4)
    w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    w.add_metadata({'/Title': 'De Potestate et Accusatione', '/Author': 'Josiah Alan-Lee',
                    '/Subject': 'Book VI, third discussion draft'})
    with open(out_pdf, 'wb') as f:
        w.write(f)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, default=ROOT / 'out')
    build(ap.parse_args().out)
