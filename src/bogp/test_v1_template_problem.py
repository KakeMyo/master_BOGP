from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np

from .diversity import TreeNodeToken
from .test_v1_problem import ObjectiveSpec


@dataclass(frozen=True)
class ExpressionNode:
    op: str
    value: float | None = None
    children: Tuple["ExpressionNode", ...] = ()


def _node_size(node: ExpressionNode) -> int:
    return 1 + sum(_node_size(child) for child in node.children)


def _paths(node: ExpressionNode, prefix: Tuple[int, ...] = ()) -> List[Tuple[int, ...]]:
    paths = [prefix]
    for index, child in enumerate(node.children):
        paths.extend(_paths(child, prefix + (index,)))
    return paths


def _get_subtree(node: ExpressionNode, path: Sequence[int]) -> ExpressionNode:
    current = node
    for index in path:
        current = current.children[index]
    return current


def _replace_subtree(
    node: ExpressionNode,
    path: Sequence[int],
    subtree: ExpressionNode,
) -> ExpressionNode:
    if not path:
        return subtree
    index = path[0]
    children = list(node.children)
    children[index] = _replace_subtree(children[index], path[1:], subtree)
    return ExpressionNode(op=node.op, value=node.value, children=tuple(children))


class TemplateSymbolicRegressionProblem:
    """Small two-objective GP problem used to validate the generic template."""

    objectives = (
        ObjectiveSpec("mse", "minimize", lower=0.0, upper=5.0),
        ObjectiveSpec("tree_size", "minimize", lower=1.0, upper=50.0),
    )

    def __init__(
        self,
        max_initial_depth: int = 4,
        max_mutation_depth: int = 2,
        sample_count: int = 41,
    ) -> None:
        self.max_initial_depth = max_initial_depth
        self.max_mutation_depth = max_mutation_depth
        self.x_values = np.linspace(-1.0, 1.0, sample_count)
        self.y_target = (self.x_values * self.x_values) + self.x_values

    def create_individual(self, rng) -> ExpressionNode:
        return self._random_tree(rng, self.max_initial_depth)

    def evaluate(self, individual: ExpressionNode) -> Sequence[float]:
        predictions = self._evaluate_node(individual, self.x_values)
        if not np.all(np.isfinite(predictions)):
            mse = 5.0
        else:
            clipped = np.clip(predictions, -10.0, 10.0)
            mse = float(np.mean((clipped - self.y_target) ** 2))
        return (mse, float(self.tree_size(individual)))

    def crossover(
        self,
        parent_a: ExpressionNode,
        parent_b: ExpressionNode,
        rng,
    ) -> Tuple[ExpressionNode, ExpressionNode]:
        path_a = _paths(parent_a)[int(rng.integers(0, len(_paths(parent_a))))]
        path_b = _paths(parent_b)[int(rng.integers(0, len(_paths(parent_b))))]
        subtree_a = _get_subtree(parent_a, path_a)
        subtree_b = _get_subtree(parent_b, path_b)
        return (
            _replace_subtree(parent_a, path_a, subtree_b),
            _replace_subtree(parent_b, path_b, subtree_a),
        )

    def mutate(self, individual: ExpressionNode, rng) -> ExpressionNode:
        paths = _paths(individual)
        path = paths[int(rng.integers(0, len(paths)))]
        replacement = self._random_tree(rng, self.max_mutation_depth)
        return _replace_subtree(individual, path, replacement)

    def tree_size(self, individual: ExpressionNode) -> int:
        return _node_size(individual)

    def structural_tokens(self, individual: ExpressionNode) -> Iterable[TreeNodeToken]:
        return self._prefix_tokens(individual)

    def _random_tree(self, rng, depth: int) -> ExpressionNode:
        if depth <= 0 or float(rng.random()) < 0.25:
            if float(rng.random()) < 0.5:
                return ExpressionNode("x")
            return ExpressionNode("const", value=float(rng.uniform(-2.0, 2.0)))

        op = str(rng.choice(["add", "sub", "mul", "sin"]))
        if op == "sin":
            return ExpressionNode(op, children=(self._random_tree(rng, depth - 1),))
        return ExpressionNode(
            op,
            children=(
                self._random_tree(rng, depth - 1),
                self._random_tree(rng, depth - 1),
            ),
        )

    def _evaluate_node(self, node: ExpressionNode, x_values: np.ndarray) -> np.ndarray:
        if node.op == "x":
            return x_values
        if node.op == "const":
            return np.full_like(x_values, float(node.value or 0.0), dtype=float)
        if node.op == "add":
            return self._evaluate_node(node.children[0], x_values) + self._evaluate_node(
                node.children[1], x_values
            )
        if node.op == "sub":
            return self._evaluate_node(node.children[0], x_values) - self._evaluate_node(
                node.children[1], x_values
            )
        if node.op == "mul":
            return self._evaluate_node(node.children[0], x_values) * self._evaluate_node(
                node.children[1], x_values
            )
        if node.op == "sin":
            return np.sin(self._evaluate_node(node.children[0], x_values))
        raise ValueError(f"Unknown expression node: {node.op}")

    def _prefix_tokens(self, node: ExpressionNode) -> List[TreeNodeToken]:
        label = node.op
        if node.op == "const":
            label = "const"
        tokens = [TreeNodeToken(label=label, arity=len(node.children))]
        for child in node.children:
            tokens.extend(self._prefix_tokens(child))
        return tokens
