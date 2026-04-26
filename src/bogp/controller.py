from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np
from scipy.stats import norm, qmc
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

from .types import ControlInput, GPStateSnapshot, RateBounds


@dataclass
class BOControllerConfig:
    bounds: RateBounds = field(default_factory=RateBounds)
    warmup_points: int = 8
    candidate_pool_size: int = 512
    control_interval: int = 3
    random_seed: int = 7
    exploration_jitter: float = 0.01
    smoothing_factor: float = 0.60
    hv_delta_scale: float = 0.03
    stagnation_scale: float = 15.0
    tree_size_scale: float = 100.0


class ContextualBayesianRateController:
    def __init__(self, config: BOControllerConfig = None) -> None:
        self.config = config or BOControllerConfig()
        self._rng = np.random.default_rng(self.config.random_seed)
        self._x_history: List[np.ndarray] = []
        self._y_history: List[float] = []
        self._previous_control: ControlInput = None
        self._warmup_design = self._build_warmup_design()

        input_dims = 8
        kernel = (
            ConstantKernel(1.0, (0.1, 10.0))
            * Matern(length_scale=np.ones(input_dims), length_scale_bounds=(1e-2, 10.0), nu=2.5)
            + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-6, 1e-1))
        )
        self._model = GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-6,
            normalize_y=True,
            n_restarts_optimizer=3,
            random_state=self.config.random_seed,
        )

    @property
    def observation_count(self) -> int:
        return len(self._y_history)

    def propose(self, context: GPStateSnapshot) -> ControlInput:
        if self.observation_count < self.config.warmup_points:
            raw = self._warmup_design[self.observation_count]
            proposal = ControlInput(crossover_rate=float(raw[0]), mutation_rate=float(raw[1]))
        else:
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
        features = self._joint_features(context, control)
        self._x_history.append(features)
        self._y_history.append(float(reward))
        self._previous_control = control

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
        return ControlInput(crossover_rate=crossover, mutation_rate=mutation)

    def _acquire(self, context: GPStateSnapshot) -> ControlInput:
        x_train = np.vstack(self._x_history)
        y_train = np.asarray(self._y_history, dtype=float)

        try:
            self._model.fit(x_train, y_train)
        except Exception:
            return self._fallback_random_control()

        candidates = self._sample_candidates(self.config.candidate_pool_size)
        context_vector = np.asarray(self._context_features(context), dtype=float)
        context_block = np.repeat(
            context_vector[np.newaxis, :],
            repeats=len(candidates),
            axis=0,
        )
        x_candidates = np.hstack((context_block, candidates))
        mean, std = self._model.predict(x_candidates, return_std=True)

        best_value = float(np.max(y_train))
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
        else:
            index = int(np.nanargmax(expected_improvement))

        return ControlInput(
            crossover_rate=float(candidates[index, 0]),
            mutation_rate=float(candidates[index, 1]),
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

    def _build_warmup_design(self) -> np.ndarray:
        target_size = max(self.config.warmup_points, 4)
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

    def _sample_candidates(self, size: int) -> np.ndarray:
        candidates: List[Sequence[float]] = []
        while len(candidates) < size:
            batch_size = max(size * 2, 16)
            raw = self._rng.random((batch_size, 2))
            crossover = self.config.bounds.crossover_min + (
                raw[:, 0] * (self.config.bounds.crossover_max - self.config.bounds.crossover_min)
            )
            mutation = self.config.bounds.mutation_min + (
                raw[:, 1] * (self.config.bounds.mutation_max - self.config.bounds.mutation_min)
            )
            batch = np.column_stack((crossover, mutation))
            batch = batch[np.sum(batch, axis=1) <= self.config.bounds.max_total_rate]
            for row in batch:
                candidates.append((float(row[0]), float(row[1])))
                if len(candidates) >= size:
                    break
        return np.asarray(candidates[:size], dtype=float)

    def _fallback_random_control(self) -> ControlInput:
        candidate = self._sample_candidates(1)[0]
        return ControlInput(crossover_rate=float(candidate[0]), mutation_rate=float(candidate[1]))
