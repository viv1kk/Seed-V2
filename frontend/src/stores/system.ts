import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { SystemEvent } from './events'

export type LifecycleState =
  | 'UNINITIALIZED'
  | 'INITIALIZED'
  | 'DISCOVERING'
  | 'DISCOVERY_BLOCKED'
  | 'DISCOVERY_COMPLETE'
  | 'ASSESSING'
  | 'AWAITING_APPROVAL'
  | 'IMPLEMENTING'
  | 'IMPLEMENTATION_COMPLETE'
  | 'READY_TO_RUN'
  | 'RUNNING'

export type Phase = 'INIT' | 'DISCOVERY' | 'ASSESSMENT' | 'IMPLEMENTATION' | 'RUNTIME'

export const PHASE_ORDER: Phase[] = [
  'INIT',
  'DISCOVERY',
  'ASSESSMENT',
  'IMPLEMENTATION',
  'RUNTIME',
]

export type RequestKind =
  | 'credentials'
  | 'ambiguity'
  | 'missing-info'
  | 'approval'
  | 'confirmation'

/** One legitimate answer to a request that is a choice rather than a form. */
export interface RequestOption {
  value: string
  label: string
  note: string | null
}

export interface BlockedOn {
  kind: RequestKind
  requestId: string
  /** What is needed (FR-H2). */
  prompt: string
  /** What access that requires (FR-H2). */
  access: string | null
  /** Why it is needed (FR-H2). The field that makes this answerable. */
  reason: string | null
  options: RequestOption[]
}

/** A request the system waited on, as System State records it (FR-H6). */
export interface HumanRequestRecord {
  requestId: string
  kind: RequestKind
  prompt: string
  status: 'pending' | 'resolved'
  /** Which fields were supplied. Never their values (FR-H5). */
  fields: string[]
  requestedAt: number
  resolvedAt: number | null
}

export type NodeKind = 'client' | 'system' | 'service' | 'api' | 'database' | 'dataset'

/** FR-D4. */
export type NodeStatus =
  | 'unknown'
  | 'detected'
  | 'testing'
  | 'validated'
  | 'requires-input'
  | 'connected'
  | 'error'

/** FR-D5. */
export type EdgeKind = 'contains' | 'connects_to' | 'provides' | 'depends_on'

export type Origin = 'declared' | 'discovered' | 'administrator-supplied'

export interface EnvironmentNode {
  id: string
  kind: NodeKind
  label: string
  detail: string | null
  system: string | null
  /** Hand-authored, in canvas units (D-4). */
  x: number
  y: number
  status: NodeStatus
  origin: Origin
  /** The rule that refused this node, when policy did. */
  excludedBy: string | null
}

export interface EnvironmentEdge {
  id: string
  source: string
  target: string
  kind: EdgeKind
  detail: string | null
}

export interface FieldProfile {
  name: string
  concept: string
  completeness: number
}

export interface DataSource {
  id: string
  label: string
  system: string | null
  source: string | null
  fields: FieldProfile[]
}

export interface DiscoverySummary {
  complete: boolean
  systems: number
  declaredSystems: number
  dataSources: number
  datasets: number
  profiled: number
  excluded: number
  bySystem: { id: string; label: string; status: NodeStatus; origin: Origin }[]
  methodologies: {
    id: string
    name: string
    required: number
    located: number
    missing: string[]
    appearsFeasible: boolean
  }[]
}

/** The constructed graph, as System State holds it. */
export interface Environment {
  client: string
  canvas: { width: number; height: number }
  nodes: EnvironmentNode[]
  edges: EnvironmentEdge[]
  dataSources: DataSource[]
  complete: boolean
  summary: DiscoverySummary | null
}

/** What an event carries when it changes the graph. */
interface EnvironmentDelta {
  client: string
  canvas: { width: number; height: number }
  nodes: EnvironmentNode[]
  edges: EnvironmentEdge[]
  dataSources: DataSource[]
  summary: DiscoverySummary | null
}

/** FR-A3. */
export type Grade = 'HIGH' | 'MEDIUM' | 'PARTIAL' | 'LOW'

export type Standing = 'sufficient' | 'limited' | 'incomplete' | 'missing'

export interface EvidenceField {
  dataset: string
  label: string
  system: string | null
  field: string
  completeness: number
}

export interface RequirementAssessment {
  concept: string
  description: string
  standing: Standing
  coverage: number | null
  weakest: EvidenceField | null
  fields: EvidenceField[]
}

export interface Improvement {
  concept: string
  action: string
  target: string
  from: Grade
  to: Grade
}

/** One methodology's assessment, with everything FR-A4 asks for. */
export interface Assessment {
  id: string
  methodologyId: string
  name: string
  purpose: string
  feasibility: Grade
  dataSufficiency: number
  coverage: { located: number; required: number }
  requirements: RequirementAssessment[]
  limitations: string[]
  declaredLimitations: string[]
  improvements: Improvement[]
  recommendation: string
  process: string[]
  /** FR-A10: these are simulated demo values, and say so. */
  simulated: boolean
}

/** FR-AP2. */
export type SolutionStatus =
  | 'PROPOSED'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'BUILDING'
  | 'READY'
  | 'RUNNING'

export interface Solution {
  id: string
  methodologyId: string
  assessmentId: string
  name: string
  description: string
  status: SolutionStatus
  dashboardId: string | null
}

/** A person's decision, with the evidence it was made on (FR-AP3). */
export interface Approval {
  id: string
  solutionId: string
  decision: 'APPROVED' | 'REJECTED'
  feasibility: Grade | null
  dataSufficiency: number | null
  rule: string
  decidedAt: number
}

/** FR-I2, in order. */
export type ComponentStatus = 'PENDING' | 'BUILDING' | 'TESTING' | 'VALIDATED' | 'COMPLETE'

export type Stage = 'ingestion' | 'normalization' | 'analysis' | 'api' | 'dashboard'

export interface BuildComponent {
  id: string
  stage: Stage
  name: string
  generated: string
  status: ComponentStatus
}

export type Suite = 'unit' | 'integration' | 'validation'

/** One named test, with its outcome and simulated timing (FR-I4). */
export interface TestCase {
  id: string
  suite: Suite
  /** The component it tests; null for a test of the whole pipeline. */
  component: string | null
  name: string
  note: string | null
  status: 'pending' | 'passed' | 'failed'
  durationMs: number
}

/** One solution's build, as System State holds it. */
export interface Implementation {
  id: string
  solutionId: string
  name: string
  status: 'PENDING' | 'BUILDING' | 'COMPLETE'
  approval: { id: string; rule: string; decidedAt: number } | null
  sources: { id: string; label: string }[]
  datasets: { id: string; label: string; system: string | null }[]
  components: BuildComponent[]
  tests: TestCase[]
  summary: { total: number; passed: number; failed: number; durationMs: number }
  simulated: boolean
}

export interface Run {
  id: string
  solutionId: string
  startedAt: number
  closedAt: number | null
}

/** Which solution is running, and every run so far (FR-L8). */
export interface Runtime {
  active: string | null
  runs: Run[]
}

/** One registered seed layer, as the Planting stage shows it (FR-S5). */
export interface RegisteredLayer {
  layer: string
  filename: string
  title: string | null
  sections: number
  topics: number
  headingCount: number
}

/** A layer as `seed.loaded` reports it; `headings` is the count. */
interface SeedLoadedLayer extends Omit<RegisteredLayer, 'headingCount'> {
  headings: number
}

export interface StateSnapshot {
  sequence: number
  lifecycle: LifecycleState
  phase: Phase
  blockedOn: BlockedOn | null
  humanRequests: HumanRequestRecord[]
  seed: Record<string, unknown> | null
  /** Empty until discovery begins. */
  environment: Environment | Record<string, never>
  assessments: Assessment[]
  solutions: Solution[]
  approvals: Approval[]
  implementations: Implementation[]
  runtime: Runtime | Record<string, never>
}

/**
 * Mirrors System State.
 *
 * The backend remains the sole source of truth (FR-L5). This store
 * holds a snapshot of it and folds subsequent events into that snapshot
 * (FR-E5), so what the screen shows is derived from the same stream the
 * audit log is built from rather than from a parallel model.
 *
 * `apply` is therefore a reducer that must stay in step with the
 * backend's own transitions. A resync is always available if it drifts,
 * which is why a gap is cheap to recover from (FR-E6).
 */
export const useSystemStore = defineStore('system', () => {
  const snapshot = ref<StateSnapshot | null>(null)
  const lifecycle = ref<LifecycleState>('UNINITIALIZED')
  const phase = ref<Phase>('INIT')
  const blockedOn = ref<BlockedOn | null>(null)

  /**
   * The environment graph, derived from the snapshot and then from the
   * deltas events carry. There is no model of it here beyond that fold:
   * what is drawn is what System State says was discovered (FR-L5).
   */
  const environment = ref<Environment | null>(null)

  /** Assessments, solutions and decisions, folded the same way (FR-L5). */
  const assessments = ref<Assessment[]>([])
  const solutions = ref<Solution[]>([])
  const approvals = ref<Approval[]>([])

  /** Builds and runs, folded the same way (FR-L5). */
  const implementations = ref<Implementation[]>([])
  const runtime = ref<Runtime>({ active: null, runs: [] })

  /** The registered seed, as the Planting stage summarises it (FR-S5). */
  const seed = ref<RegisteredLayer[]>([])

  /** The sequence number the snapshot is current as of. */
  const baseline = ref(0)

  function adopt(next: StateSnapshot): void {
    snapshot.value = next
    lifecycle.value = next.lifecycle
    phase.value = next.phase
    blockedOn.value = next.blockedOn
    baseline.value = next.sequence
    seed.value = ((next.seed?.layers ?? []) as RegisteredLayer[]).map((layer) => ({
      layer: layer.layer,
      filename: layer.filename,
      title: layer.title,
      sections: layer.sections,
      topics: layer.topics,
      headingCount: layer.headingCount,
    }))
    environment.value =
      'nodes' in next.environment ? structuredClone(next.environment as Environment) : null
    assessments.value = structuredClone(next.assessments)
    solutions.value = structuredClone(next.solutions)
    approvals.value = structuredClone(next.approvals)
    implementations.value = structuredClone(next.implementations)
    runtime.value =
      'runs' in next.runtime ? structuredClone(next.runtime as Runtime) : { active: null, runs: [] }
  }

  function upsert<T extends { id: string }>(records: T[], record: T): void {
    const index = records.findIndex((existing) => existing.id === record.id)
    if (index === -1) {
      records.push({ ...record })
    } else {
      records[index] = { ...records[index], ...record }
    }
  }

  /**
   * Fold one environment delta.
   *
   * Nodes and data sources arrive as full records and are upserted, so
   * folding one twice changes nothing and a late joiner converges on the
   * same graph as a client that watched throughout. The backend's
   * `test_discovery.py` replays the same fold against System State.
   */
  function foldEnvironment(delta: EnvironmentDelta): void {
    const target: Environment = environment.value ?? {
      client: delta.client,
      canvas: delta.canvas,
      nodes: [],
      edges: [],
      dataSources: [],
      complete: false,
      summary: null,
    }
    for (const node of delta.nodes) {
      upsert(target.nodes, node)
    }
    for (const source of delta.dataSources) {
      upsert(target.dataSources, source)
    }
    for (const edge of delta.edges) {
      if (!target.edges.some((existing) => existing.id === edge.id)) {
        target.edges.push({ ...edge })
      }
    }
    target.summary = delta.summary
    target.complete = delta.summary?.complete ?? false
    environment.value = target
  }

  async function fetchSnapshot(): Promise<void> {
    const response = await fetch('/api/state')
    if (!response.ok) {
      throw new Error(`Snapshot failed: ${response.status}`)
    }
    adopt((await response.json()) as StateSnapshot)
  }

  /**
   * Fold one event into local state.
   *
   * Only events after the snapshot's sequence number are applied.
   * Replayed events below it are already reflected in the snapshot, and
   * applying them again would move the system backwards.
   */
  function apply(event: SystemEvent): void {
    if (event.sequence <= baseline.value) {
      return
    }
    // Any event may carry a change to the graph, whatever its type.
    if (event.payload.environment) {
      foldEnvironment(event.payload.environment as EnvironmentDelta)
    }
    for (const record of (event.payload.assessments ?? []) as Assessment[]) {
      upsert(assessments.value, record)
    }
    for (const record of (event.payload.solutions ?? []) as Solution[]) {
      upsert(solutions.value, record)
    }
    for (const record of (event.payload.approvals ?? []) as Approval[]) {
      upsert(approvals.value, record)
    }
    for (const record of (event.payload.implementations ?? []) as Implementation[]) {
      upsert(implementations.value, record)
    }
    if (event.payload.runtime) {
      runtime.value = event.payload.runtime as Runtime
    }
    switch (event.type) {
      case 'seed.loaded':
        // The plant carries its own summary, so a client that planted, or
        // watched someone else plant, shows it without a reload (FR-E5).
        seed.value = (event.payload.layers as SeedLoadedLayer[]).map((layer) => ({
          layer: layer.layer,
          filename: layer.filename,
          title: layer.title,
          sections: layer.sections,
          topics: layer.topics,
          headingCount: layer.headings,
        }))
        break
      case 'lifecycle.transition':
        lifecycle.value = event.payload.to as LifecycleState
        phase.value = event.phase
        break
      case 'human.requested':
        // The whole request travels in the payload, so a client that
        // joined late rebuilds the surface without inferring it from the
        // message (FR-E5).
        blockedOn.value = event.payload.request as BlockedOn
        break
      case 'human.resolved':
        blockedOn.value = null
        break
    }
  }

  async function reset(): Promise<void> {
    const response = await fetch('/api/operator/reset', { method: 'POST' })
    if (!response.ok) {
      throw new Error(`Reset failed: ${response.status}`)
    }
    adopt((await response.json()) as StateSnapshot)
  }

  return {
    snapshot,
    seed,
    lifecycle,
    phase,
    blockedOn,
    environment,
    assessments,
    solutions,
    approvals,
    implementations,
    runtime,
    baseline,
    fetchSnapshot,
    apply,
    reset,
  }
})
