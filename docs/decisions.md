# Systems --- V1 Decision Record

> **Status:** Ruled. This document closes section 5 of
> `implementation-plan.md` and resolves the two requirement conflicts
> recorded there as R-1 and R-7.
>
> Where a ruling amends `requirements.md`, the amendment is stated here
> and applied there. Where a ruling is supported by measurement, the
> measurement is given.
>
> **Addendum, 2026-09-23:** section 7 records the rulings from the
> Seeding and Life rework (the Alex Prigojine session), D-11 to D-17 and
> amendments A-3 to A-9. That rework renumbered the milestones not yet
> built. **Milestone numbers in sections 1 to 6 refer to the plan as it
> stood before the rework:** former M11 is now M20, former M12 is now
> M21, and former M13 is now M22. M0 to M10 are unchanged.

---

## 1. Measurements taken before ruling

Run on the target machine (Windows 11, Python 3.12.10, 184,000 ticket
rows, the demo's largest dataset).

| Measurement                              | Result             |
| ---------------------------------------- | ------------------ |
| Generate 184k rows and build the frame   | 0.108 s, 6.6 MB    |
| Filter plus two-key groupby              | 0.006 s            |
| Multi-index build                        | 0.014 s            |
| Indexed lookup                           | 0.004 s            |
| `import pandas`, warm                    | 0.50 s             |
| `import pandas`, cold                    | 2.10 s             |
| `import polars`, warm                    | 0.25 s             |
| `import polars`, cold                    | 1.53 s             |
| `import numpy`, warm                     | 0.12 s             |

Two conclusions follow, and both change the plan.

**Dataset generation is not a performance risk.** R-3 assumed three
generators might not fit inside NFR-P1's two-second budget. The largest
of the three costs 0.108 s. Three generators plus indices will not
approach one second. R-3 is downgraded from *Medium / Medium* to
*closed*, and OQ-5 is answered: no local cache. Caching a 0.108 s build
behind a file read would cost more than it saves.

**Library import is the real startup cost.** Whatever the dataframe
library, a cold import dominates every other startup cost combined, and
pandas alone exceeds NFR-P1's budget on a cold interpreter. This is a
property of the Python import system, not of the design, and no
architectural choice removes it. See A-1.

---

## 2. Rulings

### D-1 · Dashboards are fully descriptor-driven

**Ruled: option (a).** The backend serves chart specifications. All three
dashboards, including Ticket Anomaly Detection, are rendered by one
generic dashboard renderer that reads those specifications. No dashboard
is a hand-authored Vue component.

FR-EV4 therefore holds literally and needs no amendment: a fourth
methodology requires a generator and a hierarchy descriptor, and no new
UI code. **R-1 is resolved by conforming to the requirement rather than
narrowing it.**

This is the most demanding of the three options and it moves work into
M9. Two consequences must be planned for rather than discovered:

*The descriptor vocabulary must be designed against the hardest case
first.* Ticket Anomaly Detection is the dashboard that has to land
(FR-AN6, R-6). Its chart set from §54 --- volume over time, anomaly
trend, category distribution, anomaly by priority, anomaly by assignment
group, resolution-time distribution, top anomaly patterns --- defines the
vocabulary. That is roughly six mark types: KPI tile, time series,
categorical bar, distribution, ranked list, and one comparison form.
Design the schema so those seven charts are expressible, then confirm the
two smaller dashboards need nothing new.

*Craft must be expressible as data.* Emphasis, span, ordering, annotation
and empty states become descriptor fields rather than component code. A
descriptor that can only say "bar chart here" will produce a generic
dashboard and lose R-6. The schema needs fields for visual weight and
layout, not just data binding.

M10 must precede M11 for this reason: M10 proves the vocabulary against
the demanding case, and M11 then confirms the generality claim.

---

### D-2 · pandas

**Ruled: pandas.** Groupby over categorical dimensions is the entire job
of the query engine, and pandas is the best-understood option for it.
The measurements remove the performance argument that might have favoured
an alternative: at this scale every candidate is far inside budget, so
the decision rests on API familiarity.

polars imports 0.25 s faster warm. That margin does not justify the less
common API when the whole query surface is groupby and filter.

Revisit only if a measured NFR-P1 failure traces to pandas specifically,
which the numbers above make unlikely.

---

### D-3 · The filter context is URL-synced

**Ruled: URL-synced query parameters**, with Pinia as the in-memory
mirror.

Browser back then works on drill state, a drill position is shareable,
and rehearsal can jump directly to a view. The last point carries more
weight under the four-to-five minute target ruled at OQ-7: rehearsing the
dashboard section must not require replaying the narrative to reach it.

The URL carries the serialized `FilterContext`. The breadcrumb remains
the ordered list of filter deltas, and back pops one delta rather than
one history entry, so the two navigation models stay aligned.

---

### D-4 · Hand-authored graph coordinates

**Ruled: hand-authored coordinates** for the roughly thirty environment
nodes.

Deterministic, and a small graph laid out by hand reads as designed where
auto-layout rarely does. Automatic layout also introduces a second source
of run-to-run variation for no benefit at this size.

Coordinates live beside the environment definition in
`backend/app/environment/acme.py`, so the graph and its layout stay in
one file.

---

### D-5 · ECharts themes derive from design tokens at runtime

**Ruled: derive the ECharts theme from computed CSS custom properties.**

One source of truth satisfies NFR-V2 without maintaining a palette twice,
and it composes well with D-1: chart specifications carry **semantic
colour roles** --- series index, positive, negative, anomaly, baseline,
muted --- and never hex values. The renderer resolves a role to a token at
paint time, and re-resolves on theme change.

This also contains R-4. Contrast validation (NFR-V3) then happens once
per token pair rather than once per chart per theme.

---

### D-6 · A parity test keeps protection.md and the rule set in sync

**Ruled: automated parity test.** The Python rule set is authoritative;
the test asserts that every rule id, effect and description in
`protection.md` matches it.

Cheap to write, and drift between a documented policy and an enforced one
is exactly the inconsistency a sceptical viewer looks for. Folded into
the D-7 suite.

---

### D-7 · Three targeted test suites

**Ruled: determinism, state machine, and query engine**, plus the D-6
parity test.

| Suite         | Asserts                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| Determinism   | Two runs from Reset produce identical events under the A-2 definition    |
| State machine | Every legal transition succeeds; every illegal one raises (FR-L1, FR-L3) |
| Query engine  | Aggregates match record-level ground truth across filter combinations    |
| Parity        | `protection.md` matches the Python rule set (FR-P7)                      |

These cover what a live demo can actually fail on. Broader coverage would
spend time that R-6 argues belongs to M12, and the visual pass is the
harder deliverable to recover if it is compressed.

The query-engine suite gains weight under D-1: with dashboards
descriptor-driven, a query bug affects all three dashboards identically
and cannot be papered over in one component.

---

### D-8 · Beat timing is a total-duration budget

**Ruled: total-duration budget**, scaled across beats. Not absolute
per-beat delays.

OQ-7 is now a single tunable number rather than a hundred edits during
rehearsal, which the tight target makes necessary rather than merely
convenient. Each beat declares a relative weight; the runner scales
weights to the configured total; the speed multiplier applies on top
(FR-O1, FR-O3).

---

### D-9 · The event log is unbounded within a run

**Ruled: unbounded.** A single run will not exceed a few thousand events,
and FR-E7 requires exact replay from the retained log, which a ring
buffer cannot guarantee.

The four-to-five minute target ruled at OQ-7 bounds the volume further.
This also makes OQ-4 almost certainly a no: an activity stream covering
that duration will not need virtualisation. Confirm at M13 rather than
building for it.

---

### D-10 · uv

**Ruled: uv.** Already installed on the target machine at version 0.12.8,
which removes the one cost the decision carried. It is faster than pip
and makes `run.py` simpler (NFR-L1).

---

## 3. Requirement amendments

### A-1 · NFR-P1 is measured on a warm start

**Amends NFR-P1.**

> Backend startup, including dataset generation, completes in under 2
> seconds **on a warm interpreter**. First-ever import of Python
> dependencies on a cold machine is excluded from the budget.

A cold `import pandas` alone costs 2.10 s on the target machine. No
design decision removes that, it applies once per machine rather than
once per run, and it does not occur during a demo, which always runs
against a warm interpreter.

`run.py` performs its imports before signalling readiness, so a cold
start is absorbed at launch rather than appearing as a slow first
request.

### A-2 · NFR-D4 defines determinism modulo timing

**Amends NFR-D4.** Resolves R-7.

> Two runs from Reset produce identical event sequences, identical
> analytical results and identical displayed figures, **compared modulo
> timestamps and durations**. Equality means: the same events, in the
> same order, with the same types, categories, severities, payloads and
> analytical figures.

As originally written the requirement could not be satisfied, because
FR-E3 requires every event to carry a wall-clock timestamp and beat
scheduling introduces millisecond jitter regardless. The amendment
preserves everything the requirement was protecting and drops only the
part that no implementation could meet.

The D-7 determinism test compares with timestamp and duration fields
excluded.

---

## 4. Open questions closed

| ID   | Question                                      | Answer                                                                                          |
| ---- | --------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| OQ-5 | Does dataset generation need a local cache?   | **No.** Generation costs 0.108 s for the largest dataset. A cache would cost more than it saves.  |
| OQ-7 | Target narrative duration at 1x               | **4 to 5 minutes.** Sets the D-8 budget at roughly 270 seconds across all beats.                  |
| OQ-4 | Does the activity stream need virtualisation? | **Provisionally no**, given OQ-7's duration. Confirm by measurement at M13.                       |
| OQ-6 | Which actions trigger the DENY and ESCALATE   | **DENY:** reading ServiceNow's security log as a usage signal (PR-033). **ESCALATE:** deploying the assessed solutions (PR-053). Settled at M5. |
| —    | Lifecycle phase names                         | **`INIT`, `DISCOVERY`, `ASSESSMENT`, `IMPLEMENTATION`, `RUNTIME`**, as built. §27 of the project notes sketches the last as `DEPLOYMENT`; it is `RUNTIME` because V1 deploys nothing real (§30) and the phase is about running solutions (FR-L8). Ruled after M8. |
| OQ-1 | Exact chart inventory per dashboard           | **KPIs on top, then treemaps, bar charts and line charts, then a focused subset table and the full record table below. Colour identifies the anomaly pattern or class, the same colour on every chart.** Inventory per dashboard in "What OQ-1 and OQ-2 mean" below. Ruled before M9. |
| OQ-2 | Drill-down hierarchies for the two smaller solutions | **License Optimization:** products, vendor, product, utilisation class, assignment. **Application Portfolio Rationalization:** portfolio, business unit, disposition, application, usage records. Both end at records with evidence (FR-EV6). Ruled before M9. |

### What OQ-7's answer costs

Four to five minutes is tight for a narrative containing discovery,
assessment, approval and implementation. Three consequences follow.

*Discovery cannot carry thirty node appearances at a readable pace.*
Nodes must appear in grouped bursts per system rather than individually,
which is also the more legible reading of FR-D3. Budget roughly half the
total to discovery, since that is where perceived activity lives.

*The activity stream must be denser and shorter.* Fewer, more
substantial events. FR-E9 already forbids narrating internal reasoning,
which helps. Events that exist only to fill time should not be written.

*The credential pause and the timeout recovery need protected time.*
Both are scripted beats that carry meaning (FR-D7, FR-D8), and both
become invisible if compressed proportionally with everything else. Give
them fixed weights that do not scale down.

These are M6 concerns. Raising the total at rehearsal is one number
(D-8), so treat 270 seconds as the target rather than a constraint.

---

## 5. Open questions still carried

| ID   | Question                                            | Needed by |
| ---- | --------------------------------------------------- | --------- |
| OQ-3 | Accent colour and typeface                           | M12       |

OQ-1 and OQ-2 were closed before M9; see §4 and below. OQ-8 to OQ-13 were
raised by the Seeding and Life rework; see §7.4.

### What OQ-1 and OQ-2 mean

The direction given was: headline numbers up top; treemaps, bar charts
and line charts; a table of all the raw data below, with smaller tables
on a subset of columns where they help; genuinely analytical, so a viewer
can drill from many anomaly clusters into one; and colour coding that
identifies the clusters across every chart.

*One layout, three dashboards.* Every dashboard is the same four bands,
declared in its descriptor (D-1): a KPI row; a chart grid whose first
chart spans the width; a focused table on a subset of columns; and the
full record table for the current filter context, paginated and sortable,
at the bottom. The evidence panel opens beside them when a cluster or a
record is selected (FR-EV7). Every band follows the one filter context
(FR-EV1), so the record table is always the rows behind the figures above
it.

*The mark vocabulary is deliberately small:* `kpi`, `line`, `bar`
(vertical or horizontal, optionally stacked), `treemap` and `table`. M9's
schema must express exactly these well, rather than many kinds thinly.
This is the answer to R-6: craft goes into the few marks the dashboards
actually use.

*Colour identifies, it does not decorate.* A categorical dimension that
carries meaning, such as anomaly pattern, utilisation class or
disposition, is bound to fixed colour slots in the descriptor, so a value
has the same colour on the treemap, in the stacked bars, on the line, in
the table's colour chip and in the evidence panel. Normal, non-anomalous
records are always the neutral colour, so anomalies stand out without a
legend. Once a view is filtered to one pattern, its clusters are coloured
from a cluster palette in the same way, so the clusters of one pattern can
be told apart on every chart. The slots resolve to design tokens (D-5),
never hex; M9 adds the categorical tokens for both themes and M12 tunes
them.

**Ticket Anomaly Detection (deep, M10).** Five planted anomaly patterns,
each with its own colour: *reassignment loop*, *resolution stall*,
*reopen churn*, *priority mismatch* and *volume burst*. Several clusters
are planted within each pattern, around thirty in all, so there are always
multiple clusters to drill into.

- KPIs: total tickets, anomalous tickets, anomaly rate, median resolution
  time, clusters detected.
- Line: ticket volume and anomalous tickets over time. Click or brush for
  a time range.
- Treemap: anomalies by pattern, then assignment group, then cluster, sized
  by ticket count and coloured by pattern. The main route from many
  clusters to one.
- Bar, horizontal and stacked by pattern: anomalies by assignment group.
- Bar, stacked by pattern: anomalies by priority.
- Line, one line per pattern: anomaly trend.
- Bar: resolution time distribution, anomalous against baseline.
- Focused table: clusters, with pattern chip, group, tickets, observed,
  baseline, deviation and excess hours. A row opens the cluster and its
  evidence.
- Record table: every ticket in the filter context, with number, opened,
  priority, category, group, reassignments, resolution hours, pattern chip,
  cluster and score. A row opens the ticket's evidence.
- Hierarchy (§55): all tickets, month, pattern, assignment group, cluster,
  ticket, evidence.

**License Optimization (M11).** Colour is the utilisation class: active,
underused, unused, and leaver (an access finding).

- KPIs: licences entitled, assigned, active, unused or underused, and
  recoverable cost. Cost is stated for priced products only, with the
  unpriced share named. This is section 20's insufficiency reaching the
  dashboard: the 64% unit-price completeness withholds cost where there is
  no price, never estimating it (PR-074).
- Treemap: vendor, then product, sized by entitlement and coloured by
  utilisation class.
- Bar, horizontal: entitlement against assignment against active use per
  product. The gap is the finding.
- Line: active users over time per product, against the entitlement.
- Bar: recoverable cost by product. Unpriced products are shown as
  withheld, not as zero.
- Focused table: optimisation candidates per product.
- Record table: assignments, with user, product, assigned, last activity,
  days inactive, class and leaver flag.
- Hierarchy: all products, vendor, product, utilisation class, assignment,
  evidence.

**Application Portfolio Rationalization (M11).** Colour is the
disposition: retain, consolidate, replace, retire, and unresolved.
Unresolved covers applications with no usage instrumentation, which are
never reported as unused.

- KPIs: applications, retire candidates, consolidation candidates, annual
  cost, unresolved.
- Treemap: business capability, then application, sized by cost and
  coloured by disposition.
- Bar, stacked by disposition: applications per business unit.
- Line: monthly distinct users by disposition.
- Bar, horizontal: cost per active user for the costliest applications.
- Focused table: retire and consolidate candidates, with owner, users,
  cost and dependencies.
- Record table: the application inventory.
- Hierarchy (§33): portfolio, business unit, disposition, application,
  usage records, evidence.

The two smaller dashboards have four charts each, within FR-AN7's
"roughly 3--4", and both tables, because the record table is part of the
common layout rather than an extra.

### What OQ-6's answer means

Both decisions are chosen so the boundary is visible without adding an
interruption to §83.6's narrative.

*The DENY carries a plausible motive.* Discovery considers sign-in events
as a usage signal, which is a reasonable analytical instinct, and asks to
read only the application identifier and timestamp. PR-033 refuses it
regardless, because the rule is about the table rather than the columns.
A boundary that holds only against obviously bad requests demonstrates
nothing; one that holds against a well-motivated, minimised request is
the point of §10. The PR-031 escalation path also matches and is recorded
as overruled, so the audit log shows a permission that existed and lost.

*The ESCALATE is the reason for the approval.* At the end of assessment
the system asks to deploy, PR-053 escalates, and the lifecycle moves to
AWAITING_APPROVAL as a consequence. The approval step of §26 is therefore
not a scripted pause but the answer to a policy decision, and it costs
the narrative no additional stop.

---

OQ-1 moves earlier, from M10 to M9. Under D-1 the chart inventory defines
the descriptor schema, so it must be settled before the schema is built
rather than while the dashboard is assembled.

---

## 6. Risk register after these rulings

| ID   | Status after ruling                                                                                             |
| ---- | ----------------------------------------------------------------------------------------------------------------- |
| R-1  | **Resolved.** D-1 conforms to FR-EV4 rather than amending it.                                                     |
| R-2  | **Raised to High / High.** D-1 moves dashboard work into M9 and makes it the schedule's single point of failure.  |
| R-3  | **Closed.** Measured at 0.108 s against a 2 s budget.                                                             |
| R-4  | **Reduced.** D-5 makes contrast validation a per-token concern rather than a per-chart one.                       |
| R-5  | Unchanged. D-7's state-machine suite should cover reducer parity against the snapshot.                            |
| R-6  | **Raised.** Under D-1, craft must be achieved through the descriptor vocabulary. If the schema is not expressive enough, no amount of M12 effort recovers it. This is the argument for designing the schema against §54's chart set. |
| R-7  | **Resolved** by A-2.                                                                                              |
| R-8  | Unchanged. Validate credential shape and show a simulated handshake.                                              |
| R-9  | Unchanged. Provide a sensible empty state for a headingless seed file.                                            |
| R-10 | **Closed** by OQ-7.                                                                                               |

The two risks that rose, R-2 and R-6, both follow from D-1 and both
concentrate on M9. The mitigation is the same for each: settle OQ-1,
then design the descriptor schema against the Ticket Anomaly chart set
before writing the renderer.

---

## 7. Stakeholder rework: Seeding and Life (2026-09-23)

Feedback from a session with Alex Prigojine, received after M10. Its
stated scope: a relabelling and pane reorganisation on top of what is
built, removing no functionality. The feedback is summarised in
`project-notes.md` §84, which also records the three Life pane options
from which D-17 was chosen.

Two items in the feedback are not relabelling. Replacing "Feasibility"
with "Potential" adds a new flag state, and the clean-up flow adds a
lifecycle state. Both are ruled below as new logic and are scheduled
after the pure renames, not inside them.

All rulings below were checked against the code as built through M10.
File references are to that code.

### 7.1 Rulings

---

### D-11 · Renames are display-only; identifiers keep their names

**Ruled: every rename changes what the viewer reads, and nothing the
code, the API or the tests name.**

| Code and contract (unchanged)               | Displayed as        | Replaces on screen      |
| ------------------------------------------- | ------------------- | ----------------------- |
| the set of built solutions, as a whole      | **Agent One VW** (ValueWise™) | nothing: new    |
| `Solution`, `solutionId`, `/api/solutions`  | **Agent Component** | Solution                |
| product name                                | **Seed**            | Systems                 |
| `Phase.RUNTIME`                             | **Life**            | Runtime                 |
| `Phase.INIT`                                | **Planting**        | Init                    |
| `feasibility`, `Grade`                      | **Potential**       | Feasibility             |

This is the principle the lifecycle phase-name ruling already applied
(§4): `RUNTIME` stays the identifier because it is load-bearing, and
that ruling stands. What changes is its label, from "Runtime" to "Life".

*Why display-only.* The viewer sees copy and never sees an identifier.
Renaming identifiers would touch the SSE contract, every test that
asserts on an event type such as `solution.approved`, and the
`EventSource` seam NFR-A2 protects, all for no visible gain. It would
also turn a low-risk pass into a high-risk one, which the feedback's own
constraint forbids.

*The cost is two vocabularies.* The code says `solution`; the screen
says "Agent Component". This table is the glossary between them. New
code keeps the code vocabulary, and new display copy uses the display
vocabulary.

Four sub-rulings resolve ambiguities in the feedback:

- **Agent One VW names what grows out of the Seed** (OQ-8, answered).
  Agent One VW (ValueWise™) is the framework through which the
  methodology of building and maintaining the analytical pipeline is
  implemented. The Seed is planted; Agent One VW is what it grows into.
  Each Agent Component is one part of it, one per approved methodology.
  So the two names are not synonyms. They sit at two levels:
  *Agent One VW* titles the whole, and *Agent Component* labels each
  part. On screen, Agent One VW names the Life pane (FR-N6), the
  Implementation stage's heading ("Building Agent One VW"), and the
  closing step's hand-over (D-16). "ValueWise™" appears with the name
  where it heads the Life pane and is omitted elsewhere, to keep the
  copy short.
- **Methodologies keep their name** (OQ-9, answered: rename only if a
  seed-themed name is coherent). A plant-themed name was assessed and
  rejected. The strongest candidate was *trait*: a seed carries traits,
  and the environment decides which ones express, which mirrors Core,
  Adaptation and Potential closely. It was rejected for three reasons.
  First, §69 and §71 make "the system has a methodology" the demo's
  central claim, and the word carrying that claim should stay on
  screen. Second, "License Optimization trait" needs explaining to an
  enterprise viewer, and NFR-V6 rules out the cute. Third, the analogy
  already holds without it: the seed's Core layer *contains* the
  methodologies (§3), just as a seed carries its genetic content.
  *Strain*, *cultivar* and *branch* failed the same tests. This gives a
  rule for any later naming: **the analogy names the lifecycle** (Seed,
  Planting, Seeding, growth, Life), **and the analysis keeps its own
  names** (methodology, evidence, finding, baseline).
- **Only the product-name "Systems" changes.** The "Systems" heading in
  the discovery summary (`EnvironmentStage.vue:74`) counts the client's
  systems. It is a different word that happens to share the spelling, and
  it is not renamed.
- **"Initiation" is the `INIT` phase**, labelled "Init" today
  (`LifecycleStrip.vue:13`). No stage called Initiation exists. The
  heading "Seed" over the registered layers in the INIT stage becomes
  "Planting", and the layers themselves remain "the Seed".

The working documents keep "Systems" in their titles as the project's
working name. Only the product as displayed is renamed.

---

### D-12 · What Potential means

**Ruled: Potential keeps the four computed grades, rewrites what each
one says, and adds a routing-problem flag alongside the grade rather than
as a fifth grade.**

The grade is still computed from evidence exactly as FR-A2 and FR-A3
require. The rule in `feasibility.py` is unchanged. What changes is the
question the grade is presented as answering: from "can this be done?"
to "how much value is within reach?".

| Grade   | Potential means                                                                                          | Unchanged computation                          |
| ------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| HIGH    | **Strong value.** The Agent Component can deliver its full findings.                                      | Every requirement sufficient                   |
| MEDIUM  | **Value, with stated limits.** Findings hold, and the limits are named beside them.                       | Some requirements only limited                 |
| PARTIAL | **Needs deeper modelling.** The findings that rest on incomplete evidence are withheld until the data improves or the model is extended. Still approvable (FR-A5). | Some requirements incomplete |
| LOW     | **Not yet modellable.** Evidence the methodology needs is missing outright.                               | Evidence missing, or most of it incomplete     |

The feedback defines only HIGH and PARTIAL. MEDIUM and LOW are kept
because the computation produces them. Their meanings above extend the
feedback's framing, and were confirmed with OQ-10.

*Routing problem.* The flag is raised when evidence a methodology
requires **exists in the environment but cannot reach the analysis**:
it was refused by policy, its source is unreachable, or it is waiting on
input.

It is a flag and not a grade because the two are independent. A
methodology can have HIGH potential and a routing problem at the same
time: the value is there, and the path to it is blocked. A single scale
would lose that information. This is the same argument that made
`blockedOn` a flag rather than a state (FR-L4).

It is also not insufficient evidence. FR-H4 keeps errors, decisions and
insufficient evidence apart. Under this definition a routing problem is
evidence that is present but out of reach. Showing it as a shortfall in
the grade would blur a distinction the requirements insist on.

Like the grade, the flag is **computed from facts System State already
holds**: protection decisions, node statuses and pending requests. It is
never authored. The obvious candidate in the scripted run is PR-033's
refusal of sign-in events as a usage signal (OQ-6). Whether a
methodology's required concept actually depends on that source is
settled at M16. If none does, the flag is computed and tested but never
appears in the narrative. That is a narrative choice to raise with the
stakeholder, not something to fake.

*Interpretation, confirmed at OQ-10.* The feedback names the state
without defining it. Two other readings were offered and not chosen:
results with no destination to be routed to, and tickets being
misrouted as a finding. The second would have been an analytical result
rather than an assessment state, and the planted *reassignment loop*
pattern already reports it (OQ-1).

*The payload key stays `feasibility`* (D-11). Display text, section
titles and the recommendation texts in `RECOMMENDATIONS` change. The
keys do not. M12 audits which references are load-bearing before M13
changes any of them.

---

### D-13 · Planting shows the declared stack, marked unverified

**Ruled: the Planting stage shows the systems the Adaptation layer
declares, labelled as declared and not yet verified.**

The feedback asks for the tech stack the seed is planted into to be
shown at planting. Taken literally, that conflicts with G-2: the
environment is supposed to be unknown until Discovery reveals it, so
listing it up front would give away Discovery's work.

The conflict dissolves on inspection. The Adaptation layer **already
declares** the five systems, and Discovery's first beat reads that
declared inventory and reveals each system as `UNKNOWN` with origin
`DECLARED` (`discovery.py:215-229`, `acme.py:190`). The seed is told what
to expect. Discovery then establishes what is actually there, reachable
and usable.

So Planting shows **what the seed was told**, and Discovery shows **what
the system found out**. Displaying the declaration earlier moves no
knowledge forward. It makes explicit a distinction that was previously
invisible. The labelling matters: every system is shown as declared and
unverified until Discovery reaches it.

This is a small backend change, not a relabel. The declared inventory
must be in System State at `INITIALIZED` rather than at Discovery's first
beat. `acme.py`'s `SYSTEM_ORDER` stays the single source for both, so the
two can never disagree.

---

### D-14 · Two panes: Seeding and Life

**Ruled: the workspace becomes two panes, Seeding and Life, with a
layout control in the top bar. Both panes stay mounted for the whole
run.**

| Pane        | Holds                                                                                                         | Source today                               |
| ----------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Seeding** | Planting, Discovery, Assessment and Implementation stages; the Activity and Protection rail; the human-input surface | `WorkspaceView.vue` and `StagePane.vue`, unchanged in content |
| **Life**    | Agent One VW: the ready Agent Components, their dashboards, and D-17's collection and recalibration                  | `RuntimeStage.vue`, relocated out of `StagePane`; `DashboardView.vue`, relocated from its full-screen overlay in `App.vue` |

*Layout control.* Three settings: Both, Seeding only, Life only. The
lifecycle sets the default, and a manual choice holds until the next
lifecycle-driven change:

```
UNINITIALIZED … IMPLEMENTING               Seeding only
IMPLEMENTATION_COMPLETE, CLOSING_SEEDING   Both
READY_TO_RUN, RUNNING                      Life only
```

*Amended by D-18:* from planting until the build completes the default
is now Life only, where the growth tree stands. The other rows hold.

*Amended again by D-19:* from planting until the build completes the
default is Both, so the stages and the tree are watched together.

*The rail in Both* (after review, 2026-09-24). With both panes showing,
a side rail of at least 22rem left the stages a sliver. In Both the
Activity and Protection rail docks along the bottom of the Seeding pane
as a drawer, and the stages keep the pane's full width above it. The
drawer can be closed to a single bar, which still shows the newest
entry, so the build stays in view. In Seeding only the rail stays beside
the stages. In either placement the human-input surface sits under the
stages and never covers the rail.

Seeding-only is the default during the build because an empty half
screen for four minutes wastes the stage the narrative is played on.
The empty Life pane is still one click away, so a presenter can show
that nothing is alive yet, which is the point the empty pane makes. The
feedback's "empty until build completes" is honoured by the pane's
content. The layout is chosen to use the screen well.

*Mounting.* NFR-A3 already keeps the workspace mounted across phases.
This extends it: changing the layout hides a pane and never unmounts
it. The activity stream keeps its scroll position, and a dashboard keeps
its URL-synced filter context (D-3) while the Seeding pane is shown.

*The seed screen stays full-screen until planting.* The upload screen
(`SeedView.vue`) is the act of planting, and FR-S2 asks for it to be a
deliberate gesture. Putting it inside a half-width pane beside an empty
Life pane would weaken that gesture and show an empty pane before
anything exists. After planting, the Planting **stage**, meaning the
registered layers and the declared stack from D-13, is the first stage
in the Seeding pane. That satisfies the feedback's ordering.

*Two rules keep existing behaviour intact:*

- A pending human request makes the Seeding pane visible. The
  human-input surface lives there, and FR-H1 is pointless if the request
  appears in a hidden pane.
- A rehearsal link (D-3) opens its dashboard inside the Life pane, in
  the Life-only layout. Rehearsal still needs no run to reach a view.

*What moves and what does not.* Nothing is rebuilt. Two components
change their mount point, one screen-selection rule in `App.vue` becomes
a layout rule, and the header gains the control. Every exit criterion
from M3 to M10 must still hold afterwards. That is the proof that the
move removed nothing.

---

### D-15 · The growth tree replaces the lifecycle strip in the Seeding pane

> **Amended by D-18 (2026-09-24).** The tree moved to the Life pane,
> grows vertically from seed to tree, and the strip returned to the
> Seeding pane. The watering rules and the motion budget below stand.

**Ruled: a hand-built SVG tree becomes the Seeding pane's progress
indicator. It grows one segment per completed lifecycle step and takes
one watering step per capability request the protection engine
evaluates.**

*Which progress bar.* The feedback says "replace the progress bar".
Three candidates exist in the code. The seed-load indicator
(`SeedView.vue:142`) and the per-node build bars (`BuildLane.vue:205`)
each belong to a single stage. The **lifecycle strip**
(`LifecycleStrip.vue`) is the only indicator that runs across the whole
seeding phase, so it is the one replaced. Confirmed at OQ-11.

*FR-L6 is kept in intent and superseded in form (A-4).* The strip exists
to show completed, current and future phases. The tree must show the
same information. Phase labels are part of the tree, not decoration
beside it, and that is also what NFR-V5 demands of any animation. The
Life pane needs no phase indicator: Life is a single phase, and the
layout control already names the pane.

*What grows it.* Segments come from lifecycle events: a system
registered, an assessment completed, a component built. Growth is
therefore a function of the event stream (FR-E1), which makes it
deterministic (A-2) and replayable (FR-E7). A tree rebuilt from a
snapshot must be identical to one that grew live.

*What waters it.* In this simulation, "an API call" is **a capability
request that passes through the protection engine**. FR-P2 guarantees
that every such request passes the gate, which makes the gate the one
honest place to count calls. The feedback also names "gen-AI calls".
None occur (NFR-D1), and the tree must not imply any. The watering
source is labelled as tool requests, never as model calls.

A **denied** request waters nothing. The tree therefore shows the
protection boundary as well as the progress. A refused request is
visibly a request that did not feed the system.

*Motion budget.* Watering is a short, low-amplitude step. At instant
speed, steps coalesce so the tree does not strobe. Growth respects
`prefers-reduced-motion`. This rework has the highest risk of the "AI
toy" effect NFR-V4 and NFR-V6 forbid, so the budget is a requirement
(NFR-V7), not a styling preference.

---

### D-16 · Closing the seeding phase is a confirmed, gated lifecycle step

**Ruled: a new lifecycle state `CLOSING_SEEDING` between
`IMPLEMENTATION_COMPLETE` and `READY_TO_RUN`. A person triggers it
through a `confirmation` request. It performs three simulated,
policy-evaluated operations, then hands the screen to Life.**

*A state, not a button handler.* The feedback's action carries three
operations and a change of screen. That is lifecycle, and FR-L1 requires
lifecycle to live in the transition table. The one edge
`IMPLEMENTATION_COMPLETE → READY_TO_RUN` becomes two:
`IMPLEMENTATION_COMPLETE → CLOSING_SEEDING → READY_TO_RUN`.
`CLOSING_SEEDING` belongs to the Implementation phase. It is the last
act of seeding, not the first act of Life.

*A confirmation, not a click.* `RequestKind.CONFIRMATION` is defined in
`domain/state.py` and used by no workflow today. Closing the seeding
phase is exactly the "deployment confirmation" of §18: *built and
validated, confirm run?* This gives FR-H3's fifth request kind its
place. It also puts a person at the boundary between building and
running, which is the kind of meaningful boundary G-4 asks for.

*Three simulated operations.* All three are given in the stakeholder's
words, and none touches a disk, a file or a network (§4.1, NFR-D2):

| Feedback says                      | The system does                                                                                   | Policy                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Merge leftover MD files            | Consolidates the seeding phase's working notes (per-system discovery notes, assessment notes, build records) into one seeding record in System State. **The seed files are never touched** (FR-S6). | New rule: ALLOW. Records are system-owned |
| Clear scratch disk space           | Releases the system's own temporary analytical workspace                                           | New rule: ALLOW. System-owned storage, contrasted with PR-051's DENY on deleting source records |
| Upgrade APIs to final versions     | Promotes each built Agent Component's interface from its build version to its release version      | New rule: ALLOW when that component's deployment was approved under PR-053, otherwise ESCALATE |

The policy column is the reason each operation is a capability request
and not a scripted message. Clearing scratch space is a deletion, and
the rule set has to tell the system's own scratch from the client's
data. Seeing it do that, one decision after PR-051 refuses deletion in a
source system, is a stronger demonstration of §10 than any explanation.
The promotion rule reads a decision already in System State, which shows
that policy can depend on history.

No rule matches these requests today. They would fall to PR-000's
restrictive default. The new rules go into the Python rule set **and**
`protection.md`, and the D-6 parity test enforces that the two agree.

*Pacing.* Closing carries a D-8 weight of roughly 10 to 15 seconds
inside the 270-second budget. R-11 already calls that budget tight, so
M22 recalibrates it.

*Afterwards.* The layout moves to Life only (D-14), and the ready Agent
Components are listed there with Run. That supersedes FR-I6's placement
of the list at Implementation's end (A-6). Collection then begins
(D-17).

---

### D-17 · Life is time-revealed operation

**Ruled: Option B from `project-notes.md` §84.3** (OQ-12). After the
seeding phase closes, Agent One VW collects data and recalibrates, and
every figure it shows is still computed from generated rows.

This is the "maintaining" half of Agent One VW, which builds **and
maintains** the pipeline (D-11), shown live. Seeding showed the
building. Life shows the maintaining.

*Collection is revealing.* Every record already exists; the generators
produced them at startup (FR-AN1). Life starts with a **collection
cursor** set some weeks before the end of each dataset. A deterministic
clock advances the cursor in fixed steps, one simulated week per step.
Each step is an event naming the source, the count and the period:
*"Collected 3,412 tickets from ServiceNow, week 34."* The stream labels
collection as simulated, as FR-A10 does for figures. Nothing is
generated at request time.

*Recalibration is precomputed arithmetic.* At fixed intervals, every
few steps, a recalibration event recomputes the baselines over the
collected window and re-scores the findings. It reports what moved: the
baseline from and to, and which clusters were newly confirmed or
withdrawn. The generator precomputes the baselines and scores **for
every step**, so FR-AN3's rule of no statistics at request time holds.
The work that computes one step today runs once per step at startup.
M19 measures the cost against NFR-P1. It is expected to stay far inside
budget, given that the whole of generation costs 0.108 s.

*One more filter term, not a new mechanism.* The collection step is a
term in the filter context (FR-EV1). Every dashboard therefore follows
it with no per-dashboard code (D-1, FR-EV4), and it is URL-synced (D-3),
so a rehearsal link can open any step.

*The system advances; a drilled-in view pins.* There are two cursors,
and the distinction is what keeps findings stable under a viewer:

- The **system cursor** lives in System State and moves with the clock.
- The **view cursor** lives in the dashboard's filter context. At the
  top of the breadcrumb, the view follows the system. Once the viewer
  drills in, the view **pins** to the step it was at. It says how many
  collections are newer, and it catches up when the viewer returns to
  the top or asks it to.

A real system does not pause collection because someone is looking, so
this does not pretend it does. It behaves like a live analytics tool
that has newer data available. No finding changes while a viewer is
inside it.

*Findings name their calibration.* The evidence panel (FR-EV7) states
the calibration a finding was scored under: *"Baseline as of
recalibration 2, week 36."* A finding that differs between steps then
reads as maintenance, not as instability.

*Collection is finite.* The cursor stops at the end of the dataset, and
the stream reports Agent One VW as caught up. A finite sequence keeps
two runs from Reset identical (A-2), and gives the demo a clean end
state. Operator speed applies to the clock (FR-O3). Operator skip
completes collection at once. Reset clears it.

*Not chosen.* The parts of Option C are not built: precision and recall
against ground truth, the per-component status strip, and the
operations console. They remain available if a later session asks for
the agent framing.

*Requirement cost.* Two amendments, both narrow:

- **A-8.** Recalibrating baselines within a run is not the Evolution
  phase that §4.1 excludes. Evolution means changing methodologies,
  components or code, and none of those changes.
- **A-9.** FR-AN4's "true counts" become the true counts of the data
  collected so far. Once collection ends, those are the dataset's full
  counts.

### D-18 · The growth tree grows in the Life pane (2026-09-24)

**Ruled after M17 was reviewed: the tree moves to the Life pane, grows
vertically from seed to tree as the process advances, and hands over to
Agent One VW when the build completes. The lifecycle strip returns to
the Seeding pane.** This amends D-15 and D-14's layout table. It adds
amendments A-10 to A-12.

*Where and when.* The tree stands in the Life pane from planting until
the build completes. Until then the Life pane showed an empty state
(FR-W4), and the thing growing into Agent One VW is the natural content
of the pane that will hold it. When Implementation completes, the tree
gives way, with a short transition, to a "Seeding complete" statement
and Agent One VW (ValueWise™) with its ready Agent Components. Once M18
lands, that hand-over moves to the end of closing, the true end of
seeding.

*The layout follows it.* D-14 made Seeding only the default during the
build. The default is now **Life only** from planting until the build
completes, so the tree is what the audience watches. A pending request
still makes the Seeding pane visible (FR-W5), and the stages and the
stream are one click away. Both at `IMPLEMENTATION_COMPLETE` and Life
only from `READY_TO_RUN` are unchanged.

*Its form follows the process.* Each phase is one growth stage:

| Phase | Stage | Grows by |
| ----- | ----- | -------- |
| Planting | Seed planted | the seed, and a root per layer; the roots bush out into laterals and fine hairs as the plant above them grows |
| Discovery | Sapling | a small leaf per system reached |
| Assessment | Small plant | a pair of leaves per methodology assessed |
| Implementation | Tree | the trunk thickens and a branch grows per Agent Component, lengthening, spreading wide and growing a leafy twig with each part built, fruiting when ready; the crown widens and fills with leaves as the build proceeds |

Growth stays a pure function of the event log (FR-G5), and every step is
an event (FR-G2). The drawing eases continuously towards the state the
log describes, so growth reads as smooth at any speed. Reduced motion,
and a reload, go straight to that state.

*Watering is unchanged* (FR-G3, FR-G4): each evaluated capability
request is a drop, and a refused one is held above the ground. *Changed
by D-19:* an allowed request no longer leaves a drop in the soil. It
sends a pulse through the plant instead.

*Its look* (after review, 2026-09-24). The roots are earth brown, apart
from the green above ground. The soil is a warm tint at the surface that
fades downward and at both ends, so the roots show through it. The tree
spreads wider than it is tall once the build is under way. D-19 adds
the stem's ageing, textures, the leaf cover and the denser roots.

*The strip returns.* With the tree in Life, the Seeding pane has its
lifecycle indicator back: the strip, as built in M4. A-4 is reversed,
and FR-L6 stands again.

### D-19 · Both during the build, and the tree kept after it (2026-09-24)

**Ruled after D-18 was reviewed. The default layout during the build is
Both, not Life only. The tree stays available after the hand-over. The
tree's look deepens.** This amends D-18 and D-14's layout table, and
adds amendments A-13 and A-14.

*Both during the build.* From planting until the build completes, the
default layout is Both. The stages and the record are on one side and
the tree grows on the other, so the process and its growth are watched
together. With both panes showing, the Seeding pane's rail is the
bottom drawer described under D-14. At `READY_TO_RUN` the default
becomes Life only, as before. A-13 supersedes A-11.

*The tree after the hand-over.* When the build completes, the tree
still gives way to "Seeding complete" and Agent One VW. It is no longer
gone. A **Growth** control in the Life pane's header drops the grown
tree open above Agent One VW, and closes it again. The tree is closed
by default, so the pane leads with what was grown. The tree it shows is
the same function of the same log (FR-G5). A new run starts closed.
This is A-14.

*Its look.* The drawing still follows the process, and it is still a
pure function of the log:

- **Stem.** The stem ages from young green to bark as the process
  advances: a little with each system reached and each methodology
  assessed, most of it with the build. The branches lag the trunk, and
  the twigs lag the branches, as younger wood does. Bark furrows and a
  rounded shading appear once the stem has begun to turn.
- **Foliage.** Each cluster is shaded for volume and covered in leaves,
  each leaf with a midrib, in three greens. The leaves fill a cluster
  from its centre outward as it grows, and the outermost ones reach past
  its rim, so the silhouette is leafy rather than round.
- **Roots.** Each layer's root carries eight laterals, each with four
  fine hairs and with nodules along it. Six finer fibres grow between
  the main roots once they begin to bush out. Roots stay below the
  surface. The stem runs down to the seed, where the roots begin, so the
  plant is one piece.
- **Roots that grow** (after review, 2026-09-24). The roots grow with the
  plant, as real roots do. Planting puts out only a radicle, a short
  first root per layer. Each system reached, methodology assessed and
  part built pushes them further, and a lateral appears only once its
  root has grown past it. The roots reach further than the drawing lets
  the eye follow. They fade into the soil around the seed, wider than
  deep, and are slightly blurred, so they read as growing on out of view
  rather than ending.
- **Watering** (after review, 2026-09-24). An allowed request no longer
  leaves a drop in the soil. It sends a pulse through the plant: the
  soil and roots take a blue tint, and the tree glows while it grows a
  little. The pulse lasts 1.1 seconds, long enough to register without
  holding the eye. A burst of requests reads as one longer watering: a
  new pulse starts only once the last has run. The growth is counted
  from the log, so it stays deterministic. The pulse plays live only,
  never for a replay and never under reduced motion. A refused request
  is still held above the ground (FR-G4).
- **The Growth control** drops the tree over the whole Life pane below
  the header. What lies beneath stays mounted.


### D-20 · Closing retires the build tools and consumes the seed (2026-09-24)

**Ruled at M18, from the review of D-19. Closing the seeding phase is
shown as a clean-up that discards the tools that built Agent One VW and
consumes the seed. The seed is no longer needed, because the tree
carries what it held and sustains itself.** This amends D-16 and adds
amendment A-15.

Three questions were answered first:

- The trigger stays D-16's: a person confirms.
- D-16's three operations stand, and a fourth is added.
- The tree shows the clean-up: its stake is removed and its seed husk
  dissolves.

*The fourth operation.* After the interfaces are promoted, closing
retires each build tool (the component generator and the test runner)
and revokes its grant. Each retirement is a capability request:

| Rule   | Decides | When |
| ------ | ------- | ---- |
| PR-095 | ALLOW | a system-owned tool, once the build is complete |
| PR-096 | ESCALATE | while a build is still in progress, because retiring a tool mid-build strands what it was building |
| PR-092 | DENY | anything the system does not own; this also bounds consolidation and clearing |

*The seed consumed.* After the four steps, the stream reports the seed
consumed. Its layers are carried by the Agent Components that grew from
them. The seed files are not touched (FR-C5), and the Planting summary
is still true.

*The rules.* The new group "Closing the seeding phase" holds PR-090 to
PR-096. They are in `rules.py` and `protection.md`, and the parity test
holds the two together.

*In the tree.* The build tools stand beside the trunk as a stake, tied
to it twice, from the start of the build. When closing retires the
tools, the stake is lifted away. When the seed sprouts, it splits into a
husk at the foot of the stem. The husk shrinks with each clean-up step
and is gone once the seed is consumed. The caption reads "Shedding the
seed" during closing and "Standing on its own" after it.

*Its name on screen* (after review, 2026-09-24). The screen calls
closing **Cleanup**: the checklist is "Cleanup, after implementation",
and the bar reads `CLEANUP` while it runs. The code keeps
`CLOSING_SEEDING`, as D-11 keeps other internal names. The confirmation
keeps FR-C1's label, "Run — clean up and close seeding".

*In the Seeding pane.* The Implementation stage ends with the Cleanup
checklist: five entries, the four steps and the seed
consumed. Each shows its decision and rule once it is done. The Activity
stream marks where the clean-up begins with a CLEANUP divider.

### 7.2 Requirement amendments

Applied in `requirements.md`. Superseded requirements are struck through
and left in place, not deleted.

| ID  | Amends | Change | Ruling |
| --- | ------ | ------ | ------ |
| A-3 | FR-L2  | Superseded by FR-L9: the state list gains `CLOSING_SEEDING`. | D-16 |
| A-4 | FR-L6  | Superseded by FR-G1: the growth tree is the Seeding pane's lifecycle indicator. | D-15 |
| A-5 | FR-L8  | Superseded by FR-L10: running returns to the Life pane's component list, not the workspace. | D-14 |
| A-6 | FR-I6  | Superseded by FR-C6: the ready list appears in the Life pane after closing, not at Implementation's end. | D-16 |
| A-7 | §7     | Acceptance includes closing the seeding phase, exploring the dashboard in the Life pane, and watching Agent One VW collect and recalibrate. | D-14, D-16, D-17 |
| A-8 | §4.1   | The Evolution exclusion stands, and is clarified: recalibrating baselines within a run is not Evolution. | D-17 |
| A-9 | FR-AN4 | Superseded by FR-AN10: headline counts are those of the data collected so far. | D-17 |
| A-10 | FR-L6, FR-G1 | A-4 reversed: FR-L6 stands again, and the strip is the Seeding pane's lifecycle indicator. FR-G1 now places the tree in the Life pane during seeding. | D-18 |
| A-11 | FR-W3  | Life only is the default from planting until the build completes. | D-18 |
| A-12 | FR-W4  | Until the build completes, the Life pane shows the growing tree rather than an empty state. When it completes, the tree hands over to Agent One VW. | D-18 |
| A-13 | FR-W3  | Supersedes A-11: Both is the default from planting until the build completes. | D-19 |
| A-14 | FR-W4  | After the hand-over the tree stays available: a Growth control in the Life pane's header drops it open above Agent One VW. | D-19 |
| A-15 | FR-C3, FR-C5 | Closing performs four operations, not three: the fourth retires the build tools and revokes their grants. Then the seed is consumed. | D-20 |

New requirement groups: FR-N (display vocabulary), FR-W (panes), FR-G
(growth tree), FR-C (closing), FR-LF (Life pane), plus FR-A11 to FR-A13,
FR-AN10, NFR-A7 and NFR-V7.

### 7.3 Deferred

**Visual continuity with the Agent One demo** (OQ-13). Deferred entirely
at the stakeholder's direction. Agent One is a separate demo that shows
the detailed agentic steps inside an analysis. It is not in this
repository or on the build machine.

If continuity is revived, one boundary needs checking first. A demo
built on detailed agentic steps presses against FR-E9, which forbids
showing simulated internal reasoning, and against NFR-D1. Borrowing its
**visual style** is compatible with both. Borrowing its **step-by-step
narration** is not, unless those requirements are amended.

### 7.4 Open questions raised, and their answers

All six were answered on 2026-09-23, the same day they were raised.

| ID    | Question | Answer |
| ----- | -------- | ------ |
| OQ-8  | What "Agent One VW" names | **What grows out of the Seed:** Agent One VW (ValueWise™), the framework that implements the methodology of building and maintaining the pipeline. Agent Components are its parts. D-11. |
| OQ-9  | Whether methodologies are renamed "Seed" | **Assess, then rename only if a seed-themed name is coherent; rename Systems to Seed.** Assessed: no coherent name found, so methodologies keep their name. D-11. |
| OQ-10 | What "routing problem" means; D-12's MEDIUM and LOW | **Evidence that exists but cannot reach the analysis.** MEDIUM and LOW wording accepted. D-12. |
| OQ-11 | Which progress bar the tree replaces | **The lifecycle strip.** D-15. |
| OQ-12 | Which Life pane option | **Option B, time-revealed operation.** D-17. |
| OQ-13 | Where the Agent One demo is | **Deferred.** Skip continuity for now. §7.3. |

### 7.5 Risk register additions

| ID   | Risk | Likelihood / Impact | Mitigation |
| ---- | ---- | ------------------- | ---------- |
| R-12 | The code and the screen use different words: `solution` in code, "Agent Component" on screen. | Certain / Low | D-11's glossary. New code uses the code vocabulary. |
| R-13 | **Silent-failure renames.** CSS selectors keyed to values, such as `[data-grade='PARTIAL']`, and cross-boundary string ids, such as `'solution-approval'` in `AssessmentStage.vue:25` and `knowledge/solutions.py:32`, break without a type error or a failing test. | Medium / Medium | M12's audit classifies them before M13. The exit criteria of M11 and M13 include a visual check of grade colours and the approval flow. |
| R-14 | The growth tree reads as decoration, or as the "AI toy" effect NFR-V4 and NFR-V6 forbid. | Medium / High | D-15 ties every segment and watering step to an event. NFR-V7 sets a motion budget. M21 reviews it. |
| R-15 | Closing the seeding phase lengthens a narrative R-11 already calls tight. | Medium / Medium | Closing has a fixed D-8 weight. M22 recalibrates the total, and raising the total is one number. |
| R-16 | The stakeholder's terms carry meanings not yet confirmed: "Agent One VW", "routing problem", "the progress bar", and the Agent One style. Building on an interpretation risks rework. | **Closed.** | OQ-8 to OQ-12 answered, and OQ-13 deferred, before any milestone built on them. |
| R-17 | "Self-improving" collides with the Evolution exclusion (§4.1), and live collection with determinism (NFR-D4). | **Resolved.** | D-17's recalibration is precomputed and finite, so A-2 holds. A-8 states why it is not Evolution. |
| R-18 | **Two cursors confuse.** The system cursor advances while a drilled-in view stays pinned, and a viewer may not realise they are looking at an earlier step. | Medium / Medium | The pinned view always says how many collections are newer, and the evidence panel names its calibration (D-17). M21 designs the treatment. |
