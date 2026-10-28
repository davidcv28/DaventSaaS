<script setup>
import { ref, reactive, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import DesignPreview from '../../components/design/DesignPreview.vue'
import { useStoreStore } from '../../stores/store.store.js'
import {
  storesApi, CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  resolveStoreTemplate, allowedTemplatesFor, STORE_TEMPLATES
} from '../../api/stores.api.js'
import '../../assets/ai-design.css'

const props = defineProps({
  plan: { type: Object, default: null }
})
const emit = defineEmits(['applied', 'navigate'])

const store = useStoreStore()

const RUBROS = ['Indumentaria', 'Comida y bebida', 'Belleza', 'Servicios', 'Tecnología', 'Hogar y deco', 'Salud', 'Otro']
const GOALS = [
  { id: 'vender', label: 'Vender online' },
  { id: 'encontrarme', label: 'Que me encuentren' },
  { id: 'mostrar', label: 'Mostrar mi trabajo' },
  { id: 'consultas', label: 'Recibir consultas' },
  { id: 'turnos', label: 'Tomar turnos' }
]
const TONES = [
  { id: 'calido', label: 'Cálido' },
  { id: 'serio', label: 'Serio' },
  { id: 'moderno', label: 'Moderno' },
  { id: 'audaz', label: 'Audaz' }
]
const MUST_HAVE = [
  { id: 'whatsapp', label: 'Botón de WhatsApp' },
  { id: 'hours', label: 'Horarios' },
  { id: 'map', label: 'Mapa' },
  { id: 'prices', label: 'Precios' },
  { id: 'testimonials', label: 'Testimonios' },
  { id: 'faqs', label: 'Preguntas frecuentes' }
]
const MISSING_LABELS = {
  faqs: 'preguntas frecuentes',
  gallery: 'fotos de la galería',
  catalog: 'productos del catálogo',
  services: 'tus servicios',
  about: 'el texto de tu negocio',
  hours: 'horarios',
  location: 'tu dirección',
  testimonials: 'testimonios',
  logo: 'tu logo',
  cover: 'una foto de portada',
  contact: 'un email de contacto',
  social: 'tus redes'
}

const answers = reactive({ rubro: '', goals: [], tone: 'moderno', audience: '', must_have: [] })

const step = ref('ask') // ask | loading | results | error
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

let requestSeq = 0
let timer = null
onBeforeUnmount(() => clearTimeout(timer))

const benefits = computed(() => props.plan?.benefits || {})
const hasDesignAdvanced = computed(() => Boolean(benefits.value.has_design_advanced))
const canUse = computed(() => Boolean(props.plan?.isCurrent && benefits.value.has_customization && benefits.value.has_ai_design))
const allowed = computed(() => allowedTemplatesFor(benefits.value))
const shopName = computed(() => store.customization.display_name || store.store?.business_name || 'Tu negocio')
const initial = computed(() => (shopName.value || 'T').slice(0, 1).toUpperCase())
const logo = computed(() => store.customization.logo || '')
const cover = computed(() => store.customization.cover || '')
const missingLabel = computed(() => missing.value.map((k) => MISSING_LABELS[k] || k).join(', '))

const liveMessage = computed(() => {
  if (step.value === 'loading') return 'Armando tus propuestas…'
  if (step.value === 'error') return 'No pudimos armar las propuestas.'
  if (step.value === 'results') return `${proposals.value.length} propuestas listas.`
  return ''
})

// Preview: se parte del diseño guardado y se pisan solo las claves que trae
// la propuesta (site_theme cerrado + copy). Nunca se inventa contenido.
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

function toggle(list, id) {
  const i = list.indexOf(id)
  if (i >= 0) list.splice(i, 1)
  else list.push(id)
}
function toggleRubro(value) {
  answers.rubro = answers.rubro === value ? '' : value
}

function payload(extra = {}) {
  const p = {}
  if (answers.rubro) p.rubro = answers.rubro
  if (answers.goals.length) p.goals = [...answers.goals]
  if (answers.tone) p.tone = answers.tone
  if (answers.audience.trim()) p.audience = answers.audience.trim()
  if (answers.must_have.length) p.must_have = [...answers.must_have]
  return { ...p, ...extra }
}

async function generate(extra = {}) {
  if (step.value === 'loading') return
  const seq = ++requestSeq
  step.value = 'loading'
  errorMsg.value = ''
  actionError.value = ''
  result.value = null
  applied.value = null
  proposals.value = []
  previewProposal.value = null
  clearTimeout(timer)
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(Object.assign(new Error('timeout'), { aidTimeout: true })), 12000)
  })
  try {
    const data = await Promise.race([storesApi.aiDesign(payload(extra)), timeout])
    if (seq !== requestSeq) return
    if (!data || !Array.isArray(data.proposals) || !data.proposals.length) throw new Error('empty')
    seed.value = data.seed
    missing.value = Array.isArray(data.missing) ? data.missing : []
    proposals.value = data.proposals
    step.value = 'results'
    await nextTick()
    resultsRef.value?.querySelector('.aid-card')?.focus()
  } catch (e) {
    if (seq !== requestSeq) return
    // Un timeout invalida la request: si la respuesta llega tarde, se ignora.
    if (e?.aidTimeout) requestSeq++
    errorMsg.value = e?.response?.data?.detail || (e?.aidTimeout
      ? 'Tardó más de la cuenta. Probá de nuevo.'
      : 'No pudimos armar las propuestas. Probá de nuevo en un momento.')
    step.value = 'error'
  } finally {
    clearTimeout(timer)
  }
}

function decideForMe() {
  answers.rubro = ''
  answers.goals.splice(0)
  answers.tone = ''
  answers.audience = ''
  answers.must_have.splice(0)
  generate()
}

function another() {
  generate({ seed: (seed.value || 0) + 1 })
}

function startOver() {
  requestSeq++
  clearTimeout(timer)
  answers.rubro = ''
  answers.goals.splice(0)
  answers.tone = 'moderno'
  answers.audience = ''
  answers.must_have.splice(0)
  proposals.value = []
  missing.value = []
  applied.value = null
  result.value = null
  actionError.value = ''
  errorMsg.value = ''
  previewProposal.value = null
  step.value = 'ask'
}

async function apply(p) {
  if (!seed.value || busy.value) return
  busy.value = `apply:${p.id}`
  actionError.value = ''
  try {
    await storesApi.aiDesignApply({ seed: seed.value, proposal_id: p.id })
    await store.refreshCustomization()
    applied.value = { id: p.id, label: p.label }
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
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="aid">
    <div class="page-head">
      <div>
        <h1>Diseñar con IA</h1>
        <p>Contanos qué querés y te armamos 2 o 3 propuestas de web. Después elegís una y la ajustás a mano.</p>
      </div>
      <button v-if="step === 'results' || step === 'error'" class="btn ghost btn-auto" type="button" @click="startOver">
        <AppIcon name="refresh" :size="16" /> Empezar de nuevo
      </button>
    </div>

    <div v-if="!canUse" class="empty">
      <span class="empty-icon"><AppIcon name="lock" :size="28" /></span>
      <h3>Diseñar con IA viene con tu plan</h3>
      <p>Sumá el beneficio desde Mi plan y volvé a entrar.</p>
      <button class="btn btn-auto" type="button" @click="emit('navigate', 'plans')">Ver planes</button>
    </div>

    <template v-else>
      <p class="aid-live" aria-live="polite">{{ liveMessage }}</p>

      <!-- PASO 1 y 2: qué querés -->
      <div v-if="step === 'ask'" class="aid-ask">
        <section class="card aid-block" aria-labelledby="aid-q1">
          <h2 id="aid-q1"><span class="aid-step">1</span> Contame qué querés</h2>
          <p class="aid-hint">Todo es opcional: si no querés completar nada, usá “Prefiero que decidas vos”.</p>

          <div class="aid-field">
            <span class="aid-label">¿A qué te dedicás?</span>
            <div class="aid-chips" role="group" aria-label="Rubro">
              <button
                v-for="r in RUBROS"
                :key="r"
                type="button"
                class="aid-chip"
                :class="{ on: answers.rubro === r }"
                :aria-pressed="answers.rubro === r"
                @click="toggleRubro(r)"
              >{{ r }}</button>
            </div>
          </div>

          <div class="aid-field">
            <span class="aid-label">¿Qué querés lograr?</span>
            <div class="aid-chips" role="group" aria-label="Objetivos">
              <button
                v-for="g in GOALS"
                :key="g.id"
                type="button"
                class="aid-chip"
                :class="{ on: answers.goals.includes(g.id) }"
                :aria-pressed="answers.goals.includes(g.id)"
                @click="toggle(answers.goals, g.id)"
              >{{ g.label }}</button>
            </div>
          </div>

          <div class="aid-field">
            <span class="aid-label">¿Qué tono te gusta?</span>
            <div class="aid-chips" role="group" aria-label="Tono">
              <button
                v-for="t in TONES"
                :key="t.id"
                type="button"
                class="aid-chip"
                :class="{ on: answers.tone === t.id }"
                :aria-pressed="answers.tone === t.id"
                @click="answers.tone = t.id"
              >{{ t.label }}</button>
            </div>
          </div>

          <div class="aid-field">
            <label class="aid-label" for="aid-audience">¿A quién le vendés? (opcional)</label>
            <input
              id="aid-audience"
              v-model="answers.audience"
              class="aid-input"
              maxlength="120"
              placeholder="Ej. familias de Salta, comercios del centro…"
            />
          </div>
        </section>

        <section class="card aid-block" aria-labelledby="aid-q2">
          <h2 id="aid-q2"><span class="aid-step">2</span> ¿Qué no puede faltar?</h2>
          <p class="aid-hint">Marcá lo que sí o sí tiene que estar en tu web.</p>
          <div class="aid-checks">
            <label v-for="m in MUST_HAVE" :key="m.id" class="aid-check">
              <input
                type="checkbox"
                :checked="answers.must_have.includes(m.id)"
                @change="toggle(answers.must_have, m.id)"
              />
              <span>{{ m.label }}</span>
            </label>
          </div>
        </section>

        <div class="aid-actions">
          <button class="btn btn-auto" type="button" @click="generate()">
            <AppIcon name="sparkles" :size="17" /> Armar mis propuestas
          </button>
          <button class="btn ghost btn-auto" type="button" @click="decideForMe">Prefiero que decidas vos</button>
        </div>
      </div>

      <!-- PASO 3: generación -->
      <div v-else-if="step === 'loading'" class="aid-loading" aria-hidden="true">
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

      <!-- PASO 4: propuestas -->
      <div v-else-if="step === 'results'" ref="resultsRef" class="aid-results">
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
          <AppIcon name="info" :size="18" />
          <p>Para un mejor resultado cargá: <strong>{{ missingLabel }}</strong>.</p>
          <button class="btn ghost btn-auto" type="button" @click="emit('navigate', 'company')">Completar mis datos</button>
        </div>

        <div class="aid-grid">
          <article v-for="(p, i) in proposals" :key="p.id" class="card aid-card" :tabindex="i === 0 ? -1 : undefined">
            <header class="aid-card-head">
              <div>
                <h2>{{ p.label }}</h2>
                <p>{{ p.why }}</p>
              </div>
              <span class="aid-badge">{{ templateLabel(p.template) }}</span>
            </header>

            <div class="aid-mini">
              <DesignPreview
                :form="proposalForm(p)"
                :vars="proposalVars(p)"
                :template="proposalTemplate(p)"
                :shop-name="shopName"
                :initial="initial"
                :logo="logo"
                :cover="cover"
                :advanced="hasDesignAdvanced"
                :catalog-on="true"
                :show-map="answers.must_have.includes('map')"
                :name-font="proposalNameFont(p)"
              />
            </div>

            <ul v-if="p.notes?.length" class="aid-notes">
              <li v-for="(n, k) in p.notes.slice(0, 3)" :key="k">{{ n }}</li>
            </ul>

            <footer class="aid-card-actions">
              <button class="btn ghost btn-auto" type="button" @click="openPreview(p)">
                <AppIcon name="eye" :size="16" /> Ver en grande
              </button>
              <button class="btn btn-auto" type="button" :disabled="Boolean(busy)" @click="apply(p)">
                <AppIcon name="check" :size="16" /> {{ busy === `apply:${p.id}` ? 'Aplicando…' : 'Aplicar al borrador' }}
              </button>
            </footer>
            <p v-if="applied?.id === p.id" class="aid-applied"><AppIcon name="check" :size="14" /> En el borrador</p>
          </article>
        </div>

        <div class="aid-actions">
          <button class="btn ghost btn-auto" type="button" @click="another">
            <AppIcon name="refresh" :size="16" /> Otra propuesta
          </button>
        </div>
      </div>

      <!-- Error con reintento -->
      <div v-else class="card aid-error-box" role="alert">
        <AppIcon name="circle-alert" :size="24" />
        <div>
          <h2>No pudimos armar las propuestas</h2>
          <p>{{ errorMsg }}</p>
          <div class="aid-actions">
            <button class="btn btn-auto" type="button" @click="generate()">Reintentar</button>
            <button class="btn ghost btn-auto" type="button" @click="startOver">Cambiar mis respuestas</button>
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
          <button class="btn btn-auto" type="button" :disabled="Boolean(busy)" @click="apply(previewProposal); closePreview()">
            Aplicar al borrador
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>
