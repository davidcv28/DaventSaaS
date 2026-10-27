<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useBillingStore } from '../stores/billing.store.js'
import { usePaymentsStore } from '../stores/payments.store.js'
import { useAdminStore } from '../stores/admin.store.js'
import { formatARS } from '../api/billing.api.js'
import { paymentStatusMeta, formatDateTime, MONTH_NAMES } from '../api/payments.api.js'
import { fetchChat, fetchChatMessages, sendChatMessage, chatHeartbeat } from '../api/chat.api.js'
import { extractApiError } from '../api/http.js'
import DashLayout from '../components/DashLayout.vue'
import ChatDock from '../components/ChatDock.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const auth = useAuthStore()
const billing = useBillingStore()
const payments = usePaymentsStore()
const admin = useAdminStore()

const section = ref('overview')
const approvingId = ref(null)
const payQuery = ref('')
const payFilter = ref('all')
const planForm = reactive({ id: null, name: '', price: '' })
const planTouched = ref(false)
// Asignación manual de plan: select por fila de usuario (userId -> planId).
const assignSel = reactive({})
const assigningId = ref(null)
// Moderación de webs: fila con el formulario de motivo abierto (storeId).
const BLOCK_REASONS = [
  'Derechos de autor',
  'Contenido ilegal',
  'Fraude o engaño',
  'Incumplimiento de los términos',
  'Otro motivo'
]
const blockingId = ref(null)
const blockReason = ref(BLOCK_REASONS[0])
const blockBusyId = ref(null)
// Búsqueda local del listado de webs: texto libre + filtro por estado.
const storesQuery = ref('')
const storesStatusFilter = ref('all')
// Cupones: formulario de alta/edición y fila expandida con el detalle de canjes.
const couponForm = reactive({ id: null, code: '', plan: '', days: 7, max_uses: '', expires_at: '' })
const couponTouched = ref(false)
const expandedCoupon = ref(null)
const couponBusyId = ref(null)

const initial = computed(() => (auth.user?.username || auth.user?.email || 'A').slice(0, 1).toUpperCase())
const displayName = computed(() => auth.user?.username || auth.user?.email || 'Administrador')
const summary = computed(() => admin.summary || {})

const navItems = [
  { heading: 'Sistema' },
  { id: 'overview', label: 'Resumen', icon: 'dashboard' },
  { id: 'payments', label: 'Movimientos', icon: 'receipt' },
  { id: 'suscriptions', label: 'Suscripciones', icon: 'credit-card' },
  { id: 'webs', label: 'Webs', icon: 'monitor' },
  { id: 'plans', label: 'Planes', icon: 'package' },
  { id: 'coupons', label: 'Cupones', icon: 'gift' },
  { id: 'users', label: 'Usuarios', icon: 'users' },
  { id: 'chat', label: 'Chat soporte', icon: 'message-circle' },
  { heading: 'Cuenta' },
  { id: 'flyer', label: 'Folleto promo', icon: 'printer' }
]

const kpis = computed(() => {
  const s = summary.value
  const money = (v) => (admin.summary ? formatARS(v) : '—')
  return [
    { icon: 'wallet', label: 'Ingresos totales', value: money(s.total_revenue) },
    { icon: 'trending-up', label: 'Ingresos del mes', value: money(s.revenue_month) },
    { icon: 'clock', label: 'Cobrado hoy', value: money(s.revenue_today) },
    { icon: 'users', label: 'Clientes', value: s.customers ?? '—' },
    { icon: 'credit-card', label: 'Suscripciones activas', value: s.suscriptions_active ?? '—' },
    { icon: 'receipt', label: 'Pagos pendientes', value: s.payments_pending ?? '—' }
  ]
})

// Últimos 14 días de ingresos aprobados (la API los trae desc).
const revenueDays = computed(() => (summary.value.revenue_by_day || []).slice(0, 14).reverse())
const revenueMax = computed(() => Math.max(...revenueDays.value.map(r => Number(r.total_amount) || 0), 0))

const planStats = computed(() => {
  const map = {}
  for (const row of summary.value.by_plan || []) map[row.plan] = row
  return map
})

const filteredPayments = computed(() => {
  const q = payQuery.value.trim().toLowerCase()
  return admin.payments.filter(p => {
    if (payFilter.value !== 'all' && p.status !== payFilter.value) return false
    if (!q) return true
    return [p.business_name, p.user_name, p.plan_name, p.external_reference, String(p.id)]
      .filter(Boolean)
      .some(v => String(v).toLowerCase().includes(q))
  })
})

const recentPayments = computed(() => admin.payments.slice(0, 5))
const staffCount = computed(() => admin.users.filter(u => u.is_staff).length)
// Suscripción vigente por usuario (auth user id): muestra el plan actual
// en la tabla de usuarios junto al control de asignación.
const suscriptionByUser = computed(() => {
  const map = {}
  for (const s of admin.suscriptions) map[s.auth_user_id] = s
  return map
})

const planError = computed(() => {
  if (!planTouched.value) return ''
  if (!planForm.name.trim()) return 'Ingresá el nombre del plan'
  return ''
})
const priceError = computed(() => {
  if (!planTouched.value) return ''
  const n = Number(planForm.price)
  if (planForm.price === '' || Number.isNaN(n) || n <= 0) return 'Ingresá un precio mayor a 0'
  return ''
})

// --- Chat de soporte: bandeja de clientes + conversación (polling + heartbeat) ---
const chatThreads = ref([])
const chatOnline = ref(new Set())
const chatActive = ref(null)
const chatMsgs = ref([])
const chatInput = ref('')
const chatBusy = ref(false)
const chatErr = ref('')
const chatLastId = ref(0)
const chatUnread = ref(0)
const chatBoxEl = ref(null)
const chatInputEl = ref(null)
const chatMin = ref(false)
const chatQuery = ref('')
// Bandeja que abre la burbuja flotante (ataljo a la sección Chat).
const chatDockOpen = ref(false)
const chatDockContent = computed(() => (chatActive.value ? 'win' : chatDockOpen.value ? 'panel' : null))
// Adjuntos en cola: [{file, url}] — objectURL local para la vista previa;
// el archivo viaja al bucket/disco del backend, nunca a la DB.
const chatFiles = ref([])
const chatFileInput = ref(null)
const CHAT_FILES_MAX = 4

const filteredChatThreads = computed(() => {
  const norm = (v) => String(v || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const q = norm(chatQuery.value.trim())
  if (!q) return chatThreads.value
  return chatThreads.value.filter((t) =>
    [t.customer?.name, t.customer?.email, t.last_message?.body].some((v) => norm(v).includes(q))
  )
})

function focusChatInput() {
  nextTick(() => chatInputEl.value?.focus({ preventScroll: true }))
}

function pickChatImages() {
  chatFileInput.value?.click()
}

function onChatFiles(e) {
  const picked = [...(e.target.files || [])].filter((f) => f.type.startsWith('image/'))
  const room = Math.max(0, CHAT_FILES_MAX - chatFiles.value.length)
  picked.slice(0, room).forEach((f) => {
    chatFiles.value.push({ file: f, url: URL.createObjectURL(f) })
  })
  e.target.value = ''
}

function removeChatFile(i) {
  const f = chatFiles.value[i]
  if (f) URL.revokeObjectURL(f.url)
  chatFiles.value.splice(i, 1)
}

function resetChatFiles() {
  chatFiles.value.forEach((f) => URL.revokeObjectURL(f.url))
  chatFiles.value = []
}

function resizeChatInput() {
  const el = chatInputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 132) + 'px'
}

function onComposerEnter(e) {
  if (e.shiftKey) return
  e.preventDefault()
  sendChat()
}
let chatThreadsTimer = null
let chatMsgsTimer = null
let chatBeatTimer = null

const chatOnlineCount = computed(() => chatOnline.value.size)

function scrollChatBox() {
  const el = chatBoxEl.value
  if (el) el.scrollTop = el.scrollHeight
}

function chatInitials(name) {
  return (name || '?').trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
}

function chatDayLabel(iso) {
  const d = new Date(iso)
  const today = new Date()
  const y = new Date(); y.setDate(today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Hoy'
  if (d.toDateString() === y.toDateString()) return 'Ayer'
  return d.toLocaleDateString('es-AR', { day: 'numeric', month: 'long' })
}

function chatRows(list) {
  const rows = []
  const same = (a, b) => a && b && a.mine === b.mine && a.sender_name === b.sender_name &&
    new Date(a.created_at).toDateString() === new Date(b.created_at).toDateString() &&
    Math.abs(new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) < 300000
  list.forEach((m, i) => {
    const p = list[i - 1]
    const n = list[i + 1]
    if (!p || new Date(p.created_at).toDateString() !== new Date(m.created_at).toDateString()) rows.push({ day: chatDayLabel(m.created_at), key: `d-${m.id}` })
    rows.push({ m, first: !same(p, m), last: !same(m, n), key: m.id })
  })
  return rows
}

function fmtChatTime(iso) {
  const d = new Date(iso)
  const sameDay = d.toDateString() === new Date().toDateString()
  return sameDay
    ? d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}

let chatThreadsLoading = false

async function loadChatThreads() {
  // Oculto no se pollea (al volver hay tick inmediato) y nunca se enciman
  // dos requests si una tardó más que el intervalo. La bandeja solo se
  // fetchea cuando hay UI que la muestre: sección Chat, el panel de la
  // burbuja o una ventana abierta (refresca su unread/last_message).
  if (document.hidden || chatThreadsLoading) return
  if (section.value !== 'chat' && !chatDockOpen.value && !chatActive.value) return
  chatThreadsLoading = true
  try {
    const data = await fetchChat()
    chatThreads.value = data.threads || []
    chatOnline.value = new Set(data.online || [])
    chatErr.value = ''
    // Si el hilo activo sigue existiendo, refresco sus contadores
    if (chatActive.value) {
      const fresh = chatThreads.value.find((t) => t.id === chatActive.value.id)
      if (fresh) chatActive.value = fresh
    }
  } catch (e) { chatErr.value = extractApiError(e).nonField }
  finally { chatThreadsLoading = false }
}

async function openChatThread(thread) {
  chatActive.value = thread
  chatMin.value = false
  chatDockOpen.value = false
  chatMsgs.value = []
  chatLastId.value = 0
  chatErr.value = ''
  resetChatFiles()
  focusChatInput() // la ventana abre con el cursor listo para responder
  try {
    const data = await fetchChatMessages({ thread: thread.id })
    const msgs = data.messages || []
    chatMsgs.value = msgs
    chatLastId.value = msgs.length ? msgs[msgs.length - 1].id : 0
    await nextTick()
    scrollChatBox()
    loadChatThreads() // el thread ya quedó leído: refresca el badge
  } catch (e) { chatErr.value = extractApiError(e).nonField }
}

function onThreadClick(t) {
  // Click sobre la conversación ya abierta: la expande si estaba
  // minimizada o simplemente devuelve el foco al composer (Messenger).
  if (chatActive.value?.id === t.id) {
    if (chatMin.value) toggleChatMin()
    else focusChatInput()
    return
  }
  openChatThread(t)
}

function toggleChatMin() {
  chatMin.value = !chatMin.value
  if (!chatMin.value) {
    // Al expandir se retoma el polling (pausado mínimo): lo que llegó en
    // el medio todavía no quedó marcado como leído en el servidor.
    pollChatMsgs()
    nextTick(() => {
      scrollChatBox()
      chatInputEl.value?.focus({ preventScroll: true })
    })
  }
}

function closeChatWindow() {
  chatActive.value = null
  chatMin.value = false
  resetChatFiles()
}

function onChatKey(e) {
  if (e.key !== 'Escape') return
  if (chatActive.value) closeChatWindow()
  if (chatDockOpen.value) chatDockOpen.value = false
}

// Alterna lo que tenga abierto la burbuja: panel/ventana visible se cierra;
// si no, abre la bandeja de conversaciones.
function onDockToggle() {
  if (chatDockOpen.value) { chatDockOpen.value = false; return }
  if (chatActive.value) { closeChatWindow(); return }
  chatDockOpen.value = true
  loadChatThreads()
  beatChat()
}

let chatMsgsPolling = false

async function pollChatMsgs() {
  // Minimizada no se fetchea: el GET marca los mensajes como leídos y el
  // staff todavía no los vio — el badge de la ventana/inbox sigue vivo.
  if (!chatActive.value || chatMin.value || document.hidden || chatMsgsPolling) return
  chatMsgsPolling = true
  try {
    const data = await fetchChatMessages({ thread: chatActive.value.id, after: chatLastId.value })
    // Dedupe por id: un send optimista o un poll encimado ya pudo traer el
    // mensaje — sin el filtro se vería dos veces hasta el próximo refetch.
    const fresh = (data.messages || []).filter((m) => !chatMsgs.value.some((x) => x.id === m.id))
    if (fresh.length) {
      chatMsgs.value = [...chatMsgs.value, ...fresh]
      chatLastId.value = fresh[fresh.length - 1].id
      await nextTick()
      scrollChatBox()
    }
  } catch { /* reintenta el próximo tick */ }
  finally { chatMsgsPolling = false }
}

async function beatChat() {
  try {
    const data = await chatHeartbeat()
    chatUnread.value = data.unread || 0
    chatOnline.value = new Set(data.online || [])
  } catch { /* silencioso */ }
}

async function sendChat() {
  const body = chatInput.value.trim()
  const files = chatFiles.value
  if ((!body && !files.length) || chatBusy.value || !chatActive.value) return
  chatBusy.value = true
  chatErr.value = ''
  chatFiles.value = [] // los objectURL mueren con la fila de previews
  // Optimista: texto + una burbuja por imagen; las pendientes se reemplazan
  // por los reales; si un POST falla se quitan las no confirmadas.
  const mkTmp = (extra = {}) => ({
    id: `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    mine: true, sender_name: 'Vos', pending: true, created_at: new Date().toISOString(), ...extra
  })
  const tmps = []
  if (body) tmps.push(mkTmp({ body }))
  files.forEach((f) => tmps.push(mkTmp({ body: '', image_url: f.url })))
  chatMsgs.value = [...chatMsgs.value, ...tmps]
  chatInput.value = ''
  await nextTick()
  scrollChatBox()
  resizeChatInput()
  try {
    let i = 0
    if (body) {
      const { message } = await sendChatMessage(body, chatActive.value.id)
      chatMsgs.value = chatMsgs.value.filter((m) => m.id !== tmps[i].id && m.id !== message.id).concat(message)
      chatLastId.value = Math.max(chatLastId.value, message.id)
      i++
    }
    for (const f of files) {
      const { message } = await sendChatMessage('', chatActive.value.id, f.file)
      chatMsgs.value = chatMsgs.value.filter((m) => m.id !== tmps[i].id && m.id !== message.id).concat(message)
      chatLastId.value = Math.max(chatLastId.value, message.id)
      i++
    }
    files.forEach((f) => URL.revokeObjectURL(f.url)) // enviados: previews fuera
    pollChatMsgs() // recoge al instante mensajes del cliente llegados en el medio
    loadChatThreads() // refresca last_message/unread de la bandeja
  } catch (e) {
    const stuck = new Set(tmps.slice(i).map((t) => t.id))
    chatMsgs.value = chatMsgs.value.filter((m) => !stuck.has(m.id))
    chatFiles.value = files // los adjuntos vuelven a la cola para reintentar
    chatInput.value = body
    nextTick(resizeChatInput)
    chatErr.value = extractApiError(e).nonField
  } finally {
    chatBusy.value = false
    focusChatInput()
  }
}

// ~2.5s mensajes / ~6s bandeja: el staff ve los mensajes del cliente con
// ~1.2s de latencia media. El throttle 'chat' (5000/h) cubre este ritmo.
const CHAT_MSGS_MS = 2500
const CHAT_THREADS_MS = 6000

function startChat() {
  stopChat()
  loadChatThreads()
  beatChat()
  chatThreadsTimer = setInterval(loadChatThreads, CHAT_THREADS_MS)
  chatMsgsTimer = setInterval(pollChatMsgs, CHAT_MSGS_MS)
  chatBeatTimer = setInterval(beatChat, 45000)
}

function stopChat() {
  clearInterval(chatThreadsTimer)
  clearInterval(chatMsgsTimer)
  clearInterval(chatBeatTimer)
  chatThreadsTimer = null
  chatMsgsTimer = null
  chatBeatTimer = null
}

// Presencia + bandeja corren con el panel montado: los clientes figuran
// "en línea" y el badge marca no-leídos sin abrir la sección Chat. Las
// lecturas pesadas (bandeja, hilo) siguen guardadas por su visibilidad.
watch(section, (s) => { if (s === 'chat') { loadChatThreads(); beatChat() } })

// Al volver al tab: tick inmediato (los intervals no corrían con la pestaña
// oculta) — el staff ve los mensajes nuevos sin esperar al próximo ciclo.
function onChatVisible() {
  if (document.visibilityState === 'visible') {
    pollChatMsgs()
    loadChatThreads()
    beatChat()
  }
}
onMounted(() => {
  startChat()
  document.addEventListener('visibilitychange', onChatVisible)
  document.addEventListener('keydown', onChatKey)
})

onUnmounted(() => {
  stopChat()
  resetChatFiles()
  document.removeEventListener('visibilitychange', onChatVisible)
  document.removeEventListener('keydown', onChatKey)
})

onMounted(async () => {
  await auth.fetchMe()
  await admin.loadAll()
})

function onNavigate(id) {
  // Folleto promo de DAVENT: se abre en pestaña aparte (vista imprimible).
  if (id === 'flyer') {
    window.open(router.resolve({ name: 'davent-flyer' }).href, '_blank', 'noopener')
    return
  }
  section.value = id
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function dayLabel(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' })
}

function barHeight(total) {
  if (!revenueMax.value) return '3%'
  return `${Math.max(3, Math.round((Number(total) / revenueMax.value) * 100))}%`
}

function suscriptionStatusMeta(status) {
  if (status === 'Suscripción activa') return { kind: 'ok', label: status }
  if (status === 'Pendiente de pago') return { kind: 'warn', label: status }
  return { kind: 'muted', label: status || '—' }
}

// Nombre del cliente en el listado de suscripciones: nombre y apellido del
// perfil; si todavía no cargó los datos fiscales se cae a la razón social.
function clientName(s) {
  return [s.first_name, s.last_name].filter(Boolean).join(' ') || s.business_name || '—'
}

// Estado público de la web: el bloqueo staff pisa cualquier otro estado;
// publicada + suscripción vigente => en vivo.
function webStatus(s) {
  if (s.is_blocked) return { key: 'blocked', kind: 'danger', label: 'Bloqueada' }
  if (!s.is_published) return { key: 'draft', kind: 'muted', label: 'Borrador' }
  if (!s.has_access) return { key: 'no_access', kind: 'warn', label: 'Sin acceso' }
  return { key: 'live', kind: 'ok', label: 'En vivo' }
}

// Filtra por nombre de la web, slug, dueño, email o plan (sin importar
// acentos), y por el estado público que muestra webStatus().
const filteredStores = computed(() => {
  const norm = (v) => String(v).toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const q = norm(storesQuery.value.trim())
  return admin.stores.filter((s) => {
    if (storesStatusFilter.value !== 'all' && webStatus(s).key !== storesStatusFilter.value) return false
    if (!q) return true
    return [s.customization?.display_name, s.business_name, s.slug, s.owner_name, s.owner_email, s.plan_name]
      .filter(Boolean)
      .some((v) => norm(v).includes(q))
  })
})

function startBlock(s) {
  blockingId.value = s.id
  blockReason.value = BLOCK_REASONS[0]
}

async function confirmBlock(s) {
  blockBusyId.value = s.id
  const ok = await admin.setStoreBlocked(s, blockReason.value)
  if (ok) blockingId.value = null
  blockBusyId.value = null
}

async function unblockStore(s) {
  blockBusyId.value = s.id
  await admin.setStoreBlocked(s)
  blockBusyId.value = null
}

async function assignTo(u) {
  const planId = assignSel[u.id]
  if (!planId) return
  assigningId.value = u.id
  const ok = await admin.assignPlan(u.id, planId)
  if (ok) delete assignSel[u.id]
  assigningId.value = null
}

async function approvePayment(p) {
  approvingId.value = p.id
  await admin.approve(p)
  approvingId.value = null
}

function editPlan(p) {
  planForm.id = p.id
  planForm.name = p.name
  planForm.price = String(p.price)
  planTouched.value = false
}

function resetPlanForm() {
  planForm.id = null
  planForm.name = ''
  planForm.price = ''
  planTouched.value = false
}

async function submitPlan() {
  planTouched.value = true
  if (planError.value || priceError.value) return
  const ok = await admin.savePlan({ id: planForm.id, name: planForm.name, price: planForm.price })
  if (ok) resetPlanForm()
}

// ============ CUPONES ============
const couponCodeError = computed(() => {
  if (!couponTouched.value) return ''
  if (couponForm.code.trim().length < 3) return 'Ingresá un código de al menos 3 caracteres'
  return ''
})
const couponPlanError = computed(() => {
  if (!couponTouched.value) return ''
  if (!couponForm.plan) return 'Elegí el plan que otorga el cupón'
  return ''
})
const couponDaysError = computed(() => {
  if (!couponTouched.value) return ''
  const n = Number(couponForm.days)
  if (!Number.isInteger(n) || n < 1) return 'Ingresá los días de acceso (mínimo 1)'
  return ''
})

// Estado efectivo del cupón para la tabla: vencido/agotado pisan "activo".
function couponStatus(c) {
  if (c.expires_at && new Date(c.expires_at).getTime() <= Date.now()) return { kind: 'warn', label: 'Vencido' }
  if (c.max_uses !== null && c.uses >= c.max_uses) return { kind: 'warn', label: 'Agotado' }
  return c.is_active ? { kind: 'ok', label: 'Activo' } : { kind: 'muted', label: 'Inactivo' }
}

function couponUsesLabel(c) {
  return c.max_uses === null ? `${c.uses} de ∞` : `${c.uses} de ${c.max_uses}`
}

function editCoupon(c) {
  couponForm.id = c.id
  couponForm.code = c.code
  couponForm.plan = c.plan
  couponForm.days = c.days
  couponForm.max_uses = c.max_uses ?? ''
  couponForm.expires_at = c.expires_at ? c.expires_at.slice(0, 10) : ''
  couponTouched.value = false
}

function resetCouponForm() {
  couponForm.id = null
  couponForm.code = ''
  couponForm.plan = ''
  couponForm.days = 7
  couponForm.max_uses = ''
  couponForm.expires_at = ''
  couponTouched.value = false
}

async function submitCoupon() {
  couponTouched.value = true
  if (couponCodeError.value || couponPlanError.value || couponDaysError.value) return
  const ok = await admin.saveCoupon({
    id: couponForm.id,
    code: couponForm.code,
    plan: couponForm.plan,
    days: couponForm.days,
    max_uses: couponForm.max_uses,
    expires_at: couponForm.expires_at
  })
  if (ok) resetCouponForm()
}

async function toggleCoupon(c) {
  couponBusyId.value = c.id
  await admin.toggleCoupon(c)
  couponBusyId.value = null
}

function toggleCouponDetail(c) {
  expandedCoupon.value = expandedCoupon.value === c.id ? null : c.id
}

async function logout() {
  billing.reset()
  payments.reset()
  admin.reset()
  // Esperar al logout: si el push corre con el request en vuelo, la cookie
  // de refresh sigue viva y ensureSession puede revivir la sesión.
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <DashLayout
    :active="section"
    :items="navItems"
    plan-name="Administración"
    :user-name="displayName"
    :initial="initial"
    force-theme="dark"
    @navigate="onNavigate"
    @logout="logout"
  >
    <template #topbar-actions>
      <!-- Campana de mensajería: punto verde = clientes en línea, badge =
           mensajes sin leer. Abre la bandeja rápida de conversaciones. -->
      <button
        type="button"
        class="top-bell"
        :aria-label="chatDockOpen ? 'Cerrar mensajes' : 'Abrir mensajes'"
        title="Mensajes"
        :aria-expanded="chatDockOpen || Boolean(chatActive)"
        @click="onDockToggle"
      >
        <AppIcon name="bell" :size="19" />
        <span class="bell-status" :class="{ on: chatOnlineCount > 0 }" aria-hidden="true"></span>
        <span v-if="chatUnread" class="chat-badge bell-badge">{{ chatUnread > 99 ? '99+' : chatUnread }}</span>
      </button>
    </template>

    <!-- ================= RESUMEN ================= -->
    <div v-show="section === 'overview'">
      <div class="page-head">
        <div>
          <h1>Administración</h1>
          <p>Estado general del sistema: ingresos, clientes y actividad de cobros.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadAll()"><AppIcon name="refresh" :size="16" /> Actualizar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.summaryStatus === 'error'" kind="error" :message="admin.lastError" />

      <div v-if="admin.pendingPayments.length" class="cta-banner">
        <div><strong>{{ admin.pendingPayments.length }} pago(s) pendiente(s) de aprobación.</strong><br />Revisalos en Movimientos para acreditar las suscripciones correspondientes.</div>
        <button class="btn light btn-auto" @click="section = 'payments'">Revisar movimientos</button>
      </div>

      <div v-if="admin.summaryStatus === 'loading'" class="card"><p>Cargando el resumen del sistema…</p></div>
      <div v-else-if="admin.summaryStatus === 'forbidden'" class="card"><p>Esta sección requiere una cuenta de administrador.</p></div>
      <template v-else>
        <div class="stats">
          <div v-for="k in kpis" :key="k.label" class="stat">
            <span class="stat-icon"><AppIcon :name="k.icon" :size="20" /></span>
            <div><strong>{{ k.value }}</strong><small>{{ k.label }}</small></div>
          </div>
        </div>

        <div class="grid-2">
          <div class="card">
            <h3><AppIcon name="trending-up" :size="18" /> Ingresos por día</h3>
            <div v-if="revenueDays.length" class="bars" role="img" aria-label="Ingresos aprobados de los últimos días">
              <div v-for="r in revenueDays" :key="r.date" class="bar-col">
                <span class="bar" :style="{ height: barHeight(r.total_amount) }" :title="`${dayLabel(r.date)} · ${formatARS(r.total_amount)} · ${r.payments_count} pago(s)`"></span>
                <span class="bar-label">{{ dayLabel(r.date) }}</span>
              </div>
            </div>
            <p v-else>Todavía no hay ingresos aprobados registrados.</p>
          </div>
          <div class="card">
            <h3><AppIcon name="dashboard" :size="18" /> Ingresos por mes</h3>
            <div v-if="summary.revenue_by_month?.length" class="kv">
              <div v-for="r in summary.revenue_by_month" :key="`${r.year}-${r.month}`">
                <span>{{ MONTH_NAMES[r.month] }} {{ r.year }}</span>
                <strong>{{ formatARS(r.total_amount) }} · {{ r.payments_count }} pago(s)</strong>
              </div>
            </div>
            <p v-else>Sin datos todavía.</p>
          </div>
        </div>

        <div class="card section-gap">
          <h3><AppIcon name="package" :size="18" /> Distribución por plan</h3>
          <div v-if="summary.by_plan?.length" class="table-wrap">
            <table class="pay-table">
              <thead>
                <tr>
                  <th>Plan</th>
                  <th>Suscripciones</th>
                  <th>Pagos aprobados</th>
                  <th>Ingresos</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in summary.by_plan" :key="row.plan">
                  <td data-label="Plan"><strong>{{ row.plan || '—' }}</strong></td>
                  <td data-label="Suscripciones">{{ row.suscriptions }}</td>
                  <td data-label="Pagos aprobados">{{ row.payments }}</td>
                  <td class="amount" data-label="Ingresos">{{ formatARS(row.revenue) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else>Sin datos todavía.</p>
        </div>

        <div class="card section-gap">
          <h3><AppIcon name="receipt" :size="18" /> Movimientos recientes</h3>
          <div v-if="recentPayments.length" class="table-wrap">
            <table class="pay-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th>Plan</th>
                  <th>Monto</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in recentPayments" :key="p.id">
                  <td data-label="Fecha">{{ formatDateTime(p.paid_at || p.created_at) }}</td>
                  <td data-label="Cliente">{{ p.business_name || p.user_name || '—' }}</td>
                  <td data-label="Plan">{{ p.plan_name || '—' }}</td>
                  <td class="amount" data-label="Monto">{{ formatARS(p.amount) }}</td>
                  <td data-label="Estado"><span class="pill" :class="paymentStatusMeta(p.status).kind">{{ p.status_display || paymentStatusMeta(p.status).label }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else>Sin movimientos registrados todavía.</p>
          <div v-if="admin.payments.length > 5" class="form-top">
            <button class="btn ghost btn-auto" @click="section = 'payments'">Ver todos los movimientos</button>
          </div>
        </div>
      </template>
    </div>

    <!-- ================= MOVIMIENTOS ================= -->
    <div v-show="section === 'payments'">
      <div class="page-head">
        <div>
          <h1>Movimientos</h1>
          <p>Registro de todos los cobros del sistema. Podés aprobar manualmente los pagos pendientes.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadPayments()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.paymentsStatus === 'error'" kind="error" :message="admin.lastError" />

      <div class="toolbar">
        <input v-model="payQuery" class="input" type="search" placeholder="Buscar por cliente, plan o referencia" aria-label="Buscar movimientos" />
        <select v-model="payFilter" class="select" aria-label="Filtrar por estado">
          <option value="all">Todos los estados</option>
          <option value="pending">Pendientes</option>
          <option value="approved">Aprobados</option>
          <option value="rejected">Rechazados</option>
          <option value="refunded">Reembolsados</option>
        </select>
      </div>

      <div v-if="admin.paymentsStatus === 'loading'" class="card"><p>Cargando movimientos…</p></div>
      <template v-else-if="filteredPayments.length">
        <p class="table-count">{{ filteredPayments.length }} movimiento(s)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Plan</th>
                <th>Monto</th>
                <th>Estado</th>
                <th>Referencia</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in filteredPayments" :key="p.id">
                <td data-label="Fecha">{{ formatDateTime(p.paid_at || p.created_at) }}</td>
                <td data-label="Cliente"><strong>{{ p.business_name || '—' }}</strong><br /><small class="muted">{{ p.user_name }}</small></td>
                <td data-label="Plan">{{ p.plan_name || '—' }}</td>
                <td class="amount" data-label="Monto">{{ formatARS(p.amount) }}</td>
                <td data-label="Estado"><span class="pill" :class="paymentStatusMeta(p.status).kind">{{ p.status_display || paymentStatusMeta(p.status).label }}</span></td>
                <td data-label="Referencia"><span class="mono">{{ p.external_reference || '—' }}</span></td>
                <td data-label="Acción">
                  <button
                    v-if="p.status === 'pending'"
                    class="btn sm"
                    :disabled="approvingId === p.id"
                    @click="approvePayment(p)"
                  >
                    <span v-if="approvingId === p.id" class="spinner"></span>
                    <AppIcon v-else name="check" :size="14" />
                    Aprobar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="receipt" :size="28" /></span>
        <h3>Sin movimientos para mostrar</h3>
        <p>{{ admin.payments.length ? 'Ningún pago coincide con los filtros aplicados.' : 'Todavía no hay pagos registrados en el sistema.' }}</p>
      </div>
    </div>

    <!-- ================= SUSCRIPCIONES ================= -->
    <div v-show="section === 'suscriptions'">
      <div class="page-head">
        <div>
          <h1>Suscripciones</h1>
          <p>Estado de las suscripciones de todos los clientes.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadSuscriptions()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <div v-if="admin.suscriptionsStatus === 'loading'" class="card"><p>Cargando suscripciones…</p></div>
      <div v-else-if="admin.suscriptionsStatus === 'error'" class="card"><p>{{ admin.lastError }}</p></div>
      <template v-else-if="admin.suscriptions.length">
        <p class="table-count">{{ admin.suscriptions.length }} suscripción(es)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Plan pendiente</th>
                <th>Inicio</th>
                <th>Vence</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in admin.suscriptions" :key="s.id">
                <td data-label="Cliente"><strong>{{ clientName(s) }}</strong><br /><small class="muted">{{ s.user_name }} · {{ s.user_email }}</small></td>
                <td data-label="Plan">{{ s.plan_name }}</td>
                <td data-label="Estado"><span class="pill" :class="suscriptionStatusMeta(s.status).kind">{{ suscriptionStatusMeta(s.status).label }}</span></td>
                <td data-label="Plan pendiente">{{ s.pending_plan_name || '—' }}</td>
                <td data-label="Inicio">{{ fmtDate(s.start_date) }}</td>
                <td data-label="Vence">{{ fmtDate(s.end_date) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="credit-card" :size="28" /></span>
        <h3>Sin suscripciones registradas</h3>
        <p>Cuando un cliente active un plan, va a aparecer acá con su vigencia y estado.</p>
      </div>
    </div>

    <!-- ================= WEBS ================= -->
    <div v-show="section === 'webs'">
      <div class="page-head">
        <div>
          <h1>Webs de clientes</h1>
          <p>Todas las webs creadas en el sistema: dueño, plan y acceso vigente.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadStores()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.storesStatus === 'error'" kind="error" :message="admin.lastError" />

      <div v-if="admin.storesStatus === 'loading'" class="card"><p>Cargando las webs…</p></div>
      <template v-else-if="admin.stores.length">
        <div class="toolbar">
          <input v-model="storesQuery" class="input" type="search" placeholder="Buscar por web, slug, dueño o email" aria-label="Buscar webs" />
          <select v-model="storesStatusFilter" class="select" aria-label="Filtrar por estado de la web">
            <option value="all">Todos los estados</option>
            <option value="live">En vivo</option>
            <option value="draft">Borrador</option>
            <option value="no_access">Sin acceso</option>
            <option value="blocked">Bloqueadas</option>
          </select>
        </div>
        <p class="table-count">{{ filteredStores.length }} de {{ admin.stores.length }} web(s)</p>
        <p v-if="!filteredStores.length" class="hint">Ninguna web coincide con los filtros.</p>
        <div v-else class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>Web</th>
                <th>Dueño</th>
                <th>Plan</th>
                <th>Estado</th>
                <th>Creada</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <template v-for="s in filteredStores" :key="s.id">
                <tr>
                  <td data-label="Web"><strong>{{ s.customization?.display_name || s.business_name || s.slug }}</strong><br /><small class="mono">/{{ s.slug }}</small></td>
                  <td data-label="Dueño">{{ s.owner_name }}<br /><small class="muted">{{ s.owner_email }}</small></td>
                  <td data-label="Plan">{{ s.plan_name || '—' }}</td>
                  <td data-label="Estado">
                    <span class="pill" :class="webStatus(s).kind">{{ webStatus(s).label }}</span>
                    <template v-if="s.is_blocked"><br /><small class="muted">{{ s.blocked_reason || 'Sin motivo cargado' }} · {{ fmtDate(s.blocked_at) }}</small></template>
                  </td>
                  <td data-label="Creada">{{ fmtDate(s.created_at) }}</td>
                  <td data-label="Acciones">
                    <div class="assign-cell">
                      <a class="btn ghost sm" :href="`/${s.slug}`" target="_blank" rel="noopener" :aria-label="`Abrir la web ${s.slug}`"><AppIcon name="external-link" :size="14" /> Ver</a>
                      <button
                        v-if="s.is_blocked"
                        class="btn ghost sm"
                        :disabled="blockBusyId === s.id"
                        @click="unblockStore(s)"
                      >
                        <span v-if="blockBusyId === s.id" class="spinner"></span>
                        <AppIcon v-else name="shield-check" :size="14" />
                        Desbloquear
                      </button>
                      <button v-else class="btn ghost sm" @click="startBlock(s)"><AppIcon name="lock" :size="14" /> Bloquear</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="blockingId === s.id" class="block-form-row">
                  <td colspan="6">
                    <div class="block-form">
                      <label :for="`block-reason-${s.id}`">Motivo del bloqueo</label>
                      <select :id="`block-reason-${s.id}`" v-model="blockReason" class="select">
                        <option v-for="r in BLOCK_REASONS" :key="r" :value="r">{{ r }}</option>
                      </select>
                      <button class="btn danger sm" :disabled="blockBusyId === s.id" @click="confirmBlock(s)">
                        <span v-if="blockBusyId === s.id" class="spinner"></span>
                        <AppIcon v-else name="lock" :size="14" />
                        Confirmar bloqueo
                      </button>
                      <button class="btn ghost sm" :disabled="blockBusyId === s.id" @click="blockingId = null">Cancelar</button>
                    </div>
                    <p class="block-form-note">La web pública queda fuera de línea de inmediato y lo sigue hasta que la desbloquees. El dueño conserva el acceso a su panel.</p>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="monitor" :size="28" /></span>
        <h3>Sin webs registradas</h3>
        <p>Cuando un cliente cree su web, va a aparecer acá con su link público.</p>
      </div>
    </div>

    <!-- ================= PLANES ================= -->
    <div v-show="section === 'plans'">
      <div class="page-head">
        <div>
          <h1>Planes</h1>
          <p>Catálogo de planes de suscripción visibles para los clientes.</p>
        </div>
      </div>

      <AlertMessage v-if="admin.lastError && admin.planFormStatus === 'error'" kind="error" :message="admin.lastError" />

      <div class="grid-2">
        <div class="card">
          <h3><AppIcon :name="planForm.id ? 'pencil' : 'plus'" :size="18" /> {{ planForm.id ? 'Editar plan' : 'Nuevo plan' }}</h3>
          <form @submit.prevent="submitPlan" novalidate>
            <AppInput v-model="planForm.name" label="Nombre" name="plan_name" type="text" placeholder="Ej. Estándar" :error="planError" @blur="planTouched = true" />
            <AppInput v-model="planForm.price" label="Precio mensual (ARS)" name="plan_price" type="number" placeholder="Ej. 35000" :error="priceError" @blur="planTouched = true" />
            <div class="btn-row">
              <AppButton :loading="admin.planFormStatus === 'loading'">{{ planForm.id ? 'Guardar cambios' : 'Crear plan' }}</AppButton>
              <button v-if="planForm.id" type="button" class="btn ghost" @click="resetPlanForm">Cancelar</button>
            </div>
          </form>
        </div>
        <div class="card">
          <h3><AppIcon name="package" :size="18" /> Catálogo actual</h3>
          <div v-if="admin.plansStatus === 'loading'"><p>Cargando planes…</p></div>
          <template v-else-if="admin.plans.length">
            <div v-for="p in admin.plans" :key="p.id" class="plan-row">
              <div>
                <strong>{{ p.name }}</strong>
                <small class="muted">{{ formatARS(p.price) }}/mes · {{ planStats[p.name]?.suscriptions ?? 0 }} suscripción(es)</small>
              </div>
              <button class="btn ghost sm" @click="editPlan(p)"><AppIcon name="pencil" :size="14" /> Editar</button>
            </div>
          </template>
          <p v-else>Todavía no hay planes cargados.</p>
        </div>
      </div>
    </div>

    <!-- ================= CUPONES ================= -->
    <div v-show="section === 'coupons'">
      <div class="page-head">
        <div>
          <h1>Cupones</h1>
          <p>Códigos promocionales canjeables: otorgan días de acceso a un plan sin cobro.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadCoupons()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.couponFormStatus === 'error'" kind="error" :message="admin.lastError" />

      <div class="grid-2 stack">
        <div class="card">
          <h3><AppIcon :name="couponForm.id ? 'pencil' : 'plus'" :size="18" /> {{ couponForm.id ? 'Editar cupón' : 'Nuevo cupón' }}</h3>
          <form @submit.prevent="submitCoupon" novalidate>
            <AppInput v-model="couponForm.code" label="Código" name="coupon_code" type="text" placeholder="Ej. SEMANA7" hint="Se normaliza a mayúsculas. El canje no distingue mayúsculas." :error="couponCodeError" @blur="couponTouched = true" />
            <div class="field">
              <label for="coupon_plan">Plan que otorga</label>
              <select id="coupon_plan" v-model="couponForm.plan" class="select" @blur="couponTouched = true">
                <option value="" disabled>Elegí un plan</option>
                <option v-for="p in admin.plans" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <p v-if="couponPlanError" class="field-error" role="alert">{{ couponPlanError }}</p>
            </div>
            <AppInput v-model="couponForm.days" label="Días de acceso" name="coupon_days" type="number" placeholder="Ej. 7" :error="couponDaysError" @blur="couponTouched = true" />
            <AppInput v-model="couponForm.max_uses" label="Máximo de canjes (opcional)" name="coupon_max_uses" type="number" placeholder="Vacío = ilimitado" />
            <AppInput v-model="couponForm.expires_at" label="Vencimiento (opcional)" name="coupon_expires" type="date" />
            <div class="btn-row">
              <AppButton :loading="admin.couponFormStatus === 'loading'">{{ couponForm.id ? 'Guardar cambios' : 'Crear cupón' }}</AppButton>
              <button v-if="couponForm.id" type="button" class="btn ghost" @click="resetCouponForm">Cancelar</button>
            </div>
          </form>
        </div>
        <div class="card">
          <h3><AppIcon name="gift" :size="18" /> Cupones cargados</h3>
          <div v-if="admin.couponsStatus === 'loading'"><p>Cargando cupones…</p></div>
          <template v-else-if="admin.coupons.length">
            <div class="table-wrap">
              <table class="pay-table">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Otorga</th>
                    <th>Canjes</th>
                    <th>Vence</th>
                    <th>Estado</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <template v-for="c in admin.coupons" :key="c.id">
                    <tr>
                      <td data-label="Código"><strong class="mono">{{ c.code }}</strong></td>
                      <td data-label="Otorga">{{ c.plan_name }} · {{ c.days }}d</td>
                      <td data-label="Canjes">
                        <button class="btn ghost sm" @click="toggleCouponDetail(c)">{{ couponUsesLabel(c) }}</button>
                      </td>
                      <td data-label="Vence">{{ c.expires_at ? fmtDate(c.expires_at) : '—' }}</td>
                      <td data-label="Estado"><span class="pill" :class="couponStatus(c).kind">{{ couponStatus(c).label }}</span></td>
                      <td data-label="Acciones">
                        <div class="assign-cell">
                          <button class="btn ghost sm" @click="editCoupon(c)"><AppIcon name="pencil" :size="14" /> Editar</button>
                          <button class="btn ghost sm" :disabled="couponBusyId === c.id" @click="toggleCoupon(c)">
                            <span v-if="couponBusyId === c.id" class="spinner"></span>
                            {{ c.is_active ? 'Desactivar' : 'Activar' }}
                          </button>
                        </div>
                      </td>
                    </tr>
                    <tr v-if="expandedCoupon === c.id" class="coupon-detail-row">
                      <td colspan="6">
                        <div v-if="c.redemptions?.length" class="coupon-detail">
                          <strong>Canjes de {{ c.code }}</strong>
                          <div v-for="r in c.redemptions" :key="r.id" class="coupon-redemption">
                            <span>{{ r.business_name || r.user_name }} <small class="muted">{{ r.user_email }}</small></span>
                            <small class="muted">{{ formatDateTime(r.redeemed_at) }}</small>
                          </div>
                        </div>
                        <p v-else class="muted">Nadie canjeó este cupón todavía.</p>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </template>
          <p v-else>Todavía no hay cupones cargados.</p>
        </div>
      </div>
    </div>

    <!-- ================= USUARIOS ================= -->
    <div v-show="section === 'users'">
      <div class="page-head">
        <div>
          <h1>Usuarios</h1>
          <p>Cuentas registradas en el sistema.</p>
        </div>
        <button class="btn ghost btn-auto" @click="admin.loadUsers()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="admin.notice" kind="success" :message="admin.notice" />
      <AlertMessage v-if="admin.lastError && admin.assignStatus === 'error'" kind="error" :message="admin.lastError" />

      <div v-if="admin.usersStatus === 'loading'" class="card"><p>Cargando usuarios…</p></div>
      <div v-else-if="admin.usersStatus === 'error'" class="card"><p>{{ admin.lastError }}</p></div>
      <template v-else-if="admin.users.length">
        <p class="table-count">{{ admin.users.length }} cuenta(s) · {{ staffCount }} administrador(es)</p>
        <div class="table-wrap">
          <table class="pay-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Plan actual</th>
                <th>Asignar plan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in admin.users" :key="u.id">
                <td data-label="ID"><span class="mono">#{{ u.id }}</span></td>
                <td data-label="Usuario"><strong>{{ u.username }}</strong></td>
                <td data-label="Email">{{ u.email || '—' }}</td>
                <td data-label="Rol"><span class="pill" :class="u.is_staff ? 'ok' : 'muted'">{{ u.is_staff ? 'Administrador' : 'Cliente' }}</span></td>
                <td data-label="Plan actual">
                  <template v-if="suscriptionByUser[u.id]">
                    {{ suscriptionByUser[u.id].plan_name }}
                    <span class="pill" :class="suscriptionByUser[u.id].is_current ? 'ok' : 'muted'">{{ suscriptionByUser[u.id].is_current ? 'Vigente' : 'Vencido' }}</span>
                  </template>
                  <span v-else class="muted">Sin plan</span>
                </td>
                <td data-label="Asignar plan">
                  <div v-if="!u.is_staff" class="assign-cell">
                    <select v-model="assignSel[u.id]" class="select" :aria-label="`Plan para ${u.username}`">
                      <option :value="undefined" disabled>Elegí un plan</option>
                      <option v-for="p in admin.plans" :key="p.id" :value="p.id">{{ p.name }}</option>
                    </select>
                    <button class="btn sm" :disabled="!assignSel[u.id] || assigningId === u.id" @click="assignTo(u)">
                      <span v-if="assigningId === u.id" class="spinner"></span>
                      <AppIcon v-else name="check" :size="14" />
                      Asignar
                    </button>
                  </div>
                  <span v-else class="muted">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="users" :size="28" /></span>
        <h3>Sin usuarios registrados</h3>
        <p>Las cuentas creadas desde el registro van a listarse acá.</p>
      </div>
    </div>

    <!-- ================= CHAT SOPORTE ================= -->
    <div v-show="section === 'chat'">
      <div class="page-head">
        <div>
          <h1>Chat de soporte</h1>
          <p>Conversaciones con clientes del plan Premium.</p>
        </div>
        <span class="presence-chip" :class="{ on: chatOnlineCount > 0 }">
          <span class="presence-dot"></span>
          {{ chatOnlineCount }} cliente{{ chatOnlineCount === 1 ? '' : 's' }} en línea
        </span>
      </div>

      <AlertMessage v-if="chatErr" kind="error" :message="chatErr" />

      <!-- Bandeja estilo Messenger: la conversación abre en una ventana
           flotante abajo a la derecha (por encima del bot del panel). -->
      <div class="chat-inbox">
        <div class="chat-threads-head">
          <h3><AppIcon name="message-circle" :size="16" /> Conversaciones</h3>
          <label class="chat-inbox-search">
            <AppIcon name="search" :size="14" />
            <input v-model="chatQuery" type="search" placeholder="Buscar cliente…" aria-label="Buscar conversación" />
          </label>
          <span v-if="chatThreads.length" class="support-count">{{ chatThreads.length }}</span>
        </div>
        <div v-if="filteredChatThreads.length" class="chat-thread-list">
          <button
            v-for="t in filteredChatThreads"
            :key="t.id"
            type="button"
            class="chat-thread"
            :class="{ active: chatActive?.id === t.id, unread: t.unread }"
            @click="onThreadClick(t)"
          >
            <span class="support-avatar">
              {{ chatInitials(t.customer.name) }}
              <span class="support-status" :class="{ on: t.online }"></span>
            </span>
            <span class="chat-thread-body">
              <span class="chat-thread-head">
                <strong>{{ t.customer.name }}</strong>
                <span v-if="t.last_message" class="chat-thread-time">{{ fmtChatTime(t.last_message.created_at) }}</span>
              </span>
              <span class="chat-thread-row">
                <span class="chat-thread-last">{{ t.last_message ? (t.last_message.body || 'Imagen adjunta') : 'Sin mensajes' }}</span>
                <span v-if="t.unread" class="chat-badge">{{ t.unread }}</span>
              </span>
            </span>
          </button>
        </div>
        <p v-else class="chat-threads-empty">{{ chatThreads.length ? 'Ninguna conversación coincide con la búsqueda.' : 'Ningún cliente escribió todavía.' }}</p>
      </div>
    </div>

    <!-- Burbuja de mensajería estilo Messenger (arrastrable, queda anclada
         a una arista): punto verde = clientes en línea, badge = no leídos.
         Abre la bandeja rápida o la ventana de conversación. -->
    <ChatDock
      :content="chatDockContent"
      :online="chatOnlineCount > 0"
      :unread="chatUnread"
      :minimized="chatMin"
      label="Mensajes de clientes"
      @toggle="onDockToggle"
    >
      <!-- Bandeja rápida: mismas conversaciones de la sección Chat. -->
      <div v-if="chatDockOpen" class="chat-dock-panel">
        <div class="chat-threads-head">
          <h3><AppIcon name="message-circle" :size="16" /> Conversaciones</h3>
          <label class="chat-inbox-search">
            <AppIcon name="search" :size="14" />
            <input v-model="chatQuery" type="search" placeholder="Buscar cliente…" aria-label="Buscar conversación" />
          </label>
          <span v-if="chatThreads.length" class="support-count">{{ chatThreads.length }}</span>
        </div>
        <div v-if="filteredChatThreads.length" class="chat-thread-list dock">
          <button
            v-for="t in filteredChatThreads"
            :key="t.id"
            type="button"
            class="chat-thread"
            :class="{ unread: t.unread }"
            @click="openChatThread(t)"
          >
            <span class="support-avatar">
              {{ chatInitials(t.customer.name) }}
              <span class="support-status" :class="{ on: t.online }"></span>
            </span>
            <span class="chat-thread-body">
              <span class="chat-thread-head">
                <strong>{{ t.customer.name }}</strong>
                <span v-if="t.last_message" class="chat-thread-time">{{ fmtChatTime(t.last_message.created_at) }}</span>
              </span>
              <span class="chat-thread-row">
                <span class="chat-thread-last">{{ t.last_message ? (t.last_message.body || 'Imagen adjunta') : 'Sin mensajes' }}</span>
                <span v-if="t.unread" class="chat-badge">{{ t.unread }}</span>
              </span>
            </span>
          </button>
        </div>
        <p v-else class="chat-threads-empty">{{ chatThreads.length ? 'Ninguna conversación coincide con la búsqueda.' : 'Ningún cliente escribió todavía.' }}</p>
      </div>

      <!-- Ventana flotante de conversación (estilo chat de Facebook):
           se minimiza al header, cierra con Esc o la X, y al abrirse el
           foco cae en el textarea. -->
      <Transition v-else-if="chatActive" name="chatwin">
        <section
          class="chat-win"
          :class="{ min: chatMin }"
          role="dialog"
          aria-modal="false"
          :aria-label="`Conversación con ${chatActive.customer.name}`"
        >
          <header class="chat-win-head" @click="toggleChatMin">
            <span class="support-avatar">
              {{ chatInitials(chatActive.customer.name) }}
              <span class="support-status" :class="{ on: chatActive.online }"></span>
            </span>
            <div class="chat-modal-who">
              <strong>{{ chatActive.customer.name }}</strong>
              <small><span class="chat-win-state" :class="{ on: chatActive.online }">{{ chatActive.online ? 'En línea ahora' : 'Desconectado' }}</span> · {{ chatActive.customer.email }}</small>
            </div>
            <span class="chat-win-actions">
              <span v-if="chatMin && chatActive.unread" class="chat-badge">{{ chatActive.unread }}</span>
              <button
                type="button"
                class="chat-win-btn"
                :aria-label="chatMin ? 'Expandir chat' : 'Minimizar chat'"
                :title="chatMin ? 'Expandir' : 'Minimizar'"
                @click.stop="toggleChatMin"
              >
                <AppIcon :name="chatMin ? 'chevron-up' : 'chevron-down'" :size="15" />
              </button>
              <button
                type="button"
                class="chat-win-btn"
                aria-label="Cerrar chat"
                title="Cerrar"
                @click.stop="closeChatWindow"
              >
                <AppIcon name="x" :size="15" />
              </button>
            </span>
          </header>

          <template v-if="!chatMin">
            <div ref="chatBoxEl" class="chat-box">
              <p v-if="!chatMsgs.length" class="chat-empty">Todavía no hay mensajes en esta conversación.</p>
              <template v-for="r in chatRows(chatMsgs)" :key="r.key">
                <div v-if="r.day" class="chat-day">{{ r.day }}</div>
                <div v-else class="chat-row" :class="{ mine: r.m.mine, first: r.first, last: r.last, 'gap-top': r.first }">
                  <span v-if="!r.m.mine" class="chat-avatar" :class="{ ghost: !r.last }">{{ chatInitials(r.m.sender_name) }}</span>
                  <div class="chat-stack">
                    <div class="chat-msg" :class="{ pending: r.m.pending, media: r.m.image_url && !r.m.body }">
                      <a v-if="r.m.image_url" class="chat-img-link" :href="r.m.image_url" target="_blank" rel="noopener" title="Abrir imagen en pestaña nueva">
                        <img class="chat-img" :src="r.m.image_url" alt="Imagen adjunta" loading="lazy">
                      </a>
                      <p v-if="r.m.body" class="chat-body">{{ r.m.body }}</p>
                    </div>
                    <span v-if="r.last" class="chat-meta">{{ r.m.pending ? 'Enviando…' : fmtChatTime(r.m.created_at) }}</span>
                  </div>
                </div>
              </template>
            </div>
            <div v-if="chatFiles.length" class="chat-files">
              <div v-for="(f, i) in chatFiles" :key="f.url" class="chat-file">
                <img :src="f.url" :alt="f.file.name">
                <button type="button" class="chat-file-x" aria-label="Quitar imagen" @click="removeChatFile(i)">
                  <AppIcon name="x" :size="10" />
                </button>
              </div>
            </div>
            <div class="chat-composer">
              <input
                ref="chatFileInput"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                multiple
                hidden
                @change="onChatFiles"
              >
              <button
                type="button"
                class="chat-attach"
                :disabled="chatBusy || chatFiles.length >= CHAT_FILES_MAX"
                aria-label="Adjuntar imagen"
                title="Adjuntar imagen"
                @click="pickChatImages"
              >
                <AppIcon name="image" :size="17" />
              </button>
              <textarea
                ref="chatInputEl"
                v-model="chatInput"
                class="chat-text"
                rows="1"
                maxlength="2000"
                placeholder="Respondé al cliente…"
                aria-label="Respuesta al cliente"
                @input="resizeChatInput"
                @keydown.enter="onComposerEnter"
              ></textarea>
              <button
                type="button"
                class="chat-send"
                :disabled="(!chatInput.trim() && !chatFiles.length) || chatBusy"
                aria-label="Enviar respuesta"
                @click="sendChat"
              >
                <AppIcon name="send" :size="17" />
              </button>
            </div>
          </template>
        </section>
      </Transition>
    </ChatDock>
  </DashLayout>
</template>
