import { computed } from 'vue'
import { defineStore } from 'pinia'

import { useEventStore, type SystemEvent } from './events'

export type Effect = 'ALLOW' | 'DENY' | 'ESCALATE'

/**
 * A policy decision, as it arrives on the stream.
 *
 * FR-P4 requires the action, the resource, the effect and the rule id, so
 * the payload carries all four. Declared here in M4 so the panel is ready
 * for M5 to fill rather than needing to be revisited: the engine that
 * produces these is M5's work, and this is the shape it emits.
 */
export interface Decision {
  sequence: number
  timestamp: string
  phase: string
  action: string
  resource: string
  effect: Effect
  rule: string
  message: string
}

function decisionOf(event: SystemEvent): Decision | null {
  const effect = event.payload.effect as Effect | undefined
  if (!effect) {
    return null
  }
  return {
    sequence: event.sequence,
    timestamp: event.timestamp,
    phase: event.phase,
    action: (event.payload.action as string) ?? '',
    resource: (event.payload.resource as string) ?? '',
    effect,
    rule: (event.payload.rule as string) ?? '',
    message: event.message,
  }
}

/**
 * The protection layer's surface.
 *
 * Derived from the event stream rather than fetched, because the decision
 * record *is* the stream: a panel with its own copy could disagree with
 * the audit log beside it, and the one thing this layer cannot afford is
 * two accounts of what was permitted (§83.7).
 *
 * M5 adds the rule set, which does need fetching — it is configuration,
 * not history.
 */
export const useProtectionStore = defineStore('protection', () => {
  const events = useEventStore()

  const decisions = computed<Decision[]>(() =>
    events.events
      .filter((event) => event.category === 'POLICY')
      .map(decisionOf)
      .filter((decision): decision is Decision => decision !== null),
  )

  function countOf(effect: Effect): number {
    return decisions.value.filter((decision) => decision.effect === effect).length
  }

  const allowed = computed(() => countOf('ALLOW'))
  const denied = computed(() => countOf('DENY'))
  const escalated = computed(() => countOf('ESCALATE'))
  const total = computed(() => decisions.value.length)

  return { decisions, allowed, denied, escalated, total }
})
