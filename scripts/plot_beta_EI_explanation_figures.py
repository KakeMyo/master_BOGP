from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUTPUT_DIR = Path("notes/figures/beta_EI")

METHODS = ["bo_current", "beta_k", "beta_EI", "beta_kEI"]
COLORS = {
    "bo_current": "#5B8FA8",
    "beta_k": "#8FBC8F",
    "beta_EI": "#E69F00",
    "beta_kEI": "#B07AA1",
}

RESULTS = {
    "Friedman-I": {
        "hv_mean": [0.773081, 0.774463, 0.774922, 0.771281],
        "hv_std": [0.055720, 0.046293, 0.050454, 0.066523],
        "div_mean": [0.603050, 0.603639, 0.606697, 0.600508],
        "div_std": [0.123937, 0.119035, 0.122603, 0.139885],
        "diff_mean": [0.001382, 0.001841, -0.001800],
        "diff_std": [0.055148, 0.012167, 0.047438],
    },
    "Poly-10": {
        "hv_mean": [0.809864, 0.810086, 0.810057, 0.811320],
        "hv_std": [0.015390, 0.015479, 0.015132, 0.016155],
        "div_mean": [0.540157, 0.564073, 0.549069, 0.558273],
        "div_std": [0.171922, 0.185181, 0.168610, 0.174853],
        "diff_mean": [0.000222, 0.000193, 0.001456],
        "diff_std": [0.015163, 0.004025, 0.016811],
    },
}


def draw_box(ax, xy, text, width=2.2, height=0.78, color="#F6F8FA"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.04,rounding_size=0.08",
        edgecolor="#2F3A45",
        facecolor=color,
        linewidth=1.4,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=10)
    return patch


def draw_arrow(ax, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=1.4,
        color="#2F3A45",
    )
    ax.add_patch(arrow)


def save_control_flow() -> None:
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.set_xlim(0, 10.8)
    ax.set_ylim(0, 6)
    ax.axis("off")

    draw_box(ax, (0.4, 3.7), "GP state\nx_l", color="#EAF2F8")
    draw_box(ax, (2.9, 3.7), "k candidates\n{1, 3, 5}", color="#FDF2E9")
    draw_box(ax, (5.4, 3.7), "GP surrogate\nf_k(x, p_c, p_m)", width=2.5, color="#F4ECF7")
    draw_box(ax, (8.2, 3.7), "action\n(p_c, p_m, k)", width=2.2, color="#E8F6EF")

    draw_arrow(ax, (2.6, 4.1), (2.9, 4.1))
    draw_arrow(ax, (5.1, 4.1), (5.4, 4.1))
    draw_arrow(ax, (7.9, 4.1), (8.2, 4.1))

    draw_box(
        ax,
        (1.2, 1.1),
        "bo_current\nEI uses per-k best\nr_best^(k)",
        width=3.1,
        height=1.25,
        color="#EEF6FA",
    )
    draw_box(
        ax,
        (5.6, 1.1),
        "beta_EI\nEI uses global best\nr_best^global",
        width=3.1,
        height=1.25,
        color="#FFF3D7",
    )

    draw_arrow(ax, (6.65, 3.7), (3.0, 2.35))
    draw_arrow(ax, (6.95, 3.7), (7.1, 2.35))

    ax.text(
        5.4,
        5.4,
        "Only the EI reference value is changed in beta_EI",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
    )
    ax.text(
        5.4,
        0.35,
        "Warm-up remains sequential. The comparison standard for k is made common.",
        ha="center",
        va="center",
        fontsize=10,
        color="#4D5965",
    )

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "beta_EI_control_flow.png", dpi=220)
    plt.close(fig)


def save_baseline_comparison() -> None:
    k_labels = ["k=1", "k=3", "k=5"]
    per_k_best = np.array([0.30, 0.45, 0.60])
    candidate_k1 = 0.35
    global_best = per_k_best.max()
    x = np.arange(len(k_labels))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)

    axes[0].bar(x, per_k_best, color="#BBD7EA", edgecolor="#2F3A45", label="per-k best")
    axes[0].scatter([0], [candidate_k1], s=120, color="#E69F00", label="candidate mean")
    axes[0].annotate(
        "positive local improvement",
        xy=(0, candidate_k1),
        xytext=(0.25, 0.43),
        arrowprops={"arrowstyle": "->", "color": "#2F3A45"},
        fontsize=9,
    )
    axes[0].set_title("bo_current: compare inside each k")
    axes[0].set_xticks(x, k_labels)
    axes[0].set_ylabel("reward")
    axes[0].set_ylim(0, 0.72)
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].legend(loc="upper left", fontsize=9)

    axes[1].bar(x, per_k_best, color="#D7EBD3", edgecolor="#2F3A45", label="observed best by k")
    axes[1].axhline(global_best, color="#C0392B", linestyle="--", linewidth=2, label="global best")
    axes[1].scatter([0], [candidate_k1], s=120, color="#E69F00", label="candidate mean")
    axes[1].annotate(
        "below global best",
        xy=(0, candidate_k1),
        xytext=(0.25, 0.18),
        arrowprops={"arrowstyle": "->", "color": "#2F3A45"},
        fontsize=9,
    )
    axes[1].set_title("beta_EI: compare against common best")
    axes[1].set_xticks(x, k_labels)
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend(loc="upper left", fontsize=9)

    fig.suptitle("How the EI reference value changes", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "ei_reference_comparison.png", dpi=220)
    plt.close(fig)


def save_metric_bars() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.2))
    x = np.arange(len(METHODS))
    bar_colors = [COLORS[m] for m in METHODS]

    for row, problem in enumerate(["Friedman-I", "Poly-10"]):
        data = RESULTS[problem]
        ax_hv = axes[row, 0]
        ax_div = axes[row, 1]

        ax_hv.bar(x, data["hv_mean"], yerr=data["hv_std"], capsize=4, color=bar_colors, edgecolor="#2F3A45")
        ax_hv.set_title(f"{problem}: final archive HV")
        ax_hv.set_xticks(x, METHODS, rotation=20, ha="right")
        ax_hv.set_ylabel("mean ± std")
        ax_hv.grid(axis="y", alpha=0.25)

        ax_div.bar(x, data["div_mean"], yerr=data["div_std"], capsize=4, color=bar_colors, edgecolor="#2F3A45")
        ax_div.set_title(f"{problem}: final diversity")
        ax_div.set_xticks(x, METHODS, rotation=20, ha="right")
        ax_div.set_ylabel("mean ± std")
        ax_div.grid(axis="y", alpha=0.25)

    fig.suptitle("Seed 100 comparison: final metrics", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "seed100_hv_diversity_bars.png", dpi=220)
    plt.close(fig)


def save_hv_diff_bars() -> None:
    methods = ["beta_k", "beta_EI", "beta_kEI"]
    colors = [COLORS[m] for m in methods]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=False)
    x = np.arange(len(methods))

    for ax, problem in zip(axes, ["Friedman-I", "Poly-10"]):
        data = RESULTS[problem]
        ax.axhline(0, color="#2F3A45", linewidth=1)
        ax.bar(
            x,
            data["diff_mean"],
            yerr=data["diff_std"],
            capsize=4,
            color=colors,
            edgecolor="#2F3A45",
        )
        ax.set_title(f"{problem}: HV difference vs bo_current")
        ax.set_xticks(x, methods, rotation=20, ha="right")
        ax.set_ylabel("method - bo_current")
        ax.grid(axis="y", alpha=0.25)

    fig.suptitle("Paired final HV difference over 100 seeds", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "seed100_hv_diff_vs_bo_current.png", dpi=220)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_control_flow()
    save_baseline_comparison()
    save_metric_bars()
    save_hv_diff_bars()


if __name__ == "__main__":
    main()
