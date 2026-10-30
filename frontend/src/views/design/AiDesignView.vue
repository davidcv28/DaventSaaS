<script setup>
import { ref, reactive, computed, nextTick, watch, onBeforeUnmount, onMounted } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import AiProposalCard from '../../components/ai/AiProposalCard.vue'
import AiKnownCard from '../../components/ai/AiKnownCard.vue'
import AiIdeaCard from '../../components/ai/AiIdeaCard.vue'
import AiCompareTable from '../../components/ai/AiCompareTable.vue'
import AiAdjustPanel from '../../components/ai/AiAdjustPanel.vue'
import AiPublishedPanel from '../../components/ai/AiPublishedPanel.vue'
import AiNightModeField from '../../components/ai/AiNightModeField.vue'
import AiCoverField from '../../components/ai/AiCoverField.vue'
import AiDevicePreview from '../../components/ai/AiDevicePreview.vue'
import { useStoreStore } from '../../stores/store.store.js'
import {
  storesApi, CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  resolveStoreTemplate, allowedTemplatesFor
} from '../../api/stores.api.js'
import { http } from '../../api/http.js'
import '../../assets/ai-design.css'

const props = defineProps({
  plan: { type: Object, default: null }
})
const emit = defineEmits(['applied', 'navigate'])

const store = useStoreStore()

const RUBROS = [
  { id: 'Indumentaria y moda', label: 'Indumentaria y moda', icon: 'tag', desc: 'Ropa, calzado y accesorios' },
  { id: 'Comida y bebida', label: 'Comida y bebida', icon: 'coffee', desc: 'Restó, bar, panadería o delivery' },
  { id: 'Belleza y estética', label: 'Belleza y estética', icon: 'flower', desc: 'Peluquería, uñas, maquillaje' },
  { id: 'Salud y bienestar', label: 'Salud y bienestar', icon: 'heart', desc: 'Consultorios, terapias, gym' },
  { id: 'Servicios para el hogar', label: 'Servicios para el hogar', icon: 'wrench', desc: 'Plomería, electricidad, arreglos' },
  // Rubro nuevo del motor (id interno de RUBROS en el backend): seguridad
  // industrial, bomberos y EPP. Se manda el id, no el label.
  { id: 'seguridad', label: 'Seguridad y bomberos', icon: 'shield-check', desc: 'Seguridad industrial, bomberos, EPP' },
  { id: 'Tecnología', label: 'Tecnología', icon: 'monitor', desc: 'Equipos, reparaciones, software' },
  { id: 'Hogar y deco', label: 'Hogar y deco', icon: 'package', desc: 'Muebles, decoración, regalos' },
  { id: 'Educación', label: 'Educación', icon: 'graduation-cap', desc: 'Clases, cursos, talleres' },
  { id: 'Profesionales', label: 'Profesionales', icon: 'file-text', desc: 'Estudios, consultoría, oficios' },
  { id: 'Mascotas', label: 'Mascotas', icon: 'paw-print', desc: 'Veterinaria, peluquería, alimento' },
  { id: 'Deportes', label: 'Deportes', icon: 'dumbbell', desc: 'Indumentaria, clases, torneos' },
  { id: 'Otro', label: 'Otra cosa', icon: 'sparkles', desc: 'Te lo armamos igual' }
]
const GOALS = [
  { id: 'vender', label: 'Vender online', icon: 'credit-card', desc: 'Que puedan comprar desde la web' },
  { id: 'servicios', label: 'Mostrar mis servicios', icon: 'wrench', desc: 'Explicar qué hacés y cuánto sale' },
  { id: 'consultas', label: 'Recibir consultas', icon: 'message-circle', desc: 'Que te escriban o te llamen' },
  { id: 'confianza', label: 'Dar confianza', icon: 'shield-check', desc: 'Que vean que sos un negocio serio' },
  { id: 'trabajos', label: 'Mostrar mis trabajos', icon: 'images', desc: 'Fotos de lo que hacés' }
]
const TONES = [
  { id: 'calido', label: 'Cálido y cercano', icon: 'heart', desc: 'Como una charla entre conocidos' },
  { id: 'serio', label: 'Serio y confiable', icon: 'building-2', desc: 'Ordenado, sobrio, profesional' },
  { id: 'moderno', label: 'Moderno y simple', icon: 'zap', desc: 'Limpio, actual, directo' },
  { id: 'audaz', label: 'Audaz y con personalidad', icon: 'flame', desc: 'Colores fuertes y letras grandes' }
]
const AUDIENCES = [
  { id: 'particulares', label: 'Personas', icon: 'users', desc: 'Clientes que compran para ellos' },
  { id: 'empresas', label: 'Empresas', icon: 'building-2', desc: 'Negocios que te contratan' },
  { id: 'ambas', label: 'Las dos', icon: 'users', desc: 'Personas y empresas' }
]
// "¿Qué te importa más?": matiz fino sobre el estilo. El motor solo entiende
// `tone`, así que cada matiz vota por uno de los cuatro estilos (y el
// elegido a mano en el select siempre gana).
const STYLE_HINTS = [
  { id: 'elegancia', label: 'Elegancia', icon: 'gem', tone: 'serio' },
  { id: 'energia', label: 'Energía', icon: 'flame', tone: 'audaz' },
  { id: 'cercania', label: 'Cercanía', icon: 'heart', tone: 'calido' },
  { id: 'tecnologia', label: 'Tecnología', icon: 'monitor', tone: 'moderno' },
  { id: 'tradicion', label: 'Tradición', icon: 'award', tone: 'serio' },
  { id: 'lujo', label: 'Lujo', icon: 'crown', tone: 'serio' }
]
const HINT_TONE_ORDER = ['audaz', 'calido', 'moderno', 'serio']
const MUST_HAVE = [
  { id: 'whatsapp', label: 'Botón de WhatsApp', icon: 'whatsapp', desc: 'Para que te escriban al toque' },
  { id: 'hours', label: 'Horarios', icon: 'clock', desc: 'Cuándo estás abierto' },
  { id: 'map', label: 'Mapa y dirección', icon: 'map-pin', desc: 'Cómo llegar a tu local' },
  { id: 'prices', label: 'Precios', icon: 'tag', desc: 'Cuánto sale cada cosa' },
  { id: 'testimonials', label: 'Opiniones de clientes', icon: 'quote', desc: 'Lo que dicen de vos' },
  { id: 'faqs', label: 'Preguntas frecuentes', icon: 'circle-help', desc: 'Las dudas que te preguntan siempre' }
]
// Lo que la entrevista vieja preguntaba y no cambia el diseño (pantalla 1:
// "lo que no te vamos a preguntar"). Se dice explícito para bajar la ansiedad
// del dueño que espera un formulario largo.
const NOT_ASKED = ['Historia del negocio', 'Misión', 'Horarios', 'Formas de pago', 'Redes sociales']
// Tipografías que el motor sabe aplicar (ids de TYPE_PAIRS en el backend).
const PAIR_OPTIONS = [
  { id: 'grotesk-clean', label: 'Grotesk limpio', icon: 'type', desc: 'Neutra y actual' },
  { id: 'serif-editorial', label: 'Serif editorial', icon: 'type', desc: 'Con carácter, tipo revista' },
  { id: 'serif-classic', label: 'Serif clásico', icon: 'type', desc: 'Sobria y elegante' },
  { id: 'display-heavy', label: 'Peso máximo', icon: 'type', desc: 'Títulos que se imponen' },
  { id: 'geometric', label: 'Geométrica', icon: 'type', desc: 'Moderna y limpia' },
  { id: 'warm-serif', label: 'Serif cálida', icon: 'type', desc: 'Cercana, con detalle' }
]
const STEP_TITLES = ['Contanos', 'Propuestas']

const EMPTY = () => ({
  rubro: '', goals: [], tone: '', style_hint: [], audience: '', must_have: [], content_hint: '',
  brand_color: '', night_mode: { enabled: false, default: 'light' }, cover_choice: 'auto', use_icons: true,
  accept_extras: true
})
const answers = reactive(EMPTY())

// ask | loading | results | adjust | published | error
const phase = ref('ask')
const proposals = ref([])
const seed = ref(null)
const missing = ref([])
const checks = ref([])
const prefill = ref(null)
const selectedId = ref('')
const constraints = ref({})
const initialConstraints = ref({})
const appliedLabels = ref([])
const refining = ref(false)
const errorMsg = ref('')
const actionError = ref('')
const published = ref(null) // { id, label }
const busy = ref('')
const previewProposal = ref(null)
const resultsRef = ref(null)
const hydrated = ref(false)

let requestSeq = 0
let timer = null
onBeforeUnmount(() => {
  clearTimeout(timer)
})

const benefits = computed(() => props.plan?.benefits || {})
const hasDesignAdvanced = computed(() => Boolean(benefits.value.has_design_advanced))
const canUse = computed(() => Boolean(props.plan?.isCurrent && benefits.value.has_customization && benefits.value.has_ai_design))
const allowed = computed(() => allowedTemplatesFor(benefits.value))
const shopName = computed(() => store.customization.display_name || store.store?.business_name || prefill.value?.name || 'Tu negocio')
const initial = computed(() => (shopName.value || 'T').slice(0, 1).toUpperCase())
const logo = computed(() => store.customization.logo || '')
const cover = computed(() => store.customization.cover || '')
const description = computed(() => String(store.customization.description || '').trim())
const storeId = computed(() => store.store?.id || '')
// La vista previa corre SIEMPRE en el mismo origen (alias /<slug>): el
// subdominio de la tienda puede no resolver (dev con *.localhost, Render sin
// wildcard) y el iframe quedaba en blanco o caía al mockup estático. Mismo
// origen = la landing real, con el mensaje del Studio aceptado por origen.
const publicUrl = computed(() => (store.store?.slug ? `${window.location.origin}/${store.store.slug}` : ''))
const storageKey = computed(() => `davent:ai-design:${storeId.value || 'sin-tienda'}`)
const progressStep = computed(() => (phase.value === 'ask' ? 1 : 2))
const selectedProposal = computed(() => proposals.value.find((p) => p.id === selectedId.value) || null)
// Cuántas familias visuales distintas trajo esta tanda (para avisarlo).
const distinctFamilies = computed(() => {
  const set = new Set()
  proposals.value.forEach((p) => {
    const family = p.skin?.family || p.variety?.family
    if (family) set.add(family)
  })
  return set.size
})
const varietyNotice = computed(() => {
  if (proposals.value.length < 2 || distinctFamilies.value < 2) return ''
  return `${proposals.value.length} estilos distintos para tu rubro`
})
const adjustDirty = computed(() => JSON.stringify(constraints.value) !== JSON.stringify(initialConstraints.value))

const autofillDefault = computed(() => {
  const c = store.customization || {}
  const empty = (v) => !v || (Array.isArray(v) && !v.length) || (typeof v === 'string' && !v.trim())
  return empty(c.about_text) && empty(c.about_mission) && empty(c.faqs) && empty(c.services) && empty(c.announcements)
})

const liveMessage = computed(() => {
  if (phase.value === 'loading') return 'Armando tus propuestas…'
  if (phase.value === 'error') return 'No pudimos armar las propuestas.'
  if (phase.value === 'results') return `${proposals.value.length} propuestas listas.`
  if (phase.value === 'adjust') return 'Ajustando la propuesta elegida.'
  if (phase.value === 'published') return 'Tu web ya está publicada.'
  return 'Paso 1 de 2: contanos lo mínimo.'
})

const hasAnswers = computed(() => Boolean(
  answers.rubro || answers.goals.length || answers.tone || answers.style_hint.length || answers.audience ||
  answers.must_have.length || answers.brand_color || answers.night_mode.enabled ||
  answers.cover_choice !== 'auto' || !answers.use_icons || answers.accept_extras === false
))

const MISSING_ACTIONS = {
  catalog: 'catalogs',
  services: 'company',
  gallery: 'design',
  cover: 'design',
  logo: 'design',
  images: 'design',
  hours: 'company',
  location: 'company',
  contact: 'company',
  social: 'company'
}
function missingTarget(m) {
  const action = m.action || ''
  if (action === 'images' || action === 'gallery' || action === 'design') return 'design'
  if (action === 'catalogs' || action === 'catalog') return 'catalogs'
  return MISSING_ACTIONS[m.code] || 'company'
}

// ---------- Persistencia de respuestas ----------
function hydrate() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const saved = JSON.parse(raw)
    const base = EMPTY()
    answers.rubro = typeof saved.rubro === 'string' ? saved.rubro : base.rubro
    answers.goals = Array.isArray(saved.goals) ? saved.goals.filter((g) => GOALS.some((o) => o.id === g)) : []
    answers.tone = typeof saved.tone === 'string' ? saved.tone : base.tone
    answers.style_hint = Array.isArray(saved.style_hint)
      ? saved.style_hint.filter((h) => STYLE_HINTS.some((o) => o.id === h)).slice(0, 2)
      : []
    answers.audience = typeof saved.audience === 'string' ? saved.audience : base.audience
    answers.must_have = Array.isArray(saved.must_have) ? saved.must_have.filter((m) => MUST_HAVE.some((o) => o.id === m)) : []
    answers.content_hint = typeof saved.content_hint === 'string' ? saved.content_hint.slice(0, 160) : ''
    answers.brand_color = /^#[0-9a-f]{6}$/i.test(saved.brand_color || '') ? saved.brand_color.toLowerCase() : ''
    const nm = saved.night_mode
    answers.night_mode = (nm && typeof nm === 'object')
      ? { enabled: Boolean(nm.enabled), default: nm.default === 'dark' ? 'dark' : 'light' }
      : { enabled: false, default: 'light' }
    answers.cover_choice = ['foto', 'logo', 'auto'].includes(saved.cover_choice) ? saved.cover_choice : 'auto'
    answers.use_icons = saved.use_icons !== false
    // v6: "¿sumar extras?" — ausente = sí (decisión del brief §2.3).
    answers.accept_extras = saved.accept_extras !== false
  } catch { /* storage bloqueado o dato viejo */ }
  hydrated.value = true
}

function persist() {
  if (!hydrated.value) return
  try {
    localStorage.setItem(storageKey.value, JSON.stringify({ ...answers }))
  } catch { /* storage bloqueado */ }
}

watch(answers, persist, { deep: true })
watch(storageKey, () => { if (storeId.value && !hydrated.value) hydrate() }, { immediate: true })

// ---------- Prefill: lo que la IA ya sabe (pantalla 1) ----------
async function loadPrefill() {
  if (!canUse.value || prefill.value) return
  try {
    const data = await storesApi.aiDesignPrefill()
    prefill.value = data
    //La deducción solo rellena lo que el dueño no eligió: nunca pisa su
    //respuesta guardada.
    if (!answers.rubro && data?.rubro) answers.rubro = data.rubro
    if (!answers.goals.length && Array.isArray(data?.goals)) {
      answers.goals = data.goals.filter((goal) => GOALS.some((o) => o.id === goal)).slice(0, 2)
    }
    if (Array.isArray(data?.checks)) checks.value = data.checks
  } catch { /* sin prefill la entrevista funciona igual */ }
}
onMounted(loadPrefill)
watch(canUse, (value) => { if (value) loadPrefill() })

// ---------- Telemetría del funnel (5.1) ----------
// Fire-and-forget: si falla (offline, throttle) la sección sigue igual.
const sessionId = (() => {
  try {
    const key = 'davent:ai-design:session'
    let id = sessionStorage.getItem(key)
    if (!id) {
      id = String(crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`).slice(0, 40)
      sessionStorage.setItem(key, id)
    }
    return id
  } catch { return '' }
})()
function track(action, extra = {}) {
  storesApi.aiDesignEvent({ session: sessionId, action, step: progressStep.value, ...extra }).catch(() => {})
}

// ---------- Preview ----------
const HEX_RE = /^#[0-9a-f]{6}$/i
function proposalForm(p) {
  const form = { ...CUSTOMIZATION_DEFAULTS, ...(store.customization || {}), ...(p.site_theme || {}), ...(p.copy || {}) }
  const accent = String(p.theme_choice?.accent || '')
  if (HEX_RE.test(accent)) form.accent_custom = accent.toLowerCase()
  const nm = p.night_mode
  if (nm?.enabled && (nm.default === 'dark' || nm.default === 'light')) form.theme = nm.default
  if (p.cover?.mode === 'logo') form.cover = ''
  return form
}
function proposalCover(p) {
  return p?.cover?.mode === 'logo' ? '' : cover.value
}
function proposalVars(p) {
  return storeThemeVars(proposalForm(p))
}
function proposalTemplate(p) {
  return resolveStoreTemplate(p.template, allowed.value)
}
function proposalNameFont(p) {
  return { fontFamily: storeFontFamily(proposalForm(p).name_font) }
}
const previewForm = computed(() => (previewProposal.value ? proposalForm(previewProposal.value) : {}))
const previewVars = computed(() => (previewProposal.value ? proposalVars(previewProposal.value) : {}))
const previewTemplate = computed(() => (previewProposal.value ? proposalTemplate(previewProposal.value) : 'raiz'))
const previewNameFont = computed(() => (previewProposal.value ? proposalNameFont(previewProposal.value) : {}))
const previewCover = computed(() => (previewProposal.value ? proposalCover(previewProposal.value) : cover.value))

// ---------- Flujo ----------
// El estilo elegido a mano manda; si no eligió, deciden los "me importa más".
function resolvedTone() {
  if (answers.tone) return answers.tone
  const votes = {}
  answers.style_hint.forEach((h) => {
    const tone = STYLE_HINTS.find((o) => o.id === h)?.tone
    if (tone) votes[tone] = (votes[tone] || 0) + 1
  })
  const keys = Object.keys(votes)
  if (!keys.length) return ''
  return keys.sort((a, b) => (votes[b] - votes[a]) || (HINT_TONE_ORDER.indexOf(a) - HINT_TONE_ORDER.indexOf(b)))[0]
}
function toggleHint(id) {
  const i = answers.style_hint.indexOf(id)
  if (i >= 0) { answers.style_hint.splice(i, 1); return }
  if (answers.style_hint.length >= 2) answers.style_hint.shift()
  answers.style_hint.push(id)
}
function toggleGoal(id) {
  const i = answers.goals.indexOf(id)
  if (i >= 0) answers.goals.splice(i, 1)
  else answers.goals.push(id)
}
function toggleMustHave(id) {
  const i = answers.must_have.indexOf(id)
  if (i >= 0) answers.must_have.splice(i, 1)
  else answers.must_have.push(id)
}

function payload(extra = {}) {
  const p = {}
  if (answers.rubro) p.rubro = answers.rubro
  if (answers.goals.length) p.goals = [...answers.goals]
  const tone = resolvedTone()
  if (tone) p.tone = tone
  if (answers.audience) p.audience = answers.audience
  if (answers.must_have.length) p.must_have = [...answers.must_have]
  const hint = String(answers.content_hint || '').trim()
  if (hint) p.content_hint = hint.slice(0, 160)
  p.brand_color = answers.brand_color || ''
  p.night_mode = {
    enabled: Boolean(answers.night_mode.enabled),
    default: answers.night_mode.enabled && answers.night_mode.default === 'dark' ? 'dark' : 'light'
  }
  p.cover_choice = answers.cover_choice || 'auto'
  p.use_icons = answers.use_icons !== false
  // v6 §2.3: ausente = true en el motor; acá siempre viaja explícito.
  p.accept_extras = answers.accept_extras !== false
  return { ...p, ...extra }
}

async function generate(extra = {}, useAnswers = true, opts = {}) {
  if (phase.value === 'loading') return
  const seq = ++requestSeq
  phase.value = 'loading'
  errorMsg.value = ''
  actionError.value = ''
  published.value = null
  selectedId.value = ''
  proposals.value = []
  previewProposal.value = null
  clearTimeout(timer)
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(Object.assign(new Error('timeout'), { aidTimeout: true })), 15000)
  })
  try {
    const body = useAnswers ? payload(extra) : { ...extra }
    const data = await Promise.race([storesApi.aiDesign(body), timeout])
    if (seq !== requestSeq) return
    if (!data || !Array.isArray(data.proposals) || !data.proposals.length) throw new Error('empty')
    seed.value = data.seed
    missing.value = Array.isArray(data.missing) ? data.missing : []
    checks.value = Array.isArray(data.checks) ? data.checks : checks.value
    proposals.value = data.proposals
    phase.value = 'results'
    track('generate', { meta: { rubro: answers.rubro, goal: answers.goals[0] || '', tone: resolvedTone() || '', count: data.proposals.length } })
    await nextTick()
    resultsRef.value?.querySelector('.aidi')?.focus?.()
  } catch (e) {
    if (seq !== requestSeq) return
    if (e?.aidTimeout) requestSeq++
    errorMsg.value = e?.response?.data?.detail || (e?.aidTimeout
      ? 'Tardó más de la cuenta. Probá de nuevo.'
      : 'No pudimos armar las propuestas. Probá de nuevo en un momento.')
    phase.value = 'error'
  } finally {
    clearTimeout(timer)
  }
}

function decideForMe() {
  track('step_done', { step: 1 })
  generate({}, false)
}
function anotherStyle() {
  track('explore', { meta: { count: proposals.value.length } })
  generate({ seed: (seed.value || 0) + 1 }, true)
}
function redoWithPhotos() {
  generate({ seed: seed.value })
}
function backToQuestions() {
  phase.value = 'ask'
  previewProposal.value = null
}

// ---------- Elegir / ajustar (pantallas 2 y 3) ----------
function constraintsOf(proposal) {
  const look = proposal?.look || {}
  return {
    typography: look.fonts?.pair || '',
    cover: proposal?.cover?.mode === 'logo' ? 'logo' : (answers.cover_choice === 'auto' ? 'auto' : 'foto'),
    air: look.density || '',
    color: proposal?.theme_choice?.source === 'user' ? String(proposal.theme_choice.accent || '').toLowerCase() : ''
  }
}

function choose(id) {
  const proposal = proposals.value.find((p) => p.id === id)
  if (!proposal) return
  selectedId.value = id
  constraints.value = constraintsOf(proposal)
  initialConstraints.value = { ...constraints.value }
  appliedLabels.value = []
  actionError.value = ''
  phase.value = 'adjust'
  track('step_done', { proposal_id: id, step: 2 })
}

async function refine(next = constraints.value) {
  const proposal = selectedProposal.value
  if (!proposal || refining.value || !seed.value) return
  refining.value = true
  busy.value = `refine:${proposal.id}`
  actionError.value = ''
  try {
    const data = await storesApi.aiDesignRefine({
      seed: seed.value,
      proposal_id: proposal.id,
      constraints: { ...next }
    })
    const index = proposals.value.findIndex((p) => p.id === proposal.id)
    if (index >= 0) proposals.value.splice(index, 1, data.proposal)
    initialConstraints.value = { ...next }
    constraints.value = { ...next }
    appliedLabels.value = Array.isArray(data.applied) ? data.applied : []
    track('refine', { proposal_id: proposal.id, meta: { applied: (data.applied || []).join(',') } })
  } catch (e) {
    actionError.value = e?.response?.data?.detail || 'No pudimos aplicar el cambio. Probá de nuevo.'
  } finally {
    refining.value = false
    busy.value = ''
  }
}

function resetAdjust() {
  const proposal = selectedProposal.value
  if (!proposal) return
  //Sin constraints el motor devuelve la propuesta original de la tanda.
  constraints.value = { typography: '', cover: 'auto', air: '', color: '' }
  refine({})
}

function backToResults() {
  phase.value = 'results'
  previewProposal.value = null
}

function startOver() {
  requestSeq++
  clearTimeout(timer)
  Object.assign(answers, EMPTY())
  try { localStorage.removeItem(storageKey.value) } catch { /* storage bloqueado */ }
  proposals.value = []
  missing.value = []
  seed.value = null
  published.value = null
  selectedId.value = ''
  constraints.value = {}
  initialConstraints.value = {}
  actionError.value = ''
  errorMsg.value = ''
  previewProposal.value = null
  phase.value = 'ask'
}

// El contrato v3 aplica y publica en un solo request: ya no hay publish/discard
// desde esta sección (siguen existiendo para el Studio).
async function apply({ proposal, autofill, extras }) {
  if (!seed.value || busy.value) return
  busy.value = `apply:${proposal.id}`
  actionError.value = ''
  try {
    await http.post('/stores/ai-design/apply/', {
      seed: seed.value,
      proposal_id: proposal.id,
      autofill: Boolean(autofill),
      // Extras elegidos en la tarjeta: `offered` deja apagados los
      // rechazados (sin borrarlos del borrador) y `applied` prende los
      // aceptados. Sin extras, el backend usa los de la propuesta.
      ...(extras ? { extras } : {})
    })
    await store.refreshCustomization()
    published.value = { id: proposal.id, label: proposal.label }
    phase.value = 'published'
    track('apply', {
      proposal_id: proposal.id,
      meta: { template: proposal.template, family: proposal.skin?.family || '', style: proposal.variety?.style || '' }
    })
    emit('applied', { action: 'publish' })
    //La lista de chequeo se recalcula con los datos que acaban de cambiar
    //(el autofill puede haber escrito la descripción).
    storesApi.aiDesignPrefill().then((data) => {
      if (Array.isArray(data?.checks)) checks.value = data.checks
    }).catch(() => {})
  } catch (e) {
    actionError.value = e?.response?.data?.detail || 'No pudimos establecer el estilo. Probá de nuevo.'
  } finally {
    busy.value = ''
  }
}

// "Todo cambio se puede deshacer": vuelve a la propuesta original de la
// tanda y la republica (el ajuste se descarta, no la propuesta).
async function revertPublished() {
  if (!selectedProposal.value || !seed.value || busy.value) return
  await refine({})
  if (actionError.value) return
  if (selectedProposal.value) {
    await apply({ proposal: selectedProposal.value, autofill: false })
  }
}

function copyLink() {
  if (!publicUrl.value) return
  navigator.clipboard?.writeText(publicUrl.value).catch(() => {})
}

function openPreview(p) {
  previewProposal.value = p
}
function closePreview() {
  previewProposal.value = null
}
</script>

<template>
  <div class="aid">
    <header class="aid-head">
      <div class="aid-head-text">
        <span class="aid-badge-new">Nuevo</span>
        <h1><AppIcon name="sparkles" :size="20" /> Diseñar con IA</h1>
        <p>Contanos dos líneas de tu negocio y te armamos tres ideas de web. Después la ajustás sin empezar de cero.</p>
        <span v-if="phase === 'published'" class="aid-pub-chip"><AppIcon name="circle-check" :size="13" /> Publicada</span>
      </div>
      <button v-if="phase !== 'ask' || hasAnswers" class="btn ghost btn-auto" type="button" @click="startOver">
        <AppIcon name="refresh" :size="16" /> Empezar de nuevo
      </button>
    </header>

    <div v-if="!canUse" class="empty">
      <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
      <h3>Diseñar con IA viene con tu plan</h3>
      <p>Sumá el beneficio desde Mi plan y volvé a entrar.</p>
      <button class="btn btn-auto" type="button" @click="emit('navigate', 'plans')">Ver planes</button>
    </div>

    <template v-else>
      <p class="aid-live" aria-live="polite">{{ liveMessage }}</p>

      <div class="aid-progress" role="group" aria-label="Progreso">
        <span v-for="n in 2" :key="n" class="aid-progress-dot" :class="{ on: progressStep >= n, now: progressStep === n }">
          <span class="sr-only">Paso {{ n }}: {{ STEP_TITLES[n - 1] }}</span>
        </span>
      </div>

      <!-- PANTALLA 1 · EMPEZAR EN DOS PASOS -->
      <div v-if="phase === 'ask'" class="aid-ask">
        <AiKnownCard v-model="answers.rubro" :prefill="prefill" :rubro-options="RUBROS" />

        <div class="aid-field">
          <p class="aid-field-title">Contanos en dos líneas qué hacés y a quién le vendés</p>
          <textarea
            v-model="answers.content_hint"
            class="aid-input"
            rows="3"
            maxlength="160"
            placeholder="Ej.: ferretería de barrio, vendemos herramientas y pintura; el que más nos escribe es el que arregla en su casa."
          ></textarea>
          <p class="aid-hints-note">Lo usamos para escribir el texto de la web. No inventamos datos: solo lo que nos contás.</p>
        </div>

        <div class="aid-field">
          <p class="aid-field-title">¿Qué querés lograr?</p>
          <div class="aid-hints" role="group" aria-label="¿Qué querés lograr?">
            <button
              v-for="goal in GOALS"
              :key="goal.id"
              type="button"
              class="aid-hint-chip"
              :class="{ on: answers.goals.includes(goal.id) }"
              :aria-pressed="answers.goals.includes(goal.id)"
              @click="toggleGoal(goal.id)"
            >
              <AppIcon :name="goal.icon" :size="15" aria-hidden="true" />
              <span>{{ goal.label }}</span>
            </button>
          </div>
        </div>

        <div class="aid-field">
          <p class="aid-field-title">A quién le hablás <span class="aid-optional">Opcional</span></p>
          <div class="aid-hints" role="group" aria-label="A quién le hablás">
            <button
              v-for="audience in AUDIENCES"
              :key="audience.id"
              type="button"
              class="aid-hint-chip"
              :class="{ on: answers.audience === audience.id }"
              :aria-pressed="answers.audience === audience.id"
              @click="answers.audience = answers.audience === audience.id ? '' : audience.id"
            >
              <AppIcon :name="audience.icon" :size="15" aria-hidden="true" />
              <span>{{ audience.label }}</span>
            </button>
          </div>
        </div>

        <div class="aid-field">
          <p class="aid-field-title">Cómo se siente <span class="aid-optional">Opcional</span></p>
          <div class="aid-hints" role="group" aria-label="Cómo se siente">
            <button
              v-for="tone in TONES"
              :key="tone.id"
              type="button"
              class="aid-hint-chip"
              :class="{ on: answers.tone === tone.id }"
              :aria-pressed="answers.tone === tone.id"
              @click="answers.tone = answers.tone === tone.id ? '' : tone.id"
            >
              <AppIcon :name="tone.icon" :size="15" aria-hidden="true" />
              <span>{{ tone.label }}</span>
            </button>
          </div>
        </div>

        <details class="aid-more">
          <summary>Más opciones (no hace falta tocarlas)</summary>
          <div class="aid-fields aid-more-body">
            <div class="aid-field">
              <p class="aid-field-title">¿Qué no puede faltar?</p>
              <div class="aid-hints" role="group" aria-label="¿Qué no puede faltar?">
                <button
                  v-for="item in MUST_HAVE"
                  :key="item.id"
                  type="button"
                  class="aid-hint-chip"
                  :class="{ on: answers.must_have.includes(item.id) }"
                  :aria-pressed="answers.must_have.includes(item.id)"
                  @click="toggleMustHave(item.id)"
                >
                  <AppIcon :name="item.icon" :size="15" aria-hidden="true" />
                  <span>{{ item.label }}</span>
                </button>
              </div>
            </div>
            <div class="aid-field">
              <p class="aid-field-title">¿Qué te importa más? <span class="aid-optional">Opcional</span></p>
              <div class="aid-hints" role="group" aria-label="¿Qué te importa más?">
                <button
                  v-for="hint in STYLE_HINTS"
                  :key="hint.id"
                  type="button"
                  class="aid-hint-chip"
                  :class="{ on: answers.style_hint.includes(hint.id) }"
                  :aria-pressed="answers.style_hint.includes(hint.id)"
                  @click="toggleHint(hint.id)"
                >
                  <AppIcon :name="hint.icon" :size="15" aria-hidden="true" />
                  <span>{{ hint.label }}</span>
                </button>
              </div>
            </div>
            <div class="aid-field">
              <p class="aid-field-title">¿Usamos una foto de portada?</p>
              <AiCoverField v-model="answers.cover_choice" :has-logo="Boolean(logo)" />
            </div>
            <div class="aid-field">
              <p class="aid-field-title">¿Querés modo noche?</p>
              <AiNightModeField v-model="answers.night_mode" :accent="answers.brand_color || '#7c3aed'" />
            </div>
            <label class="aid-switch">
              <input v-model="answers.use_icons" type="checkbox" />
              <span class="aid-switch-text">
                <strong>Usar íconos en las secciones</strong>
                <small>Ayudan a que se entienda rápido qué ofrecés.</small>
              </span>
            </label>
            <label class="aid-switch">
              <input v-model="answers.accept_extras" type="checkbox" />
              <span class="aid-switch-text">
                <strong>Que la IA agregue elementos extra</strong>
                <small>Bandas, mosaicos de fotos y precios armados con tus datos. Después los quitás uno por uno.</small>
              </span>
            </label>
          </div>
        </details>

        <div class="aid-notask">
          <p class="aid-notask-title">Lo que no te vamos a preguntar</p>
          <div class="aid-hints">
            <span v-for="item in NOT_ASKED" :key="item" class="aid-notask-chip">{{ item }}</span>
          </div>
        </div>

        <div class="aid-actions">
          <button class="btn btn-auto aid-primary" type="button" @click="generate()">
            <AppIcon name="sparkles" :size="16" /> Armar mis propuestas
          </button>
          <button class="btn ghost btn-auto" type="button" @click="decideForMe">
            Prefiero que decidas vos
          </button>
          <span class="aid-micro">2 pasos · menos de 1 minuto</span>
        </div>
      </div>

      <!-- CARGANDO -->
      <div v-else-if="phase === 'loading'" class="aid-loading" aria-hidden="true">
        <div class="aid-skel-grid">
          <div v-for="n in 3" :key="n" class="card aid-skel">
            <div class="aid-skel-line w60"></div>
            <div class="aid-skel-line w90"></div>
            <div class="aid-skel-line w40"></div>
            <div class="aid-skel-box"></div>
          </div>
        </div>
        <p class="aid-loading-text">Estamos armando tu web… puede tardar unos segundos.</p>
      </div>

      <!-- PANTALLA 2 · TRES IDEAS, NO TRES COLORES -->
      <div v-else-if="phase === 'results'" ref="resultsRef" class="aid-results">
        <p v-if="actionError" class="aid-error" role="alert">{{ actionError }}</p>

        <div v-if="missing.length" class="aid-missing">
          <div class="aid-missing-head">
            <AppIcon name="info" :size="18" />
            <strong>Para que se vea mejor</strong>
          </div>
          <ul>
            <li v-for="m in missing" :key="m.code">
              <span>
                <strong>{{ m.label }}</strong>
                <small v-if="m.hint">{{ m.hint }}</small>
              </span>
              <button class="btn ghost btn-auto" type="button" @click="emit('navigate', missingTarget(m))">Completar</button>
            </li>
          </ul>
        </div>

        <p v-if="varietyNotice" class="aid-variety">
          <AppIcon name="sparkles" :size="14" aria-hidden="true" /> {{ varietyNotice }}
        </p>

        <div class="aid-grid">
          <AiIdeaCard
            v-for="p in proposals"
            :key="p.id"
            :proposal="p"
            :form="proposalForm(p)"
            :vars="proposalVars(p)"
            :template="proposalTemplate(p)"
            :shop-name="shopName"
            :initial="initial"
            :logo="logo"
            :cover="proposalCover(p)"
            :advanced="hasDesignAdvanced"
            :show-map="answers.must_have.includes('map')"
            :name-font="proposalNameFont(p)"
            :busy="busy"
            :selected="selectedId === p.id"
            :public-url="publicUrl"
            @preview="openPreview(p)"
            @choose="choose(p.id)"
          />
        </div>

        <AiCompareTable :proposals="proposals" :selected-id="selectedId" @choose="choose" />

        <div class="aid-actions">
          <button class="btn btn-auto" type="button" @click="anotherStyle">
            <AppIcon name="refresh" :size="16" /> Ver otro estilo
          </button>
          <button class="btn ghost btn-auto" type="button" @click="backToQuestions">
            <AppIcon name="chevron-left" :size="16" /> Volver a las preguntas
          </button>
        </div>
      </div>

      <!-- PANTALLA 3 · AJUSTAR SIN EMPEZAR DE CERO -->
      <div v-else-if="phase === 'adjust' && selectedProposal" class="aid-results">
        <p v-if="actionError" class="aid-error" role="alert">{{ actionError }}</p>
        <p class="aid-keep-note">
          <AppIcon name="check" :size="14" aria-hidden="true" />
          Elegiste <strong>{{ selectedProposal.thesis?.label || selectedProposal.label }}</strong>. Cambiá solo lo que quieras.
        </p>

        <div class="aid-adjust">
          <div class="aid-adjust-preview">
            <AiProposalCard
              :proposal="selectedProposal"
              :form="proposalForm(selectedProposal)"
              :vars="proposalVars(selectedProposal)"
              :template="proposalTemplate(selectedProposal)"
              :shop-name="shopName"
              :initial="initial"
              :logo="logo"
              :cover="proposalCover(selectedProposal)"
              :advanced="hasDesignAdvanced"
              :show-map="answers.must_have.includes('map')"
              :name-font="proposalNameFont(selectedProposal)"
              :busy="busy"
              :public-url="publicUrl"
              :autofill-default="autofillDefault"
              @preview="openPreview(selectedProposal)"
              @apply="apply"
              @change-style="anotherStyle"
              @refresh-images="redoWithPhotos"
            />
          </div>
          <div class="aid-adjust-controls">
            <AiAdjustPanel
              v-model="constraints"
              :pair-options="PAIR_OPTIONS"
              :has-logo="Boolean(logo)"
              :busy="refining"
              :dirty="adjustDirty"
              :applied="appliedLabels"
              @apply="refine()"
              @reset="resetAdjust"
            />
            <button class="btn ghost btn-auto" type="button" @click="backToResults">
              <AppIcon name="chevron-left" :size="16" /> Volver a las propuestas
            </button>
          </div>
        </div>
      </div>

      <!-- PANTALLA 4 · PUBLICADA, REVISADA Y COMPARTIBLE -->
      <AiPublishedPanel
        v-else-if="phase === 'published'"
        :checks="checks"
        :name="shopName"
        :description="description"
        :logo="logo"
        :public-url="publicUrl"
        :busy="Boolean(busy)"
        @navigate="emit('navigate', $event === 'images' ? 'design' : $event)"
        @revert="revertPublished"
        @copy="copyLink"
      />

      <!-- ERROR -->
      <div v-else class="card aid-error-box" role="alert">
        <AppIcon name="circle-alert" :size="24" />
        <div>
          <h2>No pudimos armar las propuestas</h2>
          <p>{{ errorMsg }}</p>
          <div class="aid-actions">
            <button class="btn btn-auto" type="button" @click="generate()">Reintentar</button>
            <button class="btn ghost btn-auto" type="button" @click="phase = 'ask'">Volver a las preguntas</button>
          </div>
        </div>
      </div>
    </template>

    <!-- Vista previa en grande -->
    <AiDevicePreview
      v-if="previewProposal"
      :proposal="previewProposal"
      :form="previewForm"
      :vars="previewVars"
      :template="previewTemplate"
      :shop-name="shopName"
      :initial="initial"
      :logo="logo"
      :cover="previewCover"
      :advanced="hasDesignAdvanced"
      :show-map="answers.must_have.includes('map')"
      :name-font="previewNameFont"
      :night-mode="previewProposal.night_mode"
      :public-url="publicUrl"
      @close="closePreview"
    />
  </div>
</template>
