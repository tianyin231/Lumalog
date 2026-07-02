<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'
import { Activity, BarChart3, Dumbbell, Settings, Utensils } from 'lucide-vue-next'
import AnimatedBackground from '../components/AnimatedBackground.vue'
import AuthModal from '../components/AuthModal.vue'
import Navbar from './Navbar.vue'

const route = useRoute()
const store = useAppStore()
const mobileNavItems = [
  { name: 'dashboard', label: '概览', path: '/', icon: BarChart3 },
  { name: 'weight', label: '体重', path: '/weight', icon: Activity },
  { name: 'food', label: '饮食', path: '/food', icon: Utensils },
  { name: 'exercise', label: '运动', path: '/exercise', icon: Dumbbell },
  { name: 'settings', label: '设置', path: '/settings', icon: Settings },
]
</script>

<template>
  <div class="app-root">
    <!-- Animated background layers -->
    <AnimatedBackground />

    <!-- Top glass navbar -->
    <Navbar />

    <!-- Main content -->
    <main v-if="store.authChecked && store.isAuthenticated" class="main-area">
      <div class="content-container">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" :key="`${store.authUser?.id || 0}:${route.fullPath}`" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- Mobile bottom nav -->
    <nav class="mobile-nav" v-if="store.authChecked && store.isAuthenticated && route.name">
      <router-link
        v-for="item in mobileNavItems"
        :key="item.name"
        :to="item.path"
        class="mobile-nav-item"
        :class="{ active: route.name === item.name }"
      >
        <component :is="item.icon" class="mobile-icon" />
        <span>{{ item.label }}</span>
      </router-link>
    </nav>

    <AuthModal />
  </div>
</template>

<style scoped>
.app-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

.main-area {
  flex: 1;
  padding-top: 88px; /* navbar height + spacing */
  padding-bottom: 88px; /* mobile nav spacing */
  display: flex;
  justify-content: center;
}

.content-container {
  width: 100%;
  max-width: 1280px;
  padding: 0 24px;
}

/* Page transitions */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity var(--duration-base) var(--ease-standard), transform var(--duration-base) var(--ease-emphasis), filter var(--duration-base);
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.99);
  filter: blur(4px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.995);
  filter: blur(2px);
}

/* Mobile bottom nav */
.mobile-nav {
  display: none;
}

@media (max-width: 768px) {
  .main-area {
    padding-top: 72px;
  }

  .content-container {
    padding: 0 16px;
  }

  .mobile-nav {
    display: flex;
    position: fixed;
    bottom: 8px;
    left: 8px;
    right: 8px;
    z-index: 50;
    background: var(--glass-bg-strong);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    padding: 6px 8px calc(6px + env(safe-area-inset-bottom, 0px));
    justify-content: space-around;
    box-shadow: var(--shadow-lg), var(--shadow-glow);
  }

  .mobile-nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    min-width: 52px;
    min-height: 48px;
    padding: 7px 10px;
    border-radius: 12px;
    color: var(--color-text-muted);
    text-decoration: none;
    font-size: 10px;
    font-weight: 500;
    transition: transform var(--duration-fast) var(--ease-standard), background var(--duration-base), color var(--duration-base);
  }

  .mobile-nav-item.active {
    color: var(--color-primary);
    background: rgba(15, 143, 131, 0.12);
    transform: translateY(-2px);
  }

  .mobile-nav-item:active {
    transform: scale(0.96);
  }

  .mobile-icon {
    width: 20px;
    height: 20px;
    stroke-width: 2.2;
  }
}
</style>
