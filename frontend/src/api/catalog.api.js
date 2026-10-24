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
