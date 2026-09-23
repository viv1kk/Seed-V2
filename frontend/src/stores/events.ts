import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useSystemStore, type Phase } from './system'

export type Category =
  | 'DISCOVERY'
  | 'ANALYSIS'
  | 'VALIDATION'
  | 'DECISION'
  | 'POLICY'
  | 'WARNING'
  | 'SUCCESS'
  | 'HUMAN_INPUT'

export type Severity = 'INFO' | 'WARNING' | 'ERROR'

export interface SystemEvent {
  sequence: number
  timestamp: string
  type: string
  phase: Phase
  category: Category
  severity: Severity
  message: string
  payload: Record<string, unknown>
}

export type ConnectionState = 'idle' | 'connecting' | 'open' | 'error'

/** Every event type the backend emits arrives under its own SSE name. */
const EVENT_TYPES = [
  'lifecycle.transition',
  'seed.loaded',
  'system.ready',
  'run.failed',
  'discovery.inventory.loaded',
  'discovery.system.found',
  'discovery.endpoint.testing',
  'discovery.credentials.required',
  'discovery.credentials.accepted',
  'discovery.datasets.enumerated',
  'discovery.dataset.excluded',
  'discovery.system.connected',
  'discovery.endpoint.timeout',
  'discovery.endpoint.recovered',
  'discovery.system.registered',
  'discovery.completed',
  'policy.decision',
  'assessment.methodology.evaluated',
  'assessment.evidence.insufficient',
  'assessment.evidence.revised',
  'assessment.completed',
  'solution.proposed',
  'solution.submitted',
  'solution.approved',
  'solution.rejected',
  'approval.completed',
  'implementation.started',
  'implementation.build.started',
  'implementation.component.built',
  'implementation.tests.passed',
  'solution.ready',
  'implementation.completed',
  'seeding.closing.started',
  'seeding.notes.consolidated',
  'seeding.scratch.cleared',
  'seeding.interfaces.promoted',
  'seeding.tools.retired',
  'seeding.consumed',
  'deployment.ready',
  'solution.started',
  'solution.closed',
  'human.requested',
  'human.resolved',
] as const

/**
 * Owns the connection to the event stream.
 *
 * Snapshot first, then stream (FR-E5). A sequence gap means the local
 * view can no longer be trusted, so it is discarded and rebuilt rather
 * than patched (FR-E6). Reconnection replays exactly, because the
 * browser sends `Last-Event-ID` on its own and the backend serves the
 * retained log from that point (FR-E7).
 */
export const useEventStore = defineStore('events', () => {
  const system = useSystemStore()

  const events = ref<SystemEvent[]>([])
  const connection = ref<ConnectionState>('idle')
  const lastSequence = ref(0)

  /** Sequence numbers at which a gap was detected, for the operator. */
  const gaps = ref<number[]>([])
  const resyncs = ref(0)

  let source: EventSource | null = null
  let resyncing = false

  function receive(event: SystemEvent): void {
    // Contiguity is the whole guarantee. Anything else means an event
    // was lost, and a lost event cannot be reconstructed locally.
    const expected = lastSequence.value + 1
    if (lastSequence.value > 0 && event.sequence !== expected) {
      gaps.value.push(expected)
      void resync()
      return
    }

    lastSequence.value = event.sequence
    events.value.push(event)
    system.apply(event)
  }

  function open(): void {
    source = new EventSource('/api/events')
    connection.value = 'connecting'

    source.onopen = () => {
      connection.value = 'open'
    }

    // The browser reconnects on its own and replays from
    // `Last-Event-ID`, so an error here is a state to display rather
    // than something to act on.
    source.onerror = () => {
      connection.value = 'error'
    }

    for (const type of EVENT_TYPES) {
      source.addEventListener(type, (message) => {
        receive(JSON.parse((message as MessageEvent).data) as SystemEvent)
      })
    }
  }

  function close(): void {
    source?.close()
    source = null
  }

  async function connect(): Promise<void> {
    if (source) {
      return
    }
    connection.value = 'connecting'
    await system.fetchSnapshot()
    lastSequence.value = 0
    open()
  }

  /** Discard local state and rebuild it from a fresh snapshot (FR-E6). */
  async function resync(): Promise<void> {
    if (resyncing) {
      return
    }
    resyncing = true
    resyncs.value += 1
    try {
      close()
      events.value = []
      lastSequence.value = 0
      await system.fetchSnapshot()
      open()
    } finally {
      resyncing = false
    }
  }

  function disconnect(): void {
    close()
    connection.value = 'idle'
  }

  /** Reset the run, then rebuild from the state it left behind (FR-O4). */
  async function reset(): Promise<void> {
    await system.reset()
    await resync()
  }

  /** Answer an outstanding human request (FR-H7). */
  async function submitHuman(requestId: string, submission: unknown): Promise<void> {
    await fetch(`/api/human/${encodeURIComponent(requestId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submission),
    })
  }

  /**
   * Decide on one solution (FR-AP3).
   *
   * The decision answers the approval request the run is parked on. The
   * card changes when the decision comes back on the stream, not when the
   * button is pressed, so the screen never shows a decision the system
   * did not record.
   */
  async function decide(solutionId: string, decision: 'approve' | 'reject'): Promise<boolean> {
    const response = await fetch(`/api/solutions/${encodeURIComponent(solutionId)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    })
    return response.ok
  }

  /**
   * Run a ready solution, or return from it (FR-L8).
   *
   * As with a decision, the screen follows the stream rather than the
   * button: the dashboard opens when the lifecycle arrives at RUNNING.
   */
  async function runSolution(solutionId: string): Promise<boolean> {
    const response = await fetch(`/api/solutions/${encodeURIComponent(solutionId)}/run`, {
      method: 'POST',
    })
    return response.ok
  }

  async function closeSolution(solutionId: string): Promise<boolean> {
    const response = await fetch(`/api/solutions/${encodeURIComponent(solutionId)}/close`, {
      method: 'POST',
    })
    return response.ok
  }

  return {
    events,
    connection,
    lastSequence,
    gaps,
    resyncs,
    connect,
    disconnect,
    resync,
    reset,
    submitHuman,
    decide,
    runSolution,
    closeSolution,
  }
})
