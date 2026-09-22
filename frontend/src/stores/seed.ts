import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export type Layer = 'core' | 'adaptation' | 'protection'

export interface Heading {
  level: number
  text: string
}

export interface LayerSummary {
  layer: Layer
  filename: string
  title: string | null
  headings: Heading[]
  headingCount: number
  sections: number
  topics: number
  lines: number
  characters: number
}

export interface LayerDescriptor {
  layer: Layer
  filename: string
  role: string
}

/** One of the three slots on the seed screen, and what has landed in it. */
export interface Slot {
  descriptor: LayerDescriptor
  /** The name of the file the operator supplied, which need not be the canonical one. */
  supplied: string | null
  summary: LayerSummary | null
  error: string | null
  busy: boolean
}

interface Rejection {
  detail: string
  layer?: Layer
  reason?: string
}

/**
 * The plant (FR-S2).
 *
 * Two steps, because the gesture has two. A layer is parsed the moment it
 * lands, so the summary beside it is derived from the file that was
 * actually supplied rather than from a fixture (FR-S5). Initialization
 * then commits all three at once, which is where the lifecycle moves.
 *
 * The file text is held here until then. It is never parsed in the
 * browser: a summary the frontend invented would look identical and mean
 * nothing.
 */
export const useSeedStore = defineStore('seed', () => {
  const slots = ref<Slot[]>([])
  const initializing = ref(false)
  const failure = ref<string | null>(null)

  /** Supplied file text, keyed by layer, held until initialization. */
  const staged = new Map<Layer, string>()

  const ready = computed(
    () => slots.value.length === 3 && slots.value.every((slot) => slot.summary !== null),
  )

  const count = computed(() => slots.value.filter((slot) => slot.summary !== null).length)

  function slotOf(layer: Layer): Slot | undefined {
    return slots.value.find((slot) => slot.descriptor.layer === layer)
  }

  async function fetchLayers(): Promise<void> {
    const response = await fetch('/api/seed/layers')
    if (!response.ok) {
      failure.value = `The seed layers could not be read: ${response.status}`
      return
    }
    const descriptors = (await response.json()) as LayerDescriptor[]
    slots.value = descriptors.map((descriptor) => ({
      descriptor,
      supplied: null,
      summary: null,
      error: null,
      busy: false,
    }))
  }

  /**
   * Supply one layer and parse it (FR-S4, FR-S5).
   *
   * A rejection clears the slot rather than leaving a stale summary
   * beside a file that was refused.
   */
  async function supply(layer: Layer, filename: string, content: string): Promise<void> {
    const slot = slotOf(layer)
    if (!slot) {
      return
    }

    slot.busy = true
    slot.error = null
    try {
      const response = await fetch('/api/seed/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layer, content }),
      })

      if (!response.ok) {
        const rejection = (await response.json()) as Rejection
        slot.summary = null
        slot.supplied = filename
        slot.error = rejection.reason ?? rejection.detail
        staged.delete(layer)
        return
      }

      slot.summary = (await response.json()) as LayerSummary
      slot.supplied = filename
      staged.set(layer, content)
    } finally {
      slot.busy = false
    }
  }

  /** Read a dropped or chosen file and supply it. */
  async function supplyFile(layer: Layer, file: File): Promise<void> {
    await supply(layer, file.name, await file.text())
  }

  function clear(layer: Layer): void {
    const slot = slotOf(layer)
    if (slot) {
      slot.supplied = null
      slot.summary = null
      slot.error = null
    }
    staged.delete(layer)
  }

  /**
   * Load the seed files shipped with the repository (FR-S7).
   *
   * The hidden affordance skips the file picker and nothing else: the
   * text returned here goes through the same parse as a dropped file, so
   * the screen fills in exactly as it would have.
   */
  async function loadBundled(): Promise<void> {
    failure.value = null
    const response = await fetch('/api/seed/bundled')
    if (!response.ok) {
      failure.value = `The bundled seed could not be read: ${response.status}`
      return
    }

    const { layers } = (await response.json()) as { layers: Record<Layer, string> }
    for (const slot of slots.value) {
      const layer = slot.descriptor.layer
      await supply(layer, slot.descriptor.filename, layers[layer])
    }
  }

  /**
   * Plant the seed (FR-S3).
   *
   * The lifecycle change is not adopted from the response. It arrives on
   * the event stream like every other transition, so the screen that
   * replaces this one is driven by the same events the audit log is
   * built from (FR-E5).
   */
  async function initialize(): Promise<void> {
    if (!ready.value || initializing.value) {
      return
    }

    initializing.value = true
    failure.value = null
    try {
      const response = await fetch('/api/seed/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layers: Object.fromEntries(staged) }),
      })

      if (!response.ok) {
        const rejection = (await response.json()) as Rejection
        failure.value = rejection.detail
      }
    } finally {
      initializing.value = false
    }
  }

  /** Forget the staged seed, so Reset returns to an empty screen (FR-O4). */
  function discard(): void {
    for (const slot of slots.value) {
      clear(slot.descriptor.layer)
    }
    failure.value = null
  }

  return {
    slots,
    initializing,
    failure,
    ready,
    count,
    fetchLayers,
    supply,
    supplyFile,
    clear,
    loadBundled,
    initialize,
    discard,
  }
})
