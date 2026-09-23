<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import ChartCard from '../components/dashboard/ChartCard.vue'
import DataTable from '../components/dashboard/DataTable.vue'
import DrillBar from '../components/dashboard/DrillBar.vue'
import EvidencePanel from '../components/dashboard/EvidencePanel.vue'
import KpiTile from '../components/dashboard/KpiTile.vue'
import {
  useDashboardStore,
  type ChartSpec,
  type KpiResult,
  type KpiSpec,
  type RecordsResult,
  type SeriesChartResult,
  type Step,
  type SummaryResult,
  type TableSpec,
  type TreemapResult,
} from '../stores/dashboard'
import { useEventStore } from '../stores/events'

const props = defineProps<{
  solutionId: string
  /** Opened by Run, or straight from a link for rehearsal (D-3). */
  mode: 'running' | 'rehearsal'
}>()

/**
 * The one dashboard renderer (D-1).
 *
 * It draws whatever descriptor the backend serves: the bands it declares,
 * in order, each view by its mark. Every dashboard is a descriptor, not a
 * component, the deepest one included. Nothing in this file or the
 * components it uses names a methodology, a dimension or a measure, and a
 * test holds that.
 *
 * It is shown in front of the workspace, which stays mounted underneath
 * (NFR-A3), so returning finds the workspace exactly as it was left.
 */
const dashboard = useDashboardStore()
const events = useEventStore()

const evidenceOpen = ref(false)
const leaving = ref(false)

watch(
  () => props.solutionId,
  (id) => {
    evidenceOpen.value = false
    void dashboard.open(id)
  },
  { immediate: true },
)

onBeforeUnmount(() => dashboard.close())

const descriptor = computed(() => dashboard.descriptor)

function kpi(id: string): KpiSpec | undefined {
  return descriptor.value?.kpis.find((k) => k.id === id)
}

function chart(id: string): ChartSpec | undefined {
  return descriptor.value?.charts.find((c) => c.id === id)
}

function table(id: string): TableSpec | undefined {
  return descriptor.value?.tables.find((t) => t.id === id)
}

function result<T>(id: string): T | undefined {
  return dashboard.results[id] as T | undefined
}

function apply(step: Step): void {
  dashboard.apply(step)
  if (step.entityId) evidenceOpen.value = true
}

function showRecords(): void {
  const section = descriptor.value?.sections.find((s) =>
    s.views.some((v) => table(v)?.kind === 'records'),
  )
  if (section) document.getElementById(`section-${section.id}`)?.scrollIntoView({ behavior: 'smooth' })
}

async function back(): Promise<void> {
  if (leaving.value) return
  leaving.value = true
  try {
    if (props.mode === 'running') {
      await events.closeSolution(props.solutionId)
    } else {
      dashboard.close()
    }
  } finally {
    leaving.value = false
  }
}
</script>

<template>
  <div class="dashboard">
    <header class="bar">
      <button type="button" class="back" :disabled="leaving" @click="back">
        <span aria-hidden="true">←</span> Workspace
      </button>
      <div class="identity">
        <h1 class="name">{{ descriptor?.title ?? 'Dashboard' }}</h1>
        <span class="status mono" :data-mode="mode">{{
          mode === 'running' ? 'Running' : 'Rehearsal'
        }}</span>
      </div>
      <p v-if="descriptor" class="subtitle">{{ descriptor.subtitle }}</p>
    </header>

    <DrillBar @evidence="evidenceOpen = !evidenceOpen" />

    <div class="stage">
      <main class="body">
        <p v-if="dashboard.error" class="error">{{ dashboard.error }}</p>
        <template v-if="descriptor">
          <section
            v-for="section in descriptor.sections"
            :id="`section-${section.id}`"
            :key="section.id"
            class="section"
            :data-kind="section.kind"
          >
            <h2 v-if="section.title" class="section-title">{{ section.title }}</h2>

            <div v-if="section.kind === 'kpis'" class="kpis">
              <template v-for="id in section.views" :key="id">
                <KpiTile v-if="kpi(id)" :kpi="kpi(id)!" :result="result<KpiResult>(id)" />
              </template>
            </div>

            <div v-else class="grid">
              <template v-for="id in section.views" :key="id">
                <ChartCard
                  v-if="chart(id)"
                  :chart="chart(id)!"
                  :result="result<SeriesChartResult | TreemapResult>(id)"
                  @apply="apply"
                />
                <DataTable
                  v-else-if="table(id)"
                  :table="table(id)!"
                  :result="result<SummaryResult | RecordsResult>(id)"
                  @apply="apply"
                />
              </template>
            </div>
          </section>
          <p v-if="descriptor.simulated" class="simulated">
            Every figure is aggregated from the records of a simulated demo dataset at the moment
            it is shown. None is typed in.
          </p>
        </template>
      </main>

      <EvidencePanel
        v-if="evidenceOpen"
        @close="evidenceOpen = false"
        @apply="apply"
        @records="showRecords"
      />
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
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
  white-space: nowrap;
}

.back:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.identity {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  white-space: nowrap;
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

.status[data-mode='rehearsal'] {
  color: var(--text-muted);
}

.subtitle {
  margin: 0;
  overflow: hidden;
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage {
  position: relative;
  min-height: 0;
}

.body {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  height: 100%;
  padding: var(--space-5) var(--space-6) var(--space-8);
  overflow-y: auto;
}

.section-title {
  margin: 0 0 var(--space-3);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: var(--space-4);
}

.grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--space-4);
}

.error {
  margin: 0;
  color: var(--status-negative);
  font-size: var(--text-xs);
}

.simulated {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
}

@media (max-width: 64rem) {
  .grid > * {
    grid-column: span 12 !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  .dashboard {
    animation: none;
  }
}
</style>
