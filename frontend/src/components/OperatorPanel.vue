<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { rehearse } from '../stores/dashboard'
import { useEventStore } from '../stores/events'
import { useOperatorStore, type Speed } from '../stores/operator'
import { useSeedStore } from '../stores/seed'
import { useSystemStore } from '../stores/system'
import { useThemeStore } from '../stores/theme'

const operator = useOperatorStore()
const events = useEventStore()
const seed = useSeedStore()
const system = useSystemStore()
const theme = useThemeStore()

/**
 * One key advances the demo.
 *
 * Before the seed is planted there is no run to start, so the same key
 * plants it. This is the only shortcut that does two things, and it does
 * them because at any moment only one of them is available.
 */
function advance(): void | Promise<void> {
  return system.lifecycle === 'UNINITIALIZED' ? seed.initialize() : operator.start()
}

/**
 * The shortcuts, all on Shift, so nothing fires while an operator is
 * typing into the credential form. The panel is a reminder of these
 * rather than the way they are normally reached (FR-O2).
 */
const SHORTCUTS: Record<string, () => void | Promise<void>> = {
  O: () => operator.togglePanel(),
  Enter: () => advance(),
  P: () => seed.loadBundled(), // the sample seed, without a file picker (FR-S7)
  S: () => operator.skipPhase(),
  R: () => events.reset(),
  '!': () => operator.setSpeed('1x'), // Shift+1
  '@': () => operator.setSpeed('2x'), // Shift+2
  ')': () => operator.setSpeed('instant'), // Shift+0
  D: () => theme.toggle(),
}

/**
 * Evidence revision, for rehearsal: M7's proof that feasibility is
 * computed. Pick a profiled field, set its completeness, and every
 * assessment resting on it is regraded by the backend.
 */
const profiledFields = computed(() =>
  (system.environment?.dataSources ?? []).flatMap((source) =>
    source.fields.map((field) => ({
      key: `${source.id}|${field.name}`,
      dataset: source.id,
      field: field.name,
      label: `${source.label}.${field.name}`,
      completeness: field.completeness,
    })),
  ),
)
const revising = ref('')
const revisedPercent = ref(90)

function reviseEvidence(): void {
  const target = profiledFields.value.find((field) => field.key === revising.value)
  if (target) {
    void operator.reviseEvidence(target.dataset, target.field, revisedPercent.value / 100)
  }
}

/**
 * Dashboards, opened straight from here for rehearsal (D-3): the analytics
 * section can be rehearsed without replaying the narrative to reach it.
 */
const dashboards = ref<{ solutionId: string; title: string }[]>([])

onMounted(async () => {
  try {
    const response = await fetch('/api/analytics')
    if (response.ok) dashboards.value = await response.json()
  } catch {
    dashboards.value = []
  }
})

const SPEEDS: { value: Speed; label: string; hint: string }[] = [
  { value: '1x', label: '1x', hint: 'Shift+1' },
  { value: '2x', label: '2x', hint: 'Shift+2' },
  { value: 'instant', label: 'Instant', hint: 'Shift+0' },
]

function onKeydown(pressed: KeyboardEvent): void {
  if (!pressed.shiftKey || pressed.metaKey || pressed.ctrlKey || pressed.altKey) {
    return
  }
  const action = SHORTCUTS[pressed.key]
  if (action) {
    pressed.preventDefault()
    void action()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void operator.fetchRunState()
})

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <aside v-if="operator.panelVisible" class="panel" aria-label="Operator controls">
    <header class="head">
      <span class="title">Operator</span>
      <span class="hint">Shift+O to hide</span>
    </header>

    <dl class="readout">
      <dt>Lifecycle</dt>
      <dd class="mono">{{ system.lifecycle }}</dd>
      <dt>Run</dt>
      <dd class="mono">{{ operator.status }}</dd>
      <dt>Stream</dt>
      <dd class="mono">{{ events.connection }}</dd>
      <dt>Events</dt>
      <dd class="mono">{{ events.lastSequence }}</dd>
      <dt>Gaps</dt>
      <dd class="mono">{{ events.gaps.length }} / {{ events.resyncs }} resync</dd>
    </dl>

    <div class="group">
      <span class="label">Speed</span>
      <div class="row">
        <button
          v-for="option in SPEEDS"
          :key="option.value"
          type="button"
          class="action"
          :data-active="operator.speed === option.value"
          :title="option.hint"
          @click="operator.setSpeed(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <div class="group">
      <span class="label">Seed</span>
      <div class="row">
        <button type="button" class="action" title="Shift+P" @click="seed.loadBundled()">
          Load sample seed
        </button>
      </div>
    </div>

    <div class="group">
      <span class="label">Run</span>
      <div class="row">
        <button type="button" class="action" title="Shift+Enter" @click="advance()">
          {{ system.lifecycle === 'UNINITIALIZED' ? 'Initialize' : 'Start' }}
        </button>
        <button type="button" class="action" title="Shift+S" @click="operator.skipPhase()">
          Skip phase
        </button>
        <button type="button" class="action" title="Shift+R" @click="events.reset()">
          Reset
        </button>
      </div>
    </div>

    <div v-if="profiledFields.length" class="group">
      <span class="label">Evidence</span>
      <div class="row">
        <select v-model="revising" class="input" aria-label="Profiled field">
          <option value="" disabled>Profiled field</option>
          <option v-for="field in profiledFields" :key="field.key" :value="field.key">
            {{ field.label }} · {{ Math.round(field.completeness * 1000) / 10 }}%
          </option>
        </select>
      </div>
      <div class="row">
        <input
          v-model.number="revisedPercent"
          class="input narrow"
          type="number"
          min="0"
          max="100"
          step="1"
          aria-label="Completeness percent"
        />
        <button type="button" class="action" :disabled="!revising" @click="reviseEvidence()">
          Revise completeness
        </button>
      </div>
    </div>

    <div v-if="dashboards.length" class="group">
      <span class="label">Rehearse a dashboard</span>
      <div class="row wrap">
        <button
          v-for="d in dashboards"
          :key="d.solutionId"
          type="button"
          class="action"
          @click="rehearse(d.solutionId)"
        >
          {{ d.title }}
        </button>
      </div>
    </div>

    <div class="group">
      <span class="label">Display</span>
      <div class="row">
        <button type="button" class="action" title="Shift+D" @click="theme.toggle()">
          {{ theme.theme === 'light' ? 'Dark' : 'Light' }} theme
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.panel {
  position: fixed;
  right: var(--space-4);
  bottom: var(--space-4);
  z-index: 100;
  width: 17rem;
  padding: var(--space-4);
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}

.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.title {
  font-size: var(--text-sm);
  font-weight: 600;
}

.hint,
.label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.readout {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-4);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
}

.readout dt {
  color: var(--text-muted);
}

.readout dd {
  margin: 0;
  color: var(--text-secondary);
  text-align: right;
}

.mono {
  font-family: var(--font-mono);
}

.group + .group {
  margin-top: var(--space-3);
}

.row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-1);
}

.action {
  padding: var(--space-1) var(--space-2);
  color: var(--text-secondary);
  background: var(--surface-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  transition: all var(--duration-fast) var(--ease-out);
}

.action:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.action:disabled {
  opacity: 0.5;
}

.input {
  flex: 1;
  min-width: 0;
  padding: var(--space-1) var(--space-2);
  color: var(--text-primary);
  background: var(--surface-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.input.narrow {
  flex: 0 0 4.5rem;
}

.action[data-active='true'] {
  color: var(--accent);
  background: var(--accent-subtle);
  border-color: var(--accent);
}
</style>
