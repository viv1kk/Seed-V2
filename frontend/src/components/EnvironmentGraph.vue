<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  DataSource,
  Environment,
  EnvironmentEdge,
  EnvironmentNode,
  NodeKind,
  NodeStatus,
} from '../stores/system'

const props = defineProps<{ environment: Environment }>()

/**
 * The environment graph, hand-built in SVG (NFR-L3).
 *
 * Everything drawn comes from the environment in System State: the nodes
 * discovery has found, where the definition places them (D-4), their
 * status (FR-D4) and the edges between them (FR-D5). There is no layout
 * computed here and no model of the environment kept here, so the graph
 * cannot show anything the system does not know.
 *
 * Colour is status and nothing else, and every colour is a token, so
 * both themes follow from tokens.css.
 */

const byId = computed(() => new Map(props.environment.nodes.map((node) => [node.id, node])))
const sources = computed(
  () => new Map<string, DataSource>(props.environment.dataSources.map((s) => [s.id, s])),
)

/**
 * Each node's entry delay within the burst that revealed it.
 *
 * Nodes arrive in grouped bursts, one per system (OQ-7). A short stagger
 * inside a burst lets the eye read it as a group growing rather than a
 * block switching on. The animation is the appearance itself, which is
 * a real state change (NFR-V5).
 *
 * Nodes already in the snapshot when the graph mounts were not found
 * just now, so they are drawn settled. A reload or a late join shows the
 * environment as it stands rather than replaying its appearance.
 */
const STAGGER_MS = 35
const delays = ref<Record<string, number | null>>({})

watch(
  () => props.environment.nodes.map((node) => node.id),
  (ids, previous) => {
    let position = 0
    const next = { ...delays.value }
    for (const id of ids) {
      if (!(id in next)) {
        next[id] = previous === undefined ? null : position++ * STAGGER_MS
      }
    }
    delays.value = next
  },
  { immediate: true },
)

function entryOf(id: string): Record<string, string> {
  const delay = delays.value[id]
  return delay === null || delay === undefined
    ? { animation: 'none' }
    : { animationDelay: `${delay}ms` }
}

/** Radius or half-size by kind, in canvas units. */
const SIZE: Record<NodeKind, number> = {
  client: 10,
  system: 9,
  service: 7,
  api: 7,
  database: 7,
  dataset: 4.5,
}

function isSurface(kind: NodeKind): boolean {
  return kind === 'service' || kind === 'api' || kind === 'database'
}

interface DrawnEdge {
  edge: EnvironmentEdge
  path: string
  pending: boolean
}

/**
 * Structural edges run left to right as horizontal S-curves. Cross-links
 * join nodes in the same column, so they bow outward to the left, clear
 * of the labels on the right.
 */
function pathOf(from: EnvironmentNode, to: EnvironmentNode): string {
  if (Math.abs(from.x - to.x) < 1) {
    const bow = 28 + Math.abs(to.y - from.y) * 0.18
    const midY = (from.y + to.y) / 2
    return `M ${from.x} ${from.y} Q ${from.x - bow} ${midY} ${to.x} ${to.y}`
  }
  const midX = (from.x + to.x) / 2
  return `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`
}

const edges = computed<DrawnEdge[]>(() =>
  props.environment.edges.flatMap((edge) => {
    const from = byId.value.get(edge.source)
    const to = byId.value.get(edge.target)
    if (!from || !to) {
      return []
    }
    return [{ edge, path: pathOf(from, to), pending: to.status === 'unknown' }]
  }),
)

/** Draw datasets first and the client last, so larger marks sit on top. */
const ORDER: Record<NodeKind, number> = {
  dataset: 0,
  service: 1,
  api: 1,
  database: 1,
  system: 2,
  client: 3,
}

const nodes = computed(() =>
  [...props.environment.nodes].sort((a, b) => ORDER[a.kind] - ORDER[b.kind]),
)

const STATUS_WORDS: Record<NodeStatus, string> = {
  unknown: 'not yet reached',
  detected: 'detected',
  testing: 'testing',
  validated: 'validated',
  'requires-input': 'awaiting input',
  connected: 'connected',
  error: 'error',
}

/** The hover text: what it is, how it stands, and what it carries. */
function titleOf(node: EnvironmentNode): string {
  const lines = [`${node.label} · ${node.kind}`, `Status: ${STATUS_WORDS[node.status]}`]
  if (node.origin === 'administrator-supplied') {
    lines.push('Administrator-supplied')
  }
  if (node.excludedBy) {
    lines.push(`Refused under ${node.excludedBy}`)
  }
  if (node.detail) {
    lines.push(node.detail)
  }
  const source = sources.value.get(node.id)
  for (const field of source?.fields ?? []) {
    lines.push(`${field.name}  ${Math.round(field.completeness * 100)}% complete`)
  }
  return lines.join('\n')
}

/** Whether a halo marks work in progress, a wait, or a fault on this node. */
function hasHalo(status: NodeStatus): boolean {
  return status === 'testing' || status === 'requires-input' || status === 'error'
}
</script>

<template>
  <svg
    class="graph"
    :viewBox="`0 0 ${environment.canvas.width} ${environment.canvas.height}`"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    :aria-label="`${environment.client} environment graph`"
  >
    <g class="edges">
      <path
        v-for="drawn in edges"
        :key="drawn.edge.id"
        class="edge"
        :data-kind="drawn.edge.kind"
        :data-pending="drawn.pending"
        :d="drawn.path"
      >
        <title v-if="drawn.edge.detail">{{ drawn.edge.detail }}</title>
      </path>
    </g>

    <g
      v-for="node in nodes"
      :key="node.id"
      class="node"
      :data-kind="node.kind"
      :data-status="node.status"
      :data-origin="node.origin"
      :data-excluded="node.excludedBy !== null"
      :style="entryOf(node.id)"
    >
      <title>{{ titleOf(node) }}</title>

      <circle
        v-if="hasHalo(node.status)"
        class="halo"
        :cx="node.x"
        :cy="node.y"
        :r="SIZE[node.kind] + 5"
      />

      <circle
        v-if="node.kind === 'system' || node.kind === 'dataset'"
        class="mark"
        :cx="node.x"
        :cy="node.y"
        :r="SIZE[node.kind]"
      />
      <rect
        v-else
        class="mark"
        :x="node.x - SIZE[node.kind]"
        :y="node.y - SIZE[node.kind]"
        :width="SIZE[node.kind] * 2"
        :height="SIZE[node.kind] * 2"
        :rx="node.kind === 'service' ? 4.5 : node.kind === 'client' ? 3 : 1.5"
      />

      <!-- Datasets are labelled to the right, where nothing else is drawn.
           Everything else is labelled above, clear of its edges. -->
      <text v-if="node.kind === 'dataset'" class="label" :x="node.x + 11" :y="node.y + 4">
        <tspan class="name">{{ node.label }}</tspan>
        <tspan v-if="node.excludedBy" class="tag" dx="8">refused · {{ node.excludedBy }}</tspan>
        <tspan v-else-if="node.origin === 'administrator-supplied'" class="tag" dx="8"
          >admin supplied</tspan
        >
      </text>
      <text
        v-else-if="node.kind === 'client'"
        class="label strong"
        :x="node.x"
        :y="node.y + 28"
        text-anchor="middle"
      >
        {{ node.label }}
      </text>
      <text
        v-else
        class="label"
        :class="{ strong: node.kind === 'system' }"
        :x="node.x"
        :y="node.y - (SIZE[node.kind] + 8)"
        text-anchor="middle"
      >
        {{ node.label }}
        <tspan v-if="isSurface(node.kind)" class="tag" dx="5">{{ node.kind }}</tspan>
      </text>
    </g>
  </svg>
</template>

<style scoped>
.graph {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  font-family: var(--font-sans);
}

/* -- Edges ------------------------------------------------------------ */

.edge {
  fill: none;
  stroke: var(--border-default);
  stroke-width: 1;
  transition: stroke var(--duration-base) var(--ease-out);
}

.edge[data-kind='contains'] {
  stroke: var(--border-strong);
}

.edge[data-kind='connects_to'] {
  stroke: var(--text-muted);
  stroke-dasharray: 5 3;
}

.edge[data-kind='depends_on'] {
  stroke: var(--text-muted);
  stroke-dasharray: 1 3;
  stroke-linecap: round;
  stroke-width: 1.4;
}

/* An edge to a system not yet reached is a declaration, not a finding. */
.edge[data-pending='true'] {
  stroke: var(--border-default);
  stroke-dasharray: 2 4;
}

/* -- Nodes ------------------------------------------------------------ */

.node {
  animation: appear var(--duration-slow) var(--ease-out) both;
}

@keyframes appear {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.mark {
  fill: var(--surface-raised);
  stroke: var(--border-strong);
  stroke-width: 1.5;
  transition:
    fill var(--duration-base) var(--ease-out),
    stroke var(--duration-base) var(--ease-out);
}

.halo {
  fill: none;
  stroke-width: 1;
  opacity: 0.6;
}

.label {
  fill: var(--text-secondary);
  font-size: 11px;
  transition: fill var(--duration-base) var(--ease-out);
}

.label.strong {
  fill: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
}

.node[data-kind='dataset'] .label {
  font-family: var(--font-mono);
  font-size: 10.5px;
}

.tag {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 400;
  letter-spacing: 0.04em;
}

/* Status. One hue per meaning, taken from the semantic status tokens.
   Waiting on a person uses the accent, as every human decision does in
   this interface; only a fault is drawn in the negative colour (FR-H4). */

.node[data-status='unknown'] .mark {
  fill: var(--surface-base);
  stroke: var(--border-default);
  stroke-dasharray: 2 2;
}

.node[data-status='unknown'] .label {
  fill: var(--text-muted);
}

.node[data-status='testing'] .mark {
  stroke: var(--text-secondary);
}

.node[data-status='testing'] .halo {
  stroke: var(--text-muted);
  stroke-dasharray: 2 3;
}

.node[data-status='validated'] .mark {
  stroke: var(--status-positive);
}

.node[data-status='connected'] .mark {
  fill: var(--status-positive);
  stroke: var(--status-positive);
}

.node[data-status='requires-input'] .mark {
  fill: var(--accent-subtle);
  stroke: var(--accent);
}

.node[data-status='requires-input'] .halo {
  stroke: var(--accent);
}

.node[data-status='error'] .mark {
  fill: var(--surface-raised);
  stroke: var(--status-negative);
}

.node[data-status='error'] .halo {
  stroke: var(--status-negative);
}

.node[data-status='error'] .label {
  fill: var(--status-negative);
}

/* Supplied by a person rather than found: drawn as a broken outline, so
   the graph does not claim to have discovered it (FR-D6). */
.node[data-origin='administrator-supplied'] .mark {
  stroke-dasharray: 3 2;
}

/* Found, and refused by policy. Present, because it was found; muted,
   because nothing will be read from it. Not an error (FR-P4). */
.node[data-excluded='true'] .mark {
  fill: var(--surface-base);
  stroke: var(--border-default);
}

.node[data-excluded='true'] .label {
  fill: var(--text-muted);
}

.node[data-excluded='true'] .name {
  text-decoration: line-through;
}

.node[data-excluded='true'] .tag {
  fill: var(--status-warning);
}

@media (prefers-reduced-motion: reduce) {
  .node {
    animation: none;
  }
}
</style>
