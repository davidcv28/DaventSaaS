import { http } from './http.js'

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

// Catálogo geo en localStorage (24h): provincias/ciudades cambian nunca —
// sin esto cada ingreso al panel volvía a pedir las 24 provincias + todas
// las ciudades de la provincia de la cuenta (2+ requests por montaje).
// Es data pública compartida: persiste entre logins sin purgarse.
const GEO_TTL = 24 * 60 * 60 * 1000
const GEO_NS = 'davent:geo:'

function geoGet(key) {
  try {
    const raw = localStorage.getItem(GEO_NS + key)
    if (!raw) return null
    const { t, v } = JSON.parse(raw)
    if (!Number.isFinite(t) || Date.now() - t > GEO_TTL) return null
    return v
  } catch {
    return null
  }
}

function geoSet(key, v) {
  try {
    localStorage.setItem(GEO_NS + key, JSON.stringify({ t: Date.now(), v }))
  } catch { /* cuota llena o storage bloqueado */ }
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
    // Pide la primera página y, si hay más, las trae TODAS en paralelo usando
    // el `count` de DRF. Antes encadenaba página por página: una provincia con
    // ~14 páginas de ciudades tardaba más de un segundo por cada una.
    const { data } = await http.get(url, { params })
    const rows = [...unwrap(data)]
    const total = Number(data?.count)
    if (!data?.next || !Number.isFinite(total) || total <= rows.length) return rows
    const pageSize = rows.length || 10
    const remaining = Math.min(Math.ceil(total / pageSize), 50) - 1
    const rest = await Promise.all(
      Array.from({ length: remaining }, (_, i) =>
        http.get(url, { params: { ...params, page: i + 2 } })
          .then((res) => unwrap(res.data))
          .catch(() => [])
      )
    )
    rest.forEach((pageRows) => rows.push(...pageRows))
    return rows
  },

  async getProvinces() {
    const cached = geoGet('provinces')
    if (cached) {
      this.usingFallback = false
      return cached
    }
    try {
      const rows = normalize(await this.fetchAllPages('/provinces/', { page_size: 200 }))
      if (rows.length) {
        geoSet('provinces', rows)
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
    const cached = geoGet(`cities:${provinceId}`)
    if (cached) {
      this.usingFallback = false
      return cached
    }
    try {
      const rows = normalize(await this.fetchAllPages('/cities/', { province: provinceId, page_size: 200 }))
      if (rows.length) {
        geoSet(`cities:${provinceId}`, rows)
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

