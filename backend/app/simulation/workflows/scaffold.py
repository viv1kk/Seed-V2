"""Scaffold workflows, in place until the real ones arrive.

These exist to exercise the engine: two stages, a park for human input,
a protected recovery, and a run that ends in a state the operator
controls can be tested against. M6 replaces `discovery` with the ACME
environment walk, and M7 replaces `assessment` with computed
feasibility. The shape of both --- work, then a beat --- is what those
milestones keep.

Since M5 every action that needs a capability passes through the policy
engine before it proceeds (FR-P2), and discovery walks the five ACME
systems in §68's order. The narrative carries the two decisions FR-P6
requires, chosen to answer OQ-6:

- **DENY.** Discovery considers ServiceNow's security log as a usage
  signal and asks to read it, projecting only non-personal columns.
  PR-033 refuses it regardless. A boundary that holds even against a
  well-motivated, minimised request is the demonstration §10 asks for.
- **ESCALATE.** Assessment asks to deploy the assessed solutions, and
  PR-053 escalates it. That escalation is what places the system in
  AWAITING_APPROVAL, so it adds no interruption to §83.6's narrative:
  it is the reason the approval exists.

Weights sum to the declared narrative weight in `config`, so a 1x run
lasts the configured total (D-8). The calibration test holds that sum,
which is what makes drift a test failure rather than a rehearsal
surprise.
"""

from app.domain.events import Category, Severity
from app.domain.lifecycle import LifecycleState
from app.domain.state import BlockedOn, RequestKind, SystemState
from app.protection.engine import authorize
from app.protection.rules import Action, ActionRequest, Identity
from app.simulation.beats import AwaitHuman, Beat, Workflow

CREDENTIAL_REQUEST = "servicenow-incident-api"


def _found(state: SystemState, system: str, detail: str) -> None:
    state.record(
        type="discovery.system.found",
        category=Category.DISCOVERY,
        message=f"{system} detected. {detail}",
        payload={"system": system},
    )


def _authenticate(state: SystemState, system: str) -> None:
    authorize(
        state,
        ActionRequest(
            action=Action.AUTHENTICATE,
            resource=f"{system} read-only service identity",
            source=system,
            identity=Identity.SERVICE_READ_ONLY,
            source_declared=True,
            after_rejection=False,
            attempt=1,
            in_scope=True,
        ),
    )


def _enumerate(state: SystemState, system: str, surface: str) -> None:
    authorize(
        state,
        ActionRequest(
            action=Action.ENUMERATE,
            resource=f"{system} {surface}",
            source=system,
            source_declared=True,
            in_scope=True,
        ),
    )


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

    # §68 steps 4 to 7: detected, reachable, credentials requested.
    _found(state, "ServiceNow", "Incident API reachable; authentication required.")
    authorize(
        state,
        ActionRequest(
            action=Action.REQUEST_CREDENTIAL,
            resource="ServiceNow read-only service identity",
            source="ServiceNow",
            write_scope=False,
        ),
    )
    yield Beat(weight=6, label="ServiceNow detected")

    # Discovery has not ended here; it is waiting (FR-L4, FR-D7).
    #
    # Three fields, because a request a person can answer has to say what
    # is wanted, what it will be able to reach, and what for (FR-H2). This
    # is §17's example, word for word.
    state.transition(LifecycleState.DISCOVERY_BLOCKED)
    submission = yield AwaitHuman(
        request=BlockedOn(
            kind=RequestKind.CREDENTIALS,
            request_id=CREDENTIAL_REQUEST,
            prompt="ServiceNow requires authentication.",
            access="Read-only Incident API",
            reason="Historical incident data is required for Ticket Anomaly Detection.",
        )
    )

    # The shape of the submission is recorded, never its values (FR-H5).
    state.record(
        type="discovery.credentials.accepted",
        category=Category.VALIDATION,
        message="Credentials accepted. Values were used for the handshake and discarded.",
        payload={"fields": sorted((submission or {}).keys())},
    )
    _authenticate(state, "ServiceNow")
    yield Beat(weight=3, floor=2.0, label="credentials accepted")

    state.transition(LifecycleState.DISCOVERING)
    yield Beat(weight=2, label="discovery resumes")

    _enumerate(state, "ServiceNow", "table metadata")
    yield Beat(weight=3, label="ServiceNow enumerated")

    # The DENY of FR-P6 (OQ-6). A plausible analytical motive and a
    # minimised projection, refused anyway: the table is the boundary,
    # not the columns.
    authorize(
        state,
        ActionRequest(
            action=Action.READ,
            resource="ServiceNow sys_security_log",
            source="ServiceNow",
            purpose=(
                "Considered as a usage signal: sign-in counts per application, "
                "application identifier and timestamp only."
            ),
            source_declared=True,
            dataset_mapped=False,
            unmapped_personal_fields=False,
            security_table=True,
            within_window=True,
            parameterised=True,
            in_scope=True,
        ),
    )
    yield Beat(weight=3, label="security log refused")

    for system, detail, surface in (
        ("SAP", "OData service catalogue available.", "service catalogue"),
        ("SQL Server", "Reporting schema available.", "information schema"),
    ):
        _found(state, system, detail)
        _authenticate(state, system)
        _enumerate(state, system, surface)
        yield Beat(weight=4, label=f"found {system}")

    # The one scripted failure (FR-D8). Floored, because a recovery the
    # audience does not see is a recovery that did not happen.
    state.record(
        type="discovery.endpoint.timeout",
        category=Category.WARNING,
        severity=Severity.WARNING,
        message="License Management System catalogue endpoint timed out after 30s. Retrying once.",
    )
    yield Beat(weight=5, floor=3.0, label="timeout")

    state.record(
        type="discovery.endpoint.recovered",
        category=Category.SUCCESS,
        message="License Management System responded on retry. Discovery continues.",
    )
    yield Beat(weight=4, floor=2.0, label="recovery")

    _found(state, "License Management System", "Product catalogue available.")
    _authenticate(state, "License Management System")
    _enumerate(state, "License Management System", "product catalogue")
    yield Beat(weight=6, label="found License Management System")

    # No endpoint: administrator-supplied (FR-D6). Reading the export is
    # still an action, so it is still gated.
    state.record(
        type="discovery.system.registered",
        category=Category.DISCOVERY,
        message="Legacy Application Registry registered from an administrator-supplied export.",
        payload={"system": "Legacy Application Registry"},
    )
    authorize(
        state,
        ActionRequest(
            action=Action.READ,
            resource="Legacy Application Registry export",
            source="Legacy Application Registry",
            source_declared=True,
            dataset_mapped=True,
            unmapped_personal_fields=False,
            security_table=False,
            within_window=True,
            parameterised=True,
            in_scope=True,
        ),
    )
    yield Beat(weight=4, label="legacy registry")

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

    # The ESCALATE of FR-P6 (OQ-6). Deployment is consequential, so the
    # system asks rather than proceeds, and the escalation is what the
    # approval answers. The lifecycle follows the decision.
    authorize(
        state,
        ActionRequest(
            action=Action.DEPLOY,
            resource="Analytical services for the assessed methodologies",
            purpose="Implement and deploy the solutions the assessment found feasible.",
        ),
    )
    state.transition(LifecycleState.AWAITING_APPROVAL)
    yield Beat(weight=12, label="awaiting approval")
