<script setup>
// Paneles por defecto del Studio (uno por herramienta del riel).
// Los controles escriben DOS capas según corresponda:
//  - `form` (customization real: template, theme, name_font, accent_custom)
//    -> persiste hoy por la API existente.
//  - `theme` (siteTheme del contrato) -> viaja a la vista previa por
//    studio:update y al payload site_theme (campo futuro del backend).
// Cada campo lleva data-focus con el target del contrato: el shell lo usa
// para el anillo animado en la vista previa y para enfocar el control
// cuando el usuario clickea el elemento correspondiente en el iframe.
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import DesignLookTab from '../design/DesignLookTab.vue'
import { STORE_FONT_GROUPS, STORE_FONTS, ensureStoreFont } from '../../api/stores.api.js'
import { deriveAccent } from '../../utils/colorTools.js'
import { normalizeHex } from '../../studio/contract.js'
import { SURFACE_LABELS } from './studioModel.js'

const props = defineProps({
  tool: { type: String, required: true },
  form: { type: Object, required: true },
  theme: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  siteTemplates: { type: Array, default: () => [] },
  layout: { type: Object, default: null },
  canFlyers: { type: Boolean, default: false },
  shopName: { type: String, default: '' }
})
const emit = defineEmits(['navigate', 'ring'])

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))

// --- Opciones de los controles segmentados (enums del contrato) ---
const SEG = {
  scale:      [['compact', 'Compacta'], ['balanced', 'Balanceada'], ['editorial', 'Editorial']],
  radius:     [['none', 'Ninguno'], ['sm', 'Suave'], ['md', 'Medio'], ['lg', 'Amplio'], ['xl', 'XL'], ['pill', 'Píldora']],
  shadow:     [['none', 'Sin'], ['soft', 'Suave'], ['medium', 'Media'], ['deep', 'Profunda']],
  border:     [['none', 'Sin'], ['thin', 'Fino'], ['bold', 'Marcado']],
  density:    [['compact', 'Compacta'], ['comfortable', 'Cómoda'], ['spacious', 'Amplia']],
  surface:    [['flat', 'Plana'], ['glass', 'Vidrio'], ['elevated', 'Elevada'], ['outlined', 'Contorno']],
  btnShape:   [['square', 'Recto'], ['rounded', 'Redondeado'], ['pill', 'Píldora']],
  btnStyle:   [['solid', 'Sólido'], ['outline', 'Contorno'], ['ghost', 'Fantasma'], ['gradient', 'Gradiente']],
  btnSize:    [['sm', 'Chico'], ['md', 'Medio'], ['lg', 'Grande']],
  reveal:     [['none', 'Sin'], ['fade', 'Fundido'], ['rise', 'Ascenso'], ['stagger', 'Cascada']],
  hover:      [['none', 'Sin'], ['lift', 'Elevación'], ['glow', 'Brillo']],
  intensity:  [['subtle', 'Sutil'], ['medium', 'Media'], ['bold', 'Marcada']],
  nav:        [['top', 'Barra arriba'], ['bottom', 'Barra abajo'], ['drawer', 'Menú lateral']],
  cardStyle:  [['standard', 'Estándar'], ['compact', 'Compacta'], ['overlay', 'Imagen']],
  heroHeight: [['compact', 'Compacta'], ['tall', 'Amplia']],
  gridCols:   [[1, '1 columna'], [2, '2 columnas']],
  pageTheme:  [['light', 'Claro', 'sun'], ['dark', 'Oscuro', 'moon']]
}
const TRACKING = [['-0.04em', 'Ajustada'], ['-0.02em', 'Actual'], ['0em', 'Normal'], ['0.03em', 'Amplia']]

// --- Colores (siteTheme.palette) ---
const PALETTE_FIELDS = [
  { key: 'accent',    label: 'Acento',            hint: 'Botones, links y detalles de marca.', focus: 'buttons', persist: true },
  { key: 'bg',        label: 'Fondo de página',   hint: 'El lienzo detrás de todo.', focus: 'page' },
  { key: 'surface',   label: 'Tarjetas',          hint: 'Fondo de tarjetas y paneles.', focus: 'card' },
  { key: 'text',      label: 'Texto',             hint: 'Títulos y párrafos.', focus: 'typo' },
  { key: 'muted',     label: 'Texto suave',       hint: 'Descripciones y datos secundarios.', focus: 'typo' },
  { key: 'border',    label: 'Bordes y líneas',   hint: 'Contornos de tarjetas y campos.', focus: 'card' },
  { key: 'success',   label: 'Éxito',             hint: 'Confirmaciones y estados OK.', focus: 'page' },
  { key: 'danger',    label: 'Error',             hint: 'Avisos y errores.', focus: 'page' }
]

function setPalette(key, value) {
  const hex = normalizeHex(value)
  if (!hex) return
  props.theme.palette[key] = hex
  if (key === 'accent') {
    // El triplete va en la misma mutación: primary espeja el acento y
    // secondary es su tinta derivada (si lo recomputa el watcher del shell
    // queda desdoblado en dos pasos de historial y tinte viejo de por medio).
    const a = deriveAccent(hex)
    props.theme.palette.primary = hex
    props.theme.palette.secondary = a.ink
    // El acento también persiste por el campo real (accent_custom) cuando
    // el plan lo permite — el resto de la paleta viaja en site_theme.
    if (advanced.value) props.form.accent_custom = hex
  }
}
function paletteText(key, e) {
  setPalette(key, e.target.value)
  e.target.value = props.theme.palette[key]
}

// --- Tipografía ---
const fontGroups = STORE_FONT_GROUPS
const fontLabel = (k) => STORE_FONTS[k]?.label || k
function pickFont(e) {
  props.form.name_font = e.target.value
  props.theme.typography.heading = e.target.value
  props.theme.typography.body = e.target.value
  ensureStoreFont(e.target.value)
}

// --- Distribución (solo lectura en esta fase: la edición vive en Bloques) ---
const surfaces = computed(() => ['landing', 'catalog', 'services'].map((id) => {
  const blocks = Array.isArray(props.layout?.[id]?.blocks) ? props.layout[id].blocks : []
  const on = blocks.filter((b) => b && b.enabled !== false)
  return { id, label: SURFACE_LABELS[id] || id, active: props.siteTemplates.includes(id), count: on.length, total: blocks.length }
}))

// Anillos del LookTab -> targets del contrato en la vista previa.
const RING_MAP = { logo: 'chrome.nav', accent: 'buttons', font: 'typo', cover: 'hero' }
const onLookRing = (key) => emit('ring', RING_MAP[key] || key)
</script>

<template>
  <!-- ===== Estilos: la edición guiada actual queda embebida tal cual ===== -->
  <div v-if="tool === 'estilos'" class="stp stp-look">
    <DesignLookTab :form="form" :benefits="benefits" :shop-name="shopName" @go-plans="emit('navigate', 'plans')" @ring="onLookRing" />
  </div>

  <!-- ===== Colores ===== -->
  <div v-else-if="tool === 'colores'" class="stp">
    <p class="stp-hint">El acento se guarda con tu diseño; el resto de la paleta viaja con el tema del Studio.</p>
    <div v-for="f in PALETTE_FIELDS" :key="f.key" class="stp-field" :data-focus="f.focus">
      <span class="stp-lb">{{ f.label }}</span>
      <div class="stp-color">
        <input type="color" class="stp-swatch" :value="theme.palette[f.key]" :aria-label="`${f.label} (selector de color)`" @input="setPalette(f.key, $event.target.value)" />
        <input type="text" class="stp-hex" :value="theme.palette[f.key]" :aria-label="`${f.label} en hexadecimal`" maxlength="7" spellcheck="false" @change="paletteText(f.key, $event)" @keydown.enter.prevent="paletteText(f.key, $event)" />
      </div>
      <small class="stp-hint2">{{ f.hint }}</small>
    </div>
  </div>

  <!-- ===== Tipografía ===== -->
  <div v-else-if="tool === 'tipografia'" class="stp">
    <div class="stp-field" data-focus="typo">
      <span class="stp-lb">Fuente principal</span>
      <select class="stp-select" :value="form.name_font" aria-label="Fuente principal" @change="pickFont">
        <optgroup v-for="g in fontGroups" :key="g.label" :label="g.label">
          <option v-for="k in g.keys" :key="k" :value="k">{{ fontLabel(k) }}</option>
        </optgroup>
        <option v-if="!fontGroups.some((g) => g.keys.includes(form.name_font))" :value="form.name_font">{{ fontLabel(form.name_font) }} (actual)</option>
      </select>
      <small class="stp-hint2">Se aplica a todo el texto de tu página y se guarda con el diseño.</small>
    </div>
    <div class="stp-field" data-focus="typo">
      <span class="stp-lb">Escala tipográfica</span>
      <div class="stp-seg" role="group" aria-label="Escala tipográfica">
        <button v-for="[id, lb] in SEG.scale" :key="id" type="button" class="stp-opt" :class="{ active: theme.typography.scale === id }" :aria-pressed="theme.typography.scale === id" @click="theme.typography.scale = id">{{ lb }}</button>
      </div>
      <small class="stp-hint2">Tamaños relativos de títulos y cuerpo (tema Studio).</small>
    </div>
    <div class="stp-field" data-focus="typo">
      <span class="stp-lb">Peso de los títulos <b class="stp-val">{{ theme.typography.weightHeading }}</b></span>
      <input type="range" class="stp-range" min="300" max="900" step="100" :value="theme.typography.weightHeading" aria-label="Peso de los títulos" @input="theme.typography.weightHeading = Number($event.target.value)" />
    </div>
    <div class="stp-field" data-focus="typo">
      <span class="stp-lb">Espacio entre letras</span>
      <div class="stp-seg" role="group" aria-label="Espacio entre letras">
        <button v-for="[id, lb] in TRACKING" :key="id" type="button" class="stp-opt" :class="{ active: theme.typography.letterSpacing === id }" :aria-pressed="theme.typography.letterSpacing === id" @click="theme.typography.letterSpacing = id">{{ lb }}</button>
      </div>
    </div>
  </div>

  <!-- ===== Contenedores ===== -->
  <div v-else-if="tool === 'contenedores'" class="stp">
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Redondeo</span>
      <div class="stp-seg" role="group" aria-label="Redondeo de tarjetas">
        <button v-for="[id, lb] in SEG.radius" :key="id" type="button" class="stp-opt" :class="{ active: theme.containers.radius === id }" :aria-pressed="theme.containers.radius === id" @click="theme.containers.radius = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Sombra</span>
      <div class="stp-seg" role="group" aria-label="Sombra de tarjetas">
        <button v-for="[id, lb] in SEG.shadow" :key="id" type="button" class="stp-opt" :class="{ active: theme.containers.shadow === id }" :aria-pressed="theme.containers.shadow === id" @click="theme.containers.shadow = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Borde</span>
      <div class="stp-seg" role="group" aria-label="Borde de tarjetas">
        <button v-for="[id, lb] in SEG.border" :key="id" type="button" class="stp-opt" :class="{ active: theme.containers.border === id }" :aria-pressed="theme.containers.border === id" @click="theme.containers.border = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Estilo de superficie</span>
      <div class="stp-seg" role="group" aria-label="Estilo de superficie">
        <button v-for="[id, lb] in SEG.surface" :key="id" type="button" class="stp-opt" :class="{ active: theme.containers.surface === id }" :aria-pressed="theme.containers.surface === id" @click="theme.containers.surface = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Densidad</span>
      <div class="stp-seg" role="group" aria-label="Densidad">
        <button v-for="[id, lb] in SEG.density" :key="id" type="button" class="stp-opt" :class="{ active: theme.containers.density === id }" :aria-pressed="theme.containers.density === id" @click="theme.containers.density = id">{{ lb }}</button>
      </div>
    </div>
    <p class="stp-sec">Botones</p>
    <div class="stp-field" data-focus="buttons">
      <span class="stp-lb">Forma</span>
      <div class="stp-seg" role="group" aria-label="Forma de los botones">
        <button v-for="[id, lb] in SEG.btnShape" :key="id" type="button" class="stp-opt" :class="{ active: theme.buttons.shape === id }" :aria-pressed="theme.buttons.shape === id" @click="theme.buttons.shape = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="buttons">
      <span class="stp-lb">Estilo</span>
      <div class="stp-seg" role="group" aria-label="Estilo de los botones">
        <button v-for="[id, lb] in SEG.btnStyle" :key="id" type="button" class="stp-opt" :class="{ active: theme.buttons.style === id }" :aria-pressed="theme.buttons.style === id" @click="theme.buttons.style = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="buttons">
      <span class="stp-lb">Tamaño</span>
      <div class="stp-seg" role="group" aria-label="Tamaño de los botones">
        <button v-for="[id, lb] in SEG.btnSize" :key="id" type="button" class="stp-opt" :class="{ active: theme.buttons.size === id }" :aria-pressed="theme.buttons.size === id" @click="theme.buttons.size = id">{{ lb }}</button>
      </div>
    </div>
    <p class="stp-sec">Movimiento</p>
    <div class="stp-field" data-focus="page">
      <span class="stp-lb">Aparición de secciones</span>
      <div class="stp-seg" role="group" aria-label="Animación de aparición">
        <button v-for="[id, lb] in SEG.reveal" :key="id" type="button" class="stp-opt" :class="{ active: theme.motion.reveal === id }" :aria-pressed="theme.motion.reveal === id" @click="theme.motion.reveal = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Hover de tarjetas</span>
      <div class="stp-seg" role="group" aria-label="Hover de tarjetas">
        <button v-for="[id, lb] in SEG.hover" :key="id" type="button" class="stp-opt" :class="{ active: theme.motion.hover === id }" :aria-pressed="theme.motion.hover === id" @click="theme.motion.hover = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="page">
      <span class="stp-lb">Intensidad</span>
      <div class="stp-seg" role="group" aria-label="Intensidad del movimiento">
        <button v-for="[id, lb] in SEG.intensity" :key="id" type="button" class="stp-opt" :class="{ active: theme.motion.intensity === id }" :aria-pressed="theme.motion.intensity === id" @click="theme.motion.intensity = id">{{ lb }}</button>
      </div>
    </div>
  </div>

  <!-- ===== Distribución ===== -->
  <div v-else-if="tool === 'distribucion'" class="stp">
    <p class="stp-hint">Las páginas activas de tu web y sus bloques. El orden y las variantes se editan en el editor de bloques.</p>
    <ul class="stp-surfaces" data-focus="blk">
      <li v-for="s in surfaces" :key="s.id" class="stp-surface" :data-on="s.active">
        <AppIcon :name="s.id === 'landing' ? 'store' : s.id === 'catalog' ? 'layout-grid' : 'wrench'" :size="16" />
        <span class="stp-surface-lb">{{ s.label }}</span>
        <span class="stp-surface-n">{{ s.active ? `${s.count}/${s.total || s.count} bloques` : 'apagada' }}</span>
      </li>
    </ul>
    <button type="button" class="btn secondary btn-auto stp-cta" @click="emit('navigate', 'blocks')">
      <AppIcon name="list-ordered" :size="16" /> Abrir el editor de bloques
    </button>
  </div>

  <!-- ===== Móvil ===== -->
  <div v-else-if="tool === 'movil'" class="stp">
    <p class="stp-hint">Ajustes específicos de pantallas chicas (probá el modo Móvil en la vista previa).</p>
    <div class="stp-field" data-focus="chrome.nav">
      <span class="stp-lb">Navegación</span>
      <div class="stp-seg" role="group" aria-label="Navegación en móvil">
        <button v-for="[id, lb] in SEG.nav" :key="id" type="button" class="stp-opt" :class="{ active: theme.mobile.nav === id }" :aria-pressed="theme.mobile.nav === id" @click="theme.mobile.nav = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Grilla de productos</span>
      <div class="stp-seg" role="group" aria-label="Columnas de la grilla en móvil">
        <button v-for="[id, lb] in SEG.gridCols" :key="id" type="button" class="stp-opt" :class="{ active: theme.mobile.gridCols === id }" :aria-pressed="theme.mobile.gridCols === id" @click="theme.mobile.gridCols = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="card">
      <span class="stp-lb">Tarjetas</span>
      <div class="stp-seg" role="group" aria-label="Estilo de tarjetas en móvil">
        <button v-for="[id, lb] in SEG.cardStyle" :key="id" type="button" class="stp-opt" :class="{ active: theme.mobile.cardStyle === id }" :aria-pressed="theme.mobile.cardStyle === id" @click="theme.mobile.cardStyle = id">{{ lb }}</button>
      </div>
    </div>
    <div class="stp-field" data-focus="hero">
      <span class="stp-lb">Altura de la portada</span>
      <div class="stp-seg" role="group" aria-label="Altura de la portada en móvil">
        <button v-for="[id, lb] in SEG.heroHeight" :key="id" type="button" class="stp-opt" :class="{ active: theme.mobile.heroHeight === id }" :aria-pressed="theme.mobile.heroHeight === id" @click="theme.mobile.heroHeight = id">{{ lb }}</button>
      </div>
    </div>
    <label class="stp-check" data-focus="chrome.nav">
      <input type="checkbox" :checked="theme.mobile.stickyCta" @change="theme.mobile.stickyCta = $event.target.checked" />
      <span>Botón de contacto siempre visible abajo</span>
    </label>
  </div>

  <!-- ===== Folletos ===== -->
  <div v-else-if="tool === 'folletos'" class="stp">
    <div class="stp-card">
      <span class="stp-card-ico"><AppIcon name="printer" :size="22" /></span>
      <strong>Flyer Studio</strong>
      <p>Diseñá folletos imprimibles con tu logo, colores y QR a la página. Es otra superficie: se abre en Herramientas.</p>
      <button v-if="canFlyers" type="button" class="btn secondary btn-auto" @click="emit('navigate', 'tools')">
        Ir a folletos <AppIcon name="arrow-right" :size="15" />
      </button>
      <template v-else>
        <p class="stp-lock"><span class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></p>
        <button type="button" class="btn secondary btn-auto" @click="emit('navigate', 'plans')">Ver planes <AppIcon name="arrow-right" :size="15" /></button>
      </template>
    </div>
  </div>

  <!-- ===== Avanzado ===== -->
  <div v-else-if="tool === 'avanzado'" class="stp">
    <div class="stp-field" data-focus="page">
      <span class="stp-lb">Tema de la página</span>
      <div class="stp-seg" role="group" aria-label="Tema claro u oscuro">
        <button v-for="[id, lb, ic] in SEG.pageTheme" :key="id" type="button" class="stp-opt" :class="{ active: form.theme === id }" :aria-pressed="form.theme === id" @click="form.theme = id">
          <AppIcon :name="ic" :size="14" /> {{ lb }}
        </button>
      </div>
      <small class="stp-hint2">Claro u oscuro: se guarda con tu diseño. Para previsualizar sin guardar usá el sol/luna del lienzo.</small>
    </div>
    <div class="stp-card stp-soon">
      <span class="stp-card-ico"><AppIcon name="sliders" :size="22" /></span>
      <strong>Personalización total</strong>
      <p>Fondos con imagen o malla, CSS propio y tokens por plantilla llegan con el tema del Studio.</p>
      <span class="lock-badge">Próximamente</span>
    </div>
  </div>
</template>

<style scoped>
.stp { display: flex; flex-direction: column; gap: 14px; }
.stp-look { display: contents; }
/* El historial del Studio (Ctrl+Z, botones del savebar) es el único dentro
   del shell: se ocultan los controles de historial internos del LookTab. */
.stp-look :deep(.dl-hbtn) { display: none; }
.stp-look :deep(.dsg-card) { border: 0; box-shadow: none; padding: 0; border-radius: 0; background: transparent; }
.stp-hint { margin: 0; font-size: 12.5px; color: var(--muted); line-height: 1.45; }
.stp-hint2 { font-size: 11.5px; color: var(--muted); }
.stp-sec { margin: 8px 0 -6px; font-size: 11px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); }
.stp-field { display: flex; flex-direction: column; gap: 7px; padding: 10px 12px; border: 1px solid var(--line-soft); border-radius: 10px; background: var(--card); }
.stp-field.sts-flash { border-color: var(--brand-500); box-shadow: var(--ring); }
.stp-lb { font-size: 12.5px; font-weight: 600; color: var(--ink-2); }
.stp-val { font-weight: 700; color: var(--brand-600, var(--brand-500)); }
.stp-seg { display: flex; flex-wrap: wrap; gap: 4px; }
.stp-opt {
  min-height: 34px; padding: 5px 12px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--surface); color: var(--ink-2); font: inherit; font-size: 12.5px; font-weight: 600;
  cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: border-color .12s, background .12s, color .12s;
}
.stp-opt:hover { border-color: var(--brand-400, var(--brand-500)); color: var(--ink); }
.stp-opt.active { background: var(--brand-500); border-color: var(--brand-500); color: #fff; }
.stp-opt:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stp-color { display: flex; align-items: center; gap: 8px; }
.stp-swatch {
  width: 44px; height: 36px; padding: 0; border: 1px solid var(--line); border-radius: 8px;
  background: none; cursor: pointer; overflow: hidden;
}
.stp-swatch::-webkit-color-swatch-wrapper { padding: 0; }
.stp-swatch::-webkit-color-swatch { border: 0; border-radius: 7px; }
.stp-hex {
  width: 92px; height: 36px; padding: 0 10px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--surface); color: var(--ink); font: inherit; font-size: 13px; font-family: ui-monospace, monospace;
}
.stp-hex:focus-visible, .stp-swatch:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stp-select {
  width: 100%; height: 40px; padding: 0 10px; border: 1px solid var(--line); border-radius: 9px;
  background: var(--surface); color: var(--ink); font: inherit; font-size: 14px;
}
.stp-select:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stp-range { width: 100%; accent-color: var(--brand-500); }
.stp-check { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 10px 12px; border: 1px solid var(--line-soft); border-radius: 10px; background: var(--card); font-size: 13px; color: var(--ink-2); cursor: pointer; }
.stp-check input { width: 18px; height: 18px; accent-color: var(--brand-500); }
.stp-surfaces { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.stp-surface {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; min-height: 44px;
  border: 1px solid var(--line); border-radius: 10px; background: var(--card); font-size: 13px;
}
.stp-surface[data-on='false'] { opacity: .55; }
.stp-surface-lb { font-weight: 600; flex: 1; }
.stp-surface-n { font-size: 11.5px; color: var(--muted); }
.stp-cta { align-self: flex-start; }
.stp-card { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; padding: 16px; border: 1px solid var(--line); border-radius: 12px; background: var(--card); font-size: 13px; color: var(--ink-2); }
.stp-card p { margin: 0; color: var(--muted); font-size: 12.5px; line-height: 1.45; }
.stp-card-ico { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 11px; background: var(--brand-soft); color: var(--brand-ink); }
.stp-soon { opacity: .85; border-style: dashed; }
.stp-lock { margin: 0; }
</style>
