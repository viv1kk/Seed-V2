<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import LifecycleIndicator from './components/LifecycleIndicator.vue'
import { useEventStore } from './stores/events'
import { useSystemStore } from './stores/system'
import { useThemeStore } from './stores/theme'

const events = useEventStore()
const system = useSystemStore()
const theme = useThemeStore()

const busy = ref(false)

onMounted(() => events.connect())
onBeforeUnmount(() => events.disconnect())

async function post(path: string): Promise<void> {
  busy.value = true
  try {
    await fetch(path, { method: 'POST' })
  } finally {
    busy.value = false
  }
}

function clockOf(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], { hour12: false })
}
</script>

<template>
  <div class="shell">
    <header class="bar">
      <div class="identity">
        <span class="name">Systems</span>
        <span class="version">V1</span>
      </div>

      <LifecycleIndicator :phase="system.phase" />

      <div class="controls">
        <span class="connection" :data-state="events.connection">{{ events.connection }}</span>
        <button type="button" class="control" :disabled="busy" @click="post('/api/demo/start')">
          Start
        </button>
        <button type="button" class="control" :disabled="busy" @click="events.reset()">
          Reset
        </button>
        <button type="button" class="control" @click="theme.toggle()">
          {{ theme.theme === 'light' ? 'Dark' : 'Light' }}
        </button>
      </div>
    </header>

    <main class="stage">
      <section class="panel">
        <div class="status">
          <div class="field">
            <span class="key">Lifecycle</span>
            <span class="value mono">{{ system.lifecycle }}</span>
          </div>
          <div class="field">
            <span class="key">Events</span>
            <span class="value mono">{{ events.lastSequence }}</span>
          </div>
          <div class="field">
            <span class="key">Gaps</span>
            <span class="value mono">{{ events.gaps.length }}</span>
          </div>
          <div class="field">
            <span class="key">Resyncs</span>
            <span class="value mono">{{ events.resyncs }}</span>
          </div>
        </div>

        <!-- Appears only while input is required, and leaves once
             resolved (FR-H1). -->
        <div v-if="system.blockedOn" class="request" :data-kind="system.blockedOn.kind">
          <span class="kind">{{ system.blockedOn.kind }}</span>
          <p class="prompt">{{ system.blockedOn.prompt }}</p>
          <button type="button" class="control" :disabled="busy" @click="post('/api/demo/resume')">
            Provide and continue
          </button>
        </div>

        <ol class="stream">
          <li v-for="event in events.events" :key="event.sequence" class="event">
            <span class="sequence">{{ String(event.sequence).padStart(4, '0') }}</span>
            <span class="clock">{{ clockOf(event.timestamp) }}</span>
            <span class="category" :data-category="event.category">{{ event.category }}</span>
            <span class="message" :data-severity="event.severity">{{ event.message }}</span>
          </li>
          <li v-if="events.events.length === 0" class="empty">
            No activity yet. Start the run to drive the state machine.
          </li>
        </ol>
      </section>
    </main>
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

.version {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.controls {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.connection {
  margin-right: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.connection[data-state='open'] {
  color: var(--status-positive);
}

.connection[data-state='error'] {
  color: var(--status-negative);
}

.control {
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.control:hover:not(:disabled) {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.control:disabled {
  opacity: 0.5;
  cursor: default;
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

.status {
  display: flex;
  gap: var(--space-8);
  padding-bottom: var(--space-6);
  border-bottom: 1px solid var(--border-subtle);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.key {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.value {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.mono {
  font-family: var(--font-mono);
}

.request {
  margin: var(--space-6) 0;
  padding: var(--space-4) var(--space-6);
  background: var(--accent-subtle);
  border: 1px solid var(--accent);
  border-radius: var(--radius-md);
}

.kind {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.prompt {
  margin: var(--space-2) 0 var(--space-4);
  max-width: 48rem;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.stream {
  margin: var(--space-6) 0 0;
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
