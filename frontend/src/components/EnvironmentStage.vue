<script setup lang="ts">
import { computed } from 'vue'

import EnvironmentGraph from './EnvironmentGraph.vue'
import type { EdgeKind, Environment, NodeStatus } from '../stores/system'

const props = defineProps<{ environment: Environment | null }>()

/**
 * The Discovery stage: the environment graph, and what it adds up to.
 *
 * Every figure here is read from the summary the backend computes from
 * the constructed graph each time it changes (FR-D9). None is counted in
 * the browser and none is written anywhere by hand, so the numbers climb
 * as bursts arrive and stop where the graph stops.
 */
const summary = computed(() => props.environment?.summary ?? null)
const complete = computed(() => props.environment?.complete ?? false)

/** The legend is the vocabulary of FR-D4 and FR-D5, in reading order. */
const STATUSES: { status: NodeStatus; label: string }[] = [
  { status: 'unknown', label: 'Not yet reached' },
  { status: 'detected', label: 'Detected' },
  { status: 'testing', label: 'Testing' },
  { status: 'requires-input', label: 'Awaiting input' },
  { status: 'error', label: 'Error' },
  { status: 'validated', label: 'Validated' },
  { status: 'connected', label: 'Connected' },
]

const EDGES: { kind: EdgeKind; label: string }[] = [
  { kind: 'contains', label: 'contains' },
  { kind: 'provides', label: 'provides' },
  { kind: 'connects_to', label: 'connects to' },
  { kind: 'depends_on', label: 'depends on' },
]

/**
 * How each system stands at completion (FR-D10), in §19's terms. An
 * administrator-supplied source is not "connected": nothing connected to
 * it. Saying so is the point of FR-D6.
 */
function standingOf(entry: { status: NodeStatus; origin: string }): {
  label: string
  tone: 'positive' | 'caution' | 'neutral'
} {
  if (entry.origin === 'administrator-supplied') {
    return { label: 'Admin supplied', tone: 'caution' }
  }
  if (entry.status === 'connected') {
    return { label: 'Connected', tone: 'positive' }
  }
  return { label: entry.status, tone: 'neutral' }
}
</script>

<template>
  <div class="environment">
    <header class="head">
      <h2 class="title">Environment</h2>
      <span v-if="environment" class="client mono">{{ environment.client }}</span>
    </header>

    <div class="body">
      <div class="canvas">
        <EnvironmentGraph v-if="environment" :environment="environment" />
        <p v-else class="empty">Waiting for discovery to read the source inventory.</p>
      </div>

      <aside class="side">
        <!-- Live counts, computed from the graph as it stands. -->
        <dl v-if="summary" class="counts">
          <div class="count">
            <dt>Systems</dt>
            <dd>
              <span class="figure">{{ summary.systems }}</span>
              <span class="of">of {{ summary.declaredSystems }} declared</span>
            </dd>
          </div>
          <div class="count">
            <dt>Data sources</dt>
            <dd><span class="figure">{{ summary.dataSources }}</span></dd>
          </div>
          <div class="count">
            <dt>Datasets</dt>
            <dd>
              <span class="figure">{{ summary.datasets }}</span>
              <span class="of">
                {{ summary.profiled }} profiled<template v-if="summary.excluded"
                  >, {{ summary.excluded }} refused</template
                >
              </span>
            </dd>
          </div>
        </dl>

        <!-- FR-D10, once discovery has finished. -->
        <section v-if="complete && summary" class="report">
          <h3 class="report-title">Discovery complete</h3>

          <ul class="standing">
            <li v-for="entry in summary.bySystem" :key="entry.id" class="standing-row">
              <span class="standing-name">{{ entry.label }}</span>
              <span class="standing-state" :data-tone="standingOf(entry).tone">
                {{ standingOf(entry).label }}
              </span>
            </li>
          </ul>

          <h3 class="report-title">Methodologies</h3>
          <ul class="methodologies">
            <li
              v-for="methodology in summary.methodologies"
              :key="methodology.id"
              class="methodology"
              :data-feasible="methodology.appearsFeasible"
            >
              <span class="methodology-name">{{ methodology.name }}</span>
              <span class="methodology-evidence mono">
                evidence {{ methodology.located }}/{{ methodology.required }}
              </span>
              <span class="methodology-verdict">
                {{ methodology.appearsFeasible ? 'Appears feasible' : 'Evidence missing' }}
              </span>
            </li>
          </ul>
          <p class="note">Feasibility is graded in assessment, against field completeness.</p>
        </section>

        <section class="legend" aria-label="Legend">
          <ul class="legend-list">
            <li v-for="item in STATUSES" :key="item.status" class="legend-item">
              <svg class="swatch" viewBox="0 0 12 12" aria-hidden="true">
                <circle class="swatch-mark" :data-status="item.status" cx="6" cy="6" r="4" />
              </svg>
              {{ item.label }}
            </li>
          </ul>
          <ul class="legend-list">
            <li v-for="item in EDGES" :key="item.kind" class="legend-item">
              <svg class="swatch wide" viewBox="0 0 20 12" aria-hidden="true">
                <line class="swatch-edge" :data-kind="item.kind" x1="1" y1="6" x2="19" y2="6" />
              </svg>
              {{ item.label }}
            </li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.environment {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
}

.head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.client {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.mono {
  font-family: var(--font-mono);
}

.body {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1fr) 15rem;
  gap: var(--space-6);
  min-height: 0;
}

.canvas {
  min-width: 0;
  min-height: 0;
}

.empty {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.side {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-height: 0;
  overflow-y: auto;
}

/* -- Counts ----------------------------------------------------------- */

.counts {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
}

.count dt {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.count dd {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin: var(--space-1) 0 0;
}

.figure {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xl);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.of {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* -- Completion report ------------------------------------------------ */

.report {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-subtle);
  animation: settle var(--duration-slow) var(--ease-out) both;
}

@keyframes settle {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.report-title {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.standing,
.methodologies,
.legend-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.standing-row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: var(--text-xs);
}

.standing-name {
  color: var(--text-primary);
}

.standing-state {
  color: var(--text-muted);
  white-space: nowrap;
}

.standing-state[data-tone='positive'] {
  color: var(--status-positive);
}

.standing-state[data-tone='caution'] {
  color: var(--status-warning);
}

.methodology {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0 var(--space-2);
  font-size: var(--text-xs);
}

.methodology-name {
  grid-column: 1 / -1;
  color: var(--text-primary);
}

.methodology-evidence {
  color: var(--text-muted);
}

.methodology-verdict {
  color: var(--status-positive);
  text-align: right;
}

.methodology[data-feasible='false'] .methodology-verdict {
  color: var(--status-neutral);
}

.note {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
}

/* -- Legend ------------------------------------------------------------ */

.legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
  margin-top: auto;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-subtle);
}

.legend-list {
  gap: var(--space-1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.swatch {
  flex: none;
  width: 12px;
  height: 12px;
}

.swatch.wide {
  width: 20px;
}

/* The same token mapping as the graph, so the key cannot disagree with
   what it explains. */
.swatch-mark {
  fill: var(--surface-raised);
  stroke: var(--border-strong);
  stroke-width: 1.5;
}

.swatch-mark[data-status='unknown'] {
  fill: var(--surface-base);
  stroke: var(--border-default);
  stroke-dasharray: 2 2;
}

.swatch-mark[data-status='testing'] {
  stroke: var(--text-secondary);
}

.swatch-mark[data-status='requires-input'] {
  fill: var(--accent-subtle);
  stroke: var(--accent);
}

.swatch-mark[data-status='error'] {
  stroke: var(--status-negative);
}

.swatch-mark[data-status='validated'] {
  stroke: var(--status-positive);
}

.swatch-mark[data-status='connected'] {
  fill: var(--status-positive);
  stroke: var(--status-positive);
}

.swatch-edge {
  stroke: var(--border-default);
  stroke-width: 1.5;
}

.swatch-edge[data-kind='contains'] {
  stroke: var(--border-strong);
}

.swatch-edge[data-kind='connects_to'] {
  stroke: var(--text-muted);
  stroke-dasharray: 5 3;
}

.swatch-edge[data-kind='depends_on'] {
  stroke: var(--text-muted);
  stroke-dasharray: 1 3;
  stroke-linecap: round;
}

@media (max-width: 80rem) {
  .body {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(16rem, 1fr) auto;
  }

  .legend {
    margin-top: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .report {
    animation: none;
  }
}
</style>
