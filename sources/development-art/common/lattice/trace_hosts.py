"""Trace body silhouettes from the raster demon references, as hosts for the node lattice.

Each mask keeps the body (robe, limbs, hood, held objects) and drops the thin structures the
generator regrows itself: drip lines, beaded chains, terminal dots. A local ink-density
threshold does the separation: the lattice covers about half of any window it fills, a drip
or a bead a few percent. Output is hosts.json beside this script: one run-length mask per
figure on a 250 x 375 grid (4 page units per cell on the 1000 x 1500 page), with the source
path, its sha256, and the method and library versions.

    python common/lattice/trace_hosts.py [--preview sheet.png]
"""
import base64
import hashlib
import json

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))

GW, GH = 250, 375

SOURCES = [
    # key, label, office, path, crop box in source px (None = whole), opening radius px
    ("choronzon", "Choronzon", "The Dispersal (Tarot extra)", "books/06_tarot/extras/choronzon/choronzon-the-dispersal-v02.png", (52, 128, 972, 1338), 7),
    ("vassago", "Vassago", "Tier 2 Escalation Lead", "references/raster/batch-01/vassago-raster-reference-v01.png", None, 7),
    ("paimon", "Paimon", "VP of Operations", "references/raster/batch-01/paimon-raster-reference-v01.png", None, 7),
    ("orobas", "Orobas", "Deputy Department Head", "references/raster/batch-01/orobas-raster-reference-v01.png", None, 7),
    ("repetiel", "Repetiel", "Escalation Intake Coordinator", "references/raster/batch-01/repetiel-raster-reference-v01.png", None, 7),
    ("bael", "Bael", "Chief Technology Officer", "references/raster/batch-01/bael-raster-reference-v03.png", None, 6),
    ("choraz", "Choraz", "Major Incident Manager", "references/raster/batch-03/choraz-raster-reference-v02.png", None, 6),
    ("probator", "Probator", "Director of Technical Assurance", "references/raster/batch-03/probator-raster-reference-v03.png", None, 7),
    ("decision", "Decision demon", "Graduum VIII", "references/raster/batch-06/decision-demon-raster-reference-v01.png", None, 7),
    ("tiers", "Shouting tiers", "Graduum VIII", "references/raster/batch-06/shouting-tiers-raster-reference-v01.png", None, 6),
    ("foras", "Foras", "Tarot calibration figure", "books/06_tarot/major-arcana/art/foras-raster-reference-v02.png", None, 7),
]


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def trace(path, crop, open_r):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    H, W, _ = im.shape
    border = np.concatenate([im[:12].reshape(-1, 3), im[-12:].reshape(-1, 3), im[:, :12].reshape(-1, 3), im[:, -12:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    diff = np.sqrt(((im - bg) ** 2).sum(-1))
    lum = im.mean(-1)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    red = (r > 120) & (r - g > 55) & (r - b > 55)          # the red marks are the book's own, not body
    fg = (diff > 34) & ~red
    if crop:
        x0, y0, x1, y1 = crop
        m = np.zeros_like(fg)
        m[y0:y1, x0:x1] = True
        fg &= m
    # local ink density: the lattice covers half its area, a drip line or a bead covers
    # a few percent of a window, so a density threshold keeps the body and drops the rest
    dens = ndi.gaussian_filter(fg.astype(np.float32), 5.5)
    body = dens > 0.27
    body = ndi.binary_closing(body, structure=disk(4))
    body = ndi.binary_fill_holes(body)
    body = ndi.binary_opening(body, structure=disk(open_r))
    lab, n = ndi.label(body)
    if n:
        sizes = ndi.sum(body, lab, range(1, n + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s > max(2500, 0.02 * sizes.max())]
        body = np.isin(lab, keep)
    body = ndi.binary_fill_holes(body)
    # resample to the host grid: page units are px * 1000/1024, grid cell = 4 units
    small = Image.fromarray((body * 255).astype(np.uint8)).resize((GW, GH), Image.BILINEAR)
    grid = np.asarray(small) > 127
    return grid, body, lum


def rle(grid):
    out = bytearray()
    for row in grid:
        runs, cur, n = [], False, 0
        for v in row:
            if v == cur:
                n += 1
            else:
                runs.append(n)
                cur, n = v, 1
        runs.append(n)
        # split runs longer than 255 (cannot happen at width 250, kept for safety)
        out.append(len(runs))
        for k in runs:
            out.append(k)
    return base64.b64encode(bytes(out)).decode()


METHOD = {
    "background": "median colour of a 12 px border",
    "foreground": "colour distance from the background > 34, excluding red marks (r > 120, r - g > 55, r - b > 55)",
    "density": "gaussian sigma 5.5 px, threshold 0.27",
    "cleanup": "closing radius 4 px, fill holes, opening radius per host (opening_px), drop parts under 2 % of the largest",
    "resample": "bilinear to 250 x 375, threshold 0.5",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..")))
    ap.add_argument("--out", default=os.path.join(HERE, "hosts.json"))
    ap.add_argument("--preview", help="write a contact sheet of the masks over their renders")
    args = ap.parse_args()
    REPO, OUT, PREVIEW = args.repo, args.out, args.preview
    import scipy
    import PIL
    hosts = []
    previews = []
    for key, label, office, rel, crop, open_r in SOURCES:
        p = f"{REPO}/{rel}"
        sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
        grid, body, lum = trace(p, crop, open_r)
        hosts.append({"key": key, "label": label, "office": office, "source": rel, "sha256": sha,
                      "crop_px": list(crop) if crop else None, "opening_px": open_r,
                      "w": GW, "h": GH, "rle": rle(grid), "area": round(float(grid.mean()), 6)})
        print(f"{key:10s} area {grid.mean():.3f}  rle {len(hosts[-1]['rle'])} chars")
        if PREVIEW:
            base = Image.open(p).convert("RGB").resize((256, 384))
            ov = np.asarray(base).astype(np.float32)
            m = np.asarray(Image.fromarray(grid.astype(np.uint8) * 255).resize((256, 384), Image.NEAREST)) > 0
            ov[m] = ov[m] * 0.45 + np.array([200, 40, 40]) * 0.55
            previews.append(Image.fromarray(ov.astype(np.uint8)))
    record = {"grid": [GW, GH], "unit_per_cell": 4, "method": METHOD,
              "made_with": {"numpy": np.__version__, "scipy": scipy.__version__, "pillow": PIL.__version__},
              "hosts": hosts}
    with open(OUT, "w") as f:
        json.dump(record, f, indent=1)
        f.write("\n")
    if PREVIEW:
        cols = 6
        rows = (len(previews) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 256, rows * 384), (237, 230, 212))
        for i, im in enumerate(previews):
            sheet.paste(im, ((i % cols) * 256, (i // cols) * 384))
        sheet.save(PREVIEW)


if __name__ == "__main__":
    main()
