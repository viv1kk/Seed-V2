<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import { useEventStore } from '../stores/events'
import { useSystemStore } from '../stores/system'

const events = useEventStore()
const system = useSystemStore()

/**
 * Cleanup: closing the seeding phase, as a process (D-16, FR-C3).
 *
 * "Cleanup" is the screen's name for it; the code keeps `CLOSING_SEEDING`,
 * as it keeps other names the screen displays differently (D-11).
 *
 * Once the build is done, the tools that built Agent One VW are cleaned up
 * after: the working notes consolidated, the scratch space purged, the
 * interfaces promoted and the build tools retired, and then the seed is
 * consumed. Each step is shown with the decision the protection engine
 * took on it and the rule it cited (FR-C4). Everything here is read from
 * the event log, so a reload shows the same progress.
 */
const STEPS = [
  {
    event: 'seeding.notes.consolidated',
    verb: 'consolidate-records',
    label: 'Consolidate working notes',
  },
  { event: 'seeding.scratch.cleared', verb: 'clear-scratch', label: 'Purge scratch space' },
  {
    event: 'seeding.interfaces.promoted',
    verb: 'promote-interface',
    label: 'Promote interfaces to release',
  },
  { event: 'seeding.tools.retired', verb: 'retire-tool', label: 'Retire the build tools' },
  { event: 'seeding.consumed', verb: null, label: 'Seed consumed' },
] as const

const started = computed(() => events.events.some((e) => e.type === 'seeding.closing.started'))

const steps = computed(() => {
  const done = new Map(
    events.events.filter((e) => e.type.startsWith('seeding.')).map((e) => [e.type, e]),
  )
  const decisions = events.events.filter(
    (e) => e.type === 'policy.decision' && STEPS.some((s) => s.verb === e.payload.verb),
  )
  let current = started.value
  return STEPS.map((step) => {
    const record = done.get(step.event)
    const status = record ? 'done' : current ? 'running' : 'waiting'
    if (!record) current = false
    const rules = decisions
      .filter((d) => d.payload.verb === step.verb)
      .map((d) => `${d.payload.effect} ${d.payload.rule}`)
    return {
      ...step,
      status,
      message: record?.message ?? null,
      rules: [...new Set(rules)],
    }
  })
})

const visible = computed(() =>
  ['IMPLEMENTATION_COMPLETE', 'CLOSING_SEEDING', 'READY_TO_RUN', 'RUNNING'].includes(
    system.lifecycle,
  ),
)

const waiting = computed(() => system.lifecycle === 'IMPLEMENTATION_COMPLETE')

/**
 * The checklist sits below the build lanes, out of view once they fill
 * the stage. When the confirmation is asked for, and again when cleanup
 * begins, it is brought into view, so the clean-up is seen as it happens.
 */
const section = ref<HTMLElement | null>(null)
watch(
  () => [waiting.value, started.value],
  async ([asking, running], before) => {
    if (before === undefined || !(asking || running)) return
    await nextTick()
    section.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  },
)
</script>

<template>
  <section v-if="visible" ref="section" class="closing" aria-label="Cleanup">
    <header class="head">
      <h3 class="title">Cleanup <span class="subtitle">after implementation</span></h3>
      <p class="note">
        <template v-if="waiting">
          Built and validated. Confirm to clean up after the build: the tools that built Agent One
          VW are discarded, and the seed is consumed.
        </template>
        <template v-else>
          The tools that built Agent One VW are cleaned up after. Agent One VW carries what the seed
          held, and stands on its own.
        </template>
      </p>
    </header>

    <ol class="steps">
      <li v-for="step in steps" :key="step.event" class="step" :data-status="step.status">
        <span class="mark" aria-hidden="true">{{
          step.status === 'done' ? '✓' : step.status === 'running' ? '•' : ''
        }}</span>
        <div class="body">
          <div class="line">
            <span class="label">{{ step.label }}</span>
            <span v-for="rule in step.rules" :key="rule" class="rule mono">{{ rule }}</span>
          </div>
          <p v-if="step.message" class="message">{{ step.message }}</p>
          <p v-else class="message pending">
            {{
              step.status === 'running'
                ? 'In progress'
                : started
                  ? 'Queued'
                  : 'Waiting for confirmation'
            }}
          </p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.closing {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  background: var(--surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.head {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.title {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.subtitle {
  margin-left: var(--space-2);
  color: var(--text-muted);
  font-weight: 400;
  letter-spacing: 0.04em;
  text-transform: none;
}

.note {
  margin: 0;
  max-width: 68ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.step {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: var(--space-2);
  align-items: baseline;
}

.mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  border: 1px solid var(--border-default);
  border-radius: 50%;
  color: var(--text-inverse);
  font-size: 0.625rem;
  transition:
    background var(--duration-base) var(--ease-out),
    border-color var(--duration-base) var(--ease-out);
}

.step[data-status='done'] .mark {
  background: var(--status-positive);
  border-color: var(--status-positive);
}

.step[data-status='running'] .mark {
  color: var(--accent);
  border-color: var(--accent);
}

.line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
}

.label {
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.step[data-status='waiting'] .label {
  color: var(--text-muted);
}

.rule {
  color: var(--status-positive);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
}

.mono {
  font-family: var(--font-mono);
}

.message {
  margin: var(--space-1) 0 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: 1.55;
}

.message.pending {
  color: var(--text-muted);
  font-style: italic;
}
</style>
