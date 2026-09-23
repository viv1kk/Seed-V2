<script setup lang="ts">
import { computed } from 'vue'

import TestResults from './TestResults.vue'
import { secondsOf } from '../design/presentation'
import type { BuildComponent, ComponentStatus, Implementation } from '../stores/system'

const props = defineProps<{
  implementation: Implementation
  expanded: boolean
  /** The component whose tests are singled out, if one was clicked. */
  focus: string | null
}>()

const emit = defineEmits<{ toggle: []; focus: [component: string | null] }>()

/**
 * One solution's build pipeline, as §52 draws it: the data sources on the
 * left feeding six components, each moving through the five states of
 * FR-I2.
 *
 * Hand-built SVG (NFR-L3). Unlike the environment graph, the positions
 * are arithmetic rather than authored: a pipeline is a row, and a row
 * has nothing to lay out. Everything drawn is the implementation record
 * as System State holds it; the lane holds no progress of its own.
 */

const WIDTH = 1000
const HEIGHT = 104
const MID = HEIGHT / 2

const SOURCE_W = 178
const PILL_H = 20
const PILL_GAP = 5

const NODE_X = 224
const NODE_STEP = 132
const NODE_W = 116
const NODE_H = 60

const STAGE_LABELS: Record<BuildComponent['stage'], string> = {
  ingestion: 'Ingestion',
  normalization: 'Normalization',
  analysis: 'Analysis',
  api: 'API',
  dashboard: 'Dashboard',
}

const STATUS_LABELS: Record<ComponentStatus, string> = {
  PENDING: 'Pending',
  BUILDING: 'Building',
  TESTING: 'Testing',
  VALIDATED: 'Validated',
  COMPLETE: 'Complete',
}

const pills = computed(() => {
  const sources = props.implementation.sources
  const height = sources.length * PILL_H + Math.max(0, sources.length - 1) * PILL_GAP
  const top = MID - height / 2
  return sources.map((source, index) => ({
    ...source,
    y: top + index * (PILL_H + PILL_GAP),
    cy: top + index * (PILL_H + PILL_GAP) + PILL_H / 2,
  }))
})

const nodes = computed(() =>
  props.implementation.components.map((component, index) => {
    const unit = props.implementation.tests.filter(
      (t) => t.suite === 'unit' && t.component === component.id,
    )
    const passed = unit.filter((t) => t.status === 'passed').length
    return { ...component, x: NODE_X + index * NODE_STEP, unit: unit.length, passed }
  }),
)

/** Whether this build has begun; a queued lane has nothing to expand. */
const started = computed(() => props.implementation.status !== 'PENDING')

function detail(node: (typeof nodes.value)[number]): string {
  switch (node.status) {
    case 'TESTING':
      return `Testing · ${node.unit} tests`
    case 'VALIDATED':
      return `✓ ${node.passed} of ${node.unit} passed`
    case 'COMPLETE':
      return '✓ Complete'
    default:
      return STATUS_LABELS[node.status]
  }
}

const STATUS_LABEL: Record<Implementation['status'], string> = {
  PENDING: 'Queued',
  BUILDING: 'Building',
  COMPLETE: 'Ready',
}

const summary = computed(() => props.implementation.summary)
const ran = computed(() => props.implementation.tests.filter((t) => t.status !== 'pending').length)

function select(component: string): void {
  emit('focus', props.focus === component ? null : component)
}
</script>

<template>
  <article class="lane" :data-status="implementation.status">
    <header class="head">
      <div class="title-row">
        <h3 class="name">{{ implementation.name }}</h3>
        <span class="status mono">{{ STATUS_LABEL[implementation.status] }}</span>
      </div>
      <span class="scope">
        {{ implementation.datasets.length }} datasets from
        {{ implementation.sources.map((s) => s.label).join(', ') }}
      </span>
      <button
        type="button"
        class="tests mono"
        :aria-expanded="expanded"
        :disabled="!started"
        @click="emit('toggle')"
      >
        <template v-if="ran === 0">{{ summary.total }} tests</template>
        <template v-else>
          {{ summary.passed }} of {{ summary.total }} passed · {{ secondsOf(summary.durationMs) }}
        </template>
        <span class="caret" aria-hidden="true">{{ expanded ? '▴' : '▾' }}</span>
      </button>
    </header>

    <svg
      class="pipeline"
      :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
      role="img"
      :aria-label="`${implementation.name} build pipeline`"
    >
      <defs>
        <marker
          :id="`arrow-${implementation.id}`"
          viewBox="0 0 8 8"
          refX="7"
          refY="4"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M0,0 L8,4 L0,8 z" class="arrowhead" />
        </marker>
      </defs>

      <!-- Sources feed ingestion. -->
      <path
        v-for="pill in pills"
        :key="`feed-${pill.id}`"
        class="edge"
        :data-live="started"
        :d="`M${SOURCE_W},${pill.cy} C${SOURCE_W + 26},${pill.cy} ${NODE_X - 26},${MID} ${NODE_X},${MID}`"
      />

      <!-- Component to component. -->
      <line
        v-for="(node, index) in nodes.slice(1)"
        :key="`edge-${node.id}`"
        class="edge"
        :data-live="node.status !== 'PENDING'"
        :data-flowing="node.status === 'BUILDING'"
        :x1="nodes[index].x + NODE_W"
        :y1="MID"
        :x2="node.x - 3"
        :y2="MID"
        :marker-end="`url(#arrow-${implementation.id})`"
      />

      <g v-for="pill in pills" :key="pill.id" class="source">
        <rect :x="0" :y="pill.y" :width="SOURCE_W" :height="PILL_H" rx="4" />
        <circle :cx="10" :cy="pill.cy" r="3" class="dot" />
        <text :x="20" :y="pill.cy + 4" class="source-label">{{ pill.label }}</text>
      </g>

      <g
        v-for="node in nodes"
        :key="node.id"
        class="node"
        :data-status="node.status"
        :data-focus="focus === node.id"
        role="button"
        tabindex="0"
        :aria-label="`${node.name}: ${STATUS_LABELS[node.status]}`"
        @click="select(node.id)"
        @keydown.enter.prevent="select(node.id)"
      >
        <rect
          class="box"
          :x="node.x"
          :y="MID - NODE_H / 2"
          :width="NODE_W"
          :height="NODE_H"
          rx="5"
        />
        <rect
          v-if="node.status === 'BUILDING' || node.status === 'TESTING'"
          class="progress"
          :x="node.x + 1"
          :y="MID + NODE_H / 2 - 3"
          :width="NODE_W - 2"
          height="2"
        />
        <text :x="node.x + 10" :y="MID - 12" class="kicker">{{ STAGE_LABELS[node.stage] }}</text>
        <text :x="node.x + 10" :y="MID + 4" class="label">{{ node.name }}</text>
        <text :x="node.x + 10" :y="MID + 19" class="detail">{{ detail(node) }}</text>
      </g>
    </svg>

    <TestResults
      v-if="expanded"
      :implementation="implementation"
      :focus="focus"
      @focus="(component) => emit('focus', component)"
    />
  </article>
</template>

<style scoped>
.lane {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: border-color var(--duration-base) var(--ease-out);
}

.lane[data-status='BUILDING'] {
  border-color: var(--accent);
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2) var(--space-4);
}

.title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.name {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
}

.mono {
  font-family: var(--font-mono);
}

.status {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.lane[data-status='BUILDING'] .status {
  color: var(--accent);
}

.lane[data-status='COMPLETE'] .status {
  color: var(--status-positive);
}

.scope {
  flex: 1;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.tests {
  display: inline-flex;
  gap: var(--space-2);
  align-items: baseline;
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.tests:hover:not(:disabled) {
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.tests:disabled {
  opacity: 0.6;
  cursor: default;
}

.caret {
  color: var(--text-muted);
}

.pipeline {
  width: 100%;
  height: auto;
  overflow: visible;
}

/* Edges. Dormant until the component downstream has started. */
.edge {
  fill: none;
  stroke: var(--border-default);
  stroke-width: 1.25;
  stroke-dasharray: 3 4;
  transition: stroke var(--duration-base) var(--ease-out);
}

.edge[data-live='true'] {
  stroke: var(--border-strong);
  stroke-dasharray: none;
}

.edge[data-flowing='true'] {
  stroke: var(--accent);
  stroke-dasharray: 6 4;
  animation: flow 0.9s linear infinite;
}

@keyframes flow {
  to {
    stroke-dashoffset: -20;
  }
}

.arrowhead {
  fill: var(--border-strong);
}

/* Sources: the systems discovery connected, feeding the pipeline. */
.source rect {
  fill: var(--surface-sunken);
  stroke: var(--border-subtle);
}

.source .dot {
  fill: var(--status-positive);
}

.source-label {
  fill: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 11px;
}

/* Components, by FR-I2 state. */
.node {
  cursor: pointer;
  outline: none;
}

.box {
  fill: var(--surface-base);
  stroke: var(--border-default);
  stroke-width: 1.25;
  stroke-dasharray: 4 3;
  transition:
    fill var(--duration-base) var(--ease-out),
    stroke var(--duration-base) var(--ease-out);
}

.kicker {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.label {
  fill: var(--text-muted);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
}

.detail {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 9.5px;
}

.node:not([data-status='PENDING']) .box {
  stroke-dasharray: none;
}

.node:not([data-status='PENDING']) .label {
  fill: var(--text-primary);
}

.node[data-status='BUILDING'] .box {
  fill: var(--accent-subtle);
  stroke: var(--accent);
}

.node[data-status='BUILDING'] .detail {
  fill: var(--accent);
}

.node[data-status='TESTING'] .box {
  fill: var(--surface-raised);
  stroke: var(--accent);
}

.node[data-status='TESTING'] .detail {
  fill: var(--text-secondary);
}

.node[data-status='VALIDATED'] .box {
  fill: var(--surface-raised);
  stroke: var(--status-positive);
}

.node[data-status='VALIDATED'] .detail,
.node[data-status='COMPLETE'] .detail {
  fill: var(--status-positive);
}

.node[data-status='COMPLETE'] .box {
  fill: var(--surface-raised);
  stroke: var(--status-positive);
  stroke-width: 1.5;
}

.node:hover .box,
.node:focus-visible .box,
.node[data-focus='true'] .box {
  stroke-width: 2;
}

.node[data-focus='true'] .box {
  stroke: var(--text-primary);
}

/* An indeterminate sweep while a component is being worked on. */
.progress {
  fill: var(--accent);
  transform-box: fill-box;
  transform-origin: left center;
  animation: sweep 1.1s var(--ease-out) infinite;
}

.node[data-status='TESTING'] .progress {
  fill: var(--text-muted);
}

@keyframes sweep {
  from {
    transform: scaleX(0);
    opacity: 1;
  }
  80% {
    transform: scaleX(1);
    opacity: 1;
  }
  to {
    transform: scaleX(1);
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .edge[data-flowing='true'],
  .progress {
    animation: none;
  }
}
</style>
