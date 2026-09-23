<script setup lang="ts">
import { computed, ref } from 'vue'

import ActivityStream from '../components/ActivityStream.vue'
import HumanRequest from '../components/HumanRequest.vue'
import LifecycleStrip from '../components/LifecycleStrip.vue'
import ProtectionPanel from '../components/ProtectionPanel.vue'
import StagePane from '../components/StagePane.vue'
import { useEventStore } from '../stores/events'
import { useProtectionStore } from '../stores/protection'
import { useSystemStore } from '../stores/system'

const events = useEventStore()
const protection = useProtectionStore()
const system = useSystemStore()

type Rail = 'activity' | 'protection'

/**
 * Which rail pane is showing.
 *
 * Both stay mounted, so switching back does not lose the stream's scroll
 * position. The workspace changes its panes; it does not rebuild itself
 * (NFR-A3).
 */
const rail = ref<Rail>('activity')

const blocked = computed(() => system.blockedOn !== null)
</script>

<template>
  <!-- The Seeding pane (D-14, FR-W1). Mounted once, when the seed is
       planted, and never unmounted across a phase change or a layout
       change (NFR-A3, NFR-A7, §13). The lifecycle changes, the stage
       changes, the activity accrues and human input appears when needed.
       A single system operating continuously underneath. -->
  <div class="workspace">
    <header class="bar">
      <LifecycleStrip :phase="system.phase" :blocked="blocked" />
    </header>

    <div class="body">
      <StagePane class="stage" />

      <aside class="rail" aria-label="Record">
        <nav class="tabs">
          <button
            type="button"
            class="tab"
            :data-active="rail === 'activity'"
            @click="rail = 'activity'"
          >
            Activity
            <span class="tally mono">{{ events.lastSequence }}</span>
          </button>
          <button
            type="button"
            class="tab"
            :data-active="rail === 'protection'"
            @click="rail = 'protection'"
          >
            Protection
            <span class="tally mono">{{ protection.total }}</span>
          </button>
        </nav>

        <div class="pane">
          <ActivityStream v-show="rail === 'activity'" />
          <ProtectionPanel v-show="rail === 'protection'" />
        </div>
      </aside>
    </div>

    <!-- Appears only while input is required, and takes no reserved slot
         when it is not (FR-H1). -->
    <HumanRequest v-if="system.blockedOn" :request="system.blockedOn" />
  </div>
</template>

<style scoped>
.workspace {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  height: 100%;
  background: var(--surface-base);
}

.bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-3) var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
}

.body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(22rem, 30rem);
  min-height: 0;
}

.stage {
  border-right: 1px solid var(--border-subtle);
}

.rail {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  background: var(--surface-raised);
}

.tabs {
  display: flex;
  border-bottom: 1px solid var(--border-subtle);
}

.tab {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 1px solid transparent;
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  transition:
    color var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.tab:hover {
  color: var(--text-secondary);
}

.tab[data-active='true'] {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}

.tally {
  color: var(--border-strong);
  font-size: var(--text-xs);
}

.tab[data-active='true'] .tally {
  color: var(--text-muted);
}

.pane {
  min-height: 0;
}

/* Both panes stay mounted, so each keeps its scroll position; only one
   occupies the pane at a time. */
.pane > * {
  height: 100%;
}

@media (max-width: 64rem) {
  .body {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(12rem, 1fr) minmax(0, 1.2fr);
  }

  .stage {
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
  }
}
</style>
