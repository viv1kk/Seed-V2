"""The three methodologies, and the evidence each one requires.

Fixed in code rather than read from the seed (FR-S6). `core.md` states
the same content in prose under each methodology's headings --- purpose,
required evidence, analysis process --- and this module is the executable
form of it. Assessment reads nothing else about a methodology.

Each requirement names a *concept*, and a concept is located in an
environment by the fields that carry it: `acme.py` tags every profiled
field with the concept it carries, following the concept mapping in
`adaptation.md`. Discovery uses that to say which methodologies appear
feasible (FR-D10); `feasibility.py` grades how well (FR-A2, FR-A3).

A requirement's `remedy` is what would improve it, in the environment's
own terms (FR-A6). It is authored, because what a client should do about
a gap is knowledge rather than arithmetic. How far the gap is, and what
closing it would do to the grade, are computed.

`limitations` are the constraints `adaptation.md` declares as known gaps.
They hold whatever the field completeness is, so they are stated rather
than derived.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    concept: str
    description: str
    remedy: str = ""


@dataclass(frozen=True)
class Methodology:
    id: str
    name: str
    purpose: str
    requires: tuple[Requirement, ...]
    process: tuple[str, ...]
    limitations: tuple[str, ...] = ()


METHODOLOGIES: tuple[Methodology, ...] = (
    Methodology(
        id="ticket-anomaly-detection",
        name="Ticket Anomaly Detection",
        purpose=(
            "Find service tickets and ticket patterns that deviate from comparable "
            "work, so systemic failures are found rather than individual escalations."
        ),
        requires=(
            Requirement(
                "ticket",
                "Ticket records with identifier, opened and resolved timestamps, "
                "priority and assignment group",
                "Backfill resolution timestamps from the ServiceNow audit trail.",
            ),
            Requirement(
                "category-taxonomy",
                "Category and subcategory per ticket",
                "Enforce subcategory on ticket closure in ServiceNow.",
            ),
            Requirement(
                "reassignment-history",
                "Reassignment history per ticket",
                "Enable the assignment group metric definition in ServiceNow.",
            ),
            Requirement(
                "group-membership",
                "Assignment group membership and size",
                "Reconcile group membership with the identity provider.",
            ),
        ),
        process=(
            "Establish the population of closed tickets",
            "Compute per-category baselines",
            "Score each ticket against its baseline",
            "Detect level changes by category and group",
            "Adjust for multiple comparisons",
            "Group anomalies into patterns",
            "Rank patterns by excess resolution time",
        ),
        limitations=(
            "Reassignment history is retained for 13 months, so the analysis window "
            "cannot exceed 12.",
        ),
    ),
    Methodology(
        id="license-optimization",
        name="License Optimization",
        purpose=(
            "Establish the gap between entitlement, assignment and consumption for "
            "each licensed product, and quantify the recoverable cost in it."
        ),
        requires=(
            Requirement(
                "entitlement",
                "Entitlement records per product, with quantity and term",
                "Load contract terms into the License Management System.",
            ),
            Requirement(
                "assignment",
                "Assignment records per product and actor",
                "Reconcile assignments with the identity provider.",
            ),
            Requirement(
                "product-usage",
                "Usage signals per product and actor, daily or finer",
                "Extend product telemetry into the reporting warehouse.",
            ),
            Requirement(
                "unit-cost",
                "Unit cost per product per period",
                "Price the unpriced SAP contract items, or supply unit cost from the "
                "licence vendor's price list.",
            ),
            Requirement(
                "leaver-record",
                "Leaver records, to tell an inactive account from an inactive person",
                "Populate last sign-in for all ServiceNow user records.",
            ),
        ),
        process=(
            "Reconcile entitlement against assignment",
            "Classify each assignment by consumption",
            "Separate leavers as an access finding",
            "Quantify recoverable cost with its interval",
            "Identify downgrade candidates",
        ),
        limitations=(
            "Recoverable cost is an upper bound where contract terms prevent a "
            "mid-term reduction.",
        ),
    ),
    Methodology(
        id="application-portfolio-rationalization",
        name="Application Portfolio Rationalization",
        purpose=(
            "Decide for each application whether to retain, consolidate, replace or "
            "retire it, on evidence of usage, ownership, cost, dependency and "
            "criticality."
        ),
        requires=(
            Requirement(
                "application-inventory",
                "Application inventory with identifier, name and lifecycle status",
                "Complete lifecycle status for every application in the warehouse.",
            ),
            Requirement(
                "application-usage",
                "Usage signals per application, with distinct actors",
                "Instrument the applications that have no access telemetry.",
            ),
            Requirement(
                "ownership",
                "Ownership records naming an accountable owner",
                "Assign an accountable owner to every application in the CMDB.",
            ),
            Requirement(
                "application-cost",
                "Cost records per application per period",
                "Allocate cost per application rather than per cost centre in SAP.",
            ),
            Requirement(
                "dependency",
                "Dependency records, inbound and outbound",
                "Complete the CMDB relationship records.",
            ),
            Requirement(
                "criticality",
                "Business criticality per application",
                "Record business criticality for every application in the CMDB.",
            ),
            Requirement(
                "capability",
                "The business capability each application serves",
                "Map the remaining applications to a capability in the registry.",
            ),
        ),
        process=(
            "Establish the portfolio",
            "Profile usage over 12 months",
            "Build the dependency graph",
            "Group applications by capability",
            "Classify against the disposition rules",
            "Report cost and dependency consequences",
        ),
        limitations=(
            "Applications hosted outside the corporate network have no usage "
            "instrumentation; they are reported as unresolved, never as unused.",
            "The Legacy Application Registry and SQL Server disagree on portfolio "
            "membership; conclusions resting on the difference are escalated.",
        ),
    ),
)

BY_ID: dict[str, Methodology] = {methodology.id: methodology for methodology in METHODOLOGIES}
