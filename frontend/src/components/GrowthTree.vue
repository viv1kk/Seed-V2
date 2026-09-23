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

const CX = 260
const GROUND = 372
const SOIL_DEPTH = 96
const SEED_Y = GROUND + 9

/** Where the soil band starts and how wide it is. It fades at both ends. */
const SOIL_X = 40
const SOIL_W = 440

/**
 * The main roots, one per layer: out to the left, straight down, out to
 * the right. Each is a curve from the seed, given by its end and its bend.
 */
const MAIN_ROOTS: { end: [number, number]; bend: [number, number] }[] = [
  { end: [-92, 50], bend: [-34, 34] },
  { end: [6, 86], bend: [-12, 46] },
  { end: [96, 46], bend: [38, 30] },
]

/** Where laterals leave a main root, and where hairs leave a lateral. */
const LATERALS = [0.26, 0.44, 0.62, 0.8]
const HAIRS = [0.45, 0.8]
const LATERAL_ANGLE = (48 * Math.PI) / 180
const HAIR_ANGLE = (52 * Math.PI) / 180

type Point = { x: number; y: number }

/** A point on a quadratic curve, and the curve's direction there. */
function quad(p0: Point, c: Point, p1: Point, t: number): { at: Point; dir: Point } {
  const at = {
    x: (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * c.x + t * t * p1.x,
    y: (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * c.y + t * t * p1.y,
  }
  const dx = 2 * (1 - t) * (c.x - p0.x) + 2 * t * (p1.x - c.x)
  const dy = 2 * (1 - t) * (c.y - p0.y) + 2 * t * (p1.y - c.y)
  const n = Math.hypot(dx, dy) || 1
  return { at, dir: { x: dx / n, y: dy / n } }
}

function turn(dir: Point, angle: number): Point {
  const c = Math.cos(angle)
  const s = Math.sin(angle)
  return { x: dir.x * c - dir.y * s, y: dir.x * s + dir.y * c }
}

/** A slightly bowed stroke from a point, along a direction, for a length. */
function sprig(from: Point, dir: Point, length: number, bow: number): { d: string; end: Point } {
  const end = { x: from.x + dir.x * length, y: from.y + dir.y * length }
  const mid = {
    x: from.x + dir.x * length * 0.5 - dir.y * length * bow,
    y: from.y + dir.y * length * 0.5 + dir.x * length * bow,
  }
  return {
    d: `M${from.x} ${from.y} Q${mid.x} ${mid.y} ${end.x} ${end.y}`,
    end,
  }
}

/**
 * The whole root system, fixed in advance: each main root, its laterals
 * and their hairs. How much of it shows is set by growth, not here.
 */
const ROOT_SYSTEM = MAIN_ROOTS.map((root) => {
  const p0 = { x: CX, y: SEED_Y }
  const c = { x: CX + root.bend[0], y: SEED_Y + root.bend[1] }
  const p1 = { x: CX + root.end[0], y: SEED_Y + root.end[1] }
  const reach = Math.hypot(root.end[0], root.end[1]) / 90
  const laterals = LATERALS.map((t, j) => {
    const side = j % 2 === 0 ? 1 : -1
    const { at, dir } = quad(p0, c, p1, t)
    const length = 34 * (1 - t * 0.55) * reach
    const lateral = sprig(at, turn(dir, side * LATERAL_ANGLE), length, 0.12 * side)
    const middle = {
      x: (at.x + lateral.end.x) / 2,
      y: (at.y + lateral.end.y) / 2,
    }
    const hairs = HAIRS.map((s, h) => {
      const point = quad(at, middle, lateral.end, s)
      const hs = h % 2 === 0 ? -side : side
      return sprig(point.at, turn(point.dir, hs * HAIR_ANGLE), 11 * (1 - s * 0.4), 0.1 * hs).d
    })
    return { d: lateral.d, hairs }
  })
  return { d: `M${p0.x} ${p0.y} Q${c.x} ${c.y} ${p1.x} ${p1.y}`, laterals }
})

/**
 * Where a stem leaf sits, and its side and size: by index, never by time.
 * A system reached adds one small leaf to the sapling. A methodology
 * assessed adds a pair, which is what makes the small plant bushier.
 */
function stemLeaf(kind: 'system' | 'methodology', index: number, pair: 0 | 1 = 0) {
  if (kind === 'system') {
    return {
      y: GROUND - (16 + index * 9),
      side: index % 2 === 0 ? 1 : -1,
      size: 0.7,
    }
  }
  return { y: GROUND - (72 + index * 16), side: pair === 0 ? 1 : -1, size: 1 }
}

/** Each branch leaves the trunk at a fixed height and side. */
function branchBase(index: number) {
  return { y: GROUND - (92 + index * 40), side: index % 2 === 0 ? -1 : 1 }
}

/** Branches spread wide and shallow, so the tree grows out as well as up. */
const BRANCH_ANGLE = (26 * Math.PI) / 180

/** Each part built grows a twig off its branch: alternately up, then level. */
const TWIG_TURN = [(34 * Math.PI) / 180, (-30 * Math.PI) / 180]

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
  // The roots bush out as the plant above them grows: a few laterals at
  // planting, the whole system once the build is well under way.
  const progress = systems + methods * 2 + branches * 3 + parts
  t.rootSpread = g.roots.length > 0 ? 0.25 + 0.75 * Math.min(1, progress / 30) : 0

  // The seed stays small through the sapling and the small plant; most of
  // the height and girth come with the build, when it becomes a tree.
  const height =
    (g.sprouted ? 14 : 0) + systems * 9 + methods * 16 + branches * 38 + Math.min(parts, 18) * 1.2
  t.height = Math.min(height, 250)
  t.width = g.sprouted
    ? 2 + systems * 0.3 + methods * 0.6 + branches * 3.4 + Math.min(parts, 18) * 0.2
    : 0

  g.systems.forEach((_, i) => (t[`leaf:system:${i}`] = 1))
  g.assessments.forEach((_, i) => (t[`leaf:methodology:${i}`] = 1))
  // As the tree matures its lower stem leaves thin out, as a trunk's do.
  t.stemLeaves = 1 - 0.85 * (Math.min(branches, 3) / 3)
  // The crown fills out with every Agent Component and every part built,
  // and carries two leaves for each part.
  t.crown = branches > 0 ? 16 + branches * 9 + Math.min(parts, 18) * 1.2 : 0
  for (let k = 0; k < Math.min(parts, 18) * 2; k++) t[`crownLeaf:${k}`] = 1
  g.branches.forEach((branch, i) => {
    t[`branch:${i}`] = 56 + branch.leaves.length * 18
    t[`branch:${i}:cluster`] = branch.leaves.length > 0 ? 6 + branch.leaves.length * 3 : 0
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

/**
 * Ids for the soil's gradients. Fixed rather than generated, so the same
 * log draws the same markup (FR-G5); only one tree is ever mounted.
 */
const ids = {
  soil: 'growth-soil',
  edge: 'growth-edge',
  mask: 'growth-mask',
  line: 'growth-line',
}

/** The trunk: a tapered stem from the ground to its current height. */
const trunk = computed(() => {
  const h = v('height')
  const w = Math.max(v('width'), 0)
  if (h <= 0.5 || w <= 0.1) return null
  const top = GROUND - h
  const lean = Math.min(h / 60, 3)
  const tw = Math.max(w * 0.2, 0.7)
  // The base flares a little where it meets the roots.
  const flare = w * 0.18
  return (
    `M${CX - w / 2 - flare} ${GROUND + 2} ` +
    `Q${CX - w / 2} ${GROUND} ${CX - w / 2} ${GROUND - h * 0.12} ` +
    `C${CX - w / 2} ${GROUND - h * 0.5} ${CX - tw - lean} ${top + h * 0.25} ${CX - tw} ${top} ` +
    `L${CX + tw} ${top} ` +
    `C${CX + tw + lean} ${top + h * 0.25} ${CX + w / 2} ${GROUND - h * 0.5} ${CX + w / 2} ${GROUND - h * 0.12} ` +
    `Q${CX + w / 2} ${GROUND} ${CX + w / 2 + flare} ${GROUND + 2} Z`
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
    ...g.systems.map((s, i) => ({
      ...s,
      kind: 'system' as const,
      i,
      pair: 0 as const,
    })),
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

type Disc = { cx: number; cy: number; r: number }

/**
 * Foliage: overlapping discs, spread wider than they are tall so the
 * silhouette reads as a broad tree's. Offsets and sizes are in radii.
 */
const CLOUD: [number, number, number][] = [
  [0, -0.35, 1],
  [-0.95, -0.1, 0.8],
  [0.95, -0.1, 0.8],
  [-1.75, 0.25, 0.62],
  [1.75, 0.25, 0.62],
  [-2.35, 0.5, 0.42],
  [2.35, 0.5, 0.42],
  [-0.55, 0.4, 0.72],
  [0.55, 0.4, 0.72],
  [-1.25, 0.55, 0.55],
  [1.25, 0.55, 0.55],
  [-0.6, -0.8, 0.6],
  [0.6, -0.8, 0.6],
  [-1.4, -0.45, 0.5],
  [1.4, -0.45, 0.5],
]

const TUFT: [number, number, number][] = [
  [0, -0.3, 1],
  [-0.7, 0.05, 0.72],
  [0.7, 0.05, 0.72],
  [0, 0.35, 0.6],
]

function foliage(x: number, y: number, r: number, shape = TUFT): Disc[] {
  if (r <= 0.5) return []
  return shape.map(([dx, dy, s]) => ({
    cx: x + dx * r,
    cy: y + dy * r,
    r: s * r,
  }))
}

/** The crown sits on the top of the trunk and spreads out from it. */
const crown = computed(() => {
  const r = v('crown')
  const top = { x: CX, y: GROUND - v('height') + r * 0.2 }
  const parts = growth.value.branches.reduce((n, b) => n + b.leaves.length, 0)
  // Two leaves per part built, set on a spiral through the crown so they
  // spread evenly: placed by index, never by time.
  const leaves = Array.from({ length: Math.min(parts, 18) * 2 }, (_, k) => {
    const angle = k * 2.39996
    const radius = Math.sqrt((k + 0.5) / 36)
    const x = top.x + Math.cos(angle) * radius * r * 2.2
    const y = top.y - r * 0.2 + Math.sin(angle) * radius * r * 0.95
    const scale = 0.75 * v(`crownLeaf:${k}`)
    return {
      key: `crown${k}`,
      transform: leafTransform(x, y, k % 2 === 0 ? 1 : -1, (k * 47) % 360, scale),
    }
  })
  return { discs: foliage(top.x, top.y, r, CLOUD), leaves }
})

const branches = computed(() =>
  growth.value.branches.map((branch, i) => {
    const base = branchBase(i)
    const length = v(`branch:${i}`)
    const dx = Math.cos(BRANCH_ANGLE) * length * base.side
    const dy = -Math.sin(BRANCH_ANGLE) * length
    const start = { x: CX, y: base.y }
    const tip = { x: CX + dx, y: base.y + dy }
    const bend = { x: CX + dx * 0.45, y: base.y + dy * 0.2 }
    const leaves = branch.leaves.map((leaf, k) => {
      const { at } = quad(start, bend, tip, (k + 1) / 7)
      const side = k % 2 === 0 ? base.side : -base.side
      const scale = 0.7 * v(`branch:${i}:leaf:${k}`)
      return {
        key: leaf.sequence,
        label: leaf.label,
        transform: leafTransform(at.x, at.y, side, k % 2 === 0 ? -34 : 10, scale),
      }
    })
    // A twig per part built, each ending in a small tuft and two leaves.
    const twigs = branch.leaves.map((leaf, k) => {
      const grown = v(`branch:${i}:leaf:${k}`)
      const { at, dir } = quad(start, bend, tip, 0.3 + 0.12 * k)
      const heading = turn(dir, -base.side * TWIG_TURN[k % 2])
      const twig = sprig(at, heading, 24 * grown, 0.1 * base.side)
      return {
        key: `t${leaf.sequence}`,
        d: grown > 0.02 ? twig.d : null,
        tuft: foliage(twig.end.x, twig.end.y, 8.5 * grown),
        leaves: [
          leafTransform(twig.end.x, twig.end.y, base.side, -40, 0.6 * grown),
          leafTransform(twig.end.x, twig.end.y, -base.side, 20, 0.55 * grown),
        ],
      }
    })
    const cluster = v(`branch:${i}:cluster`)
    return {
      key: branch.id,
      label: branch.label,
      path: length > 0.5 ? `M${CX} ${base.y} Q${bend.x} ${bend.y} ${tip.x} ${tip.y}` : null,
      width: 2 + Math.min(branch.leaves.length, 6) * 0.55,
      leaves,
      twigs,
      cluster: foliage(tip.x, tip.y, cluster),
      fruit: {
        x: tip.x,
        y: tip.y - cluster * 0.55,
        r: 4.2 * v(`branch:${i}:fruit`),
      },
    }
  }),
)

/**
 * The roots: a main root per layer, which bushes out into laterals and
 * fine hairs as the plant above it grows.
 */
const roots = computed(() => {
  const spread = v('rootSpread') * (LATERALS.length + 1)
  const girth = 1.8 + Math.min(v('width'), 12) * 0.2
  return growth.value.roots.map((root, i) => {
    const system = ROOT_SYSTEM[i % ROOT_SYSTEM.length]
    const grown = v(`root:${i}`)
    return {
      key: root.label,
      label: `${root.label} layer`,
      d: system.d,
      grown,
      girth,
      laterals: system.laterals.map((lateral, j) => ({
        d: lateral.d,
        grown: grown * Math.min(1, Math.max(0, spread - j)),
        hairs: lateral.hairs,
        hairGrown: grown * Math.min(1, Math.max(0, spread - j - 1)),
      })),
    }
  })
})

/** Allowed and escalated requests soak in: one dot each, in the soil. */
const absorbed = computed(() =>
  growth.value.waterings
    .filter((w) => w.effect !== 'DENY')
    .map((w, i) => ({
      ...w,
      x: CX - 124 + (i % 28) * 9,
      y: GROUND + 12 + Math.min(Math.floor(i / 28), 2) * 8,
    })),
)

/** Refused requests: held above the ground, beside the tree. */
const refused = computed(() =>
  growth.value.waterings
    .filter((w) => w.effect === 'DENY')
    .map((w, i) => ({ ...w, x: CX - 150 + i * 18 })),
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
    const calm =
      primed && before !== undefined && count === before + 1 && now - lastArrival >= CALM_GAP_MS
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

    <svg viewBox="0 0 520 500" role="img" :data-settled="settled">
      <title>
        The seed growing into Agent One VW. Watered by tool requests the protection engine
        evaluated; no model calls occur.
      </title>

      <defs>
        <!-- The soil is a tint at the surface that fades downward, and at
             both ends, so the roots show through it. -->
        <linearGradient :id="ids.soil" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" class="soil-stop" stop-opacity="0.95" />
          <stop offset="0.4" class="soil-stop" stop-opacity="0.45" />
          <stop offset="1" class="soil-stop" stop-opacity="0" />
        </linearGradient>
        <linearGradient :id="ids.edge" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#fff" stop-opacity="0" />
          <stop offset="0.2" stop-color="#fff" stop-opacity="1" />
          <stop offset="0.8" stop-color="#fff" stop-opacity="1" />
          <stop offset="1" stop-color="#fff" stop-opacity="0" />
        </linearGradient>
        <linearGradient :id="ids.line" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" class="surface-stop" stop-opacity="0" />
          <stop offset="0.2" class="surface-stop" stop-opacity="1" />
          <stop offset="0.8" class="surface-stop" stop-opacity="1" />
          <stop offset="1" class="surface-stop" stop-opacity="0" />
        </linearGradient>
        <mask :id="ids.mask">
          <rect
            :x="SOIL_X"
            :y="GROUND"
            :width="SOIL_W"
            :height="SOIL_DEPTH"
            :fill="`url(#${ids.edge})`"
          />
        </mask>
      </defs>

      <!-- Soil, seed and roots: the Seed's three layers. -->
      <rect
        class="soil"
        :x="SOIL_X"
        :y="GROUND"
        :width="SOIL_W"
        :height="SOIL_DEPTH"
        :fill="`url(#${ids.soil})`"
        :mask="`url(#${ids.mask})`"
      />
      <rect :x="SOIL_X" :y="GROUND - 1" :width="SOIL_W" height="2" :fill="`url(#${ids.line})`" />
      <g v-for="root in roots" :key="root.key" class="roots">
        <title>{{ root.label }}</title>
        <path
          class="root"
          :d="root.d"
          :stroke-width="root.girth"
          pathLength="1"
          stroke-dasharray="1"
          :stroke-dashoffset="1 - root.grown"
        />
        <template v-for="(lateral, j) in root.laterals" :key="j">
          <path
            class="root lateral"
            :d="lateral.d"
            pathLength="1"
            stroke-dasharray="1"
            :stroke-dashoffset="1 - lateral.grown"
          />
          <path
            v-for="(hair, h) in lateral.hairs"
            :key="h"
            class="root hair"
            :d="hair"
            pathLength="1"
            stroke-dasharray="1"
            :stroke-dashoffset="1 - lateral.hairGrown"
          />
        </template>
      </g>
      <ellipse v-if="v('seed') > 0" class="seed" :cx="CX" :cy="SEED_Y" rx="7" ry="4.5" />

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
        <path :d="`M${drop.x} ${GROUND - 26} q6 9 0 14 q-6 -5 0 -14 z`" />
        <line :x1="drop.x - 8" :x2="drop.x + 8" :y1="GROUND - 8" :y2="GROUND - 8" />
      </g>

      <!-- The crown behind, then the trunk and its stem leaves, then the
           branches of the build with their twigs and foliage. -->
      <circle
        v-for="(disc, d) in crown.discs"
        :key="`crown${d}`"
        class="canopy deep"
        :cx="disc.cx"
        :cy="disc.cy"
        :r="disc.r"
      />
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
      <g v-for="branch in branches" :key="branch.key" class="branch">
        <title>{{ branch.label }}</title>
        <path v-if="branch.path" class="twig" :d="branch.path" :stroke-width="branch.width" />
        <g v-for="twig in branch.twigs" :key="twig.key">
          <path v-if="twig.d" class="twig" :d="twig.d" stroke-width="1.4" />
          <circle
            v-for="(disc, d) in twig.tuft"
            :key="`f${d}`"
            class="canopy"
            :cx="disc.cx"
            :cy="disc.cy"
            :r="disc.r"
          />
          <path
            v-for="(transform, l) in twig.leaves"
            :key="`l${l}`"
            class="leaf"
            :d="LEAF"
            :transform="transform"
          />
        </g>
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
      </g>
      <path
        v-for="leaf in crown.leaves"
        :key="leaf.key"
        class="leaf"
        :d="LEAF"
        :transform="leaf.transform"
      />
      <g v-for="branch in branches" :key="`fruit-${branch.key}`">
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
        :d="`M${falling.x} 50 q6 9 0 14 q-6 -5 0 -14 z`"
        @animationend="falling = null"
      />

      <text class="tally" :x="CX" y="490" text-anchor="middle">
        Watered by {{ watered }} tool
        {{ watered === 1 ? 'request' : 'requests' }}
        <tspan v-if="refused.length">· {{ refused.length }} refused</tspan>
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
  max-height: 42rem;
}

.soil-stop {
  stop-color: var(--growth-soil);
}

.surface-stop {
  stop-color: var(--growth-surface);
}

/* Roots are earth brown, apart from the green above ground. */
.root {
  fill: none;
  stroke: var(--growth-root);
  stroke-linecap: round;
}

.lateral {
  stroke-width: 1.2;
}

.hair {
  stroke-width: 0.7;
  opacity: 0.75;
}

.seed {
  fill: var(--growth-root);
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
  opacity: 0.6;
}

.canopy.deep {
  fill: var(--growth-leaf-deep);
  opacity: 0.85;
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
    transform: translateY(318px);
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
    transform: translateY(290px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .falling {
    display: none;
  }
}
</style>
