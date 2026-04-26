from __future__ import annotations

from dataclasses import dataclass
from math import exp

import numpy as np

from .types import ControlInput, GPStateSnapshot, IntervalResult


@dataclass
class ToyEngineConfig:
    total_generations: int = 60
    population_size: int = 200
    seed: int = 7
    hv_noise: float = 0.003
    diversity_noise: float = 0.010
    tree_noise: float = 0.500


class ToyDynamicGPEngine:
    """A lightweight simulator for checking whether the controller adapts over time."""

    def __init__(self, config: ToyEngineConfig = None) -> None:
        self.config = config or ToyEngineConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self._state = GPStateSnapshot(
            generation=0,
            total_generations=self.config.total_generations,
            hypervolume=0.10,
            recent_hv_delta=0.0,
            diversity=0.70,
            best_fitness=1.00,
            recent_best_improvement=0.0,
            stagnation_generations=0,
            mean_tree_size=8.0,
        )

    def snapshot(self) -> GPStateSnapshot:
        return GPStateSnapshot(**self._state.__dict__)

    def run_interval(self, control: ControlInput, interval_generations: int) -> IntervalResult:
        start_state = self.snapshot()
        interval_generations = max(1, interval_generations)
        remaining = self.config.total_generations - self._state.generation
        steps = min(interval_generations, remaining)

        cumulative_hv_delta = 0.0
        cumulative_best_improvement = 0.0

        for _ in range(steps):
            progress = self._state.progress
            target_crossover = 0.62 + (0.22 * progress)
            target_mutation = 0.25 - (0.15 * progress)

            distance = (
                ((control.crossover_rate - target_crossover) / 0.12) ** 2
                + ((control.mutation_rate - target_mutation) / 0.10) ** 2
            )

            base_gain = 0.038 * (1.0 - (0.45 * progress)) * exp(-0.5 * distance)
            diversity_bonus = 0.010 * max(0.0, self._state.diversity - 0.20)
            bloat_penalty = 0.006 * max(0.0, self._state.mean_tree_size - 36.0) / 36.0
            hv_gain = (
                base_gain
                + diversity_bonus
                - bloat_penalty
                + float(self._rng.normal(0.0, self.config.hv_noise))
            )
            hv_gain = max(-0.006, hv_gain)

            diversity_shift = (
                (0.18 * (control.mutation_rate - 0.12))
                - (0.10 * (control.crossover_rate - 0.75))
                - 0.018
                - (0.03 * progress)
                + float(self._rng.normal(0.0, self.config.diversity_noise))
            )
            diversity = min(max(self._state.diversity + diversity_shift, 0.05), 0.95)

            best_improvement = max(0.0, (0.8 * hv_gain) + float(self._rng.normal(0.0, 0.001)))
            best_fitness = max(0.0, self._state.best_fitness - best_improvement)

            tree_growth = (
                1.2
                + (4.5 * control.crossover_rate)
                - (2.2 * control.mutation_rate)
                + float(self._rng.normal(0.0, self.config.tree_noise))
            )
            mean_tree_size = max(2.0, self._state.mean_tree_size + tree_growth)

            stagnation = 0 if hv_gain > 0.004 else self._state.stagnation_generations + 1
            hypervolume = min(max(self._state.hypervolume + hv_gain, 0.0), 1.0)

            cumulative_hv_delta += hv_gain
            cumulative_best_improvement += best_improvement

            self._state = GPStateSnapshot(
                generation=self._state.generation + 1,
                total_generations=self._state.total_generations,
                hypervolume=hypervolume,
                recent_hv_delta=hv_gain,
                diversity=diversity,
                best_fitness=best_fitness,
                recent_best_improvement=best_improvement,
                stagnation_generations=stagnation,
                mean_tree_size=mean_tree_size,
            )

        self._state = GPStateSnapshot(
            generation=self._state.generation,
            total_generations=self._state.total_generations,
            hypervolume=self._state.hypervolume,
            recent_hv_delta=cumulative_hv_delta,
            diversity=self._state.diversity,
            best_fitness=self._state.best_fitness,
            recent_best_improvement=cumulative_best_improvement,
            stagnation_generations=self._state.stagnation_generations,
            mean_tree_size=self._state.mean_tree_size,
        )

        return IntervalResult(
            start_state=start_state,
            end_state=self.snapshot(),
            evaluations=steps * self.config.population_size,
        )

