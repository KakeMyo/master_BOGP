from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Protocol, Sequence, Tuple


@dataclass(frozen=True)
class ObjectiveSpec:
    """Definition of one Pareto objective.

    The GP engine treats all objectives as Pareto objectives, not as a
    weighted scalar. Bounds are used only for normalized hypervolume.
    """

    name: str
    direction: str = "minimize"
    lower: Optional[float] = None
    upper: Optional[float] = None

    def __post_init__(self) -> None:
        if self.direction not in {"minimize", "maximize"}:
            raise ValueError("direction must be 'minimize' or 'maximize'.")
        if self.lower is not None and self.upper is not None and self.upper <= self.lower:
            raise ValueError("upper must be greater than lower when both bounds are set.")

    def dominance_value(self, value: float) -> float:
        """Return a value where smaller is better."""

        if self.direction == "maximize":
            return -float(value)
        return float(value)

    def normalized_minimized_value(self, value: float) -> float:
        """Normalize to [0, 1] where smaller is better.

        If bounds are not provided, the oriented raw value is returned. The
        initial template uses bounds so that exact 2-D HV has a stable scale.
        """

        value = float(value)
        if self.lower is None or self.upper is None:
            return self.dominance_value(value)

        span = self.upper - self.lower
        if self.direction == "maximize":
            normalized = (self.upper - value) / span
        else:
            normalized = (value - self.lower) / span
        return min(max(normalized, 0.0), 1.0)


@dataclass
class EvaluatedIndividual:
    individual: Any
    objective_values: Tuple[float, ...]
    rank: int = 0
    crowding_distance: float = 0.0

    def dominance_values(self, objectives: Sequence[ObjectiveSpec]) -> Tuple[float, ...]:
        if len(self.objective_values) != len(objectives):
            raise ValueError("objective value count does not match ObjectiveSpec count.")
        return tuple(
            spec.dominance_value(value)
            for spec, value in zip(objectives, self.objective_values)
        )

    def normalized_values(self, objectives: Sequence[ObjectiveSpec]) -> Tuple[float, ...]:
        if len(self.objective_values) != len(objectives):
            raise ValueError("objective value count does not match ObjectiveSpec count.")
        return tuple(
            spec.normalized_minimized_value(value)
            for spec, value in zip(objectives, self.objective_values)
        )


class GPProblem(Protocol):
    """Problem adapter used by the generic multi-objective GP engine."""

    objectives: Sequence[ObjectiveSpec]

    def create_individual(self, rng) -> Any:
        ...

    def evaluate(self, individual: Any) -> Sequence[float]:
        ...

    def crossover(self, parent_a: Any, parent_b: Any, rng) -> Tuple[Any, Any]:
        ...

    def mutate(self, individual: Any, rng) -> Any:
        ...

    def tree_size(self, individual: Any) -> int:
        ...

    def structural_tokens(self, individual: Any) -> Iterable[object]:
        ...
