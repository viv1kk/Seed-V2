<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import { clockOf, labelOf, presentationOf, startsPhase } from '../design/presentation'
import { useEventStore } from '../stores/events'

const events = useEventStore()

const scroller = ref<HTMLElement | null>(null)

/**
 * Whether the stream follows the newest entry.
 *
 * It does until the reader scrolls back, and resumes when they return to
 * the end. An audit log that yanks itself away while it is being read is
 * not auditable (FR-E8).
 */
const following = ref(true)

function onScroll(): void {
  const element = scroller.value
  if (!element) {
    return
  }
  const distance = element.scrollHeight - element.scrollTop - element.clientHeight
  following.value = distance < 24
}

watch(
  () => events.lastSequence,
  async () => {
    if (!following.value) {
      return
    }
    await nextTick()
    const element = scroller.value
    if (element) {
      element.scrollTop = element.scrollHeight
    }
  },
)
</script>

<template>
  <!-- An auditable activity stream, not a developer terminal (FR-E8).
       Two lines per entry as in §16: when and what kind, then what
       happened. Operational facts and decision-relevant reasons only; no
       simulated reasoning appears here because none is produced (FR-E9). -->
  <section class="activity">
    <ol ref="scroller" class="entries" @scroll.passive="onScroll">
      <template v-for="(event, index) in events.events" :key="event.sequence">
        <li v-if="startsPhase(event, events.events[index - 1])" class="divider">
          <span class="phase">{{ event.phase }}</span>
        </li>

        <li class="entry" :data-presentation="presentationOf(event)">
          <div class="meta">
            <span class="clock">{{ clockOf(event.timestamp) }}</span>
            <span class="category">{{ labelOf(event.category) }}</span>
            <span class="sequence">{{ String(event.sequence).padStart(4, '0') }}</span>
          </div>
          <p class="message">{{ event.message }}</p>
        </li>
      </template>

      <li v-if="events.events.length === 0" class="empty">
        The system is initialized and idle. No activity has been recorded yet.
      </li>
    </ol>

    <footer v-if="!following" class="resume">
      <button type="button" class="follow" @click="following = true">
        Jump to latest
      </button>
    </footer>
  </section>
</template>

<style scoped>
.activity {
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 0;
  height: 100%;
}

.entries {
  flex: 1;
  margin: 0;
  padding: var(--space-2) 0;
  overflow-y: auto;
  list-style: none;
  scroll-behavior: smooth;
}

.divider {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-5) var(--space-2);
}

.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-subtle);
}

.phase {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
}

.entry {
  padding: var(--space-3) var(--space-5);
  border-left: 2px solid transparent;
}

.meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.clock {
  color: var(--text-muted);
}

.category {
  flex: 1;
  color: var(--text-secondary);
  letter-spacing: 0.06em;
}

.sequence {
  color: var(--border-strong);
}

.message {
  margin: var(--space-1) 0 0;
  max-width: 54ch;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.55;
}

/* The three states of §61, kept apart (FR-H4). A withheld conclusion is
   not a fault, and a question is neither. */
.entry[data-presentation='error'] {
  border-left-color: var(--status-negative);
}

.entry[data-presentation='error'] .category,
.entry[data-presentation='error'] .message {
  color: var(--status-negative);
}

.entry[data-presentation='decision'] {
  border-left-color: var(--accent);
}

.entry[data-presentation='decision'] .category {
  color: var(--accent);
}

.entry[data-presentation='decision'] .message {
  color: var(--text-primary);
}

.entry[data-presentation='insufficient'] {
  border-left-color: var(--status-neutral);
}

.entry[data-presentation='insufficient'] .category {
  color: var(--status-neutral);
}

.entry[data-presentation='insufficient'] .message {
  color: var(--text-secondary);
  font-style: italic;
}

.empty {
  padding: var(--space-6) var(--space-5);
  color: var(--text-muted);
  font-size: var(--text-sm);
  line-height: 1.55;
}

.resume {
  position: absolute;
  right: var(--space-4);
  bottom: var(--space-3);
}

.follow {
  padding: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  background: var(--surface-overlay);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  box-shadow: var(--shadow-sm);
}

.follow:hover {
  color: var(--text-primary);
  border-color: var(--border-strong);
}
</style>
