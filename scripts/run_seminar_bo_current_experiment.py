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


PROBLEMS = ("sr_alpha_friedman", "sr_alpha_poly10")

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
        description="Run Seminar formal experiments with bo_current as the main proposed method."
    )
    parser.add_argument("--seed-count", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--population-size", type=int, default=24)
    parser.add_argument("--total-generations", type=int, default=30)
    parser.add_argument("--archive-size", type=int, default=200)
    parser.add_argument(
        "--problem",
        action="append",
        choices=PROBLEMS,
        help="Problem to run. Can be repeated. Defaults to both Seminar problems.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional shared run id. Defaults to seminar_bo_current_<timestamp>.",
    )
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "outputs" / "seminar_bo_current"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.seed_count <= 0:
        raise ValueError("--seed-count must be positive.")

    run_id = args.run_id or "seminar_bo_current_" + datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    problems = tuple(args.problem or PROBLEMS)

    summaries = []
    for problem_name in problems:
        config = FormalExperimentConfig(
            problem_name=problem_name,
            seeds=seeds,
            population_size=args.population_size,
            total_generations=args.total_generations,
            archive_size=args.archive_size,
            archive_structure_key_mode="topology_value",
            fixed_rate_methods=FIXED_BASELINES,
            include_bogp_current=True,
            output_root=args.output_root,
            run_id=run_id,
        )
        result = run_registered_experiment(config)
        summaries.append(
            {
                "problem_name": problem_name,
                "output_dir": str(result.output_dir),
                "summary_by_seed_path": str(result.summary_by_seed_path),
                "aggregate_summary_path": str(result.aggregate_summary_path),
                "run_count": len(result.run_summaries),
            }
        )

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
