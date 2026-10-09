"""Phase 1 demo: find the ideal line on synthetic greens and save figures to results/.

Run from the repo root:  python3 scripts/demo_phase1.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from putting import Green, bump, combine, find_best_line, make_probability, planar  # noqa: E402
from putting.plot import plot_green, plot_make_map  # noqa: E402

SCENARIOS = [
    {
        "name": "side_slope",
        "title": "3 m putt, 2% side slope (high side on the left)",
        "green": Green.from_function(planar(slope_y_pct=2.0), size=(5, 3), stimp_ft=10),
        "ball": (1.0, 1.5),
        "hole": (4.0, 1.5),
    },
    {
        "name": "ridge_and_tilt",
        "title": "5 m putt over a mound, 1% uphill",
        "green": Green.from_function(
            combine(planar(slope_x_pct=1.0, slope_y_pct=0.5), bump((3.5, 2.6), 6, 0.8)),
            size=(7, 5), stimp_ft=11),
        "ball": (1.0, 2.5),
        "hole": (6.0, 2.5),
    },
]


def main():
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    for sc in SCENARIOS:
        line = find_best_line(sc["green"], sc["ball"], sc["hole"])
        p = make_probability(sc["green"], sc["ball"], sc["hole"], line.aim_deg, line.speed)
        side = "left" if line.aim_offset_cm >= 0 else "right"
        print(f"{sc['name']}: aim {abs(line.aim_offset_cm):.1f} cm {side}, "
              f"speed {line.speed:.2f} m/s, make chance {100 * p:.0f}%")
        plot_green(sc["green"], sc["ball"], sc["hole"], line, sc["title"],
                   out / f"{sc['name']}_line.png", make_prob=p)
        plot_make_map(line, f"{sc['title']}: which aim/speed combos go in",
                      out / f"{sc['name']}_make_map.png")


if __name__ == "__main__":
    main()
