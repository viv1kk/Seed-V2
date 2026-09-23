<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'

import { PHASE_LABELS } from '../design/presentation'
import { growthOf } from '../design/growth'
import { useEventStore } from '../stores/events'

const events = useEventStore()

/**
 * The growth tree: the seed growing into Agent One VW (D-15, D-18).
 *
 * It stands in the Life pane while seeding is under way and follows the
 * process as it happens. Planting puts the seed and its three roots in
 * the soil. Discovery raises a sapling, a leaf per system reached.
 * Assessment grows it into a small plant, a leaf per methodology
 * assessed. Implementation makes it a tree: the trunk thickens, and each
 * Agent Component is a branch that lengthens with every part built and
 * fruits when it is ready. When the build completes the Life pane hands
 * over to Agent One VW itself.
 *
 * It is watered by tool requests: every capability request the
 * protection engine evaluates is one drop (FR-G3). An allowed request
 * soaks into the soil. A refused one is held above the ground and stays
 * there, a request that fed nothing. Nothing here stands for a model
 * call, because none occurs (FR-G4, NFR-D1).
 *
 * What is drawn is a pure function of the event log, `growthOf(events)`,
 * so a tree rebuilt from a replay is the tree that grew live, and two
 * runs from Reset end the same (FR-G5). Motion only eases the drawing
 * towards that target; it never changes where it ends.
 */
const growth = computed(() => growthOf(events.events))

// -- Geometry, hand-authored (FR-G6) -----------------------------------

const CX = 200
const GROUND = 392

const ROOTS = [
  'M200 400 q-18 10 -46 16',
  'M200 400 q3 14 -4 24',
  'M200 400 q20 9 48 14',
]

/**
 * Where a stem leaf sits, and its side and size: by index, never by time.
 * A system reached adds one small leaf to the sapling. A methodology
 * assessed adds a pair, which is what makes the small plant bushier.
 */
function stemLeaf(kind: 'system' | 'methodology', index: number, pair: 0 | 1 = 0) {
  if (kind === 'system') {
    return { y: GROUND - (18 + index * 11), side: index % 2 === 0 ? 1 : -1, size: 0.7 }
  }
  return { y: GROUND - (74 + index * 18), side: pair === 0 ? 1 : -1, size: 1 }
}

/** Each branch leaves the trunk at a fixed height and side. */
function branchBase(index: number) {
  return { y: GROUND - (100 + index * 42), side: index % 2 === 0 ? -1 : 1 }
}

const BRANCH_ANGLE = (46 * Math.PI) / 180

// -- Targets: what the log says has grown ------------------------------

type Targets = Record<string, number>

const targets = computed<Targets>(() => {
  const g = growth.value
  const t: Targets = {}
  const systems = g.systems.length
  const methods = g.assessments.length
  const branches = g.branches.length
  const parts = g.branches.reduce((n, b) => n + b.leaves.length, 0)

  t.seed = g.roots.length > 0 ? 1 : 0
  g.roots.forEach((_, i) => (t[`root:${i}`] = 1))

  // The seed stays small through the sapling and the small plant; most of
  // the height and girth come with the build, when it becomes a tree.
  const height =
    (g.sprouted ? 14 : 0) + systems * 11 + methods * 20 + branches * 45 + Math.min(parts, 18) * 1.4
  t.height = Math.min(height, 292)
  t.width = g.sprouted
    ? 2 + systems * 0.3 + methods * 0.6 + branches * 3 + Math.min(parts, 18) * 0.15
    : 0

  g.systems.forEach((_, i) => (t[`leaf:system:${i}`] = 1))
  g.assessments.forEach((_, i) => (t[`leaf:methodology:${i}`] = 1))
  // As the tree matures its lower stem leaves thin out, as a trunk's do.
  t.stemLeaves = 1 - 0.65 * (Math.min(branches, 3) / 3)
  // The crown fills out with every Agent Component and every part built.
  t.crown = branches > 0 ? 14 + branches * 8 + Math.min(parts, 18) * 1.1 : 0
  g.branches.forEach((branch, i) => {
    t[`branch:${i}`] = 36 + branch.leaves.length * 11
    t[`branch:${i}:cluster`] = branch.leaves.length > 0 ? 5 + branch.leaves.length * 2.4 : 0
    branch.leaves.forEach((_, k) => (t[`branch:${i}:leaf:${k}`] = 1))
    t[`branch:${i}:fruit`] = branch.ready ? 1 : 0
  })
  return t
})

// -- Motion (NFR-V7) ---------------------------------------------------

/**
 * The drawing eases towards the targets, so growth is continuous rather
 * than a series of jumps, whatever the speed. At instant speed a whole
 * run's growth is simply a faster ease: nothing flashes. Reduced motion,
 * and the first draw after a reload, go straight to the target.
 */
const shown = reactive<Targets>({})
const settled = ref(true)
const reduced =
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
const TAU_MS = 320
let frame = 0
let last = 0

function step(now: number): void {
  const dt = last ? now - last : 16
  last = now
  const k = 1 - Math.exp(-dt / TAU_MS)
  let moving = false
  for (const [key, target] of Object.entries(targets.value)) {
    const current = shown[key] ?? 0
    const next = current + (target - current) * k
    if (Math.abs(target - next) < 0.01) {
      shown[key] = target
    } else {
      shown[key] = next
      moving = true
    }
  }
  settled.value = !moving
  frame = moving ? requestAnimationFrame(step) : 0
  if (!moving) last = 0
}

function snap(): void {
  for (const key of Object.keys(shown)) delete shown[key]
  Object.assign(shown, targets.value)
  settled.value = true
}

watch(
  targets,
  (next, previous) => {
    for (const key of Object.keys(shown)) if (!(key in next)) delete shown[key]
    if (previous === undefined || reduced) {
      snap()
      return
    }
    if (!frame) {
      settled.value = false
      frame = requestAnimationFrame(step)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => cancelAnimationFrame(frame))

const v = (key: string) => shown[key] ?? 0

// -- Drawing -----------------------------------------------------------

/** The trunk: a tapered stem from the ground to its current height. */
const trunk = computed(() => {
  const h = v('height')
  const w = Math.max(v('width'), 0)
  if (h <= 0.5 || w <= 0.1) return null
  const top = GROUND - h
  const lean = Math.min(h / 60, 3)
  const tw = Math.max(w * 0.2, 0.7)
  return (
    `M${CX - w / 2} ${GROUND} ` +
    `C${CX - w / 2} ${GROUND - h * 0.4} ${CX - tw - lean} ${top + h * 0.3} ${CX - tw} ${top} ` +
    `L${CX + tw} ${top} ` +
    `C${CX + tw + lean} ${top + h * 0.3} ${CX + w / 2} ${GROUND - h * 0.4} ${CX + w / 2} ${GROUND} Z`
  )
})

/** A leaf, pointing out from its stem, scaled by how far it has grown. */
const LEAF = 'M0 0 q7 -9 20 -8 q-5 8 -20 8 z'

function leafTransform(x: number, y: number, side: number, angle: number, scale: number): string {
  return `translate(${x} ${y}) scale(${side * scale} ${scale}) rotate(${angle})`
}

const stemLeaves = computed(() => {
  const g = growth.value
  const h = v('height')
  const thin = v('stemLeaves')
  const all = [
    ...g.systems.map((s, i) => ({ ...s, kind: 'system' as const, i, pair: 0 as const })),
    ...g.assessments.flatMap((a, i) => [
      { ...a, kind: 'methodology' as const, i, pair: 0 as const },
      { ...a, kind: 'methodology' as const, i, pair: 1 as const },
    ]),
  ]
  return all.map((item) => {
    const place = stemLeaf(item.kind, item.i, item.pair)
    // A leaf never shows above the stem that carries it.
    const reach = Math.min(1, Math.max(0, (h - (GROUND - place.y)) / 8))
    const scale = v(`leaf:${item.kind}:${item.i}`) * place.size * reach * thin
    return {
      key: `${item.kind}:${item.sequence}:${item.pair}`,
      label: item.kind === 'system' ? `${item.label} reached` : `${item.label} assessed`,
      transform: leafTransform(CX, place.y, place.side, -18, scale),
    }
  })
})

/** Foliage: overlapping discs, so the silhouette reads as a tree's. */
function foliage(x: number, y: number, r: number): { cx: number; cy: number; r: number }[] {
  if (r <= 0.5) return []
  return [
    { cx: x, cy: y - r * 0.35, r },
    { cx: x - r * 0.62, cy: y + r * 0.05, r: r * 0.72 },
    { cx: x + r * 0.62, cy: y + r * 0.05, r: r * 0.72 },
    { cx: x, cy: y + r * 0.3, r: r * 0.6 },
  ]
}

const crown = computed(() => foliage(CX, GROUND - v('height'), v('crown')))

const branches = computed(() =>
  growth.value.branches.map((branch, i) => {
    const base = branchBase(i)
    const length = v(`branch:${i}`)
    const dx = Math.cos(BRANCH_ANGLE) * length * base.side
    const dy = -Math.sin(BRANCH_ANGLE) * length
    const tip = { x: CX + dx, y: base.y + dy }
    const bend = { x: CX + dx * 0.45, y: base.y + dy * 0.2 }
    const leaves = branch.leaves.map((leaf, k) => {
      const t = (k + 1) / 7
      const x = (1 - t) ** 2 * CX + 2 * (1 - t) * t * bend.x + t * t * tip.x
      const y = (1 - t) ** 2 * base.y + 2 * (1 - t) * t * bend.y + t * t * tip.y
      const side = k % 2 === 0 ? base.side : -base.side
      return {
        key: leaf.sequence,
        label: leaf.label,
        transform: leafTransform(x, y, side, k % 2 === 0 ? -34 : 10, 0.7 * v(`branch:${i}:leaf:${k}`)),
      }
    })
    return {
      key: branch.id,
      label: branch.label,
      path: length > 0.5 ? `M${CX} ${base.y} Q${bend.x} ${bend.y} ${tip.x} ${tip.y}` : null,
      width: 1.6 + Math.min(branch.leaves.length, 6) * 0.45,
      leaves,
      cluster: foliage(tip.x, tip.y, v(`branch:${i}:cluster`)),
      fruit: { x: tip.x, y: tip.y - v(`branch:${i}:cluster`) * 0.55, r: 4.2 * v(`branch:${i}:fruit`) },
    }
  }),
)

const roots = computed(() =>
  growth.value.roots.map((root, i) => ({
    key: root.label,
    label: `${root.label} layer`,
    d: ROOTS[i % ROOTS.length],
    grown: v(`root:${i}`),
  })),
)

/** Allowed and escalated requests soak in: one dot each, in the soil. */
const absorbed = computed(() =>
  growth.value.waterings
    .filter((w) => w.effect !== 'DENY')
    .map((w, i) => ({ ...w, x: 76 + (i % 28) * 9, y: 404 + Math.min(Math.floor(i / 28), 2) * 8 })),
)

/** Refused requests: held above the ground, beside the tree. */
const refused = computed(() =>
  growth.value.waterings
    .filter((w) => w.effect === 'DENY')
    .map((w, i) => ({ ...w, x: 80 + i * 18 })),
)

const watered = computed(() => absorbed.value.length)

/** The drop falling now, if the latest request arrived on its own. */
const CALM_GAP_MS = 250
const falling = ref<{ sequence: number; effect: string; x: number } | null>(null)
let lastArrival = 0
let primed = false
watch(
  () => growth.value.waterings.length,
  (count, before) => {
    const now = performance.now()
    const calm = primed && before !== undefined && count === before + 1 && now - lastArrival >= CALM_GAP_MS
    lastArrival = now
    primed = true
    const latest = growth.value.waterings[count - 1]
    if (!calm || !latest || reduced) return
    const deny = latest.effect === 'DENY'
    falling.value = {
      sequence: latest.sequence,
      effect: latest.effect,
      x: deny ? refused.value[refused.value.length - 1].x : CX + 24,
    }
  },
  { immediate: true },
)

/** What the tree is now, in the process's own terms. */
const STAGES = {
  INIT: 'Seed planted',
  DISCOVERY: 'Sapling',
  ASSESSMENT: 'Small plant',
  IMPLEMENTATION: 'Growing tree',
  RUNTIME: 'Grown',
} as const

const caption = computed(() => {
  const g = growth.value
  const phase = g.phase ?? 'INIT'
  const parts = g.branches.reduce((n, b) => n + b.leaves.length, 0)
  const detail: Record<keyof typeof STAGES, string> = {
    INIT: `${g.roots.length} layers rooted`,
    DISCOVERY: `${g.systems.length} ${g.systems.length === 1 ? 'system' : 'systems'} reached`,
    ASSESSMENT: `${g.assessments.length} ${g.assessments.length === 1 ? 'methodology' : 'methodologies'} assessed`,
    IMPLEMENTATION: `${g.branches.length} Agent ${g.branches.length === 1 ? 'Component' : 'Components'}, ${parts} parts built`,
    RUNTIME: 'Agent One VW',
  }
  return {
    stage: STAGES[phase],
    phase: PHASE_LABELS[phase],
    detail: detail[phase],
    waiting: g.blocked,
  }
})
</script>

<template>
  <figure class="tree" :aria-label="`Growth: ${caption.stage}`">
    <figcaption class="caption">
      <span class="stage">{{ caption.stage }}</span>
      <span class="detail mono">
        {{ caption.phase }} · {{ caption.detail }}
        <template v-if="caption.waiting"> · waiting on input</template>
      </span>
    </figcaption>

    <svg viewBox="0 0 400 460" role="img" :data-settled="settled">
      <title>
        The seed growing into Agent One VW. Watered by tool requests the protection engine
        evaluated; no model calls occur.
      </title>

      <!-- Soil, seed and roots: the Seed's three layers. -->
      <rect class="soil" x="60" y="392" width="280" height="36" rx="6" />
      <line class="ground" x1="40" x2="360" :y1="GROUND" :y2="GROUND" />
      <path
        v-for="root in roots"
        :key="root.key"
        class="root"
        :d="root.d"
        pathLength="1"
        stroke-dasharray="1"
        :stroke-dashoffset="1 - root.grown"
      >
        <title>{{ root.label }}</title>
      </path>
      <ellipse v-if="v('seed') > 0" class="seed" :cx="CX" cy="401" rx="7" ry="4.5" />

      <!-- Water that soaked in, one dot per allowed request (FR-G3). -->
      <circle
        v-for="drop in absorbed"
        :key="drop.sequence"
        class="water"
        :data-effect="drop.effect"
        :cx="drop.x"
        :cy="drop.y"
        r="2.2"
      >
        <title>{{ drop.label }} ({{ drop.rule }})</title>
      </circle>

      <!-- Refused requests: held above the ground; they fed nothing. -->
      <g v-for="drop in refused" :key="drop.sequence" class="refused">
        <title>Refused under {{ drop.rule }}: {{ drop.label }}. It watered nothing.</title>
        <path :d="`M${drop.x} 366 q6 9 0 14 q-6 -5 0 -14 z`" />
        <line :x1="drop.x - 8" :x2="drop.x + 8" y1="384" y2="384" />
      </g>

      <!-- The trunk, its stem leaves, and the branches of the build. -->
      <path v-if="trunk" class="trunk" :d="trunk" />
      <path
        v-for="leaf in stemLeaves"
        :key="leaf.key"
        class="leaf"
        :d="LEAF"
        :transform="leaf.transform"
      >
        <title>{{ leaf.label }}</title>
      </path>
      <circle
        v-for="(disc, d) in crown"
        :key="`crown${d}`"
        class="canopy"
        :cx="disc.cx"
        :cy="disc.cy"
        :r="disc.r"
      />
      <g v-for="branch in branches" :key="branch.key" class="branch">
        <title>{{ branch.label }}</title>
        <path v-if="branch.path" class="twig" :d="branch.path" :stroke-width="branch.width" />
        <circle
          v-for="(disc, d) in branch.cluster"
          :key="`c${d}`"
          class="canopy"
          :cx="disc.cx"
          :cy="disc.cy"
          :r="disc.r"
        />
        <path
          v-for="leaf in branch.leaves"
          :key="leaf.key"
          class="leaf"
          :d="LEAF"
          :transform="leaf.transform"
        >
          <title>{{ leaf.label }}</title>
        </path>
        <circle
          v-if="branch.fruit.r > 0.2"
          class="fruit"
          :cx="branch.fruit.x"
          :cy="branch.fruit.y"
          :r="branch.fruit.r"
        />
      </g>

      <!-- The drop falling now: live, calm arrivals only. -->
      <path
        v-if="falling"
        :key="`fall-${falling.sequence}`"
        class="falling"
        :data-effect="falling.effect"
        :d="`M${falling.x} 60 q6 9 0 14 q-6 -5 0 -14 z`"
        @animationend="falling = null"
      />

      <text class="tally" :x="CX" y="450" text-anchor="middle">
        Watered by {{ watered }} tool {{ watered === 1 ? 'request' : 'requests' }}
        <tspan v-if="refused.length"> · {{ refused.length }} refused</tspan>
      </text>
    </svg>
  </figure>
</template>

<style scoped>
.tree {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  height: 100%;
  margin: 0;
  padding: var(--space-6) var(--space-6) var(--space-4);
}

.caption {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}

.stage {
  color: var(--text-primary);
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.detail {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
}

.mono {
  font-family: var(--font-mono);
}

svg {
  flex: 1;
  width: 100%;
  min-height: 0;
  max-height: 34rem;
}

.soil {
  fill: var(--growth-soil);
  stroke: var(--border-subtle);
}

.ground {
  stroke: var(--border-default);
}

.root {
  fill: none;
  stroke: var(--growth-stem);
  stroke-width: 1.6;
  stroke-linecap: round;
}

.seed {
  fill: var(--growth-stem);
}

.trunk {
  fill: var(--growth-stem);
}

.twig {
  fill: none;
  stroke: var(--growth-stem);
  stroke-linecap: round;
}

.leaf {
  fill: var(--growth-leaf);
}

.canopy {
  fill: var(--growth-leaf);
  opacity: 0.55;
}

.fruit {
  fill: var(--growth-bud);
}

.water {
  fill: var(--growth-water);
}

/* Escalated: it reached a person rather than soaking straight in. */
.water[data-effect='ESCALATE'] {
  fill: none;
  stroke: var(--growth-water);
  stroke-width: 1.1;
}

.refused path {
  fill: none;
  stroke: var(--text-muted);
}

.refused line {
  stroke: var(--text-muted);
}

.falling {
  fill: var(--growth-water);
  animation: fall 700ms var(--ease-out) both;
}

.falling[data-effect='DENY'] {
  fill: none;
  stroke: var(--text-muted);
  animation-name: held;
}

.tally {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
}

@keyframes fall {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  20% {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: translateY(334px);
  }
}

/* A refused drop stops at the barrier and fades there. */
@keyframes held {
  from {
    opacity: 0;
  }
  30% {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: translateY(300px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .falling {
    display: none;
  }
}
</style>
