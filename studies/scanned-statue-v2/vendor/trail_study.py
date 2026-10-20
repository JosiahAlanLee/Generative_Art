#!/usr/bin/env python3
"""Direct trail allocation: a network interpretation, without greedy image fitting.

Three independent image-fed swarms, one for each ink. Sample primitive centres
from each colony's recent trail; orient polygons to the trail tangent. The ink
assignment is expressive, not an estimate of source colour separations.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, zoom

from primitive_growth import INKS, KINDS, Swarm, VERSION, hex_rgb, load_source, rgb, weighted_indices, write_svg


def run_trail(source, output, count=3600, seed=23):
    rng = np.random.default_rng(seed)
    target, paper, source_size = load_source(source, 384)
    paper = rgb(hex_rgb(paper))
    h, w, _ = target.shape
    gray = target @ np.array([.2126, .7152, .0722])
    food = zoom(np.clip((paper @ np.array([.2126, .7152, .0722])) - gray, 0, 1), .5, order=1)
    food = gaussian_filter(food, .8)
    food /= max(float(np.percentile(food, 99)), 1e-8)
    shapes = []
    trails = []
    # More dark marks keep the silhouette legible; other colonies create crossings.
    allocations = [round(count * .60), round(count * .20)]
    allocations.append(count - sum(allocations))
    for ink_index, n in enumerate(allocations):
        colony = Swarm(food, rng, agents=1000, trail_weight=1.8, sensor=6 + ink_index)
        accumulated = np.zeros_like(food)
        for _ in range(8):
            colony.advance(food, 35)
            accumulated += colony.trail
        field = .65 * colony.trail + .35 * accumulated / 8
        # Keep some of the network bridges through lighter parts of the figure.
        weights = np.maximum(field, 0) ** 1.25 * (.08 + food) ** .55
        ids = weighted_indices(rng, weights, n)
        ys, xs = ids // food.shape[1], ids % food.shape[1]
        gy, gx = np.gradient(gaussian_filter(field, 1))
        angle = np.degrees(np.arctan2(gy[ys, xs], gx[ys, xs])) + 90
        for j in range(n):
            x = (xs[j] + rng.random()) * w / food.shape[1]
            y = (ys[j] + rng.random()) * h / food.shape[0]
            radius = float(rng.uniform(.65, 1.7))
            shapes.append(dict(kind=KINDS[j % 3], x=float(x), y=float(y), radius=radius,
                               angle=int(round(angle[j] / 5) * 5), color=INKS[ink_index],
                               opacity=round(float(rng.uniform(.65, .95)), 4)))
        trails.append(field)
    # Interleave the colonies rather than putting the last ink above all others.
    rng.shuffle(shapes)
    meta = {
        "version": VERSION, "source": Path(source).name,
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "core_code_sha256": hashlib.sha256(Path(__file__).with_name("primitive_growth.py").read_bytes()).hexdigest(),
        "source_size": source_size, "working_size": [w, h], "background": hex_rgb(paper),
        "method": "trail-first", "palette": "tricolor", "inks": list(INKS),
        "primitives": len(shapes), "shape_counts": dict(Counter(s["kind"] for s in shapes)),
        "ink_allocations": allocations, "seed": seed, "agents_per_colony": 1000,
        "steps_per_colony": 280, "trail_weight": 1.8, "sensors": [6, 7, 8],
        "note": "Expressive network study. Independent ink colonies; no residual-fitting stage. Not part of the equal-budget reconstruction comparison."
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_svg(output, shapes, meta)
    output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    combined = np.clip(sum(trails) / max(float(np.percentile(sum(trails), 99)), 1e-8), 0, 1)
    im = paper[None, None] * (1 - combined[..., None]) + rgb(INKS[0])[None, None] * combined[..., None]
    Image.fromarray((im * 255).astype("uint8")).save(output.with_name(output.stem + "-trail.png"))
    return meta


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--count", type=int, default=3600)
    p.add_argument("--seed", type=int, default=23)
    a = p.parse_args()
    if a.count < 3:
        p.error("count must be at least three")
    print(json.dumps(run_trail(a.source, a.output, a.count, a.seed), indent=2))
