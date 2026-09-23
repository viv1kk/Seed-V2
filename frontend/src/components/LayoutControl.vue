<script setup lang="ts">
import { useLayoutStore, type Layout } from '../stores/layout'

defineProps<{
  /** Before planting only Life has content, so the choice is withheld. */
  disabled?: boolean
}>()

const layout = useLayoutStore()

const OPTIONS: { value: Layout; label: string }[] = [
  { value: 'both', label: 'Both' },
  { value: 'seeding', label: 'Seeding' },
  { value: 'life', label: 'Life' },
]

/**
 * The layout control (FR-W2).
 *
 * Three settings, one of them current. Life only is unavailable while a
 * person is being asked something, because the question lives in the
 * Seeding pane (FR-W5).
 */
function unavailable(value: Layout): boolean {
  return value === 'life' && layout.forced
}
</script>

<template>
  <div class="control" role="radiogroup" aria-label="Layout">
    <button
      v-for="option in OPTIONS"
      :key="option.value"
      type="button"
      role="radio"
      class="option"
      :aria-checked="layout.layout === option.value"
      :data-active="layout.layout === option.value"
      :disabled="disabled || unavailable(option.value)"
      :title="unavailable(option.value) ? 'Input is required in the Seeding pane' : undefined"
      @click="layout.choose(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.control {
  display: inline-flex;
  padding: 2px;
  background: var(--surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.option {
  padding: var(--space-1) var(--space-3);
  color: var(--text-muted);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  transition:
    color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.option:hover:not(:disabled) {
  color: var(--text-secondary);
}

.option[data-active='true'] {
  color: var(--text-primary);
  background: var(--surface-raised);
}

.option:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
