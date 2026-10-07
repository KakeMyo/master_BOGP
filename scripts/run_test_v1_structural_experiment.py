from __future__ import annotations

import json
import os
import sys
import warnings
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
from bogp.test_v1_structural_problem import StructuralSearchProblem
from sklearn.exceptions import ConvergenceWarning


def _plot_pareto_archive(archive: list[dict], output_path: Path) -> None:
    objective_values = [item["objective_values"] for item in archive]
    if not objective_values:
        return
    terminal_counts = [values[0] for values in objective_values]
    impulse_integrals = [values[1] for values in objective_values]

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.scatter(terminal_counts, impulse_integrals, s=36, alpha=0.75, edgecolors="none")
    ax.set_xlabel("Objective 1: Terminal elements (minimize)")
    ax.set_ylabel("Objective 2: Impulse integral (minimize)")
    ax.set_title("Pareto archive: structural GP")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_control_history(records: list, output_path: Path) -> None:
    if not records:
        return
    generations = [record.end_state.generation for record in records]
    hv_values = [record.end_state.hypervolume for record in records]
    diversity_values = [record.end_state.diversity for record in records]
    crossover_values = [record.control.crossover_rate for record in records]
    mutation_values = [record.control.mutation_rate for record in records]

    fig, axes = plt.subplots(3, 1, figsize=(8.0, 8.0), sharex=True)
    axes[0].plot(generations, hv_values, marker="o", label="HV")
    axes[0].plot(generations, diversity_values, marker="s", label="Diversity")
    axes[0].set_ylabel("State metrics")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(generations, crossover_values, marker="o", label="p_c")
    axes[1].plot(generations, mutation_values, marker="s", label="p_m")
    axes[1].set_ylabel("Operator rates")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Draw k on the exact generation interval where the control is held.
    for index, record in enumerate(records):
        start_generation = record.start_state.generation
        end_generation = record.end_state.generation
        k_value = record.control.update_period
        axes[2].hlines(
            k_value,
            start_generation,
            end_generation,
            linewidth=2.4,
            label="k" if index == 0 else None,
        )
        if index + 1 < len(records):
            next_k = records[index + 1].control.update_period
            if next_k != k_value:
                axes[2].vlines(
                    end_generation,
                    min(k_value, next_k),
                    max(k_value, next_k),
                    linewidth=1.5,
                )
    axes[2].set_xlabel("Generation")
    axes[2].set_ylabel("Update period")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    fig.suptitle("Closed-loop control history: structural GP")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> int:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)

    output_dir = ROOT / "outputs" / "structural_gp" / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    problem = StructuralSearchProblem(max_initial_depth=3, time_steps=401)
    engine = MultiObjectiveGPEngine(
        problem,
        MultiObjectiveGPConfig(
            population_size=8,
            total_generations=5,
            random_seed=7,
            hv_reference_point=(1.0, 1.0),
        ),
    )
    controller = ContextualBayesianRateController(
        BOControllerConfig(
            candidate_k_values=(1, 3),
            warmup_per_k=1,
            min_observations_per_k=1,
            candidate_pool_size_per_k=64,
            random_seed=7,
        )
    )
    runner = ClosedLoopRunner(
        engine=engine,
        controller=controller,
        reward_config=RewardConfig(max_update_period=3),
    )
    records = runner.run()

    records_path = output_dir / "control_records.jsonl"
    with records_path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = {
                "step_index": record.step_index,
                "control": record.control.as_tuple(),
                "start_generation": record.start_state.generation,
                "end_generation": record.end_state.generation,
                "start_hv": record.start_state.hypervolume,
                "end_hv": record.end_state.hypervolume,
                "reward": record.reward.total,
                "diversity": record.end_state.diversity,
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    archive = [
        {"objective_values": item.objective_values}
        for item in engine.archive
    ]
    (output_dir / "pareto_archive.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _plot_pareto_archive(archive, output_dir / "pareto_front.png")
    _plot_control_history(records, output_dir / "control_history.png")

    final = records[-1].end_state if records else engine.snapshot()
    summary = {
        "records": len(records),
        "final_generation": final.generation,
        "final_hypervolume": final.hypervolume,
        "final_diversity": final.diversity,
        "archive_size": len(engine.archive),
        "output_dir": str(output_dir),
        "pareto_front_plot": str(output_dir / "pareto_front.png"),
        "control_history_plot": str(output_dir / "control_history.png"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
