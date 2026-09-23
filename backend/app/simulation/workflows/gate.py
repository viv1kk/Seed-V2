"""Acting on a policy decision.

The engine answers; the workflow decides what the answer means for it
(section 10). Where a workflow needs an action to happen in order to go
on, it proceeds only on an ALLOW. Proceeding without one is what PR-082
forbids, and a run that quietly carried on past a refusal would make the
gate decorative. A refusal the workflow expects, such as the security log
in discovery, is handled where it is expected rather than here.
"""

from app.protection.engine import Decision
from app.protection.rules import Effect


class PolicyRefused(RuntimeError):
    """An action the narrative needed was not allowed."""


def proceed(decision: Decision) -> Decision:
    """Continue only on an ALLOW (PR-082)."""
    if decision.effect is not Effect.ALLOW:
        raise PolicyRefused(
            f"{decision.action.label} on {decision.resource} was {decision.effect} "
            f"under {decision.rule}. The workflow does not proceed without an ALLOW."
        )
    return decision
