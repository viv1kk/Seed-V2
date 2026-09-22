"""Readiness endpoint.

`run.py` polls this to decide when the backend has finished importing
and binding, so readiness is reported once rather than guessed at
(A-1, NFR-P1).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
