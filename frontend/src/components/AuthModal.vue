<script setup lang="ts">
import { computed, ref } from 'vue'
import { LogIn, UserPlus, X } from 'lucide-vue-next'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const isRegister = computed(() => store.authMode === 'register')

async function submitAuth() {
  error.value = ''
  loading.value = true
  try {
    const res = await fetch(`/api/auth/${isRegister.value ? 'register' : 'login'}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value, password: password.value }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '登录失败')
    }
    const data = await res.json()
    store.setAuth(data.token, data.user)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请求失败'
  } finally {
    loading.value = false
  }
}

function switchMode() {
  error.value = ''
  store.authMode = isRegister.value ? 'login' : 'register'
}
</script>

<template>
  <div
    v-if="store.authModalOpen"
    class="auth-layer"
    role="dialog"
    aria-modal="true"
    aria-labelledby="auth-title"
    @click.self="store.closeAuthModal"
  >
    <form class="auth-card glass-strong" @submit.prevent="submitAuth" @click.stop>
      <button
        v-if="store.isAuthenticated"
        class="close-btn"
        type="button"
        aria-label="关闭登录窗口"
        @click="store.closeAuthModal"
      >
        <X class="close-icon" />
      </button>
      <div class="auth-icon">
        <UserPlus v-if="isRegister" class="icon" />
        <LogIn v-else class="icon" />
      </div>
      <h2 id="auth-title">{{ isRegister ? '注册 Lumalog 账号' : '登录 Lumalog' }}</h2>
      <p class="auth-desc">使用邮箱账号保存并隔离你的健康记录。</p>

      <label class="field">
        <span>邮箱</span>
        <input v-model.trim="email" type="email" autocomplete="email" required placeholder="you@example.com" />
      </label>
      <label class="field">
        <span>密码</span>
        <input v-model="password" type="password" autocomplete="current-password" required minlength="6" placeholder="至少 6 位" />
      </label>

      <p v-if="error" class="auth-error">{{ error }}</p>

      <button class="auth-submit pressable" type="submit" :disabled="loading">
        {{ loading ? '处理中...' : isRegister ? '注册并登录' : '登录' }}
      </button>
      <button class="auth-switch" type="button" @click="switchMode">
        {{ isRegister ? '已有账号，去登录' : '没有账号，去注册' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.auth-layer {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(2, 6, 23, 0.42);
}

.auth-card {
  position: relative;
  width: min(420px, 100%);
  border-radius: var(--radius-xl);
  padding: 26px;
  box-shadow: var(--shadow-xl), var(--shadow-glow);
}

.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 36px;
  height: 36px;
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  background: var(--glass-bg);
  color: var(--color-text-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background var(--duration-base), color var(--duration-base), transform var(--duration-fast);
}

.close-btn:hover {
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.08);
  transform: scale(1.04);
}

.close-icon {
  width: 16px;
  height: 16px;
}

.auth-icon {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  margin-bottom: 14px;
}

.auth-card h2 {
  font-size: 22px;
  font-weight: 800;
}

.auth-desc {
  margin: 6px 0 18px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.field span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.field input {
  min-height: 44px;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  background: var(--glass-bg);
  color: var(--color-text);
  outline: none;
}

.field input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.12);
}

.auth-error {
  margin: 2px 0 12px;
  color: var(--color-danger);
  font-size: 13px;
}

.auth-submit {
  width: 100%;
  min-height: 44px;
  border: none;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.auth-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.auth-switch {
  width: 100%;
  min-height: 40px;
  margin-top: 8px;
  border: none;
  background: transparent;
  color: var(--color-primary);
  font-weight: 700;
  cursor: pointer;
}
</style>
