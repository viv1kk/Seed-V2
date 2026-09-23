"""The narrative, as an ordered list of stages.

The runner walks this. Adding a stage is an entry here, which is what
keeps M3 to M8 additive rather than structural.
"""

from app.simulation.engine import WorkflowSpec
from app.simulation.workflows import assessment, discovery, implementation

NARRATIVE: tuple[WorkflowSpec, ...] = (
    WorkflowSpec(name="discovery", factory=discovery.discovery),
    WorkflowSpec(name="assessment", factory=assessment.assessment),
    WorkflowSpec(name="implementation", factory=implementation.implementation),
)
