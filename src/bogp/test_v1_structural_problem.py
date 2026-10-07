from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from scipy import signal

from .diversity import TreeNodeToken
from .test_v1_problem import ObjectiveSpec


@dataclass(frozen=True)
class StructuralNode:
    kind: str
    value: float | None = None
    children: Tuple["StructuralNode", ...] = ()


def _trim(poly: np.ndarray) -> np.ndarray:
    trimmed = np.trim_zeros(np.asarray(poly, dtype=float), "f")
    if len(trimmed) == 0:
        return np.asarray([0.0])
    return trimmed


def _poly_add(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return _trim(np.polyadd(left, right))


def _poly_mul(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return _trim(np.polymul(left, right))


def _paths(node: StructuralNode, prefix: Tuple[int, ...] = ()) -> List[Tuple[int, ...]]:
    paths = [prefix]
    for index, child in enumerate(node.children):
        paths.extend(_paths(child, prefix + (index,)))
    return paths


def _get_subtree(node: StructuralNode, path: Sequence[int]) -> StructuralNode:
    current = node
    for index in path:
        current = current.children[index]
    return current


def _replace_subtree(
    node: StructuralNode,
    path: Sequence[int],
    subtree: StructuralNode,
) -> StructuralNode:
    if not path:
        return subtree
    index = path[0]
    children = list(node.children)
    children[index] = _replace_subtree(children[index], path[1:], subtree)
    return StructuralNode(node.kind, node.value, tuple(children))


class StructuralSearchProblem:
    """Structural GP problem adapted from the supplied MATLAB source.

    Objectives are minimized internally:
    1. number of spring/damper terminal elements
    2. integral of the absolute impulse response
    """

    objectives = (
        ObjectiveSpec("terminal_elements", "minimize", lower=1.0, upper=32.0),
        ObjectiveSpec("impulse_integral", "minimize", lower=0.0, upper=10.0),
    )

    def __init__(
        self,
        mass: float = 130.0,
        max_initial_depth: int = 4,
        max_mutation_depth: int = 2,
        time_horizon: float = 100.0,
        time_steps: int = 1001,
    ) -> None:
        self.mass = mass
        self.max_initial_depth = max_initial_depth
        self.max_mutation_depth = max_mutation_depth
        self.time_values = np.linspace(0.0, time_horizon, time_steps)

    def create_individual(self, rng) -> StructuralNode:
        return self._random_substructure(rng, self.max_initial_depth)

    def evaluate(self, individual: StructuralNode) -> Sequence[float]:
        terminal_count = float(self._terminal_count(individual))
        impulse_integral = self._impulse_integral(individual)
        return (terminal_count, impulse_integral)

    def crossover(
        self,
        parent_a: StructuralNode,
        parent_b: StructuralNode,
        rng,
    ) -> Tuple[StructuralNode, StructuralNode]:
        paths_a = _paths(parent_a)
        paths_b = _paths(parent_b)
        path_a = paths_a[int(rng.integers(0, len(paths_a)))]
        path_b = paths_b[int(rng.integers(0, len(paths_b)))]
        subtree_a = _get_subtree(parent_a, path_a)
        subtree_b = _get_subtree(parent_b, path_b)
        return (
            _replace_subtree(parent_a, path_a, subtree_b),
            _replace_subtree(parent_b, path_b, subtree_a),
        )

    def mutate(self, individual: StructuralNode, rng) -> StructuralNode:
        paths = _paths(individual)
        path = paths[int(rng.integers(0, len(paths)))]
        replacement = self._random_substructure(rng, self.max_mutation_depth)
        return _replace_subtree(individual, path, replacement)

    def tree_size(self, individual: StructuralNode) -> int:
        return 1 + sum(self.tree_size(child) for child in individual.children)

    def structural_tokens(self, individual: StructuralNode) -> Iterable[TreeNodeToken]:
        return [TreeNodeToken("mass", 1)] + self._prefix_tokens(individual)

    def _random_substructure(self, rng, depth: int) -> StructuralNode:
        if depth <= 0 or float(rng.random()) < 0.35:
            if float(rng.random()) < 0.5:
                return StructuralNode("spring", value=float(rng.integers(500, 2501)))
            return StructuralNode("damper", value=float(rng.integers(50, 501)))

        kind = str(rng.choice(["series", "parallel"]))
        return StructuralNode(
            kind,
            children=(
                self._random_substructure(rng, depth - 1),
                self._random_substructure(rng, depth - 1),
            ),
        )

    def _terminal_count(self, node: StructuralNode) -> int:
        if node.kind in {"spring", "damper"}:
            return 1
        return sum(self._terminal_count(child) for child in node.children)

    def _equivalent_stiffness(self, node: StructuralNode) -> Tuple[np.ndarray, np.ndarray]:
        if node.kind == "spring":
            return (np.asarray([float(node.value or 0.0)]), np.asarray([1.0]))
        if node.kind == "damper":
            return (np.asarray([float(node.value or 0.0), 0.0]), np.asarray([1.0]))
        if node.kind == "parallel":
            numerator = np.asarray([0.0])
            denominator = np.asarray([1.0])
            for child in node.children:
                child_num, child_den = self._equivalent_stiffness(child)
                numerator = _poly_add(_poly_mul(numerator, child_den), _poly_mul(child_num, denominator))
                denominator = _poly_mul(denominator, child_den)
            return (_trim(numerator), _trim(denominator))
        if node.kind == "series":
            numerator_product = np.asarray([1.0])
            compliance_sum = np.asarray([0.0])
            child_terms = [self._equivalent_stiffness(child) for child in node.children]
            for child_num, _ in child_terms:
                numerator_product = _poly_mul(numerator_product, child_num)
            for index, (child_num, child_den) in enumerate(child_terms):
                other_product = np.asarray([1.0])
                for other_index, (other_num, _) in enumerate(child_terms):
                    if other_index != index:
                        other_product = _poly_mul(other_product, other_num)
                compliance_sum = _poly_add(compliance_sum, _poly_mul(child_den, other_product))
            return (_trim(numerator_product), _trim(compliance_sum))
        raise ValueError(f"Unknown structural node kind: {node.kind}")

    def _transfer_function(self, node: StructuralNode) -> signal.TransferFunction:
        stiffness_num, stiffness_den = self._equivalent_stiffness(node)
        mass_term = _poly_mul(np.asarray([self.mass, 0.0, 0.0]), stiffness_den)
        denominator = _poly_add(mass_term, stiffness_num)
        numerator = stiffness_den
        if len(denominator) == 0 or np.allclose(denominator, 0.0):
            raise ValueError("Invalid zero denominator.")
        return signal.TransferFunction(_trim(numerator), _trim(denominator))

    def _impulse_integral(self, node: StructuralNode) -> float:
        try:
            system = self._transfer_function(node)
            _, response = signal.impulse(system, T=self.time_values)
            if not np.all(np.isfinite(response)):
                return 10.0
            return float(np.trapz(np.abs(response), self.time_values))
        except Exception:
            return 10.0

    def _prefix_tokens(self, node: StructuralNode) -> List[TreeNodeToken]:
        tokens = [TreeNodeToken(label=node.kind, arity=len(node.children))]
        for child in node.children:
            tokens.extend(self._prefix_tokens(child))
        return tokens
