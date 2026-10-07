from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.types import GPStateSnapshot


def make_context(generation: int = 0, total_generations: int = 10) -> GPStateSnapshot:
    return GPStateSnapshot(
        generation=generation,
        total_generations=total_generations,
        hypervolume=0.2,
        recent_hv_delta=0.01,
        diversity=0.5,
        best_fitness=1.0,
        recent_best_improvement=0.0,
        stagnation_generations=0,
        mean_tree_size=10.0,
    )


class ControllerKTests(unittest.TestCase):
    def test_controller_returns_update_period_from_candidate_set(self) -> None:
        controller = ContextualBayesianRateController(
            BOControllerConfig(
                candidate_k_values=(1, 3),
                warmup_per_k=1,
                min_observations_per_k=1,
                candidate_pool_size_per_k=16,
                random_seed=5,
            )
        )
        control = controller.propose(make_context())
        self.assertIn(control.update_period, {1, 3})

    def test_register_observation_keeps_k_specific_history(self) -> None:
        controller = ContextualBayesianRateController(
            BOControllerConfig(
                candidate_k_values=(1, 3),
                warmup_per_k=1,
                min_observations_per_k=1,
                candidate_pool_size_per_k=16,
                random_seed=5,
            )
        )
        context = make_context()
        control = controller.propose(context)
        controller.register_observation(context, control, 0.5)
        self.assertEqual(controller.observation_count, 1)

    def test_interleaved_warmup_cycles_across_k_values(self) -> None:
        controller = ContextualBayesianRateController(
            BOControllerConfig(
                candidate_k_values=(1, 3, 5),
                warmup_strategy="interleaved",
                warmup_per_k=2,
                min_observations_per_k=1,
                candidate_pool_size_per_k=16,
                random_seed=5,
            )
        )
        context = make_context(total_generations=30)
        selected = []
        for index in range(6):
            control = controller.propose(context)
            selected.append(control.update_period)
            controller.register_observation(context, control, float(index))

        self.assertEqual(selected, [1, 3, 5, 1, 3, 5])

    def test_global_ei_best_value_uses_all_k_histories(self) -> None:
        controller = ContextualBayesianRateController(
            BOControllerConfig(
                candidate_k_values=(1, 3),
                ei_best_scope="global",
                random_seed=5,
            )
        )
        controller._y_history_by_k[1].append(0.25)
        controller._y_history_by_k[3].append(0.90)

        self.assertEqual(controller._ei_best_value(np.asarray([0.25])), 0.90)

    def test_controller_rejects_unknown_bo_strategy_options(self) -> None:
        with self.assertRaises(ValueError):
            BOControllerConfig(warmup_strategy="unknown")
        with self.assertRaises(ValueError):
            BOControllerConfig(ei_best_scope="unknown")


if __name__ == "__main__":
    unittest.main()
