from portable_paths import OUTPUT
import sys, re, json, importlib
import cairosvg
from layout import preview_svg, box_height
from portable_paths import PREVIEW
P = str(PREVIEW) + "/"

def compose(plate_svg, boxes, pal, paper, W, H, name, guides=False):
    from PIL import Image, ImageDraw
    import io, ptext
    S = 2
    inner = re.sub(r'^<svg[^>]*>', '', plate_svg.strip()).rsplit('</svg>', 1)[0]
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="{paper}"/>{inner}</svg>'
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=W * S)
    img = Image.open(io.BytesIO(png)).convert('RGBA')
    ptext.draw_boxes(img, boxes, pal, S)
    if guides:
        d = ImageDraw.Draw(img)
        for b in boxes:
            d.rectangle([b['x']*S, b['y']*S, (b['x']+b['w'])*S, (b['y']+box_height(b))*S], outline=(0,170,120,255))
    img = img.resize((W, H), Image.LANCZOS).convert('RGB')
    img.save(P + name + '.png')
    return P + name + '.png'

if __name__ == '__main__':
    which = sys.argv[1]
    if which == '1':
        import page1, text1
        doc, meta = page1.build()
        bx = text1.boxes(meta)
        AX = page1.AX
        yN, yG, yApex, yD, yF, yGr, eh = (meta[k] for k in ("yN","yG","yApex","yD","yF","yGr","exec_h"))
        keep = []
        for b in bx:
            if b.get('rot'):
                keep.append((60, b['y'] + 9 - b['w']/2, 92, b['y'] + 9 + b['w']/2)); continue
            keep.append((b['x'], b['y'], b['x'] + b['w'], b['y'] + box_height(b)))
        keep += [(AX-112, 240, AX+112, 1060), (AX-152, 690, AX+152, 762), (AX-112, 262, AX+112, 322),
                 (86, yN-24, 116, yD+24), (884, yD-24, 918, yGr+24), (300, 780, 470, 850), (100, 1010, 900, 1070)]
        for (x, y) in meta['route']:
            keep.append((x-30, y-30, x+30, y+30))
        far = max(meta['route'], key=lambda p: p[0])
        keep.append((far[0], far[1]-50, far[0]+80, far[1]+50))
        ym = yApex + eh/2
        glosses = [("noc", 350, yN + 30, 10, "right"), ("mandatory escalation", 352, yG + 36, 9.5, "right"),
                   ("executive", 395, ym + 30, 10, "right"), ("technical dispatch", 408, yD + 26, 9.5, "right"),
                   ("field crew", 408, yF + 26, 9.5, "right"), ("added route", 618, 333, 9.5, "left")]
        doc, meta = page1.build(keep=keep, glosses=glosses)
        sv = doc.svg()
        open(f'{OUTPUT}/p1_plate.svg', 'w').write(sv)
        json.dump(meta, open(f'{OUTPUT}/p1_meta.json', 'w'))
        for b in bx:
            hh = box_height(b)
            if b['id'] in ('body','lede','title'):
                print(f'{b["id"]:10s} y={b["y"]:.0f} h={hh:.0f} end={b["y"]+hh:.0f}')
        print(compose(sv, bx, text1.PAL, page1.PAPER, page1.W, page1.H, 'p1', guides='g' in sys.argv[2:]))
        print('plate bytes', len(sv))

    if which == '2':
        import page2, text2
        doc, meta = page2.build()
        sv = doc.svg()
        open(f'{OUTPUT}/p2_plate.svg', 'w').write(sv)
        bx = text2.boxes(meta)
        for b in bx:
            if b['id'] in ('lede','mark','orient','cap0','cap4','cap8'):
                hh = box_height(b); print(f'{b["id"]:10s} y={b["y"]:.0f} h={hh:.0f} end={b["y"]+hh:.0f}')
        print(compose(sv, bx, text2.PAL, page2.EARTH, page2.W, page2.H, 'p2', guides='g' in sys.argv[2:]))
        print('plate bytes', len(sv))

    if which == '3':
        import page3, text3
        doc, meta = page3.build()
        sv = doc.svg()
        open(f'{OUTPUT}/p3_plate.svg', 'w').write(sv)
        bx = text3.boxes(meta)
        for b in bx:
            if b['id'] in ('body','legend','foot'):
                hh = box_height(b); print(f'{b["id"]:10s} y={b["y"]:.0f} h={hh:.0f} end={b["y"]+hh:.0f}')
        print(compose(sv, bx, text3.PAL, page3.PAPER, page3.W, page3.H, 'p3', guides='g' in sys.argv[2:]))
        print('plate bytes', len(sv))
