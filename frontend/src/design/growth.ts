import type { SystemEvent } from '../stores/events'
import { PHASE_ORDER, type Phase } from '../stores/system'

/**
 * The growth tree, as a pure function of the event log (D-15, FR-G5).
 *
 * Nothing here reads System State or the clock. Every root, leaf, branch
 * and watering step is one event, placed by its order in the log, so the
 * same log always grows the same tree: replaying it after a reload
 * rebuilds exactly what grew live (FR-E7), and two runs from Reset end
 * with the same tree (NFR-D4). Geometry lives in the component; this
 * only says what has grown.
 */

/** One grown element, remembered with the event that grew it. */
export interface Grown {
  sequence: number
  label: string
}

export interface Branch extends Grown {
  id: string
  leaves: Grown[]
  /** The built Agent Component is ready: the branch ends in a bud. */
  ready: boolean
}

/** One capability request the protection engine evaluated (FR-G3). */
export interface Watering {
  sequence: number
  effect: 'ALLOW' | 'DENY' | 'ESCALATE'
  rule: string
  label: string
}

export interface Growth {
  /** The phase of the latest event: where the tree is now. */
  phase: Phase | null
  /** Waiting on a person: the last human event is a request. */
  blocked: boolean
  /** The seed's three layers, planted (FR-S5). */
  roots: Grown[]
  /** The system is ready to discover: the seed has sprouted. */
  sprouted: boolean
  /** One leaf per system Discovery reached or registered. */
  systems: Grown[]
  /** One leaf per methodology assessed. */
  assessments: Grown[]
  /** One branch per Agent Component built, a leaf per built part. */
  branches: Branch[]
  /** Agent One VW is ready to run: the tree flowers. */
  bloom: Grown | null
  waterings: Watering[]
}

function payloadOf<T>(event: SystemEvent, key: string): T | undefined {
  return event.payload[key] as T | undefined
}

function firstId(event: SystemEvent, key: 'implementations' | 'solutions'): string | null {
  const records = payloadOf<{ id: string; name?: string }[]>(event, key) ?? []
  return records[0]?.id ?? null
}

export function growthOf(events: readonly SystemEvent[]): Growth {
  const growth: Growth = {
    phase: null,
    blocked: false,
    roots: [],
    sprouted: false,
    systems: [],
    assessments: [],
    branches: [],
    bloom: null,
    waterings: [],
  }

  for (const event of events) {
    growth.phase = event.phase
    switch (event.type) {
      case 'seed.loaded':
        growth.roots = (payloadOf<{ title: string | null; layer: string }[]>(event, 'layers') ?? [])
          .map((layer) => ({ sequence: event.sequence, label: layer.title ?? layer.layer }))
        break
      case 'system.ready':
        growth.sprouted = true
        break
      case 'discovery.system.connected':
      case 'discovery.system.registered':
        growth.systems.push({
          sequence: event.sequence,
          label: payloadOf<string>(event, 'system') ?? 'System',
        })
        break
      case 'assessment.methodology.evaluated':
        growth.assessments.push({
          sequence: event.sequence,
          label: payloadOf<string>(event, 'methodology') ?? 'Methodology',
        })
        break
      case 'implementation.build.started': {
        const solutions = payloadOf<{ id: string; name: string }[]>(event, 'solutions') ?? []
        const building = solutions[0]
        if (building && !growth.branches.some((b) => b.id === building.id)) {
          growth.branches.push({
            id: building.id,
            sequence: event.sequence,
            label: building.name,
            leaves: [],
            ready: false,
          })
        }
        break
      }
      case 'implementation.component.built': {
        const id = firstId(event, 'implementations')
        growth.branches
          .find((b) => b.id === id)
          ?.leaves.push({ sequence: event.sequence, label: event.message })
        break
      }
      case 'solution.ready': {
        const id = firstId(event, 'solutions')
        const branch = growth.branches.find((b) => b.id === id)
        if (branch) branch.ready = true
        break
      }
      case 'deployment.ready':
        growth.bloom = { sequence: event.sequence, label: 'Agent One VW' }
        break
      case 'policy.decision':
        growth.waterings.push({
          sequence: event.sequence,
          effect: payloadOf<Watering['effect']>(event, 'effect') ?? 'ALLOW',
          rule: payloadOf<string>(event, 'rule') ?? '',
          label: `${payloadOf<string>(event, 'action') ?? 'Request'}: ${payloadOf<string>(event, 'resource') ?? ''}`,
        })
        break
      case 'human.requested':
        growth.blocked = true
        break
      case 'human.resolved':
        growth.blocked = false
        break
    }
  }
  return growth
}

/** Where each phase stands, the information the strip used to carry (FR-G1). */
export function phaseStateOf(
  phase: Phase,
  current: Phase | null,
): 'complete' | 'current' | 'future' {
  if (current === null) return phase === 'INIT' ? 'current' : 'future'
  const index = PHASE_ORDER.indexOf(phase)
  const at = PHASE_ORDER.indexOf(current)
  if (index < at) return 'complete'
  if (index === at) return 'current'
  return 'future'
}

/**
 * A stable fingerprint of what has grown, for comparing a tree grown live
 * with one rebuilt from a replay (FR-G5). Sequence numbers are included:
 * the same shape grown from different events is not the same tree.
 */
export function fingerprintOf(growth: Growth): string {
  return JSON.stringify(growth)
}
