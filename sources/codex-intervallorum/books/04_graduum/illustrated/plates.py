#!/usr/bin/env python3
"""Clavicula Graduum: the illustrated plates.

Each native plate generator (plates/*-native) runs from its own file, with the figures it drew
as apparatus or as robed stick figures replaced by slots, and the raster figures filed for the
plate (references/raster/, see README there) stand in those slots:

  I     the nine choirs and seven stations on a night ground; no figure.
  II    Hora and Tempus beside their shops, the red thread between them carried over both
        shops; the Returning Trace above the seam; Repetiel at Tempus's bench.
  III   the Measurer of Absences, whose held frame is the plate's frame at the seam.
  IV    three observers, each a handoff office that watches: Probator (technical assurance),
        Viridon (experience reporting), Severion (commercial triage).
  V     the Keeper wearing the dial, the plate's dial drawn round it; the bars, the cord.
  VI    the four hooded managers, each with its tile; Culpax, Redacth, Velaroth and Viridon
        catching the reward; the Twin Register beneath the maze.
  VII   the building with its offices at their stations, Bael's chair on the top floor and the
        figure beneath the cord on the floor of hands.
  VIII  the council: eleven handoff spirits in three tiers with Foras among them, and the
        decision demon, ears and no eyes, over the gauge.
  X     Foras with the litany registers of the proof.

Everything else each generator draws stays, including every carrier (frame rules, Tempus's
parts, the table's cells, the ground blades, the maze nodes, the litany). The plot masters are
not touched: this edition is a separate build and nothing here plots.

Output: illustrated/out/plates/tabula-<n>-illustrated.pdf (one 7 x 10 in leaf each) and
plates.json (which render went where, carriers, hashes).
"""
import glob
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(BOOK, "..", ".."))
PL = os.path.join(BOOK, "plates")
for p in (os.path.join(REPO, "common", "illum"), os.path.join(REPO, "common", "plot"), os.path.join(REPO, "common", "geometry"),
          os.path.join(PL, "viii-native"), os.path.join(PL, "vii-native"), os.path.join(PL, "v-native")):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ["GRADUUM_READING"] = "1"

from reportlab.pdfgen.canvas import Canvas  # noqa: E402
from shapely.geometry import Polygon, LineString, box as sbox  # noqa: E402

import platekit as pk  # noqa: E402
import furniture as fu  # noqa: E402
import raster  # noqa: E402
import figure_growth  # noqa: E402
import ornament  # noqa: E402
import tx  # noqa: E402
import marks  # noqa: E402
from core import arc_pts, catmull, bezier  # noqa: E402

PW, PH = 504.0, 720.0
OUT = os.path.join(HERE, "out", "plates")
FRAME_MM = (8, 10, 202, 288)
RESERVED_MM = (17, 42, 40, 24)
ROPE = (46.0, 122.0, 458.0, 604.0)          # the roped frame on the leaf, points
INNER = (ROPE[0] + 2.2, ROPE[1] + 2.2, ROPE[2] - 2.2, ROPE[3] - 2.2)
FIELD = (INNER[0] + 5.0, INNER[1] + 5.0, INNER[2] - 5.0, INNER[3] - 5.0)
CHAPTERS = {c["number"]: c for c in json.load(open(os.path.join(BOOK, "manuscript", "book.json")))["chapters"]}
CATALOGUE = json.load(open(os.path.join(REPO, "books", "03_escalationum", "manuscript", "catalogue.json")))

placed = []


def material_call(hand, method, predicate, operation):
    """Tag exact, nonsemantic construction calls, before wobble/resampling.

    This runs only in the illustrated adapter. Native plot masters, text,
    carrier tags, centerlines and supporting geometry are retained.
    """
    original = getattr(hand, method)
    def marked(pts, *args, **kwargs):
        if not kwargs.get("attrs") and predicate(pts, args, kwargs):
            kwargs["attrs"] = ' data-material="cornmeal"'
        return original(pts, *args, **kwargs)
    setattr(hand, method, marked)
    try:
        return operation()
    finally:
        setattr(hand, method, original)


def R(name):
    """the selected render for a subject (the only one outside attempts/)"""
    if name == "foras":
        return os.path.join(REPO, "books", "06_tarot", "major-arcana", "art", "foras-raster-reference-v02.png")
    hits = sorted(glob.glob(os.path.join(REPO, "references", "raster", "batch-*", f"{name}-raster-reference-v*.png")))
    if not hits:
        raise FileNotFoundError(name)
    return hits[-1]


def load(stem, path):
    sys.modules.pop(stem, None)
    spec = importlib.util.spec_from_file_location(stem, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(path))
    spec.loader.exec_module(m)
    return m


def record(plate, subject, slot, where):
    m = slot.meta
    placed.append({"plate": plate, "subject": subject, "where": where, "source": m["source"],
                   "source_sha256": m["source_sha256"], "extent_mm": [round(v, 1) for v in slot.extent_mm()],
                   "crop_px": slot.crop, "mirrored": slot.mirror})
    placed[-1]["figure_growth"] = m.get("figure_growth")


def foot_box(slot, pad=0.0):
    x0, y0, x1, y1 = slot.extent_mm()
    return Polygon([(x0 - pad, y0 - pad), (x1 + pad, y0 - pad), (x1 + pad, y1 + pad), (x0 - pad, y1 + pad)])


# ----------------------------------------------------------------- skipping --

def furniture_skip(bottom=237.5, extra=(), extra_fn=None):
    """leave out what the plot sheet's own furniture drew: its frame and frame rule (redrawn on
    the roped frame), the title block, the reserved box and its label (redrawn), the strap,
    caption strip and TABULA line (redrawn below the frame), and the long hairline rules"""
    rx, ry, rw, rh = RESERVED_MM

    def skip(bb, attrs, layer):
        if "data-tick" in attrs:
            return True
        x0, y0, x1, y1 = bb
        if x1 - x0 > 150 and y1 - y0 < 0.6:
            return True
        if abs(x0 - FRAME_MM[0]) < 0.5 and abs(x1 - FRAME_MM[2]) < 0.5:
            return True
        if y1 < 31.5:
            return True
        if y0 > bottom:
            return True
        if pk.inside(bb, (rx, ry, rx + rw, ry + rh + 5.5), 0.6):
            return True
        for ebox in extra:
            if pk.inside(bb, ebox, 0.3):
                return True
        if extra_fn and extra_fn(bb, attrs, layer):
            return True
        return False
    return skip


# -------------------------------------------------------------------- leaf --

class Leaf:
    def __init__(self, num, title, subtitle, strap, caption, shift, seed, box=(8, 31, 202, 238), dark=False):
        os.makedirs(OUT, exist_ok=True)
        fu.fonts()
        self.num, self.title, self.subtitle = num, title, subtitle
        self.strap, self.caption, self.shift = strap, caption, shift
        self.stem = f"tabula-{num.lower()}-illustrated"
        self.path = os.path.join(OUT, self.stem + ".pdf")
        self.c = Canvas(self.path, pagesize=(PW, PH), invariant=1, pageCompression=1)
        order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
        figure_growth.configure(self.c, "IV", order.index(num), len(order))
        if os.environ.get('GRIMOIRE_EDGE_GRAIN','1')!='0':
            self.c._figure_edge_subjects={'IV':('viridon',),'X':('foras',)}.get(num,())
        self.dark = dark and num in ("VI", "VIII") and self.c._figure_growth["amount"] > 0
        if self.dark:
            self.c._figure_ground = "dark"
        self.c.setTitle(f"Clavicula Graduum - Tabula {num} - {title} (illustrated)")
        self.rng = random.Random(seed)
        self.h = fu.Hand(self.c, self.rng, amp=0.16)
        self.M = pk.Map(box, FIELD)
        self.mh = pk.MapHand(self.c, random.Random(seed + 7), self.M)
        if self.dark:
            self.mh.colors.update(ink=fu.LIGHT, red=(242,116,83))
        self.mh.weight_scale = 1.0
        fu.ground(self.c, PW, PH)
        fu.specks(self.c, PW, PH, f"graduum-{num}", n=40)
        if not dark or (num in ("VI", "VIII") and not self.dark):
            x0, y0, x1, y1 = INNER
            fu.wash(self.h, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fu.OCHRE, alpha=0.075)
        elif self.dark:
            x0,y0,x1,y1=FIELD
            self.c.setFillColorRGB(*fu.rgb(fu.DARK))
            self.c.roundRect(x0,y0,x1-x0,y1-y0,5,fill=1,stroke=0)
        self.head()
        self.frame()

    def head(self):
        c, h = self.c, self.h
        fu.spaced(c, f"TABULA {self.num}", PW / 2, 676, "FellSC", 9.5, 2.2, "center", fu.RED)
        c.setFillColorRGB(*fu.rgb(fu.INK))
        title_size = min(25, 25 * (PW-80) / max(c.stringWidth(self.title, "FellTitle", 25), 1))
        c.setFont("FellTitle", title_size)
        c.drawCentredString(PW / 2, 648, self.title)
        fu.spaced(c, self.subtitle, PW / 2, 632, "FellSC", 7.6, 0.9, "center", fu.UMBER)
        fu.orn_rule(h, PW / 2, 620, 170)

    def frame(self):
        fu.rope_frame(self.h, *ROPE)
        fu.register(self.h, ROPE[0] - 16, ROPE[3] + 14)
        fu.register(self.h, ROPE[2] + 16, ROPE[1] - 14)

    def frame_rule(self, hidden, weight=0.45, color_map=None):
        """the plate's frame rule, the same ticks in the same order, on the roped frame's inner edge"""
        ah = pk.AnisoHand(self.c, self.rng, FRAME_MM, INNER)
        if color_map:
            ah.colors.update(color_map)
        n, total = ornament.scale_frame(ah, FRAME_MM, hidden, pitch=2.5, short=1.0, long=2.0, long_every=10, weight=weight)
        return {"carrier": "frame rule on the roped frame's inner edge, clockwise from the top-left", "message": hidden,
                "carrier_marks": n, "ticks": total}

    def reserved(self, color="ink"):
        if self.dark and color == "ink":
            color = "light"
        x, y, w, hh = self.M.R(*RESERVED_MM)
        h = self.h
        h.stroke([(x, y), (x + w, y), (x + w, y + hh), (x, y + hh)], "orn", color, closed=True, amp=0.1)
        h.stroke([(x + 2, y + 2), (x + w - 2, y + 2), (x + w - 2, y + hh - 2), (x + 2, y + hh - 2)], "hair", color, closed=True, amp=0.1)
        self.c.setFont("FellIt", 7.5)
        self.c.setFillColorRGB(*fu.rgb(fu.UMBER if color == "ink" else fu.LIGHT))
        self.c.drawCentredString(x + w / 2, y - 9, "reserved")

    def foot(self, cipher=True):
        c = self.c
        fu.spaced(c, self.strap, PW / 2, 103, "FellSC", 7.4, 1.0, "center", fu.INK)
        out = {}
        if cipher:
            # Keep the complete inscription inside the frame at any caption length.
            s = min(6.6, (PW - 112) / max(tx.width(self.caption, 1.0), 1))
            w = tx.width(self.caption, 1.0) * s
            x = (PW - w) / 2
            yd = fu.YDown(self.h, x, 92, s)
            cx = 0.0
            for wi, wd in enumerate(tx.encode(self.caption)):
                if wi:
                    cx += 0.55
                for (b, t) in wd:
                    tx.mark(yd, (b - 1 + self.shift) % 12 + 1, cx, 0, 1, "hair", "ink")
                    tx.tally(yd, t, cx, 0, 1, "ink")
                    cx += tx.token_width(t, 1)
            out = {"caption_cipher": {"shift": self.shift, "normalized": " ".join(tx.normalize(self.caption)),
                                      "mark_pt": s, "width_pt": w, "y_pt": 92}}
        edge_grain=(os.environ.get('GRIMOIRE_EDGE_GRAIN','1')!='0'
                    and self.c._figure_growth['amount']>0)
        wave=figure_growth.flowing_rule if edge_grain and self.num in ('IV','VIII','X') else fu.wave_rule
        wave(self.h, PW / 2 - 70, PW / 2 + 70, 66 if cipher else 82, seed=self.num)
        source_note={'IV':'Viridon / after the raster portrait in Book III.',
                     'X':'Foras / after the raster portrait in Book III.'}.get(self.num)
        if source_note and edge_grain:
            c.setFont('FellIt',8)
            c.setFillColorRGB(*fu.rgb(fu.UMBER))
            c.drawCentredString(PW/2,45,source_note)
            out['figure_source_note']=source_note
        return out

    def note(self, quote, width, at, target, align="left", size=10.5, field="any"):
        """a red note quoting the chapter or the Book III catalogue; the leader ends at `target` (mm)"""
        old_red = self.h.colors["red"]
        if self.dark:
            self.h.colors["red"] = (242,116,83)
        ch = CHAPTERS[self.num]
        hay = " ".join([ch["deck"], ch["fiction"], ch["caption"]] + [p for pg in ch["pages"] for p in pg["paragraphs"]])
        hay += " " + json.dumps(CATALOGUE, ensure_ascii=False)
        assert quote in hay, (self.num, quote)
        lines = fu.wrap(quote, "Hand", size, width)
        X, Y = self.M.P(*at)
        fu.hand_note(self.h, lines, X, Y, size, "red", align=align)
        if target:
            tX, tY = self.M.P(*target)
            nw = max(self.c.stringWidth(l, "Hand", size) for l in lines)
            sx = X + (nw / 2 if align == "left" else -nw / 2 if align == "right" else 0)
            sy = Y - (len(lines) - 1) * size * 1.05 - 5
            if tY > sy:
                sy = Y + size + 2
            mid = ((sx + tX) / 2 + 8, (sy + tY) / 2 + 3)
            self.h.stroke(catmull([(sx, sy), mid, (tX, tY)], 10), "hair", "red", amp=0.3)
            self.h.ring(tX, tY, 1.3, "hair", "red")
        self.h.colors["red"] = old_red
        return quote

    def doc(self, doc, skip, colors=None, wscale=1.8, layers=("art", "text")):
        if self.dark and colors is None:
            colors = {pk.INK_HEX: fu.LIGHT, pk.RED_HEX: (242,116,83)}
        return pk.draw_doc(self.c, doc, self.M, layers=layers, colors=colors, skip=skip, wscale=wscale)

    def save(self, meta):
        meta["figure_growth"] = getattr(self.c, "_figure_growth_records", [])
        meta["cornmeal_structural_grains"] = getattr(self.c, "_cornmeal_grains", 0)
        meta['decorative_flow_grain']=getattr(self.c,'_flow_material_records',[])
        meta["material_ground"] = "dark" if self.dark else "paper"
        self.c.showPage()
        self.c.save()
        meta.update({"plate": self.num, "title": self.title, "pdf": os.path.relpath(self.path, REPO),
                     "pdf_sha256": hashlib.sha256(open(self.path, "rb").read()).hexdigest(),
                     "figures": [p for p in placed if p["plate"] == self.num]})
        return meta


def carrier_under(doc, slots, tags, extra=None):
    """how many carrier marks the figures cover: tagged strokes (data-<tag>) and, where the
    a-form is untagged, the filled dots inside `extra` (a box in mm)"""
    from shapely.geometry import box as _box
    from shapely.ops import unary_union
    shape = unary_union([s.avoid(0.0) for s in slots]) if slots else None
    n = hit = 0
    for col, w, d, attrs in doc.layers["art"]:
        tagged = any(f"data-{t}=" in attrs for t in tags)
        if w == "DOT":
            x, y, r = (float(v) for v in d.split(","))
            bb = (x - r, y - r, x + r, y + r)
            if not tagged and not (extra and pk.inside(bb, extra)):
                continue
        elif tagged:
            bb = pk.bbox_of(d)
        else:
            continue
        n += 1
        if shape is not None and shape.intersects(_box(*bb)):
            hit += 1
    return {"carrier_marks": n, "under_a_figure": hit}


def carrier_roundtrip(doc, tag, message, skip, total, stem_tag=None):
    """Decode the retained stroke tags, also checking the actual rendering filter.

    An empty cell or a headless blade is a bit, so a count of visible b-marks
    alone cannot establish that the full carrier survived.
    """
    ones, stems = set(), set()
    expected = ornament.bits(message)
    for col, weight, path, attrs in doc.layers["art"]:
        hit = re.search(rf'data-{tag}="(\d+)"', attrs)
        stem = re.search(rf'data-{stem_tag}="(\d+)"', attrs) if stem_tag else None
        if not (hit or stem):
            continue
        if weight == "DOT":
            x, y, r = map(float, path.split(","))
            bb = (x - r, y - r, x + r, y + r)
        else:
            bb = pk.bbox_of(path)
        if skip(bb, attrs, "art"):
            raise ValueError(f"A {tag} carrier mark was omitted from the illustrated leaf")
        if hit:
            ones.add(int(hit[1]))
        if stem:
            stems.add(int(stem[1]))
    if stem_tag and stems != set(range(total)):
        raise ValueError("Ground carrier lost a blade, including a possible a-form")
    actual = [int(i in ones) for i in range(total)]
    if actual[:len(expected)] != expected or ornament.decode(actual) != message:
        raise ValueError(f"The retained {tag} carrier no longer decodes to its source text")
    return {"decoded": ornament.decode(actual), "positions": total, "roundtrip": True}


def capture_plate(m, run, tag):
    """run a Plate-based generator (I-IV) and return the Plate it built instead of exporting it"""
    cap = {}
    m.Plate.export = lambda self, out_dir, extra=None: cap.update(P=self)
    pk.filled_dots(True)
    try:
        run(pk.tmpdir(tag))
    finally:
        pk.filled_dots(False)
    return cap["P"]


def run_build(m, tag):
    """run a self-contained generator (V-VIII) and return its PlotDoc and meta"""
    pk.filled_dots(True)
    try:
        doc, meta = m.build(pk.tmpdir(tag))
    finally:
        pk.filled_dots(False)
    return doc, meta


# ---------------------------------------------------------------------- I --

def plate_i():
    m = load("tabula_i", os.path.join(PL, "i-native", "tabula_i.py"))
    P = capture_plate(m, m.main, "i")
    L = Leaf("I", "The Nine and the Seven", "A RANK HIERARCHY OVER A RATE HIERARCHY", P.strap, P.caption, P.shift, 500, dark=True)
    c, M = L.c, L.M
    rule = L.frame_rule(P.hidden)
    x0, y0, x1, y1 = FIELD
    c.setFillColorRGB(*fu.rgb(fu.DARK))
    c.roundRect(x0, y0, x1 - x0, y1 - y0, 5, stroke=0, fill=1)
    cx, cy = M.P(*m.C1)
    for (r_in, r_out), col, a in (((14, 24), fu.OCHRE, 0.20), ((33, 43), fu.SLATE, 0.30), ((52, 62), fu.UMBER, 0.28)):
        p = c.beginPath()
        p.circle(cx, cy, r_out * M.s + 2.5)
        p.circle(cx, cy, r_in * M.s - 2.5)
        c.saveState()
        c.setFillColorRGB(*fu.rgb(col))
        c.setFillAlpha(a)
        c.drawPath(p, stroke=0, fill=1, fillMode=pk.FILL_EVEN_ODD)
        c.restoreState()
    # the illumination that descends: a soft glow from the rim inward, stopping at each triad
    rng = random.Random(51)
    for _ in range(170):
        X, Y = rng.uniform(x0 + 6, x1 - 6), rng.uniform(y0 + 6, y1 - 6)
        d = math.hypot(X - cx, Y - cy) / M.s
        if any(abs(d - r) < 1.8 for r in m.RINGS):
            continue
        c.setFillColorRGB(*fu.rgb(fu.LIGHT))
        c.setFillAlpha(rng.uniform(0.12, 0.55))
        c.circle(X, Y, rng.choice([0.35, 0.5, 0.7, 1.0]), stroke=0, fill=1)
    c.setFillAlpha(1)
    colors = {pk.INK_HEX: fu.LIGHT, pk.RED_HEX: (214, 84, 66)}
    L.doc(P.doc, furniture_skip(), colors=colors, wscale=1.9)
    L.reserved("light")
    meta = L.foot()
    return L.save({"frame_rule": rule, **meta, "carrier": "frame rule"})


# --------------------------------------------------------------------- II --

def plate_ii():
    m = load("tabula_ii", os.path.join(PL, "ii-native", "tabula_ii.py"))
    m.LEFT, m.RIGHT = (38.0, 100.0), (110.0, 164.0)
    slots = {}

    def repetiel(h, rng, cx, yf, k=1.0):
        s = raster.Slot(R("repetiel"), height_mm=30 * k * 1.08, anchor_mm=(cx, yf))
        slots["Repetiel"] = s
        x0, y0, x1, y1 = s.extent_mm()
        return ((x0 + x1) / 2, y0), Polygon([(x0, y0), (x1, y0), (x1, yf), (x0, yf)])
    m.ap.repetiel = repetiel
    m.returning_trace = lambda P: None
    P = capture_plate(m, m.main, "ii")
    L = Leaf("II", "The Two Watchmakers", "ASSEMBLY UNDER INTERRUPTION", P.strap, P.caption, P.shift, 1962)
    c, M = L.c, L.M
    L.doc(P.doc, furniture_skip())
    src = R("hora-and-tempus")
    hora = raster.Slot(src, height_mm=92, anchor_mm=(24.5, m.BENCH), crop_px=(0, 0, 515, 1536))
    tempus = raster.Slot(src, height_mm=92, anchor_mm=(186.5, m.BENCH), crop_px=(520, 0, 1024, 1536))
    trace = raster.Slot(R("returning-trace"), height_mm=34, anchor_mm=(m.MID, 49.0), anchor="centre")
    for s, name, where in ((hora, "Hora (left of the pair)", "beside his shop, holding the ten he closed"),
                           (tempus, "Tempus (right of the pair)", "beside his shop, holding the loose parts"),
                           (trace, "The Returning Trace", "above the seam"),
                           (slots["Repetiel"], "Repetiel", "Tempus's bench")):
        s.draw(c, M)
        record("II", name, s, where)
    # the red thread the pair share, carried over both shops: from Hora's ring to Tempus's hand
    a = hora.mm(474, 432)
    b = tempus.mm(612, 425)
    route = [a, (a[0] + 2, a[1] - 22), (a[0] + 10, 71.2), (m.MID, 70.8), (b[0] - 10, 71.2), (b[0] - 2, b[1] - 22), b]
    L.mh.stroke(catmull(route, 14), "orn", "red", amp=0.25)
    L.mh.dot(*a, 0.45, "red")
    L.mh.dot(*b, 0.45, "red")
    L.reserved()
    meta = L.foot()
    chk = carrier_under(P.doc, [hora, tempus, trace, slots["Repetiel"]], ["part"], extra=(m.RIGHT[0] + 10, m.TOP, m.RIGHT[1], m.BENCH - 20))
    return L.save({**meta, "carrier": "Tempus's loose parts, as the generator draws them (ring = b, dot = a)", "carrier_check": chk})


# -------------------------------------------------------------------- III --

def plate_iii():
    m = load("tabula_iii", os.path.join(PL, "iii-native", "tabula_iii.py"))
    s = raster.Slot(R("measurer-of-absences-original"), height_mm=146, anchor_mm=(66.0, 218.0))
    FR_PX = (610, 420, 790, 760)               # the frame he holds, in the render
    (fx0, fy0) = s.mm(FR_PX[0], FR_PX[1])
    s.mx += (m.SEAM - 7.0) - fx0               # the held frame straddles the seam
    (fx0, fy0), (fx1, fy1) = s.mm(FR_PX[0], FR_PX[1]), s.mm(FR_PX[2], FR_PX[3])
    m.FRAME_BOX = (fx0, fy0, fx1 - fx0, fy1 - fy0)
    # Empty cells carry a-form bits too. Clear the entire table, not just its ticks.
    sx0, sy0, sx1, sy1 = s.extent_mm()
    tx0, ty0, tx1, ty1, cols, rows = m.TABLE
    m.TABLE = (max(tx0, sx1 + 4.0), ty0, tx1, ty1, cols, rows)
    avoid_fig = s.avoid(1.4)
    m.measurer = lambda P: avoid_fig

    def seam_only(P):
        h = P.art
        h.stroke([(m.SEAM, 76), (m.SEAM, 228)], "orn", "red", amp=0.08)
        marks.sig_ground(h, 16, 92, 222, 6.0, step=5.0)
    m.frame_and_seam = seam_only
    P = capture_plate(m, m.main, "iii")
    L = Leaf("III", "The Cut", "A LEVEL IS A RECORD THAT OUTLIVES ITS DYNAMICS", P.strap, P.caption, P.shift, 1973)
    c, M = L.c, L.M
    x0, y0, x1, y1, cols, rows = m.TABLE
    X0, Y1 = M.P(x0, y0)
    X1, Y0 = M.P(x1, y1)
    fu.wash(L.h, [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)], (226, 214, 186), alpha=0.38)
    L.doc(P.doc, furniture_skip(extra=[(14, 74, 82, 79.5)]))
    s.draw(c, M)
    record("III", "The Measurer of Absences", s, "left of the seam; the frame he holds is the plate's frame")
    L.note("holds an empty frame out to the seam", 64, (14.5, 79.0), (fx0 + 1.2, fy0 + 8.0))
    L.reserved()
    meta = L.foot()
    chk = carrier_under(P.doc, [s], ["cell"])
    if chk["under_a_figure"] or s.avoid(0.8).intersects(sbox(*m.TABLE[:4])):
        raise ValueError("Tabula III: the complete cell carrier must clear the figure")
    chk.update(carrier_roundtrip(P.doc, "cell", P.hidden,
                                furniture_skip(extra=[(14, 74, 82, 79.5)]), cols * rows))
    return L.save({**meta, "carrier": "the table's cells, as the generator draws them", "carrier_check": chk,
                   "table_box_mm": list(m.TABLE[:4]), "table_cells": cols * rows,
                   "frame_box_mm": [round(v, 2) for v in m.FRAME_BOX]})


# --------------------------------------------------------------------- IV --

def plate_iv():
    m = load("tabula_iv", os.path.join(PL, "iv-native", "tabula_iv.py"))
    panel = m.panel
    def grain_panel(P, *args, **kwargs):
        return material_call(P.art, "stroke", lambda p,a,k:
            len(p) == 2 and abs(p[1][0]-p[0][0]-1.6) < 1e-6
            and abs(p[1][1]-p[0][1]+.8) < 1e-6,
            lambda: panel(P, *args, **kwargs))
    m.panel = grain_panel
    m.X0 = 62.0
    order = [("probator", "Probator, Director of Technical Assurance", "the first surveyor: four terraces"),
             ("viridon", "Viridon, Experience Reporting Director", "the second surveyor: six terraces")]
    slots = []

    def surveyor(h, rng, cx, y_feet, height, arms=2, raise_to=None, papers=True):
        name, subj, where = order[len(slots)]
        s = raster.Slot(R(name), height_mm=44.0, anchor_mm=(cx - 6.0, y_feet + 0.6))
        slots.append((s, subj, where))
        return raise_to

    def severion(h, rng, cx, yf, k=1.0):
        s = raster.Slot(R("severion"), height_mm=34.0, anchor_mm=(cx - 3.0, yf + 0.4))
        slots.append((s, "Severion, Commercial Triage Analyst", "the third observer, with no count"))
        x0, y0, x1, y1 = s.extent_mm()
        return ((x0 + x1) / 2, y0), Polygon([(x0, y0), (x1, y0), (x1, yf), (x0, yf)])
    m.robed_figure = surveyor
    m.ap.severion = severion
    P = capture_plate(m, m.main, "iv")
    L = Leaf("IV", "The Observer's Ladder", "THE NUMBER OF LEVELS IS A PROPERTY OF THE DESCRIPTION", P.strap, P.caption, P.shift, 1982)
    c, M = L.c, L.M
    rule = L.frame_rule(P.hidden)
    L.doc(P.doc, furniture_skip())
    for s, subj, where in slots:
        s.draw(c, M)
        record("IV", subj, s, where)
    L.reserved()
    meta = L.foot()
    return L.save({"frame_rule": rule, **meta, "carrier": "frame rule"})


# ---------------------------------------------------------------------- V --

def plate_v():
    m = load("tabula_v", os.path.join(PL, "v-native", "tabula_v.py"))
    DIAL_PX = (481, 521)                         # the dial on the Keeper's chest, in the render
    FEET_PX_Y = 1450
    cx, cy, R0 = m.DIAL
    s_mm = (m.GROUND_Y - 0.6 - cy) / (FEET_PX_Y - DIAL_PX[1])
    keeper = raster.Slot(R("keeper-wearing-dial"), s=s_mm, anchor_px=DIAL_PX, anchor_mm=(cx, cy))
    occ = keeper.avoid(0.6)
    hand_px, thread_end_px = (742, 498), (766, 978)
    st = {}

    def draw_keeper(h, rng, bars_y, chest_ring, dial_occluder):
        """the seven bars cross the body where the body is absent: drawn from the robe's edge
        outward on each side, never across the figure"""
        for i, y in enumerate(bars_y):
            line = LineString([(cx - 46, y), (cx + 46, y)])
            hit = line.intersection(occ)
            if hit.is_empty:
                continue
            xs = [x for g in getattr(hit, "geoms", [hit]) for x, _ in g.coords]
            left, right = min(xs), max(xs)
            ov = 4.5 + 3.0 * (0.5 + 0.5 * math.sin(i * 2.1))
            for xa, xb in ((left - ov - 4.0, left - 0.4), (right + 0.4, right + ov + 4.0)):
                h.straight([(xa, y - 0.7), (xb, y - 0.7)], "orn", "ink")
                h.straight([(xa, y + 0.7), (xb, y + 0.7)], "orn", "ink")
                h.straight([(xa, y - 0.7), (xa, y + 0.7)], "orn", "ink")
            st.setdefault("bars", []).append((left - ov - 4.0, right + ov + 4.0, y))
        return keeper.mm(*hand_px), Polygon()

    def draw_cord(h, pinch, bars):
        """the Keeper's own thread carries the cord to the ground: straight down from where the
        render lets it fall, with the five knots, and the fourth bar read against it"""
        x_cord, y_top = keeper.mm(*thread_end_px)
        y_bot = m.GROUND_Y - 1.6
        h.straight([(x_cord, y_top + 0.2), (x_cord, y_bot)], "orn", "red")
        for k in range(5):
            y = y_top + (y_bot - y_top) * (k + 1) / 6
            h.dot(x_cord, y, 0.55, "red")
        h.stroke(arc_pts(x_cord + 1.7, y_bot + 0.1, 1.8, 180, 520, 30), "orn", "red", amp=0.2)
        x0, x1, y = st["bars"][3]
        thread_x = keeper.mm(758, 0)[0]
        xx = x1 + 1.8
        stop = thread_x - 1.2
        while xx < stop - 0.4:
            h.straight([(xx, y), (min(xx + 1.6, stop), y)], "hair", "red")
            xx += 2.8
        h.straight([(stop, y - 1.4), (stop, y + 1.4)], "orn", "red")
        return x_cord
    m.draw_keeper = draw_keeper
    m.draw_cord = draw_cord
    native_ground = m.draw_ground

    def root_ground(h, rng):
        # Generate first, then transform the completed paths. Mapping before the
        # wobble sampler would consume a different RNG sequence and change blades.
        start = len(h.pdoc.layers[h.layer])
        result = native_ground(h, rng)
        def Y(y):
            return 228.0 + (m.GROUND_Y - y) * 0.4
        for i in range(start, len(h.pdoc.layers[h.layer])):
            col, weight, path, attrs = h.pdoc.layers[h.layer][i]
            if weight == "DOT":
                x, y, radius = map(float, path.split(","))
                path = f"{x},{Y(y)},{radius}"
            else:
                path = re.sub(r"([ML])(-?[\d.]+),(-?[\d.]+)",
                              lambda q: f"{q[1]}{q[2]},{Y(float(q[3])):.3f}", path)
            h.pdoc.layers[h.layer][i] = (col, weight, path, attrs)
        return result
    m.draw_ground = root_ground
    doc, meta = run_build(m, "v")
    L = Leaf("V", "The Dial of Seven Keepers", "TWO SCALES / NO ALIGNMENT IMPOSED", "BOUNDARIES / ROMAN NUMERALS",
             m.CAPTION, 0, m.SEED)
    c, M = L.c, L.M
    # the raster dial carries the hands; the plate's own hands and hub inside the inner ring are left out
    def inner_dial(bb, attrs, layer):
        return layer == "art" and pk.inside(bb, (cx - 6.4, cy - 6.4, cx + 6.4, cy + 6.4))
    blot_c = M.P(cx, cy)
    fu.blot(L.h, blot_c[0], blot_c[1], R0 * M.s * 1.25, fu.OCHRE, alpha=0.18, seed="v-dial")
    L.doc(doc, furniture_skip(bottom=236.0, extra_fn=inner_dial))
    keeper.draw(c, M)
    record("V", "The Keeper wearing the dial", keeper, "centre; the plate's dial is drawn round the dial he wears")
    x0b, x1b, yb = st["bars"][3]
    L.note("The fourth is read against the thread by a dashed rule and does not reach it.", 104, (196.0, 186.0),
           (keeper.mm(758, 0)[0] - 1.2, yb + 1.6), align="right")
    L.reserved()
    meta2 = L.foot()
    chk = carrier_under(doc, [keeper], ["blade", "head"])
    if chk["under_a_figure"]:
        raise ValueError("Tabula V: ground carrier must clear the Keeper's hem")
    chk.update(carrier_roundtrip(doc, "head", m.HIDDEN,
                                furniture_skip(bottom=236.0, extra_fn=inner_dial),
                                meta["hidden"]["blades"], stem_tag="blade"))
    return L.save({**meta2, "carrier": "root blades below the hem, left to right; dot head = b, none = a",
                   "carrier_message": meta["hidden"]["message"], "carrier_check": chk,
                   "carrier_transform": {"baseline_mm": 228.0, "vertical_scale": -0.4}})


# --------------------------------------------------------------------- VI --

def plate_vi():
    m = load("tabula_vi", os.path.join(PL, "vi-native", "tabula_vi.py"))
    landings = m.draw_landings
    def grain_landings(h, *args, **kwargs):
        return material_call(h, "straight", lambda p,a,k:
            len(p) == 2 and p[0][0] == m.LX0 and p[1][0] == m.LX1
            and any(abs(p[0][1]-y-1.1) < 1e-6 for y in m.LANDINGS),
            lambda: landings(h, *args, **kwargs))
    m.draw_landings = grain_landings
    managers = ["hooded-manager-01", "hooded-manager-02", "hooded-manager-03", "hooded-manager-04-leaked-tile"]
    apps = [("culpax", "Culpax"), ("redacth", "Redacth"), ("velaroth", "Velaroth"), ("viridon", "Viridon")]
    slots = []

    def manager(h, rng, cx, y_feet, height, arms=2, raise_to=None, papers=False):
        i = sum(1 for s in slots if s[1].startswith("Hooded"))
        s = raster.Slot(R(managers[i]), height_mm=33.0, anchor_mm=(cx - 3.0, y_feet + 0.6))
        slots.append((s, f"Hooded manager {i + 1}", f"landing {i + 1}, holding its tile"))
        x0, y0, x1, y1 = s.extent_mm()
        return (x1 + 2.5, y0 + 9.0)               # the true-crop tile is set beside the figure

    def apparatus(i):
        name, subj = apps[i]

        def fn(h, rng, cx, yf, k=1.0):
            s = raster.Slot(R(name), height_mm=27.0, anchor_mm=(cx + 2.0, yf + 0.4))
            slots.append((s, subj, f"landing {i + 1}, catching the reward"))
            x0, y0, x1, y1 = s.extent_mm()
            mouth = ((x0 + x1) / 2, y0 + 1.0)
            return mouth, Polygon([(x0, y0), (x1, y0), (x1, yf), (x0, yf)])
        return fn
    m.robed_figure = manager
    m.ap.culpax, m.ap.redacth, m.ap.velaroth, m.ap.viridon_cracked = (apparatus(i) for i in range(4))
    twin = {}

    def twin_register(h, rng, x, y):
        s = raster.Slot(R("twin-register"), height_mm=44.0, anchor_mm=(x, y + 16.0))
        twin["s"] = s

    def glyphs(h, rng):
        mx, my, n, cs = m.MAZE
        marks.sig_reflexive(h, mx + n * cs - 14, my + n * cs + 9.5, 7.0, orn=0)
    m.draw_twin_register = twin_register
    m.draw_glyphs = glyphs
    doc, meta = run_build(m, "vi")
    L = Leaf("VI", "The Feudal Register", "HIDING IS THE DESIGN / THE COST IS PAID AT THE BOUNDARY",
             "REWARD HIDING / INFORMATION HIDING", m.CAPTION, m.SHIFT, m.SEED, dark=True)
    c, M = L.c, L.M
    mx, my, n, cs = m.MAZE
    X0, Y1 = M.P(mx - 2, my - 2)
    X1, Y0 = M.P(mx + n * cs + 2, my + n * cs + 2)
    fu.wash(L.h, [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)], fu.SLATE, alpha=0.08)
    def riser_hatch(bb, attrs, layer):
        x0, y0, x1, y1 = bb
        return layer == "art" and m.LX0 - 0.5 <= x0 and x1 <= m.LX1 + 0.5 and any(
            y - 0.2 <= y0 and y1 <= y + 3.6 and (y1 - y0) > 1.5 for y in m.LANDINGS)
    L.doc(doc, furniture_skip(extra_fn=riser_hatch))
    for s, subj, where in slots:
        s.draw(c, M)
        record("VI", subj, s, where)
    twin["s"].draw(c, M)
    record("VI", "The Twin Register", twin["s"], "beneath the maze: the two-way hiding")
    # Viridon's pane is cracked on the fourth landing: the crack drawn on the render's pane
    vs = [s for s, subj, _ in slots if subj == "Viridon"][0]
    px, py = vs.mm(735, 300)
    L.mh.stroke([(px - 1.8, py - 3.0), (px - 0.4, py - 1.2), (px - 1.1, py + 0.4), (px + 0.6, py + 2.2), (px + 0.1, py + 3.6)], "orn", "red", amp=0.05)
    L.mh.stroke([(px - 0.4, py - 1.2), (px + 1.4, py - 1.9)], "hair", "red", amp=0.05)
    L.reserved()
    meta2 = L.foot()
    chk = carrier_under(doc, [x[0] for x in slots] + [twin["s"]], ["nodedot"])
    return L.save({**meta2, "carrier": meta["hidden"]["carrier"], "carrier_message": meta["hidden"]["message"], "carrier_check": chk})


# -------------------------------------------------------------------- VII --

def plate_vii():
    m = load("tabula_vii", os.path.join(PL, "vii-native", "tabula_vii.py"))
    hatch_band = m.hatch_band
    def grain_hatch(h, *args, **kwargs):
        return material_call(h, "straight", lambda p,a,k: True,
                             lambda: hatch_band(h, *args, **kwargs))
    m.hatch_band = grain_hatch
    slots = []
    fig = {}

    def foras(h, rng, cx, y_feet, height, arms=6, raise_to=None, papers=True):
        s = raster.Slot(R("figure-beneath-cord"), height_mm=19.6, anchor_mm=(cx - 1.0, y_feet + 0.4), crop_px=(0, 0, 860, 1536))
        fig["foras"] = s
        return s.mm(842, 262)                    # its upper right hand, raised

    orig_top = m.draw_top_floor

    def top_floor(h, rng, font):
        """Bael's chamber: the render's empty seat in place of the drawn chair; the bracket stays"""
        yf, yc = m.floor_y(6)
        roof = m.floor_y(6)[1] - m.SLAB
        bx, by = m.CORD_X, roof - 7.0
        h.straight([(bx - 5, by + 2.2), (bx + 5, by + 2.2), (bx + 5, by - 0.6), (bx - 5, by - 0.6)], "core", "ink", closed=True)
        h.dot(bx - 3.4, by + 0.8, 0.45, "ink")
        h.dot(bx + 3.4, by + 0.8, 0.45, "ink")
        h.straight([(bx, by - 0.6), (bx, by - 3.2)], "core", "ink")
        h.stroke(arc_pts(bx + 1.6, by - 3.2, 1.6, 180, 360, 20), "core", "ink", amp=0.1)
        h.straight([(bx + 3.2, by - 3.2), (bx + 3.2, by - 1.9)], "core", "ink")
        for px in (bx - 4.2, bx + 4.2):
            h.straight([(px, roof), (px, by + 2.2)], "hair", "ink")
        s = raster.Slot(R("bael"), height_mm=17.5, anchor_mm=(m.BX1 - m.WALL - 22, yf - 0.4))
        slots.append((s, "Bael, Chief Technology Officer", "floor 6: the chair, held in reserve"))
        return (bx, by)
    m.robed_figure = foras
    m.draw_top_floor = top_floor
    doc, meta = run_build(m, "vii")
    L = Leaf("VII", "The Cord Without a Mount", "THE CHANNEL THAT TOUCHES NO OFFICE", "ONE CORD / SEVEN FLOORS / NO MOUNT",
             m.CAPTION, 0, m.SEED, box=(8, 31, 202, 269))
    c, M = L.c, L.M
    rule = L.frame_rule(m.HIDDEN)
    # the floors, alternately tinted, as Book I's strata; the walls in sepia
    for i in range(7):
        yf, yc = m.floor_y(i)
        X0, Y1 = M.P(m.BX0 + m.WALL, yc)
        X1, Y0 = M.P(m.SHAFT[0], yf)
        fu.wash(L.h, [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)], fu.OCHRE if i % 2 else fu.SLATE, alpha=0.06 + 0.012 * i)
    L.doc(doc, furniture_skip(bottom=270.0))
    # the offices at their stations, floors 1-5, each standing in the open floor between stair and seal
    names = ["vassago", "gremory", "bune", "orobas", "paimon"]
    for i, nm in enumerate(names, start=1):
        yf, yc = m.floor_y(i)
        t = CATALOGUE["tiers"][i]
        s = raster.Slot(R(nm), height_mm=14.8, anchor_mm=(101.0, yf - m.SLAB + 0.2))
        slots.append((s, f"{t['name'].title()}, {t['office']}", f"floor {i}: {t['region']}"))
    for s, subj, where in slots:
        s.draw(c, M)
        record("VII", subj, s, where)
    fig["foras"].draw(c, M)
    yf6, yc6 = m.floor_y(6)
    L.note("The top floor has a chair and no desk.", 64, (166.0, 66.0), (m.BX1 - m.WALL - 16.0, yf6 - 12.0), align="left")
    record("VII", "The figure beneath the cord (Foras)", fig["foras"], "floor 0: the floor of hands; its own cord cropped away")
    L.reserved()
    meta2 = L.foot(cipher=False)
    return L.save({"frame_rule": rule, **meta2, "second_text": "office litany, registers A and B, as the generator draws them"})


# ------------------------------------------------------------------- VIII --

def plate_viii():
    m = load("tabula_viii", os.path.join(PL, "viii-native", "tabula_viii.py"))
    original_draw_tiers = m.draw_tiers
    tier_ys = [y+1.1 for y, _, _ in m.TIERS]
    def grain_tiers(h, *args, **kwargs):
        return material_call(h, "straight", lambda p,a,k:
            len(p) == 2 and abs(p[1][1]-p[0][1]) < 1e-6
            and any(abs(p[0][1]-y) < 1e-6 for y in tier_ys),
            lambda: original_draw_tiers(h, *args, **kwargs))
    m.draw_tiers = grain_tiers
    m.PIVOT = (150.0, 88.0)
    slots = []
    ear = {}

    def spirit(name):
        def fn(h, rng, cx, yf, k=1.0):
            s = raster.Slot(R(name), height_mm=30 * k * 1.12, anchor_mm=(cx, yf + 0.4))
            subj = next(x for x in CATALOGUE["handoffs"] if x["name"].lower() == name)
            slots.append((s, f"{subj['name'].title()}, {subj['office']}", "the council"))
            x0, y0, x1, y1 = s.extent_mm()
            return ((x0 + x1) / 2, y0 + 1.0), Polygon([(x0 + 1, y0 + 2), (x1 - 1, y0 + 2), (x1 - 1, yf), (x0 + 1, yf)])
        return fn
    tiers = []
    for yf, k, row in m.TIERS:
        tiers.append((yf, k, [(nm, (spirit(nm.lower()) if fn else None), x, vol) for nm, fn, x, vol in row]))
    m.TIERS = tiers

    def foras(h, rng, cx, y_feet, height, arms=6, raise_to=None, papers=True):
        s = raster.Slot(R("foras"), height_mm=27.5, anchor_mm=(cx, y_feet + 0.4))
        slots.append((s, "Foras, Service Desk Analyst", "the lowest tier, at ordinary volume, ringed"))
        return None
    m.robed_figure = foras

    def decision(h, rng, loudest):
        """the gauge stays; the decision demon, ears and no eyes, stands over it, mirrored so its
        cupped ear turns to the council"""
        px, py = m.PIVOT
        h.straight([(px - 10, py + 18), (px + 42, py + 18)], "core", "ink")
        h.straight([(px - 10, py + 19.1), (px + 42, py + 19.1)], "hair", "ink")

        h.stroke(arc_pts(px, py, 13, 15, 165, 30), "orn", "ink", amp=0.15)
        for a in range(15, 166, 10):
            r0 = 11.2 if (a - 15) % 30 else 10.4
            h.stroke([(px + r0 * math.cos(math.radians(a)), py + r0 * math.sin(math.radians(a))),
                      (px + 13 * math.cos(math.radians(a)), py + 13 * math.sin(math.radians(a)))], "hair", "ink")
        h.stroke([(px - 13, py), (px - 13, py + 18)], "orn", "ink", amp=0.1)
        h.stroke([(px + 13, py), (px + 13, py + 18)], "orn", "ink", amp=0.1)
        a = math.atan2(loudest[1] - py, loudest[0] - px)
        tip = (px + 11.5 * math.cos(a), py + 11.5 * math.sin(a))
        h.stroke([(px - 3 * math.cos(a), py - 3 * math.sin(a)), tip], "core", "ink", amp=0.05)
        h.stroke([(tip[0] - 2.0 * math.cos(a - 0.45), tip[1] - 2.0 * math.sin(a - 0.45)), tip,
                  (tip[0] - 2.0 * math.cos(a + 0.45), tip[1] - 2.0 * math.sin(a + 0.45))], "orn", "ink", amp=0.1)
        h.dot(px, py, 0.55, "ink")
        s = raster.Slot(R("decision-demon"), height_mm=66.0, anchor_mm=(176.0, py + 18.0), mirror=True)
        ear["s"] = s
        ear["pt"] = s.mm(612, 330)
        ear["occ"] = s.avoid(0.8)
        return {"needle_deg": round(math.degrees(a), 1), "head": (ear["pt"][0] + 23, ear["pt"][1] - 10)}
    m.draw_decision = decision

    def flows(h, rng, voices, occupied, ear_left):
        by_name = {n: (mo, v) for n, mo, v in voices}
        (mx, my), _ = by_name["CHORAZ"]
        ex, ey = ear["pt"]
        occ = occupied.union(ear["occ"].difference(sbox(ex - 4, ey - 4, ex + 4, ey + 4)))
        for i in range(5):
            u = (i - 2) * 1.3
            wander = [rng.uniform(-3, 3) for _ in range(3)]
            px_ = m.PIVOT[0]
            pts = [(mx + u, my - 1), (px_ - 15 + u * 0.5, my - 10), (px_ - 13.5 + u * 0.4 + wander[0] * 0.2, 118),
                   (px_ - 12.5 + u * 0.4 + wander[1] * 0.2, 98), (px_ - 4 + u * 0.5 + wander[2] * 0.4, 70),
                   (ex - 7 + u * 0.4, ey + 6), (ex - 1.0 + u * 0.25, ey + 1.0)]
            geom = LineString(catmull(pts, 10)).difference(occ)
            for part in (geom.geoms if hasattr(geom, "geoms") else [geom]):
                if part.length > 2:
                    h.stroke(list(part.coords), "hair", "ink", amp=0.35)
        (fx, fy), _ = by_name["FORAS"]
        pts = [(fx, fy - 1), (fx + rng.uniform(-2, 2), fy - 9), (fx + rng.uniform(-3, 3), fy - 17), (fx + rng.uniform(-2, 4), fy - 23)]
        cc = catmull(pts, 10)
        geom = LineString(cc).difference(occupied)
        for part in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            if part.length > 2:
                h.stroke(list(part.coords), "hair", "ink", amp=0.35)
        h.dot(cc[-1][0], cc[-1][1], 0.3, "ink")
    m.draw_flows = flows
    doc, meta = run_build(m, "viii")
    L = Leaf("VIII", "The Council of the Loudest", "THE DECISION DEMON HEARS VOLUME", "THE QUIET ONE / RINGED",
             m.CAPTION, m.SHIFT, m.SEED, dark=True)
    c, M = L.c, L.M
    rule = L.frame_rule(m.HIDDEN)
    px = m.PIVOT[0]
    L.doc(doc, furniture_skip(extra=[(px - 27 - 34, 57, px - 26, 69)]))
    for s, subj, where in slots:
        s.draw(c, M)
        record("VIII", subj, s, where)
    ear["s"].draw(c, M)
    record("VIII", "The decision demon", ear["s"], "over the gauge; mirrored so its cupped ear faces the council")
    L.note("The decision demon hears volume, not correctness.", 96, (66, 76), ear["s"].mm(590, 318))
    L.reserved()
    meta2 = L.foot()
    return L.save({"frame_rule": rule, **meta2, "needle": meta["needle"], "loudest": meta["loudest"]})


# ----------------------------------------------------------- proofs: IX X XI --

def proof_doc(src):
    """the illustrator's proof SVG as a PlotDoc (every <path>, its stroke, width or fill)"""
    svg = open(src, encoding="utf-8").read()
    doc = pk.plotkit.PlotDoc(210, 297)
    for tag in re.findall(r"<path\b[^>]*>", svg):
        a = dict(re.findall(r'([a-z-]+)="([^"]*)"', tag))
        d = a.get("d", "")
        if not d:
            continue
        if a.get("stroke", "none") != "none":
            doc.layers["art"].append((a["stroke"].lower(), float(a.get("stroke-width", "0.17")), d, ""))
        elif a.get("fill", "none") != "none":
            doc.layers["art"].append((a["fill"].lower(), 0, d, ""))
    return doc


def proof_skip(fig=None, top=32, bottom=276):
    def skip(bb, attrs, layer):
        if fig and pk.inside(bb, fig):
            return True
        x0, y0, x1, y1 = bb
        if y1 < top or y0 > bottom:
            return True
        if x1 - x0 > 150 and y1 - y0 < 0.6:
            return True
        if abs(x0 - 8) < 0.5 and abs(x1 - 202) < 0.5:
            return True
        return False
    return skip


PROOF_COLORS = {"#161918": fu.INK, "#a32b24": fu.RED, "#a33024": fu.RED, "#201d19": fu.INK}


def plate_ix():
    src = os.path.join(BOOK, "proofs", "ix-gpt", "ix-square-table.svg")
    L = Leaf("IX", "The Square Table", "THE SQUARE TABLE / FIRST KEY", "ILLUSTRATOR'S PROOF / THE KEY IS PRINTED ON THE PLATE",
             "", 0, 1499, box=(8, 31, 202, 276))
    L.doc(proof_doc(src), proof_skip(), colors=PROOF_COLORS, wscale=1.5)
    meta = L.foot(cipher=False)
    return L.save({**meta, "second_text": "the self-encrypted caption and square table, from the illustrator's proof",
                   "proof": os.path.relpath(src, REPO)})


def plate_x():
    """the proof's litany registers and lower apparatus, with Foras in place of the drawn figure"""
    src = os.path.join(BOOK, "proofs", "x-xi-v-gpt", "x-prayer-of-the-office.svg")
    L = Leaf("X", "The Prayer of the Office", "FORAS / STATION 0", "THE LITANY / REGISTERS A AND B", "", 0, 1600,
             box=(8, 31, 202, 276))
    c, M = L.c, L.M
    doc = proof_doc(src)
    # The proof's request started at the old portrait's hand. Replace only
    # those two red paths; the litany and the lower instruments stay intact.
    doc.layers['art'] = [
        item for item in doc.layers['art']
        if not (item[0] in ('#a32b24', '#a33024')
                and pk.inside(pk.bbox_of(item[2]), (129, 154, 170, 243)))
    ]
    L.doc(doc, proof_skip(fig=(48, 52, 161, 205)), colors=PROOF_COLORS, wscale=1.6)
    s = raster.Slot(R("foras"), height_mm=150.0, anchor_mm=(104.0, 206.0))
    s.draw(c, M)
    # Continue the raster's wrist cord from its terminal bead, rather than
    # leaving the old request line floating beside the replacement figure.
    request_start = s.mm(816, 1009)
    L.mh.stroke(bezier(request_start, (request_start[0] + 14, request_start[1] + 18),
                        (156, 214), (132, 231), 48), 'hair', 'red', amp=0)
    L.mh.stroke([(132, 231), (130, 242)], 'hair', 'red', amp=0)
    record("X", "Foras, Service Desk Analyst", s, "centre; the sixth hand's request toward the permission field")
    meta = L.foot(cipher=False)
    return L.save({**meta, "second_text": "office litany, registers A and B, from the illustrator's proof",
                   "proof": os.path.relpath(src, REPO),
                   "request_start_mm": list(request_start), "request_stop_mm": [130, 242]})


def plate_xi():
    src = os.path.join(BOOK, "proofs", "x-xi-v-gpt", "xi-lifted-pen.svg")
    L = Leaf("XI", "The Lifted Pen", "ONLY THE FILE KEEPS THE LIFTS", "ILLUSTRATOR'S PROOF / THE PRINTED PLATE IS SILENT",
             "", 0, 1111, box=(8, 31, 202, 276))
    L.doc(proof_doc(src), proof_skip(), colors=PROOF_COLORS, wscale=1.7)
    meta = L.foot(cipher=False)
    return L.save({**meta, "second_text": "pen paths readable only from the proof file", "proof": os.path.relpath(src, REPO)})


def plate_xii():
    """the withheld key: Absentiel's keys from Book III, none of them this plate's"""
    L = Leaf("XII", "The Withheld Key", "THE KEY TO THIS PLATE IS NOT SUPPLIED IN THIS EDITION", "NONE SUPPLIED", "", 0, 1606)
    c, M = L.c, L.M
    s = raster.Slot(R("absentiel"), height_mm=84.0, anchor_mm=(108.0, 128.0), anchor="centre")
    s.draw(c, M)
    record("XII", "Absentiel, Business Continuity Director", s, "the five keys on their bar; none is this plate's")
    mh = L.mh
    # an empty sixth hook at the end of the bar, drawn in the plate's hand
    x0, y0, x1, y1 = s.extent_mm()
    hx, hy = x1 + 7.0, y0 + 9.0
    mh.stroke([(x1 - 2.0, hy - 2.0), (hx, hy - 2.0)], "orn", "ink", amp=0.1)
    mh.stroke(arc_pts(hx + 1.6, hy, 1.6, 180, 360, 20), "orn", "ink", amp=0.05)
    mh.stroke([(hx + 3.2, hy), (hx + 3.2, hy + 1.6)], "orn", "ink", amp=0.05)
    L.note("The absence is stated; no secret result is promised.", 160, (106.0, 196.0), None, align="center", size=12.5)
    L.reserved()
    meta = L.foot(cipher=False)
    return L.save({**meta, "second_text": "none supplied"})


PLATES = {"I": plate_i, "II": plate_ii, "III": plate_iii, "IV": plate_iv, "V": plate_v, "VI": plate_vi,
          "VII": plate_vii, "VIII": plate_viii, "IX": plate_ix, "X": plate_x, "XI": plate_xi, "XII": plate_xii}


def main(which=None):
    os.makedirs(OUT, exist_ok=True)
    man = os.path.join(OUT, "plates.json")
    results = json.load(open(man)) if os.path.exists(man) else {}
    for k, fn in PLATES.items():
        if which and k not in which:
            continue
        results[k] = fn()
        print(k, results[k]["pdf"], len(results[k]["figures"]), "figures")
    json.dump({k: results[k] for k in PLATES if k in results}, open(man, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
