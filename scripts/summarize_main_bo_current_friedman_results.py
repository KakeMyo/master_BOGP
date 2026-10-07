from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import wilcoxon


ROOT = Path(__file__).resolve().parents[1]

METHOD_ORDER = (
    "plain_fixed_standard",
    "plain_fixed_high_mutation",
    "plain_fixed_high_crossover",
    "bogp_current",
)

FIXED_METHODS = tuple(method for method in METHOD_ORDER if method != "bogp_current")

METHOD_LABELS = {
    "plain_fixed_standard": "Fixed standard\n(p_c=0.80, p_m=0.05)",
    "plain_fixed_high_mutation": "Fixed high mutation\n(p_c=0.70, p_m=0.20)",
    "plain_fixed_high_crossover": "Fixed high crossover\n(p_c=0.90, p_m=0.05)",
    "bogp_current": "BO-controlled GP\n(bo_current)",
}

PARETO_LABELS = {
    "plain_fixed_standard": "Fixed standard (p_c=0.80, p_m=0.05)",
    "plain_fixed_high_mutation": "Fixed high mutation (p_c=0.70, p_m=0.20)",
    "plain_fixed_high_crossover": "Fixed high crossover (p_c=0.90, p_m=0.05)",
    "bogp_current": "Proposed method",
}

METHOD_TEX = {
    "plain_fixed_standard": r"\texttt{plain\_fixed\_standard}",
    "plain_fixed_high_mutation": r"\texttt{plain\_fixed\_high\_mutation}",
    "plain_fixed_high_crossover": r"\texttt{plain\_fixed\_high\_crossover}",
    "bogp_current": r"\texttt{bogp\_current}",
}

COLORS = {
    "plain_fixed_standard": "#6A8CAF",
    "plain_fixed_high_mutation": "#7BAE7F",
    "plain_fixed_high_crossover": "#C48A5A",
    "bogp_current": "#D95F5F",
}

MARKERS = {
    "plain_fixed_standard": "s",
    "plain_fixed_high_mutation": "^",
    "plain_fixed_high_crossover": "D",
    "bogp_current": "o",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _metric_stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }


def _float(row: dict[str, Any], key: str) -> float:
    return float(row[key])


def _safe_wilcoxon(diffs: list[float]) -> dict[str, float]:
    if not diffs:
        return {"statistic": 0.0, "p_value": 1.0}
    if all(abs(value) <= 1.0e-12 for value in diffs):
        return {"statistic": 0.0, "p_value": 1.0}
    try:
        result = wilcoxon(diffs, zero_method="wilcox", alternative="two-sided")
        return {"statistic": float(result.statistic), "p_value": float(result.pvalue)}
    except ValueError:
        return {"statistic": 0.0, "p_value": 1.0}


def _generation_rows(run_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(run_dir / "generation_metrics.jsonl")


def _control_rows(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "control_records.jsonl"
    if not path.exists():
        return []
    return _read_jsonl(path)


def _value_at_generation(rows: list[dict[str, Any]], metric: str, generation: int) -> float:
    for row in rows:
        if int(row["generation"]) == generation:
            return float(row[metric])
    raise ValueError(f"Missing generation {generation} for metric {metric}.")


def _time_average_after_warmup(
    rows: list[dict[str, Any]],
    metric: str,
    warmup_generation: int,
) -> float:
    selected = [
        (int(row["generation"]), float(row[metric]))
        for row in rows
        if int(row["generation"]) >= warmup_generation
    ]
    if not selected:
        return 0.0
    if len(selected) == 1:
        return selected[0][1]
    generations = np.asarray([item[0] for item in selected], dtype=float)
    values = np.asarray([item[1] for item in selected], dtype=float)
    width = float(generations[-1] - generations[0])
    if width <= 0:
        return float(values[-1])
    return float(np.trapz(values, generations) / width)


def _augment_rows(
    summary_rows: list[dict[str, str]],
    warmup_generation: int,
) -> tuple[list[dict[str, Any]], dict[tuple[str, int], list[dict[str, Any]]]]:
    augmented: list[dict[str, Any]] = []
    generation_by_run: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in summary_rows:
        method = row["method_name"]
        seed = int(row["seed"])
        run_dir = Path(row["output_dir"])
        generations = _generation_rows(run_dir)
        generation_by_run[(method, seed)] = generations
        warmup_hv = _value_at_generation(generations, "archive_hypervolume", warmup_generation)
        final_hv = float(row["final_archive_hypervolume"])
        augmented.append(
            {
                **row,
                "seed": seed,
                "final_generation": int(row["final_generation"]),
                "final_archive_hypervolume": final_hv,
                "final_diversity": float(row["final_diversity"]),
                "archive_size": float(row["archive_size"]),
                "control_steps": float(row["control_steps"]),
                "evaluations": float(row["evaluations"]),
                "wall_time_seconds": float(row["wall_time_seconds"]),
                "warmup_archive_hypervolume": warmup_hv,
                "hv_gain_after_warmup": final_hv - warmup_hv,
                "hv_auc_after_warmup": _time_average_after_warmup(
                    generations,
                    "archive_hypervolume",
                    warmup_generation,
                ),
                "diversity_auc_after_warmup": _time_average_after_warmup(
                    generations,
                    "population_diversity",
                    warmup_generation,
                ),
            }
        )
    return augmented, generation_by_run


def _group_by_method(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["method_name"])].append(row)
    return dict(grouped)


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [
        "final_archive_hypervolume",
        "final_diversity",
        "warmup_archive_hypervolume",
        "hv_gain_after_warmup",
        "hv_auc_after_warmup",
        "diversity_auc_after_warmup",
        "archive_size",
        "control_steps",
        "evaluations",
        "wall_time_seconds",
    ]
    grouped = _group_by_method(rows)
    output: list[dict[str, Any]] = []
    for method in METHOD_ORDER:
        method_rows = grouped.get(method, [])
        if not method_rows:
            continue
        for metric in metrics:
            values = [float(row[metric]) for row in method_rows]
            stats = _metric_stats(values)
            output.append(
                {
                    "method_name": method,
                    "metric": metric,
                    "seed_count": len(values),
                    **stats,
                }
            )
    return output


def _paired_differences(
    rows: list[dict[str, Any]],
    metric: str,
) -> dict[str, dict[str, Any]]:
    by_seed_method: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_seed_method[int(row["seed"])][str(row["method_name"])] = row

    result: dict[str, dict[str, Any]] = {}
    for baseline in FIXED_METHODS:
        diffs: list[float] = []
        wins = ties = losses = 0
        for method_rows in by_seed_method.values():
            if "bogp_current" not in method_rows or baseline not in method_rows:
                continue
            diff = float(method_rows["bogp_current"][metric]) - float(method_rows[baseline][metric])
            diffs.append(diff)
            if diff > 1.0e-12:
                wins += 1
            elif diff < -1.0e-12:
                losses += 1
            else:
                ties += 1
        result[baseline] = {
            **_metric_stats(diffs),
            "win_count": wins,
            "tie_count": ties,
            "loss_count": losses,
            **_safe_wilcoxon(diffs),
        }

    best_fixed_diffs: list[float] = []
    wins = ties = losses = 0
    for method_rows in by_seed_method.values():
        if "bogp_current" not in method_rows:
            continue
        fixed_values = [
            float(method_rows[method][metric])
            for method in FIXED_METHODS
            if method in method_rows
        ]
        if not fixed_values:
            continue
        diff = float(method_rows["bogp_current"][metric]) - max(fixed_values)
        best_fixed_diffs.append(diff)
        if diff > 1.0e-12:
            wins += 1
        elif diff < -1.0e-12:
            losses += 1
        else:
            ties += 1
    result["best_fixed_per_seed"] = {
        **_metric_stats(best_fixed_diffs),
        "win_count": wins,
        "tie_count": ties,
        "loss_count": losses,
        **_safe_wilcoxon(best_fixed_diffs),
    }
    return result


def _control_summary(rows: list[dict[str, Any]], warmup_generation: int) -> dict[str, Any]:
    all_k_counter: Counter[int] = Counter()
    post_k_counter: Counter[int] = Counter()
    all_pc_values: list[float] = []
    all_pm_values: list[float] = []
    post_pc_values: list[float] = []
    post_pm_values: list[float] = []
    reward_values: list[float] = []
    control_steps: list[int] = []
    post_control_steps: list[int] = []
    for row in rows:
        if row["method_name"] != "bogp_current":
            continue
        records = _control_rows(Path(row["output_dir"]))
        control_steps.append(len(records))
        post_steps = 0
        for record in records:
            control = record["control"]
            k_value = int(control["update_period"])
            pc = float(control["crossover_rate"])
            pm = float(control["mutation_rate"])
            all_k_counter[k_value] += 1
            all_pc_values.append(pc)
            all_pm_values.append(pm)
            if int(record["start_generation"]) >= warmup_generation:
                post_steps += 1
                post_k_counter[k_value] += 1
                post_pc_values.append(pc)
                post_pm_values.append(pm)
            reward = record.get("reward", {})
            if "total" in reward:
                reward_values.append(float(reward["total"]))
        post_control_steps.append(post_steps)
    return {
        "k_counts_all": dict(sorted(all_k_counter.items())),
        "k_counts_after_warmup": dict(sorted(post_k_counter.items())),
        "p_c_mean_all": mean(all_pc_values) if all_pc_values else 0.0,
        "p_m_mean_all": mean(all_pm_values) if all_pm_values else 0.0,
        "p_c_mean_after_warmup": mean(post_pc_values) if post_pc_values else 0.0,
        "p_m_mean_after_warmup": mean(post_pm_values) if post_pm_values else 0.0,
        "reward_mean": mean(reward_values) if reward_values else 0.0,
        "control_steps_mean": mean(control_steps) if control_steps else 0.0,
        "post_warmup_control_steps_mean": mean(post_control_steps) if post_control_steps else 0.0,
    }


def _generation_metric_summary(
    rows: list[dict[str, Any]],
    generation_by_run: dict[tuple[str, int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    grouped = _group_by_method(rows)
    output: list[dict[str, Any]] = []
    metrics = [
        "archive_hypervolume",
        "population_diversity",
        "archive_size",
    ]
    for method in METHOD_ORDER:
        method_rows = grouped.get(method, [])
        if not method_rows:
            continue
        generations = sorted(
            {
                int(row["generation"])
                for method_row in method_rows
                for row in generation_by_run[(method, int(method_row["seed"]))]
            }
        )
        for generation in generations:
            out_row: dict[str, Any] = {
                "method_name": method,
                "generation": generation,
            }
            for metric in metrics:
                values = [
                    float(row[metric])
                    for method_row in method_rows
                    for row in generation_by_run[(method, int(method_row["seed"]))]
                    if int(row["generation"]) == generation
                ]
                if values:
                    stats = _metric_stats(values)
                    out_row[f"{metric}_mean"] = stats["mean"]
                    out_row[f"{metric}_std"] = stats["std"]
            output.append(out_row)
    return output


def _plot_final_metrics(output_dir: Path, aggregate: dict[str, dict[str, dict[str, float]]]) -> None:
    methods = [method for method in METHOD_ORDER if method in aggregate]
    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, metric, ylabel, title in (
        (
            axes[0],
            "final_archive_hypervolume",
            "Final archive HV",
            "Final archive HV (mean +/- std)",
        ),
        (
            axes[1],
            "final_diversity",
            "Final diversity",
            "Final diversity (mean +/- std)",
        ),
    ):
        ax.bar(
            x,
            [aggregate[method][metric]["mean"] for method in methods],
            yerr=[aggregate[method][metric]["std"] for method in methods],
            capsize=4,
            color=[COLORS[method] for method in methods],
            edgecolor="#30343B",
        )
        ax.set_xticks(x, [METHOD_LABELS[method] for method in methods], rotation=18, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "main_final_hv_diversity.png", dpi=220)
    plt.close(fig)


def _plot_auc_metrics(output_dir: Path, aggregate: dict[str, dict[str, dict[str, float]]]) -> None:
    methods = [method for method in METHOD_ORDER if method in aggregate]
    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, metric, ylabel, title in (
        (
            axes[0],
            "hv_auc_after_warmup",
            "HV time-average after warm-up",
            "Post-warm-up HV-AUC (mean +/- std)",
        ),
        (
            axes[1],
            "hv_gain_after_warmup",
            "HV gain after warm-up",
            "Post-warm-up HV gain (mean +/- std)",
        ),
    ):
        ax.bar(
            x,
            [aggregate[method][metric]["mean"] for method in methods],
            yerr=[aggregate[method][metric]["std"] for method in methods],
            capsize=4,
            color=[COLORS[method] for method in methods],
            edgecolor="#30343B",
        )
        ax.set_xticks(x, [METHOD_LABELS[method] for method in methods], rotation=18, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "main_post_warmup_hv_auc_gain.png", dpi=220)
    plt.close(fig)


def _plot_hv_boxplot(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    grouped = _group_by_method(rows)
    methods = [method for method in METHOD_ORDER if method in grouped]
    values = [
        [float(row["final_archive_hypervolume"]) for row in grouped[method]]
        for method in methods
    ]
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    box = ax.boxplot(values, patch_artist=True, labels=[METHOD_LABELS[method] for method in methods])
    for patch, method in zip(box["boxes"], methods):
        patch.set_facecolor(COLORS[method])
        patch.set_alpha(0.72)
    ax.set_ylabel("Final archive HV")
    ax.set_title("Distribution of final archive HV over 100 seeds")
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=18)
    fig.tight_layout()
    fig.savefig(output_dir / "main_final_hv_boxplot.png", dpi=220)
    plt.close(fig)


def _plot_paired_diff(output_dir: Path, paired: dict[str, dict[str, Any]]) -> None:
    keys = [
        "plain_fixed_standard",
        "plain_fixed_high_mutation",
        "plain_fixed_high_crossover",
        "best_fixed_per_seed",
    ]
    labels = [
        "vs standard",
        "vs high mutation",
        "vs high crossover",
        "vs best fixed\nper seed",
    ]
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    ax.axhline(0.0, color="#30343B", linewidth=1.0)
    ax.bar(
        x,
        [paired[key]["mean"] for key in keys],
        yerr=[paired[key]["std"] for key in keys],
        capsize=4,
        color=["#D95F5F", "#D95F5F", "#D95F5F", "#7A4E76"],
        edgecolor="#30343B",
    )
    ax.set_xticks(x, labels)
    ax.set_ylabel("Final HV difference (bogp_current - baseline)")
    ax.set_title("Paired final HV difference over 100 seeds")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "main_paired_final_hv_difference.png", dpi=220)
    plt.close(fig)


def _plot_mean_history(
    output_dir: Path,
    generation_summary: list[dict[str, Any]],
    metric_prefix: str,
    ylabel: str,
    title: str,
    filename: str,
    warmup_generation: int,
) -> None:
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in generation_summary:
        by_method[str(row["method_name"])].append(row)
    fig, ax = plt.subplots(figsize=(9.8, 5.6))
    for method in METHOD_ORDER:
        rows = sorted(by_method.get(method, []), key=lambda item: int(item["generation"]))
        if not rows:
            continue
        generations = np.asarray([int(row["generation"]) for row in rows], dtype=float)
        means = np.asarray([float(row[f"{metric_prefix}_mean"]) for row in rows], dtype=float)
        stds = np.asarray([float(row[f"{metric_prefix}_std"]) for row in rows], dtype=float)
        ax.plot(generations, means, color=COLORS[method], linewidth=2.1, label=METHOD_LABELS[method])
        ax.fill_between(
            generations,
            means - stds,
            means + stds,
            color=COLORS[method],
            alpha=0.12,
            linewidth=0,
        )
    ax.axvline(
        warmup_generation,
        color="#30343B",
        linestyle="--",
        linewidth=1.3,
        label=f"warm-up boundary (g={warmup_generation})",
    )
    ax.set_xlabel("Generation")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / filename, dpi=220)
    plt.close(fig)


def _plot_hv_diversity_k_alignment(
    output_dir: Path,
    rows: list[dict[str, Any]],
    seed: int,
    warmup_generation: int,
) -> Path:
    method_row = next(
        (
            row
            for row in rows
            if row["method_name"] == "bogp_current" and int(row["seed"]) == seed
        ),
        None,
    )
    if method_row is None:
        raise ValueError(f"Missing bogp_current run for representative seed={seed}.")

    run_dir = Path(method_row["output_dir"])
    generations = sorted(_generation_rows(run_dir), key=lambda item: int(item["generation"]))
    controls = sorted(_control_rows(run_dir), key=lambda item: int(item["start_generation"]))

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

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10.5, 7.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.1, 1.1, 0.9]},
    )
    for axis in axes:
        axis.axvline(
            warmup_generation,
            color="#30343B",
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
        )
        for record in controls:
            start = int(record["start_generation"])
            if start == warmup_generation:
                continue
            axis.axvline(start, color="#9AA0A6", linestyle=":", linewidth=0.55, alpha=0.24)
        axis.grid(True, alpha=0.24)

    axes[0].plot(gen_x, hv_y, color="#D95F5F", linewidth=2.1, marker="o", markersize=2.8)
    axes[0].set_ylabel("Archive HV")
    axes[0].set_title(f"Representative seed={seed}: HV, diversity, and held update period k")

    axes[1].plot(gen_x, div_y, color="#3F8F72", linewidth=2.1, marker="o", markersize=2.8)
    axes[1].set_ylabel("Population diversity")

    if k_x:
        axes[2].plot(
            k_x,
            k_y,
            drawstyle="steps-post",
            color="#3B6EA8",
            linewidth=2.4,
            marker="s",
            markersize=3.4,
        )
    axes[2].set_yticks([1, 3, 5])
    axes[2].set_ylim(0.4, 5.6)
    axes[2].set_ylabel("Held k")
    axes[2].set_xlabel("Generation")
    axes[2].text(
        warmup_generation + 0.5,
        5.25,
        f"warm-up boundary g={warmup_generation}",
        color="#30343B",
        fontsize=9,
        va="center",
    )

    fig.tight_layout()
    path = output_dir / f"main_hv_diversity_k_alignment_seed{seed}.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)

    paper_dir = output_dir / "paper_labelled_figures"
    paper_dir.mkdir(exist_ok=True)
    shutil.copy2(path, paper_dir / path.name)
    return path


def _representative_seed(rows: list[dict[str, Any]]) -> int:
    bo_rows = [row for row in rows if row["method_name"] == "bogp_current"]
    values = sorted(float(row["final_archive_hypervolume"]) for row in bo_rows)
    target = median(values)
    return min(
        (int(row["seed"]) for row in bo_rows),
        key=lambda seed: abs(
            float(
                next(
                    row["final_archive_hypervolume"]
                    for row in bo_rows
                    if int(row["seed"]) == seed
                )
            )
            - target
        ),
    )


def _plot_representative_pareto(output_dir: Path, rows: list[dict[str, Any]], seed: int) -> Path:
    fig, ax = plt.subplots(figsize=(7.6, 5.8))
    plotted = False
    for method in METHOD_ORDER:
        method_row = next(
            (row for row in rows if row["method_name"] == method and int(row["seed"]) == seed),
            None,
        )
        if method_row is None:
            continue
        archive_path = Path(str(method_row["output_dir"])) / "unique_objective_archive.json"
        values = [
            item["objective_values"]
            for item in _read_json(archive_path)
            if len(item["objective_values"]) == 2
        ]
        if not values:
            continue
        ax.scatter(
            [value[0] for value in values],
            [value[1] for value in values],
            s=38,
            alpha=0.78,
            label=PARETO_LABELS[method],
            color=COLORS[method],
            marker=MARKERS[method],
            edgecolors="black",
            linewidths=0.35,
        )
        plotted = True
    if not plotted:
        plt.close(fig)
        return output_dir / "main_representative_pareto_front.png"
    ax.set_xlabel("training NRMSE objective")
    ax.set_ylabel("tree size objective")
    ax.set_title(f"Representative final Pareto archive (seed={seed})")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = output_dir / "main_representative_pareto_front.png"
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def _aggregate_lookup(aggregate_rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    lookup: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for row in aggregate_rows:
        lookup[str(row["method_name"])][str(row["metric"])] = {
            key: float(row[key])
            for key in ("mean", "std", "median", "min", "max")
        }
    return dict(lookup)


def _paired_rows_for_csv(
    paired_by_metric: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric, paired in paired_by_metric.items():
        for comparison, values in paired.items():
            rows.append(
                {
                    "metric": metric,
                    "comparison": comparison,
                    **values,
                }
            )
    return rows


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _fmt(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def _tex_k_counts(counts: dict[str, int] | dict[int, int]) -> str:
    items = sorted((int(key), int(value)) for key, value in counts.items())
    return r",\quad ".join(f"k={key}: {value}" for key, value in items)


def _tex_table_final(aggregate: dict[str, dict[str, dict[str, float]]]) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Friedman-I 本実験の最終指標}",
        r"\label{tab:main-final-results}",
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"手法 & HV平均 & HV標準偏差 & 多様性平均 & 多様性標準偏差 & warm-up後HV増加 & HV-AUC \\",
        r"\midrule",
    ]
    for method in METHOD_ORDER:
        row = aggregate[method]
        lines.append(
            "{method} & {hv_mean} & {hv_std} & {div_mean} & {div_std} & {gain} & {auc} \\\\".format(
                method=METHOD_TEX[method],
                hv_mean=_fmt(row["final_archive_hypervolume"]["mean"]),
                hv_std=_fmt(row["final_archive_hypervolume"]["std"]),
                div_mean=_fmt(row["final_diversity"]["mean"]),
                div_std=_fmt(row["final_diversity"]["std"]),
                gain=_fmt(row["hv_gain_after_warmup"]["mean"]),
                auc=_fmt(row["hv_auc_after_warmup"]["mean"]),
            )
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines)


def _tex_table_paired(paired: dict[str, dict[str, Any]]) -> str:
    labels = {
        "plain_fixed_standard": r"\texttt{bo\_current} - standard",
        "plain_fixed_high_mutation": r"\texttt{bo\_current} - high mutation",
        "plain_fixed_high_crossover": r"\texttt{bo\_current} - high crossover",
        "best_fixed_per_seed": r"\texttt{bo\_current} - best fixed per seed",
    }
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{\texttt{bo\_current} と固定率GPの seed 内 final HV 差分}",
        r"\label{tab:main-paired-hv}",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"比較 & 差分平均 & 差分標準偏差 & win & tie & loss & Wilcoxon $p$ \\",
        r"\midrule",
    ]
    for key in (
        "plain_fixed_standard",
        "plain_fixed_high_mutation",
        "plain_fixed_high_crossover",
        "best_fixed_per_seed",
    ):
        row = paired[key]
        lines.append(
            "{label} & {mean} & {std} & {win} & {tie} & {loss} & {pval} \\\\".format(
                label=labels[key],
                mean=_fmt(row["mean"]),
                std=_fmt(row["std"]),
                win=int(row["win_count"]),
                tie=int(row["tie_count"]),
                loss=int(row["loss_count"]),
                pval=_fmt(row["p_value"], 4),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def _write_markdown_summary(
    output_dir: Path,
    metadata: dict[str, Any],
    aggregate: dict[str, dict[str, dict[str, float]]],
    paired_final_hv: dict[str, dict[str, Any]],
    control_summary: dict[str, Any],
) -> None:
    lines = [
        "# Friedman-I bo_current 本実験まとめ",
        "",
        f"- output: `{_rel(output_dir)}`",
        f"- warm-up generations: `{metadata['warmup_generations']}`",
        f"- evaluation generations: `{metadata['evaluation_generations']}`",
        f"- total generations: `{metadata['total_generations']}`",
        f"- seed count: `{metadata['seed_count']}`",
        f"- evaluations/run: `{metadata['evaluations_per_run']}`",
        "",
        "## Final Metrics",
        "",
        "| method | final HV mean | final HV std | final diversity mean | final diversity std | HV gain after warm-up | HV-AUC after warm-up |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method in METHOD_ORDER:
        row = aggregate[method]
        lines.append(
            "| {method} | {hv_mean:.6f} | {hv_std:.6f} | {div_mean:.6f} | {div_std:.6f} | {gain:.6f} | {auc:.6f} |".format(
                method=method,
                hv_mean=row["final_archive_hypervolume"]["mean"],
                hv_std=row["final_archive_hypervolume"]["std"],
                div_mean=row["final_diversity"]["mean"],
                div_std=row["final_diversity"]["std"],
                gain=row["hv_gain_after_warmup"]["mean"],
                auc=row["hv_auc_after_warmup"]["mean"],
            )
        )
    lines.extend(
        [
            "",
            "## Paired Final HV Differences",
            "",
            "| comparison | mean | std | win | tie | loss | Wilcoxon p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key, label in (
        ("plain_fixed_standard", "bo_current - standard"),
        ("plain_fixed_high_mutation", "bo_current - high mutation"),
        ("plain_fixed_high_crossover", "bo_current - high crossover"),
        ("best_fixed_per_seed", "bo_current - best fixed per seed"),
    ):
        row = paired_final_hv[key]
        lines.append(
            "| {label} | {mean:.6f} | {std:.6f} | {win} | {tie} | {loss} | {p:.4f} |".format(
                label=label,
                mean=row["mean"],
                std=row["std"],
                win=row["win_count"],
                tie=row["tie_count"],
                loss=row["loss_count"],
                p=row["p_value"],
            )
        )
    lines.extend(
        [
            "",
            "## Control Summary",
            "",
            f"- k counts all: `{control_summary['k_counts_all']}`",
            f"- k counts after warm-up: `{control_summary['k_counts_after_warmup']}`",
            f"- mean p_c after warm-up: `{control_summary['p_c_mean_after_warmup']:.4f}`",
            f"- mean p_m after warm-up: `{control_summary['p_m_mean_after_warmup']:.4f}`",
        ]
    )
    (output_dir / "main_bo_current_friedman_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_latex_report(
    report_path: Path,
    output_dir: Path,
    metadata: dict[str, Any],
    aggregate: dict[str, dict[str, dict[str, float]]],
    paired_final_hv: dict[str, dict[str, Any]],
    control_summary: dict[str, Any],
    representative_seed: int,
) -> None:
    hv_best = max(
        METHOD_ORDER,
        key=lambda method: aggregate[method]["final_archive_hypervolume"]["mean"],
    )
    bogp_vs_standard = paired_final_hv["plain_fixed_standard"]
    bogp_vs_high_mut = paired_final_hv["plain_fixed_high_mutation"]
    alignment_fig = output_dir / f"main_hv_diversity_k_alignment_seed{representative_seed}.png"
    report = rf"""% !TEX program = lualatex
\documentclass[a4paper,11pt]{{ltjsarticle}}

\usepackage{{amsmath,amssymb}}
\usepackage{{booktabs}}
\usepackage{{geometry}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\geometry{{margin=24mm}}

\title{{Friedman-I 本実験結果メモ\\
\large warm-up 除外世代定義に基づく \texttt{{bo\_current}} の評価}}
\author{{}}
\date{{{datetime.now().strftime('%Y年%m月%d日')}}}

\newcommand{{\HV}}{{\mathrm{{HV}}}}

\begin{{document}}
\maketitle

\section{{目的}}

本メモは，Friedman-I シンボリック回帰問題に対して，
現行の提案手法である \texttt{{bo\_current}} を適用した本実験結果をまとめるものである．
今回から，ユーザー指定の「世代数」は BO の warm-up を含まない
本制御・本評価区間の世代数として扱う．
したがって，本実験の設定は
\[
  \text{{総世代数}}
  =
  \text{{warm-up 世代数}}
  +
  \text{{本評価世代数}}
  =
  {metadata['warmup_generations']} + {metadata['evaluation_generations']}
  =
  {metadata['total_generations']}
\]
である．

\section{{問題選定の理由}}

対象問題は Friedman-I 型のシンボリック回帰である．
入力変数を \(x_1,\ldots,x_5\) とすると，目標関数は
\[
  y =
  10\sin(\pi x_1 x_2)
  +20(x_3-0.5)^2
  +10x_4
  +5x_5
\]
で与えられる．各入力は \(x_i\sim U(0,1)\) から生成し，
訓練点数は 200，テスト点数は 200 とした．

Friedman-I を採用した理由は次の通りである．
第一に，McDermott らの ``Genetic Programming Needs Better Benchmarks'' は，
GP 研究で単純すぎる toy benchmark のみを用いることの危険性を指摘している．
Friedman-I は，線形項，二次項，三角関数，変数間相互作用を含むため，
単純な \(y=x^2+x\) 型の smoke test よりも本実験に適している．
第二に，White らの ``Better GP Benchmarks'' は，
benchmark 選定と実験厳密性，複数 seed による評価の重要性を述べている．
本実験ではこの考えに従い，固定した問題設定のもとで 100 seed を用いる．
第三に，La Cava らの SRBench は，symbolic regression を
再現可能な benchmark として扱う枠組みを示しており，
精度とモデル複雑さの両方を考慮する評価と相性がよい．
さらに Liu らの MOGP symbolic regression の研究では，
NSGA-II による accuracy--complexity 探索で低複雑度個体が過剰に複製され，
探索効率や多様性に影響する現象が報告されている．
これは本研究の状態観測量である \(\HV\)，直近改善量，多様性，
平均木サイズ，停滞長を用いた閉ループ制御の意義と対応している．

\section{{目的関数と評価指標}}

GP の目的関数は 2 目的である．
第1目的は訓練データに対する正規化 RMSE，
第2目的は式木サイズであり，いずれも最小化する．
すなわち，個体 \(T\) に対して
\[
  f_1(T)=\mathrm{{NRMSE}}_{{\mathrm{{train}}}}(T),
  \qquad
  f_2(T)=|T|
\]
を考える．
本実験では，探索の成果集合である archive に基づく final archive \(\HV\) を主指標とし，
population diversity を副指標として用いる．
また，warm-up 後の挙動を評価するため，
\[
  \Delta \HV_{{\mathrm{{post}}}}
  =
  \HV_{{g={metadata['total_generations']}}}
  -
  \HV_{{g={metadata['warmup_generations']}}}
\]
と，warm-up 後の \(\HV\) 時間平均を用いる．

\section{{実験条件}}

比較対象は，固定率 GP 3 条件と，提案法 \texttt{{bo\_current}} である．
全手法で同じ多目的 GP エンジンを用い，
違いは \(p_c\)，\(p_m\)，更新周期 \(k\) の決定方法のみに限定した．

\begin{{table}}[htbp]
\centering
\caption{{比較した制御条件}}
\label{{tab:main-methods}}
\begin{{tabular}}{{lll}}
\toprule
手法 & 設定 & 位置づけ \\
\midrule
\texttt{{plain\_fixed\_standard}} & \(p_c=0.80,\ p_m=0.05\) & 標準的な固定率 GP \\
\texttt{{plain\_fixed\_high\_mutation}} & \(p_c=0.70,\ p_m=0.20\) & 突然変異を強めた固定率 GP \\
\texttt{{plain\_fixed\_high\_crossover}} & \(p_c=0.90,\ p_m=0.05\) & 交叉を強めた固定率 GP \\
\texttt{{bogp\_current}} & \(p_c,p_m,k\) を BO で逐次決定 & 提案法の現行版 \\
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{table}}[htbp]
\centering
\caption{{本実験の条件}}
\label{{tab:main-setting}}
\begin{{tabular}}{{ll}}
\toprule
項目 & 設定 \\
\midrule
対象問題 & Friedman-I symbolic regression \\
seed & \(0,\ldots,{metadata['seed_count'] - 1}\) \\
seed 数 & {metadata['seed_count']} \\
集団サイズ & {metadata['population_size']} \\
warm-up 世代数 & {metadata['warmup_generations']} \\
本評価世代数 & {metadata['evaluation_generations']} \\
総世代数 & {metadata['total_generations']} \\
評価回数 & {metadata['evaluations_per_run']} / run \\
目的数 & 2 \\
archive key & topology + node value \\
HV 参照点 & \((1.0,1.0)\) \\
\bottomrule
\end{{tabular}}
\end{{table}}

現行の \texttt{{bo\_current}} では，
\(k\in\{{1,3,5\}}\) に対して各 \(k\) を2回ずつ warm-up する．
sequential warm-up のため，世代数としては
\[
  1+1+3+3+5+5=18
\]
世代が warm-up 区間に対応する．
その後の {metadata['evaluation_generations']} 世代を本制御・本評価区間として扱った．

\section{{結果}}

{_tex_table_final(aggregate)}

表\ref{{tab:main-final-results}}より，
final archive \(\HV\) 平均が最も高い手法は {METHOD_TEX[hv_best]} であった．
\texttt{{bogp\_current}} は標準固定率 GP に対して，
seed 内 final HV 差分平均
{_fmt(bogp_vs_standard['mean'])} を示した．
一方，高突然変異固定率 GP に対する差分平均は
{_fmt(bogp_vs_high_mut['mean'])} であった．

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{{_rel(output_dir / 'main_final_hv_diversity.png')}}}
  \caption{{final archive HV と final diversity の平均 \(\pm\) 標準偏差}}
  \label{{fig:main-final-hv-diversity}}
\end{{figure}}

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=0.92\linewidth]{{{_rel(output_dir / 'main_final_hv_boxplot.png')}}}
  \caption{{100 seed における final archive HV の分布}}
  \label{{fig:main-final-hv-boxplot}}
\end{{figure}}

図\ref{{fig:main-hv-progress}}に archive \(\HV\) の推移を示す．
破線は warm-up 終了世代 \(g={metadata['warmup_generations']}\) を表す．
この図により，初期区間を含めた収束過程と，
warm-up 後の本評価区間でどの手法が Pareto archive を押し上げたかを分けて確認できる．

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{{_rel(output_dir / 'main_hv_mean_progress.png')}}}
  \caption{{archive HV の世代推移．帯は標準偏差を示す}}
  \label{{fig:main-hv-progress}}
\end{{figure}}

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{{_rel(output_dir / 'main_diversity_mean_progress.png')}}}
  \caption{{population diversity の世代推移．帯は標準偏差を示す}}
  \label{{fig:main-diversity-progress}}
\end{{figure}}

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{{_rel(output_dir / 'main_post_warmup_hv_auc_gain.png')}}}
  \caption{{warm-up 後の HV-AUC と HV 増加量}}
  \label{{fig:main-post-warmup}}
\end{{figure}}

\subsection{{seed 内差分}}

{_tex_table_paired(paired_final_hv)}

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=0.92\linewidth]{{{_rel(output_dir / 'main_paired_final_hv_difference.png')}}}
  \caption{{\texttt{{bo\_current}} と固定率 GP の seed 内 final HV 差分}}
  \label{{fig:main-paired-hv}}
\end{{figure}}

\subsection{{\texttt{{bo\_current}} の制御傾向}}

\texttt{{bo\_current}} の更新周期 \(k\) は，単なる選択回数だけでなく，
どの世代区間で保持されたかを確認する必要がある．
図\ref{{fig:main-k-alignment}}に，代表 seed={representative_seed} における
archive \(\HV\)，population diversity，および保持された更新周期 \(k\) の対応を示す．
ここで \(k\) は，その世代の結果を表す値ではなく，
制御更新時点で選択され，次の更新時点までの区間に適用された制御入力である．
したがって，\(k\) の意味は，同じ世代の \(\HV\) や多様性ではなく，
その後の区間で \(\HV\) や多様性がどのように変化したかと対応づけて読むべきである．

補助情報として，全制御ステップにおける \(k\) 選択回数は
\[
  {_tex_k_counts(control_summary['k_counts_all'])}
\]
であり，warm-up 後に限定すると
\[
  {_tex_k_counts(control_summary['k_counts_after_warmup'])}
\]
であった．
warm-up 後の平均操作率は
\[
  \bar{{p}}_c={_fmt(control_summary['p_c_mean_after_warmup'], 4)},
  \qquad
  \bar{{p}}_m={_fmt(control_summary['p_m_mean_after_warmup'], 4)}
\]
であった．

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=\linewidth]{{{_rel(alignment_fig)}}}
  \caption{{代表 seed={representative_seed} における archive HV，population diversity，更新周期 \(k\) の世代対応．\(k\) は選択後の区間に保持される制御入力である．}}
  \label{{fig:main-k-alignment}}
\end{{figure}}

\begin{{figure}}[htbp]
  \centering
  \includegraphics[width=0.82\linewidth]{{{_rel(output_dir / 'main_representative_pareto_front.png')}}}
  \caption{{代表 seed={representative_seed} における最終 Pareto archive}}
  \label{{fig:main-pareto}}
\end{{figure}}

\section{{考察}}

本実験では，warm-up を世代数に含めず，
BO が初期観測を終えた後の {metadata['evaluation_generations']} 世代を
本評価区間として明示した．
これにより，従来の 30 世代実験よりも
\texttt{{bo\_current}} が状態観測に基づいて制御入力を選ぶ期間を長く確保できた．

結果の解釈では，final archive \(\HV\) を主指標としつつ，
population diversity と warm-up 後の \(\HV\) 改善量を併せて見る必要がある．
Friedman-I は accuracy--complexity の 2 目的問題であるため，
単に誤差を下げるだけではなく，低複雑度の式と高精度の式の
トレードオフをどれだけ広く獲得できるかが重要である．
そのため，archive \(\HV\) は成果集合の品質を表し，
population diversity は探索状態の偏りや早期収束を読む補助指標となる．

また，強い固定率 baseline として高突然変異設定を置いたことにより，
提案法の評価は単なる標準固定率 GP との比較に留まらない．
\texttt{{bo\_current}} が標準固定率を上回る場合でも，
高突然変異固定率や seed ごとの best fixed に対して十分に優位でなければ，
「閉ループ制御の枠組みは有望だが，報酬設計や BO 制御器には改善余地がある」
と解釈するのが妥当である．

\section{{参照した文献と反映箇所}}

\begin{{itemize}}
  \item McDermott et al. (2012), ``Genetic Programming Needs Better Benchmarks'':
  toy problem だけに依存せず，説明しやすくも単純すぎない benchmark を選ぶ根拠として参照した．
  \item White et al. (2013), ``Better GP Benchmarks'':
  複数 seed，比較 baseline，出力ログを揃えた実験設計の根拠として参照した．
  \item La Cava et al. (2021), ``Contemporary Symbolic Regression Methods and their Relative Performance / SRBench'':
  symbolic regression を train/test split を持つ benchmark として扱い，
  accuracy と model complexity を重視する方向性の根拠として参照した．
  \item Liu et al. (2022), ``Evolvability Degeneration in Multi-Objective Genetic Programming for Symbolic Regression'':
  accuracy--complexity MOGP における低複雑度個体の過剰複製や多様性低下の問題を，
  本研究の状態観測量と報酬設計の背景として参照した．
  \item Li and Yao (2019), ``Quality evaluation of solution sets in multiobjective optimisation: a survey'':
  Pareto archive の品質評価において，HV と多様性など複数観点を併用する考え方の根拠として参照した．
\end{{itemize}}

\end{{document}}
"""
    report_path.write_text(report, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Experiment output directory produced by run_main_bo_current_friedman_experiment.py.",
    )
    parser.add_argument(
        "--report-path",
        default=str(ROOT / "notes" / "main_bo_current_friedman_report.tex"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    report_path = Path(args.report_path)
    metadata = _read_json(output_dir / "main_experiment_metadata.json")
    warmup_generation = int(metadata["warmup_generations"])

    summary_rows = _read_csv(output_dir / "summary_by_seed.csv")
    augmented_rows, generation_by_run = _augment_rows(summary_rows, warmup_generation)
    aggregate_rows = _aggregate_rows(augmented_rows)
    aggregate = _aggregate_lookup(aggregate_rows)
    paired_by_metric = {
        "final_archive_hypervolume": _paired_differences(
            augmented_rows,
            "final_archive_hypervolume",
        ),
        "hv_gain_after_warmup": _paired_differences(
            augmented_rows,
            "hv_gain_after_warmup",
        ),
        "hv_auc_after_warmup": _paired_differences(
            augmented_rows,
            "hv_auc_after_warmup",
        ),
    }
    control_summary = _control_summary(augmented_rows, warmup_generation)
    generation_summary = _generation_metric_summary(augmented_rows, generation_by_run)
    rep_seed = _representative_seed(augmented_rows)

    _write_csv(
        output_dir / "main_derived_by_seed.csv",
        augmented_rows,
        [
            "problem_name",
            "method_name",
            "seed",
            "final_generation",
            "final_archive_hypervolume",
            "final_diversity",
            "warmup_archive_hypervolume",
            "hv_gain_after_warmup",
            "hv_auc_after_warmup",
            "diversity_auc_after_warmup",
            "archive_size",
            "control_steps",
            "evaluations",
            "wall_time_seconds",
            "output_dir",
        ],
    )
    _write_csv(
        output_dir / "main_aggregate_summary.csv",
        aggregate_rows,
        ["method_name", "metric", "seed_count", "mean", "std", "median", "min", "max"],
    )
    _write_csv(
        output_dir / "main_paired_differences.csv",
        _paired_rows_for_csv(paired_by_metric),
        [
            "metric",
            "comparison",
            "mean",
            "std",
            "median",
            "min",
            "max",
            "win_count",
            "tie_count",
            "loss_count",
            "statistic",
            "p_value",
        ],
    )
    _write_csv(
        output_dir / "main_generation_metric_summary.csv",
        generation_summary,
        [
            "method_name",
            "generation",
            "archive_hypervolume_mean",
            "archive_hypervolume_std",
            "population_diversity_mean",
            "population_diversity_std",
            "archive_size_mean",
            "archive_size_std",
        ],
    )
    analysis_payload = {
        "metadata": metadata,
        "aggregate": aggregate,
        "paired_differences": paired_by_metric,
        "control_summary": control_summary,
        "representative_seed": rep_seed,
        "k_alignment_plot": str(
            output_dir / f"main_hv_diversity_k_alignment_seed{rep_seed}.png"
        ),
    }
    _write_json(output_dir / "main_analysis_summary.json", analysis_payload)

    _plot_final_metrics(output_dir, aggregate)
    _plot_auc_metrics(output_dir, aggregate)
    _plot_hv_boxplot(output_dir, augmented_rows)
    _plot_paired_diff(output_dir, paired_by_metric["final_archive_hypervolume"])
    _plot_mean_history(
        output_dir=output_dir,
        generation_summary=generation_summary,
        metric_prefix="archive_hypervolume",
        ylabel="Archive HV",
        title="Archive HV by generation",
        filename="main_hv_mean_progress.png",
        warmup_generation=warmup_generation,
    )
    _plot_mean_history(
        output_dir=output_dir,
        generation_summary=generation_summary,
        metric_prefix="population_diversity",
        ylabel="Population diversity",
        title="Population diversity by generation",
        filename="main_diversity_mean_progress.png",
        warmup_generation=warmup_generation,
    )
    _plot_hv_diversity_k_alignment(
        output_dir=output_dir,
        rows=augmented_rows,
        seed=rep_seed,
        warmup_generation=warmup_generation,
    )
    _plot_representative_pareto(output_dir, augmented_rows, rep_seed)
    _write_markdown_summary(
        output_dir,
        metadata,
        aggregate,
        paired_by_metric["final_archive_hypervolume"],
        control_summary,
    )
    _write_latex_report(
        report_path=report_path,
        output_dir=output_dir,
        metadata=metadata,
        aggregate=aggregate,
        paired_final_hv=paired_by_metric["final_archive_hypervolume"],
        control_summary=control_summary,
        representative_seed=rep_seed,
    )
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "report_path": str(report_path),
                "analysis_summary": str(output_dir / "main_analysis_summary.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
