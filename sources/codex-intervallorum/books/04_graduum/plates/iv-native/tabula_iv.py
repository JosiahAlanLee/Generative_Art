"""Clavicula Graduum - Tabula IV - The Observer's Ladder (native vector plate).

The same rate data three times: twenty-four processes, each a bar as tall as the log of its
interval, one slope. In the first panel a surveyor has cut it into four terraces; in the
second, another has cut it into six; the third panel holds the bars and the slope and nothing
else, for a third observer. A terrace sits at the slowest member of its group, since the
slower constrains the faster. Severion, whose pans are both marked normal, keeps the
third panel. The plate carries the tenth claim and does not resolve it.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
sys.path.insert(0, os.path.join(REPO, "books", "04_graduum", "plates", "vii-native"))
sys.path.insert(0, os.path.join(REPO, "books", "04_graduum", "plates", "viii-native"))
from plate import Plate, validate  # noqa: E402
from plotkit import catmull  # noqa: E402
from figures import robed_figure  # noqa: E402
import apparatus as ap  # noqa: E402
import marks  # noqa: E402

N = 24
X0, X1 = 44.0, 186.0
PANELS = [(122.0, "FOUR", [6, 12, 18, 24]), (174.0, "SIX", [4, 8, 12, 16, 20, 24]), (226.0, "", [])]   # floor y, count, cut points
HMAX = 34.0


def intervals(rng):
    """twenty-four intervals, log-spaced from an hour to a decade, with the noise of real data"""
    out = []
    for i in range(N):
        t = 10 ** (i / (N - 1) * 4.0 + rng.gauss(0, 0.18))
        out.append(t)
    return out


def bar_heights(ts):
    return [4.0 + (HMAX - 4.0) * max(0.0, min(1.0, math.log10(t) / 4.0)) for t in ts]


def panel(P, floor, hs, cuts, label, k):
    h, rng = P.art, P.rng
    pitch = (X1 - X0) / N
    xs = [X0 + (i + 0.5) * pitch for i in range(N)]
    h.straight([(X0 - 4, floor), (X1 + 2, floor)], "core", "ink")
    h.straight([(X0 - 4, floor + 1.1), (X1 + 2, floor + 1.1)], "hair", "ink")
    for x, hh in zip(xs, hs):
        h.stroke([(x - 0.8, floor), (x - 0.8, floor - hh)], "orn", "ink", amp=0.1)
        h.stroke([(x + 0.8, floor), (x + 0.8, floor - hh)], "orn", "ink", amp=0.1)
        h.stroke([(x - 0.8, floor - hh), (x + 0.8, floor - hh)], "orn", "ink", amp=0.1)
        for yy in range(int(hh / 2.2)):
            h.stroke([(x - 0.8, floor - 1.6 - yy * 2.2), (x + 0.8, floor - 2.4 - yy * 2.2)], "hair", "ink", amp=0.1)
    # the slope itself: the continuous thing, as three flowing lines through the bar tops
    for u in (-0.7, 0.0, 0.7):
        pts = [(x, floor - hh - 2.2 + u + rng.uniform(-0.5, 0.5)) for x, hh in zip(xs, hs)]
        h.stroke(catmull(pts, 4), "hair", "ink", amp=0.3)
    # the terraces: one per group, at the slowest member; risers between
    prev_end, prev_top = None, None
    start = 0
    for ci, end in enumerate(cuts):
        top = floor - max(hs[start:end]) - 5.0
        xa, xb = xs[start] - pitch * 0.45, xs[end - 1] + pitch * 0.45
        h.stroke([(xa, top), (xb, top)], "core", "ink", amp=0.15)
        marks.dotted(h, [(xa, top - 1.2), (xb, top - 1.2)], 2.4, 0.26, skip_ends=False)
        if prev_top is not None:
            h.stroke([(prev_end, prev_top), (xa, prev_top), (xa, top)], "core", "ink", amp=0.15)
        marks.asterisk(h, xb, top, 1.0, 8, weight="hair")
        prev_end, prev_top = xb, top
        start = end
    # the surveyor and the count, which is an institution
    if cuts:
        robed_figure(h, rng, cx=X0 - 18, y_feet=floor - 0.6, height=16.0, arms=2, raise_to=(X0 - 7, floor - 12), papers=False)
        marks.sig_boundary(h, X0 - 10, floor - 26, 4.0, orn=0)
        P.label(str(len(cuts)), X0 - 4.6, floor - 24.9, 2.5)
        P.label(f"{label} TERRACES", X0 - 4, floor + 5.6, 2.5)
    else:
        marks.sig_boundary(h, X0 - 10, floor - 26, 4.0, orn=0)
        ap.severion(h, rng, X0 - 20, floor - 0.6, 0.55)
        P.label("A THIRD OBSERVER", X0 - 4, floor + 5.6, 2.5)
    P.label(["A", "B", "C"][k], X1 + 2, floor + 5.6, 2.5, "right")


def main(out_dir):
    P = Plate("IV", "The Observer's Ladder", "THE NUMBER OF LEVELS IS A PROPERTY OF THE DESCRIPTION", "iv-observers-ladder",
              "Say what the terraces are for.", 4, "ALL OBSERVERS DRAW THE SAME STEPS", 1982,
              strap="ONE SLOPE / FOUR TERRACES / SIX TERRACES / A THIRD COLUMN")
    ts = intervals(random.Random(1982))
    hs = bar_heights(ts)
    for k, (floor, label, cuts) in enumerate(PANELS):
        panel(P, floor, hs, cuts, label, k)
    P.label("THE SAME TWENTY-FOUR RATES, THREE TIMES", X1 + 2, 78, 2.5, "right")
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    P.export(out_dir, {"intervals_log10": [round(math.log10(t), 2) for t in ts], "panels": [(f, c) for f, _, c in PANELS]})


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    main(out)
    validate(out)
