"""Clavicula Graduum - Tabula II - The Two Watchmakers (native vector plate).

A diptych. Left, Hora assembles in tens: each ten is a ring of parts round a hub, and once
closed it goes to the shelf and survives the bell. Right, Tempus assembles from loose parts,
and every bell scatters them back to the bench. The same red interruptions fall on both
timelines at the same moments. Between the panels, the Returning Trace: the bird that leaves
the ring and comes back to it, because the ring is a stable subassembly. Repetiel, who loseth
context at the boundary, keeps Tempus's bench. Below each bench, a completion specimen in the
manner of Book II.

Fourth carrier: Tempus's loose parts, read row by row: a ring is b, a dot is a.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
sys.path.insert(0, os.path.join(REPO, "books", "04_graduum", "plates", "viii-native"))
from plate import Plate, validate  # noqa: E402
from plotkit import arc_pts, catmull  # noqa: E402
import marks  # noqa: E402
import apparatus as ap  # noqa: E402

LEFT = (16.0, 100.0)
RIGHT = (110.0, 194.0)
TOP, BENCH = 80.0, 214.0
BELLS = [92, 110, 124, 146, 164, 182, 200]       # the same moments on both timelines
MID = 105.0


def ten(h, cx, cy, r, parts=10, closed=True):
    """a subassembly: ten parts round a hub"""
    for i in range(parts):
        a = math.radians(-90 + i * 36)
        h.dot(cx + r * math.cos(a), cy + r * math.sin(a), 0.42, "ink")
    if closed:
        h.stroke(arc_pts(cx, cy, r, 0, 360, 30), "hair", "ink", amp=0.15)
        h.dot(cx, cy, 0.3, "ink")
    else:
        h.ring(cx, cy, 0.5, "hair", "ink")


def timeline(h, x, rng, bells):
    h.straight([(x, TOP), (x, BENCH)], "core", "ink")
    for y in bells:
        h.straight([(x - 2.2, y), (x + 2.2, y)], "orn", "red")
    # the bell, drawn once at the top of each line
    h.stroke(arc_pts(x, TOP - 3.2, 2.2, 200, 340, 12), "orn", "ink", amp=0.1)
    h.stroke([(x - 2.0, TOP - 2.2), (x + 2.0, TOP - 2.2)], "orn", "ink", amp=0.1)
    h.dot(x, TOP - 1.4, 0.25, "ink")


SHELF = (82.0, 100.0, 30.0)                   # centre and size of the shelf's walls (sig_invariant)
SHELF_CELLS = [(x, y) for y in (91.0, 109.0) for x in (68.0, 77.0, 86.0, 95.0)]


def hora(P):
    h, rng = P.art, P.rng
    x0, x1 = LEFT
    tl = x0 + 6
    timeline(h, tl, rng, BELLS)
    # the shelf: hard walls, one door, on the right
    scx, scy, ss = SHELF
    marks.sig_invariant(h, scx, scy, ss, orn=0)
    door = (scx + ss * 0.55, scy)
    # in every interval a ten is closed beside the line; it goes to the shelf through the door
    edges = [TOP] + BELLS + [BENCH]
    done = 0
    for k in range(len(edges) - 1):
        y = (edges[k] + edges[k + 1]) / 2
        ten(h, tl + 14, y, 4.0, parts=10, closed=True)
        if done < len(SHELF_CELLS):
            sx, sy = SHELF_CELLS[done]
            ten(h, sx, sy, 3.0, closed=True)
            # the trace: out of the ten, up the channel beside the shelf, in at the door, to its cell
            pts = [(tl + 18.4, y), (door[0] + 4 + rng.uniform(-0.6, 0.6), (y + door[1]) / 2 + rng.uniform(-3, 3)),
                   (door[0] + 2.5, door[1] + rng.uniform(-2, 2)), (door[0] - 1.5, door[1]), (sx + 3.4, sy)]
            if y < door[1]:
                pts = [(tl + 18.4, y), (tl + 30, y + 2), (door[0] + 3, (y + door[1]) / 2), (door[0] - 1.5, door[1]), (sx + 3.4, sy)]
            h.stroke(catmull(pts, 10), "hair", "ink", amp=0.35)
            done += 1
    # the bench and the whole, assembled from the tens that survived
    h.straight([(x0 + 2, BENCH), (x1 - 2, BENCH)], "core", "ink")
    h.straight([(x0 + 2, BENCH + 1.1), (x1 - 2, BENCH + 1.1)], "hair", "ink")
    wx, wy = x0 + 56, BENCH - 11
    for i in range(10):
        a = math.radians(-90 + i * 36)
        if i < done:
            ten(h, wx + 7.8 * math.cos(a), wy + 7.8 * math.sin(a), 2.0, closed=True)
        else:
            h.ring(wx + 7.8 * math.cos(a), wy + 7.8 * math.sin(a), 2.0, "hair", "ink")
    h.stroke(arc_pts(wx, wy, 7.8, 0, 360, 40), "hair", "ink", amp=0.1)
    # specimen: a band of ten cells, one per ten closed, in the manner of Book II
    marks.band_x(h, (x0 + 6, BENCH + 8), (x1 - 6, BENCH + 8), 3.6, 10, centre_dots=False)
    for k in range(done):
        cx = x0 + 6 + (x1 - x0 - 12) / 10 * (k + 0.5)
        h.dot(cx, BENCH + 8, 0.45, "ink")
    return done


def tempus(P):
    h, rng = P.art, P.rng
    x0, x1 = RIGHT
    tl = x0 + 6
    timeline(h, tl, rng, BELLS)
    # the loose parts: a jittered grid across the panel, every part a mark of the fourth carrier
    bl = P.bits()
    cols, rows = 8, 13
    gx0, gy0 = tl + 12, TOP + 8
    dx, dy = (x1 - 6 - gx0) / (cols - 1), (BENCH - 24 - gy0) / (rows - 1)
    i = 0
    for r in range(rows):
        for c in range(cols):
            x = gx0 + c * dx + rng.uniform(-1.6, 1.6)
            y = gy0 + r * dy + rng.uniform(-1.4, 1.4)
            b = bl[i] if i < len(bl) else (1 if rng.random() < 0.3 else 0)
            if b:
                h.ring(x, y, 0.7, "hair", "ink")
                P.tag_last(h, "part", i)
            else:
                h.dot(x, y, 0.42, "ink")
            i += 1
    P.mark_carrier("Tempus's loose parts, row by row from the top-left", "ring = b, dot = a", i, tag="part")
    # at each bell the parts scatter: a short flowing burst from the line
    for y in BELLS:
        for u in (-1.2, 0, 1.2):
            pts = [(tl + 2.4, y + u * 0.4), (tl + 6 + rng.uniform(0, 2), y + u * 1.6), (tl + 10 + rng.uniform(0, 3), y + u * 3.2)]
            h.stroke(catmull(pts, 6), "hair", "ink", amp=0.4)
    # the bench, with the assembly that never closed, and Repetiel at the bench end
    h.straight([(x0 + 2, BENCH), (x1 - 2, BENCH)], "core", "ink")
    h.straight([(x0 + 2, BENCH + 1.1), (x1 - 2, BENCH + 1.1)], "hair", "ink")
    wx, wy = x0 + 40, BENCH - 8
    for i in range(3):
        a = math.radians(-90 + i * 36)
        h.dot(wx + 5.5 * math.cos(a), wy + 5.5 * math.sin(a), 0.42, "ink")
    h.stroke(arc_pts(wx, wy, 5.5, -90, -18, 10), "hair", "ink", amp=0.15)
    ap.repetiel(h, rng, x1 - 16, BENCH - 0.4, 0.62)
    marks.band_x(h, (x0 + 6, BENCH + 8), (x1 - 6, BENCH + 8), 3.6, 10, centre_dots=False)
    return i


def returning_trace(P):
    """the bird that leaves the ring and returns to it"""
    h, rng = P.art, P.rng
    cx, cy = MID, 50.0
    h.stroke(arc_pts(cx, cy, 4.2, 20, 340, 24), "core", "ink", amp=0.15)        # the ring, open at the right
    # the bird: a small body with two wing strokes and a beak, perched on the ring's top
    bx, by = cx + 0.5, cy - 4.6
    h.stroke(catmull([(bx - 2.2, by + 0.2), (bx - 0.6, by - 1.2), (bx + 1.4, by - 0.9), (bx + 2.4, by + 0.3)], 6), "orn", "ink", amp=0.2)
    h.stroke([(bx - 0.4, by - 1.1), (bx - 1.8, by - 3.4)], "orn", "ink", amp=0.2)
    h.stroke([(bx + 0.6, by - 1.0), (bx + 1.4, by - 3.3)], "orn", "ink", amp=0.2)
    h.stroke([(bx + 2.4, by + 0.3), (bx + 3.6, by + 0.1)], "orn", "ink", amp=0.1)
    h.dot(bx + 1.6, by - 0.3, 0.22, "ink")
    # the trace: three lines that leave the ring, loop out over Hora's side and come back
    for u in (-0.8, 0, 0.8):
        pts = [(cx + 4.2, cy - 1 + u), (cx + 10 + u, cy - 10), (cx - 4 + u * 1.5, cy - 15 + u), (cx - 16 + u, cy - 6),
               (cx - 10 + u, cy + 8), (cx + 3 + u * 0.5, cy + 6.5)]
        h.stroke(catmull(pts, 10), "hair", "ink", amp=0.35)
    h.dot(cx + 3.2, cy + 6.5, 0.3, "ink")


def main(out_dir):
    P = Plate("II", "The Two Watchmakers", "ASSEMBLY UNDER INTERRUPTION", "ii-two-watchmakers",
              "Hora's shop stayed open.", 2, "LOOSE PARTS SURVIVE", 1962,
              strap="THE SAME BELL AT THE SAME MOMENTS")
    h = P.art
    h.straight([(MID, 76), (MID, BENCH + 12)], "hair", "ink")
    done = hora(P)
    n = tempus(P)
    returning_trace(P)
    # the same moment, cut, on both lines
    for x in (LEFT[0] + 6, RIGHT[0] + 6):
        marks.sig_break(h, x, BELLS[3], 1.6)
    P.label("HORA", LEFT[0] + 2, TOP - 5, 2.5)
    P.label("IN TENS", LEFT[1] - 2, TOP - 5, 2.5, "right")
    P.label("TEMPUS", RIGHT[0] + 2, TOP - 5, 2.5)
    P.label("FROM PARTS", RIGHT[1] - 2, TOP - 5, 2.5, "right")
    P.label("SHELF", SHELF[0] - 3, SHELF[1] + SHELF[2] * 0.6 + 4.6, 2.5, "center")
    P.label("REPETIEL", RIGHT[1] - 2, BENCH - 24, 2.5, "right")
    P.label("THE RETURNING TRACE", MID, 68, 2.5, "center")
    P.label("COMPLETE", LEFT[0] + 6, BENCH + 15.5, 2.5)
    P.label("COMPLETE", RIGHT[0] + 6, BENCH + 15.5, 2.5)
    P.label(f"{done} OF 10", LEFT[1] - 6, BENCH + 15.5, 2.5, "right")
    P.label("0 OF 10", RIGHT[1] - 6, BENCH + 15.5, 2.5, "right")
    P.furniture()
    P.caption_strip()
    P.export(out_dir, {"bells": BELLS, "hora_tens_done": done, "tempus_parts": n})


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    main(out)
    validate(out)
