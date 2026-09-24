"""Application Portfolio Rationalization, declared (OQ-1, OQ-2).

Colour is the disposition. Applications with no usage instrumentation are
Unresolved and say so: never Retire, never "unused" (adaptation.md).
"""

from app.analytics.generator import MONTHS, month_labels
from app.analytics.generator.applications import BUSINESS_UNITS, CRITICALITY, DISPOSITIONS
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

RETAINED_PEERS = [Restriction(dimension="disposition", values=["Retain"])]
CANDIDATES = [Restriction(dimension="disposition", values=["Retire", "Consolidate"])]

APPLICATIONS = Dashboard(
    solution_id="application-portfolio-rationalization",
    title="Application Portfolio",
    subtitle="Every application with its usage, ownership, cost and dependencies, and the "
    "disposition that evidence supports.",
    # An application is named by its id at the record level, as a ticket is by
    # its number: its name is already the application level's crumb, and the
    # record step would repeat it.
    entity=Entity(
        label="application", plural="applications", id="application", title="application"
    ),
    frames=[Frame(id="usage", label="Monthly usage", dimensions=["month"])],
    dimensions=[
        Dimension(
            id="unit", label="Business unit", column="businessUnit", order=list(BUSINESS_UNITS)
        ),
        Dimension(id="capability", label="Capability", column="capability"),
        Dimension(
            id="disposition",
            label="Disposition",
            column="disposition",
            order=list(DISPOSITIONS),
            colour="disposition",
        ),
        Dimension(id="app", label="Application", column="name"),
        Dimension(
            id="criticality", label="Criticality", column="criticality", order=list(CRITICALITY)
        ),
        Dimension(id="owner", label="Owner", column="owner"),
        Dimension(
            id="month",
            label="Month",
            column="month",
            order=MONTHS,
            labels=month_labels(),
            frame="usage",
        ),
    ],
    measures=[
        Measure(id="applications", label="Applications", agg="count"),
        Measure(id="cost", label="Annual cost", agg="sum", column="annualCost", format="currency"),
        Measure(id="users", label="Monthly users", agg="sum", column="monthlyUsers"),
        Measure(
            id="cost-per-user",
            label="Cost per user",
            agg="ratio",
            numerator="cost",
            denominator="users",
            format="currency",
        ),
        Measure(id="dependents", label="Dependent systems", agg="sum", column="dependenciesIn"),
        Measure(
            id="monthly-users",
            label="Distinct users",
            agg="sum",
            column="users",
            frame="usage",
        ),
    ],
    colours=[
        ColourScale(
            id="disposition",
            roles={
                "Retain": "positive",
                "Consolidate": "series-1",
                "Replace": "warning",
                "Retire": "anomaly",
                "Unresolved": "muted",
            },
        ),
    ],
    kpis=[
        Kpi(id="k-applications", label="Applications", measure="applications", context="of-total"),
        Kpi(id="k-cost", label="Annual cost", measure="cost", emphasis="primary"),
        Kpi(id="k-users", label="Monthly users", measure="users"),
        Kpi(id="k-cost-per-user", label="Cost per user", measure="cost-per-user"),
        Kpi(id="k-dependents", label="Dependent systems", measure="dependents"),
    ],
    charts=[
        Chart(
            id="portfolio",
            title="Portfolio by capability",
            question="Where does the money go, and what does the evidence say to do with it?",
            mark="treemap",
            path=["capability", "app"],
            size="cost",
            colour=ColourRule(by="disposition"),
            interaction=Interaction(click="drill"),
            layout=Layout(span=7, height="tall", emphasis="primary"),
        ),
        Chart(
            id="by-unit",
            title="Dispositions by business unit",
            question="Which parts of the business hold the most to retire or consolidate?",
            mark="bar",
            x="unit",
            series="disposition",
            measures=[Series(measure="applications", role="series-1")],
            orientation="horizontal",
            stacked=True,
            layout=Layout(span=5, height="tall"),
        ),
        Chart(
            id="usage",
            title="Monthly users by disposition",
            question="Are the candidates for retirement already fading?",
            mark="line",
            frame="usage",
            x="month",
            series="disposition",
            measures=[Series(measure="monthly-users", role="series-1")],
            normalise=True,
            interaction=Interaction(click="none"),
            layout=Layout(span=6),
            note="Each disposition as a share of its own twelve months, so a fading line shows "
            "whatever its size. Unresolved applications have no usage instrumentation and draw "
            "no line.",
        ),
        Chart(
            id="cost-per-user",
            title="Cost per user",
            question="Which applications cost the most for the people who use them?",
            mark="bar",
            x="app",
            measures=[Series(measure="cost-per-user", role="series-1")],
            colour=ColourRule(by="disposition"),
            orientation="horizontal",
            sort="value",
            limit=12,
            layout=Layout(span=6),
        ),
    ],
    tables=[
        Table(
            id="candidates",
            title="Retire and consolidate candidates",
            question="Which applications could go, and what depends on them?",
            kind="records",
            columns=[
                Column(field="name", label="Application"),
                Column(field="capability", label="Capability"),
                Column(field="disposition", label="Disposition", chip="disposition"),
                Column(field="owner", label="Owner"),
                Column(field="monthlyUsers", label="Users", format="integer", align="right"),
                Column(field="annualCost", label="Annual cost", format="currency", align="right"),
                Column(field="dependenciesIn", label="Dependents", format="integer", align="right"),
            ],
            sort_by="annualCost",
            page_size=8,
            where=CANDIDATES,
            row_action="entity",
        ),
        Table(
            id="records",
            title="Applications",
            question="Every application behind the figures above.",
            kind="records",
            columns=[
                Column(field="application", label="Id"),
                Column(field="name", label="Application"),
                Column(field="unit", label="Business unit"),
                Column(field="capability", label="Capability"),
                Column(field="owner", label="Owner"),
                Column(field="criticality", label="Criticality"),
                Column(field="lifecycle", label="Lifecycle"),
                Column(field="monthlyUsers", label="Users", format="integer", align="right"),
                Column(field="annualCost", label="Annual cost", format="currency", align="right"),
                Column(field="disposition", label="Disposition", chip="disposition"),
            ],
            sort_by="annualCost",
            page_size=25,
            row_action="entity",
        ),
    ],
    sections=[
        Section(
            id="headline",
            kind="kpis",
            views=["k-applications", "k-cost", "k-users", "k-cost-per-user", "k-dependents"],
        ),
        Section(
            id="analysis", kind="grid", views=["portfolio", "by-unit", "usage", "cost-per-user"]
        ),
        Section(id="focus", kind="table", views=["candidates"]),
        Section(id="records", kind="table", views=["records"]),
    ],
    hierarchy=[
        Level(id="all", label="Portfolio"),
        Level(id="unit", label="Business unit", dimension="unit"),
        Level(id="disposition", label="Disposition", dimension="disposition"),
        Level(id="application", label="Application", dimension="app"),
        Level(id="record", label="Usage records", entity=True),
    ],
    evidence=Evidence(
        dimension="disposition",
        findings=[
            Finding(
                value="Retire",
                title="Retirement candidate",
                description="Almost nobody uses it and almost nothing depends on it.",
                metric="monthlyUsers",
                metric_label="Monthly users",
                unit="decimal",
                baseline="usersBaseline",
                comparable_by=["capability"],
                comparable_where=RETAINED_PEERS,
            ),
            Finding(
                value="Consolidate",
                title="Consolidation candidate",
                description="A minor application in a capability another application serves "
                "far more widely.",
                metric="monthlyUsers",
                metric_label="Monthly users",
                unit="decimal",
                baseline="usersBaseline",
                comparable_by=["capability"],
                comparable_where=RETAINED_PEERS,
            ),
            Finding(
                value="Replace",
                title="Replacement candidate",
                description="End of life and still in use, at a high cost per user.",
                metric="costPerUser",
                metric_label="Cost per user",
                unit="currency",
                baseline="costPerUserBaseline",
                comparable_by=["capability"],
                comparable_where=RETAINED_PEERS,
            ),
            Finding(
                value="Unresolved",
                title="Unresolved",
                description="No usage instrumentation, so usage is unknown.",
                insufficient="Usage cannot be observed for this application. It is reported as "
                "unresolved, never as unused.",
            ),
        ],
        methodology="application-portfolio-rationalization",
        validation=[
            "Disposition assigned at generation by the methodology's rules, in order: "
            "instrumentation, usage and dependencies, lifecycle, share of the capability.",
            "Baseline: the retained applications of the same capability.",
        ],
    ),
)
