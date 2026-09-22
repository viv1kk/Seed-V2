"""The beat runner --- the simulation implementation of `EventSource`.

Workflows are generators. The runner advances one, does nothing itself
except decide how long each yielded beat lasts, and sends submitted
values back into the generator at the point it parked. All pacing lives
here, so a workflow reads as narrative rather than as scheduling.
"""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.domain.events import Category, Severity
from app.domain.lifecycle import Phase
from app.domain.state import BlockedOn, StateSnapshot, SystemState
from app.simulation.beats import AwaitHuman, Beat, Workflow
from app.simulation.protocol import (
    AlreadyRunning,
    NoPendingRequest,
    RunStatus,
    Speed,
    UnknownRequest,
)

#: How finely a beat's sleep is chopped. A speed change lands within one
#: slice, so an operator who presses 2x mid-beat does not wait out the
#: rest of it at the old rate (FR-O3).
SLEEP_SLICE = 0.05


@dataclass(frozen=True)
class WorkflowSpec:
    """A named stage of the narrative.

    The runner walks these in order. Adding a stage is an entry in the
    registry, which is what keeps M3 to M8 additive.
    """

    name: str
    factory: Callable[[SystemState], Workflow]


class SimulationEngine:
    """Drives `SystemState` forward through a sequence of workflows.

    Satisfies the `EventSource` protocol (NFR-A1). Nothing in the API
    layer imports this class.
    """

    def __init__(
        self,
        state: SystemState,
        workflows: Sequence[WorkflowSpec],
        *,
        total_duration: float,
        narrative_weight: float,
    ) -> None:
        #: Public, because the transport reads events from state rather
        #: than from the engine: state is the source of truth, and the
        #: engine is one writer to it (FR-L5).
        self.state = state
        self._workflows = tuple(workflows)
        self._total_duration = total_duration
        self._narrative_weight = narrative_weight

        self._speed = Speed.NORMAL
        self._task: asyncio.Task[None] | None = None
        self._pending: BlockedOn | None = None
        self._waiter: asyncio.Future[dict[str, Any]] | None = None
        self._skip_from: Phase | None = None

        # Accounting, for the M13 calibration of the 270 s target. The
        # declared narrative weight is a configured constant; these are
        # what a run actually consumed, so drift between the two is
        # measurable rather than assumed.
        self.consumed_weight = 0.0
        self.consumed_seconds = 0.0

    # -- Pacing ------------------------------------------------------

    @property
    def scale(self) -> float:
        """Seconds per unit of weight.

        The single number that retimes the whole narrative (D-8). M13
        calibrates it against the 270 s target (OQ-7).
        """
        return self._total_duration / self._narrative_weight

    @property
    def speed(self) -> Speed:
        return self._speed

    def set_speed(self, speed: Speed) -> None:
        """FR-O3: subsequent delays only. Ordering and state are untouched."""
        self._speed = speed

    def skip_phase(self) -> None:
        """Collapse delays until the phase changes (FR-O1).

        Recording the phase rather than a countdown means the skip ends
        itself: no beat needs to know it was skipped, and the events
        still occur in order.
        """
        self._skip_from = self.state.phase

    @property
    def _skipping(self) -> bool:
        return self._skip_from is not None and self.state.phase is self._skip_from

    async def _wait(self, beat: Beat) -> None:
        target = beat.seconds(self.scale)
        self.consumed_weight += beat.weight

        elapsed = 0.0
        while True:
            if self._speed is Speed.INSTANT or self._skipping:
                break
            remaining = target / self._speed.multiplier - elapsed
            if remaining <= 0:
                break
            step = min(SLEEP_SLICE, remaining)
            await asyncio.sleep(step)
            elapsed += step

        self.consumed_seconds += elapsed

    # -- Human input -------------------------------------------------

    async def _park(self, request: BlockedOn) -> dict[str, Any]:
        """Block on a person, and hand their answer back to the generator."""
        loop = asyncio.get_running_loop()
        self._pending = request
        self._waiter = loop.create_future()
        self.state.block(request)
        try:
            return await self._waiter
        finally:
            # `resolve_human` has already cleared `_pending`; a cancelled
            # wait has not, so clearing both here keeps a reset clean.
            self._pending = None
            self._waiter = None

    async def resolve_human(self, request_id: str, submission: dict[str, Any]) -> None:
        if self._pending is None or self._waiter is None:
            raise NoPendingRequest("The system is not waiting for input.")
        if self._pending.request_id != request_id:
            raise UnknownRequest(
                f"Expected a response to {self._pending.request_id}, got {request_id}."
            )

        waiter = self._waiter
        self._pending = None
        self.state.unblock()
        # The submission travels to the generator and is not retained
        # here. Credential values are never stored (FR-H5), and
        # `unblock` records the kind of request rather than its contents.
        waiter.set_result(submission)

    # -- Run ---------------------------------------------------------

    @property
    def status(self) -> RunStatus:
        if self._pending is not None:
            return RunStatus.AWAITING_HUMAN
        if self._task is None:
            return RunStatus.IDLE
        return RunStatus.COMPLETE if self._task.done() else RunStatus.RUNNING

    async def start(self) -> None:
        """Begin a run.

        Refused unless the engine is idle. A finished run is not a
        startable one: the workflows begin by transitioning out of
        UNINITIALIZED, so starting again over a completed run would
        raise inside the task where nobody is watching.
        """
        if self.status is not RunStatus.IDLE:
            raise AlreadyRunning(
                f"The run is {self.status}. Reset before starting another."
            )
        self._task = asyncio.create_task(self._drive())

    async def _drive(self) -> None:
        try:
            for spec in self._workflows:
                await self._advance(spec.factory(self.state))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # A workflow that fails is system activity, and all system
            # activity is expressed as events (FR-E1). Letting the
            # exception die with the task would leave the interface
            # showing a run that simply stopped.
            self.state.record(
                type="run.failed",
                category=Category.WARNING,
                severity=Severity.ERROR,
                message=f"The run stopped: {error}",
                payload={"error": type(error).__name__},
            )
            raise

    async def _advance(self, workflow: Workflow) -> None:
        """Pump one generator to exhaustion.

        `send` is what makes the resume exact: the generator continues at
        the `yield` it parked on, with the submitted values as that
        expression's value (FR-H7).
        """
        submission: dict[str, Any] | None = None
        while True:
            try:
                yielded = workflow.send(submission)
            except StopIteration:
                return
            submission = None

            if isinstance(yielded, AwaitHuman):
                submission = await self._park(yielded.request)
            else:
                await self._wait(yielded)

    async def reset(self) -> None:
        """Clear the run without restarting the process (FR-O4).

        Speed survives, because it is an operator preference rather than
        part of the run. Everything belonging to the run does not.
        """
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._waiter is not None and not self._waiter.done():
            self._waiter.cancel()

        self._task = None
        self._pending = None
        self._waiter = None
        self._skip_from = None
        self.consumed_weight = 0.0
        self.consumed_seconds = 0.0
        self.state.reset()

    def snapshot(self) -> StateSnapshot:
        return self.state.snapshot()
