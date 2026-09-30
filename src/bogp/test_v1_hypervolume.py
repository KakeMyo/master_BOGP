from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .test_v1_problem import EvaluatedIndividual, ObjectiveSpec


def dominates_minimized(left: Sequence[float], right: Sequence[float]) -> bool:
    """Return True when left Pareto-dominates right in minimization space."""

    if len(left) != len(right):
        raise ValueError("points must have the same dimension.")
    return all(a <= b for a, b in zip(left, right)) and any(
        a < b for a, b in zip(left, right)
    )


def non_dominated_indices(points: Sequence[Sequence[float]]) -> List[int]:
    indices: List[int] = []
    for i, point in enumerate(points):
        dominated = False
        for j, other in enumerate(points):
            if i == j:
                continue
            if dominates_minimized(other, point):
                dominated = True
                break
        if not dominated:
            indices.append(i)
    return indices


def normalized_minimized_points(
    evaluated: Iterable[EvaluatedIndividual],
    objectives: Sequence[ObjectiveSpec],
) -> List[Tuple[float, ...]]:
    return [item.normalized_values(objectives) for item in evaluated]


def hypervolume_2d_minimized(
    points: Iterable[Sequence[float]],
    reference_point: Tuple[float, float] = (1.0, 1.0),
) -> float:
    """Exact dominated hypervolume for two normalized minimization objectives."""

    valid_points = [
        (float(point[0]), float(point[1]))
        for point in points
        if len(point) == 2
        and point[0] < reference_point[0]
        and point[1] < reference_point[1]
    ]
    if not valid_points:
        return 0.0

    front = [valid_points[i] for i in non_dominated_indices(valid_points)]
    front.sort(key=lambda item: item[0])

    area = 0.0
    previous_y = float(reference_point[1])
    reference_x = float(reference_point[0])
    for x_value, y_value in front:
        if y_value >= previous_y:
            continue
        width = max(0.0, reference_x - x_value)
        height = max(0.0, previous_y - y_value)
        area += width * height
        previous_y = y_value
    return max(0.0, area)


def hypervolume_2d_from_evaluated(
    evaluated: Iterable[EvaluatedIndividual],
    objectives: Sequence[ObjectiveSpec],
    reference_point: Tuple[float, float] = (1.0, 1.0),
) -> float:
    if len(objectives) != 2:
        raise NotImplementedError("V1 supports exact hypervolume for two objectives only.")
    points = normalized_minimized_points(evaluated, objectives)
    return hypervolume_2d_minimized(points, reference_point=reference_point)
