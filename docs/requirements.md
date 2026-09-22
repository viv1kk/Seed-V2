# Systems --- V1 Requirements

> **Status:** Agreed baseline.
>
> **Related documents:**
> `project-notes.md` --- vision and product context (§§1--82). Aspirational;
> describes the eventual agentic system.
> `implementation-plan.md` --- how these requirements will be built.
> `decisions.md` --- rulings on open decisions, and the amendments A-1 and
> A-2 applied below.
>
> Where this document and `project-notes.md` §§1--82 disagree, **this
> document wins**. References of the form (§N) point back to the vision
> document for rationale.

---

## 1. Purpose and context

V1 is a **visually polished, fully deterministic simulation** of a
methodology-driven autonomous enterprise analytical system.

It demonstrates the behaviour and architecture of the eventual product
without implementing real enterprise integration, autonomous agents, or
cloud deployment.

The demo narrative runs: plant a seed → discover a client environment →
assess analytical feasibility → escalate decisions to a human → build
approved solutions → run them → explore results down to underlying
evidence.

**The audience is a viewer being shown the system.** Every requirement
below exists to make that viewing experience credible and inspectable.

---

## 2. Goals

| ID   | Goal                                                                                                                       |
| ---- | -------------------------------------------------------------------------------------------------------------------------- |
| G-1  | Demonstrate that the system is driven by an explicit **methodology**, not by prompting a model (§69, §71).                    |
| G-2  | Show the system building an understanding of an initially **unknown environment** (§15).                                     |
| G-3  | Show that autonomy exists inside **hard governance boundaries** the viewer can inspect (§9, §10).                            |
| G-4  | Show humans as **decision authorities at meaningful boundaries**, not approvers of every step (§74).                         |
| G-5  | Produce conclusions that **trace back to underlying data**, with no unexplained assertions (§23, §35, §72).                   |
| G-6  | Deliver a genuinely **interactive analytical application**, not a static report (§31, §32).                                  |
| G-7  | Prove an architecture where each simulated subsystem can later be **replaced by a real one without rewriting the UI** (§41, §75). |
| G-8  | Run **reliably and identically** every time it is demonstrated (§45).                                                        |

### Non-goals

V1 is explicitly not a chatbot, a RAG application, a static BI dashboard,
a CRUD application, or a collection of fake AI agents (§70).

---

## 3. Scope

### 3.1 Built for real

- User interface, in full
- Lifecycle state machine
- Event generation, streaming, and replay
- Seed file upload, validation, and heading-level parsing
- Human-in-the-loop interaction and escalation
- Policy evaluation (genuinely evaluative, not scripted)
- Solution lifecycle and state transitions
- Deterministic analytical datasets
- Aggregation, filtering, cross-filtering, drill-down
- Evidence computation
- Dashboard rendering and chart interaction

### 3.2 Simulated

- Enterprise discovery and network scanning
- All system connections (ServiceNow, SAP, SQL Server, License
  Management, Legacy Registry)
- Credential validation
- Agent reasoning
- Code generation
- Model training
- Build, test execution, and deployment

The boundary between §3.1 and §3.2 must remain legible in the code
structure (§63).

---

## 4. Out of scope

### 4.1 Excluded from V1

| Area                  | Excluded                                                                 |
| --------------------- | ------------------------------------------------------------------------ |
| Intelligence          | Any LLM or inference, anywhere, in any phase                             |
| Seed                  | Seed **content** driving system behaviour; knowledge compilation         |
| Integration           | Real connectors, real credentials, real network access                   |
| Lifecycle             | Evolution phase                                                          |
| Persistence           | Durable state, pause/resume, resume after restart                        |
| Packaging             | Docker, containerisation, hosted deployment                              |
| Build phase           | Generated source-code artifacts shown to the viewer                      |
| Failure handling      | Failure-injection mode beyond the single scripted timeout                |
| Platform              | Authentication, multi-user, multi-client, distributed infrastructure     |

### 4.2 Deliberately discarded from the vision document

- **§19's discovery totals** ("7 Systems / 14 Data Sources / 31 Relevant
  Datasets"). The environment contains exactly the five systems named in
  §42; reported counts are computed from what actually exists.
- **§29's Docker requirement**, replaced by a single-command local
  launcher.
- **§71's LLM seams**, recorded as future work only.

---

## 5. Functional requirements

### 5.1 Seed and initialization --- `FR-S`

| ID     | Requirement                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FR-S1  | The repository ships three genuine seed files --- `core.md`, `adaptation.md`, `protection.md` --- containing real methodology, mapping and policy content.      |
| FR-S2  | The INIT screen presents the three layers as a deliberate "plant the seed" gesture, not a generic file uploader (§12, §48).                                    |
| FR-S3  | All three layers must be supplied before initialization can proceed.                                                                                          |
| FR-S4  | The loader validates each file is present and parseable as Markdown, and rejects it otherwise with a clear reason.                                             |
| FR-S5  | The loader parses each file's **heading structure** and displays a per-layer "loaded / parsed" summary derived from it (§67). This summary is genuinely derived from file content. |
| FR-S6  | Seed file content **must not** alter system behaviour. Methodologies, feasibility outcomes and policy rules are fixed regardless of what is uploaded.          |
| FR-S7  | A hidden operator affordance loads the bundled seed files without using a file picker.                                                                        |

### 5.2 Lifecycle and state --- `FR-L`

| ID     | Requirement                                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-L1  | The system implements a formal state machine with an explicit transition table, not scattered boolean flags (§59).                                  |
| FR-L2  | States: `UNINITIALIZED`, `INITIALIZED`, `DISCOVERING`, `DISCOVERY_BLOCKED`, `DISCOVERY_COMPLETE`, `ASSESSING`, `AWAITING_APPROVAL`, `IMPLEMENTING`, `IMPLEMENTATION_COMPLETE`, `READY_TO_RUN`, `RUNNING` (§58). |
| FR-L3  | An attempted illegal transition raises an error rather than mutating state.                                                                        |
| FR-L4  | Blocking on human input is represented as a flag (`blockedOn`) alongside the current state, not as a separate state per phase.                      |
| FR-L5  | System State is the sole source of truth. Simulated agents read from and write to it; they never hold authoritative state internally (§37, §73).     |
| FR-L6  | A persistent lifecycle indicator shows completed, current and future phases at all times (§14).                                                    |
| FR-L7  | State is held in memory for a single run. An explicit Reset returns the system to `UNINITIALIZED`.                                                  |
| FR-L8  | From `READY_TO_RUN`, the user can run any ready solution, return to the workspace, and run another. Completion is per-solution, not global.         |

### 5.3 Event stream --- `FR-E`

| ID     | Requirement                                                                                                                                     |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-E1  | All system activity is expressed as events. The UI reacts to the event stream rather than knowing how agents work (§38).                          |
| FR-E2  | Events are delivered to the frontend over SSE.                                                                                                  |
| FR-E3  | Every event carries a monotonic sequence number, timestamp, machine-readable `type`, `phase`, display `category`, `severity` and `message`.       |
| FR-E4  | Display categories: `DISCOVERY`, `ANALYSIS`, `VALIDATION`, `DECISION`, `POLICY`, `WARNING`, `SUCCESS`, `HUMAN_INPUT` (§16).                        |
| FR-E5  | The frontend fetches a full state snapshot on connect, then applies events from that snapshot's sequence number onward.                           |
| FR-E6  | A detected sequence gap causes the frontend to discard local state and re-snapshot.                                                              |
| FR-E7  | Reconnection replays missed events exactly, from the retained event log.                                                                        |
| FR-E8  | The activity stream presents events as an **auditable activity stream**, not a developer terminal (§16).                                          |
| FR-E9  | Events report operational facts and decision-relevant reasons only. No simulated internal reasoning or chain-of-thought is displayed (§16).       |

### 5.4 Discovery --- `FR-D`

| ID     | Requirement                                                                                                                             |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| FR-D1  | The mock environment contains exactly five systems: ServiceNow, SAP, SQL Server, License Management System, Legacy Application Registry (§42). |
| FR-D2  | Each system expands during discovery into its constituent services, APIs, databases and datasets (§50).                                   |
| FR-D3  | The environment is rendered as a graph whose nodes appear progressively as they are discovered (§15).                                     |
| FR-D4  | Node statuses: `unknown`, `detected`, `testing`, `validated`, `requires-input`, `connected`, `error` (§50).                               |
| FR-D5  | Edge kinds: `contains`, `connects_to`, `provides`, `depends_on` (§50).                                                                   |
| FR-D6  | The Legacy Application Registry is presented as administrator-supplied rather than automatically discovered (§8, §19).                    |
| FR-D7  | Discovery pauses for a scripted credential request and resumes on submission (§68).                                                       |
| FR-D8  | Discovery includes exactly one technical failure --- an endpoint timeout --- which the system retries and recovers from.                  |
| FR-D9  | On completion, the system reports counts of systems, data sources and datasets **computed from the constructed graph**, never authored.    |
| FR-D10 | Discovery completion displays per-system connection status and which methodologies appear feasible (§19).                                |

### 5.5 Protection layer --- `FR-P`

| ID     | Requirement                                                                                                                                 |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-P1  | Policy enforcement is implemented as an evaluative engine that matches requested actions against a rule set. It is not scripted output (§10). |
| FR-P2  | Every simulated agent action requiring a capability passes through the policy engine before proceeding.                                      |
| FR-P3  | Decision effects: `ALLOW`, `DENY`, `ESCALATE` (§62).                                                                                         |
| FR-P4  | Policy decisions appear inline in the activity stream as first-class events, citing the action, resource, effect and rule id.                 |
| FR-P5  | A dedicated Protection panel displays the active rule set, running counts of allowed / denied / escalated requests, and a filterable audit log. |
| FR-P6  | The demo includes at least one `DENY` and one `ESCALATE` decision, so the layer is visibly a boundary rather than a formality.                |
| FR-P7  | The rule set shown in the UI corresponds to the rules documented in `protection.md`.                                                          |

### 5.6 Human-in-the-loop --- `FR-H`

| ID     | Requirement                                                                                                                                   |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-H1  | The human input surface appears only when input is required, and disappears once resolved. It does not permanently occupy screen space (§17).    |
| FR-H2  | Each request states what is needed, what access is required, and **why** (§17).                                                                 |
| FR-H3  | Request kinds are distinct and visually distinguished: `credentials`, `ambiguity`, `missing-info`, `approval`, `confirmation` (§18).             |
| FR-H4  | Technical **errors**, human **decisions**, and **insufficient evidence** are presented as three different states and must not be conflated (§61). |
| FR-H5  | Submitted credential values are discarded after use. No credential storage is implemented (§62).                                               |
| FR-H6  | All human decisions are recorded in System State and remain visible in the audit log (§26).                                                    |
| FR-H7  | Resolution resumes the paused workflow from its exact point of suspension.                                                                     |

### 5.7 Assessment and feasibility --- `FR-A`

| ID     | Requirement                                                                                                                                  |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-A1  | Three methodologies are assessed: Ticket Anomaly Detection, License Optimization, Application Portfolio Rationalization (§43).                  |
| FR-A2  | Each methodology declares its required evidence. Feasibility is **computed** by matching those requirements against discovered data sources and their field completeness. |
| FR-A3  | Feasibility is graded (`HIGH` / `MEDIUM` / `PARTIAL` / `LOW`), never binary.                                                                    |
| FR-A4  | Each assessment exposes: feasibility, data sufficiency, coverage, per-requirement evidence status, known limitations, and a recommendation (§21). |
| FR-A5  | License Optimization reports `PARTIAL` feasibility due to incomplete cost information, stated as a limitation on an **approvable** solution rather than a blocker (§20). |
| FR-A6  | Where feasibility is reduced, the system states what would improve it (§20).                                                                   |
| FR-A7  | Solutions are presented as cards showing feasibility, data sufficiency, evidence coverage and a description, with Review and Approve actions (§24). |
| FR-A8  | Review opens a detail surface within the workspace --- drawer or panel --- without navigating away (§25).                                       |
| FR-A9  | The detail surface shows why the methodology is feasible, the methodology's process chain, and its limitations (§25).                           |
| FR-A10 | Feasibility figures are presented as simulated demo values and must not be implied to be real enterprise measurements (§21).                    |

### 5.8 Approval --- `FR-AP`

| ID      | Requirement                                                                                          |
| ------- | ------------------------------------------------------------------------------------------------------ |
| FR-AP1  | No solution advances to implementation without explicit human approval (§26).                          |
| FR-AP2  | Solution states: `PROPOSED` → `AWAITING_APPROVAL` → `APPROVED` → `BUILDING` → `READY` → `RUNNING`, with `REJECTED` as a terminal branch (§26). |
| FR-AP3  | Approvals and rejections are recorded in System State with their outcome preserved.                    |
| FR-AP4  | All three solutions are approvable and reach a runnable state.                                        |

### 5.9 Implementation phase --- `FR-I`

| ID     | Requirement                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------ |
| FR-I1  | The workspace persists into implementation; the visualization pane changes from environment graph to build pipeline (§27).      |
| FR-I2  | Pipeline nodes progress through `PENDING` → `BUILDING` → `TESTING` → `VALIDATED` → `COMPLETE` (§52).                            |
| FR-I3  | The activity stream reports build progress in realistic terms (§28).                                                          |
| FR-I4  | The test stage expands into a detailed result view: named test cases, pass/fail status, and timings.                           |
| FR-I5  | No generated source code is displayed, because none is generated.                                                             |
| FR-I6  | On completion, each solution is listed as Ready with a Run action (§30, §53).                                                  |

### 5.10 Analytics --- `FR-AN`

| ID      | Requirement                                                                                                                                       |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-AN1  | Analytical datasets are produced by committed generators with a fixed RNG seed, built into memory at backend startup.                                |
| FR-AN2  | Datasets contain deliberately planted patterns --- a normal population plus intentionally anomalous clusters (§45).                                  |
| FR-AN3  | Anomaly labels, scores and baselines are produced at generation time. No statistics or machine learning run at request time.                          |
| FR-AN4  | Headline metrics report the dataset's true counts.                                                                                                  |
| FR-AN5  | All aggregation is performed in the backend from record-level data. The frontend contains no analytical logic.                                       |
| FR-AN6  | Ticket Anomaly Detection receives a deep, fully polished dashboard (§44).                                                                            |
| FR-AN7  | License Optimization and Application Portfolio Rationalization each receive a dashboard with roughly 3--4 interactive charts and one drill-down path.  |
| FR-AN8  | Every chart is interactive. Decorative charts are not acceptable (§32).                                                                             |
| FR-AN9  | Supported interactions include hover tooltips, click selection, cross-filtering, time-range filtering, category filtering, drill-down, breadcrumb navigation, table views and detail panels (§32). |

### 5.11 Drill-down, cross-filtering and evidence --- `FR-EV`

| ID      | Requirement                                                                                                                                             |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-EV1  | A single filter context --- time range, dimension selections, optional entity --- drives every chart on a dashboard simultaneously.                         |
| FR-EV2  | Any click combination filters correctly. Interaction paths are not enumerated in advance (§34).                                                            |
| FR-EV3  | Drill-down hierarchies are **declared as data per methodology** and served from the backend. Drill-down must not be implemented as hardcoded UI navigation (§56). |
| FR-EV4  | Adding a new methodology requires a generator and a hierarchy descriptor, and no new UI code (§78).                                                        |
| FR-EV5  | A breadcrumb reflects the current drill path, and the user can navigate backward through it (§55).                                                         |
| FR-EV6  | Drill-down terminates at individual underlying records (§33).                                                                                            |
| FR-EV7  | An evidence panel explains any finding with: observed value, baseline, deviation, comparable population size, contributing records, methodology reference, and validation steps (§35, §57). |
| FR-EV8  | Every figure in the evidence panel is computed from the generated records, not authored.                                                                  |

### 5.12 Operator controls --- `FR-O`

| ID     | Requirement                                                                                                                       |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| FR-O1  | Speed control (1x / 2x / instant), skip-to-next-phase, and Reset are available.                                                     |
| FR-O2  | These controls are reachable only by keyboard shortcut or a hidden panel. No transport bar is visible to the audience.              |
| FR-O3  | Speed changes apply to all subsequent simulated delays without disturbing event ordering or state.                                  |
| FR-O4  | Reset returns the system to the seed screen with all state cleared, without restarting the backend.                                 |

---

## 6. Non-functional requirements

### 6.1 Determinism and independence --- `NFR-D`

| ID      | Requirement                                                                                                     |
| ------- | ----------------------------------------------------------------------------------------------------------------- |
| NFR-D1  | No LLM, inference, or model API call occurs anywhere in the system.                                              |
| NFR-D2  | The system runs fully offline with no outbound network dependency.                                               |
| NFR-D3  | No API keys or secrets are required to run the demo.                                                             |
| NFR-D4  | Two runs from Reset produce identical event sequences, identical analytical results, and identical displayed figures, compared **modulo timestamps and durations**: the same events, in the same order, with the same types, categories, severities, payloads and figures (amended by A-2, `decisions.md`). |
| NFR-D5  | Randomness is permitted only through fixed, committed seeds.                                                     |

### 6.2 Performance --- `NFR-P`

| ID      | Requirement                                                                                     |
| ------- | ------------------------------------------------------------------------------------------------- |
| NFR-P1  | Backend startup, including dataset generation, completes in under 2 seconds **on a warm interpreter**. First-ever import of Python dependencies on a cold machine is excluded (amended by A-1, `decisions.md`). |
| NFR-P2  | Any dashboard filter or drill-down interaction returns in under 200 ms.                          |
| NFR-P3  | The activity stream remains responsive for the full duration of a demo run.                      |
| NFR-P4  | The full demo narrative runs in a presentable duration at 1x speed, and much faster at instant.   |
| NFR-P5  | Simulated delays create the perception of an active system without making the demo tedious (§46). |

### 6.3 Architecture --- `NFR-A`

| ID      | Requirement                                                                                                                              |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| NFR-A1  | The API layer depends on an event-source abstraction, never on the simulation engine directly. A real agent runtime must be substitutable behind it (§41). |
| NFR-A2  | The frontend must not require rewriting when simulated subsystems are replaced with real ones (§75).                                       |
| NFR-A3  | The workspace remains mounted across Discovery, Assessment and Implementation. Only its panes change (§13).                                |
| NFR-A4  | The real/simulated boundary of §3 is legible in the code structure (§63).                                                                  |
| NFR-A5  | No Kafka, Redis, PostgreSQL, Kubernetes, vector database, microservices, agent framework or LLM orchestration framework is introduced (§64, §79). |
| NFR-A6  | Architectural boundaries take precedence over infrastructure sophistication (§79).                                                         |

### 6.4 Visual design --- `NFR-V`

| ID      | Requirement                                                                                                                       |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| NFR-V1  | The interface is minimal, technical, premium, calm, and information-dense without clutter (§47).                                    |
| NFR-V2  | Both light and dark themes are supported and toggleable, derived from a single set of design tokens.                                |
| NFR-V3  | Chart palettes are validated for contrast in both themes.                                                                          |
| NFR-V4  | Avoided: excessive gradients, generic "AI" glow effects, robot or agent illustrations, excessive cards, fake futuristic styling, too many colours, excessive motion (§47). |
| NFR-V5  | Animation corresponds to actual state changes. Decorative animation is not acceptable (§46).                                        |
| NFR-V6  | The visual language communicates serious analytical infrastructure, not an AI toy (§47).                                           |

### 6.5 Delivery --- `NFR-L`

| ID      | Requirement                                                                            |
| ------- | ---------------------------------------------------------------------------------------- |
| NFR-L1  | A single command starts backend and frontend together.                                  |
| NFR-L2  | The stack is Vue 3 + TypeScript + Pinia + Vite, FastAPI, SSE, and Apache ECharts.        |
| NFR-L3  | Bespoke visualizations --- the environment graph and build pipeline --- are hand-built SVG. |
| NFR-L4  | The demo targets a modern desktop browser at presentation resolution.                    |

---

## 7. Acceptance

V1 is complete when a presenter can, from a clean start and without
touching a terminal, perform the twenty-step narrative of §68 end to
end --- and when a sceptical viewer can then click freely through the
Ticket Anomaly dashboard, follow any anomaly down to individual source
records, and find the numbers consistent at every level.

---

## 8. Open questions

Not blocking; to be resolved during implementation. OQ-4, OQ-5 and OQ-7
are closed in `decisions.md`; the rest are carried.

| ID    | Question                                                                                                        |
| ----- | ----------------------------------------------------------------------------------------------------------------- |
| OQ-1  | Exact chart inventory per dashboard. §54 lists candidates rather than a specification.                            |
| OQ-2  | Drill-down hierarchies for License Optimization and Application Portfolio Rationalization.                        |
| OQ-3  | Accent colour and typeface selection.                                                                            |
| OQ-4  | ~~Whether the activity stream requires virtualisation.~~ Provisionally **no**; confirm at M13. See `decisions.md` §4. |
| OQ-5  | ~~Whether dataset generation needs a local cache.~~ Measured: **no**. See `decisions.md` §1. |
| OQ-6  | Which specific actions trigger the required `DENY` and `ESCALATE` policy decisions of FR-P6.                      |
| OQ-7  | ~~Target wall-clock duration of the full narrative at 1x.~~ Ruled: **4 to 5 minutes**. See `decisions.md` §4. |
