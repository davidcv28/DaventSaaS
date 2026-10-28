<script setup>
// Galería de estilos del panel "Estilos": un solo camino, elegir mirando.
// Cada tarjeta es una mini web pintada con los colores y la tipografía
// reales del estilo (fondo, superficie, borde y texto), con su estado
// encima. Debajo viven la paleta del estilo activo y la barra de prueba.
// Probar es un ensayo deshacible del shell (api.tryIt / tryPalette /
// revertTrial / keepTrial): nada se guarda hasta el Guardar de la savebar.
import { computed, inject, onMounted } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { PRESET_PICKER_IDS, ensurePresetFonts, presetLock } from './catalog.js'
import { STYLE_PALETTES, stylePaletteColors } from '../contract.js'
import { storeFontFamily } from '../../api/stores.api.js'
import { useStoreStore } from '../../stores/store.store.js'

const props = defineProps({
  benefits: { type: Object, default: () => ({}) },
  mode: { type: String, default: 'light' },
  // Acento elegido en "Ajustá el estilo": se fusiona con la paleta.
  accent: { type: String, default: '' }
})

const api = inject('studioPresets')
const store = useStoreStore()

onMounted(ensurePresetFonts)

const custom = computed(() => store.customization || {})
const stored = computed(() => custom.value.site_theme_draft?.style || custom.value.site_theme?.style || null)

const lockOf = (p) => (api.lockOf ? api.lockOf(p) : presetLock(p, props.benefits))

// "En uso": el estilo guardado coincide y no hay prueba en vivo. Manda el id
// del style; sin él (filas viejas) cae a la plantilla guardada.
const isCurrent = (p) => {
  if (api.tryingId.value) return false
  if (stored.value?.id) return stored.value.id === p.id
  return custom.value.template === p.template
}
const isTrying = (p) => api.tryingId.value === p.id

const pickerItems = computed(() => PRESET_PICKER_IDS
  .map((id) => api.presets.find((p) => p.id === id))
  .filter(Boolean))
const inUseId = computed(() => api.presets.find((p) => custom.value.template === p.template)?.id || '')
// El estilo en uso / en prueba siempre tiene tarjeta, aunque no esté en el
// subconjunto curado.
const extraItems = computed(() => {
  const picked = new Set(PRESET_PICKER_IDS)
  const ids = [...new Set([inUseId.value, api.tryingId.value].filter((id) => id && !picked.has(id)))]
  return ids.map((id) => api.presets.find((p) => p.id === id)).filter(Boolean)
})
const items = computed(() => [...pickerItems.value, ...extraItems.value])

// Paleta del estilo: en prueba manda el ensayo; en uso, la guardada.
function paletteOf(p) {
  if (isTrying(p)) return api.tryingPalette?.value || 'original'
  if (isCurrent(p) && stored.value?.id === p.id) return stored.value.palette || 'original'
  return 'original'
}
// El acento elegido solo pinta el estilo en uso / en prueba; una tarjeta
// inactiva muestra el acento propio del preset.
const accentFor = (p) => (isTrying(p) || isCurrent(p) ? props.accent || '' : '')
const colorsOf = (p) => stylePaletteColors(p.theme.palette, paletteOf(p), props.mode, accentFor(p) || null)

// Colores reales de la mini web: fondo, superficie, borde, texto y enlace.
function previewVars(p) {
  const c = colorsOf(p)
  return {
    '--pv-bg': c.containers.bg,
    '--pv-sf': c.containers.surface,
    '--pv-bd': c.containers.border,
    '--pv-ink': c.fonts.heading,
    '--pv-ac': c.fonts.link,
    '--pv-font': storeFontFamily(p.theme.typography.heading)
  }
}
function paletteSwatches(p, paletteId) {
  const c = stylePaletteColors(p.theme.palette, paletteId, props.mode, accentFor(p) || null)
  return [c.containers.bg, c.containers.surface, c.containers.border, c.fonts.heading]
}

const stateOf = (p) => {
  if (isTrying(p)) return 'trying'
  if (isCurrent(p)) return 'current'
  if (lockOf(p)) return 'locked'
  return ''
}
const STATE_LABEL = { trying: 'probando', current: 'en uso', locked: 'requiere plan' }
const stateLabel = (p) => STATE_LABEL[stateOf(p)] || ''
function ariaOf(p) {
  const state = stateLabel(p)
  return `${p.name}${state ? `, ${state}` : ''}`
}
function titleOf(p) {
  const bits = [p.name, p.desc].filter(Boolean)
  const state = stateLabel(p)
  if (state) bits.push(state)
  if (lockOf(p)) bits.push('se prueba gratis; para guardarlo necesitás un plan superior')
  return bits.join(' · ')
}

const activePreset = computed(() => (
  (api.tryingId.value && api.presets.find((p) => p.id === api.tryingId.value))
  || items.value.find((p) => isCurrent(p))
  || null
))
const trialPreset = computed(() => (api.tryingId.value ? api.presets.find((p) => p.id === api.tryingId.value) : null))
const trialLocked = computed(() => Boolean(trialPreset.value && lockOf(trialPreset.value)))

const onPick = (p) => api.tryIt(p)
const onPalette = (p, paletteId) => api.tryPalette?.(p, paletteId)
const onRevert = () => api.revertTrial()
</script>

<template>
  <div class="stg">
    <!-- ===== Estilos: se eligen mirando ===== -->
    <div v-if="items.length" class="stg-grid" role="group" aria-label="Estilos para tu web">
      <button
        v-for="p in items" :key="p.id"
        type="button" class="stg-card"
        :class="{ 'is-current': isCurrent(p), 'is-trying': isTrying(p), 'is-locked': lockOf(p) }"
        :aria-pressed="isTrying(p) || isCurrent(p)"
        :aria-label="ariaOf(p)" :title="titleOf(p)"
        @click="onPick(p)"
      >
        <span class="stg-prev" :style="previewVars(p)" aria-hidden="true">
          <span class="stg-prev-top">
            <span class="stg-aa">Aa</span>
            <span class="stg-lines"><i></i><i></i></span>
            <span v-if="stateOf(p)" class="stg-chip" :class="`is-${stateOf(p)}`">
              <AppIcon v-if="stateOf(p) === 'locked'" name="lock" :size="9" :stroke="2.4" />
              {{ stateLabel(p) }}
            </span>
          </span>
          <span class="stg-prev-card"><i></i><i class="stg-cta"></i></span>
        </span>
        <span class="stg-name">{{ p.name }}</span>
      </button>
    </div>

    <!-- ===== Vacío / error de carga ===== -->
    <div v-else class="stg-empty" role="status">
      <AppIcon name="palette" :size="20" aria-hidden="true" />
      <p>No pudimos cargar los estilos. Recargá la página y probá de nuevo.</p>
    </div>

    <!-- ===== Paleta del estilo activo ===== -->
    <div v-if="activePreset" class="stg-pal" role="group" :aria-label="`Colores de ${activePreset.name}`">
      <p class="stg-pal-lb">
        <span>Colores de la web</span>
        <span class="stg-pal-tip">tiñe fondos, tarjetas y textos</span>
      </p>
      <div class="stg-pal-row">
        <button
          v-for="pal in STYLE_PALETTES" :key="pal.id" type="button"
          class="stg-pal-btn" :class="{ active: paletteOf(activePreset) === pal.id }"
          :aria-pressed="paletteOf(activePreset) === pal.id"
          :aria-label="`${activePreset.name}, colores ${pal.label}`"
          @click="onPalette(activePreset, pal.id)"
        >
          <span class="stg-pal-sw" aria-hidden="true">
            <i v-for="(c, i) in paletteSwatches(activePreset, pal.id)" :key="i" :style="{ background: c }" />
          </span>
          <span class="stg-pal-name">{{ pal.label }}</span>
        </button>
      </div>
    </div>

    <!-- ===== Probando: una línea, siempre con salida ===== -->
    <div v-if="trialPreset" class="stg-trial" role="status">
      <p class="stg-trial-tx">Probando <b>{{ trialPreset.name }}</b></p>
      <div class="stg-trial-acts">
        <button v-if="trialLocked" type="button" class="stg-btn is-plans" @click="api.goPlans()">
          <AppIcon name="crown" :size="12" aria-hidden="true" /> Ver planes
        </button>
        <button type="button" class="stg-btn" @click="onRevert">
          <AppIcon name="undo" :size="12" aria-hidden="true" /> Deshacer
        </button>
        <button v-if="!trialLocked" type="button" class="stg-btn is-keep" @click="api.keepTrial()">
          <AppIcon name="check" :size="12" :stroke="2.6" aria-hidden="true" /> Quedarla
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stg { display: flex; flex-direction: column; gap: 8px; min-width: 0; }

/* ===== Grilla 2 columnas: la mini web manda ===== */
.stg-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; min-width: 0; }
.stg-card {
  display: flex; flex-direction: column; gap: 3px; min-width: 0;
  padding: 4px; border: 1px solid var(--line); border-radius: 10px;
  background: var(--surface); color: var(--ink); font: inherit; text-align: left;
  cursor: pointer; transition: border-color .14s, background .14s;
}
.stg-card:hover { border-color: var(--brand-500); }
.stg-card:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stg-card.is-current { border-color: var(--brand-500); }
.stg-card.is-trying { border-color: var(--brand-500); background: var(--brand-soft); }
.stg-card.is-locked .stg-name { color: var(--ink-2); }

/* Mini web: fondo, superficie, borde, texto y acento reales del estilo. */
.stg-prev {
  display: flex; flex-direction: column; gap: 4px; height: 38px; padding: 5px;
  background: var(--pv-bg); border: 1px solid var(--pv-bd); border-radius: 7px;
  overflow: hidden; min-width: 0;
}
.stg-prev-top { display: flex; align-items: center; gap: 4px; min-width: 0; }
.stg-aa { flex: none; font: 800 13px/1 var(--pv-font); color: var(--pv-ink); }
.stg-lines { flex: 1; min-width: 0; display: grid; gap: 2px; }
.stg-lines i { display: block; height: 2px; border-radius: 2px; background: var(--pv-ink); opacity: .32; }
.stg-lines i:last-child { width: 62%; }
.stg-prev-card {
  flex: 1; min-height: 0; display: flex; align-items: center; gap: 3px; padding: 0 4px;
  background: var(--pv-sf); border: 1px solid var(--pv-bd); border-radius: 4px;
}
.stg-prev-card i { display: block; width: 38%; height: 3px; border-radius: 2px; background: var(--pv-ink); opacity: .38; }
.stg-prev-card i.stg-cta { margin-left: auto; width: 16px; height: 6px; border-radius: 3px; background: var(--pv-ac); opacity: 1; }

/* Estado: siempre legible sobre la tarjeta, nunca sobre la mini web. */
.stg-chip {
  flex: none; display: inline-flex; align-items: center; gap: 2px;
  padding: 1px 4px; border: 1px solid var(--line); border-radius: 4px;
  background: var(--card); color: var(--ink-2);
  font-size: 9.5px; font-weight: 700; line-height: 1.35; white-space: nowrap;
}
.stg-chip.is-current { background: var(--brand-600); border-color: var(--brand-600); color: #fff; }
.stg-chip.is-trying { background: var(--brand-soft); border-color: var(--brand-500); color: var(--brand-ink); }
.stg-name {
  min-width: 0; padding: 0 1px; font-size: 12px; font-weight: 700; line-height: 1.25;
  color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ===== Paleta del estilo activo ===== */
.stg-pal { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.stg-pal-lb { display: flex; align-items: baseline; gap: 5px; margin: 0; min-width: 0; font-size: 11.5px; font-weight: 700; color: var(--ink-2); }
.stg-pal-tip { font-size: 10.5px; font-weight: 500; color: var(--muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.stg-pal-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; }
.stg-pal-btn {
  display: flex; flex-direction: column; gap: 3px; min-width: 0; min-height: 40px;
  padding: 4px; border: 1px solid var(--line); border-radius: 8px;
  background: var(--surface); color: var(--ink-2); font: inherit; cursor: pointer;
  transition: border-color .14s, background .14s;
}
.stg-pal-btn:hover { border-color: var(--brand-500); }
.stg-pal-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stg-pal-btn.active { border-color: var(--brand-500); background: var(--brand-soft); }
.stg-pal-sw { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); height: 11px; border-radius: 3px; overflow: hidden; }
.stg-pal-sw i { display: block; }
.stg-pal-name {
  font-size: 10.5px; font-weight: 700; line-height: 1.2; text-align: center;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.stg-pal-btn.active .stg-pal-name { color: var(--brand-ink); }

/* ===== Barra de prueba ===== */
.stg-trial {
  display: flex; align-items: center; gap: 6px; min-width: 0;
  padding: 3px 6px; border: 1px solid var(--brand-500); border-radius: 9px;
  background: var(--brand-soft); color: var(--brand-ink);
}
.stg-trial-tx { flex: 1; min-width: 0; margin: 0; font-size: 11.5px; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stg-trial-tx b { font-weight: 800; }
.stg-trial-acts { flex: none; display: flex; gap: 4px; }
.stg-btn {
  display: inline-flex; align-items: center; gap: 3px; min-height: 40px; padding: 0 8px;
  border: 1px solid var(--line); border-radius: 7px; background: var(--surface);
  color: var(--ink-2); font: inherit; font-size: 11px; font-weight: 700;
  white-space: nowrap; cursor: pointer;
}
.stg-btn:hover { border-color: var(--brand-500); }
.stg-btn:focus-visible { outline: 2px solid var(--brand-500); outline-offset: 2px; }
.stg-btn.is-keep { background: var(--brand-600); border-color: var(--brand-600); color: #fff; }
.stg-btn.is-plans { background: var(--surface); border-color: var(--brand-500); color: var(--brand-ink); }

/* ===== Vacío / error ===== */
.stg-empty {
  display: flex; align-items: center; gap: 10px; padding: 12px;
  border: 1px dashed var(--line); border-radius: 10px; background: var(--surface); color: var(--muted);
}
.stg-empty p { margin: 0; font-size: 12px; line-height: 1.4; color: var(--ink-2); }

@media (prefers-reduced-motion: reduce) {
  .stg-card, .stg-pal-btn { transition: none; }
}
</style>
