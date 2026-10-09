"""Read a COLMAP sparse model exported as text (cameras.txt, images.txt, points3D.txt)."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def quat_to_rot(qw, qx, qy, qz):
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
    ])


@dataclass
class View:
    name: str
    R: np.ndarray   # world -> camera rotation
    t: np.ndarray   # world -> camera translation

    @property
    def center(self):
        return -self.R.T @ self.t


@dataclass
class Model:
    K: np.ndarray        # 3x3 intrinsics (radial distortion ignored, it is tiny for these cameras)
    size: tuple          # (width, height)
    views: dict          # name -> View
    points: np.ndarray   # (n, 3)
    colors: np.ndarray   # (n, 3) uint8
    errors: np.ndarray   # (n,) reprojection error, px
    track_len: np.ndarray

    def project(self, view_name, X):
        """Pixel coordinates (n, 2) and depth (n,) of world points in one view."""
        v = self.views[view_name]
        Xc = X @ v.R.T + v.t
        uv = Xc @ self.K.T
        return uv[:, :2] / uv[:, 2:3], Xc[:, 2]


def _data_lines(path):
    return [l for l in Path(path).read_text().splitlines() if l and not l.startswith("#")]


def load_model(model_dir):
    d = Path(model_dir)
    cam = _data_lines(d / "cameras.txt")[0].split()
    model, w, h, params = cam[1], int(cam[2]), int(cam[3]), list(map(float, cam[4:]))
    if model in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL"):
        f, cx, cy = params[:3]
        fx = fy = f
    else:  # PINHOLE, OPENCV, ...
        fx, fy, cx, cy = params[:4]
    K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]])

    views = {}
    lines = _data_lines(d / "images.txt")
    for header in lines[0::2]:
        p = header.split()
        q, t = list(map(float, p[1:5])), np.array(list(map(float, p[5:8])))
        views[p[9]] = View(p[9], quat_to_rot(*q), t)

    pts, cols, errs, tl = [], [], [], []
    for l in _data_lines(d / "points3D.txt"):
        p = l.split()
        pts.append(list(map(float, p[1:4])))
        cols.append(list(map(int, p[4:7])))
        errs.append(float(p[7]))
        tl.append((len(p) - 8) // 2)
    return Model(K, (w, h), views, np.array(pts), np.array(cols, np.uint8), np.array(errs), np.array(tl))
