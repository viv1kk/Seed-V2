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
 * protection engine evaluates waters it or is refused (FR-G3). An allowed
 * request soaks in: the soil and roots tint blue for a moment, and the
 * tree glows as it grows a little. A refused one is held above the ground
 * and stays there, a request that fed nothing. Nothing here stands for a
 * model call, because none occurs (FR-G4, NFR-D1).
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

/**
 * Finer roots from the seed, between the three main ones. They carry no
 * layer: they are what makes the root system read as dense, and they
 * come in as the roots bush out.
 */
const FIBRES: { end: [number, number]; bend: [number, number] }[] = [
  { end: [-58, 72], bend: [-16, 40] },
  { end: [-128, 24], bend: [-52, 14] },
  { end: [54, 76], bend: [18, 42] },
  { end: [130, 20], bend: [56, 12] },
  { end: [-26, 80], bend: [-6, 44] },
  { end: [30, 82], bend: [10, 46] },
]

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

/** Evenly spaced positions along a stroke, from `from` to `to`. */
function spaced(count: number, from: number, to: number): number[] {
  return Array.from({ length: count }, (_, k) =>
    count === 1 ? from : from + ((to - from) * k) / (count - 1),
  )
}

interface Lateral {
  d: string
  hairs: string[]
  nodules: { x: number; y: number; r: number }[]
}

/**
 * One root, fixed in advance: its curve, the laterals along it, the fine
 * hairs on each lateral and the nodules they carry. How much of it shows
 * is set by growth, not here.
 */
function rootOf(
  root: { end: [number, number]; bend: [number, number] },
  lateralCount: number,
  hairCount: number,
): { d: string; laterals: Lateral[] } {
  const p0 = { x: CX, y: SEED_Y }
  const c = { x: CX + root.bend[0], y: SEED_Y + root.bend[1] }
  const p1 = { x: CX + root.end[0], y: SEED_Y + root.end[1] }
  const reach = Math.hypot(root.end[0], root.end[1]) / 90
  const laterals = spaced(lateralCount, 0.12, 0.92).map((t, j) => {
    const side = j % 2 === 0 ? 1 : -1
    const { at, dir } = quad(p0, c, p1, t)
    const length = 34 * (1 - t * 0.55) * reach
    const lateral = sprig(at, turn(dir, side * LATERAL_ANGLE), length, 0.12 * side)
    const middle = { x: (at.x + lateral.end.x) / 2, y: (at.y + lateral.end.y) / 2 }
    const hairs = spaced(hairCount, 0.25, 0.9).map((s, h) => {
      const point = quad(at, middle, lateral.end, s)
      const hs = h % 2 === 0 ? -side : side
      return sprig(point.at, turn(point.dir, hs * HAIR_ANGLE), 11 * (1 - s * 0.4), 0.1 * hs).d
    })
    // Nodules sit along the lateral: one on each, a second on every other.
    const nodules = (j % 2 === 0 ? [0.35, 0.72] : [0.5]).map((s, n) => {
      const { at: point } = quad(at, middle, lateral.end, s)
      return { x: point.x, y: point.y, r: 1.3 + ((j + n) % 3) * 0.35 }
    })
    return { d: lateral.d, hairs, nodules }
  })
  return { d: `M${p0.x} ${p0.y} Q${c.x} ${c.y} ${p1.x} ${p1.y}`, laterals }
}

/** The main roots, one per layer: eight laterals, four hairs on each. */
const ROOT_SYSTEM = MAIN_ROOTS.map((root) => rootOf(root, 8, 4))

/** The fibres: shorter, with fewer laterals. */
const FIBRE_SYSTEM = FIBRES.map((root) => rootOf(root, 4, 3))

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
  // How far the stem has aged from green shoot to bark: a little with each
  // system and methodology, most of it with the build.
  t.age = g.sprouted
    ? Math.min(1, (systems + methods * 2 + branches * 4 + Math.min(parts, 18) * 0.8) / 36)
    : 0

  // The seed stays small through the sapling and the small plant; most of
  // the height and girth come with the build, when it becomes a tree.
  const height =
    (g.sprouted ? 14 : 0) + systems * 9 + methods * 16 + branches * 38 + Math.min(parts, 18) * 1.2
  // Every request that waters the tree adds a little to it, so each
  // watering is seen to feed growth (FR-G3). Counted from the log.
  const allowed = Math.min(g.waterings.filter((w) => w.effect !== 'DENY').length, 30)
  t.height = g.sprouted ? Math.min(height, 250) + allowed * 0.4 : 0
  t.width = g.sprouted
    ? 2 +
      systems * 0.3 +
      methods * 0.6 +
      branches * 3.4 +
      Math.min(parts, 18) * 0.2 +
      allowed * 0.03
    : 0

  g.systems.forEach((_, i) => (t[`leaf:system:${i}`] = 1))
  g.assessments.forEach((_, i) => (t[`leaf:methodology:${i}`] = 1))
  // As the tree matures its lower stem leaves thin out, as a trunk's do.
  t.stemLeaves = 1 - 0.85 * (Math.min(branches, 3) / 3)
  // The crown fills out with every Agent Component and every part built,
  // and carries two leaves for each part.
  t.crown = branches > 0 ? 16 + branches * 9 + Math.min(parts, 18) * 1.2 + allowed * 0.12 : 0
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
 * Ids for the drawing's shared parts. Fixed rather than generated, so the same
 * log draws the same markup (FR-G5); only one tree is ever mounted.
 */
const ids = {
  soil: 'growth-soil',
  edge: 'growth-edge',
  mask: 'growth-mask',
  line: 'growth-line',
  leaf: 'growth-leaf',
  canopy: 'growth-canopy',
  canopyDeep: 'growth-canopy-deep',
  bark: 'growth-bark',
  shade: 'growth-shade',
  underground: 'growth-underground',
}

/**
 * The stem's colour, by age: fresh green in the sapling, turning to bark
 * as the process advances. Branches lag the trunk and twigs lag the
 * branches, as younger wood does.
 */
function woodAt(age: number): string {
  const bark = Math.round(Math.min(1, Math.max(0, age)) * 1000) / 10
  return `color-mix(in oklab, var(--growth-bark) ${bark}%, var(--growth-stem-young))`
}

const wood = computed(() => ({
  trunk: woodAt(v('age')),
  branch: woodAt(v('age') * 0.8),
  twig: woodAt(v('age') * 0.45),
  // Bark furrows show once the stem has started to turn.
  furrows: Math.round(Math.min(1, Math.max(0, (v('age') - 0.15) / 0.6)) * 100) / 100,
}))

/** The trunk: a tapered stem from the ground to its current height. */
const trunk = computed(() => {
  const h = v('height')
  const w = Math.max(v('width'), 0)
  if (h <= 0.5 || w <= 0.1) return null
  const top = GROUND - h
  const lean = Math.min(h / 60, 3)
  const tw = Math.max(w * 0.2, 0.7)
  // The base runs below the surface to the seed, where the roots start,
  // and flares a little there, so stem and roots are one plant.
  const flare = w * 0.18
  return (
    `M${CX - w / 2 - flare} ${SEED_Y} ` +
    `Q${CX - w / 2} ${GROUND} ${CX - w / 2} ${GROUND - h * 0.12} ` +
    `C${CX - w / 2} ${GROUND - h * 0.5} ${CX - tw - lean} ${top + h * 0.25} ${CX - tw} ${top} ` +
    `L${CX + tw} ${top} ` +
    `C${CX + tw + lean} ${top + h * 0.25} ${CX + w / 2} ${GROUND - h * 0.5} ${CX + w / 2} ${GROUND - h * 0.12} ` +
    `Q${CX + w / 2} ${GROUND} ${CX + w / 2 + flare} ${SEED_Y} Z`
  )
})

/** A leaf, pointing out from its stem, with a midrib drawn over it. */
const LEAF = 'M0 0 q6 -11 20 -9 q-4 10 -20 9 z'
const VEIN = 'M1.5 -0.3 q8 -3.4 17 -8.4'

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

type Tone = 'deep' | 'mid' | 'light'
const TONES: Tone[] = ['deep', 'mid', 'light']
const GOLDEN = 2.39996

/**
 * Leaves covering a cluster, so it reads as foliage rather than a disc.
 *
 * Each disc is filled from its centre outward on a sunflower spiral with
 * a fixed spacing, so a growing disc gains leaves at its rim while the
 * ones already there stay put. The outermost leaves reach past the rim,
 * so the silhouette is leafy rather than round. Each leaf points out from
 * the centre, in one of three greens. All by index, never by time.
 */
function cover(prefix: string, discs: Disc[], spacing: number, size: number) {
  return discs.flatMap((disc, d) => {
    const leaves: { key: string; tone: Tone; transform: string }[] = []
    const reach = disc.r * 1.02
    for (let k = 0; ; k++) {
      const radius = Math.sqrt(k + 0.5) * spacing
      if (radius > reach) break
      const angle = k * GOLDEN + d * 0.7
      const x = disc.cx + Math.cos(angle) * radius
      const y = disc.cy + Math.sin(angle) * radius
      // A leaf opens as the rim passes it.
      const open = Math.min(1, (reach - radius) / (spacing * 1.2))
      const heading = (angle * 180) / Math.PI - 20 + ((k * 37) % 40)
      const scale = size * (0.8 + ((k * 7) % 5) * 0.08) * open
      leaves.push({
        key: `${prefix}${d}:${k}`,
        tone: TONES[(k + d) % 3],
        transform: leafTransform(x, y, 1, heading, scale),
      })
    }
    return leaves
  })
}

/** The crown sits on the top of the trunk and spreads out from it. */
const crown = computed(() => {
  const r = v('crown')
  const top = { x: CX, y: GROUND - v('height') + r * 0.2 }
  const discs = foliage(top.x, top.y, r, CLOUD)
  return { discs, leaves: cover('crown', discs, 6, 0.72) }
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
    // A twig per part built, each ending in a small leafy tuft.
    const twigs = branch.leaves.map((leaf, k) => {
      const grown = v(`branch:${i}:leaf:${k}`)
      const { at, dir } = quad(start, bend, tip, 0.3 + 0.12 * k)
      const heading = turn(dir, -base.side * TWIG_TURN[k % 2])
      const twig = sprig(at, heading, 24 * grown, 0.1 * base.side)
      const tuft = foliage(twig.end.x, twig.end.y, 9 * grown)
      return {
        key: `t${leaf.sequence}`,
        d: grown > 0.02 ? twig.d : null,
        tuft,
        leaves: cover(`t${leaf.sequence}:`, tuft, 3, 0.4),
      }
    })
    const cluster = foliage(tip.x, tip.y, v(`branch:${i}:cluster`))
    return {
      key: branch.id,
      label: branch.label,
      path: length > 0.5 ? `M${CX} ${base.y} Q${bend.x} ${bend.y} ${tip.x} ${tip.y}` : null,
      width: 2 + Math.min(branch.leaves.length, 6) * 0.55,
      leaves,
      twigs,
      cluster,
      clusterLeaves: cover(`c${i}:`, cluster, 4.4, 0.54),
      fruit: {
        x: tip.x,
        y: tip.y - v(`branch:${i}:cluster`) * 0.55,
        r: 4.2 * v(`branch:${i}:fruit`),
      },
    }
  }),
)

/**
 * How far along a root's laterals and hairs have come, 0 to 1 each.
 *
 * A stroke that has not started is left out rather than drawn at zero
 * length, because a round cap on an empty dash still paints a dot.
 */
const STARTED = 0.01

function reveal(system: { d: string; laterals: Lateral[] }, grown: number, spread: number) {
  const steps = spread * (system.laterals.length + 1)
  return system.laterals
    .map((lateral, j) => {
      const own = grown * Math.min(1, Math.max(0, steps - j))
      const hairs = grown * Math.min(1, Math.max(0, steps - j - 1))
      return {
        key: j,
        d: lateral.d,
        grown: own,
        hairs: hairs > STARTED ? lateral.hairs : [],
        hairGrown: hairs,
        nodules: lateral.nodules.map((n) => ({ ...n, r: n.r * hairs })),
      }
    })
    .filter((lateral) => lateral.grown > STARTED)
}

/**
 * The roots: a main root per layer, which bushes out into laterals, fine
 * hairs and nodules as the plant above it grows, with finer fibres
 * between them.
 */
const roots = computed(() => {
  const spread = v('rootSpread')
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
      laterals: reveal(system, grown, spread),
    }
  })
})

const fibres = computed(() => {
  if (growth.value.roots.length === 0) return []
  const spread = v('rootSpread')
  return FIBRE_SYSTEM.map((system, f) => {
    // Each fibre starts once the roots have begun to bush out.
    const grown = Math.min(1, Math.max(0, (spread - 0.3 - f * 0.08) / 0.25))
    return {
      key: `fibre${f}`,
      d: system.d,
      grown,
      laterals: reveal(system, grown, grown),
    }
  }).filter((fibre) => fibre.grown > STARTED)
})

/** Refused requests: held above the ground, beside the tree. */
const refused = computed(() =>
  growth.value.waterings
    .filter((w) => w.effect === 'DENY')
    .map((w, i) => ({ ...w, x: CX - 150 + i * 18 })),
)

/** Allowed and escalated requests: the ones that watered the tree. */
const watered = computed(() => growth.value.waterings.length - refused.value.length)

/**
 * Watering, seen as it happens (FR-G3).
 *
 * Each request the protection engine lets through sends a pulse through
 * the plant: the soil and roots take a blue tint for a moment, and the
 * tree glows while it grows a little. The pulse lasts just over a second,
 * long enough to register without holding the eye. A burst of requests
 * reads as one longer watering rather than a flicker: a new pulse starts
 * only once the last one has run. No pulse plays for what a reload
 * replays, or under reduced motion.
 *
 * The pulse alternates between two names so that a pulse straight after
 * another restarts its animation.
 */
const PULSE_MS = 1100
const pulse = ref<'a' | 'b' | null>(null)
let pulsedAt = -Infinity
let pulseTimer = 0
let primed = false
watch(
  watered,
  (count, before) => {
    const now = performance.now()
    const fresh = primed && before !== undefined && count > before
    primed = true
    if (!fresh || reduced || now - pulsedAt < PULSE_MS) return
    pulsedAt = now
    pulse.value = pulse.value === 'a' ? 'b' : 'a'
    window.clearTimeout(pulseTimer)
    pulseTimer = window.setTimeout(() => (pulse.value = null), PULSE_MS)
  },
  { immediate: true },
)
onBeforeUnmount(() => window.clearTimeout(pulseTimer))

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
  <figure class="tree" :aria-label="`Growth: ${caption.stage}`" :data-pulse="pulse">
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
        <!-- A leaf, drawn once and placed everywhere: the blade takes the
             fill of wherever it is used, the midrib is a lighter line. -->
        <g :id="ids.leaf">
          <path :d="LEAF" />
          <path
            :d="VEIN"
            fill="none"
            stroke="#fff"
            stroke-opacity="0.32"
            stroke-width="0.9"
            stroke-linecap="round"
          />
        </g>
        <!-- Foliage has volume: lit from the upper left, darker at the rim. -->
        <radialGradient :id="ids.canopy" cx="0.38" cy="0.32" r="0.75">
          <stop offset="0" class="leaf-light-stop" />
          <stop offset="0.6" class="leaf-stop" />
          <stop offset="1" class="leaf-deep-stop" />
        </radialGradient>
        <radialGradient :id="ids.canopyDeep" cx="0.38" cy="0.32" r="0.75">
          <stop offset="0" class="leaf-stop" />
          <stop offset="1" class="leaf-deep-stop" />
        </radialGradient>
        <!-- Bark: fine vertical furrows, and a round-stem shading. -->
        <pattern :id="ids.bark" patternUnits="userSpaceOnUse" width="7" height="18">
          <path
            d="M1.5 0 q1.4 4.5 0 9 q-1.4 4.5 0 9 M5 -4 q1.2 5 0 10 q-1.2 5 0 10 M3.4 4 l0 5"
            fill="none"
            stroke="#000"
            stroke-opacity="0.32"
            stroke-width="0.8"
          />
        </pattern>
        <linearGradient :id="ids.shade" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#fff" stop-opacity="0.2" />
          <stop offset="0.45" stop-color="#fff" stop-opacity="0" />
          <stop offset="1" stop-color="#000" stop-opacity="0.3" />
        </linearGradient>
        <!-- Roots stay below the surface, however they branch. -->
        <clipPath :id="ids.underground">
          <rect x="0" :y="GROUND + 0.5" width="520" :height="SOIL_DEPTH + 40" />
        </clipPath>
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
      <rect
        class="soak"
        :x="SOIL_X"
        :y="GROUND"
        :width="SOIL_W"
        :height="SOIL_DEPTH"
        :mask="`url(#${ids.mask})`"
      />
      <rect :x="SOIL_X" :y="GROUND - 1" :width="SOIL_W" height="2" :fill="`url(#${ids.line})`" />
      <g
        v-for="fibre in fibres"
        :key="fibre.key"
        class="roots fibre"
        :clip-path="`url(#${ids.underground})`"
      >
        <path
          class="root"
          :d="fibre.d"
          stroke-width="1.1"
          pathLength="1"
          stroke-dasharray="1"
          :stroke-dashoffset="1 - fibre.grown"
        />
        <template v-for="lateral in fibre.laterals" :key="lateral.key">
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
      <g
        v-for="root in roots"
        :key="root.key"
        class="roots"
        :clip-path="`url(#${ids.underground})`"
      >
        <title>{{ root.label }}</title>
        <path
          class="root"
          :d="root.d"
          :stroke-width="root.girth"
          pathLength="1"
          stroke-dasharray="1"
          :stroke-dashoffset="1 - root.grown"
        />
        <template v-for="lateral in root.laterals" :key="lateral.key">
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
          <template v-for="(nodule, n) in lateral.nodules" :key="`n${n}`">
            <circle
              v-if="nodule.r > 0.2"
              class="nodule"
              :cx="nodule.x"
              :cy="nodule.y"
              :r="nodule.r"
            />
          </template>
        </template>
      </g>
      <ellipse v-if="v('seed') > 0" class="seed" :cx="CX" :cy="SEED_Y" rx="7" ry="4.5" />

      <!-- Refused requests: held above the ground; they fed nothing. -->
      <g v-for="drop in refused" :key="drop.sequence" class="refused">
        <title>Refused under {{ drop.rule }}: {{ drop.label }}. It watered nothing.</title>
        <path :d="`M${drop.x} ${GROUND - 26} q6 9 0 14 q-6 -5 0 -14 z`" />
        <line :x1="drop.x - 8" :x2="drop.x + 8" :y1="GROUND - 8" :y2="GROUND - 8" />
      </g>

      <g class="plant">
        <!-- The crown behind, then the trunk and its stem leaves, then the
           branches of the build with their twigs and foliage, and the
           crown's leaves over all of it. -->
        <circle
          v-for="(disc, d) in crown.discs"
          :key="`crown${d}`"
          class="canopy deep"
          :cx="disc.cx"
          :cy="disc.cy"
          :r="disc.r"
        />
        <g v-if="trunk">
          <path class="trunk" :d="trunk" :style="{ fill: wood.trunk }" />
          <path :d="trunk" :fill="`url(#${ids.bark})`" :opacity="wood.furrows" />
          <path :d="trunk" :fill="`url(#${ids.shade})`" />
        </g>
        <use
          v-for="leaf in stemLeaves"
          :key="leaf.key"
          class="leaf"
          :href="`#${ids.leaf}`"
          :transform="leaf.transform"
        >
          <title>{{ leaf.label }}</title>
        </use>
        <g v-for="branch in branches" :key="branch.key" class="branch">
          <title>{{ branch.label }}</title>
          <path
            v-if="branch.path"
            class="twig"
            :d="branch.path"
            :stroke-width="branch.width"
            :style="{ stroke: wood.branch }"
          />
          <g v-for="twig in branch.twigs" :key="twig.key">
            <path
              v-if="twig.d"
              class="twig"
              :d="twig.d"
              stroke-width="1.4"
              :style="{ stroke: wood.twig }"
            />
            <circle
              v-for="(disc, d) in twig.tuft"
              :key="`f${d}`"
              class="canopy"
              :cx="disc.cx"
              :cy="disc.cy"
              :r="disc.r"
            />
            <use
              v-for="leaf in twig.leaves"
              :key="leaf.key"
              class="leaf"
              :data-tone="leaf.tone"
              :href="`#${ids.leaf}`"
              :transform="leaf.transform"
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
          <use
            v-for="leaf in branch.clusterLeaves"
            :key="leaf.key"
            class="leaf"
            :data-tone="leaf.tone"
            :href="`#${ids.leaf}`"
            :transform="leaf.transform"
          />
          <use
            v-for="leaf in branch.leaves"
            :key="leaf.key"
            class="leaf"
            :href="`#${ids.leaf}`"
            :transform="leaf.transform"
          >
            <title>{{ leaf.label }}</title>
          </use>
        </g>
        <use
          v-for="leaf in crown.leaves"
          :key="leaf.key"
          class="leaf"
          :data-tone="leaf.tone"
          :href="`#${ids.leaf}`"
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
      </g>

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
  stroke-width: 1.1;
}

.hair {
  stroke-width: 0.6;
  opacity: 0.75;
}

.fibre .root {
  opacity: 0.85;
}

.nodule {
  fill: var(--growth-nodule);
}

.seed {
  fill: var(--growth-root);
}

.twig {
  fill: none;
  stroke-linecap: round;
}

.leaf {
  fill: var(--growth-leaf);
}

.leaf[data-tone='deep'] {
  fill: var(--growth-leaf-deep);
}

.leaf[data-tone='light'] {
  fill: var(--growth-leaf-light);
}

.leaf-stop {
  stop-color: var(--growth-leaf);
}

.leaf-deep-stop {
  stop-color: var(--growth-leaf-deep);
}

.leaf-light-stop {
  stop-color: var(--growth-leaf-light);
}

.canopy {
  fill: url(#growth-canopy);
}

.canopy.deep {
  fill: url(#growth-canopy-deep);
}

.fruit {
  fill: var(--growth-bud);
}

.refused path {
  fill: none;
  stroke: var(--text-muted);
}

.refused line {
  stroke: var(--text-muted);
}

.tally {
  fill: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
}

/* Watering: a blue tint through the soil and roots, and a glow on the
   plant as it grows a little. Two identical animations, so a pulse
   straight after another restarts. */
.soak {
  fill: var(--growth-water);
  opacity: 0;
}

.tree[data-pulse='a'] .soak {
  animation: soak-a 1100ms var(--ease-out);
}

.tree[data-pulse='b'] .soak {
  animation: soak-b 1100ms var(--ease-out);
}

.tree[data-pulse='a'] .root {
  animation: root-a 1100ms var(--ease-out);
}

.tree[data-pulse='b'] .root {
  animation: root-b 1100ms var(--ease-out);
}

.tree[data-pulse='a'] .plant {
  animation: glow-a 1100ms var(--ease-out);
}

.tree[data-pulse='b'] .plant {
  animation: glow-b 1100ms var(--ease-out);
}

@keyframes soak-a {
  25% {
    opacity: 0.28;
  }
}

@keyframes soak-b {
  25% {
    opacity: 0.28;
  }
}

@keyframes root-a {
  25% {
    stroke: var(--growth-root-wet);
  }
}

@keyframes root-b {
  25% {
    stroke: var(--growth-root-wet);
  }
}

@keyframes glow-a {
  30% {
    filter: drop-shadow(0 0 6px var(--growth-glow));
  }
}

@keyframes glow-b {
  30% {
    filter: drop-shadow(0 0 6px var(--growth-glow));
  }
}

@media (prefers-reduced-motion: reduce) {
  .tree[data-pulse] .soak,
  .tree[data-pulse] .root,
  .tree[data-pulse] .plant {
    animation: none;
  }
}
</style>
