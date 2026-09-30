"""Trajectory-preserving instrumentation for BOGP computation-cost studies.

The instrumented classes add clock reads only: all random draws, model fits,
and GP operations retain the ordering of the production implementations.  The
``fixed_core`` runner intentionally omits per-generation observation metrics;
it is therefore a timing ablation, not the primary fixed-GP comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Iterable, List, Mapping, Optional

import numpy as np
from scipy.stats import norm

from .controller import BOControllerConfig, ContextualBayesianRateController
from .loop import ClosedLoopRecord, ClosedLoopRunner
from .objectives import RewardConfig, compute_reward
from .runtime_timing import TimingRecorder
from .test_v1_plain_gp_baseline import PlainGPBaselineConfig, PlainGPGenerationRecord
from .test_ver2_b_mo_engine import MultiObjectiveGPConfig, MultiObjectiveGPEngine
from .types import ControlInput, GPStateSnapshot


@dataclass(frozen=True)
class GenerationTracePoint:
    """Completion time and cumulative evaluation count for one generation."""

    generation: int
    elapsed_wall_ns: int
    cumulative_evaluations: int

    def to_dict(self) -> dict[str, int]:
        return {
            "generation": self.generation,
            "elapsed_wall_ns": self.elapsed_wall_ns,
            "cumulative_evaluations": self.cumulative_evaluations,
        }


class InstrumentedMultiObjectiveGPEngine(MultiObjectiveGPEngine):
    """Version-2b GP engine with nested component timers and progress trace."""

    def __init__(
        self,
        problem,
        config: MultiObjectiveGPConfig | None = None,
        recorder: TimingRecorder | None = None,
    ) -> None:
        self.timing_recorder = recorder or TimingRecorder()
        self._trace_origin_wall_ns: int | None = None
        self._trace_evaluations = 0
        self._generation_trace: list[GenerationTracePoint] = []
        super().__init__(problem, config)

    @property
    def generation_trace(self) -> tuple[GenerationTracePoint, ...]:
        """Generation completion trace established by :meth:`start_trace`."""

        return tuple(self._generation_trace)

    @property
    def trace_started(self) -> bool:
        """Whether an external or runner-owned generation trace is active."""

        return self._trace_origin_wall_ns is not None

    def start_trace(self, origin_wall_ns: int, initial_evaluations: int) -> None:
        """Start (or reset) wall-time/evaluation progress tracing.

        ``origin_wall_ns`` should come from :func:`time.perf_counter_ns` in the
        current process.  ``initial_evaluations`` normally equals population
        size because construction evaluates the initial population.
        """

        if isinstance(origin_wall_ns, bool) or int(origin_wall_ns) != origin_wall_ns:
            raise ValueError("origin_wall_ns must be a nonnegative integer.")
        if isinstance(initial_evaluations, bool) or int(initial_evaluations) != initial_evaluations:
            raise ValueError("initial_evaluations must be a nonnegative integer.")
        if origin_wall_ns < 0 or initial_evaluations < 0:
            raise ValueError("Trace origin and initial evaluations must be nonnegative.")
        self._trace_origin_wall_ns = int(origin_wall_ns)
        self._trace_evaluations = int(initial_evaluations)
        self._generation_trace = []

    def run_interval(
        self,
        control: ControlInput,
        interval_generations: int | None = None,
    ):
        with self.timing_recorder.measure(
            "engine_interval",
            start_generation=self._generation,
            requested_generations=(
                control.update_period if interval_generations is None else interval_generations
            ),
        ):
            return super().run_interval(control, interval_generations)

    def _advance_one_generation(self, control: ControlInput) -> int:
        start_generation = self._generation
        with self.timing_recorder.measure(
            "gp_generation_total",
            start_generation=start_generation,
        ):
            evaluations = super()._advance_one_generation(control)
        if self._trace_origin_wall_ns is not None:
            self._trace_evaluations += evaluations
        return evaluations

    def _build_generation_metrics(self):
        metrics = super()._build_generation_metrics()
        already_traced = (
            self._generation_trace
            and self._generation_trace[-1].generation == self._generation
        )
        if self._trace_origin_wall_ns is not None and not already_traced:
            self._generation_trace.append(
                GenerationTracePoint(
                    generation=self._generation,
                    elapsed_wall_ns=max(0, perf_counter_ns() - self._trace_origin_wall_ns),
                    cumulative_evaluations=self._trace_evaluations,
                )
            )
        return metrics

    def _compute_archive_hypervolume(self) -> float:
        with self.timing_recorder.measure("archive_hv_state", generation=self._generation):
            return super()._compute_archive_hypervolume()

    def _population_diversity(self) -> float:
        with self.timing_recorder.measure("population_diversity", generation=self._generation):
            return super()._population_diversity()

    def population_hypervolume(self) -> float:
        with self.timing_recorder.measure("population_hv", generation=self._generation):
            return super().population_hypervolume()


class InstrumentedContextualBayesianRateController(ContextualBayesianRateController):
    """BO rate controller with nested proposal, sampling, fit, and predict timers."""

    def __init__(
        self,
        config: BOControllerConfig | None = None,
        recorder: TimingRecorder | None = None,
    ) -> None:
        self.timing_recorder = recorder or TimingRecorder()
        super().__init__(config)

    def propose(self, context: GPStateSnapshot) -> ControlInput:
        with self.timing_recorder.measure(
            "controller_propose",
            generation=context.generation,
            observations=self.observation_count,
        ):
            return super().propose(context)

    def register_observation(
        self,
        context: GPStateSnapshot,
        control: ControlInput,
        reward: float,
    ) -> None:
        with self.timing_recorder.measure(
            "controller_register",
            generation=context.generation,
            update_period=control.update_period,
        ):
            super().register_observation(context, control, reward)

    def _sample_candidates(
        self,
        size: int,
        previous: ControlInput | None = None,
    ) -> np.ndarray:
        with self.timing_recorder.measure("candidate_sampling", candidate_count=size):
            return super()._sample_candidates(size, previous)

    def _acquire(self, context: GPStateSnapshot) -> ControlInput:
        # This is the production algorithm with clocks placed around its three
        # costly phases.  Keeping every random/model call in the same order is
        # essential for exact replay and paired-seed comparisons.
        best_control: ControlInput | None = None
        best_ei = -np.inf
        valid_k_values = self._valid_k_values(context)
        context_vector = np.asarray(self._context_features(context), dtype=float)

        for k_value in valid_k_values:
            x_history = self._x_history_by_k.get(k_value, [])
            y_history = self._y_history_by_k.get(k_value, [])
            if len(y_history) < self.config.min_observations_per_k:
                return self._fallback_random_control(context, forced_k=k_value)

            x_train = np.vstack(x_history)
            y_train = np.asarray(y_history, dtype=float)
            model = self._model_for_k(k_value)
            try:
                with self.timing_recorder.measure(
                    "gpr_fit",
                    generation=context.generation,
                    update_period=k_value,
                    observations=len(y_history),
                ):
                    model.fit(x_train, y_train)
            except Exception:
                continue

            candidates = self._sample_candidates(
                self.config.candidate_pool_size_per_k,
                previous=self._previous_control,
            )
            context_block = np.repeat(
                context_vector[np.newaxis, :],
                repeats=len(candidates),
                axis=0,
            )
            x_candidates = np.hstack((context_block, candidates))
            with self.timing_recorder.measure(
                "gpr_predict",
                generation=context.generation,
                update_period=k_value,
                candidate_count=len(candidates),
            ):
                mean, std = model.predict(x_candidates, return_std=True)

            with self.timing_recorder.measure(
                "expected_improvement",
                generation=context.generation,
                update_period=k_value,
            ):
                best_value = self._ei_best_value(y_train)
                improvement = mean - best_value - self.config.exploration_jitter
                with np.errstate(divide="ignore", invalid="ignore"):
                    z_value = np.divide(
                        improvement,
                        std,
                        out=np.zeros_like(improvement),
                        where=std > 1e-12,
                    )
                expected_improvement = (improvement * norm.cdf(z_value)) + (
                    std * norm.pdf(z_value)
                )
                expected_improvement = np.where(
                    std > 1e-12,
                    expected_improvement,
                    0.0,
                )

                if not np.isfinite(expected_improvement).any():
                    index = int(np.argmax(mean))
                    score = float(mean[index])
                else:
                    index = int(np.nanargmax(expected_improvement))
                    score = float(expected_improvement[index])

            if score > best_ei:
                best_ei = score
                best_control = ControlInput(
                    crossover_rate=float(candidates[index, 0]),
                    mutation_rate=float(candidates[index, 1]),
                    update_period=k_value,
                )

        if best_control is None:
            return self._fallback_random_control(context)
        return best_control


class MatchedWarmupK1Controller(InstrumentedContextualBayesianRateController):
    """Match adaptive BO warm-up, then force every-generation BO updates.

    With the seminar configuration (sequential warm-up, two observations for
    each of k=1,3,5), the common warm-up occupies generations 0--17.  From
    generation 18 onward only k=1 is offered to the acquisition calculation.
    This isolates the benefit/cost of adaptive k without changing its warm-up.
    """

    def __init__(
        self,
        config: BOControllerConfig | None = None,
        recorder: TimingRecorder | None = None,
        adaptive_until_generation: int = 18,
    ) -> None:
        if adaptive_until_generation < 0:
            raise ValueError("adaptive_until_generation must be nonnegative.")
        self.adaptive_until_generation = int(adaptive_until_generation)
        super().__init__(config, recorder)

    def _valid_k_values(self, context: GPStateSnapshot | None):
        if context is not None and context.generation >= self.adaptive_until_generation:
            return (1,)
        return super()._valid_k_values(context)


@dataclass(frozen=True)
class ReplayStep:
    """One recorded closed-loop decision used for deterministic replay."""

    step_index: int
    start_generation: int
    end_generation: int
    control: ControlInput

    def __post_init__(self) -> None:
        if self.step_index < 0 or self.start_generation < 0:
            raise ValueError("Replay indices and generations must be nonnegative.")
        if self.end_generation <= self.start_generation:
            raise ValueError("end_generation must be greater than start_generation.")
        expected_end = self.start_generation + max(1, int(self.control.update_period))
        if self.end_generation > expected_end:
            raise ValueError("Replay interval exceeds the control update period.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "start_generation": self.start_generation,
            "end_generation": self.end_generation,
            "control": {
                "crossover_rate": self.control.crossover_rate,
                "mutation_rate": self.control.mutation_rate,
                "update_period": self.control.update_period,
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReplayStep":
        control = value["control"]
        return cls(
            step_index=int(value["step_index"]),
            start_generation=int(value["start_generation"]),
            end_generation=int(value["end_generation"]),
            control=ControlInput(
                crossover_rate=float(control["crossover_rate"]),
                mutation_rate=float(control["mutation_rate"]),
                update_period=int(control["update_period"]),
            ),
        )


class ReplayController:
    """Serve an immutable recorded control sequence and verify alignment."""

    def __init__(self, steps: Iterable[ReplayStep]) -> None:
        self.steps = tuple(steps)
        for expected_index, step in enumerate(self.steps):
            if step.step_index != expected_index:
                raise ValueError("Replay steps must have contiguous zero-based indices.")
        self._next_index = 0

    @classmethod
    def from_records(
        cls,
        records: Iterable[ClosedLoopRecord | Mapping[str, Any]],
    ) -> "ReplayController":
        """Build replay steps from live records or persisted record mappings."""

        steps: list[ReplayStep] = []
        for record in records:
            if isinstance(record, Mapping):
                steps.append(ReplayStep.from_dict(record))
            else:
                steps.append(
                    ReplayStep(
                        step_index=record.step_index,
                        start_generation=record.start_state.generation,
                        end_generation=record.end_state.generation,
                        control=record.control,
                    )
                )
        return cls(steps)

    @property
    def observation_count(self) -> int:
        return self._next_index

    def propose(self, context: GPStateSnapshot) -> ControlInput:
        if self._next_index >= len(self.steps):
            raise RuntimeError("Replay control sequence is exhausted.")
        step = self.steps[self._next_index]
        if context.generation != step.start_generation:
            raise ValueError(
                f"Replay generation mismatch: expected {step.start_generation}, "
                f"received {context.generation}."
            )
        self._next_index += 1
        return step.control

    def register_observation(
        self,
        context: GPStateSnapshot,
        control: ControlInput,
        reward: float,
    ) -> None:
        """Accept the runner callback; replay intentionally does not learn."""

    def assert_exhausted(self) -> None:
        """Raise unless every recorded control decision has been consumed."""

        if self._next_index != len(self.steps):
            raise AssertionError(
                f"Replay consumed {self._next_index} of {len(self.steps)} steps."
            )


@dataclass(frozen=True)
class TimedRunResult:
    """Records and evaluation count from one timed runner invocation.

    ``timing_summary`` is retained as a compatibility field, but runners leave
    it empty.  Building a full nested summary is intentionally deferred until
    after every enclosing algorithm timer has stopped; otherwise the O(events)
    artifact aggregation itself would be charged to methods with more timers.
    """

    records: tuple[Any, ...]
    evaluations: int
    final_generation: int
    timing_summary: Mapping[str, Any]


class TimedMonitoredFixedRateRunner:
    """Seminar-compatible fixed GP including every monitoring calculation."""

    def __init__(
        self,
        engine: InstrumentedMultiObjectiveGPEngine,
        config: PlainGPBaselineConfig | None = None,
        recorder: TimingRecorder | None = None,
    ) -> None:
        self.engine = engine
        self.config = config or PlainGPBaselineConfig()
        self.recorder = recorder or engine.timing_recorder
        self.control = ControlInput(
            crossover_rate=self.config.crossover_rate,
            mutation_rate=self.config.mutation_rate,
            update_period=1,
        )

    def _snapshot(self) -> GPStateSnapshot:
        with self.recorder.measure("external_snapshot", generation=self.engine._generation):
            return self.engine.snapshot()

    def run(self) -> TimedRunResult:
        records: list[PlainGPGenerationRecord] = []
        evaluations = 0
        if not self.engine.trace_started:
            self.engine.start_trace(
                perf_counter_ns(),
                initial_evaluations=self.engine.config.population_size,
            )
        with self.recorder.measure("total_algorithm", method="fixed_monitored"):
            initial = self._snapshot()
            records.append(self._record(initial, 0))
            while True:
                snapshot = self._snapshot()
                if snapshot.generation >= snapshot.total_generations:
                    break
                with self.recorder.measure("search", generation=snapshot.generation):
                    result = self.engine.run_interval(self.control, interval_generations=1)
                evaluations += result.evaluations
                records.append(self._record(result.end_state, result.evaluations))
        return TimedRunResult(
            records=tuple(records),
            evaluations=evaluations,
            final_generation=self.engine._generation,
            timing_summary={},
        )

    def _record(self, snapshot: GPStateSnapshot, evaluations: int) -> PlainGPGenerationRecord:
        return PlainGPGenerationRecord(
            generation=snapshot.generation,
            hypervolume=snapshot.hypervolume,
            diversity=snapshot.diversity,
            mean_tree_size=snapshot.mean_tree_size,
            stagnation_generations=snapshot.stagnation_generations,
            evaluations=evaluations,
            crossover_rate=self.control.crossover_rate,
            mutation_rate=self.control.mutation_rate,
        )


class TimedFixedRateCoreRunner:
    """Fixed GP timing ablation without per-generation monitoring snapshots."""

    def __init__(
        self,
        engine: InstrumentedMultiObjectiveGPEngine,
        config: PlainGPBaselineConfig | None = None,
        recorder: TimingRecorder | None = None,
    ) -> None:
        self.engine = engine
        self.config = config or PlainGPBaselineConfig()
        self.recorder = recorder or engine.timing_recorder
        self.control = ControlInput(
            crossover_rate=self.config.crossover_rate,
            mutation_rate=self.config.mutation_rate,
            update_period=1,
        )

    def run(self) -> TimedRunResult:
        evaluations = 0
        if not self.engine.trace_started:
            self.engine.start_trace(
                perf_counter_ns(),
                initial_evaluations=self.engine.config.population_size,
            )
        with self.recorder.measure("total_algorithm", method="fixed_core"):
            while self.engine._generation < self.engine.config.total_generations:
                with self.recorder.measure("search", generation=self.engine._generation):
                    evaluations += self.engine._advance_one_generation(self.control)
        return TimedRunResult(
            records=(),
            evaluations=evaluations,
            final_generation=self.engine._generation,
            timing_summary={},
        )


class TimedClosedLoopRunner(ClosedLoopRunner):
    """Closed-loop runner with explicit search and reward component timings."""

    def __init__(
        self,
        engine: InstrumentedMultiObjectiveGPEngine,
        controller,
        reward_config: RewardConfig | None = None,
        recorder: TimingRecorder | None = None,
    ) -> None:
        super().__init__(engine, controller, reward_config)
        self.recorder = recorder or engine.timing_recorder
        # A shared recorder is required to retain the controller -> GPR nesting
        # below total_algorithm.  Controller construction precedes the timed
        # run, so replacing its default empty recorder does not alter run cost.
        if isinstance(controller, InstrumentedContextualBayesianRateController):
            controller.timing_recorder = self.recorder

    def _snapshot(self) -> GPStateSnapshot:
        with self.recorder.measure("external_snapshot", generation=self.engine._generation):
            return self.engine.snapshot()

    def run(
        self,
        max_control_steps: Optional[int] = None,
        note_path: Optional[Path] = None,
        auto_log: bool = False,
    ) -> TimedRunResult:
        records: List[ClosedLoopRecord] = []
        evaluations = 0
        step_index = 0
        if not self.engine.trace_started:
            self.engine.start_trace(
                perf_counter_ns(),
                initial_evaluations=self.engine.config.population_size,
            )

        with self.recorder.measure("total_algorithm", method="closed_loop"):
            while True:
                start_state = self._snapshot()
                if start_state.generation >= start_state.total_generations:
                    break
                if max_control_steps is not None and step_index >= max_control_steps:
                    break

                with self.recorder.measure(
                    "controller_propose_total",
                    step_index=step_index,
                    generation=start_state.generation,
                ):
                    control = self.controller.propose(start_state)
                interval = max(1, int(control.update_period))
                with self.recorder.measure(
                    "search",
                    step_index=step_index,
                    update_period=interval,
                ):
                    result = self.engine.run_interval(control, interval)
                with self.recorder.measure("reward", step_index=step_index):
                    reward = compute_reward(
                        result.start_state,
                        result.end_state,
                        self.reward_config,
                        control=control,
                        interval_diversities=result.diversity_values,
                    )
                with self.recorder.measure(
                    "controller_register_total",
                    step_index=step_index,
                    generation=result.start_state.generation,
                ):
                    self.controller.register_observation(
                        result.start_state,
                        control,
                        reward.total,
                    )

                record = ClosedLoopRecord(
                    step_index=step_index,
                    control=control,
                    start_state=result.start_state,
                    end_state=result.end_state,
                    reward=reward,
                    evaluations=result.evaluations,
                )
                records.append(record)
                evaluations += result.evaluations
                if auto_log and note_path is not None:
                    self._append_note(note_path, record)
                step_index += 1

        return TimedRunResult(
            records=tuple(records),
            evaluations=evaluations,
            final_generation=self.engine._generation,
            timing_summary={},
        )


def run_timed_monitored_fixed(
    engine: InstrumentedMultiObjectiveGPEngine,
    config: PlainGPBaselineConfig | None = None,
) -> TimedRunResult:
    """Convenience function for :class:`TimedMonitoredFixedRateRunner`."""

    return TimedMonitoredFixedRateRunner(engine, config).run()


def run_timed_fixed_core(
    engine: InstrumentedMultiObjectiveGPEngine,
    config: PlainGPBaselineConfig | None = None,
) -> TimedRunResult:
    """Convenience function for :class:`TimedFixedRateCoreRunner`."""

    return TimedFixedRateCoreRunner(engine, config).run()


def run_timed_closed_loop(
    engine: InstrumentedMultiObjectiveGPEngine,
    controller,
    reward_config: RewardConfig | None = None,
    max_control_steps: int | None = None,
) -> TimedRunResult:
    """Convenience function for :class:`TimedClosedLoopRunner`."""

    return TimedClosedLoopRunner(engine, controller, reward_config).run(max_control_steps)


__all__ = [
    "GenerationTracePoint",
    "InstrumentedContextualBayesianRateController",
    "InstrumentedMultiObjectiveGPEngine",
    "MatchedWarmupK1Controller",
    "ReplayController",
    "ReplayStep",
    "TimedClosedLoopRunner",
    "TimedFixedRateCoreRunner",
    "TimedMonitoredFixedRateRunner",
    "TimedRunResult",
    "run_timed_closed_loop",
    "run_timed_fixed_core",
    "run_timed_monitored_fixed",
]
