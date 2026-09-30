from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHOD_ORDER = (
    "plain_fixed_standard",
    "plain_fixed_high_mutation",
    "plain_fixed_high_crossover",
    "bogp_current",
)

METHOD_LABELS = {
    "plain_fixed_standard": "Fixed standard\n(p_c=0.80, p_m=0.05)",
    "plain_fixed_high_mutation": "Fixed high mutation\n(p_c=0.70, p_m=0.20)",
    "plain_fixed_high_crossover": "Fixed high crossover\n(p_c=0.90, p_m=0.05)",
    "bogp_current": "BO-controlled GP\n(bo_current)",
}

COLORS = {
    "plain_fixed_standard": "#6A8CAF",
    "plain_fixed_high_mutation": "#7BAE7F",
    "plain_fixed_high_crossover": "#C48A5A",
    "bogp_current": "#D95F5F",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _group_by_method(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["method_name"]].append(row)
    return dict(grouped)


def _metric_stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "std": pstdev(values) if len(values) > 1 else 0.0,
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }


def _method_stats(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    grouped = _group_by_method(rows)
    stats: dict[str, dict[str, float]] = {}
    for method_name in METHOD_ORDER:
        method_rows = grouped.get(method_name, [])
        if not method_rows:
            continue
        stats[method_name] = {
            "final_archive_hypervolume_mean": _metric_stats(
                [_float(row, "final_archive_hypervolume") for row in method_rows]
            )["mean"],
            "final_archive_hypervolume_std": _metric_stats(
                [_float(row, "final_archive_hypervolume") for row in method_rows]
            )["std"],
            "final_archive_hypervolume_median": _metric_stats(
                [_float(row, "final_archive_hypervolume") for row in method_rows]
            )["median"],
            "final_diversity_mean": _metric_stats(
                [_float(row, "final_diversity") for row in method_rows]
            )["mean"],
            "final_diversity_std": _metric_stats(
                [_float(row, "final_diversity") for row in method_rows]
            )["std"],
            "archive_size_mean": _metric_stats(
                [_float(row, "archive_size") for row in method_rows]
            )["mean"],
            "archive_size_std": _metric_stats(
                [_float(row, "archive_size") for row in method_rows]
            )["std"],
            "control_steps_mean": _metric_stats(
                [_float(row, "control_steps") for row in method_rows]
            )["mean"],
            "wall_time_seconds_mean": _metric_stats(
                [_float(row, "wall_time_seconds") for row in method_rows]
            )["mean"],
        }
    return stats


def _paired_differences(
    rows: list[dict[str, str]],
    metric: str,
) -> dict[str, dict[str, Any]]:
    by_seed_method: dict[int, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_seed_method[int(row["seed"])][row["method_name"]] = row

    result: dict[str, dict[str, Any]] = {}
    for baseline in METHOD_ORDER:
        if baseline == "bogp_current":
            continue
        diffs: list[float] = []
        wins = ties = losses = 0
        for method_rows in by_seed_method.values():
            if "bogp_current" not in method_rows or baseline not in method_rows:
                continue
            diff = _float(method_rows["bogp_current"], metric) - _float(
                method_rows[baseline],
                metric,
            )
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
        }

    best_fixed_diffs: list[float] = []
    wins = ties = losses = 0
    fixed_methods = [method for method in METHOD_ORDER if method != "bogp_current"]
    for method_rows in by_seed_method.values():
        if "bogp_current" not in method_rows:
            continue
        fixed_values = [
            _float(method_rows[method], metric)
            for method in fixed_methods
            if method in method_rows
        ]
        if not fixed_values:
            continue
        diff = _float(method_rows["bogp_current"], metric) - max(fixed_values)
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
    }
    return result


def _read_control_records(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "control_records.jsonl"
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def _control_summary(output_dir: Path, rows: list[dict[str, str]]) -> dict[str, Any]:
    k_counter: Counter[int] = Counter()
    pc_values: list[float] = []
    pm_values: list[float] = []
    reward_values: list[float] = []
    control_steps: list[int] = []
    for row in rows:
        if row["method_name"] != "bogp_current":
            continue
        records = _read_control_records(Path(row["output_dir"]))
        control_steps.append(len(records))
        for record in records:
            control = record["control"]
            k_counter[int(control["update_period"])] += 1
            pc_values.append(float(control["crossover_rate"]))
            pm_values.append(float(control["mutation_rate"]))
            reward = record.get("reward", {})
            if "total" in reward:
                reward_values.append(float(reward["total"]))
    return {
        "k_counts": dict(sorted(k_counter.items())),
        "p_c_mean": mean(pc_values) if pc_values else 0.0,
        "p_m_mean": mean(pm_values) if pm_values else 0.0,
        "reward_mean": mean(reward_values) if reward_values else 0.0,
        "control_steps_mean": mean(control_steps) if control_steps else 0.0,
    }


def _plot_final_metrics(
    output_dir: Path,
    stats: dict[str, dict[str, float]],
) -> None:
    methods = [method for method in METHOD_ORDER if method in stats]
    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, mean_key, std_key, ylabel, title in (
        (
            axes[0],
            "final_archive_hypervolume_mean",
            "final_archive_hypervolume_std",
            "Final archive HV",
            "Final archive HV (mean +/- std)",
        ),
        (
            axes[1],
            "final_diversity_mean",
            "final_diversity_std",
            "Final diversity",
            "Final diversity (mean +/- std)",
        ),
    ):
        ax.bar(
            x,
            [stats[method][mean_key] for method in methods],
            yerr=[stats[method][std_key] for method in methods],
            capsize=4,
            color=[COLORS[method] for method in methods],
            edgecolor="#30343B",
        )
        ax.set_xticks(x, [METHOD_LABELS[method] for method in methods], rotation=18, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "seminar_final_hv_diversity.png", dpi=220)
    plt.close(fig)


def _plot_hv_boxplot(
    output_dir: Path,
    rows: list[dict[str, str]],
) -> None:
    grouped = _group_by_method(rows)
    methods = [method for method in METHOD_ORDER if method in grouped]
    values = [
        [_float(row, "final_archive_hypervolume") for row in grouped[method]]
        for method in methods
    ]
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    box = ax.boxplot(values, patch_artist=True, labels=[METHOD_LABELS[m] for m in methods])
    for patch, method in zip(box["boxes"], methods):
        patch.set_facecolor(COLORS[method])
        patch.set_alpha(0.72)
    ax.set_ylabel("Final archive HV")
    ax.set_title("Distribution of final archive HV over 100 seeds")
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=18)
    fig.tight_layout()
    fig.savefig(output_dir / "seminar_final_hv_boxplot.png", dpi=220)
    plt.close(fig)


def _plot_paired_diff(
    output_dir: Path,
    paired: dict[str, dict[str, Any]],
) -> None:
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
    fig.savefig(output_dir / "seminar_paired_hv_difference.png", dpi=220)
    plt.close(fig)


def _plot_k_counts(
    output_dir: Path,
    control_summary: dict[str, Any],
) -> None:
    counts = control_summary["k_counts"]
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    k_values = list(counts.keys())
    ax.bar(
        [str(k) for k in k_values],
        [counts[k] for k in k_values],
        color="#D95F5F",
        edgecolor="#30343B",
    )
    ax.set_xlabel("Selected update period k")
    ax.set_ylabel("Selection count")
    ax.set_title("bo_current update-period selections over 100 seeds")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "seminar_k_selection_counts.png", dpi=220)
    plt.close(fig)


def _write_markdown(
    output_dir: Path,
    stats: dict[str, dict[str, float]],
    paired: dict[str, dict[str, Any]],
    control_summary: dict[str, Any],
) -> None:
    lines = [
        "# Seminar bo_current Friedman-I 結果まとめ",
        "",
        "- 対象問題: Friedman-I symbolic regression",
        "- seed: 0..99",
        "- population size: 24",
        "- total generations: 30",
        "- evaluations/run: 720",
        "- archive key: topology_value",
        "- 提案法: bo_current",
        "",
        "## 最終指標",
        "",
        "| method | final HV mean | final HV std | diversity mean | diversity std | archive size mean |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in METHOD_ORDER:
        row = stats[method]
        lines.append(
            "| {method} | {hv_mean:.6f} | {hv_std:.6f} | {div_mean:.6f} | {div_std:.6f} | {archive:.2f} |".format(
                method=method,
                hv_mean=row["final_archive_hypervolume_mean"],
                hv_std=row["final_archive_hypervolume_std"],
                div_mean=row["final_diversity_mean"],
                div_std=row["final_diversity_std"],
                archive=row["archive_size_mean"],
            )
        )

    lines.extend(
        [
            "",
            "## bo_current と固定率GPの seed 内差分",
            "",
            "| comparison | HV diff mean | HV diff std | win | tie | loss |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for key, label in (
        ("plain_fixed_standard", "bo_current - standard"),
        ("plain_fixed_high_mutation", "bo_current - high mutation"),
        ("plain_fixed_high_crossover", "bo_current - high crossover"),
        ("best_fixed_per_seed", "bo_current - best fixed per seed"),
    ):
        row = paired[key]
        lines.append(
            "| {label} | {mean:.6f} | {std:.6f} | {win} | {tie} | {loss} |".format(
                label=label,
                mean=row["mean"],
                std=row["std"],
                win=row["win_count"],
                tie=row["tie_count"],
                loss=row["loss_count"],
            )
        )

    lines.extend(
        [
            "",
            "## bo_current の制御傾向",
            "",
            f"- k selection counts: {control_summary['k_counts']}",
            f"- mean p_c: {control_summary['p_c_mean']:.4f}",
            f"- mean p_m: {control_summary['p_m_mean']:.4f}",
            f"- mean reward: {control_summary['reward_mean']:.4f}",
            f"- mean control steps: {control_summary['control_steps_mean']:.2f}",
            "",
            "## 図",
            "",
            "- `seminar_final_hv_diversity.png`: final HV と diversity の平均 ± 標準偏差",
            "- `seminar_final_hv_boxplot.png`: seed 100 本での final HV 分布",
            "- `seminar_paired_hv_difference.png`: bo_current と固定率GPの seed 内 HV 差分",
            "- `seminar_k_selection_counts.png`: bo_current が選んだ k の回数",
            "",
            "## 考察メモ",
            "",
            "- bo_current は標準固定率と高交叉固定率より final HV 平均が高い。",
            "- 一方で、高突然変異固定率は final HV 平均が最も高く、bo_current はまだ最良固定率を安定して上回っていない。",
            "- したがって Seminar では「固定率を置き換えれば必ず勝つ」ではなく、「閉ループ制御の枠組みは動作し、標準固定率は上回るが、報酬設計・BO制御器の改善余地が残る」と説明するのが妥当である。",
        ]
    )
    (output_dir / "seminar_bo_current_friedman_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="outputs/seminar_bo_current/sr_alpha_friedman/seminar_bo_current_seed100_20260602",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    rows = _read_csv(output_dir / "summary_by_seed.csv")
    stats = _method_stats(rows)
    paired = _paired_differences(rows, "final_archive_hypervolume")
    control_summary = _control_summary(output_dir, rows)
    summary_payload = {
        "method_stats": stats,
        "paired_hv_differences": paired,
        "control_summary": control_summary,
    }
    _write_json(output_dir / "seminar_analysis_summary.json", summary_payload)
    _write_markdown(output_dir, stats, paired, control_summary)
    _plot_final_metrics(output_dir, stats)
    _plot_hv_boxplot(output_dir, rows)
    _plot_paired_diff(output_dir, paired)
    _plot_k_counts(output_dir, control_summary)
    print(json.dumps({"output_dir": str(output_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
