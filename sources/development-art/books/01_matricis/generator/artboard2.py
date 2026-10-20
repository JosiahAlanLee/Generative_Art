"""Artboard sources for the second pass."""
import html as H
import sys

from layout import html_box, WEB

GF = {
    "IM FELL English": "IM+Fell+English:ital@0;1",
    "IM FELL English SC": "IM+Fell+English+SC",
    "IM FELL DW Pica": "IM+Fell+DW+Pica:ital@0;1",
    "IM FELL DW Pica SC": "IM+Fell+DW+Pica+SC",
    "EB Garamond": "EB+Garamond:ital,wght@0,400;0,500;1,400",
    "Spectral": "Spectral:ital@0;1",
    "Spectral SC": "Spectral+SC",
    "DM Serif Display": "DM+Serif+Display",
    "IBM Plex Mono": "IBM+Plex+Mono:ital@0;1",
    "Sue Ellen Francisco": "Sue+Ellen+Francisco",
    "Zeyada": "Zeyada",
    "Cutive Mono": "Cutive+Mono",
    "Special Elite": "Special+Elite",
    "UnifrakturMaguntia": "UnifrakturMaguntia",
}


def fonts_url(boxes, extra=()):
    fams = list(extra)
    for b in boxes:
        for f in (b.get("font"), b.get("sc_font")):
            if f and f not in fams:
                fams.append(f)
    return "https://fonts.googleapis.com/css2?" + "&amp;".join(f"family={GF[f]}" for f in fams) + "&amp;display=swap"


def page(title, boxes, pal, bg, ink, blob, alt, base_font, W=1000, Hh=1600, extra="", script=None, props=None, fonts_extra=()):
    out = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">', f'<title>{H.escape(title)}</title>',
           '<script src="./support.js"></script>', '</head>', '<body>', '<x-dc>', '<helmet>',
           f'<link rel="stylesheet" href="{fonts_url(boxes, fonts_extra)}">', '<style>', 'body{margin:0}',
           f'a{{color:{pal["red"]}}}a:hover{{color:{ink}}}', '</style>', '</helmet>',
           f'<div style="position: relative; width: {W}px; height: {Hh}px; overflow: hidden; background: {bg}; color: {ink}; font-family: {WEB[base_font]}">',
           f'<img src="{blob}" alt="{H.escape(alt)}" style="position: absolute; left: 0px; top: 0px; width: {W}px; height: {Hh}px">']
    for b in boxes:
        out.append(html_box(b, pal, indent=""))
    if extra:
        out.append(extra)
    out.append('</div>')
    out.append('</x-dc>')
    p = '{"$preview":{"width":%d,"height":%d}}' % (W, Hh) if props is None else props
    out.append(f"<script type=\"text/x-dc\" data-dc-script data-props='{p}'>")
    out.append(script or "class Component extends DCLogic {\nrenderVals() {\nreturn {};\n}\n}")
    out += ['</script>', '</body>', '</html>']
    return "\n".join(out)
