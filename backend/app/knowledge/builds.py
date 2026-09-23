"""How an approved solution is constructed, and what its tests are.

A build is a pipeline of components, each generated, unit-tested and
validated in turn, then tested together and checked against the evidence
the solution was approved on (FR-I2, §28, §52). For V1 the generation is
simulated. No source code is produced, so none is displayed (FR-I5). What
is real is the structure: which components a methodology needs, which
data feeds them, and which tests the result has to pass.

Two kinds of content meet here, and the split between them follows the
rest of the knowledge layer.

- **Authored:** each methodology's components and the tests that belong to
  a component's own logic. What a Ticket Anomaly engine must get right is
  knowledge about the methodology, like its required evidence, and
  `core.md` states it in the same terms.
- **Computed from the assessment:** the sources and datasets the pipeline
  ingests, one ingestion test per dataset, one normalization test per
  requirement, and one validation check per requirement. A requirement
  assessment found insufficient becomes a check that the conclusions
  resting on it are withheld (PR-074), not a check that they are right.
  Revise the evidence before approval and the build changes with it.

Test timings are simulated. They are derived from a checksum of the test's
name, so a run is identical every time (NFR-D4) and no figure is typed in
by hand. The implementation record says it is simulated, as assessments
do (FR-A10).
"""

import re
import zlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.environment.acme import SYSTEM_ORDER
from app.knowledge.feasibility import Standing, percent


class ComponentStatus(StrEnum):
    """FR-I2, in order. Every component passes through all five."""

    PENDING = "PENDING"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    VALIDATED = "VALIDATED"
    COMPLETE = "COMPLETE"


class Stage(StrEnum):
    """Where a component sits in the pipeline of §52."""

    INGESTION = "ingestion"
    NORMALIZATION = "normalization"
    ANALYSIS = "analysis"
    API = "api"
    DASHBOARD = "dashboard"


class Suite(StrEnum):
    UNIT = "unit"
    INTEGRATION = "integration"
    VALIDATION = "validation"


class TestStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class Component:
    id: str
    stage: Stage
    name: str
    #: What the activity stream says was generated, after "Generated" (§28).
    generated: str
    #: Unit tests of the component's own logic, authored.
    tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class Blueprint:
    components: tuple[Component, ...]
    integration: tuple[str, ...]


# -- Components every pipeline shares ----------------------------------


def _ingestion(*tests: str) -> Component:
    return Component(
        "ingestion",
        Stage.INGESTION,
        "Data ingestion",
        "data ingestion service",
        ("Retries a timed-out extract without duplicating records", *tests),
    )


def _api(*tests: str) -> Component:
    return Component(
        "api",
        Stage.API,
        "Analytics API",
        "analytical API",
        (
            "Every aggregate is reproducible from record-level data",
            "A filter narrows every view consistently",
            *tests,
        ),
    )


def _dashboard(*tests: str) -> Component:
    return Component(
        "dashboard",
        Stage.DASHBOARD,
        "Dashboard",
        "dashboard and drill-down views",
        (
            "Every chart drills down to the records behind it",
            "The evidence panel cites a dataset and field for each figure",
            *tests,
        ),
    )


REPRODUCIBLE = "Replaying the pipeline reproduces identical output"

BLUEPRINTS: dict[str, Blueprint] = {
    "ticket-anomaly-detection": Blueprint(
        components=(
            _ingestion(),
            Component(
                "normalization",
                Stage.NORMALIZATION,
                "Normalization",
                "schema validation and normalization pipeline",
                ("Rejects records that fail the declared schema",),
            ),
            Component(
                "features",
                Stage.ANALYSIS,
                "Feature pipeline",
                "feature pipeline for per-category baselines",
                (
                    "Baselines are computed per category and priority",
                    "Open tickets are excluded from the baseline population",
                ),
            ),
            Component(
                "engine",
                Stage.ANALYSIS,
                "Anomaly engine",
                "anomaly detection engine",
                (
                    "Scores match a fixed reference sample",
                    "False discovery rate is controlled across categories",
                ),
            ),
            _api(),
            _dashboard(),
        ),
        integration=(
            "The pipeline runs end to end on a 5% sample",
            "Each dashboard view is answered within 250 ms",
            REPRODUCIBLE,
        ),
    ),
    "license-optimization": Blueprint(
        components=(
            _ingestion(),
            Component(
                "normalization",
                Stage.NORMALIZATION,
                "Normalization",
                "identity and product normalization",
                ("Resolves one actor across ServiceNow, the LMS and the warehouse",),
            ),
            Component(
                "reconciliation",
                Stage.ANALYSIS,
                "Reconciliation",
                "entitlement reconciliation",
                (
                    "Entitlement, assignment and consumption reconcile per product",
                    "Leavers are separated as an access finding",
                ),
            ),
            Component(
                "cost",
                Stage.ANALYSIS,
                "Cost model",
                "recoverable cost model",
                (
                    "Recoverable cost is reported with its interval",
                    "Unpriced items are excluded, never priced at zero",
                ),
            ),
            _api(),
            _dashboard(),
        ),
        integration=(
            "The pipeline runs end to end on a 5% sample",
            "Reconciled totals match the entitlement count in the LMS",
            REPRODUCIBLE,
        ),
    ),
    "application-portfolio-rationalization": Blueprint(
        components=(
            _ingestion(),
            Component(
                "resolution",
                Stage.NORMALIZATION,
                "Entity resolution",
                "application entity resolution",
                (
                    "Matches one application across the registry, CMDB and warehouse",
                    "Registry-only applications are flagged, never merged",
                ),
            ),
            Component(
                "dependencies",
                Stage.ANALYSIS,
                "Dependency graph",
                "dependency graph builder",
                (
                    "Inbound and outbound dependencies are both counted",
                    "Cycles are reported rather than broken",
                ),
            ),
            Component(
                "disposition",
                Stage.ANALYSIS,
                "Disposition engine",
                "disposition rules engine",
                (
                    "Each application receives exactly one disposition",
                    "Uninstrumented applications are unresolved, never unused",
                ),
            ),
            _api(),
            _dashboard(),
        ),
        integration=(
            "The pipeline runs end to end on a 5% sample",
            "Portfolio membership differences are escalated, not resolved",
            REPRODUCIBLE,
        ),
    ),
}


# -- Timings -------------------------------------------------------------

#: Simulated duration ranges per suite, in milliseconds: a floor and a
#: spread. Unit tests are fast, integration tests run the pipeline.
TIMINGS: dict[Suite, tuple[int, int]] = {
    Suite.UNIT: (3, 57),
    Suite.INTEGRATION: (420, 1380),
    Suite.VALIDATION: (140, 660),
}


def duration_ms(key: str, suite: Suite) -> int:
    """A stable, simulated duration for one test.

    `zlib.crc32` rather than `hash`, which is salted per process and would
    make two runs disagree.
    """
    floor, spread = TIMINGS[suite]
    return floor + zlib.crc32(key.encode("utf-8")) % spread


# -- Planning ------------------------------------------------------------


def _datasets(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    """Every dataset the assessment located evidence in, in system order."""
    seen: dict[str, dict[str, Any]] = {}
    for requirement in assessment["requirements"]:
        for field in requirement["fields"]:
            seen.setdefault(
                field["dataset"],
                {"id": field["dataset"], "label": field["label"], "system": field["system"]},
            )
    rank = {system: index for index, system in enumerate(SYSTEM_ORDER)}
    return sorted(seen.values(), key=lambda d: (rank.get(d["system"], len(rank)), d["label"]))


def _sources(datasets: list[dict[str, Any]], environment: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {n["id"]: n["label"] for n in environment.get("nodes", []) if n["kind"] == "system"}
    systems = list(dict.fromkeys(d["system"] for d in datasets))
    return [{"id": system, "label": labels.get(system, system)} for system in systems]


def _validation(requirement: dict[str, Any]) -> tuple[str, str | None]:
    """One check per requirement, on what the evidence can support."""
    description = requirement["description"]
    weakest = requirement["weakest"]
    if requirement["standing"] in (Standing.INCOMPLETE, Standing.MISSING):
        note = (
            f"{weakest['label']}.{weakest['field']} is {percent(weakest['completeness'])}% "
            "complete, so conclusions resting on it are reported as insufficient (PR-074)."
            if weakest
            else "No profiled field carries it (PR-074)."
        )
        return f"Withholds conclusions resting on {description[0].lower()}{description[1:]}", note
    if requirement["standing"] is Standing.LIMITED:
        note = (
            f"Stated as a limitation: {weakest['label']}.{weakest['field']} is "
            f"{percent(weakest['completeness'])}% complete."
        )
        return f"States the limitation on {requirement['concept'].replace('-', ' ')}", note
    subject = re.split(r",| with | per ", description)[0].lower()
    return f"Findings on {subject} reproduce on a holdout sample", None


def plan(
    solution: dict[str, Any],
    assessment: dict[str, Any],
    environment: dict[str, Any],
    approval: dict[str, Any] | None,
) -> dict[str, Any]:
    """The implementation record for one approved solution.

    Everything the build will do is laid out before it starts, with every
    component PENDING and every test pending, so the pipeline and the test
    list are on screen in full from the first moment and fill in as the
    build proceeds.
    """
    blueprint = BLUEPRINTS[solution["methodologyId"]]
    datasets = _datasets(assessment)
    sid = solution["id"]

    tests: list[dict[str, Any]] = []

    def add(suite: Suite, component: str | None, name: str, note: str | None = None) -> None:
        tests.append(
            {
                "id": f"{sid}/{suite}/{len(tests) + 1}",
                "suite": suite,
                "component": component,
                "name": name,
                "note": note,
                "status": TestStatus.PENDING,
                "durationMs": duration_ms(f"{sid}/{name}", suite),
            }
        )

    for component in blueprint.components:
        if component.stage is Stage.INGESTION:
            for dataset in datasets:
                add(
                    Suite.UNIT,
                    component.id,
                    f"Reads {dataset['label']} through a parameterised extract",
                )
        if component.stage is Stage.NORMALIZATION:
            for requirement in assessment["requirements"]:
                count = len(requirement["fields"])
                add(
                    Suite.UNIT,
                    component.id,
                    f"Maps {requirement['concept'].replace('-', ' ')} from "
                    f"{count} field{'' if count == 1 else 's'}",
                )
        for name in component.tests:
            add(Suite.UNIT, component.id, name)

    for name in blueprint.integration:
        add(Suite.INTEGRATION, None, name)

    analysis = [c.id for c in blueprint.components if c.stage is Stage.ANALYSIS][-1]
    for requirement in assessment["requirements"]:
        name, note = _validation(requirement)
        add(Suite.VALIDATION, analysis, name, note)

    record = {
        "id": sid,
        "solutionId": sid,
        "name": solution["name"],
        "status": "PENDING",
        "approval": (
            {"id": approval["id"], "rule": approval["rule"], "decidedAt": approval["decidedAt"]}
            if approval
            else None
        ),
        "sources": _sources(datasets, environment),
        "datasets": datasets,
        "components": [
            {
                "id": c.id,
                "stage": c.stage,
                "name": c.name,
                "generated": c.generated,
                "status": ComponentStatus.PENDING,
            }
            for c in blueprint.components
        ],
        "tests": tests,
        "summary": {},
        "simulated": True,
    }
    summarise(record)
    return record


# -- Progress ------------------------------------------------------------


def set_status(record: dict[str, Any], component_id: str, status: ComponentStatus) -> None:
    for component in record["components"]:
        if component["id"] == component_id:
            component["status"] = status
            return
    raise KeyError(component_id)


def pass_tests(
    record: dict[str, Any], *, suite: Suite, component: str | None = None
) -> list[dict[str, Any]]:
    """Mark a group of tests passed, and return them.

    Every test in the narrative passes. The status is still carried per
    test rather than assumed, so the result view shows what ran and how it
    ended rather than a summary that could not have said otherwise (FR-I4).
    """
    ran = [
        test
        for test in record["tests"]
        if test["suite"] == suite
        and (component is None or test["component"] == component)
        and test["status"] == TestStatus.PENDING
    ]
    for test in ran:
        test["status"] = TestStatus.PASSED
    summarise(record)
    return ran


def summarise(record: dict[str, Any]) -> dict[str, Any]:
    tests = record["tests"]
    finished = [t for t in tests if t["status"] != TestStatus.PENDING]
    record["summary"] = {
        "total": len(tests),
        "passed": sum(1 for t in tests if t["status"] == TestStatus.PASSED),
        "failed": sum(1 for t in tests if t["status"] == TestStatus.FAILED),
        "durationMs": sum(t["durationMs"] for t in finished),
    }
    return record["summary"]


def seconds(ms: int) -> str:
    """1840 as '1.84 s', 620 as '0.62 s'."""
    return f"{ms / 1000:.2f} s"
