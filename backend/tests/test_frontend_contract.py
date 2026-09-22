"""The event types the browser subscribes to, held to what the backend emits.

SSE delivers named events only to listeners registered for that name, so
an event type missing from the frontend's list is not an error anywhere:
it simply never arrives. M3 found one such gap by accident (`run.failed`).
This makes the next one a test failure instead.
"""

import asyncio
import re
from pathlib import Path

import pytest

from app.domain.lifecycle import LifecycleState
from app.domain.state import SystemState
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE

EVENTS_STORE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "stores" / "events.ts"

#: Emitted outside a narrative run: by the seed API and by a failing run.
OUTSIDE_THE_NARRATIVE = {"seed.loaded", "run.failed"}


def subscribed() -> set[str]:
    source = EVENTS_STORE.read_text(encoding="utf-8")
    block = re.search(r"const EVENT_TYPES = \[(.*?)\] as const", source, re.S)
    assert block, "EVENT_TYPES not found in events.ts"
    return set(re.findall(r"'([a-z._]+)'", block.group(1)))


@pytest.mark.asyncio
async def test_the_browser_subscribes_to_every_event_the_backend_emits() -> None:
    state = SystemState()
    state.transition(LifecycleState.INITIALIZED)
    runner = SimulationEngine(state, NARRATIVE, total_duration=0.2, narrative_weight=100.0)
    runner.set_speed(Speed.INSTANT)
    await runner.start()
    while runner.status is RunStatus.RUNNING:
        await asyncio.sleep(0.01)
    await runner.resolve_human("servicenow-incident-api", {"username": "svc"})
    while runner.status is RunStatus.RUNNING:
        await asyncio.sleep(0.01)

    emitted = {event.type for event in state.events.all()} | OUTSIDE_THE_NARRATIVE
    missing = emitted - subscribed()
    assert not missing, f"events.ts does not subscribe to {sorted(missing)}"
