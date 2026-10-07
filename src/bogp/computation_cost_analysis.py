"""Analysis utilities for the BOGP computation-cost experiment.

The module intentionally depends only on the Python standard library, NumPy,
and Matplotlib.  SciPy is used when available for Wilcoxon signed-rank tests.
Rows belonging to failed or incomplete runs are retained in the validation
report but excluded from statistical summaries.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHOD_ORDER = (
    "fixed_standard",
    "fixed_high_mutation",
    "fixed_high_crossover",
    "fixed_core",
    "bogp_adaptive",
    "bogp_replay",
    "bogp_k1_matched",
)

# fixed_core and bogp_replay isolate measurement/controller overhead.  They are
# timing ablations, not independently deployable search methods.
PRIMARY_ANALYSIS_METHODS = (
    "fixed_standard",
    "fixed_high_mutation",
    "fixed_high_crossover",
    "bogp_adaptive",
    "bogp_k1_matched",
)

METHOD_LABELS = {
    "fixed_standard": "Fixed standard",
    "fixed_high_mutation": "Fixed high mutation",
    "fixed_high_crossover": "Fixed high crossover",
    "fixed_core": "Fixed GP-core",
    "bogp_adaptive": "BOGP adaptive k",
    "bogp_replay": "BOGP replay",
    "bogp_k1_matched": "BOGP k=1",
}

COLORS = {
    "fixed_standard": "#5470A8",
    "fixed_high_mutation": "#69A36F",
    "fixed_high_crossover": "#C68845",
    "fixed_core": "#8B83A8",
    "bogp_adaptive": "#D65353",
    "bogp_replay": "#4E9B9B",
    "bogp_k1_matched": "#B66AA0",
}

METHOD_ALIASES = {
    "plain_fixed_standard": "fixed_standard",
    "plain_fixed_high_mutation": "fixed_high_mutation",
    "plain_fixed_high_crossover": "fixed_high_crossover",
    "fixed_gp_core": "fixed_core",
    "bogp_current": "bogp_adaptive",
    "adaptive": "bogp_adaptive",
    "replay": "bogp_replay",
    "bogp_k1": "bogp_k1_matched",
}

FIELD_ALIASES = {
    "method": ("method_name", "method", "setting_name"),
    "seed": ("seed", "random_seed"),
    "status": ("status", "run_status"),
    "total_time": (
        "total_algorithm_wall_seconds",
        "wall_time_seconds",
        "total_time_seconds",
        "runtime_seconds",
    ),
    "cpu_time": ("total_algorithm_cpu_seconds", "cpu_time_seconds"),
    "final_hv": ("final_archive_hypervolume", "final_hv", "archive_hypervolume"),
    "evaluations": ("total_evaluations", "evaluations", "evaluation_count"),
    "generations": ("total_generations", "generations", "final_generation"),
    "generation": ("generation", "generation_index"),
    "elapsed": (
        "elapsed_wall_seconds",
        "cumulative_elapsed_seconds",
        "elapsed_seconds",
    ),
    "trace_hv": ("archive_hypervolume", "hypervolume", "hv"),
    "trace_evaluations": ("cumulative_evaluations", "evaluations"),
}

# These timers are deliberately shown as individual measurements, not summed
# into a stack: some are nested (for example, GPR fit is inside propose).
COMPONENTS = {
    "initialization": ("initialization_wall_seconds", "initialization_seconds"),
    "search": ("search_wall_seconds", "search_seconds"),
    "controller total": (
        "controller_total_wall_seconds",
        "controller_wall_seconds",
        "controller_total_seconds",
    ),
    "controller propose": (
        "controller_propose_total_wall_seconds",
        "controller_propose_wall_seconds",
        "controller_propose_seconds",
    ),
    "controller register": (
        "controller_register_total_wall_seconds",
        "controller_register_wall_seconds",
        "controller_register_seconds",
    ),
    "GPR fit": ("gpr_fit_wall_seconds", "gpr_fit_seconds"),
    "GPR predict": ("gpr_predict_wall_seconds", "gpr_predict_seconds"),
    "candidate sampling": (
        "candidate_sampling_wall_seconds",
        "candidate_sampling_seconds",
    ),
    "expected improvement": (
        "expected_improvement_wall_seconds",
        "ei_wall_seconds",
        "expected_improvement_seconds",
    ),
    "engine interval": ("engine_interval_wall_seconds", "engine_interval_seconds"),
    "GP generation": (
        "gp_generation_total_wall_seconds",
        "gp_evolution_wall_seconds",
        "gp_generation_seconds",
    ),
    "archive HV/state": (
        "archive_hv_state_wall_seconds",
        "archive_hv_state_seconds",
    ),
    "population diversity": (
        "population_diversity_wall_seconds",
        "population_diversity_seconds",
    ),
    "population HV": ("population_hv_wall_seconds", "population_hv_seconds"),
    "reward": ("reward_wall_seconds", "reward_seconds"),
    "GP evolution excl. archive HV": (
        "gp_evolution_without_archive_hv_wall_seconds",
        "gp_evolution_without_archive_hv_seconds",
    ),
}

HASH_COLUMNS = (
    "final_population_hash",
    "final_archive_hash",
    "generation_state_hash",
    "control_schedule_hash",
)

SUCCESS_STATUSES = {
    "",
    "ok",
    "success",
    "successful",
    "succeeded",
    "complete",
    "completed",
    "done",
    "passed",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _first(row: Mapping[str, str], aliases: Sequence[str]) -> str | None:
    for key in aliases:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _number(row: Mapping[str, str], aliases: Sequence[str]) -> float:
    value = _first(row, aliases)
    if value is None:
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _canonical_method(row: Mapping[str, str]) -> str:
    raw = _first(row, FIELD_ALIASES["method"]) or "unknown"
    return METHOD_ALIASES.get(raw, raw)


def _seed(row: Mapping[str, str]) -> int | None:
    value = _number(row, FIELD_ALIASES["seed"])
    return int(value) if math.isfinite(value) else None


def _is_success(row: Mapping[str, str]) -> bool:
    status = (_first(row, FIELD_ALIASES["status"]) or "").lower()
    return status in SUCCESS_STATUSES


def _finite(value: float) -> bool:
    return math.isfinite(value)


def _json_value(value: Any) -> Any:
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_json_value(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _json_value(row.get(key, "")) for key in fields})


def _experiment_expectations(summary_path: Path) -> dict[str, Any]:
    """Read the sibling experiment config, falling back to the full design."""

    config_path = summary_path.parent / "experiment_config.json"
    fallback_seeds: list[int] = []
    if not config_path.exists():
        return {
            "config_path": str(config_path),
            "config_found": False,
            "config_error": None,
            "methods": list(METHOD_ORDER),
            "seeds": fallback_seeds,
            "population_size": None,
            "total_generations": None,
            "matched_warmup_generations": 18,
        }
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        configured_methods = config.get("methods", METHOD_ORDER)
        configured_seeds = config.get("seeds", ())
        methods = [METHOD_ALIASES.get(str(item), str(item)) for item in configured_methods]
        seeds = [int(item) for item in configured_seeds]
        return {
            "config_path": str(config_path),
            "config_found": True,
            "config_error": None,
            "methods": methods,
            "seeds": seeds,
            "population_size": int(config["population_size"]) if config.get("population_size") is not None else None,
            "total_generations": int(config["total_generations"]) if config.get("total_generations") is not None else None,
            "matched_warmup_generations": int(config.get("matched_warmup_generations", 18)),
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "config_path": str(config_path),
            "config_found": True,
            "config_error": f"{type(exc).__name__}: {exc}",
            "methods": list(METHOD_ORDER),
            "seeds": fallback_seeds,
            "population_size": None,
            "total_generations": None,
            "matched_warmup_generations": 18,
        }


def _method_sort_key(method: str) -> tuple[int, str]:
    try:
        return METHOD_ORDER.index(method), method
    except ValueError:
        return len(METHOD_ORDER), method


def _stats(values: Iterable[float]) -> dict[str, float | int]:
    array = np.asarray([v for v in values if _finite(v)], dtype=float)
    if array.size == 0:
        return {key: math.nan for key in ("mean", "std", "median", "q25", "q75", "min", "max")} | {"n": 0}
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "std": float(np.std(array, ddof=1)) if array.size > 1 else 0.0,
        "median": float(np.median(array)),
        "q25": float(np.quantile(array, 0.25)),
        "q75": float(np.quantile(array, 0.75)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def _component_value(row: Mapping[str, str], name: str) -> float:
    return _number(row, COMPONENTS[name])


def _trace_index(
    rows: Sequence[Mapping[str, str]],
) -> dict[tuple[str, int], list[dict[str, str]]]:
    result: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        seed = _seed(row)
        if seed is not None:
            result[(_canonical_method(row), seed)].append(dict(row))
    for key in result:
        result[key].sort(key=lambda row: _number(row, FIELD_ALIASES["elapsed"]))
    return dict(result)


def _run_records(
    rows: Sequence[Mapping[str, str]],
    trace: Mapping[tuple[str, int], Sequence[Mapping[str, str]]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        if not _is_success(row):
            continue
        method, seed = _canonical_method(row), _seed(row)
        if seed is None:
            continue
        total_time = _number(row, FIELD_ALIASES["total_time"])
        cpu_time = _number(row, FIELD_ALIASES["cpu_time"])
        final_hv = _number(row, FIELD_ALIASES["final_hv"])
        evaluations = _number(row, FIELD_ALIASES["evaluations"])
        generations = _number(row, FIELD_ALIASES["generations"])
        method_trace = trace.get((method, seed), ())
        if not _finite(generations) and method_trace:
            generations = max(_number(item, FIELD_ALIASES["generation"]) for item in method_trace)
        record: dict[str, Any] = {
            "method": method,
            "seed": seed,
            "total_time_seconds": total_time,
            "total_cpu_seconds": cpu_time,
            "cpu_to_wall_ratio": cpu_time / total_time if _finite(cpu_time) and _finite(total_time) and total_time > 0 else math.nan,
            "final_hv": final_hv,
            "evaluations": evaluations,
            "generations": generations,
            "seconds_per_generation": total_time / generations if _finite(total_time) and _finite(generations) and generations > 0 else math.nan,
            "seconds_per_evaluation": total_time / evaluations if _finite(total_time) and _finite(evaluations) and evaluations > 0 else math.nan,
            "raw": row,
        }
        for component in COMPONENTS:
            record[f"component::{component}"] = _component_value(row, component)
        records.append(record)
    return records


def aggregate_summary(records: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["method"])].append(record)
    metrics = [
        "total_time_seconds",
        "total_cpu_seconds",
        "cpu_to_wall_ratio",
        "final_hv",
        "evaluations",
        "generations",
        "seconds_per_generation",
        "seconds_per_evaluation",
    ] + [f"component::{name}" for name in COMPONENTS]
    statistic_names = ("n", "mean", "std", "median", "q25", "q75", "min", "max")
    fields = ["method", "n_runs", "n_unique_seeds"] + [
        f"{metric.replace('component::', 'component_').replace(' ', '_')}_{stat}"
        for metric in metrics
        for stat in statistic_names
    ]
    output: list[dict[str, Any]] = []
    for method in sorted(grouped, key=_method_sort_key):
        method_records = grouped[method]
        row: dict[str, Any] = {
            "method": method,
            "n_runs": len(method_records),
            "n_unique_seeds": len({int(r["seed"]) for r in method_records}),
        }
        for metric in metrics:
            prefix = metric.replace("component::", "component_").replace(" ", "_")
            for stat, value in _stats(float(r.get(metric, math.nan)) for r in method_records).items():
                row[f"{prefix}_{stat}"] = value
        output.append(row)
    return output, fields


def _bootstrap_mean_ci(values: np.ndarray, rng: np.random.Generator, samples: int) -> tuple[float, float]:
    if values.size == 0:
        return math.nan, math.nan
    if values.size == 1:
        return float(values[0]), float(values[0])
    means = np.empty(samples, dtype=float)
    # Chunking avoids a large (samples x n) temporary array at 100+ seeds.
    chunk = 512
    for start in range(0, samples, chunk):
        size = min(chunk, samples - start)
        indices = rng.integers(0, values.size, size=(size, values.size))
        means[start : start + size] = np.mean(values[indices], axis=1)
    return tuple(float(v) for v in np.quantile(means, [0.025, 0.975]))


def _wilcoxon(values: np.ndarray) -> tuple[float, float]:
    nonzero = values[np.abs(values) > 1.0e-15]
    if nonzero.size == 0:
        return 0.0, 1.0
    try:
        from scipy.stats import wilcoxon

        result = wilcoxon(values, zero_method="wilcox", alternative="two-sided")
        return float(result.statistic), float(result.pvalue)
    except (ImportError, ValueError):
        return math.nan, math.nan


def _rank_biserial(values: np.ndarray) -> float:
    nonzero = values[np.abs(values) > 1.0e-15]
    if nonzero.size == 0:
        return 0.0
    ranks = np.empty(nonzero.size, dtype=float)
    order = np.argsort(np.abs(nonzero), kind="mergesort")
    sorted_abs = np.abs(nonzero)[order]
    start = 0
    while start < nonzero.size:
        end = start + 1
        while end < nonzero.size and sorted_abs[end] == sorted_abs[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    positive = float(np.sum(ranks[nonzero > 0]))
    negative = float(np.sum(ranks[nonzero < 0]))
    denominator = positive + negative
    return (positive - negative) / denominator if denominator else 0.0


def _holm_adjust(p_values: Sequence[float]) -> list[float]:
    result = [math.nan] * len(p_values)
    finite_indices = [i for i, value in enumerate(p_values) if _finite(value)]
    ordered = sorted(finite_indices, key=lambda i: p_values[i])
    running = 0.0
    count = len(ordered)
    for rank, index in enumerate(ordered):
        adjusted = min(1.0, (count - rank) * p_values[index])
        running = max(running, adjusted)
        result[index] = running
    return result


def paired_comparisons(
    records: Sequence[Mapping[str, Any]],
    *,
    bootstrap_samples: int = 10_000,
    bootstrap_seed: int = 20260731,
) -> list[dict[str, Any]]:
    by_key = {(str(r["method"]), int(r["seed"])): r for r in records}
    methods = {str(r["method"]) for r in records}
    pairs: list[tuple[str, str]] = []
    if "bogp_adaptive" in methods:
        pairs.extend(("bogp_adaptive", method) for method in METHOD_ORDER if method != "bogp_adaptive" and method in methods)
    if "fixed_standard" in methods and "fixed_core" in methods:
        pair = ("fixed_standard", "fixed_core")
        if pair not in pairs:
            pairs.append(pair)

    rng = np.random.default_rng(bootstrap_seed)
    output: list[dict[str, Any]] = []
    for method_a, method_b in pairs:
        seeds = sorted(
            {seed for method, seed in by_key if method == method_a}
            & {seed for method, seed in by_key if method == method_b}
        )
        for metric in ("final_hv", "total_time_seconds"):
            paired = [
                (float(by_key[(method_a, seed)][metric]), float(by_key[(method_b, seed)][metric]))
                for seed in seeds
            ]
            paired = [(a, b) for a, b in paired if _finite(a) and _finite(b)]
            a_values = np.asarray([item[0] for item in paired], dtype=float)
            b_values = np.asarray([item[1] for item in paired], dtype=float)
            differences = a_values - b_values
            tested = differences
            log_ratios = np.asarray([], dtype=float)
            if metric == "total_time_seconds" and a_values.size:
                positive = (a_values > 0) & (b_values > 0)
                log_ratios = np.log(a_values[positive] / b_values[positive])
                tested = log_ratios
            ci_low, ci_high = _bootstrap_mean_ci(differences, rng, bootstrap_samples)
            log_low, log_high = _bootstrap_mean_ci(log_ratios, rng, bootstrap_samples)
            statistic, p_value = _wilcoxon(tested)
            output.append(
                {
                    "comparison": f"{method_a}_vs_{method_b}",
                    "method_a": method_a,
                    "method_b": method_b,
                    "metric": metric,
                    "n_pairs": int(differences.size),
                    "mean_a": float(np.mean(a_values)) if a_values.size else math.nan,
                    "mean_b": float(np.mean(b_values)) if b_values.size else math.nan,
                    "mean_difference_a_minus_b": float(np.mean(differences)) if differences.size else math.nan,
                    "difference_bootstrap_ci95_low": ci_low,
                    "difference_bootstrap_ci95_high": ci_high,
                    "median_difference_a_minus_b": float(np.median(differences)) if differences.size else math.nan,
                    "wins_a": int(np.sum(differences > 1.0e-12)),
                    "ties": int(np.sum(np.abs(differences) <= 1.0e-12)),
                    "losses_a": int(np.sum(differences < -1.0e-12)),
                    "mean_log_ratio_a_over_b": float(np.mean(log_ratios)) if log_ratios.size else math.nan,
                    "log_ratio_bootstrap_ci95_low": log_low,
                    "log_ratio_bootstrap_ci95_high": log_high,
                    "geometric_mean_ratio_a_over_b": float(np.exp(np.mean(log_ratios))) if log_ratios.size else math.nan,
                    "wilcoxon_statistic": statistic,
                    "p_value_raw": p_value,
                    "rank_biserial_a_minus_b": _rank_biserial(tested),
                }
            )
    adjusted = _holm_adjust([float(row["p_value_raw"]) for row in output])
    for row, value in zip(output, adjusted):
        row["p_value_holm"] = value
    return output


def anytime_by_seed(
    records: Sequence[Mapping[str, Any]],
    trace: Mapping[tuple[str, int], Sequence[Mapping[str, str]]],
) -> list[dict[str, Any]]:
    records_by_key = {(str(r["method"]), int(r["seed"])): r for r in records}
    budgets = {
        int(r["seed"]): float(r["total_time_seconds"])
        for r in records
        if r["method"] == "fixed_standard" and _finite(float(r["total_time_seconds"]))
    }
    output: list[dict[str, Any]] = []
    for seed, budget in sorted(budgets.items()):
        methods = sorted(
            {
                method
                for method, candidate_seed in records_by_key
                if candidate_seed == seed and method in PRIMARY_ANALYSIS_METHODS
            },
            key=_method_sort_key,
        )
        for method in methods:
            points = []
            for row in trace.get((method, seed), ()):
                elapsed = _number(row, FIELD_ALIASES["elapsed"])
                hv = _number(row, FIELD_ALIASES["trace_hv"])
                generation = _number(row, FIELD_ALIASES["generation"])
                if _finite(elapsed) and _finite(hv):
                    points.append((elapsed, hv, generation))
            points.sort()
            eligible = [point for point in points if point[0] <= budget + 1.0e-12]
            record = records_by_key[(method, seed)]
            total = float(record["total_time_seconds"])
            if _finite(total) and total <= budget + 1.0e-12 and _finite(float(record["final_hv"])):
                elapsed, hv, generation = total, float(record["final_hv"]), float(record["generations"])
                source = "summary_final"
            elif eligible:
                elapsed, hv, generation = eligible[-1]
                source = "trace_at_or_before_budget"
            else:
                elapsed = hv = generation = math.nan
                source = "unavailable"
            output.append(
                {
                    "seed": seed,
                    "method": method,
                    "fixed_standard_budget_seconds": budget,
                    "hv_at_budget": hv,
                    "last_observed_elapsed_seconds": elapsed,
                    "last_observed_generation": generation,
                    "run_total_seconds": total,
                    "run_completed_within_budget": bool(_finite(total) and total <= budget + 1.0e-12),
                    "source": source,
                }
            )
    return output


def _control_signature(row: Mapping[str, str]) -> str | None:
    raw = str(row.get("control", "")).strip()
    if raw:
        try:
            return json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    values = {
        "crossover_rate": _number(row, ("crossover_rate",)),
        "mutation_rate": _number(row, ("mutation_rate",)),
        "update_period": _number(row, ("update_period",)),
    }
    if not all(_finite(value) for value in values.values()):
        return None
    return json.dumps(values, sort_keys=True, separators=(",", ":"))


def _control_interval(row: Mapping[str, str]) -> tuple[int, int] | None:
    start = _number(row, ("start_generation",))
    end = _number(row, ("end_generation",))
    if not _finite(start) or not _finite(end) or not float(start).is_integer() or not float(end).is_integer():
        return None
    return int(start), int(end)


def _control_update_period(row: Mapping[str, str]) -> int | None:
    scalar = _number(row, ("update_period",))
    if not _finite(scalar) or not float(scalar).is_integer():
        return None
    scalar_int = int(scalar)
    raw = str(row.get("control", "")).strip()
    if raw:
        try:
            embedded = float(json.loads(raw)["update_period"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        if not _finite(embedded) or not embedded.is_integer() or int(embedded) != scalar_int:
            return None
    return scalar_int


def validation_report(
    summary_path: Path,
    trace_path: Path,
    summary_rows: Sequence[Mapping[str, str]],
    trace_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    expectations = _experiment_expectations(summary_path)
    expected_methods = tuple(dict.fromkeys(str(item) for item in expectations["methods"]))
    control_trace_path = summary_path.parent / "control_trace.csv"
    control_trace_error: str | None = None
    if control_trace_path.exists():
        try:
            control_trace_rows = _read_csv(control_trace_path)
        except (OSError, csv.Error) as exc:
            control_trace_rows = []
            control_trace_error = f"{type(exc).__name__}: {exc}"
    else:
        control_trace_rows = []
        control_trace_error = "missing control_trace.csv"
    method_counts = Counter(_canonical_method(row) for row in summary_rows)
    successful_counts = Counter(_canonical_method(row) for row in summary_rows if _is_success(row))
    failed_counts = Counter(_canonical_method(row) for row in summary_rows if not _is_success(row))
    all_summary_seeds = sorted({_seed(row) for row in summary_rows if _seed(row) is not None})
    expected_seeds = sorted(set(expectations["seeds"])) or all_summary_seeds
    keys = [(_canonical_method(row), _seed(row)) for row in summary_rows]
    duplicates = [
        {"method": method, "seed": seed, "count": count}
        for (method, seed), count in Counter(keys).items()
        if seed is not None and count > 1
    ]
    rows_by_key: dict[tuple[str, int], list[Mapping[str, str]]] = defaultdict(list)
    for row in summary_rows:
        seed = _seed(row)
        if seed is not None:
            rows_by_key[(_canonical_method(row), seed)].append(row)
    expected_run_grid_issues: list[dict[str, Any]] = []
    expected_grid = {
        (method, seed)
        for method in expected_methods
        for seed in expected_seeds
    }
    for method in expected_methods:
        for seed in expected_seeds:
            candidate_rows = rows_by_key.get((method, seed), [])
            successful_rows = [row for row in candidate_rows if _is_success(row)]
            if len(successful_rows) != 1:
                expected_run_grid_issues.append(
                    {
                        "method": method,
                        "seed": seed,
                        "issue": "missing" if not candidate_rows else "failed_or_not_uniquely_successful",
                        "row_count": len(candidate_rows),
                        "successful_row_count": len(successful_rows),
                        "statuses": [
                            _first(row, FIELD_ALIASES["status"]) or ""
                            for row in candidate_rows
                        ],
                    }
                )
    for (method, seed), candidate_rows in sorted(
        rows_by_key.items(), key=lambda item: (_method_sort_key(item[0][0]), item[0][1])
    ):
        successful_rows = [row for row in candidate_rows if _is_success(row)]
        if successful_rows and (method, seed) not in expected_grid:
            expected_run_grid_issues.append(
                {
                    "method": method,
                    "seed": seed,
                    "issue": "unexpected_successful_run",
                    "row_count": len(candidate_rows),
                    "successful_row_count": len(successful_rows),
                    "statuses": [
                        _first(row, FIELD_ALIASES["status"]) or ""
                        for row in candidate_rows
                    ],
                }
            )

    k1_gate_issues: list[dict[str, Any]] = []
    if "bogp_k1_matched" in expected_methods:
        if control_trace_error:
            k1_gate_issues.append(
                {"issue": "control_trace_unavailable", "detail": control_trace_error}
            )
        control_by_key: dict[tuple[str, int], list[Mapping[str, str]]] = defaultdict(list)
        for row in control_trace_rows:
            seed = _seed(row)
            if seed is not None:
                control_by_key[(_canonical_method(row), seed)].append(row)
        gate = int(expectations.get("matched_warmup_generations", 18))
        for seed in expected_seeds:
            adaptive_rows = control_by_key.get(("bogp_adaptive", seed), [])
            k1_rows = control_by_key.get(("bogp_k1_matched", seed), [])
            k1_summary_candidates = [
                row for row in rows_by_key.get(("bogp_k1_matched", seed), []) if _is_success(row)
            ]
            configured_generations = expectations.get("total_generations")
            generations_value = (
                float(configured_generations)
                if configured_generations is not None
                else (
                    _number(k1_summary_candidates[0], FIELD_ALIASES["generations"])
                    if len(k1_summary_candidates) == 1
                    else math.nan
                )
            )
            if not _finite(generations_value) or not float(generations_value).is_integer():
                k1_gate_issues.append(
                    {"seed": seed, "issue": "k1_total_generations_unavailable"}
                )
                continue
            total_generations = int(generations_value)
            warmup_end = min(gate, total_generations)

            def parsed_controls(rows: Sequence[Mapping[str, str]]) -> tuple[list[tuple[int, int, str, int]], int]:
                parsed: list[tuple[int, int, str, int]] = []
                invalid = 0
                for control_row in rows:
                    interval = _control_interval(control_row)
                    signature = _control_signature(control_row)
                    update_period = _control_update_period(control_row)
                    if (
                        interval is None
                        or signature is None
                        or update_period is None
                    ):
                        invalid += 1
                        continue
                    parsed.append((interval[0], interval[1], signature, update_period))
                parsed.sort(key=lambda item: (item[0], item[1], item[2]))
                return parsed, invalid

            adaptive_controls, adaptive_invalid = parsed_controls(adaptive_rows)
            k1_controls, k1_invalid = parsed_controls(k1_rows)
            if adaptive_invalid or k1_invalid:
                k1_gate_issues.append(
                    {
                        "seed": seed,
                        "issue": "invalid_control_trace_rows",
                        "adaptive_invalid_rows": adaptive_invalid,
                        "k1_invalid_rows": k1_invalid,
                    }
                )
            if not adaptive_controls or not k1_controls:
                k1_gate_issues.append(
                    {
                        "seed": seed,
                        "issue": "missing_adaptive_or_k1_control_rows",
                        "adaptive_row_count": len(adaptive_controls),
                        "k1_row_count": len(k1_controls),
                    }
                )
                continue

            warmup_adaptive = [item for item in adaptive_controls if item[0] < warmup_end]
            warmup_k1 = [item for item in k1_controls if item[0] < warmup_end]
            adaptive_warmup_signatures = [item[:3] for item in warmup_adaptive]
            k1_warmup_signatures = [item[:3] for item in warmup_k1]
            if adaptive_warmup_signatures != k1_warmup_signatures:
                k1_gate_issues.append(
                    {
                        "seed": seed,
                        "issue": "adaptive_k1_warmup_sequence_mismatch",
                        "warmup_end_generation": warmup_end,
                        "adaptive_sequence": adaptive_warmup_signatures,
                        "k1_sequence": k1_warmup_signatures,
                    }
                )

            def coverage_ok(controls: Sequence[tuple[int, int, str, int]], end: int) -> bool:
                cursor = 0
                for start, interval_end, _, _ in controls:
                    if start != cursor or interval_end <= start or interval_end > end:
                        return False
                    cursor = interval_end
                return cursor == end

            if not coverage_ok(warmup_k1, warmup_end) or not coverage_ok(warmup_adaptive, warmup_end):
                k1_gate_issues.append(
                    {
                        "seed": seed,
                        "issue": "warmup_control_intervals_do_not_cover_expected_range",
                        "warmup_end_generation": warmup_end,
                    }
                )
            if not coverage_ok(k1_controls, total_generations):
                k1_gate_issues.append(
                    {
                        "seed": seed,
                        "issue": "k1_control_intervals_do_not_cover_full_run",
                        "total_generations": total_generations,
                    }
                )
            invalid_post_gate = [
                {"start_generation": start, "end_generation": end, "update_period": update_period}
                for start, end, _, update_period in k1_controls
                if start >= gate and update_period != 1
            ]
            if invalid_post_gate:
                k1_gate_issues.append(
                    {
                        "seed": seed,
                        "issue": "k1_post_warmup_update_period_not_one",
                        "gate_generation": gate,
                        "invalid_intervals": invalid_post_gate,
                    }
                )
    nonfinite: list[dict[str, Any]] = []
    for index, row in enumerate(summary_rows, start=2):
        if not _is_success(row):
            continue
        for field in ("seed", "total_time", "final_hv"):
            if not _finite(_number(row, FIELD_ALIASES[field])):
                nonfinite.append({"file": summary_path.name, "row": index, "field": field})
        optional_numeric = (
            FIELD_ALIASES["cpu_time"]
            + FIELD_ALIASES["evaluations"]
            + FIELD_ALIASES["generations"]
            + tuple(alias for aliases in COMPONENTS.values() for alias in aliases)
        )
        for column in optional_numeric:
            raw = row.get(column)
            if raw is not None and str(raw).strip() and not _finite(_number(row, (column,))):
                nonfinite.append({"file": summary_path.name, "row": index, "field": column})
    for index, row in enumerate(trace_rows, start=2):
        for field in ("seed", "generation", "elapsed", "trace_hv"):
            if not _finite(_number(row, FIELD_ALIASES[field])):
                nonfinite.append({"file": trace_path.name, "row": index, "field": field})

    trace_unsorted: dict[tuple[str, int], list[Mapping[str, str]]] = defaultdict(list)
    for row in trace_rows:
        seed = _seed(row)
        if seed is not None:
            trace_unsorted[(_canonical_method(row), seed)].append(row)
    monotonic_issues: list[dict[str, Any]] = []
    duplicate_trace_generations: list[dict[str, Any]] = []
    for (method, seed), rows in trace_unsorted.items():
        elapsed = [_number(row, FIELD_ALIASES["elapsed"]) for row in rows]
        generations = [_number(row, FIELD_ALIASES["generation"]) for row in rows]
        hv = [_number(row, FIELD_ALIASES["trace_hv"]) for row in rows]
        if any(b + 1.0e-12 < a for a, b in zip(elapsed, elapsed[1:])):
            monotonic_issues.append({"method": method, "seed": seed, "field": "elapsed"})
        if any(b < a for a, b in zip(generations, generations[1:])):
            monotonic_issues.append({"method": method, "seed": seed, "field": "generation"})
        if any(b + 1.0e-10 < a for a, b in zip(hv, hv[1:])):
            monotonic_issues.append({"method": method, "seed": seed, "field": "archive_hypervolume"})
        generation_counts = Counter(value for value in generations if _finite(value))
        for generation, count in generation_counts.items():
            if count > 1:
                duplicate_trace_generations.append(
                    {"method": method, "seed": seed, "generation": generation, "count": count}
                )

    successful_keys = {
        (_canonical_method(row), _seed(row))
        for row in summary_rows
        if _is_success(row) and _seed(row) is not None
    }
    missing_trace = [
        {"method": method, "seed": seed}
        for method, seed in sorted(successful_keys, key=lambda item: (_method_sort_key(item[0]), item[1]))
        if (method, seed) not in trace_unsorted
    ]
    final_hv_mismatches: list[dict[str, Any]] = []
    summary_by_key = {
        (_canonical_method(row), _seed(row)): row
        for row in summary_rows
        if _is_success(row) and _seed(row) is not None
    }
    trace_completeness_issues: list[dict[str, Any]] = []
    monitored_methods = {
        "fixed_standard",
        "fixed_high_mutation",
        "fixed_high_crossover",
        "bogp_adaptive",
        "bogp_replay",
        "bogp_k1_matched",
    }
    for (method, seed), summary_row in sorted(
        summary_by_key.items(), key=lambda item: (_method_sort_key(item[0][0]), item[0][1])
    ):
        if method not in monitored_methods and method != "fixed_core":
            continue
        configured_generations = expectations.get("total_generations")
        configured_population = expectations.get("population_size")
        generations_value = (
            float(configured_generations)
            if configured_generations is not None
            else _number(summary_row, FIELD_ALIASES["generations"])
        )
        population_value = (
            float(configured_population)
            if configured_population is not None
            else _number(summary_row, ("population_size",))
        )
        if not _finite(generations_value) or generations_value < 0 or not float(generations_value).is_integer():
            trace_completeness_issues.append(
                {"method": method, "seed": seed, "issue": "total_generations_unavailable_or_invalid"}
            )
            continue
        if not _finite(population_value) or population_value <= 0 or not float(population_value).is_integer():
            trace_completeness_issues.append(
                {"method": method, "seed": seed, "issue": "population_size_unavailable_or_invalid"}
            )
            continue
        total_generations = int(generations_value)
        population_size = int(population_value)
        expected_generation_set = (
            {0, total_generations}
            if method == "fixed_core"
            else set(range(total_generations + 1))
        )
        run_trace = trace_unsorted.get((method, seed), [])
        actual_generations = [
            int(value)
            for value in (_number(row, FIELD_ALIASES["generation"]) for row in run_trace)
            if _finite(value) and float(value).is_integer()
        ]
        counts = Counter(actual_generations)
        actual_generation_set = set(actual_generations)
        missing_generations = sorted(expected_generation_set - actual_generation_set)
        unexpected_generations = sorted(actual_generation_set - expected_generation_set)
        duplicated_generations = {
            str(generation): count for generation, count in sorted(counts.items()) if count != 1
        }
        final_rows = [
            row
            for row in run_trace
            if _number(row, FIELD_ALIASES["generation"]) == total_generations
        ]
        expected_final_evaluations = population_size * (total_generations + 1)
        final_evaluations = (
            _number(final_rows[0], FIELD_ALIASES["trace_evaluations"])
            if len(final_rows) == 1
            else math.nan
        )
        final_evaluations_match = (
            _finite(final_evaluations)
            and math.isclose(final_evaluations, expected_final_evaluations, rel_tol=0.0, abs_tol=1.0e-9)
        )
        if missing_generations or unexpected_generations or duplicated_generations or not final_evaluations_match:
            trace_completeness_issues.append(
                {
                    "method": method,
                    "seed": seed,
                    "issue": "incomplete_generation_trace",
                    "expected_generation_count": len(expected_generation_set),
                    "actual_row_count": len(run_trace),
                    "missing_generations": missing_generations,
                    "unexpected_generations": unexpected_generations,
                    "duplicated_generations": duplicated_generations,
                    "expected_final_cumulative_evaluations": expected_final_evaluations,
                    "actual_final_cumulative_evaluations": final_evaluations,
                    "final_cumulative_evaluations_match": final_evaluations_match,
                }
            )
    for key, rows in trace_unsorted.items():
        summary_row = summary_by_key.get(key)
        if summary_row is None or not rows:
            continue
        summary_hv = _number(summary_row, FIELD_ALIASES["final_hv"])
        trace_hv = _number(rows[-1], FIELD_ALIASES["trace_hv"])
        if _finite(summary_hv) and _finite(trace_hv) and not math.isclose(summary_hv, trace_hv, rel_tol=1.0e-9, abs_tol=1.0e-10):
            final_hv_mismatches.append(
                {"method": key[0], "seed": key[1], "summary_final_hv": summary_hv, "trace_final_hv": trace_hv}
            )

    accounting: list[dict[str, Any]] = []
    for row in summary_rows:
        if not _is_success(row):
            continue
        total = _number(row, FIELD_ALIASES["total_time"])
        initialization = _component_value(row, "initialization")
        search = _component_value(row, "search")
        top_sum = initialization + search
        if all(_finite(value) for value in (total, initialization, search)):
            measured_residual = total - top_sum
            reported_residual = _number(row, ("algorithm_outer_residual_wall_seconds",))
            residual = (
                measured_residual - reported_residual
                if _finite(reported_residual)
                else measured_residual
            )
            residual_fraction = measured_residual / total if total > 0 else math.nan
            reconstruction_ok = abs(residual) <= max(0.002, 0.01 * total)
            # A large outer residual usually indicates a missing/overwritten
            # timing region even when the reported residual is self-consistent.
            residual_fraction_ok = not _finite(reported_residual) or residual_fraction <= 0.10
            accounting.append(
                {
                    "method": _canonical_method(row),
                    "seed": _seed(row),
                    "check": "total_minus_initialization_search_and_reported_outer_residual",
                    "residual_seconds": residual,
                    "relative_residual": residual / total if total > 0 else math.nan,
                    "measured_outer_residual_seconds": measured_residual,
                    "measured_outer_residual_fraction": residual_fraction,
                    "reported_outer_residual_seconds": reported_residual,
                    "within_tolerance": reconstruction_ok and residual_fraction_ok,
                }
            )
        propose = _component_value(row, "controller propose")
        controller_total = _component_value(row, "controller total")
        register = _component_value(row, "controller register")
        if all(_finite(value) for value in (controller_total, propose, register)):
            residual = controller_total - propose - register
            accounting.append(
                {
                    "method": _canonical_method(row),
                    "seed": _seed(row),
                    "check": "controller_total_minus_propose_and_register",
                    "residual_seconds": residual,
                    "relative_residual": residual / controller_total if controller_total > 0 else math.nan,
                    "within_tolerance": abs(residual) <= max(0.002, 0.01 * max(controller_total, 0.0)),
                }
            )
        propose_children = ("GPR fit", "GPR predict", "candidate sampling", "expected improvement")
        inner = sum(_component_value(row, name) for name in propose_children)
        if _finite(propose) and all(_finite(_component_value(row, name)) for name in propose_children):
            measured_residual = propose - inner
            reported_residual = _number(row, ("controller_propose_residual_wall_seconds",))
            residual = measured_residual - reported_residual if _finite(reported_residual) else measured_residual
            accounting.append(
                {
                    "method": _canonical_method(row),
                    "seed": _seed(row),
                    "check": "controller_propose_minus_fit_predict_sampling_ei",
                    "residual_seconds": residual,
                    "relative_residual": residual / propose if propose > 0 else math.nan,
                    "measured_unattributed_seconds": measured_residual,
                    "reported_unattributed_seconds": reported_residual,
                    "within_tolerance": (
                        abs(residual) <= max(0.002, 0.01 * max(propose, 0.0))
                        if _finite(reported_residual)
                        else residual >= -max(0.002, 0.01 * max(propose, 0.0))
                    ),
                }
            )

    hash_presence = {
        column: {
            "present": any(column in row for row in summary_rows),
            "nonempty": sum(bool(str(row.get(column, "")).strip()) for row in summary_rows),
        }
        for column in HASH_COLUMNS
    }
    schedule_match_issues: list[dict[str, Any]] = []
    for row in summary_rows:
        if not _is_success(row) or _canonical_method(row) not in {"bogp_adaptive", "bogp_replay"}:
            continue
        method = _canonical_method(row)
        raw = str(row.get("schedule_matches_source", "")).strip().lower()
        if raw in {"false", "0", "no"} or (method == "bogp_replay" and raw not in {"true", "1", "yes"}):
            schedule_match_issues.append(
                {
                    "method": method,
                    "seed": _seed(row),
                    "schedule_matches_source": row.get("schedule_matches_source", ""),
                }
            )

    replay_checks: list[dict[str, Any]] = []
    by_key = {(_canonical_method(row), _seed(row)): row for row in summary_rows if _is_success(row)}
    if {"bogp_adaptive", "bogp_replay"}.issubset(expected_methods):
        for seed in expected_seeds:
            adaptive = by_key.get(("bogp_adaptive", seed))
            replay = by_key.get(("bogp_replay", seed))
            missing_rows = [
                method
                for method, row in (("bogp_adaptive", adaptive), ("bogp_replay", replay))
                if row is None
            ]
            missing_hashes = {
                method: [column for column in HASH_COLUMNS if row is None or not str(row.get(column, "")).strip()]
                for method, row in (("bogp_adaptive", adaptive), ("bogp_replay", replay))
            }
            comparisons = {
                column: bool(adaptive and replay and str(adaptive.get(column, "")).strip() and str(replay.get(column, "")).strip())
                and adaptive.get(column) == replay.get(column)
                for column in HASH_COLUMNS
            }
            replay_checks.append(
                {
                    "seed": seed,
                    "missing_successful_rows": missing_rows,
                    "missing_required_hashes": missing_hashes,
                    "hash_matches": comparisons,
                    "all_required_hashes_present_and_match": not missing_rows and all(comparisons.values()),
                }
            )

    fixed_core_checks: list[dict[str, Any]] = []
    fixed_hash_columns = ("final_population_hash", "final_archive_hash")
    if {"fixed_standard", "fixed_core"}.issubset(expected_methods):
        for seed in expected_seeds:
            standard = by_key.get(("fixed_standard", seed))
            core = by_key.get(("fixed_core", seed))
            missing_rows = [
                method
                for method, row in (("fixed_standard", standard), ("fixed_core", core))
                if row is None
            ]
            missing_hashes = {
                method: [column for column in fixed_hash_columns if row is None or not str(row.get(column, "")).strip()]
                for method, row in (("fixed_standard", standard), ("fixed_core", core))
            }
            comparisons = {
                column: bool(standard and core and str(standard.get(column, "")).strip() and str(core.get(column, "")).strip())
                and standard.get(column) == core.get(column)
                for column in fixed_hash_columns
            }
            fixed_core_checks.append(
                {
                    "seed": seed,
                    "missing_successful_rows": missing_rows,
                    "missing_required_hashes": missing_hashes,
                    "hash_matches": comparisons,
                    "all_required_hashes_present_and_match": not missing_rows and all(comparisons.values()),
                }
            )

    methods_present = set(method_counts)
    expected_methods_missing = [method for method in expected_methods if method not in methods_present]

    checks_ok = (
        not duplicates
        and not expected_run_grid_issues
        and not k1_gate_issues
        and not nonfinite
        and not monotonic_issues
        and not duplicate_trace_generations
        and not missing_trace
        and not trace_completeness_issues
        and not final_hv_mismatches
        and not expectations["config_error"]
        and not expected_methods_missing
        and not schedule_match_issues
        and all(item["within_tolerance"] for item in accounting)
        and all(item["all_required_hashes_present_and_match"] for item in replay_checks)
        and all(item["all_required_hashes_present_and_match"] for item in fixed_core_checks)
    )
    return {
        "overall_ok": checks_ok,
        "inputs": {
            "run_summary": {"path": str(summary_path), "sha256": _sha256(summary_path), "rows": len(summary_rows)},
            "generation_trace": {"path": str(trace_path), "sha256": _sha256(trace_path), "rows": len(trace_rows)},
            "control_trace": {
                "path": str(control_trace_path),
                "sha256": _sha256(control_trace_path) if control_trace_path.exists() else None,
                "rows": len(control_trace_rows),
                "error": control_trace_error,
            },
        },
        "method_counts_all": dict(sorted(method_counts.items(), key=lambda item: _method_sort_key(item[0]))),
        "method_counts_successful": dict(sorted(successful_counts.items(), key=lambda item: _method_sort_key(item[0]))),
        "method_counts_failed_or_incomplete": dict(sorted(failed_counts.items(), key=lambda item: _method_sort_key(item[0]))),
        "experiment_expectations": expectations,
        "expected_methods_missing_from_summary": expected_methods_missing,
        "expected_successful_run_grid_issues": expected_run_grid_issues,
        "k1_gate_issues": k1_gate_issues,
        "duplicate_method_seed_rows": duplicates,
        "nonfinite_required_values": nonfinite,
        "trace_monotonicity_issues": monotonic_issues,
        "duplicate_trace_generations": duplicate_trace_generations,
        "successful_runs_missing_trace": missing_trace,
        "trace_completeness_issues": trace_completeness_issues,
        "summary_trace_final_hv_mismatches": final_hv_mismatches,
        "timing_accounting": accounting,
        "timing_accounting_note": "Only same-level timers are reconciled; nested timers must not be added to total time.",
        "hash_presence": hash_presence,
        "schedule_match_issues": schedule_match_issues,
        "adaptive_replay_hash_checks": replay_checks,
        "fixed_standard_core_hash_checks": fixed_core_checks,
    }


def _available_methods(records: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({str(record["method"]) for record in records}, key=_method_sort_key)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _plot_runtime_distribution(output_dir: Path, records: Sequence[Mapping[str, Any]]) -> None:
    methods = _available_methods(records)
    values = [[float(r["total_time_seconds"]) for r in records if r["method"] == method and _finite(float(r["total_time_seconds"]))] for method in methods]
    fig, ax = plt.subplots(figsize=(max(8.0, 1.3 * len(methods)), 5.2))
    if any(values):
        box = ax.boxplot(values, patch_artist=True, showmeans=True)
        for patch, method in zip(box["boxes"], methods):
            patch.set_facecolor(COLORS.get(method, "#888888"))
            patch.set_alpha(0.72)
    ax.set_xticks(range(1, len(methods) + 1), [METHOD_LABELS.get(m, m) for m in methods], rotation=22, ha="right")
    ax.set_ylabel("Total algorithm wall time [s]")
    ax.set_title("Runtime distribution across seeds")
    ax.grid(axis="y", alpha=0.25)
    _save(fig, output_dir / "runtime_distribution.png")


def _plot_component_breakdown(output_dir: Path, records: Sequence[Mapping[str, Any]]) -> None:
    methods = _available_methods(records)
    preferred = ("GP generation", "GP evolution excl. archive HV", "controller total", "controller propose", "GPR fit", "GPR predict", "candidate sampling", "expected improvement", "archive HV/state", "population diversity", "population HV", "reward")
    components = [name for name in preferred if any(_finite(float(r.get(f"component::{name}", math.nan))) for r in records)]
    fig, ax = plt.subplots(figsize=(max(9.0, 1.25 * len(methods)), 5.8))
    if components and methods:
        width = min(0.75 / len(components), 0.14)
        x = np.arange(len(methods), dtype=float)
        offsets = (np.arange(len(components)) - (len(components) - 1) / 2) * width
        for offset, component in zip(offsets, components):
            means = []
            for method in methods:
                vals = [float(r[f"component::{component}"]) for r in records if r["method"] == method and _finite(float(r[f"component::{component}"]))]
                means.append(float(np.mean(vals)) if vals else 0.0)
            ax.bar(x + offset, means, width=width, label=component)
        ax.set_xticks(x, [METHOD_LABELS.get(m, m) for m in methods], rotation=22, ha="right")
        ax.legend(fontsize=8, ncol=2)
    ax.set_ylabel("Mean measured component time [s]")
    ax.set_title("Measured timing components (some timers are nested)")
    ax.grid(axis="y", alpha=0.25)
    _save(fig, output_dir / "component_breakdown.png")


def _plot_quality_time(output_dir: Path, records: Sequence[Mapping[str, Any]]) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 5.5))
    for method in [item for item in _available_methods(records) if item in PRIMARY_ANALYSIS_METHODS]:
        selected = [r for r in records if r["method"] == method and _finite(float(r["total_time_seconds"])) and _finite(float(r["final_hv"]))]
        if not selected:
            continue
        times = np.asarray([float(r["total_time_seconds"]) for r in selected])
        hvs = np.asarray([float(r["final_hv"]) for r in selected])
        ax.errorbar(np.mean(times), np.mean(hvs), xerr=np.std(times, ddof=1) if times.size > 1 else 0, yerr=np.std(hvs, ddof=1) if hvs.size > 1 else 0, fmt="o", capsize=3, markersize=7, color=COLORS.get(method, "#777777"), label=METHOD_LABELS.get(method, method))
    ax.set_xlabel("Total algorithm wall time [s] (mean +/- SD)")
    ax.set_ylabel("Final archive hypervolume (mean +/- SD)")
    ax.set_title("Quality-time trade-off")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    _save(fig, output_dir / "quality_time_tradeoff.png")


def _step_value(points: Sequence[tuple[float, float]], time_value: float) -> float:
    value = math.nan
    for elapsed, hv in points:
        if elapsed > time_value:
            break
        value = hv
    return value


def _plot_hv_elapsed(output_dir: Path, trace: Mapping[tuple[str, int], Sequence[Mapping[str, str]]]) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    methods = sorted(
        {method for method, _ in trace if method in PRIMARY_ANALYSIS_METHODS},
        key=_method_sort_key,
    )
    for method in methods:
        seed_points: list[list[tuple[float, float]]] = []
        for (candidate, _), rows in trace.items():
            if candidate != method:
                continue
            points = [(_number(row, FIELD_ALIASES["elapsed"]), _number(row, FIELD_ALIASES["trace_hv"])) for row in rows]
            points = sorted((elapsed, hv) for elapsed, hv in points if _finite(elapsed) and _finite(hv))
            if points:
                seed_points.append(points)
        if not seed_points:
            continue
        endpoint = float(np.median([points[-1][0] for points in seed_points]))
        grid = np.linspace(0.0, endpoint, 160)
        matrix = np.asarray([[_step_value(points, t) for t in grid] for points in seed_points])
        valid_columns = np.any(np.isfinite(matrix), axis=0)
        if not np.any(valid_columns):
            continue
        grid = grid[valid_columns]
        matrix = matrix[:, valid_columns]
        with np.errstate(invalid="ignore"):
            center = np.nanmean(matrix, axis=0)
            lower = np.nanquantile(matrix, 0.25, axis=0)
            upper = np.nanquantile(matrix, 0.75, axis=0)
        color = COLORS.get(method, "#777777")
        ax.step(grid, center, where="post", color=color, label=METHOD_LABELS.get(method, method))
        ax.fill_between(grid, lower, upper, step="post", color=color, alpha=0.13)
    ax.set_xlabel("Elapsed algorithm wall time [s]")
    ax.set_ylabel("Archive hypervolume")
    ax.set_title("Anytime hypervolume (mean; shaded IQR)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    _save(fig, output_dir / "hv_vs_elapsed.png")


def _plot_paired(output_dir: Path, records: Sequence[Mapping[str, Any]], method_b: str, filename: str, title: str) -> None:
    by_key = {(str(r["method"]), int(r["seed"])): r for r in records}
    seeds = sorted({seed for method, seed in by_key if method == "bogp_adaptive"} & {seed for method, seed in by_key if method == method_b})
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6))
    for ax, metric, label in ((axes[0], "total_time_seconds", "Total wall time [s]"), (axes[1], "final_hv", "Final archive HV")):
        for seed in seeds:
            a = float(by_key[("bogp_adaptive", seed)][metric])
            b = float(by_key[(method_b, seed)][metric])
            if _finite(a) and _finite(b):
                ax.plot([0, 1], [a, b], color="#A0A0A0", alpha=0.45, linewidth=0.8)
                ax.scatter([0, 1], [a, b], c=[COLORS["bogp_adaptive"], COLORS.get(method_b, "#777777")], s=18)
        ax.set_xticks([0, 1], [METHOD_LABELS["bogp_adaptive"], METHOD_LABELS.get(method_b, method_b)], rotation=12)
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle(title)
    _save(fig, output_dir / filename)


def _summary_payload(
    records: Sequence[Mapping[str, Any]],
    aggregate: Sequence[Mapping[str, Any]],
    comparisons: Sequence[Mapping[str, Any]],
    anytime: Sequence[Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    aggregate_by_method = {str(row["method"]): row for row in aggregate}
    key_comparisons = [row for row in comparisons if row["method_a"] == "bogp_adaptive"]
    anytime_grouped: dict[str, list[float]] = defaultdict(list)
    for row in anytime:
        value = float(row["hv_at_budget"])
        if _finite(value):
            anytime_grouped[str(row["method"])].append(value)
    return {
        "analysis_design": {
            "primary_quality_metric": "final_archive_hypervolume",
            "primary_cost_metric": "total_algorithm_wall_seconds",
            "primary_comparison_methods": list(PRIMARY_ANALYSIS_METHODS),
            "timing_ablation_methods": ["fixed_core", "bogp_replay"],
            "anytime_budget": "Each seed's fixed_standard total algorithm wall time",
            "paired_difference_direction": "method_a minus method_b",
            "time_ratio_direction": "method_a divided by method_b",
            "multiple_testing_correction": "Holm across all reported Wilcoxon tests",
        },
        "n_valid_runs": len(records),
        "methods": aggregate_by_method,
        "adaptive_comparisons": key_comparisons,
        "mean_hv_at_fixed_standard_budget": {method: float(np.mean(values)) for method, values in anytime_grouped.items()},
        "validation_ok": bool(validation["overall_ok"]),
    }


def _write_markdown(path: Path, summary: Mapping[str, Any]) -> None:
    methods: Mapping[str, Mapping[str, Any]] = summary["methods"]
    lines = [
        "# 計算コスト実験の解析要約",
        "",
        f"- 有効run数: {summary['n_valid_runs']}",
        f"- 検証結果: {'OK' if summary['validation_ok'] else '要確認（validation_report.json参照）'}",
        "- 時間比較は対応seedを使い、比は `method_a / method_b` です。",
        "- 内部タイマには包含関係があるため、単純合計して総時間とはみなしません。",
        "- `fixed_core` と `bogp_replay` は追加コストを分離するtiming ablationであり、独立した性能比較手法ではありません。",
        "- 品質–時間図、HV–経過時間図、共通時間予算比較は、fixed 3条件・BOGP adaptive・BOGP k=1だけを対象にします。",
        "",
        "## 手法別集計",
        "",
        "| 手法 | n | 総時間 平均±SD [s] | 最終HV 平均±SD |",
        "|---|---:|---:|---:|",
    ]
    for method in sorted(methods, key=_method_sort_key):
        row = methods[method]
        lines.append(
            f"| {method} | {row['n_runs']} | {row['total_time_seconds_mean']:.6g} ± {row['total_time_seconds_std']:.3g} | {row['final_hv_mean']:.6g} ± {row['final_hv_std']:.3g} |"
        )
    lines.extend(["", "## BOGP adaptiveの対応比較", "", "| 比較対象 | 指標 | n | 平均差 | 95% bootstrap CI | 時間比 | Holm p |", "|---|---|---:|---:|---:|---:|---:|"])
    for row in summary["adaptive_comparisons"]:
        ratio = row["geometric_mean_ratio_a_over_b"]
        ratio_text = f"{ratio:.4g}" if isinstance(ratio, (int, float)) and _finite(float(ratio)) else "—"
        lines.append(
            f"| {row['method_b']} | {row['metric']} | {row['n_pairs']} | {row['mean_difference_a_minus_b']:.6g} | [{row['difference_bootstrap_ci95_low']:.6g}, {row['difference_bootstrap_ci95_high']:.6g}] | {ratio_text} | {row['p_value_holm']:.4g} |"
        )
    lines.extend(["", "## 解釈上の注意", "", "最終HVと総時間は別軸で判断してください。単一のHV/秒だけでは、途中性能や最終品質の差を隠す可能性があります。`hv_vs_elapsed.png` と `anytime_by_seed.csv` を併用します。", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def analyze_computation_cost(
    run_summary_path: str | Path,
    generation_trace_path: str | Path,
    output_dir: str | Path,
    *,
    bootstrap_samples: int = 10_000,
    bootstrap_seed: int = 20260731,
) -> dict[str, Path]:
    """Analyze experiment CSVs and return paths of generated artifacts."""

    summary_path = Path(run_summary_path).resolve()
    trace_path = Path(generation_trace_path).resolve()
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    summary_rows = _read_csv(summary_path)
    trace_rows = _read_csv(trace_path)
    trace = _trace_index(trace_rows)
    records = _run_records(summary_rows, trace)

    aggregate, aggregate_fields = aggregate_summary(records)
    comparisons = paired_comparisons(records, bootstrap_samples=bootstrap_samples, bootstrap_seed=bootstrap_seed)
    anytime = anytime_by_seed(records, trace)
    validation = validation_report(summary_path, trace_path, summary_rows, trace_rows)
    payload = _summary_payload(records, aggregate, comparisons, anytime, validation)

    paired_fields = [
        "comparison", "method_a", "method_b", "metric", "n_pairs", "mean_a", "mean_b",
        "mean_difference_a_minus_b", "difference_bootstrap_ci95_low", "difference_bootstrap_ci95_high",
        "median_difference_a_minus_b", "wins_a", "ties", "losses_a", "mean_log_ratio_a_over_b",
        "log_ratio_bootstrap_ci95_low", "log_ratio_bootstrap_ci95_high", "geometric_mean_ratio_a_over_b",
        "wilcoxon_statistic", "p_value_raw", "p_value_holm", "rank_biserial_a_minus_b",
    ]
    anytime_fields = [
        "seed", "method", "fixed_standard_budget_seconds", "hv_at_budget",
        "last_observed_elapsed_seconds", "last_observed_generation", "run_total_seconds",
        "run_completed_within_budget", "source",
    ]
    _write_csv(destination / "aggregate_summary.csv", aggregate, aggregate_fields)
    _write_csv(destination / "paired_comparisons.csv", comparisons, paired_fields)
    _write_csv(destination / "anytime_by_seed.csv", anytime, anytime_fields)
    _write_json(destination / "validation_report.json", validation)
    _write_json(destination / "analysis_summary.json", payload)
    _write_markdown(destination / "summary.md", payload)

    _plot_runtime_distribution(destination, records)
    _plot_component_breakdown(destination, records)
    _plot_quality_time(destination, records)
    _plot_hv_elapsed(destination, trace)
    _plot_paired(destination, records, "bogp_replay", "adaptive_vs_replay.png", "Adaptive BOGP vs replay (paired seeds)")
    _plot_paired(destination, records, "bogp_k1_matched", "adaptive_vs_k1.png", "Adaptive k vs k=1 BOGP (paired seeds)")

    names = (
        "aggregate_summary.csv", "paired_comparisons.csv", "anytime_by_seed.csv",
        "validation_report.json", "analysis_summary.json", "summary.md",
        "runtime_distribution.png", "component_breakdown.png", "quality_time_tradeoff.png",
        "hv_vs_elapsed.png", "adaptive_vs_replay.png", "adaptive_vs_k1.png",
    )
    return {name: destination / name for name in names}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize the BOGP computation-cost experiment.")
    parser.add_argument("--experiment-dir", type=Path, help="Directory containing run_summary.csv and generation_trace.csv")
    parser.add_argument("--run-summary", type=Path, help="Path to run_summary.csv")
    parser.add_argument("--generation-trace", type=Path, help="Path to generation_trace.csv")
    parser.add_argument("--output-dir", type=Path, help="Analysis output directory (default: EXPERIMENT_DIR/analysis)")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260731)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.experiment_dir:
        run_summary = args.run_summary or args.experiment_dir / "run_summary.csv"
        generation_trace = args.generation_trace or args.experiment_dir / "generation_trace.csv"
        output_dir = args.output_dir or args.experiment_dir / "analysis"
    else:
        if args.run_summary is None or args.generation_trace is None:
            raise SystemExit("Specify --experiment-dir, or both --run-summary and --generation-trace.")
        run_summary = args.run_summary
        generation_trace = args.generation_trace
        output_dir = args.output_dir or run_summary.parent / "analysis"
    if args.bootstrap_samples < 1:
        raise SystemExit("--bootstrap-samples must be at least 1")
    paths = analyze_computation_cost(
        run_summary,
        generation_trace,
        output_dir,
        bootstrap_samples=args.bootstrap_samples,
        bootstrap_seed=args.bootstrap_seed,
    )
    print(f"Analysis written to {Path(output_dir).resolve()}")
    for name in paths:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
