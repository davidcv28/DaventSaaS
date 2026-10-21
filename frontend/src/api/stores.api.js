import { http } from './http.js'

// Dominio stores (StoreApp):
// GET  /api/stores/                      Bearer   -> mi tienda (lista con 0..1, incluye customization)
// POST /api/stores/                      Bearer {slug} -> claim del link (onboarding)
// PATCH /api/stores/<pk>/                Bearer {slug?, is_published?} -> renombrar / pausar
// GET  /api/stores/slug-available/?slug= Bearer   -> {slug, available, reason: invalid|reserved|taken}
// GET  /api/stores/public/<slug>/        público  -> {slug, business_name, city_name, province_name, customization}
// GET  /api/stores/customization/        Bearer   -> mi diseño web (get_or_create con defaults)
// PATCH /api/stores/customization/       Bearer {headline?, description?, theme?, accent?, whatsapp?, instagram?}
//                                        -> 403 si el plan vigente no incluye 'has_customization'

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const storesApi = {
  async listMine() {
    const { data } = await http.get('/stores/')
    return unwrap(data)
  },

  async claim(slug) {
    const { data } = await http.post('/stores/', { slug })
    return data
  },

  async update(pk, payload) {
    const { data } = await http.patch(`/stores/${pk}/`, payload)
    return data
  },

  async slugAvailable(slug) {
    const { data } = await http.get('/stores/slug-available/', { params: { slug } })
    return data
  },

  async publicStore(slug) {
    const { data } = await http.get(`/stores/public/${slug}/`)
    return data
  },

  async customization() {
    const { data } = await http.get('/stores/customization/')
    return data
  },

  async updateCustomization(payload) {
    const { data } = await http.patch('/stores/customization/', payload)
    return data
  }
}

// Espejo del validador del backend (StoreApp/stores/validators.py).
const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{1,58}[a-z0-9])?$/

export function normalizeSlug(value) {
  return String(value || '').trim().toLowerCase()
}

export function validateSlugFormat(slug) {
  if (!slug) return 'Escribí tu link'
  if (!SLUG_PATTERN.test(slug)) return 'Solo letras minúsculas, números y guiones (sin guiones al principio ni al final)'
  return ''
}

export function publicStoreUrl(slug, origin = window.location.origin) {
  return `${origin}/tienda/${slug}`
}

// ===== Personalización de la web pública (espejo de StoreCustomization) =====
// El backend guarda códigos cerrados (theme/accent); el frontend los traduce a
// paletas CSS. Nada de colores libres del usuario: la web siempre se ve bien.
export const CUSTOMIZATION_DEFAULTS = {
  headline: '',
  description: '',
  theme: 'light',
  accent: 'indigo',
  whatsapp: '',
  instagram: ''
}

export const STORE_ACCENTS = {
  indigo:  { label: 'Índigo',    hex: '#4f46e5', ink: '#4338ca', soft: '#eef2ff' },
  violet:  { label: 'Violeta',   hex: '#7c3aed', ink: '#6d28d9', soft: '#f5f3ff' },
  emerald: { label: 'Esmeralda', hex: '#059669', ink: '#047857', soft: '#ecfdf5' },
  amber:   { label: 'Ámbar',     hex: '#d97706', ink: '#b45309', soft: '#fffbeb' },
  rose:    { label: 'Rosa',      hex: '#e11d48', ink: '#be123c', soft: '#fff1f2' },
  sky:     { label: 'Celeste',   hex: '#0284c7', ink: '#0369a1', soft: '#f0f9ff' }
}

export const STORE_THEMES = {
  light: { label: 'Claro' },
  dark:  { label: 'Oscuro' }
}

export function accentMeta(accent) {
  return STORE_ACCENTS[accent] || STORE_ACCENTS.indigo
}

export function storeThemeVars(customization) {
  const c = { ...CUSTOMIZATION_DEFAULTS, ...(customization || {}) }
  const a = accentMeta(c.accent)
  return {
    '--store-accent': a.hex,
    '--store-accent-ink': a.ink,
    '--store-accent-soft': a.soft
  }
}

const WHATSAPP_PATTERN = /^\+?\d{8,15}$/
const INSTAGRAM_PATTERN = /^[a-z0-9](?:[a-z0-9._]{0,28}[a-z0-9])?$/

export function validateHeadline(value) {
  if (value && value.length > 140) return 'El titular admite hasta 140 caracteres'
  return ''
}

export function validateDescription(value) {
  if (value && value.length > 800) return 'La descripción admite hasta 800 caracteres'
  return ''
}

export function validateWhatsapp(value) {
  const v = String(value || '').replace(/[\s-]/g, '')
  if (v && !WHATSAPP_PATTERN.test(v)) return 'Ingresá un número válido: 8 a 15 dígitos, con "+" opcional. Ej. +5493871551234'
  return ''
}

export function normalizeWhatsapp(value) {
  return String(value || '').replace(/[\s-]/g, '')
}

export function normalizeInstagram(value) {
  return String(value || '').trim().replace(/^@+/, '').toLowerCase()
}

export function validateInstagram(value) {
  const v = normalizeInstagram(value)
  if (v && !INSTAGRAM_PATTERN.test(v)) return 'Ingresá solo el usuario, sin "@": letras, números, puntos o guiones bajos'
  return ''
}
