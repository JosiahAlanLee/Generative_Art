"""Independent geometric constructions of traditional quilt-block families.

Python standard library only. The finish consists of editable SVG geometry,
never embedded bitmaps, SVG filters, or simulated fabric stitching. References
and the limits of the material studies are in research/barn-quilts/README.md.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path
import random
import re

Point = tuple[float, float]
PATTERNS = ("ohio-star", "sawtooth-star", "churn-dash", "pinwheel", "log-cabin",
            "flying-geese", "rail-fence", "square-in-square")
# Roles: light ground, main paint, contrasting paint, secondary paint.
PALETTES = {
    "barn-red": ("#f0e5c7", "#a8372c", "#223b45", "#d3a84d"),
    "dairy-blue": ("#eee9d7", "#244d75", "#ac4b3e", "#81a7ad"),
    "harvest": ("#f1dfac", "#753c36", "#324b3d", "#d39436"),
    "prairie": ("#f1e3c6", "#3b625a", "#9b452f", "#c6a45d"),
    "roadside": ("#fff5d9", "#ba332b", "#1c3d7a", "#e7b82f"),
    "manuscript": ("#ead9b2", "#32302a", "#913c30", "#b18c54"),
}
MATERIALS = ("wood", "mdo", "aluminum", "steel")


@dataclass(frozen=True)
class Patch:
    points: tuple[Point, ...]
    role: int


@dataclass(frozen=True)
class QuiltSpec:
    pattern: str = "ohio-star"
    palette: str = "barn-red"
    material: str = "wood"
    seed: int = 23
    texture: float = 0.5
    wear: float = 0.18
    border: float = 0.045
    rotation: int = 0
    colorway: int = 0
    detail: int = 4
    size_mm: float = 200.0
    mode: str = "painted"
    hardware: bool = False
    colors: tuple[str, ...] | None = None

    def validate(self):
        if self.pattern not in PATTERNS + ("random",):
            raise ValueError(f"unknown pattern: {self.pattern}")
        if self.palette not in (*PALETTES, "random"):
            raise ValueError(f"unknown palette: {self.palette}")
        if self.material not in MATERIALS:
            raise ValueError(f"unknown material: {self.material}")
        if self.mode not in ("painted", "flat", "outline"):
            raise ValueError("mode must be painted, flat, or outline")
        for key, high in (("texture", 1), ("wear", 1), ("border", 0.2)):
            value = getattr(self, key)
            if not math.isfinite(value) or not 0 <= value <= high:
                raise ValueError(f"{key} must be finite and between 0 and {high}")
        if not math.isfinite(self.size_mm) or self.size_mm <= 0:
            raise ValueError("size_mm must be finite and positive")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        if self.rotation not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180, or 270")
        if type(self.colorway) is not int or not 0 <= self.colorway <= 2:
            raise ValueError("colorway must be 0, 1, or 2")
        if type(self.detail) is not int or not 2 <= self.detail <= 8:
            raise ValueError("detail must be an integer between 2 and 8")
        if self.colors is not None:
            if len(self.colors) != 4 or any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in self.colors):
                raise ValueError("colors must contain exactly four #RRGGBB values")


def _rng(seed, stream):
    # Separate streams keep the support surface fixed while changing blocks.
    return random.Random(f"barn-quilts-v1/{seed}/{stream}")


def _turn(point, turns):
    x, y = point
    for _ in range(turns % 4):
        x, y = 1 - y, x
    return x, y


def _rect(x, y, w, h, role):
    return Patch(((x, y), (x + w, y), (x + w, y + h), (x, y + h)), role)


def _hst(x, y, side, corner, role):
    q = ((x, y), (x + side, y), (x + side, y + side), (x, y + side))
    k = ("tl", "tr", "br", "bl").index(corner)
    return [Patch((q[k], q[(k + 1) % 4], q[(k - 1) % 4]), role),
            Patch((q[(k + 1) % 4], q[(k + 2) % 4], q[(k - 1) % 4]), 0)]


def _goose(x, y, w, h, turns, role, sky=0):
    units = [Patch(((0, 1), (1, 1), (0.5, 0)), role),
             Patch(((0, 0), (0.5, 0), (0, 1)), sky),
             Patch(((0.5, 0), (1, 0), (1, 1)), sky)]
    return [Patch(tuple((x + w * u, y + h * v) for u, v in
                        (_turn(p, turns) for p in patch.points)), patch.role) for patch in units]


def block(pattern="ohio-star", *, seed=23, detail=4):
    """Return an exact, nonoverlapping partition of the unit square.

    Named families use fixed topology; seed resolves 'random'. Detail controls
    Log Cabin rounds, Flying Geese rows, Rail Fence rails, and nested squares.
    It is ignored by the other four families.
    """
    if type(detail) is not int or not 2 <= detail <= 8:
        raise ValueError("detail must be an integer between 2 and 8")
    if pattern == "random":
        pattern = _rng(seed, "pattern").choice(PATTERNS)
    if pattern not in PATTERNS:
        raise ValueError(f"unknown pattern: {pattern}")
    out = []
    if pattern == "ohio-star":
        s = 1 / 3
        for row in range(3):
            for col in range(3):
                x, y = col * s, row * s
                if row == col == 1:
                    out.append(_rect(x, y, s, s, 2))
                elif (row + col) % 2 == 0:
                    out.append(_rect(x, y, s, s, 0))
                else:
                    q = ((x, y), (x + s, y), (x + s, y + s), (x, y + s))
                    for k in range(4):
                        # At top/bottom, left+right triangles form the hourglass.
                        colored = k % 2 == (1 if col == 1 else 0)
                        out.append(Patch((q[k], q[(k + 1) % 4], (x + s / 2, y + s / 2)),
                                         1 if colored else 0))
    elif pattern == "sawtooth-star":
        for x in (0, 0.75):
            for y in (0, 0.75):
                out.append(_rect(x, y, 0.25, 0.25, 0))
        out.append(_rect(0.25, 0.25, 0.5, 0.5, 2))
        # Background goose points inward; its two small triangles are star tips.
        for x, y, w, h, turns in ((0.25, 0, 0.5, 0.25, 2), (0.75, 0.25, 0.25, 0.5, 3),
                                  (0.25, 0.75, 0.5, 0.25, 0), (0, 0.25, 0.25, 0.5, 1)):
            out.extend(_goose(x, y, w, h, turns, 0, 1))
    elif pattern == "churn-dash":
        s = 1 / 3
        for x, y, corner in ((0, 0, "br"), (2*s, 0, "bl"),
                              (2*s, 2*s, "tl"), (0, 2*s, "tr")):
            out.extend(_hst(x, y, s, corner, 1))
        out.append(_rect(s, s, s, s, 0))
        for x, y, w, h, inner in ((s, 0, s, s/2, (0, s/2)), (s, 2*s, s, s/2, (0, 0)),
                                    (0, s, s/2, s, (s/2, 0)), (2*s, s, s/2, s, (0, 0))):
            dx, dy = inner
            out.append(_rect(x+dx, y+dy, w, h, 1))
            out.append(_rect(x+(s/2-dx if w < h else 0),
                             y+(s/2-dy if h < w else 0), w, h, 0))
    elif pattern == "pinwheel":
        units = _hst(0, 0, 0.5, "tr", 1)
        for turns in range(4):
            for patch in units:
                out.append(Patch(tuple(_turn(p, turns) for p in patch.points), patch.role))
    elif pattern == "log-cabin":
        # A true sequential spiral: every new strip spans the enlarged square.
        x0 = y0 = 0
        x1 = y1 = 1
        out.append(_rect(0, 0, 1, 1, 2))
        for _ in range(detail):
            out.append(_rect(x0, y0-1, x1-x0, 1, 0)); y0 -= 1
            out.append(_rect(x1, y0, 1, y1-y0, 3)); x1 += 1
            out.append(_rect(x0, y1, x1-x0, 1, 1)); y1 += 1
            out.append(_rect(x0-1, y0, 1, y1-y0, 2)); x0 -= 1
        side = x1-x0
        out = [Patch(tuple(((x-x0)/side, (y-y0)/side) for x, y in p.points), p.role) for p in out]
    elif pattern == "flying-geese":
        for row in range(detail):
            for col in range(2):
                out.extend(_goose(col/2, row/detail, 0.5, 1/detail, 0, 1+col))
    elif pattern == "rail-fence":
        roles = (0, 1, 3, 2)
        for row in range(2):
            for col in range(2):
                for i in range(detail):
                    x, y = col/2, row/2
                    if (row+col) % 2:
                        out.append(_rect(x+i/(2*detail), y, 1/(2*detail), 0.5, roles[i % 4]))
                    else:
                        out.append(_rect(x, y+i/(2*detail), 0.5, 1/(2*detail), roles[i % 4]))
    elif pattern == "square-in-square":
        q = ((0, 0), (1, 0), (1, 1), (0, 1))
        for ring in range(detail):
            mids = tuple(((q[k][0]+q[(k+1) % 4][0])/2,
                          (q[k][1]+q[(k+1) % 4][1])/2) for k in range(4))
            for k in range(4):
                out.append(Patch((q[k], mids[k], mids[(k-1) % 4]), (ring+k % 2) % 4))
            q = mids
        out.append(Patch(q, 2))
    return out


def unique_edges(patches):
    """Split collinear T-junctions and return each undirected edge once.

    A long log edge beside several short logs must be split before deduping;
    simply comparing complete segments would double-draw those shared edges.
    """
    vertices = {p for patch in patches for p in patch.points}
    edges = set()
    for patch in patches:
        for a, b in zip(patch.points, patch.points[1:] + patch.points[:1]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            length2 = dx*dx + dy*dy
            if length2 < 1e-18:
                continue
            cuts = [(0, a), (1, b)]
            for p in vertices:
                t = ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2
                cross = (p[0]-a[0])*dy-(p[1]-a[1])*dx
                if 1e-9 < t < 1-1e-9 and abs(cross) < 1e-9:
                    cuts.append((t, p))
            cuts.sort()
            for (_, p), (_, q) in zip(cuts, cuts[1:]):
                p, q = (tuple(round(c, 9) for c in v) for v in (p, q))
                if p != q:
                    edges.add(tuple(sorted((p, q))))
    return sorted(edges)


def _n(value):
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _points(points, scale=1000):
    return " ".join(f"{_n(x*scale)},{_n(y*scale)}" for x, y in points)


def _color(color, target, amount):
    a = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
    b = tuple(int(target[i:i+2], 16) for i in (1, 3, 5))
    return "#"+"".join(f"{round(x*(1-amount)+y*amount):02x}" for x, y in zip(a, b))


def _resolve(spec):
    spec.validate()
    pattern = _rng(spec.seed, "pattern").choice(PATTERNS) if spec.pattern == "random" else spec.pattern
    name = _rng(spec.seed, "palette").choice(tuple(PALETTES)) if spec.palette == "random" else spec.palette
    colors = tuple(spec.colors) if spec.colors is not None else PALETTES[name]
    colors = (colors[0],) + tuple(colors[1+(i+spec.colorway) % 3] for i in range(3))
    return pattern, name, colors


def _surface(spec, prefix):
    """Panel-wide marks: opaque paint mostly hides its supporting material."""
    rng = _rng(spec.seed, "support")
    t = spec.texture
    out = [f'<g id="{prefix}-surface" fill="none" stroke-linecap="round">']
    if spec.material == "wood":
        for _ in range(round(135*t)):
            x, y = rng.uniform(0, 1000), rng.uniform(-180, 900)
            length, bend = rng.uniform(100, 650), rng.uniform(-10, 10)
            out.append(f'<path d="M {_n(x)} {_n(y)} c {_n(bend)} {_n(length*.3)} {_n(-bend)} '
                       f'{_n(length*.7)} {_n(bend*.3)} {_n(length)}" stroke="#3e2c1e" '
                       f'stroke-width="{_n(rng.uniform(.35,1.35))}" opacity="{_n(.045*t)}"/>')
        # Knots are faint relief under a paint film, never unpainted plank ovals.
        for _ in range(2):
            x, y = rng.uniform(180, 820), rng.uniform(160, 840)
            for ring in range(1, 6):
                out.append(f'<ellipse cx="{_n(x)}" cy="{_n(y)}" rx="{ring*1.8}" '
                           f'ry="{ring*7}" stroke="#483225" stroke-width=".55" opacity="{_n(.035*t)}"/>')
    elif spec.material in ("aluminum", "steel"):
        for _ in range(round((115 if spec.material == "steel" else 55)*t)):
            x, y = rng.uniform(-80, 990), rng.uniform(0, 1000)
            out.append(f'<path d="M {_n(x)} {_n(y)} l {_n(rng.uniform(6,160))} {_n(rng.uniform(-.35,.35))}" '
                       f'stroke="#fff9ed" stroke-width=".5" opacity="{_n(.06*t)}"/>')
    # Compact round-capped subpaths retain vector stipple without thousands
    # of separate elements. The paint-film stream is fixed across supports.
    roller = _rng(spec.seed, "roller")
    buckets = {(color, size):[] for color in ("#fff9ec", "#302a23") for size in (.55, 1.2, 2.0)}
    for _ in range(round(850*t)):
        x, y = roller.uniform(0, 1000), roller.uniform(0, 1000)
        color = "#fff9ec" if roller.random()<.6 else "#302a23"
        size = roller.choice((.55, 1.2, 2.0))
        buckets[color, size].append(f'M {_n(x)} {_n(y)} h .01')
    for (color, size), marks in buckets.items():
        if marks:
            out.append(f'<path d="{" ".join(marks)}" stroke="{color}" stroke-width="{size}" opacity="{_n(.065*t)}"/>')
    out.append('</g>')
    return "".join(out)


def _brush(patch, index, spec, prefix):
    rng = _rng(spec.seed, f"paint/{index}")
    xs, ys = zip(*patch.points)
    x0, x1, y0, y1 = min(xs)*1000, max(xs)*1000, min(ys)*1000, max(ys)*1000
    # Marks follow the painter's pass, independently of the support grain.
    horizontal = rng.random() < .5
    out = [f'<g id="{prefix}-brush-{index}" clip-path="url(#{prefix}-patch-{index})" '
           'fill="none" stroke-linecap="round">']
    for i in range(round(10*spec.texture)):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        dx, dy = (rng.uniform(18, max(19,x1-x0)), rng.uniform(-.8,.8)) if horizontal else (
                  rng.uniform(-.8,.8), rng.uniform(18, max(19,y1-y0)))
        out.append(f'<path d="M {_n(x-dx/2)} {_n(y-dy/2)} l {_n(dx)} {_n(dy)}" '
                   f'stroke="{"#fff9eb" if i % 2 else "#34271f"}" '
                   f'stroke-width="{_n(rng.uniform(.4,1.8))}" opacity="{_n(.055*spec.texture)}"/>')
    out.append('</g>')
    return "".join(out)


def _wear(spec, prefix):
    rng = _rng(spec.seed, "wear")
    w = spec.wear
    out = [f'<g id="{prefix}-wear">']
    base = {"wood":"#aa8b60", "mdo":"#b5a28a", "aluminum":"#b6bec1", "steel":"#909da2"}[spec.material]
    for i in range(round(12*w + 110*w*w)):
        r = rng.uniform(1, 2+8*w)
        x, y = rng.uniform(0, 1000), rng.uniform(0, 1000)
        if rng.random() < .8:
            depth = rng.expovariate(1/(2+12*w))
            x, y = _turn((depth/1000, y/1000), rng.randrange(4))
            x, y = x*1000, y*1000
        points = []
        for k in range(8):
            angle = k*math.tau/8
            reach = r*rng.uniform(.55,1.4)
            points.append((x+math.cos(angle)*reach, y+math.sin(angle)*reach))
        pts = _points(points, 1)
        out.append(f'<polygon points="{pts}" fill="{base}" stroke="#584a39" stroke-width=".45"/>')
        # Exposed substrate marks are clipped to chips, not laid over all paint.
        out.append(f'<clipPath id="{prefix}-chip-{i}"><polygon points="{pts}"/></clipPath>')
        out.append(f'<g clip-path="url(#{prefix}-chip-{i})" stroke="#f1e9d7" opacity=".45">')
        for j in (-1, 0, 1):
            if spec.material == "wood":
                out.append(f'<path d="M {_n(x+j*r*.45)} {_n(y-2*r)} v {_n(4*r)}" stroke-width=".65"/>')
            else:
                out.append(f'<path d="M {_n(x-2*r)} {_n(y+j*r*.5)} h {_n(4*r)}" stroke-width=".45"/>')
        out.append('</g>')
    out.append('</g>')
    return "".join(out)


def render_fragment(spec=QuiltSpec(), *, id_prefix=None):
    """Return a composable group in a 1000 x 1000 coordinate system.

    Supply a distinct id_prefix for repeated identical panels in one document.
    Transform the containing group to place the panel on a book page or facade.
    """
    pattern, _, colors = _resolve(spec)
    patches = block(pattern, seed=spec.seed, detail=spec.detail)
    digest = sha256(json.dumps(asdict(spec), sort_keys=True).encode()).hexdigest()[:12]
    prefix = id_prefix if id_prefix is not None else f"bq-{digest}"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", prefix):
        raise ValueError("id_prefix must be an SVG-safe identifier")
    b = spec.border*1000
    side = 1000-2*b
    out = [f'<g id="{prefix}" data-pattern="{pattern}" data-material="{spec.material}">',
           f'<defs><clipPath id="{prefix}-panel"><rect width="1000" height="1000"/></clipPath>']
    if spec.mode == "painted" and spec.texture:
        for i, patch in enumerate(patches):
            out.append(f'<clipPath id="{prefix}-patch-{i}"><polygon points="{_points(patch.points)}"/></clipPath>')
    out.append('</defs>')
    if spec.mode == "outline":
        # Inherited transforms affect the pen width; compensate for the inset.
        pen = 1000*.25/spec.size_mm
        out.append(f'<g id="{prefix}-outlines" fill="none" stroke="{colors[1]}" '
                   f'stroke-width="{_n(pen)}" stroke-linejoin="round" stroke-linecap="round">')
        if b:
            out.append('<rect x="0" y="0" width="1000" height="1000"/>')
        out.append(f'<g transform="translate({_n(b)} {_n(b)}) scale({_n(side/1000)}) '
                   f'rotate({spec.rotation} 500 500)" stroke-width="{_n(pen/(side/1000))}">')
        edges = unique_edges(patches)
        d = " ".join(f'M {_n(a[0]*1000)} {_n(a[1]*1000)} L {_n(c[0]*1000)} {_n(c[1]*1000)}' for a, c in edges)
        out.append(f'<path d="{d}"/></g></g></g>')
        return "".join(out)
    wear = spec.wear if spec.mode == "painted" else 0
    out.append(f'<g clip-path="url(#{prefix}-panel)">')
    out.append(f'<rect id="{prefix}-border" width="1000" height="1000" fill="{colors[1]}"/>')
    out.append(f'<g id="{prefix}-paint" transform="translate({_n(b)} {_n(b)}) scale({_n(side/1000)}) '
               f'rotate({spec.rotation} 500 500)">')
    for i, patch in enumerate(patches):
        color = _color(colors[patch.role], "#e7ddc4", wear*.13)
        out.append(f'<polygon id="{prefix}-piece-{i}" data-role="{patch.role}" points="{_points(patch.points)}" '
                   f'fill="{color}" stroke="{color}" stroke-width=".08" stroke-linejoin="round"/>')
    if spec.mode == "painted" and spec.texture:
        out.append(f'<g id="{prefix}-brushwork">')
        for i, patch in enumerate(patches):
            out.append(_brush(patch, i, spec, prefix))
        out.append('</g>')
    out.append('</g>')
    if b:
        out.append(f'<rect x="{_n(b*.48)}" y="{_n(b*.48)}" width="{_n(1000-b*.96)}" '
                   f'height="{_n(1000-b*.96)}" fill="none" stroke="{colors[0]}" stroke-width="1.8" opacity=".65"/>')
    if spec.mode == "painted":
        if spec.texture:
            out.append(_surface(spec, prefix))
        if spec.wear:
            out.append(_wear(spec, prefix))
    out.append('</g>')
    if spec.hardware:
        out.append(f'<g id="{prefix}-hardware">')
        for x in (18, 982):
            for y in (18, 982):
                out.append(f'<circle cx="{x}" cy="{y}" r="4.2" fill="#8e9694" stroke="#474d4c" stroke-width=".9"/>'
                           f'<path d="M {x-2.2} {y-1} l 4.4 2" stroke="#444b4a" stroke-width="1.1"/>')
        out.append('</g>')
    out.append('</g>')
    return "".join(out)


def render_svg(spec=QuiltSpec()):
    pattern, palette, _ = _resolve(spec)
    metadata = {"generator":"barn-quilts-v1", "spec":asdict(spec),
                "resolved_pattern":pattern, "resolved_palette":palette,
                "effective_texture":spec.texture if spec.mode == "painted" else 0,
                "effective_wear":spec.wear if spec.mode == "painted" else 0,
                "construction":"independent geometric interpretation; block names and colorings vary",
                "research":"research/barn-quilts/README.md"}
    title = f'{pattern.replace("-", " ").title()} — {spec.material}, {spec.mode}'
    prefix = "bq-"+sha256(json.dumps(asdict(spec), sort_keys=True).encode()).hexdigest()[:12]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{_n(spec.size_mm)}mm" '
            f'height="{_n(spec.size_mm)}mm" viewBox="0 0 1000 1000" role="img" aria-labelledby="{prefix}-title">'
            f'<title id="{prefix}-title">{escape(title)}</title><desc>Painted quilt-block geometry with separately editable material marks; '
            'opaque paint hides most substrate grain. No embedded images or filter effects.</desc>'
            f'<metadata>{escape(json.dumps(metadata, sort_keys=True))}</metadata>'
            f'{render_fragment(spec, id_prefix=prefix)}</svg>\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--pattern", choices=(*PATTERNS, "random"), default="ohio-star")
    parser.add_argument("--palette", choices=(*PALETTES, "random"), default="barn-red")
    parser.add_argument("--material", choices=MATERIALS, default="wood")
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--texture", type=float, default=.5)
    parser.add_argument("--wear", type=float, default=.18)
    parser.add_argument("--border", type=float, default=.045)
    parser.add_argument("--rotation", type=int, choices=(0,90,180,270), default=0)
    parser.add_argument("--colorway", type=int, choices=range(3), default=0)
    parser.add_argument("--detail", type=int, choices=range(2,9), default=4)
    parser.add_argument("--size-mm", type=float, default=200)
    parser.add_argument("--mode", choices=("painted", "flat", "outline"), default="painted")
    parser.add_argument("--hardware", action="store_true")
    parser.add_argument("--colors", help="Four comma-separated #RRGGBB colors: light, main, contrast, secondary")
    args = vars(parser.parse_args(argv))
    output = args.pop("output")
    if args["colors"] is not None:
        args["colors"] = tuple(c.strip() for c in args["colors"].split(","))
    try:
        svg = render_svg(QuiltSpec(**args))
    except ValueError as exc:
        parser.error(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
