from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .test_v1_mo_engine import MultiObjectiveGPEngine
from .types import ControlInput, GPStateSnapshot


@dataclass(frozen=True)
class PlainGPBaselineConfig:
    """Fixed-rate GP baseline without BO-based closed-loop control."""

    crossover_rate: float = 0.80
    mutation_rate: float = 0.05


@dataclass(frozen=True)
class PlainGPGenerationRecord:
    generation: int
    hypervolume: float
    diversity: float
    mean_tree_size: float
    stagnation_generations: int
    evaluations: int
    crossover_rate: float
    mutation_rate: float


class PlainFixedRateGPRunner:
    """Run the generic multi-objective GP with fixed operator rates."""

    def __init__(
        self,
        engine: MultiObjectiveGPEngine,
        config: PlainGPBaselineConfig | None = None,
    ) -> None:
        self.engine = engine
        self.config = config or PlainGPBaselineConfig()
        self.control = ControlInput(
            crossover_rate=self.config.crossover_rate,
            mutation_rate=self.config.mutation_rate,
            update_period=1,
        )

    def run(self) -> List[PlainGPGenerationRecord]:
        records: List[PlainGPGenerationRecord] = []
        records.append(self._record_from_snapshot(self.engine.snapshot(), evaluations=0))

        while True:
            snapshot = self.engine.snapshot()
            if snapshot.generation >= snapshot.total_generations:
                break

            result = self.engine.run_interval(self.control, interval_generations=1)
            records.append(
                self._record_from_snapshot(
                    result.end_state,
                    evaluations=result.evaluations,
                )
            )

        return records

    def _record_from_snapshot(
        self,
        snapshot: GPStateSnapshot,
        evaluations: int,
    ) -> PlainGPGenerationRecord:
        return PlainGPGenerationRecord(
            generation=snapshot.generation,
            hypervolume=snapshot.hypervolume,
            diversity=snapshot.diversity,
            mean_tree_size=snapshot.mean_tree_size,
            stagnation_generations=snapshot.stagnation_generations,
            evaluations=evaluations,
            crossover_rate=self.control.crossover_rate,
            mutation_rate=self.control.mutation_rate,
        )
