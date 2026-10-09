"""Phase 1b: run the whole pipeline on a real green filmed by someone else.

Video: "Leon Golf & Country Club, Leon Iowa.. Drone flyover holes 1 thru 9",
by Idyllic Golfer, CC BY 3.0, via Wikimedia Commons:
https://commons.wikimedia.org/wiki/File:Leon_Golf_%26_Country_Club,_Leon_Iowa.._Drone_flyover_holes_1_thru_9.webm
Segment used: 3:05-3:17 (approach to a green; the flag shows "5").

The video and the reconstruction are not stored in the repo. To rebuild them, see
scripts/reconstruct_video.sh. Then run (repo root):
    python3 scripts/demo_online_video.py ../data/online/green_0305
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from capture.colmap_model import load_model  # noqa: E402
from capture.flag import FLAG_CENTER_HEIGHT_M, locate_flag  # noqa: E402
from capture.surface import (LocalFrame, fit_surface, green_from_points, tilt,  # noqa: E402
                             up_from_gimbal)
from putting import find_best_line, make_probability  # noqa: E402
from putting.physics import BALL_RADIUS  # noqa: E402
from putting.plot import plot_green  # noqa: E402

REF_FRAME = "f_059.jpg"                 # frame where the whole green is visible
GREEN_ELLIPSE = (1016, 720, 333, 75)    # hand-drawn outline of the green in REF_FRAME (cx, cy, a, b px)
STIMP_FT = 9.0                          # unknown for this course; typical public-course value
PUTT_LENGTH_M = 5.0
COLORS_BGR = [(40, 40, 230), (230, 120, 30), (200, 40, 200)]


def main(work_dir):
    work = Path(work_dir)
    out = ROOT / "results" / "online_video"
    out.mkdir(parents=True, exist_ok=True)

    model = load_model(work / "model_txt")
    images = {n: cv2.imread(str(work / "images" / n)) for n in sorted(model.views)}
    names = sorted(model.views)
    centers = np.array([model.views[n].center for n in names])

    # 1. gravity, flag (= hole), green points
    up, up_spread = up_from_gimbal(model)
    flag, flag_obs = locate_flag(model, images)
    uv, depth = model.project(REF_FRAME, model.points)
    cx, cy, a, b = GREEN_ELLIPSE
    on_green = ((depth > 0) & (((uv[:, 0] - cx) / a) ** 2 + ((uv[:, 1] - cy) / b) ** 2 < 1)
                & (model.errors < 1.5) & (model.track_len >= 3))
    print(f"gravity from gimbal: ±{up_spread:.1f}° (95%); flag seen in {len(flag_obs)} frames; "
          f"{on_green.sum()} points on the green")

    # 2. metric, levelled frame with the hole at the origin; scale from flag height
    forward = centers[-1] - centers[0]
    unit = LocalFrame(up, forward, flag, 1.0)
    h_unit, _, _ = fit_surface(unit.to_local(model.points[on_green]), degree=2)
    scale = FLAG_CENTER_HEIGHT_M / -h_unit(np.zeros(1), np.zeros(1))[0]
    hole_world = unit.to_world([[0, 0, h_unit(np.zeros(1), np.zeros(1))[0]]])[0]
    frame = LocalFrame(up, forward, hole_world, scale)
    pts = frame.to_local(model.points[on_green])
    print(f"scale {scale:.2f} m per model unit; drone path {scale * np.linalg.norm(forward):.0f} m")

    green, keep, rms = green_from_points(pts, stimp_ft=STIMP_FT, degree=2)
    gx, gy = green.gradient(pts[keep, 0], pts[keep, 1])
    slope = 100 * np.hypot(gx, gy)
    print(f"surface fit: {keep.sum()} inliers, rms {100 * rms:.1f} cm; "
          f"slope on green {np.median(slope):.1f}% median ({np.percentile(slope, 10):.1f}-{np.percentile(slope, 90):.1f}%)")

    # 3. putts from three spots on the green, ~5 m from the hole
    hull = cv2.convexHull(pts[keep, :2].astype(np.float32))
    inside = lambda p: cv2.pointPolygonTest(hull, (float(p[0]), float(p[1])), True) > 1.0  # noqa: E731
    angles = [a for a in np.radians(np.arange(0, 360, 5))
              if inside(PUTT_LENGTH_M * np.array([np.cos(a), np.sin(a)]))]
    picks = [angles[0], angles[len(angles) // 2], angles[-1]] if len(angles) >= 3 else angles
    balls = [PUTT_LENGTH_M * np.array([np.cos(a), np.sin(a)]) for a in picks]
    hole = np.zeros(2)

    lines, report = [], []
    for i, ball in enumerate(balls):
        line = find_best_line(green, ball, hole)
        p = make_probability(green, ball, hole, line.aim_deg, line.speed)
        lines.append(line)
        side = "left" if line.aim_offset_cm >= 0 else "right"
        report.append(f"putt {i + 1}: aim {abs(line.aim_offset_cm):.0f} cm {side}, "
                      f"speed {line.speed:.2f} m/s, make chance {100 * p:.0f}%")
        print(report[-1])
        plot_green(green, ball, hole, line, f"Leon G&CC green, from drone video: putt {i + 1}",
                   out / f"putt{i + 1}_map.png", make_prob=p)

    # 4. sensitivity: how much do aim points move if gravity is off by the measured uncertainty?
    print(f"\ngravity sensitivity (tilt up-vector by ±{up_spread:.1f}°):")
    side_axis, fwd_axis = frame.R[0], frame.R[1]
    for i, ball in enumerate(balls):
        shifts = []
        for axis in (side_axis, fwd_axis):
            for sgn in (-1, 1):
                f2 = LocalFrame(tilt(up, sgn * up_spread, axis), forward, hole_world, scale)
                g2, _, _ = green_from_points(f2.to_local(model.points[on_green]), stimp_ft=STIMP_FT, degree=2)
                shifts.append(find_best_line(g2, ball, hole).aim_offset_cm - lines[i].aim_offset_cm)
        print(f"  putt {i + 1}: aim point moves by up to {max(map(abs, shifts)):.0f} cm")

    # 5. draw the predicted paths onto the video frames
    for ref in (REF_FRAME, names[int(len(names) * 0.8)]):
        img = images[ref].copy()
        for line, color in zip(lines, COLORS_BGR):
            xy = line.path
            z = green.height(xy[:, 0], xy[:, 1]) + BALL_RADIUS
            uvp, d = model.project(ref, frame.to_world(np.column_stack([xy, z])))
            uvp = uvp[d > 0].astype(np.int32)
            cv2.polylines(img, [uvp], False, color, 3, cv2.LINE_AA)
            cv2.circle(img, tuple(uvp[0]), 9, (255, 255, 255), -1)
            cv2.circle(img, tuple(uvp[0]), 9, color, 2)
        cv2.imwrite(str(out / f"overlay_{ref.replace('.jpg', '')}.jpg"), img)

    (out / "summary.txt").write_text("\n".join(report) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "data" / "online" / "green_0305")
