<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

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

.action[data-active='true'] {
  color: var(--accent);
  background: var(--accent-subtle);
  border-color: var(--accent);
}
</style>
