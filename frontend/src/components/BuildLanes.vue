<script setup lang="ts">
import { reactive } from 'vue'

import BuildLane from './BuildLane.vue'
import type { Implementation } from '../stores/system'

defineProps<{ implementations: Implementation[] }>()

/**
 * Every build, one lane each, in the order they are built.
 *
 * Which lanes are expanded, and which component is singled out, are view
 * state rather than system state: they say what the viewer is looking
 * at, not what the system did, so they live here and nowhere else.
 */
const expanded = reactive(new Set<string>())
const focus = reactive(new Map<string, string | null>())

function toggle(id: string): void {
  if (expanded.has(id)) {
    expanded.delete(id)
  } else {
    expanded.add(id)
  }
}

function select(id: string, component: string | null): void {
  focus.set(id, component)
  // Singling out a component is a request to see its tests.
  if (component !== null) {
    expanded.add(id)
  }
}
</script>

<template>
  <div class="lanes">
    <BuildLane
      v-for="implementation in implementations"
      :key="implementation.id"
      :implementation="implementation"
      :expanded="expanded.has(implementation.id)"
      :focus="focus.get(implementation.id) ?? null"
      @toggle="toggle(implementation.id)"
      @focus="(component) => select(implementation.id, component)"
    />
  </div>
</template>

<style scoped>
.lanes {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
</style>
