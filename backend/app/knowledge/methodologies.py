"""The three methodologies, and the evidence each one requires.

Fixed in code rather than read from the seed (FR-S6). `core.md` states
the same requirements in prose under each methodology's "Required
evidence" heading, and this module is the executable form of those lists.

Each requirement names a *concept*, and a concept is located in an
environment by the fields that carry it: `acme.py` tags every profiled
field with the concept it carries, following the concept mapping in
`adaptation.md`. Discovery uses this to say which methodologies appear
feasible (FR-D10). Assessment extends it at M7 with the thresholds that
turn located evidence into a graded feasibility (FR-A2, FR-A3).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Requirement:
    concept: str
    description: str


@dataclass(frozen=True)
class Methodology:
    id: str
    name: str
    requires: tuple[Requirement, ...]


METHODOLOGIES: tuple[Methodology, ...] = (
    Methodology(
        "ticket-anomaly-detection",
        "Ticket Anomaly Detection",
        (
            Requirement(
                "ticket",
                "Ticket records with identifier, opened and resolved timestamps, "
                "priority and assignment group",
            ),
            Requirement("category-taxonomy", "Category and subcategory per ticket"),
            Requirement("reassignment-history", "Reassignment history per ticket"),
            Requirement("group-membership", "Assignment group membership and size"),
        ),
    ),
    Methodology(
        "license-optimization",
        "License Optimization",
        (
            Requirement("entitlement", "Entitlement records per product, with quantity and term"),
            Requirement("assignment", "Assignment records per product and actor"),
            Requirement("product-usage", "Usage signals per product and actor, daily or finer"),
            Requirement("unit-cost", "Unit cost per product per period"),
            Requirement("leaver-record", "Leaver records, to tell an inactive account from a person"),
        ),
    ),
    Methodology(
        "application-portfolio-rationalization",
        "Application Portfolio Rationalization",
        (
            Requirement(
                "application-inventory",
                "Application inventory with identifier, name and lifecycle status",
            ),
            Requirement("application-usage", "Usage signals per application, with distinct actors"),
            Requirement("ownership", "Ownership records naming an accountable owner"),
            Requirement("application-cost", "Cost records per application per period"),
            Requirement("dependency", "Dependency records, inbound and outbound"),
            Requirement("criticality", "Business criticality per application"),
            Requirement("capability", "The business capability each application serves"),
        ),
    ),
)
