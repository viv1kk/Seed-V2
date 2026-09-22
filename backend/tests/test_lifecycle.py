"""The state-machine suite (D-7).

Asserts that every legal transition succeeds and every illegal one
raises (FR-L1, FR-L3). The table is enumerated rather than sampled, so
adding a state to `LifecycleState` without adding its edges fails here
rather than in a demo.
"""

import pytest

from app.domain.lifecycle import (
    PHASE_OF,
    TRANSITIONS,
    IllegalTransition,
    LifecycleState,
    can_transition,
)
from app.domain.state import BlockedOn, RequestKind, SystemState

LEGAL = [
    (source, target) for source, targets in TRANSITIONS.items() for target in targets
]

ILLEGAL = [
    (source, target)
    for source in LifecycleState
    for target in LifecycleState
    if not can_transition(source, target)
]


def reach(state: SystemState, target: LifecycleState) -> None:
    """Walk the table to `target` by breadth-first search.

    Tests must not set `lifecycle` directly: a test that bypasses the
    machine cannot prove anything about the machine.
    """
    if state.lifecycle is target:
        return
    queue: list[list[LifecycleState]] = [[state.lifecycle]]
    seen = {state.lifecycle}
    while queue:
        path = queue.pop(0)
        for nxt in sorted(TRANSITIONS[path[-1]]):
            if nxt in seen:
                continue
            if nxt is target:
                for step in [*path[1:], nxt]:
                    state.transition(step)
                return
            seen.add(nxt)
            queue.append([*path, nxt])
    raise AssertionError(f"{target} is unreachable from {state.lifecycle}")


def test_every_state_has_a_table_entry() -> None:
    assert set(TRANSITIONS) == set(LifecycleState)


def test_every_state_has_a_phase() -> None:
    assert set(PHASE_OF) == set(LifecycleState)


@pytest.mark.parametrize(("source", "target"), LEGAL)
def test_legal_transitions_succeed(source: LifecycleState, target: LifecycleState) -> None:
    state = SystemState()
    reach(state, source)
    state.transition(target)
    assert state.lifecycle is target


@pytest.mark.parametrize(("source", "target"), ILLEGAL)
def test_illegal_transitions_raise_without_mutating(
    source: LifecycleState, target: LifecycleState
) -> None:
    state = SystemState()
    reach(state, source)
    before = state.lifecycle
    events_before = len(state.events)

    with pytest.raises(IllegalTransition):
        state.transition(target)

    assert state.lifecycle is before
    assert len(state.events) == events_before


def test_every_state_is_reachable_from_uninitialized() -> None:
    for target in LifecycleState:
        reach(SystemState(), target)


def test_transition_records_an_event() -> None:
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    event = state.events.all()[-1]
    assert event.type == "lifecycle.transition"
    assert event.payload == {
        "from": LifecycleState.UNINITIALIZED,
        "to": LifecycleState.INITIALIZED,
    }


def test_blocking_is_a_flag_beside_the_state() -> None:
    """FR-L4: waiting does not replace the state the system waits in."""
    state = SystemState()
    reach(state, LifecycleState.DISCOVERY_BLOCKED)
    state.block(
        BlockedOn(kind=RequestKind.CREDENTIALS, request_id="r1", prompt="Credentials needed.")
    )

    assert state.lifecycle is LifecycleState.DISCOVERY_BLOCKED
    assert state.blocked_on is not None
    assert state.blocked_on.kind is RequestKind.CREDENTIALS

    state.unblock()
    assert state.blocked_on is None
    assert state.lifecycle is LifecycleState.DISCOVERY_BLOCKED


def test_reset_returns_to_uninitialized_and_clears_the_log() -> None:
    """FR-L7."""
    state = SystemState()
    reach(state, LifecycleState.ASSESSING)
    assert len(state.events) > 0

    state.reset()

    assert state.lifecycle is LifecycleState.UNINITIALIZED
    assert len(state.events) == 0
    assert state.events.last_sequence == 0
    assert state.blocked_on is None


def test_reset_keeps_listeners() -> None:
    """Connections outlive runs, so a reset must not silence them."""
    state = SystemState()
    received: list[int] = []
    state.subscribe(lambda event: received.append(event.sequence))

    state.transition(LifecycleState.INITIALIZED)
    state.reset()
    state.transition(LifecycleState.INITIALIZED)

    assert received == [1, 1]
