import { http } from './http.js'

// Dominio catalog (StoreApp): catálogo del dueño de la tienda.
// Todo cuelga de la tienda del usuario autenticado (scope server-side).
// Requiere suscripción activa (has_public_link): 403 sin plan.
//
// GET    /api/categories/                 Bearer -> [{id,name,position,products_count}]
// POST   /api/categories/                 Bearer {name} -> {Exito,item}
// PATCH  /api/categories/<pk>/            Bearer {name?} -> {Exito,item}
// DELETE /api/categories/<pk>/            Bearer -> {Exito}  (productos quedan sin categoría)
// Ídem   /api/brands/
// GET    /api/products/                   Bearer -> [{id,name,description,price,category,category_name,brand,brand_name,is_active,image,created_at}]
// POST   /api/products/                   Bearer multipart {name,price,category?,brand?,description?,is_active?,image?} -> {Exito,item,storage,image_error?}
// PATCH  /api/products/<pk>/              Bearer idem parcial (+image_clear=true) -> {Exito,item,storage,image_error?}
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
      if (value !== undefined && value !== null) form.append(key, value)
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
