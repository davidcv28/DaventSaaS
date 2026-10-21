import { http } from './http.js'

// Dominio stores (StoreApp):
// GET  /api/stores/                      Bearer   -> mi tienda (lista con 0..1, incluye customization)
// POST /api/stores/                      Bearer {slug} -> claim del link (onboarding)
// PATCH /api/stores/<pk>/                Bearer {slug?, is_published?} -> renombrar / pausar
// GET  /api/stores/slug-available/?slug= Bearer   -> {slug, available, reason: invalid|reserved|taken}
// GET  /api/stores/public/<slug>/        público  -> {slug, business_name, city_name, province_name, customization}
// GET  /api/stores/public/<slug>/catalog/ público -> {categories, brands, products} (?q=&category=&brand=)
// GET  /api/stores/customization/        Bearer   -> mi diseño web (get_or_create con defaults)
// PATCH /api/stores/customization/       Bearer {display_name?, name_font?, headline?, description?, theme?, accent?,
//                                                whatsapp?, instagram?, tiktok?, facebook?}
//                                        -> 403 si el plan vigente no incluye 'has_customization'
//                                        -> {Exito, customization, storage: {used_bytes, max_mb}}
// POST   /api/stores/customization/logo/ Bearer multipart {logo: archivo} -> {Exito, customization, storage}
// DELETE /api/stores/customization/logo/ Bearer   -> quita el logo y libera la cuota
//                                        -> 403 si falta has_customization; 400 si excede max_storage_mb
// POST   /api/stores/customization/carousel/       Bearer multipart {image} -> {Exito, image, storage}
// DELETE /api/stores/customization/carousel/<id>/  Bearer -> {Exito, storage}
// PATCH  /api/stores/customization/carousel/order/ Bearer {order:[ids]} -> {Exito}

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

  async publicCatalog(slug, { q = '', category = '', brand = '' } = {}) {
    const { data } = await http.get(`/stores/public/${slug}/catalog/`, {
      params: { q: q || undefined, category: category || undefined, brand: brand || undefined }
    })
    return data
  },

  async customization() {
    const { data } = await http.get('/stores/customization/')
    return data
  },

  async updateCustomization(payload) {
    const { data } = await http.patch('/stores/customization/', payload)
    return data
  },

  async uploadLogo(file) {
    const form = new FormData()
    form.append('logo', file)
    // multipart: axios reemplaza el header por el boundary correcto en el browser
    const { data } = await http.post('/stores/customization/logo/', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async removeLogo() {
    const { data } = await http.delete('/stores/customization/logo/')
    return data
  },

  async addCarouselImage(file) {
    const form = new FormData()
    form.append('image', file)
    const { data } = await http.post('/stores/customization/carousel/', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async removeCarouselImage(imageId) {
    const { data } = await http.delete(`/stores/customization/carousel/${imageId}/`)
    return data
  },

  async reorderCarousel(order) {
    const { data } = await http.patch('/stores/customization/carousel/order/', { order })
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
  return `${origin}/${slug}`
}

// ===== Personalización de la web pública (espejo de StoreCustomization) =====
// El backend guarda códigos cerrados (theme/accent); el frontend los traduce a
// paletas CSS. Nada de colores libres del usuario: la web siempre se ve bien.
export const CUSTOMIZATION_DEFAULTS = {
  display_name: '',
  name_font: 'sans',
  headline: '',
  description: '',
  theme: 'light',
  accent: 'indigo',
  whatsapp: '',
  instagram: '',
  tiktok: '',
  facebook: '',
  logo: null,
  carousel: []
}

// Imágenes: límites por archivo (espejo del backend).
export const LOGO_MAX_BYTES = 2 * 1024 * 1024
export const IMAGE_MAX_BYTES = 4 * 1024 * 1024
export const CAROUSEL_MAX_IMAGES = 5
export const LOGO_ACCEPT = 'image/png,image/jpeg,image/webp,image/gif'

export function validateLogoFile(file) {
  if (!file) return 'Elegí una imagen para tu logo'
  if (file.size > LOGO_MAX_BYTES) return 'El logo no puede pesar más de 2 MB'
  if (!LOGO_ACCEPT.split(',').includes(file.type)) return 'Formato no admitido: usá PNG, JPG, WebP o GIF'
  return ''
}

export function validateImageFile(file) {
  if (!file) return 'Elegí una imagen'
  if (file.size > IMAGE_MAX_BYTES) return 'La imagen no puede pesar más de 4 MB'
  if (!LOGO_ACCEPT.split(',').includes(file.type)) return 'Formato no admitido: usá PNG, JPG, WebP o GIF'
  return ''
}

export function formatStorageMB(bytes) {
  return (Number(bytes || 0) / (1024 * 1024)).toFixed(1)
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

// Fuentes del nombre junto al logo: catálogo cerrado (espejo de
// StoreCustomization.FONT_CHOICES). El CSS mapea cada código a su familia.
export const STORE_FONTS = {
  sans:      { label: 'Moderna',    family: 'Inter, system-ui, sans-serif' },
  serif:     { label: 'Elegante',   family: "'Playfair Display', Georgia, serif" },
  rounded:   { label: 'Redondeada', family: 'Nunito, Inter, sans-serif' },
  condensed: { label: 'Condensada', family: 'Oswald, Inter, sans-serif' }
}

export function storeFontFamily(nameFont) {
  return (STORE_FONTS[nameFont] || STORE_FONTS.sans).family
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
const TIKTOK_PATTERN = /^[a-z0-9](?:[a-z0-9._]{0,23}[a-z0-9])?$/
const FACEBOOK_PATTERN = /^[a-z0-9](?:[a-z0-9.]{0,58}[a-z0-9])?$/i

export function validateDisplayName(value) {
  if (value && value.length > 60) return 'El nombre admite hasta 60 caracteres'
  return ''
}

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

export function normalizeTiktok(value) {
  return String(value || '').trim().replace(/^@+/, '').toLowerCase()
}

export function validateTiktok(value) {
  const v = normalizeTiktok(value)
  if (v && !TIKTOK_PATTERN.test(v)) return 'Ingresá solo el usuario, sin "@": letras, números, puntos o guiones bajos'
  return ''
}

export function normalizeFacebook(value) {
  let v = String(value || '').trim().replace(/^\/+|\/+$/g, '')
  if (v.includes('facebook.com/')) v = v.split('facebook.com/')[1].replace(/\/+$/, '').split('/')[0]
  return v
}

export function validateFacebook(value) {
  const v = normalizeFacebook(value)
  if (v && !FACEBOOK_PATTERN.test(v)) return 'Ingresá el nombre de tu página o usuario: letras, números y puntos'
  return ''
}
