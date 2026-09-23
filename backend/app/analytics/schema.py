"""The dashboard descriptor schema: a dashboard, declared as data (D-1).

Every dashboard is one of these, served by the backend and drawn by one
generic renderer. Nothing about Ticket Anomaly Detection, licences or
applications appears in the renderer, the query engine or the API; it
appears here, in a descriptor. That is what lets a fourth methodology
arrive as a generator and a descriptor with no new UI code (FR-EV4).

The schema was designed against the hardest case first (D-1, R-6): the
Ticket Anomaly chart set of §54 and the OQ-1 inventory. It is kept
deliberately small. There are five marks (kpi, line, bar, treemap,
table), and each is expressive enough that craft is data rather than
component code:
- **visual weight and layout:** span, height, emphasis;
- **meaning:** a question each chart answers, empty states, notes;
- **colour:** semantic roles, never hex (D-5), bound to a dimension so
  one value has one colour on every chart;
- **interaction:** what a click on any datum means, declared rather than
  coded.

Validation is part of the schema. A descriptor that references a
dimension, measure, frame or view that does not exist fails when it is
built, at startup, rather than when a viewer clicks.
"""

from typing import Literal

from pydantic import Field, model_validator

from app.domain.schema import Schema

#: Semantic colour roles. The renderer resolves each to the design token
#: `--chart-<role>` at paint time, in whichever theme is showing (D-5).
Role = Literal[
    "series-1",
    "series-2",
    "series-3",
    "series-4",
    "series-5",
    "series-6",
    "series-7",
    "series-8",
    "positive",
    "warning",
    "negative",
    "anomaly",
    "baseline",
    "muted",
]
ROLES: tuple[str, ...] = Role.__args__  # type: ignore[attr-defined]
CATEGORICAL: tuple[str, ...] = tuple(r for r in ROLES if r.startswith("series-"))

#: How a number is shown. Formatting is presentation, so the renderer does
#: it; which format applies is a fact about the figure, so it is declared.
Format = Literal[
    "integer",
    "decimal",
    "percent",
    "hours",
    "days",
    "currency",
    "score",
    "lift",
    "text",
    "date",
    "datetime",
]


# -- Data ------------------------------------------------------------------


class Frame(Schema):
    """A fact table beside the primary records.

    Every dimension of the dashboard is joined onto it by the entity
    column at startup, so one filter context narrows every frame the same
    way (FR-EV1). A frame may also have dimensions of its own, such as a
    month, which filter only the views that read it.
    """

    id: str
    label: str
    dimensions: list[str] = Field(default_factory=list)


class Dimension(Schema):
    """Something the data can be grouped and filtered by."""

    id: str
    label: str
    column: str
    #: Declared order of values, where order carries meaning (priorities,
    #: bands, months). Otherwise values sort by the measure in each view.
    order: list[str] | None = None
    #: Display labels, where a stored value is not how it should read.
    labels: dict[str, str] | None = None
    #: The colour scale that colours this dimension's values, if any.
    colour: str | None = None
    #: The frame it lives in, if not every frame.
    frame: str | None = None


class ColourScale(Schema):
    """Which role each value of a dimension is drawn in.

    `fixed` assigns roles by value, for dimensions whose values mean
    something (a pattern, a class, a disposition). `ordinal` cycles the
    categorical roles over the dimension's declared order, for dimensions
    whose values are many and interchangeable (clusters). Either way a
    value has one colour everywhere it appears.
    """

    id: str
    mode: Literal["fixed", "ordinal"] = "fixed"
    roles: dict[str, Role] = Field(default_factory=dict)
    cycle: list[Role] = Field(default_factory=lambda: list(CATEGORICAL))
    fallback: Role = "muted"


class Measure(Schema):
    """A figure computed from rows by aggregation, never looked up (FR-AN5)."""

    id: str
    label: str
    agg: Literal["count", "countIf", "sum", "mean", "median", "distinct", "ratio", "lift"]
    #: The column aggregated, for every kind but count, ratio and lift.
    column: str | None = None
    #: For ratio and lift: numerator over denominator (lift subtracts one).
    numerator: str | None = None
    denominator: str | None = None
    format: Format = "integer"
    frame: str = "primary"
    #: Where a sum's column has missing values, report how many rows were
    #: left out rather than treating them as zero (PR-074).
    withhold: bool = False
    #: One line on what is excluded, shown with the figure.
    note: str | None = None


class Restriction(Schema):
    """A fixed limit on what a view reads, whatever the filter says."""

    dimension: str
    values: list[str]
    exclude: bool = False


# -- Views -----------------------------------------------------------------


class Layout(Schema):
    """Visual weight, as data (R-6)."""

    #: Columns of a twelve-column grid.
    span: int = Field(default=6, ge=1, le=12)
    height: Literal["compact", "regular", "tall"] = "regular"
    emphasis: Literal["primary", "secondary"] = "secondary"


class Kpi(Schema):
    id: str
    label: str
    measure: str
    emphasis: Literal["primary", "secondary"] = "secondary"
    #: Show the figure against the same measure with no filter applied.
    context: Literal["of-total"] | None = None
    note: str | None = None


class Series(Schema):
    """One measure drawn as its own series."""

    measure: str
    role: Role
    axis: Literal["primary", "secondary"] = "primary"


class ColourRule(Schema):
    """Colour by one dimension, refined to another once the first is fixed.

    The treemap colours by pattern until a single pattern is selected, and
    then by cluster, so the clusters of one pattern can be told apart
    (OQ-1).
    """

    by: str
    refine: str | None = None


class Interaction(Schema):
    """What clicking a datum does. The response says, per datum, exactly
    which filter it applies, so the renderer never works it out."""

    click: Literal["filter", "drill", "entity", "none"] = "filter"
    #: A line chart over time may also be brushed to a time range.
    brush: bool = False


class Chart(Schema):
    id: str
    title: str
    #: The question the chart answers, shown beneath its title.
    question: str
    mark: Literal["line", "bar", "treemap"]
    frame: str = "primary"
    #: Category axis (line, bar).
    x: str | None = None
    #: Split into one series per value of this dimension (stacked bars,
    #: one line per value).
    series: str | None = None
    #: Or one series per measure. Exactly one of `series` and a multi-entry
    #: `measures` applies.
    measures: list[Series] = Field(default_factory=list)
    #: Treemap levels, outermost first, and the measure that sizes them.
    path: list[str] = Field(default_factory=list)
    size: str | None = None
    colour: ColourRule | None = None
    orientation: Literal["vertical", "horizontal"] = "vertical"
    stacked: bool = False
    #: Show each series as shares of its own total, to compare shapes of
    #: populations of different sizes.
    normalise: bool = False
    sort: Literal["order", "value"] = "order"
    limit: int | None = None
    where: list[Restriction] = Field(default_factory=list)
    interaction: Interaction = Field(default_factory=Interaction)
    layout: Layout = Field(default_factory=Layout)
    empty: str = "Nothing matches the current selection."
    note: str | None = None


class Column(Schema):
    #: A dimension id, a measure id (summary tables) or a record column.
    field: str
    label: str
    format: Format = "text"
    #: Draw the value as a colour chip from this dimension's scale.
    chip: str | None = None
    #: Only once this dimension is fixed to one value. Cluster colours
    #: identify the clusters of one pattern; across patterns the pattern's
    #: own colour is the one that means something.
    chip_when: str | None = None
    align: Literal["left", "right"] = "left"
    #: For a summary column whose unit differs per row: take it from the
    #: row's finding (observed and baseline of different patterns).
    unit_from_finding: bool = False


class Table(Schema):
    id: str
    title: str
    question: str
    kind: Literal["summary", "records"]
    frame: str = "primary"
    #: Summary tables: the dimensions a row stands for.
    group_by: list[str] = Field(default_factory=list)
    columns: list[Column]
    sort_by: str
    descending: bool = True
    page_size: int = 10
    where: list[Restriction] = Field(default_factory=list)
    #: A summary row filters to its group; a record row opens its entity.
    row_action: Literal["filter", "entity", "none"] = "filter"
    layout: Layout = Field(default_factory=lambda: Layout(span=12))
    empty: str = "Nothing matches the current selection."


class Section(Schema):
    """One band of the page (OQ-1): KPIs, a chart grid, or a table."""

    id: str
    kind: Literal["kpis", "grid", "table"]
    title: str | None = None
    views: list[str]


# -- Drill-down and evidence ---------------------------------------------


class Level(Schema):
    """One step of a drill-down hierarchy (FR-EV3)."""

    id: str
    label: str
    dimension: str | None = None
    #: The last levels are records, then evidence.
    entity: bool = False


class Finding(Schema):
    """What a value of the finding dimension means, and how it is shown
    to deviate (FR-EV7).

    `metric` and `baseline` are record columns: the baseline is the one
    computed at generation from the comparable population, and the
    comparable population is named so its size can be counted from rows.
    A finding with no metric states why instead: an unresolved application
    is not a weaker finding, it is the absence of one.
    """

    value: str
    title: str
    description: str
    metric: str | None = None
    metric_label: str | None = None
    unit: Format = "decimal"
    baseline: str | None = None
    comparable_by: list[str] = Field(default_factory=list)
    #: The rows a baseline is drawn from.
    comparable_where: list[Restriction] = Field(default_factory=list)
    insufficient: str | None = None


class Evidence(Schema):
    dimension: str
    findings: list[Finding]
    #: A record column holding a generation-time score, if there is one.
    score: str | None = None
    methodology: str
    validation: list[str]


class Entity(Schema):
    """What one record is."""

    label: str
    plural: str
    id: str
    title: str


class Dashboard(Schema):
    solution_id: str
    title: str
    subtitle: str
    entity: Entity
    #: The record column time ranges filter on, if the data has one.
    time: str | None = None
    frames: list[Frame] = Field(default_factory=list)
    dimensions: list[Dimension]
    measures: list[Measure]
    colours: list[ColourScale] = Field(default_factory=list)
    kpis: list[Kpi]
    charts: list[Chart]
    tables: list[Table]
    sections: list[Section]
    hierarchy: list[Level]
    evidence: Evidence
    simulated: bool = True

    # -- Lookup ------------------------------------------------------

    def dimension(self, id: str) -> Dimension:
        return next(d for d in self.dimensions if d.id == id)

    def measure(self, id: str) -> Measure:
        return next(m for m in self.measures if m.id == id)

    def scale(self, id: str) -> ColourScale:
        return next(c for c in self.colours if c.id == id)

    def view(self, id: str) -> Kpi | Chart | Table:
        return next(v for v in (*self.kpis, *self.charts, *self.tables) if v.id == id)

    # -- Validation --------------------------------------------------

    @model_validator(mode="after")
    def _references_resolve(self) -> "Dashboard":
        dims = {d.id for d in self.dimensions}
        measures = {m.id for m in self.measures}
        frames = {"primary"} | {f.id for f in self.frames}
        scales = {c.id for c in self.colours}
        views = [*self.kpis, *self.charts, *self.tables]
        ids = [v.id for v in views]
        problems: list[str] = []

        def need(kind: str, value: str | None, known: set[str], where: str) -> None:
            if value is not None and value not in known:
                problems.append(f"{where}: unknown {kind} {value!r}")

        if len(ids) != len(set(ids)):
            problems.append("view ids are not unique")
        for d in self.dimensions:
            need("colour scale", d.colour, scales, f"dimension {d.id}")
            need("frame", d.frame, frames, f"dimension {d.id}")
        for m in self.measures:
            need("frame", m.frame, frames, f"measure {m.id}")
            need("measure", m.numerator, measures, f"measure {m.id}")
            need("measure", m.denominator, measures, f"measure {m.id}")
            if m.agg in ("ratio", "lift") and not (m.numerator and m.denominator):
                problems.append(f"measure {m.id}: {m.agg} needs a numerator and a denominator")
            if m.agg not in ("count", "ratio", "lift") and not m.column:
                problems.append(f"measure {m.id}: {m.agg} needs a column")
        for k in self.kpis:
            need("measure", k.measure, measures, f"kpi {k.id}")
        for c in self.charts:
            where = f"chart {c.id}"
            need("frame", c.frame, frames, where)
            for d in (c.x, c.series, *c.path, *(r.dimension for r in c.where)):
                need("dimension", d, dims, where)
            if c.colour:
                need("dimension", c.colour.by, dims, where)
                need("dimension", c.colour.refine, dims, where)
            need("measure", c.size, measures, where)
            for s in c.measures:
                need("measure", s.measure, measures, where)
            if c.mark == "treemap" and not (c.path and c.size):
                problems.append(f"{where}: a treemap needs a path and a size")
            if c.mark in ("line", "bar") and not (c.x and c.measures):
                problems.append(f"{where}: a {c.mark} needs an x dimension and a measure")
            if c.series and len(c.measures) != 1:
                problems.append(f"{where}: a split by series takes exactly one measure")
            for m in [s.measure for s in c.measures] + [c.size]:
                if m in measures and self.measure(m).frame != c.frame:
                    problems.append(f"{where}: measure {m} reads another frame")
        for t in self.tables:
            where = f"table {t.id}"
            for d in (*t.group_by, *(r.dimension for r in t.where)):
                need("dimension", d, dims, where)
            for column in t.columns:
                need("dimension", column.chip, dims, where)
                need("dimension", column.chip_when, dims, where)
                if column.chip in dims and not self.dimension(column.chip).colour:
                    problems.append(f"{where}: {column.chip} has no colour scale to chip from")
            if t.kind == "summary" and not t.group_by:
                problems.append(f"{where}: a summary table needs group_by")
        for s in self.sections:
            for v in s.views:
                need("view", v, set(ids), f"section {s.id}")
        for level in self.hierarchy:
            need("dimension", level.dimension, dims, f"level {level.id}")
        need("dimension", self.evidence.dimension, dims, "evidence")

        if problems:
            raise ValueError(f"{self.solution_id} descriptor: " + "; ".join(problems))
        return self
