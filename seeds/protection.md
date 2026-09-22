# Protection

The Protection layer is the boundary autonomy operates inside. It is
cross-cutting: every phase of the lifecycle passes requests through it,
from the first discovery probe to the last dashboard query.

Protection is not an instruction. A rule that exists only as guidance to a
model is not a control, because nothing prevents the guidance being
ignored. Every rule in this file is evaluated as a decision on a request
before the request is carried out.

## Purpose

The Protection layer answers one question:

> Is this action permitted, and who must authorise it?

It governs identity, authentication, credential handling, tool access,
data access, data movement, agent capability, write and destructive
operations, evidence integrity and auditability.

## Principles

### Autonomy inside hard boundaries

The system decides what to do. It does not decide what it is allowed to
do. Those are different questions, answered by different components, and
the second one is answered here.

### Deny by default

A request that matches no rule is denied. A permission that was never
granted is not an oversight to be worked around.

### Enforcement at the request, not at the intent

Protection evaluates the concrete action about to be taken: the endpoint,
the dataset, the operation, the destination. It does not evaluate a
description of the action.

### Escalation is a decision, not a failure

An escalated request is a request whose consequence requires human
authority. It is presented as a decision with the evidence it rests on,
and the answer is recorded.

### Every decision is recorded

Allow, deny and escalate are all recorded with the rule that produced
them. A control that leaves no record cannot be audited, and an
unauditable control is an assumption.

## Evaluation

### Decisions

| Decision | Meaning |
| --- | --- |
| ALLOW | The action proceeds. |
| DENY | The action does not proceed, and no alternative route is attempted. |
| ESCALATE | The action is suspended until a person authorises it. |

### Precedence

All matching rules are evaluated, and the strictest decision wins.

1. Any matching DENY produces DENY.
2. Otherwise, any matching ESCALATE produces ESCALATE.
3. Otherwise, a matching ALLOW produces ALLOW.
4. With no match, the decision is DENY under rule PR-000.

Precedence is fixed. A rule cannot claim priority over another rule, so
adding a permissive rule can never weaken a restrictive one.

## Rules

### Default

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-000 | Any action matching no other rule | DENY | Deny by default. Capability is granted explicitly. |

### Identity and authentication

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-010 | Authenticate to a discovered source with a supplied read-only service identity | ALLOW | Read-only service identities are the intended access path. |
| PR-011 | Authenticate with an interactive user identity | DENY | The system acts as itself, never as a person. Attribution must survive the action. |
| PR-012 | Authenticate to a source not present in the Adaptation source inventory | ESCALATE | An undeclared source may be in scope, but an administrator confirms it first. |
| PR-013 | Re-authenticate after a rejected credential | ESCALATE | A rejected credential is answered by a person, not by a retry. |
| PR-014 | Attempt a third authentication against the same source in one run | DENY | Repeated attempts against a production source are indistinguishable from an attack. |

### Credentials

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-020 | Request a credential from an operator through the human-input surface | ALLOW | Asking is the sanctioned path when a credential is not already held. |
| PR-021 | Use a supplied credential for the handshake it was requested for | ALLOW | Single declared purpose. |
| PR-022 | Persist a credential to disk, to state, or to the event log | DENY | Credentials are used and discarded. Nothing stores them. |
| PR-023 | Include a credential value in any event, message, payload or report | DENY | The audit log records that a credential was used, never its value. |
| PR-024 | Reuse a credential supplied for one source against a different source | DENY | A credential is scoped to the source it was requested for. |
| PR-025 | Request a credential with write scope | ESCALATE | Write scope exceeds what analysis requires, so it is justified to a person. |

### Data access

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-030 | Read a dataset declared in the Adaptation concept mapping | ALLOW | Declared datasets are in scope by construction. |
| PR-031 | Read a dataset from a declared source that is not in the concept mapping | ESCALATE | The source is in scope; this dataset is not yet declared. |
| PR-032 | Read a dataset classified as personal data beyond the mapped fields | DENY | Field-level scope is the control. Broadening it is not a runtime decision. |
| PR-033 | Read authentication, audit or security-log tables | DENY | Not required by any methodology, and high consequence if exfiltrated. |
| PR-034 | Read beyond the retrieval window declared in Adaptation | ESCALATE | A wider window changes what the conclusion rests on. |
| PR-035 | Enumerate schema or table metadata on a declared source | ALLOW | Discovery requires enumeration, which reveals structure rather than content. |
| PR-036 | Execute an unparameterised query against a source system | DENY | Composed queries are not reviewable and not safely bounded. |

### Data movement

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-040 | Write retrieved data to the isolated analytical workspace | ALLOW | The workspace is the intended destination and no source reads it. |
| PR-041 | Move data to any destination outside the analytical workspace | DENY | The workspace boundary is the containment. |
| PR-042 | Transmit data to a network destination outside the client environment | DENY | No outbound path exists for client data. |
| PR-043 | Export an aggregate or report to an operator-requested file | ESCALATE | Export leaves the boundary, so a person authorises what leaves. |
| PR-044 | Copy personal data into an artefact that will be presented | ESCALATE | Presentation is disclosure. It is authorised, and the fields are named. |

### Write and destructive operations

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-050 | Create or modify a record in a source system | ESCALATE | Any write to a system of record is a human decision. |
| PR-051 | Delete a record in a source system | DENY | No methodology requires deletion. There is no circumstance in which this is the system acting correctly. |
| PR-052 | Modify a schema, index or permission in a source system | DENY | Structural change is outside the system's purpose. |
| PR-053 | Deploy an analytical service into the client environment | ESCALATE | Deployment is consequential and reviewable before it happens. |
| PR-054 | Withdraw or roll back a deployment the system made | ESCALATE | Reversal is as consequential as the act, and is authorised the same way. |
| PR-055 | Take any action against a system marked out of scope | DENY | Out of scope is a boundary, not a preference. |

### Agent capability

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-060 | Invoke a tool present in the granted capability set | ALLOW | Capability is enumerated, and the enumeration is the grant. |
| PR-061 | Invoke a tool outside the granted capability set | DENY | Capability is not acquired at runtime. |
| PR-062 | Execute code supplied by, or derived from, retrieved data | DENY | Retrieved data is input. Input is never instruction. |
| PR-063 | Spawn a subordinate process with capabilities exceeding its parent | DENY | Capability cannot be escalated by delegation. |
| PR-064 | Extend the run beyond the declared analysis scope | ESCALATE | Scope is agreed in advance and changed by agreement. |

### Evidence integrity

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-070 | Record an evidence item with a source and field attribution | ALLOW | Attribution is what makes the item evidence. |
| PR-071 | Record an evidence item with no attribution | DENY | An unattributable fact cannot support a conclusion. |
| PR-072 | Modify or remove a recorded evidence item | DENY | The evidence chain is append-only. A correction is a new item. |
| PR-073 | Publish a conclusion whose required evidence is incomplete | DENY | Insufficiency is reported as insufficiency, never as a weaker conclusion. |
| PR-074 | Publish a conclusion whose supporting evidence is outside its freshness window | ESCALATE | Stale evidence may still be acceptable, and a person decides that. |
| PR-075 | Present a model output as an evidence item | DENY | A model output is a hypothesis. It is evidenced, not evidence. |

### Auditability

| Rule | Action | Decision | Rationale |
| --- | --- | --- | --- |
| PR-080 | Record every protection decision with its rule identifier | ALLOW | The decision record is itself a requirement. |
| PR-081 | Suppress, redact or delete an entry in the decision record | DENY | A record that can be edited is not a record. |
| PR-082 | Proceed with an action whose decision was not recorded | DENY | An unrecorded action is indistinguishable from an unauthorised one. |

## Human authority

The following always require a person, whatever else permits them.

1. Any write to a system of record.
2. Any deployment into the client environment.
3. Any export of data past the workspace boundary.
4. Any widening of the declared analysis scope.
5. Any conclusion published on evidence outside its freshness window.

An escalation records what was asked, the evidence presented with it, who
answered, and what they answered. An escalation that expires without an
answer is treated as a denial.

## Audit record

Every decision records:

| Field | Content |
| --- | --- |
| Decision | ALLOW, DENY or ESCALATE |
| Rule | The identifier of the rule that produced the decision |
| Action | The concrete action requested |
| Target | The source, dataset or destination |
| Phase | The lifecycle phase the request was made in |
| Timestamp | When the decision was made |
| Authority | The person, where the decision was an escalation |

The record is append-only and is retained for the life of the run. It is
the answer to the question of what the system was permitted to do, rather
than what it was asked to do.
