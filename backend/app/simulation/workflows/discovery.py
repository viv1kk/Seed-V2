"""Discovery: INITIALIZED to DISCOVERY_COMPLETE, over the ACME environment.

The walk follows §68: ServiceNow is detected, its reachability tested, a
credential requested and supplied, and then SAP, SQL Server and the rest
are found. The graph grows as it goes (FR-D3), one grouped burst per
system rather than one node at a time, because thirty separate
appearances do not fit a readable pace inside OQ-7's budget.

Three rules shape the code below.

*Every capability passes the gate, and the decision is acted on.* Each
authentication, enumeration, credential use and read is put to the policy
engine with the facts its rules require (FR-P2), and the facts about a
dataset come from that dataset's definition in `acme.py`, not from the
call site. The workflow then does what the decision says. A refusal it
expects --- the security log --- is recorded as a dataset left out. A
refusal it does not expect stops the run, because proceeding without an
ALLOW is exactly what PR-082 forbids, and a run that quietly carried on
would make the gate decorative.

*The graph is System State.* Every change goes through `Environment`,
which carries it on the next event. The screen is derived from the
snapshot and those events, never from a model of its own (FR-L5).

*Nothing is counted by hand.* Each message that states a number takes it
from the definition or from the constructed graph, and the completion
summary is computed from the graph alone (FR-D9).

Two interruptions and no more (§83.6): the credential pause and the one
timeout (FR-D7, FR-D8). Both carry floors, because a pause or a recovery
compressed into invisibility is one the audience never saw. The weights
here sum to 54 of the narrative's 100, a little over half, since
discovery is where perceived activity lives.
"""

from collections.abc import Iterable

from app.domain.events import Category, Severity
from app.domain.lifecycle import LifecycleState
from app.domain.state import BlockedOn, RequestKind, SystemState
from app.environment.acme import ACME, CLIENT, ENUMERATION, SYSTEM_ORDER
from app.environment.model import Environment, NodeKind, NodeSpec, NodeStatus, Origin, summarise
from app.protection.engine import Decision, authorize
from app.protection.rules import Action, ActionRequest, Effect, Identity
from app.simulation.beats import AwaitHuman, Beat, Workflow

CREDENTIAL_REQUEST = "servicenow-incident-api"


class PolicyRefused(RuntimeError):
    """An action the narrative needed was not allowed."""


def _proceed(decision: Decision) -> Decision:
    """Continue only on an ALLOW (PR-082)."""
    if decision.effect is not Effect.ALLOW:
        raise PolicyRefused(
            f"{decision.action.label} on {decision.resource} was {decision.effect} "
            f"under {decision.rule}. Discovery does not proceed without an ALLOW."
        )
    return decision


def _label(system_id: str) -> str:
    return ACME.by_id[system_id].label


def _authenticate(state: SystemState, system_id: str) -> Decision:
    system = _label(system_id)
    return authorize(
        state,
        ActionRequest(
            action=Action.AUTHENTICATE,
            resource=f"{system} read-only service identity",
            source=system,
            identity=Identity.SERVICE_READ_ONLY,
            source_declared=True,
            after_rejection=False,
            attempt=1,
            in_scope=True,
        ),
    )


def _enumerate(state: SystemState, system_id: str) -> Decision:
    system = _label(system_id)
    return authorize(
        state,
        ActionRequest(
            action=Action.ENUMERATE,
            resource=f"{system} {ENUMERATION[system_id]}",
            source=system,
            source_declared=True,
            in_scope=True,
        ),
    )


def _read(
    state: SystemState,
    system_id: str,
    datasets: Iterable[NodeSpec],
    resource: str,
    purpose: str,
) -> Decision:
    """Ask to read datasets, stating the facts their definitions carry.

    A batch is mapped only if every dataset in it is, and touches a
    security table if any does, so batching can never make a request
    look more benign than its most sensitive member.
    """
    specs = list(datasets)
    system = _label(system_id)
    return authorize(
        state,
        ActionRequest(
            action=Action.READ,
            resource=resource,
            source=system,
            purpose=purpose,
            source_declared=True,
            dataset_mapped=all(spec.mapped for spec in specs),
            unmapped_personal_fields=False,
            security_table=any(spec.security_table for spec in specs),
            within_window=True,
            parameterised=True,
            in_scope=True,
        ),
    )


def _surfaces(system_id: str) -> tuple[NodeSpec, ...]:
    return tuple(node for node in ACME.children(system_id) if node.kind is not NodeKind.DATASET)


def _datasets(parent_id: str) -> tuple[NodeSpec, ...]:
    return tuple(node for node in ACME.children(parent_id) if node.kind is NodeKind.DATASET)


def _profile(state: SystemState, env: Environment, system_id: str) -> int:
    """Read and profile every mapped dataset on a system, one surface at a time.

    One request per surface rather than per table: the facts are the same
    for every table behind a surface, and a stream that lists each one
    separately is a longer stream saying nothing more (FR-E8).
    """
    profiled = 0
    for surface in _surfaces(system_id):
        mapped = [spec for spec in _datasets(surface.id) if spec.mapped and env.has(spec.id)]
        if not mapped:
            continue
        noun = "dataset" if len(mapped) == 1 else "datasets"
        _proceed(
            _read(
                state,
                system_id,
                mapped,
                resource=f"{_label(system_id)} {surface.label}: {len(mapped)} mapped {noun}",
                purpose="Sample each mapped dataset to profile field completeness.",
            )
        )
        for spec in mapped:
            env.profile(spec.id)
        profiled += len(mapped)
    return profiled


def _connect(env: Environment, system_id: str) -> None:
    env.set_status(NodeStatus.CONNECTED, system_id, *(s.id for s in _surfaces(system_id)))


def _found_and_enumerated(
    state: SystemState, env: Environment, system_id: str, detail: str
) -> Workflow:
    """A system reached without incident: detected, authenticated, enumerated.

    One event for all three, because nothing happens between them that a
    viewer needs to watch, and one more when its datasets are profiled.
    """
    system = _label(system_id)
    surfaces = _surfaces(system_id)

    env.reveal(system_id, *(s.id for s in surfaces))
    _proceed(_authenticate(state, system_id))
    _proceed(_enumerate(state, system_id))
    env.set_status(NodeStatus.VALIDATED, system_id, *(s.id for s in surfaces))
    found = [d for s in surfaces for d in _datasets(s.id)]
    env.reveal(*(d.id for d in found))
    env.record(
        type="discovery.system.found",
        category=Category.DISCOVERY,
        message=(
            f"{system} detected. {detail} Authenticated with its read-only service "
            f"identity; {ENUMERATION[system_id]} lists {len(found)} datasets."
        ),
        payload={"system": system, "datasets": [d.id for d in found]},
    )
    yield Beat(weight=3, label=f"found {system}")

    profiled = _profile(state, env, system_id)
    _connect(env, system_id)
    env.record(
        type="discovery.system.connected",
        category=Category.SUCCESS,
        message=f"{system} connected. {profiled} datasets profiled for field completeness.",
        payload={"system": system, "profiled": profiled},
    )
    yield Beat(weight=2, label=f"connected {system}")


def discovery(state: SystemState) -> Workflow:
    """INITIALIZED to DISCOVERY_COMPLETE, pausing once for credentials.

    The run begins from INITIALIZED rather than reaching it. Planting the
    seed is what produces that state, and it happens over HTTP before the
    engine is started (FR-S2), so `seed.loaded` and the transition into
    INITIALIZED belong to the seed API and not to this workflow.
    """
    env = Environment(state, ACME)

    state.record(
        type="system.ready",
        category=Category.SUCCESS,
        message="Three layers registered. The system is ready to discover an environment.",
    )
    yield Beat(weight=4, label="system ready")

    # -- The declared inventory ---------------------------------------
    # The Adaptation layer names five systems. Knowing a name is not
    # knowing a system, so they enter the graph as unknown.
    state.transition(LifecycleState.DISCOVERING)
    declared = list(SYSTEM_ORDER)
    env.reveal(CLIENT, origin=Origin.DECLARED)
    env.reveal(*declared, status=NodeStatus.UNKNOWN, origin=Origin.DECLARED)
    env.record(
        type="discovery.inventory.loaded",
        category=Category.DISCOVERY,
        message=(
            f"Source inventory read from the Adaptation layer: {len(declared)} declared "
            "systems, none yet reached."
        ),
        payload={"declared": declared},
    )
    yield Beat(weight=2, label="inventory")

    # -- ServiceNow: §68 steps 4 to 8 ---------------------------------
    servicenow = "servicenow"
    api, cmdb = (s.id for s in _surfaces(servicenow))

    env.reveal(servicenow, api, cmdb)
    env.record(
        type="discovery.system.found",
        category=Category.DISCOVERY,
        message="ServiceNow detected. The REST Table API exposes the Incident API and the CMDB.",
        payload={"system": "ServiceNow"},
    )
    yield Beat(weight=2, label="ServiceNow detected")

    env.set_status(NodeStatus.TESTING, servicenow, api)
    env.record(
        type="discovery.endpoint.testing",
        category=Category.VALIDATION,
        message="Testing reachability of the ServiceNow Incident API.",
        payload={"system": "ServiceNow", "endpoint": api},
    )
    yield Beat(weight=2, label="ServiceNow reachability")

    _proceed(
        authorize(
            state,
            ActionRequest(
                action=Action.REQUEST_CREDENTIAL,
                resource="ServiceNow read-only service identity",
                source="ServiceNow",
                write_scope=False,
            ),
        )
    )
    env.set_status(NodeStatus.REQUIRES_INPUT, servicenow, api)
    env.record(
        type="discovery.credentials.required",
        category=Category.VALIDATION,
        message=(
            "Incident API reachable. It requires authentication, and no credential "
            "is held for its service account."
        ),
        payload={"system": "ServiceNow", "endpoint": api},
    )
    yield Beat(weight=2, label="credentials required")

    # Discovery has not ended here; it is waiting (FR-L4, FR-D7).
    #
    # Three fields, because a request a person can answer has to say what
    # is wanted, what it will be able to reach, and what for (FR-H2). This
    # is §17's example, word for word.
    state.transition(LifecycleState.DISCOVERY_BLOCKED)
    submission = yield AwaitHuman(
        request=BlockedOn(
            kind=RequestKind.CREDENTIALS,
            request_id=CREDENTIAL_REQUEST,
            prompt="ServiceNow requires authentication.",
            access="Read-only Incident API",
            reason="Historical incident data is required for Ticket Anomaly Detection.",
        )
    )

    # The credential is used for the one handshake it was asked for, then
    # gone. The shape of the submission is recorded, never its values
    # (FR-H5).
    state.transition(LifecycleState.DISCOVERING)
    _proceed(
        authorize(
            state,
            ActionRequest(
                action=Action.USE_CREDENTIAL,
                resource="Supplied ServiceNow credential, for the Incident API handshake",
                source="ServiceNow",
                same_source=True,
            ),
        )
    )
    _proceed(_authenticate(state, servicenow))
    env.set_status(NodeStatus.VALIDATED, servicenow, api, cmdb)
    env.record(
        type="discovery.credentials.accepted",
        category=Category.VALIDATION,
        message="Credentials accepted. Values were used for the handshake and discarded.",
        payload={"fields": sorted((submission or {}).keys())},
    )
    yield Beat(weight=3, floor=2.0, label="credentials accepted")

    _proceed(_enumerate(state, servicenow))
    tables = [*_datasets(api), *_datasets(cmdb)]
    env.reveal(*(t.id for t in tables))
    env.record(
        type="discovery.datasets.enumerated",
        category=Category.DISCOVERY,
        message=(
            f"ServiceNow table metadata enumerated: {len(_datasets(api))} tables behind "
            f"the Incident API, {len(_datasets(cmdb))} in the CMDB."
        ),
        payload={"system": "ServiceNow", "datasets": [t.id for t in tables]},
    )
    yield Beat(weight=3, label="ServiceNow enumerated")

    # The DENY of FR-P6 (OQ-6). A plausible analytical motive and a
    # minimised projection, refused anyway: the table is the boundary,
    # not the columns. The workflow acts on the answer by leaving the
    # table out, which is the requester's side of §10's separation.
    security_log = next(t for t in tables if t.security_table)
    decision = _read(
        state,
        servicenow,
        [security_log],
        resource=f"ServiceNow {security_log.label}",
        purpose=(
            "Considered as a usage signal: sign-in counts per application, "
            "application identifier and timestamp only."
        ),
    )
    if decision.effect is not Effect.ALLOW:
        env.exclude(security_log.id, decision.rule)
        env.record(
            type="discovery.dataset.excluded",
            category=Category.DISCOVERY,
            message=(
                f"{security_log.label} left out of the environment model under "
                f"{decision.rule}. Discovery continues without it."
            ),
            payload={"dataset": security_log.id, "rule": decision.rule},
        )
    yield Beat(weight=3, label="security log refused")

    profiled = _profile(state, env, servicenow)
    _connect(env, servicenow)
    env.record(
        type="discovery.system.connected",
        category=Category.SUCCESS,
        message=f"ServiceNow connected. {profiled} tables profiled for field completeness.",
        payload={"system": "ServiceNow", "profiled": profiled},
    )
    yield Beat(weight=2, label="ServiceNow connected")

    # -- §68 step 9: the rest of the environment ----------------------
    yield from _found_and_enumerated(state, env, "sap", "OData service catalogue available.")
    yield from _found_and_enumerated(state, env, "sqlserver", "Reporting schema available.")

    # -- License Management System: the one timeout (FR-D8) -----------
    lms = "lms"
    (vendor_api,) = (s.id for s in _surfaces(lms))
    env.reveal(lms, vendor_api, status=NodeStatus.TESTING)
    env.record(
        type="discovery.system.found",
        category=Category.DISCOVERY,
        message="License Management System detected. Testing reachability of its vendor REST API.",
        payload={"system": "License Management System", "endpoint": vendor_api},
    )
    yield Beat(weight=2, label="found License Management System")

    # Floored, because a recovery the audience does not see is a recovery
    # that did not happen. Reachability is a probe, not a capability, so
    # the retry is not a second authentication (PR-014 counts those).
    env.set_status(NodeStatus.ERROR, vendor_api)
    env.record(
        type="discovery.endpoint.timeout",
        category=Category.WARNING,
        severity=Severity.WARNING,
        message="License Management System vendor API did not respond within 30s. Retrying once.",
        payload={"system": "License Management System", "endpoint": vendor_api},
    )
    yield Beat(weight=5, floor=3.0, label="timeout")

    _proceed(_authenticate(state, lms))
    env.set_status(NodeStatus.VALIDATED, lms, vendor_api)
    env.record(
        type="discovery.endpoint.recovered",
        category=Category.SUCCESS,
        message=(
            "License Management System responded on retry and authenticated with its "
            "read-scope API key. Discovery continues."
        ),
        payload={"system": "License Management System", "endpoint": vendor_api},
    )
    yield Beat(weight=4, floor=2.0, label="recovery")

    _proceed(_enumerate(state, lms))
    catalogue = _datasets(vendor_api)
    env.reveal(*(d.id for d in catalogue))
    env.record(
        type="discovery.datasets.enumerated",
        category=Category.DISCOVERY,
        message=f"License Management System product catalogue enumerated: {len(catalogue)} datasets.",
        payload={"system": "License Management System", "datasets": [d.id for d in catalogue]},
    )
    yield Beat(weight=2, label="License Management System enumerated")

    profiled = _profile(state, env, lms)
    _connect(env, lms)
    env.record(
        type="discovery.system.connected",
        category=Category.SUCCESS,
        message=f"License Management System connected. {profiled} datasets profiled.",
        payload={"system": "License Management System", "profiled": profiled},
    )
    yield Beat(weight=2, label="License Management System connected")

    # -- Legacy Application Registry: administrator-supplied (FR-D6) --
    # No endpoint, so nothing is discovered: the registry is known because
    # a person handed over its export. Reading that export is still an
    # action, so it is still gated.
    legacy = "legacy"
    (export,) = _datasets(legacy)
    env.reveal(legacy, export.id, status=NodeStatus.DETECTED, origin=Origin.ADMINISTRATOR)
    _proceed(
        _read(
            state,
            legacy,
            [export],
            resource="Legacy Application Registry export",
            purpose="Parse and checksum the administrator-supplied export.",
        )
    )
    env.profile(export.id)
    env.set_status(NodeStatus.VALIDATED, legacy)
    env.record(
        type="discovery.system.registered",
        category=Category.DISCOVERY,
        message=(
            "Legacy Application Registry registered from an administrator-supplied export. "
            "It has no endpoint; the export was parsed and checksummed on receipt."
        ),
        payload={"system": "Legacy Application Registry", "origin": Origin.ADMINISTRATOR},
    )
    yield Beat(weight=2, label="legacy registry")

    # -- Completion (FR-D9, FR-D10) -----------------------------------
    env.set_status(NodeStatus.VALIDATED, CLIENT)
    env.complete()
    summary = summarise(state.environment)
    feasible = sum(1 for m in summary["methodologies"] if m["appearsFeasible"])
    env.record(
        type="discovery.completed",
        category=Category.SUCCESS,
        message=(
            f"Discovery complete: {summary['systems']} systems, {summary['dataSources']} data "
            f"sources, {summary['datasets']} datasets ({summary['profiled']} profiled, "
            f"{summary['excluded']} excluded by policy). Evidence located for {feasible} of "
            f"{len(summary['methodologies'])} methodologies."
        ),
    )
    state.transition(LifecycleState.DISCOVERY_COMPLETE)
    yield Beat(weight=4, label="discovery complete")
