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
    port: 5173,
    strictPort: true,
    proxy: {
      // En dev evitamos CORS pegando a Django por el mismo origen.
      // Ver src/config/env.js -> VITE_API_BASE_URL=/api en .env.development
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    },
    // OneDrive + escrituras atómicas de los editores crean carpetas
    // `.archivo.<pid>.<uuid>.tmpdir/` que el watcher de Vite intenta observar y
    // termina con EBUSY, tirando el servidor dev. Ignorarlas (y los temporales
    // de QA) evita el crash sin tocar el build.
    watch: {
      ignored: ['**/.*.tmpdir/**', '**/*.tmp', '**/.qa-tmp/**', '**/tmp*/**']
    }
  },
  preview: {
    port: 5173
  }
})
