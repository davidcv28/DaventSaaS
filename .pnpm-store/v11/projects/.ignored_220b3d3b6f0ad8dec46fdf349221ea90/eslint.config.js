// ESLint flat config (v9). Cubre el JS del SPA; los .vue se validan en el
// build de Vite (eslint-plugin-vue queda como paso siguiente).
import js from '@eslint/js'

const browserGlobals = {
  window: 'readonly', document: 'readonly', navigator: 'readonly',
  location: 'readonly', localStorage: 'readonly', sessionStorage: 'readonly',
  console: 'readonly', fetch: 'readonly', setTimeout: 'readonly',
  clearTimeout: 'readonly', setInterval: 'readonly', clearInterval: 'readonly',
  requestAnimationFrame: 'readonly', cancelAnimationFrame: 'readonly',
  FormData: 'readonly', File: 'readonly', Blob: 'readonly', URL: 'readonly',
  URLSearchParams: 'readonly', Image: 'readonly', HTMLElement: 'readonly',
  IntersectionObserver: 'readonly', ResizeObserver: 'readonly',
  MutationObserver: 'readonly', CustomEvent: 'readonly', Event: 'readonly',
  AbortController: 'readonly', performance: 'readonly', crypto: 'readonly',
  alert: 'readonly', confirm: 'readonly', prompt: 'readonly',
  AudioContext: 'readonly', Audio: 'readonly', CanvasRenderingContext2D: 'readonly',
  process: 'readonly', globalThis: 'readonly', structuredClone: 'readonly',
  Buffer: 'readonly', FileReader: 'readonly', XMLSerializer: 'readonly',
  KeyboardEvent: 'readonly',
}

export default [
  { ignores: ['dist/**', 'node_modules/**', 'android/**', 'apk-dist/**', 'assets/**', 'public/**', 'dev-tools/**'] },
  js.configs.recommended,
  {
    files: ['**/*.js', '**/*.mjs'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: browserGlobals,
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
]
