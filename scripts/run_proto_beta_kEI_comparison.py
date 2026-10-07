from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))

from sklearn.exceptions import ConvergenceWarning  # noqa: E402

from bogp.controller import BOControllerConfig, ContextualBayesianRateController  # noqa: E402
from bogp.formal_experiment import (  # noqa: E402
    _RunArtifact,
    _archive_to_dicts,
    _bogp_control_records,
    _engine_config,
    _generation_metrics_rows,
    _plot_bogp_control_history,
    _plot_common_histories,
    _plot_pareto_fronts,
    _write_aggregate_summary,
    _write_json,
    _write_jsonl,
    _write_summary_by_seed,
    FormalExperimentConfig,
    ProblemSpec,
    registered_problem_specs,
)
from bogp.loop import ClosedLoopRunner  # noqa: E402
from bogp.objectives import RewardConfig  # noqa: E402
from bogp.test_ver2_b_mo_engine import MultiObjectiveGPEngine  # noqa: E402


METHODS = (
    {
        "name": "bo_current",
        "description": "sequential warm-up + per-k EI best",
        "controller_overrides": {
            "warmup_strategy": "sequential",
            "ei_best_scope": "per_k",
        },
    },
    {
        "name": "ver_beta_k",
        "description": "interleaved warm-up + per-k EI best",
        "controller_overrides": {
            "warmup_strategy": "interleaved",
            "ei_best_scope": "per_k",
        },
    },
    {
        "name": "ver_beta_EI",
        "description": "sequential warm-up + global-best EI",
        "controller_overrides": {
            "warmup_strategy": "sequential",
            "ei_best_scope": "global",
        },
    },
    {
        "name": "ver_beta_kEI",
        "description": "interleaved warm-up + global-best EI",
        "controller_overrides": {
            "warmup_strategy": "interleaved",
            "ei_best_scope": "global",
        },
    },
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run BO controller ablation comparison for proto-alpha problems.",
    )
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--run-label", default="ver_beta_kEI")
    parser.add_argument("--skip-plots", action="store_true")
    parser.add_argument(
        "--problem",
        action="append",
        choices=("sr_alpha_friedman", "sr_alpha_poly10"),
        help="Problem to run. Defaults to both proto-alpha problems.",
    )
    args = parser.parse_args()

    warnings.filterwarnings("ignore", category=ConvergenceWarning)

    seed_count = max(1, int(args.seed_count))
    seeds = tuple(range(int(args.seed_start), int(args.seed_start) + seed_count))
    run_id = f"{args.run_label}_seed{seed_count}_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    problem_names = tuple(args.problem) if args.problem else ("sr_alpha_friedman", "sr_alpha_poly10")
    summaries: list[dict[str, Any]] = []
    registry = registered_problem_specs()

    for problem_name in problem_names:
        config = FormalExperimentConfig(
            problem_name=problem_name,
            seeds=seeds,
            population_size=24,
            total_generations=30,
            archive_size=200,
            archive_structure_key_mode="topology_value",
            fixed_rate_methods=(),
            include_bogp_current=False,
            output_root=str(ROOT / "outputs" / "symbolic_regression_alpha_bo_compare"),
            run_id=run_id,
        )
        problem_spec = registry[problem_name]
        output_dir = Path(config.output_root) / problem_spec.name / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            output_dir / "config.json",
            {
                "problem_name": problem_name,
                "run_id": run_id,
                "comparison": "bo_current_vs_ver_beta_k_vs_ver_beta_EI_vs_ver_beta_kEI",
                "methods": METHODS,
                "config": config,
            },
        )

        artifacts: list[_RunArtifact] = []
        for seed in config.seeds:
            for method in METHODS:
                print(
                    json.dumps(
                        {
                            "event": "run_start",
                            "problem_name": problem_name,
                            "method_name": method["name"],
                            "seed": int(seed),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                artifacts.append(
                    _run_bogp_variant(
                        problem_spec=problem_spec,
                        config=config,
                        method_name=str(method["name"]),
                        method_description=str(method["description"]),
                        controller_overrides=dict(method["controller_overrides"]),
                        seed=int(seed),
                        output_dir=output_dir,
                    )
                )

        summary_rows = [artifact.summary for artifact in artifacts]
        summary_by_seed_path = output_dir / "summary_by_seed.csv"
        aggregate_summary_path = output_dir / "aggregate_summary.csv"
        _write_summary_by_seed(summary_by_seed_path, summary_rows)
        _write_aggregate_summary(aggregate_summary_path, summary_rows)
        _write_json(output_dir / "run_summaries.json", summary_rows)
        if not args.skip_plots:
            _plot_common_histories(output_dir, artifacts)
            _plot_pareto_fronts(output_dir, artifacts)
        summaries.append(
            {
                "problem_name": problem_name,
                "output_dir": str(output_dir),
                "summary_by_seed_path": str(summary_by_seed_path),
                "aggregate_summary_path": str(aggregate_summary_path),
                "run_count": len(summary_rows),
            }
        )

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


def _run_bogp_variant(
    problem_spec: ProblemSpec,
    config: FormalExperimentConfig,
    method_name: str,
    method_description: str,
    controller_overrides: Mapping[str, Any],
    seed: int,
    output_dir: Path,
) -> _RunArtifact:
    run_dir = output_dir / "runs" / method_name / f"seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    problem = problem_spec.factory()
    objective_names = tuple(objective.name for objective in problem.objectives)
    objective_count = len(objective_names)
    engine = MultiObjectiveGPEngine(problem, _engine_config(config, seed))

    controller_kwargs = dict(controller_overrides)
    controller_kwargs.setdefault("random_seed", seed)
    controller = ContextualBayesianRateController(BOControllerConfig(**controller_kwargs))
    reward_config = RewardConfig(**dict(config.reward_overrides))
    runner = ClosedLoopRunner(engine=engine, controller=controller, reward_config=reward_config)

    started = time.perf_counter()
    records = runner.run()
    wall_time = time.perf_counter() - started
    evaluations = sum(record.evaluations for record in records)

    generation_metrics = _generation_metrics_rows(
        engine.generation_metrics_history,
        objective_count,
    )
    archive = _archive_to_dicts(engine.archive)
    unique_archive = _archive_to_dicts(engine.unique_objective_archive)
    control_records = _bogp_control_records(records, objective_count)

    _write_jsonl(run_dir / "generation_metrics.jsonl", generation_metrics)
    _write_jsonl(run_dir / "control_records.jsonl", control_records)
    _write_json(run_dir / "pareto_archive.json", archive)
    _write_json(run_dir / "unique_objective_archive.json", unique_archive)
    _plot_bogp_control_history(run_dir / "control_history.png", control_records)

    final_metrics = generation_metrics[-1]
    summary = {
        "problem_name": problem_spec.name,
        "method_name": method_name,
        "method_kind": "bogp_variant",
        "method_description": method_description,
        "seed": seed,
        "objective_count": objective_count,
        "objective_names": objective_names,
        "archive_structure_key_mode": config.archive_structure_key_mode,
        "final_generation": engine.snapshot().generation,
        "final_archive_hypervolume": final_metrics["archive_hypervolume"],
        "final_population_hypervolume": final_metrics["population_hypervolume"],
        "final_diversity": final_metrics["population_diversity"],
        "control_steps": len(records),
        "evaluations": evaluations,
        "wall_time_seconds": wall_time,
        "output_dir": str(run_dir),
        **engine.archive_statistics(),
        "bo_controller": asdict(BOControllerConfig(**controller_kwargs)),
        "reward_config": asdict(reward_config),
    }
    _write_json(run_dir / "summary.json", summary)
    return _RunArtifact(
        summary=summary,
        generation_metrics=generation_metrics,
        unique_objective_archive=unique_archive,
        control_records=control_records,
        output_dir=run_dir,
        objective_count=objective_count,
        objective_names=objective_names,
    )


if __name__ == "__main__":
    raise SystemExit(main())
