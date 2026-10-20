#!/usr/bin/env python3
"""Make a stroke-only, two-pen edition of Tabula XI from its existing SVG.

All output coordinates are millimetres. No original generators or hard-coded
Claude workspace paths are needed. Run from any directory; see README.md.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

try:
    from HersheyFonts import HersheyFonts
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install the plotter requirements: python -m pip install -r plotter/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "canvas/assets/xi_face.svg"
TITLE_FONT = Path(__file__).resolve().parents[5] / "sources/codex-intervallorum/common/fonts/IMFeENrm28P.ttf"
SVG = "http://www.w3.org/2000/svg"
INKSCAPE = "http://www.inkscape.org/namespaces/inkscape"
ET.register_namespace("", SVG)
ET.register_namespace("inkscape", INKSCAPE)
Point = tuple[float, float]
Stroke = list[Point]
BLACK, RED = "#171717", "#a13c2b"

# Original, compact monoline capitals; coordinates on a 4 x 6 grid.
# Spaces separate strokes, commas separate vertices. No outline fonts for labels.
ALPHABET = {
    "A": "06,20,46 14,34", "B": "06,00,30,41,32,02 32,43,45,36,06",
    "C": "40,10,01,05,16,46", "D": "06,00,20,41,45,26,06",
    "E": "40,00,06,46 03,33", "F": "40,00,06 03,33",
    "G": "40,10,01,05,16,46,43,23", "H": "00,06 40,46 03,43",
    "I": "00,40 20,26 06,46", "J": "00,40,45,36,16,05",
    "K": "00,06 40,03,46", "L": "00,06,46",
    "M": "06,00,23,40,46", "N": "06,00,46,40",
    "O": "10,30,41,45,36,16,05,01,10", "P": "06,00,30,41,42,33,03",
    "Q": "10,30,41,45,36,16,05,01,10 24,47", "R": "06,00,30,41,42,33,03 23,46",
    "S": "40,10,01,02,13,33,44,45,36,06", "T": "00,40 20,26",
    "U": "00,05,16,36,45,40", "V": "00,26,40",
    "W": "00,16,23,36,40", "X": "00,46 40,06", "Y": "00,23,40 23,26",
    "Z": "00,40,06,46", "0": "10,30,41,45,36,16,05,01,10 04,42",
    "1": "01,20,26 06,46", "2": "01,10,30,41,42,06,46",
    "3": "00,30,41,32,22 32,43,45,36,06", "4": "30,03,43 30,36",
    "5": "40,00,03,33,44,45,36,06", "6": "40,10,01,05,16,36,45,44,33,03",
    "7": "00,40,16", "8": "10,30,41,42,33,13,02,01,10 13,04,05,16,36,45,44,33",
    "9": "43,13,02,01,10,30,41,45,36,06", ".": "25,26", "-": "03,43",
    "/": "40,06", ":": "21,22 24,25",
}


def monoline(text: str, x: float, y: float, height: float,
             align: str = "left") -> list[Stroke]:
    """Label top-left in mm; fixed advance 1 x cap height, cap width 2/3 height."""
    text = text.upper()
    unit = height / 6
    width = max(0, (len(text) * 6 - 2) * unit)
    x -= width / 2 if align == "center" else width if align == "right" else 0
    strokes = []
    for char in text:
        if char != " ":
            if char not in ALPHABET:
                raise ValueError(f"Unsupported monoline character: {char!r}")
            for stroke in ALPHABET[char].split():
                strokes.append([(x + int(p[0]) * unit, y + int(p[1]) * unit)
                                for p in stroke.split(",")])
        x += height
    return strokes


_HERSHEY = {}


def hershey(text: str, x: float, y: float, cap: float, face: str = "timesr",
            align: str = "left") -> list[Stroke]:
    """Single-stroke Hershey lettering in mm. (x, y) is the top of the capitals."""
    if face not in _HERSHEY:
        font = HersheyFonts()
        font.load_default_font(face)
        font.normalize_rendering(100)
        hs = [p for seg in font.lines_for_text("H") for p in seg]
        _HERSHEY[face] = (font, min(q[1] for q in hs), max(q[1] for q in hs))
    font, base, top = _HERSHEY[face]
    k = cap / (top - base)
    strokes: list[Stroke] = []
    for a, b in font.lines_for_text(text):
        a = (a[0] * k, (top - a[1]) * k)
        b = (b[0] * k, (top - b[1]) * k)
        if strokes and math.dist(strokes[-1][-1], a) < 1e-6:
            strokes[-1].append(b)
        else:
            strokes.append([a, b])
    if not strokes:
        return []
    x0 = min(p[0] for s_ in strokes for p in s_)
    x1 = max(p[0] for s_ in strokes for p in s_)
    shift = x - x0 - ((x1 - x0) / 2 if align == "center" else (x1 - x0) if align == "right" else 0)
    return [[(px + shift, py + y) for px, py in s_] for s_ in strokes]


def small_caps(text: str, x: float, y: float, cap: float, align: str = "left") -> list[Stroke]:
    """Engraved small capitals: initials at full height, the rest at 0.74, one baseline.
    A word given wholly in capitals (a numeral such as XI) stays at full height throughout."""
    pieces, cx = [], 0.0
    for word in text.split():
        for i, ch in enumerate(word):
            h = cap if (word.isupper() or (i == 0 and ch.isupper())) else cap * .74
            g = hershey(ch.upper(), cx, cap - h, h)
            if g:
                pieces.append(g)
                cx = max(p[0] for s_ in g for p in s_) + cap * .16
        cx += cap * .42
    strokes = [s_ for g in pieces for s_ in g]
    if not strokes:
        return []
    width = max(p[0] for s_ in strokes for p in s_)
    shift = x - (width / 2 if align == "center" else width if align == "right" else 0)
    return [[(px + shift, py + y) for px, py in s_] for s_ in strokes]


def wrap_hershey(text: str, x: float, y: float, cap: float, face: str, width: float,
                 leading: float) -> list[Stroke]:
    """Greedy word wrap for a hand-lettered note."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        g = hershey(trial, 0, 0, cap, face)
        w = max(p[0] for s_ in g for p in s_) - min(p[0] for s_ in g for p in s_)
        if cur and w > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    out = []
    for i, line in enumerate(lines):
        out += hershey(line, x, y + i * leading, cap, face)
    return out


def distance_to_segment(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == dy == 0:
        return math.dist(p, a)
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx*dx + dy*dy)))
    return math.dist(p, (a[0] + t*dx, a[1] + t*dy))


class FlattenPen(BasePen):
    """Flatten SVG/font curves with a bounded control-polygon error."""
    def __init__(self, glyphset=None, tolerance=0.05):
        super().__init__(glyphset)
        self.tolerance = tolerance
        self.strokes: list[Stroke] = []
        self.current: Stroke = []

    def _moveTo(self, p):
        self._endPath()
        self.current = [tuple(p)]

    def _lineTo(self, p):
        self.current.append(tuple(p))

    def _curveToOne(self, p1, p2, p3):
        def recurse(a, b, c, d, depth=0):
            if depth >= 18 or max(distance_to_segment(b, a, d), distance_to_segment(c, a, d)) <= self.tolerance:
                self.current.append(tuple(d))
                return
            mid = lambda u, v: ((u[0]+v[0])/2, (u[1]+v[1])/2)
            ab, bc, cd = mid(a,b), mid(b,c), mid(c,d)
            abc, bcd = mid(ab,bc), mid(bc,cd)
            middle = mid(abc,bcd)
            recurse(a, ab, abc, middle, depth+1)
            recurse(middle, bcd, cd, d, depth+1)
        recurse(self.current[-1], p1, p2, p3)

    def _qCurveToOne(self, p1, p2):
        p0 = self.current[-1]
        self._curveToOne((p0[0]+(p1[0]-p0[0])*2/3, p0[1]+(p1[1]-p0[1])*2/3),
                         (p2[0]+(p1[0]-p2[0])*2/3, p2[1]+(p1[1]-p2[1])*2/3), p2)

    def _closePath(self):
        if self.current and self.current[-1] != self.current[0]:
            self.current.append(self.current[0])
        self._endPath()

    def _endPath(self):
        if len(self.current) > 1:
            self.strokes.append(self.current)
        self.current = []


@dataclass
class Layout:
    width: float
    height: float
    margin: float

    @property
    def scale(self):
        return min((self.width-2*self.margin)/1000, (self.height-2*self.margin)/1600)

    def point(self, p):
        s = self.scale
        return ((self.width-1000*s)/2+p[0]*s, (self.height-1600*s)/2+p[1]*s)


def outline_title(layout: Layout, spacing: float | None = None) -> list[Stroke]:
    """The large serif title as contours; with `spacing`, hatched solid so it reads as type."""
    with TTFont(TITLE_FONT) as font:
        glyphs, cmap = font.getGlyphSet(), font.getBestCmap()
        scale = 42 * layout.scale / font["head"].unitsPerEm
        text = "Of the Closed Neck"
        advance = sum(glyphs[cmap[ord(c)]].width for c in text) * scale
        x, baseline = layout.width/2-advance/2, layout.point((0,185))[1]
        strokes = []
        for char in text:
            glyph = glyphs[cmap[ord(char)]]
            pen = FlattenPen(glyphs, tolerance=0.015/scale)
            glyph.draw(pen)
            pen._endPath()
            contours = [[(x+px*scale, baseline-py*scale) for px,py in s] for s in pen.strokes]
            if spacing is None:
                strokes.extend(contours)
            else:
                shape = Polygon()
                for c in contours:          # even-odd: counters cut themselves out
                    if len(c) >= 4:
                        shape = shape.symmetric_difference(Polygon(c).buffer(0))
                strokes.extend(hatch(shape, spacing))
            x += glyph.width*scale
    return strokes


def line_parts(geom):
    if geom.is_empty:
        return []
    if geom.geom_type in ("LineString", "LinearRing"):
        return [list(geom.coords)]
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in line_parts(g)]
    return []


def hatch(shape, spacing):
    """Real horizontal pen strokes plus contours; no SVG fill dependency."""
    if shape.is_empty:
        return []
    result = line_parts(shape.boundary)
    x0,y0,x1,y1 = shape.bounds
    if y1-y0 < spacing:
        ys = [(y0+y1)/2]
    else:
        ys = [y0+spacing/2+i*spacing for i in range(math.ceil((y1-y0)/spacing))]
    for y in ys:
        result.extend(line_parts(shape.intersection(LineString([(x0-1,y),(x1+1,y)]))))
    return result


def geometry(layout: Layout, spacing: float, pen_width: float):
    root = ET.parse(SOURCE).getroot()
    if root.get("viewBox") != "0 0 1000 1600":
        raise ValueError("Source geometry changed: review its coordinate system before exporting.")
    dark_strokes, red_strokes, dark_solids, red_solids, knockouts = [], [], [], [], []
    dropped = 0
    for e in root:
        if e.tag != f"{{{SVG}}}path" or e.get("transform"):
            raise ValueError("Source contains an unsupported element or transform; review it first.")
        stroke, fill = e.get("stroke", "none"), e.get("fill", "none")
        is_dark = stroke in ("#1c1813", "#6d5f4b") or fill in ("#1c1813", "#6d5f4b")
        is_red = stroke == "#9e3b24" or fill == "#9e3b24"
        # Light asterisks cut out the filled corner tablets. Other pale rules are paper effects.
        is_knockout = stroke == "#f6efde" and e.get("stroke-width") == "1.55"
        if float(e.get("opacity", "1")) < .9 or not (is_dark or is_red or is_knockout):
            dropped += 1
            continue
        pen = FlattenPen(tolerance=0.015/layout.scale)
        parse_path(e.get("d", ""), pen)
        pen._endPath()
        for s in pen.strokes:
            mm = [layout.point(p) for p in s]
            if is_knockout:
                knockouts.append(LineString(mm).buffer(pen_width*.85, cap_style="round"))
            elif stroke != "none":
                (red_strokes if is_red else dark_strokes).append(mm)
            else:
                if mm[0] != mm[-1]:
                    raise ValueError("A source fill is not closed.")
                poly = Polygon(mm)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                (red_solids if is_red else dark_solids).append(poly)
    knockout = unary_union(knockouts)
    for poly in dark_solids:
        dark_strokes.extend(hatch(poly.difference(knockout), spacing))
    for poly in red_solids:
        red_strokes.extend(hatch(poly, spacing))
    return dark_strokes, red_strokes, dropped


def lettering(layout, spacing):
    """Three hands, as on the plate: engraved small capitals and roman (Hershey Times),
    the plotter's own monoline capitals for its stamp, and M.'s script note (Hershey Script)."""
    black = outline_title(layout, spacing)
    red = []
    s = layout.scale

    def at(x, y):
        return layout.point((x, y))
    # engraved: running heads, inset, trial numerals, folio
    black += small_caps("Clavicula Matricis", *at(56, 28), 13 * s)
    red += small_caps("Tabula XI", *at(944, 28), 13 * s, "right")
    black += hershey("Leave the neck.", *at(104, 708), 15 * s, "timesr")
    for text, x in [("I", 112), ("II", 397), ("III", 682)]:
        black += small_caps(text, *at(x, 1262), 9.5 * s)
    black += small_caps("XI", *at(500, 1570), 9.5 * s, "center")
    # the plotter's stamp keeps the machine capitals
    xx, yy = at(788, 699)
    red += monoline("PASSAGE", xx, yy, 11 * s, "right")
    xx, yy = at(807, 699)
    red += monoline("RESTORED.", xx, yy, 11 * s)
    # M.'s note in script
    red += wrap_hershey("Only to the lower gate.", *at(806, 733), 15 * s, "scripts", 112 * s, 26 * s)
    return black, red


def optimize(strokes: list[Stroke]) -> list[Stroke]:
    """Simplify sub-pen jitter, remove exact duplicates, reorder without joining gaps."""
    clean, seen = [], set()
    for stroke in strokes:
        if len(stroke) < 2 or LineString(stroke).length < .008:
            continue
        simplified = list(LineString(stroke).simplify(.015, preserve_topology=True).coords)
        p = tuple((round(x,3),round(y,3)) for x,y in simplified)
        if len(set(p)) < 2:
            continue
        key = min(p, p[::-1])
        if key not in seen:
            clean.append(list(p)); seen.add(key)
    result, current = [], (0.,0.)
    while clean:
        best_i, reverse, best = 0, False, float("inf")
        for i,s in enumerate(clean):
            for rev,point in ((False,s[0]),(True,s[-1])):
                distance = (point[0]-current[0])**2+(point[1]-current[1])**2
                if distance < best:
                    best_i, reverse, best = i, rev, distance
        s = clean.pop(best_i)
        if reverse:
            s.reverse()
        result.append(s); current=s[-1]
    return result


def registration(layout):
    # These are deliberately outside the artwork. Same coordinates in every pass.
    strokes = []
    for x,y in [(8,8),(layout.width-8,8),(8,layout.height-8),(layout.width-8,layout.height-8)]:
        strokes.extend([[(x-2,y),(x+2,y)],[(x,y-2),(x,y+2)]])
    return strokes


def svg_file(path, layout, layers, pen_width):
    root = ET.Element(f"{{{SVG}}}svg", width=f"{layout.width:g}mm", height=f"{layout.height:g}mm",
                      viewBox=f"0 0 {layout.width:g} {layout.height:g}")
    ET.SubElement(root, f"{{{SVG}}}title").text = "Tabula XI - Of the Closed Neck - pen plotter edition"
    ET.SubElement(root, f"{{{SVG}}}desc").text = (
        "All geometry is explicit millimetre linework. No fonts, fills, clipping, images or transforms. "
        "Keep the page origin fixed between passes. Hardware plotting has not been tested.")
    for name, color, strokes in layers:
        group = ET.SubElement(root, f"{{{SVG}}}g", {
            "id":name.split()[0], f"{{{INKSCAPE}}}groupmode":"layer", f"{{{INKSCAPE}}}label":name,
            "fill":"none", "stroke":color, "stroke-width":f"{pen_width:g}",
            "stroke-linecap":"round", "stroke-linejoin":"round"})
        for s in strokes:
            d = "M"+" L".join(f"{x:.3f},{y:.3f}" for x,y in s)
            ET.SubElement(group, f"{{{SVG}}}path", d=d)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def stats(strokes):
    ink = sum(LineString(s).length for s in strokes)
    travel = sum(math.dist(a[-1],b[0]) for a,b in zip(strokes,strokes[1:]))
    return {"strokes":len(strokes), "pen_down_metres":round(ink/1000,3),
            "between_strokes_travel_metres":round(travel/1000,3)}


def test_sheet(layout):
    """A two-pass coupon on the same page coordinates; no device commands."""
    cx, cy = layout.width/2, layout.height/2
    black = monoline("TWO-PEN TEST / TABULA XI",cx,cy-42,2.5,"center")
    red = []
    black += [[(cx-40,cy-35),(cx+40,cy-35),(cx+40,cy+37),(cx-40,cy+37),(cx-40,cy-35)]]
    # Overprinted crosses reveal translation or a shifted sheet.
    for x in (cx-30,cx+30):
        for y in (cy-26,cy+26):
            cross = [[(x-3,y),(x+3,y)],[(x,y-3),(x,y+3)]]
            black += cross; red += cross
    black += monoline("LEAVE THE NECK.",cx-34,cy-17,2.2)
    red += hershey("Only to the lower gate.",cx-34,cy-12,2.6,"scripts")
    for i,gap in enumerate((.35,.5,.75)):
        x = cx-32+i*23
        black += [[(x,cy+j*gap),(x+16,cy+j*gap)] for j in range(8)]
        black += monoline(f"{gap:.2f} MM",x,cy+10,1.8)
    return black, red


def validate(path, layout):
    root = ET.parse(path).getroot()
    if root.get("viewBox") != f"0 0 {layout.width:g} {layout.height:g}":
        raise AssertionError("Changed page origin")
    allowed = {"svg","title","desc","g","path"}
    for e in root.iter():
        if e.tag.split("}")[-1] not in allowed:
            raise AssertionError("Unexpected plot element")
        if e.get("transform") or e.get("opacity"):
            raise AssertionError("Plot geometry must be baked into coordinates")
        if e.tag.endswith("g") and e.tag != root.tag and e.get("fill") != "none":
            raise AssertionError("A layer depends on a fill")
        if e.tag.endswith("path"):
            pen = FlattenPen(); parse_path(e.get("d"),pen); pen._endPath()
            if len(pen.strokes) != 1:
                raise AssertionError("Each path must be one continuous pen stroke")
            for x,y in pen.strokes[0]:
                if not (math.isfinite(x) and math.isfinite(y) and 0 <= x <= layout.width and 0 <= y <= layout.height):
                    raise AssertionError("Path outside declared page")


def build(args):
    width,height = {"a4":(210,297),"a3":(297,420),"letter":(215.9,279.4)}[args.page]
    if args.width_mm is not None or args.height_mm is not None:
        if args.width_mm is None or args.height_mm is None:
            raise ValueError("Provide both --width-mm and --height-mm.")
        width,height = args.width_mm,args.height_mm
    if not all(math.isfinite(v) for v in (width,height,args.margin_mm,args.pen_mm,args.hatch_mm)):
        raise ValueError("Dimensions must be finite.")
    if width < 150 or height < 200 or args.margin_mm < 12 or 2*args.margin_mm >= min(width,height):
        raise ValueError("Use a page at least 150 x 200 mm and margins at least 12 mm, smaller than half the page.")
    if not .15 <= args.pen_mm <= .5 or args.hatch_mm < args.pen_mm:
        raise ValueError("Use a 0.15-0.5 mm pen; hatch spacing must be at least the pen width.")
    layout = Layout(width,height,args.margin_mm)
    black,red,dropped = geometry(layout,args.hatch_mm,args.pen_mm)
    tb,tr = lettering(layout, args.hatch_mm); black+=tb; red+=tr
    black,red = optimize(black),optimize(red)
    art_bounds = unary_union([LineString(s) for s in black+red]).bounds
    reg = registration(layout)
    out = args.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    for prefix,b,r in [("closed-neck",black,red),("pen-test",*test_sheet(layout))]:
        for suffix,layers in [
            ("black",[("registration Optional registration",BLACK,reg),("black 1 Black impression",BLACK,b)]),
            ("red",[("registration Optional registration",RED,reg),("red 2 Red intervention",RED,r)]),
            ("combined",[("registration Optional registration",BLACK,reg),("black 1 Black impression",BLACK,b),
                         ("red 2 Red intervention",RED,r)])]:
            path = out/f"{prefix}-{suffix}.svg"
            svg_file(path,layout,layers,args.pen_mm); validate(path,layout)
    info = {"source":"canvas/assets/xi_face.svg", "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "page_mm":[width,height], "source_scale_mm_per_unit":round(layout.scale,8),
            "artwork_bounds_mm":[round(v,3) for v in art_bounds], "pen_width_mm":args.pen_mm,
            "solid_hatch_spacing_mm":args.hatch_mm,"curve_tolerance_mm":.015,"simplification_tolerance_mm":.015,
            "discarded_paper_or_ghost_style_groups":dropped,
            "black":stats(black),"red":stats(red),"registration_each_pass":stats(reg),
            "notes":["Geometric statistics, not a runtime estimate.","Each listed stroke normally needs a pen lift.",
                     "No hardware test has been performed.","Lettering in three hands: Hershey Times small capitals, the plotter monoline stamp, Hershey Script for M.; title hatched solid."]}
    (out/"plot-stats.json").write_text(json.dumps(info,indent=2)+"\n")
    if args.preview:
        import cairosvg
        for prefix in ("closed-neck","pen-test"):
            cairosvg.svg2png(url=str(out/f"{prefix}-combined.svg"),write_to=str(out/f"{prefix}-preview.png"),
                            output_width=1260,background_color="#faf7ef")
    print(json.dumps(info,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page",choices=("a4","a3","letter"),default="a4")
    parser.add_argument("--width-mm",type=float)
    parser.add_argument("--height-mm",type=float)
    parser.add_argument("--margin-mm",type=float,default=12)
    parser.add_argument("--pen-mm",type=float,default=.28)
    parser.add_argument("--hatch-mm",type=float,default=.32)
    parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent/"a4")
    parser.add_argument("--preview",action="store_true",help="Also render PNGs; requires optional cairosvg.")
    args = parser.parse_args()
    try:
        build(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
