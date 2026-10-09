"""Turn a reconstructed point cloud into a levelled, metric height map (Green).

Steps: estimate gravity, build a local frame (origin at the hole, z up, metres),
then fit a smooth surface to the points on the green.
"""
import numpy as np

from putting.green import Green


# --- gravity ---------------------------------------------------------------

def up_from_gimbal(model):
    """Gravity 'up' from a gimbal-stabilised camera (drone footage).

    The gimbal keeps the horizon level, so every camera's sideways (x) axis is
    horizontal: up is the direction perpendicular to all of them. Accuracy
    depends on how much the camera turns during the clip; `bootstrap_deg`
    reports the 95 % spread of the estimate.
    """
    names = sorted(model.views)
    X = np.array([model.views[n].R[0] for n in names])
    Y = np.array([model.views[n].R[1] for n in names])  # image 'down' axis

    def solve(rows):
        u = np.linalg.svd(rows)[2][2]
        return u * -np.sign(Y.mean(0) @ u)

    up = solve(X)
    rng = np.random.default_rng(0)
    spread = [np.degrees(np.arccos(np.clip(solve(X[rng.choice(len(X), len(X))]) @ up, -1, 1)))
              for _ in range(300)]
    return up, float(np.percentile(spread, 95))


def up_from_level_flight(model):
    """Alternative: assume the drone held altitude, so its flight path is horizontal."""
    names = sorted(model.views)
    C = np.array([model.views[n].center for n in names])
    X = np.array([model.views[n].R[0] for n in names]).mean(0)
    Y = np.array([model.views[n].R[1] for n in names]).mean(0)
    flight = np.linalg.svd(C - C.mean(0))[2][0]
    up = np.cross(X, flight)
    up /= np.linalg.norm(up)
    return up * -np.sign(Y @ up)


def tilt(up, angle_deg, axis):
    """Rotate `up` by angle_deg about `axis` (for sensitivity tests)."""
    axis = axis / np.linalg.norm(axis)
    a = np.radians(angle_deg)
    return (up * np.cos(a) + np.cross(axis, up) * np.sin(a) + axis * (axis @ up) * (1 - np.cos(a)))


# --- local frame -------------------------------------------------------------

class LocalFrame:
    """World (COLMAP units) -> local metres: origin at `origin`, z = up, x = `forward` levelled."""

    def __init__(self, up, forward, origin, scale):
        z = up / np.linalg.norm(up)
        x = forward - (forward @ z) * z
        x /= np.linalg.norm(x)
        self.R = np.stack([x, np.cross(z, x), z])  # rows: local axes in world coords
        self.origin = np.asarray(origin, float)
        self.scale = scale  # metres per COLMAP unit

    def to_local(self, P):
        return (np.atleast_2d(P) - self.origin) @ self.R.T * self.scale

    def to_world(self, Q):
        return np.atleast_2d(Q) / self.scale @ self.R + self.origin


# --- surface fit ---------------------------------------------------------------

def _design(x, y, degree):
    return np.stack([x ** i * y ** j for i in range(degree + 1) for j in range(degree + 1 - i)], axis=1)


def fit_surface(points_local, degree=3, n_sigma=2.5, iters=5):
    """Robust polynomial fit z = h(x, y). Returns (height_fn, inlier mask, rms residual m)."""
    x, y, z = points_local.T
    keep = np.ones(len(z), bool)
    for _ in range(iters):
        coef = np.linalg.lstsq(_design(x[keep], y[keep], degree), z[keep], rcond=None)[0]
        resid = z - _design(x, y, degree) @ coef
        sigma = 1.4826 * np.median(np.abs(resid[keep] - np.median(resid[keep])))
        keep = np.abs(resid) < n_sigma * sigma
    rms = float(np.sqrt(np.mean(resid[keep] ** 2)))

    def height_fn(X, Y):
        return (_design(X.ravel(), Y.ravel(), degree) @ coef).reshape(X.shape)

    return height_fn, keep, rms


def green_from_points(points_local, stimp_ft=10.0, degree=3, margin=0.5, resolution=0.1):
    """Fit the surface and sample it as a Green over the points' extent."""
    height_fn, keep, rms = fit_surface(points_local, degree)
    lo = points_local[keep, :2].min(0) - margin
    hi = points_local[keep, :2].max(0) + margin
    x = np.arange(lo[0], hi[0], resolution)
    y = np.arange(lo[1], hi[1], resolution)
    X, Y = np.meshgrid(x, y, indexing="ij")
    return Green(x, y, height_fn(X, Y), stimp_ft=stimp_ft), keep, rms
