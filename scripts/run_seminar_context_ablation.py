"""Paired Seminar ablation: remove state features, retain reward feedback."""
from __future__ import annotations

import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.setrecursionlimit(10000)
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.formal_experiment import FormalExperimentConfig, _engine_config, _bogp_control_records, _generation_metrics_rows, registered_problem_specs
from bogp.loop import ClosedLoopRunner
from bogp.objectives import RewardConfig


class NonContextualController(ContextualBayesianRateController):
    def __init__(self, config):
        super().__init__(config)
        self._kernel = (ConstantKernel(1.0, (0.1, 10.0)) *
                        Matern(length_scale=np.ones(2), length_scale_bounds=(1e-2, 10.0), nu=2.5) +
                        WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-6, 1e-1)))

    def _context_features(self, context):
        return []


def run_one(task):
    seed, method, destination = task
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    path = Path(destination) / method / f"seed_{seed}.json"
    if path.exists():
        return str(path)
    spec = registered_problem_specs()["sr_alpha_friedman"]
    config = FormalExperimentConfig(population_size=24, total_generations=78)
    engine = spec.engine_factory(spec.factory(), _engine_config(config, seed))
    cls = ContextualBayesianRateController if method == "contextual" else NonContextualController
    controller = cls(BOControllerConfig(random_seed=seed))
    records = ClosedLoopRunner(engine, controller, RewardConfig()).run()
    generations = _generation_metrics_rows(engine.generation_metrics_history, 2)
    payload = {"seed": seed, "method": method, "controller_config": asdict(controller.config),
               "reward_config": asdict(RewardConfig()), "generations": generations,
               "records": _bogp_control_records(records, 2),
               "evaluations": sum(r.evaluations for r in records)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-count", type=int, default=100)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/seminar_context_ablation/20261001"))
    args = parser.parse_args()
    tasks = [(s, m, args.output_dir) for s in range(args.seed_count) for m in ("contextual", "noncontextual")]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]
        for i, future in enumerate(as_completed(futures), 1):
            print(f"{i}/{len(tasks)} {future.result()}", flush=True)


if __name__ == "__main__":
    main()
