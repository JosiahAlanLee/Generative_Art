"""Clavicula Graduum - Tabula I - The Nine and the Seven (native vector plate).

Three concentric triads: the nine choirs as Dionysius ordered them, their centre left empty.
Seven stations threaded through them off-centre on a spiral: Book III's seven offices in order
of permission, each carrying its own seal. No station falls on a ring; the misregistration is
drawn, not corrected. Illumination descends from the outer ring inward and stops at every
triad boundary: nothing skips a level, and nothing ascends.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
from plate import Plate, validate  # noqa: E402
from plotkit import arc_pts, catmull  # noqa: E402
from svgimport import strokes_from_svg, place  # noqa: E402
import marks  # noqa: E402

C1 = (100.0, 135.0)                                  # the choirs' centre: empty
RINGS = [14, 19, 24, 33, 38, 43, 52, 57, 62]         # three triads
CHOIRS = ["SERAPHIM", "CHERUBIM", "THRONI", "DOMINATIONES", "VIRTUTES", "POTESTATES", "PRINCIPATUS", "ARCHANGELI", "ANGELI"]
OFFICES = ["FORAS", "VASSAGO", "GREMORY", "BUNE", "OROBAS", "PAIMON", "BAEL"]
SEALS = os.path.join(REPO, "books", "03_escalationum", "output", "plates")


# the seven, in order of permission, each on the only ground the rings leave: the two gaps
# between triads, and outside the ninth. (radius from C1, angle)
STATIONS = [(67.0, 95), (47.5, 150), (28.5, 230), (47.5, 300), (28.5, 20), (47.5, 60), (67.0, 160)]


def station_points():
    return [(C1[0] + r * math.cos(math.radians(a)), C1[1] + r * math.sin(math.radians(a))) for r, a in STATIONS]


def main(out_dir):
    P = Plate("I", "The Nine and the Seven", "A RANK HIERARCHY OVER A RATE HIERARCHY", "i-nine-and-seven",
              "They were never counting the same thing.", 1, "THE TWO COUNTS ALIGN", 500,
              strap="NINE CHOIRS / SEVEN STATIONS / NO RING SHARED")
    h, rng = P.art, P.rng
    # the nine rings
    for i, R in enumerate(RINGS):
        h.stroke(arc_pts(C1[0], C1[1], R, 0, 360, max(60, int(R * 3))), "core" if i % 3 == 2 else "orn", "ink", amp=0.12)
    # illumination descends: three lines from the outer ring inward, stopping at each triad boundary
    for (r0, r1) in ((62, 52), (43, 33), (24, 14)):
        for u in (-1.6, 0.0, 1.6):
            pts = [(C1[0] + u + rng.uniform(-0.4, 0.4), C1[1] - r0 + 0.6), (C1[0] + u * 0.8 + rng.uniform(-0.8, 0.8), C1[1] - (r0 + r1) / 2),
                   (C1[0] + u * 0.6 + rng.uniform(-0.4, 0.4), C1[1] - r1 - 0.8)]
            h.stroke(catmull(pts, 8), "hair", "ink", amp=0.35)
        h.dot(C1[0], C1[1] - r1 - 1.2, 0.3, "ink")
    # the stations
    pts = station_points()
    for i, (x, y) in enumerate(pts):
        polys = [pl for col, w, pl in strokes_from_svg(os.path.join(SEALS, f"office-seal-{i}.svg"), colors=("#201d19",))]
        polys = [pl for pl in polys if max(yy for _, yy in pl) < 270]
        for pl in place(polys, (59, 54, 182, 182), (x, y), 6.6):
            h.stroke(pl, "orn", "ink", amp=0.15)
    # the order of permission, station to station, dotted
    for i in range(6):
        a, b = pts[i], pts[i + 1]
        d = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / d, (b[1] - a[1]) / d
        seg = [(a[0] + ux * 4.6, a[1] + uy * 4.6), (b[0] - ux * 4.6, b[1] - uy * 4.6)]
        marks.dotted(h, seg, 1.6, 0.28, skip_ends=False)
    # the stations' own centre, which is wherever they happen to be: standing uncertain; the choirs' centre: nothing
    C2 = (sum(x for x, _ in pts) / 7, sum(y for _, y in pts) / 7)
    marks.sig_candidate(h, C2[0], C2[1], 1.4)
    # the offset between the two centres, drawn and not corrected
    h.stroke([C1, C2], "hair", "red", amp=0.1)
    h.dot(C1[0], C1[1], 0.3, "red")
    h.dot(C2[0], C2[1], 0.3, "red")
    # numerals on the rings (at the right crossing) and at the stations; legends at the sides, no leaders
    for i, R in enumerate(RINGS):
        P.label(str(i + 1), C1[0] - R + 1.2, C1[1] - 1.2, 2.5)
    for i, (x, y) in enumerate(pts):
        P.label(str(i), x + 4.4, y + 1.2, 2.5)
    P.label("THE NINE", 163, 86, 2.5)
    for i, name in enumerate(CHOIRS):
        P.label(f"{i + 1}  {name}", 163, 93 + i * 6.2, 2.5)
    P.label("THE SEVEN", 14, 86, 2.5)
    for i, name in enumerate(OFFICES):
        P.label(f"{i}  {name}", 14, 93 + i * 6.2, 2.5)
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    P.export(out_dir, {"rings": RINGS, "stations": [[round(x, 1), round(y, 1)] for x, y in pts], "centres": [C1, [round(C2[0], 1), round(C2[1], 1)]], "station_bands": STATIONS})


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    main(out)
    validate(out)
