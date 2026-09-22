"""The seam between the API and whatever produces events (NFR-A1).

The API layer depends on this protocol and never on the simulation
engine. Substituting a real agent runtime means writing another
implementation of `EventSource`; no route changes, and the frontend does
not know the difference (NFR-A2).

The pacing controls are part of the protocol because the operator surface
needs them, but they are advisory: a real runtime that cannot be sped up
or skipped may accept them and do nothing. Leaving them out instead
would put a simulation-shaped hole in the API layer, which is the
coupling this seam exists to prevent.
"""

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from app.domain.state import StateSnapshot


class Speed(StrEnum):
    """Playback speed (FR-O1).

    `INSTANT` is not a large multiplier. It removes delay entirely,
    including the floors that protect meaning-bearing beats, because an
    operator asking for instant is rehearsing structure rather than
    watching the narrative.
    """

    NORMAL = "1x"
    DOUBLE = "2x"
    INSTANT = "instant"

    @property
    def multiplier(self) -> float:
        return {Speed.NORMAL: 1.0, Speed.DOUBLE: 2.0, Speed.INSTANT: 0.0}[self]


class EngineError(Exception):
    """A refusal by the event source, which the API returns as a 409.

    Declared on the protocol rather than on an implementation so that the
    API can catch it without importing the engine (NFR-A1).
    """


class AlreadyRunning(EngineError):
    pass


class NoPendingRequest(EngineError):
    pass


class UnknownRequest(EngineError):
    pass


class RunStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting-human"
    COMPLETE = "complete"


@runtime_checkable
class EventSource(Protocol):
    """Whatever drives System State forward.

    Implementations own their own progression. They do not return events:
    they record them into `SystemState`, which remains the sole source of
    truth (FR-L5), and the transport reads from there.
    """

    @property
    def status(self) -> RunStatus: ...

    @property
    def speed(self) -> Speed: ...

    async def start(self) -> None:
        """Begin a run. Raises if one is already in progress."""
        ...

    async def resolve_human(self, request_id: str, submission: dict[str, Any]) -> None:
        """Answer the outstanding request and resume (FR-H7)."""
        ...

    def set_speed(self, speed: Speed) -> None:
        """Apply to all subsequent delays, without touching ordering (FR-O3)."""
        ...

    def skip_phase(self) -> None:
        """Drop the remaining delay until the phase changes (FR-O1)."""
        ...

    async def reset(self) -> None:
        """Clear the run without restarting the process (FR-O4)."""
        ...

    def snapshot(self) -> StateSnapshot: ...
