import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useTheme } from '../composables/useTheme'

export interface AuthUser {
  id: number
  email: string
  avatar_path?: string | null
}

function defaultSettings() {
  return {
    nickname: '我',
    heightCm: 170,
    targetWeightKg: 65,
    dailyCalorieTarget: 2000,
  }
}

export const useAppStore = defineStore('app', () => {
  const { themeMode, isDark, setTheme, initTheme } = useTheme()
  localStorage.removeItem('qingji_token')
  localStorage.removeItem('qingji_user')
  const storedUser = localStorage.getItem('lumalog_user')
  const authToken = ref(localStorage.getItem('lumalog_token') || '')
  const authUser = ref<AuthUser | null>(
    storedUser ? JSON.parse(storedUser) : null
  )
  const authChecked = ref(false)
  const authModalOpen = ref(false)
  const authMode = ref<'login' | 'register'>('login')

  // Sidebar collapsed state
  const sidebarCollapsed = ref(false)

  // Settings from backend
  const settings = ref(defaultSettings())

  // Dashboard stats
  const currentWeight = ref<number | null>(null)
  const todayCalories = ref(0)
  const todayExercise = ref(0)

  const bmi = computed(() => {
    if (!currentWeight.value) return null
    const h = settings.value.heightCm / 100
    return +(currentWeight.value / (h * h)).toFixed(1)
  })

  const calorieProgress = computed(() =>
    Math.round((todayCalories.value / settings.value.dailyCalorieTarget) * 100)
  )

  const isAuthenticated = computed(() => Boolean(authToken.value && authUser.value))

  function openAuthModal(mode: 'login' | 'register' = 'login') {
    authMode.value = mode
    authModalOpen.value = true
  }

  function closeAuthModal() {
    if (isAuthenticated.value) authModalOpen.value = false
  }

  function resetAccountState() {
    settings.value = defaultSettings()
    currentWeight.value = null
    todayCalories.value = 0
    todayExercise.value = 0
  }

  function setAuth(token: string, user: AuthUser) {
    if (authUser.value?.id !== user.id) resetAccountState()
    authToken.value = token
    authUser.value = user
    localStorage.setItem('lumalog_token', token)
    localStorage.setItem('lumalog_user', JSON.stringify(user))
    localStorage.removeItem('qingji_token')
    localStorage.removeItem('qingji_user')
    authModalOpen.value = false
  }

  function setAuthUser(user: AuthUser) {
    authUser.value = user
    localStorage.setItem('lumalog_user', JSON.stringify(user))
  }

  function logout() {
    authToken.value = ''
    authUser.value = null
    resetAccountState()
    localStorage.removeItem('lumalog_token')
    localStorage.removeItem('lumalog_user')
    localStorage.removeItem('qingji_token')
    localStorage.removeItem('qingji_user')
    openAuthModal('login')
  }

  async function initAuth() {
    installAuthenticatedFetch()
    if (!authToken.value) {
      authChecked.value = true
      openAuthModal('login')
      return
    }
    try {
      const res = await fetch('/api/auth/me')
      if (!res.ok) throw new Error('auth failed')
      authUser.value = await res.json()
      localStorage.setItem('lumalog_user', JSON.stringify(authUser.value))
    } catch {
      logout()
    } finally {
      authChecked.value = true
    }
  }

  function installAuthenticatedFetch() {
    const win = window as any
    const rawFetch = (win.__lumalogRawFetch || window.fetch.bind(window)) as typeof window.fetch
    win.__lumalogRawFetch = rawFetch
    win.__lumalogFetchInstalled = true
    window.fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
      const headers = new Headers(init.headers)
      const token = authToken.value || localStorage.getItem('lumalog_token') || ''
      if (url.startsWith('/api') && token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
      const res = await rawFetch(input, { ...init, headers })
      if (res.status === 401 && url.startsWith('/api') && !url.startsWith('/api/auth/')) {
        openAuthModal('login')
      }
      return res
    }
  }

  return {
    authToken,
    authUser,
    authChecked,
    authModalOpen,
    authMode,
    isAuthenticated,
    themeMode,
    isDark,
    setTheme,
    initTheme,
    sidebarCollapsed,
    settings,
    currentWeight,
    todayCalories,
    todayExercise,
    bmi,
    calorieProgress,
    initAuth,
    openAuthModal,
    closeAuthModal,
    setAuth,
    setAuthUser,
    logout,
  }
})
