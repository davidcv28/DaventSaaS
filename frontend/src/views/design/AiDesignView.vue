<script setup>
import { ref, reactive, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import AiSelect from '../../components/ai/AiSelect.vue'
import AiStep from '../../components/ai/AiStep.vue'
import AiProposalCard from '../../components/ai/AiProposalCard.vue'
import DesignPreview from '../../components/design/DesignPreview.vue'
import { useStoreStore } from '../../stores/store.store.js'
import {
  storesApi, CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  resolveStoreTemplate, allowedTemplatesFor, STORE_TEMPLATES
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
const MUST_HAVE = [
  { id: 'whatsapp', label: 'Botón de WhatsApp', icon: 'whatsapp', desc: 'Para que te escriban al toque' },
  { id: 'hours', label: 'Horarios', icon: 'clock', desc: 'Cuándo estás abierto' },
  { id: 'map', label: 'Mapa y dirección', icon: 'map-pin', desc: 'Cómo llegar a tu local' },
  { id: 'prices', label: 'Precios', icon: 'tag', desc: 'Cuánto sale cada cosa' },
  { id: 'testimonials', label: 'Opiniones de clientes', icon: 'quote', desc: 'Lo que dicen de vos' },
  { id: 'faqs', label: 'Preguntas frecuentes', icon: 'circle-help', desc: 'Las dudas que te preguntan siempre' }
]

const STEP_TITLES = ['A qué te dedicás', 'Qué querés lograr', 'Cómo se siente', 'Qué no puede faltar', 'Tus propuestas']

const EMPTY = () => ({ rubro: '', goals: [], tone: '', audience: '', must_have: [] })
const answers = reactive(EMPTY())

const stepIndex = ref(1)
const phase = ref('ask') // ask | loading | results | error
const proposals = ref([])
const seed = ref(null)
const missing = ref([])
const errorMsg = ref('')
const actionError = ref('')
const applied = ref(null) // { id, label }
const result = ref(null) // apply | publish | discard
const busy = ref('')
const note = ref('')
const noteOpen = ref(false)
const previewProposal = ref(null)
const resultsRef = ref(null)
const hydrated = ref(false)

let requestSeq = 0
let timer = null
onBeforeUnmount(() => {
  clearTimeout(timer)
  document.removeEventListener('keydown', onKey)
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
const storageKey = computed(() => `davent:ai-design:${storeId.value || 'sin-tienda'}`)
const progressStep = computed(() => (phase.value === 'results' ? 5 : stepIndex.value))

const autofillDefault = computed(() => {
  const c = store.customization || {}
  const empty = (v) => !v || (Array.isArray(v) && !v.length) || (typeof v === 'string' && !v.trim())
  return empty(c.about_text) && empty(c.about_mission) && empty(c.faqs) && empty(c.services) && empty(c.announcements)
})

const liveMessage = computed(() => {
  if (phase.value === 'loading') return 'Armando tus propuestas…'
  if (phase.value === 'error') return 'No pudimos armar las propuestas.'
  if (phase.value === 'results') return `${proposals.value.length} propuestas listas.`
  return `Paso ${stepIndex.value} de 5: ${STEP_TITLES[stepIndex.value - 1]}`
})

const hasAnswers = computed(() => Boolean(answers.rubro || answers.goals.length || answers.tone || answers.audience || answers.must_have.length))

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
    answers.audience = typeof saved.audience === 'string' ? saved.audience : base.audience
    answers.must_have = Array.isArray(saved.must_have) ? saved.must_have.filter((m) => MUST_HAVE.some((o) => o.id === m)) : []
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
function proposalForm(p) {
  return { ...CUSTOMIZATION_DEFAULTS, ...(store.customization || {}), ...(p.site_theme || {}), ...(p.copy || {}) }
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
function templateLabel(key) {
  return STORE_TEMPLATES[key]?.label || key
}

// ---------- Flujo ----------
function payload(extra = {}) {
  const p = {}
  if (answers.rubro) p.rubro = answers.rubro
  if (answers.goals.length) p.goals = [...answers.goals]
  if (answers.tone) p.tone = answers.tone
  if (answers.audience) p.audience = answers.audience
  if (answers.must_have.length) p.must_have = [...answers.must_have]
  return { ...p, ...extra }
}

async function generate(extra = {}, useAnswers = true) {
  if (phase.value === 'loading') return
  const seq = ++requestSeq
  phase.value = 'loading'
  errorMsg.value = ''
  actionError.value = ''
  result.value = null
  applied.value = null
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
  if (stepIndex.value < 4) stepIndex.value += 1
  else generate()
}
function back() {
  if (stepIndex.value > 1) stepIndex.value -= 1
}
function decideForMe() {
  generate({}, false)
}
function another() {
  generate({ seed: (seed.value || 0) + 1 })
}
function redoWithPhotos() {
  generate({ seed: seed.value })
}
function backToQuestions() {
  phase.value = 'ask'
  stepIndex.value = 1
  result.value = null
  applied.value = null
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
  applied.value = null
  result.value = null
  actionError.value = ''
  errorMsg.value = ''
  previewProposal.value = null
  phase.value = 'ask'
  stepIndex.value = 1
}

// TODO(A): mover a stores.api.js (aiDesignApply con autofill) cuando ese
// archivo lo tome su dueño. El contrato v2 suma `autofill` al apply.
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
    applied.value = { id: proposal.id, label: proposal.label }
    result.value = 'apply'
    note.value = ''
    noteOpen.value = false
    emit('applied', { action: 'apply' })
  } catch (e) {
    actionError.value = e?.response?.data?.detail || 'No pudimos aplicarlo. Probá de nuevo.'
  } finally {
    busy.value = ''
  }
}

async function publish() {
  if (busy.value) return
  busy.value = 'publish'
  actionError.value = ''
  const ok = await store.publishCustomization(note.value.trim())
  busy.value = ''
  if (!ok) {
    actionError.value = store.lastError || 'No pudimos publicar. Probá de nuevo.'
    return
  }
  result.value = 'publish'
  noteOpen.value = false
  note.value = ''
  emit('applied', { action: 'publish' })
}

async function discard() {
  if (busy.value) return
  busy.value = 'discard'
  actionError.value = ''
  const ok = await store.discardCustomization()
  busy.value = ''
  if (!ok) {
    actionError.value = store.lastError || 'No pudimos descartar. Probá de nuevo.'
    return
  }
  applied.value = null
  result.value = 'discard'
  emit('applied', { action: 'discard' })
}

function openPreview(p) {
  previewProposal.value = p
  nextTick(() => document.querySelector('.aid-modal-box')?.focus())
}
function closePreview() {
  previewProposal.value = null
}
function onKey(e) {
  if (e.key === 'Escape' && previewProposal.value) closePreview()
}
onMounted(() => document.addEventListener('keydown', onKey))
</script>

<template>
  <div class="aid">
    <header class="aid-head">
      <div class="aid-head-text">
        <span class="aid-badge-new">Nuevo</span>
        <h1><AppIcon name="sparkles" :size="20" /> Diseñar con IA</h1>
        <p>Contanos cuatro cosas de tu negocio y te armamos la web lista. Después la ajustás a tu gusto.</p>
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
        <span v-for="n in 5" :key="n" class="aid-progress-dot" :class="{ on: progressStep >= n, now: progressStep === n }">
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
          </div>
        </AiStep>

        <AiStep v-else :number="4" title="¿Qué no puede faltar?" subtitle="Marcá lo que sí o sí tiene que estar en tu web.">
          <AiSelect v-model="answers.must_have" :options="MUST_HAVE" multiple label="Lo que no puede faltar" placeholder="Elegí lo importante" />
        </AiStep>

        <div class="aid-actions">
          <button v-if="stepIndex > 1" class="btn ghost btn-auto" type="button" @click="back">
            <AppIcon name="chevron-left" :size="16" /> Atrás
          </button>
          <button class="btn btn-auto aid-primary" type="button" @click="next">
            <AppIcon :name="stepIndex === 4 ? 'sparkles' : 'chevron-right'" :size="16" />
            {{ stepIndex === 4 ? 'Armar mis propuestas' : 'Siguiente' }}
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
        <div v-if="result" class="cta-banner aid-banner" role="status">
          <div class="aid-banner-text">
            <strong>{{ result === 'publish' ? 'Tu web ya está publicada' : result === 'discard' ? 'Borrador descartado' : 'Aplicado al borrador' }}</strong>
            <span v-if="result === 'apply'">{{ applied?.label }} quedó en el borrador. Revisala y publicala cuando quieras.</span>
            <span v-else-if="result === 'publish'">Los cambios ya se ven en tu página.</span>
            <span v-else>Tu web volvió a como estaba publicada.</span>
          </div>
          <div class="aid-banner-actions">
            <template v-if="result === 'apply'">
              <button v-if="!noteOpen" class="btn light btn-auto" type="button" @click="noteOpen = true">Publicar</button>
              <template v-else>
                <input
                  v-model="note"
                  class="aid-input aid-note"
                  maxlength="120"
                  placeholder="Nota opcional de la versión"
                  aria-label="Nota de la versión"
                />
                <button class="btn light btn-auto" type="button" :disabled="busy === 'publish'" @click="publish">
                  {{ busy === 'publish' ? 'Publicando…' : 'Confirmar' }}
                </button>
              </template>
              <button class="btn light btn-auto" type="button" :disabled="busy === 'discard'" @click="discard">
                {{ busy === 'discard' ? 'Descartando…' : 'Descartar' }}
              </button>
            </template>
            <button class="btn light btn-auto" type="button" @click="emit('navigate', 'design')">Ajustar a mano</button>
          </div>
        </div>

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

        <div class="aid-grid">
          <AiProposalCard
            v-for="p in proposals"
            :key="p.id"
            :proposal="p"
            :form="proposalForm(p)"
            :vars="proposalVars(p)"
            :template="proposalTemplate(p)"
            :template-label="templateLabel(p.template)"
            :shop-name="shopName"
            :initial="initial"
            :logo="logo"
            :cover="cover"
            :advanced="hasDesignAdvanced"
            :show-map="answers.must_have.includes('map')"
            :name-font="proposalNameFont(p)"
            :busy="busy"
            :applied="applied?.id === p.id"
            :autofill-default="autofillDefault"
            @preview="openPreview(p)"
            @apply="apply"
            @refresh-images="redoWithPhotos"
          />
        </div>

        <div class="aid-actions">
          <button class="btn btn-auto" type="button" @click="another">
            <AppIcon name="refresh" :size="16" /> Otra propuesta
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
    <div
      v-if="previewProposal"
      class="aid-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="aid-modal-title"
      @click.self="closePreview"
    >
      <div class="aid-modal-box" tabindex="-1">
        <header class="aid-modal-head">
          <div>
            <h2 id="aid-modal-title">{{ previewProposal.label }}</h2>
            <p>{{ previewProposal.why }}</p>
          </div>
          <button class="icon-btn" type="button" aria-label="Cerrar vista previa" @click="closePreview">
            <AppIcon name="x" :size="18" />
          </button>
        </header>
        <div class="aid-modal-body">
          <DesignPreview
            :form="previewForm"
            :vars="previewVars"
            :template="previewTemplate"
            :shop-name="shopName"
            :initial="initial"
            :logo="logo"
            :cover="cover"
            :advanced="hasDesignAdvanced"
            :catalog-on="true"
            :show-map="answers.must_have.includes('map')"
            :name-font="previewNameFont"
          />
        </div>
        <footer class="aid-modal-foot">
          <button class="btn ghost btn-auto" type="button" @click="closePreview">Cerrar</button>
          <button
            class="btn btn-auto"
            type="button"
            :disabled="Boolean(busy)"
            @click="apply({ proposal: previewProposal, autofill: autofillDefault }); closePreview()"
          >
            Aplicar al borrador
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>
