# Systems --- V1 Decision Record

> **Status:** Ruled. This document closes section 5 of
> `implementation-plan.md` and resolves the two requirement conflicts
> recorded there as R-1 and R-7.
>
> Where a ruling amends `requirements.md`, the amendment is stated here
> and applied there. Where a ruling is supported by measurement, the
> measurement is given.

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
| OQ-1 | Exact chart inventory per dashboard                  | M9        |
| OQ-2 | Drill-down hierarchies for the two smaller solutions | M9        |
| OQ-3 | Accent colour and typeface                           | M12       |

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
