"""Find the ideal putting line on a green.

"Ideal" here means: the ball's path runs through the centre of the cup and,
if the cup weren't there, would stop `past_m` metres beyond it (0.4 m / ~17 in
is a common coaching target: firm enough to hold the line, soft enough to drop).
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .physics import simulate


@dataclass
class PuttLine:
    aim_deg: float          # + = left of the hole, as seen from behind the ball
    speed: float            # initial ball speed, m/s
    aim_offset_cm: float    # where to aim: cm left (+) / right (-) of the cup
    distance_m: float
    path: np.ndarray        # (steps, 2) the ideal ball path
    sweep: dict             # aim/speed grid with make/miss map, for plotting


def _cost(res, past_m):
    # 1 cm of miss distance ~ 5 cm of pace error
    return (res.min_dist / 0.01) ** 2 + ((res.past_hole - past_m) / 0.05) ** 2


def find_best_line(green, ball, hole, past_m=0.4, max_aim_deg=20.0, n_aim=81, n_speed=41):
    ball, hole = np.asarray(ball, float), np.asarray(hole, float)
    dist = float(np.linalg.norm(hole - ball))
    flat_speed = np.sqrt(2 * green.rolling_decel * (dist + past_m))

    # 1) coarse sweep of every (aim, speed) pair in one vectorised run
    aims = np.linspace(-max_aim_deg, max_aim_deg, n_aim)
    speeds = np.linspace(0.5 * flat_speed, 1.8 * flat_speed, n_speed)
    A, S = np.meshgrid(aims, speeds, indexing="ij")
    res = simulate(green, ball, hole, A, S, capture=False, record_paths=False)
    cost = _cost(res, past_m).reshape(A.shape)
    i, j = np.unravel_index(np.argmin(cost), cost.shape)

    # 2) refine the best grid cell
    def objective(x):
        r = simulate(green, ball, hole, x[0], x[1], capture=False, record_paths=False)
        return float(_cost(r, past_m)[0])

    opt = minimize(objective, x0=[A[i, j], S[i, j]], method="Nelder-Mead",
                   options={"xatol": 0.01, "fatol": 1e-3, "initial_simplex":
                            [[A[i, j], S[i, j]], [A[i, j] + 0.5, S[i, j]], [A[i, j], S[i, j] * 1.03]]})
    aim, speed = opt.x
    best = simulate(green, ball, hole, aim, speed, capture=False)

    # 3) fine make/miss map around the ideal line ("how much room for error")
    map_aims = aim + np.linspace(-4, 4, 121)
    map_speeds = speed * np.linspace(0.75, 1.35, 81)
    A, S = np.meshgrid(map_aims, map_speeds, indexing="ij")
    made = simulate(green, ball, hole, A, S, record_paths=False).holed.reshape(A.shape)

    return PuttLine(
        aim_deg=float(aim),
        speed=float(speed),
        aim_offset_cm=float(100 * dist * np.tan(np.radians(aim))),
        distance_m=dist,
        path=best.paths[:, 0, :],
        sweep={"aims": map_aims, "speeds": map_speeds, "made": made},
    )


def make_probability(green, ball, hole, aim_deg, speed, aim_sd_deg=1.0, speed_sd_pct=4.0,
                     n=2000, seed=0):
    """Share of putts holed when the golfer's aim and pace vary randomly.

    The default spreads are placeholders for a decent amateur; phase 3 should
    measure them from real putts.
    """
    rng = np.random.default_rng(seed)
    aims = aim_deg + rng.normal(0, aim_sd_deg, n)
    speeds = speed * (1 + rng.normal(0, speed_sd_pct / 100, n))
    res = simulate(green, ball, hole, aims, speeds, record_paths=False)
    return float(res.holed.mean())
