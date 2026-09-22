"""Planting the seed.

Two steps, because the screen has two (§12, §48): the layers are supplied
one at a time and each is parsed the moment it lands, then initialization
commits all three at once.

Both endpoints take the file *text*. The browser reads the dropped file
and posts its contents, which keeps the seam free of multipart handling
and, more usefully, keeps parsing stateless: nothing is held between the
parse of a layer and the initialization that commits it. The frontend
holds the three files until the operator initializes, and System State
remains the only server-side state there is (FR-L5).
"""

from fastapi import APIRouter

from app.domain.events import Category
from app.domain.lifecycle import LifecycleState, assert_transition
from app.domain.schema import Schema
from app.knowledge.seed_loader import (
    LAYER_FILENAMES,
    LAYER_ORDER,
    LAYER_ROLES,
    Layer,
    LayerSummary,
    load_layer,
    load_seed,
    read_bundled,
)
from app.domain.state import StateSnapshot
from app.runtime import state

router = APIRouter(prefix="/seed")


class LayerUpload(Schema):
    """One supplied layer, as text."""

    layer: Layer
    content: str


class SeedUpload(Schema):
    """All three layers, supplied together at initialization (FR-S3)."""

    layers: dict[Layer, str]


class LayerDescriptor(Schema):
    """What the seed screen needs to draw one slot before anything is dropped."""

    layer: Layer
    filename: str
    role: str


@router.get("/layers", response_model=list[LayerDescriptor])
async def get_layers() -> list[LayerDescriptor]:
    """The three slots, in order, with the question each layer answers."""
    return [
        LayerDescriptor(layer=layer, filename=LAYER_FILENAMES[layer], role=LAYER_ROLES[layer])
        for layer in LAYER_ORDER
    ]


@router.post("/parse", response_model=LayerSummary)
async def parse(upload: LayerUpload) -> LayerSummary:
    """Validate and summarise one layer, without committing to it.

    This is what makes the per-layer summary on the seed screen real
    (FR-S5): the headings reported are the headings in the file that was
    just dropped. A file that cannot be read as Markdown is refused here,
    with the reason (FR-S4).
    """
    return load_layer(upload.layer, upload.content)


@router.get("/bundled", response_model=SeedUpload)
async def get_bundled() -> SeedUpload:
    """The seed files shipped with the repository (FR-S7).

    The hidden affordance fetches these and supplies them exactly as a
    dropped file would be, so the shortcut skips the file picker and
    nothing else.
    """
    return SeedUpload(layers=read_bundled())


@router.post("/initialize", response_model=StateSnapshot)
async def initialize(upload: SeedUpload) -> StateSnapshot:
    """Plant the seed and initialize the system (FR-S2, FR-S3).

    All three layers are validated before anything is recorded, so a
    rejected seed leaves the system exactly as it was. The transition is
    the last thing to happen, and it is what moves the interface off the
    seed screen.
    """
    # Checked before anything is parsed or recorded, so a second plant is
    # refused by the state machine without leaving a seed behind (FR-L3).
    assert_transition(state.lifecycle, LifecycleState.INITIALIZED)

    summary = load_seed(upload.layers)
    state.seed = summary.model_dump(by_alias=True)

    state.record(
        type="seed.loaded",
        category=Category.SUCCESS,
        message=(
            f"Seed accepted. Three layers registered from {summary.heading_count} "
            "parsed headings."
        ),
        payload={
            "layers": [
                {
                    "layer": entry.layer,
                    "filename": entry.filename,
                    "title": entry.title,
                    "headings": entry.heading_count,
                    "sections": entry.sections,
                }
                for entry in summary.layers
            ]
        },
    )

    state.transition(LifecycleState.INITIALIZED)
    return state.snapshot()
