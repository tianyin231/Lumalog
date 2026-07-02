<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Bike, CheckCircle2, Download, Dumbbell, Eye, Footprints, HeartPulse, MapPin, Plus, RefreshCw, Smartphone, Waves, X } from 'lucide-vue-next'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()

interface ExerciseRecord {
  id: number; exercise_type: string; duration_minutes: number; calories_burned: number
  steps: number | null; distance_km: number | null; avg_heart_rate: number | null
  source: string; note: string | null; recorded_at: string
}

interface TrackPoint {
  timestamp: number; timestamp_local?: string; latitude: number | null; longitude: number | null
  heart_rate: number | null; speed_mps: number | null; distance_meters: number | null
}

interface ActivitySample {
  timestamp: number; timestamp_local?: string; heart_rate: number | null
  speed_mps: number | null; distance_meters: number | null
}

interface ExerciseDetail {
  record: ExerciseRecord
  track_points: TrackPoint[]
  samples: ActivitySample[]
  sport_report: Record<string, any> | null
  recovery_rate: Record<string, any> | null
  summary: Record<string, number | null>
}

const records = ref<ExerciseRecord[]>([])
const loading = ref(true)
const showForm = ref(false)
const submitting = ref(false)
const miLoading = ref(false)
const miImporting = ref(false)
const miMessage = ref('')
const miStatus = ref<any>({ authenticated: false })
const miActivities = ref<any[]>([])
const selectedMiIds = ref<string[]>([])
const syncDays = ref(30)
const detailLoading = ref(false)
const detailError = ref('')
const detail = ref<ExerciseDetail | null>(null)
const mapTileError = ref(false)
const mapEl = ref<HTMLDivElement | null>(null)
let detailMap: L.Map | null = null

const exTypes = [
  { v: 'walk', l: '步行' }, { v: 'run', l: '跑步' }, { v: 'cycle', l: '骑行' },
  { v: 'swim', l: '游泳' }, { v: 'gym', l: '健身' }, { v: 'yoga', l: '瑜伽' }, { v: 'other', l: '其他' },
]

const exIcons: Record<string, any> = {
  walk: Footprints,
  run: HeartPulse,
  cycle: Bike,
  swim: Waves,
  gym: Dumbbell,
  yoga: HeartPulse,
  other: Dumbbell,
}

const form = ref({ exercise_type: 'walk', duration_minutes: 30, calories_burned: 0, steps: null as number | null, distance_km: null as number | null, note: '', recorded_at: '' })

onMounted(async () => {
  await fetchRecords()
  await openRouteDetail()
  await loadMiStatus()
  if (miStatus.value.authenticated) await fetchMiActivities()
})

onUnmounted(() => resetMap())

watch(() => route.query.detail, () => {
  openRouteDetail()
})

async function fetchRecords() {
  loading.value = true
  try { records.value = await (await fetch('/api/exercise/?days=30')).json() }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}

async function loadMiStatus() {
  try {
    miStatus.value = await (await fetch('/api/mi-fit/status')).json()
  } catch (e) {
    console.error(e)
  }
}

async function fetchMiActivities() {
  miLoading.value = true
  miMessage.value = ''
  try {
    const data = await (await fetch(`/api/mi-fit/activities?days=${syncDays.value}&limit=50`)).json()
    miActivities.value = data.activities || []
    selectedMiIds.value = miActivities.value.filter(a => !a.imported).map(a => a.activity_id)
    miMessage.value = `读取到 ${miActivities.value.length} 条运动`
  } catch (e) {
    console.error(e)
    miMessage.value = '读取小米运动失败，请先在设置页登录'
  } finally {
    miLoading.value = false
  }
}

async function importSelectedMi() {
  miImporting.value = true
  miMessage.value = ''
  try {
    const data = await (await fetch('/api/mi-fit/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activity_ids: selectedMiIds.value }),
    })).json()
    miMessage.value = data.message || '导入完成'
    await fetchRecords()
    await fetchMiActivities()
  } catch (e) {
    console.error(e)
    miMessage.value = '导入失败'
  } finally {
    miImporting.value = false
  }
}

async function syncMiFit() {
  miImporting.value = true
  miMessage.value = ''
  try {
    const data = await (await fetch(`/api/mi-fit/sync?days=${syncDays.value}&limit=100`, { method: 'POST' })).json()
    miMessage.value = data.message || '同步完成'
    await fetchRecords()
    await fetchMiActivities()
  } catch (e) {
    console.error(e)
    miMessage.value = '同步失败'
  } finally {
    miImporting.value = false
  }
}

async function backfillMiDetails() {
  miImporting.value = true
  miMessage.value = ''
  try {
    const data = await (await fetch('/api/mi-fit/backfill-details', { method: 'POST' })).json()
    miMessage.value = data.message || '详情补拉完成'
  } catch (e) {
    console.error(e)
    miMessage.value = '详情补拉失败'
  } finally {
    miImporting.value = false
  }
}

async function submitExercise() {
  submitting.value = true
  try {
    const body = {
      ...form.value,
      recorded_at: form.value.recorded_at ? new Date(form.value.recorded_at).toISOString() : null,
    }
    await fetch('/api/exercise/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    showForm.value = false
    form.value = { exercise_type: 'walk', duration_minutes: 30, calories_burned: 0, steps: null, distance_km: null, note: '', recorded_at: '' }
    await fetchRecords()
  } catch (e) { console.error(e) }
  finally { submitting.value = false }
}

async function deleteRecord(id: number) {
  await fetch(`/api/exercise/${id}`, { method: 'DELETE' })
  await fetchRecords()
}

async function openDetail(record: ExerciseRecord) {
  detail.value = null
  detailError.value = ''
  detailLoading.value = true
  try {
    const res = await fetch(`/api/exercise/${record.id}/detail`)
    if (!res.ok) throw new Error(record.source === 'mi_fit' ? '这条记录还没有详情，请先补拉详情' : '这条记录没有详情数据')
    detail.value = await res.json()
    detailLoading.value = false
    await nextTick()
    window.requestAnimationFrame(renderMap)
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

async function openRouteDetail() {
  const raw = Array.isArray(route.query.detail) ? route.query.detail[0] : route.query.detail
  const id = Number(raw)
  if (!Number.isInteger(id) || id <= 0) return
  if (detail.value?.record.id === id || detailLoading.value) return

  const localRecord = records.value.find(r => r.id === id)
  if (localRecord) {
    await openDetail(localRecord)
    return
  }

  try {
    const res = await fetch(`/api/exercise/${id}`)
    if (!res.ok) return
    await openDetail(await res.json())
  } catch (e) {
    console.error(e)
  }
}

function closeDetail() {
  detail.value = null
  detailError.value = ''
  detailLoading.value = false
  resetMap()
  if (route.query.detail) {
    const nextQuery = { ...route.query }
    delete nextQuery.detail
    router.replace({ path: '/exercise', query: nextQuery })
  }
}

function resetMap() {
  mapTileError.value = false
  if (detailMap) {
    detailMap.remove()
    detailMap = null
  }
}

function renderMap() {
  resetMap()
  const points = validTrackPoints.value
  if (!mapEl.value || points.length < 2) return
  detailMap = L.map(mapEl.value, { scrollWheelZoom: false })
  const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  })
  tileLayer.on('tileerror', () => {
    mapTileError.value = true
  })
  tileLayer.addTo(detailMap)
  const latLngs = points.map(p => [p.latitude as number, p.longitude as number] as [number, number])
  L.polyline(latLngs, { color: '#0f8f83', weight: 5, opacity: 0.9 }).addTo(detailMap)
  L.circleMarker(latLngs[0], { radius: 7, color: '#10b981', fillColor: '#10b981', fillOpacity: 1 }).addTo(detailMap).bindTooltip('起点')
  L.circleMarker(latLngs[latLngs.length - 1], { radius: 7, color: '#ef4444', fillColor: '#ef4444', fillOpacity: 1 }).addTo(detailMap).bindTooltip('终点')
  detailMap.fitBounds(latLngs, { padding: [24, 24] })
  window.setTimeout(() => detailMap?.invalidateSize(), 120)
}

function typeLabel(t: string) { return exTypes.find(x => x.v === t)?.l || t }
function fmtDate(s: string) { return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' }) }
function fmtMiTime(a: any) { return a.start_time_local || (a.start_time ? new Date(a.start_time * 1000).toLocaleString('zh-CN') : '未知时间') }
function miDistance(a: any) { return a.distance_km ? `${a.distance_km}km` : '' }
function fmtMetric(value: number | null | undefined, suffix = '') { return value === null || value === undefined ? '--' : `${value}${suffix}` }
function fmtDuration(seconds: number | null | undefined) {
  if (!seconds) return '--'
  const min = Math.round(seconds / 60)
  return min >= 60 ? `${Math.floor(min / 60)}小时${min % 60}分` : `${min}分钟`
}
function pointLabel(p: TrackPoint | ActivitySample) {
  return p.timestamp_local || new Date(p.timestamp * 1000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function readCssColor(name: string, fallback: string) {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

const validTrackPoints = computed(() => (detail.value?.track_points || []).filter(p => p.latitude !== null && p.longitude !== null))
const heartSeries = computed(() => {
  const source = detail.value?.samples?.some(s => s.heart_rate) ? detail.value.samples : detail.value?.track_points || []
  return source.filter(p => p.heart_rate).map(p => ({ label: pointLabel(p), value: p.heart_rate }))
})
const speedSeries = computed(() => {
  const source = detail.value?.samples?.some(s => s.speed_mps !== null) ? detail.value.samples : detail.value?.track_points || []
  return source.filter(p => p.speed_mps !== null).map(p => ({ label: pointLabel(p), value: Number(((p.speed_mps || 0) * 3.6).toFixed(2)) }))
})
const detailMetrics = computed(() => {
  const report = detail.value?.sport_report || {}
  const summary = detail.value?.summary || {}
  return [
    { label: '最大心率', value: fmtMetric((report.max_hr ?? summary.heart_rate_max) as number | null, ' bpm') },
    { label: '最低心率', value: fmtMetric((report.min_hr ?? summary.heart_rate_min) as number | null, ' bpm') },
    { label: '最大速度', value: fmtMetric(summary.speed_max_kmh as number | null, ' km/h') },
    { label: '训练效果', value: fmtMetric(report.train_effect as number | null) },
    { label: '无氧效果', value: fmtMetric(report.anaerobic_train_effect as number | null) },
    { label: '恢复时间', value: fmtDuration(report.recovery_time as number | null) },
  ]
})

function lineOptions(title: string, data: { label: string; value: number | null }[], color: string, unit: string) {
  const muted = readCssColor('--color-text-muted', '#667985')
  const border = readCssColor('--color-border-light', 'rgba(15, 23, 42, 0.08)')
  return {
    grid: { top: 28, right: 18, bottom: 28, left: 42 },
    tooltip: { trigger: 'axis', formatter: (items: any[]) => `${items[0].axisValue}<br/>${title}: ${items[0].data}${unit}` },
    xAxis: {
      type: 'category',
      data: data.map(p => p.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 10, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: border } },
      axisLabel: { color: muted, fontSize: 10 },
    },
    series: [{
      name: title,
      type: 'line',
      data: data.map(p => p.value),
      smooth: true,
      symbol: 'none',
      lineStyle: { color, width: 2.5 },
      areaStyle: { color: `${color}22` },
    }],
  }
}

const heartOptions = computed(() => lineOptions('心率', heartSeries.value, '#ef4444', ' bpm'))
const speedOptions = computed(() => lineOptions('速度', speedSeries.value, '#3b82f6', ' km/h'))

const weekStats = computed(() => {
  const d = new Date(); d.setDate(d.getDate() - 7)
  const w = records.value.filter(r => new Date(r.recorded_at) >= d)
  return {
    count: w.length,
    cal: w.reduce((s, r) => s + r.calories_burned, 0),
    min: w.reduce((s, r) => s + r.duration_minutes, 0),
    steps: w.reduce((s, r) => s + (r.steps || 0), 0),
  }
})
</script>

<template>
  <div class="page">
    <!-- Weekly Summary -->
    <div class="stat-grid">
      <div class="stat-card motion-card" style="animation-delay: 0ms">
        <span class="st-num">{{ weekStats.count }}</span>
        <span class="st-label">本周运动</span>
      </div>
      <div class="stat-card motion-card" style="animation-delay: 50ms">
        <span class="st-num">{{ weekStats.cal }}</span>
        <span class="st-label">消耗热量 kcal</span>
      </div>
      <div class="stat-card motion-card" style="animation-delay: 100ms">
        <span class="st-num">{{ weekStats.min }}</span>
        <span class="st-label">运动时长 分钟</span>
      </div>
      <div class="stat-card motion-card" style="animation-delay: 150ms">
        <span class="st-num">{{ weekStats.steps.toLocaleString() }}</span>
        <span class="st-label">本周步数</span>
      </div>
    </div>

    <!-- Records -->
    <div class="card motion-card" style="animation-delay: 200ms">
      <div class="card-row">
        <h3 class="card-title">运动记录</h3>
        <button class="btn-teal-sm pressable" @click="showForm = !showForm">
          <Plus v-if="!showForm" class="btn-icon" />
          {{ showForm ? '取消' : '手动录入' }}
        </button>
      </div>

      <!-- Entry form -->
      <div v-if="showForm" class="form-card">
        <div class="form-grid">
          <div class="field">
            <label class="f-label">类型</label>
            <select v-model="form.exercise_type" class="input-g">
              <option v-for="t in exTypes" :key="t.v" :value="t.v">{{ t.l }}</option>
            </select>
          </div>
          <div class="field">
            <label class="f-label">时长 (分钟)</label>
            <input v-model.number="form.duration_minutes" type="number" class="input-g" min="0" />
          </div>
          <div class="field">
            <label class="f-label">消耗 (kcal)</label>
            <input v-model.number="form.calories_burned" type="number" class="input-g" min="0" />
          </div>
          <div class="field">
            <label class="f-label">步数</label>
            <input v-model.number="form.steps" type="number" class="input-g" placeholder="可选" />
          </div>
          <div class="field">
            <label class="f-label">距离 (km)</label>
            <input v-model.number="form.distance_km" type="number" class="input-g" step="0.1" placeholder="可选" />
          </div>
          <div class="field">
            <label class="f-label">记录时间</label>
            <input v-model="form.recorded_at" type="datetime-local" class="input-g" />
          </div>
        </div>
        <button class="btn-teal-sm pressable" @click="submitExercise" :disabled="submitting">{{ submitting ? '保存中...' : '保存' }}</button>
      </div>

      <!-- List -->
      <div v-if="loading" class="center-text">加载中...</div>
      <div v-else-if="records.length === 0" class="empty-area">
        <p class="empty-title">还没有运动记录</p>
      </div>
      <div v-else class="ex-list">
        <div v-for="r in records" :key="r.id" class="ex-row">
          <div class="flex-1">
            <span class="ex-type">
              <component :is="exIcons[r.exercise_type] || Dumbbell" class="ex-icon" />
              {{ typeLabel(r.exercise_type) }}
            </span>
            <div class="ex-stats">
              <span v-if="r.duration_minutes">{{ r.duration_minutes }}分钟</span>
              <span>{{ r.calories_burned }} kcal</span>
              <span v-if="r.steps">{{ r.steps.toLocaleString() }}步</span>
              <span v-if="r.distance_km">{{ r.distance_km }}km</span>
            </div>
            <div class="ex-meta">
              <span v-if="r.source === 'mi_fit'" class="mi-badge"><Smartphone class="mini-icon" />小米</span>
              <span>{{ fmtDate(r.recorded_at) }}</span>
            </div>
          </div>
          <div class="row-actions">
            <button
              v-if="r.source === 'mi_fit'"
              class="detail-btn"
              @click="openDetail(r)"
              aria-label="查看运动详情"
              title="查看详情"
            >
              <Eye class="x-icon" />
            </button>
            <button class="rm-btn" @click="deleteRecord(r.id)" aria-label="删除运动记录" title="删除"><X class="x-icon" /></button>
          </div>
        </div>
      </div>
    </div>

    <!-- Mi Sync Status -->
    <div class="card sync-card motion-card">
      <div class="card-row">
        <h3 class="card-title">小米运动健康同步</h3>
        <span class="sync-pill" :class="{ on: miStatus.authenticated }">
          <Smartphone class="mini-icon" />
          {{ miStatus.authenticated ? '已连接' : '未登录' }}
        </span>
      </div>

      <div v-if="!miStatus.authenticated" class="empty-area compact">
        <p class="empty-title">请先在设置页登录小米运动健康</p>
      </div>

      <div v-else class="mi-panel">
        <div class="mi-toolbar">
          <div class="field days-field">
            <label class="f-label">同步天数</label>
            <input v-model.number="syncDays" type="number" min="1" max="365" class="input-g" />
          </div>
          <button class="btn-secondary pressable" @click="fetchMiActivities" :disabled="miLoading">
            <RefreshCw class="btn-icon" :class="{ spinning: miLoading }" />
            {{ miLoading ? '读取中...' : '读取活动' }}
          </button>
          <button class="btn-secondary pressable" @click="importSelectedMi" :disabled="miImporting || selectedMiIds.length === 0">
            <Download class="btn-icon" />
            {{ miImporting ? '导入中...' : `导入选中 ${selectedMiIds.length}` }}
          </button>
          <button class="btn-teal-sm pressable" @click="syncMiFit" :disabled="miImporting">
            <RefreshCw class="btn-icon" :class="{ spinning: miImporting }" />
            {{ miImporting ? '同步中...' : '一键同步' }}
          </button>
          <button class="btn-secondary pressable" @click="backfillMiDetails" :disabled="miImporting">
            <MapPin class="btn-icon" />
            补拉详情
          </button>
        </div>

        <p v-if="miMessage" class="status-msg">{{ miMessage }}</p>

        <div v-if="miActivities.length" class="mi-list">
          <label v-for="a in miActivities" :key="a.activity_id" class="mi-row" :class="{ imported: a.imported }">
            <input v-model="selectedMiIds" type="checkbox" :value="a.activity_id" :disabled="a.imported" />
            <span class="mi-main">
              <strong>{{ a.title || '小米运动' }}</strong>
              <small>{{ fmtMiTime(a) }} · {{ a.duration || '未知时长' }} <template v-if="miDistance(a)">· {{ miDistance(a) }}</template></small>
            </span>
            <span v-if="a.imported" class="imported-badge"><CheckCircle2 class="mini-icon" />已导入</span>
          </label>
        </div>
      </div>
    </div>

    <div v-if="detailLoading || detailError || detail" class="modal-layer" role="dialog" aria-modal="true" aria-labelledby="exercise-detail-title">
      <div class="detail-modal glass-strong">
        <div class="detail-head">
          <div>
            <p class="detail-kicker">运动详情</p>
            <h3 id="exercise-detail-title" class="detail-title">
              {{ detail ? typeLabel(detail.record.exercise_type) : '正在读取' }}
            </h3>
          </div>
          <button class="close-btn" @click="closeDetail" aria-label="关闭运动详情"><X class="x-icon" /></button>
        </div>

        <div v-if="detailLoading" class="center-text">详情加载中...</div>
        <div v-else-if="detailError" class="empty-area compact">
          <p class="empty-title">{{ detailError }}</p>
        </div>
        <div v-else-if="detail" class="detail-body">
          <div class="detail-summary">
            <div class="summary-tile">
              <span>{{ fmtMetric(detail.record.distance_km, ' km') }}</span>
              <small>距离</small>
            </div>
            <div class="summary-tile">
              <span>{{ detail.record.duration_minutes }} 分钟</span>
              <small>时长</small>
            </div>
            <div class="summary-tile">
              <span>{{ detail.record.calories_burned }} kcal</span>
              <small>消耗</small>
            </div>
            <div class="summary-tile">
              <span>{{ fmtMetric(detail.summary.heart_rate_avg, ' bpm') }}</span>
              <small>平均心率</small>
            </div>
          </div>

          <div class="map-panel">
            <template v-if="validTrackPoints.length >= 2">
              <div ref="mapEl" class="track-map" aria-label="运动轨迹地图"></div>
              <div v-if="mapTileError" class="map-warning">
                地图底图加载失败，轨迹数据仍可查看
              </div>
            </template>
            <div v-else class="map-empty">
              <MapPin class="empty-map-icon" />
              <span>该记录没有可用 GPS 轨迹</span>
            </div>
          </div>

          <div class="detail-grid">
            <div v-for="m in detailMetrics" :key="m.label" class="metric-cell">
              <span>{{ m.value }}</span>
              <small>{{ m.label }}</small>
            </div>
          </div>

          <div class="chart-grid">
            <div class="chart-panel">
              <div class="chart-title">心率曲线</div>
              <VChart v-if="heartSeries.length" class="detail-chart" :option="heartOptions" autoresize />
              <div v-else class="chart-empty">暂无心率采样</div>
            </div>
            <div class="chart-panel">
              <div class="chart-title">速度曲线</div>
              <VChart v-if="speedSeries.length" class="detail-chart" :option="speedOptions" autoresize />
              <div v-else class="chart-empty">暂无速度采样</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }

.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }

@media (max-width: 640px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }

.stat-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 18px 16px;
  text-align: center;
  box-shadow: var(--shadow-xs);
  transition: transform var(--duration-base) var(--ease-emphasis), background var(--duration-base), box-shadow var(--duration-base), border-color var(--duration-base);
}

.stat-card:hover {
  transform: translateY(-2px);
  background: var(--glass-bg-hover);
  border-color: rgba(15, 143, 131, 0.22);
  box-shadow: var(--shadow-sm), var(--shadow-glow);
}

.st-num {
  display: block;
  font-family: var(--font-heading);
  font-size: 26px;
  font-weight: 700;
  color: var(--color-primary);
}

.st-label {
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 500;
}

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
  transform: translateY(-2px);
  background: var(--glass-bg-hover);
  border-color: rgba(15, 143, 131, 0.22);
  box-shadow: var(--shadow-md), var(--shadow-glow);
}

.card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title { font-family: var(--font-heading); font-size: 18px; font-weight: 700; margin-bottom: 0; }

.btn-teal-sm {
  padding: 7px 18px; border: none; border-radius: 10px; font-size: 13px; font-weight: 700;
  font-family: var(--font-body); background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff; cursor: pointer;
  transition: transform var(--duration-fast), box-shadow var(--duration-base), filter var(--duration-base);
  box-shadow: 0 3px 12px rgba(13, 148, 136, 0.2);
  display: inline-flex; align-items: center; gap: 6px; min-height: 38px;
}

.btn-teal-sm:hover { transform: translateY(-1px); }
.btn-teal-sm:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.form-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  animation: riseIn var(--duration-slow) var(--ease-emphasis) both;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.field { display: flex; flex-direction: column; gap: 4px; }
.f-label { font-size: 11px; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

.input-g {
  padding: 8px 12px; border: 1px solid var(--glass-border); border-radius: 8px;
  font-size: 13px; font-family: var(--font-body); background: var(--glass-bg);
  color: var(--color-text); outline: none; transition: border-color var(--duration-base), box-shadow var(--duration-base), background var(--duration-base), transform var(--duration-fast);
  min-height: 40px;
}

.input-g:focus { border-color: var(--color-primary); box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.1); transform: translateY(-1px); }

select.input-g { cursor: pointer; }

/* Exercise list */
.ex-list { display: flex; flex-direction: column; }
.ex-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 0; border-bottom: 1px solid var(--color-border-light);
  border-radius: 14px;
  transition: transform var(--duration-fast), background var(--duration-base);
}

.ex-row:last-child { border-bottom: none; }
.ex-row:hover { background: rgba(15, 143, 131, 0.05); transform: translateX(4px); }

.ex-type { font-weight: 600; color: var(--color-text); display: inline-flex; align-items: center; gap: 8px; }
.ex-icon { width: 18px; height: 18px; color: var(--color-primary); }
.ex-stats { display: flex; gap: 10px; margin-top: 2px; font-size: 12px; color: var(--color-text-secondary); }
.ex-meta { display: flex; gap: 8px; margin-top: 2px; font-size: 11px; color: var(--color-text-muted); }
.mi-badge { color: var(--color-accent); font-weight: 500; display: inline-flex; align-items: center; gap: 3px; }
.mini-icon { width: 13px; height: 13px; }

.rm-btn {
  background: none; border: none; color: var(--color-text-muted);
  cursor: pointer; padding: 6px; border-radius: 8px; transition: transform var(--duration-fast), background var(--duration-base), color var(--duration-base);
  min-width: 44px; min-height: 44px; display: inline-flex; align-items: center; justify-content: center;
}

.rm-btn:hover { color: var(--color-danger); background: rgba(239,68,68,0.08); transform: scale(1.08); }

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 10px;
}

.detail-btn {
  min-width: 44px;
  min-height: 44px;
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  background: var(--glass-bg);
  color: var(--color-primary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--duration-fast), background var(--duration-base), border-color var(--duration-base), color var(--duration-base);
}

.detail-btn:hover {
  background: rgba(15, 143, 131, 0.09);
  border-color: rgba(15, 143, 131, 0.22);
  transform: translateY(-1px);
}

.x-icon { width: 16px; height: 16px; }
.btn-icon { width: 15px; height: 15px; }

/* Sync */
.sync-card { opacity: 1; }
.sync-pill {
  min-height: 30px;
  padding: 5px 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-muted);
  background: rgba(100, 116, 139, 0.1);
}

.sync-pill.on {
  color: var(--color-primary);
  background: rgba(15, 143, 131, 0.1);
}

.mi-panel { display: flex; flex-direction: column; gap: 14px; }

.mi-toolbar {
  display: flex;
  align-items: end;
  gap: 10px;
  flex-wrap: wrap;
}

.days-field { width: 120px; }

.btn-secondary {
  min-height: 40px;
  padding: 9px 14px;
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  background: var(--glass-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
}

.btn-secondary:hover {
  background: var(--glass-bg-hover);
  color: var(--color-primary);
}

.btn-secondary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.status-msg {
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 10px 12px;
  background: rgba(15, 143, 131, 0.08);
  border: 1px solid rgba(15, 143, 131, 0.14);
  border-radius: 12px;
}

.mi-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--color-border-light);
}

.mi-row {
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.mi-row input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
}

.mi-row.imported {
  opacity: 0.72;
}

.mi-main {
  flex: 1;
  min-width: 0;
}

.mi-main strong {
  display: block;
  color: var(--color-text);
  font-size: 14px;
}

.mi-main small {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}

.imported-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-success);
  font-size: 12px;
  font-weight: 700;
}

.spinning { animation: spin 0.9s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }

.empty-area { padding: 48px; text-align: center; }
.empty-area.compact { padding: 28px; }
.empty-title { font-weight: 600; color: var(--color-text-muted); }
.center-text { text-align: center; padding: 32px; color: var(--color-text-muted); }

.flex-1 { flex: 1; }
.muted-text { color: var(--color-text-muted); }
.small { font-size: 12px; }

.modal-layer {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(2, 6, 23, 0.48);
}

.detail-modal {
  width: min(1040px, 100%);
  max-height: min(88dvh, 900px);
  overflow-y: auto;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
}

.detail-head {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px 22px 14px;
  background: var(--glass-bg-strong);
  border-bottom: 1px solid var(--color-border-light);
}

.detail-kicker {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.detail-title {
  margin-top: 2px;
  font-size: 22px;
  font-weight: 800;
}

.close-btn {
  min-width: 44px;
  min-height: 44px;
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  background: var(--glass-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: var(--color-danger);
  background: rgba(239,68,68,0.08);
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 22px 22px;
}

.detail-summary,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.summary-tile,
.metric-cell,
.chart-panel {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.34)),
    var(--glass-bg);
  box-shadow: var(--shadow-xs);
  transition:
    transform var(--duration-base) var(--ease-emphasis),
    box-shadow var(--duration-base),
    border-color var(--duration-base),
    background var(--duration-base);
  animation: riseIn var(--duration-slow) var(--ease-emphasis) both;
}

.summary-tile::before,
.metric-cell::before,
.chart-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 18% 0%, rgba(84, 214, 199, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.28), transparent 42%);
  opacity: 0.72;
}

.summary-tile:hover,
.metric-cell:hover,
.chart-panel:hover {
  transform: translateY(-2px) scale(1.01);
  border-color: rgba(15, 143, 131, 0.22);
  box-shadow: var(--shadow-sm), var(--shadow-glow);
}

.summary-tile,
.metric-cell {
  min-height: 76px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.summary-tile > *,
.metric-cell > *,
.chart-panel > * {
  position: relative;
  z-index: 1;
}

.summary-tile span,
.metric-cell span {
  color: var(--color-text);
  font-size: 18px;
  font-weight: 800;
}

.summary-tile small,
.metric-cell small {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 600;
}

.map-panel {
  position: relative;
  min-height: 360px;
  border: 1px solid var(--color-border-light);
  border-radius: 16px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.06);
}

.track-map {
  width: 100%;
  height: 360px;
}

.map-warning {
  position: absolute;
  left: 12px;
  bottom: 12px;
  z-index: 500;
  padding: 7px 10px;
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 10px;
  background: rgba(255, 251, 235, 0.92);
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
  box-shadow: var(--shadow-xs);
}

.map-empty,
.chart-empty {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 14px;
}

.empty-map-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.chart-panel {
  min-width: 0;
  padding: 14px 12px 8px;
}

.chart-title {
  color: var(--color-text);
  font-size: 14px;
  font-weight: 800;
  padding: 0 4px 4px;
}

.detail-chart {
  width: 100%;
  height: 240px;
}

:deep(.leaflet-container) {
  font-family: var(--font-body);
}

@media (max-width: 760px) {
  .modal-layer { padding: 10px; align-items: stretch; }
  .detail-modal { max-height: calc(100dvh - 20px); }
  .detail-head { padding: 16px 14px 12px; }
  .detail-body { padding: 14px; }
  .detail-summary,
  .detail-grid,
  .chart-grid { grid-template-columns: 1fr; }
  .track-map,
  .map-panel { min-height: 300px; height: 300px; }
  .ex-row { align-items: flex-start; gap: 8px; }
  .ex-stats,
  .ex-meta { flex-wrap: wrap; }
  .row-actions { margin-left: 0; }
}

[data-theme="dark"] .summary-tile,
[data-theme="dark"] .metric-cell,
[data-theme="dark"] .chart-panel {
  background:
    linear-gradient(145deg, rgba(18, 38, 40, 0.74), rgba(9, 22, 22, 0.38)),
    var(--glass-bg);
}
</style>
