import { http } from './http.js'

// Dominio catalog (StoreApp): catálogo del dueño de la tienda.
// Todo cuelga de la tienda del usuario autenticado (scope server-side).
// Requiere suscripción activa (has_public_link): 403 sin plan.
//
// GET    /api/categories/                 Bearer -> [{id,name,feature_schema,position,products_count}]
// POST   /api/categories/                 Bearer {name, feature_schema?[]} -> {Exito,item}
// PATCH  /api/categories/<pk>/            Bearer {name?, feature_schema?[]} -> {Exito,item}
// DELETE /api/categories/<pk>/            Bearer -> {Exito}  (productos quedan sin categoría)
// Ídem   /api/brands/  (sin feature_schema)
// GET    /api/products/                   Bearer -> [{id,name,description,price,offer_price,category,category_name,brand,brand_name,is_active,features,image,created_at}]
// POST   /api/products/                   Bearer multipart {name,price,offer_price?,category?,brand?,description?,is_active?,features?{},image?} -> {Exito,item,storage,image_error?}
// PATCH  /api/products/<pk>/              Bearer idem parcial (+image_clear=true) -> {Exito,item,storage,image_error?}
// feature_schema = plantilla de atributos de la categoría (['Talle','Color']);
// features = objeto nombre/valor del producto ({Talle:'M'}) — la plantilla
// sugiere los atributos y el dueño puede sumar otros libres.
// DELETE /api/products/<pk>/              Bearer -> {Exito}  (libera la imagen y la cuota)
//                                        -> 403 si se supera max_products al crear
//
// GET    /api/discounts/                  Bearer -> [{id,name,percent,scope,category,category_name,brand,brand_name,products,products_count,starts_at,ends_at,is_active,status,created_at}]
// POST   /api/discounts/                  Bearer {name,percent,scope,category?,brand?,products?[],starts_at,ends_at?,is_active?} -> {Exito,item}
// PATCH  /api/discounts/<pk>/             Bearer idem parcial -> {Exito,item}
// DELETE /api/discounts/<pk>/             Bearer -> {Exito}
// Descuentos programados: scope = 'all'|'category'|'brand'|'products'; la
// ventana [starts_at, ends_at) se evalúa al leer el catálogo público — el
// descuento se activa y vence solo (status: scheduled|active|ended|paused).
// El precio promocionado viaja en product.discount_offer/discount_names
// (mi lista) y en offer_price efectivo (catálogo público).

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const catalogApi = {
  // Editor de imagen: quita el fondo y lo reemplaza por blanco. Devuelve un File PNG (no guarda nada).
  async removeProductBackground(file) {
    const form = new FormData()
    form.append('image', file)
    const { data } = await http.post('/products/remove-background/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'blob',
      timeout: 120000
    })
    return new File([data], 'producto.png', { type: 'image/png' })
  },
  // ----- Categorías -----
  async listCategories() {
    const { data } = await http.get('/categories/', { params: { page_size: 200 } })
    return unwrap(data)
  },
  async createCategory(payload) {
    const { data } = await http.post('/categories/', payload)
    return data
  },
  async updateCategory(pk, payload) {
    const { data } = await http.patch(`/categories/${pk}/`, payload)
    return data
  },
  async deleteCategory(pk) {
    const { data } = await http.delete(`/categories/${pk}/`)
    return data
  },

  // ----- Marcas -----
  async listBrands() {
    const { data } = await http.get('/brands/', { params: { page_size: 200 } })
    return unwrap(data)
  },
  async createBrand(payload) {
    const { data } = await http.post('/brands/', payload)
    return data
  },
  async updateBrand(pk, payload) {
    const { data } = await http.patch(`/brands/${pk}/`, payload)
    return data
  },
  async deleteBrand(pk) {
    const { data } = await http.delete(`/brands/${pk}/`)
    return data
  },

  // ----- Productos -----
  async listProducts() {
    const { data } = await http.get('/products/', { params: { page_size: 200 } })
    return unwrap(data)
  },
  async saveProduct(pk, { fields, image, imageClear }) {
    const form = new FormData()
    Object.entries(fields).forEach(([key, value]) => {
      if (value === undefined || value === null) return
      // En multipart el JSONField viaja como string (backend: binary=True).
      form.append(key, key === 'features' && typeof value === 'object' ? JSON.stringify(value) : value)
    })
    if (image) form.append('image', image)
    if (imageClear) form.append('image_clear', 'true')
    const request = pk
      ? http.patch(`/products/${pk}/`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      : http.post('/products/', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    const { data } = await request
    return data
  },
  async deleteProduct(pk) {
    const { data } = await http.delete(`/products/${pk}/`)
    return data
  },

  // ----- Descuentos programados -----
  async listDiscounts() {
    const { data } = await http.get('/discounts/', { params: { page_size: 200 } })
    return unwrap(data)
  },
  async createDiscount(payload) {
    const { data } = await http.post('/discounts/', payload)
    return data
  },
  async updateDiscount(pk, payload) {
    const { data } = await http.patch(`/discounts/${pk}/`, payload)
    return data
  },
  async deleteDiscount(pk) {
    const { data } = await http.delete(`/discounts/${pk}/`)
    return data
  }
}

// ===== Validadores espejo (config_fields del dominio catalog) =====
export function validateTaxonomyName(value) {
  const v = String(value || '').trim()
  if (!v) return 'Tenés que escribir un nombre'
  if (v.length < 2) return 'El nombre es demasiado corto'
  if (v.length > 60) return 'El nombre admite hasta 60 caracteres'
  return ''
}

export function validateProductName(value) {
  const v = String(value || '').trim()
  if (!v) return 'El producto necesita un nombre'
  if (v.length < 2) return 'El nombre es demasiado corto'
  if (v.length > 120) return 'El nombre admite hasta 120 caracteres'
  return ''
}

export function validateProductDescription(value) {
  if (value && value.length > 600) return 'La descripción admite hasta 600 caracteres'
  return ''
}

export function validateProductPrice(value) {
  if (value === '' || value === null || value === undefined) return 'El producto necesita un precio'
  const n = Number(value)
  if (Number.isNaN(n)) return 'Ingresá un precio válido'
  if (n < 0) return 'El precio no puede ser negativo'
  if (n > 9999999999) return 'El precio es demasiado grande'
  return ''
}

// Oferta opcional: si existe tiene que ser menor que el precio de lista
// (el backend fuerza la misma regla en ProductMixinValidator).
export function validateProductOffer(value, price) {
  if (value === '' || value === null || value === undefined) return ''
  const n = Number(value)
  if (Number.isNaN(n)) return 'Ingresá una oferta válida'
  if (n < 0) return 'La oferta no puede ser negativa'
  if (n > 9999999999) return 'La oferta es demasiado grande'
  const p = Number(price)
  if (!Number.isNaN(p) && n >= p) return 'La oferta tiene que ser menor que el precio'
  return ''
}

// ===== Helpers para mostrar precios/ofertas en la web pública =====
// La oferta aplica solo si existe y es menor que el precio (misma regla que
// el backend). effectivePrice es el número que ordena y se muestra grande.
export function productOffer(p) {
  const offer = Number(p?.offer_price)
  const price = Number(p?.price)
  return p?.offer_price != null && Number.isFinite(offer) && Number.isFinite(price) && offer < price ? offer : null
}

export function effectivePrice(p) {
  return productOffer(p) ?? Number(p?.price ?? 0)
}

// Descuento redondeado para el badge "-25%": 0 si no hay oferta.
export function offerPct(p) {
  const offer = productOffer(p)
  if (offer === null) return 0
  const price = Number(p.price)
  return price > 0 ? Math.max(1, Math.round((1 - offer / price) * 100)) : 0
}

// "Nuevo": publicado hace menos de PRODUCT_NEW_DAYS días (created_at ISO).
export const PRODUCT_NEW_DAYS = 7
export function isNewProduct(p) {
  const created = Date.parse(p?.created_at || '')
  return Number.isFinite(created) && Date.now() - created < PRODUCT_NEW_DAYS * 864e5
}

// ===== Características (espejo de FeatureLimits en config_fields.py) =====
export const FEATURE_LIMITS = { schemaMax: 15, nameMax: 40, entriesMax: 20, valueMax: 120 }

// Convierte el input "Talle, Color, Material" en la lista feature_schema
// (trim, sin vacíos, sin repetidos ignorando mayúsculas).
export function parseFeatureSchema(text) {
  const seen = new Set()
  const list = []
  for (const raw of String(text || '').split(',')) {
    const name = raw.trim()
    if (!name || seen.has(name.toLowerCase())) continue
    seen.add(name.toLowerCase())
    list.push(name)
  }
  return list
}

export function validateFeatureSchema(names) {
  if (names.length > FEATURE_LIMITS.schemaMax) return `La plantilla admite hasta ${FEATURE_LIMITS.schemaMax} características`
  if (names.some((n) => n.length > FEATURE_LIMITS.nameMax)) return `Cada característica admite hasta ${FEATURE_LIMITS.nameMax} caracteres`
  return ''
}

// Valida las filas {name, value} del form de producto. Devuelve el primer error.
export function validateProductFeatures(rows) {
  const filled = rows.filter((r) => r.name.trim() || r.value.trim())
  if (filled.length > FEATURE_LIMITS.entriesMax) return `El producto admite hasta ${FEATURE_LIMITS.entriesMax} características`
  const seen = new Set()
  for (const r of filled) {
    const name = r.name.trim()
    const value = r.value.trim()
    if (!name) return 'Cada característica necesita un nombre'
    if (name.length > FEATURE_LIMITS.nameMax) return `Los nombres admiten hasta ${FEATURE_LIMITS.nameMax} caracteres`
    if (!value) return `"${name}" necesita un valor (o quitá la fila)`
    if (value.length > FEATURE_LIMITS.valueMax) return `Los valores admiten hasta ${FEATURE_LIMITS.valueMax} caracteres`
    if (seen.has(name.toLowerCase())) return `La característica "${name}" está repetida`
    seen.add(name.toLowerCase())
  }
  return ''
}

// ===== Descuentos programados (espejo de DiscountFields/config_fields.py) =====
// Alcances admitidos por Discount.Scope; el objetivo se pide según el alcance.
export const DISCOUNT_SCOPES = [
  { value: 'all', label: 'Todo el catálogo' },
  { value: 'category', label: 'Una categoría' },
  { value: 'brand', label: 'Una marca' },
  { value: 'products', label: 'Productos elegidos' }
]
export const DISCOUNT_LIMITS = { percentMin: 1, percentMax: 99, productsMax: 500 }

// Estado derivado de la ventana (lo calcula el backend en status):
// scheduled = aún no llega starts_at | active = vigente | ended = pasó ends_at | paused = apagado a mano.
export const DISCOUNT_STATUS = {
  scheduled: { label: 'Programado', pill: 'warn' },
  active: { label: 'Vigente', pill: 'ok' },
  ended: { label: 'Finalizado', pill: 'muted' },
  paused: { label: 'Pausado', pill: 'muted' }
}
export const discountStatusMeta = (d) => DISCOUNT_STATUS[d?.status] || DISCOUNT_STATUS.active

export function discountScopeLabel(d) {
  const scope = DISCOUNT_SCOPES.find((s) => s.value === d?.scope)
  if (!scope) return ''
  if (d.scope === 'category' && d.category_name) return `Categoría: ${d.category_name}`
  if (d.scope === 'brand' && d.brand_name) return `Marca: ${d.brand_name}`
  if (d.scope === 'products') return `${d.products_count ?? d.products?.length ?? 0} productos`
  return scope.label
}

export function validateDiscountName(value) {
  const v = String(value || '').trim()
  if (!v) return 'El descuento necesita un nombre'
  if (v.length < 2) return 'El nombre es demasiado corto'
  if (v.length > 60) return 'El nombre admite hasta 60 caracteres'
  return ''
}

export function validateDiscountPercent(value) {
  if (value === '' || value === null || value === undefined) return 'Indicá el porcentaje de descuento'
  const n = Number(value)
  if (!Number.isInteger(n)) return 'Ingresá un porcentaje entero'
  if (n < DISCOUNT_LIMITS.percentMin) return 'El descuento mínimo es 1%'
  if (n > DISCOUNT_LIMITS.percentMax) return 'El descuento máximo es 99%'
  return ''
}

export function validateDiscountWindow(startsAt, endsAt) {
  if (!startsAt) return 'Indicá cuándo empieza el descuento'
  if (endsAt && new Date(endsAt).getTime() <= new Date(startsAt).getTime()) return 'El fin tiene que ser posterior al inicio'
  return ''
}

// datetime-local <-> ISO: el input edita en hora local y al backend viaja
// el instante en UTC (el servidor evalúa la ventana con timezone aware).
export function isoToLocalInput(iso) {
  const d = new Date(iso || '')
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
export function localInputToIso(value) {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

export function formatDiscountDate(iso) {
  const d = new Date(iso || '')
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
export function discountWindowLabel(d) {
  const start = formatDiscountDate(d?.starts_at)
  return d?.ends_at ? `${start} → ${formatDiscountDate(d.ends_at)}` : `Desde ${start}`
}

// Oferta a mostrar en "Tus productos": la menor entre la oferta manual
// (offer_price) y el descuento programado vigente (discount_offer) — el
// descuento nunca sube el precio mostrado. Null si ninguna aplica.
export function productListOffer(p) {
  const offers = [p?.offer_price, p?.discount_offer]
    .filter((v) => v !== null && v !== undefined && v !== '')
    .map(Number)
    .filter((n) => Number.isFinite(n) && n < Number(p?.price))
  return offers.length ? Math.min(...offers) : null
}
// True cuando el mejor precio lo deja un descuento programado (no la oferta manual).
export function isDiscountedProduct(p) {
  const offer = productListOffer(p)
  if (offer === null || p?.discount_offer === null || p?.discount_offer === undefined) return false
  return Number(p.discount_offer) <= offer
}
