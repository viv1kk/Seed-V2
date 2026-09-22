import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { useEventStore, type SystemEvent } from './events'

export type Effect = 'ALLOW' | 'DENY' | 'ESCALATE'

/**
 * A policy decision, as it arrives on the stream.
 *
 * FR-P4 requires the action, the resource, the effect and the rule id.
 * The rest is what makes the record auditable: every rule that applied
 * (so an overruled permission is visible rather than absent), the
 * rationale of the deciding rule, and what the request said it was for.
 */
export interface Decision {
  sequence: number
  timestamp: string
  phase: string
  action: string
  resource: string
  source: string | null
  purpose: string | null
  effect: Effect
  rule: string
  matched: string[]
  reason: string
  message: string
}

export interface Rule {
  id: string
  description: string
  effect: Effect
  rationale: string
  actions: string[]
  facts: string[]
}

export interface RuleGroup {
  name: string
  rules: Rule[]
}

function decisionOf(event: SystemEvent): Decision | null {
  const payload = event.payload
  const effect = payload.effect as Effect | undefined
  if (!effect) {
    return null
  }
  return {
    sequence: event.sequence,
    timestamp: event.timestamp,
    phase: event.phase,
    action: (payload.action as string) ?? '',
    resource: (payload.resource as string) ?? '',
    source: (payload.source as string | null) ?? null,
    purpose: (payload.purpose as string | null) ?? null,
    effect,
    rule: (payload.rule as string) ?? '',
    matched: (payload.matched as string[]) ?? [],
    reason: (payload.reason as string) ?? '',
    message: event.message,
  }
}

/**
 * The protection layer's surface.
 *
 * Decisions are derived from the event stream rather than fetched,
 * because the decision record *is* the stream: a panel with its own copy
 * could disagree with the audit log beside it, and two accounts of what
 * was permitted is the one thing this layer cannot afford (§83.7).
 *
 * The rule set is fetched, because it is configuration rather than
 * history. It is served from the rules the engine enforces, not from the
 * document, so what the panel shows is what is applied (FR-P7).
 */
export const useProtectionStore = defineStore('protection', () => {
  const events = useEventStore()

  const groups = ref<RuleGroup[]>([])

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

  /** How many recorded decisions each rule decided. */
  const citations = computed<Record<string, number>>(() => {
    const tally: Record<string, number> = {}
    for (const decision of decisions.value) {
      tally[decision.rule] = (tally[decision.rule] ?? 0) + 1
    }
    return tally
  })

  const ruleCount = computed(() =>
    groups.value.reduce((sum, group) => sum + group.rules.length, 0),
  )

  async function fetchRules(): Promise<void> {
    if (groups.value.length > 0) {
      return
    }
    const response = await fetch('/api/protection/rules')
    if (response.ok) {
      groups.value = (await response.json()) as RuleGroup[]
    }
  }

  return {
    groups,
    decisions,
    allowed,
    denied,
    escalated,
    total,
    citations,
    ruleCount,
    fetchRules,
  }
})
