"""Server-sent event stream with exact replay.

A client that reconnects sends `Last-Event-ID`, and receives every event
recorded since that sequence number before it receives any live one
(FR-E7). The browser's own `EventSource` sets that header without being
asked, so replay costs the frontend nothing.

The order of work in `_stream` is what makes replay exact: subscribe
first, then read the backlog. Reading first would leave a window in
which an event is recorded after the backlog is taken and before the
subscription exists, and that event would be lost with no gap visible
to the client.
"""

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import KEEPALIVE_INTERVAL
from app.domain.events import Event
from app.runtime import bus, state

router = APIRouter()


def _frame(event: Event) -> str:
    """Format one event as an SSE frame.

    The `id` field is the sequence number. That is what the browser
    echoes back as `Last-Event-ID`, so the sequence is both the gap
    check and the replay cursor.
    """
    return (
        f"id: {event.sequence}\n"
        f"event: {event.type}\n"
        f"data: {event.model_dump_json()}\n\n"
    )


def _last_event_id(request: Request) -> int:
    """Read the replay cursor, tolerating a malformed header.

    A client that sends nonsense gets the whole log rather than an
    error: over-delivery is recoverable, silent under-delivery is not.
    """
    raw = request.headers.get("last-event-id")
    if raw is None:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


async def _stream(request: Request) -> AsyncIterator[str]:
    queue = bus.subscribe()
    try:
        # Subscribe, then take the backlog, with no await in between.
        # Nothing else can run in that window, so the backlog holds
        # every event recorded before this point and the queue holds
        # every event recorded after it. The two are disjoint, which is
        # why no duplicate check is needed below --- and a duplicate
        # check would be wrong anyway, since Reset restarts the
        # sequence, after which a lower number is a new event rather
        # than an echo.
        backlog = list(state.events.since(_last_event_id(request)))

        for event in backlog:
            yield _frame(event)

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_INTERVAL)
            except asyncio.TimeoutError:
                # An SSE comment. Keeps the connection from being closed
                # as idle during the quiet stretches of the narrative.
                yield ": keepalive\n\n"
                continue
            yield _frame(event)
    finally:
        bus.unsubscribe(queue)


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
