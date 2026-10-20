"""Text for Tabula III (Rev 5 §3 and §8 verbatim; numbers from the expanded pilot, 11 Oct 2026)."""
from page3 import PENS, CELLS, ANCHOR, U

DK, RB, OL = PENS["dk"], PENS["rb"], PENS["ol"]
PAL = {"red": RB, "ink": DK}
DM, SPE, MONO = "DM Serif Display", "Spectral", "IBM Plex Mono"


def boxes(meta):
    B = []

    def add(**k):
        k.setdefault("color", DK)
        k.setdefault("lh", round(k["size"] * 1.35))
        B.append(k)

    add(id="rh_l", x=56, y=30, w=440, size=11.5, font=MONO, ls=0.22, runs=[("CLAVICULA MATRICIS", "")])
    add(id="rh_r", x=504, y=30, w=440, size=11.5, font=MONO, ls=0.22, align="right", color=RB,
        runs=[("TABULA III · § 3 · § 8", "")])
    add(id="title", x=60, y=62, w=880, size=46, lh=52, font=DM, align="center",
        runs=[("Of the Speed of Correction", "")])
    add(id="sub", x=60, y=120, w=880, size=19, lh=26, font=SPE, align="center", color=RB,
        runs=[("the Figure in the Square of Intervals", "i")])
    for k, (lab, v, mx) in CELLS.items():
        ax, ay = U(ANCHOR[k])
        add(id=f"n_{k}", x=ax - 40, y=ay - 18, w=80, size=27, lh=34, font=DM, align="center",
            color=OL if lab == "?" else DK, runs=[(lab, "")])
    add(id="body", x=56, y=1072, w=404, size=16, lh=23.5, font=SPE, sc_font="Spectral SC", para_gap=8,
        runs=[("Each audit is a question to put to a system. None yields a verdict by itself.", "i"), ("", "br"),
              ("Speed of correction.", "sc red"),
              (" How long does a problem take to reach someone able to act, and how long from there to action? "
               "Elections correct on a cycle of years; deployments change in weeks. Protected, non-punitive "
               "reporting adds a continuous channel between those bursts, but a channel needs a durable store or "
               "its signals fade before anyone acts.", ""), ("", "br"),
              ("Measure.", "sc red"),
              (" Split diagnosis-to-dispatch from dispatch-to-restoration. The first is organizational delay; the "
               "second is mostly physical repair. This split is the most directly testable idea in the practice, "
               "and regulator investigations of outages often carry timelines detailed enough to apply it.", "")])
    rows = [
        ("NUMBERS OF THE SQUARE", "red"),
        ("Upper half, minutes between recorded stages:", "i"),
        ("110  Orange ’21  technical recognition → first supplier contact", ""),
        ("134  Orange      recognition → supplier ticket", ""),
        ("114  Orange      internal escalation → supplier ticket", ""),
        ("39   Fastly ’21  detection → configuration identified", ""),
        ("85   BT ’23      decision to use DR → successful transfer", ""),
        ("7    BT          the same decision → first attempt", ""),
        ("78   BT          remainder, incl. failed execution and reversal", ""),
        ("17   OVH ’21     emergency call → responders arrive", ""),
        ("Lower half, of eight new units, how many sources made it observable:", "i"),
        ("6    a timed response sequence", ""),
        ("6    a specific obstruction mechanism", ""),
        ("3    external authority actually exercised", ""),
        ("3    an implemented change, explicitly reported", ""),
        ("1    a post-incident perturbation experiment", ""),
        ("0    a usable ownership comparison", ""),
        ("?    metric gaming: none documented, eight unknown", ""),
        ("?    reporter protection: none documented, eight unknown", ""),
        ("Expanded incident pilot, 11 Oct 2026. The endpoints differ; these are not comparable restoration "
         "metrics. Unknown is not absent.", "i"),
    ]
    runs = []
    for i, (t, st) in enumerate(rows):
        if i:
            runs.append(("", "br"))
        runs.append((t, st))
    add(id="legend", x=492, y=1074, w=452, size=11.4, lh=16, font=MONO, para_gap=1.8, pre=True, runs=runs)
    add(id="foot", x=56, y=1556, w=380, size=10.5, lh=14.5, font=MONO, color=RB,
        runs=[("Figure after Agrippa’s square and a horned stone figure; the spiral on its torso is the mark (§ 13).",
               "")])
    add(id="folio", x=844, y=1560, w=100, size=11, lh=14, font=MONO, align="right", ls=0.2, runs=[("iii", "")])
    return B
