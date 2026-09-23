<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, watch } from 'vue'

import OperatorPanel from './components/OperatorPanel.vue'
import SeedView from './views/SeedView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import { useDashboardStore } from './stores/dashboard'
import { useEventStore } from './stores/events'
import { useSeedStore } from './stores/seed'
import { useSystemStore } from './stores/system'

// Loaded when first opened: the charting library is the dashboard's alone,
// and the workspace should not wait for it.
const DashboardView = defineAsyncComponent(() => import('./views/DashboardView.vue'))

const dashboard = useDashboardStore()
const events = useEventStore()
const seed = useSeedStore()
const system = useSystemStore()

/**
 * Which screen is showing.
 *
 * Derived from the lifecycle rather than held separately, so the screen
 * follows the system instead of the other way round. The plant advances
 * the lifecycle over HTTP and the transition arrives on the event stream,
 * which is what moves the interface (FR-E5).
 */
const planted = computed(() => system.lifecycle !== 'UNINITIALIZED')

/**
 * A running solution's dashboard is shown in front of the workspace. The
 * workspace is hidden, not unmounted (NFR-A3): returning finds it exactly
 * as it was left, stream scrolled where it was (FR-L8).
 */
const running = computed(() => system.lifecycle === 'RUNNING')

/**
 * Which dashboard is showing, if any: the running solution's, or one
 * opened from a link for rehearsal, which needs no run to reach (D-3).
 */
const shown = computed<{ id: string; mode: 'running' | 'rehearsal' } | null>(() => {
  if (running.value && system.runtime.active) {
    return { id: system.runtime.active, mode: 'running' }
  }
  return dashboard.rehearsal ? { id: dashboard.rehearsal, mode: 'rehearsal' } : null
})

onMounted(() => events.connect())
onBeforeUnmount(() => events.disconnect())

// Reset returns to the seed screen (FR-O4), and it should be as empty as
// it was the first time.
watch(planted, (now) => {
  if (!now) {
    seed.discard()
  }
})
</script>

<template>
  <div class="shell">
    <WorkspaceView v-if="planted" v-show="!shown" />
    <SeedView v-else v-show="!shown" />
    <DashboardView v-if="shown" :key="shown.id" :solution-id="shown.id" :mode="shown.mode" />

    <!-- Hidden by default, and available on both screens, because the
         sample-seed shortcut is reached from the seed screen (FR-S7). -->
    <OperatorPanel />
  </div>
</template>

<style scoped>
.shell {
  height: 100%;
}
</style>
