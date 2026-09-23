"""The protection rule set --- authoritative, and mirrored in `protection.md`.

Every rule here is a declaration: which actions it covers, which facts
about the request it tests, and what it decides when they hold. The engine
evaluates requests against these declarations (FR-P1). Nothing is scripted:
a workflow asks, and the answer is whatever the rules produce.

`seeds/protection.md` is the readable form of this module. D-6 makes this
file authoritative and a parity test holds the two together, row for row:
id, action text, decision and rationale (FR-P7). Change one without the
other and the suite fails, because a documented policy that differs from
the enforced one is exactly what a sceptical viewer looks for.

Facts, not descriptions
-----------------------
A request states *facts* --- is the source declared, is the dataset
mapped, is this a security table --- and rules test them. A request never
states which rule should apply, and nothing here reads the free-text
`purpose` or `resource`. That is §10's principle made structural:
enforcement is at the request, not at the intent.

A request must state every fact that any rule for its action depends on.
Those facts are derived from the rules below rather than listed
separately, so adding a rule tightens what callers must establish without
anyone remembering to. A request that leaves one out is denied under
PR-000: an unstated fact cannot be assumed benign, or a restrictive rule
would be skipped simply by not mentioning the thing it restricts.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.domain.schema import Schema


class Effect(StrEnum):
    """The three decisions (FR-P3), in ascending strictness."""

    ALLOW = "ALLOW"
    ESCALATE = "ESCALATE"
    DENY = "DENY"

    @property
    def strictness(self) -> int:
        return {Effect.ALLOW: 0, Effect.ESCALATE: 1, Effect.DENY: 2}[self]


class Action(StrEnum):
    """What can be requested. One verb per kind of consequence."""

    AUTHENTICATE = "authenticate"
    REQUEST_CREDENTIAL = "request-credential"
    USE_CREDENTIAL = "use-credential"
    PERSIST_CREDENTIAL = "persist-credential"
    DISCLOSE_CREDENTIAL = "disclose-credential"
    READ = "read"
    ENUMERATE = "enumerate"
    MOVE_DATA = "move-data"
    TRANSMIT_EXTERNAL = "transmit-external"
    EXPORT = "export"
    PRESENT_PERSONAL_DATA = "present-personal-data"
    WRITE_SOURCE = "write-source"
    DELETE_SOURCE = "delete-source"
    ALTER_SOURCE = "alter-source"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    INVOKE_TOOL = "invoke-tool"
    EXECUTE_RETRIEVED_CODE = "execute-retrieved-code"
    SPAWN = "spawn"
    EXTEND_SCOPE = "extend-scope"
    RECORD_EVIDENCE = "record-evidence"
    MODIFY_EVIDENCE = "modify-evidence"
    PUBLISH_CONCLUSION = "publish-conclusion"
    PRESENT_MODEL_OUTPUT = "present-model-output"
    RECORD_DECISION = "record-decision"
    SUPPRESS_RECORD = "suppress-record"
    PROCEED_UNRECORDED = "proceed-unrecorded"
    CONSOLIDATE_RECORDS = "consolidate-records"
    CLEAR_SCRATCH = "clear-scratch"
    PROMOTE_INTERFACE = "promote-interface"
    RETIRE_TOOL = "retire-tool"

    @property
    def label(self) -> str:
        return ACTION_LABELS[self]


ACTION_LABELS: dict[Action, str] = {
    Action.AUTHENTICATE: "Authenticate",
    Action.REQUEST_CREDENTIAL: "Request credential",
    Action.USE_CREDENTIAL: "Use credential",
    Action.PERSIST_CREDENTIAL: "Persist credential",
    Action.DISCLOSE_CREDENTIAL: "Disclose credential value",
    Action.READ: "Read dataset",
    Action.ENUMERATE: "Enumerate metadata",
    Action.MOVE_DATA: "Move data",
    Action.TRANSMIT_EXTERNAL: "Transmit outside the environment",
    Action.EXPORT: "Export",
    Action.PRESENT_PERSONAL_DATA: "Present personal data",
    Action.WRITE_SOURCE: "Write to source",
    Action.DELETE_SOURCE: "Delete from source",
    Action.ALTER_SOURCE: "Alter source structure",
    Action.DEPLOY: "Deploy",
    Action.ROLLBACK: "Roll back deployment",
    Action.INVOKE_TOOL: "Invoke tool",
    Action.EXECUTE_RETRIEVED_CODE: "Execute retrieved code",
    Action.SPAWN: "Spawn process",
    Action.EXTEND_SCOPE: "Extend scope",
    Action.RECORD_EVIDENCE: "Record evidence",
    Action.MODIFY_EVIDENCE: "Modify evidence",
    Action.PUBLISH_CONCLUSION: "Publish conclusion",
    Action.PRESENT_MODEL_OUTPUT: "Present model output as evidence",
    Action.RECORD_DECISION: "Record decision",
    Action.SUPPRESS_RECORD: "Suppress decision record",
    Action.PROCEED_UNRECORDED: "Proceed unrecorded",
    Action.CONSOLIDATE_RECORDS: "Consolidate working notes",
    Action.CLEAR_SCRATCH: "Clear scratch space",
    Action.PROMOTE_INTERFACE: "Promote interface",
    Action.RETIRE_TOOL: "Retire build tool",
}

#: What closing the seeding phase does to the system's own artefacts, and
#: what PR-092 holds to the system's own (D-16).
CLEANUP_ACTIONS: frozenset[Action] = frozenset(
    {Action.CONSOLIDATE_RECORDS, Action.CLEAR_SCRATCH, Action.RETIRE_TOOL}
)

#: Actions that act on a source system, which is what PR-055 governs.
SOURCE_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.AUTHENTICATE,
        Action.ENUMERATE,
        Action.READ,
        Action.WRITE_SOURCE,
        Action.DELETE_SOURCE,
        Action.ALTER_SOURCE,
    }
)


class Identity(StrEnum):
    SERVICE_READ_ONLY = "service-read-only"
    SERVICE_WRITE = "service-write"
    INTERACTIVE = "interactive"


class ActionRequest(Schema):
    """One requested action, with the facts the rules decide on.

    The first four fields describe the request for the audit record and
    are never read by a rule. Everything after them is a fact, and `None`
    means the requester did not establish it.
    """

    action: Action
    resource: str
    source: str | None = None
    purpose: str | None = None

    # Facts.
    identity: Identity | None = None
    source_declared: bool | None = None
    dataset_mapped: bool | None = None
    unmapped_personal_fields: bool | None = None
    security_table: bool | None = None
    within_window: bool | None = None
    parameterised: bool | None = None
    in_scope: bool | None = None
    after_rejection: bool | None = None
    attempt: int | None = Field(default=None, ge=1)
    write_scope: bool | None = None
    same_source: bool | None = None
    to_workspace: bool | None = None
    tool_granted: bool | None = None
    exceeds_parent: bool | None = None
    attributed: bool | None = None
    evidence_complete: bool | None = None
    evidence_fresh: bool | None = None
    system_owned: bool | None = None
    deployment_approved: bool | None = None
    build_complete: bool | None = None


DESCRIPTIVE_FIELDS: frozenset[str] = frozenset({"action", "resource", "source", "purpose"})
FACTS: frozenset[str] = frozenset(ActionRequest.model_fields) - DESCRIPTIVE_FIELDS


@dataclass(frozen=True)
class AtLeast:
    """A fact condition that holds at or above a threshold."""

    minimum: int

    def holds(self, value: Any) -> bool:
        return isinstance(value, int) and value >= self.minimum


@dataclass(frozen=True)
class Rule:
    """One rule, as declared here and as documented in `protection.md`.

    `description` and `rationale` are the text of the markdown row, word
    for word; the parity test compares them. `actions` of `None` would
    mean every action, and is used only by the fallback.
    """

    id: str
    group: str
    description: str
    effect: Effect
    rationale: str
    actions: frozenset[Action] | None = None
    when: dict[str, Any] = field(default_factory=dict)
    fallback: bool = False

    def __post_init__(self) -> None:
        unknown = set(self.when) - FACTS
        if unknown:
            raise ValueError(f"{self.id} tests unknown facts: {sorted(unknown)}")

    def covers(self, action: Action) -> bool:
        return not self.fallback and self.actions is not None and action in self.actions

    def holds(self, request: ActionRequest) -> bool:
        for fact, expected in self.when.items():
            value = getattr(request, fact)
            if value is None:
                return False
            if isinstance(expected, AtLeast):
                if not expected.holds(value):
                    return False
            elif value != expected:
                return False
        return True

    @property
    def specificity(self) -> int:
        return len(self.when)


def only(*actions: Action) -> frozenset[Action]:
    return frozenset(actions)


DEFAULT = "Default"
IDENTITY = "Identity and authentication"
CREDENTIALS = "Credentials"
ACCESS = "Data access"
MOVEMENT = "Data movement"
WRITES = "Write and destructive operations"
CAPABILITY = "Agent capability"
EVIDENCE = "Evidence integrity"
AUDIT = "Auditability"
CLOSING = "Closing the seeding phase"

GROUPS: tuple[str, ...] = (
    DEFAULT,
    IDENTITY,
    CREDENTIALS,
    ACCESS,
    MOVEMENT,
    WRITES,
    CAPABILITY,
    EVIDENCE,
    AUDIT,
    CLOSING,
)

A, D, E = Effect.ALLOW, Effect.DENY, Effect.ESCALATE

RULES: tuple[Rule, ...] = (
    # -- Default --------------------------------------------------------
    Rule(
        "PR-000", DEFAULT,
        "Any action matching no other rule", D,
        "Deny by default. Capability is granted explicitly.",
        fallback=True,
    ),
    # -- Identity and authentication ------------------------------------
    Rule(
        "PR-010", IDENTITY,
        "Authenticate to a discovered source with a supplied read-only service identity", A,
        "Read-only service identities are the intended access path.",
        only(Action.AUTHENTICATE), {"identity": Identity.SERVICE_READ_ONLY},
    ),
    Rule(
        "PR-011", IDENTITY,
        "Authenticate with an interactive user identity", D,
        "The system acts as itself, never as a person. Attribution must survive the action.",
        only(Action.AUTHENTICATE), {"identity": Identity.INTERACTIVE},
    ),
    Rule(
        "PR-012", IDENTITY,
        "Authenticate to a source not present in the Adaptation source inventory", E,
        "An undeclared source may be in scope, but an administrator confirms it first.",
        only(Action.AUTHENTICATE), {"source_declared": False},
    ),
    Rule(
        "PR-013", IDENTITY,
        "Re-authenticate after a rejected credential", E,
        "A rejected credential is answered by a person, not by a retry.",
        only(Action.AUTHENTICATE), {"after_rejection": True},
    ),
    Rule(
        "PR-014", IDENTITY,
        "Attempt a third authentication against the same source in one run", D,
        "Repeated attempts against a production source are indistinguishable from an attack.",
        only(Action.AUTHENTICATE), {"attempt": AtLeast(3)},
    ),
    # -- Credentials ----------------------------------------------------
    Rule(
        "PR-020", CREDENTIALS,
        "Request a credential from an operator through the human-input surface", A,
        "Asking is the sanctioned path when a credential is not already held.",
        only(Action.REQUEST_CREDENTIAL),
    ),
    Rule(
        "PR-021", CREDENTIALS,
        "Use a supplied credential for the handshake it was requested for", A,
        "Single declared purpose.",
        only(Action.USE_CREDENTIAL), {"same_source": True},
    ),
    Rule(
        "PR-022", CREDENTIALS,
        "Persist a credential to disk, to state, or to the event log", D,
        "Credentials are used and discarded. Nothing stores them.",
        only(Action.PERSIST_CREDENTIAL),
    ),
    Rule(
        "PR-023", CREDENTIALS,
        "Include a credential value in any event, message, payload or report", D,
        "The audit log records that a credential was used, never its value.",
        only(Action.DISCLOSE_CREDENTIAL),
    ),
    Rule(
        "PR-024", CREDENTIALS,
        "Reuse a credential supplied for one source against a different source", D,
        "A credential is scoped to the source it was requested for.",
        only(Action.USE_CREDENTIAL), {"same_source": False},
    ),
    Rule(
        "PR-025", CREDENTIALS,
        "Request a credential with write scope", E,
        "Write scope exceeds what analysis requires, so it is justified to a person.",
        only(Action.REQUEST_CREDENTIAL), {"write_scope": True},
    ),
    # -- Data access ----------------------------------------------------
    Rule(
        "PR-030", ACCESS,
        "Read a dataset declared in the Adaptation concept mapping", A,
        "Declared datasets are in scope by construction.",
        only(Action.READ), {"dataset_mapped": True},
    ),
    Rule(
        "PR-031", ACCESS,
        "Read a dataset from a declared source that is not in the concept mapping", E,
        "The source is in scope; this dataset is not yet declared.",
        only(Action.READ), {"source_declared": True, "dataset_mapped": False},
    ),
    Rule(
        "PR-032", ACCESS,
        "Read a dataset classified as personal data beyond the mapped fields", D,
        "Field-level scope is the control. Broadening it is not a runtime decision.",
        only(Action.READ), {"unmapped_personal_fields": True},
    ),
    Rule(
        "PR-033", ACCESS,
        "Read authentication, credential-store or security-log tables", D,
        "Not required by any methodology, and high consequence if exfiltrated.",
        only(Action.READ), {"security_table": True},
    ),
    Rule(
        "PR-034", ACCESS,
        "Read beyond the retrieval window declared in Adaptation", E,
        "A wider window changes what the conclusion rests on.",
        only(Action.READ), {"within_window": False},
    ),
    Rule(
        "PR-035", ACCESS,
        "Enumerate schema or table metadata on a declared source", A,
        "Discovery requires enumeration, which reveals structure rather than content.",
        only(Action.ENUMERATE), {"source_declared": True},
    ),
    Rule(
        "PR-036", ACCESS,
        "Execute an unparameterised query against a source system", D,
        "Composed queries are not reviewable and not safely bounded.",
        only(Action.READ), {"parameterised": False},
    ),
    # -- Data movement --------------------------------------------------
    Rule(
        "PR-040", MOVEMENT,
        "Write retrieved data to the isolated analytical workspace", A,
        "The workspace is the intended destination and no source reads it.",
        only(Action.MOVE_DATA), {"to_workspace": True},
    ),
    Rule(
        "PR-041", MOVEMENT,
        "Move data to any destination outside the analytical workspace", D,
        "The workspace boundary is the containment.",
        only(Action.MOVE_DATA), {"to_workspace": False},
    ),
    Rule(
        "PR-042", MOVEMENT,
        "Transmit data to a network destination outside the client environment", D,
        "No outbound path exists for client data.",
        only(Action.TRANSMIT_EXTERNAL),
    ),
    Rule(
        "PR-043", MOVEMENT,
        "Export an aggregate or report to an operator-requested file", E,
        "Export leaves the boundary, so a person authorises what leaves.",
        only(Action.EXPORT),
    ),
    Rule(
        "PR-044", MOVEMENT,
        "Copy personal data into an artefact that will be presented", E,
        "Presentation is disclosure. It is authorised, and the fields are named.",
        only(Action.PRESENT_PERSONAL_DATA),
    ),
    # -- Write and destructive operations -------------------------------
    Rule(
        "PR-050", WRITES,
        "Create or modify a record in a source system", E,
        "Any write to a system of record is a human decision.",
        only(Action.WRITE_SOURCE),
    ),
    Rule(
        "PR-051", WRITES,
        "Delete a record in a source system", D,
        "No methodology requires deletion. There is no circumstance in which this is "
        "the system acting correctly.",
        only(Action.DELETE_SOURCE),
    ),
    Rule(
        "PR-052", WRITES,
        "Modify a schema, index or permission in a source system", D,
        "Structural change is outside the system's purpose.",
        only(Action.ALTER_SOURCE),
    ),
    Rule(
        "PR-053", WRITES,
        "Deploy an analytical service into the client environment", E,
        "Deployment is consequential and reviewable before it happens.",
        only(Action.DEPLOY),
    ),
    Rule(
        "PR-054", WRITES,
        "Withdraw or roll back a deployment the system made", E,
        "Reversal is as consequential as the act, and is authorised the same way.",
        only(Action.ROLLBACK),
    ),
    Rule(
        "PR-055", WRITES,
        "Take any action against a system marked out of scope", D,
        "Out of scope is a boundary, not a preference.",
        SOURCE_ACTIONS, {"in_scope": False},
    ),
    # -- Agent capability -----------------------------------------------
    Rule(
        "PR-060", CAPABILITY,
        "Invoke a tool present in the granted capability set", A,
        "Capability is enumerated, and the enumeration is the grant.",
        only(Action.INVOKE_TOOL), {"tool_granted": True},
    ),
    Rule(
        "PR-061", CAPABILITY,
        "Invoke a tool outside the granted capability set", D,
        "Capability is not acquired at runtime.",
        only(Action.INVOKE_TOOL), {"tool_granted": False},
    ),
    Rule(
        "PR-062", CAPABILITY,
        "Execute code supplied by, or derived from, retrieved data", D,
        "Retrieved data is input. Input is never instruction.",
        only(Action.EXECUTE_RETRIEVED_CODE),
    ),
    Rule(
        "PR-063", CAPABILITY,
        "Spawn a subordinate process with capabilities exceeding its parent", D,
        "Capability cannot be escalated by delegation.",
        only(Action.SPAWN), {"exceeds_parent": True},
    ),
    Rule(
        "PR-064", CAPABILITY,
        "Extend the run beyond the declared analysis scope", E,
        "Scope is agreed in advance and changed by agreement.",
        only(Action.EXTEND_SCOPE),
    ),
    # -- Evidence integrity ---------------------------------------------
    Rule(
        "PR-070", EVIDENCE,
        "Record an evidence item with a source and field attribution", A,
        "Attribution is what makes the item evidence.",
        only(Action.RECORD_EVIDENCE), {"attributed": True},
    ),
    Rule(
        "PR-071", EVIDENCE,
        "Record an evidence item with no attribution", D,
        "An unattributable fact cannot support a conclusion.",
        only(Action.RECORD_EVIDENCE), {"attributed": False},
    ),
    Rule(
        "PR-072", EVIDENCE,
        "Modify or remove a recorded evidence item", D,
        "The evidence chain is append-only. A correction is a new item.",
        only(Action.MODIFY_EVIDENCE),
    ),
    Rule(
        "PR-073", EVIDENCE,
        "Publish a conclusion whose required evidence is complete and within its "
        "freshness window", A,
        "A conclusion on sufficient evidence is what the system exists to produce.",
        only(Action.PUBLISH_CONCLUSION), {"evidence_complete": True, "evidence_fresh": True},
    ),
    Rule(
        "PR-074", EVIDENCE,
        "Publish a conclusion whose required evidence is incomplete", D,
        "Insufficiency is reported as insufficiency, never as a weaker conclusion.",
        only(Action.PUBLISH_CONCLUSION), {"evidence_complete": False},
    ),
    Rule(
        "PR-075", EVIDENCE,
        "Publish a conclusion whose supporting evidence is outside its freshness window", E,
        "Stale evidence may still be acceptable, and a person decides that.",
        only(Action.PUBLISH_CONCLUSION), {"evidence_fresh": False},
    ),
    Rule(
        "PR-076", EVIDENCE,
        "Present a model output as an evidence item", D,
        "A model output is a hypothesis. It is evidenced, not evidence.",
        only(Action.PRESENT_MODEL_OUTPUT),
    ),
    # -- Auditability ---------------------------------------------------
    Rule(
        "PR-080", AUDIT,
        "Record every protection decision with its rule identifier", A,
        "The decision record is itself a requirement.",
        only(Action.RECORD_DECISION),
    ),
    Rule(
        "PR-081", AUDIT,
        "Suppress, redact or delete an entry in the decision record", D,
        "A record that can be edited is not a record.",
        only(Action.SUPPRESS_RECORD),
    ),
    Rule(
        "PR-082", AUDIT,
        "Proceed with an action whose decision was not recorded", D,
        "An unrecorded action is indistinguishable from an unauthorised one.",
        only(Action.PROCEED_UNRECORDED),
    ),
    # -- Closing the seeding phase (D-16) -------------------------------
    Rule(
        "PR-090", CLOSING,
        "Consolidate the system's own working notes into one seeding record", A,
        "The notes are the system's own record. Consolidating keeps every entry and "
        "changes no seed file.",
        only(Action.CONSOLIDATE_RECORDS), {"system_owned": True},
    ),
    Rule(
        "PR-091", CLOSING,
        "Release the system's own temporary analytical workspace", A,
        "Scratch space is system-owned storage. Releasing it deletes nothing a source "
        "system holds.",
        only(Action.CLEAR_SCRATCH), {"system_owned": True},
    ),
    Rule(
        "PR-092", CLOSING,
        "Consolidate, clear or retire anything the system does not own", D,
        "Clean-up covers the system's own artefacts. Client data is never cleaned up.",
        CLEANUP_ACTIONS, {"system_owned": False},
    ),
    Rule(
        "PR-093", CLOSING,
        "Promote a built Agent Component's interface to its release version when its "
        "deployment was approved", A,
        "The approval given under PR-053 already authorised the deployment this completes.",
        only(Action.PROMOTE_INTERFACE), {"deployment_approved": True},
    ),
    Rule(
        "PR-094", CLOSING,
        "Promote an interface whose deployment was not approved", E,
        "A release without an approval is a deployment, and a person authorises it.",
        only(Action.PROMOTE_INTERFACE), {"deployment_approved": False},
    ),
    Rule(
        "PR-095", CLOSING,
        "Retire a build tool and revoke its grant once the build is complete", A,
        "What built Agent One VW is not needed to run it, and a tool not held cannot be "
        "misused.",
        only(Action.RETIRE_TOOL), {"system_owned": True, "build_complete": True},
    ),
    Rule(
        "PR-096", CLOSING,
        "Retire a build tool while a build is in progress", E,
        "Retiring a tool mid-build strands what it was building, so a person decides.",
        only(Action.RETIRE_TOOL), {"build_complete": False},
    ),
)

FALLBACK: Rule = next(rule for rule in RULES if rule.fallback)
RULES_BY_ID: dict[str, Rule] = {rule.id: rule for rule in RULES}


def required_facts(action: Action) -> tuple[str, ...]:
    """Every fact a request for `action` must establish, in a stable order.

    Derived from the rules, so it can never lag them.
    """
    needed: set[str] = set()
    for rule in RULES:
        if rule.covers(action):
            needed.update(rule.when)
    return tuple(sorted(needed))
