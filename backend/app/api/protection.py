"""The protection layer's surface.

The rule set is served for the panel (FR-P5), grouped as `protection.md`
groups it, so what the panel shows is the rule set being enforced rather
than a copy of the document (FR-P7).

`evaluate` is a dry run. It answers what the engine would decide for a
request and records nothing, so asking never changes the run and the
audit log contains only what the system actually requested. It exists so
the engine can be questioned directly: a decision that can be reproduced
on demand is evidence that it is evaluated rather than scripted (FR-P1).
"""

from fastapi import APIRouter

from app.domain.schema import Schema
from app.protection.engine import Decision, evaluate
from app.protection.rules import GROUPS, RULES, Action, ActionRequest, Effect

router = APIRouter(prefix="/protection")


class RuleView(Schema):
    id: str
    description: str
    effect: Effect
    rationale: str
    actions: list[Action]
    facts: list[str]


class RuleGroup(Schema):
    name: str
    rules: list[RuleView]


@router.get("/rules", response_model=list[RuleGroup])
async def get_rules() -> list[RuleGroup]:
    """The active rule set, in document order."""
    return [
        RuleGroup(
            name=group,
            rules=[
                RuleView(
                    id=rule.id,
                    description=rule.description,
                    effect=rule.effect,
                    rationale=rule.rationale,
                    actions=sorted(rule.actions or ()),
                    facts=sorted(rule.when),
                )
                for rule in RULES
                if rule.group == group
            ],
        )
        for group in GROUPS
    ]


@router.post("/evaluate", response_model=Decision)
async def post_evaluate(request: ActionRequest) -> Decision:
    """What the engine would decide. Nothing is recorded."""
    return evaluate(request)
