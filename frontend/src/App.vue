<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'

import LayoutControl from './components/LayoutControl.vue'
import OperatorPanel from './components/OperatorPanel.vue'
import LifeView from './views/LifeView.vue'
import SeedView from './views/SeedView.vue'
import WorkspaceView from './views/WorkspaceView.vue'
import { useDashboardStore } from './stores/dashboard'
import { useEventStore } from './stores/events'
import { useLayoutStore } from './stores/layout'
import { useSeedStore } from './stores/seed'
import { useSystemStore } from './stores/system'

const dashboard = useDashboardStore()
const events = useEventStore()
const layout = useLayoutStore()
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
 * The seed screen is full-screen until the seed is planted (FR-W7): it is
 * the act of planting, and half a screen beside an empty pane would
 * weaken it. The one exception is a rehearsal link, which opens its
 * dashboard in Life without a run (FR-W6, D-3).
 */
const workspace = computed(() => planted.value || dashboard.rehearsal !== null)

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
    <!-- Two panes under one bar, both mounted for the whole run (D-14,
         NFR-A7). The layout hides a pane and never unmounts it, so the
         stream keeps its scroll and a dashboard its filter context. -->
    <div v-if="workspace" class="frame">
      <!-- No transport bar. The chrome carries identity and the layout,
           and nothing an audience should not see (FR-O2). -->
      <header class="bar">
        <div class="identity">
          <span class="name">Seed</span>
          <span class="version mono">V1</span>
        </div>

        <LayoutControl :disabled="!planted" />

        <span class="lifecycle mono">{{ system.lifecycle }}</span>
      </header>

      <div class="panes" :data-layout="layout.layout">
        <WorkspaceView v-if="planted" v-show="layout.seeding" class="region" />
        <LifeView v-show="layout.life || !planted" class="region" />
      </div>
    </div>
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

.frame {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  background: var(--surface-base);
}

.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
  padding: var(--space-3) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.identity {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.name {
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.version,
.lifecycle {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.lifecycle {
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.mono {
  font-family: var(--font-mono);
}

.panes {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: 0;
}

.panes[data-layout='both'] {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.panes[data-layout='both'] > .region + .region {
  border-left: 1px solid var(--border-default);
}

.region {
  min-height: 0;
}

@media (max-width: 64rem) {
  .panes[data-layout='both'] {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
  }

  .panes[data-layout='both'] > .region + .region {
    border-left: none;
    border-top: 1px solid var(--border-default);
  }
}
</style>
