#!/usr/bin/env python3
"""Reading edition of the Nota Clausa: Tabula, Regula and seven plates at 7 x 10 in.

Builds only from public files in this folder: TABULA.md, REGULA.md and plates/*.svg.
The plates are sealed artifacts. Nothing here can regenerate or read them without the key.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re

from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle, Preformatted
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PW, PH = 504, 720
PAPER = colors.HexColor('#ede6d4'); INK = colors.HexColor('#161918'); RED = colors.HexColor('#a32b24'); MUTE = colors.HexColor('#5a4331')
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']


def fonts():
    fd = REPO / 'common/fonts'
    for name, file in [('NCBody', 'static/EBGaramond-Regular400.ttf'), ('NCItalic', 'static/EBGaramond-Italic400.ttf'),
                       ('NCTitle', 'IMFeENrm28P.ttf'), ('NCSmall', 'IMFeENsc28P.ttf'), ('NCMono', 'IBMPlexMono-Regular.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fd / file)))


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<font name="NCMono" size="8.6">\1</font>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<font name="NCSmall" color="#a32b24">\1</font>', s)
    s = re.sub(r'(?<![\w*])\*([^*]+?)\*(?![\w*])', r'<i>\1</i>', s)
    return s


class Book:
    def __init__(self, path):
        self.c = Canvas(str(path), pagesize=(PW, PH), invariant=1, pageCompression=1)
        self.c.setTitle('Nota Clausa'); self.c.setAuthor('Josiah Alan-Lee')
        self.active = False; self.y = 0; self.pages = []
        self.st = {
            'body': ParagraphStyle('b', fontName='NCBody', fontSize=11.2, leading=15.2, spaceAfter=8, textColor=INK),
            'tabula': ParagraphStyle('t', fontName='NCBody', fontSize=12.4, leading=17, spaceAfter=12, textColor=INK),
            'h1': ParagraphStyle('h1', fontName='NCTitle', fontSize=25, leading=29, spaceAfter=16, textColor=INK),
            'h2': ParagraphStyle('h2', fontName='NCSmall', fontSize=12, leading=15, spaceAfter=9, spaceBefore=4, textColor=RED),
            'item': ParagraphStyle('i', fontName='NCBody', fontSize=11.2, leading=15.2, spaceAfter=5, leftIndent=14, bulletIndent=2, textColor=INK),
            'cell': ParagraphStyle('c', fontName='NCMono', fontSize=6.6, leading=8.2, textColor=INK),
            'cellb': ParagraphStyle('cb', fontName='NCBody', fontSize=9.6, leading=11.5, textColor=INK),
            'grid': ParagraphStyle('g', fontName='NCMono', fontSize=6.4, leading=8, textColor=INK, alignment=1),
            'code': ParagraphStyle('code', fontName='NCMono', fontSize=8, leading=10.6, textColor=INK, leftIndent=10, spaceAfter=10),
        }

    def start(self, title):
        assert not self.active
        self.active = True; self.y = 638; self.running = title; c = self.c
        c.setFillColor(PAPER); c.rect(0, 0, PW, PH, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor('#8e7b5f')); c.setLineWidth(.45); c.line(40, 679, 464, 679)
        c.setFont('NCSmall', 8); c.setFillColor(INK); c.drawString(42, 690, 'NOTA CLAUSA')
        c.setFillColor(RED); c.drawRightString(462, 690, title.upper())
        c.setFont('NCSmall', 9); c.setFillColor(MUTE); c.drawCentredString(252, 24, str(c.getPageNumber()))
        self.pages.append(dict(page=c.getPageNumber(), title=title))

    def end(self):
        assert self.active
        self.c.showPage(); self.active = False

    def flow(self, flowable, space=8):
        while True:
            _, h = flowable.wrap(400, 10000)
            if self.y - h >= 55:
                flowable.drawOn(self.c, 52, self.y - h); self.y -= h + space; return
            if isinstance(flowable, Paragraph) and self.y > 130:
                parts = flowable.split(400, self.y - 55)
                if len(parts) == 2:
                    _, h0 = parts[0].wrap(400, 10000); parts[0].drawOn(self.c, 52, self.y - h0)
                    self.end(); self.start(self.running); flowable = parts[1]; continue
            self.end(); self.start(self.running)

    def para(self, text, style='body', bullet=None):
        p = Paragraph(inline(text), self.st[style], bulletText=bullet)
        self.flow(p, self.st[style].spaceAfter)

    def table(self, rows, header=True, mono_from=None):
        data = []
        for r, row in enumerate(rows):
            out = []
            for j, cell in enumerate(row):
                style = 'cell' if (mono_from is not None and j >= mono_from) else 'cellb'
                out.append(Paragraph(inline(cell), self.st[style]))
            data.append(out)
        n = len(rows[0])
        if n >= 10:
            data = [[Paragraph(inline(cell), self.st['grid']) for cell in row] for row in rows]
        widths = [400 / n] * n if mono_from is None else [62] + [338 / (n - 1)] * (n - 1)
        t = Table(data, colWidths=widths, hAlign='LEFT')
        t.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, 0), .5, MUTE) if header else ('LINEBELOW', (0, 0), (0, 0), 0, PAPER),
                               ('LINEBELOW', (0, -1), (-1, -1), .3, MUTE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                               ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5)]))
        self.flow(t, 10)

    def markdown(self, text, title, style='body'):
        self.start(title)
        lines = text.split('\n'); i = 0
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                i += 1; continue
            if ln.startswith('# '):
                self.para(ln[2:], 'h1'); i += 1; continue
            if ln.startswith('## '):
                if self.y < 200:
                    self.end(); self.start(self.running)
                self.para(ln[3:], 'h2'); i += 1; continue
            if ln.strip().startswith('```'):
                j = i + 1; block = []
                while not lines[j].strip().startswith('```'):
                    block.append(lines[j].strip('\n')); j += 1
                indent = min(len(b) - len(b.lstrip()) for b in block if b.strip())
                self.flow(Preformatted('\n'.join(b[indent:] for b in block), self.st['code']), 10)
                i = j + 1; continue
            if ln.strip().startswith('|'):
                rows = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    cells = [c.strip() for c in re.split(r'(?<!\\)\|', lines[i].strip())[1:-1]]
                    if not all(re.fullmatch(r'-+', c) for c in cells):
                        rows.append([c.replace('\\|', '|') for c in cells])
                    i += 1
                mono = 1 if any(re.fullmatch(r'`?[0-9a-f]{64}`?', r[-1]) for r in rows) else None
                self.table(rows, mono_from=mono); continue
            m = re.match(r'\s*(\d+)\.\s+(.*)', ln)
            if m:
                body = [m.group(2)]; i += 1
                while i < len(lines) and lines[i].startswith('   ') and not lines[i].strip().startswith(('|', '```', '- ')):
                    body.append(lines[i].strip()); i += 1
                self.para(' '.join(body), 'item', bullet=m.group(1) + '.'); continue
            m = re.match(r'\s*-\s+(.*)', ln)
            if m:
                self.para(m.group(1), 'item', bullet='–'); i += 1; continue
            body = [ln.strip()]; i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'\s*(#|\||```|\d+\.\s|-\s)', lines[i]):
                body.append(lines[i].strip()); i += 1
            self.para(' '.join(body), style)
        self.end()

    def plate(self, k, svg):
        self.start('Field ' + ROMAN[k - 1])
        d = svg2rlg(str(svg))
        s = min(432 / d.width, 612 / d.height)
        d.scale(s, s)
        renderPDF.draw(d, self.c, (PW - d.width * s) / 2, (PH - d.height * s) / 2 - 8)
        self.c.setFont('NCSmall', 9); self.c.setFillColor(INK)
        self.end()

    def title(self):
        self.start('The gathering'); c = self.c
        c.setFont('NCSmall', 34); c.setFillColor(INK); c.drawCentredString(252, 478, 'NOTA CLAUSA')
        c.setFont('NCItalic', 15); c.drawCentredString(252, 444, 'Seven fields, grown by a printed rule')
        c.setFont('NCSmall', 11); c.setFillColor(RED); c.drawCentredString(252, 378, 'SEPTIMUS')
        self.end()


def main():
    fonts()
    out = ROOT / 'out'; out.mkdir(exist_ok=True)
    pdf = out / 'Nota_Clausa_reading.pdf'
    b = Book(pdf)
    b.title()
    tab = (ROOT / 'TABULA.md').read_text()
    b.markdown(tab.split('\n', 1)[1], 'Tabula', style='tabula')
    b.markdown((ROOT / 'REGULA.md').read_text(), 'Regula')
    plates = sorted((ROOT / 'plates').glob('nota-clausa-*.svg'), key=lambda p: int(re.search(r'(\d+)', p.stem).group(1)))
    assert len(plates) == 7
    for k, svg in enumerate(plates, 1):
        b.plate(k, svg)
    b.c.save()
    meta = {'output': pdf.name, 'pages': b.pages,
            'inputs': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [ROOT / 'TABULA.md', ROOT / 'REGULA.md', *plates]}}
    (out / 'build-meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(pdf, len(b.pages), 'pages')


if __name__ == '__main__':
    main()
