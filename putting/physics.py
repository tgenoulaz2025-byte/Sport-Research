"""Ball-roll physics on a sloped green.

Model (small-slope approximation, standard in putting literature):
    a = -(5/7) g grad h  -  rho * v_hat
The 5/7 factor is for a solid sphere rolling without slipping; rho is the
constant grass deceleration derived from the Stimpmeter (see Green).

Hole capture uses a simple free-fall test: while the ball's centre crosses the
cup along a chord, it must drop by one ball radius before reaching the far
edge. That gives a maximum capture speed of about 1.64 m/s for a dead-centre
putt, in line with published values (~1.6 m/s).

All balls are simulated together (vectorised), so sweeps and Monte Carlo runs
of thousands of putts take seconds.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np

G = 9.81
ROLL_FACTOR = 5.0 / 7.0
BALL_RADIUS = 0.02135   # m (42.67 mm diameter)
CUP_RADIUS = 0.054      # m (108 mm diameter)
STOP_SPEED = 0.01       # m/s, treat the ball as stopped below this


def capture_speed(d):
    """Max speed (m/s) at which a ball passing d metres from the cup centre drops."""
    chord = 2.0 * np.sqrt(np.clip(CUP_RADIUS ** 2 - d ** 2, 0.0, None))
    fall_time = np.sqrt(2.0 * BALL_RADIUS / G)
    return chord / fall_time


@dataclass
class RollResult:
    holed: np.ndarray            # (n,) bool
    final_pos: np.ndarray        # (n, 2)
    min_dist: np.ndarray         # (n,) closest approach of ball centre to cup centre (m)
    speed_at_min: np.ndarray     # (n,) speed at closest approach (m/s)
    past_hole: np.ndarray        # (n,) path length travelled after the closest approach (m)
    paths: Optional[np.ndarray]  # (steps, n, 2) or None


def initial_velocity(ball, hole, aim_deg, speed):
    """Velocity vectors for an aim angle relative to the straight ball->hole line.

    Positive aim_deg = aim LEFT of the hole (as seen standing behind the ball).
    """
    ball, hole = np.asarray(ball, float), np.asarray(hole, float)
    base = np.arctan2(*(hole - ball)[::-1])
    ang = base + np.radians(aim_deg)
    return np.stack([speed * np.cos(ang), speed * np.sin(ang)], axis=-1)


def simulate(green, ball, hole, aim_deg, speed, capture=True, record_paths=True,
             dt=0.01, max_time=30.0):
    """Roll n balls from `ball` with the given aims (deg) and speeds (m/s)."""
    aim_deg, speed = np.broadcast_arrays(np.atleast_1d(aim_deg).astype(float),
                                         np.atleast_1d(speed).astype(float))
    aim_deg, speed = aim_deg.ravel(), speed.ravel()
    n = aim_deg.size
    hole = np.asarray(hole, float)
    rho = green.rolling_decel

    def accel(p, v):
        gx, gy = green.gradient(p[:, 0], p[:, 1])
        sp = np.linalg.norm(v, axis=1, keepdims=True)
        return -ROLL_FACTOR * G * np.stack([gx, gy], axis=1) - rho * v / np.maximum(sp, 1e-9)

    pos = np.tile(np.asarray(ball, float), (n, 1))
    vel = initial_velocity(ball, hole, aim_deg, speed)
    moving = np.ones(n, bool)
    holed = np.zeros(n, bool)
    min_dist = np.linalg.norm(pos - hole, axis=1)
    speed_at_min = speed.copy()
    travelled = np.zeros(n)
    travelled_at_min = np.zeros(n)
    paths = [pos.copy()] if record_paths else None

    for _ in range(int(max_time / dt)):
        idx = np.flatnonzero(moving)
        if idx.size == 0:
            break
        p, v = pos[idx], vel[idx]

        # classic RK4 step for (position, velocity)
        k1v = accel(p, v);                         k1p = v
        k2v = accel(p + dt / 2 * k1p, v + dt / 2 * k1v); k2p = v + dt / 2 * k1v
        k3v = accel(p + dt / 2 * k2p, v + dt / 2 * k2v); k3p = v + dt / 2 * k2v
        k4v = accel(p + dt * k3p, v + dt * k3v);         k4p = v + dt * k3v
        pn = p + dt / 6 * (k1p + 2 * k2p + 2 * k3p + k4p)
        vn = v + dt / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)

        # closest approach to the cup centre along this step's segment
        seg = pn - p
        seg_len = np.linalg.norm(seg, axis=1)
        t = np.clip(np.einsum("ij,ij->i", hole - p, seg) / np.maximum(seg_len ** 2, 1e-12), 0, 1)
        d = np.linalg.norm(p + t[:, None] * seg - hole, axis=1)
        sp = np.linalg.norm(v, axis=1)

        closer = d < min_dist[idx]
        min_dist[idx[closer]] = d[closer]
        speed_at_min[idx[closer]] = sp[closer]
        travelled_at_min[idx[closer]] = travelled[idx[closer]] + t[closer] * seg_len[closer]
        travelled[idx] += seg_len

        done = (np.linalg.norm(vn, axis=1) < STOP_SPEED) | ~green.contains(pn[:, 0], pn[:, 1])
        if capture:
            caught = (d < CUP_RADIUS) & (sp < capture_speed(d))
            pn[caught] = hole
            vn[caught] = 0.0
            holed[idx[caught]] = True
            done |= caught

        pos[idx], vel[idx] = pn, vn
        moving[idx[done]] = False
        if record_paths:
            paths.append(pos.copy())

    return RollResult(
        holed=holed,
        final_pos=pos,
        min_dist=min_dist,
        speed_at_min=speed_at_min,
        past_hole=travelled - travelled_at_min,
        paths=np.array(paths) if record_paths else None,
    )
