"""The application portfolio, for Application Portfolio Rationalization.

One row per application, with the evidence the methodology asks for:
usage, ownership, cost, dependencies and criticality. Each application's
disposition is decided at generation by the rules in `dispose`, which
are the methodology's classification step written down (FR-AN3):

- no usage instrumentation: **Unresolved**. Never reported as unused,
  because an application nobody can see being used is not one nobody
  uses (adaptation.md's declared limitation);
- almost no users and almost nothing depending on it: **Retire**;
- end of life and still in use: **Replace**;
- a minor application in a capability another serves far better:
  **Consolidate**;
- otherwise **Retain**.

Ownership is missing for 29% of applications and criticality for 12%,
the gaps discovery profiled in the CMDB. They show as "Unassigned" and
"Unrecorded" rather than being filled in.

A second frame holds monthly distinct users per instrumented application.
"""

import numpy as np
import pandas as pd

from app.analytics.generator import MONTHS

SEED = 20260625

BUSINESS_UNITS = (
    "Finance",
    "HR",
    "Sales",
    "Marketing",
    "Operations",
    "Engineering",
    "Customer Service",
    "Corporate IT",
)

#: Capability, and the application name stems that serve it.
CAPABILITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Expense management", ("ExpenseFlow", "Receipts", "TravelDesk", "ClaimIt")),
    ("Payroll", ("PayCore", "PayRun Legacy", "TimeSheet Pro")),
    ("Customer relationship", ("Pipeline", "AccountView", "LeadBox", "Partner Portal", "DealRoom")),
    ("Document management", ("DocVault", "FileShare Classic", "Records Hub", "Scan&Store")),
    ("Collaboration", ("TeamSpace", "Wiki Legacy", "Whiteboard", "IdeaBoard")),
    ("Reporting and BI", ("Insight", "ReportServer", "KPI Board", "DataCube", "Dash Legacy")),
    ("Recruiting", ("TalentFind", "Referrals", "Interview Kit")),
    ("Learning", ("Academy", "CourseHub", "Compliance Training")),
    ("Procurement", ("BuyDesk", "Supplier Portal", "PO Tracker", "Tender")),
    ("Project management", ("Roadmap", "TaskTrack", "Portfolio Planner", "Gantt Classic")),
    ("Service management", ("Service Portal", "Asset Register", "Change Board")),
    ("Contract management", ("ContractHub", "Obligations", "Clause Library")),
    ("Marketing automation", ("Campaigns", "EventDesk", "Newsletter", "Survey")),
    ("Data integration", ("Integration Hub", "File Transfer", "ETL Legacy", "API Gateway")),
    ("Field operations", ("FieldApp", "Dispatch", "Inspection", "Route Planner")),
    ("Identity and access", ("Access Requests", "Directory Sync", "Badge Office")),
)

LIFECYCLES = ("Active", "Sunset", "End of life")
CRITICALITY = ("High", "Medium", "Low", "Unrecorded")
DISPOSITIONS = ("Retain", "Consolidate", "Replace", "Retire", "Unresolved")
OWNERS = (
    "A. Patel",
    "B. Moreau",
    "C. Okafor",
    "D. Lindqvist",
    "E. Nakamura",
    "F. Rossi",
    "G. Mensah",
    "H. Kowalski",
    "I. Fernandes",
    "J. Byrne",
    "K. Haddad",
    "L. Svensson",
)
UNASSIGNED = "Unassigned"


#: Variants of a stem: regional copies and acquired or older versions,
#: which is how a portfolio comes to hold several of one thing.
VARIANTS = ("", " EMEA", " APAC", " Americas", " Lite", " v2", " (acquired)", " Classic")


def dispose(
    instrumented: bool, users: float, inbound: int, lifecycle: str, share_of_leader: float
) -> str:
    """The methodology's disposition rules, in the order they apply."""
    if not instrumented:
        return "Unresolved"
    if users < 40 and inbound <= 2:
        return "Retire"
    if lifecycle == "End of life":
        return "Replace"
    if share_of_leader < 0.07:
        return "Consolidate"
    return "Retain"


def _application(rng: np.random.Generator, name: str, capability: str, leader: bool) -> dict:
    legacy = any(mark in name for mark in ("Legacy", "Classic"))
    users = float(rng.lognormal(6.6 if leader else 5.0, 0.5 if leader else 1.2))
    if legacy:
        users *= 0.15
    if rng.random() < 0.08:
        lifecycle = "End of life"
    else:
        lifecycle = "End of life" if legacy else LIFECYCLES[int(rng.choice(2, p=[0.85, 0.15]))]
    owned = rng.random() > 0.29
    recorded = rng.random() > 0.12
    return {
        "name": name,
        "capability": capability,
        "businessUnit": BUSINESS_UNITS[int(rng.integers(0, len(BUSINESS_UNITS)))],
        "lifecycle": lifecycle,
        "owner": OWNERS[int(rng.integers(0, len(OWNERS)))] if owned else UNASSIGNED,
        "criticality": CRITICALITY[int(rng.choice(3, p=[0.2, 0.5, 0.3]))]
        if recorded
        else "Unrecorded",
        "instrumented": bool(rng.random() > 0.12),
        "users": users,
        "annualCost": float(np.round(rng.lognormal(10.8 if leader else 9.8, 0.7), -2)),
        "dependenciesIn": int(rng.poisson(6 if leader else 1.3)),
        "dependenciesOut": int(rng.poisson(3)),
    }


def generate() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The application frame, and the application-by-month usage frame."""
    rng = np.random.default_rng(SEED)
    rows = []
    for capability, stems in CAPABILITIES:
        count = int(rng.integers(9, 15))
        names = [
            f"{stems[i % len(stems)]}{VARIANTS[i // len(stems)]}"
            for i in range(min(count, len(stems) * len(VARIANTS)))
        ]
        rows += [_application(rng, name, capability, i == 0) for i, name in enumerate(names)]

    df = pd.DataFrame(rows)
    leaders = df.groupby("capability")["users"].transform("max")
    df["shareOfLeader"] = (df["users"] / leaders).round(3)
    df["monthlyUsers"] = np.where(df["instrumented"], np.round(df["users"]), np.nan)
    df["costPerUser"] = np.where(
        df["instrumented"], np.round(df["annualCost"] / np.maximum(df["users"], 1.0), 1), np.nan
    )
    df["disposition"] = [
        dispose(r.instrumented, r.users, r.dependenciesIn, r.lifecycle, r.shareOfLeader)
        for r in df.itertuples()
    ]
    df.insert(0, "application", [f"APP-{i + 1:04d}" for i in range(len(df))])
    df = df.drop(columns=["users"])
    for column, names in (
        ("capability", [c for c, _ in CAPABILITIES]),
        ("businessUnit", BUSINESS_UNITS),
        ("lifecycle", LIFECYCLES),
        ("criticality", CRITICALITY),
        ("disposition", DISPOSITIONS),
        ("owner", (*OWNERS, UNASSIGNED)),
        ("name", df["name"].tolist()),
    ):
        df[column] = pd.Categorical(df[column], categories=list(names))

    # Baselines for the evidence panel: the retained applications of the
    # same capability (FR-AN3).
    retained = df[df["disposition"] == "Retain"].groupby("capability", observed=True)
    for column, name in (("monthlyUsers", "usersBaseline"), ("costPerUser", "costPerUserBaseline")):
        df = df.join(retained[column].mean().round(1).rename(name), on="capability")

    # Monthly distinct users: retiring applications fade, the rest hold.
    months = len(MONTHS)
    drift = np.where(df["disposition"] == "Retire", -0.06, 0.01).astype(float)
    trend = np.exp(drift[:, None] * (np.arange(months)[None, :] - (months - 1)))
    noise = rng.normal(1.0, 0.06, (len(df), months))
    users = df["monthlyUsers"].to_numpy()[:, None] * trend * noise
    usage = pd.DataFrame(
        {
            "application": np.repeat(df["application"].to_numpy(), months),
            "month": pd.Categorical(np.tile(MONTHS, len(df)), categories=MONTHS),
            "users": np.round(users.reshape(-1)),
        }
    )
    return df, usage
