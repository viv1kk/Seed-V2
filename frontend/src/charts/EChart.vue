<script setup lang="ts">
import { BarChart, LineChart, TreemapChart } from 'echarts/charts'
import {
  BrushComponent,
  GridComponent,
  ToolboxComponent,
  TooltipComponent,
} from 'echarts/components'
import { init, use, type EChartsCoreOption, type EChartsType } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

use([
  BarChart,
  LineChart,
  TreemapChart,
  BrushComponent,
  GridComponent,
  ToolboxComponent,
  TooltipComponent,
  CanvasRenderer,
])

const props = defineProps<{
  option: EChartsCoreOption
  height: number
  /** Keep the brush cursor armed, so a drag selects a range. */
  brush?: boolean
}>()

const emit = defineEmits<{
  /** A click on a datum or an axis label. */
  select: [params: Record<string, unknown>, chart: EChartsType]
  /** A click anywhere in the plot, in pixels. */
  plot: [point: [number, number], chart: EChartsType]
  /** A completed brush, as axis index range. */
  range: [from: number, to: number, chart: EChartsType]
}>()

/**
 * The one ECharts wrapper (NFR-L2). It draws an option and reports what
 * was clicked; what a click means is decided by the card that owns it,
 * from what the backend said each datum filters to.
 */
const host = ref<HTMLDivElement | null>(null)
let chart: EChartsType | null = null
let observer: ResizeObserver | null = null

function arm(): void {
  if (chart && props.brush) {
    chart.dispatchAction({
      type: 'takeGlobalCursor',
      key: 'brush',
      brushOption: { brushType: 'lineX', brushMode: 'single' },
    })
  }
}

function draw(): void {
  if (!chart) return
  chart.setOption(props.option, { notMerge: true })
  arm()
}

onMounted(() => {
  if (!host.value) return
  chart = init(host.value, undefined, { renderer: 'canvas' })
  chart.on('click', (params) => emit('select', params as unknown as Record<string, unknown>, chart!))
  chart.getZr().on('click', (event) => {
    if (!event.target || props.brush) emit('plot', [event.offsetX, event.offsetY], chart!)
  })
  chart.on('brushEnd', (params) => {
    const areas = (params as { areas?: { coordRange?: [number, number] }[] }).areas ?? []
    const range = areas[0]?.coordRange
    if (range) {
      emit('range', Math.round(range[0]), Math.round(range[1]), chart!)
      chart!.dispatchAction({ type: 'brush', areas: [] })
    }
  })
  draw()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(host.value)
})

watch(() => props.option, draw)
watch(
  () => props.height,
  () => chart?.resize(),
)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="host" class="chart" :style="{ height: `${height}px` }" />
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>
