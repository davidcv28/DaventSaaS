import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { catalogApi } from '../api/catalog.api.js'
import { extractApiError } from '../api/http.js'

// Catálogo del cliente: categorías, marcas y productos de su tienda.
// Requiere suscripción activa (el backend devuelve 403 sin plan).
export const useCatalogStore = defineStore('catalog', () => {
  const categories = ref([])
  const brands = ref([])
  const products = ref([])
  const discounts = ref([])
  const status = ref('idle') // idle | loading | success | error
  const lastError = ref('')
  const notice = ref('')
  const fieldErrors = ref({})
  const denied = ref(false) // 403: sin suscripción activa

  const productLimitReached = computed(() => false)

  function setApiError(err) {
    const parsed = extractApiError(err)
    const { nonField, status: _s, pendingBackend, ...fields } = parsed
    lastError.value = nonField || Object.values(fields)[0] || 'Ocurrió un error'
    if (parsed.status === 403) denied.value = true
    fieldErrors.value = fields
    return parsed
  }

  async function loadAll() {
    status.value = 'loading'
    lastError.value = ''
    denied.value = false
    try {
      const [cats, brs, prods, discs] = await Promise.all([
        catalogApi.listCategories(),
        catalogApi.listBrands(),
        catalogApi.listProducts(),
        catalogApi.listDiscounts()
      ])
      categories.value = cats
      brands.value = brs
      products.value = prods
      discounts.value = discs
      status.value = 'success'
    } catch (e) {
      status.value = 'error'
      setApiError(e)
    }
  }

  async function run(action, fallback) {
    lastError.value = ''
    fieldErrors.value = {}
    notice.value = ''
    try {
      const data = await action()
      notice.value = data?.Exito || fallback
      return { ok: true, data }
    } catch (e) {
      setApiError(e)
      return { ok: false, data: null }
    }
  }

  // ----- Categorías -----
  async function saveCategory(pk, payload) {
    const res = await run(
      () => pk ? catalogApi.updateCategory(pk, payload) : catalogApi.createCategory(payload),
      'La categoría se guardó correctamente.'
    )
    if (res.ok) categories.value = await catalogApi.listCategories()
    return res.ok
  }
  async function removeCategory(pk) {
    const res = await run(() => catalogApi.deleteCategory(pk), 'La categoría se eliminó.')
    if (res.ok) {
      categories.value = categories.value.filter((c) => c.id !== pk)
      products.value = products.value.map((p) => (p.category === pk ? { ...p, category: null, category_name: null } : p))
    }
    return res.ok
  }

  // ----- Marcas -----
  async function saveBrand(pk, payload) {
    const res = await run(
      () => pk ? catalogApi.updateBrand(pk, payload) : catalogApi.createBrand(payload),
      'La marca se guardó correctamente.'
    )
    if (res.ok) brands.value = await catalogApi.listBrands()
    return res.ok
  }
  async function removeBrand(pk) {
    const res = await run(() => catalogApi.deleteBrand(pk), 'La marca se eliminó.')
    if (res.ok) {
      brands.value = brands.value.filter((b) => b.id !== pk)
      products.value = products.value.map((p) => (p.brand === pk ? { ...p, brand: null, brand_name: null } : p))
    }
    return res.ok
  }

  // ----- Productos -----
  // Devuelve {ok, imageError}: la imagen puede fallar por cuota aunque el producto se guarde.
  async function saveProduct(pk, payload) {
    const res = await run(() => catalogApi.saveProduct(pk, payload), 'El producto se guardó correctamente.')
    if (res.ok) {
      products.value = await catalogApi.listProducts()
      return { ok: true, imageError: res.data?.image_error || '', storage: res.data?.storage || null }
    }
    return { ok: false, imageError: '', storage: null }
  }
  async function removeProduct(pk) {
    const res = await run(() => catalogApi.deleteProduct(pk), 'El producto se eliminó.')
    if (res.ok) {
      products.value = products.value.filter((p) => p.id !== pk)
      return { ok: true, storage: res.data?.storage || null }
    }
    return { ok: false, storage: null }
  }

  // ----- Descuentos programados -----
  // Un alta/cambio puede alterar discount_offer de los productos: se recargan
  // los dos listados para que la vitrina del panel refleje el precio efectivo.
  async function saveDiscount(pk, payload) {
    const res = await run(
      () => pk ? catalogApi.updateDiscount(pk, payload) : catalogApi.createDiscount(payload),
      'El descuento se guardó correctamente.'
    )
    if (res.ok) {
      const [discs, prods] = await Promise.all([catalogApi.listDiscounts(), catalogApi.listProducts()])
      discounts.value = discs
      products.value = prods
    }
    return res.ok
  }
  async function toggleDiscount(d) {
    const res = await run(
      () => catalogApi.updateDiscount(d.id, { is_active: !d.is_active }),
      d.is_active ? 'El descuento se pausó.' : 'El descuento se reactivó.'
    )
    if (res.ok) {
      const [discs, prods] = await Promise.all([catalogApi.listDiscounts(), catalogApi.listProducts()])
      discounts.value = discs
      products.value = prods
    }
    return res.ok
  }
  async function removeDiscount(pk) {
    const res = await run(() => catalogApi.deleteDiscount(pk), 'El descuento se eliminó.')
    if (res.ok) {
      discounts.value = discounts.value.filter((d) => d.id !== pk)
      products.value = await catalogApi.listProducts()
    }
    return res.ok
  }

  function reset() {
    categories.value = []
    brands.value = []
    products.value = []
    discounts.value = []
    status.value = 'idle'
    lastError.value = ''
    notice.value = ''
    fieldErrors.value = {}
    denied.value = false
  }

  return {
    categories, brands, products, discounts, status, lastError, notice, fieldErrors, denied,
    productLimitReached,
    loadAll, saveCategory, removeCategory, saveBrand, removeBrand,
    saveProduct, removeProduct, saveDiscount, toggleDiscount, removeDiscount, reset
  }
})
