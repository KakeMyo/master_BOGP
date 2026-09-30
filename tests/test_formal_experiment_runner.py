from __future__ import annotations

from dataclasses import dataclass
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Iterable, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.diversity import TreeNodeToken
from bogp.formal_experiment import (
    FixedRateMethodConfig,
    FormalExperimentConfig,
    ProblemSpec,
    run_problem_experiment,
    run_registered_experiment,
)
from bogp.test_v1_problem import ObjectiveSpec
from bogp.test_v1_structural_problem import StructuralSearchProblem


@dataclass(frozen=True)
class ThreeObjectiveIndividual:
    value: float


class ThreeObjectiveProblem:
    objectives = (
        ObjectiveSpec("first", "minimize", lower=0.0, upper=1.0),
        ObjectiveSpec("second", "minimize", lower=0.0, upper=1.0),
        ObjectiveSpec("third", "minimize", lower=0.0, upper=1.0),
    )

    def create_individual(self, rng) -> ThreeObjectiveIndividual:
        return ThreeObjectiveIndividual(float(rng.random()))

    def evaluate(self, individual: ThreeObjectiveIndividual) -> Sequence[float]:
        value = individual.value
        return (value, 1.0 - value, abs(0.5 - value))

    def crossover(
        self,
        parent_a: ThreeObjectiveIndividual,
        parent_b: ThreeObjectiveIndividual,
        rng,
    ) -> Tuple[ThreeObjectiveIndividual, ThreeObjectiveIndividual]:
        midpoint = (parent_a.value + parent_b.value) / 2.0
        return ThreeObjectiveIndividual(midpoint), ThreeObjectiveIndividual(midpoint)

    def mutate(self, individual: ThreeObjectiveIndividual, rng) -> ThreeObjectiveIndividual:
        return ThreeObjectiveIndividual(float(min(max(individual.value + 0.05, 0.0), 1.0)))

    def tree_size(self, individual: ThreeObjectiveIndividual) -> int:
        return 1

    def structural_tokens(self, individual: ThreeObjectiveIndividual) -> Iterable[TreeNodeToken]:
        return [TreeNodeToken("value", 0)]


class FormalExperimentRunnerTests(unittest.TestCase):
    def test_template_problem_writes_common_outputs_for_plain_and_bogp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FormalExperimentConfig(
                problem_name="template",
                seeds=(3,),
                population_size=6,
                total_generations=1,
                fixed_rate_methods=(
                    FixedRateMethodConfig(
                        name="plain_fixed",
                        crossover_rate=0.80,
                        mutation_rate=0.05,
                    ),
                ),
                include_bogp_current=True,
                bo_controller_overrides={
                    "candidate_k_values": (1,),
                    "warmup_per_k": 1,
                    "min_observations_per_k": 1,
                    "candidate_pool_size_per_k": 8,
                },
                reward_overrides={"max_update_period": 1},
                output_root=tmpdir,
                run_id="template_smoke",
            )

            result = run_registered_experiment(config)
            method_names = {row["method_name"] for row in result.run_summaries}

            self.assertEqual(method_names, {"plain_fixed", "bogp_current"})
            self.assertTrue((result.output_dir / "config.json").exists())
            self.assertTrue(result.summary_by_seed_path.exists())
            self.assertTrue(result.aggregate_summary_path.exists())
            for method_name in method_names:
                run_dir = result.output_dir / "runs" / method_name / "seed_3"
                self.assertTrue((run_dir / "summary.json").exists())
                self.assertTrue((run_dir / "generation_metrics.jsonl").exists())
                self.assertTrue((run_dir / "control_records.jsonl").exists())
                self.assertTrue((run_dir / "pareto_archive.json").exists())
                self.assertTrue((run_dir / "unique_objective_archive.json").exists())

            metric_rows = (
                result.output_dir
                / "runs"
                / "plain_fixed"
                / "seed_3"
                / "generation_metrics.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            first_metric = json.loads(metric_rows[0])
            self.assertIsInstance(first_metric["archive_hypervolume"], float)

    def test_structural_problem_can_use_same_runner_with_topology_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = ProblemSpec(
                name="structural_small",
                factory=lambda: StructuralSearchProblem(max_initial_depth=2, time_steps=31),
            )
            config = FormalExperimentConfig(
                problem_name="structural_small",
                seeds=(4,),
                population_size=4,
                total_generations=1,
                archive_structure_key_mode="topology",
                fixed_rate_methods=(FixedRateMethodConfig(),),
                include_bogp_current=False,
                output_root=tmpdir,
                run_id="structural_smoke",
            )

            result = run_problem_experiment(spec, config)
            summary = result.run_summaries[0]

            self.assertEqual(summary["problem_name"], "structural_small")
            self.assertEqual(summary["archive_structure_key_mode"], "topology")
            self.assertEqual(summary["method_name"], "plain_fixed")
            self.assertTrue((result.output_dir / "hv_progress.png").exists())
            self.assertTrue((result.output_dir / "diversity_progress.png").exists())

    def test_three_objective_problem_marks_hv_as_not_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            spec = ProblemSpec(
                name="three_objective",
                factory=lambda: ThreeObjectiveProblem(),
            )
            config = FormalExperimentConfig(
                problem_name="three_objective",
                seeds=(5,),
                population_size=4,
                total_generations=1,
                fixed_rate_methods=(FixedRateMethodConfig(),),
                include_bogp_current=False,
                output_root=tmpdir,
                run_id="three_objective_smoke",
            )

            result = run_problem_experiment(spec, config)
            summary = result.run_summaries[0]
            metrics_path = (
                result.output_dir
                / "runs"
                / "plain_fixed"
                / "seed_5"
                / "generation_metrics.jsonl"
            )
            first_metric = json.loads(metrics_path.read_text(encoding="utf-8").splitlines()[0])

            self.assertEqual(summary["final_archive_hypervolume"], "not_available")
            self.assertEqual(first_metric["archive_hypervolume"], "not_available")
            self.assertTrue(result.aggregate_summary_path.exists())


if __name__ == "__main__":
    unittest.main()
