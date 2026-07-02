<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import { Activity, BarChart3, Dumbbell, LogIn, LogOut, Moon, Route, Settings, Sun, Sunset, Utensils } from 'lucide-vue-next'

const route = useRoute()
const store = useAppStore()

const navItems = [
  { name: 'dashboard', label: '概览', path: '/', icon: BarChart3 },
  { name: 'weight', label: '体重', path: '/weight', icon: Activity },
  { name: 'food', label: '饮食', path: '/food', icon: Utensils },
  { name: 'exercise', label: '运动', path: '/exercise', icon: Dumbbell },
  { name: 'settings', label: '设置', path: '/settings', icon: Settings },
]

function isActive(name: string) {
  return route.name === name
}

const themeModes = ['light', 'dark', 'auto'] as const
const themeLabels: Record<string, string> = { light: '浅色模式', dark: '深色模式', auto: '自动模式' }
const themeIcons = { light: Sun, dark: Moon, auto: Sunset }
let themeIdx = themeModes.indexOf(store.themeMode as any)
if (themeIdx < 0) themeIdx = 2

const accountInitial = computed(() => {
  const name = accountDisplayName.value || 'L'
  return name.trim().slice(0, 1).toUpperCase()
})

const accountDisplayName = computed(() => {
  const nickname = store.settings.nickname?.trim()
  return nickname || store.authUser?.email || ''
})

const accountTitle = computed(() => {
  const email = store.authUser?.email || ''
  return store.settings.nickname?.trim() ? `${store.settings.nickname} · ${email}` : email
})

function cycleTheme() {
  themeIdx = (themeIdx + 1) % 3
  store.setTheme(themeModes[themeIdx] as 'light' | 'dark' | 'auto')
}
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <!-- Logo -->
      <router-link to="/" class="logo-link">
        <div class="logo-icon"><Route class="icon" /></div>
        <span class="logo-text">Luma<span class="logo-accent">log</span></span>
      </router-link>

      <!-- Desktop nav -->
      <nav class="nav-links">
        <router-link
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="nav-link"
          :class="{ active: isActive(item.name) }"
        >
          <component :is="item.icon" class="nav-icon" />
          {{ item.label }}
          <span v-if="isActive(item.name)" class="active-dot" />
        </router-link>
      </nav>

      <!-- Right actions -->
      <div class="nav-actions">
        <button
          v-if="!store.isAuthenticated"
          class="auth-btn pressable"
          type="button"
          @click="store.openAuthModal('login')"
        >
          <LogIn class="btn-icon" />
          登录
        </button>
        <div v-else class="account-chip" :title="accountTitle">
          <img v-if="store.authUser?.avatar_path" :src="store.authUser.avatar_path" alt="用户头像" class="account-avatar-sm" />
          <span v-else class="account-avatar-fallback">{{ accountInitial }}</span>
          <span>{{ accountDisplayName }}</span>
          <button class="logout-btn" type="button" aria-label="退出登录" @click="store.logout">
            <LogOut class="btn-icon" />
          </button>
        </div>
        <button class="icon-btn pressable" @click="cycleTheme" :title="themeLabels[store.themeMode]" :aria-label="themeLabels[store.themeMode]">
          <component :is="themeIcons[store.themeMode]" class="icon" />
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  position: fixed;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  width: calc(100% - 32px);
  max-width: 1248px;
}

.navbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--glass-bg-strong);
  backdrop-filter: blur(24px) saturate(200%);
  -webkit-backdrop-filter: blur(24px) saturate(200%);
  border: 1px solid var(--glass-border);
  border-radius: 18px;
  box-shadow: var(--shadow-md), var(--shadow-glow);
  transition: transform var(--duration-base) var(--ease-emphasis), background var(--duration-base), border-color var(--duration-base), box-shadow var(--duration-base);
}

.navbar-inner:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}

/* Logo */
.logo-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex-shrink: 0;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background:
    radial-gradient(circle at 28% 20%, rgba(255,255,255,0.72), transparent 30%),
    linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 22px rgba(15, 143, 131, 0.28);
}

.logo-icon .icon {
  color: #fff;
}

.logo-text {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0;
}

.logo-accent {
  color: var(--color-primary);
}

/* Nav links */
.nav-links {
  display: flex;
  gap: 4px;
}

.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 18px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), color var(--duration-base);
}

.nav-link:hover {
  color: var(--color-text);
  background: rgba(15, 143, 131, 0.09);
  transform: translateY(-1px);
}

.nav-link.active {
  color: var(--color-primary);
  background: rgba(15, 143, 131, 0.13);
  font-weight: 600;
}

.nav-icon {
  width: 16px;
  height: 16px;
  stroke-width: 2.2;
}

.active-dot {
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  background: var(--color-primary);
  border-radius: 50%;
}

/* Actions */
.nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 143, 131, 0.09);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  color: var(--color-primary);
  cursor: pointer;
}

.icon-btn:hover {
  background: rgba(15, 143, 131, 0.16);
}

.auth-btn,
.account-chip {
  min-height: 36px;
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  background: rgba(15, 143, 131, 0.09);
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.auth-btn {
  padding: 0 12px;
  cursor: pointer;
}

.account-chip {
  max-width: 220px;
  padding: 0 4px 0 5px;
}

.account-avatar-sm,
.account-avatar-fallback {
  width: 26px;
  height: 26px;
  border-radius: 9px;
  flex-shrink: 0;
}

.account-avatar-sm {
  object-fit: cover;
}

.account-avatar-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.account-chip span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.logout-btn:hover {
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.08);
}

.btn-icon {
  width: 15px;
  height: 15px;
}

@media (max-width: 768px) {
  .navbar {
    top: 8px;
    width: calc(100% - 16px);
  }

  .navbar-inner {
    padding: 6px 12px;
    border-radius: 16px;
  }

  .nav-links {
    display: none;
  }

  .logo-text {
    font-size: 16px;
  }

  .logo-icon {
    width: 28px;
    height: 28px;
    font-size: 14px;
  }

  .account-chip span {
    display: none;
  }

  .account-chip .account-avatar-fallback {
    display: inline-flex;
  }

  .auth-btn {
    padding: 0 10px;
  }
}
</style>
