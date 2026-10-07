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

from bogp.test_v1_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.test_v1_plain_gp_baseline import PlainFixedRateGPRunner, PlainGPBaselineConfig
from bogp.test_v1_structural_problem import StructuralSearchProblem


def _plot_state_history(records, output_path: Path) -> None:
    generations = [record.generation for record in records]
    hv_values = [record.hypervolume for record in records]
    diversity_values = [record.diversity for record in records]

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(generations, hv_values, marker="o", label="HV")
    ax.plot(generations, diversity_values, marker="s", label="Diversity")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Metric value")
    ax.set_title("Plain fixed-rate structural GP: HV and Diversity")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _plot_pareto_archive(archive: list[dict], output_path: Path) -> None:
    values = [item["objective_values"] for item in archive]
    if not values:
        return
    terminal_counts = [row[0] for row in values]
    impulse_integrals = [row[1] for row in values]

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    ax.scatter(terminal_counts, impulse_integrals, s=34, alpha=0.75, edgecolors="none")
    ax.set_xlabel("Objective 1: Terminal elements (minimize)")
    ax.set_ylabel("Objective 2: Impulse integral (minimize)")
    ax.set_title("Pareto archive: plain fixed-rate structural GP")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> int:
    warnings.filterwarnings("ignore")

    output_dir = ROOT / "outputs" / "plain_gp_baseline_structural" / datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    problem = StructuralSearchProblem(max_initial_depth=3, time_steps=401)
    engine = MultiObjectiveGPEngine(
        problem,
        MultiObjectiveGPConfig(
            population_size=8,
            total_generations=10,
            random_seed=7,
            hv_reference_point=(1.0, 1.0),
        ),
    )
    baseline_config = PlainGPBaselineConfig(crossover_rate=0.80, mutation_rate=0.05)
    runner = PlainFixedRateGPRunner(engine=engine, config=baseline_config)
    records = runner.run()

    records_path = output_dir / "generation_records.jsonl"
    with records_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    archive = [
        {
            "objective_values": item.objective_values,
            "rank": item.rank,
            "crowding_distance": item.crowding_distance,
        }
        for item in engine.archive
    ]
    (output_dir / "pareto_archive.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _plot_state_history(records, output_dir / "hv_diversity_history.png")
    _plot_pareto_archive(archive, output_dir / "pareto_front.png")

    final = records[-1]
    summary = {
        "method": "plain_fixed_rate_structural_gp",
        "crossover_rate": baseline_config.crossover_rate,
        "mutation_rate": baseline_config.mutation_rate,
        "records": len(records),
        "final_generation": final.generation,
        "final_hypervolume": final.hypervolume,
        "final_diversity": final.diversity,
        "archive_size": len(engine.archive),
        "output_dir": str(output_dir),
        "hv_diversity_plot": str(output_dir / "hv_diversity_history.png"),
        "pareto_front_plot": str(output_dir / "pareto_front.png"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
