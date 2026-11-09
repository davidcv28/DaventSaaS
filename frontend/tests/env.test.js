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

  it('storeUrl builds the canonical subdomain link when subdomains are active', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_PLATFORM_DOMAIN', 'davent.com.ar')
    vi.stubEnv('VITE_APP_URL', 'https://www.davent.com.ar')
    globalThis.window = { location: { protocol: 'https:', hostname: 'www.davent.com.ar', port: '' } }
    const { storeUrl, storeSlugAffixes } = await import('../src/config/env.js')
    expect(storeUrl('mitienda')).toBe('https://mitienda.davent.com.ar')
    expect(storeSlugAffixes()).toEqual({ prefix: 'https://', suffix: '.davent.com.ar' })
  })

  it('storeUrl falls back to the path alias when subdomains are off', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_PLATFORM_DOMAIN', 'daventsaas.onrender.com')
    vi.stubEnv('VITE_APP_URL', 'https://daventsaas.onrender.com')
    globalThis.window = { location: { protocol: 'https:', hostname: 'daventsaas.onrender.com', port: '' } }
    const { storeUrl, storeSlugAffixes } = await import('../src/config/env.js')
    expect(storeUrl('mitienda')).toBe('https://daventsaas.onrender.com/mitienda')
    expect(storeSlugAffixes()).toEqual({ prefix: 'https://daventsaas.onrender.com/', suffix: '' })
  })

  it('storeUrl honors VITE_STORE_SUBDOMAINS=0 as path alias', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_PLATFORM_DOMAIN', 'davent.com.ar')
    vi.stubEnv('VITE_STORE_SUBDOMAINS', '0')
    vi.stubEnv('VITE_APP_URL', 'https://www.davent.com.ar')
    globalThis.window = { location: { protocol: 'https:', hostname: 'www.davent.com.ar', port: '' } }
    const { storeUrl } = await import('../src/config/env.js')
    expect(storeUrl('mitienda')).toBe('https://www.davent.com.ar/mitienda')
  })
})
