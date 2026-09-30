from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.stats import norm, qmc
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

from .types import ControlInput, GPStateSnapshot, RateBounds


@dataclass
class BOControllerConfig:
    bounds: RateBounds = field(default_factory=RateBounds)
    candidate_k_values: Tuple[int, ...] = (1, 3, 5)
    warmup_strategy: str = "sequential"
    ei_best_scope: str = "per_k"
    warmup_per_k: int = 2
    min_observations_per_k: int = 2
    candidate_pool_size_per_k: int = 128
    warmup_points: int = 0
    candidate_pool_size: int = 0
    random_seed: int = 7
    exploration_jitter: float = 0.01
    smoothing_factor: float = 0.60
    hv_delta_scale: float = 0.03
    stagnation_scale: float = 15.0
    tree_size_scale: float = 100.0

    def __post_init__(self) -> None:
        k_values = {1}
        k_values.update(max(1, int(k)) for k in self.candidate_k_values)
        self.candidate_k_values = tuple(sorted(k_values))
        if not self.candidate_k_values:
            raise ValueError("candidate_k_values must contain at least one update period.")
        if self.warmup_strategy not in {"sequential", "interleaved"}:
            raise ValueError("warmup_strategy must be 'sequential' or 'interleaved'.")
        if self.ei_best_scope not in {"per_k", "global"}:
            raise ValueError("ei_best_scope must be 'per_k' or 'global'.")
        if self.warmup_points > 0:
            per_k = int(np.ceil(self.warmup_points / len(self.candidate_k_values)))
            self.warmup_per_k = max(self.warmup_per_k, per_k)
        if self.candidate_pool_size > 0:
            per_k = int(np.ceil(self.candidate_pool_size / len(self.candidate_k_values)))
            self.candidate_pool_size_per_k = max(self.candidate_pool_size_per_k, per_k)


class ContextualBayesianRateController:
    def __init__(self, config: BOControllerConfig = None) -> None:
        self.config = config or BOControllerConfig()
        self._rng = np.random.default_rng(self.config.random_seed)
        self._x_history_by_k: Dict[int, List[np.ndarray]] = {
            k: [] for k in self.config.candidate_k_values
        }
        self._y_history_by_k: Dict[int, List[float]] = {
            k: [] for k in self.config.candidate_k_values
        }
        self._previous_control: ControlInput = None
        self._warmup_design_by_k = {
            k: self._build_warmup_design(self.config.warmup_per_k)
            for k in self.config.candidate_k_values
        }
        self._warmup_index_by_k = {k: 0 for k in self.config.candidate_k_values}
        self._warmup_cycle_position = 0

        input_dims = 8
        kernel = (
            ConstantKernel(1.0, (0.1, 10.0))
            * Matern(length_scale=np.ones(input_dims), length_scale_bounds=(1e-2, 10.0), nu=2.5)
            + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-6, 1e-1))
        )
        self._kernel = kernel
        self._models: Dict[int, GaussianProcessRegressor] = {}

    @property
    def observation_count(self) -> int:
        return sum(len(values) for values in self._y_history_by_k.values())

    def propose(self, context: GPStateSnapshot) -> ControlInput:
        proposal = self._next_warmup_control(context)
        if proposal is None:
            proposal = self._acquire(context)

        proposal = self._smooth(proposal)
        proposal = self.config.bounds.clamp(proposal, previous=self._previous_control)
        return proposal

    def register_observation(
        self,
        context: GPStateSnapshot,
        control: ControlInput,
        reward: float,
    ) -> None:
        k_value = self._nearest_configured_k(control.update_period)
        features = self._joint_features(context, control)
        self._x_history_by_k.setdefault(k_value, []).append(features)
        self._y_history_by_k.setdefault(k_value, []).append(float(reward))
        self._previous_control = ControlInput(
            crossover_rate=control.crossover_rate,
            mutation_rate=control.mutation_rate,
            update_period=k_value,
        )

    def _smooth(self, proposal: ControlInput) -> ControlInput:
        if self._previous_control is None:
            return proposal

        factor = min(max(self.config.smoothing_factor, 0.0), 1.0)
        crossover = self._previous_control.crossover_rate + (
            factor * (proposal.crossover_rate - self._previous_control.crossover_rate)
        )
        mutation = self._previous_control.mutation_rate + (
            factor * (proposal.mutation_rate - self._previous_control.mutation_rate)
        )
        return ControlInput(
            crossover_rate=crossover,
            mutation_rate=mutation,
            update_period=proposal.update_period,
        )

    def _acquire(self, context: GPStateSnapshot) -> ControlInput:
        best_control: ControlInput | None = None
        best_ei = -np.inf
        valid_k_values = self._valid_k_values(context)
        context_vector = np.asarray(self._context_features(context), dtype=float)

        for k_value in valid_k_values:
            x_history = self._x_history_by_k.get(k_value, [])
            y_history = self._y_history_by_k.get(k_value, [])
            if len(y_history) < self.config.min_observations_per_k:
                return self._fallback_random_control(context, forced_k=k_value)

            x_train = np.vstack(x_history)
            y_train = np.asarray(y_history, dtype=float)
            model = self._model_for_k(k_value)
            try:
                model.fit(x_train, y_train)
            except Exception:
                continue

            candidates = self._sample_candidates(
                self.config.candidate_pool_size_per_k,
                previous=self._previous_control,
            )
            context_block = np.repeat(
                context_vector[np.newaxis, :],
                repeats=len(candidates),
                axis=0,
            )
            x_candidates = np.hstack((context_block, candidates))
            mean, std = model.predict(x_candidates, return_std=True)

            best_value = self._ei_best_value(y_train)
            improvement = mean - best_value - self.config.exploration_jitter
            with np.errstate(divide="ignore", invalid="ignore"):
                z_value = np.divide(
                    improvement,
                    std,
                    out=np.zeros_like(improvement),
                    where=std > 1e-12,
                )
            expected_improvement = (improvement * norm.cdf(z_value)) + (std * norm.pdf(z_value))
            expected_improvement = np.where(std > 1e-12, expected_improvement, 0.0)

            if not np.isfinite(expected_improvement).any():
                index = int(np.argmax(mean))
                score = float(mean[index])
            else:
                index = int(np.nanargmax(expected_improvement))
                score = float(expected_improvement[index])

            if score > best_ei:
                best_ei = score
                best_control = ControlInput(
                    crossover_rate=float(candidates[index, 0]),
                    mutation_rate=float(candidates[index, 1]),
                    update_period=k_value,
                )

        if best_control is None:
            return self._fallback_random_control(context)
        return best_control

    def _next_warmup_control(self, context: GPStateSnapshot) -> ControlInput | None:
        if self.config.warmup_strategy == "interleaved":
            return self._next_interleaved_warmup_control(context)

        for k_value in self._valid_k_values(context):
            if len(self._y_history_by_k.get(k_value, [])) >= self.config.warmup_per_k:
                continue
            return self._warmup_control_for_k(k_value)
        return None

    def _next_interleaved_warmup_control(
        self,
        context: GPStateSnapshot,
    ) -> ControlInput | None:
        valid_k_values = set(self._valid_k_values(context))
        if not valid_k_values:
            return None

        configured = self.config.candidate_k_values
        for _ in range(len(configured)):
            k_value = configured[self._warmup_cycle_position % len(configured)]
            self._warmup_cycle_position += 1
            if k_value not in valid_k_values:
                continue
            if len(self._y_history_by_k.get(k_value, [])) < self.config.warmup_per_k:
                return self._warmup_control_for_k(k_value)

        # Near the final generations, some larger k values may be invalid. Fall
        # back to any still-valid k that has not completed warm-up.
        for k_value in self._valid_k_values(context):
            if len(self._y_history_by_k.get(k_value, [])) < self.config.warmup_per_k:
                return self._warmup_control_for_k(k_value)
        return None

    def _warmup_control_for_k(self, k_value: int) -> ControlInput:
        design = self._warmup_design_by_k[k_value]
        index = self._warmup_index_by_k[k_value] % len(design)
        self._warmup_index_by_k[k_value] += 1
        return ControlInput(
            crossover_rate=float(design[index, 0]),
            mutation_rate=float(design[index, 1]),
            update_period=k_value,
        )

    def _joint_features(
        self,
        context: GPStateSnapshot,
        control: ControlInput,
    ) -> np.ndarray:
        return np.asarray(
            self._context_features(context) + [control.crossover_rate, control.mutation_rate],
            dtype=float,
        )

    def _context_features(self, context: GPStateSnapshot) -> List[float]:
        return context.feature_vector(
            hv_delta_scale=self.config.hv_delta_scale,
            stagnation_scale=self.config.stagnation_scale,
            tree_size_scale=self.config.tree_size_scale,
        )

    def _ei_best_value(self, y_train_for_k: np.ndarray) -> float:
        if self.config.ei_best_scope == "per_k":
            return float(np.max(y_train_for_k))

        all_values = [
            float(value)
            for history in self._y_history_by_k.values()
            for value in history
        ]
        if not all_values:
            return float(np.max(y_train_for_k))
        return float(np.max(all_values))

    def _build_warmup_design(self, design_size: int) -> np.ndarray:
        target_size = max(design_size, 1)
        sample_size = target_size * 4
        sampler = qmc.LatinHypercube(d=2, seed=int(self._rng.integers(0, 2**31 - 1)))
        raw = sampler.random(n=sample_size)
        scaled = qmc.scale(
            raw,
            [self.config.bounds.crossover_min, self.config.bounds.mutation_min],
            [self.config.bounds.crossover_max, self.config.bounds.mutation_max],
        )
        valid = scaled[np.sum(scaled, axis=1) <= self.config.bounds.max_total_rate]
        if len(valid) >= target_size:
            return valid[:target_size]

        needed = target_size - len(valid)
        fallback = self._sample_candidates(max(needed, target_size))
        if len(valid) == 0:
            return fallback[:target_size]
        return np.vstack((valid, fallback[:needed]))

    def _sample_candidates(
        self,
        size: int,
        previous: ControlInput | None = None,
    ) -> np.ndarray:
        candidates: List[Sequence[float]] = []
        while len(candidates) < size:
            batch_size = max(size * 2, 16)
            if previous is None:
                crossover_min = self.config.bounds.crossover_min
                crossover_max = self.config.bounds.crossover_max
                mutation_min = self.config.bounds.mutation_min
                mutation_max = self.config.bounds.mutation_max
            else:
                crossover_min = max(
                    self.config.bounds.crossover_min,
                    previous.crossover_rate - self.config.bounds.max_step,
                )
                crossover_max = min(
                    self.config.bounds.crossover_max,
                    previous.crossover_rate + self.config.bounds.max_step,
                )
                mutation_min = max(
                    self.config.bounds.mutation_min,
                    previous.mutation_rate - self.config.bounds.max_step,
                )
                mutation_max = min(
                    self.config.bounds.mutation_max,
                    previous.mutation_rate + self.config.bounds.max_step,
                )
            raw = self._rng.random((batch_size, 2))
            crossover = crossover_min + (raw[:, 0] * (crossover_max - crossover_min))
            mutation = mutation_min + (raw[:, 1] * (mutation_max - mutation_min))
            batch = np.column_stack((crossover, mutation))
            batch = batch[np.sum(batch, axis=1) <= self.config.bounds.max_total_rate]
            for row in batch:
                candidates.append((float(row[0]), float(row[1])))
                if len(candidates) >= size:
                    break
        return np.asarray(candidates[:size], dtype=float)

    def _fallback_random_control(
        self,
        context: GPStateSnapshot | None = None,
        forced_k: int | None = None,
    ) -> ControlInput:
        candidate = self._sample_candidates(1, previous=self._previous_control)[0]
        k_value = forced_k
        if k_value is None:
            valid_k_values = self._valid_k_values(context)
            k_value = int(self._rng.choice(valid_k_values))
        return ControlInput(
            crossover_rate=float(candidate[0]),
            mutation_rate=float(candidate[1]),
            update_period=int(k_value),
        )

    def _valid_k_values(self, context: GPStateSnapshot | None) -> Tuple[int, ...]:
        if context is None:
            return self.config.candidate_k_values
        remaining = max(1, context.total_generations - context.generation)
        valid = tuple(k for k in self.config.candidate_k_values if k <= remaining)
        if valid:
            return valid
        return (min(self.config.candidate_k_values),)

    def _nearest_configured_k(self, update_period: int) -> int:
        return min(
            self.config.candidate_k_values,
            key=lambda k_value: abs(k_value - int(update_period)),
        )

    def _model_for_k(self, k_value: int) -> GaussianProcessRegressor:
        if k_value not in self._models:
            self._models[k_value] = GaussianProcessRegressor(
                kernel=self._kernel,
                alpha=1e-6,
                normalize_y=True,
                n_restarts_optimizer=3,
                random_state=self.config.random_seed + int(k_value),
            )
        return self._models[k_value]
