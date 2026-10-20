#!/usr/bin/env python3
"""The three scenes on 7 x 10 in pages: plates as vector, then 'who holds the shade'."""
import io
import json
from pathlib import Path

import cairosvg
import numpy as np
import pymupdf as fitz
from PIL import Image

HERE = Path(__file__).resolve().parent
PAPER = (237 / 255, 230 / 255, 212 / 255)
PAPER_HEX = '#ede6d4'
TEXT = (51 / 255, 45 / 255, 36 / 255)
RULE = (0.55, 0.5, 0.42)
SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'    # DejaVu Serif where installed (Linux)
HAVE_SERIF = Path(SERIF).exists()
FONT = fitz.Font(fontfile=SERIF) if HAVE_SERIF else fitz.Font('tiro')   # else PDF Times-Roman
FONTNAME = 'serif' if HAVE_SERIF else 'tiro'
PAGES = 12


def svg_pdf(path):
    svg = Path(path).read_text().replace('fill="white"', f'fill="{PAPER_HEX}"')
    return fitz.open('pdf', cairosvg.svg2pdf(bytestring=svg.encode()))


def page(doc, header, title, num):
    p = doc.new_page(width=504, height=720)
    p.draw_rect(p.rect, color=None, fill=PAPER)
    if HAVE_SERIF:
        p.insert_font(fontname='serif', fontfile=SERIF)
    centre(p, header, 41, 9)
    centre(p, title, 71, 17)
    centre(p, f'{num} / {PAGES}', 698, 8)
    return p


def centre(p, s, y, size):
    p.insert_text((252 - FONT.text_length(s, fontsize=size) / 2, y), s, fontname=FONTNAME, fontsize=size, color=TEXT)


def text(p, xy, s, size=8):
    p.insert_text(xy, s, fontname=FONTNAME, fontsize=size, color=TEXT)


def plate(p, rect, svg, caption=None, caption_y=None):
    p.show_pdf_page(rect, svg_pdf(svg), 0)
    p.draw_rect(rect, color=RULE, width=0.4)
    if caption:
        centre(p, caption, caption_y or rect.y1 + 14, 8.5)


def portrait(doc, header, num, title, svg, caption):
    p = page(doc, header, title, num)
    plate(p, fitz.Rect(42, 88, 462, 88 + 420 * 1900 / 1500), svg, caption, 652)


def image(p, rect, path):
    b = io.BytesIO()
    Image.open(path).convert('RGB').save(b, format='PNG')
    p.insert_image(rect, stream=b.getvalue())
    p.draw_rect(rect, color=RULE, width=0.4)


LEGEND = [((252, 249, 240), 'lit: the light over the ambient'), ((168, 162, 150), 'shade, unoccupied'),
          ((196, 150, 64), 'strain A, on its own ground'), ((150, 62, 36), 'strain A, ground taken from B'),
          ((84, 110, 128), 'strain B, on its own ground'), ((30, 52, 96), 'strain B, ground taken from A')]


def legend(p, x, y):
    for k, (c, label) in enumerate(LEGEND):
        r = fitz.Rect(x, y + 12 * k - 7, x + 9, y + 12 * k + 2)
        p.draw_rect(r, color=RULE, fill=tuple(v / 255 for v in c), width=0.3)
        text(p, (x + 14, y + 12 * k), label, 7.5)
    text(p, (x, y + 12 * len(LEGEND) + 4), 'rings: inoculation sites (red A, blue B)', 7.5)
    return y + 12 * len(LEGEND) + 16


def pct(v):
    return '<0.1%' if 0 < v < 0.001 else f'{100 * v:.1f}%'


def numbers(p, x, y, stats, ink_label):
    sc, pl = stats['scene'], stats['plate']
    lines = [f'trail on lit ground: {pct(sc["trail_on_lit_ground"])}',
             f'occupied ground that changed strain: {100 * sc["changed_strain"]:.1f}%',
             f'veins drawn: {pl["veins"]}; hatch marks cut: {pl["hatch_marks_cut"]}',
             f'ink near the mould: {pl["ink_near_mould"]["base"]:.3f} before, {pl["ink_near_mould"]["with_mould"]:.3f} after',
             ink_label]
    if 'sol_fans_removed' in pl:
        lines.append(f"Sol's shadow fans removed: {pl['sol_fans_removed']}; traced-shadow marks: {pl['cast_shadow_marks']}")
    for k, s in enumerate(lines):
        text(p, (x, y + 11 * k), s, 7.5)
    y += 11 * len(lines) + 8
    text(p, (x, y), 'per surface: lit share / changed strain / trail on lit', 7.5)
    y += 11
    for name, v in stats.items():
        if isinstance(v, dict) and 'lit_share' in v:
            text(p, (x, y), f'{name}: {100 * v["lit_share"]:.0f}% / {pct(v["changed_strain"])} / '
                              f'{pct(v["trail_on_lit_ground"])}', 7.2)
            y += 10
    return y


def diagnostics_portrait(doc, header, num, out, ink_label):
    p = page(doc, header, 'Who holds the shade', num)
    stats = json.loads((out / 'stats.json').read_text())
    w = 250
    r = fitz.Rect(42, 92, 42 + w, 92 + w * 1900 / 1500)
    image(p, r, out / 'shade-map.png')
    legend(p, 306, 104)
    numbers(p, 42, r.y1 + 24, stats, ink_label)


def preview(path, height=620):
    """One strip of the three 'mould in the shadow' plates, for the folder's README."""
    plates = [HERE / 'hortus' / 'output' / 'H1-mould-in-shadow.png', HERE / 'porticus' / 'output' / 'P1-mould-in-shadow.png',
              HERE / 'memento' / 'output' / 'M1-mould-in-shadow.png']
    if not all(f.exists() for f in plates):          # e.g. `build.py hortus` on a fresh checkout
        print('preview skipped: build all three scenes to make it')
        return
    ims = []
    for f in plates:
        im = Image.open(f).convert('RGB')
        ims.append(im.resize((round(im.width * height / im.height), height), Image.LANCZOS))
    gap = 16
    strip = Image.new('RGB', (sum(i.width for i in ims) + gap * (len(ims) + 1), height + 2 * gap), (237, 230, 212))
    x = gap
    for im in ims:
        tinted = Image.fromarray((np.asarray(im, float) * np.array([237, 230, 212]) / 255).round().astype(np.uint8))
        strip.paste(tinted, (x, gap))
        x += im.width + gap
    strip.save(path, quality=84, optimize=True)


def main():
    doc = fitz.open()
    n = 1
    # ---------------- Hortus ----------------
    H = HERE / 'hortus'
    hw, hh = 380, 380 * 1250 / 1800
    p = page(doc, 'HORTUS INTERVALLORUM', 'I. As drawn, and the shade traced', n)
    x0 = (504 - hw) / 2
    plate(p, fitz.Rect(x0, 90, x0 + hw, 90 + hh), H / 'inputs' / '01-garden-engraved.svg',
          "Sol's plate: faces shaded by angle to the sun, three hand-placed shadow fans.")
    plate(p, fitz.Rect(x0, 384, x0 + hw, 384 + hh), H / 'output' / 'H0-traced-shade.svg',
          'The fans replaced by cast shadow traced from the same sun.')
    n += 1
    p = page(doc, 'HORTUS INTERVALLORUM', 'II. The mould in the shade', n)
    plate(p, fitz.Rect(x0, 90, x0 + hw, 90 + hh), H / 'output' / 'H1-mould-in-shadow.svg',
          'Two strains in the traced shade; paper reserved around the veins.')
    plate(p, fitz.Rect(x0, 384, x0 + hw, 384 + hh), H / 'output' / 'H2-mould-alone.svg', 'The mould alone.')
    n += 1
    p = page(doc, 'HORTUS INTERVALLORUM', 'III. The shade, closer', n)
    for k, ((x0c, y0c, x1c, y1c), cap) in enumerate((((60, 600, 940, 1000), 'The left wall and the fountain: strain A from the near wall, strain B from the far.'),
                                                     ((1000, 760, 1500, 1010), "The tree's shadow and the bed beside it."))):
        src = svg_pdf(H / 'output' / 'H1-mould-in-shadow.svg')
        sc_ = src[0].rect.width / 1800
        wbox = 420
        hbox = wbox * (y1c - y0c) / (x1c - x0c)
        y = 92 if k == 0 else 92 + 420 * 400 / 880 + 40
        rect = fitz.Rect(42, y, 42 + wbox, y + hbox)
        p.show_pdf_page(rect, src, 0, clip=fitz.Rect(x0c * sc_, y0c * sc_, x1c * sc_, y1c * sc_))
        p.draw_rect(rect, color=RULE, width=0.4)
        centre(p, cap, rect.y1 + 14, 8.5)
    n += 1
    p = page(doc, 'HORTUS INTERVALLORUM', 'Who holds the shade', n)
    stats = json.loads((H / 'output' / 'stats.json').read_text())
    r = fitz.Rect(42, 92, 462, 92 + 420 * 1250 / 1800)
    image(p, r, H / 'output' / 'shade-map.png')
    y = legend(p, 42, r.y1 + 22)
    numbers(p, 250, r.y1 + 22, stats, 'traced-shadow hatch held around the cut; Sol\'s marks only cut')
    n += 1
    # ---------------- Porticus ----------------
    P = HERE / 'porticus' / 'output'
    portrait(doc, 'PORTICUS INTERVALLORUM', n, 'I. Ink by screen spacing', P / 'P0-screen-spaced.svg',
             "Plate II of the previous package: the base the mould is cut into.")
    n += 1
    portrait(doc, 'PORTICUS INTERVALLORUM', n, 'II. The mould in the shadow', P / 'P1-mould-in-shadow.svg',
             "Two strains; the doorway's light repels them. Hatching held around the white line.")
    n += 1
    portrait(doc, 'PORTICUS INTERVALLORUM', n, 'III. The mould alone', P / 'P2-mould-alone.svg',
             'Structure and veins only.')
    n += 1
    diagnostics_portrait(doc, 'PORTICUS INTERVALLORUM', n, P, 'hatching re-allocated to hold the tone around the cut')
    n += 1
    # ---------------- Memento ----------------
    M = HERE / 'memento'
    portrait(doc, 'MEMENTO MORI', n, 'I. Light through the casement', M / 'inputs' / '02-ray-lit.svg',
             "Sol's plate II, reproduced exactly: the base the mould is cut into.")
    n += 1
    portrait(doc, 'MEMENTO MORI', n, 'II. The mould in the shadow', M / 'output' / 'M1-mould-in-shadow.svg',
             "Two strains from the orbits, the jambs and the sill; Sol's marks only cut.")
    n += 1
    portrait(doc, 'MEMENTO MORI', n, 'III. The mould alone', M / 'output' / 'M2-mould-alone.svg',
             'Structure and veins only.')
    n += 1
    diagnostics_portrait(doc, 'MEMENTO MORI', n, M / 'output',
                         "Sol's threshold steps kept: the white line lifts the ink near the mould")
    assert n == PAGES
    doc.set_metadata(dict(title='Photophobic: the mould in three scenes',
                          author='Josiah Alan-Lee / Claude mould and white line / ChatGPT-Codex scenes and light',
                          subject='Two strains of a light-avoiding Physarum culture, drawn as white line, in the garden, corridor and windowsill studies'))
    out = HERE / 'Photophobic_Three_Scenes.pdf'
    doc.save(out, garbage=3, deflate=True, no_new_id=True)     # no random /ID: the file is reproducible
    print('saved', out, len(doc), 'pages')
    preview(HERE / 'preview.jpg')


if __name__ == '__main__':
    main()
