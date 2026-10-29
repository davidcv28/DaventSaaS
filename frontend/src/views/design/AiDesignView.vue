<script setup>
import { ref, reactive, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import AiSelect from '../../components/ai/AiSelect.vue'
import AiStep from '../../components/ai/AiStep.vue'
import AiProposalCard from '../../components/ai/AiProposalCard.vue'
import AiColorField from '../../components/ai/AiColorField.vue'
import AiNightModeField from '../../components/ai/AiNightModeField.vue'
import AiCoverField from '../../components/ai/AiCoverField.vue'
import AiDevicePreview from '../../components/ai/AiDevicePreview.vue'
import { useStoreStore } from '../../stores/store.store.js'
import {
  storesApi, CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  resolveStoreTemplate, allowedTemplatesFor, publicStoreUrl
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

const STEP_TITLES = ['A qué te dedicás', 'Qué querés lograr', 'Cómo se siente', 'Tu marca', 'Qué no puede faltar', 'Tus propuestas']

const EMPTY = () => ({
  rubro: '', goals: [], tone: '', style_hint: [], audience: '', must_have: [],
  brand_color: '', night_mode: { enabled: false, default: 'light' }, cover_choice: 'auto', use_icons: true
})
const answers = reactive(EMPTY())

const stepIndex = ref(1)
const phase = ref('ask') // ask | loading | results | error
const proposals = ref([])
const seed = ref(null)
const missing = ref([])
const errorMsg = ref('')
const actionError = ref('')
const published = ref(null) // { id, label }
const publishedSnapshot = ref(null) // propuesta publicada, para no perderla al ver otro estilo
const browsing = ref(false) // el usuario pidió "Cambiar el estilo"
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
const shopName = computed(() => store.customization.display_name || store.store?.business_name || 'Tu negocio')
const initial = computed(() => (shopName.value || 'T').slice(0, 1).toUpperCase())
const logo = computed(() => store.customization.logo || '')
const cover = computed(() => store.customization.cover || '')
const storeId = computed(() => store.store?.id || '')
const publicUrl = computed(() => (store.store?.slug ? publicStoreUrl(store.store.slug) : ''))
const storageKey = computed(() => `davent:ai-design:${storeId.value || 'sin-tienda'}`)
const progressStep = computed(() => (phase.value === 'results' ? 6 : stepIndex.value))
const showPublished = computed(() => Boolean(published.value) && !browsing.value)
const visibleProposals = computed(() => {
  if (showPublished.value) return proposals.value.filter((p) => p.id === published.value.id)
  // "Ver otro estilo": la publicada no desaparece, encabeza la lista nueva.
  if (browsing.value && publishedSnapshot.value && !proposals.value.some((p) => p.id === published.value?.id)) {
    return [publishedSnapshot.value, ...proposals.value]
  }
  return proposals.value
})
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
  if (showPublished.value || proposals.value.length < 2 || distinctFamilies.value < 2) return ''
  return `${proposals.value.length} estilos distintos para tu rubro`
})

const autofillDefault = computed(() => {
  const c = store.customization || {}
  const empty = (v) => !v || (Array.isArray(v) && !v.length) || (typeof v === 'string' && !v.trim())
  return empty(c.about_text) && empty(c.about_mission) && empty(c.faqs) && empty(c.services) && empty(c.announcements)
})

const liveMessage = computed(() => {
  if (phase.value === 'loading') return 'Armando tus propuestas…'
  if (phase.value === 'error') return 'No pudimos armar las propuestas.'
  if (phase.value === 'results') {
    return showPublished.value ? 'Tu web ya está publicada.' : `${proposals.value.length} propuestas listas.`
  }
  return `Paso ${stepIndex.value} de 6: ${STEP_TITLES[stepIndex.value - 1]}`
})

const hasAnswers = computed(() => Boolean(
  answers.rubro || answers.goals.length || answers.tone || answers.style_hint.length || answers.audience ||
  answers.must_have.length || answers.brand_color || answers.night_mode.enabled ||
  answers.cover_choice !== 'auto' || !answers.use_icons
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
    answers.brand_color = /^#[0-9a-f]{6}$/i.test(saved.brand_color || '') ? saved.brand_color.toLowerCase() : ''
    const nm = saved.night_mode
    answers.night_mode = (nm && typeof nm === 'object')
      ? { enabled: Boolean(nm.enabled), default: nm.default === 'dark' ? 'dark' : 'light' }
      : { enabled: false, default: 'light' }
    answers.cover_choice = ['foto', 'logo', 'auto'].includes(saved.cover_choice) ? saved.cover_choice : 'auto'
    answers.use_icons = saved.use_icons !== false
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
const previewTemplate = computed(() => (previewProposal.value ? proposalTemplate(previewProposal.value) : 'classic'))
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

function payload(extra = {}) {
  const p = {}
  if (answers.rubro) p.rubro = answers.rubro
  if (answers.goals.length) p.goals = [...answers.goals]
  const tone = resolvedTone()
  if (tone) p.tone = tone
  if (answers.audience) p.audience = answers.audience
  if (answers.must_have.length) p.must_have = [...answers.must_have]
  p.brand_color = answers.brand_color || ''
  p.night_mode = {
    enabled: Boolean(answers.night_mode.enabled),
    default: answers.night_mode.enabled && answers.night_mode.default === 'dark' ? 'dark' : 'light'
  }
  p.cover_choice = answers.cover_choice || 'auto'
  p.use_icons = answers.use_icons !== false
  return { ...p, ...extra }
}

async function generate(extra = {}, useAnswers = true, opts = {}) {
  if (phase.value === 'loading') return
  // "Ver otro estilo" no borra lo publicado: la tarjeta elegida sigue
  // arriba con su estado y solo se reemplaza si el usuario aplica otra.
  const keep = Boolean(opts.keepPublished && published.value && publishedSnapshot.value)
  const seq = ++requestSeq
  phase.value = 'loading'
  errorMsg.value = ''
  actionError.value = ''
  if (!keep) {
    published.value = null
    publishedSnapshot.value = null
  }
  browsing.value = keep
  if (!keep) {
    proposals.value = []
    previewProposal.value = null
  }
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
    proposals.value = data.proposals
    phase.value = 'results'
    await nextTick()
    resultsRef.value?.querySelector('.aidp')?.focus?.()
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

function next() {
  if (stepIndex.value < 5) stepIndex.value += 1
  else generate()
}
function back() {
  if (stepIndex.value > 1) stepIndex.value -= 1
}
function decideForMe() {
  generate({}, false)
}
function anotherStyle() {
  generate({ seed: (seed.value || 0) + 1 }, true, { keepPublished: true })
}
function redoWithPhotos() {
  generate({ seed: seed.value })
}
function backToQuestions() {
  phase.value = 'ask'
  stepIndex.value = 1
  browsing.value = false
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
  publishedSnapshot.value = null
  browsing.value = false
  actionError.value = ''
  errorMsg.value = ''
  previewProposal.value = null
  phase.value = 'ask'
  stepIndex.value = 1
}

// El contrato v3 aplica y publica en un solo request: ya no hay publish/discard
// desde esta sección (siguen existiendo para el Studio).
async function apply({ proposal, autofill }) {
  if (!seed.value || busy.value) return
  busy.value = `apply:${proposal.id}`
  actionError.value = ''
  try {
    await http.post('/stores/ai-design/apply/', {
      seed: seed.value,
      proposal_id: proposal.id,
      autofill: Boolean(autofill)
    })
    await store.refreshCustomization()
    published.value = { id: proposal.id, label: proposal.label }
    publishedSnapshot.value = proposal
    browsing.value = false
    emit('applied', { action: 'publish' })
  } catch (e) {
    actionError.value = e?.response?.data?.detail || 'No pudimos establecer el estilo. Probá de nuevo.'
  } finally {
    busy.value = ''
  }
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
        <p>Contanos cinco cosas de tu negocio y te armamos la web lista. Después la ajustás a tu gusto.</p>
        <span v-if="showPublished" class="aid-pub-chip"><AppIcon name="circle-check" :size="13" /> Publicada</span>
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
        <span v-for="n in 6" :key="n" class="aid-progress-dot" :class="{ on: progressStep >= n, now: progressStep === n }">
          <span class="sr-only">Paso {{ n }}: {{ STEP_TITLES[n - 1] }}</span>
        </span>
      </div>

      <!-- PREGUNTAS -->
      <div v-if="phase === 'ask'" class="aid-ask">
        <AiStep v-if="stepIndex === 1" :number="1" title="¿A qué te dedicás?" subtitle="Elegí lo que más se parezca. Con esto sabemos qué mostrar primero.">
          <AiSelect v-model="answers.rubro" :options="RUBROS" label="Rubro" placeholder="Elegí tu rubro" />
        </AiStep>

        <AiStep v-else-if="stepIndex === 2" :number="2" title="¿Qué querés lograr?" subtitle="Podés elegir más de uno. Lo usamos para ordenar las secciones.">
          <AiSelect v-model="answers.goals" :options="GOALS" multiple label="Objetivos" placeholder="Elegí uno o varios objetivos" />
        </AiStep>

        <AiStep v-else-if="stepIndex === 3" :number="3" title="¿Cómo querés que se sienta?" subtitle="El estilo de los colores y las letras.">
          <div class="aid-fields">
            <AiSelect v-model="answers.tone" :options="TONES" label="Estilo" placeholder="Elegí un estilo" />
            <AiSelect v-model="answers.audience" :options="AUDIENCES" label="A quién le hablás" placeholder="¿A quién le hablás?" />
            <div class="aid-field">
              <p class="aid-field-title">¿Qué te importa más? <span class="aid-optional">Opcional</span></p>
              <p class="aid-hints-note">Elegí hasta dos. Nos ayuda a que tu estilo no se parezca a otro.</p>
              <div class="aid-hints" role="group" aria-label="¿Qué te importa más?">
                <button
                  v-for="h in STYLE_HINTS"
                  :key="h.id"
                  type="button"
                  class="aid-hint-chip"
                  :class="{ on: answers.style_hint.includes(h.id) }"
                  :aria-pressed="answers.style_hint.includes(h.id)"
                  @click="toggleHint(h.id)"
                >
                  <AppIcon :name="h.icon" :size="15" aria-hidden="true" />
                  <span>{{ h.label }}</span>
                </button>
              </div>
            </div>
          </div>
        </AiStep>

        <AiStep v-else-if="stepIndex === 4" :number="4" title="Tu marca" subtitle="El color, el modo noche y la portada. Todo se puede cambiar después.">
          <div class="aid-fields">
            <div class="aid-field">
              <p class="aid-field-title">¿Querés elegir el color de tu marca?</p>
              <AiColorField v-model="answers.brand_color" />
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
          </div>
        </AiStep>

        <AiStep v-else :number="5" title="¿Qué no puede faltar?" subtitle="Marcá lo que sí o sí tiene que estar en tu web.">
          <AiSelect v-model="answers.must_have" :options="MUST_HAVE" multiple label="Lo que no puede faltar" placeholder="Elegí lo importante" />
        </AiStep>

        <div class="aid-actions">
          <button v-if="stepIndex > 1" class="btn ghost btn-auto" type="button" @click="back">
            <AppIcon name="chevron-left" :size="16" /> Atrás
          </button>
          <button class="btn btn-auto aid-primary" type="button" @click="next">
            <AppIcon :name="stepIndex === 5 ? 'sparkles' : 'chevron-right'" :size="16" />
            {{ stepIndex === 5 ? 'Armar mis propuestas' : 'Siguiente' }}
          </button>
          <button class="btn ghost btn-auto" type="button" @click="decideForMe">Prefiero que decidas vos</button>
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

      <!-- RESULTADOS -->
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
        <p v-if="browsing && published" class="aid-keep-note">
          <AppIcon name="circle-check" :size="14" aria-hidden="true" />
          Seguís con <strong>{{ published.label }}</strong> publicado hasta que elijas otro.
        </p>

        <div class="aid-grid">
          <AiProposalCard
            v-for="p in visibleProposals"
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
            :published="published?.id === p.id"
            :public-url="publicUrl"
            :autofill-default="autofillDefault"
            @preview="openPreview(p)"
            @apply="apply"
            @change-style="anotherStyle"
            @refresh-images="redoWithPhotos"
          />
        </div>

        <div v-if="!showPublished" class="aid-actions">
          <button class="btn btn-auto" type="button" @click="anotherStyle">
            <AppIcon name="refresh" :size="16" /> Ver otro estilo
          </button>
          <button class="btn ghost btn-auto" type="button" @click="backToQuestions">
            <AppIcon name="chevron-left" :size="16" /> Volver a las preguntas
          </button>
        </div>
      </div>

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
