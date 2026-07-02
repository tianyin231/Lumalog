<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Bot, ClipboardList, Image, Plus, RotateCcw, X } from 'lucide-vue-next'

interface FoodItem { name: string; calories: number; portion?: string; protein_g?: number; carbs_g?: number; fat_g?: number }
interface FoodRecord {
  id: number; meal_type: string; image_path: string | null; food_items: FoodItem[]
  total_calories: number; protein_g: number | null; carbs_g: number | null; fat_g: number | null
  note: string | null; recorded_at: string
}

const records = ref<FoodRecord[]>([])
const loading = ref(true)
const activeTab = ref<'list' | 'upload'>('list')
const mealType = ref('lunch')
const note = ref('')
const recordedAt = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const analyzing = ref(false)
const previewUrl = ref<string | null>(null)
const analysisResult = ref<any>(null)
const editingItems = ref<FoodItem[]>([])
const dragActive = ref(false)

const mealTypes = [
  { v: 'breakfast', l: '早餐' },
  { v: 'lunch', l: '午餐' },
  { v: 'dinner', l: '晚餐' },
  { v: 'snack', l: '零食' },
]

onMounted(() => {
  recordedAt.value = getLocalDateTimeValue()
  fetchRecords()
})

function getLocalDateTimeValue(date = new Date()) {
  const offsetMs = date.getTimezoneOffset() * 60 * 1000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs = 60000) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    window.clearTimeout(timeout)
  }
}

async function fetchRecords() {
  loading.value = true
  try { records.value = await (await fetch('/api/food/?days=7')).json() }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}

async function handleFileUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  await analyzeSelectedFile(file)
}

async function handleFileDrop(e: DragEvent) {
  dragActive.value = false
  const file = e.dataTransfer?.files?.[0]
  await analyzeSelectedFile(file)
}

async function analyzeSelectedFile(file?: File) {
  if (!file) return
  if (!file.type.startsWith('image/')) {
    alert('请上传图片文件')
    return
  }
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(file)
  analyzing.value = true
  analysisResult.value = null
  const form = new FormData()
  form.append('image', file)
  form.append('meal_type', mealType.value)
  if (recordedAt.value) form.append('recorded_at', new Date(recordedAt.value).toISOString())
  try {
    const res = await fetchWithTimeout('/api/ai/analyze-food', { method: 'POST', body: form })
    if (!res.ok) {
      const message = await res.text()
      throw new Error(message || 'Analysis failed')
    }
    analysisResult.value = await res.json()
    editingItems.value = [...(analysisResult.value?.food_items || [])]
  } catch (e) {
    console.error(e)
    const message = e instanceof DOMException && e.name === 'AbortError'
      ? 'AI分析超时，请检查模型、Base URL 或网络'
      : e instanceof Error ? e.message : 'AI分析失败'
    alert(message)
  }
  finally { analyzing.value = false }
}

function addItem() { editingItems.value.push({ name: '', calories: 0 }) }
function removeItem(i: number) { editingItems.value.splice(i, 1) }

function updateItemCalories() {
  if (!analysisResult.value) return
  analysisResult.value.total_calories = editingItems.value.reduce((s: number, i: FoodItem) => s + (i.calories || 0), 0)
  analysisResult.value.total_protein = editingItems.value.reduce((s: number, i: FoodItem) => s + (i.protein_g || 0), 0)
  analysisResult.value.total_carbs = editingItems.value.reduce((s: number, i: FoodItem) => s + (i.carbs_g || 0), 0)
  analysisResult.value.total_fat = editingItems.value.reduce((s: number, i: FoodItem) => s + (i.fat_g || 0), 0)
}

async function saveAnalysis() {
  if (!analysisResult.value) return
  updateItemCalories()
  const body = {
    meal_type: mealType.value,
    image_path: analysisResult.value.image_path || null,
    food_items: editingItems.value,
    total_calories: analysisResult.value.total_calories || 0,
    protein_g: analysisResult.value.total_protein,
    carbs_g: analysisResult.value.total_carbs,
    fat_g: analysisResult.value.total_fat,
    note: note.value || analysisResult.value.analysis_note || null,
    recorded_at: recordedAt.value ? new Date(recordedAt.value).toISOString() : null,
  }
  try {
    const res = await fetch('/api/food/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error('Save failed')
    resetUpload()
    await fetchRecords()
    activeTab.value = 'list'
  } catch (e) { console.error(e); alert('保存失败') }
}

function resetUpload() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  analysisResult.value = null
  editingItems.value = []
  dragActive.value = false
  note.value = ''
  recordedAt.value = getLocalDateTimeValue()
  if (fileInput.value) fileInput.value.value = ''
}

async function deleteRecord(id: number) {
  await fetch(`/api/food/${id}`, { method: 'DELETE' })
  await fetchRecords()
}

function fmtDate(s: string) {
  return new Date(s).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit' })
}

function mealLabel(t: string) { return mealTypes.find(m => m.v === t)?.l || t }
</script>

<template>
  <div class="page">
    <!-- Tabs -->
    <div class="tabs-row">
      <button class="tab pressable" :class="{ on: activeTab === 'list' }" @click="activeTab = 'list'"><ClipboardList class="tab-icon" />饮食记录</button>
      <button class="tab pressable" :class="{ on: activeTab === 'upload' }" @click="activeTab = 'upload'"><Bot class="tab-icon" />AI 拍照识别</button>
    </div>

    <!-- Upload Tab -->
    <div v-if="activeTab === 'upload'" class="card motion-card">
      <h3 class="card-title">AI 食物热量识别</h3>
      <p class="card-desc">上传食物照片，AI 自动识别并估算热量</p>

      <div class="meal-select">
        <button v-for="m in mealTypes" :key="m.v" class="meal-chip pressable" :class="{ on: mealType === m.v }" @click="mealType = m.v">{{ m.l }}</button>
      </div>

      <div class="field date-field">
        <label class="field-label">记录时间</label>
        <input v-model="recordedAt" type="datetime-local" class="input-sm" />
      </div>

      <!-- Upload Zone -->
      <div
        v-if="!previewUrl"
        class="upload-zone"
        :class="{ 'drag-over': dragActive }"
        role="button"
        tabindex="0"
        @click="fileInput?.click()"
        @keydown.enter.prevent="fileInput?.click()"
        @keydown.space.prevent="fileInput?.click()"
        @dragenter.prevent="dragActive = true"
        @dragover.prevent="dragActive = true"
        @dragleave.prevent="dragActive = false"
        @drop.prevent="handleFileDrop"
      >
        <input ref="fileInput" type="file" accept="image/*" hidden @change="handleFileUpload" />
        <div class="upload-icon-circle">
          <Image class="upload-icon" />
        </div>
        <p class="upload-text">拖拽图片到这里，或点击上传</p>
        <p class="upload-hint">支持 JPG、PNG、WebP · 手机可拍照或选择文件</p>
      </div>

      <!-- Preview + Result -->
      <div v-if="previewUrl" class="preview-grid">
        <div>
          <img :src="previewUrl" alt="预览" class="preview-img" />
          <button class="btn-ghost pressable" @click="resetUpload"><RotateCcw class="btn-icon" />重新选择</button>
        </div>

        <div v-if="analyzing" class="loading-box">
          <div class="spinner" />
          <p>AI 正在分析食物...</p>
        </div>

        <div v-else-if="analysisResult" class="result-box">
          <div class="macro-grid">
            <div class="macro"><span class="mv">{{ analysisResult.total_calories }}</span><span class="ml">kcal 总热量</span></div>
            <div class="macro"><span class="mv">{{ analysisResult.total_protein ?? '--' }}g</span><span class="ml">蛋白质</span></div>
            <div class="macro"><span class="mv">{{ analysisResult.total_carbs ?? '--' }}g</span><span class="ml">碳水</span></div>
            <div class="macro"><span class="mv">{{ analysisResult.total_fat ?? '--' }}g</span><span class="ml">脂肪</span></div>
          </div>

          <div class="edit-list">
            <div v-for="(item, i) in editingItems" :key="i" class="edit-row">
              <input v-model="item.name" placeholder="食物" class="input-sm flex-1" @change="updateItemCalories" />
              <input v-model.number="item.calories" type="number" placeholder="kcal" class="input-sm w-20" @change="updateItemCalories" />
              <button class="rm-btn" @click="removeItem(i)" aria-label="删除食物"><X class="x-icon" /></button>
            </div>
            <button class="add-btn pressable" @click="addItem"><Plus class="btn-icon" />添加食物</button>
          </div>

          <p class="ai-note" v-if="analysisResult.analysis_note">{{ analysisResult.analysis_note }}</p>

          <div class="save-row">
            <input v-model="note" placeholder="备注（可选）" class="input-sm flex-1" />
            <button class="btn-teal pressable" @click="saveAnalysis">确认保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- List Tab -->
    <div v-if="activeTab === 'list'" class="card motion-card">
      <h3 class="card-title">近7天饮食记录</h3>
      <div v-if="loading" class="center-text">加载中...</div>
      <div v-else-if="records.length === 0" class="empty-area">
        <p class="empty-title">还没有饮食记录</p>
        <p class="empty-desc">切换到「AI 拍照识别」来录入第一餐</p>
      </div>
      <div v-else class="food-list">
        <div v-for="r in records" :key="r.id" class="food-row">
          <img v-if="r.image_path" :src="r.image_path" class="food-thumb" />
          <div v-else class="food-thumb-empty">{{ mealLabel(r.meal_type).slice(0,2) }}</div>
          <div class="flex-1 min-w-0">
            <div class="food-head">
              <span class="badge">{{ mealLabel(r.meal_type) }}</span>
              <strong>{{ r.total_calories }} kcal</strong>
            </div>
            <div class="food-sub" v-if="r.food_items?.length">{{ r.food_items.map(i => i.name).join('、') }}</div>
            <div class="food-time">{{ fmtDate(r.recorded_at) }}</div>
          </div>
          <button class="rm-btn" @click="deleteRecord(r.id)" aria-label="删除饮食记录"><X class="x-icon" /></button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 860px; margin: 0 auto; }

/* Tabs */
.tabs-row {
  display: flex;
  gap: 4px;
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 4px;
  margin-bottom: 20px;
}

.tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  font-family: var(--font-body);
  color: var(--color-text-secondary);
  cursor: pointer;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), color var(--duration-base), box-shadow var(--duration-base);
}

.tab.on {
  background: var(--glass-bg-strong);
  color: var(--color-primary);
  font-weight: 700;
  box-shadow: var(--shadow-xs);
}

.tab-icon {
  width: 17px;
  height: 17px;
}

/* Card */
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
  background: var(--glass-bg-hover);
  border-color: rgba(15, 143, 131, 0.22);
  box-shadow: var(--shadow-md), var(--shadow-glow);
}

.card-title {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.card-desc { font-size: 13px; color: var(--color-text-muted); margin-bottom: 16px; }

/* Meal select */
.meal-select { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }

.date-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 16px;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meal-chip {
  padding: 8px 16px;
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  background: var(--glass-bg);
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--color-text-secondary);
  cursor: pointer;
  min-height: 40px;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), border-color var(--duration-base), color var(--duration-base);
}

.meal-chip.on {
  border-color: var(--color-primary);
  background: rgba(13, 148, 136, 0.12);
  color: var(--color-primary);
  font-weight: 600;
}

/* Upload zone */
.upload-zone {
  border: 2px dashed var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 60px 20px;
  text-align: center;
  cursor: pointer;
  transition: transform var(--duration-base) var(--ease-emphasis), background var(--duration-base), border-color var(--duration-base), box-shadow var(--duration-base);
}

.upload-zone:hover {
  border-color: var(--color-primary);
  background: rgba(13, 148, 136, 0.04);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.upload-zone.drag-over {
  border-color: var(--color-primary);
  background: rgba(13, 148, 136, 0.08);
  box-shadow: var(--shadow-sm), var(--shadow-glow);
  transform: translateY(-2px);
}

.upload-icon-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(13, 148, 136, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  color: var(--color-primary);
}

.upload-icon {
  width: 36px;
  height: 36px;
}

.upload-text { font-size: 16px; font-weight: 600; color: var(--color-text); }
.upload-hint { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }

/* Preview */
.preview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 640px) { .preview-grid { grid-template-columns: 1fr; } }

.preview-img { width: 100%; border-radius: var(--radius-lg); max-height: 300px; object-fit: cover; }

.btn-ghost {
  margin-top: 12px; padding: 8px 16px; border: 1px solid var(--glass-border);
  background: var(--glass-bg); border-radius: 10px; font-size: 13px;
  color: var(--color-text-secondary); cursor: pointer; font-family: var(--font-body);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 40px;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), border-color var(--duration-base);
}

.btn-ghost:hover { background: var(--glass-bg-hover); }

/* Loading */
.loading-box {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 20px; gap: 16px; color: var(--color-text-muted);
}

.spinner {
  width: 36px; height: 36px; border: 3px solid var(--color-border);
  border-top-color: var(--color-primary); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Macro */
.macro-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-bottom: 16px; }

.macro {
  text-align: center; padding: 12px 4px;
  background: var(--glass-bg); border-radius: 12px;
}

.mv { display: block; font-family: var(--font-heading); font-size: 22px; font-weight: 700; color: var(--color-primary); }
.ml { font-size: 10px; color: var(--color-text-muted); }

/* Edit items */
.edit-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }

.edit-row { display: flex; gap: 6px; align-items: center; }

.input-sm {
  padding: 6px 10px; border: 1px solid var(--glass-border); border-radius: 8px;
  font-size: 13px; font-family: var(--font-body); background: var(--glass-bg);
  color: var(--color-text); outline: none;
  min-height: 36px;
}

.input-sm:focus { border-color: var(--color-primary); }

.w-20 { width: 80px; }
.flex-1 { flex: 1; }
.min-w-0 { min-width: 0; }

.rm-btn {
  background: none; border: none; color: var(--color-text-muted);
  cursor: pointer; padding: 6px; border-radius: 8px; transition: transform var(--duration-fast), background var(--duration-base), color var(--duration-base);
  min-width: 34px; min-height: 34px; display: inline-flex; align-items: center; justify-content: center;
}

.rm-btn:hover { color: var(--color-danger); background: rgba(239,68,68,0.08); transform: scale(1.08); }

.x-icon { width: 16px; height: 16px; }

.add-btn {
  background: none; border: 1px dashed var(--glass-border); border-radius: 8px;
  padding: 6px; font-size: 12px; color: var(--color-text-muted); cursor: pointer;
  font-family: var(--font-body); transition: transform var(--duration-fast), border-color var(--duration-base), color var(--duration-base);
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}

.add-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }

.ai-note { font-size: 12px; color: var(--color-text-muted); padding: 8px; background: var(--glass-bg); border-radius: 8px; margin-bottom: 12px; }

.save-row { display: flex; gap: 10px; }

.btn-teal {
  padding: 10px 24px; border: none; border-radius: 12px; font-size: 14px; font-weight: 700;
  font-family: var(--font-body); background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff; cursor: pointer;
  transition: transform var(--duration-fast), box-shadow var(--duration-base), filter var(--duration-base);
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.25);
  white-space: nowrap;
}

.btn-teal:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(13, 148, 136, 0.35); }

/* Food list */
.food-list { display: flex; flex-direction: column; }

.food-row {
  display: flex; align-items: center; gap: 14px; padding: 14px 0;
  border-bottom: 1px solid var(--color-border-light);
  border-radius: 14px;
  transition: transform var(--duration-fast), background var(--duration-base);
}

.food-row:last-child { border-bottom: none; }
.food-row:hover { background: rgba(15, 143, 131, 0.05); transform: translateX(4px); }

.btn-icon { width: 15px; height: 15px; }

.food-thumb { width: 52px; height: 52px; border-radius: 14px; object-fit: cover; flex-shrink: 0; }

.food-thumb-empty {
  width: 52px; height: 52px; border-radius: 14px; background: rgba(13, 148, 136, 0.08);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: var(--color-primary); flex-shrink: 0;
}

.food-head { display: flex; align-items: center; gap: 8px; }
.badge { font-size: 11px; padding: 2px 8px; background: rgba(13, 148, 136, 0.1); color: var(--color-primary); border-radius: 6px; font-weight: 600; }
.food-sub { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.food-time { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }

.empty-area { padding: 48px 20px; text-align: center; }
.empty-title { font-weight: 600; color: var(--color-text-muted); }
.empty-desc { font-size: 13px; color: var(--color-text-muted); margin-top: 4px; }
.center-text { text-align: center; padding: 32px; color: var(--color-text-muted); }
</style>
