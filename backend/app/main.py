"""FastAPI application.

The application object is imported by `run.py` before it reports
readiness, so the cost of importing dependencies is paid at launch
rather than on the first request (A-1).
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import (
    environment,
    events,
    health,
    human,
    operator,
    protection,
    seed,
    solutions,
    state,
)
from app.domain.lifecycle import IllegalTransition
from app.domain.solutions import IllegalSolutionTransition
from app.knowledge.seed_loader import SeedRejected
from app.simulation.protocol import EngineError

app = FastAPI(
    title="Systems V1",
    description="Deterministic simulation of a methodology-driven analytical system.",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(state.router, prefix="/api", tags=["state"])
app.include_router(seed.router, prefix="/api", tags=["seed"])
app.include_router(protection.router, prefix="/api", tags=["protection"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(operator.router, prefix="/api", tags=["operator"])
app.include_router(human.router, prefix="/api", tags=["human"])
app.include_router(solutions.router, prefix="/api", tags=["solutions"])
app.include_router(environment.router, prefix="/api", tags=["environment"])


@app.exception_handler(EngineError)
async def engine_refusal(_: object, error: EngineError) -> JSONResponse:
    """A refusal is a conflict with the current state, not a server fault."""
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.exception_handler(IllegalTransition)
async def illegal_transition(_: object, error: IllegalTransition) -> JSONResponse:
    """The state machine refused the move, and it names what it would allow."""
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.exception_handler(IllegalSolutionTransition)
async def illegal_solution_transition(_: object, error: IllegalSolutionTransition) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.exception_handler(SeedRejected)
async def seed_rejected(_: object, error: SeedRejected) -> JSONResponse:
    """A rejected layer is the caller's to fix, and it is told which and why (FR-S4)."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(error), "layer": error.layer, "reason": error.reason},
    )
