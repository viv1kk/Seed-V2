"""FastAPI application.

The application object is imported by `run.py` before it reports
readiness, so the cost of importing dependencies is paid at launch
rather than on the first request (A-1).
"""

from fastapi import FastAPI

from app.api import demo, events, health, state

app = FastAPI(
    title="Systems V1",
    description="Deterministic simulation of a methodology-driven analytical system.",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(state.router, prefix="/api", tags=["state"])
app.include_router(events.router, prefix="/api", tags=["events"])
# Removed at M2, together with the module it points at.
app.include_router(demo.router, prefix="/api", tags=["demo"])
