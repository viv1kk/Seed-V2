<script setup lang="ts">
import { computed, ref } from 'vue'

import { useEventStore } from '../stores/events'
import type { BlockedOn, RequestKind } from '../stores/system'

const props = defineProps<{ request: BlockedOn }>()

const events = useEventStore()
const username = ref('')
const password = ref('')
const submitting = ref(false)

/**
 * What the request is called on screen.
 *
 * Five distinct kinds (FR-H3), and none of them reads as a fault. §61's
 * distinction survives here or nowhere: this surface only ever presents
 * decisions, and an error never appears in it.
 */
const HEADINGS: Record<RequestKind, string> = {
  credentials: 'Authentication required',
  ambiguity: 'Decision required',
  'missing-info': 'Information required',
  approval: 'Approval required',
  confirmation: 'Confirmation required',
}

/** The action, named for what it does rather than "Submit" five times. */
const ACTIONS: Record<RequestKind, string> = {
  credentials: 'Configure',
  ambiguity: 'Select',
  'missing-info': 'Provide',
  approval: 'Approve',
  confirmation: 'Confirm',
}

const heading = computed(() => HEADINGS[props.request.kind])
const action = computed(() => ACTIONS[props.request.kind])
const isCredentials = computed(() => props.request.kind === 'credentials')
const hasOptions = computed(() => props.request.options.length > 0)

/**
 * An approval is answered on the solution cards, beside the evidence each
 * decision rests on (FR-A7, FR-A8). This surface still appears, because
 * the system is waiting on a person and says so (FR-H1), but it offers no
 * button of its own: a single Approve here would approve nothing in
 * particular.
 */
const answeredElsewhere = computed(() => props.request.kind === 'approval' && !hasOptions.value)

/**
 * Submit and forget.
 *
 * Credential fields are cleared before the request settles, so the values
 * do not sit in component state waiting for a response. The backend
 * discards them too (FR-H5); this is the frontend half of the same
 * promise.
 */
async function submit(chosen?: string): Promise<void> {
  submitting.value = true

  const submission: Record<string, unknown> = isCredentials.value
    ? { username: username.value, password: password.value }
    : { acknowledged: true }

  if (chosen !== undefined) {
    submission.choice = chosen
  }

  username.value = ''
  password.value = ''

  try {
    await events.submitHuman(props.request.requestId, submission)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <!-- Present only while input is required, and gone once resolved. It
       holds no reserved slot in the layout (FR-H1). -->
  <form class="request" :data-kind="request.kind" @submit.prevent="submit()">
    <header class="head">
      <span class="heading">{{ heading }}</span>
      <span class="kind mono">{{ request.kind }}</span>
    </header>

    <!-- What is needed, what access it requires, and why (FR-H2). Three
         labelled facts rather than one sentence, because the third is the
         one that makes an escalation answerable. -->
    <p class="prompt">{{ request.prompt }}</p>

    <dl class="facts">
      <template v-if="request.access">
        <dt>Required access</dt>
        <dd>{{ request.access }}</dd>
      </template>
      <template v-if="request.reason">
        <dt>Reason</dt>
        <dd>{{ request.reason }}</dd>
      </template>
    </dl>

    <div v-if="isCredentials" class="fields">
      <label class="field">
        <span class="label">Account</span>
        <input v-model="username" type="text" autocomplete="off" spellcheck="false" />
      </label>
      <label class="field">
        <span class="label">Secret</span>
        <input v-model="password" type="password" autocomplete="off" />
      </label>
    </div>

    <!-- A choice between stated alternatives, which is what ambiguity,
         missing information and approval actually are (§8, §18). -->
    <div v-if="hasOptions" class="options">
      <button
        v-for="option in request.options"
        :key="option.value"
        type="button"
        class="option"
        :disabled="submitting"
        @click="submit(option.value)"
      >
        <span class="option-label">{{ option.label }}</span>
        <span v-if="option.note" class="option-note">{{ option.note }}</span>
      </button>
    </div>

    <div class="foot">
      <button
        v-if="!hasOptions && !answeredElsewhere"
        type="submit"
        class="submit"
        :disabled="submitting"
      >
        {{ submitting ? 'Working…' : action }}
      </button>
      <span v-if="isCredentials" class="note">
        Values are used for the handshake and discarded. Nothing is stored.
      </span>
      <span v-else-if="answeredElsewhere" class="note">
        Approve or reject each solution on its card. Every decision is recorded with the evidence
        it was made on.
      </span>
      <span v-else class="note">The decision is recorded in the audit log.</span>
    </div>
  </form>
</template>

<style scoped>
.request {
  padding: var(--space-4) var(--space-6) var(--space-5);
  background: var(--surface-raised);
  border-top: 1px solid var(--border-default);
  border-left: 2px solid var(--accent);
}

/* The kinds are visually distinct, so an approval never reads like an
   error and an error never reads like a decision (FR-H3, FR-H4). None of
   these is the negative colour: nothing has gone wrong here. */
.request[data-kind='credentials'] {
  border-left-color: var(--accent);
}

.request[data-kind='approval'],
.request[data-kind='confirmation'] {
  border-left-color: var(--status-positive);
}

.request[data-kind='ambiguity'],
.request[data-kind='missing-info'] {
  border-left-color: var(--status-warning);
}

.head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.heading {
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.kind {
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.mono {
  font-family: var(--font-mono);
}

.prompt {
  margin: var(--space-2) 0 var(--space-3);
  max-width: 68ch;
  color: var(--text-primary);
  font-size: var(--text-sm);
  line-height: 1.55;
}

.facts {
  display: grid;
  grid-template-columns: auto minmax(0, 60ch);
  /* Without this the auto column stretches to absorb the free width, and
     each fact sits a screen away from its label. */
  justify-content: start;
  gap: var(--space-1) var(--space-4);
  margin: 0 0 var(--space-4);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.facts dt {
  color: var(--text-muted);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.facts dd {
  margin: 0;
  color: var(--text-secondary);
}

.fields {
  display: flex;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.label {
  color: var(--text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

input {
  width: 13rem;
  padding: var(--space-1) var(--space-2);
  color: var(--text-primary);
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

input:focus {
  outline: 2px solid var(--accent);
  outline-offset: -1px;
}

.options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.option {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  color: var(--text-primary);
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  text-align: left;
  transition: all var(--duration-fast) var(--ease-out);
}

.option:hover:not(:disabled) {
  border-color: var(--accent);
}

.option-label {
  font-size: var(--text-sm);
}

.option-note {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.foot {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.submit {
  padding: var(--space-1) var(--space-5);
  color: var(--text-inverse);
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  transition: background var(--duration-fast) var(--ease-out);
}

.submit:hover:not(:disabled) {
  background: var(--accent-hover);
}

.submit:disabled {
  opacity: 0.5;
  cursor: default;
}

.note {
  color: var(--text-muted);
  font-size: var(--text-xs);
}
</style>
