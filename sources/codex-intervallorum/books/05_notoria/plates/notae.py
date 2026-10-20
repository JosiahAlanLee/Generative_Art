"""Ars Notoria Stigmatum - the five notae as native plotter plates.

Each nota is a computed trace field (books/05_notoria/fields/physarum.py) drawn in the
Matricis stroke vocabulary on the shared plate furniture: A4, two layers, two inks, a
reserved blank, the caption in the twelve-mark hand at a per-plate shift, and the frame
scale carrying the run's manifest identifier as the fourth carrier. A validator regenerates
the field from the manifest and checks that identifier against the frame.

    python notae.py all out/            build the five plates into out/<stem>/
    python notae.py i out/              one nota (i, ii, iii, iv, v)
    python validate.py out/             regenerate and check

The field is the rule by which the plate was computed, not a reading of it. The reading
leaf says what the construction does and does not establish.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
sys.path.insert(0, os.path.join(REPO, "common", "geometry"))
sys.path.insert(0, os.path.join(HERE, "..", "fields"))
import plate as plate_mod  # noqa: E402
from plate import Plate, FRAME, RESERVED, W, H, png_preview  # noqa: E402
from plotkit import INK, RED, arc_pts, catmull  # noqa: E402
import marks  # noqa: E402
import tx  # noqa: E402
import physarum  # noqa: E402

BOOK = "ARS NOTORIA STIGMATUM"


# ---------------------------------------------------------------- the plate --

class Nota(Plate):
    """the Graduum plate furniture with the Notoria's names on it"""

    def furniture(self, strap_y=245, reserved=True):
        h = self.text
        x0, y0, x1, y1 = FRAME
        h.straight([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "ink", closed=True)
        # Matricis corner stars on the frame
        for (cx, cy) in ((x0 + 2.4, y0 + 2.4), (x1 - 2.4, y0 + 2.4), (x0 + 2.4, y1 - 2.4), (x1 - 2.4, y1 - 2.4)):
            marks.asterisk(self.art, cx, cy, 1.5, 8, weight="hair", centre=True)
        self.label(BOOK, W / 2, 20.5, 4.1, "center")
        self.label(self.subtitle, W / 2, 27, 2.5, "center")
        marks.band_x(h, (x0 + 4, 30.5), (x1 - 4, 30.5), 1.2, 48, weight="hair", centre_dots=False)
        if reserved:
            rx, ry, rw, rh = RESERVED
            h.straight([(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)], "orn", "ink", closed=True)
            self.label("RESERVED", rx + rw / 2, ry + rh + 4.2, 2.5, "center")
        h.straight([(x0 + 4, 238), (x1 - 4, 238)], "hair", "ink")
        if self.strap:
            self.label(self.strap, W / 2, strap_y, 2.5, "center")
        h.straight([(x0 + 4, 268), (x1 - 4, 268)], "hair", "ink")
        self.label(f"NOTA {self.number}", W / 2, 275.5, 2.5, "center")
        self.label(self.title.upper().replace("'", ""), W / 2, 281.5, 3.0, "center")

    def export(self, out_dir, extra=None):
        os.makedirs(out_dir, exist_ok=True)
        if extra:
            self.meta.update(extra)
        title = f"Ars Notoria Stigmatum - Nota {self.number} - {self.title}"
        desc = ("Stroke-only pen plot plate, 210 x 297 mm, from a computed trace field (Jones 2010 agent model). "
                "Two layers (Art Paths, Text Outlines), two inks. The frame scale carries the run manifest "
                "identifier. Untested on a physical plotter.")
        doc, stem = self.doc, self.stem
        files = {
            f"{stem}.svg": doc.svg(("art", "text"), (INK, RED), title, desc),
            f"{stem}-black-a4.svg": doc.svg(("art", "text"), (INK,), title + " - black pass", desc),
            f"{stem}-red-a4.svg": doc.svg(("art", "text"), (RED,), title + " - red pass", desc),
            f"{stem}-art-only.svg": doc.svg(("art",), (INK, RED), title + " - art layer", desc),
            f"{stem}-text-only.svg": doc.svg(("text",), (INK, RED), title + " - text layer", desc),
        }
        for name, s in files.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                f.write(s)
        with open(os.path.join(out_dir, f"{stem}-type-audit.json"), "w") as f:
            json.dump({"plate": self.type_audit, "minimum_cap_mm": min(t["cap_height_mm"] for t in self.type_audit),
                       "cipher_base_square_mm": self.meta["caption"]["base_square_mm"]}, f, indent=1)
        self.meta["stem"] = stem
        self.meta["reading_edition"] = self.reading
        with open(os.path.join(out_dir, "build-meta.json"), "w") as f:
            json.dump(self.meta, f, indent=1)
        png_preview(os.path.join(out_dir, f"{stem}.svg"), os.path.join(out_dir, f"{stem}.png"))
        print(stem, "strokes:", len(doc.strokes()), "art:", len(doc.strokes("art")), "text:", len(doc.strokes("text")))
        return self.meta


# --------------------------------------------------------------- the field --

class Field:
    """a computed field placed on the page: grid cell (x, y) -> mm"""

    def __init__(self, result, step, centre, radius_mm):
        self.F = result["field"][step]
        self.spec = result["spec"]
        self.W, self.H = self.spec["grid"]
        self.cx, self.cy = centre
        self.R = radius_mm
        self.scale = (2 * radius_mm) / (self.spec["arena_radius"] * 2 * self.W)   # mm per cell
        self.gcx, self.gcy = self.W / 2.0, self.H / 2.0
        self.vmax = float(self.F.max()) or 1.0

    def mm(self, gx, gy):
        return (self.cx + (gx - self.gcx) * self.scale, self.cy + (gy - self.gcy) * self.scale)

    def grid(self, x, y):
        return ((x - self.cx) / self.scale + self.gcx, (y - self.cy) / self.scale + self.gcy)

    def sample(self, x, y):
        """bilinear sample of the field at page mm (x, y), 0 outside"""
        gx, gy = self.grid(x, y)
        if gx < 0 or gy < 0 or gx >= self.W - 1 or gy >= self.H - 1:
            return 0.0
        i, j = int(gx), int(gy)
        u, v = gx - i, gy - j
        F = self.F
        return float((1 - u) * (1 - v) * F[j, i] + u * (1 - v) * F[j, i + 1] + (1 - u) * v * F[j + 1, i] + u * v * F[j + 1, i + 1])

    # marching squares -----------------------------------------------------
    def contours(self, level, min_len=6):
        """iso-lines of the field at `level`, in page mm, chained into polylines"""
        F = self.F
        segs = []
        H_, W_ = F.shape
        a = F[:-1, :-1] >= level
        b = F[:-1, 1:] >= level
        c = F[1:, 1:] >= level
        d = F[1:, :-1] >= level
        idx = (a << 3) | (b << 2) | (c << 1) | d.astype(int)
        ys, xs = np.nonzero((idx != 0) & (idx != 15))

        def interp(p0, p1, v0, v1):
            t = 0.5 if v1 == v0 else (level - v0) / (v1 - v0)
            return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)

        for y, x in zip(ys, xs):
            k = int(idx[y, x])
            v = (F[y, x], F[y, x + 1], F[y + 1, x + 1], F[y + 1, x])
            P = ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))
            top, right, bottom, left = (interp(P[0], P[1], v[0], v[1]), interp(P[1], P[2], v[1], v[2]),
                                        interp(P[3], P[2], v[3], v[2]), interp(P[0], P[3], v[0], v[3]))
            table = {1: [(left, bottom)], 2: [(bottom, right)], 3: [(left, right)], 4: [(top, right)],
                     5: [(top, left), (bottom, right)] if (sum(v) / 4 < level) else [(top, right), (left, bottom)],
                     6: [(top, bottom)], 7: [(top, left)], 8: [(top, left)], 9: [(top, bottom)],
                     10: [(top, right), (left, bottom)] if (sum(v) / 4 < level) else [(top, left), (bottom, right)],
                     11: [(top, right)], 12: [(left, right)], 13: [(bottom, right)], 14: [(left, bottom)]}
            for s0, s1 in table[k]:
                segs.append((s0, s1))
        # chain
        key = lambda p: (round(p[0], 3), round(p[1], 3))
        adj = {}
        for i, (s0, s1) in enumerate(segs):
            adj.setdefault(key(s0), []).append(i)
            adj.setdefault(key(s1), []).append(i)
        used = [False] * len(segs)
        lines = []
        for i in range(len(segs)):
            if used[i]:
                continue
            used[i] = True
            line = [segs[i][0], segs[i][1]]
            for direction in (1, 0):
                while True:
                    end = line[-1] if direction else line[0]
                    nxt = None
                    for j in adj.get(key(end), []):
                        if not used[j]:
                            nxt = j
                            break
                    if nxt is None:
                        break
                    used[nxt] = True
                    s0, s1 = segs[nxt]
                    other = s1 if key(s0) == key(end) else s0
                    if direction:
                        line.append(other)
                    else:
                        line.insert(0, other)
            if len(line) >= min_len:
                lines.append([self.mm(gx, gy) for gx, gy in line])
        return lines

    def hatch(self, level, step, ang_deg, phase=0.0, dash_min=1.2):
        """parallel hatch lines across the disc, kept only where the field exceeds `level`"""
        out = []
        ang = math.radians(ang_deg)
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -uy, ux
        R = self.R
        k0 = int(-R / step) - 1
        k1 = int(R / step) + 1
        for k in range(k0, k1 + 1):
            off = k * step + phase
            if abs(off) >= R:
                continue
            half = math.sqrt(R * R - off * off)
            n = max(2, int(2 * half / 0.35))
            run = []
            for i in range(n + 1):
                t = -half + 2 * half * i / n
                x, y = self.cx + nx * off + ux * t, self.cy + ny * off + uy * t
                if self.sample(x, y) >= level:
                    run.append((x, y))
                else:
                    if len(run) >= 2 and math.dist(run[0], run[-1]) >= dash_min:
                        out.append(run)
                    run = []
            if len(run) >= 2 and math.dist(run[0], run[-1]) >= dash_min:
                out.append(run)
        return out

    def levels(self, fractions):
        return [f * self.vmax for f in fractions]


def draw_field(h, fld, levels=(0.08, 0.2, 0.4, 0.65), contour_weights=("hair", "hair", "orn", "orn"),
               hatch_from=2, hatch_steps=(1.3, 0.8), hatch_angles=(45, -45), dot_level=None, rng=None):
    """contours at the given fractions of the maximum, and crosshatch in the denser bands"""
    lv = fld.levels(levels)
    strokes = 0
    for L, wgt in zip(lv, contour_weights):
        for line in fld.contours(L):
            h.stroke(line, wgt, "ink", amp=0.1)
            strokes += 1
    for i, (st, ang) in enumerate(zip(hatch_steps, hatch_angles)):
        L = lv[min(hatch_from + i, len(lv) - 1)]
        for run in fld.hatch(L, st, ang, phase=0.3 * i):
            h.stroke(run, "hair", "ink", amp=0.05)
            strokes += 1
    return strokes


def ring_text(h, text, cx, cy, r, a_start_deg, s=2.6, color="ink"):
    """the twelve-mark hand written clockwise round a circle, mark tops outward"""
    def tf(p):
        x, y = p
        ang = math.radians(a_start_deg) + x / r
        rr = r - (y - s)        # the marks are drawn in a box (0..s); y down = inward
        return (cx + rr * math.cos(ang), cy + rr * math.sin(ang))
    xh = marks.XHand(h, tf)
    w = tx.write(xh, text, 0, 0, s, color=color)
    return a_start_deg + math.degrees(w / r)


def standing_dots(h, fld, paths, step, count, rng, r=0.33, color="ink"):
    """a sample of the agents at `step` as Book I's standing dots"""
    n = paths.shape[0]
    idx = sorted(rng.sample(range(n), min(count, n)))
    for i in idx:
        x, y = fld.mm(paths[i, step, 0], paths[i, step, 1])
        h.dot(x, y, r, color)
    return idx


def legend(P, x, y, lines, cap=2.5, lead=5.6):
    for i, t in enumerate(lines):
        P.label(t, x, y + i * lead, cap)


def spec_legend(spec, steps=None):
    return [f"AGENTS {spec['agents']}", f"STEPS {steps if steps is not None else spec['steps']}",
            f"SENSE {spec['sensor_offset']:g} AT {spec['sensor_angle_deg']:g}",
            f"TURN {spec['rotation_angle_deg']:g}", f"DEPOSIT {spec['deposit']:g}",
            f"EVAPORATE {spec['evaporation']:g}", f"SEED {spec['seed']}"]


def disc_frame(h, cx, cy, R, fringe=True):
    """the nota's own ring: a double rule with a short fringe outward (Matricis frame grammar)"""
    h.stroke(arc_pts(cx, cy, R + 0.8, 0, 360, 240), "orn", "ink", amp=0.15)
    h.stroke(arc_pts(cx, cy, R + 1.6, 0, 360, 240), "hair", "ink", amp=0.15)
    if fringe:
        marks.fringe(h, arc_pts(cx, cy, R + 1.6, 0, 360, 240), 2.4, 1.1, side=-1, weight="hair")


def scatter_stars(h, rng, cx, cy, r_in, r_out, n):
    """small asterisks in the ground above and below the nota, clear of the legend columns"""
    for _ in range(n):
        a = rng.uniform(-2.3, -0.85)
        rr = rng.uniform(r_in, r_out)
        marks.asterisk(h, cx + rr * math.cos(a), cy + rr * math.sin(a), rng.uniform(0.7, 1.2), 6, weight="hair", centre=False)


# ------------------------------------------------------------------ runs --

CENTRE = (105.0, 142.0)
RADIUS = 50.0
RING = RADIUS + 6.0
LEFT, RIGHT = 14, 166


def small_disc(h, result, step, centre, rad, vmax=None, label=None, P=None):
    """a secondary figure: the same run at another step, small, in the lower band"""
    fld = Field(result, step, centre, rad)
    if vmax:
        fld.vmax = vmax
    draw_field(h, fld, levels=(0.1, 0.3, 0.6), contour_weights=("hair", "hair", "orn"), hatch_from=2,
               hatch_steps=(0.7,), hatch_angles=(45,))
    disc_frame(h, centre[0], centre[1], rad, fringe=False)
    if label and P:
        P.label(label, centre[0], centre[1] + rad + 6.0, 2.5, "center")
    return fld

RUNS = {
    "i": {"snapshots": [20, 45, 70], "steps": 70, "seed": 11},
    "ii": {"snapshots": [90], "steps": 90, "seed": 23, "sensor_offset": 14.0},
    "iii": {"snapshots": [60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180], "steps": 180, "stop_deposit_at": 60,
            "evaporation": 0.02, "seed": 37},
    "iv": {"snapshots": [160], "steps": 160, "seed": 41, "sensor_offset": 11.0},
    "v": {"snapshots": [420], "steps": 420, "seed": 53, "agents": 1700, "deposit": 2.0, "evaporation": 0.06,
          "nodes": [[80, 38, 40], [126, 62, 40], [132, 104, 40], [92, 130, 40], [50, 112, 40], [44, 66, 40], [100, 94, 40]]},
}


def run_for(key):
    r = physarum.run(RUNS[key])
    return r, physarum.manifest(r)


def hidden_for(num, m):
    return f"NOTA {num} RUN {m['id']}"


def write_manifest(out_dir, m):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "run-manifest.json"), "w") as f:
        json.dump(m, f, indent=1)


# ------------------------------------------------------------------- notae --

def nota_i(out_dir):
    """Deposit — the Ars Vestigiorum: the field as the agents left it, the agents still on it"""
    r, m = run_for("i")
    P = Nota("I", "Deposit", "ARS VESTIGIORUM / THE FIELD AS THE AGENTS LEFT IT", "nota-i-deposit",
             "The address is not the verse.", 1, hidden_for("I", m), 1101,
             strap="MARKED BY THE CAST / READ WHOLE / NOT YET ERASED")
    h, rng = P.art, P.rng
    cx, cy = CENTRE
    fld = Field(r, 70, CENTRE, RADIUS)
    draw_field(h, fld)
    standing_dots(h, fld, r["paths"], 70, 150, rng)
    disc_frame(h, cx, cy, RADIUS)
    end = ring_text(h, "THE ADDRESS IS NOT THE VERSE", cx, cy, RING, -150)
    ring_text(h, "WHAT IS HEARD IS NOT YET WHAT IS KNOWN", cx, cy, RING, end + 14)
    scatter_stars(h, rng, cx, cy, RING + 4, RING + 24, 10)
    # one deposit traced in red: the agent that travelled farthest over its last thirty steps
    P_ = r["paths"]
    travel = np.sum(np.hypot(np.diff(P_[:, 40:71, 0], axis=1), np.diff(P_[:, 40:71, 1], axis=1)), axis=1)
    i = int(np.argmax(travel))
    trail = [fld.mm(*p) for p in P_[i, 40:71]]
    h.stroke(catmull(trail, 4), "core", "red", amp=0.1)
    h.dot(trail[-1][0], trail[-1][1], 0.45, "red")
    # the lower band: the same cast earlier, the field forming
    small_disc(h, r, 20, (52.0, 217.0), 12.5, vmax=fld.vmax, label="STEP 20", P=P)
    small_disc(h, r, 45, (158.0, 217.0), 12.5, vmax=fld.vmax, label="STEP 45", P=P)
    marks.dotted(h, [(67, 217), (90, 217)], 1.6, 0.26, skip_ends=False)
    marks.dotted(h, [(120, 217), (143, 217)], 1.6, 0.26, skip_ends=False)
    P.label("STEP 70 ABOVE", 105, 218.5, 2.5, "center")
    legend(P, RIGHT, 86, ["THE CAST"] + spec_legend(r["spec"]))
    legend(P, LEFT, 86, ["THE FIELD", "CONTOURS AT", "8 20 40 65", "OF THE MAXIMUM", "HATCH ABOVE 40", "DOTS: 150 OF", f"{r['spec']['agents']} AGENTS", "RED: ONE AGENT", "THIRTY STEPS"])
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    write_manifest(out_dir, m)
    P.export(out_dir, {"manifest_id": m["id"], "snapshot": 70, "field_max": round(fld.vmax, 3)})


def nota_ii(out_dir):
    """Sense — the Ars Vestigiorum: the field as one agent perceives it"""
    r, m = run_for("ii")
    P = Nota("II", "Sense", "ARS VESTIGIORUM / THE FIELD AS ONE AGENT PERCEIVES IT", "nota-ii-sense",
             "Only the gradient, only within range.", 2, hidden_for("II", m), 1102,
             strap="THREE SENSORS / ONE OFFSET / THE REST UNSEEN")
    h, rng = P.art, P.rng
    cx, cy = CENTRE
    fld = Field(r, 90, CENTRE, RADIUS)
    spec = r["spec"]
    # the agent: the one nearest the centre at the last step
    pts = r["paths"][:, 90, :]
    i = int(np.argmin((pts[:, 0] - fld.gcx) ** 2 + (pts[:, 1] - fld.gcy) ** 2))
    ax, ay = fld.mm(pts[i, 0], pts[i, 1])
    prev = fld.mm(*r["paths"][i, 89])
    hd = math.atan2(ay - prev[1], ax - prev[0])
    SO = spec["sensor_offset"] * fld.scale
    SA = math.radians(spec["sensor_angle_deg"])
    view = SO * 2.2
    # the whole field as a ghost: two contours, dotted
    for lv_, sp in ((0.1, 1.1), (0.35, 1.6)):
        for line in fld.contours(fld.levels([lv_])[0]):
            marks.dotted(h, line, sp, 0.15, skip_ends=False)
    # within range: the field in full, clipped to the disc of view
    lv = fld.levels((0.08, 0.2, 0.4, 0.65))
    inside = lambda p: math.dist(p, (ax, ay)) <= view
    for L, wgt in zip(lv, ("hair", "hair", "orn", "orn")):
        for line in fld.contours(L):
            run = []
            for p in line:
                if inside(p):
                    run.append(p)
                else:
                    if len(run) > 1:
                        h.stroke(run, wgt, "ink", amp=0.1)
                    run = []
            if len(run) > 1:
                h.stroke(run, wgt, "ink", amp=0.1)
    for (st, ang, L) in ((1.3, 45, lv[2]), (0.8, -45, lv[3])):
        for run in fld.hatch(L, st, ang):
            seg = [p for p in run if inside(p)]
            if len(seg) > 1:
                h.stroke(seg, "hair", "ink", amp=0.05)
    # the disc of view, and the three sensors
    h.stroke(arc_pts(ax, ay, view, 0, 360, 120), "orn", "ink", amp=0.2)
    marks.fringe(h, arc_pts(ax, ay, view, 0, 360, 120), 2.0, 0.9, side=1, weight="hair")
    for da in (-SA, 0.0, SA):
        sx, sy = ax + SO * math.cos(hd + da), ay + SO * math.sin(hd + da)
        h.stroke([(ax, ay), (sx, sy)], "hair", "ink", amp=0.05)
        h.ring(sx, sy, 0.9, "hair", "ink")
    marks.sig_candidate(h, ax, ay, 1.3)
    # the strongest sensor, in red, and the turn it dictates
    vals = [fld.sample(ax + SO * math.cos(hd + da), ay + SO * math.sin(hd + da)) for da in (-SA, 0.0, SA)]
    k = int(np.argmax(vals))
    da = (-SA, 0.0, SA)[k]
    sx, sy = ax + SO * math.cos(hd + da), ay + SO * math.sin(hd + da)
    h.stroke([(ax, ay), (sx, sy)], "core", "red", amp=0.05)
    h.dot(sx, sy, 0.45, "red")
    disc_frame(h, cx, cy, RADIUS)
    end = ring_text(h, "ONLY THE GRADIENT", cx, cy, RING, -160)
    ring_text(h, "ONLY WITHIN RANGE", cx, cy, RING, end + 60)
    scatter_stars(h, rng, cx, cy, RING + 4, RING + 24, 8)
    # the lower band: the view enlarged, with what each sensor read
    mag = 1.5
    mx, my, mr = 105.0, 218.0, 15.0
    tf = lambda p: (mx + (p[0] - ax) * mag, my + (p[1] - ay) * mag)
    clipm = lambda p: math.dist(p, (ax, ay)) <= mr / mag
    for L, wgt in zip(lv, ("hair", "hair", "orn", "orn")):
        for line in fld.contours(L):
            run = []
            for p in line:
                if clipm(p):
                    run.append(tf(p))
                else:
                    if len(run) > 1:
                        h.stroke(run, wgt, "ink", amp=0.1)
                    run = []
            if len(run) > 1:
                h.stroke(run, wgt, "ink", amp=0.1)
    h.stroke(arc_pts(mx, my, mr, 0, 360, 120), "orn", "ink", amp=0.15)
    for j, da in enumerate((-SA, 0.0, SA)):
        sx, sy = tf((ax + SO * math.cos(hd + da), ay + SO * math.sin(hd + da)))
        h.stroke([(mx, my), (sx, sy)], "core" if j == k else "hair", "red" if j == k else "ink", amp=0.05)
        h.ring(sx, sy, 1.4, "orn", "red" if j == k else "ink")
    marks.sig_candidate(h, mx, my, 1.6)
    P.label(f"LEFT {vals[0]:.1f}", 48, 212, 2.5)
    P.label(f"FRONT {vals[1]:.1f}", 48, 218, 2.5)
    P.label(f"RIGHT {vals[2]:.1f}", 48, 224, 2.5)
    P.label("TURNS " + ("LEFT" if k == 0 else "RIGHT" if k == 2 else "NOT AT ALL"), 140, 215, 2.5)
    P.label(f"VIEW X {mag:g}", 140, 221, 2.5)
    legend(P, RIGHT, 86, ["THE CAST"] + spec_legend(spec))
    legend(P, LEFT, 86, ["ONE AGENT", f"OFFSET {spec['sensor_offset']:g} CELLS", f"ANGLE {spec['sensor_angle_deg']:g}",
                         "VIEW: OFFSET X 2.2", "BEYOND IT", "TWO CONTOURS", "AS A GHOST", "RED: THE SENSOR", "THAT WON"])
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    write_manifest(out_dir, m)
    P.export(out_dir, {"manifest_id": m["id"], "snapshot": 90, "agent": i, "sensor_values": [round(v, 3) for v in vals]})


def nota_iii(out_dir):
    """Decay — the Ars Mutationum: the same field at three later times, deposition stopped"""
    r, m = run_for("iii")
    P = Nota("III", "Decay", "ARS MUTATIONUM / THE SAME FIELD AT THREE LATER TIMES", "nota-iii-decay",
             "The number does not date the line.", 3, hidden_for("III", m), 1103,
             strap="DEPOSIT STOPPED AT 60 / EVAPORATION CONTINUES / ONE TRAIL SURVIVES")
    h, rng = P.art, P.rng
    rad = 25.0
    centres = [(68.0, 124.0), (142.0, 124.0), (105.0, 186.0)]
    steps = [60, 80, 110]
    vmax0 = float(r["field"][60].max())
    last = None
    for (c, t) in zip(centres, steps):
        fld = Field(r, t, c, rad)
        fld.vmax = vmax0            # the same levels on all three, so thinning is thinning
        draw_field(h, fld, hatch_steps=(0.9, 0.6))
        disc_frame(h, c[0], c[1], rad, fringe=(t == steps[-1]))
        last = fld
    # the surviving trail: the longest contour at the second level still standing at t3, in red
    sv, red_level = [], None
    for frac in (0.65, 0.4, 0.2, 0.08):
        sv = sorted(last.contours(last.levels([frac])[0]), key=lambda ln: -len(ln))[:1]
        if sv:
            red_level = frac
            break
    for line in sv:
        h.stroke(line, "core", "red", amp=0.1)
    # the sequence: dotted arrows between the panels, and the time at each
    for a, b in ((0, 1), (1, 2)):
        p0, p1 = centres[a], centres[b]
        d = math.dist(p0, p1)
        ux, uy = (p1[0] - p0[0]) / d, (p1[1] - p0[1]) / d
        pad1 = rad + 4 if b == 1 else rad + 11
        seg = [(p0[0] + ux * (rad + 4), p0[1] + uy * (rad + 4)), (p1[0] - ux * pad1, p1[1] - uy * pad1)]
        marks.dotted(h, seg, 1.6, 0.26, skip_ends=False)
        marks.arrowhead(h, seg[1], math.degrees(math.atan2(uy, ux)), 2.2, weight="orn")
    for (c, t, lab) in zip(centres[:2], steps[:2], ("T ONE", "T TWO")):
        P.label(lab, c[0], c[1] - rad - 5.0, 2.5, "center")
        P.label(f"STEP {t}", c[0], c[1] + rad + 7.0, 2.5, "center")
    P.label("T THREE", 150, 186, 2.5)
    P.label(f"STEP {steps[2]}", 150, 192, 2.5)
    # the ring text round the last panel
    ring_text(h, "THE NUMBER DOES NOT DATE THE LINE", centres[2][0], centres[2][1], rad + 6.0, -150)
    # the decay scale: the field maximum every ten steps from the stop, as a row of bars
    bx, by, bw, bh = 14.0, 232.0, 3.4, 24.0
    maxes = [float(r["field"][t].max()) for t in range(60, 181, 10)]
    for j, v in enumerate(maxes):
        x = bx + j * bw
        h.straight([(x, by), (x, by - bh * v / maxes[0])], "orn", "red" if j == len(maxes) - 1 else "ink")
        h.dot(x, by - bh * v / maxes[0], 0.3, "red" if j == len(maxes) - 1 else "ink")
    h.straight([(bx - 1.5, by), (bx + 12 * bw + 1.5, by)], "hair", "ink")
    P.label("MAXIMUM, STEPS 60 TO 180", bx, 236.5, 2.5)
    scatter_stars(h, rng, 105, 150, 78, 95, 8)
    legend(P, RIGHT, 86, ["THE CAST"] + spec_legend(r["spec"], 180))
    legend(P, LEFT, 86, ["LEVELS FIXED", "AT T ONE", "RED: THE LONGEST", f"CONTOUR AT {int(red_level * 100)}", "STILL STANDING", "AT T THREE"])
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    write_manifest(out_dir, m)
    P.export(out_dir, {"manifest_id": m["id"], "snapshots": steps, "field_max_t1": round(vmax0, 3),
                       "field_max_by_ten": [round(v, 3) for v in maxes], "red_level_fraction": red_level})


def nota_iv(out_dir):
    """Follow — the Ars Sortium: the paths only, no field, converging where nobody told them to"""
    r, m = run_for("iv")
    P = Nota("IV", "Follow", "ARS SORTIUM / THE PATHS ONLY / THE FIELD WITHHELD", "nota-iv-follow",
             "The neighbour was chosen.", 4, hidden_for("IV", m), 1104,
             strap="THREE HUNDRED AND TWENTY AGENTS / SIXTY STEPS / ONE THAT DID NOT CONVERGE")
    h, rng = P.art, P.rng
    cx, cy = CENTRE
    fld = Field(r, 160, CENTRE, RADIUS)
    paths = r["paths"]
    n = paths.shape[0]
    t0, t1 = 100, 160
    # the field underfoot, averaged over the window, per agent: who followed and who did not
    F = r["field"][160]
    under = np.zeros(n)
    for i in range(n):
        seg = paths[i, t0:t1 + 1]
        ix = np.clip(np.rint(seg[:, 0]).astype(int), 0, fld.W - 1)
        iy = np.clip(np.rint(seg[:, 1]).astype(int), 0, fld.H - 1)
        under[i] = F[iy, ix].mean()
    moved = np.array([np.sum(np.hypot(np.diff(paths[i, t0:t1 + 1, 0]), np.diff(paths[i, t0:t1 + 1, 1]))) for i in range(n)])
    cand = [i for i in range(n) if moved[i] > 24]
    chosen = sorted(rng.sample(cand, min(320, len(cand))))

    def smooth(seg, k=5):
        out = []
        for j in range(len(seg)):
            a, b = max(0, j - k // 2), min(len(seg), j + k // 2 + 1)
            out.append((sum(p[0] for p in seg[a:b]) / (b - a), sum(p[1] for p in seg[a:b]) / (b - a)))
        return out

    for i in chosen:
        pts = smooth([fld.mm(*p) for p in paths[i, t0:t1 + 1]])
        h.stroke(pts, "hair", "ink", amp=0.08)
        h.dot(pts[-1][0], pts[-1][1], 0.28, "ink")
    # the one that did not converge: the moving agent with the least field underfoot
    far = [i for i in cand if math.dist(paths[i, t0], paths[i, t1]) > 14] or cand
    wander = min(far, key=lambda i: under[i])
    pts = smooth([fld.mm(*p) for p in paths[wander, t0:t1 + 1]])
    h.stroke(pts, "core", "red", amp=0.1)
    marks.sig_candidate(h, pts[-1][0], pts[-1][1], 1.2, color="red")
    disc_frame(h, cx, cy, RADIUS)
    end = ring_text(h, "THE NEIGHBOUR WAS CHOSEN", cx, cy, RING, -150)
    ring_text(h, "NO AGENT DREW THE ROUTE", cx, cy, RING, end + 30)
    scatter_stars(h, rng, cx, cy, RING + 4, RING + 24, 8)
    # the lower band: the run as a line, the window drawn on it
    bx0, bx1, by = 30.0, 180.0, 220.0
    h.straight([(bx0, by), (bx1, by)], "orn", "ink")
    for t in range(0, t1 + 1, 20):
        x = bx0 + (bx1 - bx0) * t / t1
        h.straight([(x, by - 1.5), (x, by + 1.5)], "hair", "ink")
        P.label(str(t), x, by + 6.5, 2.5, "center")
    xw0, xw1 = bx0 + (bx1 - bx0) * t0 / t1, bx1
    h.straight([(xw0, by - 3.2), (xw1, by - 3.2)], "core", "red")
    marks.dotted(h, [(xw0, by - 3.2), (xw0, by - 12)], 1.4, 0.22, skip_ends=False)
    P.label("THE WINDOW DRAWN", (xw0 + xw1) / 2, by - 14, 2.5, "center")
    P.label("STEPS OF THE RUN", bx0, by - 14, 2.5)
    legend(P, RIGHT, 86, ["THE CAST"] + spec_legend(r["spec"]))
    legend(P, LEFT, 86, ["THE PATHS", f"STEPS {t0} TO {t1}", f"OF {len(chosen)} AGENTS", "THAT MOVED", "SMOOTHED OVER", "FIVE STEPS", "RED: THE ONE", "WITH LEAST FIELD", "UNDERFOOT"])
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    write_manifest(out_dir, m)
    P.export(out_dir, {"manifest_id": m["id"], "window": [t0, t1], "drawn_agents": chosen, "wanderer": wander,
                       "field_underfoot_wanderer": round(float(under[wander]), 3)})


def nota_v(out_dir):
    """Nota Generalis — a network relaxed between fixed nodes; no corpus"""
    r, m = run_for("v")
    P = Nota("V", "Nota Generalis", "A NETWORK BETWEEN FIXED NODES / NO CORPUS", "nota-v-generalis",
             "The path has no corpus.", 5, hidden_for("V", m), 1105,
             strap="SEVEN NODES / THE AGENTS FIND THE ROUTES / NOBODY ASSIGNED THEM")
    h, rng = P.art, P.rng
    cx, cy = CENTRE
    fld = Field(r, 420, CENTRE, RADIUS)
    nodes = r["spec"]["nodes"]
    # the nodes dominate the maximum; take levels from the field away from them
    F = r["field"][420].copy()
    for (nx0, ny0, _) in nodes:
        y0, x0 = int(ny0), int(nx0)
        F[max(0, y0 - 4):y0 + 5, max(0, x0 - 4):x0 + 5] = 0
    fld.vmax = float(np.percentile(F[F > 0], 99.5))
    draw_field(h, fld, levels=(0.1, 0.25, 0.5, 0.8), hatch_steps=(1.2, 0.75))
    npts = []
    for k, (nx0, ny0, _) in enumerate(nodes):
        x, y = fld.mm(nx0, ny0)
        npts.append((x, y))
        marks.sig_standing(h, x, y, 1.3, orn=1.0)
        P.label(str(k + 1), x + 5.4, y + 1.0, 2.5)
    disc_frame(h, cx, cy, RADIUS)
    end = ring_text(h, "THE PATH HAS NO CORPUS", cx, cy, RING, -150)
    ring_text(h, "WHAT THE ARTS LOOK LIKE WITHOUT A BOOK", cx, cy, RING, end + 12)
    # the centre: nothing
    h.dot(cx, cy, 0.3, "red")
    h.stroke(arc_pts(cx, cy, 2.4, 0, 360, 40), "hair", "red", amp=0.2)
    scatter_stars(h, rng, cx, cy, RING + 4, RING + 24, 8)
    # the lower band: which pairs of nodes a continuous trail joins at the second level
    # (a flood fill over the cells at or above the level, from each node's cell)
    Lj = fld.levels([0.25])[0]
    Fg = r["field"][420]
    above = Fg >= Lj
    comp = -np.ones(Fg.shape, dtype=int)
    from collections import deque
    cid = 0
    for (nx0, ny0, _) in nodes:
        y0, x0 = int(ny0), int(nx0)
        if comp[y0, x0] >= 0 or not above[y0, x0]:
            continue
        q = deque([(y0, x0)])
        comp[y0, x0] = cid
        while q:
            yy, xx = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                y2, x2 = yy + dy, xx + dx
                if 0 <= y2 < Fg.shape[0] and 0 <= x2 < Fg.shape[1] and above[y2, x2] and comp[y2, x2] < 0:
                    comp[y2, x2] = cid
                    q.append((y2, x2))
        cid += 1
    cells = [comp[int(ny0), int(nx0)] for (nx0, ny0, _) in nodes]
    edges = [(a, b) for a in range(len(nodes)) for b in range(a + 1, len(nodes)) if cells[a] >= 0 and cells[a] == cells[b]]
    gx, gy, gr = 105.0, 217.0, 14.0
    gp = [(gx + gr * math.cos(math.radians(-90 + 360 * k / 7)), gy + gr * math.sin(math.radians(-90 + 360 * k / 7))) for k in range(7)]
    for (a, b) in edges:
        h.stroke([gp[a], gp[b]], "orn", "ink", amp=0.1)
    for k, (x, y) in enumerate(gp):
        h.dot(x, y, 0.55, "ink")
        P.label(str(k + 1), x + 2.6 * math.cos(math.radians(-90 + 360 * k / 7)) + 0.8, y + 2.6 * math.sin(math.radians(-90 + 360 * k / 7)) + 1.0, 2.5)
    P.label("JOINED BY A TRAIL", 140, 213, 2.5)
    P.label("AT LEVEL 25 OR MORE", 140, 219, 2.5)
    P.label(f"{len(edges)} OF 21 PAIRS", 140, 225, 2.5)
    P.label("THE NODES", 48, 213, 2.5)
    P.label("AS PLACED", 48, 219, 2.5)
    legend(P, RIGHT, 86, ["THE CAST"] + spec_legend(r["spec"]))
    legend(P, LEFT, 86, ["SEVEN NODES", "EACH DEPOSITS 40", "PER STEP", "LEVELS FROM THE", "99.5 PERCENTILE", "AWAY FROM NODES", "RED: THE CENTRE", "WHICH IS EMPTY"])
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    write_manifest(out_dir, m)
    P.export(out_dir, {"manifest_id": m["id"], "snapshot": 420, "nodes": nodes, "joined_pairs": [[a + 1, b + 1] for a, b in edges]})


NOTAE = {"i": nota_i, "ii": nota_ii, "iii": nota_iii, "iv": nota_iv, "v": nota_v}
STEMS = {"i": "nota-i-deposit", "ii": "nota-ii-sense", "iii": "nota-iii-decay", "iv": "nota-iv-follow", "v": "nota-v-generalis"}


def build(which, out_root):
    keys = list(NOTAE) if which == "all" else [which]
    for k in keys:
        NOTAE[k](os.path.join(out_root, STEMS[k]))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out")
    build(which, out)
