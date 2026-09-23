"""Implementation and run (FR-I1 to FR-I6, FR-L8).

M8's exit criterion: an approved solution builds, tests, becomes Ready,
and Run transitions to its dashboard. Beyond that, these hold the build to
what it claims. Every component passes through all five states in order.
A test reads as passed only once its component has been validated. The
tests are derived from the evidence the solution was approved on, so
revising that evidence changes them. Nothing unapproved is built, and a
rejected solution cannot be run. Every capability-bearing step passes the
gate, and deployment is not asked twice.
"""

import copy
import time
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.domain.lifecycle import LifecycleState
from app.domain.solutions import IllegalSolutionTransition
from app.domain.state import RequestKind, SystemState
from app.knowledge.builds import BLUEPRINTS, ComponentStatus, duration_ms, Suite
from app.knowledge.methodologies import METHODOLOGIES
from app.knowledge.seed_loader import read_bundled
from app.knowledge.solutions import (
    APPROVAL_REQUEST,
    NotRunnable,
    close,
    revise_evidence,
    run,
)
from app.main import app
from app.protection.capabilities import granted
from app.protection.engine import evaluate
from app.protection.rules import Action, ActionRequest, Effect
from app.runtime import state as process_state
from app.simulation.beats import AwaitHuman, Beat
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE
from narrative import finish, run_to_end, settle

TAD, LO, APR = (m.id for m in METHODOLOGIES)
FR_I2 = [status.value for status in ComponentStatus]


def engine() -> SimulationEngine:
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    runner = SimulationEngine(state, NARRATIVE, total_duration=0.2, narrative_weight=100.0)
    runner.set_speed(Speed.INSTANT)
    return runner


@pytest_asyncio.fixture
async def built() -> SystemState:
    """The scripted narrative: every solution approved, built and ready."""
    runner = engine()
    await run_to_end(runner)
    return runner.state


def events_of(state: SystemState, type: str) -> list[Any]:
    return [e for e in state.events.all() if e.type == type]


def implementation(state: SystemState, solution_id: str) -> dict[str, Any]:
    return next(i for i in state.implementations if i["id"] == solution_id)


def timeline(state: SystemState, solution_id: str) -> list[list[dict[str, Any]]]:
    """The component list of one build, as each event carried it."""
    return [
        record["components"]
        for event in state.events.all()
        for record in event.payload.get("implementations", [])
        if record["id"] == solution_id
    ]


# -- Lifecycle ---------------------------------------------------------


@pytest.mark.asyncio
async def test_the_narrative_ends_ready_to_run(built: SystemState) -> None:
    moves = [e.payload["to"] for e in events_of(built, "lifecycle.transition")]
    assert moves[-3:] == ["IMPLEMENTING", "IMPLEMENTATION_COMPLETE", "READY_TO_RUN"]
    assert built.lifecycle is LifecycleState.READY_TO_RUN
    assert built.events.all()[-1].type == "deployment.ready"


@pytest.mark.asyncio
async def test_every_approved_solution_is_ready_with_its_dashboard_named(built: SystemState) -> None:
    """FR-I6: listed as Ready, with the dashboard Run will open."""
    assert [(s["status"], s["dashboardId"]) for s in built.solutions] == [
        ("READY", TAD),
        ("READY", LO),
        ("READY", APR),
    ]
    assert events_of(built, "deployment.ready")[0].payload["ready"] == [TAD, LO, APR]


@pytest.mark.asyncio
async def test_solutions_move_approved_building_ready(built: SystemState) -> None:
    """FR-AP2, as the events carried it."""
    for solution_id in (TAD, LO, APR):
        statuses = [
            record["status"]
            for event in built.events.all()
            for record in event.payload.get("solutions", [])
            if record["id"] == solution_id
        ]
        collapsed = [s for i, s in enumerate(statuses) if i == 0 or s != statuses[i - 1]]
        assert collapsed == ["PROPOSED", "AWAITING_APPROVAL", "APPROVED", "BUILDING", "READY"]


# -- The pipeline (FR-I2) ----------------------------------------------


@pytest.mark.asyncio
async def test_every_component_passes_through_all_five_states_in_order(built: SystemState) -> None:
    for solution_id in (TAD, LO, APR):
        frames = timeline(built, solution_id)
        ids = [c["id"] for c in frames[0]]
        for index, component in enumerate(ids):
            seen = [frame[index]["status"] for frame in frames]
            collapsed = [s for i, s in enumerate(seen) if i == 0 or s != seen[i - 1]]
            assert collapsed == FR_I2, (solution_id, component, collapsed)


@pytest.mark.asyncio
async def test_every_pipeline_is_on_screen_whole_before_any_build_starts(built: SystemState) -> None:
    started = events_of(built, "implementation.started")[0]
    planned = started.payload["implementations"]
    assert [p["id"] for p in planned] == [TAD, LO, APR]
    assert all(c["status"] == "PENDING" for p in planned for c in p["components"])
    assert all(t["status"] == "pending" for p in planned for t in p["tests"])


@pytest.mark.asyncio
async def test_builds_run_one_at_a_time(built: SystemState) -> None:
    """Only one solution is building at any moment in the stream."""
    for event in built.events.all():
        building = [
            r["id"] for r in event.payload.get("implementations", []) if r["status"] == "BUILDING"
        ]
        assert len(building) <= 1


@pytest.mark.asyncio
async def test_the_stream_reports_one_generated_component_at_a_time(built: SystemState) -> None:
    """§28, in realistic terms (FR-I3)."""
    generated = [e.message for e in events_of(built, "implementation.component.built")]
    assert len(generated) == sum(len(BLUEPRINTS[i].components) for i in (TAD, LO, APR))
    assert generated[:6] == [
        "Generated data ingestion service.",
        "Generated schema validation and normalization pipeline.",
        "Generated feature pipeline for per-category baselines.",
        "Generated anomaly detection engine.",
        "Generated analytical API.",
        "Generated dashboard and drill-down views.",
    ]


# -- Tests (FR-I4) -----------------------------------------------------


@pytest.mark.asyncio
async def test_a_test_passes_only_once_its_component_is_validated(built: SystemState) -> None:
    for event in built.events.all():
        for record in event.payload.get("implementations", []):
            status = {c["id"]: c["status"] for c in record["components"]}
            for test in record["tests"]:
                if test["suite"] != Suite.UNIT:
                    continue
                done = status[test["component"]] in ("VALIDATED", "COMPLETE")
                assert (test["status"] == "passed") == done, (event.sequence, test["name"])


@pytest.mark.asyncio
async def test_every_test_is_named_timed_and_passed(built: SystemState) -> None:
    for record in built.implementations:
        assert record["tests"]
        for test in record["tests"]:
            assert test["name"] and test["status"] == "passed"
            assert test["durationMs"] == duration_ms(f"{record['id']}/{test['name']}", test["suite"])
        summary = record["summary"]
        assert summary["total"] == summary["passed"] == len(record["tests"])
        assert summary["failed"] == 0
        assert summary["durationMs"] == sum(t["durationMs"] for t in record["tests"])
        assert {t["suite"] for t in record["tests"]} == {"unit", "integration", "validation"}


@pytest.mark.asyncio
async def test_the_tests_are_derived_from_the_evidence_approved_on(built: SystemState) -> None:
    """One ingestion test per dataset, one validation check per requirement."""
    for record in built.implementations:
        evidence = next(a for a in built.assessments if a["id"] == record["id"])
        datasets = {f["dataset"] for r in evidence["requirements"] for f in r["fields"]}
        assert {d["id"] for d in record["datasets"]} == datasets
        reads = [t for t in record["tests"] if t["name"].startswith("Reads ")]
        assert len(reads) == len(datasets)
        checks = [t for t in record["tests"] if t["suite"] == Suite.VALIDATION]
        assert len(checks) == len(evidence["requirements"])


@pytest.mark.asyncio
async def test_an_insufficiency_becomes_a_check_that_the_conclusion_is_withheld(
    built: SystemState,
) -> None:
    """License Optimization's unit cost is 64% complete (PR-074)."""
    checks = [t for t in implementation(built, LO)["tests"] if t["suite"] == Suite.VALIDATION]
    withheld = [t for t in checks if t["name"].startswith("Withholds")]
    assert len(withheld) == 1
    assert "unit_price is 64% complete" in withheld[0]["note"]
    ready = next(e for e in events_of(built, "solution.ready") if e.payload["solutions"][0]["id"] == LO)
    assert "one conclusion withheld as insufficient" in ready.message


@pytest.mark.asyncio
async def test_revising_the_evidence_before_approval_changes_the_build() -> None:
    runner = engine()
    await runner.start()
    await settle(runner)
    await runner.resolve_human("servicenow-incident-api", {"username": "svc"})
    await settle(runner)
    assert runner.state.blocked_on.kind is RequestKind.APPROVAL
    revise_evidence(runner.state, "sap.contract_item", "unit_price", 0.95)
    await finish(runner)

    checks = [
        t for t in implementation(runner.state, LO)["tests"] if t["suite"] == Suite.VALIDATION
    ]
    assert not [t for t in checks if t["name"].startswith("Withholds")]


# -- Governance --------------------------------------------------------


@pytest.mark.asyncio
async def test_each_build_passes_the_gate_before_it_starts(built: SystemState) -> None:
    decisions = []
    for event in built.events.all():
        if event.type == "policy.decision" and event.payload["verb"] in ("move-data", "invoke-tool"):
            decisions.append((event.payload["verb"], event.payload["effect"], event.payload["rule"]))
        if event.type == "implementation.build.started":
            assert decisions[-2:] == [
                ("move-data", "ALLOW", "PR-040"),
                ("invoke-tool", "ALLOW", "PR-060"),
            ]
    assert len(decisions) == 6


@pytest.mark.asyncio
async def test_deployment_is_escalated_once_and_answered_by_the_approvals(
    built: SystemState,
) -> None:
    deploys = [
        e.payload for e in events_of(built, "policy.decision") if e.payload["verb"] == "deploy"
    ]
    assert [(d["effect"], d["rule"]) for d in deploys] == [("ESCALATE", "PR-053")]
    for event in events_of(built, "solution.ready"):
        record = event.payload["implementations"][0]
        assert record["approval"]["rule"] == "PR-053"
        assert f"#{record['approval']['decidedAt']} (PR-053)" in event.message


def test_the_test_runner_is_granted_and_nothing_else_is() -> None:
    assert granted("test-runner")
    refused = evaluate(
        ActionRequest(
            action=Action.INVOKE_TOOL, resource="shell", tool_granted=granted("shell")
        )
    )
    assert (refused.effect, refused.rule) == (Effect.DENY, "PR-061")


@pytest.mark.asyncio
async def test_a_rejected_solution_is_not_built() -> None:
    runner = engine()
    await run_to_end(runner, decisions={LO: "reject"})
    state = runner.state
    assert [i["id"] for i in state.implementations] == [TAD, APR]
    assert {s["id"]: s["status"] for s in state.solutions}[LO] == "REJECTED"
    started = events_of(state, "implementation.started")[0]
    assert "License Optimization was rejected and will not be built." in started.message


@pytest.mark.asyncio
async def test_with_nothing_approved_the_system_is_ready_with_nothing_to_run() -> None:
    runner = engine()
    await run_to_end(runner, decisions={TAD: "reject", LO: "reject", APR: "reject"})
    state = runner.state
    assert state.lifecycle is LifecycleState.READY_TO_RUN
    assert state.implementations == []
    assert "nothing to run" in state.events.all()[-1].message


# -- Pacing ------------------------------------------------------------


def test_implementation_takes_its_declared_share() -> None:
    """21 of 100 in the scripted narrative: 1 to open, 6 per build, 2 to close."""
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    beats: dict[str, float] = {}
    for spec in NARRATIVE:
        workflow = spec.factory(state)
        answer = None
        while True:
            try:
                yielded = workflow.send(answer)
            except StopIteration:
                break
            answer = None
            if isinstance(yielded, Beat):
                beats[spec.name] = beats.get(spec.name, 0.0) + yielded.weight
            elif isinstance(yielded, AwaitHuman):
                state.unblock()
                if yielded.request.kind is RequestKind.APPROVAL:
                    pending = next(s for s in state.solutions if s["status"] == "AWAITING_APPROVAL")
                    answer = {"solution": pending["id"], "decision": "approve"}
                else:
                    answer = {"username": "svc"}
    assert beats == pytest.approx({"discovery": 54, "assessment": 25, "implementation": 21})


# -- Records -----------------------------------------------------------


@pytest.mark.asyncio
async def test_the_fold_of_the_stream_matches_system_state(built: SystemState) -> None:
    """What the frontend folds is what System State holds (FR-L5, R-5)."""
    run(built, TAD)
    folded: dict[str, dict[str, Any]] = {}
    runtime: dict[str, Any] = {}
    for event in built.events.all():
        for record in event.payload.get("implementations", []):
            folded[record["id"]] = record
        if "runtime" in event.payload:
            runtime = event.payload["runtime"]
    assert list(folded.values()) == built.implementations
    assert runtime == built.runtime


@pytest.mark.asyncio
async def test_recorded_build_events_do_not_change_afterwards(built: SystemState) -> None:
    """FR-E7: the record keeps changing; what an event said does not."""
    first = events_of(built, "implementation.build.started")[0]
    assert first.payload["implementations"][0]["components"][0]["status"] == "BUILDING"
    assert all(t["status"] == "pending" for t in first.payload["implementations"][0]["tests"])


@pytest.mark.asyncio
async def test_two_runs_build_identically() -> None:
    """NFR-D4, durations included: they are checksums, not clocks."""
    first, second = engine(), engine()
    await run_to_end(first)
    await run_to_end(second)
    assert first.state.implementations == second.state.implementations
    assert [(e.type, e.message) for e in first.state.events.all()] == [
        (e.type, e.message) for e in second.state.events.all()
    ]


def test_no_source_code_is_produced() -> None:
    """FR-I5: a component is a name and a status, never an artefact."""
    for blueprint in BLUEPRINTS.values():
        for component in blueprint.components:
            assert set(vars(component)) == {"id", "stage", "name", "generated", "tests"}


# -- Run (FR-L8) -------------------------------------------------------


@pytest.mark.asyncio
async def test_run_opens_a_solution_and_return_makes_the_next_runnable(built: SystemState) -> None:
    run(built, TAD)
    assert built.lifecycle is LifecycleState.RUNNING
    assert built.runtime["active"] == TAD
    assert {s["id"]: s["status"] for s in built.solutions}[TAD] == "RUNNING"

    close(built, TAD)
    assert built.lifecycle is LifecycleState.READY_TO_RUN
    assert built.runtime["active"] is None
    assert all(s["status"] == "READY" for s in built.solutions)

    run(built, APR)
    close(built, APR)
    run(built, TAD)
    runs = built.runtime["runs"]
    assert [r["solutionId"] for r in runs] == [TAD, APR, TAD]
    assert [r["closedAt"] is None for r in runs] == [False, False, True]
    assert [e.type for e in built.events.all()[-2:]] == ["lifecycle.transition", "solution.started"]


@pytest.mark.asyncio
async def test_one_solution_runs_at_a_time(built: SystemState) -> None:
    run(built, TAD)
    before = (len(built.events.all()), copy.deepcopy(built.solutions), built.lifecycle)
    with pytest.raises(NotRunnable, match="Ticket Anomaly Detection is running"):
        run(built, LO)
    with pytest.raises(NotRunnable):
        close(built, LO)
    assert (len(built.events.all()), built.solutions, built.lifecycle) == before


@pytest.mark.asyncio
async def test_a_rejected_solution_cannot_be_run() -> None:
    runner = engine()
    await run_to_end(runner, decisions={LO: "reject"})
    before = len(runner.state.events.all())
    with pytest.raises(IllegalSolutionTransition):
        run(runner.state, LO)
    assert runner.state.lifecycle is LifecycleState.READY_TO_RUN
    assert len(runner.state.events.all()) == before


@pytest.mark.asyncio
async def test_nothing_runs_before_implementation_is_complete() -> None:
    runner = engine()
    await runner.start()
    await settle(runner)
    await runner.resolve_human("servicenow-incident-api", {"username": "svc"})
    await settle(runner)
    # Proposed and awaiting a decision: it exists, and it is not runnable.
    with pytest.raises(NotRunnable, match="AWAITING_APPROVAL"):
        run(runner.state, TAD)
    await finish(runner)
    assert runner.status is RunStatus.COMPLETE


# -- Over HTTP ---------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    process_state.reset()
    with TestClient(app) as connection:
        yield connection
        connection.post("/api/operator/reset")
    process_state.reset()


def test_run_and_return_over_http(client: TestClient) -> None:
    client.post("/api/seed/initialize", json={"layers": read_bundled()})
    client.post("/api/operator/speed", json={"speed": "instant"})
    client.post("/api/operator/start")
    assert client.post(f"/api/solutions/{TAD}/run").status_code == 404  # not yet proposed

    refused_while_deciding = False
    for _ in range(2000):
        snapshot = client.get("/api/state").json()
        blocked = snapshot["blockedOn"]
        if snapshot["lifecycle"] == "READY_TO_RUN":
            break
        if blocked and blocked["requestId"] == APPROVAL_REQUEST:
            if not refused_while_deciding:
                assert client.post(f"/api/solutions/{TAD}/run").status_code == 409
                refused_while_deciding = True
            waiting = next(s for s in snapshot["solutions"] if s["status"] == "AWAITING_APPROVAL")
            client.post(f"/api/solutions/{waiting['id']}/decision", json={"decision": "approve"})
        elif blocked:
            client.post(f"/api/human/{blocked['requestId']}", json={"username": "svc"})
        time.sleep(0.005)
    assert snapshot["lifecycle"] == "READY_TO_RUN"
    assert refused_while_deciding
    assert [i["summary"]["passed"] for i in snapshot["implementations"]] == [
        len(i["tests"]) for i in snapshot["implementations"]
    ]

    opened = client.post(f"/api/solutions/{TAD}/run")
    assert opened.status_code == 200
    assert opened.json()["lifecycle"] == "RUNNING"
    assert opened.json()["runtime"]["active"] == TAD
    assert client.post(f"/api/solutions/{LO}/run").status_code == 409
    assert client.post(f"/api/solutions/{LO}/close").status_code == 409
    assert client.post("/api/solutions/nope/run").status_code == 404

    closed = client.post(f"/api/solutions/{TAD}/close")
    assert closed.status_code == 200
    assert closed.json()["lifecycle"] == "READY_TO_RUN"
    assert client.post(f"/api/solutions/{LO}/run").status_code == 200
