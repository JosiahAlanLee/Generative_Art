"""Small figures for the building plates: a robed office-holder with any number of
arms, and a raised hand. Same stroke vocabulary as the Keeper, at a smaller scale."""
import math
import random

from plotkit import catmull, arc_pts, lerp, dist, Polygon, LineString, Point


def _flow(h, poly, rng, y0, y1, n, step=0.8):
    for k in range(n):
        u = (k + 0.5) / n
        pts = []
        y = y0
        while y <= y1:
            g = LineString([(0, y), (300, y)]).intersection(poly)
            if g.is_empty:
                y += step
                continue
            xs = [c[0] for part in (g.geoms if hasattr(g, "geoms") else [g]) for c in part.coords]
            pts.append((min(xs) + (max(xs) - min(xs)) * u, y))
            y += step
        if len(pts) > 2:
            h.stroke(pts, "hair", "ink", amp=0.3)


def hand_up(h, rng, x, y_base, size):
    """a raised open hand: wrist, palm arc, five fingers fanning up"""
    s = size
    h.stroke([(x - 0.5 * s * 0.22, y_base), (x - 0.5 * s * 0.22, y_base - 0.35 * s)], "orn", "ink", amp=0.2)
    h.stroke([(x + 0.5 * s * 0.22, y_base), (x + 0.5 * s * 0.22, y_base - 0.35 * s)], "orn", "ink", amp=0.2)
    palm_y = y_base - 0.35 * s
    h.stroke(arc_pts(x, palm_y, 0.3 * s, 180, 360, 14), "orn", "ink", amp=0.15)
    for k, ang in enumerate((-150, -118, -92, -66, -34)):
        a = math.radians(ang)
        L = s * (0.42 if k in (0, 4) else 0.58 if k in (1, 3) else 0.64)
        tip = (x + 0.22 * s * math.cos(a) + L * math.cos(a), palm_y + 0.2 * s * math.sin(a) + L * math.sin(a))
        base = (x + 0.26 * s * math.cos(a), palm_y + 0.22 * s * math.sin(a))
        h.stroke([base, tip], "orn", "ink", amp=0.25)
        h.dot(tip[0], tip[1], 0.22, "ink")


def robed_figure(h, rng, cx, y_feet, height, arms=2, raise_to=None, papers=True):
    """hooded, robed, with `arms` arms (half per side). Returns the raised hand's point."""
    s = height / 19.0
    y_top = y_feet - height
    # hood
    hc = (cx + 0.2 * s, y_top + 3.4 * s)
    hood_pts = []
    for i in range(40):
        th = math.radians(i * 9)
        x, y = 2.5 * s * math.cos(th), 3.2 * s * math.sin(th)
        a = math.radians(14)                                     # a slight forward tilt
        hood_pts.append((hc[0] + x * math.cos(a) - y * math.sin(a), hc[1] + x * math.sin(a) + y * math.cos(a)))
    hood_pts.append(hood_pts[0])
    h.stroke(hood_pts, "core", "ink", amp=0.3)
    # the hood's fall: a few lines down the back of the head
    for k in range(4):
        u = -1.9 + k * 0.55
        h.stroke([(hc[0] + u * s, hc[1] - 2.2 * s), (hc[0] + (u - 0.5) * s, hc[1] + 2.6 * s)], "hair", "ink", amp=0.3)
    # a notch for the face on the facing (right) side
    prof = [(hc[0] + 1.3 * s, hc[1] - 1.4 * s), (hc[0] + 2.4 * s, hc[1] - 0.2 * s), (hc[0] + 1.9 * s, hc[1] + 0.5 * s),
            (hc[0] + 2.1 * s, hc[1] + 1.1 * s), (hc[0] + 1.2 * s, hc[1] + 1.9 * s)]
    h.stroke(catmull(prof, 6), "orn", "ink", amp=0.2)
    h.dot(hc[0] + 1.1 * s, hc[1] - 0.3 * s, 0.22, "ink")
    # robe
    y_s = y_top + 6.2 * s
    robe = [(cx - 3.4 * s, y_s), (cx + 3.4 * s, y_s), (cx + 5.6 * s, y_feet), (cx - 5.6 * s, y_feet)]
    rp = Polygon(robe)
    h.stroke(robe, "orn", "ink", closed=True, amp=0.3)
    _flow(h, rp.buffer(-0.25 * s), rng, y_s + 0.4, y_feet - 0.3, max(6, int(9 * s)))
    h.stroke([(hc[0] - 1.2 * s, hc[1] + 2.7 * s), (cx - 1.0 * s, y_s)], "hair", "ink", amp=0.2)
    h.stroke([(hc[0] + 1.2 * s, hc[1] + 2.7 * s), (cx + 1.0 * s, y_s)], "hair", "ink", amp=0.2)
    # arms: sleeves as tapered ribbons from the shoulder line to hand points
    per_side = max(1, arms // 2)
    raised = None
    for side in (-1, 1):
        for k in range(per_side):
            sh = (cx + side * 2.8 * s, y_s + 0.8 * s + k * 2.6 * s)
            hp = (cx + side * (8.6 + k * 0.6) * s, y_s - 1.6 * s + k * 4.2 * s)
            if side == 1 and k == 0 and raise_to:
                hp = raise_to
                raised = hp
            mid = lerp(sh, hp, 0.55)
            mid = (mid[0], mid[1] + (1.2 * s if not (side == 1 and k == 0 and raise_to) else -1.5 * s))
            c = catmull([sh, mid, hp], 8)
            # ribbon
            w0, w1 = 1.5 * s, 0.7 * s
            left, right = [], []
            for i, p in enumerate(c):
                j0, j1 = max(0, i - 1), min(len(c) - 1, i + 1)
                tx, ty = c[j1][0] - c[j0][0], c[j1][1] - c[j0][1]
                m = math.hypot(tx, ty) or 1
                w = (w0 + (w1 - w0) * i / (len(c) - 1)) / 2
                left.append((p[0] - ty / m * w, p[1] + tx / m * w))
                right.append((p[0] + ty / m * w, p[1] - tx / m * w))
            h.stroke(left, "orn", "ink", amp=0.25)
            h.stroke(right, "orn", "ink", amp=0.25)
            for u in (0.33, 0.66):
                h.stroke([lerp(a, b, u) for a, b in zip(left, right)], "hair", "ink", amp=0.25)
            # the hand: three fingers; a paper in alternate hands
            d = (hp[0] - c[-2][0], hp[1] - c[-2][1])
            m = math.hypot(*d) or 1
            d = (d[0] / m, d[1] / m)
            for ang in (-28, 0, 28):
                a = math.radians(ang)
                fx = d[0] * math.cos(a) - d[1] * math.sin(a)
                fy = d[0] * math.sin(a) + d[1] * math.cos(a)
                h.stroke([hp, (hp[0] + fx * 1.3 * s, hp[1] + fy * 1.3 * s)], "orn", "ink", amp=0.2)
            if papers and k == 1 and not (side == 1 and k == 0 and raise_to):
                px, py = hp[0] + side * 1.6 * s, hp[1] - 1.2 * s
                h.stroke([(px - 1.3 * s, py - 1.7 * s), (px + 1.3 * s, py - 1.7 * s), (px + 1.3 * s, py + 1.7 * s), (px - 1.3 * s, py + 1.7 * s)],
                         "orn", "ink", closed=True, amp=0.15)
                for ly in (-0.8, 0, 0.8):
                    h.straight([(px - 0.8 * s, py + ly * s), (px + 0.8 * s, py + ly * s)], "hair", "ink")
    return raised or (cx + 8.0 * s, y_s)
