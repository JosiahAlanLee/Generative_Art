"""Text boxes shared by the artboard HTML and a local preview.

A box: dict(x, y, w, size, lh, font, color, align, ls (letter-spacing em), rot (deg),
            runs=[(text, style)], para_gap)
style flags: 'i' italic, 'sc' small-caps family, 'red' rubric colour, 'br' paragraph break.
"""
import html
import math

from PIL import ImageFont

from portable_paths import FONTS
FONTDIR = str(FONTS) + "/"
FILES = {
    ("IM FELL English", ""): "IMFeENrm28P.ttf",
    ("IM FELL English", "i"): "IMFeENit28P.ttf",
    ("IM FELL English SC", ""): "IMFeENsc28P.ttf",
    ("IM FELL DW Pica", ""): "IMFePIrm28P.ttf",
    ("IM FELL DW Pica", "i"): "IMFePIit28P.ttf",
    ("IM FELL DW Pica SC", ""): "IMFePIsc28P.ttf",
    ("EB Garamond", ""): "EBGaramond[wght].ttf",
    ("EB Garamond", "i"): "EBGaramond-Italic[wght].ttf",
    ("Spectral", ""): "Spectral-Regular.ttf",
    ("Spectral", "i"): "Spectral-Italic.ttf",
    ("DM Serif Display", ""): "DMSerifDisplay-Regular.ttf",
    ("DM Serif Display", "i"): "DMSerifDisplay-Italic.ttf",
    ("IBM Plex Mono", ""): "IBMPlexMono-Regular.ttf",
    ("Spectral SC", ""): "SpectralSC-Regular.ttf",
    ("Sue Ellen Francisco", ""): "SueEllenFrancisco-Regular.ttf",
    ("Zeyada", ""): "Zeyada.ttf",
    ("Cutive Mono", ""): "CutiveMono-Regular.ttf",
    ("IBM Plex Mono", "i"): "IBMPlexMono-Italic.ttf",
    ("Special Elite", ""): "SpecialElite-Regular.ttf",
    ("UnifrakturMaguntia", ""): "UnifrakturMaguntia-Book.ttf",
}
# web family names (Google Fonts) for the artboards
WEB = {
    "IM FELL English": "'IM Fell English', serif",
    "IM FELL English SC": "'IM Fell English SC', serif",
    "IM FELL DW Pica": "'IM Fell DW Pica', serif",
    "IM FELL DW Pica SC": "'IM Fell DW Pica SC', serif",
    "EB Garamond": "'EB Garamond', serif",
    "Spectral": "'Spectral', serif",
    "DM Serif Display": "'DM Serif Display', serif",
    "IBM Plex Mono": "'IBM Plex Mono', monospace",
    "Spectral SC": "'Spectral SC', serif",
    "Sue Ellen Francisco": "'Sue Ellen Francisco', cursive",
    "Zeyada": "'Zeyada', cursive",
    "Cutive Mono": "'Cutive Mono', monospace",
    "Special Elite": "'Special Elite', monospace",
    "UnifrakturMaguntia": "'UnifrakturMaguntia', serif",
}
_cache = {}
ZW = "\u200b"


def font(fam, style, size):
    k = (fam, "i" if "i" in style else "", size)
    if k not in _cache:
        fn = FILES.get((fam, k[1])) or FILES[(fam, "")]
        _cache[k] = ImageFont.truetype(FONTDIR + fn, size=int(round(size * 4)))
    return _cache[k]


def run_font(box, style):
    fam = box["font"]
    if "sc" in style and box.get("sc_font"):
        fam = box["sc_font"]
    return fam


def text_w(s, fam, style, size, ls=0.0):
    f = font(fam, style, size)
    if "v" in style:
        return f.getlength(s, features=["smcp"]) / 4 + (ls + 0.04) * size * len(s)
    return f.getlength(s) / 4 + ls * size * len(s)


def layout_lines(box):
    """greedy wrap over styled runs -> list of lines; each line = list of (word, style, width)"""
    size = box["size"]
    ls = box.get("ls", 0)
    paras = [[]]
    extras = [0]
    prev_end_space = True
    for text, style in box["runs"]:
        if "br" in style:
            paras.append([])
            extras.append(_extra(style))
            prev_end_space = True
            continue
        glue_first = bool(text) and not prev_end_space and not text[0].isspace()
        if text:
            prev_end_space = text[-1].isspace()
        for k, wd in enumerate(text.split(" ")):
            if wd == "" and not box.get("pre"):
                continue
            frags = wd.split(ZW)
            if k == 0 and glue_first and paras[-1]:
                frags[0] = ZW + frags[0]
            paras[-1].append((frags[0], style))
            for fr in frags[1:]:
                if fr:
                    paras[-1].append((ZW + fr, style))
    lines = []
    cols = box.get("cols", 1)
    colw = (box["w"] - box.get("gap", 0) * (cols - 1)) / cols
    for pi, p in enumerate(paras):
        if pi and extras[pi]:
            lines.append({"gap": extras[pi]})
        cur, cw = [], 0.0
        for wd, st in p:
            fam = run_font(box, st)
            w = text_w(wd.replace(ZW, ""), fam, st, size, ls)
            sp = text_w(" ", fam, st, size, ls)
            add = w if (not cur or wd.startswith(ZW)) else sp + w
            if cur and cw + add > colw:
                lines.append(cur)
                cur, cw = [(wd, st, w)], w
            else:
                cur.append((wd, st, w))
                cw += add
        lines.append(cur)
        lines.append("PARA")
    if lines and lines[-1] == "PARA":
        lines.pop()
    return lines


def _extra(style):
    for tok in style.split():
        if tok.startswith("+"):
            return float(tok[1:])
    return 0


def _h(lines, box):
    n = sum(1 for l in lines if isinstance(l, list))
    gaps = sum(1 for l in lines if l == "PARA")
    extra = sum(l["gap"] for l in lines if isinstance(l, dict))
    return n * box["lh"] + gaps * box.get("para_gap", 0) + extra


def split_cols(box):
    lines = layout_lines(box)
    if box.get("cols", 1) == 1:
        return [lines]
    best = None
    for i in range(1, len(lines)):
        a, b = lines[:i], lines[i:]
        while b and b[0] == "PARA":
            b = b[1:]
        while a and a[-1] == "PARA":
            a = a[:-1]
        ha, hb = _h(a, box), _h(b, box)
        if ha >= hb and (best is None or ha < best[0]):
            best = (ha, a, b)
    return [best[1], best[2]]


def box_height(box):
    return max(_h(c, box) for c in split_cols(box))


# ---------------------------------------------------------------- preview --

def preview_svg(boxes, palette):
    out = []
    for b in boxes:
      cols = split_cols(b)
      g = []
      ncol = b.get("cols", 1)
      colw = (b["w"] - b.get("gap", 0) * (ncol - 1)) / ncol
      for ci, lines in enumerate(cols):
        size, lh = b["size"], b["lh"]
        y = b["y"]
        bx0 = b["x"] + ci * (colw + b.get("gap", 0))
        for ln in lines:
            if ln == "PARA":
                y += b.get("para_gap", 0)
                continue
            if isinstance(ln, dict):
                y += ln["gap"]
                continue
            base = y + lh / 2 + size * 0.33
            total = sum(w for _, _, w in ln) + text_w(" ", b["font"], "", size) * (len(ln) - 1)
            if b.get("align") == "center":
                x = bx0 + (colw - total) / 2
            elif b.get("align") == "right":
                x = bx0 + colw - total
            else:
                x = bx0
            for wd, st, w in ln:
                fam = run_font(b, st)
                col = palette.get("red") if "red" in st else b.get("color", "#000")
                fs = "italic" if "i" in st else "normal"
                if "v" in st:
                    g.append(f'<text x="{x:.1f}" y="{base:.1f}" font-family="{fam}" font-size="{size * 0.8:.1f}" '
                             f'letter-spacing="{size * 0.06:.1f}" fill="{col}">{html.escape(wd.upper())}</text>')
                elif b.get("ls"):
                    cx = x
                    for ch in wd:
                        g.append(f'<text x="{cx:.1f}" y="{base:.1f}" font-family="{fam}" font-size="{size}" '
                                 f'font-style="{fs}" fill="{col}">{html.escape(ch)}</text>')
                        cx += text_w(ch, fam, st, size, b["ls"])
                else:
                    g.append(f'<text x="{x:.1f}" y="{base:.1f}" font-family="{fam}" font-size="{size}" '
                             f'font-style="{fs}" fill="{col}">{html.escape(wd)}</text>')
                x += w + text_w(" ", fam, st, size, b.get("ls", 0))
            y += lh
      if True:
        if b.get("rot"):
            cx, cy = b["x"] + b["w"] / 2, b["y"] + b.get("h", lh) / 2
            out.append(f'<g transform="rotate({b["rot"]} {cx:.1f} {cy:.1f})">' + "".join(g) + "</g>")
        else:
            out.extend(g)
    return "\n".join(out)


# ------------------------------------------------------------------- html --

def html_box(b, palette, indent="  "):
    st = [f"position: absolute", f"left: {b['x']:.0f}px", f"top: {b['y']:.0f}px", f"width: {b['w']:.0f}px",
          f"margin: 0", f"font-family: {WEB[b['font']]}", f"font-size: {b['size']}px",
          f"line-height: {b['lh']}px", f"color: {b.get('color', '#000')}"]
    if b.get("align"):
        st.append(f"text-align: {b['align']}")
    if b.get("ls"):
        st.append(f"letter-spacing: {b['ls']}em")
    if b.get("rot"):
        h = b.get("h", b["lh"])
        st.append(f"height: {h:.0f}px")
        st.append(f"transform: rotate({b['rot']}deg)")
        st.append("transform-origin: center center")
    if b.get("hyph"):
        st.append("hyphens: auto")
    if b.get("pre"):
        st.append("white-space: pre-wrap")
    if b.get("cols", 1) > 1:
        st.append(f"column-count: {b['cols']}")
        st.append(f"column-gap: {b.get('gap', 0)}px")
    paras = [[]]
    pextra = [0]
    for text, style in b["runs"]:
        if "br" in style:
            paras.append([])
            pextra.append(_extra(style))
        else:
            paras[-1].append((text, style))
    inner = []
    for i, p in enumerate(paras):
        spans = []
        for text, style in p:
            css = []
            if "i" in style:
                css.append("font-style: italic")
            if "red" in style:
                css.append(f"color: {palette['red']}")
            for tok in style.split():
                if tok.startswith("#"):
                    css.append(f"color: {tok}")
            if "x" in style.split():
                css.append(f"text-decoration: line-through; text-decoration-color: {palette['red']}; text-decoration-thickness: 1.6px")
            if "sc" in style and b.get("sc_font"):
                css.append(f"font-family: {WEB[b['sc_font']]}")
            if "v" in style:
                css.append("font-variant: small-caps")
                css.append("letter-spacing: 0.04em")
            t = html.escape(text)
            spans.append(f'<span style="{"; ".join(css)}">{t}</span>' if css else t)
        top = (pextra[i] + b.get("para_gap", 0)) if (i and pextra[i]) else 0   # margins collapse: carry the gap
        bot = b.get("para_gap", 0) if i < len(paras) - 1 else 0
        pst = f' style="margin: {top:g}px 0 {bot:g}px 0"' if (top or bot) else ' style="margin: 0"'
        inner.append(f"<p{pst}>{''.join(spans)}</p>")
    tag = b.get("tag", "div")
    return f'{indent}<{tag} style="{"; ".join(st)}">' + "".join(inner) + f"</{tag}>"
