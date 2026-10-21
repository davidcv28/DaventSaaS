<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useBillingStore } from '../stores/billing.store.js'
import { usePaymentsStore } from '../stores/payments.store.js'
import { useInvoicesStore } from '../stores/invoices.store.js'
import { useStoreStore } from '../stores/store.store.js'
import { useSlugCheck } from '../composables/useSlugCheck.js'
import {
  normalizeSlug, publicStoreUrl,
  CUSTOMIZATION_DEFAULTS, STORE_ACCENTS, STORE_THEMES, storeThemeVars,
  validateHeadline, validateDescription, validateWhatsapp, validateInstagram,
  normalizeWhatsapp, normalizeInstagram
} from '../api/stores.api.js'
import { formatARS } from '../api/billing.api.js'
import { formatDate as formatInvDate } from '../api/invoices.api.js'
import { paymentStatusMeta, formatDateTime, MONTH_NAMES } from '../api/payments.api.js'
import { locationsApi } from '../api/locations.api.js'
import {
  TAX_CONDITIONS, validatePassword, validateEmail, validateName,
  validateDocument, validateBusinessName, validatePhone, validateAddress,
  documentKindFor
} from '../validators/auth.validators.js'
import DashLayout from '../components/DashLayout.vue'
import PlanCard from '../components/PlanCard.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PasswordStrength from '../components/PasswordStrength.vue'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const billing = useBillingStore()
const payments = usePaymentsStore()
const invoices = useInvoicesStore()
const store = useStoreStore()

const section = ref('overview')
const busyPlan = ref(null)
const passForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const touched = reactive({})
const passMsg = ref('')
const passErr = ref('')

// --- Cuenta: edición de correo + perfil fiscal ---
const accountForm = reactive({
  email: '', first_name: '', last_name: '', tax_condition: 'CF', business_name: '',
  document: '', province: '', city: '', address: '', phone: ''
})
const accountTouched = reactive({})
const accountMsg = ref('')
const accountErr = ref('')
const accountBusy = ref(false)
const provinces = ref([])
const cities = ref([])
const geoNotice = ref('')
const geoErr = ref('')

const docKind = computed(() => documentKindFor(accountForm.tax_condition))
const docHint = computed(() =>
  docKind.value === 'DNI'
    ? 'DNI: 7 a 8 dígitos.'
    : 'CUIT/CUIL: 11 dígitos con prefijo válido (20, 23, 24, 27, 30, 33, 34) y dígito verificador.'
)
watch(() => accountForm.tax_condition, () => { accountTouched.document = false })

async function loadAccountProvinces() {
  try {
    provinces.value = await locationsApi.getProvinces()
    geoNotice.value = locationsApi.usingFallback
      ? 'La API no respondió: usando catálogo local de emergencia. Revisá que Django esté corriendo.'
      : ''
  } catch {
    geoErr.value = 'No se pudieron cargar las provincias. Reintentá recargando.'
  }
}

async function loadAccountCities() {
  cities.value = []
  if (!accountForm.province) return
  try {
    cities.value = await locationsApi.getCities(accountForm.province)
  } catch {
    cities.value = []
  }
}

// Cambio manual de provincia: la ciudad guardada ya no aplica.
function onAccountProvinceChange() {
  accountForm.city = ''
  loadAccountCities()
}

// Precarga desde auth.user (perfil ya trae province/city como ids).
// Carga las ciudades de la provincia guardada sin pisar la ciudad actual.
async function fillAccountForm() {
  const p = auth.user?.profile || {}
  Object.assign(accountForm, {
    email: auth.user?.email || '',
    first_name: p.first_name || '',
    last_name: p.last_name || '',
    tax_condition: p.tax_condition || 'CF',
    business_name: p.business_name || '',
    document: p.document || '',
    province: p.province || '',
    city: p.city || '',
    address: p.address || '',
    phone: p.phone || ''
  })
  Object.keys(accountTouched).forEach((k) => { accountTouched[k] = false })
  await loadAccountCities()
}

const accountErrors = computed(() => {
  const e = {}
  const m = validateEmail(accountForm.email)
  const fn = validateName(accountForm.first_name, 'Nombre')
  const ln = validateName(accountForm.last_name, 'Apellido')
  const bn = validateBusinessName(accountForm.business_name, accountForm.tax_condition)
  const dc = validateDocument(accountForm.document, accountForm.tax_condition)
  const ad = validateAddress(accountForm.address)
  const ph = validatePhone(accountForm.phone)
  if (m) e.email = m
  if (fn) e.first_name = fn
  if (ln) e.last_name = ln
  if (bn) e.business_name = bn
  if (dc) e.document = dc
  if (!accountForm.province) e.province = 'Seleccioná tu provincia'
  if (!accountForm.city) e.city = 'Seleccioná tu ciudad'
  if (ad) e.address = ad
  if (ph) e.phone = ph
  return e
})

function accountFieldErr(name) {
  if (!accountTouched[name]) return ''
  return accountErrors.value[name] || auth.fieldErrors[name] || ''
}

async function saveAccount() {
  Object.keys(accountForm).forEach((k) => { accountTouched[k] = true })
  accountMsg.value = ''
  accountErr.value = ''
  if (Object.keys(accountErrors.value).length) return
  accountBusy.value = true
  try {
    const res = await auth.updateAccount({
      email: accountForm.email.trim(),
      profile: {
        first_name: accountForm.first_name.trim(),
        last_name: accountForm.last_name.trim(),
        tax_condition: accountForm.tax_condition,
        business_name: accountForm.business_name.trim() || null,
        document: accountForm.document.trim(),
        province: Number(accountForm.province),
        city: Number(accountForm.city),
        address: accountForm.address.trim() || null,
        phone: accountForm.phone.trim() || null
      }
    })
    if (res.ok) {
      accountMsg.value = res.message
      await fillAccountForm()
    } else {
      accountErr.value = auth.lastError
    }
  } finally {
    accountBusy.value = false
  }
}

async function reloadAccount() {
  await auth.fetchMe()
  await fillAccountForm()
}

const initial = computed(() => (auth.user?.username || auth.user?.email || 'U').slice(0, 1).toUpperCase())
const displayName = computed(() => auth.user?.username || auth.user?.email || 'Usuario DAVENT')

// Menú del sidebar: el staff ve además la entrada al panel de administración.
// El grupo "Avanzado" es el menú premium (flag has_advanced_menu); cada entrada
// se muestra solo si el plan vigente habilita su beneficio.
const navItems = computed(() => {
  const b = plan.value?.benefits || {}
  const items = [
    { id: 'overview', label: 'Resumen', icon: 'dashboard' },
    { id: 'store', label: 'Mi tienda', icon: 'store' },
    { id: 'catalogs', label: 'Mis catálogos', icon: 'library' }
  ]
  const advanced = []
  if (b.has_customization) advanced.push({ id: 'design', label: 'Diseño web', icon: 'palette' })
  if (b.has_stats) advanced.push({ id: 'stats', label: 'Estadísticas', icon: 'trending-up' })
  if (b.has_qr || b.has_flyers) advanced.push({ id: 'tools', label: 'QR y folletos', icon: 'qr-code' })
  if (b.has_advanced_menu && advanced.length) {
    items.push({ heading: 'Avanzado' }, ...advanced)
  }
  items.push(
    { id: 'plans', label: 'Planes', icon: 'credit-card' },
    { id: 'payments', label: 'Pagos', icon: 'receipt' },
    { id: 'invoices', label: 'Facturas', icon: 'file-text' },
    { id: 'settings', label: 'Cuenta', icon: 'user' }
  )
  if (auth.user?.is_staff) {
    items.push({ heading: 'Administración' }, { id: 'admin', label: 'Panel admin', icon: 'shield-check' })
  }
  return items
})

function onNavigate(id) {
  if (id === 'admin') {
    router.push({ name: 'admin' })
    return
  }
  section.value = id
}
const business = computed(() => auth.user?.profile?.business_name || '')
const plan = computed(() => billing.currentPlan)
const catalogLimit = computed(() => {
  if (!plan.value) return 'Activá un plan para habilitar tu catálogo'
  const max = plan.value.benefits?.max_products
  if (max === undefined) return 'Tu plan habilita tu catálogo'
  return max === null ? 'Tu plan incluye productos ilimitados' : `Tu plan incluye hasta ${max} productos`
})

const planProgress = computed(() => {
  const p = plan.value
  if (!p?.start || !p?.end) return 0
  const total = new Date(p.end) - new Date(p.start)
  if (total <= 0) return 0
  return Math.min(100, Math.max(0, Math.round(((Date.now() - new Date(p.start)) / total) * 100)))
})

const nextSteps = computed(() => [
  { title: 'Reservá tu link público', text: 'Es la dirección de tu tienda.', done: store.hasStore },
  { title: 'Elegí un plan', text: 'Definí el tamaño de tu catálogo.', done: billing.hasSubscription },
  { title: 'Cargá tus productos', text: 'Sumá fotos, precios y stock.', done: false },
  { title: 'Compartí tu link público', text: 'Enviáselo a tus clientes.', done: false }
])

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// --- Mi tienda: link público (copiar, abrir, pausar, renombrar) ---
const renameSlug = ref('')
const renameBusy = ref(false)
const storeBusy = ref(false)
const { state: renameCheck, isAvailable: renameOk, message: renameMsg, kind: renameKind, requestCheck: requestRenameCheck, clear: clearRenameCheck } = useSlugCheck()

const publicUrl = computed(() => (store.store ? publicStoreUrl(store.store.slug) : ''))
const canRename = computed(() => renameOk.value && !renameBusy.value)

function onRenameInput(event) {
  renameSlug.value = event.target.value
  requestRenameCheck(event.target.value, { current: store.store?.slug || '' })
}

async function saveRename() {
  if (!canRename.value) return
  renameBusy.value = true
  const ok = await store.update({ slug: normalizeSlug(renameSlug.value) })
  renameBusy.value = false
  if (ok) {
    renameSlug.value = ''
    clearRenameCheck()
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(publicUrl.value)
    store.notice = 'Link copiado al portapapeles.'
  } catch {
    store.notice = `Tu link es ${publicUrl.value}`
  }
}

function openStore() {
  if (publicUrl.value) window.open(publicUrl.value, '_blank', 'noopener')
}

async function togglePublished() {
  if (!store.store || storeBusy.value) return
  storeBusy.value = true
  await store.update({ is_published: !store.store.is_published })
  storeBusy.value = false
}

// --- Diseño web: personalización premium de la página pública ---
// Editable solo con el beneficio has_customization (el backend lo fuerza en PATCH).
const designForm = reactive({ ...CUSTOMIZATION_DEFAULTS })
const designTouched = reactive({})
const designBusy = ref(false)
const canCustomize = computed(() => Boolean(plan.value?.benefits?.has_customization))
const businessInitial = computed(() => (business.value || 'T').slice(0, 1).toUpperCase())
const designPreviewVars = computed(() => storeThemeVars(designForm))
const storeAccents = STORE_ACCENTS
const storeThemes = STORE_THEMES

// Precarga el diseño guardado cuando llega la tienda (customization anidada).
watch(() => store.store, (s) => {
  if (s) Object.assign(designForm, store.customization)
}, { immediate: true })

const designErrors = computed(() => {
  const e = {}
  const h = validateHeadline(designForm.headline.trim())
  const d = validateDescription(designForm.description.trim())
  const w = validateWhatsapp(designForm.whatsapp)
  const ig = validateInstagram(designForm.instagram)
  if (h) e.headline = h
  if (d) e.description = d
  if (w) e.whatsapp = w
  if (ig) e.instagram = ig
  return e
})

function designFieldErr(name) {
  return (designTouched[name] ? designErrors.value[name] || '' : '') || store.fieldErrors[name] || ''
}

async function saveDesign() {
  Object.keys(designForm).forEach((k) => { designTouched[k] = true })
  if (Object.keys(designErrors.value).length) return
  designBusy.value = true
  await store.saveCustomization({
    headline: designForm.headline.trim(),
    description: designForm.description.trim(),
    theme: designForm.theme,
    accent: designForm.accent,
    whatsapp: normalizeWhatsapp(designForm.whatsapp),
    instagram: normalizeInstagram(designForm.instagram)
  })
  designBusy.value = false
}

onMounted(async () => {
  await auth.fetchMe()
  fillAccountForm()
  loadAccountProvinces()
  if (store.status === 'idle') store.loadMine()
  await Promise.all([billing.loadPlans(), billing.loadMine(), payments.loadPayments(), invoices.loadInvoices()])
  // Primero el retorno del checkout (trae payment_id en la URL): es la vía instantánea.
  await handlePaymentReturn()
  // Red de seguridad: registra pagos ya acreditados en MP que aún no estén en el sistema.
  const synced = await payments.sync()
  if (synced > 0) await Promise.all([billing.loadMine(), payments.loadPayments()])
  // Rollups de ingresos: solo existen para admin (el store detecta 403).
  if (auth.user?.is_staff) payments.loadRevenues()
  // Puente entre pestañas: el retorno de MP cae en la pestaña del checkout,
  // esta escucha avisa a la pestaña original para acreditar al instante.
  window.addEventListener('storage', onPaymentBroadcast)
})

onUnmounted(() => {
  stopCheckoutWatch()
  window.removeEventListener('storage', onPaymentBroadcast)
})

// La pestaña del checkout avisa por acá cuando vuelve de Mercado Pago.
async function onPaymentBroadcast(event) {
  if (event.key !== 'davent:last-payment' || !event.newValue) return
  let payload = null
  try { payload = JSON.parse(event.newValue) } catch { return }
  if (!payload?.payment_id) return
  const synced = await payments.sync(payload.payment_id)
  if (synced > 0 || payload.status === 'approved') {
    await Promise.all([billing.loadMine(), payments.loadPayments()])
    showPlanActivated()
    stopCheckoutWatch()
  }
}

function broadcastPaymentReturn(paymentId, pay) {
  try {
    localStorage.setItem('davent:last-payment', JSON.stringify({ payment_id: String(paymentId), pay: pay || null, at: Date.now() }))
  } catch {
    // Si el navegador bloquea el storage, la pestaña original sigue con el polling.
  }
}

// Retorno de Mercado Pago (Checkout Pro): back_urls -> /dashboard?pay=...&payment_id=...
async function handlePaymentReturn() {
  const q = route.query
  const paymentId = q.payment_id || q.collection_id
  const payStatus = q.pay || q.status || q.collection_status
  if (!payStatus && !paymentId) return
  // Avisa a la pestaña original (el retorno cae en la pestaña del checkout).
  if (paymentId) broadcastPaymentReturn(paymentId, payStatus)
  if (paymentId && billing.subscription) {
    // Vía instantánea: verifica ese pago directo en MP y aplica el plan.
    const synced = await payments.sync(paymentId)
    if (synced > 0) {
      await Promise.all([billing.loadMine(), payments.loadPayments()])
      showPlanActivated()
    } else {
      const ok = await payments.confirm({ suscription: billing.subscription.id, paymentId })
      // Si el pago se acreditó, el plan pendiente ya se aplicó en backend.
      if (ok) {
        await billing.loadMine()
        showPlanActivated()
      } else {
        section.value = 'payments'
      }
    }
  } else if (payStatus === 'failure' || payStatus === 'rejected') {
    section.value = 'payments'
    payments.lastError = 'El pago no se completó. Podés intentarlo de nuevo desde la sección Pagos.'
  } else {
    section.value = 'payments'
    payments.notice = 'Tu pago quedó pendiente de acreditación. Se actualiza solo cuando Mercado Pago lo confirme.'
  }
  router.replace({ name: 'dashboard' })
}

// Pago acreditado: lleva al Resumen con el plan ya actualizado.
function showPlanActivated() {
  section.value = 'overview'
  billing.notice = 'Tu pago se acreditó y tu plan ya está activo.'
  payments.notice = ''
}

async function planAction(p) {
  busyPlan.value = p.id
  billing.lastError = ''
  billing.notice = ''
  payments.lastError = ''
  payments.notice = ''
  try {
    // Todos los planes son pagos: la suscripción se establece cuando el pago se acredita.
    // La pestaña se abre dentro del gesto del usuario para que el navegador no la bloquee.
    const checkoutTab = window.open('about:blank', '_blank')
    const url = await payments.checkout({ suscription: billing.subscription?.id ?? null, planPk: p.id })
    if (!url) {
      checkoutTab?.close()
      return
    }
    checkoutTab.location.href = url
    billing.notice = 'Abrimos Mercado Pago en otra pestaña. Cuando el pago se acredite, tu plan se activa solo.'
    startCheckoutWatch(p.id)
  } finally {
    busyPlan.value = null
  }
}

let checkoutWatch = null
function stopCheckoutWatch() {
  if (checkoutWatch) {
    clearInterval(checkoutWatch)
    checkoutWatch = null
  }
}

// Polling a /payments/sync/: cuando MP acredita, el backend aplica el plan pendiente.
function startCheckoutWatch(targetPlanId) {
  stopCheckoutWatch()
  let tries = 0
  checkoutWatch = setInterval(async () => {
    tries += 1
    try {
      await payments.sync()
      await billing.loadMine()
      const s = billing.subscription
      if (s && s.plan_suscription === targetPlanId && s.status === 'Suscripción activa') {
        stopCheckoutWatch()
        await payments.loadPayments()
        showPlanActivated()
        return
      }
      if (tries >= 36) {
        stopCheckoutWatch()
        billing.notice = 'Seguimos esperando la confirmación de Mercado Pago. Si ya pagaste, recargá la página.'
      }
    } catch {
      // Reintenta en el próximo tick.
    }
  }, 5000)
}

// Abre el comprobante imprimible en una pestaña aparte.
function openInvoice(id) {
  const href = router.resolve({ name: 'invoice-print', params: { id } }).href
  window.open(href, '_blank', 'noopener')
}

function logout() {
  billing.reset()
  payments.reset()
  invoices.reset()
  store.reset()
  auth.logout()
  router.push({ name: 'login' })
}

async function changePassword() {
  touched.old_password = true
  touched.new_password = true
  touched.confirm_password = true
  passMsg.value = ''
  passErr.value = ''
  const v = validatePassword(passForm.new_password)
  if (!passForm.old_password) { passErr.value = 'Ingresá tu contraseña actual.'; return }
  if (v) { passErr.value = v; return }
  if (passForm.new_password !== passForm.confirm_password) { passErr.value = 'Las contraseñas no coinciden.'; return }
  if (passForm.old_password === passForm.new_password) { passErr.value = 'No puedes reutilizar la contraseña actual.'; return }
  const res = await auth.updatePassword({ ...passForm })
  if (res.ok) {
    passMsg.value = res.message
    passForm.old_password = ''
    passForm.new_password = ''
    passForm.confirm_password = ''
  } else {
    passErr.value = auth.lastError
  }
}
</script>

<template>
  <DashLayout
    :active="section"
    :items="navItems"
    :plan-name="plan?.name || ''"
    :user-name="displayName"
    :initial="initial"
    @navigate="onNavigate"
    @logout="logout"
  >
    <!-- ================= RESUMEN ================= -->
    <div v-show="section === 'overview'">
      <div class="page-head">
        <div>
          <h1>Hola{{ business ? `, ${business}` : '' }}</h1>
          <p>Este es el centro de tu negocio: suscripción, catálogos y cuenta.</p>
        </div>
      </div>

      <div v-if="!billing.hasSubscription && billing.status !== 'loading'" class="cta-banner">
        <div><strong>Todavía no tenés una suscripción.</strong><br />Elegí un plan para montar tu primer catálogo y compartirlo con tus clientes.</div>
        <button class="btn light btn-auto" @click="section = 'plans'">Ver planes <AppIcon name="arrow-right" :size="16" /></button>
      </div>

      <div v-if="plan" class="hero">
        <div class="hero-main">
          <span class="hero-eyebrow">Tu suscripción</span>
          <h2>{{ plan.name }}</h2>
          <p class="hero-meta"><AppIcon name="calendar" :size="16" /> Vigente del {{ fmtDate(plan.start) }} al {{ fmtDate(plan.end) }}</p>
          <div class="hero-progress" role="progressbar" aria-label="Tiempo transcurrido de la suscripción" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="planProgress">
            <span class="hero-progress-bar" :style="{ width: planProgress + '%' }"></span>
          </div>
          <p class="hero-remaining"><strong>{{ plan.remaining }} días restantes</strong></p>
          <p v-if="billing.subscription?.pending_plan_name" class="hero-pending">Cambio a {{ billing.subscription.pending_plan_name }} pendiente: se aplica cuando se acredite el pago.</p>
        </div>
        <div class="hero-side">
          <span class="badge-ok"><AppIcon name="dot" :size="12" /> {{ plan.status }}</span>
          <div class="hero-price-wrap">
            <strong class="hero-price">{{ formatARS(plan.price) }}</strong>
            <span>por mes</span>
          </div>
          <button class="btn secondary btn-auto" @click="section = 'plans'">Cambiar plan</button>
        </div>
      </div>

      <div v-if="billing.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu suscripción…</p></div>
      <AlertMessage v-if="billing.notice" kind="success" :message="billing.notice" />
      <AlertMessage v-if="billing.lastError" kind="error" :message="billing.lastError" />

      <div class="stats">
        <div class="stat"><span class="stat-icon"><AppIcon name="package" :size="20" /></span><div><strong>0</strong><small>Productos</small></div></div>
        <div class="stat"><span class="stat-icon"><AppIcon name="eye" :size="20" /></span><div><strong>—</strong><small>Visitas (próximamente)</small></div></div>
        <div class="stat"><span class="stat-icon"><AppIcon name="clock" :size="20" /></span><div><strong>{{ plan?.remaining ?? '—' }}</strong><small>Días restantes</small></div></div>
      </div>

      <div class="card">
        <h3><AppIcon name="checklist" :size="18" /> Próximos pasos</h3>
        <ol class="steps-list">
          <li v-for="(s, i) in nextSteps" :key="s.title" :class="{ done: s.done }">
            <span class="steps-num" aria-hidden="true"><AppIcon v-if="s.done" name="check" :size="14" :stroke="2.25" /><template v-else>{{ i + 1 }}</template></span>
            <div><strong>{{ s.title }}</strong><small>{{ s.text }}</small></div>
          </li>
        </ol>
      </div>
    </div>

    <!-- ================= CATÁLOGO ================= -->
    <div v-show="section === 'catalogs'">
      <div class="page-head">
        <div>
          <h1>Mi catálogo</h1>
          <p>{{ catalogLimit }}</p>
        </div>
        <button class="btn btn-auto" disabled title="Disponible en el próximo dominio"><AppIcon name="plus" :size="16" /> Nuevo producto</button>
      </div>
      <AlertMessage kind="info" message="Publicá únicamente imágenes, logos y textos propios o con autorización de uso: sos responsable del contenido de tu catálogo." />
      <div class="empty">
        <span class="empty-icon"><AppIcon name="library" :size="28" /></span>
        <h3>{{ billing.hasSubscription ? 'Todavía no cargaste tu primer producto' : 'Necesitás una suscripción' }}</h3>
        <p>El dominio de catálogo (productos, fotos, stock y link público) es el próximo módulo del sistema. Tu plan ya deja reservado el cupo.</p>
        <button v-if="!billing.hasSubscription" class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>
    </div>
    <!-- ================= MI TIENDA ================= -->
    <div v-show="section === 'store'">
      <div class="page-head">
        <div>
          <h1>Mi tienda</h1>
          <p>Tu link público es la dirección que compartís con tus clientes.</p>
        </div>
      </div>
      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <div v-if="store.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu tienda…</p></div>
      <template v-else-if="store.hasStore">
        <div class="card">
          <h3><AppIcon name="store" :size="18" /> Tu link público</h3>
          <div class="link-bar">
            <code class="mono link-url">{{ publicUrl }}</code>
            <span class="pill" :class="store.store.is_published ? 'ok' : 'muted'">{{ store.store.is_published ? 'Activo' : 'Pausado' }}</span>
          </div>
          <div class="btn-row link-actions">
            <button class="btn ghost btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar link</button>
            <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Abrir tienda</button>
            <button class="btn ghost btn-auto" :disabled="storeBusy" @click="togglePublished">{{ store.store.is_published ? 'Pausar link' : 'Activar link' }}</button>
          </div>
          <p class="hint">Con el link pausado, la página pública muestra “tienda no disponible”.</p>
        </div>

        <div class="card">
          <h3><AppIcon name="pencil" :size="18" /> Cambiar tu link</h3>
          <div class="field">
            <label for="rename-slug">Nuevo link</label>
            <div class="slug-box" :class="{ invalid: renameKind === 'err' || !!store.fieldErrors.slug }">
              <span class="slug-prefix">/tienda/</span>
              <input
                id="rename-slug"
                name="rename-slug"
                type="text"
                class="input slug-input"
                :value="renameSlug"
                :placeholder="store.store.slug"
                maxlength="60"
                autocomplete="off"
                @input="onRenameInput"
              />
            </div>
            <p class="hint">Al cambiarlo, el link anterior deja de funcionar.</p>
            <p v-if="store.fieldErrors.slug" class="field-error" role="alert">{{ store.fieldErrors.slug }}</p>
            <p v-else-if="renameMsg" class="slug-check" :class="renameKind" role="status">
              <AppIcon v-if="renameCheck === 'available'" name="circle-check" :size="14" />
              <span v-else-if="renameCheck === 'checking'" class="spinner spinner-brand" aria-hidden="true"></span>
              {{ renameMsg }}
            </p>
          </div>
          <button class="btn btn-auto" :disabled="!canRename" @click="saveRename">
            <span v-if="renameBusy" class="spinner" aria-hidden="true"></span>Guardar nuevo link
          </button>
        </div>

        <div class="card">
          <h3><AppIcon name="palette" :size="18" /> Diseño de tu web</h3>
          <p>Titular, descripción, colores y botones de contacto de tu página pública.</p>
          <AlertMessage v-if="!canCustomize" kind="info" message="La personalización de tu web está disponible en el Plan premium." />
          <div class="btn-row link-actions">
            <button class="btn btn-auto" @click="section = 'design'">
              <AppIcon :name="canCustomize ? 'pencil' : 'lock'" :size="16" /> {{ canCustomize ? 'Editar diseño' : 'Conocer el diseño web' }}
            </button>
          </div>
        </div>
      </template>
    </div>
    <!-- ================= DISEÑO WEB (premium) ================= -->
    <div v-show="section === 'design'">
      <div class="page-head">
        <div>
          <h1>Diseño web</h1>
          <p>Personalizá cómo se ve tu página pública. Los cambios se aplican en el momento.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
      </div>
      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <template v-if="canCustomize">
        <div class="grid-2">
          <div class="card">
            <h3><AppIcon name="pencil" :size="18" /> Contenido</h3>
            <AppInput v-model="designForm.headline" label="Titular" name="design_headline" placeholder="Ej. Indumentaria y calzado en Salta" hint="Frase corta bajo el nombre de tu negocio (opcional, hasta 140 caracteres)." :error="designFieldErr('headline')" @blur="designTouched.headline = true" />
            <div class="field">
              <label for="design-description">Descripción</label>
              <textarea
                id="design-description"
                v-model="designForm.description"
                class="textarea"
                :class="{ invalid: designFieldErr('description') }"
                placeholder="Contale a tus clientes qué ofrecés"
                maxlength="800"
                rows="4"
                @blur="designTouched.description = true"
              ></textarea>
              <p class="hint">Aparece debajo del titular. {{ designForm.description.length }}/800</p>
              <p v-if="designFieldErr('description')" class="field-error" role="alert">{{ designFieldErr('description') }}</p>
            </div>
            <AppInput v-model="designForm.whatsapp" label="WhatsApp de contacto" name="design_whatsapp" placeholder="+5493871551234" hint="Formato internacional. Genera un botón de chat en tu web." :error="designFieldErr('whatsapp')" @blur="designTouched.whatsapp = true" />
            <AppInput v-model="designForm.instagram" label="Instagram" name="design_instagram" placeholder="tu.negocio" hint="Solo el usuario, sin @. Genera un botón a tu perfil." :error="designFieldErr('instagram')" @blur="designTouched.instagram = true" />
          </div>
          <div class="card">
            <h3><AppIcon name="palette" :size="18" /> Apariencia</h3>
            <div class="field">
              <label id="design-theme-label">Tema</label>
              <div class="theme-options" role="radiogroup" aria-labelledby="design-theme-label">
                <button
                  v-for="(t, key) in storeThemes" :key="key" type="button"
                  class="theme-option" :class="{ active: designForm.theme === key }"
                  :aria-pressed="designForm.theme === key"
                  @click="designForm.theme = key"
                >
                  <span class="theme-thumb" :data-store-theme="key"></span>
                  {{ t.label }}
                </button>
              </div>
            </div>
            <div class="field">
              <label id="design-accent-label">Color de acento</label>
              <div class="swatches" role="radiogroup" aria-labelledby="design-accent-label">
                <button
                  v-for="(a, key) in storeAccents" :key="key" type="button"
                  class="swatch" :class="{ active: designForm.accent === key }"
                  :style="{ '--swatch': a.hex }"
                  :title="a.label" :aria-label="`Color ${a.label}`"
                  :aria-pressed="designForm.accent === key"
                  @click="designForm.accent = key"
                >
                  <AppIcon v-if="designForm.accent === key" name="check" :size="14" :stroke="2.5" />
                </button>
              </div>
              <p class="hint">Se aplica a la portada, los botones y los detalles de tu página.</p>
            </div>
          </div>
        </div>

        <div class="card">
          <h3><AppIcon name="eye" :size="18" /> Vista previa</h3>
          <div class="design-preview" :data-store-theme="designForm.theme" :style="designPreviewVars">
            <div class="dp-cover"></div>
            <div class="dp-body">
              <span class="dp-mono">{{ businessInitial }}</span>
              <strong class="dp-name">{{ business || 'Tu negocio' }}</strong>
              <span class="dp-headline">{{ designForm.headline || 'El titular de tu tienda' }}</span>
              <span v-if="designForm.description" class="dp-desc">{{ designForm.description }}</span>
              <div v-if="designForm.whatsapp || designForm.instagram" class="dp-cta">
                <span v-if="designForm.whatsapp" class="dp-btn">WhatsApp</span>
                <span v-if="designForm.instagram" class="dp-btn ghost">Instagram</span>
              </div>
            </div>
          </div>
          <AppButton :loading="designBusy" @click="saveDesign">Guardar diseño</AppButton>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
        <h3>La personalización es Premium</h3>
        <p>Con el Plan premium podés editar el titular, la descripción, los colores y los botones de contacto de tu página pública.</p>
        <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>
    </div>
    <!-- ================= ESTADÍSTICAS (premium) ================= -->
    <div v-show="section === 'stats'">
      <div class="page-head">
        <div>
          <h1>Estadísticas</h1>
          <p>Métricas de tu tienda y de tu link público.</p>
        </div>
      </div>
      <div class="empty">
        <span class="empty-icon"><AppIcon name="trending-up" :size="28" /></span>
        <h3>Las estadísticas llegan con el catálogo</h3>
        <p>Tu plan ya incluye estadísticas de visitas. Cuando el catálogo esté disponible vas a ver acá las visitas a tu link, los productos más vistos y la evolución por día.</p>
      </div>
    </div>
    <!-- ================= QR Y FOLLETOS (premium) ================= -->
    <div v-show="section === 'tools'">
      <div class="page-head">
        <div>
          <h1>QR y folletos</h1>
          <p>Herramientas de difusión para tu link público.</p>
        </div>
      </div>
      <div class="empty">
        <span class="empty-icon"><AppIcon name="qr-code" :size="28" /></span>
        <h3>Disponible con el catálogo</h3>
        <p>Tu plan ya incluye el código QR de tu tienda y folletos listos para imprimir. Se generan automáticamente cuando publiques tu primer catálogo.</p>
      </div>
    </div>
    <!-- ================= PLANES ================= -->
    <div v-show="section === 'plans'">
      <div class="page-head">
        <div>
          <h1>Planes</h1>
          <p>Elegí el plan que acompaña el tamaño de tu negocio. Podés cambiarlo cuando quieras.</p>
        </div>
      </div>
      <div class="price-grid">
        <PlanCard
          v-for="p in billing.plans"
          :key="p.id"
          :plan="p"
          :current="billing.hasSubscription && plan?.pk === p.id"
          :busy="busyPlan === p.id"
          @select="planAction"
        />
      </div>
    </div>
    <!-- ================= PAGOS ================= -->
    <div v-show="section === 'payments'">
      <div class="page-head">
        <div>
          <h1>Pagos</h1>
          <p>Historial de pagos de tu suscripción. Se acreditan solos cuando Mercado Pago los confirma.</p>
        </div>
        <button class="btn ghost btn-auto" @click="payments.loadPayments()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="payments.notice" kind="success" :message="payments.notice" />
      <AlertMessage v-if="payments.lastError" kind="error" :message="payments.lastError" />

      <div v-if="payments.status === 'loading'" class="card"><p>Cargando tus pagos…</p></div>
      <div v-else-if="payments.hasPayments" class="table-wrap">
        <table class="pay-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Plan</th>
              <th>Monto</th>
              <th>Estado</th>
              <th>Referencia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in payments.payments" :key="p.id">
              <td data-label="Fecha">{{ formatDateTime(p.paid_at || p.created_at) }}</td>
              <td data-label="Plan">{{ p.plan_name || '—' }}</td>
              <td class="amount" data-label="Monto">{{ formatARS(p.amount) }}</td>
              <td data-label="Estado"><span class="pill" :class="paymentStatusMeta(p.status).kind">{{ p.status_display || paymentStatusMeta(p.status).label }}</span></td>
              <td data-label="Referencia"><span class="mono">{{ p.external_reference || '—' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="receipt" :size="28" /></span>
        <h3>Todavía no hay pagos registrados</h3>
        <p>Cuando registres tu primer cobro de Mercado Pago, va a aparecer acá con su estado y referencia.</p>
      </div>

      <div v-if="payments.revenuesStatus === 'success'" class="grid-2 section-gap">
        <div class="card">
          <h3><AppIcon name="dashboard" :size="18" /> Ingresos por día</h3>
          <div v-if="payments.dailyRevenues.length" class="kv">
            <div v-for="r in payments.dailyRevenues.slice(0, 7)" :key="r.id">
              <span>{{ r.date }}</span>
              <strong>{{ formatARS(r.total_amount) }} · {{ r.payments_count }} pago(s)</strong>
            </div>
          </div>
          <p v-else>Sin datos todavía.</p>
        </div>
        <div class="card">
          <h3><AppIcon name="dashboard" :size="18" /> Ingresos por mes</h3>
          <div v-if="payments.monthlyRevenues.length" class="kv">
            <div v-for="r in payments.monthlyRevenues" :key="r.id">
              <span>{{ MONTH_NAMES[r.month] }} {{ r.year }}</span>
              <strong>{{ formatARS(r.total_amount) }} · {{ r.payments_count }} pago(s)</strong>
            </div>
          </div>
          <p v-else>Sin datos todavía.</p>
        </div>
      </div>
    </div>
    <!-- ================= FACTURAS ================= -->
    <div v-show="section === 'invoices'">
      <div class="page-head">
        <div>
          <h1>Facturas</h1>
          <p>Tus comprobantes emitidos por cada pago acreditado.</p>
        </div>
        <button class="btn ghost btn-auto" @click="invoices.loadInvoices()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="invoices.lastError" kind="error" :message="invoices.lastError" />

      <div v-if="invoices.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tus facturas…</p></div>
      <div v-else-if="invoices.hasInvoices" class="table-wrap">
        <table class="pay-table">
          <thead>
            <tr>
              <th>Comprobante</th>
              <th>Emisión</th>
              <th>Plan</th>
              <th>Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in invoices.invoices" :key="inv.id">
              <td data-label="Comprobante"><span class="mono">{{ inv.type_display }} · {{ inv.comprobante }}</span></td>
              <td data-label="Emisión">{{ formatInvDate(inv.issued_at) }}</td>
              <td data-label="Plan">{{ inv.plan_name || '—' }}</td>
              <td class="amount" data-label="Total">{{ formatARS(inv.total) }}</td>
              <td data-label="Acciones">
                <button class="btn ghost btn-auto" type="button" @click="openInvoice(inv.id)">
                  <AppIcon name="printer" :size="16" /> Ver / imprimir
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="file-text" :size="28" /></span>
        <h3>Todavía no tenés facturas</h3>
        <p>Cuando se acredite un pago de tu suscripción, el comprobante se emite solo y aparece acá, listo para imprimir o guardar como PDF.</p>
        <button class="btn btn-auto" @click="section = 'payments'">Ver mis pagos</button>
      </div>
    </div>
    <!-- ================= CUENTA ================= -->
    <div v-show="section === 'settings'">
      <div class="page-head">
        <div>
          <h1>Cuenta</h1>
          <p>Tus datos comerciales y de acceso.</p>
        </div>
        <button class="btn ghost btn-auto" @click="reloadAccount"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>
      <div class="grid-2">
        <div class="card">
          <h3><AppIcon name="user" :size="18" /> Tu perfil</h3>
          <p>Actualizá tu correo de acceso y tus datos fiscales. Usamos estos datos para tu facturación.</p>
          <AlertMessage v-if="accountMsg" kind="success" :message="accountMsg" />
          <AlertMessage v-if="accountErr" kind="error" :message="accountErr" />
          <AlertMessage v-if="geoNotice" kind="warn" :message="geoNotice" />
          <AlertMessage v-if="geoErr" kind="error" :message="geoErr" />
          <form class="form-top" @submit.prevent="saveAccount" novalidate>
            <AppInput v-model="accountForm.email" label="Correo electrónico" name="acc_email" type="email" autocomplete="email" placeholder="Ej. alfredito2026@outlook.com" hint="Solo: gmail, hotmail, outlook, yahoo, live." required :error="accountFieldErr('email')" @blur="accountTouched.email = true" />
            <div class="grid-2">
              <AppInput v-model="accountForm.first_name" label="Nombre" name="acc_first_name" autocomplete="given-name" placeholder="Escribe tu nombre" required :error="accountFieldErr('first_name')" @blur="accountTouched.first_name = true" />
              <AppInput v-model="accountForm.last_name" label="Apellido/s" name="acc_last_name" autocomplete="family-name" placeholder="Escribe tu/s apellido/s" required :error="accountFieldErr('last_name')" @blur="accountTouched.last_name = true" />
            </div>
            <div class="field">
              <label for="acc_tax_condition">Condición fiscal *</label>
              <select id="acc_tax_condition" v-model="accountForm.tax_condition" class="select">
                <option v-for="t in TAX_CONDITIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
              <p class="hint">Tipo de documento automático: {{ docKind }} (CF → DNI, resto → CUIT).</p>
            </div>
            <AppInput v-model="accountForm.business_name" label="Nombre de negocio" name="acc_business_name" placeholder="Escribe tu nombre de negocio" :hint="accountForm.tax_condition === 'CF' ? 'Opcional únicamente para consumidor final.' : 'Obligatorio para tu condición fiscal.'" :error="accountFieldErr('business_name')" @blur="accountTouched.business_name = true" />
            <AppInput v-model="accountForm.document" label="Documento" name="acc_document" placeholder="Escribe tu número de identificación" :hint="docHint" required :error="accountFieldErr('document')" @blur="accountTouched.document = true" />
            <div class="grid-2">
              <div class="field">
                <label for="acc_province">Provincia *</label>
                <select id="acc_province" v-model="accountForm.province" class="select" :class="{ invalid: accountFieldErr('province') }" @change="onAccountProvinceChange">
                  <option value="">Seleccionar…</option>
                  <option v-for="p in provinces" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
                <p v-if="accountFieldErr('province')" class="field-error">{{ accountFieldErr('province') }}</p>
              </div>
              <div class="field">
                <label for="acc_city">Ciudad *</label>
                <select id="acc_city" v-model="accountForm.city" class="select" :class="{ invalid: accountFieldErr('city') }" :disabled="!accountForm.province">
                  <option value="">{{ accountForm.province ? 'Seleccionar…' : 'Primero elegí provincia' }}</option>
                  <option v-for="c in cities" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
                <p v-if="accountFieldErr('city')" class="field-error">{{ accountFieldErr('city') }}</p>
              </div>
            </div>
            <AppInput v-model="accountForm.address" label="Domicilio" name="acc_address" autocomplete="street-address" placeholder="Escribe tu domicilio" :error="accountFieldErr('address')" @blur="accountTouched.address = true" />
            <AppInput v-model="accountForm.phone" label="Número de celular" name="acc_phone" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" :error="accountFieldErr('phone')" @blur="accountTouched.phone = true" />
            <AppButton :loading="accountBusy">Guardar cambios</AppButton>
          </form>
        </div>
        <div class="card">
          <h3><AppIcon name="key" :size="18" /> Cambiar contraseña</h3>
          <AlertMessage v-if="passMsg" kind="success" :message="passMsg" />
          <AlertMessage v-if="passErr" kind="error" :message="passErr" />
          <form @submit.prevent="changePassword" novalidate>
            <AppInput v-model="passForm.old_password" label="Actual" name="old_password" type="password" autocomplete="current-password" :error="touched.old_password && !passForm.old_password ? 'Obligatorio' : ''" @blur="touched.old_password = true" />
            <AppInput v-model="passForm.new_password" label="Nueva" name="new_password" type="password" autocomplete="new-password" :error="touched.new_password ? (validatePassword(passForm.new_password) || '') : ''" @blur="touched.new_password = true" />
            <PasswordStrength :value="passForm.new_password" />
            <AppInput v-model="passForm.confirm_password" label="Confirmar" name="confirm_password" type="password" autocomplete="new-password" @blur="touched.confirm_password = true" />
            <AppButton :loading="auth.status === 'loading'">Actualizar</AppButton>
          </form>
        </div>
      </div>
    </div>
  </DashLayout>
</template>
