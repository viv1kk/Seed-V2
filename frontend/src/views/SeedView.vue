<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useSeedStore, type Layer } from '../stores/seed'

const seed = useSeedStore()

/** The slot currently under a drag, so the target can acknowledge it. */
const hovering = ref<Layer | null>(null)

/** One hidden input per slot, opened when the slot is activated. */
const pickers = ref<Record<string, HTMLInputElement | null>>({})

onMounted(() => seed.fetchLayers())

function onDrop(layer: Layer, drop: DragEvent): void {
  hovering.value = null
  const file = drop.dataTransfer?.files?.[0]
  if (file) {
    void seed.supplyFile(layer, file)
  }
}

function onChoose(layer: Layer, change: Event): void {
  const input = change.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    void seed.supplyFile(layer, file)
  }
  // Cleared so choosing the same file twice still fires a change.
  input.value = ''
}

function open(layer: Layer): void {
  pickers.value[layer]?.click()
}
</script>

<template>
  <!-- Planting the seed, not uploading files (FR-S2, §12, §48). The
       three layers are named for what they are and each says what it
       answers, so the gesture reads as giving the system a foundation. -->
  <main class="seed">
    <header class="head">
      <h1 class="title">Systems</h1>
      <p class="subtitle">Plant the methodology.</p>
    </header>

    <div class="layers">
      <section
        v-for="slot in seed.slots"
        :key="slot.descriptor.layer"
        class="layer"
        :data-state="slot.error ? 'rejected' : slot.summary ? 'loaded' : 'empty'"
        :data-hovering="hovering === slot.descriptor.layer"
        @dragenter.prevent="hovering = slot.descriptor.layer"
        @dragover.prevent
        @dragleave="hovering = null"
        @drop.prevent="onDrop(slot.descriptor.layer, $event)"
      >
        <span class="name">{{ slot.descriptor.layer }}</span>
        <p class="role">{{ slot.descriptor.role }}</p>

        <!-- Before anything lands: the gesture. -->
        <button
          v-if="!slot.summary && !slot.error"
          type="button"
          class="target"
          :disabled="slot.busy"
          @click="open(slot.descriptor.layer)"
        >
          <span class="plus" aria-hidden="true">+</span>
          <span class="invite">
            {{ slot.busy ? 'Reading…' : `Drop ${slot.descriptor.filename}` }}
          </span>
        </button>

        <!-- After it lands: what was actually found in it (FR-S5). -->
        <dl v-else-if="slot.summary" class="summary">
          <div class="check">
            <span class="tick" aria-hidden="true">✓</span>
            <span>Loaded</span>
            <span class="file">{{ slot.supplied }}</span>
          </div>
          <div class="check">
            <span class="tick" aria-hidden="true">✓</span>
            <span>Parsed</span>
            <span class="file">{{ slot.summary.title ?? 'no title' }}</span>
          </div>

          <div class="counts">
            <dt>Headings</dt>
            <dd>{{ slot.summary.headingCount }}</dd>
            <dt>Sections</dt>
            <dd>{{ slot.summary.sections }}</dd>
            <dt>Topics</dt>
            <dd>{{ slot.summary.topics }}</dd>
            <dt>Lines</dt>
            <dd>{{ slot.summary.lines }}</dd>
          </div>

          <p v-if="slot.summary.headingCount === 0" class="plain">
            No headings found. The layer is registered as plain text.
          </p>

          <button type="button" class="replace" @click="seed.clear(slot.descriptor.layer)">
            Replace
          </button>
        </dl>

        <!-- Refused, with the reason (FR-S4). -->
        <div v-else class="rejected">
          <span class="cross" aria-hidden="true">✕</span>
          <p class="reason">
            <span class="file">{{ slot.supplied }}</span>
            was not accepted: {{ slot.error }}.
          </p>
          <button type="button" class="replace" @click="seed.clear(slot.descriptor.layer)">
            Try another file
          </button>
        </div>

        <input
          :ref="(element) => (pickers[slot.descriptor.layer] = element as HTMLInputElement)"
          class="picker"
          type="file"
          accept=".md,.markdown,text/markdown,text/plain"
          @change="onChoose(slot.descriptor.layer, $event)"
        />
      </section>
    </div>

    <footer class="foot">
      <button
        type="button"
        class="initialize"
        :disabled="!seed.ready || seed.initializing"
        @click="seed.initialize()"
      >
        {{ seed.initializing ? 'Initializing…' : 'Initialize' }}
      </button>
      <p class="progress">
        <template v-if="seed.ready">Three layers supplied. The system can be planted.</template>
        <template v-else>{{ seed.count }} of 3 layers supplied.</template>
      </p>
      <p v-if="seed.failure" class="failure">{{ seed.failure }}</p>
    </footer>
  </main>
</template>

<style scoped>
.seed {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-10);
  min-height: 100%;
  padding: var(--space-10) var(--space-6);
}

.head {
  text-align: center;
}

.title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.subtitle {
  margin: var(--space-2) 0 0;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.layers {
  display: grid;
  grid-template-columns: repeat(3, minmax(15rem, 20rem));
  gap: var(--space-6);
}

@media (max-width: 62rem) {
  .layers {
    grid-template-columns: minmax(15rem, 26rem);
  }
}

.layer {
  display: flex;
  flex-direction: column;
  padding: var(--space-5) var(--space-5) var(--space-4);
  background: var(--surface-raised);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  transition:
    border-color var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
}

.layer[data-hovering='true'] {
  border-color: var(--accent);
  box-shadow: var(--shadow-md);
}

.layer[data-state='loaded'] {
  border-color: var(--status-positive);
}

.layer[data-state='rejected'] {
  border-color: var(--status-negative);
}

.name {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.role {
  margin: var(--space-2) 0 var(--space-5);
  min-height: 3.5rem;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.target {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex: 1;
  min-height: 8rem;
  padding: var(--space-4);
  color: var(--text-muted);
  background: var(--surface-sunken);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
}

.target:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.plus {
  font-size: var(--text-lg);
  line-height: 1;
}

.invite {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.summary,
.rejected {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
  margin: 0;
  min-height: 8rem;
}

.check {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.tick {
  color: var(--status-positive);
}

.cross {
  color: var(--status-negative);
}

.file {
  flex: 1;
  overflow: hidden;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.counts {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto;
  gap: var(--space-1) var(--space-2);
  margin-top: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
}

.counts dt {
  color: var(--text-muted);
}

.counts dd {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-mono);
  text-align: right;
}

.plain,
.reason {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.replace {
  margin-top: auto;
  padding: var(--space-1) 0;
  color: var(--text-muted);
  background: none;
  border: none;
  font-size: var(--text-xs);
  text-align: left;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.replace:hover {
  color: var(--text-primary);
}

.picker {
  display: none;
}

.foot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.initialize {
  padding: var(--space-2) var(--space-8);
  color: var(--text-inverse);
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  letter-spacing: 0.04em;
  transition: background var(--duration-fast) var(--ease-out);
}

.initialize:hover:not(:disabled) {
  background: var(--accent-hover);
}

.initialize:disabled {
  color: var(--text-muted);
  background: var(--surface-raised);
  border-color: var(--border-subtle);
  cursor: default;
}

.progress {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.failure {
  margin: 0;
  color: var(--status-negative);
  font-size: var(--text-xs);
}
</style>
