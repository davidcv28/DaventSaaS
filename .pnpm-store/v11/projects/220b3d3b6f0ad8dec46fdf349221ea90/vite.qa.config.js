import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// Solo en `vite dev` (apply:'serve'): expone /set-token.html desde dev-tools/
// — la página de debug escribe JWT en localStorage del origen, por eso NO vive
// en public/ (vite build copiaría a dist y se iría a producción). El build y
// `vite preview` jamás la sirven.
const devSetToken = {
  name: 'dev-set-token',
  apply: 'serve',
  configureServer(server) {
    const file = fileURLToPath(new URL('./dev-tools/set-token.html', import.meta.url))
    server.middlewares.use('/set-token.html', (_req, res) => {
      res.setHeader('Content-Type', 'text/html; charset=utf-8')
      res.end(readFileSync(file))
    })
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue(), devSetToken],
  server: {
    port: 5175,
    strictPort: true,
    proxy: {
      // En dev evitamos CORS pegando a Django por el mismo origen.
      // Ver src/config/env.js -> VITE_API_BASE_URL=/api en .env.development
      '/api': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5175
  }
})
