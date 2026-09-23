"""Evidence revision, for rehearsal.

Moving one profiled field's completeness regrades every assessment that
rests on it, through the same computation that graded it in the first
place. This is the demonstration that feasibility is computed rather than
authored (FR-A2), and M7's exit criterion.

It is an operator control, reached from the hidden panel and never from
the audience's surface (FR-O2). The revision is recorded in the stream
all the same: evidence that changed without a record is the one thing an
audit log must never allow.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domain.state import StateSnapshot
from app.knowledge.solutions import revise_evidence
from app.runtime import state

router = APIRouter()


class Revision(BaseModel):
    completeness: float = Field(ge=0.0, le=1.0)


@router.post(
    "/environment/sources/{dataset_id}/fields/{field}", response_model=StateSnapshot
)
async def revise(dataset_id: str, field: str, revision: Revision) -> StateSnapshot:
    try:
        revise_evidence(state, dataset_id, field, revision.completeness)
    except KeyError as error:
        raise HTTPException(404, str(error.args[0])) from error
    return state.snapshot()
