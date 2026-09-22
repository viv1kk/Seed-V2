<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { clockOf } from '../design/presentation'
import { useProtectionStore, type Effect } from '../stores/protection'

const protection = useProtectionStore()

const EFFECTS: Effect[] = ['ALLOW', 'DENY', 'ESCALATE']

type View = 'log' | 'rules'

const view = ref<View>('log')

/** Which effects the audit log is showing. Empty means all of them. */
const effects = ref<Set<Effect>>(new Set())

/** A single rule the audit log is narrowed to, chosen from the rule set. */
const rule = ref<string | null>(null)

onMounted(() => protection.fetchRules())

const visible = computed(() =>
  protection.decisions.filter(
    (decision) =>
      (effects.value.size === 0 || effects.value.has(decision.effect)) &&
      (rule.value === null || decision.rule === rule.value),
  ),
)

const filtering = computed(() => effects.value.size > 0 || rule.value !== null)

function toggle(effect: Effect): void {
  const next = new Set(effects.value)
  if (next.has(effect)) {
    next.delete(effect)
  } else {
    next.add(effect)
  }
  effects.value = next
  view.value = 'log'
}

function narrowTo(id: string): void {
  rule.value = rule.value === id ? null : id
  view.value = 'log'
}

function clear(): void {
  effects.value = new Set()
  rule.value = null
}

function countOf(effect: Effect): number {
  if (effect === 'ALLOW') return protection.allowed
  if (effect === 'DENY') return protection.denied
  return protection.escalated
}

/** Rules that applied but did not decide, which the record keeps visible. */
function overruled(matched: string[], deciding: string): string[] {
  return matched.filter((id) => id !== deciding)
}
</script>

<template>
  <!-- The layer is cross-cutting, so it has a surface that is present
       whether or not it has interrupted anything (§9, §83.7). Decisions
       also appear inline in the activity stream (FR-P4); this is the
       detail view: the active rule set, running counts and a filterable
       audit log (FR-P5). -->
  <section class="protection">
    <div class="counts">
      <button
        v-for="effect in EFFECTS"
        :key="effect"
        type="button"
        class="count"
        :data-effect="effect"
        :data-active="effects.has(effect)"
        :aria-pressed="effects.has(effect)"
        @click="toggle(effect)"
      >
        <span class="value">{{ countOf(effect) }}</span>
        <span class="effect">{{ effect }}</span>
      </button>
    </div>

    <nav class="views">
      <button type="button" class="view" :data-active="view === 'log'" @click="view = 'log'">
        Audit log
      </button>
      <button type="button" class="view" :data-active="view === 'rules'" @click="view = 'rules'">
        Rule set <span class="mono muted">{{ protection.ruleCount }}</span>
      </button>
      <button v-if="filtering && view === 'log'" type="button" class="clear" @click="clear()">
        Clear filter{{ rule ? ` · ${rule}` : '' }}
      </button>
    </nav>

    <!-- The audit log: what the system asked to do, and what it was told. -->
    <div v-show="view === 'log'" class="scroll">
      <ol v-if="visible.length > 0" class="decisions">
        <li
          v-for="decision in visible"
          :key="decision.sequence"
          class="decision"
          :data-effect="decision.effect"
        >
          <div class="head">
            <span class="clock">{{ clockOf(decision.timestamp) }}</span>
            <span class="verdict">{{ decision.effect }}</span>
            <button type="button" class="rule-id" @click="narrowTo(decision.rule)">
              {{ decision.rule }}
            </button>
          </div>
          <p class="action">
            {{ decision.action }} <span class="resource">{{ decision.resource }}</span>
          </p>
          <p v-if="decision.purpose" class="detail">
            <span class="term">Purpose</span> {{ decision.purpose }}
          </p>
          <p v-if="decision.effect !== 'ALLOW'" class="detail">
            <span class="term">Reason</span> {{ decision.reason }}
          </p>
          <p v-if="overruled(decision.matched, decision.rule).length > 0" class="detail">
            <span class="term">Overruled</span>
            <span class="mono">{{ overruled(decision.matched, decision.rule).join(', ') }}</span>
          </p>
        </li>
      </ol>

      <p v-else-if="protection.total > 0" class="note">No decisions match the filter.</p>

      <p v-else class="note">
        No capability has been requested yet. Every action that needs one passes through
        this gate before it proceeds, and every decision is recorded here.
      </p>
    </div>

    <!-- The rule set being enforced, served from the engine rather than the
         document, so this is what is applied (FR-P7). -->
    <div v-show="view === 'rules'" class="scroll">
      <p class="note">
        All matching rules are evaluated and the strictest decision wins. A request that
        matches nothing is denied under PR-000. Mirrored in
        <span class="mono">protection.md</span>.
      </p>

      <section v-for="group in protection.groups" :key="group.name" class="group">
        <h3 class="group-name">{{ group.name }}</h3>
        <ul class="rules">
          <li v-for="entry in group.rules" :key="entry.id">
            <button
              type="button"
              class="rule"
              :data-effect="entry.effect"
              :data-active="rule === entry.id"
              :disabled="!protection.citations[entry.id]"
              @click="narrowTo(entry.id)"
            >
              <span class="rule-head">
                <span class="mono">{{ entry.id }}</span>
                <span class="verdict">{{ entry.effect }}</span>
                <span v-if="protection.citations[entry.id]" class="cited mono">
                  {{ protection.citations[entry.id] }}×
                </span>
              </span>
              <span class="rule-text">{{ entry.description }}</span>
            </button>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>

<style scoped>
.protection {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-height: 0;
  height: 100%;
}

.counts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
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
  transition: border-color var(--duration-fast) var(--ease-out);
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

.views {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}

.view {
  padding: var(--space-2) 0;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 1px solid transparent;
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
}

.view[data-active='true'] {
  color: var(--text-primary);
  border-bottom-color: var(--text-secondary);
}

.clear {
  margin-left: auto;
  color: var(--accent);
  background: none;
  border: none;
  font-size: var(--text-xs);
}

.scroll {
  min-height: 0;
  overflow-y: auto;
}

.decisions,
.rules {
  margin: 0;
  padding: 0;
  list-style: none;
}

.decision {
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
  border-left: 2px solid transparent;
}

.decision[data-effect='DENY'] {
  border-left-color: var(--status-negative);
}

.decision[data-effect='ESCALATE'] {
  border-left-color: var(--status-warning);
}

.head,
.rule-head {
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

[data-effect='ALLOW'] .verdict {
  color: var(--status-positive);
}

[data-effect='DENY'] .verdict {
  color: var(--status-negative);
}

[data-effect='ESCALATE'] .verdict {
  color: var(--status-warning);
}

.rule-id {
  padding: 0;
  color: var(--text-muted);
  background: none;
  border: none;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-decoration: underline dotted;
  text-underline-offset: 3px;
}

.rule-id:hover {
  color: var(--text-primary);
}

.action {
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.resource {
  color: var(--text-primary);
}

.detail {
  margin: var(--space-1) 0 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.55;
}

.term {
  display: inline-block;
  min-width: 5.5rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
}

.note {
  margin: 0;
  padding: var(--space-4) var(--space-5);
  max-width: 52ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.group {
  padding: 0 var(--space-5) var(--space-3);
}

.group-name {
  margin: var(--space-3) 0 var(--space-2);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 400;
  letter-spacing: 0.08em;
}

.rule {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: none;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  text-align: left;
}

.rule:not(:disabled):hover {
  border-color: var(--border-subtle);
  background: var(--surface-sunken);
}

.rule:disabled {
  cursor: default;
}

.rule[data-active='true'] {
  border-color: var(--accent);
}

.rule-text {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.cited {
  color: var(--text-primary);
}

.mono {
  font-family: var(--font-mono);
}

.muted {
  color: var(--text-muted);
}
</style>
