"""Sanity checks for the physics and solver.

Run:  python3 -m pytest tests/      (or simply: python3 tests/test_physics.py)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from putting import Green, find_best_line, planar, simulate  # noqa: E402
from putting.green import FT, STIMP_RELEASE_SPEED  # noqa: E402
from putting.physics import capture_speed  # noqa: E402

FLAT = Green.from_function(planar(), size=(6, 3), stimp_ft=10)
BALL, HOLE = (0.5, 1.5), (4.0, 1.5)


def test_stimpmeter_roll_distance():
    # a ball leaving the Stimpmeter ramp rolls exactly the stimp reading on a flat green
    res = simulate(FLAT, BALL, (5.9, 1.5), 0.0, STIMP_RELEASE_SPEED, capture=False)
    rolled = res.final_pos[0, 0] - BALL[0]
    assert abs(rolled - 10 * FT) < 0.02


def test_flat_green_goes_straight():
    res = simulate(FLAT, BALL, HOLE, 0.0, 1.5, capture=False)
    assert np.allclose(res.paths[:, 0, 1], 1.5, atol=1e-9)


def test_capture_speed_dead_centre():
    assert 1.5 < capture_speed(0.0) < 1.8  # published values are ~1.6 m/s
    assert capture_speed(0.054) == 0.0


def test_too_fast_lips_out_and_gentle_drops():
    flat_speed = np.sqrt(2 * FLAT.rolling_decel * 3.5)
    gentle = simulate(FLAT, BALL, HOLE, 0.0, flat_speed + 0.1, record_paths=False)
    rocket = simulate(FLAT, BALL, HOLE, 0.0, 4.0, record_paths=False)
    assert gentle.holed[0] and not rocket.holed[0]


def test_side_slope_aims_uphill():
    # height rises toward +y, which is the golfer's left when putting along +x
    green = Green.from_function(planar(slope_y_pct=2.0), size=(5, 3), stimp_ft=10)
    line = find_best_line(green, BALL, HOLE)
    assert line.aim_offset_cm > 5
    res = simulate(green, BALL, HOLE, line.aim_deg, line.speed, record_paths=False)
    assert res.holed[0]


def test_uphill_needs_more_speed():
    uphill = Green.from_function(planar(slope_x_pct=2.0), size=(6, 3), stimp_ft=10)
    up = find_best_line(uphill, BALL, HOLE)
    flat = find_best_line(FLAT, BALL, HOLE)
    assert up.speed > flat.speed
    assert abs(up.aim_offset_cm) < 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
