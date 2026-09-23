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
