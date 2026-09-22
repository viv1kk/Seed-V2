"""Beats --- the units a workflow is paced in.

A workflow is a generator. It does its work, then yields a `Beat` to say
"let that land before the next thing happens", or an `AwaitHuman` to
park until a person answers. Nothing about timing appears in the
workflow itself, which is what makes the whole narrative retimeable from
one number (D-8).

Weights are relative, never seconds. A beat worth twice another takes
twice as long at any total duration, so raising or lowering the target
at rehearsal is a single edit rather than a hundred (OQ-7).
"""

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from app.domain.state import BlockedOn


@dataclass(frozen=True)
class Beat:
    """A pause, expressed as a share of the narrative rather than a time.

    `floor` protects a beat that carries meaning from being compressed
    into invisibility when the total duration is lowered. The credential
    pause and the timeout recovery are the cases that need it: both are
    scripted to be noticed (FR-D7, FR-D8), and both disappear if they
    scale down with everything else.

    The floor is a minimum on the scaled duration, not an override of
    the speed control. An operator who asks for 2x gets 2x.
    """

    weight: float
    floor: float = 0.0
    label: str | None = None

    def seconds(self, scale: float) -> float:
        """The unsped duration of this beat at `scale` seconds per unit."""
        return max(self.weight * scale, self.floor)


@dataclass(frozen=True)
class AwaitHuman:
    """Park the workflow until a person answers.

    The generator suspends at the `yield`, and the submitted values are
    sent back into it there, so the workflow resumes from its exact
    point of suspension rather than from a checkpoint near it (FR-H7).
    """

    request: BlockedOn


#: What a workflow yields, and what it receives back when it parks.
Workflow = Generator[Beat | AwaitHuman, dict[str, Any] | None, None]
