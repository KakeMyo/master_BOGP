from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


def _as_lines(values: Optional[Iterable[str]]) -> str:
    if not values:
        return "- なし"
    return "\n".join("- {0}".format(value) for value in values)


def render_operation_log(
    title: str,
    summary: str,
    rationale: str,
    details: Optional[Iterable[str]] = None,
    validation: Optional[Iterable[str]] = None,
    next_actions: Optional[Iterable[str]] = None,
    timestamp: Optional[datetime] = None,
) -> str:
    timestamp = timestamp or datetime.now()
    stamp = timestamp.strftime("%Y-%m-%d %H:%M")
    return (
        "\n"
        "### {stamp} | {title}\n\n"
        "- 何をしたか: {summary}\n"
        "- なぜそうしたか: {rationale}\n"
        "- 詳細:\n"
        "{details}\n"
        "- 確認方法:\n"
        "{validation}\n"
        "- 次にやること:\n"
        "{next_actions}\n"
    ).format(
        stamp=stamp,
        title=title,
        summary=summary,
        rationale=rationale,
        details=_as_lines(details),
        validation=_as_lines(validation),
        next_actions=_as_lines(next_actions),
    )


def append_operation_log(
    note_path: Path,
    title: str,
    summary: str,
    rationale: str,
    details: Optional[Iterable[str]] = None,
    validation: Optional[Iterable[str]] = None,
    next_actions: Optional[Iterable[str]] = None,
    timestamp: Optional[datetime] = None,
) -> None:
    note_path = Path(note_path)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    entry = render_operation_log(
        title=title,
        summary=summary,
        rationale=rationale,
        details=details,
        validation=validation,
        next_actions=next_actions,
        timestamp=timestamp,
    )
    with note_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)

