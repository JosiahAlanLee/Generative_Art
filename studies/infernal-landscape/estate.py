"""The original estate grammar: vertical duration storeys, raised foundations
for release time, closed portcullises, raised service trays for prerequisites.

Moved unchanged from model.py; the builder `T` now supplies the primitives.
"""
import numpy as np

CAMERAS = [('main', (27, -38, 23), (0, 9.5, 3), 3500.), ('low', (30, -38, 13), (0, 9, 3), 3500.)]
# One foreground engraved oak remains a drawing-plane symbol (render.py's default).
PLANAR_TREES = [(-12.5, -.6, 7.0)]


def dimensions(node):
    name = node['id']
    return (3.3, 3.0) if name == 'approval' else (4.1, 3.6) if name == 'staff' else (3.6, 3.2)


def build_scene(A, T):
    box, beam, ink, mesh, arch, ground = T.box, T.beam, T.ink, T.mesh, T.arch, T.terrain_z
    TOP = {}; BASE = {}; FOOTPRINTS = []
    for node in A['nodes']:
        name = node['id']; x, y = node['x'], node['y']; z = float(ground(x, y)) + .14 + node['plinth']
        w, d = dimensions(node)
        BASE[name] = (x, y, z); FOOTPRINTS.append([x - w / 2 - .55, y - d / 2 - .5, x + w / 2 + .55, y + d / 2 + .5])
        box(name + ' foundation', (x - w / 2 - .2, y - d / 2 - .2, float(ground(x, y)) - .8), (x + w / 2 + .2, y + d / 2 + .2, z))
        # A grounded 0.8-unit entrance base gives the one-bay building a portal
        # taller than its windows without pushing the portcullis through its roof.
        box(name + ' entrance base', (x - w / 2, y - d / 2, z), (x + w / 2, y + d / 2, z + .8))
        h = .8 + T.story_nodes(name, x, y, z + .8, w, d, node['bays']); TOP[name] = z + h
        T.roof(name + ' roof', x, y, z + h + .02, w + .65, d + .60, 1.0 if name == 'approval' else .7)
        arch(name + ' portal', x, y - d / 2 - .12, z, 1.15, 1.75)
        # Foundation courses remain fixed to the building; surface marks are separate.
        for dz in np.arange(float(ground(x, y)) - .1, z, .24):
            ink('Rusticated foundation', [(x - w / 2 - .21, y - d / 2 - .21, dz), (x + w / 2 + .21, y - d / 2 - .21, dz), (x + w / 2 + .21, y + d / 2 + .21, dz)], .10)
        if node['release_at']:
            # Late release is drawn as a real lift tower, not extra duration bays.
            for dx in (-.9, .9):
                beam('Release lift upright', (x + dx, y - d / 2 - .5, float(ground(x, y))), (x + dx, y - d / 2 - .5, z + .3), .09)
            for dz in np.arange(float(ground(x, y)), z, .55):
                beam('Release lift bracing', (x - .9, y - d / 2 - .5, dz), (x + .9, y - d / 2 - .5, dz + .5), .04)
            box('Release lift landing', (x - 1, y - d / 2 - .75, z - .12), (x + 1, y - d / 2 + .1, z), 2)
        if not node['available']:
            for dx in np.linspace(-.48, .48, 7):
                beam('Unavailable portcullis', (x + dx, y - d / 2 - .27, z), (x + dx, y - d / 2 - .27, z + 1.5), .035)

    # Two prerequisites join at restore: two independent supported service routes.
    ROUTES = []
    for k, e in enumerate(A['edges']):
        a, b = e['source'], e['target']; x, y, z = BASE[a]; X, Y, Z = BASE[b]
        # A raised cable tray leaves a separate socket on the right of each facade.
        p = np.array([(x + 1.2, y, z + .75), (x + 2.3, y, z + .75), (x + 2.3, y, Z + .75), (X + 2.3, Y, Z + .75), (X + 1.2, Y, Z + .75)])
        p = p[np.r_[True, np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-5]]
        for j, (u, v) in enumerate(zip(p, p[1:])):
            beam('Service tray ' + str(k), u + [0, 0, -.10], v + [0, 0, -.10], .055, 2)
            if np.linalg.norm((v - u)[:2]) > .3:
                for t in np.linspace(0, 1, max(2, int(np.linalg.norm(v - u) / 1.8))):
                    q = u * (1 - t) + v * t
                    beam('Service support', q + [0, 0, -.15], [q[0], q[1], float(ground(q[0], q[1])) - .10], .045)
        # Ink-only lifted centerline, so the tray does not swallow its own route.
        ink('Dependency ' + a + ' to ' + b, p + [0, 0, .035], .32, 2)
        ROUTES.append(dict(source=a, target=b, pts=p.tolist()))

    # Restoration powerhouse: a grounded chimney, fluted vat and flywheel.
    x, y, z = BASE[A['target']]
    beam('Powerhouse chimney', (x + .8, y + .6, z), (x + .8, y + .6, TOP[A['target']] + 2.4), .34, 3, 10)
    for r in (.76, .94):
        t = np.linspace(0, 2 * np.pi, 97)
        ink('External flywheel', np.c_[x + np.cos(t) * r, np.full(len(t), y - 1.88), z + 1.05 + np.sin(t) * r], .16)
    for t in np.arange(8) * np.pi / 4:
        ink('Flywheel spoke', [(x, y - 1.88, z + 1.05), (x + np.cos(t) * .76, y - 1.88, z + 1.05 + np.sin(t) * .76)], .12)
    beam('Wheel pedestal', (x, y - 1.88, float(ground(x, y))), (x, y - 1.88, z + .35), .18)

    # Open field gateway: masonry and threshold give plant occlusion thin blockers.
    for x in (-1.9, 1.9):
        z = float(ground(x, -.3)); box('Entry pier', (x - .22, -.6, z - .2), (x + .22, -.1, z + 2.3))
    arch('Open approach arch', 0, -.35, float(ground(0, -.35)), 3.8, 4.1, .30)

    # Fence rooted independently along an undulating contour.
    posts = []
    for x in np.arange(-15, 15.1, 1.7):
        if abs(x) < 2.5:
            posts.append(None); continue
        y = -.1 + .10 * x; z = float(ground(x, y)) - .08
        beam('Meadow fence post', (x, y, z), (x, y, z + 1.0), .07); posts.append(np.array([x, y, z]))
    for a, b in zip(posts, posts[1:]):
        if a is None or b is None: continue
        for h in (.40, .79):
            beam('Meadow fence rail', a + [0, 0, h], b + [0, 0, h], .035)

    T.oak('Volume oak near', 10.3, 9.5, 6.7, 371)
    T.oak('Volume oak far', -11.8, 20, 6.5, 521)
    for i, (x, y, h) in enumerate([(-20, 27, 4.6), (-15, 29, 4.4), (-7, 31, 4.5), (0, 31, 5.2), (8, 30, 4.8), (16, 29, 5.1)]):
        T.oak('Ridge oak ' + str(i), x, y, h, 900 + i)

    # Limestone bluff slabs, their strata give the field a recognisable region.
    for j in range(3):
        # Every exposed stratum follows the ridge, with its lower edge buried.
        xs = np.linspace(-25, -8, 20); ys = 23 + .17 * xs + j * .65
        zs = ground(xs, ys) - .10
        vs = np.vstack([np.c_[xs, ys, zs], np.c_[xs, ys + .22, zs + .28]])
        mesh('Limestone ledge ' + str(j), vs, [(i, i + 1, i + 21, i + 20) for i in range(19)], 1)
    return TOP, BASE, FOOTPRINTS, ROUTES
