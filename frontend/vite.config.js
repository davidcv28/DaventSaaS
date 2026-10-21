import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // En dev evitamos CORS pegando a Django por el mismo origen.
      // Ver src/config/env.js -> VITE_API_BASE_URL=/api en .env.development
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5173
  }
})
