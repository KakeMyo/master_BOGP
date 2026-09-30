from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.diversity import (
    TreeNodeToken,
    population_structural_diversity,
    semantic_similarity,
    structural_similarity,
)


def tree_add_x_1():
    return [
        TreeNodeToken("+", 2),
        TreeNodeToken("x", 0),
        TreeNodeToken("1", 0),
    ]


def tree_mul_x_1():
    return [
        TreeNodeToken("*", 2),
        TreeNodeToken("x", 0),
        TreeNodeToken("1", 0),
    ]


def tree_plus_nested():
    return [
        TreeNodeToken("+", 2),
        TreeNodeToken("*", 2),
        TreeNodeToken("x", 0),
        TreeNodeToken("2", 0),
        TreeNodeToken("1", 0),
    ]


class DiversityTests(unittest.TestCase):
    def test_identical_trees_have_similarity_one(self) -> None:
        self.assertEqual(structural_similarity(tree_add_x_1(), tree_add_x_1()), 1.0)

    def test_different_trees_have_lower_similarity(self) -> None:
        self.assertLess(structural_similarity(tree_add_x_1(), tree_mul_x_1()), 1.0)

    def test_population_diversity_reflects_tree_variety(self) -> None:
        repeated_population = [tree_add_x_1(), tree_add_x_1(), tree_add_x_1()]
        mixed_population = [tree_add_x_1(), tree_mul_x_1(), tree_plus_nested()]
        self.assertEqual(population_structural_diversity(repeated_population), 0.0)
        self.assertGreater(population_structural_diversity(mixed_population), 0.0)

    def test_semantic_similarity_uses_squared_correlation(self) -> None:
        self.assertEqual(semantic_similarity([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]), 1.0)
        self.assertEqual(semantic_similarity([2.0, 2.0, 2.0], [1.0, 2.0, 3.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
