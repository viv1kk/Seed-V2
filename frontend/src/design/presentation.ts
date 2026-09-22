import type { Category, Severity, SystemEvent } from '../stores/events'

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
