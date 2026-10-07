from __future__ import annotations

import json
import os
import sys
import warnings
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.loop import ClosedLoopRunner
from bogp.objectives import RewardConfig
from bogp.test_v1_plain_gp_baseline import PlainFixedRateGPRunner, PlainGPBaselineConfig
from bogp.test_v1_template_problem import TemplateSymbolicRegressionProblem
from bogp.test_ver2_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from sklearn.exceptions import ConvergenceWarning


def _proposed_record_to_dict(record) -> dict:
    return {
        "step_index": record.step_index,
        "control": {
            "crossover_rate": record.control.crossover_rate,
            "mutation_rate": record.control.mutation_rate,
            "update_period": record.control.update_period,
        },
        "start_generation": record.start_state.generation,
        "end_generation": record.end_state.generation,
        "start_hv": record.start_state.hypervolume,
        "end_hv": record.end_state.hypervolume,
        "diversity": record.end_state.diversity,
        "reward": record.reward.total,
        "reward_terms": {
            "hv_term": record.reward.hv_term,
            "diversity_term": record.reward.diversity_term,
            "control_cost": record.reward.control_cost,
        },
    }


def _state_to_dict(state) -> dict:
    return {
        "generation": state.generation,
        "hypervolume": state.hypervolume,
        "diversity": state.diversity,
        "mean_tree_size": state.mean_tree_size,
        "stagnation_generations": state.stagnation_generations,
    }


def _archive_to_dicts(items) -> list[dict]:
    return [
        {
            "objective_values": item.objective_values,
            "rank": item.rank,
            "crowding_distance": item.crowding_distance,
        }
        for item in items
    ]


def _plot_comparison(proposed_records, baseline_records, output_path: Path) -> None:
    proposed_generations = [0] + [record.end_state.generation for record in proposed_records]
    proposed_hv = [proposed_records[0].start_state.hypervolume] + [
        record.end_state.hypervolume for record in proposed_records
    ]
    proposed_diversity = [proposed_records[0].start_state.diversity] + [
        record.end_state.diversity for record in proposed_records
    ]

    baseline_generations = [record.generation for record in baseline_records]
    baseline_hv = [record.hypervolume for record in baseline_records]
    baseline_diversity = [record.diversity for record in baseline_records]

    fig, axes = plt.subplots(2, 1, figsize=(8.5, 7.2), sharex=True)
    axes[0].plot(
        baseline_generations,
        baseline_hv,
        marker="o",
        markersize=3.5,
        label="Plain GP HV",
    )
    axes[0].plot(
        proposed_generations,
        proposed_hv,
        marker="s",
        linewidth=2.0,
        label="BO-controlled GP HV",
    )
    axes[0].set_ylabel("Hypervolume")
    axes[0].set_title("Template GP comparison: test_ver2 archive")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(
        baseline_generations,
        baseline_diversity,
        marker="o",
        markersize=3.5,
        label="Plain GP Diversity",
    )
    axes[1].plot(
        proposed_generations,
        proposed_diversity,
        marker="s",
        linewidth=2.0,
        label="BO-controlled GP Diversity",
    )
    axes[1].set_xlabel("Generation")
    axes[1].set_ylabel("Diversity")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_per_generation_comparison(
    proposed_history,
    baseline_history,
    output_path: Path,
) -> None:
    proposed_generations = [state.generation for state in proposed_history]
    proposed_hv = [state.hypervolume for state in proposed_history]
    proposed_diversity = [state.diversity for state in proposed_history]

    baseline_generations = [state.generation for state in baseline_history]
    baseline_hv = [state.hypervolume for state in baseline_history]
    baseline_diversity = [state.diversity for state in baseline_history]

    fig, axes = plt.subplots(2, 1, figsize=(8.5, 7.2), sharex=True)
    axes[0].plot(
        baseline_generations,
        baseline_hv,
        marker="o",
        markersize=3.5,
        label="Plain GP HV",
    )
    axes[0].plot(
        proposed_generations,
        proposed_hv,
        marker="s",
        markersize=3.5,
        linewidth=2.0,
        label="BO-controlled GP HV",
    )
    axes[0].set_ylabel("Hypervolume")
    axes[0].set_title("Per-generation HV and Diversity: template GP")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(
        baseline_generations,
        baseline_diversity,
        marker="o",
        markersize=3.5,
        label="Plain GP Diversity",
    )
    axes[1].plot(
        proposed_generations,
        proposed_diversity,
        marker="s",
        markersize=3.5,
        linewidth=2.0,
        label="BO-controlled GP Diversity",
    )
    axes[1].set_xlabel("Generation")
    axes[1].set_ylabel("Diversity")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_control_periods(proposed_records, output_path: Path) -> None:
    if not proposed_records:
        return
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 6.2), sharex=True)
    generations = [record.end_state.generation for record in proposed_records]
    crossover_values = [record.control.crossover_rate for record in proposed_records]
    mutation_values = [record.control.mutation_rate for record in proposed_records]

    axes[0].plot(generations, crossover_values, marker="o", label="p_c")
    axes[0].plot(generations, mutation_values, marker="s", label="p_m")
    axes[0].set_ylabel("Operator rates")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    for index, record in enumerate(proposed_records):
        axes[1].hlines(
            record.control.update_period,
            record.start_state.generation,
            record.end_state.generation,
            linewidth=2.4,
            label="k" if index == 0 else None,
        )
        if index + 1 < len(proposed_records):
            next_k = proposed_records[index + 1].control.update_period
            current_k = record.control.update_period
            if next_k != current_k:
                axes[1].vlines(
                    record.end_state.generation,
                    min(current_k, next_k),
                    max(current_k, next_k),
                    linewidth=1.5,
                )
    axes[1].set_xlabel("Generation")
    axes[1].set_ylabel("Update period k")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_unique_objective_pareto(
    proposed_archive: list[dict],
    baseline_archive: list[dict],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharex=True, sharey=True)
    panels = [
        (axes[0], baseline_archive, "Plain GP", "tab:blue", "o"),
        (axes[1], proposed_archive, "BO-controlled GP", "tab:orange", "s"),
    ]
    all_values = []
    for _, archive, _, _, _ in panels:
        all_values.extend(item["objective_values"] for item in archive)

    for ax, archive, title, color, marker in panels:
        values = [item["objective_values"] for item in archive]
        if values:
            ax.scatter(
                [row[0] for row in values],
                [row[1] for row in values],
                s=42,
                alpha=0.75,
                marker=marker,
                color=color,
                edgecolors="none",
            )
        ax.set_xlabel("MSE (minimize)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Tree size (minimize)")
    if all_values:
        x_values = [row[0] for row in all_values]
        y_values = [row[1] for row in all_values]
        x_margin = max(0.02, 0.08 * (max(x_values) - min(x_values) + 0.001))
        y_margin = max(0.5, 0.08 * (max(y_values) - min(y_values) + 1.0))
        for ax in axes:
            ax.set_xlim(min(x_values) - x_margin, max(x_values) + x_margin)
            ax.set_ylim(min(y_values) - y_margin, max(y_values) + y_margin)

    fig.suptitle("Unique-objective Pareto archive: template GP")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> int:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    output_dir = ROOT / "outputs" / "template_plain_vs_bogp_test_ver2" / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    engine_config = MultiObjectiveGPConfig(
        population_size=24,
        total_generations=30,
        random_seed=7,
    )

    proposed_engine = MultiObjectiveGPEngine(
        TemplateSymbolicRegressionProblem(),
        engine_config,
    )
    proposed_controller = ContextualBayesianRateController(
        BOControllerConfig(
            candidate_k_values=(1, 3, 5),
            warmup_per_k=2,
            min_observations_per_k=2,
            candidate_pool_size_per_k=128,
            random_seed=7,
        )
    )
    proposed_runner = ClosedLoopRunner(
        engine=proposed_engine,
        controller=proposed_controller,
        reward_config=RewardConfig(max_update_period=5),
    )
    proposed_records = proposed_runner.run()

    baseline_engine = MultiObjectiveGPEngine(
        TemplateSymbolicRegressionProblem(),
        engine_config,
    )
    baseline_config = PlainGPBaselineConfig(crossover_rate=0.80, mutation_rate=0.05)
    baseline_runner = PlainFixedRateGPRunner(
        engine=baseline_engine,
        config=baseline_config,
    )
    baseline_records = baseline_runner.run()

    with (output_dir / "bogp_control_records.jsonl").open("w", encoding="utf-8") as handle:
        for record in proposed_records:
            handle.write(json.dumps(_proposed_record_to_dict(record), ensure_ascii=False) + "\n")

    with (output_dir / "plain_gp_generation_records.jsonl").open("w", encoding="utf-8") as handle:
        for record in baseline_records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    proposed_history = proposed_engine.state_history
    baseline_history = baseline_engine.state_history
    with (output_dir / "bogp_per_generation_records.jsonl").open("w", encoding="utf-8") as handle:
        for state in proposed_history:
            handle.write(json.dumps(_state_to_dict(state), ensure_ascii=False) + "\n")
    with (output_dir / "plain_gp_per_generation_records.jsonl").open("w", encoding="utf-8") as handle:
        for state in baseline_history:
            handle.write(json.dumps(_state_to_dict(state), ensure_ascii=False) + "\n")

    proposed_archive = _archive_to_dicts(proposed_engine.archive)
    baseline_archive = _archive_to_dicts(baseline_engine.archive)
    proposed_unique_archive = _archive_to_dicts(proposed_engine.unique_objective_archive)
    baseline_unique_archive = _archive_to_dicts(baseline_engine.unique_objective_archive)
    (output_dir / "bogp_pareto_archive_objective_structure_pairs.json").write_text(
        json.dumps(proposed_archive, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "plain_gp_pareto_archive_objective_structure_pairs.json").write_text(
        json.dumps(baseline_archive, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "bogp_pareto_archive_unique_objectives.json").write_text(
        json.dumps(proposed_unique_archive, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "plain_gp_pareto_archive_unique_objectives.json").write_text(
        json.dumps(baseline_unique_archive, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _plot_comparison(proposed_records, baseline_records, output_dir / "hv_diversity_comparison.png")
    _plot_per_generation_comparison(
        proposed_history,
        baseline_history,
        output_dir / "per_generation_hv_diversity_comparison.png",
    )
    _plot_control_periods(proposed_records, output_dir / "bogp_control_periods.png")
    _plot_unique_objective_pareto(
        proposed_unique_archive,
        baseline_unique_archive,
        output_dir / "pareto_front_unique_objectives.png",
    )

    proposed_final = proposed_records[-1].end_state
    baseline_final = baseline_records[-1]
    summary = {
        "problem": "template_symbolic_regression",
        "archive_policy": "test_ver2_objective_structure_pair_dedup",
        "proposed": {
            "final_generation": proposed_final.generation,
            "final_hypervolume": proposed_final.hypervolume,
            "final_diversity": proposed_final.diversity,
            "control_steps": len(proposed_records),
            **proposed_engine.archive_statistics(),
        },
        "plain_gp": {
            "crossover_rate": baseline_config.crossover_rate,
            "mutation_rate": baseline_config.mutation_rate,
            "final_generation": baseline_final.generation,
            "final_hypervolume": baseline_final.hypervolume,
            "final_diversity": baseline_final.diversity,
            "records": len(baseline_records),
            **baseline_engine.archive_statistics(),
        },
        "output_dir": str(output_dir),
        "comparison_plot": str(output_dir / "hv_diversity_comparison.png"),
        "per_generation_comparison_plot": str(
            output_dir / "per_generation_hv_diversity_comparison.png"
        ),
        "bogp_control_plot": str(output_dir / "bogp_control_periods.png"),
        "pareto_front_unique_objectives_plot": str(output_dir / "pareto_front_unique_objectives.png"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
