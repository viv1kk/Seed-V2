# Adaptation

The Adaptation layer binds the Core to one client environment. The Core
knows that licence optimisation requires entitlement, assignment, usage
and cost. This file records where each of those lives at this client, how
it is retrieved, which fields carry which concept, and how far each source
can be trusted.

This file is environment-specific and is replaced wholesale at the next
client. The Core is not.

## Purpose

The Adaptation layer answers one question:

> How is this methodology applied to this specific environment?

It holds the source inventory, the concept-to-field mapping, the retrieval
procedures, the trust assessment for each source, and the identity
reconciliation rules that make counts across sources comparable.

## Client

| Field | Value |
| --- | --- |
| Client | ACME Enterprise |
| Environment | Production, read-only |
| Discovery mode | Endpoint enumeration, with administrator-supplied entries |
| Time zone for reporting | Europe/London |
| Fiscal period | Calendar month |

## Systems

Five systems constitute the discoverable environment. Anything not named
here is out of scope until Discovery reports it and an administrator
confirms it.

### ServiceNow

| Field | Value |
| --- | --- |
| Role | System of record for service tickets and the CMDB |
| Access | REST Table API, read-only service account |
| Authentication | Service account, basic, rotated quarterly |
| Enumeration | Table metadata endpoint |
| Rate limit | 1000 requests per hour |

### SAP

| Field | Value |
| --- | --- |
| Role | System of record for cost centres and vendor contracts |
| Access | OData service, read-only |
| Authentication | Service account, OAuth client credentials |
| Enumeration | Service catalogue document |
| Rate limit | 300 requests per hour |

### SQL Server

| Field | Value |
| --- | --- |
| Role | Reporting warehouse; holds usage telemetry and the application inventory |
| Access | Read-only login, single reporting schema |
| Authentication | Integrated, read-only role |
| Enumeration | Information schema |
| Rate limit | None; concurrency capped at four |

### Licence Management System

| Field | Value |
| --- | --- |
| Role | System of record for entitlements and assignments |
| Access | Vendor REST API |
| Authentication | API key, read scope |
| Enumeration | Product catalogue endpoint |
| Rate limit | 120 requests per minute |

### Legacy Application Registry

| Field | Value |
| --- | --- |
| Role | Historic application inventory, partially superseded by SQL Server |
| Access | No endpoint. Administrator-supplied export |
| Authentication | Not applicable |
| Enumeration | Not discoverable |
| Rate limit | Not applicable |

## Concept mapping

Each Core concept is located here. A concept with no mapping is reported
as an insufficiency by the methodology that requires it, not silently
skipped.

### Ticket concepts

| Concept | Source | Field |
| --- | --- | --- |
| Entity (ticket) | ServiceNow | incident.number |
| Opened timestamp | ServiceNow | incident.opened_at |
| Resolved timestamp | ServiceNow | incident.resolved_at |
| Category | ServiceNow | incident.category, incident.subcategory |
| Priority | ServiceNow | incident.priority |
| Assignment group | ServiceNow | incident.assignment_group |
| Reassignment history | ServiceNow | sys_audit on incident.assignment_group |
| Group size | ServiceNow | sys_user_grmember, counted per group |

### Licence concepts

| Concept | Source | Field |
| --- | --- | --- |
| Entitlement | Licence Management System | entitlement.quantity |
| Entitlement term | Licence Management System | entitlement.start_date, entitlement.end_date |
| Assignment | Licence Management System | assignment.user_id, assignment.product_id |
| Usage signal | SQL Server | rpt.product_activity (actor, product, activity_date) |
| Cost | SAP | contract_item.unit_price, contract_item.currency |
| Leaver record | ServiceNow | sys_user.active, sys_user.last_login_time |

### Application concepts

| Concept | Source | Field |
| --- | --- | --- |
| Entity (application) | SQL Server | rpt.application (app_id, app_name) |
| Lifecycle status | SQL Server | rpt.application.lifecycle_status |
| Usage signal | SQL Server | rpt.app_access (actor, app_id, access_date) |
| Owner | ServiceNow | cmdb_ci_appl.owned_by |
| Cost | SAP | cost_centre_allocation.amount |
| Dependency | ServiceNow | cmdb_rel_ci, filtered to depends-on |
| Criticality | ServiceNow | cmdb_ci_appl.business_criticality |
| Capability | Legacy Application Registry | capability column of the supplied export |

## Retrieval

### Procedures

| Source | Procedure |
| --- | --- |
| ServiceNow | Paged Table API reads, 1000 rows per page, ordered by sys_id, filtered to the analysis window |
| SAP | OData query with an explicit select list, paged by skip token |
| SQL Server | Parameterised read against the reporting schema only |
| Licence Management System | Full catalogue read, then per-product assignment reads |
| Legacy Application Registry | Administrator-supplied CSV export, parsed and checksummed on receipt |

### Windows

| Dataset | Window |
| --- | --- |
| Tickets | 12 months, closed tickets only |
| Product activity | 12 months, daily grain |
| Application access | 12 months, daily grain |
| Entitlements and assignments | Current, at retrieval time |
| Cost | 12 closed fiscal periods |
| Dependencies | Current, at retrieval time |

### Isolation

Retrieved data is written to an analytical workspace that no source
system reads. No retrieval procedure in this file performs a write to a
source system. The Protection layer enforces this independently of
anything stated here.

## Identity reconciliation

Counts of distinct actors cross three identity spaces, so they are
reconciled before any count is taken.

| Space | Key | Reconciled by |
| --- | --- | --- |
| ServiceNow user | sys_user.sys_id | Corporate email, lowercased |
| Licence assignment | assignment.user_id | Corporate email, lowercased |
| Warehouse actor | rpt.*.actor | Domain-qualified account name, mapped through rpt.actor_identity |

Rules:

- An actor present in only one space is counted, and its single-space
  origin is recorded on the evidence item.
- Two actors reconciling to the same email are merged, and the merge is
  reported.
- A service account is excluded from person counts and counted separately
  as automated access.

## Trust assessment

Each source is assessed for authority, completeness and freshness. This
assessment is evidence about the evidence, and it travels with any
conclusion drawn from the source.

| Source | Authority | Completeness | Freshness | Notes |
| --- | --- | --- | --- | --- |
| ServiceNow (tickets) | Authoritative | High | Minutes | Resolution timestamps are reliable; reopen handling changed 14 months ago, outside the window |
| ServiceNow (CMDB) | Authoritative for ownership | Medium | Days | Ownership is unassigned on part of the portfolio |
| SAP | Authoritative for cost | High | One closed period | Cost is allocated per cost centre, not per application, for part of the portfolio |
| SQL Server | Derived, not authoritative | High for instrumented entities | 24 hours | Instrumentation does not cover every application |
| Licence Management System | Authoritative for entitlement and assignment | High | Hours | Holds no usage signal, so it cannot evidence consumption |
| Legacy Application Registry | Not authoritative | Unknown | At export | Superseded in part by SQL Server; overlap is unresolved |

### Declared conflicts

Two conflicts are known in this environment and are declared here so they
are surfaced rather than rediscovered.

1. The application inventory exists in both SQL Server and the Legacy
   Application Registry, and the two disagree on membership. Neither is
   declared authoritative. Any portfolio conclusion resting on the
   difference is escalated as an ambiguity.
2. Ownership exists in the ServiceNow CMDB and in the Legacy Application
   Registry. The CMDB is declared authoritative. Where the CMDB has no
   owner, the registry value is reported as a candidate and not adopted.

### Known gaps

| Gap | Consequence |
| --- | --- |
| No usage instrumentation for applications hosted outside the corporate network | Those applications are unresolved for usage, never classified as unused |
| Cost allocated at cost-centre level for part of the portfolio | Per-application cost is reported as an allocation, with the method named |
| The Legacy Application Registry has no endpoint | Its data is administrator-supplied and its freshness is the export date |
| Reassignment history is retained for 13 months | A 12-month window is supported; anything longer is not |

## Feasibility

Adaptation reports what each Core methodology can be run on in this
environment. Feasibility is a statement about evidence coverage, not a
prediction of the result.

| Methodology | Feasible | Limiting factor |
| --- | --- | --- |
| Ticket Anomaly Detection | Yes | None. All required evidence is present and authoritative. |
| Licence Optimisation | Yes | Usage signal coverage must be confirmed per product before an unconsumed classification is reported. |
| Application Portfolio Rationalisation | Partially | Usage instrumentation is incomplete and the inventory conflict is unresolved. Retirement dispositions are withheld for uninstrumented applications. |
