"""Import stroke geometry from the books' own SVG plates (M / l / L / a / A / Z paths)
as polylines, so a plate can carry another book's seal as pen strokes."""
import math
import re


def _arc(p0, rx, ry, phi, large, sweep, p1, n=24):
    """SVG endpoint arc -> points (p0 excluded)"""
    x1, y1 = p0
    x2, y2 = p1
    if rx == 0 or ry == 0:
        return [p1]
    phi = math.radians(phi)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy
    lam = (x1p ** 2) / (rx ** 2) + (y1p ** 2) / (ry ** 2)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    coef = math.sqrt(max(0, num / den)) if den else 0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        d = ux * vx + uy * vy
        l = math.hypot(ux, uy) * math.hypot(vx, vy)
        a = math.acos(max(-1, min(1, d / l)))
        return -a if ux * vy - uy * vx < 0 else a
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(4, int(abs(dt) / (2 * math.pi) * n * 2))
    out = []
    for i in range(1, n + 1):
        t = t1 + dt * i / n
        x = cp * rx * math.cos(t) - sp * ry * math.sin(t) + cx
        y = sp * rx * math.cos(t) + cp * ry * math.sin(t) + cy
        out.append((x, y))
    return out


def parse_path(d):
    toks = re.findall(r"[MmLlHhVvAaZz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    polys, cur, pen, start = [], [], (0.0, 0.0), (0.0, 0.0)
    i, cmd = 0, None
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append(start)
                    polys.append(cur)
                    cur = []
                pen = start
            continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            x, y = float(toks[i]), float(toks[i + 1])
            i += 2
            if rel:
                x, y = pen[0] + x, pen[1] + y
            if len(cur) > 1:
                polys.append(cur)
            cur = [(x, y)]
            pen = start = (x, y)
            cmd = "l" if rel else "L"
        elif c == "L":
            x, y = float(toks[i]), float(toks[i + 1])
            i += 2
            if rel:
                x, y = pen[0] + x, pen[1] + y
            cur.append((x, y))
            pen = (x, y)
        elif c == "H":
            x = float(toks[i])
            i += 1
            x = pen[0] + x if rel else x
            cur.append((x, pen[1]))
            pen = (x, pen[1])
        elif c == "V":
            y = float(toks[i])
            i += 1
            y = pen[1] + y if rel else y
            cur.append((pen[0], y))
            pen = (pen[0], y)
        elif c == "A":
            rx, ry, phi, large, sweep, x, y = [float(v) for v in toks[i:i + 7]]
            i += 7
            if rel:
                x, y = pen[0] + x, pen[1] + y
            cur.extend(_arc(pen, rx, ry, phi, int(large), int(sweep), (x, y)))
            pen = (x, y)
        else:
            i += 1
    if len(cur) > 1:
        polys.append(cur)
    return polys


def strokes_from_svg(path, colors=None):
    """[(stroke_colour, stroke_width, polyline), ...] for every <path> in the file"""
    s = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"<path ([^>]*)/>", s):
        a = m.group(1)
        col = re.search(r'stroke="([^"]+)"', a)
        col = col.group(1) if col else "#000"
        if colors and col not in colors:
            continue
        w = re.search(r'stroke-width="([^"]+)"', a)
        d = re.search(r' d="([^"]*)"', a)
        if not d:
            continue
        for pl in parse_path(d.group(1)):
            out.append((col, float(w.group(1)) if w else 1.0, pl))
    return out


def place(polys, src_box, dst_centre, dst_size):
    """scale polylines from a source box (x, y, w, h) to fit dst_size (mm) centred at dst_centre"""
    sx, sy, sw, sh = src_box
    k = dst_size / max(sw, sh)
    cx, cy = sx + sw / 2, sy + sh / 2
    return [[(dst_centre[0] + (x - cx) * k, dst_centre[1] + (y - cy) * k) for x, y in pl] for pl in polys]
