"""Fan-out from the event log to connected clients.

The domain records events without knowing who is listening. This module
is the only place that knows about asyncio, and it exists so that
`SystemState` stays a plain object that a test can drive synchronously.
"""

import asyncio

from app.domain.events import Event


class EventBus:
    """Delivers each recorded event to every open stream.

    Queues are unbounded. A slow client cannot drop events, because
    FR-E7 promises exact replay and a dropped event would break the
    sequence the frontend checks against (FR-E6).
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[Event]] = set()

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: Event) -> None:
        for queue in self._subscribers:
            queue.put_nowait(event)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)
