"""The lifecycle state machine.

A single explicit transition table, not boolean flags spread across the
codebase (FR-L1). Every legal move is one entry below, so extending the
lifecycle is an edit to a table rather than a hunt through call sites.

Blocking on human input is deliberately *not* a state. A system that is
waiting for credentials during discovery is still discovering; the wait
is recorded as a flag beside the state (FR-L4). Modelling it as a state
would multiply the table by the number of phases and lose the
information about what the system was doing when it stopped.
"""

from enum import StrEnum


class LifecycleState(StrEnum):
    """The states of FR-L9 (FR-L2 as amended by A-3), in narrative order."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZED = "INITIALIZED"
    DISCOVERING = "DISCOVERING"
    DISCOVERY_BLOCKED = "DISCOVERY_BLOCKED"
    DISCOVERY_COMPLETE = "DISCOVERY_COMPLETE"
    ASSESSING = "ASSESSING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    IMPLEMENTING = "IMPLEMENTING"
    IMPLEMENTATION_COMPLETE = "IMPLEMENTATION_COMPLETE"
    CLOSING_SEEDING = "CLOSING_SEEDING"
    READY_TO_RUN = "READY_TO_RUN"
    RUNNING = "RUNNING"


class Phase(StrEnum):
    """The coarse phases the lifecycle indicator draws (FR-L6, §14).

    Several lifecycle states map to one phase: the indicator shows
    progress through the narrative, while the state machine tracks the
    finer positions the engine needs.
    """

    INIT = "INIT"
    DISCOVERY = "DISCOVERY"
    ASSESSMENT = "ASSESSMENT"
    IMPLEMENTATION = "IMPLEMENTATION"
    RUNTIME = "RUNTIME"


PHASE_ORDER: tuple[Phase, ...] = (
    Phase.INIT,
    Phase.DISCOVERY,
    Phase.ASSESSMENT,
    Phase.IMPLEMENTATION,
    Phase.RUNTIME,
)

PHASE_OF: dict[LifecycleState, Phase] = {
    LifecycleState.UNINITIALIZED: Phase.INIT,
    LifecycleState.INITIALIZED: Phase.INIT,
    LifecycleState.DISCOVERING: Phase.DISCOVERY,
    LifecycleState.DISCOVERY_BLOCKED: Phase.DISCOVERY,
    LifecycleState.DISCOVERY_COMPLETE: Phase.DISCOVERY,
    LifecycleState.ASSESSING: Phase.ASSESSMENT,
    LifecycleState.AWAITING_APPROVAL: Phase.ASSESSMENT,
    LifecycleState.IMPLEMENTING: Phase.IMPLEMENTATION,
    LifecycleState.IMPLEMENTATION_COMPLETE: Phase.IMPLEMENTATION,
    # Closing is the last act of seeding, not the first act of Life (D-16).
    LifecycleState.CLOSING_SEEDING: Phase.IMPLEMENTATION,
    LifecycleState.READY_TO_RUN: Phase.RUNTIME,
    LifecycleState.RUNNING: Phase.RUNTIME,
}

#: The transition table. Reset is not an edge here: it is an explicit
#: operation that rebuilds state from nothing (FR-L7), and modelling it
#: as a transition from all twelve states would say something false
#: about how it works.
TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.UNINITIALIZED: frozenset({LifecycleState.INITIALIZED}),
    LifecycleState.INITIALIZED: frozenset({LifecycleState.DISCOVERING}),
    LifecycleState.DISCOVERING: frozenset(
        {LifecycleState.DISCOVERY_BLOCKED, LifecycleState.DISCOVERY_COMPLETE}
    ),
    # Resolving the block returns to discovery, which is the whole point
    # of FR-L4: the system resumes where it stopped (FR-H7).
    LifecycleState.DISCOVERY_BLOCKED: frozenset({LifecycleState.DISCOVERING}),
    LifecycleState.DISCOVERY_COMPLETE: frozenset({LifecycleState.ASSESSING}),
    LifecycleState.ASSESSING: frozenset({LifecycleState.AWAITING_APPROVAL}),
    LifecycleState.AWAITING_APPROVAL: frozenset({LifecycleState.IMPLEMENTING}),
    LifecycleState.IMPLEMENTING: frozenset({LifecycleState.IMPLEMENTATION_COMPLETE}),
    # A built system is not yet a running one. A person confirms the close
    # of seeding, and closing cleans up after the build before anything
    # runs (D-16). The direct edge to READY_TO_RUN is gone.
    LifecycleState.IMPLEMENTATION_COMPLETE: frozenset({LifecycleState.CLOSING_SEEDING}),
    LifecycleState.CLOSING_SEEDING: frozenset({LifecycleState.READY_TO_RUN}),
    # Running a solution and returning to the workspace, repeatedly:
    # completion is per-solution, not global (FR-L8).
    LifecycleState.READY_TO_RUN: frozenset({LifecycleState.RUNNING}),
    LifecycleState.RUNNING: frozenset({LifecycleState.READY_TO_RUN}),
}


class IllegalTransition(Exception):
    """Raised instead of mutating state on an illegal move (FR-L3)."""

    def __init__(self, source: LifecycleState, target: LifecycleState) -> None:
        allowed = sorted(TRANSITIONS[source])
        super().__init__(
            f"Illegal transition {source} -> {target}. "
            f"Allowed from {source}: {', '.join(allowed) or 'nothing'}."
        )
        self.source = source
        self.target = target


def can_transition(source: LifecycleState, target: LifecycleState) -> bool:
    return target in TRANSITIONS[source]


def assert_transition(source: LifecycleState, target: LifecycleState) -> None:
    if not can_transition(source, target):
        raise IllegalTransition(source, target)
