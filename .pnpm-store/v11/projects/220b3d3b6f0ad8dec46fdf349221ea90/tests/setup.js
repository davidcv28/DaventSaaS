// Mínimo navegador para los módulos que leen window/location al importarse
// (env.js, http.js). No hace falta jsdom: el SPA se prueba en Node.
if (!globalThis.window) {
  globalThis.window = { location: { protocol: 'http:', hostname: 'localhost', port: '', href: 'http://localhost/' } }
}
if (!globalThis.localStorage) {
  const store = new Map()
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
    clear: () => store.clear(),
  }
}
