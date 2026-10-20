"""Pinhole camera shared by the three scenes (each scene module supplies its own constants)."""
import numpy as np


class Camera:
    def __init__(self, eye, forward, right, up, focal, cx, cy, width, height):
        self.eye = np.asarray(eye, float)
        self.F, self.R, self.U = (np.asarray(a, float) for a in (forward, right, up))
        self.focal, self.cx, self.cy = float(focal), float(cx), float(cy)
        self.W, self.H = int(width), int(height)

    def project(self, P):
        """World points (..., 3) -> screen x, y and camera depth."""
        q = np.asarray(P, float) - self.eye
        z = q @ self.F
        return self.cx + self.focal * (q @ self.R) / z, self.cy - self.focal * (q @ self.U) / z, z

    def jacobian(self, P, e_u, e_v):
        """d(screen)/d(u, v) at world points P for surface directions e_u, e_v: (..., 2, 2)."""
        q = np.asarray(P, float) - self.eye
        z = (q @ self.F)[..., None]
        qr, qu = (q @ self.R)[..., None], (q @ self.U)[..., None]
        dsx = self.focal * (self.R * z - qr * self.F) / z ** 2
        dsy = -self.focal * (self.U * z - qu * self.F) / z ** 2
        J = np.empty(q.shape[:-1] + (2, 2))
        J[..., 0, 0] = (dsx * e_u).sum(-1)
        J[..., 0, 1] = (dsx * e_v).sum(-1)
        J[..., 1, 0] = (dsy * e_u).sum(-1)
        J[..., 1, 1] = (dsy * e_v).sum(-1)
        return J

    def inside(self, x, y, z, margin=2):
        return (z > .15) & (x > margin) & (x < self.W - margin) & (y > margin) & (y < self.H - margin)
