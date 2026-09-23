<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'

import RuntimeStage from '../components/RuntimeStage.vue'
import { useDashboardStore } from '../stores/dashboard'
import { useSystemStore } from '../stores/system'

// Loaded when first opened: the charting library is the dashboard's alone,
// and the rest of the interface should not wait for it.
const DashboardView = defineAsyncComponent(() => import('./DashboardView.vue'))

const dashboard = useDashboardStore()
const system = useSystemStore()

/**
 * The Life pane: Agent One VW, what grew out of the Seed (D-14, FR-N6).
 *
 * It holds what was built once the build is done: the ready Agent
 * Components, and the dashboard of whichever one is open (FR-LF1). Until
 * then it says so plainly rather than showing blank space (FR-W4).
 *
 * The pane is never unmounted while the workspace exists, and nor is the
 * component list inside it while a dashboard is open, so returning from a
 * dashboard or from the Seeding pane finds both as they were left
 * (NFR-A7, FR-LF2).
 */
const grown = computed(() => system.phase === 'RUNTIME')

/**
 * Which dashboard is open, if any: the running component's, or one
 * opened from a link for rehearsal, which needs no run to reach (D-3).
 */
const shown = computed<{ id: string; mode: 'running' | 'rehearsal' } | null>(() => {
  if (system.lifecycle === 'RUNNING' && system.runtime.active) {
    return { id: system.runtime.active, mode: 'running' }
  }
  return dashboard.rehearsal ? { id: dashboard.rehearsal, mode: 'rehearsal' } : null
})
</script>

<template>
  <section class="life" aria-label="Life">
    <header class="head">
      <h2 class="title">Agent One VW <span class="mark">(ValueWise™)</span></h2>
    </header>

    <div class="body">
      <div v-show="!shown" class="scroll">
        <RuntimeStage v-if="grown" />
        <div v-else class="empty">
          <p class="empty-title">Nothing is alive yet.</p>
          <p class="empty-note">
            Agent One VW grows out of the Seed. Its Agent Components appear here once
            Implementation completes, each ready to run.
          </p>
        </div>
      </div>

      <DashboardView
        v-if="shown"
        :key="shown.id"
        :solution-id="shown.id"
        :mode="shown.mode"
      />
    </div>
  </section>
</template>

<style scoped>
.life {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  grid-template-columns: minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  background: var(--surface-base);
}

.head {
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
}

.title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.mark {
  color: var(--text-muted);
  font-weight: 400;
}

.body {
  min-width: 0;
  min-height: 0;
}

.body > * {
  height: 100%;
}

.scroll {
  padding: var(--space-6) var(--space-8);
  overflow-y: auto;
}

.empty {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 44ch;
  margin: 18vh auto 0;
  text-align: center;
}

.empty-title {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.empty-note {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}
</style>
