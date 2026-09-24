"""Dataset generators, one per methodology (FR-AN1).

Each is a pure function of a fixed, committed seed (NFR-D5). It returns
record-level frames with the planted patterns, their labels, scores and
baselines already in them, so nothing statistical runs at request time
(FR-AN3). The query engine only filters and aggregates what is here.

Every dataset covers the same twelve closed months, September 2025 to
August 2026, fixed rather than relative to today, so a run next year
draws the same figures (NFR-D4).
"""

import numpy as np
import pandas as pd

#: The analysis window: twelve closed months. Reassignment history is kept
#: for thirteen, so twelve is the most the methodology allows.
START = pd.Timestamp("2025-09-01")
END = pd.Timestamp("2026-09-01")
MONTHS: list[str] = [
    p.strftime("%Y-%m") for p in pd.period_range(START, END - pd.Timedelta(days=1), freq="M")
]
#: The day the snapshot was taken, for "days since" figures.
AS_OF = pd.Timestamp("2026-08-31")


#: Life's collection window (D-17). Agent One VW collects the final twelve
#: weeks of every dataset, ISO weeks 24 to 35 of 2026, one simulated week a
#: step, and recalibrates every four steps. The month ends fall on the
#: recalibration steps (30 June in step 4, 31 July in step 8, 31 August in
#: step 12), so monthly data arrives exactly as a recalibration reads it.
COLLECTION_START = pd.Timestamp("2026-06-08")
STEPS = 12
EVERY = 4
#: Calibration 0 is the one Life starts with; the last is the full dataset.
CALIBRATIONS = STEPS // EVERY + 1
#: The column, in every frame that has one, naming the step a record is
#: collected at: 0 for what was collected before Life began.
COLLECTED = "collected"


def step_of(stamps) -> np.ndarray:
    """The collection step a date's records arrive at."""
    days = (pd.DatetimeIndex(stamps) - COLLECTION_START).days.to_numpy()
    return np.where(days < 0, 0, np.minimum(days // 7 + 1, STEPS)).astype(np.int16)


def month_step(months) -> np.ndarray:
    """The step at which a month is complete, and its figures arrive."""
    ends = pd.DatetimeIndex([pd.Period(m, freq="M").end_time.normalize() for m in months])
    return step_of(ends)


def calibration_of(step: int | None) -> int:
    """The calibration in force at a step. No step is the full dataset."""
    return CALIBRATIONS - 1 if step is None else min(step // EVERY, CALIBRATIONS - 1)


def week_of(step: int) -> dict[str, str]:
    """A step's simulated week: its ISO number and its dates."""
    first = COLLECTION_START + pd.Timedelta(days=7 * max(step - 1, 0))
    last = first + pd.Timedelta(days=6 if step < STEPS else 7)
    if step == 0:
        first, last = START, COLLECTION_START - pd.Timedelta(days=1)
    return {
        "week": f"week {first.isocalendar().week}" if step else "before week 24",
        "from": first.date().isoformat(),
        "to": last.date().isoformat(),
    }


def month_labels() -> dict[str, str]:
    return {m: pd.Period(m, freq="M").strftime("%b %Y") for m in MONTHS}


def allocate(total: int, weights: np.ndarray) -> np.ndarray:
    """Split `total` into integers proportional to `weights`, exactly.

    Largest remainder, with ties broken by position, so the parts always
    sum to the total and the split is the same every time.
    """
    raw = weights / weights.sum() * total
    parts = np.floor(raw).astype(int)
    short = total - parts.sum()
    order = np.argsort(-(raw - parts), kind="stable")
    parts[order[:short]] += 1
    return parts
