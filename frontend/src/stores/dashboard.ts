import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { Format } from '../design/format'

/*
 * The wire types, mirroring backend/app/analytics/schema.py and the query
 * engine's answers. A dashboard is data (D-1): nothing below names a
 * methodology, and the renderer draws whatever descriptor it is given.
 */

export type Role =
  | 'series-1'
  | 'series-2'
  | 'series-3'
  | 'series-4'
  | 'series-5'
  | 'series-6'
  | 'series-7'
  | 'series-8'
  | 'positive'
  | 'warning'
  | 'negative'
  | 'anomaly'
  | 'baseline'
  | 'muted'

export type Filter = Record<string, string[]>

export interface DimensionSpec {
  id: string
  label: string
  column: string
  order: string[] | null
  labels: Record<string, string> | null
  colour: string | null
  frame: string | null
}

export interface MeasureSpec {
  id: string
  label: string
  agg: string
  format: Format
  frame: string
  withhold: boolean
  note: string | null
}

export interface LayoutSpec {
  span: number
  height: 'compact' | 'regular' | 'tall'
  emphasis: 'primary' | 'secondary'
}

export interface KpiSpec {
  id: string
  label: string
  measure: string
  emphasis: 'primary' | 'secondary'
  context: 'of-total' | null
  note: string | null
}

export interface ChartSpec {
  id: string
  title: string
  question: string
  mark: 'line' | 'bar' | 'treemap'
  x: string | null
  series: string | null
  measures: { measure: string; role: Role; axis: 'primary' | 'secondary' }[]
  path: string[]
  size: string | null
  colour: { by: string; refine: string | null } | null
  orientation: 'vertical' | 'horizontal'
  stacked: boolean
  normalise: boolean
  interaction: { click: 'filter' | 'drill' | 'entity' | 'none'; brush: boolean }
  layout: LayoutSpec
  empty: string
  note: string | null
}

export interface ColumnSpec {
  field: string
  label: string
  format: Format
  chip: string | null
  chipWhen: string | null
  align: 'left' | 'right'
  unitFromFinding: boolean
}

export interface TableSpec {
  id: string
  title: string
  question: string
  kind: 'summary' | 'records'
  groupBy: string[]
  columns: ColumnSpec[]
  sortBy: string
  descending: boolean
  pageSize: number
  rowAction: 'filter' | 'entity' | 'none'
  layout: LayoutSpec
  empty: string
}

export interface SectionSpec {
  id: string
  kind: 'kpis' | 'grid' | 'table'
  title: string | null
  views: string[]
}

export interface Descriptor {
  solutionId: string
  title: string
  subtitle: string
  entity: { label: string; plural: string; id: string; title: string }
  dimensions: DimensionSpec[]
  measures: MeasureSpec[]
  kpis: KpiSpec[]
  charts: ChartSpec[]
  tables: TableSpec[]
  sections: SectionSpec[]
  hierarchy: { id: string; label: string; dimension: string | null; entity: boolean }[]
  evidence: { dimension: string; methodology: string }
  simulated: boolean
}

export interface KpiResult {
  id: string
  value: number | null
  total?: number | null
  withheld: number | null
  ignored: string[]
}

export interface Category {
  key: string
  label: string
  filter: Filter | null
}

export interface SeriesResult {
  key: string
  label: string
  role: Role
  axis: 'primary' | 'secondary'
  values: (number | null)[]
  filter: Filter | null
}

export interface SeriesChartResult {
  id: string
  mark: 'line' | 'bar'
  categories: Category[]
  series: SeriesResult[]
  roles: (Role | null)[] | null
  withheld: number[] | null
  truncated: number
  empty: boolean
  ignored: string[]
}

export interface TreeNode {
  key: string
  label: string
  value: number
  role: Role | null
  colourValue: string | null
  filter: Filter | null
  children: TreeNode[]
}

export interface TreemapResult {
  id: string
  mark: 'treemap'
  colourBy: string | null
  nodes: TreeNode[]
  total: number
  empty: boolean
  ignored: string[]
}

export interface SummaryResult {
  id: string
  kind: 'summary'
  rows: {
    key: string
    cells: Record<string, unknown>
    filter: Filter
    unit?: Format | null
    metricLabel?: string | null
  }[]
  total: number
  ignored: string[]
}

export interface RecordsResult {
  id: string
  kind: 'records'
  rows: { id: string; cells: Record<string, unknown> }[]
  total: number
  page: number
  pageSize: number
  sortBy: string
  descending: boolean
  ignored: string[]
}

export type ViewResult =
  | KpiResult
  | SeriesChartResult
  | TreemapResult
  | SummaryResult
  | RecordsResult

export interface DrillLevel {
  id: string
  label: string
  dimension: string | null
  value: string | null
  valueLabel: string | null
}

export interface Drill {
  root: string
  levels: DrillLevel[]
  next: string | null
}

export interface EvidenceResult {
  status: 'empty' | 'none' | 'choose' | 'finding' | 'insufficient'
  message?: string | null
  dimension: string
  selected: number
  findings?: { value: string; title: string; count: number; role: Role | null; filter: Filter }[]
  finding?: { value: string; title: string; description: string; role: Role | null }
  records?: { count: number; sample: string[]; filter: Filter }
  methodology?: { id: string; name: string; process: string[] }
  validation?: string[]
  metric?: { label: string | null; unit: Format }
  observed?: number | null
  baseline?: number | null
  deviation?: number | null
  comparable?: { size: number; by: string[]; where: string[] }
  score?: number | null
  entity?: string | null
  simulated: boolean
}

/**
 * One step of the drill path: what a click added, and its name in the
 * breadcrumb (FR-EV5). The filter in force is these steps folded in
 * order, so the breadcrumb and the filter can never disagree (D-3).
 */
export interface Step {
  label: string
  dimensions?: Filter
  entityId?: string
}

export interface Context {
  dimensions: Filter
  entityId: string | null
}

export function fold(steps: Step[]): Context {
  const dimensions: Filter = {}
  let entityId: string | null = null
  for (const step of steps) {
    Object.assign(dimensions, step.dimensions ?? {})
    if (step.entityId !== undefined) entityId = step.entityId
  }
  return { dimensions, entityId }
}

function same(a: Context, b: Context): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

// -- The URL (D-3) -------------------------------------------------------

interface Location {
  dashboard: string | null
  steps: Step[]
}

function readUrl(): Location {
  const params = new URLSearchParams(window.location.search)
  let steps: Step[] = []
  try {
    const raw = params.get('drill')
    steps = raw ? (JSON.parse(raw) as Step[]) : []
  } catch {
    steps = []
  }
  return { dashboard: params.get('dashboard'), steps }
}

function writeUrl(location: Location, push: boolean): void {
  const params = new URLSearchParams()
  if (location.dashboard) params.set('dashboard', location.dashboard)
  if (location.dashboard && location.steps.length) {
    params.set('drill', JSON.stringify(location.steps))
  }
  const query = params.toString()
  const url = `${window.location.pathname}${query ? `?${query}` : ''}`
  if (url === `${window.location.pathname}${window.location.search}`) return
  if (push) {
    window.history.pushState(null, '', url)
  } else {
    window.history.replaceState(null, '', url)
  }
}

async function post<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) {
    throw new Error(`${url}: ${response.status}`)
  }
  return (await response.json()) as T
}

/**
 * The open dashboard: its descriptor, the drill path, and the figures the
 * backend returned for it.
 *
 * The filter context lives in the URL, with this store as its in-memory
 * mirror (D-3). Each click pushes one history entry, so the browser's Back
 * pops exactly one drill step, and a rehearsal can open a dashboard at
 * any drill position straight from a link, without replaying the
 * narrative. All aggregation is the backend's; this holds answers.
 */
export const useDashboardStore = defineStore('dashboard', () => {
  const solutionId = ref<string | null>(null)
  const descriptor = ref<Descriptor | null>(null)
  const domains = ref<Record<string, string[]>>({})
  const palettes = ref<Record<string, Record<string, Role>>>({})

  const steps = ref<Step[]>([])
  const results = ref<Record<string, ViewResult>>({})
  const drill = ref<Drill | null>(null)
  const evidence = ref<EvidenceResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** A dashboard named in the URL, opened for rehearsal (D-3). */
  const rehearsal = ref<string | null>(readUrl().dashboard)

  const context = computed(() => fold(steps.value))
  let controller: AbortController | null = null
  let pushed = 0

  function measure(id: string): MeasureSpec | undefined {
    return descriptor.value?.measures.find((m) => m.id === id)
  }

  function dimension(id: string): DimensionSpec | undefined {
    return descriptor.value?.dimensions.find((d) => d.id === id)
  }

  function request(): { filter: { dimensions: Filter; entityId: string | null } } {
    return { filter: { dimensions: context.value.dimensions, entityId: context.value.entityId } }
  }

  async function refresh(): Promise<void> {
    if (!solutionId.value) return
    controller?.abort()
    controller = new AbortController()
    const base = `/api/analytics/${encodeURIComponent(solutionId.value)}`
    loading.value = true
    try {
      const [answer, why] = await Promise.all([
        post<{ views: Record<string, ViewResult>; drill: Drill }>(
          `${base}/query`,
          request(),
          controller.signal,
        ),
        post<EvidenceResult>(`${base}/evidence`, request(), controller.signal),
      ])
      results.value = answer.views
      drill.value = answer.drill
      evidence.value = why
      error.value = null
    } catch (caught) {
      if ((caught as Error).name !== 'AbortError') {
        error.value = (caught as Error).message
      }
    } finally {
      loading.value = false
    }
  }

  async function open(id: string): Promise<void> {
    if (solutionId.value === id && descriptor.value) return
    solutionId.value = id
    descriptor.value = null
    results.value = {}
    const response = await fetch(`/api/analytics/${encodeURIComponent(id)}/dashboard`)
    if (!response.ok) {
      error.value = `No dashboard for ${id}.`
      return
    }
    const body = (await response.json()) as {
      descriptor: Descriptor
      domains: Record<string, string[]>
      palettes: Record<string, Record<string, Role>>
    }
    descriptor.value = body.descriptor
    domains.value = body.domains
    palettes.value = body.palettes
    const location = readUrl()
    steps.value = location.dashboard === id ? location.steps : []
    pushed = 0
    writeUrl({ dashboard: id, steps: steps.value }, false)
    await refresh()
  }

  function close(): void {
    controller?.abort()
    solutionId.value = null
    descriptor.value = null
    results.value = {}
    drill.value = null
    evidence.value = null
    steps.value = []
    rehearsal.value = null
    writeUrl({ dashboard: null, steps: [] }, false)
  }

  /** Add a drill step, unless it changes nothing. */
  function apply(step: Step): void {
    const next = [...steps.value, step]
    if (same(fold(next), context.value)) return
    steps.value = next
    pushed += 1
    writeUrl({ dashboard: solutionId.value, steps: next }, true)
    void refresh()
  }

  /** Back one step: the browser's Back, so the two can never disagree. */
  function back(): void {
    if (!steps.value.length) return
    if (pushed > 0) {
      window.history.back()
      return
    }
    steps.value = steps.value.slice(0, -1)
    writeUrl({ dashboard: solutionId.value, steps: steps.value }, false)
    void refresh()
  }

  /** Return to a breadcrumb position; `0` is the whole dashboard. */
  function jump(index: number): void {
    if (index >= steps.value.length) return
    steps.value = steps.value.slice(0, index)
    pushed += 1
    writeUrl({ dashboard: solutionId.value, steps: steps.value }, true)
    void refresh()
  }

  /** A page or a new sort of a record table. */
  async function page(tableId: string, pageNumber: number, sortBy?: string, descending?: boolean): Promise<void> {
    if (!solutionId.value) return
    const answer = await post<RecordsResult & { elapsedMs: number }>(
      `/api/analytics/${encodeURIComponent(solutionId.value)}/records`,
      { ...request(), table: tableId, page: pageNumber, sortBy, descending },
    )
    results.value = { ...results.value, [tableId]: answer }
  }

  window.addEventListener('popstate', () => {
    const location = readUrl()
    rehearsal.value = location.dashboard
    if (location.dashboard && location.dashboard === solutionId.value) {
      pushed = Math.max(0, pushed - 1)
      steps.value = location.steps
      void refresh()
    }
  })

  return {
    solutionId,
    descriptor,
    domains,
    palettes,
    steps,
    results,
    drill,
    evidence,
    loading,
    error,
    rehearsal,
    context,
    measure,
    dimension,
    open,
    close,
    apply,
    back,
    jump,
    page,
    refresh,
  }
})

/** Open a dashboard for rehearsal, from the operator panel (D-3). */
export function rehearse(id: string): void {
  writeUrl({ dashboard: id, steps: [] }, true)
  useDashboardStore().rehearsal = id
}
