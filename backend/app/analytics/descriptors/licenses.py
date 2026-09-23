"""License Optimization, declared (OQ-1, OQ-2).

Colour is the utilisation class. Recoverable cost is stated for priced
products only, and the seats it cannot price are counted and named: the
64% unit-price completeness discovery found reaches the dashboard as a
withheld figure, never an estimate (PR-074).
"""

from app.analytics.generator import MONTHS, month_labels
from app.analytics.generator.licenses import CLASSES, DEPARTMENTS, PRODUCTS, UNASSIGNED
from app.analytics.schema import (
    Chart,
    ColourRule,
    ColourScale,
    Column,
    Dashboard,
    Dimension,
    Entity,
    Evidence,
    Finding,
    Frame,
    Interaction,
    Kpi,
    Layout,
    Level,
    Measure,
    Restriction,
    Section,
    Series,
    Table,
)

ACTIVE_SEATS = [Restriction(dimension="class", values=["Active"])]

LICENSES = Dashboard(
    solution_id="license-optimization",
    title="Licence Utilisation",
    subtitle="Every entitled seat, whether it is assigned, and whether it is used: the gap "
    "between what is paid for and what is needed.",
    entity=Entity(label="seat", plural="seats", id="seat", title="seat"),
    frames=[Frame(id="activity", label="Monthly seat activity", dimensions=["month"])],
    dimensions=[
        Dimension(id="vendor", label="Vendor", column="vendor"),
        Dimension(id="product", label="Product", column="product", order=[p[1] for p in PRODUCTS]),
        Dimension(
            id="department",
            label="Department",
            column="department",
            order=[*DEPARTMENTS, UNASSIGNED],
        ),
        Dimension(
            id="class", label="Utilisation", column="class", order=list(CLASSES), colour="class"
        ),
        Dimension(
            id="month",
            label="Month",
            column="month",
            order=MONTHS,
            labels=month_labels(),
            frame="activity",
        ),
    ],
    measures=[
        Measure(id="seats", label="Seats", agg="count"),
        Measure(id="assigned", label="Assigned", agg="countIf", column="assigned"),
        Measure(id="active", label="Active", agg="countIf", column="active"),
        Measure(id="idle", label="Unused or underused", agg="countIf", column="idle"),
        Measure(
            id="recoverable-seats", label="Recoverable seats", agg="countIf", column="recoverable"
        ),
        Measure(
            id="recoverable-cost",
            label="Recoverable cost",
            agg="sum",
            column="recoverableCost",
            format="currency",
            withhold=True,
            note="Priced products only. Seats of unpriced products are withheld, not estimated.",
        ),
        Measure(
            id="utilisation",
            label="Utilisation",
            agg="ratio",
            numerator="active",
            denominator="seats",
            format="percent",
        ),
        Measure(
            id="assigned-monthly",
            label="Assigned seats",
            agg="countIf",
            column="assigned",
            frame="activity",
        ),
        Measure(
            id="active-monthly",
            label="Seats in use",
            agg="countIf",
            column="active",
            frame="activity",
        ),
        Measure(
            id="days-inactive",
            label="Days since last use",
            agg="mean",
            column="daysInactive",
            format="days",
        ),
    ],
    colours=[
        ColourScale(
            id="class",
            roles={
                "Active": "positive",
                "Underused": "warning",
                "Unused": "anomaly",
                "Leaver": "negative",
                "Unassigned": "muted",
            },
        ),
    ],
    kpis=[
        Kpi(id="k-seats", label="Licences entitled", measure="seats", context="of-total"),
        Kpi(id="k-assigned", label="Assigned", measure="assigned"),
        Kpi(id="k-active", label="Active", measure="active"),
        Kpi(id="k-idle", label="Unused or underused", measure="idle", emphasis="primary"),
        Kpi(
            id="k-cost",
            label="Recoverable cost a year",
            measure="recoverable-cost",
            emphasis="primary",
            note="Priced products only.",
        ),
    ],
    charts=[
        Chart(
            id="portfolio",
            title="Seats by vendor and product",
            question="Where is the licence estate, and how much of each product is used?",
            mark="treemap",
            path=["vendor", "product", "class"],
            size="seats",
            colour=ColourRule(by="class"),
            interaction=Interaction(click="drill"),
            layout=Layout(span=7, height="tall", emphasis="primary"),
        ),
        Chart(
            id="gap",
            title="Entitled, assigned and active",
            question="How wide is the gap between what is bought and what is used?",
            mark="bar",
            x="product",
            measures=[
                Series(measure="seats", role="baseline"),
                Series(measure="assigned", role="series-1"),
                Series(measure="active", role="positive"),
            ],
            orientation="horizontal",
            sort="value",
            limit=12,
            layout=Layout(span=5, height="tall"),
        ),
        Chart(
            id="use-over-time",
            title="Assigned and in use, by month",
            question="Is the gap closing, or growing as more seats are assigned?",
            mark="line",
            frame="activity",
            x="month",
            measures=[
                Series(measure="assigned-monthly", role="baseline"),
                Series(measure="active-monthly", role="positive"),
            ],
            interaction=Interaction(click="none"),
            layout=Layout(span=6),
        ),
        Chart(
            id="cost",
            title="Recoverable cost by product",
            question="Which products would return the most if idle seats were released?",
            mark="bar",
            x="product",
            measures=[Series(measure="recoverable-cost", role="series-1")],
            orientation="horizontal",
            sort="value",
            layout=Layout(span=6, height="tall"),
            note="Unpriced products are withheld rather than shown as zero.",
        ),
    ],
    tables=[
        Table(
            id="candidates",
            title="Optimisation candidates",
            question="Which products have the most seats to release?",
            kind="summary",
            group_by=["product"],
            columns=[
                Column(field="product", label="Product"),
                Column(field="vendor", label="Vendor"),
                Column(field="seats", label="Seats", format="integer", align="right"),
                Column(field="utilisation", label="Utilisation", format="percent", align="right"),
                Column(field="idle", label="Idle", format="integer", align="right"),
                Column(
                    field="recoverable-seats", label="Recoverable", format="integer", align="right"
                ),
                Column(
                    field="recoverable-cost",
                    label="Recoverable cost",
                    format="currency",
                    align="right",
                ),
            ],
            sort_by="recoverable-seats",
            page_size=8,
        ),
        Table(
            id="records",
            title="Seats",
            question="Every seat behind the figures above.",
            kind="records",
            columns=[
                Column(field="seat", label="Seat"),
                Column(field="product", label="Product"),
                Column(field="department", label="Department"),
                Column(field="assignee", label="Assignee"),
                Column(field="lastActivity", label="Last used", format="date"),
                Column(field="daysInactive", label="Days idle", format="integer", align="right"),
                Column(field="class", label="Utilisation", chip="class"),
                Column(field="unitCost", label="Unit cost", format="currency", align="right"),
            ],
            sort_by="daysInactive",
            page_size=25,
            row_action="entity",
        ),
    ],
    sections=[
        Section(
            id="headline",
            kind="kpis",
            views=["k-seats", "k-assigned", "k-active", "k-idle", "k-cost"],
        ),
        Section(id="analysis", kind="grid", views=["portfolio", "gap", "use-over-time", "cost"]),
        Section(id="focus", kind="table", views=["candidates"]),
        Section(id="records", kind="table", views=["records"]),
    ],
    hierarchy=[
        Level(id="all", label="All products"),
        Level(id="vendor", label="Vendor", dimension="vendor"),
        Level(id="product", label="Product", dimension="product"),
        Level(id="class", label="Utilisation", dimension="class"),
        Level(id="seat", label="Seat", entity=True),
    ],
    evidence=Evidence(
        dimension="class",
        findings=[
            Finding(
                value="Unused",
                title="Unused seat",
                description="Assigned to someone who has not used it in the last 90 days.",
                metric="daysInactive",
                metric_label="Days since last use",
                unit="days",
                baseline="daysInactiveBaseline",
                comparable_by=["product"],
                comparable_where=ACTIVE_SEATS,
            ),
            Finding(
                value="Underused",
                title="Underused seat",
                description="Used on fewer than 10 of the last 90 days: a downgrade candidate.",
                metric="activeDays90",
                metric_label="Days used in the last 90",
                unit="days",
                baseline="activeDaysBaseline",
                comparable_by=["product"],
                comparable_where=ACTIVE_SEATS,
            ),
            Finding(
                value="Leaver",
                title="Seat held by a leaver",
                description="Assigned to a person who has left. An access finding as much as a "
                "cost one.",
                metric="daysInactive",
                metric_label="Days since last use",
                unit="days",
                baseline="daysInactiveBaseline",
                comparable_by=["product"],
                comparable_where=ACTIVE_SEATS,
            ),
            Finding(
                value="Unassigned",
                title="Unassigned seat",
                description="Entitled and paid for, and assigned to nobody.",
                insufficient="There is no use to compare: the seat has never been assigned.",
            ),
        ],
        methodology="license-optimization",
        validation=[
            "Utilisation class assigned at generation from days used in the last 90, the "
            "leaver record and the assignment.",
            "Baseline: active seats of the same product.",
            "Recoverable cost sums priced seats only; unpriced seats are counted and withheld.",
        ],
    ),
)
