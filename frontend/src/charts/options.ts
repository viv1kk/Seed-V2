import type { EChartsCoreOption } from 'echarts/core'

import { formatTick, formatValue, type Format } from '../design/format'
import type {
  ChartSpec,
  MeasureSpec,
  Role,
  SeriesChartResult,
  TreeNode,
  TreemapResult,
} from '../stores/dashboard'

/**
 * Chart options, built from what the backend returned.
 *
 * Colours are semantic roles resolved against the design tokens at paint
 * time (D-5), so a chart carries no palette of its own and follows the
 * theme. The builders place figures; they compute none. Every value
 * drawn here is one the query engine sent (FR-AN5).
 */

export interface Tokens {
  role: (role: Role | null | undefined) => string
  text: string
  secondary: string
  muted: string
  inverse: string
  grid: string
  border: string
  surface: string
  sunken: string
  overlay: string
  accent: string
  brush: string
  sans: string
  mono: string
}

/** Read the tokens as they stand in the active theme. */
export function readTokens(): Tokens {
  const style = getComputedStyle(document.documentElement)
  const get = (name: string) => style.getPropertyValue(name).trim()
  return {
    role: (role) => get(`--chart-${role ?? 'muted'}`),
    text: get('--text-primary'),
    secondary: get('--text-secondary'),
    muted: get('--text-muted'),
    inverse: get('--text-inverse'),
    grid: get('--chart-grid'),
    border: get('--border-default'),
    surface: get('--surface-raised'),
    sunken: get('--surface-sunken'),
    overlay: get('--surface-overlay'),
    accent: get('--accent'),
    brush: get('--chart-brush'),
    sans: get('--font-sans'),
    mono: get('--font-mono'),
  }
}

/** Text that reads on a filled role: light fills take dark text. */
function onFill(role: Role | null, tokens: Tokens): string {
  return role === 'muted' || role === 'baseline' || role === null ? tokens.text : tokens.inverse
}

function base(tokens: Tokens, motion: boolean): EChartsCoreOption {
  return {
    animation: motion,
    animationDuration: 350,
    textStyle: { fontFamily: tokens.sans, color: tokens.secondary, fontSize: 11 },
    tooltip: {
      backgroundColor: tokens.overlay,
      borderColor: tokens.border,
      borderWidth: 1,
      padding: [6, 10],
      textStyle: { color: tokens.text, fontSize: 12, fontFamily: tokens.sans },
      extraCssText: 'box-shadow: none; border-radius: 4px;',
      confine: true,
    },
  }
}

function axisStyle(tokens: Tokens) {
  return {
    axisLine: { lineStyle: { color: tokens.grid } },
    axisTick: { show: false },
    axisLabel: { color: tokens.muted, fontSize: 11 },
    splitLine: { lineStyle: { color: tokens.grid } },
  }
}

/** Line and bar charts share their data shape. */
export function seriesOption(
  chart: ChartSpec,
  result: SeriesChartResult,
  formats: Format[],
  tokens: Tokens,
  motion: boolean,
  withheldLabel: (count: number) => string,
): EChartsCoreOption {
  const horizontal = chart.mark === 'bar' && chart.orientation === 'horizontal'
  const labels = result.categories.map((c) => c.label)
  const secondary = result.series.some((s) => s.axis === 'secondary')
  const primaryFormat = formats[result.series.findIndex((s) => s.axis !== 'secondary')] ?? 'integer'
  const secondaryFormat = formats[result.series.findIndex((s) => s.axis === 'secondary')] ?? 'integer'

  const category = {
    type: 'category',
    data: labels,
    boundaryGap: chart.mark === 'bar',
    inverse: horizontal,
    triggerEvent: chart.interaction.click !== 'none',
    ...axisStyle(tokens),
    splitLine: { show: false },
    axisLabel: {
      color: tokens.muted,
      fontSize: 11,
      width: horizontal ? 150 : undefined,
      overflow: 'truncate',
      interval: horizontal ? 0 : 'auto',
    },
  }
  const value = (format: Format, index = 0) => ({
    type: 'value',
    ...axisStyle(tokens),
    splitLine: { show: index === 0, lineStyle: { color: tokens.grid } },
    axisLabel: {
      color: tokens.muted,
      fontSize: 11,
      formatter: (v: number) => formatTick(v, format),
    },
  })

  const series = result.series.map((s, index) => {
    const colour = tokens.role(s.role)
    const format = formats[index] ?? 'integer'
    if (chart.mark === 'line') {
      return {
        type: 'line',
        name: s.label,
        data: s.values,
        yAxisIndex: s.axis === 'secondary' ? 1 : 0,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: labels.length <= 24,
        lineStyle: { width: 2, color: colour },
        itemStyle: { color: colour },
        areaStyle: chart.series ? undefined : { color: colour, opacity: 0.07 },
        emphasis: { focus: 'series' },
        connectNulls: false,
        tooltip: { valueFormatter: (v: number) => formatValue(v, format) },
      }
    }
    return {
      type: 'bar',
      name: s.label,
      stack: chart.stacked ? 'total' : undefined,
      barMaxWidth: 26,
      barGap: '12%',
      itemStyle: { color: colour, borderRadius: chart.stacked ? 0 : 2 },
      emphasis: { focus: 'series' },
      tooltip: { valueFormatter: (v: number) => formatValue(v, format) },
      data: s.values.map((v, j) => {
        const withheld = result.withheld?.[j] ?? 0
        if (v === null && withheld > 0) {
          return {
            value: 0,
            itemStyle: { color: 'transparent' },
            label: {
              show: true,
              position: horizontal ? 'right' : 'top',
              color: tokens.muted,
              fontStyle: 'italic',
              formatter: withheldLabel(withheld),
            },
          }
        }
        const role = result.roles?.[j]
        return role ? { value: v, itemStyle: { color: tokens.role(role) } } : v
      }),
    }
  })

  const axes = secondary
    ? [value(primaryFormat, 0), value(secondaryFormat, 1)]
    : [value(primaryFormat, 0)]

  return {
    ...base(tokens, motion),
    grid: { left: 8, right: secondary ? 8 : 16, top: 14, bottom: 4, containLabel: true },
    tooltip: {
      ...(base(tokens, motion).tooltip as object),
      trigger: chart.mark === 'line' ? 'axis' : 'item',
      axisPointer: { type: chart.mark === 'line' ? 'line' : 'shadow', lineStyle: { color: tokens.border } },
    },
    xAxis: horizontal ? axes : category,
    yAxis: horizontal ? category : axes,
    series,
    brush: chart.interaction.brush
      ? {
          xAxisIndex: 0,
          brushType: 'lineX',
          brushMode: 'single',
          transformable: false,
          throttleType: 'debounce',
          throttleDelay: 250,
          brushStyle: { color: tokens.brush, borderColor: tokens.accent, borderWidth: 1 },
          outOfBrush: { colorAlpha: 0.35 },
        }
      : undefined,
    toolbox: chart.interaction.brush ? { show: false, feature: { brush: {} } } : undefined,
  }
}

/** Nested rectangles, each coloured by the role the backend resolved. */
export function treemapOption(
  chart: ChartSpec,
  result: TreemapResult,
  measure: MeasureSpec,
  tokens: Tokens,
  motion: boolean,
): EChartsCoreOption {
  const format = measure.format
  const node = (n: TreeNode, inherited: Role | null): Record<string, unknown> => {
    const role = n.role ?? inherited
    const leaf = n.children.length === 0
    return {
      name: n.label,
      value: n.value,
      filter: n.filter,
      key: n.key,
      itemStyle: {
        color: role ? tokens.role(role) : tokens.sunken,
        borderColor: leaf ? tokens.surface : role ? tokens.role(role) : tokens.sunken,
      },
      label: { color: onFill(role, tokens) },
      upperLabel: { color: role ? onFill(role, tokens) : tokens.secondary },
      children: n.children.length ? n.children.map((c) => node(c, n.role)) : undefined,
    }
  }
  return {
    ...base(tokens, motion),
    tooltip: {
      ...(base(tokens, motion).tooltip as object),
      formatter: (info: { treePathInfo: { name: string }[]; value: number }) => {
        const path = info.treePathInfo.slice(1).map((p) => p.name).join(' › ')
        return `${path}<br/><b>${formatValue(info.value, format)}</b> ${measure.label.toLowerCase()}`
      },
    },
    series: [
      {
        type: 'treemap',
        data: result.nodes.map((n) => node(n, null)),
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        squareRatio: 0.9,
        label: {
          show: true,
          fontSize: 11,
          overflow: 'truncate',
          formatter: (info: { name: string; value: number }) =>
            `${info.name}\n${formatValue(info.value, format)}`,
        },
        upperLabel: {
          show: true,
          height: 18,
          fontSize: 11,
          fontWeight: 600,
          formatter: (info: { name: string; value: number }) =>
            `${info.name}  ${formatValue(info.value, format)}`,
        },
        // Level 0 is the invisible root that holds the top-level nodes.
        levels: [
          { itemStyle: { borderWidth: 0, gapWidth: 3 }, upperLabel: { show: false } },
          { itemStyle: { borderWidth: 2, gapWidth: 2 } },
          { itemStyle: { borderWidth: 2, gapWidth: 1 } },
          { itemStyle: { borderWidth: 1, gapWidth: 1 } },
        ],
        emphasis: { itemStyle: { borderColor: tokens.text } },
      },
    ],
  }
}
