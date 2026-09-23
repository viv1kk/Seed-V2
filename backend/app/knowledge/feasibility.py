"""Feasibility, computed from the evidence discovery profiled (FR-A2).

Nothing here is a verdict written in advance. A methodology declares the
concepts it needs; discovery profiled which fields carry each concept and
how complete each field is; the grade follows from those two facts and
from the thresholds below. Change a field's completeness and the grade
moves, which is the proof M7 exists to give.

The rules, in full:

- A requirement is only as good as its weakest field. A ticket record
  whose resolution timestamp is missing is not a ticket record the
  analysis can use, however complete its other fields are.
- A requirement is *sufficient* at 90% or better, *limited* from 70%,
  *incomplete* below that, and *missing* when no profiled field carries
  it at all.
- Feasibility is graded, never binary (FR-A3). HIGH when every
  requirement is sufficient. MEDIUM when some are only limited: the
  conclusions hold, with stated limitations. PARTIAL when some are
  incomplete: the conclusions that rest on them are withheld and the rest
  stand, which is §20's License Optimization exactly. LOW when evidence
  is missing outright or most of it is incomplete.
- Data sufficiency is the mean coverage across requirements. Feasibility
  is set by the weakest requirement and sufficiency by all of them, so the
  two answer different questions and can disagree.

Figures are simulated demo values (FR-A10), and every assessment says so.
"""

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from app.knowledge.methodologies import BY_ID, Methodology, Requirement
from app.knowledge.routing import routing_of

SUFFICIENT = 0.90
USABLE = 0.70

#: Fields below this completeness are named as a limitation even when the
#: requirement they belong to is sufficient, as §21 does with "8% of
#: records have incomplete categorization".
NOTEWORTHY = 0.99


class Standing(StrEnum):
    SUFFICIENT = "sufficient"
    LIMITED = "limited"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


class Grade(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    PARTIAL = "PARTIAL"
    LOW = "LOW"


RECOMMENDATIONS: dict[Grade, str] = {
    Grade.HIGH: "Strong value. Proceed: the Agent Component can deliver its full findings.",
    Grade.MEDIUM: "Value, with stated limits. Proceed: the findings hold, and the limits "
    "are named beside them.",
    Grade.PARTIAL: "Needs deeper modelling. Proceed with reduced scope: findings that rest "
    "on incomplete evidence are withheld until the data improves or the model is extended.",
    Grade.LOW: "Not yet modellable. Evidence the methodology needs is missing. Do not "
    "proceed until it is supplied.",
}


def percent(value: float) -> str:
    """0.942 as '94.2', 0.64 as '64'."""
    return f"{value * 100:.1f}".rstrip("0").rstrip(".")


def standing_of(coverage: float | None) -> Standing:
    if coverage is None:
        return Standing.MISSING
    if coverage >= SUFFICIENT:
        return Standing.SUFFICIENT
    if coverage >= USABLE:
        return Standing.LIMITED
    return Standing.INCOMPLETE


def grade_of(standings: Iterable[Standing]) -> Grade:
    standings = list(standings)
    incomplete = sum(1 for s in standings if s is Standing.INCOMPLETE)
    if Standing.MISSING in standings or incomplete * 2 > len(standings):
        return Grade.LOW
    if incomplete:
        return Grade.PARTIAL
    if Standing.LIMITED in standings:
        return Grade.MEDIUM
    return Grade.HIGH


def _carriers(requirement: Requirement, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every profiled field that carries the requirement's concept."""
    return [
        {
            "dataset": source["id"],
            "label": source["label"],
            "system": source["system"],
            "field": field["name"],
            "completeness": field["completeness"],
        }
        for source in sources
        for field in source["fields"]
        if field["concept"] == requirement.concept
    ]


def assess(methodology: Methodology, environment: dict[str, Any]) -> dict[str, Any]:
    """One methodology's assessment, with everything FR-A4 asks for."""
    sources = environment.get("dataSources", [])

    requirements = []
    for requirement in methodology.requires:
        fields = _carriers(requirement, sources)
        weakest = min(fields, key=lambda f: f["completeness"]) if fields else None
        coverage = weakest["completeness"] if weakest else None
        requirements.append(
            {
                "concept": requirement.concept,
                "description": requirement.description,
                "standing": standing_of(coverage),
                "coverage": coverage,
                "weakest": weakest,
                "fields": fields,
            }
        )

    standings = [r["standing"] for r in requirements]
    grade = grade_of(standings)
    located = sum(1 for r in requirements if r["standing"] is not Standing.MISSING)
    sufficiency = sum(r["coverage"] or 0.0 for r in requirements) / len(requirements)

    return {
        "id": methodology.id,
        "methodologyId": methodology.id,
        "name": methodology.name,
        "purpose": methodology.purpose,
        "feasibility": grade,
        "dataSufficiency": round(sufficiency, 3),
        "coverage": {"located": located, "required": len(requirements)},
        "requirements": requirements,
        "limitations": _limitations(requirements),
        "declaredLimitations": list(methodology.limitations),
        "improvements": _improvements(methodology, requirements, grade),
        "recommendation": RECOMMENDATIONS[grade],
        # Beside the grade, never inside it: evidence that exists but
        # cannot reach the analysis (D-12). Empty means no routing problem.
        "routing": routing_of(methodology.requires, environment),
        "process": list(methodology.process),
        "simulated": True,
    }


def _limitations(requirements: list[dict[str, Any]]) -> list[str]:
    """What the evidence cannot support, in figures taken from the profile."""
    found: list[str] = []
    for requirement in requirements:
        weakest = requirement["weakest"]
        if requirement["standing"] is Standing.MISSING:
            found.append(f"{requirement['description']}: no profiled field carries it.")
        elif requirement["standing"] is not Standing.SUFFICIENT:
            found.append(
                f"{requirement['description']}: {weakest['label']}.{weakest['field']} "
                f"is {percent(weakest['completeness'])}% complete."
            )
        else:
            for field in requirement["fields"]:
                if field["completeness"] < NOTEWORTHY:
                    found.append(
                        f"{percent(1 - field['completeness'])}% of {field['label']} records "
                        f"lack {field['field']}."
                    )
    return found


def _improvements(
    methodology: Methodology, requirements: list[dict[str, Any]], grade: Grade
) -> list[dict[str, Any]]:
    """What would raise feasibility, and to what (FR-A6).

    Each shortfall is lifted to sufficient on its own and the methodology
    regraded, so the effect claimed for an improvement is computed by the
    same rule that produced the grade rather than asserted beside it.
    """
    remedies = {r.concept: r.remedy for r in methodology.requires}
    found = []
    for index, requirement in enumerate(requirements):
        if requirement["standing"] is Standing.SUFFICIENT:
            continue
        lifted = [
            Standing.SUFFICIENT if i == index else r["standing"]
            for i, r in enumerate(requirements)
        ]
        weakest = requirement["weakest"]
        found.append(
            {
                "concept": requirement["concept"],
                "action": remedies[requirement["concept"]],
                "target": (
                    f"Raise {weakest['label']}.{weakest['field']} from "
                    f"{percent(weakest['completeness'])}% to {percent(SUFFICIENT)}% complete."
                    if weakest
                    else "Supply a source that carries it."
                ),
                "from": grade,
                "to": grade_of(lifted),
            }
        )
    return found


def assess_all(environment: dict[str, Any], ids: Iterable[str]) -> list[dict[str, Any]]:
    return [assess(BY_ID[i], environment) for i in ids]
