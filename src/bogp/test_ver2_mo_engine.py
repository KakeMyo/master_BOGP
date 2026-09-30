from __future__ import annotations

import copy
from dataclasses import dataclass
from math import inf
from statistics import mean
from typing import Hashable, List, Sequence, Tuple

import numpy as np

from .diversity import population_structural_diversity
from .test_v1_hypervolume import dominates_minimized, hypervolume_2d_from_evaluated
from .test_v1_problem import EvaluatedIndividual, GPProblem, ObjectiveSpec
from .types import ControlInput, GPStateSnapshot, IntervalResult


@dataclass
class MultiObjectiveGPConfig:
    population_size: int = 50
    total_generations: int = 50
    tournament_size: int = 3
    random_seed: int = 7
    archive_size: int = 200
    hv_reference_point: tuple[float, float] = (1.0, 1.0)
    diversity_pair_sample_size: int | None = None
    objective_key_precision: int = 12


def _dominates(
    left: EvaluatedIndividual,
    right: EvaluatedIndividual,
    objectives: Sequence[ObjectiveSpec],
) -> bool:
    return dominates_minimized(
        left.dominance_values(objectives),
        right.dominance_values(objectives),
    )


def fast_non_dominated_sort(
    population: Sequence[EvaluatedIndividual],
    objectives: Sequence[ObjectiveSpec],
) -> List[List[EvaluatedIndividual]]:
    domination_counts = [0 for _ in population]
    dominated_sets: List[List[int]] = [[] for _ in population]
    fronts: List[List[int]] = [[]]

    for p_index, p_item in enumerate(population):
        for q_index, q_item in enumerate(population):
            if p_index == q_index:
                continue
            if _dominates(p_item, q_item, objectives):
                dominated_sets[p_index].append(q_index)
            elif _dominates(q_item, p_item, objectives):
                domination_counts[p_index] += 1
        if domination_counts[p_index] == 0:
            p_item.rank = 0
            fronts[0].append(p_index)

    current_rank = 0
    while fronts[current_rank]:
        next_front: List[int] = []
        for p_index in fronts[current_rank]:
            for q_index in dominated_sets[p_index]:
                domination_counts[q_index] -= 1
                if domination_counts[q_index] == 0:
                    population[q_index].rank = current_rank + 1
                    next_front.append(q_index)
        current_rank += 1
        fronts.append(next_front)

    return [[population[index] for index in front] for front in fronts if front]


def assign_crowding_distance(
    front: Sequence[EvaluatedIndividual],
    objectives: Sequence[ObjectiveSpec],
) -> None:
    if not front:
        return
    for item in front:
        item.crowding_distance = 0.0
    if len(front) <= 2:
        for item in front:
            item.crowding_distance = inf
        return

    for objective_index, objective in enumerate(objectives):
        ordered = sorted(
            front,
            key=lambda item: objective.dominance_value(item.objective_values[objective_index]),
        )
        ordered[0].crowding_distance = inf
        ordered[-1].crowding_distance = inf
        values = [
            objective.dominance_value(item.objective_values[objective_index])
            for item in ordered
        ]
        span = values[-1] - values[0]
        if span <= 0.0:
            continue
        for index in range(1, len(ordered) - 1):
            if ordered[index].crowding_distance == inf:
                continue
            ordered[index].crowding_distance += (values[index + 1] - values[index - 1]) / span


def assign_rank_and_crowding(
    population: Sequence[EvaluatedIndividual],
    objectives: Sequence[ObjectiveSpec],
) -> List[List[EvaluatedIndividual]]:
    fronts = fast_non_dominated_sort(population, objectives)
    for front in fronts:
        assign_crowding_distance(front, objectives)
    return fronts


def select_nsga2_survivors(
    population: Sequence[EvaluatedIndividual],
    objectives: Sequence[ObjectiveSpec],
    target_size: int,
) -> List[EvaluatedIndividual]:
    survivors: List[EvaluatedIndividual] = []
    fronts = assign_rank_and_crowding(population, objectives)
    for front in fronts:
        if len(survivors) + len(front) <= target_size:
            survivors.extend(front)
            continue
        ordered = sorted(front, key=lambda item: item.crowding_distance, reverse=True)
        survivors.extend(ordered[: target_size - len(survivors)])
        break
    return survivors


class MultiObjectiveGPEngine:
    """test_ver2 plant with objective-structure pair deduplication in archive."""

    def __init__(
        self,
        problem: GPProblem,
        config: MultiObjectiveGPConfig | None = None,
    ) -> None:
        self.problem = problem
        self.config = config or MultiObjectiveGPConfig()
        self._rng = np.random.default_rng(self.config.random_seed)
        self._generation = 0
        self._last_hv_delta = 0.0
        self._best_hypervolume = 0.0
        self._stagnation_generations = 0

        self._population = [
            self.problem.create_individual(self._rng)
            for _ in range(self.config.population_size)
        ]
        self._evaluated_population = self._evaluate_population(self._population)
        self._archive: List[EvaluatedIndividual] = []
        self._update_archive(self._evaluated_population)
        self._hypervolume = self._compute_hypervolume()
        self._best_hypervolume = self._hypervolume
        assign_rank_and_crowding(self._evaluated_population, self.problem.objectives)
        self._state_history: List[GPStateSnapshot] = [self.snapshot()]

    @property
    def evaluated_population(self) -> List[EvaluatedIndividual]:
        return list(self._evaluated_population)

    @property
    def archive(self) -> List[EvaluatedIndividual]:
        return list(self._archive)

    @property
    def unique_objective_archive(self) -> List[EvaluatedIndividual]:
        return self._unique_objective_representatives(self._archive)

    def archive_statistics(self) -> dict[str, int]:
        objective_keys = {self._objective_key(item) for item in self._archive}
        structure_keys = {self._structure_key(item) for item in self._archive}
        pair_keys = {self._archive_pair_key(item) for item in self._archive}
        return {
            "archive_size": len(self._archive),
            "archive_unique_objective_size": len(objective_keys),
            "archive_unique_structure_size": len(structure_keys),
            "archive_unique_pair_size": len(pair_keys),
        }

    @property
    def state_history(self) -> List[GPStateSnapshot]:
        return list(self._state_history)

    def snapshot(self) -> GPStateSnapshot:
        diversity = self._population_diversity()
        mean_size = mean(self.problem.tree_size(item.individual) for item in self._evaluated_population)
        return GPStateSnapshot(
            generation=self._generation,
            total_generations=self.config.total_generations,
            hypervolume=self._hypervolume,
            recent_hv_delta=self._last_hv_delta,
            diversity=diversity,
            best_fitness=1.0 - self._hypervolume,
            recent_best_improvement=max(0.0, self._last_hv_delta),
            stagnation_generations=self._stagnation_generations,
            mean_tree_size=float(mean_size),
        )

    def run_interval(
        self,
        control: ControlInput,
        interval_generations: int | None = None,
    ) -> IntervalResult:
        start_state = self.snapshot()
        requested_steps = interval_generations if interval_generations is not None else control.update_period
        requested_steps = max(1, int(requested_steps))
        remaining = self.config.total_generations - self._generation
        steps = min(requested_steps, remaining)

        start_hv = self._hypervolume
        diversity_values: List[float] = []
        evaluations = 0
        for _ in range(steps):
            evaluations += self._advance_one_generation(control)
            generation_state = self.snapshot()
            diversity_values.append(generation_state.diversity)
            self._state_history.append(generation_state)

        self._last_hv_delta = self._hypervolume - start_hv
        end_state = self.snapshot()
        return IntervalResult(
            start_state=start_state,
            end_state=end_state,
            evaluations=evaluations,
            diversity_values=tuple(diversity_values),
        )

    def _advance_one_generation(self, control: ControlInput) -> int:
        offspring: List[object] = []
        while len(offspring) < self.config.population_size:
            roll = float(self._rng.random())
            if roll < control.crossover_rate and len(offspring) <= self.config.population_size - 2:
                parent_a = self._select_parent()
                parent_b = self._select_parent()
                child_a, child_b = self.problem.crossover(parent_a, parent_b, self._rng)
                offspring.extend([child_a, child_b])
            elif roll < control.crossover_rate + control.mutation_rate:
                parent = copy.deepcopy(self._select_parent())
                offspring.append(self.problem.mutate(parent, self._rng))
            else:
                offspring.append(copy.deepcopy(self._select_parent()))

        offspring = offspring[: self.config.population_size]
        evaluated_offspring = self._evaluate_population(offspring)
        combined = self._evaluated_population + evaluated_offspring
        self._evaluated_population = select_nsga2_survivors(
            combined,
            self.problem.objectives,
            self.config.population_size,
        )
        self._population = [item.individual for item in self._evaluated_population]
        self._update_archive(self._evaluated_population)

        previous_hv = self._hypervolume
        self._hypervolume = self._compute_hypervolume()
        generation_delta = self._hypervolume - previous_hv
        if generation_delta > 1e-9:
            self._stagnation_generations = 0
        else:
            self._stagnation_generations += 1
        self._best_hypervolume = max(self._best_hypervolume, self._hypervolume)
        self._generation += 1
        return len(evaluated_offspring)

    def _select_parent(self):
        candidates = self._rng.choice(
            self._evaluated_population,
            size=min(self.config.tournament_size, len(self._evaluated_population)),
            replace=False,
        )
        best = sorted(
            candidates,
            key=lambda item: (item.rank, -item.crowding_distance),
        )[0]
        return copy.deepcopy(best.individual)

    def _evaluate_population(self, population: Sequence[object]) -> List[EvaluatedIndividual]:
        evaluated: List[EvaluatedIndividual] = []
        for individual in population:
            values = tuple(float(value) for value in self.problem.evaluate(individual))
            if len(values) != len(self.problem.objectives):
                raise ValueError("Problem returned an objective vector with an unexpected size.")
            evaluated.append(EvaluatedIndividual(individual=individual, objective_values=values))
        return evaluated

    def _update_archive(self, candidates: Sequence[EvaluatedIndividual]) -> None:
        combined = [
            EvaluatedIndividual(copy.deepcopy(item.individual), item.objective_values)
            for item in (self._archive + list(candidates))
        ]
        fronts = assign_rank_and_crowding(combined, self.problem.objectives)
        archive = fronts[0] if fronts else []
        archive = self._dedupe_objective_structure_pairs(archive)
        assign_rank_and_crowding(archive, self.problem.objectives)
        archive = sorted(archive, key=lambda item: item.crowding_distance, reverse=True)
        self._archive = archive[: self.config.archive_size]

    def _dedupe_objective_structure_pairs(
        self,
        items: Sequence[EvaluatedIndividual],
    ) -> List[EvaluatedIndividual]:
        seen: set[Tuple[Hashable, Hashable]] = set()
        unique: List[EvaluatedIndividual] = []
        for item in items:
            key = self._archive_pair_key(item)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _objective_key(self, item: EvaluatedIndividual) -> Tuple[float, ...]:
        precision = max(0, int(self.config.objective_key_precision))
        return tuple(round(float(value), precision) for value in item.objective_values)

    def _structure_key(self, item: EvaluatedIndividual) -> Tuple[Tuple[str, int], ...]:
        tokens = self.problem.structural_tokens(item.individual)
        return tuple(
            (
                str(getattr(token, "label", token)),
                int(getattr(token, "arity", 0)),
            )
            for token in tokens
        )

    def _archive_pair_key(
        self,
        item: EvaluatedIndividual,
    ) -> Tuple[Tuple[float, ...], Tuple[Tuple[str, int], ...]]:
        return (self._objective_key(item), self._structure_key(item))

    def _unique_objective_representatives(
        self,
        items: Sequence[EvaluatedIndividual],
    ) -> List[EvaluatedIndividual]:
        representatives: dict[Tuple[float, ...], EvaluatedIndividual] = {}
        for item in items:
            key = self._objective_key(item)
            if key not in representatives:
                representatives[key] = item
        return list(representatives.values())

    def _compute_hypervolume(self) -> float:
        if len(self.problem.objectives) != 2:
            return 0.0
        return hypervolume_2d_from_evaluated(
            self.unique_objective_archive,
            self.problem.objectives,
            reference_point=self.config.hv_reference_point,
        )

    def _population_diversity(self) -> float:
        tokens = [
            list(self.problem.structural_tokens(item.individual))
            for item in self._evaluated_population
        ]
        return population_structural_diversity(
            tokens,
            pair_sample_size=self.config.diversity_pair_sample_size,
        )
