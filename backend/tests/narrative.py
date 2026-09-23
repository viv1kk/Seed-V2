"""Driving a run to its end, answering whatever it asks.

Since M7 the narrative parks twice over: once for the credential and then
once per solution for its decision. Every test that needs a finished run
answers the same way, so the answering lives here rather than in five
slightly different loops.
"""

import asyncio
from typing import Any

from app.domain.state import RequestKind
from app.knowledge.solutions import awaiting
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus


async def settle(runner: SimulationEngine, limit: float = 10.0) -> None:
    """Wait until the run finishes or parks on a person."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + limit
    while loop.time() < deadline:
        if runner.status in (RunStatus.AWAITING_HUMAN, RunStatus.COMPLETE):
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Run did not settle; status is {runner.status}.")


async def finish(
    runner: SimulationEngine,
    credentials: dict[str, Any] | None = None,
    decisions: dict[str, str] | None = None,
) -> None:
    """Answer every request until the run completes.

    Credentials are answered with `credentials`. Each solution awaiting a
    decision is approved unless `decisions` says otherwise, in the order
    the solutions were proposed.
    """
    while True:
        await settle(runner)
        pending = runner.state.blocked_on
        if runner.status is RunStatus.COMPLETE or pending is None:
            return
        if pending.kind is RequestKind.APPROVAL:
            target = awaiting(runner.state)[0]["id"]
            verdict = (decisions or {}).get(target, "approve")
            await runner.resolve_human(pending.request_id, {"solution": target, "decision": verdict})
        else:
            await runner.resolve_human(pending.request_id, dict(credentials or {"username": "svc"}))


async def run_to_end(runner: SimulationEngine, **answers: Any) -> None:
    await runner.start()
    await finish(runner, **answers)
