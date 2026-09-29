<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, axisKeepsAllMarks, noticeForFork } from '../viewHints'
const tips = ref<any[]>([])
onMounted(async () => { tips.value = (await api('/reports/suggestions?line_id=1')).suggestions })
</script>
<template>
  <h1>建议</h1>
  <p class="sub">按本次实际尺子（双班均在高峰窗才用高峰计划，否则平峰计划）给出的调班提示</p>
  <div class="card" v-for="(t,i) in tips" :key="i">
    <div><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分</div>
    <p class="muted">{{ t.suggestion }}</p>
  </div>
  <p v-if="!tips.length" class="muted">暂无异常建议</p>
</template>
