from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.loop import ClosedLoopRunner
from bogp.objectives import RewardConfig
from bogp.test_v1_toy_engine import ToyDynamicGPEngine
from sklearn.exceptions import ConvergenceWarning


def main() -> int:
    warnings.filterwarnings("ignore", category=ConvergenceWarning)

    controller = ContextualBayesianRateController(
        BOControllerConfig(
            candidate_k_values=(1, 3, 5),
            warmup_per_k=2,
            min_observations_per_k=2,
            candidate_pool_size_per_k=128,
            random_seed=7,
        )
    )
    engine = ToyDynamicGPEngine()
    runner = ClosedLoopRunner(engine=engine, controller=controller, reward_config=RewardConfig())
    records = runner.run(max_control_steps=20)

    if not records:
        print("No control steps were executed.")
        return 1

    first = records[0]
    last = records[-1]
    best_reward = max(record.reward.total for record in records)
    print("Closed-loop smoke test completed.")
    print(
        "Initial control: p_c={0:.3f}, p_m={1:.3f}, k={2}".format(
            first.control.crossover_rate,
            first.control.mutation_rate,
            first.control.update_period,
        )
    )
    print(
        "Final control:   p_c={0:.3f}, p_m={1:.3f}, k={2}".format(
            last.control.crossover_rate,
            last.control.mutation_rate,
            last.control.update_period,
        )
    )
    print(
        "HV change:      {0:.4f} -> {1:.4f}".format(
            first.start_state.hypervolume,
            last.end_state.hypervolume,
        )
    )
    print(
        "Final metrics: generation={0}, diversity={1:.4f}, best_reward={2:.4f}".format(
            last.end_state.generation,
            last.end_state.diversity,
            best_reward,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
