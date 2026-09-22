"""The beat runner.

Covers the four things an operator can do to a run --- let it go, speed it
up, skip a phase, reset it --- plus the park and resume that FR-H7 requires
to be exact.

Two kinds of workflow appear here. The real narrative from the registry
is used where the content matters, and a purpose-built `tiny` workflow is
used where only the engine's behaviour matters. The reason is the beat
floors: a floor is an absolute number of seconds, so the scaffold's
protected beats cost seven seconds at 1x no matter how small the total
duration is. That is correct for the demo and wrong for a test suite, so
tests that need real delays use a workflow whose floors are small, and
tests that only need to reach the end run at instant speed.
"""

import asyncio
from typing import Any

import pytest

from app.domain.events import Category, Severity
from app.domain.lifecycle import LifecycleState, Phase
from app.domain.state import BlockedOn, RequestKind, SystemState
from app.simulation.beats import AwaitHuman, Beat, Workflow
from app.simulation.engine import SimulationEngine, WorkflowSpec
from app.simulation.protocol import (
    AlreadyRunning,
    EventSource,
    NoPendingRequest,
    RunStatus,
    Speed,
    UnknownRequest,
)
from app.simulation.workflows.registry import NARRATIVE

REQUEST = "sccm-inventory"
TINY_REQUEST = "tiny-request"
TINY_WEIGHT = 50.0


def tiny(state: SystemState) -> Workflow:
    """A workflow with the shape of the real ones and none of the content.

    Same structure --- work, beat, park, resume, work --- so the engine is
    exercised the same way. One small floor, so a test that needs a real
    delay waits milliseconds rather than seconds.
    """
    state.transition(LifecycleState.INITIALIZED)
    yield Beat(weight=10)

    state.transition(LifecycleState.DISCOVERING)
    yield Beat(weight=10)

    state.transition(LifecycleState.DISCOVERY_BLOCKED)
    submission: dict[str, Any] | None = yield AwaitHuman(
        request=BlockedOn(
            kind=RequestKind.CREDENTIALS,
            request_id=TINY_REQUEST,
            prompt="Credentials are required.",
        )
    )

    state.record(
        type="tiny.resumed",
        category=Category.VALIDATION,
        message="Resumed after human input.",
        payload={"fields": sorted((submission or {}).keys())},
    )
    yield Beat(weight=10, floor=0.05)

    state.transition(LifecycleState.DISCOVERING)
    yield Beat(weight=10)

    state.transition(LifecycleState.DISCOVERY_COMPLETE)
    state.transition(LifecycleState.ASSESSING)
    yield Beat(weight=10)

    state.transition(LifecycleState.AWAITING_APPROVAL)


TINY = (WorkflowSpec(name="tiny", factory=tiny),)


def engine(
    workflows=NARRATIVE, *, total: float = 0.2, weight: float = 100.0
) -> SimulationEngine:
    return SimulationEngine(
        SystemState(), workflows, total_duration=total, narrative_weight=weight
    )


def small(total: float = 0.2) -> SimulationEngine:
    """An engine running the `tiny` workflow."""
    return engine(TINY, total=total, weight=TINY_WEIGHT)


async def settle(runner: SimulationEngine, limit: float = 10.0) -> None:
    """Wait until the run finishes or parks on a person."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + limit
    while loop.time() < deadline:
        if runner.status in (RunStatus.AWAITING_HUMAN, RunStatus.COMPLETE):
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Run did not settle; status is {runner.status}.")


async def drive(
    runner: SimulationEngine,
    request_id: str,
    submission: dict[str, Any] | None = None,
) -> None:
    """Start, answer the one request, and run to the end."""
    await runner.start()
    await settle(runner)
    await runner.resolve_human(request_id, submission or {})
    await settle(runner)


# -- The seam ---------------------------------------------------------


def test_the_engine_satisfies_the_protocol() -> None:
    """NFR-A1: a real runtime must be substitutable behind this."""
    assert isinstance(engine(), EventSource)


# -- Pacing -----------------------------------------------------------


def test_beat_weight_scales_with_the_total() -> None:
    beat = Beat(weight=10)
    assert beat.seconds(scale=2.7) == 27.0
    assert beat.seconds(scale=0.27) == 2.7


def test_a_floor_protects_a_beat_from_being_compressed_away() -> None:
    """A recovery the audience does not see is a recovery that did not happen."""
    beat = Beat(weight=5, floor=3.0)
    assert beat.seconds(scale=2.0) == 10.0  # weight wins when the total is generous
    assert beat.seconds(scale=0.1) == 3.0  # the floor holds when it is not


def test_the_scale_is_the_one_number_that_retimes_the_narrative() -> None:
    """D-8."""
    assert engine(total=270.0, weight=100.0).scale == 2.7
    assert engine(total=135.0, weight=100.0).scale == 1.35


# -- Park and resume --------------------------------------------------


@pytest.mark.asyncio
async def test_a_run_parks_on_the_human_request() -> None:
    runner = engine()
    runner.set_speed(Speed.INSTANT)
    await runner.start()
    await settle(runner)

    assert runner.status is RunStatus.AWAITING_HUMAN
    snapshot = runner.snapshot()
    assert snapshot.lifecycle is LifecycleState.DISCOVERY_BLOCKED
    assert snapshot.blocked_on is not None
    assert snapshot.blocked_on.request_id == REQUEST


@pytest.mark.asyncio
async def test_resume_continues_from_the_point_of_suspension() -> None:
    """FR-H7: the generator continues at the yield it parked on."""
    runner = small()
    await runner.start()
    await settle(runner)

    # Nothing after the park has happened yet.
    types = [event.type for event in runner.state.events.all()]
    assert "tiny.resumed" not in types

    await runner.resolve_human(TINY_REQUEST, {"username": "svc"})
    await settle(runner)

    assert runner.snapshot().lifecycle is LifecycleState.AWAITING_APPROVAL
    assert [event.type for event in runner.state.events.all()].count("tiny.resumed") == 1


@pytest.mark.asyncio
async def test_the_submission_reaches_the_workflow() -> None:
    runner = small()
    await drive(runner, TINY_REQUEST, {"username": "svc", "password": "hunter2"})

    resumed = next(
        event for event in runner.state.events.all() if event.type == "tiny.resumed"
    )
    assert resumed.payload == {"fields": ["password", "username"]}


@pytest.mark.asyncio
async def test_no_submitted_value_appears_anywhere_in_the_log() -> None:
    """FR-H5: values are used for the handshake and discarded."""
    runner = engine()
    runner.set_speed(Speed.INSTANT)
    await drive(runner, REQUEST, {"username": "svc-acme", "password": "hunter2"})

    whole_log = " ".join(event.model_dump_json() for event in runner.state.events.all())
    assert "svc-acme" not in whole_log
    assert "hunter2" not in whole_log
    # The field names do travel, so the audit log can say what was asked for.
    assert "username" in whole_log


@pytest.mark.asyncio
async def test_resolving_the_wrong_request_is_refused() -> None:
    runner = small()
    await runner.start()
    await settle(runner)

    with pytest.raises(UnknownRequest):
        await runner.resolve_human("not-the-request", {})

    assert runner.status is RunStatus.AWAITING_HUMAN
    await runner.reset()


@pytest.mark.asyncio
async def test_resolving_when_nothing_is_pending_is_refused() -> None:
    runner = small()
    with pytest.raises(NoPendingRequest):
        await runner.resolve_human(TINY_REQUEST, {})


@pytest.mark.asyncio
async def test_starting_twice_is_refused() -> None:
    runner = small()
    await runner.start()
    with pytest.raises(AlreadyRunning):
        await runner.start()
    await runner.reset()


# -- Speed ------------------------------------------------------------


@pytest.mark.asyncio
async def test_speed_does_not_disturb_event_order_or_state() -> None:
    """FR-O3, compared modulo timestamps and durations (A-2)."""

    async def at(speed: Speed) -> list[tuple[int, str, str]]:
        runner = small(total=0.3)
        runner.set_speed(speed)
        await drive(runner, TINY_REQUEST, {"username": "svc"})
        return [
            (event.sequence, event.type, event.message)
            for event in runner.state.events.all()
        ]

    normal = await at(Speed.NORMAL)
    assert normal == await at(Speed.DOUBLE) == await at(Speed.INSTANT)


@pytest.mark.asyncio
async def test_double_speed_halves_the_wait() -> None:
    async def elapsed(speed: Speed) -> float:
        runner = small(total=1.0)
        runner.set_speed(speed)
        loop = asyncio.get_running_loop()
        started = loop.time()
        await runner.start()
        await settle(runner)
        return loop.time() - started

    at_one = await elapsed(Speed.NORMAL)
    at_two = await elapsed(Speed.DOUBLE)
    assert at_two < at_one * 0.75


@pytest.mark.asyncio
async def test_instant_removes_delay_entirely() -> None:
    runner = engine(total=600.0)  # ten minutes at 1x
    runner.set_speed(Speed.INSTANT)

    loop = asyncio.get_running_loop()
    started = loop.time()
    await runner.start()
    await settle(runner)

    assert runner.status is RunStatus.AWAITING_HUMAN
    assert loop.time() - started < 1.0


@pytest.mark.asyncio
async def test_a_speed_change_lands_inside_the_current_beat() -> None:
    """FR-O3: an operator does not wait out the rest of a long beat."""
    runner = engine(total=600.0)
    loop = asyncio.get_running_loop()

    started = loop.time()
    await runner.start()
    await asyncio.sleep(0.1)
    runner.set_speed(Speed.INSTANT)
    await settle(runner)

    assert loop.time() - started < 2.0


# -- Skip -------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_advances_exactly_one_phase() -> None:
    """FR-O1: the skip is bounded by the phase, not by a countdown.

    At a ten-minute total every beat is tens of seconds long, so nothing
    moves on its own inside this test. What moves is the skip.
    """
    runner = engine(total=600.0)
    await runner.start()
    await asyncio.sleep(0.05)
    assert runner.snapshot().phase is Phase.INIT

    runner.skip_phase()
    await asyncio.sleep(0.3)

    # The skip ran out the rest of INIT and stopped at the boundary
    # rather than carrying on through discovery.
    assert runner.snapshot().phase is Phase.DISCOVERY
    assert runner.status is RunStatus.RUNNING

    await runner.reset()


@pytest.mark.asyncio
async def test_skip_does_not_drop_or_reorder_events() -> None:
    """A skipped phase produces the same events, sooner."""

    async def events_of(skip: bool) -> list[tuple[int, str]]:
        runner = small(total=0.5)
        await runner.start()
        if skip:
            runner.skip_phase()
        await settle(runner)
        await runner.resolve_human(TINY_REQUEST, {})
        await settle(runner)
        return [(event.sequence, event.type) for event in runner.state.events.all()]

    assert await events_of(skip=False) == await events_of(skip=True)


# -- Reset ------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_clears_the_run_and_keeps_the_speed() -> None:
    """FR-O4. Speed is an operator preference, not part of the run."""
    runner = small()
    runner.set_speed(Speed.DOUBLE)
    await runner.start()
    await settle(runner)

    await runner.reset()

    assert runner.status is RunStatus.IDLE
    snapshot = runner.snapshot()
    assert snapshot.lifecycle is LifecycleState.UNINITIALIZED
    assert snapshot.sequence == 0
    assert snapshot.blocked_on is None
    assert runner.speed is Speed.DOUBLE


@pytest.mark.asyncio
async def test_reset_while_parked_then_run_again() -> None:
    runner = small()
    await runner.start()
    await settle(runner)
    await runner.reset()

    await runner.start()
    await settle(runner)
    assert runner.status is RunStatus.AWAITING_HUMAN
    await runner.reset()


@pytest.mark.asyncio
async def test_reset_mid_beat_leaves_nothing_behind() -> None:
    runner = engine(total=600.0)
    await runner.start()
    await asyncio.sleep(0.05)

    await runner.reset()

    assert runner.status is RunStatus.IDLE
    assert runner.snapshot().sequence == 0
    assert runner.consumed_weight == 0.0


# -- Determinism ------------------------------------------------------


@pytest.mark.asyncio
async def test_two_runs_produce_identical_event_sequences() -> None:
    """NFR-D4 as amended by A-2: identical modulo timestamps and durations."""

    async def fingerprint() -> list[tuple]:
        runner = engine()
        runner.set_speed(Speed.INSTANT)
        await drive(runner, REQUEST, {"username": "svc"})
        return [
            (
                event.sequence,
                event.type,
                event.phase,
                event.category,
                event.severity,
                event.message,
                event.payload,
            )
            for event in runner.state.events.all()
        ]

    assert await fingerprint() == await fingerprint()


@pytest.mark.asyncio
async def test_a_reset_run_reproduces_the_first_one() -> None:
    """The path an operator actually takes, rather than two fresh engines."""
    runner = engine()
    runner.set_speed(Speed.INSTANT)

    await drive(runner, REQUEST, {"username": "svc"})
    first = [(event.sequence, event.type, event.message) for event in runner.state.events.all()]

    await runner.reset()
    await drive(runner, REQUEST, {"username": "svc"})
    second = [(event.sequence, event.type, event.message) for event in runner.state.events.all()]

    assert first == second


# -- Calibration ------------------------------------------------------


@pytest.mark.asyncio
async def test_the_narrative_consumes_the_declared_weight() -> None:
    """The calibration that keeps D-8's single number meaningful.

    If a workflow gains or loses beats without `NARRATIVE_WEIGHT` being
    updated, the configured total stops describing the run. That drift
    fails here rather than during a rehearsal.
    """
    from app.config import NARRATIVE_WEIGHT

    runner = engine(weight=NARRATIVE_WEIGHT)
    runner.set_speed(Speed.INSTANT)
    await drive(runner, REQUEST)

    assert runner.status is RunStatus.COMPLETE
    assert runner.consumed_weight == pytest.approx(NARRATIVE_WEIGHT)


@pytest.mark.asyncio
async def test_a_workflow_with_no_beats_completes() -> None:
    def empty(state: SystemState):
        state.transition(LifecycleState.INITIALIZED)
        return
        yield  # pragma: no cover

    runner = engine((WorkflowSpec(name="empty", factory=empty),))
    await runner.start()
    await settle(runner)
    assert runner.status is RunStatus.COMPLETE


@pytest.mark.asyncio
async def test_starting_over_a_finished_run_is_refused() -> None:
    """A finished run is not a startable one.

    Workflows begin by transitioning out of UNINITIALIZED, so a second
    start over a completed run would raise inside the task where nobody
    is watching. Reset is the way back.
    """
    runner = small()
    runner.set_speed(Speed.INSTANT)
    await drive(runner, TINY_REQUEST)
    assert runner.status is RunStatus.COMPLETE

    with pytest.raises(AlreadyRunning):
        await runner.start()

    await runner.reset()
    await runner.start()
    await settle(runner)
    assert runner.status is RunStatus.AWAITING_HUMAN
    await runner.reset()


@pytest.mark.asyncio
async def test_starting_while_parked_is_refused() -> None:
    runner = small()
    await runner.start()
    await settle(runner)

    with pytest.raises(AlreadyRunning):
        await runner.start()

    await runner.reset()


@pytest.mark.asyncio
async def test_a_failing_workflow_is_reported_as_an_event() -> None:
    """FR-E1: all system activity is expressed as events, failure included."""

    def broken(state: SystemState) -> Workflow:
        state.transition(LifecycleState.INITIALIZED)
        yield Beat(weight=1)
        # Illegal from INITIALIZED, so the machine refuses it (FR-L3).
        state.transition(LifecycleState.RUNNING)

    runner = engine((WorkflowSpec(name="broken", factory=broken),), total=0.01)
    runner.set_speed(Speed.INSTANT)
    await runner.start()

    for _ in range(200):
        if any(event.type == "run.failed" for event in runner.state.events.all()):
            break
        await asyncio.sleep(0.01)

    failure = next(
        event for event in runner.state.events.all() if event.type == "run.failed"
    )
    assert failure.severity is Severity.ERROR
    assert failure.payload == {"error": "IllegalTransition"}
    # The state machine held: nothing illegal was applied.
    assert runner.snapshot().lifecycle is LifecycleState.INITIALIZED
