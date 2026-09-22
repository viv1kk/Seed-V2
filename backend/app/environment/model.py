"""The environment graph, as System State holds it.

Two things live here and they are kept apart on purpose. The *definition*
of an environment --- every node it has, where each is drawn, what each
dataset carries --- is static and lives beside this module in `acme.py`
(D-4). The *constructed graph* is what discovery has established so far,
and it lives in `state.environment` (FR-L5). A node is in the constructed
graph only once discovery has found it, so the state never claims to know
more than the run has shown.

`Environment` is the one way a workflow changes that graph. Every change
it makes is held as pending until the next event is recorded through it,
and that event carries the changed records in full. The frontend folds
those records into its snapshot by upsert, so a client that joins late,
or resyncs after a gap, converges on the same graph whichever order it
saw the snapshot and the event in (FR-E5, FR-E6). A change that never
reached the stream is the one kind of drift this cannot recover from,
which is why no change can bypass it.

The completion counts of FR-D9 are computed here, from the constructed
graph, every time the graph changes. Nothing anywhere states how many
systems, data sources or datasets there are.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.events import Category, Event, Severity
from app.domain.state import SystemState
from app.knowledge.methodologies import METHODOLOGIES


class NodeKind(StrEnum):
    """The node kinds of §50."""

    CLIENT = "client"
    SYSTEM = "system"
    SERVICE = "service"
    API = "api"
    DATABASE = "database"
    DATASET = "dataset"


class NodeStatus(StrEnum):
    """The node statuses of FR-D4.

    `requires-input` is a decision awaited, not a fault, and `error` is a
    fault, not a decision (FR-H4). A dataset refused by policy stays
    `detected`: it was genuinely found, and a refusal is the boundary
    working rather than a status of the thing refused. The refusal is
    carried beside the status, with the rule that made it.
    """

    UNKNOWN = "unknown"
    DETECTED = "detected"
    TESTING = "testing"
    VALIDATED = "validated"
    REQUIRES_INPUT = "requires-input"
    CONNECTED = "connected"
    ERROR = "error"


class EdgeKind(StrEnum):
    """The edge kinds of FR-D5."""

    CONTAINS = "contains"
    CONNECTS_TO = "connects_to"
    PROVIDES = "provides"
    DEPENDS_ON = "depends_on"


class Origin(StrEnum):
    """How the system came to know a node.

    `declared` is a system named in the Adaptation source inventory but
    not yet reached. `administrator-supplied` is FR-D6: known because a
    person handed it over, not because anything was discovered.
    """

    DECLARED = "declared"
    DISCOVERED = "discovered"
    ADMINISTRATOR = "administrator-supplied"


@dataclass(frozen=True)
class FieldProfile:
    """One profiled field of a dataset, and the concept it carries.

    Completeness is the share of sampled records in which the field is
    populated. These are simulated demo values (FR-A10), consistent with
    the trust assessment in `adaptation.md`, and they are the input M7's
    feasibility computation matches requirements against (FR-A2).
    """

    name: str
    concept: str
    completeness: float


@dataclass(frozen=True)
class NodeSpec:
    """One node of an environment definition.

    `parent` is the node this one hangs from, and the structural edge to
    it is derived from the kinds: a dataset is *provided* by its parent,
    anything else is *contained* in it. `x` and `y` are hand-authored
    (D-4) in the canvas units of the definition.

    The dataset facts --- mapped, security table, fields --- are what the
    workflow states to the policy engine when it asks to read, so a
    decision about a dataset follows from the definition of that dataset
    rather than from a flag written at the call site.
    """

    id: str
    kind: NodeKind
    label: str
    x: float
    y: float
    parent: str | None = None
    detail: str | None = None
    mapped: bool = False
    security_table: bool = False
    fields: tuple[FieldProfile, ...] = ()

    @property
    def concepts(self) -> frozenset[str]:
        return frozenset(profile.concept for profile in self.fields)


@dataclass(frozen=True)
class EdgeSpec:
    source: str
    target: str
    kind: EdgeKind
    detail: str | None = None

    @property
    def id(self) -> str:
        return f"{self.source}:{self.kind}:{self.target}"


@dataclass(frozen=True)
class Definition:
    """A whole environment: its nodes, its cross-links and its canvas."""

    client: str
    width: float
    height: float
    nodes: tuple[NodeSpec, ...]
    links: tuple[EdgeSpec, ...] = ()
    by_id: dict[str, NodeSpec] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        by_id = {node.id: node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise ValueError("Node identifiers must be unique.")
        for node in self.nodes:
            if node.parent is not None and node.parent not in by_id:
                raise ValueError(f"{node.id} hangs from unknown node {node.parent}.")
        for link in self.links:
            if link.source not in by_id or link.target not in by_id:
                raise ValueError(f"{link.id} joins an unknown node.")
        object.__setattr__(self, "by_id", by_id)

    def children(self, parent: str) -> tuple[NodeSpec, ...]:
        return tuple(node for node in self.nodes if node.parent == parent)

    def structural_edge(self, node: NodeSpec) -> EdgeSpec | None:
        if node.parent is None:
            return None
        kind = EdgeKind.PROVIDES if node.kind is NodeKind.DATASET else EdgeKind.CONTAINS
        return EdgeSpec(node.parent, node.id, kind)

    def system_of(self, node_id: str) -> str | None:
        node: NodeSpec | None = self.by_id[node_id]
        while node is not None:
            if node.kind is NodeKind.SYSTEM:
                return node.id
            node = self.by_id[node.parent] if node.parent else None
        return None


class Environment:
    """The constructed graph in System State, and the only way to change it."""

    def __init__(self, state: SystemState, definition: Definition) -> None:
        self.state = state
        self.definition = definition
        self._touched: list[str] = []
        self._new_edges: list[dict[str, Any]] = []
        self._new_sources: list[dict[str, Any]] = []

        if not state.environment:
            state.environment = {
                "client": definition.client,
                "canvas": {"width": definition.width, "height": definition.height},
                "nodes": [],
                "edges": [],
                "dataSources": [],
                "complete": False,
                "summary": None,
            }

    # -- Reading -----------------------------------------------------

    @property
    def _nodes(self) -> list[dict[str, Any]]:
        return self.state.environment["nodes"]

    @property
    def _edges(self) -> list[dict[str, Any]]:
        return self.state.environment["edges"]

    def node(self, node_id: str) -> dict[str, Any] | None:
        return next((node for node in self._nodes if node["id"] == node_id), None)

    def has(self, node_id: str) -> bool:
        return self.node(node_id) is not None

    def status(self, node_id: str) -> NodeStatus | None:
        node = self.node(node_id)
        return NodeStatus(node["status"]) if node else None

    # -- Changing ----------------------------------------------------

    def _touch(self, node_id: str) -> None:
        if node_id not in self._touched:
            self._touched.append(node_id)

    def reveal(
        self,
        *node_ids: str,
        status: NodeStatus = NodeStatus.DETECTED,
        origin: Origin = Origin.DISCOVERED,
    ) -> None:
        """Add nodes to the constructed graph, with their structural edges.

        Revealing a node already present updates its status and origin
        instead, which is how a declared system becomes a discovered one.
        Any cross-link whose ends are now both known is added with it, so
        a dependency appears the moment discovery could have seen it.
        """
        for node_id in node_ids:
            spec = self.definition.by_id[node_id]
            existing = self.node(node_id)
            if existing is not None:
                existing["status"] = status
                existing["origin"] = origin
            else:
                self._nodes.append(
                    {
                        "id": spec.id,
                        "kind": spec.kind,
                        "label": spec.label,
                        "detail": spec.detail,
                        "system": self.definition.system_of(spec.id),
                        "x": spec.x,
                        "y": spec.y,
                        "status": status,
                        "origin": origin,
                        "excludedBy": None,
                    }
                )
                edge = self.definition.structural_edge(spec)
                if edge is not None:
                    self._link(edge)
            self._touch(node_id)
        self._resolve_links()

    def set_status(self, status: NodeStatus, *node_ids: str) -> None:
        for node_id in node_ids:
            node = self.node(node_id)
            if node is None:
                raise KeyError(f"{node_id} has not been discovered.")
            node["status"] = status
            self._touch(node_id)

    def exclude(self, node_id: str, rule: str) -> None:
        """Record that policy refused this node, citing the deciding rule."""
        node = self.node(node_id)
        if node is None:
            raise KeyError(f"{node_id} has not been discovered.")
        node["excludedBy"] = rule
        self._touch(node_id)

    def profile(self, node_id: str) -> None:
        """Validate a dataset and register it as a data source for assessment."""
        spec = self.definition.by_id[node_id]
        self.set_status(NodeStatus.VALIDATED, node_id)
        record = {
            "id": spec.id,
            "label": spec.label,
            "system": self.definition.system_of(spec.id),
            "source": spec.parent,
            "fields": [
                {"name": f.name, "concept": f.concept, "completeness": f.completeness}
                for f in spec.fields
            ],
        }
        self.state.environment["dataSources"].append(record)
        self._new_sources.append(record)

    def _link(self, edge: EdgeSpec) -> None:
        if any(existing["id"] == edge.id for existing in self._edges):
            return
        record = {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "kind": edge.kind,
            "detail": edge.detail,
        }
        self._edges.append(record)
        self._new_edges.append(record)

    def _resolve_links(self) -> None:
        for link in self.definition.links:
            if self.has(link.source) and self.has(link.target):
                self._link(link)

    # -- Recording ---------------------------------------------------

    def record(
        self,
        *,
        type: str,
        category: Category,
        message: str,
        severity: Severity = Severity.INFO,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        """Record an event carrying every change since the last one.

        The summary is recomputed and carried every time, so the counts on
        screen are always the counts of the graph as it stands (FR-D9).
        """
        summary = summarise(self.state.environment)
        self.state.environment["summary"] = summary
        delta = {
            # Constant, and carried anyway: a client whose snapshot predates
            # discovery has no environment to fold into until it has these.
            "client": self.state.environment["client"],
            "canvas": self.state.environment["canvas"],
            "nodes": [dict(self.node(node_id) or {}) for node_id in self._touched],
            "edges": list(self._new_edges),
            "dataSources": list(self._new_sources),
            "summary": summary,
        }
        self._touched.clear()
        self._new_edges.clear()
        self._new_sources.clear()
        return self.state.record(
            type=type,
            category=category,
            message=message,
            severity=severity,
            payload={**(payload or {}), "environment": delta},
        )

    def complete(self) -> None:
        """Mark the summary final, so the surface can report completion."""
        self.state.environment["complete"] = True


def summarise(environment: dict[str, Any]) -> dict[str, Any]:
    """The discovery counts and per-system status, from the graph alone.

    - A *system* counts once it has been reached, whether by discovery or
      by an administrator; a declared system not yet reached does not.
    - A *data source* is anything that provides a dataset, which is the
      reading §19 implies when it counts data sources separately from the
      datasets inside them.
    - A *dataset* counts once detected. Profiled ones are those validated
      for use; excluded ones were refused by policy and are counted so
      that the refusal stays visible in the totals.

    Methodology evidence is located, not graded: a methodology *appears
    feasible* when every concept it requires is carried by a profiled
    dataset (FR-D10). How well the evidence supports it is assessment's
    question (FR-A2, FR-A3), and it is not anticipated here.
    """
    nodes = environment.get("nodes", [])
    edges = environment.get("edges", [])

    systems = [n for n in nodes if n["kind"] == NodeKind.SYSTEM]
    reached = [n for n in systems if n["status"] != NodeStatus.UNKNOWN]
    datasets = [n for n in nodes if n["kind"] == NodeKind.DATASET]
    providers = {e["source"] for e in edges if e["kind"] == EdgeKind.PROVIDES}

    located: set[str] = set()
    for source in environment.get("dataSources", []):
        located.update(f["concept"] for f in source["fields"])

    return {
        "complete": bool(environment.get("complete")),
        "systems": len(reached),
        "declaredSystems": len(systems),
        "dataSources": len(providers),
        "datasets": len(datasets),
        "profiled": sum(1 for n in datasets if n["status"] == NodeStatus.VALIDATED),
        "excluded": sum(1 for n in datasets if n["excludedBy"]),
        "bySystem": [
            {
                "id": n["id"],
                "label": n["label"],
                "status": n["status"],
                "origin": n["origin"],
            }
            for n in systems
        ],
        "methodologies": [
            {
                "id": methodology.id,
                "name": methodology.name,
                "required": len(methodology.requires),
                "located": sum(1 for r in methodology.requires if r.concept in located),
                "missing": [r.concept for r in methodology.requires if r.concept not in located],
                "appearsFeasible": all(r.concept in located for r in methodology.requires),
            }
            for methodology in METHODOLOGIES
        ],
    }
