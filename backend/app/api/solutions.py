"""Solutions, and the decisions a person makes on them (FR-AP1-AP3).

A decision is an answer to the approval request the run is parked on, so
it travels through the `EventSource` protocol like any other answer
(NFR-A1) and the workflow resumes from its exact point of suspension
(FR-H7). What this module adds is validation before anything is sent: a
decision on a solution that is not awaiting one is refused here with the
reason, rather than reaching the run at all.

Running a ready solution, and returning from it, are not answers to
anything the run is waiting on. The narrative has finished by then, so
they are operations on System State in their own right, like planting the
seed. The state machine checks them (FR-L3, FR-L8), and each is recorded
in the stream because it is a person acting on the system.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domain.state import StateSnapshot
from app.knowledge.solutions import (
    APPROVAL_REQUEST,
    InvalidDecision,
    NotRunnable,
    check,
    close,
    run,
)
from app.runtime import source, state

router = APIRouter()


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]


@router.post("/solutions/{solution_id}/decision", response_model=StateSnapshot)
async def decide(solution_id: str, request: DecisionRequest) -> StateSnapshot:
    pending = state.blocked_on
    if pending is None or pending.request_id != APPROVAL_REQUEST:
        raise HTTPException(409, "The system is not waiting for a decision on solutions.")
    try:
        check(state, solution_id, request.decision)
    except InvalidDecision as error:
        raise HTTPException(409, str(error)) from error

    await source.resolve_human(
        APPROVAL_REQUEST, {"solution": solution_id, "decision": request.decision}
    )
    return source.snapshot()


@router.post("/solutions/{solution_id}/run", response_model=StateSnapshot)
async def run_solution(solution_id: str) -> StateSnapshot:
    """Open a ready solution's dashboard (FR-I6, §53)."""
    try:
        run(state, solution_id)
    except KeyError as error:
        raise HTTPException(404, str(error.args[0])) from error
    except NotRunnable as error:
        raise HTTPException(409, str(error)) from error
    return state.snapshot()


@router.post("/solutions/{solution_id}/close", response_model=StateSnapshot)
async def close_solution(solution_id: str) -> StateSnapshot:
    """Return to the workspace; the solution stays ready to run (FR-L8)."""
    try:
        close(state, solution_id)
    except KeyError as error:
        raise HTTPException(404, str(error.args[0])) from error
    except NotRunnable as error:
        raise HTTPException(409, str(error)) from error
    return state.snapshot()
