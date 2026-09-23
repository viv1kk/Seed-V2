"""The solution lifecycle (FR-AP2).

A solution is what a feasible methodology becomes once assessment proposes
it. Its states are declared as a table, like the system lifecycle, so an
illegal move raises instead of mutating (FR-L1, FR-L3): approving a
solution twice, or building one nobody approved, is refused here rather
than trusted not to happen (FR-AP1).

REJECTED is terminal. A rejection is a decision, and a decision that could
be quietly reversed would not be a record of one.
"""

from enum import StrEnum


class SolutionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BUILDING = "BUILDING"
    READY = "READY"
    RUNNING = "RUNNING"


SOLUTION_TRANSITIONS: dict[SolutionStatus, frozenset[SolutionStatus]] = {
    SolutionStatus.PROPOSED: frozenset({SolutionStatus.AWAITING_APPROVAL}),
    SolutionStatus.AWAITING_APPROVAL: frozenset(
        {SolutionStatus.APPROVED, SolutionStatus.REJECTED}
    ),
    SolutionStatus.APPROVED: frozenset({SolutionStatus.BUILDING}),
    SolutionStatus.REJECTED: frozenset(),
    SolutionStatus.BUILDING: frozenset({SolutionStatus.READY}),
    # Running and returning, repeatedly: completion is per solution (FR-L8).
    SolutionStatus.READY: frozenset({SolutionStatus.RUNNING}),
    SolutionStatus.RUNNING: frozenset({SolutionStatus.READY}),
}


class IllegalSolutionTransition(Exception):
    def __init__(self, solution: str, source: SolutionStatus, target: SolutionStatus) -> None:
        allowed = sorted(SOLUTION_TRANSITIONS[source])
        super().__init__(
            f"{solution} cannot move from {source} to {target}. "
            f"Allowed from {source}: {', '.join(allowed) or 'nothing'}."
        )


def assert_solution_transition(
    solution: str, source: SolutionStatus, target: SolutionStatus
) -> None:
    if target not in SOLUTION_TRANSITIONS[source]:
        raise IllegalSolutionTransition(solution, source, target)
