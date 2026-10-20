#!/usr/bin/env python3
"""An image-guided, Physarum-inspired sampler and greedy primitive SVG fitter.

This is an artistic hybrid, not an implementation of biological Physarum or a
claim of optimal reconstruction. Only placement proposals use the swarm.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import time
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import gaussian_filter, uniform_filter, zoom

VERSION = "primitive-growth-0.1"
KINDS = ("circle", "square", "triangle")
INKS = ("#202c32", "#b84836", "#af894b")  # charcoal, vermilion, ochre


def rgb(hex_color):
    return np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255


def hex_rgb(color):
    return "#" + "".join(f"{int(c):02x}" for c in np.clip(np.rint(color * 255), 0, 255))


def weighted_indices(rng, weights, count):
    a = np.maximum(np.asarray(weights).ravel(), 0).astype(np.float64)
    total = a.sum()
    if total <= 1e-15:
        return rng.integers(len(a), size=count)
    return np.searchsorted(np.cumsum(a), rng.random(count) * total).clip(0, len(a) - 1)


def load_source(path, width):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    white = Image.new("RGBA", im.size, "white")
    white.alpha_composite(im)
    im = white.convert("RGB")
    size = im.size
    im = im.resize((width, round(width * size[1] / size[0])), Image.Resampling.LANCZOS)
    target = np.asarray(im, dtype=np.float32) / 255
    # Border median is appropriate for these paper-backed illustrations; CLI can override.
    band = max(1, round(width * .02))
    border = np.concatenate((target[:band].reshape(-1, 3), target[-band:].reshape(-1, 3),
                             target[:, :band].reshape(-1, 3), target[:, -band:].reshape(-1, 3)))
    return target, np.median(border, axis=0), size


class Swarm:
    """Three forward sensors, turning, trail deposition, diffusion and decay.

    Artistic additions: image residual as food, no cell exclusion, reflecting
    boundaries, small heading noise, and occasional food-weighted reseeding.
    """
    def __init__(self, food, rng, agents=1600, trail_weight=.9, sensor=5.0):
        self.rng = rng
        self.h, self.w = food.shape
        self.trail = np.zeros_like(food)
        self.trail_weight = trail_weight
        self.sensor = sensor
        self.agents = agents
        ids = weighted_indices(rng, food + 1e-5, agents)
        self.x = ids % self.w + rng.random(agents)
        self.y = ids // self.w + rng.random(agents)
        self.heading = rng.uniform(-np.pi, np.pi, agents)
        self.steps = 0

    def sample(self, field, x, y):
        return field[np.clip(y.astype(int), 0, self.h - 1), np.clip(x.astype(int), 0, self.w - 1)]

    def advance(self, food, steps=6):
        for _ in range(steps):
            normalized = self.trail / max(float(np.percentile(self.trail, 97)), .1)
            field = food * 1.8 + self.trail_weight * np.minimum(normalized, 3)
            samples = [self.sample(field,
                                   self.x + self.sensor * np.cos(self.heading + angle),
                                   self.y + self.sensor * np.sin(self.heading + angle))
                       for angle in (-np.pi / 4, 0, np.pi / 4)]
            left, front, right = samples
            both = (left > front) & (right > front)
            turn = np.where(both, self.rng.choice((-1., 1.), self.agents),
                            np.where(left > right, -1., 1.))
            turn = np.where((left > front) | (right > front), turn, 0)
            self.heading += turn * np.pi / 5 + self.rng.normal(0, .035, self.agents)
            nx = self.x + 1.25 * np.cos(self.heading)
            ny = self.y + 1.25 * np.sin(self.heading)
            outside = (nx < 0) | (nx >= self.w) | (ny < 0) | (ny >= self.h)
            self.heading[outside] += np.pi
            self.x = np.clip(nx, .01, self.w - 1.01)
            self.y = np.clip(ny, .01, self.h - 1.01)
            np.add.at(self.trail, (self.y.astype(int), self.x.astype(int)), 1)
            self.trail = uniform_filter(self.trail, 3, mode="constant") * .92
            self.steps += 1
            if self.steps % 12 == 0:
                reset = self.rng.choice(self.agents, max(1, self.agents // 30), replace=False)
                ids = weighted_indices(self.rng, food + 1e-5, len(reset))
                self.x[reset], self.y[reset] = ids % self.w + .5, ids // self.w + .5
                self.heading[reset] = self.rng.uniform(-np.pi, np.pi, len(reset))

    def propose(self, food, count):
        # 80% proposals from persistent agents; 20% residual-food rescue proposals.
        n_swarm = max(1, round(count * .8))
        weights = self.sample(food, self.x, self.y) + .002
        ids = weighted_indices(self.rng, weights, n_swarm)
        x, y = self.x[ids].copy(), self.y[ids].copy()
        if n_swarm < count:
            rescue = weighted_indices(self.rng, food, count - n_swarm)
            x = np.r_[x, rescue % self.w + .5]
            y = np.r_[y, rescue // self.w + .5]
        return x, y


def vertices(kind, radius, angle):
    """Shapes have equal area pi*r^2 before rasterization/clipping."""
    if kind == "square":
        half = math.sqrt(math.pi) * radius / 2
        pts = np.array([[-half, -half], [half, -half], [half, half], [-half, half]])
    elif kind == "triangle":
        cr = math.sqrt(4 * math.pi / (3 * math.sqrt(3))) * radius
        a = np.array([-np.pi / 2, np.pi / 6, 5 * np.pi / 6])
        pts = np.column_stack((np.cos(a), np.sin(a))) * cr
    else:
        raise ValueError(kind)
    a = math.radians(angle)
    return pts @ np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])


@lru_cache(maxsize=2048)
def shape_mask(kind, radius, angle):
    bound = math.ceil(radius * 1.6 + 2)
    size, ss = bound * 2 + 1, 3
    axis = (np.arange(size * ss) + .5) / ss - (bound + .5)
    xx, yy = np.meshgrid(axis, axis)
    if kind == "circle":
        inside = xx ** 2 + yy ** 2 <= radius ** 2
    else:
        pts = vertices(kind, radius, angle)
        inside = np.ones_like(xx, dtype=bool)
        for p0, p1 in zip(pts, np.roll(pts, -1, axis=0)):
            delta = p1 - p0
            inside &= delta[0] * (yy - p0[1]) - delta[1] * (xx - p0[0]) >= 0
    mask = inside.reshape(size, ss, size, ss).mean(axis=(1, 3)).astype(np.float32)
    return mask[..., None], bound


def fit_patch(target, canvas, mask, palette):
    residual = target - canvas
    if palette is None:
        # Closed-form best constant RGB fill at either of two opacity levels.
        alphas = np.array([.65, 1.], dtype=np.float32)
        colors = []
        for alpha in alphas:
            m = mask * alpha
            color = np.sum(m * (target - (1 - m) * canvas), axis=(0, 1)) / max(float(np.sum(m * m)), 1e-9)
            colors.append(np.clip(color, 0, 1))
        colors = np.array(colors)
    else:
        colors = palette
        directions = mask[None] * (colors[:, None, None, :] - canvas[None])
        numerator = np.sum(directions * residual[None], axis=(1, 2, 3))
        denominator = np.sum(directions ** 2, axis=(1, 2, 3))
        alphas = np.clip(numerator / np.maximum(denominator, 1e-9), 0, 1)
    changes = mask[None] * alphas[:, None, None, None] * (colors[:, None, None, :] - canvas[None])
    gains = np.sum(2 * changes * residual[None] - changes ** 2, axis=(1, 2, 3))
    best = int(np.argmax(gains))
    return float(gains[best]), colors[best], float(alphas[best])


def run(source, out, *, method="physarum", palette="tricolor", count=2400,
        width=384, seed=23, candidates=8, min_radius=1.2, max_radius=18.,
        trail_weight=.9, sensor=5., shapes=KINDS, background=None):
    started = time.monotonic()
    rng = np.random.default_rng(seed)
    target, paper, source_size = load_source(source, width)
    if background:
        paper = rgb(background)
    # Quantize paper so the working canvas exactly matches the SVG fill.
    paper = rgb(hex_rgb(paper))
    h, w, _ = target.shape
    canvas = np.broadcast_to(paper, target.shape).copy()
    pal = np.array([rgb(c) for c in INKS] + [paper]) if palette == "tricolor" else None
    gray = target @ np.array([.2126, .7152, .0722])
    gy, gx = np.gradient(gaussian_filter(gray, .8))
    # Orientation follows local source contours. The swarm chooses position, not geometry.
    orientation = np.degrees(np.arctan2(gy, gx)) + 90
    importance = np.linalg.norm(target - paper, axis=2)
    swarm_shape = (max(1, h // 2), max(1, w // 2))
    food = None
    swarm = None
    shapes_out = []
    progress = []
    attempt = 0
    while len(shapes_out) < count and attempt < count * 3:
        if attempt % 24 == 0:
            error = np.mean((target - canvas) ** 2, axis=2)
            # Smooth to avoid single-pixel traps, keep a faint source-structure cue.
            food_full = gaussian_filter(np.sqrt(error) + .035 * importance, .7)
            food = zoom(food_full, (swarm_shape[0] / h, swarm_shape[1] / w), order=1)
            food /= max(float(np.percentile(food, 99)), 1e-8)
            if method == "physarum":
                if swarm is None:
                    swarm = Swarm(food, rng, trail_weight=trail_weight, sensor=sensor)
                    swarm.advance(food, 80)
                swarm.advance(food, 6)
        if method == "physarum":
            xs, ys = swarm.propose(food, candidates)
        else:
            ids = weighted_indices(rng, food, candidates)
            xs, ys = ids % food.shape[1] + .5, ids // food.shape[1] + .5
        xs = np.clip(np.rint(xs * w / food.shape[1]).astype(int), 0, w - 1)
        ys = np.clip(np.rint(ys * h / food.shape[0]).astype(int), 0, h - 1)
        kind = shapes[len(shapes_out) % len(shapes)]
        fraction = len(shapes_out) / count
        upper = max(min_radius + .5, max_radius * (1 - fraction) ** 1.5 + min_radius)
        best = None
        for cx, cy in zip(xs, ys):
            for _ in range(2):
                radius = round(float(np.exp(rng.uniform(math.log(min_radius), math.log(upper)))) * 2) / 2
                radius = max(.5, radius)
                angle = 0 if kind == "circle" else round((orientation[cy, cx] + rng.choice([-20, 0, 20])) / 10) * 10 % 360
                mask, bound = shape_mask(kind, radius, angle)
                x0, x1 = max(0, cx - bound), min(w, cx + bound + 1)
                y0, y1 = max(0, cy - bound), min(h, cy + bound + 1)
                m = mask[y0 - cy + bound:y1 - cy + bound, x0 - cx + bound:x1 - cx + bound]
                gain, color, alpha = fit_patch(target[y0:y1, x0:x1], canvas[y0:y1, x0:x1], m, pal)
                if best is None or gain > best[0]:
                    best = (gain, color, alpha, int(cx), int(cy), radius, angle, x0, x1, y0, y1, m)
        if best[0] > 1e-7:
            gain, color, alpha, cx, cy, radius, angle, x0, x1, y0, y1, mask = best
            # SVG serializes channels and opacity; fit with those same quantized values.
            color = rgb(hex_rgb(color))
            alpha = round(alpha, 4)
            canvas[y0:y1, x0:x1] += mask * alpha * (color - canvas[y0:y1, x0:x1])
            shapes_out.append(dict(kind=kind, x=cx + .5, y=cy + .5, radius=radius,
                                   angle=int(angle), color=hex_rgb(color), opacity=alpha))
        attempt += 1
        if len(shapes_out) and len(shapes_out) % 600 == 0 and (not progress or progress[-1]["count"] != len(shapes_out)):
            rmse = float(np.sqrt(np.mean((canvas - target) ** 2)) * 255)
            progress.append({"count": len(shapes_out), "fit_rmse_8bit": round(rmse, 3)})
            print(f"{Path(out).stem}: {len(shapes_out)}/{count}, fit RMSE {rmse:.2f}", flush=True)

    meta = {
        "version": VERSION, "source": Path(source).name,
        "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "method": method, "palette": palette, "inks": list(INKS) if pal is not None else "source-sampled RGB",
        "background": hex_rgb(paper), "source_size": source_size, "working_size": [w, h],
        "seed": seed, "requested_primitives": count, "primitives": len(shapes_out),
        "shape_counts": dict(Counter(s["kind"] for s in shapes_out)), "candidates_per_step": candidates,
        "min_radius": min_radius, "max_radius": max_radius, "trail_weight": trail_weight,
        "sensor_distance": sensor, "agent_count": 1600 if swarm else 0,
        "agent_steps": swarm.steps if swarm else 0, "rescue_fraction": .2 if swarm else 0,
        "fit_rmse_8bit": round(float(np.sqrt(np.mean((canvas - target) ** 2)) * 255), 4),
        "progress": progress, "elapsed_seconds": round(time.monotonic() - started, 2),
        "note": "Painter-ordered filled primitives; tricolor permits paper-colour repair shapes. RGB is unrestricted colour, not three primary ink separations."
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_svg(out, shapes_out, meta)
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    if swarm:
        trail = swarm.trail / max(float(np.percentile(swarm.trail, 99)), .01)
        heat = np.clip(trail, 0, 1)
        heat_rgb = paper[None, None] * (1 - heat[..., None]) + rgb(INKS[0])[None, None] * heat[..., None]
        Image.fromarray((heat_rgb * 255).astype("uint8")).save(out.with_name(out.stem + "-trail.png"))
    return meta


def write_svg(out, shapes, meta):
    w, h = meta["working_size"]
    sw, sh = meta["source_size"]
    title = f"{meta['source']} — {meta['method']}, {meta['palette']}"
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}" viewBox="0 0 {w} {h}">',
             f'<title>{escape(title)}</title>',
             '<desc>Experimental raster approximation made solely of filled circles, squares and equilateral triangles. Not an exact tracing of text or detail.</desc>',
             f'<metadata>{escape(json.dumps({k: v for k, v in meta.items() if k != "elapsed_seconds"}, sort_keys=True))}</metadata>',
             f'<rect width="{w}" height="{h}" fill="{meta["background"]}"/>']
    for i, s in enumerate(shapes):
        if i % 100 == 0:
            lines.append(f'<g id="pass-{i // 100:03d}">')
        x, y, r, angle = s["x"], s["y"], s["radius"], s["angle"]
        style = f'fill="{s["color"]}" fill-opacity="{s["opacity"]:.4f}"'
        if s["kind"] == "circle":
            lines.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}" {style}/>')
        elif s["kind"] == "square":
            side = math.sqrt(math.pi) * r
            lines.append(f'<rect x="{x-side/2:.3f}" y="{y-side/2:.3f}" width="{side:.3f}" height="{side:.3f}" transform="rotate({angle} {x:.3f} {y:.3f})" {style}/>')
        else:
            points = " ".join(f"{px+x:.3f},{py+y:.3f}" for px, py in vertices("triangle", r, angle))
            lines.append(f'<polygon points="{points}" {style}/>')
        if i % 100 == 99 or i == len(shapes) - 1:
            lines.append('</g>')
    lines.append('</svg>')
    out.write_text("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--method", choices=("physarum", "baseline"), default="physarum")
    p.add_argument("--palette", choices=("tricolor", "rgb"), default="tricolor")
    p.add_argument("--count", type=int, default=2400)
    p.add_argument("--width", type=int, default=384)
    p.add_argument("--seed", type=int, default=23)
    p.add_argument("--candidates", type=int, default=8)
    p.add_argument("--min-radius", type=float, default=1.2)
    p.add_argument("--max-radius", type=float, default=18)
    p.add_argument("--trail-weight", type=float, default=.9)
    p.add_argument("--sensor", type=float, default=5.)
    p.add_argument("--shapes", nargs="+", choices=KINDS, default=KINDS)
    p.add_argument("--background", help="Override border-derived paper, e.g. '#f1ead5'")
    args = vars(p.parse_args())
    source, output = args.pop("source"), args.pop("output")
    args["shapes"] = tuple(args["shapes"])
    if args["count"] < 1 or args["width"] < 32 or args["candidates"] < 1:
        p.error("count and candidates must be positive; width must be at least 32")
    if not 0 < args["min_radius"] < args["max_radius"]:
        p.error("require 0 < min-radius < max-radius")
    if args["sensor"] <= 0 or args["trail_weight"] < 0:
        p.error("sensor must be positive and trail-weight must be nonnegative")
    print(json.dumps(run(source, output, **args), indent=2))


if __name__ == "__main__":
    main()
