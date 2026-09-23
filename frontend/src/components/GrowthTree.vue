<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import { PHASE_LABELS } from '../design/presentation'
import { growthOf, phaseStateOf, type Grown } from '../design/growth'
import { useEventStore } from '../stores/events'
import { PHASE_ORDER, type Phase } from '../stores/system'

const events = useEventStore()

/**
 * The growth tree: the Seeding pane's progress indicator (D-15, FR-G1).
 *
 * It replaces the lifecycle strip and carries the same information:
 * every phase is labelled, and each reads as complete, current or
 * future. What it adds is how the phase is going. The seed's layers are
 * its roots, each system reached and each methodology assessed is a
 * leaf, each Agent Component built is a branch, and the tree flowers when
 * Agent One VW is ready to run (FR-G2).
 *
 * It is watered by tool requests: every capability request the
 * protection engine evaluates is one drop (FR-G3). An allowed request
 * soaks into the soil. A refused one stops above the ground and stays
 * there, a request that did not feed the system. Nothing here stands for
 * a model call, because none occurs (FR-G4, NFR-D1).
 *
 * Everything drawn is `growthOf(events)`, a pure function of the event
 * log, so a tree rebuilt from a replay is the tree that grew live (FR-G5).
 */
const growth = computed(() => growthOf(events.events))

// -- Geometry, hand-authored (FR-G6) -----------------------------------

const STEM_Y = 52
const END_X = 930

/** Each phase's stretch of stem, left to right. */
const SECTIONS: Record<Phase, [number, number]> = {
  INIT: [52, 170],
  DISCOVERY: [170, 420],
  ASSESSMENT: [420, 560],
  IMPLEMENTATION: [560, 860],
  RUNTIME: [860, END_X],
}

const LABEL_X: Record<Phase, number> = {
  INIT: 89,
  DISCOVERY: 295,
  ASSESSMENT: 490,
  IMPLEMENTATION: 710,
  RUNTIME: 895,
}

const systemX = (i: number) => 200 + i * 44
const assessmentX = (i: number) => 450 + i * 40
const branchX = (i: number) => 590 + i * 90

/** The stem, from the seed up and along; normalised to 1000 units. */
const STEM_PATH = `M52 76 C52 64 56 54 70 ${STEM_Y} L${END_X} ${STEM_Y}`
const CURVE_LENGTH = 32
const STEM_LENGTH = CURVE_LENGTH + (END_X - 70)

/** How far along the stem the tree has grown, as an x on the stem. */
const frontier = computed(() => {
  const g = growth.value
  const current = g.phase
  if (current === null) return 52
  let x = 52
  for (const phase of PHASE_ORDER) {
    const state = phaseStateOf(phase, current)
    const [start, end] = SECTIONS[phase]
    if (state === 'complete') {
      x = end
    } else if (state === 'current') {
      const tips: number[] = []
      if (phase === 'INIT') tips.push(g.sprouted ? 110 : 60)
      if (phase === 'DISCOVERY') tips.push(...g.systems.map((_, i) => systemX(i) + 14))
      if (phase === 'ASSESSMENT') tips.push(...g.assessments.map((_, i) => assessmentX(i) + 14))
      if (phase === 'IMPLEMENTATION') tips.push(...g.branches.map((_, i) => branchX(i) + 20))
      if (phase === 'RUNTIME') tips.push(g.bloom ? END_X : start + 20)
      x = Math.max(start + 12, ...tips)
      x = Math.min(x, end)
    }
  }
  return x
})

const grownOffset = computed(() => {
  const x = frontier.value
  const along = x <= 70 ? (Math.max(0, x - 52) / 18) * CURVE_LENGTH : CURVE_LENGTH + (x - 70)
  return 1000 - (Math.min(along, STEM_LENGTH) / STEM_LENGTH) * 1000
})

/** A leaf on the stem, alternating above and below. */
function stemLeaf(x: number, index: number): string {
  return index % 2 === 0
    ? `M${x} ${STEM_Y} q4 -12 14 -14 q-2 10 -14 14 z`
    : `M${x} ${STEM_Y} q4 12 14 14 q-2 -10 -14 -14 z`
}

/** A branch rising from the stem, and points along it for its leaves. */
function branchPath(x: number): string {
  return `M${x} ${STEM_Y} Q${x + 14} 30 ${x + 60} 20`
}

function branchPoint(x: number, t: number): [number, number] {
  const u = 1 - t
  return [u * u * x + 2 * u * t * (x + 14) + t * t * (x + 60), u * u * STEM_Y + 2 * u * t * 30 + t * t * 20]
}

function branchLeaf(x: number, index: number): string {
  const [px, py] = branchPoint(x, (index + 1) / 7)
  return index % 2 === 0
    ? `M${px} ${py} q-2 -8 4 -12 q2 7 -4 12 z`
    : `M${px} ${py} q8 -1 11 4 q-7 2 -11 -4 z`
}

const ROOTS = ['M52 78 q-6 6 -18 10', 'M52 78 q2 8 -2 13', 'M52 78 q8 6 22 9']

/** Allowed and escalated requests soak in; each is one dot of water. */
const absorbed = computed(() =>
  growth.value.waterings
    .filter((w) => w.effect !== 'DENY')
    .map((w, i) => ({ ...w, x: 84 + (i % 14) * 5.5, y: 76 + Math.min(Math.floor(i / 14), 3) * 5 })),
)

/** Refused requests stop above the ground and stay visible there. */
const refused = computed(() =>
  growth.value.waterings.filter((w) => w.effect === 'DENY').map((w, i) => ({ ...w, x: 132 + i * 12 })),
)

const phases = computed(() =>
  PHASE_ORDER.map((phase) => ({
    phase,
    label: PHASE_LABELS[phase],
    x: LABEL_X[phase],
    state: phaseStateOf(phase, growth.value.phase),
  })),
)

// -- Motion (NFR-V7) ----------------------------------------------------

/**
 * Which grown elements may animate as they appear.
 *
 * Only an event that arrives on its own, after a pause, animates. A
 * replay on connect, a resync, or a run at instant speed delivers events
 * in a burst, and those simply appear in their final state, so nothing
 * strobes. Reduced motion turns every animation off in CSS. The final
 * state is the same either way: motion only ever decides how an element
 * arrives, never what is drawn.
 */
const CALM_GAP_MS = 250
const moving = reactive(new Set<number>())
let primed = false
let lastArrival = 0

watch(
  () => events.events.length,
  (length, previous) => {
    const before = previous ?? 0
    if (length < before) {
      moving.clear()
      primed = false
      return
    }
    const now = performance.now()
    const fresh = events.events.slice(before)
    const calm = primed && fresh.length === 1 && now - lastArrival >= CALM_GAP_MS
    lastArrival = now
    primed = true
    moving.clear()
    if (calm && fresh[0]) moving.add(fresh[0].sequence)
  },
  { immediate: true },
)

const isNew = (item: Grown | { sequence: number }) => moving.has(item.sequence)
const motion = computed(() => moving.size > 0)

const latestWatering = computed(() => {
  const all = growth.value.waterings
  const last = all[all.length - 1]
  return last && moving.has(last.sequence) ? last : null
})

const watered = computed(() => growth.value.waterings.filter((w) => w.effect !== 'DENY').length)
</script>

<template>
  <figure class="tree" aria-label="Growth">
    <svg
      viewBox="0 0 1000 116"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      :data-motion="motion"
      :aria-label="`Lifecycle: ${phases.find((p) => p.state === 'current')?.label ?? 'not started'}`"
    >
      <title>
        Growth of the seed. Watered by tool requests the protection engine evaluated; no model
        calls occur.
      </title>

      <!-- Watering tally: what fed the tree, and what did not (FR-G3, FR-G4). -->
      <text class="tally" x="14" y="14">
        Watered by {{ watered }} tool {{ watered === 1 ? 'request' : 'requests' }}
        <tspan v-if="refused.length"> · {{ refused.length }} refused</tspan>
      </text>

      <!-- Soil, seed and roots: the three layers of the Seed. -->
      <rect class="soil" x="14" y="70" width="150" height="24" rx="4" />
      <g class="roots">
        <path
          v-for="(root, index) in growth.roots"
          :key="root.label"
          class="root"
          :data-new="isNew(root)"
          :d="ROOTS[index % ROOTS.length]"
        >
          <title>{{ root.label }} layer</title>
        </path>
      </g>
      <ellipse class="seed" cx="52" cy="77" rx="5" ry="3.5" />

      <!-- Water that soaked in, one dot per allowed request. -->
      <circle
        v-for="drop in absorbed"
        :key="drop.sequence"
        class="water"
        :data-effect="drop.effect"
        :data-new="isNew(drop)"
        :cx="drop.x"
        :cy="drop.y"
        r="1.8"
      >
        <title>{{ drop.label }} ({{ drop.rule }})</title>
      </circle>

      <!-- Refused requests: a drop held above the ground. -->
      <g v-for="drop in refused" :key="drop.sequence" class="refused" :data-new="isNew(drop)">
        <title>Refused under {{ drop.rule }}: {{ drop.label }}. It watered nothing.</title>
        <path class="refused-drop" :d="`M${drop.x} 56 q4 6 0 9 q-4 -3 0 -9 z`" />
        <line class="barrier" :x1="drop.x - 5" :x2="drop.x + 5" y1="67" y2="67" />
      </g>

      <!-- The drop falling now, if one is: live and calm arrivals only. -->
      <path
        v-if="latestWatering"
        :key="`fall-${latestWatering.sequence}`"
        class="falling"
        :data-effect="latestWatering.effect"
        :d="`M${latestWatering.effect === 'DENY' ? refused[refused.length - 1]?.x ?? 132 : 110} 22 q4 6 0 9 q-4 -3 0 -9 z`"
      />

      <!-- The stem: the whole path as a guide, the grown part over it. -->
      <path class="guide" :d="STEM_PATH" pathLength="1000" />
      <path
        class="stem"
        :d="STEM_PATH"
        pathLength="1000"
        stroke-dasharray="1000"
        :stroke-dashoffset="grownOffset"
      />

      <!-- Discovery: a leaf per system reached. -->
      <path
        v-for="(system, index) in growth.systems"
        :key="`s${system.sequence}`"
        class="leaf"
        :data-new="isNew(system)"
        :d="stemLeaf(systemX(index), index)"
      >
        <title>{{ system.label }} reached</title>
      </path>

      <!-- Assessment: a leaf per methodology assessed. -->
      <path
        v-for="(assessment, index) in growth.assessments"
        :key="`a${assessment.sequence}`"
        class="leaf"
        :data-new="isNew(assessment)"
        :d="stemLeaf(assessmentX(index), index)"
      >
        <title>{{ assessment.label }} assessed</title>
      </path>

      <!-- Implementation: a branch per Agent Component, a leaf per part. -->
      <g v-for="(branch, index) in growth.branches" :key="branch.id" class="branch">
        <title>{{ branch.label }}</title>
        <path class="twig" :data-new="isNew(branch)" :d="branchPath(branchX(index))" />
        <path
          v-for="(leaf, leafIndex) in branch.leaves"
          :key="leaf.sequence"
          class="leaf small"
          :data-new="isNew(leaf)"
          :d="branchLeaf(branchX(index), leafIndex)"
        >
          <title>{{ leaf.label }}</title>
        </path>
        <circle
          v-if="branch.ready"
          class="bud"
          :cx="branchX(index) + 60"
          :cy="20"
          r="3.2"
        />
      </g>

      <!-- Life: Agent One VW flowers when it is ready to run. -->
      <g v-if="growth.bloom" class="bloom" :data-new="isNew(growth.bloom)">
        <title>Agent One VW, ready to run</title>
        <circle
          v-for="angle in [0, 72, 144, 216, 288]"
          :key="angle"
          class="petal"
          :cx="END_X + 8 * Math.cos((angle * Math.PI) / 180)"
          :cy="STEM_Y + 8 * Math.sin((angle * Math.PI) / 180)"
          r="4.5"
        />
        <circle class="heart" :cx="END_X" :cy="STEM_Y" r="3" />
      </g>

      <!-- The phases: complete, current and future, as the strip had them. -->
      <g
        v-for="item in phases"
        :key="item.phase"
        class="phase"
        :data-state="item.state"
        :data-blocked="item.state === 'current' && growth.blocked"
      >
        <circle class="marker" :cx="item.x - 4 - item.label.length * 3.4" cy="106" r="2.6" />
        <text class="label" :x="item.x" y="109" text-anchor="middle">{{ item.label }}</text>
      </g>
    </svg>
  </figure>
</template>

<style scoped>
.tree {
  width: 100%;
  max-width: 64rem;
  margin: 0 auto;
}

svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.tally {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
}

.soil {
  fill: var(--growth-soil);
  stroke: var(--border-subtle);
}

.seed {
  fill: var(--growth-stem);
}

.root {
  fill: none;
  stroke: var(--growth-stem);
  stroke-width: 1.2;
  stroke-linecap: round;
}

.water {
  fill: var(--growth-water);
}

/* Escalated: it reached a person rather than soaking straight in. */
.water[data-effect='ESCALATE'] {
  fill: none;
  stroke: var(--growth-water);
  stroke-width: 0.9;
}

.refused-drop {
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 1;
}

.barrier {
  stroke: var(--text-muted);
  stroke-width: 1;
}

.falling {
  fill: var(--growth-water);
  animation: fall 520ms var(--ease-out) both;
}

.falling[data-effect='DENY'] {
  fill: none;
  stroke: var(--text-muted);
}

.guide {
  fill: none;
  stroke: var(--growth-guide);
  stroke-width: 1;
  stroke-dasharray: 2 4;
}

.stem {
  fill: none;
  stroke: var(--growth-stem);
  stroke-width: 2;
  stroke-linecap: round;
}

svg[data-motion='true'] .stem {
  transition: stroke-dashoffset 520ms var(--ease-out);
}

.leaf {
  fill: var(--growth-leaf);
}

.twig {
  fill: none;
  stroke: var(--growth-stem);
  stroke-width: 1.4;
  stroke-linecap: round;
}

.bud {
  fill: var(--growth-bud);
}

.petal {
  fill: var(--growth-bud);
  opacity: 0.85;
}

.heart {
  fill: var(--growth-leaf);
}

.marker {
  fill: none;
  stroke: var(--border-default);
}

.label {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
}

.phase[data-state='complete'] .marker {
  fill: var(--border-strong);
  stroke: var(--border-strong);
}

.phase[data-state='complete'] .label {
  fill: var(--text-secondary);
}

.phase[data-state='current'] .marker {
  fill: var(--accent);
  stroke: var(--accent);
}

.phase[data-state='current'] .label {
  fill: var(--text-primary);
  font-weight: 600;
}

/* Waiting on a person is not progress, and not a fault (FR-H4). */
.phase[data-blocked='true'] .marker {
  fill: var(--status-warning);
  stroke: var(--status-warning);
}

/* Arrival: a short, low-amplitude sprout, only for calm live events. */
[data-new='true'] {
  transform-box: fill-box;
  transform-origin: 0% 100%;
  animation: sprout 420ms var(--ease-out) both;
}

.water[data-new='true'] {
  transform-origin: 50% 50%;
  animation-delay: 380ms;
}

@keyframes sprout {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
}

@keyframes fall {
  from {
    opacity: 0;
    transform: translateY(-14px);
  }
  70% {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: translateY(46px);
  }
}

@media (prefers-reduced-motion: reduce) {
  [data-new='true'],
  .falling {
    animation: none;
  }

  .falling {
    display: none;
  }

  svg[data-motion='true'] .stem {
    transition: none;
  }
}
</style>
