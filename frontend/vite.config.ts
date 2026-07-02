import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const frontendPort = Number(process.env.FRONTEND_PORT || 7012)
const backendPort = Number(process.env.BACKEND_PORT || 7014)

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': `http://127.0.0.1:${backendPort}`,
      '/uploads': `http://127.0.0.1:${backendPort}`,
    },
  },
})
