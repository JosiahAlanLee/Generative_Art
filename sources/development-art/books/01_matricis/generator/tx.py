"""The twelve-sign transcription hand (Astra's key): base mark I–XII plus a tally of 1–3 strokes."""
import math
import sys

from core import arc_pts, spiral_pts, bezier

LETTERS = {}
for t, row in ((1, "ABCDEFGHIJKL"), (2, "MNOPQRSTUVWX"), (3, "YZ")):
    for i, ch in enumerate(row):
        LETTERS[ch] = (i + 1, t)
INV = {v: k for k, v in LETTERS.items()}
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def normalize(text):
    return "".join(ch for ch in text.upper() if ch.isalpha() or ch == " ").split()


def encode(text):
    """list of words, each a list of (base, tally)"""
    return [[LETTERS[ch] for ch in w] for w in normalize(text)]


def decode(words):
    return " ".join("".join(INV[t] for t in w) for w in words)


def codes(text):
    return " / ".join(" ".join(f"{b:02d}:{t}" for b, t in w) for w in encode(text))


def mark(h, base, x, y, s, weight="orn", color="ink"):
    """draw base mark `base` (1..12) in the box (x, y, s, s)"""
    P = lambda u, v: (x + u * s, y + v * s)
    if base == 1:
        h.dot(*P(0.5, 0.5), 0.17 * s, color)
    elif base == 2:
        h.ring(*P(0.5, 0.5), 0.2 * s, weight, color)
    elif base == 3:
        for k in range(8):
            a0 = k * 45 + 8
            h.stroke([P(0.5 + 0.38 * math.cos(math.radians(a)), 0.5 + 0.38 * math.sin(math.radians(a)))
                      for a in range(int(a0), int(a0 + 28), 4)], weight, color)
        h.dot(*P(0.4, 0.56), 0.06 * s, color)
        h.dot(*P(0.6, 0.42), 0.06 * s, color)
    elif base == 4:
        h.stroke([P(0.5, 0.12), P(0.88, 0.84), P(0.12, 0.84)], weight, color, closed=True)
    elif base == 5:
        for (u, v) in ((0.08, 0.22), (0.08, 0.78), (0.92, 0.22), (0.92, 0.78)):
            h.stroke([P(u, v), P(0.5, 0.5)], weight, color)
        h.dot(*P(0.5, 0.5), 0.085 * s, color)
    elif base == 6:
        pts = [P(0.5 + 0.32 * math.cos(math.radians(a)), 0.5 + 0.32 * math.sin(math.radians(a))) for a in range(-60, 252, 6)]
        h.stroke(pts, weight, color)
        e = pts[-1]
        h.stroke([(e[0] - 0.13 * s, e[1] - 0.02 * s), e, (e[0] + 0.02 * s, e[1] - 0.14 * s)], weight, color)
    elif base == 7:
        pts = []
        for i in range(90):
            t = i / 89
            a = math.radians(90 + t * 1.75 * 360)
            r = (0.07 + 0.31 * t) * s
            pts.append((x + 0.5 * s + r * math.cos(a), y + 0.5 * s + r * math.sin(a)))
        h.stroke(pts, weight, color)
    elif base == 8:
        h.stroke([P(0.06, 0.74), P(0.94, 0.74)], weight, color)
        h.stroke(bezier(P(0.32, 0.74), P(0.6, 0.74), P(0.66, 0.3), P(0.92, 0.28), 20), weight, color)
    elif base == 9:
        h.stroke([P(0.06, 0.74), P(0.34, 0.74)], weight, color)
        for k in range(3):
            u0 = 0.4 + k * 0.19
            h.stroke([P(u0, 0.74), P(u0 + 0.1, 0.74)], weight, color)
        h.stroke([P(0.6, 0.64), P(0.78, 0.84)], weight, color)
        h.stroke([P(0.78, 0.64), P(0.6, 0.84)], weight, color)
        h.stroke(bezier(P(0.34, 0.74), P(0.5, 0.74), P(0.52, 0.3), P(0.82, 0.24), 20), weight, color)
    elif base == 10:
        h.stroke([P(0.08, 0.58), P(0.92, 0.58)], weight, color)
        for k in range(5):
            u = 0.18 + k * 0.17
            h.stroke([P(u, 0.62), P(u - 0.09, 0.84)], "hair", color)
        h.dot(*P(0.5, 0.32), 0.075 * s, color)
    elif base == 11:
        h.stroke([P(0.06, 0.48), P(0.36, 0.48), P(0.36, 0.78), P(0.06, 0.78)], weight, color, closed=True)
        h.stroke([P(0.42, 0.63), P(0.78, 0.63)], weight, color)
        h.dot(*P(0.88, 0.63), 0.07 * s, color)
        h.stroke(bezier(P(0.88, 0.54), P(0.88, 0.18), P(0.21, 0.16), P(0.21, 0.42), 20), weight, color)
    elif base == 12:
        h.stroke([P(0.76, 0.18), P(0.2, 0.18), P(0.2, 0.84), P(0.76, 0.84)], weight, color)
        h.stroke([P(0.76, 0.18), P(0.76, 0.36)], weight, color)
        h.stroke([P(0.76, 0.84), P(0.76, 0.66)], weight, color)


def tally(h, n, x, y, s, color="ink"):
    for i in range(n):
        u = x + (1.06 + i * 0.14) * s
        h.stroke([(u, y + 0.6 * s), (u, y + 0.94 * s)], "orn", color, amp=0.02)


def token_width(t, s):
    return (1.06 + 0.14 * t + 0.16) * s


def write(h, text, x, y, s, word_gap=0.55, color="ink"):
    """draw a passage; returns its width"""
    cx = x
    for wi, w in enumerate(encode(text)):
        if wi:
            cx += word_gap * s
        for (b, t) in w:
            mark(h, b, cx, y, s, "orn", color)
            tally(h, t, cx, y, s, color)
            cx += token_width(t, s)
    return cx - x


def width(text, s, word_gap=0.55):
    words = encode(text)
    return sum(token_width(t, s) for w in words for (b, t) in w) + word_gap * s * (len(words) - 1)
