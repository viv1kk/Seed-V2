"""The narrative, as an ordered list of stages.

The runner walks this. Adding a stage is an entry here, which is what
keeps M3 to M8 additive rather than structural.
"""

from app.simulation.engine import WorkflowSpec
from app.simulation.workflows import assessment, closing, discovery, implementation, life

NARRATIVE: tuple[WorkflowSpec, ...] = (
    WorkflowSpec(name="discovery", factory=discovery.discovery),
    WorkflowSpec(name="assessment", factory=assessment.assessment),
    WorkflowSpec(name="implementation", factory=implementation.implementation),
    WorkflowSpec(name="closing", factory=closing.closing),
)

#: Life, after the narrative (D-17). Kept out of NARRATIVE: it runs after
#: the 270-second story and carries no narrative weight, so the narrative
#: is what it was, and the running app plays the two in order.
LIFE: tuple[WorkflowSpec, ...] = (WorkflowSpec(name="life", factory=life.life),)
