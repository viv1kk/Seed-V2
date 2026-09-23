<script setup lang="ts">
import { computed } from 'vue'

import BuildLanes from './BuildLanes.vue'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()

/**
 * The Implementation stage: the approved solutions being built (FR-I1).
 *
 * The workspace around it is the one discovery and assessment used; only
 * the stage has changed, from environment graph to build pipeline (§27).
 * Each approved solution is one lane, laid out in full before the first
 * component moves, so the viewer sees the whole of what will be built and
 * then watches it happen. Rejected solutions are named and not built.
 */

const rejected = computed(() => system.solutions.filter((s) => s.status === 'REJECTED'))

const done = computed(
  () => system.implementations.filter((i) => i.status === 'COMPLETE').length,
)
</script>

<template>
  <div class="implementation">
    <header class="head">
      <div class="title-row">
        <h2 class="title">Build</h2>
        <span v-if="system.implementations.length" class="tally mono">
          {{ done }} of {{ system.implementations.length }} ready
        </span>
      </div>
      <p class="note">
        Each approved solution is built as a pipeline over the data discovery connected, tested,
        and validated against the evidence it was approved on. Select a component to see its
        tests.
      </p>
    </header>

    <p v-if="system.implementations.length === 0" class="note">
      No solution was approved, so there is nothing to build.
    </p>
    <BuildLanes v-else :implementations="system.implementations" />

    <p v-if="rejected.length" class="rejected">
      Not built:
      {{ rejected.map((s) => s.name).join(', ') }}
      {{ rejected.length === 1 ? 'was' : 'were' }} rejected at approval.
    </p>
  </div>
</template>

<style scoped>
.implementation {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-4);
}

.title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.mono {
  font-family: var(--font-mono);
}

.tally {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.note,
.rejected {
  margin: 0;
  max-width: 70ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}
</style>
