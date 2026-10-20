"""Four composition studies: process outputs combined with contour/pen hands."""
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from shapely.geometry import Polygon

from .drawing import Plate, INK, RED, contours, clipped, furniture, specimen_polygon
from .models import catchment, gray_scott, space_colonize, stratigraphy, recurrence


def basin_plate(seed=11, variant=0):
    state = catchment(seed, n=176, steps=42+variant*12, incision=.022+variant*.01)
    p = Plate("Dendritic ledger")
    furniture(p, 1)
    box = (15, 25, 140, 168)
    border = specimen_polygon(box)
    yy, xx = np.mgrid[:176, :176]
    mask = ((xx-87.5)/82)**2 + ((yy-87.5)/82)**2 < 1
    h = gaussian_filter(state["height"], .65)
    contours(p, h, np.linspace(.11, float(h.max())*.98, 78), box, mask, width=.105)
    rec, area = state["receiver"].ravel(), state["area"].ravel()
    threshold = 44 if variant == 0 else 72
    active = (area > threshold) & mask.ravel() & (rec >= 0)
    incoming = np.zeros(len(rec), int)
    np.add.at(incoming, rec[active], 1)
    starts = np.flatnonzero(active & (incoming != 1))
    channel_count = 0
    for i in starts:
        path, j = [int(i)], int(rec[i])
        while j >= 0:
            path.append(j)
            if not active[j] or incoming[j] != 1:
                break
            j = int(rec[j])
        if len(path) < 2:
            continue
        a = np.asarray(path)
        xy = np.column_stack([a % 176, a // 176])/175
        if len(xy) > 3:
            xy = gaussian_filter1d(xy, .8, axis=0, mode="nearest")
        xy = xy*[box[2], box[3]] + box[:2]
        clipped(p, xy, border, RED, min(.45, .10+.043*np.log1p(area[i])))
        channel_count += 1
    # Three survey ticks are deliberate apparatus, not additional data series.
    for y in (57, 109, 161):
        p.add([(8, y), (13, y)], width=.14)
    p.metadata = {"model": "dimensionless D8 + stream-power-inspired incision",
                  "seed": seed, "variant": variant, "n": 176, "steps": 42+variant*12,
                  "incision": .022+variant*.01, "contour_count": 78,
                  "channel_threshold_cells": threshold,
                  "channel_segments": channel_count,
                  "rendering": "height smoothed sigma=.65 cells; channel geometry sigma=.8 cells",
                  "limits": "open edges; depression fill; no sediment deposition; not calibrated"}
    return p, state


def strata_plate(seed=11, variant=0):
    state = stratigraphy(seed, throw=.24+.13*variant, fold=.24+.07*variant)
    p = Plate("Fault archive")
    furniture(p, 2)
    box = (13, 23, 144, 174)
    levels = np.linspace(-1.25, 1.35, 112)
    # Most layers in black; a sparse red marker bed repeats across the fault.
    contours(p, state["age"], levels, box, state["mask"], width=.11)
    contours(p, state["age"], levels[5::19], box, state["mask"], RED, .22)
    contours(p, state["body"].astype(float), [.5], box, width=.23)
    # Faults terminate on the specimen boundary, using the exact body mask.
    for key in ("fault1", "fault2"):
        curve = np.column_stack([(state[key][:, 0]+1)/2, np.linspace(0, 1, 320)])
        inside = state["body"][np.arange(320), np.clip((curve[:, 0]*319).astype(int), 0, 319)]
        cuts = np.flatnonzero(np.diff(np.r_[False, inside, False]))
        for a, b in cuts.reshape(-1, 2):
            p.add(curve[a:b]*box[2:]+box[:2], RED, .24)
    # Fine hatch follows the gradient-normal direction only in selected beds.
    gy, gx = np.gradient(state["age"])
    rng = np.random.default_rng(seed+400)
    for _ in range(4500):
        y, x = rng.integers(2, 318, 2)
        age = state["age"][y, x]
        if not state["mask"][y, x] or not (.23 < (age*9 % 1) < .53):
            continue
        if abs(age) > .85:
            continue
        g = np.array([gx[y, x], gy[y, x]])
        g /= max(np.linalg.norm(g), 1e-12)
        start = np.array([x, y])/319*box[2:]+box[:2]
        p.add([start, start+g*.45], INK, .075)
    p.metadata = {"model": "kinematic folded stratigraphy with two offset faults",
                  "seed": seed, "variant": variant, "n": 320,
                  "throw": .24+.13*variant, "fold": .24+.07*variant,
                  "contour_count": 112, "red": "marker beds and faults",
                  "limits": "illustrative deformation, no rock mechanics; hatch is a rendering choice"}
    return p, state


def tissue_plate(seed=11, variant=0):
    feed, kill = (.036, .061) if variant == 0 else (.028, .057)
    state = gray_scott(seed, n=192, steps=1900, feed=feed, kill=kill)
    rng = np.random.default_rng(seed+20)
    y, x = np.mgrid[0:1:192j, 0:1:192j]
    if variant == 0:
        # A pointed leaf envelope, with a reserved circular aperture.
        envelope = np.abs(x-.5) < .43*np.sin(np.pi*np.clip((y-.04)/.92, 0, 1))**.82
        aperture = (x-.5)**2 + ((y-.46)*1.3)**2 < .105**2
        roots = np.column_stack([np.full(25, .5), np.linspace(.94, .13, 25)])
    else:
        radius = np.sqrt(((x-.5)/.88)**2 + (y-.5)**2)
        envelope, aperture = radius < .465, radius < .13
        t = np.linspace(0, 2*np.pi, 42, endpoint=False)
        roots = np.column_stack([.5+.15*.88*np.cos(t), .5+.15*np.sin(t)])
    mask = envelope & ~aperture
    candidates = rng.random((16000, 2))
    xi, yi = (candidates[:, 0]*191).astype(int), (candidates[:, 1]*191).astype(int)
    food = state["v"][yi, xi]
    # Actual coupling: V changes the spatial distribution of attraction points.
    accept = mask[yi, xi] & (rng.random(len(candidates)) < .10+.82*np.clip(food/.35, 0, 1))
    growth = space_colonize(candidates[accept][:4200], roots, iterations=260)
    p = Plate("Vascular palimpsest")
    furniture(p, 3)
    box = (15, 22, 140, 174)
    # Analytic specimen boundaries avoid pixel stair steps at print scale.
    t = np.linspace(0, 2*np.pi, 600)
    if variant == 0:
        q = np.linspace(0, 1, 500)
        w = .43*np.sin(np.pi*q)**.82
        outer = np.vstack([np.column_stack([.5-w, .04+.92*q]),
                           np.column_stack([.5+w[::-1], .04+.92*q[::-1]])])
        inner = np.column_stack([.5+.105*np.cos(t), .46+.105/1.3*np.sin(t)])
    else:
        outer = np.column_stack([.5+.465*.88*np.cos(t), .5+.465*np.sin(t)])
        inner = np.column_stack([.5+.13*.88*np.cos(t), .5+.13*np.sin(t)])
    outer, inner = outer*box[2:]+box[:2], inner*box[2:]+box[:2]
    shape = Polygon(outer).difference(Polygon(inner))
    chemical = Plate("chemical contours")
    contours(chemical, state["v"], [.08, .18, .29, .36], box, width=.10)
    for s in chemical.strokes:
        clipped(p, s.points, shape, s.color, s.width)
    p.add(np.vstack([outer, outer[0]]), width=.24)
    p.add(inner, RED, .20)
    for i, parent in enumerate(growth["parents"]):
        if parent < 0:
            continue
        line = growth["nodes"][[parent, i]]*box[2:]+box[:2]
        w = .105 + .034*np.sqrt(min(120, growth["mass"][i]))
        clipped(p, line, shape, RED, w)
    if variant == 0:
        clipped(p, roots*box[2:]+box[:2], shape, RED, .42)
    state.update({"mask": mask, "nodes": growth["nodes"], "parents": growth["parents"],
                  "mass": growth["mass"], "attractors": candidates[accept][:4200]})
    p.metadata = {"model": "Gray-Scott -> biased attractors -> space colonization",
                  "seed": seed, "variant": variant, "n": 192, "steps": 1900,
                  "feed": feed, "kill": kill, "Du": .16, "Dv": .08, "dt": 1,
                  "boundaries": "reflecting chemical field; geometry clipped to specimen",
                  "attractor_count": int(min(4200, accept.sum())), "nodes": len(growth["nodes"]),
                  "space_colonization": {"step": .012, "kill": .025, "influence": .20, "iterations": 260},
                  "red": "tree edges, stem and aperture; width from subtree mass",
                  "limits": "one-way coupling; not Physarum, vasculature physiology, or a Turing-instability claim"}
    return p, state


def recurrence_plate(seed=11, variant=0, values=None, source="synthetic demonstration series"):
    rng = np.random.default_rng(seed)
    if values is None:
        t = np.arange(240)
        values = np.sin(t*.12 + .9*np.sin(t*.014)) + .3*np.sin(t*.049)
        values += .055*rng.normal(size=len(t))
        if variant:
            values[110:] += .6*np.sin((t[110:]-110)*.30)
    values = np.asarray(values, float)
    state = recurrence(values, epsilon=.48 if variant == 0 else .62)
    p = Plate("The return engine" if variant == 0 else "Recurrence loom")
    furniture(p, 4)
    indices = state["indices"]
    # One angular position per original input row; missing windows leave gaps.
    angles = -np.pi/2 + 2*np.pi*indices/len(values)
    xy = np.column_stack([85+60*np.cos(angles), 108+77*np.sin(angles)])
    pairs = np.column_stack(np.where(np.triu(state["matrix"], 1)))
    if variant == 1:
        # A second composition of the same declared relation: its symmetric
        # matrix drawn as short diagonal strokes, with the input trace above.
        n = len(values)
        x0, y0, size = 18, 47, 134
        cell = size/n
        for i, j in np.column_stack(np.where(state["matrix"])):
            x, y = x0+size*indices[j]/n, y0+size*indices[i]/n
            p.add([(x-cell*.30, y-cell*.30), (x+cell*.30, y+cell*.30)],
                  RED if indices[j] > indices[i] else INK, .13, simplify=0)
        p.add([(x0, y0), (x0+size, y0), (x0+size, y0+size), (x0, y0+size), (x0, y0)], width=.12)
        finite = values[np.isfinite(values)]
        norm = (values-finite.min())/max(np.ptp(finite), 1e-12)
        valid = np.isfinite(values)
        cuts = np.flatnonzero(np.diff(np.r_[False, valid, False]))
        for a, b in cuts.reshape(-1, 2):
            p.add(np.column_stack([x0+size*np.arange(a, b)/n, 35-12*norm[a:b]]), RED, .20)
        for fraction in np.arange(0, 1.01, .1):
            p.add([(x0+size*fraction, y0+size+2), (x0+size*fraction, y0+size+4)], width=.12)
        state["values"] = values
        p.metadata = {"model": "delay-embedded recurrence matrix", "source": source,
                      "synthetic": source == "synthetic demonstration series",
                      "seed": seed, "variant": variant, "input_rows": n,
                      "embedding_dimension": 3, "delay_rows": 2, "theiler_rows": 5,
                      "epsilon": .62, "metric": "Euclidean, per-coordinate population z-score",
                      "pair_count": state["pair_count"], "eligible_pairs": state["eligible_pairs"],
                      "sampling": "both symmetric matrix entries; no thinning",
                      "red": "upper triangle and min-max normalized input trace",
                      "limits": "row order, not elapsed time; no causal inference"}
        return p, state
    # No random thinning: every eligible recurrence is drawn once.
    u = np.linspace(0, 1, 22)[:, None]
    for i, j in pairs:
        a, b = xy[i], xy[j]
        centre = np.array([85, 108])
        control = centre + .22*((a+b)/2-centre)
        points = (1-u)**2*a + 2*(1-u)*u*control + u*u*b
        p.add(points, INK, .075, simplify=.045)
    # Actual data trace as a radial envelope; auxiliary rings are decoration.
    finite = values[np.isfinite(values)]
    lo, hi = float(finite.min()), float(finite.max())
    v = (values-lo)/max(hi-lo, 1e-12)
    angle = -np.pi/2 + 2*np.pi*np.arange(len(values))/len(values)
    trace = np.column_stack([85+(64+v*9)*np.cos(angle), 108+(81+v*9)*np.sin(angle)])
    valid = np.isfinite(values)
    cuts = np.flatnonzero(np.diff(np.r_[False, valid, False]))
    for a, b in cuts.reshape(-1, 2):
        p.add(trace[a:b], RED, .22)
    for radius in [1, 1.022]:
        t = np.linspace(0, 2*np.pi, 500)
        p.add(np.column_stack([85+61.5*radius*np.cos(t), 108+78.5*radius*np.sin(t)]), width=.11)
    for i in range(0, len(values), max(1, len(values)//60)):
        a = -np.pi/2 + 2*np.pi*i/len(values)
        p.add([(85+74.5*np.cos(a), 108+91.5*np.sin(a)),
               (85+76*np.cos(a), 108+93*np.sin(a))], RED if i % 5 == 0 else INK, .12)
    state["values"] = values
    p.metadata = {"model": "delay-embedded recurrence chords", "source": source,
                  "synthetic": source == "synthetic demonstration series",
                  "seed": seed, "variant": variant, "input_rows": len(values),
                  "embedding_dimension": 3, "delay_rows": 2, "theiler_rows": 5,
                  "epsilon": .48 if variant == 0 else .62, "metric": "Euclidean, per-coordinate population z-score",
                  "pair_count": state["pair_count"], "eligible_pairs": state["eligible_pairs"],
                  "sampling": "all eligible undirected pairs, no thinning",
                  "red": "min-max normalized input series in original row order",
                  "limits": "angular spacing encodes row order, not elapsed time; curves are decorative; no causal inference"}
    return p, state


STUDIES = {"basin": basin_plate, "strata": strata_plate, "tissue": tissue_plate,
           "recurrence": recurrence_plate}
