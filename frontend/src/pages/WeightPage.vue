<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { X } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

const API = '/api/weight'

interface TrendPoint { date: string; weight: number; bmi: number | null; smoothed: number | null }
interface WeightRecord { id: number; weight_kg: number; bmi: number | null; body_fat_pct: number | null; note: string | null; recorded_at: string }

const trendPoints = ref<TrendPoint[]>([])
const records = ref<WeightRecord[]>([])
const loading = ref(true)
const timeRange = ref(30)
const newWeight = ref('')
const newNote = ref('')
const newRecordedAt = ref('')
const submitting = ref(false)
const targetWeight = ref(65)
const heightCm = ref(170)

onMounted(async () => {
  newRecordedAt.value = getLocalDateTimeValue()
  await Promise.all([fetchTrend(), fetchRecords()])
  try {
    const s = await (await fetch('/api/settings/')).json()
    targetWeight.value = s.target_weight_kg
    heightCm.value = s.height_cm
  } catch {}
  loading.value = false
})

function getLocalDateTimeValue(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60 * 1000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

async function fetchTrend() {
  const res = await fetch(`${API}/trend?days=${timeRange.value}`)
  trendPoints.value = await res.json()
}

async function fetchRecords() {
  const res = await fetch(`${API}/?days=${timeRange.value}`)
  records.value = await res.json()
}

async function submitWeight() {
  const w = Math.round(parseFloat(newWeight.value) * 100) / 100
  if (!w || w < 20 || w > 300) return
  submitting.value = true
  await fetch(API + '/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      weight_kg: w,
      note: newNote.value || null,
      recorded_at: newRecordedAt.value ? new Date(newRecordedAt.value).toISOString() : null,
    }),
  })
  newRecordedAt.value = getLocalDateTimeValue()
  await Promise.all([fetchTrend(), fetchRecords()])
  submitting.value = false
}

async function deleteRecord(id: number) {
  await fetch(`${API}/${id}`, { method: 'DELETE' })
  await Promise.all([fetchTrend(), fetchRecords()])
}

function changeRange(days: number) { timeRange.value = days; Promise.all([fetchTrend(), fetchRecords()]) }

const bmiNormal = computed(() => {
  const h = heightCm.value / 100
  return { low: +(18.5 * h * h).toFixed(1), high: +(24 * h * h).toFixed(1) }
})

function readCssColor(name: string, fallback: string) {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

const chartOption = computed(() => {
  const primary = readCssColor('--color-primary', '#0f8f83')
  const accent = readCssColor('--color-accent', '#3b82f6')
  const muted = readCssColor('--color-text-muted', '#667985')
  const border = readCssColor('--color-border-light', 'rgba(15, 23, 42, 0.08)')
  const success = readCssColor('--color-success', '#10b981')
  const markLine: any = {
    silent: true, symbol: 'none',
    lineStyle: { type: 'dashed', width: 2 },
    data: [
      { yAxis: targetWeight.value, lineStyle: { color: success }, label: { formatter: `目标 ${targetWeight.value}kg`, color: success, fontSize: 12 } },
    ],
  }

  return {
    grid: { top: 40, right: 30, bottom: 24, left: 56 },
    xAxis: {
      type: 'category',
      data: trendPoints.value.map(p => p.date.slice(5)),
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 11 },
    },
    yAxis: {
      type: 'value', scale: true,
      axisLine: { show: false }, axisTick: { show: false },
      splitLine: { lineStyle: { color: border } },
      axisLabel: { color: muted, fontSize: 11 },
      name: 'kg',
      nameTextStyle: { color: muted, fontSize: 11 },
    },
    tooltip: { trigger: 'axis' },
    series: [
      {
        name: '体重', type: 'line',
        data: trendPoints.value.map(p => p.weight),
        smooth: true, symbol: 'circle', symbolSize: 6,
        lineStyle: { color: primary, width: 2.5 },
        itemStyle: { color: primary },
        emphasis: { lineStyle: { color: primary, width: 2.5 }, itemStyle: { color: primary } },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [{ offset: 0, color: 'rgba(15, 143, 131, 0.18)' }, { offset: 1, color: 'rgba(15, 143, 131, 0)' }],
          },
        },
        markLine,
      },
      {
        name: '7日均线', type: 'line',
        data: trendPoints.value.map(p => p.smoothed),
        smooth: true, symbol: 'none',
        lineStyle: { color: accent, width: 2, type: 'dashed' },
        emphasis: { lineStyle: { color: accent, width: 2, type: 'dashed' } },
      },
    ],
  }
})

const ranges = [{ d: 7, l: '7天' }, { d: 30, l: '1月' }, { d: 90, l: '3月' }, { d: 365, l: '1年' }]

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="page">
    <div class="grid-2col">
      <!-- Chart -->
      <div class="card card-wide motion-card">
        <div class="card-row">
          <h3 class="card-title">体重趋势</h3>
          <div class="pills">
            <button v-for="r in ranges" :key="r.d" class="pill pressable" :class="{ on: timeRange === r.d }" @click="changeRange(r.d)">{{ r.l }}</button>
          </div>
        </div>
        <div class="chart-box" v-if="trendPoints.length > 0">
          <v-chart :option="chartOption" autoresize style="height:340px" />
        </div>
        <div v-else class="empty-area">
          <p class="empty-title">还没有体重数据</p>
          <p class="empty-desc">在右侧快速录入第一条记录</p>
        </div>
      </div>

      <!-- Entry + List -->
      <div class="card motion-card" style="animation-delay: 80ms">
        <h3 class="card-title">快速录入</h3>
        <form @submit.prevent="submitWeight" class="form-stack">
          <div class="field">
            <label class="field-label">体重 (kg)</label>
            <input v-model="newWeight" type="number" step="0.01" min="20" max="300" placeholder="例：70.55" class="input-glass" required />
          </div>
          <div class="field">
            <label class="field-label">备注（可选）</label>
            <input v-model="newNote" type="text" placeholder="早晨空腹" class="input-glass" />
          </div>
          <div class="field">
            <label class="field-label">记录时间</label>
            <input v-model="newRecordedAt" type="datetime-local" class="input-glass" />
          </div>
          <button type="submit" class="btn-teal pressable" :disabled="submitting">{{ submitting ? '保存中...' : '记录体重' }}</button>
        </form>

        <div class="info-strip">
          <span>目标体重 <strong>{{ targetWeight }}kg</strong></span>
          <span>健康范围 <strong>{{ bmiNormal.low }}–{{ bmiNormal.high }}kg</strong></span>
        </div>

        <!-- Records -->
        <div class="records-scroll">
          <div v-for="r in records.slice(0, 20)" :key="r.id" class="rec-row">
            <div>
              <span class="rec-kg">{{ r.weight_kg }}<small>kg</small></span>
              <span class="rec-bmi" v-if="r.bmi">BMI {{ r.bmi }}</span>
            </div>
            <div class="rec-meta">
              <span>{{ fmtDate(r.recorded_at) }}</span>
              <span v-if="r.note">· {{ r.note }}</span>
              <button class="rec-del" @click="deleteRecord(r.id)" aria-label="删除体重记录"><X class="x-icon" /></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 1200px; margin: 0 auto; }

.grid-2col {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  align-items: start;
}

@media (max-width: 768px) {
  .grid-2col { grid-template-columns: 1fr; }
}

/* Glass card */
.card {
  background: var(--glass-bg);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  transition: transform var(--duration-base) var(--ease-emphasis), background var(--duration-base), box-shadow var(--duration-base), border-color var(--duration-base);
}

.card:hover {
  box-shadow: var(--shadow-md), var(--shadow-glow);
  background: var(--glass-bg-hover);
  border-color: rgba(15, 143, 131, 0.22);
  transform: translateY(-2px);
}

.card-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--color-text);
}

.card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-row .card-title { margin-bottom: 0; }

/* Pills */
.pills {
  display: flex;
  gap: 3px;
  background: rgba(100,116,139,0.08);
  border-radius: 10px;
  padding: 3px;
}

.pill {
  padding: 4px 12px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 12px;
  font-family: var(--font-body);
  font-weight: 500;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), color var(--duration-base), box-shadow var(--duration-base);
}

.pill.on {
  background: var(--glass-bg-strong);
  color: var(--color-primary);
  font-weight: 600;
  box-shadow: var(--shadow-xs);
}

.pill:hover {
  color: var(--color-text);
}

/* Chart */
.chart-box { min-height: 280px; }

.empty-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  gap: 4px;
}

.empty-title { font-weight: 600; color: var(--color-text-muted); }
.empty-desc { font-size: 13px; color: var(--color-text-muted); }

/* Form */
.form-stack { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }

.field { display: flex; flex-direction: column; gap: 4px; }

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.input-glass {
  padding: 10px 14px;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-family: var(--font-body);
  color: var(--color-text);
  outline: none;
  min-height: 44px;
  transition: border-color var(--duration-base), box-shadow var(--duration-base), background var(--duration-base), transform var(--duration-fast);
}

.input-glass:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
  background: var(--glass-bg-hover);
  transform: translateY(-1px);
}

.btn-teal {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 700;
  font-family: var(--font-body);
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  cursor: pointer;
  min-height: 44px;
  transition: transform var(--duration-fast) var(--ease-standard), box-shadow var(--duration-base), filter var(--duration-base);
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.25);
}

.btn-teal:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(13, 148, 136, 0.35);
}

.btn-teal:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

/* Info strip */
.info-strip {
  display: flex;
  justify-content: space-between;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 16px;
}

.info-strip strong { color: var(--color-text); }

/* Records */
.records-scroll {
  max-height: 340px;
  overflow-y: auto;
  border-top: 1px solid var(--color-border-light);
}

.rec-row {
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-light);
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base);
  border-radius: 12px;
}

.rec-row:last-child { border-bottom: none; }

.rec-row:hover {
  background: rgba(15, 143, 131, 0.05);
  transform: translateX(4px);
}

.rec-kg {
  font-family: var(--font-heading);
  font-size: 19px;
  font-weight: 700;
  color: var(--color-text);
}

.rec-kg small {
  font-size: 13px;
  font-weight: 400;
  color: var(--color-text-muted);
}

.rec-bmi {
  font-size: 11px;
  background: rgba(13, 148, 136, 0.12);
  color: var(--color-primary);
  padding: 1px 8px;
  border-radius: 6px;
  margin-left: 8px;
  font-weight: 500;
}

.rec-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.rec-del {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 18px;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
  min-width: 32px;
  min-height: 32px;
  transition: background var(--duration-base), color var(--duration-base), transform var(--duration-fast);
}

.rec-del:hover { color: var(--color-danger); background: rgba(239,68,68,0.08); transform: scale(1.08); }
.x-icon { width: 16px; height: 16px; }
</style>
