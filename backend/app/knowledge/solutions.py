"""Solutions: proposed, decided by a person, built and run (FR-AP1-AP3, FR-L8).

These operations are the real part of assessment in the sense of section
3.1 of the requirements: the solution lifecycle and its decisions are
built, not simulated. The assessment workflow calls them, and so does the
API, which is why they live here rather than inside `simulation/`.

Every change is recorded in System State and carried on an event, as full
records the frontend upserts, so the cards on screen are derived from the
same stream as the audit log (FR-L5).

A decision is recorded with the evidence it was made on: the feasibility
grade and data sufficiency at the moment of the decision, and the policy
rule that required it. `core.md` asks for exactly that where a
consequence is irreversible or external, and deployment is both. A later
revision of the evidence changes the assessment, never the record of
what the decision rested on.
"""

import copy
from typing import Any

from app.domain.events import Category
from app.domain.lifecycle import LifecycleState
from app.domain.solutions import SolutionStatus, assert_solution_transition
from app.domain.state import SystemState
from app.environment.acme import ACME
from app.environment.model import Environment
from app.knowledge.feasibility import Standing, assess, percent
from app.knowledge.methodologies import BY_ID, METHODOLOGIES

APPROVAL_REQUEST = "solution-approval"

VERDICTS: dict[str, SolutionStatus] = {
    "approve": SolutionStatus.APPROVED,
    "reject": SolutionStatus.REJECTED,
}


class InvalidDecision(ValueError):
    """A decision that names no awaiting solution, or no known verdict."""


def solution(state: SystemState, solution_id: str) -> dict[str, Any] | None:
    return next((s for s in state.solutions if s["id"] == solution_id), None)


def assessment(state: SystemState, assessment_id: str) -> dict[str, Any] | None:
    return next((a for a in state.assessments if a["id"] == assessment_id), None)


def awaiting(state: SystemState) -> list[dict[str, Any]]:
    return [s for s in state.solutions if s["status"] == SolutionStatus.AWAITING_APPROVAL]


def _move(record: dict[str, Any], target: SolutionStatus) -> None:
    assert_solution_transition(record["name"], SolutionStatus(record["status"]), target)
    record["status"] = target


def record_assessment(state: SystemState, result: dict[str, Any]) -> None:
    """Store an assessment, replacing any earlier one for the methodology.

    Replaced rather than updated in place: an event that carried the
    earlier assessment holds that object, and it must not change after
    the fact (FR-E7).
    """
    for index, existing in enumerate(state.assessments):
        if existing["id"] == result["id"]:
            state.assessments[index] = result
            return
    state.assessments.append(result)


def propose(state: SystemState) -> list[dict[str, Any]]:
    """One solution per assessed methodology, in the methodologies' order.

    Every methodology is proposed, whatever its grade. A grade is a
    statement about evidence, and deciding what to do about weak evidence
    is the person's call, not the system's (FR-A5, FR-AP4).
    """
    proposed = []
    for methodology in METHODOLOGIES:
        if assessment(state, methodology.id) is None or solution(state, methodology.id):
            continue
        record = {
            "id": methodology.id,
            "methodologyId": methodology.id,
            "assessmentId": methodology.id,
            "name": methodology.name,
            "description": methodology.purpose,
            "status": SolutionStatus.PROPOSED,
            "dashboardId": None,
        }
        state.solutions.append(record)
        proposed.append(record)
    return proposed


def submit(state: SystemState) -> list[dict[str, Any]]:
    """Put every proposed solution to a person."""
    submitted = []
    for record in state.solutions:
        if record["status"] == SolutionStatus.PROPOSED:
            _move(record, SolutionStatus.AWAITING_APPROVAL)
            submitted.append(dict(record))
    return submitted


def check(state: SystemState, solution_id: Any, verdict: Any) -> tuple[dict[str, Any], SolutionStatus]:
    """Validate a decision before anything is recorded."""
    target = VERDICTS.get(verdict) if isinstance(verdict, str) else None
    if target is None:
        raise InvalidDecision(f"A decision is one of {', '.join(VERDICTS)}.")
    record = solution(state, solution_id) if isinstance(solution_id, str) else None
    if record is None:
        raise InvalidDecision(f"No solution {solution_id!r} has been proposed.")
    if record["status"] != SolutionStatus.AWAITING_APPROVAL:
        raise InvalidDecision(f"{record['name']} is {record['status']}, not awaiting a decision.")
    return record, target


def decide(state: SystemState, solution_id: Any, verdict: Any, rule: str) -> dict[str, Any]:
    """Record a person's decision on one solution (FR-AP3, FR-H6)."""
    record, target = check(state, solution_id, verdict)
    evidence = assessment(state, record["assessmentId"]) or {}
    _move(record, target)

    approval = {
        "id": f"{record['id']}@{state.events.last_sequence + 1}",
        "solutionId": record["id"],
        "decision": target,
        "feasibility": evidence.get("feasibility"),
        "dataSufficiency": evidence.get("dataSufficiency"),
        "rule": rule,
        "decidedAt": state.events.last_sequence + 1,
    }
    state.approvals.append(approval)

    grade = evidence.get("feasibility", "unassessed")
    if target is SolutionStatus.APPROVED:
        message = f"{record['name']} approved for implementation, on feasibility {grade}."
        kind = "solution.approved"
    else:
        message = (
            f"{record['name']} rejected, on feasibility {grade}. "
            "The decision is recorded and is final."
        )
        kind = "solution.rejected"
    state.record(
        type=kind,
        category=Category.HUMAN_INPUT,
        message=message,
        payload={"solutions": [dict(record)], "approvals": [dict(approval)]},
    )
    return approval


def revise_evidence(
    state: SystemState, dataset_id: str, field: str, completeness: float
) -> dict[str, Any]:
    """Revise one field's completeness and regrade what depends on it.

    The rehearsal proof that FR-A2 is computed: the grade on the card
    changes because the evidence under it changed, by the same function
    that produced it in the first place. The revision is recorded, since
    evidence that changed without a record is exactly what the audit log
    exists to rule out.
    """
    env = Environment(state, ACME)
    previous = env.revise(dataset_id, field, completeness)

    changes = []
    revised = []
    for existing in list(state.assessments):
        result = assess(BY_ID[existing["methodologyId"]], state.environment)
        if result["feasibility"] != existing["feasibility"]:
            changes.append(f"{result['name']} {existing['feasibility']} to {result['feasibility']}")
        record_assessment(state, result)
        revised.append(result)

    label = (env.source(dataset_id) or {}).get("label", dataset_id)
    message = (
        f"Evidence revised by the operator: {label}.{field} is now "
        f"{percent(completeness)}% complete, was {percent(previous)}%."
    )
    if changes:
        message += " Feasibility moved: " + "; ".join(changes) + "."
    elif revised:
        message += " No feasibility grade changed."
    event = env.record(
        type="assessment.evidence.revised",
        category=Category.VALIDATION,
        message=message,
        payload={
            "dataset": dataset_id,
            "field": field,
            "from": previous,
            "to": completeness,
            "assessments": copy.deepcopy(revised),
        },
    )
    return event.payload


def shortfalls(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Requirements too weak to conclude on, which assessment reports as such."""
    return [
        r
        for r in result["requirements"]
        if r["standing"] in (Standing.INCOMPLETE, Standing.MISSING)
    ]


# -- Implementation and runtime (FR-I6, FR-L8) ---------------------------


class NotRunnable(ValueError):
    """A run or a return the current state does not allow."""


def approval_of(state: SystemState, solution_id: str) -> dict[str, Any] | None:
    """The decision a solution was approved on, if it was."""
    return next(
        (
            a
            for a in reversed(state.approvals)
            if a["solutionId"] == solution_id and a["decision"] == SolutionStatus.APPROVED
        ),
        None,
    )


def approved(state: SystemState) -> list[dict[str, Any]]:
    return [s for s in state.solutions if s["status"] == SolutionStatus.APPROVED]


def begin_build(record: dict[str, Any]) -> None:
    """APPROVED to BUILDING. Nothing unapproved can reach here (FR-AP1)."""
    _move(record, SolutionStatus.BUILDING)


def mark_ready(record: dict[str, Any]) -> None:
    """BUILDING to READY. The solution's dashboard is named from here on."""
    _move(record, SolutionStatus.READY)
    record["dashboardId"] = record["id"]


def runnable(state: SystemState) -> list[dict[str, Any]]:
    return [s for s in state.solutions if s["status"] == SolutionStatus.READY]


def run(state: SystemState, solution_id: str) -> dict[str, Any]:
    """Run a ready solution: the system moves to RUNNING and its dashboard opens.

    Every check precedes every change, so a refused run leaves the system
    exactly as it was (FR-L3). One solution runs at a time; returning to the
    workspace is what makes the next one runnable (FR-L8).
    """
    record = solution(state, solution_id)
    if record is None:
        raise KeyError(f"No solution {solution_id!r} has been proposed.")
    if state.lifecycle is LifecycleState.RUNNING:
        active = solution(state, state.runtime.get("active") or "") or {"name": "A solution"}
        raise NotRunnable(
            f"{active['name']} is running. Return to the workspace before running another."
        )
    if state.lifecycle is not LifecycleState.READY_TO_RUN:
        raise NotRunnable(
            f"The system is {state.lifecycle}. Solutions run once implementation is complete."
        )
    assert_solution_transition(record["name"], SolutionStatus(record["status"]), SolutionStatus.RUNNING)

    state.transition(LifecycleState.RUNNING)
    _move(record, SolutionStatus.RUNNING)
    sequence = state.events.last_sequence + 1
    runs = list(state.runtime.get("runs", []))
    runs.append(
        {
            "id": f"{solution_id}@{sequence}",
            "solutionId": solution_id,
            "startedAt": sequence,
            "closedAt": None,
        }
    )
    state.runtime = {"active": solution_id, "runs": runs}
    return state.record(
        type="solution.started",
        category=Category.HUMAN_INPUT,
        message=f"{record['name']} is running. Its dashboard is open.",
        payload={"solutions": [dict(record)], "runtime": copy.deepcopy(state.runtime)},
    ).payload


def close(state: SystemState, solution_id: str) -> dict[str, Any]:
    """Return from a running solution to the workspace (FR-L8)."""
    record = solution(state, solution_id)
    if record is None:
        raise KeyError(f"No solution {solution_id!r} has been proposed.")
    if state.lifecycle is not LifecycleState.RUNNING or state.runtime.get("active") != solution_id:
        raise NotRunnable(f"{record['name']} is not running.")

    _move(record, SolutionStatus.READY)
    state.transition(LifecycleState.READY_TO_RUN)
    sequence = state.events.last_sequence + 1
    runs = [dict(r) for r in state.runtime.get("runs", [])]
    runs[-1]["closedAt"] = sequence
    state.runtime = {"active": None, "runs": runs}
    return state.record(
        type="solution.closed",
        category=Category.HUMAN_INPUT,
        message=f"Returned to the workspace from {record['name']}. It remains ready to run.",
        payload={"solutions": [dict(record)], "runtime": copy.deepcopy(state.runtime)},
    ).payload
