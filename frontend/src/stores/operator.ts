import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Speed = '1x' | '2x' | 'instant'
export type RunStatus = 'idle' | 'running' | 'awaiting-human' | 'complete'

interface RunState {
  status: RunStatus
  speed: Speed
}

/**
 * The operator's controls (FR-O1).
 *
 * The audience never sees these. They are reached by keyboard shortcut
 * or through a panel that is hidden by default, and there is no
 * transport bar anywhere in the interface (FR-O2). The panel exists so
 * that an operator who forgets a shortcut has somewhere to look, not so
 * that the controls have a home on screen.
 */
export const useOperatorStore = defineStore('operator', () => {
  const status = ref<RunStatus>('idle')
  const speed = ref<Speed>('1x')

  /** Whether the hidden panel is currently revealed. */
  const panelVisible = ref(false)

  function adopt(next: RunState): void {
    status.value = next.status
    speed.value = next.speed
  }

  async function send(path: string, body?: unknown): Promise<void> {
    const response = await fetch(path, {
      method: 'POST',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) {
      // A refusal is a conflict with the current state rather than a
      // fault, so the panel reports it and the run continues untouched.
      return
    }
    adopt((await response.json()) as RunState)
  }

  async function fetchRunState(): Promise<void> {
    const response = await fetch('/api/operator')
    if (response.ok) {
      adopt((await response.json()) as RunState)
    }
  }

  const start = () => send('/api/operator/start')
  const setSpeed = (next: Speed) => send('/api/operator/speed', { speed: next })
  const skipPhase = () => send('/api/operator/skip')

  /**
   * Revise one profiled field's completeness (M7's rehearsal proof).
   *
   * Every assessment resting on the field is regraded by the backend, and
   * the result arrives on the stream like any other change.
   */
  async function reviseEvidence(dataset: string, field: string, completeness: number): Promise<void> {
    await fetch(
      `/api/environment/sources/${encodeURIComponent(dataset)}/fields/${encodeURIComponent(field)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completeness }),
      },
    )
  }

  function togglePanel(): void {
    panelVisible.value = !panelVisible.value
  }

  return {
    status,
    speed,
    panelVisible,
    fetchRunState,
    start,
    setSpeed,
    skipPhase,
    reviseEvidence,
    togglePanel,
  }
})
