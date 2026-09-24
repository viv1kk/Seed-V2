"""The analytics API: dashboards as data, and figures for a filter context.

Generic over methodologies: nothing here names one (FR-EV4). A dashboard
is whatever its descriptor declares, and every figure is aggregated from
record-level rows when it is asked for (FR-AN5).

- `GET  /analytics` lists the dashboards.
- `GET  /analytics/{id}/dashboard` returns the descriptor, with each
  dimension's values and each coloured value's role.
- `POST /analytics/{id}/query` answers a filter context for some or all views.
- `POST /analytics/{id}/records` pages a record table.
- `POST /analytics/{id}/evidence` explains the finding a filter narrows to.

Each answer carries the milliseconds it took, so NFR-P2's 200 ms is
measured where it is served rather than assumed.
"""

import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import Field

from app.analytics.evidence import evidence
from app.analytics.generator import CALIBRATIONS, EVERY, STEPS, week_of
from app.analytics.query import Engine, FilterContext, QueryError, run
from app.analytics.store import STORE, Dataset, UnknownDashboard
from app.domain.schema import Schema

router = APIRouter()


class QueryRequest(Schema):
    filter: FilterContext = Field(default_factory=FilterContext)
    views: list[str] | None = None


class RecordsRequest(Schema):
    filter: FilterContext = Field(default_factory=FilterContext)
    table: str = "records"
    page: int = Field(default=0, ge=0)
    sort_by: str | None = None
    descending: bool | None = None


class EvidenceRequest(Schema):
    filter: FilterContext = Field(default_factory=FilterContext)


def _dataset(solution_id: str) -> Dataset:
    try:
        return STORE.get(solution_id)
    except UnknownDashboard as error:
        raise HTTPException(404, str(error.args[0])) from error


def _timed(answer) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = answer()
    except (QueryError, KeyError) as error:
        raise HTTPException(422, str(error)) from error
    return {**result, "elapsedMs": round((time.perf_counter() - start) * 1000, 1)}


@router.get("/analytics")
async def dashboards() -> list[dict[str, str]]:
    return [
        {"solutionId": d.dashboard.solution_id, "title": d.dashboard.title}
        for d in STORE.datasets.values()
    ]


@router.get("/analytics/{solution_id}/dashboard")
async def dashboard(solution_id: str) -> dict[str, Any]:
    dataset = _dataset(solution_id)
    collection = None
    if dataset.dashboard.collection:
        # Life's clock, so the dashboard can name the week a step is.
        collection = {
            "steps": STEPS,
            "every": EVERY,
            "calibrations": CALIBRATIONS - 1,
            "weeks": [week_of(step) for step in range(STEPS + 1)],
        }
    return {
        "descriptor": dataset.dashboard.model_dump(by_alias=True),
        "domains": dataset.domains,
        "palettes": dataset.palettes,
        "collection": collection,
    }


@router.post("/analytics/{solution_id}/query")
async def query(solution_id: str, request: QueryRequest) -> dict[str, Any]:
    dataset = _dataset(solution_id)
    return _timed(lambda: run(dataset, request.filter, request.views))


@router.post("/analytics/{solution_id}/records")
async def records(solution_id: str, request: RecordsRequest) -> dict[str, Any]:
    dataset = _dataset(solution_id)

    def page() -> dict[str, Any]:
        table = dataset.dashboard.view(request.table)
        if getattr(table, "kind", None) != "records":
            raise QueryError(f"{request.table} is not a record table.")
        return Engine(dataset, request.filter).records(
            table, request.page, request.sort_by, request.descending
        )

    try:
        return _timed(page)
    except StopIteration as error:
        raise HTTPException(422, f"Unknown table {request.table!r}.") from error


@router.post("/analytics/{solution_id}/evidence")
async def explain(solution_id: str, request: EvidenceRequest) -> dict[str, Any]:
    dataset = _dataset(solution_id)
    return _timed(lambda: evidence(dataset, request.filter))
