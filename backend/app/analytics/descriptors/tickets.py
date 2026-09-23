"""Ticket Anomaly Detection, declared (OQ-1, §54, §55).

The deep dashboard. Five patterns, each a fixed colour everywhere; normal
tickets always neutral. The treemap is the route from many clusters into
one: pattern, then assignment group, then cluster, recoloured by cluster
once a single pattern is chosen.
"""

from app.analytics.generator import MONTHS, month_labels
from app.analytics.generator.tickets import (
    BANDS,
    CLUSTERS,
    METRICS,
    NORMAL,
    PATTERNS,
    PRIORITIES,
)
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

ANOMALIES_ONLY = [Restriction(dimension="pattern", values=[NORMAL], exclude=True)]

DESCRIPTIONS = {
    "Resolution stall": "Tickets resolved far more slowly than comparable work of the same "
    "category and priority.",
    "Reopen churn": "Tickets closed and reopened repeatedly, so the fix did not hold.",
    "Priority mismatch": "Tickets whose priority was changed back and forth, a sign they were "
    "misclassified when raised.",
    "Volume burst": "Many tickets raised against one configuration item within a day or two: "
    "one fault, reported many times.",
    "Reassignment loop": "Tickets passed between assignment groups far more often than "
    "comparable tickets, so nobody owned them.",
}

UNITS = {"hours": "hours", "count": "decimal"}

TICKETS = Dashboard(
    solution_id="ticket-anomaly-detection",
    title="Ticket Intelligence",
    subtitle="Service tickets that deviate from comparable work, grouped into patterns and "
    "clusters, each traceable to the tickets behind it.",
    entity=Entity(label="ticket", plural="tickets", id="number", title="number"),
    time="opened",
    dimensions=[
        Dimension(id="month", label="Month", column="month", order=MONTHS, labels=month_labels()),
        Dimension(
            id="pattern",
            label="Anomaly pattern",
            column="pattern",
            order=[NORMAL, *PATTERNS],
            colour="pattern",
        ),
        Dimension(
            id="cluster",
            label="Cluster",
            column="cluster",
            order=[f"Cluster {i + 1}" for i in range(len(CLUSTERS))],
            colour="cluster",
        ),
        Dimension(id="group", label="Assignment group", column="assignmentGroup"),
        Dimension(id="priority", label="Priority", column="priority", order=list(PRIORITIES)),
        Dimension(id="category", label="Category", column="category"),
        Dimension(id="band", label="Resolution time", column="resolutionBand", order=list(BANDS)),
        Dimension(
            id="status",
            label="Status",
            column="status",
            order=["Normal", "Anomalous"],
            colour="status",
        ),
    ],
    measures=[
        Measure(id="tickets", label="Tickets", agg="count"),
        Measure(id="anomalies", label="Anomalous tickets", agg="countIf", column="anomalous"),
        Measure(
            id="rate",
            label="Anomaly rate",
            agg="ratio",
            numerator="anomalies",
            denominator="tickets",
            format="percent",
        ),
        Measure(
            id="resolution",
            label="Median resolution",
            agg="median",
            column="resolutionHours",
            format="hours",
        ),
        Measure(id="clusters", label="Clusters", agg="distinct", column="cluster"),
        Measure(id="observed", label="Observed", agg="mean", column="observed", format="decimal"),
        Measure(id="expected", label="Baseline", agg="mean", column="expected", format="decimal"),
        Measure(
            id="deviation",
            label="Deviation",
            agg="lift",
            numerator="observed",
            denominator="expected",
            format="lift",
        ),
        Measure(
            id="excess",
            label="Excess resolution",
            agg="sum",
            column="excessHours",
            format="hours",
        ),
        Measure(id="score", label="Mean score", agg="mean", column="score", format="score"),
    ],
    colours=[
        ColourScale(
            id="pattern",
            roles={
                NORMAL: "muted",
                "Resolution stall": "series-1",
                "Reopen churn": "series-2",
                "Priority mismatch": "series-3",
                "Volume burst": "series-4",
                "Reassignment loop": "series-5",
            },
        ),
        # Clusters are numbered by pattern, so cycling eight colours over
        # them gives every cluster of one pattern its own colour.
        ColourScale(id="cluster", mode="ordinal"),
        ColourScale(id="status", roles={"Normal": "baseline", "Anomalous": "anomaly"}),
    ],
    kpis=[
        Kpi(id="k-tickets", label="Total tickets", measure="tickets", context="of-total"),
        Kpi(
            id="k-anomalies",
            label="Anomalies",
            measure="anomalies",
            emphasis="primary",
            context="of-total",
        ),
        Kpi(id="k-rate", label="Anomaly rate", measure="rate"),
        Kpi(id="k-resolution", label="Median resolution", measure="resolution"),
        Kpi(id="k-clusters", label="Clusters", measure="clusters", context="of-total"),
    ],
    charts=[
        Chart(
            id="volume",
            title="Ticket volume and anomalies",
            question="Is anomalous work rising with volume, or on its own?",
            mark="line",
            x="month",
            measures=[
                Series(measure="tickets", role="baseline"),
                Series(measure="anomalies", role="anomaly", axis="secondary"),
            ],
            interaction=Interaction(click="drill", brush=True),
            layout=Layout(span=12, height="compact", emphasis="primary"),
        ),
        Chart(
            id="clusters",
            title="Anomaly clusters",
            question="Where do the anomalies concentrate? Pattern, then group, then cluster.",
            mark="treemap",
            path=["pattern", "group", "cluster"],
            size="anomalies",
            colour=ColourRule(by="pattern", refine="cluster"),
            where=ANOMALIES_ONLY,
            interaction=Interaction(click="drill"),
            layout=Layout(span=7, height="tall", emphasis="primary"),
            empty="No anomalous tickets in the current selection.",
        ),
        Chart(
            id="by-group",
            title="Anomalies by assignment group",
            question="Which teams carry the anomalous work, and of which kind?",
            mark="bar",
            x="group",
            series="pattern",
            measures=[Series(measure="anomalies", role="anomaly")],
            orientation="horizontal",
            stacked=True,
            sort="value",
            limit=12,
            where=ANOMALIES_ONLY,
            layout=Layout(span=5, height="tall"),
            empty="No anomalous tickets in the current selection.",
        ),
        Chart(
            id="trend",
            title="Anomaly trend by pattern",
            question="When did each pattern appear, and is it recurring?",
            mark="line",
            x="month",
            series="pattern",
            measures=[Series(measure="anomalies", role="anomaly")],
            where=ANOMALIES_ONLY,
            interaction=Interaction(click="drill"),
            layout=Layout(span=6),
        ),
        Chart(
            id="by-priority",
            title="Anomalies by priority",
            question="Are anomalies concentrated in urgent work or routine work?",
            mark="bar",
            x="priority",
            series="pattern",
            measures=[Series(measure="anomalies", role="anomaly")],
            stacked=True,
            where=ANOMALIES_ONLY,
            layout=Layout(span=3),
        ),
        Chart(
            id="resolution",
            title="Resolution time",
            question="How differently are anomalous tickets resolved from normal ones?",
            mark="bar",
            x="band",
            series="status",
            measures=[Series(measure="tickets", role="baseline")],
            normalise=True,
            layout=Layout(span=3),
            note="Share of each population, so a small anomalous group compares with a large "
            "normal one.",
        ),
    ],
    tables=[
        Table(
            id="cluster-table",
            title="Top anomaly clusters",
            question="Which clusters cost the most resolution time?",
            kind="summary",
            group_by=["cluster"],
            columns=[
                Column(field="cluster", label="Cluster", chip="cluster"),
                Column(field="pattern", label="Pattern", chip="pattern"),
                Column(field="group", label="Assignment group"),
                Column(field="anomalies", label="Tickets", format="integer", align="right"),
                Column(
                    field="observed",
                    label="Observed",
                    format="decimal",
                    align="right",
                    unit_from_finding=True,
                ),
                Column(
                    field="expected",
                    label="Baseline",
                    format="decimal",
                    align="right",
                    unit_from_finding=True,
                ),
                Column(field="deviation", label="Deviation", format="lift", align="right"),
                Column(field="excess", label="Excess resolution", format="hours", align="right"),
            ],
            sort_by="excess",
            page_size=8,
            where=ANOMALIES_ONLY,
            row_action="filter",
            empty="No anomalous tickets in the current selection.",
        ),
        Table(
            id="records",
            title="Tickets",
            question="Every ticket behind the figures above.",
            kind="records",
            columns=[
                Column(field="number", label="Number"),
                Column(field="opened", label="Opened", format="datetime"),
                Column(field="priority", label="Priority"),
                Column(field="category", label="Category"),
                Column(field="group", label="Assignment group"),
                Column(field="reassignments", label="Groups", format="integer", align="right"),
                Column(field="resolutionHours", label="Resolution", format="hours", align="right"),
                Column(field="pattern", label="Pattern", chip="pattern"),
                Column(field="cluster", label="Cluster", chip="cluster"),
                Column(field="score", label="Score", format="score", align="right"),
            ],
            sort_by="score",
            page_size=25,
            row_action="entity",
        ),
    ],
    sections=[
        Section(
            id="headline",
            kind="kpis",
            views=["k-tickets", "k-anomalies", "k-rate", "k-resolution", "k-clusters"],
        ),
        Section(
            id="analysis",
            kind="grid",
            views=["volume", "clusters", "by-group", "trend", "by-priority", "resolution"],
        ),
        Section(id="focus", kind="table", views=["cluster-table"]),
        Section(id="records", kind="table", views=["records"]),
    ],
    hierarchy=[
        Level(id="all", label="All tickets"),
        Level(id="month", label="Month", dimension="month"),
        Level(id="pattern", label="Pattern", dimension="pattern"),
        Level(id="group", label="Assignment group", dimension="group"),
        Level(id="cluster", label="Cluster", dimension="cluster"),
        Level(id="ticket", label="Ticket", entity=True),
    ],
    evidence=Evidence(
        dimension="pattern",
        findings=[
            Finding(
                value=pattern,
                title=pattern,
                description=DESCRIPTIONS[pattern],
                metric=metric.column,
                metric_label=metric.label,
                unit=UNITS[metric.unit],
                baseline=f"{metric.column}Baseline",
                comparable_by=[{"assignmentGroup": "group"}.get(c, c) for c in metric.comparable],
                comparable_where=[Restriction(dimension="pattern", values=[NORMAL])],
            )
            for pattern, metric in METRICS.items()
        ],
        score="score",
        methodology="ticket-anomaly-detection",
        validation=[
            "Baseline: the mean of the same measure over normal tickets comparable to each "
            "anomalous one, computed when the dataset was generated.",
            "Anomaly label and score assigned at generation; nothing is re-scored when the "
            "dashboard is queried.",
            "Every figure here is an aggregate of the ticket rows listed as contributing.",
        ],
    ),
)
