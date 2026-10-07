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
from bogp.test_v1_structural_problem import StructuralSearchProblem
from bogp.test_ver2_b_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine


MODES = (
    ("test_ver2_b1", "topology"),
    ("test_ver2_b2", "topology_value"),
)


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
        "start_archive_hv": record.start_state.hypervolume,
        "end_archive_hv": record.end_state.hypervolume,
        "diversity": record.end_state.diversity,
        "reward": record.reward.total,
        "reward_terms": {
            "hv_term": record.reward.hv_term,
            "diversity_term": record.reward.diversity_term,
            "control_cost": record.reward.control_cost,
        },
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


def _write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _plot_archive_population_diversity(
    proposed_metrics,
    baseline_metrics,
    output_path: Path,
    title_suffix: str,
) -> None:
    proposed_generations = [item.generation for item in proposed_metrics]
    baseline_generations = [item.generation for item in baseline_metrics]

    fig, axes = plt.subplots(3, 1, figsize=(8.8, 9.0), sharex=True)
    axes[0].plot(
        baseline_generations,
        [item.archive_hypervolume for item in baseline_metrics],
        marker="o",
        markersize=3.5,
        label="Plain structural GP archive HV",
    )
    axes[0].plot(
        proposed_generations,
        [item.archive_hypervolume for item in proposed_metrics],
        marker="s",
        markersize=3.5,
        linewidth=2.0,
        label="BO-controlled structural GP archive HV",
    )
    axes[0].set_ylabel("Archive HV")
    axes[0].set_title(f"Structural GP archive/population metrics: {title_suffix}")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].plot(
        baseline_generations,
        [item.population_hypervolume for item in baseline_metrics],
        marker="o",
        markersize=3.5,
        label="Plain structural GP population HV",
    )
    axes[1].plot(
        proposed_generations,
        [item.population_hypervolume for item in proposed_metrics],
        marker="s",
        markersize=3.5,
        linewidth=2.0,
        label="BO-controlled structural GP population HV",
    )
    axes[1].set_ylabel("Population HV")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(
        baseline_generations,
        [item.population_diversity for item in baseline_metrics],
        marker="o",
        markersize=3.5,
        label="Plain structural GP diversity",
    )
    axes[2].plot(
        proposed_generations,
        [item.population_diversity for item in proposed_metrics],
        marker="s",
        markersize=3.5,
        linewidth=2.0,
        label="BO-controlled structural GP diversity",
    )
    axes[2].set_xlabel("Generation")
    axes[2].set_ylabel("Population diversity")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_control_periods(proposed_records, output_path: Path) -> None:
    if not proposed_records:
        return
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 6.2), sharex=True)
    generations = [record.end_state.generation for record in proposed_records]
    axes[0].plot(
        generations,
        [record.control.crossover_rate for record in proposed_records],
        marker="o",
        label="p_c",
    )
    axes[0].plot(
        generations,
        [record.control.mutation_rate for record in proposed_records],
        marker="s",
        label="p_m",
    )
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
        (axes[0], baseline_archive, "Plain structural GP", "tab:blue", "o"),
        (axes[1], proposed_archive, "BO-controlled structural GP", "tab:orange", "s"),
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
                s=38,
                alpha=0.75,
                marker=marker,
                color=color,
                edgecolors="none",
            )
        ax.set_xlabel("Terminal elements (minimize)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Impulse integral (minimize)")
    if all_values:
        x_values = [row[0] for row in all_values]
        y_values = [row[1] for row in all_values]
        x_margin = max(0.5, 0.06 * (max(x_values) - min(x_values) + 1.0))
        y_margin = max(0.005, 0.08 * (max(y_values) - min(y_values) + 0.001))
        for ax in axes:
            ax.set_xlim(min(x_values) - x_margin, max(x_values) + x_margin)
            ax.set_ylim(min(y_values) - y_margin, max(y_values) + y_margin)

    fig.suptitle("Unique-objective Pareto archive: structural GP")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _run_one_mode(version_label: str, structure_mode: str) -> dict:
    output_dir = ROOT / "outputs" / f"structural_plain_vs_bogp_{version_label}" / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    engine_config = MultiObjectiveGPConfig(
        population_size=8,
        total_generations=10,
        random_seed=7,
        hv_reference_point=(1.0, 1.0),
        archive_structure_key_mode=structure_mode,
    )

    proposed_engine = MultiObjectiveGPEngine(
        StructuralSearchProblem(max_initial_depth=3, time_steps=401),
        engine_config,
    )
    proposed_controller = ContextualBayesianRateController(
        BOControllerConfig(
            candidate_k_values=(1, 3),
            warmup_per_k=1,
            min_observations_per_k=1,
            candidate_pool_size_per_k=64,
            random_seed=7,
        )
    )
    proposed_runner = ClosedLoopRunner(
        engine=proposed_engine,
        controller=proposed_controller,
        reward_config=RewardConfig(max_update_period=3),
    )
    proposed_records = proposed_runner.run()

    baseline_engine = MultiObjectiveGPEngine(
        StructuralSearchProblem(max_initial_depth=3, time_steps=401),
        engine_config,
    )
    baseline_config = PlainGPBaselineConfig(crossover_rate=0.80, mutation_rate=0.05)
    baseline_runner = PlainFixedRateGPRunner(
        engine=baseline_engine,
        config=baseline_config,
    )
    baseline_records = baseline_runner.run()

    _write_jsonl(
        output_dir / "bogp_control_records.jsonl",
        [_proposed_record_to_dict(record) for record in proposed_records],
    )
    _write_jsonl(
        output_dir / "plain_gp_generation_records.jsonl",
        [asdict(record) for record in baseline_records],
    )
    _write_jsonl(
        output_dir / "bogp_generation_metrics.jsonl",
        [asdict(item) for item in proposed_engine.generation_metrics_history],
    )
    _write_jsonl(
        output_dir / "plain_gp_generation_metrics.jsonl",
        [asdict(item) for item in baseline_engine.generation_metrics_history],
    )

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

    _plot_archive_population_diversity(
        proposed_engine.generation_metrics_history,
        baseline_engine.generation_metrics_history,
        output_dir / "archive_population_hv_diversity_comparison.png",
        version_label,
    )
    _plot_control_periods(proposed_records, output_dir / "bogp_control_periods.png")
    _plot_unique_objective_pareto(
        proposed_unique_archive,
        baseline_unique_archive,
        output_dir / "pareto_front_unique_objectives.png",
    )

    proposed_final_state = proposed_records[-1].end_state
    proposed_final_metrics = proposed_engine.generation_metrics_history[-1]
    baseline_final_record = baseline_records[-1]
    baseline_final_metrics = baseline_engine.generation_metrics_history[-1]
    summary = {
        "problem": "structural_search",
        "version_label": version_label,
        "archive_policy": "test_ver2_b_archive_population_split",
        "archive_structure_key_mode": structure_mode,
        "proposed": {
            "final_generation": proposed_final_state.generation,
            "final_archive_hypervolume": proposed_final_metrics.archive_hypervolume,
            "final_population_hypervolume": proposed_final_metrics.population_hypervolume,
            "final_diversity": proposed_final_state.diversity,
            "control_steps": len(proposed_records),
            **proposed_engine.archive_statistics(),
        },
        "plain_gp": {
            "crossover_rate": baseline_config.crossover_rate,
            "mutation_rate": baseline_config.mutation_rate,
            "final_generation": baseline_final_record.generation,
            "final_archive_hypervolume": baseline_final_metrics.archive_hypervolume,
            "final_population_hypervolume": baseline_final_metrics.population_hypervolume,
            "final_diversity": baseline_final_record.diversity,
            "records": len(baseline_records),
            **baseline_engine.archive_statistics(),
        },
        "output_dir": str(output_dir),
        "archive_population_plot": str(
            output_dir / "archive_population_hv_diversity_comparison.png"
        ),
        "bogp_control_plot": str(output_dir / "bogp_control_periods.png"),
        "pareto_front_unique_objectives_plot": str(
            output_dir / "pareto_front_unique_objectives.png"
        ),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    warnings.filterwarnings("ignore")
    summaries = [_run_one_mode(version_label, mode) for version_label, mode in MODES]
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
