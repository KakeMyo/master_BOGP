from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ID = "ver_beta_kEI_20260529_122615"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs" / "symbolic_regression_alpha_bo_compare"
DEFAULT_PROBLEMS = ("sr_alpha_friedman", "sr_alpha_poly10")
METHOD_ORDER = ("bo_current", "ver_beta_k", "ver_beta_EI", "ver_beta_kEI")
METHOD_LABELS = {
    "bo_current": "current",
    "ver_beta_k": "beta_k",
    "ver_beta_EI": "beta_EI",
    "ver_beta_kEI": "beta_kEI",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plot seed-wise beta BO controller comparison figures.",
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory containing problem/run outputs.",
    )
    parser.add_argument(
        "--problem",
        action="append",
        choices=DEFAULT_PROBLEMS,
        help="Problem name to plot. Defaults to all proto-alpha problems.",
    )
    args = parser.parse_args()

    problem_names = tuple(args.problem) if args.problem else DEFAULT_PROBLEMS
    output_root = Path(args.output_root)
    created: list[str] = []
    for problem_name in problem_names:
        problem_dir = output_root / problem_name / args.run_id
        created.extend(plot_problem_seedwise(problem_dir))

    print(json.dumps({"created": created}, ensure_ascii=False, indent=2))
    return 0


def plot_problem_seedwise(problem_dir: Path) -> list[str]:
    summary_path = problem_dir / "summary_by_seed.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"summary_by_seed.csv not found: {summary_path}")

    rows = _read_csv_rows(summary_path)
    seeds = sorted({int(row["seed"]) for row in rows})
    methods = [method for method in METHOD_ORDER if any(row["method_name"] == method for row in rows)]
    if not methods:
        methods = sorted({row["method_name"] for row in rows})

    created: list[str] = []
    for seed in seeds:
        figure_path = problem_dir / f"seedwise_hv_diversity_k_seed_{seed}.png"
        _plot_seed_overview(problem_dir, methods, seed, figure_path)
        created.append(str(figure_path))
    return created


def _plot_seed_overview(
    problem_dir: Path,
    methods: list[str],
    seed: int,
    figure_path: Path,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for index, method in enumerate(methods):
        run_dir = problem_dir / "runs" / method / f"seed_{seed}"
        metrics = _read_jsonl(run_dir / "generation_metrics.jsonl")
        controls = _read_jsonl(run_dir / "control_records.jsonl")
        color = colors[index % len(colors)]
        label = METHOD_LABELS.get(method, method)

        generations = [row["generation"] for row in metrics]
        archive_hv = [row["archive_hypervolume"] for row in metrics]
        diversity = [row["population_diversity"] for row in metrics]

        axes[0].plot(
            generations,
            archive_hv,
            marker="o",
            markersize=4,
            linewidth=2,
            color=color,
            label=label,
        )
        axes[1].plot(
            generations,
            diversity,
            marker="o",
            markersize=4,
            linewidth=2,
            color=color,
            label=label,
        )
        _plot_control_period_line(axes[2], controls, label, color)

    problem_label = problem_dir.parent.name
    fig.suptitle(f"{problem_label}: seed {seed} comparison", fontsize=16)
    axes[0].set_ylabel("Archive HV")
    axes[1].set_ylabel("Population diversity")
    axes[2].set_ylabel("k")
    axes[2].set_xlabel("Generation")
    axes[2].set_yticks([1, 3, 5])

    for axis in axes:
        axis.grid(True, alpha=0.35)
        axis.legend(loc="best")

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)


def _plot_control_period_line(
    axis: Any,
    controls: list[dict[str, Any]],
    label: str,
    color: str,
) -> None:
    xs: list[float] = []
    ys: list[float] = []
    for record in controls:
        start = float(record["start_generation"])
        end = float(record["end_generation"])
        update_period = float(record["control"]["update_period"])
        xs.extend([start, end])
        ys.extend([update_period, update_period])

    axis.plot(
        xs,
        ys,
        drawstyle="steps-post",
        marker="s",
        markersize=4,
        linewidth=2,
        color=color,
        label=label,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
