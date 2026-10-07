from __future__ import annotations

import csv
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Callable, Iterable, Mapping, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .controller import BOControllerConfig, ContextualBayesianRateController
from .loop import ClosedLoopRunner
from .objectives import RewardConfig
from .symbolic_regression_alpha import SymbolicRegressionAlphaProblem
from .test_v1_plain_gp_baseline import PlainFixedRateGPRunner, PlainGPBaselineConfig
from .test_v1_problem import GPProblem
from .test_v1_structural_problem import StructuralSearchProblem
from .test_v1_template_problem import TemplateSymbolicRegressionProblem
from .test_ver2_b_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine


NOT_AVAILABLE = "not_available"


@dataclass(frozen=True)
class ProblemSpec:
    name: str
    factory: Callable[[], GPProblem]
    engine_factory: Callable[[GPProblem, MultiObjectiveGPConfig], MultiObjectiveGPEngine] = MultiObjectiveGPEngine
    run_artifact_writer: Callable[[MultiObjectiveGPEngine, Path], None] | None = None


@dataclass(frozen=True)
class FixedRateMethodConfig:
    name: str = "plain_fixed"
    crossover_rate: float = 0.80
    mutation_rate: float = 0.05


@dataclass(frozen=True)
class FormalExperimentConfig:
    problem_name: str = "template"
    seeds: tuple[int, ...] = (0,)
    population_size: int = 24
    total_generations: int = 30
    tournament_size: int = 3
    archive_size: int = 200
    hv_reference_point: tuple[float, float] = (1.0, 1.0)
    diversity_pair_sample_size: int | None = None
    objective_key_precision: int = 12
    archive_structure_key_mode: str = "topology_value"
    structure_value_precision: int = 8
    fixed_rate_methods: tuple[FixedRateMethodConfig, ...] = field(
        default_factory=lambda: (FixedRateMethodConfig(),)
    )
    include_bogp_current: bool = True
    bo_controller_overrides: Mapping[str, Any] = field(default_factory=dict)
    reward_overrides: Mapping[str, Any] = field(default_factory=dict)
    output_root: str = "outputs/formal_experiments"
    run_id: str | None = None


@dataclass(frozen=True)
class FormalExperimentResult:
    output_dir: Path
    summary_by_seed_path: Path
    aggregate_summary_path: Path
    run_summaries: tuple[dict[str, Any], ...]


@dataclass
class _RunArtifact:
    summary: dict[str, Any]
    generation_metrics: list[dict[str, Any]]
    unique_objective_archive: list[dict[str, Any]]
    control_records: list[dict[str, Any]]
    output_dir: Path
    objective_count: int
    objective_names: tuple[str, ...]


def registered_problem_specs() -> dict[str, ProblemSpec]:
    return {
        "template": ProblemSpec(
            name="template",
            factory=lambda: TemplateSymbolicRegressionProblem(),
        ),
        "structural": ProblemSpec(
            name="structural",
            factory=lambda: StructuralSearchProblem(max_initial_depth=3, time_steps=401),
        ),
        "sr_alpha_friedman": ProblemSpec(
            name="sr_alpha_friedman",
            factory=lambda: SymbolicRegressionAlphaProblem.friedman_i(),
        ),
        "sr_alpha_poly10": ProblemSpec(
            name="sr_alpha_poly10",
            factory=lambda: SymbolicRegressionAlphaProblem.poly10(),
        ),
    }


def run_registered_experiment(config: FormalExperimentConfig) -> FormalExperimentResult:
    registry = registered_problem_specs()
    if config.problem_name not in registry:
        available = ", ".join(sorted(registry))
        raise ValueError(
            f"Unknown problem_name '{config.problem_name}'. Available problems: {available}"
        )
    return run_problem_experiment(registry[config.problem_name], config)


def run_problem_experiment(
    problem_spec: ProblemSpec,
    config: FormalExperimentConfig,
) -> FormalExperimentResult:
    metadata_problem = problem_spec.factory()
    objective_names = tuple(objective.name for objective in metadata_problem.objectives)
    objective_count = len(objective_names)

    run_id = config.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_root) / problem_spec.name / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        output_dir / "config.json",
        {
            "problem_name": problem_spec.name,
            "objective_names": objective_names,
            "objective_count": objective_count,
            "config": config,
        },
    )

    artifacts: list[_RunArtifact] = []
    for seed in config.seeds:
        for method_config in config.fixed_rate_methods:
            artifacts.append(
                _run_plain_fixed(
                    problem_spec=problem_spec,
                    config=config,
                    method_config=method_config,
                    seed=int(seed),
                    objective_count=objective_count,
                    objective_names=objective_names,
                    output_dir=output_dir,
                )
            )

        if config.include_bogp_current:
            artifacts.append(
                _run_bogp_current(
                    problem_spec=problem_spec,
                    config=config,
                    seed=int(seed),
                    objective_count=objective_count,
                    objective_names=objective_names,
                    output_dir=output_dir,
                )
            )

    summary_rows = [artifact.summary for artifact in artifacts]
    summary_by_seed_path = output_dir / "summary_by_seed.csv"
    aggregate_summary_path = output_dir / "aggregate_summary.csv"
    _write_summary_by_seed(summary_by_seed_path, summary_rows)
    _write_aggregate_summary(aggregate_summary_path, summary_rows)
    _write_json(output_dir / "run_summaries.json", summary_rows)
    _plot_common_histories(output_dir, artifacts)
    _plot_pareto_fronts(output_dir, artifacts)

    return FormalExperimentResult(
        output_dir=output_dir,
        summary_by_seed_path=summary_by_seed_path,
        aggregate_summary_path=aggregate_summary_path,
        run_summaries=tuple(summary_rows),
    )


def _run_plain_fixed(
    problem_spec: ProblemSpec,
    config: FormalExperimentConfig,
    method_config: FixedRateMethodConfig,
    seed: int,
    objective_count: int,
    objective_names: tuple[str, ...],
    output_dir: Path,
) -> _RunArtifact:
    method_name = _safe_name(method_config.name)
    run_dir = output_dir / "runs" / method_name / f"seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    engine = problem_spec.engine_factory(
        problem_spec.factory(),
        _engine_config(config, seed),
    )
    runner = PlainFixedRateGPRunner(
        engine,
        PlainGPBaselineConfig(
            crossover_rate=method_config.crossover_rate,
            mutation_rate=method_config.mutation_rate,
        ),
    )

    started = time.perf_counter()
    records = runner.run()
    wall_time = time.perf_counter() - started
    evaluations = sum(record.evaluations for record in records)

    generation_metrics = _generation_metrics_rows(
        engine.generation_metrics_history,
        objective_count,
    )
    archive = _archive_to_dicts(engine.archive)
    unique_archive = _archive_to_dicts(engine.unique_objective_archive)
    control_records = _plain_control_records(records, objective_count)

    _write_jsonl(run_dir / "generation_metrics.jsonl", generation_metrics)
    _write_jsonl(run_dir / "control_records.jsonl", control_records)
    _write_json(run_dir / "pareto_archive.json", archive)
    _write_json(run_dir / "unique_objective_archive.json", unique_archive)
    if problem_spec.run_artifact_writer is not None:
        problem_spec.run_artifact_writer(engine, run_dir)

    final_metrics = generation_metrics[-1]
    final_record = records[-1]
    summary = _base_summary(
        problem_name=problem_spec.name,
        method_name=method_name,
        method_kind="plain_fixed",
        seed=seed,
        objective_count=objective_count,
        objective_names=objective_names,
        config=config,
        output_dir=run_dir,
        evaluations=evaluations,
        wall_time=wall_time,
        final_generation=final_record.generation,
        final_archive_hypervolume=final_metrics["archive_hypervolume"],
        final_population_hypervolume=final_metrics["population_hypervolume"],
        final_diversity=final_metrics["population_diversity"],
        control_steps=0,
        archive_stats=engine.archive_statistics(),
    )
    summary.update(
        {
            "crossover_rate": method_config.crossover_rate,
            "mutation_rate": method_config.mutation_rate,
        }
    )
    _write_json(run_dir / "summary.json", summary)
    return _RunArtifact(
        summary=summary,
        generation_metrics=generation_metrics,
        unique_objective_archive=unique_archive,
        control_records=control_records,
        output_dir=run_dir,
        objective_count=objective_count,
        objective_names=objective_names,
    )


def _run_bogp_current(
    problem_spec: ProblemSpec,
    config: FormalExperimentConfig,
    seed: int,
    objective_count: int,
    objective_names: tuple[str, ...],
    output_dir: Path,
) -> _RunArtifact:
    method_name = "bogp_current"
    run_dir = output_dir / "runs" / method_name / f"seed_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)

    engine = problem_spec.engine_factory(
        problem_spec.factory(),
        _engine_config(config, seed),
    )
    controller_kwargs = dict(config.bo_controller_overrides)
    controller_kwargs.setdefault("random_seed", seed)
    controller = ContextualBayesianRateController(BOControllerConfig(**controller_kwargs))
    reward_config = RewardConfig(**dict(config.reward_overrides))
    runner = ClosedLoopRunner(
        engine=engine,
        controller=controller,
        reward_config=reward_config,
    )

    started = time.perf_counter()
    records = runner.run()
    wall_time = time.perf_counter() - started
    evaluations = sum(record.evaluations for record in records)

    generation_metrics = _generation_metrics_rows(
        engine.generation_metrics_history,
        objective_count,
    )
    archive = _archive_to_dicts(engine.archive)
    unique_archive = _archive_to_dicts(engine.unique_objective_archive)
    control_records = _bogp_control_records(records, objective_count)

    _write_jsonl(run_dir / "generation_metrics.jsonl", generation_metrics)
    _write_jsonl(run_dir / "control_records.jsonl", control_records)
    _write_json(run_dir / "pareto_archive.json", archive)
    _write_json(run_dir / "unique_objective_archive.json", unique_archive)
    _plot_bogp_control_history(run_dir / "control_history.png", control_records)
    if problem_spec.run_artifact_writer is not None:
        problem_spec.run_artifact_writer(engine, run_dir)

    final_metrics = generation_metrics[-1]
    final_generation = engine.snapshot().generation
    summary = _base_summary(
        problem_name=problem_spec.name,
        method_name=method_name,
        method_kind="bogp_current",
        seed=seed,
        objective_count=objective_count,
        objective_names=objective_names,
        config=config,
        output_dir=run_dir,
        evaluations=evaluations,
        wall_time=wall_time,
        final_generation=final_generation,
        final_archive_hypervolume=final_metrics["archive_hypervolume"],
        final_population_hypervolume=final_metrics["population_hypervolume"],
        final_diversity=final_metrics["population_diversity"],
        control_steps=len(records),
        archive_stats=engine.archive_statistics(),
    )
    summary.update(
        {
            "bo_controller": BOControllerConfig(**controller_kwargs),
            "reward_config": reward_config,
        }
    )
    _write_json(run_dir / "summary.json", summary)
    return _RunArtifact(
        summary=summary,
        generation_metrics=generation_metrics,
        unique_objective_archive=unique_archive,
        control_records=control_records,
        output_dir=run_dir,
        objective_count=objective_count,
        objective_names=objective_names,
    )


def _engine_config(config: FormalExperimentConfig, seed: int) -> MultiObjectiveGPConfig:
    return MultiObjectiveGPConfig(
        population_size=config.population_size,
        total_generations=config.total_generations,
        tournament_size=config.tournament_size,
        random_seed=seed,
        archive_size=config.archive_size,
        hv_reference_point=config.hv_reference_point,
        diversity_pair_sample_size=config.diversity_pair_sample_size,
        objective_key_precision=config.objective_key_precision,
        archive_structure_key_mode=config.archive_structure_key_mode,
        structure_value_precision=config.structure_value_precision,
    )


def _base_summary(
    problem_name: str,
    method_name: str,
    method_kind: str,
    seed: int,
    objective_count: int,
    objective_names: tuple[str, ...],
    config: FormalExperimentConfig,
    output_dir: Path,
    evaluations: int,
    wall_time: float,
    final_generation: int,
    final_archive_hypervolume: Any,
    final_population_hypervolume: Any,
    final_diversity: float,
    control_steps: int,
    archive_stats: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "problem_name": problem_name,
        "method_name": method_name,
        "method_kind": method_kind,
        "seed": seed,
        "objective_count": objective_count,
        "objective_names": objective_names,
        "archive_structure_key_mode": config.archive_structure_key_mode,
        "final_generation": final_generation,
        "final_archive_hypervolume": final_archive_hypervolume,
        "final_population_hypervolume": final_population_hypervolume,
        "final_diversity": final_diversity,
        "control_steps": control_steps,
        "evaluations": evaluations,
        "wall_time_seconds": wall_time,
        "output_dir": str(output_dir),
        **dict(archive_stats),
    }


def _generation_metrics_rows(
    metrics: Sequence[Any],
    objective_count: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        row = asdict(metric)
        if objective_count != 2:
            row["archive_hypervolume"] = NOT_AVAILABLE
            row["population_hypervolume"] = NOT_AVAILABLE
        rows.append(row)
    return rows


def _plain_control_records(
    records: Sequence[Any],
    objective_count: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        hypervolume = record.hypervolume if objective_count == 2 else NOT_AVAILABLE
        rows.append(
            {
                "generation": record.generation,
                "control": {
                    "crossover_rate": record.crossover_rate,
                    "mutation_rate": record.mutation_rate,
                    "update_period": 1,
                },
                "archive_hypervolume": hypervolume,
                "diversity": record.diversity,
                "mean_tree_size": record.mean_tree_size,
                "stagnation_generations": record.stagnation_generations,
                "evaluations": record.evaluations,
            }
        )
    return rows


def _bogp_control_records(
    records: Sequence[Any],
    objective_count: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        start_hv = record.start_state.hypervolume if objective_count == 2 else NOT_AVAILABLE
        end_hv = record.end_state.hypervolume if objective_count == 2 else NOT_AVAILABLE
        rows.append(
            {
                "step_index": record.step_index,
                "start_generation": record.start_state.generation,
                "end_generation": record.end_state.generation,
                "control": {
                    "crossover_rate": record.control.crossover_rate,
                    "mutation_rate": record.control.mutation_rate,
                    "update_period": record.control.update_period,
                },
                "start_archive_hypervolume": start_hv,
                "end_archive_hypervolume": end_hv,
                "diversity": record.end_state.diversity,
                "evaluations": record.evaluations,
                "reward": {
                    "total": record.reward.total,
                    "hv_term": record.reward.hv_term,
                    "diversity_term": record.reward.diversity_term,
                    "control_cost": record.reward.control_cost,
                    "stagnation_penalty": record.reward.stagnation_penalty,
                    "bloat_penalty": record.reward.bloat_penalty,
                    "floor_penalty": record.reward.floor_penalty,
                    "target_diversity": record.reward.target_diversity,
                },
            }
        )
    return rows


def _archive_to_dicts(items: Sequence[Any]) -> list[dict[str, Any]]:
    return [
        {
            "objective_values": item.objective_values,
            "rank": item.rank,
            "crowding_distance": item.crowding_distance,
        }
        for item in items
    ]


def _write_summary_by_seed(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    fields = [
        "problem_name",
        "method_name",
        "method_kind",
        "seed",
        "objective_count",
        "archive_structure_key_mode",
        "final_generation",
        "final_archive_hypervolume",
        "final_population_hypervolume",
        "final_diversity",
        "control_steps",
        "evaluations",
        "wall_time_seconds",
        "archive_size",
        "archive_unique_objective_size",
        "archive_unique_structure_size",
        "archive_unique_pair_size",
        "output_dir",
    ]
    _write_csv(path, fields, rows)


def _write_aggregate_summary(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    numeric_metrics = [
        "final_archive_hypervolume",
        "final_population_hypervolume",
        "final_diversity",
        "control_steps",
        "evaluations",
        "wall_time_seconds",
        "archive_size",
        "archive_unique_objective_size",
        "archive_unique_structure_size",
        "archive_unique_pair_size",
    ]
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["problem_name"]),
            str(row["method_name"]),
            str(row["archive_structure_key_mode"]),
        )
        groups.setdefault(key, []).append(row)

    aggregate_rows: list[dict[str, Any]] = []
    for (problem_name, method_name, archive_mode), group_rows in sorted(groups.items()):
        for metric in numeric_metrics:
            values = [_as_numeric(row.get(metric)) for row in group_rows]
            numeric_values = [value for value in values if value is not None]
            aggregate_rows.append(
                {
                    "problem_name": problem_name,
                    "method_name": method_name,
                    "archive_structure_key_mode": archive_mode,
                    "metric": metric,
                    "seed_count": len(group_rows),
                    "value_count": len(numeric_values),
                    "mean": mean(numeric_values) if numeric_values else "",
                    "std": pstdev(numeric_values) if len(numeric_values) > 1 else 0.0
                    if numeric_values
                    else "",
                    "median": median(numeric_values) if numeric_values else "",
                    "best": _best_metric_value(metric, numeric_values),
                }
            )

    _write_csv(
        path,
        [
            "problem_name",
            "method_name",
            "archive_structure_key_mode",
            "metric",
            "seed_count",
            "value_count",
            "mean",
            "std",
            "median",
            "best",
        ],
        aggregate_rows,
    )


def _best_metric_value(metric: str, values: Sequence[float]) -> float | str:
    if not values:
        return ""
    if metric in {"evaluations", "wall_time_seconds", "control_steps"}:
        return min(values)
    return max(values)


def _plot_common_histories(output_dir: Path, artifacts: Sequence[_RunArtifact]) -> None:
    _plot_metric_history(
        output_dir / "hv_progress.png",
        artifacts,
        metric="archive_hypervolume",
        ylabel="Archive HV",
        title="Archive hypervolume by generation",
    )
    _plot_metric_history(
        output_dir / "diversity_progress.png",
        artifacts,
        metric="population_diversity",
        ylabel="Population diversity",
        title="Population diversity by generation",
    )
    _plot_metric_history(
        output_dir / "archive_size_progress.png",
        artifacts,
        metric="archive_size",
        ylabel="Archive size",
        title="Archive size by generation",
    )


def _plot_metric_history(
    path: Path,
    artifacts: Sequence[_RunArtifact],
    metric: str,
    ylabel: str,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    method_names = sorted({str(artifact.summary["method_name"]) for artifact in artifacts})
    seeds = sorted({int(artifact.summary["seed"]) for artifact in artifacts})
    color_cycle = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    method_colors = {
        method: color_cycle[index % len(color_cycle)] if color_cycle else None
        for index, method in enumerate(method_names)
    }
    seed_styles = ["-", "--", "-.", ":"]
    seed_markers = ["o", "s", "^", "D", "v", "P", "X"]
    seed_style_index = {seed: index for index, seed in enumerate(seeds)}
    plotted = False
    for artifact in artifacts:
        generations: list[int] = []
        values: list[float] = []
        for row in artifact.generation_metrics:
            value = _as_numeric(row.get(metric))
            if value is None:
                continue
            generations.append(int(row["generation"]))
            values.append(value)
        if not values:
            continue
        method_name = str(artifact.summary["method_name"])
        seed = int(artifact.summary["seed"])
        style_index = seed_style_index.get(seed, 0)
        ax.plot(
            generations,
            values,
            alpha=0.55,
            linewidth=1.5,
            color=method_colors.get(method_name),
            linestyle=seed_styles[style_index % len(seed_styles)],
            marker=seed_markers[style_index % len(seed_markers)],
            markersize=2.8,
            label=f"{method_name} (seed={seed})",
        )
        plotted = True

    if not plotted:
        plt.close(fig)
        return
    ax.set_xlabel("Generation")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(title="Method / seed", fontsize=8, title_fontsize=8, ncols=2)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_pareto_fronts(output_dir: Path, artifacts: Sequence[_RunArtifact]) -> None:
    seeds = sorted({int(artifact.summary["seed"]) for artifact in artifacts})
    for seed in seeds:
        seed_artifacts = [
            artifact
            for artifact in artifacts
            if int(artifact.summary["seed"]) == seed and artifact.objective_count == 2
        ]
        if not seed_artifacts:
            continue
        fig, ax = plt.subplots(figsize=(7.5, 5.8))
        plotted = False
        for artifact in seed_artifacts:
            values = [
                item["objective_values"]
                for item in artifact.unique_objective_archive
                if len(item["objective_values"]) == 2
            ]
            if not values:
                continue
            ax.scatter(
                [row[0] for row in values],
                [row[1] for row in values],
                s=36,
                alpha=0.75,
                label=artifact.summary["method_name"],
            )
            plotted = True
        if not plotted:
            plt.close(fig)
            continue
        objective_names = seed_artifacts[0].objective_names
        ax.set_xlabel(f"{objective_names[0]} objective")
        ax.set_ylabel(f"{objective_names[1]} objective")
        ax.set_title(f"Final unique-objective Pareto archive (seed={seed})")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / f"pareto_front_seed_{seed}.png", dpi=180)
        plt.close(fig)


def _plot_bogp_control_history(path: Path, control_records: Sequence[dict[str, Any]]) -> None:
    if not control_records:
        return
    fig, axes = plt.subplots(2, 1, figsize=(8.2, 6.2), sharex=True)
    end_generations = [int(record["end_generation"]) for record in control_records]
    controls = [record["control"] for record in control_records]
    axes[0].plot(
        end_generations,
        [control["crossover_rate"] for control in controls],
        marker="o",
        label="p_c",
    )
    axes[0].plot(
        end_generations,
        [control["mutation_rate"] for control in controls],
        marker="s",
        label="p_m",
    )
    axes[0].set_ylabel("Operator rate")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    for index, record in enumerate(control_records):
        control = record["control"]
        axes[1].hlines(
            control["update_period"],
            int(record["start_generation"]),
            int(record["end_generation"]),
            linewidth=2.4,
            label="k" if index == 0 else None,
        )
    axes[1].set_xlabel("Generation")
    axes[1].set_ylabel("Update period k")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_to_jsonable(row), ensure_ascii=False) + "\n")


def _write_csv(
    path: Path,
    fields: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field, "")) for field in fields})


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _csv_value(value: Any) -> Any:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(_to_jsonable(value), ensure_ascii=False)
    return value


def _as_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return safe or "method"
