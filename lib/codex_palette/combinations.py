"""Three composition experiments using existing collection mechanisms.

These are original combinations, not historical reconstructions or calibrated
models. No Blender or Driftless code is changed. All geometry is millimetre
stroke data accepted by the book's existing SVG importer.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from shapely.geometry import LineString, Polygon

from lib.barn_quilts.generator import block, unique_edges
from lib.process_art.drawing import INK, RED, Plate, clipped, contours, furniture
from lib.process_art.textile import (compartment_chemistry, draw_component,
                                     flux_laplacian, grammar)
from . import historyflow, marbling
from .studies import guilloche_plate


def quilt_chemistry(seed=31, steps=2100):
    """Exact Ohio Star edges become reflecting chemical compartment walls."""
    patches = block("ohio-star")
    edges = unique_edges(patches)
    resolution = 321
    image = Image.new("L", (resolution, resolution))
    pen = ImageDraw.Draw(image)
    for a, b in edges:
        pen.line([tuple(np.asarray(p) * (resolution - 1)) for p in (a, b)],
                 fill=255, width=3)
    solid = np.asarray(image) > 0
    state = compartment_chemistry(solid, seed=seed, steps=steps)
    plate = Plate("Partitioned star")
    origin, side = np.array([17., 35.]), 136.
    # Painted blocks become two sparse ruled hands, leaving the chemical
    # filaments readable. The same exact partition supplies both operations.
    for patch in patches:
        if patch.role == 0:
            continue
        polygon = Polygon(np.asarray(patch.points) * side + origin)
        for offset in np.arange(-side, side * 2, 2.6):
            if patch.role == 1:
                path = np.array([[offset, 0], [offset + side, side]]) * [1, 1] + origin
            else:
                path = np.array([[offset, 0], [offset - side, side]]) + origin
            clipped(plate, path, polygon, INK, .085)
    contours(plate, state["v"], [.065, .14, .24, .34],
             box=(*origin, side, side), mask=~solid, color=RED, width=.14)
    for a, b in edges:
        plate.add(np.asarray([a, b]) * side + origin, INK, .23, simplify=0)
    for inset in (2., 4.4):
        x, y = origin - inset
        d = side + 2 * inset
        plate.add([(x, y), (x + d, y), (x + d, y + d), (x, y + d), (x, y)],
                  INK, .13, simplify=0)
    furniture(plate, 7)
    plate.metadata.update({
        "study": "quilt-chemistry", "seed": seed, "steps": steps,
        "pattern": "ohio-star", "chemical_grid": list(solid.shape),
        "wall_pixels": 3, "box_mm": [*origin.tolist(), side, side],
        "coupling": "The exact block edges become impermeable raster walls; Gray–Scott "
                    "exchange uses zero permeability across them, not a clipped full-field run.",
        "scope": "Original geometry/chemistry combination; no historical or biological claim.",
    })
    return plate, {k: v for k, v in state.items() if isinstance(v, np.ndarray)}


def marbled_credentials(data, strength=1.0):
    """Two comb shears deform the actual catalogue-derived engraving paths."""
    if not np.isfinite(strength) or not 0 <= strength <= 2:
        raise ValueError("strength must be between 0 and 2")
    source, _ = guilloche_plate(data["tiers"], data["handoffs"])
    # Exclude the source composition's registration marks before deformation.
    strokes = [s for s in source.strokes if s.points[:, 1].min() > 20
               and s.points[:, 1].max() < 199]
    lines = [s.points for s in strokes]
    before = np.vstack(lines)
    lines = marbling.comb(lines, (0, 30), (1, 0), (0, 1), 16, 10,
                          10 * strength, 3.0, alternate=True, step=.7)
    lines = marbling.comb(lines, (25, 0), (0, 1), (1, 0), 19, 8,
                          5 * strength, 4.0, alternate=True, step=.7)
    points = np.vstack(lines)
    lo, hi = points.min(0), points.max(0)
    scale = min(140 / (hi[0] - lo[0]), 164 / (hi[1] - lo[1]))
    offset = np.array([85., 106.]) - (lo + hi) / 2 * scale
    plate = Plate("Credentials in a current")
    for points, original in zip(lines, strokes):
        plate.add(points * scale + offset, original.color, original.width, simplify=.015)
    furniture(plate, 7)
    plate.metadata.update({
        "study": "marbled-credentials", "strength": strength, "source": data["source"],
        "coupling": "Catalogue values construct the original engraving; two alternating "
                    "closed-form comb shears then move every vertex of that engraving.",
        "mapping": source.metadata["mapping"], "source_strokes": len(strokes),
        "scope": "Geometric deformation, not simulated corrosion. The source guilloché "
                 "intentionally has crossings; this composition does not remove them. "
                 "The deformed ornament is not presented as a decodable cipher.",
    })
    return plate, {"source_bounds": np.array([before.min(0), before.max(0)]),
                   "deformed_bounds": np.array([lo, hi])}


def turnover(record):
    """Per-file, per-version changed character fraction in [0, 1].

    (inserted + removed characters) / (previous + current characters).
    Identity is the existing blame key, not first authorship. The import
    column has no previous version and is deliberately assigned zero.
    """
    versions = historyflow.versions_from_runs(record)
    values = np.zeros((len(record["files"]), len(versions)))
    for k in range(1, len(versions)):
        for fi in range(len(record["files"])):
            a = {key: chars for key, _, f, chars in versions[k - 1] if f == fi}
            b = {key: chars for key, _, f, chars in versions[k] if f == fi}
            changed = sum(v for key, v in a.items() if key not in b)
            changed += sum(v for key, v in b.items() if key not in a)
            values[fi, k] = changed / max(sum(a.values()) + sum(b.values()), 1)
    return values


def revision_loom(record, seed=17, steps=1400):
    """Recorded manuscript turnover drives local dissolution in a shared textile."""
    change = turnover(record)
    ny, nx = change.shape
    if nx < 2 or ny < 1:
        raise ValueError("at least two versions and one manuscript required")
    textile = grammar(seed=seed, nx=nx, ny=ny)
    solid = textile.raster(pixels_per_tile=35, width=3)
    material = solid.astype(float)
    acid = np.zeros_like(material)
    supply = np.zeros_like(material)
    clearance = distance_transform_edt(~solid)
    yy, xx = np.mgrid[:solid.shape[0], :solid.shape[1]]
    vents = []
    for row, col in np.argwhere(change > 0):
        y0, x0 = row * 35, col * 35
        local = clearance[y0:y0 + 35, x0:x0 + 35]
        y, x = np.unravel_index(np.argmax(local), local.shape)
        y, x = int(y + y0), int(x + x0)
        # Small edits are made visible by an explicit nonlinear display gain.
        gain = .15 + .85 * np.sqrt(change[row, col])
        mask = ((xx - x) ** 2 + (yy - y) ** 2 < 3.5 ** 2) & ~solid
        supply[mask] = np.maximum(supply[mask], gain)
        vents.append([int(row), int(col), y, x, float(gain)])
    fixed = supply > 0
    history = []
    for step in range(steps):
        acid += .16 * flux_laplacian(acid, .03 + .30 * (1 - material))
        loss = .035 * acid * material
        material -= loss
        acid = np.maximum(acid - .20 * loss, 0)
        acid[fixed] = supply[fixed]
        if step % 50 == 0:
            history.append(float((solid - material).sum()))
    state = {"material": material, "acid": acid}
    plate = Plate("Revision loom")
    draw_component(plate, textile, "erosion", state, box=(20, 24, 130, 170))
    # A small unlabelled register: one column per recorded version. The JSON
    # carries the actual dates, titles, file names and numeric key.
    for k, value in enumerate(change.mean(0)):
        x = 32 + k * 106 / max(nx - 1, 1)
        plate.add([(x, 202), (x, 202 - 6 * np.sqrt(value))], RED, .35, simplify=0)
    furniture(plate, nx)
    plate.metadata.update({
        "study": "revision-loom", "seed": seed, "steps": steps,
        "book_revision": record["rev"], "files": record["files"],
        "versions": [{k: v[k] for k in ("commit", "date", "subject")}
                     for v in record["versions"]],
        "turnover": change.tolist(), "vents_row_col_y_x_gain": vents,
        "grid": list(solid.shape), "removed_material_cells": float((solid - material).sum()),
        "coupling": "Manuscript rows and revision columns locate reagent sources. "
                    "Source intensity = .15 + .85 sqrt(character turnover); diffusion "
                    "and irreversible material loss then alter the shared textile paths.",
        "scope": "An artistic material analogy driven by real Git records. Not an "
                 "authorship measure, quality score, or empirical model of editing.",
    })
    return plate, {"material": material, "initial": solid, "acid": acid,
                   "turnover": change, "supply": supply, "loss_history": np.array(history)}
