"""The scaffold assessment, in place until M7 replaces it.

It exists to carry the narrative from DISCOVERY_COMPLETE to
AWAITING_APPROVAL while computed feasibility is still to be built. M6
replaced the scaffold discovery with the ACME walk in `discovery.py`; M7
replaces this with methodology assessment over the environment that walk
constructs. The shape --- work, then a beat --- is what M7 keeps.

It carries the ESCALATE of FR-P6, chosen to answer OQ-6. Assessment asks
to deploy the assessed solutions, and PR-053 escalates it. That
escalation is what places the system in AWAITING_APPROVAL, so it adds no
interruption to §83.6's narrative: it is the reason the approval exists.

With discovery, the weights sum to the declared narrative weight in
`config`, so a 1x run lasts the configured total (D-8). The calibration
test holds that sum, which is what makes drift a test failure rather than
a rehearsal surprise.
"""

from app.domain.events import Category
from app.domain.lifecycle import LifecycleState
from app.domain.state import SystemState
from app.protection.engine import authorize
from app.protection.rules import Action, ActionRequest
from app.simulation.beats import Beat, Workflow


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
