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
from bogp.test_ver2_b_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.types import ControlInput


@dataclass(frozen=True)
class ValueTree:
    kind: str
    value: float | None
    objective_values: Tuple[float, float]
    children: Tuple["ValueTree", ...] = ()


class ValueTreeProblem:
    objectives = (
        ObjectiveSpec("a", "minimize", lower=0.0, upper=1.0),
        ObjectiveSpec("b", "minimize", lower=0.0, upper=1.0),
    )

    def create_individual(self, rng) -> ValueTree:
        return ValueTree("seed", 0.0, (0.9, 0.9))

    def evaluate(self, individual: ValueTree) -> Sequence[float]:
        return individual.objective_values

    def crossover(
        self,
        parent_a: ValueTree,
        parent_b: ValueTree,
        rng,
    ) -> Tuple[ValueTree, ValueTree]:
        return parent_a, parent_b

    def mutate(self, individual: ValueTree, rng) -> ValueTree:
        return individual

    def tree_size(self, individual: ValueTree) -> int:
        return 1 + sum(self.tree_size(child) for child in individual.children)

    def structural_tokens(self, individual: ValueTree) -> Iterable[TreeNodeToken]:
        tokens = [TreeNodeToken(individual.kind, len(individual.children))]
        for child in individual.children:
            tokens.extend(self.structural_tokens(child))
        return tokens


class OffspringArchiveProblem(ValueTreeProblem):
    def __init__(self) -> None:
        self._created = 0

    def create_individual(self, rng) -> ValueTree:
        values = [
            ValueTree("extreme_left", None, (0.1, 0.9)),
            ValueTree("extreme_right", None, (0.9, 0.1)),
        ]
        item = values[self._created % len(values)]
        self._created += 1
        return item

    def crossover(
        self,
        parent_a: ValueTree,
        parent_b: ValueTree,
        rng,
    ) -> Tuple[ValueTree, ValueTree]:
        middle = ValueTree("middle", 1.0, (0.5, 0.5))
        return middle, middle


class TestVer2BArchiveMetrics(unittest.TestCase):
    def test_topology_mode_dedupes_same_topology_different_values(self) -> None:
        engine = MultiObjectiveGPEngine(
            ValueTreeProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=1,
                archive_structure_key_mode="topology",
            ),
        )
        candidates = [
            EvaluatedIndividual(ValueTree("spring", 1000.0, (0.1, 0.5)), (0.1, 0.5)),
            EvaluatedIndividual(ValueTree("spring", 1500.0, (0.1, 0.5)), (0.1, 0.5)),
        ]

        engine._update_archive(candidates)
        stats = engine.archive_statistics()

        self.assertEqual(stats["archive_size"], 1)
        self.assertEqual(stats["archive_unique_objective_size"], 1)
        self.assertEqual(stats["archive_unique_structure_size"], 1)
        self.assertEqual(stats["archive_unique_pair_size"], 1)

    def test_topology_value_mode_keeps_same_topology_different_values(self) -> None:
        engine = MultiObjectiveGPEngine(
            ValueTreeProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=1,
                archive_structure_key_mode="topology_value",
            ),
        )
        candidates = [
            EvaluatedIndividual(ValueTree("spring", 1000.0, (0.1, 0.5)), (0.1, 0.5)),
            EvaluatedIndividual(ValueTree("spring", 1500.0, (0.1, 0.5)), (0.1, 0.5)),
        ]

        engine._update_archive(candidates)
        stats = engine.archive_statistics()

        self.assertEqual(stats["archive_size"], 2)
        self.assertEqual(stats["archive_unique_objective_size"], 1)
        self.assertEqual(stats["archive_unique_structure_size"], 2)
        self.assertEqual(stats["archive_unique_pair_size"], 2)

    def test_invalid_structure_key_mode_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            MultiObjectiveGPConfig(archive_structure_key_mode="bad_mode")

    def test_offspring_only_nondominated_solution_is_archived(self) -> None:
        engine = MultiObjectiveGPEngine(
            OffspringArchiveProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=1,
                archive_structure_key_mode="topology_value",
            ),
        )

        engine.run_interval(ControlInput(crossover_rate=1.0, mutation_rate=0.0, update_period=1))

        archive_objectives = {item.objective_values for item in engine.archive}
        population_objectives = {item.objective_values for item in engine.evaluated_population}
        self.assertIn((0.5, 0.5), archive_objectives)
        self.assertNotIn((0.5, 0.5), population_objectives)

    def test_snapshot_uses_archive_hv_and_population_hv_is_separate(self) -> None:
        engine = MultiObjectiveGPEngine(
            OffspringArchiveProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=1,
                archive_structure_key_mode="topology_value",
            ),
        )

        engine.run_interval(ControlInput(crossover_rate=1.0, mutation_rate=0.0, update_period=1))

        snapshot = engine.snapshot()
        self.assertAlmostEqual(snapshot.hypervolume, 0.33)
        self.assertAlmostEqual(engine.population_hypervolume(), 0.17)
        self.assertGreater(snapshot.hypervolume, engine.population_hypervolume())

    def test_recent_hv_delta_is_archive_hv_rate(self) -> None:
        engine = MultiObjectiveGPEngine(
            OffspringArchiveProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=2,
                archive_structure_key_mode="topology_value",
            ),
        )

        start_hv = engine.snapshot().hypervolume
        result = engine.run_interval(
            ControlInput(crossover_rate=1.0, mutation_rate=0.0, update_period=2)
        )
        expected_rate = (result.end_state.hypervolume - start_hv) / 2.0

        self.assertAlmostEqual(result.end_state.recent_hv_delta, expected_rate)

    def test_generation_metrics_history_records_each_generation(self) -> None:
        engine = MultiObjectiveGPEngine(
            OffspringArchiveProblem(),
            MultiObjectiveGPConfig(
                population_size=2,
                total_generations=3,
                archive_structure_key_mode="topology_value",
            ),
        )

        engine.run_interval(ControlInput(crossover_rate=1.0, mutation_rate=0.0, update_period=2))
        engine.run_interval(ControlInput(crossover_rate=1.0, mutation_rate=0.0, update_period=2))

        generations = [item.generation for item in engine.generation_metrics_history]
        self.assertEqual(generations, [0, 1, 2, 3])
        self.assertTrue(
            all(item.archive_size >= item.archive_unique_objective_size for item in engine.generation_metrics_history)
        )


if __name__ == "__main__":
    unittest.main()
