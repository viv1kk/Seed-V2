# Core

The Core is the methodology layer. It describes how a class of problem
should be thought about and solved, independent of any particular client
environment.

Nothing in this file names a system, a database, a table or a field.
Those belong to Adaptation. If a statement here cannot be reused at the
next client unchanged, it is in the wrong file.

## Purpose

The Core answers one question:

> How should this problem be thought about and solved?

It holds the concepts a conclusion is expressed in, the evidence a
conclusion requires, the procedure that assembles that evidence, the
statistical and machine-learning methods appropriate to each question,
and the conditions under which a conclusion must be withdrawn.

## Principles

### Evidence precedes conclusion

A conclusion is admissible only when every item of required evidence
named by its methodology is present, attributed to a source, and within
its freshness window. Absence of contradicting evidence is not evidence.

### Conclusions carry their assumptions

Every conclusion records the assumptions it rests on. An assumption that
cannot be stated cannot be reviewed, and a conclusion that cannot be
reviewed is an assertion.

### Baselines precede judgements

No observation is anomalous, excessive or underused in isolation. It is
so relative to a baseline computed over a stated window, on a stated
population, by a stated method.

### Methods are chosen by question, not by availability

The question determines the method. A method is justified by the shape of
the data and the decision the answer supports, never by the fact that it
is at hand.

### Uncertainty is reported, not absorbed

Where a quantity is estimated, the estimate is reported with its interval
and the sample it rests on. A point estimate presented alone overstates
what is known.

### Human authority at consequence

Where a conclusion leads to an irreversible act, the conclusion is
presented for decision rather than acted on. Autonomy ends where the
consequence becomes external.

## Concepts

These are the terms every methodology below is expressed in. A concept is
defined here once, and Adaptation is responsible for locating it in a
given environment.

| Concept | Definition |
| --- | --- |
| Entity | A thing the organisation manages and can be counted: an application, a licence, a ticket, a host, a person. |
| Owner | The accountable party for an entity, distinguished from the party that operates it. |
| Usage signal | A record that an entity was exercised, carrying an actor, a timestamp and a granularity. |
| Usage baseline | The expected level of a usage signal for an entity over a window, computed on a comparable population. |
| Entitlement | A contractual right to consume a quantity of something. |
| Assignment | An allocation of an entitlement to an actor, which may or may not be exercised. |
| Consumption | Exercised entitlement, evidenced by a usage signal rather than by an assignment. |
| Cost | A recurring or one-off monetary amount attributable to an entity, with a period and a currency. |
| Dependency | A directed relation stating that one entity requires another to function. |
| Criticality | The business consequence of an entity becoming unavailable, on a declared scale. |
| Anomaly | An observation whose deviation from its baseline exceeds a stated threshold by a stated method. |
| Evidence item | A retrieved fact with a source, a retrieval time and a field-level attribution. |
| Freshness window | The maximum age at which an evidence item may still support a conclusion. |
| Assumption | A statement taken as true without direct evidence, on which a conclusion depends. |
| Invalidator | An observation that, if true, withdraws a conclusion. |

## Evidence

### Sufficiency

Evidence is sufficient for a conclusion when all of the following hold.

1. Every required evidence class named by the methodology is present.
2. Each item is attributed to a named source and a named field.
3. Each item is within its freshness window.
4. Coverage of the population under analysis meets the stated minimum.
5. No invalidator for the conclusion is observed.

Where any of these fails, the methodology reports insufficient evidence
and names the missing class. It does not report a weaker conclusion.

### Attribution

An evidence item that cannot be traced to the field it came from is not
an evidence item. Aggregates carry the attribution of their inputs.

### Freshness

| Evidence class | Freshness window |
| --- | --- |
| Inventory and registry records | 30 days |
| Ownership and organisational records | 90 days |
| Usage signals | 7 days |
| Entitlement and contract records | 90 days |
| Cost records | one closed billing period |
| Ticket records | 24 hours |
| Dependency records | 30 days |

### Conflict

Where two sources disagree on the same fact, the conflict is surfaced
rather than resolved by precedence. Adaptation may declare one source
authoritative for a concept; where it has not, the disagreement is
escalated as an ambiguity for human resolution.

## Statistical methods

### Selecting a method

| Question | Method | Condition of use |
| --- | --- | --- |
| Is this value unusual for this population? | Robust z-score on the median and MAD | Population of 30 or more comparable observations |
| Is this count unusual for this period? | Poisson or negative-binomial tail probability | Counts of events in fixed intervals |
| Has the level changed? | Change-point detection on the mean | 12 or more periods, no seasonality shorter than the window |
| Is there a seasonal component? | Seasonal decomposition | Three or more full cycles observed |
| Are two groups different? | Mann-Whitney U | Ordinal or non-normal distributions |
| Is there an association? | Spearman rank correlation | Monotonic but not necessarily linear relations |
| What proportion is affected? | Wilson score interval | Any proportion, reported with the interval |

### Thresholds

A threshold is part of a conclusion and is stated with it. The defaults
below apply unless a methodology overrides them.

- Robust z-score: flag above 3.5.
- Tail probability: flag below 0.01.
- Minimum population for a baseline: 30 observations.
- Minimum coverage for a population conclusion: 80 per cent.

### Multiple comparisons

Where a test is applied across many entities, the false discovery rate is
controlled by the Benjamini-Hochberg procedure at 0.05. An unadjusted
scan across thousands of entities produces findings by construction.

## Machine learning

### When it is justified

Machine learning is justified when the relation being modelled is not
expressible as a stated rule, the training population is representative
of the population under analysis, and the output is a ranking or a
grouping that a person will review rather than a decision that will be
acted on unattended.

### When it is not

- The question is answerable by a described statistic. A described
  statistic is preferred, because it can be explained.
- The label is scarce, imbalanced beyond 1 in 100, or derived from the
  same signal being predicted.
- The output would be used as evidence rather than as a candidate
  generator. A model output is a hypothesis, not an evidence item.

### Reporting

A model in use reports its training window, its population, its features
in concept terms, its validation scheme and its performance on a held-out
period. A model that cannot report these is withdrawn.

## Methodologies

### Ticket Anomaly Detection

#### Purpose

Identify service tickets and ticket patterns that deviate from the
established behaviour of comparable work, so that systemic failures are
found rather than individual escalations.

#### Required evidence

- Ticket records with identifier, opened timestamp, resolved timestamp,
  category, priority and assignment group.
- Reassignment history per ticket.
- Assignment group membership and size.
- Category taxonomy, with the effective dates of any change.

#### Analysis process

1. Establish the population: tickets closed within the analysis window,
   excluding categories with fewer than 30 closed tickets.
2. Compute per-category baselines for resolution time, reassignment
   count and reopen rate.
3. Score each ticket against its category baseline by robust z-score.
4. Scan for category-level and group-level level changes by change-point
   detection.
5. Adjust the ticket-level scan for multiple comparisons.
6. Group surviving anomalies by shared category, group and time window
   into candidate patterns.
7. Rank patterns by affected volume multiplied by median excess
   resolution time.

#### Validation rules

- A category whose taxonomy changed inside the window is analysed only
  on the segment after the change.
- A ticket reopened more than once is counted once in volume and once per
  reopen in reopen rate.
- A group smaller than five members is excluded from group-level
  comparison, since its baseline is dominated by individuals.

#### Assumptions

- The category recorded on a ticket reflects the work performed.
- Resolution timestamps reflect resolution rather than administrative
  closure.
- The analysis window contains no change in working-hours policy.

#### Invalidators

- A bulk closure event inside the window.
- A ticketing platform migration inside the window.
- More than 10 per cent of tickets in the window missing a resolved
  timestamp.

### License Optimization

#### Purpose

Establish the difference between entitlement, assignment and consumption
for each licensed product, and quantify the recoverable cost in that
difference.

#### Required evidence

- Entitlement records per product, with quantity and term.
- Assignment records per product and actor.
- Usage signals per product and actor, at daily granularity or finer.
- Unit cost per product per period.
- Leaver records, to distinguish an inactive account from an inactive
  person.

#### Analysis process

1. Reconcile entitlement against assignment per product and report the
   difference in both directions.
2. Classify each assignment over the usage window as consumed,
   under-consumed or unconsumed, against the stated threshold for the
   product.
3. Exclude assignments held by leavers from the optimisation candidate
   set and report them separately as an access finding.
4. Quantify recoverable cost as unconsumed assignments multiplied by unit
   cost, reported with the Wilson interval on the unconsumed proportion.
5. Identify downgrade candidates where a lower tier of the same product
   covers observed consumption.

#### Validation rules

- Over-assignment beyond entitlement is a compliance finding and is
  reported before any optimisation finding.
- A usage window shorter than 90 days does not support an unconsumed
  classification, because quarterly work is invisible in it.
- Recoverable cost is reported as an upper bound where contract terms
  prevent mid-term reduction.

#### Assumptions

- Usage signals capture all consumption paths for the product.
- Unit cost is attributable per assignment rather than per site.
- The assignment record is current rather than a historical snapshot.

#### Invalidators

- A contract renewal inside the usage window that changed entitlement.
- Any product where usage signal coverage is below 80 per cent of
  assignments.

### Application Portfolio Rationalization

#### Purpose

Determine, for each application in the portfolio, whether it should be
retained, consolidated, replaced or retired, on evidence of usage,
ownership, cost, dependency and business criticality.

#### Required evidence

- Application inventory with identifier, name and lifecycle status.
- Usage signals per application, with distinct actor counts per period.
- Ownership records naming an accountable owner.
- Cost records per application per period.
- Dependency records, both inbound and outbound.
- Business metadata: criticality, and the capability the application
  serves.

#### Analysis process

1. Establish the portfolio: applications with a lifecycle status of
   active or unknown.
2. Compute a usage profile per application over 12 months: distinct
   actors, trend, and last observed use.
3. Build the dependency graph and identify the inbound dependents of
   each application.
4. Group applications by served capability to find functional overlap.
5. Classify each application against the disposition rules below.
6. Report cost and dependency consequences for each classification.

#### Disposition rules

| Disposition | Condition |
| --- | --- |
| Retire | No usage in 12 months, no inbound dependents, criticality not high. |
| Consolidate | Functional overlap with another application in the same capability, where one has materially higher usage. |
| Replace | In use, but lifecycle status is end-of-support or the owner is unassigned and cost exceeds the portfolio median. |
| Retain | Everything else, including every application with unresolved evidence. |

#### Validation rules

- An application with inbound dependents is never classified for
  retirement, whatever its own usage.
- An application without an accountable owner is classified as retain
  and reported as an ownership gap, since there is no party to confirm a
  disposition with.
- Usage measured on fewer than 12 months is stated as such and lowers
  the disposition to retain where retirement would otherwise follow.

#### Assumptions

- The usage signal reaches every access path, including service accounts
  and scheduled jobs.
- The dependency record is complete for inbound relations.
- Capability metadata is applied consistently across the portfolio.

#### Invalidators

- Dependency coverage below 80 per cent of the portfolio.
- Any application whose usage signal source changed inside the window.

## Failure modes

These are the ways an analysis of this kind is commonly wrong. Each is
checked explicitly rather than trusted not to occur.

| Failure mode | Check |
| --- | --- |
| Silence read as absence | Distinguish no usage from no usage signal. An entity with no instrumentation is unresolved, not unused. |
| Assignment read as consumption | Never substitute an assignment record for a usage signal. |
| Survivorship in the population | Include entities decommissioned inside the window when computing baselines. |
| Baseline contaminated by the anomaly | Compute baselines on medians and MAD, so an outlier does not raise the line it is measured against. |
| Window shorter than the cycle | Reject conclusions whose window is shorter than the periodicity of the behaviour. |
| Aggregation hiding the finding | Report the distribution alongside every mean. |
| Identity collision | Reconcile actors across sources before counting distinct actors. |
| Stale authority | Re-check the authoritative-source declaration when a conflict appears, rather than applying the prior precedence. |

## Decision frameworks

### Escalate rather than assume

Where two readings of the evidence are both admissible, the system
presents both and the ambiguity is resolved by a person. It does not
choose the more likely one silently.

### Reversibility governs autonomy

| Consequence | Authority |
| --- | --- |
| Read, and compute in an isolated workspace | The system acts. |
| Write to a system of record | A person approves. |
| Irreversible, or external to the organisation | A person approves, and the approval is recorded with the evidence it rested on. |

### Sufficiency governs reporting

A methodology reports one of three outcomes and never anything between
them: a conclusion with its evidence, an insufficiency naming what is
missing, or an ambiguity naming the readings in conflict.
