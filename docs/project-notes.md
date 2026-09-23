# Systems --- Autonomous Analytical System

## Extended Project Context, Product Vision, Architecture and Demo Specification

> **Purpose of this document:**\
> This document is the detailed context/specification to give Claude
> Code before beginning implementation planning. It explains the
> conceptual system, methodology, lifecycle, demo behavior, UI intent,
> architecture principles, and MVP boundaries.
>
> **Important:** This is a planning/specification document, not an
> instruction to immediately generate the entire application. Claude
> Code should first understand the system, identify architectural
> decisions, surface ambiguities, and propose an implementation plan.

------------------------------------------------------------------------

# 1. Executive Summary

The project is a simulation of an **autonomous enterprise analytical
system**.

The fundamental idea is that the system is not simply an AI chatbot, an
agent framework, or a dashboard generator.

Instead, the system contains a **problem-solving methodology** as its
internal "intelligence". This methodology can be planted into a client
environment, where autonomous agents discover the available enterprise
systems and data, assess whether the methodology can be applied, build
analytical solutions, and eventually expose those solutions through
interactive dashboards.

The conceptual lifecycle is:

``` text
             SEED
               │
               ▼
             INIT
               │
               ▼
          DISCOVERY
               │
               ▼
        ASSESSMENT / GROWTH
               │
          HUMAN APPROVAL
               │
               ▼
         IMPLEMENTATION
               │
          HUMAN CONFIRMATION
               │
               ▼
       DEPLOYMENT / RUN
               │
               ▼
           ANALYTICS
```

For the initial demo, the entire enterprise environment and agent
execution can be **simulated**.

The goal is to demonstrate the *behavior and architecture of the
eventual system* without first having to implement real
ServiceNow/SAP/network discovery, production credentials, autonomous
code generation, or cloud deployment.

------------------------------------------------------------------------

# 2. The Problem This System Is Trying to Solve

The organization has methodologies for solving enterprise problems such
as:

-   Application Portfolio Rationalization
-   Ticket Anomaly Detection
-   License Optimization

These exercises are not merely collections of predefined reports.

They follow a common underlying approach to problem solving:

1.  Start from first principles.
2.  Remove irrelevant noise.
3.  Understand the actual problem.
4.  Identify the relevant data.
5.  Assess data quality and sufficiency.
6.  Establish measurable baselines.
7.  Form hypotheses.
8.  Test hypotheses against evidence.
9.  Use mathematics/statistics where appropriate.
10. Use machine learning where it provides value.
11. Validate conclusions.
12. Derive recommendations from evidence.
13. Make assumptions explicit.
14. Escalate ambiguity to a human when necessary.

The proposed system attempts to **encode this methodology into a
reusable autonomous system**.

Instead of a consulting/analytical team manually repeating the same
methodology for every client, the system should eventually be able to
take the methodology, understand a new environment, discover available
evidence, adapt the methodology to that environment, and construct the
appropriate analytical solution.

------------------------------------------------------------------------

# 3. The Seed Analogy

The system is intentionally modeled around a **seed** analogy.

The seed contains the conceptual intelligence needed for the system to
operate.

The seed is planted into an unknown client environment.

The system then:

``` text
Seed
 │
 ├── Understand itself
 │
 ├── Understand the environment
 │
 ├── Determine what can grow
 │
 ├── Build the appropriate solution
 │
 └── Produce useful analytical output
```

This is not intended merely as a visual metaphor.

It should influence the architecture:

-   The Core should remain largely environment-independent.
-   The Adaptation layer should learn how to connect the Core to a
    particular environment.
-   The Protection layer should constrain what the system is allowed to
    do.
-   The system should progressively accumulate knowledge about its
    environment.
-   Solutions should emerge from the interaction between methodology and
    environment.

------------------------------------------------------------------------

# 4. Three Persistent Layers

There are three conceptual layers.

They are **not lifecycle stages**.

They persist throughout the lifecycle and have different
responsibilities.

``` text
                    ┌───────────────────────────┐
                    │     PROTECTION LAYER       │
                    │                           │
                    │ Security / Governance     │
                    │ Agent permissions         │
                    │ Data integrity            │
                    │ Human approvals           │
                    │ Policy enforcement        │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │      ADAPTATION LAYER     │
                    │                           │
                    │ Environment discovery     │
                    │ Connectors                │
                    │ Schema understanding      │
                    │ Data mapping              │
                    │ Source assessment         │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │         CORE LAYER        │
                    │                           │
                    │ Methodology               │
                    │ Domain knowledge          │
                    │ Mathematics               │
                    │ Statistics                │
                    │ ML approaches             │
                    │ Hypothesis testing        │
                    │ Evidence requirements     │
                    └───────────────────────────┘
```

------------------------------------------------------------------------

# 5. Core Layer

## 5.1 Purpose

The Core is the intellectual foundation of the system.

It answers:

> **"How should this problem be thought about and solved?"**

It should contain the methodology independent of a particular client.

For example, the Core may know:

-   What Application Portfolio Rationalization means.
-   What evidence is required to determine whether an application is a
    candidate for retirement.
-   How to establish usage baselines.
-   How to identify dependencies.
-   What assumptions invalidate a conclusion.
-   What statistical methods are appropriate for a particular question.
-   When ML is justified.
-   How anomalies should be validated.
-   What constitutes sufficient evidence.

------------------------------------------------------------------------

## 5.2 The Core is NOT simply a document repository

For the demo, Markdown can be the input format.

For example:

``` text
core.md
```

However, the conceptual architecture should not assume:

``` text
Markdown → RAG → LLM → answer
```

That would make the system little more than a chatbot with
documentation.

Instead, think of the Core as containing several types of knowledge:

``` text
CORE
│
├── Concepts
│
├── Methodologies
│
├── Procedures
│
├── Mathematical methods
│
├── Statistical methods
│
├── ML methods
│
├── Hypothesis templates
│
├── Evidence requirements
│
├── Assumptions
│
├── Validation rules
│
├── Failure modes
│
└── Decision frameworks
```

Eventually, the human-authored knowledge may be compiled into structured
representations.

For example:

``` text
Human-authored Markdown/YAML
            │
            ▼
      Knowledge Loader
            │
      ┌─────┼─────┐
      ▼     ▼     ▼
    Rules  Methods Concepts
      │     │     │
      └─────┼─────┘
            ▼
     Runtime Knowledge
```

The MVP does not need to implement a sophisticated knowledge compiler.

------------------------------------------------------------------------

# 6. Adaptation Layer

The Adaptation layer answers:

> **"How do I apply the methodology to this specific client
> environment?"**

The Core may say:

> "License optimization requires entitlement, assignment, usage and cost
> information."

The Adaptation layer determines:

``` text
Where is entitlement information?

Where is assignment information?

Where is usage information?

Where is cost information?

How do I retrieve each dataset?

What fields correspond to the concepts expected by the Core?

Are those fields complete and trustworthy?
```

This is what makes the methodology reusable across different client
environments.

------------------------------------------------------------------------

# 7. Discovery

The Adaptation layer initially acts like a scouting mechanism.

The system starts with incomplete knowledge.

The Discovery Agent explores the environment and builds an Environment
Registry.

Potential discovery mechanisms include:

-   Network discovery
-   Endpoint discovery
-   API discovery
-   Database discovery
-   Service identification
-   Configuration inspection
-   Data-source discovery
-   Admin-provided information

Example:

``` text
Unknown Client Environment

        ↓

ServiceNow discovered
SAP discovered
SQL Server discovered
License Management System discovered
Legacy system reported by Admin

        ↓

Environment Registry
```

------------------------------------------------------------------------

# 8. Admin-Provided Discovery Information

Not everything can be automatically discovered.

Some systems may:

-   Be isolated.
-   Require special procedures.
-   Be legacy systems.
-   Not expose discoverable endpoints.
-   Require explicit administrator knowledge.
-   Exist behind special network boundaries.

Therefore, Discovery must support human input.

Example:

``` text
AGENT:

I have discovered an application registry but cannot
determine whether it is authoritative.

Please provide information.

[ Application Registry is authoritative ]

[ SAP inventory is authoritative ]

[ Both are required ]
```

Another example:

``` text
AGENT:

A legacy license database was reported by the administrator.

Please provide:

Connection method
Credentials
Read-only access

[ Configure ]
```

------------------------------------------------------------------------

# 9. Protection Layer

The Protection Layer is cross-cutting.

It exists throughout:

``` text
INIT
DISCOVERY
ASSESSMENT
IMPLEMENTATION
DEPLOYMENT
RUN
```

It should govern:

-   Identity
-   Authentication
-   Authorization
-   Credentials
-   Tool access
-   Data access
-   Data movement
-   Agent capabilities
-   Human approvals
-   Destructive operations
-   Evidence integrity
-   Hypothesis validation
-   Auditability

The key philosophy is:

> **The system can be autonomous, but autonomy exists inside hard
> boundaries.**

------------------------------------------------------------------------

# 10. Protection Should Not Be Prompt-Only

A critical architectural principle:

Do not rely entirely on an LLM instruction such as:

``` text
"Do not delete production data."
```

Instead:

``` text
Agent
  ↓
Tool request
  ↓
Policy engine
  ↓
Allowed / Denied / Human approval
  ↓
Tool execution
```

For example:

``` text
Read approved ServiceNow API
        ↓
Allowed

Create temporary analytical dataset
        ↓
Allowed

Deploy production service
        ↓
Human approval

Delete source records
        ↓
Denied
```

For the MVP these can be simulated, but the architecture should leave
room for real enforcement later.

------------------------------------------------------------------------

# 11. Lifecycle

The demo lifecycle is:

``` text
INIT
 ↓
DISCOVERY
 ↓
ASSESSMENT / GROWTH
 ↓
HUMAN APPROVAL
 ↓
IMPLEMENTATION
 ↓
DEPLOYMENT / RUN
 ↓
ANALYTICS
```

Evolution is intentionally excluded from V1.

------------------------------------------------------------------------

# 12. INIT Phase

The first screen should be minimal.

The user provides three Seed files:

``` text
Core
Adaptation
Protection
```

For example:

``` text
core.md
adaptation.md
protection.md
```

The UI should communicate:

> **Plant the Seed**

rather than looking like a generic file uploader.

Possible conceptual layout:

``` text
                    PLANT SYSTEMS

              Give the system its foundation.

       ┌──────────┐  ┌──────────────┐  ┌────────────┐
       │   CORE   │  │  ADAPTATION  │  │ PROTECTION │
       │    ✓     │  │      ✓       │  │     ✓      │
       └──────────┘  └──────────────┘  └────────────┘

                    [ Initialize ]
```

Once initialized, the system transitions into Discovery.

------------------------------------------------------------------------

# 13. Main UI Philosophy

After initialization, the user should enter a **persistent system
workspace**.

The page should not completely change between Discovery, Assessment and
Implementation.

Instead:

``` text
Same Workspace
      │
      ├── Lifecycle changes
      ├── Visualization changes
      ├── Activity changes
      ├── State changes
      └── Human input appears when needed
```

This gives the impression that a single system is operating continuously
underneath the UI.

------------------------------------------------------------------------

# 14. Lifecycle Visualization

A persistent lifecycle indicator should be visible.

Conceptually:

``` text
INIT ───── DISCOVERY ───── ASSESSMENT ───── IMPLEMENT ───── DEPLOY
                    ●
                 CURRENT
```

Completed phases should appear complete.

The current phase should have a subtle active state.

Future phases should remain inactive.

Avoid excessive animation.

The visualization should feel like an operating system, not a marketing
animation.

------------------------------------------------------------------------

# 15. Discovery Visualization

During Discovery, the environment should visually grow.

For example:

``` text
                   CLIENT ENVIRONMENT

                          SYSTEM
                         /      \
                  ServiceNow    SAP
                       |
                   SQL Server
                       |
               License Database
```

As the agent discovers systems, nodes can appear progressively.

Potential states:

``` text
Unknown
  ↓
Detected
  ↓
Reachability Testing
  ↓
Validated
  ↓
Understanding Data
  ↓
Registered
```

This is an important visual representation because the user should be
able to see that the agent is building an understanding of an initially
unknown environment.

------------------------------------------------------------------------

# 16. Agent Activity Log

The log is important but should not look like a raw developer terminal.

It should look like an **auditable activity stream**.

Example:

``` text
02:41:07  DISCOVERY
Scanning known enterprise endpoints...

02:41:12  DISCOVERY
ServiceNow endpoint detected

02:41:13  VALIDATION
Testing endpoint reachability...

02:41:14  SUCCESS
Endpoint reachable

02:41:15  DISCOVERY
Identified incident management API

02:41:18  ANALYSIS
Evaluating available incident fields...

02:41:21  WARNING
Authentication required

02:41:21  HUMAN INPUT REQUIRED
ServiceNow credentials are required
```

Potential categories:

``` text
DISCOVERY
ANALYSIS
VALIDATION
DECISION
WARNING
SUCCESS
HUMAN INPUT
```

The log should communicate what the system is doing without exposing
meaningless internal chain-of-thought.

Important distinction:

> Show **operational events and decision-relevant reasons**, not hidden
> model reasoning.

------------------------------------------------------------------------

# 17. Human-in-the-Loop Interaction

The human input interface should only appear when needed.

Do not permanently occupy screen space with an empty input panel.

Example:

``` text
────────────────────────────────────────

             HUMAN INPUT REQUIRED

ServiceNow requires authentication.

Required access:
Read-only Incident API

Reason:
Historical incident data is required for
Ticket Anomaly Detection.

              [ Configure ]

────────────────────────────────────────
```

After submission:

``` text
✓ Credentials configured

Agent continuing...
```

The panel disappears.

------------------------------------------------------------------------

# 18. Human Decision States

The system can encounter several types of human interaction.

## Credentials

``` text
Credentials required
```

## Ambiguity

``` text
Two sources appear to represent the same concept.
Which should be authoritative?
```

## Missing information

``` text
Application ownership information is unavailable.
Provide source or continue with reduced feasibility.
```

## Solution approval

``` text
Solution is ready for implementation.
Approve?
```

## Deployment confirmation

``` text
Solution has been built and validated.
Confirm run?
```

Human involvement should therefore be treated as an **escalation
mechanism**.

------------------------------------------------------------------------

# 19. Discovery Completion

When Discovery completes, the system should transition into an
assessment/reporting state.

Example:

``` text
DISCOVERY COMPLETE

7 Systems
14 Data Sources
31 Relevant Datasets
3 Applicable Methodologies
```

Then show the discovered environment:

``` text
ServiceNow              ✓ Connected
SAP                     ✓ Connected
SQL Server              ✓ Connected
License Database        ✓ Connected
Legacy Application DB   ⚠ Admin supplied
```

The system should then show which methodologies appear feasible.

------------------------------------------------------------------------

# 20. Assessment / Growth Phase

The Growth phase is the analytical heart of the demo.

The system evaluates:

``` text
Environment
    ↓
Available Data
    ↓
Data Quality
    ↓
Methodology Requirements
    ↓
Feasibility
    ↓
Potential Solution
```

The system should not assume that because a methodology exists, it can
automatically be executed.

Example:

``` text
License Optimization

Core requires:
- Entitlement
- Assignment
- Usage
- Cost

Available:
✓ Entitlement
✓ Assignment
✓ Usage
⚠ Cost information incomplete

Result:
Partial feasibility
```

The system can then recommend what would improve feasibility.

------------------------------------------------------------------------

# 21. Feasibility

Every proposed solution should have a clear assessment.

Potential attributes:

``` text
Feasibility
Data Sufficiency
Data Quality
Coverage
Methodology Match
Known Limitations
Missing Information
Expected Analytical Value
```

Example:

``` text
Ticket Anomaly Detection

Feasibility: HIGH

Data sufficiency: HIGH

Available:
✓ Historical tickets
✓ Resolution timestamps
✓ Assignment groups
✓ Priority
✓ Categories

Limitations:
• 8% of records have incomplete categorization

Recommendation:
Proceed
```

The exact numerical feasibility score can be simulated for the demo.

Do not imply that these values are real enterprise measurements.

------------------------------------------------------------------------

# 22. First-Principles Reasoning

The demo should demonstrate the methodology rather than merely state
that AI was used.

For example:

``` text
Question:
Are there anomalous ticket behaviors?

        ↓

Establish baseline

        ↓

Characterize normal behavior

        ↓

Identify deviations

        ↓

Form hypothesis

        ↓

Test against historical data

        ↓

Validate anomaly

        ↓

Quantify impact
```

The same principle should conceptually apply to the other methodologies.

------------------------------------------------------------------------

# 23. Evidence Chain

The system should maintain an evidence chain for conclusions.

Example:

``` text
CONCLUSION

Application X has retirement potential.

        │
        ├── Evidence
        │   ├── No production transactions in 180 days
        │   ├── No active users
        │   ├── Infrastructure cost
        │   └── No detected dependencies
        │
        ├── Hypothesis
        │   └── Application is no longer operationally required
        │
        ├── Validation
        │   ├── Usage analysis ✓
        │   ├── Dependency analysis ✓
        │   └── Owner verification ✓
        │
        ├── Assumption
        │   └── Monitoring coverage is complete
        │
        └── Recommendation
            Human approval required
```

This concept should be visible in the assessment/report experience.

------------------------------------------------------------------------

# 24. Solution List

After Discovery and Assessment, the system should list potential
solutions.

Initial methodologies:

``` text
1. Ticket Anomaly Detection
2. License Optimization
3. Application Portfolio Rationalization
```

Example solution card:

``` text
┌───────────────────────────────────────────┐
│ Ticket Anomaly Detection                  │
│                                           │
│ Feasibility                        High   │
│ Data Sufficiency                   High   │
│                                           │
│ Evidence available: 6 / 6               │
│                                           │
│ Detect anomalous ticket patterns and      │
│ identify operational risk.                │
│                                           │
│ [ Review ]       [ Approve ]              │
└───────────────────────────────────────────┘
```

------------------------------------------------------------------------

# 25. Assessment Report

Clicking Review should expose the detailed assessment.

It does not necessarily need to navigate away from the main workspace.

A drawer/modal/detail panel is appropriate.

Example structure:

``` text
TICKET ANOMALY DETECTION

Why is this feasible?

✓ Historical ticket data
✓ Resolution timestamps
✓ Assignment groups
✓ Priority information
✓ Incident categories
✓ Sufficient historical volume

────────────────────────

Methodology

Baseline
   ↓
Statistical characterization
   ↓
Pattern detection
   ↓
Anomaly identification
   ↓
ML validation

────────────────────────

Limitations

• Historical data begins in 2023
• 8% of tickets lack categorization
• Some SAP-linked tickets cannot be correlated

────────────────────────

[ Approve Solution ]
```

------------------------------------------------------------------------

# 26. Approval

A solution cannot automatically move to implementation.

The Admin explicitly approves it.

Possible state transition:

``` text
PROPOSED
   ↓
AWAITING_APPROVAL
   ↓
APPROVED
   ↓
IMPLEMENTATION
```

If rejected:

``` text
PROPOSED
   ↓
REJECTED
```

The system should preserve the decision in System State.

------------------------------------------------------------------------

# 27. Implementation Phase

After approval, the same main workspace remains.

The lifecycle changes:

``` text
INIT → DISCOVERY → ASSESSMENT → IMPLEMENTATION → DEPLOYMENT
```

The visualization can change from an environment graph into a solution
architecture/build graph.

Example:

``` text
ServiceNow
     ↓
Data Ingestion
     ↓
Normalization
     ↓
Feature Pipeline
     ↓
┌──────────────────────┐
│ Analytical Engine    │
│                      │
│ Statistical Analysis │
│ + ML                  │
└──────────┬───────────┘
           ↓
      Analytics API
           ↓
       Dashboard
```

------------------------------------------------------------------------

# 28. Implementation Activity

The activity stream should show realistic progress.

Example:

``` text
BUILD

Generated data ingestion service
Generated schema validation
Generated normalization pipeline
Generated feature pipeline
Generated anomaly detection engine
Generated analytical APIs
Generated dashboard
Running unit tests
Running integration tests
Validating analytical output
```

For V1, these are simulated operations.

------------------------------------------------------------------------

# 29. Technical Stack

Preferred stack:

## Backend

-   Python
-   FastAPI

## Frontend

-   Vue.js
-   Or another frontend framework if there is a strong reason

## Visualization

-   Plotly or another mature interactive visualization library

## Packaging

-   Docker

The eventual system should have a preferred stack but not an absolute
restriction.

Conceptually:

``` text
Preferred Stack
      ↓
Can deviate if justified
      ↓
Compatibility + Security + Maintainability
```

------------------------------------------------------------------------

# 30. Deployment Phase

Actual infrastructure deployment is outside V1.

The demo focuses on the logical deployment/run lifecycle.

At the end of implementation:

``` text
SYSTEM READY

3 solutions implemented.

Ticket Anomaly Detection
Status: Ready
[ Run ]

License Optimization
Status: Ready
[ Run ]

Application Portfolio Rationalization
Status: Ready
[ Run ]
```

The Admin can select a solution and run it.

------------------------------------------------------------------------

# 31. Analytics Dashboard

The final output should be a real analytical application, not a static
report.

The dashboard should feel like a high-performance enterprise analytics
product.

For V1, Ticket Anomaly Detection can be the primary fully polished
dashboard.

Potential dashboard:

``` text
Ticket Intelligence

Total Tickets     Anomalies     Avg Resolution     Risk
184,392           1,842         6.4h               3.8%
```

Then interactive charts.

------------------------------------------------------------------------

# 32. Interactive Charts

This is a hard requirement.

Charts must support actual interaction.

Examples:

-   Hover tooltips
-   Click selection
-   Cross-filtering
-   Time-range filtering
-   Category filtering
-   Entity filtering
-   Drill-down
-   Breadcrumb navigation
-   Table views
-   Detail panels

The dashboard should not contain charts that are merely decorative.

------------------------------------------------------------------------

# 33. Drill-Down Model

A user should be able to move from high-level analytics to underlying
evidence.

Example:

``` text
All Tickets
    ↓
Anomalous Tickets
    ↓
Reassignment Anomalies
    ↓
Assignment Group: Network Operations
    ↓
Ticket Cluster
    ↓
Individual Tickets
    ↓
Evidence
```

Another example:

``` text
Application Portfolio
       ↓
Business Unit
       ↓
Application
       ↓
Usage Pattern
       ↓
Dependency
       ↓
Underlying Records
```

The exact drill-down structure depends on the methodology.

------------------------------------------------------------------------

# 34. Dashboard Cross-Filtering

Interactions should propagate.

Example:

User clicks:

``` text
Network Operations
```

Then the rest of the dashboard automatically updates:

``` text
Ticket count
Anomaly count
Resolution trend
Priority distribution
Application distribution
Top anomaly patterns
```

This should feel like a real analytical workspace.

------------------------------------------------------------------------

# 35. Evidence From Dashboard

A user should be able to ask "why?" through interaction.

For example:

``` text
1,842 anomalous tickets
        ↓ click
614 reassignment anomalies
        ↓ click
Network Operations
        ↓ click
Cluster #27
```

Then:

``` text
WHY WAS THIS FLAGGED?

Pattern:
Repeated reassignment

Observed:
7.2 average assignments

Baseline:
2.1 average assignments

Deviation:
+242%

Evidence:
• Comparable historical tickets
• Statistical baseline
• Model result
• Source records

[ View underlying records ]
```

This is critical to the philosophy.

The dashboard should connect:

``` text
Result
 ↓
Pattern
 ↓
Data
 ↓
Evidence
 ↓
Methodology
```

------------------------------------------------------------------------

# 36. Analytics Philosophy

The dashboard should demonstrate that the system is not just producing
an answer.

It is producing:

``` text
Answer
+
Evidence
+
Context
+
Drill-down
+
Traceability
```

The user should be able to investigate the result.

------------------------------------------------------------------------

# 37. System State

Agents should not be the source of truth.

The system should maintain a persistent conceptual state.

Example:

``` text
SYSTEM STATE

Environment
├── Systems
├── Services
├── Data Sources
├── Schemas
└── Credential References

Knowledge
├── Methodologies
├── Concepts
├── Rules
└── Procedures

Assessments
├── Data Quality
├── Feasibility
├── Hypotheses
└── Evidence

Solutions
├── Proposed
├── Approved
├── Building
├── Ready
├── Running
└── Failed

Human Decisions
├── Inputs
├── Approvals
└── Rejections

History
└── Events
```

This is important for resilience.

If an agent stops:

``` text
Agent fails
   ↓
System State remains
   ↓
Another agent/process can resume
   ↓
Continue from last valid state
```

------------------------------------------------------------------------

# 38. Event-Driven Model

The UI should ideally react to events rather than directly knowing how
agents work.

Example event:

``` json
{
  "type": "RESOURCE_DISCOVERED",
  "phase": "DISCOVERY",
  "resource": "ServiceNow",
  "status": "detected"
}
```

Another:

``` json
{
  "type": "HUMAN_INPUT_REQUIRED",
  "inputType": "credentials",
  "resource": "ServiceNow",
  "requiredScope": "read-only"
}
```

Another:

``` json
{
  "type": "SOLUTION_PROPOSED",
  "solutionId": "ticket-anomaly",
  "feasibility": "high"
}
```

The UI consumes the event stream and updates itself.

------------------------------------------------------------------------

# 39. Suggested Event Types

``` text
SYSTEM_INITIALIZED

PHASE_STARTED
PHASE_COMPLETED

AGENT_STARTED
AGENT_COMPLETED

DISCOVERY_STARTED
RESOURCE_DISCOVERED
RESOURCE_VALIDATED
DATA_SOURCE_IDENTIFIED
SCHEMA_DISCOVERED

HUMAN_INPUT_REQUIRED
HUMAN_INPUT_RECEIVED

ASSESSMENT_STARTED
DATA_QUALITY_ASSESSED
HYPOTHESIS_FORMED
HYPOTHESIS_VALIDATED
SOLUTION_PROPOSED

APPROVAL_REQUIRED
SOLUTION_APPROVED
SOLUTION_REJECTED

IMPLEMENTATION_STARTED
COMPONENT_BUILD_STARTED
COMPONENT_BUILD_COMPLETED
TEST_STARTED
TEST_COMPLETED

DEPLOYMENT_READY
SOLUTION_STARTED
SOLUTION_COMPLETED

WARNING
ERROR
```

------------------------------------------------------------------------

# 40. Agent Simulation

For the MVP, do not implement a fully autonomous LLM agent system.

Create an **Agent Simulation Engine**.

The simulation should behave like an agent.

For example:

``` text
DiscoveryAgent

1. Start discovery
2. Scan environment
3. Detect ServiceNow
4. Test reachability
5. Request credentials
6. Pause
7. Receive credentials
8. Continue
9. Discover SAP
10. Discover SQL Server
11. Discover License DB
12. Complete discovery
```

The important part is the event sequence and state transitions.

The eventual real agent runtime can replace the simulator.

------------------------------------------------------------------------

# 41. Replaceability

Architect the simulation so that later:

``` text
                 Event Interface
                       ▲
                       │
          ┌────────────┴────────────┐
          │                         │
   Simulation Engine          Real Agent Runtime
          │                         │
          └────────────┬────────────┘
                       ▼
                      UI
```

The frontend should not care whether an event came from:

-   A simulator
-   An LLM agent
-   A deterministic worker
-   A real connector
-   A future orchestration engine

This is one of the most important architectural goals for V1.

------------------------------------------------------------------------

# 42. Mock Client Environment

Use one fictional client environment.

Example:

``` text
Client: ACME Enterprise

Systems:

ServiceNow
SAP
SQL Server
License Management System
Legacy Application Registry
```

The simulated environment should contain enough data to make the demo
believable.

------------------------------------------------------------------------

# 43. Initial Methodologies

Use three methodologies in the demo:

## Ticket Anomaly Detection

Inputs:

-   Ticket history
-   Priority
-   Assignment groups
-   Resolution time
-   Categories
-   Reassignment history

Outputs:

-   Anomalous tickets
-   Anomaly patterns
-   Risk categories
-   Trends
-   Root patterns
-   Interactive drill-down

------------------------------------------------------------------------

## License Optimization

Inputs:

-   License entitlements
-   Assignments
-   Usage
-   Costs

Outputs:

-   Unused licenses
-   Underutilized licenses
-   Potential optimization
-   Cost impact

The implementation can initially be simplified.

------------------------------------------------------------------------

## Application Portfolio Rationalization

Inputs:

-   Application inventory
-   Usage
-   Ownership
-   Cost
-   Dependencies
-   Business metadata

Outputs:

-   Candidate applications
-   Rationalization categories
-   Dependency analysis
-   Cost/usage insights

Again, this can initially be simulated.

------------------------------------------------------------------------

# 44. V1 Recommendation

Do not fully implement three complex analytical products.

Instead:

``` text
Ticket Anomaly Detection
        ↓
Fully polished end-to-end dashboard

License Optimization
        ↓
Functional simulated solution

Application Portfolio Rationalization
        ↓
Functional simulated solution
```

This gives the demo breadth without sacrificing quality.

------------------------------------------------------------------------

# 45. Data Strategy for Demo

Use deterministic mock data.

Avoid random data that changes on every run unless randomness is
explicitly useful.

Deterministic data makes:

-   Testing easier
-   Screenshots reproducible
-   Demo behavior predictable
-   Drill-down relationships reliable
-   Agent simulation easier to debug

The mock data should contain deliberate patterns.

For example:

``` text
Ticket population
    ↓
Normal tickets
    ↓
Several intentionally anomalous clusters
```

Then the analytical result can be deterministic.

------------------------------------------------------------------------

# 46. Simulation Timing

The system should progress progressively rather than instantly.

Example:

``` text
Scanning...
      1 sec

ServiceNow detected
      0.8 sec

Testing reachability...
      1 sec

Reachability confirmed
      0.7 sec

Inspecting schema...
      1.5 sec
```

The exact timing is not important.

The purpose is to create the perception of an active system.

However:

-   Do not make the demo unnecessarily slow.
-   Provide a sensible fast/demo mode if useful.
-   Avoid fake animations that do not correspond to state changes.

------------------------------------------------------------------------

# 47. UI Design Direction

The interface should be:

-   Minimal
-   Beautiful
-   Technical
-   Premium
-   Calm
-   Information-dense without being cluttered
-   Dark/light theme can be evaluated during implementation
-   Strong typography
-   Subtle animation
-   Clear hierarchy

Avoid:

-   Excessive gradients
-   Generic "AI" glowing effects
-   Robot/agent illustrations
-   Excessive cards
-   Fake futuristic styling
-   Too many colors
-   Excessive motion

The visual language should communicate:

> serious analytical infrastructure

rather than:

> AI toy / chatbot.

------------------------------------------------------------------------

# 48. The Seed Screen

The first screen can be intentionally sparse.

Concept:

``` text
                         SYSTEMS

                  Plant the methodology.

       Core           Adaptation           Protection
       ┌───┐          ┌─────┐              ┌───┐
       │ + │          │  +  │              │ + │
       └───┘          └─────┘              └───┘

                 [ Plant Seed ]
```

After upload:

``` text
Core          ✓
Adaptation    ✓
Protection    ✓

              [ Initialize ]
```

The actual visual implementation can be determined later.

------------------------------------------------------------------------

# 49. Main Workspace

Conceptual structure:

``` text
┌───────────────────────────────────────────────────────────────┐
│ SYSTEMS                                      DISCOVERY ●       │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│              INIT ─ DISCOVERY ─ ASSESS ─ BUILD ─ DEPLOY       │
│                          ●                                    │
│                                                               │
├──────────────────────────────────┬────────────────────────────┤
│                                  │                            │
│        ENVIRONMENT               │        ACTIVITY            │
│                                  │                            │
│      ServiceNow                 │  Detecting ServiceNow      │
│           │                      │  Testing endpoint          │
│      ┌────┴────┐                 │  API identified            │
│      SAP     SQL Server          │  Credentials required      │
│                                  │                            │
├──────────────────────────────────┴────────────────────────────┤
│                                                               │
│                   HUMAN INPUT / STATUS                        │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

This is conceptual, not a final UI requirement.

------------------------------------------------------------------------

# 50. Discovery Visualization

The environment visualization can be graph-like.

Nodes:

``` text
Client
System
Service
API
Database
Dataset
```

Edges:

``` text
contains
connects to
provides
depends on
```

As the agent discovers resources, nodes become visible.

Potential statuses:

``` text
discovering
detected
testing
validated
requires-input
connected
error
```

------------------------------------------------------------------------

# 51. Assessment Visualization

After Discovery, the environment graph may transition into a
methodology/solution view.

Conceptually:

``` text
Discovered Data
      │
      ├───────────────┐
      ▼               ▼
Ticket Method     License Method
      │               │
      ▼               ▼
High Feasibility  Medium Feasibility
      │               │
      ▼               ▼
Approved?         Needs data
```

This is where the system demonstrates that it is **reasoning about what
can actually be done**.

------------------------------------------------------------------------

# 52. Implementation Visualization

During build:

``` text
Data Source
     ↓
Ingestion
     ↓
Normalization
     ↓
Analysis
     ↓
API
     ↓
Dashboard
```

Nodes can progress through:

``` text
Pending
Building
Testing
Validated
Complete
```

------------------------------------------------------------------------

# 53. Deployment/Run

At deployment/run:

``` text
Implemented Solutions

┌───────────────────────────────────────────┐
│ Ticket Anomaly Detection                  │
│ Ready                                     │
│ [ Run ]                                   │
└───────────────────────────────────────────┘

┌───────────────────────────────────────────┐
│ License Optimization                      │
│ Ready                                     │
│ [ Run ]                                   │
└───────────────────────────────────────────┘
```

Clicking Run should transition to the corresponding analytical
dashboard.

------------------------------------------------------------------------

# 54. Dashboard: Ticket Anomaly Detection

Potential top-level metrics:

``` text
Total Tickets
Anomalies
Average Resolution Time
Anomaly Rate
```

Potential charts:

``` text
Ticket volume over time
Anomaly trend
Anomaly category distribution
Anomaly by priority
Anomaly by assignment group
Resolution time distribution
Top anomaly patterns
```

Every meaningful chart should be interactive.

------------------------------------------------------------------------

# 55. Dashboard Drill-Down

Example:

``` text
Anomaly Trend
       ↓ click month
June
       ↓
Anomaly Categories
       ↓ click category
Reassignment
       ↓
Assignment Groups
       ↓ click group
Network Operations
       ↓
Ticket Clusters
       ↓
Underlying Tickets
       ↓
Evidence
```

The dashboard should maintain a breadcrumb:

``` text
All Tickets
 / June 2026
 / Reassignment
 / Network Operations
 / Cluster 27
```

The user should be able to go backward.

------------------------------------------------------------------------

# 56. Drill-Down Data Model

The data model should support relationships such as:

``` text
Dashboard Metric
      ↓
Chart Point
      ↓
Filter Context
      ↓
Entity
      ↓
Record
      ↓
Evidence
```

Do not implement drill-down merely as hardcoded UI navigation.

The eventual architecture should allow different methodologies to define
different analytical hierarchies.

------------------------------------------------------------------------

# 57. Dashboard Evidence Panel

A detail panel can expose:

``` text
Finding

Repeated reassignment anomaly

Observed:
7.2 assignments

Baseline:
2.1 assignments

Deviation:
+242%

Comparable population:
1,284 tickets

Evidence:
- Historical ticket data
- Assignment history
- Resolution data

Methodology:
Ticket Anomaly Detection

Validation:
Statistical baseline
ML anomaly model
```

Again, the numbers can be deterministic mock values.

------------------------------------------------------------------------

# 58. Backend State Model

Possible high-level state:

``` text
System
│
├── seed
│
├── lifecycle
│
├── environment
│
├── assessments
│
├── solutions
│
├── approvals
│
├── implementations
│
├── runtime
│
└── events
```

Example lifecycle:

``` text
INITIALIZED
DISCOVERING
DISCOVERY_BLOCKED
DISCOVERY_COMPLETE
ASSESSING
AWAITING_APPROVAL
IMPLEMENTING
IMPLEMENTATION_COMPLETE
READY_TO_RUN
RUNNING
COMPLETED
```

------------------------------------------------------------------------

# 59. State Machine

A formal state machine is preferable to scattered boolean flags.

Example:

``` text
INIT
 ↓
DISCOVERY
 ↓
ASSESSMENT
 ↓
AWAITING_APPROVAL
 ↓
IMPLEMENTATION
 ↓
READY
 ↓
RUNNING
 ↓
COMPLETED
```

With human-intervention substates:

``` text
DISCOVERY
   ↓
WAITING_FOR_HUMAN
   ↓
DISCOVERY
```

This will make the simulator and UI easier to reason about.

------------------------------------------------------------------------

# 60. Error Handling

The demo should include meaningful failure states.

Examples:

``` text
Endpoint unreachable
Schema mismatch
Insufficient data
Credential missing
Hypothesis rejected
Implementation test failed
```

The system should not simply pretend everything always works.

A believable autonomous system needs to demonstrate that it can
encounter uncertainty and recover or escalate.

For example:

``` text
ServiceNow API reachable
        ↓
Schema inspection
        ↓
Required field missing
        ↓
Assessment degraded
        ↓
Human input requested
```

------------------------------------------------------------------------

# 61. Human Decision vs Error

Do not confuse these.

### Error

Something went wrong technically.

Example:

``` text
Connection failed
```

### Human decision

The system has multiple legitimate choices.

Example:

``` text
Two authoritative data sources detected.
Which one should be used?
```

### Insufficient evidence

The system cannot responsibly conclude something.

Example:

``` text
Application retirement cannot be recommended
because ownership information is missing.
```

These should have different UI states.

------------------------------------------------------------------------

# 62. Security Simulation

For V1, security can be simulated.

However, the demo should conceptually show:

``` text
Agent requests action
        ↓
Protection Layer evaluates
        ↓
Allowed
OR
Human approval
OR
Denied
```

This is enough to demonstrate the architectural principle.

Do not build real credential storage or enterprise security
infrastructure for V1 unless required by implementation constraints.

------------------------------------------------------------------------

# 63. What Should Be Real vs Simulated

## Real

-   UI
-   State machine
-   Event streaming
-   File upload
-   Seed parsing/validation
-   Human interaction
-   Solution lifecycle
-   Dashboard rendering
-   Chart interaction
-   Drill-down
-   Backend/frontend communication
-   Deterministic data model

## Simulated

-   Enterprise discovery
-   ServiceNow connection
-   SAP connection
-   Network scanning
-   Credential validation
-   Agent reasoning
-   Code generation
-   ML training
-   Production deployment

This boundary should remain clear in the architecture.

------------------------------------------------------------------------

# 64. Suggested Demo Backend

Initial architecture:

``` text
Vue.js
   │
   │ SSE/WebSocket
   ▼
FastAPI
   │
   ├── Lifecycle Manager
   │
   ├── Event Manager
   │
   ├── Simulation Engine
   │
   ├── State Manager
   │
   ├── Seed Loader
   │
   └── Mock Data
```

Potentially:

``` text
SQLite
```

for persistence if useful.

Do not introduce Kafka, Redis, Kubernetes, or other distributed
infrastructure simply because the eventual production system might use
them.

The demo should remain simple.

------------------------------------------------------------------------

# 65. Why Event Streaming Matters

The system should feel alive.

A traditional request/response flow:

``` text
POST /discover
     ↓
wait 30 seconds
     ↓
return everything
```

does not convey the intended experience.

Instead:

``` text
Start discovery
     ↓
Event stream

DISCOVERY_STARTED
RESOURCE_DISCOVERED
RESOURCE_VALIDATED
HUMAN_INPUT_REQUIRED
HUMAN_INPUT_RECEIVED
RESOURCE_DISCOVERED
...
DISCOVERY_COMPLETED
```

This gives the UI a continuous stream of system activity.

SSE may be sufficient for V1.

WebSockets can be used if bidirectional communication becomes useful.

------------------------------------------------------------------------

# 66. Seed File Format

For V1, Markdown is preferred because it is:

-   Human-readable
-   Easy to edit
-   Easy to demo
-   Easy to version-control

Potential structure:

``` markdown
# Methodology

## Purpose

...

## Principles

...

## Required Evidence

...

## Analysis Process

...

## Validation Rules

...
```

The exact structure should be determined during implementation planning.

Do not over-engineer the knowledge representation before understanding
what the demo actually needs.

------------------------------------------------------------------------

# 67. Seed Loading

When the user uploads the Seed:

``` text
Upload
 ↓
Validate
 ↓
Parse
 ↓
Register
 ↓
Initialize System State
 ↓
Start Lifecycle
```

The system should show that the Seed has actually been loaded.

Potential UI:

``` text
CORE
✓ Loaded
✓ Parsed

ADAPTATION
✓ Loaded
✓ Parsed

PROTECTION
✓ Loaded
✓ Parsed

SYSTEM READY
```

------------------------------------------------------------------------

# 68. Demo Script

The demo should be possible to run as a controlled narrative.

Recommended sequence:

### Step 1

Upload Seed.

### Step 2

Plant Seed.

### Step 3

Discovery starts.

### Step 4

ServiceNow is detected.

### Step 5

ServiceNow reachability is tested.

### Step 6

Credentials are requested.

### Step 7

Admin provides credentials.

### Step 8

Discovery continues.

### Step 9

SAP, SQL Server and other sources are discovered.

### Step 10

Discovery completes.

### Step 11

System evaluates methodologies.

### Step 12

Assessment reports appear.

### Step 13

Admin reviews and approves Ticket Anomaly Detection.

### Step 14

Implementation begins.

### Step 15

Backend, analytical engine and dashboard are "built".

### Step 16

Tests run.

### Step 17

Solution becomes ready.

### Step 18

Admin runs solution.

### Step 19

Interactive dashboard opens.

### Step 20

User drills down from an anomaly to evidence.

This should be a smooth, impressive end-to-end story.

------------------------------------------------------------------------

# 69. What the Demo Should Communicate

By the end, a viewer should understand:

### The system has methodology.

It is not simply prompting an LLM.

### The system understands environments.

It discovers and maps client systems.

### The system adapts.

The same methodology can operate against different environments.

### The system is governed.

Agents cannot arbitrarily do anything.

### Humans remain decision authorities.

Humans intervene at meaningful boundaries.

### Conclusions are evidence-driven.

The system can trace findings back to data.

### Solutions are constructed.

The system moves beyond analysis into implementation.

### The result is useful.

The final product is an interactive analytical application.

------------------------------------------------------------------------

# 70. What the Project Is NOT

Do not turn V1 into:

-   A generic chatbot
-   A ChatGPT clone
-   A generic RAG application
-   A static BI dashboard
-   A CRUD application
-   A collection of fake AI agents
-   A generic LangChain demo
-   A dashboard with random generated logs
-   A complicated microservice architecture
-   A real enterprise integration platform

The core concept is:

> **Methodology-driven autonomous analytical execution.**

------------------------------------------------------------------------

# 71. Architecture Principle: Methodology Over Model

The LLM is not the product.

The methodology is the product.

An LLM may help:

-   Interpret ambiguous data
-   Map concepts
-   Generate hypotheses
-   Choose analytical methods
-   Generate implementation code
-   Explain findings

But the system should maintain deterministic structure around it:

``` text
Methodology
     ↓
Constraints
     ↓
Data
     ↓
Analysis
     ↓
Evidence
     ↓
Conclusion
```

The LLM should operate within that system.

------------------------------------------------------------------------

# 72. Architecture Principle: Evidence Over Assertions

The system should not allow:

``` text
LLM says X
      ↓
X becomes truth
```

Instead:

``` text
Hypothesis
     ↓
Required evidence
     ↓
Data acquisition
     ↓
Validation
     ↓
Analysis
     ↓
Conclusion
```

This should influence the System State model.

------------------------------------------------------------------------

# 73. Architecture Principle: State Over Conversations

Agents should not maintain the entire system state only inside their
context window.

Instead:

``` text
System State
     ▲
     │
 Agent reads
     │
 Agent performs work
     │
 Agent writes
     ▼
System State
```

This provides:

-   Recovery
-   Auditing
-   Observability
-   Reproducibility
-   Multi-agent coordination later

------------------------------------------------------------------------

# 74. Architecture Principle: Human Escalation

Humans should not have to approve every action.

Instead:

``` text
Agent knows what to do
        ↓
Proceed

Agent lacks information
        ↓
Ask human

Agent reaches high-impact action
        ↓
Require approval

Policy prohibits action
        ↓
Deny
```

This gives the system meaningful autonomy.

------------------------------------------------------------------------

# 75. Architecture Principle: Progressive Replacement

The demo should be designed so that each simulated subsystem can later
be replaced.

Example:

``` text
Mock Discovery
     ↓
Real Discovery Agent

Mock ServiceNow
     ↓
Real ServiceNow Connector

Mock Assessment
     ↓
Real Methodology Engine

Mock Build
     ↓
Real Code-generation workflow

Mock Run
     ↓
Real Deployment/runtime
```

The UI should not need to be rewritten when this happens.

------------------------------------------------------------------------

# 76. V1 Scope

## Must Have

-   Seed upload
-   Seed validation
-   Three-layer Seed
-   Lifecycle state machine
-   Simulated Discovery
-   Mock client environment
-   Environment registry
-   Live event stream
-   Human input
-   Assessment
-   Feasibility
-   Solution proposal
-   Approval
-   Implementation simulation
-   Run flow
-   Interactive analytics dashboard
-   Drill-down
-   Evidence view

## Nice to Have

-   Persistent local state
-   Pause/resume
-   Restart from state
-   Failure/retry
-   Multiple solution runs
-   Rich environment graph
-   Detailed methodology viewer

## Explicitly Out of Scope

-   Evolution phase
-   Real ServiceNow integration
-   Real SAP integration
-   Real network scanning
-   Production credentials
-   Real cloud deployment
-   Real autonomous infrastructure modification
-   Full enterprise authentication
-   Multi-client production deployment
-   Complex distributed infrastructure

------------------------------------------------------------------------

# 77. Recommended Implementation Order

Do not start by building the dashboard.

Recommended sequence:

``` text
1. Define domain/state model
2. Define lifecycle state machine
3. Define event schema
4. Define Seed format
5. Implement Seed loader
6. Implement simulation engine
7. Implement human-input mechanism
8. Implement SSE/WebSocket event stream
9. Implement lifecycle UI
10. Implement Discovery visualization
11. Implement Assessment/report
12. Implement approval flow
13. Implement Implementation simulation
14. Implement Run lifecycle
15. Build analytical data model
16. Build interactive dashboard
17. Implement drill-down
18. Implement evidence views
19. Polish visual design
20. Add failure/recovery paths
```

This order prevents the UI from becoming tightly coupled to arbitrary
backend behavior.

------------------------------------------------------------------------

# 78. Questions Claude Code Should Answer Before Coding

Before substantial implementation, Claude Code should analyze and
propose answers for:

### Architecture

-   What should the repository structure be?
-   What belongs in frontend vs backend?
-   What is the domain model?
-   What is the state machine?
-   How should events be represented?

### Seed

-   What should the three Markdown files contain?
-   How should they be parsed?
-   Which information should be structured vs free-form?

### Agent Simulation

-   How should deterministic agent workflows be represented?
-   How should pauses for human input work?
-   How should simulation timing work?
-   How should failures/retries work?

### Backend

-   FastAPI structure?
-   State management?
-   SSE vs WebSocket?
-   Persistence?
-   Mock environment representation?

### Frontend

-   Vue architecture?
-   State management?
-   Visualization architecture?
-   Lifecycle rendering?
-   Human-input components?
-   Dashboard routing?

### Analytics

-   How should analytical entities be modeled?
-   How should drill-down relationships work?
-   How should cross-filtering work?
-   How should evidence be linked to findings?

### Future Evolution

-   How can simulated agents later be replaced by real agents?
-   How can real connectors later replace mocks?
-   How can methodologies be added without rewriting the engine?

------------------------------------------------------------------------

# 79. Important Implementation Constraint

Do not over-engineer the demo.

There is a temptation to immediately introduce:

``` text
Kafka
Redis
PostgreSQL
Kubernetes
Multiple microservices
Vector databases
LLM orchestration frameworks
Agent frameworks
Cloud infrastructure
```

Do not do this unless there is a concrete requirement.

The demo should prove the **concept and interaction model** first.

A simple architecture such as:

``` text
Vue
  ↓
FastAPI
  ↓
State + Simulation
  ↓
Mock Data
```

is completely acceptable.

Architectural boundaries matter more than infrastructure complexity.

------------------------------------------------------------------------

# 80. Potential Future Architecture

The eventual production system may evolve toward:

``` text
                         ┌───────────────────────┐
                         │     PROTECTION        │
                         │                       │
                         │ Policy Engine         │
                         │ Identity              │
                         │ Authorization         │
                         │ Audit                 │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │    AGENT RUNTIME      │
                         │                       │
                         │ Discovery             │
                         │ Assessment            │
                         │ Analysis              │
                         │ Builder               │
                         │ Validator             │
                         │ Operator              │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     SYSTEM STATE      │
                         │                       │
                         │ Environment           │
                         │ Evidence              │
                         │ Hypotheses            │
                         │ Solutions             │
                         │ Decisions             │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │        CORE           │
                         │                       │
                         │ Methodologies         │
                         │ Knowledge             │
                         │ Methods               │
                         │ Rules                 │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │      ADAPTATION       │
                         │                       │
                         │ Connectors            │
                         │ Discovery             │
                         │ Mapping               │
                         │ Data acquisition      │
                         └───────────┬───────────┘
                                     │
                                     ▼
                              CLIENT SYSTEMS
```

V1 does not need to implement this full architecture.

------------------------------------------------------------------------

# 81. Final Product Definition

The V1 demo should be understood as:

> **A visually polished simulation of a methodology-driven autonomous
> enterprise analytical system that can be planted into a simulated
> client environment, discover available systems and data, assess
> analytical feasibility, escalate decisions to a human, build approved
> solutions, and expose the resulting analysis through interactive
> drill-down dashboards.**

The central flow is:

``` text
          PLANT
            ↓
          DISCOVER
            ↓
          UNDERSTAND
            ↓
          ASSESS
            ↓
          DECIDE
            ↓
          BUILD
            ↓
          RUN
            ↓
          EXPLORE
            ↓
          TRACE TO EVIDENCE
```

The three persistent layers are:

``` text
CORE
"How should the problem be solved?"

ADAPTATION
"How does this methodology apply to this environment?"

PROTECTION
"What is the system allowed to do?"
```

The lifecycle is:

``` text
INIT
→ DISCOVERY
→ ASSESSMENT
→ IMPLEMENTATION
→ DEPLOYMENT/RUN
→ ANALYTICS
```

And the key design philosophy is:

> **The system should appear autonomous, but never uncontrolled;
> analytical, but never a black box; and intelligent, but grounded in an
> explicit methodology and evidence.**

------------------------------------------------------------------------

# 82. Immediate Next Step

Claude Code should **not immediately begin writing the complete
application**.

First:

1.  Read and understand this document.
2.  Identify the core domain entities.
3.  Propose the System State model.
4.  Propose the lifecycle state machine.
5.  Propose the event model.
6.  Propose the repository structure.
7.  Propose the Seed format.
8.  Propose the simulation architecture.
9.  Propose the frontend/backend boundary.
10. Propose how interactive analytics and drill-down should be modeled.
11. Identify architectural risks or ambiguities.
12. Present the proposed implementation plan for review.

Only after that planning step should implementation begin.

------------------------------------------------------------------------

# 83. Resolved Requirements (V1)

> **Status:** Agreed. Sections 1--82 remain the vision document and
> describe the eventual system. This section is the binding specification
> for V1 and takes precedence wherever the two disagree.

## 83.1 Intelligence model

**No LLM anywhere in V1.**

There is no API key, no network dependency, and no inference at any point
in the lifecycle. The system runs fully offline and produces a
byte-identical run every time.

What §40 calls the Agent Simulation Engine is a deterministic scripted
workflow runner that emits events. It is not an agent and does not
pretend to reason.

§71's LLM seams (concept mapping, hypothesis generation, finding
explanation) are recorded as future work. They are not built.

## 83.2 Seed

The repository ships three genuine seed files:

``` text
core.md
adaptation.md
protection.md
```

These contain real methodology content and are themselves a deliverable
--- they are what you show someone who asks "what is actually in the
seed?".

At INIT, the presenter supplies all three. The loader:

``` text
Validate all three present and parseable as Markdown
        ↓
Parse heading structure
        ↓
Display a real "knowledge loaded" summary from those headings
        ↓
Initialize System State
```

**Seed content does not branch system behavior in V1.** The heading
summary shown to the user is real; the methodologies, feasibility results
and policy rules are fixed. §2's seed-driven adaptation and §5's
knowledge compiler are deferred.

## 83.3 Analytics data

A committed generator module with a hardcoded RNG seed builds the ticket
dataset into memory at backend startup.

``` text
Generator (fixed seed)
        ↓
~184,000 tickets, in memory
        ↓
Planted anomaly clusters, labels and scores baked in
        ↓
Backend aggregates per filter context at request time
```

Consequences:

-   Nothing large enters version control.
-   §31's headline figures are the dataset's true counts, not decoration.
-   No statistics or ML run at request time --- anomaly labels and scores
    are produced by the generator.
-   Any cross-filter combination works, because aggregates are computed
    from records rather than read from precomputed fixtures. This
    resolves the conflict between §34 and a fixture-based approach.
-   Drill-down terminates at genuine records, so §35's trace-to-evidence
    is real rather than staged.

## 83.4 Technical stack

``` text
Frontend      Vue 3 + TypeScript + Pinia + Vite
Backend       FastAPI
Transport     SSE
Charts        Apache ECharts
Graphs        Hand-built SVG (discovery graph, build pipeline)
Theme         Light and dark, both from design tokens
State         In-memory, single run, explicit Reset
Packaging     Single-command launcher
```

Docker is **not** part of V1, superseding §29.

## 83.5 Mock environment

The ACME environment contains exactly the five systems named in §42:

``` text
ServiceNow
SAP
SQL Server
License Management System
Legacy Application Registry
```

§19's "7 Systems / 14 Data Sources / 31 Relevant Datasets" is
**discarded**. The discovery-completion summary reports the environment's
actual totals.

## 83.6 Demo narrative

The main run contains two interruptions:

1.  The scripted credential request of §68 (human input).
2.  One endpoint timeout that the runner retries and recovers from
    (technical error).

The Implementation phase shows the pipeline graph with nodes progressing
Pending → Building → Testing → Complete. The test stage expands into a
detailed result view --- named test cases, pass/fail, timings. **No
generated source code is displayed**, because none is generated.

All three solutions reach runnable dashboards:

``` text
Ticket Anomaly Detection        Deep, fully polished
License Optimization            3-4 interactive charts, one drill-down path
Application Portfolio Rat.      3-4 interactive charts, one drill-down path
```

License Optimization retains §20's partial feasibility (incomplete cost
data) as a **stated limitation on an approvable solution**, not as a
blocker. Feasibility is graded, not binary.

## 83.7 Protection layer surface

Policy decisions are first-class events in the activity stream:

``` text
Tool request: read ServiceNow incident API   →  ALLOWED   (rule R-04)
Tool request: create analytical dataset      →  ALLOWED   (rule R-11)
Tool request: deploy production service      →  ESCALATED (rule R-19)
Tool request: delete source records          →  DENIED    (rule R-02)
```

In addition, a dedicated Protection panel exposes:

-   The active rule set
-   Running counts of allowed / denied / escalated requests
-   A filterable audit log

This keeps the layer visibly cross-cutting per §9, rather than appearing
only when it interrupts.

## 83.8 Operator controls

Speed (1x / 2x / instant), skip-phase and reset exist, reachable by
keyboard shortcut only. The audience sees no transport bar.

## 83.9 Explicitly deferred

These appear in §§1--82 as aspiration and are **not** V1 work:

``` text
Seed content driving system behavior
Knowledge compilation into structured representations
Any LLM involvement
Evolution phase
Real connectors of any kind
Persistence, pause/resume, resume-after-restart
Docker packaging
Failure-injection mode beyond the single scripted timeout
Generated source-code artifacts
```

------------------------------------------------------------------------

# 84. Stakeholder Rework --- Alex Prigojine Session (2026-09-23)

> **Status:** Incorporated into `decisions.md` §7, `requirements.md` and
> `implementation-plan.md` (Phase R, M11 to M19). Every question it
> raised was answered on the same day. The Life pane is **Option B**
> (§84.3, D-17). Visual continuity with Agent One is deferred.

## 84.1 What the session asked for

Feedback received after M10 was built. It asked to reorganise the
existing interface into two views, **Seeding** (build time) and **Life**
(run time), under new names, without removing any functionality.

1.  **Renaming**, as display copy only. Solution becomes Agent Component
    (also called "Agent One VW"). Systems, and the methodology label,
    become Seed. Runtime becomes Life. Initiation becomes Planting, which
    should also show the tech stack being planted into. Feasibility
    becomes Potential: high means strong value, partial means needs
    deeper modelling, and a "routing problem" flag is possible.
2.  **Two panes** with a top toggle for both, left only or right only.
    Seeding on the left: Planting, Discovery, Assessment and
    Implementation, with the activity and protection panels. Life on the
    right: empty until the build completes, then the live system.
3.  **A growth tree** replaces the progress bar in the Seeding pane. It
    grows segment by segment, and each API or gen-AI call triggers a
    watering step.
4.  **Run / Clean up: close the seeding phase**, after Implementation.
    Merge leftover MD files, clear scratch disk space, upgrade APIs to
    their final versions, then collapse Seeding and maximise Life.
5.  **Life pane behaviour:** the model actively running, collecting
    data, dashboards, and self-improving, consistent with the earlier
    Agent One demo and reusing its visual style.

## 84.2 How it was incorporated

| Item | Ruling | Milestone | Tag |
| ---- | ------ | --------- | --- |
| 1, renames | D-11: display-only; identifiers keep their names | M11 | RENAME |
| 1, Feasibility | D-12: Potential semantics and the routing-problem flag | M12 audit, M13 copy, M16 flag | RENAME, NEW |
| 1, Planting stack | D-13: show the declared stack, marked unverified | M15 | NEW |
| 2, panes | D-14: Seeding and Life, both mounted | M14 | MOVE |
| 3, tree | D-15: replaces the lifecycle strip; protection decisions water it | M17 | NEW |
| 4, closing | D-16: a new lifecycle state, a confirmation, three gated operations | M18 | NEW |
| 5, Life | D-17: time-revealed operation, Option B of §84.3 | M19 | NEW |

**What it reworks among built milestones.** M4's single workspace
becomes the Seeding pane. M7's grade is presented as Potential and gains
the flag. M8's transition from Implementation to Run gains the closing
step. M3 and M10 are relabelled and relocated without functional change.
No requirement was deleted. Four were superseded with successors (A-3 to
A-6).

**Two items were not pure relabelling,** despite the feedback's framing.
The routing-problem flag is a new state, and the clean-up action is a
new lifecycle state. Both are scheduled as NEW milestones after the
renames and the move, not folded into them.

**Two items were adjusted to fit fixed requirements.** The tree cannot
be watered by gen-AI calls, because none exist (NFR-D1). It is watered
by the tool requests the protection engine evaluates, which are this
system's API calls. The clean-up's three operations are simulated; none
touches a disk, a file or the network, and the seed files are never
merged into anything.

**Follow-up questions, all answered on 2026-09-23:**

- **Agent One VW (OQ-8)** is what comes out of a seed. It is the
  framework through which the methodology of building and maintaining
  the pipeline is implemented. See §84.4.
- **Methodology naming (OQ-9):** rename only if a seed-themed name is
  coherent. None was, so methodologies keep their name. Systems becomes
  Seed, as Alex proposed.
- **Routing problem (OQ-10):** evidence that exists but cannot reach the
  analysis. The wording for MEDIUM and LOW is accepted.
- **Progress bar (OQ-11):** the lifecycle strip.
- **Life (OQ-12):** Option B.
- **Agent One demo (OQ-13):** skipped for now. It is a separate demo
  that displays the detailed agentic steps of an analysis.

**Milestones renumbered.** The rework inserts M11 to M19 after M10. The
three milestones not yet built move from M11, M12 and M13 to M20, M21
and M22.

## 84.3 Life pane: the options considered (OQ-12)

> **Chosen, 2026-09-23: Option B**, without Option C's additions.
> Specified as D-17 and FR-LF4 to FR-LF11. Built at M19. The options are
> kept here as the record of what was weighed.

The feedback's least-specified item. Every option respects what V1
already fixes: no LLM (NFR-D1), determinism modulo timing (A-2), no
statistics at request time (FR-AN3), descriptor-driven dashboards (D-1)
and the motion budget (NFR-V4). The Evolution phase is excluded (§83.9,
`requirements.md` §4.1), so "self-improving" has to mean something
narrower than Evolution or be left out.

### Option A --- Life hosts what was built

**The viewer sees:** the Life pane opens on the list of Agent
Components. Run opens each one's dashboard inside the pane, and a short
Life activity stream records runs and evidence opened.

**Collection:** none shown. Dashboards present the generated dataset
whole. **Self-improvement:** none.

**Requirement cost:** none beyond FR-LF1 and FR-LF2. §4.1 is untouched.
**Build:** almost nothing past M14. M19 becomes an empty-state and copy
pass.

**Trade-off:** no risk and no new claims. But it delivers neither
"actively running" nor "self-improving". Life is the old Runtime stage
under a new name, which the stakeholder may reasonably read as the
feedback not having been acted on.

### Option B --- Time-revealed operation *(recommended)*

**The viewer sees:** each Agent Component collecting. A deterministic
clock advances through the last stretch of the generated data in steps,
for example one simulated week every few seconds. Each step is a
collection event: *"Collected 3,412 tickets from ServiceNow, week 34."*
KPIs and charts update as the cursor advances. At intervals a
recalibration event recomputes the baseline over the revealed window and
re-scores the findings: *"Resolution-stall baseline recalibrated on 12
more weeks: 41.2 h to 39.8 h. Three clusters newly confirmed, one
withdrawn."*

**How it stays honest.** The records already exist in the generator.
Collection reveals them, and the stream labels this as simulated
collection. The cursor is one more term in the filter context (FR-EV1),
so every dashboard follows it with no per-dashboard code (D-1). The
generator precomputes the baselines and scores for every step, which
keeps FR-AN3 intact. Every figure still comes from real rows, and fixed
steps keep A-2.

**Requirement cost:** an amendment to §4.1 stating that recalibrating
baselines within a run is not Evolution, where Evolution means new
methodologies, components or code. FR-AN4's "true counts" becomes "true
counts of the revealed data". New requirements for the cursor, collection
events and recalibration. Operator speed applies to the clock (FR-O3).

**Build:** medium. The generator produces per-step baselines and scores;
the arithmetic already exists for one step. The query engine gains the
cursor term. The Life stream and clock are new. The evidence panel names
the calibration a finding was made under.

**Trade-offs:** the most "alive" option that stays truthful, and it
reuses existing machinery. Two UX risks come with it. Findings could
shift under a viewer mid-drill; this is mitigated by freezing the cursor
while the viewer interacts with a dashboard and resuming it on return.
And a finding that changes between steps looks unstable unless the
evidence panel says which calibration step produced it.

### Option C --- Agent operations console

**The viewer sees:** Life as a console with one card per running Agent
Component. Each card shows its state (collecting, analysing or idle),
cycle count, records ingested, findings emitted and model version. A
version timeline per component, v1.0 to v1.1 to v1.2, carries a measured
quality figure: **precision and recall against the planted ground
truth.** The generator knows which records it planted as anomalous, so
these figures are arithmetic, not claims. Dashboards open from the
cards.

**Requirement cost:** needs Option B's mechanics underneath. Without
them, the cards animate over nothing, which NFR-V5 and the §70 non-goal
of "a collection of fake AI agents" both forbid. It needs the same §4.1
amendment as B and pushes further: model versions within a run sit
closer to Evolution. It also adds new interface surface to take through
M21.

**Build:** the largest. Option B, plus the console and the timeline.

**Trade-offs:** the most agent-flavoured, and possibly the closest to
the Agent One demo, if that demo was agent-centred (unknown; OQ-13). It
carries the highest risk of reading as fake agents, and the most new
interface to get through the design pass.

### Comparison

|                         | A --- Host what was built | B --- Time-revealed | C --- Operations console |
| ----------------------- | ------------------------- | ------------------- | ------------------------ |
| Actively running        | No                        | Yes                 | Yes                      |
| Collecting data         | No                        | Yes, revealed       | Yes, revealed            |
| Self-improving          | No                        | Recalibration       | Versions with measured precision |
| Every figure real       | Yes                       | Yes                 | Yes, only with B beneath |
| Amends §4.1             | No                        | Narrowly            | Further                  |
| Build size              | Small                     | Medium              | Large                    |
| Main risk               | Feedback reads as ignored | Findings shift mid-drill | Reads as fake agents |

### Recommendation

**Option B.** It is the smallest option that delivers both halves of
the request, running and improving, while every number stays traceable
to a row. Two parts of Option C are cheap and worth borrowing:

- **Precision and recall against planted ground truth** as the measure
  of each recalibration. It makes "self-improving" checkable rather than
  asserted.
- **A thin per-component status strip** at the top of the Life pane, in
  place of the full console, if the stakeholder wants the agent framing.

### On reusing the Agent One demo's style

**Deferred** at the stakeholder's direction (OQ-13). Agent One is a
separate demo that shows the detailed agentic steps of an analysis. None
of the three options depended on visual style, which lands in M21.

If continuity is revived, its **visual style** can be borrowed freely.
Its **step-by-step agentic narration** conflicts with FR-E9, which
forbids showing simulated internal reasoning, and with NFR-D1, unless
those are amended first (`decisions.md` §7.3).

## 84.4 Naming, as confirmed

The seed analogy names the **lifecycle**. The analysis keeps its own
names.

```
Seed                        the product; what is planted
 ├── Core · Adaptation · Protection      its three layers
 │    └── methodologies                   carried in Core; name unchanged
 │
Planting → Seeding          build time: Discovery, Assessment, Implementation
 │                          the growth tree shows it happening
 ▼
Agent One VW (ValueWise™)   what grows out of the Seed: the framework that
 │                          implements building and maintaining the pipeline
 └── Agent Components       its parts, one per approved methodology
 │
Life                        run time: Agent One VW collecting, recalibrating,
                            and answering questions through its dashboards
```

Seeding shows Agent One VW being **built**. Life shows it being
**maintained**. Together they make up the whole of what the name claims.

## 84.5 Phase R build log

One entry per Phase R milestone, in build order. Each records what
changed, the files touched, and what needs checking by hand. The commit
hash for each milestone is in the Status table of
`implementation-plan.md` §3.

### M11 · Display vocabulary

**What changed.** The screen now uses D-11's display vocabulary, apart
from Feasibility, which M12 and M13 handle.

- The product name is **Seed**: the page title, the seed screen's
  heading and the workspace identity.
- The phase labels are **Planting** and **Life**. The INIT stage's
  heading "Seed" is now "Planting".
- Display copy says **Agent Component** instead of "solution": the
  approval note on the human-input surface, the review drawer's approve
  button, the ready list's summary, and the stream messages from the
  assessment and implementation workflows. That includes the approval
  request's prompt ("3 of 3 Agent Components await a decision").
- The Implementation stage is headed **Building Agent One VW**, and its
  note calls each lane an Agent Component that is part of Agent One VW
  (FR-N6, in part).

One gap in the plan was closed. The activity stream's phase dividers
printed the raw phase value, so `INIT` and `RUNTIME` still reached the
screen. The labels now live in one table, `PHASE_LABELS` in
`design/presentation.ts`. The lifecycle strip and the stream dividers
both read it. M17's growth tree can read the same table.

**Deliberately unchanged.** Nothing in M11's load-bearing table was
touched: types, payload keys, `/api/solutions`, the `solution.*` event
types, the `'solution-approval'` request id, the `INIT` and `RUNTIME`
values, and the component file names. Also left alone:

- The `## Systems` heading in `seeds/adaptation.md`. It lists the
  client's systems, the same case as FR-N4, so no seed file changed.
- API error strings that mention a solution. The frontend never shows
  API error detail.
- The FastAPI title `Systems V1` (`backend/app/main.py`). It appears only
  on the `/docs` page.
- The raw lifecycle state in the header, such as `INITIALIZED`. It is a
  state value, not the phase label.
- "Workspace" in the ready-list note and on the dashboard's back button.
  M14 revisits both.
- The word "feasible" in the deployment request's purpose. M13 changes
  it.

**Files.** `frontend/index.html`; `views/SeedView.vue`,
`views/WorkspaceView.vue`; `components/LifecycleStrip.vue`,
`ActivityStream.vue`, `StagePane.vue`, `HumanRequest.vue`,
`ReviewDrawer.vue`, `ImplementationStage.vue`, `RuntimeStage.vue`;
`design/presentation.ts`; `backend/app/simulation/workflows/assessment.py`
and `implementation.py`.

**Gates.** `pytest` gives 417 passed with no test edited. Typecheck and
build pass. Live: the bundled seed was planted and the narrative run to
the end. All three approvals were made through the interface, one from
the review drawer and two from the cards, which exercises the
`'solution-approval'` id across the boundary (R-13). Run then opened the
Ticket Anomaly dashboard. The text on screen at the Life stage has no
"Solution", "Runtime", "Init" or product-name "Systems". Two words
remain, both expected: "feasibility", which M13 changes, and "systems"
as the count of client systems (FR-N4).

**Check by hand.**

1. Read the renamed copy in context, especially the Implementation
   stage's new note and the stream messages "Three Agent Components
   proposed…" and "Every Agent Component decided…".
2. Approve one component from the drawer and one from its card, and
   confirm both register.
3. Look at the lifecycle strip and the stream dividers in the light
   theme as well as the dark one.

**Carried forward to M14.** The live run confirmed that the lifecycle
passes from `IMPLEMENTATION_COMPLETE` to `READY_TO_RUN` in the same
beat. Until M18 adds closing, FR-W3's Both default at
`IMPLEMENTATION_COMPLETE` would only flash before Life only takes over.

### M12 · Feasibility references, classified

**What changed.** No code. The preliminary inventory in M12's block of
`implementation-plan.md` was re-verified against the code after M11 and
replaced. `feasib` occurs on 65 lines across `backend/app`,
`backend/tests`, `frontend/src` and `seeds/`. Each line is classified
once, as contract, logic, tested, silent failure, display or comment.
The grade references that do not contain the word are classified too.

The audit found five differences from the preliminary inventory:

- A new **tested** class. `test_assessment.py:201` asserts the regrade
  format "License Optimization PARTIAL to HIGH", so that format is kept.
- Two more contract items: `Approval.feasibility` in the store, and the
  `recommendation` key, whose non-empty value a test asserts.
- One more display string: the deployment request's purpose.
- `ReviewDrawer.vue` has no MEDIUM selector. MEDIUM inherits
  `--text-primary`, the same colour the card sets, so nothing needs
  fixing.
- The `Grade` type sits one line earlier than the plan said.

**Agreed for M13.** The display wording table, the four recommendation
drafts, and two findings:

- The seed's `## Feasibility` table becomes a Potential column showing
  the computed grades, HIGH, PARTIAL and MEDIUM, with limiting factors
  matching what assessment reports. Today it says "Yes, Yes, Partially",
  and its limiting factors are not the ones the computation finds.
- The deployment purpose drops "found feasible" and reads "…the Agent
  Components the assessment proposed."

**Files.** `docs/implementation-plan.md` (M12's inventory, and the
Status table, which also gains M11's hash) and this log.

**Gate.** Your review of the audit, given 2026-09-23. No code changed,
so the test suite and the build were not rerun.

**Check by hand.** Nothing further. M13 carries the colour check for
all four grades in both themes.

### M13 · Feasibility displayed as Potential

**What changed.** Exactly the display list M12 agreed, and nothing M12
classified as load-bearing.

- Labels. "Feasibility" becomes "Potential" on the card, in the drawer,
  in the ready list and in the assessment and discovery notes. The
  drawer's section "Why this is feasible" becomes "Why the value is
  within reach". The discovery verdict "Appears feasible" becomes
  "Evidence located".
- Stream messages. "{name}: potential {grade}", "approved …, on
  potential {grade}", "Potential moved:" and "No potential grade
  changed." The regrade format "{name} {from} to {to}" is kept, because
  `test_assessment.py:201` asserts it.
- The deployment request's purpose reads "…the Agent Components the
  assessment proposed."
- The four `RECOMMENDATIONS` values are rewritten to D-12's meanings. The
  keys are unchanged.
- `seeds/adaptation.md`: `## Feasibility` becomes `## Potential`, and
  the table now shows the computed grades, HIGH, PARTIAL and MEDIUM, with
  the limiting factors assessment reports. It previously said "Yes, Yes,
  Partially". The heading count FR-S5 displays is unchanged.
- One comment, `ReviewDrawer.vue:21`, which names the section title.

**Kept.** The `feasibility`, `appearsFeasible` and `recommendation`
keys, the `Grade` values, `grade_of`, the `[data-grade]` and
`data-feasible` selectors, the module name, and every other comment.

**Files.** `backend/app/knowledge/feasibility.py`,
`knowledge/solutions.py`, `simulation/workflows/assessment.py`;
`frontend/src/components/SolutionCard.vue`, `ReviewDrawer.vue`,
`RuntimeStage.vue`, `AssessmentStage.vue`, `EnvironmentStage.vue`;
`seeds/adaptation.md`.

**Gates.** `pytest` gives 417 passed with no test edited. Typecheck and
build pass. Live checks:

- Discovery's summary shows "Evidence located" for all three
  methodologies.
- The full event log of the run has 115 events and none mentions
  "feasib". The screen showed none at the discovery summary, at
  assessment with the drawer open, in the protection panel, or at the
  Life stage.
- For the silent-failure check (R-13), Application Portfolio
  Rationalization was driven to LOW by revising four fields to 40%, then
  restored to MEDIUM. All four grades were read with their computed
  colours on the card and in the drawer, in both themes. The two surfaces
  agree:
  - dark: HIGH `rgb(63,178,122)`, MEDIUM `rgb(232,235,240)`, PARTIAL
    `rgb(215,154,58)`, LOW `rgb(111,120,133)`;
  - light: HIGH `rgb(27,127,75)`, MEDIUM `rgb(18,21,27)`, PARTIAL
    `rgb(169,106,0)`, LOW `rgb(90,97,114)`.
- All three approvals were made through the interface. The drawer then
  reads "Approved on potential HIGH, under PR-053."

**Check by hand.**

1. Read the four recommendation texts in the drawer as content, as the
   plan asks. Note that the drawer's section title, "Why the value is
   within reach", also heads a LOW assessment, where the value is not
   within reach. M21 may want a grade-aware title.
2. Read the rewritten `## Potential` section of `seeds/adaptation.md`.
3. The discovery verdict for missing evidence ("Evidence missing",
   `data-feasible='false'`) is unchanged, but the scripted run never
   shows it. The selector was not edited.

### M14 · Seeding and Life panes

**What changed.** The workspace is now two panes under one top bar
(D-14). Both panes stay mounted for the whole run, and a layout change
only hides one (NFR-A7).

- **Top bar** (`App.vue`): the identity, the layout control (Both,
  Seeding, Life) and the raw lifecycle state. It replaces the full-screen
  dashboard overlay. `SeedView` still takes the whole screen until the
  seed is planted (FR-W7).
- **Seeding pane** (`WorkspaceView.vue`): unchanged in content. It keeps
  the lifecycle strip in its own bar, then the stage, the Activity and
  Protection rail, and the human-input surface. `StagePane` no longer
  shows the ready list. At `RUNTIME` it keeps the finished build on
  screen, as the record of what was built.
- **Life pane** (`views/LifeView.vue`, new): headed "Agent One VW
  (ValueWise™)". It shows an empty state until the build is done (FR-W4).
  From `RUNTIME` it shows the ready list (`RuntimeStage`, moved). Run
  opens the dashboard inside the pane, over the list, which stays
  mounted. The dashboard is still loaded lazily.
- **Layout rules** (`stores/layout.ts`, new):
  - The lifecycle sets the default: Seeding until
    `IMPLEMENTATION_COMPLETE`, Both at `IMPLEMENTATION_COMPLETE`, then
    Life at `READY_TO_RUN` and `RUNNING`.
  - A manual choice holds until the default next changes. I read "the
    next lifecycle-driven change" in FR-W3 that way, so a transition
    that keeps the same default does not override the choice.
  - A pending request turns Life only into Both, and disables Life only
    until it is answered (FR-W5).
  - A rehearsal link sets Life only (FR-W6). Closing the rehearsal hands
    the layout back to the lifecycle default. Before planting, the
    rehearsal is shown in the pane shell with the control disabled.
- **Copy.** The dashboard's back button reads "← Agent Components". The
  ready list's note says to return to this list, not the workspace
  (FR-L10).
- **One layout fix.** The dashboard was built for the full screen. In
  the Both layout it overflowed the pane's right edge, so its grid is now
  held to the pane's width.

**Files.** `frontend/src/App.vue`; `views/LifeView.vue` (new),
`views/WorkspaceView.vue`, `views/DashboardView.vue`;
`components/LayoutControl.vue` (new), `components/StagePane.vue`,
`components/RuntimeStage.vue`; `stores/layout.ts` (new). No backend
change.

**Gates.** `pytest` gives 417 passed with no test edited. Typecheck and
build pass. Live: one headless-Chrome session drove the full narrative
through the interface with 31 checks. 29 passed. The 2 failures are
described under "Found, pre-existing" below.

- The layout rules: all three layouts reachable; Life's empty state; a
  credential request forcing Seeding visible from Life only; Life only
  after the build; a rehearsal link opening Life only, both before and
  after planting; and a reload at `READY_TO_RUN` opening Life only.
- Neither pane was unmounted across the run, checked by element
  identity.
- The stream kept its scroll position across a hide and show (700 to
  700).
- A drilled dashboard kept its element, its URL filter and its figures
  across Seeding only and back.
- Re-verified from M3 to M10 (FR-W8):
  - M3: the seed screen summarises each dropped layer.
  - M5: DENY PR-033 and ESCALATE PR-053 appear in both the stream and
    the panel.
  - M6: one credential pause, answered through the form; the timeout
    recovered; and counts derived from the graph.
  - M7: a completeness edit moves a grade on the card, and reverting it
    moves it back.
  - M8: approval through the interface, the build, and Run.
  - M10: headline, then cluster, then ticket, with consistent figures,
    and the browser's Back popped exactly one step.
  - M9's backend is untouched, and its suite passes.

**Found, pre-existing.** Both were confirmed by running the same steps
against the M13 code with the M14 changes stashed. Neither was fixed,
because neither is in M14's rework list.

1. **After a live plant, the Planting stage shows no layer summary.**
   `StagePane` reads the layers from the snapshot, and planting from the
   interface never refreshes the snapshot. The summary appears only
   after a reload. M15 changes the Planting stage anyway, so it is the
   natural place to fix this. Waiting for a ruling.
2. **Back, then closing a running dashboard, leaves it open as a
   rehearsal.** The dashboard store's `popstate` handler sets
   `rehearsal` from the URL, so after the browser's Back the closed run
   falls through to a rehearsal of the same dashboard. A second click on
   back closes it. The fix belongs in `stores/dashboard.ts` (M10).
   Waiting for a ruling.

**Check by hand.**

1. The Both layout is cramped at 1600 px. The Seeding stage's column is
   about 320 px wide beside the rail, and the build lanes shrink. M21
   owns this, but judge whether it is acceptable until then.
2. The top bar still shows the raw lifecycle state, such as
   `READY_TO_RUN`, as before.
3. Before M18, Both at `IMPLEMENTATION_COMPLETE` lasts one beat, so in
   practice the layout goes from Seeding straight to Life.

### Follow-up · Potential grade colours (requested after M14)

**What changed.** MEDIUM used to render in plain text colour, so the
four grades did not read as one scale. Potential now has its own tokens
in `design/tokens.css`, forming an ordered scale: `--grade-high` (green),
`--grade-medium` (olive, new), `--grade-partial` (amber) and `--grade-low`
(grey). HIGH, PARTIAL and LOW alias the existing status tokens, so their
colours are unchanged. PARTIAL stays the caution colour and never the
fault colour (FR-H4).

- The card, the drawer and the Life ready list all read the grade
  tokens. The drawer gains the MEDIUM rule it never had. The ready list
  now colours its grade, where before it was plain text.
- The `[data-grade]` selectors are unchanged (M12's silent-failure
  class). Only the colours they apply changed, at your request.

**Contrast.** Measured against the card surface:

| Theme | HIGH | MEDIUM | PARTIAL | LOW |
| ----- | ---- | ------ | ------- | --- |
| Light | 5.0:1 | 4.6:1 (`#5f7f1a`) | 4.4:1 | 6.2:1 |
| Dark | 6.5:1 | 6.6:1 (`#8aab4c`) | 7.1:1 | 3.9:1 |

The dark MEDIUM was first tried as a brighter lime (9:1). It was toned
down so MEDIUM does not outshine HIGH.

**Files.** `frontend/src/design/tokens.css`,
`components/SolutionCard.vue`, `components/ReviewDrawer.vue`,
`components/RuntimeStage.vue`.

**Gates.** Typecheck and build pass. No backend change. Live: all three
surfaces show the four grade colours, read as computed styles, in both
themes.

**Check by hand.** In light theme, confirm that HIGH (dark green) and
MEDIUM (olive) are distinct enough at a glance. M21 tunes the palette.
