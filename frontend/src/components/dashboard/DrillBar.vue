<script setup lang="ts">
import { computed } from 'vue'

import { formatValue } from '../../design/format'
import { useDashboardStore } from '../../stores/dashboard'

const emit = defineEmits<{ evidence: [] }>()

/**
 * The drill path, as a breadcrumb (FR-EV5, §55).
 *
 * Each crumb is one click, in the order it was made. Choosing a crumb
 * returns there; Back undoes one click, and so does the browser's own Back
 * (D-3). Beside it: what the next level down is, so the viewer knows where
 * a click leads, and the evidence for the current selection.
 */
const dashboard = useDashboardStore()

const next = computed(() => {
  const drill = dashboard.drill
  if (!drill?.next) return null
  return drill.levels.find((l) => l.id === drill.next)?.label ?? null
})

/**
 * Where the view stands against collection (D-17, FR-LF8): following it,
 * or pinned to the step it was at when the viewer drilled in, with how
 * many collections have landed since.
 */
const collection = computed(() => {
  const step = dashboard.viewStep
  if (step === null || dashboard.live === null) return null
  const week = dashboard.weeks[step]?.week ?? `step ${step}`
  if (dashboard.pinned === null) {
    return { pinned: false, text: `Following collection · ${week}` }
  }
  const newer = dashboard.newer
  return {
    pinned: true,
    text: `Pinned to ${week}${newer ? ` · ${newer} newer ${newer === 1 ? 'collection' : 'collections'}` : ''}`,
    newer,
  }
})

const why = computed(() => {
  const e = dashboard.evidence
  if (!e) return 'Evidence'
  if (e.status === 'finding' && e.finding) {
    const lift =
      e.deviation !== null && e.deviation !== undefined ? formatValue(e.deviation, 'lift') : ''
    return `Why? ${e.finding.title} ${lift}`.trim()
  }
  if (e.status === 'insufficient' && e.finding) return `Why? ${e.finding.title}`
  if (e.status === 'choose') return `Evidence · ${e.findings?.length ?? 0} findings`
  return 'Evidence'
})
</script>

<template>
  <nav class="bar" aria-label="Drill path">
    <button
      type="button"
      class="back"
      :disabled="!dashboard.steps.length"
      @click="dashboard.back()"
    >
      ← Back
    </button>
    <ol class="crumbs">
      <li>
        <button
          type="button"
          class="crumb"
          :data-current="!dashboard.steps.length"
          @click="dashboard.jump(0)"
        >
          {{ dashboard.drill?.root ?? 'All' }}
        </button>
      </li>
      <li v-for="(step, index) in dashboard.steps" :key="index">
        <span class="sep" aria-hidden="true">/</span>
        <button
          type="button"
          class="crumb"
          :data-current="index === dashboard.steps.length - 1"
          @click="dashboard.jump(index + 1)"
        >
          {{ step.label }}
        </button>
      </li>
    </ol>
    <span v-if="next" class="next">Click a figure to drill into {{ next.toLowerCase() }}</span>
    <span v-if="collection" class="collection" :data-pinned="collection.pinned">
      {{ collection.text }}
      <button
        v-if="collection.pinned && collection.newer"
        type="button"
        class="catch-up"
        @click="dashboard.catchUp()"
      >
        Catch up
      </button>
    </span>
    <span v-if="dashboard.loading" class="loading" aria-hidden="true" />
    <button type="button" class="why" @click="emit('evidence')">{{ why }}</button>
  </nav>
</template>

<style scoped>
.bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.back,
.why {
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  white-space: nowrap;
}

.back:disabled {
  opacity: 0.4;
  cursor: default;
}

.collection {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.collection[data-pinned='true'] {
  color: var(--status-warning);
}

.catch-up {
  padding: 2px var(--space-2);
  color: var(--text-primary);
  background: none;
  border: 1px solid var(--status-warning);
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
}

.collection + .loading + .why,
.collection + .why {
  margin-left: 0;
}

.why {
  margin-left: auto;
  color: var(--text-primary);
  border-color: var(--accent);
}

.crumbs {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.crumbs li {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.sep {
  color: var(--border-strong);
}

.crumb {
  padding: 2px var(--space-2);
  color: var(--text-secondary);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.crumb:hover {
  color: var(--text-primary);
  background: var(--surface-sunken);
}

.crumb[data-current='true'] {
  color: var(--text-primary);
  font-weight: 600;
}

.next {
  color: var(--text-muted);
  font-size: var(--text-xs);
  white-space: nowrap;
}

.loading {
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 30%;
  height: 2px;
  background: var(--accent);
  animation: travel 0.9s linear infinite;
}

@keyframes travel {
  from {
    left: -30%;
  }
  to {
    left: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading {
    animation: none;
    width: 100%;
    opacity: 0.4;
  }
}
</style>
