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
// GET    /api/products/                   Bearer -> [{id,name,description,price,category,category_name,brand,brand_name,is_active,features,image,created_at}]
// POST   /api/products/                   Bearer multipart {name,price,category?,brand?,description?,is_active?,features?{},image?} -> {Exito,item,storage,image_error?}
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
  // ----- Categorías -----
  async listCategories() {
    const { data } = await http.get('/categories/')
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
    const { data } = await http.get('/brands/')
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
    const { data } = await http.get('/products/')
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
