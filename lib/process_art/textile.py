"""Reusable textile grammar and three couplings, rather than a page-wide style.

Original motifs combine nested quarter-turn/stepped paths and occasional cross
junctions. Truchet/Smith is the tiling precedent; Wright's office is a design
reference, not the inventor of these algorithms. Coordinates are tile units.
"""
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, label, map_coordinates
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve
from shapely.geometry import LineString

from .drawing import Plate, INK, RED, clipped, contours


@dataclass
class Textile:
    nodes: np.ndarray
    edges: np.ndarray
    paths: list
    length: np.ndarray
    nx: int
    ny: int
    seed: int

    def raster(self, pixels_per_tile=40, width=2):
        """Rasterize the same scaffold used for drawing; white is solid material."""
        if pixels_per_tile < 8 or width < 1:
            raise ValueError("pixels_per_tile >= 8 and width >= 1 required")
        size = (self.nx*pixels_per_tile+1, self.ny*pixels_per_tile+1)
        image = Image.new("L", size)
        pen = ImageDraw.Draw(image)
        for p in self.paths:
            pen.line([tuple(v*pixels_per_tile) for v in p], fill=255, width=width, joint="curve")
        return np.asarray(image) > 0


def grammar(seed=17, nx=6, ny=8):
    """Shared edge ports at .35, .50, .65 make the tiles join across rotations.

    Nested curves and steps are drawing edges. A geometric crossing is not a
    graph junction unless it shares an explicit endpoint. Cross junctions join
    the middle lanes; the other lanes remain decorative loops/routes.
    """
    if not isinstance(nx, int) or not isinstance(ny, int) or nx < 1 or ny < 1:
        raise ValueError("positive integer tile dimensions required")
    rng = np.random.default_rng(seed)
    nodes, node_ids, paths, edges = [], {}, [], []

    def node(p):
        key = tuple(np.round(p, 7))
        if key not in node_ids:
            node_ids[key] = len(nodes)
            nodes.append(key)
        return node_ids[key]

    def add(p):
        p = np.asarray(p, float)
        paths.append(p)
        edges.append((node(p[0]), node(p[-1])))

    for y in range(ny):
        for x in range(nx):
            # Large bands of related motifs; no independent per-stroke jitter.
            turn = int((x//2 + y//3 + seed) % 2) ^ int(rng.random() < .12)
            stepped = (x+y+seed) % 4 == 0
            for radius in (.35, .5, .65):
                if stepped:
                    base = np.array([[radius, 0], [radius, radius], [0, radius]])
                else:
                    t = np.linspace(0, np.pi/2, 25)
                    base = np.column_stack([radius*np.cos(t), radius*np.sin(t)])
                for opposite in (False, True):
                    p = 1-base if opposite else base.copy()
                    if turn:
                        p[:, 0] = 1-p[:, 0]
                    add(p+[x, y])
            if (x+y) % 3 == 0 or (x == nx//2):
                c = np.array([x+.5, y+.5])
                for port in ([x+.5, y], [x+1, y+.5], [x+.5, y+1], [x, y+.5]):
                    add([port, c])
    lengths = [np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for p in paths]
    return Textile(np.asarray(nodes), np.asarray(edges), paths, np.asarray(lengths), nx, ny, seed)


def graph_veins(textile, steps=90):
    """Pressure flow with conductance adaptation on the largest scaffold component.

    One unit of source flow, shared equally by six requested drains; gauge p=0
    at the source. Kirchhoff at all other nodes, including prescribed demands.
    D <- .82 D + .18 (.015 + |Q|/max|Q|). This is a geometric transport analogue,
    inspired by adaptive Physarum transport models, not a vascular growth solver.
    """
    edges, nodes = textile.edges, textile.nodes
    n = len(nodes)
    row = np.r_[edges[:, 0], edges[:, 1]]
    col = np.r_[edges[:, 1], edges[:, 0]]
    adjacency = coo_matrix((np.ones(len(row)), (row, col)), shape=(n, n)).tocsr()
    _, labels = connected_components(adjacency, directed=False)
    counts = np.bincount(labels)
    component = int(np.argmax(counts))
    ids = np.flatnonzero(labels == component)
    active = (labels[edges[:, 0]] == component)
    sources = [int(ids[np.argmin(nodes[ids, 1] + .23*nodes[ids, 0])])]
    targets = [[textile.nx*x, textile.ny*y] for x, y in
               ((.12, .25), (.87, .23), (.13, .55), (.88, .57), (.18, .92), (.84, .91))]
    drains = sorted({int(ids[np.argmin(np.linalg.norm(nodes[ids]-t, axis=1))]) for t in targets} - set(sources))
    if not drains:
        raise ValueError("scaffold has no distinct source/drain")
    fixed = np.asarray(sources)
    unknown = np.setdiff1d(ids, fixed)
    free = np.setdiff1d(ids, sources+drains)
    pressure = np.zeros(n)
    injection = np.zeros(n)
    injection[sources] = 1
    injection[drains] = -1/len(drains)
    conductance = np.zeros(len(edges))
    conductance[active] = 1

    def solve():
        c = conductance/textile.length
        a, b = edges[:, 0], edges[:, 1]
        lap = coo_matrix((np.r_[c, c, -c, -c],
                          (np.r_[a, b, a, b], np.r_[a, b, b, a])), shape=(n, n)).tocsr()
        if len(unknown):
            pressure[unknown] = spsolve(lap[unknown][:, unknown], injection[unknown])
        return c*(pressure[a]-pressure[b])

    for _ in range(steps):
        flow = solve()
        target = .015 + np.abs(flow)/max(np.max(np.abs(flow)), 1e-12)
        conductance[active] = .82*conductance[active] + .18*target[active]
    flow = solve()
    residual = np.zeros(n)
    np.add.at(residual, edges[:, 0], flow)
    np.add.at(residual, edges[:, 1], -flow)
    return {"pressure": pressure, "conductance": conductance, "flow": flow,
            "sources": np.asarray(sources), "drains": np.asarray(drains),
            "active_edges": active, "free_nodes": free, "kirchhoff_residual": residual,
            "prescribed_injection": injection}


def flux_laplacian(field, permeability):
    """Conservative face flux, reflecting outer edges; zero closes a face."""
    out = np.zeros_like(field)
    px = np.minimum(permeability[:, 1:], permeability[:, :-1])
    flux = px*(field[:, 1:]-field[:, :-1])
    out[:, :-1] += flux
    out[:, 1:] -= flux
    py = np.minimum(permeability[1:, :], permeability[:-1, :])
    flux = py*(field[1:, :]-field[:-1, :])
    out[:-1, :] += flux
    out[1:, :] -= flux
    return out


def compartment_chemistry(solid, seed=17, steps=1800):
    """Gray–Scott with no chemical exchange across the rasterized scaffold."""
    rng = np.random.default_rng(seed)
    free = ~solid
    permeability = free.astype(float)
    u, v = np.ones(solid.shape), np.zeros(solid.shape)
    components, count = label(free)
    sizes = np.bincount(components.ravel())
    sizes[0] = 0
    # Inoculate seven large compartments, rather than clipping a full-field run.
    selected = np.argsort(sizes)[-min(7, count):]
    clearance = distance_transform_edt(free)
    yy, xx = np.mgrid[:solid.shape[0], :solid.shape[1]]
    seeds = []
    for c in selected:
        candidates = np.argwhere((components == c) & (clearance > 3))
        if not len(candidates):
            continue
        for _ in range(min(3, max(1, len(candidates)//250))):
            y, x = candidates[rng.integers(len(candidates))]
            patch = ((xx-x)**2+(yy-y)**2 < 4.5**2) & free
            u[patch], v[patch] = .5, .25
            seeds.append((int(y), int(x)))
    for _ in range(steps):
        uvv = u*v*v
        u += .16*flux_laplacian(u, permeability) - uvv + .035*(1-u)*free
        v += .08*flux_laplacian(v, permeability) + uvv - (.035+.061)*v
    return {"u": u, "v": v, "solid": solid, "components": components,
            "inoculation_yx": np.asarray(seeds), "component_count": np.asarray(count)}


def dissolve(solid, seed=17, steps=2200):
    """Illustrative acid diffusion/reaction removes scaffold material over time.

    Local material loss is irreversible. Low permeability through intact material
    permits a reaction front. Eight replenished pore vents are explicit inputs.
    Units and rate constants are dimensionless; this is not calibrated corrosion.
    """
    rng = np.random.default_rng(seed)
    material = solid.astype(float)
    initial = material.copy()
    acid = np.zeros_like(material)
    clearance = distance_transform_edt(~solid)
    vent_radius = min(5.0, float(clearance.max())*.7)
    candidates = np.argwhere(clearance > vent_radius)
    if not len(candidates):
        raise ValueError("scaffold needs open pores")
    vents = [candidates[rng.integers(len(candidates))]]
    # Farthest-point sampling spreads exposure rather than adding white noise.
    for _ in range(7):
        distances = np.min(np.linalg.norm(candidates[:, None]-np.asarray(vents)[None, :], axis=2), axis=1)
        vents.append(candidates[int(np.argmax(distances))])
    vent_mask = np.zeros_like(solid)
    yy, xx = np.mgrid[:solid.shape[0], :solid.shape[1]]
    for y, x in vents:
        vent_mask |= ((yy-y)**2+(xx-x)**2 < vent_radius**2) & ~solid
    loss_history = []
    for t in range(steps):
        permeability = .025+.19*(1-material)
        acid += flux_laplacian(acid, permeability)
        loss = .022*acid*material
        material -= loss
        acid -= .35*loss
        acid[vent_mask] = 1
        if t % 20 == 0:
            loss_history.append(float(np.sum(initial-material)))
    _, before = label(~solid)
    _, after = label(material < .35)
    return {"material": material, "initial": initial, "acid": acid,
            "vents_yx": np.asarray(vents), "vent_mask": vent_mask,
            "loss_history": np.asarray(loss_history),
            "compartments_before": np.asarray(before), "compartments_after": np.asarray(after)}


def path_spans(path, scalar, textile, threshold=.35):
    """Split original paths at a material threshold before SVG export."""
    line = LineString(path)
    n = max(3, int(line.length*65))
    points = np.array([line.interpolate(d).coords[0] for d in np.linspace(0, line.length, n)])
    coords = np.vstack([points[:, 1]/textile.ny*(scalar.shape[0]-1),
                        points[:, 0]/textile.nx*(scalar.shape[1]-1)])
    keep = map_coordinates(scalar, coords, order=1, mode="nearest") >= threshold
    cuts = np.flatnonzero(np.diff(np.r_[False, keep, False]))
    return [points[a:b] for a, b in cuts.reshape(-1, 2) if b-a >= 2]


def draw_component(plate, textile, mode="control", state=None, box=(0, 0, 132, 176), clip=None):
    """Place just this material on any plate; no furniture or lettering is added."""
    x, y, width, height = box
    scale = np.array([width/textile.nx, height/textile.ny])

    def draw(points, color=INK, pen=.12):
        points = np.asarray(points)*scale+[x, y]
        if clip is None:
            plate.add(points, color, pen)
        else:
            clipped(plate, points, clip, color, pen)

    for path in textile.paths:
        spans = path_spans(path, state["material"], textile) if mode == "erosion" else [path]
        for span in spans:
            draw(span, pen=.13 if mode == "control" else .095)
    if mode == "veins":
        flow = np.abs(state["flow"])
        normalized = flow/max(flow.max(), 1e-12)
        for path, value in zip(textile.paths, normalized):
            if value > .015:
                draw(path, RED, .14+.48*np.sqrt(value))
        for ids in (state["sources"], state["drains"]):
            for node in textile.nodes[ids]:
                t = np.linspace(0, 2*np.pi, 48)
                circle = node + .045*np.column_stack([np.cos(t), np.sin(t)])
                # Wells at an outer edge are left as open edge connections.
                if (circle >= 0).all() and (circle <= [textile.nx, textile.ny]).all():
                    draw(circle, RED, .2)
    if mode in ("chemistry", "erosion"):
        chemical = Plate("field overlay", plate.width, plate.height)
        if mode == "chemistry":
            contours(chemical, state["v"], [.07, .16, .28, .36], box, ~state["solid"], RED, .13)
        else:
            # The front contours and surviving scaffold are distinct layers.
            front = state["acid"]*np.sqrt(np.maximum(state["material"], 0))
            contours(chemical, front, [.035, .08, .16], box, color=RED, width=.105)
        for stroke in chemical.strokes:
            if clip is None:
                plate.add(stroke.points, stroke.color, stroke.width)
            else:
                clipped(plate, stroke.points, clip, stroke.color, stroke.width)


def run(seed=17, mode="control", pixels_per_tile=40):
    textile = grammar(seed)
    if mode == "control":
        state = {}
    elif mode == "veins":
        state = graph_veins(textile)
    elif mode == "chemistry":
        state = compartment_chemistry(textile.raster(pixels_per_tile), seed)
    elif mode == "erosion":
        state = dissolve(textile.raster(pixels_per_tile), seed)
    else:
        raise ValueError("mode must be control, veins, chemistry or erosion")
    return textile, state
