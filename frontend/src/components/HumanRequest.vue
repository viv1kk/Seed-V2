<script setup lang="ts">
import { ref } from 'vue'

import { useEventStore } from '../stores/events'
import type { BlockedOn } from '../stores/system'

const props = defineProps<{ request: BlockedOn }>()

const events = useEventStore()
const username = ref('')
const password = ref('')
const submitting = ref(false)

/**
 * Submit and forget.
 *
 * The fields are cleared before the request settles, so the values do
 * not sit in component state waiting for a response. The backend
 * discards them too (FR-H5); this is the frontend half of the same
 * promise.
 */
async function submit(): Promise<void> {
  submitting.value = true
  const submission =
    props.request.kind === 'credentials'
      ? { username: username.value, password: password.value }
      : { acknowledged: true }

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
  <!-- Present only while input is required, and gone once resolved.
       It does not hold a reserved slot in the layout (FR-H1). -->
  <form class="request" :data-kind="request.kind" @submit.prevent="submit">
    <span class="kind">{{ request.kind }}</span>
    <p class="prompt">{{ request.prompt }}</p>

    <div v-if="request.kind === 'credentials'" class="fields">
      <label class="field">
        <span class="label">Account</span>
        <input v-model="username" type="text" autocomplete="off" spellcheck="false" />
      </label>
      <label class="field">
        <span class="label">Secret</span>
        <input v-model="password" type="password" autocomplete="off" />
      </label>
    </div>

    <div class="foot">
      <button type="submit" class="submit" :disabled="submitting">Submit and continue</button>
      <span class="note">Values are used for the handshake and discarded. Nothing is stored.</span>
    </div>
  </form>
</template>

<style scoped>
.request {
  margin: var(--space-6) 0;
  padding: var(--space-4) var(--space-6) var(--space-6);
  background: var(--surface-sunken);
  border: 1px solid var(--border-default);
  border-left: 2px solid var(--accent);
  border-radius: var(--radius-md);
}

/* The kinds are visually distinct, so an approval never reads like an
   error and an error never reads like a decision (FR-H3, FR-H4). */
.request[data-kind='credentials'] {
  border-left-color: var(--accent);
}

.request[data-kind='approval'] {
  border-left-color: var(--status-positive);
}

.request[data-kind='ambiguity'],
.request[data-kind='missing-info'] {
  border-left-color: var(--status-warning);
}

.kind {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.prompt {
  margin: var(--space-2) 0 var(--space-4);
  max-width: 46rem;
  font-size: var(--text-sm);
  color: var(--text-primary);
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
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

input {
  width: 13rem;
  padding: var(--space-1) var(--space-2);
  color: var(--text-primary);
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

input:focus {
  outline: 2px solid var(--accent);
  outline-offset: -1px;
}

.foot {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.submit {
  padding: var(--space-1) var(--space-4);
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
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
