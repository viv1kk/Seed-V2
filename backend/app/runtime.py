"""Process-wide singletons.

One `SystemState` per process, because the demo is a single run watched
by everyone connected to it (FR-L7). The bus is wired to the state once,
at import, and survives Reset: connections outlive runs.
"""

from app.bus import EventBus
from app.domain.state import SystemState

state = SystemState()
bus = EventBus()

state.subscribe(bus.publish)
