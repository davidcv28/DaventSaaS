import { beforeEach, describe, expect, it, vi } from 'vitest'

// env.js lee import.meta.env y window.location al importarse: cada caso
// resetea módulos y vuelve a cargarlo con el entorno que quiere probar.
async function loadEnv({ base = '', domain = 'localhost', host = 'localhost', port = '5173' } = {}) {
  vi.resetModules()
  vi.stubEnv('VITE_API_BASE_URL', base)
  vi.stubEnv('VITE_PLATFORM_DOMAIN', domain)
  globalThis.window = { location: { protocol: 'https:', hostname: host, port } }
  return import('../src/config/env.js')
}

describe('env', () => {
  beforeEach(() => {
    vi.unstubAllEnvs()
  })

  it('falls back to a relative /api base instead of localhost', async () => {
    const { env } = await loadEnv()
    expect(env.apiBaseUrl).toBe('/api')
  })

  it('apiUrl joins the base without duplicate slashes', async () => {
    const { apiUrl } = await loadEnv({ base: 'https://davent.com/api/' })
    expect(apiUrl('/products/')).toBe('https://davent.com/api/products/')
    expect(apiUrl('products/')).toBe('https://davent.com/api/products/')
  })

  it('detects the store subdomain only for real store hosts', async () => {
    const store = await loadEnv({ domain: 'davent.com', host: 'mitienda.davent.com', port: '' })
    expect(store.storeHostSlug).toBe('mitienda')
    const platform = await loadEnv({ domain: 'davent.com', host: 'www.davent.com', port: '' })
    expect(platform.storeHostSlug).toBe(null)
  })

  it('storeUrl uses path aliases when subdomains are disabled', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_STORE_SUBDOMAINS', '0')
    vi.stubEnv('VITE_PLATFORM_DOMAIN', 'davent.com')
    globalThis.window = { location: { protocol: 'https:', hostname: 'davent.com', port: '' } }
    const { storeUrl } = await import('../src/config/env.js')
    expect(storeUrl('mitienda')).toMatch(/\/mitienda$/)
  })
})
