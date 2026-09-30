from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.context_metrics import (
    ContextMetricConfig,
    build_context_vector,
    normalize_hv_delta,
    normalize_progress,
)


class ContextMetricTests(unittest.TestCase):
    def test_progress_is_normalized(self) -> None:
        self.assertEqual(normalize_progress(0, 100), 0.0)
        self.assertEqual(normalize_progress(100, 100), 1.0)

    def test_hv_delta_is_clipped(self) -> None:
        config = ContextMetricConfig(hv_delta_scale=0.02)
        self.assertEqual(normalize_hv_delta(0.05, config), 1.0)
        self.assertEqual(normalize_hv_delta(-0.05, config), -1.0)

    def test_context_vector_has_expected_shape(self) -> None:
        vector = build_context_vector(
            generation=15,
            total_generations=60,
            hypervolume=0.45,
            recent_hv_delta=0.01,
            diversity=0.35,
            stagnation_generations=5,
            mean_tree_size=28.0,
        )
        self.assertEqual(len(vector), 6)
        self.assertTrue(all(-1.0 <= value <= 1.0 for value in vector))


if __name__ == "__main__":
    unittest.main()
