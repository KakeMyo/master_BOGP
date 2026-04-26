from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol

from .journal import append_operation_log
from .objectives import RewardBreakdown, RewardConfig, compute_reward
from .types import ControlInput, GPStateSnapshot, IntervalResult


class GeneticProgrammingEngine(Protocol):
    def snapshot(self) -> GPStateSnapshot:
        ...

    def run_interval(self, control: ControlInput, interval_generations: int) -> IntervalResult:
        ...


@dataclass(frozen=True)
class ClosedLoopRecord:
    step_index: int
    control: ControlInput
    start_state: GPStateSnapshot
    end_state: GPStateSnapshot
    reward: RewardBreakdown
    evaluations: int


class ClosedLoopRunner:
    def __init__(
        self,
        engine: GeneticProgrammingEngine,
        controller,
        reward_config: RewardConfig = None,
    ) -> None:
        self.engine = engine
        self.controller = controller
        self.reward_config = reward_config or RewardConfig()

    def run(
        self,
        max_control_steps: Optional[int] = None,
        note_path: Optional[Path] = None,
        auto_log: bool = False,
    ) -> List[ClosedLoopRecord]:
        records: List[ClosedLoopRecord] = []
        step_index = 0

        while True:
            start_state = self.engine.snapshot()
            if start_state.generation >= start_state.total_generations:
                break
            if max_control_steps is not None and step_index >= max_control_steps:
                break

            control = self.controller.propose(start_state)
            interval = getattr(self.controller.config, "control_interval", 1)
            result = self.engine.run_interval(control, interval)
            reward = compute_reward(result.start_state, result.end_state, self.reward_config)
            self.controller.register_observation(result.start_state, control, reward.total)

            record = ClosedLoopRecord(
                step_index=step_index,
                control=control,
                start_state=result.start_state,
                end_state=result.end_state,
                reward=reward,
                evaluations=result.evaluations,
            )
            records.append(record)

            if auto_log and note_path is not None:
                self._append_note(note_path, record)

            step_index += 1

        return records

    def _append_note(self, note_path: Path, record: ClosedLoopRecord) -> None:
        summary = (
            "制御ステップ {0} で p_c={1:.3f}, p_m={2:.3f} を適用し、"
            "報酬 {3:.3f} を観測した。"
        ).format(
            record.step_index,
            record.control.crossover_rate,
            record.control.mutation_rate,
            record.reward.total,
        )
        rationale = "現在の GP 状態に応じた BO 制御の挙動を、研究ノートへ逐次記録するため。"
        details = [
            "開始世代: {0}".format(record.start_state.generation),
            "終了世代: {0}".format(record.end_state.generation),
            "HV: {0:.4f} -> {1:.4f}".format(
                record.start_state.hypervolume,
                record.end_state.hypervolume,
            ),
            "多様性: {0:.4f} -> {1:.4f}".format(
                record.start_state.diversity,
                record.end_state.diversity,
            ),
            "停滞世代数: {0}".format(record.end_state.stagnation_generations),
        ]
        validation = [
            "報酬内訳 hv_term={0:.3f}, diversity_term={1:.3f}".format(
                record.reward.hv_term,
                record.reward.diversity_term,
            )
        ]
        next_actions = ["実 GP 実装へ接続し、同じ形式でログを継続する。"]
        append_operation_log(
            note_path=note_path,
            title="閉ループ制御ログ",
            summary=summary,
            rationale=rationale,
            details=details,
            validation=validation,
            next_actions=next_actions,
        )

