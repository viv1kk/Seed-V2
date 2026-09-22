"""A throwaway workflow, to prove the backbone carries real transitions.

This exists to satisfy M1's exit criterion and nothing else. M2 deletes
it and replaces it with generator-based workflows driven by the beat
runner, so nothing here should be built on. It is scripted with plain
sleeps rather than weighted beats (D-8) precisely so that it does not
start looking like the engine.

What it does prove is the shape M2 must preserve: every step moves the
state machine and records an event, the human pause is a flag beside a
state rather than a state of its own (FR-L4), and the resume continues
from the point of suspension (FR-H7).
"""

import asyncio

from fastapi import APIRouter, HTTPException

from app.config import DEMO_STEP_INTERVAL
from app.domain.events import Category, Severity
from app.domain.lifecycle import LifecycleState
from app.domain.state import BlockedOn, RequestKind
from app.runtime import state

router = APIRouter()

_task: asyncio.Task | None = None


async def _pause() -> None:
    await asyncio.sleep(DEMO_STEP_INTERVAL)


async def _run() -> None:
    state.transition(LifecycleState.INITIALIZED)
    state.record(
        type="seed.loaded",
        category=Category.SUCCESS,
        message="Seed accepted. Three methodology definitions registered.",
    )
    await _pause()

    state.transition(LifecycleState.DISCOVERING)
    for system in ("ServiceNow", "Active Directory", "SCCM"):
        state.record(
            type="discovery.system.found",
            category=Category.DISCOVERY,
            message=f"{system} responded. Enumerating available data sources.",
            payload={"system": system},
        )
        await _pause()

    # The scripted pause. Discovery has not ended; it is waiting
    # (FR-L4, FR-D7).
    state.transition(LifecycleState.DISCOVERY_BLOCKED)
    state.block(
        BlockedOn(
            kind=RequestKind.CREDENTIALS,
            request_id="demo-credentials",
            prompt=(
                "Read credentials are required for the SCCM inventory endpoint, "
                "which holds the deployment data the assessment needs."
            ),
        )
    )


async def _resume() -> None:
    state.unblock()
    state.transition(LifecycleState.DISCOVERING)
    await _pause()

    state.record(
        type="discovery.endpoint.timeout",
        category=Category.WARNING,
        severity=Severity.WARNING,
        message="Inventory endpoint timed out after 30s. Retrying once.",
    )
    await _pause()

    state.record(
        type="discovery.endpoint.recovered",
        category=Category.SUCCESS,
        message="Inventory endpoint responded on retry. Discovery continues.",
    )
    await _pause()

    state.transition(LifecycleState.DISCOVERY_COMPLETE)
    state.transition(LifecycleState.ASSESSING)
    await _pause()

    state.record(
        type="assessment.completed",
        category=Category.ANALYSIS,
        message="Three methodologies assessed against the discovered evidence.",
    )
    state.transition(LifecycleState.AWAITING_APPROVAL)


def _start(coroutine) -> None:
    global _task
    if _task is not None and not _task.done():
        raise HTTPException(status_code=409, detail="The demo workflow is already running.")
    _task = asyncio.create_task(coroutine)


@router.post("/demo/start", status_code=202)
async def start() -> dict[str, str]:
    """Drive the state machine from UNINITIALIZED to the human pause."""
    if state.lifecycle is not LifecycleState.UNINITIALIZED:
        raise HTTPException(
            status_code=409,
            detail=f"Reset first. The system is in {state.lifecycle}.",
        )
    _start(_run())
    return {"status": "started"}


@router.post("/demo/resume", status_code=202)
async def resume() -> dict[str, str]:
    """Resolve the human pause and continue to AWAITING_APPROVAL."""
    if state.blocked_on is None:
        raise HTTPException(status_code=409, detail="The system is not waiting for input.")
    _start(_resume())
    return {"status": "resumed"}
