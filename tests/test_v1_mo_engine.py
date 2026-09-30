from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.test_v1_mo_engine import (
    MultiObjectiveGPConfig,
    MultiObjectiveGPEngine,
    assign_rank_and_crowding,
)
from bogp.test_v1_problem import EvaluatedIndividual, ObjectiveSpec
from bogp.test_v1_template_problem import TemplateSymbolicRegressionProblem
from bogp.types import ControlInput


class MultiObjectiveEngineTests(unittest.TestCase):
    def test_non_dominated_sort_assigns_expected_first_front(self) -> None:
        objectives = (
            ObjectiveSpec("a", "minimize"),
            ObjectiveSpec("b", "minimize"),
        )
        population = [
            EvaluatedIndividual("a", (0.2, 0.8)),
            EvaluatedIndividual("b", (0.5, 0.4)),
            EvaluatedIndividual("c", (0.8, 0.9)),
        ]
        fronts = assign_rank_and_crowding(population, objectives)
        self.assertEqual({item.individual for item in fronts[0]}, {"a", "b"})
        self.assertEqual(population[2].rank, 1)

    def test_template_engine_runs_interval(self) -> None:
        problem = TemplateSymbolicRegressionProblem(sample_count=11)
        engine = MultiObjectiveGPEngine(
            problem,
            MultiObjectiveGPConfig(
                population_size=10,
                total_generations=4,
                random_seed=3,
            ),
        )
        start = engine.snapshot()
        result = engine.run_interval(
            ControlInput(crossover_rate=0.70, mutation_rate=0.20, update_period=2)
        )
        self.assertEqual(result.start_state.generation, start.generation)
        self.assertEqual(result.end_state.generation, 2)
        self.assertEqual(len(result.diversity_values), 2)
        self.assertGreaterEqual(result.end_state.hypervolume, 0.0)


if __name__ == "__main__":
    unittest.main()
