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
  CUSTOMIZATION_DEFAULTS, storeThemeVars,
  SITE_TEMPLATE_KEYS, SITE_TEMPLATES,
  siteTemplatesLimit, allowedSiteTemplatesFor, normalizeSiteTemplates, resolveSiteTemplates,
  ensureStoreFont, ensureStoreFontPicker,
  validateDisplayName, validateHeadline, validateDescription,
  validateAboutTitle, validateAboutText, validateAboutYears, validateAboutMission, validateAboutSpecialties,
  validateContactEmail,
  validateWhatsapp, validateInstagram, validateTiktok, validateFacebook,
  normalizeWhatsapp, normalizeInstagram, normalizeTiktok, normalizeFacebook,
  validateImageFile, validateLogoFile, LOGO_ACCEPT, CAROUSEL_MAX_IMAGES, DECOR_MAX_IMAGES,
  CHATBOT_DEFAULTS, CHATBOT_QA_MAX,
  MARKETING_LIMITS, SERVICE_ICONS, serviceHue,
  validateSectionTitle, validateCtaTitle, validateCtaText, validateCtaLabel, validateVideoUrl, validateLiveStreamUrl, videosLimit
} from '../api/stores.api.js'
import {
  validateTaxonomyName, validateProductName, validateProductPrice, validateProductDescription, validateProductStock,
  catalogApi, FEATURE_LIMITS, validateFeatureSchema, validateProductFeatures,
  DISCOUNT_SCOPES, DISCOUNT_DEFAULT_PERCENT, DISCOUNT_LIMITS,
  validateDiscountName, validateDiscountPercent, validateDiscountWindow,
  isoToLocalInput, localInputToIso, productListOffer, isDiscountedProduct, campaignWindowLabel
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
import { fetchNotifications, markNotificationRead, markReviewsSeen, fetchChangelog } from '../api/notifications.api.js'
import { fetchAssistant, sendAssistant } from '../api/assistant.api.js'
import { extractApiError } from '../api/http.js'
import { env } from '../config/env.js'
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
import FlyerEditor from '../components/FlyerEditor.vue'
import AiAssistModal from '../components/assist/AiAssistModal.vue'
import AiAssistOptIn from '../components/assist/AiAssistOptIn.vue'
import PriceUpdateModal from '../components/PriceUpdateModal.vue'
import { useOffers } from '../composables/useOffers.js'
import CatalogToolbar from '../components/dashboard/catalog/CatalogToolbar.vue'
import ProductTable from '../components/dashboard/catalog/ProductTable.vue'
import ProductForm from '../components/dashboard/catalog/ProductForm.vue'
import DiscountCard from '../components/dashboard/catalog/DiscountCard.vue'
import ChatDock from '../components/ChatDock.vue'
import RobotGuide from '../components/RobotGuide.vue'
import GlobalSearch from '../components/GlobalSearch.vue'
import TourGuide from '../components/TourGuide.vue'
import TipHint from '../components/TipHint.vue'
import { useStudioDesign, DESIGN_FIELDS } from '../composables/useStudioDesign.js'
import DesignStylesTab from '../components/design/DesignStylesTab.vue'
import DesignStudioTab from '../components/design/DesignStudioTab.vue'
import WebQualityCard from '../components/design/WebQualityCard.vue'
import { useWebQuality } from '../composables/useWebQuality.js'
import { TEMPLATE_DEFS, TEMPLATE_LABELS, templateDef, templatePages, patternsForSiteTemplates, patternSurfaces, normalizeLayoutConfig } from '../templates/index.js'
import { designApi } from '../api/design.api.js'
import OrdersPanel from '../components/dashboard/commerce/OrdersPanel.vue'
import SalesPanel from '../components/dashboard/commerce/SalesPanel.vue'
import CustomersPanel from '../components/dashboard/commerce/CustomersPanel.vue'
import BuyerSupportPanel from '../components/dashboard/commerce/BuyerSupportPanel.vue'
import PaymentsConfigPanel from '../components/dashboard/commerce/PaymentsConfigPanel.vue'
import LegalPagesPanel from '../components/dashboard/commerce/LegalPagesPanel.vue'
import PlansPanel from '../components/dashboard/commerce/PlansPanel.vue'
import CustomerAuthPanel from '../components/dashboard/commerce/CustomerAuthPanel.vue'

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
      { id: 'photos', label: 'Mis fotos', icon: 'images', hint: 'Logo, portada y galería' },
      { id: 'design', label: 'Diseño', icon: 'palette', hint: 'Cómo se ve tu página' },
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
  // E-commerce del dueño: pedidos/ventas/clientes/consultas/cobros/legal/
  // membresías de SU tienda (los paneles viven en components/dashboard/commerce).
  const selling = [
    { id: 'orders', label: 'Pedidos', icon: 'package', hint: 'Lo que te compraron' },
    { id: 'sales', label: 'Ventas', icon: 'trending-up', hint: 'Números del período' },
    { id: 'customers', label: 'Clientes', icon: 'users', hint: 'Compradores y miembros' },
    { id: 'inquiries', label: 'Consultas', icon: 'message-circle', hint: 'Preguntas de clientes' },
    { id: 'payconfig', label: 'Cobros', icon: 'wallet', hint: 'Métodos, fiscal y Mercado Pago' },
    { id: 'legal', label: 'Legal', icon: 'file-text', hint: 'Páginas y devoluciones' },
    { id: 'memberships', label: 'Membresías', icon: 'crown', hint: 'Planes de tus clientes' }
  ]
  return { web, promo, billing: billingTabs, selling }
})

// Qué secciones se bloquean por plan y con qué copy abre el candado
// (vista previa del beneficio: 'expired' = suscripción vencida, 'upgrade' =
// falta el beneficio en el plan actual).
const SECTION_BENEFITS = {
  selling: ['has_ecommerce'],
  accounts: ['has_customer_auth'],
  design_assisted: ['has_ai_design'],
  design_studio: ['has_design_advanced'],
  services: ['has_services_site'],
  reviews: ['has_product_comments'],
  support: ['has_support_chat'],
  bot: ['has_chatbot'],
  stats: ['has_stats'],
  tools: ['has_qr', 'has_flyers'],
  flyer_editor: ['has_flyer_editor']
}
const LOCKED_FEATURES = {
  selling: { icon: 'lucide:shopping-cart', title: 'Vender online', text: 'Carrito, checkout y seguimiento de pedidos en tu web; cobros con tu Mercado Pago, membresías para tus clientes y registro de ventas.' },
  accounts: { icon: 'lucide:id-card', title: 'Acceso de clientes', text: 'Tus clientes crean su cuenta en tu web, ingresan con email o Google y siguen sus pedidos desde su perfil.' },
  design_assisted: { icon: 'sparkles', title: 'Diseño asistido', text: 'Contale a qué te dedicás y recibí tu web armada: plantilla, orden de secciones y textos. Después la ajustás a mano.' },
  design_studio: { icon: 'layout-panel-left', title: 'Studio de diseño', text: 'El editor completo con vista previa en vivo: colores, tipografía, contenedores, portada y versión de prueba antes de publicar.' },
  catalogs: { icon: 'package', title: 'Tu catálogo de productos', text: 'Cargá productos con foto, precio y categorías: se publican solos en tu web.' },
  services: { icon: 'wrench', title: 'Página de servicios', text: 'Una página propia para mostrar lo que hacés, con duración, precio y botón de consulta directa a tu WhatsApp.' },
  pos: { icon: 'monitor', title: 'Venta en persona', text: 'Cobrá en tu local usando el mismo catálogo de tu web. Llega muy pronto.' },
  reviews: { icon: 'star', title: 'Opiniones de clientes', text: 'Tus clientes valoran tus productos y dejan comentarios que se muestran en tu web; vos decidís qué se ve.' },
  support: { icon: 'message-circle', title: 'Tu Asistente', text: 'Te responde sobre tu cuenta: plan, tienda, productos, visitas, pagos y facturas.' },
  bot: { icon: 'bot', title: 'Asistente virtual', text: 'Un ayudante en tu web que responde solo las preguntas frecuentes de tus clientes, las 24 horas.' },
  tools: { icon: 'qr-code', title: 'QR y folletos', text: 'Código QR y folletos listos para imprimir y repartir: del papel a tu web en un escaneo.' },
  flyer_editor: { icon: 'pen-tool', title: 'Editor avanzado de folletos', text: 'Un lienzo libre para diseñar tu folleto pieza por pieza: textos, fotos, productos y QR donde quieras, y salida lista para imprenta.' },
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
  for (const id of ['catalogs', 'services', 'pos', 'reviews', 'support', 'bot', 'tools', 'stats', 'design_assisted', 'design_studio', 'flyer_editor', 'selling', 'accounts']) {
    // El asistente/soporte es para planes pagos (gate mcp_user_access en
    // el backend): el trial queda con candado de upgrade aunque esté vigente.
    map[id] = !hasAccess ? 'expired' : (id === 'support' && plan.value?.isTrial) ? 'upgrade' : gated(id) ? 'upgrade' : null
  }
  return map
})

//Opiniones sin leer: badge del ítem "Opiniones" del menú (viene en el
//mismo poll que las notificaciones). Declarado acá arriba porque navItems
//se evalúa durante setup (validIds) — después del ref era un TDZ fatal.
const unreadReviewsCount = ref(0)
// Mismo motivo: badge de "Mensajes" en navItems (TDZ si queda más abajo).
const chatUnread = ref(0)

// Menú por intención: lo que el dueño quiere hacer, no el módulo técnico.
const navItems = computed(() => {
  const L = navLocks.value
  return [
    { id: 'overview', label: 'Inicio', icon: 'dashboard', hint: 'Tu negocio hoy' },
    { id: 'catalogs', label: 'Mis productos', icon: 'package', hint: 'Fotos, precios y categorías', locked: L.catalogs, badge: catalog.products.length || null },
    { id: 'services', label: 'Mis servicios', icon: 'wrench', hint: 'Lo que ofrecés hacer', locked: L.services },
    { id: 'selling', label: 'Vender online', icon: 'lucide:shopping-cart', hint: 'Pedidos, ventas y cobros de tu tienda', locked: L.selling },
    { id: 'accounts', label: 'Acceso de clientes', icon: 'lucide:id-card', hint: 'Registro e ingreso en tu web', locked: L.accounts },
    // "Vender en persona" se comunica como novedad (roadmap), no como sección.

    { id: 'web', label: 'Mi página', icon: 'store', hint: 'Diseño, secciones y dirección' },
    { id: 'reviews', label: 'Opiniones', icon: 'star', hint: 'Lo que dicen de vos', locked: L.reviews, badge: unreadReviewsCount.value || null },
    { id: 'tools', label: 'Promocionar', icon: 'megaphone', hint: 'QR, folletos y visitas', locked: L.tools },
    { id: 'support', label: 'Ayuda', icon: 'message-circle', hint: 'Te ayuda con tu cuenta', locked: L.support },
    { id: 'bot', label: 'Asistente virtual', icon: 'bot', hint: 'Responde por vos en tu web', locked: L.bot },
    { sep: true },
    { id: 'plans', label: 'Plan y pagos', icon: 'credit-card', hint: 'Suscripción, pagos y facturas' },
    { id: 'settings', label: 'Mi cuenta', icon: 'user', hint: 'Datos y contraseña' },
    //Discreto a propósito: el changelog no compite con las secciones de trabajo.
    { id: 'changelog', label: 'Novedades', icon: 'history', hint: 'Lo nuevo en DAVENT' }
  ]
})

const validIds = computed(() => {
  const ids = new Set(navItems.value.filter((i) => i.id).map((i) => i.id))
  Object.values(tabGroups.value).forEach((tabs) => tabs.forEach((t) => ids.add(t.id)))
  return ids
})

// Grupo de pestañas -> ítem de menú que lo representa cuando la primera
// pestaña ya no tiene entrada propia ('web' es solo un índice de apartados,
// no abre ninguna pestaña por defecto).
const GROUP_NAV_ID = { web: 'web', selling: 'selling' }
// Entrada del menú que corresponde a la sección actual (las pestañas comparten una).
const navActive = computed(() => {
  const ids = new Set(navItems.value.filter((i) => i.id).map((i) => i.id))
  if (ids.has(section.value)) return section.value
  for (const [key, tabs] of Object.entries(tabGroups.value)) {
    if (tabs.some((t) => t.id === section.value)) return GROUP_NAV_ID[key] || tabs[0].id
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
  for (const [key, tabs] of Object.entries(tabGroups.value)) {
    const idx = tabs.findIndex((t) => t.id === section.value)
    if (idx === 0) return null
    if (idx > 0) {
      const pid = GROUP_NAV_ID[key] || tabs[0].id
      return { id: pid, label: navItems.value.find((i) => i.id === pid)?.label || tabs[0].label }
    }
  }
  return null
})

// Deep links del panel: /dashboard/<slug> (español, sin acentos) abre la
// sección directo — la URL queda prolija y compartible. Pasa por el setter
// de `section`: valida el plan vigente y abre el candado si falta el
// beneficio (mismo criterio que ?s= y los clics del menú).
const SECTION_SLUGS = {
  inicio: 'overview',
  productos: 'catalogs', catalogo: 'catalogs', catalogos: 'catalogs',
  servicios: 'services',
  vender: 'selling', ventas: 'sales', pedidos: 'orders',
  clientes: 'customers', consultas: 'inquiries', cobros: 'payconfig',
  cuentas: 'accounts', acceso: 'accounts', accesos: 'accounts',
  legal: 'legal', membresias: 'memberships',
  pagina: 'web', direccion: 'store',
  diseno: 'design', fotos: 'photos', negocio: 'company',
  visitas: 'stats', promocionar: 'tools', qr: 'tools', folletos: 'tools',
  opiniones: 'reviews', ayuda: 'support', asistente: 'bot',
  plan: 'plans', planes: 'plans', pagos: 'payments', facturas: 'invoices',
  cuenta: 'settings', novedades: 'changelog'
}
function sectionForSlug(slug) {
  return SECTION_SLUGS[String(slug || '')] || null
}
// /dashboard/<slug> → /dashboard/<otro> reusa esta vista (mismo componente):
// el param se observa en vivo. Solo aplica slugs mapeados — un replace a
// /dashboard pelado (retorno de MP, botones "volver") no pisa la sección.
watch(() => route.params.section, (slug) => {
  const id = sectionForSlug(slug)
  if (id) section.value = id
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
    selling: 'vender online ecommerce tienda online carrito checkout pedidos ventas clientes consultas soporte compradores cobros pagos fiscal mercado pago mp legal devoluciones terminos privacidad membresias suscripciones planes tienda',
    accounts: 'cuentas clientes acceso registro ingresar login google autenticacion compradores sesion perfil',
    pos: 'vender persona local fisico cobrar caja punto venta mostrador ticket',
    store: 'pagina web tienda diseno link direccion url dominio slug logo colores plantilla publicar pausar editar',
    reviews: 'opiniones comentarios valoraciones estrellas clientes review reputacion',
    support: 'ayuda soporte chat mensaje consulta hablar equipo problema duda',
    bot: 'asistente chatbot automatico responder preguntas robot virtual',
    tools: 'qr codigo folleto volante imprimir promocionar vidriera flyer repartir visitas estadisticas cuanta gente analytics numeros',
    plans: 'plan suscripcion pagos facturas comprobantes precio renovar debito automatico mercado pago cupon descuento vencimiento abonar',
    settings: 'cuenta datos contrasena email correo perfil fiscal cuit dni provincia ciudad celular nombre apellido seguridad',
    changelog: 'novedades cambios nuevo nuevo en davent actualizaciones changelog historial mejoras'
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
  cmds.push({ id: 'change-logo', label: 'Cambiar mi logo', hint: 'En Mis fotos', icon: 'image', kw: 'logo cambiar subir imagen marca foto perfil', run: go('photos'), group: 'Acciones', locked: navLocks.value.catalogs })
  cmds.push({ id: 'theme', label: theme.isDark ? 'Modo claro' : 'Modo oscuro', hint: 'Cambiar la apariencia del panel', icon: theme.isDark ? 'sun' : 'moon', kw: 'tema oscuro claro modo nocturno dark light apariencia color', run: () => theme.toggleTheme(), group: 'Acciones' })
  cmds.push({ id: 'coupon', label: 'Canjear un cupón', hint: 'Código promocional o de regalo', icon: 'gift', kw: 'cupon codigo promo promocional descuento regalo canjear', run: go('plans'), group: 'Acciones' })
  cmds.push({ id: 'password', label: 'Cambiar contraseña', hint: 'Seguridad de tu cuenta', icon: 'key', kw: 'contrasena password clave seguridad cambiar', run: go('settings'), group: 'Acciones' })
  cmds.push({ id: 'messages', label: 'Mensajes de soporte', hint: 'Abrir la conversación con el equipo', icon: 'message-circle', kw: 'mensajes chat soporte hablar conversacion inbox', run: () => onBellClick(), group: 'Acciones' })
  return cmds
})

// Los 4 destinos del pulgar + "Más" (el quinto tab lo dibuja el layout).
const mobileTabs = computed(() => [
  { id: 'overview', label: 'Inicio', icon: 'dashboard' },
  { id: 'catalogs', label: 'Vender', icon: 'package', locked: navLocks.value.catalogs },
  { id: 'web', label: 'Mi web', icon: 'store' },
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
  { title: 'Reservá tu link público', doneTitle: 'Link público reservado', text: 'Es la dirección de tu tienda, gratis.', done: store.hasStore, target: 'store', cta: 'Reservar', icon: 'globe' },
  { title: 'Elegí un plan', doneTitle: 'Plan elegido', text: 'Definí el tamaño de tu catálogo.', done: billing.hasSubscription, target: 'plans', cta: 'Elegir', icon: 'crown' },
  { title: 'Cargá tu primer producto', doneTitle: 'Productos cargados', text: 'Se publica solo en tu web.', done: catalog.products.length > 0, target: 'catalogs', cta: 'Cargar', icon: 'package' },
  { title: 'Subí la foto de portada', doneTitle: 'Portada cargada', text: 'Tu página se ve mejor con imagen.', done: Boolean(store.customization.cover), target: 'photos', cta: 'Subir', icon: 'image' },
  { title: 'Activá el asistente virtual', doneTitle: 'Asistente activo', text: 'Responde clientes 24/7 en tu web.', done: !canChatbot.value || Boolean(store.chatbot?.is_enabled), target: 'bot', cta: 'Activar', icon: 'bot' },
  { title: 'Compartí tu link público', text: 'Mandáselo a tus clientes por WhatsApp.', done: false, target: 'store', cta: 'Copiar', icon: 'send', run: copyLink }
])
const stepsDone = computed(() => nextSteps.value.filter((s) => s.done).length)
const pendingSteps = computed(() => nextSteps.value.filter((s) => !s.done))

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
  if (billing.subscription?.pending_plan_name) {
    const charge = billing.subscription.pending_charge
    const text = charge != null
      ? `Pagá solo la diferencia prorrateada ($${Number(charge).toLocaleString('es-AR')}) y el plan cambia al instante, sin mover tu fecha de facturación.`
      : 'Se aplica en tu próxima facturación, al precio del plan nuevo.'
    list.push({ id: 'pending', kind: 'info', title: `Cambio a ${billing.subscription.pending_plan_name} pendiente`, text, cta: 'Ver pagos', run: go('payments') })
  }
  if (storagePct.value >= 80) list.push({ id: 'storage', kind: 'warn', title: `Almacenamiento al ${storagePct.value}%`, text: 'Te estás quedando sin espacio para imágenes: borrá fotos viejas o ampliá el plan.', cta: 'Revisar', run: go('design') })
  if (chatUnread.value) list.push({ id: 'chat', kind: 'info', title: chatUnread.value === 1 ? 'Tenés un mensaje sin leer' : `Tenés ${chatUnread.value} mensajes sin leer`, text: 'El equipo de soporte te respondió.', cta: 'Responder', run: onBellClick })
  return list
})
const topAlert = computed(() => alertQueue.value[0] || null)
const extraAlerts = computed(() => alertQueue.value.slice(1))
const alertIcon = (kind) => ({ danger: 'circle-alert', warn: 'triangle-alert', info: 'info' }[kind] || 'bell')

// Visitas con contexto: semana actual vs. anterior.
const visitWeek = computed(() => {
  const days = store.visitStats?.days || []
  const now = days.slice(-7).reduce((a, d) => a + d.count, 0)
  const prev = days.slice(-14, -7).reduce((a, d) => a + d.count, 0)
  const delta = prev > 0 ? Math.round(((now - prev) / prev) * 100) : now > 0 ? 100 : null
  return { now, prev, delta }
})
const yesterdayVisits = computed(() => store.visitStats?.days?.slice(-2, -1)[0]?.count ?? 0)
const storagePct = computed(() => {
  const s = store.storage
  if (!s?.max_mb) return 0
  return Math.min(100, Math.round((s.used_bytes / (s.max_mb * 1024 * 1024)) * 100))
})

// Feed "Actividad reciente": cada entrada es accionable.
function relDays(iso) {
  const t = Date.parse(iso || '')
  if (!Number.isFinite(t)) return ''
  const d = Math.floor((Date.now() - t) / 86400000)
  return d <= 0 ? 'hoy' : d === 1 ? 'ayer' : `hace ${d} días`
}
const activityFeed = computed(() => {
  const go = (id) => () => { section.value = id }
  const items = []
  if (chatUnread.value) items.push({ icon: 'message-circle', title: chatUnread.value === 1 ? 'Un mensaje nuevo de soporte' : `${chatUnread.value} mensajes nuevos de soporte`, text: 'Abrí la conversación para responder.', cta: 'Responder', run: onBellClick })
  if (plan.value?.isCurrent && !plan.value.autoRenew && plan.value.remaining !== null && plan.value.remaining <= 7) items.push({ icon: 'clock', title: `Tu plan vence en ${plan.value.remaining} ${plan.value.remaining === 1 ? 'día' : 'días'}`, text: 'Renová para no perder tu web.', cta: 'Renovar', run: go('plans') })
  const rev = catalog.reviews[0]
  if (rev) items.push({ icon: 'star', title: `Nueva opinión de ${[rev.name, rev.surname_initial || rev.surname].filter(Boolean).join(' ') || 'un cliente'}`, text: [rev.is_positive ? 'Le gustó' : rev.is_positive === false ? 'No le gustó' : '', relDays(rev.created_at)].filter(Boolean).join(' · '), cta: 'Responder', run: go('reviews') })
  const today = store.visitStats?.today ?? 0
  const days = store.visitStats?.days || []
  const peak = days.reduce((m, d) => (d.count > (m?.count ?? -1) ? d : m), null)
  if (canStats.value && today) items.push({ icon: 'trending-up', title: `${today} ${today === 1 ? 'visita nueva' : 'visitas nuevas'} hoy`, text: peak?.count ? `Tu mejor día: ${peak.count} el ${fmtDate(peak.date)}.` : '', cta: 'Ver', run: go('stats') })
  const lastProduct = catalog.products.reduce((m, p) => (Date.parse(p.created_at || '') > Date.parse(m?.created_at || 0) ? p : m), null)
  if (lastProduct?.created_at) items.push({ icon: 'package', title: `Se publicó «${lastProduct.name}»`, text: `Ya está visible en tu web · ${relDays(lastProduct.created_at)}`, cta: 'Ver', run: go('catalogs') })
  const last = payments.payments[0]
  if (last) items.push({ icon: 'receipt', title: 'Último pago registrado', text: `${formatARS(last.amount)} · ${formatDateTime(last.paid_at || last.created_at)}`, cta: 'Ver pagos', run: go('payments') })
  return items.slice(0, 5)
})

// --- Inicio bento: tarjetas de números, gráfico y panel "Tu página" ---
const ownerName = computed(() => auth.user?.profile?.first_name || auth.user?.username || business.value || displayName.value)
const todayDelta = computed(() => {
  const today = store.visitStats?.today ?? 0
  const y = yesterdayVisits.value
  if (!y) return today > 0 ? 100 : null
  return Math.round(((today - y) / y) * 100)
})
const reviewStats = computed(() => {
  const list = catalog.reviews
  const pos = list.filter((r) => r.is_positive).length
  return { total: list.length, pct: list.length ? Math.round((pos / list.length) * 100) : null }
})
const WEEK_LETTERS = ['D', 'L', 'M', 'M', 'J', 'V', 'S']
const visitBars = computed(() => {
  const days = (store.visitStats?.days || []).slice(-14)
  if (!days.length) return []
  const max = Math.max(1, ...days.map((d) => d.count))
  return days.map((d) => ({
    h: Math.max(4, Math.round((d.count / max) * 100)),
    label: WEEK_LETTERS[new Date(`${d.date}T12:00:00`).getDay()],
    count: d.count,
    date: d.date
  }))
})
const heroSub = computed(() => {
  if (plan.value && !plan.value.isCurrent && plan.value.status !== 'Pendiente de pago') return 'Tu plan venció y la web pública está pausada. La renovás en un minuto.'
  if (!store.hasStore) return 'Reservá tu link público y empezá a vender hoy.'
  if (canStats.value && visitWeek.value.now) {
    const d = visitWeek.value.delta
    const cmp = d === null ? '' : d >= 0 ? `, un ${d}% más que la anterior` : `, un ${Math.abs(d)}% menos que la anterior`
    return `Tu web está publicada y recibiste ${visitWeek.value.now} visitas esta semana${cmp}.`
  }
  return 'Tu web está publicada. Compartí el link para sumar visitas y clientes.'
})
const designTarget = computed(() => {
  const b = plan.value?.benefits || {}
  return plan.value?.isCurrent && b.has_customization ? 'design' : 'web'
})
// Checklist "Calidad de tu web": score + checks del endpoint
// /stores/<slug>/web-quality/. Se monta en Inicio y se oculta solo con
// score 100; cada check navega a su pestaña vía el setter de `section`
// (valida ids y abre el candado del plan si la sección está bloqueada).
const { report: webQualityReport, loading: webQualityLoading, load: loadWebQuality } = useWebQuality(() => store.store?.slug)
watch(section, (s) => { if (s === 'overview') loadWebQuality() })
function onQualityNavigate(tab) { section.value = tab }
const stepsPct = computed(() => (nextSteps.value.length ? Math.round((stepsDone.value / nextSteps.value.length) * 100) : 0))
const quickLinks = [
  { id: 'catalogs', label: 'Productos', hint: 'Cargar y editar', icon: 'package' },
  { id: 'web', label: 'Mi página', hint: 'Diseño y dirección', icon: 'store' },
  { id: 'tools', label: 'Promocionar', hint: 'QR, folletos y visitas', icon: 'megaphone' },
  { id: 'stats', label: 'Visitas', hint: 'Tus números del mes', icon: 'trending-up' },
  { id: 'reviews', label: 'Opiniones', hint: 'Lo que dicen de vos', icon: 'star' },
  { id: 'bot', label: 'Asistente', hint: 'Responde 24/7', icon: 'bot' }
]

// (La vista previa viva de la web salió de Inicio en el rediseño: la portada
// muestra una sola acción principal; editar/ver la web quedan en accesos
// rápidos y en la sección Diseño.)

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// --- Mi tienda: link público (copiar, abrir, pausar, renombrar) ---
// El link público es path sobre el dominio de plataforma:
// https://www.davent.com.ar/[slug]
const slugPrefix = `${env.appUrl}/`
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

// --- Dominio propio (has_custom_domain, Plan premium): alta, DNS y verificación ---
const canCustomDomain = computed(() => Boolean(plan.value?.benefits?.has_custom_domain))
const domainInfo = ref(null)
const domainInput = ref('')
const domainBusy = ref(false)
const domainErr = ref('')
let domainLoaded = false
const domainStatus = computed(() => {
  const s = domainInfo.value?.status
  return { verified: { text: 'Verificado', kind: 'ok' }, failed: { text: 'DNS sin configurar', kind: 'danger' }, pending: { text: 'Pendiente', kind: 'muted' } }[s] || null
})
const domainUrl = computed(() => (domainInfo.value?.status === 'verified' ? `https://${domainInfo.value.domain}` : ''))

async function loadDomain() {
  try {
    domainInfo.value = await storesApi.getDomain()
    domainInput.value = domainInfo.value?.domain || ''
  } catch { /* sin web o error de red: la tarjeta queda con el formulario */ }
}
watch([section, () => store.hasStore], ([s, has]) => {
  if (s === 'store' && has && !domainLoaded) {
    domainLoaded = true
    loadDomain()
  }
}, { immediate: true })

async function saveDomainLink() {
  if (domainBusy.value) return
  domainBusy.value = true
  domainErr.value = ''
  try {
    domainInfo.value = await storesApi.saveDomain(domainInput.value)
    domainInput.value = domainInfo.value?.domain || domainInput.value.trim().toLowerCase()
    pushToast('Dominio guardado. Ahora configurá el DNS y verificalo')
  } catch (e) {
    const err = extractApiError(e)
    domainErr.value = err.domain || err.nonField || 'No se pudo guardar el dominio.'
  } finally {
    domainBusy.value = false
  }
}

function openDomain() {
  if (domainUrl.value) window.open(domainUrl.value, '_blank', 'noopener')
}

async function checkDomainNow() {
  if (domainBusy.value) return
  domainBusy.value = true
  domainErr.value = ''
  try {
    domainInfo.value = await storesApi.verifyDomain()
    if (domainInfo.value?.status === 'verified') pushToast('Dominio verificado: tu web ya responde ahí')
  } catch (e) {
    domainErr.value = extractApiError(e).nonField || 'No se pudo verificar el dominio.'
  } finally {
    domainBusy.value = false
  }
}

function removeDomain() {
  askConfirm({
    title: 'Desvincular el dominio',
    desc: 'Tu web deja de responder en ese dominio personalizado. Podés volver a vincularlo cuando quieras.',
    confirmLabel: 'Desvincular',
    action: async () => {
      if (domainBusy.value) return
      domainBusy.value = true
      domainErr.value = ''
      try {
        await storesApi.deleteDomain()
        domainInfo.value = null
        domainInput.value = ''
        pushToast('Dominio desvinculado')
      } catch (e) {
        domainErr.value = extractApiError(e).nonField || 'No se pudo quitar el dominio.'
      } finally {
        domainBusy.value = false
      }
    }
  })
}

// --- Mis catálogos: productos, categorías y marcas de la tienda ---
// El catálogo se habilita con suscripción activa (el backend devuelve 403 sin plan).
const catalogTab = ref('products') // products | categories | brands | discounts
const catalogSectionTabs = computed(() => [
  { id: 'products', label: 'Mis productos', icon: 'package', hint: 'Tu catálogo' },
  { id: 'categories', label: 'Categorías', icon: 'layout-grid', hint: 'Para ordenarlos' },
  { id: 'brands', label: 'Marcas', icon: 'tag', hint: 'De tus productos' },
  { id: 'discounts', label: 'Descuentos', icon: 'percent', hint: canDiscounts.value ? 'Se activan solos' : 'Premium' }
])
const showPriceUpdate = ref(false) // modal "Actualizar precios" (bulk + import CSV)
const catalogLoaded = ref(false)

// El interruptor del catálogo público (customization.show_catalog) y el
// carrusel de portada viven en esta misma sección, en la tarjeta "Tu
// página de catálogo": el dueño controla el catálogo por separado del
// diseño general de su web.

// offer_price ya no se edita: el precio promocionado lo dan los descuentos
// programados (pestaña Descuentos). Los productos viejos que lo tengan lo
// conservan hasta que el dueño lo quite — legacyOffer lo muestra y el
// botón "Quitar" lo limpia al guardar.
const productForm = reactive({ name: '', price: '', category: '', brand: '', description: '', is_active: true, stock: '' })
const productTouched = reactive({})
const legacyOffer = ref(null)
const offerCleared = ref(false)
const productBusy = ref(false)
const productEditing = ref(null)
const productImage = ref(null)
const productImagePreview = ref('')
const productImageCleared = ref(false)
const productImageErr = ref('')

// Tono estable por nombre: la misma categoría/marca lleva el mismo color
// en el punto de la fila (idéntico al de los productos).
function taxonomyHue(str) {
  let h = 0
  for (const ch of String(str || '?')) h = (h * 31 + ch.codePointAt(0)) % 360
  return h
}
const taxonomyForm = reactive({ category: '', brand: '' })
// Características de la categoría: chips que se agregan de a una
// (reemplaza el input separado por comas).
const taxonomyFeatures = ref([])
const taxonomyFeatureInput = ref('')
function addTaxonomyFeature() {
  const v = taxonomyFeatureInput.value.trim()
  if (!v) return
  if (taxonomyFeatures.value.some((f) => f.toLowerCase() === v.toLowerCase())) { taxonomyFeatureInput.value = ''; return }
  const next = [...taxonomyFeatures.value, v]
  const err = validateFeatureSchema(next)
  if (err) { taxonomyErr.category = err; return }
  taxonomyErr.category = ''
  taxonomyFeatures.value = next
  taxonomyFeatureInput.value = ''
}
const taxonomyBusy = reactive({ category: false, brand: false })
const taxonomyErr = reactive({ category: '', brand: '' })
// Imagen de marca: un solo input oculto; el botón de cada fila deja la
// marca objetivo y dispara el picker (PNG/JPG/WebP -> WebP con alfa).
const brandImageInput = ref(null)
const brandImageTarget = ref(null)
const brandImageBusy = ref(null)
const brandImageErr = ref('')
// Logo opcional al crear/editar la marca: queda elegido hasta el submit y
// se sube después por /brands/<id>/image/ (WebP con alfa, 2 MB).
const brandFormImage = ref(null)
const brandFormPreview = ref('')
const brandFormImageInput = ref(null)
const brandFormErr = ref('')
// Edición de marca: el mismo form del alta carga nombre (y permite cambiar
// el logo) — igual que categorías.
const brandEditing = ref(null)
// Buscador de la lista de marcas: filtra por nombre sin tildes.
const brandQuery = ref('')
const filteredBrands = computed(() => {
  const strip = (v) => (v || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const q = strip(brandQuery.value.trim())
  return q ? catalog.brands.filter((b) => strip(b.name).includes(q)) : catalog.brands
})
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
  if (s === 'catalogs') ensureCatalog()
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
// Toolbar del listado: filtros por categoría/marca, "solo en oferta",
// orden del listado (una sola vista: tabla densa).
const prodFilterCategory = ref('')
const prodFilterBrand = ref('')
const prodOnlyOffers = ref(false)
const prodSort = ref('newest')

const filteredProducts = computed(() => {
  const strip = (v) => (v || '').toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  const q = strip(productQuery.value.trim())
  let list = catalog.products.filter((p) => {
    if (q && ![p.name, p.category_name, p.brand_name].some((v) => strip(v).includes(q))) return false
    if (prodFilterCategory.value && p.category !== Number(prodFilterCategory.value)) return false
    if (prodFilterBrand.value && p.brand !== Number(prodFilterBrand.value)) return false
    if (prodOnlyOffers.value && productListOffer(p) == null) return false
    return true
  })
  const effective = (p) => productListOffer(p) ?? (Number(p.price) || 0)
  const pctOff = (p) => {
    const o = productListOffer(p)
    return o === null || !Number(p.price) ? 0 : (1 - o / Number(p.price))
  }
  if (prodSort.value === 'name') list = [...list].sort((a, b) => a.name.localeCompare(b.name, 'es'))
  else if (prodSort.value === 'price') list = [...list].sort((a, b) => effective(a) - effective(b))
  else if (prodSort.value === 'discount') list = [...list].sort((a, b) => pctOff(b) - pctOff(a))
  else list = [...list].sort((a, b) => Date.parse(b.created_at || 0) - Date.parse(a.created_at || 0))
  return list
})

// Paginado cliente del listado (la API devuelve el catálogo completo).
const PROD_PAGE_SIZE = 15
const prodPage = ref(1)
const pagedProducts = computed(() => {
  const start = (prodPage.value - 1) * PROD_PAGE_SIZE
  return filteredProducts.value.slice(start, start + PROD_PAGE_SIZE)
})
const prodPageInfo = computed(() => {
  const total = filteredProducts.value.length
  if (!total) return { from: 0, to: 0, total: 0, pages: 0 }
  const from = (prodPage.value - 1) * PROD_PAGE_SIZE + 1
  return { from, to: Math.min(prodPage.value * PROD_PAGE_SIZE, total), total, pages: Math.ceil(total / PROD_PAGE_SIZE) }
})
watch([productQuery, prodFilterCategory, prodFilterBrand, prodOnlyOffers, prodSort, () => catalog.products.length], () => { prodPage.value = 1; selectedIds.value = [] })

// Selección múltiple de la vista tabla + acciones en lote (bucles sobre los
// endpoints unitarios: el backend no expone bulk de productos).
const selectedIds = ref([])
const bulkBusy = ref(false)
async function bulkSetActive(active) {
  if (bulkBusy.value || !selectedIds.value.length) return
  bulkBusy.value = true
  const ids = [...selectedIds.value]
  for (const id of ids) {
    const p = catalog.products.find((x) => x.id === id)
    if (p && p.is_active !== active) await catalog.saveProduct(id, { fields: { is_active: active }, image: null, imageClear: false })
  }
  bulkBusy.value = false
  selectedIds.value = []
  pushToast(active ? 'Productos visibles en tu web' : 'Productos ocultos')
}
async function bulkRemove() {
  if (bulkBusy.value || !selectedIds.value.length) return
  const ids = [...selectedIds.value]
  const n = ids.length
  askConfirm({
    title: n === 1 ? 'Eliminar 1 producto' : `Eliminar ${n} productos`,
    desc: 'Se borran del catálogo y de tu web. No se puede deshacer.',
    action: async () => {
      bulkBusy.value = true
      for (const id of ids) await catalog.removeProduct(id)
      bulkBusy.value = false
      if (productEditing.value && ids.includes(productEditing.value)) closeProductForm()
      selectedIds.value = []
      pushToast(n === 1 ? 'Producto eliminado' : `${n} productos eliminados`)
    }
  })
}
async function bulkDuplicate() {
  if (bulkBusy.value || !selectedIds.value.length) return
  bulkBusy.value = true
  const ids = [...selectedIds.value]
  let n = 0
  for (const id of ids) {
    const p = catalog.products.find((x) => x.id === id)
    if (!p) continue
    const res = await catalog.saveProduct(null, {
      fields: {
        name: `${p.name} (copia)`, price: p.price, category: p.category || '', brand: p.brand || '',
        description: p.description || '', is_active: p.is_active, features: p.features || {},
        ...(hasStockControl.value && p.stock != null ? { stock: p.stock } : {})
      },
      image: null, imageClear: false
    })
    if (res?.ok) n++
  }
  bulkBusy.value = false
  selectedIds.value = []
  pushToast(n === 1 ? 'Producto duplicado' : `${n} productos duplicados`)
}

// Acciones de fila (menú ⋮): mismas operaciones que la barra de selección.
async function toggleProductActive(p) {
  await catalog.saveProduct(p.id, { fields: { is_active: !p.is_active }, image: null, imageClear: false })
  pushToast(p.is_active ? 'Producto oculto' : 'Producto visible en tu web')
}
function removeProduct(p) {
  askConfirm({
    title: `Eliminar «${p.name}»`,
    desc: 'El producto se borra del catálogo y de tu web. No se puede deshacer.',
    action: async () => {
      await catalog.removeProduct(p.id)
      if (productEditing.value === p.id) closeProductForm()
      pushToast('Producto eliminado')
    }
  })
}
async function duplicateProduct(p) {
  const res = await catalog.saveProduct(null, {
    fields: {
      name: `${p.name} (copia)`, price: p.price, category: p.category || '', brand: p.brand || '',
      description: p.description || '', is_active: p.is_active, features: p.features || {},
      ...(hasStockControl.value && p.stock != null ? { stock: p.stock } : {})
    },
    image: null, imageClear: false
  })
  if (res?.ok) pushToast('Producto duplicado')
}

// Chips de estado de la cabecera: escaneo rápido del catálogo.
const productStats = computed(() => {
  const list = catalog.products
  return {
    visible: list.filter((p) => p.is_active).length,
    offers: list.filter((p) => productListOffer(p) != null).length,
    noImage: list.filter((p) => !p.image).length,
    discounted: list.filter((p) => isDiscountedProduct(p)).length
  }
})

// Etiqueta de campaña por producto: entre los descuentos que lo cubren con
// campaña propia gana el que vence antes (máx. 1 etiqueta por tarjeta).
const productCampaign = computed(() => {
  const byName = new Map()
  for (const d of catalog.discounts) {
    if (d.campaign) byName.set(d.name, { campaign: d.campaign, ends_at: d.ends_at || '9999' })
  }
  const map = new Map()
  for (const p of catalog.products) {
    let best = null
    for (const n of p.discount_names || []) {
      const hit = byName.get(n)
      if (hit && (!best || hit.ends_at < best.ends_at)) best = hit
    }
    if (best) map.set(p.id, best.campaign)
  }
  return map
})

const productLimit = computed(() => plan.value?.benefits?.max_products)
// Control de stock del catálogo: superficie de la venta online — solo
// planes con has_ecommerce ven el campo en el form y la columna en la
// tabla (el backend lo rechaza con 400 si igual llega).
const hasStockControl = computed(() => Boolean(plan.value?.benefits?.has_ecommerce))
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
  const s = hasStockControl.value ? validateProductStock(productForm.stock) : ''
  if (n) e.name = n
  if (p) e.price = p
  if (d) e.description = d
  if (s) e.stock = s
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
  Object.assign(productForm, { name: '', price: '', category: '', brand: '', description: '', is_active: true, stock: '' })
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
    description: p.description || '', is_active: p.is_active, stock: p.stock ?? ''
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
  openProductForm()
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
      // stock solo viaja con has_ecommerce: '' limpia el control (NULL =
      // sin límite); sin el beneficio la clave no se manda y el valor
      // guardado queda intacto.
      ...(hasStockControl.value ? { stock: productForm.stock } : {}),
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
    closeProductForm()
  }
}

// El formulario vive en un drawer lateral: el inventario queda a ancho
// completo y el alta/edición no roba espacio permanente a la lista.
const productFormOpen = ref(false)
function openProductForm() {
  catalogTab.value = 'products'
  productFormOpen.value = true
}
function closeProductForm() {
  productFormOpen.value = false
  resetProductForm()
}
function onProductFormKey(e) {
  if (e.key === 'Escape' && productFormOpen.value) closeProductForm()
}
watch(productFormOpen, (open) => {
  if (open) document.addEventListener('keydown', onProductFormKey)
  else document.removeEventListener('keydown', onProductFormKey)
})

// CTA "Cargar producto": abre el drawer en modo alta.
async function focusProductForm() {
  resetProductForm()
  openProductForm()
}

// --- Descuentos programados: se activan y vencen solos por la ventana ---
// El precio promocionado lo calcula el backend al leer (nunca se pisa
// offer_price): acá solo se programa nombre, %, alcance y fechas. La ventana
// se edita como fecha + hora separadas (el datetime-local nativo mezclaba
// ambos en una caja críptica); "Sin fin" deja ends_at en null.
const pad2 = (n) => String(n).padStart(2, '0')
const localDateInput = (d) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`

const discountForm = reactive({
  name: '', percent: '', scope: 'all', category: '', brand: '',
  product_ids: [], campaign: '',
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
// Ventana del descuento: por defecto "Sin fin" (lo más simple); con
// "Personalizado" se despliegan las fechas, y si hay un evento especial
// en su ventana de configuración el descuento toma sus fechas solo.
const discountWindowPreset = ref('none')
const offers = useOffers()

// Ventana de configuración de cada campaña: los eventos cortos (2-3 días)
// se habilitan 3 días antes para dar tiempo de armarlos; los largos,
// desde el 1° del mes de inicio (p. ej. Navidad disponible todo diciembre).
function campaignConfigWindow(c) {
  const start = new Date(c?.starts_at || '')
  const end = new Date(c?.ends_at || '')
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
  const days = Math.max(1, Math.round((end - start) / 86400000))
  const open = days <= 3
    ? new Date(start.getTime() - 3 * 86400000)
    : new Date(start.getFullYear(), start.getMonth(), 1)
  return { open, close: end }
}
const availableCampaigns = computed(() => {
  const now = Date.now()
  return offers.campaigns.value.filter((c) => {
    const w = campaignConfigWindow(c)
    return w && now >= w.open.getTime() && now <= w.close.getTime()
  })
})
const selectedCampaign = computed(() => offers.campaigns.value.find((c) => c.id === Number(discountForm.campaign)) || null)
// Opciones del select: eventos en ventana + el ya elegido aunque haya vencido
// (así al editar un descuento viejo el select no queda en blanco).
const campaignOptions = computed(() => {
  const list = [...availableCampaigns.value]
  if (selectedCampaign.value && !list.some((c) => c.id === selectedCampaign.value.id)) list.push(selectedCampaign.value)
  return list
})

// Aviso "se aproxima un evento": todas las campañas en ventana de
// configuración, siempre. El dueño puede querer varias ofertas del mismo
// evento por alcance distinto (catálogo completo, categorías, marcas,
// productos) — que ya exista una no tiene que ocultar el CTA.
const upcomingCampaigns = computed(() => availableCampaigns.value)
watch(catalogTab, (t) => { if (t === 'discounts') offers.load() })
// Abre el drawer con el evento ya elegido: fechas fijas, solo falta nombre y %.
function newCampaignDiscount(c) {
  resetDiscountForm()
  discountForm.campaign = c.id
  discountWindowPreset.value = 'campaign'
  const s = isoToLocalInput(c.starts_at)
  const e = isoToLocalInput(c.ends_at)
  discountForm.end_none = false
  discountForm.start_date = s.slice(0, 10); discountForm.start_time = s.slice(11, 16) || '00:00'
  discountForm.end_date = e.slice(0, 10); discountForm.end_time = e.slice(11, 16) || '23:59'
  offers.load()
  openDiscountForm()
}

// El select "¿Cuándo?": 'camp:<id>' para eventos, presets para lo demás.
const discountWhen = computed({
  get: () => (discountForm.campaign ? `camp:${discountForm.campaign}` : discountWindowPreset.value),
  set: (v) => {
    if (String(v).startsWith('camp:')) {
      const c = offers.campaigns.value.find((x) => x.id === Number(String(v).slice(5)))
      if (!c) return
      discountForm.campaign = c.id
      discountWindowPreset.value = 'campaign'
      const s = isoToLocalInput(c.starts_at)
      const e = isoToLocalInput(c.ends_at)
      discountForm.end_none = false
      discountForm.start_date = s.slice(0, 10); discountForm.start_time = s.slice(11, 16) || '00:00'
      discountForm.end_date = e.slice(0, 10); discountForm.end_time = e.slice(11, 16) || '23:59'
      return
    }
    discountForm.campaign = ''
    if (v === 'custom') {
      // Venir de un evento no debe arrastrar sus fechas: arrancan limpias.
      discountForm.end_none = false
      discountForm.start_date = localDateInput(new Date()); discountForm.start_time = '00:00'
      discountForm.end_date = ''; discountForm.end_time = '23:59'
      discountWindowPreset.value = 'custom'
      return
    }
    discountPreset(v)
  }
})
function discountPreset(kind) {
  discountWindowPreset.value = kind
  if (kind === 'custom') { discountForm.end_none = false; return }
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
    name: '', percent: String(DISCOUNT_DEFAULT_PERCENT), scope: 'all', category: '', brand: '',
    product_ids: [], campaign: '',
    start_date: localDateInput(new Date()), start_time: '00:00',
    end_none: true, end_date: '', end_time: '23:59',
    is_active: true
  })
  Object.keys(discountTouched).forEach((k) => { discountTouched[k] = false })
  discountEditing.value = null
  discountWindowPreset.value = 'none'
}

// El alta/edición abre el drawer (mismo patrón que el form de producto).
const discountFormOpen = ref(false)
function openDiscountForm() { discountFormOpen.value = true }
function closeDiscountForm() { discountFormOpen.value = false; resetDiscountForm() }
function newDiscount() { resetDiscountForm(); offers.load(); openDiscountForm() }
function onDiscountFormKey(e) { if (e.key === 'Escape' && discountFormOpen.value) closeDiscountForm() }
watch(discountFormOpen, (open) => {
  if (open) document.addEventListener('keydown', onDiscountFormKey)
  else document.removeEventListener('keydown', onDiscountFormKey)
})

function editDiscount(d) {
  discountEditing.value = d.id
  const start = isoToLocalInput(d.starts_at)
  const end = isoToLocalInput(d.ends_at)
  Object.assign(discountForm, {
    name: d.name, percent: d.percent, scope: d.scope,
    category: d.category || '', brand: d.brand || '', product_ids: [...(d.products || [])],
    campaign: d.campaign?.id || '',
    start_date: start.slice(0, 10), start_time: start.slice(11, 16) || '00:00',
    end_none: !end, end_date: end.slice(0, 10), end_time: end.slice(11, 16) || '23:59',
    is_active: d.is_active
  })
  discountWindowPreset.value = d.campaign ? 'campaign' : (d.ends_at ? 'custom' : 'none')
  catalog.notice = ''
  catalog.lastError = ''
  offers.load()
  openDiscountForm()
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
    campaign: discountForm.campaign || null,
    // Con evento las fechas quedan congeladas a la ventana de la campaña.
    starts_at: localInputToIso(selectedCampaign.value ? isoToLocalInput(selectedCampaign.value.starts_at) : discountStartLocal.value),
    ends_at: selectedCampaign.value
      ? localInputToIso(isoToLocalInput(selectedCampaign.value.ends_at))
      : (discountForm.end_none ? null : localInputToIso(discountEndLocal.value)),
    is_active: discountForm.is_active
  })
  discountBusy.value = false
  if (ok) closeDiscountForm()
}

async function toggleDiscount(d) {
  if (discountBusy.value) return
  discountBusy.value = true
  await catalog.toggleDiscount(d)
  discountBusy.value = false
}

function removeDiscount(d) {
  askConfirm({
    title: 'Eliminar la oferta',
    desc: 'La promoción deja de aplicarse en tu catálogo y en tu web.',
    action: async () => {
      if (discountBusy.value) return
      discountBusy.value = true
      await catalog.removeDiscount(d.id)
      discountBusy.value = false
      if (discountEditing.value === d.id) closeDiscountForm()
    }
  })
}

async function addTaxonomy(kind) {
  const name = taxonomyForm[kind].trim()
  taxonomyErr[kind] = validateTaxonomyName(name)
  if (taxonomyErr[kind]) return
  const payload = { name }
  if (kind === 'category') {
    // Lo que quedó tipeado sin tocar "Agregar" entra como última característica.
    const schema = taxonomyFeatureInput.value.trim() && !taxonomyFeatures.value.some((f) => f.toLowerCase() === taxonomyFeatureInput.value.trim().toLowerCase())
      ? [...taxonomyFeatures.value, taxonomyFeatureInput.value.trim()]
      : [...taxonomyFeatures.value]
    const schemaErr = validateFeatureSchema(schema)
    if (schemaErr) { taxonomyErr.category = schemaErr; return }
    payload.feature_schema = schema
  }
  taxonomyBusy[kind] = true
  if (kind === 'category') {
    const ok = await catalog.saveCategory(taxonomyEditing.value, payload)
    taxonomyBusy.category = false
    if (ok) {
      taxonomyForm.category = ''
      cancelCategoryEdit()
    } else taxonomyErr.category = catalog.fieldErrors.name || catalog.fieldErrors.feature_schema || catalog.lastError
    return
  }
  const res = await catalog.saveBrand(brandEditing.value, payload)
  taxonomyBusy.brand = false
  if (!res.ok) {
    taxonomyErr.brand = catalog.fieldErrors.name || catalog.lastError
    return
  }
  // Si venía logo elegido se sube por el endpoint de imagen (multipart ->
  // normalize_image). Si falla, la marca queda guardada y el error se
  // muestra abajo para reintentar desde la fila.
  const image = brandFormImage.value
  const brandId = res.data?.item?.id || brandEditing.value
  if (image && brandId) {
    const up = await catalog.saveBrandImage(brandId, image)
    if (!up.ok) brandImageErr.value = catalog.lastError
  }
  taxonomyForm.brand = ''
  brandEditing.value = null
  clearBrandFormImage()
}

// Carga la marca en el form para editar nombre y logo (misma vista que
// "Agregar", con botón Guardar). El preview arranca con su imagen actual.
function editBrand(b) {
  brandEditing.value = b.id
  taxonomyForm.brand = b.name
  taxonomyErr.brand = ''
  brandFormErr.value = ''
  if (brandFormPreview.value?.startsWith('blob:')) URL.revokeObjectURL(brandFormPreview.value)
  brandFormImage.value = null
  brandFormPreview.value = b.image || ''
}
function cancelBrandEdit() {
  brandEditing.value = null
  taxonomyForm.brand = ''
  brandFormErr.value = ''
  if (brandFormPreview.value?.startsWith('blob:')) URL.revokeObjectURL(brandFormPreview.value)
  brandFormImage.value = null
  brandFormPreview.value = ''
}

function onBrandFormImagePicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  brandFormErr.value = validateLogoFile(file)
  if (brandFormErr.value) return
  if (brandFormPreview.value?.startsWith('blob:')) URL.revokeObjectURL(brandFormPreview.value)
  brandFormImage.value = file
  brandFormPreview.value = URL.createObjectURL(file)
}
function clearBrandFormImage() {
  if (brandFormPreview.value?.startsWith('blob:')) URL.revokeObjectURL(brandFormPreview.value)
  brandFormImage.value = null
  brandFormErr.value = ''
  const editing = catalog.brands.find((b) => b.id === brandEditing.value)
  brandFormPreview.value = editing?.image || ''
}

// Carga la categoría en el form para editar nombre y plantilla de
// características (misma vista que "Agregar", con botón Guardar).
function editCategory(c) {
  taxonomyEditing.value = c.id
  taxonomyForm.category = c.name
  taxonomyFeatures.value = [...(c.feature_schema || [])]
  taxonomyFeatureInput.value = ''
  taxonomyErr.category = ''
}

function cancelCategoryEdit() {
  taxonomyEditing.value = null
  taxonomyForm.category = ''
  taxonomyFeatures.value = []
  taxonomyFeatureInput.value = ''
  taxonomyErr.category = ''
}

function removeTaxonomy(kind, item) {
  const label = kind === 'category' ? 'categoría' : 'marca'
  askConfirm({
    title: `Eliminar la ${label} «${item.name}»`,
    desc: `La ${label} se quita de tu catálogo. Los productos que la tengan asignada quedan sin ${label === 'categoría' ? 'categoría' : 'marca'}.`,
    action: async () => {
      const ok = kind === 'category' ? await catalog.removeCategory(item.id) : await catalog.removeBrand(item.id)
      if (!ok) taxonomyErr[kind] = catalog.lastError
      else if (kind === 'category' && taxonomyEditing.value === item.id) cancelCategoryEdit()
      else if (kind === 'brand' && brandEditing.value === item.id) cancelBrandEdit()
    }
  })
}

function pickBrandImage(brand) {
  brandImageTarget.value = brand
  brandImageErr.value = ''
  brandImageInput.value?.click()
}
async function onBrandImagePicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  const brand = brandImageTarget.value
  brandImageTarget.value = null
  if (!file || !brand) return
  brandImageErr.value = validateLogoFile(file)
  if (brandImageErr.value) return
  brandImageBusy.value = brand.id
  const res = await catalog.saveBrandImage(brand.id, file)
  brandImageBusy.value = null
  if (!res.ok) brandImageErr.value = catalog.lastError
}
function removeBrandImage(brand) {
  askConfirm({
    title: `Quitar la imagen de ${brand.name}`,
    desc: 'La marca queda solo con su nombre en tu catálogo.',
    action: async () => {
      if (brandImageBusy.value) return
      brandImageBusy.value = brand.id
      brandImageErr.value = ''
      const res = await catalog.removeBrandImage(brand.id)
      brandImageBusy.value = null
      if (!res.ok) brandImageErr.value = catalog.lastError
    }
  })
}

// --- QR y folletos (premium): QR del link público + folleto imprimible ---
const qrDataUrl = ref('')
const canStats = computed(() => Boolean(plan.value?.benefits?.has_stats))
// Visitas de la web pública (endpoint /stores/stats/: 1 por visitante/día).
const visitDays = computed(() => store.visitStats?.days || [])
const visitMax = computed(() => Math.max(1, ...visitDays.value.map((d) => d.count)))
const visitHasData = computed(() => visitDays.value.some((d) => d.count > 0))
const visitAvg = computed(() => {
  if (!visitDays.value.length) return '0'
  const sum = visitDays.value.reduce((a, d) => a + d.count, 0)
  return (sum / visitDays.value.length).toFixed(1)
})
const canQr = computed(() => Boolean(plan.value?.benefits?.has_qr))
const canFlyers = computed(() => Boolean(plan.value?.benefits?.has_flyers))
const canFlyerEditor = computed(() => Boolean(plan.value?.benefits?.has_flyer_editor))

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

// El preview arranca con un 25% de muestra: un "-0%" se lee como error y el
// ejemplo explica mejor qué va a ver el cliente.
const discountPreviewPct = computed(() => Math.min(DISCOUNT_LIMITS.percentMax, Math.max(DISCOUNT_LIMITS.percentMin, Math.round(Number(discountForm.percent)) || DISCOUNT_DEFAULT_PERCENT)))
const toolsTab = ref('ready')
watch([section, canFlyers, canFlyerEditor], () => {
  if (!canFlyers.value && toolsTab.value === 'studio') toolsTab.value = 'ready'
  if (!canFlyerEditor.value && toolsTab.value === 'editor') toolsTab.value = 'ready'
})

function openFlyer(custom = false) {
  const href = router.resolve({ name: 'store-flyer', query: custom ? { custom: custom === true ? '1' : String(custom) } : {} }).href
  window.open(href, '_blank', 'noopener')
}

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
const designForm = reactive({ ...CUSTOMIZATION_DEFAULTS, services: [], stats: [], testimonials: [], faqs: [], hours: [], benefits: [], timeline: [], team: [], plans: [], section_order: [], announcements: [], site_templates: [], service_steps: [], service_days: [], service_slots: [], layout_config: {}, site_theme: {} })
const designTouched = reactive({})
const designTab = ref('look')
const designPreviewOpen = ref(false)
const canCustomize = computed(() => Boolean(plan.value?.benefits?.has_customization))
const canDesignAdvanced = computed(() => Boolean(plan.value?.benefits?.has_design_advanced))
// Editor Avanzado: modal fullscreen del site_theme (botón en Diseño).
// Sin has_design_advanced el click abre el modal de planes, no el editor.
const studioModalOpen = ref(false)
function onOpenStudio() {
  if (!canDesignAdvanced.value) { openLocked('design_studio'); return }
  studioModalOpen.value = true
}

// "Asistencia con IA": mismo modal con dos contextos ('design' | 'business').
// Candado = has_ai_design (mismo gate que el diseño asistido) + opt-out del
// primer ingreso (profile.ai_assist_enabled; sin perfil cargado se asume
// activa, que es el default del modelo).
const aiAssistEnabled = computed(() => (auth.user?.profile ? auth.user.profile.ai_assist_enabled !== false : true))
const aiOptInOpen = ref(false)
const aiOptInPending = ref(false)
const assistOpen = ref(false)
const assistOrigin = ref('design')
function openAssist(origin) {
  if (!aiAssistEnabled.value) return
  if (navLocks.value.design_assisted) { openLocked('design_assisted'); return }
  assistOrigin.value = origin
  assistOpen.value = true
}
function onAssistApplied() {
  Object.assign(designForm, store.customization)
  pushToast('Listo ✓')
}
const canLocationMap = computed(() => Boolean(plan.value?.benefits?.has_location_map))
const canLiveStream = computed(() => Boolean(plan.value?.benefits?.has_live_stream))
const videosCap = computed(() => videosLimit(plan.value?.benefits || {}))
const canProductComments = computed(() => Boolean(plan.value?.benefits?.has_product_comments))
const canDiscounts = computed(() => Boolean(plan.value?.benefits?.has_discounts))
const businessInitial = computed(() => (business.value || 'T').slice(0, 1).toUpperCase())
const IDENTITY_DEFAULTS = { accent_custom: '', logo_scale: 'm', logo_mode: 'logo_name', mono_style: 'accent', cover_overlay: 0, cover_focus_x: 50, cover_focus_y: 50 }
// Todos los diseños del catálogo quedan habilitados para el usuario (sin
// recorte por plan): el diseño elegido es el que bloquea las plantillas de
// la web que no cubre — ver designSitePages.
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
  // Los beneficios de cada plan viajan como lista; en el formulario se
  // editan como texto (uno por línea) y savePlans los vuelve a partir.
  designForm.plans = (Array.isArray(designForm.plans) ? designForm.plans : []).map((p) => ({ ...p, items: Array.isArray(p.items) ? p.items.join('\n') : String(p.items || '') }))
  Object.assign(designForm, keep)
  lastServerDesign = Object.fromEntries(DESIGN_FIELDS.map((k) => [k, { ...CUSTOMIZATION_DEFAULTS, ...store.customization }[k]]))
  // La fuente guardada tiene que estar cargada cuando llega el valor:
  // la vista previa del panel y el picker la muestran con la tipografía real.
  ensureStoreFont(designForm.name_font)
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
// Apartados por diseño: cada plantilla declara su whitelist en
// blocks.landing (templates/<id>/index.js). Si el diseño elegido no
// soporta la sección (Servicios, Planes de suscripción…), la tarjeta se
// bloquea y la web pública nunca la monta.
const templateLandingBlocks = computed(() => templateDef(designForm.template).blocks?.landing || [])
const supportsBlock = (id) => templateLandingBlocks.value.some((b) => (typeof b === 'string' ? b : b.id) === id)
const supportsServices = computed(() => supportsBlock('services'))
const supportsPlans = computed(() => supportsBlock('plans'))
const blockDesigns = (id) => Object.entries(TEMPLATE_DEFS)
  .filter(([, def]) => (def.blocks?.landing || []).some((b) => (typeof b === 'string' ? b : b.id) === id))
  .map(([key]) => TEMPLATE_LABELS[key] || key)
  .join(', ')
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

// "Sobre mi negocio": cada bloque es una tarjeta-lanzador que abre su
// formulario dentro de un modal (menos scroll, más amigable para usuarios
// no técnicos). El orden de las tarjetas sigue el de las secciones de la web.
const mkOpen = ref(null)
const mkNav = [
  { key: 'identity', label: 'Tu negocio', icon: 'user', desc: 'Nombre, titular y descripción' },
  { key: 'about', label: 'Sobre nosotros', icon: 'store', desc: 'Tu historia, años y misión' },
  { key: 'services', label: 'Qué ofrecemos', icon: 'layout-grid', desc: 'Ventajas y servicios con ícono' },
  { key: 'plans', label: 'Planes y membresías', icon: 'crown', desc: 'Packs y clubs para tus clientes' },
  { key: 'stats', label: 'Tus números', icon: 'trending-up', desc: 'Cifras que generan confianza' },
  { key: 'testimonials', label: 'Testimonios', icon: 'star', desc: 'Lo que dicen tus clientes' },
  { key: 'faqs', label: 'Preguntas frecuentes', icon: 'message-circle', desc: 'Respuestas a dudas comunes' },
  { key: 'benefits', label: 'Garantías', icon: 'shield-check', desc: 'Envíos, garantía y formas de pago' },
  { key: 'timeline', label: 'Tu trayectoria', icon: 'calendar', desc: 'Hitos del negocio, paso a paso' },
  { key: 'team', label: 'Tu equipo', icon: 'users', desc: 'Quiénes trabajan con vos' },
  { key: 'hours', label: 'Horarios', icon: 'clock', desc: 'Cuándo atendés al público' },
  { key: 'cta', label: 'Llamado a la acción', icon: 'zap', desc: 'El botón final que invita a escribirte' },
  { key: 'ann', label: 'Anuncios', icon: 'megaphone', desc: 'Novedades que corren bajo la portada' },
  { key: 'video', label: 'Videos', icon: 'play', desc: 'Videos de tus redes y stream en vivo' },
  { key: 'contact', label: 'Contacto y redes', icon: 'phone', desc: 'WhatsApp, redes y email público' },
  { key: 'extras', label: 'Extras', icon: 'plus', desc: 'Aviso del catálogo y frase del pie' }
]
const mkOpenMeta = computed(() => mkNav.find((m) => m.key === mkOpen.value) || null)
// Estado resumido de cada bloque: cuánto hay cargado (para el sello de la
// tarjeta-lanzador — el usuario ve de un vistazo qué le falta).
function mkSummary(key) {
  const f = designForm
  const n = (list) => (Array.isArray(list) ? list.length : 0)
  switch (key) {
    case 'identity': return (f.display_name || f.headline || f.description) ? 'Con contenido' : ''
    case 'about': return (f.about_text || f.about_mission || f.about_specialties || f.about_years) ? 'Con contenido' : ''
    case 'services': return n(f.services) ? `${n(f.services)} cargado${n(f.services) === 1 ? '' : 's'}` : ''
    case 'plans': return n(f.plans) ? `${n(f.plans)} cargado${n(f.plans) === 1 ? '' : 's'}` : ''
    case 'stats': return n(f.stats) ? `${n(f.stats)} cargado${n(f.stats) === 1 ? '' : 's'}` : ''
    case 'testimonials': return n(f.testimonials) ? `${n(f.testimonials)} cargado${n(f.testimonials) === 1 ? '' : 's'}` : ''
    case 'faqs': return n(f.faqs) ? `${n(f.faqs)} cargada${n(f.faqs) === 1 ? '' : 's'}` : ''
    case 'benefits': return n(f.benefits) ? `${n(f.benefits)} cargada${n(f.benefits) === 1 ? '' : 's'}` : ''
    case 'timeline': return n(f.timeline) ? `${n(f.timeline)} cargado${n(f.timeline) === 1 ? '' : 's'}` : ''
    case 'team': return n(f.team) ? `${n(f.team)} cargado${n(f.team) === 1 ? '' : 's'}` : ''
    case 'hours': return n(f.hours) ? `${n(f.hours)} cargado${n(f.hours) === 1 ? '' : 's'}` : ''
    case 'cta': return (f.cta_title || f.cta_text || f.cta_label) ? 'Con contenido' : ''
    case 'ann': return n(f.announcements) ? `${n(f.announcements)} cargado${n(f.announcements) === 1 ? '' : 's'}` : ''
    case 'video': {
      const nv = n(f.videos) + (f.video_url ? 1 : 0)
      return (nv || f.live_stream_url) ? `${nv ? `${nv} video${nv === 1 ? '' : 's'}` : ''}${nv && f.live_stream_url ? ' + ' : ''}${f.live_stream_url ? 'en vivo' : ''}` : ''
    }
    case 'contact': return (f.whatsapp || f.instagram || f.tiktok || f.facebook || f.contact_email) ? 'Con contenido' : ''
    case 'extras': return (f.catalog_note || f.footer_text) ? 'Con contenido' : ''
    default: return ''
  }
}
watch(mkOpen, (on) => {
  document.body.style.overflow = on ? 'hidden' : ''
  //Video legado (video_url suelto): se migra a la lista la primera vez que
  //se abre el editor para que el dueño lo vea y pueda ampliarlo.
  if (on === 'video' && !(designForm.videos || []).length && designForm.video_url) {
    designForm.videos = [designForm.video_url]
  }
})
function onMkKey(e) { if (e.key === 'Escape' && mkOpen.value) mkOpen.value = null }
onMounted(() => window.addEventListener('keydown', onMkKey))
onUnmounted(() => {
  window.removeEventListener('keydown', onMkKey)
  document.body.style.overflow = ''
})

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

// Identidad visible de la portada (nombre, titular, descripción) y datos de
// contacto/redes: viajan en el mismo PATCH parcial que el resto de las
// tarjetas — antes no tenían editor en ninguna sección.
const IDENTITY_FIELDS = ['display_name', 'headline', 'description']
const CONTACT_FIELDS = ['contact_email', 'whatsapp', 'instagram', 'tiktok', 'facebook']
async function saveIdentity() {
  IDENTITY_FIELDS.forEach((k) => { designTouched[k] = true })
  if (IDENTITY_FIELDS.some((k) => designErrors.value[k])) return
  companyBusy.value = true
  const ok = await store.saveCustomization({
    display_name: designForm.display_name.trim(),
    headline: designForm.headline.trim(),
    description: designForm.description.trim()
  })
  companyBusy.value = false
  if (ok) pushToast('Guardado ✓')
}

async function saveContact() {
  CONTACT_FIELDS.forEach((k) => { designTouched[k] = true })
  if (CONTACT_FIELDS.some((k) => designErrors.value[k])) return
  companyBusy.value = true
  const ok = await store.saveCustomization({
    contact_email: designForm.contact_email.trim(),
    show_contact: Boolean(designForm.show_contact),
    whatsapp: normalizeWhatsapp(designForm.whatsapp),
    instagram: normalizeInstagram(designForm.instagram),
    tiktok: normalizeTiktok(designForm.tiktok),
    facebook: normalizeFacebook(designForm.facebook),
    show_location: Boolean(designForm.show_location)
  })
  companyBusy.value = false
  if (ok) pushToast('Guardado ✓')
}

async function saveServices() {
  if (!supportsServices.value) return
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

async function savePlans() {
  companyErrs.plans = ''
  if (validateSectionTitle(designForm.plans_title.trim())) { companyErrs.plans = 'El título admite hasta 80 caracteres.'; return }
  if (hasPartialRow(designForm.plans, ['name', 'price'], ['name', 'price'])) {
    companyErrs.plans = 'Cada plan necesita nombre y precio. Completá la fila o borrala con el tachito.'
    return
  }
  companyBusy.value = true
  await store.saveCustomization({
    plans_title: designForm.plans_title.trim(),
    show_plans: Boolean(designForm.show_plans),
    plans: designForm.plans
      .map((p) => ({
        name: String(p.name || '').trim(),
        price: String(p.price || '').trim(),
        note: String(p.note || '').trim(),
        items: String(p.items || '').split(/\r?\n/).map((f) => f.trim()).filter(Boolean)
      }))
      .filter((p) => p.name && p.price)
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
  const bad = (designForm.videos || []).find((u) => validateVideoUrl(String(u || '').trim()))
  const err = (bad ? validateVideoUrl(String(bad || '').trim()) : '')
    || validateLiveStreamUrl(designForm.live_stream_url.trim())
    || validateSectionTitle(designForm.video_title.trim())
  if (err) { companyErrs.video = err; return }
  companyBusy.value = true
  await store.saveCustomization({
    show_video: Boolean(designForm.show_video),
    video_title: designForm.video_title.trim(),
    videos: (designForm.videos || []).map((u) => String(u || '').trim()).filter(Boolean),
    live_stream_url: designForm.live_stream_url.trim()
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

const leaveStay = ref(null)
const leaveGuard = reactive({ open: false, target: null, route: null })
watch(() => leaveGuard.open, (on) => { if (on) nextTick(() => leaveStay.value?.focus()) })

// Confirmación genérica para acciones destructivas (borrar, desvincular).
const confirmStay = ref(null)
const confirmDlg = reactive({ open: false, title: '', desc: '', confirmLabel: 'Eliminar', danger: true, action: null })
watch(() => confirmDlg.open, (on) => { if (on) nextTick(() => confirmStay.value?.focus()) })
function askConfirm(opts) {
  Object.assign(confirmDlg, { desc: '', confirmLabel: 'Eliminar', danger: true, action: null }, opts, { open: true })
}
function resolveConfirm(ok) {
  const fn = confirmDlg.action
  confirmDlg.open = false
  confirmDlg.action = null
  if (ok && typeof fn === 'function') fn()
}
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
onUnmounted(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
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
// El diseño elegido bloquea las plantillas que no cubre: si hay un patrón
// seleccionado mandan sus superficies declaradas (patternSurfaces); si no,
// las páginas que ofrece la plantilla base (templates/raiz).
const sitePatternList = ref([])
const LAYOUT_SURFACE_SET = new Set(['landing', 'catalog', 'services'])
const sameLayout = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})
const selectedSitePattern = computed(() => (
  sitePatternList.value.find((p) => p.slug === designForm.template)
  || sitePatternList.value.find((p) => (
    p.template === designForm.template && sameLayout(normalizeLayoutConfig(p.layout), designForm.layout_config)
  ))
  || sitePatternList.value.find((p) => p.template === designForm.template)
  || null
))
const designSitePages = computed(() => {
  const pages = !selectedSitePattern.value
    ? new Set(templatePages(designForm.template))
    : new Set([
        ...patternSurfaces(selectedSitePattern.value),
        // Las claves que no son superficies de layout (p. ej. 'plans') las
        // declara el template del patrón en `pages`, no su layout.
        ...templatePages(selectedSitePattern.value.template).filter((k) => !LAYOUT_SURFACE_SET.has(k))
      ])
  // 'plans' solo se puede activar cuando el diseño la declara en `pages`
  // (Ruta/Turismo no la cubre: la opción desaparece del selector).
  if (templatePages(selectedSitePattern.value?.template || designForm.template).includes('plans')) pages.add('plans')
  return [...pages]
})
const allowedSiteTemplates = computed(() =>
  allowedSiteTemplatesFor(plan.value?.benefits || {}).filter((k) => designSitePages.value.includes(k)))
const siteTemplatesMax = computed(() => siteTemplatesLimit(plan.value?.benefits || {}))
// Set que se muestra: guardado normalizado ∩ plan ∩ diseño (el backend manda
// lo guardado; acá se recorta igual que effective_site_templates).
const designSiteTemplates = computed(() =>
  resolveSiteTemplates(designForm.site_templates, plan.value?.benefits || {}).filter((k) => designSitePages.value.includes(k)))
const siteTemplatesHint = computed(() => {
  const max = siteTemplatesMax.value
  return max === null ? 'Tu plan permite tener todas las páginas activas.' : `Tu plan permite hasta ${max} ${max === 1 ? 'página' : 'páginas'} a la vez.`
})
function siteTemplateLock(key) {
  if (!designSitePages.value.includes(key)) return 'No disponible para este diseño'
  if (key === 'services' && !canServicesSite.value) return 'Desde Estándar'
  if (!designSiteTemplates.value.includes(key) && siteTemplatesMax.value !== null && designSiteTemplates.value.length >= siteTemplatesMax.value) {
    return `Tu plan admite hasta ${siteTemplatesMax.value} ${siteTemplatesMax.value === 1 ? 'página' : 'páginas'}`
  }
  return ''
}
function canToggleSiteTemplate(key) {
  if (siteTemplatesBusy.value || !designSitePages.value.includes(key) || !allowedSiteTemplates.value.includes(key)) return false
  const on = designSiteTemplates.value.includes(key)
  if (on) return designSiteTemplates.value.length > 1 // la web nunca queda vacía
  return siteTemplatesMax.value === null || designSiteTemplates.value.length < siteTemplatesMax.value
}
// Opciones del grupo "Páginas" del modal Qué mostrar (DesignStylesTab):
// mismo estado y locks que la lista de Diseño → las arma el padre.
const designPageOptions = computed(() => siteTemplateKeys.map((key) => ({
  key,
  label: siteTemplates[key].label,
  desc: siteTemplates[key].desc,
  on: designSiteTemplates.value.includes(key),
  lock: siteTemplateLock(key),
  disabled: !canToggleSiteTemplate(key),
  busy: siteTemplatesBusy.value
})))
// Diseños compatibles con la combinación de páginas: un patrón cubre una
// superficie si su `layout` la declara (o la hereda su template). Si la
// combinación elegida no tiene ningún diseño, el toggle se revierte y se
// obliga a elegir otra — la sección Diseño filtra por el mismo criterio.
let sitePatternPromise = null
function loadSitePatterns() {
  if (!sitePatternPromise) {
    sitePatternPromise = designApi.listPatterns().catch(() => [])
    sitePatternPromise.then((list) => { sitePatternList.value = list })
  }
  return sitePatternPromise
}
onMounted(() => loadSitePatterns())
// Toggle de página en "Qué mostrar": solo muta el form (borrador). La
// publicación sale del footer del modal — «Aplicar y guardar» →
// saveShowFromModal — que hace el PATCH de páginas + saveDesign una vez.
async function toggleSiteTemplate(key) {
  if (!canToggleSiteTemplate(key)) return
  const current = [...designSiteTemplates.value]
  const i = current.indexOf(key)
  if (i === -1) current.push(key)
  else current.splice(i, 1)
  const next = SITE_TEMPLATE_KEYS.filter((k) => current.includes(k))
  if (next.length) {
    const patterns = await loadSitePatterns()
    if (patterns.length && !patternsForSiteTemplates(patterns, next).length) {
      pushToast('Esa combinación no tiene diseños disponibles: elegí otra en «Qué mostrar».')
      return
    }
  }
  designForm.site_templates = next
  designForm.show_catalog = next.includes('catalog')
}
// «Aplicar y guardar» del modal: primero el set de páginas (reglas de
// plan/diseño propias del PATCH), después el diseño completo — publica
// layout_config con los bloques apagados/prendidos.
async function saveShowFromModal() {
  siteTemplatesBusy.value = true
  const okPages = await store.saveCustomization({
    site_templates: normalizeSiteTemplates(designForm.site_templates),
    show_catalog: Boolean(designForm.show_catalog)
  })
  siteTemplatesBusy.value = false
  if (!okPages) {
    pushToast(store.lastError || 'No se pudo guardar las páginas de tu web')
    return false
  }
  const okDesign = await saveDesign(false, true)
  if (okDesign) pushToast('Cambios guardados ✓')
  else pushToast(store.lastError || 'No se pudo guardar el diseño')
  return okDesign
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
function removeService(s) {
  askConfirm({
    title: `Eliminar «${s.name || s.title || 'el servicio'}»`,
    desc: 'El servicio se borra de tu web. No se puede deshacer.',
    action: () => services.removeService(s.id).then(() => {
      if (serviceEditing.value?.id === s.id) resetServiceForm()
    })
  })
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
  if (s === 'reviews' && canProductComments.value) {
    if (!reviewsLoaded.value) { reviewsLoaded.value = true; catalog.loadReviews() }
    //Abrir la sección marca las opiniones como vistas (badge del menú).
    if (unreadReviewsCount.value) {
      unreadReviewsCount.value = 0
      markReviewsSeen().then((d) => { unreadReviewsCount.value = d?.unread_reviews || 0 }).catch(() => {})
    }
  }
  if (s === 'changelog' && !changelogLoaded.value) {
    changelogLoaded.value = true
    fetchChangelog().then((rows) => {
      rows = Array.isArray(rows) ? rows : []
      changelogEntries.value = rows.filter(r => r.kind !== 'roadmap')
      roadmapItems.value = rows.filter(r => r.kind === 'roadmap').sort((a, b) => a.position - b.position)
    }).catch(() => {})
  }
}, { immediate: true })
async function goToReviewProduct(r) {
  await ensureCatalog()
  section.value = 'catalogs'
  const p = catalog.products.find((x) => x.id === r.product)
  if (p) editProduct(p)
}
function onDeleteReview(r) {
  if (reviewDeleting.value === r.id) return
  askConfirm({
    title: 'Eliminar la opinión',
    desc: `Se borra la reseña de ${r.name || 'este cliente'} y deja de verse en tu web.`,
    action: async () => {
      reviewDeleting.value = r.id
      await catalog.removeReview(r.id)
      reviewDeleting.value = null
    }
  })
}
// Respuesta del dueño a una opinión: se publica bajo la opinión en la
// ficha del producto (PATCH /api/reviews/<pk>/reply/ — función exclusiva
// del comercio; el visitante nunca puede responder).
const reviewReplying = ref(null)
const reviewReplyText = ref('')
const reviewReplyBusy = ref(false)
function startReviewReply(r) {
  reviewReplying.value = r.id
  reviewReplyText.value = r.owner_reply || ''
}
function cancelReviewReply() {
  reviewReplying.value = null
  reviewReplyText.value = ''
}
async function saveReviewReply(r) {
  if (reviewReplyBusy.value) return
  reviewReplyBusy.value = true
  const ok = await catalog.replyReview(r.id, reviewReplyText.value.trim())
  reviewReplyBusy.value = false
  if (ok) cancelReviewReply()
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

async function onCarouselPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !canCustomize.value) return
  carouselErr.value = validateImageFile(file)
  if (carouselErr.value) return
  carouselBusy.value = true
  const ok = await store.addCarouselImage(file)
  carouselBusy.value = false
  if (!ok) carouselErr.value = store.fieldErrors.image || store.fieldErrors.detail || store.lastError
}

async function onRemoveCarousel(imageId) {
  if (carouselBusy.value || !canCustomize.value) return
  carouselErr.value = ''
  carouselBusy.value = true
  const ok = await store.removeCarouselImage(imageId)
  carouselBusy.value = false
  if (!ok) carouselErr.value = store.lastError
}

async function onMoveCarousel(imageId, direction) {
  if (carouselBusy.value || !canCustomize.value) return
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
  if (!file || !canCustomize.value) return
  coverErr.value = validateImageFile(file)
  if (coverErr.value) return
  coverBusy.value = true
  const ok = await store.uploadCover(file)
  coverBusy.value = false
  if (!ok) coverErr.value = store.fieldErrors.cover || store.fieldErrors.detail || store.lastError
}

async function onRemoveCover() {
  if (coverBusy.value || !canCustomize.value) return
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
  // /user/me/ + /profile/me/ ya los resolvió el guard del router al entrar
  // (y initSession al boot): refetchear en cada montaje duplicaba el par de
  // requests por navegación. Solo se repide si el perfil nunca cargó; los
  // refrescos puntuales (guardar cuenta, Recargar, verificación de email —
  // que llega por reload completo) ya llaman fetchMe por su cuenta.
  if (auth.user) fillAccountForm()
  else auth.fetchMe().then(() => fillAccountForm())
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
    // El paso "Activá el asistente" del checklist necesita el flag del bot.
    if (canChatbot.value && store.hasStore && !botLoaded.value) { botLoaded.value = true; store.loadChatbot() }
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
  // Deep link por path (/dashboard/diseno, /dashboard/productos, etc.):
  // mismo efecto que ?s= — espera a que plan/tienda resuelvan para que
  // validIds ya incluya las pestañas habilitadas por el plan.
  const slugSection = sectionForSlug(route.params.section)
  if (slugSection) section.value = slugSection
  // Deep link ?s=<seccion> (mails de estado de cuenta, etc.): abre la
  // sección directo si es válida para el plan del usuario.
  const deepSection = route.query.s
  if (deepSection && validIds.value.has(String(deepSection))) {
    //Por el setter (no sectionInner) para que una sección bloqueada abra
    //la preview del beneficio en vez de mostrar el contenido crudo.
    section.value = String(deepSection)
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
  // Asistencia IA: el modal del opt-out sale una sola vez por cuenta. Si la
  // guía está abierta espera a que cierre (watch de tourOpen más abajo).
  if (auth.user?.profile?.ai_assist_prompted === false) {
    aiOptInPending.value = true
    setTimeout(() => {
      if (!tourOpen.value) { aiOptInPending.value = false; aiOptInOpen.value = true }
    }, 1400)
  }
})

// La guía tapa el opt-in: cuando cierra, entra la consulta de IA.
watch(tourOpen, (v) => {
  if (!v && aiOptInPending.value) { aiOptInPending.value = false; aiOptInOpen.value = true }
})

watch(() => carouselImages.value.length, (total) => {
  previewSlide.value = 0
  clearInterval(previewTimer)
  previewTimer = null
  if (total > 1 && !previewReduceMotion) {
    previewTimer = setInterval(() => { previewSlide.value = (previewSlide.value + 1) % carouselImages.value.length }, 3000)
  }
})

// --- Notificaciones del sistema (avisos, NO chat): el click marca leído y
// navega a la sección destino (`target`); nunca abre la conversación ---
const notifs = ref([])
const notifsUnread = ref(0)
//Timestamp del último "visto" de opiniones: las creadas después se
//marcan "Sin leer" en la lista (null = nunca se abrió la sección).
const reviewsSeenAt = ref(null)
const notifsOpen = ref(false)
const changelogEntries = ref([])
const changelogLoaded = ref(false)
// Detalle de una novedad (changelog publicado o item del roadmap) en modal.
const newsModal = ref(null)
// Items de "Próximamente": vienen del backend (kind='roadmap').
const roadmapItems = ref([])

const NOTIF_ICONS = { review: 'star', admin_message: 'message-circle', subscription: 'credit-card', changelog: 'sparkles', system: 'info' }
const notifIcon = (kind) => NOTIF_ICONS[kind] || 'info'

async function loadNotifications() {
  try {
    const data = await fetchNotifications()
    notifs.value = data.notifications || []
    notifsUnread.value = data.unread || 0
    unreadReviewsCount.value = data.unread_reviews || 0
    reviewsSeenAt.value = data.reviews_seen_at || null
  } catch { /* silencioso: reintenta el próximo tick */ }
}

//Opinión creada después del último visto del dueño (o todas si nunca
//abrió la sección — reviews_seen_at null).
function isReviewUnread(r) {
  if (!reviewsSeenAt.value) return true
  const seen = new Date(reviewsSeenAt.value).getTime()
  const created = new Date(r.created_at).getTime()
  return Number.isFinite(created) && created > seen
}

function toggleNotifs() {
  notifsOpen.value = !notifsOpen.value
  if (notifsOpen.value) loadNotifications()
}

//Cierre por click afuera (sin backdrop fijo: el topbar usa backdrop-filter
//y este atraparía un position:fixed dentro del header).
function onDocClick(e) {
  if (notifsOpen.value && !e.target.closest?.('.notif-wrap')) notifsOpen.value = false
}

async function onNotifClick(n) {
  notifsOpen.value = false
  if (!n.read_at) {
    n.read_at = new Date().toISOString()
    notifsUnread.value = Math.max(0, notifsUnread.value - 1)
    markNotificationRead(n.id).catch(() => {})
  }
  //Solo secciones válidas del dashboard; '' = aviso puramente informativo
  //(ej. mensaje del staff: el click NO abre el chat).
  if (n.target && validIds.value.has(n.target)) section.value = n.target
}

async function markAllNotifsRead() {
  const fresh = notifs.value.filter((n) => !n.read_at)
  if (!fresh.length) return
  fresh.forEach((n) => { n.read_at = new Date().toISOString() })
  notifsUnread.value = 0
  markNotificationRead().catch(() => loadNotifications())
}

// Poll propio (~60s): las notificaciones también llegan a cuentas trial,
// que no tienen chat habilitado (el heartbeat de chat ni siquiera corre).
const NOTIF_POLL_MS = 60000
let notifTimer = null
function startNotifs() {
  stopNotifs()
  loadNotifications()
  notifTimer = setInterval(loadNotifications, NOTIF_POLL_MS)
}
function stopNotifs() {
  clearInterval(notifTimer)
  notifTimer = null
}

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
const chatTarget = ref(null)
// Adjuntos en cola: [{file, url}] — el url es un objectURL local (vista
// previa optimista); el archivo nunca toca la DB, viaja al bucket/disco.
const chatFiles = ref([])
const chatFileInput = ref(null)
const CHAT_FILES_MAX = 4
const chatOnlineCount = computed(() => chatStaff.value.filter((s) => s.online).length)
// El chat (heartbeat incluido) solo corre con el beneficio del plan; el
// asistente automático queda disponible para cualquier cuenta como contacto.
// Mismo criterio que el backend (chat_enabled): plan VIGENTE y no-trial —
// el trial trae has_support_chat=true en benefits pero el servidor lo
// rechaza con 403 y el heartbeat spamearía en cada carga del panel.
const canChat = computed(() => Boolean(
  plan.value?.isCurrent && !plan.value?.isTrial && plan.value?.benefits?.has_support_chat
))
// El asistente figura como un integrante más del equipo de soporte: es un
// contacto local (respuestas automáticas, nunca toca la API del chat).
const BOT_MEMBER = { id: 'bot', name: 'Tu Asistente', online: true, bot: true }
const chatContacts = computed(() => canChat.value ? [BOT_MEMBER, ...chatStaff.value] : [BOT_MEMBER])
const botMode = computed(() => Boolean(chatTarget.value?.bot))
// Panel de contactos que abre la burbuja flotante.
const chatDockPanel = ref(false)
const chatDockContent = computed(() => (chatOpen.value ? 'win' : chatDockPanel.value ? 'panel' : null))
// Ocultar la burbuja del asistente (persiste en localStorage): vuelve sola
// si entra un mensaje del equipo o si se abre el chat desde Ayuda/campana.
const chatDockHidden = ref(false)
try { chatDockHidden.value = localStorage.getItem('davent:dock-hidden') === '1' } catch { /* storage bloqueado */ }
function hideChatDock() {
  if (chatDockPanel.value) chatDockPanel.value = false
  if (chatOpen.value) closeChat()
  chatDockHidden.value = true
  try { localStorage.setItem('davent:dock-hidden', '1') } catch { /* storage bloqueado */ }
  pushToast('Asistente oculto — reabrilo desde Ayuda o la campana ✓')
}
watch([chatDockContent, chatUnread], () => {
  if (!chatDockHidden.value) return
  if (chatDockContent.value || chatUnread.value > 0) {
    chatDockHidden.value = false
    try { localStorage.removeItem('davent:dock-hidden') } catch { /* storage bloqueado */ }
  }
})
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
    // "Tu Asistente" (bot MCP): hilo propio en el servidor, separado del
    // chat de soporte. El GET trae el historial (+ saludo en el primer
    // acceso); 403 = sin plan pago → se avisa dentro de la ventana.
    resetChatFiles()
    loadAssistant()
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
    if (!data) return // 204 = nada nuevo (el backend lo devuelve pronto)
    // Dedupe por id: un send optimista o un poll encimado ya pudo traer el
    // mensaje — sin el filtro se vería dos veces hasta el próximo refetch.
    const fresh = (data.messages || []).filter((m) => !chatMessages.value.some((x) => x.id === m.id))
    if (fresh.length) {
      chatMessages.value = [...chatMessages.value, ...fresh]
      chatLastId.value = fresh[fresh.length - 1].id
      await nextTick()
      scrollChat()
    }
  } catch (e) {
    // 403 = plan sin chat (bajó a trial/venció con la ventana abierta):
    // mismo corte que el heartbeat para no seguir pollendo un 403.
    if (e?.response?.status === 403) stopChat()
    // El resto reintenta en el próximo tick.
  } finally { chatPolling = false }
}

async function beatChat() {
  try {
    const data = await chatHeartbeat()
    if (!data) return // 204 = sin payload: no hay presencia/unread que actualizar
    chatStaffOnline.value = Boolean(data.staff_online)
    if (data.staff) chatStaff.value = data.staff
    // El no-leído llega por heartbeat (no marca lectura): con la ventana
    // cerrada/minimizada es el contador del badge; abierta queda en 0
    // porque el polling ya marcó todo como leído.
    chatUnread.value = data.unread || 0
  } catch (e) {
    // 403 = el plan ya no habilita el chat (trial, vencido o cambio de plan
    // en caliente): cortar heartbeat y polling — si no, cada tick spamea
    // un POST que el backend rechaza. Si el plan mejora, el watch de
    // canChat vuelve a llamar startChat().
    if (e?.response?.status === 403) stopChat()
  }
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
const botMsgs = ref([])
const botTyping = ref(false)
let botSeq = 0
const BOT_FALLBACK = 'No pude responder eso todavía. Probá preguntarme por tu plan, tu tienda, tus productos, visitas, pagos o facturas.'

function botPush(mine, body) {
  botMsgs.value.push({
    id: `bot-${++botSeq}`, mine, bot: !mine,
    sender_name: mine ? 'Vos' : BOT_MEMBER.name,
    body, created_at: new Date().toISOString()
  })
  nextTick(scrollChat)
}

// Trae el historial de "Tu Asistente" (hilo propio, no el de soporte).
async function loadAssistant() {
  try {
    const data = await fetchAssistant()
    botMsgs.value = (data.messages || []).map((m) => ({ ...m, bot: m.from_bot }))
  } catch (err) {
    if (!botMsgs.value.length) {
      botPush(false, err?.response?.data?.detail || BOT_FALLBACK)
    }
  }
  nextTick(scrollChat)
}

function sendBotChat() {
  const text = chatInput.value.trim()
  if (!text || botTyping.value) return
  chatInput.value = ''
  nextTick(resizeChatInput)
  askAssistant(text.slice(0, 2000))
}

// El asistente puede pedir que el panel ejecute una acción: abrir la
// Asistencia con IA de la sección que corresponde (diseño asistido o
// datos del negocio) en vez de solo mandar al usuario a buscarla.
function runBotAction(action) {
  if (action === 'assist_design' || action === 'assist_business') {
    section.value = action === 'assist_design' ? 'design' : 'company'
    openAssist(action === 'assist_design' ? 'design' : 'business')
  }
}

async function askAssistant(text) {
  botPush(true, text)
  botTyping.value = true
  try {
    const { reply, action } = await sendAssistant(text)
    botTyping.value = false
    if (reply) botPush(false, reply.body)
    else botPush(false, BOT_FALLBACK)
    if (action) runBotAction(action)
  } catch (err) {
    botTyping.value = false
    botPush(false, err?.response?.data?.detail || BOT_FALLBACK)
  }
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
  if (document.visibilityState === 'visible') {
    loadNotifications()
    if (canChat.value) {
      pollChat()
      beatChat()
    }
  }
}

// Sesión expirada (refresh 401): cortar polling y heartbeat — si no, cada
// 45s se reintentaba el heartbeat contra un access muerto (401 en consola).
function onChatSessionExpired() { stopChat() }

onMounted(() => {
  document.addEventListener('visibilitychange', onChatVisible)
  document.addEventListener('click', onDocClick)
  window.addEventListener('davent:session-expired', onChatSessionExpired)
  startNotifs()
})

onUnmounted(() => {
  stopCheckoutWatch()
  stopChat()
  stopNotifs()
  closeChat()
  window.removeEventListener('davent:session-expired', onChatSessionExpired)
  clearInterval(previewTimer)
  window.removeEventListener('storage', onPaymentBroadcast)
  document.removeEventListener('visibilitychange', onChatVisible)
  document.removeEventListener('click', onDocClick)
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
      <!-- Campana de notificaciones del sistema (avisos, NO chat): lista
           las novedades/avisos del panel; el click marca leído y navega a
           la sección destino sin abrir la conversación. -->
      <div class="notif-wrap">
        <button
          type="button"
          class="top-bell"
          :aria-label="notifsOpen ? 'Cerrar notificaciones' : 'Abrir notificaciones'"
          title="Notificaciones"
          :aria-expanded="notifsOpen"
          @click="toggleNotifs"
        >
          <AppIcon name="inbox" :size="19" />
          <span v-if="notifsUnread" class="chat-badge bell-badge">{{ notifsUnread > 99 ? '99+' : notifsUnread }}</span>
        </button>
        <div v-if="notifsOpen" class="notif-panel" role="dialog" aria-label="Notificaciones">
          <header class="notif-head">
            <strong>Notificaciones</strong>
            <button v-if="notifsUnread" type="button" class="notif-readall" @click="markAllNotifsRead">Marcar leídas</button>
          </header>
          <ul class="notif-list">
            <li
              v-for="n in notifs" :key="n.id"
              class="notif-item" :class="{ unread: !n.read_at }"
              @click="onNotifClick(n)"
            >
              <span class="notif-ico"><AppIcon :name="notifIcon(n.kind)" :size="15" /></span>
              <span class="notif-body">
                <strong>{{ n.title }}</strong>
                <span v-if="n.body" class="notif-text">{{ n.body }}</span>
                <small>{{ formatDateTime(n.created_at) }}</small>
              </span>
              <span v-if="!n.read_at" class="notif-dot" aria-hidden="true"></span>
            </li>
            <li v-if="!notifs.length" class="notif-empty">No tenés notificaciones.</li>
          </ul>
        </div>
      </div>
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
      <!-- 1. Héroe: saludo + acciones + mini tarjeta de tu página -->
      <section class="ovh ovh-hero">
        <div class="ovh-hero-main">
          <span v-if="plan" class="ovh-pill">
            <span class="ovh-pill-dot" :class="{ ok: plan.isCurrent, warn: plan.status === 'Pendiente de pago', bad: !plan.isCurrent && plan.status !== 'Pendiente de pago' }" aria-hidden="true"></span>
            {{ plan.name }}<template v-if="plan.isCurrent"> · vigente hasta {{ fmtDate(plan.end) }}</template><template v-else> · {{ plan.status }}</template>
          </span>
          <h1 class="ovh-title">Hola, {{ ownerName }}</h1>
          <p class="ovh-sub">{{ heroSub }}</p>
          <div class="ovh-hero-actions">
            <a v-if="store.hasStore" class="btn btn-auto" :href="publicUrl" target="_blank" rel="noopener"><AppIcon name="external-link" :size="15" /> Ver mi página</a>
            <button v-else type="button" class="btn btn-auto" @click="section = 'store'"><AppIcon name="store" :size="15" /> Reservar mi link</button>
            <button type="button" class="btn ghost btn-auto" :disabled="!store.hasStore" @click="shareWhatsApp"><AppIcon name="whatsapp" :size="15" /> Compartir</button>
          </div>
        </div>
        <div class="ovh-site">
          <template v-if="store.hasStore">
            <a class="ovh-site-cover" :href="publicUrl" target="_blank" rel="noopener" :aria-label="`Abrir ${publicUrl}`">
              <img v-if="currentCover" :src="currentCover" alt="" />
              <span v-else class="ovh-site-cover-empty"><AppIcon name="image" :size="22" /></span>
              <span class="ovh-site-cover-cta"><AppIcon name="external-link" :size="13" /> Abrir</span>
            </a>
            <div class="ovh-site-info">
              <div class="ovh-site-urlrow">
                <span class="ovh-site-url" :title="publicUrl">{{ publicUrl }}</span>
                <button type="button" class="ovh-icon-btn" aria-label="Copiar link" title="Copiar link" @click="copyLink"><AppIcon name="copy" :size="14" /></button>
              </div>
              <dl class="ovh-site-stats">
                <div><dt>{{ visitWeek.now }}</dt><dd>visitas · 7 días</dd></div>
                <div><dt>{{ productStats.visible }}</dt><dd>productos</dd></div>
                <div><dt>{{ reviewStats.total }}</dt><dd>opiniones</dd></div>
              </dl>
              <button type="button" class="ovh-link ovh-site-edit" @click="section = designTarget">Editar diseño <AppIcon name="arrow-right" :size="13" /></button>
            </div>
          </template>
          <div v-else class="ovh-site-empty">
            <span class="ovh-site-empty-icon"><AppIcon name="store" :size="20" /></span>
            <div class="ovh-site-empty-txt">
              <strong>Tu página todavía no existe</strong>
              <small>Reservá tu link público y empezá a vender hoy.</small>
            </div>
            <button type="button" class="btn btn-auto" @click="section = 'store'">Reservar link</button>
          </div>
        </div>
      </section>

      <!-- 2. Alertas: solo lo urgente, en una franja -->
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

      <!-- 3. Números del día: una sola banda con divisores, no cuatro tarjetas -->
      <section class="ovh ovh-metrics" aria-label="Resumen de tu negocio">
        <div class="ovh-metric">
          <span class="ovh-label">Visitas hoy</span>
          <strong class="ovh-num">{{ canStats ? (store.visitStats?.today ?? 0) : '—' }}</strong>
          <small class="ovh-meta" :class="{ up: (todayDelta ?? 0) > 0, down: (todayDelta ?? 0) < 0 }">
            <template v-if="canStats && todayDelta !== null"><AppIcon :name="todayDelta >= 0 ? 'trending-up' : 'trending-down'" :size="12" /> {{ Math.abs(todayDelta) }}% vs ayer</template>
            <template v-else-if="canStats">igual que ayer</template>
            <template v-else><button type="button" class="ovh-link" @click="section = 'plans'">con un plan superior</button></template>
          </small>
        </div>
        <div class="ovh-metric">
          <span class="ovh-label">Productos activos</span>
          <strong class="ovh-num">{{ billing.hasSubscription ? productStats.visible : 0 }}</strong>
          <small class="ovh-meta">{{ productStats.noImage ? `${productStats.noImage} sin foto` : 'todos con foto' }}</small>
        </div>
        <div class="ovh-metric">
          <span class="ovh-label">Opiniones</span>
          <strong class="ovh-num">{{ reviewStats.total }}</strong>
          <small class="ovh-meta">{{ reviewStats.pct !== null ? `${reviewStats.pct}% positivas` : 'todavía sin reseñas' }}</small>
        </div>
        <div class="ovh-metric">
          <span class="ovh-label">Próximo cobro</span>
          <strong class="ovh-num">{{ plan && plan.isCurrent ? formatARS(plan.price) : '—' }}</strong>
          <small class="ovh-meta">{{ plan && plan.isCurrent ? `${fmtDate(plan.end)} · ${plan.name}` : 'sin plan vigente' }}</small>
        </div>
      </section>

      <!-- 3b. Calidad de la web: score + pendientes con acción directa -->
      <WebQualityCard :report="webQualityReport" :loading="webQualityLoading" @navigate="onQualityNavigate" />

      <!-- 4. Fila: gráfico de visitas + checklist de puesta en marcha -->
      <div class="ovh-row">
        <section class="ovh ovh-card">
          <header class="ovh-card-head">
            <h3>Visitas — últimos 14 días</h3>
            <button v-if="canStats" type="button" class="ovh-link" @click="section = 'stats'">Ver estadísticas</button>
          </header>
          <div v-if="visitBars.length" class="ovh-bars" role="img" :aria-label="`Visitas de los últimos ${visitBars.length} días`">
            <div v-for="(b, i) in visitBars" :key="i" class="ovh-bar" :title="`${b.count} ${b.count === 1 ? 'visita' : 'visitas'} · ${fmtDate(b.date)}`">
              <span class="ovh-bar-track"><span class="ovh-bar-fill" :class="{ today: i === visitBars.length - 1 }" :style="{ height: `${b.h}%` }"></span></span>
              <small>{{ b.label }}</small>
            </div>
          </div>
          <p v-else class="ovh-empty">{{ canStats ? 'Todavía no hay visitas registradas.' : 'Las estadísticas de visitas están disponibles en planes superiores.' }}</p>
        </section>

        <section class="ovh ovh-card">
          <header class="ovh-card-head">
            <h3>Puesta en marcha</h3>
            <span class="ovh-count">{{ stepsDone }} de {{ nextSteps.length }}</span>
          </header>
          <div class="ovh-prog" role="progressbar" aria-label="Avance de puesta en marcha" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="stepsPct"><span :style="{ transform: `scaleX(${stepsPct / 100})` }"></span></div>
          <ol v-if="pendingSteps.length" class="ovh-list">
            <li v-for="s in pendingSteps" :key="s.title">
              <span class="ovh-item-icon" aria-hidden="true"><AppIcon :name="s.icon" :size="15" /></span>
              <div class="ovh-item-body"><strong>{{ s.title }}</strong><small>{{ s.text }}</small></div>
              <button type="button" class="ovh-link" @click="s.run ? s.run() : (section = s.target)">{{ s.cta }} <AppIcon name="arrow-right" :size="13" /></button>
            </li>
          </ol>
          <p v-else class="ovh-done"><AppIcon name="circle-check" :size="16" /> Tu tienda está lista para vender.</p>
        </section>
      </div>

      <!-- 5. Fila: actividad reciente + tu página -->
      <div class="ovh-row">
        <section class="ovh ovh-card">
          <header class="ovh-card-head">
            <h3>Actividad reciente</h3>
            <button type="button" class="ovh-link" @click="section = 'stats'">Ver todo</button>
          </header>
          <ol v-if="activityFeed.length" class="ovh-list">
            <li v-for="(a, i) in activityFeed" :key="i">
              <span class="ovh-item-icon" aria-hidden="true"><AppIcon :name="a.icon" :size="15" /></span>
              <div class="ovh-item-body"><strong>{{ a.title }}</strong><small v-if="a.text">{{ a.text }}</small></div>
              <button type="button" class="ovh-link" @click="a.run">{{ a.cta }} <AppIcon name="arrow-right" :size="13" /></button>
            </li>
          </ol>
          <p v-else class="ovh-empty">Todavía no hay novedades.</p>
          <div v-if="store.hasStore" class="ovh-storage"><StorageMeter /></div>
        </section>

        <section class="ovh ovh-card">
          <header class="ovh-card-head">
            <h3>Atajos</h3>
          </header>
          <div class="ovh-quick">
            <button v-for="q in quickLinks" :key="q.id" type="button" class="ovh-quick-item" :class="{ locked: navLocks[q.id] }" @click="section = q.id">
              <span class="ovh-item-icon" aria-hidden="true"><AppIcon :name="q.icon" :size="15" /></span>
              <span class="ovh-quick-txt"><strong>{{ q.label }}</strong><small>{{ q.hint }}</small></span>
              <AppIcon :name="navLocks[q.id] ? 'lock' : 'arrow-right'" :size="13" class="ovh-quick-go" />
            </button>
          </div>
        </section>
      </div>

      <!-- Franja de plan compacta + confirmación de cancelar débito -->
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

      <!-- 6. Ayuda: soporte + guía, siempre visible -->
      <div class="card oh-help">
        <span class="oh-help-icon"><AppIcon name="message-circle" :size="22" /></span>
        <div class="oh-help-txt">
          <strong>¿Necesitás ayuda?</strong>
          <small>Escribinos y te respondemos, o mirá la guía paso a paso.</small>
        </div>
        <div class="oh-help-actions">
          <button type="button" class="btn btn-auto" @click="onBellClick">Hablar con soporte</button>
          <button type="button" class="btn ghost btn-auto" @click="tourOpen = true"><AppIcon name="graduation-cap" :size="16" /> Ver la guía</button>
        </div>
      </div>
    </div>

    <!-- ================= CATÁLOGO ================= -->
    <div v-if="seen.catalogs" v-show="section === 'catalogs'" :class="{ 'sec-on': section === 'catalogs' }">
      <div class="page-head">
        <div>
          <h1>Mis productos</h1>
          <p>Acá cargás lo que vendés: aparece solo en tu página web. {{ billing.hasSubscription ? productsCountText : catalogLimit }}</p>
          <div v-if="billing.hasSubscription && catalog.products.length" class="cat-stats">
            <span class="cat-stat tone-info"><AppIcon name="eye" :size="13" aria-hidden="true" /> {{ productStats.visible }} visibles</span>
            <span class="cat-stat tone-warn"><AppIcon name="percent" :size="13" aria-hidden="true" /> {{ productStats.offers }} en oferta</span>
            <span class="cat-stat tone-ok"><AppIcon name="image" :size="13" aria-hidden="true" /> {{ productStats.noImage }} sin foto</span>
            <span class="cat-stat tone-brand"><AppIcon name="tag" :size="13" aria-hidden="true" /> {{ productStats.discounted }} con descuento</span>
          </div>
        </div>
        <div class="page-head-actions cat-actions">
          <button class="btn ghost btn-auto" @click="catalog.loadAll()"><AppIcon name="refresh" :size="16" /> Recargar</button>
          <button v-if="billing.hasSubscription && !catalog.denied" class="btn btn-auto" @click="focusProductForm"><AppIcon name="plus" :size="16" /> Cargar producto</button>
        </div>
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
        <SectionTabs :tabs="catalogSectionTabs" :active="catalogTab" @select="catalogTab = $event" />

        <div v-if="catalog.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu catálogo…</p></div>

        <template v-else>
          <!-- -------- Productos: inventario a ancho completo; el formulario
               vive en el drawer lateral (Teleport al final del layout). -------- -->
          <div v-show="catalogTab === 'products'">
            <div class="card">
              <StorageMeter />
              <div v-if="!catalog.products.length" class="empty-mini">
                <AppIcon name="package" :size="22" />
                <div><p>Todavía no cargaste productos. El primero tarda un minuto: nombre, precio y una foto.</p><button type="button" class="empty-mini-cta" @click="focusProductForm">Cargar el primero</button></div>
              </div>
              <template v-else>
                <div class="inv-head">
                  <h3><AppIcon name="package" :size="17" /> Inventario <small>· {{ filteredProducts.length }} de {{ catalog.products.length }}</small></h3>
                  <button type="button" class="btn inv-add" @click="focusProductForm"><AppIcon name="plus" :size="15" /> Registrar nuevo producto</button>
                </div>
                <CatalogToolbar
                  v-model:query="productQuery" v-model:category="prodFilterCategory" v-model:brand="prodFilterBrand"
                  v-model:only-offers="prodOnlyOffers" v-model:sort="prodSort"
                  :categories="catalog.categories" :brands="catalog.brands"
                  @prices="showPriceUpdate = true"
                />
                <div v-if="!filteredProducts.length" class="empty-mini">
                  <AppIcon name="search" :size="22" />
                  <div>
                    <p>No hay productos que coincidan con los filtros.</p>
                    <button type="button" class="empty-mini-cta" @click="productQuery = ''; prodFilterCategory = ''; prodFilterBrand = ''; prodOnlyOffers = false">Limpiar filtros</button>
                  </div>
                </div>
                <template v-else>
                  <div v-if="selectedIds.length" class="prod-bulkbar">
                    <AppIcon name="check" :size="15" />
                    <span>{{ selectedIds.length }} seleccionado{{ selectedIds.length === 1 ? '' : 's' }}</span>
                    <button type="button" @click="bulkDuplicate" :disabled="bulkBusy">Duplicar</button>
                    <button type="button" @click="bulkSetActive(true)" :disabled="bulkBusy">Mostrar</button>
                    <button type="button" @click="bulkSetActive(false)" :disabled="bulkBusy">Ocultar</button>
                    <button type="button" class="danger" @click="bulkRemove" :disabled="bulkBusy">Eliminar</button>
                    <span class="prod-bulkbar-hint">Seleccioná con la casilla de cada fila</span>
                    <button type="button" class="prod-bulkbar-x" aria-label="Limpiar selección" @click="selectedIds = []"><AppIcon name="x" :size="14" /></button>
                  </div>
                  <ProductTable
                    :products="pagedProducts" v-model:selected-ids="selectedIds"
                    :campaign-of="(id) => productCampaign.get(id) || null"
                    :stock-enabled="hasStockControl"
                    @edit="editProduct" @duplicate="duplicateProduct"
                    @toggle-active="toggleProductActive" @remove="removeProduct"
                  />
                  <div v-if="prodPageInfo.pages > 1" class="prod-pager">
                    <span>Mostrando {{ prodPageInfo.from }}–{{ prodPageInfo.to }} de {{ prodPageInfo.total }}</span>
                    <span class="prod-pager-btns">
                      <button type="button" class="btn ghost btn-auto" :disabled="prodPage <= 1" @click="prodPage--">← Anterior</button>
                      <button type="button" class="btn ghost btn-auto" :disabled="prodPage >= prodPageInfo.pages" @click="prodPage++">Siguiente →</button>
                    </span>
                  </div>
                </template>
              </template>
            </div>
          </div>

          <!-- -------- Categorías -------- -->
          <div v-show="catalogTab === 'categories'" class="card">
            <div class="inv-head">
              <h3><AppIcon name="layout-grid" :size="17" /> Categorías <small>· {{ catalog.categories.length }}</small></h3>
              <small class="inv-head-note">Agrupan tus productos en el menú de tu página</small>
            </div>
            <div class="tax-add">
              <div class="tax-fields">
                <AppInput v-model="taxonomyForm.category" :label="taxonomyEditing ? 'Editar categoría' : 'Nueva categoría'" name="cat_name" placeholder="Ej. Indumentaria" :error="taxonomyErr.category" />
                <div class="field">
                  <label for="cat_feature">Características <small class="tab-sub">(opcional)</small></label>
                  <div class="feat-add">
                    <input
                      id="cat_feature" v-model="taxonomyFeatureInput" class="input" type="text"
                      placeholder="Ej. Talle" @keydown.enter.prevent="addTaxonomyFeature"
                    />
                    <button type="button" class="btn ghost btn-auto" :disabled="!taxonomyFeatureInput.trim()" @click="addTaxonomyFeature"><AppIcon name="plus" :size="14" /> Agregar</button>
                  </div>
                  <div v-if="taxonomyFeatures.length" class="feat-chips">
                    <span v-for="(f, i) in taxonomyFeatures" :key="f" class="feat-chip">
                      {{ f }}
                      <button type="button" :aria-label="`Quitar ${f}`" @click="taxonomyFeatures.splice(i, 1)"><AppIcon name="x" :size="11" /></button>
                    </span>
                  </div>
                  <p class="hint">Se sugieren al cargar productos de esta categoría.</p>
                </div>
                <div class="tax-actions">
                  <button v-if="taxonomyEditing" type="button" class="btn ghost btn-auto" @click="cancelCategoryEdit">Cancelar</button>
                  <AppButton :loading="taxonomyBusy.category" class="btn-auto" @click="addTaxonomy('category')">{{ taxonomyEditing ? 'Guardar' : 'Agregar categoría' }}</AppButton>
                </div>
              </div>
            </div>
            <ul v-if="catalog.categories.length" class="tax-list">
              <li v-for="c in catalog.categories" :key="c.id">
                <span class="tax-dot" :style="{ '--h': taxonomyHue(c.name) }" aria-hidden="true"></span>
                <span class="tax-name">
                  <strong>{{ c.name }}</strong>
                  <small>{{ c.products_count || 0 }} productos<template v-if="c.feature_schema?.length"> · {{ c.feature_schema.join(' · ') }}</template></small>
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
            <div class="inv-head">
              <h3><AppIcon name="tag" :size="17" /> Marcas <small>· {{ catalog.brands.length }}</small></h3>
              <small class="inv-head-note">Filtran tus productos por marca en el menú de tu página</small>
            </div>
            <div class="tax-add">
              <div class="tax-fields">
                <AppInput v-model="taxonomyForm.brand" :label="brandEditing ? 'Editar marca' : 'Nueva marca'" name="brand_name" placeholder="Ej. Nike" :error="taxonomyErr.brand" />
                <div class="field">
                  <label>Logo <small class="tab-sub">(opcional)</small></label>
                  <div class="brand-logo-pick">
                    <span class="brand-logo-thumb">
                      <img v-if="brandFormPreview" :src="brandFormPreview" alt="Logo de la marca" />
                      <AppIcon v-else name="image" :size="18" />
                    </span>
                    <span class="brand-logo-meta">
                      <strong>{{ brandFormImage ? brandFormImage.name : (brandEditing ? 'Logo actual' : 'Sin imagen') }}</strong>
                      <small>PNG, JPG, WebP o GIF de hasta 2 MB</small>
                    </span>
                    <button type="button" class="btn ghost btn-auto" @click="brandFormImageInput?.click()">
                      <AppIcon name="upload" :size="14" /> {{ brandFormImage || brandFormPreview ? 'Cambiar' : 'Elegir' }}
                    </button>
                    <button v-if="brandFormImage" type="button" class="icon-btn danger" aria-label="Quitar imagen" @click="clearBrandFormImage"><AppIcon name="x" :size="15" /></button>
                  </div>
                  <input ref="brandFormImageInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Logo de la marca" @change="onBrandFormImagePicked" />
                  <p v-if="brandFormErr" class="field-error" role="alert">{{ brandFormErr }}</p>
                </div>
                <div class="tax-actions">
                  <button v-if="brandEditing" type="button" class="btn ghost btn-auto" @click="cancelBrandEdit">Cancelar</button>
                  <AppButton :loading="taxonomyBusy.brand" class="btn-auto" @click="addTaxonomy('brand')">{{ brandEditing ? 'Guardar' : 'Agregar marca' }}</AppButton>
                </div>
              </div>
            </div>
            <p class="hint">Logo opcional por marca: PNG, JPG, WebP o GIF de hasta 2 MB. Se convierte a WebP con fondo transparente.</p>
            <div v-if="catalog.brands.length" class="brand-search">
              <AppIcon name="search" :size="15" />
              <input v-model="brandQuery" class="input" type="search" placeholder="Buscar marca…" aria-label="Buscar marca" />
            </div>
            <ul v-if="filteredBrands.length" class="tax-list">
              <li v-for="b in filteredBrands" :key="b.id">
                <img v-if="b.image" class="tax-thumb" :src="b.image" :alt="`Logo de ${b.name}`" loading="lazy" decoding="async" />
                <span v-else class="tax-dot" :style="{ '--h': taxonomyHue(b.name) }" aria-hidden="true"></span>
                <span class="tax-name">
                  <strong>{{ b.name }}</strong>
                  <small>{{ b.products_count || 0 }} productos</small>
                </span>
                <span class="tax-item-actions">
                  <button type="button" class="icon-btn" aria-label="Editar marca" @click="editBrand(b)"><AppIcon name="pencil" :size="15" /></button>
                  <button type="button" class="icon-btn" :disabled="brandImageBusy === b.id" :aria-label="b.image ? `Cambiar imagen de ${b.name}` : `Subir imagen de ${b.name}`" @click="pickBrandImage(b)"><AppIcon name="image" :size="15" /></button>
                  <button v-if="b.image" type="button" class="icon-btn danger" :disabled="brandImageBusy === b.id" :aria-label="`Quitar imagen de ${b.name}`" @click="removeBrandImage(b)"><AppIcon name="x" :size="15" /></button>
                  <button type="button" class="icon-btn danger" aria-label="Eliminar marca" @click="removeTaxonomy('brand', b)"><AppIcon name="trash" :size="15" /></button>
                </span>
              </li>
            </ul>
            <input ref="brandImageInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Subir imagen de marca" @change="onBrandImagePicked" />
            <p v-if="brandImageErr" class="field-error" role="alert">{{ brandImageErr }}</p>
            <p v-if="!catalog.brands.length" class="hint">Sin marcas todavía.</p>
            <p v-else-if="!filteredBrands.length" class="hint">
              Ninguna marca coincide con «{{ brandQuery.trim() }}».
              <button type="button" class="empty-mini-cta" @click="brandQuery = ''">Limpiar búsqueda</button>
            </p>
          </div>

          <!-- -------- Descuentos programados (premium) -------- -->
          <div v-show="catalogTab === 'discounts'">
          <div v-if="!canDiscounts" class="empty">
            <span class="empty-icon"><AppIcon name="percent" :size="28" /></span>
            <h3>Los descuentos programados son Premium</h3>
            <p>Con el Plan premium creás ofertas que se activan y se apagan solas en las fechas que elijas, sin tocar los precios a mano.</p>
            <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
          </div>
          <div v-else class="disc-wrap">
          <!-- Aviso de evento próximo: solo aparece cuando una campaña entró
               en su ventana de configuración y no tiene descuento armado. -->
          <div v-for="c in upcomingCampaigns" :key="c.id" class="disc-alert">
            <span class="disc-alert-ico" :style="c.accent ? { background: c.accent } : null"><AppIcon name="percent" :size="16" /></span>
            <div class="disc-alert-txt">
              <strong>Se acerca {{ c.name }} <span class="disc-alert-when">· {{ campaignWindowLabel(c) }}</span></strong>
              <small>Programá un descuento ahora: se enciende y se apaga solo durante el evento.</small>
            </div>
            <button type="button" class="btn btn-auto disc-alert-cta" @click="newCampaignDiscount(c)">Programar oferta</button>
          </div>
          <!-- El formulario vive en un drawer como el de productos: la lista
               queda limpia y sin competir con los pasos del alta. -->
          <Teleport to="body">
            <Transition name="pf">
              <div v-if="discountFormOpen" class="pf-overlay" @click.self="closeDiscountForm">
                <div class="pf-drawer" role="dialog" aria-modal="true" :aria-label="discountEditing ? 'Editar descuento' : 'Nuevo descuento'">
                  <header class="pf-drawer-head">
                    <div class="pf-drawer-title">
                      <span class="pf-drawer-ico"><AppIcon :name="discountEditing ? 'pencil' : 'percent'" :size="17" /></span>
                      <h3>{{ discountEditing ? 'Editar descuento' : 'Nuevo descuento' }}</h3>
                    </div>
                    <button type="button" class="icon-btn" aria-label="Cerrar" @click="closeDiscountForm"><AppIcon name="x" :size="16" /></button>
                  </header>
                  <div class="pf-drawer-body">
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

              <div class="form-step"><span class="form-step-num">1</span> ¿A qué aplica?</div>
              <div class="field">
                <label id="disc-scope-label" for="disc-scope"><AppIcon name="layout-grid" :size="14" class="label-icon" aria-hidden="true" />Alcance</label>
                <select id="disc-scope" v-model="discountForm.scope" class="select">
                  <option v-for="s in DISCOUNT_SCOPES" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
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

              <div class="form-step"><span class="form-step-num">2</span> ¿Cuánto descuenta?</div>
              <div class="field">
                <label for="disc-percent" class="sr-only"><AppIcon name="percent" :size="14" class="label-icon" aria-hidden="true" />Descuento</label>
                <div class="disc-pct-row">
                  <input id="disc-percent" v-model="discountForm.percent" type="number" min="1" max="99" step="1" class="input disc-pct-input" :class="{ invalid: discountFieldErr('percent') }" placeholder="25" aria-label="Porcentaje de descuento" @blur="discountTouched.percent = true" />
                  <span class="disc-pct-sign" aria-hidden="true">%</span>
                  <input v-model="discountForm.percent" type="range" min="1" max="99" step="1" class="disc-pct-slider" aria-label="Descuento en porcentaje" />
                </div>
                <p v-if="discountFieldErr('percent')" class="field-error" role="alert">{{ discountFieldErr('percent') }}</p>
              </div>

              <div class="form-step"><span class="form-step-num">3</span> ¿Cuándo aplica?</div>
              <div class="field">
                <label id="disc-window-label" for="disc-when"><AppIcon name="calendar" :size="14" class="label-icon" aria-hidden="true" />Vigencia</label>
                <select id="disc-when" v-model="discountWhen" class="select" :disabled="!!selectedCampaign">
                  <option value="none">Sin fin — queda activo siempre</option>
                  <option value="today">Solo hoy</option>
                  <option value="week">Esta semana</option>
                  <option value="fortnight">Próximos 15 días</option>
                  <option value="month">Hasta fin de mes</option>
                  <option value="custom">Otras fechas…</option>
                  <optgroup v-if="campaignOptions.length" label="Eventos especiales">
                    <option v-for="c in campaignOptions" :key="c.id" :value="`camp:${c.id}`">{{ c.name }} · {{ campaignWindowLabel(c) }}</option>
                  </optgroup>
                </select>
                <div v-if="selectedCampaign" class="disc-event-lock">
                  <AppIcon name="lock" :size="14" aria-hidden="true" />
                  <span><strong>{{ selectedCampaign.name }}</strong> · {{ campaignWindowLabel(selectedCampaign) }}<small>Fechas fijas del evento: se enciende y se apaga solo.</small></span>
                  <button type="button" class="disc-event-unlock" title="Usar otra vigencia" @click="discountForm.campaign = ''; discountWindowPreset = 'none'"><AppIcon name="x" :size="13" /></button>
                </div>
                <div v-if="discountWindowPreset === 'custom'" class="disc-window">
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

              <details v-if="selectedCampaign" class="disc-adv">
                <summary>Sobre el evento</summary>
                <p class="hint">Las fechas de <strong>{{ selectedCampaign.name }}</strong> son fijas y no se pueden editar. Para usar fechas propias, elegí otra vigencia arriba.</p>
              </details>

              <div class="check-list">
                <label class="check-item">
                  <input type="checkbox" v-model="discountForm.is_active" />
                  <span class="check-text"><strong><AppIcon name="zap" :size="14" class="label-icon" aria-hidden="true" /> Descuento activo</strong><small>Si lo pausás, deja de aplicarse aunque esté en fecha.</small></span>
                </label>
              </div>
              <div class="btn-row">
                <AppButton :loading="discountBusy" @click="saveDiscount"><AppIcon name="check" :size="16" /> {{ discountEditing ? 'Guardar cambios' : 'Crear descuento' }}</AppButton>
                <button type="button" class="btn ghost btn-auto" @click="closeDiscountForm">Cancelar</button>
              </div>
                  </div>
                </div>
              </div>
            </Transition>
          </Teleport>

            <div class="card disc-card">
              <div class="inv-head">
                <h3><AppIcon name="percent" :size="17" /> Descuentos <small>· {{ catalog.discounts.length }}</small></h3>
                <button type="button" class="btn btn-auto" @click="newDiscount"><AppIcon name="plus" :size="15" /> Nuevo descuento</button>
              </div>
              <div v-if="!catalog.discounts.length" class="disc-empty">
                <span class="disc-empty-icon"><AppIcon name="percent" :size="22" /></span>
                <strong>Todavía no programaste descuentos</strong>
                <p>Creá una oferta y se enciende y se apaga sola en las fechas que elijas.</p>
                <ul class="disc-empty-tips">
                  <li><AppIcon name="zap" :size="13" /> Se activa sola</li>
                  <li><AppIcon name="clock" :size="13" /> Se apaga sola</li>
                  <li><AppIcon name="eye" :size="13" /> Se ve en tu web</li>
                </ul>
              </div>
              <div v-else class="disc-cards">
                <DiscountCard
                  v-for="d in catalog.discounts" :key="d.id" :d="d" :busy="discountBusy"
                  @toggle="toggleDiscount" @edit="editDiscount" @remove="removeDiscount"
                />
              </div>
            </div>
          </div>
          </div>

        </template>
      </template>
    </div>
    <!-- ================= MIS SERVICIOS ================= -->
    <div v-if="seen.services" v-show="section === 'services'" class="sec-serv" :class="{ 'sec-on': section === 'services' }">
      <div class="page-head">
        <div>
          <h1>Mis servicios</h1>
          <p>Mostrá lo que hacés, con precio y duración, en tu página. El cliente arma su presupuesto y el pedido te llega por WhatsApp; nada se cobra online.</p>
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
        <div v-if="!designSiteTemplates.includes('services')" class="card svc-note" role="note">
          <span class="svc-note-ico" aria-hidden="true"><AppIcon name="eye-off" :size="18" /></span>
          <div class="svc-note-body">
            <h3>Tu página de servicios está apagada</h3>
            <p class="hint">Los clientes no la ven en tu web. Tus servicios quedan guardados: activá la página en <a href="#" @click.prevent="section = 'pages'"><strong>Plantillas</strong></a> cuando quieras mostrarla.</p>
          </div>
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
          <div class="grid-2 svc-grid">
            <div class="card svc-form">
              <header class="svc-form-head">
                <h3><AppIcon :name="serviceEditing ? 'pencil' : 'plus'" :size="18" /> {{ serviceEditing ? 'Editar servicio' : 'Agregar un servicio' }}</h3>
                <p class="hint">Completá los campos: arriba ves una vista previa de cómo queda en tu web.</p>
              </header>
              <div class="svc-preview" :style="{ '--h': serviceHue(serviceForm.icon) }" aria-hidden="true">
                <span class="svc-ico"><AppIcon :name="serviceIcon(serviceForm.icon)" :size="22" /></span>
                <div>
                  <strong>{{ serviceForm.name || 'Nombre del servicio' }}</strong>
                  <small>{{ servicePriceLabel(serviceForm) }}<template v-if="serviceForm.duration"> · {{ serviceForm.duration }}</template></small>
                </div>
              </div>
              <div class="svc-group">
                <span class="svc-group-label">Qué ofrecés</span>
                <AppInput v-model="serviceForm.name" label="Nombre" icon="pencil" name="svc_name" placeholder="Ej. Reparación a domicilio" :error="serviceFieldErr('name')" @blur="serviceTouched.name = true" />
                <div class="field">
                  <label for="svc-description"><AppIcon name="message-circle" :size="14" class="label-icon" aria-hidden="true" />Descripción corta <span class="svc-opt">opcional</span></label>
                  <textarea id="svc-description" v-model="serviceForm.description" class="textarea" :class="{ invalid: serviceFieldErr('description') }" placeholder="Qué incluye o cómo se coordina" :maxlength="serviceLimits.description" rows="2" @blur="serviceTouched.description = true"></textarea>
                  <p class="hint">{{ serviceForm.description.length }}/{{ serviceLimits.description }}</p>
                  <p v-if="serviceFieldErr('description')" class="field-error" role="alert">{{ serviceFieldErr('description') }}</p>
                </div>
              </div>
              <div class="svc-group">
                <span class="svc-group-label">Precio y duración</span>
                <div class="grid-2">
                  <AppInput v-model="serviceForm.price" label="Precio orientativo" icon="tag" name="svc_price" type="number" min="0" step="0.01" placeholder="Vacío = a convenir" :error="serviceFieldErr('price')" @blur="serviceTouched.price = true" />
                  <AppInput v-model="serviceForm.duration" label="Duración estimada" icon="clock" name="svc_duration" placeholder="Ej. ≈ 45 min" :error="serviceFieldErr('duration')" @blur="serviceTouched.duration = true" />
                </div>
                <p class="hint">Si dejás el precio vacío, en tu web se muestra como «a convenir».</p>
              </div>
              <div class="svc-group">
                <span class="svc-group-label">Cómo se ve en tu web</span>
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
              </div>
              <div class="btn-row">
                <AppButton :loading="serviceBusy" :disabled="!serviceEditing && services.limitReached" @click="saveService">{{ serviceEditing ? 'Guardar cambios' : 'Publicar servicio' }}</AppButton>
                <button v-if="serviceEditing" type="button" class="btn ghost btn-auto" @click="resetServiceForm">Cancelar</button>
              </div>
              <p v-if="services.limitReached" class="hint">Llegaste al máximo de {{ serviceLimits.max }} servicios por página.</p>
            </div>

            <div class="card svc-list-card">
              <header class="svc-list-head">
                <h3><AppIcon name="wrench" :size="18" /> Tus servicios</h3>
                <p class="hint">Aparecen en tu web en este orden.</p>
              </header>
              <div v-if="!services.items.length" class="empty-mini svc-empty">
                <span class="svc-empty-ico" aria-hidden="true"><AppIcon name="wrench" :size="26" /></span>
                <h4>Empezá tu carta de servicios</h4>
                <ul class="svc-empty-points">
                  <li><AppIcon name="check" :size="14" aria-hidden="true" /> Mostrá qué hacés, con precio y duración</li>
                  <li><AppIcon name="check" :size="14" aria-hidden="true" /> El cliente arma su presupuesto solo</li>
                  <li><AppIcon name="check" :size="14" aria-hidden="true" /> El pedido te llega por WhatsApp</li>
                </ul>
                <button type="button" class="empty-mini-cta svc-empty-cta" @click="focusField('svc_name')"><AppIcon name="plus" :size="15" aria-hidden="true" /> Agregar mi primer servicio</button>
              </div>
              <ul v-else class="svc-list">
                <li v-for="(s, i) in services.items" :key="s.id" class="svc-card" :class="{ off: !s.is_active, editing: serviceEditing?.id === s.id }" :style="{ '--h': serviceHue(s.icon) }">
                  <span class="svc-ico"><AppIcon :name="serviceIcon(s.icon)" :size="22" aria-hidden="true" /></span>
                  <div class="svc-body">
                    <div class="svc-title">
                      <span class="svc-num">{{ String(i + 1).padStart(2, '0') }}</span>
                      <strong>{{ s.name }}</strong>
                    </div>
                    <div class="svc-meta">
                      <span><AppIcon name="tag" :size="13" aria-hidden="true" /> {{ servicePriceLabel(s) }}</span>
                      <span v-if="s.duration"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ s.duration }}</span>
                    </div>
                    <p v-if="s.description" class="svc-desc">{{ s.description }}</p>
                  </div>
                  <div class="svc-side">
                    <button type="button" class="svc-vis" :class="{ on: s.is_active }" role="switch" :aria-checked="s.is_active" :aria-label="s.is_active ? 'Ocultar servicio' : 'Mostrar servicio'" :title="s.is_active ? 'Ocultarlo en tu web' : 'Mostrarlo en tu web'" @click="services.toggleService(s)">
                      <span class="svc-vis-track" aria-hidden="true"><i></i></span>
                      <span class="svc-vis-text">{{ s.is_active ? 'Visible' : 'Oculto' }}</span>
                    </button>
                    <div class="svc-actions">
                      <button type="button" class="icon-btn" aria-label="Subir" :disabled="i === 0" @click="moveService(s, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                      <button type="button" class="icon-btn" aria-label="Bajar" :disabled="i === services.items.length - 1" @click="moveService(s, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                      <button type="button" class="icon-btn" aria-label="Editar servicio" title="Editar" @click="editService(s)"><AppIcon name="pencil" :size="15" /></button>
                      <button type="button" class="icon-btn danger" aria-label="Eliminar servicio" title="Eliminar" @click="removeService(s)"><AppIcon name="trash" :size="15" /></button>
                    </div>
                  </div>
                </li>
              </ul>
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
    <div v-if="seen.reviews" v-show="section === 'reviews'" class="sec-rev" :class="{ 'sec-on': section === 'reviews' }">
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
            <li v-for="r in catalog.reviews" :key="r.id" class="rev-item" :class="{ 'rev-unread': isReviewUnread(r) }">
              <div class="rev-head">
                <span v-if="r.is_positive != null" class="rev-vote" :class="{ down: !r.is_positive }" :title="r.is_positive ? 'Le gustó' : 'No le gustó'">
                  <AppIcon :name="r.is_positive ? 'thumbs-up' : 'thumbs-down'" :size="14" />
                </span>
                <strong>{{ r.name }} {{ r.surname }}</strong>
                <span v-if="isReviewUnread(r)" class="rev-new">Sin leer</span>
                <span class="rev-mail">{{ r.email }}</span>
                <span class="rev-date">{{ fmtDate(r.created_at) }}</span>
              </div>
              <span class="rev-prod"><AppIcon name="package" :size="12" /> Sobre
                <button type="button" class="rev-prod-link" @click="goToReviewProduct(r)">{{ r.product_name }}</button>
              </span>
              <p v-if="r.text" class="rev-text">{{ r.text }}</p>
              <div v-if="r.owner_reply && reviewReplying !== r.id" class="rev-reply">
                <strong><AppIcon name="store" :size="12" /> Tu respuesta</strong>
                <p>{{ r.owner_reply }}</p>
              </div>
              <div v-if="reviewReplying === r.id" class="rev-reply-form">
                <label :for="`rev-reply-${r.id}`">Tu respuesta <small>se muestra en la web, bajo la opinión</small></label>
                <textarea
                  :id="`rev-reply-${r.id}`" v-model="reviewReplyText" class="textarea" rows="3"
                  maxlength="600" placeholder="Gracias por tu opinión. Si tenés alguna duda, escribinos."
                ></textarea>
                <div class="rev-reply-actions">
                  <button type="button" class="btn ghost" :disabled="reviewReplyBusy" @click="cancelReviewReply">Cancelar</button>
                  <button type="button" class="btn btn-auto" :disabled="reviewReplyBusy" @click="saveReviewReply(r)">
                    <span v-if="reviewReplyBusy" class="spinner spinner-brand" aria-hidden="true"></span>
                    {{ reviewReplyText.trim() ? 'Guardar respuesta' : 'Quitar respuesta' }}
                  </button>
                </div>
              </div>
              <div class="rev-foot">
                <button
                  type="button" class="icon-btn" :disabled="reviewReplyBusy"
                  :aria-label="r.owner_reply ? `Editar tu respuesta a ${r.name}` : `Responder la opinión de ${r.name}`"
                  :title="r.owner_reply ? 'Editar respuesta' : 'Responder'" @click="startReviewReply(r)"
                >
                  <AppIcon name="message-circle" :size="15" />
                </button>
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
    <!-- ================= MI PÁGINA (índice de apartados) ================= -->
    <div v-if="seen.web" v-show="section === 'web'" class="web-scope" :class="{ 'sec-on': section === 'web' }">
      <div class="page-head">
        <div>
          <h1>Mi página</h1>
          <p>Lo que ven tus clientes en internet. Elegí un apartado para empezar.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.web" :active="''" @select="section = $event" />
      <div v-if="store.hasStore" class="web-live">
        <span class="web-live-icon"><AppIcon name="external-link" :size="20" /></span>
        <div class="web-live-txt">
          <strong>Tu página está en vivo</strong>
          <small>{{ publicUrl }}</small>
        </div>
        <div class="web-live-actions">
          <button type="button" class="btn ghost btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar link</button>
          <button type="button" class="btn btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Abrir mi página</button>
        </div>
      </div>
    </div>
    <!-- ================= MI TIENDA ================= -->
    <div v-if="seen.store" v-show="section === 'store' || (section === 'web' && tabGroups.web.length === 1)" class="web-scope" :class="{ 'sec-on': section === 'store' }">
      <div class="page-head">
        <div>
          <h1>Mi página web</h1>
          <p>Tu dirección en internet. Compartí el link por WhatsApp o donde quieras.</p>
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
          <p class="hint">Si la pausás, tus clientes ven un aviso hasta que la vuelvas a publicar.</p>
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

            </div>
            <p class="hint">Ojo: la dirección anterior deja de funcionar y vas a tener que avisarles a tus clientes.</p>
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

        <div class="card domain-card">
          <h3><AppIcon name="globe" :size="18" /> Tu dominio propio</h3>
          <template v-if="!canCustomDomain">
            <p>Usá un dominio que ya sea tuyo (por ejemplo <code class="mono">mitienda.com</code>) en lugar del link de DAVENT.</p>
            <p class="hint">Disponible en el plan Premium.</p>
            <button class="btn secondary btn-auto" @click="section = 'plans'">Ver planes <AppIcon name="arrow-right" :size="16" /></button>
          </template>
          <template v-else>
            <p>¿Querés que tu web tenga nombre propio, como <code class="mono">mitienda.com</code>? Comprá el dominio y conectalo acá — te guiamos paso a paso.</p>
            <AlertMessage v-if="domainErr" kind="error" :message="domainErr" />
            <div v-if="domainInfo?.status === 'verified'" class="link-bar">
              <code class="mono link-url">{{ domainUrl }}</code>
              <span class="pill ok">Verificado</span>
            </div>
            <template v-else>
              <ol v-if="!domainInfo" class="domain-mini-steps">
                <li><span>1</span> Comprá tu dominio</li>
                <li><span>2</span> Pegalo en el campo de abajo</li>
                <li><span>3</span> Copiá 2 datos en tu registrador</li>
              </ol>
              <div class="field">
                <label for="custom-domain">Tu dominio</label>
                <input
                  id="custom-domain"
                  name="custom-domain"
                  type="text"
                  class="input"
                  v-model="domainInput"
                  placeholder="mitienda.com"
                  maxlength="253"
                  autocomplete="off"
                  @keyup.enter="saveDomainLink"
                />
              </div>
            </template>
            <div v-if="domainInfo && domainInfo.status !== 'verified'" class="domain-dns">
              <p class="hint">Copiá estos dos datos en tu registrador (buscá «DNS» o «Registros» en su menú) y después verificá:</p>
              <div class="dns-row">
                <span class="pill muted">CNAME</span>
                <code class="mono">{{ domainInfo.domain }}</code>
                <span>→</span>
                <code class="mono">{{ domainInfo.cname_target }}</code>
              </div>
              <div class="dns-row">
                <span class="pill muted">TXT</span>
                <code class="mono">{{ domainInfo.txt_name }}</code>
                <span>→</span>
                <code class="mono dns-txt">{{ domainInfo.txt_value }}</code>
              </div>
              <p class="hint">Los cambios pueden tardar hasta 48 h en verse.</p>
              <p v-if="domainStatus" class="slug-check" role="status">
                <span class="pill" :class="domainStatus.kind">{{ domainStatus.text }}</span>
              </p>
            </div>
            <div class="btn-row link-actions">
              <button v-if="domainInfo?.status === 'verified'" class="btn btn-auto" @click="openDomain"><AppIcon name="external-link" :size="16" /> Abrir {{ domainInfo.domain }}</button>
              <button v-else class="btn btn-auto" :disabled="domainBusy || !domainInput.trim()" @click="saveDomainLink">
                <span v-if="domainBusy" class="spinner" aria-hidden="true"></span>{{ domainInfo ? 'Guardar cambios' : 'Conectar mi dominio' }}
              </button>
              <button v-if="domainInfo && domainInfo.status !== 'verified'" class="btn secondary btn-auto" :disabled="domainBusy" @click="checkDomainNow">Ya lo configuré, verificar</button>
              <button v-if="domainInfo" class="btn ghost btn-auto" :disabled="domainBusy" @click="removeDomain">Quitar dominio</button>
            </div>
            <details class="domain-guide" :open="!domainInfo">
              <summary><AppIcon name="circle-help" :size="15" /> Guía paso a paso</summary>
              <ol>
                <li><strong>Comprá tu dominio</strong> en NIC Argentina, GoDaddy o Cloudflare. Sale muy poco al año.</li>
                <li><strong>Pegalo en el campo de arriba</strong> y tocá «Conectar mi dominio».</li>
                <li><strong>Copiá los 2 datos</strong> que te mostramos y pegalos en tu registrador (sección «DNS» o «Registros DNS»).</li>
                <li><strong>Tocá «Ya lo configuré, verificar»</strong>. Puede tardar hasta 48 h.</li>
              </ol>
              <button type="button" class="btn ghost btn-auto domain-guide-help" @click="section = 'support'">¿Dudas? Pedile ayuda a tu asistente</button>
            </details>
          </template>
        </div>

      </template>
    </div>
    <!-- ================= DISEÑO ================= -->
    <div v-if="seen.design" v-show="section === 'design'" class="web-scope" :class="{ 'sec-on': section === 'design' }">
      <div class="page-head">
        <div>
          <h1>Diseño</h1>
          <p>Elegí el diseño y los colores de tu página.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="design" @select="section = $event" />

      <div v-if="aiAssistEnabled" class="next-card assist-card">
        <span class="next-icon"><AppIcon name="sparkles" :size="22" /></span>
        <div><strong>Asistencia con IA</strong><small>Respondé unas preguntas y te armamos el diseño de tu web.</small></div>
        <button class="btn btn-auto assist-btn" @click="openAssist('design')">
          <AppIcon v-if="navLocks.design_assisted" name="lock" :size="15" /><AppIcon v-else name="sparkles" :size="15" /> Empezar
        </button>
      </div>

      <DesignStylesTab
        :form="designForm" :benefits="plan?.benefits || {}"
        :shop-name="store.customization?.display_name || business" :can-studio="canDesignAdvanced"
        :site-templates="designSiteTemplates" v-model:preview-open="designPreviewOpen"
        :page-options="designPageOptions" @toggle-page="toggleSiteTemplate" :on-save-show="saveShowFromModal"
        @navigate="section = $event" @open-studio="onOpenStudio" @support="onBellClick"
      >
        <template #actions>
          <div class="design-actions">
            <AppButton :loading="designBusy" :disabled="!designDirtyAll" @click="saveDesign()"><AppIcon name="check" :size="16" /> Guardar cambios</AppButton>
            <button type="button" class="btn secondary btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
          </div>
          <p v-if="designDirtyAll" class="hint design-dirty-hint"><AppIcon name="pencil" :size="13" /> Los cambios ya se ven en la vista previa, pero todavía no están publicados: tocá «Guardar cambios».</p>
        </template>
      </DesignStylesTab>
    </div>

    <!-- Editor Avanzado (Premium): modal fullscreen con el preview al
         centro y los editores del site_theme en el sidebar izquierdo. -->
    <Teleport to="body">
      <DesignStudioTab
        v-if="studioModalOpen" :form="designForm" :benefits="plan?.benefits || {}"
        :customization="store.customization || {}" @close="studioModalOpen = false"
      >
        <template #actions>
          <div class="design-actions">
            <AppButton :loading="designBusy" :disabled="!designDirtyAll" @click="saveDesign()"><AppIcon name="check" :size="16" /> Guardar cambios</AppButton>
            <button type="button" class="btn secondary btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
          </div>
          <p v-if="designDirtyAll" class="hint design-dirty-hint"><AppIcon name="pencil" :size="13" /> Los cambios ya se ven en la vista previa, pero todavía no están publicados: tocá «Guardar cambios».</p>
        </template>
      </DesignStudioTab>
    </Teleport>
    <!-- ================= MI EMPRESA (marketing de la portada) ================= -->
    <div v-if="seen.company" v-show="section === 'company'" :class="{ 'sec-on': section === 'company' }">
      <div class="page-head">
        <div>
          <h1>Sobre mi negocio</h1>
          <p>Tocá una tarjeta, completá el formulario y listo. Lo que dejes vacío no aparece en tu web.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="company" @select="section = $event" />

      <div v-if="aiAssistEnabled" class="next-card assist-card">
        <span class="next-icon"><AppIcon name="sparkles" :size="22" /></span>
        <div><strong>Asistencia con IA</strong><small>Te ayudamos a completar los datos de tu negocio, sin pisar lo que ya cargaste.</small></div>
        <button class="btn btn-auto assist-btn" @click="openAssist('business')">
          <AppIcon v-if="navLocks.design_assisted" name="lock" :size="15" /><AppIcon v-else name="sparkles" :size="15" /> Empezar
        </button>
      </div>

      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <template v-if="canCustomize">
        <nav class="mk-launch" aria-label="Secciones de tu página">
          <button
            v-for="l in mkNav" :key="l.key" type="button" class="mk-launcher"
            @click="mkOpen = l.key"
          >
            <span class="mk-launcher-ico" :class="`hue-${l.key}`"><AppIcon :name="l.icon" :size="20" /></span>
            <span class="mk-launcher-txt">
              <strong>{{ l.label }}</strong>
              <small>{{ l.desc }}</small>
            </span>
            <span class="mk-launcher-side">
              <span v-if="mkSummary(l.key)" class="mk-done"><AppIcon name="check" :size="12" :stroke="2.5" /> {{ mkSummary(l.key) }}</span>
              <AppIcon name="chevron-right" :size="16" class="mk-launcher-go" />
            </span>
          </button>
        </nav>
        <p class="hint mk-launch-hint">Tocá una tarjeta para editarla.</p>

        <!-- ===== Modal de edición: un bloque a la vez ===== -->
        <div v-if="mkOpen" class="mk-overlay" @click.self="mkOpen = null">
          <div class="mk-modal" role="dialog" aria-modal="true" :aria-label="mkOpenMeta?.label || 'Editar sección'">
            <header class="mk-modal-head">
              <span class="mk-modal-ico" :class="`hue-${mkOpen}`"><AppIcon :name="mkOpenMeta?.icon || 'pencil'" :size="20" /></span>
              <div class="mk-modal-txt">
                <h2>{{ mkOpenMeta?.label }}</h2>
                <small>{{ mkOpenMeta?.desc }}</small>
              </div>
              <button type="button" class="mk-modal-x" aria-label="Cerrar" @click="mkOpen = null"><AppIcon name="x" :size="18" /></button>
            </header>
            <div class="mk-modal-body">

        <!-- ===== Tu negocio (nombre visible, titular y descripción) ===== -->
        <div v-show="mkOpen === 'identity'" class="card mk-card">
          <h3><AppIcon name="user" :size="18" /> Tu negocio</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Lo primero que se ve en tu portada: el nombre, una frase corta y una descripción.</span></p>
          <AppInput v-model="designForm.display_name" label="Nombre que se muestra" name="company_display_name" placeholder="Ej. Almacén Don Pedro" hint="Vacío: se usa el nombre de tu cuenta." maxlength="60" :error="designFieldErr('display_name')" @blur="designTouched.display_name = true" />
          <AppInput v-model="designForm.headline" label="Titular" name="company_headline" placeholder="Ej. Tu almacén de barrio, ahora también online" hint="Frase corta debajo del nombre. Vacío: no se muestra." maxlength="140" :error="designFieldErr('headline')" @blur="designTouched.headline = true" />
          <div class="field">
            <label for="company-description">Descripción</label>
            <textarea
              id="company-description"
              v-model="designForm.description"
              class="textarea"
              :class="{ invalid: designFieldErr('description') }"
              placeholder="Contá en pocas líneas qué hace tu negocio"
              maxlength="800"
              rows="4"
              @blur="designTouched.description = true"
            ></textarea>
            <p class="hint">Se ve en la portada y al compartir el link de tu web. {{ designForm.description.length }}/800</p>
            <p v-if="designFieldErr('description')" class="field-error" role="alert">{{ designFieldErr('description') }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveIdentity">Guardar información</AppButton>
          </div>
        </div>

        <!-- ===== Sobre nosotros ===== -->
        <div v-show="mkOpen === 'about'" class="card mk-card">
          <h3><AppIcon name="building-2" :size="18" /> Sobre nosotros</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Contá quién sos y qué hace tu negocio. Lo que dejes vacío no se muestra en tu página.</span></p>
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
        <div v-show="mkOpen === 'services'" class="card mk-card">
          <h3><AppIcon name="layout-grid" :size="18" /> Qué ofrecemos <span v-if="!supportsServices" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> No disponible en este diseño</span></h3>
          <p v-if="!supportsServices" class="hint">La plantilla que elegiste no tiene apartado de servicios. Disponible en: {{ blockDesigns('services') }}.</p>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Sumá tarjetas con ícono que resuman lo que ofrecés. Podés agregar varias y ordenarlas con las flechas.</span></p>
          <fieldset class="mk-fieldset" :disabled="!supportsServices">
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
                  <span class="qa-num">Servicio {{ i + 1 }}</span>
                  <label class="mk-mini"><span>Ícono que se muestra</span>
                    <div class="mk-icon-field">
                      <span class="mk-icon-preview" aria-hidden="true"><AppIcon :name="serviceIcons[s.icon] ? s.icon : 'package'" :size="17" /></span>
                      <select v-model="s.icon" class="select" :aria-label="`Ícono del servicio ${i + 1}`">
                        <option v-for="(label, key) in serviceIcons" :key="key" :value="key">{{ label }}</option>
                      </select>
                    </div>
                  </label>
                  <label class="mk-mini"><span>Nombre</span>
                    <input v-model="s.title" class="input" type="text" :maxlength="mkLimits.serviceTitle" placeholder="Ej. Envíos a todo el país" :aria-label="`Título del servicio ${i + 1}`" />
                  </label>
                  <label class="mk-mini"><span>Descripción corta</span>
                    <textarea v-model="s.text" class="textarea" rows="2" :maxlength="mkLimits.serviceText" placeholder="Una línea que lo describa" :aria-label="`Descripción del servicio ${i + 1}`"></textarea>
                  </label>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el servicio ${i + 1}`" @click="moveRow(designForm.services, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.services.length - 1" :aria-label="`Bajar el servicio ${i + 1}`" @click="moveRow(designForm.services, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el servicio ${i + 1}`" @click="designForm.services.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste servicios.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.services.length >= mkLimits.services" @click="addRow(designForm.services, mkLimits.services, { icon: 'package', title: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar servicio
            </button>
            <p class="hint">Se muestran como tarjetas con ícono. Ordenalas con las flechas.</p>
            <p v-if="companyErrs.services" class="field-error" role="alert">{{ companyErrs.services }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveServices">Guardar sección</AppButton>
          </div>
          </fieldset>
        </div>

        <!-- ===== Planes de suscripción (publicidad, sin cobro online) ===== -->
        <div v-show="mkOpen === 'plans'" class="card mk-card">
          <h3><AppIcon name="crown" :size="18" /> Planes de suscripción</h3>
          <p v-if="!supportsPlans" class="hint">El diseño elegido no muestra este apartado en tu web, pero podés cargar los planes igual: se ven cuando cambies a un diseño que lo incluya ({{ blockDesigns('plans') }}).</p>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Publicá membresías o clubs sin cobro online: los interesados te escriben por WhatsApp o el formulario.</span></p>
          <fieldset class="mk-fieldset">
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_plans" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Tarjetas con membresías, clubs o packs por suscripción que ofrecés a tus clientes. Es solo publicidad: no se cobran desde la plataforma. Se oculta sola si no cargás ninguno.</small>
              </span>
            </label>
          </div>
          <AppInput v-model="designForm.plans_title" label="Título de la sección" name="company_plans_title" placeholder="Planes y membresías" hint="Vacío: se muestra 'Planes y membresías'." maxlength="80" />
          <div class="field">
            <label>Planes <span class="hint-inline">({{ designForm.plans.length }}/{{ mkLimits.plans }})</span></label>
            <div v-if="designForm.plans.length" class="qa-list">
              <div v-for="(p, i) in designForm.plans" :key="i" class="qa-item">
                <div class="qa-fields">
                  <span class="qa-num">Plan {{ i + 1 }}</span>
                  <div class="mk-pair">
                    <label class="mk-mini"><span>Nombre</span>
                      <input v-model="p.name" class="input" type="text" :maxlength="mkLimits.planName" placeholder="Ej. Club mensual" :aria-label="`Nombre del plan ${i + 1}`" />
                    </label>
                    <label class="mk-mini"><span>Precio</span>
                      <input v-model="p.price" class="input" type="text" :maxlength="mkLimits.planPrice" placeholder="Ej. $15.000/mes" :aria-label="`Precio del plan ${i + 1}`" />
                    </label>
                  </div>
                  <label class="mk-mini"><span>Detalle <em>(opcional)</em></span>
                    <input v-model="p.note" class="input" type="text" :maxlength="mkLimits.planNote" placeholder="Ej. El más elegido — sin permanencia" :aria-label="`Detalle del plan ${i + 1}`" />
                  </label>
                  <label class="mk-mini"><span>Beneficios, uno por línea</span>
                    <textarea v-model="p.items" class="textarea" rows="3" placeholder="Un beneficio por línea. Ej.&#10;2 visitas al mes&#10;Descuento en productos" :aria-label="`Beneficios del plan ${i + 1}`"></textarea>
                  </label>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el plan ${i + 1}`" @click="moveRow(designForm.plans, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.plans.length - 1" :aria-label="`Bajar el plan ${i + 1}`" @click="moveRow(designForm.plans, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el plan ${i + 1}`" @click="designForm.plans.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste planes.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.plans.length >= mkLimits.plans" @click="addRow(designForm.plans, mkLimits.plans, { name: '', price: '', note: '', items: '' })">
              <AppIcon name="plus" :size="15" /> Agregar plan
            </button>
            <p class="hint">El precio es texto libre (ej. "$15.000/mes" o "Consultar"). Los interesados te escriben por WhatsApp o el formulario de contacto — acá no se cobra nada.</p>
            <p v-if="companyErrs.plans" class="field-error" role="alert">{{ companyErrs.plans }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="savePlans">Guardar sección</AppButton>
          </div>
          </fieldset>
        </div>

        <!-- ===== Tus números (cifras destacadas) ===== -->
        <div v-show="mkOpen === 'stats'" class="card mk-card">
          <h3><AppIcon name="trending-up" :size="18" /> Tus números</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Mostrá cifras que generan confianza: cuántos clientes, años de trayectoria o productos vendidos.</span></p>
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
                <div class="qa-fields">
                  <span class="qa-num">Cifra {{ i + 1 }}</span>
                  <div class="mk-pair">
                    <label class="mk-mini"><span>Número</span>
                      <input v-model="s.value" class="input" type="text" :maxlength="mkLimits.statValue" placeholder="+500" :aria-label="`Valor de la cifra ${i + 1}`" />
                    </label>
                    <label class="mk-mini"><span>Qué significa</span>
                      <input v-model="s.label" class="input" type="text" :maxlength="mkLimits.statLabel" placeholder="clientes que nos eligen" :aria-label="`Etiqueta de la cifra ${i + 1}`" />
                    </label>
                  </div>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir la cifra ${i + 1}`" @click="moveRow(designForm.stats, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.stats.length - 1" :aria-label="`Bajar la cifra ${i + 1}`" @click="moveRow(designForm.stats, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar la cifra ${i + 1}`" @click="designForm.stats.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste cifras.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.stats.length >= mkLimits.stats" @click="addRow(designForm.stats, mkLimits.stats, { value: '', label: '' })">
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
        <div v-show="mkOpen === 'testimonials'" class="card mk-card">
          <h3><AppIcon name="quote" :size="18" /> Testimonios</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Las opiniones de tus clientes convencen mejor que cualquier anuncio. Pediles permiso antes de publicarlas.</span></p>
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
                  <span class="qa-num">Testimonio {{ i + 1 }}</span>
                  <div class="mk-pair">
                    <label class="mk-mini"><span>Nombre del cliente</span>
                      <input v-model="t.name" class="input" type="text" :maxlength="mkLimits.testimonialName" placeholder="Ej. María Gómez" :aria-label="`Nombre del testimonio ${i + 1}`" />
                    </label>
                    <label class="mk-mini"><span>Detalle <em>(opcional)</em></span>
                      <input v-model="t.detail" class="input" type="text" :maxlength="mkLimits.testimonialDetail" placeholder="Ej. Cliente desde 2019" :aria-label="`Detalle del testimonio ${i + 1}`" />
                    </label>
                  </div>
                  <label class="mk-mini"><span>Su opinión</span>
                    <textarea v-model="t.text" class="textarea" rows="2" :maxlength="mkLimits.testimonialText" placeholder="Lo que dijo de tu negocio" :aria-label="`Texto del testimonio ${i + 1}`"></textarea>
                  </label>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el testimonio ${i + 1}`" @click="moveRow(designForm.testimonials, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.testimonials.length - 1" :aria-label="`Bajar el testimonio ${i + 1}`" @click="moveRow(designForm.testimonials, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el testimonio ${i + 1}`" @click="designForm.testimonials.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste testimonios.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.testimonials.length >= mkLimits.testimonials" @click="addRow(designForm.testimonials, mkLimits.testimonials, { name: '', detail: '', text: '' })">
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
        <div v-show="mkOpen === 'faqs'" class="card mk-card">
          <h3><AppIcon name="message-circle" :size="18" /> Preguntas frecuentes</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Ahorrá consultas repetidas: escribí la pregunta tal como te la haría un cliente y su respuesta.</span></p>
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
                  <span class="qa-num">Pregunta {{ i + 1 }}</span>
                  <label class="mk-mini"><span>La pregunta</span>
                    <input v-model="f.q" class="input" type="text" :maxlength="mkLimits.faqQ" placeholder="Ej. ¿Hacen envíos?" :aria-label="`Pregunta ${i + 1}`" />
                  </label>
                  <label class="mk-mini"><span>La respuesta</span>
                    <textarea v-model="f.a" class="textarea" rows="2" :maxlength="mkLimits.faqA" placeholder="Respuesta que ve la visita" :aria-label="`Respuesta ${i + 1}`"></textarea>
                  </label>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir la pregunta ${i + 1}`" @click="moveRow(designForm.faqs, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.faqs.length - 1" :aria-label="`Bajar la pregunta ${i + 1}`" @click="moveRow(designForm.faqs, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar la pregunta ${i + 1}`" @click="designForm.faqs.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste preguntas.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.faqs.length >= mkLimits.faqs" @click="addRow(designForm.faqs, mkLimits.faqs, { q: '', a: '' })">
              <AppIcon name="plus" :size="15" /> Agregar pregunta
            </button>
            <p v-if="companyErrs.faqs" class="field-error" role="alert">{{ companyErrs.faqs }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveFaqs">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Garantías y beneficios ===== -->
        <div v-show="mkOpen === 'benefits'" class="card mk-card">
          <h3><AppIcon name="shield-check" :size="18" /> Garantías y beneficios</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Envíos, garantía y medios de pago: lo que tranquiliza a quien está por comprar.</span></p>
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
                  <span class="qa-num">Beneficio {{ i + 1 }}</span>
                  <label class="mk-mini"><span>Ícono que se muestra</span>
                    <div class="mk-icon-field">
                      <span class="mk-icon-preview" aria-hidden="true"><AppIcon :name="serviceIcons[b.icon] ? b.icon : 'shield-check'" :size="17" /></span>
                      <select v-model="b.icon" class="select" :aria-label="`Ícono del beneficio ${i + 1}`">
                        <option v-for="(label, key) in serviceIcons" :key="key" :value="key">{{ label }}</option>
                      </select>
                    </div>
                  </label>
                  <label class="mk-mini"><span>Nombre</span>
                    <input v-model="b.title" class="input" type="text" :maxlength="mkLimits.benefitTitle" placeholder="Ej. Garantía de 30 días" :aria-label="`Título del beneficio ${i + 1}`" />
                  </label>
                  <label class="mk-mini"><span>Descripción corta</span>
                    <textarea v-model="b.text" class="textarea" rows="2" :maxlength="mkLimits.benefitText" placeholder="Una línea que lo describa" :aria-label="`Descripción del beneficio ${i + 1}`"></textarea>
                  </label>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el beneficio ${i + 1}`" @click="moveRow(designForm.benefits, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.benefits.length - 1" :aria-label="`Bajar el beneficio ${i + 1}`" @click="moveRow(designForm.benefits, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el beneficio ${i + 1}`" @click="designForm.benefits.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste beneficios.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.benefits.length >= mkLimits.benefits" @click="addRow(designForm.benefits, mkLimits.benefits, { icon: 'shield-check', title: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar beneficio
            </button>
            <p v-if="companyErrs.benefits" class="field-error" role="alert">{{ companyErrs.benefits }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveBenefits">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Línea de tiempo ===== -->
        <div v-show="mkOpen === 'timeline'" class="card mk-card">
          <h3><AppIcon name="flag" :size="18" /> Línea de tiempo</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Contá tu historia paso a paso: cuándo empezaste, el local nuevo, cada logro.</span></p>
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
                  <span class="qa-num">Hito {{ i + 1 }}</span>
                  <label class="mk-mini"><span>Cuándo <em>(año o etapa)</em></span>
                    <input v-model="t.label" class="input" type="text" :maxlength="mkLimits.timelineLabel" placeholder="Ej. 2015 o Hoy" :aria-label="`Rótulo del hito ${i + 1}`" />
                  </label>
                  <label class="mk-mini"><span>Qué pasó</span>
                    <textarea v-model="t.text" class="textarea" rows="2" :maxlength="mkLimits.timelineText" placeholder="Qué pasó en ese momento" :aria-label="`Texto del hito ${i + 1}`"></textarea>
                  </label>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el hito ${i + 1}`" @click="moveRow(designForm.timeline, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.timeline.length - 1" :aria-label="`Bajar el hito ${i + 1}`" @click="moveRow(designForm.timeline, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el hito ${i + 1}`" @click="designForm.timeline.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste hitos.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.timeline.length >= mkLimits.timeline" @click="addRow(designForm.timeline, mkLimits.timeline, { label: '', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar hito
            </button>
            <p v-if="companyErrs.timeline" class="field-error" role="alert">{{ companyErrs.timeline }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveTimeline">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Equipo ===== -->
        <div v-show="mkOpen === 'team'" class="card mk-card">
          <h3><AppIcon name="users" :size="18" /> Equipo</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Presentá a las personas detrás del negocio con su nombre y su rol.</span></p>
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
                  <span class="qa-num">Integrante {{ i + 1 }}</span>
                  <div class="mk-pair">
                    <label class="mk-mini"><span>Nombre</span>
                      <input v-model="m.name" class="input" type="text" :maxlength="mkLimits.teamName" placeholder="Ej. Laura" :aria-label="`Nombre del integrante ${i + 1}`" />
                    </label>
                    <label class="mk-mini"><span>Su rol</span>
                      <input v-model="m.role" class="input" type="text" :maxlength="mkLimits.teamRole" placeholder="Ej. Dueña, Técnica" :aria-label="`Rol del integrante ${i + 1}`" />
                    </label>
                  </div>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el integrante ${i + 1}`" @click="moveRow(designForm.team, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.team.length - 1" :aria-label="`Bajar el integrante ${i + 1}`" @click="moveRow(designForm.team, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el integrante ${i + 1}`" @click="designForm.team.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste integrantes.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.team.length >= mkLimits.team" @click="addRow(designForm.team, mkLimits.team, { name: '', role: '' })">
              <AppIcon name="plus" :size="15" /> Agregar integrante
            </button>
            <p v-if="companyErrs.team" class="field-error" role="alert">{{ companyErrs.team }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveTeam">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Horarios de atención ===== -->
        <div v-show="mkOpen === 'hours'" class="card mk-card">
          <h3><AppIcon name="clock" :size="18" /> Horarios de atención</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Indicá cuándo atendés: aparece junto a tus datos de contacto en la web.</span></p>
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
                <div class="qa-fields">
                  <span class="qa-num">Horario {{ i + 1 }}</span>
                  <div class="mk-pair">
                    <label class="mk-mini"><span>Días</span>
                      <input v-model="h.label" class="input" type="text" :maxlength="mkLimits.hourLabel" placeholder="Lunes a viernes" :aria-label="`Días del horario ${i + 1}`" />
                    </label>
                    <label class="mk-mini"><span>Horario</span>
                      <input v-model="h.value" class="input" type="text" :maxlength="mkLimits.hourValue" placeholder="9 a 18 h" :aria-label="`Franja del horario ${i + 1}`" />
                    </label>
                  </div>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el horario ${i + 1}`" @click="moveRow(designForm.hours, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.hours.length - 1" :aria-label="`Bajar el horario ${i + 1}`" @click="moveRow(designForm.hours, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el horario ${i + 1}`" @click="designForm.hours.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste horarios.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.hours.length >= mkLimits.hours" @click="addRow(designForm.hours, mkLimits.hours, { label: '', value: '' })">
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
        <div v-show="mkOpen === 'cta'" class="card mk-card">
          <h3><AppIcon name="megaphone" :size="18" /> Llamado a la acción</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>La banda final de tu portada: un título, una frase y un botón grande para que te escriban.</span></p>
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
        <div v-show="mkOpen === 'ann'" class="card mk-card">
          <h3><AppIcon name="megaphone" :size="18" /> Cinta de anuncios</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Avisos cortos que corren en bucle debajo de tu portada: promos, envíos gratis, cuotas.</span></p>
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
                <div class="qa-fields">
                  <span class="qa-num">Anuncio {{ i + 1 }}</span>
                  <div class="mk-pair">
                    <label class="mk-mini"><span>Ícono</span>
                      <div class="mk-icon-field">
                        <span class="mk-icon-preview" aria-hidden="true"><AppIcon :name="serviceIcons[a.icon] ? a.icon : 'megaphone'" :size="17" /></span>
                        <select v-model="a.icon" class="select" :aria-label="`Ícono del anuncio ${i + 1}`">
                          <option v-for="(label, key) in serviceIcons" :key="key" :value="key">{{ label }}</option>
                        </select>
                      </div>
                    </label>
                    <label class="mk-mini"><span>Texto del anuncio</span>
                      <input v-model="a.text" class="input" type="text" :maxlength="mkLimits.announcementText" placeholder="Ej. Envíos gratis superando $80.000" :aria-label="`Texto del anuncio ${i + 1}`" />
                    </label>
                  </div>
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el anuncio ${i + 1}`" @click="moveRow(designForm.announcements, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.announcements.length - 1" :aria-label="`Bajar el anuncio ${i + 1}`" @click="moveRow(designForm.announcements, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el anuncio ${i + 1}`" @click="designForm.announcements.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste anuncios.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="designForm.announcements.length >= mkLimits.announcements" @click="addRow(designForm.announcements, mkLimits.announcements, { icon: 'megaphone', text: '' })">
              <AppIcon name="plus" :size="15" /> Agregar anuncio
            </button>
            <p class="hint">Frases cortas con ícono que se repiten en bucle. Se ocultan solas si no cargás ninguna.</p>
            <p v-if="companyErrs.announcements" class="field-error" role="alert">{{ companyErrs.announcements }}</p>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveAnnouncements">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Videos (embeds de redes + stream en vivo Premium) ===== -->
        <div v-show="mkOpen === 'video'" class="card mk-card">
          <h3><AppIcon name="play" :size="18" /> Videos</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Pegá el link completo de cada video de TikTok, Instagram, YouTube, Facebook o Vimeo: se muestran como tarjetas en tu página.</span></p>
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_video" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar en tu web</strong>
                <small>Sección con tus videos y, si cargás un stream, el botón "Transmitiendo en vivo".</small>
              </span>
            </label>
          </div>
          <div class="field">
            <label>Links de videos <span class="hint-inline">({{ (designForm.videos || []).length }}/{{ videosCap }})</span></label>
            <div v-if="(designForm.videos || []).length" class="qa-list">
              <div v-for="(u, i) in designForm.videos" :key="i" class="qa-item">
                <div class="qa-fields">
                  <span class="qa-num">Video {{ i + 1 }}</span>
                  <input v-model="designForm.videos[i]" class="input" type="url" maxlength="300" placeholder="https://www.tiktok.com/@tunegocio/video/…" :aria-label="`Link del video ${i + 1}`" />
                </div>
                <div class="qa-actions">
                  <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir el video ${i + 1}`" @click="moveRow(designForm.videos, i, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                  <button type="button" class="icon-btn" :disabled="i === designForm.videos.length - 1" :aria-label="`Bajar el video ${i + 1}`" @click="moveRow(designForm.videos, i, 1)"><AppIcon name="chevron-down" :size="14" /></button>
                  <button type="button" class="icon-btn danger" :aria-label="`Borrar el video ${i + 1}`" @click="designForm.videos.splice(i, 1)"><AppIcon name="trash" :size="15" /></button>
                </div>
              </div>
            </div>
            <div v-else class="mk-empty"><AppIcon name="inbox" :size="16" /><span>Todavía no cargaste videos.</span></div>
            <button type="button" class="btn ghost btn-auto mk-add" :disabled="(designForm.videos || []).length >= videosCap" @click="addRow(designForm.videos, videosCap, '')">
              <AppIcon name="plus" :size="15" /> Agregar video
            </button>
            <p class="hint">YouTube, Vimeo, TikTok, Instagram o Facebook. Tu plan admite hasta {{ videosCap }} videos.</p>
          </div>
          <div class="field" :class="{ locked: !canLiveStream }">
            <AppInput v-model="designForm.live_stream_url" label="Link del stream en vivo" name="company_live_stream_url" placeholder="Link del stream (YouTube, Facebook) o de tu canal de Twitch" hint="Con un link cargado aparece el botón «Transmitiendo en vivo» en tu portada: al tocarlo se abre el stream en un modal. Disponible en el plan Premium." maxlength="300" />
          </div>
          <AppInput v-model="designForm.video_title" label="Título de la sección" name="company_video_title" placeholder="Mirá nuestro video" hint="Vacío: se muestra 'Mirá nuestro video'." maxlength="80" />
          <p class="hint">Aparece en un orden fijo entre las secciones de tu página.</p>
          <p v-if="companyErrs.video" class="field-error" role="alert">{{ companyErrs.video }}</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveVideo">Guardar sección</AppButton>
          </div>
        </div>

        <!-- ===== Contacto y redes (WhatsApp, redes, email público y mapa) ===== -->
        <div v-show="mkOpen === 'contact'" class="card mk-card">
          <h3><AppIcon name="phone" :size="18" /> Contacto y redes</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Cómo te escriben tus clientes: el botón de WhatsApp, tus redes y la sección de contacto al final de la página.</span></p>
          <AppInput v-model="designForm.whatsapp" label="WhatsApp" name="company_whatsapp" type="tel" placeholder="+5493871551234" hint="Número con código de país. Los botones «Escribime» de tu web abren este chat. Vacío: no hay botón." :error="designFieldErr('whatsapp')" @blur="designTouched.whatsapp = true" />
          <div class="grid-2">
            <AppInput v-model="designForm.instagram" label="Instagram" name="company_instagram" placeholder="tunegocio" hint="Solo el usuario, sin «@»." :error="designFieldErr('instagram')" @blur="designTouched.instagram = true" />
            <AppInput v-model="designForm.tiktok" label="TikTok" name="company_tiktok" placeholder="tunegocio" hint="Solo el usuario, sin «@»." :error="designFieldErr('tiktok')" @blur="designTouched.tiktok = true" />
          </div>
          <AppInput v-model="designForm.facebook" label="Facebook" name="company_facebook" placeholder="tunegocio o link de tu página" hint="El nombre de tu página o tu usuario." :error="designFieldErr('facebook')" @blur="designTouched.facebook = true" />
          <AppInput v-model="designForm.contact_email" label="Email de contacto público" name="company_contact_email" type="email" placeholder="hola@tunegocio.com" hint="Los mensajes del formulario de contacto llegan acá. Vacío: llegan al email de tu cuenta." :error="designFieldErr('contact_email')" @blur="designTouched.contact_email = true" />
          <div class="check-list">
            <label class="check-item">
              <input v-model="designForm.show_contact" type="checkbox" />
              <span class="check-text">
                <strong>Mostrar sección de contacto</strong>
                <small>El formulario «Escribinos» al final de tu página. Se oculta sola si no hay datos de contacto.</small>
              </span>
            </label>
            <label class="check-item" :class="{ disabled: !canLocationMap }">
              <input v-model="designForm.show_location" type="checkbox" :disabled="!canLocationMap" />
              <span class="check-text">
                <strong>Mostrar mapa de ubicación <span v-if="!canLocationMap" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Plan Estándar en adelante</span></strong>
                <small>Tu domicilio en un mapa dentro de la sección de contacto.</small>
              </span>
            </label>
          </div>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveContact">Guardar información</AppButton>
          </div>
        </div>

        <!-- ===== Extras (aviso del catálogo + texto del pie) ===== -->
        <div v-show="mkOpen === 'extras'" class="card mk-card">
          <h3><AppIcon name="plus" :size="18" /> Extras</h3>
          <p class="mk-tip"><AppIcon name="info" :size="15" /><span>Dos detalles finales: un aviso arriba del catálogo y una frase al pie de tu página.</span></p>
          <AppInput v-model="designForm.catalog_note" label="Aviso del catálogo" name="company_catalog_note" placeholder="Ej. Envíos a todo el país · Aceptamos todos los medios de pago" hint="Tira informativa que aparece arriba de tu página de catálogo. Vacío: no se muestra." maxlength="160" />
          <AppInput v-model="designForm.footer_text" label="Frase del pie" name="company_footer_text" placeholder="Ej. Tienda familiar desde 1998" hint="Línea extra al final de tu web, debajo del copyright. Vacío: no se muestra." maxlength="160" />
          <p v-if="companyErrs.extras" class="field-error" role="alert">{{ companyErrs.extras }}</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveExtras">Guardar sección</AppButton>
          </div>
        </div>

            </div>
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
    <!-- ================= MIS FOTOS ================= -->
    <div v-if="seen.photos" v-show="section === 'photos'" :class="{ 'sec-on': section === 'photos' }">
      <div class="page-head">
        <div>
          <h1>Mis fotos</h1>
          <p>El logo, la portada y las imágenes que se ven en tu página.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi página</button>
      </div>
      <SectionTabs :tabs="tabGroups.web" active="photos" @select="section = $event" />

      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />

      <template v-if="canCustomize">
        <div class="photos-grid">
        <div class="card">
          <h3><AppIcon name="store" :size="18" /> Logo</h3>
          <div class="logo-box">
            <span class="logo-thumb">
              <img v-if="currentLogo" :src="currentLogo" alt="Logo de tu negocio" />
              <AppIcon v-else name="image" :size="22" />
            </span>
            <div class="logo-actions">
              <AppButton type="button" class="btn-auto" :loading="logoBusy" @click="logoInput?.click()"><AppIcon name="upload" :size="15" /> {{ currentLogo ? 'Cambiar' : 'Subir logo' }}</AppButton>
              <button v-if="currentLogo" type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="onRemoveLogo"><AppIcon name="trash" :size="15" /> Quitar</button>
            </div>
          </div>
          <input ref="logoInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Subir logo" @change="onLogoPicked" />
          <p class="hint">Aparece arriba de todo en tu web. PNG o JPG de hasta 4 MB.</p>
          <p v-if="logoErr" class="field-error" role="alert">{{ logoErr }}</p>
        </div>

        <div class="card">
          <h3><AppIcon name="image" :size="18" /> Foto de portada</h3>
          <div class="cover-box">
            <span class="cover-thumb" :class="{ empty: !currentCover }">
              <img v-if="currentCover" :src="currentCover" alt="Foto de portada" />
              <AppIcon v-else name="image" :size="22" />
            </span>
            <div class="logo-actions">
              <AppButton type="button" class="btn-auto" :loading="coverBusy" @click="coverInput?.click()"><AppIcon name="upload" :size="15" /> {{ currentCover ? 'Cambiar' : 'Subir portada' }}</AppButton>
              <button v-if="currentCover" type="button" class="btn ghost btn-auto" :disabled="coverBusy" @click="onRemoveCover"><AppIcon name="trash" :size="15" /> Quitar</button>
            </div>
          </div>
          <input ref="coverInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Subir foto de portada" @change="onCoverPicked" />
          <p class="hint">La foto grande al entrar a tu web. Horizontal, hasta 4 MB.</p>
          <p v-if="coverErr" class="field-error" role="alert">{{ coverErr }}</p>
        </div>

        <div class="card">
          <h3><AppIcon name="images" :size="18" /> Carrusel de portada</h3>
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
          <input ref="carouselInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Agregar imagen al carrusel" @change="onCarouselPicked" />
          <p class="hint">Hasta {{ CAROUSEL_MAX_IMAGES }} imágenes de 4 MB. Rotan como banners en tu portada.</p>
          <p v-if="carouselErr" class="field-error" role="alert">{{ carouselErr }}</p>
        </div>

        <div class="card">
          <h3><AppIcon name="layout-grid" :size="18" /> Galería</h3>
          <div class="carousel-box">
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
          <input ref="galleryInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Agregar imagen a la galería" @change="onGalleryPicked" />
          <p class="hint">{{ galleryHint }}</p>
          <p v-if="galleryErr" class="field-error" role="alert">{{ galleryErr }}</p>
        </div>

        <div v-if="canDesignAdvanced || decorImages.length" class="card">
          <h3><AppIcon name="sparkles" :size="18" /> Fotos decorativas</h3>
          <div class="carousel-box">
            <div v-for="(img, i) in decorImages" :key="img.id" class="carousel-thumb">
              <img :src="img.url" :alt="`Imagen decorativa ${i + 1}`" />
              <div class="carousel-thumb-actions">
                <button type="button" class="icon-btn danger" aria-label="Eliminar imagen" :disabled="galleryBusy" @click="onRemoveGallery(img.id)"><AppIcon name="trash" :size="13" /></button>
              </div>
            </div>
            <button
              v-if="canAddDecor"
              type="button" class="carousel-add" :disabled="galleryBusy"
              @click="decorInput?.click()"
            >
              <span v-if="galleryBusy" class="spinner" aria-hidden="true"></span>
              <AppIcon v-else name="images" :size="20" />
              Agregar
            </button>
          </div>
          <input ref="decorInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-label="Agregar imagen decorativa" @change="onDecorPicked" />
          <p class="hint">Hasta {{ DECOR_MAX_IMAGES }} fotos que ilustran tu portada. Comparten el cupo de la galería. <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></p>
        </div>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
        <h3>Las fotos de tu web vienen con tu plan</h3>
        <p>Activá una suscripción para subir el logo, la portada y tu galería.</p>
        <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
      </div>
    </div>
    <!-- ================= VENDER ONLINE (e-commerce del dueño) ================= -->
    <div v-if="seen.selling" v-show="section === 'selling'" class="web-scope" :class="{ 'sec-on': section === 'selling' }">
      <div class="page-head">
        <div>
          <h1>Vender online</h1>
          <p>Tu tienda vende de verdad: pedidos, cobros, clientes y membresías en un solo lugar.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" :active="''" @select="section = $event" />
      <div class="grid-2">
        <button v-for="t in tabGroups.selling" :key="t.id" type="button" class="card sell-entry" @click="section = t.id">
          <span class="stat-icon"><AppIcon :name="t.icon" :size="18" /></span>
          <span class="sell-entry-txt">
            <strong>{{ t.label }}</strong>
            <small>{{ t.hint }}</small>
          </span>
          <AppIcon name="chevron-right" :size="16" class="sell-entry-arrow" />
        </button>
      </div>
    </div>

    <!-- ================= PEDIDOS ================= -->
    <div v-if="seen.orders" v-show="section === 'orders'" class="web-scope" :class="{ 'sec-on': section === 'orders' }">
      <div class="page-head">
        <div>
          <h1>Pedidos</h1>
          <p>Todo lo que te compraron: del pago a la entrega.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="orders" @select="section = $event" />
      <OrdersPanel />
    </div>

    <!-- ================= VENTAS ================= -->
    <div v-if="seen.sales" v-show="section === 'sales'" class="web-scope" :class="{ 'sec-on': section === 'sales' }">
      <div class="page-head">
        <div>
          <h1>Ventas</h1>
          <p>Cuánto vendiste en el período, por día, método de pago y estado.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="sales" @select="section = $event" />
      <SalesPanel />
    </div>

    <!-- ================= CLIENTES ================= -->
    <div v-if="seen.customers" v-show="section === 'customers'" class="web-scope" :class="{ 'sec-on': section === 'customers' }">
      <div class="page-head">
        <div>
          <h1>Clientes</h1>
          <p>Compradores y miembros de tu tienda, con su historial de compras.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="customers" @select="section = $event" />
      <CustomersPanel />
    </div>

    <!-- ================= CONSULTAS DE CLIENTES ================= -->
    <div v-if="seen.inquiries" v-show="section === 'inquiries'" class="web-scope" :class="{ 'sec-on': section === 'inquiries' }">
      <div class="page-head">
        <div>
          <h1>Consultas de clientes</h1>
          <p>Preguntas y mensajes que te dejan desde tu web.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="inquiries" @select="section = $event" />
      <BuyerSupportPanel />
    </div>

    <!-- ================= COBROS ================= -->
    <div v-if="seen.payconfig" v-show="section === 'payconfig'" class="web-scope" :class="{ 'sec-on': section === 'payconfig' }">
      <div class="page-head">
        <div>
          <h1>Cobros</h1>
          <p>Venta online, métodos de pago, datos fiscales y Mercado Pago.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="payconfig" @select="section = $event" />
      <PaymentsConfigPanel @locked="openLocked('selling')" />
    </div>

    <!-- ================= LEGAL ================= -->
    <div v-if="seen.legal" v-show="section === 'legal'" class="web-scope" :class="{ 'sec-on': section === 'legal' }">
      <div class="page-head">
        <div>
          <h1>Páginas legales y devoluciones</h1>
          <p>Términos, privacidad y devoluciones de tu web, más la bandeja de solicitudes.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="legal" @select="section = $event" />
      <LegalPagesPanel />
    </div>

    <!-- ================= MEMBRESÍAS ================= -->
    <div v-if="seen.memberships" v-show="section === 'memberships'" class="web-scope" :class="{ 'sec-on': section === 'memberships' }">
      <div class="page-head">
        <div>
          <h1>Membresías</h1>
          <p>Planes que tus clientes pueden suscribir desde tu web.</p>
        </div>
      </div>
      <SectionTabs :tabs="tabGroups.selling" active="memberships" @select="section = $event" />
      <PlansPanel />
    </div>

    <!-- ================= ACCESO DE CLIENTES (plan Ecommerce) ================= -->
    <div v-if="seen.accounts" v-show="section === 'accounts'" class="web-scope" :class="{ 'sec-on': section === 'accounts' }">
      <div class="page-head">
        <div>
          <h1>Acceso de clientes</h1>
          <p>Tus compradores crean su cuenta en tu web e ingresan con email o Google.</p>
        </div>
      </div>
      <CustomerAuthPanel />
    </div>

    <!-- ================= ESTADÍSTICAS (premium) ================= -->
    <div v-if="seen.stats" v-show="section === 'stats'" class="promo-sec promo-stats" :class="{ 'sec-on': section === 'stats' }">
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
          <div v-if="visitHasData" class="stats-chart" role="img" aria-label="Visitas por día">
            <span
              v-for="d in visitDays" :key="d.date" class="stats-bar"
              :class="{ today: d.date === visitDays[visitDays.length - 1]?.date }"
              :style="{ height: `${Math.max(2, (d.count / visitMax) * 100)}%` }"
              :title="`${d.date}: ${d.count} visita${d.count === 1 ? '' : 's'}`"
            ></span>
          </div>
          <div v-if="visitHasData" class="stats-chart-axis"><span>{{ visitDays[0]?.date?.slice(5) }}</span><span>{{ visitDays[visitDays.length - 1]?.date?.slice(5) }}</span></div>
          <div v-else class="stats-empty">
            <span class="stats-empty-icon"><AppIcon name="eye" :size="24" /></span>
            <strong>Todavía no hay visitas este mes</strong>
            <p>Cuando alguien abra tu página lo vas a ver acá, día por día.</p>
            <button type="button" class="btn btn-auto" @click="shareWhatsApp"><AppIcon name="phone" :size="16" /> Compartir mi página</button>
          </div>
          <p v-if="visitHasData" class="hint">Cada barra es un día; cuanto más alta, más visitas. Contamos una visita por persona por día.</p>
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
    <div v-if="seen.tools" v-show="section === 'tools'" class="promo-sec promo-tools" :class="{ 'sec-on': section === 'tools' }">
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
        <button v-if="canFlyers" type="button" role="tab" class="dsg-tab" :class="{ active: toolsTab === 'editor', locked: !canFlyerEditor }" :aria-selected="toolsTab === 'editor'" @click="canFlyerEditor ? toolsTab = 'editor' : openLocked('flyer_editor')"><AppIcon name="pen-tool" :size="15" /> Editor libre <span v-if="canFlyerEditor" class="tools-new">Nuevo</span><AppIcon v-else name="lock" :size="13" /></button>
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

      <FlyerEditor
        v-if="canFlyerEditor && toolsTab === 'editor'"
        :slug="store.store?.slug || ''"
        :shop-name="designShopName"
        :logo="currentLogo"
        :qr="qrDataUrl"
        :url="publicUrl"
        :can-add-gallery="canAddGallery"
        @print="openFlyer('2')"
      />
    </div>

    <!-- ================= VENTA EN LOCAL (próximamente) ================= -->
    <!-- ================= CHATBOT (solo Premium) ================= -->
    <div v-if="seen.bot" v-show="section === 'bot'" class="sec-bot" :class="{ 'sec-on': section === 'bot' }">
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
    <div v-if="seen.support" v-show="section === 'support'" class="sec-support" :class="{ 'sec-on': section === 'support' }">
      <div class="page-head">
        <div>
          <h1>Mensajes y Tu Asistente</h1>
          <p>El equipo de soporte responde en tu hilo, y Tu Asistente te informa sobre tu plan, tienda, productos, visitas, pagos y facturas.</p>
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
            <h3>Tu Asistente</h3>
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
          <AppInput v-model="accountForm.phone" label="Número de celular" name="bill_phone" type="tel" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" required :error="accountFieldErr('phone')" @blur="accountTouched.phone = true" />
          <div class="btn-row">
            <AppButton variant="ghost" type="button" @click="closeBilling">Cancelar</AppButton>
            <AppButton type="submit" :loading="billingBusy">Guardar y continuar al pago</AppButton>
          </div>
        </form>
      </div>
      <div class="price-grid">
        <PlanCard
          v-for="(p, i) in billing.plans"
          :key="p.id"
          :plan="p"
          :prev="i > 0 ? billing.plans[i - 1] : null"
          :current="billing.hasSubscription && plan?.pk === p.id"
          :busy="busyPlan === p.id"
          @select="planAction"
        />
      </div>
    </div>
    <!-- ================= PAGOS ================= -->
    <div v-if="seen.payments" v-show="section === 'payments'" class="acc-sec" :class="{ 'sec-on': section === 'payments' }">
      <div class="page-head">
        <div>
          <h1>Plan y pagos</h1>
          <p>Historial de pagos de tu suscripción. Se acreditan cuando Mercado Pago los confirma.</p>
        </div>
        <button class="btn ghost btn-auto" @click="payments.loadPayments()"><AppIcon name="refresh" :size="16" /> Actualizar</button>
      </div>
      <SectionTabs :tabs="tabGroups.billing" active="payments" @select="section = $event" />


      <AlertMessage v-if="payments.notice" kind="success" :message="payments.notice" />
      <AlertMessage v-if="payments.lastError" kind="error" :message="payments.lastError" />

      <div v-if="payments.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tus pagos…</p></div>
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
              <strong>{{ formatARS(r.total_amount) }} · {{ r.payments_count }} {{ r.payments_count === 1 ? 'pago' : 'pagos' }}</strong>
            </div>
          </div>
          <p v-else>Sin datos todavía.</p>
        </div>
        <div class="card">
          <h3><AppIcon name="dashboard" :size="18" /> Ingresos por mes</h3>
          <div v-if="payments.monthlyRevenues.length" class="kv">
            <div v-for="r in payments.monthlyRevenues" :key="r.id">
              <span>{{ MONTH_NAMES[r.month] }} {{ r.year }}</span>
              <strong>{{ formatARS(r.total_amount) }} · {{ r.payments_count }} {{ r.payments_count === 1 ? 'pago' : 'pagos' }}</strong>
            </div>
          </div>
          <p v-else>Sin datos todavía.</p>
        </div>
      </div>
    </div>
    <!-- ================= FACTURAS ================= -->
    <div v-if="seen.invoices" v-show="section === 'invoices'" class="acc-sec" :class="{ 'sec-on': section === 'invoices' }">
      <div class="page-head">
        <div>
          <h1>Plan y pagos</h1>
          <p>Comprobantes de cada pago acreditado. También te los enviamos por correo.</p>
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
    <!-- ================= NOVEDADES (changelog — discreto, sin candados) ====
         -->
    <div v-if="seen.changelog" v-show="section === 'changelog'" class="acc-sec" :class="{ 'sec-on': section === 'changelog' }">
      <div class="page-head">
        <div>
          <h1>Novedades</h1>
          <p>Los cambios y mejoras que fuimos sumando a DAVENT.</p>
        </div>
      </div>
      <div class="card">
        <div v-if="!changelogEntries.length" class="empty-mini">
          <AppIcon name="history" :size="22" />
          <div><p>Todavía no hay novedades publicadas.</p></div>
        </div>
        <ul v-else class="changelog-list">
          <li
            v-for="c in changelogEntries" :key="c.id" class="changelog-item" role="button" tabindex="0"
            @click="newsModal = { icon: c.icon || 'sparkles', title: c.title, desc: c.body, feats: c.features, image: c.image_url, date: fmtDate(c.published_at || c.created_at) }"
            @keydown.enter="newsModal = { icon: c.icon || 'sparkles', title: c.title, desc: c.body, feats: c.features, image: c.image_url, date: fmtDate(c.published_at || c.created_at) }"
          >
            <img v-if="c.image_url" class="changelog-thumb" :src="c.image_url" alt="" />
            <span v-else class="roadmap-ico"><AppIcon :name="c.icon || 'sparkles'" :size="15" /></span>
            <span class="changelog-date">{{ fmtDate(c.published_at || c.created_at) }}</span>
            <div class="changelog-text">
              <strong>{{ c.title }}</strong>
              <p class="changelog-body">{{ c.summary || c.body }}</p>
            </div>
            <AppIcon name="chevron-right" :size="14" class="roadmap-arrow" />
          </li>
        </ul>
      </div>

      <div class="card">
        <h2 class="roadmap-title">Próximamente</h2>
        <p class="roadmap-sub">En lo que estamos trabajando para tu tienda.</p>
        <ul class="roadmap-list">
          <li
            v-for="r in roadmapItems" :key="r.id" class="roadmap-item" role="button" tabindex="0"
            @click="newsModal = { icon: r.icon || 'sparkles', title: r.title, desc: r.body, feats: r.features, image: r.image_url }"
            @keydown.enter="newsModal = { icon: r.icon || 'sparkles', title: r.title, desc: r.body, feats: r.features, image: r.image_url }"
          >
            <img v-if="r.image_url" class="roadmap-thumb" :src="r.image_url" alt="" />
            <span v-else class="roadmap-ico"><AppIcon :name="r.icon || 'sparkles'" :size="15" /></span>
            <span class="roadmap-item-txt"><strong>{{ r.title }}</strong><small>{{ r.summary || r.body }}</small></span>
            <AppIcon name="chevron-right" :size="14" class="roadmap-arrow" />
          </li>
        </ul>
      </div>

      <!-- Detalle de la novedad en modal: título, descripción completa y
           el listado de todo lo que incluye. -->
      <Teleport to="body">
        <Transition name="pf">
          <div v-if="newsModal" class="pf-overlay" @click.self="newsModal = null">
            <div class="news-modal" role="dialog" aria-modal="true" :aria-label="newsModal.title">
              <button type="button" class="news-modal-close" aria-label="Cerrar" @click="newsModal = null"><AppIcon name="x" :size="16" /></button>
              <div class="news-modal-body">
                <div class="news-modal-head-row">
                  <span class="news-modal-ico"><AppIcon :name="newsModal.icon" :size="20" /></span>
                  <span class="news-modal-chip">{{ newsModal.date || 'Próximamente' }}</span>
                </div>
                <h3 class="news-modal-title">{{ newsModal.title }}</h3>
                <p class="news-modal-desc">{{ newsModal.desc }}</p>
                <img v-if="newsModal.image" class="news-modal-fig" :src="newsModal.image" alt="" />
                <div v-if="newsModal.feats?.length" class="news-modal-includes">
                  <h4>Qué incluye</h4>
                  <ul>
                    <li v-for="f in newsModal.feats" :key="f"><AppIcon name="check" :size="14" />{{ f }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>
    </div>

    <div v-if="seen.settings" v-show="section === 'settings'" class="acc-sec" :class="{ 'sec-on': section === 'settings' }">
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
            <AppInput v-model="accountForm.phone" label="Número de celular" name="acc_phone" type="tel" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" required :error="accountFieldErr('phone')" @blur="accountTouched.phone = true" />
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
      v-if="!chatDockHidden"
      :content="chatDockContent"
      :online="chatStaffOnline"
      :unread="chatUnread"
      :minimized="chatMin"
      label="Tu Asistente"
      dismissible
      @toggle="onDockToggle"
      @dismiss="hideChatDock"
    >
      <!-- Panel de contactos: el asistente automático figura como un
           integrante más del equipo. -->
      <div v-if="chatDockPanel" class="chat-dock-panel">
        <div class="chat-threads-head">
          <h3><AppIcon name="message-circle" :size="16" /> Tu Asistente</h3>
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
              <strong>{{ chatPeer?.name || 'Tu Asistente' }}</strong>
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
              </template>
              <template v-else>
                <p v-if="!chatMessages.length" class="chat-empty">
                  Preguntale a Tu Asistente por tu plan, tu tienda, tus productos, visitas, pagos o facturas.
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

    <!-- Guía de primera vez: robot + globo que presenta la burbuja de chat
         (solo escritorio, 5s, una vez por sesión). -->
    <RobotGuide :active="!chatDockHidden && !chatDockContent" />

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

    <!-- Confirmación de acciones destructivas -->
    <div v-if="confirmDlg.open" class="dsg-confirm" role="presentation" @keydown.esc="resolveConfirm(false)">
      <div class="dsg-confirm-box" role="alertdialog" aria-modal="true" :aria-label="confirmDlg.title">
        <h3>{{ confirmDlg.title }}</h3>
        <p v-if="confirmDlg.desc">{{ confirmDlg.desc }}</p>
        <div class="dsg-confirm-actions">
          <button type="button" class="btn ghost btn-auto" ref="confirmStay" @click="resolveConfirm(false)">Cancelar</button>
          <button type="button" class="btn btn-auto" :class="{ danger: confirmDlg.danger }" @click="resolveConfirm(true)">{{ confirmDlg.confirmLabel }}</button>
        </div>
      </div>
    </div>
    <TourGuide v-model:open="tourOpen" />

    <!-- Asistencia con IA: mismo asistente para Diseño y Mi negocio -->
    <Teleport to="body">
      <AiAssistOptIn v-if="aiOptInOpen" @done="aiOptInOpen = false" />
      <AiAssistModal
        v-if="assistOpen"
        :origin="assistOrigin"
        :plan="plan"
        @close="assistOpen = false"
        @applied="onAssistApplied"
        @navigate="assistOpen = false; section = $event"
      />
      <PriceUpdateModal v-if="showPriceUpdate" @close="showPriceUpdate = false" />

      <!-- Drawer del formulario de producto: se abre desde "Cargar producto",
           editar o duplicar; el inventario queda siempre a ancho completo. -->
      <Transition name="pf">
        <div v-if="productFormOpen" class="pf-overlay" @click.self="closeProductForm">
          <div class="pf-drawer" role="dialog" aria-modal="true" :aria-label="productEditing ? 'Editar producto' : 'Agregar un producto'">
            <header class="pf-drawer-head">
              <div class="pf-drawer-title">
                <span class="pf-drawer-ico"><AppIcon :name="productEditing ? 'pencil' : 'plus'" :size="17" /></span>
                <h3>{{ productEditing ? 'Editar producto' : 'Agregar un producto' }}</h3>
              </div>
              <button type="button" class="icon-btn" aria-label="Cerrar" @click="closeProductForm"><AppIcon name="x" :size="16" /></button>
            </header>
            <div class="pf-drawer-body">
              <ProductForm
                :form="productForm" :touched="productTouched" :features="productFeatures"
                :categories="catalog.categories" :brands="catalog.brands"
                :editing="Boolean(productEditing)" :busy="productBusy"
                :legacy-offer="legacyOffer" :offer-cleared="offerCleared"
                :image-preview="productImagePreview" :image-err="productImageErr"
                :has-image="Boolean(productImage)" :has-original="Boolean(productOriginal)" :bg-busy="productBgBusy"
                :accept="LOGO_ACCEPT_TYPES" :feature-limit="FEATURE_LIMITS.entriesMax"
                :features-err="featuresErr" :field-err="productFieldErr"
                :stock-enabled="hasStockControl"
                @save="saveProduct" @cancel="closeProductForm"
                @pick-image="onProductImagePicked" @remove-bg="removeProductBg"
                @restore-original="restoreProductOriginal"
                @clear-image="productImage = null; productOriginal = null; productImagePreview = ''; productImageCleared = true"
                @clear-offer="offerCleared = true"
                @add-feature="addFeatureRow" @remove-feature="removeFeatureRow"
              />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

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
