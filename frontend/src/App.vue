<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

import HumanRequest from './components/HumanRequest.vue'
import LifecycleIndicator from './components/LifecycleIndicator.vue'
import OperatorPanel from './components/OperatorPanel.vue'
import { useEventStore } from './stores/events'
import { useSystemStore } from './stores/system'

const events = useEventStore()
const system = useSystemStore()

onMounted(() => events.connect())
onBeforeUnmount(() => events.disconnect())

function clockOf(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { hour12: false })
}
</script>

<template>
  <div class="shell">
    <!-- No transport bar. The chrome carries identity and the lifecycle
         and nothing an audience should not see (FR-O2). -->
    <header class="bar">
      <div class="identity">
        <span class="name">Systems</span>
        <span class="version">V1</span>
      </div>
      <LifecycleIndicator :phase="system.phase" />
      <span class="lifecycle mono">{{ system.lifecycle }}</span>
    </header>

    <main class="stage">
      <section class="panel">
        <HumanRequest v-if="system.blockedOn" :request="system.blockedOn" />

        <ol class="stream">
          <li v-for="event in events.events" :key="event.sequence" class="event">
            <span class="sequence">{{ String(event.sequence).padStart(4, '0') }}</span>
            <span class="clock">{{ clockOf(event.timestamp) }}</span>
            <span class="category" :data-category="event.category">{{ event.category }}</span>
            <span class="message" :data-severity="event.severity">{{ event.message }}</span>
          </li>
          <li v-if="events.events.length === 0" class="empty">
            No activity yet. Shift+O for the operator panel.
          </li>
        </ol>
      </section>
    </main>

    <OperatorPanel />
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-8);
  padding: var(--space-3) var(--space-6);
  background: var(--surface-raised);
  border-bottom: 1px solid var(--border-subtle);
}

.identity {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.name {
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.version,
.lifecycle {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.lifecycle {
  letter-spacing: 0.06em;
}

.mono {
  font-family: var(--font-mono);
}

.stage {
  flex: 1;
  padding: var(--space-8) var(--space-6);
  overflow-y: auto;
}

.panel {
  max-width: 68rem;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.stream {
  margin: 0;
  padding: 0;
  list-style: none;
}

.event {
  display: grid;
  grid-template-columns: 4rem 6rem 8rem 1fr;
  gap: var(--space-4);
  align-items: baseline;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-sm);
}

.sequence,
.clock,
.category {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.sequence,
.clock {
  color: var(--text-muted);
}

.category {
  color: var(--text-secondary);
  letter-spacing: 0.04em;
}

.category[data-category='SUCCESS'] {
  color: var(--status-positive);
}

.category[data-category='WARNING'] {
  color: var(--status-warning);
}

.category[data-category='HUMAN_INPUT'] {
  color: var(--accent);
}

.message {
  color: var(--text-secondary);
}

.message[data-severity='WARNING'] {
  color: var(--status-warning);
}

.message[data-severity='ERROR'] {
  color: var(--status-negative);
}

.empty {
  padding: var(--space-4) 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
