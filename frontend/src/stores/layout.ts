import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { useDashboardStore } from './dashboard'
import { useSystemStore, type LifecycleState } from './system'

/** Which panes the workspace shows (D-14, FR-W2). */
export type Layout = 'both' | 'seeding' | 'life'

/**
 * The layout the lifecycle asks for (FR-W3, as amended by D-18).
 *
 * Life only while the seed is being grown: the Life pane shows it growing
 * as the process advances, and the Seeding pane's detail is one click
 * away. A question still brings the Seeding pane forward (FR-W5). Both
 * once Implementation completes, so the hand-over is visible. Life only
 * once there is something running to look at.
 */
function defaultFor(lifecycle: LifecycleState): Layout {
  switch (lifecycle) {
    case 'UNINITIALIZED':
      return 'seeding'
    case 'IMPLEMENTATION_COMPLETE':
      return 'both'
    default:
      return 'life'
  }
}

/**
 * The layout of the two panes.
 *
 * The lifecycle sets the default, and a person's choice holds until the
 * lifecycle next changes the default (FR-W3). A layout only hides panes;
 * both stay mounted (NFR-A7), so neither loses its state to the other.
 */
export const useLayoutStore = defineStore('layout', () => {
  const system = useSystemStore()
  const dashboard = useDashboardStore()

  const chosen = ref<Layout>(dashboard.rehearsal ? 'life' : defaultFor(system.lifecycle))

  /**
   * A pending request makes the Seeding pane visible, whatever was chosen
   * (FR-W5). The human-input surface lives there, and a question asked in
   * a hidden pane is not asked at all (FR-H1).
   */
  const forced = computed(() => system.blockedOn !== null)

  const layout = computed<Layout>(() =>
    forced.value && chosen.value === 'life' ? 'both' : chosen.value,
  )

  const seeding = computed(() => layout.value !== 'life')
  const life = computed(() => layout.value !== 'seeding')

  watch(
    () => defaultFor(system.lifecycle),
    (next) => {
      chosen.value = next
    },
  )

  // A rehearsal link opens its dashboard in Life only (FR-W6). Closing it
  // hands the layout back to the lifecycle, or a rehearsal opened before
  // planting would leave the new workspace on an empty Life pane.
  watch(
    () => dashboard.rehearsal,
    (id) => {
      chosen.value = id ? 'life' : defaultFor(system.lifecycle)
    },
  )

  function choose(next: Layout): void {
    chosen.value = next
  }

  return { layout, forced, seeding, life, choose }
})
