"""Clavicula Graduum - Tabula V, The Dial of Seven Keepers. Native vector edition.

The Keeper is drawn, not traced: control curves dressed in the Matricis stroke
vocabulary (flow-lines, cellular net, coils, hatched rules). Stroke-only, A4,
two layers, two inks.
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
import ornament  # noqa: E402
from plotkit import (PlotDoc, PlotHand, SVGFont, INK, RED, roman_year_angles, bezier, arc_pts, lerp,  # noqa: E402
                     Polygon, LineString, Point)
from figure import draw_keeper, clip_polyline  # noqa: E402
import tx  # noqa: E402

SEED = 1508   # De septem secundeis
W, H = 210, 297
FRAME = (8, 10, 202, 288)
CAPTION = "Count III M I Y II Y V Y X Y XX Y L Y."
CAPTION_NORM = "COUNT III M I Y II Y V Y X Y XX Y L Y"
RESERVED = (17, 42, 40, 24)
HIDDEN = "NO SLOWER AT THE TOP"   # D6 falsifier; carried by the ground blades, a = no head, b = dot head
JAQUES = [(0.25, "III M", "3M"), (1, "I Y", "1Y"), (2, "II Y", "2Y"), (5, "V Y", "5Y"), (10, "X Y", "10Y"),
          (20, "XX Y", "20Y"), (50, "L Y", "50Y")]
DIAL = (113.5, 126.5, 12.6)          # cx, cy, outer radius: worn on the chest where the ring was
BARS_Y = [113, 127, 141, 155, 169, 183, 197]
CHEST_RING = (113.5, 126.5, 12.6)    # the dial occupies the ring's place
GROUND_Y = 221

type_audit = []


def label(font, h, text, x, y, cap, align="left", color="ink"):
    x0, w = font.write(h, text, x, y, cap, align, color)
    type_audit.append({"text": text, "cap_height_mm": cap, "x": round(x0, 2), "y": y, "width": round(w, 2), "ink": color})
    return x0, w


# -------------------------------------------------------------------- dial --

def draw_dial(h, rng, font, occluder):
    """the dial sits behind the hood; every stroke is clipped against the figure"""
    cx, cy, R = DIAL
    a0, a1 = -90, 250
    band_in = R - 2.9
    free = Polygon([(0, 0), (210, 0), (210, 297), (0, 297)]).difference(occluder)

    def S(pts, weight, color, amp=0.2, straight=False):
        for seg in clip_polyline(pts, free):
            if straight:
                h.straight(seg, weight, color)
            else:
                h.stroke(seg, weight, color, amp=amp)

    S(arc_pts(cx, cy, R, 0, 360, 200), "core", "ink")
    S(arc_pts(cx, cy, band_in, 0, 360, 180), "orn", "ink")
    vals = [v for v, _, _ in JAQUES]
    angs = roman_year_angles(vals, 0.25, 50, a0, a1)
    for (v, _, lab), a in zip(JAQUES, angs):
        ar = math.radians(a)
        S([(cx + band_in * math.cos(ar), cy + band_in * math.sin(ar)), (cx + (R + 0.9) * math.cos(ar), cy + (R + 0.9) * math.sin(ar))],
          "orn", "ink", straight=True)
    # the boundaries are not lettered on the chest: the left register names them in order
    for v in (0.5, 3, 4, 6, 7, 8, 9, 15, 30, 40):
        ar = math.radians(roman_year_angles([v], 0.25, 50, a0, a1)[0])
        S([(cx + band_in * math.cos(ar), cy + band_in * math.sin(ar)), (cx + (band_in + 1.0) * math.cos(ar), cy + (band_in + 1.0) * math.sin(ar))],
          "hair", "ink", straight=True)
    for a in (a0 - 8, a1 + 8):   # the open twenty degrees
        ar = math.radians(a)
        p = (cx + (R - 1.4) * math.cos(ar), cy + (R - 1.4) * math.sin(ar))
        if free.contains(Point(p)):
            h.dot(p[0], p[1], 0.3, "ink")

    r_in = R - 5.4
    S(arc_pts(cx, cy, r_in, 0, 360, 120), "orn", "ink")
    for k in range(7):
        ar = math.radians(-90 + k * 360 / 7)
        p = (cx + r_in * math.cos(ar), cy + r_in * math.sin(ar))
        S(arc_pts(p[0], p[1], 0.7, 0, 360, 20), "orn", "ink")
    phases = [rng.uniform(0, 6.283) for _ in range(7)]
    t = 0.37
    for k, (v, _, _) in enumerate(JAQUES):
        ang = phases[k] + 6.283 * t / v
        L = 2.6 + k * 0.62
        p = (cx + L * math.cos(ang), cy + L * math.sin(ang))
        col = "red" if k == 3 else "ink"
        S([(cx, cy), p], "orn" if col == "ink" else "core", col, straight=True)
        if free.contains(Point(p)):
            h.dot(p[0], p[1], 0.3, col)
    S(arc_pts(cx, cy, 0.9, 0, 360, 20), "core", "ink")
    return phases


# ------------------------------------------------------------------ ground --

def draw_ground(h, rng):
    """the ground: blades left to right. Each blade is one mark of the fourth carrier:
    a dot head is the b form, none the a form; red is decoration and carries nothing."""
    y0 = GROUND_Y
    h.straight([(26, y0), (186, y0)], "core", "ink")
    h.straight([(26, y0 + 1.2), (186, y0 + 1.2)], "hair", "ink")
    bl = ornament.bits(HIDDEN)
    x, i = 27.0, 0
    while x < 185:
        env = 2.2 + 8.5 * math.exp(-((x - 114) / 24) ** 2) + 3.5 * math.exp(-((x - 58) / 13) ** 2) + 3.0 * math.exp(-((x - 168) / 11) ** 2)
        ht = max(0.8, rng.gauss(env, env * 0.35))
        col = "red" if rng.random() < 0.06 else "ink"
        h.stroke([(x, y0 - 0.3), (x, y0 - ht)], "hair", col, amp=0.3, attrs=f' data-blade="{i}"')
        head = bl[i] if i < len(bl) else (1 if rng.random() < 0.3 else 0)
        if head:
            h.dot(x, y0 - ht - 0.45, 0.3 if col == "ink" else 0.36, col)
            h.pdoc.layers[h.layer][-1] = h.pdoc.layers[h.layer][-1][:3] + (f' data-head="{i}"',)
        if rng.random() < 0.18:
            h.straight([(x, y0 + 1.6), (x, y0 + 1.6 + rng.uniform(0.6, 2.4))], "hair", "ink")
        x += rng.uniform(0.9, 1.9)
        i += 1
    h.straight([(26, y0 + 4.4), (186, y0 + 4.4)], "hair", "ink")
    if len(bl) > i:
        raise ValueError(f"message needs {len(bl)} blades, ground has {i}")
    return {"carrier": "ground blades, left to right", "form": "dot head = b, none = a; ink carries nothing",
            "message": HIDDEN, "carrier_marks": len(bl), "blades": i}


# -------------------------------------------------------------------- cord --

def draw_cord(h, pinch, bars):
    cx, cy, cr = CHEST_RING
    start = (cx + (cr + 0.3) * math.cos(math.radians(318)), cy + (cr + 0.3) * math.sin(math.radians(318)))
    th = bezier(start, (128, 112), (140, 100), pinch, 40)
    h.stroke(th, "orn", "red", amp=0.3)
    x_cord, y_top, y_bot = pinch[0] + 0.4, pinch[1], GROUND_Y - 1.6
    h.straight([(x_cord, y_top), (x_cord, y_bot)], "orn", "red")
    for k in range(5):
        y = y_top + (y_bot - y_top) * (k + 1) / 6
        h.dot(x_cord, y, 0.55, "red")
    loop = arc_pts(x_cord + 1.7, y_bot + 0.1, 1.8, 180, 520, 30)
    h.stroke(loop, "orn", "red", amp=0.2)
    # the fourth interval is read against the cord: a dashed red rule from the bar's end to the cord
    x0, x1, y = bars[3]
    xx = x1 + 1.8
    while xx < x_cord - 1.0:
        h.straight([(xx, y), (min(xx + 1.6, x_cord - 1.0), y)], "hair", "red")
        xx += 2.8
    h.straight([(x_cord - 1.4, y - 1.4), (x_cord - 1.4, y + 1.4)], "orn", "red")
    return x_cord


# --------------------------------------------------------------- furniture --

def draw_furniture(h, font):
    x0, y0, x1, y1 = FRAME
    h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
    label(font, h, "CLAVICULA GRADUUM", W / 2, 20.5, 4.1, "center")
    label(font, h, "TWO SCALES / NO ALIGNMENT IMPOSED", W / 2, 27, 2.5, "center")
    h.straight([(x0 + 4, 30.5), (x1 - 4, 30.5)], "hair", "ink")
    rx, ry, rw, rh = RESERVED
    h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
    label(font, h, "RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
    label(font, h, "JAQUES", 18, 96, 2.5)
    for i, (_, lab, _) in enumerate(JAQUES):
        label(font, h, lab, 18, 108 + i * 12.5, 2.5)
    label(font, h, "REIGN", 194, 134, 2.5, "right")
    label(font, h, "354 Y", 194, 146, 2.5, "right")
    label(font, h, "04 M", 194, 158, 2.5, "right")
    label(font, h, "EACH", 194, 170, 2.5, "right")
    h.straight([(x0 + 4, 232), (x1 - 4, 232)], "hair", "ink")
    label(font, h, "BOUNDARIES / ROMAN NUMERALS", W / 2, 240, 2.5, "center")
    h.straight([(x0 + 4, 268), (x1 - 4, 268)], "hair", "ink")
    label(font, h, "TABULA V", W / 2, 275.5, 2.5, "center")
    label(font, h, "THE DIAL OF SEVEN KEEPERS", W / 2, 281.5, 3.0, "center")


def draw_caption(h):
    s = 2.8
    wdt = tx.width(CAPTION, s)
    x = (W - wdt) / 2
    tx.write(h, CAPTION, x, 248, s)
    return {"base_square_mm": s, "x": round(x, 2), "y": 248, "width": round(wdt, 2)}


# -------------------------------------------------------------------- build --

def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(SEED)
    doc = PlotDoc(W, H)
    from plate import lettering
    font, suffix = lettering()
    art = PlotHand(doc, rng, "art", amp=0.07)
    text = PlotHand(doc, random.Random(SEED + 1), "text", amp=0.03)

    from figure import robe_outline, edge_fn
    robe = Polygon(robe_outline()).buffer(0)
    bars = []
    for i, y in enumerate(BARS_Y):
        b, f = edge_fn(robe, y, "back"), edge_fn(robe, y, "front")
        ov = 4.5 + 3.0 * (0.5 + 0.5 * math.sin(i * 2.1))
        bars.append((b - ov, f + ov, y))

    pinch, occluder = draw_keeper(art, rng, BARS_Y, CHEST_RING, None)
    phases = draw_dial(art, rng, font, occluder)
    hidden = draw_ground(art, rng)
    x_cord = draw_cord(art, pinch, bars)
    draw_furniture(text, font)
    cap_pos = draw_caption(text)

    meta = {"plate": "V", "title": "The Dial of Seven Keepers", "seed": SEED, "dial": DIAL, "hand_phases": phases,
            "bars_y": BARS_Y, "chest_ring": CHEST_RING, "cord_x": round(x_cord, 2), "caption": cap_pos,
            "reserved_blank_mm": RESERVED, "hidden": hidden}
    title = "Clavicula Graduum - Tabula V - The Dial of Seven Keepers"
    desc = ("Stroke-only pen plot plate, 210 x 297 mm. Two layers (Art Paths, Text Outlines), two inks. "
            "Untested on a physical plotter.")
    stem = "v-dial-of-seven-keepers" + suffix
    files = {
        f"{stem}.svg": doc.svg(("art", "text"), (INK, RED), title, desc),
        f"{stem}-black-a4.svg": doc.svg(("art", "text"), (INK,), title + " - black pass", desc),
        f"{stem}-red-a4.svg": doc.svg(("art", "text"), (RED,), title + " - red pass", desc),
        f"{stem}-art-only.svg": doc.svg(("art",), (INK, RED), title + " - art layer", desc),
        f"{stem}-text-only.svg": doc.svg(("text",), (INK, RED), title + " - text layer", desc),
    }
    for name, s in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(s)
    with open(os.path.join(out_dir, f"{stem}-type-audit.json"), "w") as f:
        json.dump({"plate": type_audit, "minimum_cap_mm": min(t["cap_height_mm"] for t in type_audit),
                   "cipher_base_square_mm": cap_pos["base_square_mm"]}, f, indent=1)
    meta["stem"] = stem
    with open(os.path.join(out_dir, "build-meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    from plate import png_preview
    png_preview(os.path.join(out_dir, f"{stem}.svg"), os.path.join(out_dir, f"{stem}.png"))
    return doc, meta


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    doc, meta = build(out)
    print("strokes:", len(doc.strokes()), "art:", len(doc.strokes("art")), "text:", len(doc.strokes("text")))
