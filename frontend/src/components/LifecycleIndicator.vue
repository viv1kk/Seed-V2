<script setup lang="ts">
import { computed } from 'vue'

import { PHASE_ORDER, type Phase } from '../stores/system'

const props = defineProps<{ phase: Phase }>()

const current = computed(() => PHASE_ORDER.indexOf(props.phase))

function stateOf(index: number): 'complete' | 'current' | 'future' {
  if (index < current.value) return 'complete'
  if (index === current.value) return 'current'
  return 'future'
}
</script>

<template>
  <ol class="track">
    <li
      v-for="(name, index) in PHASE_ORDER"
      :key="name"
      class="phase"
      :data-state="stateOf(index)"
    >
      <span class="marker" />
      <span class="label">{{ name }}</span>
    </li>
  </ol>
</template>

<style scoped>
/* Completed, current and future are all visible at once (FR-L6), and
   the difference between them is weight rather than movement (§14). */
.track {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.phase {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-right: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
}

.phase:not(:last-child)::after {
  content: '';
  width: var(--space-6);
  height: 1px;
  background: var(--border-default);
}

.marker {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  border: 1px solid var(--border-strong);
  transition: all var(--duration-base) var(--ease-out);
}

.label {
  color: var(--text-muted);
  transition: color var(--duration-base) var(--ease-out);
}

.phase[data-state='complete'] .marker {
  background: var(--border-strong);
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
</style>
