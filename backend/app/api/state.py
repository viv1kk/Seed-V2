"""The state snapshot.

Reset lives on the operator router, because clearing state and
cancelling the run must happen together and the event source owns
the run (FR-O4).
"""

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
