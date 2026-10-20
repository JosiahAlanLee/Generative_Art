"""Scan ingestion, the arched setting, and camera presets for the v2 engraving.

Geometry is v1's: same transform, same plinth and recess. The one change is that
UV-seam duplicates in the GLB are welded, so the scan is a connected surface.
"""
from pathlib import Path
import hashlib
import numpy as np
import trimesh
import engraving_core as e   # v1 helpers: face(), line(), box(), FACES, LINES

ROOT = Path(__file__).resolve().parent
W, H = 1500, 1900
TARGET = np.array([0., 0., 2.35])
FOCAL = 3000.
LIGHT = np.array([-3.8, -3.0, 6.3])
LIGHT_SIZE = (1.8, 2.0)          # x by z extent of v1's rectangular source
CAMERAS = {
    'front': np.array([-3.0, -8., 3.2]),    # Scanned Statue plates
    'second': np.array([4.8, -7.1, 3.35]),  # Trail First second angle
}


class Camera:
    def __init__(self, eye, target=TARGET, focal=FOCAL, w=W, h=H):
        self.eye = np.asarray(eye, float); self.target = np.asarray(target, float)
        self.focal = focal; self.w = w; self.h = h; self.cx = w * .5; self.cy = h * .51
        F = self.target - self.eye; self.F = F / np.linalg.norm(F)
        R = np.cross(self.F, [0., 0., 1.]); self.R = R / np.linalg.norm(R)
        self.U = np.cross(self.R, self.F)

    def project(self, p):
        q = np.asarray(p) - self.eye; z = q @ self.F
        return np.stack([self.cx + self.focal * (q @ self.R) / z, self.cy - self.focal * (q @ self.U) / z, z], -1)

    def px_per_unit(self, p):
        return self.focal / ((np.asarray(p) - self.eye) @ self.F)

    def jacobian(self, p):
        q = p - self.eye; z = q @ self.F
        jx = self.focal * (self.R[None, :] / z[:, None] - (q @ self.R)[:, None] * self.F[None, :] / z[:, None] ** 2)
        jy = -self.focal * (self.U[None, :] / z[:, None] - (q @ self.U)[:, None] * self.F[None, :] / z[:, None] ** 2)
        return jx, jy

    def rays(self, px, py):
        d = self.F[None, :] + ((px - self.cx) / self.focal)[:, None] * self.R[None, :] \
            - ((py - self.cy) / self.focal)[:, None] * self.U[None, :]
        return d / np.linalg.norm(d, axis=1)[:, None]


def load_scan():
    """v1 transform, then weld vertices that share an exact position.

    The Sketchfab GLB splits the surface along its texture atlas: 94,531 vertex
    records for 74,939 positions, leaving ~37k open seam edges. v1 found
    silhouettes by vertex index, so every outline broke at every seam.
    All 149,999 triangles are kept; welding changes connectivity only.
    """
    scan = trimesh.load(ROOT / 'greek-slave.glb').to_geometry()
    raw = np.asarray(scan.vertices)
    faces = np.asarray(scan.faces)
    _, first, inverse = np.unique(raw, axis=0, return_index=True, return_inverse=True)
    v = raw[first].copy()[:, [0, 2, 1]]; v[:, 1] *= -1
    scale = 4 / np.ptp(v[:, 2]); v *= scale; v[:, 2] -= v[:, 2].min(); v[:, 2] += .48
    mesh = trimesh.Trimesh(v, inverse.reshape(-1)[faces], process=False)
    return mesh, scale, len(raw)


def build_setting():
    """v1's plinth, arch and recess, collected through v1's helpers."""
    e.FACES.clear(); e.LINES.clear()
    e.box(-.77, -.72, 0, .77, .70, .12, 0)
    e.box(-.64, -.60, .12, .64, .58, .39, 0)
    e.box(-.72, -.66, .39, .72, .64, .48, 0)
    spring = 3.50; rad = 1.30
    arch = np.array([[rad * np.cos(a), 1.03, spring + rad * np.sin(a)] for a in np.linspace(0, np.pi, 81)])
    boundary = np.vstack([[-rad, 1.03, 0], [rad, 1.03, 0], arch])
    e.face(boundary, 0)
    e.line(boundary, 1.05, 'arch')
    for radius, y in [(1.42, .93), (1.48, .91)]:
        q = np.array([[radius * np.cos(a), y, spring + radius * np.sin(a)] for a in np.linspace(0, np.pi, 81)])
        q = np.vstack([[radius, y, 0], q, [-radius, y, 0]])
        e.line(q, 1.05, 'arch')
    for a, b in zip(arch, arch[1:]):
        e.face([a, b, b + [0, -.12, 0], a + [0, -.12, 0]], 0)
    e.face([[-rad, 1.03, 0], [-rad, 1.03, spring], [-rad, .91, spring], [-rad, .91, 0]], 0)
    e.face([[rad, .91, 0], [rad, .91, spring], [rad, 1.03, spring], [rad, 1.03, 0]], 0)
    e.face([[-2, -1.25, -.006], [2, -1.25, -.006], [2, 1.04, -.006], [-2, 1.04, -.006]], 0)
    return list(e.FACES), list(e.LINES)


def scene_triangles(mesh, setting_faces):
    """All ray-traced triangles. owner >= 0 is a scan face index; owner < 0 is
    -(setting face index + 1). Degenerate triangles are skipped, as in v1."""
    st = mesh.vertices[mesh.faces]
    area = np.linalg.norm(np.cross(st[:, 1] - st[:, 0], st[:, 2] - st[:, 0]), axis=1)
    keep = area > 1e-9
    tris = [st[keep]]; mats = [np.full(keep.sum(), 6)]; owner = [np.flatnonzero(keep)]
    for k, f in enumerate(setting_faces):
        for i in range(1, len(f.p) - 1):
            t = f.p[[0, i, i + 1]]
            if np.linalg.norm(np.cross(t[1] - t[0], t[2] - t[0])) > 1e-9:
                tris.append(t[None]); mats.append([f.mat]); owner.append([-(k + 1)])
    return np.concatenate(tris), np.concatenate(mats).astype(int), np.concatenate(owner).astype(np.int64)


def vertex_normals(mesh, smooth=0):
    """Area-weighted vertex normals, optionally averaged over 1-rings `smooth` times."""
    v, f = mesh.vertices, mesh.faces
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    vn = np.zeros_like(v)
    for k in range(3):
        np.add.at(vn, f[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1)[:, None], 1e-15)
    if smooth:
        import scipy.sparse as sp
        ed = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
        A = sp.coo_matrix((np.ones(len(ed)), (ed[:, 0], ed[:, 1])), shape=(len(v), len(v))).tocsr()
        A = ((A + A.T) > 0).astype(float)
        for _ in range(smooth):
            vn = vn + A @ vn
            vn /= np.maximum(np.linalg.norm(vn, axis=1)[:, None], 1e-15)
    return vn


def digest(*arrays, extra=''):
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.ascontiguousarray(a).tobytes())
    h.update(extra.encode())
    return h.hexdigest()
