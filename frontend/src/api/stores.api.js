import { http } from './http.js'

// Dominio stores (StoreApp):
// GET  /api/stores/                      Bearer   -> mi tienda (lista con 0..1, incluye customization)
// POST /api/stores/                      Bearer {slug} -> claim del link (onboarding)
// PATCH /api/stores/<pk>/                Bearer {slug?, is_published?} -> renombrar / pausar
// GET  /api/stores/slug-available/?slug= Bearer   -> {slug, available, reason: invalid|reserved|taken}
// GET  /api/stores/public/<slug>/        público  -> {slug, business_name, city_name, province_name, customization,
//                                                   has_design_advanced} — sin has_design_advanced la web no muestra
//                                                   portada y expone un toggle claro/oscuro al visitante en el nav
// GET  /api/stores/public/<slug>/catalog/ público -> {categories, brands, products} (?q=&category=&brand=)
// GET  /api/stores/customization/        Bearer   -> mi diseño web (get_or_create con defaults)
// PATCH /api/stores/customization/       Bearer {display_name?, name_font?, name_font_size?, headline?, description?,
//                                                theme?, accent?, whatsapp?, instagram?, tiktok?, facebook?}
//                                        -> 403 si el plan vigente no incluye 'has_customization'
//                                        -> sin 'has_design_advanced' (premium) el backend descarta
//                                           name_font, name_font_size y accent del payload
//                                        -> {Exito, customization, storage: {used_bytes, max_mb}}
// POST   /api/stores/customization/logo/ Bearer multipart {logo: archivo} -> {Exito, customization, storage}
// DELETE /api/stores/customization/logo/ Bearer   -> quita el logo y libera la cuota
//                                        -> 403 si falta has_customization; 400 si excede max_storage_mb
// POST   /api/stores/customization/carousel/       Bearer multipart {image} -> {Exito, image, storage}
// DELETE /api/stores/customization/carousel/<id>/  Bearer -> {Exito, storage}
// PATCH  /api/stores/customization/carousel/order/ Bearer {order:[ids]} -> {Exito}
//                                        -> 403 en las 3 si falta has_design_advanced

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
  name_font: 'inter',
  name_font_size: 32,
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

// Fuentes del nombre junto al logo: catálogo cerrado de Google Fonts
// (espejo de StoreCustomization.FONT_CHOICES). `google` es el query del
// css2 de Google Fonts; null = ya viene cargada (Inter va en index.html).
export const STORE_FONTS = {
  'inter':            { label: 'Inter',            family: 'Inter, system-ui, sans-serif',        google: null },
  'montserrat':       { label: 'Montserrat',       family: "'Montserrat', sans-serif",            google: 'Montserrat:wght@400..800' },
  'poppins':          { label: 'Poppins',          family: "'Poppins', sans-serif",               google: 'Poppins:wght@400;600;700;800' },
  'raleway':          { label: 'Raleway',          family: "'Raleway', sans-serif",               google: 'Raleway:wght@400..800' },
  'nunito':           { label: 'Nunito',           family: "'Nunito', sans-serif",                google: 'Nunito:wght@400..800' },
  'work-sans':        { label: 'Work Sans',        family: "'Work Sans', sans-serif",             google: 'Work+Sans:wght@400..800' },
  'dm-sans':          { label: 'DM Sans',          family: "'DM Sans', sans-serif",               google: 'DM+Sans:wght@400..800' },
  'sora':             { label: 'Sora',             family: "'Sora', sans-serif",                  google: 'Sora:wght@400..800' },
  'space-grotesk':    { label: 'Space Grotesk',    family: "'Space Grotesk', sans-serif",         google: 'Space+Grotesk:wght@400..700' },
  'comfortaa':        { label: 'Comfortaa',        family: "'Comfortaa', sans-serif",             google: 'Comfortaa:wght@400..700' },
  'quicksand':        { label: 'Quicksand',        family: "'Quicksand', sans-serif",             google: 'Quicksand:wght@400..700' },
  'rubik':            { label: 'Rubik',            family: "'Rubik', sans-serif",                 google: 'Rubik:wght@400..800' },
  'oswald':           { label: 'Oswald',           family: "'Oswald', sans-serif",                google: 'Oswald:wght@400..700' },
  'bebas-neue':       { label: 'Bebas Neue',       family: "'Bebas Neue', sans-serif",            google: 'Bebas+Neue' },
  'anton':            { label: 'Anton',            family: "'Anton', sans-serif",                 google: 'Anton' },
  'archivo-black':    { label: 'Archivo Black',    family: "'Archivo Black', sans-serif",         google: 'Archivo+Black' },
  'righteous':        { label: 'Righteous',        family: "'Righteous', sans-serif",             google: 'Righteous' },
  'playfair-display': { label: 'Playfair Display', family: "'Playfair Display', Georgia, serif",  google: 'Playfair+Display:wght@400..800' },
  'merriweather':     { label: 'Merriweather',     family: "'Merriweather', Georgia, serif",      google: 'Merriweather:wght@400..800' },
  'lora':             { label: 'Lora',             family: "'Lora', Georgia, serif",              google: 'Lora:wght@400..700' },
  'fraunces':         { label: 'Fraunces',         family: "'Fraunces', Georgia, serif",          google: 'Fraunces:wght@400..800' },
  'cinzel':           { label: 'Cinzel',           family: "'Cinzel', Georgia, serif",            google: 'Cinzel:wght@400..800' },
  'pacifico':         { label: 'Pacifico',         family: "'Pacifico', cursive",                 google: 'Pacifico' },
  'dancing-script':   { label: 'Dancing Script',   family: "'Dancing Script', cursive",           google: 'Dancing+Script:wght@400..700' },
  'caveat':           { label: 'Caveat',           family: "'Caveat', cursive",                   google: 'Caveat:wght@400..700' },
  'lobster':          { label: 'Lobster',          family: "'Lobster', cursive",                  google: 'Lobster' }
}

export function storeFontFamily(nameFont) {
  return (STORE_FONTS[nameFont] || STORE_FONTS.inter).family
}

// Carga on-demand de la fuente elegida: inyecta el <link> del css2 una sola
// vez por familia. La web pública y el folleto solo piden la del diseño;
// el selector del dashboard carga el listado completo (ensureStoreFontList).
const loadedFonts = new Set()
const FONT_CSS_BASE = 'https://fonts.googleapis.com/css2'

function injectFontLink(id, href) {
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = href
  document.head.appendChild(link)
}

export function ensureStoreFont(nameFont) {
  const font = STORE_FONTS[nameFont]
  if (!font || !font.google || loadedFonts.has(nameFont)) return
  loadedFonts.add(nameFont)
  injectFontLink(`store-font-${nameFont}`, `${FONT_CSS_BASE}?family=${font.google}&display=swap`)
}

export function ensureStoreFontList() {
  if (loadedFonts.has('__all__')) return
  loadedFonts.add('__all__')
  Object.keys(STORE_FONTS).forEach((k) => loadedFonts.add(k))
  const families = Object.values(STORE_FONTS)
    .filter((f) => f.google)
    .map((f) => `family=${f.google}`)
    .sort()
    .join('&')
  injectFontLink('store-fonts-all', `${FONT_CSS_BASE}?${families}&display=swap`)
}

// Tamaño del nombre junto al logo (espejo de los validators del modelo).
export const NAME_FONT_SIZE_MIN = 20
export const NAME_FONT_SIZE_MAX = 64
export const NAME_FONT_SIZE_DEFAULT = 32

export function storeNameSize(size) {
  const n = Number(size)
  return Number.isFinite(n) ? Math.min(NAME_FONT_SIZE_MAX, Math.max(NAME_FONT_SIZE_MIN, n)) : NAME_FONT_SIZE_DEFAULT
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
    '--store-accent-soft': a.soft,
    '--store-name-size': `${storeNameSize(c.name_font_size)}px`
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
