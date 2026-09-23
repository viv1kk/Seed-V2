"""The seed: its content, its parse, and the plant that initializes on it.

Three things are under test here, and they pull in different directions,
which is why they are tested together.

FR-S5 requires the per-layer summary to be *derived from the file*, so a
different file must produce a different summary. FR-S6 requires seed
content *not* to alter behaviour, so a different file must produce an
identical run. Both hold, and they meet at exactly one event: `seed.loaded`
reports what was parsed, and nothing downstream reads it.

FR-S1 is the third: the files shipped in `seeds/` are a deliverable, so
their absence or emptiness is a test failure rather than a missing fixture.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.lifecycle import LifecycleState
from app.knowledge.seed_loader import (
    LAYER_FILENAMES,
    LAYER_ORDER,
    SEEDS_DIRECTORY,
    Layer,
    SeedRejected,
    load_layer,
    load_seed,
    parse_headings,
    read_bundled,
)
from app.main import app
from app.runtime import state
from app.simulation.engine import SimulationEngine
from app.simulation.protocol import RunStatus, Speed
from app.simulation.workflows.registry import NARRATIVE
from narrative import run_to_end

MINIMAL = "# Layer\n\nOne line of content.\n"

#: A valid seed whose content has nothing to do with the real one. FR-S6
#: says the run must not notice.
UNRELATED = {
    layer: f"# Not the real {layer}\n\n## A section\n\nContents unrelated to anything.\n"
    for layer in LAYER_ORDER
}


@pytest.fixture
def client() -> TestClient:
    """A client over the process-wide state, cleared before and after.

    The seed API writes to the one `SystemState` the process has (FR-L5),
    so a test that plants must leave it as it found it.
    """
    state.reset()
    with TestClient(app) as connection:
        yield connection
    state.reset()


# -- Heading parsing --------------------------------------------------


def test_headings_are_read_with_their_levels() -> None:
    headings = parse_headings("# One\n\n## Two\n\n### Three\n")
    assert [(entry.level, entry.text) for entry in headings] == [
        (1, "One"),
        (2, "Two"),
        (3, "Three"),
    ]


def test_hashes_inside_a_code_fence_are_not_headings() -> None:
    """Both real seed files contain fenced examples."""
    text = "# Real\n\n```markdown\n# Sample\n## Sample\n```\n\n## Also real\n"
    assert [entry.text for entry in parse_headings(text)] == ["Real", "Also real"]


def test_a_tilde_fence_closes_only_on_tildes() -> None:
    text = "~~~\n# Inside\n```\n# Still inside\n~~~\n\n# Outside\n"
    assert [entry.text for entry in parse_headings(text)] == ["Outside"]


def test_a_hash_without_a_space_is_not_a_heading() -> None:
    assert parse_headings("#hashtag\n") == []


def test_a_closing_hash_sequence_is_not_part_of_the_text() -> None:
    assert parse_headings("## Title ##\n")[0].text == "Title"


def test_seven_hashes_is_not_a_heading() -> None:
    assert parse_headings("####### Too deep\n") == []


# -- Per-layer summary ------------------------------------------------


def test_the_summary_is_derived_from_the_supplied_file() -> None:
    """FR-S5: not a fixture. Different content, different summary."""
    one = load_layer(Layer.CORE, "# A\n\n## B\n\n## C\n\n### D\n")
    assert one.title == "A"
    assert one.heading_count == 4
    assert one.sections == 2
    assert one.topics == 1

    other = load_layer(Layer.CORE, MINIMAL)
    assert other.title == "Layer"
    assert other.sections == 0
    assert other != one


def test_a_layer_with_no_headings_loads_with_an_empty_outline() -> None:
    """R-9: a headingless file is plain, not invalid."""
    summary = load_layer(Layer.PROTECTION, "Just prose, with no structure at all.\n")
    assert summary.title is None
    assert summary.headings == []
    assert summary.heading_count == 0
    assert summary.lines == 1


def test_the_summary_names_the_layer_and_its_filename() -> None:
    summary = load_layer(Layer.ADAPTATION, MINIMAL)
    assert summary.layer is Layer.ADAPTATION
    assert summary.filename == "adaptation.md"


# -- Validation -------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        ("", "the file is empty"),
        ("   \n\n  \n", "the file is empty"),
        ("# Title\n\x00binary\n", "binary content"),
        ("# Title\n\n```python\nnever closed\n", "is never closed"),
    ],
)
def test_an_unusable_layer_is_rejected_with_a_reason(content: str, reason: str) -> None:
    """FR-S4: rejected, and the caller is told why."""
    with pytest.raises(SeedRejected) as refusal:
        load_layer(Layer.CORE, content)

    assert refusal.value.layer is Layer.CORE
    assert reason in refusal.value.reason
    # The message names the file, so the screen can point at the slot.
    assert "core.md" in str(refusal.value)


def test_all_three_layers_are_required() -> None:
    """FR-S3."""
    with pytest.raises(SeedRejected) as refusal:
        load_seed({Layer.CORE: MINIMAL, Layer.ADAPTATION: MINIMAL})

    assert refusal.value.layer is Layer.PROTECTION
    assert "not supplied" in refusal.value.reason


def test_the_missing_layer_is_reported_before_a_rejected_one() -> None:
    """A seed with a gap is incomplete first and invalid second."""
    with pytest.raises(SeedRejected) as refusal:
        load_seed({Layer.CORE: ""})

    assert refusal.value.layer is Layer.ADAPTATION


# -- The shipped files ------------------------------------------------


def test_the_repository_ships_three_seed_files() -> None:
    """FR-S1: these are a deliverable, not a fixture."""
    for filename in LAYER_FILENAMES.values():
        assert (SEEDS_DIRECTORY / filename).is_file(), f"{filename} is missing"


def test_the_shipped_files_parse_into_a_substantial_outline() -> None:
    """A seed that parses to three headings would not survive the question.

    The thresholds are deliberately low. They catch a truncated or
    placeholder file without pinning the content, which is still being
    written.
    """
    summary = load_seed(read_bundled())

    assert summary.heading_count > 60
    for entry in summary.layers:
        assert entry.title is not None
        assert entry.sections >= 4, f"{entry.filename} has {entry.sections} sections"
        assert entry.lines > 50


def test_each_shipped_layer_declares_its_own_subject() -> None:
    """Three files, three titles. A copied file is a real failure mode."""
    titles = {entry.title for entry in load_seed(read_bundled()).layers}
    assert titles == {"Core", "Adaptation", "Protection"}


def test_the_shipped_protection_file_names_the_rules_the_engine_mirrors() -> None:
    """M5 mirrors this rule set in Python. The identifiers are the contract."""
    text = (SEEDS_DIRECTORY / "protection.md").read_text(encoding="utf-8")
    for decision in ("ALLOW", "DENY", "ESCALATE"):
        assert decision in text
    assert "PR-000" in text


# -- Planting ---------------------------------------------------------


def test_the_seed_screen_is_told_what_the_three_slots_are(client: TestClient) -> None:
    response = client.get("/api/seed/layers")
    assert response.status_code == 200

    body = response.json()
    assert [entry["layer"] for entry in body] == list(LAYER_ORDER)
    assert all(entry["role"].endswith("?") for entry in body)


def test_parsing_a_layer_does_not_commit_to_it(client: TestClient) -> None:
    response = client.post(
        "/api/seed/parse", json={"layer": "core", "content": "# A\n\n## B\n"}
    )
    assert response.status_code == 200
    assert response.json()["sections"] == 1

    # Nothing happened to the system. The parse is a preview.
    assert state.lifecycle is LifecycleState.UNINITIALIZED
    assert state.events.last_sequence == 0


def test_a_rejected_layer_returns_the_reason(client: TestClient) -> None:
    """FR-S4 over the wire."""
    response = client.post("/api/seed/parse", json={"layer": "adaptation", "content": ""})

    assert response.status_code == 400
    body = response.json()
    assert body["layer"] == "adaptation"
    assert body["reason"] == "the file is empty"


def test_the_bundled_seed_is_served_for_the_hidden_affordance(client: TestClient) -> None:
    """FR-S7: the shortcut skips the file picker and nothing else."""
    response = client.get("/api/seed/bundled")
    assert response.status_code == 200

    layers = response.json()["layers"]
    assert set(layers) == {layer.value for layer in LAYER_ORDER}
    assert layers["core"] == (SEEDS_DIRECTORY / "core.md").read_text(encoding="utf-8")


def test_planting_the_seed_initializes_the_system(client: TestClient) -> None:
    """FR-S2, FR-S3: three layers in, lifecycle advanced."""
    response = client.post("/api/seed/initialize", json={"layers": read_bundled()})
    assert response.status_code == 200

    snapshot = response.json()
    assert snapshot["lifecycle"] == LifecycleState.INITIALIZED
    assert snapshot["phase"] == "INIT"
    assert snapshot["seed"]["headingCount"] > 60

    types = [event.type for event in state.events.all()]
    assert types == ["seed.loaded", "lifecycle.transition"]


def test_the_plant_records_what_was_parsed(client: TestClient) -> None:
    """The stream is the record, so the parse has to appear in it (FR-E9)."""
    client.post("/api/seed/initialize", json={"layers": read_bundled()})

    loaded = state.events.all()[0]
    layers = loaded.payload["layers"]
    assert [entry["layer"] for entry in layers] == list(LAYER_ORDER)
    assert [entry["title"] for entry in layers] == ["Core", "Adaptation", "Protection"]
    assert all(entry["headings"] > 0 for entry in layers)


def test_an_incomplete_seed_leaves_the_system_untouched(client: TestClient) -> None:
    response = client.post(
        "/api/seed/initialize", json={"layers": {"core": MINIMAL, "adaptation": MINIMAL}}
    )

    assert response.status_code == 400
    assert response.json()["layer"] == "protection"
    assert state.lifecycle is LifecycleState.UNINITIALIZED
    assert state.seed is None
    assert state.events.last_sequence == 0


def test_a_rejected_seed_leaves_no_seed_behind(client: TestClient) -> None:
    """Validation precedes every write, so a refusal is not a partial plant."""
    layers = dict(read_bundled())
    layers[Layer.PROTECTION] = "# Protection\n\n```\nunclosed\n"

    response = client.post("/api/seed/initialize", json={"layers": layers})

    assert response.status_code == 400
    assert state.seed is None
    assert state.events.last_sequence == 0


def test_planting_twice_is_refused(client: TestClient) -> None:
    """The state machine answers this, not a second check (FR-L3)."""
    assert client.post("/api/seed/initialize", json={"layers": read_bundled()}).status_code == 200
    before = state.events.last_sequence

    response = client.post("/api/seed/initialize", json={"layers": read_bundled()})

    assert response.status_code == 409
    assert "INITIALIZED" in response.json()["detail"]
    assert state.events.last_sequence == before


def test_reset_returns_to_the_seed_screen(client: TestClient) -> None:
    """FR-O4: after reset the seed can be planted again."""
    client.post("/api/seed/initialize", json={"layers": read_bundled()})

    response = client.post("/api/operator/reset")
    assert response.status_code == 200
    assert response.json()["lifecycle"] == LifecycleState.UNINITIALIZED
    assert response.json()["seed"] is None

    assert client.post("/api/seed/initialize", json={"layers": read_bundled()}).status_code == 200


def test_the_run_cannot_be_started_before_the_seed_is_planted(client: TestClient) -> None:
    response = client.post("/api/operator/start")

    assert response.status_code == 409
    assert "Plant the seed" in response.json()["detail"]


# -- FR-S6 ------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_content_does_not_alter_the_run() -> None:
    """FR-S6: the methodologies and outcomes are fixed, whatever is planted.

    The plant itself reports what it parsed, which is FR-S5 and is meant
    to differ. Everything after the plant must not.
    """

    async def run_after_planting(layers: dict[Layer, str]) -> list[tuple]:
        from app.api.seed import initialize  # local, to keep the module import light
        from app.api.seed import SeedUpload

        state.reset()
        await initialize(SeedUpload(layers=layers))
        planted = state.events.last_sequence

        runner = SimulationEngine(
            state, NARRATIVE, total_duration=0.2, narrative_weight=100.0
        )
        runner.set_speed(Speed.INSTANT)
        await run_to_end(runner)
        assert runner.status is RunStatus.COMPLETE

        return [
            (event.sequence, event.type, event.phase, event.category, event.message)
            for event in state.events.all()
            if event.sequence > planted
        ]

    real = await run_after_planting(read_bundled())
    unrelated = await run_after_planting(UNRELATED)
    state.reset()

    assert real == unrelated
    assert len(real) > 10


async def _tick() -> None:
    import asyncio

    await asyncio.sleep(0.01)


def test_the_seed_summary_survives_the_round_trip_to_state() -> None:
    """State carries the summary under wire names, since that is what ships."""
    state.reset()
    try:
        summary = load_seed(read_bundled())
        assert "headingCount" in summary.model_dump(by_alias=True)
        assert Path(SEEDS_DIRECTORY, summary.of(Layer.CORE).filename).is_file()
    finally:
        state.reset()
