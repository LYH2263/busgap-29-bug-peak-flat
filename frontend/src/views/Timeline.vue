<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, axisKeepsAllMarks, noticeForFork } from '../viewHints'
const data = ref<{ stop_name: string; marks: any[]; peak_band?: any; peak_configured?: boolean }>({ stop_name: '', marks: [] })
onMounted(async () => { data.value = await api('/reports/timeline?line_id=1') })

function markColor(m: any) {
  // 未配高峰:与底座早期一致(前 15% 红、其余青);配了高峰:按本次 pair 真用的尺子着色
  if (!data.value.peak_configured) return m.pct < 15 ? 'var(--bg-red)' : 'var(--bg-cyan)'
  if (m.ruler === 'peak') return 'var(--bg-amber)'
  return 'var(--bg-cyan)'
}
function rulerText(m: any) {
  if (!data.value.peak_configured) return ''
  return m.ruler === 'peak' ? ' · 高峰尺' : ' · 平峰尺'
}
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布（顶部已展示发车间隔轴）· 琥珀色带为高峰窗，点色=与前一班对照时真用的尺子</p>
  <div class="card">
    <div class="tl-track">
      <div
        v-if="data.peak_band"
        class="tl-peak-band"
        :style="{ left: data.peak_band.start_pct + '%', width: (data.peak_band.end_pct - data.peak_band.start_pct) + '%' }"
      />
      <div v-for="m in data.marks" :key="m.trip_no" class="tl-mark"
        :style="{ left: m.pct + '%', background: markColor(m) }"
        :title="m.trip_no + ' ' + m.actual_arrive + rulerText(m)" />
    </div>
    <table>
      <thead><tr><th>班次</th><th>到站时间</th><th>相对位置</th><th>本次尺子</th></tr></thead>
      <tbody>
        <tr v-for="m in data.marks" :key="m.trip_no">
          <td>{{ m.trip_no }}</td><td>{{ m.actual_arrive }}</td><td>{{ m.pct }}%</td>
          <td>{{ data.peak_configured ? (m.ruler === 'peak' ? '高峰尺' : (m.ruler === 'offpeak' ? '平峰尺' : '—')) : '未配高峰' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
