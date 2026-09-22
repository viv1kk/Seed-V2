"""Server-sent event stream.

M0 carries a single trivial event type end to end so the transport is
proven before anything depends on it. M1 replaces the generator below
with the real event log, `Last-Event-ID` replay and sequence-gap
detection (FR-E1--E7); the wire format used here is already the one
M1 needs, so only the source of the events changes.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import HEARTBEAT_INTERVAL

router = APIRouter()


def _frame(sequence: int, event_type: str, payload: dict) -> str:
    """Format one event as an SSE frame.

    The `id` field is the sequence number, which is what makes
    `Last-Event-ID` replay possible in M1.
    """
    body = {
        "sequence": sequence,
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    return f"id: {sequence}\nevent: {event_type}\ndata: {json.dumps(body)}\n\n"


async def _stream(request: Request) -> AsyncIterator[str]:
    sequence = 0
    while True:
        if await request.is_disconnected():
            return
        sequence += 1
        yield _frame(sequence, "system.heartbeat", {"message": "backbone alive"})
        await asyncio.sleep(HEARTBEAT_INTERVAL)


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disables proxy buffering, which otherwise holds frames
            # until the stream closes.
            "X-Accel-Buffering": "no",
        },
    )
