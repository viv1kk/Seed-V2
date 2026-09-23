"""The analytics core: generators, query engine, evidence (D-7's query suite).

The load-bearing claim of M9 is that every figure a dashboard shows is an
aggregate of record-level rows for whatever filter is in force. So most
tests here compute a figure the naive way, straight from the frame with
plain pandas, and compare it with what the engine returned, across many
filter combinations drawn from a fixed seed. The rest hold the planted
data to its figures, the engine to its time budget, and the engine and
API to knowing nothing about any one methodology (FR-EV4).
"""

import ast
import time
import zlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.analytics.descriptors import SOURCES
from app.analytics.evidence import evidence
from app.analytics.generator import applications, licenses, tickets
from app.analytics.query import Engine, FilterContext, QueryError, run
from app.analytics.schema import ROLES, Dashboard, Measure
from app.analytics.store import build, build_all
from app.main import app

TAD, LO, APR = (
    "ticket-anomaly-detection",
    "license-optimization",
    "application-portfolio-rationalization",
)
TOKENS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "design" / "tokens.css"
APP = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture(scope="module")
def data() -> dict[str, Any]:
    return build_all()


def context(**dimensions: list[str]) -> FilterContext:
    return FilterContext(dimensions=dimensions)


def naive_rows(ds, flt: FilterContext, frame: str = "primary") -> pd.DataFrame:
    """Rows selected, by the plainest possible pandas."""
    df = ds.frames[frame]
    keep = pd.Series(True, index=df.index)
    for dim_id, values in flt.dimensions.items():
        dimension = ds.dashboard.dimension(dim_id)
        if dimension.frame and dimension.frame != frame:
            continue
        keep &= df[dimension.column].astype(str).isin(values)
    if flt.time_range and ds.dashboard.time in df:
        start, end = (pd.Timestamp(d) for d in flt.time_range)
        keep &= (df[ds.dashboard.time] >= start) & (
            df[ds.dashboard.time] < end + pd.Timedelta(days=1)
        )
    if flt.entity_id:
        keep &= df[ds.dashboard.entity.id].astype(str) == flt.entity_id
    return df[keep]


def combinations(ds, count: int, seed: int) -> list[FilterContext]:
    """Filter contexts drawn at random, from a fixed seed, over every
    dimension that lives in the primary frame."""
    rng = np.random.default_rng(seed)
    dims = [d for d in ds.dashboard.dimensions if d.frame is None]
    out = [FilterContext()]
    for _ in range(count):
        chosen = rng.choice(len(dims), size=int(rng.integers(1, 4)), replace=False)
        picked = {}
        for index in chosen:
            dimension = dims[int(index)]
            domain = ds.domains[dimension.id]
            size = int(rng.integers(1, min(3, len(domain)) + 1))
            picked[dimension.id] = [str(v) for v in rng.choice(domain, size=size, replace=False)]
        time_range = None
        if ds.dashboard.time and rng.random() < 0.3:
            time_range = ("2026-01-01", "2026-04-30")
        out.append(FilterContext(dimensions=picked, time_range=time_range))
    return out


def naive(rows: pd.DataFrame, measure: Measure, dashboard: Dashboard) -> float:
    if measure.agg == "count":
        return float(len(rows))
    if measure.agg in ("ratio", "lift"):
        n = naive(rows, dashboard.measure(measure.numerator), dashboard)
        d = naive(rows, dashboard.measure(measure.denominator), dashboard)
        if not d or np.isnan(d):
            return np.nan
        return n / d - (1 if measure.agg == "lift" else 0)
    column = rows[measure.column]
    if measure.agg == "countIf":
        return float(column.astype(bool).sum())
    if measure.agg == "sum":
        return float(np.nansum(column.astype(float)))
    if measure.agg == "mean":
        return float(column.astype(float).mean()) if column.notna().any() else np.nan
    if measure.agg == "median":
        return float(column.astype(float).median()) if column.notna().any() else np.nan
    return float(column.dropna().nunique())


def same(a: Any, b: float) -> bool:
    if a is None:
        return b is None or np.isnan(b)
    return bool(np.isclose(a, b, rtol=1e-9, atol=1e-9))


# -- Generators (FR-AN1 to FR-AN4, NFR-D4, NFR-D5) ----------------------


def test_the_ticket_headlines_are_the_datasets_true_counts(data) -> None:
    df = data[TAD].primary
    assert len(df) == 184_392
    assert int(df["anomalous"].sum()) == 1_842
    assert df["cluster"].nunique() == 31
    assert (
        df[df["anomalous"]].groupby("pattern", observed=True).size().to_dict()
        == tickets.PATTERN_TOTALS
    )
    # Every anomaly is in exactly one cluster, and every cluster is one pattern.
    assert df.loc[df["anomalous"], "cluster"].notna().all()
    assert df.loc[~df["anomalous"], "cluster"].isna().all()
    assert (df[df["anomalous"]].groupby("cluster", observed=True)["pattern"].nunique() == 1).all()


def test_cluster_27_is_the_reassignment_loop_of_section_35(data) -> None:
    rows = data[TAD].primary.query("cluster == 'Cluster 27'")
    assert set(rows["pattern"].astype(str)) == {"Reassignment loop"}
    assert set(rows["assignmentGroup"].astype(str)) == {"Network Operations"}
    assert set(rows["month"].astype(str)) == {"2026-06"}


@pytest.mark.parametrize("generate", [tickets.generate, licenses.generate, applications.generate])
def test_generation_is_identical_every_time(generate) -> None:
    first, second = generate(), generate()
    for a, b in zip(
        first if isinstance(first, tuple) else (first,),
        second if isinstance(second, tuple) else (second,),
    ):
        pd.testing.assert_frame_equal(a, b)


def test_every_ticket_baseline_is_the_mean_of_its_comparable_normal_tickets(data) -> None:
    """FR-AN3: baselines made at generation, from the rows they claim."""
    df = data[TAD].primary
    normal = df[~df["anomalous"]]
    for metric in tickets.METRICS.values():
        by = list(metric.comparable)
        expected = normal.groupby(by, observed=True)[metric.column].mean().round(3)
        actual = df.groupby(by, observed=True)[f"{metric.column}Baseline"].first()
        pd.testing.assert_series_equal(
            actual.sort_index(), expected.sort_index(), check_names=False
        )


def test_anomalies_deviate_from_their_baselines(data) -> None:
    df = data[TAD].primary
    anomalous = df[df["anomalous"]]
    assert (
        anomalous.groupby("cluster", observed=True)["observed"].mean()
        > 2 * anomalous.groupby("cluster", observed=True)["expected"].mean()
    ).all()


def test_licence_classes_follow_the_utilisation_rule(data) -> None:
    df = data[LO].primary
    ruled = [
        licenses.classify(a, l, d)
        for a, l, d in zip(df["assigned"], df["leaver"], df["activeDays90"])
    ]
    assert ruled == df["class"].astype(str).tolist()


def test_unit_price_is_missing_where_discovery_said(data) -> None:
    """64% of seats priced, matching contract_item.unit_price's completeness."""
    df = data[LO].primary
    assert round(float(df["priced"].mean()), 2) == 0.64
    unpriced = df[~df["priced"] & df["recoverable"]]
    assert unpriced["recoverableCost"].isna().all()


def test_uninstrumented_applications_are_unresolved_never_retired(data) -> None:
    df = data[APR].primary
    assert (df["disposition"].astype(str) == "Unresolved").tolist() == (
        ~df["instrumented"]
    ).tolist()
    assert df.loc[~df["instrumented"], "monthlyUsers"].isna().all()


def test_every_dataset_builds_inside_the_startup_budget() -> None:
    """NFR-P1 on a warm interpreter: generation is a fraction of it."""
    start = time.perf_counter()
    build_all()
    assert time.perf_counter() - start < 1.5


# -- Query engine against ground truth (FR-AN5, FR-EV1, FR-EV2) --------


@pytest.mark.parametrize("solution", [TAD, LO, APR])
def test_every_kpi_matches_the_rows_across_filter_combinations(data, solution) -> None:
    ds = data[solution]
    for flt in combinations(ds, 25, seed=zlib.crc32(solution.encode())):
        result = run(ds, flt, [k.id for k in ds.dashboard.kpis])
        for kpi in ds.dashboard.kpis:
            measure = ds.dashboard.measure(kpi.measure)
            rows = naive_rows(ds, flt, measure.frame)
            got = result["views"][kpi.id]["value"]
            assert same(got, naive(rows, measure, ds.dashboard)), (solution, kpi.id, flt)


def test_stacked_bars_are_the_crosstab_of_the_selected_rows(data) -> None:
    ds = data[TAD]
    for flt in combinations(ds, 15, seed=7):
        view = run(ds, flt, ["by-group"])["views"]["by-group"]
        rows = naive_rows(ds, flt)
        rows = rows[rows["pattern"].astype(str) != "Normal"]
        table = pd.crosstab(rows["assignmentGroup"].astype(str), rows["pattern"].astype(str))
        for series in view["series"]:
            for category, value in zip(view["categories"], series["values"]):
                expected = (
                    table.at[category["key"], series["key"]]
                    if (category["key"] in table.index and series["key"] in table.columns)
                    else 0
                )
                assert value == expected


def test_a_time_line_shows_every_month_and_counts_each(data) -> None:
    ds = data[TAD]
    flt = context(group=["Messaging"], priority=["P3"])
    view = run(ds, flt, ["volume"])["views"]["volume"]
    assert [c["key"] for c in view["categories"]] == ds.domains["month"]
    counts = naive_rows(ds, flt).groupby("month", observed=False).size()
    assert view["series"][0]["values"] == [int(counts.get(m, 0)) for m in ds.domains["month"]]


def test_normalised_series_are_shares(data) -> None:
    view = run(data[TAD], FilterContext(), ["resolution"])["views"]["resolution"]
    for series in view["series"]:
        assert sum(series["values"]) == pytest.approx(1.0)


def test_treemap_nodes_add_up_and_leaves_are_the_rows(data) -> None:
    ds = data[TAD]
    for flt in combinations(ds, 10, seed=11):
        view = run(ds, flt, ["clusters"])["views"]["clusters"]
        rows = naive_rows(ds, flt)
        rows = rows[rows["pattern"].astype(str) != "Normal"]
        assert view["total"] == len(rows)

        def check(nodes):
            for node in nodes:
                if node["children"]:
                    assert node["value"] == sum(c["value"] for c in node["children"])
                    check(node["children"])
                else:
                    pattern, group, cluster = (
                        node["filter"]["pattern"][0],
                        node["filter"]["group"][0],
                        node["filter"]["cluster"][0],
                    )
                    assert node["value"] == len(
                        rows[
                            (rows["pattern"].astype(str) == pattern)
                            & (rows["assignmentGroup"].astype(str) == group)
                            & (rows["cluster"].astype(str) == cluster)
                        ]
                    )

        check(view["nodes"])


def test_the_cluster_table_is_computed_from_its_tickets(data) -> None:
    ds = data[TAD]
    view = run(ds, FilterContext(), ["cluster-table"])["views"]["cluster-table"]
    excess = [row["cells"]["excess"] for row in view["rows"]]
    assert excess == sorted(excess, reverse=True)
    assert view["total"] == 31
    for row in view["rows"]:
        rows = ds.primary[ds.primary["cluster"].astype(str) == row["key"]]
        assert row["cells"]["anomalies"] == len(rows)
        assert row["cells"]["observed"] == pytest.approx(rows["observed"].mean())
        assert row["cells"]["expected"] == pytest.approx(rows["expected"].mean())
        assert row["cells"]["deviation"] == pytest.approx(
            rows["observed"].mean() / rows["expected"].mean() - 1
        )
        assert row["filter"] == {"cluster": [row["key"]]}
        assert row["unit"] in ("hours", "decimal")


def test_record_pages_are_the_selected_rows_in_order(data) -> None:
    ds = data[TAD]
    flt = context(pattern=["Reassignment loop"], priority=["P2", "P3"])
    engine = Engine(ds, flt)
    table = ds.dashboard.view("records")
    rows = naive_rows(ds, flt).sort_values("score", ascending=False, kind="stable")
    first, second = engine.records(table, 0), engine.records(table, 1)
    assert first["total"] == len(rows)
    ids = [r["id"] for r in first["rows"] + second["rows"]]
    assert ids == rows["number"].head(50).tolist()


def test_an_entity_narrows_every_view_to_one_record(data) -> None:
    ds = data[TAD]
    number = ds.primary.query("cluster == 'Cluster 27'")["number"].iloc[0]
    result = run(ds, FilterContext(entity_id=number))
    assert result["views"]["k-tickets"]["value"] == 1
    assert result["views"]["records"]["rows"][0]["id"] == number
    assert result["drill"]["levels"][-1]["value"] == number


def test_a_secondary_frame_is_narrowed_by_the_primary_dimensions(data) -> None:
    ds = data[LO]
    flt = context(product=["AutoCAD"], **{"class": ["Unused"]})
    view = run(ds, flt, ["use-over-time"])["views"]["use-over-time"]
    rows = naive_rows(ds, flt, "activity")
    expected = rows.groupby("month", observed=False)["active"].sum()
    assert view["series"][1]["values"] == [int(expected.get(m, 0)) for m in ds.domains["month"]]


def test_a_filter_that_cannot_apply_says_so(data) -> None:
    """A month narrows the monthly activity but not a seat count: the
    headline reports it was not filtered rather than pretending."""
    result = run(data[LO], context(month=["2026-03"]), ["k-seats", "use-over-time"])
    assert result["views"]["k-seats"]["ignored"] == ["month"]
    assert result["views"]["use-over-time"]["ignored"] == []


def test_unpriced_cost_is_withheld_never_zero(data) -> None:
    ds = data[LO]
    result = run(ds, FilterContext(), ["k-cost", "cost", "candidates"])["views"]
    rows = ds.primary
    assert result["k-cost"]["value"] == pytest.approx(float(np.nansum(rows["recoverableCost"])))
    assert result["k-cost"]["withheld"] == int((rows["recoverable"] & ~rows["priced"]).sum())
    unpriced = {p[1] for p in licenses.PRODUCTS if p[3] is None}
    for category, value, missing in zip(
        result["cost"]["categories"],
        result["cost"]["series"][0]["values"],
        result["cost"]["withheld"],
    ):
        assert (value is None) == (category["key"] in unpriced) == (missing > 0)
    for row in result["candidates"]["rows"]:
        assert (row["cells"]["recoverable-cost"] is None) == (row["key"] in unpriced)


# -- Colour (OQ-1, D-5) ---------------------------------------------------


def test_a_pattern_has_one_colour_on_every_chart(data) -> None:
    ds = data[TAD]
    palette = ds.palettes["pattern"]
    result = run(ds, FilterContext())["views"]
    for chart in ("by-group", "trend", "by-priority"):
        for series in result[chart]["series"]:
            assert series["role"] == palette[series["key"]]
    for node in result["clusters"]["nodes"]:
        assert node["role"] == palette[node["label"]]
    assert palette["Normal"] == "muted"


def test_one_pattern_selected_recolours_the_treemap_by_cluster(data) -> None:
    ds = data[TAD]
    view = run(ds, context(pattern=["Reassignment loop"]), ["clusters"])["views"]["clusters"]
    assert view["colourBy"] == "cluster"
    leaves = [c for n in view["nodes"] for g in n["children"] for c in g["children"]]
    roles = [leaf["role"] for leaf in leaves]
    assert len(set(roles)) == len(roles) == 8


def test_every_role_a_descriptor_can_name_is_a_token_in_both_themes() -> None:
    css = TOKENS.read_text(encoding="utf-8")
    light, dark = css.split("[data-theme='dark'] {", 1)
    for role in ROLES:
        assert f"--chart-{role}:" in light, role
        assert f"--chart-{role}:" in dark, role


# -- Drill-down (FR-EV3, FR-EV6) ----------------------------------------


def test_the_drill_path_reports_reached_levels_and_the_next(data) -> None:
    ds = data[TAD]
    drill = run(ds, context(pattern=["Reassignment loop"]), ["k-tickets"])["drill"]
    assert drill["root"] == "All tickets"
    assert [l["id"] for l in drill["levels"]] == ["month", "pattern", "group", "cluster", "ticket"]
    assert drill["next"] == "group"
    drill = run(ds, context(cluster=["Cluster 27"]), ["k-tickets"])["drill"]
    assert drill["next"] == "ticket"


def test_every_hierarchy_ends_at_records() -> None:
    for source in SOURCES:
        assert source.dashboard.hierarchy[-1].entity


def test_every_clickable_datum_carries_the_filter_it_applies(data) -> None:
    result = run(data[TAD], FilterContext())["views"]
    assert result["by-group"]["categories"][0]["filter"] == {
        "group": [result["by-group"]["categories"][0]["key"]]
    }
    assert result["clusters"]["nodes"][0]["filter"] == {
        "pattern": [result["clusters"]["nodes"][0]["label"]]
    }


# -- Evidence (FR-EV7, FR-EV8) ------------------------------------------


def test_cluster_27_evidence_is_computed_from_its_rows(data) -> None:
    ds = data[TAD]
    result = evidence(ds, context(cluster=["Cluster 27"]))
    rows = ds.primary.query("cluster == 'Cluster 27'")
    normal = ds.primary.query("pattern == 'Normal' and assignmentGroup == 'Network Operations'")
    assert result["status"] == "finding"
    assert result["finding"]["value"] == "Reassignment loop"
    assert result["observed"] == pytest.approx(rows["reassignments"].mean(), abs=1e-3)
    assert result["baseline"] == pytest.approx(rows["reassignmentsBaseline"].mean(), abs=1e-3)
    assert result["baseline"] == pytest.approx(normal["reassignments"].mean(), abs=1e-3)
    assert result["deviation"] == pytest.approx(
        result["observed"] / result["baseline"] - 1, abs=1e-3
    )
    assert result["comparable"]["size"] == len(normal)
    assert result["records"]["count"] == len(rows) == 175
    assert result["methodology"]["name"] == "Ticket Anomaly Detection"
    assert result["validation"]


def test_one_ticket_is_explained_against_its_own_baseline(data) -> None:
    ds = data[TAD]
    ticket = ds.primary.query("cluster == 'Cluster 1'").iloc[0]
    result = evidence(ds, FilterContext(entity_id=ticket["number"]))
    assert result["observed"] == pytest.approx(ticket["resolutionHours"])
    assert result["baseline"] == pytest.approx(ticket["resolutionHoursBaseline"])


def test_a_selection_across_findings_asks_which(data) -> None:
    result = evidence(data[TAD], FilterContext())
    assert result["status"] == "choose"
    assert {f["value"]: f["count"] for f in result["findings"]} == tickets.PATTERN_TOTALS


def test_normal_work_is_no_finding(data) -> None:
    assert evidence(data[TAD], context(pattern=["Normal"]))["status"] == "none"


def test_what_cannot_be_measured_is_insufficient_not_weaker(data) -> None:
    unresolved = evidence(data[APR], context(disposition=["Unresolved"]))
    assert unresolved["status"] == "insufficient"
    assert "never as unused" in unresolved["message"]
    assert "observed" not in unresolved
    unassigned = evidence(data[LO], context(**{"class": ["Unassigned"]}))
    assert unassigned["status"] == "insufficient"


# -- Performance (NFR-P2) -----------------------------------------------


@pytest.mark.parametrize("solution", [TAD, LO, APR])
def test_any_filter_answers_every_view_inside_200_ms(data, solution) -> None:
    ds = data[solution]
    run(ds, FilterContext())
    worst = 0.0
    for flt in combinations(ds, 12, seed=3):
        start = time.perf_counter()
        run(ds, flt)
        worst = max(worst, time.perf_counter() - start)
    assert worst < 0.2, f"{solution}: {worst * 1000:.0f} ms"


# -- Genericity (FR-EV4) ------------------------------------------------


def names_in(module: Path) -> set[str]:
    """Every identifier and string literal in a module, docstrings aside."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            found.add(node.value)
    return found


@pytest.mark.parametrize(
    "module",
    [
        "analytics/query.py",
        "analytics/evidence.py",
        "analytics/store.py",
        "analytics/schema.py",
        "api/analytics.py",
    ],
)
def test_the_engine_and_api_name_no_methodology(module) -> None:
    """Everything specific lives in descriptors and generators (FR-EV4)."""
    specific = (
        TAD,
        LO,
        APR,
        "ticket",
        "licen",
        "cluster",
        "pattern",
        "reassign",
        "seat",
        "disposition",
        "assignmentGroup",
    )
    names = {n.lower() for n in names_in(APP / module)}
    for word in specific:
        assert not [n for n in names if word.lower() in n], (module, word)


def test_a_descriptor_naming_something_missing_fails_when_built() -> None:
    from app.analytics.descriptors.tickets import TICKETS

    with pytest.raises(ValueError, match="unknown measure"):
        Dashboard.model_validate(
            {**TICKETS.model_dump(), "kpis": [{"id": "x", "label": "x", "measure": "nope"}]}
        )

    broken = TICKETS.model_copy(
        update={"evidence": TICKETS.evidence.model_copy(update={"score": "noSuchColumn"})}
    )
    source = type(SOURCES[0])(broken, SOURCES[0].generate)
    with pytest.raises(ValueError, match="noSuchColumn"):
        build(source)


# -- API ----------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as connection:
        yield connection


def test_the_dashboard_is_served_as_data(client) -> None:
    body = client.get(f"/api/analytics/{TAD}/dashboard").json()
    assert body["descriptor"]["solutionId"] == TAD
    assert body["palettes"]["pattern"]["Reassignment loop"] == "series-5"
    assert body["domains"]["priority"] == ["P1", "P2", "P3", "P4"]
    assert [d["solutionId"] for d in client.get("/api/analytics").json()] == [TAD, LO, APR]


def test_queries_records_and_evidence_over_http(client) -> None:
    flt = {"dimensions": {"cluster": ["Cluster 27"]}}
    answer = client.post(f"/api/analytics/{TAD}/query", json={"filter": flt})
    assert answer.status_code == 200
    body = answer.json()
    assert body["views"]["k-anomalies"]["value"] == 175
    assert body["elapsedMs"] < 200
    page = client.post(f"/api/analytics/{TAD}/records", json={"filter": flt, "page": 6}).json()
    assert page["total"] == 175 and len(page["rows"]) == 175 - 150
    why = client.post(f"/api/analytics/{TAD}/evidence", json={"filter": flt}).json()
    assert why["finding"]["value"] == "Reassignment loop"
    ranged = client.post(
        f"/api/analytics/{TAD}/query",
        json={"filter": {"timeRange": ["2026-06-01", "2026-06-30"]}, "views": ["k-tickets"]},
    ).json()
    june = build_all()[TAD].primary["month"].astype(str) == "2026-06"
    assert ranged["views"]["k-tickets"]["value"] == int(june.sum())


def test_refusals_over_http(client) -> None:
    assert client.post("/api/analytics/nope/query", json={}).status_code == 404
    assert (
        client.post(
            f"/api/analytics/{TAD}/query", json={"filter": {"dimensions": {"bogus": ["x"]}}}
        ).status_code
        == 422
    )
    assert client.post(f"/api/analytics/{TAD}/query", json={"views": ["nope"]}).status_code == 422
    assert (
        client.post(f"/api/analytics/{TAD}/records", json={"table": "cluster-table"}).status_code
        == 422
    )
    assert (
        client.post(f"/api/analytics/{TAD}/records", json={"sortBy": "nothing"}).status_code == 422
    )


def test_every_methodology_has_a_dashboard_its_solution_can_open() -> None:
    """Run opens `dashboardId`, which is the solution id: each must be served."""
    from app.knowledge.methodologies import METHODOLOGIES

    assert [m.id for m in METHODOLOGIES] == [s.dashboard.solution_id for s in SOURCES]
