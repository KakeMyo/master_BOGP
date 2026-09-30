from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
sys.setrecursionlimit(10000)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.formal_experiment import (  # noqa: E402
    FixedRateMethodConfig,
    FormalExperimentConfig,
    run_registered_experiment,
)
from sklearn.exceptions import ConvergenceWarning  # noqa: E402

warnings.filterwarnings("ignore", category=ConvergenceWarning)


FIXED_BASELINES = (
    FixedRateMethodConfig(
        name="plain_fixed_standard",
        crossover_rate=0.80,
        mutation_rate=0.05,
    ),
    FixedRateMethodConfig(
        name="plain_fixed_high_mutation",
        crossover_rate=0.70,
        mutation_rate=0.20,
    ),
    FixedRateMethodConfig(
        name="plain_fixed_high_crossover",
        crossover_rate=0.90,
        mutation_rate=0.05,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the main Friedman-I experiment for bo_current. "
            "The reported generation count excludes BO warm-up."
        )
    )
    parser.add_argument("--seed-count", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--population-size", type=int, default=24)
    parser.add_argument(
        "--warmup-generations",
        type=int,
        default=18,
        help="BO warm-up generations excluded from the reported evaluation generations.",
    )
    parser.add_argument(
        "--evaluation-generations",
        type=int,
        default=60,
        help="Main evaluation generations after warm-up.",
    )
    parser.add_argument("--archive-size", type=int, default=200)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id. Defaults to main_bo_current_friedman_seed<N>_eval<G>_<timestamp>.",
    )
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "outputs" / "main_bo_current_friedman"),
    )
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    if args.seed_count <= 0:
        raise ValueError("--seed-count must be positive.")
    if args.warmup_generations < 0:
        raise ValueError("--warmup-generations must be non-negative.")
    if args.evaluation_generations <= 0:
        raise ValueError("--evaluation-generations must be positive.")

    total_generations = args.warmup_generations + args.evaluation_generations
    run_id = args.run_id or "main_bo_current_friedman_seed{seed}_eval{eval}_{time}".format(
        seed=args.seed_count,
        eval=args.evaluation_generations,
        time=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))

    config = FormalExperimentConfig(
        problem_name="sr_alpha_friedman",
        seeds=seeds,
        population_size=args.population_size,
        total_generations=total_generations,
        archive_size=args.archive_size,
        archive_structure_key_mode="topology_value",
        fixed_rate_methods=FIXED_BASELINES,
        include_bogp_current=True,
        output_root=args.output_root,
        run_id=run_id,
    )
    result = run_registered_experiment(config)

    metadata = {
        "experiment_name": "main_bo_current_friedman",
        "problem_name": "sr_alpha_friedman",
        "reported_generation_definition": (
            "evaluation_generations excludes BO warm-up. "
            "total_generations = warmup_generations + evaluation_generations."
        ),
        "warmup_generations": args.warmup_generations,
        "evaluation_generations": args.evaluation_generations,
        "total_generations": total_generations,
        "seed_start": args.seed_start,
        "seed_count": args.seed_count,
        "seeds": list(seeds),
        "population_size": args.population_size,
        "evaluations_per_run": args.population_size * total_generations,
        "fixed_baselines": [
            {
                "name": baseline.name,
                "crossover_rate": baseline.crossover_rate,
                "mutation_rate": baseline.mutation_rate,
            }
            for baseline in FIXED_BASELINES
        ],
        "bo_current": {
            "candidate_k_values": [1, 3, 5],
            "warmup_strategy": "sequential",
            "ei_best_scope": "per_k",
            "warmup_per_k": 2,
            "warmup_generation_count_reason": "1+1+3+3+5+5 = 18 generations",
        },
        "literature_basis": [
            {
                "source": "McDermott et al. (2012), Genetic Programming Needs Better Benchmarks",
                "used_for": "Avoiding an overly simple toy problem and choosing a reproducible benchmark.",
            },
            {
                "source": "White et al. (2013), Better GP Benchmarks",
                "used_for": "Using multiple seeds and standardized benchmark/reporting settings.",
            },
            {
                "source": "La Cava et al. (2021), SRBench",
                "used_for": "Treating symbolic regression as an accuracy-complexity benchmark with train/test data.",
            },
            {
                "source": "Liu et al. (2022), Evolvability Degeneration in MOGP for SR",
                "used_for": "Using accuracy-complexity MOGP and discussing low-complexity takeover/diversity issues.",
            },
        ],
    }
    _write_json(result.output_dir / "main_experiment_metadata.json", metadata)

    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "summary_by_seed_path": str(result.summary_by_seed_path),
                "aggregate_summary_path": str(result.aggregate_summary_path),
                "run_count": len(result.run_summaries),
                "metadata_path": str(result.output_dir / "main_experiment_metadata.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
