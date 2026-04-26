from __future__ import annotations

from dataclasses import dataclass
from math import exp

from .types import GPStateSnapshot


@dataclass(frozen=True)
class RewardConfig:
    hv_weight: float = 0.55
    diversity_weight: float = 0.25
    stagnation_weight: float = 0.10
    bloat_weight: float = 0.10
    hv_delta_scale: float = 0.03
    diversity_start: float = 0.60
    diversity_end: float = 0.20
    diversity_tolerance: float = 0.15
    diversity_floor: float = 0.10
    floor_penalty_weight: float = 0.25
    stagnation_scale: float = 12.0
    tree_growth_scale: float = 12.0


@dataclass(frozen=True)
class RewardBreakdown:
    total: float
    hv_term: float
    diversity_term: float
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
) -> RewardBreakdown:
    config = config or RewardConfig()

    hv_delta = end.hypervolume - start.hypervolume
    hv_term = clip(hv_delta / max(config.hv_delta_scale, 1e-9), -1.0, 1.0)

    target = target_diversity(end.progress, config)
    diversity_term = diversity_alignment_score(end.diversity, end.progress, config)

    stagnation_penalty = clip(
        end.stagnation_generations / max(config.stagnation_scale, 1.0),
        0.0,
        1.0,
    )

    growth = max(0.0, end.mean_tree_size - start.mean_tree_size)
    bloat_penalty = clip(growth / max(config.tree_growth_scale, 1.0), 0.0, 1.0)

    floor_penalty = 0.0
    if end.diversity < config.diversity_floor:
        floor_penalty = clip(
            (config.diversity_floor - end.diversity) / max(config.diversity_floor, 1e-9),
            0.0,
            1.0,
        )

    total = (
        (config.hv_weight * hv_term)
        + (config.diversity_weight * diversity_term)
        - (config.stagnation_weight * stagnation_penalty)
        - (config.bloat_weight * bloat_penalty)
        - (config.floor_penalty_weight * floor_penalty)
    )

    return RewardBreakdown(
        total=total,
        hv_term=hv_term,
        diversity_term=diversity_term,
        stagnation_penalty=stagnation_penalty,
        bloat_penalty=bloat_penalty,
        floor_penalty=floor_penalty,
        target_diversity=target,
    )

