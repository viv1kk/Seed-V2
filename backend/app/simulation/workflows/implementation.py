"""Implementation: AWAITING_APPROVAL to IMPLEMENTATION_COMPLETE.

Each approved solution is built in turn as a pipeline of components
(§27, §52). Components move through a wave: while one is generated, the
one before it is under unit test and the one before that is validated,
so every component passes through all five states of FR-I2 and the
pipeline visibly advances rather than flipping to done. Then the unit
and integration suites report, the output is validated against the
evidence the solution was approved on, and the solution is Ready (FR-I6).
Closing the seeding phase follows, in its own workflow (D-16).

The activity stream reports this as §28 does, one "Generated ..." per
component, and nothing that is not happening is narrated (FR-E9). No
source code is produced or shown (FR-I5).

Two actions pass the gate for each build. Staging the retrieved data in
the analytical workspace is decided under PR-040, and invoking the test
runner under PR-060, whose `tool_granted` fact is computed from the
enumerated grant rather than asserted. Deployment is not asked again. It
was escalated once under PR-053 at the end of assessment, and each
solution's approval is the answer to that escalation. Asking a second
time would either park the run on a question already answered, or need a
fact that says "approved" and lets a caller claim it. The solution's
readiness cites the recorded decision instead.

Only approved solutions are built. A rejected solution is named once and
left alone: rejection is final (FR-AP2).

The beats: one to open, six per solution, one to close. NARRATIVE_WEIGHT
describes the scripted narrative, in which all three solutions are
approved (§83.6). A run that approves fewer is shorter by the builds it
does not do, which is the honest reading of a total-duration budget.
"""

import copy
from typing import Any

from app.domain.events import Category
from app.domain.lifecycle import LifecycleState
from app.domain.state import SystemState
from app.knowledge import builds
from app.knowledge.builds import ComponentStatus, Suite
from app.knowledge.solutions import (
    approval_of,
    approved,
    assessment,
    begin_build,
    mark_ready,
)
from app.protection.capabilities import granted
from app.protection.engine import authorize
from app.protection.rules import Action, ActionRequest
from app.simulation.beats import Beat, Workflow
from app.simulation.workflows.gate import proceed

TEST_RUNNER = "test-runner"

NUMBERS = dict(
    enumerate(("No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"))
)


def _count(n: int, noun: str) -> str:
    return f"{NUMBERS.get(n, str(n))} {noun}{'' if n == 1 else 's'}"


def _names(records: list[dict[str, Any]], key: str = "name") -> str:
    names = [r[key] for r in records]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def implementation(state: SystemState) -> Workflow:
    state.transition(LifecycleState.IMPLEMENTING)

    building = approved(state)
    rejected = [s for s in state.solutions if s["status"] == "REJECTED"]

    # Every build is planned before any starts, so each pipeline is on
    # screen whole, every component PENDING, before the first one moves.
    for solution in building:
        evidence = assessment(state, solution["assessmentId"]) or {"requirements": []}
        decision = approval_of(state, solution["id"])
        state.implementations.append(
            builds.plan(solution, evidence, state.environment, decision)
        )

    message = f"Implementation begins. {_count(len(building), 'approved Agent Component')} to build"
    message += f": {_names(building)}." if building else "."
    if rejected:
        verb = "was" if len(rejected) == 1 else "were"
        message += f" {_names(rejected)} {verb} rejected and will not be built."
    state.record(
        type="implementation.started",
        category=Category.ANALYSIS,
        message=message,
        payload={"implementations": copy.deepcopy(state.implementations)},
    )
    yield Beat(weight=1, label="implementation begins")

    for solution, build in zip(building, state.implementations, strict=True):
        yield from _build(state, solution, build)

    ready = [s for s in state.solutions if s["status"] == "READY"]
    state.record(
        type="implementation.completed",
        category=Category.SUCCESS,
        message=(
            f"Implementation complete. {_count(len(ready), 'Agent Component')} built, tested and "
            "validated against the evidence each was approved on."
        ),
        payload={"ready": [s["id"] for s in ready]},
    )
    state.transition(LifecycleState.IMPLEMENTATION_COMPLETE)
    yield Beat(weight=1, label="implementation complete")


def _emit(
    state: SystemState,
    type: str,
    message: str,
    build: dict[str, Any],
    solution: dict[str, Any] | None = None,
    category: Category = Category.ANALYSIS,
) -> None:
    """Record a build event carrying full copies of what it changed.

    Copies, because the record keeps changing after the event is written
    and an event must say what was true when it was recorded (FR-E7).
    """
    payload: dict[str, Any] = {"implementations": [copy.deepcopy(build)]}
    if solution is not None:
        payload["solutions"] = [dict(solution)]
    state.record(type=type, category=category, message=message, payload=payload)


def _build(state: SystemState, solution: dict[str, Any], build: dict[str, Any]) -> Workflow:
    """One solution, from APPROVED to READY."""
    decision = build["approval"]
    datasets = build["datasets"]
    sources = build["sources"]

    proceed(
        authorize(
            state,
            ActionRequest(
                action=Action.MOVE_DATA,
                resource=(
                    f"{_count(len(datasets), 'dataset').lower()} for {solution['name']}, "
                    "into the analytical workspace"
                ),
                source=", ".join(s["label"] for s in sources) or None,
                purpose="Stage the retrieved data the pipeline is built over.",
                to_workspace=True,
            ),
        )
    )
    proceed(
        authorize(
            state,
            ActionRequest(
                action=Action.INVOKE_TOOL,
                resource=f"{TEST_RUNNER} for {solution['name']}",
                purpose="Run the unit, integration and validation suites.",
                tool_granted=granted(TEST_RUNNER),
            ),
        )
    )

    begin_build(solution)
    build["status"] = "BUILDING"
    components = build["components"]
    builds.set_status(build, components[0]["id"], ComponentStatus.BUILDING)
    systems = _names(sources, "label") if sources else "no source"
    _emit(
        state,
        "implementation.build.started",
        (
            f"Building {solution['name']}: {_count(len(components), 'component').lower()} over "
            f"{_count(len(datasets), 'dataset').lower()} from {systems}."
        ),
        build,
        solution,
    )
    yield Beat(weight=0.9, label=f"build {solution['id']}")

    # The wave. Generating component k puts it under test, starts k + 1,
    # and validates k - 1, whose unit tests have passed.
    for k, component in enumerate(components):
        builds.set_status(build, component["id"], ComponentStatus.TESTING)
        if k + 1 < len(components):
            builds.set_status(build, components[k + 1]["id"], ComponentStatus.BUILDING)
        if k > 0:
            _validate(build, components[k - 1]["id"])
        _emit(state, "implementation.component.built", f"Generated {component['generated']}.", build)
        yield Beat(weight=0.55, label=f"generated {component['id']}")

    _validate(build, components[-1]["id"])
    unit = [t for t in build["tests"] if t["suite"] == Suite.UNIT]
    integration = builds.pass_tests(build, suite=Suite.INTEGRATION)
    ran = unit + integration
    passed = sum(1 for t in ran if t["status"] == "passed")
    _emit(
        state,
        "implementation.tests.passed",
        (
            f"Unit and integration tests: {passed} of {len(ran)} passed in "
            f"{builds.seconds(sum(t['durationMs'] for t in ran))}."
        ),
        build,
        category=Category.VALIDATION,
    )
    yield Beat(weight=0.9, label=f"tested {solution['id']}")

    checks = builds.pass_tests(build, suite=Suite.VALIDATION)
    withheld = sum(1 for t in checks if t["name"].startswith("Withholds"))
    for component in components:
        builds.set_status(build, component["id"], ComponentStatus.COMPLETE)
    build["status"] = "COMPLETE"
    mark_ready(solution)

    message = (
        f"{solution['name']} validated against the evidence it was approved on: "
        f"{len(checks)} of {len(checks)} checks passed"
    )
    message += (
        f", {_count(withheld, 'conclusion').lower()} withheld as insufficient."
        if withheld
        else "."
    )
    if decision:
        message += (
            f" Ready to run, under the approval recorded at #{decision['decidedAt']} "
            f"({decision['rule']})."
        )
    else:
        message += " Ready to run."
    _emit(state, "solution.ready", message, build, solution, category=Category.SUCCESS)
    yield Beat(weight=0.9, label=f"ready {solution['id']}")


def _validate(build: dict[str, Any], component_id: str) -> None:
    builds.pass_tests(build, suite=Suite.UNIT, component=component_id)
    builds.set_status(build, component_id, ComponentStatus.VALIDATED)
