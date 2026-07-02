<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'
import AppShell from './layout/AppShell.vue'

const store = useAppStore()

onMounted(() => {
  store.initTheme()
  store.initAuth()
})
</script>

<template>
  <AppShell />
</template>
