from __future__ import annotations

from dataclasses import dataclass
from math import exp
from statistics import mean
from typing import Sequence

from .types import ControlInput, GPStateSnapshot


@dataclass(frozen=True)
class RewardConfig:
    hv_weight: float = 0.55
    diversity_weight: float = 0.35
    control_cost_weight: float = 0.05
    stagnation_weight: float = 0.00
    bloat_weight: float = 0.00
    hv_delta_scale: float = 0.01
    diversity_start: float = 0.60
    diversity_end: float = 0.20
    diversity_tolerance: float = 0.15
    diversity_floor: float = 0.10
    floor_penalty_weight: float = 0.25
    stagnation_scale: float = 12.0
    tree_growth_scale: float = 12.0
    min_update_period: int = 1
    max_update_period: int = 5


@dataclass(frozen=True)
class RewardBreakdown:
    total: float
    hv_term: float
    diversity_term: float
    control_cost: float
    stagnation_penalty: float
    bloat_penalty: float
    floor_penalty: float
    target_diversity: float


def clip(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def target_diversity(progress: float, config: RewardConfig) -> float:
    progress = clip(progress, 0.0, 1.0)
    return config.diversity_start - (
        (config.diversity_start - config.diversity_end) * progress
    )


def diversity_alignment_score(
    diversity: float,
    progress: float,
    config: RewardConfig,
) -> float:
    target = target_diversity(progress, config)
    error = abs(diversity - target)
    if config.diversity_tolerance <= 0.0:
        return 1.0 if error == 0.0 else 0.0
    return exp(-((error / config.diversity_tolerance) ** 2))


def compute_reward(
    start: GPStateSnapshot,
    end: GPStateSnapshot,
    config: RewardConfig = None,
    control: ControlInput | None = None,
    interval_diversities: Sequence[float] | None = None,
) -> RewardBreakdown:
    config = config or RewardConfig()

    interval_generations = max(1, end.generation - start.generation)
    hv_delta_rate = (end.hypervolume - start.hypervolume) / float(interval_generations)
    hv_term = clip(hv_delta_rate / max(config.hv_delta_scale, 1e-9), -1.0, 1.0)

    target = target_diversity(end.progress, config)
    diversity_value = (
        mean(interval_diversities)
        if interval_diversities is not None and len(interval_diversities) > 0
        else end.diversity
    )
    diversity_term = diversity_alignment_score(diversity_value, end.progress, config)

    control_cost = 0.0
    if control is not None:
        k_min = max(1, int(config.min_update_period))
        k_max = max(k_min + 1, int(config.max_update_period))
        k_value = min(max(int(control.update_period), k_min), k_max)
        control_cost = (k_max - k_value) / float(k_max - k_min)

    stagnation_penalty = clip(
        end.stagnation_generations / max(config.stagnation_scale, 1.0),
        0.0,
        1.0,
    )

    growth = max(0.0, end.mean_tree_size - start.mean_tree_size)
    bloat_penalty = clip(growth / max(config.tree_growth_scale, 1.0), 0.0, 1.0)

    floor_penalty = 0.0
    if diversity_value < config.diversity_floor:
        floor_penalty = clip(
            (config.diversity_floor - diversity_value) / max(config.diversity_floor, 1e-9),
            0.0,
            1.0,
        )

    total = (
        (config.hv_weight * hv_term)
        + (config.diversity_weight * diversity_term)
        - (config.control_cost_weight * control_cost)
        - (config.stagnation_weight * stagnation_penalty)
        - (config.bloat_weight * bloat_penalty)
        - (config.floor_penalty_weight * floor_penalty)
    )

    return RewardBreakdown(
        total=total,
        hv_term=hv_term,
        diversity_term=diversity_term,
        control_cost=control_cost,
        stagnation_penalty=stagnation_penalty,
        bloat_penalty=bloat_penalty,
        floor_penalty=floor_penalty,
        target_diversity=target,
    )
