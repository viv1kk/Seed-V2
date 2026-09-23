"""The routing-problem flag (D-12, FR-A12, FR-A13).

In M7's style: the flag is computed, so change the fact and the flag
moves. The facts are a node's status and the policy decision recorded on
it. Each test changes one of them on a copy of the environment a real
discovery produced, and reads the flag back through `assess`, the one
function the workflow, the regrade and the API all use.
"""

import copy
from typing import Any

import pytest
import pytest_asyncio

from app.domain.lifecycle import LifecycleState
from app.domain.state import RequestKind, SystemState
from app.environment.model import NodeStatus
from app.knowledge.feasibility import assess
from app.knowledge.methodologies import BY_ID, METHODOLOGIES
from app.knowledge.solutions import revise_evidence
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import Speed
from app.simulation.workflows.registry import NARRATIVE
from narrative import settle

TAD, LO, APR = (m.id for m in METHODOLOGIES)


async def discovered() -> SystemState:
    """A run parked on approval: discovery complete and everything assessed."""
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    runner = SimulationEngine(state, NARRATIVE, total_duration=0.2, narrative_weight=100.0)
    runner.set_speed(Speed.INSTANT)
    await runner.start()
    await settle(runner)
    await runner.resolve_human("servicenow-incident-api", {"username": "svc"})
    await settle(runner)
    assert state.blocked_on is not None and state.blocked_on.kind is RequestKind.APPROVAL
    return state


@pytest_asyncio.fixture
async def environment() -> dict[str, Any]:
    return copy.deepcopy((await discovered()).environment)


def node(environment: dict[str, Any], node_id: str) -> dict[str, Any]:
    return next(n for n in environment["nodes"] if n["id"] == node_id)


def routing(environment: dict[str, Any], methodology: str) -> list[dict[str, Any]]:
    return assess(BY_ID[methodology], environment)["routing"]


# -- The scripted run --------------------------------------------------


@pytest.mark.asyncio
async def test_the_scripted_run_raises_no_routing_problem() -> None:
    """Recorded for D-12: no methodology carries the flag in the narrative.

    PR-033 refuses ServiceNow's security log, the candidate D-12 named. The
    log is outside the concept mapping, so it carries nothing any
    methodology requires, and its refusal is not a routing problem.
    """
    state = await discovered()
    assert all(a["routing"] == [] for a in state.assessments)

    log = node(state.environment, "servicenow.sys_security_log")
    assert log["excludedBy"] == "PR-033"


# -- Change the fact, the flag moves -----------------------------------


@pytest.mark.asyncio
async def test_a_carrier_in_error_raises_the_flag(environment: dict[str, Any]) -> None:
    node(environment, "servicenow.metric_instance")["status"] = NodeStatus.ERROR

    found = routing(environment, TAD)
    assert [(r["concept"], r["reason"], r["dataset"]) for r in found] == [
        ("reassignment-history", "unreachable", "servicenow.metric_instance")
    ]
    assert routing(environment, LO) == []
    assert routing(environment, APR) == []


@pytest.mark.asyncio
async def test_a_surface_awaiting_input_blocks_every_dataset_behind_it(
    environment: dict[str, Any],
) -> None:
    node(environment, "servicenow.incident-api")["status"] = NodeStatus.REQUIRES_INPUT

    tad = routing(environment, TAD)
    assert {r["concept"] for r in tad} == {
        "ticket",
        "category-taxonomy",
        "reassignment-history",
        "group-membership",
    }
    assert {r["reason"] for r in tad} == {"awaiting-input"}
    assert {r["at"] for r in tad} == {"Incident API"}
    # License Optimization reads leaver records through the same API.
    assert {r["concept"] for r in routing(environment, LO)} == {"leaver-record"}


@pytest.mark.asyncio
async def test_a_policy_refusal_raises_the_flag_citing_the_rule(
    environment: dict[str, Any],
) -> None:
    node(environment, "servicenow.cmdb_ci_appl")["excludedBy"] = "PR-032"

    found = routing(environment, APR)
    assert {r["concept"] for r in found} == {"ownership", "criticality"}
    assert {(r["reason"], r["rule"]) for r in found} == {("refused", "PR-032")}


@pytest.mark.asyncio
async def test_restoring_the_fact_clears_the_flag(environment: dict[str, Any]) -> None:
    target = node(environment, "servicenow.metric_instance")
    target["status"] = NodeStatus.ERROR
    assert routing(environment, TAD)

    target["status"] = NodeStatus.VALIDATED
    assert routing(environment, TAD) == []


@pytest.mark.asyncio
async def test_evidence_not_yet_found_is_not_a_routing_problem(
    environment: dict[str, Any],
) -> None:
    """A dataset nobody has found is not known to exist (G-2)."""
    node(environment, "servicenow.incident-api")["status"] = NodeStatus.ERROR
    environment["nodes"] = [
        n for n in environment["nodes"] if n["id"] != "servicenow.metric_instance"
    ]

    concepts = {r["concept"] for r in routing(environment, TAD)}
    assert "reassignment-history" not in concepts
    assert "ticket" in concepts


@pytest.mark.asyncio
async def test_the_flag_never_moves_the_grade(environment: dict[str, Any]) -> None:
    """Independent of the grade: HIGH potential with a blocked path (D-12)."""
    before = assess(BY_ID[TAD], environment)
    node(environment, "servicenow.metric_instance")["status"] = NodeStatus.ERROR
    after = assess(BY_ID[TAD], environment)

    assert after["routing"] and not before["routing"]
    assert after["feasibility"] == before["feasibility"] == "HIGH"
    assert after["dataSufficiency"] == before["dataSufficiency"]


@pytest.mark.asyncio
async def test_a_regrade_carries_the_flag_into_system_state() -> None:
    """The real path: System State changes, the next regrade reports it."""
    state = await discovered()
    node(state.environment, "servicenow.metric_instance")["status"] = NodeStatus.ERROR

    revise_evidence(state, "servicenow.incident", "resolved_at", 0.998)

    tad = next(a for a in state.assessments if a["id"] == TAD)
    assert [r["concept"] for r in tad["routing"]] == ["reassignment-history"]
