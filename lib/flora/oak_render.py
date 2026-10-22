"""A bur oak on its own page: an orthographic engraving with crown.py's marks.

For specimen sheets and tests. Inside a landscape the host's camera, model
and light draw the tree (see studies/infernal-landscape/plates.py); here a
small orthographic camera does the same with the repository's BVH ray kernel
(the Infernal Landscape study's `raycore`, loaded under the name that study
uses, as lib/farm_objects does) and a sun from the upper left.

    python -m lib.flora.oak_render --seed 371 --height 6.7 --out oak.svg
"""
from pathlib import Path
import importlib.util
import sys

import numpy as np

from . import crown as CR
from .oak import savanna_oak
from .render import Drawing, camera

PENS = {"crown row": .08, "crown outline": .10, "limb": .25, "scaffold": .16, "branch": .10, "bark": .085}


def _raycore():
    path = Path(__file__).resolve().parents[2] / "studies/infernal-landscape/vendor/raycore.py"
    rc = sys.modules.get("raycore")
    if rc is None or Path(getattr(rc, "__file__", "") or "").resolve() != path:
        spec = importlib.util.spec_from_file_location("raycore" if rc is None else "_flora_raycore", path)
        rc = importlib.util.module_from_spec(spec); sys.modules[spec.name] = rc; spec.loader.exec_module(rc)
    sys.modules.setdefault("_farm_raycore", rc)     # caches an older loader wrote
    return rc


def render_oak(oak, width=110., height=90., *, azimuth=20., elevation=6., px_per_mm=20., margin=6.,
               sun=(-10., -8., 9.), row_gap_mm=.34, seed=0):
    """An orthographic engraving of `oak` (a lib.flora.oak.Oak), as a Drawing in mm."""
    rc = _raycore()
    basis = camera(azimuth, elevation)            # rows: right, down (screen), toward the viewer
    right, down, toward = basis
    meshes = oak.meshes()
    tris, mats, mass_of = [], [], []
    mass_index = np.cumsum([part == "crown" for part, _, _ in meshes]) - 1
    for k, (part, v, faces) in enumerate(meshes):
        v = np.asarray(v, float)
        for f in faces:
            for j in range(1, len(f) - 1):
                tris.append(v[[f[0], f[j], f[j + 1]]]); mats.append(0 if part == "crown" else 1)
                mass_of.append(int(mass_index[k]) if part == "crown" else -1)
    V = np.vstack([np.asarray(v, float) for _, v, _ in meshes])
    q = V @ basis.T
    lo, hi = q[:, :2].min(0), q[:, :2].max(0)
    scale = min((width - 2 * margin) / max(hi[0] - lo[0], 1e-3), (height - 2 * margin) / max(hi[1] - lo[1], 1e-3))
    offset = np.array([width, height]) / 2 - (lo + hi) / 2 * scale
    g = 4 * max(hi - lo)                          # ground: catches the crown's shadow and hides the trunk's foot
    tris += [np.array([[-g, -g, 0], [g, -g, 0], [g, g, 0]]), np.array([[-g, -g, 0], [g, g, 0], [-g, g, 0]])]
    mats += [2, 2]; mass_of += [-1, -1]
    bvh = rc.build_bvh(np.array(tris), np.array(mats, np.int32))
    mass_leaf = np.asarray(mass_of)[bvh[8]]
    sun = np.asarray(sun, float) / np.linalg.norm(sun)
    far = float(np.abs(V).max()) * 4 + 50

    def to_world(xy_px):
        mm = np.asarray(xy_px, float) / px_per_mm
        m = (mm - offset) / scale
        return m[:, :1] * right + m[:, 1:] * down

    def to_page(P):                                # world points to page millimetres
        Q = np.asarray(P, float) @ basis.T
        return Q[:, :2] * scale + offset

    def light(P, N):
        N = np.where((N @ toward)[:, None] < 0, -N, N)
        _, hit = rc.first_hits(P + N * .01, np.tile(sun, (len(P), 1)), 1e3, *bvh[:6])
        return np.clip(.22 + .78 * np.clip(N @ sun, 0, 1) * (hit < 0), 0, 1)

    def visible(P):
        _, hit = rc.first_hits(P + toward * .004, np.tile(toward, (len(P), 1)), 1e3, *bvh[:6])
        return hit < 0

    # ---- foliage masses
    step = 2.
    xs = np.arange(0, width * px_per_mm, step); ys = np.arange(0, height * px_per_mm, step)
    gx, gy = np.meshgrid(xs, ys)
    base = to_world(np.column_stack([gx.ravel(), gy.ravel()]))
    O = base + toward * far
    dist, hit = rc.first_hits(O, np.tile(-toward, (len(O), 1)), 2 * far, *bvh[:6])
    ok = hit >= 0
    owner = np.full(len(O), CR.SKY); owner[ok] = np.where(mass_leaf[hit[ok]] >= 0, mass_leaf[hit[ok]], CR.OTHER)
    depth = np.where(ok, dist, np.inf); P = O - toward * np.where(ok, dist, 0)[:, None]
    tone = np.zeros(len(O)); m = owner >= 0
    if m.any():
        tone[m] = (1 - light(P[m], bvh[7][hit[m]])) * .92
    raster = CR.CrownRaster(owner.reshape(gx.shape), depth.reshape(gx.shape), P[:, 2].reshape(gx.shape),
                            tone.reshape(gx.shape), 0., 0., step, px_per_mm)
    rng = np.random.default_rng([int(oak.metadata.get("seed", 0)), int(seed)])
    drawn = CR.draw_masses(raster, rng, row_gap_mm / scale)
    paths = [("crown row", p / px_per_mm) for p in drawn["rows"]]
    paths += [("crown outline", p / px_per_mm) for p in drawn["outlines"]]

    # ---- limbs and bark
    eye = toward * 1e4
    for limb in oak.limbs:
        role = "limb" if limb.order == 0 else "scaffold" if limb.order == 1 else "branch"
        lines = (CR.limb_outline(limb.points, limb.radii, eye) if 2 * limb.radii.max() * scale > .3
                 else [limb.points])
        for line in lines:
            seen = visible(line) & (line[:, 2] > 0)
            for run in CR._runs(seen):
                paths.append((role, to_page(line[run])))
    furrows = oak.furrows()
    for f in furrows:
        facing = f.normals @ toward
        tone_f = np.where(facing > .03, (1 - light(f.points, f.normals)) * .95, 0)
        keep = (facing > .03) & CR.furrow_keep(f.k, f.count, tone_f, f.spacing * scale * np.clip(facing, 0, 1),
                                                PENS["bark"])
        keep &= f.points[:, 2] > 0
        if keep.any():
            keep &= visible(f.points)
        for run in CR._runs(keep):
            paths.append(("bark", to_page(f.points[run])))
    paths = [(r, p) for r, p in paths if len(p) > 1]
    d = Drawing(width, height, paths, dict(plant=oak.metadata, camera=dict(azimuth=azimuth, elevation=elevation,
                                                                           projection="orthographic"),
                                           scale_mm_per_metre=round(scale, 4), row_gap_mm=row_gap_mm,
                                           crown=drawn["stats"], visibility="BVH rays"), dict(PENS))
    d.metadata["plot"] = d.stats()
    return d


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Engrave one open-grown bur oak (lib/flora/oak.py).")
    ap.add_argument("--seed", type=int, default=371); ap.add_argument("--height", type=float, default=6.7)
    ap.add_argument("--spread", type=float); ap.add_argument("--stage", default="leafy", choices=("leafy", "bare"))
    ap.add_argument("--azimuth", type=float, default=20.); ap.add_argument("--elevation", type=float, default=6.)
    ap.add_argument("--detail", type=int, default=3, choices=(1, 2, 3))
    ap.add_argument("--out", type=Path, default=Path("bur_oak.svg"))
    a = ap.parse_args(argv)
    oak = savanna_oak(a.seed, a.height, spread=a.spread, stage=a.stage, detail=a.detail)
    d = render_oak(oak, azimuth=a.azimuth, elevation=a.elevation)
    a.out.write_text(d.svg()); d.png(a.out.with_suffix(".png"))
    print(a.out, d.stats())


if __name__ == "__main__":
    main()
