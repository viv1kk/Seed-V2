<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { useEventStore } from '../stores/events'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
const events = useEventStore()

/**
 * A running solution's dashboard (§31, §53).
 *
 * Shown in front of the workspace, never instead of it: the workspace
 * stays mounted underneath (NFR-A3), so returning to it is instant and
 * finds the stream and the build record exactly as they were. Which
 * solution is open is read from System State's runtime, not held here.
 *
 * The analytical views are M9 to M11's work, drawn by one generic renderer
 * from descriptors the backend serves (D-1). Until then this frame states
 * what will be shown and over what, and says plainly that it is not shown
 * yet rather than drawing placeholder charts that could be mistaken for
 * findings.
 */

const active = computed(
  () => system.solutions.find((s) => s.id === system.runtime.active) ?? null,
)
const build = computed(
  () => system.implementations.find((i) => i.id === system.runtime.active) ?? null,
)
const assessment = computed(
  () => system.assessments.find((a) => a.id === active.value?.assessmentId) ?? null,
)

const leaving = ref(false)

async function back(): Promise<void> {
  if (!active.value || leaving.value) {
    return
  }
  leaving.value = true
  try {
    await events.closeSolution(active.value.id)
  } finally {
    leaving.value = false
  }
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && !event.shiftKey) {
    void back()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="dashboard">
    <header class="bar">
      <button type="button" class="back" :disabled="leaving" @click="back">
        <span aria-hidden="true">←</span> Workspace
      </button>
      <div class="identity">
        <h1 class="name">{{ active?.name ?? 'Dashboard' }}</h1>
        <span class="status mono">Running</span>
      </div>
      <span class="lifecycle mono">{{ system.lifecycle }}</span>
    </header>

    <main class="body">
      <section class="frame">
        <p class="purpose">{{ assessment?.purpose ?? active?.description }}</p>

        <dl v-if="build" class="facts">
          <div>
            <dt>Sources</dt>
            <dd>{{ build.sources.map((s) => s.label).join(', ') }}</dd>
          </div>
          <div>
            <dt>Datasets</dt>
            <dd class="mono">{{ build.datasets.length }}</dd>
          </div>
          <div>
            <dt>Feasibility</dt>
            <dd class="mono">{{ assessment?.feasibility ?? '—' }}</dd>
          </div>
          <div>
            <dt>Tests</dt>
            <dd class="mono">{{ build.summary.passed }} of {{ build.summary.total }} passed</dd>
          </div>
        </dl>

        <div class="pending">
          <p class="pending-title">Analytical views are not available in this build yet.</p>
          <p class="pending-note">
            The dashboard for {{ active?.name }} will be drawn here over its analytical dataset,
            with drill-down from each figure to the records and evidence behind it.
          </p>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  background: var(--surface-base);
  animation: enter var(--duration-base) var(--ease-out) both;
}

@keyframes enter {
  from {
    opacity: 0;
  }
}

.bar {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-3) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.back {
  display: inline-flex;
  gap: var(--space-2);
  align-items: baseline;
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.back:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.identity {
  display: flex;
  flex: 1;
  align-items: baseline;
  gap: var(--space-3);
}

.name {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
}

.mono {
  font-family: var(--font-mono);
}

.status {
  color: var(--status-positive);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.lifecycle {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
}

.body {
  min-height: 0;
  padding: var(--space-8);
  overflow-y: auto;
}

.frame {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 72rem;
}

.purpose {
  margin: 0;
  max-width: 70ch;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-8);
  margin: 0;
}

.facts dt {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.facts dd {
  margin: var(--space-1) 0 0;
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.pending {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-10) var(--space-8);
  background: var(--surface-sunken);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
}

.pending-title {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: 600;
}

.pending-note {
  margin: 0;
  max-width: 62ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

@media (prefers-reduced-motion: reduce) {
  .dashboard {
    animation: none;
  }
}
</style>
