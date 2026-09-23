<script setup lang="ts">
import type { EChartsType } from 'echarts/core'
import { computed } from 'vue'

import EChart from '../../charts/EChart.vue'
import { readTokens, seriesOption, treemapOption } from '../../charts/options'
import type { Format } from '../../design/format'
import {
  useDashboardStore,
  type ChartSpec,
  type Filter,
  type Role,
  type SeriesChartResult,
  type Step,
  type TreemapResult,
} from '../../stores/dashboard'
import { useThemeStore } from '../../stores/theme'

const props = defineProps<{
  chart: ChartSpec
  result: SeriesChartResult | TreemapResult | undefined
}>()

const emit = defineEmits<{ apply: [step: Step] }>()

/**
 * One chart of any dashboard: title, the question it answers, the chart,
 * its legend and its caveats.
 *
 * Every click becomes a drill step whose filter is the one the backend
 * attached to the datum, so this card never decides what a bar or a cell
 * means (FR-EV2). A line's months can also be brushed into a range.
 */
const dashboard = useDashboardStore()
const theme = useThemeStore()

const HEIGHTS = { compact: 190, regular: 250, tall: 390 } as const
const height = computed(() => HEIGHTS[props.chart.layout.height])

const motion =
  typeof window !== 'undefined' &&
  !window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** The declared format of each series the result drew. */
const formats = computed<Format[]>(() => {
  const result = props.result
  if (!result || result.mark === 'treemap') return []
  return result.series.map((s) => {
    if (props.chart.normalise) return 'percent'
    const id = props.chart.series ? props.chart.measures[0]?.measure : s.key
    return dashboard.measure(id ?? '')?.format ?? 'integer'
  })
})

const plural = computed(() => dashboard.descriptor?.entity.plural ?? 'rows')

const option = computed(() => {
  // Theme is read so a theme change repaints from the new tokens (D-5).
  void theme.theme
  const result = props.result
  if (!result) return null
  const tokens = readTokens()
  if (result.mark === 'treemap') {
    const measure = dashboard.measure(props.chart.size ?? '')
    return measure ? treemapOption(props.chart, result, measure, tokens, motion) : null
  }
  return seriesOption(props.chart, result, formats.value, tokens, motion, (n) =>
    `Withheld · ${n.toLocaleString('en-GB')} ${plural.value}`,
  )
})

// -- Legend ----------------------------------------------------------------

interface Entry {
  key: string
  label: string
  role: Role | null
  filter: Filter | null
}

const legend = computed<Entry[]>(() => {
  const result = props.result
  if (!result) return []
  if (result.mark === 'treemap') {
    const by = result.colourBy
    if (!by) return []
    const seen = new Set<string>()
    const walk = (nodes: typeof result.nodes) => {
      for (const n of nodes) {
        if (n.colourValue) seen.add(n.colourValue)
        walk(n.children)
      }
    }
    walk(result.nodes)
    return paletteEntries(by, seen)
  }
  if (result.roles && props.chart.colour) {
    const by = props.chart.colour.by
    const palette = dashboard.palettes[by] ?? {}
    const seen = new Set(
      Object.entries(palette)
        .filter(([, role]) => result.roles?.includes(role))
        .map(([value]) => value),
    )
    return paletteEntries(by, seen)
  }
  return result.series.map((s) => ({ key: s.key, label: s.label, role: s.role, filter: s.filter }))
})

function paletteEntries(dimension: string, present: Set<string>): Entry[] {
  const palette = dashboard.palettes[dimension] ?? {}
  const labels = dashboard.dimension(dimension)?.labels ?? {}
  return (dashboard.domains[dimension] ?? [])
    .filter((value) => present.has(value))
    .map((value) => ({
      key: value,
      label: labels[value] ?? value,
      role: palette[value] ?? null,
      filter: props.chart.interaction.click === 'none' ? null : { [dimension]: [value] },
    }))
}

const colourTitle = computed(() => {
  const result = props.result
  const by = result?.mark === 'treemap' ? result.colourBy : props.chart.colour?.by
  return by ? dashboard.dimension(by)?.label : null
})

// -- Caveats -----------------------------------------------------------------

const ignored = computed(() =>
  (props.result?.ignored ?? []).map((id) => dashboard.dimension(id)?.label ?? id),
)

const truncated = computed(() => {
  const result = props.result
  return result && result.mark !== 'treemap' ? result.truncated : 0
})

// -- Interaction -----------------------------------------------------------

function applyFilter(filter: Filter | null, label: string): void {
  if (filter && Object.keys(filter).length) {
    emit('apply', { label, dimensions: filter })
  }
}

function onSelect(params: Record<string, unknown>): void {
  const result = props.result
  if (!result || props.chart.interaction.click === 'none') return
  if (result.mark === 'treemap') {
    const data = params.data as { filter?: Filter; name?: string } | undefined
    applyFilter(data?.filter ?? null, data?.name ?? String(params.name))
    return
  }
  // A click on an axis label selects the category.
  if (params.componentType === 'xAxis' || params.componentType === 'yAxis') {
    const category = result.categories.find((c) => c.label === params.value)
    if (category) applyFilter(category.filter, category.label)
    return
  }
  const index = params.dataIndex as number
  const category = result.categories[index]
  const series = result.series[params.seriesIndex as number]
  if (!category) return
  const filter = { ...(category.filter ?? {}), ...(series?.filter ?? {}) }
  const label = series?.filter ? `${category.label} · ${series.label}` : category.label
  applyFilter(filter, label)
}

/** A click on a line's plot area: the nearest month, and the nearest line. */
function onPlot(point: [number, number], chart: EChartsType): void {
  const result = props.result
  if (!result || result.mark !== 'line' || props.chart.interaction.click === 'none') return
  if (!chart.containPixel({ gridIndex: 0 }, point)) return
  const [index, value] = chart.convertFromPixel({ gridIndex: 0 }, point) as [number, number]
  const category = result.categories[Math.round(index)]
  if (!category) return
  let nearest = null as (typeof result.series)[number] | null
  if (props.chart.series) {
    let gap = Infinity
    for (const s of result.series) {
      const v = s.values[Math.round(index)]
      if (v !== null && Math.abs(v - value) < gap) {
        gap = Math.abs(v - value)
        nearest = s
      }
    }
  }
  const filter = { ...(category.filter ?? {}), ...(nearest?.filter ?? {}) }
  applyFilter(filter, nearest ? `${category.label} · ${nearest.label}` : category.label)
}

/** A brushed range of categories: one step filtering to all of them. */
function onRange(from: number, to: number): void {
  const result = props.result
  if (!result || result.mark === 'treemap' || !props.chart.x) return
  const chosen = result.categories.slice(Math.max(0, from), Math.max(from, to) + 1)
  if (!chosen.length) return
  const label =
    chosen.length === 1 ? chosen[0].label : `${chosen[0].label} – ${chosen[chosen.length - 1].label}`
  applyFilter({ [props.chart.x]: chosen.map((c) => c.key) }, label)
}
</script>

<template>
  <article
    class="card"
    :data-emphasis="chart.layout.emphasis"
    :style="{ gridColumn: `span ${chart.layout.span}` }"
  >
    <header class="head">
      <h3 class="title">{{ chart.title }}</h3>
      <p class="question">{{ chart.question }}</p>
    </header>

    <div v-if="!result" class="placeholder" :style="{ height: `${height}px` }" />
    <p v-else-if="result.empty" class="empty" :style="{ height: `${height}px` }">
      {{ chart.empty }}
    </p>
    <EChart
      v-else-if="option"
      :option="option"
      :height="height"
      :brush="chart.interaction.brush"
      @select="onSelect"
      @plot="onPlot"
      @range="onRange"
    />

    <footer v-if="legend.length || chart.note || ignored.length || truncated" class="foot">
      <ul v-if="legend.length" class="legend" :aria-label="colourTitle ?? 'Legend'">
        <li v-for="entry in legend" :key="entry.key">
          <button
            type="button"
            class="entry"
            :disabled="!entry.filter"
            @click="applyFilter(entry.filter, entry.label)"
          >
            <span class="swatch" :style="{ background: `var(--chart-${entry.role ?? 'muted'})` }" />
            {{ entry.label }}
          </button>
        </li>
      </ul>
      <p v-if="truncated" class="caveat">Largest shown; {{ truncated }} more not drawn.</p>
      <p v-if="ignored.length" class="caveat">Not narrowed by {{ ignored.join(', ') }}.</p>
      <p v-if="chart.note" class="caveat">{{ chart.note }}</p>
      <p v-if="chart.interaction.brush" class="caveat">Drag across months to select a range.</p>
    </footer>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4) var(--space-5);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.card[data-emphasis='primary'] {
  border-color: var(--border-default);
}

.head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.title {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
}

.question {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.placeholder {
  background: var(--surface-sunken);
  border-radius: var(--radius-sm);
}

.empty {
  display: grid;
  place-items: center;
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  background: var(--surface-sunken);
  border-radius: var(--radius-sm);
}

.foot {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.entry {
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
  padding: 0;
  color: var(--text-secondary);
  background: none;
  border: none;
  font-size: var(--text-xs);
}

.entry:not(:disabled):hover {
  color: var(--text-primary);
}

.entry:disabled {
  cursor: default;
}

.swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.caveat {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
}
</style>
