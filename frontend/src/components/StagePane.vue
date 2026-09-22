<script setup lang="ts">
import { computed } from 'vue'

import EnvironmentStage from './EnvironmentStage.vue'
import type { LayerSummary } from '../stores/seed'
import { useSystemStore, type Phase } from '../stores/system'

const system = useSystemStore()

/**
 * What each phase puts on the stage.
 *
 * The pane changes; the workspace around it does not (NFR-A3, §13). Init
 * shows what the seed loader actually registered, and Discovery the
 * environment graph as System State holds it. The other three state what
 * belongs there, and the milestone that builds each one replaces the
 * corresponding branch rather than the layout.
 */
type Pending = Exclude<Phase, 'INIT' | 'DISCOVERY'>

const PENDING: Record<Pending, { title: string; note: string }> = {
  ASSESSMENT: {
    title: 'Assessment',
    note: 'Each methodology is shown against the evidence discovery found, with its feasibility and the limitations behind it.',
  },
  IMPLEMENTATION: {
    title: 'Build',
    note: 'The build pipeline is shown here, with each stage progressing through pending, building, testing and complete.',
  },
  RUNTIME: {
    title: 'Runtime',
    note: 'The delivered solutions run here, as interactive dashboards over the analytical datasets.',
  },
}

const layers = computed<LayerSummary[]>(
  () => (system.snapshot?.seed?.layers as LayerSummary[] | undefined) ?? [],
)

const pending = computed(() =>
  system.phase === 'INIT' || system.phase === 'DISCOVERY'
    ? null
    : PENDING[system.phase as Pending],
)
</script>

<template>
  <section class="stage">
    <!-- Init: the registered seed, summarised from the files that were
         actually supplied (FR-S5). It stays visible while the system is
         initialized and idle, so the screen after planting is not empty. -->
    <!-- Discovery: the environment, growing as it is found (FR-D3). -->
    <EnvironmentStage v-if="system.phase === 'DISCOVERY'" :environment="system.environment" />

    <template v-else-if="!pending">
      <header class="head">
        <h2 class="title">Seed</h2>
        <p class="note">
          Three layers registered. Content is fixed at initialization and does not
          change during a run.
        </p>
      </header>

      <ul v-if="layers.length > 0" class="layers">
        <li v-for="layer in layers" :key="layer.layer" class="layer">
          <div class="layer-head">
            <span class="layer-name">{{ layer.layer }}</span>
            <span class="layer-file">{{ layer.filename }}</span>
          </div>
          <p class="layer-title">{{ layer.title ?? 'no title' }}</p>
          <dl class="layer-counts">
            <dt>Sections</dt>
            <dd>{{ layer.sections }}</dd>
            <dt>Topics</dt>
            <dd>{{ layer.topics }}</dd>
            <dt>Headings</dt>
            <dd>{{ layer.headingCount }}</dd>
          </dl>
        </li>
      </ul>
    </template>

    <!-- Every other phase, until the milestone that fills it. -->
    <template v-else>
      <header class="head">
        <h2 class="title">{{ pending.title }}</h2>
        <p class="note">{{ pending.note }}</p>
      </header>
    </template>
  </section>
</template>

<style scoped>
.stage {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-height: 0;
  height: 100%;
  padding: var(--space-6) var(--space-8);
  overflow-y: auto;
}

.head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.note {
  margin: 0;
  max-width: 62ch;
  color: var(--text-muted);
  font-size: var(--text-xs);
  line-height: 1.6;
}

.layers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: var(--space-4);
  margin: 0;
  padding: 0;
  list-style: none;
}

.layer {
  padding: var(--space-4);
  background: var(--surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}

.layer-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.layer-name {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.layer-file {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.layer-title {
  margin: var(--space-2) 0 var(--space-3);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.layer-counts {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--space-1) var(--space-3);
  margin: 0;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
}

.layer-counts dt {
  color: var(--text-muted);
}

.layer-counts dd {
  margin: 0;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  text-align: right;
}
</style>
