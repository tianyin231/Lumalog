<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { BarChart3, ChevronLeft, ChevronRight, Dumbbell } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const store = useAppStore()
const router = useRouter()

interface TrendPoint { date: string; weight: number; bmi: number | null; smoothed: number | null }
interface WeightRecord {
  id: number; weight_kg: number; bmi: number | null; body_fat_pct: number | null
  note: string | null; source: string; recorded_at: string
}
interface FoodRecord {
  id: number; meal_type: string; total_calories: number; note: string | null; recorded_at: string
}
interface WeightStats {
  current_weight: number | null; start_weight: number | null; weight_change: number | null
  avg_7days: number | null; min_weight: number | null; max_weight: number | null
  bmi: number | null; days_tracked: number; trend_direction: string
}
interface ExerciseRecord {
  id: number; exercise_type: string; duration_minutes: number; calories_burned: number
  steps: number | null; distance_km: number | null; avg_heart_rate: number | null
  source: string; note: string | null; recorded_at: string
}
interface DailyCalorieSummary { date: string; total_calories: number }
interface DailyExerciseSummary { total_calories_burned: number }

const stats = ref<WeightStats | null>(null)
const trendPoints = ref<TrendPoint[]>([])
const monthWeights = ref<WeightRecord[]>([])
const monthFoods = ref<FoodRecord[]>([])
const monthExercises = ref<ExerciseRecord[]>([])
const recentExercises = ref<ExerciseRecord[]>([])
const selectedMonth = ref(monthStart(new Date()))
const diaryLoading = ref(false)
const loading = ref(true)

onMounted(async () => {
  try {
    const [sRes, tRes, eRes, fRes, exSummaryRes, settingsRes] = await Promise.all([
      fetch('/api/weight/stats'),
      fetch('/api/weight/trend?days=14'),
      fetch('/api/exercise/?days=30'),
      fetch('/api/food/summary?days=1'),
      fetch('/api/exercise/summary/today'),
      fetch('/api/settings/'),
    ])
    stats.value = await sRes.json()
    trendPoints.value = await tRes.json()
    recentExercises.value = (await eRes.json()).slice(0, 3)
    const foodSummary: DailyCalorieSummary[] = await fRes.json()
    const exerciseSummary: DailyExerciseSummary = await exSummaryRes.json()
    const settings = await settingsRes.json()
    const todayFood = foodSummary.find(item => item.date === localDateKey())
    store.todayCalories = todayFood?.total_calories ?? 0
    store.todayExercise = exerciseSummary.total_calories_burned ?? 0
    store.settings.nickname = settings.nickname
    store.settings.heightCm = settings.height_cm
    store.settings.targetWeightKg = settings.target_weight_kg
    store.settings.dailyCalorieTarget = settings.daily_calorie_target
    store.currentWeight = stats.value?.current_weight ?? null
    await loadDiaryMonth()
  } catch (e) { console.error(e) }
  finally { loading.value = false }
})

function monthStart(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function localDateKey(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60 * 1000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 10)
}

function daysSince(date: Date) {
  const now = new Date()
  return Math.ceil((now.getTime() - date.getTime()) / 86400000) + 1
}

function dateKeyFromString(value: string) {
  return localDateKey(new Date(value))
}

const monthLabel = computed(() => {
  return selectedMonth.value.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
})

const canGoNextMonth = computed(() => {
  const current = monthStart(new Date())
  return selectedMonth.value < current
})

const diaryCells = computed(() => {
  const year = selectedMonth.value.getFullYear()
  const month = selectedMonth.value.getMonth()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const firstDay = new Date(year, month, 1).getDay()
  const summaries: Record<string, {
    weight?: WeightRecord; calories: number; exerciseKcal: number; exerciseMin: number; notes: string[]
  }> = {}

  for (const item of monthWeights.value) {
    const key = dateKeyFromString(item.recorded_at)
    summaries[key] ??= { calories: 0, exerciseKcal: 0, exerciseMin: 0, notes: [] }
    summaries[key].weight = item
    if (item.note) summaries[key].notes.push(item.note)
  }

  for (const item of monthFoods.value) {
    const key = dateKeyFromString(item.recorded_at)
    summaries[key] ??= { calories: 0, exerciseKcal: 0, exerciseMin: 0, notes: [] }
    summaries[key].calories += item.total_calories || 0
    if (item.note) summaries[key].notes.push(item.note)
  }

  for (const item of monthExercises.value) {
    const key = dateKeyFromString(item.recorded_at)
    summaries[key] ??= { calories: 0, exerciseKcal: 0, exerciseMin: 0, notes: [] }
    summaries[key].exerciseKcal += item.calories_burned || 0
    summaries[key].exerciseMin += item.duration_minutes || 0
    if (item.note) summaries[key].notes.push(item.note)
  }

  const cells: Array<{
    key: string; day: number | null; level: number; isToday: boolean; summary: string
  }> = []

  for (let i = 0; i < firstDay; i += 1) {
    cells.push({ key: `blank-${i}`, day: null, level: 0, isToday: false, summary: '' })
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = new Date(year, month, day)
    const key = localDateKey(date)
    const data = summaries[key]
    const parts = [`${month + 1}月${day}日`]
    if (data?.weight) parts.push(`体重 ${data.weight.weight_kg}kg`)
    if (data?.calories) parts.push(`摄入 ${Math.round(data.calories)}kcal`)
    if (data?.exerciseKcal) parts.push(`运动 ${Math.round(data.exerciseKcal)}kcal / ${data.exerciseMin}分钟`)
    if (data?.notes.length) parts.push(`备注 ${data.notes.slice(0, 2).join('；')}`)

    const score = (data?.weight ? 1 : 0) + (data?.calories ? 1 : 0) + (data?.exerciseKcal ? 1 : 0) + Math.min(data?.notes.length || 0, 1)
    cells.push({
      key,
      day,
      level: Math.min(score, 4),
      isToday: key === localDateKey(),
      summary: data ? parts.join(' · ') : `${month + 1}月${day}日 · 暂无记录`,
    })
  }

  return cells
})

async function loadDiaryMonth() {
  diaryLoading.value = true
  try {
    const days = Math.min(daysSince(selectedMonth.value), 3650)
    const [wRes, eRes, foodListRes] = await Promise.all([
      fetch(`/api/weight/?days=${days}`),
      fetch(`/api/exercise/?days=${days}`),
      fetch(`/api/food/?days=${days}`),
    ])
    const monthPrefix = localDateKey(selectedMonth.value).slice(0, 7)
    monthWeights.value = (await wRes.json()).filter((item: WeightRecord) => dateKeyFromString(item.recorded_at).startsWith(monthPrefix))
    monthExercises.value = (await eRes.json()).filter((item: ExerciseRecord) => dateKeyFromString(item.recorded_at).startsWith(monthPrefix))
    monthFoods.value = (await foodListRes.json()).filter((item: FoodRecord) => dateKeyFromString(item.recorded_at).startsWith(monthPrefix))
  } catch (e) {
    console.error(e)
  } finally {
    diaryLoading.value = false
  }
}

function changeDiaryMonth(offset: number) {
  const next = monthStart(new Date(selectedMonth.value.getFullYear(), selectedMonth.value.getMonth() + offset, 1))
  const current = monthStart(new Date())
  if (next > current) return
  selectedMonth.value = next
  loadDiaryMonth()
}

function readCssColor(name: string, fallback: string) {
  if (typeof window === 'undefined') return fallback
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

const trendOptions = computed(() => {
  const primary = readCssColor('--color-primary', '#0f8f83')
  const accent = readCssColor('--color-accent', '#3b82f6')
  const muted = readCssColor('--color-text-muted', '#667985')
  const border = readCssColor('--color-border-light', 'rgba(15, 23, 42, 0.08)')

  return {
    grid: { top: 12, right: 24, bottom: 12, left: 48 },
    xAxis: {
      type: 'category',
      data: trendPoints.value.map(p => p.date.slice(5)),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: border } },
      axisLabel: { color: muted, fontSize: 10 },
    },
    tooltip: { trigger: 'axis' },
    series: [
      {
        name: '体重', type: 'line',
        data: trendPoints.value.map(p => p.weight),
        smooth: true, symbol: 'circle', symbolSize: 5,
        lineStyle: { color: primary, width: 2.5 },
        itemStyle: { color: primary },
        emphasis: { lineStyle: { color: primary, width: 2.5 }, itemStyle: { color: primary } },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(15, 143, 131, 0.2)' },
              { offset: 1, color: 'rgba(15, 143, 131, 0)' },
            ],
          },
        },
      },
      {
        name: '趋势', type: 'line',
        data: trendPoints.value.map(p => p.smoothed),
        smooth: true, symbol: 'none',
        lineStyle: { color: accent, width: 2, type: 'dashed' },
        emphasis: { lineStyle: { color: accent, width: 2, type: 'dashed' } },
      },
    ],
  }
})

const trendLabel = computed(() => {
  if (!stats.value) return '--'
  const d = stats.value.trend_direction
  return d === 'down' ? '下降中' : d === 'up' ? '上升中' : '保持稳定'
})

const trendMark = computed(() => {
  const d = stats.value?.trend_direction
  return d === 'down' ? 'down' : d === 'up' ? 'up' : 'flat'
})

const bmiCategory = computed(() => {
  const b = stats.value?.bmi
  if (!b) return null
  if (b < 18.5) return { label: '偏瘦', color: '#60a5fa', pct: (b / 18.5) * 50 }
  if (b < 24) return { label: '健康', color: '#34d399', pct: 50 + ((b - 18.5) / 5.5) * 30 }
  if (b < 28) return { label: '偏胖', color: '#fbbf24', pct: 80 + ((b - 24) / 4) * 20 }
  return { label: '肥胖', color: '#f87171', pct: 95 }
})

function typeLabel(t: string) {
  const labels: Record<string, string> = {
    walk: '步行',
    run: '跑步',
    cycle: '骑行',
    swim: '游泳',
    gym: '健身',
    yoga: '瑜伽',
    other: '其他',
  }
  return labels[t] || t
}

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function openExerciseDetail(item: ExerciseRecord) {
  router.push({ path: '/exercise', query: { detail: item.id } })
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="page-header-section">
      <div>
        <h2 class="greeting">你好，{{ store.settings.nickname }}</h2>
        <p class="subtitle">
          <template v-if="stats?.days_tracked">
            已坚持 <strong>{{ stats.days_tracked }}</strong> 天 ·
            当前 <strong>{{ stats.current_weight }}kg</strong>
            · BMI <strong>{{ stats.bmi }}</strong>
          </template>
          <template v-else>开始记录你的第一条体重吧</template>
        </p>
      </div>
    </div>

    <!-- Bento Grid -->
    <div class="bento">
      <!-- Hero Card: Current Weight -->
      <div class="card card-hero motion-card" style="animation-delay: 0ms">
        <div class="card-label">当前体重</div>
        <div class="hero-value">
          <span class="hero-num">{{ stats?.current_weight ?? '--' }}</span>
          <span class="hero-unit">kg</span>
        </div>
        <div class="hero-change" v-if="stats?.weight_change != null">
          <span :class="stats.weight_change < 0 ? 'good' : stats.weight_change > 0 ? 'warn' : ''">
            {{ stats.weight_change < 0 ? '降低' : stats.weight_change > 0 ? '增加' : '持平' }}
            {{ Math.abs(stats.weight_change).toFixed(1) }}kg
          </span>
          <span class="muted-text ml-1">总计</span>
        </div>

        <!-- BMI gauge -->
        <div class="bmi-gauge" v-if="bmiCategory">
          <div class="bmi-track">
            <div class="bmi-indicator" :style="{ left: bmiCategory.pct + '%', background: bmiCategory.color }" />
          </div>
          <div class="bmi-chips">
            <span class="bmi-chip" :class="{ active: bmiCategory.label === '偏瘦' }">偏瘦</span>
            <span class="bmi-chip" :class="{ active: bmiCategory.label === '健康' }">健康</span>
            <span class="bmi-chip" :class="{ active: bmiCategory.label === '偏胖' }">偏胖</span>
            <span class="bmi-chip" :class="{ active: bmiCategory.label === '肥胖' }">肥胖</span>
          </div>
        </div>
      </div>

      <!-- Trend Card -->
      <div class="card card-trend-summary motion-card" style="animation-delay: 50ms">
        <div class="card-label">趋势</div>
        <div class="card-value trend-value" :class="trendMark">
          {{ trendLabel }}
        </div>
        <div class="muted-text small">
          7日均 {{ stats?.avg_7days ?? '--' }}kg · 最低 {{ stats?.min_weight ?? '--' }}kg
        </div>
      </div>

      <!-- Calories Card -->
      <div class="card card-calories motion-card" style="animation-delay: 100ms">
        <div class="card-label">今日热量</div>
        <div class="card-value">
          {{ store.todayCalories }} <small class="muted-text">/ {{ store.settings.dailyCalorieTarget }} kcal</small>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: Math.min(store.calorieProgress, 100) + '%' }" />
        </div>
      </div>

      <!-- Exercise Card -->
      <div class="card card-today-exercise motion-card" style="animation-delay: 150ms">
        <div class="card-label">今日运动</div>
        <div class="card-value">{{ store.todayExercise }} <small class="muted-text">kcal</small></div>
      </div>

      <!-- Wide: Trend Chart -->
      <div class="card card-wide motion-card" style="animation-delay: 180ms">
        <div class="card-label">体重趋势 · 近14天</div>
        <div class="chart-box" v-if="trendPoints.length > 0">
          <v-chart :option="trendOptions" autoresize style="height:260px" />
        </div>
        <div v-else class="empty-chart">
          <BarChart3 class="empty-icon" />
          <p>暂无数据，去体重页记录第一条吧</p>
        </div>
      </div>

      <!-- Monthly Diary -->
      <div class="card card-diary motion-card" style="animation-delay: 190ms">
        <div class="diary-head">
          <div>
            <div class="card-label">日记热力图</div>
            <div class="diary-nav">
              <button
                type="button"
                class="diary-nav-btn"
                aria-label="查看上个月"
                :disabled="diaryLoading"
                @click="changeDiaryMonth(-1)"
              >
                <ChevronLeft class="diary-nav-icon" />
              </button>
              <div class="diary-title">{{ monthLabel }}</div>
              <button
                type="button"
                class="diary-nav-btn"
                aria-label="查看下个月"
                :disabled="diaryLoading || !canGoNextMonth"
                @click="changeDiaryMonth(1)"
              >
                <ChevronRight class="diary-nav-icon" />
              </button>
            </div>
          </div>
          <div class="diary-legend" aria-label="记录强度图例">
            <span>少</span>
            <i class="level-1" />
            <i class="level-2" />
            <i class="level-3" />
            <i class="level-4" />
            <span>多</span>
          </div>
        </div>
        <div class="diary-weekdays" :class="{ loading: diaryLoading }" aria-hidden="true">
          <span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span>
        </div>
        <div class="diary-grid" :class="{ loading: diaryLoading }" aria-label="本月记录热力图">
          <div
            v-for="cell in diaryCells"
            :key="cell.key"
            class="diary-cell"
            :class="[`level-${cell.level}`, { blank: !cell.day, today: cell.isToday }]"
            :data-tooltip="cell.summary"
            :tabindex="cell.day ? 0 : -1"
            :aria-label="cell.summary"
          >
            <span v-if="cell.day">{{ cell.day }}</span>
          </div>
        </div>
      </div>

      <!-- Recent Exercises -->
      <div class="card card-recent-exercise motion-card" style="animation-delay: 200ms">
        <div class="card-label">最近运动</div>
        <div v-if="recentExercises.length" class="exercise-mini-list">
          <button
            v-for="item in recentExercises"
            :key="item.id"
            type="button"
            class="exercise-mini-row"
            :aria-label="`查看${typeLabel(item.exercise_type)}运动详情`"
            @click="openExerciseDetail(item)"
          >
            <div class="exercise-mini-icon">
              <Dumbbell class="mini-icon" />
            </div>
            <div class="exercise-mini-main">
              <strong>{{ typeLabel(item.exercise_type) }}</strong>
              <span>{{ fmtDate(item.recorded_at) }}</span>
            </div>
            <div class="exercise-mini-stat">
              <strong>{{ item.calories_burned }}</strong>
              <span>kcal</span>
            </div>
          </button>
        </div>
        <div v-else class="mini-empty">暂无运动记录</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header-section {
  margin-bottom: 24px;
}

.greeting {
  font-family: var(--font-heading);
  font-size: 28px;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.5px;
}

.subtitle {
  font-size: 14px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.subtitle strong {
  color: var(--color-primary);
  font-weight: 600;
}

/* Bento Grid */
.bento {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: 200px;
  gap: 16px;
}

.card {
  background: var(--glass-bg);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  padding: 22px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-shadow: var(--shadow-sm);
  transition: transform var(--duration-base) var(--ease-emphasis), background var(--duration-base), box-shadow var(--duration-base), border-color var(--duration-base);
  overflow: hidden;
  position: relative;
}

.card:hover {
  background: var(--glass-bg-hover);
  box-shadow: var(--shadow-md), var(--shadow-glow);
  transform: translateY(-2px);
  border-color: rgba(15, 143, 131, 0.24);
}

.card-hero {
  background:
    radial-gradient(circle at 84% 12%, rgba(255,255,255,0.56), transparent 26%),
    linear-gradient(135deg, rgba(15, 143, 131, 0.16), rgba(59, 130, 246, 0.1));
  border-color: rgba(15, 143, 131, 0.25);
}

.card-wide {
  grid-column: span 2;
  grid-row: span 2;
}

.card-recent-exercise {
  grid-column: span 2;
  min-height: 304px;
  justify-content: flex-start;
  gap: 14px;
}

.card-diary {
  grid-column: span 2;
  grid-row: span 2;
  min-height: 304px;
  justify-content: flex-start;
  gap: 14px;
}

.card-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.card-value {
  font-family: var(--font-heading);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
}

.card-value small {
  font-size: 14px;
  font-weight: 400;
}

.trend-value.down { color: var(--color-success); }
.trend-value.up { color: var(--color-warning); }
.trend-value.flat { color: var(--color-text); }

/* Hero card */
.hero-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.hero-num {
  font-family: var(--font-heading);
  font-size: 52px;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1;
  letter-spacing: -2px;
}

.hero-unit {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-muted);
}

.hero-change {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.good { color: var(--color-success); }
.warn { color: var(--color-warning); }

/* BMI gauge */
.bmi-gauge { margin-top: 8px; }

.bmi-track {
  position: relative;
  height: 6px;
  background: linear-gradient(to right, #60a5fa, #34d399, #fbbf24, #f87171);
  border-radius: 4px;
}

.bmi-indicator {
  position: absolute;
  top: -4px;
  width: 12px;
  height: 14px;
  border-radius: 4px;
  border: 2px solid var(--color-surface);
  transform: translateX(-50%);
  transition: left 0.6s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.bmi-chips {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}

.bmi-chip {
  font-size: 10px;
  color: var(--color-text-muted);
  padding: 1px 6px;
  border-radius: 4px;
  transition: all 0.3s;
}

.bmi-chip.active {
  background: var(--color-primary);
  color: #fff;
  font-weight: 600;
}

/* Progress */
.progress-bar {
  height: 6px;
  background: var(--color-border-light);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
  border-radius: 4px;
  transition: width 0.7s var(--ease-emphasis);
}

/* Chart */
.chart-box { flex: 1; min-height: 0; }

.empty-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 14px;
  gap: 8px;
}

.empty-icon {
  width: 36px;
  height: 36px;
  color: var(--color-primary);
  opacity: 0.78;
}

/* Monthly diary heatmap */
.diary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.diary-title {
  color: var(--color-text);
  font-family: var(--font-heading);
  font-size: 20px;
  font-weight: 750;
  min-width: 116px;
  text-align: center;
}

.diary-nav {
  margin-top: 4px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.diary-nav-btn {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.34);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), border-color var(--duration-base), opacity var(--duration-base);
}

.diary-nav-btn:hover:not(:disabled),
.diary-nav-btn:focus-visible {
  background: rgba(15, 143, 131, 0.09);
  border-color: rgba(15, 143, 131, 0.24);
  color: var(--color-primary);
  outline: none;
  transform: translateY(-1px);
}

.diary-nav-btn:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.diary-nav-icon {
  width: 18px;
  height: 18px;
}

.diary-legend {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--color-text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.diary-legend i {
  width: 12px;
  height: 12px;
  border-radius: 4px;
  border: 1px solid var(--color-border-light);
}

.diary-weekdays,
.diary-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
}

.diary-weekdays span {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 650;
  text-align: center;
}

.diary-weekdays.loading,
.diary-grid.loading {
  opacity: 0.56;
  pointer-events: none;
}

.diary-cell {
  position: relative;
  height: 44px;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--color-border-light);
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.28);
  transition: transform var(--duration-fast) var(--ease-standard), border-color var(--duration-base), background var(--duration-base), box-shadow var(--duration-base);
}

.diary-cell:not(.blank) {
  cursor: default;
}

.diary-cell:not(.blank):hover,
.diary-cell:not(.blank):focus-visible {
  z-index: 5;
  transform: translateY(-2px);
  border-color: rgba(15, 143, 131, 0.38);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
  outline: none;
}

.diary-cell:not(.blank):hover::after,
.diary-cell:not(.blank):focus-visible::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  width: max-content;
  max-width: min(280px, 80vw);
  padding: 9px 10px;
  border-radius: 10px;
  background: rgba(16, 32, 31, 0.94);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
  text-align: left;
  white-space: normal;
  transform: translateX(-50%);
  box-shadow: var(--shadow-md);
  pointer-events: none;
}

.diary-cell.blank {
  border-color: transparent;
  background: transparent;
}

.diary-cell.today {
  box-shadow: inset 0 0 0 2px var(--color-primary);
}

.diary-cell.level-1,
.diary-legend .level-1 { background: rgba(15, 143, 131, 0.16); }

.diary-cell.level-2,
.diary-legend .level-2 { background: rgba(15, 143, 131, 0.32); }

.diary-cell.level-3,
.diary-legend .level-3 { background: rgba(15, 143, 131, 0.52); color: #fff; }

.diary-cell.level-4,
.diary-legend .level-4 { background: rgba(15, 143, 131, 0.78); color: #fff; }

/* Recent exercise */
.exercise-mini-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exercise-mini-row {
  min-height: 44px;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.32);
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), border-color var(--duration-base);
}

.exercise-mini-row:hover {
  background: rgba(15, 143, 131, 0.07);
  border-color: rgba(15, 143, 131, 0.18);
  transform: translateX(3px);
}

.exercise-mini-row:active {
  transform: translateX(1px) scale(0.99);
}

.exercise-mini-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: var(--color-primary);
  background: rgba(15, 143, 131, 0.1);
}

.mini-icon {
  width: 16px;
  height: 16px;
}

.exercise-mini-main {
  min-width: 0;
}

.exercise-mini-main strong,
.exercise-mini-main span {
  display: block;
}

.exercise-mini-main strong {
  color: var(--color-text);
  font-size: 14px;
}

.exercise-mini-main span,
.exercise-mini-stat span,
.mini-empty {
  color: var(--color-text-muted);
  font-size: 11px;
}

.exercise-mini-stat {
  text-align: right;
}

.exercise-mini-stat strong {
  display: block;
  color: var(--color-primary);
  font-size: 15px;
}

.mini-empty {
  min-height: 120px;
  display: flex;
  align-items: center;
}

/* Utils */
.muted-text { color: var(--color-text-muted); }
.small { font-size: 12px; }
.ml-1 { margin-left: 4px; }

/* Responsive */
@media (max-width: 1024px) {
  .bento { grid-template-columns: repeat(2, 1fr); }
  .card-wide { grid-column: span 2; }
}
@media (max-width: 640px) {
  .bento { grid-template-columns: 1fr; }
  .card-wide,
  .card-diary,
  .card-recent-exercise { grid-column: span 1; }
  .card-diary,
  .card-recent-exercise { min-height: 304px; }
  .card-diary { grid-row: span 2; }
  .diary-cell { height: 40px; }
  .card-hero { order: 1; }
  .card-wide { order: 2; }
  .card-diary { order: 3; }
  .card-trend-summary { order: 4; }
  .card-calories { order: 5; }
  .card-today-exercise { order: 6; }
  .card-recent-exercise { order: 7; }
  .diary-head { flex-direction: column; }
  .hero-num { font-size: 40px; }
  .greeting { font-size: 22px; }
}

[data-theme="dark"] .exercise-mini-row {
  background: rgba(9, 22, 22, 0.38);
}
</style>
