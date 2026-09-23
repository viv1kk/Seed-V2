"""The declared stack at Planting (D-13, FR-N5).

The Planting stage shows what the seed was told it is planted into,
before anything has been reached. The same declared inventory is where
Discovery begins, from one source, so the two can never disagree. What
is shown at Planting is a declaration, not a discovery: the environment
graph stays empty until Discovery runs (G-2).
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.seed import SeedUpload, initialize
from app.domain.lifecycle import LifecycleState
from app.environment.acme import ACME, SYSTEM_ORDER, declared_inventory
from app.knowledge.seed_loader import read_bundled
from app.main import app
from app.runtime import state
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE
from narrative import run_to_end


@pytest.fixture
def client() -> TestClient:
    state.reset()
    with TestClient(app) as connection:
        yield connection
    state.reset()


def test_the_declared_inventory_is_the_system_order_with_labels() -> None:
    declared = declared_inventory()
    assert [system["id"] for system in declared] == list(SYSTEM_ORDER)
    assert [system["label"] for system in declared] == [
        ACME.by_id[system].label for system in SYSTEM_ORDER
    ]
    assert len(declared) == 5


def test_planting_records_the_declared_stack_and_reveals_nothing(client: TestClient) -> None:
    snapshot = client.post("/api/seed/initialize", json={"layers": read_bundled()}).json()

    assert snapshot["lifecycle"] == LifecycleState.INITIALIZED
    assert snapshot["declared"] == declared_inventory()
    # Declared is not discovered: nothing is in the graph yet (G-2).
    assert snapshot["environment"] == {}


def test_the_plant_event_carries_the_declared_stack(client: TestClient) -> None:
    """A client watching the plant shows the stack without a reload (FR-E5)."""
    client.post("/api/seed/initialize", json={"layers": read_bundled()})

    loaded = state.events.all()[0]
    assert loaded.type == "seed.loaded"
    assert loaded.payload["declared"] == state.declared


def test_the_stack_is_empty_before_planting_and_after_reset(client: TestClient) -> None:
    assert client.get("/api/state").json()["declared"] == []
    client.post("/api/seed/initialize", json={"layers": read_bundled()})
    assert client.get("/api/state").json()["declared"]

    state.reset()
    assert client.get("/api/state").json()["declared"] == []


@pytest.mark.asyncio
async def test_discovery_begins_from_the_stack_planting_showed() -> None:
    """One source: the first discovery beat names exactly what Planting listed."""
    state.reset()
    try:
        await initialize(SeedUpload(layers=read_bundled()))
        planted = [system["id"] for system in state.declared]

        runner = SimulationEngine(state, NARRATIVE, total_duration=0.2, narrative_weight=100.0)
        runner.set_speed(Speed.INSTANT)
        await run_to_end(runner)
        assert runner.status is RunStatus.COMPLETE

        inventory = next(e for e in state.events.all() if e.type == "discovery.inventory.loaded")
        assert inventory.payload["declared"] == planted

        # The declaration outlives the run unchanged: it is what the seed
        # was told, and Discovery's findings live in the graph instead.
        assert state.declared == declared_inventory()
        revealed: dict[str, Any] = {n["id"]: n for n in state.environment["nodes"]}
        assert all(system in revealed for system in planted)
    finally:
        state.reset()
