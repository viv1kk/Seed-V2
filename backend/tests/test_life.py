"""Life: collection and recalibration (M19, D-17, FR-LF4 to FR-LF11, FR-AN10).

Collection reveals records the generators already made, one simulated
week a step, and every four steps a recalibration moves the baselines and
confirms clusters. These hold that to the rows:

- the step term narrows every figure to what has been collected, checked
  against record-level ground truth at several steps;
- the caught-up state is the full dataset, and the last calibration is
  the generated frames;
- a pinned step reads the same figures however far collection has gone;
- the Life workflow reports what arrived and what moved, from the rows;
- two runs from Reset produce the same collection and recalibration;
- speed, skip and Reset apply.
"""

import asyncio
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.analytics.evidence import evidence
from app.analytics.generator import CALIBRATIONS, COLLECTED, EVERY, STEPS, calibration_of
from app.analytics.query import FilterContext, Selection, run
from app.analytics.store import STORE, Dataset
from app.domain.lifecycle import LifecycleState
from app.domain.presentation import Presentation, presentation_of
from app.domain.state import SystemState
from app.knowledge.methodologies import METHODOLOGIES
from app.knowledge.seed_loader import read_bundled
from app.main import app
from app.runtime import state as process_state
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import LIFE, NARRATIVE
from narrative import run_to_end, settle

TAD, LO, APR = (m.id for m in METHODOLOGIES)
STEPS_TO_CHECK = [0, 1, 4, 7, 8, 11, STEPS]
EVENTS_STORE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "stores" / "events.ts"


def dataset(solution_id: str) -> Dataset:
    return STORE.get(solution_id)


def figures(answer: dict[str, Any]) -> dict[str, Any]:
    """A query answer without its timing, for comparison."""
    return {k: v for k, v in answer["views"].items()}


# -- The step term, against the rows (FR-LF7, FR-AN10) ------------------


@pytest.mark.parametrize("solution", [TAD, LO, APR])
@pytest.mark.parametrize("step", STEPS_TO_CHECK)
def test_the_step_narrows_every_frame_to_what_has_been_collected(solution, step) -> None:
    ds = dataset(solution)
    selection = Selection(ds, FilterContext(step=step))
    for frame_id, frame in ds.frames.items():
        expected = int((frame[COLLECTED].to_numpy() <= step).sum())
        assert len(selection.rows(frame_id)) == expected, frame_id


@pytest.mark.parametrize("step", STEPS_TO_CHECK)
def test_ticket_kpis_count_only_collected_tickets(step) -> None:
    ds = dataset(TAD)
    frame = ds.primary
    seen = frame[frame[COLLECTED] <= step]
    answer = run(ds, FilterContext(step=step), ["k-tickets", "k-anomalies"])["views"]
    assert answer["k-tickets"]["value"] == len(seen)
    assert answer["k-tickets"]["total"] == len(seen)
    assert answer["k-anomalies"]["value"] == int(seen["anomalous"].sum())


@pytest.mark.parametrize("step", [3, 8, STEPS])
def test_a_filter_and_the_step_combine(step) -> None:
    ds = dataset(TAD)
    frame = ds.primary
    wanted = (frame[COLLECTED] <= step) & (frame["assignmentGroup"] == "Network Operations")
    context = FilterContext(step=step, dimensions={"group": ["Network Operations"]})
    answer = run(ds, context, ["k-tickets"])["views"]["k-tickets"]
    assert answer["value"] == int(wanted.sum())
    # "Of total" is every ticket collected so far, not every ticket.
    assert answer["total"] == int((frame[COLLECTED] <= step).sum())


def test_ticket_kpis_grow_step_by_step() -> None:
    ds = dataset(TAD)
    counts = [
        run(ds, FilterContext(step=s), ["k-tickets"])["views"]["k-tickets"]["value"]
        for s in range(STEPS + 1)
    ]
    assert counts == sorted(counts) and len(set(counts)) == STEPS + 1
    assert counts[-1] == len(ds.primary)


@pytest.mark.parametrize("solution", [TAD, LO, APR])
def test_caught_up_is_the_full_dataset(solution) -> None:
    """FR-AN10: once collection ends, the true counts are the dataset's."""
    ds = dataset(solution)
    assert figures(run(ds, FilterContext(step=STEPS))) == figures(run(ds, FilterContext()))
    assert ds.at(CALIBRATIONS - 1) is ds.frames


@pytest.mark.parametrize("solution", [TAD, LO, APR])
def test_the_generated_frames_are_untouched_by_calibration(solution) -> None:
    ds = dataset(solution)
    before = {f: frame.copy() for f, frame in ds.frames.items()}
    for c in range(CALIBRATIONS):
        ds.at(c)
    for frame_id, frame in ds.frames.items():
        assert frame.equals(before[frame_id]), frame_id


# -- Recalibration (FR-LF6, FR-AN3) -------------------------------------


def test_ticket_baselines_are_recomputed_over_what_was_collected() -> None:
    """Each calibration's baseline is the comparable normal tickets' mean, so far."""
    ds = dataset(TAD)
    for c in range(CALIBRATIONS - 1):
        frame = ds.at(c)["primary"]
        normal = frame[(frame[COLLECTED] <= c * EVERY) & ~frame["anomalous"]]
        group = "Network Operations"
        rows = frame[frame["assignmentGroup"] == group]
        expected = normal[normal["assignmentGroup"] == group]["reassignments"].mean()
        assert rows["reassignmentsBaseline"].iloc[0] == pytest.approx(round(expected, 3))


def test_a_recalibration_moves_a_baseline_and_confirms_clusters() -> None:
    first = dataset(TAD).recalibrations[0]
    assert first["baseline"]["from"] != first["baseline"]["to"]
    # Cluster 27, the Network Operations reassignment loop of §35, arrives
    # during the window and is confirmed at the first recalibration.
    assert "Cluster 27" in first["confirmed"]
    confirmed = [v for r in dataset(TAD).recalibrations for v in r["confirmed"]]
    assert len(confirmed) == len(set(confirmed))


def test_a_provisional_cluster_scores_below_confirmation() -> None:
    ds = dataset(TAD)
    early = FilterContext(step=2, dimensions={"cluster": ["Cluster 27"]})
    late = FilterContext(step=EVERY, dimensions={"cluster": ["Cluster 27"]})
    assert evidence(ds, early)["confirmation"]["status"] == "provisional"
    assert evidence(ds, late)["confirmation"]["status"] == "confirmed"


def test_application_figures_follow_the_latest_month_collected() -> None:
    ds = dataset(APR)
    before = run(ds, FilterContext(step=0), ["k-users"])["views"]["k-users"]["value"]
    after = run(ds, FilterContext(step=STEPS), ["k-users"])["views"]["k-users"]["value"]
    assert before != after
    assert after == run(ds, FilterContext(), ["k-users"])["views"]["k-users"]["value"]


def test_the_evidence_names_its_calibration() -> None:
    """FR-LF9."""
    ds = dataset(TAD)
    pattern = {"pattern": ["Reassignment loop"]}
    assert evidence(ds, FilterContext(dimensions=pattern))["calibration"] is None
    named = evidence(ds, FilterContext(step=9, dimensions=pattern))["calibration"]
    assert named["index"] == 2 and "recalibration 2" in named["label"]
    assert evidence(ds, FilterContext(step=1, dimensions=pattern))["calibration"]["index"] == 0


def test_a_pinned_step_reads_the_same_whatever_collection_has_done() -> None:
    """FR-LF8: a finding does not change while a viewer is inside it."""
    ds = dataset(TAD)
    pinned = FilterContext(step=5, dimensions={"cluster": ["Cluster 27"]})
    first = evidence(ds, pinned)
    for c in range(CALIBRATIONS):
        ds.at(c)
    assert evidence(ds, pinned) == first
    assert calibration_of(5) == 1


# -- The Life workflow (FR-LF4, FR-LF6, FR-LF10, FR-LF11) ----------------


def engine(speed: Speed = Speed.INSTANT, total: float = 0.2) -> SimulationEngine:
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    runner = SimulationEngine(
        state, (*NARRATIVE, *LIFE), total_duration=total, narrative_weight=105.0
    )
    runner.set_speed(speed)
    return runner


def life_events(state: SystemState) -> list[Any]:
    return [e for e in state.events.all() if e.type.startswith("life.")]


@pytest_asyncio.fixture
async def lived() -> SystemState:
    runner = engine()
    await run_to_end(runner)
    assert runner.status is RunStatus.COMPLETE
    return runner.state


@pytest.mark.asyncio
async def test_life_collects_every_week_then_catches_up(lived: SystemState) -> None:
    types = [e.type for e in life_events(lived)]
    assert types[0] == "life.collection.started"
    assert types.count("life.collection.step") == STEPS
    assert types.count("life.recalibrated") == CALIBRATIONS - 1
    assert types[-1] == "life.caught_up" and lived.events.all()[-1].type == "life.caught_up"
    assert lived.collection["step"] == STEPS and lived.collection["caughtUp"] is True
    # Life begins only once seeding has closed.
    ready = next(i for i, e in enumerate(lived.events.all()) if e.type == "deployment.ready")
    started = next(i for i, e in enumerate(lived.events.all()) if e.type.startswith("life."))
    assert started > ready


@pytest.mark.asyncio
async def test_each_step_reports_what_the_rows_say_arrived(lived: SystemState) -> None:
    steps = [e for e in life_events(lived) if e.type == "life.collection.step"]
    for step, event in enumerate(steps, start=1):
        assert event.payload["collection"]["step"] == step
        for arrived in event.payload["arrived"]:
            ds = dataset(arrived["solutionId"])
            frame = ds.frames[ds.dashboard.collection.frame]
            assert arrived["count"] == int((frame[COLLECTED] == step).sum())
        assert "Simulated collection" in event.message


@pytest.mark.asyncio
async def test_the_first_recalibration_reports_a_move_and_a_confirmation(
    lived: SystemState,
) -> None:
    first = next(e for e in life_events(lived) if e.type == "life.recalibrated")
    assert first.payload["collection"]["step"] == EVERY
    tickets = next(m for m in first.payload["moves"] if m["solutionId"] == TAD)
    assert tickets["baseline"]["from"] != tickets["baseline"]["to"]
    assert "Cluster 27" in tickets["confirmed"]
    assert "moved from" in first.message and "Cluster 27" in first.message


@pytest.mark.asyncio
async def test_two_runs_from_reset_collect_and_recalibrate_alike() -> None:
    """FR-LF11, NFR-D4 modulo timestamps (A-2)."""
    runs = []
    for _ in range(2):
        runner = engine()
        await run_to_end(runner)
        runs.append([(e.type, e.message, e.payload) for e in life_events(runner.state)])
    assert runs[0] == runs[1]


@pytest.mark.asyncio
async def test_a_rejected_component_is_not_collected() -> None:
    runner = engine()
    await run_to_end(runner, decisions={LO: "reject"})
    assert runner.state.collection["sources"] == [TAD, APR]


@pytest.mark.asyncio
async def test_life_draws_nothing_from_the_narrative_budget() -> None:
    from app.config import NARRATIVE_WEIGHT

    runner = engine()
    await run_to_end(runner)
    assert runner.consumed_weight == pytest.approx(NARRATIVE_WEIGHT)


@pytest.mark.asyncio
async def test_skip_completes_collection() -> None:
    """FR-LF10: a skip taken in Life carries collection to the end at once."""
    runner = engine(Speed.INSTANT)
    await runner.start()
    # Answer everything up to the confirmation that closes seeding.
    while True:
        await settle(runner, limit=30.0)
        pending = runner.state.blocked_on
        if pending.kind.value == "confirmation":
            break
        if pending.kind.value == "approval":
            target = next(s for s in runner.state.solutions if s["status"] == "AWAITING_APPROVAL")
            await runner.resolve_human(
                pending.request_id, {"solution": target["id"], "decision": "approve"}
            )
        else:
            await runner.resolve_human(pending.request_id, {"username": "svc"})
    # At 1x, closing's weighted beats are near instant at this total, and
    # Life's floored beats are not: collection would take the better part
    # of a minute.
    runner.set_speed(Speed.NORMAL)
    await runner.resolve_human(pending.request_id, {"acknowledged": True})
    for _ in range(200):
        if runner.state.collection.get("step", 0) >= 1:
            break
        await asyncio.sleep(0.05)
    assert 1 <= runner.state.collection["step"] < STEPS
    assert not runner.state.collection["caughtUp"]
    runner.skip_phase()
    started = time.monotonic()
    await settle(runner, limit=5.0)
    assert runner.status is RunStatus.COMPLETE
    assert runner.state.collection["caughtUp"] is True
    assert time.monotonic() - started < 2.0


@pytest.mark.asyncio
async def test_reset_clears_collection(lived: SystemState) -> None:
    assert lived.collection
    lived.reset()
    assert lived.collection == {} and lived.snapshot().collection == {}


@pytest.mark.asyncio
async def test_life_events_are_presented_as_activity_and_subscribed(lived: SystemState) -> None:
    subscribed = EVENTS_STORE.read_text(encoding="utf-8")
    for event in life_events(lived):
        assert f"'{event.type}'" in subscribed, event.type
        presented = presentation_of(
            type=event.type, category=event.category, severity=event.severity
        )
        assert presented is Presentation.ACTIVITY


# -- Over HTTP (D-3) ----------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    process_state.reset()
    with TestClient(app) as connection:
        yield connection
        connection.post("/api/operator/reset")
    process_state.reset()


def test_a_step_is_asked_for_over_http_and_the_clock_is_described(client: TestClient) -> None:
    described = client.get(f"/api/analytics/{TAD}/dashboard").json()
    assert described["collection"]["steps"] == STEPS
    assert described["collection"]["weeks"][1]["week"] == "week 24"
    at = client.post(
        f"/api/analytics/{TAD}/query", json={"filter": {"step": 4}, "views": ["k-tickets"]}
    ).json()
    frame = dataset(TAD).primary
    assert at["views"]["k-tickets"]["value"] == int((frame[COLLECTED] <= 4).sum())
    assert (
        client.post(f"/api/analytics/{TAD}/query", json={"filter": {"step": STEPS + 1}}).status_code
        == 422
    )


def test_the_running_app_collects_after_closing(client: TestClient) -> None:
    client.post("/api/seed/initialize", json={"layers": read_bundled()})
    client.post("/api/operator/speed", json={"speed": "instant"})
    client.post("/api/operator/start")
    for _ in range(3000):
        snapshot = client.get("/api/state").json()
        if snapshot["collection"].get("caughtUp"):
            break
        blocked = snapshot["blockedOn"]
        if blocked and blocked["kind"] == "approval":
            waiting = next(s for s in snapshot["solutions"] if s["status"] == "AWAITING_APPROVAL")
            client.post(f"/api/solutions/{waiting['id']}/decision", json={"decision": "approve"})
        elif blocked:
            client.post(f"/api/human/{blocked['requestId']}", json={"acknowledged": True})
        time.sleep(0.005)
    assert snapshot["collection"]["caughtUp"] is True
    assert snapshot["collection"]["step"] == STEPS
    assert np.array_equal(snapshot["collection"]["sources"], [TAD, LO, APR])
