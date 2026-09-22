"""The three states of §61, and the convention that keeps them apart.

FR-H4 is a requirement about the interface, but the thing that can
actually break it is a name. An event called `assessment.insufficient`
renders as a withheld conclusion; the same event called
`assessment.failure` renders as a malfunction. Nothing in the frontend
can recover the difference once the name is wrong.

So the convention is asserted here, against every event type the
narrative emits, rather than trusted to hold.
"""

import asyncio

import pytest

from app.domain.events import Category, Severity
from app.domain.lifecycle import LifecycleState
from app.domain.presentation import (
    ERROR_SUFFIXES,
    INSUFFICIENT_SUFFIXES,
    Presentation,
    presentation_of,
)
from app.domain.state import BlockedOn, RequestKind, RequestOption, SystemState
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE


def classify(type: str, category: Category, severity: Severity = Severity.INFO) -> Presentation:
    return presentation_of(type=type, category=category, severity=severity)


# -- The three states must not collapse -------------------------------


def test_the_three_states_of_section_61_are_three_states() -> None:
    """A fault, a decision and a withheld conclusion, all distinct (FR-H4)."""
    fault = classify("discovery.endpoint.timeout", Category.WARNING, Severity.WARNING)
    decision = classify("human.requested", Category.HUMAN_INPUT)
    withheld = classify("assessment.evidence.insufficient", Category.ANALYSIS)

    assert len({fault, decision, withheld}) == 3
    assert fault is Presentation.ERROR
    assert decision is Presentation.DECISION
    assert withheld is Presentation.INSUFFICIENT


def test_an_insufficiency_is_not_an_error_however_severe_it_sounds() -> None:
    """The case the other two swallow. Nothing is broken and nothing is asked."""
    assert (
        classify("assessment.cost.insufficient", Category.ANALYSIS, Severity.WARNING)
        is Presentation.INSUFFICIENT
    )


def test_a_policy_denial_is_not_an_error() -> None:
    """FR-P4: a denial is the boundary working, not a fault."""
    assert classify("policy.decision", Category.POLICY) is Presentation.ACTIVITY


def test_an_error_severity_is_an_error_whatever_it_is_called() -> None:
    assert classify("run.stopped", Category.DECISION, Severity.ERROR) is Presentation.ERROR


def test_ordinary_progress_is_ordinary() -> None:
    assert classify("discovery.system.found", Category.DISCOVERY) is Presentation.ACTIVITY
    assert classify("lifecycle.transition", Category.DECISION) is Presentation.ACTIVITY


def test_the_two_suffix_sets_do_not_overlap() -> None:
    """A type cannot be both, so the classification stays total and unambiguous."""
    assert not set(ERROR_SUFFIXES) & set(INSUFFICIENT_SUFFIXES)


# -- Against what the narrative actually emits ------------------------


@pytest.mark.asyncio
async def test_every_event_the_narrative_emits_classifies_as_intended() -> None:
    """The names in the workflows land in the buckets they should.

    Written as an explicit expectation per type rather than a smoke test,
    because a silently reclassified event is exactly the drift this
    guards.
    """
    expected = {
        "system.ready": Presentation.ACTIVITY,
        "lifecycle.transition": Presentation.ACTIVITY,
        "discovery.system.found": Presentation.ACTIVITY,
        "discovery.credentials.accepted": Presentation.ACTIVITY,
        "discovery.endpoint.timeout": Presentation.ERROR,
        "discovery.endpoint.recovered": Presentation.ACTIVITY,
        "assessment.methodology.evaluated": Presentation.ACTIVITY,
        "assessment.completed": Presentation.ACTIVITY,
        "human.requested": Presentation.DECISION,
        "human.resolved": Presentation.DECISION,
    }

    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    runner = SimulationEngine(
        state, NARRATIVE, total_duration=0.2, narrative_weight=100.0
    )
    runner.set_speed(Speed.INSTANT)

    await runner.start()
    while runner.status is RunStatus.RUNNING:
        await asyncio.sleep(0.01)
    await runner.resolve_human("sccm-inventory", {"username": "svc"})
    while runner.status is RunStatus.RUNNING:
        await asyncio.sleep(0.01)
    assert runner.status is RunStatus.COMPLETE

    emitted = {event.type for event in state.events.all()}
    assert emitted == set(expected), emitted.symmetric_difference(expected)

    for event in state.events.all():
        assert (
            presentation_of(
                type=event.type, category=event.category, severity=event.severity
            )
            is expected[event.type]
        ), event.type


# -- The request model ------------------------------------------------


def test_a_request_states_what_access_and_why() -> None:
    """FR-H2. All three, separately, so the surface can label each one."""
    state = SystemState()
    state.block(
        BlockedOn(
            kind=RequestKind.CREDENTIALS,
            request_id="r1",
            prompt="The endpoint requires authentication.",
            access="Read-only inventory API",
            reason="Deployment records are required evidence.",
        )
    )

    request = state.events.all()[0].payload["request"]
    assert request["prompt"] == "The endpoint requires authentication."
    assert request["access"] == "Read-only inventory API"
    assert request["reason"] == "Deployment records are required evidence."


def test_the_whole_request_travels_in_the_event(  ) -> None:
    """A late client rebuilds the surface from the stream alone (FR-E5)."""
    state = SystemState()
    state.block(
        BlockedOn(
            kind=RequestKind.AMBIGUITY,
            request_id="inventory-authority",
            prompt="Two sources appear to represent the application inventory.",
            reason="A portfolio conclusion depends on which is authoritative.",
            options=[
                RequestOption(value="warehouse", label="SQL Server is authoritative"),
                RequestOption(value="registry", label="Legacy Registry is authoritative"),
                RequestOption(value="both", label="Both are required", note="Reconcile first"),
            ],
        )
    )

    rebuilt = BlockedOn.model_validate(state.events.all()[0].payload["request"])
    assert rebuilt == state.blocked_on
    assert [option.label for option in rebuilt.options][0] == "SQL Server is authoritative"


def test_the_request_is_carried_under_wire_names() -> None:
    """The frontend reads camelCase, and the payload is not translated twice."""
    state = SystemState()
    state.block(
        BlockedOn(kind=RequestKind.APPROVAL, request_id="solutions", prompt="Approve?")
    )

    request = state.events.all()[0].payload["request"]
    assert "requestId" in request
    assert "request_id" not in request


def test_the_scripted_credential_request_states_all_three(  ) -> None:
    """FR-D7's request is the one the audience reads. §17's shape, exactly."""
    from app.simulation.workflows import scaffold

    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    workflow = scaffold.discovery(state)

    request = None
    for step in workflow:
        if hasattr(step, "request"):
            request = step.request
            break

    assert request is not None
    assert request.kind is RequestKind.CREDENTIALS
    assert request.access
    assert request.reason
    # The reason says what the evidence is for, not that it is needed.
    assert "Rationalisation" in request.reason


def test_every_request_kind_is_distinct() -> None:
    """FR-H3: five kinds, and the surface keys on them."""
    assert len(set(RequestKind)) == 5
    assert {kind.value for kind in RequestKind} == {
        "credentials",
        "ambiguity",
        "missing-info",
        "approval",
        "confirmation",
    }
