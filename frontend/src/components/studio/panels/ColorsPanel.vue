<script setup>
// Panel "Colores": paleta por rol (siteTheme.palette), generador por
// armonías desde 1 color, extracción del logo, paletas por rubro,
// "Sorprendeme", conversor hex/HSL, gotero (EyeDropper con fallback),
// medidor de contraste AA en vivo con corrección automática y el modo
// claro/oscuro/automático con previsualización lado a lado.
// Escribe `theme.palette` (contrato) y espeja el acento en
// `form.accent_custom`/`form.theme` (campos que ya persisten).
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import AppIcon from '../../AppIcon.vue'
import TipHint from '../../TipHint.vue'
import PanelField from './PanelField.vue'
import PanelLock from './PanelLock.vue'
import { PALETTES } from '../../../utils/palettes.js'
import { extractLogoColors, harmonicAccent, deriveAccent } from '../../../utils/colorTools.js'
import {
  HARMONIES, harmonyPalette, contrastChecks, contrastRatio, fixContrast,
  normalizeHex, hexToHsl, hslToHex, hexToRgb
} from './panelShared.js'

const props = defineProps({
  theme: { type: Object, required: true },
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  customization: { type: Object, default: () => ({}) },
  viewer: { type: String, default: 'light' },
  shopName: { type: String, default: '' }
})
const emit = defineEmits(['navigate', 'set-viewer'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const pal = computed(() => props.theme.palette)
const isDark = computed(() => props.form?.theme === 'dark')

// ---------------------------------------------------------------------------
// Modo: tema de la página (persiste) + modo del lienzo (solo vista previa).
// ---------------------------------------------------------------------------
const pageModes = [
  { id: 'light', label: 'Claro', icon: 'sun' },
  { id: 'dark', label: 'Oscuro', icon: 'moon' }
]
function setPageTheme(mode) {
  props.form.theme = mode
  emit('set-viewer', mode)
}
// `Automático` resuelve con prefers-color-scheme y sigue al sistema mientras
// esté activo; si el usuario toca el sol/luna del lienzo se apaga solo.
const autoMode = ref(false)
let lastEmitted = null
const mq = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null
function emitViewer(m) { lastEmitted = m; emit('set-viewer', m) }
function setViewerMode(mode) {
  if (mode === 'auto') { autoMode.value = true; emitViewer(mq?.matches ? 'dark' : 'light') }
  else { autoMode.value = false; emitViewer(mode) }
}
function onOsMode() { if (autoMode.value) emitViewer(mq?.matches ? 'dark' : 'light') }
watch(() => props.viewer, (v) => { if (v !== lastEmitted) autoMode.value = false })
onMounted(() => mq?.addEventListener?.('change', onOsMode))
onBeforeUnmount(() => mq?.removeEventListener?.('change', onOsMode))
const viewerOpts = [
  { id: 'light', label: 'Claro', icon: 'sun' },
  { id: 'dark', label: 'Oscuro', icon: 'moon' },
  { id: 'auto', label: 'Automático', icon: 'sparkles' }
]
const viewerActive = computed(() => autoMode.value ? 'auto' : props.viewer)

// Miniatura lado a lado: el mismo .dl-pal-web del LookTab con los colores
// del borrador (acento, secundario y superficie del tema Studio).
const modeVars = computed(() => ({
  '--pa': pal.value.accent,
  '--pi': pal.value.secondary,
  '--ps': pal.value.surface
}))

// ---------------------------------------------------------------------------
// Paleta por rol. `accent` se sincroniza con el campo persistido
// (accent_custom) y arrastra primary/secondary para que el trío quede
// coherente; `bg` vuelve el fondo a sólido (un color plano gana a un
// degradado elegido antes).
// ---------------------------------------------------------------------------
const ROLE_GROUPS = [
  {
    id: 'marca', label: 'Marca', roles: [
      { key: 'primary', label: 'Primario', tip: 'El color fuerte de botones y llamadas a la acción.' },
      { key: 'secondary', label: 'Secundario', tip: 'Compañero del primario en degradados y detalles.' },
      { key: 'accent', label: 'Acento', tip: 'Enlaces, precios y detalles de marca. Se guarda con tu diseño.' }
    ]
  },
  {
    id: 'fondos', label: 'Fondos', roles: [
      { key: 'bg', label: 'Fondo', tip: 'El lienzo detrás de todo. Con color sólido reemplaza al fondo elegido en Fondo.' },
      { key: 'surface', label: 'Superficie', tip: 'El fondo de tarjetas, paneles y barras.' }
    ]
  },
  {
    id: 'texto', label: 'Texto', roles: [
      { key: 'text', label: 'Texto', tip: 'Títulos y párrafos.' },
      { key: 'muted', label: 'Texto suave', tip: 'Descripciones y datos secundarios.' }
    ]
  },
  {
    id: 'detalles', label: 'Detalles', roles: [
      { key: 'border', label: 'Bordes', tip: 'Contornos de tarjetas y campos.' },
      { key: 'success', label: 'Éxito', tip: 'Confirmaciones y estados correctos.' },
      { key: 'danger', label: 'Error', tip: 'Avisos y errores.' }
    ]
  }
]
function setRole(key, value) {
  const hex = normalizeHex(value)
  if (!hex) return
  pal.value[key] = hex
  if (key === 'accent') {
    pal.value.primary = hex
    pal.value.secondary = deriveAccent(hex).ink
    if (advanced.value) props.form.accent_custom = hex
  }
  if (key === 'bg' && props.theme.background.type !== 'solid') {
    props.theme.background.type = 'solid'
    props.theme.background.value = null
  }
}
function roleText(key, e) {
  setRole(key, e.target.value)
  e.target.value = pal.value[key]
}

// ---------------------------------------------------------------------------
// Generador desde 1 color + armonías.
// ---------------------------------------------------------------------------
const genBase = ref(pal.value.accent || '#6366f1')
const genMode = ref('analogous')
const genResult = computed(() => harmonyPalette(genBase.value, genMode.value, isDark.value))
async function applyGenerated() {
  // Primero el campo persistido: el watcher del shell rederiva secondary
  // desde el acento; la paleta completa se aplica después del flush para
  // que el tono de la armonía quede intacto.
  if (advanced.value) props.form.accent_custom = genResult.value.palette.accent
  await nextTick()
  Object.assign(pal.value, genResult.value.palette)
}
const baseInput = ref(null)
const hasEyeDropper = typeof window !== 'undefined' && 'EyeDropper' in window
async function pickWithDropper() {
  if (hasEyeDropper) {
    try {
      const { sRGBHex } = await new window.EyeDropper().open()
      const hex = normalizeHex(sRGBHex)
      if (hex) genBase.value = hex
    } catch { /* cancelado por el usuario */ }
  } else {
    baseInput.value?.showPicker?.()
  }
}

// ---------------------------------------------------------------------------
// Paletas por rubro + sorpresa.
// ---------------------------------------------------------------------------
const paletteVars = (p) => {
  const a = deriveAccent(p.accent)
  return { '--pa': a.hex, '--pi': a.ink, '--ps': a.soft }
}
const paletteActive = (p) => normalizeHex(pal.value.accent) === p.accent && props.form.theme === p.theme
function applyPalette(p) {
  setRole('accent', p.accent)
  props.form.theme = p.theme
}
const surpriseMsg = ref('')
async function surprise() {
  const next = harmonicAccent(pal.value.accent, props.form.theme)
  setRole('accent', next)
  // El watcher que limpia los mensajes corre antes del nextTick: el texto
  // queda visible hasta el próximo cambio real de paleta.
  await nextTick()
  surpriseMsg.value = `Probamos ${next}. Si no te convence, deshacelo con Ctrl+Z o sorprendete de nuevo.`
}

// ---------------------------------------------------------------------------
// Extracción de colores del logo (canvas).
// ---------------------------------------------------------------------------
const logoUrl = computed(() => props.customization?.logo || '')
const logoColors = ref([])
const logoBusy = ref(false)
const logoMsg = ref('')
async function readLogo() {
  if (!logoUrl.value) return
  logoBusy.value = true
  logoMsg.value = ''
  try {
    logoColors.value = await extractLogoColors(logoUrl.value, { max: 5 })
    if (!logoColors.value.length) logoMsg.value = 'No encontramos colores dominantes en tu logo.'
  } catch {
    logoMsg.value = 'No pudimos leer los colores del logo (probá subirlo de nuevo en Identidad).'
  } finally {
    logoBusy.value = false
  }
}
onMounted(readLogo)
function useLogoColor(hex) {
  setRole('accent', hex)
  logoMsg.value = `Aplicamos ${hex} como acento de tu marca.`
}

// ---------------------------------------------------------------------------
// Conversor hex / HSL.
// ---------------------------------------------------------------------------
const convHex = ref(normalizeHex(pal.value.accent) || '#4f46e5')
const convHsl = computed(() => hexToHsl(convHex.value))
function setConvFromHsl(part, v) {
  const { h, s, l } = convHsl.value
  const next = { h, s, l, [part]: Number(v) }
  convHex.value = hslToHex(next.h, next.s, next.l)
}
const convRgb = computed(() => hexToRgb(convHex.value))
const convReadout = computed(() => {
  const { h, s, l } = convHsl.value
  const [r, g, b] = convRgb.value
  return `hsl(${Math.round(h)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%) · rgb(${r}, ${g}, ${b})`
})
function applyConv() { setRole('accent', convHex.value) }

// ---------------------------------------------------------------------------
// Contraste AA en vivo + corrección automática.
// ---------------------------------------------------------------------------
const meters = computed(() => contrastChecks(pal.value).map((c) => ({
  ...c,
  ratio: contrastRatio(c.fg, c.bg),
  ok: contrastRatio(c.fg, c.bg) >= c.min
})))
const needsFix = computed(() => meters.value.some((m) => !m.ok))
const fixMsg = ref('')
async function fixAll() {
  // Hasta 3 pasadas: corregir un rol puede mover el piso de otro (el acento
  // se evalúa contra fondo y superficie).
  for (let i = 0; i < 3; i += 1) {
    const failing = contrastChecks(pal.value).filter((c) => contrastRatio(pal.value[c.fix], c.bg) < c.min)
    if (!failing.length) break
    for (const c of failing) pal.value[c.fix] = fixContrast(pal.value[c.fix], c.bg, c.min)
  }
  pal.value.primary = pal.value.accent
  if (advanced.value) props.form.accent_custom = pal.value.accent
  await nextTick()
  fixMsg.value = 'Ajustamos los colores que no llegaban al contraste AA.'
}
watch(() => JSON.stringify(pal.value), () => { fixMsg.value = ''; surpriseMsg.value = '' })
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      La paleta de tu página por rol, con herramientas para generarla y verificarla.
      Todo lo que tocás se ve al instante en la vista previa.
    </p>

    <!-- ===== Modo claro/oscuro + lado a lado ===== -->
    <PanelField
      label="Tema de la página"
      tip="¿Qué es esto? Es el modo en que tus visitantes ven tu página: colores claros sobre fondo claro, o invertidos en modo oscuro. Compará los dos y elegí."
      focus="page" need="none" :benefits="benefits"
      hint="Se guarda con tu diseño."
    >
      <div class="stp-modes" role="group" aria-label="Tema claro u oscuro de la página">
        <button
          v-for="m in pageModes" :key="m.id" type="button"
          class="stp-mode" :class="{ active: form.theme === m.id }" :data-t="m.id"
          :aria-pressed="form.theme === m.id" :style="modeVars"
          @click="setPageTheme(m.id)"
        >
          <span class="dl-pal-web" aria-hidden="true"><i class="dl-pal-nav"></i><i class="dl-pal-hero"><b></b></i><i class="dl-pal-row"><b></b><b></b></i></span>
          <span class="stp-mode-lb"><AppIcon :name="m.icon" :size="13" aria-hidden="true" /> {{ m.label }}</span>
        </button>
      </div>
    </PanelField>

    <PanelField
      label="Modo de la vista previa"
      tip="¿Qué es esto? Solo cambia cómo VOS ves el lienzo del Studio, sin guardar nada. En Automático la vista sigue al modo de tu sistema."
      focus="page" need="none" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Modo del lienzo de vista previa">
        <button
          v-for="o in viewerOpts" :key="o.id" type="button"
          class="stp-opt" :class="{ active: viewerActive === o.id }"
          :aria-pressed="viewerActive === o.id" @click="setViewerMode(o.id)"
        ><AppIcon :name="o.icon" :size="14" aria-hidden="true" /> {{ o.label }}</button>
      </div>
    </PanelField>

    <!-- ===== Generador desde 1 color ===== -->
    <PanelField
      label="Generador de paleta"
      tip="¿Qué es esto? Elegí un color base y una armonía: generamos una paleta completa con roles que ya cumplen el contraste. Análoga = tonos vecinos, Complementaria = el color opuesto, Triádica = tres colores equilibrados."
      focus="buttons" need="advanced" :benefits="benefits"
      :hint="HARMONIES.find((h) => h.id === genMode)?.hint"
    >
      <div class="stp-role">
        <input ref="baseInput" type="color" class="stp-swatch" :value="normalizeHex(genBase) || '#6366f1'" aria-label="Color base" @input="genBase = $event.target.value" />
        <input type="text" class="stp-hex" :value="genBase" aria-label="Color base en hexadecimal" maxlength="7" spellcheck="false" @change="genBase = normalizeHex($event.target.value) || genBase; $event.target.value = genBase" @keydown.enter.prevent="genBase = normalizeHex($event.target.value) || genBase; $event.target.value = genBase" />
        <button type="button" class="btn ghost btn-auto" @click="pickWithDropper">
          <AppIcon name="pipette" :size="15" aria-hidden="true" /> Gotero
        </button>
      </div>
      <div class="stp-seg" role="group" aria-label="Tipo de armonía">
        <button
          v-for="h in HARMONIES" :key="h.id" type="button"
          class="stp-opt" :class="{ active: genMode === h.id }"
          :aria-pressed="genMode === h.id" @click="genMode = h.id"
        >{{ h.label }}</button>
      </div>
      <div class="stp-tones" aria-hidden="true">
        <span v-for="(t, i) in genResult.tones" :key="i" class="stp-tone" :style="{ background: t }" :title="t"></span>
      </div>
      <button type="button" class="btn secondary btn-auto" @click="applyGenerated">
        <AppIcon name="check" :size="15" aria-hidden="true" /> Aplicar esta paleta
      </button>
    </PanelField>

    <!-- ===== Paletas por rubro + sorprender ===== -->
    <PanelField
      label="Paletas por rubro"
      tip="¿Qué es esto? Combinaciones ya probadas según tu tipo de negocio. Cada una aplica el acento y el modo de página juntos."
      focus="buttons" need="advanced" :benefits="benefits"
    >
      <div class="dl-pals" role="group" aria-label="Paletas sugeridas por rubro">
        <button
          v-for="p in PALETTES" :key="p.id" type="button" class="dl-pal"
          :class="{ active: paletteActive(p) }" :data-t="p.theme" :style="paletteVars(p)"
          :aria-pressed="paletteActive(p)" @click="applyPalette(p)"
        >
          <span class="dl-pal-web" aria-hidden="true"><i class="dl-pal-nav"></i><i class="dl-pal-hero"><b></b></i><i class="dl-pal-row"><b></b><b></b></i></span>
          <span class="dl-pal-name dl-ell">{{ p.label }}</span>
          <small class="dl-pal-hint">{{ p.hint }}</small>
        </button>
      </div>
      <button type="button" class="btn ghost btn-auto" @click="surprise">
        <AppIcon name="sparkles" :size="15" aria-hidden="true" /> Sorprendeme
      </button>
      <p v-if="surpriseMsg" class="stp-fhint" role="status">{{ surpriseMsg }}</p>
    </PanelField>

    <!-- ===== Desde el logo ===== -->
    <PanelField
      label="Color de tu logo"
      tip="¿Qué es esto? Leemos los colores dominantes de tu logo con un canvas y te los proponemos como acento, para que la página combine con tu marca."
      focus="buttons" need="advanced" :benefits="benefits"
      :hint="logoUrl ? 'Tocá un color para aplicarlo como acento.' : 'Subí tu logo en Estilos > Identidad y te sugerimos sus colores acá.'"
    >
      <template v-if="logoUrl">
        <div class="dl-chips" aria-live="polite">
          <span v-if="logoBusy" class="spinner" aria-hidden="true"></span>
          <button
            v-for="c in logoColors" :key="c" type="button" class="dl-chip"
            :style="{ background: c }" :title="`Usar ${c}`"
            :aria-label="`Usar el color ${c} del logo como acento`"
            @click="useLogoColor(c)"
          ></button>
        </div>
        <p v-if="logoMsg" class="stp-fhint" role="status">{{ logoMsg }}</p>
      </template>
    </PanelField>

    <!-- ===== Paleta por rol ===== -->
    <PanelField
      label="Paleta por rol"
      tip="¿Qué es esto? Cada color tiene un trabajo: primario manda en botones, secundario lo acompaña en degradados, acento marca enlaces y detalles, fondos y texto ordenan la lectura, y los estados avisan si algo salió bien o mal."
      focus="buttons" need="advanced" :benefits="benefits"
    >
      <div v-for="g in ROLE_GROUPS" :key="g.id" class="stp-role-group">
        <span class="stp-role-group-lb">{{ g.label }}</span>
        <div v-for="r in g.roles" :key="r.key" class="stp-role" :data-focus="r.key === 'accent' ? 'buttons' : 'page'">
          <span class="stp-role-lb">{{ r.label }} <TipHint :text="r.tip" /></span>
          <input type="color" class="stp-swatch" :value="pal[r.key]" :aria-label="`${r.label} (selector de color)`" @input="setRole(r.key, $event.target.value)" />
          <input type="text" class="stp-hex" :value="pal[r.key]" :aria-label="`${r.label} en hexadecimal`" maxlength="7" spellcheck="false" @change="roleText(r.key, $event)" @keydown.enter.prevent="roleText(r.key, $event)" />
        </div>
      </div>
    </PanelField>

    <!-- ===== Conversor hex / HSL ===== -->
    <PanelField
      label="Conversor de color"
      tip="¿Qué es esto? Un traductor entre hex (#4f46e5) y HSL (tono, saturación y luz). Mové los deslizadores para afinar el color y aplicarlo como acento."
      focus="buttons" need="advanced" :benefits="benefits"
      :hint="convReadout"
    >
      <div class="stp-role">
        <input type="color" class="stp-swatch" :value="normalizeHex(convHex) || '#4f46e5'" aria-label="Color a convertir" @input="convHex = $event.target.value" />
        <input type="text" class="stp-hex" :value="convHex" aria-label="Color en hexadecimal" maxlength="7" spellcheck="false" @change="convHex = normalizeHex($event.target.value) || convHex; $event.target.value = convHex" @keydown.enter.prevent="convHex = normalizeHex($event.target.value) || convHex; $event.target.value = convHex" />
        <button type="button" class="btn ghost btn-auto" @click="applyConv">Usar como acento</button>
      </div>
      <label class="stp-angle">
        <span class="stp-role-lb">Tono <b class="stp-val">{{ Math.round(convHsl.h) }}°</b></span>
        <input type="range" class="stp-range" min="0" max="360" :value="Math.round(convHsl.h)" aria-label="Tono del color" @input="setConvFromHsl('h', $event.target.value)" />
      </label>
      <label class="stp-angle">
        <span class="stp-role-lb">Saturación <b class="stp-val">{{ Math.round(convHsl.s * 100) }}%</b></span>
        <input type="range" class="stp-range" min="0" max="100" :value="Math.round(convHsl.s * 100)" aria-label="Saturación del color" @input="setConvFromHsl('s', Number($event.target.value) / 100)" />
      </label>
      <label class="stp-angle">
        <span class="stp-role-lb">Luz <b class="stp-val">{{ Math.round(convHsl.l * 100) }}%</b></span>
        <input type="range" class="stp-range" min="0" max="100" :value="Math.round(convHsl.l * 100)" aria-label="Luz del color" @input="setConvFromHsl('l', Number($event.target.value) / 100)" />
      </label>
    </PanelField>

    <!-- ===== Contraste AA ===== -->
    <PanelField
      label="Contraste accesible"
      tip="¿Qué es esto? El estándar WCAG pide que el texto se lea bien sobre su fondo (4.5:1 para texto normal, 3:1 para textos grandes y elementos). Si algo no llega, lo corregimos por vos."
      focus="page" need="advanced" :benefits="benefits"
    >
      <div class="dl-meters" aria-live="polite">
        <div v-for="m in meters" :key="m.key" class="dl-meter" :class="m.ok ? 'ok' : 'warn'">
          <span class="dl-meter-ico"><AppIcon :name="m.ok ? 'circle-check' : 'circle-alert'" :size="18" aria-hidden="true" /></span>
          <div class="dl-meter-body">
            <strong>{{ m.label }} <span class="dl-meter-ratio">{{ m.ratio.toFixed(1) }}:1</span></strong>
            <small>{{ m.ok ? 'Cumple el mínimo AA.' : `Pide ${m.min}:1 — corregilo automáticamente o ajustá el color.` }}</small>
          </div>
        </div>
      </div>
      <div v-if="needsFix" class="dl-fix">
        <button type="button" class="btn ghost btn-auto" @click="fixAll"><AppIcon name="check" :size="16" aria-hidden="true" /> Corregir automáticamente</button>
      </div>
      <p v-if="fixMsg" class="stp-fhint" role="status">{{ fixMsg }}</p>
    </PanelField>

    <PanelLock
      v-if="!advanced"
      text="La paleta por rol, las armonías y las paletas por rubro vienen con el Plan premium. Tu acento básico se sigue editando en Estilos."
      @plans="emit('navigate', 'plans')"
    />
  </div>
</template>

