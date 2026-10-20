"""Clavicula Graduum - Tabula VII, The Cord Without a Mount. Native vector edition.

The Escalationum building in section: seven floors, each with its office's own
seal imported as strokes from Book III, the black route offered between them,
and one red cord that runs from the floor of hands to the roof touching no
office, where it ends under an empty bracket. Stroke-only, A4, two layers,
two inks. The second text is the office litany down registers A and B.
"""
import csv
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
from plotkit import (PlotDoc, PlotHand, SVGFont, INK, RED, catmull, bezier, arc_pts, lerp, dist,  # noqa: E402
                     Polygon, LineString, Point, voronoi_net)
from svgimport import strokes_from_svg, place  # noqa: E402
from figures import robed_figure, hand_up  # noqa: E402

SEED = 1606   # the year the Steganographia was printed with its key
W, H = 210, 297
FRAME = (8, 10, 202, 288)
RESERVED = (17, 42, 40, 24)
CAPTION = "The cord is sound. The mount was never made."
CAPTION_NORM = "THE CORD IS SOUND THE MOUNT WAS NEVER MADE"
HIDDEN = "THE UNEXPOSED ANSWER NO SLOWER"   # D7 falsifier; carried by the frame scale, black a / red b
SEALS_DIR = os.path.join(REPO, "books", "03_escalationum", "output", "plates")
LITANY_CSV = os.path.join(REPO, "books", "04_graduum", "proofs", "x-xi-v-gpt", "office-litany.csv")
CATALOGUE = os.path.join(REPO, "books", "03_escalationum", "manuscript", "catalogue.json")

# the building
BX0, BX1 = 52, 158            # outer walls
WALL = 2.4
GROUND = 232.0
FLOOR_H = 22.0
SLAB = 1.4
SHAFT = (147.0, 153.0)        # the cord's shaft inside the right wall zone
CORD_X = 150.0

type_audit = []
SUFFIX = ""


def label(font, h, text, x, y, cap, align="left", color="ink"):
    x0, w = font.write(h, text, x, y, cap, align, color)
    type_audit.append({"text": text, "cap_height_mm": cap, "x": round(x0, 2), "y": y, "width": round(w, 2), "ink": color})
    return x0, w


def litany_table():
    t = {}
    for r in csv.DictReader(open(LITANY_CSV, encoding="utf-8")):
        t[r["plaintext"]] = r["carrier_word"]
    return t


def encode_litany(text, table):
    return [table["SPACE"] if ch == " " else table[ch] for ch in text]


# ---------------------------------------------------------------- building --

def floor_y(i):
    """top surface of floor i's slab (i = 0 ground ... 6 top), and the ceiling slab above it"""
    y_floor = GROUND - i * FLOOR_H
    return y_floor, y_floor - FLOOR_H


def hatch_band(h, poly, step=0.7, ang=45):
    from plotkit import hatch_lines
    for ln in hatch_lines(poly, step, ang):
        h.straight(ln, "hair", "ink")


def draw_building(h, rng, font, tiers):
    x0, x1 = BX0, BX1
    roof_top = floor_y(6)[1]
    # walls as poché (hatched section), the shaft left open through the right wall zone
    left_wall = Polygon([(x0, GROUND + 1.4), (x0 + WALL, GROUND + 1.4), (x0 + WALL, roof_top), (x0, roof_top)])
    right_wall = Polygon([(x1 - WALL, GROUND + 1.4), (x1, GROUND + 1.4), (x1, roof_top), (x1 - WALL, roof_top)])
    for wpoly in (left_wall, right_wall):
        h.straight(list(wpoly.exterior.coords), "core", "ink")
        hatch_band(h, wpoly.buffer(-0.25))
    # slabs: double rules from wall to wall, broken at the shaft
    for i in range(8):
        y = GROUND - i * FLOOR_H
        for xa, xb in ((x0 + WALL, SHAFT[0] - 0.6), (SHAFT[1] + 0.6, x1 - WALL)):
            h.straight([(xa, y), (xb, y)], "core", "ink")
            h.straight([(xa, y - SLAB), (xb, y - SLAB)], "hair", "ink")
            if i < 7:
                hatch_band(h, Polygon([(xa, y - SLAB), (xb, y - SLAB), (xb, y), (xa, y)]).buffer(-0.15), step=0.55, ang=60)
    # shaft: two hairlines the full height, with the slabs' broken ends ticked
    for xs in SHAFT:
        h.straight([(xs, GROUND), (xs, roof_top - SLAB)], "hair", "ink")
    # ground line under the building
    h.straight([(x0 - 14, GROUND + 1.4), (x1 + 14, GROUND + 1.4)], "core", "ink")
    h.straight([(x0 - 14, GROUND + 2.6), (x1 + 14, GROUND + 2.6)], "hair", "ink")

    # floors: numeral, region, the office seal, and the route offered
    seal_pos = {}
    for i, t in enumerate(tiers):
        yf, yc = floor_y(i)
        label(font, h, str(i), x0 + WALL + 2.2, yf - 2.2, 3.0)
        # the region is written under the ceiling, on the seal's side, clear of the stair
        if i % 2 == 0:
            label(font, h, t["region"].upper(), x0 + WALL + (6.5 if i == 0 else 2.2), yc + SLAB + 3.4, 2.5)
        else:
            label(font, h, t["region"].upper(), SHAFT[0] - 3.0, yc + SLAB + 3.4, 2.5, "right")
        # seal, imported from Book III as black strokes only
        seal_file = os.path.join(SEALS_DIR, f"office-seal-{i}.svg")
        polys = [pl for col, w, pl in strokes_from_svg(seal_file, colors=("#201d19",))]
        # the seal proper sits in the upper 300x300 of the 300x330 source (the red strip is below it)
        polys = [pl for pl in polys if max(y for _, y in pl) < 270]
        cx = x0 + WALL + 20 if i % 2 == 0 else x1 - WALL - 28
        if i == 0:
            cx = 100.0                      # the floor of hands: seal in the middle, Foras at the shaft side
        cy = (yf + yc) / 2 + 0.6
        for pl in place(polys, (59, 54, 182, 182), (cx, cy), 11.5):
            h.stroke(pl, "orn", "ink", amp=0.15)
        seal_pos[i] = (cx, cy)
        # a desk: a small lattice-filled block on the other side (the ground floor has none: Foras is the desk)
        if i in (0, 6):                 # the top floor has only the chair
            continue
        dx = x1 - WALL - 30 if i % 2 == 0 else x0 + WALL + 12
        desk = Polygon([(dx, yf - 1.6), (dx + 16, yf - 1.6), (dx + 16, yf - 6.2), (dx, yf - 6.2)])
        h.straight(list(desk.exterior.coords), "orn", "ink")
        hatch_band(h, desk.buffer(-0.3), step=0.9, ang=45)
        hatch_band(h, desk.buffer(-0.3), step=0.9, ang=-45)
    # the route offered: a black stair from each desk up the wall side to the floor above
    for i in range(6):
        yf, yc = floor_y(i)
        if i == 0:
            xa, xb, ya = x0 + WALL + 18, x0 + WALL + 2.5, yf          # from the floor itself, up the left wall
        elif i % 2 == 0:
            xa, xb, ya = x1 - WALL - 30, SHAFT[0] - 2.5, yf - 6.2
        else:
            xa, xb, ya = x0 + WALL + 28, x0 + WALL + 2.5, yf - 6.2
        n = 9
        pts = [(xa, ya)]
        for k in range(1, n + 1):
            tt = k / n
            pts.append((xa + (xb - xa) * tt, ya - (ya - (yc + SLAB)) * tt))
        for k in range(n):
            a, b = pts[k], pts[k + 1]
            h.straight([a, (b[0], a[1])], "orn", "ink")
            h.straight([(b[0], a[1]), b], "orn", "ink")
        h.straight([pts[0], pts[-1]], "hair", "ink")
    return seal_pos


def draw_top_floor(h, rng, font):
    """Bael's chamber: the empty chair, and above the roof the bracket with nothing in it"""
    yf, yc = floor_y(6)
    # the chair, in section, lattice-built, facing the shaft
    cx, cy = BX1 - WALL - 22, yf - 1.6
    seat = [(cx - 7, cy - 7.5), (cx + 7, cy - 7.5), (cx + 7, cy - 9.5), (cx - 7, cy - 9.5)]
    back = [(cx - 7.5, cy - 9.5), (cx - 5.5, cy - 9.5), (cx - 5.0, cy - 20), (cx - 7.6, cy - 20)]
    for poly in (seat, back):
        h.stroke(poly, "orn", "ink", closed=True, amp=0.2)
        hatch_band(h, Polygon(poly).buffer(-0.3), step=0.8, ang=45)
    for lx in (cx - 6, cx + 6):
        h.straight([(lx, cy - 7.5), (lx, cy)], "orn", "ink")
        h.dot(lx, cy + 0.3, 0.3, "ink")
    # roof slab is the top slab already drawn; the bracket stands on the roof line above the shaft
    roof = floor_y(6)[1] - SLAB
    bx, by = CORD_X, roof - 7.0
    # wall plate with two bolt coils, and an open hook that holds nothing
    h.straight([(bx - 5, by + 2.2), (bx + 5, by + 2.2), (bx + 5, by - 0.6), (bx - 5, by - 0.6)], "core", "ink", closed=True)
    h.dot(bx - 3.4, by + 0.8, 0.45, "ink")
    h.dot(bx + 3.4, by + 0.8, 0.45, "ink")
    h.straight([(bx, by - 0.6), (bx, by - 3.2)], "core", "ink")
    h.stroke(arc_pts(bx + 1.6, by - 3.2, 1.6, 180, 360, 20), "core", "ink", amp=0.1)
    h.straight([(bx + 3.2, by - 3.2), (bx + 3.2, by - 1.9)], "core", "ink")
    # two posts from the roof to the plate
    for px in (bx - 4.2, bx + 4.2):
        h.straight([(px, roof), (px, by + 2.2)], "hair", "ink")
    return (bx, by)


def draw_cord(h, hand_pt, bracket):
    """the red cord: from Foras's raised hand into the shaft and up to just under the hook"""
    bx, by = bracket
    hx, hy = hand_pt
    # from the hand to the shaft entrance, then straight up
    entry = (CORD_X, hy - 2.0)
    h.stroke(bezier((hx, hy), (hx + 3, hy - 3), (CORD_X - 2, hy - 1), entry, 24), "core", "red", amp=0.2)
    top = by + 6.0   # the knot stops short of the hook
    h.straight([(CORD_X, entry[1]), (CORD_X, top)], "core", "red")
    h.dot(CORD_X, top - 0.3, 0.6, "red")
    # a red tick where the cord passes each slab: it passes, it is not mounted
    for i in range(1, 8):
        y = GROUND - i * FLOOR_H - SLAB / 2
        h.straight([(CORD_X - 1.3, y), (CORD_X - 0.5, y)], "hair", "red")


def draw_floor_of_hands(h, rng):
    """the ground floor: raised hands along the floor behind Foras"""
    yf = GROUND
    xs = [BX0 + WALL + 8 + k * 3.7 for k in range(26)]
    for k, x in enumerate(xs):
        if x < 74 or 92 < x < 108 or 118 < x or SHAFT[0] - 8 < x:   # clear of the stair, the seal, Foras and the shaft
            continue
        hand_up(h, rng, x + rng.uniform(-0.8, 0.8), yf - 1.6, 4.2 + rng.uniform(-0.6, 1.2))


# ------------------------------------------------------------------ bottom --

def draw_specimens(h, font):
    y_top, y_bot = 243, 262
    cols = [(46, "MOUNTED"), (105, "RECEIVED"), (164, "NEITHER")]
    for k, (cx, lab) in enumerate(cols):
        # a cord hanging from a bracket
        bx, by = cx, y_top + 1.5
        h.straight([(bx - 4, by), (bx + 4, by)], "orn", "ink")
        if k == 0:
            # mounted: a hook with a bell on the cord
            h.straight([(bx, by), (bx, by + 2.4)], "orn", "ink")
            h.straight([(bx, by + 2.4), (bx, y_bot - 4.5)], "orn", "red")
            h.stroke(arc_pts(bx, y_bot - 2.2, 2.4, 200, 340, 16), "orn", "ink", amp=0.1)
            h.straight([(bx - 2.3, y_bot - 1.4), (bx + 2.3, y_bot - 1.4)], "orn", "ink")
            h.dot(bx, y_bot - 0.6, 0.3, "ink")
        elif k == 1:
            # received: the cord ends in a hand that holds it
            h.straight([(bx, by), (bx, by + 2.4)], "orn", "ink")
            h.straight([(bx, by + 2.4), (bx, y_bot - 5.0)], "orn", "red")
            hand_up(h, random.Random(7), bx, y_bot - 0.5, 4.6)
        else:
            # neither: the bracket is open and the cord stops short of it
            h.straight([(bx, by), (bx, by + 1.6)], "orn", "ink")
            h.stroke(arc_pts(bx + 1.2, by + 1.6, 1.2, 180, 360, 14), "orn", "ink", amp=0.1)
            h.straight([(bx, by + 5.2), (bx, y_bot - 2.5)], "orn", "red")
            h.dot(bx, by + 4.9, 0.4, "red")
        label(font, h, lab, cx, y_bot + 5.0, 2.5, "center")


# --------------------------------------------------------------- furniture --

def draw_furniture(h, font, litany_words):
    x0, y0, x1, y1 = FRAME
    h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
    label(font, h, "CLAVICULA GRADUUM", W / 2, 20.5, 4.1, "center")
    label(font, h, "THE CHANNEL THAT TOUCHES NO OFFICE", W / 2, 27, 2.5, "center")
    h.straight([(x0 + 4, 30.5), (x1 - 4, 30.5)], "hair", "ink")
    rx, ry, rw, rh = RESERVED
    h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
    label(font, h, "RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
    # registers A and B: the litany, A top to bottom then B
    half = (len(litany_words) + 1) // 2
    colA, colB = litany_words[:half], litany_words[half:]
    label(font, h, "A", 14, 78, 2.5)
    label(font, h, "B", 196, 78, 2.5, "right")
    for k, wd in enumerate(colA):
        label(font, h, wd, 14, 85 + k * 4.3, 2.5)
    for k, wd in enumerate(colB):
        label(font, h, wd, 196, 85 + k * 4.3, 2.5, "right")
    h.straight([(x0 + 4, 238), (x1 - 4, 238)], "hair", "ink")
    h.straight([(x0 + 4, 271), (x1 - 4, 271)], "hair", "ink")
    label(font, h, "TABULA VII", W / 2, 277.5, 2.5, "center")
    label(font, h, "THE CORD WITHOUT A MOUNT", W / 2, 283.5, 3.0, "center")


def draw_scale(h):
    """the frame as a rule: the plate is an instrument section, so its frame is graduated.
    The ticks are the fourth carrier, black a / red b; the long ticks are periodic and carry nothing."""
    n, total = ornament.scale_frame(h, FRAME, HIDDEN, pitch=2.5, short=1.0, long=2.0, long_every=10, weight="orn" if SUFFIX else "hair")
    return {"carrier": "frame scale, clockwise from the top-left corner", "form": "ink: black a, red b",
            "message": HIDDEN, "carrier_marks": n, "ticks": total, "pitch_mm": 2.5}


# -------------------------------------------------------------------- build --

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
    tiers = json.load(open(CATALOGUE, encoding="utf-8"))["tiers"]
    table = litany_table()
    words = encode_litany(CAPTION_NORM, table)

    seal_pos = draw_building(art, rng, font, tiers)
    bracket = draw_top_floor(art, rng, font)
    draw_floor_of_hands(art, rng)
    # Foras on the floor of hands: six arms, the upper right hand raised to the shaft
    hand_pt = robed_figure(art, rng, cx=131, y_feet=GROUND - 1.6, height=19.2, arms=6, raise_to=(SHAFT[0] - 1.0, GROUND - 18.0))
    draw_cord(art, hand_pt, bracket)
    draw_specimens(art, font)
    draw_furniture(text, font, words)
    hidden = draw_scale(text)

    meta = {"plate": "VII", "title": "The Cord Without a Mount", "seed": SEED, "reserved_blank_mm": RESERVED,
            "cord_x": CORD_X, "bracket": bracket, "hand": hand_pt, "seal_positions": seal_pos,
            "litany_words": words, "caption_normalized": CAPTION_NORM, "hidden": hidden}
    title = "Clavicula Graduum - Tabula VII - The Cord Without a Mount"
    desc = ("Stroke-only pen plot plate, 210 x 297 mm. Two layers (Art Paths, Text Outlines), two inks. "
            "Untested on a physical plotter.")
    stem = "vii-cord-without-a-mount" + suffix
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
        json.dump({"plate": type_audit, "minimum_cap_mm": min(t["cap_height_mm"] for t in type_audit)}, f, indent=1)
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
