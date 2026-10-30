<script setup>
import { ref, reactive, computed, nextTick, watch, onBeforeUnmount, onMounted } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import AiProposalCard from '../../components/ai/AiProposalCard.vue'
import AiIdeaCard from '../../components/ai/AiIdeaCard.vue'
import AiCompareTable from '../../components/ai/AiCompareTable.vue'
import AiAdjustPanel from '../../components/ai/AiAdjustPanel.vue'
import AiPublishedPanel from '../../components/ai/AiPublishedPanel.vue'
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

// Rubros del motor (ids de RUBROS en ai_design_recipes): el mensaje que se
// arma acá se traduce del otro lado, pero el id canónico es el que manda.
const RUBROS = [
  { id: 'comercio', label: 'Comercio o tienda', icon: 'tag', desc: 'Local, kiosco, mayorista' },
  { id: 'gastronomia', label: 'Comida y bebida', icon: 'coffee', desc: 'Restó, bar, panadería, delivery' },
  { id: 'indumentaria', label: 'Indumentaria y moda', icon: 'tag', desc: 'Ropa, calzado, accesorios' },
  { id: 'belleza', label: 'Belleza y estética', icon: 'flower', desc: 'Peluquería, uñas, maquillaje' },
  { id: 'salud', label: 'Salud y bienestar', icon: 'heart', desc: 'Consultorios, terapias, gym' },
  { id: 'construccion', label: 'Construcción y oficios', icon: 'wrench', desc: 'Obra, plomería, electricidad' },
  { id: 'seguridad', label: 'Seguridad y bomberos', icon: 'shield-check', desc: 'Seguridad industrial, EPP' },
  { id: 'tecnologia', label: 'Tecnología', icon: 'monitor', desc: 'Equipos, reparaciones, software' },
  { id: 'educacion', label: 'Educación', icon: 'graduation-cap', desc: 'Clases, cursos, talleres' },
  { id: 'turismo', label: 'Turismo y viajes', icon: 'map-pin', desc: 'Alojamiento, excursiones' },
  { id: 'mascotas', label: 'Mascotas', icon: 'paw-print', desc: 'Veterinaria, peluquería, alimento' },
  { id: 'arte', label: 'Arte y diseño', icon: 'palette', desc: 'Muebles, deco, regalos, talleres' },
  { id: 'servicios_profesionales', label: 'Servicios profesionales', icon: 'file-text', desc: 'Estudios, consultoría, oficios' },
  { id: 'otro', label: 'Otra cosa', icon: 'sparkles', desc: 'Te lo armamos igual' }
]
const GOALS = [
  { id: 'vender_online', label: 'Vender online', icon: 'credit-card', desc: 'Que puedan comprar desde la web' },
  { id: 'mostrar_servicios', label: 'Mostrar mis servicios', icon: 'wrench', desc: 'Explicar qué hacés y cuánto sale' },
  { id: 'conseguir_consultas', label: 'Recibir consultas', icon: 'message-circle', desc: 'Que te escriban o te llamen' },
  { id: 'dar_confianza', label: 'Dar confianza', icon: 'shield-check', desc: 'Que vean que sos un negocio serio' },
  { id: 'mostrar_trabajos', label: 'Mostrar mis trabajos', icon: 'images', desc: 'Fotos de lo que hacés' }
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
// elegido a mano siempre gana).
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
// Los cuatro pasos del wizard. `icon`/`title`/`subtitle` encabezan cada
// pantalla; `hint` es la ayuda corta debajo del título.
const STEPS = [
  { id: 'business', icon: 'store', title: 'Tu negocio', subtitle: 'Contanos qué hacés y te armamos una web', hint: 'Elegí el rubro que más se parezca al tuyo.' },
  { id: 'goal', icon: 'flag', title: 'Qué buscás', subtitle: 'Para qué querés la web y a quién le hablás', hint: 'Podés marcar más de un objetivo.' },
  { id: 'style', icon: 'palette', title: 'Tu estilo', subtitle: 'Cómo querés que se sienta tu web', hint: 'Se puede cambiar después sin rehacer nada.' },
  { id: 'must', icon: 'checklist', title: 'Lo que no puede faltar', subtitle: 'Las secciones que tu cliente tiene que encontrar', hint: 'Todo lo que marques aparece en la propuesta.' }
]
// Tipografías que el motor sabe aplicar (ids de TYPE_PAIRS en el backend).
const PAIR_OPTIONS = [
  { id: 'grotesk-clean', label: 'Grotesk limpio', icon: 'type', desc: 'Neutra y actual' },
  { id: 'serif-editorial', label: 'Serif editorial', icon: 'type', desc: 'Con carácter, tipo revista' },
  { id: 'serif-classic', label: 'Serif clásico', icon: 'type', desc: 'Sobria y elegante' },
  { id: 'display-heavy', label: 'Peso máximo', icon: 'type', desc: 'Títulos que se imponen' },
  { id: 'geometric', label: 'Geométrica', icon: 'type', desc: 'Moderna y limpia' },
  { id: 'warm-serif', label: 'Serif cálida', icon: 'type', desc: 'Cercana, con detalle' }
]

const EMPTY = () => ({ rubro: '', goals: [], tone: '', style_hint: [], audience: '', must_have: [], content_hint: '' })
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

// ---------- Wizard ----------
const step = ref(0)
const stepTitle = ref(null)
// Claves del pedido que el dueño quitó a mano antes de enviar.
const blockHidden = reactive({})
const showJson = ref(false)
// Lo que decidió el MCP: skills de diseño aplicados a la tanda.
const mcp = ref(null)

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
const progressStep = computed(() => (phase.value === 'ask' ? step.value + 1 : STEPS.length))
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
  return `Paso ${step.value + 1} de ${STEPS.length}: ${STEPS[step.value].title}.`
})

const currentStep = computed(() => STEPS[step.value])
const stepValid = computed(() => {
  if (step.value === 0) return Boolean(answers.rubro)
  if (step.value === 1) return answers.goals.length > 0
  if (step.value === 2) return Boolean(answers.tone)
  return true
})
const canSubmit = computed(() => Boolean(answers.rubro && answers.goals.length && answers.tone))
const hasAnswers = computed(() => Boolean(
  answers.rubro || answers.goals.length || answers.tone || answers.style_hint.length ||
  answers.audience || answers.must_have.length || answers.content_hint
))

// ---------- Prompt estructurado ----------
// Cada respuesta del wizard es una clave del pedido que se manda al MCP.
// `blockHidden` deja quitar una clave antes de enviar (volver a responder
// ese paso la restaura).
const rubroMeta = computed(() => RUBROS.find((r) => r.id === answers.rubro) || null)
const toneMeta = computed(() => TONES.find((t) => t.id === answers.tone) || null)
const audienceLabel = computed(() => AUDIENCES.find((a) => a.id === answers.audience)?.label || '')
const goalLabels = computed(() => answers.goals.map((id) => GOALS.find((g) => g.id === id)?.label).filter(Boolean))
const mustLabels = computed(() => answers.must_have.map((id) => MUST_HAVE.find((m) => m.id === id)?.label).filter(Boolean))

const prompt = computed(() => {
  const p = {}
  if (!blockHidden.rubro && answers.rubro) p.rubro = answers.rubro
  if (!blockHidden.goals && answers.goals.length) p.goals = [...answers.goals]
  if (!blockHidden.tone && answers.tone) p.tone = answers.tone
  if (!blockHidden.audience && answers.audience) p.audience = answers.audience
  if (!blockHidden.must_have && answers.must_have.length) p.must_have = [...answers.must_have]
  const notes = String(answers.content_hint || '').trim()
  if (!blockHidden.notes && notes) p.notes = notes
  return p
})
const promptJson = computed(() => JSON.stringify(prompt.value, null, 2))

const BLOCK_ROWS = computed(() => [
  { id: 'rubro', label: 'Rubro', key: 'rubro', icon: 'tag', value: rubroMeta.value?.label || '' },
  { id: 'goals', label: 'Objetivo', key: 'goals', icon: 'flag', value: goalLabels.value.join(', ') },
  { id: 'tone', label: 'Tono', key: 'tone', icon: 'palette', value: toneMeta.value?.label || '' },
  { id: 'audience', label: 'Audiencia', key: 'audience', icon: 'users', value: audienceLabel.value },
  { id: 'must_have', label: 'Imprescindible', key: 'must_have', icon: 'checklist', value: mustLabels.value.join(', ') },
  { id: 'notes', label: 'Notas', key: 'notes', icon: 'file-text', value: String(answers.content_hint || '').trim() }
])
const blocks = computed(() => BLOCK_ROWS.value.filter((row) => row.id in prompt.value))

function restoreBlock(id) {
  delete blockHidden[id]
}
function removeBlock(block) {
  blockHidden[block.id] = true
  if (block.id === 'rubro') answers.rubro = ''
  else if (block.id === 'goals') answers.goals = []
  else if (block.id === 'tone') answers.tone = ''
  else if (block.id === 'audience') answers.audience = ''
  else if (block.id === 'must_have') answers.must_have = []
  else if (block.id === 'notes') answers.content_hint = ''
}

// ---------- Selección de cada paso ----------
function pickRubro(id) {
  answers.rubro = answers.rubro === id ? '' : id
  restoreBlock('rubro')
}
function toggleGoal(id) {
  const i = answers.goals.indexOf(id)
  if (i >= 0) answers.goals.splice(i, 1)
  else answers.goals.push(id)
  restoreBlock('goals')
}
function pickTone(id) {
  answers.tone = answers.tone === id ? '' : id
  restoreBlock('tone')
}
function pickAudience(id) {
  answers.audience = answers.audience === id ? '' : id
  restoreBlock('audience')
}
function toggleHint(id) {
  const i = answers.style_hint.indexOf(id)
  if (i >= 0) { answers.style_hint.splice(i, 1); return }
  if (answers.style_hint.length >= 2) answers.style_hint.shift()
  answers.style_hint.push(id)
}
function toggleMustHave(id) {
  const i = answers.must_have.indexOf(id)
  if (i >= 0) answers.must_have.splice(i, 1)
  else answers.must_have.push(id)
  restoreBlock('must_have')
}
function onNotes() {
  restoreBlock('notes')
}

function goStep(index) {
  if (index < 0 || index >= STEPS.length) return
  if (index > step.value && !stepValid.value) return
  step.value = index
  nextTick(() => stepTitle.value?.focus?.())
}
function nextStep() {
  if (!stepValid.value) return
  if (step.value < STEPS.length - 1) goStep(step.value + 1)
  else submit()
}
function prevStep() {
  goStep(step.value - 1)
}
function onStepKey(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  const tag = event.target?.tagName
  if (tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'A' || tag === 'INPUT') return
  event.preventDefault()
  nextStep()
}

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
    answers.rubro = RUBROS.some((r) => r.id === saved.rubro) ? saved.rubro : base.rubro
    answers.goals = Array.isArray(saved.goals) ? saved.goals.filter((g) => GOALS.some((o) => o.id === g)).slice(0, 2) : []
    answers.tone = TONES.some((t) => t.id === saved.tone) ? saved.tone : base.tone
    answers.style_hint = Array.isArray(saved.style_hint)
      ? saved.style_hint.filter((h) => STYLE_HINTS.some((o) => o.id === h)).slice(0, 2)
      : []
    answers.audience = AUDIENCES.some((a) => a.id === saved.audience) ? saved.audience : base.audience
    answers.must_have = Array.isArray(saved.must_have) ? saved.must_have.filter((m) => MUST_HAVE.some((o) => o.id === m)) : []
    answers.content_hint = typeof saved.content_hint === 'string' ? saved.content_hint.slice(0, 160) : ''
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

// ---------- Prefill: lo que la IA ya sabe (paso 1) ----------
async function loadPrefill() {
  if (!canUse.value || prefill.value) return
  try {
    const data = await storesApi.aiDesignPrefill()
    prefill.value = data
    //La deducción solo rellena lo que el dueño no eligió: nunca pisa su
    //respuesta guardada.
    if (!answers.rubro && RUBROS.some((r) => r.id === data?.rubro)) answers.rubro = data.rubro
    if (!answers.goals.length && Array.isArray(data?.goals)) {
      answers.goals = data.goals.filter((goal) => GOALS.some((o) => o.id === goal)).slice(0, 2)
    }
    if (Array.isArray(data?.checks)) checks.value = data.checks
  } catch { /* sin prefill el wizard funciona igual */ }
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
async function submit(extraSeed = 0) {
  if (phase.value === 'loading' || !canSubmit.value) return
  const seq = ++requestSeq
  phase.value = 'loading'
  errorMsg.value = ''
  actionError.value = ''
  published.value = null
  selectedId.value = ''
  proposals.value = []
  previewProposal.value = null
  mcp.value = null
  clearTimeout(timer)
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(Object.assign(new Error('timeout'), { aidTimeout: true })), 20000)
  })
  try {
    const body = { prompt: prompt.value, history: [] }
    if (extraSeed) body.seed = extraSeed
    const data = await Promise.race([storesApi.aiDesignMcp(body), timeout])
    if (seq !== requestSeq) return
    if (!data || !Array.isArray(data.proposals) || !data.proposals.length) throw new Error('empty')
    seed.value = data.seed
    missing.value = Array.isArray(data.missing) ? data.missing : []
    checks.value = Array.isArray(data.checks) ? data.checks : checks.value
    proposals.value = data.proposals
    mcp.value = data.mcp || null
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

function anotherStyle() {
  track('explore', { meta: { count: proposals.value.length } })
  submit((seed.value || 0) + 1)
}
function redoWithPhotos() {
  submit(seed.value || 0)
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
    cover: proposal?.cover?.mode === 'logo' ? 'logo' : 'auto',
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
  track('step_done', { proposal_id: id, step: STEPS.length + 1 })
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
  Object.keys(blockHidden).forEach((key) => delete blockHidden[key])
  try { localStorage.removeItem(storageKey.value) } catch { /* storage bloqueado */ }
  proposals.value = []
  missing.value = []
  seed.value = null
  mcp.value = null
  published.value = null
  selectedId.value = ''
  constraints.value = {}
  initialConstraints.value = {}
  actionError.value = ''
  errorMsg.value = ''
  previewProposal.value = null
  phase.value = 'ask'
  step.value = 0
  nextTick(() => stepTitle.value?.focus?.())
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
        <h1><AppIcon name="sparkles" :size="20" /> Diseño asistido</h1>
        <p>Contanos qué hacés y te armamos una web. Después la ajustás sin empezar de cero.</p>
        <span v-if="phase === 'published'" class="aid-pub-chip"><AppIcon name="circle-check" :size="13" /> Publicada</span>
      </div>
      <button v-if="phase !== 'ask' || hasAnswers" class="btn ghost btn-auto" type="button" @click="startOver">
        <AppIcon name="refresh" :size="16" /> Empezar de nuevo
      </button>
    </header>

    <div v-if="!canUse" class="empty">
      <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
      <h3>El diseño asistido viene con tu plan</h3>
      <p>Sumá el beneficio desde Mi plan y volvé a entrar.</p>
      <button class="btn btn-auto" type="button" @click="emit('navigate', 'plans')">Ver planes</button>
    </div>

    <template v-else>
      <p class="aid-live" aria-live="polite">{{ liveMessage }}</p>

      <!-- PANTALLA 1 · WIZARD DE 4 PASOS + PEDIDO ACUMULADO -->
      <div v-if="phase === 'ask'" class="aidw" @keydown="onStepKey">
        <div class="aidw-main">
          <ol class="aidw-bar" aria-label="Progreso del pedido">
            <li
              v-for="(s, i) in STEPS"
              :key="s.id"
              class="aidw-bar-item"
              :class="{ done: i < step, now: i === step }"
            >
              <button
                type="button"
                class="aidw-bar-btn"
                :aria-current="i === step ? 'step' : undefined"
                :aria-label="`Paso ${i + 1}: ${s.title}`"
                :disabled="i > step && !stepValid"
                @click="goStep(i)"
              >
                <span class="aidw-bar-num" aria-hidden="true">
                  <AppIcon v-if="i < step" name="check" :size="13" :stroke="2.5" />
                  <template v-else>{{ i + 1 }}</template>
                </span>
                <span class="aidw-bar-label">{{ s.title }}</span>
              </button>
            </li>
          </ol>

          <section class="aidw-step" :aria-labelledby="`aidw-title-${currentStep.id}`">
            <header class="aidw-step-head">
              <span class="aidw-step-ico" aria-hidden="true"><AppIcon :name="currentStep.icon" :size="20" /></span>
              <div class="aidw-step-text">
                <h2 :id="`aidw-title-${currentStep.id}`" ref="stepTitle" tabindex="-1">{{ currentStep.title }}</h2>
                <p>{{ currentStep.subtitle }}</p>
              </div>
            </header>
            <p class="aidw-step-hint">{{ currentStep.hint }}</p>

            <!-- PASO 1 · TU NEGOCIO -->
            <div v-if="currentStep.id === 'business'" class="aidw-grid rubros" role="radiogroup" aria-label="Rubro de tu negocio">
              <button
                v-for="r in RUBROS"
                :key="r.id"
                type="button"
                role="radio"
                class="aidw-card"
                :class="{ on: answers.rubro === r.id }"
                :aria-checked="answers.rubro === r.id"
                @click="pickRubro(r.id)"
              >
                <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="r.icon" :size="18" /></span>
                <span class="aidw-card-txt">
                  <strong>{{ r.label }}</strong>
                  <small>{{ r.desc }}</small>
                </span>
                <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.rubro === r.id" name="check" :size="13" :stroke="2.5" /></span>
              </button>
            </div>

            <!-- PASO 2 · QUÉ BUSCÁS -->
            <template v-else-if="currentStep.id === 'goal'">
              <p class="aidw-field-title">¿Qué querés lograr con la web?</p>
              <div class="aidw-grid goals" role="group" aria-label="¿Qué querés lograr con la web?">
                <button
                  v-for="g in GOALS"
                  :key="g.id"
                  type="button"
                  class="aidw-card"
                  :class="{ on: answers.goals.includes(g.id) }"
                  :aria-pressed="answers.goals.includes(g.id)"
                  @click="toggleGoal(g.id)"
                >
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="g.icon" :size="18" /></span>
                  <span class="aidw-card-txt">
                    <strong>{{ g.label }}</strong>
                    <small>{{ g.desc }}</small>
                  </span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.goals.includes(g.id)" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="aidw-field-title">¿A quién le hablás? <span class="aidw-opt">Opcional</span></p>
              <div class="aidw-grid audiences" role="radiogroup" aria-label="¿A quién le hablás?">
                <button
                  v-for="a in AUDIENCES"
                  :key="a.id"
                  type="button"
                  role="radio"
                  class="aidw-card"
                  :class="{ on: answers.audience === a.id }"
                  :aria-checked="answers.audience === a.id"
                  @click="pickAudience(a.id)"
                >
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="a.icon" :size="18" /></span>
                  <span class="aidw-card-txt">
                    <strong>{{ a.label }}</strong>
                    <small>{{ a.desc }}</small>
                  </span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.audience === a.id" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
            </template>

            <!-- PASO 3 · TU ESTILO -->
            <template v-else-if="currentStep.id === 'style'">
              <p class="aidw-field-title">¿Cómo se tiene que sentir?</p>
              <div class="aidw-grid tones" role="radiogroup" aria-label="¿Cómo se tiene que sentir tu web?">
                <button
                  v-for="t in TONES"
                  :key="t.id"
                  type="button"
                  role="radio"
                  class="aidw-card tone"
                  :class="{ on: answers.tone === t.id }"
                  :aria-checked="answers.tone === t.id"
                  @click="pickTone(t.id)"
                >
                  <span class="aidw-card-ico big" aria-hidden="true"><AppIcon :name="t.icon" :size="22" /></span>
                  <span class="aidw-card-txt">
                    <strong>{{ t.label }}</strong>
                    <small>{{ t.desc }}</small>
                  </span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.tone === t.id" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="aidw-field-title">¿Qué te importa más? <span class="aidw-opt">Opcional, hasta dos</span></p>
              <div class="aidw-chips" role="group" aria-label="¿Qué te importa más?">
                <button
                  v-for="h in STYLE_HINTS"
                  :key="h.id"
                  type="button"
                  class="aidw-chip"
                  :class="{ on: answers.style_hint.includes(h.id) }"
                  :aria-pressed="answers.style_hint.includes(h.id)"
                  @click="toggleHint(h.id)"
                >
                  <AppIcon :name="h.icon" :size="15" aria-hidden="true" /> {{ h.label }}
                </button>
              </div>
            </template>

            <!-- PASO 4 · LO QUE NO PUEDE FALTAR -->
            <template v-else>
              <p class="aidw-field-title">Marcá lo que tu cliente tiene que encontrar</p>
              <div class="aidw-grid must" role="group" aria-label="Lo que no puede faltar">
                <button
                  v-for="m in MUST_HAVE"
                  :key="m.id"
                  type="button"
                  class="aidw-card"
                  :class="{ on: answers.must_have.includes(m.id) }"
                  :aria-pressed="answers.must_have.includes(m.id)"
                  @click="toggleMustHave(m.id)"
                >
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="m.icon" :size="18" /></span>
                  <span class="aidw-card-txt">
                    <strong>{{ m.label }}</strong>
                    <small>{{ m.desc }}</small>
                  </span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.must_have.includes(m.id)" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="aidw-field-title">Contalo con tus palabras <span class="aidw-opt">Opcional</span></p>
              <textarea
                v-model="answers.content_hint"
                class="aidw-input"
                rows="3"
                maxlength="160"
                aria-label="Contanos en dos líneas qué hacés y a quién le vendés"
                placeholder="Ej.: ferretería de barrio, vendemos herramientas y pintura; el que más nos escribe es el que arregla en su casa."
                @input="onNotes"
              ></textarea>
              <p class="aidw-note">Lo usamos para escribir el texto de la web. No inventamos datos: solo lo que nos contás.</p>
            </template>

            <div class="aidw-nav">
              <button v-if="step > 0" type="button" class="btn ghost btn-auto" @click="prevStep">
                <AppIcon name="chevron-left" :size="16" /> Atrás
              </button>
              <button
                v-if="step < STEPS.length - 1"
                type="button"
                class="btn btn-auto aidw-next"
                :disabled="!stepValid"
                @click="nextStep"
              >
                Siguiente <AppIcon name="chevron-right" :size="16" />
              </button>
              <button
                v-else
                type="button"
                class="btn btn-auto aidw-next"
                :disabled="!canSubmit"
                @click="submit()"
              >
                <AppIcon name="sparkles" :size="16" /> Generar propuesta
              </button>
              <span class="aidw-nav-note">{{ step + 1 }} de {{ STEPS.length }}</span>
            </div>
          </section>
        </div>

        <!-- PEDIDO ESTRUCTURADO -->
        <aside class="aidw-ask" aria-label="Tu pedido">
          <header class="aidw-ask-head">
            <h3><AppIcon name="clipboard-list" :size="16" /> Tu pedido</h3>
            <span class="aidw-ask-count">{{ blocks.length }}</span>
          </header>
          <p v-if="!blocks.length" class="aidw-ask-empty">
            Cada respuesta arma una clave del pedido. El MCP lee esta estructura y elige el estilo de diseño.
          </p>
          <ul v-else class="aidw-bubbles">
            <li v-for="b in blocks" :key="b.id" class="aidw-bubble">
              <span class="aidw-bubble-ico" aria-hidden="true"><AppIcon :name="b.icon" :size="14" /></span>
              <div class="aidw-bubble-body">
                <span class="aidw-bubble-label">{{ b.label }}</span>
                <span class="aidw-bubble-text">{{ b.value }}</span>
                <code class="aidw-bubble-key">{{ b.key }}: {{ b.key === 'goals' || b.key === 'must_have' ? '[]' : '""' }}</code>
              </div>
              <div class="aidw-bubble-actions">
                <button type="button" class="aidw-icon-btn" :aria-label="`Quitar ${b.label}`" title="Quitar" @click="removeBlock(b)"><AppIcon name="trash" :size="14" /></button>
              </div>
            </li>
          </ul>
          <button v-if="blocks.length" type="button" class="aidw-json-btn" :aria-expanded="showJson" @click="showJson = !showJson">
            <AppIcon :name="showJson ? 'chevron-up' : 'chevron-down'" :size="14" />
            {{ showJson ? 'Ocultar' : 'Ver' }} la estructura de datos
          </button>
          <pre v-if="showJson && blocks.length" class="aidw-json" aria-label="Pedido en formato de datos">{{ promptJson }}</pre>
          <button type="button" class="btn btn-auto aidw-send" :disabled="!canSubmit" @click="submit()">
            <AppIcon name="send" :size="16" /> Generar propuesta
          </button>
          <p class="aidw-ask-note">El MCP elige el estilo de diseño a partir de este pedido.</p>
        </aside>
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

        <div v-if="mcp?.styles?.length" class="aid-mcp">
          <div class="aid-mcp-head">
            <AppIcon name="gem" :size="16" aria-hidden="true" />
            <strong>El MCP eligió {{ mcp.styles.length === 1 ? 'este estilo' : `${mcp.styles.length} estilos` }} de su catálogo</strong>
          </div>
          <ul class="aid-mcp-list">
            <li v-for="s in mcp.styles" :key="s.slug">
              <strong>{{ s.nombre }}</strong>
              <span class="aid-mcp-cat">{{ s.categoria }}</span>
              <span v-if="s.tags?.length" class="aid-mcp-tags">{{ s.tags.join(' · ') }}</span>
            </li>
          </ul>
        </div>

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
            <button class="btn btn-auto" type="button" @click="submit()">Reintentar</button>
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

<style scoped>
.aidw { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 18px; align-items: start; }
@media (max-width: 980px) {
  .aidw { grid-template-columns: minmax(0, 1fr); }
  .aidw-ask { order: -1; }
}

/* Barra de progreso */
.aidw-bar { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 14px; padding: 0; list-style: none; }
.aidw-bar-item { flex: 1 1 120px; min-width: 0; }
.aidw-bar-btn {
  display: flex; align-items: center; gap: 8px; width: 100%; min-width: 0;
  padding: 9px 10px; border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--surface); color: var(--muted); font: inherit; font-size: 12.5px; font-weight: 600;
  cursor: pointer; text-align: left;
  transition: border-color var(--dur) var(--ease-out), background var(--dur) var(--ease-out), color var(--dur) var(--ease-out);
}
.aidw-bar-btn:hover:not(:disabled) { border-color: var(--line-strong); color: var(--ink-2); }
.aidw-bar-btn:focus-visible { outline: var(--focus-ring); outline-offset: 2px; }
.aidw-bar-btn:disabled { cursor: not-allowed; opacity: .6; }
.aidw-bar-num {
  display: grid; place-items: center; flex: none;
  width: 22px; height: 22px; border-radius: 999px;
  background: var(--card); border: 1px solid var(--line);
  font-size: 11.5px; font-variant-numeric: tabular-nums;
}
.aidw-bar-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.aidw-bar-item.now .aidw-bar-btn { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }
.aidw-bar-item.now .aidw-bar-num { background: var(--brand-500); border-color: var(--brand-500); color: #fff; }
.aidw-bar-item.done .aidw-bar-btn { color: var(--ink-2); }
.aidw-bar-item.done .aidw-bar-num { background: var(--brand-500); border-color: var(--brand-500); color: #fff; }

/* Paso */
.aidw-step {
  display: flex; flex-direction: column; gap: 14px; min-width: 0;
  padding: 18px; border: 1px solid var(--line); border-radius: var(--radius-lg);
  background: var(--card); box-shadow: var(--shadow-sm);
}
.aidw-step-head { display: flex; align-items: flex-start; gap: 12px; min-width: 0; }
.aidw-step-ico {
  display: grid; place-items: center; flex: none;
  width: 40px; height: 40px; border-radius: 12px;
  background: var(--brand-soft); color: var(--brand-ink);
  border: 1px solid var(--brand-soft-line);
}
.aidw-step-text { min-width: 0; }
.aidw-step-text h2 { margin: 0; font-size: 18px; line-height: 1.25; }
.aidw-step-text h2:focus { outline: none; }
.aidw-step-text h2:focus-visible { outline: var(--focus-ring); outline-offset: 3px; border-radius: 4px; }
.aidw-step-text p { margin: 2px 0 0; color: var(--muted); font-size: 13px; }
.aidw-step-hint { margin: 0; color: var(--muted); font-size: 12.5px; }
.aidw-field-title { margin: 4px 0 0; font-size: 13px; font-weight: 600; color: var(--ink-2); }
.aidw-opt { font-weight: 500; color: var(--muted); font-size: 11.5px; }

/* Grillas de selección */
.aidw-grid { display: grid; gap: 10px; min-width: 0; }
.aidw-grid.rubros { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.aidw-grid.goals { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.aidw-grid.audiences { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.aidw-grid.tones { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.aidw-grid.must { grid-template-columns: repeat(3, minmax(0, 1fr)); }
@media (max-width: 1180px) {
  .aidw-grid.rubros, .aidw-grid.must { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .aidw-grid.rubros, .aidw-grid.goals, .aidw-grid.audiences, .aidw-grid.tones, .aidw-grid.must { grid-template-columns: minmax(0, 1fr); }
}

.aidw-card {
  position: relative; display: flex; align-items: flex-start; gap: 10px; min-width: 0;
  padding: 12px; border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--card); color: var(--ink); font: inherit; text-align: left;
  cursor: pointer;
  transition: border-color var(--dur) var(--ease-out), background var(--dur) var(--ease-out), box-shadow var(--dur) var(--ease-out);
}
.aidw-card:hover { border-color: var(--line-strong); background: var(--surface); }
.aidw-card:focus-visible { outline: var(--focus-ring); outline-offset: 2px; }
.aidw-card.on {
  border-color: var(--brand-500);
  background: var(--brand-soft);
  box-shadow: 0 0 0 1px var(--brand-500) inset;
}
.aidw-card-ico {
  display: grid; place-items: center; flex: none;
  width: 34px; height: 34px; border-radius: 10px;
  background: var(--surface); border: 1px solid var(--line); color: var(--ink-2);
}
.aidw-card-ico.big { width: 40px; height: 40px; border-radius: 12px; }
.aidw-card.on .aidw-card-ico { background: var(--card); border-color: var(--brand-500); color: var(--brand-ink); }
.aidw-card-txt { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.aidw-card-txt strong { font-size: 13.5px; line-height: 1.3; }
.aidw-card-txt small { color: var(--muted); font-size: 11.5px; line-height: 1.35; }
.aidw-card-check {
  position: absolute; top: 9px; right: 9px;
  display: grid; place-items: center;
  width: 18px; height: 18px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--card); color: #fff;
}
.aidw-card.on .aidw-card-check { background: var(--brand-500); border-color: var(--brand-500); }
.aidw-card.tone { padding: 14px; }

/* Chips */
.aidw-chips { display: flex; flex-wrap: wrap; gap: 8px; min-width: 0; }
.aidw-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 999px;
  background: var(--card); color: var(--ink-2); font: inherit; font-size: 12.5px; font-weight: 600;
  cursor: pointer;
  transition: border-color var(--dur) var(--ease-out), background var(--dur) var(--ease-out), color var(--dur) var(--ease-out);
}
.aidw-chip:hover { border-color: var(--line-strong); }
.aidw-chip:focus-visible { outline: var(--focus-ring); outline-offset: 2px; }
.aidw-chip.on { border-color: var(--brand-500); background: var(--brand-soft); color: var(--brand-ink); }

.aidw-input {
  width: 100%; min-width: 0; padding: 11px 12px;
  border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--surface); color: var(--ink); font: inherit; font-size: 13px;
  resize: vertical;
}
.aidw-input:focus-visible { outline: var(--focus-ring); outline-offset: 1px; border-color: var(--brand-500); }
.aidw-note { margin: 0; color: var(--muted); font-size: 11.5px; }

/* Navegación del paso */
.aidw-nav { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 4px; padding-top: 14px; border-top: 1px solid var(--line-soft); }
.aidw-next { margin-left: auto; }
.aidw-nav-note { color: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }

/* Pedido acumulado */
.aidw-ask {
  display: flex; flex-direction: column; gap: 12px; min-width: 0;
  padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-lg);
  background: var(--surface);
  position: sticky; top: 12px;
}
@media (max-width: 980px) { .aidw-ask { position: static; } }
.aidw-ask-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.aidw-ask-head h3 { display: flex; align-items: center; gap: 7px; margin: 0; font-size: 14px; }
.aidw-ask-count {
  display: grid; place-items: center; min-width: 22px; height: 22px; padding: 0 7px;
  border-radius: 999px; background: var(--card); border: 1px solid var(--line);
  color: var(--muted); font-size: 11.5px; font-variant-numeric: tabular-nums;
}
.aidw-ask-empty { margin: 0; color: var(--muted); font-size: 12.5px; line-height: 1.5; }
.aidw-bubbles { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0; list-style: none; }
.aidw-bubble {
  display: flex; gap: 8px; min-width: 0;
  padding: 10px; border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--card);
}
.aidw-bubble-ico { flex: none; color: var(--muted); padding-top: 2px; }
.aidw-bubble-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1 1 auto; }
.aidw-bubble-label { color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.aidw-bubble-text { font-size: 12.5px; line-height: 1.45; overflow-wrap: anywhere; }
.aidw-bubble-key {
  margin-top: 2px; color: var(--muted); font-family: ui-monospace, 'SFMono-Regular', Menlo, monospace;
  font-size: 10.5px; overflow-wrap: anywhere;
}
.aidw-json-btn {
  display: inline-flex; align-items: center; gap: 6px; align-self: flex-start;
  padding: 4px 8px; border: 1px dashed var(--line-strong); border-radius: 8px;
  background: transparent; color: var(--ink-2); font: inherit; font-size: 11.5px; font-weight: 600;
  cursor: pointer;
}
.aidw-json-btn:hover { border-color: var(--brand-500); color: var(--brand-ink); }
.aidw-json-btn:focus-visible { outline: var(--focus-ring); outline-offset: 2px; }
.aidw-json {
  margin: 0; padding: 10px; max-height: 220px; overflow: auto;
  border: 1px solid var(--line); border-radius: var(--radius); background: var(--card);
  color: var(--ink-2); font-family: ui-monospace, 'SFMono-Regular', Menlo, monospace;
  font-size: 11px; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere;
}
.aidw-bubble-actions { display: flex; gap: 4px; margin-left: auto; }
.aidw-icon-btn {
  display: grid; place-items: center; width: 28px; height: 28px;
  border: 1px solid transparent; border-radius: 8px;
  background: transparent; color: var(--muted); cursor: pointer;
  transition: background var(--dur) var(--ease-out), color var(--dur) var(--ease-out);
}
.aidw-icon-btn:hover { background: var(--surface); color: var(--ink-2); border-color: var(--line); }
.aidw-icon-btn:focus-visible { outline: var(--focus-ring); outline-offset: 1px; }
.aidw-send { width: 100%; justify-content: center; }
.aidw-send:disabled { opacity: .55; cursor: not-allowed; }
.aidw-ask-note { margin: 0; color: var(--muted); font-size: 11.5px; text-align: center; }

/* Decisión del MCP sobre la tanda */
.aid-mcp {
  display: flex; flex-direction: column; gap: 8px; min-width: 0;
  padding: 14px 16px; border: 1px solid var(--brand-soft-line); border-radius: var(--radius-lg);
  background: var(--brand-soft);
}
.aid-mcp-head { display: flex; align-items: center; gap: 8px; color: var(--brand-ink); font-size: 13px; }
.aid-mcp-list { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; list-style: none; }
.aid-mcp-list li {
  display: inline-flex; flex-wrap: wrap; align-items: baseline; gap: 6px; min-width: 0;
  padding: 6px 10px; border: 1px solid var(--line); border-radius: 999px;
  background: var(--card); font-size: 12px;
}
.aid-mcp-cat {
  padding: 1px 7px; border-radius: 999px; background: var(--surface);
  color: var(--muted); font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
}
.aid-mcp-tags { color: var(--muted); font-size: 11px; }
</style>
