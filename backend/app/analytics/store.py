"""The analytical datasets, built into memory once, at startup (FR-AN1).

Generation is deterministic and fast enough that there is no cache: all
three datasets build in well under a second (OQ-5, NFR-P1). What the store
adds to the generators' frames is the wiring every query relies on:

- every dimension of a dashboard is joined onto each secondary frame by
  the entity id, so one filter context narrows every frame alike (FR-EV1);
- every column a descriptor names is checked to exist, so a descriptor
  that names a missing column fails here, at startup, not in front of a
  viewer;
- each dimension's domain and each coloured value's role are resolved
  once, for legends and chips.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.analytics.descriptors import SOURCES
from app.analytics.generator import CALIBRATIONS, COLLECTED, EVERY, STEPS
from app.analytics.schema import ColourScale, Dashboard

#: A value of a collection's confirm dimension is confirmed when its
#: collected records score at least this on average.
CONFIRMED = 0.8


class UnknownDashboard(KeyError):
    pass


@dataclass
class Dataset:
    dashboard: Dashboard
    frames: dict[str, pd.DataFrame]
    #: Each dimension's values, in display order.
    domains: dict[str, list[str]] = field(default_factory=dict)
    #: For coloured dimensions: each value's role.
    palettes: dict[str, dict[str, str]] = field(default_factory=dict)
    #: Entity id to row position in the primary frame.
    positions: dict[str, int] = field(default_factory=dict)
    #: Life's recalibrations (D-17): for each, the columns that differ from
    #: the generated frames. The last is the generated frames themselves.
    calibrations: list[dict[str, dict[str, np.ndarray]]] = field(default_factory=list)
    #: Life's plan, precomputed: arrivals per step, and what each
    #: recalibration moved.
    arrivals: list[int] = field(default_factory=list)
    recalibrations: list[dict] = field(default_factory=list)
    _calibrated: dict[int, dict[str, pd.DataFrame]] = field(default_factory=dict, repr=False)

    @property
    def primary(self) -> pd.DataFrame:
        return self.frames["primary"]

    def at(self, calibration: int) -> dict[str, pd.DataFrame]:
        """The frames as a calibration saw them.

        Shallow copies with the recalibrated columns swapped in: every
        other column is the generated one, shared rather than copied.
        """
        changes = self.calibrations[calibration] if calibration < len(self.calibrations) else {}
        if not changes:
            return self.frames
        if calibration not in self._calibrated:
            frames = dict(self.frames)
            for frame_id, columns in changes.items():
                frame = frames[frame_id].copy(deep=False)
                for column, values in columns.items():
                    frame[column] = values
                frames[frame_id] = frame
            self._calibrated[calibration] = frames
        return self._calibrated[calibration]


def roles_for(scale: ColourScale, values: list[str]) -> dict[str, str]:
    if scale.mode == "fixed":
        return {v: scale.roles.get(v, scale.fallback) for v in values}
    return {v: scale.cycle[i % len(scale.cycle)] for i, v in enumerate(values)}


def _domain(frame: pd.DataFrame, column: str, order: list[str] | None) -> list[str]:
    series = frame[column]
    if order is not None:
        return list(order)
    if isinstance(series.dtype, pd.CategoricalDtype):
        present = set(series.cat.categories[np.unique(series.cat.codes[series.cat.codes >= 0])])
        return [str(v) for v in series.cat.categories if v in present]
    return sorted(str(v) for v in series.dropna().unique())


def build(source) -> Dataset:
    dashboard: Dashboard = source.dashboard
    frames = source.generate()
    primary = frames["primary"]
    entity = dashboard.entity.id
    problems: list[str] = []

    shared = [d for d in dashboard.dimensions if d.frame is None]
    for frame_id, frame in frames.items():
        if frame_id == "primary":
            continue
        position = pd.Index(primary[entity]).get_indexer(frame[entity])
        if (position < 0).any():
            problems.append(f"frame {frame_id} has rows with no {entity} in the primary frame")
        for dimension in shared:
            if dimension.column not in frame:
                frame[dimension.column] = primary[dimension.column].take(position).to_numpy()
                if isinstance(primary[dimension.column].dtype, pd.CategoricalDtype):
                    frame[dimension.column] = pd.Categorical(
                        frame[dimension.column],
                        categories=primary[dimension.column].cat.categories,
                    )

    def has(frame_id: str, column: str, where: str) -> None:
        if column not in frames.get(frame_id, pd.DataFrame()):
            problems.append(f"{where}: no column {column!r} in frame {frame_id}")

    for dimension in dashboard.dimensions:
        for frame_id in [dimension.frame] if dimension.frame else list(frames):
            has(frame_id, dimension.column, f"dimension {dimension.id}")
    for measure in dashboard.measures:
        if measure.column:
            has(measure.frame, measure.column, f"measure {measure.id}")
    dims = {d.id for d in dashboard.dimensions}
    measures = {m.id for m in dashboard.measures}
    for table in dashboard.tables:
        for column in table.columns:
            dimension = next((d for d in dashboard.dimensions if d.id == column.field), None)
            if (
                table.kind == "records"
                and dimension
                and dimension.column != column.field
                and column.field in frames[table.frame]
            ):
                problems.append(
                    f"table {table.id}: {column.field!r} is both a dimension and another column"
                )
            if column.field in dims or (table.kind == "summary" and column.field in measures):
                continue
            has(table.frame, column.field, f"table {table.id}")
        if table.kind == "records" and table.sort_by not in dims:
            has(table.frame, table.sort_by, f"table {table.id} sort")
    for finding in dashboard.evidence.findings:
        for column in (finding.metric, finding.baseline):
            if column:
                has("primary", column, f"finding {finding.value}")
    if dashboard.evidence.score:
        has("primary", dashboard.evidence.score, "evidence score")
    if dashboard.time:
        has("primary", dashboard.time, "time")
    if problems:
        raise ValueError(f"{dashboard.solution_id} dataset: " + "; ".join(problems))

    dataset = Dataset(dashboard=dashboard, frames=frames)
    for dimension in dashboard.dimensions:
        frame = frames[dimension.frame or "primary"]
        values = _domain(frame, dimension.column, dimension.order)
        dataset.domains[dimension.id] = values
        if dimension.colour:
            dataset.palettes[dimension.id] = roles_for(dashboard.scale(dimension.colour), values)
    dataset.positions = {str(v): i for i, v in enumerate(primary[entity].tolist())}
    if dashboard.collection:
        dataset.calibrations = source.calibrate(frames) if source.calibrate else [{}] * CALIBRATIONS
        if len(dataset.calibrations) != CALIBRATIONS or dataset.calibrations[-1]:
            raise ValueError(
                f"{dashboard.solution_id}: {CALIBRATIONS} calibrations, the last the generated frames"
            )
        _plan(dataset)
    return dataset


def _plan(dataset: Dataset) -> None:
    """Life's plan: what arrives at each step, and what each recalibration moves.

    Counted from rows, once, so the stream reports what the dashboards
    will show (FR-LF4, FR-LF6).
    """
    dashboard = dataset.dashboard
    spec = dashboard.collection
    collected = dataset.frames[spec.frame][COLLECTED].to_numpy()
    dataset.arrivals = np.bincount(collected, minlength=STEPS + 1).tolist()

    evidence = dashboard.evidence
    column = dashboard.dimension(evidence.dimension).column

    def confirmed(c: int) -> set[str]:
        if not spec.confirm or not evidence.score:
            return set()
        frame = dataset.at(c)["primary"]
        seen = frame[frame[COLLECTED] <= c * EVERY]
        key = dashboard.dimension(spec.confirm).column
        scores = seen.groupby(key, observed=True)[evidence.score].mean()
        return {str(v) for v, s in scores.items() if s >= CONFIRMED}

    def baselines(c: int) -> dict[str, float]:
        frame = dataset.at(c)["primary"]
        seen = frame[frame[COLLECTED] <= c * EVERY]
        values = {}
        for finding in evidence.findings:
            if finding.baseline:
                rows = seen[seen[column] == finding.value]
                if len(rows):
                    values[finding.value] = float(rows[finding.baseline].astype(float).mean())
        return values

    order = {v: i for i, v in enumerate(dataset.domains.get(spec.confirm or "", []))}
    before, held = baselines(0), confirmed(0)
    dataset.recalibrations = []
    for c in range(1, CALIBRATIONS):
        after, now = baselines(c), confirmed(c)
        moved = [
            (abs(after[v] - before[v]) / before[v], v)
            for v in after
            if v in before and before[v] and round(after[v], 2) != round(before[v], 2)
        ]
        baseline = None
        if moved:
            _, value = max(moved)
            finding = next(f for f in evidence.findings if f.value == value)
            baseline = {
                "finding": value,
                "metric": finding.metric_label,
                "unit": finding.unit,
                "from": round(before[value], 2),
                "to": round(after[value], 2),
            }
        dataset.recalibrations.append(
            {
                "calibration": c,
                "step": c * EVERY,
                "baseline": baseline,
                "confirmed": sorted(now - held, key=lambda v: order.get(v, 0)),
                "withdrawn": sorted(held - now, key=lambda v: order.get(v, 0)),
            }
        )
        before, held = after, now


def build_all() -> dict[str, Dataset]:
    return {source.dashboard.solution_id: build(source) for source in SOURCES}


class Store:
    """Built on first use and kept for the life of the process.

    The API imports this at startup, so the build happens before the
    launcher reports readiness (A-1) rather than on the first request.
    """

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] | None = None

    @property
    def datasets(self) -> dict[str, Dataset]:
        if self._datasets is None:
            self._datasets = build_all()
        return self._datasets

    def get(self, solution_id: str) -> Dataset:
        try:
            return self.datasets[solution_id]
        except KeyError as error:
            raise UnknownDashboard(f"No dashboard for {solution_id!r}.") from error


STORE = Store()
