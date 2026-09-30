#!/usr/bin/env python3
"""Create slide-readable versions of the final-metric and HV-progress figures."""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = (
    ROOT
    / "outputs"
    / "main_bo_current_friedman"
    / "sr_alpha_friedman"
    / "main_bo_current_friedman_seed100_eval60_20260603"
)
FIG_DIR = RUN_ROOT / "paper_labelled_figures"
AGGREGATE_CSV = RUN_ROOT / "main_aggregate_summary.csv"
GENERATION_CSV = RUN_ROOT / "main_generation_metric_summary.csv"
WARMUP_GENERATION = 18

METHOD_ORDER = (
    "plain_fixed_standard",
    "plain_fixed_high_mutation",
    "plain_fixed_high_crossover",
    "bogp_current",
)

SHORT_LABELS = {
    "plain_fixed_standard": "Fixed\nstandard",
    "plain_fixed_high_mutation": "High\nmutation",
    "plain_fixed_high_crossover": "High\ncrossover",
    "bogp_current": "Proposed\nmethod",
}

LEGEND_LABELS = {
    "plain_fixed_standard": "Fixed standard",
    "plain_fixed_high_mutation": "High mutation",
    "plain_fixed_high_crossover": "High crossover",
    "bogp_current": "Proposed method",
}

COLORS = {
    "plain_fixed_standard": "#6A8CAF",
    "plain_fixed_high_mutation": "#7BAE7F",
    "plain_fixed_high_crossover": "#C48A5A",
    "bogp_current": "#D95F5F",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _aggregate_by_metric(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, float]]]:
    aggregate: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for row in rows:
        aggregate[row["method_name"]][row["metric"]] = {
            "mean": float(row["mean"]),
            "std": float(row["std"]),
        }
    return aggregate


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.size": 13,
            "axes.titlesize": 18,
            "axes.labelsize": 16,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 11,
            "axes.titleweight": "bold",
            "axes.labelweight": "bold",
        }
    )


def _plot_final_metrics(aggregate: dict[str, dict[str, dict[str, float]]]) -> Path:
    methods = [method for method in METHOD_ORDER if method in aggregate]
    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 6.6))
    for ax, metric, ylabel, title in (
        (
            axes[0],
            "final_archive_hypervolume",
            "Final archive HV",
            "Final archive HV",
        ),
        (
            axes[1],
            "final_diversity",
            "Final diversity",
            "Final diversity",
        ),
    ):
        means = [aggregate[method][metric]["mean"] for method in methods]
        stds = [aggregate[method][metric]["std"] for method in methods]
        bars = ax.bar(
            x,
            means,
            yerr=stds,
            capsize=5,
            color=[COLORS[method] for method in methods],
            edgecolor="#30343B",
            linewidth=1.2,
        )
        ax.bar_label(bars, labels=[f"{value:.3f}" for value in means], padding=4, fontsize=11)
        ax.set_xticks(x, [SHORT_LABELS[method] for method in methods])
        ax.set_ylabel(ylabel, labelpad=10)
        ax.set_title(title, pad=12)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)

    fig.subplots_adjust(left=0.085, right=0.985, top=0.88, bottom=0.17, wspace=0.30)
    path = FIG_DIR / "main_final_hv_diversity_slide.png"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)
    return path


def _plot_hv_progress(rows: list[dict[str, str]]) -> Path:
    by_method: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_method[row["method_name"]].append(row)

    fig, ax = plt.subplots(figsize=(11.5, 6.3))
    for method in METHOD_ORDER:
        method_rows = sorted(by_method.get(method, []), key=lambda row: int(row["generation"]))
        if not method_rows:
            continue
        generations = np.asarray([int(row["generation"]) for row in method_rows], dtype=float)
        means = np.asarray([float(row["archive_hypervolume_mean"]) for row in method_rows], dtype=float)
        stds = np.asarray([float(row["archive_hypervolume_std"]) for row in method_rows], dtype=float)
        ax.plot(
            generations,
            means,
            color=COLORS[method],
            linewidth=2.8,
            label=LEGEND_LABELS[method],
        )
        ax.fill_between(
            generations,
            means - stds,
            means + stds,
            color=COLORS[method],
            alpha=0.13,
            linewidth=0,
        )

    ax.axvline(
        WARMUP_GENERATION,
        color="#30343B",
        linestyle="--",
        linewidth=1.8,
        label=f"warm-up boundary (g={WARMUP_GENERATION})",
    )
    ax.set_xlabel("Generation", labelpad=9)
    ax.set_ylabel("Archive HV", labelpad=11)
    ax.set_title("Archive HV progress over generations", pad=12)
    ax.grid(True, alpha=0.26)
    ax.legend(loc="lower right", frameon=True, framealpha=0.9, ncol=1)
    fig.subplots_adjust(left=0.095, right=0.985, top=0.88, bottom=0.125)

    path = FIG_DIR / "main_hv_mean_progress_slide.png"
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240)
    plt.close(fig)
    return path


def main() -> None:
    _configure_matplotlib()
    aggregate = _aggregate_by_metric(_read_csv(AGGREGATE_CSV))
    generation_rows = _read_csv(GENERATION_CSV)
    final_path = _plot_final_metrics(aggregate)
    progress_path = _plot_hv_progress(generation_rows)
    print(final_path)
    print(progress_path)


if __name__ == "__main__":
    main()
