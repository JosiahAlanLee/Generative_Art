"""The photophobic mould, shared by every scene.

One species, two strains. Both live in the dark: the traced light is terrain they
avoid (Physarum plasmodia are photophobic; Tero et al. 2010 used illumination to
stand in for mountains and lakes). The strains start from authored inoculation
sites, three or so each, meet in the shadow and contest the ground between them.
They are drawn as white line: paper reserved around an ochre vein, cut out of the
scene's own hatching (the plasmodium of P. polycephalum is yellow).

A scene supplies: its surfaces (common.atlas), the traced light on each surface
('darkness' and 'excess', the light over the ambient floor, 0..1), a camera, a
visibility test, and its base ink as labelled screen polylines.
"""
from __future__ import annotations

import math

import numpy as np
from numba import njit
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, map_coordinates, median_filter, zoom

import physarum_plot as pp

LOOK_A = dict(wfood=6.0, flow=0.15, so=8.0, edge=1.0)       # fine mesh
LOOK_B = dict(wfood=4.0, flow=0.10, so=11.0, edge=1.0)      # coarser mesh, same species
PARAMS = dict(repel=0.8, mark=0.5, steps=900, density=0.12, held_sigma=8.0, avg_last=150)
LAMBDA = 1.5                     # the light's repellent weight, in food units
PENS = {'ink': '#29261f', 'strain A': '#b8892c', 'strain B': '#a0761f'}
COLONY_WEIGHT = 0.7
HALO_PX = 4.0


# ----------------------------------------------------------------------------
# light on a surface
# ----------------------------------------------------------------------------
def surface_light(s, light_fn, step=2):
    """Evaluate a scene's light model at the surface's cell centres (every `step`
    cells), median-filter, and upsample. light_fn(P, N, albedo) -> dict of (n,) arrays
    including 'darkness' and 'excess'."""
    uu, vv = s.centers(step)
    P = s.world(uu, vv)
    N = s.normal(uu, vv)
    ch = light_fn(np.ascontiguousarray(P.reshape(-1, 3)), np.ascontiguousarray(N.reshape(-1, 3)),
                  s.material_albedo)
    out = {}
    for name, a in ch.items():
        a = median_filter(a.reshape(uu.shape), size=3)
        big = zoom(a, step, order=1)[:s.nv, :s.nu]
        if big.shape != (s.nv, s.nu):
            big = np.pad(big, ((0, s.nv - big.shape[0]), (0, s.nu - big.shape[1])), mode='edge')
        out[name] = big.astype(np.float32)
    return out


def excess_from(direct, bounce, albedo, exposure=2.4, norm=0.3):
    """The doorway/window/sun light over the ambient floor, 0..1."""
    return np.clip((direct + 0.7 * bounce) * albedo * exposure / norm, 0, 1)


# ----------------------------------------------------------------------------
# where the strains start and reach
# ----------------------------------------------------------------------------
def noise3(P, seed=11, octaves=4, base=0.45):
    """Smooth world-space noise in about [-1, 1] (sums of random plane waves), so a
    colony's front stays continuous across the seam between two surfaces."""
    rng = np.random.default_rng(seed)
    acc, norm = np.zeros(P.shape[:-1]), 0.0
    for i in range(octaves):
        amp, f = 0.55 ** i, base * 2.0 ** i
        for _ in range(3):
            k = rng.normal(size=3)
            k /= np.linalg.norm(k)
            acc += amp * np.sin(2 * np.pi * f * (P @ k) + rng.uniform(0, 2 * np.pi))
            norm += amp
    return acc / norm * 2.2


def reach(P, sites, wobble=0.35, seed=11, noise_scale=1.0):
    """1 at an inoculation site, falling to 0 at its (noisy) reach."""
    n = noise3(P / noise_scale, seed)
    out = np.zeros(P.shape[:-1])
    for _, c, R in sites:
        x = np.linalg.norm(P - np.array(c), axis=-1) / (R * (1 + wobble * n))
        out = np.maximum(out, np.clip(1 - x, 0, 1) ** 0.6)
    return out


def run_strains(s, L, sites_a, sites_b, seed, joints=None, noise_scale=1.0, params=None, lam=LAMBDA):
    """Grow both strains on one surface. Returns trails, held ground and the maps used."""
    uu, vv = s.centers(1)
    P = s.world(uu, vv)
    dom = s.domain(uu, vv)
    dark, Lx = L['darkness'], L['excess']
    ra = reach(P, sites_a, seed=11, noise_scale=noise_scale)
    rb = reach(P, sites_b, seed=11, noise_scale=noise_scale)
    dens = np.maximum(ra, rb) * (1 - Lx) ** 2 * dom
    a_ground = (ra >= rb) & dom
    out = dict(domain=dom, density=dens.astype(np.float32), a_ground=a_ground, excess=Lx, darkness=dark)
    zero = np.zeros(dark.shape, np.float32)
    if dens.sum() < 200:                            # no colony reaches this surface
        out.update(trail_a=zero, trail_b=zero, held=a_ground.astype(np.float32))
        return out
    base = 0.6 * gaussian_filter(dark, 2)
    if joints is not None:
        base = base + 0.15 * joints
    foods = [(base * (0.35 + 0.65 * gaussian_filter(r, 4)) - lam * Lx).astype(np.float32) for r in (ra, rb)]
    # Simulate only the window the colony can reach (plus a margin), then paste back.
    rows, cols = np.nonzero(dens > 0)
    m = 40
    r0, r1 = max(0, rows.min() - m), min(dens.shape[0], rows.max() + m + 1)
    c0, c1 = max(0, cols.min() - m), min(dens.shape[1], cols.max() + m + 1)
    win = (slice(r0, r1), slice(c0, c1))
    phi, fstr = pp.structure_flow([dark[win]])
    fields = dict(dark=dens[win].astype(np.float32), phi=phi, fstr=fstr, home=None, accents=[],
                  foods=[np.ascontiguousarray(f[win]) for f in foods])
    sim = pp.simulate_cultures(fields, (LOOK_A, LOOK_B), 0.5, territories=0, seed=seed, verbose=False,
                               territory_map=a_ground[win], domain=dom[win], **(params or PARAMS))
    ta, tb, held = zero.copy(), zero.copy(), a_ground.astype(np.float32)
    ta[win], tb[win], held[win] = sim['trail'][1], sim['trail'][0], sim['held']
    out.update(trail_a=ta, trail_b=tb, held=held, window=[int(r0), int(r1), int(c0), int(c1)])
    return out


def contest(res):
    """Share of occupied ground that changed strain, and share of trail on lit ground."""
    tot = res['trail_a'] + res['trail_b']
    occ = gaussian_filter(tot, 4) > 0.02
    dom = res['domain']
    moved = (((res['held'] > 0.5) != res['a_ground']) & dom & occ).sum() / max(1, (dom & occ).sum())
    lit = res['excess'] > 0.5
    in_light = tot[lit].sum() / max(1e-9, tot.sum())
    return float(moved), float(in_light)


# ----------------------------------------------------------------------------
# veins
# ----------------------------------------------------------------------------
def transport_network(T, D, thr=0.12, min_spur=12.0, min_len=4.0, max_link=20.0):
    """The trail's skeleton as a transport tree. Each branch is weighted by how much of
    the colony lies beyond it on the shortest-path tree from that piece's densest
    point (its inoculation site): Physarum tubes thicken with the flow through them
    (Tero et al. 2007, 2010). Only short cross-links survive as loops.
    Returns [(xy in cells (col, row), flow, piece total)]."""
    import networkx as nx
    Tn = pp.norm_trail(np.asarray([T]))[0]
    Sk, df = pp._skeleton_paths(pp._drop_small(Tn > thr, 12))
    if Sk is None:
        return []
    Hh, Ww = Tn.shape
    G = nx.MultiGraph()
    pos, keep = {}, []
    for i in range(Sk.n_paths):
        bt, bl = int(df['branch_type'][i]), float(df['branch_distance'][i])
        if (bt == 1 and bl < min_spur) or bl < min_len:
            continue
        a, b = int(df['node_id_src'][i]), int(df['node_id_dst'][i])
        G.add_edge(a, b, key=i, w=bl)
        pos[a] = (df['image_coord_src_0'][i], df['image_coord_src_1'][i])
        pos[b] = (df['image_coord_dst_0'][i], df['image_coord_dst_1'][i])
        keep.append(i)
    dens = lambda n: D[int(np.clip(pos[n][0], 0, Hh - 1)), int(np.clip(pos[n][1], 0, Ww - 1))]
    flow = {}
    for comp in nx.connected_components(G):
        sub = G.subgraph(comp)
        total = sum(d['w'] for _, _, d in sub.edges(data=True))
        src = max(comp, key=dens)
        dist, paths = nx.single_source_dijkstra(sub, src, weight='w')
        parent = {n: q[-2] for n, q in paths.items() if len(q) > 1}
        acc = dict.fromkeys(comp, 0.0)
        tree = {}
        for n, par in parent.items():
            ks = sub[par][n]
            k = min(ks, key=lambda kk: ks[kk]['w'])
            tree[n] = (k, ks[k]['w'])
        for n in sorted(parent, key=lambda n: -dist[n]):
            acc[parent[n]] += acc[n] + tree[n][1]
        for n, (k, w) in tree.items():
            flow[k] = (acc[n] + w, total)
        for _, _, k, d in sub.edges(keys=True, data=True):
            if k not in flow and d['w'] <= max_link:
                flow[k] = (d['w'], total)
    out = []
    for i in keep:
        if i in flow:
            rc = Sk.path_coordinates(i)
            out.append((pp._smooth(rc[:, ::-1].astype(float), 5), flow[i][0], flow[i][1]))
    return out


def vein_level(f, total):
    lv = 0
    for j, (a, frac) in enumerate(((250, .03), (900, .12), (2500, .35)), 1):
        if f > max(a, frac * total):
            lv = j
    return lv


def _plen(c):
    return float(np.hypot(*np.diff(c, axis=0).T).sum()) if len(c) > 1 else 0.0


class Strokes:
    """Concatenated world polylines with per-point attributes."""

    def __init__(self):
        self.world, self.sid, self.attr, self.meta = [], [], {}, []

    def add(self, world, **attr):
        if len(world) < 2:
            return
        self.world.append(np.asarray(world, float))
        self.sid.append(np.full(len(world), len(self.meta)))
        for k, v in attr.items():
            self.attr.setdefault(k, []).append(np.broadcast_to(np.asarray(v), (len(world),)).copy()
                                              if np.ndim(v) else np.full(len(world), v))
        self.meta.append(len(world))

    def finish(self, cam):
        self.world = np.concatenate(self.world) if self.world else np.zeros((0, 3))
        self.sid = np.concatenate(self.sid) if self.sid else np.zeros(0, int)
        self.attr = {k: np.concatenate(v) for k, v in self.attr.items()}
        sx, sy, z = cam.project(self.world)
        self.xy, self.z = np.stack([sx, sy], 1), z
        return self


def resample_screen(cam, world_fn, t0, t1, n_coarse, step_px=1.6, min_pts=2):
    t = np.linspace(t0, t1, n_coarse)
    sx, sy, _ = cam.project(world_fn(t))
    cum = np.r_[0, np.cumsum(np.hypot(np.diff(sx), np.diff(sy)))]
    n = max(min_pts, int(math.ceil(cum[-1] / step_px)) + 1)
    return np.interp(np.linspace(0, cum[-1], n), cum, t)


def colony_strokes(surfaces, results, cam, lens_gap=1.05):
    """Both strains on every surface -> world polylines. rank 0 = the heaviest vein."""
    st = Strokes()
    for si, s in enumerate(surfaces):
        r = results[s.name]
        for strain, key in (('A', 'trail_a'), ('B', 'trail_b')):
            T = r[key]
            if T.max() <= 0:
                continue
            net = transport_network(T, r['density'])
            if not net:
                continue
            flows = np.array([f for _, f, _ in net])
            lens_ = np.array([max(_plen(c), 1e-6) for c, _, _ in net])
            order = np.argsort(-flows)
            cum = np.cumsum(lens_[order]) / lens_.sum()
            rank = np.empty(len(net))
            rank[order] = cum - lens_[order] / lens_.sum()
            for (c, f, total), rk in zip(net, rank):
                lv = vein_level(f, total)
                n = len(c)
                strokes = [(c, 0)]
                if lv and n >= 8:
                    t = np.arange(n)
                    taper = np.clip(np.minimum(t, n - 1 - t) / 6.0, 0, 1)
                    taper = taper * taper * (3 - 2 * taper)
                    for j in range(1, lv + 1):
                        d = j * lens_gap * taper
                        strokes.append((np.vstack([pp._offset(c, d), pp._offset(c, -d)[::-1]]), j))
                for xy, j in strokes:
                    u, v = s.cell_uv(xy[:, 0], xy[:, 1])
                    m = len(u)
                    fu = lambda tt: np.interp(tt, np.arange(m), u)
                    fv = lambda tt: np.interp(tt, np.arange(m), v)
                    tf = resample_screen(cam, lambda tt: s.world(fu(tt), fv(tt)), 0., m - 1., m)
                    uu, vv = fu(tf), fv(tf)
                    P = s.world(uu, vv)
                    eu, ev = s.frame(uu, vv)
                    J = cam.jacobian(P, eu, ev)
                    scale = np.sqrt(np.abs(J[..., 0, 0] * J[..., 1, 1] - J[..., 0, 1] * J[..., 1, 0]))
                    minpx = np.full(len(uu), 99.0) if j == 0 else j * lens_gap * s.cell * scale
                    st.add(P + s.normal(uu, vv) * .003, rank=float(rk), width=1.35 if j == 0 else 0.95,
                           strain=strain, level=j, minpx=minpx, surf=si, alive=s.domain(uu, vv))
    return st.finish(cam)


# ----------------------------------------------------------------------------
# screen budget and polylines
# ----------------------------------------------------------------------------
GRID = 2


@njit(cache=True)
def _splat(xy, sid, keep, width, weight, out):
    Hc, Wc = out.shape
    for i in range(xy.shape[0] - 1):
        if sid[i] != sid[i + 1] or not keep[i] or not keep[i + 1]:
            continue
        L = math.hypot(xy[i + 1, 0] - xy[i, 0], xy[i + 1, 1] - xy[i, 1])
        cx = int(0.5 * (xy[i, 0] + xy[i + 1, 0]) / 2.0)
        cy = int(0.5 * (xy[i, 1] + xy[i + 1, 1]) / 2.0)
        if 0 <= cx < Wc and 0 <= cy < Hc:
            out[cy, cx] += L * width[i] * weight[i] / 4.0


def coverage_map(st, keep, weight, cam):
    out = np.zeros((cam.H // GRID, cam.W // GRID))
    _splat(st.xy, st.sid, keep, st.attr['width'].astype(float), np.broadcast_to(weight, len(keep)).astype(float), out)
    return gaussian_filter(out, 3.0)


def sample(grid, xy):
    return map_coordinates(grid, [xy[:, 1] / GRID - .5, xy[:, 0] / GRID - .5], order=1, mode='nearest')


def rdp(p, tol=.25):
    p = np.asarray(p)
    if len(p) < 3:
        return list(p)
    a, b = p[0], p[-1]
    ab = b - a
    length = np.linalg.norm(ab)
    if length < 1e-8:
        j = np.argmax(np.sum((p - a) ** 2, 1))
        if j == 0:
            return [p[0], p[-1]]
        return rdp(p[:j + 1], tol)[:-1] + rdp(p[j:], tol)
    dist = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / length
    j = int(np.argmax(dist))
    if dist[j] < tol:
        return [p[0], p[-1]]
    return rdp(p[:j + 1], tol)[:-1] + rdp(p[j:], tol)


def runs(st, keep, min_px=2.5, tol=0.25):
    out, widths, labels = [], [], []
    idx = np.flatnonzero(keep)
    if not len(idx):
        return out, widths, labels
    brk = np.flatnonzero((np.diff(idx) != 1) | (np.diff(st.sid[idx]) != 0)) + 1
    for g in np.split(idx, brk):
        if len(g) < 2:
            continue
        q = st.xy[g]
        if np.hypot(*np.diff(q, axis=0).T).sum() < min_px:
            continue
        out.append(np.array(rdp(q, tol) if len(q) > 2 else list(q)))
        widths.append(float(st.attr['width'][g[0]]))
        labels.append(st.attr['strain'][g[0]] if 'strain' in st.attr else '')
    return out, widths, labels


def allocate_colony(st, vis, cap, cam):
    """Heaviest veins first, until the colony's own ink reaches `cap` coverage on screen;
    side strokes dropped where they would sit closer than a pen width to their vein."""
    alive = st.attr['alive'] & vis & ((st.attr['level'] == 0) | (st.attr['minpx'] >= 1.1))
    full = coverage_map(st, alive, COLONY_WEIGHT, cam)
    phi = np.minimum(1, cap / np.maximum(sample(full, st.xy), 1e-4))
    return alive & (st.attr['rank'] < phi)


def halo_raster(lines, radius, cam):
    """Paper reserved around the colony's veins: True within `radius` px of a vein."""
    img = Image.new('1', (cam.W, cam.H), 0)
    dr = ImageDraw.Draw(img)
    for q in lines:
        dr.line([tuple(map(float, a)) for a in q], fill=1, width=int(round(2 * radius)))
    return np.asarray(img, bool)


def clip_polyline(q, mask, step=0.8, min_px=1.4, tol=0.25):
    """Cut a screen polyline wherever it enters `mask`; returns the pieces outside it."""
    q = np.asarray(q, float)
    if len(q) < 2:
        return []
    seg = np.hypot(*np.diff(q, axis=0).T)
    cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] <= 0:
        return []
    t = np.linspace(0, cum[-1], max(2, int(cum[-1] / step) + 2))
    pts = np.stack([np.interp(t, cum, q[:, 0]), np.interp(t, cum, q[:, 1])], 1)
    H, W = mask.shape
    ix = np.clip(np.rint(pts[:, 0]).astype(int), 0, W - 1)
    iy = np.clip(np.rint(pts[:, 1]).astype(int), 0, H - 1)
    keep = ~mask[iy, ix]
    if keep.all():
        return [q]
    out = []
    d = np.diff(np.r_[0, keep.astype(np.int8), 0])
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        piece = pts[a:b]
        if len(piece) >= 2 and np.hypot(*np.diff(piece, axis=0).T).sum() >= min_px:
            out.append(np.array(rdp(piece, tol)))
    return out


def write_svg(path, layers, title, cam, pens=None, underlay=''):
    """layers: {name: [(polyline (n, 2), width, opacity)]}; one Inkscape layer each."""
    pens = pens or PENS
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{cam.W}" height="{cam.H}" viewBox="0 0 {cam.W} {cam.H}"><title>{title}</title>'
             f'<rect width="100%" height="100%" fill="white"/>{underlay}']
    for li, (lname, items) in enumerate(layers.items(), 1):
        parts.append(f'<g inkscape:groupmode="layer" inkscape:label="{li} {lname}" fill="none" stroke="{pens[lname]}" '
                     f'stroke-linecap="round" stroke-linejoin="round">')
        for q, w, op in items:
            d = 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in q)
            parts.append(f'<path d="{d}" stroke-width="{w:.2f}"' + (f' opacity="{op:.2f}"' if op < 1 else '') + '/>')
        parts.append('</g>')
    parts.append('</svg>')
    path.write_text(''.join(parts))
    import cairosvg
    cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix('.png')), output_width=cam.W, output_height=cam.H)


def veins(colony_st, colony_vis, cam, cap=0.16, halo_px=HALO_PX):
    """The veins that are kept, and the paper reserved around them."""
    keep_c = allocate_colony(colony_st, colony_vis, cap, cam)
    lines, widths, strains = runs(colony_st, keep_c, min_px=3.0)
    return dict(lines=lines, widths=widths, strains=strains, halo=halo_raster(lines, halo_px, cam))


def paper_share(V, sigma=8.0, cap=0.5):
    """Local share of paper the white line reserves (screen map, 0..cap). Marks this
    package allocates from a tone target use it to thicken around the cut, so the
    local tone holds; Sol's own marks are only cut."""
    return np.clip(gaussian_filter(V['halo'].astype(float), sigma), 0, cap)


def compose(base, V):
    """base: [(polyline, width, opacity, cuttable)]. Returns plate layers: the base ink
    with paper reserved around the veins (only 'cuttable' marks are cut: hatching,
    never structure), and the veins themselves, one layer per strain."""
    ink, cut_count = [], 0
    for q, w, op, cuttable in base:
        if cuttable:
            pieces = clip_polyline(q, V['halo'])
            cut_count += int(len(pieces) != 1 or len(pieces[0]) != len(q))
            ink += [(p, w, op) for p in pieces]
        else:
            ink.append((np.asarray(q), w, op))
    strain = lambda s: [(q, w, 1.0) for q, w, sa in zip(V['lines'], V['widths'], V['strains']) if sa == s]
    layers = {'ink': ink, 'strain A': strain('A'), 'strain B': strain('B')}
    alone = {'ink': [(np.asarray(q), w, op) for q, w, op, cuttable in base if not cuttable],
             'strain A': layers['strain A'], 'strain B': layers['strain B']}
    return layers, alone, dict(veins=len(V['lines']), hatch_marks_cut=cut_count)


def local_ink(png_base, png_mould, V, cam, near_px=12, sigma=8.0):
    """Ink near the mould, measured on the rendered plates: mean blurred coverage
    within `near_px` of a vein, before and after."""
    from scipy.ndimage import binary_dilation
    def cov(p):
        g = np.asarray(Image.open(p).convert('L'), float)
        return gaussian_filter(np.clip((255 - g) / (255 - 37), 0, 1), sigma)
    near = binary_dilation(halo_raster(V['lines'], 1.0, cam), iterations=near_px)
    a, b = cov(png_base), cov(png_mould)
    return dict(base=float(a[near].mean()), with_mould=float(b[near].mean()), pixels=int(near.sum()))
