"""Discovery over the ACME environment (FR-D1 to FR-D10).

Most of these drive the discovery workflow directly, a step at a time,
rather than through the engine. That exposes the graph between events,
which is what "nodes appear progressively" and "status transitions" are
claims about; the engine adds timing and nothing else.

The fold test at the end is the one that protects the screen. The
frontend builds its graph from the snapshot plus the environment deltas
carried on events, and that test replays the same deltas the same way and
requires the result to equal System State exactly (R-5).
"""

import copy
import math
from typing import Any

import pytest

from app.domain.events import Event
from app.domain.lifecycle import LifecycleState
from app.domain.state import SystemState
from app.environment.acme import ACME, CLIENT, SYSTEM_ORDER
from app.environment.model import EdgeKind, NodeKind, NodeStatus, Origin, summarise
from app.knowledge.methodologies import METHODOLOGIES
from app.simulation.beats import AwaitHuman, Beat
from app.simulation.workflows import discovery as workflow

SUBMISSION = {"username": "svc-discovery", "password": "correct horse battery staple"}


Timeline = list[tuple[Event, list[dict[str, Any]]]]


def run_discovery() -> tuple[SystemState, list[Beat], Timeline, dict[int, dict[str, Any]]]:
    """Drive discovery to the end, answering the one request it makes.

    Returns the final state, every beat, for each event the node list as
    it stood when that event was recorded, and the whole environment at
    each sequence number --- the snapshot a client joining then would get.
    """
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    timeline: Timeline = []
    snapshots: dict[int, dict[str, Any]] = {}

    def capture(event: Event) -> None:
        environment = copy.deepcopy(state.environment)
        snapshots[event.sequence] = environment
        timeline.append((event, environment.get("nodes", [])))

    state.subscribe(capture)

    beats: list[Beat] = []
    steps = workflow.discovery(state)
    sent: dict[str, Any] | None = None
    while True:
        try:
            step = steps.send(sent)
        except StopIteration:
            break
        sent = None
        if isinstance(step, AwaitHuman):
            state.block(step.request)
            state.unblock(fields=list(SUBMISSION))
            sent = dict(SUBMISSION)
        else:
            beats.append(step)
    return state, beats, timeline, snapshots


@pytest.fixture(scope="module")
def run() -> tuple[SystemState, list[Beat], Timeline, dict[int, dict[str, Any]]]:
    return run_discovery()


def events_of(run_result: Any) -> list[Event]:
    return run_result[0].events.all()


def node(state: SystemState, node_id: str) -> dict[str, Any]:
    return next(n for n in state.environment["nodes"] if n["id"] == node_id)


# -- The definition (FR-D1, FR-D2, D-4) -------------------------------


def test_the_environment_has_exactly_the_five_systems_of_section_42() -> None:
    systems = [n.label for n in ACME.nodes if n.kind is NodeKind.SYSTEM]
    assert sorted(systems) == sorted(
        [
            "ServiceNow",
            "SAP",
            "SQL Server",
            "License Management System",
            "Legacy Application Registry",
        ]
    )
    assert len(SYSTEM_ORDER) == 5


def test_every_system_expands_into_what_it_is_made_of() -> None:
    for system_id in SYSTEM_ORDER:
        descendants = [n for n in ACME.nodes if ACME.system_of(n.id) == system_id and n.id != system_id]
        assert any(n.kind is NodeKind.DATASET for n in descendants), system_id


def test_the_graph_is_roughly_thirty_nodes_and_uses_every_kind() -> None:
    assert 25 <= len(ACME.nodes) <= 35
    assert {n.kind for n in ACME.nodes} == set(NodeKind)


def test_coordinates_are_on_the_canvas_and_nothing_overlaps() -> None:
    """D-4: laid out by hand, so the layout is checked rather than trusted."""
    for spec in ACME.nodes:
        assert 0 < spec.x < ACME.width and 0 < spec.y < ACME.height, spec.id
    for a in ACME.nodes:
        for b in ACME.nodes:
            if a.id < b.id:
                assert math.dist((a.x, a.y), (b.x, b.y)) >= 24, (a.id, b.id)


def test_the_legacy_registry_has_no_discoverable_surface() -> None:
    """FR-D6: no endpoint, so nothing between the system and its export."""
    children = ACME.children("legacy")
    assert [c.kind for c in children] == [NodeKind.DATASET]


# -- Progressive construction (FR-D3, FR-D4, FR-D5) -------------------


def test_the_graph_starts_from_the_declared_inventory_only(run: Any) -> None:
    _, _, timeline, _ = run
    first = next(nodes for event, nodes in timeline if event.type == "discovery.inventory.loaded")
    assert {n["id"] for n in first} == {CLIENT, *SYSTEM_ORDER}
    systems = [n for n in first if n["kind"] == NodeKind.SYSTEM]
    assert all(n["status"] == NodeStatus.UNKNOWN for n in systems)
    assert all(n["origin"] == Origin.DECLARED for n in systems)


def test_nodes_appear_progressively_in_grouped_bursts(run: Any) -> None:
    """Never shrinking, and far fewer appearances than nodes (OQ-7)."""
    _, _, timeline, _ = run
    counts = [len(nodes) for _, nodes in timeline]
    assert counts == sorted(counts)
    assert counts[-1] == len(ACME.nodes)

    bursts = sum(1 for before, after in zip(counts, counts[1:]) if after > before)
    assert bursts <= 12 < len(ACME.nodes)


def test_every_node_status_is_one_of_fr_d4(run: Any) -> None:
    _, _, timeline, _ = run
    seen = {n["status"] for _, nodes in timeline for n in nodes}
    assert seen <= {status.value for status in NodeStatus}
    # The narrative exercises all seven.
    assert seen == {status.value for status in NodeStatus}


def test_every_edge_kind_of_fr_d5_appears(run: Any) -> None:
    state, _, _, _ = run
    assert {e["kind"] for e in state.environment["edges"]} == set(EdgeKind)


def test_edges_only_join_discovered_nodes(run: Any) -> None:
    state, _, _, _ = run
    ids = {n["id"] for n in state.environment["nodes"]}
    for edge in state.environment["edges"]:
        assert edge["source"] in ids and edge["target"] in ids


def test_servicenow_waits_on_input_before_it_is_validated(run: Any) -> None:
    _, _, timeline, _ = run
    history = []
    for _, nodes in timeline:
        status = next((n["status"] for n in nodes if n["id"] == "servicenow"), None)
        if status and (not history or history[-1] != status):
            history.append(status)
    assert history == ["unknown", "detected", "testing", "requires-input", "validated", "connected"]


# -- The two interruptions (FR-D7, FR-D8) -----------------------------


def test_discovery_pauses_exactly_once_for_credentials(run: Any) -> None:
    requested = [e for e in events_of(run) if e.type == "human.requested"]
    assert len(requested) == 1
    assert requested[0].payload["requestId"] == workflow.CREDENTIAL_REQUEST
    assert requested[0].payload["kind"] == "credentials"


def test_there_is_exactly_one_timeout_and_it_recovers(run: Any) -> None:
    _, _, timeline, _ = run
    types = [event.type for event, _ in timeline]
    assert types.count("discovery.endpoint.timeout") == 1
    assert types.count("discovery.endpoint.recovered") == 1
    assert types.index("discovery.endpoint.timeout") < types.index("discovery.endpoint.recovered")

    timeout = next(e for e, _ in timeline if e.type == "discovery.endpoint.timeout")
    endpoint = timeout.payload["endpoint"]
    statuses = [
        next(n["status"] for n in nodes if n["id"] == endpoint)
        for event, nodes in timeline
        if any(n["id"] == endpoint for n in nodes)
    ]
    assert "error" in statuses
    assert statuses[-1] == NodeStatus.CONNECTED
    # Nothing else in the environment ever errors.
    assert all(
        n["id"] == endpoint for _, nodes in timeline for n in nodes if n["status"] == "error"
    )


def test_the_meaning_bearing_beats_keep_their_floors(run: Any) -> None:
    _, beats, _, _ = run
    floors = {beat.label: beat.floor for beat in beats if beat.floor > 0}
    assert floors == {"credentials accepted": 2.0, "timeout": 3.0, "recovery": 2.0}


def test_discovery_takes_roughly_half_the_narrative(run: Any) -> None:
    from app.config import NARRATIVE_WEIGHT

    _, beats, _, _ = run
    share = sum(beat.weight for beat in beats) / NARRATIVE_WEIGHT
    assert 0.45 <= share <= 0.6


# -- Administrator-supplied (FR-D6) -----------------------------------


def test_the_legacy_registry_is_administrator_supplied_not_discovered(run: Any) -> None:
    state, _, _, _ = run
    assert node(state, "legacy")["origin"] == Origin.ADMINISTRATOR
    assert node(state, "legacy.export")["origin"] == Origin.ADMINISTRATOR

    decisions = [e.payload for e in state.events.all() if e.type == "policy.decision"]
    legacy = [d["verb"] for d in decisions if d["source"] == "Legacy Application Registry"]
    # Nothing was authenticated against or enumerated: there is nothing to
    # reach. Reading the export is still an action, so it is still gated.
    assert legacy == ["read"]


# -- Policy on the graph (FR-P2, OQ-6) --------------------------------


def test_the_refused_table_is_found_but_left_out_by_the_deciding_rule(run: Any) -> None:
    state, _, _, _ = run
    denial = next(
        e.payload for e in state.events.all()
        if e.type == "policy.decision" and e.payload["effect"] == "DENY"
    )
    log = node(state, "servicenow.sys_security_log")
    assert denial["rule"] == "PR-033"
    assert log["excludedBy"] == denial["rule"]
    assert log["status"] == NodeStatus.DETECTED
    assert "servicenow.sys_security_log" not in {s["id"] for s in state.environment["dataSources"]}


def test_every_profiled_dataset_was_read_under_an_allow(run: Any) -> None:
    state, _, _, _ = run
    reads = [
        e.payload for e in state.events.all()
        if e.type == "policy.decision" and e.payload["verb"] == "read"
    ]
    allowed = [r for r in reads if r["effect"] == "ALLOW"]
    assert allowed and all(r["rule"] == "PR-030" for r in allowed)
    assert all(not r["missing"] for r in reads)


def test_an_unexpected_refusal_stops_discovery() -> None:
    from app.protection.engine import Decision
    from app.protection.rules import Action, Effect

    refused = Decision(
        effect=Effect.DENY, rule="PR-000", action=Action.READ, resource="x", reason="test"
    )
    with pytest.raises(workflow.PolicyRefused):
        workflow._proceed(refused)


# -- Computed counts (FR-D9, FR-D10) ----------------------------------


def test_the_completion_counts_are_those_of_the_constructed_graph(run: Any) -> None:
    state, _, _, _ = run
    nodes = state.environment["nodes"]
    edges = state.environment["edges"]
    summary = state.environment["summary"]

    assert summary["complete"] is True
    assert summary["systems"] == sum(1 for n in nodes if n["kind"] == "system")
    assert summary["datasets"] == sum(1 for n in nodes if n["kind"] == "dataset")
    assert summary["dataSources"] == len({e["source"] for e in edges if e["kind"] == "provides"})
    assert summary["profiled"] == len(state.environment["dataSources"])
    assert summary["excluded"] == 1


def test_the_counts_follow_the_graph_rather_than_a_script(run: Any) -> None:
    """Remove a dataset from the graph and the reported count moves with it."""
    state, _, _, _ = run
    environment = copy.deepcopy(state.environment)
    before = summarise(environment)
    environment["nodes"] = [n for n in environment["nodes"] if n["id"] != "lms.product"]
    after = summarise(environment)
    assert after["datasets"] == before["datasets"] - 1


def test_the_completion_message_reports_the_computed_counts(run: Any) -> None:
    state, _, _, _ = run
    completed = next(e for e in state.events.all() if e.type == "discovery.completed")
    summary = completed.payload["environment"]["summary"]
    for key in ("systems", "dataSources", "datasets", "profiled", "excluded"):
        assert str(summary[key]) in completed.message


def test_completion_reports_per_system_status_and_methodologies(run: Any) -> None:
    state, _, _, _ = run
    summary = state.environment["summary"]

    by_system = {s["label"]: s for s in summary["bySystem"]}
    assert [s["id"] for s in summary["bySystem"]] == list(SYSTEM_ORDER)
    assert by_system["Legacy Application Registry"]["origin"] == Origin.ADMINISTRATOR
    assert all(
        s["status"] == NodeStatus.CONNECTED
        for label, s in by_system.items()
        if label != "Legacy Application Registry"
    )

    assert [m["name"] for m in summary["methodologies"]] == [m.name for m in METHODOLOGIES]
    assert all(m["appearsFeasible"] for m in summary["methodologies"])


def test_a_methodology_whose_evidence_is_missing_does_not_appear_feasible(run: Any) -> None:
    state, _, _, _ = run
    environment = copy.deepcopy(state.environment)
    environment["dataSources"] = [
        s for s in environment["dataSources"] if s["id"] != "sap.contract_item"
    ]
    licence = next(
        m for m in summarise(environment)["methodologies"] if m["id"] == "license-optimization"
    )
    assert licence["appearsFeasible"] is False
    assert licence["missing"] == ["unit-cost"]


def test_the_discovery_completed_state_follows_the_report(run: Any) -> None:
    state, _, _, _ = run
    events = state.events.all()
    index = next(i for i, e in enumerate(events) if e.type == "discovery.completed")
    assert events[index + 1].type == "lifecycle.transition"
    assert events[index + 1].payload["to"] == LifecycleState.DISCOVERY_COMPLETE
    assert state.lifecycle is LifecycleState.DISCOVERY_COMPLETE


# -- Human input recorded, values discarded (FR-H5, FR-H6) ------------


def test_the_human_decision_is_recorded_in_state(run: Any) -> None:
    state, _, _, _ = run
    (entry,) = state.human_requests
    assert entry["requestId"] == workflow.CREDENTIAL_REQUEST
    assert entry["status"] == "resolved"
    assert entry["fields"] == sorted(SUBMISSION)
    assert entry["resolvedAt"] > entry["requestedAt"]
    assert state.snapshot().human_requests == state.human_requests


def test_no_submitted_value_appears_in_state_or_stream(run: Any) -> None:
    state, _, _, _ = run
    everything = state.snapshot().model_dump_json() + "".join(
        e.model_dump_json() for e in state.events.all()
    )
    for value in SUBMISSION.values():
        assert value not in everything


# -- The screen's fold (FR-L5, FR-E5, R-5) ----------------------------


def fold(environment: dict[str, Any], delta: dict[str, Any]) -> None:
    """The frontend's reducer, in Python: upsert nodes and sources, add edges."""
    for key in ("nodes", "dataSources"):
        for record in delta.get(key, []):
            existing = next((r for r in environment[key] if r["id"] == record["id"]), None)
            if existing is None:
                environment[key].append(dict(record))
            else:
                existing.update(record)
    for edge in delta.get("edges", []):
        if not any(e["id"] == edge["id"] for e in environment["edges"]):
            environment["edges"].append(dict(edge))
    environment["summary"] = delta.get("summary", environment["summary"])


def test_folding_the_events_reproduces_system_state(run: Any) -> None:
    state, _, _, _ = run
    rebuilt: dict[str, Any] = {"nodes": [], "edges": [], "dataSources": [], "summary": None}
    for event in state.events.all():
        if "environment" in event.payload:
            fold(rebuilt, event.payload["environment"])

    for key in ("nodes", "edges", "dataSources", "summary"):
        assert rebuilt[key] == state.environment[key], key


def test_folding_from_any_snapshot_converges(run: Any) -> None:
    """A client that joins mid-run ends where one that watched throughout does.

    It fetches the snapshot current at some sequence, then folds only the
    events after it (FR-E5). Every possible join point is tried.
    """
    state, _, _, snapshots = run
    for joined_at, snapshot in snapshots.items():
        view = copy.deepcopy(snapshot)
        if not view:
            continue
        for event in state.events.all():
            if event.sequence > joined_at and "environment" in event.payload:
                fold(view, event.payload["environment"])
        for key in ("nodes", "edges", "dataSources", "summary"):
            assert view[key] == state.environment[key], (joined_at, key)
