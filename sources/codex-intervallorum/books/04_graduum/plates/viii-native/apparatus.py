"""The handoff demons of Book III drawn as apparatus (the series rule: offices are persons
in robes, handoffs are apparatus). Each function draws one at (cx, y_feet) with scale k
(k = 1 is about 30 mm tall) and returns (mouth_point, footprint_polygon). Same stroke
vocabulary as the Keeper and the building."""
import math

from plotkit import catmull, arc_pts, bezier, Polygon


def _box(cx, y0, y1, hw):
    return Polygon([(cx - hw, y0), (cx + hw, y0), (cx + hw, y1), (cx - hw, y1)])


def _tripod(h, cx, y, k, spread=4.0):
    for dx in (-spread, 0, spread):
        h.stroke([(cx, y - 3.5 * k), (cx + dx * k, y)], "orn", "ink", amp=0.2)
        h.dot(cx + dx * k, y, 0.3, "ink")


def _hatch(h, pts, step=0.6, ang=45):
    from plotkit import hatch_lines
    for ln in hatch_lines(Polygon(pts), step, ang):
        h.stroke(ln, "hair", "ink", amp=0.05)


def repetiel(h, rng, cx, yf, k=1.0):
    """a mouth at either end of a clean speaking tube: a U on two feet"""
    s = 30 * k
    top = yf - s
    w = 0.42 * s
    # the U, two walls
    for sgn in (-1, 1):
        pts = [(cx - w, top), (cx - w, yf - 0.42 * s)] if sgn < 0 else [(cx + w, top), (cx + w, yf - 0.42 * s)]
        bottom = arc_pts(cx, yf - 0.42 * s, w, 180, 360, 20) if sgn < 0 else []
        h.stroke(pts, "core", "ink", amp=0.15)
    h.stroke(arc_pts(cx, yf - 0.42 * s, w, 0, 180, 24), "core", "ink", amp=0.15)
    h.stroke(arc_pts(cx, yf - 0.42 * s, w - 0.16 * s, 0, 180, 24), "orn", "ink", amp=0.15)
    for sgn in (-1, 1):
        x = cx + sgn * w
        h.stroke([(x - sgn * 0.16 * s, top + 0.06 * s), (x - sgn * 0.16 * s, yf - 0.42 * s)], "orn", "ink", amp=0.15)
        # mouth: an open ellipse with teeth
        mx, my = x - sgn * 0.08 * s, top
        h.stroke([(mx + 0.13 * s * math.cos(math.radians(a)), my + 0.07 * s * math.sin(math.radians(a))) for a in range(0, 361, 15)], "orn", "ink", amp=0.2)
        for a in range(200, 341, 28):
            px = mx + 0.11 * s * math.cos(math.radians(a))
            h.stroke([(px, my), (px, my + 0.045 * s)], "hair", "ink")
    # rings around the tube
    for t in (0.25, 0.5, 0.75):
        y = top + t * (yf - 0.42 * s - top)
        for sgn in (-1, 1):
            x = cx + sgn * w
            h.stroke([(x, y), (x - sgn * 0.16 * s, y)], "hair", "ink")
    # feet
    for sgn in (-1, 1):
        x = cx + sgn * 0.2 * s
        h.stroke([(x, yf - 0.1 * s), (x, yf)], "orn", "ink", amp=0.15)
        h.stroke([(x - 0.08 * s, yf), (x + 0.1 * s, yf)], "orn", "ink", amp=0.15)
    return (cx + w - 0.08 * s, top - 0.07 * s), _box(cx, top - 0.1 * s, yf, w + 0.12 * s)


def culpax(h, rng, cx, yf, k=1.0):
    """a funnel with a name badge at its narrow end"""
    s = 30 * k
    top = yf - s
    hw = 0.42 * s
    cone = [(cx - hw, top), (cx + hw, top), (cx + 0.05 * s, yf - 0.5 * s), (cx - 0.05 * s, yf - 0.5 * s)]
    h.stroke(cone, "core", "ink", closed=True, amp=0.15)
    h.stroke([(cx + hw * math.cos(math.radians(a)), top + 0.08 * s * math.sin(math.radians(a))) for a in range(0, 361, 12)], "orn", "ink", amp=0.15)
    _hatch(h, [(cx - hw + 0.04 * s, top + 0.1 * s), (cx + hw - 0.04 * s, top + 0.1 * s), (cx + 0.04 * s, yf - 0.52 * s), (cx - 0.04 * s, yf - 0.52 * s)], 0.9, 70)
    # stem and badge
    h.stroke([(cx - 0.04 * s, yf - 0.5 * s), (cx - 0.04 * s, yf - 0.15 * s)], "orn", "ink", amp=0.1)
    h.stroke([(cx + 0.04 * s, yf - 0.5 * s), (cx + 0.04 * s, yf - 0.15 * s)], "orn", "ink", amp=0.1)
    bx, by = cx + 0.14 * s, yf - 0.36 * s
    h.stroke([(bx - 0.1 * s, by - 0.06 * s), (bx + 0.1 * s, by - 0.06 * s), (bx + 0.1 * s, by + 0.06 * s), (bx - 0.1 * s, by + 0.06 * s)], "orn", "ink", closed=True, amp=0.1)
    h.stroke([(bx - 0.06 * s, by), (bx + 0.06 * s, by)], "hair", "ink")
    h.stroke([(cx + 0.04 * s, by), (bx - 0.1 * s, by)], "hair", "ink")
    _tripod(h, cx, yf, k, 5.0)
    return (cx, top - 0.02 * s), _box(cx, top - 0.1 * s, yf, hw + 0.05 * s)


def calmor(h, rng, cx, yf, k=1.0):
    """a bell padded on the inside, hung from a small gallows"""
    s = 30 * k
    top = yf - s
    # gallows
    h.stroke([(cx - 0.45 * s, yf), (cx - 0.45 * s, top)], "orn", "ink", amp=0.15)
    h.stroke([(cx - 0.45 * s, top), (cx + 0.1 * s, top)], "orn", "ink", amp=0.15)
    h.stroke([(cx - 0.45 * s, top + 0.2 * s), (cx - 0.25 * s, top)], "hair", "ink")
    h.stroke([(cx - 0.55 * s, yf), (cx - 0.35 * s, yf)], "orn", "ink")
    # bell
    bx, by = cx, top + 0.08 * s
    prof = [(bx, by), (bx + 0.08 * s, by + 0.04 * s), (bx + 0.12 * s, by + 0.3 * s), (bx + 0.2 * s, by + 0.5 * s), (bx + 0.34 * s, by + 0.62 * s), (bx + 0.36 * s, by + 0.68 * s)]
    left = [(2 * bx - x, y) for x, y in prof]
    h.stroke(catmull(prof, 6), "core", "ink", amp=0.15)
    h.stroke(catmull(left, 6), "core", "ink", amp=0.15)
    h.stroke([(bx - 0.36 * s, by + 0.68 * s), (bx + 0.36 * s, by + 0.68 * s)], "core", "ink", amp=0.1)
    # the padding: a felt lining drawn as a hatched inner band under the rim
    lining = [(bx - 0.33 * s, by + 0.66 * s), (bx + 0.33 * s, by + 0.66 * s), (bx + 0.2 * s, by + 0.5 * s), (bx - 0.2 * s, by + 0.5 * s)]
    _hatch(h, lining, 0.55, 0)
    h.stroke([(bx - 0.2 * s, by + 0.5 * s), (bx + 0.2 * s, by + 0.5 * s)], "hair", "ink")
    # clapper, hanging short of the lining
    h.stroke([(bx, by + 0.1 * s), (bx, by + 0.46 * s)], "orn", "ink", amp=0.1)
    h.dot(bx, by + 0.44 * s, 0.6 * k, "ink")
    return (bx, by + 0.72 * s), _box(cx, top - 0.05 * s, yf, 0.5 * s)


def instantor(h, rng, cx, yf, k=1.0):
    """an enormous finger pointing at a muted microphone"""
    s = 30 * k
    top = yf - s
    # microphone on a stand
    mx, my = cx, yf - 0.3 * s
    _tripod(h, mx, yf, k, 3.5)
    h.stroke([(mx, yf - 0.12 * s), (mx, my + 0.1 * s)], "orn", "ink", amp=0.1)
    cap = [(mx + 0.09 * s * math.cos(math.radians(a)), my + 0.13 * s * math.sin(math.radians(a))) for a in range(0, 361, 12)]
    h.stroke(cap, "orn", "ink", amp=0.15)
    _hatch(h, cap, 0.5, 45)
    _hatch(h, cap, 0.5, -45)
    # the mute: a stroke through it
    h.stroke([(mx - 0.16 * s, my + 0.14 * s), (mx + 0.16 * s, my - 0.16 * s)], "core", "ink", amp=0.05)
    # the finger alone: a tapered tube from above the cell, nail and two creases, pointing at the capsule
    fx = cx + 0.08 * s
    tip_y = my - 0.2 * s
    w0, w1 = 0.17 * s, 0.1 * s
    left = [(fx - w0, top - 0.3 * s), (fx - w0 * 0.95, top + 0.1 * s), (fx - w1 * 1.1, tip_y - 0.12 * s), (fx - w1 * 0.6, tip_y)]
    right = [(fx + w0, top - 0.3 * s), (fx + w0 * 0.95, top + 0.1 * s), (fx + w1 * 1.1, tip_y - 0.12 * s), (fx + w1 * 0.6, tip_y)]
    h.stroke(catmull(left, 8), "core", "ink", amp=0.15)
    h.stroke(catmull(right, 8), "core", "ink", amp=0.15)
    h.stroke(arc_pts(fx, tip_y, w1 * 0.6, 0, 180, 10), "core", "ink", amp=0.15)
    # the nail, on the far side, and two creases
    nail = [(fx + w1 * 0.2, tip_y - 0.02 * s), (fx + w1 * 1.05, tip_y - 0.1 * s), (fx + w1 * 1.0, tip_y - 0.26 * s), (fx + w1 * 0.3, tip_y - 0.22 * s)]
    h.stroke(catmull(nail + [nail[0]], 6), "orn", "ink", amp=0.15)
    for t in (0.42, 0.72):
        y = top - 0.3 * s + t * (tip_y - top + 0.3 * s)
        w = w0 + (w1 - w0) * t
        h.stroke(arc_pts(fx, y, w * 0.95, 20, 160, 10), "hair", "ink", amp=0.3)
        h.stroke(arc_pts(fx, y + 0.03 * s, w * 0.9, 30, 150, 10), "hair", "ink", amp=0.3)
    return (fx, tip_y + 0.03 * s), _box(cx, top - 0.32 * s, yf, 0.26 * s)


def choraz(h, rng, cx, yf, k=1.0, trumpets=16):
    """sixteen small trumpets attached to one empty helmet"""
    s = 30 * k
    top = yf - s
    # stand
    _tripod(h, cx, yf, k, 4.5)
    h.stroke([(cx, yf - 0.12 * s), (cx, yf - 0.38 * s)], "orn", "ink", amp=0.1)
    # the helmet: a dome with an open face that shows nothing
    hx, hy = cx, yf - 0.55 * s
    dome = arc_pts(hx, hy, 0.22 * s, 180, 360, 24)
    h.stroke(dome, "core", "ink", amp=0.15)
    h.stroke([(hx - 0.22 * s, hy), (hx - 0.22 * s, hy + 0.18 * s), (hx + 0.22 * s, hy + 0.18 * s), (hx + 0.22 * s, hy)], "core", "ink", amp=0.15)
    h.stroke([(hx - 0.12 * s, hy - 0.02 * s), (hx + 0.12 * s, hy - 0.02 * s), (hx + 0.12 * s, hy + 0.12 * s), (hx - 0.12 * s, hy + 0.12 * s)], "orn", "ink", closed=True, amp=0.1)
    # the trumpets: a fan from the crest
    mouths = []
    for i in range(trumpets):
        a = math.radians(200 + i * (140 / (trumpets - 1)))
        r0, r1 = 0.22 * s, (0.46 + 0.06 * math.sin(i * 1.7)) * s
        p0 = (hx + r0 * math.cos(a), hy + r0 * math.sin(a))
        p1 = (hx + r1 * math.cos(a), hy + r1 * math.sin(a))
        h.stroke([p0, p1], "orn", "ink", amp=0.1)
        # bell of the trumpet
        n = (-math.sin(a), math.cos(a))
        bw = 0.035 * s
        h.stroke([(p1[0] - n[0] * bw, p1[1] - n[1] * bw), (p1[0] + math.cos(a) * 0.05 * s, p1[1] + math.sin(a) * 0.05 * s), (p1[0] + n[0] * bw, p1[1] + n[1] * bw)], "orn", "ink", amp=0.15)
        mouths.append((p1[0] + math.cos(a) * 0.06 * s, p1[1] + math.sin(a) * 0.06 * s))
    return (hx, hy - 0.5 * s), _box(cx, top - 0.05 * s, yf, 0.55 * s)


def viridon(h, rng, cx, yf, k=1.0):
    """a green pane held before a red lamp (both in black here)"""
    s = 30 * k
    top = yf - s
    _tripod(h, cx, yf, k, 4.0)
    h.stroke([(cx, yf - 0.12 * s), (cx, top + 0.25 * s)], "orn", "ink", amp=0.1)
    # the lamp, behind
    lx, ly = cx, top + 0.3 * s
    h.ring(lx, ly, 0.1 * s, "orn", "ink")
    for a in range(0, 360, 30):
        h.stroke([(lx + 0.13 * s * math.cos(math.radians(a)), ly + 0.13 * s * math.sin(math.radians(a))), (lx + 0.2 * s * math.cos(math.radians(a)), ly + 0.2 * s * math.sin(math.radians(a)))], "hair", "ink")
    # the pane, in front, on an arm
    px, py = cx + 0.22 * s, top + 0.3 * s
    pane = [(px - 0.14 * s, py - 0.24 * s), (px + 0.14 * s, py - 0.24 * s), (px + 0.14 * s, py + 0.24 * s), (px - 0.14 * s, py + 0.24 * s)]
    h.stroke(pane, "core", "ink", closed=True, amp=0.1)
    _hatch(h, pane, 0.7, 60)
    h.stroke([(cx, py + 0.3 * s), (px, py + 0.3 * s), (px, py + 0.24 * s)], "orn", "ink", amp=0.1)
    return (px, py - 0.26 * s), _box(cx, top - 0.02 * s, yf, 0.4 * s)


def posthum(h, rng, cx, yf, k=1.0):
    """a small chair wheeled in after the meeting hath ended"""
    s = 30 * k
    top = yf - 0.6 * s
    seat_y = yf - 0.28 * s
    h.stroke([(cx - 0.2 * s, seat_y), (cx + 0.2 * s, seat_y)], "core", "ink", amp=0.1)
    h.stroke([(cx - 0.18 * s, seat_y), (cx - 0.16 * s, top)], "core", "ink", amp=0.1)
    h.stroke([(cx - 0.16 * s, top), (cx - 0.04 * s, top)], "core", "ink", amp=0.1)
    h.stroke([(cx - 0.04 * s, top), (cx - 0.06 * s, seat_y)], "orn", "ink", amp=0.1)
    _hatch(h, [(cx - 0.18 * s, seat_y), (cx - 0.16 * s, top), (cx - 0.04 * s, top), (cx - 0.06 * s, seat_y)], 0.6, 0)
    for x in (cx - 0.15 * s, cx + 0.15 * s):
        h.stroke([(x, seat_y), (x, yf - 0.08 * s)], "orn", "ink", amp=0.1)
        h.ring(x, yf - 0.05 * s, 0.05 * s, "orn", "ink")
        h.dot(x, yf - 0.05 * s, 0.25, "ink")
    # a short push-handle
    h.stroke([(cx - 0.16 * s, top + 0.1 * s), (cx - 0.3 * s, top + 0.02 * s)], "hair", "ink")
    return (cx - 0.1 * s, top - 0.02 * s), _box(cx, top - 0.05 * s, yf, 0.32 * s)


def exceptor(h, rng, cx, yf, k=1.0):
    """a stamp upon a form asking for a stamp"""
    s = 30 * k
    top = yf - s
    # the form on a lectern
    fx, fy = cx, yf - 0.46 * s
    form = [(fx - 0.26 * s, fy - 0.2 * s), (fx + 0.26 * s, fy - 0.2 * s), (fx + 0.26 * s, fy + 0.2 * s), (fx - 0.26 * s, fy + 0.2 * s)]
    h.stroke(form, "orn", "ink", closed=True, amp=0.1)
    for i in range(4):
        y = fy - 0.12 * s + i * 0.06 * s
        h.straight([(fx - 0.2 * s, y), (fx + (0.04 if i == 3 else 0.2) * s, y)], "hair", "ink")
    # the box asking for the stamp
    box = [(fx + 0.08 * s, fy + 0.02 * s), (fx + 0.22 * s, fy + 0.02 * s), (fx + 0.22 * s, fy + 0.16 * s), (fx + 0.08 * s, fy + 0.16 * s)]
    h.stroke(box, "hair", "ink", closed=True)
    # the stamp above, descending into the box
    sx = fx + 0.15 * s
    h.stroke([(sx - 0.1 * s, top + 0.02 * s), (sx + 0.1 * s, top + 0.02 * s), (sx + 0.06 * s, top + 0.2 * s), (sx - 0.06 * s, top + 0.2 * s)], "core", "ink", closed=True, amp=0.1)
    h.stroke([(sx - 0.03 * s, top + 0.2 * s), (sx - 0.03 * s, fy - 0.1 * s)], "orn", "ink", amp=0.1)
    h.stroke([(sx + 0.03 * s, top + 0.2 * s), (sx + 0.03 * s, fy - 0.1 * s)], "orn", "ink", amp=0.1)
    h.stroke([(sx - 0.09 * s, fy - 0.1 * s), (sx + 0.09 * s, fy - 0.1 * s), (sx + 0.09 * s, fy - 0.04 * s), (sx - 0.09 * s, fy - 0.04 * s)], "core", "ink", closed=True, amp=0.1)
    _hatch(h, [(sx - 0.09 * s, fy - 0.1 * s), (sx + 0.09 * s, fy - 0.1 * s), (sx + 0.09 * s, fy - 0.04 * s), (sx - 0.09 * s, fy - 0.04 * s)], 0.45, 90)
    # the impression already in the box: the same oblong, stamped
    h.stroke([(sx - 0.05 * s, fy + 0.06 * s), (sx + 0.05 * s, fy + 0.06 * s), (sx + 0.05 * s, fy + 0.12 * s), (sx - 0.05 * s, fy + 0.12 * s)], "orn", "ink", closed=True, amp=0.2)
    # lectern
    h.stroke([(fx, fy + 0.2 * s), (fx, yf - 0.1 * s)], "orn", "ink", amp=0.1)
    _tripod(h, fx, yf, k, 3.5)
    return (sx, top), _box(cx, top - 0.05 * s, yf, 0.3 * s)


def velaroth(h, rng, cx, yf, k=1.0):
    """a sheet folded until only its heading remaineth, on an easel"""
    s = 30 * k
    top = yf - 0.8 * s
    # easel
    for dx in (-0.2, 0.2):
        h.stroke([(cx + dx * s, yf), (cx, top)], "orn", "ink", amp=0.1)
    h.stroke([(cx, top + 0.05 * s), (cx + 0.05 * s, yf)], "hair", "ink")
    # the folded sheet: a short strip with the fold edges below it
    fx, fy = cx, top + 0.25 * s
    strip = [(fx - 0.28 * s, fy - 0.05 * s), (fx + 0.28 * s, fy - 0.05 * s), (fx + 0.28 * s, fy + 0.05 * s), (fx - 0.28 * s, fy + 0.05 * s)]
    h.stroke(strip, "core", "ink", closed=True, amp=0.1)
    h.straight([(fx - 0.22 * s, fy), (fx + 0.1 * s, fy)], "hair", "ink")
    for i in range(6):
        y = fy + 0.07 * s + i * 0.035 * s
        w = 0.28 * s - i * 0.012 * s
        h.stroke([(fx - w, y), (fx + w, y)], "hair", "ink", amp=0.3)
    return (fx, fy - 0.07 * s), _box(cx, top - 0.05 * s, yf, 0.32 * s)


def quarteroth(h, rng, cx, yf, k=1.0):
    """four clocks, each set to the last day of a different quarter"""
    s = 30 * k
    top = yf - s
    _tripod(h, cx, yf, k, 4.0)
    h.stroke([(cx, yf - 0.12 * s), (cx, top + 0.12 * s)], "orn", "ink", amp=0.1)
    for i, (dx, dy, hand) in enumerate(((-0.2, 0.22, 90), (0.2, 0.22, 180), (-0.2, 0.52, 270), (0.2, 0.52, 0))):
        x, y = cx + dx * s, top + dy * s
        h.ring(x, y, 0.13 * s, "core", "ink")
        for a in range(0, 360, 90):
            h.stroke([(x + 0.1 * s * math.cos(math.radians(a)), y + 0.1 * s * math.sin(math.radians(a))), (x + 0.13 * s * math.cos(math.radians(a)), y + 0.13 * s * math.sin(math.radians(a)))], "hair", "ink")
        h.stroke([(x, y), (x + 0.1 * s * math.cos(math.radians(hand)), y + 0.1 * s * math.sin(math.radians(hand)))], "orn", "ink", amp=0.05)
        h.stroke([(x, y), (x + 0.06 * s * math.cos(math.radians(hand + 100)), y + 0.06 * s * math.sin(math.radians(hand + 100)))], "orn", "ink", amp=0.05)
        h.dot(x, y, 0.25, "ink")
        h.stroke([(cx, y), (x, y)], "hair", "ink")
    return (cx, top + 0.06 * s), _box(cx, top - 0.02 * s, yf, 0.36 * s)


def severion(h, rng, cx, yf, k=1.0):
    """a balance whose pans are both marked normal"""
    s = 30 * k
    top = yf - s
    _tripod(h, cx, yf, k, 4.0)
    h.stroke([(cx, yf - 0.12 * s), (cx, top + 0.1 * s)], "orn", "ink", amp=0.1)
    h.stroke([(cx - 0.34 * s, top + 0.12 * s), (cx + 0.34 * s, top + 0.12 * s)], "core", "ink", amp=0.1)
    h.dot(cx, top + 0.11 * s, 0.35, "ink")
    for dx in (-0.3, 0.3):
        x = cx + dx * s
        py = top + 0.42 * s
        for ddx in (-0.1, 0.1):
            h.stroke([(x, top + 0.12 * s), (x + ddx * s, py)], "hair", "ink")
        h.stroke(arc_pts(x, py - 0.03 * s, 0.13 * s, 0, 180, 14), "orn", "ink", amp=0.15)
        # 'marked normal': an identical small tick on each pan
        h.stroke([(x - 0.03 * s, py + 0.04 * s), (x + 0.03 * s, py + 0.04 * s)], "hair", "ink")
    return (cx, top + 0.08 * s), _box(cx, top - 0.02 * s, yf, 0.45 * s)


def redacth(h, rng, cx, yf, k=1.0):
    """a black veil with spaces for initials, hung from a rod on a stand"""
    s = 30 * k
    top = yf - s
    _tripod(h, cx, yf, k, 4.0)
    h.stroke([(cx, yf - 0.12 * s), (cx, top + 0.04 * s)], "orn", "ink", amp=0.1)
    h.stroke([(cx - 0.32 * s, top + 0.04 * s), (cx + 0.32 * s, top + 0.04 * s)], "core", "ink", amp=0.1)
    veil = [(cx - 0.3 * s, top + 0.06 * s), (cx + 0.3 * s, top + 0.06 * s), (cx + 0.36 * s, top + 0.72 * s), (cx - 0.36 * s, top + 0.72 * s)]
    h.stroke(veil, "core", "ink", closed=True, amp=0.15)
    for i in range(7):
        u = -0.26 + i * 0.087
        h.stroke([(cx + u * s, top + 0.08 * s), (cx + u * 1.18 * s, top + 0.7 * s)], "hair", "ink", amp=0.4)
    # the spaces for initials: three small blanks the folds do not cross
    for i, (dx, dy) in enumerate(((-0.14, 0.26), (0.1, 0.4), (-0.02, 0.56))):
        bx, by = cx + dx * s, top + dy * s
        h.straight([(bx - 0.06 * s, by - 0.04 * s), (bx + 0.06 * s, by - 0.04 * s), (bx + 0.06 * s, by + 0.04 * s), (bx - 0.06 * s, by + 0.04 * s), (bx - 0.06 * s, by - 0.04 * s)], "orn", "ink")
    return (cx, top), _box(cx, top - 0.02 * s, yf, 0.4 * s)


def viridon_cracked(h, rng, cx, yf, k=1.0):
    """Viridon with the pane cracked: the 2017 leak"""
    mouth, fp = viridon(h, rng, cx, yf, k)
    s = 30 * k
    top = yf - s
    px, py = cx + 0.22 * s, top + 0.3 * s
    crack = [(px - 0.14 * s, py - 0.1 * s), (px - 0.04 * s, py - 0.02 * s), (px - 0.08 * s, py + 0.08 * s), (px + 0.03 * s, py + 0.12 * s), (px + 0.14 * s, py + 0.2 * s)]
    h.stroke(crack, "core", "ink", amp=0.35)
    h.stroke([(px - 0.04 * s, py - 0.02 * s), (px + 0.02 * s, py - 0.09 * s)], "orn", "ink", amp=0.3)
    return mouth, fp
