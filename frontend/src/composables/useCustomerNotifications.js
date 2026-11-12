import { ref } from 'vue'
import { customerNotificationsApi, notificationsStreamUrl } from '../api/customerNotifications.api.js'

// =============================================================================
// Notificaciones del comprador — singleton compartido por la campana del
// header y el tab "Notificaciones" de /cuenta.
//
// - Carga inicial por REST (list) y push en vivo por SSE (stream/):
//   cada conexión dura ~50s y se reconecta con ticket nuevo (el ticket
//   firmado vive ~120s — re-mintear por conexión evita el loop de 401).
// - Estado module-level: una sola suscripción SSE por pestaña aunque la
//   campana y la cuenta estén montadas a la vez.
// - Solo corre con sesión de comprador (el layout llama start/stop al
//   cambiar customerStore.isAuthenticated o el slug de la tienda).
// =============================================================================

const items = ref([])       // ≤50 más recientes (del scope `slug`)
const unread = ref(0)
const loading = ref(false)
const error = ref('')
const live = ref(false)

const MAX_ITEMS = 50
let slug = ''
let es = null
let started = false
let retryTimer = null
let retryDelay = 0

function _closeStream() {
  es?.close()
  es = null
  live.value = false
}

function _scheduleReconnect(delay) {
  clearTimeout(retryTimer)
  const wait = delay ?? retryDelay
  retryDelay = Math.min((retryDelay || 2000) * 2, 30000)
  retryTimer = setTimeout(_openStream, wait)
}

async function _openStream() {
  if (!started) return
  _closeStream()
  let ticket
  try {
    const res = await customerNotificationsApi.streamTicket(slug)
    ticket = res?.ticket
  } catch {
    // Sesión caída o red: reintenta con backoff; si el comprador salió,
    // stop() ya corrió y `started` corta el ciclo.
    if (started) _scheduleReconnect()
    return
  }
  if (!ticket || !started) return
  retryDelay = 0
  try {
    es = new EventSource(notificationsStreamUrl(ticket, slug))
  } catch {
    _scheduleReconnect()
    return
  }
  live.value = true
  es.addEventListener('notification', (e) => {
    try {
      const n = JSON.parse(e.data)
      const i = items.value.findIndex((x) => x.id === n.id)
      if (i >= 0) items.value.splice(i, 1, n)
      else items.value.unshift(n)
      if (items.value.length > MAX_ITEMS) items.value.length = MAX_ITEMS
    } catch { /* payload inválido: se ignora */ }
  })
  es.addEventListener('unread', (e) => {
    try {
      const n = JSON.parse(e.data)?.unread
      if (typeof n === 'number') unread.value = n
    } catch { /* idem */ }
  })
  // Cierre limpio del servidor (~50s): reconexión inmediata con ticket fresco.
  es.addEventListener('bye', () => { _closeStream(); _scheduleReconnect(0) })
  es.onerror = () => {
    _closeStream()
    // Re-mintear siempre: el retry nativo de EventSource reusaría el
    // ticket viejo y, vencido, respondería 401 sin volver a levantarse.
    _scheduleReconnect()
  }
}

export function useCustomerNotifications() {
  // Lista inicial + scope por tienda (slug = tienda visitada; '' = todas).
  async function load(storeSlug = slug) {
    if (storeSlug !== undefined) slug = storeSlug || ''
    loading.value = true
    error.value = ''
    try {
      const data = await customerNotificationsApi.list(slug)
      items.value = data?.notifications || []
      unread.value = typeof data?.unread === 'number' ? data.unread : unread.value
    } catch {
      error.value = 'No pudimos cargar tus notificaciones.'
    } finally {
      loading.value = false
    }
  }

  // Inicia el ciclo REST+SSE para `storeSlug` (idempotente; re-bindea si
  // cambió la tienda).
  async function start(storeSlug) {
    const next = storeSlug || ''
    if (started && next === slug) return
    slug = next
    started = true
    _closeStream()
    await load(slug)
    if (started) _openStream()
  }

  function stop() {
    started = false
    clearTimeout(retryTimer)
    retryTimer = null
    _closeStream()
    items.value = []
    unread.value = 0
    error.value = ''
  }

  async function markRead(notification) {
    if (!notification || notification.read_at) return
    notification.read_at = new Date().toISOString()
    try {
      const res = await customerNotificationsApi.markRead(notification.id)
      if (typeof res?.unread === 'number') unread.value = res.unread
    } catch { /* queda marcado local; el próximo sync corrige */ }
  }

  async function markAll() {
    const now = new Date().toISOString()
    items.value.forEach((n) => { if (!n.read_at) n.read_at = now })
    try {
      const res = await customerNotificationsApi.markAllRead(slug)
      if (typeof res?.unread === 'number') unread.value = res.unread
    } catch { /* idem */ }
  }

  return { items, unread, loading, error, live, load, start, stop, markRead, markAll }
}
