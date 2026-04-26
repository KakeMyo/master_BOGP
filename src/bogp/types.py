from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .context_metrics import ContextMetricConfig, build_context_vector


@dataclass(frozen=True)
class ControlInput:
    crossover_rate: float
    mutation_rate: float

    def as_tuple(self) -> Tuple[float, float]:
        return (self.crossover_rate, self.mutation_rate)


@dataclass(frozen=True)
class RateBounds:
    crossover_min: float = 0.55
    crossover_max: float = 0.95
    mutation_min: float = 0.01
    mutation_max: float = 0.30
    max_total_rate: float = 1.00
    max_step: float = 0.12

    def clamp(
        self,
        control: ControlInput,
        previous: ControlInput = None,
    ) -> ControlInput:
        crossover = min(max(control.crossover_rate, self.crossover_min), self.crossover_max)
        mutation = min(max(control.mutation_rate, self.mutation_min), self.mutation_max)

        if previous is not None:
            crossover_delta = max(
                -self.max_step,
                min(self.max_step, crossover - previous.crossover_rate),
            )
            mutation_delta = max(
                -self.max_step,
                min(self.max_step, mutation - previous.mutation_rate),
            )
            crossover = previous.crossover_rate + crossover_delta
            mutation = previous.mutation_rate + mutation_delta

        crossover = min(max(crossover, self.crossover_min), self.crossover_max)
        mutation = min(max(mutation, self.mutation_min), self.mutation_max)

        if crossover + mutation > self.max_total_rate:
            total = crossover + mutation
            scale = self.max_total_rate / total
            crossover *= scale
            mutation *= scale

        crossover = min(max(crossover, self.crossover_min), self.crossover_max)
        mutation = min(max(mutation, self.mutation_min), self.mutation_max)

        if crossover + mutation > self.max_total_rate:
            overflow = crossover + mutation - self.max_total_rate
            mutation = max(self.mutation_min, mutation - overflow)
            if crossover + mutation > self.max_total_rate:
                crossover = max(self.crossover_min, self.max_total_rate - mutation)

        return ControlInput(crossover_rate=crossover, mutation_rate=mutation)


@dataclass(frozen=True)
class GPStateSnapshot:
    generation: int
    total_generations: int
    hypervolume: float
    recent_hv_delta: float
    diversity: float
    best_fitness: float
    recent_best_improvement: float
    stagnation_generations: int
    mean_tree_size: float

    @property
    def progress(self) -> float:
        if self.total_generations <= 0:
            return 0.0
        return min(1.0, max(0.0, self.generation / float(self.total_generations)))

    def feature_vector(
        self,
        metric_config: ContextMetricConfig | None = None,
        stagnation_scale: float = 15.0,
        tree_size_scale: float = 100.0,
        hv_delta_scale: float = 0.03,
    ) -> List[float]:
        metric_config = metric_config or ContextMetricConfig(
            hv_delta_scale=hv_delta_scale,
            stagnation_scale=stagnation_scale,
            tree_size_scale=tree_size_scale,
        )
        return build_context_vector(
            generation=self.generation,
            total_generations=self.total_generations,
            hypervolume=self.hypervolume,
            recent_hv_delta=self.recent_hv_delta,
            diversity=self.diversity,
            stagnation_generations=self.stagnation_generations,
            mean_tree_size=self.mean_tree_size,
            config=metric_config,
        )


@dataclass(frozen=True)
class IntervalResult:
    start_state: GPStateSnapshot
    end_state: GPStateSnapshot
    evaluations: int
