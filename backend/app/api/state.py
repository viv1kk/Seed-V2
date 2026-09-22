"""State snapshot and Reset."""

from fastapi import APIRouter

from app.domain.state import StateSnapshot
from app.runtime import state

router = APIRouter()


@router.get("/state", response_model=StateSnapshot)
async def get_state() -> StateSnapshot:
    """The full state, with the sequence number it is current as of.

    The frontend fetches this on connect and then applies the event
    stream from that sequence onward (FR-E5).
    """
    return state.snapshot()


@router.post("/state/reset", response_model=StateSnapshot)
async def reset_state() -> StateSnapshot:
    """Return the system to UNINITIALIZED (FR-L7, FR-O1).

    The event log is discarded with the run. Connected clients see the
    sequence restart and re-snapshot, which is the same path FR-E6
    already requires them to handle.
    """
    state.reset()
    return state.snapshot()
