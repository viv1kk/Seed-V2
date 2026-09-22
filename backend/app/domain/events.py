"""Event schema, factory and log.

All system activity is expressed as events, and the UI reacts to the
stream rather than to the mechanics behind it (FR-E1). The schema is
therefore the contract between the simulation and every surface that
displays it.

The log is unbounded within a run (D-9). FR-E7 requires exact replay of
missed events from the retained log, which a ring buffer cannot
guarantee, and a run produces at most a few thousand events.
"""

import itertools
from collections.abc import Iterator
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.domain.lifecycle import Phase
from app.domain.schema import Schema


class Category(StrEnum):
    """Display categories (FR-E4).

    These drive how the activity stream groups and colours an entry.
    They are a presentation concern, deliberately separate from
    `Severity`, which is about how much the entry matters.
    """

    DISCOVERY = "DISCOVERY"
    ANALYSIS = "ANALYSIS"
    VALIDATION = "VALIDATION"
    DECISION = "DECISION"
    POLICY = "POLICY"
    WARNING = "WARNING"
    SUCCESS = "SUCCESS"
    HUMAN_INPUT = "HUMAN_INPUT"


class Severity(StrEnum):
    """How much an entry matters, independent of its category.

    Three levels rather than more: the activity stream is an auditable
    record, not a developer log (FR-E8), and finer gradations would
    invite the log-level noise that requirement exists to prevent.
    """

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Event(Schema):
    """One entry in the activity stream.

    Carries everything FR-E3 requires. `payload` holds structured detail
    for surfaces that need more than the message; the message alone must
    always be enough to read the stream.
    """

    sequence: int
    timestamp: datetime
    type: str
    phase: Phase
    category: Category
    severity: Severity = Severity.INFO
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class EventFactory:
    """Mints events with monotonic sequence numbers.

    One counter per run, owned by the log, so sequence numbers are the
    single thing the frontend can trust to detect a gap (FR-E6).
    """

    def __init__(self) -> None:
        self._sequence = itertools.count(1)

    def make(
        self,
        *,
        type: str,
        phase: Phase,
        category: Category,
        message: str,
        severity: Severity = Severity.INFO,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        return Event(
            sequence=next(self._sequence),
            timestamp=datetime.now(timezone.utc),
            type=type,
            phase=phase,
            category=category,
            severity=severity,
            message=message,
            payload=payload or {},
        )


class EventLog:
    """The retained record of a run.

    Append-only, and the source of the replay that FR-E7 requires.
    """

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._factory = EventFactory()

    def __len__(self) -> int:
        return len(self._events)

    @property
    def last_sequence(self) -> int:
        return self._events[-1].sequence if self._events else 0

    def append(
        self,
        *,
        type: str,
        phase: Phase,
        category: Category,
        message: str,
        severity: Severity = Severity.INFO,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        event = self._factory.make(
            type=type,
            phase=phase,
            category=category,
            message=message,
            severity=severity,
            payload=payload,
        )
        self._events.append(event)
        return event

    def since(self, sequence: int) -> Iterator[Event]:
        """Every event after `sequence`, in order.

        Sequence numbers start at 1 and are contiguous within a run, so
        the offset is exact and no scan is needed.

        A caller asking for a sequence beyond the end of the log is
        ahead of this run, which happens when it reconnects across a
        Reset. It receives the whole log rather than nothing: the
        alternative is a client that waits forever for events that no
        longer exist.
        """
        if sequence <= 0 or sequence > self.last_sequence:
            yield from self._events
            return
        yield from self._events[sequence:]

    def all(self) -> list[Event]:
        return list(self._events)
