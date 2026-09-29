<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, axisKeepsAllMarks, noticeForFork } from '../viewHints'
const data = ref<{
  stop_name: string
  marks: any[]
  peak_band: { left_pct: number; width_pct: number } | null
  peak_headway_min: number | null
  planned_headway_min: number | null
}>({ stop_name: '', marks: [], peak_band: null, peak_headway_min: null, planned_headway_min: null })
onMounted(async () => { data.value = await api('/reports/timeline?line_id=1') })
// 与班对选尺同源: ruler 为该班与上一班这一对真正使用的尺子
function rulerText(m: any): string {
  if (m.ruler === 'peak') return `高峰计划 ${data.value.peak_headway_min}′`
  if (m.ruler === 'offpeak') return `平峰计划 ${data.value.planned_headway_min}′`
  return data.value.planned_headway_min == null ? '—' : `计划 ${data.value.planned_headway_min}′`
}
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布 · 琥珀色带为高峰窗；点的颜色只表示该班是否在窗内，对尺以班对为准</p>
  <div class="card">
    <div class="tl-track">
      <div v-if="data.peak_band" class="tl-peak-band"
           :style="{ left: data.peak_band.left_pct + '%', width: data.peak_band.width_pct + '%' }"
           title="高峰窗" />
      <div v-for="m in data.marks" :key="m.trip_no" class="tl-mark"
        :style="{ left: m.pct + '%', background: m.in_peak ? 'var(--bg-amber)' : (m.pct < 15 ? 'var(--bg-red)' : 'var(--bg-cyan)') }"
        :title="m.trip_no + ' ' + m.actual_arrive + (m.ruler === 'peak' ? ' · 对尺:高峰计划' : m.ruler === 'offpeak' ? ' · 对尺:平峰计划' : '')" />
    </div>
    <table>
      <thead><tr><th>班次</th><th>到站时间</th><th>相对位置</th><th>与上班对尺</th></tr></thead>
      <tbody>
        <tr v-for="m in data.marks" :key="m.trip_no">
          <td>{{ m.trip_no }}</td><td>{{ m.actual_arrive }}</td><td>{{ m.pct }}%</td>
          <td>{{ m.ruler == null ? '—（首班）' : rulerText(m) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
