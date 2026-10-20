"""A small visual tour using the imported book functions, with no source rasters.

Run from the repository root: python examples/make_sampler.py
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "sources/codex-intervallorum"
sys.path[:0] = [str(BOOK / "common/geometry"), str(BOOK / "common/plot")]
from core import Doc, bezier, arc_pts  # noqa: E402
import marks  # noqa: E402
import tx  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, BOOK / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def doc():
    styles = {}
    for color, ink in (("ink", "#252825"), ("red", "#a32b24")):
        for weight, width in (("core", 1.1), ("orn", .65), ("hair", .35), ("cip", .65)):
            styles[f"{color}_{weight}"] = {"fill": "none", "stroke": ink, "stroke-width": width, "stroke-linecap": "round"}
        styles[f"{color}_fill"] = {"fill": ink, "stroke": "none"}
        for size, width in (("s", .65), ("m", 1.05), ("l", 1.55)):
            styles[f"{color}_g{size}"] = {"fill": "none", "stroke": ink, "stroke-width": width, "stroke-linecap": "round"}
    return Doc(240, 180, styles)


def scaffold(h):
    h.ring(120, 87, 51, "core")
    h.ring(120, 87, 42, "hair")
    for k in range(5):
        y = 51 + k * 18
        h.stroke(bezier((36, y), (87, y - 45), (151, y + 45), (204, y), 70), "orn")
    marks.asterisk(h, 120, 87, 21, n=8, color="red", centre=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "examples/out")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    panels = []
    for mode in ("ink", "grain"):
        d = doc()
        scaffold(marks.Hand(d, random.Random(17), mode=mode, amp=.65))
        panels.append(d.body())
    d = doc()
    h = marks.Hand(d, random.Random(19), amp=.4)
    shape = [(31, 58), (72, 24), (192, 45), (213, 123), (145, 156), (46, 137)]
    marks.lattice_fill(h, shape, 12, marker="mixed", ang=35, msize=.19)
    panels.append(d.body())
    d = doc()
    h = marks.Hand(d, random.Random(21), amp=.3)
    message = "REVISE THE RULE"
    assert tx.decode(tx.encode(message)) == message
    tx.write(h, message, 19, 67, 10)
    for x in range(27, 220, 31):
        h.ring(x, 124, 8, color="red")
    panels.append(d.body())
    physarum = load("sampler_physarum", "books/05_notoria/fields/physarum.py")
    result = physarum.run(dict(grid=[80, 80], agents=180, steps=100, snapshots=[100],
                              seed=23, arena="disc", spawn="disc", spawn_radius=.75,
                              exclusion=True, record_paths=True))
    d = doc()
    h = marks.Hand(d, random.Random(23), amp=.04)
    for path in result["paths"][::2]:
        h.stroke([(40 + x * 2, 10 + y * 2) for x, y in path], "hair")
    panels.append(d.body())
    figure = load("sampler_figure", "books/04_graduum/plates/v-native/figure.py")
    d = doc()
    h = marks.Hand(d, random.Random(29), amp=.2)
    outline = figure.robe_outline()
    transform = lambda pts: [(120 + (x - 115) * 2.1, 15 + (y - 100) * 1.25) for x, y in pts]
    h.stroke(transform(outline), "core", closed=True)
    for path in figure.flow_lines(Polygon(outline), random.Random(29), 103, 212, 29, wander=.12):
        h.stroke(transform(path), "hair")
    panels.append(d.body())
    titles = [("01 / INK", "Seeded wobble over shared paths"),
              ("02 / CORNMEAL", "Same scaffold, granular hand"),
              ("03 / CLIPPED LATTICE", "Hatching and seeded marks"),
              ("04 / TRANSCRIPTION", "Recoverable twelve-sign script"),
              ("05 / AGENT TRACES", "Recorded Notoria trajectories"),
              ("06 / ROBE FLOW", "Curves following a silhouette")]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="780" viewBox="0 0 1000 780">',
           '<rect width="1000" height="780" fill="#eee7d6"/>',
           '<text x="38" y="49" font-family="serif" font-size="29" fill="#252825">Six techniques from the book</text>',
           '<text x="38" y="76" font-family="sans-serif" font-size="12" fill="#645b4b">Unchanged source functions / fixed seeds / small demonstration parameters</text>']
    for i, (body, (title, subtitle)) in enumerate(zip(panels, titles)):
        x, y = 35 + (i % 3) * 322, 106 + (i // 3) * 319
        svg += [f'<g transform="translate({x},{y})">',
                '<rect width="300" height="293" rx="2" fill="#f5f0e5" stroke="#c3b8a1" stroke-width=".7"/>',
                f'<text x="17" y="28" font-family="sans-serif" font-size="12" fill="#a32b24">{title}</text>',
                f'<g transform="translate(6,45) scale(1.2)">{body}</g>',
                f'<text x="17" y="274" font-family="sans-serif" font-size="12" fill="#645b4b">{subtitle}</text>', '</g>']
    svg += ['<text x="38" y="760" font-family="sans-serif" font-size="11" fill="#645b4b">Josiah Alan-Lee / Generative Art / See CATALOG.md for source, tuning and production examples</text>', '</svg>']
    target = args.out / "technique-sampler.svg"
    target.write_text("\n".join(svg) + "\n")
    record = dict(book_commit=json.loads((ROOT / "catalog/source-manifest.json").read_text())["commit"],
                  example="Small demonstrations, not reproductions of book plates", seeds=[17, 19, 21, 23, 29],
                  svg_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), field=physarum.manifest(result),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.out / "sampler-manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    import cairosvg
    cairosvg.svg2png(url=str(target), write_to=str(target.with_suffix(".png")))
    print(target)


if __name__ == "__main__":
    main()
