"""ServiceNow incidents for Ticket Anomaly Detection.

184,392 tickets over twelve months, of which 1,842 are anomalous: the
§31 figures, true counts of this dataset rather than decoration (FR-AN4).
Every anomaly belongs to one of 31 planted clusters, and every cluster to
one of five patterns (OQ-1). Normal tickets are drawn from
per-category, per-priority distributions; clusters are drawn to deviate
from them in one specific way each.

What is computed here, at generation (FR-AN3):
- each ticket's anomaly label, pattern, cluster and score;
- for each pattern's metric, the baseline a ticket is judged against: the
  mean of that metric over the *normal* tickets comparable to it, where
  comparable is declared per metric in `METRICS`.

So when the evidence panel says a cluster averaged 7.2 assignment groups
against a baseline of 2.1, both figures are aggregates of rows in this
frame, and the baseline is the one the ticket was labelled against.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analytics.generator import (
    CALIBRATIONS,
    COLLECTED,
    END,
    EVERY,
    MONTHS,
    START,
    allocate,
    step_of,
)

SEED = 20260623

TOTAL = 184_392
ANOMALIES = 1_842

PRIORITIES = ("P1", "P2", "P3", "P4")
PRIORITY_SHARE = np.array([0.02, 0.10, 0.48, 0.40])
#: Median resolution hours of a normal ticket, by priority.
PRIORITY_HOURS = np.array([2.5, 7.0, 22.0, 46.0])

#: Category, share of volume, resolution factor, CI prefix, CI pool size,
#: and the assignment groups that work it with their shares.
CATEGORIES: tuple[tuple[str, float, float, str, int, tuple[tuple[str, float], ...]], ...] = (
    ("Network", 0.14, 0.9, "netsw", 60, (("Network Operations", 1.0),)),
    ("Access", 0.18, 0.6, "idp", 40, (("Identity & Access", 0.55), ("Service Desk", 0.45))),
    ("Hardware", 0.12, 1.4, "lap", 180, (("End User Computing", 1.0),)),
    ("Software", 0.16, 1.0, "pkg", 150, (("End User Computing", 0.6), ("Service Desk", 0.4))),
    ("Email", 0.07, 0.7, "mail", 20, (("Messaging", 1.0),)),
    ("Database", 0.06, 1.2, "sqldb", 45, (("Database Services", 1.0),)),
    (
        "Application",
        0.17,
        1.3,
        "svc",
        120,
        (
            ("Application Support - SAP", 0.4),
            ("Application Support - LMS", 0.3),
            ("Application Support - Portal", 0.3),
        ),
    ),
    ("Security", 0.04, 1.1, "sec", 30, (("Security Operations", 1.0),)),
    ("Cloud", 0.06, 1.0, "vm", 90, (("Cloud Platform", 0.6), ("Infrastructure", 0.4))),
)

#: Mean extra assignment groups a normal ticket passes through, by group.
REASSIGNMENT_RATE = {
    "Network Operations": 1.1,
    "Identity & Access": 0.7,
    "Service Desk": 1.2,
    "End User Computing": 0.8,
    "Messaging": 0.6,
    "Database Services": 0.9,
    "Application Support - SAP": 1.0,
    "Application Support - LMS": 0.9,
    "Application Support - Portal": 1.0,
    "Security Operations": 0.8,
    "Cloud Platform": 0.9,
    "Infrastructure": 1.0,
}
GROUPS = tuple(REASSIGNMENT_RATE)

BANDS = ("Under 4 h", "4-8 h", "8-24 h", "1-3 days", "3-7 days", "Over 7 days")
BAND_EDGES = (0, 4, 8, 24, 72, 168, np.inf)

NORMAL = "Normal"
PATTERNS = (
    "Resolution stall",
    "Reopen churn",
    "Priority mismatch",
    "Volume burst",
    "Reassignment loop",
)


@dataclass(frozen=True)
class Metric:
    """The measurement a pattern deviates on, and what it is compared with."""

    column: str
    label: str
    unit: str
    comparable: tuple[str, ...]


#: One metric per pattern. `comparable` names the columns whose values a
#: normal ticket must share with the ticket it is a baseline for.
METRICS: dict[str, Metric] = {
    "Resolution stall": Metric(
        "resolutionHours", "Resolution time", "hours", ("category", "priority")
    ),
    "Reopen churn": Metric("reopens", "Reopens", "count", ("category", "priority")),
    "Priority mismatch": Metric(
        "priorityChanges", "Priority changes", "count", ("category", "priority")
    ),
    "Volume burst": Metric(
        "ciDayVolume", "Tickets on the same CI that day", "count", ("category",)
    ),
    "Reassignment loop": Metric(
        "reassignments", "Assignment groups", "count", ("assignmentGroup",)
    ),
}

#: The planted clusters: pattern, category, group, month and relative size.
#: Numbered in this order, so Cluster 27 is the Network Operations
#: reassignment loop of §35.
CLUSTERS: tuple[tuple[str, str, str, str, float], ...] = (
    ("Resolution stall", "Database", "Database Services", "2025-10", 1.2),
    ("Resolution stall", "Application", "Application Support - SAP", "2025-12", 1.0),
    ("Resolution stall", "Hardware", "End User Computing", "2026-01", 0.9),
    ("Resolution stall", "Cloud", "Infrastructure", "2026-03", 1.0),
    ("Resolution stall", "Application", "Application Support - LMS", "2026-04", 1.1),
    ("Resolution stall", "Software", "Service Desk", "2026-06", 0.8),
    ("Resolution stall", "Security", "Security Operations", "2026-08", 0.7),
    ("Reopen churn", "Email", "Messaging", "2025-09", 1.0),
    ("Reopen churn", "Software", "End User Computing", "2025-11", 1.1),
    ("Reopen churn", "Access", "Service Desk", "2026-02", 1.2),
    ("Reopen churn", "Application", "Application Support - Portal", "2026-05", 0.9),
    ("Reopen churn", "Hardware", "End User Computing", "2026-07", 0.8),
    ("Reopen churn", "Access", "Identity & Access", "2026-08", 1.0),
    ("Priority mismatch", "Network", "Network Operations", "2025-10", 1.0),
    ("Priority mismatch", "Access", "Service Desk", "2026-01", 1.1),
    ("Priority mismatch", "Application", "Application Support - SAP", "2026-03", 0.9),
    ("Priority mismatch", "Cloud", "Cloud Platform", "2026-05", 1.0),
    ("Priority mismatch", "Email", "Messaging", "2026-07", 0.8),
    ("Volume burst", "Network", "Network Operations", "2025-11", 1.3),
    ("Volume burst", "Email", "Messaging", "2026-02", 0.9),
    ("Volume burst", "Access", "Identity & Access", "2026-04", 1.2),
    ("Volume burst", "Cloud", "Cloud Platform", "2026-06", 0.8),
    ("Volume burst", "Application", "Application Support - LMS", "2026-08", 0.8),
    ("Reassignment loop", "Access", "Service Desk", "2025-09", 0.9),
    ("Reassignment loop", "Application", "Application Support - SAP", "2025-12", 1.0),
    ("Reassignment loop", "Database", "Database Services", "2026-02", 0.8),
    ("Reassignment loop", "Network", "Network Operations", "2026-06", 2.4),
    ("Reassignment loop", "Software", "End User Computing", "2026-03", 0.9),
    ("Reassignment loop", "Cloud", "Infrastructure", "2026-05", 0.8),
    ("Reassignment loop", "Application", "Application Support - Portal", "2026-07", 0.9),
    ("Reassignment loop", "Security", "Security Operations", "2026-08", 0.7),
)

#: Anomalies per pattern. The reassignment figure is §35's 614.
PATTERN_TOTALS = {
    "Resolution stall": 402,
    "Reopen churn": 298,
    "Priority mismatch": 236,
    "Volume burst": 292,
    "Reassignment loop": 614,
}


DAYS = pd.date_range(START, END - pd.Timedelta(days=1), freq="D")
#: Each day's month, as an index into MONTHS.
DAY_MONTH = np.array([MONTHS.index(d.strftime("%Y-%m")) for d in DAYS])

CATEGORY_NAMES = tuple(c[0] for c in CATEGORIES)
#: Every configuration item, numbered globally; each category owns a range.
CI_NAMES: tuple[str, ...] = tuple(
    f"{prefix}-{n:03d}" for _, _, _, prefix, pool, _ in CATEGORIES for n in range(1, pool + 1)
)
CI_OFFSET = np.cumsum([0] + [c[4] for c in CATEGORIES])[:-1]
RATE = np.array([REASSIGNMENT_RATE[g] for g in GROUPS])
FACTOR = np.array([c[2] for c in CATEGORIES])


def _days(rng: np.random.Generator, n: int) -> np.ndarray:
    """Open days: weekdays busier than weekends, with a gentle upward trend."""
    weight = np.where(DAYS.dayofweek < 5, 1.0, 0.35) * np.linspace(0.94, 1.06, len(DAYS))
    return rng.choice(len(DAYS), size=n, p=weight / weight.sum())


def _seconds(rng: np.random.Generator, n: int) -> np.ndarray:
    """Seconds into the day: working hours busier than nights."""
    office = rng.random(n) < 0.85
    hour = np.where(office, np.clip(rng.normal(11.5, 2.8, n), 0, 23.99), rng.uniform(0, 24, n))
    return (hour * 3600).astype(np.int64)


def _normal(rng: np.random.Generator, n: int) -> dict[str, np.ndarray]:
    category = rng.choice(len(CATEGORIES), size=n, p=np.array([c[1] for c in CATEGORIES]))
    priority = rng.choice(len(PRIORITIES), size=n, p=PRIORITY_SHARE)
    group = np.empty(n, dtype=np.int64)
    ci = np.empty(n, dtype=np.int64)
    for index, (_, _, _, _, pool, owners) in enumerate(CATEGORIES):
        rows = np.flatnonzero(category == index)
        codes = np.array([GROUPS.index(g) for g, _ in owners])
        shares = np.array([s for _, s in owners])
        group[rows] = codes[rng.choice(len(codes), size=len(rows), p=shares)]
        ci[rows] = CI_OFFSET[index] + rng.integers(0, pool, len(rows))

    hours = PRIORITY_HOURS[priority] * FACTOR[category] * np.exp(rng.normal(0.0, 0.65, n))
    return {
        "day": _days(rng, n),
        "second": _seconds(rng, n),
        "priority": priority,
        "category": category,
        "group": group,
        "ci": ci,
        "hours": hours,
        "reassignments": 1 + rng.poisson(RATE[group]),
        "reopens": rng.poisson(0.06, n),
        "changes": rng.poisson(0.08, n),
        "pattern": np.full(n, -1),
        "cluster": np.full(n, -1),
        "score": rng.beta(2, 9, n) * 0.5,
    }


def _cluster(
    rng: np.random.Generator, number: int, spec: tuple, size: int
) -> dict[str, np.ndarray]:
    pattern, category_name, group_name, month, _ = spec
    category = CATEGORY_NAMES.index(category_name)
    group = GROUPS.index(group_name)
    pool = CATEGORIES[category][4]
    first = int(np.flatnonzero(DAY_MONTH == MONTHS.index(month))[0]) + int(rng.integers(0, 8))

    burst = pattern == "Volume burst"
    day = np.minimum(first + rng.integers(0, 2 if burst else 21, size), len(DAYS) - 1)
    second = (np.clip(rng.normal(11.0, 3.0, size), 0, 23.99) * 3600).astype(np.int64)
    priority = rng.choice(len(PRIORITIES), size=size, p=np.array([0.05, 0.25, 0.45, 0.25]))
    hours = PRIORITY_HOURS[priority] * FACTOR[category] * np.exp(rng.normal(0.0, 0.45, size))
    reassignments = 1 + rng.poisson(RATE[group], size)
    reopens = rng.poisson(0.06, size)
    changes = rng.poisson(0.08, size)
    ci = CI_OFFSET[category] + rng.integers(0, pool, size)

    if pattern == "Resolution stall":
        hours = hours * rng.uniform(5.0, 9.0, size)
    elif pattern == "Reopen churn":
        reopens = rng.integers(2, 5, size)
        hours = hours * rng.uniform(1.6, 2.4, size)
    elif pattern == "Priority mismatch":
        changes = rng.integers(2, 4, size)
        priority = rng.choice([2, 3], size=size)
    elif burst:
        ci = np.full(size, CI_OFFSET[category] + int(rng.integers(0, pool)))
        hours = hours * rng.uniform(0.6, 1.2, size)
    elif pattern == "Reassignment loop":
        reassignments = np.maximum(5, 1 + rng.poisson(6.2, size))
        hours = hours * rng.uniform(2.0, 3.0, size)

    return {
        "day": day,
        "second": second,
        "priority": priority,
        "category": np.full(size, category),
        "group": np.full(size, group),
        "ci": ci,
        "hours": hours,
        "reassignments": reassignments,
        "reopens": reopens,
        "changes": changes,
        "pattern": np.full(size, PATTERNS.index(pattern)),
        "cluster": np.full(size, number - 1),
        "score": rng.uniform(0.82, 0.99, size),
    }


def _sizes() -> list[int]:
    """Cluster sizes: each pattern's total split across its clusters by weight."""
    sizes: dict[int, int] = {}
    for pattern in PATTERNS:
        index = [i for i, c in enumerate(CLUSTERS) if c[0] == pattern]
        parts = allocate(PATTERN_TOTALS[pattern], np.array([CLUSTERS[i][4] for i in index]))
        sizes.update(zip(index, (int(p) for p in parts)))
    return [sizes[i] for i in range(len(CLUSTERS))]


def _categorical(codes: np.ndarray, names: tuple[str, ...] | list[str]) -> pd.Categorical:
    return pd.Categorical.from_codes(codes, categories=list(names))


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    parts = [_normal(rng, TOTAL - ANOMALIES)]
    parts += [
        _cluster(rng, i + 1, spec, size) for i, (spec, size) in enumerate(zip(CLUSTERS, _sizes()))
    ]
    raw = {key: np.concatenate([part[key] for part in parts]) for key in parts[0]}

    # Time order, so ticket numbers rise with open time.
    order = np.lexsort((raw["second"], raw["day"]))
    raw = {key: values[order] for key, values in raw.items()}
    n = len(order)

    opened = DAYS.values[raw["day"]] + raw["second"].astype("timedelta64[s]")
    hours = np.round(raw["hours"], 1)
    anomalous = raw["pattern"] >= 0
    # Tickets raised against the same configuration item on the same day.
    key = raw["ci"] * len(DAYS) + raw["day"]
    _, inverse, counts = np.unique(key, return_inverse=True, return_counts=True)

    pattern_names = (NORMAL, *PATTERNS)
    cluster_names = [f"Cluster {i + 1}" for i in range(len(CLUSTERS))]
    df = pd.DataFrame(
        {
            "number": pd.Series([f"INC{1_000_001 + i:07d}" for i in range(n)], dtype=object),
            "opened": opened,
            "month": _categorical(DAY_MONTH[raw["day"]], MONTHS),
            "priority": _categorical(raw["priority"], PRIORITIES),
            "category": _categorical(raw["category"], CATEGORY_NAMES),
            "assignmentGroup": _categorical(raw["group"], GROUPS),
            "ci": _categorical(raw["ci"], CI_NAMES),
            "resolutionHours": hours,
            "resolutionBand": _categorical(
                np.searchsorted(BAND_EDGES, hours, side="right") - 1, BANDS
            ),
            "reassignments": raw["reassignments"],
            "reopens": raw["reopens"],
            "priorityChanges": raw["changes"],
            "ciDayVolume": counts[inverse],
            "anomalous": anomalous,
            "status": _categorical(anomalous.astype(int), ("Normal", "Anomalous")),
            "pattern": _categorical(raw["pattern"] + 1, pattern_names),
            "cluster": _categorical(raw["cluster"], cluster_names),
            "score": np.round(raw["score"], 3),
        }
    )

    # Baselines, one per metric, from normal tickets only (FR-AN3).
    normal = df[~anomalous]
    for metric in METRICS.values():
        name = f"{metric.column}Baseline"
        by = list(metric.comparable)
        means = normal.groupby(by, observed=True)[metric.column].mean().round(3).rename(name)
        df = df.join(means, on=by)

    # Each anomaly's own metric and baseline, so a cluster's observed and
    # expected are means of rows rather than figures written down.
    observed = np.full(n, np.nan)
    expected = np.full(n, np.nan)
    codes = df["pattern"].cat.codes.to_numpy()
    for index, pattern in enumerate(PATTERNS):
        metric = METRICS[pattern]
        rows = codes == index + 1
        observed[rows] = df[metric.column].to_numpy()[rows]
        expected[rows] = df[f"{metric.column}Baseline"].to_numpy()[rows]
    df["observed"] = observed
    df["expected"] = expected
    excess = np.clip(hours - df["resolutionHoursBaseline"].to_numpy(), 0, None)
    df["excessHours"] = np.where(anomalous, np.round(excess, 1), 0.0)
    # The week each ticket is collected in, once Life begins (D-17).
    df[COLLECTED] = step_of(df["opened"])
    return df


#: A cluster is confirmed once this share of its tickets has been collected.
#: Until then it is provisional: its tickets are flagged, but the cluster is
#: scored on partial evidence, below the confirmation threshold.
CONFIRM_SHARE = 0.6
PROVISIONAL = 0.75


def calibrate(frames: dict[str, pd.DataFrame]) -> list[dict[str, dict[str, np.ndarray]]]:
    """Every recalibration's baselines and scores, computed once (FR-LF6).

    Calibration c is taken at step c x EVERY, over the tickets collected by
    then. Each metric's baseline is the mean over the comparable normal
    tickets collected so far, the same rule generation uses over all of
    them, so the last calibration is exactly the generated frame. A
    cluster's tickets keep their score once enough of it has arrived, and
    are marked down to provisional before that. Nothing here runs when a
    dashboard asks (FR-AN3).
    """
    df = frames["primary"]
    collected = df[COLLECTED].to_numpy()
    anomalous = df["anomalous"].to_numpy()
    codes = df["pattern"].cat.codes.to_numpy()
    cluster = df["cluster"].cat.codes.to_numpy()
    sizes = np.bincount(cluster[cluster >= 0], minlength=len(CLUSTERS))
    hours = df["resolutionHours"].to_numpy()
    # Each metric's comparable cell, as one integer per ticket, so a
    # baseline is two bincounts rather than a groupby and a join.
    cells: dict[str, tuple[np.ndarray, int]] = {}
    for metric in METRICS.values():
        key = np.zeros(len(df), dtype=np.int64)
        width = 1
        for column in metric.comparable:
            codes_of = df[column].cat.codes.to_numpy().astype(np.int64)
            size = len(df[column].cat.categories)
            key = key * size + codes_of
            width *= size
        cells[metric.column] = (key, width)
    calibrations = []
    for c in range(CALIBRATIONS):
        step = c * EVERY
        if c == CALIBRATIONS - 1:
            calibrations.append({})
            continue
        seen = collected <= step
        normal = ~anomalous & seen
        columns: dict[str, np.ndarray] = {}
        for metric in METRICS.values():
            key, width = cells[metric.column]
            values = df[metric.column].to_numpy().astype(float)
            sums = np.bincount(key[normal], weights=values[normal], minlength=width)
            counts = np.bincount(key[normal], minlength=width)
            with np.errstate(invalid="ignore", divide="ignore"):
                means = np.round(sums / counts, 3)
            columns[f"{metric.column}Baseline"] = means[key]
        expected = np.full(len(df), np.nan)
        for index, pattern in enumerate(PATTERNS):
            rows = codes == index + 1
            expected[rows] = columns[f"{METRICS[pattern].column}Baseline"][rows]
        columns["expected"] = expected
        excess = np.clip(hours - columns["resolutionHoursBaseline"], 0, None)
        columns["excessHours"] = np.where(anomalous, np.round(excess, 1), 0.0)
        share = np.bincount(cluster[(cluster >= 0) & seen], minlength=len(CLUSTERS)) / sizes
        provisional = (cluster >= 0) & (share[np.maximum(cluster, 0)] < CONFIRM_SHARE)
        score = df["score"].to_numpy()
        columns["score"] = np.where(provisional, np.round(score * PROVISIONAL, 3), score)
        calibrations.append({"primary": columns})
    return calibrations
