#!/usr/bin/env python3
"""Four-page proof: two vector plates, the engraving before/after, Trail First before/after."""
from pathlib import Path
import io, json, re
import numpy as np
from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import cairosvg
import pymupdf as fitz

ROOT = Path(__file__).resolve().parent; OUT = ROOT / 'output'; REF = ROOT / 'reference'
PAPER = '#f3eddf'; INK = '#2e2a22'


def svg_crop(path, box, zoom):
    """Rasterise a region of a plate SVG on white."""
    x0, y0, x1, y1 = box
    s = Path(path).read_text()
    s = re.sub(r'viewBox="[^"]+"', f'viewBox="{x0} {y0} {x1 - x0} {y1 - y0}"', s, count=1)
    s = re.sub(r'<svg([^>]*?) width="[^"]+" height="[^"]+"',
               lambda m: f'<svg{m.group(1)} width="{(x1 - x0) * zoom:.0f}" height="{(y1 - y0) * zoom:.0f}"', s, count=1)
    png = cairosvg.svg2png(bytestring=s.encode(), output_width=int((x1 - x0) * zoom), output_height=int((y1 - y0) * zoom))
    im = Image.open(io.BytesIO(png)).convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im)
    return bg.convert('RGB')


def main():
    pdfmetrics.registerFont(TTFont('PlateSerif', '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'))
    front = json.loads((OUT / 'front-report.json').read_text())
    second = json.loads((OUT / 'second-report.json').read_text())
    big = json.loads((OUT / 'front-296mm-report.json').read_text())
    net = json.loads((OUT / 'trail-network-20000.json').read_text())
    tl = lambda r, t: next(x for x in r['treatments'] if x['treatment'] == t)
    pdf = OUT / 'Statue_v2_Study.pdf'
    c = Canvas(str(pdf), pagesize=(504, 720), pageCompression=1, invariant=1)  # no timestamps or random ids
    c.setTitle('Scanned statue v2 - resolution study'); c.setAuthor('Scan by the Smithsonian Institution (CC0)')

    def page(title, num):
        c.setFillColor(HexColor(PAPER)); c.rect(0, 0, 504, 720, fill=1, stroke=0)
        c.setFillColor(HexColor(INK)); c.setFont('PlateSerif', 9); c.drawCentredString(252, 683, 'SCANNED STATUE / V2')
        c.setFont('PlateSerif', 17); c.drawCentredString(252, 656, title)
        c.setFont('PlateSerif', 8); c.drawCentredString(252, 25, f'{num} / 4')

    def raster(im, x, y, w, h, tint=True):
        a = np.asarray(im.convert('RGB'), dtype=float)
        if tint:  # white plate renders take on the paper colour; paper-backed ones are already tinted
            a = a / 255 * np.array([243, 237, 223])
        b = io.BytesIO(); Image.fromarray(np.uint8(a)).save(b, format='PNG')
        c.drawImage(ImageReader(b), x, y, width=w, height=h)

    def paragraph(text, y, size=8.6, leading=12.4, x=36, width=432):
        c.setFont('PlateSerif', size); line = ''
        for word in text.split():
            cand = (line + ' ' + word).strip()
            if pdfmetrics.stringWidth(cand, 'PlateSerif', size) > width:
                c.drawString(x, y, line); y -= leading; line = word
            else:
                line = cand
        if line:
            c.drawString(x, y, line); y -= leading
        return y

    page('I. A figure in the recess', 1)
    fc = tl(front, 'cross')
    c.setFont('PlateSerif', 9)
    c.drawCentredString(252, 62, f'Contours, fold lines and surface hatches. {fc["line_metres"]:.1f} m of line at 148 mm.')
    c.setFont('PlateSerif', 7.5)
    c.drawCentredString(252, 46, 'Hiram Powers, Model of the Greek Slave (1843). Smithsonian American Art Museum. Scan CC0.')
    c.showPage()
    page('II. The second angle', 2)
    sc = tl(second, 'cross')
    c.setFont('PlateSerif', 9)
    c.drawCentredString(252, 62, f'The camera of the Trail First study. {sc["line_metres"]:.1f} m of line at 148 mm.')
    c.setFont('PlateSerif', 7.5)
    c.drawCentredString(252, 46, 'Same scan, light, setting and tone curve as v1; geometry and light are read at stroke resolution.')
    c.showPage()

    page('Where the detail was going', 3)
    box = (700, 210, 880, 400)
    panels = [(svg_crop(REF / 'v1-front-cross.svg', box, 4), 'v1, 148 mm'),
              (svg_crop(OUT / 'front-cross.svg', box, 4), 'v2, 148 mm'),
              (svg_crop(OUT / 'front-296mm-cross.svg', box, 4), 'v2, 296 mm, same pen')]
    for k, (im, label) in enumerate(panels):
        x = 36 + k * 148; raster(im, x, 470, 136, 136 * im.height / im.width)
        c.setFont('PlateSerif', 8); c.drawString(x, 458, label)
    c.setFont('PlateSerif', 7.5); c.drawString(36, 446, 'The head, enlarged 4x from the plate (about 18 x 19 mm at 148 mm).')
    y = 420
    y = paragraph(f'Outlines. The GLB is split along its texture atlas: {front["glb_vertex_records"]:,} vertex records for '
                  f'{front["welded_vertices"]:,} positions. v1 found silhouettes by vertex index, so they broke at every '
                  'seam: 4,101 chains with a median of 3 vertices, drawn as dashes. v2 welds the seams and draws the '
                  'zero set of n.v on vertex normals: 430 continuous chains, tested for visibility from a point '
                  'lifted just off the surface.', y) - 6
    y = paragraph('Fold lines. Suggestive contours (DeCarlo et al., 2003) draw the eyelids, the side of the nose, the '
                  'line of the lips and the jaw. On a lit face, tone alone cannot carry these at this scale.', y) - 6
    y = paragraph('Light. v1 read light from a 600 x 760 screen buffer (2.5 plate units per sample, flat triangle '
                  'normals, 3 x 3 median). v2 shades the scan\'s vertices with 64 light, 32 occlusion and 12 bounce '
                  'samples, and the setting on 0.01-unit texture grids, then interpolates to each stroke sample. '
                  'The tone curve is unchanged.', y) - 6
    y = paragraph(f'Line spacing. v1 spaced candidates 0.008 scene units apart, about 3.1 pen widths, at any plate size. '
                  f'v2 spaces them {front["spacing_pen_widths"]} pen widths apart on paper. At 148 mm that gives '
                  f'{tl(front, "cross")["line_metres"]:.0f} m of line. At 296 mm with the same 0.09 mm pen it gives '
                  f'{tl(big, "cross")["line_metres"]:.0f} m, which is where the lit face starts to carry tone.', y) - 6
    paragraph('Not changed: scan, pose, camera, light position, exposure, tone curve, hatch plane families and the '
              'nested on/off order (now 64 steps instead of 32). The 150k-triangle mesh projects to ~3.9 plate units '
              'per edge, so at 296 mm about five hatch lines cross each triangle. Beyond that, the museum\'s larger '
              'download becomes the limit.', y)
    c.showPage()

    page('Trail First at plate resolution', 4)
    box = (500, 120, 1020, 1720)
    ims = [(Image.open(REF / 'v1-trail-first-mono.png').convert('RGB').crop(box), 'v1, unchanged sampler'),
           (Image.open(OUT / 'trail-original-plate-scale.png').convert('RGB').crop(box), 'Unchanged rules, 0.12 mm grid'),
           (Image.open(OUT / 'trail-network-20000.png').convert('RGB').crop(box), 'Guided food, marks on trails')]
    for k, (im, label) in enumerate(ims):
        x = 40 + k * 148; h = 128 * im.height / im.width
        raster(im, x, 620 - h, 128, h, tint=False); c.setFont('PlateSerif', 8); c.drawString(x, 610 - h, label)
    y = 202
    y = paragraph('The vendor sampler works in grid cells: sensors 6-8 cells, steps of 1.25 cells, 3 x 3 diffusion. '
                  'v1 fixed the grid at 192 cells across. One cell was 7.8 plate units on the full frame and 2.45 on '
                  'the crop. On the full frame the sensors reached 47-62 plate units, about a third of the head\'s '
                  'height, and the trails merged into one trunk.', y) - 6
    y = paragraph(f'Here a cell is {net["cell_plate_units"]} plate units ({net["cell_mm"]:.2f} mm), with '
                  f'{net["agents_per_colony"]:,} agents per colony scaled to the statue\'s area. The vendor code is unchanged. '
                  'Under the original rules the network now branches inside the figure. With the guided food '
                  '(darkness plus gradient), the trails follow edges. Placing the marks on the trails rather than the '
                  f'food draws the figure as a network: {net["primitives"]:,} marks, {net["radius_mm"][0]}-'
                  f'{net["radius_mm"][1]} mm.', y) - 6
    paragraph('The mark budget is the other half of resolution. 7,200 marks over the figure is about one per 45 '
              'square plate units; in v1 about 450 of them landed in the whole head and neck.', y)
    c.save()
    doc = fitz.open(pdf)
    for i, name in enumerate(['front-cross', 'second-cross']):
        svg = (OUT / f'{name}.svg').read_text().replace('fill="white"', f'fill="{PAPER}"')
        plate = fitz.open(stream=cairosvg.svg2pdf(bytestring=svg.encode()), filetype='pdf')
        doc[i].show_pdf_page(fitz.Rect(42, 97, 462, 629), plate, 0); plate.close()
    tmp = pdf.with_suffix('.writing.pdf'); doc.save(tmp, garbage=4, deflate=True, no_new_id=True); doc.close(); tmp.replace(pdf)
    check = fitz.open(pdf)
    assert len(check) == 4 and all(not check[i].get_images() for i in (0, 1))
    for i, p in enumerate(check):
        p.get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save(OUT / f'proof-page-{i + 1}.png')
    print('Proof written:', pdf)
    preview(ROOT / 'preview.jpg')


def preview(path, height=620):
    """Front plate, second plate, Trail First network: one strip for the README."""
    tiles = []
    for name, box in (('front-cross', (420, 60, 1140, 1760)), ('second-cross', (300, 60, 1020, 1760)),
                      ('trail-network-20000-supported', (430, 100, 1150, 1800))):
        im = Image.open(OUT / f'{name}.png').convert('RGB').crop(box)
        a = np.asarray(im, float)
        if name != 'trail-network-20000-supported':
            a = a / 255 * np.array([243, 237, 223])   # white plates onto the proof's paper
        im = Image.fromarray(np.uint8(a))
        tiles.append(im.resize((round(im.width * height / im.height), height), Image.Resampling.LANCZOS))
    gap = 14
    strip = Image.new('RGB', (sum(t.width for t in tiles) + gap * (len(tiles) + 1), height + 2 * gap), (243, 237, 223))
    x = gap
    for t in tiles:
        strip.paste(t, (x, gap)); x += t.width + gap
    strip.save(path, quality=88, optimize=True)
    print('Preview written:', path)


if __name__ == '__main__':
    main()
