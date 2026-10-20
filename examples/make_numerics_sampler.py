"""Number systems drawn with the book's hands: AQ -> Tic Xenotation, and the numogram.

Run from the repository root: python examples/make_numerics_sampler.py
Writes examples/out/numerics-sampler.svg, its PNG and numerics-manifest.json.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "sources/codex-intervallorum"
sys.path[:0] = [str(BOOK / "common/geometry"), str(ROOT / "lib/numerics")]
from core import Doc, bezier  # noqa: E402
import marks  # noqa: E402
import aq  # noqa: E402
import numogram as ng  # noqa: E402
import xenotation as tx  # noqa: E402

PHRASE = "HIC ET NUNC"
SEEDS = [31, 37, 41, 43]


def doc():
    styles = {}
    for color, ink in (("ink", "#252825"), ("red", "#a32b24")):
        for weight, width in (("core", 1.1), ("orn", .65), ("hair", .35)):
            styles[f"{color}_{weight}"] = {"fill": "none", "stroke": ink, "stroke-width": width, "stroke-linecap": "round"}
        styles[f"{color}_fill"] = {"fill": ink, "stroke": "none"}
        for size, width in (("s", .65), ("m", 1.05), ("l", 1.55)):
            styles[f"{color}_g{size}"] = {"fill": "none", "stroke": ink, "stroke-width": width, "stroke-linecap": "round"}
    return Doc(240, 180, styles)


def text(x, y, s, size=7, fill="#645b4b", anchor="middle", family="sans-serif"):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}">{s}</text>')


def centred_glyph(h, value, cx, cy, size, **kw):
    g = tx.layout(value if isinstance(value, str) else tx.encode(value),
                  **{k: v for k, v in kw.items() if k == "style"})
    w, ht = g["width"] * size, g["height"] * size
    tx.draw(h, value, cx - w / 2, cy - ht / 2, size, **kw)
    return w, ht


def aq_panel(mode):
    value = aq.aq(PHRASE)
    glyph = tx.encode(value)
    d = doc()
    h = marks.Hand(d, random.Random(SEEDS[0 if mode == "ink" else 1]), mode=mode, amp=.35,
                   grain={"core": (2.2, .55), "sizes": (5, 3, 1), "stray": .02})
    style = "capsule" if mode == "ink" else "parens"
    weight = "core"
    centred_glyph(h, glyph, 120, 80, 19 if mode == "ink" else 21, weight=weight, style=style)
    labels = [text(120, 160, f"{PHRASE} = AQ {value} = {glyph}", 8, "#252825", family="serif")]
    return d.body(), labels, dict(phrase=PHRASE, aq=value, xenotation=glyph, style=style)


def table_panel():
    d = doc()
    h = marks.Hand(d, random.Random(SEEDS[2]), amp=.2)
    labels = []
    for i, n in enumerate(range(2, 14)):
        cx, cy = 34 + (i % 4) * 57, 30 + (i // 4) * 56
        centred_glyph(h, n, cx, cy, 7, weight="orn")
        labels.append(text(cx, cy + 25, f"{n}  {tx.encode(n)}", 6.5))
    return d.body(), labels, dict(range=[2, 13])


def zone_xy(z, cx=120, cy=86, r=66):
    # Our own layout, not the Ccru drawing: zones on a circle placed so every
    # nine-sum syzygy is a horizontal rung, 4::5 at the top and 0::9 at the bottom.
    a = math.radians(108 + 36 * z)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def toward(p, q, gap):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1
    return p[0] + dx / L * gap, p[1] + dy / L * gap


def numogram_panel():
    d = doc()
    h = marks.Hand(d, random.Random(SEEDS[3]), amp=.25)
    labels, ring = [], 5.2
    centre = (120, 86)
    for z in ng.ZONES:
        x, y = zone_xy(z)
        h.ring(x, y, ring, "core")
        lx, ly = zone_xy(z, r=79)
        labels.append(text(lx, ly + 2.6, str(z), 8, "#252825", family="serif"))
    for lo, hi in ng.SYZYGIES:
        a, b = zone_xy(lo), zone_xy(hi)
        h.stroke([toward(a, b, ring), toward(b, a, ring)], "hair")
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        target = zone_xy(ng.current(lo))
        tip = toward(target, mid, ring + 1.5)
        bend = toward(mid, centre, 14) if ng.region(lo) == "time-circuit" else mid
        path = bezier(mid, bend, bend, tip, 30)
        h.stroke(path, "orn", "red")
        ang = math.degrees(math.atan2(tip[1] - path[-4][1], tip[0] - path[-4][0]))
        marks.arrowhead(h, tip, ang, 4.2, color="red", weight="orn")
    for z in ng.ZONES:
        g, dest = ng.channel(z)
        if dest == z:
            continue
        p, q = zone_xy(z), zone_xy(dest)
        out_p, out_q = zone_xy(z, r=86), zone_xy(dest, r=86)
        marks.dotted(h, bezier(toward(p, out_p, ring + 1), out_p, out_q, toward(q, out_q, ring + 1), 40), 2.4, .38)
    legend = [text(120, 176, "rungs: syzygies / red: currents / dotted: gate channels", 6.3)]
    return d.body(), labels + legend, dict(layout="circle, syzygies as horizontal rungs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "examples/out")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    panels = [aq_panel("ink"), aq_panel("grain"), table_panel(), numogram_panel()]
    titles = [("01 / AQ TO XENOTATION", "A phrase's AQ value as a prime glyph"),
              ("02 / CORNMEAL, OPEN ARCS", "Same glyph, grain hand, parens style"),
              ("03 / TIC XENOTATION 2-13", "':' is 2; (x) is the x-th prime"),
              ("04 / NUMOGRAM", "Currents and gates as plain arithmetic")]
    W, H = 692, 780
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="#eee7d6"/>',
           '<text x="38" y="49" font-family="serif" font-size="29" fill="#252825">Number systems</text>',
           '<text x="38" y="76" font-family="sans-serif" font-size="12" fill="#645b4b">lib/numerics drawn through the book\'s marks.Hand / fixed seeds</text>']
    for i, ((body, labels, _), (title, subtitle)) in enumerate(zip(panels, titles)):
        x, y = 35 + (i % 2) * 322, 106 + (i // 2) * 319
        svg += [f'<g transform="translate({x},{y})">',
                '<rect width="300" height="293" rx="2" fill="#f5f0e5" stroke="#c3b8a1" stroke-width=".7"/>',
                f'<text x="17" y="28" font-family="sans-serif" font-size="12" fill="#a32b24">{title}</text>',
                f'<g transform="translate(6,45) scale(1.2)">{body}{"".join(labels)}</g>',
                f'<text x="17" y="274" font-family="sans-serif" font-size="12" fill="#645b4b">{subtitle}</text>', '</g>']
    svg += [f'<text x="38" y="{H - 20}" font-family="sans-serif" font-size="11" fill="#645b4b">Josiah Alan-Lee / Generative Art / See techniques/09-number-systems for sources and limits</text>', '</svg>']
    target = args.out / "numerics-sampler.svg"
    target.write_text("\n".join(svg) + "\n")
    lib = ROOT / "lib/numerics"
    record = dict(book_commit=json.loads((ROOT / "catalog/source-manifest.json").read_text())["commit"],
                  example="Small demonstrations of lib/numerics through the book's Hand", seeds=SEEDS,
                  panels=[p[2] for p in panels],
                  svg_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  modules={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(lib.glob("*.py"))})
    (args.out / "numerics-manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    import cairosvg
    cairosvg.svg2png(url=str(target), write_to=str(target.with_suffix(".png")))
    print(target)


if __name__ == "__main__":
    main()
