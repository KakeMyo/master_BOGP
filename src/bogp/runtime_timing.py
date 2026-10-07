"""Low-overhead nested wall-clock and process-CPU timing utilities.

The clocks deliberately use integer nanoseconds.  This avoids rounding while
events are collected and makes the resulting JSON suitable for later,
reproducible aggregation.
"""

from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from time import perf_counter_ns, process_time_ns
from typing import Any, Iterator, Mapping


def _nonnegative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number, not {type(value).__name__}.")
    if not math.isfinite(float(value)) or value < 0 or int(value) != value:
        raise ValueError(f"{field_name} must be a finite, nonnegative integer.")
    return int(value)


def _json_value(value: Any, path: str = "metadata") -> Any:
    """Return a JSON-compatible copy and reject non-finite numeric values."""

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number.")
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value), path)
    if isinstance(value, Mapping):
        converted: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings.")
            converted[key] = _json_value(item, f"{path}.{key}")
        return converted
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{path}[]") for item in value]

    # Numpy scalar types expose item(), but importing numpy in this small timing
    # module would add avoidable import and start-up cost.
    item_method = getattr(value, "item", None)
    if callable(item_method):
        converted = item_method()
        if converted is not value:
            return _json_value(converted, path)
    raise TypeError(f"{path} contains non-JSON value {type(value).__name__}.")


@dataclass(frozen=True)
class TimingEvent:
    """One inclusive timed region in a nested :class:`TimingRecorder` trace."""

    event_id: int
    parent_event_id: int | None
    name: str
    start_wall_ns: int
    end_wall_ns: int
    start_cpu_ns: int
    end_cpu_ns: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        event_id = _nonnegative_integer(self.event_id, "event_id")
        object.__setattr__(self, "event_id", event_id)
        if self.parent_event_id is not None:
            parent_id = _nonnegative_integer(self.parent_event_id, "parent_event_id")
            if parent_id == event_id:
                raise ValueError("An event cannot be its own parent.")
            object.__setattr__(self, "parent_event_id", parent_id)
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string.")

        start_wall = _nonnegative_integer(self.start_wall_ns, "start_wall_ns")
        end_wall = _nonnegative_integer(self.end_wall_ns, "end_wall_ns")
        start_cpu = _nonnegative_integer(self.start_cpu_ns, "start_cpu_ns")
        end_cpu = _nonnegative_integer(self.end_cpu_ns, "end_cpu_ns")
        if end_wall < start_wall:
            raise ValueError("end_wall_ns must not precede start_wall_ns.")
        if end_cpu < start_cpu:
            raise ValueError("end_cpu_ns must not precede start_cpu_ns.")
        object.__setattr__(self, "start_wall_ns", start_wall)
        object.__setattr__(self, "end_wall_ns", end_wall)
        object.__setattr__(self, "start_cpu_ns", start_cpu)
        object.__setattr__(self, "end_cpu_ns", end_cpu)
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", _json_value(dict(self.metadata)))

    @property
    def wall_duration_ns(self) -> int:
        """Inclusive wall-clock duration in nanoseconds."""

        return self.end_wall_ns - self.start_wall_ns

    @property
    def cpu_duration_ns(self) -> int:
        """Inclusive process CPU duration in nanoseconds."""

        return self.end_cpu_ns - self.start_cpu_ns

    @property
    def duration_wall_ns(self) -> int:
        """Compatibility alias for :attr:`wall_duration_ns`."""

        return self.wall_duration_ns

    @property
    def duration_cpu_ns(self) -> int:
        """Compatibility alias for :attr:`cpu_duration_ns`."""

        return self.cpu_duration_ns

    @property
    def wall_duration_seconds(self) -> float:
        return self.wall_duration_ns / 1_000_000_000.0

    @property
    def cpu_duration_seconds(self) -> float:
        return self.cpu_duration_ns / 1_000_000_000.0

    def to_dict(self) -> dict[str, Any]:
        """Convert this event to a JSON-compatible dictionary."""

        return {
            "event_id": self.event_id,
            "parent_event_id": self.parent_event_id,
            "name": self.name,
            "start_wall_ns": self.start_wall_ns,
            "end_wall_ns": self.end_wall_ns,
            "start_cpu_ns": self.start_cpu_ns,
            "end_cpu_ns": self.end_cpu_ns,
            "wall_duration_ns": self.wall_duration_ns,
            "cpu_duration_ns": self.cpu_duration_ns,
            "metadata": _json_value(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TimingEvent":
        """Reconstruct an event from :meth:`to_dict` output."""

        return cls(
            event_id=value["event_id"],
            parent_event_id=value.get("parent_event_id"),
            name=value["name"],
            start_wall_ns=value["start_wall_ns"],
            end_wall_ns=value["end_wall_ns"],
            start_cpu_ns=value["start_cpu_ns"],
            end_cpu_ns=value["end_cpu_ns"],
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True)
class _ActiveEvent:
    event_id: int
    parent_event_id: int | None
    name: str
    start_wall_ns: int
    start_cpu_ns: int
    metadata: Mapping[str, Any]


class TimingRecorder:
    """Collect nested timing events using monotonic wall and process clocks.

    A recorder is intended for one experiment process and is deliberately not
    shared across threads.  Events are returned in start order, even though
    child regions necessarily finish before their parents.
    """

    def __init__(self) -> None:
        self._events: list[TimingEvent] = []
        self._stack: list[_ActiveEvent] = []
        self._next_event_id = 0

    @property
    def events(self) -> tuple[TimingEvent, ...]:
        """Completed events in start order."""

        return tuple(sorted(self._events, key=lambda event: event.event_id))

    @contextmanager
    def measure(self, name: str, **metadata: Any) -> Iterator[None]:
        """Measure a possibly nested code region.

        Events are retained even if the measured operation raises.  In that
        case ``exception_type`` is added to the event metadata and the original
        exception is re-raised unchanged.
        """

        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string.")
        clean_metadata = _json_value(metadata)
        event_id = self._next_event_id
        self._next_event_id += 1
        parent_id = self._stack[-1].event_id if self._stack else None
        active = _ActiveEvent(
            event_id=event_id,
            parent_event_id=parent_id,
            name=name,
            start_wall_ns=perf_counter_ns(),
            start_cpu_ns=process_time_ns(),
            metadata=clean_metadata,
        )
        self._stack.append(active)
        failure_type: str | None = None
        try:
            yield
        except BaseException as error:
            failure_type = type(error).__name__
            raise
        finally:
            end_cpu = process_time_ns()
            end_wall = perf_counter_ns()
            popped = self._stack.pop()
            if popped.event_id != event_id:
                raise RuntimeError("Timing regions exited out of nesting order.")
            final_metadata = dict(clean_metadata)
            if failure_type is not None:
                final_metadata["exception_type"] = failure_type
            self._events.append(
                TimingEvent(
                    event_id=event_id,
                    parent_event_id=parent_id,
                    name=name,
                    start_wall_ns=active.start_wall_ns,
                    end_wall_ns=end_wall,
                    start_cpu_ns=active.start_cpu_ns,
                    end_cpu_ns=end_cpu,
                    metadata=final_metadata,
                )
            )

    def totals(
        self,
        name: str,
        ancestor_name: str | None = None,
    ) -> dict[str, Any]:
        """Sum inclusive durations for matching events.

        When ``ancestor_name`` is supplied, only events nested anywhere below
        an event with that name are included.
        """

        by_id = {event.event_id: event for event in self.events}

        def has_ancestor(event: TimingEvent) -> bool:
            parent_id = event.parent_event_id
            while parent_id is not None:
                parent = by_id.get(parent_id)
                if parent is None:
                    return False
                if parent.name == ancestor_name:
                    return True
                parent_id = parent.parent_event_id
            return False

        matches = [
            event
            for event in self.events
            if event.name == name and (ancestor_name is None or has_ancestor(event))
        ]
        wall_ns = sum(event.wall_duration_ns for event in matches)
        cpu_ns = sum(event.cpu_duration_ns for event in matches)
        return {
            "name": name,
            "ancestor_name": ancestor_name,
            "count": len(matches),
            "wall_duration_ns": wall_ns,
            "cpu_duration_ns": cpu_ns,
            "wall_duration_seconds": wall_ns / 1_000_000_000.0,
            "cpu_duration_seconds": cpu_ns / 1_000_000_000.0,
        }

    def summary(self) -> dict[str, Any]:
        """Return per-component inclusive totals plus all raw events."""

        names = sorted({event.name for event in self.events})
        return {
            "clock": {
                "wall": "time.perf_counter_ns",
                "cpu": "time.process_time_ns",
                "unit": "nanoseconds",
            },
            "components": {name: self.totals(name) for name in names},
            "events": [event.to_dict() for event in self.events],
        }

    def to_dict(self) -> dict[str, Any]:
        """Alias for :meth:`summary`, suitable for ``json.dump``."""

        return self.summary()

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialize the complete trace as standards-compliant JSON."""

        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False, indent=indent)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TimingRecorder":
        """Reconstruct a recorder from :meth:`to_dict` output."""

        recorder = cls()
        recorder._events = [TimingEvent.from_dict(item) for item in value.get("events", [])]
        recorder._next_event_id = (
            max((event.event_id for event in recorder._events), default=-1) + 1
        )
        return recorder
