<script setup lang="ts">
import { computed } from 'vue'

import { formatValue } from '../../design/format'
import { useDashboardStore, type KpiResult, type KpiSpec } from '../../stores/dashboard'

const props = defineProps<{ kpi: KpiSpec; result: KpiResult | undefined }>()

/**
 * A headline number (§31): the dataset's true count under the current
 * filter (FR-AN4), and, where it helps, what it is out of.
 *
 * What the figure leaves out is said beside it: withheld rows, and any
 * filtered dimension it could not be narrowed by.
 */
const dashboard = useDashboardStore()
const measure = computed(() => dashboard.measure(props.kpi.measure))
const format = computed(() => measure.value?.format ?? 'integer')

const value = computed(() => formatValue(props.result?.value ?? null, format.value))
const total = computed(() => {
  const r = props.result
  if (!r || r.total === undefined || r.total === null || r.total === r.value) return null
  return formatValue(r.total, format.value)
})
const withheld = computed(() => {
  const n = props.result?.withheld
  if (!n) return null
  const plural = dashboard.descriptor?.entity.plural ?? 'rows'
  return `${n.toLocaleString('en-GB')} ${plural} withheld`
})
const ignored = computed(() =>
  (props.result?.ignored ?? []).map((id) => dashboard.dimension(id)?.label ?? id),
)
</script>

<template>
  <div class="tile" :data-emphasis="kpi.emphasis">
    <span class="label">{{ kpi.label }}</span>
    <span class="value mono">{{ value }}</span>
    <span v-if="total" class="context mono">of {{ total }}</span>
    <span v-if="kpi.note" class="note">{{ kpi.note }}</span>
    <span v-if="withheld" class="note">{{ withheld }}</span>
    <span v-if="ignored.length" class="note">Not narrowed by {{ ignored.join(', ') }}</span>
  </div>
</template>

<style scoped>
.tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: var(--space-4) var(--space-5);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.tile[data-emphasis='primary'] {
  border-top: 2px solid var(--chart-anomaly);
}

.label {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.mono {
  font-family: var(--font-mono);
}

.value {
  color: var(--text-primary);
  font-size: var(--text-xl);
  font-weight: 600;
  line-height: 1.2;
}

.context {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.note {
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
}
</style>
