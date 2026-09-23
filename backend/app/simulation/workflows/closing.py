"""Closing the seeding phase: IMPLEMENTATION_COMPLETE to READY_TO_RUN (D-16).

A built system is not yet a running one. Seeding ends with a clean-up, and
a person confirms it first (FR-C1, FR-C2). This is the "deployment
confirmation" of §18, and the one place the fifth request kind is used.

Once confirmed, closing does four things, each a capability request the
protection engine decides and records (FR-C3, FR-C4):

1. It consolidates the seeding phase's working notes into one seeding
   record in System State (PR-090).
2. It releases the system's own scratch space (PR-091). That is a
   deletion, and the rule set tells the system's scratch from the
   client's data. Deleting from a source system stays refused (PR-051).
3. It promotes each built Agent Component's interface from its build
   version to its release version (PR-093), on the strength of the
   approval already recorded under PR-053. Policy here reads history.
4. It retires the tools that built Agent One VW and revokes their grants
   (PR-095). What built the system is not needed to run it.

Then the seed is consumed: its three layers are carried by what grew from
them, so nothing of the seeding phase needs to remain. The seed files
themselves are never touched (FR-S6). All of this is simulated. None of
it touches a seed file, a source system, the local filesystem or the
network (FR-C5, NFR-D2).

The beats weigh six units in all: one opening, four steps, the seed
consumed, and the hand-over. See `config.NARRATIVE_WEIGHT`.
"""

from typing import Any

from app.domain.events import Category
from app.domain.lifecycle import LifecycleState
from app.domain.state import BlockedOn, RequestKind, RequestOption, SystemState
from app.knowledge.solutions import approval_of
from app.protection.capabilities import BUILD_TOOLS
from app.protection.engine import authorize
from app.protection.rules import Action, ActionRequest
from app.simulation.beats import AwaitHuman, Beat, Workflow
from app.simulation.workflows.gate import proceed

CLOSE_REQUEST = "close-seeding"

#: The action FR-C1 names, as the confirmation's one option.
CLOSE_LABEL = "Run — clean up and close seeding"

STEPS = 4

NUMBERS = dict(
    enumerate(("No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"))
)


def _count(n: int, noun: str) -> str:
    return f"{NUMBERS.get(n, str(n))} {noun}{'' if n == 1 else 's'}"


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _notes(state: SystemState) -> dict[str, int]:
    """The seeding phase's working notes, counted from the log by phase of work."""
    counts = {"discovery": 0, "assessment": 0, "build": 0}
    for event in state.events.all():
        head = event.type.split(".", 1)[0]
        if head == "discovery":
            counts["discovery"] += 1
        elif head in ("assessment", "solution", "approval"):
            counts["assessment"] += 1
        elif head == "implementation":
            counts["build"] += 1
    return counts


def _step(
    state: SystemState, type: str, step: str, index: int, message: str, **payload: Any
) -> None:
    state.record(
        type=type,
        category=Category.ANALYSIS,
        message=message,
        payload={"step": step, "index": index, "of": STEPS, **payload},
    )


def closing(state: SystemState) -> Workflow:
    ready = [s for s in state.solutions if s["status"] == "READY"]

    # FR-C1, FR-C2: a person confirms, told what will happen and why.
    yield AwaitHuman(
        request=BlockedOn(
            kind=RequestKind.CONFIRMATION,
            request_id=CLOSE_REQUEST,
            prompt=(
                "Seeding is complete. Close it: clean up after the build, retire the tools that "
                "built Agent One VW, and hand over to Life."
            ),
            access=(
                "Consolidate the working notes, release scratch space, promote interfaces to "
                "release, and retire the build tools"
            ),
            reason=(
                "Agent One VW now carries what the Seed held. The tools that built it are not "
                "needed to run it, and moving from building to running is a person's call."
            ),
            options=[
                RequestOption(
                    value="close",
                    label=CLOSE_LABEL,
                    note="Four clean-up steps, each decided by the protection engine.",
                )
            ],
        )
    )

    state.transition(LifecycleState.CLOSING_SEEDING)
    state.record(
        type="seeding.closing.started",
        category=Category.DECISION,
        message=(
            "Closing the seeding phase. Four clean-up steps, each decided by the protection "
            "engine; the seed files are not touched."
        ),
        payload={"steps": STEPS},
    )
    yield Beat(weight=0.6, label="closing begins")

    # 1. The working notes, consolidated into one seeding record.
    notes = _notes(state)
    total = sum(notes.values())
    proceed(
        authorize(
            state,
            ActionRequest(
                action=Action.CONSOLIDATE_RECORDS,
                resource=(
                    f"{notes['discovery']} discovery notes, {notes['assessment']} assessment "
                    f"notes and {notes['build']} build records"
                ),
                purpose="Keep one seeding record in place of the phase's working notes.",
                system_owned=True,
            ),
        )
    )
    state.closing["record"] = {**notes, "total": total, "at": state.events.last_sequence + 1}
    _step(
        state,
        "seeding.notes.consolidated",
        "notes",
        1,
        (
            f"Working notes consolidated: {total} entries from discovery, assessment and the "
            "build are one seeding record now. Every entry is kept."
        ),
        record=dict(state.closing["record"]),
    )
    yield Beat(weight=1, label="notes consolidated")

    # 2. Scratch space, released. System-owned storage, not client data.
    staged = sum(len(build["datasets"]) for build in state.implementations)
    proceed(
        authorize(
            state,
            ActionRequest(
                action=Action.CLEAR_SCRATCH,
                resource=(
                    f"the analytical workspace's scratch: staged copies of "
                    f"{_count(staged, 'dataset').lower()} and intermediate build results"
                ),
                purpose="Release the temporary storage the build used.",
                system_owned=True,
            ),
        )
    )
    state.closing["scratch"] = {"datasets": staged, "released": True}
    _step(
        state,
        "seeding.scratch.cleared",
        "scratch",
        2,
        (
            f"Scratch space purged: staged copies of {_count(staged, 'dataset').lower()} and "
            "every intermediate result released. No source system was touched."
        ),
        datasets=staged,
    )
    yield Beat(weight=1, label="scratch cleared")

    # 3. Interfaces promoted, each on its recorded approval.
    promoted: list[dict[str, Any]] = []
    for solution in ready:
        decision = approval_of(state, solution["id"])
        proceed(
            authorize(
                state,
                ActionRequest(
                    action=Action.PROMOTE_INTERFACE,
                    resource=f"{solution['name']} interface, build version to release version",
                    purpose="Complete the deployment the approval authorised.",
                    deployment_approved=decision is not None,
                ),
            )
        )
        promoted.append(
            {"id": solution["id"], "approvedAt": decision["decidedAt"] if decision else None}
        )
    state.closing["promoted"] = promoted
    message = (
        f"Interfaces promoted to release: {_names([s['name'] for s in ready])}, each under the "
        "approval recorded for it (PR-053)."
        if ready
        else "No interface to promote: no Agent Component was approved."
    )
    _step(state, "seeding.interfaces.promoted", "interfaces", 3, message, promoted=promoted)
    yield Beat(weight=1, label="interfaces promoted")

    # 4. The build tools, retired and their grants revoked.
    for tool in BUILD_TOOLS:
        proceed(
            authorize(
                state,
                ActionRequest(
                    action=Action.RETIRE_TOOL,
                    resource=f"{tool}, and its build-time grant",
                    purpose="The build is complete; Agent One VW runs without it.",
                    system_owned=True,
                    build_complete=all(i["status"] == "COMPLETE" for i in state.implementations),
                ),
            )
        )
    state.closing["retired"] = list(BUILD_TOOLS)
    _step(
        state,
        "seeding.tools.retired",
        "tools",
        4,
        (
            f"Build tools retired: the {_names(list(BUILD_TOOLS))} are discarded and their "
            "grants revoked. Agent One VW stands without them."
        ),
        tools=list(BUILD_TOOLS),
    )
    yield Beat(weight=1, label="tools retired")

    # The seed, consumed: what it held now lives in what grew from it.
    layers = len((state.seed or {}).get("layers", [])) or 3
    state.closing["consumed"] = True
    state.record(
        type="seeding.consumed",
        category=Category.SUCCESS,
        message=(
            f"The Seed is consumed. Its {NUMBERS.get(layers, str(layers)).lower()} layers are "
            f"carried by {NUMBERS.get(len(ready), str(len(ready))).lower()} Agent "
            f"Component{'' if len(ready) == 1 else 's'} of Agent One VW, which "
            "sustains itself from here. The seed files are unchanged."
        ),
        payload={"layers": layers, "components": [s["id"] for s in ready]},
    )
    yield Beat(weight=0.4, label="seed consumed")

    state.transition(LifecycleState.READY_TO_RUN)
    state.record(
        type="deployment.ready",
        category=Category.SUCCESS,
        message=(
            f"System ready. {_count(len(ready), 'Agent Component')} ready to run."
            if ready
            else "System ready. No Agent Component was approved, so there is nothing to run."
        ),
        payload={"ready": [s["id"] for s in ready]},
    )
    yield Beat(weight=1, label="system ready")
