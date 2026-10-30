<script setup>
// Dos selectores del catálogo de diseño: patrón (estructura de la web) y
// estilo (piel visual + iconos). El patrón escribe template + layout_config;
// el estilo escribe tema/acento/tipografía + site_theme.style.id y, además,
// su propia estructura (template + layout) para que el cambio se vea en la
// ubicación de los elementos, no solo en los colores.
import { computed, onMounted } from 'vue'
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
  return tier === 'plus' ? 'Desde Estándar' : tier === 'advanced' ? 'Premium' : 'Incluido'
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
  // muestra el de la misma plantilla en vez de dejar el select vacío.
  || patternOptions.value.find((p) => p.template === props.form.template)?.slug
  || ''
))
const currentStyle = computed(() => props.form.site_theme?.style?.id || '')
const currentPatternMeta = computed(() => patternOptions.value.find((p) => p.slug === currentPattern.value) || null)
const currentStyleMeta = computed(() => styleOptions.value.find((s) => s.slug === currentStyle.value) || null)

function onPatternPick(event) {
  const p = patternOptions.value.find((x) => x.slug === event.target.value)
  if (!p) return
  if (!templateAllowed(p.template)) {
    event.target.value = currentPattern.value
    return
  }
  props.form.template = p.template
  props.form.layout_config = patternLayout(p)
}

function onStylePick(event) {
  const s = styleOptions.value.find((x) => x.slug === event.target.value)
  if (!s) return
  if (!templateAllowed(s.template)) {
    event.target.value = currentStyle.value
    return
  }
  const tokens = s.tokens || {}
  props.form.site_theme = { ...(props.form.site_theme || {}), style: { id: s.slug } }
  props.form.theme = s.page_theme || props.form.theme
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
</script>

<template>
  <section class="dpicks card" aria-label="Diseño de tu web">
    <header class="dpicks-head">
      <strong><AppIcon name="layout-grid" :size="16" aria-hidden="true" /> Diseño de tu web</strong>
      <small>Elegí el patrón y el estilo por separado: cualquier combinación funciona.</small>
    </header>
    <div class="dpicks-grid">
      <div class="field">
        <label for="design-pattern">Patrón de diseño web</label>
        <select id="design-pattern" class="select" :value="currentPattern" :disabled="!patternOptions.length" @change="onPatternPick">
          <option value="" disabled>Elegí un patrón…</option>
          <option
            v-for="p in patternOptions" :key="p.slug" :value="p.slug"
            :disabled="!templateAllowed(p.template)"
          >
            {{ p.nombre }} · {{ p.categoria }} · {{ tierLabel(p.template) }}
          </option>
        </select>
        <p class="hint">La estructura de la portada, el catálogo y los servicios.</p>
        <p v-if="currentPatternMeta" class="dpicks-current">
          <span class="dpicks-dot" aria-hidden="true"></span>
          {{ currentPatternMeta.nombre }} · {{ tierLabel(currentPatternMeta.template) }}
        </p>
      </div>
      <div class="field">
        <label for="design-style-pick">Estilo</label>
        <select id="design-style-pick" class="select" :value="currentStyle" :disabled="!styleOptions.length" @change="onStylePick">
          <option value="" disabled>Elegí un estilo…</option>
          <option
            v-for="s in styleOptions" :key="s.slug" :value="s.slug"
            :disabled="!templateAllowed(s.template)"
          >
            {{ s.nombre }} · {{ s.categoria }} · {{ tierLabel(s.template) }}
          </option>
        </select>
        <p class="hint">Colores, tipografía, estructura e iconos de la web.</p>
        <p v-if="currentStyleMeta" class="dpicks-current">
          <span class="dpicks-dot" aria-hidden="true"></span>
          {{ currentStyleMeta.nombre }} · {{ tierLabel(currentStyleMeta.template) }}
        </p>
      </div>
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
.dpicks { display: flex; flex-direction: column; gap: 14px; padding: 16px; min-width: 0; }
.dpicks-head strong { display: inline-flex; align-items: center; gap: 6px; font-size: 15px; }
.dpicks-head small { display: block; margin-top: 4px; font-size: 12px; opacity: .72; }
/* Dos columnas alineadas: misma altura de label, select, hint y estado. */
.dpicks-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px 16px; align-items: start; min-width: 0; }
@media (min-width: 720px) { .dpicks-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.dpicks .field { display: grid; grid-template-rows: auto auto auto auto; gap: 6px; min-width: 0; margin: 0; }
.dpicks .field label { font-size: 13px; font-weight: 600; line-height: 1.3; min-height: 18px; }
.dpicks .select { width: 100%; min-width: 0; min-height: 44px; font-size: 16px; }
.dpicks .hint { margin: 0; font-size: 12px; line-height: 1.35; opacity: .7; min-height: 16px; }
.dpicks-current { display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; font-weight: 600; color: var(--ink-2); min-width: 0; overflow-wrap: anywhere; }
.dpicks-dot { flex: none; width: 7px; height: 7px; border-radius: 999px; background: var(--brand-500); }
.dpicks-alert { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 12px; color: var(--danger, #b91c1c); }
.dpicks-alert code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
