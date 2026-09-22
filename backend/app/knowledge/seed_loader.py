"""The seed loader.

Three layers are supplied at INIT, validated, and parsed for their
heading structure. The summary shown on the seed screen is derived from
the file that was actually supplied (FR-S5) --- it is not a fixture, and
a different file produces a different summary.

What the summary does *not* do is change how the system behaves (FR-S6).
The methodologies, the feasibility outcomes and the policy rules are
fixed in code. The seed files are the document those fixed behaviours
were written from, and they are a deliverable in their own right (FR-S1):
they are what you open when someone asks what is actually in the seed.

Parsing is deliberately small. ATX headings outside fenced code blocks,
and nothing else. A Markdown parser would be a dependency bought to
extract six lines of structure, and §66 is explicit that the knowledge
representation should not be over-engineered before the demo needs it.
"""

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from app.domain.schema import Schema

SEEDS_DIRECTORY = Path(__file__).resolve().parents[3] / "seeds"

MAX_HEADING_LEVEL = 6
FENCES = ("```", "~~~")


class Layer(StrEnum):
    """The three persistent layers of §4."""

    CORE = "core"
    ADAPTATION = "adaptation"
    PROTECTION = "protection"


LAYER_ORDER: tuple[Layer, ...] = (Layer.CORE, Layer.ADAPTATION, Layer.PROTECTION)

LAYER_FILENAMES: dict[Layer, str] = {
    Layer.CORE: "core.md",
    Layer.ADAPTATION: "adaptation.md",
    Layer.PROTECTION: "protection.md",
}

LAYER_ROLES: dict[Layer, str] = {
    Layer.CORE: "How should this problem be thought about and solved?",
    Layer.ADAPTATION: "How is this methodology applied to this specific environment?",
    Layer.PROTECTION: "Is this action permitted, and who must authorise it?",
}


class SeedRejected(Exception):
    """A supplied layer is not usable, with the reason a person needs (FR-S4)."""

    def __init__(self, layer: Layer, reason: str) -> None:
        self.layer = layer
        self.reason = reason
        super().__init__(f"{LAYER_FILENAMES[layer]}: {reason}")


class Heading(Schema):
    """One ATX heading, with the level that gives the outline its shape."""

    level: int
    text: str


class LayerSummary(Schema):
    """What was found in one supplied layer (FR-S5).

    `sections` and `topics` are the level-2 and level-3 counts, which is
    what the seed screen reports. The flat heading list is carried too,
    so a later milestone can show the outline itself without re-parsing.
    """

    layer: Layer
    filename: str
    title: str | None
    headings: list[Heading]
    heading_count: int
    sections: int
    topics: int
    lines: int
    characters: int


class SeedSummary(Schema):
    """The three layers, as registered at initialization."""

    layers: list[LayerSummary] = Field(default_factory=list)
    heading_count: int = 0

    def of(self, layer: Layer) -> LayerSummary:
        return next(entry for entry in self.layers if entry.layer is layer)


def parse_headings(text: str) -> list[Heading]:
    """Extract ATX headings, ignoring anything inside a fenced block.

    A rule of hashes inside a code fence is sample content, not
    structure. Both seed files contain fenced examples, so skipping
    fences is what keeps the reported outline honest.
    """
    headings: list[Heading] = []
    fence: str | None = None

    for line in text.splitlines():
        stripped = line.strip()

        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue

        if stripped.startswith(FENCES):
            fence = stripped[:3]
            continue

        if not stripped.startswith("#"):
            continue

        level = len(stripped) - len(stripped.lstrip("#"))
        if level > MAX_HEADING_LEVEL:
            continue

        remainder = stripped[level:]
        # `#hashtag` is not a heading; ATX requires the space.
        if remainder and not remainder.startswith((" ", "\t")):
            continue

        # Trailing hashes are a closing sequence, not part of the text.
        headings.append(Heading(level=level, text=remainder.strip().rstrip("#").strip()))

    return headings


def _validate(layer: Layer, text: str) -> None:
    """Reject what cannot be read as Markdown, with a reason (FR-S4).

    Markdown accepts almost anything, so the checks here are the few
    faults that genuinely make a file unusable rather than merely plain.
    A file with no headings is *not* rejected: it loads with an empty
    outline (R-9).
    """
    if not text.strip():
        raise SeedRejected(layer, "the file is empty")

    if "\x00" in text:
        raise SeedRejected(layer, "the file contains binary content, not Markdown text")

    fence: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if fence is None:
            if stripped.startswith(FENCES):
                fence = stripped[:3]
        elif stripped.startswith(fence):
            fence = None

    if fence is not None:
        raise SeedRejected(layer, f"a code block opened with {fence} is never closed")


def load_layer(layer: Layer, text: str) -> LayerSummary:
    """Validate one supplied layer and summarise what it contains."""
    _validate(layer, text)
    headings = parse_headings(text)
    top = next((heading.text for heading in headings if heading.level == 1), None)

    return LayerSummary(
        layer=layer,
        filename=LAYER_FILENAMES[layer],
        title=top,
        headings=headings,
        heading_count=len(headings),
        sections=sum(1 for heading in headings if heading.level == 2),
        topics=sum(1 for heading in headings if heading.level == 3),
        lines=len(text.splitlines()),
        characters=len(text),
    )


def load_seed(supplied: dict[Layer, str]) -> SeedSummary:
    """Validate and summarise all three layers (FR-S3).

    Every layer is required. A partial seed is not a seed, and the
    missing layer is named so the screen can say which one.
    """
    missing = [layer for layer in LAYER_ORDER if layer not in supplied]
    if missing:
        raise SeedRejected(missing[0], "the layer was not supplied")

    layers = [load_layer(layer, supplied[layer]) for layer in LAYER_ORDER]
    return SeedSummary(
        layers=layers,
        heading_count=sum(entry.heading_count for entry in layers),
    )


def read_bundled() -> dict[Layer, str]:
    """Read the seed files shipped with the repository (FR-S1, FR-S7).

    The hidden operator affordance uses this to skip the file picker. It
    skips only the picker: the returned text goes through the same
    validation and the same parse as a dropped file, so the summary on
    screen is produced the same way either way.
    """
    supplied: dict[Layer, str] = {}
    for layer, filename in LAYER_FILENAMES.items():
        path = SEEDS_DIRECTORY / filename
        if not path.is_file():
            raise SeedRejected(layer, f"{path} is missing from the repository")
        supplied[layer] = path.read_text(encoding="utf-8")
    return supplied
