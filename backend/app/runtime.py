"""Process-wide singletons.

One `SystemState` per process, because the demo is a single run watched
by everyone connected to it (FR-L7). The bus is wired to the state once,
at import, and survives Reset: connections outlive runs.

`source` is annotated as `EventSource`, not as `SimulationEngine`. That
annotation is the seam of NFR-A1 in the one place it can be enforced:
every caller sees the protocol, so substituting a real agent runtime is
an edit here and nowhere else.
"""

from app.bus import EventBus
from app.config import NARRATIVE_WEIGHT, TOTAL_DURATION_SECONDS
from app.domain.state import SystemState
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import EventSource
from app.simulation.workflows.registry import NARRATIVE

state = SystemState()
bus = EventBus()

state.subscribe(bus.publish)

source: EventSource = SimulationEngine(
    state,
    NARRATIVE,
    total_duration=TOTAL_DURATION_SECONDS,
    narrative_weight=NARRATIVE_WEIGHT,
)
