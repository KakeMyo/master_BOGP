from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.setrecursionlimit(10000)

from bogp.formal_experiment import FormalExperimentConfig, ProblemSpec, run_problem_experiment
from bogp.symbolic_regression_benchmarks import (
    BenchmarkRecordingEngine, BenchmarkRegressionProblem, dataset_manifest,
    load_official_data, make_uball_dataset, write_regression_artifacts,
)
from run_main_bo_current_friedman_experiment import FIXED_BASELINES
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)


def main() -> int:
    parser = argparse.ArgumentParser(description="Three-seed pilots with FINAL seminar GP/BO settings.")
    parser.add_argument("--problem", choices=["all", "uball5d", "airfoil", "concrete"], default="all")
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / "thesis_three_problem_pilot")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "problem_settings" / "raw")
    args = parser.parse_args()
    if args.seed_count <= 0 or args.seed_start < 0:
        raise ValueError("Invalid algorithm seeds.")
    run_id = args.run_id or datetime.now().strftime("seminar_conditions_seed3_%Y%m%d_%H%M%S")
    problems = ["uball5d", "airfoil", "concrete"] if args.problem == "all" else [args.problem]
    for name in problems:
        output_dir = args.output_root / run_id / name / "seminar_78_generations"
        if (output_dir / "config.json").exists():
            raise FileExistsError(f"Existing experiment will not be overwritten: {output_dir}")
        dataset = make_uball_dataset() if name == "uball5d" else load_official_data(name, args.raw_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        problem = BenchmarkRegressionProblem(dataset)
        protocol = {
            "seminar_source": "notes/paper_8page_2col_draft_expanded.tex, experimental settings",
            "seminar_runner": "scripts/run_main_bo_current_friedman_experiment.py",
            "population_size": 24, "warmup_generations": 18, "evaluation_generations": 60,
            "total_generations": 78, "offspring_fitness_evaluations": 1872,
            "initial_population_fitness_evaluations": 24, "total_training_fitness_calls": 1896,
            "seeds": list(range(args.seed_start, args.seed_start + args.seed_count)),
            "primitive_set": ["add", "sub", "mul", "div", "sin", "cos"],
            "protected_division": "abs(denominator)<=1e-6 returns numerator",
            "constant_range": list(problem.constant_range),
            "max_initial_depth": problem.max_initial_depth,
            "max_mutation_depth": problem.max_mutation_depth,
            "error_objective": "train RMSE / train target std, clipped to [0,5]",
            "tree_size_normalization": [1, 100], "hard_tree_size_limit": None,
            "prediction_clip": problem.prediction_clip, "hv_reference_point": [1, 1],
            "archive_size": 200, "tournament_size": 3,
            "archive_structure_key_mode": "topology_value",
            "fixed_baselines": [asdict(method) for method in FIXED_BASELINES],
            "bo_controller_overrides": {}, "reward_overrides": {},
            "heldout_evaluation": "after all 78 generations; trees chosen by training objective only",
            "departures_from_problem_shortlist": [
                "population=24 and total=78 per user, not proposed long-horizon screening budgets",
                "seminar primitives including sin/cos; no sqrt/log/AQ or coefficient optimisation",
                "train-only z-score for real data; no fitted linear scaling of GP outputs",
                "duplicates share a partition; 60/15/25 fractions apply to unique-input groups",
            ],
        }
        (output_dir / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
        (output_dir / "dataset_manifest.json").write_text(
            json.dumps(dataset_manifest(dataset), ensure_ascii=False, indent=2), encoding="utf-8")
        config = FormalExperimentConfig(
            problem_name=name, seeds=tuple(protocol["seeds"]), population_size=24,
            total_generations=78, archive_size=200, archive_structure_key_mode="topology_value",
            fixed_rate_methods=FIXED_BASELINES, include_bogp_current=True,
            output_root=str(args.output_root / run_id), run_id="seminar_78_generations",
        )
        spec = ProblemSpec(
            name=name, factory=lambda: BenchmarkRegressionProblem(dataset),
            engine_factory=BenchmarkRecordingEngine, run_artifact_writer=write_regression_artifacts,
        )
        print(f"Starting {name}: sizes={dataset_manifest(dataset)['partition_sizes']}; seeds={protocol['seeds']}", flush=True)
        result = run_problem_experiment(spec, config)
        print(json.dumps({"problem": name, "output_dir": str(result.output_dir),
                          "run_count": len(result.run_summaries)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
