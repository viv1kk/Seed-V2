<script setup lang="ts">
import { computed } from 'vue'

import { PHASE_ORDER, type Phase } from '../stores/system'

const props = defineProps<{
  phase: Phase
  /** True while the system waits on a person, which is not progress. */
  blocked?: boolean
}>()

const LABELS: Record<Phase, string> = {
  INIT: 'Init',
  DISCOVERY: 'Discovery',
  ASSESSMENT: 'Assessment',
  IMPLEMENTATION: 'Implementation',
  RUNTIME: 'Runtime',
}

const current = computed(() => PHASE_ORDER.indexOf(props.phase))

function stateOf(index: number): 'complete' | 'current' | 'future' {
  if (index < current.value) return 'complete'
  if (index === current.value) return 'current'
  return 'future'
}
</script>

<template>
  <!-- Persistent, and showing all three states at once (FR-L6, §14).
       The difference between complete, current and future is weight, not
       movement: this should read like an operating system rather than a
       marketing animation (NFR-V5, NFR-V6). -->
  <ol class="track" aria-label="Lifecycle">
    <li
      v-for="(name, index) in PHASE_ORDER"
      :key="name"
      class="phase"
      :data-state="stateOf(index)"
      :data-blocked="stateOf(index) === 'current' && blocked"
      :aria-current="stateOf(index) === 'current' ? 'step' : undefined"
    >
      <span class="marker" aria-hidden="true" />
      <span class="label">{{ LABELS[name] }}</span>
      <span v-if="index < PHASE_ORDER.length - 1" class="rule" aria-hidden="true" />
    </li>
  </ol>
</template>

<style scoped>
.track {
  display: flex;
  align-items: center;
  margin: 0;
  padding: 0;
  list-style: none;
}

.phase {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
}

.rule {
  width: clamp(var(--space-4), 4vw, var(--space-10));
  height: 1px;
  margin: 0 var(--space-3);
  background: var(--border-subtle);
}

.phase[data-state='complete'] .rule {
  background: var(--border-strong);
}

.marker {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  border: 1px solid var(--border-default);
  transition:
    background var(--duration-base) var(--ease-out),
    border-color var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out);
}

.label {
  color: var(--text-muted);
  transition: color var(--duration-base) var(--ease-out);
}

.phase[data-state='complete'] .marker {
  background: var(--border-strong);
  border-color: var(--border-strong);
}

.phase[data-state='complete'] .label {
  color: var(--text-secondary);
}

.phase[data-state='current'] .marker {
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-subtle);
}

.phase[data-state='current'] .label {
  color: var(--text-primary);
  font-weight: 600;
}

/* Waiting on a person is not progress, and it is not a fault either
   (FR-H4). The current phase holds its place and changes hue. */
.phase[data-blocked='true'] .marker {
  background: var(--status-warning);
  border-color: var(--status-warning);
  box-shadow: none;
}

@media (max-width: 68rem) {
  .phase .label {
    display: none;
  }

  .phase[data-state='current'] .label {
    display: inline;
  }
}
</style>
