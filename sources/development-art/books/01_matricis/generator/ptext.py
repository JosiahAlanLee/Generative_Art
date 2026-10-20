"""Accurate-ish text preview: PIL with the same font files the artboards load."""
from PIL import Image, ImageDraw, ImageFont
import layout
from layout import FONTDIR, FILES, split_cols, run_font

_f = {}
def F(fam, style, px):
    k = (fam, 'i' if 'i' in style else '', round(px * 4) / 4)
    if k not in _f:
        fn = FILES.get((fam, k[1])) or FILES[(fam, '')]
        _f[k] = ImageFont.truetype(FONTDIR + fn, size=k[2])
    return _f[k]

def draw_boxes(img, boxes, pal, S=2):
    d = ImageDraw.Draw(img)
    for b in boxes:
        if b.get('rot'):
            w, hgt = int(b['w'] * S), int(b.get('h', b['lh']) * S)
            layer = Image.new('RGBA', (w, hgt), (0, 0, 0, 0))
            _draw(ImageDraw.Draw(layer), dict(b, x=0, y=0, rot=0), pal, S)
            layer = layer.rotate(-b['rot'], expand=True)
            cx, cy = (b['x'] + b['w'] / 2) * S, (b['y'] + b.get('h', b['lh']) / 2) * S
            img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)
        else:
            _draw(d, b, pal, S)

def _draw(d, b, pal, S):
    ncol = b.get('cols', 1)
    colw = (b['w'] - b.get('gap', 0) * (ncol - 1)) / ncol
    size, lh = b['size'], b['lh']
    for ci, lines in enumerate(split_cols(b)):
        y = b['y']
        x0 = b['x'] + ci * (colw + b.get('gap', 0))
        for ln in lines:
            if ln == 'PARA':
                y += b.get('para_gap', 0); continue
            if isinstance(ln, dict):
                y += ln['gap']; continue
            sp = layout.text_w(' ', b['font'], '', size, b.get('ls', 0))
            total = sum(w for _, _, w in ln) + sp * (len(ln) - 1)
            al = b.get('align')
            x = x0 + ((colw - total) / 2 if al == 'center' else (colw - total) if al == 'right' else 0)
            for wi, (wd, st, w) in enumerate(ln):
                wd = wd.replace(layout.ZW, '')
                fam = run_font(b, st)
                f = F(fam, st, size * S)
                asc, desc = f.getmetrics()
                base = (y * S) + (lh * S - (asc + desc)) / 2 + asc
                col = pal['red'] if 'red' in st else b.get('color', '#000')
                for tok in st.split():
                    if tok.startswith('#'):
                        col = tok
                feats = ['smcp'] if 'v' in st else None
                ls = (b.get('ls', 0) + (0.04 if 'v' in st else 0)) * size * S
                if ls:
                    cx = x * S
                    for ch in wd:
                        d.text((cx, base), ch, font=f, fill=col, anchor='ls', features=feats)
                        cx += f.getlength(ch, features=feats) + ls
                else:
                    d.text((x * S, base), wd, font=f, fill=col, anchor='ls', features=feats)
                if 'x' in st.split():
                    yy = base - asc * 0.3
                    d.line([(x * S, yy), ((x + w) * S, yy)], fill=pal['red'], width=max(2, int(1.6 * S)))
                nxt = ln[wi + 1][0] if wi + 1 < len(ln) else ''
                x += w + (0 if nxt.startswith(layout.ZW) else layout.text_w(' ', fam, st, size, b.get('ls', 0)))
            y += lh
