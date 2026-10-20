"""The fourth carrier: a biliteral cipher after Bacon (De augmentis, 1623), five marks
per letter, each mark in one of two forms, riding in marks the plate has anyway.

Decisions (16 Oct 2026), recorded in brief/PLATES.md:
  1. Carrier by plate class. Figure plates: marks of the drawing (ground blades, hatch).
     Apparatus plates: the frame drawn as a scale, its ticks the marks. Key plates: the
     lettering, in two forms of the hand, no marks added.
  2. Form. On figure plates the form is geometric (a dot head present or absent), so the
     black pass is complete and red stays decoration. On apparatus plates the form is the
     ink (black a, red b), so the red marks read as calibration; the black pass then
     shows the message as gaps, which is stated on the Clavis.
  3. Table. Codes are weighted by English frequency so the b-form stays sparse: space is
     00000, the five commonest letters have one b, the next ten two, and so on; the stop
     is 11111. This is in Bacon's manner and is not his table.
  4. Message. Each plate's hidden text is the falsifier of the claim the plate draws.
  5. Reading. Marks are read in the order the drawing gives (a ground left to right, a
     frame clockwise from the top-left corner, lettering in reading order). No start mark
     is added; the Clavis says where to begin.
"""
import math

FREQ = "ETAOINSHRDLCUMWFGYPBVKJXQZ"
TABLE = {" ": 0}
_codes = sorted(range(1, 31), key=lambda c: (bin(c).count("1"), c))   # popcount 1..4, ascending
for _ch, _c in zip(FREQ, _codes):
    TABLE[_ch] = _c
STOP = 31
INV = {v: k for k, v in TABLE.items()}


def codes(text):
    out = [TABLE[ch] for ch in text.upper() if ch in TABLE]
    out.append(STOP)
    return out


def bits(text):
    return [(c >> (4 - k)) & 1 for c in codes(text) for k in range(5)]


def decode(bitlist):
    """five bits at a time until the stop"""
    out = []
    for i in range(0, len(bitlist) - 4, 5):
        c = 0
        for b in bitlist[i:i + 5]:
            c = (c << 1) | b
        if c == STOP:
            break
        out.append(INV.get(c, "?"))
    return "".join(out)


def b_fraction(text):
    bl = bits(text)
    return sum(bl) / len(bl)


# ------------------------------------------------------------- frame scale --

def scale_positions(frame, pitch):
    """tick positions along the frame, clockwise from the top-left corner: (x, y, side, k)
    where k counts from the corner along each side."""
    x0, y0, x1, y1 = frame
    out = []
    for (ax, ay, bx, by, side) in ((x0, y0, x1, y0, "top"), (x1, y0, x1, y1, "right"),
                                   (x1, y1, x0, y1, "bottom"), (x0, y1, x0, y0, "left")):
        L = math.hypot(bx - ax, by - ay)
        n = int(L // pitch)
        ux, uy = (bx - ax) / L, (by - ay) / L
        for k in range(1, n):                       # corners themselves carry no tick
            out.append((ax + ux * k * pitch, ay + uy * k * pitch, side, k))
    return out


def scale_frame(h, frame, text, pitch=2.5, short=1.0, long=2.0, long_every=10, attr="tick", weight="hair"):
    """the frame as a rule: a tick every `pitch` mm inward from the frame line, every tenth
    longer (periodic, independent of the text). The ink carries the bit: black a, red b.
    Returns (carrier_marks, total_marks)."""
    pos = scale_positions(frame, pitch)
    bl = bits(text)
    if len(bl) > len(pos):
        raise ValueError(f"message needs {len(bl)} ticks, frame has {len(pos)}")
    inward = {"top": (0, 1), "right": (-1, 0), "bottom": (0, -1), "left": (1, 0)}
    for i, (x, y, side, k) in enumerate(pos):
        b = bl[i] if i < len(bl) else 0
        L = long if k % long_every == 0 else short
        dx, dy = inward[side]
        h.straight([(x, y), (x + dx * L, y + dy * L)], weight, "red" if b else "ink", attrs=f' data-{attr}="{i}"')
    return len(bl), len(pos)
