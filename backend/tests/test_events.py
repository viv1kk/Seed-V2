"""Event schema and replay.

The sequence number carries two guarantees at once: it is the gap check
the frontend runs (FR-E6) and the replay cursor the backend serves from
(FR-E7). These tests hold both.
"""

from app.domain.events import Category, EventLog, Severity
from app.domain.lifecycle import LifecycleState, Phase
from app.domain.state import SystemState


def fill(log: EventLog, count: int) -> None:
    for index in range(count):
        log.append(
            type="test.event",
            phase=Phase.DISCOVERY,
            category=Category.DISCOVERY,
            message=f"event {index}",
        )


def test_sequence_numbers_start_at_one_and_are_contiguous() -> None:
    log = EventLog()
    fill(log, 5)
    assert [event.sequence for event in log.all()] == [1, 2, 3, 4, 5]


def test_events_carry_everything_fr_e3_requires() -> None:
    log = EventLog()
    fill(log, 1)
    event = log.all()[0]
    for field in ("sequence", "timestamp", "type", "phase", "category", "severity", "message"):
        assert getattr(event, field) is not None


def test_since_returns_only_later_events() -> None:
    log = EventLog()
    fill(log, 5)
    assert [event.sequence for event in log.since(2)] == [3, 4, 5]
    assert [event.sequence for event in log.since(0)] == [1, 2, 3, 4, 5]
    assert list(log.since(5)) == []


def test_since_beyond_the_log_returns_everything() -> None:
    """A client reconnecting across a Reset is ahead of the run.

    It must receive the new log rather than nothing, or it waits forever
    for events that no longer exist.
    """
    log = EventLog()
    fill(log, 3)
    assert [event.sequence for event in log.since(99)] == [1, 2, 3]


def test_listeners_receive_every_recorded_event_in_order() -> None:
    state = SystemState()
    seen: list[int] = []
    state.subscribe(lambda event: seen.append(event.sequence))

    state.transition(LifecycleState.INITIALIZED)
    state.transition(LifecycleState.DISCOVERING)
    state.record(type="test", category=Category.DISCOVERY, message="hello")

    assert seen == [1, 2, 3]
    assert seen == [event.sequence for event in state.events.all()]


def test_event_phase_comes_from_the_current_state() -> None:
    """An event cannot claim a phase the system is not in."""
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    state.transition(LifecycleState.DISCOVERING)
    event = state.record(type="test", category=Category.DISCOVERY, message="hello")
    assert event.phase is Phase.DISCOVERY


def test_snapshot_reports_the_sequence_it_is_current_as_of() -> None:
    """FR-E5: the frontend applies the stream from this number onward."""
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    snapshot = state.snapshot()
    assert snapshot.sequence == state.events.last_sequence == 1


def test_snapshot_serialises_blocked_on_in_camel_case() -> None:
    """FR-L4 names the field `blockedOn`."""
    state = SystemState()
    payload = state.snapshot().model_dump(by_alias=True)
    assert "blockedOn" in payload
    assert "blocked_on" not in payload


def test_severity_defaults_to_info() -> None:
    log = EventLog()
    fill(log, 1)
    assert log.all()[0].severity is Severity.INFO
