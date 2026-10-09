"""Putting-green surfaces.

A green is a height map z = h(x, y) sampled on a regular grid (all units metres).
Phase 1 builds synthetic greens from formulas; later phases will build the same
object from LiDAR / photogrammetry point clouds, so the simulator never needs
to know where the surface came from.
"""
import numpy as np
from scipy.interpolate import RectBivariateSpline

FT = 0.3048                 # metres per foot
STIMP_RELEASE_SPEED = 1.83  # m/s, ball speed leaving a Stimpmeter ramp


class Green:
    """Height map on a regular grid, with smooth height and slope lookup.

    x, y : 1-D grid coordinates (m); z : heights with shape (len(x), len(y)) (m).
    stimp_ft : green speed as a Stimpmeter reading in feet (typical 8-13).
    """

    def __init__(self, x, y, z, stimp_ft=10.0):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.z = np.asarray(z, dtype=float)
        self.stimp_ft = stimp_ft
        self._spline = RectBivariateSpline(self.x, self.y, self.z, kx=3, ky=3)

    @classmethod
    def from_function(cls, height_fn, size=(6.0, 6.0), resolution=0.05, stimp_ft=10.0):
        """Sample height_fn(X, Y) on a size[0] x size[1] metre grid."""
        x = np.arange(0.0, size[0] + 1e-9, resolution)
        y = np.arange(0.0, size[1] + 1e-9, resolution)
        X, Y = np.meshgrid(x, y, indexing="ij")
        return cls(x, y, height_fn(X, Y), stimp_ft=stimp_ft)

    @property
    def rolling_decel(self):
        """Deceleration (m/s^2) from grass friction, derived from the Stimpmeter.

        On a flat green a ball released at 1.83 m/s rolls stimp distance S,
        so the constant deceleration is v^2 / (2 S).
        """
        return STIMP_RELEASE_SPEED ** 2 / (2.0 * self.stimp_ft * FT)

    def height(self, x, y):
        return self._spline.ev(x, y)

    def gradient(self, x, y):
        """Slope (dz/dx, dz/dy) at the given points; 0.02 means a 2 % slope."""
        return self._spline.ev(x, y, dx=1), self._spline.ev(x, y, dy=1)

    def contains(self, x, y):
        return (x >= self.x[0]) & (x <= self.x[-1]) & (y >= self.y[0]) & (y <= self.y[-1])


# --- synthetic surfaces (height functions for Green.from_function) ---------

def planar(slope_x_pct=0.0, slope_y_pct=0.0):
    """A tilted plane: height rises slope_x_pct % per metre along x, etc."""
    return lambda X, Y: (slope_x_pct * X + slope_y_pct * Y) / 100.0


def bump(center, height_cm, radius_m):
    """A Gaussian mound (negative height_cm gives a hollow)."""
    cx, cy = center
    return lambda X, Y: height_cm / 100.0 * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * radius_m ** 2))


def combine(*height_fns):
    return lambda X, Y: sum(f(X, Y) for f in height_fns)
