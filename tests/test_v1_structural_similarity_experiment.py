from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.diversity import structural_similarity
from bogp.test_v1_structural_similarity_experiment import (
    SimilarityExperimentConfig,
    build_controlled_tree,
    is_non_decreasing,
    run_ideal_multiset_experiment,
    run_one_sided_experiment,
    run_shared_tree_experiment,
)


class StructuralSimilarityExperimentTests(unittest.TestCase):
    def test_ideal_multiset_matches_theory(self) -> None:
        config = SimilarityExperimentConfig(max_m=8)
        rows = run_ideal_multiset_experiment(config)
        for row in rows:
            self.assertAlmostEqual(row.similarity, row.theory_similarity)
            self.assertAlmostEqual(row.diversity, 1.0 - row.similarity)

    def test_identical_controlled_trees_have_similarity_one(self) -> None:
        tree = build_controlled_tree("same", shared_motif_count=4, unique_leaf_count=3)
        self.assertEqual(structural_similarity(tree, tree), 1.0)

    def test_shared_tree_similarity_is_non_decreasing(self) -> None:
        config = SimilarityExperimentConfig(max_m=12)
        rows = run_shared_tree_experiment(config)
        self.assertTrue(is_non_decreasing([row.similarity for row in rows]))
        self.assertEqual(rows[0].similarity, 0.0)

    def test_one_sided_experiment_peaks_at_fixed_m(self) -> None:
        config = SimilarityExperimentConfig(max_m=16, one_sided_fixed_m=6)
        rows = run_one_sided_experiment(config)
        peak = max(rows, key=lambda row: row.similarity)
        self.assertEqual(peak.m, config.one_sided_fixed_m)
        for row in rows:
            self.assertAlmostEqual(row.diversity, 1.0 - row.similarity)


if __name__ == "__main__":
    unittest.main()
