<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const rows = ref<any[]>([])
const edits = reactive<Record<number, { start: string; end: string; headway: string }>>({})
const msgs = reactive<Record<number, string>>({})

function minToHm(m: number | null): string {
  if (m == null) return ''
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
}
function hmToMin(s: string): number | null {
  if (!s) return null
  const [h, m] = s.split(':').map(Number)
  return h * 60 + m
}
async function load() {
  rows.value = await api('/lines')
  for (const r of rows.value) {
    edits[r.id] = {
      start: minToHm(r.peak_start_min),
      end: minToHm(r.peak_end_min),
      headway: r.peak_headway_min == null ? '' : String(r.peak_headway_min),
    }
  }
}
onMounted(load)

async function save(r: any) {
  const e = edits[r.id]
  const start = hmToMin(e.start)
  const end = hmToMin(e.end)
  const headway = e.headway === '' ? null : Number(e.headway)
  const filled = [start, end, headway].filter(v => v != null).length
  if (filled !== 0 && filled !== 3) { msgs[r.id] = '高峰起止与间隔需同时填写或同时留空'; return }
  if (filled === 3 && !(start! < end!)) { msgs[r.id] = '高峰开始需早于结束'; return }
  if (filled === 3 && !(headway! > 0)) { msgs[r.id] = '高峰间隔需大于 0'; return }
  try {
    await api(`/lines/${r.id}`, {
      method: 'PUT',
      body: JSON.stringify({ peak_start_min: start, peak_end_min: end, peak_headway_min: headway }),
    })
    msgs[r.id] = filled === 3 ? '已保存高峰配置' : '已清除高峰配置'
    await load()
  } catch (err: any) {
    let m = err.message || '保存失败'
    try { m = JSON.parse(m).detail || m } catch { /* 非 JSON 错误 */ }
    msgs[r.id] = m
  }
}
function clearPeak(r: any) {
  edits[r.id] = { start: '', end: '', headway: '' }
  save(r)
}
</script>
<template>
  <h1>线路</h1>
  <p class="sub">运营线路与串车 / 大间隔判定阈值 · 可登记高峰时段与高峰计划间隔</p>
  <p class="muted">业务页与检测读口未强制同参与集</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>计划间隔(分)</th><th>串车阈值</th><th>大间隔阈值</th><th>高峰起</th><th>高峰止</th><th>高峰间隔(分)</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.planned_headway_min }}</td><td>{{ r.bunch_threshold }}</td><td>{{ r.large_threshold }}</td>
          <td><input type="time" v-model="edits[r.id].start"></td>
          <td><input type="time" v-model="edits[r.id].end"></td>
          <td><input class="cell-num" type="number" min="0" step="0.5" v-model="edits[r.id].headway" placeholder="未配置"></td>
          <td>
            <div class="peak-edit">
              <div>
                <button class="btn" @click="save(r)">保存</button>
                <button class="btn btn-ghost" @click="clearPeak(r)">清除</button>
              </div>
              <div class="peak-msg muted">{{ msgs[r.id] }}</div>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
