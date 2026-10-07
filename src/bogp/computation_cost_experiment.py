from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from statistics import median
from time import perf_counter_ns, process_time_ns
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "1.0"

METHOD_ORDER = (
    "fixed_standard",
    "fixed_high_mutation",
    "fixed_high_crossover",
    "fixed_core",
    "bogp_adaptive",
    "bogp_replay",
    "bogp_k1_matched",
)

FIXED_RATES: dict[str, tuple[float, float]] = {
    "fixed_standard": (0.80, 0.05),
    "fixed_high_mutation": (0.70, 0.20),
    "fixed_high_crossover": (0.90, 0.05),
    "fixed_core": (0.80, 0.05),
}

THREAD_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "BLIS_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
}


@dataclass(frozen=True)
class CostWorkerSpec:
    output_dir: str
    setting_name: str
    method_name: str
    seed: int
    run_position: int
    population_size: int = 24
    total_generations: int = 78
    tournament_size: int = 3
    archive_size: int = 200
    hv_reference_point: tuple[float, float] = (1.0, 1.0)
    diversity_pair_sample_size: int | None = None
    objective_key_precision: int = 12
    archive_structure_key_mode: str = "topology_value"
    structure_value_precision: int = 8
    replay_control_records_path: str | None = None
    matched_warmup_generations: int = 18

    def __post_init__(self) -> None:
        if self.method_name not in METHOD_ORDER:
            raise ValueError(f"Unknown method_name: {self.method_name}")
        if self.population_size <= 0 or self.total_generations <= 0:
            raise ValueError("population_size and total_generations must be positive.")
        if self.method_name == "bogp_replay" and not self.replay_control_records_path:
            raise ValueError("bogp_replay requires replay_control_records_path.")

    @property
    def run_dir(self) -> Path:
        return Path(self.output_dir) / "runs" / self.method_name / f"seed_{self.seed}"

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CostWorkerSpec":
        kwargs = dict(value)
        kwargs["hv_reference_point"] = tuple(kwargs.get("hv_reference_point", (1.0, 1.0)))
        return cls(**kwargs)


@dataclass(frozen=True)
class CostExperimentConfig:
    output_root: str = "outputs/computation_cost_friedman"
    run_id: str = "cost_experiment"
    setting_name: str = "g78_main"
    seeds: tuple[int, ...] = tuple(range(20))
    population_size: int = 24
    total_generations: int = 78
    tournament_size: int = 3
    archive_size: int = 200
    replay_source_run: str | None = None
    methods: tuple[str, ...] = METHOD_ORDER
    matched_warmup_generations: int = 18
    resume: bool = False
    bootstrap_samples: int = 10000
    analysis_random_seed: int = 20260731
    extra_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.seeds:
            raise ValueError("At least one seed is required.")
        unknown = sorted(set(self.methods) - set(METHOD_ORDER))
        if unknown:
            raise ValueError(f"Unknown methods: {', '.join(unknown)}")
        if "bogp_replay" in self.methods and not self.replay_source_run:
            raise ValueError("replay_source_run is required when bogp_replay is enabled.")

    @property
    def output_dir(self) -> Path:
        return Path(self.output_root) / self.setting_name / self.run_id

    def worker_spec(self, method_name: str, seed: int, run_position: int) -> CostWorkerSpec:
        replay_path = None
        if self.replay_source_run and method_name in {
            "bogp_adaptive",
            "bogp_replay",
        }:
            replay_path = str(
                Path(self.replay_source_run)
                / "runs"
                / "bogp_current"
                / f"seed_{seed}"
                / "control_records.jsonl"
            )
        return CostWorkerSpec(
            output_dir=str(self.output_dir),
            setting_name=self.setting_name,
            method_name=method_name,
            seed=int(seed),
            run_position=int(run_position),
            population_size=self.population_size,
            total_generations=self.total_generations,
            tournament_size=self.tournament_size,
            archive_size=self.archive_size,
            replay_control_records_path=replay_path,
            matched_warmup_generations=self.matched_warmup_generations,
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(asdict(self))


def balanced_method_order(seed: int, methods: Sequence[str] = METHOD_ORDER) -> tuple[str, ...]:
    """Return a deterministic Williams-type balanced Latin-square order.

    Across ``2 * n`` consecutive seeds, every method occupies each position
    twice and every directed adjacent-method pair occurs twice.  This balances
    both run position and first-order thermal/cache carryover, which matters
    because the k=1 controller is systematically more expensive.
    """

    ordered = list(methods)
    if not ordered:
        return ()
    size = len(ordered)
    base_indices: list[int] = [0]
    for offset in range(1, size):
        if offset % 2 == 1:
            base_indices.append((offset + 1) // 2)
        else:
            base_indices.append(size - (offset // 2))
    label_shift = int(seed) % size
    sequence = [ordered[(index + label_shift) % size] for index in base_indices]
    if (int(seed) // size) % 2 == 1:
        sequence.reverse()
    return tuple(sequence)


def run_cost_experiment_subprocesses(
    config: CostExperimentConfig,
    worker_script: Path,
) -> None:
    """Run each method/seed in an isolated, single-threaded subprocess."""

    output_dir = config.output_dir
    order_rows: list[dict[str, Any]] = []
    for seed in config.seeds:
        order = balanced_method_order(seed, config.methods)
        for position, method_name in enumerate(order):
            order_rows.append(
                {
                    "setting_name": config.setting_name,
                    "seed": int(seed),
                    "run_position": position,
                    "method_name": method_name,
                }
            )

    current_environment = collect_environment_metadata()
    output_is_nonempty = output_dir.exists() and any(output_dir.iterdir())
    if output_is_nonempty:
        if not config.resume:
            raise FileExistsError(
                "Refusing to mix a new experiment with an existing nonempty "
                f"directory: {output_dir}. Use a new run id, or --resume only "
                "for an identical interrupted experiment."
            )
        _validate_resume_directory(output_dir, config, current_environment)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "experiment_config.json", config.to_dict())
        _write_json(output_dir / "environment.json", current_environment)
        _write_csv(output_dir / "run_order.csv", order_rows)

    specs_dir = output_dir / "worker_specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    worker_environment = os.environ.copy()
    worker_environment.update(THREAD_ENVIRONMENT)
    total_runs = len(order_rows)
    for run_index, row in enumerate(order_rows, start=1):
        spec = config.worker_spec(
            method_name=str(row["method_name"]),
            seed=int(row["seed"]),
            run_position=int(row["run_position"]),
        )
        summary_path = spec.run_dir / "summary.json"
        if config.resume and _resume_worker_is_complete(spec):
            print(
                f"[{run_index}/{total_runs}] skip {spec.method_name} seed={spec.seed}",
                flush=True,
            )
            continue

        spec_path = specs_dir / f"seed_{spec.seed}_{spec.method_name}.json"
        _write_json(spec_path, spec.to_dict())
        print(
            f"[{run_index}/{total_runs}] run {spec.method_name} seed={spec.seed}",
            flush=True,
        )
        subprocess.run(
            [sys.executable, str(worker_script), "--worker-spec", str(spec_path)],
            cwd=str(Path(__file__).resolve().parents[2]),
            env=worker_environment,
            check=True,
        )

    _write_json(output_dir / "timing_calibration.json", calibrate_timing_recorder())
    compile_cost_outputs(output_dir)


def _resume_config_signature(value: Mapping[str, Any]) -> dict[str, Any]:
    signature = dict(value)
    # Whether the current invocation is resuming is orchestration state, not an
    # experimental condition.  Every other config field must remain identical.
    signature.pop("resume", None)
    return _to_jsonable(signature)


def _resume_environment_signature(value: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "platform",
        "machine",
        "processor",
        "python",
        "thread_environment",
        "git_commit",
        "numpy",
        "scipy",
        "scikit_learn",
        "source_files",
    )
    return {key: _to_jsonable(value.get(key)) for key in keys}


def _validate_resume_directory(
    output_dir: Path,
    config: CostExperimentConfig,
    current_environment: Mapping[str, Any],
) -> None:
    config_path = output_dir / "experiment_config.json"
    environment_path = output_dir / "environment.json"
    run_order_path = output_dir / "run_order.csv"
    for required in (config_path, environment_path, run_order_path):
        if not required.is_file():
            raise RuntimeError(
                f"Cannot safely resume because provenance file is missing: {required}"
            )

    stored_config = _read_json(config_path)
    if _resume_config_signature(stored_config) != _resume_config_signature(
        config.to_dict()
    ):
        raise RuntimeError(
            "Cannot resume: the requested experiment config differs from the "
            f"stored config in {config_path}."
        )

    stored_environment = _read_json(environment_path)
    if _resume_environment_signature(stored_environment) != _resume_environment_signature(
        current_environment
    ):
        raise RuntimeError(
            "Cannot resume: source hashes, dependencies, interpreter, platform, "
            f"or thread settings differ from {environment_path}."
        )


def _schedule_hash_from_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    schedule = []
    for row in rows:
        schedule.append(
            {
                "step_index": int(row["step_index"]),
                "start_generation": int(row["start_generation"]),
                "end_generation": int(row["end_generation"]),
                "control": {
                    "crossover_rate": float(row["control"]["crossover_rate"]),
                    "mutation_rate": float(row["control"]["mutation_rate"]),
                    "update_period": int(row["control"]["update_period"]),
                },
            }
        )
    return stable_hash(schedule)


def _source_schedule_hash(path: Path) -> str:
    return _schedule_hash_from_rows(_read_jsonl(path))


def _resume_worker_is_complete(spec: CostWorkerSpec) -> bool:
    run_dir = spec.run_dir
    required_paths = (
        run_dir / "worker_spec.json",
        run_dir / "summary.json",
        run_dir / "timing_events.jsonl",
        run_dir / "generation_trace.jsonl",
        run_dir / "control_trace.jsonl",
        run_dir / "final_population_signature.json",
        run_dir / "final_archive_signature.json",
    )
    if not all(path.is_file() for path in required_paths):
        return False

    try:
        stored_spec = _read_json(run_dir / "worker_spec.json")
        summary = _read_json(run_dir / "summary.json")
        timing_rows = _read_jsonl(run_dir / "timing_events.jsonl")
        generation_rows = _read_jsonl(run_dir / "generation_trace.jsonl")
        control_rows = _read_jsonl(run_dir / "control_trace.jsonl")
        population_signature = _read_json(
            run_dir / "final_population_signature.json"
        )
        archive_signature = _read_json(run_dir / "final_archive_signature.json")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    if stored_spec != spec.to_dict():
        raise RuntimeError(
            "Cannot resume: stored worker spec differs for "
            f"{spec.method_name} seed={spec.seed}."
        )
    if summary.get("status") != "ok":
        return False
    if (
        summary.get("method_name") != spec.method_name
        or int(summary.get("seed", -1)) != spec.seed
        or int(summary.get("run_position", -1)) != spec.run_position
    ):
        raise RuntimeError(
            "Cannot resume: stored summary identity differs for "
            f"{spec.method_name} seed={spec.seed}."
        )

    event_names = {str(row.get("name", "")) for row in timing_rows}
    if not {
        "total_algorithm_including_initialization",
        "total_algorithm",
    }.issubset(event_names):
        return False
    expected_trace_rows = 2 if spec.method_name == "fixed_core" else (
        spec.total_generations + 1
    )
    if len(generation_rows) != expected_trace_rows:
        return False
    final_trace = generation_rows[-1]
    if (
        int(final_trace.get("generation", -1)) != spec.total_generations
        or int(final_trace.get("cumulative_evaluations", -1))
        != spec.population_size * (spec.total_generations + 1)
    ):
        return False
    if not isinstance(population_signature, list) or not isinstance(
        archive_signature, list
    ):
        return False
    if (
        stable_hash(population_signature) != summary.get("final_population_hash")
        or stable_hash(archive_signature) != summary.get("final_archive_hash")
    ):
        return False

    if spec.method_name.startswith("bogp_"):
        if not control_rows:
            return False
        if _schedule_hash_from_rows(control_rows) != summary.get(
            "control_schedule_hash"
        ):
            return False
    elif control_rows:
        return False

    if spec.replay_control_records_path:
        source_path = Path(spec.replay_control_records_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Replay control trace not found: {source_path}")
        current_source_hash = _source_schedule_hash(source_path)
        if summary.get("source_schedule_hash") != current_source_hash:
            raise RuntimeError(
                "Cannot resume: replay/adaptive source schedule changed for "
                f"{spec.method_name} seed={spec.seed}."
            )
    return True


def run_cost_worker(spec: CostWorkerSpec) -> dict[str, Any]:
    """Execute one isolated method/seed run and write its raw artifacts."""

    from .computation_cost import (
        InstrumentedContextualBayesianRateController,
        InstrumentedMultiObjectiveGPEngine,
        MatchedWarmupK1Controller,
        ReplayController,
        ReplayStep,
        run_timed_closed_loop,
        run_timed_fixed_core,
        run_timed_monitored_fixed,
    )
    from .controller import BOControllerConfig
    from .objectives import RewardConfig
    from .runtime_timing import TimingRecorder
    from .symbolic_regression_alpha import SymbolicRegressionAlphaProblem
    from .test_v1_plain_gp_baseline import PlainGPBaselineConfig
    from .test_ver2_b_mo_engine import MultiObjectiveGPConfig

    run_dir = spec.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    recorder = TimingRecorder()
    replay_steps: tuple[Any, ...] = ()
    source_schedule_hash = ""
    if spec.replay_control_records_path:
        replay_rows = _read_jsonl(Path(spec.replay_control_records_path))
        replay_steps = tuple(ReplayStep.from_dict(row) for row in replay_rows)
        source_schedule_hash = stable_hash([step.to_dict() for step in replay_steps])
        if replay_steps and replay_steps[-1].end_generation != spec.total_generations:
            raise ValueError(
                "Replay trace final generation does not match worker total_generations: "
                f"{replay_steps[-1].end_generation} != {spec.total_generations}"
            )

    origin_wall_ns = perf_counter_ns()
    controller: Any = None
    with recorder.measure(
        "total_algorithm_including_initialization",
        method_name=spec.method_name,
        seed=spec.seed,
    ):
        with recorder.measure("problem_engine_initialization"):
            problem = SymbolicRegressionAlphaProblem.friedman_i()
            engine = InstrumentedMultiObjectiveGPEngine(
                problem,
                MultiObjectiveGPConfig(
                    population_size=spec.population_size,
                    total_generations=spec.total_generations,
                    tournament_size=spec.tournament_size,
                    random_seed=spec.seed,
                    archive_size=spec.archive_size,
                    hv_reference_point=spec.hv_reference_point,
                    diversity_pair_sample_size=spec.diversity_pair_sample_size,
                    objective_key_precision=spec.objective_key_precision,
                    archive_structure_key_mode=spec.archive_structure_key_mode,
                    structure_value_precision=spec.structure_value_precision,
                ),
                recorder=recorder,
            )

        if spec.method_name in {
            "bogp_adaptive",
            "bogp_replay",
            "bogp_k1_matched",
        }:
            with recorder.measure("controller_initialization"):
                if spec.method_name == "bogp_replay":
                    controller = ReplayController(replay_steps)
                elif spec.method_name == "bogp_k1_matched":
                    controller = MatchedWarmupK1Controller(
                        BOControllerConfig(random_seed=spec.seed),
                        recorder=recorder,
                        adaptive_until_generation=spec.matched_warmup_generations,
                    )
                else:
                    controller = InstrumentedContextualBayesianRateController(
                        BOControllerConfig(random_seed=spec.seed),
                        recorder=recorder,
                    )

        initialization_elapsed_wall_ns = max(0, perf_counter_ns() - origin_wall_ns)
        engine.start_trace(origin_wall_ns, initial_evaluations=spec.population_size)

        if spec.method_name in FIXED_RATES:
            crossover_rate, mutation_rate = FIXED_RATES[spec.method_name]
            baseline_config = PlainGPBaselineConfig(
                crossover_rate=crossover_rate,
                mutation_rate=mutation_rate,
            )
            if spec.method_name == "fixed_core":
                result = run_timed_fixed_core(engine, baseline_config)
            else:
                result = run_timed_monitored_fixed(engine, baseline_config)
        else:
            result = run_timed_closed_loop(
                engine,
                controller,
                RewardConfig(),
            )

        if isinstance(controller, ReplayController):
            controller.assert_exhausted()

    total_end_wall_ns = perf_counter_ns()

    # Final metrics and artifact conversion are deliberately outside the
    # algorithm timer.  The monitored methods already computed the same final
    # values online; fixed_core computes them only here.
    with recorder.measure("postprocess_not_timed"):
        final_metric = engine._build_generation_metrics()
        archive_stats = engine.archive_statistics()
        population_signature = engine_population_signature(engine)
        archive_signature = engine_archive_signature(engine)
        control_rows = _control_trace_rows(spec, result.records)
        current_schedule = [
            {
                "step_index": row["step_index"],
                "start_generation": row["start_generation"],
                "end_generation": row["end_generation"],
                "control": row["control"],
            }
            for row in control_rows
            if "step_index" in row
        ]
        current_schedule_hash = stable_hash(current_schedule) if current_schedule else ""
        generation_rows = _generation_trace_rows(
            spec=spec,
            engine=engine,
            final_metric=final_metric,
            initialization_elapsed_wall_ns=initialization_elapsed_wall_ns,
            total_elapsed_wall_ns=max(0, total_end_wall_ns - origin_wall_ns),
        )

    timing = _timing_summary(recorder)
    metric_history = [asdict(item) for item in engine.generation_metrics_history]
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "setting_name": spec.setting_name,
        "problem_name": "sr_alpha_friedman",
        "method_name": spec.method_name,
        "method_kind": _method_kind(spec.method_name),
        "seed": spec.seed,
        "run_position": spec.run_position,
        "status": "ok",
        "population_size": spec.population_size,
        "total_generations": spec.total_generations,
        "final_generation": result.final_generation,
        "initial_evaluations": spec.population_size,
        "offspring_evaluations": result.evaluations,
        "total_evaluations": spec.population_size + result.evaluations,
        "control_steps": len(result.records) if spec.method_name.startswith("bogp_") else 0,
        "final_archive_hypervolume": final_metric.archive_hypervolume,
        "final_population_hypervolume": final_metric.population_hypervolume,
        "final_diversity": final_metric.population_diversity,
        "final_mean_tree_size": final_metric.mean_tree_size,
        **archive_stats,
        **timing,
        "final_population_hash": stable_hash(population_signature),
        "final_archive_hash": stable_hash(archive_signature),
        "generation_state_hash": stable_hash(metric_history),
        "control_schedule_hash": current_schedule_hash,
        "source_schedule_hash": source_schedule_hash,
        "schedule_matches_source": (
            current_schedule_hash == source_schedule_hash
            if spec.method_name in {"bogp_adaptive", "bogp_replay"} and source_schedule_hash
            else "not_applicable"
        ),
        "replay_source_path": spec.replay_control_records_path or "",
        "timing_scope": (
            "problem/engine/controller initialization plus search; excludes Python startup, "
            "imports, artifact serialization, plots, and post-hoc final metrics"
        ),
    }

    event_rows = []
    for event in recorder.events:
        row = event.to_dict()
        row.update(
            {
                "schema_version": SCHEMA_VERSION,
                "setting_name": spec.setting_name,
                "method_name": spec.method_name,
                "seed": spec.seed,
                "wall_seconds": event.wall_duration_seconds,
                "cpu_seconds": event.cpu_duration_seconds,
            }
        )
        event_rows.append(row)

    _write_json(run_dir / "worker_spec.json", spec.to_dict())
    _write_json(run_dir / "summary.json", summary)
    _write_jsonl(run_dir / "timing_events.jsonl", event_rows)
    _write_jsonl(run_dir / "generation_trace.jsonl", generation_rows)
    _write_jsonl(run_dir / "control_trace.jsonl", control_rows)
    _write_json(run_dir / "final_population_signature.json", population_signature)
    _write_json(run_dir / "final_archive_signature.json", archive_signature)
    return summary


def compile_cost_outputs(output_dir: Path) -> None:
    summaries: list[dict[str, Any]] = []
    generation_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []

    component_path = output_dir / "component_times.csv"
    component_path.parent.mkdir(parents=True, exist_ok=True)
    with component_path.open("w", encoding="utf-8", newline="") as component_handle:
        component_writer: csv.DictWriter | None = None
        for summary_path in sorted((output_dir / "runs").glob("*/seed_*/summary.json")):
            summary = _read_json(summary_path)
            summaries.append(summary)
            run_dir = summary_path.parent
            generation_rows.extend(_read_jsonl(run_dir / "generation_trace.jsonl"))
            control_rows.extend(_read_jsonl(run_dir / "control_trace.jsonl"))
            for component_row in _component_rows(summary, run_dir):
                if component_writer is None:
                    component_writer = csv.DictWriter(
                        component_handle,
                        fieldnames=list(component_row),
                    )
                    component_writer.writeheader()
                component_writer.writerow(
                    {
                        key: _csv_value(component_row.get(key))
                        for key in component_writer.fieldnames
                    }
                )

    _write_csv(output_dir / "run_summary.csv", summaries)
    _write_csv(output_dir / "generation_trace.csv", generation_rows)
    _write_csv(output_dir / "control_trace.csv", control_rows)
    _write_json(
        output_dir / "manifest.json",
        {
            "schema_version": SCHEMA_VERSION,
            "run_count": len(summaries),
            "files": _manifest_entries(output_dir),
        },
    )


def _method_kind(method_name: str) -> str:
    if method_name == "fixed_core":
        return "fixed_core_ablation"
    if method_name.startswith("fixed_"):
        return "fixed_monitored"
    if method_name == "bogp_replay":
        return "bogp_replay_ablation"
    if method_name == "bogp_k1_matched":
        return "bogp_k1_ablation"
    if method_name == "bogp_adaptive":
        return "bogp_adaptive"
    raise ValueError(f"Unknown method_name: {method_name}")


def _control_trace_rows(
    spec: CostWorkerSpec,
    records: Sequence[Any],
) -> list[dict[str, Any]]:
    """Serialize BOGP decisions with both nested and flat control columns."""

    if not spec.method_name.startswith("bogp_"):
        return []

    rows: list[dict[str, Any]] = []
    cumulative_evaluations = spec.population_size
    for record in records:
        cumulative_evaluations += int(record.evaluations)
        control = {
            "crossover_rate": float(record.control.crossover_rate),
            "mutation_rate": float(record.control.mutation_rate),
            "update_period": int(record.control.update_period),
        }
        reward = {
            "total": float(record.reward.total),
            "hv_term": float(record.reward.hv_term),
            "diversity_term": float(record.reward.diversity_term),
            "control_cost": float(record.reward.control_cost),
            "stagnation_penalty": float(record.reward.stagnation_penalty),
            "bloat_penalty": float(record.reward.bloat_penalty),
            "floor_penalty": float(record.reward.floor_penalty),
            "target_diversity": float(record.reward.target_diversity),
        }
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "setting_name": spec.setting_name,
                "method_name": spec.method_name,
                "seed": spec.seed,
                "run_position": spec.run_position,
                "step_index": int(record.step_index),
                "start_generation": int(record.start_state.generation),
                "end_generation": int(record.end_state.generation),
                "crossover_rate": control["crossover_rate"],
                "mutation_rate": control["mutation_rate"],
                "update_period": control["update_period"],
                "control": control,
                "start_archive_hypervolume": float(record.start_state.hypervolume),
                "end_archive_hypervolume": float(record.end_state.hypervolume),
                "end_diversity": float(record.end_state.diversity),
                "interval_evaluations": int(record.evaluations),
                "cumulative_evaluations": cumulative_evaluations,
                "reward_total": reward["total"],
                "reward": reward,
            }
        )
    return rows


def _generation_trace_rows(
    spec: CostWorkerSpec,
    engine: Any,
    final_metric: Any,
    initialization_elapsed_wall_ns: int,
    total_elapsed_wall_ns: int,
) -> list[dict[str, Any]]:
    """Join generation-completion clocks to the already-computed GP metrics.

    The monitored methods expose a genuine online point after each generation.
    ``fixed_core`` deliberately omits those observations, so it contains only
    the initialized state and a post-hoc final point explicitly marked as such.
    """

    metrics_by_generation = {
        int(metric.generation): metric
        for metric in engine.generation_metrics_history
    }
    metrics_by_generation[int(final_metric.generation)] = final_metric

    def row(
        metric: Any,
        elapsed_wall_ns: int,
        cumulative_evaluations: int,
        *,
        online_observed: bool,
    ) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "setting_name": spec.setting_name,
            "method_name": spec.method_name,
            "seed": spec.seed,
            "run_position": spec.run_position,
            "generation": int(metric.generation),
            "elapsed_wall_ns": int(max(0, elapsed_wall_ns)),
            "elapsed_wall_seconds": max(0, elapsed_wall_ns) / 1_000_000_000.0,
            "cumulative_evaluations": int(cumulative_evaluations),
            "archive_hypervolume": float(metric.archive_hypervolume),
            "population_hypervolume": float(metric.population_hypervolume),
            "population_diversity": float(metric.population_diversity),
            "mean_tree_size": float(metric.mean_tree_size),
            "stagnation_generations": int(metric.stagnation_generations),
            "archive_size": int(metric.archive_size),
            "archive_unique_objective_size": int(
                metric.archive_unique_objective_size
            ),
            "archive_unique_structure_size": int(
                metric.archive_unique_structure_size
            ),
            "archive_unique_pair_size": int(metric.archive_unique_pair_size),
            "online_observed": bool(online_observed),
        }

    initial_metric = metrics_by_generation.get(0)
    if initial_metric is None:
        raise AssertionError("Generation-zero metrics are missing.")
    rows = [
        row(
            initial_metric,
            initialization_elapsed_wall_ns,
            spec.population_size,
            online_observed=True,
        )
    ]

    if spec.method_name == "fixed_core":
        rows.append(
            row(
                final_metric,
                total_elapsed_wall_ns,
                spec.population_size * (spec.total_generations + 1),
                online_observed=False,
            )
        )
        return rows

    for trace_point in engine.generation_trace:
        generation = int(trace_point.generation)
        if generation == 0:
            continue
        metric = metrics_by_generation.get(generation)
        if metric is None:
            raise AssertionError(f"Metrics missing for generation {generation}.")
        rows.append(
            row(
                metric,
                trace_point.elapsed_wall_ns,
                trace_point.cumulative_evaluations,
                online_observed=True,
            )
        )

    expected_generations = list(range(spec.total_generations + 1))
    observed_generations = [int(item["generation"]) for item in rows]
    if observed_generations != expected_generations:
        raise AssertionError(
            "Incomplete monitored generation trace: "
            f"expected {expected_generations}, received {observed_generations}."
        )
    return rows


def _timing_summary(recorder: Any) -> dict[str, Any]:
    """Create hierarchical, non-overlapping timing summaries.

    Component durations are inclusive at their own hierarchy.  Residual fields
    are provided only between direct conceptual layers so nested quantities are
    never presented as if they were additive peers.
    """

    def totals(name: str, *, search_only: bool = False) -> dict[str, Any]:
        return recorder.totals(
            name,
            ancestor_name="total_algorithm" if search_only else None,
        )

    outer = totals("total_algorithm_including_initialization")
    search_loop = totals("total_algorithm")
    problem_init = totals("problem_engine_initialization")
    controller_init = totals("controller_initialization")

    component_names = (
        "external_snapshot",
        "engine_interval",
        "gp_generation_total",
        "archive_hv_state",
        "population_diversity",
        "population_hv",
        "controller_propose_total",
        "controller_propose",
        "candidate_sampling",
        "gpr_fit",
        "gpr_predict",
        "expected_improvement",
        "reward",
        "controller_register_total",
        "controller_register",
    )
    components = {
        name: totals(name, search_only=True)
        for name in component_names
    }
    search_regions = totals("search", search_only=True)

    events = recorder.events
    by_id = {event.event_id: event for event in events}
    outer_ids = {
        event.event_id
        for event in events
        if event.name == "total_algorithm_including_initialization"
    }
    search_ids = {
        event.event_id for event in events if event.name == "total_algorithm"
    }

    def belongs_to(event: Any, root_ids: set[int]) -> bool:
        event_id = event.event_id
        while True:
            if event_id in root_ids:
                return True
            parent_id = by_id[event_id].parent_event_id
            if parent_id is None or parent_id not in by_id:
                return False
            event_id = parent_id

    events_in_outer = sum(belongs_to(event, outer_ids) for event in events)
    events_in_search = sum(belongs_to(event, search_ids) for event in events)

    result: dict[str, Any] = {
        "timing_clock_wall": "time.perf_counter_ns",
        "timing_clock_cpu": "time.process_time_ns",
        "timing_event_count_in_algorithm": events_in_outer,
        "timing_event_count_in_search": events_in_search,
        "timing_event_count_total_trace": len(events),
        "total_algorithm_wall_seconds": outer["wall_duration_seconds"],
        "total_algorithm_cpu_seconds": outer["cpu_duration_seconds"],
        "search_wall_seconds": search_loop["wall_duration_seconds"],
        "search_cpu_seconds": search_loop["cpu_duration_seconds"],
        "initialization_wall_seconds": (
            problem_init["wall_duration_seconds"]
            + controller_init["wall_duration_seconds"]
        ),
        "initialization_cpu_seconds": (
            problem_init["cpu_duration_seconds"]
            + controller_init["cpu_duration_seconds"]
        ),
        "problem_engine_initialization_wall_seconds": problem_init[
            "wall_duration_seconds"
        ],
        "problem_engine_initialization_cpu_seconds": problem_init[
            "cpu_duration_seconds"
        ],
        "controller_initialization_wall_seconds": controller_init[
            "wall_duration_seconds"
        ],
        "controller_initialization_cpu_seconds": controller_init[
            "cpu_duration_seconds"
        ],
        "search_region_wall_seconds": search_regions["wall_duration_seconds"],
        "search_region_cpu_seconds": search_regions["cpu_duration_seconds"],
        "search_region_count": search_regions["count"],
    }
    for name, values in components.items():
        result[f"{name}_wall_seconds"] = values["wall_duration_seconds"]
        result[f"{name}_cpu_seconds"] = values["cpu_duration_seconds"]
        result[f"{name}_count"] = values["count"]

    for clock in ("wall", "cpu"):
        suffix = f"{clock}_seconds"

        def value(name: str) -> float:
            return float(result[f"{name}_{suffix}"])

        controller_total = value("controller_propose_total") + value(
            "controller_register_total"
        )
        result[f"controller_total_{suffix}"] = controller_total
        result[f"bo_control_path_{suffix}"] = controller_total + value("reward")

        result[f"algorithm_outer_residual_{suffix}"] = max(
            0.0,
            float(result[f"total_algorithm_{suffix}"])
            - float(result[f"initialization_{suffix}"])
            - float(result[f"search_{suffix}"]),
        )
        result[f"search_loop_residual_{suffix}"] = max(
            0.0,
            float(result[f"search_{suffix}"])
            - value("external_snapshot")
            - float(result[f"search_region_{suffix}"])
            - value("controller_propose_total")
            - value("reward")
            - value("controller_register_total"),
        )
        result[f"engine_interval_residual_{suffix}"] = max(
            0.0,
            value("engine_interval") - value("gp_generation_total"),
        )
        result[f"gp_evolution_without_archive_hv_{suffix}"] = max(
            0.0,
            value("gp_generation_total") - value("archive_hv_state"),
        )
        result[f"controller_propose_residual_{suffix}"] = max(
            0.0,
            value("controller_propose_total")
            - value("candidate_sampling")
            - value("gpr_fit")
            - value("gpr_predict")
            - value("expected_improvement"),
        )
        total_algorithm = float(result[f"total_algorithm_{suffix}"])
        result[f"controller_fraction_{clock}"] = (
            controller_total / total_algorithm if total_algorithm > 0.0 else 0.0
        )

    return result


def _component_rows(summary: Mapping[str, Any], run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    events_path = run_dir / "timing_events.jsonl"
    events = _read_jsonl(events_path)
    by_id = {int(event["event_id"]): event for event in events}

    def ancestor_names(event: Mapping[str, Any]) -> set[str]:
        names: set[str] = set()
        parent_id = event.get("parent_event_id")
        while parent_id is not None:
            parent = by_id.get(int(parent_id))
            if parent is None:
                break
            names.add(str(parent.get("name", "")))
            parent_id = parent.get("parent_event_id")
        return names

    for event in events:
        ancestors = ancestor_names(event)
        event_name = str(event.get("name", ""))
        within_search = (
            event_name == "total_algorithm" or "total_algorithm" in ancestors
        )
        within_timed_algorithm = (
            event_name == "total_algorithm_including_initialization"
            or "total_algorithm_including_initialization" in ancestors
        )
        if within_search:
            phase = "search"
        elif (
            event_name in {
                "problem_engine_initialization",
                "controller_initialization",
            }
            or ancestors.intersection(
                {"problem_engine_initialization", "controller_initialization"}
            )
        ):
            phase = "initialization"
        elif (
            event_name == "postprocess_not_timed"
            or "postprocess_not_timed" in ancestors
        ):
            phase = "postprocess_not_timed"
        elif within_timed_algorithm:
            phase = "timed_wrapper"
        else:
            phase = "harness_not_timed"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "setting_name": summary.get("setting_name"),
                "method_name": summary.get("method_name"),
                "seed": summary.get("seed"),
                "run_position": summary.get("run_position"),
                "event_id": event.get("event_id"),
                "parent_event_id": event.get("parent_event_id"),
                "event_name": event_name,
                "phase": phase,
                "within_timed_algorithm": within_timed_algorithm,
                "within_search_algorithm": within_search,
                "start_wall_ns": event.get("start_wall_ns"),
                "end_wall_ns": event.get("end_wall_ns"),
                "wall_duration_ns": event.get("wall_duration_ns"),
                "start_cpu_ns": event.get("start_cpu_ns"),
                "end_cpu_ns": event.get("end_cpu_ns"),
                "cpu_duration_ns": event.get("cpu_duration_ns"),
                "wall_seconds": event.get("wall_seconds", 0.0),
                "cpu_seconds": event.get("cpu_seconds", 0.0),
                "metadata": event.get("metadata", {}),
            }
        )
    return rows


def collect_environment_metadata() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    metadata: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
        "thread_environment": dict(THREAD_ENVIRONMENT),
        "git_commit": _command_output(["git", "rev-parse", "HEAD"], root),
        "git_status_short": _command_output(["git", "status", "--short"], root),
    }
    try:
        import numpy
        import scipy
        import sklearn

        metadata.update(
            {
                "numpy": numpy.__version__,
                "scipy": scipy.__version__,
                "scikit_learn": sklearn.__version__,
            }
        )
    except Exception as exc:  # pragma: no cover - metadata is best effort.
        metadata["dependency_error"] = repr(exc)
    try:
        from threadpoolctl import threadpool_info

        metadata["threadpool_info"] = threadpool_info()
    except Exception as exc:  # pragma: no cover - metadata is best effort.
        metadata["threadpool_error"] = repr(exc)
    metadata["source_files"] = _source_file_hashes(root)
    return metadata


def calibrate_timing_recorder(
    events_per_repeat: int = 10_000,
    repeats: int = 7,
) -> dict[str, Any]:
    """Estimate gross no-op event-recording overhead after the experiment.

    The estimate is diagnostic only and is not subtracted from measured run
    times.  Subtraction would inject calibration noise into small component
    timings; event counts and this upper-bound-like estimate instead make
    sub-percent conclusions auditable.
    """

    from .runtime_timing import TimingRecorder

    if events_per_repeat <= 0 or repeats <= 0:
        raise ValueError("Calibration sizes must be positive.")
    wall_samples: list[float] = []
    cpu_samples: list[float] = []
    for _ in range(repeats):
        recorder = TimingRecorder()
        start_wall_ns = perf_counter_ns()
        start_cpu_ns = process_time_ns()
        for _event_index in range(events_per_repeat):
            with recorder.measure("calibration_noop"):
                pass
        elapsed_cpu_ns = process_time_ns() - start_cpu_ns
        elapsed_wall_ns = perf_counter_ns() - start_wall_ns
        wall_samples.append(elapsed_wall_ns / float(events_per_repeat))
        cpu_samples.append(elapsed_cpu_ns / float(events_per_repeat))

    return {
        "schema_version": SCHEMA_VERSION,
        "calibration": "gross_noop_TimingRecorder.measure_overhead",
        "events_per_repeat": events_per_repeat,
        "repeats": repeats,
        "wall_ns_per_event_samples": wall_samples,
        "cpu_ns_per_event_samples": cpu_samples,
        "median_wall_ns_per_event": median(wall_samples),
        "median_cpu_ns_per_event": median(cpu_samples),
        "subtracted_from_run_times": False,
        "interpretation": (
            "Diagnostic gross overhead only. Multiply by each run's "
            "timing_event_count_in_algorithm for a conservative scale check; "
            "do not treat it as an exact correction."
        ),
    }


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        _to_jsonable(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def engine_population_signature(engine: Any) -> list[dict[str, Any]]:
    return [_evaluated_signature(engine, item) for item in engine.evaluated_population]


def engine_archive_signature(engine: Any) -> list[dict[str, Any]]:
    return [_evaluated_signature(engine, item) for item in engine.archive]


def _evaluated_signature(engine: Any, item: Any) -> dict[str, Any]:
    return {
        "structure": repr(engine._structure_key(item)),
        "objectives": [float(value) for value in item.objective_values],
    }


def _source_file_hashes(root: Path) -> list[dict[str, str]]:
    paths = sorted((root / "src" / "bogp").glob("*.py"))
    paths.extend(
        [
            root / "scripts" / "run_computation_cost_experiment.py",
            root / "scripts" / "summarize_computation_cost_experiment.py",
        ]
    )
    result: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        result.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": _file_sha256(path),
            }
        )
    return result


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_entries(output_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.name == "manifest.json":
            continue
        entries.append(
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    return entries


def _command_output(command: Sequence[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(
            list(command),
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return repr(exc)
    return completed.stdout.strip() or completed.stderr.strip()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            _to_jsonable(value),
            handle,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    _to_jsonable(dict(row)),
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                )
                + "\n"
            )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(str(key))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: _csv_value(row.get(key))
                    for key in fieldnames
                }
            )


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return value


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        try:
            return _to_jsonable(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return "nan"
    return value


__all__ = [
    "CostExperimentConfig",
    "CostWorkerSpec",
    "FIXED_RATES",
    "METHOD_ORDER",
    "SCHEMA_VERSION",
    "THREAD_ENVIRONMENT",
    "balanced_method_order",
    "calibrate_timing_recorder",
    "collect_environment_metadata",
    "compile_cost_outputs",
    "engine_archive_signature",
    "engine_population_signature",
    "run_cost_experiment_subprocesses",
    "run_cost_worker",
    "stable_hash",
]
