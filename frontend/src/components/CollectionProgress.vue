<script setup lang="ts">
import { computed } from 'vue'

import { useSystemStore } from '../stores/system'

const system = useSystemStore()

/**
 * Life's collection, as it goes (D-17, FR-LF4). Agent One VW collects the
 * final weeks of each dataset one simulated week at a time, recalibrating
 * every few, until it is caught up. This says where it is.
 */
const progress = computed(() => {
  const c = system.collection
  if (!c) return null
  return {
    share: c.steps ? c.step / c.steps : 1,
    caughtUp: c.caughtUp,
    text: c.caughtUp
      ? `Caught up · ${c.steps} weeks collected · recalibrated ${c.calibrations} times`
      : `Collecting · ${c.week} · ${c.step} of ${c.steps}` +
        (c.calibration ? ` · recalibration ${c.calibration} of ${c.calibrations}` : ''),
  }
})
</script>

<template>
  <div
    v-if="progress"
    class="progress"
    :data-caught-up="progress.caughtUp"
    role="status"
    aria-label="Collection"
  >
    <span class="text mono">{{ progress.text }}</span>
    <span class="track" aria-hidden="true">
      <span class="fill" :style="{ transform: `scaleX(${progress.share})` }" />
    </span>
    <span class="simulated">Simulated collection</span>
  </div>
</template>

<style scoped>
.progress {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.text {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.mono {
  font-family: var(--font-mono);
}

.track {
  position: relative;
  width: 7rem;
  height: 3px;
  overflow: hidden;
  background: var(--surface-sunken);
  border-radius: 2px;
}

.fill {
  position: absolute;
  inset: 0;
  background: var(--accent);
  transform-origin: left;
  transition: transform var(--duration-slow) var(--ease-out);
}

.progress[data-caught-up='true'] .fill {
  background: var(--status-positive);
}

.simulated {
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .fill {
    transition: none;
  }
}
</style>
