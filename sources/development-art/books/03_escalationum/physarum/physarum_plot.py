#!/usr/bin/env python3
"""
physarum_plot.py - raster image -> Physarum transport network -> layered plotter SVG.

Pipeline
  1. Separate the image into pen layers (any pen colors; light or dark paper)
     with a small non-negative least-squares unmix (optical density on light
     paper, additive light on dark paper).
  2. Build food maps from tone + edge strength, plus a shared edge-tangent
     flow field (structure tensor).
  3. Run a Jones (2010) style agent model (sense / rotate / move / deposit, one
     agent per cell, 3x3 diffusion + decay). Agents follow their own trail plus
     the image's food, and their heading is nudged along the image's contours.
     Two ways to assign agents:
       per pen   one population per pen, each fed by its own color separation
       cultures  a faithful population (strong image pull) and a feral one
                 (weak pull, follows its own trail), drawn in two pens, sharing
                 space; they repel (competing; optionally holding marked
                 territories and home ground) or attract (symbiotic, shared cords)
  4. Vectorize each layer's trail map, order the strokes to cut pen-up travel,
     and write an SVG with one Inkscape/AxiDraw layer per pen, plus raster
     previews and the raw trail map ("plate"). Styles:
       topo     nested iso-lines of the trail map
       network  skeleton centerlines, thickened into tapered veins
       fibers   traced paths of a sample of agents
       hatch    tone hatching: outline, hatch, then crosshatch as the trail
                thickens; one direction per layer (after the Book V notae)
       marks    one short dash per lattice cell along the vein, in the pen of
                the strongest layer, inside a double contour (after Nota Clausa)

Usage
  python physarum_plot.py photo.jpg -o out/                     # CMYK, balanced
  python physarum_plot.py photo.jpg -o out/ --look feral --palette sepia
  python physarum_plot.py photo.jpg -o out/ --palette "paper=#ffffff,ink=#222222"
  python physarum_plot.py sample:chelsea -o out/ --grid 600 --steps 500   # quick test

  Per pen, with the station dial and an accent pen:
  python physarum_plot.py gremory.png -o out/ --station 2 --floor rust=0.3 \\
      --palette "paper=#eae3d1,ochre=#a8854a,steel=#3d5e6e,slate=#1f2b30,rust=#a32b24"

  Two cultures, competing over marked territories, with home ground:
  python physarum_plot.py gremory.png -o out/ --cultures slate:ochre --station 2 \\
      --floor rust=0.3 --density 0.3 --home "0.53,0.225,0.045,0.04" \\
      --palette "paper=#eae3d1,ochre=#a8854a,slate=#1f2b30,rust=#a32b24"
  ... or symbiotic: replace --home with --attract 1

  --look sets the fidelity dial (faithful / balanced / feral); --station N sets
  it continuously instead (0 = faithful ... 6 = feral), and with --cultures it
  sets the feral share of agents (15% ... 85%). Any of --wfood, --flow, --so,
  --edge given explicitly overrides the dial. --floor makes a pen an accent that
  only draws where it clearly belongs. List pens light to dark: layers are
  written in that order, so plotting them in order puts dark lines on top.
  Runtime is roughly proportional to grid area x steps x pens: a 720 x 1080,
  three-layer run is about a minute plus export on two cores.

Requires: numpy scipy scikit-image pillow numba skan
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from pathlib import Path

import numpy as np
from numba import njit
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage import io, measure, transform
from skimage.filters import gaussian

# ----------------------------------------------------------------------------
# pens / color separation
# ----------------------------------------------------------------------------
PRESETS = {
    # name: (paper, [(label, hex), ...])
    "cmyk": ("#f7f4ec", [("cyan", "#009fe3"), ("magenta", "#e5007d"),
                         ("yellow", "#ffd500"), ("black", "#1d1d1b")]),
    "rgb-black": ("#121212", [("red", "#ff4a3d"), ("green", "#3ddc6a"),
                              ("blue", "#3b82ff"), ("white", "#f2f2f2")]),
    "sepia": ("#f4efe4", [("slate", "#3d5a80"), ("sienna", "#b5532d"),
                          ("ochre", "#d9a23b"), ("sepia", "#2b211b")]),
}

# the fidelity dial: how hard the image pulls vs. the network's own trail
LOOKS = {
    "faithful": dict(wfood=30.0, flow=0.6, so=7.0, edge=1.3),
    "balanced": dict(wfood=12.0, flow=0.35, so=9.0, edge=1.0),
    "feral": dict(wfood=3.5, flow=0.12, so=12.0, edge=1.0),
}


def station_look(station, n_max=6):
    """Continuous dial: station 0 = faithful ... station n_max = feral
    (image pull interpolated in log space, the rest linearly)."""
    t = min(max(station / n_max, 0.0), 1.0)
    f, r = LOOKS["faithful"], LOOKS["feral"]
    out = {k: f[k] + t * (r[k] - f[k]) for k in f}
    out["wfood"] = math.exp((1 - t) * math.log(f["wfood"]) + t * math.log(r["wfood"]))
    return out


def hex2rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255.0


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def separate(img_srgb, pens_srgb, paper_srgb, ridge=0.03):
    """Exact ridge-regularized NNLS by active-set enumeration (fine for <=6 pens).

    Light paper: inks add optical density.  Dark paper: inks add light.
    Returns coverage (K,H,W) in [0,1].
    """
    img = srgb_to_lin(img_srgb)
    pens = srgb_to_lin(np.asarray(pens_srgb))
    paper = srgb_to_lin(paper_srgb)
    light = paper.mean() > 0.4
    if light:
        T = -np.log(np.clip(img / paper, 1e-3, 1.0))
        B = -np.log(np.clip(pens / paper, 0.02, 1.0))  # real inks never hit 0
    else:
        T = np.clip(img - paper, 0, None)
        B = np.clip(pens - paper, 0, None)
    H, W, _ = T.shape
    X = T.reshape(-1, 3)
    K = len(B)
    best_err = (X ** 2).sum(1)  # empty support
    best = np.zeros((X.shape[0], K))
    for r in range(1, K + 1):
        for sub in itertools.combinations(range(K), r):
            sub = list(sub)
            Bs = B[sub]
            A = Bs @ Bs.T + ridge * np.eye(r)
            Cs = X @ Bs.T @ np.linalg.inv(A)
            ok = (Cs >= 0).all(1)
            full = np.zeros_like(best)
            full[:, sub] = Cs
            err = ((full @ B - X) ** 2).sum(1) + ridge * (full ** 2).sum(1)
            upd = ok & (err < best_err)
            best[upd] = full[upd]
            best_err[upd] = err[upd]
    cov = np.clip(best, 0, 1).reshape(H, W, K).transpose(2, 0, 1)
    return cov


# ----------------------------------------------------------------------------
# image fields
# ----------------------------------------------------------------------------
def pctnorm(a, p=99.0):
    v = np.percentile(a, p)
    return np.clip(a / (v + 1e-9), 0, 1)


def structure_flow(cov, sigma_d=1.0, rho=4.0):
    """Multi-channel (Di Zenzo) structure tensor -> tangent angle + strength."""
    J11 = J12 = J22 = 0.0
    for c in cov:
        g = gaussian(c, sigma_d)
        gy, gx = np.gradient(g)
        J11 = J11 + gx * gx
        J12 = J12 + gx * gy
        J22 = J22 + gy * gy
    J11, J12, J22 = (gaussian(j, rho) for j in (J11, J12, J22))
    disc = np.sqrt(np.maximum((J11 - J22) ** 2 / 4 + J12 ** 2, 0))
    tr = (J11 + J22) / 2
    l1, l2 = tr + disc, tr - disc
    theta = 0.5 * np.arctan2(2 * J12, J11 - J22)      # gradient direction
    phi = theta + np.pi / 2                            # contour (tangent)
    coh = ((l1 - l2) / (l1 + l2 + 1e-12)) ** 2
    strength = coh * pctnorm(np.sqrt(np.maximum(l1, 0)), 98)
    return phi.astype(np.float32), strength.astype(np.float32)


def prepare(img_srgb, grid_w, pens, paper, tone_gamma=0.85,
            tone_w=0.6, edge_w=1.0, tone_blur=2.0, edge_blur=1.5, floors=None):
    """floors: {pen_name: f} turns a pen into an accent: coverage below f is
    dropped and the rest rescaled, so it only draws where it clearly belongs."""
    H0, W0 = img_srgb.shape[:2]
    grid_h = int(round(H0 * grid_w / W0))
    img = transform.resize(img_srgb, (grid_h, grid_w), anti_aliasing=True)
    cov = separate(img, [hex2rgb(p) for _, p in pens], hex2rgb(paper))
    accent = np.zeros(len(pens), bool)
    for k, (name, _) in enumerate(pens):
        f = (floors or {}).get(name)
        if f:
            cov[k] = np.clip((cov[k] - f) / (1 - f), 0, 1)
            # keep only coherent marks: drop isolated specks that clear the floor
            core = _drop_small(cov[k] > 0.2, max(4, int((grid_w / 100) ** 2 / 2)))
            cov[k] *= ndi.binary_dilation(core, iterations=2)
            accent[k] = True
    cov = cov ** tone_gamma
    food, edges = [], []
    for c in cov:
        gm = np.hypot(*np.gradient(gaussian(c, 1.0)))
        e = pctnorm(gaussian(pctnorm(gm, 99), edge_blur), 99.5)
        edges.append(e)
        food.append(tone_w * gaussian(c, tone_blur) + edge_w * e)
    phi, fstr = structure_flow(cov)
    return dict(img=img, cov=cov.astype(np.float32), accent=accent,
                food=np.array(food, np.float32), edges=np.array(edges, np.float32),
                phi=phi, fstr=fstr)


# ----------------------------------------------------------------------------
# Physarum (Jones 2010 style, excluded volume)
# ----------------------------------------------------------------------------
@njit(cache=True)
def _seed(s):
    np.random.seed(s)


@njit(cache=True, fastmath=True)
def _sense(field, x, y, H, W):
    ix = int(x)
    iy = int(y)
    if x < 0.0 or y < 0.0 or ix >= W or iy >= H:
        return -1e9
    return field[iy, ix]


@njit(cache=True)
def _shuffle(a):
    for i in range(a.shape[0] - 1, 0, -1):
        j = np.random.randint(i + 1)
        t = a[i]
        a[i] = a[j]
        a[j] = t


@njit(cache=True, fastmath=True)
def _step(x, y, h, order, moved, trail, sense, occ, flow,
          SA, RA, SO, SS, dep, kflow, jitter):
    """One Jones-model update for one species.
    sense = trail + wfood*food (from the previous step); deposits go to trail.
    flow[..., :2] = unit contour tangent, flow[..., 2] = steering strength."""
    H, W = trail.shape
    _shuffle(order)
    twopi = 2.0 * np.pi
    cSA = np.cos(SA)
    sSA = np.sin(SA)
    for k in range(order.shape[0]):
        i = order[k]
        hi = h[i]
        ch = np.cos(hi)
        sh = np.sin(hi)
        # --- motor stage: step forward if the cell is free, else pick a new heading
        nx = x[i] + ch * SS
        ny = y[i] + sh * SS
        cx0 = int(x[i])
        cy0 = int(y[i])
        moved[i] = False
        if nx < 0.0 or ny < 0.0 or nx >= W or ny >= H:
            hi = np.random.random() * twopi
            ch = np.cos(hi)
            sh = np.sin(hi)
        else:
            cx = int(nx)
            cy = int(ny)
            if (cx == cx0 and cy == cy0) or occ[cy, cx] == 0:
                occ[cy0, cx0] = 0
                occ[cy, cx] = 1
                x[i] = nx
                y[i] = ny
                trail[cy, cx] += dep
                moved[i] = True
            else:
                hi = np.random.random() * twopi
                ch = np.cos(hi)
                sh = np.sin(hi)
        # --- sensory stage: three sensors, rotate toward the strongest
        xf = x[i]
        yf = y[i]
        cl = ch * cSA + sh * sSA
        sl = sh * cSA - ch * sSA
        cr = ch * cSA - sh * sSA
        sr = sh * cSA + ch * sSA
        F = _sense(sense, xf + ch * SO, yf + sh * SO, H, W)
        FL = _sense(sense, xf + cl * SO, yf + sl * SO, H, W)
        FR = _sense(sense, xf + cr * SO, yf + sr * SO, H, W)
        if F > FL and F > FR:
            pass
        elif F < FL and F < FR:
            if np.random.random() < 0.5:
                hi += RA
            else:
                hi -= RA
        elif FL < FR:
            hi += RA
        elif FR < FL:
            hi -= RA
        # --- nudge heading along the image's contour direction
        if kflow > 0.0:
            ix = int(xf)
            iy = int(yf)
            s = flow[iy, ix, 2]
            if s > 0.0:
                tx = flow[iy, ix, 0]
                ty = flow[iy, ix, 1]
                if ch * tx + sh * ty < 0.0:   # contour is unoriented: use nearer sense
                    tx = -tx
                    ty = -ty
                hi += kflow * s * (ch * ty - sh * tx)   # sin(angle to tangent)
        if jitter > 0.0:
            hi += jitter * (np.random.random() - 0.5)
        h[i] = hi - twopi * np.floor(hi / twopi)


@njit(cache=True)
def _respawn(x, y, h, moved, occ, cov, cand, rate):
    """Move a few agents sitting on low-coverage cells to cells drawn from the
    coverage distribution (keeps agent density tracking tone)."""
    H, W = occ.shape
    n = x.shape[0]
    m = int(n * rate) + 1
    for t in range(m):
        i = np.random.randint(n)
        cx0 = int(x[i])
        cy0 = int(y[i])
        if np.random.random() < 1.0 - cov[cy0, cx0]:
            c = cand[np.random.randint(cand.shape[0])]
            cy = c // W
            cx = c % W
            if occ[cy, cx] == 0:
                occ[cy0, cx0] = 0
                occ[cy, cx] = 1
                x[i] = cx + np.random.random()
                y[i] = cy + np.random.random()
                h[i] = np.random.random() * 2.0 * np.pi
                moved[i] = False


def _sample_cells(p, n, rng):
    """n distinct cells, probability ∝ p (Gumbel top-k)."""
    p = p.ravel().astype(float)
    n = min(n, int((p > 0).sum()))
    keys = np.log(rng.random(p.size) + 1e-300) / np.maximum(p, 1e-12)
    return np.argpartition(-keys, n - 1)[:n]


def simulate(prep, steps=1200, density=0.16, SA=22.5, RA=45.0, SO=9.0, SS=1.0,
             dep=5.0, decay=0.1, wfood=12.0, kflow=0.35, jitter=0.0,
             respawn=0.003, avg_last=150, record_last=0, record_frac=0.12,
             seed=1, verbose=True):
    rng = np.random.default_rng(seed)
    _seed(seed)
    cov, food = prep["cov"], prep["food"]
    phi, fstr = prep["phi"], prep["fstr"]
    flow = np.ascontiguousarray(np.stack([np.cos(phi), np.sin(phi), fstr], -1), np.float32)
    K, H, W = cov.shape
    SA, RA = math.radians(SA), math.radians(RA)
    wfood = np.float32(wfood)
    sp = []
    for s in range(K):
        n = int(density * cov[s].sum())
        cells = _sample_cells(cov[s] + 1e-7, n, rng)
        n = len(cells)
        occ = np.zeros((H, W), np.uint8)
        occ.ravel()[cells] = 1
        x = (cells % W + rng.random(n)).astype(np.float64)
        y = (cells // W + rng.random(n)).astype(np.float64)
        h = rng.random(n) * 2 * np.pi
        p = cov[s].ravel()
        cand = _sample_cells(p + 1e-9, min(400_000, max(1, int((p > 0.05).sum()))), rng)
        terr = None
        if prep.get("accent") is not None and prep["accent"][s]:
            # accent pens stay local: trail only survives near their own marks
            terr = ndi.binary_dilation(cov[s] > 0.05, iterations=max(2, int(1.5 * SO))).astype(np.float32)
        rec_ids = rng.choice(n, max(1, int(n * record_frac)), replace=False) if record_last else None
        sp.append(dict(terr=terr, x=x, y=y, h=h, occ=occ, order=np.arange(n, dtype=np.int64),
                       moved=np.zeros(n, np.bool_), trail=np.zeros((H, W), np.float32),
                       avg=np.zeros((H, W), np.float32), cand=cand.astype(np.int64),
                       rec_ids=rec_ids, rec=[]))
    if verbose:
        print("agents per layer:", [len(s["x"]) for s in sp], f"grid {W}x{H}")
    t0 = time.time()
    for t in range(steps):
        for s, d in enumerate(sp):
            sense = d["trail"] + wfood * food[s]
            _step(d["x"], d["y"], d["h"], d["order"], d["moved"], d["trail"], sense,
                  d["occ"], flow, SA, RA, SO, SS, dep, kflow, jitter)
            if respawn > 0:
                _respawn(d["x"], d["y"], d["h"], d["moved"], d["occ"], cov[s], d["cand"], respawn)
            d["trail"] = ndi.uniform_filter(d["trail"], 3, mode="constant") * (1 - decay)
            if d["terr"] is not None:
                d["trail"] *= d["terr"]
            if t >= steps - avg_last:
                d["avg"] += d["trail"] / avg_last
            if record_last and t >= steps - record_last:
                ids = d["rec_ids"]
                d["rec"].append(np.stack([d["x"][ids], d["y"][ids],
                                          d["moved"][ids].astype(float)], 1).astype(np.float32))
        if verbose and (t % 200 == 0 or t == steps - 1):
            print(f"  step {t:5d}  {time.time() - t0:6.1f}s", flush=True)
    out = dict(trail=np.array([d["avg"] for d in sp]),
               final=np.array([d["trail"] for d in sp]))
    if record_last:
        out["paths"] = [np.array(d["rec"]) for d in sp]   # (T, n, 3)
    return out


# ----------------------------------------------------------------------------
# two competing cultures
# ----------------------------------------------------------------------------
def ink_darkness(img_srgb, paper, gamma=0.85):
    """Perceptual darkness relative to the paper: 0 = paper, 1 = black."""
    w = np.array([0.2126, 0.7152, 0.0722])
    return np.clip(1 - (img_srgb @ w) / (hex2rgb(paper) @ w), 0, 1) ** gamma


def home_map(shape, anchors):
    """anchors: [(cx, cy, rx, ry)] as fractions of the image -> soft map in [0, 1]."""
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W]
    m = np.zeros(shape)
    for cx, cy, rx, ry in anchors:
        m = np.maximum(m, np.exp(-0.5 * (((xx / W - cx) / rx) ** 2 + ((yy / H - cy) / ry) ** 2)))
    return m.astype(np.float32)


def prepare_cultures(img_srgb, grid_w, pens, paper, looks, floors=None, tone_w=0.6, anchors=None):
    """Fields for two cultures sharing one figure.
    Both cultures feed on the same ink-darkness map (each with its own edge weight);
    accent pens (those with a floor) keep their own color-separated coverage."""
    prep = prepare(img_srgb, grid_w, pens, paper, tone_w=tone_w, floors=floors)
    dark = ink_darkness(prep["img"], paper)
    gm = np.hypot(*np.gradient(gaussian(dark, 1.0)))
    e = pctnorm(gaussian(pctnorm(gm, 99), 1.5), 99.5)
    tone = gaussian(dark, 2.0)
    phi, fstr = structure_flow([dark])
    out = dict(img=prep["img"], dark=dark.astype(np.float32), phi=phi, fstr=fstr,
               foods=[(tone_w * tone + L["edge"] * e).astype(np.float32) for L in looks],
               accents=[(prep["cov"][k], prep["food"][k]) for k in np.flatnonzero(prep["accent"])],
               home=home_map(dark.shape, anchors) if anchors else None)
    return out


def _territories(dark, home, balance, k, rng):
    """Split the figure into k Voronoi regions seeded on the ink; give a share
    `balance` of them to the feral culture, but regions holding home ground
    always go to the faithful culture. Returns a bool map: True = faithful."""
    H, W = dark.shape
    sites = _sample_cells(dark + 1e-9, k, rng)
    pts = np.c_[sites % W, sites // W].astype(float)
    yy, xx = np.mgrid[0:H, 0:W]
    _, lab = cKDTree(pts).query(np.c_[xx.ravel(), yy.ravel()])
    lab = lab.reshape(H, W)
    faithful = np.zeros(k, bool)
    if home is not None:
        faithful |= ndi.maximum(home, lab, np.arange(k)) > 0.8     # regions holding an anchor
    free = np.flatnonzero(~faithful)
    n_feral = min(len(free), int(round(balance * k)))
    # nested: with the same seed, a higher balance annexes regions in the same order
    faithful[rng.permutation(free)[n_feral:]] = True
    return faithful[lab]


@njit(cache=True)
def _recall(x, y, h, moved, occ, cov, cand, thr, prob):
    """Agents that wandered off the figure (coverage < thr) return to it."""
    H, W = occ.shape
    for i in range(x.shape[0]):
        cx0 = int(x[i])
        cy0 = int(y[i])
        if cov[cy0, cx0] < thr and np.random.random() < prob:
            c = cand[np.random.randint(cand.shape[0])]
            cy = c // W
            cx = c % W
            if occ[cy, cx] == 0:
                occ[cy0, cx0] = 0
                occ[cy, cx] = 1
                x[i] = cx + np.random.random()
                y[i] = cy + np.random.random()
                h[i] = np.random.random() * 2.0 * np.pi
                moved[i] = False


def simulate_cultures(fields, looks, balance, repel=1.0, home_boost=1.0, territories=0, mark=0.25,
                      steps=1200, density=0.3, SA=22.5, RA=45.0, SS=1.0, dep=5.0, decay=0.1,
                      respawn=0.003, recall=0.02, avg_last=150, record_last=0, record_frac=0.08,
                      seed=1, verbose=True):
    """Two cultures compete for one figure.

    looks = (faithful, feral), each a dict with wfood / flow / so.
    balance = the feral culture's share of the agents (the station sets this).
    The cultures share one occupancy grid, so they compete for space, and each is
    repelled by the other's trail. With territories=k the figure starts divided
    into k regions held by one culture or the other. Ground is marked: a culture
    feeds fully on its own ground but gets only `mark` of the image pull on the
    other's, and agents respawn near their own colony. The marked map follows
    whichever culture actually occupies the ground, so borders move only by
    competition. Where fields['home'] is set, the faithful culture always holds
    that ground (woven mode: it gets a boosted pull there instead). Accent
    species stay near their marks. Layers are returned as [feral, faithful, *accents].
    """
    rng = np.random.default_rng(seed)
    _seed(seed)
    dark, home = fields["dark"], fields["home"]
    H, W = dark.shape
    env = gaussian(dark, max(2.0, W / 70)).astype(np.float32)   # the figure's envelope, for recall
    flow = np.ascontiguousarray(np.stack([np.cos(fields["phi"]), np.sin(fields["phi"]), fields["fstr"]], -1),
                                np.float32)
    SA, RA = math.radians(SA), math.radians(RA)
    fa, fe = looks
    boost = (1 + home_boost * home) if (home is not None and not territories) else 1.0
    pull = [np.float32(fe["wfood"]) * fields["foods"][1],                      # feral
            (np.float32(fa["wfood"]) * fields["foods"][0] * boost).astype(np.float32)]  # faithful

    def agents(cells):
        n = len(cells)
        return dict(x=(cells % W + rng.random(n)).astype(np.float64),
                    y=(cells // W + rng.random(n)).astype(np.float64),
                    h=rng.random(n) * 2 * np.pi, order=np.arange(n, dtype=np.int64),
                    moved=np.zeros(n, np.bool_), trail=np.zeros((H, W), np.float32),
                    avg=np.zeros((H, W), np.float32),
                    rec_ids=rng.choice(n, max(1, int(n * record_frac)), replace=False) if (record_last and n) else None,
                    rec=[])

    # --- the two cultures: seeded together on the ink, split by balance (and home ground)
    n = int(density * dark.sum())
    cells = _sample_cells(dark + 1e-7, n, rng)
    n_cand = min(400_000, max(1, int((dark > 0.05).sum())))
    if territories:
        terr_f = _territories(dark, home, balance, territories, rng)
        is_f = terr_f.ravel()[cells]
        cands = [_sample_cells(dark * ~terr_f + 1e-9, n_cand, rng), _sample_cells(dark * terr_f + 1e-9, n_cand, rng)]
    else:
        p_faith = np.full(len(cells), 1.0 - balance)
        if home is not None:
            p_faith = np.clip(p_faith * (1 + 3.0 * home.ravel()[cells]), 0, 1)
        is_f = rng.random(len(cells)) < p_faith
        cands = [_sample_cells(dark + 1e-9, n_cand, rng)] * 2
    occ = np.zeros((H, W), np.uint8)
    occ.ravel()[cells] = 1
    sp = [agents(cells[~is_f]), agents(cells[is_f])]
    for d, L, c in zip(sp, (fe, fa), cands):
        d.update(occ=occ, cand=c.astype(np.int64), cov=dark, SO=L["so"], kflow=L["flow"], terr=None)

    # --- accents: own space, confined near their own marks, faithful look
    for cov, food in fields["accents"]:
        n_a = int(density * cov.sum())
        c_a = _sample_cells(cov + 1e-7, n_a, rng)
        d = agents(c_a)
        occ_a = np.zeros((H, W), np.uint8)
        occ_a.ravel()[c_a] = 1
        p = cov.ravel()
        d.update(occ=occ_a, cov=cov, SO=fa["so"], kflow=fa["flow"],
                 cand=_sample_cells(p + 1e-9, min(400_000, max(1, int((p > 0.05).sum()))), rng).astype(np.int64),
                 terr=ndi.binary_dilation(cov > 0.05, iterations=max(2, int(1.5 * fa["so"]))).astype(np.float32),
                 pull=np.float32(fa["wfood"]) * food)
        sp.append(d)
    if verbose:
        print("agents: feral", len(sp[0]["x"]), "faithful", len(sp[1]["x"]),
              "accents", [len(d["x"]) for d in sp[2:]], f"grid {W}x{H}")

    sig = max(2.0, W / 60)
    held = None                                   # faithful-held ground, 0..1 (territories only)
    pr, pf = pull
    if territories:
        held = gaussian(terr_f.astype(np.float32), sig)
        if home is not None:
            held = np.maximum(held, home)
    t0 = time.time()
    for t in range(steps):
        tr_r, tr_f = sp[0]["trail"], sp[1]["trail"]
        if territories:
            if t and t % 50 == 0:
                # the marked ground follows whoever actually occupies it
                gr, gf = gaussian(tr_r, sig), gaussian(tr_f, sig)
                held = 0.8 * held + 0.2 * (gf + 1e-3) / (gr + gf + 2e-3)
                if home is not None:
                    held = np.maximum(held, home)
                for d, own in ((sp[0], 1 - held), (sp[1], held)):    # respawn near your own colony
                    d["cand"] = _sample_cells(dark * own ** 2 + 1e-9, n_cand, rng).astype(np.int64)
            if t % 50 == 0:
                pr = (pull[0] * (mark + (1 - mark) * (1 - held))).astype(np.float32)
                pf = (pull[1] * (mark + (1 - mark) * held)).astype(np.float32)
        senses = [tr_r + pr - repel * tr_f, tr_f + pf - repel * tr_r]
        senses += [d["trail"] + d["pull"] for d in sp[2:]]
        order = [0, 1] if t % 2 == 0 else [1, 0]          # alternate who moves first
        for s in order + list(range(2, len(sp))):
            d = sp[s]
            if len(d["x"]) == 0:
                continue
            _step(d["x"], d["y"], d["h"], d["order"], d["moved"], d["trail"], senses[s],
                  d["occ"], flow, SA, RA, d["SO"], SS, dep, d["kflow"], 0.0)
            if respawn > 0:
                _respawn(d["x"], d["y"], d["h"], d["moved"], d["occ"], d["cov"], d["cand"], respawn)
            if recall > 0 and s < 2:
                _recall(d["x"], d["y"], d["h"], d["moved"], d["occ"], env, d["cand"], 0.02, recall)
        for d in sp:
            d["trail"] = ndi.uniform_filter(d["trail"], 3, mode="constant") * (1 - decay)
            if d["terr"] is not None:
                d["trail"] *= d["terr"]
            if t >= steps - avg_last:
                d["avg"] += d["trail"] / avg_last
            if record_last and t >= steps - record_last and d["rec_ids"] is not None:
                ids = d["rec_ids"]
                d["rec"].append(np.stack([d["x"][ids], d["y"][ids],
                                          d["moved"][ids].astype(float)], 1).astype(np.float32))
        if verbose and (t % 200 == 0 or t == steps - 1):
            print(f"  step {t:5d}  {time.time() - t0:6.1f}s", flush=True)
    out = dict(trail=np.array([d["avg"] for d in sp]), final=np.array([d["trail"] for d in sp]))
    if record_last:
        out["paths"] = [np.array(d["rec"]) if d["rec"] else np.zeros((1, 1, 3), np.float32) for d in sp]
    return out


# ----------------------------------------------------------------------------
# vectorization
# ----------------------------------------------------------------------------
def _drop_small(mask, n):
    """Remove connected blobs of <= n pixels (works across skimage versions)."""
    from skimage.morphology import remove_small_objects
    try:
        return remove_small_objects(mask, max_size=n)
    except TypeError:
        return remove_small_objects(mask, min_size=n + 1)


def _skeleton_paths(mask):
    """skan Skeleton + branch table with underscore column names (any skan version)."""
    from skan import Skeleton, summarize
    from skimage.morphology import skeletonize
    sk = skeletonize(mask)
    if sk.sum() < 3:
        return None, None
    S = Skeleton(sk)
    try:
        df = summarize(S, separator="_")
    except TypeError:
        df = summarize(S)
        df.columns = [c.replace("-", "_") for c in df.columns]
    return S, df


def _plen(c):
    return float(np.hypot(*np.diff(c, axis=0).T).sum()) if len(c) > 1 else 0.0


def _smooth(c, win=5, closed=False):
    if len(c) < win + 2:
        return c
    k = np.ones(win) / win
    if closed:
        pad = np.concatenate([c[-win:], c, c[:win]])
        return np.stack([np.convolve(pad[:, j], k, "same")[win:-win] for j in range(2)], 1)
    out = np.stack([np.convolve(c[:, j], k, "same") for j in range(2)], 1)
    h = win // 2
    out[:h], out[-h:] = c[:h], c[-h:]  # keep endpoints
    return out


def norm_trail(T, p=99.3):
    out = []
    for t in T:
        t = gaussian(t, 0.8)
        nz = t[t > 1e-3]
        out.append(t / (np.percentile(nz, p) if nz.size else 1.0))
    return np.array(out)


def contours(Tn, levels=(0.12, 0.35, 0.7), min_len=10.0, tol=0.25, sigma=1.0):
    """'topo' style: nested iso-lines of the trail map, so thick veins get
    several concentric outlines and thin capillaries a single tight loop."""
    lines = []
    Ts = gaussian(Tn, sigma) if sigma else Tn
    for lv in levels:
        for c in measure.find_contours(Ts, lv):
            if _plen(c) < min_len:
                continue
            closed = np.allclose(c[0], c[-1])
            c = _smooth(c, 3, closed)
            c = measure.approximate_polygon(c, tol)
            lines.append(c[:, ::-1].copy())          # (row,col) -> (x,y)
    return lines


def _offset(c, d):
    """Offset an (x,y) polyline sideways by d (scalar or per-vertex array)."""
    t = np.gradient(c, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    d = np.asarray(d, float).reshape(-1, 1)
    return c + d * np.stack([-t[:, 1], t[:, 0]], 1)


def weighted_network(Tn, thr=0.12, levels=(0.3, 0.55, 0.8), spacing=1.05, ramp=0.2,
                     min_spur=12.0, min_len=4.0, tol=0.3):
    """'network' style: skeleton centerlines, thickened with strokes that peel
    away from the centerline as the vein gets stronger, so trunks taper into
    capillaries as in the trail-map plates. Each thickening level is drawn as
    one closed lens (out along one side, back along the other) to save pen lifts."""
    S, df = _skeleton_paths(_drop_small(Tn > thr, 12))
    if S is None:
        return []
    Ts = gaussian(Tn, 1.5)          # vein strength, a little wider than the ridge
    H, W = Tn.shape
    lines = []
    for i in range(S.n_paths):
        bt, bl = int(df["branch_type"][i]), float(df["branch_distance"][i])
        if (bt == 1 and bl < min_spur) or bl < min_len:
            continue
        rc = S.path_coordinates(i)
        inten = Ts[np.clip(rc[:, 0], 0, H - 1).astype(int), np.clip(rc[:, 1], 0, W - 1).astype(int)]
        c = _smooth(rc[:, ::-1].astype(float), 5)
        if len(inten) >= 7:
            inten = np.convolve(np.pad(inten, 3, mode="edge"), np.ones(7) / 7, "valid")
        lines.append(measure.approximate_polygon(c, tol))
        for j, lv in enumerate(levels, 1):
            on = inten > lv
            if not on.any():
                break
            idx = np.flatnonzero(np.diff(np.concatenate([[0], on.astype(int), [0]])))
            for a, b in zip(idx[::2], idx[1::2]):
                if b - a < 4:
                    continue
                w = np.clip((inten[a:b] - lv) / ramp, 0, 1)
                w = w * w * (3 - 2 * w)                      # smoothstep taper
                d = j * spacing * w
                lens = np.vstack([_offset(c[a:b], d), _offset(c[a:b], -d)[::-1]])
                lines.append(measure.approximate_polygon(lens, tol))
    return lines


def agent_paths(rec, Tn, thr=0.15, min_len=25.0, win=9, tol=0.35, break_on_bump=False,
                max_paths=None, rng=None):
    """'fibers' style: recorded agent trajectories, cut where the agent
    teleported (respawn) or wandered off the network; optionally also where it
    bumped into a neighbor."""
    T, n, _ = rec.shape
    H, W = Tn.shape
    lines = []
    for j in range(n):
        xy = rec[:, j, :2].astype(float)
        mv = rec[:, j, 2] > 0.5 if break_on_bump else np.ones(T, bool)
        ix = np.clip(xy[:, 0].astype(int), 0, W - 1)
        iy = np.clip(xy[:, 1].astype(int), 0, H - 1)
        jump = np.r_[True, np.hypot(*np.diff(xy, axis=0).T) > 2.5]
        good = mv & (Tn[iy, ix] > thr) & ~jump
        # split into runs of good samples
        idx = np.flatnonzero(np.diff(np.concatenate([[0], good.astype(int), [0]])))
        for a, b in zip(idx[::2], idx[1::2]):
            c = xy[a:b]
            if _plen(c) < min_len:
                continue
            c = _smooth(c, win)
            c = measure.approximate_polygon(c, tol)
            lines.append(c)
    if max_paths and len(lines) > max_paths:
        rng = rng or np.random.default_rng(0)
        keep = rng.choice(len(lines), max_paths, replace=False)
        lines = [lines[k] for k in sorted(keep)]
    return lines


def _hatch_runs(mask, step, ang_deg, phase=0.0, sample=0.5, min_len=4.0):
    """Straight parallel lines `step` cells apart at `ang_deg`, kept where `mask` is set,
    as 2-point strokes (runs shorter than min_len cells are dropped)."""
    H, W = mask.shape
    a = math.radians(ang_deg)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    R = math.hypot(W, H) / 2
    offs = np.arange(-R, R, step) + phase
    ts = np.arange(-R, R, sample)
    X = W / 2 + nx * offs[:, None] + ux * ts[None, :]
    Y = H / 2 + ny * offs[:, None] + uy * ts[None, :]
    inside = (X >= 0) & (Y >= 0) & (X < W) & (Y < H)
    on = inside & mask[np.clip(Y.astype(int), 0, H - 1), np.clip(X.astype(int), 0, W - 1)]
    lines = []
    for r in np.flatnonzero(on.any(1)):
        d = np.diff(np.r_[0, on[r].astype(np.int8), 0])
        for s, e in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1):
            if (e - s) * sample >= min_len:
                lines.append(np.array([[X[r, s], Y[r, s]], [X[r, e], Y[r, e]]]))
    return lines


def hatch_fill(T, angle, spacing=3.6, levels=(0.15, 0.3, 0.6), sigma=3.0, min_len=4.8):
    """'hatch' style, after the Book V notae: smooth the trail into tone, outline its lowest
    band, hatch the band above in one direction and cross-hatch the densest band."""
    Ts = gaussian(T, sigma)
    nz = Ts[Ts > 1e-3]
    Ts = Ts / (np.percentile(nz, 99) if nz.size else 1.0)
    lines = []
    for c in measure.find_contours(Ts, levels[0]):
        if _plen(c) >= 12:
            c = measure.approximate_polygon(_smooth(c, 3, bool(np.allclose(c[0], c[-1]))), 0.25)
            lines.append(c[:, ::-1].copy())
    lines += _hatch_runs(Ts >= levels[1], spacing, angle, min_len=min_len)
    lines += _hatch_runs(Ts >= levels[2], spacing * 0.7, angle + 90, phase=spacing * 0.35, min_len=min_len)
    return lines


def lattice_marks(Tn, pitch, thr=0.2, dash=0.65, quant=8, sigma=1.5):
    """'marks' style, after the Nota Clausa plates: one short dash per lattice cell, laid
    along the local vein direction (quantized to `quant` directions), in the pen of
    whichever layer is strongest there. Returns one list of strokes per layer."""
    K, H, W = Tn.shape
    Ts = np.array([gaussian(t, sigma) for t in Tn])
    phi, _ = structure_flow([Ts.sum(0)], sigma_d=1.0, rho=2.0)
    xs, ys = np.arange(pitch / 2, W, pitch), np.arange(pitch / 2, H, pitch)
    gx, gy = np.meshgrid(xs, ys)
    ix, iy = gx.astype(int), gy.astype(int)
    vals = Ts[:, iy, ix]
    best, vmax = vals.argmax(0), vals.max(0)
    ang = phi[iy, ix]
    if quant:
        ang = np.round(ang / (np.pi / quant)) * (np.pi / quant)
    half = dash * pitch / 2
    dx, dy = np.cos(ang) * half, np.sin(ang) * half
    out = [[] for _ in range(K)]
    for j, i in zip(*np.nonzero(vmax >= thr)):
        out[best[j, i]].append(np.array([[gx[j, i] - dx[j, i], gy[j, i] - dy[j, i]],
                                         [gx[j, i] + dx[j, i], gy[j, i] + dy[j, i]]]))
    return out


HATCH_ANGLES = (135, 45, 90, 0)   # per layer, repeating


def order_lines(lines, join_tol=0.75):
    """Greedy nearest-endpoint ordering (with reversal) + join touching ends."""
    if not lines:
        return []
    n = len(lines)
    ends = np.array([l[0] for l in lines] + [l[-1] for l in lines])
    tree = cKDTree(ends)
    used = np.zeros(n, bool)
    cur = np.zeros(2)
    out = []
    for _ in range(n):
        k = 16
        pick = None
        while pick is None:
            d, idx = tree.query(cur, k=min(k, 2 * n))
            for j in np.atleast_1d(idx):
                if not used[j % n]:
                    pick = j
                    break
            if k >= 2 * n and pick is None:
                break
            k *= 4
        li = pick % n
        used[li] = True
        l = lines[li] if pick < n else lines[li][::-1]
        if out and np.hypot(*(out[-1][-1] - l[0])) <= join_tol:
            out[-1] = np.vstack([out[-1], l[1:]])
        else:
            out.append(l)
        cur = l[-1]
    return out


def travel_stats(lines):
    draw = sum(_plen(l) for l in lines)
    up = sum(np.hypot(*(b[0] - a[-1])) for a, b in zip(lines[:-1], lines[1:]))
    return draw, up


# ----------------------------------------------------------------------------
# output
# ----------------------------------------------------------------------------
def write_svg(path, layers, pens, W, H, width_mm, pen_mm, paper=None):
    height_mm = width_mm * H / W
    sw = pen_mm * W / width_mm
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
           f'width="{width_mm:.2f}mm" height="{height_mm:.2f}mm" viewBox="0 0 {W} {H}">']
    if paper:
        out.append(f'<!-- paper {paper}: preview only, not plotted -->')
    for k, ((name, col), lines) in enumerate(zip(pens, layers), 1):
        out.append(f'<g inkscape:groupmode="layer" inkscape:label="{k} {name}" id="layer{k}" '
                   f'fill="none" stroke="{col}" stroke-width="{sw:.3f}" '
                   f'stroke-linecap="round" stroke-linejoin="round">')
        for l in lines:
            pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in l)
            out.append(f'<polyline points="{pts}"/>')
        out.append("</g>")
    out.append("</svg>")
    Path(path).write_text("\n".join(out))


def _coverage_mask(lines, W, H, scale, width_px, ss=3):
    im = Image.new("L", (int(W * scale * ss), int(H * scale * ss)), 0)
    dr = ImageDraw.Draw(im)
    w = max(1, int(round(width_px * ss)))
    f = scale * ss
    for l in lines:
        pts = [(float(x) * f, float(y) * f) for x, y in l]
        if len(pts) > 1:
            dr.line(pts, fill=255, width=w, joint="curve")
    im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0


def composite(alphas, pens, paper, opacity=0.9):
    """Ink-on-paper simulation: multiply on light paper, 'over' on dark paper."""
    paper_rgb = hex2rgb(paper)
    light = paper_rgb.mean() > 0.4
    out = np.ones(alphas[0].shape + (3,)) * paper_rgb
    for a, (_, col) in zip(alphas, pens):
        c = hex2rgb(col)
        a = (a * opacity)[..., None]
        if light:
            out = out * (1 - a * (1 - c))
        else:
            out = out * (1 - a) + c * a
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def render_preview(layers, pens, paper, W, H, width_mm, pen_mm, px_per_mm=6.0):
    scale = px_per_mm * width_mm / W
    alphas = [_coverage_mask(l, W, H, scale, pen_mm * px_per_mm) for l in layers]
    return Image.fromarray(composite(alphas, pens, paper))


def render_plate(Tn, pens, paper, gamma=0.8):
    alphas = [np.clip(t, 0, 1) ** gamma for t in Tn]
    return Image.fromarray(composite(alphas, pens, paper, opacity=0.95))


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def load_image(src):
    if src.startswith("sample:"):
        from skimage import data
        return getattr(data, src.split(":", 1)[1])()[..., :3] / 255.0
    im = io.imread(src)
    if np.issubdtype(im.dtype, np.integer):
        im = im.astype(float) / np.iinfo(im.dtype).max
    else:
        im = im.astype(float) / max(1.0, float(im.max()))
    if im.ndim == 2:
        im = np.stack([im] * 3, -1)
    if im.shape[-1] == 4:                      # flatten transparency onto white
        a = im[..., 3:4]
        im = im[..., :3] * a + (1 - a)
    return np.clip(im[..., :3], 0, 1)


STYLES = ("topo", "network", "fibers", "hatch", "marks")


def vectorize(sim, Tn, style, k, fiber_keep=1.0, fiber_steps=160, seed=0):
    if style == "topo":
        return contours(Tn[k])
    if style == "network":
        return weighted_network(Tn[k])
    rec = sim["paths"][k][-fiber_steps:]
    if fiber_keep < 1.0:
        n = rec.shape[1]
        keep = np.sort(np.random.default_rng(seed).choice(n, max(1, int(n * fiber_keep)), replace=False))
        rec = rec[:, keep]
    return agent_paths(rec, Tn[k])


def export(sim, pens, paper, out, styles=STYLES, width_mm=270.0, pen_mm=0.35, fiber_keep=1.0,
           hatch_mm=0.9, mark_mm=1.0, hatch_angles=HATCH_ANGLES, verbose=True):
    """Write <style>.svg + <style>_preview.png per style, plate.png and stats.json."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    Tn = norm_trail(sim["trail"])
    K, H, W = Tn.shape
    render_plate(Tn, pens, paper).save(out / "plate.png")
    try:                                   # keep stats for styles not re-exported this time
        stats = json.loads((out / "stats.json").read_text())
    except (OSError, ValueError):
        stats = {}
    mm = width_mm / W
    for style in styles:
        if style == "fibers" and "paths" not in sim:
            continue
        if style == "hatch":
            raw = [hatch_fill(Tn[k], hatch_angles[k % len(hatch_angles)], spacing=hatch_mm / mm,
                              min_len=1.2 / mm) for k in range(K)]
        elif style == "marks":
            raw = lattice_marks(Tn, mark_mm / mm)
            # the Nota Clausa frames its marks with a double contour; draw it in the darkest pen
            dark_k = int(np.argmin([hex2rgb(c) @ [0.2126, 0.7152, 0.0722] for _, c in pens]))
            Ts = gaussian(Tn.sum(0), 3.0)
            Ts /= np.percentile(Ts[Ts > 1e-3], 99)
            for lv in (0.10, 0.15):
                for c in measure.find_contours(Ts, lv):
                    if _plen(c) >= 20:
                        c = measure.approximate_polygon(_smooth(c, 5, bool(np.allclose(c[0], c[-1]))), 0.25)
                        raw[dark_k].append(c[:, ::-1].copy())
        else:
            raw = [vectorize(sim, Tn, style, k, fiber_keep) for k in range(K)]
        layers = [order_lines(L) for L in raw]
        pw = pen_mm * (0.8 if style == "fibers" else 1.0)
        write_svg(out / f"{style}.svg", layers, pens, W, H, width_mm, pw, paper)
        render_preview(layers, pens, paper, W, H, width_mm, pw).save(out / f"{style}_preview.png")
        stats[style] = {name: dict(lines=len(l), draw_m=round(travel_stats(l)[0] * mm / 1000, 1),
                                   pen_up_m=round(travel_stats(l)[1] * mm / 1000, 1))
                        for (name, _), l in zip(pens, layers)}
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    if verbose:
        print(json.dumps(stats, indent=1))
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="path, or sample:chelsea / sample:coffee ...")
    ap.add_argument("-o", "--out", default="out")
    ap.add_argument("--palette", default="cmyk",
                    help=f"preset {list(PRESETS)} or 'paper=#hex,name=#hex,name=#hex,...'")
    ap.add_argument("--grid", type=int, default=1350, help="simulation width in cells (~0.2 mm/cell at 270 mm)")
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--look", default="balanced", choices=list(LOOKS),
                    help="fidelity dial preset; sets --wfood --flow --so --edge")
    ap.add_argument("--station", type=float,
                    help="continuous dial instead of --look: 0 = faithful ... --station-max = feral")
    ap.add_argument("--station-max", type=float, default=6)
    ap.add_argument("--floor", default="",
                    help="accent pens, e.g. 'rust=0.3': ignore that pen's coverage below the floor and keep it local")
    ap.add_argument("--cultures", metavar="FAITHFUL:FERAL",
                    help="two competing cultures drawn in these two palette pens instead of one culture per "
                         "pen; --station (or --balance) sets the feral share")
    ap.add_argument("--balance", type=float, default=0.5, help="cultures: feral share of the agents")
    ap.add_argument("--territories", type=int, default=24,
                    help="cultures: start as this many held regions (0 = woven together)")
    ap.add_argument("--repel", type=float, help="cultures: repulsion between them (default 2, or 1 when woven)")
    ap.add_argument("--attract", type=float,
                    help="cultures: symbiosis instead of competition; they share cords (woven, no territories)")
    ap.add_argument("--home", default="", metavar="CX,CY,RX,RY;...",
                    help="cultures: ground the faithful culture always holds, as image fractions")
    ap.add_argument("--density", type=float, default=0.16, help="agents per fully-inked cell")
    ap.add_argument("--sa", type=float, default=22.5, help="sensor angle (deg)")
    ap.add_argument("--ra", type=float, default=45.0, help="rotation angle (deg)")
    ap.add_argument("--so", type=float, help="sensor offset (cells): network mesh size")
    ap.add_argument("--decay", type=float, default=0.1)
    ap.add_argument("--wfood", type=float,
                    help="image pull vs. self-trail: high = faithful, low = feral")
    ap.add_argument("--tone", type=float, default=0.6, help="tone share of the food map")
    ap.add_argument("--edge", type=float, help="edge share of the food map")
    ap.add_argument("--flow", type=float, help="steering along image contours")
    ap.add_argument("--styles", default=",".join(STYLES), help="comma list of topo, network, fibers, hatch (notae-style tone), marks (cipher-style dashes)")
    ap.add_argument("--hatch-mm", type=float, default=0.9, help="hatch line spacing")
    ap.add_argument("--mark-mm", type=float, default=1.0, help="lattice pitch for marks")
    ap.add_argument("--fiber-frac", type=float, default=0.03, help="share of agents traced for fibers")
    ap.add_argument("--width-mm", type=float, default=270.0)
    ap.add_argument("--pen-mm", type=float, default=0.35)
    a = ap.parse_args()
    look = station_look(a.station, a.station_max) if a.station is not None else LOOKS[a.look]
    for k, v in look.items():
        if getattr(a, k) is None:
            setattr(a, k, v)
    floors = {k: float(v) for k, v in (p.split("=") for p in a.floor.split(",") if "=" in p)}

    if a.palette in PRESETS:
        paper, pens = PRESETS[a.palette]
    else:
        kv = [p.split("=") for p in a.palette.split(",")]
        paper = dict(kv).get("paper", "#ffffff")
        pens = [(k, v) for k, v in kv if k != "paper"]
    styles = [s.strip() for s in a.styles.split(",") if s.strip()]

    img = load_image(a.image)
    if a.cultures:
        names = [n for n, _ in pens]
        fa_name, fe_name = a.cultures.split(":")
        missing = [n for n in (fa_name, fe_name) if n not in names]
        others = [n for n in names if n not in (fa_name, fe_name) and n not in floors]
        if missing or others:
            ap.error(f"--cultures: pens {missing} not in palette" if missing else
                     f"--cultures: pens {others} are neither a culture nor an accent (--floor)")
        looks = (LOOKS["faithful"], LOOKS["feral"])
        bal = (0.15 + 0.7 * min(max(a.station / a.station_max, 0), 1)) if a.station is not None else a.balance
        anchors = [tuple(float(v) for v in h.split(",")) for h in a.home.split(";") if h.strip()]
        fields = prepare_cultures(img, a.grid, pens, paper, looks, floors=floors, tone_w=a.tone,
                                  anchors=anchors or None)
        terr = 0 if a.attract is not None else a.territories
        repel = (-a.attract if a.attract is not None else
                 a.repel if a.repel is not None else (2.0 if terr else 1.0))
        sim = simulate_cultures(fields, looks, bal, territories=terr, repel=repel,
                                steps=a.steps, density=a.density, seed=a.seed,
                                record_last=160 if "fibers" in styles else 0, record_frac=a.fiber_frac)
        out_pens = [pens[names.index(fe_name)], pens[names.index(fa_name)]] + [p for p in pens if p[0] in floors]
        export(sim, out_pens, paper, a.out, styles, a.width_mm, a.pen_mm,
               hatch_mm=a.hatch_mm, mark_mm=a.mark_mm)
        return
    prep = prepare(img, a.grid, pens, paper, tone_w=a.tone, edge_w=a.edge, floors=floors)
    sim = simulate(prep, steps=a.steps, density=a.density, SA=a.sa, RA=a.ra, SO=a.so,
                   decay=a.decay, wfood=a.wfood, kflow=a.flow, seed=a.seed,
                   record_last=160 if "fibers" in styles else 0, record_frac=a.fiber_frac)
    export(sim, pens, paper, a.out, styles, a.width_mm, a.pen_mm, hatch_mm=a.hatch_mm, mark_mm=a.mark_mm)


if __name__ == "__main__":
    main()
