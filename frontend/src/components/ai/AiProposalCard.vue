<script setup>
import { ref, computed, watch } from 'vue'
import AppIcon from '../AppIcon.vue'
import AiLiveThumb from './AiLiveThumb.vue'
import AiImageRequest from './AiImageRequest.vue'
import AiDraftCopy from './AiDraftCopy.vue'
import { storeFontFamily, ensureStoreFont } from '../../api/stores.api.js'

const props = defineProps({
  proposal: { type: Object, required: true },
  form: { type: Object, default: () => ({}) },
  vars: { type: Object, default: () => ({}) },
  template: { type: String, default: 'classic' },
  shopName: { type: String, default: '' },
  initial: { type: String, default: 'T' },
  logo: { type: String, default: '' },
  cover: { type: String, default: '' },
  advanced: { type: Boolean, default: false },
  showMap: { type: Boolean, default: false },
  nameFont: { type: Object, default: () => ({}) },
  busy: { type: String, default: '' },
  published: { type: Boolean, default: false },
  publicUrl: { type: String, default: '' },
  autofillDefault: { type: Boolean, default: true }
})
const emit = defineEmits(['preview', 'apply', 'change-style', 'refresh-images'])

const autofill = ref(props.autofillDefault)
watch(() => props.autofillDefault, (v) => { autofill.value = v })

// ---- v6 Extras: la IA propone, el dueño acepta ----
// `extras.offered` trae el detalle legible de cada bloque ai_only (label +
// para qué + qué datos reales usa); `extras.applied` son los que ya viajan
// prendidos en el layout. El tope es el del motor (AI_ELEMENT_MAX = 4): acá
// se refleja para que el contador "N de 4" y el disabled sean locales.
const EXTRA_MAX = 4
const extraItems = computed(() => {
  const list = props.proposal?.extras?.offered
  return Array.isArray(list) ? list.filter((item) => item && item.kind) : []
})
const chosen = ref([])
function resetExtras() {
  chosen.value = extraItems.value
    .filter((item) => item.block?.enabled)
    .map((item) => item.kind)
    .slice(0, EXTRA_MAX)
}
watch(() => props.proposal, resetExtras, { immediate: true })
const chosenCount = computed(() => chosen.value.length)
const canAdd = computed(() => chosen.value.length < EXTRA_MAX)
function isChosen(kind) {
  return chosen.value.includes(kind)
}
function addExtra(kind) {
  if (!isChosen(kind) && canAdd.value) chosen.value = [...chosen.value, kind]
}
function removeExtra(kind) {
  chosen.value = chosen.value.filter((k) => k !== kind)
}
// apply recibe la elección completa: los ofrecidos (para que un extra
// rechazado quede apagado en el borrador y no desaparezca) y los elegidos.
const extrasPayload = computed(() => ({
  offered: extraItems.value.map((item) => item.kind),
  applied: chosen.value
}))
function applyProposal() {
  emit('apply', {
    proposal: props.proposal,
    autofill,
    ...(extraItems.value.length ? { extras: extrasPayload.value } : {})
  })
}

const requests = computed(() => (Array.isArray(props.proposal.image_requests) ? props.proposal.image_requests : []))
const draft = computed(() => props.proposal.copy_draft || {})
const applying = computed(() => props.busy === `apply:${props.proposal.id}`)
const notes = computed(() => (Array.isArray(props.proposal.notes) ? props.proposal.notes.slice(0, 3) : []))
const themeChoice = computed(() => props.proposal.theme_choice || null)
// v6: qué rediseñó el motor (composición + piel). Se muestra como chip de
// texto: la tarjeta tiene que decir qué cambió, no solo de qué color es.
const redesign = computed(() => props.proposal.redesign || null)
const redesignText = computed(() => {
  const summary = String(redesign.value?.summary || '').trim()
  if (summary) return summary
  return redesign.value?.changed ? 'Portada, catálogo y servicios reorganizados' : ''
})
// ---- v6: `look` (resumen legible) y `score` (calidad medida) ----
// `look.changed` es lo que el motor tocó de verdad (tipografía, portada,
// orden, grilla, servicios): la tarjeta lo lista para que el dueño vea el
// rediseño y no solo un punto de color. `score` va sin número frío: tres
// barras + una etiqueta en castellano.
const look = computed(() => (props.proposal.look && typeof props.proposal.look === 'object' ? props.proposal.look : null))
const styleLabel = computed(() => String(look.value?.style_label || props.proposal.variety?.style_label || '').trim())
const changed = computed(() => {
  const list = look.value?.changed
  if (!Array.isArray(list)) {
    return redesign.value?.changed ? ['Portada, catálogo y servicios reorganizados'] : []
  }
  return list.filter((item) => typeof item === 'string' && item.trim()).slice(0, 5)
})
const score = computed(() => {
  const raw = props.proposal.score
  if (!raw || typeof raw !== 'object') return null
  const total = Number(raw.total)
  if (!Number.isFinite(total)) return null
  const label = total >= 90 ? 'Excelente' : total >= 80 ? 'Muy bueno' : total >= 70 ? 'Bueno' : 'Aceptable'
  const level = total >= 90 ? 3 : total >= 75 ? 2 : 1
  const issues = Array.isArray(raw.issues) ? raw.issues.filter((i) => typeof i === 'string' && i.trim()).slice(0, 2) : []
  return { total, label, level, issues }
})

const nightMode = computed(() => props.proposal.night_mode || null)
const coverChoice = computed(() => props.proposal.cover || null)
const themeSource = computed(() => (themeChoice.value?.source === 'user' ? 'elegido por vos' : 'elegido por la IA'))
const nightText = computed(() => {
  if (!nightMode.value?.enabled) return ''
  return nightMode.value.default === 'dark'
    ? 'Con modo noche, arranca en oscuro'
    : 'Con modo noche, arranca en claro'
})

// ---- Firma visual: familia del estilo + tipografía real por rol ----
// Nada de nombres técnicos: el backend manda la etiqueta humana del estilo y
// acá traducimos la familia a un nombre en castellano. El punto de color es
// el de la familia, no el acento: así dos propuestas se distinguen de un
// vistazo aunque compartan paleta.
const FAMILY_LABELS = {
  glass: 'Cristal', editorial: 'Editorial', brutal: 'Brutal', tech: 'Tecnología',
  warm: 'Cálida', luxury: 'Lujo', kinetic: 'Cinética', paper: 'Papel', neon: 'Neón',
  minimal: 'Minimal', organic: 'Orgánica', retro: 'Retro', corporate: 'Corporativa',
  playful: 'Lúdica', mono: 'Monocromo', gradient: 'Degradé', cinematic: 'Cinemática'
}
const FAMILY_COLORS = {
  glass: '#38bdf8', editorial: '#334155', brutal: '#111827', tech: '#0ea5e9',
  warm: '#f97316', luxury: '#a16207', kinetic: '#ec4899', paper: '#c9b892', neon: '#84cc16',
  minimal: '#64748b', organic: '#16a34a', retro: '#e11d48', corporate: '#1d4ed8',
  playful: '#f59e0b', mono: '#475569', gradient: '#8b5cf6', cinematic: '#0f766e'
}
// Tamaño relativo de cada rol (los tokens son xs..display; acá se achican
// para que los tres "Aa" entren en una tira sin dominar la tarjeta).
const ROLE_SIZE = { xs: 10, sm: 11, md: 12, lg: 14, xl: 16, '2xl': 19, '3xl': 21, display: 24 }
const ROLE_TRACKING = { tighter: '-.03em', tight: '-.015em', normal: '0', wide: '.03em', wider: '.07em' }
const ROLE_LEADING = { tight: 1.05, snug: 1.15, normal: 1.3, relaxed: 1.45 }
const ROLE_SAMPLES = [
  { role: 'display', label: 'Título' },
  { role: 'body', label: 'Texto' },
  { role: 'price', label: 'Precio' }
]

// El contrato v4 manda `skin` arriba; si viene solo dentro del tema se lee
// de ahí (así la tarjeta no depende de un único lugar).
const skin = computed(() => {
  const direct = props.proposal.skin
  if (direct && typeof direct === 'object' && Object.keys(direct).length) return direct
  const themed = props.proposal.site_theme?.skin
  return themed && typeof themed === 'object' ? themed : {}
})
const family = computed(() => skin.value.family || props.proposal.variety?.family || '')
const familyLabel = computed(() => FAMILY_LABELS[family.value] || '')
const skinLabel = computed(() => String(skin.value.label || '').trim())
const skinDot = computed(() => {
  const accent = props.proposal.theme_choice?.accent
  return FAMILY_COLORS[family.value] || (/^#[0-9a-f]{6}$/i.test(String(accent || '')) ? accent : 'var(--aid-accent)')
})
const roles = computed(() => {
  const direct = props.proposal.typography_roles
  if (direct && typeof direct === 'object' && Object.keys(direct).length) return direct
  return props.proposal.site_theme?.typography?.roles || {}
})

function fontStack(slug) {
  const s = String(slug || '').trim()
  if (!s) return ''
  if (s.includes(',') || s.includes("'") || s.includes('"')) return s
  return storeFontFamily(s)
}
function roleStyle(role) {
  const def = roles.value?.[role] || {}
  const fallbackFont = role === 'display'
    ? props.proposal.site_theme?.typography?.heading
    : props.proposal.site_theme?.typography?.body
  return {
    fontFamily: fontStack(def.font || fallbackFont),
    fontSize: `${ROLE_SIZE[def.size] || (role === 'display' ? 24 : 12)}px`,
    fontWeight: String(def.weight || (role === 'display' ? 700 : 500)),
    letterSpacing: ROLE_TRACKING[def.tracking] || '0',
    lineHeight: String(ROLE_LEADING[def.leading] || 1.2),
    textTransform: def.case === 'upper' ? 'uppercase' : 'none'
  }
}
const roleSamples = computed(() => ROLE_SAMPLES.map((r) => ({ ...r, style: roleStyle(r.role) })))
const roleText = computed(() => {
  const names = ROLE_SAMPLES.map((r) => {
    const def = roles.value?.[r.role] || {}
    const label = def.font ? (storeFontFamily(def.font) || '').split(',')[0].replace(/['"]/g, '') : ''
    return label ? `${label} para ${r.label.toLowerCase()}` : ''
  }).filter(Boolean)
  return names.length ? `Tipografía: ${names.join(', ')}.` : ''
})
const hasSignature = computed(() => Boolean(skinLabel.value || familyLabel.value || roleText.value))

// Las fuentes de la tira se piden a Google Fonts la primera vez (una sola
// vez por familia, en todo el panel).
watch(
  () => ROLE_SAMPLES.map((r) => roles.value?.[r.role]?.font || '').join('|'),
  (key) => key.split('|').filter(Boolean).forEach((slug) => ensureStoreFont(slug)),
  { immediate: true }
)
</script>

<template>
  <article class="aidp" :class="{ applied: published }">
    <header class="aidp-head">
      <div>
        <h3>{{ proposal.label }}</h3>
        <p v-if="proposal.why">{{ proposal.why }}</p>
      </div>
      <span v-if="published" class="aidp-badge published">
        <AppIcon name="circle-check" :size="12" /> Publicada
      </span>
    </header>

    <div v-if="hasSignature" class="aidp-sig">
      <div class="aidp-sig-chips">
        <span v-if="skinLabel" class="aidp-chip aidp-chip-skin">
          <span class="aidp-dot" :style="{ background: skinDot }" aria-hidden="true"></span>
          {{ skinLabel }}
        </span>
        <span v-if="familyLabel" class="aidp-chip aidp-chip-family">{{ familyLabel }}</span>
        <span v-if="styleLabel" class="aidp-chip aidp-chip-style">{{ styleLabel }}</span>
      </div>
      <div v-if="roleText" class="aidp-type" aria-hidden="true">
        <span v-for="s in roleSamples" :key="s.role" class="aidp-type-item">
          <span class="aidp-type-aa" :style="s.style">Aa</span>
          <span class="aidp-type-label">{{ s.label }}</span>
        </span>
      </div>
      <span v-if="roleText" class="sr-only">{{ roleText }}</span>
    </div>

    <div class="aidp-media">
      <div class="aid-mini">
        <AiLiveThumb
          :proposal="proposal"
          :form="form"
          :vars="vars"
          :template="template"
          :shop-name="shopName"
          :initial="initial"
          :logo="logo"
          :cover="cover"
          :advanced="advanced"
          :show-map="showMap"
          :name-font="nameFont"
          :public-url="publicUrl"
        />
      </div>
      <button
        type="button"
        class="aidp-media-btn"
        :aria-label="`Ver en grande: ${proposal.label}`"
        @click="emit('preview')"
      >
        <span class="aidp-media-hint"><AppIcon name="eye" :size="14" /> Ver en grande</span>
      </button>
    </div>

    <div v-if="themeChoice || nightText" class="aidp-chips">
      <span v-if="themeChoice" class="aidp-chip">
        <span class="aidp-dot" :style="{ background: themeChoice.accent || 'var(--aid-accent)' }" aria-hidden="true"></span>
        Color {{ themeSource }}
      </span>
      <span v-if="nightText" class="aidp-chip">
        <AppIcon name="moon" :size="13" aria-hidden="true" /> {{ nightText }}
      </span>
      <span v-if="redesignText" class="aidp-chip aidp-chip-redesign">
        <AppIcon name="dashboard" :size="13" aria-hidden="true" /> {{ redesignText }}
      </span>
    </div>

    <p v-if="coverChoice?.reason" class="aidp-reason">
      <AppIcon name="image" :size="13" aria-hidden="true" /> {{ coverChoice.reason }}
    </p>

    <ul v-if="notes.length" class="aidp-notes">
      <li v-for="(n, k) in notes" :key="k">{{ n }}</li>
    </ul>

    <!-- Qué cambió: lo que el motor rediseñó de verdad, no una lista fija. -->
    <section v-if="changed.length" class="aidp-changed" :aria-labelledby="`changed-${proposal.id}`">
      <strong :id="`changed-${proposal.id}`">Qué cambió</strong>
      <ul>
        <li v-for="(item, k) in changed" :key="k">
          <AppIcon name="check" :size="13" aria-hidden="true" /> {{ item }}
        </li>
      </ul>
    </section>

    <!-- Calidad: barras + etiqueta ("Se ve así de bien"), nunca un número frío. -->
    <div v-if="score" class="aidp-score">
      <span class="aidp-score-bars" aria-hidden="true">
        <span v-for="n in 3" :key="n" :class="['aidp-score-bar', { on: n <= score.level }]"></span>
      </span>
      <span class="aidp-score-text">Se ve así de bien: <strong>{{ score.label }}</strong></span>
      <small v-for="(issue, k) in score.issues" :key="`i${k}`" class="aidp-score-issue">{{ issue }}</small>
    </div>

    <!-- Extras: chips con Quitar (aplicados) / Sumar (ofrecidos) y "N de 4". -->
    <section v-if="extraItems.length" class="aidp-extras" :aria-labelledby="`extras-${proposal.id}`">
      <div class="aidp-extras-head">
        <strong :id="`extras-${proposal.id}`">Elementos extra</strong>
        <span class="aidp-extras-count" :aria-label="`${chosenCount} de ${EXTRA_MAX} elegidos`">
          {{ chosenCount }} de {{ EXTRA_MAX }}
        </span>
      </div>
      <ul class="aidp-extras-list">
        <li
          v-for="ex in extraItems"
          :key="ex.kind"
          class="aidp-extra"
          :class="{ on: isChosen(ex.kind) }"
        >
          <span class="aidp-extra-main">
            <span class="aidp-extra-label">
              <AppIcon :name="isChosen(ex.kind) ? 'circle-check' : 'plus-circle'" :size="14" aria-hidden="true" />
              {{ ex.label }}
            </span>
            <small class="aidp-extra-why">{{ ex.why }}</small>
            <small v-if="ex.needs" class="aidp-extra-needs">{{ ex.needs }}</small>
          </span>
          <button
            v-if="!published && isChosen(ex.kind)"
            type="button"
            class="aidp-extra-btn"
            @click="removeExtra(ex.kind)"
          >
            Quitar
          </button>
          <button
            v-else-if="!published"
            type="button"
            class="aidp-extra-btn add"
            :disabled="!canAdd"
            @click="addExtra(ex.kind)"
          >
            Sumar
          </button>
          <span v-else-if="isChosen(ex.kind)" class="aidp-extra-tag">Aplicado</span>
        </li>
      </ul>
    </section>

    <AiImageRequest
      v-for="req in requests"
      :key="req.id"
      :request="req"
      @refresh="emit('refresh-images')"
    />

    <AiDraftCopy v-model="autofill" :draft="draft" />

    <div v-if="published" class="aidp-published" role="status">
      <span class="aidp-published-title">
        <AppIcon name="circle-check" :size="16" /> Tu web ya está publicada
      </span>
      <div class="aidp-published-actions">
        <a v-if="publicUrl" class="btn btn-auto" :href="publicUrl" target="_blank" rel="noopener">
          <AppIcon name="external-link" :size="16" /> Ver mi página
        </a>
        <button class="btn ghost btn-auto" type="button" @click="emit('change-style')">
          <AppIcon name="refresh" :size="16" /> Cambiar el estilo
        </button>
      </div>
    </div>

    <footer v-else class="aidp-actions">
      <button class="btn ghost btn-auto" type="button" @click="emit('preview')">
        <AppIcon name="eye" :size="16" /> Ver en grande
      </button>
      <button class="btn btn-auto aid-primary" type="button" :disabled="Boolean(busy)" @click="applyProposal">
        <AppIcon name="check" :size="16" /> {{ applying ? 'Publicando…' : 'Establecer este estilo' }}
      </button>
    </footer>
  </article>
</template>
