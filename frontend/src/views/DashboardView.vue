<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useBillingStore } from '../stores/billing.store.js'
import { usePaymentsStore } from '../stores/payments.store.js'
import { useInvoicesStore } from '../stores/invoices.store.js'
import { useStoreStore } from '../stores/store.store.js'
import { useCatalogStore } from '../stores/catalog.store.js'
import { useServicesStore } from '../stores/services.store.js'
import { useThemeStore } from '../stores/theme.store.js'
import { useSlugCheck } from '../composables/useSlugCheck.js'
import {
  normalizeSlug, publicStoreUrl, storesApi,
  CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  allowedTemplatesFor, resolveStoreTemplate,
  SITE_TEMPLATE_KEYS, SITE_TEMPLATES, DEFAULT_SITE_TEMPLATES,
  siteTemplatesLimit, allowedSiteTemplatesFor, normalizeSiteTemplates, resolveSiteTemplates,
  ensureStoreFont, ensureStoreFontPicker,
  validateDisplayName, validateHeadline, validateDescription,
  validateAboutTitle, validateAboutText, validateAboutYears, validateAboutMission, validateAboutSpecialties,
  validateContactEmail,
  validateWhatsapp, validateInstagram, validateTiktok, validateFacebook,
  validateImageFile, validateLogoFile, LOGO_ACCEPT, CAROUSEL_MAX_IMAGES, DECOR_MAX_IMAGES,
  CHATBOT_DEFAULTS, CHATBOT_QA_MAX,
  MARKETING_LIMITS, SERVICE_ICONS, serviceHue,
  validateSectionTitle, validateCtaTitle, validateCtaText, validateCtaLabel, validateVideoUrl
} from '../api/stores.api.js'
import {
  validateTaxonomyName, validateProductName, validateProductPrice, validateProductDescription,
  catalogApi, FEATURE_LIMITS, parseFeatureSchema, validateFeatureSchema, validateProductFeatures,
  DISCOUNT_SCOPES, discountStatusMeta, discountScopeLabel, discountWindowLabel,
  validateDiscountName, validateDiscountPercent, validateDiscountWindow,
  isoToLocalInput, localInputToIso, productListOffer, isDiscountedProduct
} from '../api/catalog.api.js'
import {
  SERVICE_LIMITS, SERVICE_PAGE_LIMITS, servicePriceLabel, servicePayload,
  validateServiceName, validateServiceDescription, validateServicePrice, validateServiceDuration
} from '../api/services.api.js'
import { formatARS } from '../api/billing.api.js'
import { formatDate as formatInvDate } from '../api/invoices.api.js'
import { paymentStatusMeta, formatDateTime, MONTH_NAMES } from '../api/payments.api.js'
import { locationsApi } from '../api/locations.api.js'
import { authApi } from '../api/auth.api.js'
import { fetchChat, fetchChatMessages, sendChatMessage, chatHeartbeat } from '../api/chat.api.js'
import { extractApiError } from '../api/http.js'
import { env, storeSubdomains } from '../config/env.js'
import {
  TAX_CONDITIONS, validatePassword, validateEmail, validateName,
  validateDocument, validateBusinessName, validatePhone, validateAddress,
  documentKindFor
} from '../validators/auth.validators.js'
import DashLayout from '../components/DashLayout.vue'
import PlanCard from '../components/PlanCard.vue'
import SectionTabs from '../components/SectionTabs.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PasswordStrength from '../components/PasswordStrength.vue'
import StorageMeter from '../components/StorageMeter.vue'
import AppIcon from '../components/AppIcon.vue'
import IconSelect from '../components/IconSelect.vue'
import CountUp from '../components/CountUp.vue'
import FlyerStudio from '../components/FlyerStudio.vue'
import ChatDock from '../components/ChatDock.vue'
import GlobalSearch from '../components/GlobalSearch.vue'
import TourGuide from '../components/TourGuide.vue'
import TipHint from '../components/TipHint.vue'
import DesignPreview from '../components/design/DesignPreview.vue'
import DesignStylesTab from '../components/design/DesignStylesTab.vue'
import AiDesignView from './design/AiDesignView.vue'
import { useStudioDesign, DESIGN_FIELDS } from '../composables/useStudioDesign.js'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const billing = useBillingStore()
const payments = usePaymentsStore()
const invoices = useInvoicesStore()
const store = useStoreStore()
const catalog = useCatalogStore()
const services = useServicesStore()
const theme = useThemeStore()

// Sección activa con setter validado: un botón interno (o una sección que
// desaparece del menú cuando vence el plan) jamás deja una vista vacía.
const sectionInner = ref('overview')
const section = computed({
  get: () => sectionInner.value,
  set: (id) => {
    // Las secciones bloqueadas no navegan: abren la vista previa del
    // beneficio (también los `section = 'x'` internos pasan por acá).
    if (navLocks.value?.[id]) { openLocked(id); return }
    const next = validIds.value.has(id) ? id : 'overview'
    if (sectionInner.value === 'design' && next !== 'design' && designDirtyAll.value) {
      leaveGuard.target = next
      leaveGuard.open = true
      return
    }
    sectionInner.value = next
  }
})
const busyPlan = ref(null)
const couponCode = ref('')
const couponBusy = ref(false)
const renewBusy = ref(false)
const confirmCancel = ref(false)
const passForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const touched = reactive({})
const passMsg = ref('')
const passErr = ref('')

// --- Verificación de email (anti-abuso trial: bloquea el claim de la web) ---
const verifyBusy = ref(false)
const verifyMsg = ref('')
const verifyErr = ref('')
// Solo perfiles comerciales sin verificar; el staff no tiene profile.
const needsEmailVerification = computed(() => {
  const p = auth.user?.profile
  return Boolean(p) && p.email_verified === false
})
async function resendVerification() {
  verifyBusy.value = true
  verifyMsg.value = ''
  verifyErr.value = ''
  try {
    const data = await authApi.resendVerificationEmail()
    verifyMsg.value = data?.Exito || 'Te reenviamos el correo de verificación.'
  } catch (e) {
    verifyErr.value = e.response?.status === 429
      ? 'Ya pediste varios reenvíos. Esperá un rato y revisá también el spam.'
      : 'No se pudo reenviar el correo. Reintentá en unos minutos.'
  } finally {
    verifyBusy.value = false
  }
}

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
      pushToast('Tus datos quedaron guardados ✓')
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

// Plan vigente: declarado antes de navItems porque su watcher evalúa el
// computed apenas se registra (TDZ si queda debajo).
const plan = computed(() => billing.currentPlan)

// Apartados agrupados (pestañas dentro de una misma sección): la navegación
// apunta al primer apartado y las pestañas viven adentro.
const tabGroups = computed(() => {
  const b = plan.value?.benefits || {}
  const hasAccess = Boolean(plan.value?.isCurrent)
  const web = [{ id: 'store', label: 'Mi dirección web', icon: 'share-2', hint: 'Link para compartir' }]
  if (hasAccess && b.has_customization) {
    web.push(
      { id: 'design', label: 'Diseño', icon: 'palette', hint: 'Estilos, Studio e IA' },
      { id: 'pages', label: 'Plantillas', icon: 'layout-grid', hint: 'Qué páginas tiene tu web' },
      { id: 'company', label: 'Sobre mi negocio', icon: 'building-2', hint: 'Servicios, horarios y más' }
    )
  }
  const promo = [
    { id: 'tools', label: 'QR y folletos', icon: 'qr-code', hint: 'Para imprimir y repartir' },
    { id: 'stats', label: 'Mis visitas', icon: 'trending-up', hint: 'Cuánta gente te mira' }
  ]
  const billingTabs = [
    { id: 'plans', label: 'Mi plan', icon: 'crown', hint: 'Elegir o cambiar plan' },
    { id: 'payments', label: 'Pagos', icon: 'receipt', hint: 'Lo que pagaste' },
    { id: 'invoices', label: 'Facturas', icon: 'file-text', hint: 'Tus comprobantes' }
  ]
  return { web, promo, billing: billingTabs }
})

// Qué secciones se bloquean por plan y con qué copy abre el candado
// (vista previa del beneficio: 'expired' = suscripción vencida, 'upgrade' =
// falta el beneficio en el plan actual).
const SECTION_BENEFITS = {
  design_assisted: ['has_ai_design'],
  design_studio: ['has_design_advanced'],
  design_ai: ['has_ai_chat'],
  services: ['has_services_site'],
  reviews: ['has_product_comments'],
  support: ['has_support_chat'],
  bot: ['has_chatbot'],
  stats: ['has_stats'],
  tools: ['has_qr', 'has_flyers']
}
const LOCKED_FEATURES = {
  design_assisted: { icon: 'sparkles', title: 'Diseño asistido', text: 'Contale a qué te dedicás y recibí tu web armada: plantilla, orden de secciones y textos. Después la ajustás a mano.' },
  design_studio: { icon: 'layout-panel-left', title: 'Studio de diseño', text: 'El editor completo con vista previa en vivo: colores, tipografía, contenedores, portada y versión de prueba antes de publicar.' },
  design_ai: { icon: 'bot', title: 'Diseñar con IA', text: 'Un chat donde describís tu web ideal y la IA la configura por vos. Revisás la propuesta y la aplicás cuando te gusta.' },
  catalogs: { icon: 'package', title: 'Tu catálogo de productos', text: 'Cargá productos con foto, precio y categorías: se publican solos en tu web.' },
  services: { icon: 'wrench', title: 'Página de servicios', text: 'Una página propia para mostrar lo que hacés, con duración, precio y botón de consulta directa a tu WhatsApp.' },
  pos: { icon: 'monitor', title: 'Venta en persona', text: 'Cobrá en tu local usando el mismo catálogo de tu web. Llega muy pronto.' },
  reviews: { icon: 'star', title: 'Opiniones de clientes', text: 'Tus clientes valoran tus productos y dejan comentarios que se muestran en tu web; vos decidís qué se ve.' },
  support: { icon: 'message-circle', title: 'Asistente de diseño', text: 'Un asistente te hace preguntas sobre tu negocio y te recomienda el estilo ideal para tu web.' },
  bot: { icon: 'bot', title: 'Asistente virtual', text: 'Un ayudante en tu web que responde solo las preguntas frecuentes de tus clientes, las 24 horas.' },
  tools: { icon: 'qr-code', title: 'QR y folletos', text: 'Código QR y folletos listos para imprimir y repartir: del papel a tu web en un escaneo.' },
  stats: { icon: 'trending-up', title: 'Estadísticas de visitas', text: 'Cuánta gente entra a tu web día por día durante el último mes.' }
}

// Por sección: null = accesible, 'expired' = plan vencido, 'upgrade' = falta
// el beneficio. Los ítems bloqueados se muestran igual (con candado) para
// que el usuario descubra lo que el plan superior le habilita.
const navLocks = computed(() => {
  const b = plan.value?.benefits || {}
  const hasAccess = Boolean(plan.value?.isCurrent)
  const map = {}
  const gated = (id) => (SECTION_BENEFITS[id] || []).some((k) => !b[k])
  for (const id of ['catalogs', 'services', 'pos', 'reviews', 'support', 'bot', 'tools', 'stats']) {
    map[id] = !hasAccess ? 'expired' : gated(id) ? 'upgrade' : null
  }
  return map
})

// Menú por intención: lo que el dueño quiere hacer, no el módulo técnico.
const navItems = computed(() => {
  const L = navLocks.value
  return [
    { id: 'overview', label: 'Inicio', icon: 'dashboard', hint: 'Tu negocio hoy' },
    { heading: 'Vender' },
    { id: 'catalogs', label: 'Mis productos', icon: 'package', hint: 'Fotos, precios y categorías', locked: L.catalogs },
    { id: 'services', label: 'Mis servicios', icon: 'wrench', hint: 'Lo que ofrecés hacer', locked: L.services },
    { id: 'pos', label: 'Vender en persona', icon: 'monitor', hint: 'Cobrar en tu local', locked: L.pos },
    { heading: 'Mi web' },
    { id: 'store', label: 'Mi página', icon: 'store', hint: 'Diseño, secciones y dirección' },
    { heading: 'Clientes' },
    { id: 'reviews', label: 'Opiniones', icon: 'star', hint: 'Lo que dicen de vos', locked: L.reviews },
    { id: 'support', label: 'Asistente de diseño', icon: 'message-circle', hint: 'Te ayuda a armar tu web', locked: L.support },
    { id: 'bot', label: 'Asistente virtual', icon: 'bot', hint: 'Responde por vos en tu web', locked: L.bot },
    { heading: 'Crecer' },
    { id: 'tools', label: 'Promocionar', icon: 'megaphone', hint: 'QR y folletos para imprimir', locked: L.tools },
    { id: 'stats', label: 'Mis visitas', icon: 'trending-up', hint: 'Quién entra a tu página', locked: L.stats },
    { heading: 'Mi cuenta' },
    { id: 'plans', label: 'Plan y pagos', icon: 'credit-card', hint: 'Suscripción, pagos y facturas' },
    { id: 'settings', label: 'Mis datos', icon: 'user', hint: 'Cuenta y contraseña' }
  ]
})

const validIds = computed(() => {
  const ids = new Set(navItems.value.filter((i) => i.id).map((i) => i.id))
  Object.values(tabGroups.value).forEach((tabs) => tabs.forEach((t) => ids.add(t.id)))
  return ids
})

// Entrada del menú que corresponde a la sección actual (las pestañas comparten una).
const navActive = computed(() => {
  const ids = new Set(navItems.value.filter((i) => i.id).map((i) => i.id))
  if (ids.has(section.value)) return section.value
  for (const tabs of Object.values(tabGroups.value)) {
    if (tabs.some((t) => t.id === section.value)) return tabs[0].id
  }
  return section.value
})

// Título de la sección actual (incluye apartados sin entrada propia en el
// menú) y su sección padre para el botón "volver" y la miga de pan.
const sectionTitle = computed(() => {
  const hit = navItems.value.find((i) => i.id === section.value)
  if (hit) return hit.label
  for (const tabs of Object.values(tabGroups.value)) {
    const t = tabs.find((t) => t.id === section.value)
    if (t) return t.label
  }
  return 'Inicio'
})
const navParent = computed(() => {
  for (const tabs of Object.values(tabGroups.value)) {
    const idx = tabs.findIndex((t) => t.id === section.value)
    if (idx > 0) return { id: tabs[0].id, label: tabs[0].label }
    if (idx === 0) return null
  }
  return null
})

// Plan más barato que incluye alguno de los beneficios pedidos (para el
// "Disponible en {plan}" del candado).
function minPlanFor(keys) {
  const list = Array.isArray(keys) ? keys : [keys]
  const cands = billing.plans.filter((p) => !p.is_trial && list.some((k) => p.benefits?.[k]))
  cands.sort((a, b) => Number(a.price) - Number(b.price))
  return cands[0]?.name || null
}
const lockedFeature = ref(null)
function openLocked(id) {
  const meta = LOCKED_FEATURES[id] || { icon: 'lock', title: 'Función bloqueada', text: '' }
  const reason = navLocks.value[id] || 'upgrade'
  const planName = reason === 'upgrade' ? minPlanFor(SECTION_BENEFITS[id] || []) : null
  lockedFeature.value = { id, reason, planName, ...meta }
}
function onLockedNav(item) { openLocked(item.id) }
function goPlansFromLocked() {
  lockedFeature.value = null
  sectionInner.value = 'plans'
}

// Si la sección activa desaparece o se bloquea (venció el plan), volver a Inicio.
watch(validIds, (ids) => {
  if (!ids.has(section.value)) sectionInner.value = 'overview'
})
watch(navLocks, (locks) => {
  if (locks[section.value]) sectionInner.value = 'overview'
})

function onNavigate(id) {
  section.value = id
}

// --- Búsqueda global (⌘K / Ctrl+K), tour de primera vez y toast ----------
const searchOpen = ref(false)
const tourOpen = ref(false)

// Toast "Guardado ✓": feedback optimista flotante; con deshacer donde la
// acción es reversible (toggles, pausa de la web).
const toast = ref(null)
let toastTimer = null
function pushToast(msg, undo) {
  clearTimeout(toastTimer)
  toast.value = { msg, undo: undo || null }
  toastTimer = setTimeout(() => { toast.value = null }, 4200)
}
function closeToast() { clearTimeout(toastTimer); toast.value = null }
function focusField(id) { document.getElementById(id)?.focus() }

// Comandos buscables: secciones (con sinónimos de lenguaje cotidiano) +
// acciones frecuentes. Cada comando corre una función al elegirse.
const searchCommands = computed(() => {
  const cmds = []
  const go = (id) => () => { section.value = id }
  const KW = {
    overview: 'inicio resumen home panel hoy comienzo',
    catalogs: 'productos catalogo cargar subir precio foto stock mercaderia categoria marca articulo cosa vender',
    services: 'servicios trabajos ofrezco duracion turnos profesional',
    pos: 'vender persona local fisico cobrar caja punto venta mostrador ticket',
    store: 'pagina web tienda diseno link direccion url dominio slug logo colores plantilla publicar pausar editar',
    reviews: 'opiniones comentarios valoraciones estrellas clientes review reputacion',
    support: 'ayuda soporte chat mensaje consulta hablar equipo problema duda',
    bot: 'asistente chatbot automatico responder preguntas robot virtual',
    tools: 'qr codigo folleto volante imprimir promocionar vidriera flyer repartir',
    stats: 'estadisticas visitas metricas cuanta gente analytics numeros',
    plans: 'plan suscripcion pagos facturas comprobantes precio renovar debito automatico mercado pago cupon descuento vencimiento abonar',
    settings: 'cuenta datos contrasena email correo perfil fiscal cuit dni provincia ciudad celular nombre apellido seguridad'
  }
  for (const i of navItems.value.filter((x) => x.id)) {
    cmds.push({ id: i.id, label: i.label, hint: i.hint || '', icon: i.icon, kw: KW[i.id] || '', locked: i.locked, run: go(i.id), group: 'Secciones' })
  }
  if (store.hasStore) {
    cmds.push({ id: 'copy-link', label: 'Copiar mi link', hint: 'La dirección de tu web, lista para pegar', icon: 'copy', kw: 'copiar link url direccion compartir pegar', run: () => copyLink(), group: 'Acciones' })
    cmds.push({ id: 'open-store', label: 'Ver mi página', hint: 'Abrirla como la ven tus clientes', icon: 'external-link', kw: 'ver tienda pagina publica preview abrir mirar', run: () => openStore(), group: 'Acciones' })
    cmds.push({ id: 'share-wa', label: 'Compartir por WhatsApp', hint: 'Mandá tu link a tus contactos', icon: 'phone', kw: 'whatsapp compartir enviar link clientes mensaje', run: () => shareWhatsApp(), group: 'Acciones' })
  }
  cmds.push({ id: 'new-product', label: 'Cargar un producto', hint: 'Foto, precio y categoría', icon: 'plus', kw: 'nuevo producto agregar cargar subir crear', run: go('catalogs'), group: 'Acciones', locked: navLocks.value.catalogs })
  cmds.push({ id: 'change-logo', label: 'Cambiar mi logo', hint: 'En Diseño → Logo y colores', icon: 'image', kw: 'logo cambiar subir imagen marca foto perfil', run: go('design'), group: 'Acciones', locked: navLocks.value.catalogs })
  cmds.push({ id: 'theme', label: theme.isDark ? 'Modo claro' : 'Modo oscuro', hint: 'Cambiar la apariencia del panel', icon: theme.isDark ? 'sun' : 'moon', kw: 'tema oscuro claro modo nocturno dark light apariencia color', run: () => theme.toggleTheme(), group: 'Acciones' })
  cmds.push({ id: 'coupon', label: 'Canjear un cupón', hint: 'Código promocional o de regalo', icon: 'gift', kw: 'cupon codigo promo promocional descuento regalo canjear', run: go('plans'), group: 'Acciones' })
  cmds.push({ id: 'password', label: 'Cambiar contraseña', hint: 'Seguridad de tu cuenta', icon: 'key', kw: 'contrasena password clave seguridad cambiar', run: go('settings'), group: 'Acciones' })
  cmds.push({ id: 'messages', label: 'Mensajes de soporte', hint: 'Abrir la conversación con el equipo', icon: 'message-circle', kw: 'mensajes chat soporte hablar conversacion inbox', run: () => onBellClick(), group: 'Acciones' })
  return cmds
})

// Los 4 destinos del pulgar + "Más" (el quinto tab lo dibuja el layout).
const mobileTabs = computed(() => [
  { id: 'overview', label: 'Inicio', icon: 'dashboard' },
  { id: 'catalogs', label: 'Vender', icon: 'package' },
  { id: 'store', label: 'Mi web', icon: 'store' },
  { id: 'chat', label: 'Mensajes', icon: 'message-circle', badge: chatUnread.value }
])

function shareWhatsApp() {
  if (!publicUrl.value) return
  const text = `Mirá mi tienda online: ${publicUrl.value}`
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener')
}
const business = computed(() => auth.user?.profile?.business_name || '')

// Render diferido: cada sección se monta recién la primera vez que se visita
// (después queda montada con v-show, así conserva estado y no re-renderiza).
const seen = reactive({ overview: true })
watch(section, (s) => { seen[s] = true }, { flush: 'sync', immediate: true })

const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 6 ? 'Buenas noches' : h < 13 ? 'Buen día' : h < 20 ? 'Buenas tardes' : 'Buenas noches'
})
const RING_R = 44
const RING_C = 2 * Math.PI * RING_R
const ringOffset = computed(() => RING_C * (1 - planProgress.value / 100))
// Gracia del débito: venció end_date pero el débito automático sigue reintentando.
const inGrace = computed(() => {
  const p = plan.value
  return Boolean(p?.isCurrent && p.autoRenew && p.end && new Date(p.end).getTime() < Date.now())
})
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
  { title: 'Reservá tu link público', text: 'Es la dirección de tu tienda, gratis.', done: store.hasStore, target: 'store', cta: 'Reservar mi link' },
  { title: 'Elegí un plan', text: 'Definí el tamaño de tu catálogo.', done: billing.hasSubscription, target: 'plans', cta: 'Elegir plan' },
  { title: 'Cargá tus productos', text: 'Sumá fotos, precios y descripciones.', done: catalog.products.length > 0, target: 'catalogs', cta: 'Cargar producto' },
  { title: 'Compartí tu link público', text: 'Mandáselo a tus clientes por WhatsApp.', done: false, target: 'store', cta: 'Copiar mi link', run: copyLink }
])
const stepsDone = computed(() => nextSteps.value.filter((s) => s.done).length)
const stepsPct = computed(() => Math.round((stepsDone.value / nextSteps.value.length) * 100))
const nextStepIdx = computed(() => nextSteps.value.findIndex((s) => !s.done))
const nextStep = computed(() => (nextStepIdx.value >= 0 ? nextSteps.value[nextStepIdx.value] : null))
const pendingSteps = computed(() => nextSteps.value.filter((s) => !s.done))

// Primera vez en el panel (todavía sin link público): la portada se arma
// como bienvenida guiada — tres pasos, un solo CTA — y esconde los paneles
// que aún no tienen datos (números en cero y actividad vacía).
const firstRun = computed(() => !store.hasStore)
const welcomeSteps = computed(() => nextSteps.value.slice(0, 3))

// --- "Tu negocio hoy": alertas, números con contexto y actividad -----------

// Cola de alertas priorizada: una sola franja visible, el resto se despliega
// con "N más". Orden = urgencia para el dueño del negocio.
const alertsOpen = ref(false)
const alertQueue = computed(() => {
  const list = []
  const go = (id) => () => { section.value = id }
  if (!billing.hasSubscription && billing.status !== 'loading') list.push({ id: 'nosub', kind: 'brand', title: 'Elegí tu plan para empezar a vender', text: 'En un minuto montás tu catálogo y lo compartís con tus clientes.', cta: 'Ver planes', run: go('plans') })
  if (plan.value && !plan.value.isCurrent && plan.value.status !== 'Pendiente de pago') list.push({ id: 'expired', kind: 'danger', title: 'Tu suscripción venció', text: 'Tu web pública está pausada. Renová el plan para reactivarla al instante.', cta: 'Renovar', run: go('plans') })
  else if (inGrace.value) list.push({ id: 'grace', kind: 'warn', title: 'Estamos reintentando el débito', text: 'Mercado Pago reintenta la renovación durante unos días; tu plan sigue activo mientras tanto.', cta: 'Ver mi plan', run: go('plans') })
  if (plan.value?.isCurrent && !plan.value.autoRenew && plan.value.remaining !== null && plan.value.remaining <= 5) list.push({ id: 'expiring', kind: 'warn', title: `Tu plan vence en ${plan.value.remaining} ${plan.value.remaining === 1 ? 'día' : 'días'}`, text: 'Renová antes del vencimiento para no perder tu web ni tu catálogo.', cta: 'Renovar', run: go('plans') })
  if (billing.subscription?.pending_plan_name) list.push({ id: 'pending', kind: 'info', title: `Cambio a ${billing.subscription.pending_plan_name} pendiente`, text: 'Se aplica solo cuando se acredite el pago.', cta: 'Ver pagos', run: go('payments') })
  if (storagePct.value >= 80) list.push({ id: 'storage', kind: 'warn', title: `Almacenamiento al ${storagePct.value}%`, text: 'Te estás quedando sin espacio para imágenes: borrá fotos viejas o ampliá el plan.', cta: 'Revisar', run: go('design') })
  if (chatUnread.value) list.push({ id: 'chat', kind: 'info', title: chatUnread.value === 1 ? 'Tenés un mensaje sin leer' : `Tenés ${chatUnread.value} mensajes sin leer`, text: 'El equipo de soporte te respondió.', cta: 'Responder', run: onBellClick })
  return list
})
const topAlert = computed(() => alertQueue.value[0] || null)
const extraAlerts = computed(() => alertQueue.value.slice(1))
const alertIcon = (kind) => ({ danger: 'circle-alert', warn: 'triangle-alert', info: 'info' }[kind] || 'bell')

// Visitas con contexto: semana actual vs. anterior + sparkline SVG de 30 días.
const visitWeek = computed(() => {
  const days = store.visitStats?.days || []
  const now = days.slice(-7).reduce((a, d) => a + d.count, 0)
  const prev = days.slice(-14, -7).reduce((a, d) => a + d.count, 0)
  const delta = prev > 0 ? Math.round(((now - prev) / prev) * 100) : now > 0 ? 100 : null
  return { now, prev, delta }
})
const yesterdayVisits = computed(() => store.visitStats?.days?.slice(-2, -1)[0]?.count ?? 0)
const sparkline = computed(() => {
  const days = store.visitStats?.days || []
  if (!days.length) return null
  const max = Math.max(1, ...days.map((d) => d.count))
  const step = days.length > 1 ? 100 / (days.length - 1) : 0
  const pts = days.map((d, i) => `${(i * step).toFixed(1)},${(26 - (d.count / max) * 22).toFixed(1)}`)
  return { line: pts.join(' '), area: `0,28 ${pts.join(' ')} 100,28` }
})
const storagePct = computed(() => {
  const s = store.storage
  if (!s?.max_mb) return 0
  return Math.min(100, Math.round((s.used_bytes / (s.max_mb * 1024 * 1024)) * 100))
})

// Feed "Actividad reciente": cada entrada es accionable.
const activityFeed = computed(() => {
  const items = []
  if (chatUnread.value) items.push({ icon: 'message-circle', title: chatUnread.value === 1 ? 'Un mensaje nuevo de soporte' : `${chatUnread.value} mensajes nuevos de soporte`, text: 'Abrí la conversación para responder.', cta: 'Responder', run: onBellClick })
  const rev = catalog.reviews[0]
  if (rev) items.push({ icon: rev.is_positive ? 'thumbs-up' : 'thumbs-down', title: `${rev.is_positive ? 'Opinión positiva' : 'Opinión'} de ${[rev.name, rev.surname].filter(Boolean).join(' ') || 'un cliente'}`, text: rev.text ? `“${rev.text.slice(0, 90)}${rev.text.length > 90 ? '…' : ''}”` : rev.product_name ? `Sobre ${rev.product_name}` : '', cta: 'Ver', run: () => { section.value = 'reviews' } })
  const days = store.visitStats?.days || []
  const peak = days.reduce((m, d) => (d.count > (m?.count ?? -1) ? d : m), null)
  if (peak?.count) items.push({ icon: 'trending-up', title: `Tu mejor día: ${peak.count} ${peak.count === 1 ? 'visita' : 'visitas'}`, text: `Fue el ${fmtDate(peak.date)}.`, cta: 'Ver visitas', run: () => { section.value = 'stats' } })
  const last = payments.payments[0]
  if (last) items.push({ icon: 'receipt', title: 'Último pago registrado', text: `${formatARS(last.amount)} · ${formatDateTime(last.paid_at || last.created_at)}`, cta: 'Ver pagos', run: () => { section.value = 'payments' } })
  return items.slice(0, 4)
})

// Vista previa viva de la web (mock con los datos reales: más liviana que un
// iframe de la página entera — la CSP ya permite embeberla same-site y el
// editor de Bloques lo hace; acá basta el resumen).
const ovPreviewVars = computed(() => storeThemeVars(store.customization))
const ovShopName = computed(() => store.customization?.display_name || business.value || 'Tu negocio')
const ovCatalogOn = computed(() => store.customization?.show_catalog !== false)
const ovCover = computed(() => store.customization?.cover || '')

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// --- Mi tienda: link público (copiar, abrir, pausar, renombrar) ---
const platformHost = env.platformHost
const scheme = `${window.location.protocol}//`
// Sin wildcard (Render test) el link es path: https://host/[slug]; con dominio
// propio el slug va de subdominio: https://[slug].host
const slugPrefix = storeSubdomains ? scheme : `${scheme}${platformHost}/`
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
    pushToast('Tu link cambió ✓')
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

// Vista previa del diseño activo: la URL pública real de la tienda (el
// diseño elegido es el que se ve publicado).
const previewUrl = computed(() => publicUrl.value || '')
function openPreview() {
  if (previewUrl.value) window.open(previewUrl.value, '_blank', 'noopener')
}

async function togglePublished() {
  if (!store.store || storeBusy.value) return
  storeBusy.value = true
  const ok = await store.update({ is_published: !store.store.is_published })
  storeBusy.value = false
  if (ok) {
    const paused = !store.store.is_published
    pushToast(paused ? 'Tu web está pausada: tus clientes no la ven' : 'Tu web volvió a estar publicada',
      async () => { await store.update({ is_published: !store.store.is_published }) })
  }
}

// --- Mis catálogos: productos, categorías y marcas de la tienda ---
// El catálogo se habilita con suscripción activa (el backend devuelve 403 sin plan).
const catalogTab = ref('products') // products | categories | brands | discounts
const catalogLoaded = ref(false)

// El interruptor del catálogo público (customization.show_catalog) y el
// carrusel de portada viven en esta misma sección, en la tarjeta "Tu
// página de catálogo": el dueño controla el catálogo por separado del
// diseño general de su web.

// offer_price ya no se edita: el precio promocionado lo dan los descuentos
// programados (pestaña Descuentos). Los productos viejos que lo tengan lo
// conservan hasta que el dueño lo quite — legacyOffer lo muestra y el
// botón "Quitar" lo limpia al guardar.
const productForm = reactive({ name: '', price: '', category: '', brand: '', description: '', is_active: true })
const productTouched = reactive({})
const legacyOffer = ref(null)
const offerCleared = ref(false)
const productBusy = ref(false)
const productEditing = ref(null)
const productImage = ref(null)
const productImagePreview = ref('')
const productImageInput = ref(null)
const productImageCleared = ref(false)
const productImageErr = ref('')

const taxonomyForm = reactive({ category: '', categoryFeatures: '', brand: '' })
const taxonomyBusy = reactive({ category: false, brand: false })
const taxonomyErr = reactive({ category: '', brand: '' })
// Edición de categoría: el mismo form agrega o guarda según haya id cargado.
const taxonomyEditing = ref(null)

// Características del producto: filas {name, value}. Al elegir categoría se
// precargan los atributos de su feature_schema; el resto se agrega libre.
const productFeatures = ref([])

function applyCategorySchema(categoryId) {
  const schema = catalog.categories.find((c) => c.id === categoryId)?.feature_schema || []
  const present = new Set(productFeatures.value.map((r) => r.name.trim().toLowerCase()))
  schema.forEach((name) => {
    if (!present.has(name.toLowerCase())) productFeatures.value.push({ name, value: '' })
  })
}

watch(() => productForm.category, (categoryId) => {
  if (categoryId) applyCategorySchema(categoryId)
})

function addFeatureRow() {
  if (productFeatures.value.length >= FEATURE_LIMITS.entriesMax) return
  productFeatures.value.push({ name: '', value: '' })
}

function removeFeatureRow(index) {
  productFeatures.value.splice(index, 1)
}

// Filas -> objeto {nombre: valor} que viaja como features (JSON) al backend.
function featuresToDict() {
  const dict = {}
  for (const row of productFeatures.value) {
    const name = row.name.trim()
    const value = row.value.trim()
    if (name && value) dict[name] = value
  }
  return dict
}

const featuresErr = computed(() => validateProductFeatures(productFeatures.value))

async function ensureCatalog() {
  if (!store.hasStore || !billing.hasSubscription) return
  if (!catalogLoaded.value) {
    catalogLoaded.value = true
    await catalog.loadAll()
  }
}
watch(section, (s) => {
  if (s === 'catalogs' || s === 'pos') ensureCatalog()
  // Al entrar a Diseño: la fuente elegida ya tiene que estar; el resto del
  // picker (las populares) se trae en un único <link> para que las flechas
  // y la vista previa muestren cada tipografía real al instante.
  if (s === 'design') {
    ensureStoreFont(designForm.name_font)
    ensureStoreFontPicker()
  }
  if (s === 'bot') ensureBot()
  if (s === 'stats' && canStats.value) store.loadStats()
  if (s === 'payments') billing.loadRedemptions()
})

// Los avisos se renderizan arriba de cada sección y el botón de guardar puede
// quedar muy abajo: cuando aparece un mensaje nuevo, scrollear hasta él.
watch(
  [
    () => store.notice, () => store.lastError,
    () => catalog.notice, () => catalog.lastError,
    () => billing.notice, () => billing.lastError,
    () => payments.notice, () => payments.lastError,
    () => invoices.lastError,
    accountMsg, accountErr, geoNotice, geoErr, verifyMsg, verifyErr
  ],
  async (vals, prev) => {
    if (!vals.some((v, i) => v && v !== prev[i])) return
    await nextTick()
    const alertEl = document.querySelector('.sec-on .alert') || document.querySelector('.main > .alert')
    alertEl?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
)

// Buscador del listado: filtra por nombre, categoría o marca (sin tildes).
const productQuery = ref('')
const filteredProducts = computed(() => {
  const q = productQuery.value.trim().toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  if (!q) return catalog.products
  return catalog.products.filter((p) =>
    [p.name, p.category_name, p.brand_name]
      .some((v) => (v || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').includes(q))
  )
})

const productLimit = computed(() => plan.value?.benefits?.max_products)
const productsCountText = computed(() => {
  const max = productLimit.value
  const total = catalog.products.length
  return max === null || max === undefined ? `${total} productos` : `${total} de ${max} productos`
})

const productErrors = computed(() => {
  const e = {}
  const n = validateProductName(productForm.name)
  const p = validateProductPrice(productForm.price)
  const d = validateProductDescription(productForm.description.trim())
  if (n) e.name = n
  if (p) e.price = p
  if (d) e.description = d
  if (featuresErr.value) e.features = featuresErr.value
  return e
})

function productFieldErr(name) {
  return (productTouched[name] ? productErrors.value[name] || '' : '') || catalog.fieldErrors[name] || ''
}

function onProductImagePicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  productImageErr.value = validateImageFile(file)
  if (productImageErr.value) return
  productImage.value = file
  productOriginal.value = null
  productImageCleared.value = false
  productImagePreview.value = URL.createObjectURL(file)
}

const productBgBusy = ref(false)
const productOriginal = ref(null)
async function removeProductBg() {
  if (!productImage.value || productBgBusy.value) return
  productImageErr.value = ''
  productBgBusy.value = true
  try {
    const source = productImage.value
    const result = await catalogApi.removeProductBackground(source)
    productOriginal.value = source
    productImage.value = result
    productImagePreview.value = URL.createObjectURL(result)
  } catch (e) {
    productImageErr.value = await bgErrorMessage(e)
  } finally {
    productBgBusy.value = false
  }
}
async function bgErrorMessage(e) {
  try {
    const body = e?.response?.data
    const parsed = body instanceof Blob ? JSON.parse(await body.text()) : body
    return parsed?.image || parsed?.detail || 'No pudimos quitar el fondo. Probá con otra foto.'
  } catch {
    return 'No pudimos quitar el fondo. Probá con otra foto.'
  }
}
function restoreProductOriginal() {
  if (!productOriginal.value) return
  productImage.value = productOriginal.value
  productImagePreview.value = URL.createObjectURL(productOriginal.value)
  productOriginal.value = null
}

function resetProductForm() {
  productOriginal.value = null
  Object.assign(productForm, { name: '', price: '', category: '', brand: '', description: '', is_active: true })
  legacyOffer.value = null
  offerCleared.value = false
  productFeatures.value = []
  Object.keys(productTouched).forEach((k) => { productTouched[k] = false })
  productEditing.value = null
  productImage.value = null
  productImagePreview.value = ''
  productImageCleared.value = false
  productImageErr.value = ''
}

function editProduct(p) {
  productEditing.value = p.id
  Object.assign(productForm, {
    name: p.name, price: p.price, category: p.category || '', brand: p.brand || '',
    description: p.description || '', is_active: p.is_active
  })
  legacyOffer.value = p.offer_price ?? null
  offerCleared.value = false
  productFeatures.value = Object.entries(p.features || {}).map(([name, value]) => ({ name, value }))
  if (p.category) applyCategorySchema(p.category)
  productImage.value = null
  productImagePreview.value = p.image || ''
  productImageCleared.value = false
  productImageErr.value = ''
  catalog.notice = ''
  catalog.lastError = ''
}

async function saveProduct() {
  Object.keys(productForm).forEach((k) => { productTouched[k] = true })
  productTouched.features = true
  if (Object.keys(productErrors.value).length) return
  productBusy.value = true
  const res = await catalog.saveProduct(productEditing.value, {
    fields: {
      name: productForm.name.trim(),
      price: productForm.price,
      // La oferta manual legada solo viaja cuando el dueño la quitó:
      // '' mapea a None en el backend. Sin el flag no se envía y el valor
      // guardado queda intacto mientras migra a Descuentos.
      ...(offerCleared.value ? { offer_price: '' } : {}),
      category: productForm.category,
      brand: productForm.brand,
      description: productForm.description.trim(),
      is_active: productForm.is_active,
      features: featuresToDict()
    },
    image: productImage.value,
    imageClear: productImageCleared.value
  })
  productBusy.value = false
  if (res.ok) {
    if (res.storage) store.storage = res.storage
    if (res.imageError) catalog.notice = `${res.imageError} (el producto se guardó sin imagen nueva).`
    pushToast(productEditing.value ? 'Cambios guardados ✓' : 'Producto publicado ✓')
    resetProductForm()
  }
}

async function removeProduct(p) {
  if (productBusy.value) return
  productBusy.value = true
  const res = await catalog.removeProduct(p.id)
  productBusy.value = false
  if (res?.storage) store.storage = res.storage
  if (productEditing.value === p.id) resetProductForm()
}

// --- Descuentos programados: se activan y vencen solos por la ventana ---
// El precio promocionado lo calcula el backend al leer (nunca se pisa
// offer_price): acá solo se programa nombre, %, alcance y fechas. La ventana
// se edita como fecha + hora separadas (el datetime-local nativo mezclaba
// ambos en una caja críptica); "Sin fin" deja ends_at en null.
const SCOPE_ICONS = { all: 'layout-grid', category: 'checklist', brand: 'tag', products: 'package' }
const pad2 = (n) => String(n).padStart(2, '0')
const localDateInput = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`

const discountForm = reactive({
  name: '', percent: '', scope: 'all', category: '', brand: '',
  product_ids: [],
  start_date: localDateInput(new Date()), start_time: '00:00',
  end_none: false, end_date: '', end_time: '23:59',
  is_active: true
})
const discountTouched = reactive({})
const discountBusy = ref(false)
const discountEditing = ref(null)

// Ventana en formato datetime-local (YYYY-MM-DDTHH:mm) para validar y
// convertir a ISO al guardar — las piezas sueltas del form se combinan acá.
const discountStartLocal = computed(() => discountForm.start_date ? `${discountForm.start_date}T${discountForm.start_time || '00:00'}` : '')
const discountEndLocal = computed(() => (discountForm.end_none || !discountForm.end_date) ? '' : `${discountForm.end_date}T${discountForm.end_time || '23:59'}`)

const discountErrors = computed(() => {
  const e = {}
  const n = validateDiscountName(discountForm.name)
  const p = validateDiscountPercent(discountForm.percent)
  const w = validateDiscountWindow(discountStartLocal.value, discountEndLocal.value)
  if (n) e.name = n
  if (p) e.percent = p
  if (w) e[discountForm.start_date ? 'end_date' : 'start_date'] = w
  if (!discountForm.end_none && !discountForm.end_date) e.end_date = 'Elegí la fecha de fin o marcá "Sin fin".'
  if (discountForm.scope === 'category' && !discountForm.category) e.category = 'Elegí la categoría a descontar.'
  if (discountForm.scope === 'brand' && !discountForm.brand) e.brand = 'Elegí la marca a descontar.'
  if (discountForm.scope === 'products' && !discountForm.product_ids.length) e.products = 'Elegí al menos un producto.'
  return e
})

// El backend reporta errores con las keys del modelo (starts_at/ends_at);
// el form las divide en fecha+hora (start_date/end_date) — se mapean acá.
// Un producto solo puede vivir en un grupo de ofertas vigente a la vez:
// los ya tomados por OTRO descuento con scope 'products' (vigente,
// programado o pausado — no el terminado) se muestran bloqueados con el
// nombre del grupo que los ocupa. El backend también lo rechaza; esto
// evita el ida y vuelta del error.
const discountTakenBy = computed(() => {
  const taken = new Map()
  for (const d of catalog.discounts) {
    if (d.scope !== 'products' || d.status === 'ended' || d.id === discountEditing.value) continue
    for (const pid of d.products || []) if (!taken.has(pid)) taken.set(pid, d.name)
  }
  return taken
})

const DISCOUNT_FIELD_MAP = { start_date: 'starts_at', end_date: 'ends_at' }
function discountFieldErr(name) {
  const serverKey = DISCOUNT_FIELD_MAP[name] || name
  return (discountTouched[name] ? discountErrors.value[name] || '' : '') || catalog.fieldErrors[serverKey] || catalog.fieldErrors[name] || ''
}

// Atajos de duración: completan inicio/fin de un toque (siempre se puede
// ajustar a mano después — son presets, no modos).
function discountPreset(kind) {
  const start = new Date()
  const end = new Date(start)
  discountForm.end_none = kind === 'none'
  if (kind === 'week') end.setDate(end.getDate() + (7 - end.getDay()) % 7) // domingo inclusive
  else if (kind === 'month') end.setMonth(end.getMonth() + 1, 0) // último día del mes
  else if (kind === 'fortnight') end.setDate(end.getDate() + 14)
  // 'today' y 'none' dejan end = hoy
  discountForm.start_date = localDateInput(start)
  discountForm.start_time = '00:00'
  discountForm.end_date = discountForm.end_none ? '' : localDateInput(end)
  discountForm.end_time = '23:59'
}

function resetDiscountForm() {
  Object.assign(discountForm, {
    name: '', percent: '', scope: 'all', category: '', brand: '',
    product_ids: [],
    start_date: localDateInput(new Date()), start_time: '00:00',
    end_none: false, end_date: '', end_time: '23:59',
    is_active: true
  })
  Object.keys(discountTouched).forEach((k) => { discountTouched[k] = false })
  discountEditing.value = null
}

function editDiscount(d) {
  discountEditing.value = d.id
  const start = isoToLocalInput(d.starts_at)
  const end = isoToLocalInput(d.ends_at)
  Object.assign(discountForm, {
    name: d.name, percent: d.percent, scope: d.scope,
    category: d.category || '', brand: d.brand || '', product_ids: [...(d.products || [])],
    start_date: start.slice(0, 10), start_time: start.slice(11, 16) || '00:00',
    end_none: !end, end_date: end.slice(0, 10), end_time: end.slice(11, 16) || '23:59',
    is_active: d.is_active
  })
  catalog.notice = ''
  catalog.lastError = ''
}

async function saveDiscount() {
  Object.keys(discountForm).forEach((k) => { discountTouched[k] = true })
  if (Object.keys(discountErrors.value).length) return
  discountBusy.value = true
  const ok = await catalog.saveDiscount(discountEditing.value, {
    name: discountForm.name.trim(),
    percent: Number(discountForm.percent),
    scope: discountForm.scope,
    // Fuera del alcance elegido viaja null: el backend limpia los restos.
    category: discountForm.scope === 'category' ? discountForm.category : null,
    brand: discountForm.scope === 'brand' ? discountForm.brand : null,
    products: discountForm.scope === 'products' ? discountForm.product_ids : [],
    starts_at: localInputToIso(discountStartLocal.value),
    ends_at: discountForm.end_none ? null : localInputToIso(discountEndLocal.value),
    is_active: discountForm.is_active
  })
  discountBusy.value = false
  if (ok) resetDiscountForm()
}

async function toggleDiscount(d) {
  if (discountBusy.value) return
  discountBusy.value = true
  await catalog.toggleDiscount(d)
  discountBusy.value = false
}

async function removeDiscount(d) {
  if (discountBusy.value) return
  discountBusy.value = true
  await catalog.removeDiscount(d.id)
  discountBusy.value = false
  if (discountEditing.value === d.id) resetDiscountForm()
}

async function addTaxonomy(kind) {
  const name = taxonomyForm[kind].trim()
  taxonomyErr[kind] = validateTaxonomyName(name)
  if (taxonomyErr[kind]) return
  const payload = { name }
  if (kind === 'category') {
    const schema = parseFeatureSchema(taxonomyForm.categoryFeatures)
    const schemaErr = validateFeatureSchema(schema)
    if (schemaErr) { taxonomyErr.category = schemaErr; return }
    payload.feature_schema = schema
  }
  taxonomyBusy[kind] = true
  const ok = kind === 'category'
    ? await catalog.saveCategory(taxonomyEditing.value, payload)
    : await catalog.saveBrand(null, payload)
  taxonomyBusy[kind] = false
  if (ok) {
    taxonomyForm[kind] = ''
    if (kind === 'category') cancelCategoryEdit()
  } else taxonomyErr[kind] = catalog.fieldErrors.name || catalog.fieldErrors.feature_schema || catalog.lastError
}

// Carga la categoría en el form para editar nombre y plantilla de
// características (misma vista que "Agregar", con botón Guardar).
function editCategory(c) {
  taxonomyEditing.value = c.id
  taxonomyForm.category = c.name
  taxonomyForm.categoryFeatures = (c.feature_schema || []).join(', ')
  taxonomyErr.category = ''
}

function cancelCategoryEdit() {
  taxonomyEditing.value = null
  taxonomyForm.category = ''
  taxonomyForm.categoryFeatures = ''
  taxonomyErr.category = ''
}

async function removeTaxonomy(kind, item) {
  const ok = kind === 'category' ? await catalog.removeCategory(item.id) : await catalog.removeBrand(item.id)
  if (!ok) taxonomyErr[kind] = catalog.lastError
  else if (kind === 'category' && taxonomyEditing.value === item.id) cancelCategoryEdit()
}

// --- QR y folletos (premium): QR del link público + folleto imprimible ---
const qrDataUrl = ref('')
const canStats = computed(() => Boolean(plan.value?.benefits?.has_stats))
// Visitas de la web pública (endpoint /stores/stats/: 1 por visitante/día).
const visitDays = computed(() => store.visitStats?.days || [])
const visitMax = computed(() => Math.max(1, ...visitDays.value.map((d) => d.count)))
const visitAvg = computed(() => {
  if (!visitDays.value.length) return '0'
  const sum = visitDays.value.reduce((a, d) => a + d.count, 0)
  return (sum / visitDays.value.length).toFixed(1)
})
const canQr = computed(() => Boolean(plan.value?.benefits?.has_qr))
const canFlyers = computed(() => Boolean(plan.value?.benefits?.has_flyers))

async function buildQr() {
  if (!publicUrl.value || !canQr.value) return
  try {
    // La lib del QR solo se descarga al abrir la sección Herramientas.
    const QRCode = (await import('qrcode')).default
    qrDataUrl.value = await QRCode.toDataURL(publicUrl.value, {
      width: 480, margin: 1, color: { dark: '#0f172a', light: '#ffffff' }
    })
  } catch {
    qrDataUrl.value = ''
  }
}
watch([section, publicUrl], ([s]) => { if (s === 'tools') buildQr() })

function downloadQr() {
  if (!qrDataUrl.value) return
  const a = document.createElement('a')
  a.href = qrDataUrl.value
  a.download = `qr-${store.store?.slug || 'tienda'}.png`
  a.click()
}

const discountPreviewPct = computed(() => Math.min(99, Math.max(0, Math.round(Number(discountForm.percent)) || 0)))
const toolsTab = ref('ready')
watch([section, canFlyers], () => { if (!canFlyers.value && toolsTab.value === 'studio') toolsTab.value = 'ready' })

function openFlyer(custom = false) {
  const href = router.resolve({ name: 'store-flyer', query: custom === true ? { custom: '1' } : {} }).href
  window.open(href, '_blank', 'noopener')
}

// --- Venta en local (POS de escritorio, próximamente) ---
// El mockup estático se dibuja con el logo, el nombre y el acento reales de
// la tienda (storeThemeVars), y con los primeros productos del catálogo
// cuando ya están cargados (placeholders si todavía no hay ninguno).
const POS_SAMPLE_PRODUCTS = ['Producto 1', 'Producto 2', 'Producto 3', 'Producto 4', 'Producto 5', 'Producto 6']
  .map((name) => ({ name }))
const POS_CART_QTY = [2, 1, 1]
const posCartQty = POS_CART_QTY
const posToday = new Date().toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
const posVars = computed(() => storeThemeVars(store.customization))
const posProducts = computed(() => (catalog.products.length ? catalog.products.slice(0, 6) : POS_SAMPLE_PRODUCTS))
const posCartItems = computed(() => posProducts.value.slice(0, POS_CART_QTY.length))
const posSubtotal = computed(() => posCartItems.value.reduce((acc, p, i) => acc + (Number(p.price) || 0) * POS_CART_QTY[i], 0))
const posHasPrices = computed(() => posSubtotal.value > 0)
const posIva = computed(() => (posHasPrices.value ? formatARS(posSubtotal.value * 0.21) : '—'))
const posInvoiceTotal = computed(() => (posHasPrices.value ? formatARS(posSubtotal.value * 1.21) : '—'))
const posCityName = computed(() => {
  const found = cities.value.find((c) => Number(c.id) === Number(accountForm.city))
  return found?.name || ''
})
const posAddress = computed(() => [accountForm.address, posCityName.value].filter(Boolean).join(', '))

// --- Chatbot (solo Premium, beneficio has_chatbot): el asistente de la web
// pública responde a las visitas con los pares pregunta/respuesta que el
// dueño carga acá. PATCH /api/stores/chatbot/ da 403 sin el beneficio y la
// web pública solo lo recibe cuando is_enabled está prendido.
const canChatbot = computed(() => Boolean(plan.value?.benefits?.has_chatbot))
const botForm = reactive({ ...CHATBOT_DEFAULTS, qa: [] })
const botBusy = ref(false)
const botErr = ref('')
const botLoaded = ref(false)

// El store Pinia guarda la config cargada/guardada; espeja al form.
watch(() => store.chatbot, (cfg) => {
  if (!cfg) return
  botForm.is_enabled = Boolean(cfg.is_enabled)
  botForm.greeting = cfg.greeting || ''
  botForm.qa = (cfg.qa || []).map((i) => ({ q: i.q || '', a: i.a || '' }))
})

function ensureBot() {
  if (botLoaded.value || !canChatbot.value || !store.hasStore) return
  botLoaded.value = true
  store.loadChatbot()
}

function addBotQa() {
  if (botForm.qa.length < CHATBOT_QA_MAX) botForm.qa.push({ q: '', a: '' })
}

async function saveBot() {
  if (botBusy.value) return
  botErr.value = ''
  const qa = botForm.qa.map((i) => ({ q: String(i.q || '').trim(), a: String(i.a || '').trim() }))
  if (qa.some((i) => (i.q && !i.a) || (!i.q && i.a))) {
    botErr.value = 'Cada pregunta necesita su respuesta. Completá la fila o borrala con el tachito.'
    return
  }
  botBusy.value = true
  const ok = await store.saveChatbot({
    is_enabled: botForm.is_enabled,
    greeting: botForm.greeting.trim(),
    qa: qa.filter((i) => i.q && i.a)
  })
  botBusy.value = false
  if (!ok) botErr.value = store.fieldErrors.detail || store.lastError || 'No se pudo guardar el chatbot.'
}

// --- Diseño web: personalización de la página pública ---
// Contenido, logo y tema claro/oscuro: beneficio has_customization (en todos
// los planes; el backend lo fuerza en PATCH). Fuente, portada, tamaño del
// nombre, acento y carrusel son premium (has_design_advanced): se ven
// bloqueados y el carrusel directamente no se muestra. La fuente se elige
// solo entre las populares del mercado (STORE_FONT_GROUPS): el backend
// acepta el superset de FONT_CHOICES así un valor guardado de otra época
// sigue validando — el select lo agrega como opción extra "Guardada".
// Las listas se inicializan frescas: el spread compartiría las instancias
// de CUSTOMIZATION_DEFAULTS y editarlas antes de que llegue la tienda
// ensuciaría los defaults del módulo.
const designForm = reactive({ ...CUSTOMIZATION_DEFAULTS, services: [], stats: [], testimonials: [], faqs: [], hours: [], benefits: [], timeline: [], team: [], section_order: [], announcements: [], site_templates: [], service_steps: [], service_days: [], service_slots: [], layout_config: {}, site_theme: {} })
const designTouched = reactive({})
const designTab = ref('look')
// Vista previa de la pestaña Diseño en mobile: la savebar sticky la abre.
const lookPreview = ref(false)
// Sub-secciones de "Diseño": las tres últimas se muestran con candado cuando
// el plan no trae el beneficio (nunca se ocultan).
const designTabs = [
  { id: 'look', label: 'Diseño', icon: 'palette', desc: 'Estilo, colores y tipografía' },
  { id: 'assisted', label: 'Diseño asistido', icon: 'sparkles', desc: 'La IA arma una propuesta', benefit: 'has_ai_design' },
  { id: 'studio', label: 'Studio', icon: 'layout-panel-left', desc: 'Control total, pantalla completa', benefit: 'has_design_advanced' }
]
const designContentTabs = [
  { id: 'content', label: 'Mis datos', icon: 'pencil' },
  { id: 'images', label: 'Fotos', icon: 'images' },
  { id: 'sections', label: 'Qué mostrar', icon: 'layout-grid' }
]
const DESIGN_TAB_LOCKS = { assisted: 'design_assisted', studio: 'design_studio' }
function designTabLocked(tab) {
  return Boolean(tab.benefit) && !plan.value?.benefits?.[tab.benefit]
}
function openDesignTab(tab) {
  if (designTabLocked(tab)) { openLocked(DESIGN_TAB_LOCKS[tab.id] || 'design_studio'); return }
  if (tab.id === 'studio') { openStudioRoute(); return }
  designTab.value = tab.id
}
// Studio en pestaña/ventana exclusiva: ruta propia a pantalla completa.
function openStudioRoute() {
  if (!canDesignAdvanced.value) { openLocked('design_studio'); return }
  router.push({ name: 'design-studio' })
}
// Navegación interna de las sub-secciones (Diseño asistido / IA): las
// secciones reales del panel cambian `section`; "design" apunta a Fotos.
function onDesignNav(target) {
  if (target === 'design' || target === 'images') { designTab.value = 'images'; return }
  if (validIds.value.has(target)) { section.value = target; return }
  section.value = 'design'
}
const canCustomize = computed(() => Boolean(plan.value?.benefits?.has_customization))
const canDesignAdvanced = computed(() => Boolean(plan.value?.benefits?.has_design_advanced))
const canLocationMap = computed(() => Boolean(plan.value?.benefits?.has_location_map))
const canProductComments = computed(() => Boolean(plan.value?.benefits?.has_product_comments))
const canDiscounts = computed(() => Boolean(plan.value?.benefits?.has_discounts))
const businessInitial = computed(() => (business.value || 'T').slice(0, 1).toUpperCase())
const IDENTITY_DEFAULTS = { accent_custom: '', logo_scale: 'm', logo_mode: 'logo_name', mono_style: 'accent', cover_overlay: 0, cover_focus_x: 50, cover_focus_y: 50 }
const designPreviewVars = computed(() => storeThemeVars(canDesignAdvanced.value ? designForm : { ...designForm, ...IDENTITY_DEFAULTS }))
// Plantillas elegibles por nivel de plan (espejo del backend): Básico
// elige base, Estándar suma 'plus' y Premium todo el catálogo.
const allowedTemplates = computed(() => allowedTemplatesFor(plan.value?.benefits || {}))
const designTemplate = computed(() => resolveStoreTemplate(designForm.template, allowedTemplates.value))
// Si el guardado quedó fuera del nivel (baja de plan o una plantilla
// retirada del catálogo) el select vuelve al primer diseño permitido.
// Solo con beneficios ya resueltos: si el plan todavía no llegó la lista
// queda en base y degradaría cualquier plantilla plus/advanced guardada
// (dirty falso al montar y un save que pisa el template real).
watch(allowedTemplates, (list) => {
  if (plan.value?.benefits && !list.includes(designForm.template)) designForm.template = list[0] || 'raiz'
})
// Si cambia la fuente elegida, traerla en el momento (cubre una "Guardada"
// fuera del picker, que el link colectivo no incluye).
watch(() => designForm.name_font, (f) => ensureStoreFont(f))

let lastServerDesign = null
// Bandera compartida con useStudioDesign: true mientras el save del diseño
// está en vuelo, para que el watcher de la tienda no pise lo editado.
const serverFlags = { accept: false }
const designFieldValue = (v) => (
  typeof v === 'string' ? v.trim() : (v && typeof v === 'object' ? JSON.stringify(v) : v ?? '')
)
// Precarga el diseño guardado cuando llega la tienda (customization anidada).
watch(() => store.store, (s) => {
  if (!s) return
  // Subir un logo/portada o guardar otra sección refresca la tienda: lo que
  // el usuario editó y todavía no guardó en el diseño se conserva (salvo
  // justo después de guardar el diseño, donde manda lo que devolvió el server).
  const keep = {}
  if (lastServerDesign && !serverFlags.accept) {
    DESIGN_FIELDS.forEach((k) => { if (designFieldValue(designForm[k]) !== designFieldValue(lastServerDesign[k])) keep[k] = designForm[k] })
  }
  serverFlags.accept = false
  Object.assign(designForm, store.customization)
  Object.assign(designForm, keep)
  lastServerDesign = Object.fromEntries(DESIGN_FIELDS.map((k) => [k, { ...CUSTOMIZATION_DEFAULTS, ...store.customization }[k]]))
  // La fuente guardada tiene que estar cargada cuando llega el valor:
  // la vista previa del panel y el picker la muestran con la tipografía real.
  ensureStoreFont(designForm.name_font)
  // Si el plan ya estaba cargado y el diseño guardado quedó fuera de su
  // nivel (baja de plan o plantilla retirada del catálogo), vuelve al
  // primero permitido. Con beneficios aún sin resolver no se degrada:
  // la lista vendría en base y pisaría una plantilla superior guardada.
  if (plan.value?.benefits && !allowedTemplates.value.includes(designForm.template)) designForm.template = allowedTemplates.value[0] || 'raiz'
}, { immediate: true })

const designErrors = computed(() => {
  const e = {}
  const dn = validateDisplayName(designForm.display_name.trim())
  const h = validateHeadline(designForm.headline.trim())
  const d = validateDescription(designForm.description.trim())
  const at = validateAboutTitle(designForm.about_title.trim())
  const ax = validateAboutText(designForm.about_text.trim())
  const ay = validateAboutYears(designForm.about_years)
  const am = validateAboutMission(designForm.about_mission.trim())
  const asp = validateAboutSpecialties(designForm.about_specialties.trim())
  const ce = validateContactEmail(designForm.contact_email)
  const w = validateWhatsapp(designForm.whatsapp)
  const ig = validateInstagram(designForm.instagram)
  const tt = validateTiktok(designForm.tiktok)
  const fb = validateFacebook(designForm.facebook)
  if (dn) e.display_name = dn
  if (h) e.headline = h
  if (d) e.description = d
  if (at) e.about_title = at
  if (ax) e.about_text = ax
  if (ay) e.about_years = ay
  if (am) e.about_mission = am
  if (asp) e.about_specialties = asp
  if (ce) e.contact_email = ce
  if (w) e.whatsapp = w
  if (ig) e.instagram = ig
  if (tt) e.tiktok = tt
  if (fb) e.facebook = fb
  return e
})

function designFieldErr(name) {
  return (designTouched[name] ? designErrors.value[name] || '' : '') || store.fieldErrors[name] || ''
}

// "Mi empresa" (sección propia): hub del contenido de marketing de la
// portada. Cada tarjeta guarda su propio PATCH parcial con los campos de su
// bloque; las listas (servicios, cifras, testimonios, FAQ, horarios) se
// editan como filas y el backend las sanea igual que el qa del chatbot:
// recorta textos, descarta filas incompletas y filtra lo desconocido.
const COMPANY_FIELDS = ['about_title', 'about_text', 'about_years', 'about_mission', 'about_specialties']
const companyBusy = ref(false)
const companyErrs = reactive({})
const mkLimits = MARKETING_LIMITS
const serviceIcons = SERVICE_ICONS
const serviceIconOptions = Object.entries(SERVICE_ICONS).map(([value, label]) => ({ value, label, icon: value }))
const serviceVisibilityOptions = [
  { value: true, label: 'Visible en mi web', icon: 'eye' },
  { value: false, label: 'Oculto', icon: 'eye-off' }
]
// Una fila "a medias" (algo escrito pero sin sus campos requeridos) avisa y
// no deja guardar — mismo criterio que las preguntas del chatbot.
function hasPartialRow(rows, keys, required) {
  return rows.some((r) => keys.some((k) => String(r[k] ?? '').trim()) && required.some((k) => !String(r[k] ?? '').trim()))
}
function cleanRows(rows, keys, required = keys) {
  return rows
    .map((r) => Object.fromEntries(keys.map((k) => [k, String(r[k] ?? '').trim()])))
    .filter((r) => required.every((k) => r[k]))
}
function addRow(list, max, row) {
  if (list.length < max) list.push(row)
}
function moveRow(list, index, direction) {
  const target = index + direction
  if (target < 0 || target >= list.length) return
  ;[list[index], list[target]] = [list[target], list[index]]
}

// Atajos a cada bloque de la sección (es larga: chips con scroll suave).
const mkNav = [
  { id: 'mk-about', label: 'Sobre nosotros' },
  { id: 'mk-services', label: 'Qué ofrecemos' },
  { id: 'mk-stats', label: 'Tus números' },
  { id: 'mk-testimonials', label: 'Testimonios' },
  { id: 'mk-faqs', label: 'Preguntas' },
  { id: 'mk-benefits', label: 'Garantías' },
  { id: 'mk-timeline', label: 'Trayectoria' },
  { id: 'mk-team', label: 'Equipo' },
  { id: 'mk-hours', label: 'Horarios' },
  { id: 'mk-cta', label: 'Llamado a la acción' },
  { id: 'mk-ann', label: 'Anuncios' },
  { id: 'mk-video', label: 'Video' },
  { id: 'mk-extras', label: 'Extras' }
]
function scrollToCard(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function saveCompany() {
  COMPANY_FIELDS.forEach((k) => { designTouched[k] = true })
  if (COMPANY_FIELDS.some((k) => designErrors.value[k])) return
  companyBusy.value = true
  const years = designForm.about_years
  const ok = await store.saveCustomization({
    about_title: designForm.about_title.trim(),
    about_text: designForm.about_text.trim(),
    about_years: years === '' || years === null || years === undefined ? null : Number(years),
    about_mission: designForm.about_mission.trim(),
    about_specialties: designForm.about_specialties.trim()
  })
  companyBusy.value = false
  if (ok) pushToast('Guardado ✓')
}

async function saveServices() {
  companyErrs.services = ''
  if (validateSectionTitle(designForm.services_title.trim())) { companyErrs.services = 'El título admite hasta 80 caracteres.'; return }
  if (hasPartialRow(designForm.services, ['title', 'text'], ['title', 'text'])) {
    companyErrs.services = 'Cada servicio necesita título y descripción. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    services_title: designForm.services_title.trim(),
    show_services: Boolean(designForm.show_services),
    services: cleanRows(designForm.services, ['icon', 'title', 'text'], ['title', 'text'])
  })
  companyBusy.value = false
}

async function saveStats() {
  companyErrs.stats = ''
  if (hasPartialRow(designForm.stats, ['value', 'label'], ['value', 'label'])) {
    companyErrs.stats = 'Cada número necesita valor y etiqueta. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    show_stats: Boolean(designForm.show_stats),
    stats: cleanRows(designForm.stats, ['value', 'label'])
  })
  companyBusy.value = false
}

async function saveTestimonials() {
  companyErrs.testimonials = ''
  if (validateSectionTitle(designForm.testimonials_title.trim())) { companyErrs.testimonials = 'El título admite hasta 80 caracteres.'; return }
  if (hasPartialRow(designForm.testimonials, ['name', 'detail', 'text'], ['name', 'text'])) {
    companyErrs.testimonials = 'Cada testimonio necesita nombre y texto. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    testimonials_title: designForm.testimonials_title.trim(),
    show_testimonials: Boolean(designForm.show_testimonials),
    testimonials: cleanRows(designForm.testimonials, ['name', 'detail', 'text'], ['name', 'text'])
  })
  companyBusy.value = false
}

async function saveFaqs() {
  companyErrs.faqs = ''
  if (validateSectionTitle(designForm.faqs_title.trim())) { companyErrs.faqs = 'El título admite hasta 80 caracteres.'; return }
  if (hasPartialRow(designForm.faqs, ['q', 'a'], ['q', 'a'])) {
    companyErrs.faqs = 'Cada pregunta necesita su respuesta. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    faqs_title: designForm.faqs_title.trim(),
    show_faq: Boolean(designForm.show_faq),
    faqs: cleanRows(designForm.faqs, ['q', 'a'])
  })
  companyBusy.value = false
}

async function saveBenefits() {
  companyErrs.benefits = ''
  if (hasPartialRow(designForm.benefits || [], ['title', 'text'], ['title'])) {
    companyErrs.benefits = 'Cada beneficio necesita al menos su título. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    show_benefits: Boolean(designForm.show_benefits),
    benefits: cleanRows(designForm.benefits || [], ['icon', 'title', 'text'], ['title'])
  })
  companyBusy.value = false
}

async function saveTimeline() {
  companyErrs.timeline = ''
  if (hasPartialRow(designForm.timeline || [], ['label', 'text'], ['label', 'text'])) {
    companyErrs.timeline = 'Cada hito necesita su rótulo (año o etapa) y el texto. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    show_timeline: Boolean(designForm.show_timeline),
    timeline: cleanRows(designForm.timeline || [], ['label', 'text'], ['label', 'text'])
  })
  companyBusy.value = false
}

async function saveTeam() {
  companyErrs.team = ''
  if (hasPartialRow(designForm.team || [], ['name', 'role'], ['name'])) {
    companyErrs.team = 'Cada integrante necesita su nombre. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    show_team: Boolean(designForm.show_team),
    team: cleanRows(designForm.team || [], ['name', 'role'], ['name'])
  })
  companyBusy.value = false
}

async function saveHours() {
  companyErrs.hours = ''
  if (hasPartialRow(designForm.hours, ['label', 'value'], ['label', 'value'])) {
    companyErrs.hours = 'Cada horario necesita los días y la franja. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    show_hours: Boolean(designForm.show_hours),
    hours: cleanRows(designForm.hours, ['label', 'value'])
  })
  companyBusy.value = false
}

async function saveCta() {
  companyErrs.cta = ''
  const err = validateCtaTitle(designForm.cta_title.trim())
    || validateCtaText(designForm.cta_text.trim())
    || validateCtaLabel(designForm.cta_label.trim())
  if (err) { companyErrs.cta = err; return }
  companyBusy.value = true
  await store.saveCustomization({
    show_cta: Boolean(designForm.show_cta),
    cta_title: designForm.cta_title.trim(),
    cta_text: designForm.cta_text.trim(),
    cta_label: designForm.cta_label.trim()
  })
  companyBusy.value = false
}

async function saveAnnouncements() {
  companyErrs.announcements = ''
  if (hasPartialRow(designForm.announcements, ['icon', 'text'], ['text'])) {
    companyErrs.announcements = 'Cada anuncio necesita su texto. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    show_announcements: Boolean(designForm.show_announcements),
    announcements: cleanRows(designForm.announcements, ['icon', 'text'], ['text'])
  })
  companyBusy.value = false
}

async function saveVideo() {
  companyErrs.video = ''
  const err = validateVideoUrl(designForm.video_url.trim())
    || validateSectionTitle(designForm.video_title.trim())
  if (err) { companyErrs.video = err; return }
  companyBusy.value = true
  await store.saveCustomization({
    show_video: Boolean(designForm.show_video),
    video_url: designForm.video_url.trim(),
    video_title: designForm.video_title.trim()
  })
  companyBusy.value = false
}

async function saveExtras() {
  companyErrs.extras = ''
  if (designForm.catalog_note.trim().length > mkLimits.catalogNote || designForm.footer_text.trim().length > mkLimits.footerText) {
    companyErrs.extras = `El aviso del catálogo y el texto del pie admiten hasta ${mkLimits.catalogNote} caracteres.`
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    catalog_note: designForm.catalog_note.trim(),
    footer_text: designForm.footer_text.trim()
  })
  companyBusy.value = false
}

// Cambios sin guardar del editor de diseño: solo los campos que viajan en
// saveDesign (las demás secciones guardan por su cuenta).
const designDirty = computed(() => {
  if (!store.store) return false
  const base = { ...CUSTOMIZATION_DEFAULTS, ...store.customization }
  return DESIGN_FIELDS.some((k) => {
    if (!canDesignAdvanced.value && (['name_font', 'name_font_size', 'accent'].includes(k) || k in IDENTITY_DEFAULTS)) return false
    return designFieldValue(designForm[k]) !== designFieldValue(base[k])
  })
})
// Studio de diseño: estado y handlers viven en el composable compartido con
// la ruta exclusiva /dashboard/diseno/studio (sin duplicar guardado/publicación).
const {
  designBusy, designDirtyAll, saveDesign, discardDesign
} = useStudioDesign({
  store, plan, designForm, designDirty, designErrors, designTouched,
  canDesignAdvanced, canLocationMap, catalog, services,
  pushToast, serverFlags, companyFields: COMPANY_FIELDS,
  designTab,
  navigate(target) {
    if (target === 'tools') { section.value = 'tools'; toolsTab.value = 'studio' }
    else if (['blocks', 'plans', 'company', 'catalogs', 'services'].includes(target)) section.value = target
    else pushToast('Esa sección no está disponible desde el Studio')
  }
})

// Diseñar con IA: la vista aplica/publica/descarta sobre el borrador y avisa
// acá para refrescar el estado de la tienda y mover al usuario si pidió seguir
// a mano. El banner de resultado vive dentro de la vista.
async function onAiApplied(payload) {
  await store.refreshCustomization()
  const action = payload?.action
  pushToast(action === 'publish' ? 'Publicado: tu web ya muestra los cambios ✓'
    : action === 'discard' ? 'Borrador descartado'
    : 'Diseño aplicado al borrador')
  if (payload?.section) sectionInner.value = payload.section
}
const lookRing = ref(null)
const previewSheet = ref(false)
const previewBottom = ref(80)
const dsgBar = ref(null)
const leaveStay = ref(null)
function measureSheet() {
  const r = dsgBar.value?.getBoundingClientRect()
  previewBottom.value = r ? Math.max(0, Math.round(window.innerHeight - r.top + 8)) : 80
}
watch(previewSheet, (on) => { if (on) nextTick(measureSheet) })
const leaveGuard = reactive({ open: false, target: null, route: null })
watch(() => leaveGuard.open, (on) => { if (on) nextTick(() => leaveStay.value?.focus()) })
function onBeforeUnload(e) {
  if (designDirtyAll.value) { e.preventDefault(); e.returnValue = '' }
}
function confirmLeave(discard) {
  const { target, route: to } = leaveGuard
  leaveGuard.open = false
  leaveGuard.target = null
  leaveGuard.route = null
  if (!discard) return
  discardDesign()
  if (to) router.push(to)
  else if (target) sectionInner.value = target
}
onBeforeRouteLeave((to) => {
  if (!designDirtyAll.value) return true
  leaveGuard.route = to
  leaveGuard.open = true
  return false
})
window.addEventListener('beforeunload', onBeforeUnload)
window.addEventListener('resize', measureSheet)
onUnmounted(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  window.removeEventListener('resize', measureSheet)
})

// Páginas de la web (site_templates): multi-selección de catálogo cerrado
// que reemplazó al site_mode (both/marketing/catalog). El plan fija el
// cupo (max_site_templates: Básico/Estándar 2, Premium las tres) y la
// página Servicios exige además el flag has_services_site. Cada cambio
// guarda al instante con su propio PATCH — el backend fuerza las mismas
// reglas (400 si el set viola el plan).
const siteTemplateKeys = SITE_TEMPLATE_KEYS
const siteTemplates = SITE_TEMPLATES
const siteTemplatesBusy = ref(false)
const canServicesSite = computed(() => Boolean(plan.value?.benefits?.has_services_site))
const allowedSiteTemplates = computed(() => allowedSiteTemplatesFor(plan.value?.benefits || {}))
const siteTemplatesMax = computed(() => siteTemplatesLimit(plan.value?.benefits || {}))
// Set que se muestra: guardado normalizado ∩ plan (el backend manda lo
// guardado; acá se recorta igual que effective_site_templates).
const designSiteTemplates = computed(() => resolveSiteTemplates(designForm.site_templates, plan.value?.benefits || {}))
const siteTemplatesHint = computed(() => {
  const max = siteTemplatesMax.value
  return max === null ? 'Tu plan permite tener las tres páginas activas.' : `Tu plan permite hasta ${max} ${max === 1 ? 'página' : 'páginas'} a la vez.`
})
function siteTemplateLock(key) {
  return key === 'services' && !canServicesSite.value ? 'Desde Estándar' : ''
}
function canToggleSiteTemplate(key) {
  if (siteTemplatesBusy.value || !allowedSiteTemplates.value.includes(key)) return false
  const on = designSiteTemplates.value.includes(key)
  if (on) return designSiteTemplates.value.length > 1 // la web nunca queda vacía
  return siteTemplatesMax.value === null || designSiteTemplates.value.length < siteTemplatesMax.value
}
async function toggleSiteTemplate(key) {
  if (!canToggleSiteTemplate(key)) return
  const current = [...designSiteTemplates.value]
  const i = current.indexOf(key)
  if (i === -1) current.push(key)
  else current.splice(i, 1)
  const next = SITE_TEMPLATE_KEYS.filter((k) => current.includes(k))
  const prev = normalizeSiteTemplates(designForm.site_templates)
  designForm.site_templates = next
  designForm.show_catalog = next.includes('catalog')
  siteTemplatesBusy.value = true
  const ok = await store.saveCustomization({ site_templates: next })
  if (!ok) {
    designForm.site_templates = prev
    designForm.show_catalog = prev.includes('catalog')
  }
  siteTemplatesBusy.value = false
}

// ----- Mis servicios (sección propia del menú, gated por has_services_site) -----
// CRUD de los ítems de la página "Servicios" + la config del embudo
// (pasos, días, franjas, notas). El endpoint responde 403 sin el flag —
// services.denied dispara la tarjeta de upgrade.
const servicesLoaded = ref(false)
watch(section, (s) => {
  if (s === 'services' && !servicesLoaded.value) {
    servicesLoaded.value = true
    services.loadAll()
  }
})
const serviceForm = reactive({ name: '', price: '', duration: '', icon: 'wrench', description: '', is_active: true })
const serviceTouched = reactive({})
const serviceBusy = ref(false)
const serviceEditing = ref(null)
const serviceLimits = SERVICE_LIMITS
const servicePageLimits = SERVICE_PAGE_LIMITS
const svcBusy = ref(false) // PATCH de la config de la página (pasos/días/notas)

const serviceErrors = computed(() => {
  const e = {}
  const n = validateServiceName(serviceForm.name)
  const d = validateServiceDescription(serviceForm.description.trim())
  const p = validateServicePrice(serviceForm.price)
  const du = validateServiceDuration(serviceForm.duration.trim())
  if (n) e.name = n
  if (d) e.description = d
  if (p) e.price = p
  if (du) e.duration = du
  return e
})
function serviceFieldErr(name) {
  return (serviceTouched[name] ? serviceErrors.value[name] || '' : '') || services.fieldErrors[name] || ''
}
function resetServiceForm() {
  serviceEditing.value = null
  Object.assign(serviceForm, { name: '', price: '', duration: '', icon: 'wrench', description: '', is_active: true })
  Object.keys(serviceTouched).forEach((k) => { serviceTouched[k] = false })
}
function editService(s) {
  serviceEditing.value = s
  Object.assign(serviceForm, {
    name: s.name, price: s.price ?? '', duration: s.duration || '',
    icon: s.icon || 'wrench', description: s.description || '', is_active: Boolean(s.is_active)
  })
}
async function saveService() {
  Object.keys(serviceForm).forEach((k) => { serviceTouched[k] = true })
  if (Object.keys(serviceErrors.value).length) return
  serviceBusy.value = true
  const ok = await services.saveService(serviceEditing.value?.id, servicePayload(serviceForm))
  serviceBusy.value = false
  if (ok) {
    pushToast(serviceEditing.value ? 'Cambios guardados ✓' : 'Servicio publicado ✓')
    resetServiceForm()
  }
}
async function removeService(s) {
  await services.removeService(s.id)
  if (serviceEditing.value?.id === s.id) resetServiceForm()
}
async function moveService(s, dir) {
  services.moveItem(s.id, dir)
  await services.saveOrder()
}
function serviceIcon(key) {
  return SERVICE_ICONS[key] ? key : 'wrench'
}
const serviceStats = computed(() => {
  const list = services.items
  const active = list.filter((s) => s.is_active).length
  const priced = list.filter((s) => s.price !== null && s.price !== '' && s.price !== undefined).length
  return [
    { key: 'total', icon: 'wrench', label: 'Servicios', value: list.length, hint: `de ${serviceLimits.max} posibles`, hue: 250 },
    { key: 'on', icon: 'eye', label: 'Visibles', value: active, hint: 'en tu web ahora', hue: 155 },
    { key: 'off', icon: 'eye-off', label: 'Ocultos', value: list.length - active, hint: 'solo vos los ves', hue: 38 },
    { key: 'price', icon: 'tag', label: 'Con precio', value: priced, hint: `${list.length - priced} a convenir`, hue: 330 }
  ]
})
const serviceUsage = computed(() => Math.min(100, Math.round((services.items.length / (serviceLimits.max || 1)) * 100)))
function addServiceStep() {
  const list = designForm.service_steps || (designForm.service_steps = [])
  if (list.length < servicePageLimits.steps) list.push({ icon: 'check', title: '', text: '' })
}
function removeServiceStep(i) {
  designForm.service_steps?.splice(i, 1)
}

// Config del embudo de la página (service_* de customization): filas de
// pasos como las de "Qué ofrecemos", días y franjas como listas de
// etiquetas, y las notas de precio/pago. Se guarda junto con un PATCH.
const serviceChipDraft = reactive({ service_days: '', service_slots: '' })
const SERVICE_CHIP_SUGGESTIONS = {
  service_days: ['Hoy', 'Mañana', 'Lunes a viernes', 'Sábado', 'Domingo'],
  service_slots: ['Mañana (9 a 12 h)', 'Tarde (15 a 18 h)', 'Noche (19 a 21 h)']
}
function chipMax(field) {
  return field === 'service_days' ? servicePageLimits.days : servicePageLimits.slots
}
function addServiceChip(field, value) {
  const v = String(value ?? serviceChipDraft[field]).trim().slice(0, servicePageLimits.day)
  const list = designForm[field] || (designForm[field] = [])
  if (v && list.length < chipMax(field) && !list.some((x) => x.toLowerCase() === v.toLowerCase())) list.push(v)
  serviceChipDraft[field] = ''
}
function removeServiceChip(field, i) {
  designForm[field]?.splice(i, 1)
}
function onChipKey(e, field) {
  if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addServiceChip(field) }
  else if (e.key === 'Backspace' && !serviceChipDraft[field]) designForm[field]?.pop()
}
async function saveServicePage() {
  companyErrs.servicePage = ''
  if (hasPartialRow(designForm.service_steps || [], ['title', 'text'], ['title', 'text'])) {
    companyErrs.servicePage = 'Cada paso necesita título y descripción. Completá la fila o borrala con el tachito.'
    return
  }
  if ((designForm.service_price_note || '').length > servicePageLimits.note || (designForm.service_pay_note || '').length > servicePageLimits.note) {
    companyErrs.servicePage = `Las notas admiten hasta ${servicePageLimits.note} caracteres.`
    return
  }
  svcBusy.value = true
  const okSvcPage = await store.saveCustomization({
    service_steps: cleanRows(designForm.service_steps || [], ['icon', 'title', 'text'], ['title', 'text']),
    service_days: (designForm.service_days || []).map((s) => String(s).trim()).filter(Boolean),
    service_slots: (designForm.service_slots || []).map((s) => String(s).trim()).filter(Boolean),
    service_ask_address: Boolean(designForm.service_ask_address),
    service_price_note: (designForm.service_price_note || '').trim(),
    service_pay_note: (designForm.service_pay_note || '').trim()
  })
  svcBusy.value = false
  if (okSvcPage) pushToast('Guardado ✓')
}

// Valoraciones/comentarios de la web pública: toggles instantáneos como
// site_templates (la sección Opiniones no tiene botón de guardar). Toda la
// función pide has_product_comments (premium); el backend descarta
// show_reviews/show_comments sin el flag — el checkbox solo se bloquea
// en la UI.
const reviewToggleBusy = ref(false)
async function toggleShowReviews() {
  if (reviewToggleBusy.value || !canProductComments.value) return
  const prev = designForm.show_reviews
  designForm.show_reviews = !prev
  reviewToggleBusy.value = true
  const ok = await store.saveCustomization({ show_reviews: designForm.show_reviews })
  if (!ok) { designForm.show_reviews = prev }
  else pushToast(`Las valoraciones ${designForm.show_reviews ? 'se muestran' : 'se ocultaron'} en tu web`, toggleShowReviews)
  reviewToggleBusy.value = false
}
async function toggleShowComments() {
  if (reviewToggleBusy.value || !canProductComments.value) return
  const prev = designForm.show_comments
  designForm.show_comments = !prev
  reviewToggleBusy.value = true
  const ok = await store.saveCustomization({ show_comments: designForm.show_comments })
  if (!ok) { designForm.show_comments = prev }
  else pushToast(`Los comentarios ${designForm.show_comments ? 'se muestran' : 'se ocultaron'} en tu web`, toggleShowComments)
  reviewToggleBusy.value = false
}

// ----- Opiniones recibidas (sección propia del menú: moderación, solo borrado) -----
const reviewsLoaded = ref(false)
const reviewDeleting = ref(null)
watch(section, (s) => {
  if (s === 'reviews' && canProductComments.value && !reviewsLoaded.value) {
    reviewsLoaded.value = true
    catalog.loadReviews()
  }
})
async function onDeleteReview(r) {
  if (reviewDeleting.value === r.id) return
  reviewDeleting.value = r.id
  await catalog.removeReview(r.id)
  reviewDeleting.value = null
}

// Carrusel de banners de la web pública (premium, has_design_advanced). Misma
// cuota que el logo. La vista previa rota las imágenes cada 3s como en la web real.
const previewSlide = ref(0)
let previewTimer = null
const previewReduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
const carouselInput = ref(null)
const carouselBusy = ref(false)
const carouselErr = ref('')
const carouselImages = computed(() => store.customization.carousel || [])
const designShopName = computed(() => designForm.display_name || business.value || 'Tu negocio')
// Espejo del catálogo público (se apaga desde "Mi catálogo"): la vista previa
// oculta el link, el CTA y la página Catálogo igual que la web real.
const designCatalogOn = computed(() => designForm.show_catalog !== false)
const designNameFont = computed(() => ({ fontFamily: storeFontFamily(designForm.name_font) }))

async function onCarouselPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !canDesignAdvanced.value) return
  carouselErr.value = validateImageFile(file)
  if (carouselErr.value) return
  carouselBusy.value = true
  const ok = await store.addCarouselImage(file)
  carouselBusy.value = false
  if (!ok) carouselErr.value = store.fieldErrors.image || store.fieldErrors.detail || store.lastError
}

async function onRemoveCarousel(imageId) {
  if (carouselBusy.value || !canDesignAdvanced.value) return
  carouselErr.value = ''
  carouselBusy.value = true
  const ok = await store.removeCarouselImage(imageId)
  carouselBusy.value = false
  if (!ok) carouselErr.value = store.lastError
}

async function onMoveCarousel(imageId, direction) {
  if (carouselBusy.value || !canDesignAdvanced.value) return
  carouselErr.value = ''
  carouselBusy.value = true
  const ok = await store.moveCarouselImage(imageId, direction)
  carouselBusy.value = false
  if (!ok) carouselErr.value = store.lastError
}

// Galería de la web pública: la sección la activa el dueño (show_gallery) y
// el cupo lo fija el beneficio max_gallery_images del plan (Básico 0,
// Estándar 5, Premium 15). Misma cuota de imágenes que logo y carrusel;
// borrar/reordenar sigue disponible aunque el plan baje el cupo.
const galleryInput = ref(null)
const galleryBusy = ref(false)
const galleryErr = ref('')
const galleryImages = computed(() => store.customization.gallery || [])
const decorImages = computed(() => store.customization.decor || [])
const galleryUsed = computed(() => galleryImages.value.length + decorImages.value.length)
const canAddGallery = computed(() => canGallery.value && (galleryMax.value === null || galleryUsed.value < galleryMax.value))
const canAddDecor = computed(() => canDesignAdvanced.value && decorImages.value.length < DECOR_MAX_IMAGES && canAddGallery.value)
const decorInput = ref(null)
const galleryMax = computed(() => plan.value?.benefits?.max_gallery_images)
const canGallery = computed(() => galleryMax.value === null || Number(galleryMax.value) > 0)
const galleryHint = computed(() => {
  const base = 'Se muestran como una grilla en tu web y al hacer clic se ven en grande.'
  if (!canGallery.value) return `La galería se habilita con una suscripción activa. ${base}`
  return galleryMax.value === null ? `Imágenes de hasta 4 MB. Las ajustamos automáticamente para que se vean bien. ${base}` : `Hasta ${galleryMax.value} imágenes de 4 MB entre galería e imágenes decorativas (usadas: ${galleryUsed.value}). Las ajustamos automáticamente para que se vean bien. ${base}`
})

async function onGalleryPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !canGallery.value) return
  galleryErr.value = validateImageFile(file)
  if (galleryErr.value) return
  galleryBusy.value = true
  const ok = await store.addGalleryImage(file)
  galleryBusy.value = false
  if (!ok) galleryErr.value = store.fieldErrors.image || store.fieldErrors.detail || store.lastError
}

async function onDecorPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !canAddDecor.value) return
  galleryErr.value = validateImageFile(file)
  if (galleryErr.value) return
  galleryBusy.value = true
  const ok = await store.addGalleryImage(file, 'decor')
  galleryBusy.value = false
  if (!ok) galleryErr.value = store.fieldErrors.image || store.fieldErrors.detail || store.lastError
}

async function onRemoveGallery(imageId) {
  if (galleryBusy.value) return
  galleryErr.value = ''
  galleryBusy.value = true
  const ok = await store.removeGalleryImage(imageId)
  galleryBusy.value = false
  if (!ok) galleryErr.value = store.lastError
}

async function onMoveGallery(imageId, direction) {
  if (galleryBusy.value) return
  galleryErr.value = ''
  galleryBusy.value = true
  const ok = await store.moveGalleryImage(imageId, direction)
  galleryBusy.value = false
  if (!ok) galleryErr.value = store.lastError
}

// Logo y portada de la web pública: viven en la pestaña Fotos junto con la
// galería (la pestaña Diseño solo elige estructura, estilo y tipografía).
const LOGO_ACCEPT_TYPES = LOGO_ACCEPT
const currentLogo = computed(() => store.customization.logo || '')
const currentCover = computed(() => store.customization.cover || '')
const logoInput = ref(null)
const logoBusy = ref(false)
const logoErr = ref('')
const coverInput = ref(null)
const coverBusy = ref(false)
const coverErr = ref('')

async function onLogoPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  logoErr.value = validateLogoFile(file)
  if (logoErr.value) return
  logoBusy.value = true
  const ok = await store.uploadLogo(file)
  logoBusy.value = false
  if (!ok) logoErr.value = store.fieldErrors.logo || store.lastError
}

async function onRemoveLogo() {
  if (logoBusy.value) return
  logoErr.value = ''
  logoBusy.value = true
  const ok = await store.removeLogo()
  logoBusy.value = false
  if (!ok) logoErr.value = store.fieldErrors.logo || store.lastError
}

async function onCoverPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !canDesignAdvanced.value) return
  coverErr.value = validateImageFile(file)
  if (coverErr.value) return
  coverBusy.value = true
  const ok = await store.uploadCover(file)
  coverBusy.value = false
  if (!ok) coverErr.value = store.fieldErrors.cover || store.fieldErrors.detail || store.lastError
}

async function onRemoveCover() {
  if (coverBusy.value || !canDesignAdvanced.value) return
  coverErr.value = ''
  coverBusy.value = true
  const ok = await store.removeCover()
  coverBusy.value = false
  if (!ok) coverErr.value = store.fieldErrors.cover || store.fieldErrors.detail || store.lastError
}

onMounted(async () => {
  // Puente entre pestañas: el retorno de MP cae en la pestaña del checkout,
  // esta escucha avisa a la pestaña original para acreditar al instante.
  window.addEventListener('storage', onPaymentBroadcast)
  // Todo en paralelo: ninguna lectura del panel depende de otra. El perfil ya
  // llegó por el guard del router; este refetch actualiza los flags de
  // verificación y alimenta el formulario de Cuenta sin frenar el resto.
  auth.fetchMe().then(() => fillAccountForm())
  loadAccountProvinces()
  const storeReady = store.status === 'idle' ? store.loadMine() : Promise.resolve()
  // Vía rápida: plan + tienda destraban stats, la precarga del catálogo y el
  // retorno de MP sin esperar a los listados de pagos/facturas (los stores
  // SWR ya pintan con la data cacheada mientras revalidan).
  const fastLane = Promise.all([billing.loadPlans(), billing.loadMine(), storeReady]).then(async () => {
    if (canStats.value) store.loadStats()
    // Precarga silenciosa del catálogo para los próximos pasos del resumen.
    ensureCatalog()
    // La última opinión alimenta el feed de actividad del Inicio.
    if (canProductComments.value && !reviewsLoaded.value) { reviewsLoaded.value = true; catalog.loadReviews() }
    // Retorno del checkout (trae payment_id en la URL): es la vía instantánea.
    await handlePaymentReturn()
  })
  await Promise.allSettled([fastLane, payments.loadPayments(), invoices.loadInvoices()])
  // Aviso de una ruta exclusiva bloqueada (ej. Studio sin has_design_advanced).
  if (route.query.locked) {
    const { locked, ...rest } = route.query
    fastLane.then(() => openLocked(String(locked)))
    router.replace({ query: rest })
  }
  // Red de seguridad en segundo plano (registra pagos ya acreditados en MP
  // que aún no estén en el sistema): el barrido contra la API de MP tarda
  // ~1s, así que ya no se espera — el backend además lo acota a uno cada
  // 15s por usuario, así re-entradas al panel no repiden el barrido.
  payments.sync().then(async (synced) => {
    if (synced > 0) await Promise.all([billing.loadMine(), payments.loadPayments()])
  })
  // Tour de primera vez: se muestra una sola vez por dispositivo y se
  // relanza desde "Repetir la guía" en el menú.
  try {
    if (localStorage.getItem('davent:tour:done') !== '1') setTimeout(() => { tourOpen.value = true }, 900)
  } catch {}
})

watch(() => carouselImages.value.length, (total) => {
  previewSlide.value = 0
  clearInterval(previewTimer)
  previewTimer = null
  if (total > 1 && !previewReduceMotion) {
    previewTimer = setInterval(() => { previewSlide.value = (previewSlide.value + 1) % carouselImages.value.length }, 3000)
  }
})

// --- Ayuda: chat de soporte con el equipo (premium — polling + heartbeat) ---
const chatMessages = ref([])
const chatInput = ref('')
const chatBusy = ref(false)
const chatErr = ref('')
const chatStaffOnline = ref(false)
const chatLastId = ref(0)
const chatBoxEl = ref(null)
const chatInputEl = ref(null)
const chatStaff = ref([])
const chatOpen = ref(false)
const chatMin = ref(false)
const chatUnread = ref(0)
const chatTarget = ref(null)
// Adjuntos en cola: [{file, url}] — el url es un objectURL local (vista
// previa optimista); el archivo nunca toca la DB, viaja al bucket/disco.
const chatFiles = ref([])
const chatFileInput = ref(null)
const CHAT_FILES_MAX = 4
const chatOnlineCount = computed(() => chatStaff.value.filter((s) => s.online).length)
// El chat (heartbeat incluido) solo corre con el beneficio del plan; el
// asistente automático queda disponible para cualquier cuenta como contacto.
const canChat = computed(() => Boolean(plan.value?.benefits?.has_support_chat))
// El asistente figura como un integrante más del equipo de soporte: es un
// contacto local (respuestas automáticas, nunca toca la API del chat).
const BOT_MEMBER = { id: 'bot', name: 'Asistente de diseño', online: true, bot: true }
const chatContacts = computed(() => canChat.value ? [BOT_MEMBER, ...chatStaff.value] : [BOT_MEMBER])
const botMode = computed(() => Boolean(chatTarget.value?.bot))
// Panel de contactos que abre la burbuja flotante.
const chatDockPanel = ref(false)
const chatDockContent = computed(() => (chatOpen.value ? 'win' : chatDockPanel.value ? 'panel' : null))
//El objetivo del chat se resuelve contra el roster vivo: si cambia su
//presencia, el header refleja el estado nuevo sin reabrir la ventana.
const chatPeer = computed(() => {
  if (!chatTarget.value) return null
  return chatStaff.value.find((s) => s.id === chatTarget.value.id) || chatTarget.value
})
let chatPollTimer = null
let chatBeatTimer = null

function staffInitials(name) {
  const p = String(name || '?').trim().split(/\s+/)
  return ((p[0]?.[0] || '?') + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase()
}

function resizeChatInput() {
  const el = chatInputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 132) + 'px'
}

function onChatKey(e) {
  if (e.key !== 'Escape') return
  if (chatOpen.value) closeChat()
  if (chatDockPanel.value) chatDockPanel.value = false
}

// Alterna lo que tenga abierto la burbuja: si hay panel/ventana visible los
// cierra; si no, abre la lista de contactos.
function onDockToggle() {
  if (chatDockPanel.value) { chatDockPanel.value = false; return }
  if (chatOpen.value) { closeChat(); return }
  chatDockPanel.value = true
  if (canChat.value) beatChat() // roster fresco al abrir los contactos
}

// La campana del topbar abre la conversación de una: el hilo con el equipo
// si el plan lo habilita, si no, el asistente automático.
function onBellClick() {
  if (chatOpen.value) { closeChat(); return }
  openChat(canChat.value ? null : BOT_MEMBER)
}

function openChat(member = null) {
  chatTarget.value = member
  chatOpen.value = true
  chatMin.value = false
  chatDockPanel.value = false
  window.addEventListener('keydown', onChatKey)
  if (member?.bot) {
    // Conversación local con el asistente: no hay hilo en el servidor ni
    // lectura que marcar — el saludo se agrega la primera vez.
    resetChatFiles()
    if (!botMsgs.value.length) botPush(false, BOT_GREETING)
    nextTick(() => {
      scrollChat()
      resizeChatInput()
      chatInputEl.value?.focus({ preventScroll: true })
    })
    return
  }
  if (!canChat.value) { openChat(BOT_MEMBER); return }
  // Al abrir se trae el historial: el GET marca los mensajes del staff
  // como leídos (por eso solo corre con la ventana abierta).
  loadChat()
  nextTick(() => {
    scrollChat()
    resizeChatInput()
    chatInputEl.value?.focus({ preventScroll: true })
  })
}

function toggleChatMin() {
  chatMin.value = !chatMin.value
  if (!chatMin.value) {
    // Al expandir se retoma el polling (pausado minimizada): lo que llegó
    // en el medio todavía no quedó marcado como leído en el servidor.
    pollChat()
    nextTick(() => {
      scrollChat()
      chatInputEl.value?.focus({ preventScroll: true })
    })
  }
}

function closeChat() {
  chatOpen.value = false
  chatMin.value = false
  resetChatFiles()
  window.removeEventListener('keydown', onChatKey)
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
  e.target.value = '' // mismo archivo dos veces = mismo change
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

function onComposerEnter(e) {
  if (e.shiftKey) return
  e.preventDefault()
  sendChat()
}

function contactStaff(s) {
  openChat(s)
}

function requestLiveHelp() {
  //Abre la ventana con el mensaje precargado — nada se envía solo: el
  //cliente revisa el texto y lo manda con Enter o el botón.
  openChat(chatStaff.value.find((s) => s.online) || null)
  if (!chatInput.value.trim()) {
    chatInput.value = 'Hola, necesito asistencia en vivo, ¿pueden ayudarme?'
    nextTick(resizeChatInput)
  }
}

function scrollChat() {
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
  const today = new Date()
  const sameDay = d.toDateString() === today.toDateString()
  return sameDay
    ? d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}

async function loadChat() {
  try {
    const data = await fetchChat()
    chatStaffOnline.value = Boolean(data.staff_online)
    chatStaff.value = data.staff || []
    chatUnread.value = data.unread || 0
    const msgs = data.messages || []
    chatMessages.value = msgs
    chatLastId.value = msgs.length ? msgs[msgs.length - 1].id : 0
    chatErr.value = ''
    await nextTick()
    scrollChat()
  } catch (e) { chatErr.value = extractApiError(e).nonField }
}

let chatPolling = false

async function pollChat() {
  // Silencioso: un tick fallido reintenta en el próximo intervalo.
  // Oculto no se pollea (ahorra cuota; al volver hay tick inmediato) y nunca
  // se enciman dos requests si una tardó más que el intervalo.
  // Ventana cerrada o minimizada tampoco se pollea: el GET marca los
  // mensajes del staff como leídos y el cliente todavía no los vio —
  // el no-leído sigue contando por el heartbeat (badge en el header).
  if (!chatOpen.value || chatMin.value || botMode.value || document.hidden || chatPolling) return
  chatPolling = true
  try {
    const data = await fetchChatMessages({ after: chatLastId.value })
    // Dedupe por id: un send optimista o un poll encimado ya pudo traer el
    // mensaje — sin el filtro se vería dos veces hasta el próximo refetch.
    const fresh = (data.messages || []).filter((m) => !chatMessages.value.some((x) => x.id === m.id))
    if (fresh.length) {
      chatMessages.value = [...chatMessages.value, ...fresh]
      chatLastId.value = fresh[fresh.length - 1].id
      await nextTick()
      scrollChat()
    }
  } catch { /* reintenta el próximo tick */ }
  finally { chatPolling = false }
}

async function beatChat() {
  try {
    const data = await chatHeartbeat()
    chatStaffOnline.value = Boolean(data.staff_online)
    if (data.staff) chatStaff.value = data.staff
    // El no-leído llega por heartbeat (no marca lectura): con la ventana
    // cerrada/minimizada es el contador del badge; abierta queda en 0
    // porque el polling ya marcó todo como leído.
    chatUnread.value = data.unread || 0
  } catch { /* silencioso */ }
}

async function sendChat() {
  if (botMode.value) { sendBotChat(); return }
  const body = chatInput.value.trim()
  const files = chatFiles.value
  if ((!body && !files.length) || chatBusy.value) return
  chatBusy.value = true
  chatErr.value = ''
  chatFiles.value = [] // los objectURL mueren con la fila de previews
  // Optimista: el texto + una burbuja por imagen aparecen al instante como
  // pendientes y se reemplazan por los reales; si un POST falla se quitan
  // los que quedaron sin confirmar y se restaura el input.
  const mkTmp = (extra = {}) => ({
    id: `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    mine: true, sender_name: 'Vos', pending: true, created_at: new Date().toISOString(), ...extra
  })
  const tmps = []
  if (body) tmps.push(mkTmp({ body }))
  files.forEach((f) => tmps.push(mkTmp({ body: '', image_url: f.url })))
  chatMessages.value = [...chatMessages.value, ...tmps]
  chatInput.value = ''
  await nextTick()
  scrollChat()
  resizeChatInput()
  try {
    let i = 0
    if (body) {
      const { message } = await sendChatMessage(body)
      chatMessages.value = chatMessages.value.filter((m) => m.id !== tmps[i].id && m.id !== message.id).concat(message)
      chatLastId.value = Math.max(chatLastId.value, message.id)
      i++
    }
    for (const f of files) {
      const { message } = await sendChatMessage('', null, f.file)
      chatMessages.value = chatMessages.value.filter((m) => m.id !== tmps[i].id && m.id !== message.id).concat(message)
      chatLastId.value = Math.max(chatLastId.value, message.id)
      i++
    }
    files.forEach((f) => URL.revokeObjectURL(f.url)) // enviados: previews fuera
    pollChat() // recoge al instante cualquier respuesta que haya llegado en el medio
  } catch (e) {
    // Los tmps aún pendientes (índice >= i) se retiran; los enviados quedan.
    const stuck = new Set(tmps.slice(i).map((t) => t.id))
    chatMessages.value = chatMessages.value.filter((m) => !stuck.has(m.id))
    chatFiles.value = files // los adjuntos vuelven a la cola para reintentar
    chatInput.value = body
    await nextTick()
    resizeChatInput()
    chatErr.value = extractApiError(e).nonField
  } finally {
    chatBusy.value = false
    chatInputEl.value?.focus({ preventScroll: true })
  }
}

// --- Asistente automático (contacto del equipo, respuestas locales) ---
// Mismas respuestas que tenía el SupportBot en modo panel: temas sugeridos
// + texto libre matcheado por keywords. Todo local, sin API.
const PANEL_TOPICS = [
  { id: 'sub', label: 'Mi suscripción', kw: 'suscripcion plan dias restantes vencida vigente' },
  { id: 'link', label: 'Mi link público', kw: 'link url publico direccion dominio slug web' },
  { id: 'products', label: 'Cargar productos', kw: 'productos producto catalogo cargar subir categorias marcas fotos' },
  { id: 'design', label: 'Diseño de mi web', kw: 'diseno logo color fuente carrusel personalizar portada' },
  { id: 'renew', label: 'Renovación del plan', kw: 'renovacion renovar debito automatico vencimiento' },
  { id: 'invoices', label: 'Pagos y facturas', kw: 'facturas factura pagos comprobantes historial cobros' }
]
const BOT_GREETING = 'Hola, soy el asistente de DAVENT. Elegí un tema o escribime tu consulta y te explico cómo funciona.'
const BOT_FALLBACK = 'No tengo una respuesta automática para eso. Probá con alguna de las preguntas sugeridas — o escribí al equipo de soporte, que responde a la brevedad.'
const botMsgs = ref([])
const botTyping = ref(false)
const botAsked = ref(new Set())
let botSeq = 0
// Temas todavía no preguntados: se ofrecen como mensajes sugeridos en el chat.
const botPending = computed(() => PANEL_TOPICS.filter((t) => !botAsked.value.has(t.id)))

function panelAnswer(id) {
  const p = plan.value
  switch (id) {
    case 'sub': {
      if (!p) return 'Todavía no tenés una suscripción activa. En la sección Planes elegís el que mejor te quede y se activa cuando se acredita el pago.'
      const parts = [`Tu plan actual es ${p.name}.`]
      if (p.remaining != null) parts.push(`Te quedan ${p.remaining} días.`)
      if (p.autoRenew) parts.push('El débito automático está activo: se renueva solo cada mes.')
      else if (p.cancelledAt) parts.push('La renovación automática está desactivada: al terminar el período vas a tener que pagar de nuevo.')
      const pending = billing.subscription?.pending_plan_name
      if (pending) parts.push(`Tenés un cambio a ${pending} pendiente.`)
      if (!p.isCurrent) parts.push('Ojo: tu suscripción está vencida. En Planes podés reactivarla.')
      return parts.join(' ')
    }
    case 'link': {
      const s = store.store
      if (!s) return 'Todavía no reservaste tu link público.'
      const state = s.is_published ? 'Está activo.' : 'Está pausado: podés reactivarlo desde "Mi tienda".'
      return `Tu link público es ${publicStoreUrl(s.slug)} — ese es el que compartís con tus clientes. ${state}`
    }
    case 'products':
      return 'En "Mis catálogos" cargás productos con foto, nombre, precio, categoría y marca. Todo lo que publiques aparece al instante en tu web pública. Las categorías y marcas se crean en las pestañas de ese mismo panel.'
    case 'design': {
      const b = p?.benefits || {}
      const mapa = b.has_location_map ? ', el mapa de ubicación' : ''
      if (b.has_design_advanced) return 'En "Diseño web" personalizás todo: logo, nombre, titular, descripción, tema, color de acento, fuente y tamaño del nombre, carrusel de portada, mapa de ubicación y botones de WhatsApp y redes.'
      if (b.has_customization) return `En "Diseño web" personalizás el logo, el nombre, el titular, la descripción, el tema claro/oscuro${mapa} y los botones de WhatsApp y redes. El color de acento, la fuente y el carrusel de portada se habilitan con el Plan premium.`
      return 'Con una suscripción activa podés personalizar el diseño de tu web (logo, textos, tema y botones de contacto). El color de acento, las fuentes y el carrusel son del Plan premium. En "Planes" elegís el que mejor te quede.'
    }
    case 'renew':
      return 'Podés pagar cada mes a mano desde "Planes", o activar el débito automático con Mercado Pago y el plan se renueva solo. Si un débito falla, Mercado Pago reintenta durante unos días y tu plan sigue activo mientras tanto.'
    case 'invoices':
      return 'En "Pagos" ves el historial de cobros con su estado; en "Facturas" están los comprobantes de cada pago acreditado, listos para imprimir o bajar en PDF.'
    default:
      return ''
  }
}

const normChatText = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')

// Matching del texto libre contra etiqueta + keywords del tema (mismo
// criterio que el SupportBot: exacto > inclusión > solape de palabras >3).
function findBotTopic(text) {
  const t = normChatText(text)
  if (!t) return null
  let best = null
  let score = 0
  for (const topic of PANEL_TOPICS) {
    const q = normChatText(`${topic.label} ${topic.kw}`)
    let s = 0
    if (t === normChatText(topic.label)) s += 20
    else if (t.length > 3 && q.includes(t)) s += 6
    for (const w of q.split(/[^a-z0-9ñ]+/).filter((w) => w.length > 3)) {
      if (t.includes(w)) s += 2
    }
    if (s > score) { score = s; best = topic }
  }
  return score >= 3 ? best : null
}

function botPush(mine, body) {
  botMsgs.value.push({
    id: `bot-${++botSeq}`, mine, bot: !mine,
    sender_name: mine ? 'Vos' : BOT_MEMBER.name,
    body, created_at: new Date().toISOString()
  })
  nextTick(scrollChat)
}

function botAnswer(topicId) {
  botAsked.value = new Set([...botAsked.value, topicId])
  botPush(false, panelAnswer(topicId))
}

function selectBotTopic(t) {
  if (botTyping.value) return
  botPush(true, t.label)
  botTyping.value = true
  // Pausa breve de "escribiendo…" como en el asistente de las tiendas.
  window.setTimeout(() => { botTyping.value = false; botAnswer(t.id) }, 450)
}

function sendBotChat() {
  const text = chatInput.value.trim()
  if (!text || botTyping.value) return
  chatInput.value = ''
  nextTick(resizeChatInput)
  botPush(true, text.slice(0, 2000))
  botTyping.value = true
  window.setTimeout(() => {
    botTyping.value = false
    const topic = findBotTopic(text)
    if (topic) botAnswer(topic.id)
    else botPush(false, BOT_FALLBACK)
  }, 450)
}

// ~2.5s de poll: latencia media de ~1.2s contra ~2.5s antes. El throttle
// del scope 'chat' (5000/h) cubre este ritmo en ambos lados.
const CHAT_POLL_MS = 2500
const CHAT_BEAT_MS = 45000

function startChat() {
  stopChat()
  beatChat()
  // Si la ventana quedó abierta al cambiar de sección, se refresca el
  // hilo; si no, alcanza con el heartbeat (marca presencia + no-leídos).
  if (chatOpen.value && !botMode.value) loadChat()
  chatPollTimer = setInterval(pollChat, CHAT_POLL_MS)
  chatBeatTimer = setInterval(beatChat, CHAT_BEAT_MS)
}

function stopChat() {
  clearInterval(chatPollTimer)
  clearInterval(chatBeatTimer)
  chatPollTimer = null
  chatBeatTimer = null
}

// Presencia siempre activa mientras el panel está montado: el usuario figura
// "en línea" para el staff (y ve al staff conectado) sin entrar a Soporte.
// Sin el beneficio solo queda el asistente local — el heartbeat daría 403.
watch(canChat, (on) => {
  if (on) startChat()
  else { stopChat(); if (chatOpen.value && !botMode.value) closeChat() }
}, { immediate: true })

// Al volver al tab: tick inmediato (los intervals no corrían con la pestaña
// oculta) — el usuario ve los mensajes nuevos sin esperar al próximo ciclo.
function onChatVisible() {
  if (document.visibilityState === 'visible' && canChat.value) {
    pollChat()
    beatChat()
  }
}

// Sesión expirada (refresh 401): cortar polling y heartbeat — si no, cada
// 45s se reintentaba el heartbeat contra un access muerto (401 en consola).
function onChatSessionExpired() { stopChat() }

onMounted(() => {
  document.addEventListener('visibilitychange', onChatVisible)
  window.addEventListener('davent:session-expired', onChatSessionExpired)
})

onUnmounted(() => {
  stopCheckoutWatch()
  stopChat()
  closeChat()
  window.removeEventListener('davent:session-expired', onChatSessionExpired)
  clearInterval(previewTimer)
  window.removeEventListener('storage', onPaymentBroadcast)
  document.removeEventListener('visibilitychange', onChatVisible)
})

// La pestaña del checkout avisa por acá cuando vuelve de Mercado Pago.
async function onPaymentBroadcast(event) {
  if (event.key !== 'davent:last-payment' || !event.newValue) return
  let payload = null
  try { payload = JSON.parse(event.newValue) } catch { return }
  if (payload?.sub) {
    // Retorno de la autorización del débito automático en la otra pestaña.
    await payments.sync()
    await billing.loadMine()
    if (billing.subscription?.auto_renew) {
      showRenewalActivated()
      stopCheckoutWatch()
    }
    return
  }
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

function broadcastSubReturn() {
  try {
    localStorage.setItem('davent:last-payment', JSON.stringify({ sub: true, at: Date.now() }))
  } catch {
    // Si el navegador bloquea el storage, la pestaña original sigue con el polling.
  }
}

// Retorno de Mercado Pago (Checkout Pro): back_urls -> /dashboard?pay=...&payment_id=...
async function handlePaymentReturn() {
  const q = route.query
  if (q.sub === 'return') {
    // Retorno de la autorización del débito automático (preapproval).
    broadcastSubReturn()
    await handleSubscriptionReturn()
    router.replace({ name: 'dashboard' })
    return
  }
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

// Retorno de Mercado Pago (débito automático): back_url -> /dashboard?sub=return
async function handleSubscriptionReturn() {
  await payments.sync()
  await billing.loadMine()
  if (billing.subscription?.auto_renew) {
    showRenewalActivated()
  } else {
    billing.notice = 'Estoy confirmando la autorización del débito automático con Mercado Pago.'
    startRenewalWatch()
  }
}

// Pago acreditado: lleva al Resumen con el plan ya actualizado.
function showPlanActivated() {
  section.value = 'overview'
  billing.notice = 'Tu pago se acreditó y tu plan ya está activo.'
  payments.notice = ''
}

// Débito automático autorizado: lleva al Resumen con la renovación activa.
function showRenewalActivated() {
  section.value = 'overview'
  billing.notice = 'Débito automático activado: tu plan se renueva solo cada mes.'
  payments.notice = ''
}

// --- Datos de facturación (se piden recién al iniciar un cobro) ---
// El backend responde 400 billing_required cuando falta info fiscal: se abre
// este form (mismo accountForm de Cuenta) y, al guardar, se reintenta la acción.
const needsBilling = ref(false)
const billingRetry = ref(null) // {kind:'plan', plan} | {kind:'renew'}
const billingBusy = ref(false)

function openBilling(retry) {
  billingRetry.value = retry
  needsBilling.value = true
  payments.lastError = ''
  //El form vive en la sección Planes: si el cobro salió de otra (ej. el
  //débito automático del Resumen) llevamos al usuario hasta él.
  section.value = 'plans'
  if (!provinces.value.length) loadAccountProvinces()
  fillAccountForm()
}

function closeBilling() {
  needsBilling.value = false
  billingRetry.value = null
}

async function saveBilling() {
  Object.keys(accountForm).forEach((k) => { accountTouched[k] = true })
  billing.lastError = ''
  if (Object.keys(accountErrors.value).length) return
  billingBusy.value = true
  try {
    const res = await auth.updateAccount({
      email: accountForm.email.trim() || auth.user?.email,
      profile: {
        first_name: accountForm.first_name.trim(),
        last_name: accountForm.last_name.trim(),
        tax_condition: accountForm.tax_condition,
        business_name: accountForm.business_name.trim() || null,
        document: accountForm.document.trim() || null,
        province: Number(accountForm.province),
        city: Number(accountForm.city),
        address: accountForm.address.trim() || null,
        phone: accountForm.phone.trim() || null
      }
    })
    if (!res.ok) {
      billing.lastError = auth.lastError || 'No se pudieron guardar tus datos de facturación.'
      return
    }
    await fillAccountForm()
    needsBilling.value = false
    billing.notice = 'Datos de facturación guardados. Retomando tu pago…'
    const retry = billingRetry.value
    billingRetry.value = null
    if (retry?.kind === 'plan') await planAction(retry.plan)
    else if (retry?.kind === 'renew') await activateAutoRenew()
  } finally {
    billingBusy.value = false
  }
}

async function planAction(p) {
  if (p.is_trial) return // plan de prueba: informativo, no se puede elegir
  busyPlan.value = p.id
  billing.lastError = ''
  billing.notice = ''
  payments.lastError = ''
  payments.notice = ''
  // La pestaña se abre dentro del gesto del usuario para que el navegador no la bloquee.
  const checkoutTab = window.open('about:blank', '_blank')
  try {
    if (billing.subscription?.auto_renew) {
      // Con débito automático activo, el cambio de plan se aplica en el próximo débito mensual.
      const data = await payments.subscribeAuto({ suscription: billing.subscription.id, planPk: p.id })
      if (data?.auto_renew) {
        checkoutTab?.close()
        await billing.loadMine()
        billing.notice = `Cambio a ${p.name} programado: se aplica con el próximo débito automático.`
        return
      }
      const renewUrl = data?.checkout_url || data?.init_point || data?.sandbox_init_point
      if (!renewUrl) {
        checkoutTab?.close()
        if (payments.billingRequired.length) openBilling({ kind: 'plan', plan: p })
        return
      }
      checkoutTab.location.href = renewUrl
      billing.notice = 'Abrimos Mercado Pago en otra pestaña para autorizar el débito automático.'
      startRenewalWatch()
      return
    }
    // Todos los planes son pagos: la suscripción se establece cuando el pago se acredita.
    const url = await payments.checkout({ suscription: billing.subscription?.id ?? null, planPk: p.id })
    if (!url) {
      checkoutTab?.close()
      if (payments.billingRequired.length) openBilling({ kind: 'plan', plan: p })
      return
    }
    checkoutTab.location.href = url
    billing.notice = 'Abrimos Mercado Pago en otra pestaña. Cuando el pago se acredite, tu plan se activa solo.'
    startCheckoutWatch(p.id)
  } finally {
    busyPlan.value = null
  }
}

// Canje de cupón promocional (sección Planes): el backend pisa la suscripción
// con el plan del cupón por coupon.days días.
async function redeemCoupon() {
  const code = couponCode.value.trim()
  if (!code || couponBusy.value) return
  couponBusy.value = true
  try {
    const ok = await billing.redeemCoupon(code)
    if (ok) couponCode.value = ''
  } finally {
    couponBusy.value = false
  }
}

// Alta del débito automático (MP preapproval): la autorización se hace en la pestaña de MP.
async function activateAutoRenew() {
  if (renewBusy.value) return
  renewBusy.value = true
  billing.lastError = ''
  billing.notice = ''
  payments.lastError = ''
  payments.notice = ''
  const tab = window.open('about:blank', '_blank')
  try {
    const data = await payments.subscribeAuto({ suscription: billing.subscription?.id ?? null, planPk: plan.value?.pk })
    if (data?.auto_renew) {
      tab?.close()
      await billing.loadMine()
      showRenewalActivated()
      return
    }
    const url = data?.checkout_url || data?.init_point || data?.sandbox_init_point
    if (!url) {
      tab?.close()
      if (payments.billingRequired.length) openBilling({ kind: 'renew' })
      return
    }
    tab.location.href = url
    billing.notice = 'Abrimos Mercado Pago en otra pestaña para autorizar el débito automático.'
    startRenewalWatch()
  } finally {
    renewBusy.value = false
  }
}

// Baja del débito automático: el plan sigue vigente hasta el fin del período pago.
async function doCancelRenewal() {
  if (renewBusy.value) return
  renewBusy.value = true
  const ok = await payments.cancelRenewal()
  renewBusy.value = false
  if (ok) {
    confirmCancel.value = false
    await billing.loadMine()
    billing.notice = payments.notice
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

// Polling a /payments/sync/: sincroniza también el preapproval; se corta cuando
// MP marca el débito como autorizado (auto_renew).
function startRenewalWatch() {
  stopCheckoutWatch()
  let tries = 0
  checkoutWatch = setInterval(async () => {
    tries += 1
    try {
      await payments.sync()
      await billing.loadMine()
      if (billing.subscription?.auto_renew) {
        stopCheckoutWatch()
        showRenewalActivated()
        return
      }
      if (tries >= 36) {
        stopCheckoutWatch()
        billing.notice = 'Seguimos esperando la autorización de Mercado Pago. Si ya la completaste, recargá la página.'
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

async function logout() {
  billing.reset()
  payments.reset()
  invoices.reset()
  store.reset()
  catalog.reset()
  // Esperar al logout: si el push corre con el request en vuelo, la cookie
  // de refresh sigue viva y ensureSession puede revivir la sesión.
  await auth.logout()
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
    :active="navActive"
    :items="navItems"
    :tabs="mobileTabs"
    :parent="navParent"
    :title="sectionTitle"
    :plan-name="plan?.name || ''"
    :user-name="displayName"
    :initial="initial"
    @navigate="onNavigate"
    @locked="onLockedNav"
    @search="searchOpen = true"
    @messages="onBellClick"
    @tour="tourOpen = true"
    @logout="logout"
  >
    <template #topbar-actions>
      <!-- Campana de mensajería: punto verde = equipo en línea, badge = no
           leídos. Abre la conversación directa (o el asistente si el plan
           no habilita el chat con el staff). -->
      <button
        type="button"
        class="top-bell"
        :aria-label="chatOpen ? 'Cerrar mensajes' : 'Abrir mensajes'"
        title="Mensajes"
        :aria-expanded="chatOpen"
        @click="onBellClick"
      >
        <AppIcon name="bell" :size="19" />
        <span class="bell-status" :class="{ on: chatStaffOnline }" aria-hidden="true"></span>
        <span v-if="chatUnread" class="chat-badge bell-badge">{{ chatUnread > 99 ? '99+' : chatUnread }}</span>
      </button>
    </template>

    <!-- Banner global: correo sin verificar (bloquea crear la web pública) -->
    <div v-if="needsEmailVerification" class="cta-banner">
      <div>
        <strong>Verificá tu correo electrónico.</strong><br />
        Te enviamos un enlace a {{ auth.user?.email }}. Hasta confirmarlo no podés crear tu web pública.
      </div>
      <button class="btn light btn-auto" :disabled="verifyBusy" @click="resendVerification">
        <span v-if="verifyBusy" class="spinner"></span>Reenviar correo
      </button>
    </div>
    <AlertMessage v-if="verifyMsg" kind="success" :message="verifyMsg" />
    <AlertMessage v-if="verifyErr" kind="error" :message="verifyErr" />

    <!-- ================= RESUMEN ================= -->
    <div v-show="section === 'overview'" :class="{ 'sec-on': section === 'overview' }">
      <div class="page-head ov-head">
        <div>
          <h1>{{ greeting }}<template v-if="business">, <span class="ov-name">{{ business }}</span></template></h1>
          <p>{{ firstRun ? 'Este es tu panel: acá vas a ver tu web, tus productos y tus visitas. Empecemos.' : 'Tu negocio, de un vistazo.' }}</p>
        </div>
        <div v-if="billing.hasSubscription && store.hasStore" class="ov-actions">
          <button class="btn btn-auto" @click="section = 'design'"><AppIcon name="palette" :size="16" /> Editar mi web</button>
          <a class="btn secondary btn-auto" :href="publicUrl" target="_blank" rel="noopener"><AppIcon name="external-link" :size="16" /> Ver mi tienda</a>
        </div>
      </div>

      <!-- Franja de plan compacta: estado de la suscripción de un vistazo,
           sin robarle el primer viewport a "Tu negocio hoy". -->
      <div v-if="plan" class="plan-strip">
        <span class="ps-dot" :class="{ ok: plan.isCurrent, warn: plan.status === 'Pendiente de pago', bad: !plan.isCurrent && plan.status !== 'Pendiente de pago' }" aria-hidden="true"></span>
        <span class="ps-name">{{ plan.name }}</span>
        <span class="ps-meta">
          <template v-if="plan.isCurrent">{{ plan.autoRenew ? `Se renueva solo el ${fmtDate(plan.end)}` : `Quedan ${plan.remaining} ${plan.remaining === 1 ? 'día' : 'días'} · vence el ${fmtDate(plan.end)}` }}</template>
          <template v-else>{{ plan.status }}</template>
        </span>
        <span class="ps-bar" role="progressbar" aria-label="Tiempo transcurrido de la suscripción" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="planProgress"><span :style="{ transform: `scaleX(${planProgress / 100})` }"></span></span>
        <span class="ps-actions">
          <button v-if="plan.autoRenew" type="button" class="chip-btn" @click="confirmCancel = true">Cancelar débito</button>
          <button v-else-if="!plan.isTrial && plan.isCurrent" type="button" class="chip-btn" :disabled="renewBusy" @click="activateAutoRenew"><AppIcon name="refresh" :size="13" /> Activar débito</button>
          <TipHint v-if="plan.isCurrent" text="Débito automático: Mercado Pago te cobra el plan solo cada mes, sin que tengas que acordarte. Podés darlo de baja cuando quieras." />
          <button type="button" class="chip-btn strong" @click="section = 'plans'">{{ plan.isTrial ? 'Ver planes' : 'Cambiar plan' }}</button>
        </span>
      </div>

      <div v-if="confirmCancel" class="card confirm-card">
        <h3><AppIcon name="triangle-alert" :size="18" /> Cancelar la renovación automática</h3>
        <p>Vas a dejar de pagar el débito mensual. Tu plan sigue vigente hasta el <strong>{{ fmtDate(plan?.end) }}</strong>; después tu web pública y tu catálogo se desactivan. Podés reactivar el débito cuando quieras.</p>
        <div class="btn-row">
          <button class="btn danger btn-auto" :disabled="renewBusy" @click="doCancelRenewal"><span v-if="renewBusy" class="spinner"></span>Sí, cancelar la renovación</button>
          <button class="btn ghost btn-auto" :disabled="renewBusy" @click="confirmCancel = false">Mantener activa</button>
        </div>
      </div>

      <!-- Cola de alertas: una franja con lo más urgente; el resto se despliega. -->
      <div v-if="topAlert" class="aq" :class="`a-${topAlert.kind}`">
        <div class="aq-main" role="alert">
          <AppIcon :name="alertIcon(topAlert.kind)" :size="18" class="aq-icon" />
          <div class="aq-body"><strong>{{ topAlert.title }}</strong><span>{{ topAlert.text }}</span></div>
          <button v-if="topAlert.cta" type="button" class="chip-btn strong" @click="topAlert.run">{{ topAlert.cta }}</button>
          <button v-if="extraAlerts.length" type="button" class="aq-more" :aria-expanded="alertsOpen" @click="alertsOpen = !alertsOpen">
            {{ extraAlerts.length === 1 ? '1 más' : `${extraAlerts.length} más` }}<AppIcon :name="alertsOpen ? 'chevron-up' : 'chevron-down'" :size="14" />
          </button>
        </div>
        <div v-if="alertsOpen" class="aq-list">
          <div v-for="a in extraAlerts" :key="a.id" class="aq-row" :class="`a-${a.kind}`">
            <AppIcon :name="alertIcon(a.kind)" :size="16" class="aq-icon" />
            <div class="aq-body"><strong>{{ a.title }}</strong><span>{{ a.text }}</span></div>
            <button v-if="a.cta" type="button" class="chip-btn" @click="a.run">{{ a.cta }}</button>
          </div>
        </div>
      </div>

      <div v-if="billing.status === 'loading' && !plan" class="skel-hero" aria-busy="true" aria-label="Cargando tu suscripción">
        <span class="skel" style="width: 120px; height: 12px"></span>
        <span class="skel" style="width: 220px; height: 30px"></span>
        <span class="skel" style="width: 60%; height: 12px"></span>
        <span class="skel" style="width: 100%; max-width: 420px; height: 6px"></span>
      </div>
      <AlertMessage v-if="billing.notice" kind="success" :message="billing.notice" />
      <AlertMessage v-if="billing.lastError" kind="error" :message="billing.lastError" />
      <AlertMessage v-if="payments.notice" kind="success" :message="payments.notice" />
      <AlertMessage v-if="payments.lastError" kind="error" :message="payments.lastError" />

      <div class="today" :class="{ 'first-run': firstRun }">
        <!-- Una sola decisión principal: el próximo paso de la puesta en marcha -->
        <div class="card next-do" :class="{ 'first-run': firstRun }">
          <span class="next-do-tag"><AppIcon name="sparkles" :size="13" /> {{ firstRun ? 'Bienvenido a DAVENT' : 'Qué hacer ahora' }}</span>
          <template v-if="firstRun">
            <h2>Tu tienda online, en tres pasos</h2>
            <p>Reservá tu link, elegí un plan y cargá tus primeros productos. Te acompañamos en cada paso y podés volver a esta guía cuando quieras.</p>
            <ol class="first-steps">
              <li v-for="(s, i) in welcomeSteps" :key="s.title" :class="{ done: s.done }">
                <span class="first-steps-num" aria-hidden="true">
                  <AppIcon v-if="s.done" name="check" :size="13" />
                  <template v-else>{{ i + 1 }}</template>
                </span>
                <span class="first-steps-txt"><strong>{{ s.title }}</strong><small>{{ s.text }}</small></span>
              </li>
            </ol>
            <div class="first-cta">
              <button type="button" class="btn btn-auto next-do-cta" @click="section = 'store'">
                Empezar ahora <AppIcon name="arrow-right" :size="16" />
              </button>
              <button type="button" class="btn ghost btn-auto" @click="tourOpen = true">
                <AppIcon name="graduation-cap" :size="16" /> Ver la guía
              </button>
            </div>
          </template>
          <template v-else-if="nextStep">
            <h2>{{ nextStep.title }}</h2>
            <p>{{ nextStep.text }}</p>
            <button type="button" class="btn btn-auto next-do-cta" @click="nextStep.run ? nextStep.run() : (section = nextStep.target)">
              {{ nextStep.cta }} <AppIcon name="arrow-right" :size="16" />
            </button>
            <span class="next-do-step">Paso {{ nextStepIdx + 1 }} de {{ nextSteps.length }}</span>
          </template>
          <template v-else>
            <h2>Todo listo para vender</h2>
            <p>Tu tienda está completa. Compartí el link para sumar visitas y clientes.</p>
            <button type="button" class="btn btn-auto next-do-cta" @click="shareWhatsApp"><AppIcon name="phone" :size="16" /> Compartir por WhatsApp</button>
          </template>
        </div>

        <!-- Vista previa viva de la web con Editar / Compartir -->
        <div class="card wp-card">
          <h3><AppIcon name="store" :size="18" /> Tu página en vivo</h3>
          <template v-if="store.hasStore">
            <div class="wp-frame" aria-hidden="true">
              <span class="wp-url"><AppIcon name="lock" :size="10" /> {{ publicUrl.replace(/^https?:\/\//, '') }}</span>
              <div class="design-preview wp-mini" :data-store-theme="store.customization?.theme" :style="ovPreviewVars">
                <div class="dp-nav">
                  <span class="dp-nav-brand">
                    <img v-if="currentLogo" class="dp-nav-logo" :src="currentLogo" alt="" />
                    <span v-else class="dp-nav-mono">{{ businessInitial }}</span>
                    <span class="dp-nav-name">{{ ovShopName }}</span>
                  </span>
                </div>
                <div class="dp-hero" :class="{ 'has-cover': ovCover }" :style="ovCover ? { '--dp-cover': `url(${ovCover})` } : null">
                  <img v-if="currentLogo" class="dp-logo" :src="currentLogo" alt="" />
                  <span v-else class="dp-mono">{{ businessInitial }}</span>
                  <strong class="dp-title is-name">{{ store.customization?.headline || ovShopName }}</strong>
                  <span v-if="store.customization?.description" class="dp-desc">{{ store.customization.description }}</span>
                  <div class="dp-cta"><span v-if="ovCatalogOn" class="dp-btn">Ver catálogo</span><span class="dp-btn ghost">Contáctanos</span></div>
                </div>
              </div>
            </div>
            <div class="wp-actions">
              <button type="button" class="btn btn-auto" @click="section = 'design'"><AppIcon name="palette" :size="15" /> Editar</button>
              <button type="button" class="wp-icon" aria-label="Copiar link" title="Copiar link" @click="copyLink"><AppIcon name="copy" :size="16" /></button>
              <button type="button" class="wp-icon" aria-label="Compartir por WhatsApp" title="Compartir por WhatsApp" @click="shareWhatsApp"><AppIcon name="phone" :size="16" /></button>
              <button type="button" class="wp-icon" aria-label="Abrir mi página" title="Abrir mi página" @click="openStore"><AppIcon name="external-link" :size="16" /></button>
            </div>
          </template>
          <div v-else class="wp-empty">
            <p>Todavía no tenés tu página. Reservá la dirección gratis y aparece acá en vivo.</p>
            <button type="button" class="btn btn-auto" @click="section = 'store'">Reservar mi link</button>
          </div>
        </div>

        <!-- Números con contexto: valor + variación + tendencia de 30 días -->
        <div v-if="!firstRun" class="stats" aria-label="Números de tu negocio">
          <button type="button" class="stat stat-link" @click="section = 'catalogs'">
            <span class="stat-icon"><AppIcon name="package" :size="20" /></span>
            <div class="stat-body">
              <strong><CountUp :value="billing.hasSubscription ? catalog.products.length : 0" /></strong>
              <small>Productos en tu web</small>
            </div>
            <AppIcon class="stat-go" name="arrow-up-right" :size="16" />
          </button>
          <button type="button" class="stat stat-link" :disabled="!canStats" @click="section = 'stats'">
            <span class="stat-icon"><AppIcon name="trending-up" :size="20" /></span>
            <div class="stat-body">
              <strong><CountUp :value="canStats ? visitWeek.now : '—'" /></strong>
              <small>Visitas esta semana</small>
              <span v-if="!canStats" class="stat-sub">Con plan superior</span>
              <span v-else-if="visitWeek.delta !== null" class="stat-delta" :class="{ down: visitWeek.delta < 0 }">
                <AppIcon :name="visitWeek.delta >= 0 ? 'trending-up' : 'chevron-down'" :size="12" /> {{ Math.abs(visitWeek.delta) }}%
              </span>
            </div>
            <svg v-if="sparkline" class="stat-spark" viewBox="0 0 100 28" preserveAspectRatio="none" aria-hidden="true">
              <polygon class="spk-area" :points="sparkline.area" /><polyline class="spk-line" :points="sparkline.line" fill="none" />
            </svg>
            <AppIcon class="stat-go" name="arrow-up-right" :size="16" />
          </button>
          <button type="button" class="stat stat-link" :disabled="!canStats" @click="section = 'stats'">
            <span class="stat-icon"><AppIcon name="eye" :size="20" /></span>
            <div class="stat-body">
              <strong><CountUp :value="canStats ? (store.visitStats?.today ?? 0) : '—'" /></strong>
              <small>Visitas hoy</small>
              <span v-if="canStats" class="stat-sub">Ayer: {{ yesterdayVisits }}</span>
              <span v-else class="stat-sub">Con plan superior</span>
            </div>
            <AppIcon class="stat-go" name="arrow-up-right" :size="16" />
          </button>
          <button type="button" class="stat stat-link" @click="section = 'plans'">
            <span class="stat-icon"><AppIcon name="clock" :size="20" /></span>
            <div class="stat-body">
              <strong><CountUp :value="plan?.remaining ?? '—'" /></strong>
              <small>{{ plan?.autoRenew ? 'Se renueva solo' : 'Días de plan' }}</small>
            </div>
            <AppIcon class="stat-go" name="arrow-up-right" :size="16" />
          </button>
        </div>

        <!-- Checklist de activación: solo lo que falta, sin ruido -->
        <div v-if="!firstRun" class="card steps-card" :class="{ complete: !pendingSteps.length }">
          <h3><AppIcon name="checklist" :size="18" /> Puesta en marcha <span class="steps-count">{{ stepsDone }} de {{ nextSteps.length }}</span></h3>
          <div class="steps-bar" role="progressbar" aria-label="Pasos completados" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="stepsPct"><span :style="{ transform: `scaleX(${stepsPct / 100})` }"></span></div>
          <ol v-if="pendingSteps.length" class="steps-list">
            <li v-for="(s, i) in pendingSteps" :key="s.title" :class="{ next: i === 0 }" :style="{ '--i': i }">
              <span class="steps-num" aria-hidden="true">{{ stepsDone + i + 1 }}</span>
              <div><strong>{{ s.title }}</strong><small>{{ s.text }}</small></div>
              <button type="button" class="steps-go" :aria-label="`Ir a: ${s.title}`" @click="s.run ? s.run() : (section = s.target)"><AppIcon name="arrow-right" :size="16" /></button>
            </li>
          </ol>
          <p v-else class="steps-done-msg"><AppIcon name="check" :size="15" /> Todo listo. Compartí tu link para empezar a vender.</p>
        </div>

        <!-- Actividad reciente accionable + espacio de fotos -->
        <div v-if="!firstRun" class="card feed-card">
          <h3><AppIcon name="bell" :size="18" /> Actividad reciente</h3>
          <ul v-if="activityFeed.length" class="feed-list">
            <li v-for="(a, i) in activityFeed" :key="i">
              <span class="feed-icon"><AppIcon :name="a.icon" :size="15" /></span>
              <div class="feed-body"><strong>{{ a.title }}</strong><small v-if="a.text">{{ a.text }}</small></div>
              <button type="button" class="feed-cta" @click="a.run">{{ a.cta }}</button>
            </li>
          </ul>
          <p v-else class="feed-empty">Sin novedades por ahora.</p>
          <div v-if="store.hasStore" class="feed-storage"><StorageMeter /></div>
        </div>
      </div>
    </div>

    <!-- ================= CATÁLOGO ================= -->
    <div v-if="seen.catalogs" v-show="section === 'catalogs'" :class="{ 'sec-on': section === 'catalogs' }">
      <div class="page-head">
        <div>
          <h1>Mis productos</h1>
          <p>Acá cargás lo que vendés: aparece solo en tu página web. {{ billing.hasSubscription ? productsCountText : catalogLimit }}</p>
        </div>
        <button class="btn ghost btn-auto" @click="catalog.loadAll()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="catalog.notice" kind="success" :message="catalog.notice" />
      <AlertMessage v-if="catalog.lastError" kind="error" :message="catalog.lastError" />

      <template v-if="!billing.hasSubscription || catalog.denied">
        <div class="empty">
          <span class="empty-icon"><AppIcon name="library" :size="28" /></span>
          <h3>Para cargar productos necesitás un plan activo</h3>
          <p>Elegí un plan y en un minuto podés empezar a publicar tus productos.</p>
          <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
        </div>
      </template>

      <template v-else>
        <div class="tabs">
          <button type="button" class="tab" :class="{ active: catalogTab === 'products' }" @click="catalogTab = 'products'">
            <AppIcon name="package" :size="16" /> Mis productos
          </button>
          <button type="button" class="tab" :class="{ active: catalogTab === 'categories' }" @click="catalogTab = 'categories'">
            <AppIcon name="layout-grid" :size="16" /> Categorías <small class="tab-sub">para ordenarlos</small>
          </button>
          <button type="button" class="tab" :class="{ active: catalogTab === 'brands' }" @click="catalogTab = 'brands'">
            <AppIcon name="tag" :size="16" /> Marcas
          </button>
          <button type="button" class="tab" :class="{ active: catalogTab === 'discounts' }" @click="catalogTab = 'discounts'">
            <AppIcon name="percent" :size="16" /> Descuentos <small class="tab-sub">{{ canDiscounts ? 'se activan solos' : 'Premium' }}</small>
          </button>
        </div>

        <div v-if="catalog.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu catálogo…</p></div>

        <template v-else>
          <!-- -------- Productos -------- -->
          <div v-show="catalogTab === 'products'" class="grid-2">
            <div class="card">
              <h3><AppIcon :name="productEditing ? 'pencil' : 'plus'" :size="18" /> {{ productEditing ? 'Editar producto' : 'Agregar un producto' }}</h3>
              <p class="lead">Completá lo básico y tocá «Publicar». Después lo podés cambiar cuando quieras.</p>
              <div class="form-step"><span class="form-step-num">1</span> ¿Qué vendés?</div>
              <AppInput v-model="productForm.name" label="Nombre" name="prod_name" placeholder="Ej. Remera oversize" :error="productFieldErr('name')" @blur="productTouched.name = true" />
              <div class="grid-2">
                <AppInput v-model="productForm.price" label="Precio" name="prod_price" type="number" min="0" step="0.01" placeholder="0.00" :error="productFieldErr('price')" @blur="productTouched.price = true" />
              </div>
              <div v-if="legacyOffer && !offerCleared" class="legacy-offer">
                <AppIcon name="tag" :size="14" aria-hidden="true" />
                <span>Este producto tiene una oferta manual: <strong>{{ formatARS(legacyOffer) }}</strong>. Las ofertas ahora se programan en «Descuentos».</span>
                <button type="button" class="legacy-offer-btn" @click="offerCleared = true">Quitar</button>
              </div>
              <p v-else class="hint">¿Oferta? Programala en la pestaña «Descuentos»: se activa y vence sola.</p>
              <div class="form-step"><span class="form-step-num">2</span> Sumá una foto</div>
              <div class="field">
                <label id="prod-image-label">Imagen</label>
                <div class="logo-box">
                  <span class="logo-thumb">
                    <img v-if="productImagePreview" :src="productImagePreview" alt="Imagen del producto" />
                    <AppIcon v-else name="image" :size="20" aria-hidden="true" />
                  </span>
                  <div class="logo-actions">
                    <input ref="productImageInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="prod-image-label" @change="onProductImagePicked" />
                    <button type="button" class="btn ghost btn-auto" @click="productImageInput?.click()">
                      <AppIcon name="upload" :size="16" /> {{ productImagePreview ? 'Cambiar' : 'Subir imagen' }}
                    </button>
                    <button v-if="productImage && !productOriginal" type="button" class="btn ghost btn-auto" :disabled="productBgBusy" @click="removeProductBg">
                      <span v-if="productBgBusy" class="spinner" aria-hidden="true"></span><AppIcon v-else name="sparkles" :size="16" /> {{ productBgBusy ? 'Procesando…' : 'Quitar fondo' }}
                    </button>
                    <button v-if="productOriginal" type="button" class="btn ghost btn-auto" @click="restoreProductOriginal">Volver al original</button>
                    <button v-if="productImagePreview" type="button" class="btn ghost btn-auto" @click="productImage = null; productOriginal = null; productImagePreview = ''; productImageCleared = true">Quitar</button>
                  </div>
                </div>
                <p class="hint">Una foto clara vende más. Si el fondo molesta, usá «Quitar fondo». Máximo 4 MB. Usá solo fotos propias o con permiso.</p>
                <p v-if="productImageErr" class="field-error" role="alert">{{ productImageErr }}</p>
              </div>
              <details class="more-opts" :open="productEditing">
                <summary><span class="form-step-num">3</span> Más detalles <small>(opcional: categoría, descripción, características)</small></summary>
              <div class="grid-2">
                <div class="field">
                  <label for="prod-active">Visibilidad</label>
                  <select id="prod-active" v-model="productForm.is_active" class="select">
                    <option :value="true">Visible en mi web</option>
                    <option :value="false">Oculto</option>
                  </select>
                </div>
              </div>
              <div class="grid-2">
                <div class="field">
                  <label for="prod-category">Categoría</label>
                  <select id="prod-category" v-model="productForm.category" class="select">
                    <option value="">Sin categoría</option>
                    <option v-for="c in catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                  </select>
                  <p class="hint">Se cargan en la pestaña Categorías.</p>
                </div>
                <div class="field">
                  <label for="prod-brand">Marca</label>
                  <select id="prod-brand" v-model="productForm.brand" class="select">
                    <option value="">Sin marca</option>
                    <option v-for="b in catalog.brands" :key="b.id" :value="b.id">{{ b.name }}</option>
                  </select>
                </div>
              </div>
              <div class="field">
                <label for="prod-description">Descripción</label>
                <textarea
                  id="prod-description"
                  v-model="productForm.description"
                  class="textarea"
                  :class="{ invalid: productFieldErr('description') }"
                  placeholder="Detalles del producto (opcional)"
                  maxlength="600"
                  rows="3"
                  @blur="productTouched.description = true"
                ></textarea>
                <p class="hint">{{ productForm.description.length }}/600</p>
                <p v-if="productFieldErr('description')" class="field-error" role="alert">{{ productFieldErr('description') }}</p>
              </div>
              <div class="field">
                <label id="prod-features-label">Características</label>
                <ul v-if="productFeatures.length" class="feat-rows" aria-labelledby="prod-features-label">
                  <li v-for="(row, i) in productFeatures" :key="i" class="feat-row">
                    <input v-model="row.name" class="input" type="text" maxlength="40" placeholder="Atributo (ej. Talle)" :aria-label="`Nombre de la característica ${i + 1}`" />
                    <input v-model="row.value" class="input" type="text" maxlength="120" placeholder="Valor (ej. M)" :aria-label="`Valor de la característica ${i + 1}`" />
                    <button type="button" class="icon-btn danger" aria-label="Quitar característica" @click="removeFeatureRow(i)"><AppIcon name="trash" :size="15" /></button>
                  </li>
                </ul>
                <button type="button" class="btn ghost btn-auto" :disabled="productFeatures.length >= FEATURE_LIMITS.entriesMax" @click="addFeatureRow"><AppIcon name="plus" :size="15" /> Agregar característica</button>
                <p class="hint">La categoría sugiere atributos (se cargan desde la pestaña Categorías); podés sumar otros propios.</p>
                <p v-if="productTouched.features && featuresErr" class="field-error" role="alert">{{ featuresErr }}</p>
              </div>
              </details>
              <div class="btn-row">
                <AppButton :loading="productBusy" @click="saveProduct">{{ productEditing ? 'Guardar cambios' : 'Publicar producto' }}</AppButton>
                <button v-if="productEditing" type="button" class="btn ghost btn-auto" @click="resetProductForm">Cancelar</button>
              </div>
            </div>

            <div class="card">
              <h3><AppIcon name="package" :size="18" /> Tus productos</h3>
              <StorageMeter />
              <div v-if="!catalog.products.length" class="empty-mini">
                <AppIcon name="package" :size="22" />
                <div><p>Todavía no cargaste productos. El primero tarda un minuto: nombre, precio y una foto.</p><button type="button" class="empty-mini-cta" @click="focusField('prod_name')">Cargar el primero</button></div>
              </div>
              <template v-else>
                <label class="prod-search">
                  <AppIcon name="search" :size="16" aria-hidden="true" />
                  <input v-model="productQuery" type="search" placeholder="Buscar por nombre, categoría o marca" aria-label="Buscar productos" />
                </label>
                <p v-if="!filteredProducts.length" class="hint">No hay productos que coincidan con tu búsqueda.</p>
                <ul v-else class="prod-list">
                  <li v-for="p in filteredProducts" :key="p.id" class="prod-item">
                  <span class="prod-thumb">
                    <img v-if="p.image" :src="p.image" :alt="p.name" />
                    <AppIcon v-else name="package" :size="16" aria-hidden="true" />
                  </span>
                  <div class="prod-info">
                    <strong>{{ p.name }}</strong>
                    <small><template v-if="productListOffer(p) != null"><s class="prod-old">{{ formatARS(p.price) }}</s> {{ formatARS(productListOffer(p)) }}</template><template v-else>{{ formatARS(p.price) }}</template><template v-if="p.category_name"> · {{ p.category_name }}</template><template v-if="p.brand_name"> · {{ p.brand_name }}</template></small>
                  </div>
                  <span v-if="isDiscountedProduct(p)" class="pill ok" :title="(p.discount_names || []).join(' · ')">Promo</span>
                  <span v-else-if="productListOffer(p) != null" class="pill ok">Oferta</span>
                  <span v-if="!p.is_active" class="pill muted">Oculto</span>
                  <button type="button" class="icon-btn" aria-label="Editar producto" @click="editProduct(p)"><AppIcon name="pencil" :size="15" /></button>
                  <button type="button" class="icon-btn danger" aria-label="Eliminar producto" @click="removeProduct(p)"><AppIcon name="trash" :size="15" /></button>
                  </li>
                </ul>
              </template>
            </div>
          </div>

          <!-- -------- Categorías -------- -->
          <div v-show="catalogTab === 'categories'" class="card">
            <h3><AppIcon name="layout-grid" :size="18" /> Categorías</h3>
            <p>Agrupan tus productos en el menú de tu página pública.</p>
            <div class="tax-add">
              <div class="tax-fields">
                <AppInput v-model="taxonomyForm.category" :label="taxonomyEditing ? 'Editar categoría' : 'Nueva categoría'" name="cat_name" placeholder="Ej. Indumentaria" :error="taxonomyErr.category" />
                <AppInput v-model="taxonomyForm.categoryFeatures" label="Características (opcional)" name="cat_features" placeholder="Ej. Talle, Color, Material" hint="Separalas con comas: se sugieren al cargar productos de esta categoría." />
              </div>
              <div class="tax-actions">
                <AppButton :loading="taxonomyBusy.category" @click="addTaxonomy('category')">{{ taxonomyEditing ? 'Guardar' : 'Agregar' }}</AppButton>
                <button v-if="taxonomyEditing" type="button" class="btn ghost btn-auto" @click="cancelCategoryEdit">Cancelar</button>
              </div>
            </div>
            <ul v-if="catalog.categories.length" class="tax-list">
              <li v-for="c in catalog.categories" :key="c.id">
                <span>{{ c.name }}
                  <small class="hint-inline">{{ c.products_count || 0 }} productos</small>
                  <small v-if="c.feature_schema?.length" class="tax-schema">{{ c.feature_schema.join(' · ') }}</small>
                </span>
                <span class="tax-item-actions">
                  <button type="button" class="icon-btn" aria-label="Editar categoría" @click="editCategory(c)"><AppIcon name="pencil" :size="15" /></button>
                  <button type="button" class="icon-btn danger" aria-label="Eliminar categoría" @click="removeTaxonomy('category', c)"><AppIcon name="trash" :size="15" /></button>
                </span>
              </li>
            </ul>
            <p v-else class="hint">Sin categorías todavía.</p>
          </div>

          <!-- -------- Marcas -------- -->
          <div v-show="catalogTab === 'brands'" class="card">
            <h3><AppIcon name="tag" :size="18" /> Marcas</h3>
            <p>Filtran tus productos por marca en el menú de tu página pública.</p>
            <div class="tax-add">
              <AppInput v-model="taxonomyForm.brand" label="Nueva marca" name="brand_name" placeholder="Ej. Nike" :error="taxonomyErr.brand" />
              <AppButton :loading="taxonomyBusy.brand" @click="addTaxonomy('brand')">Agregar</AppButton>
            </div>
            <ul v-if="catalog.brands.length" class="tax-list">
              <li v-for="b in catalog.brands" :key="b.id">
                <span>{{ b.name }} <small class="hint-inline">{{ b.products_count || 0 }} productos</small></span>
                <button type="button" class="icon-btn danger" aria-label="Eliminar marca" @click="removeTaxonomy('brand', b)"><AppIcon name="trash" :size="15" /></button>
              </li>
            </ul>
            <p v-else class="hint">Sin marcas todavía.</p>
          </div>

          <!-- -------- Descuentos programados (premium) -------- -->
          <div v-show="catalogTab === 'discounts'">
          <div v-if="!canDiscounts" class="empty">
            <span class="empty-icon"><AppIcon name="percent" :size="28" /></span>
            <h3>Los descuentos programados son Premium</h3>
            <p>Con el Plan premium creás ofertas que se activan y se apagan solas en las fechas que elijas, sin tocar los precios a mano.</p>
            <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
          </div>
          <div v-else class="grid-2 disc-wrap">
            <div class="card disc-card">
              <h3><AppIcon :name="discountEditing ? 'pencil' : 'percent'" :size="18" /> {{ discountEditing ? 'Editar descuento' : 'Nuevo descuento' }}</h3>
              <p class="lead">Programá una oferta: se activa y se apaga sola en las fechas que elijas, sin que tengas que tocar los precios.</p>
              <div class="disc-preview" aria-hidden="true">
                <span class="disc-preview-badge"><b>-{{ discountPreviewPct }}</b><i>%</i></span>
                <div class="disc-preview-info">
                  <small>Así se verá en tu tienda</small>
                  <strong>{{ discountForm.name || 'Nombre de tu oferta' }}</strong>
                  <span class="disc-preview-price"><s>{{ formatARS(10000) }}</s><b>{{ formatARS(10000 * (1 - discountPreviewPct / 100)) }}</b></span>
                </div>
              </div>
              <AppInput v-model="discountForm.name" label="Nombre" name="disc_name" icon="tag" placeholder="Ej. Semana de ofertas" :error="discountFieldErr('name')" @blur="discountTouched.name = true" />

              <div class="field">
                <label for="disc-percent"><AppIcon name="percent" :size="14" class="label-icon" aria-hidden="true" />Descuento</label>
                <div class="disc-pct-row">
                  <input id="disc-percent" v-model="discountForm.percent" type="number" min="1" max="99" step="1" class="input disc-pct-input" :class="{ invalid: discountFieldErr('percent') }" placeholder="25" aria-label="Porcentaje de descuento" @blur="discountTouched.percent = true" />
                  <span class="disc-pct-sign" aria-hidden="true">%</span>
                  <input v-model="discountForm.percent" type="range" min="1" max="99" step="1" class="disc-pct-slider" aria-label="Descuento en porcentaje" />
                </div>
                <p v-if="discountFieldErr('percent')" class="field-error" role="alert">{{ discountFieldErr('percent') }}</p>
              </div>

              <div class="field">
                <label id="disc-scope-label"><AppIcon name="layout-grid" :size="14" class="label-icon" aria-hidden="true" />¿A qué aplica?</label>
                <div class="disc-scope" role="radiogroup" aria-labelledby="disc-scope-label">
                  <label v-for="s in DISCOUNT_SCOPES" :key="s.value" class="disc-scope-card" :class="{ on: discountForm.scope === s.value }">
                    <input v-model="discountForm.scope" type="radio" :value="s.value" class="sr-only" />
                    <AppIcon :name="SCOPE_ICONS[s.value]" :size="17" aria-hidden="true" />
                    <span>{{ s.label }}</span>
                  </label>
                </div>
              </div>

              <div v-if="discountForm.scope === 'category'" class="field">
                <label for="disc-category"><AppIcon name="checklist" :size="14" class="label-icon" aria-hidden="true" />Categoría</label>
                <select id="disc-category" v-model="discountForm.category" class="select" :class="{ invalid: discountFieldErr('category') }">
                  <option value="">Elegí una categoría</option>
                  <option v-for="c in catalog.categories" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
                <p v-if="!catalog.categories.length" class="hint">No tenés categorías: cargalas en la pestaña Categorías.</p>
                <p v-if="discountFieldErr('category')" class="field-error" role="alert">{{ discountFieldErr('category') }}</p>
              </div>
              <div v-if="discountForm.scope === 'brand'" class="field">
                <label for="disc-brand"><AppIcon name="tag" :size="14" class="label-icon" aria-hidden="true" />Marca</label>
                <select id="disc-brand" v-model="discountForm.brand" class="select" :class="{ invalid: discountFieldErr('brand') }">
                  <option value="">Elegí una marca</option>
                  <option v-for="b in catalog.brands" :key="b.id" :value="b.id">{{ b.name }}</option>
                </select>
                <p v-if="!catalog.brands.length" class="hint">No tenés marcas: cargalas en la pestaña Marcas.</p>
                <p v-if="discountFieldErr('brand')" class="field-error" role="alert">{{ discountFieldErr('brand') }}</p>
              </div>
              <div v-if="discountForm.scope === 'products'" class="field">
                <label id="disc-products-label"><AppIcon name="package" :size="14" class="label-icon" aria-hidden="true" />Productos incluidos</label>
                <template v-if="catalog.products.length">
                  <div class="disc-products-tools">
                    <button type="button" class="disc-tool" @click="discountForm.product_ids = catalog.products.filter((p) => !discountTakenBy.has(p.id)).map((p) => p.id)"><AppIcon name="check" :size="13" /> Todos</button>
                    <button type="button" class="disc-tool" @click="discountForm.product_ids = []"><AppIcon name="x" :size="13" /> Ninguno</button>
                    <span class="hint">{{ discountForm.product_ids.length }} seleccionados</span>
                  </div>
                  <div class="check-list disc-products" role="group" aria-labelledby="disc-products-label">
                    <label v-for="p in catalog.products" :key="p.id" class="check-item" :class="{ taken: discountTakenBy.has(p.id) }">
                      <input type="checkbox" :value="p.id" v-model="discountForm.product_ids" :disabled="discountTakenBy.has(p.id)" />
                      <span class="check-text"><strong>{{ p.name }}</strong><small>{{ formatARS(p.price) }}</small></span>
                      <span v-if="discountTakenBy.has(p.id)" class="check-taken" :title="`Ya está en el descuento «${discountTakenBy.get(p.id)}»`"><AppIcon name="lock" :size="11" /> {{ discountTakenBy.get(p.id) }}</span>
                    </label>
                  </div>
                  <p v-if="discountTakenBy.size" class="hint">Los productos que ya están en otro descuento vigente no se pueden elegir.</p>
                </template>
                <p v-else class="hint">Todavía no cargaste productos.</p>
                <p v-if="discountFieldErr('products')" class="field-error" role="alert">{{ discountFieldErr('products') }}</p>
              </div>

              <div class="field">
                <label id="disc-window-label"><AppIcon name="calendar" :size="14" class="label-icon" aria-hidden="true" />¿Cuándo aplica?</label>
                <div class="disc-presets" role="group" aria-label="Duraciones rápidas">
                  <button type="button" class="disc-preset" @click="discountPreset('today')">Solo hoy</button>
                  <button type="button" class="disc-preset" @click="discountPreset('week')">Esta semana</button>
                  <button type="button" class="disc-preset" @click="discountPreset('fortnight')">15 días</button>
                  <button type="button" class="disc-preset" @click="discountPreset('month')">Este mes</button>
                  <button type="button" class="disc-preset" @click="discountPreset('none')">Sin fin</button>
                </div>
                <div class="disc-window">
                  <div class="disc-when">
                    <span class="disc-when-label"><AppIcon name="calendar" :size="13" aria-hidden="true" /> Empieza</span>
                    <div class="disc-when-fields">
                      <input v-model="discountForm.start_date" type="date" class="input" :class="{ invalid: discountFieldErr('start_date') }" aria-label="Fecha de inicio" @blur="discountTouched.start_date = true" />
                      <input v-model="discountForm.start_time" type="time" class="input" :class="{ invalid: discountFieldErr('start_date') }" aria-label="Hora de inicio" @blur="discountTouched.start_date = true" />
                    </div>
                    <p v-if="discountFieldErr('start_date')" class="field-error" role="alert">{{ discountFieldErr('start_date') }}</p>
                  </div>
                  <div class="disc-when">
                    <span class="disc-when-label"><AppIcon name="clock" :size="13" aria-hidden="true" /> Termina</span>
                    <label class="disc-none">
                      <input v-model="discountForm.end_none" type="checkbox" />
                      <span>Sin fin definido</span>
                    </label>
                    <div v-if="!discountForm.end_none" class="disc-when-fields">
                      <input v-model="discountForm.end_date" type="date" class="input" :class="{ invalid: discountFieldErr('end_date') }" :min="discountForm.start_date || undefined" aria-label="Fecha de fin" @blur="discountTouched.end_date = true" />
                      <input v-model="discountForm.end_time" type="time" class="input" :class="{ invalid: discountFieldErr('end_date') }" aria-label="Hora de fin" @blur="discountTouched.end_date = true" />
                    </div>
                    <p v-if="discountFieldErr('end_date')" class="field-error" role="alert">{{ discountFieldErr('end_date') }}</p>
                  </div>
                </div>
              </div>

              <div class="check-list">
                <label class="check-item">
                  <input type="checkbox" v-model="discountForm.is_active" />
                  <span class="check-text"><strong><AppIcon name="zap" :size="14" class="label-icon" aria-hidden="true" /> Descuento activo</strong><small>Si lo pausás, deja de aplicarse aunque esté en fecha.</small></span>
                </label>
              </div>
              <div class="btn-row">
                <AppButton :loading="discountBusy" @click="saveDiscount"><AppIcon name="check" :size="16" /> {{ discountEditing ? 'Guardar cambios' : 'Crear descuento' }}</AppButton>
                <button v-if="discountEditing" type="button" class="btn ghost btn-auto" @click="resetDiscountForm">Cancelar</button>
              </div>
            </div>

            <div class="card disc-card">
              <h3><AppIcon name="percent" :size="18" /> Tus descuentos</h3>
              <div v-if="!catalog.discounts.length" class="empty-mini"><AppIcon name="percent" :size="22" /><p>Todavía no programaste descuentos. Crean ofertas que se encienden y se apagan solas.</p></div>
              <ul v-else class="disc-list">
                <li v-for="d in catalog.discounts" :key="d.id" class="disc-item">
                  <span class="disc-badge" aria-hidden="true"><b>-{{ d.percent }}</b><i>%</i></span>
                  <span class="disc-info">
                    <strong class="disc-name">{{ d.name }}</strong>
                    <small class="disc-meta"><AppIcon name="tag" :size="12" aria-hidden="true" /> {{ discountScopeLabel(d) }}</small>
                    <small class="disc-range"><AppIcon name="calendar" :size="12" aria-hidden="true" /> {{ discountWindowLabel(d) }}</small>
                  </span>
                  <span class="disc-actions">
                    <span class="pill" :class="discountStatusMeta(d).pill">{{ discountStatusMeta(d).label }}</span>
                    <button type="button" class="icon-btn" :aria-label="d.is_active ? 'Pausar descuento' : 'Reactivar descuento'" :title="d.is_active ? 'Pausar' : 'Reactivar'" @click="toggleDiscount(d)"><AppIcon :name="d.is_active ? 'pause' : 'play'" :size="15" /></button>
                    <button type="button" class="icon-btn" aria-label="Editar descuento" @click="editDiscount(d)"><AppIcon name="pencil" :size="15" /></button>
                    <button type="button" class="icon-btn danger" aria-label="Eliminar descuento" @click="removeDiscount(d)"><AppIcon name="trash" :size="15" /></button>
                  </span>
                </li>
              </ul>
            </div>
          </div>
          </div>

          <!-- -------- Opciones avanzadas -------- -->
          <details class="card more-card">
            <summary><AppIcon name="store" :size="18" /> Opciones avanzadas de tu catálogo <small>Páginas de la web y carrusel de portada</small></summary>
            <div class="field">
              <label id="site-templates-label-cat">Páginas de tu web</label>
              <div class="check-list" role="group" aria-labelledby="site-templates-label-cat">
                <label v-for="key in siteTemplateKeys" :key="key" class="check-item" :class="{ disabled: !allowedSiteTemplates.includes(key) }">
                  <input type="checkbox" :checked="designSiteTemplates.includes(key)" :disabled="!canToggleSiteTemplate(key)" @change="toggleSiteTemplate(key)" />
                  <span class="check-text">
                    <strong>{{ siteTemplates[key].label }} <span v-if="siteTemplateLock(key)" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> {{ siteTemplateLock(key) }}</span> <span v-if="siteTemplatesBusy" class="spinner spinner-brand" aria-hidden="true"></span></strong>
                    <small>{{ siteTemplates[key].desc }}</small>
                  </span>
                </label>
              </div>
              <p class="hint">{{ siteTemplatesHint }} Se guarda al instante — también podés administrarlas desde «Plantillas» en Mi página web.</p>
            </div>
            <div v-if="canDesignAdvanced" class="field">
              <label id="catalog-carousel-label">Carrusel de portada</label>
              <div class="carousel-box">
                <div v-for="(img, i) in carouselImages" :key="img.id" class="carousel-thumb">
                  <img :src="img.url" :alt="`Imagen ${i + 1} del carrusel`" />
                  <div class="carousel-thumb-actions">
                    <button type="button" class="icon-btn" aria-label="Mover a la izquierda" :disabled="i === 0 || carouselBusy" @click="onMoveCarousel(img.id, -1)"><AppIcon name="chevron-left" :size="13" /></button>
                    <button type="button" class="icon-btn" aria-label="Mover a la derecha" :disabled="i === carouselImages.length - 1 || carouselBusy" @click="onMoveCarousel(img.id, 1)"><AppIcon name="chevron-right" :size="13" /></button>
                    <button type="button" class="icon-btn danger" aria-label="Eliminar imagen" :disabled="carouselBusy" @click="onRemoveCarousel(img.id)"><AppIcon name="trash" :size="13" /></button>
                  </div>
                </div>
                <button
                  v-if="carouselImages.length < CAROUSEL_MAX_IMAGES"
                  type="button" class="carousel-add" :disabled="carouselBusy"
                  @click="carouselInput?.click()"
                >
                  <span v-if="carouselBusy" class="spinner" aria-hidden="true"></span>
                  <AppIcon v-else name="images" :size="20" />
                  Agregar
                </button>
              </div>
              <input ref="carouselInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="catalog-carousel-label" @change="onCarouselPicked" />
              <p class="hint">Hasta {{ CAROUSEL_MAX_IMAGES }} imágenes de 4 MB. Se muestran como banners sobre tu catálogo.</p>
              <p v-if="carouselErr" class="field-error" role="alert">{{ carouselErr }}</p>
            </div>
            <p v-else class="hint">El carrusel de portada del catálogo se habilita con el Plan premium.</p>
          </details>
        </template>
      </template>
    </div>
    <!-- ================= MIS SERVICIOS ================= -->
    <div v-if="seen.services" v-show="section === 'services'" :class="{ 'sec-on': section === 'services' }">
      <div class="page-head">
        <div>
          <h1>Mis servicios</h1>
          <p>Lo que ofrecés en la página Servicios de tu web: tus clientes arman su presupuesto y el pedido te llega por WhatsApp. Nada se cobra online.</p>
        </div>
        <button class="btn ghost btn-auto" @click="services.loadAll()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="services.notice" kind="success" :message="services.notice" />
      <AlertMessage v-if="services.lastError" kind="error" :message="services.lastError" />

      <template v-if="services.denied">
        <div class="empty">
          <span class="empty-icon"><AppIcon name="wrench" :size="28" /></span>
          <h3>La página Servicios está disponible desde el plan Estándar</h3>
          <p>Sumala a tu web: tus clientes eligen servicios, ven un presupuesto orientativo y te escriben por WhatsApp.</p>
          <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
        </div>
      </template>

      <template v-else>
        <div v-if="!designSiteTemplates.includes('services')" class="card" role="note">
          <h3><AppIcon name="info" :size="18" /> La página está apagada</h3>
          <p class="hint">Tus servicios quedan guardados, pero la página Servicios no aparece en tu web hasta que la actives en <a href="#" @click.prevent="section = 'pages'"><strong>Plantillas</strong></a>.</p>
        </div>
        <div v-if="services.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tus servicios…</p></div>
        <template v-else>
          <div class="svc-stats">
            <div v-for="st in serviceStats" :key="st.key" class="svc-stat" :style="{ '--h': st.hue }">
              <span class="svc-stat-ico"><AppIcon :name="st.icon" :size="20" aria-hidden="true" /></span>
              <div>
                <strong>{{ st.value }}</strong>
                <span>{{ st.label }}</span>
                <small>{{ st.hint }}</small>
              </div>
            </div>
          </div>
          <div class="svc-meter" role="progressbar" :aria-valuenow="serviceUsage" aria-valuemin="0" aria-valuemax="100" aria-label="Cupo de servicios usado">
            <span :style="{ width: serviceUsage + '%' }"></span>
          </div>
          <div class="grid-2">
            <div class="card">
              <h3><AppIcon :name="serviceEditing ? 'pencil' : 'plus'" :size="18" /> {{ serviceEditing ? 'Editar servicio' : 'Agregar un servicio' }}</h3>
              <div class="svc-preview" :style="{ '--h': serviceHue(serviceForm.icon) }" aria-hidden="true">
                <span class="svc-ico"><AppIcon :name="serviceIcon(serviceForm.icon)" :size="22" /></span>
                <div>
                  <strong>{{ serviceForm.name || 'Nombre del servicio' }}</strong>
                  <small>{{ servicePriceLabel(serviceForm) }}<template v-if="serviceForm.duration"> · {{ serviceForm.duration }}</template></small>
                </div>
              </div>
              <p class="lead">El precio es orientativo: podés dejarlo vacío y se muestra como «a convenir».</p>
              <AppInput v-model="serviceForm.name" label="Nombre" icon="pencil" name="svc_name" placeholder="Ej. Reparación a domicilio" :error="serviceFieldErr('name')" @blur="serviceTouched.name = true" />
              <div class="grid-2">
                <AppInput v-model="serviceForm.price" label="Precio orientativo" icon="tag" name="svc_price" type="number" min="0" step="0.01" placeholder="Vacío = a convenir" :error="serviceFieldErr('price')" @blur="serviceTouched.price = true" />
                <AppInput v-model="serviceForm.duration" label="Duración estimada" icon="clock" name="svc_duration" placeholder="Ej. ≈ 45 min" :error="serviceFieldErr('duration')" @blur="serviceTouched.duration = true" />
              </div>
              <div class="grid-2">
                <div class="field">
                  <label for="svc-icon"><AppIcon name="sparkles" :size="14" class="label-icon" aria-hidden="true" />Icono</label>
                  <IconSelect id="svc-icon" v-model="serviceForm.icon" :options="serviceIconOptions" />
                </div>
                <div class="field">
                  <label for="svc-active"><AppIcon name="eye" :size="14" class="label-icon" aria-hidden="true" />Visibilidad</label>
                  <IconSelect id="svc-active" v-model="serviceForm.is_active" :options="serviceVisibilityOptions" />
                </div>
              </div>
              <div class="field">
                <label for="svc-description"><AppIcon name="message-circle" :size="14" class="label-icon" aria-hidden="true" />Descripción corta</label>
                <textarea id="svc-description" v-model="serviceForm.description" class="textarea" :class="{ invalid: serviceFieldErr('description') }" placeholder="Qué incluye o cómo se coordina (opcional)" :maxlength="serviceLimits.description" rows="2" @blur="serviceTouched.description = true"></textarea>
                <p class="hint">{{ serviceForm.description.length }}/{{ serviceLimits.description }}</p>
                <p v-if="serviceFieldErr('description')" class="field-error" role="alert">{{ serviceFieldErr('description') }}</p>
              </div>
              <div class="btn-row">
                <AppButton :loading="serviceBusy" :disabled="!serviceEditing && services.limitReached" @click="saveService">{{ serviceEditing ? 'Guardar cambios' : 'Publicar servicio' }}</AppButton>
                <button v-if="serviceEditing" type="button" class="btn ghost btn-auto" @click="resetServiceForm">Cancelar</button>
              </div>
              <p v-if="services.limitReached" class="hint">Llegaste al máximo de {{ serviceLimits.max }} servicios por página.</p>
            </div>

            <div class="card">
              <h3><AppIcon name="wrench" :size="18" /> Tus servicios</h3>
              <div v-if="!services.items.length" class="empty-mini">
                <AppIcon name="wrench" :size="22" />
                <div><p>Todavía no cargaste servicios. Contá qué hacés, cuánto tarda y a qué precio.</p><button type="button" class="empty-mini-cta" @click="focusField('svc_name')">Cargar el primero</button></div>
              </div>
              <ul v-else class="svc-list">
                <li v-for="(s, i) in services.items" :key="s.id" class="svc-card" :class="{ off: !s.is_active, editing: serviceEditing?.id === s.id }" :style="{ '--h': serviceHue(s.icon) }">
                  <span class="svc-ico"><AppIcon :name="serviceIcon(s.icon)" :size="22" aria-hidden="true" /></span>
                  <div class="svc-body">
                    <div class="svc-title">
                      <span class="svc-num">{{ String(i + 1).padStart(2, '0') }}</span>
                      <strong>{{ s.name }}</strong>
                      <span class="svc-badge" :class="s.is_active ? 'on' : 'off'">{{ s.is_active ? 'Visible' : 'Oculto' }}</span>
                    </div>
                    <div class="svc-meta">
                      <span><AppIcon name="tag" :size="13" aria-hidden="true" /> {{ servicePriceLabel(s) }}</span>
                      <span v-if="s.duration"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ s.duration }}</span>
                    </div>
                    <p v-if="s.description" class="svc-desc">{{ s.description }}</p>
                  </div>
                  <div class="svc-actions">
                    <button type="button" class="icon-btn" aria-label="Subir" :disabled="i === 0" @click="moveService(s, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                    <button type="button" class="icon-btn" aria-label="Bajar" :disabled="i === services.items.length - 1" @click="moveService(s, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                    <button type="button" class="icon-btn" :aria-label="s.is_active ? 'Ocultar servicio' : 'Mostrar servicio'" :title="s.is_active ? 'Ocultar' : 'Mostrar'" @click="services.toggleService(s)"><AppIcon :name="s.is_active ? 'eye-off' : 'eye'" :size="15" /></button>
                    <button type="button" class="icon-btn" aria-label="Editar servicio" @click="editService(s)"><AppIcon name="pencil" :size="15" /></button>
                    <button type="button" class="icon-btn danger" aria-label="Eliminar servicio" @click="removeService(s)"><AppIcon name="trash" :size="15" /></button>
                  </div>
                </li>
              </ul>
              <p class="hint">El orden de esta lista es el orden en que aparecen en tu web.</p>
            </div>
          </div>

          <div class="card">
            <h3><AppIcon name="wrench" :size="18" /> Tu página de servicios</h3>
            <p class="lead">Ajustá cómo pide los datos el formulario y qué leen tus clientes junto al presupuesto.</p>
            <section class="svc-block">
              <header class="svc-block-head" style="--h: 250">
                <span class="svc-block-ico"><AppIcon name="checklist" :size="18" aria-hidden="true" /></span>
                <div>
                  <h4 id="svc-steps-label">Cómo funciona</h4>
                  <p>Los pasos que ve tu cliente antes de pedir. Hasta {{ servicePageLimits.steps }}; sin pasos se usan unos por defecto.</p>
                </div>
                <span class="svc-count">{{ (designForm.service_steps || []).length }}/{{ servicePageLimits.steps }}</span>
              </header>
              <ul v-if="(designForm.service_steps || []).length" class="feat-rows" aria-labelledby="svc-steps-label">
                <li v-for="(row, i) in designForm.service_steps" :key="i" class="feat-row svc-step-row">
                  <IconSelect v-model="row.icon" :id="`svc-step-icon-${i}`" class="svc-step-icon" :options="serviceIconOptions" :aria-label="`Icono del paso ${i + 1}`" />
                  <input v-model="row.title" class="input" type="text" :maxlength="servicePageLimits.stepTitle" placeholder="Título (ej. Confirmamos por WhatsApp)" :aria-label="`Título del paso ${i + 1}`" />
                  <input v-model="row.text" class="input" type="text" :maxlength="servicePageLimits.stepText" placeholder="Descripción breve" :aria-label="`Texto del paso ${i + 1}`" />
                  <button type="button" class="icon-btn danger" aria-label="Quitar paso" @click="removeServiceStep(i)"><AppIcon name="trash" :size="15" /></button>
                </li>
              </ul>
              <button type="button" class="btn ghost btn-auto" :disabled="(designForm.service_steps || []).length >= servicePageLimits.steps" @click="addServiceStep"><AppIcon name="plus" :size="15" /> Agregar paso</button>
            </section>

            <section class="svc-block">
              <header class="svc-block-head" style="--h: 195">
                <span class="svc-block-ico"><AppIcon name="calendar" :size="18" aria-hidden="true" /></span>
                <div>
                  <h4>Cuándo atendés</h4>
                  <p>Escribí y presioná Enter, o tocá una sugerencia. Si lo dejás vacío, la página propone opciones genéricas.</p>
                </div>
              </header>
              <div class="grid-2">
                <div v-for="f in [{ k: 'service_days', label: 'Días que ofrecés', icon: 'calendar', ph: 'Ej. Sábado' }, { k: 'service_slots', label: 'Franjas horarias', icon: 'clock', ph: 'Ej. 9 a 12 h' }]" :key="f.k" class="field">
                  <label :for="`chip-${f.k}`">{{ f.label }} <span class="svc-count">{{ (designForm[f.k] || []).length }}/{{ chipMax(f.k) }}</span></label>
                  <div class="svc-chips" @click="$refs[`chip_${f.k}`]?.[0]?.focus()">
                    <span v-for="(c, i) in designForm[f.k] || []" :key="c" class="svc-chip">
                      <AppIcon :name="f.icon" :size="12" aria-hidden="true" /> {{ c }}
                      <button type="button" :aria-label="`Quitar ${c}`" @click.stop="removeServiceChip(f.k, i)"><AppIcon name="x" :size="12" /></button>
                    </span>
                    <input :id="`chip-${f.k}`" :ref="`chip_${f.k}`" v-model="serviceChipDraft[f.k]" type="text" class="svc-chip-input" :maxlength="servicePageLimits.day" :placeholder="(designForm[f.k] || []).length ? 'Agregar otro…' : f.ph" :disabled="(designForm[f.k] || []).length >= chipMax(f.k)" @keydown="onChipKey($event, f.k)" @blur="addServiceChip(f.k)" />
                  </div>
                  <div class="svc-sugg">
                    <button v-for="sg in SERVICE_CHIP_SUGGESTIONS[f.k].filter((x) => !(designForm[f.k] || []).includes(x))" :key="sg" type="button" @click="addServiceChip(f.k, sg)"><AppIcon name="plus" :size="11" aria-hidden="true" /> {{ sg }}</button>
                  </div>
                </div>
              </div>
            </section>

            <section class="svc-block">
              <header class="svc-block-head" style="--h: 330">
                <span class="svc-block-ico"><AppIcon name="message-circle" :size="18" aria-hidden="true" /></span>
                <div>
                  <h4>Datos y mensajes</h4>
                  <p>Qué te pide el formulario y qué aclaraciones lee el cliente junto al presupuesto.</p>
                </div>
              </header>
              <label class="svc-switch">
                <input v-model="designForm.service_ask_address" type="checkbox" role="switch" />
                <span class="svc-switch-track" aria-hidden="true"><i></i></span>
                <span class="check-text">
                  <strong>Pedir dirección en el pedido</strong>
                  <small>Útil si trabajás a domicilio. Si no lo necesitás, el formulario la omite.</small>
                </span>
              </label>
              <div class="grid-2">
                <AppInput v-model="designForm.service_price_note" label="Nota de precios" name="svc_price_note" placeholder="Ej. El valor final se confirma al ver el trabajo" />
                <AppInput v-model="designForm.service_pay_note" label="Nota de pago" name="svc_pay_note" placeholder="Ej. Se paga en persona: efectivo, débito o transferencia" />
              </div>
            </section>

            <p v-if="companyErrs.servicePage" class="field-error" role="alert">{{ companyErrs.servicePage }}</p>
            <div class="btn-row">
              <AppButton :loading="svcBusy" @click="saveServicePage">Guardar configuración</AppButton>
            </div>
          </div>
        </template>
      </template>
    </div>
    <!-- ================= OPINIONES ================= -->
    <div v-if="seen.reviews" v-show="section === 'reviews'" :class="{ 'sec-on': section === 'reviews' }">
      <div class="page-head">
        <div>
          <h1>Opiniones</h1>
          <p>Las valoraciones y comentarios que los visitantes dejan en los productos de tu web.</p>
        </div>
      </div>

      <AlertMessage v-if="catalog.notice" kind="success" :message="catalog.notice" />
      <AlertMessage v-if="catalog.lastError" kind="error" :message="catalog.lastError" />

      <div v-if="store.status === 'loading' || store.status === 'idle'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu tienda…</p></div>

      <div v-else-if="!store.hasStore" class="empty">
        <span class="empty-icon"><AppIcon name="store" :size="28" /></span>
        <h3>Primero creá tu página web</h3>
        <p>Las opiniones se dejan en los productos de tu web. Cuando la tengas, volvé acá para activarlas.</p>
        <button class="btn btn-auto" @click="section = 'store'">Crear mi página web</button>
      </div>

      <div v-else-if="!canProductComments" class="empty">
        <span class="empty-icon"><AppIcon name="star" :size="28" /></span>
        <h3>Las opiniones son una función Premium</h3>
        <p>Con el Plan premium tus clientes valoran tus productos y dejan comentarios que se muestran en tu web. Vos decidís cuáles se ven.</p>
        <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>

      <template v-else>
        <div class="card">
          <h3><AppIcon name="star" :size="18" /> Opiniones de tus clientes</h3>
          <p class="hint">Elegí qué pueden dejar los visitantes en tus productos. Los cambios se aplican al instante.</p>
          <div class="check-list" role="group" aria-label="Opiniones de tus clientes">
            <label class="check-item" :class="{ disabled: reviewToggleBusy }">
              <input type="checkbox" :checked="designForm.show_reviews" :disabled="reviewToggleBusy" @change="toggleShowReviews" />
              <span class="check-text">
                <strong>Valoraciones de productos <span v-if="reviewToggleBusy" class="spinner spinner-brand" aria-hidden="true"></span></strong>
                <small>Los visitantes votan “me gustó” o “no me gustó”; el resultado se ve en el catálogo.</small>
              </span>
            </label>
            <label class="check-item" :class="{ disabled: reviewToggleBusy }">
              <input type="checkbox" :checked="designForm.show_comments" :disabled="reviewToggleBusy" @change="toggleShowComments" />
              <span class="check-text">
                <strong>Comentarios en productos</strong>
                <small>Opinan con nombre, apellido, email y captcha antispam. Los moderás en la lista de abajo.</small>
              </span>
            </label>
          </div>
        </div>

        <div class="card">
          <h3><AppIcon name="checklist" :size="18" /> Opiniones recibidas</h3>
          <p class="hint">Podés borrar las que no quieras mostrar en tu web.</p>
          <div v-if="!catalog.reviews.length" class="empty-mini">
            <AppIcon name="star" :size="22" />
            <div><p>Todavía no recibiste opiniones. Compartí tu link y pediles a tus clientes que te dejen una valoración.</p><button type="button" class="empty-mini-cta" @click="copyLink">Copiar mi link</button></div>
          </div>
          <ul v-else class="rev-list">
            <li v-for="r in catalog.reviews" :key="r.id" class="rev-item">
              <div class="rev-head">
                <span v-if="r.is_positive != null" class="rev-vote" :class="{ down: !r.is_positive }" :title="r.is_positive ? 'Le gustó' : 'No le gustó'">
                  <AppIcon :name="r.is_positive ? 'thumbs-up' : 'thumbs-down'" :size="14" />
                </span>
                <strong>{{ r.name }} {{ r.surname }}</strong>
                <span class="rev-mail">{{ r.email }}</span>
                <span class="rev-date">{{ fmtDate(r.created_at) }}</span>
              </div>
              <p v-if="r.text" class="rev-text">{{ r.text }}</p>
              <div class="rev-foot">
                <span class="rev-prod"><AppIcon name="package" :size="12" /> {{ r.product_name }}</span>
                <button
                  type="button" class="icon-btn danger" :disabled="reviewDeleting === r.id"
                  :aria-label="`Eliminar la opinión de ${r.name}`" @click="onDeleteReview(r)"
                >
                  <span v-if="reviewDeleting === r.id" class="spinner" aria-hidden="true"></span>
                  <AppIcon v-else name="trash" :size="15" />
                </button>
              </div>
            </li>
          </ul>
        </div>
      </template>
    </div>
    <!-- ================= MI TIENDA ================= -->
    <div v-if="seen.store" v-show="section === 'store'" :class="{ 'sec-on': section === 'store' }">
      <div class="page-head">
        <div>
          <h1>Mi página web</h1>
          <p>Esta es la dirección de tu negocio en internet. Compartila por WhatsApp, Instagram o donde quieras.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="store" @select="section = $event" />

      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <div v-if="store.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu tienda…</p></div>
      <template v-else-if="store.hasStore">
        <div class="card">
          <h3><AppIcon name="share-2" :size="18" /> Tu dirección web</h3>
          <AlertMessage
            v-if="store.store.is_blocked"
            kind="error"
            :message="`Tu web fue bloqueada por DAVENT${store.store.blocked_reason ? ` — motivo: ${store.store.blocked_reason}` : ''}. Si creés que es un error, escribime desde la sección de ayuda.`"
          />
          <div class="link-bar">
            <code class="mono link-url">{{ publicUrl }}</code>
            <span class="pill" :class="store.store.is_blocked ? 'danger' : (store.store.is_published ? 'ok' : 'muted')">{{ store.store.is_blocked ? 'Bloqueada' : (store.store.is_published ? 'Activo' : 'Pausado') }}</span>
          </div>
          <div class="btn-row link-actions">
            <button class="btn btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar dirección</button>
            <button class="btn secondary btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
            <button class="btn ghost btn-auto" :disabled="storeBusy" @click="togglePublished">{{ store.store.is_published ? 'Pausar mi página' : 'Volver a publicarla' }}</button>
          </div>
          <p class="hint">Si la pausás, tus clientes ven un cartel de “tienda no disponible” hasta que la vuelvas a publicar.</p>
        </div>

        <details class="card more-card">
          <summary><AppIcon name="pencil" :size="18" /> Cambiar mi dirección <small>Solo si de verdad lo necesitás</small></summary>
          <div class="field">
            <label for="rename-slug">Nuevo link <TipHint text="El «slug» es la última parte de tu dirección web: lo que va después de la barra. Tiene que ser corto y fácil de decir, como el nombre de tu negocio." /></label>
            <div class="slug-box" :class="{ invalid: renameKind === 'err' || !!store.fieldErrors.slug }">
              <span class="slug-prefix">{{ slugPrefix }}</span>
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
              <span v-if="storeSubdomains" class="slug-suffix">.{{ platformHost }}</span>
            </div>
            <p class="hint">Ojo: la dirección anterior deja de funcionar, y tendrás que avisarle a tus clientes.</p>
            <p v-if="store.fieldErrors.slug" class="field-error" role="alert">{{ store.fieldErrors.slug }}</p>
            <p v-else-if="renameMsg" class="slug-check" :class="renameKind" role="status">
              <AppIcon v-if="renameCheck === 'available'" name="circle-check" :size="14" />
              <span v-else-if="renameCheck === 'checking'" class="spinner spinner-brand" aria-hidden="true"></span>
              {{ renameMsg }}
            </p>
          </div>
          <button class="btn btn-auto" :disabled="!canRename" @click="saveRename">
            <span v-if="renameBusy" class="spinner" aria-hidden="true"></span>Guardar nueva dirección
          </button>
        </details>

        <div v-if="canCustomize" class="next-card">
          <span class="next-icon"><AppIcon name="palette" :size="22" /></span>
          <div><strong>Dale tu estilo a tu página</strong><small>Poné tu logo, tus colores y contá qué hacés.</small></div>
          <button class="btn btn-auto" @click="section = 'design'">Personalizar <AppIcon name="arrow-right" :size="16" /></button>
        </div>
        <div class="next-card">
          <span class="next-icon"><AppIcon name="package" :size="22" /></span>
          <div><strong>Cargá tus productos</strong><small>Es lo primero que ven tus clientes al entrar.</small></div>
          <button class="btn secondary btn-auto" @click="section = 'catalogs'">Ir a mis productos <AppIcon name="arrow-right" :size="16" /></button>
        </div>
      </template>
    </div>
    <!-- ================= PLANTILLAS (páginas de la web) ================= -->
    <div v-if="seen.pages" v-show="section === 'pages'" :class="{ 'sec-on': section === 'pages' }">
      <div class="page-head">
        <div>
          <h1>Plantillas de tu web</h1>
          <p>Tu sitio puede tener hasta {{ siteTemplatesMax === null ? 'tres' : siteTemplatesMax }} páginas. Elegí cuáles mostrar: se guardan al instante.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="pages" @select="section = $event" />

      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <div class="card">
        <h3><AppIcon name="layout-grid" :size="18" /> Páginas activas</h3>
        <p class="lead">Cada página es una sección distinta de tu misma web. Desmarcar una la apaga sin borrar su contenido.</p>
        <div class="check-list" role="group" aria-label="Páginas de tu web">
          <label v-for="key in siteTemplateKeys" :key="key" class="check-item" :class="{ disabled: !allowedSiteTemplates.includes(key) }">
            <input type="checkbox" :checked="designSiteTemplates.includes(key)" :disabled="!canToggleSiteTemplate(key)" @change="toggleSiteTemplate(key)" />
            <span class="check-text">
              <strong>
                <AppIcon :name="siteTemplates[key].icon" :size="15" aria-hidden="true" /> {{ siteTemplates[key].label }}
                <span v-if="siteTemplateLock(key)" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> {{ siteTemplateLock(key) }}</span>
                <span v-if="siteTemplatesBusy" class="spinner spinner-brand" aria-hidden="true"></span>
              </strong>
              <small>{{ siteTemplates[key].desc }}</small>
            </span>
          </label>
        </div>
        <p class="hint">{{ siteTemplatesHint }} La web siempre conserva al menos una página.</p>
        <p v-if="!canServicesSite" class="hint">La página <strong>Servicios</strong> se habilita desde el plan Estándar: tus clientes arman su presupuesto y te llega el pedido por WhatsApp, sin pagos online.</p>
      </div>

      <div v-if="canServicesSite" class="next-card">
        <span class="next-icon"><AppIcon name="wrench" :size="22" /></span>
        <div><strong>¿Tenés la página Servicios activa?</strong><small>Cargá tus servicios con precios orientativos y recibí pedidos por WhatsApp.</small></div>
        <button class="btn btn-auto" @click="section = 'services'">Ir a mis servicios <AppIcon name="arrow-right" :size="16" /></button>
      </div>
      <div v-else class="next-card">
        <span class="next-icon"><AppIcon name="crown" :size="22" /></span>
        <div><strong>Servicios es un plan Estándar</strong><small>Sumala a tu web subiendo de plan: presupuestos orientativos y pedidos por WhatsApp.</small></div>
        <button class="btn secondary btn-auto" @click="section = 'plans'">Ver planes <AppIcon name="arrow-right" :size="16" /></button>
      </div>
    </div>
    <!-- ================= DISEÑO (4 sub-secciones) ================= -->
    <div v-if="seen.design" v-show="section === 'design'" :class="{ 'sec-on': section === 'design' }">
      <div class="page-head">
        <div>
          <h1>Diseño de mi página</h1>
          <p>Elegí el estilo, ajustá todo en el Studio o dejá que la IA lo arme. Cuando guardás, tu página se actualiza al instante.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="design" @select="section = $event" />

      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <template v-if="canCustomize">
        <div class="dsg-wrap">
          <div class="dsg-nav">
            <nav class="dsg-cards" role="tablist" aria-label="Cómo querés diseñar">
              <button
                v-for="t in designTabs" :key="t.id" type="button" role="tab"
                class="dsg-card-btn" :class="{ active: designTab === t.id, locked: designTabLocked(t) }"
                :aria-selected="designTab === t.id" @click="openDesignTab(t)"
              >
                <span class="dsg-card-ico"><AppIcon :name="t.icon" :size="18" /></span>
                <span class="dsg-card-txt">
                  <strong>{{ t.label }}</strong>
                  <small>{{ t.desc }}</small>
                </span>
                <span v-if="designTabLocked(t)" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /></span>
              </button>
            </nav>
            <nav class="dsg-tabs dsg-tabs-sub" role="tablist" aria-label="Contenido de mi web">
              <button v-for="t in designContentTabs" :key="t.id" type="button" role="tab" class="dsg-tab" :class="{ active: designTab === t.id }" :aria-selected="designTab === t.id" @click="designTab = t.id">
                <AppIcon :name="t.icon" :size="15" /> {{ t.label }}
              </button>
            </nav>
          </div>
        <template v-if="designTab === 'look'">
          <DesignStylesTab
            v-model:preview-open="lookPreview"
            :form="designForm"
            :benefits="plan?.benefits || {}"
            :shop-name="designShopName"
            :can-studio="canDesignAdvanced"
            @navigate="onDesignNav"
            @ring="lookRing = $event"
            @open-studio="openStudioRoute"
          />
          <div class="dsg-savebar" :class="{ dirty: designDirty }">
            <p class="dsg-state" :class="{ dirty: designDirty }" role="status">
              <span v-if="designDirty" class="dsg-dot" aria-hidden="true"></span>
              <span>{{ designDirty ? 'Cambios sin guardar' : 'Todo guardado' }}</span>
            </p>
            <div class="dsg-actions">
              <button v-if="designDirty" type="button" class="btn ghost btn-auto" :disabled="designBusy" @click="discardDesign"><AppIcon name="undo" :size="16" /> Descartar</button>
              <AppButton :loading="designBusy" type="button" @click="saveDesign()">Guardar diseño</AppButton>
            </div>
          </div>
        </template>
        <div v-else-if="designTab === 'assisted'" class="dsg-ai">
          <AiDesignView :plan="plan" @applied="onAiApplied" @navigate="onDesignNav" />
        </div>
        <div v-else class="dsg-layout">
          <div class="dsg-main">
          <div v-show="designTab === 'content'" class="card dsg-card">
            <h3><AppIcon name="pencil" :size="18" /> Contenido</h3>
            <section class="form-group">
              <header class="form-group-head"><span class="fg-icon"><AppIcon name="store" :size="17" /></span><div><strong>Presentación</strong><small>Lo primero que ve tu cliente al entrar.</small></div></header>
              <AppInput v-model="designForm.display_name" label="Nombre visible" name="design_display_name" icon="store" :placeholder="business || 'Tu negocio'" hint="El nombre que aparece junto a tu logo. Vacío: se usa tu nombre de negocio." :error="designFieldErr('display_name')" @blur="designTouched.display_name = true" />
              <AppInput v-model="designForm.headline" label="Titular" name="design_headline" icon="type" placeholder="Ej. Indumentaria y calzado en Salta" hint="Frase corta bajo el nombre de tu negocio (opcional, hasta 140 caracteres)." :error="designFieldErr('headline')" @blur="designTouched.headline = true" />
              <div class="field">
                <label for="design-description"><AppIcon name="file-text" :size="14" class="label-icon" aria-hidden="true" />Descripción <span class="counter" :class="{ warn: designForm.description.length > 720 }">{{ designForm.description.length }}/800</span></label>
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
                <p class="hint">Aparece debajo del titular.</p>
                <p v-if="designFieldErr('description')" class="field-error" role="alert">{{ designFieldErr('description') }}</p>
              </div>
            </section>
            <section class="form-group">
              <header class="form-group-head"><span class="fg-icon wa"><AppIcon name="message-circle" :size="17" /></span><div><strong>Contacto</strong><small>Por dónde te escriben tus clientes.</small></div></header>
              <AppInput v-model="designForm.whatsapp" label="WhatsApp de contacto" name="design_whatsapp" icon="whatsapp" placeholder="+5493871551234" hint="Formato internacional. Genera un botón de chat en tu web." :error="designFieldErr('whatsapp')" @blur="designTouched.whatsapp = true" />
              <AppInput v-model="designForm.contact_email" label="Email de contacto público" name="design_contact_email" icon="mail" type="email" placeholder="contacto@tunegocio.com" hint="A esta casilla llegan los mensajes del formulario Contáctanos. Vacío: se usa el email de tu cuenta." :error="designFieldErr('contact_email')" @blur="designTouched.contact_email = true" />
            </section>
            <section class="form-group">
              <header class="form-group-head"><span class="fg-icon ig"><AppIcon name="share-2" :size="17" /></span><div><strong>Redes sociales</strong><small>Se muestran como botones en tu web.</small></div></header>
              <div class="grid-2">
                <AppInput v-model="designForm.instagram" label="Instagram" name="design_instagram" icon="instagram" placeholder="tu.negocio" hint="Solo el usuario, sin @." :error="designFieldErr('instagram')" @blur="designTouched.instagram = true" />
                <AppInput v-model="designForm.tiktok" label="TikTok" name="design_tiktok" icon="tiktok" placeholder="tu.negocio" hint="Solo el usuario, sin @." :error="designFieldErr('tiktok')" @blur="designTouched.tiktok = true" />
              </div>
              <AppInput v-model="designForm.facebook" label="Facebook" name="design_facebook" icon="facebook" placeholder="tu.negocio o URL de tu página" hint="Nombre de tu página o pegá el link completo." :error="designFieldErr('facebook')" @blur="designTouched.facebook = true" />
            </section>
          </div>
          <div v-show="designTab === 'images'" class="card dsg-card">
            <h3><AppIcon name="images" :size="18" /> Imágenes</h3>
            <div class="field">
              <label id="design-logo-label">Logo</label>
              <div class="carousel-box">
                <div v-if="currentLogo" class="carousel-thumb">
                  <img :src="currentLogo" alt="Logo de tu tienda" />
                  <div class="carousel-thumb-actions">
                    <button type="button" class="icon-btn danger" aria-label="Quitar logo" :disabled="logoBusy" @click="onRemoveLogo"><AppIcon name="trash" :size="13" /></button>
                  </div>
                </div>
                <button type="button" class="carousel-add" :disabled="logoBusy" @click="logoInput?.click()">
                  <span v-if="logoBusy" class="spinner" aria-hidden="true"></span>
                  <AppIcon v-else name="image" :size="20" />
                  {{ currentLogo ? 'Cambiar logo' : 'Subir logo' }}
                </button>
              </div>
              <input ref="logoInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-logo-label" @change="onLogoPicked" />
              <p class="hint">PNG, JPG, WebP o GIF de hasta 2 MB. Mejor si es cuadrado.</p>
              <p v-if="logoErr" class="field-error" role="alert">{{ logoErr }}</p>
            </div>
            <div class="field" :class="{ locked: !canDesignAdvanced }">
              <label id="design-cover-label">Foto de portada <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="carousel-box">
                <div v-if="currentCover" class="carousel-thumb">
                  <img :src="currentCover" alt="Portada actual de tu web" />
                  <div class="carousel-thumb-actions">
                    <button v-if="canDesignAdvanced" type="button" class="icon-btn danger" aria-label="Quitar portada" :disabled="coverBusy" @click="onRemoveCover"><AppIcon name="trash" :size="13" /></button>
                  </div>
                </div>
                <button type="button" class="carousel-add" :disabled="coverBusy || !canDesignAdvanced" @click="coverInput?.click()">
                  <span v-if="coverBusy" class="spinner" aria-hidden="true"></span>
                  <AppIcon v-else name="image" :size="20" />
                  {{ currentCover ? 'Cambiar portada' : 'Subir portada' }}
                </button>
              </div>
              <input ref="coverInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-cover-label" :disabled="!canDesignAdvanced" @change="onCoverPicked" />
              <p class="hint">Foto apaisada y luminosa de hasta 4 MB; la ajustamos sola.</p>
              <p v-if="coverErr" class="field-error" role="alert">{{ coverErr }}</p>
            </div>
            <div class="field" :class="{ locked: !canGallery }">
              <label id="design-gallery-label">Galería de imágenes <span v-if="!canGallery" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Con plan activo</span></label>
              <div v-if="canGallery || galleryImages.length" class="carousel-box">
                <div v-for="(img, i) in galleryImages" :key="img.id" class="carousel-thumb">
                  <img :src="img.url" :alt="`Imagen ${i + 1} de la galería`" />
                  <div class="carousel-thumb-actions">
                    <button type="button" class="icon-btn" aria-label="Mover a la izquierda" :disabled="i === 0 || galleryBusy" @click="onMoveGallery(img.id, -1)"><AppIcon name="chevron-left" :size="13" /></button>
                    <button type="button" class="icon-btn" aria-label="Mover a la derecha" :disabled="i === galleryImages.length - 1 || galleryBusy" @click="onMoveGallery(img.id, 1)"><AppIcon name="chevron-right" :size="13" /></button>
                    <button type="button" class="icon-btn danger" aria-label="Eliminar imagen" :disabled="galleryBusy" @click="onRemoveGallery(img.id)"><AppIcon name="trash" :size="13" /></button>
                  </div>
                </div>
                <button
                  v-if="canAddGallery"
                  type="button" class="carousel-add" :disabled="galleryBusy"
                  @click="galleryInput?.click()"
                >
                  <span v-if="galleryBusy" class="spinner" aria-hidden="true"></span>
                  <AppIcon v-else name="images" :size="20" />
                  Agregar
                </button>
              </div>
              <input ref="galleryInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-gallery-label" @change="onGalleryPicked" />
              <p class="hint">{{ galleryHint }}</p>
              <p v-if="galleryErr" class="field-error" role="alert">{{ galleryErr }}</p>
            </div>
            <div v-if="canDesignAdvanced || decorImages.length" class="field" :class="{ locked: !canDesignAdvanced }">
              <label id="design-decor-label">Imágenes decorativas de la portada <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="carousel-box">
                <div v-for="(img, i) in decorImages" :key="img.id" class="carousel-thumb">
                  <img :src="img.url" :alt="`Imagen decorativa ${i + 1}`" />
                  <div class="carousel-thumb-actions">
                    <button type="button" class="icon-btn danger" aria-label="Eliminar imagen" :disabled="galleryBusy" @click="onRemoveGallery(img.id)"><AppIcon name="trash" :size="13" /></button>
                  </div>
                </div>
                <button v-if="canAddDecor" type="button" class="carousel-add" :disabled="galleryBusy" @click="decorInput?.click()">
                  <span v-if="galleryBusy" class="spinner" aria-hidden="true"></span>
                  <AppIcon v-else name="images" :size="20" />
                  Agregar
                </button>
              </div>
              <input ref="decorInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-decor-label" @change="onDecorPicked" />
              <p class="hint">Hasta {{ DECOR_MAX_IMAGES }} imágenes ilustrativas que decoran tu página principal: una enmarca Sobre nosotros, otra abre una banda a lo ancho y el resto va bajo la portada. Gastan cupo de tu galería ({{ galleryUsed }}{{ galleryMax === null ? '' : ` de ${galleryMax}` }} usadas).</p>
            </div>
          </div>
          <div v-show="designTab === 'sections'" class="card dsg-card">
            <h3><AppIcon name="layout-grid" :size="18" /> Secciones</h3>
            <div class="field">
              <label id="site-templates-label">¿Qué páginas tiene tu web?</label>
              <div class="check-list" role="group" aria-labelledby="site-templates-label">
                <label v-for="key in siteTemplateKeys" :key="key" class="check-item" :class="{ disabled: !allowedSiteTemplates.includes(key) }">
                  <input type="checkbox" :checked="designSiteTemplates.includes(key)" :disabled="!canToggleSiteTemplate(key)" @change="toggleSiteTemplate(key)" />
                  <span class="check-text">
                    <strong>{{ siteTemplates[key].label }} <span v-if="siteTemplateLock(key)" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> {{ siteTemplateLock(key) }}</span></strong>
                    <small>{{ siteTemplates[key].desc }}</small>
                  </span>
                </label>
              </div>
              <p class="hint">{{ siteTemplatesHint }} Se guarda al instante.</p>
            </div>
            <div class="field">
              <label id="design-theme-toggle-label"><AppIcon name="moon" :size="14" class="label-icon" aria-hidden="true" />Modo noche en tu web</label>
              <label class="check-item">
                <input v-model="designForm.theme_toggle" type="checkbox" aria-labelledby="design-theme-toggle-label" />
                <span class="check-text">
                  <strong>Mostrar botón claro/oscuro al visitante</strong>
                  <small>Un botón sol/luna en la barra superior para alternar el tema. Circuito y Seguridad son oscuros por defecto: con esto el visitante puede pasarlos a claro.</small>
                </span>
              </label>
              <p class="hint">Se guarda con el diseño.</p>
            </div>
            <div v-if="designSiteTemplates.includes('landing')" class="field">
              <label id="design-sections-label">Secciones de tu web</label>
              <div class="check-list" role="group" aria-labelledby="design-sections-label">
                <label class="check-item">
                  <input v-model="designForm.show_highlights" type="checkbox" />
                  <span class="check-text">
                    <strong>Franja de etiquetas</strong>
                    <small>Cuatro destacados breves bajo la portada (catálogo, consultas, ubicación, trayectoria).</small>
                  </span>
                </label>
                <label class="check-item">
                  <input v-model="designForm.show_about" type="checkbox" />
                  <span class="check-text">
                    <strong>Sobre nosotros</strong>
                    <small>Historia, especialidades y misión. El contenido se edita en "Sobre mi negocio".</small>
                  </span>
                </label>
                <label class="check-item">
                  <input v-model="designForm.show_gallery" type="checkbox" />
                  <span class="check-text">
                    <strong>Galería</strong>
                    <small>Grilla de imágenes del negocio. Se oculta sola si no hay ninguna cargada.</small>
                  </span>
                </label>
                <label class="check-item">
                  <input v-model="designForm.show_contact" type="checkbox" />
                  <span class="check-text">
                    <strong>Contáctanos</strong>
                    <small>Formulario con verificación antispam, tus canales y el mapa.</small>
                  </span>
                </label>
                <label class="check-item">
                  <input v-model="designForm.show_offers" type="checkbox" />
                  <span class="check-text">
                    <strong>Ofertas</strong>
                    <small>Tira de productos en oferta del catálogo. Se oculta sola si no hay ninguna vigente.</small>
                  </span>
                </label>
                <label class="check-item">
                  <input v-model="designForm.show_brands" type="checkbox" />
                  <span class="check-text">
                    <strong>Marcas</strong>
                    <small>Marquesina con las marcas cargadas en tu catálogo. Se oculta sola si no hay ninguna.</small>
                  </span>
                </label>
                <label class="check-item">
                  <input v-model="designForm.show_countdown" type="checkbox" />
                  <span class="check-text">
                    <strong>Cuenta regresiva</strong>
                    <small>Contador hasta el fin del descuento vigente más próximo. Se oculta sola si no hay ninguno con fecha.</small>
                  </span>
                </label>
                <label class="check-item" :class="{ disabled: !canLocationMap }">
                  <input v-model="designForm.show_location" type="checkbox" :disabled="!canLocationMap" />
                  <span class="check-text">
                    <strong>Mapa de ubicación <span v-if="!canLocationMap" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Desde Estándar</span></strong>
                    <small>Tu domicilio dentro de Contáctanos. Se carga desde "Mi cuenta".</small>
                  </span>
                </label>
              </div>
            </div>
          </div>
          <div ref="dsgBar" class="dsg-savebar" :class="{ dirty: designDirty }">
            <p class="dsg-state" :class="{ dirty: designDirty }" role="status">
              <span v-if="designDirty" class="dsg-dot" aria-hidden="true"></span>
              <AppIcon v-else name="circle-check" :size="16" aria-hidden="true" />
              <span>{{ designDirty ? 'Cambios sin guardar' : 'Todo guardado' }}</span>
            </p>
            <button type="button" class="btn ghost btn-auto dsg-preview-open" :aria-expanded="previewSheet" @click="previewSheet = !previewSheet"><AppIcon name="eye" :size="16" /> Ver vista previa</button>
            <div class="dsg-actions">
              <button v-if="designDirty" type="button" class="btn ghost btn-auto" :disabled="designBusy" @click="discardDesign"><AppIcon name="undo" :size="16" /> Descartar</button>
              <AppButton :loading="designBusy" type="button" @click="saveDesign()">Guardar diseño</AppButton>
            </div>
          </div>
          </div>

        <DesignPreview
          v-model:open="previewSheet"
          :form="designForm"
          :vars="designPreviewVars"
          :template="designTemplate"
          :shop-name="designShopName"
          :initial="businessInitial"
          :logo="currentLogo"
          :cover="currentCover"
          :advanced="canDesignAdvanced"
          :catalog-on="designCatalogOn"
          :show-map="canLocationMap && Boolean(designForm.show_location)"
          :carousel="carouselImages"
          :slide="previewSlide"
          :name-font="designNameFont"
          :ring="lookRing"
          :sheet-bottom="previewBottom"
        />
        </div>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
        <h3>El diseño web viene con tu plan</h3>
        <p>Activá una suscripción para personalizar el logo, el titular, la descripción y los botones de contacto de tu página pública.</p>
        <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>
    </div>
    <!-- ================= MI EMPRESA (marketing de la portada) ================= -->
    <div v-if="seen.company" v-show="section === 'company'" :class="{ 'sec-on': section === 'company' }">
      <div class="page-head">
        <div>
          <h1>Sobre mi negocio</h1>
          <p>Contale a tus clientes quién sos, qué ofrecés y cuándo atendés. Cada bloque es opcional: si lo dejás vacío, no se muestra.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="company" @select="section = $event" />

      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <template v-if="canCustomize">
        <nav class="mk-nav" aria-label="Bloques de contenido">
          <button v-for="l in mkNav" :key="l.id" type="button" class="mk-chip" @click="scrollToCard(l.id)">{{ l.label }}</button>
        </nav>

        <!-- ===== Sobre nosotros ===== -->
        <div id="mk-about" class="card mk-card">
          <h3><AppIcon name="building-2" :size="18" /> Sobre nosotros</h3>
          <AppInput v-model="designForm.about_title" label="Título de la sección" name="company_about_title" placeholder="Sobre nosotros" hint="Encabezado de la sección en tu web. Vacío: se muestra 'Sobre nosotros'." :error="designFieldErr('about_title')" @blur="designTouched.about_title = true" />
          <div class="field">
            <label for="company-about-text">Descripción de la empresa</label>
            <textarea
              id="company-about-text"
              v-model="designForm.about_text"
              class="textarea"
              :class="{ invalid: designFieldErr('about_text') }"
              placeholder="Contá la historia de tu negocio: qué hacen, hace cuánto y qué los diferencia"
              maxlength="2000"
              rows="6"
              @blur="designTouched.about_text = true"
            ></textarea>
            <p class="hint">El texto principal de la sección. {{ designForm.about_text.length }}/2000</p>
            <p v-if="designFieldErr('about_text')" class="field-error" role="alert">{{ designFieldErr('about_text') }}</p>
          </div>
          <div class="grid-2">
            <AppInput v-model="designForm.about_years" label="Años de trayectoria" name="company_about_years" type="number" placeholder="Ej. 15" hint="Se muestra destacado en la sección. Vacío: no se muestra." :error="designFieldErr('about_years')" @blur="designTouched.about_years = true" />
            <AppInput v-model="designForm.about_specialties" label="Especialidades" name="company_about_specialties" placeholder="Ej. Venta mayorista, Envíos, Atención personalizada" hint="Separadas por coma: aparecen como etiquetas en la sección." :error="designFieldErr('about_specialties')" @blur="designTouched.about_specialties = true" />
          </div>
          <div class="field">
            <label for="company-about-mission">Misión</label>
            <textarea
              id="company-about-mission"
              v-model="designForm.about_mission"
              class="textarea"
              :class="{ invalid: designFieldErr('about_mission') }"
              placeholder="Qué busca lograr tu empresa cada día"
              maxlength="400"
              rows="3"
              @blur="designTouched.about_mission = true"
            ></textarea>
            <p class="hint">Se muestra destacada debajo de la descripción. {{ designForm.about_mission.length }}/400</p>
            <p v-if="designFieldErr('about_mission')" class="field-error" role="alert">{{ designFieldErr('about_mission') }}</p>
          </div>
          <p class="hint">La sección se apaga desde "Cómo se ve", en la pestaña "Qué mostrar". También se oculta sola si no cargaste ningún contenido.</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveCompany">Guardar información</AppButton>
          </div>
        </div>

        <!-- ===== Qué ofrecemos (servicios/ventajas con ícono) ===== -->
        <div id="mk-services" class="card mk-card">
          <h3><AppIcon name="layout-grid" :size="18" /> Qué ofrecemos</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_services" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Tarjetas con ícono que resumen tus servicios o ventajas. Se ocultan solas si no cargás ninguna.</small>
              </span>
            </label>
          </div>
          <AppInput v-model="designForm.services_title" label="Título de la sección" name="company_services_title" placeholder="Qué ofrecemos" hint="Vacío: se muestra 'Qué ofrecemos'." maxlength="80" />
          <div class="field">
            <label>Servicios o ventajas <span class="hint-inline">({{ designForm.services.length }}/{{ mkLimits.services }})</span></label>
            <div v-if="designForm.services.length" class="qa-list">
              <div v-for="(s, i) in designForm.services" :key="i" class="qa-item">
                <div class="qa-fields">
                  <div class="mk-icon-field">
                    <span class="mk-icon-preview" aria-hidden="true"><AppIcon :name="serviceIcons[s.icon] ? s.icon : 'package'" :size="17" /></span>
                    <select v-model="s.icon" class="select" :aria-label="`Ícono del servicio ${i + 1}`">
                      <option v-for="(label, key) in serviceIcons" :key="key" :value="key">{{ label }}</option>
                    </select>
                  </div>
                  <input v-model="s.title" class="input" type="text" :maxlength="mkLimits.serviceTitle" placeholder="Ej. Envíos a todo el país" :aria-label="`Título del servicio ${i + 1}`" />
                  <textarea v-model="s.text" class="textarea" rows="2" :maxlength="mkLimits.serviceText" placeholder="Una línea que lo describa" :aria-label="`Descripción del servicio ${i + 1}`"></textarea>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el servicio ${i + 1}`" @click="moveRow(designForm.services, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.services.length - 1" :aria-label="`Bajar el servicio ${i + 1}`" @click="moveRow(designForm.services, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el servicio ${i + 1}`" @click="designForm.services.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.services.length >= mkLimits.services" @click="addRow(designForm.services, mkLimits.services, { icon: 'package', title: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar servicio
            </button>
            <p class="hint">Se muestran como tarjetas con ícono. Ordenalas con las flechas.</p>
            <p v-if="companyErrs.services" class="field-error" role="alert">{{ companyErrs.services }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveServices">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Tus números (cifras destacadas) ===== -->
        <div id="mk-stats" class="card mk-card">
          <h3><AppIcon name="trending-up" :size="18" /> Tus números</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_stats" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Banda de cifras que resume tu negocio: clientes, años, productos vendidos.</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Cifras <span class="hint-inline">({{ designForm.stats.length }}/{{ mkLimits.stats }})</span></label>
            <div v-if="designForm.stats.length" class="qa-list">
              <div v-for="(s, i) in designForm.stats" :key="i" class="qa-item">
                <div class="qa-fields mk-pair">
                  <input v-model="s.value" class="input" type="text" :maxlength="mkLimits.statValue" placeholder="+500" :aria-label="`Valor de la cifra ${i + 1}`" />
                  <input v-model="s.label" class="input" type="text" :maxlength="mkLimits.statLabel" placeholder="clientes que nos eligen" :aria-label="`Etiqueta de la cifra ${i + 1}`" />
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir la cifra ${i + 1}`" @click="moveRow(designForm.stats, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.stats.length - 1" :aria-label="`Bajar la cifra ${i + 1}`" @click="moveRow(designForm.stats, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar la cifra ${i + 1}`" @click="designForm.stats.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.stats.length >= mkLimits.stats" @click="addRow(designForm.stats, mkLimits.stats, { value: '', label: '' })">
              <AppIcon name="plus" :size="15" /> Agregar cifra
            </button>
            <p class="hint">Ej. "+500" y "clientes", o "15" y "años de trayectoria". Se ven en grande en una banda de tu portada.</p>
            <p v-if="companyErrs.stats" class="field-error" role="alert">{{ companyErrs.stats }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveStats">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Testimonios ===== -->
        <div id="mk-testimonials" class="card mk-card">
          <h3><AppIcon name="quote" :size="18" /> Testimonios</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_testimonials" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Opiniones de tus clientes: la mejor prueba social para vender más.</small>
              </span>
            </label>
          </div>
          <AppInput v-model="designForm.testimonials_title" label="Título de la sección" name="company_testimonials_title" placeholder="Lo que dicen nuestros clientes" hint="Vacío: se muestra 'Lo que dicen nuestros clientes'." maxlength="80" />
          <div class="field">
            <label>Testimonios <span class="hint-inline">({{ designForm.testimonials.length }}/{{ mkLimits.testimonials }})</span></label>
            <div v-if="designForm.testimonials.length" class="qa-list">
              <div v-for="(t, i) in designForm.testimonials" :key="i" class="qa-item">
                <div class="qa-fields">
                  <div class="mk-pair">
                    <input v-model="t.name" class="input" type="text" :maxlength="mkLimits.testimonialName" placeholder="Nombre del cliente" :aria-label="`Nombre del testimonio ${i + 1}`" />
                    <input v-model="t.detail" class="input" type="text" :maxlength="mkLimits.testimonialDetail" placeholder="Detalle opcional. Ej. Cliente desde 2019" :aria-label="`Detalle del testimonio ${i + 1}`" />
                  </div>
                  <textarea v-model="t.text" class="textarea" rows="2" :maxlength="mkLimits.testimonialText" placeholder="Lo que dijo de tu negocio" :aria-label="`Texto del testimonio ${i + 1}`"></textarea>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el testimonio ${i + 1}`" @click="moveRow(designForm.testimonials, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.testimonials.length - 1" :aria-label="`Bajar el testimonio ${i + 1}`" @click="moveRow(designForm.testimonials, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el testimonio ${i + 1}`" @click="designForm.testimonials.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.testimonials.length >= mkLimits.testimonials" @click="addRow(designForm.testimonials, mkLimits.testimonials, { name: '', detail: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar testimonio
            </button>
            <p class="hint">Publicá solo opiniones reales de clientes que te hayan autorizado a usarlas.</p>
            <p v-if="companyErrs.testimonials" class="field-error" role="alert">{{ companyErrs.testimonials }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveTestimonials">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Preguntas frecuentes ===== -->
        <div id="mk-faqs" class="card mk-card">
          <h3><AppIcon name="message-circle" :size="18" /> Preguntas frecuentes</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_faq" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Respuestas que se despliegan al tocarlas: ahorran consultas repetidas.</small>
              </span>
            </label>
          </div>
          <AppInput v-model="designForm.faqs_title" label="Título de la sección" name="company_faqs_title" placeholder="Preguntas frecuentes" hint="Vacío: se muestra 'Preguntas frecuentes'." maxlength="80" />
          <div class="field">
            <label>Preguntas y respuestas <span class="hint-inline">({{ designForm.faqs.length }}/{{ mkLimits.faqs }})</span></label>
            <div v-if="designForm.faqs.length" class="qa-list">
              <div v-for="(f, i) in designForm.faqs" :key="i" class="qa-item">
                <div class="qa-fields">
                  <input v-model="f.q" class="input" type="text" :maxlength="mkLimits.faqQ" placeholder="Ej. ¿Hacen envíos?" :aria-label="`Pregunta ${i + 1}`" />
                  <textarea v-model="f.a" class="textarea" rows="2" :maxlength="mkLimits.faqA" placeholder="Respuesta que ve la visita" :aria-label="`Respuesta ${i + 1}`"></textarea>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir la pregunta ${i + 1}`" @click="moveRow(designForm.faqs, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.faqs.length - 1" :aria-label="`Bajar la pregunta ${i + 1}`" @click="moveRow(designForm.faqs, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar la pregunta ${i + 1}`" @click="designForm.faqs.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.faqs.length >= mkLimits.faqs" @click="addRow(designForm.faqs, mkLimits.faqs, { q: '', a: '' })">
              <AppIcon name="plus" :size="15" /> Agregar pregunta
            </button>
            <p v-if="companyErrs.faqs" class="field-error" role="alert">{{ companyErrs.faqs }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveFaqs">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Garantías y beneficios ===== -->
        <div id="mk-benefits" class="card mk-card">
          <h3><AppIcon name="shield-check" :size="18" /> Garantías y beneficios</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_benefits" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Envíos, garantías, medios de pago, devoluciones. Se oculta sola si no cargás ninguno.</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Beneficios <span class="hint-inline">({{ designForm.benefits.length }}/{{ mkLimits.benefits }})</span></label>
            <div v-if="designForm.benefits.length" class="qa-list">
              <div v-for="(b, i) in designForm.benefits" :key="i" class="qa-item">
                <div class="qa-fields">
                  <div class="mk-icon-field">
                    <span class="mk-icon-preview" aria-hidden="true"><AppIcon :name="serviceIcons[b.icon] ? b.icon : 'shield-check'" :size="17" /></span>
                    <select v-model="b.icon" class="select" :aria-label="`Ícono del beneficio ${i + 1}`">
                      <option v-for="(label, key) in serviceIcons" :key="key" :value="key">{{ label }}</option>
                    </select>
                  </div>
                  <input v-model="b.title" class="input" type="text" :maxlength="mkLimits.benefitTitle" placeholder="Ej. Garantía de 30 días" :aria-label="`Título del beneficio ${i + 1}`" />
                  <textarea v-model="b.text" class="textarea" rows="2" :maxlength="mkLimits.benefitText" placeholder="Una línea que lo describa" :aria-label="`Descripción del beneficio ${i + 1}`"></textarea>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el beneficio ${i + 1}`" @click="moveRow(designForm.benefits, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.benefits.length - 1" :aria-label="`Bajar el beneficio ${i + 1}`" @click="moveRow(designForm.benefits, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el beneficio ${i + 1}`" @click="designForm.benefits.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.benefits.length >= mkLimits.benefits" @click="addRow(designForm.benefits, mkLimits.benefits, { icon: 'shield-check', title: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar beneficio
            </button>
            <p v-if="companyErrs.benefits" class="field-error" role="alert">{{ companyErrs.benefits }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveBenefits">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Línea de tiempo ===== -->
        <div id="mk-timeline" class="card mk-card">
          <h3><AppIcon name="flag" :size="18" /> Línea de tiempo</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_timeline" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Los hitos del negocio: fundación, local nuevo, logros. Se oculta sola si no cargás ninguno.</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Hitos <span class="hint-inline">({{ designForm.timeline.length }}/{{ mkLimits.timeline }})</span></label>
            <div v-if="designForm.timeline.length" class="qa-list">
              <div v-for="(t, i) in designForm.timeline" :key="i" class="qa-item">
                <div class="qa-fields">
                  <input v-model="t.label" class="input" type="text" :maxlength="mkLimits.timelineLabel" placeholder="Ej. 2015 o Hoy" :aria-label="`Rótulo del hito ${i + 1}`" />
                  <textarea v-model="t.text" class="textarea" rows="2" :maxlength="mkLimits.timelineText" placeholder="Qué pasó en ese momento" :aria-label="`Texto del hito ${i + 1}`"></textarea>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el hito ${i + 1}`" @click="moveRow(designForm.timeline, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.timeline.length - 1" :aria-label="`Bajar el hito ${i + 1}`" @click="moveRow(designForm.timeline, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el hito ${i + 1}`" @click="designForm.timeline.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.timeline.length >= mkLimits.timeline" @click="addRow(designForm.timeline, mkLimits.timeline, { label: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar hito
            </button>
            <p v-if="companyErrs.timeline" class="field-error" role="alert">{{ companyErrs.timeline }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveTimeline">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Equipo ===== -->
        <div id="mk-team" class="card mk-card">
          <h3><AppIcon name="users" :size="18" /> Equipo</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_team" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Las personas detrás del negocio, con su rol. Se oculta sola si no cargás a nadie.</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Integrantes <span class="hint-inline">({{ designForm.team.length }}/{{ mkLimits.team }})</span></label>
            <div v-if="designForm.team.length" class="qa-list">
              <div v-for="(m, i) in designForm.team" :key="i" class="qa-item">
                <div class="qa-fields">
                  <div class="mk-pair">
                    <input v-model="m.name" class="input" type="text" :maxlength="mkLimits.teamName" placeholder="Nombre" :aria-label="`Nombre del integrante ${i + 1}`" />
                    <input v-model="m.role" class="input" type="text" :maxlength="mkLimits.teamRole" placeholder="Rol. Ej. Dueña, Técnica" :aria-label="`Rol del integrante ${i + 1}`" />
                  </div>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el integrante ${i + 1}`" @click="moveRow(designForm.team, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.team.length - 1" :aria-label="`Bajar el integrante ${i + 1}`" @click="moveRow(designForm.team, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el integrante ${i + 1}`" @click="designForm.team.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.team.length >= mkLimits.team" @click="addRow(designForm.team, mkLimits.team, { name: '', role: '' })">
              <AppIcon name="plus" :size="15" /> Agregar integrante
            </button>
            <p v-if="companyErrs.team" class="field-error" role="alert">{{ companyErrs.team }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveTeam">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Horarios de atención ===== -->
        <div id="mk-hours" class="card mk-card">
          <h3><AppIcon name="clock" :size="18" /> Horarios de atención</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_hours" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Aparecen dentro de la sección Contáctanos, junto a tus canales.</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Horarios <span class="hint-inline">({{ designForm.hours.length }}/{{ mkLimits.hours }})</span></label>
            <div v-if="designForm.hours.length" class="qa-list">
              <div v-for="(h, i) in designForm.hours" :key="i" class="qa-item">
                <div class="qa-fields mk-pair">
                  <input v-model="h.label" class="input" type="text" :maxlength="mkLimits.hourLabel" placeholder="Lunes a viernes" :aria-label="`Días del horario ${i + 1}`" />
                  <input v-model="h.value" class="input" type="text" :maxlength="mkLimits.hourValue" placeholder="9 a 18 h" :aria-label="`Franja del horario ${i + 1}`" />
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el horario ${i + 1}`" @click="moveRow(designForm.hours, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.hours.length - 1" :aria-label="`Bajar el horario ${i + 1}`" @click="moveRow(designForm.hours, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el horario ${i + 1}`" @click="designForm.hours.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.hours.length >= mkLimits.hours" @click="addRow(designForm.hours, mkLimits.hours, { label: '', value: '' })">
              <AppIcon name="plus" :size="15" /> Agregar horario
            </button>
            <p class="hint">Si apagás la sección Contáctanos desde "Cómo se ve", los horarios también se ocultan.</p>
            <p v-if="companyErrs.hours" class="field-error" role="alert">{{ companyErrs.hours }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveHours">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Llamado a la acción ===== -->
        <div id="mk-cta" class="card mk-card">
          <h3><AppIcon name="megaphone" :size="18" /> Llamado a la acción</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_cta" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Banda de cierre de tu portada con un botón grande para que te escriban.</small>
              </span>
            </label>
          </div>
          <AppInput v-model="designForm.cta_title" label="Título" name="company_cta_title" placeholder="¿Listo para hacer tu pedido?" maxlength="120" />
          <AppInput v-model="designForm.cta_text" label="Texto" name="company_cta_text" placeholder="Escribinos y te armamos el pedido en el día." hint="Frase corta que acompaña al título." maxlength="280" />
          <AppInput v-model="designForm.cta_label" label="Texto del botón" name="company_cta_label" placeholder="Escribinos por WhatsApp" hint="Vacío: se usa uno genérico según el destino del botón." maxlength="40" />
          <p class="hint">El botón abre tu WhatsApp si cargaste uno; si no, lleva al formulario de contacto o a tu catálogo. La banda solo aparece si hay título o texto.</p>
          <p v-if="companyErrs.cta" class="field-error" role="alert">{{ companyErrs.cta }}</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveCta">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Cinta de anuncios (marquee bajo la portada) ===== -->
        <div id="mk-ann" class="card mk-card">
          <h3><AppIcon name="megaphone" :size="18" /> Cinta de anuncios</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_announcements" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Banda que corre en bucle debajo de la portada con tus avisos cortos (envíos gratis, cuotas, promos).</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Anuncios <span class="hint-inline">({{ designForm.announcements.length }}/{{ mkLimits.announcements }})</span></label>
            <div v-if="designForm.announcements.length" class="qa-list">
              <div v-for="(a, i) in designForm.announcements" :key="i" class="qa-item">
                <div class="qa-fields mk-pair">
                  <div class="mk-icon-field">
                    <span class="mk-icon-preview" aria-hidden="true"><AppIcon :name="serviceIcons[a.icon] ? a.icon : 'megaphone'" :size="17" /></span>
                    <select v-model="a.icon" class="select" :aria-label="`Ícono del anuncio ${i + 1}`">
                      <option v-for="(label, key) in serviceIcons" :key="key" :value="key">{{ label }}</option>
                    </select>
                  </div>
                  <input v-model="a.text" class="input" type="text" :maxlength="mkLimits.announcementText" placeholder="Ej. Envíos gratis superando $80.000" :aria-label="`Texto del anuncio ${i + 1}`" />
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el anuncio ${i + 1}`" @click="moveRow(designForm.announcements, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.announcements.length - 1" :aria-label="`Bajar el anuncio ${i + 1}`" @click="moveRow(designForm.announcements, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el anuncio ${i + 1}`" @click="designForm.announcements.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <button type="button" class="btn ghost btn-auto" :disabled="designForm.announcements.length >= mkLimits.announcements" @click="addRow(designForm.announcements, mkLimits.announcements, { icon: 'megaphone', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar anuncio
            </button>
            <p class="hint">Frases cortas con ícono que se repiten en bucle. Se ocultan solas si no cargás ninguna.</p>
            <p v-if="companyErrs.announcements" class="field-error" role="alert">{{ companyErrs.announcements }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveAnnouncements">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Video (embed YouTube/Vimeo) ===== -->
        <div id="mk-video" class="card mk-card">
          <h3><AppIcon name="eye" :size="18" /> Video</h3>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_video" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Sección con un video de YouTube o Vimeo: ideal para mostrar el local, un producto o cómo comprar.</small>
              </span>
            </label>
          </div>
          <AppInput v-model="designForm.video_url" label="Link del video" name="company_video_url" placeholder="https://www.youtube.com/watch?v=…" hint="Pegá el link completo de YouTube o Vimeo. Vacío: la sección no se muestra." maxlength="300" />
          <AppInput v-model="designForm.video_title" label="Título de la sección" name="company_video_title" placeholder="Mirá nuestro local en video" hint="Vacío: se muestra 'Mirá nuestro video'." maxlength="80" />
          <p class="hint">Aparece en un orden fijo entre las secciones de tu página.</p>
          <p v-if="companyErrs.video" class="field-error" role="alert">{{ companyErrs.video }}</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveVideo">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Extras (aviso del catálogo + texto del pie) ===== -->
        <div id="mk-extras" class="card mk-card">
          <h3><AppIcon name="plus" :size="18" /> Extras</h3>
          <AppInput v-model="designForm.catalog_note" label="Aviso del catálogo" name="company_catalog_note" placeholder="Ej. Envíos a todo el país · Aceptamos todos los medios de pago" hint="Tira informativa que aparece arriba de tu página de catálogo. Vacío: no se muestra." maxlength="160" />
          <AppInput v-model="designForm.footer_text" label="Frase del pie" name="company_footer_text" placeholder="Ej. Tienda familiar desde 1998" hint="Línea extra al final de tu web, debajo del copyright. Vacío: no se muestra." maxlength="160" />
          <p v-if="companyErrs.extras" class="field-error" role="alert">{{ companyErrs.extras }}</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveExtras">Guardar sección</AppButton>
          </div>
        </div>

      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
        <h3>El contenido de tu empresa viene con tu plan</h3>
        <p>Activá una suscripción para completar las secciones de marketing de tu página pública.</p>
        <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>
    </div>
    <!-- ================= ESTADÍSTICAS (premium) ================= -->
    <div v-if="seen.stats" v-show="section === 'stats'" :class="{ 'sec-on': section === 'stats' }">
      <div class="page-head">
        <div>
          <h1>Mis visitas</h1>
          <p>Cuánta gente entró a tu página web.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.promo" active="stats" @select="section = $event" />

      <template v-if="store.visitStats">
        <div class="stats">
          <div class="stat"><span class="stat-icon"><AppIcon name="eye" :size="20" /></span><div><strong>{{ store.visitStats.total }}</strong><small>Visitas totales</small></div></div>
          <div class="stat"><span class="stat-icon"><AppIcon name="trending-up" :size="20" /></span><div><strong>{{ store.visitStats.today }}</strong><small>Visitas hoy</small></div></div>
          <div class="stat"><span class="stat-icon"><AppIcon name="calendar" :size="20" /></span><div><strong>{{ visitAvg }}</strong><small>Promedio por día (último mes)</small></div></div>
        </div>
        <div class="card">
          <h3><AppIcon name="trending-up" :size="18" /> Visitas de los últimos 30 días</h3>
          <div class="stats-chart" role="img" aria-label="Visitas por día">
            <span
              v-for="d in visitDays" :key="d.date" class="stats-bar"
              :class="{ today: d.date === visitDays[visitDays.length - 1]?.date }"
              :style="{ height: `${Math.max(2, (d.count / visitMax) * 100)}%` }"
              :title="`${d.date}: ${d.count} visita${d.count === 1 ? '' : 's'}`"
            ></span>
          </div>
          <div class="stats-chart-axis"><span>{{ visitDays[0]?.date?.slice(5) }}</span><span>{{ visitDays[visitDays.length - 1]?.date?.slice(5) }}</span></div>
          <p class="hint">Cada barra es un día; cuanto más alta, más visitas. Contamos una visita por persona por día.</p>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="trending-up" :size="28" /></span>
        <h3>Todavía nadie visitó tu página</h3>
        <p>Compartí tu dirección web con tus clientes: apenas alguien entre, lo vas a ver acá.</p>
        <button class="btn btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar mi dirección</button>
      </div>
    </div>
    <!-- ================= QR Y FOLLETOS (premium) ================= -->
    <div v-if="seen.tools" v-show="section === 'tools'" :class="{ 'sec-on': section === 'tools' }">
      <div class="page-head">
        <div>
          <h1>QR y folletos</h1>
          <p>Material listo para imprimir o compartir, para que más gente llegue a tu página.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
      </div>
      <SectionTabs :tabs="tabGroups.promo" active="tools" @select="section = $event" />

      <div class="tools-hero">
        <span class="tools-hero-icon"><AppIcon name="megaphone" :size="26" /></span>
        <div>
          <strong>Llevá tu tienda al mundo real</strong>
          <p>Un QR en la vidriera, un folleto en la mano: cada impreso es un cliente más que entra a tu página.</p>
        </div>
        <span v-if="visitDays.length && canStats" class="tools-hero-chip"><AppIcon name="eye" :size="14" /> {{ store.visitStats?.total ?? 0 }} visitas</span>
      </div>

      <nav class="dsg-tabs tools-tabs" role="tablist" aria-label="Herramientas">
        <button type="button" role="tab" class="dsg-tab" :class="{ active: toolsTab === 'ready' }" :aria-selected="toolsTab === 'ready'" @click="toolsTab = 'ready'"><AppIcon name="qr-code" :size="15" /> QR y folleto rápido</button>
        <button v-if="canFlyers" type="button" role="tab" class="dsg-tab" :class="{ active: toolsTab === 'studio' }" :aria-selected="toolsTab === 'studio'" @click="toolsTab = 'studio'"><AppIcon name="sparkles" :size="15" /> Diseñá tu folleto <span class="tools-new">Nuevo</span></button>
      </nav>

      <div v-show="toolsTab === 'ready'" class="grid-2 tools-grid">
        <div v-if="canQr" class="card tools-card">
          <h3><AppIcon name="qr-code" :size="18" /> Tu código QR</h3>
          <p>Quien lo escanee con el celular entra directo a tu página. Pegalo en tu vidriera, mostrador o paquetes.</p>
          <div class="qr-stage">
            <div v-if="qrDataUrl" class="qr-frame"><i></i><i></i><i></i><i></i><img :src="qrDataUrl" alt="Código QR de tu tienda" /></div>
            <span v-else class="spinner spinner-brand" aria-hidden="true"></span>
          </div>
          <button type="button" class="qr-link" title="Copiar dirección" @click="copyLink"><AppIcon name="external-link" :size="14" /> <span>{{ publicUrl.replace(/^https?:\/\//, '') }}</span> <AppIcon name="copy" :size="14" /></button>
          <ul class="tools-tips">
            <li><AppIcon name="store" :size="15" /> Vidriera o puerta del local</li>
            <li><AppIcon name="package" :size="15" /> Bolsas, cajas y paquetes</li>
            <li><AppIcon name="receipt" :size="15" /> Tickets y tarjetas personales</li>
          </ul>
          <div class="btn-row">
            <button class="btn btn-auto" :disabled="!qrDataUrl" @click="downloadQr"><AppIcon name="download" :size="16" /> Descargar QR</button>
            <button class="btn ghost btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar dirección</button>
          </div>
        </div>
        <div v-if="canFlyers" class="card tools-card">
          <h3><AppIcon name="file-text" :size="18" /> Folleto rápido</h3>
          <p>Un folleto a color con tu logo, tus productos, tu contacto y el QR, armado solo. Salen 4 por hoja: imprimilos, cortalos y repartilos (o guardalos como PDF).</p>
          <div class="flyer-mini" aria-hidden="true">
            <span class="flyer-mini-top"><i></i><b></b></span>
            <span class="flyer-mini-lines"><b></b><b></b><b></b></span>
            <span class="flyer-mini-prods"><i></i><i></i><i></i></span>
            <span class="flyer-mini-foot"><i></i><b></b></span>
          </div>
          <div class="btn-row">
            <button class="btn btn-auto" @click="openFlyer"><AppIcon name="printer" :size="16" /> Generar folleto</button>
            <button class="btn ghost btn-auto" @click="toolsTab = 'studio'"><AppIcon name="sparkles" :size="16" /> Quiero diseñarlo yo</button>
          </div>
        </div>
      </div>

      <FlyerStudio
        v-if="canFlyers && toolsTab === 'studio'"
        :slug="store.store?.slug || ''"
        :shop-name="designShopName"
        :logo="currentLogo"
        :qr="qrDataUrl"
        :url="publicUrl"
        :contact="designForm.whatsapp || auth.user?.profile?.phone || ''"
        :can-add-gallery="canAddGallery"
        @print="openFlyer(true)"
      />
    </div>

    <!-- ================= VENTA EN LOCAL (próximamente) ================= -->
    <div v-if="seen.pos" v-show="section === 'pos'" :class="{ 'sec-on': section === 'pos' }">
      <div class="page-head">
        <div>
          <h1>Venta en persona</h1>
          <p>Un programa para cobrar en tu local, con tus productos ya cargados.</p>
        </div>
        <span class="pill warn"><AppIcon name="clock" :size="14" /> Próximamente</span>
      </div>

      <div class="pos-layout">
        <div>
          <div class="card">
            <h3><AppIcon name="monitor" :size="18" /> DAVENT Ventas</h3>
            <p>Estoy desarrollando un programa de venta para tu computadora. Cobrás en persona con el mismo catálogo que ya publicás en tu web, emitís el comprobante con tus datos y cerrás el día con el resumen de tus ventas.</p>
            <ul class="pos-feats">
              <li><AppIcon name="package" :size="16" /> <span>Productos, fotos y precios sincronizados con tu catálogo web.</span></li>
              <li><AppIcon name="receipt" :size="16" /> <span>Facturación integrada: tickets y facturas con tus datos.</span></li>
              <li><AppIcon name="printer" :size="16" /> <span>Comprobante imprimible al momento de cobrar.</span></li>
              <li><AppIcon name="trending-up" :size="16" /> <span>Resumen de ventas del día al cierre.</span></li>
              <li><AppIcon name="circle-check" :size="16" /> <span>Funciona sin internet: si se corta seguís vendiendo y sincroniza después.</span></li>
            </ul>
          </div>
          <AlertMessage kind="info" message="Todavía está en desarrollo. Cuando salga, vas a poder sumarlo a tu suscripción desde esta misma sección." />
        </div>

        <div class="card">
          <h3><AppIcon name="eye" :size="18" /> Así se va a ver</h3>
          <p class="pos-note">Vista de ejemplo: el programa sale con tu logo y el nombre de tu web.</p>
          <div class="pos-window" :style="posVars">
            <div class="pos-titlebar">
              <span class="pos-dots"><i></i><i></i><i></i></span>
              <span class="pos-title">DAVENT Ventas</span>
            </div>
            <div class="pos-topbar">
              <img v-if="currentLogo" class="pos-logo" :src="currentLogo" alt="" />
              <span v-else class="pos-mono">{{ businessInitial }}</span>
              <strong class="pos-shop">{{ designShopName }}</strong>
              <span class="pos-date"><AppIcon name="calendar" :size="12" /> {{ posToday }}</span>
            </div>

            <div class="pos-body">
              <div class="pos-bill-form">
                <div class="pos-bill-head">
                  <strong>Nueva factura</strong>
                  <span class="pos-inv-num">N° 0001-00000042</span>
                </div>
                <span class="pos-group-label">Comprobante</span>
                <div class="pos-field">
                  <span class="pos-field-label">Tipo</span>
                  <div class="pos-chips">
                    <span class="pos-chip">Ticket</span>
                    <span class="pos-chip active">Factura B</span>
                    <span class="pos-chip">Factura C</span>
                  </div>
                </div>
                <span class="pos-group-label">Comprador</span>
                <div class="pos-field">
                  <span class="pos-field-label">Nombre</span>
                  <span class="pos-input"><AppIcon name="user" :size="12" /> Consumidor final</span>
                </div>
                <div class="pos-field-row">
                  <div class="pos-field">
                    <span class="pos-field-label">Documento</span>
                    <span class="pos-input muted"><AppIcon name="search" :size="12" /> Opcional</span>
                  </div>
                  <div class="pos-field">
                    <span class="pos-field-label">Condición fiscal</span>
                    <span class="pos-input select-look">Consumidor final <AppIcon name="chevron-down" :size="12" /></span>
                  </div>
                </div>
                <div class="pos-field">
                  <span class="pos-field-label">Domicilio</span>
                  <span class="pos-input"><AppIcon name="map-pin" :size="12" /> {{ posAddress || '—' }}</span>
                </div>
                <span class="pos-group-label">Pago</span>
                <div class="pos-field">
                  <span class="pos-field-label">Medio de pago</span>
                  <div class="pos-chips">
                    <span class="pos-chip active">Efectivo</span>
                    <span class="pos-chip">Tarjeta</span>
                    <span class="pos-chip">Transferencia</span>
                    <span class="pos-chip">QR</span>
                  </div>
                </div>
              </div>
              <div class="pos-cart">
                <span class="pos-cart-head">Ítems de la venta</span>
                <div v-for="(p, i) in posCartItems" :key="`inv-${p.id || i}`" class="pos-cart-item">
                  <span class="pos-cart-qty">{{ posCartQty[i] }}</span>
                  <span class="pos-cart-name">{{ p.name }}</span>
                  <span class="pos-cart-price">{{ Number(p.price) ? formatARS(Number(p.price) * posCartQty[i]) : '—' }}</span>
                </div>
                <div class="pos-inv-totals">
                  <div><span>Subtotal</span><span>{{ posHasPrices ? formatARS(posSubtotal) : '—' }}</span></div>
                  <div><span>IVA 21%</span><span>{{ posIva }}</span></div>
                  <div class="pos-inv-grand"><span>Total</span><strong>{{ posInvoiceTotal }}</strong></div>
                </div>
                <span class="pos-pay">Emitir factura</span>
              </div>
            </div>
            <div class="pos-status"><span class="pos-dot"></span> Caja abierta · {{ displayName }}</div>
          </div>
          <p class="hint">Imagen de referencia. El producto final puede variar.</p>
        </div>
      </div>
    </div>
    <!-- ================= CHATBOT (solo Premium) ================= -->
    <div v-if="seen.bot" v-show="section === 'bot'" :class="{ 'sec-on': section === 'bot' }">
      <div class="page-head">
        <div>
          <h1>Asistente de chat</h1>
          <p>Un ayudante que responde solo las preguntas más comunes de quienes visitan tu página.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
      </div>
      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />
      <AlertMessage v-if="botErr" kind="error" :message="botErr" />

      <div class="card">
        <h3><AppIcon name="bot" :size="18" /> Configurá tu asistente</h3>
        <div class="field">
          <div class="check-list">
            <label class="check-item">
              <input v-model="botForm.is_enabled" type="checkbox" />
              <span class="check-text">
                <strong>Encender el asistente</strong>
                <small>Aparece como un globito de chat abajo a la derecha de tu página, con tu logo y el nombre de tu negocio.</small>
              </span>
            </label>
          </div>
        </div>
        <AppInput
          v-model="botForm.greeting"
          label="Mensaje de bienvenida"
          maxlength="200"
          placeholder="¡Hola! Soy el asistente de tu negocio. ¿En qué te puedo ayudar?"
          hint="Es lo primero que lee la persona al abrir el chat. Si lo dejás vacío, usamos uno automático."
        />
        <div class="field">
          <label>Preguntas y respuestas <span class="hint-inline">({{ botForm.qa.length }}/{{ CHATBOT_QA_MAX }})</span></label>
          <p class="hint">Ejemplo: pregunta «¿Hacen envíos?» y respuesta «Sí, a todo el país». Si el asistente no sabe responder, invita a escribirte desde Contáctanos.</p>
          <div v-if="botForm.qa.length" class="qa-list">
            <div v-for="(item, i) in botForm.qa" :key="i" class="qa-item">
              <div class="qa-fields">
                <input v-model="item.q" class="input" type="text" maxlength="120" placeholder="Pregunta frecuente. Ej: ¿Hacen envíos?" :aria-label="`Pregunta ${i + 1}`" />
                <textarea v-model="item.a" class="textarea" rows="2" maxlength="500" placeholder="Respuesta que da el bot" :aria-label="`Respuesta ${i + 1}`"></textarea>
              </div>
              <button type="button" class="icon-btn danger" :aria-label="`Borrar la pregunta ${i + 1}`" @click="botForm.qa.splice(i, 1)">
                <AppIcon name="trash" :size="15" />
              </button>
            </div>
          </div>
          <button type="button" class="btn ghost btn-auto" :disabled="botForm.qa.length >= CHATBOT_QA_MAX" @click="addBotQa">
            <AppIcon name="plus" :size="15" /> Agregar pregunta
          </button>
        </div>
        <AppButton :loading="botBusy" @click="saveBot">Guardar cambios</AppButton>
      </div>
    </div>
    <!-- ================= SOPORTE (equipo + chat en vivo) ================= -->
    <div v-if="seen.support" v-show="section === 'support'" :class="{ 'sec-on': section === 'support' }">
      <div class="page-head">
        <div>
          <h1>Asistente de diseño</h1>
          <p>Contale a DAVENT qué vendés y cómo querés que se vea tu web: te guía con preguntas y te recomienda un estilo del catálogo.</p>
        </div>
        <span class="presence-chip" :class="{ on: chatStaffOnline }">
          <span class="presence-dot"></span>
          {{ chatStaffOnline ? `${chatOnlineCount} en línea` : 'Equipo desconectado' }}
        </span>
      </div>

      <AlertMessage v-if="chatErr" kind="error" :message="chatErr" />

      <div class="support-grid">
        <aside class="card support-team">
          <div class="support-team-head">
            <h3>Asistente de diseño</h3>
            <span class="support-count">{{ chatOnlineCount }}/{{ chatStaff.length }}</span>
          </div>
          <ul class="support-list">
            <li v-for="s in chatContacts" :key="s.id">
              <button type="button" class="support-member" :class="{ on: s.online, bot: s.bot }" @click="contactStaff(s)">
                <span class="support-avatar" :class="{ bot: s.bot }">
                  <AppIcon v-if="s.bot" name="bot" :size="19" />
                  <template v-else>{{ staffInitials(s.name) }}</template>
                  <span class="support-status" :class="{ on: s.online }"></span>
                </span>
                <span class="support-info">
                  <strong>{{ s.name }}</strong>
                  <small>{{ s.bot ? 'Respuestas automáticas' : (s.online ? 'En línea ahora' : 'Desconectado') }}</small>
                </span>
                <AppIcon class="support-go" name="message-circle" :size="16" />
              </button>
            </li>
          </ul>
        </aside>

        <div class="card support-side">
          <div class="support-side-icon"><AppIcon name="message-circle" :size="20" /></div>
          <h3>Diseñemos tu web</h3>
          <p>
            Contale tu rubro, tu objetivo y el estilo que te gusta. El asistente te
            recomienda un diseño y después lo aplicás desde Diseñar con IA.
          </p>
          <AppButton class="support-live" :loading="chatBusy" :disabled="!chatStaffOnline" @click="requestLiveHelp">
            Solicitar asistencia en vivo
          </AppButton>
          <button v-if="chatUnread && !chatOpen" type="button" class="support-unread" @click="openChat()">
            <span class="chat-badge">{{ chatUnread }}</span>
            <span>Tenés {{ chatUnread === 1 ? 'un mensaje' : `${chatUnread} mensajes` }} sin leer — abrir chat</span>
          </button>
          <ul class="support-facts">
            <li><AppIcon name="check" :size="15" /> Elegí un integrante para abrir la conversación</li>
            <li><AppIcon name="check" :size="15" /> Tu historial de chat queda guardado</li>
            <li><AppIcon name="check" :size="15" /> Si el equipo está desconectado, te responde a la brevedad</li>
          </ul>
        </div>
      </div>
    </div>
    <!-- ================= PLANES ================= -->
    <div v-if="seen.plans" v-show="section === 'plans'" :class="{ 'sec-on': section === 'plans' }">
      <div class="page-head">
        <div>
          <h1>Plan y pagos</h1>
          <p>Elegí el plan que mejor te viene. Podés cambiarlo cuando quieras.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.billing" active="plans" @select="section = $event" />

      <AlertMessage v-if="billing.notice" kind="success" :message="billing.notice" />
      <AlertMessage v-if="billing.lastError" kind="error" :message="billing.lastError" />
      <AlertMessage v-if="payments.notice" kind="success" :message="payments.notice" />
      <AlertMessage v-if="payments.lastError" kind="error" :message="payments.lastError" />
      <div class="card coupon-card">
        <div class="coupon-copy">
          <h3><AppIcon name="gift" :size="18" /> ¿Tenés un código promocional?</h3>
          <p>Ingresalo acá para activar los días de acceso que te otorga.</p>
        </div>
        <form class="coupon-form" @submit.prevent="redeemCoupon">
          <input
            v-model="couponCode"
            class="input"
            type="text"
            maxlength="40"
            placeholder="Ej. FLYER7"
            aria-label="Código promocional"
            :disabled="couponBusy"
          />
          <button class="btn btn-auto" type="submit" :disabled="couponBusy || !couponCode.trim()">
            <span v-if="couponBusy" class="spinner"></span> Canjear
          </button>
        </form>
      </div>
      <!-- Datos de facturación: se piden recién al iniciar un cobro (billing_required). -->
      <div v-if="needsBilling" class="card billing-card">
        <div class="billing-head">
          <h3><AppIcon name="receipt" :size="18" /> Datos de facturación</h3>
          <p>Los necesitamos una sola vez para emitir tu factura. Se guardan en tu perfil y solo se usan para los cobros.</p>
        </div>
        <form @submit.prevent="saveBilling" novalidate>
          <div class="grid-2">
            <AppInput v-model="accountForm.first_name" label="Nombre" name="bill_first_name" autocomplete="given-name" placeholder="Escribe tu nombre" required :error="accountFieldErr('first_name')" @blur="accountTouched.first_name = true" />
            <AppInput v-model="accountForm.last_name" label="Apellido/s" name="bill_last_name" autocomplete="family-name" placeholder="Escribe tu/s apellido/s" required :error="accountFieldErr('last_name')" @blur="accountTouched.last_name = true" />
          </div>
          <div class="field">
            <label for="bill_tax_condition">Condición fiscal *</label>
            <select id="bill_tax_condition" v-model="accountForm.tax_condition" class="select">
              <option v-for="t in TAX_CONDITIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
            <p class="hint">Tipo de documento automático: {{ docKind }} (CF → DNI, resto → CUIT).</p>
          </div>
          <AppInput v-model="accountForm.business_name" label="Nombre de negocio" name="bill_business_name" placeholder="Escribe tu nombre de negocio" :hint="accountForm.tax_condition === 'CF' ? 'Opcional únicamente para consumidor final.' : 'Obligatorio para tu condición fiscal.'" :error="accountFieldErr('business_name')" @blur="accountTouched.business_name = true" />
          <AppInput v-model="accountForm.document" label="Documento" name="bill_document" placeholder="Escribe tu número de identificación" :hint="docHint" required :error="accountFieldErr('document')" @blur="accountTouched.document = true" />
          <div class="grid-2">
            <div class="field">
              <label for="bill_province">Provincia *</label>
              <select id="bill_province" v-model="accountForm.province" class="select" :class="{ invalid: accountFieldErr('province') }" @change="onAccountProvinceChange">
                <option value="">Seleccionar…</option>
                <option v-for="p in provinces" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <p v-if="accountFieldErr('province')" class="field-error">{{ accountFieldErr('province') }}</p>
            </div>
            <div class="field">
              <label for="bill_city">Ciudad *</label>
              <select id="bill_city" v-model="accountForm.city" class="select" :class="{ invalid: accountFieldErr('city') }" :disabled="!accountForm.province">
                <option value="">{{ accountForm.province ? 'Seleccionar…' : 'Primero elegí provincia' }}</option>
                <option v-for="c in cities" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
              <p v-if="accountFieldErr('city')" class="field-error">{{ accountFieldErr('city') }}</p>
            </div>
          </div>
          <AppInput v-model="accountForm.address" label="Domicilio" name="bill_address" autocomplete="street-address" placeholder="Escribe tu domicilio" :error="accountFieldErr('address')" @blur="accountTouched.address = true" />
          <AppInput v-model="accountForm.phone" label="Número de celular" name="bill_phone" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" required :error="accountFieldErr('phone')" @blur="accountTouched.phone = true" />
          <div class="btn-row">
            <AppButton variant="ghost" type="button" @click="closeBilling">Cancelar</AppButton>
            <AppButton type="submit" :loading="billingBusy">Guardar y continuar al pago</AppButton>
          </div>
        </form>
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
    <div v-if="seen.payments" v-show="section === 'payments'" :class="{ 'sec-on': section === 'payments' }">
      <div class="page-head">
        <div>
          <h1>Plan y pagos</h1>
          <p>Todo lo que pagaste por tu suscripción. Se acredita solo cuando Mercado Pago lo confirma.</p>
        </div>
        <button class="btn ghost btn-auto" @click="payments.loadPayments()"><AppIcon name="refresh" :size="16" /> Actualizar</button>
      </div>
      <SectionTabs :tabs="tabGroups.billing" active="payments" @select="section = $event" />


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
        <h3>Todavía no hiciste ningún pago</h3>
        <p>Cuando pagues tu plan, el pago va a aparecer acá.</p>
        <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>

      <!-- Los cupones canjeados no son pagos ni facturas: se listan aparte
           como actividad promocional de la cuenta. -->
      <div v-if="billing.redemptions.length" class="card section-gap">
        <h3><AppIcon name="badge-check" :size="18" /> Cupones canjeados</h3>
        <ul class="coupon-history">
          <li v-for="r in billing.redemptions" :key="r.id">
            <span class="coupon-code mono">{{ r.code }}</span>
            <span class="coupon-detail">{{ r.plan_name }} · {{ r.days }} día{{ r.days === 1 ? '' : 's' }}</span>
            <time>{{ formatDateTime(r.redeemed_at) }}</time>
          </li>
        </ul>
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
    <div v-if="seen.invoices" v-show="section === 'invoices'" :class="{ 'sec-on': section === 'invoices' }">
      <div class="page-head">
        <div>
          <h1>Plan y pagos</h1>
          <p>Tus comprobantes por cada pago. También te los mandamos por correo.</p>
        </div>
        <button class="btn ghost btn-auto" @click="invoices.loadInvoices()"><AppIcon name="refresh" :size="16" /> Actualizar</button>
      </div>
      <SectionTabs :tabs="tabGroups.billing" active="invoices" @select="section = $event" />


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
        <p>Cuando se acredite un pago de tu suscripción, el comprobante se emite solo, llega al correo de tu cuenta y aparece acá, listo para imprimir o guardar como PDF.</p>
        <button class="btn btn-auto" @click="section = 'payments'">Ver mis pagos</button>
      </div>
    </div>
    <!-- ================= CUENTA ================= -->
    <div v-if="seen.settings" v-show="section === 'settings'" :class="{ 'sec-on': section === 'settings' }">
      <div class="page-head">
        <div>
          <h1>Mi cuenta</h1>
          <p>Tus datos personales y tu contraseña. Mantenelos al día para poder facturarte bien.</p>
        </div>
        <button class="btn ghost btn-auto" @click="reloadAccount"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>
      <div class="grid-2">
        <div class="card">
          <h3><AppIcon name="user" :size="18" /> Mis datos</h3>
          <p>Con estos datos armamos tus facturas y te contactamos si hace falta.</p>
          <AlertMessage v-if="accountMsg" kind="success" :message="accountMsg" />
          <AlertMessage v-if="accountErr" kind="error" :message="accountErr" />
          <AlertMessage v-if="geoNotice" kind="warn" :message="geoNotice" />
          <AlertMessage v-if="geoErr" kind="error" :message="geoErr" />
          <form class="form-top" @submit.prevent="saveAccount" novalidate>
            <AppInput v-model="accountForm.email" label="Correo electrónico" name="acc_email" type="email" autocomplete="email" placeholder="Ej. alfredito2026@outlook.com" hint="Si lo cambiás, tenés que verificar el nuevo correo." required :error="accountFieldErr('email')" @blur="accountTouched.email = true" />
            <div class="grid-2">
              <AppInput v-model="accountForm.first_name" label="Nombre" name="acc_first_name" autocomplete="given-name" placeholder="Escribe tu nombre" required :error="accountFieldErr('first_name')" @blur="accountTouched.first_name = true" />
              <AppInput v-model="accountForm.last_name" label="Apellido/s" name="acc_last_name" autocomplete="family-name" placeholder="Escribe tu/s apellido/s" required :error="accountFieldErr('last_name')" @blur="accountTouched.last_name = true" />
            </div>
            <div class="field">
              <label for="acc_tax_condition">Condición fiscal *</label>
              <select id="acc_tax_condition" v-model="accountForm.tax_condition" class="select">
                <option v-for="t in TAX_CONDITIONS" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
              <p class="hint">Tipo de documento automático: {{ docKind }} (CF usa DNI; el resto, CUIT).</p>
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
            <AppInput v-model="accountForm.phone" label="Número de celular" name="acc_phone" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" required :error="accountFieldErr('phone')" @blur="accountTouched.phone = true" />
            <AppButton :loading="accountBusy">Guardar cambios</AppButton>
          </form>
        </div>
        <div class="card">
          <h3><AppIcon name="key" :size="18" /> Cambiar mi contraseña</h3>
          <p class="lead">Por seguridad, al cambiarla se cierra tu sesión en los demás dispositivos.</p>
          <AlertMessage v-if="passMsg" kind="success" :message="passMsg" />
          <AlertMessage v-if="passErr" kind="error" :message="passErr" />
          <form @submit.prevent="changePassword" novalidate>
            <AppInput v-model="passForm.old_password" label="Contraseña actual" name="old_password" type="password" autocomplete="current-password" :error="touched.old_password && !passForm.old_password ? 'Obligatorio' : ''" @blur="touched.old_password = true" />
            <AppInput v-model="passForm.new_password" label="Contraseña nueva" name="new_password" type="password" autocomplete="new-password" :error="touched.new_password ? (validatePassword(passForm.new_password) || '') : ''" @blur="touched.new_password = true" />
            <PasswordStrength :value="passForm.new_password" />
            <AppInput v-model="passForm.confirm_password" label="Repetí la contraseña nueva" name="confirm_password" type="password" autocomplete="new-password" @blur="touched.confirm_password = true" />
            <AppButton :loading="auth.status === 'loading'">Cambiar contraseña</AppButton>
          </form>
        </div>
      </div>
    </div>

    <!-- Burbuja de mensajería estilo Messenger (arrastrable, queda anclada
         a una arista): punto verde = equipo en línea, badge = no leídos.
         Abre el panel de contactos o la ventana de conversación. -->
    <ChatDock
      :content="chatDockContent"
      :online="chatStaffOnline"
      :unread="chatUnread"
      :minimized="chatMin"
      label="Asistente de diseño"
      @toggle="onDockToggle"
    >
      <!-- Panel de contactos: el asistente automático figura como un
           integrante más del equipo. -->
      <div v-if="chatDockPanel" class="chat-dock-panel">
        <div class="chat-threads-head">
          <h3><AppIcon name="message-circle" :size="16" /> Asistente de diseño</h3>
          <span class="presence-chip" :class="{ on: chatStaffOnline }">
            <span class="presence-dot"></span>
            {{ chatStaffOnline ? `${chatOnlineCount} en línea` : 'Desconectado' }}
          </span>
        </div>
        <ul class="support-list dock">
          <li v-for="s in chatContacts" :key="s.id">
            <button type="button" class="support-member" :class="{ on: s.online, bot: s.bot }" @click="openChat(s)">
              <span class="support-avatar" :class="{ bot: s.bot }">
                <AppIcon v-if="s.bot" name="bot" :size="19" />
                <template v-else>{{ staffInitials(s.name) }}</template>
                <span class="support-status" :class="{ on: s.online }"></span>
              </span>
              <span class="support-info">
                <strong>{{ s.name }}</strong>
                <small>{{ s.bot ? 'Respuestas automáticas' : (s.online ? 'En línea ahora' : 'Desconectado') }}</small>
              </span>
              <AppIcon class="support-go" name="chevron-right" :size="16" />
            </button>
          </li>
        </ul>
      </div>

      <!-- Ventana flotante de conversación (estilo chat de Facebook):
           minimiza al header, cierra con Esc o la X, badge de no-leídos
           mientras está minimizada (el polling se pausa para no marcar
           leídos sin verlos) y foco al textarea al abrir/expandir/enviar. -->
      <Transition v-else-if="chatOpen" name="chatwin">
        <section
          class="chat-win"
          :class="{ min: chatMin, bot: botMode }"
          role="dialog"
          aria-modal="false"
          :aria-label="`Conversación con ${chatPeer?.name || 'equipo DAVENT'}`"
        >
          <header class="chat-win-head" @click="toggleChatMin">
            <span class="support-avatar" :class="{ bot: botMode }">
              <AppIcon v-if="botMode" name="bot" :size="18" />
              <template v-else>{{ staffInitials(chatPeer?.name || 'DAVENT') }}</template>
              <span class="support-status" :class="{ on: botMode || (chatPeer ? chatPeer.online : chatStaffOnline) }"></span>
            </span>
            <div class="chat-modal-who">
              <strong>{{ chatPeer?.name || 'Asistente de diseño' }}</strong>
              <small><span class="chat-win-state" :class="{ on: botMode || (chatPeer ? chatPeer.online : chatStaffOnline) }">{{ botMode ? 'Respuestas automáticas · siempre disponible' : chatPeer ? (chatPeer.online ? 'En línea ahora' : 'Asistente disponible') : (chatStaffOnline ? 'Asistente en línea' : 'Asistente disponible') }}</span></small>
            </div>
            <span class="chat-win-actions">
              <span v-if="chatMin && chatUnread && !botMode" class="chat-badge">{{ chatUnread }}</span>
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
                @click.stop="closeChat"
              >
                <AppIcon name="x" :size="15" />
              </button>
            </span>
          </header>

          <template v-if="!chatMin">
            <div ref="chatBoxEl" class="chat-box">
              <template v-if="botMode">
                <template v-for="r in chatRows(botMsgs)" :key="r.key">
                  <div v-if="r.day" class="chat-day">{{ r.day }}</div>
                  <div v-else class="chat-row" :class="{ mine: r.m.mine, first: r.first, last: r.last, 'gap-top': r.first }">
                    <span v-if="!r.m.mine" class="chat-avatar bot" :class="{ ghost: !r.last }"><AppIcon name="bot" :size="14" /></span>
                    <div class="chat-stack">
                      <div class="chat-msg"><p class="chat-body">{{ r.m.body }}</p></div>
                      <span v-if="r.last" class="chat-meta">{{ fmtChatTime(r.m.created_at) }}</span>
                    </div>
                  </div>
                </template>
                <div v-if="botTyping" class="chat-row first last">
                  <span class="chat-avatar bot"><AppIcon name="bot" :size="14" /></span>
                  <div class="chat-msg"><p class="chat-typing"><i /><i /><i /></p></div>
                </div>
                <div v-if="botPending.length && !botTyping" class="chat-sugg">
                  <button
                    v-for="t in botPending" :key="t.id" type="button"
                    class="chat-sugg-msg"
                    @click="selectBotTopic(t)"
                  >
                    {{ t.label }}
                  </button>
                </div>
              </template>
              <template v-else>
                <p v-if="!chatMessages.length" class="chat-empty">
                  Contale a tu asistente qué vendés y qué estilo te gustaría para tu web.
                </p>
                <template v-for="r in chatRows(chatMessages)" :key="r.key">
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
              </template>
            </div>

            <!-- Adjuntos en cola: preview local antes de subir -->
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
                v-if="!botMode"
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
                :placeholder="botMode ? 'Preguntale al asistente…' : 'Escribí tu mensaje…'"
                :aria-label="botMode ? 'Pregunta para el asistente' : 'Mensaje para el asistente de diseño'"
                @input="resizeChatInput"
                @keydown.enter="onComposerEnter"
              ></textarea>
              <button
                type="button"
                class="chat-send"
                :disabled="(!chatInput.trim() && !chatFiles.length) || chatBusy || botTyping"
                aria-label="Enviar mensaje"
                @click="sendChat"
              >
                <AppIcon name="send" :size="17" />
              </button>
            </div>
          </template>
        </section>
      </Transition>
    </ChatDock>

    <!-- Búsqueda global: Ctrl/⌘+K o "/" desde cualquier sección -->
    <GlobalSearch v-model:open="searchOpen" :commands="searchCommands" />

    <!-- Tour de primera vez (4 pasos sobre el menú) -->
    <div v-if="leaveGuard.open" class="dsg-confirm" role="presentation" @keydown.esc="confirmLeave(false)">
      <div class="dsg-confirm-box" role="alertdialog" aria-modal="true" aria-labelledby="dsg-leave-title" aria-describedby="dsg-leave-desc">
        <h3 id="dsg-leave-title">Tenés cambios sin guardar</h3>
        <p id="dsg-leave-desc">Si salís ahora, se pierden los cambios que hiciste en el diseño de tu página.</p>
        <div class="dsg-confirm-actions">
          <button type="button" class="btn ghost btn-auto" ref="leaveStay" @click="confirmLeave(false)">Seguir editando</button>
          <button type="button" class="btn btn-auto" @click="confirmLeave(true)">Salir sin guardar</button>
        </div>
      </div>
    </div>
    <TourGuide v-model:open="tourOpen" />

    <!-- Toast "Guardado ✓" con deshacer donde la acción es reversible -->
    <Teleport to="body">
      <div class="toast-wrap">
        <Transition name="toast">
          <div v-if="toast" class="toast" role="status">
            <AppIcon name="circle-check" :size="17" class="toast-ok" />
            <span class="toast-msg">{{ toast.msg }}</span>
            <button v-if="toast.undo" type="button" class="toast-undo" @click="toast.undo(); closeToast()">Deshacer</button>
            <button type="button" class="toast-x" aria-label="Cerrar" @click="closeToast"><AppIcon name="x" :size="14" /></button>
          </div>
        </Transition>
      </div>
    </Teleport>

    <!-- Vista previa del beneficio bloqueado: candado del menú, búsqueda o
         deep-link. 'expired' = renovar; 'upgrade' = plan superior. -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="lockedFeature" class="lock-overlay" @click.self="lockedFeature = null">
          <div class="lock-sheet" role="dialog" aria-modal="true" :aria-label="lockedFeature.title">
            <button type="button" class="lock-x" aria-label="Cerrar" @click="lockedFeature = null"><AppIcon name="x" :size="16" /></button>
            <span class="lock-icon"><AppIcon :name="lockedFeature.icon" :size="26" /></span>
            <p class="lock-tag">
              <AppIcon name="lock" :size="12" />
              <span v-if="lockedFeature.reason === 'expired'">Tu plan venció — renová para volver a usarla</span>
              <span v-else>Disponible en {{ lockedFeature.planName || 'planes superiores' }}</span>
            </p>
            <h3>{{ lockedFeature.title }}</h3>
            <p class="lock-text">{{ lockedFeature.text }}</p>
            <div class="lock-actions">
              <button type="button" class="btn btn-auto" @click="goPlansFromLocked">
                {{ lockedFeature.reason === 'expired' ? 'Renovar mi plan' : 'Ver planes' }}
              </button>
              <button type="button" class="btn ghost btn-auto" @click="lockedFeature = null">Ahora no</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </DashLayout>
</template>
