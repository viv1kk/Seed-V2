<script setup lang="ts">
import { computed } from 'vue'

import { formatValue, type Format } from '../../design/format'
import {
  useDashboardStore,
  type ColumnSpec,
  type RecordsResult,
  type Step,
  type SummaryResult,
  type TableSpec,
} from '../../stores/dashboard'

const props = defineProps<{
  table: TableSpec
  result: SummaryResult | RecordsResult | undefined
}>()

const emit = defineEmits<{ apply: [step: Step] }>()

/**
 * A table of any dashboard: a summary with one row per group, or the
 * records behind every figure above it (OQ-1, FR-EV6).
 *
 * A summary row drills into its group; a record row opens that record,
 * which narrows every view to it and explains it in the evidence panel.
 * Record tables page and sort on the server, over the same filter.
 */
const dashboard = useDashboardStore()

const records = computed(() => (props.result?.kind === 'records' ? props.result : null))
const summary = computed(() => (props.result?.kind === 'summary' ? props.result : null))

interface Row {
  key: string
  cells: Record<string, unknown>
  unit?: Format | null
  step: Step | null
}

const rows = computed<Row[]>(() => {
  const entity = dashboard.descriptor?.entity
  if (summary.value) {
    return summary.value.rows.map((row) => ({
      key: row.key,
      cells: row.cells,
      unit: row.unit,
      step: props.table.rowAction === 'filter' ? { label: row.key, dimensions: row.filter } : null,
    }))
  }
  return (records.value?.rows ?? []).map((row) => ({
    key: row.id,
    cells: row.cells,
    step:
      props.table.rowAction === 'entity'
        ? { label: String(row.cells[entity?.title ?? ''] ?? row.id), entityId: row.id }
        : null,
  }))
})

function withheld(column: ColumnSpec): boolean {
  return Boolean(dashboard.measure(column.field)?.withhold)
}

function cell(row: Row, column: ColumnSpec): string {
  const value = row.cells[column.field]
  if (value === null && withheld(column)) return 'Withheld'
  const format = column.unitFromFinding && row.unit ? row.unit : column.format
  return formatValue(value, format)
}

function chip(column: ColumnSpec, row: Row): string | null {
  if (!column.chip) return null
  if (column.chipWhen && dashboard.context.dimensions[column.chipWhen]?.length !== 1) return null
  const value = row.cells[column.field]
  if (value === null || value === undefined) return null
  return dashboard.palettes[column.chip]?.[String(value)] ?? null
}

const selected = computed(() => dashboard.context.entityId)

const footer = computed(() => {
  const plural = dashboard.descriptor?.entity.plural ?? 'rows'
  if (summary.value) {
    const shown = summary.value.rows.length
    return shown < summary.value.total ? `${shown} of ${summary.value.total}` : `${shown}`
  }
  const r = records.value
  if (!r || !r.total) return `0 ${plural}`
  const first = r.page * r.pageSize + 1
  const last = Math.min(r.total, first + r.rows.length - 1)
  return `${first.toLocaleString('en-GB')}–${last.toLocaleString('en-GB')} of ${r.total.toLocaleString('en-GB')} ${plural}`
})

const pages = computed(() => {
  const r = records.value
  return r ? Math.max(1, Math.ceil(r.total / r.pageSize)) : 1
})

function turn(delta: number): void {
  const r = records.value
  if (!r) return
  const next = r.page + delta
  if (next < 0 || next >= pages.value) return
  void dashboard.page(props.table.id, next, r.sortBy, r.descending)
}

function sort(column: ColumnSpec): void {
  const r = records.value
  if (!r) return
  const descending = r.sortBy === column.field ? !r.descending : true
  void dashboard.page(props.table.id, 0, column.field, descending)
}

function open(row: Row): void {
  if (row.step) emit('apply', row.step)
}
</script>

<template>
  <section class="table" :style="{ gridColumn: `span ${table.layout.span}` }">
    <header class="head">
      <div>
        <h3 class="title">{{ table.title }}</h3>
        <p class="question">{{ table.question }}</p>
      </div>
      <span class="count mono">{{ footer }}</span>
    </header>

    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th
              v-for="column in table.columns"
              :key="column.field"
              :data-align="column.align"
              :data-sortable="Boolean(records)"
              :aria-sort="
                records?.sortBy === column.field
                  ? records.descending
                    ? 'descending'
                    : 'ascending'
                  : undefined
              "
              @click="sort(column)"
            >
              {{ column.label }}
              <span v-if="records?.sortBy === column.field" class="arrow">{{
                records.descending ? '↓' : '↑'
              }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.key"
            :data-clickable="Boolean(row.step)"
            :data-selected="records !== null && row.key === selected"
            @click="open(row)"
          >
            <td
              v-for="column in table.columns"
              :key="column.field"
              :data-align="column.align"
              :class="{ mono: column.format !== 'text', withheld: cell(row, column) === 'Withheld' }"
            >
              <span v-if="chip(column, row)" class="chip">
                <span class="swatch" :style="{ background: `var(--chart-${chip(column, row)})` }" />
                {{ cell(row, column) }}
              </span>
              <template v-else>{{ cell(row, column) }}</template>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td :colspan="table.columns.length" class="empty">{{ table.empty }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="records && pages > 1" class="pager">
      <button type="button" class="turn" :disabled="records.page === 0" @click="turn(-1)">
        ← Previous
      </button>
      <span class="mono">Page {{ records.page + 1 }} of {{ pages.toLocaleString('en-GB') }}</span>
      <button
        type="button"
        class="turn"
        :disabled="records.page + 1 >= pages"
        @click="turn(1)"
      >
        Next →
      </button>
    </footer>
  </section>
</template>

<style scoped>
.table {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
  padding: var(--space-4) var(--space-5);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
}

.title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
}

.question {
  margin: 2px 0 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.count {
  color: var(--text-muted);
  font-size: var(--text-xs);
  white-space: nowrap;
}

.mono {
  font-family: var(--font-mono);
}

.scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-xs);
}

th {
  padding: var(--space-2) var(--space-3);
  color: var(--text-muted);
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border-default);
}

th[data-sortable='true'] {
  cursor: pointer;
}

th[data-sortable='true']:hover {
  color: var(--text-primary);
}

th[data-align='right'],
td[data-align='right'] {
  text-align: right;
}

.arrow {
  color: var(--accent);
}

td {
  padding: 6px var(--space-3);
  color: var(--text-primary);
  white-space: nowrap;
  border-bottom: 1px solid var(--border-subtle);
}

tr[data-clickable='true'] {
  cursor: pointer;
}

tr[data-clickable='true']:hover td {
  background: var(--surface-sunken);
}

tr[data-selected='true'] td {
  background: var(--accent-subtle);
}

.withheld {
  color: var(--text-muted);
  font-style: italic;
}

.chip {
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
}

.swatch {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.empty {
  padding: var(--space-6);
  color: var(--text-muted);
  text-align: center;
}

.pager {
  display: flex;
  gap: var(--space-4);
  align-items: center;
  justify-content: flex-end;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.turn {
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.turn:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
