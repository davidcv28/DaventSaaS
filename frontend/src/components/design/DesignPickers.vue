<script setup>
// Selectores del catálogo de diseño: patrón (estructura de la web) y estilo
// (piel visual + iconos). Se muestran como galerías de tarjetas con muestra
// real (paleta del estilo / mapa de bloques del patrón) en vez de selects:
// elegir diseño es una decisión visual.
import { computed, onMounted, ref } from 'vue'
import { useDesignCatalog } from '../../composables/useDesignCatalog.js'
import { STORE_TEMPLATES, STORE_ACCENTS, allowedTemplatesFor, ensureStoreFont } from '../../api/stores.api.js'
import { nearestAccent, hexToRgb } from '../../utils/colorTools.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})

const { patterns, styles, status, load } = useDesignCatalog()
onMounted(() => load())

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const allowed = computed(() => allowedTemplatesFor(props.benefits || {}))
const templateAllowed = (tpl) => allowed.value.includes(tpl)
const tierOf = (tpl) => STORE_TEMPLATES[tpl]?.tier || 'base'
const tierLabel = (tpl) => {
  const tier = tierOf(tpl)
  return tier === 'plus' ? 'Estándar' : tier === 'advanced' ? 'Premium' : 'Incluido'
}

const patternOptions = computed(() => patterns.value.filter((p) => p.is_active !== false))
const styleOptions = computed(() => styles.value.filter((s) => s.is_active !== false))

// Layout del patrón en el contrato {superficie: {blocks}}: el catálogo lo
// guarda como listas por superficie (composición de la plantilla).
function wrapLayout(layout) {
  const out = {}
  for (const surface of ['landing', 'catalog', 'services']) {
    const blocks = layout?.[surface]
    if (!Array.isArray(blocks) || !blocks.length) continue
    out[surface] = {
      blocks: blocks.map((b, i) => ({
        id: b.id,
        enabled: b.enabled !== false,
        order: typeof b.order === 'number' ? b.order : i,
        ...(b.variant ? { variant: b.variant } : {})
      }))
    }
  }
  return out
}
const patternLayout = (p) => wrapLayout(p.layout)
const sameJson = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})

const currentPattern = computed(() => (
  patternOptions.value.find((p) => (
    p.template === props.form.template && sameJson(patternLayout(p), props.form.layout_config)
  ))?.slug
  // Un estilo aplica su propia estructura: si no hay patrón idéntico se
  // muestra el de la misma plantilla en vez de dejar la galería sin marca.
  || patternOptions.value.find((p) => p.template === props.form.template)?.slug
  || ''
))
const currentStyle = computed(() => props.form.site_theme?.style?.id || '')

function onPatternPick(p) {
  if (!p || !templateAllowed(p.template)) return
  props.form.template = p.template
  props.form.layout_config = patternLayout(p)
}

function onStylePick(s) {
  if (!s || !templateAllowed(s.template)) return
  const tokens = s.tokens || {}
  props.form.site_theme = { ...(props.form.site_theme || {}), style: { id: s.slug } }
  props.form.theme = s.page_theme || props.form.theme
  // El estilo también es un diseño completo: cambia la estructura (plantilla
  // + orden de bloques por superficie) además de la piel. El patrón queda
  // como control para volver a mover la estructura después.
  props.form.template = s.template || props.form.template
  if (s.layout && Object.keys(s.layout).length) props.form.layout_config = wrapLayout(s.layout)
  const body = tokens.typography?.body
  if (body) {
    props.form.name_font = body
    ensureStoreFont(body)
  }
  const accent = tokens.palette?.accent
  if (accent && advanced.value) props.form.accent_custom = accent
  else if (accent) {
    const slug = nearestAccent(hexToRgb(accent), STORE_ACCENTS)
    if (slug) props.form.accent = slug
  }
}

// --- Muestras ---
const COLORS_SHOWN = 4
// Paleta del estilo: acento, primario, superficie y fondo del tema.
function swatch(s) {
  const p = s.tokens?.palette || {}
  return {
    background: p.bg || p.surface || '#fff',
    borderColor: p.border || 'transparent'
  }
}
function dots(s) {
  const p = s.tokens?.palette || {}
  return [p.accent, p.primary, p.surface || p.bg, p.text].filter(Boolean).slice(0, COLORS_SHOWN)
}
// Mapa de bloques de la portada: barras con el ancho de cada bloque.
const BLOCK_WIDTHS = ['100%', '72%', '88%', '60%', '80%']
function patternBars(p) {
  const blocks = Array.isArray(p.layout?.landing) ? p.layout.landing : []
  return blocks.filter((b) => b && b.enabled !== false).slice(0, 5).map((b, i) => BLOCK_WIDTHS[i % BLOCK_WIDTHS.length])
}

// Galerías plegadas: mostrar las primeras y expandir a demanda (Hick's law).
const SHOW = 6
const allStyles = ref(false)
const allPatterns = ref(false)
const visibleStyles = computed(() => (allStyles.value ? styleOptions.value : styleOptions.value.slice(0, SHOW)))
const visiblePatterns = computed(() => (allPatterns.value ? patternOptions.value : patternOptions.value.slice(0, SHOW)))
</script>

<template>
  <section class="dpicks card" aria-label="Diseño de tu web">
    <header class="dpicks-head">
      <strong><AppIcon name="layout-grid" :size="16" aria-hidden="true" /> Diseño de tu web</strong>
      <small>El estilo cambia colores, tipografía, estructura e iconos. El patrón ajusta solo la estructura.</small>
    </header>

    <div class="dpicks-block">
      <div class="dpicks-row">
        <h4>Estilo visual</h4>
        <span class="dpicks-note">Elegí el look completo</span>
      </div>
      <div class="dpicks-grid styles" role="radiogroup" aria-label="Estilo visual de tu web">
        <button
          v-for="s in visibleStyles" :key="s.slug" type="button" role="radio"
          class="dpick style" :class="{ on: currentStyle === s.slug, locked: !templateAllowed(s.template) }"
          :aria-checked="currentStyle === s.slug"
          :title="templateAllowed(s.template) ? s.descripcion : `${s.nombre} — disponible en el plan ${tierLabel(s.template)}`"
          @click="onStylePick(s)"
        >
          <span class="dpick-swatch" :style="swatch(s)" aria-hidden="true">
            <i v-for="(c, i) in dots(s)" :key="i" :style="{ background: c }"></i>
            <span v-if="s.page_theme === 'dark'" class="dpick-dark"><AppIcon name="moon" :size="11" /></span>
          </span>
          <span class="dpick-name">{{ s.nombre }}</span>
          <span class="dpick-meta">{{ s.categoria }}</span>
          <span class="dpick-tier" :class="{ locked: !templateAllowed(s.template) }">
            <AppIcon v-if="!templateAllowed(s.template)" name="lock" :size="10" :stroke="2" />
            {{ tierLabel(s.template) }}
          </span>
        </button>
      </div>
      <button v-if="styleOptions.length > SHOW" type="button" class="dpicks-more" :aria-expanded="allStyles" @click="allStyles = !allStyles">
        {{ allStyles ? 'Ver menos' : `Ver los ${styleOptions.length} estilos` }}
        <AppIcon :name="allStyles ? 'chevron-up' : 'chevron-down'" :size="14" />
      </button>
    </div>

    <div class="dpicks-block">
      <div class="dpicks-row">
        <h4>Patrón de la web</h4>
        <span class="dpicks-note">Orden de las secciones</span>
      </div>
      <div class="dpicks-grid patterns" role="radiogroup" aria-label="Patrón de diseño web">
        <button
          v-for="p in visiblePatterns" :key="p.slug" type="button" role="radio"
          class="dpick pattern" :class="{ on: currentPattern === p.slug, locked: !templateAllowed(p.template) }"
          :aria-checked="currentPattern === p.slug"
          :title="templateAllowed(p.template) ? p.descripcion : `${p.nombre} — disponible en el plan ${tierLabel(p.template)}`"
          @click="onPatternPick(p)"
        >
          <span class="dpick-bars" aria-hidden="true">
            <i v-for="(w, i) in patternBars(p)" :key="i" :style="{ width: w }"></i>
          </span>
          <span class="dpick-name">{{ p.nombre }}</span>
          <span class="dpick-meta">{{ p.categoria }}</span>
          <span class="dpick-tier" :class="{ locked: !templateAllowed(p.template) }">
            <AppIcon v-if="!templateAllowed(p.template)" name="lock" :size="10" :stroke="2" />
            {{ tierLabel(p.template) }}
          </span>
        </button>
      </div>
      <button v-if="patternOptions.length > SHOW" type="button" class="dpicks-more" :aria-expanded="allPatterns" @click="allPatterns = !allPatterns">
        {{ allPatterns ? 'Ver menos' : `Ver los ${patternOptions.length} patrones` }}
        <AppIcon :name="allPatterns ? 'chevron-up' : 'chevron-down'" :size="14" />
      </button>
    </div>

    <p v-if="status === 'error'" class="dpicks-alert" role="alert">
      No pudimos cargar el catálogo de diseño.
      <button type="button" class="btn ghost btn-auto" @click="load(true)">Reintentar</button>
    </p>
    <p v-else-if="status === 'success' && !patternOptions.length && !styleOptions.length" class="dpicks-alert" role="status">
      El catálogo está vacío: corré <code>manage.py seed_design_catalog</code> en el servidor.
    </p>
  </section>
</template>

<style scoped>
.dpicks { display: flex; flex-direction: column; gap: 18px; padding: 16px; }
.dpicks-head strong { display: inline-flex; align-items: center; gap: 6px; font-size: 15px; }
.dpicks-head small { display: block; margin-top: 4px; font-size: 12px; opacity: .72; }
.dpicks-block { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.dpicks-row { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.dpicks-row h4 { margin: 0; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--ink-2); }
.dpicks-note { font-size: 11.5px; color: var(--muted); }
.dpicks-grid { display: grid; gap: 8px; min-width: 0; }
.dpicks-grid.styles { grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); }
.dpicks-grid.patterns { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
.dpick {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px; min-width: 0;
  padding: 8px; border: 1px solid var(--line); border-radius: 12px;
  background: var(--card); color: var(--ink); font: inherit; text-align: left; cursor: pointer;
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.dpick:hover { border-color: var(--line-strong); }
.dpick:focus-visible { outline: var(--focus-ring, 2px solid var(--brand-500)); outline-offset: 2px; }
.dpick.on { border-color: var(--brand-500); box-shadow: inset 0 0 0 1px var(--brand-500); }
.dpick.locked { opacity: .78; }
.dpick-swatch {
  position: relative; display: flex; align-items: flex-end; gap: 4px; width: 100%; height: 46px;
  padding: 7px; border: 1px solid var(--line); border-radius: 8px; overflow: hidden;
}
.dpick-swatch i { width: 14px; height: 14px; border-radius: 999px; box-shadow: 0 0 0 1px rgba(0,0,0,.08); }
.dpick-dark { position: absolute; top: 5px; right: 5px; display: grid; place-items: center; width: 18px; height: 18px; border-radius: 999px; background: rgba(0,0,0,.42); color: #fff; }
.dpick-bars { display: flex; flex-direction: column; gap: 3px; width: 100%; height: 46px; padding: 7px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); justify-content: center; }
.dpick-bars i { display: block; height: 4px; border-radius: 999px; background: color-mix(in srgb, var(--brand-500) 55%, var(--line)); }
.dpick-name { font-size: 12.5px; font-weight: 650; line-height: 1.25; overflow-wrap: anywhere; }
.dpick-meta { font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.dpick-tier { display: inline-flex; align-items: center; gap: 3px; margin-top: 2px; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--line); font-size: 10px; font-weight: 700; letter-spacing: .02em; color: var(--ink-3, var(--muted)); }
.dpick-tier.locked { border-color: color-mix(in srgb, var(--warn, #b45309) 45%, var(--line)); color: var(--warn, #b45309); }
.dpicks-more { align-self: flex-start; display: inline-flex; align-items: center; gap: 4px; min-height: 36px; padding: 6px 10px; border: 1px dashed var(--line); border-radius: 999px; background: none; color: var(--ink-2); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; }
.dpicks-more:hover { border-color: var(--line-strong); color: var(--ink); }
.dpicks-more:focus-visible { outline: var(--focus-ring, 2px solid var(--brand-500)); outline-offset: 2px; }
.dpicks-alert { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 12px; color: var(--danger, #b91c1c); }
.dpicks-alert code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
@media (max-width: 640px) {
  .dpicks-grid.styles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dpicks-grid.patterns { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dpick { padding: 7px; }
  .dpick-swatch, .dpick-bars { height: 40px; }
}
</style>
