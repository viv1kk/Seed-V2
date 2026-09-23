<script setup lang="ts">
import { computed, ref } from 'vue'

import BuildLanes from './BuildLanes.vue'
import { useEventStore } from '../stores/events'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
const events = useEventStore()

/**
 * The Runtime stage: what was built, ready to run (FR-I6, §30, §53).
 *
 * Each ready solution is listed with Run. Running one opens its dashboard;
 * returning brings the viewer back here with every solution still ready,
 * so any of them can be run next (FR-L8). Completion is per solution, not
 * global. The build record stays below, so what was built and how it was
 * tested remains one glance away.
 */

const busy = ref<string | null>(null)

const listed = computed(() =>
  system.solutions.map((solution) => {
    const build = system.implementations.find((i) => i.id === solution.id) ?? null
    const assessment = system.assessments.find((a) => a.id === solution.assessmentId) ?? null
    const withheld =
      build?.tests.filter((t) => t.suite === 'validation' && t.name.startsWith('Withholds'))
        .length ?? 0
    return { solution, build, grade: assessment?.feasibility ?? null, withheld }
  }),
)

const ready = computed(() => system.solutions.filter((s) => s.status === 'READY').length)

/** How often each solution has been run: per-solution completion (FR-L8). */
const runs = computed(() => {
  const counts = new Map<string, number>()
  for (const run of system.runtime.runs) {
    counts.set(run.solutionId, (counts.get(run.solutionId) ?? 0) + 1)
  }
  return counts
})

const STATUS: Partial<Record<string, string>> = {
  READY: 'Ready',
  RUNNING: 'Running',
  REJECTED: 'Rejected',
}

async function run(solutionId: string): Promise<void> {
  busy.value = solutionId
  try {
    await events.runSolution(solutionId)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="runtime">
    <header class="head">
      <h2 class="title">System ready</h2>
      <p class="note">
        {{ ready }} {{ ready === 1 ? 'Agent Component' : 'Agent Components' }} implemented. Run one
        to open its dashboard; return to the workspace to run another.
      </p>
    </header>

    <ul class="list">
      <li
        v-for="item in listed"
        :key="item.solution.id"
        class="item"
        :data-status="item.solution.status"
      >
        <div class="main">
          <h3 class="name">{{ item.solution.name }}</h3>
          <p class="facts mono">
            <template v-if="item.solution.status === 'REJECTED'">
              Rejected at approval. Not implemented.
            </template>
            <template v-else-if="item.build">
              <span>Feasibility {{ item.grade }}</span>
              <span>
                {{ item.build.summary.passed }} of {{ item.build.summary.total }} tests passed
              </span>
              <span v-if="item.withheld">
                {{ item.withheld }} conclusion withheld as insufficient
              </span>
              <span v-if="runs.get(item.solution.id)">
                Run {{ runs.get(item.solution.id) }}×
              </span>
            </template>
          </p>
        </div>
        <span class="status mono">{{ STATUS[item.solution.status] ?? item.solution.status }}</span>
        <button
          v-if="item.solution.status === 'READY'"
          type="button"
          class="action primary"
          :disabled="busy !== null || system.lifecycle !== 'READY_TO_RUN'"
          @click="run(item.solution.id)"
        >
          Run
        </button>
      </li>
    </ul>

    <section v-if="system.implementations.length" class="record">
      <h3 class="section-title">Build record</h3>
      <BuildLanes :implementations="system.implementations" />
    </section>
  </div>
</template>

<style scoped>
.runtime {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.note {
  margin: 0;
  max-width: 70ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.mono {
  font-family: var(--font-mono);
}

.list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-4) var(--space-5);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--status-positive);
  border-radius: var(--radius-md);
}

.item[data-status='REJECTED'] {
  background: var(--surface-base);
  border-left-color: var(--border-default);
}

.main {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.name {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
}

.item[data-status='REJECTED'] .name {
  color: var(--text-muted);
}

.facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.status {
  color: var(--status-positive);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.item[data-status='REJECTED'] .status {
  color: var(--text-muted);
}

.action {
  padding: var(--space-2) var(--space-5);
  color: var(--text-primary);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.action.primary {
  color: var(--text-inverse);
  background: var(--accent);
  border-color: var(--accent);
}

.action.primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.action:disabled {
  opacity: 0.5;
  cursor: default;
}

.section-title {
  margin: 0 0 var(--space-3);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
