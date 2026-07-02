<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'
import { Camera, Check, Coins, ExternalLink, KeyRound, Link, ListChecks, LogIn, LogOut, Mail, Moon, RefreshCw, ShieldCheck, Smartphone, Sun, Sunset, UserRound, Zap } from 'lucide-vue-next'

const store = useAppStore()

interface Settings {
  nickname: string; height_cm: number; gender: string; birth_year: number
  target_weight_kg: number; weekly_loss_rate_kg: number; daily_calorie_target: number
  theme_mode: 'light' | 'dark' | 'auto'; sunset_lat: number | null; sunset_lng: number | null
  mi_fit_enabled: boolean; openai_base_url: string; openai_model: string
}

const settings = ref<Settings>({
  nickname: '我', height_cm: 170, gender: 'male', birth_year: 1990,
  target_weight_kg: 65, weekly_loss_rate_kg: 0.5, daily_calorie_target: 2000,
  theme_mode: 'auto', sunset_lat: null, sunset_lng: null,
  mi_fit_enabled: false, openai_base_url: 'https://api.openai.com/v1', openai_model: 'gpt-4o',
})

const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const testingMi = ref(false)
const syncingMi = ref(false)
const testingAi = ref(false)
const loadingModels = ref(false)
const checkingBalance = ref(false)
const apiSaving = ref(false)
const miMessage = ref('')
const aiMessage = ref('')
const aiModels = ref<string[]>([])
const aiBalance = ref('')
const apiKey = ref('')
const accountSaving = ref(false)
const accountMessage = ref('')
const accountError = ref('')
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const passwordForm = ref({ current_password: '', new_password: '', confirm_password: '' })
const passwordSaving = ref(false)
const passwordMessage = ref('')
const passwordError = ref('')
const miStatus = ref<any>({ authenticated: false })
const miLogin = ref({ email: '', password: '' })
const miSessionId = ref('')
const miVerificationUrl = ref('')
const miVerificationOpenedBrowser = ref(false)
const miAutoPolling = ref(false)
let miAutoPollTimer: number | null = null
let miAutoPollAttempts = 0
let miAutoPollInFlight = false

const accountInitial = computed(() => {
  const name = settings.value.nickname || store.authUser?.email || 'L'
  return name.trim().slice(0, 1).toUpperCase()
})
const avatarSrc = computed(() => store.authUser?.avatar_path || '')

const themeOptions = [
  { v: 'light', l: '浅色', d: '始终使用浅色模式', icon: Sun },
  { v: 'dark', l: '深色', d: '始终使用深色模式', icon: Moon },
  { v: 'auto', l: '日落自动', d: '日出浅色，日落后切换深色', icon: Sunset },
]

onMounted(async () => {
  try {
    const d = await (await fetch('/api/settings/')).json()
    Object.assign(settings.value, d)
    store.settings.nickname = d.nickname
    store.settings.heightCm = d.height_cm
    store.settings.targetWeightKg = d.target_weight_kg
    store.settings.dailyCalorieTarget = d.daily_calorie_target
  } catch (e) { console.error(e) }
  finally {
    await loadMiStatus()
    loading.value = false
  }
})

onUnmounted(() => {
  stopMiAutoPoll()
})

async function saveProfile() {
  saving.value = true; saved.value = false
  try {
    const body: any = {
      nickname: settings.value.nickname, height_cm: settings.value.height_cm,
      gender: settings.value.gender, birth_year: settings.value.birth_year,
      target_weight_kg: settings.value.target_weight_kg,
      weekly_loss_rate_kg: settings.value.weekly_loss_rate_kg,
      daily_calorie_target: settings.value.daily_calorie_target,
      mi_fit_enabled: settings.value.mi_fit_enabled,
    }
    await fetch('/api/settings/', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    store.settings.nickname = settings.value.nickname
    store.settings.heightCm = settings.value.height_cm
    store.settings.targetWeightKg = settings.value.target_weight_kg
    store.settings.dailyCalorieTarget = settings.value.daily_calorie_target
    saved.value = true
    setTimeout(() => saved.value = false, 3000)
  } catch (e) { console.error(e) }
  finally { saving.value = false }
}

async function saveApiConfig(showSuccess = true) {
  apiSaving.value = true
  if (showSuccess) aiMessage.value = ''
  try {
    const body: any = {
      openai_base_url: settings.value.openai_base_url,
      openai_model: settings.value.openai_model,
    }
    if (apiKey.value) body.openai_api_key = apiKey.value
    const res = await fetch('/api/settings/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'API 配置保存失败')
    }
    apiKey.value = ''
    if (showSuccess) aiMessage.value = 'API 配置已保存'
  } catch (e) {
    const message = e instanceof Error ? e.message : 'API 配置保存失败'
    if (showSuccess) aiMessage.value = message
    throw e
  } finally {
    apiSaving.value = false
  }
}

async function saveAccountProfile() {
  accountSaving.value = true
  accountMessage.value = ''
  accountError.value = ''
  try {
    const res = await fetch('/api/settings/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname: settings.value.nickname }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '昵称保存失败')
    }
    store.settings.nickname = settings.value.nickname
    accountMessage.value = '昵称已更新'
  } catch (e) {
    accountError.value = e instanceof Error ? e.message : '昵称保存失败'
  } finally {
    accountSaving.value = false
  }
}

async function uploadAvatar(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  accountMessage.value = ''
  accountError.value = ''
  if (!file.type.startsWith('image/')) {
    accountError.value = '请上传图片文件'
    return
  }
  avatarUploading.value = true
  try {
    const form = new FormData()
    form.append('avatar', file)
    const res = await fetch('/api/auth/avatar', { method: 'POST', body: form })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '头像上传失败')
    }
    store.setAuthUser(await res.json())
    accountMessage.value = '头像已更新'
  } catch (e) {
    accountError.value = e instanceof Error ? e.message : '头像上传失败'
  } finally {
    avatarUploading.value = false
    if (avatarInput.value) avatarInput.value.value = ''
  }
}

async function changePassword() {
  passwordMessage.value = ''
  passwordError.value = ''
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  passwordSaving.value = true
  try {
    const res = await fetch('/api/auth/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: passwordForm.value.current_password,
        new_password: passwordForm.value.new_password,
      }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '密码修改失败')
    }
    passwordForm.value = { current_password: '', new_password: '', confirm_password: '' }
    passwordMessage.value = '密码已更新'
  } catch (e) {
    passwordError.value = e instanceof Error ? e.message : '密码修改失败'
  } finally {
    passwordSaving.value = false
  }
}

async function loadMiStatus() {
  try {
    miStatus.value = await (await fetch('/api/mi-fit/status')).json()
  } catch (e) {
    console.error(e)
  }
}

async function loadAiModels() {
  loadingModels.value = true
  aiMessage.value = ''
  try {
    await saveApiConfig(false)
    const data = await (await fetch('/api/ai/models')).json()
    aiModels.value = data.models || []
    aiMessage.value = data.message || `已读取 ${aiModels.value.length} 个模型`
  } catch (e) {
    console.error(e)
    aiMessage.value = e instanceof Error ? e.message : '获取模型失败'
  } finally {
    loadingModels.value = false
  }
}

async function testAi() {
  testingAi.value = true
  aiMessage.value = ''
  try {
    await saveApiConfig(false)
    const data = await (await fetch('/api/ai/test', { method: 'POST' })).json()
    if (data.models?.length) aiModels.value = data.models
    aiMessage.value = data.message || (data.ok ? '连接成功' : '连接失败')
  } catch (e) {
    console.error(e)
    aiMessage.value = e instanceof Error ? e.message : '测试失败'
  } finally {
    testingAi.value = false
  }
}

async function checkBalance() {
  checkingBalance.value = true
  aiBalance.value = ''
  aiMessage.value = ''
  try {
    await saveApiConfig(false)
    const data = await (await fetch('/api/ai/balance')).json()
    aiMessage.value = data.message || ''
    aiBalance.value = data.data ? JSON.stringify(data.data, null, 2) : ''
  } catch (e) {
    console.error(e)
    aiMessage.value = e instanceof Error ? e.message : '余额查询失败'
  } finally {
    checkingBalance.value = false
  }
}

async function testMiFit() {
  testingMi.value = true
  miMessage.value = ''
  try {
    const res = await fetch('/api/mi-fit/test', { method: 'POST' })
    const data = await res.json()
    miMessage.value = data.message || (data.ok ? '连接成功' : '连接失败')
  } catch (e) {
    console.error(e)
    miMessage.value = '连接失败，请检查后端服务'
  } finally {
    testingMi.value = false
  }
}

async function loginMiFit() {
  testingMi.value = true
  miMessage.value = ''
  miSessionId.value = ''
  miVerificationUrl.value = ''
  miVerificationOpenedBrowser.value = false
  stopMiAutoPoll()
  try {
    const res = await fetch('/api/mi-fit/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(miLogin.value),
    })
    const data = await res.json()
    miMessage.value = data.message || ''
    if (data.ok) {
      miLogin.value.password = ''
      await loadMiStatus()
    }
    if (data.status === 'verification_required') {
      miSessionId.value = data.session_id
      miVerificationUrl.value = data.verification_url
      miVerificationOpenedBrowser.value = Boolean(data.opened_browser)
      if (!data.opened_browser) {
        window.open(data.verification_url, '_blank', 'noopener,noreferrer')
      } else {
        startMiAutoPoll()
      }
    }
  } catch (e) {
    console.error(e)
    miMessage.value = '登录失败，请检查后端服务'
  } finally {
    testingMi.value = false
  }
}

async function continueMiLogin(silent = false) {
  if (!miSessionId.value) return
  if (!silent) {
    testingMi.value = true
    miMessage.value = ''
  }
  try {
    const res = await fetch('/api/mi-fit/login/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: miSessionId.value }),
    })
    const data = await res.json()
    if (!silent || data.ok || data.status !== 'verification_required') {
      miMessage.value = data.message || ''
    }
    if (data.ok) {
      stopMiAutoPoll()
      miSessionId.value = ''
      miVerificationUrl.value = ''
      miVerificationOpenedBrowser.value = false
      miLogin.value.password = ''
      await loadMiStatus()
    }
    if (data.status === 'verification_required') {
      miSessionId.value = data.session_id
      miVerificationUrl.value = data.verification_url
      miVerificationOpenedBrowser.value = Boolean(data.opened_browser)
      if (!data.opened_browser) {
        stopMiAutoPoll()
        window.open(data.verification_url, '_blank', 'noopener,noreferrer')
      }
    }
  } catch (e) {
    console.error(e)
    if (!silent) miMessage.value = '继续登录失败'
  } finally {
    if (!silent) testingMi.value = false
  }
}

function startMiAutoPoll() {
  stopMiAutoPoll()
  miAutoPolling.value = true
  miAutoPollAttempts = 0
  miAutoPollTimer = window.setInterval(async () => {
    if (!miSessionId.value) {
      stopMiAutoPoll()
      return
    }
    if (miAutoPollInFlight) return
    miAutoPollAttempts += 1
    if (miAutoPollAttempts > 120) {
      stopMiAutoPoll()
      miMessage.value = '自动确认超时，请确认验证窗口已完成后手动点击“我已完成验证”'
      return
    }
    miAutoPollInFlight = true
    try {
      await continueMiLogin(true)
    } finally {
      miAutoPollInFlight = false
    }
  }, 2500)
}

function stopMiAutoPoll() {
  if (miAutoPollTimer !== null) {
    window.clearInterval(miAutoPollTimer)
    miAutoPollTimer = null
  }
  miAutoPolling.value = false
  miAutoPollAttempts = 0
  miAutoPollInFlight = false
}

async function logoutMiFit() {
  testingMi.value = true
  miMessage.value = ''
  try {
    const data = await (await fetch('/api/mi-fit/logout', { method: 'POST' })).json()
    miMessage.value = data.message || '已退出'
    stopMiAutoPoll()
    miSessionId.value = ''
    miVerificationUrl.value = ''
    miVerificationOpenedBrowser.value = false
    await loadMiStatus()
  } catch (e) {
    console.error(e)
    miMessage.value = '退出失败'
  } finally {
    testingMi.value = false
  }
}

async function syncMiFit() {
  syncingMi.value = true
  miMessage.value = ''
  try {
    const res = await fetch('/api/mi-fit/sync?days=30', { method: 'POST' })
    const data = await res.json()
    miMessage.value = data.message || '同步完成'
  } catch (e) {
    console.error(e)
    miMessage.value = '同步失败，请检查 Token 或网络'
  } finally {
    syncingMi.value = false
  }
}

async function handleThemeChange(mode: string) {
  settings.value.theme_mode = mode as any
  store.setTheme(mode as any)
  await fetch('/api/settings/', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ theme_mode: mode }) })
}
</script>

<template>
  <div class="page">
    <div class="cards-stack">
      <!-- Account -->
      <div class="card account-card motion-card" style="animation-delay: 0ms">
        <div class="account-head">
          <button
            class="account-avatar-button"
            type="button"
            aria-label="更换头像"
            :disabled="avatarUploading"
            @click="avatarInput?.click()"
          >
            <img v-if="avatarSrc" :src="avatarSrc" alt="用户头像" class="account-avatar-img" />
            <span v-else class="account-avatar-initial">{{ accountInitial }}</span>
            <span class="avatar-camera">
              <Camera class="avatar-camera-icon" />
            </span>
          </button>
          <input ref="avatarInput" type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden @change="uploadAvatar" />
          <div class="account-title">
            <h3 class="card-title">账号信息</h3>
            <p>{{ store.authUser?.email || '未登录' }}</p>
          </div>
        </div>

        <div class="account-grid">
          <form class="account-panel" @submit.prevent="saveAccountProfile">
            <div class="panel-title">
              <UserRound class="panel-icon" />
              <span>基础资料</span>
            </div>
            <div class="field">
              <label class="f-label">邮箱</label>
              <div class="readonly-field">
                <Mail class="readonly-icon" />
                <span>{{ store.authUser?.email || '--' }}</span>
              </div>
            </div>
            <div class="field">
              <label class="f-label">昵称</label>
              <input v-model.trim="settings.nickname" class="input-g" autocomplete="nickname" />
            </div>
            <button class="btn-secondary pressable" type="submit" :disabled="accountSaving">
              <Check class="btn-icon" />
              {{ accountSaving ? '保存中...' : '保存昵称' }}
            </button>
            <p v-if="accountMessage" class="status-msg compact">{{ accountMessage }}</p>
            <p v-if="accountError" class="status-msg error compact">{{ accountError }}</p>
          </form>

          <form class="account-panel" @submit.prevent="changePassword">
            <div class="panel-title">
              <KeyRound class="panel-icon" />
              <span>修改密码</span>
            </div>
            <input type="hidden" name="username" autocomplete="username" :value="store.authUser?.email || ''" />
            <div class="field">
              <label class="f-label">当前密码</label>
              <input v-model="passwordForm.current_password" type="password" class="input-g" autocomplete="current-password" required minlength="6" />
            </div>
            <div class="field">
              <label class="f-label">新密码</label>
              <input v-model="passwordForm.new_password" type="password" class="input-g" autocomplete="new-password" required minlength="6" />
            </div>
            <div class="field">
              <label class="f-label">确认新密码</label>
              <input v-model="passwordForm.confirm_password" type="password" class="input-g" autocomplete="new-password" required minlength="6" />
            </div>
            <button class="btn-secondary pressable" type="submit" :disabled="passwordSaving">
              <KeyRound class="btn-icon" />
              {{ passwordSaving ? '修改中...' : '修改密码' }}
            </button>
            <p v-if="passwordMessage" class="status-msg compact">{{ passwordMessage }}</p>
            <p v-if="passwordError" class="status-msg error compact">{{ passwordError }}</p>
          </form>
        </div>
      </div>

      <!-- Profile -->
      <div class="card motion-card" style="animation-delay: 60ms">
        <h3 class="card-title">个人资料</h3>
        <div class="form-grid">
          <div class="field">
            <label class="f-label">身高 (cm)</label>
            <input v-model.number="settings.height_cm" type="number" class="input-g" step="0.1" />
          </div>
          <div class="field">
            <label class="f-label">性别</label>
            <select v-model="settings.gender" class="input-g">
              <option value="male">男</option>
              <option value="female">女</option>
            </select>
          </div>
          <div class="field">
            <label class="f-label">出生年份</label>
            <input v-model.number="settings.birth_year" type="number" class="input-g" />
          </div>
        </div>
      </div>

      <!-- Goals -->
      <div class="card motion-card" style="animation-delay: 120ms">
        <h3 class="card-title">减重目标</h3>
        <div class="form-grid">
          <div class="field">
            <label class="f-label">目标体重 (kg)</label>
            <input v-model.number="settings.target_weight_kg" type="number" class="input-g" step="0.1" />
          </div>
          <div class="field">
            <label class="f-label">每周减重 (kg)</label>
            <input v-model.number="settings.weekly_loss_rate_kg" type="number" class="input-g" step="0.1" />
          </div>
          <div class="field">
            <label class="f-label">每日热量目标 (kcal)</label>
            <input v-model.number="settings.daily_calorie_target" type="number" class="input-g" />
          </div>
        </div>
      </div>

      <!-- Theme -->
      <div class="card motion-card" style="animation-delay: 180ms">
        <h3 class="card-title">主题设置</h3>
        <div class="theme-row">
          <button v-for="t in themeOptions" :key="t.v" class="theme-card pressable" :class="{ on: settings.theme_mode === t.v }" @click="handleThemeChange(t.v)">
            <component :is="t.icon" class="theme-icon" />
            <span class="t-label">{{ t.l }}</span>
            <span class="t-desc">{{ t.d }}</span>
          </button>
        </div>
      </div>

      <!-- API Keys -->
      <div class="card motion-card" style="animation-delay: 240ms">
        <div class="card-title-row">
          <h3 class="card-title">API 配置</h3>
          <Zap class="title-icon" />
        </div>
        <div class="form-stack">
          <div class="field">
            <label class="f-label">OpenAI API Key</label>
            <input v-model="apiKey" type="password" class="input-g" placeholder="sk-..." />
            <p class="hint">兼容 OpenAI / One API / New API / 常见中转格式。</p>
          </div>
          <div class="field">
            <label class="f-label">Base URL</label>
            <input v-model="settings.openai_base_url" class="input-g" placeholder="https://api.openai.com/v1" />
          </div>
          <div class="field">
            <label class="f-label">模型</label>
            <input v-model="settings.openai_model" list="ai-models" class="input-g" placeholder="gpt-4o" />
            <datalist id="ai-models">
              <option v-for="m in aiModels" :key="m" :value="m" />
            </datalist>
          </div>
          <div class="action-row">
            <button class="btn-secondary pressable" @click="saveApiConfig()" :disabled="apiSaving">
              <Check class="btn-icon" />
              {{ apiSaving ? '保存中...' : '保存配置' }}
            </button>
            <button class="btn-secondary pressable" @click="loadAiModels" :disabled="loadingModels">
              <ListChecks class="btn-icon" />
              {{ loadingModels ? '读取中...' : '读取模型' }}
            </button>
            <button class="btn-secondary pressable" @click="testAi" :disabled="testingAi">
              <Link class="btn-icon" />
              {{ testingAi ? '测试中...' : '测试连接' }}
            </button>
            <button class="btn-secondary pressable" @click="checkBalance" :disabled="checkingBalance">
              <Coins class="btn-icon" />
              {{ checkingBalance ? '查询中...' : '查余额' }}
            </button>
          </div>
          <p v-if="aiMessage" class="status-msg">{{ aiMessage }}</p>
          <pre v-if="aiBalance" class="balance-box">{{ aiBalance }}</pre>
        </div>
      </div>

      <!-- Mi Fit -->
      <div class="card motion-card" style="animation-delay: 300ms">
        <div class="card-title-row">
          <h3 class="card-title">小米运动健康同步</h3>
          <Smartphone class="title-icon" />
        </div>
        <div class="form-stack">
          <div class="mi-status-box" :class="{ authed: miStatus.authenticated }">
            <ShieldCheck class="mi-status-icon" />
            <span>
              <strong>{{ miStatus.authenticated ? '已连接小米运动健康' : '尚未连接小米运动健康' }}</strong>
              <small>{{ miStatus.authenticated ? `${miStatus.email || '当前账号'} · ${miStatus.updated_at || ''}` : '登录后可直接在网页拉取、解析并导入运动记录' }}</small>
            </span>
          </div>
          <label class="switch-row">
            <span>
              <strong>启用同步</strong>
              <small>开启后可从小米运动健康导入运动、步数、心率</small>
            </span>
            <input v-model="settings.mi_fit_enabled" type="checkbox" />
          </label>
          <div v-if="!miStatus.authenticated" class="form-grid">
            <div class="field">
              <label class="f-label">小米账号</label>
              <input v-model="miLogin.email" class="input-g" autocomplete="username" placeholder="手机号或邮箱" />
            </div>
            <div class="field">
              <label class="f-label">密码</label>
              <input v-model="miLogin.password" type="password" class="input-g" autocomplete="current-password" />
            </div>
          </div>
          <div class="action-row">
            <button v-if="!miStatus.authenticated" class="btn-secondary pressable" @click="loginMiFit" :disabled="testingMi || !miLogin.email || !miLogin.password">
              <LogIn class="btn-icon" />
              {{ testingMi ? '登录中...' : '登录小米' }}
            </button>
            <button v-if="miSessionId" class="btn-secondary pressable" @click="continueMiLogin()" :disabled="testingMi">
              <ExternalLink class="btn-icon" />
              {{ testingMi ? '确认中...' : miAutoPolling ? '自动确认中...' : '我已完成验证' }}
            </button>
            <button v-if="miStatus.authenticated" class="btn-secondary pressable" @click="testMiFit" :disabled="testingMi">
              <Link class="btn-icon" />
              {{ testingMi ? '测试中...' : '测试连接' }}
            </button>
            <button v-if="miStatus.authenticated" class="btn-secondary pressable" @click="syncMiFit" :disabled="syncingMi || !settings.mi_fit_enabled">
              <RefreshCw class="btn-icon" :class="{ spinning: syncingMi }" />
              {{ syncingMi ? '同步中...' : '同步最近30天' }}
            </button>
            <button v-if="miStatus.authenticated" class="btn-secondary pressable" @click="logoutMiFit" :disabled="testingMi">
              <LogOut class="btn-icon" />
              退出登录
            </button>
          </div>
          <a v-if="miVerificationUrl && !miVerificationOpenedBrowser" class="verify-link" :href="miVerificationUrl" target="_blank" rel="noreferrer">
            <ExternalLink class="btn-icon" />
            打开验证页面
          </a>
          <p v-if="miMessage" class="status-msg">{{ miMessage }}</p>
        </div>
      </div>

      <!-- Save -->
      <div class="save-row">
        <button class="btn-teal pressable" @click="saveProfile" :disabled="saving">
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
        <span v-if="saved" class="saved"><Check class="saved-icon" />已保存</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 760px; margin: 0 auto; }

.cards-stack { display: flex; flex-direction: column; gap: 20px; }

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

.card-title { font-family: var(--font-heading); font-size: 18px; font-weight: 700; margin-bottom: 16px; }

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title-row .card-title { margin-bottom: 0; }
.title-icon { width: 22px; height: 22px; color: var(--color-primary); }

.account-card {
  background:
    radial-gradient(circle at 88% 8%, rgba(255, 255, 255, 0.48), transparent 25%),
    var(--glass-bg);
}

.account-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}

.account-avatar-button {
  position: relative;
  width: 52px;
  height: 52px;
  padding: 0;
  border: none;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  cursor: pointer;
  overflow: hidden;
  transition: transform var(--duration-fast), box-shadow var(--duration-base), filter var(--duration-base);
}

.account-avatar-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(15, 143, 131, 0.28);
}

.account-avatar-button:disabled {
  cursor: wait;
  filter: saturate(0.6);
}

.account-avatar-initial {
  font-size: 22px;
  font-weight: 800;
}

.account-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-camera {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(2, 6, 23, 0.68);
  color: #fff;
}

.avatar-camera-icon {
  width: 11px;
  height: 11px;
}

.account-title {
  min-width: 0;
}

.account-title .card-title {
  margin-bottom: 4px;
}

.account-title p {
  color: var(--color-text-muted);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.account-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.account-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.22);
}

.panel-title {
  min-height: 28px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 800;
}

.panel-icon {
  width: 17px;
  height: 17px;
  color: var(--color-primary);
}

.readonly-field {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.04);
  color: var(--color-text-secondary);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.readonly-icon {
  width: 15px;
  height: 15px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 640px) {
  .account-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-stack { display: flex; flex-direction: column; gap: 14px; }

.field { display: flex; flex-direction: column; gap: 4px; }
.f-label { font-size: 12px; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0; }

.input-g {
  padding: 9px 14px; border: 1px solid var(--glass-border); border-radius: 10px;
  font-size: 14px; font-family: var(--font-body); background: var(--glass-bg);
  color: var(--color-text); outline: none; transition: border-color var(--duration-base), box-shadow var(--duration-base), background var(--duration-base), transform var(--duration-fast);
  min-height: 44px;
}

.input-g:focus { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.1); background: var(--glass-bg-hover); transform: translateY(-1px); }
select.input-g { cursor: pointer; }

.hint { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  background: var(--glass-bg);
}

.switch-row strong {
  display: block;
  color: var(--color-text);
  font-size: 14px;
}

.switch-row small {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 2px;
}

.switch-row input {
  width: 44px;
  height: 24px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
}

.mi-status-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(245, 158, 11, 0.24);
  border-radius: var(--radius-md);
  background: rgba(245, 158, 11, 0.08);
}

.mi-status-box.authed {
  border-color: rgba(16, 185, 129, 0.24);
  background: rgba(16, 185, 129, 0.08);
}

.mi-status-box strong {
  display: block;
  font-size: 14px;
  color: var(--color-text);
}

.mi-status-box small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-text-muted);
  overflow-wrap: anywhere;
}

.mi-status-icon {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.verify-link {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  align-self: flex-start;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-secondary {
  min-height: 44px;
  padding: 9px 16px;
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  background: var(--glass-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
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

.btn-icon { width: 15px; height: 15px; }

.status-msg {
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 10px 12px;
  background: rgba(15, 143, 131, 0.08);
  border: 1px solid rgba(15, 143, 131, 0.14);
  border-radius: 12px;
}

.status-msg.compact {
  padding: 8px 10px;
  font-size: 12px;
}

.status-msg.error {
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.16);
}

.balance-box {
  max-height: 180px;
  overflow: auto;
  padding: 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.08);
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.spinning {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Theme */
.theme-row { display: flex; gap: 10px; }
@media (max-width: 480px) { .theme-row { flex-direction: column; } }

.theme-card {
  flex: 1; padding: 14px; border: 2px solid var(--glass-border); border-radius: var(--radius-md);
  background: var(--glass-bg); cursor: pointer;
  transition: transform var(--duration-fast), background var(--duration-base), border-color var(--duration-base), box-shadow var(--duration-base);
  font-family: var(--font-body); text-align: center;
}

.theme-card:hover { border-color: var(--color-primary-light); }
.theme-card.on { border-color: var(--color-primary); background: rgba(13, 148, 136, 0.06); }

.theme-icon {
  width: 22px;
  height: 22px;
  color: var(--color-primary);
  margin: 0 auto 8px;
}

.t-label { display: block; font-size: 14px; font-weight: 600; color: var(--color-text); margin-bottom: 4px; }
.t-desc { display: block; font-size: 11px; color: var(--color-text-muted); }

/* Save */
.save-row { display: flex; align-items: center; gap: 16px; }

.btn-teal {
  padding: 11px 32px; border: none; border-radius: 14px; font-size: 15px; font-weight: 700;
  font-family: var(--font-body); background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff; cursor: pointer; transition: transform var(--duration-fast), box-shadow var(--duration-base), filter var(--duration-base);
  min-height: 44px;
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.25);
}

.btn-teal:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(13, 148, 136, 0.35); }
.btn-teal:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.saved { font-size: 14px; font-weight: 600; color: var(--color-success); display: inline-flex; align-items: center; gap: 6px; }
.saved-icon { width: 16px; height: 16px; }
</style>
