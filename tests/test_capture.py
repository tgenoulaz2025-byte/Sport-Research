"""Checks for the capture side: local frame maths and surface fitting.

Run:  python3 -m pytest tests/      (or simply: python3 tests/test_capture.py)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from capture.surface import LocalFrame, fit_surface, tilt  # noqa: E402


def test_local_frame_round_trip():
    rng = np.random.default_rng(1)
    up = np.array([0.1, -0.9, 0.2])
    frame = LocalFrame(up, np.array([1.0, 0.0, 0.3]), origin=[1, 2, 3], scale=7.5)
    P = rng.normal(size=(50, 3))
    assert np.allclose(frame.to_world(frame.to_local(P)), P)
    # moving along 'up' in the world only changes local z
    d = frame.to_local(np.array([1, 2, 3]) + up / np.linalg.norm(up))[0]
    assert np.allclose(d, [0, 0, 7.5])


def test_fit_recovers_slope_despite_noise_and_outliers():
    rng = np.random.default_rng(2)
    x, y = rng.uniform(-10, 10, (2, 400))
    z = 0.02 * x - 0.01 * y + rng.normal(0, 0.05, 400)   # 2 % / -1 % slope, 5 cm noise
    z[:20] += 1.0                                          # 5 % gross outliers
    h, keep, rms = fit_surface(np.column_stack([x, y, z]), degree=1)
    assert not keep[:20].any()
    gx = (h(np.array([1.0]), np.array([0.0])) - h(np.array([0.0]), np.array([0.0])))[0]
    assert abs(gx - 0.02) < 0.002
    assert rms < 0.06


def test_tilt_angle():
    up = np.array([0, 0, 1.0])
    t = tilt(up, 2.0, np.array([1.0, 0, 0]))
    assert np.isclose(np.degrees(np.arccos(t @ up)), 2.0)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
