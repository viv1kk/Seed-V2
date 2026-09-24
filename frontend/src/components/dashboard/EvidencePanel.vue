<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'

import { formatValue } from '../../design/format'
import { useDashboardStore, type Step } from '../../stores/dashboard'

const emit = defineEmits<{ close: []; apply: [step: Step]; records: [] }>()

/**
 * "Why was this flagged?" (§35, §57, FR-EV7).
 *
 * The finding the current selection narrows to, with the figures that
 * make it one: observed against baseline, the deviation, the population
 * it was compared with, the records that contribute, the methodology that
 * found it and how it was validated. Every figure came from the backend,
 * computed from rows (FR-EV8). A selection that spans several findings is
 * asked to choose; one that cannot be measured says why.
 */
const dashboard = useDashboardStore()
const e = computed(() => dashboard.evidence)

const unit = computed(() => e.value?.metric?.unit ?? 'decimal')

const comparable = computed(() => {
  const c = e.value?.comparable
  if (!c) return null
  const plural = dashboard.descriptor?.entity.plural ?? 'rows'
  const parts = [...c.where]
  if (c.by.length) parts.push(`same ${c.by.join(' and ').toLowerCase()}`)
  return { size: `${c.size.toLocaleString('en-GB')} ${plural}`, basis: parts.join('; ') }
})

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <aside class="panel" aria-label="Evidence">
    <header class="head">
      <span class="kicker">Why was this flagged?</span>
      <button type="button" class="close" aria-label="Close" @click="emit('close')">×</button>
    </header>

    <div v-if="!e" class="body"><p class="message">Loading evidence.</p></div>

    <div v-else-if="e.status === 'empty' || e.status === 'none'" class="body">
      <p class="message">{{ e.message }}</p>
    </div>

    <div v-else-if="e.status === 'choose'" class="body">
      <p class="message">{{ e.message }}</p>
      <ul class="choices">
        <li v-for="f in e.findings" :key="f.value">
          <button
            type="button"
            class="choice"
            @click="emit('apply', { label: f.value, dimensions: f.filter })"
          >
            <span class="swatch" :style="{ background: `var(--chart-${f.role ?? 'muted'})` }" />
            <span class="choice-title">{{ f.title }}</span>
            <span class="mono count">{{ f.count.toLocaleString('en-GB') }}</span>
          </button>
        </li>
      </ul>
    </div>

    <div v-else class="body">
      <section class="finding">
        <h2 class="title">
          <span
            class="swatch"
            :style="{ background: `var(--chart-${e.finding?.role ?? 'muted'})` }"
          />
          {{ e.finding?.title }}
        </h2>
        <p class="description">{{ e.finding?.description }}</p>
        <p v-if="e.entity" class="entity mono">{{ e.entity }}</p>
      </section>

      <p v-if="e.status === 'insufficient'" class="insufficient">{{ e.message }}</p>

      <dl v-else class="figures">
        <div>
          <dt>Observed</dt>
          <dd class="mono">{{ formatValue(e.observed, unit) }}</dd>
        </div>
        <div>
          <dt>Baseline</dt>
          <dd class="mono">{{ formatValue(e.baseline, unit) }}</dd>
        </div>
        <div>
          <dt>Deviation</dt>
          <dd class="mono deviation">{{ formatValue(e.deviation, 'lift') }}</dd>
        </div>
      </dl>
      <p v-if="e.metric?.label && e.status === 'finding'" class="metric">
        {{ e.metric.label }}, mean over the contributing records.
      </p>

      <!-- The calibration the finding is scored under, so a finding that
           differs between steps reads as maintenance (FR-LF9). -->
      <section v-if="e.calibration" class="section">
        <h3 class="section-title">Calibration</h3>
        <p class="line">{{ e.calibration.label }}.</p>
        <p v-if="e.confirmation" class="line">
          {{ e.confirmation.value }}
          <span class="confirmation" :data-status="e.confirmation.status">
            {{ e.confirmation.status === 'confirmed' ? 'confirmed' : 'provisional' }}
          </span>
          <template v-if="e.confirmation.status === 'provisional'">
            , scored on partial evidence until more of it is collected
          </template>
        </p>
      </section>

      <section v-if="comparable" class="section">
        <h3 class="section-title">Comparable population</h3>
        <p class="line">
          <span class="mono">{{ comparable.size }}</span> · {{ comparable.basis }}
        </p>
      </section>

      <section v-if="e.records" class="section">
        <h3 class="section-title">Contributing records</h3>
        <p class="line">
          <span class="mono">{{ e.records.count.toLocaleString('en-GB') }}</span>
          <template v-if="e.score !== null && e.score !== undefined">
            · mean score <span class="mono">{{ formatValue(e.score, 'score') }}</span>
          </template>
        </p>
        <ul class="sample">
          <li v-for="id in e.records.sample" :key="id">
            <button
              type="button"
              class="record mono"
              :data-current="id === e.entity"
              @click="emit('apply', { label: id, entityId: id })"
            >
              {{ id }}
            </button>
          </li>
        </ul>
        <button type="button" class="link" @click="emit('records')">View underlying records</button>
      </section>

      <section v-if="e.methodology" class="section">
        <h3 class="section-title">Methodology · {{ e.methodology.name }}</h3>
        <ol class="steps">
          <li v-for="step in e.methodology.process" :key="step">{{ step }}</li>
        </ol>
      </section>

      <section v-if="e.validation?.length" class="section">
        <h3 class="section-title">Validation</h3>
        <ul class="notes">
          <li v-for="line in e.validation" :key="line">{{ line }}</li>
        </ul>
      </section>

      <p class="simulated">Figures are computed from the simulated demo dataset's records.</p>
    </div>
  </aside>
</template>

<style scoped>
.panel {
  position: absolute;
  inset: 0 0 0 auto;
  z-index: 3;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  width: min(26rem, 100%);
  background: var(--surface-overlay);
  border-left: 1px solid var(--border-default);
  box-shadow: var(--shadow-md);
  animation: slide var(--duration-base) var(--ease-out) both;
}

@keyframes slide {
  from {
    opacity: 0;
    transform: translateX(1.5rem);
  }
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}

.kicker,
.section-title {
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.section-title {
  margin: 0 0 var(--space-2);
}

.close {
  color: var(--text-muted);
  background: none;
  border: none;
  font-size: var(--text-lg);
  line-height: 1;
}

.body {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
  overflow-y: auto;
}

.mono {
  font-family: var(--font-mono);
}

.message,
.description,
.metric,
.line {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.title {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin: 0 0 var(--space-2);
  font-size: var(--text-md);
  font-weight: 600;
}

.swatch {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.entity {
  margin: var(--space-2) 0 0;
  color: var(--text-primary);
  font-size: var(--text-xs);
}

.insufficient {
  margin: 0;
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
  font-size: var(--text-xs);
  line-height: 1.6;
  background: var(--surface-sunken);
  border-left: 2px solid var(--status-warning);
}

.figures {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin: 0;
}

.figures dt {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.figures dd {
  margin: var(--space-1) 0 0;
  color: var(--text-primary);
  font-size: var(--text-lg);
  font-weight: 600;
}

.deviation {
  color: var(--chart-anomaly);
}

.choices,
.sample,
.notes,
.steps {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-xs);
}

.choices {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.choice {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  color: var(--text-primary);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  text-align: left;
}

.choice:hover {
  border-color: var(--border-strong);
}

.choice-title {
  flex: 1;
}

.count {
  color: var(--text-muted);
}

.sample {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-2);
}

.record {
  padding: 2px var(--space-2);
  color: var(--text-secondary);
  background: var(--surface-sunken);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.record:hover,
.record[data-current='true'] {
  color: var(--text-primary);
  border-color: var(--accent);
}

.link {
  margin-top: var(--space-3);
  padding: 0;
  color: var(--accent);
  background: none;
  border: none;
  font-size: var(--text-xs);
}

.steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-left: var(--space-5);
  list-style: decimal;
  color: var(--text-secondary);
}

.notes {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  color: var(--text-secondary);
  line-height: 1.5;
}

.notes li {
  padding-left: var(--space-3);
  border-left: 2px solid var(--border-default);
}

.simulated {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
}

@media (prefers-reduced-motion: reduce) {
  .panel {
    animation: none;
  }
}

.confirmation {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--status-positive);
}

.confirmation[data-status='provisional'] {
  color: var(--status-warning);
}
</style>
