from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.formal_experiment import (  # noqa: E402
    FixedRateMethodConfig,
    FormalExperimentConfig,
    registered_problem_specs,
    run_registered_experiment,
)


def _parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("seeds must contain at least one integer.")
    return seeds


def _parse_fixed_rate(value: str) -> FixedRateMethodConfig:
    parts = [item.strip() for item in value.split(":")]
    if len(parts) == 2:
        name = "plain_fixed"
        crossover, mutation = parts
    elif len(parts) == 3:
        name, crossover, mutation = parts
    else:
        raise argparse.ArgumentTypeError(
            "fixed rate must be 'p_c:p_m' or 'name:p_c:p_m'."
        )
    return FixedRateMethodConfig(
        name=name,
        crossover_rate=float(crossover),
        mutation_rate=float(mutation),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run problem-independent formal GP/BOGP experiments."
    )
    parser.add_argument(
        "--problem",
        default="template",
        choices=sorted(registered_problem_specs()),
        help="Registered problem name.",
    )
    parser.add_argument(
        "--seeds",
        type=_parse_seeds,
        default=(0,),
        help="Comma-separated random seeds, e.g. '0,1,2'.",
    )
    parser.add_argument("--population-size", type=int, default=24)
    parser.add_argument("--total-generations", type=int, default=30)
    parser.add_argument("--archive-size", type=int, default=200)
    parser.add_argument(
        "--archive-structure-key-mode",
        choices=("topology", "topology_value"),
        default="topology_value",
    )
    parser.add_argument(
        "--fixed-rate",
        action="append",
        type=_parse_fixed_rate,
        help="Fixed-rate method. Use 'p_c:p_m' or 'name:p_c:p_m'. Can be repeated.",
    )
    parser.add_argument(
        "--skip-bogp",
        action="store_true",
        help="Run only fixed-rate GP baselines.",
    )
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "outputs" / "formal_experiments"),
    )
    parser.add_argument("--run-id", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    fixed_methods = tuple(args.fixed_rate or [FixedRateMethodConfig()])
    config = FormalExperimentConfig(
        problem_name=args.problem,
        seeds=args.seeds,
        population_size=args.population_size,
        total_generations=args.total_generations,
        archive_size=args.archive_size,
        archive_structure_key_mode=args.archive_structure_key_mode,
        fixed_rate_methods=fixed_methods,
        include_bogp_current=not args.skip_bogp,
        output_root=args.output_root,
        run_id=args.run_id,
    )
    result = run_registered_experiment(config)
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "summary_by_seed_path": str(result.summary_by_seed_path),
                "aggregate_summary_path": str(result.aggregate_summary_path),
                "run_count": len(result.run_summaries),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
