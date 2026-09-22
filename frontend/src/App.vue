<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'

import OperatorPanel from './components/OperatorPanel.vue'
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
    <WorkspaceView v-if="planted" />
    <SeedView v-else />

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
