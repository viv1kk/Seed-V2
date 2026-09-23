<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'

import { percentOf } from '../design/presentation'
import type { Approval, Assessment, Solution, Standing } from '../stores/system'

const props = defineProps<{
  solution: Solution
  assessment: Assessment
  approval: Approval | null
  decidable: boolean
  busy: boolean
}>()

const emit = defineEmits<{ close: []; decide: [decision: 'approve' | 'reject'] }>()

/**
 * The assessment behind a solution, opened beside the cards rather than
 * in place of them (FR-A8, §25).
 *
 * It answers the three questions FR-A9 names --- why this is feasible,
 * how the methodology works, what limits it --- and then says what would
 * improve it (FR-A6), each improvement with the grade it would produce.
 * Every figure is read from the assessment the backend computed; none is
 * worked out here (FR-A2).
 */

const MARKS: Record<Standing, string> = {
  sufficient: '✓',
  limited: '◐',
  incomplete: '!',
  missing: '–',
}

const WORDS: Record<Standing, string> = {
  sufficient: 'Sufficient',
  limited: 'Limited',
  incomplete: 'Insufficient',
  missing: 'Missing',
}

const percent = percentOf

const limitations = computed(() => [
  ...props.assessment.limitations,
  ...props.assessment.declaredLimitations,
])

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <aside class="drawer" :aria-label="`${solution.name} assessment`">
    <header class="head">
      <div class="title-row">
        <h2 class="title">{{ solution.name }}</h2>
        <button type="button" class="close" aria-label="Close" @click="emit('close')">×</button>
      </div>
      <p class="purpose">{{ assessment.purpose }}</p>
      <dl class="headline">
        <div>
          <dt>Feasibility</dt>
          <dd class="grade" :data-grade="assessment.feasibility">{{ assessment.feasibility }}</dd>
        </div>
        <div>
          <dt>Data sufficiency</dt>
          <dd>{{ percent(assessment.dataSufficiency) }}</dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{{ assessment.coverage.located }} / {{ assessment.coverage.required }}</dd>
        </div>
      </dl>
    </header>

    <div class="body">
      <section class="section">
        <h3 class="section-title">Why this is feasible</h3>
        <ul class="requirements">
          <li
            v-for="requirement in assessment.requirements"
            :key="requirement.concept"
            class="requirement"
            :data-standing="requirement.standing"
          >
            <span class="mark" :title="WORDS[requirement.standing]">{{ MARKS[requirement.standing] }}</span>
            <span class="requirement-text">
              {{ requirement.description }}
              <span v-if="requirement.weakest" class="source mono">
                {{ requirement.weakest.label }}.{{ requirement.weakest.field }}
              </span>
            </span>
            <span class="coverage mono">{{ percent(requirement.coverage) }}</span>
          </li>
        </ul>
      </section>

      <section class="section">
        <h3 class="section-title">Methodology</h3>
        <ol class="process">
          <li v-for="(step, index) in assessment.process" :key="index" class="step">
            <span class="step-index mono">{{ index + 1 }}</span>
            {{ step }}
          </li>
        </ol>
      </section>

      <section v-if="limitations.length" class="section">
        <h3 class="section-title">Limitations</h3>
        <ul class="notes">
          <li v-for="(line, index) in limitations" :key="index">{{ line }}</li>
        </ul>
      </section>

      <section v-if="assessment.improvements.length" class="section">
        <h3 class="section-title">What would improve it</h3>
        <ul class="improvements">
          <li v-for="item in assessment.improvements" :key="item.concept" class="improvement">
            <span>{{ item.action }}</span>
            <span class="target">{{ item.target }}</span>
            <span v-if="item.from !== item.to" class="lift mono">
              {{ item.from }} → {{ item.to }}
            </span>
          </li>
        </ul>
      </section>

      <section class="section">
        <h3 class="section-title">Recommendation</h3>
        <p class="recommendation">{{ assessment.recommendation }}</p>
      </section>

      <p class="simulated">
        Figures are simulated demo values, computed from the profile of a simulated environment.
        They are not measurements of a real enterprise.
      </p>
    </div>

    <footer class="foot">
      <template v-if="solution.status === 'AWAITING_APPROVAL'">
        <button
          type="button"
          class="action primary"
          :disabled="!decidable || busy"
          @click="emit('decide', 'approve')"
        >
          Approve Agent Component
        </button>
        <button
          type="button"
          class="action"
          :disabled="!decidable || busy"
          @click="emit('decide', 'reject')"
        >
          Reject
        </button>
      </template>
      <p v-else-if="approval" class="decided">
        {{ approval.decision === 'APPROVED' ? 'Approved' : 'Rejected' }} on feasibility
        {{ approval.feasibility }}, under {{ approval.rule }}. The decision is recorded with the
        evidence it was made on.
      </p>
    </footer>
  </aside>
</template>

<style scoped>
.drawer {
  position: absolute;
  inset: 0 0 0 auto;
  z-index: 2;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  width: min(34rem, 100%);
  background: var(--surface-overlay);
  border-left: 1px solid var(--border-default);
  box-shadow: var(--shadow-md);
  animation: slide var(--duration-base) var(--ease-out) both;
}

@keyframes slide {
  from {
    opacity: 0;
    transform: translateX(1.5rem);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.head {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-6) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}

.title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
}

.close {
  padding: 0 var(--space-1);
  color: var(--text-muted);
  background: none;
  border: none;
  font-size: var(--text-lg);
  line-height: 1;
}

.close:hover {
  color: var(--text-primary);
}

.purpose {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.headline {
  display: flex;
  gap: var(--space-8);
  margin: 0;
}

.headline dt {
  color: var(--text-muted);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.headline dd {
  margin: var(--space-1) 0 0;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-md);
}

.grade[data-grade='HIGH'] {
  color: var(--status-positive);
}

.grade[data-grade='PARTIAL'] {
  color: var(--status-warning);
}

.grade[data-grade='LOW'] {
  color: var(--status-neutral);
}

.body {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5) var(--space-6);
  overflow-y: auto;
}

.section-title {
  margin: 0 0 var(--space-2);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.mono {
  font-family: var(--font-mono);
}

.requirements,
.notes,
.improvements,
.process {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-xs);
  line-height: 1.5;
}

.requirement {
  display: grid;
  grid-template-columns: 1rem 1fr auto;
  gap: var(--space-2);
  align-items: baseline;
  color: var(--text-primary);
}

.mark {
  font-family: var(--font-mono);
  text-align: center;
}

.requirement[data-standing='sufficient'] .mark {
  color: var(--status-positive);
}

.requirement[data-standing='limited'] .mark {
  color: var(--text-secondary);
}

.requirement[data-standing='incomplete'] .mark,
.requirement[data-standing='incomplete'] .coverage {
  color: var(--status-warning);
}

.requirement[data-standing='missing'] .mark {
  color: var(--status-neutral);
}

.source {
  display: block;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.coverage {
  color: var(--text-secondary);
}

.step {
  display: flex;
  gap: var(--space-3);
  align-items: baseline;
  color: var(--text-primary);
}

.step-index {
  flex: none;
  width: 1.25rem;
  color: var(--text-muted);
  text-align: right;
}

.notes li {
  padding-left: var(--space-3);
  color: var(--text-secondary);
  border-left: 2px solid var(--border-default);
}

.improvement {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: var(--space-3);
  color: var(--text-primary);
  border-left: 2px solid var(--accent);
}

.target {
  color: var(--text-secondary);
}

.lift {
  color: var(--accent);
}

.recommendation {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.simulated {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-style: italic;
  line-height: 1.5;
}

.foot {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--border-subtle);
}

.decided {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.action {
  padding: var(--space-2) var(--space-4);
  color: var(--text-primary);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
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

@media (prefers-reduced-motion: reduce) {
  .drawer {
    animation: none;
  }
}
</style>
