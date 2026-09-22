"""System State --- the sole source of truth (FR-L5).

Everything the system knows lives here. Simulated agents read from it
and write to it; none of them holds authoritative state of its own, so
there is exactly one place to look when the displayed system disagrees
with itself.

State is held in memory for a single run, and Reset rebuilds it from
nothing (FR-L7). There is no persistence layer, by design: a run that
survives a restart would make determinism harder to reason about, not
easier (NFR-D4).
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.domain.events import Category, Event, EventLog, Severity
from app.domain.lifecycle import (
    PHASE_OF,
    LifecycleState,
    Phase,
    assert_transition,
)
from app.domain.schema import Schema


class RequestKind(StrEnum):
    """The kinds of human input the system can wait on (FR-H3)."""

    CREDENTIALS = "credentials"
    AMBIGUITY = "ambiguity"
    MISSING_INFO = "missing-info"
    APPROVAL = "approval"
    CONFIRMATION = "confirmation"


class RequestOption(Schema):
    """One legitimate answer to a request that is a choice, not a form.

    Ambiguity, missing information, approval and confirmation are all
    decisions between stated alternatives (§8, §18). The alternatives are
    modelled rather than written into the prompt, so the surface can
    present them as choices and the audit log can record which was taken.
    """

    value: str
    label: str
    note: str | None = None


class BlockedOn(Schema):
    """What the system is waiting for, beside the state it waits in.

    A flag rather than a state (FR-L4), so the lifecycle still reports
    what the system was doing when it stopped.

    The three fields after `kind` are FR-H2: what is needed, what access
    that requires, and why it is needed. `prompt` alone would collapse
    them into a sentence and lose the third one, which is the one that
    makes an escalation answerable rather than merely obeyed.
    """

    kind: RequestKind
    request_id: str
    prompt: str
    access: str | None = None
    reason: str | None = None
    options: list[RequestOption] = Field(default_factory=list)


class StateSnapshot(Schema):
    """The full state, as the frontend receives it on connect (FR-E5).

    `sequence` is the number of the last event folded into this
    snapshot. The frontend applies the stream from that point onward,
    which is what makes snapshot-then-stream exact rather than
    approximate.
    """

    sequence: int
    lifecycle: LifecycleState
    phase: Phase
    blocked_on: BlockedOn | None = None
    seed: dict[str, Any] | None = None
    environment: dict[str, Any] = Field(default_factory=dict)
    assessments: list[dict[str, Any]] = Field(default_factory=list)
    solutions: list[dict[str, Any]] = Field(default_factory=list)
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    implementations: list[dict[str, Any]] = Field(default_factory=list)
    runtime: dict[str, Any] = Field(default_factory=dict)


class SystemState:
    """The mutable run state.

    The branches below follow the state model of §58. M1 fills the
    lifecycle and the event log; later milestones fill the rest. They
    exist now, empty, so the shape of the whole is visible from the
    start rather than accreting.
    """

    def __init__(self) -> None:
        self._listeners: list[Callable[[Event], None]] = []
        self.reset()

    # -- Composition -------------------------------------------------

    def subscribe(self, listener: Callable[[Event], None]) -> None:
        """Register a listener for newly recorded events.

        The transport layer uses this to fan events out to connected
        clients. The domain does not know what a listener does with
        them, which is what keeps asyncio out of this module.
        """
        self._listeners.append(listener)

    # -- Lifecycle ---------------------------------------------------

    def reset(self) -> None:
        """Return to UNINITIALIZED and discard the run (FR-L7).

        Listeners survive a reset: they belong to the process, not to
        the run.
        """
        self.lifecycle = LifecycleState.UNINITIALIZED
        self.blocked_on: BlockedOn | None = None
        self.events = EventLog()
        self.seed: dict[str, Any] | None = None
        self.environment: dict[str, Any] = {}
        self.assessments: list[dict[str, Any]] = []
        self.solutions: list[dict[str, Any]] = []
        self.approvals: list[dict[str, Any]] = []
        self.implementations: list[dict[str, Any]] = []
        self.runtime: dict[str, Any] = {}

    @property
    def phase(self) -> Phase:
        return PHASE_OF[self.lifecycle]

    def transition(self, target: LifecycleState) -> None:
        """Move to `target`, or raise without mutating (FR-L3).

        The check precedes every assignment, so a rejected transition
        leaves the system exactly as it was.
        """
        assert_transition(self.lifecycle, target)
        source = self.lifecycle
        self.lifecycle = target
        self.record(
            type="lifecycle.transition",
            category=Category.DECISION,
            message=f"Lifecycle moved from {source} to {target}.",
            payload={"from": source, "to": target},
        )

    # -- Human input -------------------------------------------------

    def block(self, blocked_on: BlockedOn) -> None:
        """Wait on a person, and say so in the stream.

        The whole request travels in the payload, not a summary of it. A
        client that joins late, or resyncs after a gap, rebuilds the
        surface from the event alone and cannot drift from the snapshot.
        """
        self.blocked_on = blocked_on
        self.record(
            type="human.requested",
            category=Category.HUMAN_INPUT,
            message=blocked_on.prompt,
            payload={
                "kind": blocked_on.kind,
                "requestId": blocked_on.request_id,
                "request": blocked_on.model_dump(by_alias=True),
            },
        )

    def unblock(self) -> None:
        if self.blocked_on is None:
            return
        resolved = self.blocked_on
        self.blocked_on = None
        self.record(
            type="human.resolved",
            category=Category.HUMAN_INPUT,
            message="Human input received. Resuming from the point of suspension.",
            payload={"kind": resolved.kind, "requestId": resolved.request_id},
        )

    # -- Events ------------------------------------------------------

    def record(
        self,
        *,
        type: str,
        category: Category,
        message: str,
        severity: Severity = Severity.INFO,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        """Append an event and notify listeners.

        The phase is taken from the current lifecycle state rather than
        passed in, so an event can never claim a phase the system is not
        in.
        """
        event = self.events.append(
            type=type,
            phase=self.phase,
            category=category,
            message=message,
            severity=severity,
            payload=payload,
        )
        for listener in self._listeners:
            listener(event)
        return event

    # -- Projection --------------------------------------------------

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            sequence=self.events.last_sequence,
            lifecycle=self.lifecycle,
            phase=self.phase,
            blocked_on=self.blocked_on,
            seed=self.seed,
            environment=self.environment,
            assessments=self.assessments,
            solutions=self.solutions,
            approvals=self.approvals,
            implementations=self.implementations,
            runtime=self.runtime,
        )
