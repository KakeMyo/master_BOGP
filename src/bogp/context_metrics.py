from __future__ import annotations

from dataclasses import dataclass
from typing import List


def clip(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


@dataclass(frozen=True)
class ContextMetricConfig:
    """Normalization parameters for the contextual BO input vector."""

    hypervolume_min: float = 0.0
    hypervolume_max: float = 1.0
    hv_delta_scale: float = 0.03
    stagnation_scale: float = 15.0
    tree_size_scale: float = 100.0


def normalize_progress(generation: int, total_generations: int) -> float:
    if total_generations <= 0:
        return 0.0
    return clip(generation / float(total_generations), 0.0, 1.0)


def normalize_hypervolume(value: float, config: ContextMetricConfig) -> float:
    span = config.hypervolume_max - config.hypervolume_min
    if span <= 0.0:
        return 0.0
    return clip((value - config.hypervolume_min) / span, 0.0, 1.0)


def normalize_hv_delta(value: float, config: ContextMetricConfig) -> float:
    scale = max(config.hv_delta_scale, 1e-9)
    return clip(value / scale, -1.0, 1.0)


def normalize_stagnation(value: int, config: ContextMetricConfig) -> float:
    scale = max(config.stagnation_scale, 1.0)
    return clip(value / scale, 0.0, 1.0)


def normalize_tree_size(value: float, config: ContextMetricConfig) -> float:
    scale = max(config.tree_size_scale, 1.0)
    return clip(value / scale, 0.0, 1.0)


def build_context_vector(
    generation: int,
    total_generations: int,
    hypervolume: float,
    recent_hv_delta: float,
    diversity: float,
    stagnation_generations: int,
    mean_tree_size: float,
    config: ContextMetricConfig | None = None,
) -> List[float]:
    config = config or ContextMetricConfig()
    return [
        normalize_progress(generation, total_generations),
        normalize_hypervolume(hypervolume, config),
        normalize_hv_delta(recent_hv_delta, config),
        clip(diversity, 0.0, 1.0),
        normalize_stagnation(stagnation_generations, config),
        normalize_tree_size(mean_tree_size, config),
    ]
