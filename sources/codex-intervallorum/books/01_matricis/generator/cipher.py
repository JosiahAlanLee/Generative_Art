"""The cipher hand: a substitution alphabet built from the sketching marks, with
charaktêres-style dot and ring terminals. Lines written in it are real text."""
import math

from core import arc_pts, spiral_pts, bezier, catmull, rot


def L(x1, y1, x2, y2):
    return ("p", [(x1, y1), (x2, y2)])


def P(*pts):
    return ("p", list(pts))


def C(*pts):
    return ("c", list(pts))


def A(cx, cy, r, a0, a1):
    return ("p", arc_pts(cx, cy, r, a0, a1, max(10, int(abs(a1 - a0) / 9))))


def D(x, y, r=0.07):
    return ("d", x, y, r)


def O(x, y, r=0.075):
    return ("o", x, y, r)


def T(cx, cy, w, h, up=True):
    if up:
        return C((cx, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2))
    return C((cx, cy + h / 2), (cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2))


def CR(*pts):
    return ("p", catmull(list(pts), 8))


def SP(cx, cy, r0, r1, a0, turns, hand=1):
    return ("p", spiral_pts(cx, cy, r0, r1, a0, turns, hand, n=int(40 * turns)))


G = {
    "a": (0.62, [T(0.31, 0.62, 0.56, 0.7), D(0.31, 0.74, 0.07)]),
    "b": (0.64, [L(0.08, 0.06, 0.08, 1.0), C((0.08, 0.45), (0.08, 0.8), (0.33, 0.625)),
                 C((0.6, 0.45), (0.6, 0.8), (0.33, 0.625)), D(0.08, 0.06, 0.06)]),
    "c": (0.66, [A(0.33, 0.63, 0.29, -45, 228), P((0.135, 0.42), (0.11, 0.3)), P((0.135, 0.42), (0.25, 0.4))]),
    "d": (0.46, [L(0.23, 0.36, 0.23, 1.0), O(0.23, 0.2, 0.1), L(0.08, 1.0, 0.38, 1.0)]),
    "e": (0.6, [L(0.17, 0.32, 0.17, 1.0), D(0.17, 0.16, 0.075), L(0.17, 0.7, 0.48, 0.42), O(0.52, 0.37, 0.065)]),
    "f": (0.6, [L(0.16, 0.04, 0.16, 1.0), L(0.16, 0.3, 0.5, 0.5), L(0.16, 0.56, 0.5, 0.76),
                D(0.52, 0.52, 0.06), D(0.52, 0.78, 0.06)]),
    "g": (0.6, [C((0.06, 0.3), (0.54, 0.3), (0.3, 0.64)), C((0.06, 0.98), (0.54, 0.98), (0.3, 0.64)),
                D(0.3, 0.64, 0.065)]),
    "h": (0.66, [L(0.04, 0.6, 0.62, 0.6), L(0.16, 0.65, 0.08, 0.82), L(0.32, 0.65, 0.24, 0.82),
                 L(0.48, 0.65, 0.4, 0.82), O(0.33, 0.38, 0.1)]),
    "i": (0.38, [L(0.19, 0.44, 0.19, 1.0), D(0.19, 0.25, 0.075)]),
    "j": (0.5, [L(0.33, 0.28, 0.33, 0.78), SP(0.2, 0.8, 0.13, 0.03, 0, 1.1, 1), D(0.33, 0.13, 0.07)]),
    "k": (0.64, [P((0.56, 0.32), (0.1, 0.32), (0.1, 1.0), (0.56, 1.0)), L(0.56, 1.0, 0.56, 0.83),
                 L(0.56, 0.32, 0.56, 0.49)]),
    "l": (0.44, [L(0.22, 0.02, 0.22, 1.0), L(0.06, 0.62, 0.38, 0.48), D(0.22, 1.0, 0.065)]),
    "m": (0.76, [T(0.2, 0.66, 0.34, 0.64), T(0.54, 0.66, 0.34, 0.64)]),
    "n": (0.66, [L(0.05, 0.36, 0.33, 0.66), L(0.05, 0.97, 0.33, 0.66), L(0.61, 0.36, 0.33, 0.66),
                 L(0.61, 0.97, 0.33, 0.66), D(0.33, 0.66, 0.075)]),
    "o": (0.64, [O(0.32, 0.64, 0.28), D(0.32, 0.64, 0.05)]),
    "p": (0.58, [L(0.42, 0.3, 0.42, 1.22), O(0.2, 1.06, 0.13), L(0.42, 0.3, 0.2, 0.3)]),
    "q": (0.68, [SP(0.34, 0.63, 0.31, 0.06, -100, 1.55, 1), CR((0.04, 0.5), (-0.06, 0.28), (0.02, 0.12))]),
    "r": (0.58, [L(0.13, 0.26, 0.13, 1.0), C((0.13, 0.26), (0.52, 0.41), (0.13, 0.56))]),
    "s": (0.56, [L(0.08, 0.98, 0.48, 0.36), O(0.12, 0.38, 0.075), D(0.44, 0.96, 0.07)]),
    "t": (0.66, [L(0.05, 0.3, 0.61, 0.3), C((0.17, 0.42), (0.49, 0.42), (0.33, 0.7)), L(0.33, 0.7, 0.33, 1.0),
                 D(0.05, 0.3, 0.055), D(0.61, 0.3, 0.055)]),
    "u": (0.64, [A(0.32, 0.58, 0.26, 0, 180), D(0.58, 0.58, 0.06), D(0.06, 0.58, 0.06), L(0.32, 0.84, 0.32, 1.02)]),
    "v": (0.62, [C((0.06, 0.4), (0.56, 0.4), (0.31, 0.98)), D(0.31, 0.24, 0.065)]),
    "w": (0.78, [A(0.21, 0.6, 0.16, 0, 180), A(0.55, 0.6, 0.16, 0, 180), D(0.05, 0.6, 0.055),
                 D(0.38, 0.6, 0.055), D(0.71, 0.6, 0.055)]),
    "x": (0.62, [A(0.62, 0.66, 0.42, 145, 215), A(0.0, 0.66, 0.42, -35, 35), L(0.12, 0.66, 0.5, 0.66),
                 O(0.31, 0.38, 0.06)]),
    "y": (0.66, [L(0.33, 1.0, 0.33, 0.66), CR((0.33, 0.66), (0.18, 0.52), (0.1, 0.36), (0.2, 0.28), (0.24, 0.38)),
                 CR((0.33, 0.66), (0.48, 0.52), (0.56, 0.36), (0.46, 0.28), (0.42, 0.38)), D(0.33, 1.0, 0.06)]),
    "z": (0.5, [P((0.1, 0.3), (0.4, 0.46), (0.1, 0.64), (0.4, 0.8), (0.1, 0.98)), D(0.4, 0.3, 0.055)]),
    ".": (0.24, [D(0.12, 0.95, 0.06)]),
    ",": (0.24, [P((0.14, 0.92), (0.1, 1.1))]),
    ";": (0.24, [D(0.12, 0.6, 0.05), P((0.14, 0.92), (0.1, 1.1))]),
    ":": (0.24, [D(0.12, 0.6, 0.05), D(0.12, 0.95, 0.05)]),
    "-": (0.36, [L(0.04, 0.66, 0.32, 0.66)]),
    "—": (0.5, [L(0.04, 0.66, 0.46, 0.66)]),
    "?": (0.36, [O(0.18, 0.5, 0.09), D(0.18, 0.95, 0.05)]),
}

SPACE = 0.44
TRACK = 0.17


def clean(text):
    t = text.lower()
    t = t.replace("’", "").replace("'", "").replace("“", "").replace("”", "").replace('"', "")
    t = t.replace("–", "—")
    out = []
    for ch in t:
        if ch in G or ch == " ":
            out.append(ch)
        elif ch.isdigit():
            continue
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def measure(text, size):
    t = clean(text)
    w = 0.0
    for ch in t:
        if ch == " ":
            w += SPACE
        else:
            w += G[ch][0] + TRACK
    return w * size


def wrap(text, size, width):
    words = clean(text).split(" ")
    lines, cur = [], ""
    for wd in words:
        cand = (cur + " " + wd).strip()
        if measure(cand, size) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def write(h, text, x, y, size, weight="cip", color="ink", rail=True, jit=True, rail_color=None):
    """y is the baseline. returns advance width in px."""
    rng = h.rng
    t = clean(text)
    cx = x
    word_start = x
    for i, ch in enumerate(t + " "):
        if ch == " ":
            if rail and cx - word_start > size * 0.3:
                ry = y + size * 0.16
                h.stroke([(word_start - size * 0.06, ry), (cx - size * 0.12, ry)], "hair", rail_color or color,
                         amp=0.15)
                h.dot(cx - size * 0.06, ry, size * 0.045, rail_color or color)
            cx += SPACE * size
            word_start = cx
            continue
        w, ops = G[ch]
        ang = math.radians(rng.uniform(-2.5, 2.5)) if jit else 0
        dy = rng.uniform(-0.025, 0.025) * size if jit else 0
        sc = size * (rng.uniform(0.96, 1.04) if jit else 1)
        piv = (w / 2, 0.6)

        def tf(p):
            q = rot(p, ang, piv)
            return (cx + q[0] * sc, y - size + q[1] * sc + dy)

        for op in ops:
            if op[0] == "p":
                h.stroke([tf(p) for p in op[1]], weight, color, amp=size * 0.012)
            elif op[0] == "c":
                h.stroke([tf(p) for p in op[1]], weight, color, closed=True, amp=size * 0.012)
            elif op[0] == "d":
                p = tf((op[1], op[2]))
                h.dot(p[0], p[1], op[3] * sc, color)
            elif op[0] == "o":
                p = tf((op[1], op[2]))
                h.ring(p[0], p[1], op[3] * sc, weight, color)
        cx += (w + TRACK) * size
    return cx - x - SPACE * size


def glyph_only(h, ch, x, y, size, weight="cip", color="ink"):
    """draw one glyph with baseline at y, no jitter (for keys)"""
    w, ops = G[ch]

    def tf(p):
        return (x + p[0] * size, y - size + p[1] * size)

    for op in ops:
        if op[0] == "p":
            h.stroke([tf(p) for p in op[1]], weight, color, amp=size * 0.008)
        elif op[0] == "c":
            h.stroke([tf(p) for p in op[1]], weight, color, closed=True, amp=size * 0.008)
        elif op[0] == "d":
            p = tf((op[1], op[2]))
            h.dot(p[0], p[1], op[3] * size, color)
        elif op[0] == "o":
            p = tf((op[1], op[2]))
            h.ring(p[0], p[1], op[3] * size, weight, color)
    return w * size
