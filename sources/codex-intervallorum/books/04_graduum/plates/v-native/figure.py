"""The Keeper: a hooded, hunched figure in right profile, built from control
curves and dressed in flow-lines that follow the fall of the cloth."""
import math
import random

from plotkit import catmull, bezier, arc_pts, lerp, dist, resample, Polygon, LineString, Point, voronoi_net


def edge_fn(poly, y, side):
    """x of the back (min) or front (max) edge of poly at height y, or None"""
    g = LineString([(0, y), (210, y)]).intersection(poly)
    if g.is_empty:
        return None
    xs = []
    for part in (g.geoms if hasattr(g, "geoms") else [g]):
        xs.extend(c[0] for c in part.coords)
    return min(xs) if side == "back" else max(xs)


def robe_outline():
    """robe silhouette, clockwise from the back of the neck; hunch forward, hem to the ground"""
    back = [(108, 104), (103.5, 118), (100.5, 136), (99, 156), (97.5, 176), (95.5, 196), (93.5, 212)]
    front = [(131, 104), (128.5, 118), (125, 136), (124, 156), (125.5, 176), (129.5, 196), (136, 212)]
    hem = [(93.5, 212), (104, 213.5), (116, 212.5), (127, 213.8), (136, 212)]
    top = [(131, 104), (127, 101.2), (119, 100.2), (111, 101.4), (108, 104)]
    pts = catmull(back, 8) + catmull(hem, 6)[1:] + catmull(front[::-1], 8)[1:] + catmull(top, 6)[1:]
    return pts


HOOD_RX, HOOD_RY, HOOD_TILT = 11.0, 13.4, 34   # tilt: degrees clockwise on the page (head bowed forward)


def head_local(p, hc):
    """local head frame (x = facing direction, y = down the skull) -> page"""
    a = math.radians(HOOD_TILT)
    x, y = p
    return (hc[0] + x * math.cos(a) - y * math.sin(a), hc[1] + x * math.sin(a) + y * math.cos(a))


def hood_outline(hc):
    """hood as a tilted egg around the head with a concave opening on the facing side"""
    pts = []
    for i in range(96):
        th = math.radians(i * 360 / 96)
        x, y = HOOD_RX * math.cos(th), HOOD_RY * math.sin(th)
        d = math.degrees(th)
        d = d - 360 if d > 180 else d
        if -58 < d < 58:                       # the opening: pull the rim inward
            k = 0.5 * (1 + math.cos(math.pi * d / 58))
            x *= 1 - 0.34 * k
            y *= 1 - 0.10 * k
        pts.append(head_local((x, y), hc))
    return pts + [pts[0]]


def sleeve_path():
    return [(126, 110), (135, 116), (144, 112), (151, 103), (156, 97.5)]


def ribbon(path, w0, w1, n=10):
    c = catmull(path, n)
    L = [0.0]
    for i in range(1, len(c)):
        L.append(L[-1] + dist(c[i - 1], c[i]))
    tot = L[-1] or 1
    left, right = [], []
    for i, p in enumerate(c):
        j0, j1 = max(0, i - 1), min(len(c) - 1, i + 1)
        t_ = (c[j1][0] - c[j0][0], c[j1][1] - c[j0][1])
        m = math.hypot(*t_) or 1
        nx, ny = -t_[1] / m, t_[0] / m
        w = (w0 + (w1 - w0) * L[i] / tot) / 2
        left.append((p[0] + nx * w, p[1] + ny * w))
        right.append((p[0] - nx * w, p[1] - ny * w))
    return left, right, c


def flow_lines(poly, rng, y_top, y_bot, n_lines, wander=0.10, step=1.5):
    """lines that interpolate between the back and front edges of poly. One shared wander
    field, scaled toward the middle, so the lines drift like cloth and never cross."""
    ph = [rng.uniform(0, 6.283) for _ in range(3)]
    wl = [rng.uniform(48, 70), rng.uniform(20, 30), rng.uniform(90, 130)]

    def off(y):
        return (0.55 * math.sin(y / wl[0] * 6.283 + ph[0]) + 0.3 * math.sin(y / wl[1] * 6.283 + ph[1])
                + 0.15 * math.sin(y / wl[2] * 6.283 + ph[2]))

    edges = {}
    y = y_top
    while y <= y_bot:
        edges[round(y, 3)] = (edge_fn(poly, y, "back"), edge_fn(poly, y, "front"))
        y += step
    out = []
    for k in range(n_lines):
        u0 = (k + 0.5) / n_lines
        u0 = 0.5 + 0.5 * math.copysign(abs(2 * u0 - 1) ** 0.8, 2 * u0 - 1)   # crowd toward the edges
        jit = rng.uniform(-0.25, 0.25) / n_lines
        pts = []
        for yk, (b, f) in edges.items():
            if b is None or f is None:
                continue
            u = u0 + jit + wander * (1 - abs(2 * u0 - 1)) * off(yk)
            u = min(0.985, max(0.015, u))
            pts.append((b + (f - b) * u, yk))
        if len(pts) > 2:
            out.append(pts)
    return out


def clip_polyline(pts, geom):
    g = LineString(pts).intersection(geom)
    out = []
    for part in (g.geoms if hasattr(g, "geoms") else [g]):
        if part.geom_type == "LineString" and part.length > 0.8:
            out.append(list(part.coords))
    return out


def draw_keeper(h, rng, bars_y, chest_ring, dial_occluder):
    """draws the figure; returns (pinch point, occluder polygon for the dial)"""
    robe = Polygon(robe_outline()).buffer(0)
    hc = (117.5, 92.5)
    hood = Polygon(hood_outline(hc)).buffer(0)
    sl_l, sl_r, sl_c = ribbon(sleeve_path(), 8.5, 4.2)
    sleeve = Polygon(sl_l + sl_r[::-1]).buffer(0)
    cx, cy, cr = chest_ring

    # --- bars: the body is absent across seven intervals
    bars = []
    cut = robe
    for i, y in enumerate(bars_y):
        b, f = edge_fn(robe, y, "back"), edge_fn(robe, y, "front")
        ov = 4.5 + 3.0 * (0.5 + 0.5 * math.sin(i * 2.1))
        bars.append((b - ov, f + ov, y))
        cut = cut.difference(Polygon([(b - 10, y - 1.2), (f + 10, y - 1.2), (f + 10, y + 1.2), (b - 10, y + 1.2)]))
    cut = cut.difference(Point(cx, cy).buffer(cr + 1.3))
    cut = cut.difference(hood.buffer(0.5))
    cut = cut.difference(sleeve.buffer(0.7))

    # --- the fall of the robe: flow-lines following the edges, clipped to the cut body
    lines = flow_lines(robe, rng, 103, 211.2, 46, wander=0.11)
    for pts in lines:
        for seg in clip_polyline(pts, cut):
            h.stroke(seg, "hair", "ink", amp=0.35)
    # hem: threads continue past the hem and end in coils
    for k in range(30):
        x = rng.uniform(95, 135)
        y0 = 212.4 + 1.2 * math.sin((x - 93) / 43 * 6.283)
        y1 = y0 + rng.uniform(1.0, 9.0)
        col = "red" if rng.random() < 0.07 else "ink"
        h.stroke([(x, y0), (x, y1)], "hair", col, amp=0.4)
        h.dot(x, y1 + 0.4, 0.3 if col == "ink" else 0.36, col)

    # --- sleeve: lines along the arm
    for k in range(9):
        u = (k + 0.5) / 9
        pts = [lerp(a, b, u) for a, b in zip(sl_l, sl_r)]
        h.stroke(pts, "hair", "ink", amp=0.4)
    h.stroke(sl_l, "orn", "ink", amp=0.4)
    h.stroke(sl_r, "orn", "ink", amp=0.4)
    cuff = (sl_l[-1], sl_r[-1])
    h.stroke(list(cuff), "orn", "ink", amp=0.2)

    # --- hood: drape lines following the hood loop, then the net on the crown
    hood_pts = hood_outline(hc)
    h.stroke(hood_pts, "core", "ink", amp=0.4)
    # the face opening: an oval on the facing side, left empty but for the profile
    opening = Polygon([head_local((5.2 + 5.6 * math.cos(math.radians(a)), 0.8 + 8.2 * math.sin(math.radians(a))), hc)
                       for a in range(0, 360, 8)])
    hood_cloth = Polygon(hood_pts).buffer(-0.9).difference(opening.buffer(0.8))
    # the crown carries the net; the rest of the hood falls like the robe
    crown_zone = Polygon([head_local(p, hc) for p in ((-14, -16), (14, -16), (14, -7), (-14, -7))])
    crown = hood_cloth.intersection(crown_zone)
    voronoi_net(h, crown, 24, rng, "hair", "ink")
    hminy, hmaxy = hood_cloth.bounds[1], hood_cloth.bounds[3]
    for pts in flow_lines(hood_cloth.difference(crown_zone), rng, hminy, hmaxy + 1, 16, wander=0.08, step=1.0):
        for seg in clip_polyline(pts, hood_cloth.difference(crown_zone.buffer(0.3))):
            h.stroke(seg, "hair", "ink", amp=0.35)

    # --- face in the opening (local frame: +x faces, +y down the skull)
    prof = [(5.0, -6.4), (6.9, -3.6), (9.6, -0.4), (7.4, 1.1), (8.0, 3.0), (6.3, 5.2), (3.4, 7.2), (0.6, 8.0)]
    h.stroke(catmull([head_local(p, hc) for p in prof], 8), "core", "ink", amp=0.3)
    ex, ey = head_local((3.8, -2.9), hc)
    h.ring(ex, ey, 1.05, "orn", "ink")
    h.dot(ex, ey, 0.32, "ink")
    h.stroke([head_local((1.4, -4.9), hc), head_local((5.6, -5.2), hc)], "hair", "ink", amp=0.2)   # brow
    # beard: a few threads falling from the jaw, page-vertical
    for k in range(5):
        p = head_local((0.8 + k * 0.8, 7.4 + k * 0.25), hc)
        h.stroke([p, (p[0] + rng.uniform(-0.6, 0.6), p[1] + rng.uniform(3, 8))], "hair", "ink", amp=0.6)

    # --- outlines of the cut body (each remaining piece)
    for part in (cut.geoms if hasattr(cut, "geoms") else [cut]):
        h.stroke(list(part.exterior.coords), "orn", "ink", amp=0.5)

    # --- bars as double rules with coil ends
    page = Polygon([(0, 0), (210, 0), (210, 297), (0, 297)]).difference(sleeve.buffer(0.9)).difference(Point(cx, cy).buffer(cr + 0.9))
    for i, (x0, x1, y) in enumerate(bars):
        for dy in (-0.85, 0.85):
            for seg in clip_polyline([(x0, y + dy), (x1, y + dy)], page):
                h.straight(seg, "hair", "ink")
        h.dot(x0 - 0.7, y, 0.42, "ink")
        if page.contains(Point(x1 + 0.7, y)):
            h.dot(x1 + 0.7, y, 0.42, "ink")

    # --- the crescent crest: worn behind the crown, horns toward the facing side
    big = Point(head_local((-3.0, -9.5), hc)).buffer(17.5, 96)
    bite = Point(head_local((2.4, -12.5), hc)).buffer(15.2, 96)
    crescent = big.difference(bite).difference(hood.buffer(0.7))
    for part in (crescent.geoms if hasattr(crescent, "geoms") else [crescent]):
        if part.area < 2:
            continue
        h.stroke(list(part.exterior.coords), "core", "ink", amp=0.4)
        voronoi_net(h, part.buffer(-0.6), 34, rng, "hair", "ink")
        # threads hanging from the lower edge of the crest
        minx, miny, maxx, maxy = part.bounds
        for k in range(14):
            x = rng.uniform(minx + 1, min(maxx - 1, hc[0] - 3))     # only from the part behind the head
            col = LineString([(x, miny), (x, maxy + 1)]).intersection(part)
            if col.is_empty:
                continue
            ys = [c[1] for g in (col.geoms if hasattr(col, "geoms") else [col]) for c in g.coords]
            y0 = max(ys)
            y1 = y0 + rng.uniform(1.5, 7.0)
            if hood.buffer(0.5).contains(Point(x, y1)):
                continue
            h.stroke([(x, y0), (x, y1)], "hair", "ink", amp=0.4)
            h.dot(x, y1 + 0.35, 0.3, "ink")

    # --- the front hand: fingers pinching the thread
    c0 = lerp(*cuff, 0.5)
    pinch = (c0[0] + 6.0, c0[1] - 0.8)
    # three fingers from the cuff curving in to the pinch, a thumb from below
    for u, bulge in ((0.22, -2.6), (0.5, -1.2), (0.78, 0.6)):
        base = lerp(*cuff, u)
        mid = (lerp(base, pinch, 0.5)[0] + 0.6, lerp(base, pinch, 0.5)[1] + bulge)
        h.stroke(catmull([base, mid, pinch], 7), "orn", "ink", amp=0.4)
        h.dot(mid[0], mid[1], 0.26, "ink")
    tb = lerp(*cuff, 0.95)
    h.stroke(catmull([tb, (tb[0] + 2.4, tb[1] + 2.4), (pinch[0] - 0.6, pinch[1] + 1.2)], 7), "orn", "ink", amp=0.4)

    occluder = hood.union(sleeve).buffer(0.9)   # the dial on the chest is clipped by the hood and sleeve only
    return pinch, occluder
