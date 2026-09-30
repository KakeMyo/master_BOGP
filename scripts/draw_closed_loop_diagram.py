from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]


def add_box(ax, xy, width, height, title, body, facecolor, edgecolor="#263238"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.035,rounding_size=0.035",
        linewidth=1.8,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(box)
    x, y = xy
    ax.text(
        x + width / 2,
        y + height * 0.66,
        title,
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#102027",
    )
    ax.text(
        x + width / 2,
        y + height * 0.34,
        body,
        ha="center",
        va="center",
        fontsize=10,
        color="#263238",
        linespacing=1.35,
    )


def add_arrow(ax, start, end, label=None, curve=0.0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=18,
        linewidth=2.0,
        color="#37474f",
        connectionstyle=f"arc3,rad={curve}",
    )
    ax.add_patch(arrow)
    if label:
        x = (start[0] + end[0]) / 2
        y = (start[1] + end[1]) / 2
        ax.text(
            x,
            y + 0.18,
            label,
            ha="center",
            va="center",
            fontsize=9,
            color="#455a64",
            bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec="none", alpha=0.85),
        )


def add_elbow_arrow(ax, points, label=None, label_xy=None):
    """Draw an orthogonal feedback arrow outside the main vertical flow."""

    if len(points) < 2:
        return
    xs = [point[0] for point in points[:-1]]
    ys = [point[1] for point in points[:-1]]
    ax.plot(xs, ys, linewidth=2.0, color="#37474f")
    arrow = FancyArrowPatch(
        points[-2],
        points[-1],
        arrowstyle="-|>",
        mutation_scale=18,
        linewidth=2.0,
        color="#37474f",
    )
    ax.add_patch(arrow)
    if label and label_xy:
        ax.text(
            label_xy[0],
            label_xy[1],
            label,
            ha="center",
            va="center",
            fontsize=9,
            color="#455a64",
            bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec="none", alpha=0.9),
        )


def main() -> int:
    output_dir = ROOT / "outputs" / "diagrams"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11.5, 10.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    colors = {
        "state": "#e3f2fd",
        "bo": "#fff3e0",
        "action": "#ede7f6",
        "plant": "#e8f5e9",
        "stats": "#fce4ec",
        "reward": "#fffde7",
        "history": "#eceff1",
    }

    box_x = 3.35
    box_w = 3.3
    box_h = 1.05
    y_positions = {
        "state": 9.85,
        "bo": 8.25,
        "action": 6.65,
        "plant": 5.05,
        "stats": 3.45,
        "reward": 1.85,
        "history": 0.35,
    }

    add_box(
        ax,
        (box_x, y_positions["state"]),
        box_w,
        box_h,
        "State Observation",
        "x = [tau, HV, DeltaHV,\nDiversity, Tree size, Stagnation]",
        colors["state"],
    )
    add_box(
        ax,
        (box_x, y_positions["bo"]),
        box_w,
        box_h,
        "Contextual BO Controller",
        "per-k GP surrogate\n+ Expected Improvement",
        colors["bo"],
    )
    add_box(
        ax,
        (box_x, y_positions["action"]),
        box_w,
        box_h,
        "Action Output",
        "u = (p_c, p_m, k)\nrates + update period",
        colors["action"],
    )
    add_box(
        ax,
        (box_x, y_positions["plant"]),
        box_w,
        box_h,
        "Multi-objective GP Plant",
        "run k generations\ncrossover / mutation / NSGA-II",
        colors["plant"],
    )
    add_box(
        ax,
        (box_x, y_positions["stats"]),
        box_w,
        box_h,
        "Interval Statistics",
        "DeltaHV_rate, mean Diversity,\nHV, Tree size, Stagnation",
        colors["stats"],
    )
    add_box(
        ax,
        (box_x, y_positions["reward"]),
        box_w,
        box_h,
        "Reward Computation",
        "r = progress + diversity\n- control cost",
        colors["reward"],
    )
    add_box(
        ax,
        (box_x, y_positions["history"]),
        box_w,
        box_h,
        "BO History Update",
        "D_k <- (x, p_c, p_m, k, r)",
        colors["history"],
    )

    center_x = box_x + box_w / 2
    for upper, lower, label in [
        ("state", "bo", "context x"),
        ("bo", "action", "maximize EI"),
        ("action", "plant", "hold p_c, p_m for k generations"),
        ("plant", "stats", "population + metrics"),
        ("stats", "reward", "interval summary"),
        ("reward", "history", "reward r"),
    ]:
        add_arrow(
            ax,
            (center_x, y_positions[upper]),
            (center_x, y_positions[lower] + box_h),
            label,
        )

    # Outer feedback arrows make the closed loop explicit without crossing blocks.
    left_margin = 0.95
    right_margin = 9.05
    add_elbow_arrow(
        ax,
        [
            (box_x, y_positions["plant"] + box_h / 2),
            (left_margin, y_positions["plant"] + box_h / 2),
            (left_margin, y_positions["state"] + box_h / 2),
            (box_x, y_positions["state"] + box_h / 2),
        ],
        "next state",
        (left_margin, 7.75),
    )
    add_elbow_arrow(
        ax,
        [
            (box_x + box_w, y_positions["history"] + box_h / 2),
            (right_margin, y_positions["history"] + box_h / 2),
            (right_margin, y_positions["bo"] + box_h / 2),
            (box_x + box_w, y_positions["bo"] + box_h / 2),
        ],
        "learn surrogate",
        (right_margin, 4.55),
    )

    ax.text(
        6.0,
        11.55,
        "Closed-loop Control Flow: Contextual BO for Multi-objective GP",
        ha="center",
        va="center",
        fontsize=17,
        fontweight="bold",
        color="#102027",
    )
    ax.text(
        6.0,
        11.15,
        "BO observes the GP state, selects operator rates and update period, then learns from interval reward.",
        ha="center",
        va="center",
        fontsize=10.5,
        color="#455a64",
    )

    fig.tight_layout()
    fig.savefig(output_dir / "closed_loop_control_flow.png", dpi=220)
    fig.savefig(output_dir / "closed_loop_control_flow.svg")
    plt.close(fig)

    print(output_dir / "closed_loop_control_flow.png")
    print(output_dir / "closed_loop_control_flow.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
