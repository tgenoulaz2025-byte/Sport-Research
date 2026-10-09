"""Figures: green map with the ideal line, and the make/miss map."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .physics import CUP_RADIUS


def plot_green(green, ball, hole, line, title, out_path, make_prob=None):
    fig, ax = plt.subplots(figsize=(7, 6))
    X, Y = np.meshgrid(green.x, green.y, indexing="ij")
    cf = ax.contourf(X, Y, 100 * green.z, levels=20, cmap="Greens")
    fig.colorbar(cf, ax=ax, label="height (cm)")

    step = max(1, len(green.x) // 15)
    xs, ys = green.x[::step], green.y[::step]
    QX, QY = np.meshgrid(xs, ys, indexing="ij")
    gx, gy = green.gradient(QX.ravel(), QY.ravel())
    ax.quiver(QX, QY, -gx.reshape(QX.shape), -gy.reshape(QX.shape), color="0.35",
              alpha=0.6, width=0.003)  # arrows point downhill

    ax.plot(*zip(ball, hole), "k--", lw=1, label="straight line")
    ax.plot(line.path[:, 0], line.path[:, 1], color="tab:red", lw=2, label="ideal path")
    ax.add_patch(plt.Circle(hole, CUP_RADIUS, color="black"))
    ax.plot(*ball, "o", ms=8, mfc="white", mec="black", label="ball")

    side = "left" if line.aim_offset_cm >= 0 else "right"
    text = (f"Aim {abs(line.aim_offset_cm):.0f} cm {side} of cup\n"
            f"Start speed {line.speed:.2f} m/s, {line.distance_m:.1f} m putt")
    if make_prob is not None:
        text += f"\nMake chance (typical golfer): {100 * make_prob:.0f}%"
    ax.text(0.02, 0.98, text, transform=ax.transAxes, va="top",
            bbox=dict(boxstyle="round", fc="white", alpha=0.9))
    ax.set(title=title, xlabel="x (m)", ylabel="y (m)", aspect="equal")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def plot_make_map(line, title, out_path):
    s = line.sweep
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.pcolormesh(s["aims"], s["speeds"], s["made"].T, cmap="Greens", shading="nearest", vmin=0, vmax=1.4)
    ax.plot(line.aim_deg, line.speed, "r*", ms=14, label="ideal line")
    ax.set(title=title, xlabel="aim angle (deg, + = left)", ylabel="start speed (m/s)")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
