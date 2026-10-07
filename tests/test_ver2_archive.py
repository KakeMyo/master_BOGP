from __future__ import annotations

from dataclasses import dataclass
import sys
import unittest
from pathlib import Path
from typing import Iterable, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.diversity import TreeNodeToken
from bogp.test_v1_problem import EvaluatedIndividual, ObjectiveSpec
from bogp.test_ver2_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.types import ControlInput


@dataclass(frozen=True)
class DummyIndividual:
    objective_values: Tuple[float, float]
    structure_label: str


class DummyArchiveProblem:
    objectives = (
        ObjectiveSpec("a", "minimize", lower=0.0, upper=1.0),
        ObjectiveSpec("b", "minimize", lower=0.0, upper=1.0),
    )

    def create_individual(self, rng) -> DummyIndividual:
        return DummyIndividual((0.9, 0.9), "seed")

    def evaluate(self, individual: DummyIndividual) -> Sequence[float]:
        return individual.objective_values

    def crossover(
        self,
        parent_a: DummyIndividual,
        parent_b: DummyIndividual,
        rng,
    ) -> Tuple[DummyIndividual, DummyIndividual]:
        return parent_a, parent_b

    def mutate(self, individual: DummyIndividual, rng) -> DummyIndividual:
        return individual

    def tree_size(self, individual: DummyIndividual) -> int:
        return 1

    def structural_tokens(self, individual: DummyIndividual) -> Iterable[TreeNodeToken]:
        return [TreeNodeToken(individual.structure_label, 0)]


class TestVer2ArchiveTests(unittest.TestCase):
    def test_archive_dedupes_by_objective_and_structure_pair(self) -> None:
        engine = MultiObjectiveGPEngine(
            DummyArchiveProblem(),
            MultiObjectiveGPConfig(population_size=2, total_generations=1, random_seed=1),
        )
        candidates = [
            EvaluatedIndividual(DummyIndividual((0.1, 0.5), "same"), (0.1, 0.5)),
            EvaluatedIndividual(DummyIndividual((0.1, 0.5), "same"), (0.1, 0.5)),
            EvaluatedIndividual(DummyIndividual((0.1, 0.5), "different"), (0.1, 0.5)),
            EvaluatedIndividual(DummyIndividual((0.8, 0.8), "dominated"), (0.8, 0.8)),
        ]

        engine._update_archive(candidates)
        stats = engine.archive_statistics()

        self.assertEqual(stats["archive_size"], 2)
        self.assertEqual(stats["archive_unique_pair_size"], 2)
        self.assertEqual(stats["archive_unique_objective_size"], 1)
        self.assertEqual(stats["archive_unique_structure_size"], 2)
        self.assertEqual(len(engine.unique_objective_archive), 1)

    def test_archive_objective_key_uses_rounding_precision(self) -> None:
        engine = MultiObjectiveGPEngine(
            DummyArchiveProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=1,
                random_seed=1,
                objective_key_precision=3,
            ),
        )
        candidates = [
            EvaluatedIndividual(DummyIndividual((0.10001, 0.5), "same"), (0.10001, 0.5)),
            EvaluatedIndividual(DummyIndividual((0.10002, 0.5), "same"), (0.10002, 0.5)),
        ]

        engine._update_archive(candidates)
        stats = engine.archive_statistics()

        self.assertEqual(stats["archive_size"], 1)
        self.assertEqual(stats["archive_unique_objective_size"], 1)
        self.assertEqual(stats["archive_unique_structure_size"], 1)

    def test_state_history_records_each_generation(self) -> None:
        engine = MultiObjectiveGPEngine(
            DummyArchiveProblem(),
            MultiObjectiveGPConfig(population_size=2, total_generations=3, random_seed=1),
        )

        engine.run_interval(
            ControlInput(crossover_rate=0.70, mutation_rate=0.20, update_period=2)
        )
        engine.run_interval(
            ControlInput(crossover_rate=0.70, mutation_rate=0.20, update_period=2)
        )

        generations = [state.generation for state in engine.state_history]
        self.assertEqual(generations, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
