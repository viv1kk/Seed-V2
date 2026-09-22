import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface SystemEvent {
  sequence: number
  type: string
  timestamp: string
  payload: Record<string, unknown>
}

export type ConnectionState = 'idle' | 'connecting' | 'open' | 'error'

/**
 * Holds the event stream.
 *
 * M0 proves the transport only: connect, receive, render. M1 replaces
 * this with snapshot-then-stream, `Last-Event-ID` replay and
 * sequence-gap detection (FR-E4--E7). The gap check below is the seam
 * that work extends rather than replaces.
 */
export const useEventStore = defineStore('events', () => {
  const events = ref<SystemEvent[]>([])
  const connection = ref<ConnectionState>('idle')
  const lastSequence = ref(0)
  const gaps = ref<number[]>([])

  let source: EventSource | null = null

  function record(event: SystemEvent): void {
    const expected = lastSequence.value + 1
    if (lastSequence.value > 0 && event.sequence !== expected) {
      gaps.value.push(expected)
    }
    lastSequence.value = event.sequence
    events.value.push(event)
  }

  function connect(): void {
    if (source) {
      return
    }
    connection.value = 'connecting'
    source = new EventSource('/api/events')

    source.onopen = () => {
      connection.value = 'open'
    }

    source.onerror = () => {
      connection.value = 'error'
    }

    source.addEventListener('system.heartbeat', (message) => {
      record(JSON.parse((message as MessageEvent).data) as SystemEvent)
    })
  }

  function disconnect(): void {
    source?.close()
    source = null
    connection.value = 'idle'
  }

  return { events, connection, lastSequence, gaps, connect, disconnect }
})
