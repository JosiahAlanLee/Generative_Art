"""Clavicula Graduum - Tabula VI - The Feudal Register (native vector plate).

A maze from above. Four hooded managers on four landings, each holding one tile, which is a
true crop of the maze: the cell it is allowed to see. The environment's reward enters at the
top as a red thread from the maze's goal and is caught at each landing by one of Book III's
hiding apparatus (Culpax, Redacth, Velaroth) and not passed down. At the fourth landing the
pane is cracked and the drop reaches the last manager's tile: the leak of 2017.

Second text: the caption in the twelve-mark hand at shift +6.
Fourth carrier: the maze's junction nodes, read row by row: a dot is b, none is a.
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
sys.path.insert(0, os.path.join(REPO, "books", "04_graduum", "plates", "viii-native"))
import ornament  # noqa: E402
import tx  # noqa: E402
import apparatus as ap  # noqa: E402
from figures import robed_figure  # noqa: E402
from plotkit import PlotDoc, PlotHand, SVGFont, INK, RED, arc_pts, catmull  # noqa: E402
import marks  # noqa: E402  (the Matricis glyph system)

SEED = 1993   # Dayan and Hinton
W, H = 210, 297
FRAME = (8, 10, 202, 288)
RESERVED = (17, 42, 40, 24)
CAPTION = "Each learned its tile and nothing beyond it."
CAPTION_NORM = "EACH LEARNED ITS TILE AND NOTHING BEYOND IT"
SHIFT = 6
HIDDEN = "FULL SIGHT LEARNS AS FAST"      # the clause that would count against the ninth claim

MAZE = (22.0, 76.0, 12, 7.2)             # x, y, cells per side, cell mm  (86.4 mm square)
GOAL = (8, 3)                            # cell (col, row) holding the environment's reward
TILES = [(1, 1), (10, 2), (3, 9), (9, 10)]      # the cell each manager may see, top landing first
LANDINGS = [88.0, 128.0, 168.0, 208.0]   # y of each landing's floor
LX0, LX1 = 128.0, 192.0                  # landing extent
MGR_X, APP_X = 143.0, 176.0

type_audit = []


def label(font, h, text, x, y, cap, align="left", color="ink"):
    x0, w = font.write(h, text, x, y, cap, align, color)
    type_audit.append({"text": text, "cap_height_mm": cap, "x": round(x0, 2), "y": y, "width": round(w, 2), "ink": color})
    return x0, w


# ------------------------------------------------------------------- maze --

def carve(n, rng):
    """recursive backtracker; walls[(c, r)] = set of open sides among 'N','S','E','W'"""
    open_ = {(c, r): set() for c in range(n) for r in range(n)}
    stack = [(0, 0)]
    seen = {(0, 0)}
    while stack:
        c, r = stack[-1]
        nb = [(c + dc, r + dr, d, o) for dc, dr, d, o in ((1, 0, "E", "W"), (-1, 0, "W", "E"), (0, 1, "S", "N"), (0, -1, "N", "S"))
              if 0 <= c + dc < n and 0 <= r + dr < n and (c + dc, r + dr) not in seen]
        if not nb:
            stack.pop()
            continue
        nc, nr, d, o = rng.choice(nb)
        open_[(c, r)].add(d)
        open_[(nc, nr)].add(o)
        seen.add((nc, nr))
        stack.append((nc, nr))
    return open_


def wall_segments(open_, n):
    """closed wall segments as ((c0, r0), (c1, r1)) in node coordinates"""
    segs = set()
    for (c, r), o in open_.items():
        if "N" not in o:
            segs.add(((c, r), (c + 1, r)))
        if "W" not in o:
            segs.add(((c, r), (c, r + 1)))
        if c == n - 1 and "E" not in o:
            segs.add(((c + 1, r), (c + 1, r + 1)))
        if r == n - 1 and "S" not in o:
            segs.add(((c, r + 1), (c + 1, r + 1)))
    return sorted(segs)


def draw_maze(h, rng, open_):
    mx, my, n, cs = MAZE
    P = lambda c, r: (mx + c * cs, my + r * cs)
    for (a, b) in wall_segments(open_, n):
        h.stroke([P(*a), P(*b)], "orn", "ink", amp=0.12)
    # the goal: the environment's reward, a red drop in its cell
    gx, gy = P(GOAL[0] + 0.5, GOAL[1] + 0.5)
    drop(h, gx, gy, 1.3)
    # the junction nodes: the fourth carrier, row by row, a dot for b
    bl = ornament.bits(HIDDEN)
    i = 0
    for r in range(n + 1):
        for c in range(n + 1):
            b = bl[i] if i < len(bl) else (1 if rng.random() < 0.28 else 0)
            if b:
                h.dot(P(c, r)[0], P(c, r)[1], 0.34, "ink")
                h.pdoc.layers[h.layer][-1] = h.pdoc.layers[h.layer][-1][:3] + (f' data-nodedot="{i}"',)
            i += 1
    return {"carrier": "maze junction nodes, row by row from the top-left", "form": "dot = b, none = a",
            "message": HIDDEN, "carrier_marks": len(bl), "nodes": i}


def solve(open_, n, start, goal):
    """breadth-first path of cells from start to goal"""
    from collections import deque
    prev = {start: None}
    q = deque([start])
    step = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
    while q:
        c = q.popleft()
        if c == goal:
            break
        for d in open_[c]:
            nb = (c[0] + step[d][0], c[1] + step[d][1])
            if nb not in prev:
                prev[nb] = c
                q.append(nb)
    path, c = [], goal
    while c is not None:
        path.append(c)
        c = prev[c]
    return path[::-1]


def draw_flow(h, rng, open_):
    """flowing lines for the narrative: the environment's own route from the entrance to the
    reward, three wandering lines through the cells, which no manager's tile shows"""
    mx, my, n, cs = MAZE
    path = solve(open_, n, (0, 0), GOAL)
    centres = [(mx + (c + 0.5) * cs, my + (r + 0.5) * cs) for c, r in path]
    for u in (-0.9, 0.0, 0.9):
        pts = [(x + u + rng.uniform(-0.3, 0.3), y + u * 0.6 + rng.uniform(-0.3, 0.3)) for x, y in centres]
        c = catmull(pts, 6)
        h.stroke(c[:-4], "hair", "ink", amp=0.35)
    marks.asterisk(h, centres[0][0], centres[0][1], 1.6, 8, weight="hair", tipdots=False)
    return len(path)


def draw_glyphs(h, rng):
    """the Matricis glyph system: map -> world and the map moves it, beside the environment;
    the cut, in red, at the crack"""
    mx, my, n, cs = MAZE
    marks.sig_reflexive(h, mx + n * cs - 14, my + n * cs + 9.5, 7.0, orn=0)
    px, py = APP_X + 0.22 * 30 * 0.72, LANDINGS[3] - 0.4 - 30 * 0.72 + 0.3 * 30 * 0.72
    marks.sig_break(h, px, py, 2.4)


def drop(h, x, y, s, color="red"):
    pts = [(x, y - 1.4 * s)]
    for a in range(-60, 241, 15):
        pts.append((x + 0.8 * s * math.cos(math.radians(a)), y + 0.8 * s * math.sin(math.radians(a))))
    pts.append((x, y - 1.4 * s))
    h.stroke(catmull(pts, 4), "orn", color, amp=0.15)


def tile(h, open_, cell, cx, cy, size):
    """a true crop of the maze: the cell's four sides as they are, in a square of `size`"""
    c, r = cell
    o = open_[cell]
    hs = size / 2
    corners = {"N": ((cx - hs, cy - hs), (cx + hs, cy - hs)), "S": ((cx - hs, cy + hs), (cx + hs, cy + hs)),
               "W": ((cx - hs, cy - hs), (cx - hs, cy + hs)), "E": ((cx + hs, cy - hs), (cx + hs, cy + hs))}
    h.straight([(cx - hs - 0.8, cy - hs - 0.8), (cx + hs + 0.8, cy - hs - 0.8), (cx + hs + 0.8, cy + hs + 0.8), (cx - hs - 0.8, cy + hs + 0.8)], "hair", "ink", closed=True)
    for side, seg in corners.items():
        if side not in o:
            h.stroke(list(seg), "orn", "ink", amp=0.12)


# --------------------------------------------------------------- landings --

def draw_landings(h, rng, open_):
    mx, my, n, cs = MAZE
    P = lambda c, r: (mx + c * cs, my + r * cs)
    apps = [ap.culpax, ap.redacth, ap.velaroth, ap.viridon_cracked]
    mouths = []
    for i, y in enumerate(LANDINGS):
        h.straight([(LX0, y), (LX1, y)], "core", "ink")
        h.straight([(LX0, y + 1.1), (LX1, y + 1.1)], "hair", "ink")
        # the hatched riser under each landing
        for xx in range(int(LX0) + 2, int(LX1) - 1, 2):
            h.stroke([(xx, y + 1.1), (xx - 1.2, y + 3.4)], "hair", "ink", amp=0.1)
        # the manager, hooded, holding its tile up in the raised hand
        hand = robed_figure(h, rng, cx=MGR_X, y_feet=y - 0.6, height=21.0, arms=2, raise_to=(MGR_X + 11.5, y - 20.5), papers=False)
        tile(h, open_, TILES[i], hand[0] + 0.5, hand[1] - 4.8, 6.0)
        # the apparatus that catches the reward on this landing
        mouth, fp = apps[i](h, rng, APP_X, y - 0.4, 0.72)
        mouths.append(mouth)
        # the cell each manager sees, ringed in the maze
        c, r = TILES[i]
        cx_, cy_ = P(c + 0.5, r + 0.5)
        h.straight([(cx_ - cs / 2 + 0.6, cy_ - cs / 2 + 0.6), (cx_ + cs / 2 - 0.6, cy_ - cs / 2 + 0.6), (cx_ + cs / 2 - 0.6, cy_ + cs / 2 - 0.6), (cx_ - cs / 2 + 0.6, cy_ + cs / 2 - 0.6)], "hair", "ink", closed=True)
    # the reward: a red thread from the goal cell, out of the maze, across to the first apparatus
    gx, gy = P(GOAL[0] + 0.5, GOAL[1] + 0.5)
    m0 = mouths[0]
    route = [(gx, gy - 2.0), (gx, my - 14), (mx + n * cs + 6, my - 14), (m0[0], my - 14), (m0[0], m0[1] - 2.2)]
    h.stroke(catmull(route, 3), "hair", "red", amp=0.2)
    # a drop in each apparatus: the environment's at the top, and below it each manager's own,
    # which is what the next level is rewarded with. Nothing passes down.
    for i, m in enumerate(mouths):
        drop(h, m[0], m[1] - 0.6, 1.0)
    # the leak: through the cracked pane, down to the last tile
    last = mouths[-1]
    tile_pt = (MGR_X + 12.0, LANDINGS[-1] - 25.3)
    h.stroke([(last[0] + 1.0, last[1] + 6.0), (last[0] - 6.0, last[1] + 9.0), (tile_pt[0] + 3.0, tile_pt[1] + 3.0)], "hair", "red", amp=0.3)
    drop(h, tile_pt[0] + 0.5, tile_pt[1] + 0.8, 0.7)
    return mouths


# ----------------------------------------------------------- twin register --

def draw_twin_register(h, rng, cx, cy):
    """two heads and one body around an open ring"""
    marks.sig_boundary(h, cx, cy, 5.6, orn=0)
    body = [(cx + 9.5 * math.cos(math.radians(a)), cy + 9.5 * math.sin(math.radians(a)) + 0.9 * math.sin(math.radians(a * 5))) for a in range(40, 321, 5)]
    for off in (-1.1, 1.1):
        pts = []
        for i, (x, y) in enumerate(body):
            j0, j1 = max(0, i - 1), min(len(body) - 1, i + 1)
            tx_, ty_ = body[j1][0] - body[j0][0], body[j1][1] - body[j0][1]
            m = math.hypot(tx_, ty_) or 1
            pts.append((x - ty_ / m * off, y + tx_ / m * off))
        h.stroke(pts, "orn", "ink", amp=0.2)
    for i in range(0, len(body), 4):
        x, y = body[i]
        h.stroke([(x - 0.9, y), (x + 0.9, y)], "hair", "ink")
    for end, sgn in ((body[0], 1), (body[-1], -1)):
        hx, hy = end
        head = [(hx, hy), (hx + sgn * 1.2, hy - 2.6 * sgn), (hx + sgn * 3.4, hy - 2.4 * sgn), (hx + sgn * 3.6, hy - 0.4 * sgn), (hx + sgn * 1.5, hy + 1.0 * sgn)]
        h.stroke(catmull(head + [head[0]], 5), "core", "ink", amp=0.2)
        h.dot(hx + sgn * 2.2, hy - 1.3 * sgn, 0.3, "ink")


# -------------------------------------------------------------- furniture --

def draw_furniture(h, font):
    x0, y0, x1, y1 = FRAME
    h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
    label(font, h, "CLAVICULA GRADUUM", W / 2, 20.5, 4.1, "center")
    label(font, h, "HIDING IS THE DESIGN / THE COST IS PAID AT THE BOUNDARY", W / 2, 27, 2.5, "center")
    h.straight([(x0 + 4, 30.5), (x1 - 4, 30.5)], "hair", "ink")
    rx, ry, rw, rh = RESERVED
    h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
    label(font, h, "RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
    mx, my, n, cs = MAZE
    label(font, h, "THE ENVIRONMENT", mx, my + n * cs + 5.2, 2.5)
    label(font, h, "SEEN FROM ABOVE", mx, my + n * cs + 10.0, 2.5)
    for i, y in enumerate(LANDINGS):
        label(font, h, ["I", "II", "III", "IV"][i], LX0 - 5, y - 1.5, 2.5, "right")
    label(font, h, "CULPAX", APP_X, LANDINGS[0] + 5.6, 2.5, "center")
    label(font, h, "REDACTH", APP_X, LANDINGS[1] + 5.6, 2.5, "center")
    label(font, h, "VELAROTH", APP_X, LANDINGS[2] + 5.6, 2.5, "center")
    label(font, h, "VIRIDON / LEAKS", APP_X, LANDINGS[3] + 5.6, 2.5, "center")
    label(font, h, "THE TWIN REGISTER", 60, 226.5, 2.5, "center")
    h.straight([(x0 + 4, 238), (x1 - 4, 238)], "hair", "ink")
    label(font, h, "REWARD HIDING / INFORMATION HIDING", W / 2, 245, 2.5, "center")
    h.straight([(x0 + 4, 268), (x1 - 4, 268)], "hair", "ink")
    label(font, h, "TABULA VI", W / 2, 275.5, 2.5, "center")
    label(font, h, "THE FEUDAL REGISTER", W / 2, 281.5, 3.0, "center")


def write_shifted(h, text, x, y, s, shift):
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


# ------------------------------------------------------------------ build --

def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rng = random.Random(SEED)
    doc = PlotDoc(W, H)
    from plate import lettering
    font, suffix = lettering()
    art = PlotHand(doc, rng, "art", amp=0.07)
    text = PlotHand(doc, random.Random(SEED + 1), "text", amp=0.03)

    open_ = carve(MAZE[2], random.Random(SEED + 2))
    hidden = draw_maze(art, rng, open_)
    path_len_cells = draw_flow(art, rng, open_)
    draw_glyphs(art, rng)
    mouths = draw_landings(art, rng, open_)
    draw_twin_register(art, rng, 60, 206)
    draw_furniture(text, font)
    cap_pos = draw_caption(text)

    meta = {"plate": "VI", "title": "The Feudal Register", "seed": SEED, "reserved_blank_mm": RESERVED,
            "maze": MAZE, "goal": GOAL, "tiles": TILES, "landings": LANDINGS, "mouths": [[round(a, 1), round(b, 1)] for a, b in mouths],
            "caption": cap_pos, "caption_normalized": CAPTION_NORM, "hidden": hidden, "route_cells": path_len_cells}
    title = "Clavicula Graduum - Tabula VI - The Feudal Register"
    desc = ("Stroke-only pen plot plate, 210 x 297 mm. Two layers (Art Paths, Text Outlines), two inks. "
            "Untested on a physical plotter.")
    stem = "vi-feudal-register" + suffix
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
