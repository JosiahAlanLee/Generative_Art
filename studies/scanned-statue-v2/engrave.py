#!/usr/bin/env python3
"""v2: CC0 museum scan -> object-space light -> plotter engraving.

Resolution is set by the printed plate size and the pen, not by scene units:
hatch candidates are spaced a fixed number of pen widths apart on the paper,
so a larger plate (or a finer pen) gets proportionally more lines.

Changes from v1, each addressing a measured loss of detail:
  * scan vertices are welded across UV seams, so surfaces and outlines connect;
  * outlines are interpolated contours (zero set of n.v on smoothed vertex
    normals), not zig-zag triangle edges, tested for visibility from a point
    lifted off the surface so grazing rays do not hide them;
  * light is computed on the scan's own vertices and on texture grids over the
    setting, then interpolated to each stroke sample. v1 read it back from a
    600x760 screen buffer through a 3x3 median filter;
  * hatch candidates default to 1.75 pen widths apart (v1: ~3.1), with a 64-step
    nested order (v1: 32), and tone is smoothed along each stroke before the
    on/off decision, which removes the stair-step dashes.
"""
import argparse, inspect, json, math, sys, time
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d, map_coordinates
import cairosvg
import scene, raycore, meshlines, suggestive
import engraving_core as e

ROOT = Path(__file__).resolve().parent
INK = '#29261f'
V1_PEN = .90                       # v1 hatch stroke, plate units
REL = dict(hatch0=1.0, hatch1=.80 / .90, set0=.80 / .90, set1=.70 / .90,
           contour=1.08 / .90, arch=1.05 / .90, structure=1.30 / .90)
FAMILIES = ([-.35, .12, 1.], [1., .16, .32])
sys.setrecursionlimit(20000)


def log(*a):
    print(*a, flush=True)


def rank_of(k, bits=6):
    n = 1 << bits
    return int(f'{k % n:0{bits}b}'[::-1], 2) / n + .5 / n


# --------------------------------------------------------------------- light
def setting_frames(setting_faces, cam):
    frames = []
    for f in setting_faces:
        p = f.p; u = p[1] - p[0]; u /= np.linalg.norm(u)
        n = np.cross(u, p[-1] - p[0]); n /= np.linalg.norm(n)
        if np.dot(n, cam.eye - p.mean(0)) < 0:
            n = -n
        v = np.cross(n, u)
        frames.append((p[0], u, v, n))
    return frames


def light_pass(mesh, setting_faces, bvh, cam, out, tex_step=.01):
    """Shade every scan vertex and a texture grid on every setting face.
    Cached in output/light-<key>.npz; the key covers geometry, camera, samples
    and the shading source."""
    vn = scene.vertex_normals(mesh)
    lights_hi = raycore.light_grid(scene.LIGHT, *scene.LIGHT_SIZE, 8)
    lights_lo = raycore.light_grid(scene.LIGHT, *scene.LIGHT_SIZE, 6)
    ao_hi, ao_lo = raycore.hemi_pattern(32), raycore.hemi_pattern(16)
    b_hi, b_lo = raycore.hemi_pattern(12), raycore.hemi_pattern(6)
    frames = setting_frames(setting_faces, cam)
    src = ''.join(inspect.getsource(fn.py_func) for fn in (raycore.trace, raycore.shade, raycore._direct))
    key = scene.digest(mesh.vertices, mesh.faces, cam.eye, lights_hi, ao_hi, b_hi,
                       *[f.p for f in setting_faces], extra=src + f'{tex_step}')[:16]
    path = out / f'light-{key}.npz'
    if path.exists():
        z = np.load(path)
        meta = z['tex_meta']
        tex = [(m[0], m[1], m[2], z[f'tex_{i}']) for i, m in enumerate(meta)]
        return z['vertex'], tex, vn
    log('Shading', len(mesh.vertices), 'scan vertices (64 light, 32 occlusion, 12 bounce samples)')
    t = time.time()
    vertex = raycore.shade(mesh.vertices, vn, lights_hi, scene.LIGHT, ao_hi, b_hi, *bvh[:3], *bvh[3:6], bvh[7])
    log('  vertex light seconds', round(time.time() - t, 1))
    tex = []; t = time.time(); total = 0
    for f, (o, u, v, n) in zip(setting_faces, frames):
        uv = np.stack([(f.p - o) @ u, (f.p - o) @ v], -1)
        u0, v0 = uv.min(0) - tex_step; u1, v1 = uv.max(0) + tex_step
        us = np.arange(u0, u1 + tex_step, tex_step); vs = np.arange(v0, v1 + tex_step, tex_step)
        gu, gv = np.meshgrid(us, vs, indexing='ij')
        P = o + gu.ravel()[:, None] * u + gv.ravel()[:, None] * v + n * .0015
        N = np.tile(n, (len(P), 1))
        s = raycore.shade(P, N, lights_lo, scene.LIGHT, ao_lo, b_lo, *bvh[:3], *bvh[3:6], bvh[7])[:, 0]
        tex.append((u0, v0, tex_step, s.reshape(gu.shape))); total += len(P)
    log('  setting texels', total, 'seconds', round(time.time() - t, 1))
    np.savez_compressed(path, vertex=vertex, key=key, tex_meta=np.array([t_[:3] for t_ in tex]),
                        **{f'tex_{i}': t_[3] for i, t_ in enumerate(tex)})
    return vertex, tex, vn


def tex_lookup(tex_entry, uv):
    u0, v0, h, grid = tex_entry
    return map_coordinates(grid, [(uv[:, 0] - u0) / h, (uv[:, 1] - v0) / h], order=1, mode='nearest')


# ------------------------------------------------------------------ strokes
def statue_strokes(mesh, vn, vlight, step, sample, pen):
    V, F = mesh.vertices, mesh.faces; NV = len(V)
    out = []
    for family, normal in enumerate(FAMILIES):
        normal = np.asarray(normal, float); normal /= np.linalg.norm(normal)
        dots = V @ normal; fd = dots[F]; fmin = fd.min(1); fmax = fd.max(1)
        order = np.argsort(fmin); fmin_sorted = fmin[order]
        offsets = np.arange(math.floor(dots.min() / step) * step, dots.max(), step)
        width = pen * (REL['hatch0'] if family == 0 else REL['hatch1'])
        for k, off in enumerate(offsets):
            idx = order[:np.searchsorted(fmin_sorted, off, 'right')]
            idx = idx[fmax[idx] >= off]
            if len(idx) == 0:
                continue
            res = meshlines.level_set(F[idx], dots - off, NV)
            if res is None:
                continue
            ea, eb, t, chains = res
            P = V[ea] + t[:, None] * (V[eb] - V[ea])
            N = vn[ea] + t[:, None] * (vn[eb] - vn[ea])
            S = vlight[ea] + t * (vlight[eb] - vlight[ea])
            for c in chains:
                if len(c) < 2:
                    continue
                r = meshlines.resample(P[c], [N[c], S[c]], sample)
                if r is None:
                    continue
                q, (nn, ss) = r
                if np.linalg.norm(np.diff(q, axis=0), axis=1).sum() < 1.5 * step:
                    continue
                nn /= np.maximum(np.linalg.norm(nn, axis=1)[:, None], 1e-12)
                out.append(dict(p=q, n=nn, light=ss, width=width, family=family, rank=rank_of(k),
                                normal=normal, step=step, kind='scan hatch'))
        log('  section family', family, 'planes', len(offsets), 'curves so far', len(out))
    return out


def setting_strokes(setting_faces, lines, frames, tex, step, sample, pen):
    """v1's setting hatch (two families per planar face, same retention rule)."""
    out = []
    for fi, (f, (o, u, v, n)) in enumerate(zip(setting_faces, frames)):
        if f.mat != 0:
            continue
        uv = np.stack([(f.p - o) @ u, (f.p - o) @ v], -1)
        for family, angle in enumerate((.65, -.68)):
            direction = np.array([np.cos(angle), np.sin(angle)]); perp = np.array([-direction[1], direction[0]])
            values = uv @ perp
            width = pen * (REL['set0'] if family == 0 else REL['set1'])
            for k, off in enumerate(np.arange(values.min() + .003, values.max(), step)):
                hits = []
                for a, b, va, vb in zip(uv, np.roll(uv, -1, axis=0), values, np.roll(values, -1)):
                    if (va <= off < vb) or (vb <= off < va):
                        hits.append(a + (b - a) * (off - va) / (vb - va))
                if len(hits) < 2:
                    continue
                hits = sorted(hits, key=lambda q: q @ direction); a, b = hits[0], hits[-1]
                length = np.linalg.norm(b - a)
                if length < 1.5 * step:
                    continue
                t = np.linspace(0, 1, max(3, int(np.ceil(length / sample)) + 1))
                q2 = a + (b - a) * t[:, None]
                q = o + q2[:, 0, None] * u + q2[:, 1, None] * v + n * .0015
                out.append(dict(p=q, n=np.tile(n, (len(q), 1)), light=tex_lookup(tex[fi], q2), width=width,
                                family=family, rank=rank_of(k), normal=perp[0] * u + perp[1] * v,
                                step=step, kind='setting hatch'))
    for p, w, kind in lines:
        pieces = []
        for a, b in zip(p, p[1:]):
            L = np.linalg.norm(b - a)
            pieces.extend(a + np.linspace(0, 1, max(2, int(L / sample) + 1))[:, None] * (b - a))
        out.append(dict(p=np.asarray(pieces), width=pen * w / V1_PEN, family=0, kind=kind))
    return out


def contour_strokes(mesh, cam, sample, pen, smooth):
    V = mesh.vertices
    vn = scene.vertex_normals(mesh, smooth=smooth)
    view = cam.eye - V; view /= np.linalg.norm(view, axis=1)[:, None]
    g = (vn * view).sum(1)
    ea, eb, t, chains = meshlines.level_set(mesh.faces, g, len(V))
    P = V[ea] + t[:, None] * (V[eb] - V[ea])
    N = vn[ea] + t[:, None] * (vn[eb] - vn[ea]); N /= np.linalg.norm(N, axis=1)[:, None]
    out = []
    for c in chains:
        r = meshlines.resample(P[c], [N[c]], sample)
        if r is None:
            continue
        out.append(dict(p=r[0], n=r[1][0], width=pen * REL['contour'], family=0, kind='scan contour'))
    log('  contours', len(out), 'chains from', len(P), 'edge crossings')
    return out


def suggestive_strokes(mesh, cam, sample, pen, smooth, threshold):
    vn = scene.vertex_normals(mesh, smooth=smooth)
    chains, info = suggestive.suggestive_contours(mesh, cam.eye, vn, threshold)
    out = []
    for P, N, ok, strength in chains:
        if len(P) < 2:
            continue
        r = meshlines.resample(P, [N, ok], sample)
        if r is None:
            continue
        out.append(dict(p=r[0], n=r[1][0], ok=r[1][1] > .5, width=pen * REL['hatch0'], family=0,
                        kind='scan suggestive'))
    log('  suggestive contour chains', len(out))
    return out


def projected_spacing(cam, p, n, normal, step):
    """v1's exact perspective Jacobian: screen distance between adjacent sections."""
    jx, jy = cam.jacobian(p)
    grad = normal[None, :] - n * (n @ normal)[:, None]; g = np.linalg.norm(grad, axis=1)
    across = grad / np.maximum(g[:, None], 1e-8); tangent = np.cross(n, across)
    tx = (jx * tangent).sum(1); ty = (jy * tangent).sum(1)
    ax = (jx * across).sum(1); ay = (jy * across).sum(1)
    return step / np.maximum(g, 1e-8) * np.abs(tx * ay - ty * ax) / np.maximum(np.hypot(tx, ty), 1e-8)


# ------------------------------------------------------------------ render
def runs(mask):
    ch = np.diff(np.r_[0, mask.astype(np.int8), 0])
    return np.flatnonzero(ch == 1), np.flatnonzero(ch == -1)


def clean(keep, xy, gap_px, min_px):
    """Close gaps shorter than gap_px between kept runs; drop runs shorter than min_px."""
    keep = keep.copy()
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
    a, b = runs(keep)
    for i in range(len(a) - 1):
        if seg[a[i + 1]] - seg[b[i] - 1] <= gap_px:
            keep[b[i]:a[i + 1]] = True
    a, b = runs(keep)
    for s, t in zip(a, b):
        if seg[t - 1] - seg[s] < min_px:
            keep[s:t] = False
    return keep


def visibility(cands, cam, bvh):
    pts = np.concatenate([c['p'] for c in cands]); lift = np.zeros_like(pts)
    start = 0
    for c in cands:
        k = len(c['p']); sl = slice(start, start + k); start += k
        to_eye = cam.eye - c['p']; to_eye /= np.linalg.norm(to_eye, axis=1)[:, None]
        if c['kind'] in ('scan hatch', 'scan suggestive'):
            n = c['n'] * np.sign((c['n'] * to_eye).sum(1))[:, None]
            lift[sl] = n * .0015
        elif c['kind'] == 'scan contour':
            lift[sl] = c['n'] * .003
        else:
            lift[sl] = to_eye * .0015
    log('  visibility rays', len(pts))
    vis = raycore.visible_from(pts, lift, cam.eye, *bvh[:3], *bvh[3:6])
    pp = cam.project(pts)
    vis &= (pp[:, 2] > .1) & (pp[:, 0] > 3) & (pp[:, 0] < cam.w - 3) & (pp[:, 1] > 3) & (pp[:, 1] < cam.h - 3)
    return vis, pp


def draw(cands, vis, pp, cam, pen, treatment, tone):
    groups = dict(contours=[], features=[], hatch_primary=[], hatch_cross=[], setting=[])
    stats = dict(paths=0, length_units=0.)
    start = 0
    for c in cands:
        k = len(c['p']); sl = slice(start, start + k); start += k
        xy = pp[sl, :2]; keep = vis[sl].copy(); kind = c['kind']
        if kind in ('scan hatch', 'setting hatch'):
            if treatment == 'contour' and c['family'] == 1 and kind == 'scan hatch':
                continue
            d = 1 - np.sqrt(np.clip(c['light'], 0, 1))
            spacing = projected_spacing(cam, c['p'], c['n'], c['normal'], c['step'])
            desired = tone['scale'] * np.power(d, tone['gamma'])
            split = .30 * np.clip((d - .38) / .28, 0, 1) if treatment == 'cross' else np.zeros(k)
            coverage = desired * (1 - split if c['family'] == 0 else split)
            prob = np.clip(coverage * spacing / c['width'], 0, 1)
            if k > 4:
                prob = gaussian_filter1d(prob, tone['smooth_samples'], mode='nearest')
            keep &= prob > c['rank']
            keep = clean(keep, xy, .8 * pen, 2.5 * pen)
            group = 'setting' if kind == 'setting hatch' else ('hatch_primary' if c['family'] == 0 else 'hatch_cross')
        elif kind == 'scan contour':
            keep = clean(keep, xy, 2.0 * pen, 4.0 * pen)
            group = 'contours'
        elif kind == 'scan suggestive':
            keep = clean(keep & c['ok'], xy, 1.5 * pen, 6.0 * pen)
            group = 'features'
        else:
            keep = clean(keep, xy, .5 * pen, 1.5 * pen)
            group = 'setting'
        for a, b in zip(*runs(keep)):
            if b - a < 2:
                continue
            seg_xy = xy[a:b]
            if kind in ('scan contour', 'scan suggestive') and b - a > 4:
                # Scan noise shows as sub-pixel wobble on feature lines; ease it out.
                seg_xy = gaussian_filter1d(seg_xy, 1.0, axis=0, mode='nearest')
            q = np.asarray(e.rdp(seg_xy, .2 * pen))
            ln = np.linalg.norm(np.diff(q, axis=0), axis=1).sum()
            if ln < 2 * pen:
                continue
            groups[group].append('<path d="M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in q)
                                 + f'" stroke-width="{c["width"]:.3f}"/>')
            stats['paths'] += 1; stats['length_units'] += ln
    return groups, stats


LAYERS = (('setting', '1 setting'), ('hatch_primary', '2 hatch'), ('hatch_cross', '3 cross-hatch'),
          ('features', '4 fold lines'), ('contours', '5 outlines'))


def write_svg(path, groups, plate_mm, title):
    """One Inkscape/AxiDraw layer per stroke class, all in the same ink, outlines drawn last."""
    w, h = scene.W, scene.H
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{plate_mm:.2f}mm" height="{plate_mm * h / w:.2f}mm" viewBox="0 0 {w} {h}">'
             f'<title>{title}</title><rect width="100%" height="100%" fill="white"/>']
    for key, label in LAYERS:
        if groups[key]:
            parts.append(f'<g id="{key.replace("_", "-")}" inkscape:groupmode="layer" inkscape:label="{label}" '
                         f'fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">'
                         + ''.join(groups[key]) + '</g>')
    parts.append('</svg>')
    svg = ''.join(parts)
    path.write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(path.with_suffix('.png')), output_width=w, output_height=h)


def render_light(mesh, setting_faces, frames, bvh, owner, cam, vlight, tex, ss=2):
    """Plate-resolution light image (2x2 supersampled) and visible-statue mask."""
    W, H = cam.w, cam.h
    img = np.zeros((H * ss, W * ss)); statue = np.zeros((H * ss, W * ss), bool)
    owner_bvh = owner[bvh[8]]
    V, F = mesh.vertices, mesh.faces
    for r0 in range(0, H * ss, 128):
        rows = np.arange(r0, min(H * ss, r0 + 128))
        gx, gy = np.meshgrid((np.arange(W * ss) + .5) / ss, (rows + .5) / ss)
        d = cam.rays(gx.ravel(), gy.ravel())
        T, Hh = raycore.first_hits(np.tile(cam.eye, (len(d), 1)), d, 100., *bvh[:3], *bvh[3:6])
        val = np.ones(len(d)); hit = Hh >= 0
        p = cam.eye + d * T[:, None]
        own = np.where(hit, owner_bvh[np.maximum(Hh, 0)], 0)
        sm = hit & (own >= 0)
        if sm.any():
            tri = V[F[own[sm]]]; q = p[sm]
            v0 = tri[:, 1] - tri[:, 0]; v1 = tri[:, 2] - tri[:, 0]; v2 = q - tri[:, 0]
            d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
            d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1); den = d00 * d11 - d01 * d01
            b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den; b0 = 1 - b1 - b2
            L = vlight[F[own[sm]]]
            val[sm] = b0 * L[:, 0] + b1 * L[:, 1] + b2 * L[:, 2]
        st = hit & (own < 0)
        for fi in np.unique(-own[st] - 1):
            m = st & (own == -(fi + 1)); o, u, v, n = frames[fi]
            q2 = np.stack([(p[m] - o) @ u, (p[m] - o) @ v], -1)
            val[m] = tex_lookup(tex[fi], q2)
        img[rows] = val.reshape(len(rows), W * ss); statue[rows] = sm.reshape(len(rows), W * ss)
    shade = np.sqrt(np.clip(img, 0, 1))
    shade = shade.reshape(H, ss, W, ss).mean((1, 3)); mask = statue.reshape(H, ss, W, ss).mean((1, 3))
    return shade, mask


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--camera', choices=sorted(scene.CAMERAS), default='front')
    ap.add_argument('--plate-mm', type=float, default=148., help='printed width of the plate (v1 proof: 148)')
    ap.add_argument('--pen-mm', type=float, default=.09, help='pen line width (v1 strokes were ~0.089 mm at 148 mm)')
    ap.add_argument('--spacing', type=float, default=1.75, help='closest hatch spacing, in pen widths (v1: ~3.1)')
    ap.add_argument('--contour-smooth', type=int, default=0, help='1-ring normal smoothing passes for contours')
    ap.add_argument('--suggestive-smooth', type=int, default=2, help='normal smoothing passes for curvature')
    ap.add_argument('--suggestive-threshold', type=float, default=5., help='minimum fold strength (x1e-3)')
    ap.add_argument('--no-suggestive', action='store_true', help='omit the suggestive-contour layer')
    ap.add_argument('--tone-scale', type=float, default=.68); ap.add_argument('--tone-gamma', type=float, default=1.30)
    ap.add_argument('--prefix', default=None, help='output name prefix (default: camera name)')
    ap.add_argument('--out', default=str(ROOT / 'output'))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    prefix = a.prefix or a.camera
    units_per_mm = scene.W / a.plate_mm
    pen = a.pen_mm * units_per_mm
    cam = scene.Camera(scene.CAMERAS[a.camera])
    px_per_world = cam.px_per_unit(scene.TARGET)
    step = a.spacing * pen / px_per_world
    sample = max(.7 * step, .9 / px_per_world)  # along-stroke sample spacing, world units
    log(f'plate {a.plate_mm} mm, pen {a.pen_mm} mm = {pen:.3f} units; candidate spacing '
        f'{a.spacing * pen:.2f} units ({a.spacing * a.pen_mm:.3f} mm) = {step:.5f} scene units')
    t0 = time.time()
    mesh, scale, raw_vertices = scene.load_scan()
    setting_faces, lines = scene.build_setting()
    tris, mats, owner = scene.scene_triangles(mesh, setting_faces)
    bvh = raycore.build_bvh(tris, mats)
    frames = setting_frames(setting_faces, cam)
    vertex, tex, vn = light_pass(mesh, setting_faces, bvh, cam, out)
    vlight = vertex[:, 0]
    log('Building strokes')
    cands = statue_strokes(mesh, vn, vlight, step, sample, pen)
    cands += setting_strokes(setting_faces, lines, frames, tex, step, sample, pen)
    cands += contour_strokes(mesh, cam, sample, pen, a.contour_smooth)
    if not a.no_suggestive:
        cands += suggestive_strokes(mesh, cam, sample, pen, a.suggestive_smooth, a.suggestive_threshold)
    vis, pp = visibility(cands, cam, bvh)
    tone = dict(scale=a.tone_scale, gamma=a.tone_gamma, smooth_samples=1.5)
    report = dict(version='scan-engraving-v2', camera=a.camera, eye=cam.eye.tolist(), plate_mm=a.plate_mm,
                  pen_mm=a.pen_mm, pen_units=pen, spacing_pen_widths=a.spacing,
                  candidate_spacing_mm=a.spacing * a.pen_mm, section_step_scene_units=step,
                  sample_step_scene_units=sample, source_triangles=len(mesh.faces),
                  glb_vertex_records=raw_vertices, welded_vertices=len(mesh.vertices),
                  contour_normal_smoothing=a.contour_smooth,
                  suggestive=None if a.no_suggestive else dict(normal_smoothing=a.suggestive_smooth,
                                                               threshold=a.suggestive_threshold, max_cos=.94),
                  tone=tone, light=dict(
                      vertex_light_samples=64, vertex_ao=32, vertex_bounce=12, setting_texel=.01,
                      setting_light_samples=36, setting_ao=16, setting_bounce=6, ambient=.10, exposure=1.6),
                  treatments=[])
    for treatment in ('contour', 'cross'):
        groups, stats = draw(cands, vis, pp, cam, pen, treatment, tone)
        name = f'{prefix}-{treatment}'
        write_svg(out / f'{name}.svg', groups, a.plate_mm,
                  'The Greek Slave - scanned geometry, ray-lit engraving (v2)')
        stats.update(treatment=treatment, file=f'{name}.svg', line_metres=stats.pop('length_units') / units_per_mm / 1000,
                     paths_by_layer={k: len(v) for k, v in groups.items()})
        report['treatments'].append(stats); log(stats)
    shade, mask = render_light(mesh, setting_faces, frames, bvh, owner, cam, vlight, tex)
    Image.fromarray(np.uint8(np.clip(shade, 0, 1) * 255)).save(out / f'{prefix}-light.png')
    Image.fromarray(np.uint8(mask > .5) * 255).save(out / f'{prefix}-statue-mask.png')
    Image.fromarray(np.uint8(np.where(mask > .5, shade, 1.) * 255)).save(out / f'{prefix}-statue-food.png')
    # No timings in the report, so a rebuild reproduces it byte for byte.
    (out / f'{prefix}-report.json').write_text(json.dumps(report, indent=2))
    log('Finished in', round(time.time() - t0, 1), 's')


if __name__ == '__main__':
    main()
