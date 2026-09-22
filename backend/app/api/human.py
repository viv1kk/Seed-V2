"""Human input submission.

The submitted body is forwarded to the parked workflow and is not
retained, logged or written to state. Credential values are used for the
simulated handshake and discarded (FR-H5), so this module deliberately
holds no model of what a submission contains: an unvalidated dict cannot
leak a field that a schema would have named.
"""

from typing import Any

from fastapi import APIRouter, Body

from app.domain.state import StateSnapshot
from app.runtime import source

router = APIRouter()


@router.post("/human/{request_id}", response_model=StateSnapshot)
async def resolve(
    request_id: str,
    submission: dict[str, Any] = Body(default_factory=dict),
) -> StateSnapshot:
    """Answer the outstanding request and resume the workflow (FR-H7)."""
    await source.resolve_human(request_id, submission)
    return source.snapshot()
