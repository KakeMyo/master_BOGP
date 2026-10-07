from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import warnings
from collections import Counter
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from bogp.computation_cost import (
    InstrumentedContextualBayesianRateController,
    InstrumentedMultiObjectiveGPEngine,
    MatchedWarmupK1Controller,
    ReplayController,
    run_timed_closed_loop,
    run_timed_fixed_core,
    run_timed_monitored_fixed,
)
from bogp.computation_cost_experiment import (
    METHOD_ORDER,
    CostExperimentConfig,
    CostWorkerSpec,
    balanced_method_order,
    compile_cost_outputs,
    run_cost_experiment_subprocesses,
    run_cost_worker,
)
import bogp.computation_cost_experiment as cost_experiment
from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.loop import ClosedLoopRunner
from bogp.objectives import RewardConfig
from bogp.runtime_timing import TimingRecorder
from bogp.test_v1_plain_gp_baseline import PlainGPBaselineConfig
from bogp.test_v1_template_problem import TemplateSymbolicRegressionProblem
from bogp.test_ver2_b_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from bogp.types import GPStateSnapshot


def make_context(generation: int, total_generations: int = 78) -> GPStateSnapshot:
    return GPStateSnapshot(
        generation=generation,
        total_generations=total_generations,
        hypervolume=0.25,
        recent_hv_delta=0.01,
        diversity=0.55,
        best_fitness=0.75,
        recent_best_improvement=0.01,
        stagnation_generations=1,
        mean_tree_size=9.0,
    )


def engine_config(seed: int = 17, total_generations: int = 3) -> MultiObjectiveGPConfig:
    return MultiObjectiveGPConfig(
        population_size=6,
        total_generations=total_generations,
        tournament_size=3,
        random_seed=seed,
        archive_size=40,
        archive_structure_key_mode="topology_value",
    )


def controller_config(seed: int = 23) -> BOControllerConfig:
    return BOControllerConfig(
        candidate_k_values=(1,),
        warmup_per_k=1,
        min_observations_per_k=1,
        candidate_pool_size_per_k=4,
        random_seed=seed,
    )


def evaluated_signature(engine) -> tuple[tuple[str, tuple[float, ...]], ...]:
    return tuple(
        (repr(item.individual), tuple(item.objective_values))
        for item in engine.evaluated_population
    )


def archive_signature(engine) -> tuple[tuple[str, tuple[float, ...]], ...]:
    return tuple(
        (repr(item.individual), tuple(item.objective_values))
        for item in engine.archive
    )


class TimingRecorderTests(unittest.TestCase):
    def test_nested_events_aggregate_by_ancestor_and_round_trip(self) -> None:
        recorder = TimingRecorder()
        with recorder.measure("outer", run=3):
            with recorder.measure("child", phase="first"):
                sum(index * index for index in range(100))
            with recorder.measure("child", phase="second"):
                with recorder.measure("grandchild"):
                    sum(range(100))

        events = recorder.events
        self.assertEqual([event.event_id for event in events], [0, 1, 2, 3])
        self.assertEqual([event.parent_event_id for event in events], [None, 0, 0, 2])
        self.assertGreaterEqual(events[0].wall_duration_ns, events[1].wall_duration_ns)
        self.assertGreaterEqual(events[0].cpu_duration_ns, events[1].cpu_duration_ns)

        child_totals = recorder.totals("child", ancestor_name="outer")
        self.assertEqual(child_totals["count"], 2)
        self.assertEqual(
            child_totals["wall_duration_ns"],
            events[1].wall_duration_ns + events[2].wall_duration_ns,
        )
        self.assertEqual(recorder.totals("outer", ancestor_name="outer")["count"], 0)

        serialized = recorder.to_dict()
        restored = TimingRecorder.from_dict(serialized)
        self.assertEqual(restored.to_dict(), serialized)
        self.assertEqual(json.loads(restored.to_json()), serialized)

    def test_failed_region_is_retained_without_suppressing_exception(self) -> None:
        recorder = TimingRecorder()
        with self.assertRaisesRegex(RuntimeError, "expected"):
            with recorder.measure("failure", seed=5):
                raise RuntimeError("expected")

        self.assertEqual(len(recorder.events), 1)
        self.assertEqual(recorder.events[0].metadata["seed"], 5)
        self.assertEqual(recorder.events[0].metadata["exception_type"], "RuntimeError")


class TrajectoryPreservationTests(unittest.TestCase):
    def test_instrumented_bogp_matches_production_and_replay_exactly(self) -> None:
        production_engine = MultiObjectiveGPEngine(
            TemplateSymbolicRegressionProblem(sample_count=15),
            engine_config(),
        )
        production_controller = ContextualBayesianRateController(controller_config())

        instrumented_engine = InstrumentedMultiObjectiveGPEngine(
            TemplateSymbolicRegressionProblem(sample_count=15),
            engine_config(),
        )
        instrumented_controller = InstrumentedContextualBayesianRateController(
            controller_config()
        )

        # The tiny data set can make sklearn report harmless kernel-bound
        # convergence warnings; they are unrelated to trajectory equality.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            production_records = ClosedLoopRunner(
                production_engine,
                production_controller,
                RewardConfig(),
            ).run()
            instrumented_result = run_timed_closed_loop(
                instrumented_engine,
                instrumented_controller,
                RewardConfig(),
            )

        self.assertEqual(list(instrumented_result.records), production_records)
        self.assertEqual(instrumented_result.timing_summary, {})
        self.assertEqual(
            instrumented_engine.generation_metrics_history,
            production_engine.generation_metrics_history,
        )
        self.assertEqual(
            evaluated_signature(instrumented_engine),
            evaluated_signature(production_engine),
        )
        self.assertEqual(
            archive_signature(instrumented_engine),
            archive_signature(production_engine),
        )

        event_names = [event.name for event in instrumented_engine.timing_recorder.events]
        self.assertIn("gpr_fit", event_names)
        self.assertIn("gpr_predict", event_names)
        self.assertIn("expected_improvement", event_names)
        self.assertEqual(event_names.count("controller_propose_total"), 3)

        replay_engine = InstrumentedMultiObjectiveGPEngine(
            TemplateSymbolicRegressionProblem(sample_count=15),
            engine_config(),
        )
        replay_controller = ReplayController.from_records(instrumented_result.records)
        replay_result = run_timed_closed_loop(
            replay_engine,
            replay_controller,
            RewardConfig(),
        )
        replay_controller.assert_exhausted()

        self.assertEqual(replay_result.records, instrumented_result.records)
        self.assertEqual(replay_result.timing_summary, {})
        self.assertEqual(
            evaluated_signature(replay_engine),
            evaluated_signature(instrumented_engine),
        )
        self.assertEqual(
            archive_signature(replay_engine),
            archive_signature(instrumented_engine),
        )
        replay_event_names = [event.name for event in replay_engine.timing_recorder.events]
        self.assertNotIn("gpr_fit", replay_event_names)
        self.assertEqual(replay_event_names.count("controller_propose_total"), 3)

    def test_monitored_and_core_fixed_gp_have_identical_final_search_state(self) -> None:
        monitored_engine = InstrumentedMultiObjectiveGPEngine(
            TemplateSymbolicRegressionProblem(sample_count=15),
            engine_config(seed=31, total_generations=4),
        )
        core_engine = InstrumentedMultiObjectiveGPEngine(
            TemplateSymbolicRegressionProblem(sample_count=15),
            engine_config(seed=31, total_generations=4),
        )
        baseline = PlainGPBaselineConfig(crossover_rate=0.80, mutation_rate=0.05)

        monitored_result = run_timed_monitored_fixed(monitored_engine, baseline)
        core_result = run_timed_fixed_core(core_engine, baseline)

        self.assertEqual(monitored_result.timing_summary, {})
        self.assertEqual(core_result.timing_summary, {})
        self.assertEqual(monitored_result.evaluations, core_result.evaluations)
        self.assertEqual(monitored_result.final_generation, core_result.final_generation)
        self.assertEqual(
            evaluated_signature(monitored_engine),
            evaluated_signature(core_engine),
        )
        self.assertEqual(
            archive_signature(monitored_engine),
            archive_signature(core_engine),
        )
        self.assertEqual(monitored_engine._rng.bit_generator.state, core_engine._rng.bit_generator.state)
        self.assertEqual(monitored_engine._hypervolume, core_engine._hypervolume)

        self.assertEqual(
            [point.generation for point in monitored_engine.generation_trace],
            [1, 2, 3, 4],
        )
        self.assertEqual(core_engine.generation_trace, ())
        self.assertEqual(
            core_engine.timing_recorder.totals(
                "external_snapshot", ancestor_name="total_algorithm"
            )["count"],
            0,
        )
        self.assertEqual(
            monitored_engine.timing_recorder.totals(
                "gp_generation_total", ancestor_name="total_algorithm"
            )["count"],
            4,
        )


class MatchedK1ControllerTests(unittest.TestCase):
    def test_common_warmup_is_preserved_then_k_is_forced_to_one(self) -> None:
        config_values = dict(
            candidate_k_values=(1, 3, 5),
            warmup_strategy="sequential",
            warmup_per_k=2,
            min_observations_per_k=2,
            candidate_pool_size_per_k=4,
            random_seed=43,
        )
        adaptive = InstrumentedContextualBayesianRateController(
            BOControllerConfig(**config_values)
        )
        matched = MatchedWarmupK1Controller(
            BOControllerConfig(**config_values),
            adaptive_until_generation=18,
        )

        generation = 0
        update_periods: list[int] = []
        for reward_index in range(6):
            context = make_context(generation)
            adaptive_control = adaptive.propose(context)
            matched_control = matched.propose(context)
            self.assertEqual(matched_control, adaptive_control)
            update_periods.append(matched_control.update_period)
            adaptive.register_observation(context, adaptive_control, float(reward_index))
            matched.register_observation(context, matched_control, float(reward_index))
            generation += matched_control.update_period

        self.assertEqual(update_periods, [1, 1, 3, 3, 5, 5])
        self.assertEqual(generation, 18)
        self.assertEqual(
            matched._valid_k_values(make_context(17)),
            adaptive._valid_k_values(make_context(17)),
        )
        self.assertEqual(matched._valid_k_values(make_context(18)), (1,))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            post_warmup = matched.propose(make_context(18))
        self.assertEqual(post_warmup.update_period, 1)


class BalancedMethodOrderTests(unittest.TestCase):
    def test_williams_order_balances_positions_and_directed_adjacencies(self) -> None:
        methods = tuple(METHOD_ORDER)
        sequences = [balanced_method_order(seed, methods) for seed in range(14)]

        for sequence in sequences:
            self.assertEqual(len(sequence), len(methods))
            self.assertEqual(set(sequence), set(methods))

        position_counts = Counter(
            (method, position)
            for sequence in sequences
            for position, method in enumerate(sequence)
        )
        expected_position_counts = {
            (method, position): 2
            for method in methods
            for position in range(len(methods))
        }
        self.assertEqual(position_counts, expected_position_counts)

        adjacency_counts = Counter(
            adjacent_pair
            for sequence in sequences
            for adjacent_pair in zip(sequence, sequence[1:])
        )
        expected_adjacency_counts = {
            pair: 2 for pair in permutations(methods, 2)
        }
        self.assertEqual(adjacency_counts, expected_adjacency_counts)

        self.assertEqual(
            sequences,
            [balanced_method_order(seed, methods) for seed in range(14)],
        )


class ResumeSafetyTests(unittest.TestCase):
    def test_non_resume_refuses_a_nonempty_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CostExperimentConfig(
                output_root=tmpdir,
                run_id="existing",
                setting_name="tiny",
                seeds=(0,),
                population_size=4,
                total_generations=1,
                methods=("fixed_standard",),
                resume=False,
            )
            config.output_dir.mkdir(parents=True)
            (config.output_dir / "unrelated.txt").write_text("occupied", encoding="utf-8")

            with mock.patch.object(
                cost_experiment,
                "collect_environment_metadata",
                return_value={},
            ):
                with self.assertRaisesRegex(FileExistsError, "nonempty"):
                    run_cost_experiment_subprocesses(
                        config,
                        worker_script=Path("unused_worker.py"),
                    )

    def test_resume_rejects_config_and_source_environment_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stored_config = CostExperimentConfig(
                output_root=tmpdir,
                run_id="resume",
                setting_name="tiny",
                seeds=(0,),
                population_size=4,
                total_generations=1,
                methods=("fixed_standard",),
                resume=False,
            )
            output_dir = stored_config.output_dir
            output_dir.mkdir(parents=True)
            (output_dir / "experiment_config.json").write_text(
                json.dumps(stored_config.to_dict()),
                encoding="utf-8",
            )
            stored_environment = {
                "platform": "test-platform",
                "python": "test-python",
                "source_files": [
                    {"path": "src/bogp/computation_cost.py", "sha256": "same"}
                ],
            }
            (output_dir / "environment.json").write_text(
                json.dumps(stored_environment),
                encoding="utf-8",
            )
            (output_dir / "run_order.csv").write_text("seed,method_name\n", encoding="utf-8")

            resume_config = replace(stored_config, resume=True)
            cost_experiment._validate_resume_directory(
                output_dir,
                resume_config,
                stored_environment,
            )

            with self.assertRaisesRegex(RuntimeError, "config differs"):
                cost_experiment._validate_resume_directory(
                    output_dir,
                    replace(resume_config, total_generations=2),
                    stored_environment,
                )

            changed_environment = dict(stored_environment)
            changed_environment["source_files"] = [
                {"path": "src/bogp/computation_cost.py", "sha256": "changed"}
            ]
            with self.assertRaisesRegex(RuntimeError, "source hashes"):
                cost_experiment._validate_resume_directory(
                    output_dir,
                    resume_config,
                    changed_environment,
                )

    def test_completed_worker_requires_all_artifacts_and_matching_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "source_control_records.jsonl"
            source_row = {
                "step_index": 0,
                "start_generation": 0,
                "end_generation": 1,
                "control": {
                    "crossover_rate": 0.80,
                    "mutation_rate": 0.05,
                    "update_period": 1,
                },
            }
            source_path.write_text(json.dumps(source_row) + "\n", encoding="utf-8")
            spec = CostWorkerSpec(
                output_dir=str(Path(tmpdir) / "output"),
                setting_name="tiny_g1",
                method_name="bogp_replay",
                seed=53,
                run_position=2,
                population_size=4,
                total_generations=1,
                tournament_size=2,
                archive_size=20,
                replay_control_records_path=str(source_path),
            )
            run_cost_worker(spec)
            self.assertTrue(cost_experiment._resume_worker_is_complete(spec))

            artifact_path = spec.run_dir / "generation_trace.jsonl"
            missing_path = spec.run_dir / "generation_trace.jsonl.missing"
            artifact_path.rename(missing_path)
            self.assertFalse(cost_experiment._resume_worker_is_complete(spec))
            missing_path.rename(artifact_path)

            required_artifact_names = (
                "worker_spec.json",
                "summary.json",
                "timing_events.jsonl",
                "generation_trace.jsonl",
                "control_trace.jsonl",
                "final_population_signature.json",
                "final_archive_signature.json",
            )
            for artifact_name in required_artifact_names:
                artifact = spec.run_dir / artifact_name
                original_bytes = artifact.read_bytes()
                artifact.write_bytes(b"")
                self.assertFalse(
                    cost_experiment._resume_worker_is_complete(spec),
                    msg=f"empty {artifact_name} must not be treated as complete",
                )
                artifact.write_bytes(original_bytes)

            for signature_name in (
                "final_population_signature.json",
                "final_archive_signature.json",
            ):
                signature_path = spec.run_dir / signature_name
                original_signature_text = signature_path.read_text(encoding="utf-8")
                corrupted_signature = json.loads(original_signature_text)
                corrupted_signature.append(
                    {"structure": "corrupted", "objectives": [9.0, 9.0]}
                )
                signature_path.write_text(
                    json.dumps(corrupted_signature),
                    encoding="utf-8",
                )
                self.assertFalse(cost_experiment._resume_worker_is_complete(spec))
                signature_path.write_text(original_signature_text, encoding="utf-8")

            control_path = spec.run_dir / "control_trace.jsonl"
            original_control_text = control_path.read_text(encoding="utf-8")
            corrupted_control = json.loads(original_control_text.splitlines()[0])
            corrupted_control["control"]["mutation_rate"] = 0.06
            control_path.write_text(
                json.dumps(corrupted_control) + "\n",
                encoding="utf-8",
            )
            self.assertFalse(cost_experiment._resume_worker_is_complete(spec))
            control_path.write_text(original_control_text, encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "worker spec differs"):
                cost_experiment._resume_worker_is_complete(
                    replace(spec, archive_size=21)
                )

            summary_path = spec.run_dir / "summary.json"
            original_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            mismatched_summary = dict(original_summary)
            mismatched_summary["run_position"] = 3
            summary_path.write_text(json.dumps(mismatched_summary), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "summary identity differs"):
                cost_experiment._resume_worker_is_complete(spec)
            summary_path.write_text(json.dumps(original_summary), encoding="utf-8")

            incomplete_summary = dict(original_summary)
            incomplete_summary["status"] = "failed"
            summary_path.write_text(json.dumps(incomplete_summary), encoding="utf-8")
            self.assertFalse(cost_experiment._resume_worker_is_complete(spec))
            summary_path.write_text(json.dumps(original_summary), encoding="utf-8")

            changed_source_row = dict(source_row)
            changed_source_row["control"] = dict(source_row["control"])
            changed_source_row["control"]["mutation_rate"] = 0.06
            source_path.write_text(
                json.dumps(changed_source_row) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "source schedule changed"):
                cost_experiment._resume_worker_is_complete(spec)


class CostWorkerSmokeTests(unittest.TestCase):
    def test_tiny_fixed_workers_write_complete_outputs_and_respect_timing_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summaries = {}
            traces = {}
            for run_position, method_name in enumerate(("fixed_standard", "fixed_core")):
                spec = CostWorkerSpec(
                    output_dir=tmpdir,
                    setting_name="tiny_g1",
                    method_name=method_name,
                    seed=47,
                    run_position=run_position,
                    population_size=4,
                    total_generations=1,
                    tournament_size=2,
                    archive_size=20,
                )
                summary = run_cost_worker(spec)
                summaries[method_name] = summary
                run_dir = spec.run_dir

                required_files = {
                    "worker_spec.json",
                    "summary.json",
                    "timing_events.jsonl",
                    "generation_trace.jsonl",
                    "control_trace.jsonl",
                    "final_population_signature.json",
                    "final_archive_signature.json",
                }
                self.assertEqual(
                    required_files,
                    {path.name for path in run_dir.iterdir()},
                )
                persisted_summary = json.loads(
                    (run_dir / "summary.json").read_text(encoding="utf-8")
                )
                self.assertEqual(persisted_summary, summary)
                self.assertEqual(summary["status"], "ok")
                self.assertEqual(summary["final_generation"], 1)
                self.assertEqual(summary["offspring_evaluations"], 4)
                self.assertEqual(summary["total_evaluations"], 8)
                self.assertEqual(summary["gp_generation_total_count"], 1)
                self.assertEqual(summary["controller_propose_total_count"], 0)
                self.assertGreater(summary["total_algorithm_wall_seconds"], 0.0)
                self.assertGreater(summary["search_wall_seconds"], 0.0)
                self.assertIn("search_region_wall_seconds", summary)
                self.assertIn("search_region_cpu_seconds", summary)
                self.assertEqual(summary["search_region_count"], 1)
                self.assertNotIn("search_count", summary)
                for clock in ("wall", "cpu"):
                    total = summary[f"total_algorithm_{clock}_seconds"]
                    initialization = summary[f"initialization_{clock}_seconds"]
                    search_loop = summary[f"search_{clock}_seconds"]
                    wrapper_residual = summary[
                        f"algorithm_outer_residual_{clock}_seconds"
                    ]
                    search_region = summary[f"search_region_{clock}_seconds"]
                    self.assertAlmostEqual(
                        total,
                        initialization + search_loop + wrapper_residual,
                        places=9,
                    )
                    self.assertLessEqual(
                        wrapper_residual,
                        0.0005,
                    )
                    self.assertLessEqual(wrapper_residual / total, 0.05)
                    self.assertGreaterEqual(search_loop, search_region)
                self.assertEqual(
                    (run_dir / "control_trace.jsonl").read_text(encoding="utf-8"),
                    "",
                )

                timing_events = [
                    json.loads(line)
                    for line in (run_dir / "timing_events.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
                event_names = [event["name"] for event in timing_events]
                self.assertEqual(event_names.count("total_algorithm_including_initialization"), 1)
                self.assertEqual(event_names.count("total_algorithm"), 1)
                self.assertEqual(event_names.count("postprocess_not_timed"), 1)
                postprocess_event = next(
                    event for event in timing_events if event["name"] == "postprocess_not_timed"
                )
                self.assertIsNone(postprocess_event["parent_event_id"])

                traces[method_name] = [
                    json.loads(line)
                    for line in (run_dir / "generation_trace.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
                self.assertEqual(
                    [row["generation"] for row in traces[method_name]],
                    [0, 1],
                )
                self.assertEqual(
                    [row["cumulative_evaluations"] for row in traces[method_name]],
                    [4, 8],
                )

            self.assertEqual(
                summaries["fixed_standard"]["final_population_hash"],
                summaries["fixed_core"]["final_population_hash"],
            )
            self.assertEqual(
                summaries["fixed_standard"]["final_archive_hash"],
                summaries["fixed_core"]["final_archive_hash"],
            )
            self.assertEqual(
                [row["online_observed"] for row in traces["fixed_standard"]],
                [True, True],
            )
            self.assertEqual(
                [row["online_observed"] for row in traces["fixed_core"]],
                [True, False],
            )

            # Manifest hashing must stream files rather than loading each
            # potentially large aggregate into memory in one read.
            with mock.patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("manifest hashing must be chunked"),
            ):
                compile_cost_outputs(Path(tmpdir))
            component_path = Path(tmpdir) / "component_times.csv"
            with component_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                component_rows = list(reader)
                self.assertTrue(
                    {
                        "event_id",
                        "parent_event_id",
                        "phase",
                        "within_timed_algorithm",
                        "within_search_algorithm",
                    }.issubset(set(reader.fieldnames or ()))
                )

            postprocess_rows = [
                row
                for row in component_rows
                if row["event_name"] == "postprocess_not_timed"
            ]
            self.assertEqual(len(postprocess_rows), 2)
            for row in postprocess_rows:
                self.assertEqual(row["phase"], "postprocess_not_timed")
                self.assertEqual(row["within_timed_algorithm"], "False")
                self.assertEqual(row["within_search_algorithm"], "False")


if __name__ == "__main__":
    unittest.main()
