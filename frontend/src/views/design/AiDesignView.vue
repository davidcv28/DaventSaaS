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
import { authApi } from '../../api/auth.api.js'
import { locationsApi } from '../../api/locations.api.js'
import {
  storesApi, CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  resolveStoreTemplate, allowedTemplatesFor, publicStoreUrl,
  validateLogoFile, validateImageFile, LOGO_ACCEPT
} from '../../api/stores.api.js'
import { http } from '../../api/http.js'
import {
  RUBROS, GOALS, TONES, AUDIENCES, STYLE_HINTS, SECTIONS, PAIR_OPTIONS,
  emptyAssistAnswers as EMPTY, resolvedTone as toneOf,
  buildPrompt, suggestDescription as suggestDesc
} from '../../composables/useAiAssist.js'
import '../../assets/ai-design.css'

const props = defineProps({
  plan: { type: Object, default: null }
})
const emit = defineEmits(['applied', 'navigate'])

const store = useStoreStore()

// Rubros, objetivos, tonos, audiencias y secciones vienen del composable
// compartido useAiAssist (los ids son canónicos del motor de diseño).
// Los pasos del asistente: bienvenida + 4 preguntas en lenguaje llano.
// `optional` habilita el botón "Saltar".
const STEPS = [
  { id: 'welcome', icon: 'sparkles', title: 'Bienvenida', subtitle: 'Te armamos tu web paso a paso', hint: '' },
  { id: 'business', icon: 'store', title: 'Tu negocio', subtitle: 'Lo básico: nombre, rubro y cómo te contactan', hint: 'Esto queda guardado en tu web, no solo en el diseño.' },
  { id: 'content', icon: 'file-text', title: 'Qué vendés', subtitle: 'Una descripción corta y tus fotos principales', hint: 'Todo se puede cambiar después.', optional: true },
  { id: 'sections', icon: 'checklist', title: 'Qué mostrar', subtitle: 'Las secciones que tu cliente tiene que encontrar', hint: 'Lo que marques aparece en la web.', optional: true },
  { id: 'style', icon: 'palette', title: 'Tu estilo', subtitle: 'Cómo querés que se sienta tu web', hint: 'Elegí sensaciones, no colores: el diseño se arma solo.' }
]
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
const askOpen = ref(false)
const showJson = ref(false)
// Lo que decidió el catálogo/MCP sobre la tanda.
const mcp = ref(null)
// Persistencia de datos del negocio (pasos 2-4 escriben de verdad).
const savingStep = ref(false)
const saveError = ref('')
// Selects de ubicación (paso negocio).
const provinces = ref([])
const cities = ref([])
const citiesLoading = ref(false)
// Uploads inline (paso contenido).
const logoInput = ref(null)
const coverInput = ref(null)
const logoBusy = ref(false)
const coverBusy = ref(false)
const mediaErr = ref('')

let requestSeq = 0
let timer = null
onBeforeUnmount(() => {
  clearTimeout(timer)
})

const benefits = computed(() => props.plan?.benefits || {})
const hasDesignAdvanced = computed(() => Boolean(benefits.value.has_design_advanced))
const canUse = computed(() => Boolean(props.plan?.isCurrent && benefits.value.has_customization && benefits.value.has_ai_design))
const allowed = computed(() => allowedTemplatesFor(benefits.value))
const shopName = computed(() => answers.name.trim() || store.customization.display_name || store.store?.business_name || prefill.value?.name || 'Tu negocio')
const initial = computed(() => (shopName.value || 'T').slice(0, 1).toUpperCase())
const logo = computed(() => store.customization.logo || '')
const cover = computed(() => store.customization.cover || '')
const description = computed(() => String(store.customization.description || '').trim())
const storeId = computed(() => store.store?.id || '')
// La vista previa corre SIEMPRE en el mismo origen (alias /<slug>): la web
// real, no una maqueta.
const publicUrl = computed(() => (store.store?.slug ? publicStoreUrl(store.store.slug) : ''))
const storageKey = computed(() => `davent:ai-design:${storeId.value || 'sin-tienda'}`)
const progressStep = computed(() => (phase.value === 'ask' ? step.value + 1 : STEPS.length))
const selectedProposal = computed(() => proposals.value.find((p) => p.id === selectedId.value) || null)
const adjustDirty = computed(() => JSON.stringify(constraints.value) !== JSON.stringify(initialConstraints.value))

const autofillDefault = computed(() => {
  const c = store.customization || {}
  const empty = (v) => !v || (Array.isArray(v) && !v.length) || (typeof v === 'string' && !v.trim())
  return empty(c.about_text) && empty(c.about_mission) && empty(c.faqs) && empty(c.services) && empty(c.announcements)
})

const liveMessage = computed(() => {
  if (phase.value === 'loading') return 'Armando tu propuesta…'
  if (phase.value === 'error') return 'No pudimos armar la propuesta.'
  if (phase.value === 'results') return 'Tu propuesta está lista.'
  if (phase.value === 'adjust') return 'Ajustando la propuesta elegida.'
  if (phase.value === 'published') return 'Tu web ya está publicada.'
  return `Paso ${step.value + 1} de ${STEPS.length}: ${STEPS[step.value].title}.`
})

const currentStep = computed(() => STEPS[step.value])
const stepValid = computed(() => {
  const id = currentStep.value.id
  if (id === 'welcome') return true
  if (id === 'business') return Boolean(answers.name.trim() && answers.rubro)
  if (id === 'content' || id === 'sections') return true
  if (id === 'style') return Boolean(resolvedTone())
  return true
})
const canSubmit = computed(() => Boolean(answers.rubro && resolvedTone()))
const stepPct = computed(() => Math.round(((step.value + (stepValid.value ? 1 : 0)) / STEPS.length) * 100))
const hasAnswers = computed(() => Boolean(
  answers.name || answers.rubro || answers.goals.length || answers.tone || answers.style_hint.length ||
  answers.audience || answers.sections.length || answers.content_hint || answers.description
))

// ---------- Pedido estructurado ----------
const rubroMeta = computed(() => RUBROS.find((r) => r.id === answers.rubro) || null)
const toneMeta = computed(() => TONES.find((t) => t.id === answers.tone) || null)
const audienceLabel = computed(() => AUDIENCES.find((a) => a.id === answers.audience)?.label || '')
const goalLabels = computed(() => answers.goals.map((id) => GOALS.find((g) => g.id === id)?.label).filter(Boolean))
const sectionLabels = computed(() => answers.sections.map((id) => SECTIONS.find((s) => s.id === id)?.label).filter(Boolean))

const prompt = computed(() => buildPrompt(answers))
const promptJson = computed(() => JSON.stringify(prompt.value, null, 2))

const BLOCK_ROWS = computed(() => [
  { id: 'rubro', label: 'Rubro', icon: 'tag', value: rubroMeta.value?.label || '' },
  { id: 'goals', label: 'Objetivo', icon: 'flag', value: goalLabels.value.join(', ') },
  { id: 'tone', label: 'Tono', icon: 'palette', value: toneMeta.value?.label || (resolvedTone() ? TONES.find((t) => t.id === resolvedTone())?.label : '') },
  { id: 'audience', label: 'Audiencia', icon: 'users', value: audienceLabel.value },
  { id: 'sections', label: 'Secciones', icon: 'checklist', value: sectionLabels.value.join(', ') },
  { id: 'notes', label: 'Descripción', icon: 'file-text', value: String(answers.description || answers.content_hint || '').trim() }
])
const blocks = computed(() => BLOCK_ROWS.value.filter((row) => row.value))

// ---------- Selección de cada paso ----------
function pickRubro(id) {
  answers.rubro = answers.rubro === id ? '' : id
}
function toggleGoal(id) {
  const i = answers.goals.indexOf(id)
  if (i >= 0) answers.goals.splice(i, 1)
  else answers.goals.push(id)
}
function pickTone(id) {
  answers.tone = answers.tone === id ? '' : id
}
function pickAudience(id) {
  answers.audience = answers.audience === id ? '' : id
}
function toggleHint(id) {
  const i = answers.style_hint.indexOf(id)
  if (i >= 0) { answers.style_hint.splice(i, 1); return }
  if (answers.style_hint.length >= 2) answers.style_hint.shift()
  answers.style_hint.push(id)
}
function toggleSection(id) {
  const i = answers.sections.indexOf(id)
  if (i >= 0) answers.sections.splice(i, 1)
  else answers.sections.push(id)
}

const resolvedTone = () => toneOf(answers)

// ---------- Guardado real de los datos del negocio ----------
// Los pasos 2-4 escriben en customization/perfil al avanzar. Un fallo no
// frena el asistente: se avisa y se sigue (los datos quedan editables en el
// dashboard igual).
async function saveBusiness() {
  const payload = {}
  const name = answers.name.trim().slice(0, 60)
  if (name && name !== (store.customization.display_name || '')) payload.display_name = name
  const wsp = answers.whatsapp.trim().slice(0, 20)
  if (wsp !== (store.customization.whatsapp || '')) payload.whatsapp = wsp
  const hLabel = answers.hours_label.trim().slice(0, 60)
  const hValue = answers.hours_value.trim().slice(0, 60)
  if (hLabel && hValue) {
    payload.hours = [{ label: hLabel, value: hValue }]
    payload.show_hours = true
  }
  if (Object.keys(payload).length) await store.saveCustomization(payload)
  const profile = {}
  if (name) profile.business_name = name
  if (answers.province) profile.province = answers.province
  if (answers.city) profile.city = answers.city
  if (Object.keys(profile).length) await authApi.updateProfile(profile).catch(() => {})
}

async function saveContent() {
  const text = answers.description.trim().slice(0, 800)
  if (text && text !== description.value) await store.saveCustomization({ description: text })
}

async function saveSections() {
  const payload = {}
  SECTIONS.forEach((s) => {
    const on = answers.sections.includes(s.id)
    if (s.flag) payload[s.flag] = on
    if (s.also && on) payload[s.also] = true
  })
  const current = Array.isArray(store.customization.site_templates) ? [...store.customization.site_templates] : ['landing']
  if (!current.includes('landing')) current.unshift('landing')
  SECTIONS.forEach((s) => {
    if (!s.site) return
    const on = answers.sections.includes(s.id)
    const at = current.indexOf(s.site)
    if (on && at < 0) current.push(s.site)
    if (!on && at >= 0) current.splice(at, 1)
  })
  payload.site_templates = current
  await store.saveCustomization(payload)
}

// ---------- Uploads inline (logo + portada, con compresión) ----------
async function compressImage(file, maxW = 1600) {
  if (file.size <= 512 * 1024) return file
  try {
    const bmp = await createImageBitmap(file)
    const scale = Math.min(1, maxW / bmp.width)
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bmp.width * scale))
    canvas.height = Math.max(1, Math.round(bmp.height * scale))
    canvas.getContext('2d').drawImage(bmp, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', 0.85))
    return blob ? new File([blob], file.name.replace(/\.\w+$/, '') + '.webp', { type: 'image/webp' }) : file
  } catch { return file }
}

async function onLogoPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  mediaErr.value = ''
  logoBusy.value = true
  const prepared = await compressImage(file, 800)
  mediaErr.value = validateLogoFile(prepared)
  if (!mediaErr.value) {
    const ok = await store.uploadLogo(prepared)
    if (!ok) mediaErr.value = store.fieldErrors.logo || store.lastError
  }
  logoBusy.value = false
}

async function onCoverPicked(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file || !hasDesignAdvanced.value) return
  mediaErr.value = ''
  coverBusy.value = true
  const prepared = await compressImage(file, 1920)
  mediaErr.value = validateImageFile(prepared)
  if (!mediaErr.value) {
    const ok = await store.uploadCover(prepared)
    if (!ok) mediaErr.value = store.fieldErrors.cover || store.fieldErrors.detail || store.lastError
  }
  coverBusy.value = false
}

function suggestDescription() {
  const city = cities.value.find((c) => c.id === answers.city)?.name || ''
  answers.description = suggestDesc({ name: shopName.value, rubro: answers.rubro, city })
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
    answers.sections = Array.isArray(saved.sections)
      ? saved.sections.filter((s) => SECTIONS.some((o) => o.id === s))
      : base.sections
    answers.content_hint = typeof saved.content_hint === 'string' ? saved.content_hint.slice(0, 160) : ''
    if (typeof saved.name === 'string') answers.name = saved.name.slice(0, 60)
    if (typeof saved.whatsapp === 'string') answers.whatsapp = saved.whatsapp.slice(0, 20)
    if (typeof saved.hours_label === 'string') answers.hours_label = saved.hours_label.slice(0, 60)
    if (typeof saved.hours_value === 'string') answers.hours_value = saved.hours_value.slice(0, 60)
    if (typeof saved.description === 'string') answers.description = saved.description.slice(0, 800)
    if (saved.province) answers.province = saved.province
    if (saved.city) answers.city = saved.city
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

// ---------- Prefill: lo que ya sabemos del negocio ----------
async function loadPrefill() {
  if (!canUse.value || prefill.value) return
  try {
    const data = await storesApi.aiDesignPrefill()
    prefill.value = data
    if (!answers.rubro && RUBROS.some((r) => r.id === data?.rubro)) answers.rubro = data.rubro
    if (!answers.goals.length && Array.isArray(data?.goals)) {
      answers.goals = data.goals.filter((goal) => GOALS.some((o) => o.id === goal)).slice(0, 2)
    }
    if (Array.isArray(data?.checks)) checks.value = data.checks
  } catch { /* sin prefill el asistente funciona igual */ }
  // Lo que la tienda ya tiene cargado precarga el paso "Tu negocio".
  const c = store.customization || {}
  if (!answers.name && c.display_name) answers.name = c.display_name
  if (!answers.whatsapp && c.whatsapp) answers.whatsapp = c.whatsapp
  if (!answers.description && c.description) answers.description = String(c.description).slice(0, 800)
  if (!answers.hours_label && Array.isArray(c.hours) && c.hours[0]) {
    answers.hours_label = c.hours[0].label || ''
    answers.hours_value = c.hours[0].value || ''
  }
}
onMounted(loadPrefill)
watch(canUse, (value) => { if (value) loadPrefill() })

// Ubicación: provincias del catálogo; las ciudades se cargan al elegir.
async function loadProvinces() {
  if (provinces.value.length) return
  provinces.value = await locationsApi.getProvinces()
}
watch(() => answers.province, async (id) => {
  answers.city = ''
  cities.value = []
  if (!id) return
  citiesLoading.value = true
  cities.value = await locationsApi.getCities(id)
  citiesLoading.value = false
})
watch(() => currentStep.value?.id, (id) => { if (id === 'business') loadProvinces() }, { immediate: true })

// ---------- Telemetría del funnel ----------
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
      : 'No pudimos armar la propuesta. Probá de nuevo en un momento.')
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

// ---------- Elegir / ajustar ----------
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
  mcp.value = null
  published.value = null
  selectedId.value = ''
  constraints.value = {}
  initialConstraints.value = {}
  actionError.value = ''
  errorMsg.value = ''
  saveError.value = ''
  previewProposal.value = null
  phase.value = 'ask'
  step.value = 0
  nextTick(() => stepTitle.value?.focus?.())
}

// El contrato v3 aplica y publica en un solo request.
async function apply({ proposal, autofill, extras }) {
  if (!seed.value || busy.value) return
  busy.value = `apply:${proposal.id}`
  actionError.value = ''
  try {
    await http.post('/stores/ai-design/apply/', {
      seed: seed.value,
      proposal_id: proposal.id,
      autofill: Boolean(autofill),
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
    storesApi.aiDesignPrefill().then((data) => {
      if (Array.isArray(data?.checks)) checks.value = data.checks
    }).catch(() => {})
  } catch (e) {
    actionError.value = e?.response?.data?.detail || 'No pudimos establecer el estilo. Probá de nuevo.'
  } finally {
    busy.value = ''
  }
}

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

// ---------- Navegación del asistente ----------
// Al salir de un paso con datos reales se guarda primero; si falla se avisa
// y se avanza igual (el dueño puede completarlo después desde el panel).
async function goStep(index) {
  if (index < 0 || index >= STEPS.length || savingStep.value) return
  if (index > step.value && !stepValid.value) return
  if (index > step.value) await persistStep(step.value)
  step.value = index
  nextTick(() => stepTitle.value?.focus?.())
}
async function nextStep() {
  if (!stepValid.value || savingStep.value) return
  if (step.value < STEPS.length - 1) return goStep(step.value + 1)
  await persistStep(step.value)
  submit()
}
function prevStep() {
  goStep(step.value - 1)
}
function skipStep() {
  if (!currentStep.value.optional || savingStep.value) return
  goStep(step.value + 1)
}
async function persistStep(index) {
  const id = STEPS[index]?.id
  saveError.value = ''
  savingStep.value = true
  try {
    if (id === 'business') await saveBusiness()
    else if (id === 'content') await saveContent()
    else if (id === 'sections') await saveSections()
    if (saveError.value === '' && store.lastError) saveError.value = store.lastError
  } catch { saveError.value = 'No pudimos guardar esos datos. Los podés cargar después desde el panel.' }
  savingStep.value = false
}
function onStepKey(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  const tag = event.target?.tagName
  if (tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || tag === 'SELECT') return
  event.preventDefault()
  nextStep()
}
</script>

<template>
  <div class="aid">
    <header class="aid-head">
      <div class="aid-head-text">
        <h1><AppIcon name="sparkles" :size="20" /> Diseño asistido</h1>
        <p>Te guiamos paso a paso para armar tu web completa: datos, fotos, secciones y diseño.</p>
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

      <!-- ASISTENTE PASO A PASO -->
      <div v-if="phase === 'ask'" class="aidw" @keydown="onStepKey">
        <div class="aidw-main">
          <ol class="aidw-bar" aria-label="Progreso del asistente">
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
          <div class="aidw-progress">
            <div class="aidw-progress-track" role="progressbar" :aria-valuenow="stepPct" aria-valuemin="0" aria-valuemax="100" :aria-label="`Avance: ${stepPct}%`">
              <span class="aidw-progress-fill" :style="{ width: `${stepPct}%` }"></span>
            </div>
            <span class="aidw-progress-txt">Paso {{ step + 1 }} de {{ STEPS.length }} · {{ stepPct }}%</span>
          </div>

          <section class="aidw-step" :aria-labelledby="`aidw-title-${currentStep.id}`">
            <header class="aidw-step-head">
              <span class="aidw-step-ico" aria-hidden="true"><AppIcon :name="currentStep.icon" :size="20" /></span>
              <div class="aidw-step-text">
                <h2 :id="`aidw-title-${currentStep.id}`" ref="stepTitle" tabindex="-1">{{ currentStep.title }}</h2>
                <p>{{ currentStep.subtitle }}</p>
              </div>
            </header>
            <p v-if="currentStep.hint" class="aidw-step-hint">{{ currentStep.hint }}</p>
            <p v-if="saveError" class="aid-error" role="alert">{{ saveError }}</p>

            <!-- PASO 1 · BIENVENIDA -->
            <div v-if="currentStep.id === 'welcome'" class="aidw-welcome">
              <p class="aidw-welcome-text">
                Te hacemos <strong>5 preguntas simples</strong> sobre tu negocio y te armamos la web completa:
                tus datos, tus fotos, las secciones y el diseño.
              </p>
              <p class="aidw-welcome-text">No necesitás saber de diseño ni de computadoras: respondés, mirás el resultado y publicás.</p>
              <button type="button" class="btn btn-auto aidw-cta" @click="nextStep">
                <AppIcon name="sparkles" :size="18" /> Empezar ahora
              </button>
              <p class="aidw-note">Lleva unos 2 minutos. Todo se puede cambiar después.</p>
            </div>

            <!-- PASO 2 · DATOS DEL NEGOCIO (escribe customization + perfil) -->
            <template v-else-if="currentStep.id === 'business'">
              <label class="aidw-field">
                <span class="aidw-field-title">¿Cómo se llama tu negocio?</span>
                <input v-model="answers.name" class="aidw-input" type="text" maxlength="60" placeholder="Ej.: Ferretería El Tornillo" aria-label="Nombre del negocio" />
              </label>
              <p class="aidw-field-title">¿De qué es tu negocio?</p>
              <div class="aidw-grid rubros" role="radiogroup" aria-label="Rubro de tu negocio">
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
              <div class="aidw-2col">
                <label class="aidw-field">
                  <span class="aidw-field-title">¿En qué provincia estás? <span class="aidw-opt">Opcional</span></span>
                  <select v-model="answers.province" class="aidw-input" aria-label="Provincia">
                    <option value="">Elegí una provincia</option>
                    <option v-for="p in provinces" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                </label>
                <label class="aidw-field">
                  <span class="aidw-field-title">¿En qué ciudad o zona? <span class="aidw-opt">Opcional</span></span>
                  <select v-model="answers.city" class="aidw-input" :disabled="!answers.province || citiesLoading" aria-label="Ciudad o zona">
                    <option value="">{{ citiesLoading ? 'Cargando…' : 'Elegí una ciudad' }}</option>
                    <option v-for="c in cities" :key="c.id" :value="c.id">{{ c.name }}</option>
                  </select>
                </label>
              </div>
              <label class="aidw-field">
                <span class="aidw-field-title">Tu WhatsApp <span class="aidw-opt">Opcional</span></span>
                <input v-model="answers.whatsapp" class="aidw-input" type="tel" maxlength="20" placeholder="Ej.: 221 555 1234" aria-label="Número de WhatsApp" />
                <small class="aidw-note">Con código de área. Es el botón verde que van a tocar tus clientes.</small>
              </label>
              <div class="aidw-2col">
                <label class="aidw-field">
                  <span class="aidw-field-title">¿Qué días abrís? <span class="aidw-opt">Opcional</span></span>
                  <input v-model="answers.hours_label" class="aidw-input" type="text" maxlength="60" placeholder="Ej.: Lunes a viernes" aria-label="Días de atención" />
                </label>
                <label class="aidw-field">
                  <span class="aidw-field-title">¿En qué horario? <span class="aidw-opt">Opcional</span></span>
                  <input v-model="answers.hours_value" class="aidw-input" type="text" maxlength="60" placeholder="Ej.: 9 a 18 h" aria-label="Horario de atención" />
                </label>
              </div>
            </template>

            <!-- PASO 3 · CONTENIDO -->
            <template v-else-if="currentStep.id === 'content'">
              <label class="aidw-field">
                <span class="aidw-field-title">Contanos qué vendés en una frase</span>
                <textarea
                  v-model="answers.description"
                  class="aidw-input"
                  rows="3"
                  maxlength="800"
                  aria-label="Descripción corta del negocio"
                  placeholder="Ej.: vendemos herramientas y pintura para el que arregla su casa."
                ></textarea>
              </label>
              <button type="button" class="aidw-json-btn" @click="suggestDescription">
                <AppIcon name="sparkles" :size="14" /> Escribime una sugerencia
              </button>
              <label class="aidw-field">
                <span class="aidw-field-title">¿Qué es lo que más vendés? <span class="aidw-opt">Opcional</span></span>
                <input v-model="answers.content_hint" class="aidw-input" type="text" maxlength="160" placeholder="Ej.: arreglos de grifería y materiales eléctricos" aria-label="Productos o servicios destacados" />
              </label>
              <div class="aidw-2col">
                <div class="aidw-field">
                  <span class="aidw-field-title">Tu logo <span class="aidw-opt">Opcional</span></span>
                  <div class="aidw-media">
                    <img v-if="logo" :src="logo" alt="Tu logo" class="aidw-media-img" />
                    <span v-else class="aidw-media-empty"><AppIcon name="image" :size="18" /></span>
                    <div class="aidw-media-btns">
                      <button type="button" class="btn ghost btn-auto" :disabled="logoBusy" @click="logoInput?.click()">
                        <AppIcon name="upload" :size="15" /> {{ logoBusy ? 'Subiendo…' : (logo ? 'Cambiar logo' : 'Subir logo') }}
                      </button>
                      <input ref="logoInput" type="file" :accept="LOGO_ACCEPT" hidden @change="onLogoPicked" />
                    </div>
                  </div>
                </div>
                <div class="aidw-field">
                  <span class="aidw-field-title">Foto de portada <span class="aidw-opt">Opcional{{ hasDesignAdvanced ? '' : ' · Plan Premium' }}</span></span>
                  <div class="aidw-media" :class="{ off: !hasDesignAdvanced }">
                    <img v-if="cover" :src="cover" alt="Tu foto de portada" class="aidw-media-img wide" />
                    <span v-else class="aidw-media-empty"><AppIcon name="image" :size="18" /></span>
                    <div class="aidw-media-btns">
                      <button v-if="hasDesignAdvanced" type="button" class="btn ghost btn-auto" :disabled="coverBusy" @click="coverInput?.click()">
                        <AppIcon name="upload" :size="15" /> {{ coverBusy ? 'Subiendo…' : (cover ? 'Cambiar foto' : 'Subir foto') }}
                      </button>
                      <span v-else class="aidw-note"><AppIcon name="lock" :size="13" /> Viene con el Plan Premium</span>
                      <input ref="coverInput" type="file" :accept="LOGO_ACCEPT" hidden @change="onCoverPicked" />
                    </div>
                  </div>
                </div>
              </div>
              <p v-if="mediaErr" class="aid-error" role="alert">{{ mediaErr }}</p>
              <p class="aidw-note">Las fotos se achican solas antes de subir: cualquier imagen del celular sirve.</p>
            </template>

            <!-- PASO 4 · QUÉ MOSTRAR -->
            <template v-else-if="currentStep.id === 'sections'">
              <p class="aidw-field-title">Marcá lo que tiene que aparecer en tu web</p>
              <div class="aidw-grid must" role="group" aria-label="Secciones de la web">
                <button
                  v-for="s in SECTIONS"
                  :key="s.id"
                  type="button"
                  class="aidw-card"
                  :class="{ on: answers.sections.includes(s.id) }"
                  :aria-pressed="answers.sections.includes(s.id)"
                  :disabled="s.needs && !benefits[s.needs]"
                  @click="toggleSection(s.id)"
                >
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="s.icon" :size="18" /></span>
                  <span class="aidw-card-txt">
                    <strong>{{ s.label }} <AppIcon v-if="s.needs && !benefits[s.needs]" name="lock" :size="12" /></strong>
                    <small>{{ s.desc }}</small>
                    <span class="aidw-mock" aria-hidden="true"><i></i><i></i><i></i></span>
                  </span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.sections.includes(s.id)" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
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
            </template>

            <!-- PASO 5 · ESTILO (tono/audiencia, nunca colores ni fuentes) -->
            <template v-else>
              <p class="aidw-field-title">¿Cómo se tiene que sentir tu web?</p>
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

            <div class="aidw-nav">
              <button v-if="step > 0" type="button" class="btn ghost btn-auto" :disabled="savingStep" @click="prevStep">
                <AppIcon name="chevron-left" :size="16" /> Atrás
              </button>
              <button v-if="currentStep.optional && step < STEPS.length - 1" type="button" class="btn ghost btn-auto" :disabled="savingStep" @click="skipStep">
                Saltar este paso
              </button>
              <button
                v-if="step < STEPS.length - 1"
                type="button"
                class="btn btn-auto aidw-next"
                :disabled="!stepValid || savingStep"
                @click="nextStep"
              >
                {{ savingStep ? 'Guardando…' : 'Siguiente' }} <AppIcon name="chevron-right" :size="16" />
              </button>
              <button
                v-else
                type="button"
                class="btn btn-auto aidw-next"
                :disabled="!canSubmit || savingStep"
                @click="nextStep"
              >
                <AppIcon name="sparkles" :size="16" /> {{ savingStep ? 'Guardando…' : 'Generar mi web' }}
              </button>
              <span class="aidw-nav-note">{{ step + 1 }} de {{ STEPS.length }}</span>
            </div>
          </section>
        </div>

        <!-- PEDIDO ESTRUCTURADO -->
        <aside class="aidw-ask" :class="{ 'is-open': askOpen }" aria-label="Tu pedido">
          <header class="aidw-ask-head">
            <h3><AppIcon name="clipboard-list" :size="16" /> Tu pedido</h3>
            <span class="aidw-ask-count">{{ blocks.length }}</span>
            <button
              type="button" class="aidw-ask-toggle"
              :aria-expanded="askOpen" aria-controls="aidw-ask-body"
              @click="askOpen = !askOpen"
            >
              {{ askOpen ? 'Ocultar' : 'Ver' }}
              <AppIcon :name="askOpen ? 'chevron-up' : 'chevron-down'" :size="14" />
            </button>
          </header>
          <div id="aidw-ask-body" class="aidw-ask-body">
          <p v-if="!blocks.length" class="aidw-ask-empty">
            Cada respuesta arma una clave del pedido. El diseño se elige por mapeo directo: rubro + tono → patrón del catálogo.
          </p>
          <ul v-else class="aidw-bubbles">
            <li v-for="b in blocks" :key="b.id" class="aidw-bubble">
              <span class="aidw-bubble-ico" aria-hidden="true"><AppIcon :name="b.icon" :size="14" /></span>
              <div class="aidw-bubble-body">
                <span class="aidw-bubble-label">{{ b.label }}</span>
                <span class="aidw-bubble-text">{{ b.value }}</span>
              </div>
            </li>
          </ul>
          <button v-if="blocks.length" type="button" class="aidw-json-btn" :aria-expanded="showJson" @click="showJson = !showJson">
            <AppIcon :name="showJson ? 'chevron-up' : 'chevron-down'" :size="14" />
            {{ showJson ? 'Ocultar' : 'Ver' }} la estructura de datos
          </button>
          <pre v-if="showJson && blocks.length" class="aidw-json" aria-label="Pedido en formato de datos">{{ promptJson }}</pre>
          <button type="button" class="btn btn-auto aidw-send" :disabled="!canSubmit || savingStep" @click="nextStep">
            <AppIcon name="send" :size="16" /> Generar mi web
          </button>
          <p class="aidw-ask-note">El diseño sale de tus respuestas: mismo rubro + tono = mismo diseño, siempre.</p>
          </div>
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

      <!-- RESULTADO: propuesta + vista previa real en iframe -->
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

        <div v-if="mcp?.pattern" class="aid-mcp">
          <div class="aid-mcp-head">
            <AppIcon name="gem" :size="16" aria-hidden="true" />
            <strong>Elegimos el diseño «{{ mcp.pattern.nombre }}»{{ mcp.style ? ` con el estilo «${mcp.style.nombre}»` : '' }}</strong>
          </div>
          <ul class="aid-mcp-list">
            <li><strong>{{ mcp.pattern.nombre }}</strong><span class="aid-mcp-cat">{{ mcp.pattern.categoria }}</span><span class="aid-mcp-tags">catálogo de diseños</span></li>
          </ul>
        </div>
        <div v-else-if="mcp?.styles?.length" class="aid-mcp">
          <div class="aid-mcp-head">
            <AppIcon name="gem" :size="16" aria-hidden="true" />
            <strong>El MCP eligió {{ mcp.styles.length === 1 ? 'este patrón' : `${mcp.styles.length} patrones` }} de sus fuentes</strong>
          </div>
          <ul class="aid-mcp-list">
            <li v-for="s in mcp.styles" :key="s.slug">
              <strong>{{ s.nombre }}</strong>
              <span class="aid-mcp-cat">{{ s.categoria }}</span>
              <span v-if="s.source_repo" class="aid-mcp-tags">{{ s.source_repo }}</span>
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
            :show-map="answers.sections.includes('map')"
            :name-font="proposalNameFont(p)"
            :busy="busy"
            :selected="selectedId === p.id"
            :public-url="publicUrl"
            @preview="openPreview(p)"
            @choose="choose(p.id)"
          />
        </div>

        <AiCompareTable :proposals="proposals" :selected-id="selectedId" @choose="choose" />

        <div v-if="publicUrl" class="aid-live-preview">
          <p class="aidw-field-title"><AppIcon name="eye" :size="14" /> Tu web ahora mismo</p>
          <iframe :src="publicUrl" title="Vista previa real de tu web" loading="lazy"></iframe>
          <p class="aidw-note">Cuando publiques, esta página se actualiza sola con el diseño nuevo.</p>
        </div>

        <div class="aid-actions">
          <button class="btn btn-auto" type="button" :disabled="busy || !proposals.length" @click="apply({ proposal: proposals[0], autofill: autofillDefault })">
            <AppIcon name="check" :size="16" /> Publicar así
          </button>
          <button class="btn btn-auto" type="button" @click="anotherStyle">
            <AppIcon name="refresh" :size="16" /> Ver otro estilo
          </button>
          <button class="btn ghost btn-auto" type="button" @click="backToQuestions">
            <AppIcon name="chevron-left" :size="16" /> Volver a las preguntas
          </button>
        </div>
      </div>

      <!-- AJUSTAR SIN EMPEZAR DE CERO -->
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
              :show-map="answers.sections.includes('map')"
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

      <!-- PUBLICADA -->
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
          <h2>No pudimos armar la propuesta</h2>
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
      :show-map="answers.sections.includes('map')"
      :name-font="previewNameFont"
      :night-mode="previewProposal.night_mode"
      :public-url="publicUrl"
      @close="closePreview"
    />
  </div>
</template>

