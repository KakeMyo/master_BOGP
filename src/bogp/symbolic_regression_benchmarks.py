"""Reproducible pilot data with the unmodified seminar GP representation.

No extra primitives, coefficient optimisation, linear scaling, or size limits
are introduced. Real-data standardisation is fitted on training rows only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .symbolic_regression_alpha import AlphaExpressionNode, SymbolicRegressionAlphaProblem
from .test_ver2_b_mo_engine import MultiObjectiveGPEngine


DATASET_SEED = 20260527
FEATURE_NAMES = {
    "airfoil": ["frequency_Hz", "attack_angle_deg", "chord_length_m",
                "free_stream_velocity_m_s", "suction_displacement_thickness_m"],
    "concrete": ["cement_kg_m3", "slag_kg_m3", "fly_ash_kg_m3", "water_kg_m3",
                 "superplasticizer_kg_m3", "coarse_aggregate_kg_m3",
                 "fine_aggregate_kg_m3", "age_days"],
}


@dataclass(frozen=True)
class RegressionDataset:
    name: str
    x_train: np.ndarray
    y_train: np.ndarray
    x_validation: np.ndarray
    y_validation: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    target_offset: float
    target_scale: float
    metadata: dict[str, Any]


def uball_target(x: np.ndarray) -> np.ndarray:
    return 10.0 / (5.0 + np.sum((x - 3.0) ** 2, axis=1))


def make_uball_dataset(dataset_seed: int = DATASET_SEED) -> RegressionDataset:
    rng = np.random.default_rng(dataset_seed)
    # Generate canonical train/test first; validation must not change either.
    x_train = rng.uniform(0.05, 6.05, (1024, 5))
    x_test = rng.uniform(-0.25, 6.35, (5000, 5))
    x_validation = rng.uniform(0.05, 6.05, (1024, 5))
    return RegressionDataset(
        "uball5d", x_train, uball_target(x_train),
        x_validation, uball_target(x_validation), x_test, uball_target(x_test),
        0.0, 1.0,
        {"dataset_seed": dataset_seed, "formula": "10/(5+sum((xi-3)^2,i=1..5))",
         "train_range": [0.05, 6.05], "test_range": [-0.25, 6.35],
         "validation_range": [0.05, 6.05], "noise_sigma": 0.0,
         "preprocessing": "none; canonical raw inputs and targets",
         "validation_is_research_extension": True,
         "source": "White et al. (2013), Better GP Benchmarks, Table 5"},
    )


def split_input_groups(x: np.ndarray, seed: int) -> dict[str, np.ndarray]:
    """60/15/25% of unique-input groups; retain duplicates within one partition."""
    groups: dict[tuple[float, ...], list[int]] = {}
    for index, row in enumerate(x):
        groups.setdefault(tuple(row), []).append(index)
    group_rows = list(groups.values())
    if len(group_rows) < 7:
        raise ValueError("At least seven distinct input groups are required.")
    order = np.random.default_rng(seed).permutation(len(group_rows))
    train_end = int(0.60 * len(group_rows))
    validation_end = train_end + int(0.15 * len(group_rows))
    boundaries = {"train": order[:train_end],
                  "validation": order[train_end:validation_end],
                  "test": order[validation_end:]}
    return {name: np.asarray([row for group in indices for row in group_rows[group]], dtype=int)
            for name, indices in boundaries.items()}


def make_tabular_dataset(
    name: str, values: np.ndarray, dataset_seed: int = DATASET_SEED,
    source_metadata: dict[str, Any] | None = None,
) -> RegressionDataset:
    values = np.array(values, dtype=float, copy=True)
    if name not in FEATURE_NAMES:
        raise ValueError(f"Unknown tabular problem: {name}")
    if values.ndim != 2 or values.shape[1] != len(FEATURE_NAMES[name]) + 1:
        raise ValueError("Unexpected feature/target column count.")
    if not np.all(np.isfinite(values)):
        raise ValueError("Raw data contain non-finite or missing values.")
    x, y = values[:, :-1], values[:, -1]
    indices = split_input_groups(x, dataset_seed)
    training = indices["train"]
    x_offset = np.mean(x[training], axis=0)
    x_scale = np.std(x[training], axis=0)
    x_scale = np.where(x_scale > 1.0e-12, x_scale, 1.0)
    y_offset, y_scale = float(np.mean(y[training])), float(np.std(y[training]))
    if y_scale <= 1.0e-12:
        raise ValueError("Training target has no usable variance.")
    standardized_x, standardized_y = (x - x_offset) / x_scale, (y - y_offset) / y_scale
    metadata = {
        **(source_metadata or {}), "dataset_seed": dataset_seed,
        "feature_names": FEATURE_NAMES[name], "row_count": len(y),
        "unique_input_count": len(np.unique(x, axis=0)),
        "duplicate_input_rows_beyond_first": len(x) - len(np.unique(x, axis=0)),
        "exact_duplicate_rows_beyond_first": len(values) - len(np.unique(values, axis=0)),
        "split_rule": "permute unique-input groups; floor(60%) train, floor(15%) validation, rest test",
        "split_indices_0_based": {key: item.tolist() for key, item in indices.items()},
        "preprocessing": "train-only z-score of X and y; no fitted linear scaling of GP output",
        "x_offset": x_offset.tolist(), "x_scale": x_scale.tolist(),
        "target_offset": y_offset, "target_scale": y_scale,
        "target_unit": "dB" if name == "airfoil" else "MPa",
        "raw_numeric_sha256": hashlib.sha256(values.astype("<f8").tobytes()).hexdigest(),
    }
    return RegressionDataset(
        name, standardized_x[training], standardized_y[training],
        standardized_x[indices["validation"]], standardized_y[indices["validation"]],
        standardized_x[indices["test"]], standardized_y[indices["test"]],
        y_offset, y_scale, metadata,
    )


def load_official_data(name: str, raw_dir: Path) -> RegressionDataset:
    if name == "airfoil":
        path = raw_dir / "airfoil_self_noise.dat"
        values = np.loadtxt(path)
        expected_shape = (1503, 6)
        url = "https://archive.ics.uci.edu/dataset/291/airfoil%2Bself%2Bnoise"
    elif name == "concrete":
        try:
            import xlrd
        except ImportError as exc:
            raise ImportError("Install the optional datasets extra: pip install -e '.[dev,datasets]'") from exc
        path = raw_dir / "Concrete_Data.xls"
        sheet = xlrd.open_workbook(str(path)).sheet_by_index(0)
        values = np.asarray([sheet.row_values(i) for i in range(1, sheet.nrows)], dtype=float)
        expected_shape = (1030, 9)
        url = "https://archive.ics.uci.edu/dataset/165/concrete%2Bcompressive%2Bstrength"
    else:
        raise ValueError(f"Unknown official dataset: {name}")
    if values.shape != expected_shape:
        raise ValueError(f"Unexpected official dataset shape {values.shape}; expected {expected_shape}")
    return make_tabular_dataset(name, values, source_metadata={
        "source": url, "license": "CC BY 4.0", "raw_file": path.name,
        "raw_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })


def dataset_manifest(dataset: RegressionDataset) -> dict[str, Any]:
    return {"name": dataset.name, **dataset.metadata,
            "partition_sizes": {"train": len(dataset.y_train),
                                "validation": len(dataset.y_validation), "test": len(dataset.y_test)},
            "partition_array_sha256": {
                name: hashlib.sha256(x.astype("<f8").tobytes() + y.astype("<f8").tobytes()).hexdigest()
                for name, x, y in [("train", dataset.x_train, dataset.y_train),
                                   ("validation", dataset.x_validation, dataset.y_validation),
                                   ("test", dataset.x_test, dataset.y_test)]}}


class BenchmarkRegressionProblem(SymbolicRegressionAlphaProblem):
    def __init__(self, dataset: RegressionDataset) -> None:
        self.dataset = dataset
        super().__init__(target_name=dataset.name, n_train=len(dataset.y_train),
                         n_test=len(dataset.y_test), dataset_seed=DATASET_SEED)

    def _make_dataset(self, rng):
        return (self.dataset.x_train, self.dataset.y_train,
                self.dataset.x_test, self.dataset.y_test)

    def diagnostics(self, node: AlphaExpressionNode) -> dict[str, Any]:
        result: dict[str, Any] = {"tree_size": self.tree_size(node)}
        for name, x, y in [("train", self.x_train, self.y_train),
                           ("validation", self.dataset.x_validation, self.dataset.y_validation),
                           ("test", self.x_test, self.y_test)]:
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                prediction = self._evaluate_node(node, x)
            if not np.all(np.isfinite(prediction)):
                result.update({f"{name}_rmse_original_units": None, f"{name}_nrmse_raw": None,
                               f"{name}_r2": None, f"{name}_prediction_finite": False})
                continue
            clipped = np.clip(prediction, -self.prediction_clip, self.prediction_clip)
            mse = float(np.mean((clipped - y) ** 2))
            variance = max(float(np.var(y)), 1.0e-24)
            result.update({f"{name}_rmse_original_units": float(np.sqrt(mse)) * self.dataset.target_scale,
                           f"{name}_nrmse_raw": float(np.sqrt(mse / variance)),
                           f"{name}_r2": 1.0 - mse / variance,
                           f"{name}_prediction_finite": True})
        return result


def expression_text(node: AlphaExpressionNode) -> str:
    if node.op == "var":
        return f"x{node.variable_index + 1}"
    if node.op == "const":
        return format(node.value, ".17g")
    return f"{node.op}({','.join(expression_text(child) for child in node.children)})"


class BenchmarkRecordingEngine(MultiObjectiveGPEngine):
    """Observe train-selected trees without changing selection, RNG, or fitness."""
    def __init__(self, problem, config):
        super().__init__(problem, config)
        self.train_best_checkpoints = [self._capture_train_best()]

    def _capture_train_best(self):
        selected = min(self.archive, key=lambda item: (item.objective_values[0],
                                                     item.objective_values[1]))
        return (self.snapshot().generation, selected.individual, selected.objective_values[0])

    def _advance_one_generation(self, control):
        evaluations = super()._advance_one_generation(control)
        self.train_best_checkpoints.append(self._capture_train_best())
        return evaluations


def write_regression_artifacts(engine: BenchmarkRecordingEngine, run_dir: Path) -> None:
    # All holdout evaluation takes place AFTER the entire search has finished.
    problem = engine.problem
    rows = [{"generation": generation, "train_nrmse_objective": objective,
             "expression": asdict(node), "expression_text": expression_text(node),
             **problem.diagnostics(node)}
            for generation, node, objective in engine.train_best_checkpoints]
    (run_dir / "regression_diagnostics.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows), encoding="utf-8")
    archive = [{"objective_values": item.objective_values, "expression": asdict(item.individual),
                "expression_text": expression_text(item.individual), **problem.diagnostics(item.individual)}
               for item in engine.unique_objective_archive]
    (run_dir / "regression_archive.json").write_text(
        json.dumps(archive, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Completed {problem.dataset.name}/{run_dir.parent.name}/{run_dir.name}", flush=True)
