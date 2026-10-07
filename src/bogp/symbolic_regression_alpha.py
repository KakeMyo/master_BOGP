from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

import numpy as np

from .diversity import TreeNodeToken
from .test_v1_problem import ObjectiveSpec


@dataclass(frozen=True)
class AlphaExpressionNode:
    op: str
    value: float | None = None
    variable_index: int | None = None
    children: Tuple["AlphaExpressionNode", ...] = ()


def _node_size(node: AlphaExpressionNode) -> int:
    return 1 + sum(_node_size(child) for child in node.children)


def _paths(
    node: AlphaExpressionNode,
    prefix: Tuple[int, ...] = (),
) -> list[Tuple[int, ...]]:
    paths = [prefix]
    for index, child in enumerate(node.children):
        paths.extend(_paths(child, prefix + (index,)))
    return paths


def _get_subtree(
    node: AlphaExpressionNode,
    path: Sequence[int],
) -> AlphaExpressionNode:
    current = node
    for index in path:
        current = current.children[index]
    return current


def _replace_subtree(
    node: AlphaExpressionNode,
    path: Sequence[int],
    subtree: AlphaExpressionNode,
) -> AlphaExpressionNode:
    if not path:
        return subtree
    index = path[0]
    children = list(node.children)
    children[index] = _replace_subtree(children[index], path[1:], subtree)
    return AlphaExpressionNode(
        op=node.op,
        value=node.value,
        variable_index=node.variable_index,
        children=tuple(children),
    )


class SymbolicRegressionAlphaProblem:
    """Two-objective symbolic regression problem for formal experiment pilots.

    Objective 1 is clipped training NRMSE. Objective 2 is expression tree size.
    The target can be switched between Friedman-I and Poly-10.
    """

    def __init__(
        self,
        target_name: str = "friedman_i",
        n_train: int = 200,
        n_test: int = 200,
        dataset_seed: int = 20260527,
        max_initial_depth: int = 5,
        max_mutation_depth: int = 2,
        error_upper: float = 5.0,
        max_tree_size: int = 100,
        constant_range: tuple[float, float] = (-2.0, 2.0),
        prediction_clip: float = 1.0e6,
        protected_epsilon: float = 1.0e-6,
        noise_sigma: float = 0.0,
    ) -> None:
        self.target_name = target_name
        self.n_train = n_train
        self.n_test = n_test
        self.dataset_seed = dataset_seed
        self.max_initial_depth = max_initial_depth
        self.max_mutation_depth = max_mutation_depth
        self.error_upper = float(error_upper)
        self.max_tree_size = int(max_tree_size)
        self.constant_range = constant_range
        self.prediction_clip = float(prediction_clip)
        self.protected_epsilon = float(protected_epsilon)
        self.noise_sigma = float(noise_sigma)
        self.objectives = (
            ObjectiveSpec("train_nrmse", "minimize", lower=0.0, upper=self.error_upper),
            ObjectiveSpec(
                "tree_size",
                "minimize",
                lower=1.0,
                upper=float(self.max_tree_size),
            ),
        )

        rng = np.random.default_rng(self.dataset_seed)
        self.x_train, self.y_train, self.x_test, self.y_test = self._make_dataset(rng)
        self.variable_count = int(self.x_train.shape[1])
        self.y_train_std = float(np.std(self.y_train))

    @classmethod
    def friedman_i(cls, **kwargs) -> "SymbolicRegressionAlphaProblem":
        return cls(target_name="friedman_i", **kwargs)

    @classmethod
    def poly10(cls, **kwargs) -> "SymbolicRegressionAlphaProblem":
        return cls(target_name="poly10", **kwargs)

    def create_individual(self, rng) -> AlphaExpressionNode:
        return self._random_tree(rng, self.max_initial_depth)

    def evaluate(self, individual: AlphaExpressionNode) -> Sequence[float]:
        predictions = self._evaluate_node(individual, self.x_train)
        if not np.all(np.isfinite(predictions)):
            nrmse = self.error_upper
        else:
            clipped = np.clip(
                predictions,
                -self.prediction_clip,
                self.prediction_clip,
            )
            rmse = float(np.sqrt(np.mean((clipped - self.y_train) ** 2)))
            nrmse = rmse / max(self.y_train_std, 1.0e-12)
            nrmse = min(max(nrmse, 0.0), self.error_upper)
        return (float(nrmse), float(self.tree_size(individual)))

    def test_nrmse(self, individual: AlphaExpressionNode) -> float:
        predictions = self._evaluate_node(individual, self.x_test)
        if not np.all(np.isfinite(predictions)):
            return self.error_upper
        clipped = np.clip(predictions, -self.prediction_clip, self.prediction_clip)
        rmse = float(np.sqrt(np.mean((clipped - self.y_test) ** 2)))
        return min(max(rmse / max(float(np.std(self.y_test)), 1.0e-12), 0.0), self.error_upper)

    def crossover(
        self,
        parent_a: AlphaExpressionNode,
        parent_b: AlphaExpressionNode,
        rng,
    ) -> tuple[AlphaExpressionNode, AlphaExpressionNode]:
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

    def mutate(self, individual: AlphaExpressionNode, rng) -> AlphaExpressionNode:
        paths = _paths(individual)
        path = paths[int(rng.integers(0, len(paths)))]
        replacement = self._random_tree(rng, self.max_mutation_depth)
        return _replace_subtree(individual, path, replacement)

    def tree_size(self, individual: AlphaExpressionNode) -> int:
        return _node_size(individual)

    def structural_tokens(self, individual: AlphaExpressionNode) -> Iterable[TreeNodeToken]:
        return self._prefix_tokens(individual)

    def _make_dataset(
        self,
        rng: np.random.Generator,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if self.target_name == "friedman_i":
            x_train = rng.uniform(0.0, 1.0, size=(self.n_train, 5))
            x_test = rng.uniform(0.0, 1.0, size=(self.n_test, 5))
            y_train = self._friedman_i_target(x_train)
            y_test = self._friedman_i_target(x_test)
        elif self.target_name == "poly10":
            x_train = rng.uniform(-1.0, 1.0, size=(self.n_train, 10))
            x_test = rng.uniform(-1.0, 1.0, size=(self.n_test, 10))
            y_train = self._poly10_target(x_train)
            y_test = self._poly10_target(x_test)
        else:
            raise ValueError("target_name must be 'friedman_i' or 'poly10'.")

        if self.noise_sigma > 0.0:
            y_train = y_train + rng.normal(0.0, self.noise_sigma, size=len(y_train))
        return x_train, y_train, x_test, y_test

    def _friedman_i_target(self, x_values: np.ndarray) -> np.ndarray:
        return (
            10.0 * np.sin(np.pi * x_values[:, 0] * x_values[:, 1])
            + 20.0 * ((x_values[:, 2] - 0.5) ** 2)
            + (10.0 * x_values[:, 3])
            + (5.0 * x_values[:, 4])
        )

    def _poly10_target(self, x_values: np.ndarray) -> np.ndarray:
        return (
            (x_values[:, 0] * x_values[:, 1])
            + (x_values[:, 2] * x_values[:, 3])
            + (x_values[:, 4] * x_values[:, 5])
            + (x_values[:, 0] * x_values[:, 6] * x_values[:, 8])
            + (x_values[:, 2] * x_values[:, 5] * x_values[:, 9])
        )

    def _random_tree(self, rng, depth: int) -> AlphaExpressionNode:
        if depth <= 0 or float(rng.random()) < 0.22:
            return self._random_terminal(rng)

        op = str(rng.choice(["add", "sub", "mul", "div", "sin", "cos"]))
        if op in {"sin", "cos"}:
            return AlphaExpressionNode(
                op=op,
                children=(self._random_tree(rng, depth - 1),),
            )
        return AlphaExpressionNode(
            op=op,
            children=(
                self._random_tree(rng, depth - 1),
                self._random_tree(rng, depth - 1),
            ),
        )

    def _random_terminal(self, rng) -> AlphaExpressionNode:
        if float(rng.random()) < 0.70:
            return AlphaExpressionNode(
                op="var",
                variable_index=int(rng.integers(0, self.variable_count)),
            )
        lower, upper = self.constant_range
        return AlphaExpressionNode(
            op="const",
            value=float(rng.uniform(lower, upper)),
        )

    def _evaluate_node(
        self,
        node: AlphaExpressionNode,
        x_values: np.ndarray,
    ) -> np.ndarray:
        if node.op == "var":
            if node.variable_index is None:
                raise ValueError("Variable node does not have variable_index.")
            return x_values[:, node.variable_index]
        if node.op == "const":
            return np.full(x_values.shape[0], float(node.value or 0.0), dtype=float)

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
        if node.op == "div":
            numerator = self._evaluate_node(node.children[0], x_values)
            denominator = self._evaluate_node(node.children[1], x_values)
            return np.divide(
                numerator,
                denominator,
                out=numerator.copy(),
                where=np.abs(denominator) > self.protected_epsilon,
            )
        if node.op == "sin":
            return np.sin(self._evaluate_node(node.children[0], x_values))
        if node.op == "cos":
            return np.cos(self._evaluate_node(node.children[0], x_values))
        raise ValueError(f"Unknown alpha expression op: {node.op}")

    def _prefix_tokens(self, node: AlphaExpressionNode) -> list[TreeNodeToken]:
        if node.op == "var":
            label = f"x{int(node.variable_index or 0) + 1}"
        elif node.op == "const":
            label = "const"
        else:
            label = node.op
        tokens = [TreeNodeToken(label=label, arity=len(node.children))]
        for child in node.children:
            tokens.extend(self._prefix_tokens(child))
        return tokens
