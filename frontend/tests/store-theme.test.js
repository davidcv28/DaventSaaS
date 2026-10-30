// Modo noche universal: el tema efectivo y la persistencia del visitante.
import { describe, expect, it } from 'vitest'
import {
  STORE_THEME_KEY, persistVisitorTheme, readVisitorTheme, resolveStoreTheme
} from '../src/utils/storeTheme.js'

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial))
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
    dump: () => Object.fromEntries(data)
  }
}

describe('tema de la web publicada', () => {
  it('el visitante manda sobre el default de la tienda', () => {
    expect(resolveStoreTheme({ visitor: 'dark', storeDefault: 'light', prefersDark: false })).toBe('dark')
    expect(resolveStoreTheme({ visitor: 'light', storeDefault: 'dark', prefersDark: true })).toBe('light')
  })

  it('sin elección del visitante respeta el default del negocio', () => {
    expect(resolveStoreTheme({ storeDefault: 'dark', prefersDark: false })).toBe('dark')
  })

  it('sin default respeta prefers-color-scheme', () => {
    expect(resolveStoreTheme({ prefersDark: true })).toBe('dark')
    expect(resolveStoreTheme({ prefersDark: false })).toBe('light')
  })

  it('el preview del Studio gana sobre todo', () => {
    expect(resolveStoreTheme({
      studio: 'light', studioView: true, visitor: 'dark', storeDefault: 'dark', prefersDark: true
    })).toBe('light')
    expect(resolveStoreTheme({ studio: 'light', studioView: false, storeDefault: 'dark' })).toBe('dark')
  })

  it('persiste por tienda y solo acepta light/dark', () => {
    const storage = memoryStorage({ [STORE_THEME_KEY('otra')]: 'light' })
    expect(readVisitorTheme(storage, 'mistienda')).toBeNull()
    persistVisitorTheme(storage, 'mistienda', 'dark')
    expect(storage.dump()[STORE_THEME_KEY('mistienda')]).toBe('dark')
    expect(readVisitorTheme(storage, 'mistienda')).toBe('dark')
    storage.setItem(STORE_THEME_KEY('rota'), 'oscuro')
    expect(readVisitorTheme(storage, 'rota')).toBeNull()
  })

  it('un storage bloqueado no rompe la web', () => {
    const blocked = { getItem: () => { throw new Error('privado') }, setItem: () => { throw new Error('privado') } }
    expect(readVisitorTheme(blocked, 'x')).toBeNull()
    expect(() => persistVisitorTheme(blocked, 'x', 'dark')).not.toThrow()
  })
})
