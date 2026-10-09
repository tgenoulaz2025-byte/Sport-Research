"""Find the flag in 3-D: bright yellow blobs in each frame, kept only if they
triangulate to one consistent 3-D point across frames (RANSAC).

The flag marks the hole (straight below it) and gives a scale reference,
since flagsticks are about 7 ft (2.13 m) tall.
"""
import cv2
import numpy as np

FLAG_CENTER_HEIGHT_M = 1.95   # 7 ft stick, flag cloth (~0.5 m) at the top


def yellow_blobs(image_bgr, min_sat=215, min_val=190, hue=(24, 38), area=(6, 4000)):
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (hue[0], min_sat, min_val), (hue[1], 255, 255))
    n, _, stats, cents = cv2.connectedComponentsWithStats(mask)
    return [cents[i] for i in range(1, n) if area[0] <= stats[i, 4] <= area[1]]


def _triangulate(model, obs):
    """Linear (DLT) triangulation from [(view_name, (u, v)), ...]."""
    rows = []
    for name, (u, v) in obs:
        view = model.views[name]
        P = model.K @ np.hstack([view.R, view.t[:, None]])
        rows += [u * P[2] - P[0], v * P[2] - P[1]]
    X = np.linalg.svd(np.array(rows))[2][-1]
    return X[:3] / X[3]


def locate_flag(model, images, px_tol=12.0, iters=3000, seed=0):
    """images: dict view_name -> BGR image. Returns (3-D point, inlier observations)."""
    cands = {n: yellow_blobs(im) for n, im in images.items() if n in model.views}
    names = [n for n, c in cands.items() if c]
    rng = np.random.default_rng(seed)
    best_X, best_obs = None, []
    for _ in range(iters):
        a, b = rng.choice(names, 2, replace=False)
        X = _triangulate(model, [(a, cands[a][rng.integers(len(cands[a]))]),
                                 (b, cands[b][rng.integers(len(cands[b]))])])
        obs = []
        for n in names:
            uv, depth = model.project(n, X[None])
            if depth[0] <= 0:
                continue
            d = [np.linalg.norm(c - uv[0]) for c in cands[n]]
            if min(d) < px_tol:
                obs.append((n, cands[n][int(np.argmin(d))]))
        if len(obs) > len(best_obs):
            best_X, best_obs = X, obs
    return _triangulate(model, best_obs), best_obs
