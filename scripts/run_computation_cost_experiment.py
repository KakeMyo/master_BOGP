#!/usr/bin/env python3
"""Run isolated, paired computation-cost experiments for fixed GP and BOGP."""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path


# Set these before importing NumPy/SciPy through bogp.  Every worker is also
# launched with the same explicit environment by the experiment orchestrator.
for _variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ[_variable] = "1"
os.environ["PYTHONHASHSEED"] = "0"
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")
sys.setrecursionlimit(10000)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.computation_cost_analysis import analyze_computation_cost  # noqa: E402
from bogp.computation_cost_experiment import (  # noqa: E402
    METHOD_ORDER,
    CostExperimentConfig,
    CostWorkerSpec,
    run_cost_experiment_subprocesses,
    run_cost_worker,
)
from sklearn.exceptions import ConvergenceWarning  # noqa: E402

warnings.filterwarnings("ignore", category=ConvergenceWarning)


def _method_list(value: str) -> tuple[str, ...]:
    methods = tuple(item.strip() for item in value.split(",") if item.strip())
    if not methods:
        raise argparse.ArgumentTypeError("--methods must contain at least one method.")
    unknown = sorted(set(methods) - set(METHOD_ORDER))
    if unknown:
        raise argparse.ArgumentTypeError(
            "Unknown methods: " + ", ".join(unknown)
        )
    if len(set(methods)) != len(methods):
        raise argparse.ArgumentTypeError("--methods must not contain duplicates.")
    return methods


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure fixed-GP and BOGP wall/CPU time in isolated single-threaded "
            "processes, then produce paired-seed cost and quality-time analyses."
        )
    )
    parser.add_argument("--seed-count", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--population-size", type=int, default=24)
    parser.add_argument("--total-generations", type=int, default=78)
    parser.add_argument("--tournament-size", type=int, default=3)
    parser.add_argument("--archive-size", type=int, default=200)
    parser.add_argument("--matched-warmup-generations", type=int, default=18)
    parser.add_argument("--setting-name", default="g78_main")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--output-root",
        default=str(ROOT / "outputs" / "computation_cost_friedman"),
    )
    parser.add_argument(
        "--replay-source-run",
        default=None,
        help=(
            "Prior formal-experiment directory containing "
            "runs/bogp_current/seed_<n>/control_records.jsonl."
        ),
    )
    parser.add_argument(
        "--methods",
        type=_method_list,
        default=METHOD_ORDER,
        help="Comma-separated subset of the seven registered methods.",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    parser.add_argument("--analysis-random-seed", type=int, default=20260731)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--worker-spec",
        default=None,
        help=argparse.SUPPRESS,
    )
    return parser


def _validate_master_arguments(args: argparse.Namespace) -> None:
    if args.seed_count <= 0:
        raise ValueError("--seed-count must be positive.")
    if args.population_size <= 0:
        raise ValueError("--population-size must be positive.")
    if args.total_generations <= 0:
        raise ValueError("--total-generations must be positive.")
    if args.tournament_size <= 0 or args.archive_size <= 0:
        raise ValueError("Tournament and archive sizes must be positive.")
    if args.matched_warmup_generations < 0:
        raise ValueError("--matched-warmup-generations must be nonnegative.")
    if args.bootstrap_samples <= 0:
        raise ValueError("--bootstrap-samples must be positive.")
    if "bogp_replay" in args.methods and not args.replay_source_run:
        raise ValueError("--replay-source-run is required for bogp_replay.")

    if args.replay_source_run:
        source = Path(args.replay_source_run)
        for seed in range(args.seed_start, args.seed_start + args.seed_count):
            control_path = (
                source
                / "runs"
                / "bogp_current"
                / f"seed_{seed}"
                / "control_records.jsonl"
            )
            if not control_path.is_file():
                raise FileNotFoundError(f"Replay control trace not found: {control_path}")


def _run_worker(spec_path: Path) -> int:
    with spec_path.open("r", encoding="utf-8") as handle:
        spec = CostWorkerSpec.from_dict(json.load(handle))
    summary = run_cost_worker(spec)
    print(
        json.dumps(
            {
                "method_name": summary["method_name"],
                "seed": summary["seed"],
                "total_algorithm_wall_seconds": summary[
                    "total_algorithm_wall_seconds"
                ],
                "final_archive_hypervolume": summary[
                    "final_archive_hypervolume"
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


def main() -> int:
    args = build_parser().parse_args()
    if args.worker_spec:
        return _run_worker(Path(args.worker_spec))

    _validate_master_arguments(args)
    run_id = args.run_id or "cost_{setting}_seed{count}_{time}".format(
        setting=args.setting_name,
        count=args.seed_count,
        time=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    config = CostExperimentConfig(
        output_root=args.output_root,
        run_id=run_id,
        setting_name=args.setting_name,
        seeds=seeds,
        population_size=args.population_size,
        total_generations=args.total_generations,
        tournament_size=args.tournament_size,
        archive_size=args.archive_size,
        replay_source_run=args.replay_source_run,
        methods=args.methods,
        matched_warmup_generations=args.matched_warmup_generations,
        resume=args.resume,
        bootstrap_samples=args.bootstrap_samples,
        analysis_random_seed=args.analysis_random_seed,
        extra_metadata={
            "timing_protocol": "isolated_process_single_thread_balanced_order",
            "quality_time_primary_methods": [
                "fixed_standard",
                "fixed_high_mutation",
                "fixed_high_crossover",
                "bogp_adaptive",
                "bogp_k1_matched",
            ],
            "fixed_core_role": "minimal_observation_timing_ablation",
            "replay_role": "controller_learning_overhead_ablation",
        },
    )

    worker_script = Path(__file__).resolve()
    run_cost_experiment_subprocesses(config, worker_script)
    analysis_dir = config.output_dir / "analysis"
    analysis = analyze_computation_cost(
        config.output_dir / "run_summary.csv",
        config.output_dir / "generation_trace.csv",
        analysis_dir,
        bootstrap_samples=config.bootstrap_samples,
        bootstrap_seed=config.analysis_random_seed,
    )
    print(f"Experiment: {config.output_dir}", flush=True)
    print(f"Analysis:   {analysis_dir}", flush=True)
    print(
        json.dumps(analysis, ensure_ascii=False, sort_keys=True, default=str),
        flush=True,
    )
    calibration_path = config.output_dir / "timing_calibration.json"
    print(f"Calibration: {calibration_path}", flush=True)
    with analysis["validation_report.json"].open("r", encoding="utf-8") as handle:
        validation = json.load(handle)
    if not validation.get("overall_ok", False):
        raise RuntimeError(
            "Computation-cost validation failed; inspect "
            f"{analysis['validation_report.json']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
