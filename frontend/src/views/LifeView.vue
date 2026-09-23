<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'

import GrowthTree from '../components/GrowthTree.vue'
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
 * While seeding is under way it shows the seed growing, following the
 * process as it advances (D-18). When the build completes, the tree gives
 * way to what it grew: Agent One VW, its ready Agent Components, and the
 * dashboard of whichever one is open (FR-LF1).
 *
 * After the hand-over the tree stays one click away: the header's Growth
 * control drops it open above Agent One VW (D-19).
 *
 * The pane is never unmounted while the workspace exists, and nor is the
 * component list inside it while a dashboard is open, so returning from a
 * dashboard or from the Seeding pane finds both as they were left
 * (NFR-A7, FR-LF2).
 */
const grown = computed(() => system.phase === 'RUNTIME')

/** The build is done: the hand-over from the growing tree to Agent One VW. */
const complete = computed(() =>
  ['IMPLEMENTATION_COMPLETE', 'READY_TO_RUN', 'RUNNING'].includes(system.lifecycle),
)

/** Seeding is under way: the seed is planted and the build is not done. */
const growing = computed(() => system.lifecycle !== 'UNINITIALIZED' && !complete.value)

const ready = computed(() => system.solutions.filter((s) => s.status !== 'REJECTED').length)

/**
 * Whether the grown tree is open above Agent One VW.
 *
 * After the hand-over the tree is not gone: the header keeps a Growth
 * control that drops it open again, fully grown, drawn from the same log.
 * Closed by default, so Agent One VW is what the pane leads with. A new
 * run starts closed again.
 */
const treeOpen = ref(false)
watch(complete, (now) => {
  if (!now) treeOpen.value = false
})

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
      <span v-if="growing" class="state mono">Growing</span>
      <button
        v-if="complete"
        type="button"
        class="growth-toggle"
        :aria-expanded="treeOpen"
        aria-controls="life-growth"
        @click="treeOpen = !treeOpen"
      >
        Growth
        <span class="chevron" aria-hidden="true">{{ treeOpen ? '▴' : '▾' }}</span>
      </button>
    </header>

    <div class="body">
      <!-- The grown tree, dropped open from the header after the hand-over.
           It covers the whole pane, over Agent One VW rather than in place
           of it: what lies beneath stays mounted, so a dashboard keeps its
           filter context while the tree is open (NFR-A7). -->
      <Transition name="drop">
        <div v-if="complete && treeOpen" id="life-growth" class="growth">
          <GrowthTree />
        </div>
      </Transition>

      <div v-show="!shown" class="holder">
        <!-- The seed growing while seeding runs, then the hand-over to what
             it grew. One gives way to the other (D-18). -->
        <Transition name="handover" mode="out-in">
          <GrowthTree v-if="growing" key="growing" />
          <div v-else-if="complete" key="grown" class="scroll">
            <header class="grown">
              <p class="eyebrow mono">Seeding complete</p>
              <h3 class="grown-title">Agent One VW <span class="mark">(ValueWise™)</span></h3>
              <p class="grown-note">
                Grown out of the Seed: {{ ready }}
                {{ ready === 1 ? 'Agent Component' : 'Agent Components' }}, built, tested and
                validated against the evidence each was approved on.
              </p>
            </header>
            <RuntimeStage v-if="grown" />
          </div>
        </Transition>
      </div>

      <DashboardView v-if="shown" :key="shown.id" :solution-id="shown.id" :mode="shown.mode" />
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
  display: flex;
  align-items: baseline;
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
  position: relative;
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

.holder {
  min-height: 0;
}

.holder > * {
  height: 100%;
}

.state {
  margin-left: var(--space-3);
  color: var(--growth-leaf);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.mono {
  font-family: var(--font-mono);
}

.growth-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  transition:
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.growth-toggle:hover,
.growth-toggle[aria-expanded='true'] {
  color: var(--text-primary);
  border-color: var(--growth-leaf);
}

.chevron {
  font-size: 0.7em;
}

.growth {
  position: absolute;
  inset: 0;
  z-index: 2;
  overflow: hidden;
  background: var(--surface-base);
}

/* It drops down from the header, revealed top first. */
.drop-enter-active,
.drop-leave-active {
  transition:
    clip-path var(--duration-slow) var(--ease-out),
    opacity var(--duration-slow) var(--ease-out);
}

.drop-enter-from,
.drop-leave-to {
  clip-path: inset(0 0 100% 0);
  opacity: 0;
}

.grown {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}

.eyebrow {
  margin: 0;
  color: var(--status-positive);
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.grown-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
}

.grown-note {
  margin: 0;
  max-width: 62ch;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

/* The hand-over: the tree fades as Agent One VW arrives. */
.handover-enter-active,
.handover-leave-active {
  transition:
    opacity 600ms var(--ease-out),
    transform 600ms var(--ease-out);
}

.handover-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.handover-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .handover-enter-active,
  .handover-leave-active,
  .drop-enter-active,
  .drop-leave-active {
    transition: none;
  }
}
</style>
