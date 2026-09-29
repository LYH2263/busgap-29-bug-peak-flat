<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, axisKeepsAllMarks, noticeForFork } from '../viewHints'
const tips = ref<any[]>([])
onMounted(async () => { tips.value = (await api('/reports/suggestions?line_id=1')).suggestions })
</script>
<template>
  <h1>建议</h1>
  <p class="sub">串车 / 大间隔调班提示 · 双班都落在高峰窗才按高峰尺，否则按平峰尺</p>
  <div class="card" v-for="(t,i) in tips" :key="i">
    <div><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分</div>
    <p class="muted">{{ t.suggestion }}</p>
  </div>
  <p v-if="!tips.length" class="muted">暂无异常建议</p>
</template>
