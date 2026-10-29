import { http, publicHttp } from './http.js'
import { storeUrl } from '../config/env.js'
import { isHex, deriveAccent, bandPalette } from '../utils/colorTools.js'

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
//                                                   (la web fuerza 'raiz' si el guardado no está permitido);
//                                                   location_address es null sin has_location_map (Estándar+)
//                                                   o si el dueño apagó el mapa (customization.show_location);
//                                                   service_items = servicios activos [{id,name,description,
//                                                   price,duration,icon}] — vacío si la página Servicios no
//                                                   está en site_templates efectivo o sin has_services_site;
//                                                   customization.site_templates ya llega como set EFECTIVO
//                                                   (guardado ∩ plan) y site_mode/site_services derivados
//                                                   de compat: catalog | marketing | both
// GET  /api/stores/public/<slug>/catalog/ público -> {categories, brands, products, promotions,
//                                                   facets, offer_count, new_count, price_max}
//                                                   (?q= texto que busca en nombre, descripción, categoría,
//                                                     marca y características; &category=1,2 &brand=3,4
//                                                     multi-selección; &features={"Talle":["M"]} JSON;
//                                                     &offer=1 &new=1 solo ofertas / novedades (7 días);
//                                                     &min_price= &max_price= sobre el precio efectivo;
//                                                     &sort= name|recent|price_asc|price_desc;
//                                                     valores inválidos se ignoran en el backend.
//                                                     facets = [{name, values:[{value,count}]}] con los
//                                                     atributos del catálogo para el panel de filtros)
// GET  /api/stores/public/<slug>/contact/captcha/ público -> {challenge_id, question} (captcha antispam)
// POST /api/stores/public/<slug>/contact/       público {name, email, message, website (honeypot),
//                                                        challenge_id, captcha_answer} -> envía el
//                                                        mensaje por email al dueño (throttle 10/h por IP)
// GET  /api/stores/public/<slug>/reviews/captcha/ público -> {challenge_id, question} (mismo captcha)
// GET  /api/stores/public/<slug>/products/<id>/reviews/ público -> [{is_positive, text, name, surname_initial, created_at}]
// POST /api/stores/public/<slug>/products/<id>/reviews/ público {is_positive? (like/dislike), text?, name, surname, email,
//                                                        website (honeypot), challenge_id, captcha_answer}
//                                                        -> 404 si la tienda apagó valoraciones y comentarios;
//                                                        el texto solo viaja con show_comments (premium,
//                                                        has_product_comments); throttle 10/h por IP
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
//                                           Raíz; Estándar suma Trama; Premium suma Circuito;
//                                           Premium todo); sin 'has_location_map' (Estándar+)
//                                           descarta show_location; sin 'has_product_comments'
//                                           (premium) descarta show_comments
//                                        -> {Exito, customization, storage: {used_bytes, max_mb}}
// Flujo borrador → publicar del Studio (los *_draft editan sin tocar la
// web; publish aplica y guarda versión — últimas 10 por tienda):
// POST   /api/stores/customization/publish/   Bearer {note?} -> {Exito, customization}
// POST   /api/stores/customization/discard/   Bearer -> {Exito, customization}
// GET    /api/stores/customization/versions/  Bearer -> [{id, note, created_at, snapshot}]
// POST   /api/stores/customization/restore/<id>/ Bearer -> {Exito, customization}
// POST   /api/stores/customization/share/     Bearer -> {token, path, expires_at, ttl}
//                                        (link temporal /<slug>?preview=<t>: la web
//                                        muestra el borrador sin auth, vence en 72 h)
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
// Diseñar con IA (motor local determinista, sin llamadas a servicios de IA):
// POST /api/stores/ai-design/            Bearer {rubro?, goals?: string[],
//                                                  tone?: calido|serio|moderno|audaz,
//                                                  audience?, must_have?: string[], seed?}
//                                        -> {engine, seed, missing: string[],
//                                            proposals: [{id, label, why, template, site_theme,
//                                              layout_config, copy: {headline, description,
//                                              cta_title, cta_text, cta_label}, notes}]}
//                                        (2 o 3 propuestas; template siempre dentro de
//                                         allowed_templates_of(user); 403 sin has_customization
//                                         o sin has_ai_design; 429 throttle 'ai_design' 20/h)
// POST /api/stores/ai-design/apply/      Bearer {seed, proposal_id} -> {Exito, customization, storage}
//                                        (recalcula server-side y escribe SOLO el borrador;
//                                         el copy solo rellena campos vacíos; publicar y
//                                         descartar siguen por customization/publish|discard)

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

// Params canónicos del catálogo público: una sola forma por combinación de
// filtros (ids ordenados, features con claves/valores ordenados, vacíos en
// undefined) — la usa publicCatalog para la request y StorePublicLayout
// para la clave del cache compartido.
export function normalizeCatalogParams({ q = '', category = '', brand = '', min_price = '', max_price = '', sort = '', features = null, offer = false, is_new = false } = {}) {
  const ids = (v) => [...new Set([].concat(v || []).map((x) => Number(x)).filter((n) => Number.isInteger(n) && n > 0))].sort((a, b) => a - b).join(',')
  const feats = {}
  if (features && typeof features === 'object') {
    for (const name of Object.keys(features).sort()) {
      const values = [...new Set([].concat(features[name] || []).map((v) => String(v).trim()).filter(Boolean))].sort()
      if (name.trim() && values.length) feats[name.trim()] = values
    }
  }
  return {
    q: String(q || '').trim() || undefined,
    category: ids(category) || undefined,
    brand: ids(brand) || undefined,
    min_price: min_price !== '' && min_price != null ? min_price : undefined,
    max_price: max_price !== '' && max_price != null ? max_price : undefined,
    sort: sort || undefined,
    features: Object.keys(feats).length ? JSON.stringify(feats) : undefined,
    offer: offer ? '1' : undefined,
    new: is_new ? '1' : undefined
  }
}

export const storesApi = {
  async listMine() {
    // mine=1: un staff también recibe solo su tienda (sin él, /stores/ lista todas).
    const { data } = await http.get('/stores/', { params: { mine: 1, page_size: 200 } })
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

  async publicStore(slug, { preview } = {}) {
    // ?preview=<token firmado>: el backend muestra el borrador del Studio
    // (link temporal de "compartir vista previa") en vez de lo publicado.
    const { data } = await publicHttp.get(`/stores/public/${slug}/`, { params: preview ? { preview } : {} })
    return data
  },

  async publicCatalog(slug, params = {}) {
    const { data } = await publicHttp.get(`/stores/public/${slug}/catalog/`, { params: normalizeCatalogParams(params) })
    return data
  },

  async contactCaptcha(slug) {
    const { data } = await publicHttp.get(`/stores/public/${slug}/contact/captcha/`)
    return data
  },

  async sendContact(slug, payload) {
    const { data } = await publicHttp.post(`/stores/public/${slug}/contact/`, payload)
    return data
  },

  // Opiniones de producto (valoraciones/comentarios de visitantes): mismo
  // captcha firmado que el contacto + honeypot 'website' en el payload.
  async reviewCaptcha(slug) {
    const { data } = await publicHttp.get(`/stores/public/${slug}/reviews/captcha/`)
    return data
  },

  async productReviews(slug, productId) {
    const { data } = await publicHttp.get(`/stores/public/${slug}/products/${productId}/reviews/`)
    return data
  },

  async sendProductReview(slug, productId, payload) {
    const { data } = await publicHttp.post(`/stores/public/${slug}/products/${productId}/reviews/`, payload)
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

  // Diseñar con IA: propuestas (2-3) a partir de las respuestas del dueño y
  // aplicación de una al borrador. El backend recalcula: apply solo recibe
  // seed + proposal_id, nunca el layout del cliente.
  async aiDesign(payload = {}) {
    const { data } = await http.post('/stores/ai-design/', payload)
    return data
  },

  async aiDesignApply({ seed, proposal_id, extras = null, skip_extras = false }) {
    const payload = { seed, proposal_id }
    if (extras) payload.extras = extras
    if (skip_extras) payload.skip_extras = true
    const { data } = await http.post('/stores/ai-design/apply/', payload)
    return data
  },

  // Studio — flujo borrador → publicar: publish aplica los *_draft a la
  // web y guarda la versión; discard los vuelve a lo publicado; versions
  // lista el historial y restore recupera un snapshot; sharePreview emite
  // el token firmado del link temporal /<slug>?preview=<token> (72 h).
  async publishCustomization(note = '') {
    const { data } = await http.post('/stores/customization/publish/', { note })
    return data
  },
  async discardCustomization() {
    const { data } = await http.post('/stores/customization/discard/')
    return data
  },
  async studioVersions() {
    const { data } = await http.get('/stores/customization/versions/')
    return data
  },
  async restoreStudioVersion(versionId) {
    const { data } = await http.post(`/stores/customization/restore/${versionId}/`)
    return data
  },
  async sharePreview() {
    const { data } = await http.post('/stores/customization/share/')
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
  // quedó vacío. Las secciones de la portada se muestran en un orden fijo
  // (SECTION_ORDER_KEYS); el hero va primero y el contacto último.
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
  // Bloques extra: cinta de anuncios bajo la portada (marquee {icon, text}),
  // sección Video (embed YouTube/Vimeo ya normalizado por el backend),
  // aviso que encabeza el catálogo y línea extra del pie.
  announcements: [],
  show_announcements: true,
  video_url: '',
  video_title: '',
  show_video: true,
  catalog_note: '',
  footer_text: '',
  // Bloques del rediseño de portada (espejo del modelo): garantías, hitos y
  // equipo viajan en JSON; ofertas/marcas/cuenta regresiva son automáticos
  // y solo conservan su show_* (se auto-ocultan sin datos).
  benefits: [],
  show_benefits: true,
  timeline: [],
  show_timeline: true,
  team: [],
  show_team: true,
  show_offers: true,
  show_brands: true,
  show_countdown: true,
  contact_email: '',
  show_contact: true,
  theme: 'light',
  accent: 'indigo',
  accent_custom: '',
  logo_scale: 'm',
  logo_mode: 'logo_name',
  mono_style: 'accent',
  cover_overlay: 0,
  cover_focus_x: 50,
  cover_focus_y: 50,
  template: 'raiz',
  whatsapp: '',
  instagram: '',
  tiktok: '',
  facebook: '',
  show_location: true,
  show_gallery: true,
  show_catalog: true,
  // Páginas de la web: portada + servicios + catálogo (el backend deriva
  // show_catalog y expone site_mode de compat para las plantillas viejas).
  site_templates: ['landing', 'catalog'],
  site_mode: 'both',
  // Página "Servicios": pasos del embudo, días/franjas del pedido y notas.
  service_steps: [],
  service_days: [],
  service_slots: [],
  service_ask_address: true,
  service_price_note: '',
  service_pay_note: '',
  show_highlights: true,
  show_reviews: false,
  show_comments: false,
  logo: null,
  cover: null,
  carousel: [],
  gallery: [],
  decor: []
}

// ===== Páginas de la web (espejo de services/services.py del backend) =====
// site_templates es multi-selección de catálogo cerrado: 'landing' =
// portada de marketing, 'services' = página de servicios con pedidos por
// WhatsApp, 'catalog' = catálogo de productos. El plan fija el cupo
// (max_site_templates) y 'services' exige además el flag has_services_site;
// el backend fuerza ambas reglas en el PATCH de customization (400) y la
// web pública recibe el set EFECTIVO (guardado ∩ plan vigente).
export const SITE_TEMPLATE_KEYS = ['landing', 'services', 'catalog']
export const SITE_TEMPLATES = {
  landing:  { label: 'Portada',   icon: 'store',        desc: 'Tu página principal: presentación, secciones de marketing y contacto.' },
  services: { label: 'Servicios', icon: 'wrench',       desc: 'Listá tus servicios con precios orientativos y recibí pedidos por WhatsApp. Sin pagos online.', benefit: 'has_services_site' },
  catalog:  { label: 'Catálogo',  icon: 'package',      desc: 'Tu catálogo de productos con buscador, filtros y fichas.' }
}
// Web mínima por defecto (misma conducta que el viejo site_mode='both').
export const DEFAULT_SITE_TEMPLATES = ['landing', 'catalog']

// Tope de páginas según el plan: max_site_templates ausente -> 2 (piso
// histórico portada+catálogo); null -> las tres.
export function siteTemplatesLimit(benefits = {}) {
  if (!('max_site_templates' in benefits)) return 2
  return benefits.max_site_templates
}

// Páginas elegibles por el plan: 'services' solo con has_services_site.
export function allowedSiteTemplatesFor(benefits = {}) {
  return SITE_TEMPLATE_KEYS.filter((key) => key !== 'services' || benefits.has_services_site)
}

// Normaliza un set guardado: whitelist, sin repetidas, orden canónico.
export function normalizeSiteTemplates(value) {
  if (!Array.isArray(value)) return []
  return SITE_TEMPLATE_KEYS.filter((key) => value.includes(key))
}

// Set efectivo para mostrar (dashboard/público): guardado normalizado ∩
// permitido por el plan, recortado al cupo; vacío -> default.
export function resolveSiteTemplates(saved, benefits = {}) {
  const allowed = allowedSiteTemplatesFor(benefits)
  let list = normalizeSiteTemplates(saved).filter((key) => allowed.includes(key))
  const limit = siteTemplatesLimit(benefits)
  if (limit != null) list = list.slice(0, limit)
  return list.length ? list : [...DEFAULT_SITE_TEMPLATES]
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
  benefits: 6, benefitTitle: 40, benefitText: 90,
  timeline: 6, timelineLabel: 24, timelineText: 160,
  team: 6, teamName: 60, teamRole: 60,
  ctaTitle: 120, ctaText: 280, ctaLabel: 40,
  announcements: 6, announcementText: 60,
  videoUrl: 300, videoTitle: 80,
  catalogNote: 160, footerText: 160
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
  'check':          'Otro',
  'sparkles':       'Destellos',
  'award':          'Premio',
  'hard-hat':       'Construcción',
  'scissors':       'Corte / Estilo',
  'coffee':         'Café / Bebidas',
  'dumbbell':       'Deporte / Gimnasio',
  'paw-print':      'Mascotas',
  'flower':         'Flores / Naturaleza',
  'book':           'Libros / Educación',
  'graduation-cap': 'Cursos / Títulos',
  'music':          'Música',
  'film':           'Video / Cine',
  'camera':         'Fotografía',
  'heart':          'Salud / Bienestar',
  'hand':           'Apoyo / Ayuda',
  'leaf':           'Ecológico / Orgánico',
  'umbrella':       'Protección / Respaldo',
  'paintbrush':     'Pintura / Diseño',
  'mic':            'Audio / Locución',
  'trophy':         'Logros',
  'diamond':        'Lujo / Joyería'
}

// Color identidad por ícono de servicio (hue HSL): el panel lo usa para las
// tarjetas del admin y la página Servicios para los tiles del picker — mismo
// ícono, mismo color en toda la plataforma.
export const SERVICE_HUES = {
  'package': 215, 'truck': 28, 'wrench': 250, 'tag': 330, 'percent': 350, 'gift': 300,
  'star': 45, 'zap': 38, 'shield-check': 160, 'clock': 195, 'map-pin': 5, 'users': 265,
  'phone': 140, 'message-circle': 170, 'store': 20, 'credit-card': 225, 'wallet': 100,
  'crown': 48, 'badge-check': 155, 'trending-up': 130, 'calendar': 280, 'flame': 15,
  'megaphone': 320, 'check': 200, 'sparkles': 290, 'award': 42, 'hard-hat': 36, 'scissors': 335, 'coffee': 25,
  'dumbbell': 235, 'paw-print': 22, 'flower': 325, 'book': 210, 'graduation-cap': 240, 'music': 275,
  'film': 255, 'camera': 185, 'heart': 345, 'hand': 30, 'leaf': 120, 'umbrella': 205,
  'paintbrush': 310, 'mic': 0, 'trophy': 50, 'diamond': 190
}
export const serviceHue = (key) => SERVICE_HUES[key] ?? 250

// Orden fijo de las secciones de la portada (espejo de SECTION_ORDER del
// modelo): la web pública lo aplica siempre así — no es editable por el
// usuario; el hero queda primero y el contacto último siempre.
export const SECTION_ORDER_KEYS = ['about', 'services', 'stats', 'benefits', 'offers', 'brands', 'countdown', 'gallery', 'testimonials', 'timeline', 'team', 'faq', 'video', 'cta']
// Bloques automáticos (sin contenido propio en customization): la sección
// Ofertas sale del catálogo (ítems con oferta efectiva), la marquesina de
// las marcas cargadas y la cuenta regresiva del descuento vigente con fin
// más próximo. Solo tienen show_* — se auto-ocultan cuando no hay datos.
export const AUTO_SECTION_KEYS = ['offers', 'brands', 'countdown']

// Video de la portada: el backend normaliza a la URL de embed oficial
// (youtube-nocookie / player.vimeo) — el iframe usa video_url tal cual.
// Acá solo se valida el formato para avisar antes de guardar.
export function validateVideoUrl(value) {
  const v = String(value || '').trim()
  if (!v) return ''
  if (v.length > 300) return 'El link del video admite hasta 300 caracteres'
  if (/^(https?:\/\/)?(www\.|m\.|music\.)?youtube\.com\/(watch\?.*v=|embed\/|shorts\/|live\/)[\w-]{6,20}/i.test(v)) return ''
  if (/^(https?:\/\/)?(www\.)?youtu\.be\/[\w-]{6,20}/i.test(v)) return ''
  if (/^(https?:\/\/)?(www\.|player\.)?vimeo\.com\/(video\/)?\d{5,}/i.test(v)) return ''
  return 'Solo se admiten videos de YouTube o Vimeo. Pegá el link completo del video.'
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
// — catálogo de 3, uno por nivel, organizado por RUBRO (no por "estilo de
// autor"). `tier` marca qué beneficio lo habilita:
//   'base'     -> todo plan con has_customization (Básico)
//   'plus'     -> has_design_plus (Estándar y Premium)
//   'advanced' -> has_design_advanced (Premium)
// El backend descarta del PATCH un diseño fuera del nivel y la web fuerza
// 'raiz' (fallback global) si el guardado deja de estar permitido (baja de
// plan o una plantilla retirada). Todo diseño retirado se remapea por
// afinidad de rubro al más cercano del catálogo (STORE_TEMPLATE_RETIRED_MAP).
export const STORE_TEMPLATES = {
  raiz:     { label: 'Raíz',     rubro: 'general',      tier: 'base',     defaultAccent: '#0F766E', desc: 'Generalista, claro y comercial: retail y servicios con portada partida, garantías y presupuesto.' },
  trama:    { label: 'Trama',    rubro: 'indumentaria', tier: 'plus',     defaultAccent: '#E4472B', desc: 'Editorial de moda: blanco y tinta, titulares condensados, marquee de acento y lookbook.' },
  circuito: { label: 'Circuito', rubro: 'tecnologia',   tier: 'advanced', defaultAccent: '#22D3EE', desc: 'Tecnología oscura y técnica: retícula sutil, mono en etiquetas y tarjetas de producto con specs.' },
}

// Familias de diseño para el selector del dashboard: una por RUBRO, con los
// diseños de ese rubro (el sistema queda listo para sumar comida, bebida,
// etc. sin tocar el render de estos 3).
export const STORE_TEMPLATE_FAMILIES = [
  { key: 'general',      label: 'Generalista',  caption: 'Retail y servicios', templates: ['raiz'] },
  { key: 'indumentaria', label: 'Indumentaria', caption: 'Moda y accesorios',   templates: ['trama'] },
  { key: 'tecnologia',   label: 'Tecnología',   caption: 'Electrónica y tech',  templates: ['circuito'] },
]
export const FAMILY_TEMPLATE_KEYS = STORE_TEMPLATE_FAMILIES.flatMap((f) => f.templates)

// Mapa de retiro (espejo de StoreCustomization.TEMPLATE_RETIRED_MAP): una
// tienda con un diseño viejo se sirve con el nuevo equivalente, nunca cae al
// fallback ni rompe el render.
export const STORE_TEMPLATE_RETIRED_MAP = {
  classic: 'raiz', duo: 'raiz', minimal: 'raiz', calma: 'raiz',
  mercado: 'raiz', studio: 'raiz', arena: 'raiz', proceso: 'raiz',
  carta: 'raiz', terra: 'raiz', bloque: 'raiz', shop: 'raiz',
  atelier: 'trama', lookbook: 'trama', boutique: 'trama', signature: 'trama',
  cobre: 'trama', vitrina: 'trama', street: 'trama', riso: 'trama',
  promo: 'trama', aurora: 'trama',
  perspective: 'circuito', circuit: 'circuito', terminal: 'circuito',
  lab: 'circuito', ai_lumen: 'circuito', ai_pulse: 'trama',
}

// Patrones exclusivos del motor "Diseñar con IA": ya no existen (el motor
// propone los 3 diseños del catálogo). Se conservan vacíos por compatibilidad
// con los consumidores que los importan.
export const AI_ONLY_TEMPLATES = []
export const AI_LEGACY_TEMPLATES = []
export const AI_EXTRA_TEMPLATES = []

// Plantillas elegibles según los beneficios del plan vigente (espejo de
// allowed_templates_of del backend: mismo orden del catálogo). Sirve tanto
// con el dict de benefits del plan como con la lista allowed_templates que
// devuelve /public/<slug>/.
const TEMPLATE_TIER_BENEFIT = { base: null, plus: 'has_design_plus', advanced: 'has_design_advanced' }

export function allowedTemplatesFor(benefits = {}) {
  if (!benefits.has_customization) return ['raiz']
  return Object.keys(STORE_TEMPLATES).filter((key) => {
    const need = TEMPLATE_TIER_BENEFIT[STORE_TEMPLATES[key].tier]
    return !need || Boolean(benefits[need])
  })
}

// Normaliza un diseño guardado contra la whitelist: 'raiz' si el valor no
// existe en el catálogo o quedó fuera del nivel del plan. Un id retirado se
// remapea a su equivalente antes de validar.
export function resolveStoreTemplate(value, allowed) {
  const list = Array.isArray(allowed) && allowed.length ? allowed : ['raiz']
  const normalized = STORE_TEMPLATE_RETIRED_MAP[value] || value
  const known = Boolean(STORE_TEMPLATES[normalized])
  return known && list.includes(normalized) ? normalized : 'raiz'
}

// Fuentes del nombre junto al logo: catálogo cerrado de Google Fonts
// (espejo de StoreCustomization.FONT_CHOICES). `google` es el query del
// css2 de Google Fonts; null = ya viene cargada (Inter va en index.html).
// Es el superset para RENDERIZAR — una tienda con una fuente guardada de
// otra época o una display de plantilla (p.ej. Orbitron en 'arena') la
// sigue mostrando; el selector del dashboard ofrece solo las populares
// (STORE_FONT_GROUPS / STORE_FONT_PICKER).
export const STORE_FONTS = {
  'inter':            { label: 'Inter',            family: 'Inter, system-ui, sans-serif',        google: null },
  'roboto':           { label: 'Roboto',           family: "'Roboto', sans-serif",                google: 'Roboto:wght@400;500;700;900' },
  'open-sans':        { label: 'Open Sans',        family: "'Open Sans', sans-serif",             google: 'Open+Sans:wght@400..800' },
  'lato':             { label: 'Lato',             family: "'Lato', sans-serif",                  google: 'Lato:wght@400;700;900' },
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
  'jetbrains-mono':   { label: 'JetBrains Mono',   family: "'JetBrains Mono', monospace",         google: 'JetBrains+Mono:ital,wght@0,400..800;1,400..800' },
  'manrope':          { label: 'Manrope',          family: "'Manrope', sans-serif",               google: 'Manrope:wght@400..800' },
  'archivo':          { label: 'Archivo',          family: "'Archivo', 'Helvetica Neue', sans-serif", google: 'Archivo:wdth,wght@62..125,400..900' },
  'bricolage-grotesque': { label: 'Bricolage Grotesque', family: "'Bricolage Grotesque', 'Arial Black', sans-serif", google: 'Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,400..800' },
  'orbitron':         { label: 'Orbitron',        family: "'Orbitron', 'Arial Black', sans-serif",    google: 'Orbitron:wght@500..900' },
  'figtree':          { label: 'Figtree',          family: "'Figtree', system-ui, sans-serif",     google: 'Figtree:wght@400..700' },
  // Familias del motor de IA (typography.roles): sin entrada acá la familia
  // no se carga y el rol cae a Inter (el diseño se ve distinto al propuesto).
  'cormorant-garamond': { label: 'Cormorant Garamond', family: "'Cormorant Garamond', Georgia, serif", google: 'Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400' },
  'dm-serif-display': { label: 'DM Serif Display', family: "'DM Serif Display', Georgia, serif",   google: 'DM+Serif+Display' },
  'libre-baskerville':{ label: 'Libre Baskerville', family: "'Libre Baskerville', Georgia, serif",  google: 'Libre+Baskerville:ital,wght@0,400;0,700;1,400' },
  'outfit':           { label: 'Outfit',           family: "'Outfit', system-ui, sans-serif",      google: 'Outfit:wght@300..900' },
  'plus-jakarta-sans':{ label: 'Plus Jakarta Sans', family: "'Plus Jakarta Sans', system-ui, sans-serif", google: 'Plus+Jakarta+Sans:wght@300..800' }
}

export function storeFontFamily(nameFont) {
  return (STORE_FONTS[nameFont] || STORE_FONTS.inter).family
}

// Selector del Diseño web: SOLO las fuentes más populares del mercado
// (Google Fonts de adopción masiva), agrupadas por estilo para el
// <optgroup> del select. Las display/exóticas del superset no se ofrecen:
// quedan para renderizar diseños guardados y tipografía propia de
// plantillas — nunca para elección libre del usuario.
export const STORE_FONT_GROUPS = [
  { label: 'Sans serif',  keys: ['inter', 'roboto', 'open-sans', 'lato', 'montserrat', 'poppins', 'raleway', 'nunito', 'dm-sans', 'work-sans', 'rubik', 'manrope'] },
  { label: 'Serif',       keys: ['playfair-display', 'merriweather', 'lora'] },
  { label: 'Display',     keys: ['oswald', 'bebas-neue', 'anton'] },
  { label: 'Manuscritas', keys: ['dancing-script', 'pacifico'] },
]
export const STORE_FONT_PICKER = STORE_FONT_GROUPS.flatMap((g) => g.keys)

// Carga on-demand de la fuente elegida: inyecta el <link> del css2 una sola
// vez por familia. La web pública y el folleto solo piden la del diseño;
// el selector del dashboard trae las del picker en un único <link>
// (ensureStoreFontPicker) para que la vista previa las muestre al instante.
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

export function ensureStoreFontPicker() {
  if (loadedFonts.has('__picker__')) return
  loadedFonts.add('__picker__')
  STORE_FONT_PICKER.forEach((k) => loadedFonts.add(k))
  const families = STORE_FONT_PICKER
    .map((k) => STORE_FONTS[k]?.google)
    .filter(Boolean)
    .sort()
    .map((g) => `family=${g}`)
    .join('&')
  injectFontLink('store-fonts-picker', `${FONT_CSS_BASE}?${families}&display=swap`)
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

export const LOGO_SCALES = { s: 0.8, m: 1, l: 1.3 }

export function effectiveAccent(customization) {
  const c = customization || {}
  return isHex(c.accent_custom) ? deriveAccent(c.accent_custom) : accentMeta(c.accent)
}

export function storeThemeVars(customization) {
  const c = { ...CUSTOMIZATION_DEFAULTS, ...(customization || {}) }
  const a = effectiveAccent(c)
  const band = bandPalette(a.hex)
  return {
    '--store-accent': a.hex,
    '--store-accent-ink': a.ink,
    '--store-accent-soft': a.soft,
    // Banda de acento con texto blanco garantizado (hero, inicial, placas).
    '--sp-band-c1': band.c1,
    '--sp-band-c2': band.c2,
    '--sp-band-c3': band.c3,
    '--sp-band-c4': band.c4,
    '--sp-band-base1': band.base1,
    '--sp-band-base2': band.base2,
    '--sp-band-mark': band.mark,
    '--store-name-size': `${storeNameSize(c.name_font_size)}px`,
    //La fuente elegida aplica a TODO el texto de la web (herencia desde la raíz).
    '--store-font': storeFontFamily(c.name_font),
    '--store-logo-scale': LOGO_SCALES[c.logo_scale] || 1,
    '--store-cover-overlay': Math.min(80, Math.max(0, Number(c.cover_overlay) || 0)) / 100,
    '--store-cover-pos': `${clampPct(c.cover_focus_x)}% ${clampPct(c.cover_focus_y)}%`
  }
}

function clampPct(v) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.min(100, Math.max(0, n)) : 50
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
