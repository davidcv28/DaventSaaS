<script setup>
// Modal "Asistencia con IA": mismo asistente con dos contextos.
//  - origin 'design': preguntas de diseño -> POST /stores/ai-design/mcp/ ->
//    propuesta -> apply (mismos endpoints y gates que AiDesignView).
//  - origin 'business': preguntas de datos del negocio -> resumen que SOLO
//    rellena campos vacíos de customization/perfil (no pisa lo ya cargado).
import { ref, reactive, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'
import AiIdeaCard from '../ai/AiIdeaCard.vue'
import { useStoreStore } from '../../stores/store.store.js'
import { useAuthStore } from '../../stores/auth.store.js'
import { authApi } from '../../api/auth.api.js'
import { locationsApi } from '../../api/locations.api.js'
import { http } from '../../api/http.js'
import {
  storesApi, CUSTOMIZATION_DEFAULTS, storeThemeVars, storeFontFamily,
  resolveStoreTemplate, allowedTemplatesFor
} from '../../api/stores.api.js'
import {
  RUBROS, GOALS, TONES, AUDIENCES, STYLE_HINTS, SECTIONS,
  emptyAssistAnswers, resolvedTone, buildPrompt, suggestDescription, toggleId
} from '../../composables/useAiAssist.js'
import '../../assets/ai-design.css'

const props = defineProps({
  origin: { type: String, default: 'design' }, // 'design' | 'business'
  plan: { type: Object, default: null }
})
const emit = defineEmits(['close', 'applied', 'navigate'])

const store = useStoreStore()
const auth = useAuthStore()

const isBusiness = computed(() => props.origin === 'business')
const benefits = computed(() => props.plan?.benefits || {})
const hasDesignAdvanced = computed(() => Boolean(benefits.value.has_design_advanced))
const allowed = computed(() => allowedTemplatesFor(benefits.value))

// ---------- Pasos por origen ----------
const DESIGN_STEPS = [
  { id: 'rubro', icon: 'store', title: 'Tu rubro', subtitle: 'De qué es tu negocio', hint: 'Con eso elegimos el diseño base.' },
  { id: 'sections', icon: 'checklist', title: 'Qué mostrar', subtitle: 'Secciones y objetivos de tu web', hint: 'Lo que marques aparece en la web.', optional: true },
  { id: 'style', icon: 'palette', title: 'Tu estilo', subtitle: 'Cómo querés que se sienta tu web', hint: 'Elegí sensaciones, no colores: el diseño se arma solo.' }
]
const BUSINESS_STEPS = [
  { id: 'contact', icon: 'store', title: 'Nombre y contacto', subtitle: 'Cómo te encuentran tus clientes', hint: 'Solo se completa lo que esté vacío.' },
  { id: 'describe', icon: 'file-text', title: 'Qué hacés', subtitle: 'Una descripción corta de tu negocio', hint: 'Podés pedir una sugerencia y editarla.', optional: true },
  { id: 'place', icon: 'map-pin', title: 'Dónde estás', subtitle: 'Provincia y ciudad', hint: '', optional: true },
  { id: 'hours', icon: 'clock', title: 'Tus horarios', subtitle: 'Cuándo atendés', hint: '', optional: true }
]
const steps = computed(() => (isBusiness.value ? BUSINESS_STEPS : DESIGN_STEPS))

const answers = reactive(emptyAssistAnswers())
// ask | loading | results | summary | done | error
const phase = ref('ask')
const step = ref(0)
const stepTitle = ref(null)
const confirming = ref(false)
const errorMsg = ref('')
const actionError = ref('')
const busy = ref('')
const saving = ref(false)
const proposals = ref([])
const seed = ref(null)
const mcp = ref(null)
const selectedId = ref('')
const provinces = ref([])
const cities = ref([])
const citiesLoading = ref(false)
const appliedKeys = ref([])

const currentStep = computed(() => steps.value[step.value])
const hasAnswers = computed(() => Boolean(
  answers.name || answers.rubro || answers.whatsapp || answers.description ||
  answers.province || answers.city || answers.hours_label || answers.hours_value ||
  answers.goals.length || answers.tone || answers.style_hint.length || answers.audience
))
const canSubmit = computed(() => Boolean(answers.rubro && resolvedTone(answers)))
const stepValid = computed(() => {
  const id = currentStep.value?.id
  if (id === 'rubro') return Boolean(answers.rubro)
  if (id === 'style') return Boolean(resolvedTone(answers))
  if (id === 'contact') return Boolean(answers.name.trim())
  return true
})
const stepPct = computed(() => Math.round(((step.value + (stepValid.value ? 1 : 0)) / steps.value.length) * 100))
const liveMessage = computed(() => {
  if (phase.value === 'loading') return 'Armando tu propuesta…'
  if (phase.value === 'results') return 'Tu propuesta está lista.'
  if (phase.value === 'summary') return 'Revisá qué se va a completar.'
  if (phase.value === 'done') return 'Listo.'
  if (phase.value === 'error') return 'No pudimos armar la propuesta.'
  return `Paso ${step.value + 1} de ${steps.value.length}: ${currentStep.value?.title || ''}.`
})

const shopName = computed(() =>
  answers.name.trim() || store.customization.display_name || auth.user?.profile?.business_name || 'Tu negocio')
const initial = computed(() => (shopName.value || 'T').slice(0, 1).toUpperCase())
const logo = computed(() => store.customization.logo || '')
const cover = computed(() => store.customization.cover || '')
const publicUrl = computed(() => (store.store?.slug ? `${window.location.origin}/${store.store.slug}` : ''))
const autofillDefault = computed(() => {
  const c = store.customization || {}
  const empty = (v) => !v || (Array.isArray(v) && !v.length) || (typeof v === 'string' && !v.trim())
  return empty(c.about_text) && empty(c.about_mission) && empty(c.faqs) && empty(c.services) && empty(c.announcements)
})

// ---------- Resumen "Mi negocio": solo campos vacíos ----------
// Cada fila: lo que el asistente juntó + si el campo actual ya tiene valor
// (en ese caso se omite, no se pisa).
const profile = computed(() => auth.user?.profile || {})
const fillRows = computed(() => {
  const c = store.customization || {}
  const has = (v) => Boolean(v && String(v).trim())
  const hasHours = Array.isArray(c.hours) && c.hours.length && has(c.hours[0]?.label)
  const rows = []
  if (answers.name.trim()) {
    rows.push({ key: 'name', label: 'Nombre del negocio', value: answers.name.trim(), skip: has(c.display_name) && has(profile.value.business_name) })
  }
  if (answers.whatsapp.trim()) {
    rows.push({ key: 'whatsapp', label: 'WhatsApp', value: answers.whatsapp.trim(), skip: has(c.whatsapp) })
  }
  if (answers.description.trim()) {
    rows.push({ key: 'description', label: 'Descripción', value: answers.description.trim(), skip: has(c.description) })
  }
  if (answers.province) {
    const label = provinces.value.find((p) => p.id === answers.province)?.name || answers.province
    rows.push({ key: 'province', label: 'Provincia', value: label, skip: has(profile.value.province) })
  }
  if (answers.city) {
    const label = cities.value.find((x) => x.id === answers.city)?.name || answers.city
    rows.push({ key: 'city', label: 'Ciudad', value: label, skip: has(profile.value.city) })
  }
  if (answers.hours_label.trim() && answers.hours_value.trim()) {
    rows.push({ key: 'hours', label: 'Horarios', value: `${answers.hours_label.trim()} · ${answers.hours_value.trim()}`, skip: hasHours })
  }
  return rows
})
const fillCount = computed(() => fillRows.value.filter((r) => !r.skip).length)

// ---------- Helpers de propuesta (misma vista que AiDesignView) ----------
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
const proposalVars = (p) => storeThemeVars(proposalForm(p))
const proposalTemplate = (p) => resolveStoreTemplate(p.template, allowed.value)
const proposalNameFont = (p) => ({ fontFamily: storeFontFamily(proposalForm(p).name_font) })
const proposalCover = (p) => (p?.cover?.mode === 'logo' ? '' : cover.value)
const selectedProposal = computed(() => proposals.value.find((p) => p.id === selectedId.value) || null)

// ---------- Ubicación ----------
async function loadProvinces() {
  if (provinces.value.length) return
  provinces.value = await locationsApi.getProvinces().catch(() => [])
}
watch(() => answers.province, async (id) => {
  answers.city = ''
  cities.value = []
  if (!id) return
  citiesLoading.value = true
  cities.value = await locationsApi.getCities(id).catch(() => [])
  citiesLoading.value = false
})
watch(() => currentStep.value?.id, (id) => {
  if (id === 'place') loadProvinces()
}, { immediate: true })

// ---------- Navegación del wizard ----------
function goStep(i) {
  if (i < 0 || i >= steps.value.length || saving.value) return
  if (i > step.value && !stepValid.value) return
  step.value = i
  nextTick(() => stepTitle.value?.focus?.())
}
function nextStep() {
  if (!stepValid.value || saving.value) return
  if (step.value < steps.value.length - 1) return goStep(step.value + 1)
  finish()
}
function prevStep() { goStep(step.value - 1) }
function skipStep() {
  if (!currentStep.value?.optional || saving.value) return
  goStep(step.value + 1)
}
function onStepKey(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  const tag = event.target?.tagName
  if (tag === 'TEXTAREA' || tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || tag === 'SELECT') return
  event.preventDefault()
  nextStep()
}

// ---------- Selecciones ----------
const pickRubro = (id) => { answers.rubro = answers.rubro === id ? '' : id }
const pickTone = (id) => { answers.tone = answers.tone === id ? '' : id }
const pickAudience = (id) => { answers.audience = answers.audience === id ? '' : id }
const toggleGoal = (id) => toggleId(answers.goals, id)
const toggleHint = (id) => toggleId(answers.style_hint, id, 2)
const toggleSection = (id) => toggleId(answers.sections, id)
function suggest() {
  const city = cities.value.find((c) => c.id === answers.city)?.name || ''
  answers.description = suggestDescription({ name: shopName.value, rubro: answers.rubro, city })
}

// ---------- Cierre / cancelación ----------
function requestClose() {
  if (busy.value) return
  if (hasAnswers.value && phase.value === 'ask' && !confirming.value) {
    confirming.value = true
    return
  }
  emit('close')
}
function onEsc(event) {
  if (event.key === 'Escape') requestClose()
}
onMounted(() => window.addEventListener('keydown', onEsc))
onBeforeUnmount(() => window.removeEventListener('keydown', onEsc))

// ---------- Flujo: Diseño ----------
async function submitDesign(extraSeed = 0) {
  phase.value = 'loading'
  errorMsg.value = ''
  actionError.value = ''
  try {
    const body = { prompt: buildPrompt(answers), history: [] }
    if (extraSeed) body.seed = extraSeed
    const data = await storesApi.aiDesignMcp(body)
    if (!data || !Array.isArray(data.proposals) || !data.proposals.length) throw new Error('empty')
    seed.value = data.seed
    proposals.value = data.proposals
    mcp.value = data.mcp || null
    phase.value = 'results'
    await nextTick()
    stepTitle.value?.focus?.()
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || 'No pudimos armar la propuesta. Probá de nuevo en un momento.'
    phase.value = 'error'
  }
}
async function applyProposal(proposal) {
  if (!seed.value || busy.value) return
  busy.value = `apply:${proposal.id}`
  actionError.value = ''
  try {
    await http.post('/stores/ai-design/apply/', {
      seed: seed.value,
      proposal_id: proposal.id,
      autofill: autofillDefault.value
    })
    await store.refreshCustomization()
    phase.value = 'done'
    emit('applied', { action: 'publish' })
  } catch (e) {
    actionError.value = e?.response?.data?.detail || 'No pudimos establecer el estilo. Probá de nuevo.'
  } finally {
    busy.value = ''
  }
}
function anotherStyle() { submitDesign((seed.value || 0) + 1) }

// ---------- Flujo: Mi negocio (solo rellena vacíos) ----------
async function applyBusiness() {
  if (saving.value || !fillCount.value) return
  saving.value = true
  actionError.value = ''
  const c = store.customization || {}
  const has = (v) => Boolean(v && String(v).trim())
  const payload = {}
  const name = answers.name.trim().slice(0, 60)
  if (name && !has(c.display_name)) payload.display_name = name
  const wsp = answers.whatsapp.trim().slice(0, 20)
  if (wsp && !has(c.whatsapp)) payload.whatsapp = wsp
  const desc = answers.description.trim().slice(0, 800)
  if (desc && !has(c.description)) payload.description = desc
  const hLabel = answers.hours_label.trim().slice(0, 60)
  const hValue = answers.hours_value.trim().slice(0, 60)
  const hasHours = Array.isArray(c.hours) && c.hours.length && has(c.hours[0]?.label)
  if (hLabel && hValue && !hasHours) {
    payload.hours = [{ label: hLabel, value: hValue }]
    payload.show_hours = true
  }
  const prof = {}
  if (name && !has(profile.value.business_name)) prof.business_name = name
  if (answers.province && !has(profile.value.province)) prof.province = answers.province
  if (answers.city && !has(profile.value.city)) prof.city = answers.city
  try {
    if (Object.keys(payload).length) await store.saveCustomization(payload)
    if (Object.keys(prof).length) await authApi.updateProfile(prof).catch(() => {})
    appliedKeys.value = [...Object.keys(payload), ...Object.keys(prof)]
    phase.value = 'done'
    emit('applied', { action: 'business' })
  } catch {
    actionError.value = 'No pudimos guardar esos datos. Los podés cargar después desde el panel.'
  } finally {
    saving.value = false
  }
}

function finish() {
  if (isBusiness.value) {
    phase.value = 'summary'
    nextTick(() => stepTitle.value?.focus?.())
  } else {
    submitDesign()
  }
}
</script>

<template>
  <div class="aia-overlay" @click.self="requestClose">
    <div class="aia-modal" role="dialog" aria-modal="true" :aria-label="isBusiness ? 'Asistencia con IA: datos del negocio' : 'Asistencia con IA: diseño de tu web'" @keydown="onStepKey">
      <header class="aia-head">
        <span class="aia-head-ico" aria-hidden="true"><AppIcon name="sparkles" :size="20" /></span>
        <div class="aia-head-txt">
          <h2>Asistencia con IA</h2>
          <small>{{ isBusiness ? 'Completamos los datos de tu negocio sin pisar lo que ya cargaste.' : 'Unas preguntas y te armamos el diseño de tu web.' }}</small>
        </div>
        <button type="button" class="aia-x" aria-label="Cerrar" @click="requestClose"><AppIcon name="x" :size="18" /></button>
      </header>
      <p class="aia-live" aria-live="polite">{{ liveMessage }}</p>

      <!-- CONFIRMAR SALIDA -->
      <div v-if="confirming" class="aia-confirm" role="alertdialog" aria-modal="true" aria-label="Descartar el asistente">
        <p><strong>¿Descartar el asistente?</strong> Perdés las respuestas que ya diste.</p>
        <div class="aia-confirm-btns">
          <button type="button" class="btn ghost btn-auto" @click="confirming = false">Seguir respondiendo</button>
          <button type="button" class="btn btn-auto" @click="emit('close')">Salir sin aplicar</button>
        </div>
      </div>

      <template v-else>
        <!-- WIZARD -->
        <div v-if="phase === 'ask'" class="aia-body">
          <ol class="aidw-bar" aria-label="Progreso del asistente">
            <li v-for="(s, i) in steps" :key="s.id" class="aidw-bar-item" :class="{ done: i < step, now: i === step }">
              <button type="button" class="aidw-bar-btn" :aria-current="i === step ? 'step' : undefined" :aria-label="`Paso ${i + 1}: ${s.title}`" :disabled="i > step && !stepValid" @click="goStep(i)">
                <span class="aidw-bar-num" aria-hidden="true"><AppIcon v-if="i < step" name="check" :size="13" :stroke="2.5" /><template v-else>{{ i + 1 }}</template></span>
                <span class="aidw-bar-label">{{ s.title }}</span>
              </button>
            </li>
          </ol>
          <div class="aidw-progress">
            <div class="aidw-progress-track" role="progressbar" :aria-valuenow="stepPct" aria-valuemin="0" aria-valuemax="100" :aria-label="`Avance: ${stepPct}%`">
              <span class="aidw-progress-fill" :style="{ width: `${stepPct}%` }"></span>
            </div>
            <span class="aidw-progress-txt">Paso {{ step + 1 }} de {{ steps.length }} · {{ stepPct }}%</span>
          </div>

          <section class="aidw-step" :aria-labelledby="`aia-title-${currentStep.id}`">
            <header class="aidw-step-head">
              <span class="aidw-step-ico" aria-hidden="true"><AppIcon :name="currentStep.icon" :size="20" /></span>
              <div class="aidw-step-text">
                <h3 :id="`aia-title-${currentStep.id}`" ref="stepTitle" tabindex="-1">{{ currentStep.title }}</h3>
                <p>{{ currentStep.subtitle }}</p>
              </div>
            </header>
            <p v-if="currentStep.hint" class="aidw-step-hint">{{ currentStep.hint }}</p>

            <!-- DISEÑO · rubro -->
            <template v-if="currentStep.id === 'rubro'">
              <p class="aidw-field-title">¿De qué es tu negocio?</p>
              <div class="aidw-grid rubros" role="radiogroup" aria-label="Rubro de tu negocio">
                <button v-for="r in RUBROS" :key="r.id" type="button" role="radio" class="aidw-card" :class="{ on: answers.rubro === r.id }" :aria-checked="answers.rubro === r.id" @click="pickRubro(r.id)">
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="r.icon" :size="18" /></span>
                  <span class="aidw-card-txt"><strong>{{ r.label }}</strong><small>{{ r.desc }}</small></span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.rubro === r.id" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
            </template>

            <!-- DISEÑO · secciones + objetivos -->
            <template v-else-if="currentStep.id === 'sections'">
              <p class="aidw-field-title">Marcá lo que tiene que aparecer en tu web</p>
              <div class="aidw-grid must" role="group" aria-label="Secciones de la web">
                <button v-for="s in SECTIONS" :key="s.id" type="button" class="aidw-card" :class="{ on: answers.sections.includes(s.id) }" :aria-pressed="answers.sections.includes(s.id)" :disabled="s.needs && !benefits[s.needs]" @click="toggleSection(s.id)">
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="s.icon" :size="18" /></span>
                  <span class="aidw-card-txt"><strong>{{ s.label }} <AppIcon v-if="s.needs && !benefits[s.needs]" name="lock" :size="12" /></strong><small>{{ s.desc }}</small></span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.sections.includes(s.id)" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="aidw-field-title">¿Qué querés lograr con la web?</p>
              <div class="aidw-grid goals" role="group" aria-label="¿Qué querés lograr con la web?">
                <button v-for="g in GOALS" :key="g.id" type="button" class="aidw-card" :class="{ on: answers.goals.includes(g.id) }" :aria-pressed="answers.goals.includes(g.id)" @click="toggleGoal(g.id)">
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="g.icon" :size="18" /></span>
                  <span class="aidw-card-txt"><strong>{{ g.label }}</strong><small>{{ g.desc }}</small></span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.goals.includes(g.id)" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
            </template>

            <!-- DISEÑO · estilo -->
            <template v-else-if="currentStep.id === 'style'">
              <p class="aidw-field-title">¿Cómo se tiene que sentir tu web?</p>
              <div class="aidw-grid tones" role="radiogroup" aria-label="¿Cómo se tiene que sentir tu web?">
                <button v-for="t in TONES" :key="t.id" type="button" role="radio" class="aidw-card tone" :class="{ on: answers.tone === t.id }" :aria-checked="answers.tone === t.id" @click="pickTone(t.id)">
                  <span class="aidw-card-ico big" aria-hidden="true"><AppIcon :name="t.icon" :size="22" /></span>
                  <span class="aidw-card-txt"><strong>{{ t.label }}</strong><small>{{ t.desc }}</small></span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.tone === t.id" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="aidw-field-title">¿A quién le hablás? <span class="aidw-opt">Opcional</span></p>
              <div class="aidw-grid audiences" role="radiogroup" aria-label="¿A quién le hablás?">
                <button v-for="a in AUDIENCES" :key="a.id" type="button" role="radio" class="aidw-card" :class="{ on: answers.audience === a.id }" :aria-checked="answers.audience === a.id" @click="pickAudience(a.id)">
                  <span class="aidw-card-ico" aria-hidden="true"><AppIcon :name="a.icon" :size="18" /></span>
                  <span class="aidw-card-txt"><strong>{{ a.label }}</strong><small>{{ a.desc }}</small></span>
                  <span class="aidw-card-check" aria-hidden="true"><AppIcon v-if="answers.audience === a.id" name="check" :size="13" :stroke="2.5" /></span>
                </button>
              </div>
              <p class="aidw-field-title">¿Qué te importa más? <span class="aidw-opt">Opcional, hasta dos</span></p>
              <div class="aidw-chips" role="group" aria-label="¿Qué te importa más?">
                <button v-for="h in STYLE_HINTS" :key="h.id" type="button" class="aidw-chip" :class="{ on: answers.style_hint.includes(h.id) }" :aria-pressed="answers.style_hint.includes(h.id)" @click="toggleHint(h.id)">
                  <AppIcon :name="h.icon" :size="15" aria-hidden="true" /> {{ h.label }}
                </button>
              </div>
            </template>

            <!-- NEGOCIO · contacto -->
            <template v-else-if="currentStep.id === 'contact'">
              <label class="aidw-field">
                <span class="aidw-field-title">¿Cómo se llama tu negocio?</span>
                <input v-model="answers.name" class="aidw-input" type="text" maxlength="60" placeholder="Ej.: Ferretería El Tornillo" aria-label="Nombre del negocio" />
                <small v-if="store.customization.display_name" class="aidw-note"><AppIcon name="check" :size="12" /> Ya tenés «{{ store.customization.display_name }}»: no se va a pisar.</small>
              </label>
              <label class="aidw-field">
                <span class="aidw-field-title">Tu WhatsApp <span class="aidw-opt">Opcional</span></span>
                <input v-model="answers.whatsapp" class="aidw-input" type="tel" maxlength="20" placeholder="Ej.: 221 555 1234" aria-label="Número de WhatsApp" />
                <small v-if="store.customization.whatsapp" class="aidw-note"><AppIcon name="check" :size="12" /> Ya cargado: no se va a pisar.</small>
              </label>
            </template>

            <!-- NEGOCIO · descripción -->
            <template v-else-if="currentStep.id === 'describe'">
              <p class="aidw-field-title">¿De qué es tu negocio? <span class="aidw-opt">Opcional</span></p>
              <div class="aidw-chips" role="radiogroup" aria-label="Rubro de tu negocio">
                <button v-for="r in RUBROS" :key="r.id" type="button" role="radio" class="aidw-chip" :class="{ on: answers.rubro === r.id }" :aria-checked="answers.rubro === r.id" @click="pickRubro(r.id)">
                  <AppIcon :name="r.icon" :size="15" aria-hidden="true" /> {{ r.label }}
                </button>
              </div>
              <label class="aidw-field">
                <span class="aidw-field-title">Contanos qué vendés en una frase <span class="aidw-opt">Opcional</span></span>
                <textarea v-model="answers.description" class="aidw-input" rows="3" maxlength="800" aria-label="Descripción corta del negocio" placeholder="Ej.: vendemos herramientas y pintura para el que arregla su casa."></textarea>
                <small v-if="store.customization.description" class="aidw-note"><AppIcon name="check" :size="12" /> Ya tenés una descripción: no se va a pisar.</small>
              </label>
              <button type="button" class="aidw-json-btn" @click="suggest"><AppIcon name="sparkles" :size="14" /> Escribime una sugerencia</button>
            </template>

            <!-- NEGOCIO · ubicación -->
            <template v-else-if="currentStep.id === 'place'">
              <div class="aidw-2col">
                <label class="aidw-field">
                  <span class="aidw-field-title">¿En qué provincia estás? <span class="aidw-opt">Opcional</span></span>
                  <select v-model="answers.province" class="aidw-input" aria-label="Provincia">
                    <option value="">Elegí una provincia</option>
                    <option v-for="p in provinces" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>
                  <small v-if="profile.province" class="aidw-note"><AppIcon name="check" :size="12" /> Ya cargada: no se va a pisar.</small>
                </label>
                <label class="aidw-field">
                  <span class="aidw-field-title">¿En qué ciudad o zona? <span class="aidw-opt">Opcional</span></span>
                  <select v-model="answers.city" class="aidw-input" :disabled="!answers.province || citiesLoading" aria-label="Ciudad o zona">
                    <option value="">{{ citiesLoading ? 'Cargando…' : 'Elegí una ciudad' }}</option>
                    <option v-for="c in cities" :key="c.id" :value="c.id">{{ c.name }}</option>
                  </select>
                  <small v-if="profile.city" class="aidw-note"><AppIcon name="check" :size="12" /> Ya cargada: no se va a pisar.</small>
                </label>
              </div>
            </template>

            <!-- NEGOCIO · horarios -->
            <template v-else-if="currentStep.id === 'hours'">
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
              <small v-if="store.customization.hours?.length" class="aidw-note"><AppIcon name="check" :size="12" /> Ya tenés horarios cargados: no se van a pisar.</small>
            </template>

            <div class="aidw-nav">
              <button v-if="step > 0" type="button" class="btn ghost btn-auto" :disabled="saving" @click="prevStep">
                <AppIcon name="chevron-left" :size="16" /> Atrás
              </button>
              <button type="button" class="btn ghost btn-auto" @click="requestClose">Cancelar</button>
              <button v-if="currentStep.optional && step < steps.length - 1" type="button" class="btn ghost btn-auto" :disabled="saving" @click="skipStep">Saltar este paso</button>
              <button v-if="step < steps.length - 1" type="button" class="btn btn-auto aidw-next" :disabled="!stepValid || saving" @click="nextStep">
                Siguiente <AppIcon name="chevron-right" :size="16" />
              </button>
              <button v-else type="button" class="btn btn-auto aidw-next" :disabled="(isBusiness ? false : !canSubmit) || saving" @click="nextStep">
                <AppIcon name="sparkles" :size="16" /> {{ isBusiness ? 'Revisar y aplicar' : 'Generar mi web' }}
              </button>
              <span class="aidw-nav-note">{{ step + 1 }} de {{ steps.length }}</span>
            </div>
          </section>
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

        <!-- RESULTADO DISEÑO -->
        <div v-else-if="phase === 'results'" class="aia-body">
          <p v-if="actionError" class="aid-error" role="alert">{{ actionError }}</p>
          <div v-if="mcp?.pattern" class="aid-mcp">
            <div class="aid-mcp-head">
              <AppIcon name="gem" :size="16" aria-hidden="true" />
              <strong>Elegimos el diseño «{{ mcp.pattern.nombre }}»{{ mcp.style ? ` con el estilo «${mcp.style.nombre}»` : '' }}</strong>
            </div>
          </div>
          <h3 ref="stepTitle" tabindex="-1" class="aia-results-title">Tu propuesta</h3>
          <div class="aid-grid">
            <AiIdeaCard
              v-for="p in proposals" :key="p.id"
              :proposal="p" :form="proposalForm(p)" :vars="proposalVars(p)" :template="proposalTemplate(p)"
              :shop-name="shopName" :initial="initial" :logo="logo" :cover="proposalCover(p)"
              :advanced="hasDesignAdvanced" :show-map="answers.sections.includes('map')"
              :name-font="proposalNameFont(p)" :busy="busy" :selected="selectedId === p.id" :public-url="publicUrl"
              @choose="selectedId = p.id" @preview="() => {}"
            />
          </div>
          <div class="aid-actions">
            <button class="btn btn-auto" type="button" :disabled="busy || !proposals.length" @click="applyProposal(selectedProposal || proposals[0])">
              <AppIcon name="check" :size="16" /> Publicar así
            </button>
            <button class="btn btn-auto" type="button" @click="anotherStyle"><AppIcon name="refresh" :size="16" /> Ver otro estilo</button>
            <button class="btn ghost btn-auto" type="button" @click="phase = 'ask'"><AppIcon name="chevron-left" :size="16" /> Volver a las preguntas</button>
          </div>
        </div>

        <!-- RESUMEN NEGOCIO -->
        <div v-else-if="phase === 'summary'" class="aia-body">
          <p v-if="actionError" class="aid-error" role="alert">{{ actionError }}</p>
          <section class="aidw-step" aria-labelledby="aia-title-summary">
            <header class="aidw-step-head">
              <span class="aidw-step-ico" aria-hidden="true"><AppIcon name="checklist" :size="20" /></span>
              <div class="aidw-step-text">
                <h3 id="aia-title-summary" ref="stepTitle" tabindex="-1">Revisá antes de aplicar</h3>
                <p>Solo se completa lo que está vacío. Lo que ya cargaste queda como está.</p>
              </div>
            </header>
            <ul v-if="fillRows.length" class="aia-fill">
              <li v-for="r in fillRows" :key="r.key" class="aia-fill-row" :class="{ skip: r.skip }">
                <span class="aia-fill-ico" aria-hidden="true"><AppIcon :name="r.skip ? 'lock' : 'check'" :size="14" /></span>
                <span class="aia-fill-txt">
                  <strong>{{ r.label }}</strong>
                  <small>{{ r.value }}</small>
                </span>
                <span class="aia-fill-tag">{{ r.skip ? 'Ya tiene valor' : 'Se completa' }}</span>
              </li>
            </ul>
            <p v-else class="aidw-note">No respondiste nada todavía: volvé atrás para completar.</p>
            <div class="aidw-nav">
              <button type="button" class="btn ghost btn-auto" :disabled="saving" @click="phase = 'ask'; goStep(steps.length - 1)"><AppIcon name="chevron-left" :size="16" /> Atrás</button>
              <button type="button" class="btn ghost btn-auto" @click="emit('close')">Descartar</button>
              <button type="button" class="btn btn-auto aidw-next" :disabled="!fillCount || saving" @click="applyBusiness">
                <AppIcon name="check" :size="16" /> {{ saving ? 'Aplicando…' : `Aplicar ${fillCount ? `(${fillCount})` : ''}` }}
              </button>
            </div>
          </section>
        </div>

        <!-- LISTO -->
        <div v-else-if="phase === 'done'" class="aia-body">
          <section class="aidw-step aia-done">
            <span class="aia-done-ico" aria-hidden="true"><AppIcon name="circle-check" :size="40" /></span>
            <h3 ref="stepTitle" tabindex="-1">{{ isBusiness ? 'Datos aplicados' : '¡Tu web quedó publicada!' }}</h3>
            <p>{{ isBusiness ? 'Completamos los campos vacíos de tu negocio.' : 'El diseño nuevo ya se ve en tu página.' }}</p>
            <div class="aid-actions">
              <a v-if="publicUrl" class="btn ghost btn-auto" :href="publicUrl" target="_blank" rel="noopener"><AppIcon name="external-link" :size="16" /> Ver mi web</a>
              <button type="button" class="btn btn-auto" @click="emit('close')"><AppIcon name="check" :size="16" /> Listo</button>
            </div>
          </section>
        </div>

        <!-- ERROR -->
        <div v-else class="card aid-error-box" role="alert">
          <AppIcon name="circle-alert" :size="24" />
          <div>
            <h2>No pudimos armar la propuesta</h2>
            <p>{{ errorMsg }}</p>
            <div class="aid-actions">
              <button class="btn btn-auto" type="button" @click="submitDesign()">Reintentar</button>
              <button class="btn ghost btn-auto" type="button" @click="phase = 'ask'">Volver a las preguntas</button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.aia-overlay {
  position: fixed; inset: 0; z-index: 90;
  display: grid; place-items: center; padding: 16px;
  background: rgb(15 18 25 / .55); backdrop-filter: blur(3px);
}
.aia-modal {
  display: flex; flex-direction: column; gap: 12px;
  width: min(960px, 100%); max-height: min(92vh, 860px); overflow-y: auto;
  padding: 18px 20px 20px;
  border: 1px solid var(--line); border-radius: var(--radius-lg);
  background: var(--surface); box-shadow: var(--shadow-lg, 0 18px 60px rgb(0 0 0 / .28));
}
.aia-head { display: flex; align-items: flex-start; gap: 12px; }
.aia-head-ico {
  display: grid; place-items: center; flex: none;
  width: 40px; height: 40px; border-radius: 12px;
  background: var(--brand-soft); color: var(--brand-ink); border: 1px solid var(--brand-soft-line);
}
.aia-head-txt { min-width: 0; flex: 1 1 auto; }
.aia-head-txt h2 { margin: 0; font-size: 18px; }
.aia-head-txt small { color: var(--muted); font-size: 12.5px; }
.aia-x {
  display: grid; place-items: center; flex: none;
  width: 34px; height: 34px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--card); color: var(--ink-2); cursor: pointer;
}
.aia-x:hover { border-color: var(--line-strong); }
.aia-x:focus-visible { outline: var(--focus-ring); outline-offset: 2px; }
.aia-live {
  position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap;
}
.aia-body { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.aia-results-title { margin: 0; font-size: 15px; }
.aia-results-title:focus { outline: none; }
.aia-confirm {
  display: flex; flex-direction: column; gap: 12px;
  padding: 16px; border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--card);
}
.aia-confirm p { margin: 0; font-size: 14px; }
.aia-confirm-btns { display: flex; flex-wrap: wrap; gap: 10px; justify-content: flex-end; }
.aia-fill { display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0; list-style: none; }
.aia-fill-row {
  display: flex; align-items: center; gap: 10px; min-width: 0;
  padding: 10px 12px; border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--card);
}
.aia-fill-row.skip { opacity: .65; }
.aia-fill-ico {
  display: grid; place-items: center; flex: none;
  width: 26px; height: 26px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--surface); color: var(--brand-ink);
}
.aia-fill-row.skip .aia-fill-ico { color: var(--muted); }
.aia-fill-txt { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 auto; }
.aia-fill-txt strong { font-size: 13px; }
.aia-fill-txt small { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.aia-fill-tag {
  flex: none; padding: 2px 8px; border-radius: 999px;
  background: var(--brand-soft); color: var(--brand-ink);
  font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
}
.aia-fill-row.skip .aia-fill-tag { background: var(--surface); color: var(--muted); }
.aia-done { align-items: center; text-align: center; }
.aia-done-ico { color: var(--brand-500); }
.aia-done h3 { margin: 0; font-size: 18px; }
.aia-done p { margin: 0; color: var(--muted); font-size: 13.5px; }
@media (max-width: 720px) {
  .aia-modal { padding: 14px; max-height: 96vh; }
  .aidw-bar-label { max-width: 96px; }
}
</style>
