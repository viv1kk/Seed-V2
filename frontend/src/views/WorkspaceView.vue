<script setup lang="ts">
import { computed, ref } from 'vue'

import ActivityStream from '../components/ActivityStream.vue'
import HumanRequest from '../components/HumanRequest.vue'
import LifecycleStrip from '../components/LifecycleStrip.vue'
import ProtectionPanel from '../components/ProtectionPanel.vue'
import StagePane from '../components/StagePane.vue'
import { labelOf } from '../design/presentation'
import { useEventStore } from '../stores/events'
import { useLayoutStore } from '../stores/layout'
import { useProtectionStore } from '../stores/protection'
import { useSystemStore } from '../stores/system'

const events = useEventStore()
const layout = useLayoutStore()
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

/**
 * Where the rail sits.
 *
 * Beside the stage when the Seeding pane has the width to itself. With
 * both panes showing, a side rail of at least 22rem left the stage a
 * sliver, so the rail docks along the bottom of the pane instead, as a
 * drawer the stage keeps the full width above.
 */
const docked = computed(() => layout.layout === 'both')

/** Whether the docked drawer is open. It keeps its state for the run. */
const open = ref(true)

/** The newest entry, shown in the drawer's bar while it is closed. */
const latest = computed(() => events.events[events.events.length - 1] ?? null)
</script>

<template>
  <!-- The Seeding pane (D-14, FR-W1). Mounted once, when the seed is
       planted, and never unmounted across a phase change or a layout
       change (NFR-A3, NFR-A7, §13). The lifecycle changes, the stage
       changes, the activity accrues and human input appears when needed.
       A single system operating continuously underneath. -->
  <div class="workspace" :data-rail="docked ? 'bottom' : 'side'" :data-open="open">
    <header class="bar">
      <LifecycleStrip :phase="system.phase" :blocked="blocked" />
    </header>

    <div class="body">
      <!-- The stage, with the human-input surface beneath it. The surface
           appears only while input is required and takes no reserved slot
           when it is not (FR-H1). It spans the stage's column only, so it
           never covers the Activity rail. -->
      <div class="main">
        <StagePane class="stage" />
        <HumanRequest v-if="system.blockedOn" :request="system.blockedOn" />
      </div>

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

          <!-- Docked, the bar opens and closes the drawer. Closed, it still
               shows the newest entry, so the build stays in view. -->
          <template v-if="docked">
            <p v-if="!open && latest" class="latest">
              <span class="latest-kind mono">{{ labelOf(latest.category) }}</span>
              <span class="latest-message">{{ latest.message }}</span>
            </p>
            <button
              type="button"
              class="toggle"
              :aria-expanded="open"
              :aria-label="open ? 'Close the record' : 'Open the record'"
              @click="open = !open"
            >
              <span class="chevron" aria-hidden="true">{{ open ? '▾' : '▴' }}</span>
            </button>
          </template>
        </nav>

        <div v-show="!docked || open" class="pane">
          <ActivityStream v-show="rail === 'activity'" />
          <ProtectionPanel v-show="rail === 'protection'" />
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.workspace {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
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

.main {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-height: 0;
  border-right: 1px solid var(--border-subtle);
}

.stage {
  min-height: 0;
}

/* A long request scrolls within itself rather than crushing the stage. */
.main > .request {
  max-height: 45vh;
  overflow-y: auto;
}

/* Docked: the stage keeps the full width, and the rail is a drawer along
   the bottom of the pane. */
.workspace[data-rail='bottom'] .body {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
}

.workspace[data-rail='bottom'][data-open='true'] .body {
  grid-template-rows: minmax(0, 1fr) clamp(9rem, 26vh, 15rem);
}

.workspace[data-rail='bottom'] .main {
  border-right: none;
}

.workspace[data-rail='bottom'] .rail {
  border-top: 1px solid var(--border-default);
}

.workspace[data-rail='bottom'][data-open='false'] .rail {
  grid-template-rows: auto;
}

.latest {
  display: flex;
  flex: 1;
  align-items: baseline;
  gap: var(--space-3);
  min-width: 0;
  margin: 0;
  padding: 0 var(--space-4);
  align-self: center;
  font-size: var(--text-xs);
}

.latest-kind {
  flex: none;
  color: var(--text-muted);
  letter-spacing: 0.06em;
}

.latest-message {
  overflow: hidden;
  color: var(--text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toggle {
  margin-left: auto;
  padding: 0 var(--space-5);
  color: var(--text-muted);
  background: none;
  border: none;
  font-size: var(--text-sm);
  transition: color var(--duration-fast) var(--ease-out);
}

.toggle:hover {
  color: var(--text-primary);
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

  .main {
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
  }
}
</style>
