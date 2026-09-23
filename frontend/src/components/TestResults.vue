<script setup lang="ts">
import { computed } from 'vue'

import { secondsOf } from '../design/presentation'
import type { Implementation, Suite, TestCase } from '../stores/system'

const props = defineProps<{
  implementation: Implementation
  focus: string | null
}>()

const emit = defineEmits<{ focus: [component: string | null] }>()

/**
 * The test stage, expanded (FR-I4): every named test case, its outcome and
 * its timing, grouped by suite.
 *
 * A test reads as pending until the stream says it ran, so the list fills
 * in as the build proceeds rather than appearing finished. Timings are
 * simulated and deterministic, and the list says so. There is no source
 * code to show, and none is shown (FR-I5).
 */

const SUITES: { id: Suite; label: string; note: string }[] = [
  { id: 'unit', label: 'Unit', note: 'Each component, as it is generated' },
  { id: 'integration', label: 'Integration', note: 'The pipeline, end to end' },
  {
    id: 'validation',
    label: 'Validation',
    note: 'Analytical output, against the evidence approved on',
  },
]

const names = computed(
  () => new Map(props.implementation.components.map((c) => [c.id, c.name] as const)),
)

const groups = computed(() =>
  SUITES.map((suite) => {
    // The selected component's tests lead, so selecting one shows them
    // without a search; the rest keep their order beneath.
    const tests = props.implementation.tests
      .filter((t) => t.suite === suite.id)
      .sort((a, b) => Number(b.component === props.focus) - Number(a.component === props.focus))
    const ran = tests.filter((t) => t.status !== 'pending')
    return {
      ...suite,
      tests,
      passed: tests.filter((t) => t.status === 'passed').length,
      failed: tests.filter((t) => t.status === 'failed').length,
      durationMs: ran.reduce((total, t) => total + t.durationMs, 0),
      ran: ran.length,
    }
  }),
)

const MARKS: Record<TestCase['status'], string> = { passed: '✓', failed: '✕', pending: '○' }

function dimmed(test: TestCase): boolean {
  return props.focus !== null && test.component !== props.focus
}
</script>

<template>
  <div class="results">
    <p v-if="focus" class="filter">
      Tests of <strong>{{ names.get(focus) }}</strong> first.
      <button type="button" class="clear" @click="emit('focus', null)">Show all</button>
    </p>

    <section v-for="group in groups" :key="group.id" class="suite">
      <header class="suite-head">
        <h4 class="suite-name">{{ group.label }}</h4>
        <span class="suite-note">{{ group.note }}</span>
        <span class="suite-count mono">
          {{ group.passed }} / {{ group.tests.length }}
          <template v-if="group.ran"> · {{ secondsOf(group.durationMs) }}</template>
        </span>
      </header>

      <ol class="cases">
        <li
          v-for="test in group.tests"
          :key="test.id"
          class="case"
          :data-status="test.status"
          :data-dim="dimmed(test)"
        >
          <span class="mark mono" :aria-label="test.status">{{ MARKS[test.status] }}</span>
          <span class="case-text">
            {{ test.name }}
            <span v-if="test.note" class="case-note">{{ test.note }}</span>
          </span>
          <span v-if="test.component" class="case-component mono">{{
            names.get(test.component)
          }}</span>
          <span v-else class="case-component mono">Pipeline</span>
          <span class="case-time mono">{{
            test.status === 'pending' ? '—' : secondsOf(test.durationMs)
          }}</span>
        </li>
      </ol>
    </section>

    <p class="simulated">
      Test runs are simulated for this demonstration; names, outcomes and timings are
      deterministic. No source code is generated, so none is shown.
    </p>
  </div>
</template>

<style scoped>
.results {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  animation: open var(--duration-base) var(--ease-out) both;
}

@keyframes open {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
}

.mono {
  font-family: var(--font-mono);
}

.filter {
  display: flex;
  gap: var(--space-3);
  align-items: baseline;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

.clear {
  padding: 0;
  color: var(--accent);
  background: none;
  border: none;
  font-size: var(--text-xs);
}

.suite-head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.suite-name {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.suite-note {
  flex: 1;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.suite-count {
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

.cases {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-xs);
}

.case {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr) 9rem 4.5rem;
  gap: var(--space-3);
  align-items: baseline;
  padding: 3px 0;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
  transition: opacity var(--duration-fast) var(--ease-out);
}

.case:last-child {
  border-bottom: none;
}

.case[data-dim='true'] {
  opacity: 0.35;
}

.case[data-status='pending'] {
  color: var(--text-muted);
}

.mark {
  text-align: center;
  color: var(--text-muted);
}

.case[data-status='passed'] .mark {
  color: var(--status-positive);
}

.case[data-status='failed'] .mark {
  color: var(--status-negative);
}

.case-note {
  display: block;
  color: var(--text-muted);
}

.case-component {
  overflow: hidden;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-time {
  color: var(--text-secondary);
  text-align: right;
}

.simulated {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
}

@media (prefers-reduced-motion: reduce) {
  .results {
    animation: none;
  }
}
</style>
