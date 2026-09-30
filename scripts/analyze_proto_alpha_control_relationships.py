from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


RUN_ID = "ver_alpha_20260528_205110"
PROBLEM_DIRS = {
    "sr_alpha_friedman": ROOT
    / "outputs"
    / "symbolic_regression_alpha"
    / "sr_alpha_friedman"
    / RUN_ID,
    "sr_alpha_poly10": ROOT
    / "outputs"
    / "symbolic_regression_alpha"
    / "sr_alpha_poly10"
    / RUN_ID,
}
OUTPUT_DIR = (
    ROOT
    / "outputs"
    / "symbolic_regression_alpha"
    / "proto_alpha_control_analysis"
    / RUN_ID
)


@dataclass(frozen=True)
class IntervalRow:
    problem_name: str
    seed: int
    step_index: int
    start_generation: int
    end_generation: int
    interval_length: int
    p_c: float
    p_m: float
    k: int
    start_hv: float
    end_hv: float
    delta_hv: float
    hv_rate: float
    start_diversity: float
    end_diversity: float
    delta_diversity: float
    mean_interval_diversity: float
    reward_total: float
    reward_hv_term: float
    reward_diversity_term: float
    reward_control_cost: float
    target_diversity: float


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[IntervalRow] = []
    for problem_name, problem_dir in PROBLEM_DIRS.items():
        rows = _load_problem_rows(problem_name, problem_dir)
        all_rows.extend(rows)
        problem_output = OUTPUT_DIR / problem_name
        problem_output.mkdir(parents=True, exist_ok=True)
        _write_interval_csv(problem_output / "control_interval_analysis.csv", rows)
        _write_k_summary_csv(problem_output / "control_interval_summary_by_k.csv", rows)
        _plot_seed_timelines(problem_output, problem_name, problem_dir, rows)
        _plot_hv_diversity_k_alignment(problem_output, problem_name, problem_dir, rows)
        _plot_k_relationships(problem_output, problem_name, rows)

    _write_interval_csv(OUTPUT_DIR / "control_interval_analysis_all.csv", all_rows)
    _write_k_summary_csv(OUTPUT_DIR / "control_interval_summary_by_problem_k.csv", all_rows)
    _plot_problem_k_comparison(OUTPUT_DIR, all_rows)
    _write_markdown_summary(OUTPUT_DIR / "proto_alpha_control_analysis_summary.md", all_rows)
    print(json.dumps({"output_dir": str(OUTPUT_DIR), "interval_count": len(all_rows)}, indent=2))
    return 0


def _load_problem_rows(problem_name: str, problem_dir: Path) -> list[IntervalRow]:
    rows: list[IntervalRow] = []
    run_root = problem_dir / "runs" / "bogp_current"
    for seed_dir in sorted(run_root.glob("seed_*")):
        seed = int(seed_dir.name.split("_")[-1])
        metrics = _load_generation_metrics(seed_dir / "generation_metrics.jsonl")
        controls = _load_jsonl(seed_dir / "control_records.jsonl")
        for record in controls:
            start = int(record["start_generation"])
            end = int(record["end_generation"])
            interval_metrics = [
                metrics[g]["population_diversity"]
                for g in range(start + 1, end + 1)
                if g in metrics
            ]
            if not interval_metrics and end in metrics:
                interval_metrics = [metrics[end]["population_diversity"]]
            start_div = float(metrics[start]["population_diversity"])
            end_div = float(metrics[end]["population_diversity"])
            start_hv = float(record["start_archive_hypervolume"])
            end_hv = float(record["end_archive_hypervolume"])
            interval_length = max(1, end - start)
            reward = record.get("reward", {})
            control = record["control"]
            rows.append(
                IntervalRow(
                    problem_name=problem_name,
                    seed=seed,
                    step_index=int(record["step_index"]),
                    start_generation=start,
                    end_generation=end,
                    interval_length=interval_length,
                    p_c=float(control["crossover_rate"]),
                    p_m=float(control["mutation_rate"]),
                    k=int(control["update_period"]),
                    start_hv=start_hv,
                    end_hv=end_hv,
                    delta_hv=end_hv - start_hv,
                    hv_rate=(end_hv - start_hv) / float(interval_length),
                    start_diversity=start_div,
                    end_diversity=end_div,
                    delta_diversity=end_div - start_div,
                    mean_interval_diversity=float(mean(interval_metrics)),
                    reward_total=float(reward.get("total", 0.0)),
                    reward_hv_term=float(reward.get("hv_term", 0.0)),
                    reward_diversity_term=float(reward.get("diversity_term", 0.0)),
                    reward_control_cost=float(reward.get("control_cost", 0.0)),
                    target_diversity=float(reward.get("target_diversity", 0.0)),
                )
            )
    return rows


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_generation_metrics(path: Path) -> dict[int, dict[str, Any]]:
    return {int(row["generation"]): row for row in _load_jsonl(path)}


def _write_interval_csv(path: Path, rows: Iterable[IntervalRow]) -> None:
    rows = list(rows)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].__dict__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _write_k_summary_csv(path: Path, rows: Iterable[IntervalRow]) -> None:
    groups: dict[tuple[str, int], list[IntervalRow]] = defaultdict(list)
    for row in rows:
        groups[(row.problem_name, row.k)].append(row)
    fields = [
        "problem_name",
        "k",
        "count",
        "mean_hv_rate",
        "mean_delta_hv",
        "mean_delta_diversity",
        "mean_interval_diversity",
        "mean_reward_total",
        "mean_reward_hv_term",
        "mean_reward_diversity_term",
        "mean_p_c",
        "mean_p_m",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for (problem_name, k_value), group in sorted(groups.items()):
            writer.writerow(
                {
                    "problem_name": problem_name,
                    "k": k_value,
                    "count": len(group),
                    "mean_hv_rate": mean(row.hv_rate for row in group),
                    "mean_delta_hv": mean(row.delta_hv for row in group),
                    "mean_delta_diversity": mean(row.delta_diversity for row in group),
                    "mean_interval_diversity": mean(row.mean_interval_diversity for row in group),
                    "mean_reward_total": mean(row.reward_total for row in group),
                    "mean_reward_hv_term": mean(row.reward_hv_term for row in group),
                    "mean_reward_diversity_term": mean(
                        row.reward_diversity_term for row in group
                    ),
                    "mean_p_c": mean(row.p_c for row in group),
                    "mean_p_m": mean(row.p_m for row in group),
                }
            )


def _plot_seed_timelines(
    output_dir: Path,
    problem_name: str,
    problem_dir: Path,
    rows: list[IntervalRow],
) -> None:
    by_seed: dict[int, list[IntervalRow]] = defaultdict(list)
    for row in rows:
        by_seed[row.seed].append(row)

    for seed, seed_rows in sorted(by_seed.items()):
        metrics = _load_generation_metrics(
            problem_dir / "runs" / "bogp_current" / f"seed_{seed}" / "generation_metrics.jsonl"
        )
        generations = sorted(metrics)
        hv_values = [float(metrics[g]["archive_hypervolume"]) for g in generations]
        diversity_values = [float(metrics[g]["population_diversity"]) for g in generations]
        mean_sizes = [float(metrics[g]["mean_tree_size"]) for g in generations]

        fig, axes = plt.subplots(4, 1, figsize=(10.0, 9.2), sharex=True)
        axes[0].plot(generations, hv_values, marker="o", markersize=3.0, label="Archive HV")
        axes[0].set_ylabel("Archive HV")
        axes[0].legend(loc="lower right")

        axes[1].plot(
            generations,
            diversity_values,
            marker="s",
            markersize=3.0,
            color="tab:green",
            label="Population diversity",
        )
        axes[1].set_ylabel("Diversity")
        axes[1].legend(loc="lower right")

        axes[2].plot(
            generations,
            mean_sizes,
            marker="^",
            markersize=3.0,
            color="tab:purple",
            label="Mean tree size",
        )
        axes[2].set_ylabel("Mean size")
        axes[2].legend(loc="upper right")

        end_generations = [row.end_generation for row in seed_rows]
        axes[3].step(
            end_generations,
            [row.p_c for row in seed_rows],
            where="post",
            marker="o",
            label="p_c",
        )
        axes[3].step(
            end_generations,
            [row.p_m for row in seed_rows],
            where="post",
            marker="s",
            label="p_m",
        )
        k_axis = axes[3].twinx()
        for index, row in enumerate(seed_rows):
            k_axis.hlines(
                row.k,
                row.start_generation,
                row.end_generation,
                color="tab:red",
                linewidth=2.4,
                alpha=0.6,
                label="k interval" if index == 0 else None,
            )
        axes[3].set_ylabel("Operator rate")
        k_axis.set_ylabel("k")
        axes[3].set_xlabel("Generation")
        axes[3].legend(loc="upper left")
        k_axis.legend(loc="upper right")

        for axis in axes:
            axis.grid(True, alpha=0.3)
            for row in seed_rows:
                axis.axvspan(row.start_generation, row.end_generation, color="black", alpha=0.018)

        fig.suptitle(f"{problem_name}: BO control and metrics (seed={seed})")
        fig.tight_layout()
        fig.savefig(output_dir / f"control_metric_timeline_seed_{seed}.png", dpi=180)
        plt.close(fig)


def _plot_hv_diversity_k_alignment(
    output_dir: Path,
    problem_name: str,
    problem_dir: Path,
    rows: list[IntervalRow],
) -> None:
    by_seed: dict[int, list[IntervalRow]] = defaultdict(list)
    for row in rows:
        by_seed[row.seed].append(row)

    for seed, seed_rows in sorted(by_seed.items()):
        metrics = _load_generation_metrics(
            problem_dir / "runs" / "bogp_current" / f"seed_{seed}" / "generation_metrics.jsonl"
        )
        generations = sorted(metrics)
        hv_values = [float(metrics[g]["archive_hypervolume"]) for g in generations]
        diversity_values = [float(metrics[g]["population_diversity"]) for g in generations]

        fig, axes = plt.subplots(
            3,
            1,
            figsize=(10.5, 7.4),
            sharex=True,
            gridspec_kw={"height_ratios": [1.2, 1.2, 0.95]},
        )
        update_points = sorted({row.start_generation for row in seed_rows} | {seed_rows[-1].end_generation})

        axes[0].plot(
            generations,
            hv_values,
            color="tab:blue",
            marker="o",
            markersize=3.2,
            linewidth=2.0,
            label="Archive HV",
        )
        axes[0].set_ylabel("Archive HV")
        axes[0].legend(loc="lower right")

        axes[1].plot(
            generations,
            diversity_values,
            color="tab:green",
            marker="s",
            markersize=3.2,
            linewidth=2.0,
            label="Population diversity",
        )
        axes[1].set_ylabel("Diversity")
        axes[1].legend(loc="lower right")

        k_colors = {1: "tab:blue", 3: "tab:orange", 5: "tab:red"}
        for row in seed_rows:
            color = k_colors.get(row.k, "tab:gray")
            axes[2].hlines(
                row.k,
                row.start_generation,
                row.end_generation,
                color=color,
                linewidth=5.0,
                alpha=0.80,
                label=f"k={row.k}" if f"k={row.k}" not in axes[2].get_legend_handles_labels()[1] else None,
            )
            midpoint = (row.start_generation + row.end_generation) / 2.0
            axes[2].text(
                midpoint,
                row.k + 0.08,
                str(row.k),
                ha="center",
                va="bottom",
                fontsize=8,
                color=color,
            )

        axes[2].set_ylabel("Update period k")
        axes[2].set_xlabel("Generation")
        axes[2].set_yticks(sorted({row.k for row in seed_rows}))
        axes[2].set_ylim(0.5, max(row.k for row in seed_rows) + 0.8)
        axes[2].legend(loc="upper right", title="Selected k")

        for axis in axes:
            axis.grid(True, alpha=0.30)
            for point in update_points:
                axis.axvline(point, color="0.25", linestyle=":", linewidth=0.8, alpha=0.35)
            for row in seed_rows:
                axis.axvspan(row.start_generation, row.end_generation, color="black", alpha=0.015)

        fig.suptitle(
            f"{problem_name}: HV / Diversity / k alignment (seed={seed})",
            fontsize=14,
        )
        fig.tight_layout()
        fig.savefig(output_dir / f"hv_diversity_k_alignment_seed_{seed}.png", dpi=200)
        plt.close(fig)


def _plot_k_relationships(output_dir: Path, problem_name: str, rows: list[IntervalRow]) -> None:
    if not rows:
        return
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0))
    _scatter_by_k(axes[0], rows, "hv_rate", "HV gain per generation", lambda row: row.hv_rate)
    _scatter_by_k(
        axes[1],
        rows,
        "delta_diversity",
        "Diversity change",
        lambda row: row.delta_diversity,
    )
    _scatter_by_k(
        axes[2],
        rows,
        "reward_total",
        "Reward",
        lambda row: row.reward_total,
    )
    fig.suptitle(f"{problem_name}: interval outcomes grouped by k")
    fig.tight_layout()
    fig.savefig(output_dir / "control_interval_outcomes_by_k.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    color_by_k = {1: "tab:blue", 3: "tab:orange", 5: "tab:green"}
    for k_value in sorted({row.k for row in rows}):
        group = [row for row in rows if row.k == k_value]
        ax.scatter(
            [row.p_c for row in group],
            [row.p_m for row in group],
            s=[40.0 + 900.0 * max(row.hv_rate, 0.0) for row in group],
            alpha=0.65,
            color=color_by_k.get(k_value),
            label=f"k={k_value}",
            edgecolor="white",
            linewidth=0.5,
        )
    ax.set_xlabel("p_c")
    ax.set_ylabel("p_m")
    ax.set_title(f"{problem_name}: selected controls (size = positive HV rate)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "selected_controls_pc_pm.png", dpi=180)
    plt.close(fig)


def _scatter_by_k(ax, rows: list[IntervalRow], column: str, ylabel: str, getter) -> None:
    rng = np.random.default_rng(20260529)
    for k_value in sorted({row.k for row in rows}):
        group = [row for row in rows if row.k == k_value]
        x_values = np.full(len(group), float(k_value)) + rng.normal(0.0, 0.035, size=len(group))
        y_values = [getter(row) for row in group]
        ax.scatter(x_values, y_values, alpha=0.70, label=f"k={k_value}")
        ax.hlines(mean(y_values), k_value - 0.22, k_value + 0.22, linewidth=2.5)
    ax.set_xlabel("k")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()


def _plot_problem_k_comparison(output_dir: Path, rows: list[IntervalRow]) -> None:
    if not rows:
        return
    problems = sorted({row.problem_name for row in rows})
    k_values = sorted({row.k for row in rows})
    width = 0.35

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3))
    for axis, metric_name, getter, ylabel in [
        (axes[0], "hv_rate", lambda row: row.hv_rate, "Mean HV gain per generation"),
        (
            axes[1],
            "delta_diversity",
            lambda row: row.delta_diversity,
            "Mean diversity change per interval",
        ),
    ]:
        for p_index, problem in enumerate(problems):
            values = []
            for k_value in k_values:
                group = [row for row in rows if row.problem_name == problem and row.k == k_value]
                values.append(mean(getter(row) for row in group) if group else 0.0)
            offset = (p_index - (len(problems) - 1) / 2.0) * width
            axis.bar(
                np.arange(len(k_values)) + offset,
                values,
                width=width,
                label=problem,
            )
        axis.set_xticks(np.arange(len(k_values)))
        axis.set_xticklabels([str(k) for k in k_values])
        axis.set_xlabel("k")
        axis.set_ylabel(ylabel)
        axis.grid(True, axis="y", alpha=0.3)
        axis.legend()
        axis.set_title(metric_name)
    fig.tight_layout()
    fig.savefig(output_dir / "problem_k_comparison.png", dpi=180)
    plt.close(fig)


def _write_markdown_summary(path: Path, rows: list[IntervalRow]) -> None:
    lines = [
        "# proto_alpha BO制御履歴解析",
        "",
        f"- 対象run: `{RUN_ID}`",
        f"- 解析区間数: `{len(rows)}`",
        "- 各行は BO が1回出力した制御区間を表す。",
        "- `hv_rate` は `(end_hv - start_hv) / interval_length`。",
        "",
    ]
    for problem_name in sorted({row.problem_name for row in rows}):
        problem_rows = [row for row in rows if row.problem_name == problem_name]
        lines.extend([f"## {problem_name}", ""])
        lines.append("| k | count | mean hv_rate | mean delta_hv | mean delta_diversity | mean reward |")
        lines.append("|---:|---:|---:|---:|---:|---:|")
        for k_value in sorted({row.k for row in problem_rows}):
            group = [row for row in problem_rows if row.k == k_value]
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(k_value),
                        str(len(group)),
                        f"{mean(row.hv_rate for row in group):.6f}",
                        f"{mean(row.delta_hv for row in group):.6f}",
                        f"{mean(row.delta_diversity for row in group):.6f}",
                        f"{mean(row.reward_total for row in group):.6f}",
                    ]
                )
                + " |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
