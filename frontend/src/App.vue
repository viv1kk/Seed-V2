<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'

import OperatorPanel from './components/OperatorPanel.vue'
import DashboardView from './views/DashboardView.vue'
import SeedView from './views/SeedView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import { useEventStore } from './stores/events'
import { useSeedStore } from './stores/seed'
import { useSystemStore } from './stores/system'

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
    <WorkspaceView v-if="planted" v-show="!running" />
    <SeedView v-else />
    <DashboardView v-if="running" />

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
