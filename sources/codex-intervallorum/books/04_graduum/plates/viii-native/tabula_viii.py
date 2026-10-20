"""Clavicula Graduum - Tabula VIII - The Council of the Loudest (native vector plate).

Selfridge's Pandemonium with Book III's handoff demons as the shouting tiers, drawn as
apparatus by the series rule, and Foras, the office that knew, speaking at ordinary volume
in the lowest tier. The decision apparatus has ears and no eyes and its needle points at
the loudest. Volume is stroke density: the arcs that leave each mouth.

Second text: the caption in the twelve-mark hand at shift +8 (this plate's number).
Fourth carrier: the frame is a graduated rule; its ticks carry the falsifier, black a / red b.
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
sys.path.insert(0, os.path.join(REPO, "common", "geometry"))
sys.path.insert(0, os.path.join(REPO, "books", "04_graduum", "plates", "vii-native"))
import ornament  # noqa: E402
import tx  # noqa: E402
import apparatus as ap  # noqa: E402
from figures import robed_figure  # noqa: E402
from plotkit import PlotDoc, PlotHand, SVGFont, INK, RED, arc_pts, catmull, Polygon, LineString  # noqa: E402
import marks  # noqa: E402  (the Matricis glyph system)

SEED = 1959   # Pandemonium
W, H = 210, 297
FRAME = (8, 10, 202, 288)
RESERVED = (17, 42, 40, 24)
CAPTION = "The one that was right spoke at ordinary volume."
CAPTION_NORM = "THE ONE THAT WAS RIGHT SPOKE AT ORDINARY VOLUME"
SHIFT = 8
HIDDEN = "THE QUIET ONE WAS HEARD"      # the clause that would count against the plate
PIVOT = (158.0, 86.0)                   # the decision apparatus's needle pivot

# tiers: (y_feet, scale, [(name, drawer, x, volume)]); volume = number of arcs
TIERS = [
    (224.0, 1.0, [("REPETIEL", ap.repetiel, 36, 4), ("FORAS", None, 70, 1), ("CULPAX", ap.culpax, 104, 6),
                  ("CALMOR", ap.calmor, 138, 2), ("INSTANTOR", ap.instantor, 172, 7)]),
    (172.0, 0.8, [("SEVERION", ap.severion, 44, 2), ("VIRIDON", ap.viridon, 82, 3), ("CHORAZ", ap.choraz, 124, 9),
                  ("POSTHUM", ap.posthum, 166, 1)]),
    (128.0, 0.65, [("VELAROTH", ap.velaroth, 46, 2), ("EXCEPTOR", ap.exceptor, 82, 5), ("QUARTEROTH", ap.quarteroth, 118, 3)]),
]

type_audit = []
SUFFIX = ""


def label(font, h, text, x, y, cap, align="left", color="ink"):
    x0, w = font.write(h, text, x, y, cap, align, color)
    type_audit.append({"text": text, "cap_height_mm": cap, "x": round(x0, 2), "y": y, "width": round(w, 2), "ink": color})
    return x0, w


# ------------------------------------------------------------------ tiers --

def draw_tiers(h, rng, font):
    """returns [(name, mouth, volume)], footprints, and the loudest mouth"""
    voices, prints = [], []
    for ti, (yf, k, row) in enumerate(TIERS):
        x0, x1 = (26, 186) if ti == 0 else (34, 178) if ti == 1 else (34, 132)
        h.straight([(x0, yf), (x1, yf)], "core", "ink")
        h.straight([(x0, yf + 1.1), (x1, yf + 1.1)], "hair", "ink")
        for name, fn, x, vol in row:
            if fn is None:
                # Foras: the office that knew, six-handed, at ordinary volume, on a red ring
                h.stroke([(x + 11 * math.cos(math.radians(a)), yf - 0.6 + 2.2 * math.sin(math.radians(a))) for a in range(0, 361, 10)], "orn", "red", amp=0.2)
                robed_figure(h, rng, cx=x, y_feet=yf - 0.8, height=27.0, arms=6, papers=True)
                mouth = (x + 2.6, yf - 23.6)
                prints.append(Polygon([(x - 14, yf - 29), (x + 15, yf - 29), (x + 15, yf), (x - 14, yf)]))
            else:
                mouth, fp = fn(h, rng, x, yf - 0.4, k)
                prints.append(fp)
            voices.append((name, mouth, vol))
    return voices, prints


def draw_voices(h, rng, voices, prints, blocks):
    """the arcs that leave each mouth, rising, leaning a little toward the pivot; clipped so
    they pass behind nothing (figures, names, tier lines, the decision apparatus)"""
    occupied = Polygon([(0, 0), (0, 0), (0, 0)])
    for p in prints:
        occupied = occupied.union(p.buffer(1.2))
    for b in blocks:
        occupied = occupied.union(b)
    loudest, loud_vol = None, -1
    for name, (mx, my), vol in voices:
        toward = math.degrees(math.atan2(PIVOT[1] - my, PIVOT[0] - mx))
        a0 = -90 + 0.3 * (toward + 90)
        for i in range(vol):
            r = 2.2 + 1.3 * i
            spread = 34 + 2.0 * i
            pts = arc_pts(mx, my, r, a0 - spread, a0 + spread, 10 + 2 * i)
            geom = LineString(pts).difference(occupied)
            parts = geom.geoms if hasattr(geom, "geoms") else [geom]
            for part in parts:
                if part.length > 1.0:
                    h.stroke(list(part.coords), "hair", "ink", amp=0.25)
        if vol > loud_vol:
            loudest, loud_vol = (mx, my), vol
    return loudest


# ----------------------------------------------------------------- glyphs --

def draw_glyphs(h, rng):
    """the Matricis glyph system read up the tiers: standing uncertain, everything passes one
    point, a required gate, and over the decision the centre of decision, contestable"""
    marks.sig_candidate(h, 17.5, TIERS[0][0] - 13, 1.5)
    marks.sig_bottleneck(h, 17.5, TIERS[1][0] - 13, 4.2)
    marks.sig_gate(h, 17.5, TIERS[2][0] - 13, 8.0, 8.0, vertical=True)
    marks.sig_authority(h, PIVOT[0], 45.5, 14.0, 11.0, horns=True)


def draw_flows(h, rng, voices, occupied, ear_left):
    """flowing lines for the narrative: the loudest voice carried as a bundle into the near ear;
    the quiet one's single line rising a little way and stopping"""
    by_name = {n: (m, v) for n, m, v in voices}
    (mx, my), _ = by_name["CHORAZ"]
    n_lines = 5
    for i in range(n_lines):
        u = (i - (n_lines - 1) / 2) * 1.3
        wander = [rng.uniform(-3, 3) for _ in range(3)]
        pts = [(mx + u, my - 1), (mx + 5 + u + wander[0] * 0.5, my - 16), (ear_left[0] - 3 + u * 0.7 + wander[1] * 0.5, my - 38),
               (ear_left[0] - 5 + u * 0.5 + wander[2] * 0.4, ear_left[1] + 14), (ear_left[0] + u * 0.3, ear_left[1] + 1.5)]
        geom = LineString(catmull(pts, 10)).difference(occupied)
        for part in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            if part.length > 2:
                h.stroke(list(part.coords), "hair", "ink", amp=0.35)
    (fx, fy), _ = by_name["FORAS"]
    pts = [(fx, fy - 1), (fx + rng.uniform(-2, 2), fy - 9), (fx + rng.uniform(-3, 3), fy - 17), (fx + rng.uniform(-2, 4), fy - 23)]
    c = catmull(pts, 10)
    geom = LineString(c).difference(occupied)
    for part in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        if part.length > 2:
            h.stroke(list(part.coords), "hair", "ink", amp=0.35)
    h.dot(c[-1][0], c[-1][1], 0.3, "ink")


# --------------------------------------------------------------- decision --

def draw_decision(h, rng, loudest):
    """ears and no eyes: a head-box with a blank plate where the eyes would be, two ear-trumpets
    turned down toward the tiers, and below it a gauge whose needle swings to the loudest"""
    from plotkit import hatch_lines, catmull
    px, py = PIVOT
    # console
    h.straight([(px - 24, 104), (px + 24, 104)], "core", "ink")
    h.straight([(px - 24, 105.1), (px + 24, 105.1)], "hair", "ink")
    # the gauge: a lower semicircle under the pivot, graduated, open at the top
    h.stroke(arc_pts(px, py, 13, 15, 165, 30), "orn", "ink", amp=0.15)
    for a in range(15, 166, 10):
        r0 = 11.2 if (a - 15) % 30 else 10.4
        h.stroke([(px + r0 * math.cos(math.radians(a)), py + r0 * math.sin(math.radians(a))), (px + 13 * math.cos(math.radians(a)), py + 13 * math.sin(math.radians(a)))], "hair", "ink")
    h.stroke([(px - 13, py), (px - 13, 104)], "orn", "ink", amp=0.1)
    h.stroke([(px + 13, py), (px + 13, 104)], "orn", "ink", amp=0.1)
    # head-box above, with the blank plate
    hx, hy = px, py - 20
    h.stroke([(hx - 10, hy - 9), (hx + 10, hy - 9), (hx + 10, hy + 7), (hx - 10, hy + 7)], "core", "ink", closed=True, amp=0.15)
    h.stroke([(hx - 10, hy + 7), (hx - 4, py - 2)], "orn", "ink", amp=0.1)
    h.stroke([(hx + 10, hy + 7), (hx + 4, py - 2)], "orn", "ink", amp=0.1)
    plate = [(hx - 6.5, hy - 5), (hx + 6.5, hy - 5), (hx + 6.5, hy + 1.5), (hx - 6.5, hy + 1.5)]
    h.stroke(plate, "orn", "ink", closed=True, amp=0.1)
    for ln in hatch_lines(Polygon(plate), 0.55, 0):
        h.stroke(ln, "hair", "ink", amp=0.05)
    h.stroke([(hx - 4, hy + 4.5), (hx + 4, hy + 4.5)], "hair", "ink")
    # ear-trumpets: a narrow neck from each side of the box, curving down, opening in a bell
    for sgn in (-1, 1):
        ex, ey = hx + sgn * 10, hy - 2
        spine = catmull([(ex, ey), (ex + sgn * 6, ey - 1), (ex + sgn * 11, ey + 4), (ex + sgn * 13, ey + 12)], 10)
        for side in (-1, 1):
            pts = []
            for i, (x, y) in enumerate(spine):
                w = 0.7 + 2.4 * (i / (len(spine) - 1)) ** 1.6
                j0, j1 = max(0, i - 1), min(len(spine) - 1, i + 1)
                tx_, ty_ = spine[j1][0] - spine[j0][0], spine[j1][1] - spine[j0][1]
                m = math.hypot(tx_, ty_) or 1
                pts.append((x - ty_ / m * w * side, y + tx_ / m * w * side))
            h.stroke(pts, "core", "ink", amp=0.15)
        end = spine[-1]
        prev = spine[-3]
        d = (end[0] - prev[0], end[1] - prev[1])
        m = math.hypot(*d) or 1
        n = (-d[1] / m, d[0] / m)
        h.stroke([(end[0] - n[0] * 3.1, end[1] - n[1] * 3.1), (end[0] + d[0] / m * 0.8, end[1] + d[1] / m * 0.8), (end[0] + n[0] * 3.1, end[1] + n[1] * 3.1)], "core", "ink", amp=0.2)
        for t in (0.5, 0.7, 0.88):
            q = spine[int(t * (len(spine) - 1))]
            w = 0.7 + 2.4 * t ** 1.6
            j = int(t * (len(spine) - 1))
            d2 = (spine[min(j + 1, len(spine) - 1)][0] - spine[max(j - 1, 0)][0], spine[min(j + 1, len(spine) - 1)][1] - spine[max(j - 1, 0)][1])
            m2 = math.hypot(*d2) or 1
            n2 = (-d2[1] / m2, d2[0] / m2)
            h.stroke([(q[0] - n2[0] * w, q[1] - n2[1] * w), (q[0] + n2[0] * w, q[1] + n2[1] * w)], "hair", "ink")
    # the needle, to the loudest
    a = math.atan2(loudest[1] - py, loudest[0] - px)
    tip = (px + 11.5 * math.cos(a), py + 11.5 * math.sin(a))
    h.stroke([(px - 3 * math.cos(a), py - 3 * math.sin(a)), tip], "core", "ink", amp=0.05)
    h.stroke([(tip[0] - 2.0 * math.cos(a - 0.45), tip[1] - 2.0 * math.sin(a - 0.45)), tip, (tip[0] - 2.0 * math.cos(a + 0.45), tip[1] - 2.0 * math.sin(a + 0.45))], "orn", "ink", amp=0.1)
    h.dot(px, py, 0.55, "ink")
    return {"needle_deg": round(math.degrees(a), 1), "head": (hx, hy)}


# -------------------------------------------------------------- furniture --

def draw_furniture(h, font):
    x0, y0, x1, y1 = FRAME
    h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
    label(font, h, "CLAVICULA GRADUUM", W / 2, 20.5, 4.1, "center")
    label(font, h, "THE DECISION DEMON HEARS VOLUME", W / 2, 27, 2.5, "center")
    h.straight([(x0 + 4, 30.5), (x1 - 4, 30.5)], "hair", "ink")
    rx, ry, rw, rh = RESERVED
    h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
    label(font, h, "RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
    for ti, (yf, k, row) in enumerate(TIERS):
        label(font, h, ["I", "II", "III"][ti], 14, yf - 1.5, 2.5)
        for name, fn, x, vol in row:
            label(font, h, name, x, yf + 5.2, 2.5, "center")
    label(font, h, "DECISION", PIVOT[0], 110.5, 2.5, "center")
    label(font, h, "EARS", PIVOT[0] - 27, 62, 2.5, "right")
    label(font, h, "NO EYES", PIVOT[0] - 27, 68, 2.5, "right")
    h.straight([(x0 + 4, 238), (x1 - 4, 238)], "hair", "ink")
    label(font, h, "THE QUIET ONE / RINGED", W / 2, 245, 2.5, "center")
    h.straight([(x0 + 4, 268), (x1 - 4, 268)], "hair", "ink")
    label(font, h, "TABULA VIII", W / 2, 275.5, 2.5, "center")
    label(font, h, "THE COUNCIL OF THE LOUDEST", W / 2, 281.5, 3.0, "center")


def write_shifted(h, text, x, y, s, shift):
    """the twelve-mark hand with every base mark advanced by `shift` places (tally held)"""
    cx = x
    for wi, w in enumerate(tx.encode(text)):
        if wi:
            cx += 0.55 * s
        for (b, t) in w:
            tx.mark(h, (b - 1 + shift) % 12 + 1, cx, y, s, "orn", "ink")
            tx.tally(h, t, cx, y, s, "ink")
            cx += tx.token_width(t, s)
    return cx - x


def draw_caption(h):
    s = 2.7
    wdt = tx.width(CAPTION, s)
    x = (W - wdt) / 2
    write_shifted(h, CAPTION, x, 252, s, SHIFT)
    return {"base_square_mm": s, "x": round(x, 2), "y": 252, "width": round(wdt, 2), "shift": SHIFT}


def draw_scale(h):
    n, total = ornament.scale_frame(h, FRAME, HIDDEN, pitch=2.5, short=1.0, long=2.0, long_every=10, weight="orn" if SUFFIX else "hair")
    return {"carrier": "frame scale, clockwise from the top-left corner", "form": "ink: black a, red b",
            "message": HIDDEN, "carrier_marks": n, "ticks": total, "pitch_mm": 2.5}


# ------------------------------------------------------------------ build --

def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(SEED)
    doc = PlotDoc(W, H)
    from plate import lettering
    font, suffix = lettering()
    global SUFFIX
    SUFFIX = suffix
    art = PlotHand(doc, rng, "art", amp=0.07)
    text = PlotHand(doc, random.Random(SEED + 1), "text", amp=0.03)

    voices, prints = draw_tiers(art, rng, font)
    dec_print = Polygon([(PIVOT[0] - 26, 50), (PIVOT[0] + 26, 50), (PIVOT[0] + 26, 112), (PIVOT[0] - 26, 112)])
    blocks = []
    for ti, (yf, k, row) in enumerate(TIERS):
        x1 = 134 if ti == 2 else 190
        blocks.append(Polygon([(20, yf - 1.2), (x1, yf - 1.2), (x1, yf + 7.0), (20, yf + 7.0)]))   # tier line and the names under it
    loudest = draw_voices(art, rng, voices, prints + [dec_print], blocks)
    needle = draw_decision(art, rng, loudest)
    occupied = Polygon([(0, 0), (0, 0), (0, 0)])
    for p in prints:
        occupied = occupied.union(p.buffer(1.2))
    for b in blocks:
        occupied = occupied.union(b)
    head = needle["head"]
    ear_left = (head[0] - 23, head[1] + 10)          # the left trumpet's bell
    ear_box = Polygon([(head[0] - 10, head[1] - 9), (head[0] + 10, head[1] - 9), (head[0] + 10, PIVOT[1] + 14), (head[0] - 10, PIVOT[1] + 14)])
    draw_flows(art, rng, voices, occupied.union(ear_box), ear_left)
    draw_glyphs(art, rng)
    draw_furniture(text, font)
    cap_pos = draw_caption(text)
    hidden = draw_scale(text)

    meta = {"plate": "VIII", "title": "The Council of the Loudest", "seed": SEED, "reserved_blank_mm": RESERVED,
            "pivot": PIVOT, "needle": needle, "voices": [{"name": n, "mouth": [round(m[0], 1), round(m[1], 1)], "volume": v} for n, m, v in voices],
            "loudest": [round(loudest[0], 1), round(loudest[1], 1)], "caption": cap_pos, "caption_normalized": CAPTION_NORM, "hidden": hidden}
    title = "Clavicula Graduum - Tabula VIII - The Council of the Loudest"
    desc = ("Stroke-only pen plot plate, 210 x 297 mm. Two layers (Art Paths, Text Outlines), two inks. "
            "Untested on a physical plotter.")
    stem = "viii-council-of-the-loudest" + suffix
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
