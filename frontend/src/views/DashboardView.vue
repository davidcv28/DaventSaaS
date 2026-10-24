<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useBillingStore } from '../stores/billing.store.js'
import { usePaymentsStore } from '../stores/payments.store.js'
import { useInvoicesStore } from '../stores/invoices.store.js'
import { useStoreStore } from '../stores/store.store.js'
import { useCatalogStore } from '../stores/catalog.store.js'
import { useSlugCheck } from '../composables/useSlugCheck.js'
import QRCode from 'qrcode'
import {
  normalizeSlug, publicStoreUrl,
  CUSTOMIZATION_DEFAULTS, STORE_ACCENTS, STORE_THEMES, STORE_TEMPLATES, STORE_FONTS, storeThemeVars, storeFontFamily,
  allowedTemplatesFor, resolveStoreTemplate,
  ensureStoreFont, ensureStoreFontList, NAME_FONT_SIZE_MIN, NAME_FONT_SIZE_MAX,
  validateDisplayName, validateHeadline, validateDescription,
  validateAboutTitle, validateAboutText, validateAboutYears, validateAboutMission, validateAboutSpecialties,
  validateContactEmail,
  validateWhatsapp, validateInstagram, validateTiktok, validateFacebook,
  normalizeWhatsapp, normalizeInstagram, normalizeTiktok, normalizeFacebook,
  validateLogoFile, validateImageFile, LOGO_ACCEPT, CAROUSEL_MAX_IMAGES, DECOR_MAX_IMAGES, formatStorageMB,
  CHATBOT_DEFAULTS, CHATBOT_QA_MAX,
  MARKETING_LIMITS, SERVICE_ICONS, SECTION_ORDER_LABELS, resolveSectionOrder,
  validateSectionTitle, validateCtaTitle, validateCtaText, validateCtaLabel
} from '../api/stores.api.js'
import {
  validateTaxonomyName, validateProductName, validateProductPrice, validateProductOffer, validateProductDescription,
  catalogApi, FEATURE_LIMITS, parseFeatureSchema, validateFeatureSchema, validateProductFeatures
} from '../api/catalog.api.js'
import { formatARS } from '../api/billing.api.js'
import { formatDate as formatInvDate } from '../api/invoices.api.js'
import { paymentStatusMeta, formatDateTime, MONTH_NAMES } from '../api/payments.api.js'
import { locationsApi } from '../api/locations.api.js'
import { authApi } from '../api/auth.api.js'
import { sendVerificationSms, confirmSmsCode } from '../api/phone-verify.js'
import { env, storeSubdomains, firebaseEnabled } from '../config/env.js'
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
import StorageMeter from '../components/StorageMeter.vue'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const billing = useBillingStore()
const payments = usePaymentsStore()
const invoices = useInvoicesStore()
const store = useStoreStore()
const catalog = useCatalogStore()

// Sección activa con setter validado: un botón interno (o una sección que
// desaparece del menú cuando vence el plan) jamás deja una vista vacía.
const sectionInner = ref('overview')
const section = computed({
  get: () => sectionInner.value,
  set: (id) => { sectionInner.value = navItems.value.some((i) => i.id === id) ? id : 'overview' }
})
const busyPlan = ref(null)
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

// --- Verificación de celular (SMS de Firebase — gratis, ancla anti-abuso) ---
// Flujo: sendVerificationSms dispara el SMS de Firebase -> el usuario carga
// el código -> confirmSmsCode devuelve el idToken -> el backend lo valida
// contra Identity Toolkit y marca phone_verified si el número coincide.
const phoneVerifyBusy = ref(false)
const phoneVerifyErr = ref('')
const phoneVerifySent = ref(false)
const phoneVerifyCode = ref('')
const recaptchaEl = ref(null)
let confirmationResult = null
const phoneVerified = computed(() => auth.user?.profile?.phone_verified === true)
const hasPhone = computed(() => Boolean(auth.user?.profile?.phone))

async function startPhoneVerify() {
  phoneVerifyBusy.value = true
  phoneVerifyErr.value = ''
  try {
    confirmationResult = await sendVerificationSms(auth.user.profile.phone, recaptchaEl.value)
    phoneVerifySent.value = true
    phoneVerifyCode.value = ''
  } catch (e) {
    phoneVerifyErr.value = 'No se pudo enviar el SMS. Reintentá en unos minutos.'
  } finally {
    phoneVerifyBusy.value = false
  }
}
async function confirmPhoneVerify() {
  if (!confirmationResult || !phoneVerifyCode.value.trim()) return
  phoneVerifyBusy.value = true
  phoneVerifyErr.value = ''
  try {
    const idToken = await confirmSmsCode(confirmationResult, phoneVerifyCode.value.trim())
    await authApi.confirmPhoneVerification(idToken)
    if (auth.user?.profile) auth.user.profile.phone_verified = true
    phoneVerifySent.value = false
    phoneVerifyCode.value = ''
  } catch (e) {
    phoneVerifyErr.value = e.response?.status === 429
      ? 'Demasiados intentos. Esperá un rato y probá de nuevo.'
      : e.response?.data?.detail || 'El código no es válido o ya venció. Pedí un SMS nuevo.'
  } finally {
    phoneVerifyBusy.value = false
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

// Menú del sidebar: el staff ve además la entrada al panel de administración.
// Sin acceso vigente (is_current = grants_access del backend: suscripción
// activa dentro de vigencia + gracia) solo quedan las secciones de cuenta;
// catálogos, diseño, empresa, POS y el grupo Avanzado desaparecen. Dentro
// del acceso, "Diseño web"/"Mi empresa" piden has_customization (todos los
// planes). Estadísticas/QR-folletos van por flag propio; has_advanced_menu
// (Premium) solo decide si se agrupan bajo el heading "Avanzado".
const navItems = computed(() => {
  const b = plan.value?.benefits || {}
  const hasAccess = Boolean(plan.value?.isCurrent)
  const items = [
    { id: 'overview', label: 'Resumen', icon: 'dashboard' },
    { id: 'store', label: 'Mi tienda', icon: 'store' }
  ]
  if (hasAccess) {
    items.push({ id: 'catalogs', label: 'Mis catálogos', icon: 'library' })
    if (b.has_customization) items.push({ id: 'design', label: 'Diseño web', icon: 'palette' })
    if (b.has_customization) items.push({ id: 'company', label: 'Mi empresa', icon: 'building-2' })
    items.push({ id: 'pos', label: 'Venta en persona', icon: 'monitor' })
    if (b.has_chatbot) items.push({ id: 'bot', label: 'Chatbot', icon: 'bot' })
    const advanced = []
    if (b.has_stats) advanced.push({ id: 'stats', label: 'Estadísticas', icon: 'trending-up' })
    if (b.has_qr || b.has_flyers) advanced.push({ id: 'tools', label: 'QR y folletos', icon: 'qr-code' })
    // Con has_advanced_menu (Premium) van agrupados; si no, aparecen sueltos
    // según su flag propio (Básico tiene stats; Estándar stats + QR/folletos).
    if (b.has_advanced_menu && advanced.length) {
      items.push({ heading: 'Avanzado' }, ...advanced)
    } else {
      items.push(...advanced)
    }
  }
  items.push(
    { id: 'plans', label: 'Planes', icon: 'credit-card' },
    { id: 'payments', label: 'Pagos', icon: 'receipt' },
    { id: 'invoices', label: 'Facturas', icon: 'file-text' },
    { id: 'settings', label: 'Cuenta', icon: 'user' }
  )
  return items
})

// Si la sección activa desaparece del menú (venció el plan), volver a Resumen.
watch(navItems, (items) => {
  if (!items.some((i) => i.id === section.value)) section.value = 'overview'
})

function onNavigate(id) {
  section.value = id
}
const business = computed(() => auth.user?.profile?.business_name || '')
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
  { title: 'Reservá tu link público', text: 'Es la dirección de tu tienda.', done: store.hasStore },
  { title: 'Elegí un plan', text: 'Definí el tamaño de tu catálogo.', done: billing.hasSubscription },
  { title: 'Cargá tus productos', text: 'Sumá fotos, precios y stock.', done: catalog.products.length > 0 },
  { title: 'Compartí tu link público', text: 'Enviáselo a tus clientes.', done: false }
])

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

// --- Mis catálogos: productos, categorías y marcas de la tienda ---
// El catálogo se habilita con suscripción activa (el backend devuelve 403 sin plan).
const catalogTab = ref('products') // products | categories | brands
const catalogLoaded = ref(false)

// El interruptor del catálogo público (customization.show_catalog) y el
// carrusel de portada viven en esta misma sección, en la tarjeta "Tu
// página de catálogo": el dueño controla el catálogo por separado del
// diseño general de su web.

const productForm = reactive({ name: '', price: '', offer_price: '', category: '', brand: '', description: '', is_active: true })
const productTouched = reactive({})
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
  // catálogo se trae en un único <link> para previsualizar cada opción.
  if (s === 'design') {
    ensureStoreFont(designForm.name_font)
    ensureStoreFontList()
  }
  if (s === 'bot') ensureBot()
  if (s === 'stats' && canStats.value) store.loadStats()
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
  const o = validateProductOffer(productForm.offer_price, productForm.price)
  const d = validateProductDescription(productForm.description.trim())
  if (n) e.name = n
  if (p) e.price = p
  if (o) e.offer_price = o
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
  Object.assign(productForm, { name: '', price: '', offer_price: '', category: '', brand: '', description: '', is_active: true })
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
    name: p.name, price: p.price, offer_price: p.offer_price ?? '', category: p.category || '', brand: p.brand || '',
    description: p.description || '', is_active: p.is_active
  })
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
      // '' viaja como vacío y el backend lo mapea a None (quita la oferta).
      offer_price: productForm.offer_price,
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

function openFlyer() {
  const href = router.resolve({ name: 'store-flyer' }).href
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
// los planes; el backend lo fuerza en PATCH). Fuente, tamaño, acento y
// carrusel son premium (has_design_advanced): fuente/tamaño/acento se ven
// bloqueados y el carrusel directamente no se muestra.
// Las listas se inicializan frescas: el spread compartiría las instancias
// de CUSTOMIZATION_DEFAULTS y editarlas antes de que llegue la tienda
// ensuciaría los defaults del módulo.
const designForm = reactive({ ...CUSTOMIZATION_DEFAULTS, services: [], stats: [], testimonials: [], faqs: [], hours: [], section_order: [] })
const designTouched = reactive({})
const designBusy = ref(false)
const designTab = ref('content')
const designTabs = [
  { id: 'content', label: 'Contenido', icon: 'pencil' },
  { id: 'look', label: 'Apariencia', icon: 'palette' },
  { id: 'images', label: 'Imágenes', icon: 'images' },
  { id: 'sections', label: 'Secciones', icon: 'layout-grid' }
]
const canCustomize = computed(() => Boolean(plan.value?.benefits?.has_customization))
const canDesignAdvanced = computed(() => Boolean(plan.value?.benefits?.has_design_advanced))
const canLocationMap = computed(() => Boolean(plan.value?.benefits?.has_location_map))
const businessInitial = computed(() => (business.value || 'T').slice(0, 1).toUpperCase())
const designPreviewVars = computed(() => storeThemeVars(designForm))
const storeAccents = STORE_ACCENTS
const storeThemes = STORE_THEMES
// Diseños de la web (STORE_TEMPLATES): cada plantilla declara su tier
// ('base' | 'plus' | 'advanced'). La vista previa usa el mismo fallback
// que la web pública: 'classic' si el diseño queda fuera del plan.
const storeTemplates = STORE_TEMPLATES
// Plantillas elegibles por nivel de plan (espejo del backend): Básico
// elige base, Estándar suma 'plus' y Premium todo el catálogo.
const allowedTemplates = computed(() => allowedTemplatesFor(plan.value?.benefits || {}))
const designTemplate = computed(() => resolveStoreTemplate(designForm.template, allowedTemplates.value))
// Si el guardado quedó fuera del nivel (baja de plan o plantilla retirada
// como 'atelier') el select vuelve al primer diseño permitido.
watch(allowedTemplates, (list) => {
  if (!list.includes(designForm.template)) designForm.template = list[0] || 'classic'
})
function templatePlanLabel(key) {
  const tier = STORE_TEMPLATES[key]?.tier
  return tier === 'plus' ? 'Estándar' : tier === 'advanced' ? 'Premium' : ''
}
function pickTemplate(key) {
  if (allowedTemplates.value.includes(key)) designForm.template = key
}
function pickFont(key) {
  if (canDesignAdvanced.value) designForm.name_font = key
}
function pickAccent(key) {
  if (canDesignAdvanced.value) designForm.accent = key
}

// Precarga el diseño guardado cuando llega la tienda (customization anidada).
watch(() => store.store, (s) => {
  if (!s) return
  Object.assign(designForm, store.customization)
  // Si el plan ya estaba cargado y el diseño guardado quedó fuera de su
  // nivel (baja de plan o plantilla retirada), vuelve al primero permitido.
  if (!allowedTemplates.value.includes(designForm.template)) designForm.template = allowedTemplates.value[0] || 'classic'
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
const sectionLabels = SECTION_ORDER_LABELS

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
  { id: 'mk-hours', label: 'Horarios' },
  { id: 'mk-cta', label: 'Llamado a la acción' },
  { id: 'mk-order', label: 'Orden' }
]
function scrollToCard(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function saveCompany() {
  COMPANY_FIELDS.forEach((k) => { designTouched[k] = true })
  if (COMPANY_FIELDS.some((k) => designErrors.value[k])) return
  companyBusy.value = true
  const years = designForm.about_years
  await store.saveCustomization({
    about_title: designForm.about_title.trim(),
    about_text: designForm.about_text.trim(),
    about_years: years === '' || years === null || years === undefined ? null : Number(years),
    about_mission: designForm.about_mission.trim(),
    about_specialties: designForm.about_specialties.trim()
  })
  companyBusy.value = false
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

// Orden de las secciones de la portada: claves cerradas espejo del backend
// (resolveSectionOrder descarta desconocidas y completa las faltantes);
// la web lo aplica como CSS order. Hero primero y Contáctanos último siempre.
const sectionOrderList = computed(() => resolveSectionOrder(designForm.section_order))
function moveSection(key, direction) {
  const order = [...sectionOrderList.value]
  const index = order.indexOf(key)
  const target = index + direction
  if (index < 0 || target < 0 || target >= order.length) return
  ;[order[index], order[target]] = [order[target], order[index]]
  designForm.section_order = order
}
async function saveSectionOrder() {
  companyBusy.value = true
  await store.saveCustomization({ section_order: sectionOrderList.value })
  companyBusy.value = false
}

async function saveDesign() {
  Object.keys(designForm).forEach((k) => { designTouched[k] = true })
  if (Object.keys(designErrors.value).some((k) => !COMPANY_FIELDS.includes(k))) return
  designBusy.value = true
  const payload = {
    display_name: designForm.display_name.trim(),
    headline: designForm.headline.trim(),
    description: designForm.description.trim(),
    show_about: Boolean(designForm.show_about),
    show_gallery: Boolean(designForm.show_gallery),
    contact_email: designForm.contact_email.trim(),
    show_contact: Boolean(designForm.show_contact),
    theme: designForm.theme,
    whatsapp: normalizeWhatsapp(designForm.whatsapp),
    instagram: normalizeInstagram(designForm.instagram),
    tiktok: normalizeTiktok(designForm.tiktok),
    facebook: normalizeFacebook(designForm.facebook)
  }
  // Sin has_design_advanced no se envían las opciones premium (el backend las descartaría igual).
  if (canDesignAdvanced.value) {
    Object.assign(payload, {
      name_font: designForm.name_font,
      name_font_size: Number(designForm.name_font_size),
      accent: designForm.accent
    })
  }
  // La plantilla viaja siempre: el backend la descarta del payload si
  // quedó fuera del nivel del plan (allowed_templates_of).
  payload.template = designForm.template
  // El mapa tiene beneficio propio (has_location_map: Estándar y Premium).
  if (canLocationMap.value) payload.show_location = Boolean(designForm.show_location)
  await store.saveCustomization(payload)
  designBusy.value = false
}

// La página Catálogo se controla desde "Mis catálogos" (tarjeta "Tu
// página de catálogo"), separada del diseño general: el interruptor
// guarda show_catalog al instante con su propio PATCH.
const catalogPageBusy = ref(false)
async function toggleCatalogPage() {
  if (catalogPageBusy.value) return
  catalogPageBusy.value = true
  const ok = await store.saveCustomization({ show_catalog: Boolean(designForm.show_catalog) })
  if (!ok) designForm.show_catalog = store.customization?.show_catalog !== false
  catalogPageBusy.value = false
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
const storeFonts = STORE_FONTS
const fontSizeMin = NAME_FONT_SIZE_MIN
const fontSizeMax = NAME_FONT_SIZE_MAX
const designShopName = computed(() => designForm.display_name || business.value || 'Tu negocio')
// Espejo del catálogo público (se apaga desde "Mi catálogo"): la vista previa
// oculta el link, el CTA y la página Catálogo igual que la web real.
const designCatalogOn = computed(() => designForm.show_catalog !== false)
const designNameFont = computed(() => ({ fontFamily: storeFontFamily(designForm.name_font) }))

// Si cambia la fuente elegida, traerla en el momento (la lista ya las carga
// todas al entrar a Diseño; esto cubre selecciones previas al primer ingreso).
watch(() => designForm.name_font, (f) => ensureStoreFont(f))

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

// Logo de la web pública (has_customization): sube directo a R2 vía /stores/customization/logo/.
// Consume la cuota del beneficio max_storage_mb; el backend devuelve `storage` actualizado.
const logoInput = ref(null)
const logoBusy = ref(false)
const logoErr = ref('')
const LOGO_ACCEPT_TYPES = LOGO_ACCEPT

const currentLogo = computed(() => store.customization.logo || '')
const storageText = computed(() => {
  const s = store.storage
  if (!s) return ''
  const used = formatStorageMB(s.used_bytes)
  return s.max_mb === null
    ? `Usás ${used} MB de almacenamiento de imágenes`
    : `Usás ${used} MB de ${s.max_mb} MB de almacenamiento de imágenes`
})

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

// Imagen de portada (premium, has_design_advanced): fondo del hero de la web.
// Comparte cuota con logo/galería; el backend la normaliza a WebP.
const coverInput = ref(null)
const coverBusy = ref(false)
const coverErr = ref('')
const currentCover = computed(() => store.customization.cover || '')

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
  await auth.fetchMe()
  fillAccountForm()
  loadAccountProvinces()
  if (store.status === 'idle') store.loadMine()
  await Promise.all([billing.loadPlans(), billing.loadMine(), payments.loadPayments(), invoices.loadInvoices()])
  if (canStats.value) store.loadStats()
  // Precarga silenciosa del catálogo para los próximos pasos del resumen.
  ensureCatalog()
  // Primero el retorno del checkout (trae payment_id en la URL): es la vía instantánea.
  await handlePaymentReturn()
  // Red de seguridad: registra pagos ya acreditados en MP que aún no estén en el sistema.
  const synced = await payments.sync()
  if (synced > 0) await Promise.all([billing.loadMine(), payments.loadPayments()])
  // Puente entre pestañas: el retorno de MP cae en la pestaña del checkout,
  // esta escucha avisa a la pestaña original para acreditar al instante.
  window.addEventListener('storage', onPaymentBroadcast)
})

watch(() => carouselImages.value.length, (total) => {
  previewSlide.value = 0
  clearInterval(previewTimer)
  previewTimer = null
  if (total > 1 && !previewReduceMotion) {
    previewTimer = setInterval(() => { previewSlide.value = (previewSlide.value + 1) % carouselImages.value.length }, 3000)
  }
})

onUnmounted(() => {
  stopCheckoutWatch()
  clearInterval(previewTimer)
  window.removeEventListener('storage', onPaymentBroadcast)
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
      return
    }
    checkoutTab.location.href = url
    billing.notice = 'Abrimos Mercado Pago en otra pestaña. Cuando el pago se acredite, tu plan se activa solo.'
    startCheckoutWatch(p.id)
  } finally {
    busyPlan.value = null
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
    :active="section"
    :items="navItems"
    :plan-name="plan?.name || ''"
    :user-name="displayName"
    :initial="initial"
    @navigate="onNavigate"
    @logout="logout"
  >
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
          <p v-if="plan.isTrial" class="hero-pending">Plan de prueba: al terminar el día de prueba tenés que elegir un plan para seguir publicado.</p>
          <p v-if="billing.subscription?.pending_plan_name" class="hero-pending">Cambio a {{ billing.subscription.pending_plan_name }} pendiente: se aplica cuando se acredite el pago.</p>
          <p v-if="plan.autoRenew" class="hero-pending"><AppIcon name="refresh" :size="14" /> Débito automático activo: se renueva el {{ fmtDate(plan.end) }}.</p>
          <p v-else-if="plan.cancelledAt" class="hero-pending"><AppIcon name="calendar" :size="14" /> Renovación automática desactivada: tu plan termina el {{ fmtDate(plan.end) }}.</p>
        </div>
        <div class="hero-side">
          <span v-if="plan.isCurrent" class="badge-ok"><AppIcon name="dot" :size="12" /> {{ plan.status }}</span>
          <span v-else-if="plan.status === 'Pendiente de pago'" class="badge-warn"><AppIcon name="dot" :size="12" /> {{ plan.status }}</span>
          <span v-else class="badge-danger"><AppIcon name="dot" :size="12" /> Vencida</span>
          <div class="hero-price-wrap">
            <strong class="hero-price">{{ formatARS(plan.price) }}</strong>
            <span v-if="Number(plan.price) > 0">por mes</span>
          </div>
          <button class="btn secondary btn-auto" @click="section = 'plans'">{{ plan.isTrial ? 'Ver planes' : 'Cambiar plan' }}</button>
          <button v-if="plan.autoRenew" class="btn secondary btn-auto" :disabled="renewBusy" @click="confirmCancel = true">Cancelar renovación</button>
          <button v-else-if="!plan.isTrial" class="btn secondary btn-auto" :disabled="renewBusy" @click="activateAutoRenew"><AppIcon name="refresh" :size="16" /> Activar débito automático</button>
        </div>
      </div>

      <div v-if="confirmCancel" class="card confirm-card">
        <h3><AppIcon name="triangle-alert" :size="18" /> Cancelar la renovación automática</h3>
        <p>Vas a dejar de pagar el débito mensual. Tu plan sigue vigente hasta el <strong>{{ fmtDate(plan?.end) }}</strong>; después tu web pública y tu catálogo se desactivan. Podés reactivar el débito cuando quieras.</p>
        <div class="btn-row">
          <button class="btn danger btn-auto" :disabled="renewBusy" @click="doCancelRenewal"><span v-if="renewBusy" class="spinner"></span>Sí, cancelar la renovación</button>
          <button class="btn ghost btn-auto" :disabled="renewBusy" @click="confirmCancel = false">Mantener activa</button>
        </div>
      </div>

      <AlertMessage v-if="plan && !plan.isCurrent && plan.status !== 'Pendiente de pago'" kind="warn" message="Tu suscripción venció: tu web pública está pausada. Elegí un plan para reactivarla." />
      <AlertMessage v-else-if="inGrace" kind="warn" message="Todavía no pudimos cobrar la renovación: Mercado Pago reintenta el débito durante unos días y tu plan sigue activo mientras tanto." />

      <div v-if="billing.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu suscripción…</p></div>
      <AlertMessage v-if="billing.notice" kind="success" :message="billing.notice" />
      <AlertMessage v-if="billing.lastError" kind="error" :message="billing.lastError" />
      <AlertMessage v-if="payments.notice" kind="success" :message="payments.notice" />
      <AlertMessage v-if="payments.lastError" kind="error" :message="payments.lastError" />

      <div class="stats">
        <div class="stat"><span class="stat-icon"><AppIcon name="package" :size="20" /></span><div><strong>0</strong><small>Productos</small></div></div>
        <div class="stat"><span class="stat-icon"><AppIcon name="eye" :size="20" /></span><div><strong>{{ canStats ? (store.visitStats?.total ?? '0') : '—' }}</strong><small>{{ canStats ? 'Visitas totales' : 'Visitas' }}</small></div></div>
        <div class="stat"><span class="stat-icon"><AppIcon name="clock" :size="20" /></span><div><strong>{{ plan?.remaining ?? '—' }}</strong><small>Días restantes</small></div></div>
      </div>

      <div v-if="store.hasStore" class="card">
        <h3><AppIcon name="image" :size="18" /> Almacenamiento</h3>
        <StorageMeter />
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
    <div v-show="section === 'catalogs'" :class="{ 'sec-on': section === 'catalogs' }">
      <div class="page-head">
        <div>
          <h1>Mi catálogo</h1>
          <p>{{ billing.hasSubscription ? productsCountText : catalogLimit }}</p>
        </div>
        <button class="btn ghost btn-auto" @click="catalog.loadAll()"><AppIcon name="refresh" :size="16" /> Recargar</button>
      </div>

      <AlertMessage v-if="catalog.notice" kind="success" :message="catalog.notice" />
      <AlertMessage v-if="catalog.lastError" kind="error" :message="catalog.lastError" />
      <AlertMessage kind="info" message="Publicá únicamente imágenes, logos y textos propios o con autorización de uso: sos responsable del contenido de tu catálogo." />

      <template v-if="!billing.hasSubscription || catalog.denied">
        <div class="empty">
          <span class="empty-icon"><AppIcon name="library" :size="28" /></span>
          <h3>Necesitás una suscripción</h3>
          <p>El catálogo (productos, categorías y marcas de tu página pública) se habilita con un plan activo.</p>
          <button class="btn btn-auto" @click="section = 'plans'">Ver planes</button>
        </div>
      </template>

      <template v-else>
        <div class="card">
          <h3><AppIcon name="store" :size="18" /> Tu página de catálogo</h3>
          <p>Tu catálogo tiene su propia página pública. Acá controlás su visibilidad y su carrusel de portada, por separado del diseño general de tu web.</p>
          <label class="check-item">
            <input v-model="designForm.show_catalog" type="checkbox" :disabled="catalogPageBusy" @change="toggleCatalogPage" />
            <span class="check-text">
              <strong>Página Catálogo <span v-if="catalogPageBusy" class="spinner spinner-brand" aria-hidden="true"></span></strong>
              <small>Tus productos a la vista. Apagala para usar tu web solo como vidriera del negocio.</small>
            </span>
          </label>
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
        </div>

        <div class="tabs">
          <button type="button" class="tab" :class="{ active: catalogTab === 'products' }" @click="catalogTab = 'products'">
            <AppIcon name="package" :size="16" /> Productos
          </button>
          <button type="button" class="tab" :class="{ active: catalogTab === 'categories' }" @click="catalogTab = 'categories'">
            <AppIcon name="layout-grid" :size="16" /> Categorías
          </button>
          <button type="button" class="tab" :class="{ active: catalogTab === 'brands' }" @click="catalogTab = 'brands'">
            <AppIcon name="tag" :size="16" /> Marcas
          </button>
        </div>

        <div v-if="catalog.status === 'loading'" class="card card-loading"><span class="spinner spinner-brand"></span><p>Cargando tu catálogo…</p></div>

        <template v-else>
          <!-- -------- Productos -------- -->
          <div v-show="catalogTab === 'products'" class="grid-2">
            <div class="card">
              <h3><AppIcon name="pencil" :size="18" /> {{ productEditing ? 'Editar producto' : 'Nuevo producto' }}</h3>
              <AppInput v-model="productForm.name" label="Nombre" name="prod_name" placeholder="Ej. Remera oversize" :error="productFieldErr('name')" @blur="productTouched.name = true" />
              <div class="grid-2">
                <AppInput v-model="productForm.price" label="Precio" name="prod_price" type="number" min="0" step="0.01" placeholder="0.00" :error="productFieldErr('price')" @blur="productTouched.price = true" />
                <AppInput v-model="productForm.offer_price" label="Precio de oferta" name="prod_offer" type="number" min="0" step="0.01" placeholder="Opcional" hint="Si es menor que el precio, tu web lo muestra tachado con el descuento." :error="productFieldErr('offer_price')" @blur="productTouched.offer_price = true" />
              </div>
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
                <p class="hint">PNG, JPG, WebP o GIF de hasta 4 MB. Ajustamos la imagen automáticamente; con «Quitar fondo» lo reemplazamos por blanco y centramos el producto. Consume tu cuota de almacenamiento.</p>
                <p v-if="productImageErr" class="field-error" role="alert">{{ productImageErr }}</p>
              </div>
              <div class="btn-row">
                <AppButton :loading="productBusy" @click="saveProduct">{{ productEditing ? 'Guardar cambios' : 'Publicar producto' }}</AppButton>
                <button v-if="productEditing" type="button" class="btn ghost btn-auto" @click="resetProductForm">Cancelar</button>
              </div>
            </div>

            <div class="card">
              <h3><AppIcon name="package" :size="18" /> Tus productos</h3>
              <StorageMeter />
              <p v-if="!catalog.products.length" class="hint">Todavía no cargaste productos. Completá el formulario para publicar el primero.</p>
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
                    <small><template v-if="p.offer_price != null"><s class="prod-old">{{ formatARS(p.price) }}</s> {{ formatARS(p.offer_price) }}</template><template v-else>{{ formatARS(p.price) }}</template><template v-if="p.category_name"> · {{ p.category_name }}</template><template v-if="p.brand_name"> · {{ p.brand_name }}</template></small>
                  </div>
                  <span v-if="p.offer_price != null" class="pill ok">Oferta</span>
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
        </template>
      </template>
    </div>
    <!-- ================= MI TIENDA ================= -->
    <div v-show="section === 'store'" :class="{ 'sec-on': section === 'store' }">
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
          <p>Logo, titular, descripción, colores y botones de contacto de tu página pública.</p>
          <AlertMessage v-if="!canCustomize" kind="info" message="La personalización de tu web está disponible en el Plan premium." />
          <div class="btn-row link-actions">
            <button class="btn btn-auto" @click="section = 'design'">
              <AppIcon :name="canCustomize ? 'pencil' : 'lock'" :size="16" /> {{ canCustomize ? 'Editar diseño' : 'Conocer el diseño web' }}
            </button>
          </div>
        </div>
      </template>
    </div>
    <!-- ================= DISEÑO WEB ================= -->
    <div v-show="section === 'design'" :class="{ 'sec-on': section === 'design' }">
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
        <div class="dsg-layout">
          <div class="dsg-main">
          <nav class="dsg-tabs" role="tablist" aria-label="Opciones de diseño">
            <button v-for="t in designTabs" :key="t.id" type="button" role="tab" class="dsg-tab" :class="{ active: designTab === t.id }" :aria-selected="designTab === t.id" @click="designTab = t.id">
              <AppIcon :name="t.icon" :size="15" /> {{ t.label }}
            </button>
          </nav>
          <div v-show="designTab === 'content'" class="card dsg-card">
            <h3><AppIcon name="pencil" :size="18" /> Contenido</h3>
            <AppInput v-model="designForm.display_name" label="Nombre visible" name="design_display_name" :placeholder="business || 'Tu negocio'" hint="El nombre que aparece junto a tu logo. Vacío: se usa tu nombre de negocio." :error="designFieldErr('display_name')" @blur="designTouched.display_name = true" />
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
            <div class="grid-2">
              <AppInput v-model="designForm.instagram" label="Instagram" name="design_instagram" placeholder="tu.negocio" hint="Solo el usuario, sin @." :error="designFieldErr('instagram')" @blur="designTouched.instagram = true" />
              <AppInput v-model="designForm.tiktok" label="TikTok" name="design_tiktok" placeholder="tu.negocio" hint="Solo el usuario, sin @." :error="designFieldErr('tiktok')" @blur="designTouched.tiktok = true" />
            </div>
            <AppInput v-model="designForm.facebook" label="Facebook" name="design_facebook" placeholder="tu.negocio o URL de tu página" hint="Nombre de tu página o pegá el link completo." :error="designFieldErr('facebook')" @blur="designTouched.facebook = true" />
            <AppInput v-model="designForm.contact_email" label="Email de contacto público" name="design_contact_email" type="email" placeholder="contacto@tunegocio.com" hint="A esta casilla llegan los mensajes del formulario Contáctanos. Vacío: se usa el email de tu cuenta." :error="designFieldErr('contact_email')" @blur="designTouched.contact_email = true" />
          </div>
          <div v-show="designTab === 'images'" class="card dsg-card">
            <h3><AppIcon name="images" :size="18" /> Imágenes</h3>
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
              <label id="design-sections-label">Secciones de tu web</label>
              <div class="check-list" role="group" aria-labelledby="design-sections-label">
                <label class="check-item">
                  <input v-model="designForm.show_about" type="checkbox" />
                  <span class="check-text">
                    <strong>Sobre nosotros</strong>
                    <small>Historia, especialidades y misión. El contenido se edita en "Mi empresa".</small>
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
          <div v-show="designTab === 'look'" class="card dsg-card">
            <h3><AppIcon name="palette" :size="18" /> Apariencia</h3>
            <div class="field">
              <label id="design-logo-label">Logo</label>
              <div class="logo-box">
                <span class="logo-thumb">
                  <img v-if="currentLogo" :src="currentLogo" alt="Logo de tu tienda" />
                  <AppIcon v-else name="image" :size="20" aria-hidden="true" />
                </span>
                <div class="logo-actions">
                  <input
                    ref="logoInput"
                    type="file"
                    class="sr-only"
                    :accept="LOGO_ACCEPT_TYPES"
                    aria-labelledby="design-logo-label"
                    @change="onLogoPicked"
                  />
                  <button type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="logoInput?.click()">
                    <span v-if="logoBusy" class="spinner" aria-hidden="true"></span>
                    <AppIcon v-else name="upload" :size="16" />
                    {{ currentLogo ? 'Cambiar logo' : 'Subir logo' }}
                  </button>
                  <button v-if="currentLogo" type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="onRemoveLogo">Quitar</button>
                </div>
              </div>
              <p class="hint">PNG, JPG, WebP o GIF de hasta 2 MB. Aparece en la barra superior y la portada de tu web.</p>
              <p v-if="storageText" class="hint">{{ storageText }}</p>
              <p v-if="logoErr" class="field-error" role="alert">{{ logoErr }}</p>
            </div>
            <div class="field" :class="{ locked: !canDesignAdvanced }">
              <label id="design-cover-label">Imagen de portada <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="cover-box">
                <span class="cover-thumb" :class="{ empty: !currentCover }">
                  <img v-if="currentCover" :src="currentCover" alt="Portada actual de tu web" />
                  <AppIcon v-else name="image" :size="22" aria-hidden="true" />
                </span>
                <div class="logo-actions">
                  <input ref="coverInput" type="file" class="sr-only" :accept="LOGO_ACCEPT_TYPES" aria-labelledby="design-cover-label" :disabled="!canDesignAdvanced" @change="onCoverPicked" />
                  <button type="button" class="btn ghost btn-auto" :disabled="coverBusy || !canDesignAdvanced" @click="coverInput?.click()">
                    <span v-if="coverBusy" class="spinner" aria-hidden="true"></span>
                    <AppIcon v-else name="upload" :size="16" />
                    {{ currentCover ? 'Cambiar portada' : 'Subir portada' }}
                  </button>
                  <button v-if="currentCover && canDesignAdvanced" type="button" class="btn ghost btn-auto" :disabled="coverBusy" @click="onRemoveCover">Quitar</button>
                </div>
              </div>
              <p class="hint">Foto de hasta 4 MB que decora el fondo de tu página principal. La ajustamos automáticamente; elegí una imagen apaisada y luminosa.</p>
              <p v-if="coverErr" class="field-error" role="alert">{{ coverErr }}</p>
            </div>
            <div class="field">
              <label for="design-template">Diseño de tu web</label>
              <select id="design-template" v-model="designForm.template" class="select">
                <option
                  v-for="(t, key) in storeTemplates" :key="key" :value="key"
                  :disabled="!allowedTemplates.includes(key)"
                >
                  {{ t.label }}<template v-if="!allowedTemplates.includes(key)"> · Plan {{ templatePlanLabel(key) }}</template>
                </option>
              </select>
              <div class="pick-strip tpl-thumbs" aria-label="Vista previa de cada diseño">
                <button
                  v-for="(t, key) in storeTemplates" :key="key" type="button"
                  class="tpl-thumb-btn" :class="{ active: designForm.template === key }"
                  :aria-disabled="!allowedTemplates.includes(key)"
                  :aria-pressed="designForm.template === key"
                  :title="allowedTemplates.includes(key) ? t.desc : `${t.label} · Plan ${templatePlanLabel(key)}`"
                  @click="pickTemplate(key)"
                >
                  <span class="tpl-thumb" :data-tpl="key" aria-hidden="true"><i></i></span>
                  <span class="tpl-thumb-name">{{ t.label }}</span>
                  <span v-if="!allowedTemplates.includes(key)" class="tpl-thumb-lock" aria-hidden="true"><AppIcon name="lock" :size="10" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="hint">Cambia la estructura completa de tu portada: podés alternar sin perder tu contenido. Los diseños bloqueados se habilitan subiendo de plan.</p>
            </div>
            <AlertMessage v-if="!canDesignAdvanced" kind="info" message="Las fuentes, el color de acento, la imagen de portada, el carrusel y las decoraciones se habilitan con el Plan premium. Los diseños Urbano y Publicidad vienen desde el Estándar." />
            <div v-if="!canDesignAdvanced" class="btn-row">
              <button type="button" class="btn ghost btn-auto" @click="section = 'plans'">Ver planes</button>
            </div>
            <div class="field" :class="{ locked: !canDesignAdvanced }">
              <label for="design-font">Fuente de tu web <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <select id="design-font" v-model="designForm.name_font" class="select" :disabled="!canDesignAdvanced">
                <option v-for="(f, key) in storeFonts" :key="key" :value="key" :style="{ fontFamily: f.family }">{{ f.label }}</option>
              </select>
              <div class="pick-strip font-chips" aria-label="Vista previa de cada fuente">
                <button
                  v-for="(f, key) in storeFonts" :key="key" type="button"
                  class="font-chip" :class="{ active: designForm.name_font === key }"
                  :style="{ fontFamily: f.family }"
                  :aria-disabled="!canDesignAdvanced"
                  :title="f.label"
                  @click="pickFont(key)"
                >{{ f.label }}</button>
              </div>
              <p class="hint">Se aplica a todo el texto de tu web: nombre, secciones y catálogo.</p>
            </div>
            <div class="field" :class="{ locked: !canDesignAdvanced }">
              <label for="design-name-size">Tamaño del nombre <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <div class="size-slider">
                <input
                  id="design-name-size"
                  v-model.number="designForm.name_font_size"
                  type="range"
                  :min="fontSizeMin"
                  :max="fontSizeMax"
                  step="1"
                  :disabled="!canDesignAdvanced"
                />
                <span class="size-value">{{ designForm.name_font_size }} px</span>
              </div>
              <p class="hint">Alto del nombre en la portada de tu web ({{ fontSizeMin }} a {{ fontSizeMax }} px).</p>
            </div>
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
              <p class="hint">Claro u oscuro: se aplica a la barra superior, la portada y todo tu catálogo.</p>
            </div>
            <div class="field" :class="{ locked: !canDesignAdvanced }">
              <label for="design-accent">Color de acento <span v-if="!canDesignAdvanced" class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></label>
              <select id="design-accent" v-model="designForm.accent" class="select" :disabled="!canDesignAdvanced">
                <option v-for="(a, key) in storeAccents" :key="key" :value="key">{{ a.label }}</option>
              </select>
              <div class="pick-strip swatches compact" aria-label="Vista previa de cada color">
                <button
                  v-for="(a, key) in storeAccents" :key="key" type="button"
                  class="swatch" :class="{ active: designForm.accent === key }"
                  :style="{ '--swatch': a.hex }"
                  :title="a.label" :aria-label="`Color ${a.label}`"
                  :aria-disabled="!canDesignAdvanced"
                  :aria-pressed="designForm.accent === key"
                  @click="pickAccent(key)"
                >
                  <AppIcon v-if="designForm.accent === key" name="check" :size="13" :stroke="2.5" />
                </button>
              </div>
              <p class="hint">Se aplica a la portada, los botones y los detalles de tu página.</p>
            </div>
          </div>
          </div>

        <aside class="card dsg-preview">
          <h3><AppIcon name="eye" :size="18" /> Vista previa</h3>
          <div class="design-preview" :data-store-theme="designForm.theme" :data-store-template="designTemplate" :style="designPreviewVars">
            <div class="dp-nav" aria-hidden="true">
              <span class="dp-nav-brand">
                <img v-if="currentLogo" class="dp-nav-logo" :src="currentLogo" alt="" />
                <span v-else class="dp-nav-mono" aria-hidden="true">{{ businessInitial }}</span>
                <span class="dp-nav-name" :style="designNameFont">{{ designShopName }}</span>
              </span>
              <span class="dp-nav-links">
                <span class="dp-nav-item">Inicio</span>
                <span v-if="designCatalogOn" class="dp-nav-item">Catálogo</span>
                <span class="dp-nav-item">Contacto</span>
              </span>
            </div>
            <div class="dp-hero" :class="{ 'has-cover': canDesignAdvanced && currentCover }" :style="canDesignAdvanced && currentCover ? { '--dp-cover': `url(${currentCover})` } : null">
              <img v-if="currentLogo" class="dp-logo" :src="currentLogo" alt="" />
              <span v-else class="dp-mono" aria-hidden="true">{{ businessInitial }}</span>
              <span class="dp-badge">{{ designForm.headline ? designShopName : (designCatalogOn ? 'Catálogo online' : 'Sitio oficial') }}</span>
              <strong class="dp-title" :class="{ 'is-name': !designForm.headline }" :style="designForm.headline ? null : designNameFont">{{ designForm.headline || designShopName }}</strong>
              <span v-if="designForm.description" class="dp-desc">{{ designForm.description }}</span>
              <div class="dp-cta">
                <span v-if="designCatalogOn" class="dp-btn">Ver catálogo</span>
                <span class="dp-btn ghost">Contáctanos</span>
              </div>
            </div>
            <div v-if="designCatalogOn && canDesignAdvanced && carouselImages.length" class="dp-catalog">
              <span class="dp-section-label"><AppIcon name="layout-grid" :size="11" /> Página Catálogo</span>
              <div class="dp-carousel">
                <div class="dp-carousel-track" :style="{ transform: `translateX(-${previewSlide * 100}%)` }">
                  <img v-for="img in carouselImages" :key="img.id" class="dp-carousel-img" :src="img.url" alt="" draggable="false" />
                </div>
              </div>
            </div>
            <div v-if="canLocationMap && designForm.show_location" class="dp-map" aria-hidden="true">
              <AppIcon name="map-pin" :size="13" /> Mapa con la ubicación de tu negocio
            </div>
          </div>
          <AppButton :loading="designBusy" @click="saveDesign">Guardar diseño</AppButton>
        </aside>
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
    <div v-show="section === 'company'" :class="{ 'sec-on': section === 'company' }">
      <div class="page-head">
        <div>
          <h1>Mi empresa</h1>
          <p>El contenido de marketing de tu página principal: cada bloque se publica al guardarlo y se oculta solo si quedó vacío o lo apagás.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
      </div>
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
          <p class="hint">La sección se apaga desde Diseño web, en "Secciones de tu web". También se oculta sola si no cargaste ningún contenido.</p>
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
            <p class="hint">Si apagás la sección Contáctanos desde Diseño web, los horarios también se ocultan.</p>
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

        <!-- ===== Orden de las secciones ===== -->
        <div id="mk-order" class="card mk-card">
          <h3><AppIcon name="arrow-down-wide-narrow" :size="18" /> Orden de las secciones</h3>
          <p>Definí en qué orden aparecen los bloques de tu página principal. La portada va primero y Contáctanos último siempre.</p>
          <div class="mk-order-list">
            <div v-for="(key, i) in sectionOrderList" :key="key" class="mk-order-item">
              <span class="mk-order-num" aria-hidden="true">{{ i + 1 }}</span>
              <strong>{{ sectionLabels[key] }}</strong>
              <span class="qa-actions mk-order-actions">
                <button type="button" class="icon-btn" :disabled="i === 0" :aria-label="`Subir ${sectionLabels[key]}`" @click="moveSection(key, -1)"><AppIcon name="chevron-up" :size="14" /></button>
                <button type="button" class="icon-btn" :disabled="i === sectionOrderList.length - 1" :aria-label="`Bajar ${sectionLabels[key]}`" @click="moveSection(key, 1)"><AppIcon name="chevron-down" :size="14" /></button>
              </span>
            </div>
          </div>
          <p class="hint">Las secciones vacías o apagadas se saltan solas: el orden aplica solo a las visibles.</p>
          <div class="btn-row">
            <AppButton :loading="companyBusy" @click="saveSectionOrder">Guardar orden</AppButton>
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
    <div v-show="section === 'stats'" :class="{ 'sec-on': section === 'stats' }">
      <div class="page-head">
        <div>
          <h1>Estadísticas</h1>
          <p>Métricas de tu tienda y de tu link público.</p>
        </div>
      </div>
      <template v-if="store.visitStats">
        <div class="stats">
          <div class="stat"><span class="stat-icon"><AppIcon name="eye" :size="20" /></span><div><strong>{{ store.visitStats.total }}</strong><small>Visitas totales</small></div></div>
          <div class="stat"><span class="stat-icon"><AppIcon name="trending-up" :size="20" /></span><div><strong>{{ store.visitStats.today }}</strong><small>Visitas hoy</small></div></div>
          <div class="stat"><span class="stat-icon"><AppIcon name="calendar" :size="20" /></span><div><strong>{{ visitAvg }}</strong><small>Promedio diario (30 días)</small></div></div>
        </div>
        <div class="card">
          <h3><AppIcon name="trending-up" :size="18" /> Últimos 30 días</h3>
          <div class="stats-chart" role="img" aria-label="Visitas por día">
            <span
              v-for="d in visitDays" :key="d.date" class="stats-bar"
              :class="{ today: d.date === visitDays[visitDays.length - 1]?.date }"
              :style="{ height: `${Math.max(2, (d.count / visitMax) * 100)}%` }"
              :title="`${d.date}: ${d.count} visita${d.count === 1 ? '' : 's'}`"
            ></span>
          </div>
          <div class="stats-chart-axis"><span>{{ visitDays[0]?.date?.slice(5) }}</span><span>{{ visitDays[visitDays.length - 1]?.date?.slice(5) }}</span></div>
          <p class="hint">Se cuenta una visita por persona por día en tu link público.</p>
        </div>
      </template>
      <div v-else class="empty">
        <span class="empty-icon"><AppIcon name="trending-up" :size="28" /></span>
        <h3>Todavía no hay visitas registradas</h3>
        <p>En cuanto alguien entre a tu link público vas a ver acá las visitas por día. Compartí tu web para empezar a medir.</p>
      </div>
    </div>
    <!-- ================= QR Y FOLLETOS (premium) ================= -->
    <div v-show="section === 'tools'" :class="{ 'sec-on': section === 'tools' }">
      <div class="page-head">
        <div>
          <h1>QR y folletos</h1>
          <p>Herramientas de difusión para tu link público.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
      </div>
      <div class="grid-2">
        <div v-if="canQr" class="card">
          <h3><AppIcon name="qr-code" :size="18" /> QR de tu tienda</h3>
          <p>Apunta a tu link público: <span class="mono link-url">{{ publicUrl }}</span></p>
          <div v-if="qrDataUrl" class="qr-box">
            <img :src="qrDataUrl" alt="Código QR de tu tienda" />
          </div>
          <div class="btn-row">
            <button class="btn btn-auto" :disabled="!qrDataUrl" @click="downloadQr"><AppIcon name="download" :size="16" /> Descargar QR</button>
            <button class="btn ghost btn-auto" @click="copyLink"><AppIcon name="copy" :size="16" /> Copiar link</button>
          </div>
        </div>
        <div v-if="canFlyers" class="card">
          <h3><AppIcon name="file-text" :size="18" /> Folleto imprimible</h3>
          <p>Panfletito A6 a color para repartir: tu logo, tus productos destacados, tu contacto y el QR de tu link. Salen 4 por hoja A4, listos para cortar, imprimir o guardar como PDF.</p>
          <div class="btn-row">
            <button class="btn btn-auto" @click="openFlyer"><AppIcon name="printer" :size="16" /> Generar folleto</button>
          </div>
        </div>
      </div>
    </div>
    <!-- ================= VENTA EN LOCAL (próximamente) ================= -->
    <div v-show="section === 'pos'" :class="{ 'sec-on': section === 'pos' }">
      <div class="page-head">
        <div>
          <h1>Venta en persona</h1>
          <p>Un punto de venta para cobrar cara a cara: tu catálogo, ya cargado.</p>
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
    <div v-show="section === 'bot'" :class="{ 'sec-on': section === 'bot' }">
      <div class="page-head">
        <div>
          <h1>Chatbot</h1>
          <p>Un asistente con la cara de tu negocio que responde solito a las visitas de tu web.</p>
        </div>
        <button class="btn ghost btn-auto" @click="openStore"><AppIcon name="external-link" :size="16" /> Ver mi web</button>
      </div>
      <AlertMessage v-if="store.notice" kind="success" :message="store.notice" />
      <AlertMessage v-if="store.lastError" kind="error" :message="store.lastError" />
      <AlertMessage v-if="botErr" kind="error" :message="botErr" />

      <div class="card">
        <h3><AppIcon name="bot" :size="18" /> Tu asistente</h3>
        <div class="field">
          <div class="check-list">
            <label class="check-item">
              <input v-model="botForm.is_enabled" type="checkbox" />
              <span class="check-text">
                <strong>Chatbot activo</strong>
                <small>Aparece como burbuja flotante abajo a la derecha de tu web pública, con el nombre y el logo de tu negocio.</small>
              </span>
            </label>
          </div>
        </div>
        <AppInput
          v-model="botForm.greeting"
          label="Mensaje de bienvenida"
          maxlength="200"
          placeholder="¡Hola! Soy el asistente de tu negocio. ¿En qué te puedo ayudar?"
          hint="Es lo primero que ve la visita al abrir el chat. Si lo dejás vacío se usa uno genérico con el nombre de tu negocio."
        />
        <div class="field">
          <label>Preguntas y respuestas <span class="hint-inline">({{ botForm.qa.length }}/{{ CHATBOT_QA_MAX }})</span></label>
          <p class="hint">Las visitas las tocan como sugerencias o escriben algo parecido: el bot contesta con tu respuesta. Si no entiende, las deriva a la sección Contáctanos.</p>
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
        <AppButton :loading="botBusy" @click="saveBot">Guardar chatbot</AppButton>
      </div>
    </div>
    <!-- ================= PLANES ================= -->
    <div v-show="section === 'plans'" :class="{ 'sec-on': section === 'plans' }">
      <div class="page-head">
        <div>
          <h1>Planes</h1>
          <p>Elegí el plan que acompaña el tamaño de tu negocio. Podés cambiarlo cuando quieras.</p>
        </div>
      </div>
      <AlertMessage v-if="billing.notice" kind="success" :message="billing.notice" />
      <AlertMessage v-if="billing.lastError" kind="error" :message="billing.lastError" />
      <AlertMessage v-if="payments.notice" kind="success" :message="payments.notice" />
      <AlertMessage v-if="payments.lastError" kind="error" :message="payments.lastError" />
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
    <div v-show="section === 'payments'" :class="{ 'sec-on': section === 'payments' }">
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
    <div v-show="section === 'invoices'" :class="{ 'sec-on': section === 'invoices' }">
      <div class="page-head">
        <div>
          <h1>Facturas</h1>
          <p>Tus comprobantes emitidos por cada pago acreditado. También te los enviamos al correo registrado en tu cuenta.</p>
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
        <p>Cuando se acredite un pago de tu suscripción, el comprobante se emite solo, llega al correo de tu cuenta y aparece acá, listo para imprimir o guardar como PDF.</p>
        <button class="btn btn-auto" @click="section = 'payments'">Ver mis pagos</button>
      </div>
    </div>
    <!-- ================= CUENTA ================= -->
    <div v-show="section === 'settings'" :class="{ 'sec-on': section === 'settings' }">
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
          <!-- Verificación del celular por SMS de Firebase (plan Spark gratis).
               El SDK confirma el código y manda el idToken al backend. -->
          <div class="verify-phone">
            <template v-if="phoneVerified">
              <p class="badge-ok"><AppIcon name="badge-check" :size="16" /> Celular verificado</p>
            </template>
            <template v-else>
              <p class="verify-phone-text">Verificá tu celular: te enviamos un código por SMS. Nos ayuda a confirmar que la cuenta es de una persona real.</p>
              <button type="button" class="btn ghost btn-auto" :disabled="!hasPhone || !firebaseEnabled || phoneVerifyBusy" @click="startPhoneVerify">
                <span v-if="phoneVerifyBusy" class="spinner"></span><AppIcon name="message-circle" :size="16" /> {{ phoneVerifySent ? 'Reenviar SMS' : 'Verificar por SMS' }}
              </button>
              <p v-if="!hasPhone" class="hint">Cargá tu número de celular arriba y guardá los cambios para poder verificarlo.</p>
              <p v-else-if="!firebaseEnabled" class="hint">La verificación por SMS no está habilitada en este despliegue.</p>
              <div v-if="phoneVerifySent" class="verify-phone-pending">
                <p>Ingresá el código que te llegó por SMS:</p>
                <input
                  v-model="phoneVerifyCode"
                  class="input verify-phone-input"
                  type="text"
                  inputmode="numeric"
                  autocomplete="one-time-code"
                  maxlength="6"
                  placeholder="123456"
                />
                <button type="button" class="btn btn-auto" :disabled="phoneVerifyBusy || phoneVerifyCode.trim().length < 6" @click="confirmPhoneVerify">
                  <span v-if="phoneVerifyBusy" class="spinner"></span>Confirmar código
                </button>
              </div>
              <AlertMessage v-if="phoneVerifyErr" kind="error" :message="phoneVerifyErr" />
              <!-- Firebase monta el reCAPTCHA invisible acá (obligatorio) -->
              <div ref="recaptchaEl"></div>
            </template>
          </div>
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
