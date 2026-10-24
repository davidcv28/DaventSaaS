import { http } from './http.js'
import { storeUrl } from '../config/env.js'

// Dominio stores (StoreApp):
// GET  /api/stores/                      Bearer   -> mi tienda (lista con 0..1, incluye customization,
//                                                   storage: {used_bytes, max_mb, images, max_images} y
//                                                   is_blocked/blocked_reason si el staff la bloqueó;
//                                                   para staff devuelve TODAS las webs con datos del dueño)
// POST /api/stores/                      Bearer {slug} -> claim del link (onboarding)
// PATCH /api/stores/<pk>/                Bearer {slug?, is_published?} -> renombrar / pausar
// GET  /api/stores/slug-available/?slug= Bearer   -> {slug, available, reason: invalid|reserved|taken}
// GET  /api/stores/stats/                  Bearer   -> {total, today, days:[{date,count}] últimos 30 días;
//                                                   cuenta una visita por visitante/día en la web pública}
//                                                   -> 403 sin el beneficio has_stats (plan Básico)
// GET  /api/stores/public/<slug>/        público  -> {slug, business_name, city_name, province_name, customization,
//                                                   has_design_advanced, allowed_templates, location_address} —
//                                                   sin has_design_advanced la web no muestra portada y expone
//                                                   un toggle claro/oscuro al visitante en el nav;
//                                                   allowed_templates es la whitelist de plantillas del plan
//                                                   (la web fuerza 'classic' si el guardado no está permitido);
//                                                   location_address es null sin has_location_map (Estándar+)
//                                                   o si el dueño apagó el mapa (customization.show_location)
// GET  /api/stores/public/<slug>/catalog/ público -> {categories, brands, products}
//                                                   (?q=&category=&brand=&min_price=&max_price=&sort=
//                                                     name|recent|price_asc|price_desc; valores
//                                                     inválidos se ignoran en el backend)
// GET  /api/stores/public/<slug>/contact/captcha/ público -> {challenge_id, question} (captcha antispam)
// POST /api/stores/public/<slug>/contact/       público {name, email, message, website (honeypot),
//                                                        challenge_id, captcha_answer} -> envía el
//                                                        mensaje por email al dueño (throttle 10/h por IP)
// GET  /api/stores/customization/        Bearer   -> mi diseño web (get_or_create con defaults)
// PATCH /api/stores/customization/       Bearer {display_name?, name_font?, name_font_size?, headline?, description?,
//                                                about_title?, about_text?, show_about?, contact_email?, show_contact?,
//                                                theme?, accent?, template?, whatsapp?, instagram?, tiktok?, facebook?, show_location?,
//                                                show_gallery?, show_catalog? (apaga la página Catálogo de la
//                                                web: queda como vidriera del negocio; no borra productos)}
//                                        -> 403 si el plan vigente no incluye 'has_customization'
//                                        -> sin 'has_design_advanced' (premium) el backend descarta
//                                           name_font, name_font_size y accent del payload; template
//                                           se descarta si no está en el nivel del plan (Básico:
//                                           Clásico/Perspectiva; Estándar suma Urbano/Publicidad;
//                                           Premium todo); sin 'has_location_map' (Estándar+)
//                                           descarta show_location
//                                        -> {Exito, customization, storage: {used_bytes, max_mb}}
// POST   /api/stores/customization/logo/ Bearer multipart {logo: archivo} -> {Exito, customization, storage}
// DELETE /api/stores/customization/logo/ Bearer   -> quita el logo y libera la cuota
//                                        -> 403 si falta has_customization; 400 si excede max_storage_mb
// POST   /api/stores/customization/cover/ Bearer multipart {cover: archivo} -> {Exito, customization, storage}
// DELETE /api/stores/customization/cover/ Bearer   -> quita la portada y libera la cuota
//                                        -> 403 sin has_design_advanced (solo premium); el backend normaliza a WebP
// POST   /api/stores/customization/carousel/       Bearer multipart {image} -> {Exito, image, storage}
// DELETE /api/stores/customization/carousel/<id>/  Bearer -> {Exito, storage}
// PATCH  /api/stores/customization/carousel/order/ Bearer {order:[ids]} -> {Exito}
//                                        -> 403 en las 3 si falta has_design_advanced
// POST   /api/stores/customization/gallery/        Bearer multipart {image, kind?: 'gallery'|'decor'} -> {Exito, image, storage}
//                                           kind=decor: hasta 3 imágenes ilustrativas de la portada (solo premium),
//                                           gastan cupo de la galería. El backend normaliza la imagen (WebP, tamaño, proporción).
// DELETE /api/stores/customization/gallery/<id>/   Bearer -> {Exito, storage}
// PATCH  /api/stores/customization/gallery/order/  Bearer {order:[ids]} -> {Exito}
//                                        -> 403 en las 3 si falta has_customization; el tope
//                                           max_gallery_images del plan (Básico 0 / Estándar 5 /
//                                           Premium 15) responde 400 con mensaje
// GET/PATCH /api/stores/chatbot/         Bearer   -> config del chatbot {is_enabled, greeting,
//                                                  qa:[{q,a}] (máx 12, q≤120, a≤500; pares
//                                                  incompletos se descartan en el backend)}
//                                        -> PATCH 403 sin el beneficio has_chatbot (solo Premium)
//                                        -> la web pública lo recibe en `chatbot` del payload
//                                           de /public/<slug>/ solo si está habilitado y el
//                                           plan lo incluye (None en otro caso)

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const storesApi = {
  async listMine() {
    // mine=1: un staff también recibe solo su tienda (sin él, /stores/ lista todas).
    const { data } = await http.get('/stores/', { params: { mine: 1 } })
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

  async stats() {
    // 403 sin el beneficio has_stats (Básico), 404 si aún no hay web creada.
    const { data } = await http.get('/stores/stats/')
    return data
  },

  async publicStore(slug) {
    const { data } = await http.get(`/stores/public/${slug}/`)
    return data
  },

  async publicCatalog(slug, { q = '', category = '', brand = '', min_price = '', max_price = '', sort = '' } = {}) {
    const { data } = await http.get(`/stores/public/${slug}/catalog/`, {
      params: {
        q: q || undefined, category: category || undefined, brand: brand || undefined,
        min_price: min_price || undefined, max_price: max_price || undefined, sort: sort || undefined
      }
    })
    return data
  },

  async contactCaptcha(slug) {
    const { data } = await http.get(`/stores/public/${slug}/contact/captcha/`)
    return data
  },

  async sendContact(slug, payload) {
    const { data } = await http.post(`/stores/public/${slug}/contact/`, payload)
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

  async uploadCover(file) {
    const form = new FormData()
    form.append('cover', file)
    const { data } = await http.post('/stores/customization/cover/', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async removeCover() {
    const { data } = await http.delete('/stores/customization/cover/')
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
  },

  async addGalleryImage(file, kind = 'gallery') {
    const form = new FormData()
    form.append('image', file)
    form.append('kind', kind)
    const { data } = await http.post('/stores/customization/gallery/', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  async removeGalleryImage(imageId) {
    const { data } = await http.delete(`/stores/customization/gallery/${imageId}/`)
    return data
  },

  async reorderGallery(order) {
    const { data } = await http.patch('/stores/customization/gallery/order/', { order })
    return data
  },

  async chatbot() {
    // Config del dueño; PATCH 403 sin has_chatbot (solo Premium).
    const { data } = await http.get('/stores/chatbot/')
    return data
  },

  async updateChatbot(payload) {
    const { data } = await http.patch('/stores/chatbot/', payload)
    return data
  }
}

// Chatbot de la web pública (espejo de StoreChatbot): pares {q, a} que el
// widget responde por coincidencia de palabras. Sin has_chatbot el PATCH da
// 403 y la web pública nunca lo recibe (serializer lo devuelve None).
export const CHATBOT_DEFAULTS = { is_enabled: false, greeting: '', qa: [] }
export const CHATBOT_QA_MAX = 12

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

// Link público canónico: subdominio propio <slug>.<dominio> (env.js/storeUrl).
// La variante <dominio>/<slug> sigue funcionando como alias.
export function publicStoreUrl(slug) {
  return storeUrl(slug)
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
  about_title: '',
  about_text: '',
  about_years: null,
  about_mission: '',
  about_specialties: '',
  show_about: true,
  // Secciones de marketing de la portada (se editan en "Mi empresa"): cada
  // bloque se apaga con su show_* y además se oculta solo en la web cuando
  // quedó vacío. section_order ordena las secciones de la portada (claves
  // de SECTION_ORDER_KEYS); el hero va primero y el contacto último.
  services: [],
  services_title: '',
  show_services: true,
  stats: [],
  show_stats: true,
  testimonials: [],
  testimonials_title: '',
  show_testimonials: true,
  faqs: [],
  faqs_title: '',
  show_faq: true,
  hours: [],
  show_hours: true,
  cta_title: '',
  cta_text: '',
  cta_label: '',
  show_cta: true,
  section_order: [],
  contact_email: '',
  show_contact: true,
  theme: 'light',
  accent: 'indigo',
  template: 'classic',
  whatsapp: '',
  instagram: '',
  tiktok: '',
  facebook: '',
  show_location: true,
  show_gallery: true,
  show_catalog: true,
  logo: null,
  cover: null,
  carousel: [],
  gallery: [],
  decor: []
}

// Imágenes: límites por archivo (espejo del backend).
export const LOGO_MAX_BYTES = 2 * 1024 * 1024
export const IMAGE_MAX_BYTES = 4 * 1024 * 1024
export const CAROUSEL_MAX_IMAGES = 5
export const DECOR_MAX_IMAGES = 3
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

// ===== Secciones de marketing de la portada (espejo del modelo) =====
// Límites por bloque: el backend recorta igual, así que acá solo se evita
// mandar de más y se muestran contadores. Filas incompletas se descartan.
export const MARKETING_LIMITS = {
  services: 6, serviceTitle: 60, serviceText: 160,
  stats: 4, statValue: 20, statLabel: 60,
  testimonials: 6, testimonialName: 60, testimonialDetail: 80, testimonialText: 300,
  faqs: 8, faqQ: 140, faqA: 500,
  hours: 8, hourLabel: 60, hourValue: 60,
  ctaTitle: 120, ctaText: 280, ctaLabel: 40
}

// Iconos elegibles para "Qué ofrecemos" (catálogo cerrado, espejo de
// StoreCustomization.SERVICE_ICONS). Se renderizan con AppIcon.
export const SERVICE_ICONS = {
  'package':        'Productos',
  'truck':          'Envíos',
  'wrench':         'Servicio técnico',
  'tag':            'Ofertas',
  'percent':        'Descuentos',
  'gift':           'Regalos',
  'star':           'Destacado',
  'zap':            'Rápido',
  'shield-check':   'Garantía',
  'clock':          'Horarios',
  'map-pin':        'Ubicación',
  'users':          'Atención',
  'phone':          'Teléfono',
  'message-circle': 'Consultas',
  'store':          'Local',
  'credit-card':    'Tarjetas',
  'wallet':         'Pagos',
  'crown':          'Premium',
  'badge-check':    'Calidad',
  'trending-up':    'Trayectoria',
  'calendar':       'Turnos',
  'flame':          'Novedades',
  'megaphone':      'Promos',
  'check':          'Otro'
}

// Orden de las secciones de la portada (espejo de SECTION_ORDER del modelo):
// el dueño las reordena desde "Mi empresa"; el hero queda primero y el
// contacto último siempre.
export const SECTION_ORDER_KEYS = ['about', 'services', 'stats', 'gallery', 'testimonials', 'faq', 'cta']
export const SECTION_ORDER_LABELS = {
  about:        'Sobre nosotros',
  services:     'Qué ofrecemos',
  stats:        'Tus números',
  gallery:      'Galería',
  testimonials: 'Testimonios',
  faq:          'Preguntas frecuentes',
  cta:          'Llamado a la acción'
}

// Orden efectivo: respeta lo guardado, descarta claves desconocidas y
// completa al final las que falten (mismo criterio del serializer).
export function resolveSectionOrder(saved) {
  const clean = (Array.isArray(saved) ? saved : []).filter((k, i, arr) => SECTION_ORDER_KEYS.includes(k) && arr.indexOf(k) === i)
  return [...clean, ...SECTION_ORDER_KEYS.filter((k) => !clean.includes(k))]
}

export function validateSectionTitle(value) {
  if (value && value.length > 80) return 'El título admite hasta 80 caracteres'
  return ''
}

export function validateCtaTitle(value) {
  if (value && value.length > MARKETING_LIMITS.ctaTitle) return 'El título admite hasta 120 caracteres'
  return ''
}

export function validateCtaText(value) {
  if (value && value.length > MARKETING_LIMITS.ctaText) return 'El texto admite hasta 280 caracteres'
  return ''
}

export function validateCtaLabel(value) {
  if (value && value.length > MARKETING_LIMITS.ctaLabel) return 'El texto del botón admite hasta 40 caracteres'
  return ''
}

export const STORE_ACCENTS = {
  indigo:  { label: 'Índigo',    hex: '#4f46e5', ink: '#4338ca', soft: '#eef2ff' },
  violet:  { label: 'Violeta',   hex: '#7c3aed', ink: '#6d28d9', soft: '#f5f3ff' },
  emerald: { label: 'Esmeralda', hex: '#059669', ink: '#047857', soft: '#ecfdf5' },
  amber:   { label: 'Ámbar',     hex: '#d97706', ink: '#b45309', soft: '#fffbeb' },
  rose:    { label: 'Rosa',      hex: '#e11d48', ink: '#be123c', soft: '#fff1f2' },
  sky:     { label: 'Celeste',   hex: '#0284c7', ink: '#0369a1', soft: '#f0f9ff' },
  orange:  { label: 'Naranja',   hex: '#ea580c', ink: '#c2410c', soft: '#fff7ed' },
  lime:    { label: 'Lima',      hex: '#65a30d', ink: '#4d7c0f', soft: '#f7fee7' }
}

export const STORE_THEMES = {
  light: { label: 'Claro' },
  dark:  { label: 'Oscuro' }
}

// Diseños de la web pública (espejo de StoreCustomization.TEMPLATE_CHOICES)
// por nivel de plan — `tier` marca qué beneficio lo habilita:
//   'base'     -> todo plan con has_customization (Básico)
//   'plus'     -> has_design_plus (Estándar y Premium)
//   'advanced' -> has_design_advanced (Premium)
// El backend descarta del PATCH un diseño fuera del nivel y la web fuerza
// 'classic' si el guardado deja de estar permitido (baja de plan o
// plantilla retirada, como la extinta 'atelier').
export const STORE_TEMPLATES = {
  classic:     { label: 'Clásico',     tier: 'base',     desc: 'Diseño moderno y ordenado, pensado para catálogos: portada centrada y tarjetas de destacados.' },
  perspective: { label: 'Perspectiva', tier: 'base',     desc: 'Profundidad espacial: piso isométrico con punto de fuga, planos flotantes en capas y títulos Oswald con relieve.' },
  street:      { label: 'Urbano',      tier: 'plus',     desc: 'Espíritu streetwear: titulares XXL condensados, pegatina giratoria, código de barras, cinta de colección y relieve duro.' },
  promo:       { label: 'Publicidad',  tier: 'plus',     desc: 'Pensado para promocionar: afiche con sello giratorio, CTA a WhatsApp y cinta de ofertas.' },
  terminal:    { label: 'Terminal',    tier: 'advanced', desc: 'Estética de consola: pantalla de fósforo con tu acento, barra de ventana, prompt >, cursor que parpadea y comandos entre corchetes.' },
  lookbook:    { label: 'Lookbook',    tier: 'advanced', desc: 'Editorial de moda: papel cálido, titulares serif de revista, pliegos de imagen numerados y catálogo como índice de colección.' },
  shop:        { label: 'Tienda Pro',  tier: 'advanced', desc: 'Estilo marketplace: barra superior con buscador, menú de secciones, portada tipo banner con promos y productos destacados.' }
}

// Plantillas elegibles según los beneficios del plan vigente (espejo de
// allowed_templates_of del backend: mismo orden del catálogo). Sirve tanto
// con el dict de benefits del plan como con la lista allowed_templates que
// devuelve /public/<slug>/.
const TEMPLATE_TIER_BENEFIT = { base: null, plus: 'has_design_plus', advanced: 'has_design_advanced' }

export function allowedTemplatesFor(benefits = {}) {
  if (!benefits.has_customization) return ['classic']
  return Object.keys(STORE_TEMPLATES).filter((key) => {
    const need = TEMPLATE_TIER_BENEFIT[STORE_TEMPLATES[key].tier]
    return !need || Boolean(benefits[need])
  })
}

// Normaliza un diseño guardado contra la whitelist: 'classic' si el valor
// no existe en el catálogo o quedó fuera del nivel del plan.
export function resolveStoreTemplate(value, allowed) {
  const list = Array.isArray(allowed) && allowed.length ? allowed : ['classic']
  return STORE_TEMPLATES[value] && list.includes(value) ? value : 'classic'
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
  'fraunces':         { label: 'Fraunces',         family: "'Fraunces', Georgia, serif",          google: 'Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900' },
  'cinzel':           { label: 'Cinzel',           family: "'Cinzel', Georgia, serif",            google: 'Cinzel:wght@400..800' },
  'pacifico':         { label: 'Pacifico',         family: "'Pacifico', cursive",                 google: 'Pacifico' },
  'dancing-script':   { label: 'Dancing Script',   family: "'Dancing Script', cursive",           google: 'Dancing+Script:wght@400..700' },
  'caveat':           { label: 'Caveat',           family: "'Caveat', cursive",                   google: 'Caveat:wght@400..700' },
  'lobster':          { label: 'Lobster',          family: "'Lobster', cursive",                  google: 'Lobster' },
  'space-mono':       { label: 'Space Mono',       family: "'Space Mono', monospace",             google: 'Space+Mono:ital,wght@0,400;0,700;1,400;1,700' },
  'jetbrains-mono':   { label: 'JetBrains Mono',   family: "'JetBrains Mono', monospace",         google: 'JetBrains+Mono:ital,wght@0,400..800;1,400..800' }
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
    '--store-name-size': `${storeNameSize(c.name_font_size)}px`,
    //La fuente elegida aplica a TODO el texto de la web (herencia desde la raíz).
    '--store-font': storeFontFamily(c.name_font)
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

export function validateAboutTitle(value) {
  if (value && value.length > 80) return 'El título admite hasta 80 caracteres'
  return ''
}

export function validateAboutText(value) {
  if (value && value.length > 2000) return 'El texto admite hasta 2000 caracteres'
  return ''
}

export function validateAboutYears(value) {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  if (!Number.isInteger(n) || n < 0 || n > 150) return 'Ingresá un número entero entre 0 y 150'
  return ''
}

export function validateAboutMission(value) {
  if (value && value.length > 400) return 'La misión admite hasta 400 caracteres'
  return ''
}

export function validateAboutSpecialties(value) {
  if (value && value.length > 300) return 'Las especialidades admiten hasta 300 caracteres'
  return ''
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

export function validateContactEmail(value) {
  const v = String(value || '').trim()
  if (v && !EMAIL_PATTERN.test(v)) return 'Ingresá un email válido'
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
