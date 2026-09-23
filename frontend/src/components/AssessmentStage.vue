<script setup lang="ts">
import { computed, ref } from 'vue'

import ReviewDrawer from './ReviewDrawer.vue'
import SolutionCard from './SolutionCard.vue'
import { useEventStore } from '../stores/events'
import { useSystemStore } from '../stores/system'

const system = useSystemStore()
const events = useEventStore()

/**
 * The Assessment stage: what can actually be done, and a person deciding.
 *
 * §51 describes this as the point where the system shows it is reasoning
 * about what is possible. So the cards appear as each methodology is
 * assessed, with the grade the evidence supports, and the decisions are
 * made on them rather than in a separate form.
 *
 * Everything shown is folded from the stream: the assessments, the
 * solutions and the decisions. A button press sends a decision and
 * nothing else; the card changes when the decision comes back recorded.
 */

const APPROVAL_REQUEST = 'solution-approval'

const reviewing = ref<string | null>(null)
const busy = ref(false)

const cards = computed(() => {
  const proposed = system.solutions.map((solution) => ({
    key: solution.id,
    solution,
    assessment: system.assessments.find((a) => a.id === solution.assessmentId) ?? null,
  }))
  // Before the solutions are proposed, the assessments alone are shown,
  // so each card appears as its methodology is assessed.
  const pending = system.assessments
    .filter((a) => !system.solutions.some((s) => s.assessmentId === a.id))
    .map((assessment) => ({
      key: assessment.id,
      solution: {
        id: assessment.id,
        methodologyId: assessment.methodologyId,
        assessmentId: assessment.id,
        name: assessment.name,
        description: assessment.purpose,
        status: 'PROPOSED' as const,
        dashboardId: null,
      },
      assessment,
    }))
  return [...proposed, ...pending]
})

const decidable = computed(() => system.blockedOn?.requestId === APPROVAL_REQUEST)

const open = computed(() => {
  const card = cards.value.find((c) => c.key === reviewing.value)
  if (!card || !card.assessment) {
    return null
  }
  const approval =
    [...system.approvals].reverse().find((a) => a.solutionId === card.solution.id) ?? null
  return { ...card, assessment: card.assessment, approval }
})

const decided = computed(() => ({
  approved: system.solutions.filter((s) => s.status === 'APPROVED').length,
  rejected: system.solutions.filter((s) => s.status === 'REJECTED').length,
}))

const basis = computed(() => {
  const summary = system.environment?.summary
  return summary
    ? `Assessed against ${summary.profiled} profiled datasets from ${summary.systems} systems.`
    : 'Assessed against the environment discovery profiled.'
})

async function decide(solutionId: string, decision: 'approve' | 'reject'): Promise<void> {
  busy.value = true
  try {
    await events.decide(solutionId, decision)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="assessment">
    <header class="head">
      <div class="title-row">
        <h2 class="title">Assessment</h2>
        <span v-if="decided.approved + decided.rejected > 0" class="tally mono">
          {{ decided.approved }} approved · {{ decided.rejected }} rejected
        </span>
      </div>
      <p class="note">
        {{ basis }} Feasibility is computed from field completeness; figures are simulated demo
        values.
      </p>
    </header>

    <p v-if="cards.length === 0" class="empty">Assessing methodologies against the evidence.</p>

    <div v-else class="cards">
      <SolutionCard
        v-for="card in cards"
        :key="card.key"
        :solution="card.solution"
        :assessment="card.assessment"
        :decidable="decidable"
        :busy="busy"
        @review="reviewing = card.key"
        @approve="decide(card.solution.id, 'approve')"
      />
    </div>

    <ReviewDrawer
      v-if="open"
      :solution="open.solution"
      :assessment="open.assessment"
      :approval="open.approval"
      :decidable="decidable"
      :busy="busy"
      @close="reviewing = null"
      @decide="(decision) => decide(open!.solution.id, decision)"
    />
  </div>
</template>

<style scoped>
.assessment {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-height: 100%;
}

.head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-4);
}

.title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.mono {
  font-family: var(--font-mono);
}

.tally {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.note,
.empty {
  margin: 0;
  max-width: 70ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
  gap: var(--space-4);
  align-items: stretch;
}
</style>
