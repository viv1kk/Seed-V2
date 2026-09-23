"""The routing-problem flag, computed from System State (D-12, FR-A12, FR-A13).

A routing problem is evidence a methodology requires that **exists in
the environment but cannot reach the analysis**. It is a flag beside the
grade, not a fifth grade, because the two are independent: a
methodology can have HIGH potential and a blocked path to part of it at
the same time. Folding the two into one scale would lose that.

It is also not insufficient evidence (FR-H4). Insufficiency is evidence
that is thin or absent, and the grade already says so. A routing problem
is evidence that is there and out of reach.

What counts, and from where
---------------------------
Every fact is read from the environment graph System State holds; none
is authored:

- *Exists* means the dataset has been found: it is a node in the graph.
  A dataset nobody has found yet is not a routing problem, because it is
  not yet known to exist (G-2).
- *Carries a required concept* is read from the Adaptation layer's
  concept mapping, the same field-to-concept mapping a profile reports.
  A dataset outside that mapping carries nothing a methodology requires,
  whatever policy decided about it.
- *Cannot reach the analysis* is one of three facts. Policy refused the
  dataset, which the graph records with the deciding rule. The dataset,
  or the surface or system it is read through, is in error. Or one of
  them is waiting on a person's input.

The mapping and the parentage come from the environment definition,
which is where the graph's nodes come from. The state of each node comes
from the graph, so changing a node's status, or the policy decision
recorded on it, changes the flag (FR-A13).
"""

from collections.abc import Iterable
from typing import Any

from app.environment.acme import ACME
from app.environment.model import Definition, NodeKind, NodeStatus

#: Why a dataset's evidence cannot reach the analysis.
REFUSED = "refused"
UNREACHABLE = "unreachable"
AWAITING_INPUT = "awaiting-input"


def _blocked(
    node_id: str, nodes: dict[str, dict[str, Any]], definition: Definition
) -> tuple[str, str | None, str] | None:
    """Why this dataset's evidence cannot reach the analysis, if it cannot.

    Returns the reason, the rule that decided it (for a refusal), and the
    node where the path is blocked, which is the dataset itself or the
    surface or system above it.
    """
    node = nodes[node_id]
    if node.get("excludedBy"):
        return REFUSED, node["excludedBy"], node_id
    current: str | None = node_id
    while current is not None:
        found = nodes.get(current)
        if found is not None:
            if found["status"] == NodeStatus.ERROR:
                return UNREACHABLE, None, current
            if found["status"] == NodeStatus.REQUIRES_INPUT:
                return AWAITING_INPUT, None, current
        current = definition.by_id[current].parent
    return None


def routing_of(
    requires: Iterable[Any],
    environment: dict[str, Any],
    definition: Definition = ACME,
) -> list[dict[str, Any]]:
    """Every required concept whose found evidence cannot reach the analysis.

    One entry per blocked dataset and concept. An empty list means no
    routing problem.
    """
    nodes = {node["id"]: node for node in environment.get("nodes", [])}
    found: list[dict[str, Any]] = []
    for requirement in requires:
        for node_id in nodes:
            spec = definition.by_id.get(node_id)
            if spec is None or spec.kind is not NodeKind.DATASET:
                continue
            if requirement.concept not in spec.concepts:
                continue
            blocked = _blocked(node_id, nodes, definition)
            if blocked is None:
                continue
            reason, rule, at = blocked
            found.append(
                {
                    "concept": requirement.concept,
                    "description": requirement.description,
                    "dataset": node_id,
                    "label": spec.label,
                    "reason": reason,
                    "rule": rule,
                    "at": definition.by_id[at].label,
                }
            )
    return found
