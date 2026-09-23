"""Assessment and approval: DISCOVERY_COMPLETE to AWAITING_APPROVAL.

Each methodology is assessed against the evidence discovery profiled, by
computation rather than by script (FR-A2): `feasibility.py` grades it from
field completeness, and nothing in this module names a grade. §20's
License Optimization comes out PARTIAL because SAP's unit prices are 64%
complete, not because this file says so. Revise that figure and the grade
moves.

Recording the evidence behind an assessment is a capability (PR-070), so
it passes the gate like every other action, once per methodology. The
policy engine requires the evidence to be attributed, and it is: each
requirement names the dataset and field it rests on.

A requirement too weak to conclude on is reported as an insufficiency, a
third state beside errors and decisions (FR-H4, §61). It is the first one
the narrative produces.

Then the approval. Assessment asks to deploy, PR-053 escalates, and the
lifecycle moves to AWAITING_APPROVAL as the consequence (OQ-6). The run
parks on one request and stays parked until every solution has a
decision. Each Approve or Reject answers the request once, with the
solution and the verdict, and the workflow asks again while any solution
is still waiting. The decisions are made on the solution cards rather than
in a form, because that is where the evidence is (FR-A7, FR-A8), and the
resume is still the exact one FR-H7 requires.
"""

import copy

from app.domain.events import Category
from app.domain.lifecycle import LifecycleState
from app.domain.state import BlockedOn, RequestKind, SystemState
from app.knowledge.feasibility import assess, percent
from app.knowledge.methodologies import METHODOLOGIES
from app.knowledge.solutions import (
    APPROVAL_REQUEST,
    InvalidDecision,
    awaiting,
    decide,
    propose,
    record_assessment,
    shortfalls,
    submit,
)
from app.protection.engine import EFFECT_VERBS, authorize
from app.protection.rules import Action, ActionRequest, Effect
from app.simulation.beats import AwaitHuman, Beat, Workflow
from app.simulation.workflows.gate import PolicyRefused, proceed

NUMBERS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}


def _count(n: int, noun: str) -> str:
    return f"{NUMBERS.get(n, str(n))} {noun}{'' if n == 1 else 's'}"


def assessment(state: SystemState) -> Workflow:
    """DISCOVERY_COMPLETE to AWAITING_APPROVAL, and every solution decided."""
    state.transition(LifecycleState.ASSESSING)
    yield Beat(weight=2, label="assessment begins")

    for methodology in METHODOLOGIES:
        result = assess(methodology, state.environment)
        located = result["coverage"]["located"]

        proceed(
            authorize(
                state,
                ActionRequest(
                    action=Action.RECORD_EVIDENCE,
                    resource=f"{methodology.name}: {located} evidence items",
                    purpose="Attribute each requirement to the dataset and field it rests on.",
                    attributed=True,
                ),
            )
        )
        record_assessment(state, result)
        state.record(
            type="assessment.methodology.evaluated",
            category=Category.ANALYSIS,
            message=(
                f"{methodology.name}: potential {result['feasibility']}. Evidence "
                f"{located} of {result['coverage']['required']}, data sufficiency "
                f"{percent(result['dataSufficiency'])}%."
            ),
            payload={"methodology": methodology.name, "assessments": [copy.deepcopy(result)]},
        )

        # Reported as insufficiency, never as a weaker conclusion (PR-074).
        for requirement in shortfalls(result):
            weakest = requirement["weakest"]
            where = (
                f"{weakest['label']}.{weakest['field']} is "
                f"{percent(weakest['completeness'])}% complete"
                if weakest
                else "no profiled field carries it"
            )
            state.record(
                type="assessment.evidence.insufficient",
                category=Category.ANALYSIS,
                message=(
                    f"{methodology.name}: {requirement['description'].lower()} is "
                    f"insufficient; {where}. Conclusions that rest on it will be withheld."
                ),
                payload={
                    "methodology": methodology.name,
                    "concept": requirement["concept"],
                    "coverage": requirement["coverage"],
                },
            )
        yield Beat(weight=5, label=f"assessed {methodology.name}")

    grades = ", ".join(f"{a['name']} {a['feasibility']}" for a in state.assessments)
    count = len(state.assessments)
    state.record(
        type="assessment.completed",
        category=Category.ANALYSIS,
        message=f"{NUMBERS.get(count, str(count))} methodologies assessed: {grades}.",
    )
    proposed = propose(state)
    state.record(
        type="solution.proposed",
        category=Category.ANALYSIS,
        message=f"{_count(len(proposed), 'Agent Component')} proposed, each with its assessment.",
        payload={"solutions": [dict(s) for s in proposed]},
    )
    yield Beat(weight=3, label="solutions proposed")

    # The ESCALATE of FR-P6 (OQ-6). Deployment is consequential, so the
    # system asks rather than proceeds, and the escalation is what the
    # approval answers. The lifecycle follows the decision.
    decision = authorize(
        state,
        ActionRequest(
            action=Action.DEPLOY,
            resource="Analytical services for the assessed methodologies",
            purpose="Implement and deploy the Agent Components the assessment proposed.",
        ),
    )
    if decision.effect is Effect.DENY:
        raise PolicyRefused(
            f"Deployment was denied under {decision.rule}. Nothing can be implemented."
        )
    state.transition(LifecycleState.AWAITING_APPROVAL)

    # No solution advances without a person's approval, whatever the rule
    # set says about deployment (FR-AP1): even an ALLOW would not bypass
    # the decision, it would only remove the reason for it.
    submitted = submit(state)
    state.record(
        type="solution.submitted",
        category=Category.DECISION,
        message=(
            f"{_count(len(submitted), 'Agent Component')} submitted for approval. Deployment was "
            f"{EFFECT_VERBS[decision.effect].lower()} under {decision.rule}."
        ),
        payload={"solutions": submitted, "rule": decision.rule},
    )
    yield Beat(weight=3, label="submitted for approval")

    total = len(submitted)
    while pending := awaiting(state):
        submission = yield AwaitHuman(
            request=BlockedOn(
                kind=RequestKind.APPROVAL,
                request_id=APPROVAL_REQUEST,
                prompt=(
                    f"{len(pending)} of {total} Agent Components "
                    f"await{'s' if len(pending) == 1 else ''} a decision."
                ),
                access="Deploy analytical services into the client environment",
                reason=(
                    f"Deployment is escalated under {decision.rule}: it is consequential, "
                    "and reviewable before it happens."
                ),
            )
        )
        submission = submission or {}
        try:
            decide(state, submission.get("solution"), submission.get("decision"), decision.rule)
        except InvalidDecision:
            # The API validates before resolving, so this is a client that
            # went round it. Nothing is recorded and the question stands.
            continue

    approved = sum(1 for s in state.solutions if s["status"] == "APPROVED")
    rejected = sum(1 for s in state.solutions if s["status"] == "REJECTED")
    state.record(
        type="approval.completed",
        category=Category.DECISION,
        message=f"Every Agent Component decided: {approved} approved, {rejected} rejected.",
        payload={"approved": approved, "rejected": rejected},
    )
    yield Beat(weight=2, label="decisions recorded")
