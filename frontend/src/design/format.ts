/**
 * How a figure reads, by its declared format.
 *
 * Which format applies is a fact about the figure, declared in the
 * dashboard descriptor; how that format looks is presentation, and lives
 * here, once, for every dashboard. Nothing here computes a figure: the
 * backend sends the numbers and this only writes them down (FR-AN5).
 */

export type Format =
  | 'integer'
  | 'decimal'
  | 'percent'
  | 'hours'
  | 'days'
  | 'currency'
  | 'score'
  | 'lift'
  | 'text'
  | 'date'
  | 'datetime'

const whole = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function decimal(value: number): string {
  const size = Math.abs(value)
  const digits = size >= 100 ? 0 : size >= 10 ? 1 : 2
  return new Intl.NumberFormat('en-GB', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value)
}

function money(value: number): string {
  const size = Math.abs(value)
  if (size >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
  if (size >= 10_000) return `$${(value / 1000).toFixed(0)}k`
  if (size >= 1000) return `$${(value / 1000).toFixed(1)}k`
  return `$${value.toFixed(0)}`
}

/**
 * A deviation, stored as observed over baseline minus one. Within a few
 * times the baseline it reads as a percentage, as §35 writes it; beyond
 * that a percentage stops meaning anything and it reads as a multiple.
 */
function lift(value: number): string {
  if (value >= 5) return `${(value + 1).toFixed(1)}×`
  const sign = value >= 0 ? '+' : '−'
  return `${sign}${Math.abs(value * 100).toFixed(0)}%`
}

function date(value: string, withTime: boolean): string {
  const stamp = new Date(value)
  if (Number.isNaN(stamp.getTime())) return value
  const day = `${stamp.getDate()} ${MONTHS[stamp.getMonth()]} ${stamp.getFullYear()}`
  if (!withTime) return day
  const hh = String(stamp.getHours()).padStart(2, '0')
  const mm = String(stamp.getMinutes()).padStart(2, '0')
  return `${day} ${hh}:${mm}`
}

export function formatValue(value: unknown, format: Format): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value !== 'number') {
    if (format === 'date' || format === 'datetime') return date(String(value), format === 'datetime')
    return String(value)
  }
  switch (format) {
    case 'integer':
      return whole.format(value)
    case 'percent':
      return `${(value * 100).toFixed(value < 0.1 && value > 0 ? 2 : 1)}%`
    case 'hours':
      // Always hours, so figures beside each other compare directly.
      return value >= 10_000 ? `${decimal(value / 1000)}k h` : `${whole.format(Math.round(value * 10) / 10)} h`
    case 'days':
      return `${whole.format(value)} d`
    case 'currency':
      return money(value)
    case 'score':
      return value.toFixed(2)
    case 'lift':
      return lift(value)
    case 'decimal':
      return decimal(value)
    default:
      return String(value)
  }
}

/** Shorter, for axis ticks. */
export function formatTick(value: number, format: Format): string {
  if (format === 'percent') return `${Math.round(value * 100)}%`
  if (format === 'currency') return money(value)
  if (format === 'hours') return `${decimal(value)} h`
  if (Math.abs(value) >= 1000) return `${decimal(value / 1000)}k`
  return decimal(value)
}
