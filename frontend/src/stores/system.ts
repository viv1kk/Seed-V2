import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { SystemEvent } from './events'

export type LifecycleState =
  | 'UNINITIALIZED'
  | 'INITIALIZED'
  | 'DISCOVERING'
  | 'DISCOVERY_BLOCKED'
  | 'DISCOVERY_COMPLETE'
  | 'ASSESSING'
  | 'AWAITING_APPROVAL'
  | 'IMPLEMENTING'
  | 'IMPLEMENTATION_COMPLETE'
  | 'READY_TO_RUN'
  | 'RUNNING'

export type Phase = 'INIT' | 'DISCOVERY' | 'ASSESSMENT' | 'IMPLEMENTATION' | 'RUNTIME'

export const PHASE_ORDER: Phase[] = [
  'INIT',
  'DISCOVERY',
  'ASSESSMENT',
  'IMPLEMENTATION',
  'RUNTIME',
]

export type RequestKind =
  | 'credentials'
  | 'ambiguity'
  | 'missing-info'
  | 'approval'
  | 'confirmation'

export interface BlockedOn {
  kind: RequestKind
  requestId: string
  prompt: string
}

export interface StateSnapshot {
  sequence: number
  lifecycle: LifecycleState
  phase: Phase
  blockedOn: BlockedOn | null
  seed: Record<string, unknown> | null
  environment: Record<string, unknown>
  assessments: Record<string, unknown>[]
  solutions: Record<string, unknown>[]
  approvals: Record<string, unknown>[]
  implementations: Record<string, unknown>[]
  runtime: Record<string, unknown>
}

/**
 * Mirrors System State.
 *
 * The backend remains the sole source of truth (FR-L5). This store
 * holds a snapshot of it and folds subsequent events into that snapshot
 * (FR-E5), so what the screen shows is derived from the same stream the
 * audit log is built from rather than from a parallel model.
 *
 * `apply` is therefore a reducer that must stay in step with the
 * backend's own transitions. A resync is always available if it drifts,
 * which is why a gap is cheap to recover from (FR-E6).
 */
export const useSystemStore = defineStore('system', () => {
  const snapshot = ref<StateSnapshot | null>(null)
  const lifecycle = ref<LifecycleState>('UNINITIALIZED')
  const phase = ref<Phase>('INIT')
  const blockedOn = ref<BlockedOn | null>(null)

  /** The sequence number the snapshot is current as of. */
  const baseline = ref(0)

  function adopt(next: StateSnapshot): void {
    snapshot.value = next
    lifecycle.value = next.lifecycle
    phase.value = next.phase
    blockedOn.value = next.blockedOn
    baseline.value = next.sequence
  }

  async function fetchSnapshot(): Promise<void> {
    const response = await fetch('/api/state')
    if (!response.ok) {
      throw new Error(`Snapshot failed: ${response.status}`)
    }
    adopt((await response.json()) as StateSnapshot)
  }

  /**
   * Fold one event into local state.
   *
   * Only events after the snapshot's sequence number are applied.
   * Replayed events below it are already reflected in the snapshot, and
   * applying them again would move the system backwards.
   */
  function apply(event: SystemEvent): void {
    if (event.sequence <= baseline.value) {
      return
    }
    switch (event.type) {
      case 'lifecycle.transition':
        lifecycle.value = event.payload.to as LifecycleState
        phase.value = event.phase
        break
      case 'human.requested':
        blockedOn.value = {
          kind: event.payload.kind as RequestKind,
          requestId: event.payload.requestId as string,
          prompt: event.message,
        }
        break
      case 'human.resolved':
        blockedOn.value = null
        break
    }
  }

  async function reset(): Promise<void> {
    const response = await fetch('/api/state/reset', { method: 'POST' })
    if (!response.ok) {
      throw new Error(`Reset failed: ${response.status}`)
    }
    adopt((await response.json()) as StateSnapshot)
  }

  return { snapshot, lifecycle, phase, blockedOn, baseline, fetchSnapshot, apply, reset }
})
