from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.test_v1_hypervolume import hypervolume_2d_minimized
from bogp.test_v1_problem import EvaluatedIndividual, ObjectiveSpec


class ProblemHypervolumeTests(unittest.TestCase):
    def test_objective_direction_is_converted_to_minimization_space(self) -> None:
        minimize = ObjectiveSpec("loss", "minimize", lower=0.0, upper=10.0)
        maximize = ObjectiveSpec("score", "maximize", lower=0.0, upper=10.0)

        self.assertEqual(minimize.dominance_value(3.0), 3.0)
        self.assertEqual(maximize.dominance_value(3.0), -3.0)
        self.assertAlmostEqual(minimize.normalized_minimized_value(2.0), 0.2)
        self.assertAlmostEqual(maximize.normalized_minimized_value(8.0), 0.2)

    def test_evaluated_individual_supports_objective_lists(self) -> None:
        objectives = (
            ObjectiveSpec("loss", "minimize"),
            ObjectiveSpec("score", "maximize"),
        )
        item = EvaluatedIndividual("x", (2.0, 5.0))
        self.assertEqual(item.dominance_values(objectives), (2.0, -5.0))

    def test_two_objective_hypervolume_known_case(self) -> None:
        points = [(0.2, 0.8), (0.5, 0.4)]
        self.assertAlmostEqual(hypervolume_2d_minimized(points), 0.36)


if __name__ == "__main__":
    unittest.main()
