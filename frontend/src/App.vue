<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

import { useEventStore } from './stores/events'
import { useThemeStore } from './stores/theme'

const events = useEventStore()
const theme = useThemeStore()

onMounted(() => events.connect())
onBeforeUnmount(() => events.disconnect())

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

      <div class="controls">
        <span class="connection" :data-state="events.connection">
          {{ events.connection }}
        </span>
        <button type="button" class="toggle" @click="theme.toggle()">
          {{ theme.theme === 'light' ? 'Dark' : 'Light' }}
        </button>
      </div>
    </header>

    <main class="stage">
      <section class="panel">
        <h1 class="heading">Walking skeleton</h1>
        <p class="note">
          Backend, event stream and frontend are connected. Milestone M1
          replaces this stream with the real event backbone.
        </p>

        <ol class="stream">
          <li v-for="event in events.events" :key="event.sequence" class="event">
            <span class="sequence">{{ String(event.sequence).padStart(4, '0') }}</span>
            <span class="clock">{{ clockOf(event.timestamp) }}</span>
            <span class="type">{{ event.type }}</span>
            <span class="message">{{ event.payload.message }}</span>
          </li>
          <li v-if="events.events.length === 0" class="empty">Waiting for the first event.</li>
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
  gap: var(--space-4);
}

.connection {
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

.toggle {
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: var(--surface-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.toggle:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.stage {
  flex: 1;
  padding: var(--space-12) var(--space-6);
  overflow-y: auto;
}

.panel {
  max-width: 62rem;
  margin: 0 auto;
  padding: var(--space-8);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.heading {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.note {
  margin: var(--space-2) 0 var(--space-8);
  max-width: 44rem;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.stream {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--border-subtle);
}

.event {
  display: grid;
  grid-template-columns: 4rem 6rem 12rem 1fr;
  gap: var(--space-4);
  align-items: baseline;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-sm);
}

.sequence,
.clock,
.type {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.sequence {
  color: var(--text-muted);
}

.clock {
  color: var(--text-muted);
}

.type {
  color: var(--accent);
}

.message {
  color: var(--text-secondary);
}

.empty {
  padding: var(--space-4) 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
