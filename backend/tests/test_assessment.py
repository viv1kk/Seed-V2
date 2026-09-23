"""Assessment and approval (FR-A1 to FR-A10, FR-AP1 to FR-AP4).

The load-bearing test here is the one M7's exit criterion names: revise a
data source's field completeness and a feasibility grade moves. If the
grades were authored, nothing would move. Everything else checks that the
grade the narrative shows is the one the rules produce, that weak
evidence is reported as weak rather than hidden, and that no solution
advances without a recorded human decision.
"""

import copy
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.lifecycle import LifecycleState
from app.domain.solutions import (
    IllegalSolutionTransition,
    SolutionStatus,
    assert_solution_transition,
)
from app.domain.state import RequestKind, SystemState
from app.knowledge.feasibility import Grade, Standing, assess, grade_of, standing_of
from app.knowledge.methodologies import BY_ID, METHODOLOGIES
from app.knowledge.solutions import (
    APPROVAL_REQUEST,
    InvalidDecision,
    awaiting,
    decide,
    revise_evidence,
)
from app.knowledge.seed_loader import read_bundled
from app.main import app
from app.runtime import state as process_state
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE
from narrative import finish, run_to_end, settle

TAD, LO, APR = (m.id for m in METHODOLOGIES)


def engine() -> SimulationEngine:
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    runner = SimulationEngine(state, NARRATIVE, total_duration=0.2, narrative_weight=100.0)
    runner.set_speed(Speed.INSTANT)
    return runner


async def parked_on_approval() -> SimulationEngine:
    """A run that has assessed everything and waits on the first decision."""
    runner = engine()
    await runner.start()
    await settle(runner)
    await runner.resolve_human("servicenow-incident-api", {"username": "svc"})
    await settle(runner)
    assert runner.state.blocked_on is not None
    assert runner.state.blocked_on.kind is RequestKind.APPROVAL
    return runner


def graded(state: SystemState) -> dict[str, str]:
    return {a["id"]: a["feasibility"] for a in state.assessments}


# -- The rules ---------------------------------------------------------


@pytest.mark.parametrize(
    ("coverage", "standing"),
    [
        (1.0, Standing.SUFFICIENT),
        (0.90, Standing.SUFFICIENT),
        (0.899, Standing.LIMITED),
        (0.70, Standing.LIMITED),
        (0.699, Standing.INCOMPLETE),
        (0.0, Standing.INCOMPLETE),
        (None, Standing.MISSING),
    ],
)
def test_a_requirement_is_as_good_as_its_coverage(coverage: float | None, standing: Standing) -> None:
    assert standing_of(coverage) is standing


def test_feasibility_is_graded_never_binary() -> None:
    """FR-A3: four grades, each reachable."""
    S, L, I, M = Standing.SUFFICIENT, Standing.LIMITED, Standing.INCOMPLETE, Standing.MISSING
    assert grade_of([S, S, S]) is Grade.HIGH
    assert grade_of([S, L, S]) is Grade.MEDIUM
    assert grade_of([S, L, I]) is Grade.PARTIAL
    assert grade_of([S, S, M]) is Grade.LOW
    assert grade_of([I, I, S]) is Grade.LOW


def test_a_requirement_is_only_as_good_as_its_weakest_field() -> None:
    environment = {
        "dataSources": [
            {
                "id": "d",
                "label": "d",
                "system": "s",
                "fields": [
                    {"name": "a", "concept": "unit-cost", "completeness": 1.0},
                    {"name": "b", "concept": "unit-cost", "completeness": 0.5},
                ],
            }
        ]
    }
    result = assess(BY_ID[LO], environment)
    cost = next(r for r in result["requirements"] if r["concept"] == "unit-cost")
    assert cost["coverage"] == 0.5
    assert cost["weakest"]["field"] == "b"


# -- The narrative's assessments --------------------------------------


@pytest.mark.asyncio
async def test_the_three_methodologies_are_graded_by_their_evidence() -> None:
    """FR-A1, FR-A5, and §51's spread: not every methodology is feasible alike."""
    runner = await parked_on_approval()
    assert graded(runner.state) == {TAD: "HIGH", LO: "PARTIAL", APR: "MEDIUM"}
    await runner.reset()


@pytest.mark.asyncio
async def test_every_assessment_carries_what_fr_a4_requires() -> None:
    runner = await parked_on_approval()
    for result in runner.state.assessments:
        assert result["feasibility"] in set(Grade)
        assert 0 <= result["dataSufficiency"] <= 1
        assert result["coverage"]["required"] == len(BY_ID[result["id"]].requires)
        assert all("standing" in r and "weakest" in r for r in result["requirements"])
        assert isinstance(result["limitations"], list)
        assert result["recommendation"]
        assert result["process"], "FR-A9 needs the process chain"
        assert result["simulated"] is True  # FR-A10
    await runner.reset()


@pytest.mark.asyncio
async def test_licence_optimization_is_partial_for_the_stated_reason() -> None:
    """FR-A5 and FR-A6: the limitation names its figure, and the fix names its effect."""
    runner = await parked_on_approval()
    licence = next(a for a in runner.state.assessments if a["id"] == LO)

    cost = next(r for r in licence["requirements"] if r["concept"] == "unit-cost")
    assert cost["standing"] is Standing.INCOMPLETE
    assert any("contract_item.unit_price is 64% complete" in line for line in licence["limitations"])

    (improvement,) = licence["improvements"]
    assert improvement["concept"] == "unit-cost"
    assert improvement["from"] == "PARTIAL" and improvement["to"] == "HIGH"
    assert "64%" in improvement["target"]
    await runner.reset()


@pytest.mark.asyncio
async def test_weak_evidence_is_reported_as_insufficient_not_hidden() -> None:
    """FR-H4: the first insufficiency the narrative produces."""
    runner = await parked_on_approval()
    insufficient = [e for e in runner.state.events.all() if e.type == "assessment.evidence.insufficient"]
    assert [e.payload["concept"] for e in insufficient] == ["unit-cost"]
    await runner.reset()


@pytest.mark.asyncio
async def test_the_evidence_behind_each_assessment_is_recorded_under_policy() -> None:
    runner = await parked_on_approval()
    records = [
        e.payload for e in runner.state.events.all()
        if e.type == "policy.decision" and e.payload["verb"] == "record-evidence"
    ]
    assert len(records) == len(METHODOLOGIES)
    assert all(r["effect"] == "ALLOW" and r["rule"] == "PR-070" for r in records)
    await runner.reset()


# -- FR-A2: computed, not authored (M7's exit criterion) --------------


@pytest.mark.asyncio
async def test_revising_evidence_moves_the_grade() -> None:
    runner = await parked_on_approval()
    state = runner.state

    revise_evidence(state, "sap.contract_item", "unit_price", 0.95)
    assert graded(state)[LO] == "HIGH"

    revise_evidence(state, "sap.contract_item", "unit_price", 0.30)
    assert graded(state)[LO] == "PARTIAL"

    revise_evidence(state, "servicenow.incident", "resolved_at", 0.5)
    assert graded(state)[TAD] == "PARTIAL"

    revised = [e for e in state.events.all() if e.type == "assessment.evidence.revised"]
    assert len(revised) == 3
    assert "License Optimization PARTIAL to HIGH" in revised[0].message
    await runner.reset()


@pytest.mark.asyncio
async def test_a_revision_never_rewrites_an_event_already_recorded() -> None:
    """FR-E7: replay must return what was said at the time."""
    runner = await parked_on_approval()
    state = runner.state
    evaluated = next(
        e for e in state.events.all()
        if e.type == "assessment.methodology.evaluated" and e.payload["methodology"] == "License Optimization"
    )
    before = copy.deepcopy(evaluated.payload)

    revise_evidence(state, "sap.contract_item", "unit_price", 0.95)

    assert evaluated.payload == before
    assert evaluated.payload["assessments"][0]["feasibility"] == "PARTIAL"
    await runner.reset()


@pytest.mark.asyncio
async def test_an_approval_keeps_the_evidence_it_was_made_on() -> None:
    runner = await parked_on_approval()
    state = runner.state
    decide(state, LO, "approve", "PR-053")
    revise_evidence(state, "sap.contract_item", "unit_price", 0.95)

    (approval,) = state.approvals
    assert approval["feasibility"] == "PARTIAL"
    assert graded(state)[LO] == "HIGH"
    await runner.reset()


# -- Approval (FR-AP1 to FR-AP4) --------------------------------------


@pytest.mark.asyncio
async def test_the_run_waits_until_every_solution_has_a_decision() -> None:
    runner = await parked_on_approval()
    state = runner.state
    assert state.lifecycle is LifecycleState.AWAITING_APPROVAL
    assert [s["status"] for s in state.solutions] == ["AWAITING_APPROVAL"] * 3

    await runner.resolve_human(APPROVAL_REQUEST, {"solution": TAD, "decision": "approve"})
    await settle(runner)
    assert runner.status is RunStatus.AWAITING_HUMAN
    assert "2 of 3" in state.blocked_on.prompt

    await runner.resolve_human(APPROVAL_REQUEST, {"solution": APR, "decision": "reject"})
    await settle(runner)
    await runner.resolve_human(APPROVAL_REQUEST, {"solution": LO, "decision": "approve"})
    await settle(runner)

    assert runner.status is RunStatus.COMPLETE
    # Approved solutions go on to be built (M8); the rejection is final.
    assert {s["id"]: s["status"] for s in state.solutions} == {
        TAD: "READY",
        LO: "READY",
        APR: "REJECTED",
    }
    assert [(a["solutionId"], a["decision"]) for a in state.approvals] == [
        (TAD, "APPROVED"),
        (APR, "REJECTED"),
        (LO, "APPROVED"),
    ]
    assert all(a["rule"] == "PR-053" for a in state.approvals)
    completed = next(e for e in state.events.all() if e.type == "approval.completed")
    assert completed.payload == {"approved": 2, "rejected": 1}


@pytest.mark.asyncio
async def test_every_solution_is_approvable_whatever_its_grade() -> None:
    """FR-AP4: approvable, and runnable once approved, whatever the grade.

    A PARTIAL grade is a stated limitation, not a blocker (FR-A5).
    """
    runner = engine()
    await run_to_end(runner)
    assert all(a["decision"] == "APPROVED" for a in runner.state.approvals)
    assert all(s["status"] == "READY" for s in runner.state.solutions)


@pytest.mark.asyncio
async def test_an_invalid_answer_records_nothing_and_the_question_stands() -> None:
    runner = await parked_on_approval()
    before = len(runner.state.approvals)
    await runner.resolve_human(APPROVAL_REQUEST, {"solution": "nonexistent", "decision": "approve"})
    await settle(runner)

    assert runner.status is RunStatus.AWAITING_HUMAN
    assert len(runner.state.approvals) == before
    assert len(awaiting(runner.state)) == 3
    await finish(runner)


@pytest.mark.asyncio
async def test_a_decision_is_made_once() -> None:
    runner = await parked_on_approval()
    decide(runner.state, TAD, "reject", "PR-053")
    with pytest.raises(InvalidDecision):
        decide(runner.state, TAD, "approve", "PR-053")
    await runner.reset()


def test_rejection_is_terminal_and_nothing_skips_approval() -> None:
    """FR-AP1, FR-AP2."""
    with pytest.raises(IllegalSolutionTransition):
        assert_solution_transition("x", SolutionStatus.REJECTED, SolutionStatus.APPROVED)
    with pytest.raises(IllegalSolutionTransition):
        assert_solution_transition("x", SolutionStatus.PROPOSED, SolutionStatus.BUILDING)
    with pytest.raises(IllegalSolutionTransition):
        assert_solution_transition("x", SolutionStatus.AWAITING_APPROVAL, SolutionStatus.BUILDING)


@pytest.mark.asyncio
async def test_the_screen_can_rebuild_solutions_from_the_stream() -> None:
    """Upserting every record the events carry reproduces System State (R-5)."""
    runner = engine()
    await run_to_end(runner, decisions={LO: "reject"})
    revise_evidence(runner.state, "sap.contract_item", "unit_price", 0.95)

    rebuilt: dict[str, list[dict[str, Any]]] = {"assessments": [], "solutions": [], "approvals": []}
    for event in runner.state.events.all():
        for key, records in rebuilt.items():
            for record in event.payload.get(key, []):
                index = next((i for i, r in enumerate(records) if r["id"] == record["id"]), None)
                if index is None:
                    records.append(record)
                else:
                    records[index] = {**records[index], **record}

    assert rebuilt["assessments"] == runner.state.assessments
    assert rebuilt["solutions"] == runner.state.solutions
    assert rebuilt["approvals"] == runner.state.approvals


# -- Over HTTP ---------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    process_state.reset()
    with TestClient(app) as connection:
        yield connection
        connection.post("/api/operator/reset")
    process_state.reset()


def wait_for(client: TestClient, status: str) -> None:
    for _ in range(500):
        if client.get("/api/operator").json()["status"] == status:
            return
        time.sleep(0.01)
    raise AssertionError(f"never reached {status}")


def wait_for_decision(client: TestClient) -> None:
    """The run re-asks after each decision; wait until it has."""
    for _ in range(500):
        blocked = client.get("/api/state").json()["blockedOn"]
        if blocked and blocked["requestId"] == APPROVAL_REQUEST:
            return
        time.sleep(0.01)
    raise AssertionError("the run never asked for a decision")


def test_decisions_and_revisions_over_http(client: TestClient) -> None:
    client.post("/api/seed/initialize", json={"layers": read_bundled()})
    client.post("/api/operator/speed", json={"speed": "instant"})

    # Not parked on a decision yet: refused, with nothing sent to the run.
    client.post("/api/operator/start")
    wait_for(client, "awaiting-human")
    assert client.post(f"/api/solutions/{TAD}/decision", json={"decision": "approve"}).status_code == 409

    client.post("/api/human/servicenow-incident-api", json={"username": "svc"})
    wait_for_decision(client)

    assert client.post("/api/solutions/nope/decision", json={"decision": "approve"}).status_code == 409
    assert client.post(f"/api/solutions/{TAD}/decision", json={"decision": "maybe"}).status_code == 422

    revised = client.post(
        "/api/environment/sources/sap.contract_item/fields/unit_price", json={"completeness": 0.95}
    )
    assert revised.status_code == 200
    grades = {a["id"]: a["feasibility"] for a in revised.json()["assessments"]}
    assert grades[LO] == "HIGH"

    assert client.post(
        "/api/environment/sources/sap.nothing/fields/x", json={"completeness": 0.5}
    ).status_code == 404
    assert client.post(
        "/api/environment/sources/sap.contract_item/fields/unit_price", json={"completeness": 1.5}
    ).status_code == 422

    for solution in (TAD, LO, APR):
        wait_for_decision(client)
        assert client.post(f"/api/solutions/{solution}/decision", json={"decision": "approve"}).status_code == 200
    wait_for(client, "complete")
    snapshot = client.get("/api/state").json()
    assert [s["status"] for s in snapshot["solutions"]] == ["READY"] * 3
    assert len(snapshot["approvals"]) == 3
