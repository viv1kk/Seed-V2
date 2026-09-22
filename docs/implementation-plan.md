# Systems --- V1 Implementation Plan

> **Status:** Proposal, for review. Derived from `requirements.md`; every
> milestone below names the requirements it discharges.
>
> Nothing here is built yet. **Every decision in section 5 is now ruled,
> and both requirement conflicts are resolved** --- see `decisions.md`,
> which is authoritative where it differs from an earlier draft of this
> document. Section 5 below summarises those rulings; section 6 carries
> the risk register forward.

---

## 1. Shape of the build

Four phases. Each ends at a state worth showing someone.

```
PHASE 1   Foundation          M0 - M2    nothing to see, everything depends on it
PHASE 2   Narrative           M3 - M8    the whole story runs; dashboards are stubs
PHASE 3   Analytics           M9 - M11   the story ends somewhere real
PHASE 4   Craft               M12 - M13  the part that actually sells it
```

The ordering is deliberately inverted from the temptation to start with
the dashboard. Phase 2 produces a complete, demonstrable narrative before
a single chart exists — which means if the schedule slips, it slips into
a system that still runs end to end.

---

## 2. Architecture summary

Condensed; the reasoning behind each choice is in `requirements.md`.

### Domain model

```
SystemState
├── lifecycle     { phase, state, blockedOn, since }
├── seed          { layers: { core, adaptation, protection } }
├── environment   { nodes, edges, dataSources }
├── knowledge     { methodologies }
├── assessments   [ { feasibility, coverage, checks, limitations } ]
├── solutions     [ { status, components, dashboardId } ]
├── protection    { rules, decisions }
├── humanRequests [ { kind, fields?, options?, status } ]
├── runs
└── events        [ { seq, ts, type, phase, category, severity, message } ]
```

Events carry two layers on purpose: `type` is contract and drives state
reducers, `category` + `message` are presentation and drive the activity
stream. Neither can break the other (FR-E3, FR-E4).

### Lifecycle

One declared transition table, validated on every attempt; illegal
transitions raise (FR-L1, FR-L3). Blocking on human input is a
`blockedOn` flag beside the current state rather than a
`WAITING_FOR_HUMAN` state per phase (FR-L4) — this avoids a
combinatorial state table.

### Simulation engine

Workflows are Python generators yielding **beats**. Generators give
pause/resume natively, which is exactly what FR-H7 needs.

```python
def discovery_workflow(ctx):
    yield ctx.beat(1000, evt.discovery_started())
    yield ctx.beat( 800, evt.resource_discovered("ServiceNow"))
    yield ctx.beat(1400, evt.error("Endpoint timed out"))       # FR-D8
    yield ctx.beat( 600, evt.warning("Retrying (1/3)"))
    yield ctx.beat( 900, evt.success("Endpoint reachable"))

    creds = yield ctx.await_human(requests.servicenow_credentials())
    ...
```

One asyncio task pulls beats, applies mutations, publishes events, sleeps
`delay × speed`. On `await_human` it parks the generator and resumes via
`generator.send()`. Operator controls fall out of this almost for free:

| Control | Implementation                     | Requirement |
| ------- | ---------------------------------- | ----------- |
| Speed   | multiply every beat delay          | FR-O1, FR-O3 |
| Skip    | drain remaining beats with delay 0 | FR-O1       |
| Reset   | cancel task, rebuild `SystemState` | FR-O4       |

### The replaceability seam

The API layer never imports the simulation engine. It depends on:

```python
class EventSource(Protocol):
    def subscribe(self, from_seq: int) -> AsyncIterator[Event]: ...
    async def start(self, phase: Phase) -> None: ...
    async def resolve_human(self, request_id: str, response: dict) -> None: ...
```

`SimulationEngine` implements it now; a real agent runtime implements it
later (NFR-A1, NFR-A2). This is the one boundary worth defending even at
cost elsewhere.

### Analytics

A single **filter context** drives every chart on a dashboard:

```ts
FilterContext = {
  timeRange?: [string, string]
  dimensions: Record<string, string[]>
  entityId?: string
}
```

Every chart click emits a delta; the breadcrumb is the ordered list of
deltas; back pops one. Cross-filtering is then automatic and no
interaction path needs anticipating (FR-EV1, FR-EV2).

```
POST /api/analytics/{solutionId}/query
{ "filter": FilterContext, "views": ["kpis","volumeOverTime","byCategory"] }
```

Dashboards are **data, served from the backend** (D-1). Chart
specifications carry mark type, data binding, semantic colour role,
visual weight and layout; one generic renderer draws them. Drill-down
hierarchies are data on the same principle (FR-EV3):

```json
{ "levels": [
    { "id": "all",             "label": "All Tickets" },
    { "id": "month",           "dimension": "month" },
    { "id": "anomalyType",     "dimension": "anomalyType" },
    { "id": "assignmentGroup", "dimension": "assignmentGroup" },
    { "id": "cluster",         "dimension": "clusterId" },
    { "id": "ticket",          "entity": "ticket" } ] }
```

### Repository structure

```
seed-v2/
├── run.py                        single-command launcher (NFR-L1)
├── seeds/                        core.md, adaptation.md, protection.md
├── backend/app/
│   ├── api/                      lifecycle, seed, events, human,
│   │                             solutions, analytics, operator
│   ├── domain/                   models, lifecycle, events, state
│   ├── simulation/
│   │   ├── protocol.py           EventSource — the NFR-A1 seam
│   │   ├── engine.py             beat runner, speed, skip
│   │   └── workflows/            discovery, assessment, implementation
│   ├── knowledge/                seed_loader, methodologies
│   ├── environment/acme.py       five systems and their graph
│   ├── protection/               rules, engine
│   └── analytics/
│       ├── generator/            tickets, licenses, applications
│       ├── store.py              in-memory frames + indices
│       ├── descriptors/          chart specs + hierarchies (D-1)
│       └── query.py              filter context → aggregates
└── frontend/src/
    ├── stores/                   system, events, operator, dashboard
    ├── design/tokens.css         light + dark, single source (NFR-V2)
    ├── components/               lifecycle, environment, activity,
    │                             protection, human, build, charts
    └── views/
        ├── SeedView.vue
        ├── WorkspaceView.vue     stays mounted (NFR-A3)
        └── DashboardView.vue     the one generic renderer (D-1)
```

---

## 3. Milestones

### Phase 1 — Foundation

---

**M0 · Walking skeleton**

Repo scaffold, `run.py` launcher on `uv` (D-10), FastAPI app, Vite +
Vue 3 + TS + Pinia, design-token file with both themes stubbed, one
trivial event travelling backend → SSE → browser. `run.py` completes its
imports before signalling readiness (A-1).

*Discharges:* NFR-L1, NFR-L2, NFR-L4
*Exit:* one command starts both services; the browser renders a live
event; the theme toggle flips tokens.

---

**M1 · State and event backbone**

Domain models, lifecycle machine and transition table, `SystemState`,
event schema and factory, event log, SSE endpoint with `Last-Event-ID`
replay, `GET /api/state` snapshot, frontend event store implementing
snapshot-then-stream with sequence-gap detection.

*Discharges:* FR-L1–L5, FR-L7, FR-E1–E7
*Exit:* a throwaway workflow drives real state transitions; killing and
restoring the SSE connection replays exactly; an illegal transition
raises rather than mutating.

---

**M2 · Simulation engine**

Beat runner, generator-based workflows, `await_human` park/resume,
speed/skip/reset, `EventSource` protocol and its simulation
implementation. Beats carry **relative weights** scaled to a configured
total duration (D-8), set to 270 s for the 4--5 minute target (OQ-7).

*Discharges:* FR-O1, FR-O3, FR-O4, FR-H7, NFR-A1
*Exit:* a two-step workflow pauses for input, resumes on submission, and
survives being sped up, skipped and reset.

> **Phase 1 exit:** nothing worth showing, but every subsequent milestone
> is now additive rather than structural.

---

### Phase 2 — Narrative

---

**M3 · Seed and INIT**

Author the three seed files — real methodology, mapping and policy
content, since they are a deliverable in their own right (FR-S1). Seed
loader with Markdown heading parsing, INIT screen with the plant gesture,
plant → initialize transition, hidden sample-seed shortcut.

*Discharges:* FR-S1–S7
*Exit:* dragging in three files produces a genuine per-layer heading
summary and advances the lifecycle.
*Note:* the writing of the seed content is real work and easy to
underestimate.

---

**M4 · Workspace shell**

Persistent `WorkspaceView`, lifecycle strip, activity stream, human-input
surface, protection panel shell, overall layout.

*Discharges:* FR-L6, FR-E8, FR-E9, FR-H1–H4, NFR-A3
*Exit:* the workspace renders live events from M2's throwaway workflow
and never unmounts across phase changes.

---

**M5 · Protection layer**

Rule set authored in Python and mirrored into `protection.md`, evaluation
engine, policy events inline in the activity stream, protection panel
with live counts and a filterable audit log.

*Discharges:* FR-P1–P7
*Exit:* a requested action returns a real `ALLOW`/`DENY`/`ESCALATE`
decision citing a rule id, and it appears in both the stream and the
panel.
*Note:* sequenced before Discovery because every discovery action passes
through this gate (FR-P2).

---

**M6 · Discovery**

ACME environment definition — five systems expanded to roughly thirty
nodes — discovery workflow including the credential pause and the
timeout/retry, SVG environment graph with progressive node appearance and
status transitions, computed completion counts.

*Discharges:* FR-D1–D10, FR-H5, FR-H6
*Exit:* discovery runs start to finish, pauses once for credentials,
recovers from one timeout, and reports counts derived from the graph
rather than authored.
*Pacing (OQ-7):* discovery takes roughly half the 270 s budget. Nodes
appear in **grouped bursts per system**, not individually --- thirty
individual appearances do not fit a readable pace. The credential pause
and the timeout recovery carry fixed weights that do not scale down,
since both are meaning-bearing beats (FR-D7, FR-D8).

---

**M7 · Assessment and approval**

Methodology definitions with declared evidence requirements, feasibility
computed by matching requirements against data-source field
completeness, solution cards, review drawer, approve/reject with recorded
outcomes.

*Discharges:* FR-A1–A10, FR-AP1–AP4
*Exit:* editing a data source's field completeness visibly changes a
feasibility grade — the proof that FR-A2 is computed rather than
authored.

---

**M8 · Implementation and run**

Build workflow, SVG pipeline with node state progression, expandable
test-results detail, ready-to-run listing, run action.

*Discharges:* FR-I1–I6, FR-L8
*Exit:* an approved solution builds, tests, becomes Ready, and Run
transitions to a (still stubbed) dashboard.

> **Phase 2 exit — the significant one.** The entire §68 narrative runs
> end to end. Everything from here is about what the viewer finds when
> they arrive.

---

### Phase 3 — Analytics

---

**M9 · Analytics core** *(load-bearing)*

Three generators with fixed seeds and planted anomaly clusters, in-memory
store, query engine translating filter context to aggregates, hierarchy
descriptors, evidence endpoint, records endpoint --- **and the chart
specification schema that D-1 makes load-bearing**, covering mark type,
data binding, semantic colour role, visual weight and layout.
OQ-1 moves here from M10: under D-1 the chart inventory defines the
schema, so it must be settled before the schema is built.

*Discharges:* FR-AN1–AN5, FR-EV1–EV4, FR-EV6–EV8, NFR-D4, NFR-D5,
NFR-P1, NFR-P2
*Exit:* an arbitrary filter combination returns correct aggregates in
under 200 ms, and an evidence query returns figures computed from real
rows.
*Note:* under D-1 this is the schedule's single point of failure, not
merely its pivot. If the schema is right, M10 and M11 are both
configuration. If it is not expressive enough, no amount of M12 effort
recovers the craft --- see R-6. Design it against §54's seven Ticket
Anomaly charts, the hardest case, before writing the renderer.
*Measured:* generation costs 0.108 s and a two-key groupby 6 ms, so
NFR-P1 and NFR-P2 have ample headroom (R-3 closed, OQ-5 answered no).

---

**M10 · Ticket Anomaly dashboard**

The **generic descriptor-driven renderer** (D-1): ECharts wrappers
resolving semantic colour roles against design tokens (D-5), KPI row,
chart set, cross-filter wiring, URL-synced filter context (D-3),
drill-down and breadcrumb, evidence panel, underlying-record table. The
Ticket Anomaly dashboard is a descriptor, not a component.

*Discharges:* FR-AN6, FR-AN8, FR-AN9, FR-EV5
*Exit:* a viewer can click freely from a headline number to an individual
ticket and find every intermediate figure consistent --- and the dashboard
that achieves this contains no methodology-specific UI code.

---

**M11 · Remaining dashboards**

License Optimization and Application Portfolio Rationalization, each a
generator plus a hierarchy descriptor plus a dashboard descriptor.

*Discharges:* FR-AN7, and demonstrates FR-EV4
*Exit:* both dashboards work with **no new UI code and no new backend
query code**. Any UI code written here is evidence that M9's schema was
under-specified.
*Contingency:* under D-1 the degradation path is a thinner descriptor,
not a different build. Cheaper than the earlier hand-built plan assumed.

---

### Phase 4 — Craft

---

**M12 · Design pass**

Final tokens, both themes, typography, motion, chart palettes with
contrast validation in both themes.

*Discharges:* NFR-V1–V6
*Exit:* both themes pass contrast checks and the interface reads as
analytical infrastructure rather than an AI console.
*Note:* this is a deliverable, not optional polish. See R-6.

---

**M13 · Rehearsal and hardening**

Operator control concealment, beat-timing calibration against the 270 s
target (D-8, OQ-7), an automated determinism test comparing modulo
timestamps and durations (A-2), full narrative runs.

*Discharges:* FR-O2, NFR-D1–D4, NFR-P3–P5, and the §7 acceptance
criterion
*Exit:* two consecutive runs from Reset produce identical output under
A-2's definition, and the full narrative runs cleanly without touching a
terminal. Confirm OQ-4 here: measure whether the stream needs
virtualisation rather than assuming it does not.

---

## 4. Critical path

```
M0 → M1 → M2 ──┬─→ M3 ─→ M4 ─→ M5 ─→ M6 ─→ M7 ─→ M8 ──→ M13
               └─────────────────────→ M9 ─→ M10 → M11 ─→ M12
```

M9 has no dependency on M3–M8 beyond the solution id. **It can be built
in parallel with Phase 2, and should be started early if anything looks
tight** — under D-1 it carries the chart specification schema as well as
the query engine, so everything visible in Phase 3 rests on it. M10
precedes M11 deliberately: M10 proves the schema against the demanding
case, M11 then confirms the generality claim.

---

## 5. Decisions --- ruled

Full reasoning, measurements and consequences are in `decisions.md`. The
rulings themselves:

| ID   | Ruling | Note |
| ---- | ------ | ---- |
| **D-1** | **Fully descriptor-driven dashboards.** The backend serves chart specifications; one generic renderer draws all three dashboards, including Ticket Anomaly. | Conforms to FR-EV4 literally, so **R-1 needs no amendment**. Moves significant work into M9 and raises R-2 and R-6. |
| **D-2** | **pandas.** | Measured: the largest dataset builds in 0.108 s and a two-key groupby costs 6 ms. Performance is not a differentiator here, so familiarity decides. |
| **D-3** | **URL-synced filter context**, Pinia as the in-memory mirror. | Back works on drill state, and rehearsal can jump straight to a view --- which the tight OQ-7 target makes necessary. |
| **D-4** | **Hand-authored graph coordinates.** | Deterministic; reads as designed at ~30 nodes. Lives beside `acme.py`. |
| **D-5** | **Derive the ECharts theme from CSS custom properties at runtime.** | Chart specs carry semantic colour roles, never hex. Contains R-4. |
| **D-6** | **Parity test** between `protection.md` and the Python rule set. | Folded into D-7's suite. |
| **D-7** | **Determinism, state machine, query engine**, plus the D-6 parity test. | Covers what a live demo can fail on, without spending M12's time. |
| **D-8** | **Total-duration budget**, beats carry relative weights. | Mandatory rather than convenient under a 4--5 minute target. |
| **D-9** | **Unbounded event log** within a run. | FR-E7 needs exact replay; OQ-7's duration bounds the volume anyway. |
| **D-10** | **uv.** | Already installed on the target machine (0.12.8), which removes its only cost. |

Two requirement amendments follow from these and are applied in
`requirements.md`:

- **A-1** --- NFR-P1 is measured on a warm interpreter. A cold
  `import pandas` alone costs 2.10 s, which no design decision removes.
- **A-2** --- NFR-D4 defines determinism modulo timestamps and durations.
  **This resolves R-7.**

---

## 6. Risks after the rulings

Status per risk; full reasoning in `decisions.md` §6.

### Resolved

**R-1 · FR-EV4 versus hand-built dashboards.** Resolved by D-1, which
conforms to the requirement instead of narrowing it. All three dashboards
are descriptor-driven, so a fourth methodology genuinely needs no new UI
code.

**R-7 · NFR-D4 unsatisfiable as written.** Resolved by amendment A-2:
determinism is defined modulo timestamps and durations. The M13 test
compares with those fields excluded.

**R-3 · NFR-P1 may not survive three generators.** Closed by
measurement. The largest dataset builds in 0.108 s against a 2 s budget.
The real startup cost is library import, addressed by A-1.

**R-10 · Beat timing uncalibrated.** Closed by OQ-7's answer of 4--5
minutes and D-8's budget model.

### Live

**R-2 · The dashboards dominate the schedule.** — *High / High, raised.*
D-1 moves the dashboard machinery into M9 and makes it the schedule's
single point of failure rather than merely its pivot. Mitigated by
settling OQ-1 first and designing the schema against the hardest chart
set. Trigger for concern: M9 slipping, or M10 requiring UI code that is
specific to Ticket Anomaly.

**R-6 · The differentiation is craft, not architecture.** — *Medium /
Very high, raised.* Under D-1 the craft must be expressible as data.
Emphasis, span, ordering, annotation and empty states have to be
descriptor fields, or the renderer produces a generic dashboard that no
M12 effort recovers. This is now an M9 schema-design concern as much as
an M12 one.

**R-4 · Dual theme doubles chart styling work.** — *Medium / Medium,
reduced.* D-5 makes contrast validation a per-token concern rather than a
per-chart one. Residual risk remains a design problem: a palette that
reads well dark can look washed out light.

**R-5 · Event-sourced state can drift from snapshots.** — *Low / High,
unchanged.* Largely designed out by snapshot-then-stream and the
sequence-gap check. D-7's state-machine suite should cover reducer parity
against the snapshot.

**R-8 · The credential form has nothing to validate.** Unchanged.
Validate shape --- non-empty, plausible URL --- and show a brief simulated
handshake, so obvious junk is rejected even though acceptance is
unconditional.

**R-9 · FR-S5 and FR-S6 sit close together.** Unchanged. A headingless
seed file yields an empty but successful summary. Give it a sensible
empty state.

### New

**R-11 · A 4--5 minute narrative is tight.** — *Medium / Medium.* Four
phases inside 270 s leaves little room per beat. Mitigated by grouped
node bursts at M6, a denser and shorter activity stream, and protected
weights for the credential pause and timeout recovery. Raising the total
during rehearsal is a single number (D-8), so treat 270 s as a target
rather than a constraint.

---

## 7. What is still open

| ID   | Question | Needed by |
| ---- | -------- | --------- |
| OQ-1 | Exact chart inventory per dashboard | **M9** (moved earlier: it defines the D-1 schema) |
| OQ-2 | Drill-down hierarchies for the two smaller solutions | M9 |
| OQ-3 | Accent colour and typeface | M12 |
| OQ-6 | Which actions trigger the required DENY and ESCALATE | M5 |

Closed: OQ-4 (provisionally no virtualisation), OQ-5 (no cache),
OQ-7 (4--5 minutes). See `decisions.md` §4.
