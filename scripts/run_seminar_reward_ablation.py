"""Remove each active reward term under the final Seminar settings.

The other weights are left unchanged. Inactive stagnation/bloat terms are
audited analytically rather than enabled with arbitrary new weights.
"""
from __future__ import annotations

import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.setrecursionlimit(10000)

from sklearn.exceptions import ConvergenceWarning
from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.formal_experiment import (
    FormalExperimentConfig, _engine_config, _bogp_control_records,
    _generation_metrics_rows, registered_problem_specs,
)
from bogp.loop import ClosedLoopRunner
from bogp.objectives import RewardConfig

VARIANTS = {
    "no_hv": {"hv_weight": 0.0},
    "no_diversity": {"diversity_weight": 0.0},
    "no_control_cost": {"control_cost_weight": 0.0},
    "no_floor": {"floor_penalty_weight": 0.0},
    "full": {},
}
DEFAULT_OUT = ROOT / "outputs/seminar_reward_ablation/20261001"


def run_one(task):
    seed, variant, destination = task
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    reward_config = replace(RewardConfig(), **VARIANTS[variant])
    controller_config = BOControllerConfig(random_seed=seed)
    config = FormalExperimentConfig(population_size=24, total_generations=78)
    path = Path(destination) / variant / f"seed_{seed}.json"
    if path.exists():
        saved = json.loads(path.read_text())
        assert saved["reward_config"] == asdict(reward_config), path
        assert saved["controller_config"] == json.loads(json.dumps(asdict(controller_config))), path
        assert saved["seed"] == seed and saved["evaluations"] == 1872, path
        assert len(saved["generations"]) == 79, path
        return str(path)
    spec = registered_problem_specs()["sr_alpha_friedman"]
    engine = spec.engine_factory(spec.factory(), _engine_config(config, seed))
    controller = ContextualBayesianRateController(controller_config)
    records = ClosedLoopRunner(engine, controller, reward_config).run()
    payload = {
        "seed": seed, "method": variant,
        "controller_config": asdict(controller_config),
        "reward_config": asdict(reward_config),
        "generations": _generation_metrics_rows(engine.generation_metrics_history, 2),
        "records": _bogp_control_records(records, 2),
        "states": [{"start": asdict(r.start_state), "end": asdict(r.end_state)} for r in records],
        "evaluations": sum(r.evaluations for r in records),
    }
    assert payload["evaluations"] == 1872
    assert len(payload["generations"]) == 79
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-count", type=int, default=100)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--variant", action="append", choices=tuple(VARIANTS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    if args.seed_count < 1 or args.workers < 1:
        parser.error("seed-count and workers must be positive")
    variants = args.variant or [name for name in VARIANTS if name != "full"]
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "problem": "sr_alpha_friedman", "seeds": list(range(args.seed_count)),
        "population_size": 24, "total_generations": 78, "warmup_generations": 18,
        "evaluations_per_run": 1872, "variants": {v: VARIANTS[v] for v in variants},
        "remaining_weights_renormalized": False,
        "baseline": str(ROOT / "outputs/seminar_context_ablation/20261001/contextual"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tasks = [(seed, variant, args.output_dir) for seed in range(args.seed_count) for variant in variants]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]
        for count, future in enumerate(as_completed(futures), 1):
            print(f"{count}/{len(tasks)} {future.result()}", flush=True)


if __name__ == "__main__":
    main()
