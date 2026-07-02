import { ref } from 'vue'

type ThemeMode = 'light' | 'dark' | 'auto'

const themeMode = ref<ThemeMode>(
  (localStorage.getItem('theme-mode') as ThemeMode) || 'auto'
)
const isDark = ref(false)

function applyTheme(mode: ThemeMode) {
  if (mode === 'auto') {
    const isDarkTime = checkSunsetDark()
    isDark.value = isDarkTime
  } else {
    isDark.value = mode === 'dark'
  }
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
}

function checkSunsetDark(): boolean {
  // Check user's preferred color scheme
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return true
  }
  // Check if it's between sunset and sunrise based on user's location
  const saved = getSunsetTimes()
  if (saved) {
    const now = new Date()
    const hours = now.getHours()
    const minutes = now.getMinutes()
    const currentMinutes = hours * 60 + minutes
    return currentMinutes >= saved.sunset || currentMinutes < saved.sunrise
  }
  // Fallback: use time-based heuristic (6:00 sunrise, 18:30 sunset in China)
  const now = new Date()
  const hours = now.getHours()
  return hours >= 18 || hours < 6
}

interface SunsetTimes {
  sunrise: number  // minutes from midnight
  sunset: number   // minutes from midnight
}

function getSunsetTimes(): SunsetTimes | null {
  try {
    const raw = localStorage.getItem('sunset-times')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed.sunrise != null && parsed.sunset != null) {
        return parsed
      }
    }
  } catch {}
  return null
}

function setTheme(mode: ThemeMode) {
  themeMode.value = mode
  localStorage.setItem('theme-mode', mode)
  applyTheme(mode)
}

function initTheme() {
  // Listen for system color scheme changes (for auto mode)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (themeMode.value === 'auto') {
      applyTheme('auto')
    }
  })
  applyTheme(themeMode.value)
}

export function useTheme() {
  return { themeMode, isDark, setTheme, initTheme }
}
