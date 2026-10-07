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
from bogp.test_v1_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.objectives import RewardConfig
from bogp.test_v1_plain_gp_baseline import PlainFixedRateGPRunner, PlainGPBaselineConfig
from bogp.test_v1_template_problem import TemplateSymbolicRegressionProblem
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
    axes[0].set_title("Template GP comparison")
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


def main() -> int:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    output_dir = ROOT / "outputs" / "template_plain_vs_bogp" / datetime.now().strftime(
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

    _plot_comparison(proposed_records, baseline_records, output_dir / "hv_diversity_comparison.png")
    _plot_control_periods(proposed_records, output_dir / "bogp_control_periods.png")

    proposed_final = proposed_records[-1].end_state
    baseline_final = baseline_records[-1]
    summary = {
        "problem": "template_symbolic_regression",
        "proposed": {
            "final_generation": proposed_final.generation,
            "final_hypervolume": proposed_final.hypervolume,
            "final_diversity": proposed_final.diversity,
            "control_steps": len(proposed_records),
        },
        "plain_gp": {
            "crossover_rate": baseline_config.crossover_rate,
            "mutation_rate": baseline_config.mutation_rate,
            "final_generation": baseline_final.generation,
            "final_hypervolume": baseline_final.hypervolume,
            "final_diversity": baseline_final.diversity,
            "records": len(baseline_records),
        },
        "output_dir": str(output_dir),
        "comparison_plot": str(output_dir / "hv_diversity_comparison.png"),
        "bogp_control_plot": str(output_dir / "bogp_control_periods.png"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
