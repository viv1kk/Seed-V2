"""How an event is presented, and why that is a decision worth naming.

§61 draws a distinction the interface must not lose. A technical error, a
human decision and an insufficiency are three different things, and
FR-H4 forbids conflating them:

- A **technical error** is a fault. Something did not work.
- A **human decision** is a legitimate choice the system declines to make
  alone. Nothing is broken.
- An **insufficiency** is the system refusing to conclude on the evidence
  it has. Nothing is broken and nothing is being asked.

Rendering all three in warning orange would say that a request for
credentials is a malfunction and that a withheld conclusion is a failure.
Both are false, and both are the specific misreading a sceptical viewer
takes away.

The classification is derived from the event rather than carried on it,
because FR-E3 fixes the event's fields and a presentation hint is not a
fact about the system. It is derived by *convention on the type name*, so
a milestone that adds events falls into the right bucket by naming them
consistently rather than by editing a list here.

The frontend mirrors this module. It is the authority because this is
where a test can reach it: D-7 rules three Python suites and no frontend
runner, so the convention is asserted here against every type the
narrative actually emits.
"""

from enum import StrEnum

from app.domain.events import Category, Severity


class Presentation(StrEnum):
    """The four ways the interface treats an event."""

    ACTIVITY = "activity"
    ERROR = "error"
    DECISION = "decision"
    INSUFFICIENT = "insufficient"


#: A fault. Note that `.denied` is deliberately absent: a policy denial is
#: the protection layer working, not a failure, and it is categorised
#: POLICY rather than presented as an error (FR-P4).
ERROR_SUFFIXES: tuple[str, ...] = (".failed", ".timeout", ".error", ".unreachable")

#: The system declining to conclude. Distinct from a fault, and distinct
#: from a question: nothing is being asked of anyone.
INSUFFICIENT_SUFFIXES: tuple[str, ...] = (".insufficient", ".unresolved", ".withheld")


def presentation_of(*, type: str, category: Category, severity: Severity) -> Presentation:
    """Classify one event.

    Insufficiency is tested first. It is the case most easily swallowed by
    the others: it often carries a WARNING severity in spirit, and saying
    so in the interface would turn a careful refusal into a malfunction.
    """
    if type.endswith(INSUFFICIENT_SUFFIXES):
        return Presentation.INSUFFICIENT

    if type.endswith(ERROR_SUFFIXES) or severity is Severity.ERROR:
        return Presentation.ERROR

    if category is Category.HUMAN_INPUT:
        return Presentation.DECISION

    return Presentation.ACTIVITY
