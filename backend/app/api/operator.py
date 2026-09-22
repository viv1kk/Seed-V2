"""Run and operator controls.

Every route here goes through the `EventSource` protocol. Nothing in this
module knows that a simulation is behind it (NFR-A1).

The controls are deliberately unglamorous endpoints: the surface that
reaches them is a keyboard shortcut and a hidden panel, never a visible
transport bar (FR-O2), and that is a frontend concern.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.state import StateSnapshot
from app.runtime import source
from app.simulation.protocol import RunStatus, Speed

router = APIRouter()


class RunState(BaseModel):
    """What the operator panel needs to render itself."""

    status: RunStatus
    speed: Speed


class SpeedChange(BaseModel):
    speed: Speed


@router.get("/operator", response_model=RunState)
async def get_run_state() -> RunState:
    return RunState(status=source.status, speed=source.speed)


@router.post("/operator/start", status_code=202, response_model=RunState)
async def start() -> RunState:
    await source.start()
    return RunState(status=source.status, speed=source.speed)


@router.post("/operator/speed", response_model=RunState)
async def set_speed(change: SpeedChange) -> RunState:
    """FR-O1, FR-O3. Applies to subsequent delays; ordering is untouched."""
    source.set_speed(change.speed)
    return RunState(status=source.status, speed=source.speed)


@router.post("/operator/skip", response_model=RunState)
async def skip_phase() -> RunState:
    """FR-O1. Drops the remaining delay until the phase changes."""
    source.skip_phase()
    return RunState(status=source.status, speed=source.speed)


@router.post("/operator/reset", response_model=StateSnapshot)
async def reset() -> StateSnapshot:
    """FR-O4. Clears the run without restarting the backend."""
    await source.reset()
    return source.snapshot()
