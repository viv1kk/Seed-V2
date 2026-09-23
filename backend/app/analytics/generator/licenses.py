"""Licence seats for License Optimization.

One row per entitled seat, so every headline is a count of rows: seats
entitled, assigned, active, idle. A seat is Unassigned, or assigned to a
person who has left (Leaver), or classified by how many of the last 90
days it was used: Active from 10 days, Underused from 1, Unused at none.
The class is computed from those figures at generation (FR-AN3), by the
rule in `classify`, and a test holds the two together.

Unit cost is missing for some products, deliberately. Discovery profiled
SAP's `contract_item.unit_price` at 64% complete, and that gap is carried
here as unpriced products covering 36% of seats: their recoverable cost is withheld, never
estimated and never zero (PR-074, OQ-1).

A second frame holds each seat's month-by-month use, for the trend.
"""

import numpy as np
import pandas as pd

from app.analytics.generator import AS_OF, MONTHS, allocate

SEED = 20260624

#: Vendor, product, seats entitled, annual unit cost (None where the
#: contract item is unpriced), and how its seats tend to be used:
#: shares of unassigned, leaver, unused and underused seats.
PRODUCTS: tuple[tuple[str, str, int, float | None, tuple[float, float, float, float]], ...] = (
    ("Microsoft", "Microsoft 365 E3", 2600, 432.0, (0.03, 0.02, 0.04, 0.06)),
    ("Microsoft", "Microsoft 365 E5", 420, 684.0, (0.04, 0.03, 0.08, 0.22)),
    ("Microsoft", "Visio Plan 2", 380, 180.0, (0.08, 0.03, 0.24, 0.18)),
    ("Microsoft", "Project Plan 3", 310, 360.0, (0.10, 0.03, 0.21, 0.16)),
    ("Microsoft", "Power BI Pro", 900, 120.0, (0.05, 0.02, 0.12, 0.20)),
    ("Adobe", "Acrobat Pro", 1400, None, (0.04, 0.03, 0.18, 0.14)),
    ("Adobe", "Creative Cloud All Apps", 210, None, (0.06, 0.02, 0.15, 0.12)),
    ("Adobe", "Adobe Sign", 350, None, (0.07, 0.02, 0.10, 0.18)),
    ("Atlassian", "Jira Software", 1150, 98.0, (0.03, 0.02, 0.07, 0.08)),
    ("Atlassian", "Confluence", 1250, 69.0, (0.03, 0.02, 0.09, 0.15)),
    ("Salesforce", "Sales Cloud Enterprise", 640, None, (0.05, 0.04, 0.09, 0.10)),
    ("Salesforce", "Service Cloud", 380, None, (0.06, 0.03, 0.08, 0.09)),
    ("Salesforce", "Tableau Creator", 160, 900.0, (0.27, 0.03, 0.14, 0.10)),
    ("Autodesk", "AutoCAD", 190, None, (0.05, 0.03, 0.34, 0.12)),
    ("Zoom", "Zoom Business", 1100, 180.0, (0.04, 0.03, 0.16, 0.12)),
    ("Zoom", "Zoom Webinars", 90, None, (0.10, 0.02, 0.30, 0.20)),
    ("DocuSign", "DocuSign Business Pro", 260, None, (0.06, 0.03, 0.12, 0.16)),
    ("Slack", "Slack Business+", 1350, None, (0.03, 0.02, 0.06, 0.09)),
    ("Miro", "Miro Business", 420, 192.0, (0.08, 0.03, 0.26, 0.20)),
    ("Snowflake", "Snowflake Standard", 60, None, (0.05, 0.02, 0.10, 0.12)),
)

DEPARTMENTS = (
    "Finance",
    "HR",
    "Sales",
    "Marketing",
    "Engineering",
    "Operations",
    "Legal",
    "IT",
    "Customer Service",
)
DEPARTMENT_SHARE = np.array([0.10, 0.06, 0.18, 0.09, 0.20, 0.14, 0.04, 0.09, 0.10])

CLASSES = ("Active", "Underused", "Unused", "Leaver", "Unassigned")
RECOVERABLE = ("Unused", "Leaver", "Unassigned")

UNASSIGNED = "Unassigned"


def classify(assigned: bool, leaver: bool, active_days: int) -> str:
    """The utilisation rule, as the methodology states it."""
    if not assigned:
        return "Unassigned"
    if leaver:
        return "Leaver"
    if active_days >= 10:
        return "Active"
    return "Underused" if active_days >= 1 else "Unused"


def _categorical(codes: np.ndarray, names) -> pd.Categorical:
    return pd.Categorical.from_codes(codes, categories=list(names))


def generate() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The seat frame, and the seat-by-month activity frame."""
    rng = np.random.default_rng(SEED)
    months = len(MONTHS)
    month_end = np.array(
        [pd.Period(m, freq="M").end_time.normalize().to_datetime64() for m in MONTHS],
        dtype="datetime64[D]",
    )
    as_of = AS_OF.to_datetime64().astype("datetime64[D]")
    columns: dict[str, list[np.ndarray]] = {}
    activity: list[np.ndarray] = []
    assigned_from: list[np.ndarray] = []

    def put(name: str, values: np.ndarray) -> None:
        columns.setdefault(name, []).append(values)

    for index, (_, _, seats, cost, shares) in enumerate(PRODUCTS):
        unassigned, leaver, unused, underused = shares
        weights = np.array([1 - sum(shares), underused, unused, leaver, unassigned])
        latent = np.repeat(np.arange(len(CLASSES)), allocate(seats, weights))
        rng.shuffle(latent)
        assigned = latent != 4

        start = np.where(assigned, rng.integers(-18, months - 1, seats), months)
        active_days = np.select(
            [latent == 0, latent == 1],
            [rng.integers(10, 70, seats), rng.integers(1, 10, seats)],
            default=0,
        )

        # Month-by-month use, consistent with the class: nothing before
        # assignment, nothing after a leaver left, nothing in the last
        # three months of an unused seat, and some use in them for an
        # underused one.
        rate = np.array([0.93, 0.35, 0.45, 0.8, 0.0])[latent]
        span = np.arange(months)[None, :]
        used = rng.random((seats, months)) < rate[:, None]
        used &= span >= np.maximum(start, 0)[:, None]
        left = rng.integers(3, months - 3, seats)
        used &= ~((latent == 3)[:, None] & (span >= left[:, None]))
        used[latent == 2, months - 3 :] = False
        used[latent == 0, months - 1] = True
        recent = latent == 1
        used[recent, months - 1 - rng.integers(0, 3, int(recent.sum()))] = True
        activity.append(used)
        assigned_from.append(start)

        ever = used.any(axis=1)
        last = months - 1 - np.argmax(used[:, ::-1], axis=1)
        days = np.where(
            latent <= 1,
            as_of - rng.integers(0, 30, seats).astype("timedelta64[D]"),
            month_end[last] - rng.integers(0, 25, seats).astype("timedelta64[D]"),
        )
        days = np.where(latent == 2, np.minimum(days, as_of - np.timedelta64(91, "D")), days)
        days = np.where(ever, days, np.datetime64("NaT", "D"))

        put("product", np.full(seats, index))
        department = rng.choice(len(DEPARTMENTS), seats, p=DEPARTMENT_SHARE)
        put("department", np.where(assigned, department, len(DEPARTMENTS)))
        put("assignee", np.where(assigned, rng.integers(10000, 99999, seats), -1))
        put("class", latent)
        put("activeDays90", active_days)
        put("lastActivity", days)
        put("unitCost", np.full(seats, np.nan if cost is None else cost))

    raw = {name: np.concatenate(parts) for name, parts in columns.items()}
    n = len(raw["product"])
    vendors = tuple(dict.fromkeys(p[0] for p in PRODUCTS))
    product_vendor = np.array([vendors.index(p[0]) for p in PRODUCTS])
    latent = raw["class"]

    df = pd.DataFrame(
        {
            "seat": pd.Series([f"LIC-{i + 1:06d}" for i in range(n)], dtype=object),
            "vendor": _categorical(product_vendor[raw["product"]], vendors),
            "product": _categorical(raw["product"], [p[1] for p in PRODUCTS]),
            "department": _categorical(raw["department"], [*DEPARTMENTS, UNASSIGNED]),
            "assignee": pd.Series(
                [f"u{a}" if a >= 0 else None for a in raw["assignee"].tolist()], dtype=object
            ),
            "assigned": latent != 4,
            "leaver": latent == 3,
            "activeDays90": raw["activeDays90"],
            "lastActivity": raw["lastActivity"].astype("datetime64[s]"),
            "class": _categorical(latent, CLASSES),
            "unitCost": raw["unitCost"],
        }
    )
    df["daysInactive"] = (AS_OF - df["lastActivity"]).dt.days.astype(float)
    df["priced"] = df["unitCost"].notna()
    df["active"] = latent == 0
    df["idle"] = (latent == 1) | (latent == 2)
    df["recoverable"] = df["class"].isin(RECOVERABLE).to_numpy()
    df["recoverableCost"] = np.where(df["recoverable"], df["unitCost"], 0.0)

    # Baselines for the evidence panel: how an active seat of the same
    # product is used (FR-AN3).
    active = df[df["active"]].groupby("product", observed=True)
    for column, name in (
        ("daysInactive", "daysInactiveBaseline"),
        ("activeDays90", "activeDaysBaseline"),
    ):
        df = df.join(active[column].mean().round(1).rename(name), on="product")

    used = np.concatenate(activity)
    start = np.concatenate(assigned_from)
    frame = pd.DataFrame(
        {
            "seat": np.repeat(df["seat"].to_numpy(), months),
            "month": pd.Categorical.from_codes(np.tile(np.arange(months), n), categories=MONTHS),
            "assigned": (np.arange(months)[None, :] >= start[:, None]).reshape(-1),
            "active": used.reshape(-1),
        }
    )
    return df, frame
