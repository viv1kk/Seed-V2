"""The ACME Enterprise environment: five systems and their graph.

Exactly the five systems of §42 and §83.5 (FR-D1), each expanded into the
services, APIs, databases and datasets it is made of (FR-D2). The datasets
are the ones `adaptation.md` maps concepts onto, plus one it does not:
ServiceNow's security log, which enumeration finds and policy refuses.

Coordinates are hand-authored (D-4), in a 900 by 640 canvas, and they live
here so the graph and its layout stay in one file. The layout reads left
to right from the client to the datasets, one band per system:

    client      systems        access surface       datasets
      x=70       x=250            x=480               x=700

Bands are ordered for the cross-links rather than for the narrative, so
that each dependency joins neighbouring rows and no link crosses the
graph. Discovery still walks the systems in §68's order; the graph fills
in out of reading order, which is what finding an environment looks like.

Dataset rows sit 30 apart, with 18 more between surfaces. A surface sits
at the mean height of its datasets and a system at the mean of its
surfaces, so the fan-out stays symmetrical if a row is added.

Field completeness figures are simulated demo values (FR-A10). They follow
the trust assessment: ServiceNow tickets are complete, CMDB ownership is
not, SAP cost is incomplete at item level and allocated by cost centre for
part of the portfolio.
"""

from app.environment.model import (
    Definition,
    EdgeKind,
    EdgeSpec,
    FieldProfile,
    NodeKind,
    NodeSpec,
)

F = FieldProfile

CLIENT_X, SYSTEM_X, SURFACE_X, DATASET_X = 70.0, 250.0, 480.0, 700.0

CLIENT = "acme"


def _dataset(
    id: str,
    label: str,
    y: float,
    parent: str,
    *fields: FieldProfile,
    detail: str | None = None,
    mapped: bool = True,
    security_table: bool = False,
) -> NodeSpec:
    return NodeSpec(
        id=id,
        kind=NodeKind.DATASET,
        label=label,
        x=DATASET_X,
        y=y,
        parent=parent,
        detail=detail,
        mapped=mapped,
        security_table=security_table,
        fields=fields,
    )


NODES: tuple[NodeSpec, ...] = (
    NodeSpec(CLIENT, NodeKind.CLIENT, "ACME Enterprise", CLIENT_X, 385,
             detail="Production, read-only"),

    # -- ServiceNow ------------------------------------------------------
    NodeSpec("servicenow", NodeKind.SYSTEM, "ServiceNow", SYSTEM_X, 161, parent=CLIENT,
             detail="System of record for service tickets and the CMDB"),
    NodeSpec("servicenow.incident-api", NodeKind.API, "Incident API", SURFACE_X, 100,
             parent="servicenow", detail="REST Table API, read-only service account"),
    _dataset("servicenow.incident", "incident", 40, "servicenow.incident-api",
             F("number", "ticket", 1.0),
             F("opened_at", "ticket", 1.0),
             F("resolved_at", "ticket", 0.998),
             F("priority", "ticket", 1.0),
             F("assignment_group", "ticket", 0.994),
             F("category", "category-taxonomy", 0.987),
             F("subcategory", "category-taxonomy", 0.942)),
    _dataset("servicenow.metric_instance", "metric_instance", 70, "servicenow.incident-api",
             F("value", "reassignment-history", 1.0),
             F("start", "reassignment-history", 1.0),
             detail="Assignment group metric: reassignment history"),
    _dataset("servicenow.sys_user_grmember", "sys_user_grmember", 100, "servicenow.incident-api",
             F("group", "group-membership", 1.0),
             F("user", "group-membership", 1.0)),
    _dataset("servicenow.sys_user", "sys_user", 130, "servicenow.incident-api",
             F("active", "leaver-record", 1.0),
             F("last_login_time", "leaver-record", 0.913)),
    _dataset("servicenow.sys_security_log", "sys_security_log", 160, "servicenow.incident-api",
             detail="Authentication events. Not in the concept mapping.",
             mapped=False, security_table=True),
    NodeSpec("servicenow.cmdb", NodeKind.SERVICE, "CMDB", SURFACE_X, 223,
             parent="servicenow", detail="Configuration items, through the same Table API"),
    _dataset("servicenow.cmdb_ci_appl", "cmdb_ci_appl", 208, "servicenow.cmdb",
             F("owned_by", "ownership", 0.71),
             F("business_criticality", "criticality", 0.88)),
    _dataset("servicenow.cmdb_rel_ci", "cmdb_rel_ci", 238, "servicenow.cmdb",
             F("parent", "dependency", 1.0),
             F("child", "dependency", 1.0),
             F("type", "dependency", 1.0)),

    # -- SQL Server ------------------------------------------------------
    NodeSpec("sqlserver", NodeKind.SYSTEM, "SQL Server", SYSTEM_X, 331, parent=CLIENT,
             detail="Reporting warehouse: usage telemetry and the application inventory"),
    NodeSpec("sqlserver.rpt", NodeKind.DATABASE, "Reporting schema", SURFACE_X, 331,
             parent="sqlserver", detail="rpt schema, read-only role"),
    _dataset("sqlserver.rpt.application", "rpt.application", 286, "sqlserver.rpt",
             F("app_id", "application-inventory", 1.0),
             F("app_name", "application-inventory", 1.0),
             F("lifecycle_status", "application-inventory", 0.93)),
    _dataset("sqlserver.rpt.app_access", "rpt.app_access", 316, "sqlserver.rpt",
             F("actor", "application-usage", 0.99),
             F("app_id", "application-usage", 1.0),
             F("access_date", "application-usage", 1.0)),
    _dataset("sqlserver.rpt.actor_identity", "rpt.actor_identity", 346, "sqlserver.rpt",
             F("account", "identity-reconciliation", 1.0),
             F("email", "identity-reconciliation", 0.97)),
    _dataset("sqlserver.rpt.product_activity", "rpt.product_activity", 376, "sqlserver.rpt",
             F("actor", "product-usage", 0.99),
             F("product", "product-usage", 1.0),
             F("activity_date", "product-usage", 1.0)),

    # -- License Management System ---------------------------------------
    NodeSpec("lms", NodeKind.SYSTEM, "License Management System", SYSTEM_X, 454, parent=CLIENT,
             detail="System of record for entitlements and assignments"),
    NodeSpec("lms.api", NodeKind.API, "Vendor REST API", SURFACE_X, 454,
             parent="lms", detail="API key, read scope"),
    _dataset("lms.entitlement", "entitlement", 424, "lms.api",
             F("quantity", "entitlement", 1.0),
             F("start_date", "entitlement", 1.0),
             F("end_date", "entitlement", 0.97)),
    _dataset("lms.product", "product", 454, "lms.api",
             F("product_id", "product-catalogue", 1.0),
             F("name", "product-catalogue", 1.0)),
    _dataset("lms.assignment", "assignment", 484, "lms.api",
             F("user_id", "assignment", 1.0),
             F("product_id", "assignment", 1.0)),

    # -- SAP -------------------------------------------------------------
    NodeSpec("sap", NodeKind.SYSTEM, "SAP", SYSTEM_X, 547, parent=CLIENT,
             detail="System of record for cost centres and vendor contracts"),
    NodeSpec("sap.odata", NodeKind.SERVICE, "OData service", SURFACE_X, 547,
             parent="sap", detail="Finance and procurement, read-only"),
    _dataset("sap.contract_item", "contract_item", 532, "sap.odata",
             F("unit_price", "unit-cost", 0.64),
             F("currency", "unit-cost", 1.0)),
    _dataset("sap.cost_centre_allocation", "cost_centre_allocation", 562, "sap.odata",
             F("amount", "application-cost", 0.58),
             detail="Allocated per cost centre, not per application, for part of the portfolio"),

    # -- Legacy Application Registry --------------------------------------
    # No endpoint and no surface: the export hangs from the system itself,
    # because an administrator handed it over (FR-D6).
    NodeSpec("legacy", NodeKind.SYSTEM, "Legacy Application Registry", SYSTEM_X, 610,
             parent=CLIENT, detail="Historic application inventory, partially superseded"),
    _dataset("legacy.export", "registry export", 610, "legacy",
             F("capability", "capability", 0.82),
             F("owner", "ownership-candidate", 0.64),
             detail="Administrator-supplied CSV export, checksummed on receipt"),
)

#: Links across the structure, found once both ends are known.
LINKS: tuple[EdgeSpec, ...] = (
    EdgeSpec("sqlserver.rpt", "lms.api", EdgeKind.CONNECTS_TO,
             "Nightly product catalogue sync"),
    EdgeSpec("sqlserver.rpt.app_access", "sqlserver.rpt.application", EdgeKind.DEPENDS_ON,
             "Access is keyed by app_id"),
    EdgeSpec("sqlserver.rpt.product_activity", "lms.product", EdgeKind.DEPENDS_ON,
             "Activity is keyed by the licence product_id"),
    EdgeSpec("sap.contract_item", "lms.product", EdgeKind.DEPENDS_ON,
             "Contract items are priced per licence product"),
)

ACME = Definition(
    client="ACME Enterprise",
    width=900,
    height=640,
    nodes=NODES,
    links=LINKS,
)

#: The declared systems, in the order discovery walks them (§68).
SYSTEM_ORDER: tuple[str, ...] = ("servicenow", "sap", "sqlserver", "lms", "legacy")

#: What enumeration reads on each system, from the Adaptation inventory.
ENUMERATION: dict[str, str] = {
    "servicenow": "table metadata",
    "sap": "service catalogue",
    "sqlserver": "information schema",
    "lms": "product catalogue",
}
