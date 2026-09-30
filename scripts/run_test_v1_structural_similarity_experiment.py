from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from statistics import mean, stdev

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.test_v1_structural_similarity_experiment import (
    SimilarityExperimentConfig,
    SimilarityRow,
    run_all_experiments,
    summarize_rows,
)


def _rows_for(rows: list[SimilarityRow], experiment: str) -> list[SimilarityRow]:
    return sorted(
        [row for row in rows if row.experiment == experiment],
        key=lambda row: (row.m, row.trial),
    )


def _write_csv(rows: list[SimilarityRow], output_path: Path) -> None:
    fieldnames = list(rows[0].to_dict().keys()) if rows else []
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def _plot_similarity_curve(rows: list[SimilarityRow], output_path: Path) -> None:
    ideal = _rows_for(rows, "ideal_multiset")
    shared = _rows_for(rows, "shared_tree")

    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.0), sharex=True)

    axes[0][0].plot(
        [row.m for row in ideal],
        [row.theory_similarity for row in ideal],
        linestyle="--",
        label="Theory: mq/(U_A+U_B+mq)",
    )
    axes[0][0].plot(
        [row.m for row in ideal],
        [row.similarity for row in ideal],
        marker="o",
        markersize=3.2,
        label="Ideal multiset",
    )
    axes[0][0].plot(
        [row.m for row in shared],
        [row.similarity for row in shared],
        marker="s",
        markersize=3.2,
        label="Actual prefix tree",
    )
    axes[0][0].set_ylabel("Structural similarity")
    axes[0][0].set_title("Similarity curve")
    axes[0][0].grid(True, alpha=0.3)
    axes[0][0].legend()

    axes[0][1].plot(
        [row.m for row in ideal],
        [row.diversity for row in ideal],
        marker="o",
        markersize=3.2,
        label="Ideal multiset",
    )
    axes[0][1].plot(
        [row.m for row in shared],
        [row.diversity for row in shared],
        marker="s",
        markersize=3.2,
        label="Actual prefix tree",
    )
    axes[0][1].set_ylabel("Structural diversity")
    axes[0][1].set_title("Diversity = 1 - similarity")
    axes[0][1].grid(True, alpha=0.3)
    axes[0][1].legend()

    axes[1][0].plot(
        [row.m for row in ideal],
        [row.intersection for row in ideal],
        marker="o",
        markersize=3.2,
        label="Ideal multiset",
    )
    axes[1][0].plot(
        [row.m for row in shared],
        [row.intersection for row in shared],
        marker="s",
        markersize=3.2,
        label="Actual prefix tree",
    )
    axes[1][0].set_xlabel("Number of shared isomorphic motifs m")
    axes[1][0].set_ylabel("Intersection")
    axes[1][0].grid(True, alpha=0.3)
    axes[1][0].legend()

    axes[1][1].plot(
        [row.m for row in ideal],
        [row.union for row in ideal],
        marker="o",
        markersize=3.2,
        label="Ideal multiset",
    )
    axes[1][1].plot(
        [row.m for row in shared],
        [row.union for row in shared],
        marker="s",
        markersize=3.2,
        label="Actual prefix tree",
    )
    axes[1][1].set_xlabel("Number of shared isomorphic motifs m")
    axes[1][1].set_ylabel("Union")
    axes[1][1].grid(True, alpha=0.3)
    axes[1][1].legend()

    fig.suptitle("Structural similarity response to shared isomorphic subtrees")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_one_sided_curve(
    rows: list[SimilarityRow],
    fixed_m: int,
    output_path: Path,
) -> None:
    one_sided = _rows_for(rows, "one_sided_tree")

    fig, axes = plt.subplots(2, 1, figsize=(8.4, 7.0), sharex=True)
    axes[0].plot(
        [row.m for row in one_sided],
        [row.theory_similarity for row in one_sided],
        linestyle="--",
        label="Theory",
    )
    axes[0].plot(
        [row.m for row in one_sided],
        [row.similarity for row in one_sided],
        marker="o",
        label="Actual prefix tree",
    )
    axes[0].axvline(fixed_m, color="gray", linestyle=":", label="fixed m in tree A")
    axes[0].set_ylabel("Structural similarity")
    axes[0].set_title("One-sided motif increase")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(
        [row.m for row in one_sided],
        [row.diversity for row in one_sided],
        marker="s",
        color="tab:orange",
        label="Diversity",
    )
    axes[1].axvline(fixed_m, color="gray", linestyle=":")
    axes[1].set_xlabel("Number of shared motifs in tree B")
    axes[1].set_ylabel("Structural diversity")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _aggregate_random_rows(rows: list[SimilarityRow]) -> list[dict]:
    random_rows = _rows_for(rows, "random_background")
    m_values = sorted({row.m for row in random_rows})
    aggregates = []
    for m in m_values:
        values = [row.similarity for row in random_rows if row.m == m]
        diversities = [row.diversity for row in random_rows if row.m == m]
        theories = [row.theory_similarity for row in random_rows if row.m == m]
        similarity_std = stdev(values) if len(values) >= 2 else 0.0
        diversity_std = stdev(diversities) if len(diversities) >= 2 else 0.0
        aggregates.append(
            {
                "m": m,
                "similarity_mean": mean(values),
                "similarity_std": similarity_std,
                "diversity_mean": mean(diversities),
                "diversity_std": diversity_std,
                "theory_mean": mean(theories),
            }
        )
    return aggregates


def _plot_random_background_curve(rows: list[SimilarityRow], output_path: Path) -> None:
    aggregates = _aggregate_random_rows(rows)
    m_values = [row["m"] for row in aggregates]
    similarity_mean = [row["similarity_mean"] for row in aggregates]
    similarity_std = [row["similarity_std"] for row in aggregates]
    diversity_mean = [row["diversity_mean"] for row in aggregates]
    diversity_std = [row["diversity_std"] for row in aggregates]
    theory_mean = [row["theory_mean"] for row in aggregates]

    similarity_lower = [value - std for value, std in zip(similarity_mean, similarity_std)]
    similarity_upper = [value + std for value, std in zip(similarity_mean, similarity_std)]
    diversity_lower = [value - std for value, std in zip(diversity_mean, diversity_std)]
    diversity_upper = [value + std for value, std in zip(diversity_mean, diversity_std)]

    fig, axes = plt.subplots(2, 1, figsize=(8.4, 7.0), sharex=True)
    axes[0].plot(m_values, theory_mean, linestyle="--", label="Mean theory")
    axes[0].plot(m_values, similarity_mean, marker="o", label="Mean similarity")
    axes[0].fill_between(m_values, similarity_lower, similarity_upper, alpha=0.20)
    axes[0].set_ylabel("Structural similarity")
    axes[0].set_title("Random background experiment")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(m_values, diversity_mean, marker="s", color="tab:orange", label="Mean diversity")
    axes[1].fill_between(m_values, diversity_lower, diversity_upper, color="tab:orange", alpha=0.20)
    axes[1].set_xlabel("Number of shared isomorphic motifs m")
    axes[1].set_ylabel("Structural diversity")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> int:
    output_dir = ROOT / "outputs" / "structural_similarity_test_v1" / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    config = SimilarityExperimentConfig()
    rows = run_all_experiments(config)
    summary = summarize_rows(rows, config)

    csv_path = output_dir / "similarity_curve.csv"
    similarity_plot = output_dir / "similarity_curve.png"
    one_sided_plot = output_dir / "one_sided_curve.png"
    random_plot = output_dir / "random_background_curve.png"
    summary_path = output_dir / "summary.json"

    _write_csv(rows, csv_path)
    _plot_similarity_curve(rows, similarity_plot)
    _plot_one_sided_curve(rows, config.one_sided_fixed_m, one_sided_plot)
    _plot_random_background_curve(rows, random_plot)

    payload = {
        **summary,
        "output_dir": str(output_dir),
        "csv": str(csv_path),
        "similarity_curve_plot": str(similarity_plot),
        "one_sided_curve_plot": str(one_sided_plot),
        "random_background_curve_plot": str(random_plot),
    }
    summary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
