<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, axisKeepsAllMarks, noticeForFork } from '../viewHints'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const loading = ref(false)
async function run() {
  loading.value = true
  try {
    events.value = (await api('/reports/run?line_id=1', { method: 'POST' })).events || []
  } finally { loading.value = false }
}
onMounted(async () => {
  trips.value = await api('/trips')
  await run()
})
function stripClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function label(s: string) {
  return unifyStatusLabel(s)
}
function rulerName(e: any) {
  // 与后端 suggestion 同源:本次真用哪把尺子就写哪个
  if (e.period === 'peak') return `高峰计划 ${e.planned_headway_min}′`
  if (e.period === 'offpeak') return `平峰计划 ${e.planned_headway_min}′`
  return `计划 ${e.planned_headway_min}′`
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">按实际到站间隔对照计划发车间隔 · 竖直条带展示</p>
  <button class="btn" :disabled="loading" @click="run">重新检测</button>
  <div class="bg-split" style="margin-top:1rem">
    <aside class="bg-trip-col">
      <h2>关联班次</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">{{ r.vehicle_no }}</div>
        </div>
        <div class="bg-trip-meta">{{ r.planned_depart }}</div>
      </div>
    </aside>
    <div class="bg-strip-col">
      <article
        v-for="(e, i) in events"
        :key="i"
        class="bg-gap-strip"
        :class="stripClass(e.status)"
      >
        <header>{{ e.stop_name }}</header>
        <div class="bg-gap-body">
          <div class="bg-gap-val">{{ e.gap_min }}′</div>
          <div>{{ rulerName(e) }}</div>
          <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
          <span class="badge" :class="e.status === 'bunching' ? 'badge-bad' : e.status === 'large_gap' ? 'badge-warn' : 'badge-ok'">
            {{ label(e.status) }}
          </span>
        </div>
      </article>
    </div>
  </div>
</template>
