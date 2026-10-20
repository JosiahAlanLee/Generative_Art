"""'Who holds the shade': a screen map of the traced light and the strains' ground."""
import numpy as np
from PIL import Image, ImageDraw

PAPER = np.array([237, 230, 212]) / 255
COL = dict(lit=np.array([252, 249, 240]) / 255, shade=np.array([168, 162, 150]) / 255,
           A=np.array([196, 150, 64]) / 255, A_taken=np.array([150, 62, 36]) / 255,
           B=np.array([84, 110, 128]) / 255, B_taken=np.array([30, 52, 96]) / 255)


def who_holds_the_shade(surfaces, results, cam, visible_fn, sites_a, sites_b, path, lift=0.003, scale=2,
                        lines_png=None):
    W, H = cam.W // scale, cam.H // scale
    img = np.tile(PAPER, (H, W, 1))
    depth = np.full((H, W), np.inf)
    for s in surfaces:
        r = results[s.name]
        uu, vv = s.centers(1)
        P = s.world(uu, vv)
        dom = r['domain']
        sx, sy, z = cam.project(P)
        ok = dom & cam.inside(sx, sy, z)
        idx = np.flatnonzero(ok.ravel())
        if not len(idx):
            continue
        N = s.normal(uu, vv).reshape(-1, 3)[idx]
        vis = visible_fn(np.ascontiguousarray(P.reshape(-1, 3)[idx] + N * lift))
        idx = idx[vis]
        eu, ev = s.frame(uu.ravel()[idx], vv.ravel()[idx])
        J = cam.jacobian(P.reshape(-1, 3)[idx], eu, ev)
        px = np.sqrt(np.abs(J[:, 0, 0] * J[:, 1, 1] - J[:, 0, 1] * J[:, 1, 0])) * s.cell / scale
        ex = r['excess'].ravel()[idx]
        tot = (r['trail_a'] + r['trail_b']).ravel()[idx]
        occ = tot > 0.05 * max(1e-9, np.percentile((r['trail_a'] + r['trail_b'])[dom], 99.5))
        held_a = r['held'].ravel()[idx] > 0.5
        seed_a = r['a_ground'].ravel()[idx]
        col = np.where((ex > 0.5)[:, None], COL['lit'], COL['shade'])
        col = np.where((occ & held_a & seed_a)[:, None], COL['A'], col)
        col = np.where((occ & held_a & ~seed_a)[:, None], COL['A_taken'], col)
        col = np.where((occ & ~held_a & ~seed_a)[:, None], COL['B'], col)
        col = np.where((occ & ~held_a & seed_a)[:, None], COL['B_taken'], col)
        x = (sx.ravel()[idx] / scale).astype(int)
        y = (sy.ravel()[idx] / scale).astype(int)
        zz = z.ravel()[idx]
        k = np.clip(np.ceil(px).astype(int), 1, 8)
        for dx in range(8):
            for dy in range(8):
                m = (dx < k) & (dy < k)
                xx, yy = np.clip(x[m] + dx, 0, W - 1), np.clip(y[m] + dy, 0, H - 1)
                order = np.argsort(-zz[m])                       # far first, near last
                xx, yy, cz, cc = xx[order], yy[order], zz[m][order], col[m][order]
                nearer = cz <= depth[yy, xx] + 1e-6
                img[yy[nearer], xx[nearer]] = cc[nearer]
                depth[yy[nearer], xx[nearer]] = np.minimum(depth[yy[nearer], xx[nearer]], cz[nearer])
    if lines_png is not None:                                   # the plate's structure, for orientation
        g = np.asarray(Image.open(lines_png).convert('L').resize((W, H), Image.LANCZOS), float) / 255
        img = img * (0.25 + 0.75 * g)[..., None]
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    dr = ImageDraw.Draw(im)
    for sites, c in ((sites_a, (150, 62, 36)), (sites_b, (30, 52, 96))):
        for _, p, _ in sites:
            x, y, z = cam.project(np.array(p, float)[None])
            x, y = float(x[0]) / scale, float(y[0]) / scale
            if z[0] > 0 and 0 < x < W and 0 < y < H:
                dr.ellipse([x - 8, y - 8, x + 8, y + 8], outline=c, width=3)
    im.save(path)
    return path


def scene_totals(results):
    """Scene-wide share of the trail on lit ground and of occupied ground that changed strain."""
    from scipy.ndimage import gaussian_filter
    lit_t = tot_t = moved = occupied = 0.0
    for r in results.values():
        tot = r['trail_a'] + r['trail_b']
        lit_t += tot[r['excess'] > 0.5].sum()
        tot_t += tot.sum()
        occ = gaussian_filter(tot, 4) > 0.02
        dom = r['domain']
        moved += (((r['held'] > 0.5) != r['a_ground']) & dom & occ).sum()
        occupied += (dom & occ).sum()
    return dict(trail_on_lit_ground=float(lit_t / max(tot_t, 1e-9)), changed_strain=float(moved / max(occupied, 1)))
