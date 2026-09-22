"""FastAPI application.

The application object is imported by `run.py` before it reports
readiness, so the cost of importing dependencies is paid at launch
rather than on the first request (A-1).
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api import events, health, human, operator, state
from app.simulation.protocol import EngineError

app = FastAPI(
    title="Systems V1",
    description="Deterministic simulation of a methodology-driven analytical system.",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(state.router, prefix="/api", tags=["state"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(operator.router, prefix="/api", tags=["operator"])
app.include_router(human.router, prefix="/api", tags=["human"])


@app.exception_handler(EngineError)
async def engine_refusal(_: object, error: EngineError) -> JSONResponse:
    """A refusal is a conflict with the current state, not a server fault."""
    return JSONResponse(status_code=409, content={"detail": str(error)})
