"""The query engine: a filter context in, every view's figures out.

One filter context drives every view on a dashboard (FR-EV1). Any
combination is answered, because every figure is aggregated from the
record-level rows at request time rather than read from a table of
precomputed answers (FR-EV2, FR-AN5, §83.3). The frontend receives
figures, labels, colour roles and, for every datum it can click, the exact
filter that clicking applies. It does no analysis of its own.

Nothing here names a methodology. Everything specific arrives in the
descriptor (FR-EV4).
"""

import datetime as dt
import math
from typing import Any

import numpy as np
import pandas as pd
from pydantic import Field

from app.analytics.schema import Chart, Dashboard, Kpi, Measure, Restriction, Table
from app.analytics.store import Dataset
from app.domain.schema import Schema


class QueryError(ValueError):
    """A request the descriptor cannot answer: an unknown view or dimension."""


class FilterContext(Schema):
    """What the viewer has selected (FR-EV1).

    Values within one dimension are alternatives; dimensions combine. The
    time range is inclusive of both dates.
    """

    time_range: tuple[dt.date, dt.date] | None = None
    dimensions: dict[str, list[str]] = Field(default_factory=dict)
    entity_id: str | None = None


# -- Values ------------------------------------------------------------


def plain(value: Any) -> Any:
    """A JSON-safe scalar: numpy to Python, NaN and infinity to None."""
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (pd.Timestamp, dt.datetime, np.datetime64)):
        stamp = pd.Timestamp(value)
        return None if pd.isna(stamp) else stamp.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return value if isinstance(value, (int, str)) else str(value)


# -- Selection ---------------------------------------------------------


def _isin(series: pd.Series, values: list[str]) -> np.ndarray:
    if isinstance(series.dtype, pd.CategoricalDtype):
        wanted = series.cat.categories.get_indexer(values)
        return np.isin(series.cat.codes.to_numpy(), wanted[wanted >= 0])
    return series.isin(values).to_numpy()


class Selection:
    """The rows of each frame that a filter context selects.

    Masks are computed once per frame and restriction set and reused by
    every view in the request.
    """

    def __init__(self, dataset: Dataset, context: FilterContext) -> None:
        self.dataset = dataset
        self.dashboard = dataset.dashboard
        self.context = context
        self._masks: dict[tuple, tuple[np.ndarray, list[str]]] = {}
        known = {d.id for d in self.dashboard.dimensions}
        unknown = sorted(set(context.dimensions) - known)
        if unknown:
            raise QueryError(f"Unknown dimension {', '.join(unknown)}.")

    def mask(
        self, frame_id: str, where: list[Restriction] = (), apply: bool = True
    ) -> tuple[np.ndarray, list[str]]:
        """The rows selected, and which filtered dimensions did not apply.

        A dimension that lives in another frame (a month in a monthly
        activity table) cannot narrow this one, and the view says so
        rather than silently showing a figure the filter did not touch.
        """
        key = (frame_id, tuple((r.dimension, tuple(r.values), r.exclude) for r in where), apply)
        if key in self._masks:
            return self._masks[key]

        frame = self.dataset.frames[frame_id]
        selected = np.ones(len(frame), dtype=bool)
        ignored: list[str] = []
        if apply:
            for dim_id, values in self.context.dimensions.items():
                if not values:
                    continue
                dimension = self.dashboard.dimension(dim_id)
                if dimension.frame and dimension.frame != frame_id:
                    ignored.append(dim_id)
                    continue
                selected &= _isin(frame[dimension.column], values)
            if self.context.time_range:
                time = self.dashboard.time
                if time and time in frame:
                    start, end = self.context.time_range
                    stamps = frame[time]
                    selected &= (stamps >= pd.Timestamp(start)).to_numpy()
                    selected &= (stamps < pd.Timestamp(end) + pd.Timedelta(days=1)).to_numpy()
                else:
                    ignored.append("time")
            if self.context.entity_id is not None:
                if frame_id == "primary":
                    one = np.zeros(len(frame), dtype=bool)
                    position = self.dataset.positions.get(self.context.entity_id)
                    if position is not None:
                        one[position] = True
                    selected &= one
                else:
                    column = frame[self.dashboard.entity.id]
                    selected &= (column == self.context.entity_id).to_numpy()
        for restriction in where:
            dimension = self.dashboard.dimension(restriction.dimension)
            hit = _isin(frame[dimension.column], restriction.values)
            selected &= ~hit if restriction.exclude else hit

        self._masks[key] = (selected, ignored)
        return selected, ignored

    def rows(
        self, frame_id: str, where: list[Restriction] = (), apply: bool = True
    ) -> pd.DataFrame:
        selected, _ = self.mask(frame_id, where, apply)
        return self.dataset.frames[frame_id][selected]

    def single(self, dim_id: str) -> str | None:
        values = self.context.dimensions.get(dim_id) or []
        return values[0] if len(values) == 1 else None


# -- Aggregation -------------------------------------------------------


def aggregate(
    rows: pd.DataFrame, measure: Measure, dashboard: Dashboard, by: list[str] | None = None
):
    """One measure over rows, optionally per group of `by` columns.

    Returns a scalar without `by`, a Series indexed by the groups with it.
    Ratio and lift are computed from their parts, so a rate is always the
    quotient of the two figures it is shown beside.
    """
    if measure.agg in ("ratio", "lift"):
        numerator = aggregate(rows, dashboard.measure(measure.numerator), dashboard, by)
        denominator = aggregate(rows, dashboard.measure(measure.denominator), dashboard, by)
        if by is None:
            value = numerator / denominator if denominator else np.nan
            return value - 1 if measure.agg == "lift" and not pd.isna(value) else value
        quotient = numerator / denominator.replace(0, np.nan)
        return quotient - 1 if measure.agg == "lift" else quotient

    if by is None:
        if measure.agg == "count":
            return len(rows)
        column = rows[measure.column]
        return {
            "countIf": lambda: int(column.sum()),
            "sum": lambda: float(column.sum()),
            "mean": lambda: float(column.mean()) if len(column.dropna()) else np.nan,
            "median": lambda: float(column.median()) if len(column.dropna()) else np.nan,
            "distinct": lambda: int(column.nunique()),
        }[measure.agg]()

    grouped = rows.groupby(by, observed=True, sort=False)
    if measure.agg == "count":
        return grouped.size()
    column = grouped[measure.column]
    return {
        "countIf": column.sum,
        "sum": column.sum,
        "mean": column.mean,
        "median": column.median,
        "distinct": column.nunique,
    }[measure.agg]()


def withheld(rows: pd.DataFrame, measure: Measure) -> int | None:
    """Rows a withholding sum left out because their value is missing."""
    if not measure.withhold or not measure.column:
        return None
    return int(rows[measure.column].isna().sum())


# -- Views -------------------------------------------------------------


class Engine:
    def __init__(self, dataset: Dataset, context: FilterContext) -> None:
        self.dataset = dataset
        self.dashboard = dataset.dashboard
        self.selection = Selection(dataset, context)
        self.context = context

    # -- helpers -------------------------------------------------------

    def _label(self, dim_id: str, value: str) -> str:
        labels = self.dashboard.dimension(dim_id).labels or {}
        return labels.get(value, value)

    def _role(self, dim_id: str, value: str) -> str | None:
        return self.dataset.palettes.get(dim_id, {}).get(value)

    def _column(self, dim_id: str) -> str:
        return self.dashboard.dimension(dim_id).column

    def _clickable(self, chart: Chart) -> bool:
        return chart.interaction.click in ("filter", "drill")

    # -- dispatch ------------------------------------------------------

    def view(self, view_id: str) -> dict[str, Any]:
        try:
            view = self.dashboard.view(view_id)
        except StopIteration as error:
            raise QueryError(f"Unknown view {view_id!r}.") from error
        if isinstance(view, Kpi):
            return self.kpi(view)
        if isinstance(view, Chart):
            return self.treemap(view) if view.mark == "treemap" else self.series_chart(view)
        return self.table(view)

    # -- KPI -----------------------------------------------------------

    def kpi(self, kpi: Kpi) -> dict[str, Any]:
        measure = self.dashboard.measure(kpi.measure)
        rows = self.selection.rows(measure.frame)
        _, ignored = self.selection.mask(measure.frame)
        result = {
            "id": kpi.id,
            "value": plain(aggregate(rows, measure, self.dashboard)),
            "withheld": withheld(rows, measure),
            "ignored": ignored,
        }
        if kpi.context == "of-total":
            everything = self.dataset.frames[measure.frame]
            result["total"] = plain(aggregate(everything, measure, self.dashboard))
        return result

    # -- Line and bar --------------------------------------------------

    def series_chart(self, chart: Chart) -> dict[str, Any]:
        rows = self.selection.rows(chart.frame, chart.where)
        _, ignored = self.selection.mask(chart.frame, chart.where)
        x = chart.x
        x_column = self._column(x)
        dimension = self.dashboard.dimension(x)
        domain = self.dataset.domains[x]

        series: list[dict[str, Any]] = []
        if chart.series:
            measure = self.dashboard.measure(chart.measures[0].measure)
            s_column = self._column(chart.series)
            table = aggregate(rows, measure, self.dashboard, [x_column, s_column])
            table = table.unstack(s_column) if len(table) else pd.DataFrame()
            if measure.agg in ("count", "countIf", "sum"):
                # A combination with no rows is a count of nought, not a gap.
                table = table.fillna(0)
            present = set(table.columns.astype(str)) if len(table.columns) else set()
            for key in [v for v in self.dataset.domains[chart.series] if v in present]:
                values = table[key]
                values.index = values.index.astype(str)
                series.append(
                    {
                        "key": key,
                        "label": self._label(chart.series, key),
                        "role": self._role(chart.series, key) or chart.measures[0].role,
                        "axis": "primary",
                        "measure": measure.id,
                        "values": values,
                        "filter": {chart.series: [key]} if self._clickable(chart) else None,
                    }
                )
        else:
            for spec in chart.measures:
                measure = self.dashboard.measure(spec.measure)
                values = aggregate(rows, measure, self.dashboard, [x_column])
                values.index = values.index.astype(str)
                series.append(
                    {
                        "key": measure.id,
                        "label": measure.label,
                        "role": spec.role,
                        "axis": spec.axis,
                        "measure": measure.id,
                        "values": values,
                        "filter": None,
                    }
                )

        # Categories: the declared order in full where order means
        # something (every month, every priority), otherwise what is present.
        present = set().union(*(set(s["values"].index) for s in series)) if series else set()
        if dimension.order is not None:
            keys = list(domain)
        else:
            keys = [v for v in domain if v in present]
        additive = all(
            self.dashboard.measure(s["measure"]).agg in ("count", "countIf", "sum") for s in series
        )
        if chart.normalise:
            for s in series:
                total = s["values"].sum()
                s["values"] = s["values"] / total if total else s["values"] * 0
        if chart.sort == "value":
            weight = {k: 0.0 for k in keys}
            for s in series:
                for k, v in s["values"].items():
                    if k in weight and not pd.isna(v):
                        weight[k] += float(v) if additive else max(weight[k], float(v))
            keys = sorted(keys, key=lambda k: -weight[k])
            keys = [k for k in keys if weight[k] != 0 or dimension.order is not None]
        truncated = 0
        if chart.limit and len(keys) > chart.limit:
            truncated = len(keys) - chart.limit
            keys = keys[: chart.limit]

        roles = None
        if chart.colour and not chart.series:
            if chart.colour.by == x:
                roles = [self._role(x, k) for k in keys]
            else:
                by = self._column(chart.colour.by)
                first = rows.groupby(x_column, observed=True)[by].first()
                first.index = first.index.astype(str)
                roles = [self._role(chart.colour.by, str(first.get(k))) for k in keys]

        # A bar is drawn only where its figure is complete. A group with
        # rows a withholding sum could not value is withheld outright, since
        # a partial bar beside complete ones would compare unlike with like.
        withheld_by: list[int] | None = None
        for s in series:
            measure = self.dashboard.measure(s["measure"])
            missing = None
            if measure.withhold and not chart.series:
                missing = rows[measure.column].isna().groupby(rows[x_column], observed=True).sum()
                missing.index = missing.index.astype(str)
                withheld_by = [int(missing.get(k, 0)) for k in keys]
            empty = (
                0 if (measure.agg in ("count", "countIf", "sum") and not chart.normalise) else None
            )
            fill = 0.0 if chart.normalise else empty
            s["values"] = [
                None
                if missing is not None and missing.get(k, 0)
                else plain(s["values"].get(k, fill))
                for k in keys
            ]
            s.pop("measure")

        return {
            "id": chart.id,
            "mark": chart.mark,
            "categories": [
                {
                    "key": k,
                    "label": self._label(x, k),
                    "filter": {x: [k]} if self._clickable(chart) else None,
                }
                for k in keys
            ],
            "series": series,
            "roles": roles,
            "withheld": withheld_by,
            "truncated": truncated,
            "empty": len(rows) == 0,
            "ignored": ignored,
        }

    # -- Treemap -------------------------------------------------------

    def treemap(self, chart: Chart) -> dict[str, Any]:
        rows = self.selection.rows(chart.frame, chart.where)
        _, ignored = self.selection.mask(chart.frame, chart.where)
        measure = self.dashboard.measure(chart.size)
        path = chart.path
        columns = [self._column(d) for d in path]
        base = {"id": chart.id, "mark": "treemap", "ignored": ignored}

        colour = chart.colour.by if chart.colour else None
        if chart.colour and chart.colour.refine and self.selection.single(chart.colour.by):
            colour = chart.colour.refine
        base["colourBy"] = colour
        if not len(rows):
            return {**base, "nodes": [], "total": 0, "empty": True}

        # The leaf table: one row per full path, with its size and, where
        # colour is not on the path, the colour value its rows share.
        leaves = aggregate(rows, measure, self.dashboard, columns).rename("value").reset_index()
        colour_column = self._column(colour) if colour else None
        if colour and colour not in path:
            shared = rows.groupby(columns, observed=True)[colour_column].agg(["first", "nunique"])
            shared = shared.reset_index()
            leaves = leaves.merge(shared, on=columns, how="left")
            leaves["shade"] = np.where(leaves["nunique"] == 1, leaves["first"].astype(str), None)
        for column in columns:
            leaves[column] = leaves[column].astype(str)
        leaves = leaves[leaves["value"] > 0]

        def build(part: pd.DataFrame, prefix: tuple[str, ...], depth: int) -> list[dict[str, Any]]:
            column = columns[depth]
            totals = (
                part.groupby(column, sort=False)["value"]
                .sum()
                .sort_values(ascending=False, kind="stable")
            )
            if chart.limit:
                totals = totals.iloc[: chart.limit]
            nodes = []
            for value, size in totals.items():
                key = (*prefix, value)
                below = part[part[column] == value]
                if colour in path[: depth + 1]:
                    shade = key[path.index(colour)]
                elif colour and colour not in path:
                    shades = set(below["shade"])
                    shade = shades.pop() if len(shades) == 1 else None
                else:
                    shade = None
                nodes.append(
                    {
                        "key": "/".join(key),
                        "label": self._label(path[depth], value),
                        "value": plain(size),
                        "role": self._role(colour, shade) if shade else None,
                        "colourValue": shade,
                        "filter": {d: [v] for d, v in zip(path, key)}
                        if self._clickable(chart)
                        else None,
                        "children": build(below, key, depth + 1) if depth + 1 < len(path) else [],
                    }
                )
            return nodes

        return {
            **base,
            "nodes": build(leaves, (), 0),
            "total": plain(leaves["value"].sum()),
            "empty": False,
        }

    # -- Tables --------------------------------------------------------

    def table(
        self,
        table: Table,
        page: int = 0,
        sort_by: str | None = None,
        descending: bool | None = None,
    ) -> dict[str, Any]:
        if table.kind == "summary":
            return self.summary(table)
        return self.records(table, page, sort_by, descending)

    def summary(self, table: Table) -> dict[str, Any]:
        rows = self.selection.rows(table.frame, table.where)
        _, ignored = self.selection.mask(table.frame, table.where)
        keys = [self._column(d) for d in table.group_by]
        dims = {d.id for d in self.dashboard.dimensions}
        measures = {m.id for m in self.dashboard.measures}
        if not len(rows):
            return {"id": table.id, "kind": "summary", "rows": [], "total": 0, "ignored": ignored}

        grouped = rows.groupby(keys, observed=True, sort=False)
        frame = pd.DataFrame(index=grouped.size().index)
        for column in table.columns:
            if column.field in table.group_by:
                continue
            if column.field in measures:
                measure = self.dashboard.measure(column.field)
                values = aggregate(rows, measure, self.dashboard, keys)
                if measure.withhold:
                    missing = grouped[measure.column].apply(lambda c: c.isna().any())
                    values = values.where(~missing)
                frame[column.field] = values
            elif column.field in dims:
                frame[column.field] = grouped[self._column(column.field)].first().astype(str)
            else:
                frame[column.field] = grouped[column.field].first()
        sort = table.sort_by
        if sort in frame:
            frame = frame.sort_values(sort, ascending=not table.descending, kind="stable")

        evidence = self.dashboard.evidence
        findings = {f.value: f for f in evidence.findings}
        finding_column = self._column(evidence.dimension)
        finding_of = grouped[finding_column].first().astype(str) if finding_column in rows else None
        needs_unit = any(c.unit_from_finding for c in table.columns)

        out = []
        for index, record in frame.head(table.page_size).iterrows():
            key = index if isinstance(index, tuple) else (index,)
            key = tuple(str(k) for k in key)
            cells = {d: key[i] for i, d in enumerate(table.group_by)}
            cells.update({c: plain(record[c]) for c in frame.columns})
            row = {
                "key": "/".join(key),
                "cells": cells,
                "filter": {d: [key[i]] for i, d in enumerate(table.group_by)},
            }
            if needs_unit and finding_of is not None:
                finding = findings.get(str(finding_of.loc[index]))
                row["unit"] = finding.unit if finding else None
                row["metricLabel"] = finding.metric_label if finding else None
            out.append(row)
        return {
            "id": table.id,
            "kind": "summary",
            "rows": out,
            "total": len(frame),
            "ignored": ignored,
        }

    def records(
        self,
        table: Table,
        page: int = 0,
        sort_by: str | None = None,
        descending: bool | None = None,
    ) -> dict[str, Any]:
        rows = self.selection.rows(table.frame, table.where)
        _, ignored = self.selection.mask(table.frame, table.where)
        dims = {d.id: d.column for d in self.dashboard.dimensions}
        sort = sort_by or table.sort_by
        sort_column = dims.get(sort, sort)
        if sort_column not in rows:
            raise QueryError(f"Cannot sort {table.id} by {sort!r}.")
        down = table.descending if descending is None else descending

        values = rows[sort_column]
        if isinstance(values.dtype, pd.CategoricalDtype):
            values = values.astype(str)
        order = values.sort_values(ascending=not down, kind="stable", na_position="last").index
        start = page * table.page_size
        chosen = rows.loc[order[start : start + table.page_size]]

        entity = self.dashboard.entity.id
        out = [
            {
                "id": str(record[entity]),
                "cells": {
                    c.field: plain(record[dims.get(c.field, c.field)]) for c in table.columns
                },
            }
            for _, record in chosen.iterrows()
        ]
        return {
            "id": table.id,
            "kind": "records",
            "rows": out,
            "total": len(rows),
            "page": page,
            "pageSize": table.page_size,
            "sortBy": sort,
            "descending": down,
            "ignored": ignored,
        }

    # -- Drill ---------------------------------------------------------

    def drill(self) -> dict[str, Any]:
        """Where the filter context stands in the hierarchy (FR-EV3).

        A level is reached when its dimension is fixed to one value, or,
        for the record level, when an entity is selected. The breadcrumb
        itself is the frontend's ordered list of filter deltas (D-3); this
        says which levels those deltas have reached and which comes next.
        """
        levels = []
        for level in self.dashboard.hierarchy[1:]:
            if level.entity:
                value = self.context.entity_id
                label = value
            else:
                value = self.selection.single(level.dimension)
                label = self._label(level.dimension, value) if value else None
            levels.append(
                {
                    "id": level.id,
                    "label": level.label,
                    "dimension": level.dimension,
                    "value": value,
                    "valueLabel": label,
                }
            )
        # The next level is the first one below the deepest reached, so a
        # viewer who went straight to a cluster is offered its tickets, not
        # the month they skipped.
        reached = [i for i, level in enumerate(levels) if level["value"] is not None]
        start = reached[-1] + 1 if reached else 0
        following = next((level["id"] for level in levels[start:] if level["value"] is None), None)
        return {"root": self.dashboard.hierarchy[0].label, "levels": levels, "next": following}


def run(dataset: Dataset, context: FilterContext, views: list[str] | None = None) -> dict[str, Any]:
    engine = Engine(dataset, context)
    wanted = views or [
        v.id
        for v in (*dataset.dashboard.kpis, *dataset.dashboard.charts, *dataset.dashboard.tables)
    ]
    return {
        "views": {view_id: engine.view(view_id) for view_id in wanted},
        "drill": engine.drill(),
    }
