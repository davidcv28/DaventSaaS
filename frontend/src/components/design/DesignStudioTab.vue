<script setup>
// Pestaña "Studio" de la sección Diseño (Premium / has_design_advanced).
// Cinco editores que escriben el site_theme PARCIAL del formulario — el
// mismo que aplica DesignStylesTab— así la vista previa en vivo los muestra
// al instante por postMessage y «Guardar cambios» los publica:
//   1. Colores de contenedores  -> site_theme.surfaces {card,nav,footer,hero}
//   2. Fuentes por área         -> site_theme.typography.roles (13 roles)
//   3. Fotos de producto        -> site_theme.images {ratio,fit,bg,radius,border}
//   4. Fondo de la web          -> site_theme.background {type,value,overlay}
//   5. Botones                   -> site_theme.buttons {style,shape,size,borderStyle}
// Cada control escribe solo su clave: lo no tocado hereda el look del
// diseño/estilo elegido y el tema guardado queda parcial y limpio.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { normalizeHex, inkOn } from '../../studio/contract.js'
import { STORE_FONTS, ensureStoreFont } from '../../api/stores.api.js'
import {
  buildGradient, buildMesh, buildPattern, parseGradient,
  MESH_LOOKS, PATTERN_LOOKS
} from '../studio/panels/panelShared.js'
import DesignLivePreview from './DesignLivePreview.vue'
import AppIcon from '../AppIcon.vue'
import '../../assets/studio-panels.css'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  customization: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['close'])

// Modal fullscreen: Escape cierra, el scroll del fondo se bloquea y el
// foco arranca en la X (mismo criterio que los modales de DesignStylesTab).
const closeBtn = ref(null)
function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  document.body.style.overflow = 'hidden'
  nextTick(() => closeBtn.value?.focus())
  // Las muestras «Aa» de cada rol necesitan su familia cargada en el dashboard.
  ROLE_ROWS.forEach((r) => {
    const f = roleVal(r.role, 'font')
    if (f && STORE_FONTS[f]) ensureStoreFont(f)
  })
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})

const theme = computed(() => (props.form.site_theme && typeof props.form.site_theme === 'object'
  ? props.form.site_theme : {}))
const pal = computed(() => theme.value.palette || {})

// Escritura quirúrgica del tema parcial: valor null/vacío borra la clave
// (vuelve a heredar); sección vacía se elimina entera.
function patchTheme(mut) {
  const next = { ...theme.value }
  mut(next)
  props.form.site_theme = next
}
function setKey(section, key, value) {
  patchTheme((t) => {
    const sec = { ...(t[section] || {}) }
    if (value === undefined || value === null || value === '') delete sec[key]
    else sec[key] = value
    if (Object.keys(sec).length) t[section] = sec
    else delete t[section]
  })
}
function setColor(section, key, raw) {
  const hex = normalizeHex(raw)
  if (hex) setKey(section, key, hex)
}
function colorText(section, key, e) {
  setColor(section, key, e.target.value)
  e.target.value = theme.value[section]?.[key] || ''
}

// ===========================================================================
// 1. Colores de contenedores (surfaces)
// ===========================================================================
const SURFACES = [
  { key: 'card', label: 'Tarjetas y paneles', hint: 'El fondo de tarjetas de producto, servicios, preguntas y formularios.' },
  { key: 'nav', label: 'Barra superior', hint: 'La barra con tu logo, el menú y el botón de acción.' },
  { key: 'footer', label: 'Pie de página', hint: 'La franja final con tus datos, links y redes.' },
  { key: 'hero', label: 'Portada', hint: 'La banda principal de la home cuando no lleva foto.' }
]
const surfaceColor = (key) => theme.value.surfaces?.[key] || ''
function setSurface(key, raw) { setColor('surfaces', key, raw) }
function surfaceText(key, e) { colorText('surfaces', key, e) }
function clearSurface(key) { setKey('surfaces', key, null) }

// ===========================================================================
// 2. Fuentes por área (typography.roles — 13 roles del contrato v4)
// ===========================================================================
const ROLE_ROWS = [
  { role: 'display', label: 'Display gigante', group: 'Titulares' },
  { role: 'h1', label: 'Título principal', group: 'Titulares' },
  { role: 'h2', label: 'Título de sección', group: 'Titulares' },
  { role: 'h3', label: 'Subtítulo', group: 'Titulares' },
  { role: 'quote', label: 'Citas', group: 'Titulares' },
  { role: 'body', label: 'Texto', group: 'Cuerpo' },
  { role: 'lead', label: 'Bajada', group: 'Cuerpo' },
  { role: 'eyebrow', label: 'Etiqueta', group: 'Cuerpo' },
  { role: 'label', label: 'Rótulos', group: 'Cuerpo' },
  { role: 'price', label: 'Precios', group: 'Cuerpo' },
  { role: 'nav', label: 'Menú', group: 'Navegación' },
  { role: 'button', label: 'Botones', group: 'Navegación' },
  { role: 'footer', label: 'Pie de página', group: 'Navegación' }
]
const ROLE_GROUPS = [...new Set(ROLE_ROWS.map((r) => r.group))]
const rowsOf = (g) => ROLE_ROWS.filter((r) => r.group === g)

// Defaults por rol cuando el usuario personaliza uno que no existía: el
// spec viaja completo (el backend exige los 6 campos por rol).
const DISPLAY_ROLES = ['display', 'h1', 'h2', 'h3', 'quote']
const ROLE_DEFAULTS = {
  display: { size: 'display', weight: 800, tracking: 'tight', leading: 'tight', case: 'none' },
  h1: { size: '3xl', weight: 800, tracking: 'tight', leading: 'tight', case: 'none' },
  h2: { size: '2xl', weight: 700, tracking: 'tight', leading: 'snug', case: 'none' },
  h3: { size: 'xl', weight: 700, tracking: 'tight', leading: 'snug', case: 'none' },
  quote: { size: 'xl', weight: 600, tracking: 'tight', leading: 'snug', case: 'none' },
  body: { size: 'md', weight: 400, tracking: 'normal', leading: 'relaxed', case: 'none' },
  lead: { size: 'lg', weight: 400, tracking: 'normal', leading: 'relaxed', case: 'none' },
  eyebrow: { size: 'xs', weight: 700, tracking: 'wider', leading: 'normal', case: 'upper' },
  label: { size: 'xs', weight: 700, tracking: 'wider', leading: 'normal', case: 'upper' },
  price: { size: 'lg', weight: 700, tracking: 'normal', leading: 'normal', case: 'none' },
  nav: { size: 'sm', weight: 600, tracking: 'normal', leading: 'normal', case: 'none' },
  button: { size: 'sm', weight: 600, tracking: 'normal', leading: 'normal', case: 'none' },
  footer: { size: 'sm', weight: 400, tracking: 'normal', leading: 'relaxed', case: 'none' }
}
const roleSpec = (role) => theme.value.typography?.roles?.[role] || null
// El default del rol hereda la familia display/cuerpo del tema SOLO si está
// en el catálogo de roles; si no (p. ej. 'roboto' del selector general), cae
// a Inter — el backend rechaza fuentes fuera de las 24.
const defaultRoleFont = (role) => {
  const base = DISPLAY_ROLES.includes(role) ? (theme.value.typography?.heading || 'inter') : (theme.value.typography?.body || 'inter')
  return ROLE_FONT_SET.has(base) ? base : 'inter'
}
function writeRole(role, patch) {
  patchTheme((t) => {
    const ty = { ...(t.typography || {}) }
    const roles = { ...(ty.roles || {}) }
    roles[role] = { font: defaultRoleFont(role), ...ROLE_DEFAULTS[role], ...(roles[role] || {}), ...patch }
    ty.roles = roles
    t.typography = ty
  })
  const font = roleSpec(role)?.font
  if (font) ensureStoreFont(font)
}
function clearRole(role) {
  patchTheme((t) => {
    const ty = { ...(t.typography || {}) }
    const roles = { ...(ty.roles || {}) }
    delete roles[role]
    if (Object.keys(roles).length) ty.roles = roles
    else delete ty.roles
    if (Object.keys(ty).length) t.typography = ty
    else delete t.typography
  })
}
const FONT_GROUPS = [
  { label: 'Sans', keys: ['inter', 'manrope', 'figtree', 'dm-sans', 'space-grotesk', 'archivo', 'sora', 'work-sans', 'outfit', 'plus-jakarta-sans', 'nunito', 'raleway'] },
  { label: 'Serif', keys: ['playfair-display', 'fraunces', 'lora', 'cormorant-garamond', 'dm-serif-display', 'libre-baskerville', 'cinzel'] },
  { label: 'Display', keys: ['oswald', 'archivo-black', 'bebas-neue'] },
  { label: 'Mono', keys: ['space-mono', 'jetbrains-mono'] }
]
// Las 24 familias de arriba SON el catálogo cerrado del backend
// (FONT_SLUGS de ai_design_typography): un font fuera de él es 400.
const ROLE_FONT_SET = new Set(FONT_GROUPS.flatMap((g) => g.keys))
const fontLabel = (slug) => STORE_FONTS[slug]?.label || slug
const ROLE_SIZES = [
  ['xs', 'Extra chico'], ['sm', 'Chico'], ['md', 'Normal'], ['lg', 'Grande'],
  ['xl', 'Extra grande'], ['2xl', 'Enorme'], ['3xl', 'Gigante'], ['display', 'Display']
]
const ROLE_WEIGHTS = [300, 400, 500, 600, 700, 800, 900]
const ROLE_TRACKINGS = [
  ['tighter', 'Muy junto'], ['tight', 'Junto'], ['normal', 'Normal'], ['wide', 'Separado'], ['wider', 'Muy separado']
]
const ROLE_LEADINGS = [
  ['tight', 'Compacta'], ['snug', 'Corta'], ['normal', 'Normal'], ['relaxed', 'Holgada']
]
const ROLE_CASES = [['none', 'Normal'], ['upper', 'Mayúsculas']]
// Valor efectivo del control: el del spec propio o el default del rol.
const roleVal = (role, field) => roleSpec(role)?.[field] ?? ROLE_DEFAULTS[role][field] ?? (field === 'font' ? defaultRoleFont(role) : '')

// ===========================================================================
// 3. Fotos de producto (images — marco de .tpc-media)
// ===========================================================================
const IMG = computed(() => theme.value.images || {})
const RATIOS = [
  { id: 'square', label: '1:1', hint: 'Cuadrada' },
  { id: 'portrait', label: '4:5', hint: 'Vertical' },
  { id: 'tall', label: '3:4', hint: 'Más alta' },
  { id: 'wide', label: '16:10', hint: 'Apaisada' }
]
const FITS = [
  { id: 'cover', label: 'Llenar', hint: 'La foto cubre todo el marco (recorta lo que sobre).' },
  { id: 'contain', label: 'Completa', hint: 'La foto entera visible; el fondo del marco se ve detrás.' }
]
const RADII = [['none', 'Rectas'], ['sm', 'Suaves'], ['md', 'Redondas'], ['lg', 'Muy redondas']]
const BORDERS = [['none', 'Sin borde'], ['thin', 'Fino'], ['bold', 'Grueso']]
function setImg(key, value) { setKey('images', key, value) }

// ===========================================================================
// 4. Fondo de la web (background)
// ===========================================================================
const BG = computed(() => theme.value.background || {})
const BG_TYPES = [
  { id: 'solid', label: 'Sólido', icon: 'dot' },
  { id: 'gradient', label: 'Degradado', icon: 'paintbrush' },
  { id: 'mesh', label: 'Malla', icon: 'sparkles' },
  { id: 'pattern', label: 'Patrón', icon: 'layout-grid' },
  { id: 'image', label: 'Imagen', icon: 'image' }
]
const images = computed(() => {
  const out = []
  const cover = props.customization?.cover
  if (cover) out.push({ id: 'cover', url: cover, label: 'Portada' })
  ;(props.customization?.carousel || []).forEach((img, i) => {
    if (img?.url) out.push({ id: `car-${img.id ?? i}`, url: img.url, label: `Carrusel ${i + 1}` })
  })
  ;(props.customization?.gallery || []).forEach((img, i) => {
    if (img?.url) out.push({ id: `gal-${img.id ?? i}`, url: img.url, label: `Galería ${i + 1}` })
  })
  return out
})
const isStoreImage = (v) => images.value.some((i) => i.url === v)

function setBgType(id) {
  setKey('background', 'type', id)
  if (id === 'solid') setKey('background', 'value', null)
  else if (id === 'gradient') {
    const saved = parseGradient(BG.value.value)
    if (!saved) setKey('background', 'value', buildGradient([
      { color: pal.value.accent || '#4f46e5', pos: 0 },
      { color: pal.value.bg || '#eaeef8', pos: 100 }
    ], 135))
  } else if (id === 'mesh') {
    if (!BG.value.value) setKey('background', 'value', buildMesh('aurora', pal.value.accent, pal.value.bg))
  } else if (id === 'pattern') {
    if (!BG.value.value) setKey('background', 'value', buildPattern('dots', pal.value.text, pal.value.bg))
  } else if (id === 'image' && !isStoreImage(BG.value.value)) {
    setKey('background', 'value', images.value[0]?.url || null)
  }
}
// Sólido: el color de fondo es palette.bg (como en el Studio completo).
function setSolidBg(raw) { setColor('palette', 'bg', raw) }

// Degradado: dos paradas + ángulo (el valor viaja como CSS lineal). Los
// controles son refs locales sincronizados con el valor guardado — así el
// usuario puede mover un color sin que el otro se resetee a mitad de gesto.
const gradA = ref('')
const gradB = ref('')
const gradAngle = ref(135)
watch(() => BG.value.value, (v) => {
  const g = parseGradient(v)
  gradA.value = g?.stops[0]?.color || pal.value.accent || '#4f46e5'
  gradB.value = g?.stops[g.stops.length - 1]?.color || pal.value.bg || '#eaeef8'
  gradAngle.value = g?.angle ?? 135
}, { immediate: true })
function applyGradient() {
  const a = normalizeHex(gradA.value)
  const b = normalizeHex(gradB.value)
  if (a && b) setKey('background', 'value', buildGradient([{ color: a, pos: 0 }, { color: b, pos: 100 }], gradAngle.value))
}
function setGradA(raw) { const h = normalizeHex(raw); if (h) { gradA.value = h; applyGradient() } }
function setGradB(raw) { const h = normalizeHex(raw); if (h) { gradB.value = h; applyGradient() } }
function setGradAngle(e) {
  gradAngle.value = Number(e.target.value)
  applyGradient()
}

const meshes = computed(() => MESH_LOOKS.map((m) => ({ ...m, css: buildMesh(m.id, pal.value.accent, pal.value.bg) })))
const patterns = computed(() => PATTERN_LOOKS.map((p) => ({ ...p, css: buildPattern(p.id, pal.value.text, pal.value.bg) })))
function pickMesh(m) { setBgType('mesh'); setKey('background', 'value', m.css) }
function pickPattern(p) { setBgType('pattern'); setKey('background', 'value', p.css) }
function pickBgImage(i) { setBgType('image'); setKey('background', 'value', i.url) }
const OVERLAYS = [['none', 'Sin'], ['soft', 'Suave'], ['strong', 'Fuerte']]

function clearBackground() {
  patchTheme((t) => { delete t.background })
}

// ===========================================================================
// 5. Botones (buttons: style/shape/size/borderStyle)
// ===========================================================================
const BTNS = computed(() => theme.value.buttons || {})

// ===========================================================================
// Navegación del sidebar: acordeón de secciones + previews en vivo
// ===========================================================================
const SECTIONS = [
  { id: 'surfaces', icon: 'palette', tone: 'violet', title: 'Colores', sub: 'Superficies', desc: 'Colores propios para las superficies de la página. Lo que no toques hereda el look de tu diseño.' },
  { id: 'type', icon: 'type', tone: 'blue', title: 'Tipografía', sub: 'Fuentes por área', desc: 'Cada rol tiene su propia familia, tamaño, peso, interletraje, interlineado y caja. «Heredar» vuelve al estilo del diseño.' },
  { id: 'media', icon: 'image', tone: 'emerald', title: 'Fotos', sub: 'Marco de producto', desc: 'El marco de las fotos en las tarjetas: proporción, encaje, fondo detrás, esquinas y borde.' },
  { id: 'bg', icon: 'monitor', tone: 'amber', title: 'Fondo', sub: 'El fondo de la web', desc: 'Qué lleva el fondo detrás de todo: color, degradado, malla, patrón o una imagen tuya.' },
  { id: 'buttons', icon: 'sliders', tone: 'rose', title: 'Botones', sub: 'Estilo y forma', desc: 'Estilo, forma, tamaño y borde de todos los botones de la web.' }
]
const secMeta = (id) => SECTIONS.find((s) => s.id === id)
const openSection = ref('surfaces')
function toggleSection(id) { openSection.value = openSection.value === id ? null : id }
// Cuántos ajustes propios tiene cada sección — el numerito del encabezado.
const customCount = computed(() => ({
  surfaces: Object.keys(theme.value.surfaces || {}).length,
  type: Object.keys(theme.value.typography?.roles || {}).length,
  media: Object.keys(theme.value.images || {}).length,
  bg: theme.value.background ? 1 : 0,
  buttons: Object.keys(theme.value.buttons || {}).length
}))

// Muestra «Aa» de cada rol: refleja familia/tamaño/peso/tracking/caja al instante.
const ROLE_SAMPLE_SIZE = { xs: 10, sm: 11, md: 12, lg: 14, xl: 16, '2xl': 18, '3xl': 21, display: 24 }
const ROLE_SAMPLE_TRACK = { tighter: '-0.04em', tight: '-0.02em', normal: '0', wide: '0.05em', wider: '0.1em' }
function roleSampleStyle(role) {
  const font = roleVal(role, 'font')
  return {
    fontFamily: STORE_FONTS[font]?.family || 'inherit',
    fontSize: `${ROLE_SAMPLE_SIZE[roleVal(role, 'size')] || 12}px`,
    fontWeight: roleVal(role, 'weight') || 400,
    letterSpacing: ROLE_SAMPLE_TRACK[roleVal(role, 'tracking')] || '0',
    textTransform: roleVal(role, 'case') === 'upper' ? 'uppercase' : 'none'
  }
}

// Botón de muestra que refleja estilo/forma/tamaño/borde elegidos.
const accentColor = computed(() => normalizeHex(pal.value.accent) || '#4f46e5')
const btnSampleStyle = computed(() => {
  const b = BTNS.value
  const style = b.style || 'solid'
  const shape = b.shape || 'pill'
  const size = b.size || 'md'
  const bs = b.borderStyle || 'solid'
  const acc = accentColor.value
  const ink = inkOn(acc)
  const border = bs === 'none' ? 'none' : `1.5px ${bs} `
  const base = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    borderRadius: shape === 'pill' ? '999px' : shape === 'rounded' ? '12px' : '6px',
    padding: size === 'sm' ? '7px 14px' : size === 'lg' ? '13px 26px' : '10px 20px',
    fontSize: size === 'sm' ? '12.5px' : size === 'lg' ? '15.5px' : '14px',
    fontWeight: 650, letterSpacing: '.01em', whiteSpace: 'nowrap'
  }
  if (style === 'outline') return { ...base, background: 'transparent', color: acc, border: `${border}${acc}` }
  if (style === 'ghost') return { ...base, background: `color-mix(in srgb, ${acc} 12%, transparent)`, color: acc, border: `${border}color-mix(in srgb, ${acc} 35%, transparent)` }
  if (style === 'gradient') return { ...base, background: `linear-gradient(135deg, ${acc}, ${normalizeHex(pal.value.secondary) || acc})`, color: '#fff', border: `${border}rgba(255,255,255,.4)` }
  if (style === 'transparent') return { ...base, background: 'transparent', color: acc, border: `${border}${acc}` }
  return { ...base, background: acc, color: ink, border: `${border}${ink}` }
})

// Marco de foto simulado: proporción + fondo + esquinas + borde + encuadre.
const FRAME_RATIO = { square: '1 / 1', portrait: '4 / 5', tall: '3 / 4', wide: '16 / 10' }
const FRAME_RADIUS = { none: '0', sm: '6px', md: '12px', lg: '20px' }
const FRAME_BORDER = { thin: '1px', bold: '3px' }
const frameSampleStyle = computed(() => {
  const img = IMG.value
  return {
    aspectRatio: FRAME_RATIO[img.ratio] || '1 / 1',
    background: normalizeHex(img.bg) || 'var(--surface, #eef1f6)',
    borderRadius: FRAME_RADIUS[img.radius] || '10px',
    border: img.border && img.border !== 'none'
      ? `${FRAME_BORDER[img.border] || '1px'} solid var(--ink-3, #94a3b8)`
      : '1px dashed var(--line-strong, #cbd5e1)'
  }
})

const BTN_STYLES = [
  { id: 'solid', label: 'Sólido', hint: 'Relleno del color primario.' },
  { id: 'outline', label: 'Contorno', hint: 'Borde del color de acento, fondo transparente.' },
  { id: 'ghost', label: 'Suave', hint: 'Fondo tenue del acento, sin borde.' },
  { id: 'gradient', label: 'Degradado', hint: 'Del primario al secundario.' },
  { id: 'transparent', label: 'Transparente', hint: 'Casi invisible: el borde lo decidís abajo.' }
]
const BTN_SHAPES = [['square', 'Recto'], ['rounded', 'Redondeado'], ['pill', 'Píldora']]
const BTN_SIZES = [['sm', 'Chico'], ['md', 'Normal'], ['lg', 'Grande']]
const BTN_BORDERS = [
  { id: '', label: 'Heredar', hint: 'El borde que trae el estilo elegido.' },
  { id: 'none', label: 'Sin borde', hint: 'Quita el borde: botón de solo fondo o texto.' },
  { id: 'solid', label: 'Sólido', hint: 'Borde continuo marcado.' },
  { id: 'dashed', label: 'Punteado', hint: 'Borde de trazos.' },
  { id: 'dotted', label: 'Discontinuo', hint: 'Borde de puntos.' }
]
function setBtn(key, value) { setKey('buttons', key, value) }
</script>

<template>
  <div class="dstm" role="dialog" aria-modal="true" aria-label="Editor avanzado de tu web">
    <header class="dstm-bar">
      <div class="dstm-title">
        <span class="dstm-ico" aria-hidden="true"><AppIcon name="sliders" :size="17" /></span>
        <div>
          <strong>Editor Avanzado</strong>
          <small>Colores, fuentes, fotos, fondo y botones — se ve al instante en la vista previa.</small>
        </div>
      </div>
      <div class="dstm-actions"><slot name="actions" /></div>
      <button ref="closeBtn" type="button" class="dstm-x" aria-label="Cerrar el editor" @click="emit('close')">
        <AppIcon name="x" :size="18" />
      </button>
    </header>

    <div class="dstm-body">
      <aside class="dstm-side">
        <div class="dst-main">

      <!-- ===== 1. Colores de contenedores ===== -->
      <section class="dst-sec card" :class="{ 'is-open': openSection === 'surfaces' }">
        <h3 class="dst-sec-h">
          <button type="button" class="dst-sec-head" :aria-expanded="openSection === 'surfaces'" @click="toggleSection('surfaces')">
            <span class="dst-sec-ico" data-tone="violet" aria-hidden="true"><AppIcon name="palette" :size="16" /></span>
            <span class="dst-sec-tx"><strong>Colores</strong><small>Superficies de la página</small></span>
            <span v-if="customCount.surfaces" class="dst-sec-n" :title="`${customCount.surfaces} ajuste(s) propio(s)`">{{ customCount.surfaces }}</span>
            <AppIcon name="chevron-down" :size="15" class="dst-sec-chev" aria-hidden="true" />
          </button>
        </h3>
        <div class="dst-sec-body">
          <div class="dst-sec-inner">
            <p class="dst-sec-desc">Colores propios para las superficies de la página. Lo que no toques hereda el look de tu diseño.</p>
            <div class="stp-fields">
          <div v-for="s in SURFACES" :key="s.key" class="stp-role" :title="s.hint">
            <span class="dst-surf-lb">
              <span class="dst-surf-chip" :class="{ 'is-inherit': !surfaceColor(s.key) }" :style="surfaceColor(s.key) ? { background: surfaceColor(s.key) } : null" aria-hidden="true"></span>
              {{ s.label }}
            </span>
            <input
              type="color" class="stp-swatch" :value="normalizeHex(surfaceColor(s.key)) || '#ffffff'"
              :aria-label="`${s.label}: selector de color`"
              @input="setSurface(s.key, $event.target.value)"
            />
            <input
              type="text" class="stp-hex" :value="surfaceColor(s.key)" maxlength="7" spellcheck="false"
              :placeholder="s.key === 'card' ? '#ffffff' : 'Heredar'"
              :aria-label="`${s.label} en hexadecimal`"
              @change="surfaceText(s.key, $event)" @keydown.enter.prevent="surfaceText(s.key, $event)"
            />
            <button
              v-if="surfaceColor(s.key)" type="button" class="btn ghost btn-auto dst-reset"
              :aria-label="`Quitar color de ${s.label}`" @click="clearSurface(s.key)"
            ><AppIcon name="x" :size="13" aria-hidden="true" /> Heredar</button>
          </div>
          <p class="stp-fhint">El texto dentro de cada superficie se ajusta solo para seguir leyéndose (contraste AA).</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 2. Fuentes por área ===== -->
      <section class="dst-sec card" :class="{ 'is-open': openSection === 'type' }">
        <h3 class="dst-sec-h">
          <button type="button" class="dst-sec-head" :aria-expanded="openSection === 'type'" @click="toggleSection('type')">
            <span class="dst-sec-ico" data-tone="blue" aria-hidden="true"><AppIcon name="type" :size="16" /></span>
            <span class="dst-sec-tx"><strong>Tipografía</strong><small>Fuentes por área</small></span>
            <span v-if="customCount.type" class="dst-sec-n" :title="`${customCount.type} ajuste(s) propio(s)`">{{ customCount.type }}</span>
            <AppIcon name="chevron-down" :size="15" class="dst-sec-chev" aria-hidden="true" />
          </button>
        </h3>
        <div class="dst-sec-body">
          <div class="dst-sec-inner">
            <p class="dst-sec-desc">Cada rol tiene su propia familia, tamaño, peso, interletraje, interlineado y caja. «Heredar» vuelve al estilo del diseño.</p>
            <div class="stp-fields">
          <div v-for="g in ROLE_GROUPS" :key="g" class="stp-role-group">
            <span class="stp-role-group-lb">{{ g }}</span>
            <div v-for="r in rowsOf(g)" :key="r.role" class="dst-role">
              <div class="dst-role-top">
                <span class="dst-role-name">{{ r.label }} <em v-if="roleSpec(r.role)" class="dst-badge">Propio</em></span>
                <span class="dst-role-act">
                  <span class="dst-role-sample" :style="roleSampleStyle(r.role)" aria-hidden="true">Aa</span>
                  <button
                    v-if="roleSpec(r.role)" type="button" class="dst-reset-btn"
                    :aria-label="`Heredar la fuente de ${r.label}`" @click="clearRole(r.role)"
                  >Heredar</button>
                </span>
              </div>
              <div class="dst-role-grid">
                <label class="dst-f">
                  <span>Familia</span>
                  <select
                    class="dst-select" :value="roleVal(r.role, 'font')"
                    :aria-label="`${r.label}: familia tipográfica`"
                    @change="writeRole(r.role, { font: $event.target.value })"
                  >
                    <optgroup v-for="fg in FONT_GROUPS" :key="fg.label" :label="fg.label">
                      <option v-for="k in fg.keys" :key="k" :value="k">{{ fontLabel(k) }}</option>
                    </optgroup>
                  </select>
                </label>
                <label class="dst-f">
                  <span>Tamaño</span>
                  <select
                    class="dst-select" :value="roleVal(r.role, 'size')"
                    :aria-label="`${r.label}: tamaño`"
                    @change="writeRole(r.role, { size: $event.target.value })"
                  >
                    <option v-for="[id, lb] in ROLE_SIZES" :key="id" :value="id">{{ lb }}</option>
                  </select>
                </label>
                <details class="dst-role-more">
                  <summary>Detalles</summary>
                  <div class="dst-role-extra">
                    <label class="dst-f">
                      <span>Peso</span>
                      <select class="dst-select" :value="roleVal(r.role, 'weight')" :aria-label="`${r.label}: peso`" @change="writeRole(r.role, { weight: Number($event.target.value) })">
                        <option v-for="w in ROLE_WEIGHTS" :key="w" :value="w">{{ w }}</option>
                      </select>
                    </label>
                    <label class="dst-f">
                      <span>Interletraje</span>
                      <select class="dst-select" :value="roleVal(r.role, 'tracking')" :aria-label="`${r.label}: interletraje`" @change="writeRole(r.role, { tracking: $event.target.value })">
                        <option v-for="[id, lb] in ROLE_TRACKINGS" :key="id" :value="id">{{ lb }}</option>
                      </select>
                    </label>
                    <label class="dst-f">
                      <span>Interlineado</span>
                      <select class="dst-select" :value="roleVal(r.role, 'leading')" :aria-label="`${r.label}: interlineado`" @change="writeRole(r.role, { leading: $event.target.value })">
                        <option v-for="[id, lb] in ROLE_LEADINGS" :key="id" :value="id">{{ lb }}</option>
                      </select>
                    </label>
                    <label class="dst-f">
                      <span>Caja</span>
                      <select class="dst-select" :value="roleVal(r.role, 'case')" :aria-label="`${r.label}: caja`" @change="writeRole(r.role, { case: $event.target.value })">
                        <option v-for="[id, lb] in ROLE_CASES" :key="id" :value="id">{{ lb }}</option>
                      </select>
                    </label>
                  </div>
                </details>
              </div>
            </div>
          </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 3. Fotos de producto ===== -->
      <section class="dst-sec card" :class="{ 'is-open': openSection === 'media' }">
        <h3 class="dst-sec-h">
          <button type="button" class="dst-sec-head" :aria-expanded="openSection === 'media'" @click="toggleSection('media')">
            <span class="dst-sec-ico" data-tone="emerald" aria-hidden="true"><AppIcon name="image" :size="16" /></span>
            <span class="dst-sec-tx"><strong>Fotos</strong><small>Marco de producto</small></span>
            <span v-if="customCount.media" class="dst-sec-n" :title="`${customCount.media} ajuste(s) propio(s)`">{{ customCount.media }}</span>
            <AppIcon name="chevron-down" :size="15" class="dst-sec-chev" aria-hidden="true" />
          </button>
        </h3>
        <div class="dst-sec-body">
          <div class="dst-sec-inner">
            <p class="dst-sec-desc">El marco de las fotos en las tarjetas: proporción, encuadre, fondo detrás, esquinas y borde.</p>
            <div class="dst-frame-preview">
              <span class="dst-frame" :style="frameSampleStyle" aria-hidden="true">
                <span class="dst-frame-photo" :class="{ 'is-contain': IMG.fit === 'contain' }"><AppIcon name="image" :size="20" /></span>
              </span>
              <span class="dst-frame-lb">Vista previa del marco</span>
            </div>
            <div class="stp-fields">
          <div>
            <span class="stp-role-lb">Proporción</span>
            <div class="dst-ratios" role="group" aria-label="Proporción del marco de foto">
              <button
                v-for="r in RATIOS" :key="r.id" type="button" class="dst-ratio"
                :class="{ active: IMG.ratio === r.id, inherit: !IMG.ratio && r.id === 'square' }"
                :aria-pressed="IMG.ratio === r.id" :title="r.hint"
                @click="setImg('ratio', r.id)"
              >
                <span class="dst-ratio-box" :style="{ aspectRatio: r.id === 'square' ? '1 / 1' : r.id === 'portrait' ? '4 / 5' : r.id === 'tall' ? '3 / 4' : '16 / 10' }"></span>
                <span class="dst-ratio-lb">{{ r.label }}</span>
              </button>
              <button
                v-if="IMG.ratio" type="button" class="dst-ratio dst-ratio-inherit"
                aria-label="Heredar la proporción del diseño" @click="setImg('ratio', null)"
              ><span class="dst-ratio-lb">Heredar</span></button>
            </div>
          </div>
          <div>
            <span class="stp-role-lb">Encuadre</span>
            <div class="stp-seg" role="group" aria-label="Encuadre de la foto">
              <button
                v-for="f in FITS" :key="f.id" type="button" class="stp-opt"
                :class="{ active: IMG.fit === f.id }" :aria-pressed="IMG.fit === f.id"
                :title="f.hint" @click="setImg('fit', f.id)"
              >{{ f.label }}</button>
              <button
                v-if="IMG.fit" type="button" class="stp-opt" aria-label="Heredar el encuadre"
                @click="setImg('fit', null)"
              >Heredar</button>
            </div>
          </div>
          <div class="stp-role">
            <span class="stp-role-lb">Fondo del marco</span>
            <input
              type="color" class="stp-swatch" :value="normalizeHex(IMG.bg) || '#eaeef8'"
              aria-label="Color detrás de la foto" @input="setImg('bg', normalizeHex($event.target.value))"
            />
            <input
              type="text" class="stp-hex" :value="IMG.bg || ''" maxlength="7" spellcheck="false"
              placeholder="Heredar" aria-label="Color detrás de la foto en hexadecimal"
              @change="colorText('images', 'bg', $event)" @keydown.enter.prevent="colorText('images', 'bg', $event)"
            />
            <button
              v-if="IMG.bg" type="button" class="btn ghost btn-auto dst-reset"
              aria-label="Quitar el fondo del marco" @click="setImg('bg', null)"
            ><AppIcon name="x" :size="13" aria-hidden="true" /> Heredar</button>
          </div>
          <div class="dst-2col">
            <label class="dst-f">
              <span>Esquinas</span>
              <select class="dst-select" :value="IMG.radius || ''" aria-label="Radio de las esquinas de la foto" @change="setImg('radius', $event.target.value || null)">
                <option value="">Heredar</option>
                <option v-for="[id, lb] in RADII" :key="id" :value="id">{{ lb }}</option>
              </select>
            </label>
            <label class="dst-f">
              <span>Borde</span>
              <select class="dst-select" :value="IMG.border || ''" aria-label="Borde del marco de la foto" @change="setImg('border', $event.target.value || null)">
                <option value="">Heredar</option>
                <option v-for="[id, lb] in BORDERS" :key="id" :value="id">{{ lb }}</option>
              </select>
            </label>
          </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 4. Fondo de la web ===== -->
      <section class="dst-sec card" :class="{ 'is-open': openSection === 'bg' }">
        <h3 class="dst-sec-h">
          <button type="button" class="dst-sec-head" :aria-expanded="openSection === 'bg'" @click="toggleSection('bg')">
            <span class="dst-sec-ico" data-tone="amber" aria-hidden="true"><AppIcon name="monitor" :size="16" /></span>
            <span class="dst-sec-tx"><strong>Fondo</strong><small>El fondo de la web</small></span>
            <span v-if="customCount.bg" class="dst-sec-n" :title="`${customCount.bg} ajuste(s) propio(s)`">{{ customCount.bg }}</span>
            <AppIcon name="chevron-down" :size="15" class="dst-sec-chev" aria-hidden="true" />
          </button>
        </h3>
        <div class="dst-sec-body">
          <div class="dst-sec-inner">
            <p class="dst-sec-desc">Qué lleva el fondo detrás de todo: color, degradado, malla, patrón o una imagen tuya.</p>
            <div class="stp-fields">
          <div class="stp-seg dst-bgtypes" role="group" aria-label="Tipo de fondo">
            <button
              v-for="t in BG_TYPES" :key="t.id" type="button" class="stp-opt"
              :class="{ active: (BG.type || 'solid') === t.id }" :aria-pressed="(BG.type || 'solid') === t.id"
              @click="setBgType(t.id)"
            ><AppIcon :name="t.icon" :size="14" aria-hidden="true" /> {{ t.label }}</button>
          </div>

          <template v-if="(BG.type || 'solid') === 'solid'">
            <div class="stp-role">
              <span class="stp-role-lb">Color de fondo</span>
              <input
                type="color" class="stp-swatch" :value="normalizeHex(pal.bg) || '#eaeef8'"
                aria-label="Color sólido del fondo" @input="setSolidBg($event.target.value)"
              />
              <input
                type="text" class="stp-hex" :value="pal.bg || ''" maxlength="7" spellcheck="false"
                aria-label="Color sólido del fondo en hexadecimal"
                @change="colorText('palette', 'bg', $event)" @keydown.enter.prevent="colorText('palette', 'bg', $event)"
              />
            </div>
            <p class="stp-fhint">El fondo sólido usa el color de página de tu paleta (Diseño → Colores del Studio completo).</p>
          </template>

          <template v-else-if="BG.type === 'gradient'">
            <div class="dst-2col">
              <label class="dst-f">
                <span>Desde</span>
                <input type="color" class="stp-swatch dst-swatch" :value="normalizeHex(gradA) || '#4f46e5'" aria-label="Color inicial del degradado" @input="setGradA($event.target.value)" />
              </label>
              <label class="dst-f">
                <span>Hasta</span>
                <input type="color" class="stp-swatch dst-swatch" :value="normalizeHex(gradB) || '#eaeef8'" aria-label="Color final del degradado" @input="setGradB($event.target.value)" />
              </label>
            </div>
            <label class="stp-angle">
              <span class="stp-role-lb">Ángulo <b class="stp-val">{{ gradAngle }}°</b></span>
              <input type="range" class="stp-range" min="0" max="360" :value="gradAngle" aria-label="Ángulo del degradado" @input="setGradAngle" />
            </label>
          </template>

          <template v-else-if="BG.type === 'mesh'">
            <div class="dst-minis" role="group" aria-label="Mallas de fondo">
              <button
                v-for="m in meshes" :key="m.id" type="button" class="dst-mini"
                :class="{ active: BG.value === m.css }" :aria-pressed="BG.value === m.css"
                :title="m.label" @click="pickMesh(m)"
              ><span class="dst-mini-art" :style="{ background: m.css }" aria-hidden="true"></span><span class="dst-mini-lb">{{ m.label }}</span></button>
            </div>
          </template>

          <template v-else-if="BG.type === 'pattern'">
            <div class="dst-minis" role="group" aria-label="Patrones de fondo">
              <button
                v-for="p in patterns" :key="p.id" type="button" class="dst-mini"
                :class="{ active: BG.value === p.css }" :aria-pressed="BG.value === p.css"
                :title="p.label" @click="pickPattern(p)"
              ><span class="dst-mini-art" :style="{ background: p.css }" aria-hidden="true"></span><span class="dst-mini-lb">{{ p.label }}</span></button>
            </div>
          </template>

          <template v-else-if="BG.type === 'image'">
            <div v-if="images.length" class="stp-imgs" role="group" aria-label="Imágenes de tu tienda">
              <button
                v-for="i in images" :key="i.id" type="button" class="stp-img"
                :class="{ active: BG.value === i.url }" :aria-pressed="BG.value === i.url"
                @click="pickBgImage(i)"
              ><img :src="i.url" :alt="i.label" loading="lazy" /><span class="stp-img-lb">{{ i.label }}</span></button>
            </div>
            <p v-else class="stp-fhint">Todavía no subiste imágenes: cargá tu portada o fotos en Diseño → Fotos.</p>
          </template>

          <div class="stp-seg" role="group" aria-label="Velo sobre el fondo">
            <button
              v-for="[id, lb] in OVERLAYS" :key="id" type="button" class="stp-opt"
              :class="{ active: (BG.overlay || 'none') === id }" :aria-pressed="(BG.overlay || 'none') === id"
              @click="setKey('background', 'overlay', id === 'none' ? null : id)"
            >Velo {{ lb.toLowerCase() }}</button>
          </div>

          <button type="button" class="btn ghost btn-auto" @click="clearBackground">
            <AppIcon name="refresh" :size="14" aria-hidden="true" /> Quitar fondo personalizado
          </button>
            </div>
          </div>
        </div>
      </section>

      <!-- ===== 5. Botones ===== -->
      <section class="dst-sec card" :class="{ 'is-open': openSection === 'buttons' }">
        <h3 class="dst-sec-h">
          <button type="button" class="dst-sec-head" :aria-expanded="openSection === 'buttons'" @click="toggleSection('buttons')">
            <span class="dst-sec-ico" data-tone="rose" aria-hidden="true"><AppIcon name="sliders" :size="16" /></span>
            <span class="dst-sec-tx"><strong>Botones</strong><small>Estilo y forma</small></span>
            <span v-if="customCount.buttons" class="dst-sec-n" :title="`${customCount.buttons} ajuste(s) propio(s)`">{{ customCount.buttons }}</span>
            <AppIcon name="chevron-down" :size="15" class="dst-sec-chev" aria-hidden="true" />
          </button>
        </h3>
        <div class="dst-sec-body">
          <div class="dst-sec-inner">
            <p class="dst-sec-desc">Estilo, forma, tamaño y borde de todos los botones de la web.</p>
            <div class="dst-btn-preview">
              <span class="dst-btn-sample" :style="btnSampleStyle">Comprar ahora</span>
              <span class="dst-btn-preview-lb">Vista previa del estilo elegido</span>
            </div>
            <div class="stp-fields">
          <div>
            <span class="stp-role-lb">Estilo</span>
            <div class="stp-minis wide" role="group" aria-label="Estilo de botón">
              <button
                v-for="b in BTN_STYLES" :key="b.id" type="button" class="stp-mini"
                :class="{ active: (BTNS.style || 'solid') === b.id }" :aria-pressed="(BTNS.style || 'solid') === b.id"
                :title="b.hint" @click="setBtn('style', b.id)"
              >
                <span class="dst-mini-art dst-btn-art" :data-style="b.id" aria-hidden="true"></span>
                <span class="stp-mini-lb">{{ b.label }}</span>
              </button>
            </div>
          </div>
          <div class="dst-2col">
            <label class="dst-f">
              <span>Forma</span>
              <select class="dst-select" :value="BTNS.shape || 'pill'" aria-label="Forma de los botones" @change="setBtn('shape', $event.target.value)">
                <option v-for="[id, lb] in BTN_SHAPES" :key="id" :value="id">{{ lb }}</option>
              </select>
            </label>
            <label class="dst-f">
              <span>Tamaño</span>
              <select class="dst-select" :value="BTNS.size || 'md'" aria-label="Tamaño de los botones" @change="setBtn('size', $event.target.value)">
                <option v-for="[id, lb] in BTN_SIZES" :key="id" :value="id">{{ lb }}</option>
              </select>
            </label>
          </div>
          <div>
            <span class="stp-role-lb">Borde</span>
            <div class="stp-seg dst-borders" role="group" aria-label="Estilo de borde de los botones">
              <button
                v-for="b in BTN_BORDERS" :key="b.id || 'inherit'" type="button" class="stp-opt"
                :class="{ active: (BTNS.borderStyle || '') === b.id }" :aria-pressed="(BTNS.borderStyle || '') === b.id"
                :title="b.hint" @click="setBtn('borderStyle', b.id || null)"
              >{{ b.label }}</button>
            </div>
            <p class="stp-fhint">Punteado y discontinuo se ven mejor sobre Contorno o Transparente; sobre Sólido el borde toma el color del texto del botón.</p>
          </div>
            </div>
          </div>
        </div>
      </section>
        </div>
      </aside>

      <div class="dstm-stage">
        <DesignLivePreview :form="form" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Modal fullscreen del Editor Avanzado: barra con acciones + X, sidebar
   izquierdo con las secciones del editor y la vista previa al centro. */
.dstm { position: fixed; inset: 0; z-index: 160; display: flex; flex-direction: column; background: var(--bg, #eef1f6); }
.dstm-bar {
  flex: none; display: flex; align-items: center; gap: 12px;
  padding: 10px 16px; border-bottom: 1px solid var(--line, #e5e7eb); background: var(--card, #fff);
}
.dstm-title { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1 1 auto; }
.dstm-ico {
  display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; flex: none;
  border-radius: 10px; background: var(--brand-soft, #eef2ff); color: var(--brand-600, #4f46e5);
}
.dstm-title strong { font-size: 14.5px; letter-spacing: -.01em; }
.dstm-title small { font-size: 11.5px; color: var(--muted); }
.dstm-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
.dstm-x {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border: 1px solid var(--line, #e5e7eb); border-radius: 10px;
  background: var(--card, #fff); color: var(--ink-2, #334155); cursor: pointer;
}
.dstm-x:hover { border-color: var(--line-strong, #cbd5e1); background: var(--surface, #f8fafc); }
.dstm-body { flex: 1 1 auto; min-height: 0; display: grid; grid-template-columns: minmax(300px, 360px) minmax(0, 1fr); }
.dstm-side { overflow-y: auto; padding: 14px; border-right: 1px solid var(--line, #e5e7eb); background: var(--surface, #f8fafc); min-width: 0; }
.dstm-side .dst-main { padding-bottom: 6px; }
.dstm-stage { min-width: 0; overflow: auto; padding: 20px; display: flex; }
.dstm-stage > * { margin: auto; width: 100%; max-width: 1180px; }
.dst-main { display: flex; flex-direction: column; gap: 10px; min-width: 0; }

/* ===== Acordeón de secciones ===== */
.dst-sec { padding: 0; overflow: hidden; }
.dst-sec-h { margin: 0; }
.dst-sec-head {
  display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 11px 14px; border: 0; background: none; cursor: pointer;
  font: inherit; text-align: left;
}
.dst-sec-head:hover { background: var(--surface, #f8fafc); }
.dst-sec-ico {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; flex: none; border-radius: 9px;
}
.dst-sec-ico[data-tone='violet'] { background: #f3e8ff; color: #7c3aed; }
.dst-sec-ico[data-tone='blue'] { background: #dbeafe; color: #2563eb; }
.dst-sec-ico[data-tone='emerald'] { background: #d1fae5; color: #059669; }
.dst-sec-ico[data-tone='amber'] { background: #fef3c7; color: #b45309; }
.dst-sec-ico[data-tone='rose'] { background: #ffe4e6; color: #e11d48; }
.dst-sec-tx { display: grid; gap: 1px; min-width: 0; flex: 1 1 auto; }
.dst-sec-tx strong { font-size: 13px; font-weight: 700; color: var(--ink, #0f172a); }
.dst-sec-tx small { font-size: 11px; color: var(--muted); }
.dst-sec-n {
  flex: none; min-width: 20px; height: 20px; padding: 0 6px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 99px; background: var(--brand-500, #4f46e5); color: #fff;
  font-size: 10.5px; font-weight: 700;
}
.dst-sec-chev { flex: none; color: var(--muted); transition: transform .22s ease; }
.dst-sec.is-open .dst-sec-chev { transform: rotate(180deg); }
.dst-sec-desc { margin: 0; padding: 0 16px 10px; font-size: 11.5px; color: var(--muted); line-height: 1.45; }
.dst-sec-body {
  display: grid; grid-template-rows: 0fr; visibility: hidden;
  transition: grid-template-rows .26s ease, visibility 0s .26s;
}
.dst-sec.is-open .dst-sec-body {
  grid-template-rows: 1fr; visibility: visible;
  transition: grid-template-rows .26s ease, visibility 0s;
}
.dst-sec-inner { overflow: hidden; min-height: 0; padding-bottom: 14px; }
.dst-sec-inner > .stp-fields { padding: 0 16px; }

/* ===== Chips de color por superficie ===== */
.dst-surf-lb {
  flex: 0 0 96px; display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600; color: var(--ink-2); min-width: 0;
}
.dst-surf-chip {
  width: 15px; height: 15px; flex: none; border-radius: 5px;
  border: 1px solid var(--line-strong, #cbd5e1);
}
.dst-surf-chip.is-inherit {
  background: repeating-linear-gradient(45deg, var(--surface, #f8fafc) 0 3px, var(--line, #e5e7eb) 3px 6px);
}

/* ===== Muestra tipográfica «Aa» ===== */
.dst-role-act { display: inline-flex; align-items: center; gap: 6px; }
.dst-role-sample {
  min-width: 32px; padding: 3px 9px; border-radius: 7px; text-align: center;
  background: var(--surface, #f8fafc); border: 1px solid var(--line, #e5e7eb);
  color: var(--ink, #0f172a); line-height: 1.25;
}

/* ===== Previews de marco de foto y botón ===== */
.dst-frame-preview, .dst-btn-preview {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 12px; border: 1px dashed var(--line, #e5e7eb); border-radius: 12px;
  background: var(--surface, #f8fafc); margin-bottom: 12px;
}
.dst-frame { display: block; width: 74px; position: relative; overflow: hidden; }
.dst-frame-photo {
  position: absolute; inset: 0; display: grid; place-items: center;
  background: linear-gradient(135deg, #cbd5e1, #94a3b8); color: #fff;
}
.dst-frame-photo.is-contain { inset: 14%; border: 1px solid rgba(255, 255, 255, .55); border-radius: 4px; }
.dst-frame-lb, .dst-btn-preview-lb { font-size: 10.5px; font-weight: 600; color: var(--muted); }
.dst-btn-preview { flex-direction: row; gap: 14px; }
.dst-btn-sample { user-select: none; }
.dst-reset { min-height: 32px; padding: 4px 10px; font-size: 11.5px; }
.dst-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.dst-f { display: grid; gap: 4px; min-width: 0; }
.dst-f > span { font-size: 11px; font-weight: 600; color: var(--muted); }
.dst-select {
  width: 100%; min-height: 38px; padding: 6px 10px; border: 1px solid var(--line, #e5e7eb);
  border-radius: 10px; background: var(--card, #fff); color: var(--ink, #0f172a);
  font: inherit; font-size: 12.5px; font-weight: 600;
}
.dst-swatch { width: 44px; height: 38px; }
.dst-ratios { display: flex; flex-wrap: wrap; gap: 6px; }
.dst-ratio {
  display: grid; justify-items: center; gap: 4px; padding: 8px 10px; min-height: 44px;
  border: 1px solid var(--line, #e5e7eb); border-radius: 12px; background: var(--card, #fff);
  cursor: pointer; font: inherit;
}
.dst-ratio:hover { border-color: var(--line-strong, #cbd5e1); }
.dst-ratio.active { border-color: var(--brand-500, #4f46e5); box-shadow: 0 0 0 1px var(--brand-500, #4f46e5); background: var(--brand-soft, #eef2ff); }
.dst-ratio-box { width: 26px; max-height: 30px; border: 1.5px solid var(--ink-2, #334155); border-radius: 4px; background: var(--surface, #f8fafc); }
.dst-ratio-lb { font-size: 11px; font-weight: 700; color: var(--ink-2, #334155); }
.dst-role { display: grid; gap: 6px; padding: 8px 0; border-top: 1px dashed var(--line, #e5e7eb); }
.dst-role:first-child { border-top: 0; padding-top: 2px; }
.dst-role-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.dst-role-name { font-size: 12.5px; font-weight: 700; color: var(--ink, #0f172a); }
.dst-role-name em { font-style: normal; font-size: 10px; font-weight: 700; color: var(--brand-600, #4f46e5); background: var(--brand-soft, #eef2ff); border-radius: 99px; padding: 1px 7px; margin-left: 4px; vertical-align: 1px; }
.dst-reset-btn { border: 0; background: none; color: var(--muted); font: inherit; font-size: 11px; font-weight: 600; cursor: pointer; padding: 4px 6px; border-radius: 6px; }
.dst-reset-btn:hover { color: var(--brand-600, #4f46e5); background: var(--surface, #f8fafc); }
.dst-role-grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) auto; gap: 8px; align-items: end; }
.dst-role-more { font-size: 11px; }
.dst-role-more summary { cursor: pointer; color: var(--muted); font-weight: 600; padding: 6px 2px; min-height: 32px; display: inline-flex; align-items: center; }
.dst-role-more summary:hover { color: var(--ink, #0f172a); }
.dst-role-extra { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; padding: 4px 0 8px; }
.dst-minis { display: grid; grid-template-columns: repeat(auto-fill, minmax(76px, 1fr)); gap: 6px; }
.dst-mini { display: grid; justify-items: center; gap: 4px; padding: 8px 6px; border: 1px solid var(--line, #e5e7eb); border-radius: 12px; background: var(--card, #fff); cursor: pointer; font: inherit; }
.dst-mini:hover { border-color: var(--line-strong, #cbd5e1); }
.dst-mini.active { border-color: var(--brand-500, #4f46e5); box-shadow: 0 0 0 1px var(--brand-500, #4f46e5); background: var(--brand-soft, #eef2ff); }
.dst-mini-art { width: 100%; height: 34px; border-radius: 7px; border: 1px solid var(--line, #e5e7eb); }
.dst-mini-lb { font-size: 10.5px; font-weight: 600; color: var(--ink-2, #334155); text-align: center; }
.dst-btn-art { display: grid; place-items: center; }
.dst-btn-art::after { content: ''; width: 34px; height: 15px; border-radius: 99px; }
.dst-btn-art[data-style='solid']::after { background: var(--brand-500, #4f46e5); }
.dst-btn-art[data-style='outline']::after { background: transparent; border: 1.5px solid var(--brand-500, #4f46e5); }
.dst-btn-art[data-style='ghost']::after { background: color-mix(in srgb, var(--brand-500, #4f46e5) 14%, transparent); }
.dst-btn-art[data-style='gradient']::after { background: linear-gradient(90deg, var(--brand-500, #4f46e5), var(--brand-700, #3730a3)); }
.dst-btn-art[data-style='transparent']::after { background: color-mix(in srgb, var(--brand-500, #4f46e5) 8%, transparent); border: 1.5px dashed var(--brand-500, #4f46e5); }
.dst-bgtypes { flex-wrap: wrap; }
@media (max-width: 900px) {
  .dstm-body { grid-template-columns: 1fr; grid-template-rows: auto minmax(0, 1fr); }
  .dstm-side { max-height: 42vh; border-right: 0; border-bottom: 1px solid var(--line, #e5e7eb); }
  .dstm-stage { padding: 12px; }
}
</style>
