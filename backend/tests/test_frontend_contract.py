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
from app.knowledge.solutions import close, run
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE
from narrative import run_to_end

EVENTS_STORE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "stores" / "events.ts"

#: Emitted outside a narrative run: by the seed API, by a failing run, and
#: by an operator revising evidence.
OUTSIDE_THE_NARRATIVE = {"seed.loaded", "run.failed", "assessment.evidence.revised"}


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
    # One rejection, so both kinds of decision are emitted.
    await run_to_end(runner, decisions={"license-optimization": "reject"})
    # And a solution run and returned from, which the API does after the run.
    run(state, "ticket-anomaly-detection")
    close(state, "ticket-anomaly-detection")

    emitted = {event.type for event in state.events.all()} | OUTSIDE_THE_NARRATIVE
    missing = emitted - subscribed()
    assert not missing, f"events.ts does not subscribe to {sorted(missing)}"


# -- The dashboard renderer is generic (D-1, FR-EV4) --------------------

FRONTEND = EVENTS_STORE.parents[1]

RENDERER = [
    FRONTEND / "views" / "DashboardView.vue",
    FRONTEND / "stores" / "dashboard.ts",
    FRONTEND / "design" / "format.ts",
    *sorted((FRONTEND / "charts").iterdir()),
    *sorted((FRONTEND / "components" / "dashboard").iterdir()),
]

#: Words that would mean the renderer knows which dashboard it is drawing.
SPECIFIC = (
    "ticket-anomaly",
    "license-optimization",
    "portfolio-rationalization",
    "ticket",
    "licen",
    "cluster",
    "pattern",
    "reassign",
    "seat",
    "disposition",
    "servicenow",
)


def test_the_dashboard_renderer_names_no_methodology() -> None:
    """M10's exit: the dashboard that works contains no methodology-specific
    UI code. Ticket Anomaly Detection is a descriptor, not a component."""
    assert len(RENDERER) >= 8
    for path in RENDERER:
        text = path.read_text(encoding="utf-8").lower()
        found = [word for word in SPECIFIC if word in text]
        assert not found, f"{path.name} mentions {found}"
