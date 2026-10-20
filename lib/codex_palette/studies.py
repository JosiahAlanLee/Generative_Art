"""Plate compositions for the Codex palette studies (170 × 220 mm, two inks).

Each study returns ``(plate, state)``: a ``lib.process_art.drawing.Plate`` and a
dict of arrays for the sidecar NPZ. Geometry is absolute millimetres, written
the same way as the process-art studies, so the book's ``svgimport`` reads it.
"""
from math import cos, radians, sin

import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union

from lib.process_art.drawing import INK, RED, Plate, furniture

from . import guilloche, historyflow, marbling
from .tubes import adapt, chains, disc_mesh, tube_graph

__all__ = ["history_plate", "tubes_plate", "marbling_plate", "guilloche_plate",
           "NOTA_V_NODES", "TUBE_PRESETS", "MARBLING_STAGES"]


# --- History Flow ------------------------------------------------------------

# Texture per class: (ink, thread spacing in mm, pen width in mm).
HISTORY_TEXTURE = {
    "base": (INK, 1.10, .10),
    "codex": (INK, .36, .13),
    "claude": (RED, .36, .13),
    "direct": (RED, 1.10, .10),
}


def _bezier(x0, y0, x1, y1, n=28):
    t = np.linspace(0, 1, n)[:, None]
    dx = (x1 - x0) / 2
    p0, p1, p2, p3 = (np.array(p, float) for p in ((x0, y0), (x0 + dx, y0), (x1 - dx, y1), (x1, y1)))
    return (1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3


def history_plate(record, spacing="version", box=(22, 24, 126, 172), column=2.0):
    """History Flow of ``record`` (from ``historyflow.extract``).

    Columns are versions; a column's length is its character count. Bands are
    drawn as threads whose spacing and ink identify the class of the commit
    that last changed those lines. Short red rules beside the outer columns
    mark where one file ends and the next begins.
    """
    lines = historyflow.versions_from_runs(record)
    n = len(lines)
    if n < 2:
        raise ValueError("History Flow needs at least two versions")
    x0, y0, w, h = box
    totals = [sum(l[3] for l in v) for v in lines]
    scale = h / max(totals)
    if spacing == "time":
        from datetime import datetime
        t = np.array([datetime.fromisoformat(v["date"]).timestamp() for v in record["versions"]])
        xs = x0 + (t - t[0]) / max(t[-1] - t[0], 1) * w
    elif spacing == "version":
        xs = x0 + np.arange(n) * w / (n - 1)
    else:
        raise ValueError("spacing is 'version' or 'time'")
    spans = [y0 + np.concatenate([[0], np.cumsum([l[3] for l in v])]) * scale for v in lines]
    plate = Plate("History Flow — revisions of the Codex manuscripts")
    half = column / 2
    threads = {c: 0 for c in historyflow.CLASSES}
    for k in range(n - 1):
        for i0, i1, j0, j1, cls in historyflow.transitions(lines[k], lines[k + 1]):
            ink, gap, width = HISTORY_TEXTURE[cls]
            ta, ba = spans[k][i0], spans[k][i1]
            tb, bb = spans[k + 1][j0], spans[k + 1][j1]
            count = max(1, int(round(max(ba - ta, bb - tb) / gap)))
            for q in range(count):
                f = (q + .5) / count
                plate.add(_bezier(xs[k] + half, ta + f*(ba - ta), xs[k+1] - half, tb + f*(bb - tb)),
                          ink, width, simplify=.01)
            threads[cls] += count
    for k, v in enumerate(lines):
        left, right = xs[k] - half, xs[k] + half
        plate.add([(left, spans[k][0]), (left, spans[k][-1])], INK, .10)
        plate.add([(right, spans[k][0]), (right, spans[k][-1])], INK, .10)
        start = 0
        for i in range(1, len(v) + 1):
            if i == len(v) or v[i][1] != v[start][1]:
                cls = v[start][1]
                if cls != "base":       # the base text stays open; later text is hatched in
                    ink, gap, width = HISTORY_TEXTURE[cls]
                    top, bottom = spans[k][start], spans[k][i]
                    for y in np.arange(top + gap / 2, max(bottom, top + gap / 2 + 1e-6), gap):
                        plate.add([(left, y), (right, y)], ink, width, simplify=0)
                start = i
        if k in (0, n - 1):
            side = -1 if k == 0 else 1
            for i in range(1, len(v)):
                if v[i][2] != v[i - 1][2]:
                    y = spans[k][i]
                    plate.add([(xs[k] + side*(half + .8), y), (xs[k] + side*(half + 4.0), y)], RED, .16)
    furniture(plate, n)
    plate.metadata.update({
        "study": "history-flow", "spacing": spacing, "repository_rev": record["rev"],
        "files": record["files"],
        "versions": [{"commit": v["commit"], "date": v["date"], "subject": v["subject"],
                      "characters": int(t)} for v, t in zip(record["versions"], totals)],
        "classes": {c: {"ink": "red" if HISTORY_TEXTURE[c][0] == RED else "black",
                        "thread_spacing_mm": HISTORY_TEXTURE[c][1]} for c in historyflow.CLASSES},
        "origins": record["origins"], "threads": threads,
        "meaning": "Band class is the class of the last commit to change each line (git blame); "
                   "not first authorship and not a share of authorship.",
    })
    return plate, {"characters": np.array(totals)}


# --- Tube networks -------------------------------------------------------------

# Nota V's seven food nodes and arena as the book declares them:
# books/05_notoria/plates/notae.py RUNS["v"]["nodes"] (cells on a 160-cell grid)
# and fields/physarum.py (disc arena, radius .47 of the grid width).
NOTA_V_NODES = ((80, 38), (126, 62), (132, 104), (92, 130), (50, 112), (44, 66), (100, 94))
NOTA_GRID, NOTA_ARENA = 160, .47

TUBE_PRESETS = {
    0: {"gamma": 1.8, "flux": 2.0, "label": "gamma 1.8: a single tree-like loop"},
    1: {"gamma": 1.15, "flux": 1.0, "label": "gamma 1.15: loops and cross-links"},
    2: {"gamma": 1.15, "flux": 0.2, "label": "gamma 1.15, lower flux: thinner, fewer links"},
}


def _chaikin(p, rounds=3):
    p = np.asarray(p, float)
    for _ in range(rounds):
        if len(p) < 3:
            return p
        q = .75 * p[:-1] + .25 * p[1:]
        r = .25 * p[:-1] + .75 * p[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2], mid[1::2] = q, r
        p = np.vstack([p[:1], mid, p[-1:]])
    return p


def _dashed(p, on=1.1, off=.9):
    p = np.asarray(p, float)
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])
    out, start = [], 0.0
    while start < s[-1]:
        stop = min(start + on, s[-1])
        u = np.linspace(start, stop, max(2, int((stop - start) / .2) + 1))
        out.append(np.column_stack([np.interp(u, s, p[:, 0]), np.interp(u, s, p[:, 1])]))
        start = stop + off
    return out


def _vessels(plate, pts, edges, D, threshold, to_mm, wall=.13, core_share=.35, min_w=.35, max_w=2.6):
    """Outline the union of all tubes; draw red centre lines in the strongest tubes."""
    e, w = tube_graph(edges, D, threshold)
    if not len(e):
        return 0
    top = w.max()
    shapes, cores = [], []
    for path, weight in chains(e, w):
        p = _chaikin(to_mm(pts[path]))
        width = min_w + (max_w - min_w) * (weight / top) ** .5   # D ~ radius^4 is drawn as radius ~ D^.25..^.5
        shapes.append(LineString(p).buffer(width / 2, quad_segs=6))
        if weight / top > core_share:
            cores.append(p)
    union = unary_union(shapes)
    for g in (union.geoms if hasattr(union, "geoms") else [union]):
        plate.add(np.asarray(g.exterior.coords), INK, wall, simplify=.02)
        for ring in g.interiors:
            plate.add(np.asarray(ring.coords), INK, wall, simplify=.02)
    for p in cores:
        plate.add(p, RED, .10, simplify=.01)
    return len(shapes)


def _strands(plate, pts, edges, D, threshold, to_mm, width=.10):
    e, w = tube_graph(edges, D, threshold)
    for path, _ in chains(e, w):
        plate.add(_chaikin(to_mm(pts[path]), 2), INK, width, simplify=.02)


def tubes_plate(seed=53, variant=1, steps=2400, spacing=2.0, nodes=NOTA_V_NODES):
    """Tero tubes grown between Nota V's seven nodes in the Notoria's disc arena.

    Black: the walls of every tube still above threshold, merged at junctions.
    Red: centre lines of the strongest tubes, the food nodes, and (dashed) tubes
    that were strong at the middle inset's step and have since been given up.
    Three small discs show earlier states of the same run.
    """
    preset = TUBE_PRESETS[variant]
    rng = np.random.default_rng(seed)
    centre, radius = np.array([NOTA_GRID / 2, NOTA_GRID / 2]), NOTA_ARENA * NOTA_GRID
    pts, edges, lengths, food = disc_mesh(nodes, centre, radius, spacing, rng)
    marks = (steps // 12, steps // 4, steps // 2)
    D, snaps, _ = adapt(pts, edges, lengths, food, rng, steps=steps, flux=preset["flux"],
                        gamma=preset["gamma"], record=marks)
    threshold = .01
    plate = Plate("Tubes between seven nodes — after Tero et al.")
    cx, cy, R = 85, 90, 68
    big = lambda p: (np.asarray(p) - centre) / radius * R + [cx, cy]
    drawn = _vessels(plate, pts, edges, D, threshold, big)
    abandoned = (snaps[marks[1]] > threshold * 4) & (D < threshold)
    for path, _ in chains(edges[abandoned], np.ones(int(abandoned.sum()))):
        for dash in _dashed(_chaikin(big(pts[path]))):
            plate.add(dash, RED, .10, simplify=0)
    plate.ring(cx, cy, R + 1.4, INK, .12)
    plate.ring(cx, cy, R + 2.2, INK, .10)
    for x, y in big(np.asarray(nodes, float)):
        plate.ring(x, y, 1.7, RED, .16)
        plate.ring(x, y, .5, RED, .16)
    for k, m in enumerate(marks):
        sx, sy, r = 47 + k * 38, 183, 13.5
        small = lambda p, sx=sx: (np.asarray(p) - centre) / radius * r + [sx, sy]
        _strands(plate, pts, edges, snaps[m], threshold * 2, small)
        plate.ring(sx, sy, r + .8, INK, .10)
        for x, y in small(np.asarray(nodes, float)):
            plate.ring(x, y, .5, RED, .12)
    furniture(plate, len(nodes))
    plate.metadata.update({
        "study": "tero-tubes", "seed": seed, "variant": variant, "preset": preset,
        "model": "Tero, Kobayashi & Nakagaki 2007 / Tero et al. 2010: Kirchhoff flow between a "
                 "random source and sink among the food nodes each step; conductivity relaxes "
                 "toward q^gamma/(1+q^gamma) of the flux it carried",
        "nodes_cells": [list(map(int, n)) for n in nodes],
        "arena": {"grid": NOTA_GRID, "disc_radius_fraction": NOTA_ARENA},
        "mesh": {"spacing_cells": spacing, "points": int(len(pts)), "edges": int(len(edges))},
        "steps": steps, "dt": .05, "initial_D": [.5, 1.0], "threshold": threshold,
        "insets_at_steps": list(marks), "drawn_tube_chains": drawn,
        "edges_above_threshold": int((D > threshold).sum()), "abandoned_edges": int(abandoned.sum()),
        "abandoned_rule": f"D > {threshold*4} at step {marks[1]} (middle inset) and D < {threshold} at the end",
        "drawing": "wall width .35-2.6 mm grows with sqrt(D/Dmax); red centre lines where D > .35 Dmax",
        "comparison": "Same nodes and arena as the book's Nota V (Jones agents). A different model, "
                      "not a control run for that plate.",
    })
    return plate, {"points": pts, "edges": edges, "D": D, "food": food}


# --- Marbling --------------------------------------------------------------------

MARBLING_STAGES = {0: "stone", 1: "gel-git", 2: "nonpareil"}


def marbling_plate(seed=7, variant=2, step=.5):
    """A plottable marbled sheet: stone drops, then (variant 1) gel-git, then (2) nonpareil.

    The tank is larger than the paper; operations act on the tank and the result
    is clipped to the paper, as a sheet is lifted from a larger bath.
    """
    rng = np.random.default_rng(seed)
    tank = (-12.0, -12.0, 182.0, 232.0)
    lines, tags = marbling.stone_ground(rng, tank, count=64, radius=17.0, rings=3, step=step)
    ops = [{"op": "stone", "sites": 64, "drops": 64 * 3, "radius_mm": 17.0, "rings": 3}]
    if variant >= 1:
        lines = marbling.comb(lines, (tank[0] + 4, tank[1]), (0, 1), (1, 0), 11.0, 18, 15.0, 5.0,
                              alternate=True, step=step)
        ops.append({"op": "gel-git", "direction": "vertical, alternating", "spacing_mm": 11.0,
                    "tines": 18, "z_mm": 15.0, "lambda_mm": 5.0})
    if variant >= 2:
        lines = marbling.comb(lines, (tank[0], tank[1] + 1), (1, 0), (0, 1), 2.8, 88, 5.0, 1.4, step=step)
        ops.append({"op": "nonpareil comb", "direction": "horizontal", "spacing_mm": 2.8,
                    "tines": 88, "z_mm": 5.0, "lambda_mm": 1.4})
    paper = (12.0, 14.0, 158.0, 206.0)
    plate = Plate(f"Marbled sheet — {MARBLING_STAGES[variant]}")
    clipped_lines, clipped_tags = [], []
    for p, tag in zip(lines, tags):
        for part in marbling.clip([p], paper):
            clipped_lines.append(part)
            clipped_tags.append(tag)
    printable, owners, repair = marbling.print_paths(clipped_lines)
    for part, owner in zip(printable, owners):
        plate.add(part, RED if clipped_tags[owner] == 1 else INK, .12, simplify=0)
    x0, y0, x1, y1 = paper
    plate.add([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], INK, .16, simplify=0)
    plate.metadata.update({
        "study": "marbling", "seed": seed, "variant": variant, "stage": MARBLING_STAGES[variant],
        "operations": ops, "resample_step_mm": step, "tank_mm": tank, "paper_mm": paper,
        "inks": "first and third ring of each drop black, second ring red",
        "model": "Lu, Jaffer et al. 2012 closed-form drop and tine maps applied to polylines",
        "print_repair": repair,
    })
    return plate, {"tags": np.array(tags)}


# --- Guilloché credentials -------------------------------------------------------

GUILLOCHE_CENTRE, GUILLOCHE_RING, GUILLOCHE_SEAL = (85.0, 106.0), 57.0, 12.5


def _station(i):
    a = radians(-90 + i * 360 / 7)
    cx, cy = GUILLOCHE_CENTRE
    return np.array([cx + GUILLOCHE_RING * cos(a), cy + GUILLOCHE_RING * sin(a)])


def _outside(plate, points, keep_out, color, width):
    g = LineString(points).difference(keep_out)
    for part in (g.geoms if hasattr(g, "geoms") else [g]):
        if part.geom_type == "LineString" and len(part.coords) > 1:
            plate.add(np.asarray(part.coords), color, width, simplify=.01)


def guilloche_plate(tiers, handoffs):
    """Seven office rosettes and twenty-one passage bands from the Escalationum catalogue.

    ``tiers``: dicts with id, name, legions, authority, competence, liability.
    ``handoffs``: dicts with source, target, name, legions, mark.

    Declared mapping, taking the catalogue's "authority is a quantity of
    ornament" literally:
      rosette passes = 3 + 4 × authority; lobes = 6 + 2 × authority
      reeds on the rim (a coin's milled edge) = the office's legions
      red plain rings at the centre = competence (6 − authority in the catalogue)
      band crests along a passage = the passage spirit's legions
      the red strand's phase = its mark, read as a clock hour (mark × 30°)
    Stations sit on a heptagon as in the book's own seal matrix; bands stop at
    every seal's rim.
    """
    from shapely.geometry import Point
    plate = Plate("Credentials — seven offices and twenty-one passages")
    centre = np.array(GUILLOCHE_CENTRE)
    seals = unary_union([Point(*_station(t["id"])).buffer(GUILLOCHE_SEAL + .6, quad_segs=24)
                         for t in tiers])
    rows = []
    for h in handoffs:
        a, b = _station(h["source"]), _station(h["target"])
        bow = centre + .38 * ((a + b) / 2 - centre)
        crests = max(1, int(h["legions"]))
        for strand in guilloche.path_band(a, b, bow, 1.5, crests, 3):
            _outside(plate, strand, seals, INK, .10)
        red = guilloche.path_band(a, b, bow, 1.5, crests, 1, phase0=radians(30 * int(h["mark"])))[0]
        _outside(plate, red, seals, RED, .10)
        rows.append({k: h[k] for k in ("source", "target", "name", "legions", "mark")})
    for t in tiers:
        c = _station(t["id"])
        authority, competence = int(t["authority"]), int(t["competence"])
        r_out = GUILLOCHE_SEAL
        lobes = 6 + 2 * authority
        for p in guilloche.rosette(c, 4.2, r_out - 2.4, 3 + 4 * authority, lobes,
                                   .55 + .08 * authority, np.pi / lobes / 2):
            plate.add(p, INK, .10, simplify=.01)
        plate.ring(c[0], c[1], r_out - 1.2, INK, .12)
        plate.ring(c[0], c[1], r_out, INK, .14)
        for reed in guilloche.reeded_rim(c, r_out - .05, max(1, int(t["legions"])), .9):
            plate.add(reed, INK, .10, simplify=0)
        for k in range(competence):
            plate.ring(c[0], c[1], .6 + .5 * k, RED, .12)
    furniture(plate, 7)
    plate.metadata.update({
        "study": "guilloche-credentials",
        "mapping": {
            "rosette_passes": "3 + 4 * authority", "lobes": "6 + 2 * authority",
            "rim_reeds": "office legions", "red_centre_rings": "competence",
            "band_crests": "passage legions", "red_strand_phase_deg": "30 * mark",
        },
        "tiers": [{k: t[k] for k in ("id", "name", "legions", "authority", "competence", "liability")}
                  for t in tiers],
        "handoffs": rows,
        "source": "books/03_escalationum/manuscript/catalogue.json in Codex-Intervallorum",
    })
    return plate, {"legions": np.array([t["legions"] for t in tiers])}
