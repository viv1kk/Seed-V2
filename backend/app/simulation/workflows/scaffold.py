"""Scaffold workflows, in place until the real ones arrive.

These exist to exercise the engine: two stages, a park for human input,
a protected recovery, and a run that ends in a state the operator
controls can be tested against. M6 replaces `discovery` with the ACME
environment walk, and M7 replaces `assessment` with computed
feasibility. The shape of both --- work, then a beat --- is what those
milestones keep.

Weights sum to the declared narrative weight in `config`, so a 1x run
lasts the configured total (D-8). The calibration test holds that sum,
which is what makes drift a test failure rather than a rehearsal
surprise.
"""

from app.domain.events import Category, Severity
from app.domain.lifecycle import LifecycleState
from app.domain.state import BlockedOn, RequestKind, SystemState
from app.simulation.beats import AwaitHuman, Beat, Workflow


def discovery(state: SystemState) -> Workflow:
    """INITIALIZED to DISCOVERY_COMPLETE, pausing once for credentials.

    The run begins from INITIALIZED rather than reaching it. Planting the
    seed is what produces that state, and it happens over HTTP before the
    engine is started (FR-S2), so `seed.loaded` and the transition into
    INITIALIZED belong to the seed API and not to this workflow.
    """
    state.record(
        type="system.ready",
        category=Category.SUCCESS,
        message="Three layers registered. The system is ready to discover an environment.",
    )
    yield Beat(weight=4, label="system ready")

    state.transition(LifecycleState.DISCOVERING)
    yield Beat(weight=2, label="discovery begins")

    for system in ("ServiceNow", "Active Directory", "SCCM"):
        state.record(
            type="discovery.system.found",
            category=Category.DISCOVERY,
            message=f"{system} responded. Enumerating available data sources.",
            payload={"system": system},
        )
        yield Beat(weight=6, label=f"found {system}")

    # Discovery has not ended here; it is waiting (FR-L4, FR-D7).
    #
    # Three fields, because a request a person can answer has to say what
    # is wanted, what it will be able to reach, and what for (FR-H2). The
    # third is the one that makes this an escalation rather than a prompt.
    state.transition(LifecycleState.DISCOVERY_BLOCKED)
    submission = yield AwaitHuman(
        request=BlockedOn(
            kind=RequestKind.CREDENTIALS,
            request_id="sccm-inventory",
            prompt="The SCCM inventory endpoint requires authentication.",
            access="Read-only inventory API",
            reason=(
                "Deployment and usage records from SCCM are required evidence for "
                "Application Portfolio Rationalisation. Without them no application "
                "can be classified as unused rather than uninstrumented."
            ),
        )
    )

    # The shape of the submission is recorded, never its values (FR-H5).
    state.record(
        type="discovery.credentials.accepted",
        category=Category.VALIDATION,
        message="Credentials accepted. Values were used for the handshake and discarded.",
        payload={"fields": sorted((submission or {}).keys())},
    )
    yield Beat(weight=3, floor=2.0, label="credentials accepted")

    state.transition(LifecycleState.DISCOVERING)
    yield Beat(weight=2, label="discovery resumes")

    # The one scripted failure (FR-D8). Floored, because a recovery the
    # audience does not see is a recovery that did not happen.
    state.record(
        type="discovery.endpoint.timeout",
        category=Category.WARNING,
        severity=Severity.WARNING,
        message="Inventory endpoint timed out after 30s. Retrying once.",
    )
    yield Beat(weight=5, floor=3.0, label="timeout")

    state.record(
        type="discovery.endpoint.recovered",
        category=Category.SUCCESS,
        message="Inventory endpoint responded on retry. Discovery continues.",
    )
    yield Beat(weight=4, floor=2.0, label="recovery")

    for system in ("Jira", "Entra ID"):
        state.record(
            type="discovery.system.found",
            category=Category.DISCOVERY,
            message=f"{system} responded. Enumerating available data sources.",
            payload={"system": system},
        )
        yield Beat(weight=6, label=f"found {system}")

    state.transition(LifecycleState.DISCOVERY_COMPLETE)
    yield Beat(weight=4, label="discovery complete")


def assessment(state: SystemState) -> Workflow:
    """DISCOVERY_COMPLETE to AWAITING_APPROVAL."""
    state.transition(LifecycleState.ASSESSING)
    yield Beat(weight=4, label="assessment begins")

    for methodology in (
        "Ticket Anomaly Detection",
        "License Optimization",
        "Application Portfolio Rationalization",
    ):
        state.record(
            type="assessment.methodology.evaluated",
            category=Category.ANALYSIS,
            message=f"{methodology} evaluated against the discovered evidence.",
            payload={"methodology": methodology},
        )
        yield Beat(weight=8, label=f"assessed {methodology}")

    state.record(
        type="assessment.completed",
        category=Category.ANALYSIS,
        message="Three methodologies assessed. Feasibility computed for each.",
    )
    yield Beat(weight=6, label="assessment complete")

    state.transition(LifecycleState.AWAITING_APPROVAL)
    yield Beat(weight=12, label="awaiting approval")
