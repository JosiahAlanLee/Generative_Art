#!/usr/bin/env python3
"""Build a controlled textile/process comparison and portable components."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point, LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.process_art.drawing import Plate, INK, RED, clipped  # noqa: E402
from lib.process_art.textile import run, draw_component  # noqa: E402

MODES = ("control", "veins", "chemistry", "erosion")


def projection(plate, component, origin, u, v, clip=None):
    """Affine display projection; does not change the model or its scalar fields."""
    origin, u, v = map(np.asarray, (origin, u, v))
    for s in component.strokes:
        q = s.points/[component.width, component.height]
        points = origin + q[:, :1]*u + q[:, 1:]*v
        width = max(.095, s.width*min(np.linalg.norm(u)/component.width,
                                     np.linalg.norm(v)/component.height))
        if clip is None:
            plate.add(points, s.color, width)
        else:
            clipped(plate, points, clip, s.color, width)


def context_example(components):
    """The same material as two building surfaces and an exposed plinth fragment."""
    p = Plate("Textile components in an architectural study")
    a = np.array([52., 116.])
    u, v, up = np.array([76., 22.]), np.array([23., -15.]), np.array([0., -74.])
    lower = [a, a+u, a+u+v, a+v]
    upper = [q+up for q in lower]
    f = [a-.12*u-.12*v, a+1.12*u-.12*v,
         a+1.12*u+1.12*v, a-.12*u+1.12*v]
    # Exposed plinth is geometrically cut out around the building footprint.
    building = Polygon([upper[0], upper[3], upper[2], lower[2], lower[1], lower[0]])
    visible = Polygon([(0, 0), (170, 0), (170, 220), (0, 220)]).difference(building)
    plinth = Polygon(f).intersection(visible)
    projection(p, components["erosion"], f[0], 1.24*u, 1.24*v, clip=plinth)
    projection(p, components["veins"], upper[0], u, -up)
    projection(p, components["chemistry"], upper[1], v, -up)
    # Plain roof, silhouette and step construction establish a larger context.
    for t in np.linspace(.04, .96, 21):
        p.add([upper[0]+t*v, upper[1]+t*v], width=.105)
    for face in ([upper[0], upper[1], lower[1], lower[0]],
                 [upper[1], upper[2], lower[2], lower[1]], upper):
        p.add([*face, face[0]], width=.32)
    clipped(p, [*f, f[0]], visible, width=.27)
    down = np.array([0, 5.5])
    clipped(p, [f[0], f[0]+down, f[1]+down, f[2]+down, f[2]], visible, width=.28)
    for q in f[:3]:
        clipped(p, [q, q+down], visible, width=.23)
    # Ground lines radiate from the supported platform; no floating apparatus.
    for i in np.linspace(0, 1, 12):
        p.add([f[0]+i*(f[1]-f[0])+down,
               f[0]+i*(f[1]-f[0])+down+[i*5-15, 13]], width=.095)
    return p


def save(plate, stem, out, pixels):
    (out/"svg"/(stem+".svg")).write_text(plate.svg())
    plate.png(out/"png"/(stem+".png"), pixels)
    plate.png(out/"transparent"/(stem+".png"), pixels, transparent=True)
    return {"stem": stem, "stroke_count": len(plate.strokes),
            "size_mm": [plate.width, plate.height],
            "svg_sha256": hashlib.sha256(plate.svg().encode()).hexdigest()}


def contact(items, out, path):
    width, height = 380, 535
    sheet = Image.new("RGB", (4*width, 2*height), "#e6e1d7")
    d = ImageDraw.Draw(sheet)
    font, small = ImageFont.load_default(size=18), ImageFont.load_default(size=13)
    for i, item in enumerate(items):
        im = Image.open(out/"png"/(item["stem"]+".png")).convert("RGB")
        im.thumbnail((368, 460), Image.Resampling.LANCZOS)
        x, y = i % 4*width, i // 4*height
        sheet.paste(im, (x+(width-im.width)//2, y+8))
        d.text((x+13, y+477), item["label"], font=font, fill="#161918")
        d.text((x+13, y+505), item.get("key", ""), font=small, fill="#5b554c")
    sheet.save(path, quality=87, optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT/"examples/out/textile-process")
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--pixels", type=int, default=2000)
    ap.add_argument("--zip", type=Path)
    ap.add_argument("--update-preview", action="store_true")
    args = ap.parse_args()
    if not 400 <= args.pixels <= 4000:
        ap.error("pixels must be 400..4000")
    for folder in ("png", "transparent", "svg", "fields", "settings"):
        (args.out/folder).mkdir(parents=True, exist_ok=True)
    manifest = {"title": "Textile grammar / three process couplings", "seed": args.seed,
                "comparison": "The identical seeded scaffold is used for all four modes.",
                "reference": "Wright-office design research; original Truchet/Smith-derived geometry, not a reproduction of a Wright textile.",
                "items": [], "code_sha256": {}}
    for path in (ROOT/"lib/process_art/textile.py", Path(__file__).resolve(), ROOT/"lib/process_art/drawing.py"):
        manifest["code_sha256"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    components, states = {}, {}
    for mode in MODES:
        textile, state = run(args.seed, mode)
        components[mode] = Plate(mode, 132, 176)
        draw_component(components[mode], textile, mode, state)
        # One tiled panel is the control; the process choices change no motifs.
        plate = Plate(f"Textile / {mode}")
        draw_component(plate, textile, mode, state, box=(19, 22, 132, 176))
        stem = f"textile-s{args.seed}-{mode}"
        item = save(plate, stem, args.out, args.pixels)
        item.update({"label": {"control": "Unchanged scaffold", "veins": "Transport on joints",
                               "chemistry": "Confined chemistry", "erosion": "Dissolving scaffold"}[mode],
                     "mode": mode, "key": "same geometry / same seed"})
        component_stem = stem+"-component"
        (args.out/"svg"/(component_stem+".svg")).write_text(components[mode].svg())
        arrays = {**state, "nodes": textile.nodes, "edges": textile.edges, "edge_length": textile.length}
        np.savez_compressed(args.out/"fields"/(stem+".npz"), **arrays)
        settings = {"seed": args.seed, "mode": mode, "tile_grid": [6, 8],
                    "raster_pixels_per_tile": 40, "solid_width_pixels": 2,
                    "steps": {"control": 0, "veins": 90, "chemistry": 1800, "erosion": 2200}[mode],
                    "component_svg": component_stem+".svg", "component_size_mm": [132, 176]}
        if mode == "veins":
            settings.update({"source_flow": 1, "drain_flow": "equal shares totaling -1", "pressure_gauge": "source=0", "requested_drain_targets": 6,
                             "actual_drain_nodes": len(state["drains"]),
                             "max_free_node_residual": float(np.max(np.abs(state["kirchhoff_residual"][state["free_nodes"]]))),
                             "adaptation": "D <- .82 D + .18 (.015 + abs(Q)/max(abs(Q)))"})
        if mode == "chemistry":
            settings.update({"Du": .16, "Dv": .08, "feed": .035, "kill": .061, "dt": 1,
                             "boundary": "zero face flux through solid; reflecting outer edges",
                             "inoculated_patches": len(state["inoculation_yx"])})
        if mode == "erosion":
            settings.update({"permeability": ".025 + .19*(1-material)",
                             "material_loss": ".022*acid*material per step",
                             "acid_consumption": ".35*material_loss", "vent_value": 1,
                             "compartments_before": int(state["compartments_before"]),
                             "compartments_after": int(state["compartments_after"]),
                             "compartment_threshold": "material < .35, four-neighbor connectivity"})
            item["key"] = f'{settings["compartments_before"]} -> {settings["compartments_after"]} pore components'
        (args.out/"settings"/(stem+".json")).write_text(json.dumps(settings, indent=2)+"\n")
        item["settings"] = settings
        manifest["items"].append(item)
        states[mode] = state
        print(stem, len(plate.strokes), flush=True)
    contextual = context_example(components)
    item = save(contextual, f"textile-s{args.seed}-context", args.out, args.pixels)
    item.update({"label": "A surface among others", "mode": "context",
                 "key": "affine placement / same process outputs"})
    manifest["items"].append(item)
    # Small fragments demonstrate geometric clipping, not a new simulation.
    for mode, name in (("veins", "arch"), ("chemistry", "medallion"), ("erosion", "corner")):
        p = Plate(name, 80, 100)
        shape = Polygon([(5, 94), (75, 94), (75, 42), (65, 20), (40, 6), (15, 20), (5, 42)])
        if name == "medallion":
            shape = Point(40, 50).buffer(35, quad_segs=96)
        if name == "corner":
            shape = Polygon([(5, 5), (75, 5), (75, 25), (30, 25), (30, 95), (5, 95)])
        draw_component(p, textile, mode, states[mode], box=(4, 4, 72, 92), clip=shape)
        item = save(p, f"textile-s{args.seed}-{name}", args.out, args.pixels)
        item.update({"label": name.capitalize()+" fragment", "mode": "fragment",
                     "key": "portable strokes / transparent ground"})
        manifest["items"].append(item)
    contact(manifest["items"], args.out, args.out/"contact-sheet.jpg")
    (args.out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (args.out/"README.txt").write_text(
        "TEXTILE GRAMMAR / PROCESS STUDY\n\n"
        "Four controlled panels: an unchanged scaffold, adaptive transport, confined Gray-Scott chemistry, and material dissolution.\n"
        "One architectural placement and three clipped fragments show the pattern as a reusable element.\n"
        "png/ and transparent/ contain previews and alpha versions; svg/ includes panels plus borderless components.\n"
        "fields/ contains numeric states, graph nodes and edges; settings/ declares parameters and measured results.\n"
        "Crossings are graph junctions only at explicit shared endpoints; the raster wall model treats intersecting ink as solid.\n"
        "These are illustrative dimensionless process models; the context drawing is an affine projection, not another simulation.\n"
        "Reference research includes Wright, Marion Mahony Griffin and Ling Po; geometry is an original Truchet/Smith-derived composition.\n"
        "See techniques/12-process-art/TEXTILE.md in JosiahAlanLee/Generative_Art for source credits and integration.\n"
    )
    if args.update_preview:
        preview = ROOT/"examples/previews/textile-process"
        preview.mkdir(exist_ok=True)
        (preview/"contact-sheet.jpg").write_bytes((args.out/"contact-sheet.jpg").read_bytes())
        (preview/"manifest.json").write_text((args.out/"manifest.json").read_text())
    if args.zip:
        with ZipFile(args.zip, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(args.out.rglob("*")):
                if path.is_file() and path.resolve() != args.zip.resolve():
                    archive.write(path, path.relative_to(args.out))
        print(f"ZIP: {args.zip.stat().st_size:,} bytes", flush=True)


if __name__ == "__main__":
    main()
