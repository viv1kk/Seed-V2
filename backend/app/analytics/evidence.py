"""Why was this flagged? The evidence panel's answer (FR-EV7, §35, §57).

Given a filter context, the evidence names the finding it narrows to and
shows what makes it one:
- observed value;
- baseline;
- deviation;
- the size of the comparable population;
- the records that contribute;
- the methodology;
- how it was validated.

Every figure is an aggregate of rows (FR-EV8):
- **observed:** the mean of the finding's metric over the contributing
  records.
- **baseline:** the mean of each record's own baseline, which generation
  computed from its comparable population.
- **comparable population:** counted from the rows that match it.

A selection that spans several findings is not averaged into a
meaningless one. The panel lists them and asks which. A finding that
cannot be measured, such as an application with no usage
instrumentation, says why, as an insufficiency rather than a weaker
conclusion (PR-074).
"""

from typing import Any

import numpy as np

from app.analytics.query import FilterContext, Selection, plain
from app.analytics.store import Dataset
from app.knowledge.methodologies import BY_ID

SAMPLE = 10


def evidence(dataset: Dataset, context: FilterContext) -> dict[str, Any]:
    dashboard = dataset.dashboard
    spec = dashboard.evidence
    findings = {f.value: f for f in spec.findings}
    dimension = dashboard.dimension(spec.dimension)
    column = dimension.column
    palette = dataset.palettes.get(dimension.id, {})

    selection = Selection(dataset, context)
    rows = selection.rows("primary")
    base: dict[str, Any] = {"dimension": dimension.id, "selected": len(rows), "simulated": True}
    if not len(rows):
        return {**base, "status": "empty", "message": "Nothing matches the current selection."}

    counts = rows[column].astype(str).value_counts()
    present = [v for v in dataset.domains[dimension.id] if v in findings and counts.get(v, 0) > 0]
    if not present:
        return {
            **base,
            "status": "none",
            "message": f"No {dimension.label.lower()} in the current selection is a finding.",
        }
    if len(present) > 1:
        return {
            **base,
            "status": "choose",
            "message": f"The selection spans {len(present)} findings. Choose one to see its "
            "evidence.",
            "findings": [
                {
                    "value": value,
                    "title": findings[value].title,
                    "count": int(counts[value]),
                    "role": palette.get(value),
                    "filter": {dimension.id: [value]},
                }
                for value in present
            ],
        }

    value = present[0]
    finding = findings[value]
    contributing = rows[rows[column].astype(str) == value]
    entity = dashboard.entity.id
    if spec.score:
        contributing = contributing.sort_values(spec.score, ascending=False, kind="stable")
    records = {
        "count": len(contributing),
        "sample": [str(v) for v in contributing[entity].head(SAMPLE)],
        "filter": {**context.dimensions, dimension.id: [value]},
    }
    methodology = BY_ID[spec.methodology]
    result: dict[str, Any] = {
        **base,
        "finding": {
            "value": value,
            "title": finding.title,
            "description": finding.description,
            "role": palette.get(value),
        },
        "records": records,
        "methodology": {
            "id": methodology.id,
            "name": methodology.name,
            "process": list(methodology.process),
        },
        "validation": list(spec.validation),
        "entity": context.entity_id,
    }
    if finding.insufficient or not finding.metric:
        return {**result, "status": "insufficient", "message": finding.insufficient}

    observed = float(contributing[finding.metric].astype(float).mean())
    baseline = float(contributing[finding.baseline].astype(float).mean())
    deviation = observed / baseline - 1 if baseline else None

    # The comparable population: rows that meet the comparison's condition
    # and share a comparable value with some contributing record.
    frame = dataset.primary
    comparable = np.ones(len(frame), dtype=bool)
    for restriction in finding.comparable_where:
        hit = (
            frame[dashboard.dimension(restriction.dimension).column]
            .astype(str)
            .isin(restriction.values)
        )
        comparable &= (~hit if restriction.exclude else hit).to_numpy()
    if finding.comparable_by:
        keys = [dashboard.dimension(d).column for d in finding.comparable_by]
        cells = contributing[keys].astype(str).drop_duplicates()
        joined = frame[keys].astype(str).merge(cells, on=keys, how="left", indicator=True)
        comparable &= (joined["_merge"] == "both").to_numpy()

    return {
        **result,
        "status": "finding",
        "metric": {"label": finding.metric_label, "unit": finding.unit},
        "observed": plain(round(observed, 3)),
        "baseline": plain(round(baseline, 3)),
        "deviation": plain(round(deviation, 4)) if deviation is not None else None,
        "comparable": {
            "size": int(comparable.sum()),
            "by": [dashboard.dimension(d).label for d in finding.comparable_by],
            "where": [
                f"{dashboard.dimension(r.dimension).label} "
                f"{'is not' if r.exclude else 'is'} {', '.join(r.values)}"
                for r in finding.comparable_where
            ],
        },
        "score": plain(round(float(contributing[spec.score].mean()), 3)) if spec.score else None,
    }
