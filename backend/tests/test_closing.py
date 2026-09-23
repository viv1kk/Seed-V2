"""Closing the seeding phase (M18, D-16, FR-C1 to FR-C7).

A person confirms, and closing then cleans up after the build in four
policy-decided steps before handing over to Life. These hold it to that:
the new edges and no others, a confirmation that states what and why,
each step decided under its own rule, the seed untouched, and a skip that
passes through.
"""

import copy
import time
from typing import Any

import pytest
import pytest_asyncio

from app.domain.lifecycle import TRANSITIONS, LifecycleState, can_transition
from app.domain.state import RequestKind, SystemState
from app.knowledge.methodologies import METHODOLOGIES
from app.protection.capabilities import BUILD_TOOLS
from app.protection.engine import evaluate
from app.protection.rules import Action, ActionRequest, Effect
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.closing import CLOSE_LABEL, CLOSE_REQUEST
from app.simulation.workflows.registry import NARRATIVE
from narrative import finish, run_to_end, settle

TAD, LO, APR = (m.id for m in METHODOLOGIES)

STEPS = [
    "seeding.notes.consolidated",
    "seeding.scratch.cleared",
    "seeding.interfaces.promoted",
    "seeding.tools.retired",
]


def engine(speed: Speed = Speed.INSTANT, total: float = 0.2) -> SimulationEngine:
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    state.seed = {"layers": [{"layer": name} for name in ("core", "adaptation", "protection")]}
    runner = SimulationEngine(state, NARRATIVE, total_duration=total, narrative_weight=105.0)
    runner.set_speed(speed)
    return runner


async def parked_on_closing(runner: SimulationEngine) -> SimulationEngine:
    """Run until the confirmation, answering everything before it."""
    await runner.start()
    while True:
        await settle(runner, limit=30.0)
        pending = runner.state.blocked_on
        if pending is not None and pending.kind is RequestKind.CONFIRMATION:
            return runner
        if pending is None:
            raise AssertionError("the run finished without asking to close seeding")
        if pending.kind is RequestKind.APPROVAL:
            target = next(s for s in runner.state.solutions if s["status"] == "AWAITING_APPROVAL")
            await runner.resolve_human(
                pending.request_id, {"solution": target["id"], "decision": "approve"}
            )
        else:
            await runner.resolve_human(pending.request_id, {"username": "svc"})


@pytest_asyncio.fixture
async def closed() -> SystemState:
    runner = engine()
    await run_to_end(runner)
    return runner.state


def events_of(state: SystemState, type: str) -> list[Any]:
    return [e for e in state.events.all() if e.type == type]


def after(state: SystemState, type: str) -> list[Any]:
    """Every event from the first `type` onward."""
    events = state.events.all()
    start = next(i for i, e in enumerate(events) if e.type == type)
    return events[start:]


# -- The lifecycle (FR-L9) ---------------------------------------------


def test_closing_sits_between_implementation_complete_and_ready_to_run() -> None:
    assert TRANSITIONS[LifecycleState.IMPLEMENTATION_COMPLETE] == frozenset(
        {LifecycleState.CLOSING_SEEDING}
    )
    assert TRANSITIONS[LifecycleState.CLOSING_SEEDING] == frozenset({LifecycleState.READY_TO_RUN})


def test_the_direct_edge_to_ready_to_run_is_gone() -> None:
    assert not can_transition(LifecycleState.IMPLEMENTATION_COMPLETE, LifecycleState.READY_TO_RUN)
    # And closing cannot be skipped back into, or jumped past into running.
    assert not can_transition(LifecycleState.CLOSING_SEEDING, LifecycleState.RUNNING)
    assert not can_transition(LifecycleState.READY_TO_RUN, LifecycleState.CLOSING_SEEDING)
    assert not can_transition(LifecycleState.IMPLEMENTING, LifecycleState.CLOSING_SEEDING)


def test_closing_is_the_last_act_of_seeding_not_the_first_of_life() -> None:
    state = SystemState()
    for target in (
        LifecycleState.INITIALIZED,
        LifecycleState.DISCOVERING,
        LifecycleState.DISCOVERY_COMPLETE,
        LifecycleState.ASSESSING,
        LifecycleState.AWAITING_APPROVAL,
        LifecycleState.IMPLEMENTING,
        LifecycleState.IMPLEMENTATION_COMPLETE,
        LifecycleState.CLOSING_SEEDING,
    ):
        state.transition(target)
    assert state.phase.value == "IMPLEMENTATION"


# -- The confirmation (FR-C1, FR-C2) -----------------------------------


@pytest.mark.asyncio
async def test_the_narrative_pauses_once_more_to_confirm_closing() -> None:
    runner = await parked_on_closing(engine())
    state = runner.state
    request = state.blocked_on

    assert state.lifecycle is LifecycleState.IMPLEMENTATION_COMPLETE
    assert runner.status is RunStatus.AWAITING_HUMAN
    assert request.kind is RequestKind.CONFIRMATION
    assert request.request_id == CLOSE_REQUEST
    # What will happen, what it touches, and why (FR-H2).
    assert "clean up" in request.prompt
    assert request.access and request.reason
    assert [(o.value, o.label) for o in request.options] == [("close", CLOSE_LABEL)]
    assert CLOSE_LABEL == "Run — clean up and close seeding"
    # Nothing has been cleaned up before the person confirms.
    assert state.closing == {}
    assert not events_of(state, "seeding.closing.started")

    await finish(runner)
    assert runner.status is RunStatus.COMPLETE
    assert state.lifecycle is LifecycleState.READY_TO_RUN


# -- The four steps (FR-C3, FR-C4) ------------------------------------


@pytest.mark.asyncio
async def test_each_step_is_reported_in_order_after_its_decision(closed: SystemState) -> None:
    tail = [e.type for e in after(closed, "seeding.closing.started")]
    steps = [t for t in tail if t.startswith("seeding.")]
    assert steps == ["seeding.closing.started", *STEPS, "seeding.consumed"]
    # Each step's report follows at least one policy decision of its own.
    for step in STEPS:
        index = tail.index(step)
        previous = tail.index(STEPS[STEPS.index(step) - 1]) if step != STEPS[0] else 0
        assert "policy.decision" in tail[previous:index]
    assert tail[-2:] == ["lifecycle.transition", "deployment.ready"]


@pytest.mark.asyncio
async def test_each_operation_is_decided_under_its_own_rule(closed: SystemState) -> None:
    decisions = [
        (e.payload["verb"], e.payload["effect"], e.payload["rule"])
        for e in after(closed, "seeding.closing.started")
        if e.type == "policy.decision"
    ]
    assert decisions == [
        (Action.CONSOLIDATE_RECORDS, Effect.ALLOW, "PR-090"),
        (Action.CLEAR_SCRATCH, Effect.ALLOW, "PR-091"),
        *[(Action.PROMOTE_INTERFACE, Effect.ALLOW, "PR-093")] * 3,
        *[(Action.RETIRE_TOOL, Effect.ALLOW, "PR-095")] * len(BUILD_TOOLS),
    ]


@pytest.mark.asyncio
async def test_the_closing_record_says_what_was_done(closed: SystemState) -> None:
    record = closed.closing
    assert record["record"]["total"] == sum(
        record["record"][k] for k in ("discovery", "assessment", "build")
    )
    assert record["scratch"] == {
        "datasets": sum(len(i["datasets"]) for i in closed.implementations),
        "released": True,
    }
    assert [p["id"] for p in record["promoted"]] == [TAD, LO, APR]
    assert all(p["approvedAt"] is not None for p in record["promoted"])
    assert record["retired"] == list(BUILD_TOOLS)
    assert record["consumed"] is True
    assert closed.snapshot().closing == record


@pytest.mark.asyncio
async def test_a_rejected_component_is_not_promoted() -> None:
    runner = engine()
    await run_to_end(runner, decisions={LO: "reject"})
    promoted = [p["id"] for p in runner.state.closing["promoted"]]
    assert promoted == [TAD, APR]


# -- The rules (FR-C4) ------------------------------------------------


def _request(action: Action, **facts: Any) -> ActionRequest:
    return ActionRequest(action=action, resource="test resource", **facts)


def test_scratch_is_released_and_client_data_is_not() -> None:
    """The contrast D-16 asks for: the system's scratch, not a source record."""
    own = evaluate(_request(Action.CLEAR_SCRATCH, system_owned=True))
    theirs = evaluate(_request(Action.CLEAR_SCRATCH, system_owned=False))
    source = evaluate(_request(Action.DELETE_SOURCE, in_scope=True))
    assert (own.effect, own.rule) == (Effect.ALLOW, "PR-091")
    assert (theirs.effect, theirs.rule) == (Effect.DENY, "PR-092")
    assert (source.effect, source.rule) == (Effect.DENY, "PR-051")


def test_promotion_reads_the_recorded_approval() -> None:
    approved = evaluate(_request(Action.PROMOTE_INTERFACE, deployment_approved=True))
    unapproved = evaluate(_request(Action.PROMOTE_INTERFACE, deployment_approved=False))
    assert (approved.effect, approved.rule) == (Effect.ALLOW, "PR-093")
    assert (unapproved.effect, unapproved.rule) == (Effect.ESCALATE, "PR-094")


def test_a_tool_is_retired_only_once_the_build_is_complete() -> None:
    done = evaluate(_request(Action.RETIRE_TOOL, system_owned=True, build_complete=True))
    midway = evaluate(_request(Action.RETIRE_TOOL, system_owned=True, build_complete=False))
    foreign = evaluate(_request(Action.RETIRE_TOOL, system_owned=False, build_complete=True))
    unstated = evaluate(_request(Action.RETIRE_TOOL, system_owned=True))
    assert (done.effect, done.rule) == (Effect.ALLOW, "PR-095")
    assert (midway.effect, midway.rule) == (Effect.ESCALATE, "PR-096")
    assert (foreign.effect, foreign.rule) == (Effect.DENY, "PR-092")
    assert (unstated.effect, unstated.rule, unstated.missing) == (
        Effect.DENY,
        "PR-000",
        ["build_complete"],
    )


# -- Simulated only (FR-C5, FR-S6) ------------------------------------


@pytest.mark.asyncio
async def test_closing_leaves_the_seed_as_it_was() -> None:
    runner = await parked_on_closing(engine())
    seed = copy.deepcopy(runner.state.seed)
    await finish(runner)
    assert runner.state.seed == seed
    consumed = events_of(runner.state, "seeding.consumed")[0]
    assert "seed files are unchanged" in consumed.message
    assert consumed.payload["layers"] == 3


# -- Operator skip (FR-C7) ----------------------------------------------


@pytest.mark.asyncio
async def test_skip_passes_through_closing() -> None:
    # At 1x with a long total, closing's beats would take seconds. A skip
    # taken as it starts carries the run through to the hand-over.
    runner = await parked_on_closing(engine(Speed.INSTANT, total=60.0))
    runner.set_speed(Speed.NORMAL)
    await runner.resolve_human(CLOSE_REQUEST, {"acknowledged": True, "choice": "close"})
    runner.skip_phase()
    started = time.monotonic()
    await settle(runner, limit=5.0)
    assert runner.status is RunStatus.COMPLETE
    assert runner.state.lifecycle is LifecycleState.READY_TO_RUN
    assert time.monotonic() - started < 2.0
