from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.test_v1_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.test_v1_plain_gp_baseline import PlainFixedRateGPRunner, PlainGPBaselineConfig
from bogp.test_v1_template_problem import TemplateSymbolicRegressionProblem


class PlainGPBaselineTests(unittest.TestCase):
    def test_plain_gp_runs_one_record_per_generation_plus_initial_state(self) -> None:
        engine = MultiObjectiveGPEngine(
            TemplateSymbolicRegressionProblem(sample_count=11),
            MultiObjectiveGPConfig(
                population_size=8,
                total_generations=3,
                random_seed=11,
            ),
        )
        runner = PlainFixedRateGPRunner(
            engine,
            PlainGPBaselineConfig(crossover_rate=0.8, mutation_rate=0.05),
        )
        records = runner.run()

        self.assertEqual([record.generation for record in records], [0, 1, 2, 3])
        self.assertTrue(all(record.crossover_rate == 0.8 for record in records))
        self.assertTrue(all(record.mutation_rate == 0.05 for record in records))


if __name__ == "__main__":
    unittest.main()
