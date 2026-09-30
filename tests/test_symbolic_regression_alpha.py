from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.formal_experiment import FormalExperimentConfig, run_registered_experiment
from bogp.symbolic_regression_alpha import AlphaExpressionNode, SymbolicRegressionAlphaProblem


class SymbolicRegressionAlphaTests(unittest.TestCase):
    def test_friedman_problem_evaluates_two_objectives(self) -> None:
        problem = SymbolicRegressionAlphaProblem.friedman_i(
            n_train=12,
            n_test=12,
            dataset_seed=1,
        )
        individual = AlphaExpressionNode(
            op="add",
            children=(
                AlphaExpressionNode(op="var", variable_index=0),
                AlphaExpressionNode(op="const", value=1.0),
            ),
        )

        values = problem.evaluate(individual)

        self.assertEqual(len(values), 2)
        self.assertGreaterEqual(values[0], 0.0)
        self.assertLessEqual(values[0], problem.error_upper)
        self.assertEqual(values[1], 3.0)

    def test_poly10_problem_uses_ten_variables_and_protected_division_is_finite(self) -> None:
        problem = SymbolicRegressionAlphaProblem.poly10(
            n_train=12,
            n_test=12,
            dataset_seed=2,
        )
        individual = AlphaExpressionNode(
            op="div",
            children=(
                AlphaExpressionNode(op="var", variable_index=0),
                AlphaExpressionNode(op="const", value=0.0),
            ),
        )

        values = problem.evaluate(individual)

        self.assertEqual(problem.variable_count, 10)
        self.assertEqual(len(values), 2)
        self.assertGreaterEqual(values[0], 0.0)
        self.assertLessEqual(values[0], problem.error_upper)

    def test_registered_friedman_alpha_smoke_experiment_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FormalExperimentConfig(
                problem_name="sr_alpha_friedman",
                seeds=(0,),
                population_size=6,
                total_generations=1,
                include_bogp_current=False,
                output_root=tmpdir,
                run_id="sr_alpha_smoke",
            )

            result = run_registered_experiment(config)

            self.assertEqual(len(result.run_summaries), 1)
            self.assertTrue((result.output_dir / "summary_by_seed.csv").exists())


if __name__ == "__main__":
    unittest.main()
