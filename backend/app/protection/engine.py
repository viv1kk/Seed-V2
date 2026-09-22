"""The policy engine: evaluate a request, then record the decision.

§10's diagram, in code:

    Agent -> Tool request -> Policy engine -> Allowed / Denied / Human approval -> Tool execution

`evaluate` is pure. It reads a request and the rule set and returns a
decision, touching nothing, which is what makes it testable exhaustively
and what lets the API offer it as a dry run. `authorize` is what a
workflow calls: it evaluates, records the decision as a first-class event
(FR-P4), and hands the decision back so the workflow can act on it.

The engine does not act on the decision itself. Proceeding, skipping a
dataset, or waiting on a person is the requester's business; the engine's
is the answer and the record of it. That separation is the architectural
point of §10: the component that wants to do something is not the
component that decides whether it may.
"""

from pydantic import Field

from app.domain.events import Category, Severity
from app.domain.schema import Schema
from app.domain.state import SystemState
from app.protection.rules import (
    FALLBACK,
    RULES,
    Action,
    ActionRequest,
    Effect,
    Rule,
    required_facts,
)

EFFECT_VERBS: dict[Effect, str] = {
    Effect.ALLOW: "Allowed",
    Effect.DENY: "Denied",
    Effect.ESCALATE: "Escalated",
}


class Decision(Schema):
    """The engine's answer, with the rule that produced it (FR-P3, FR-P4).

    `rule` is the deciding rule. `matched` lists every rule that applied,
    so the audit log can show that a permissive rule was present and
    overruled rather than absent. `missing` is non-empty only when the
    request failed to establish the facts its rules depend on.
    """

    effect: Effect
    rule: str
    matched: list[str] = Field(default_factory=list)
    action: Action
    resource: str
    reason: str
    missing: list[str] = Field(default_factory=list)


def _deciding(rules: list[Rule]) -> Rule:
    """The strictest effect wins; among those, the most specific rule is cited.

    Precedence is fixed (protection.md, "Precedence"): no rule can claim
    priority, so a permissive rule can never weaken a restrictive one.
    Specificity only chooses *which* restrictive rule to cite when several
    agree, and ties go to the lower identifier so the citation is stable.
    """
    strictest = max(rule.effect.strictness for rule in rules)
    candidates = [rule for rule in rules if rule.effect.strictness == strictest]
    return sorted(candidates, key=lambda rule: (-rule.specificity, rule.id))[0]


def evaluate(request: ActionRequest, rules: tuple[Rule, ...] = RULES) -> Decision:
    """Decide one request. Pure: nothing is recorded (FR-P1)."""
    missing = [fact for fact in required_facts(request.action) if getattr(request, fact) is None]
    if missing:
        return Decision(
            effect=FALLBACK.effect,
            rule=FALLBACK.id,
            action=request.action,
            resource=request.resource,
            reason=(
                "The request did not establish "
                + ", ".join(missing)
                + ". An unstated fact is not assumed benign."
            ),
            missing=missing,
        )

    matched = [rule for rule in rules if rule.covers(request.action) and rule.holds(request)]
    if not matched:
        return Decision(
            effect=FALLBACK.effect,
            rule=FALLBACK.id,
            action=request.action,
            resource=request.resource,
            reason=FALLBACK.rationale,
        )

    deciding = _deciding(matched)
    return Decision(
        effect=deciding.effect,
        rule=deciding.id,
        matched=sorted(rule.id for rule in matched),
        action=request.action,
        resource=request.resource,
        reason=deciding.rationale,
    )


def authorize(state: SystemState, request: ActionRequest) -> Decision:
    """Evaluate a request and record the decision in the stream (FR-P2, FR-P4).

    Every decision is recorded, allow included (PR-080). A control that
    only speaks when it refuses is indistinguishable from one that was
    never consulted.

    DENY and ESCALATE carry WARNING severity because they are notable, not
    because they are faults: the presentation convention keys on the type,
    and `policy.decision` is never presented as an error (FR-H4).
    """
    decision = evaluate(request)
    verb = EFFECT_VERBS[decision.effect]

    state.record(
        type="policy.decision",
        category=Category.POLICY,
        severity=Severity.INFO if decision.effect is Effect.ALLOW else Severity.WARNING,
        message=f"{request.action.label}: {request.resource}. {verb} under {decision.rule}.",
        payload={
            "verb": request.action,
            "action": request.action.label,
            "resource": request.resource,
            "source": request.source,
            "purpose": request.purpose,
            "effect": decision.effect,
            "rule": decision.rule,
            "matched": decision.matched,
            "reason": decision.reason,
            "missing": decision.missing,
        },
    )
    return decision
