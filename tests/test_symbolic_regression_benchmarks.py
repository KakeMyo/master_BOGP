from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bogp.benchmark_analysis import warmup_headroom
from bogp.formal_experiment import FormalExperimentConfig, ProblemSpec, run_problem_experiment
from bogp.symbolic_regression_alpha import AlphaExpressionNode as Node
from bogp.symbolic_regression_benchmarks import (
    BenchmarkRecordingEngine, BenchmarkRegressionProblem, dataset_manifest,
    make_tabular_dataset, make_uball_dataset, split_input_groups,
    uball_target, write_regression_artifacts,
)
from bogp.test_ver2_b_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.types import ControlInput


def test_uball_canonical_ranges_counts_and_reproducibility():
    data = make_uball_dataset()
    again = make_uball_dataset()
    assert data.x_train.shape == (1024, 5)
    assert data.x_test.shape == (5000, 5)
    assert data.x_validation.shape == (1024, 5)
    assert np.all((data.x_train >= .05) & (data.x_train <= 6.05))
    assert np.all((data.x_test >= -.25) & (data.x_test <= 6.35))
    np.testing.assert_array_equal(data.x_train, again.x_train)
    np.testing.assert_allclose(uball_target(np.full((1, 5), 3.0)), [2.0])
    json.dumps(dataset_manifest(data), allow_nan=False)


def test_duplicate_input_groups_never_cross_partitions():
    x = np.repeat(np.arange(20.0)[:, None], 2, axis=0)
    splits = split_input_groups(x, 42)
    assert sorted(np.concatenate(list(splits.values()))) == list(range(40))
    sets = {key: set(x[rows, 0]) for key, rows in splits.items()}
    assert not sets["train"] & sets["validation"]
    assert not sets["train"] & sets["test"]
    assert not sets["validation"] & sets["test"]
    assert list(map(len, splits.values())) == [24, 6, 10]


def test_scaler_uses_train_only_and_never_changes_raw_data():
    values = np.arange(120.0).reshape(20, 6)
    original = values.copy()
    data = make_tabular_dataset("airfoil", values, 42)
    indices = data.metadata["split_indices_0_based"]
    train = indices["train"]
    np.testing.assert_array_equal(values, original)
    np.testing.assert_allclose(data.x_train.mean(axis=0), 0.0, atol=1e-12)
    np.testing.assert_allclose(data.x_train.std(axis=0), 1.0, atol=1e-12)
    assert data.target_offset == np.mean(values[train, -1])
    # Target-only changes on held-out rows cannot affect training/scaler.
    modified = values.copy()
    modified[indices["test"], -1] += 100000.0
    new_data = make_tabular_dataset("airfoil", modified, 42)
    np.testing.assert_array_equal(new_data.x_train, data.x_train)
    np.testing.assert_array_equal(new_data.y_train, data.y_train)
    assert new_data.target_scale == data.target_scale


def test_invalid_tabular_shapes_and_missing_values_are_rejected():
    with pytest.raises(ValueError):
        make_tabular_dataset("airfoil", np.ones((20, 5)))
    values = np.arange(120.0).reshape(20, 6)
    values[0, 0] = np.nan
    with pytest.raises(ValueError):
        make_tabular_dataset("airfoil", values)


def test_uball_exact_expression_is_representable_using_seminar_constants():
    def binary(op, left, right):
        return Node(op=op, children=(left, right))
    one, two = Node(op="const", value=1.0), Node(op="const", value=2.0)
    three = binary("add", one, two)
    five = binary("add", binary("add", two, two), one)
    denominator = five
    for i in range(5):
        difference = binary("sub", Node(op="var", variable_index=i), three)
        denominator = binary("add", denominator, binary("mul", difference, difference))
    node = binary("div", binary("mul", five, two), denominator)
    problem = BenchmarkRegressionProblem(make_uball_dataset())
    error, size = problem.evaluate(node)
    assert error < 1e-12
    assert size <= 100
    assert problem.diagnostics(node)["test_nrmse_raw"] < 1e-12


def test_observation_engine_preserves_evolution_and_counts_every_generation():
    data = make_uball_dataset()
    config = MultiObjectiveGPConfig(population_size=6, total_generations=5, random_seed=42,
                                   archive_structure_key_mode="topology_value")
    original = MultiObjectiveGPEngine(BenchmarkRegressionProblem(data), config)
    recorded = BenchmarkRecordingEngine(BenchmarkRegressionProblem(data), config)
    control = ControlInput(.7, .2, 3)
    for _ in range(2):
        assert original.run_interval(control).evaluations == recorded.run_interval(control).evaluations
    assert original.generation_metrics_history == recorded.generation_metrics_history
    assert [item.individual for item in original.archive] == [item.individual for item in recorded.archive]
    assert [item[0] for item in recorded.train_best_checkpoints] == list(range(6))


def test_formal_runner_exports_train_selected_trees_after_search():
    data = make_uball_dataset()
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = ProblemSpec("uball_test", lambda: BenchmarkRegressionProblem(data),
                           BenchmarkRecordingEngine, write_regression_artifacts)
        config = FormalExperimentConfig(population_size=4, total_generations=1,
                                        include_bogp_current=False, output_root=tmpdir, run_id="smoke")
        result = run_problem_experiment(spec, config)
        path = result.output_dir / "runs" / "plain_fixed" / "seed_0"
        rows = [json.loads(line) for line in (path / "regression_diagnostics.jsonl").read_text().splitlines()]
        assert [row["generation"] for row in rows] == [0, 1]
        assert "test_nrmse_raw" in rows[-1]
        assert "expression" in json.loads((path / "regression_archive.json").read_text())[0]


def test_zero_gain_headroom_is_missing_not_spurious_zero():
    result = warmup_headroom([.8] * 79)
    assert result["warmup_improvement_fraction"] is None
    assert result["t90_finite_budget"] is None


def test_headroom_uses_running_max_but_keeps_raw_hv_decreases():
    hv = np.linspace(.1, .9, 79)
    hv[-1] = .8
    result = warmup_headroom(hv)
    assert result["hv_final"] == .8
    assert result["hv_decrease_count"] == 1
    assert 0 < result["warmup_improvement_fraction"] < 1
    assert result["t90_finite_budget"] >= 60
