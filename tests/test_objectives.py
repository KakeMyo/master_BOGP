from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.objectives import RewardConfig, compute_reward, target_diversity
from bogp.types import GPStateSnapshot


def make_state(
    generation: int,
    hypervolume: float,
    diversity: float,
    stagnation: int,
    tree_size: float,
) -> GPStateSnapshot:
    return GPStateSnapshot(
        generation=generation,
        total_generations=60,
        hypervolume=hypervolume,
        recent_hv_delta=0.0,
        diversity=diversity,
        best_fitness=1.0,
        recent_best_improvement=0.0,
        stagnation_generations=stagnation,
        mean_tree_size=tree_size,
    )


class RewardTests(unittest.TestCase):
    def test_target_diversity_decreases_over_time(self) -> None:
        config = RewardConfig()
        self.assertGreater(target_diversity(0.0, config), target_diversity(1.0, config))

    def test_reward_is_positive_for_hv_gain_and_healthy_diversity(self) -> None:
        config = RewardConfig()
        start = make_state(0, hypervolume=0.20, diversity=0.60, stagnation=0, tree_size=10.0)
        end = make_state(3, hypervolume=0.25, diversity=0.57, stagnation=1, tree_size=12.0)
        reward = compute_reward(start, end, config)
        self.assertGreater(reward.total, 0.0)

    def test_reward_penalizes_diversity_collapse(self) -> None:
        config = RewardConfig()
        start = make_state(30, hypervolume=0.45, diversity=0.30, stagnation=0, tree_size=20.0)
        end = make_state(33, hypervolume=0.46, diversity=0.02, stagnation=8, tree_size=35.0)
        reward = compute_reward(start, end, config)
        self.assertGreater(reward.floor_penalty, 0.0)
        self.assertLess(reward.total, 0.0)


if __name__ == "__main__":
    unittest.main()

