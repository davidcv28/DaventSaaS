import { http } from './http.js'
import { env } from '../config/env.js'

// Dominio locations — endpoints reales (AllowAny, paginados DRF):
// GET /api/provinces/            -> lista ordenada
// GET /api/cities/?province=<id> -> filtradas por provincia
// GET /api/zipcodes/             -> catálogo
// Si el backend no responde (DB caída, 404), usa catálogo local de emergencia.

export const FALLBACK_PROVINCES = [
  { id: 1, name: 'Buenos Aires' },
  { id: 2, name: 'CABA' },
  { id: 3, name: 'Córdoba' },
  { id: 4, name: 'Santa Fe' },
  { id: 5, name: 'Mendoza' },
  { id: 6, name: 'Tucumán' },
  { id: 7, name: 'Salta' },
  { id: 8, name: 'Entre Ríos' }
]

export const FALLBACK_CITIES = {
  1: [
    { id: 101, name: 'La Plata' },
    { id: 102, name: 'Mar del Plata' },
    { id: 103, name: 'Bahía Blanca' }
  ],
  2: [
    { id: 201, name: 'CABA - Comuna 1' },
    { id: 202, name: 'CABA - Comuna 2' }
  ],
  3: [
    { id: 301, name: 'Córdoba Capital' },
    { id: 302, name: 'Villa María' }
  ],
  4: [
    { id: 401, name: 'Rosario' },
    { id: 402, name: 'Santa Fe Capital' }
  ],
  5: [
    { id: 501, name: 'Mendoza Capital' },
    { id: 502, name: 'San Rafael' }
  ],
  6: [{ id: 601, name: 'San Miguel de Tucumán' }],
  7: [{ id: 701, name: 'Salta Capital' }],
  8: [{ id: 801, name: 'Paraná' }]
}

function unwrap(data) {
  // DRF paginado {results:[...]} o lista directa
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function normalize(rows) {
  return (rows || []).map((item) => {
    if (typeof item === 'string') return { id: item, name: item }
    const name =
      item?.name ??
      item?.name_province ??
      item?.name_city ??
      item?.nombre ??
      `ID ${item?.id ?? item?.pk}`
    return { id: item?.id ?? item?.pk, name, raw: item }
  }).filter((r) => r.id !== undefined)
}

export const locationsApi = {
  usingFallback: false,

  async fetchAllPages(url, params = {}) {
    // Recorre todas las páginas DRF (?page=1..N) y devuelve lista completa.
    const rows = []
    let nextUrl = url
    let nextParams = { ...params }
    let guard = 0
    while (nextUrl && guard < 50) {
      guard += 1
      const { data } = await http.get(nextUrl, { params: nextParams })
      rows.push(...unwrap(data))
      const next = data?.next
      if (!next) break
      // data.next llega como URL absoluta del backend (127.0.0.1:8000). La reescribimos
      // al mismo origen para seguir por el proxy de Vite y no depender de CORS.
      const u = new URL(next, 'http://local')
      const basePath = new URL(env.apiBaseUrl, 'http://local').pathname.replace(/\/$/, '')
      nextUrl = (u.pathname + u.search).replace(new RegExp(`^${basePath}`), '') || null
      nextParams = {}
    }
    return rows
  },

  async getProvinces() {
    try {
      const rows = normalize(await this.fetchAllPages('/provinces/'))
      if (rows.length) {
        this.usingFallback = false
        return rows
      }
    } catch (e) {
      // Sin respuesta (Django apagado) o 404/500: caemos al catálogo local.
      // Solo relanzamos errores de programación; los de red/HTTP usan fallback.
      if (e?.response?.status !== undefined && ![404, 500, 502, 503].includes(e.response.status) && !e.request) {
        throw e
      }
    }
    this.usingFallback = true
    return FALLBACK_PROVINCES
  },

  async getCities(provinceId) {
    if (!provinceId) return []
    try {
      const rows = normalize(await this.fetchAllPages('/cities/', { province: provinceId }))
      if (rows.length) {
        this.usingFallback = false
        return rows
      }
    } catch (e) {
      if (e?.response?.status !== undefined && ![404, 500, 502, 503].includes(e.response.status) && !e.request) {
        throw e
      }
    }
    this.usingFallback = true
    return FALLBACK_CITIES[Number(provinceId)] || []
  },

  async getZipcodes() {
    try {
      const { data } = await http.get('/zipcodes/')
      return normalize(unwrap(data))
    } catch {
      return []
    }
  }
}

