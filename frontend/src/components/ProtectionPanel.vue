<script setup lang="ts">
import { computed, ref } from 'vue'

import { clockOf } from '../design/presentation'
import { useProtectionStore, type Effect } from '../stores/protection'

const protection = useProtectionStore()

const EFFECTS: Effect[] = ['ALLOW', 'DENY', 'ESCALATE']

/** Which effects the audit log is showing. Empty means all of them. */
const filtered = ref<Set<Effect>>(new Set())

const visible = computed(() =>
  filtered.value.size === 0
    ? protection.decisions
    : protection.decisions.filter((decision) => filtered.value.has(decision.effect)),
)

function toggle(effect: Effect): void {
  const next = new Set(filtered.value)
  next.has(effect) ? next.delete(effect) : next.add(effect)
  filtered.value = next
}

function countOf(effect: Effect): number {
  return effect === 'ALLOW'
    ? protection.allowed
    : effect === 'DENY'
      ? protection.denied
      : protection.escalated
}
</script>

<template>
  <!-- The layer is cross-cutting, so it has a surface that is present
       whether or not it has interrupted anything (§9, §83.7). Decisions
       also appear inline in the activity stream (FR-P4); this is the
       detail view, with counts and a filterable audit log (FR-P5). -->
  <section class="protection">
    <div class="counts">
      <button
        v-for="effect in EFFECTS"
        :key="effect"
        type="button"
        class="count"
        :data-effect="effect"
        :data-active="filtered.has(effect)"
        @click="toggle(effect)"
      >
        <span class="value">{{ countOf(effect) }}</span>
        <span class="effect">{{ effect }}</span>
      </button>
    </div>

    <div class="log">
      <ol v-if="visible.length > 0" class="decisions">
        <li v-for="decision in visible" :key="decision.sequence" class="decision">
          <div class="head">
            <span class="clock">{{ clockOf(decision.timestamp) }}</span>
            <span class="verdict" :data-effect="decision.effect">{{ decision.effect }}</span>
            <span class="rule">{{ decision.rule }}</span>
          </div>
          <p class="action">{{ decision.action }}</p>
          <p v-if="decision.resource" class="resource">{{ decision.resource }}</p>
        </li>
      </ol>

      <p v-else-if="protection.total > 0" class="note">
        No decisions match the selected effects.
      </p>

      <p v-else class="note">
        No capability has been requested yet. Every action that needs one passes
        through this gate before it proceeds, and every decision is recorded here.
      </p>
    </div>

    <footer class="ruleset">
      <span class="label">Rule set</span>
      <p class="note">
        Loaded from <span class="mono">protection.md</span>. The active rules appear
        here once the policy engine is in place.
      </p>
    </footer>
  </section>
</template>

<style scoped>
.protection {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.counts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  padding: var(--space-4) var(--space-5) var(--space-5);
  background: transparent;
}

.count {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  text-align: left;
  transition: all var(--duration-fast) var(--ease-out);
}

.count:hover {
  border-color: var(--border-strong);
}

.count[data-active='true'] {
  border-color: var(--accent);
  background: var(--accent-subtle);
}

.value {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  line-height: 1;
}

.effect {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
}

.count[data-effect='ALLOW'] .value {
  color: var(--status-positive);
}

.count[data-effect='DENY'] .value {
  color: var(--status-negative);
}

.count[data-effect='ESCALATE'] .value {
  color: var(--status-warning);
}

.log {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-top: 1px solid var(--border-subtle);
}

.decisions {
  margin: 0;
  padding: 0;
  list-style: none;
}

.decision {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}

.head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.clock {
  color: var(--text-muted);
}

.verdict {
  flex: 1;
  letter-spacing: 0.08em;
}

.verdict[data-effect='ALLOW'] {
  color: var(--status-positive);
}

.verdict[data-effect='DENY'] {
  color: var(--status-negative);
}

.verdict[data-effect='ESCALATE'] {
  color: var(--status-warning);
}

.rule {
  color: var(--text-muted);
}

.action {
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.resource {
  margin: var(--space-1) 0 0;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.note {
  margin: 0;
  padding: var(--space-5);
  max-width: 48ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.ruleset {
  padding: var(--space-4) 0 var(--space-2);
  border-top: 1px solid var(--border-subtle);
}

.ruleset .note {
  padding: var(--space-1) var(--space-5) var(--space-3);
}

.label {
  display: block;
  padding: 0 var(--space-5);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
}

.mono {
  font-family: var(--font-mono);
}
</style>
