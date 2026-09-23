import type { Category, Severity, SystemEvent } from '../stores/events'
import type { Phase } from '../stores/system'

/**
 * How an event is presented.
 *
 * Mirrors `backend/app/domain/presentation.py`, which is the authority
 * and which holds the reasoning. In short: §61 draws a distinction
 * between a technical error, a human decision and a withheld conclusion,
 * and FR-H4 forbids conflating them. Rendering all three in warning
 * orange would say that a request for credentials is a malfunction.
 *
 * The rules key on the event *type* by suffix, so a milestone that adds
 * events lands in the right bucket by naming them consistently rather
 * than by editing a list here.
 */
export type Presentation = 'activity' | 'error' | 'decision' | 'insufficient'

/** A fault. `.denied` is absent: a policy denial is the boundary working. */
const ERROR_SUFFIXES = ['.failed', '.timeout', '.error', '.unreachable']

/** The system declining to conclude. Neither a fault nor a question. */
const INSUFFICIENT_SUFFIXES = ['.insufficient', '.unresolved', '.withheld']

function endsWithAny(value: string, suffixes: string[]): boolean {
  return suffixes.some((suffix) => value.endsWith(suffix))
}

export function presentationOf(event: {
  type: string
  category: Category
  severity: Severity
}): Presentation {
  // Tested first: it is the case the other two swallow.
  if (endsWithAny(event.type, INSUFFICIENT_SUFFIXES)) {
    return 'insufficient'
  }
  if (endsWithAny(event.type, ERROR_SUFFIXES) || event.severity === 'ERROR') {
    return 'error'
  }
  if (event.category === 'HUMAN_INPUT') {
    return 'decision'
  }
  return 'activity'
}

/**
 * Category labels for the stream.
 *
 * §16 writes `HUMAN INPUT REQUIRED` rather than `HUMAN_INPUT`. The wire
 * name is machine-readable (FR-E3) and this is the reading version; an
 * auditable stream is not a log of enum values (FR-E8).
 */
const CATEGORY_LABELS: Record<Category, string> = {
  DISCOVERY: 'Discovery',
  ANALYSIS: 'Analysis',
  VALIDATION: 'Validation',
  DECISION: 'Decision',
  POLICY: 'Policy',
  WARNING: 'Warning',
  SUCCESS: 'Success',
  HUMAN_INPUT: 'Human input',
}

export function labelOf(category: Category): string {
  return CATEGORY_LABELS[category] ?? category
}

/**
 * What a phase is called on screen (D-11, FR-N1).
 *
 * The phase values are contract and keep their names; only the label
 * the viewer reads follows the display vocabulary.
 */
export const PHASE_LABELS: Record<Phase, string> = {
  INIT: 'Planting',
  DISCOVERY: 'Discovery',
  ASSESSMENT: 'Assessment',
  IMPLEMENTATION: 'Implementation',
  RUNTIME: 'Life',
}

/** Wall-clock time, to the second. The stream is read, not measured. */
export function clockOf(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { hour12: false })
}

/**
 * Whether a phase separator belongs above this entry.
 *
 * The stream is an audit record, so where one phase ended and the next
 * began is part of what it records (FR-E8).
 */
export function startsPhase(event: SystemEvent, previous: SystemEvent | undefined): boolean {
  return previous === undefined || previous.phase !== event.phase
}

/**
 * A proportion as a percentage, to one decimal where it has one.
 *
 * One formatter for every surface, so a figure reads the same on a card,
 * in the review and in the stream: 0.903 is 90.3% everywhere, never 90%
 * in one place and 90.3% in another.
 */
export function percentOf(value: number | null | undefined): string {
  return value === null || value === undefined
    ? '—'
    : `${(value * 100).toFixed(1).replace(/\.0$/, '')}%`
}

/**
 * A simulated duration, as a test runner would print it: 1840 ms reads
 * "1.84 s", 21 ms reads "21 ms". From a second up it matches
 * `builds.seconds` in the backend, so a total reads the same in the stream
 * and on the pipeline.
 */
export function secondsOf(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`
}
