<script setup lang="ts">
import { computed } from 'vue'

import { percentOf } from '../design/presentation'
import type { Assessment, Grade, Solution, SolutionStatus } from '../stores/system'

const props = defineProps<{
  solution: Solution
  assessment: Assessment | null
  /** Whether a decision can be made on this solution now. */
  decidable: boolean
  busy: boolean
}>()

const emit = defineEmits<{ review: []; approve: [] }>()

/**
 * One proposed solution, as §24 draws it (FR-A7).
 *
 * The card states the assessment and asks nothing else of the viewer. A
 * PARTIAL grade is shown in the caution colour and never the fault
 * colour: it is a stated limitation on an approvable solution, not a
 * failure (FR-A5, FR-H4). The Approve action is here because §24 puts it
 * here; Reject lives with the evidence, in the review.
 */

/** Filled segments per grade: a grade read at a glance, not decoded. */
const SEGMENTS: Record<Grade, number> = { HIGH: 4, MEDIUM: 3, PARTIAL: 2, LOW: 1 }

const STATUS_LABELS: Record<SolutionStatus, string> = {
  PROPOSED: 'Proposed',
  AWAITING_APPROVAL: 'Awaiting decision',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  BUILDING: 'Building',
  READY: 'Ready',
  RUNNING: 'Running',
}

const grade = computed(() => props.assessment?.feasibility ?? null)
const sufficiency = computed(() => percentOf(props.assessment?.dataSufficiency))
</script>

<template>
  <article class="card" :data-status="solution.status">
    <header class="head">
      <h3 class="name">{{ solution.name }}</h3>
      <span class="status mono">{{ STATUS_LABELS[solution.status] }}</span>
    </header>

    <dl v-if="assessment" class="figures">
      <div class="figure">
        <dt>Potential</dt>
        <dd class="grade" :data-grade="grade">
          <span class="meter" aria-hidden="true">
            <span
              v-for="segment in 4"
              :key="segment"
              class="segment"
              :data-on="grade !== null && segment <= SEGMENTS[grade]"
            />
          </span>
          {{ grade }}
        </dd>
      </div>
      <div class="figure">
        <dt>Data sufficiency</dt>
        <dd class="mono">{{ sufficiency }}</dd>
      </div>
      <div class="figure">
        <dt>Evidence available</dt>
        <dd class="mono">{{ assessment.coverage.located }} / {{ assessment.coverage.required }}</dd>
      </div>
    </dl>

    <p class="description">{{ solution.description }}</p>

    <footer class="actions">
      <button type="button" class="action" @click="emit('review')">Review</button>
      <button
        v-if="solution.status === 'AWAITING_APPROVAL'"
        type="button"
        class="action primary"
        :disabled="!decidable || busy"
        @click="emit('approve')"
      >
        Approve
      </button>
    </footer>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: border-color var(--duration-base) var(--ease-out);
}

.card[data-status='APPROVED'] {
  border-color: var(--status-positive);
}

.card[data-status='REJECTED'] {
  background: var(--surface-base);
}

.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}

.name {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
}

.card[data-status='REJECTED'] .name {
  color: var(--text-muted);
}

.mono {
  font-family: var(--font-mono);
}

.status {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.card[data-status='AWAITING_APPROVAL'] .status {
  color: var(--accent);
}

.card[data-status='APPROVED'] .status {
  color: var(--status-positive);
}

.figures {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: var(--space-3) 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.figure {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: var(--text-xs);
}

.figure dt {
  color: var(--text-muted);
}

.figure dd {
  margin: 0;
  color: var(--text-primary);
}

.grade {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.meter {
  display: inline-flex;
  gap: 2px;
}

.segment {
  width: 10px;
  height: 4px;
  background: var(--border-default);
  border-radius: 1px;
}

.segment[data-on='true'] {
  background: currentColor;
}

.grade[data-grade='HIGH'] {
  color: var(--grade-high);
}

.grade[data-grade='MEDIUM'] {
  color: var(--grade-medium);
}

.grade[data-grade='PARTIAL'] {
  color: var(--grade-partial);
}

.grade[data-grade='LOW'] {
  color: var(--grade-low);
}

.description {
  flex: 1;
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.actions {
  display: flex;
  gap: var(--space-2);
}

.action {
  padding: var(--space-2) var(--space-4);
  color: var(--text-primary);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.action:hover:not(:disabled) {
  border-color: var(--border-strong);
}

.action.primary {
  color: var(--text-inverse);
  background: var(--accent);
  border-color: var(--accent);
}

.action.primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.action:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
