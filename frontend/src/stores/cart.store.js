import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { cartApi } from '../api/cart.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import { useCustomerStore } from './customer.store.js'

// =============================================================================
// Carrito del COMPRADOR por tienda (e-commerce de la web pública).
// Store slug-scoped: la sesión es la del comprador (customer.store), nunca
// la DAVENT del dueño. Los precios los recalcula el server en cada lectura
// — el estado local solo refleja el último payload del API.
//
// También concentra la UI de comercio que el layout monta una sola vez:
// drawer del carrito y modal de auth del comprador (con acción pendiente
// post-login: "agregar", "ir a pagar", suscribirse…).
// =============================================================================
export const useCartStore = defineStore('storeCart', () => {
  const customer = useCustomerStore()

  const slug = ref('')
  const cart = ref(null)          // {store, items, item_count, items_total, member_discount_percent}
  const status = ref('idle')      // idle | loading | ready | error
  const busy = ref(false)         // mutación en curso (add/qty/remove)
  const notice = ref(null)        // {kind:'ok'|'err', text} — toast efímero
  let noticeTimer = 0

  // ---- UI global (la monta StorePublicLayout una vez) ----
  const drawerOpen = ref(false)
  const authOpen = ref(false)
  const authMode = ref('login')   // 'login' | 'register' | 'forgot'
  const pending = ref(null)       // {action?:fn, route?:RouteLocationRaw}

  const itemCount = computed(() => cart.value?.item_count ?? 0)
  const items = computed(() => cart.value?.items || [])
  const itemsTotal = computed(() => cart.value?.items_total || '0')
  const hasItems = computed(() => itemCount.value > 0)
  const memberDiscount = computed(() => cart.value?.member_discount_percent || 0)

  function flash(kind, text, ms = 3200) {
    notice.value = { kind, text }
    clearTimeout(noticeTimer)
    noticeTimer = setTimeout(() => { notice.value = null }, ms)
  }

  // El layout llama esto al resolver la tienda (slug computado).
  function bindStore(storeSlug) {
    const next = (storeSlug || '').toLowerCase()
    if (next === slug.value) return
    slug.value = next
    cart.value = null
    status.value = 'idle'
    drawerOpen.value = false
    if (next) refresh()
  }

  async function refresh() {
    if (!slug.value) return
    if (!customer.isAuthenticated) {
      // Sin sesión no hay carrito que leer (es del comprador, no guest).
      cart.value = null
      status.value = 'idle'
      return
    }
    status.value = 'loading'
    try {
      cart.value = await cartApi.get(slug.value)
      status.value = 'ready'
    } catch (err) {
      if (err.response?.status === 404) {
        // Tienda sin venta online o carrito inexistente: estado vacío.
        cart.value = null
        status.value = 'ready'
      } else {
        status.value = 'error'
        flash('err', extractApiError(err).nonField || 'No pudimos cargar tu carrito.')
      }
    }
  }

  async function ensureCustomer() {
    return customer.ensureSession()
  }

  // Abre el modal de auth recordando qué hacer después (acción o ruta).
  function openAuth(mode = 'login', opts = {}) {
    authMode.value = mode
    pending.value = opts.action || opts.route ? { action: opts.action || null, route: opts.route || null } : null
    authOpen.value = true
  }
  function closeAuth() { authOpen.value = false }
  // El modal llama esto tras login/register/google exitoso: devuelve la
  // continuación pendiente (la ejecuta el layout, que tiene el router).
  function takePending() {
    const p = pending.value
    pending.value = null
    return p
  }

  // Alta de línea con gate de sesión: sin comprador logueado abre el
  // modal pidiendo login y reintenta la acción al volver.
  async function addToCart(productId, qty = 1, productName = '') {
    if (!slug.value || !productId) return { ok: false }
    if (!(await ensureCustomer())) {
      openAuth('login', { action: () => addToCart(productId, qty, productName) })
      return { ok: false, needsAuth: true }
    }
    busy.value = true
    try {
      cart.value = await cartApi.addItem(slug.value, productId, qty)
      flash('ok', productName ? `Agregaste ${productName} al carrito.` : 'Agregaste el producto al carrito.')
      drawerOpen.value = true
      return { ok: true }
    } catch (err) {
      const parsed = extractApiError(err)
      flash('err', Object.values(parsed).find((v) => typeof v === 'string') || 'No pudimos agregar el producto.')
      return { ok: false }
    } finally {
      busy.value = false
    }
  }

  async function setQty(itemId, qty) {
    if (!slug.value) return
    busy.value = true
    try {
      cart.value = await cartApi.updateItem(slug.value, itemId, qty)
    } catch (err) {
      const parsed = extractApiError(err)
      flash('err', parsed.qty || parsed.nonField || 'No pudimos actualizar la cantidad.')
      await refresh().catch(() => {})
    } finally {
      busy.value = false
    }
  }

  async function removeItem(itemId) {
    if (!slug.value) return
    busy.value = true
    try {
      cart.value = await cartApi.removeItem(slug.value, itemId)
    } catch (err) {
      flash('err', extractApiError(err).nonField || 'No pudimos quitar el producto.')
    } finally {
      busy.value = false
    }
  }

  async function clear() {
    if (!slug.value) return
    busy.value = true
    try {
      cart.value = await cartApi.clear(slug.value)
    } catch (err) {
      flash('err', extractApiError(err).nonField || 'No pudimos vaciar el carrito.')
    } finally {
      busy.value = false
    }
  }

  // Sesión del comprador expirada (evento de customer.http): el carrito
  // era de esa sesión — se limpia y la UI vuelve a "invitado".
  function onSessionExpired() {
    cart.value = null
    status.value = 'idle'
    drawerOpen.value = false
    pending.value = null
  }

  // Ruta de checkout según el host: en subdominio/dominio propio es
  // '/checkout'; en la plataforma '/<slug>/checkout' (el named route
  // 'store-checkout' exigiría el param slug — el path evita el acoplamiento).
  const checkoutRoute = () => ({
    path: storeHostSlug ? '/checkout' : `/${slug.value}/checkout`
  })

  // Serializa el destino post-auth (?next= de StoreAuthView) a un path
  // interno: acepta un string o un RouteLocationRaw ({path, query}) y
  // descarta lo que no sea path interno — anti open-redirect (la vista
  // vuelve a sanitizar por las dudas).
  function authNextPath(next) {
    let p = ''
    if (typeof next === 'string') {
      p = next
    } else if (next && typeof next === 'object' && typeof next.path === 'string') {
      p = next.path
      const qs = new URLSearchParams()
      for (const [k, v] of Object.entries(next.query || {})) {
        if (v === undefined || v === null || v === '') continue
        qs.set(k, String(v))
      }
      const s = qs.toString()
      if (s) p += `?${s}`
    }
    if (!p.startsWith('/') || p.startsWith('//') || p.includes('\\')) return ''
    // La propia página de auth no puede ser destino (loop /ingresar).
    if (p.split(/[?#]/)[0].endsWith('/ingresar')) return ''
    return p
  }

  // Página de auth del comprador (StoreAuthView): '/ingresar' en host
  // propio, '/<slug>/ingresar' en la plataforma — mismo criterio que
  // checkoutRoute. `mode` = login|register|forgot; `next` = destino
  // post-auth (path o route object, viaja como ?next= sanitizado).
  function authRoute(mode = 'login', next = '') {
    const path = storeHostSlug || !slug.value ? '/ingresar' : `/${slug.value}/ingresar`
    const query = {}
    if (mode && mode !== 'login') query.mode = mode
    const nextPath = authNextPath(next)
    if (nextPath) query.next = nextPath
    return { path, query }
  }

  function openDrawer() {
    if (!customer.isAuthenticated) {
      openAuth('login', { route: checkoutRoute() })
      return
    }
    drawerOpen.value = true
    refresh()
  }

  return {
    slug, cart, status, busy, notice, drawerOpen, authOpen, authMode, pending,
    itemCount, items, itemsTotal, hasItems, memberDiscount,
    bindStore, refresh, ensureCustomer, flash,
    openAuth, closeAuth, takePending,
    addToCart, setQty, removeItem, clear, openDrawer, onSessionExpired, authRoute,
  }
})
