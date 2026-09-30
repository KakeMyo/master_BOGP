#!/usr/bin/env python3
"""Create a slide-readable version of the representative k-alignment figure."""

from __future__ import annotations

import json
import os
from pathlib import Path

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
SEED = 26
WARMUP_GENERATION = 18
RUN_DIR = RUN_ROOT / "runs" / "bogp_current" / f"seed_{SEED}"
OUTPUT_PATH = (
    RUN_ROOT
    / "paper_labelled_figures"
    / f"main_hv_diversity_k_alignment_seed{SEED}_slide.png"
)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    generations = sorted(
        _read_jsonl(RUN_DIR / "generation_metrics.jsonl"),
        key=lambda row: int(row["generation"]),
    )
    controls = sorted(
        _read_jsonl(RUN_DIR / "control_records.jsonl"),
        key=lambda row: int(row["start_generation"]),
    )

    gen_x = np.asarray([int(row["generation"]) for row in generations], dtype=float)
    hv_y = np.asarray([float(row["archive_hypervolume"]) for row in generations], dtype=float)
    div_y = np.asarray([float(row["population_diversity"]) for row in generations], dtype=float)

    k_x: list[float] = []
    k_y: list[float] = []
    for record in controls:
        start = float(record["start_generation"])
        end = float(record["end_generation"])
        update_period = float(record["control"]["update_period"])
        k_x.extend([start, end])
        k_y.extend([update_period, update_period])

    plt.rcParams.update(
        {
            "font.size": 15,
            "axes.titlesize": 20,
            "axes.labelsize": 18,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "axes.titleweight": "bold",
            "axes.labelweight": "bold",
        }
    )

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(11.2, 7.0),
        sharex=True,
        gridspec_kw={"height_ratios": [1.08, 1.08, 0.92], "hspace": 0.16},
    )

    for axis in axes:
        axis.axvline(
            WARMUP_GENERATION,
            color="#30343B",
            linestyle="--",
            linewidth=1.8,
            alpha=0.95,
        )
        for record in controls:
            start = int(record["start_generation"])
            if start == WARMUP_GENERATION:
                continue
            axis.axvline(start, color="#9AA0A6", linestyle=":", linewidth=0.75, alpha=0.25)
        axis.grid(True, alpha=0.26)
        axis.tick_params(axis="both", which="major", width=1.1, length=4)

    axes[0].plot(gen_x, hv_y, color="#D95F5F", linewidth=3.0, marker="o", markersize=4.3)
    axes[0].set_ylabel("Archive HV", labelpad=14)
    axes[0].set_title(
        f"Representative seed={SEED}: HV, diversity, and held update period k",
        pad=10,
    )

    axes[1].plot(gen_x, div_y, color="#3F8F72", linewidth=3.0, marker="o", markersize=4.3)
    axes[1].set_ylabel("Population\ndiversity", labelpad=14)

    if k_x:
        axes[2].plot(
            k_x,
            k_y,
            drawstyle="steps-post",
            color="#3B6EA8",
            linewidth=3.4,
            marker="s",
            markersize=4.9,
        )
    axes[2].set_yticks([1, 3, 5])
    axes[2].set_ylim(0.35, 5.65)
    axes[2].set_ylabel("Held k", labelpad=14)
    axes[2].set_xlabel("Generation", labelpad=9)
    axes[2].text(
        WARMUP_GENERATION + 0.7,
        5.25,
        f"warm-up boundary g={WARMUP_GENERATION}",
        color="#30343B",
        fontsize=14,
        fontweight="bold",
        va="center",
    )

    fig.subplots_adjust(left=0.105, right=0.985, top=0.91, bottom=0.095)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=240)
    plt.close(fig)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
