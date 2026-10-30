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
import { resolveSiteTheme } from '../../studio/contract.js'
import { normalizeLayoutConfig } from '../../templates/index.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})

const { patterns, styles, status, load } = useDesignCatalog()
// El catálogo es la base de datos: se revalida al entrar a la sección para
// que los patrones/estilos recién cargados aparezcan sin recargar la página.
onMounted(() => load(true))

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

// Layout del catálogo en el contrato {superficie: {blocks}}. Los patrones
// llegan como lista por superficie y los estilos como {blocks:[...]}: el
// normalizador acepta ambas formas y descarta ids/variantes inválidos.
const patternLayout = (p) => normalizeLayoutConfig(p.layout)
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

// Un patrón sin estilo elegido trae su propia piel (tokens del DesignPattern:
// fuentes y acento). Si ya hay un estilo aplicado, el estilo manda la piel y
// el patrón solo cambia la estructura.
function patternTheme(p) {
  const tokens = p.tokens || {}
  const theme = { ...(props.form.site_theme || {}) }
  const fonts = Array.isArray(tokens.fonts) ? tokens.fonts.filter(Boolean) : []
  if (fonts.length) {
    theme.typography = { ...(theme.typography || {}), body: fonts[0], heading: fonts[1] || fonts[0] }
    fonts.forEach((f) => ensureStoreFont(f))
  }
  const palette = { ...(theme.palette || {}) }
  if (tokens.accent) palette.accent = tokens.accent
  if (tokens.palette && typeof tokens.palette === 'object') Object.assign(palette, tokens.palette)
  if (Object.keys(palette).length) theme.palette = palette
  return theme
}

function onPatternPick(event) {
  const p = patternOptions.value.find((x) => x.slug === event.target.value)
  if (!p) return
  if (!templateAllowed(p.template)) {
    event.target.value = currentPattern.value
    return
  }
  props.form.template = p.template
  props.form.layout_config = patternLayout(p)
  if (!props.form.site_theme?.style?.id) props.form.site_theme = patternTheme(p)
}

function onStylePick(event) {
  const s = styleOptions.value.find((x) => x.slug === event.target.value)
  if (!s) return
  if (!templateAllowed(s.template)) {
    event.target.value = currentStyle.value
    return
  }
  // El estilo es un tema completo: se aplican sus tokens (paleta,
  // tipografía, contenedores, botones, fondo, movimiento y móvil) para que
  // el look elegido se vea igual acá, en el Studio y en la web publicada.
  const theme = resolveSiteTheme(s.tokens || {})
  props.form.site_theme = { ...theme, style: { id: s.slug } }
  props.form.theme = s.page_theme || props.form.theme
  props.form.template = s.template || props.form.template
  const layout = normalizeLayoutConfig(s.layout)
  if (Object.keys(layout).length) props.form.layout_config = layout
  const heading = theme.typography?.heading
  const body = theme.typography?.body
  if (heading) ensureStoreFont(heading)
  if (body) {
    props.form.name_font = body
    ensureStoreFont(body)
  }
  const accent = theme.palette?.accent
  if (accent && advanced.value) props.form.accent_custom = accent
  else if (accent) {
    const slug = nearestAccent(hexToRgb(accent), STORE_ACCENTS)
    if (slug) props.form.accent = slug
  }
}
</script>

<template>
  <div class="dpicks" role="group" aria-labelledby="dpicks-title">
    <div class="dpicks-head">
      <div class="dpicks-title">
        <strong id="dpicks-title"><AppIcon name="layout-grid" :size="15" aria-hidden="true" /> Diseño de tu web</strong>
        <button type="button" class="dpicks-refresh" :disabled="status === 'loading'" @click="load(true)">
          <AppIcon name="refresh" :size="13" /> {{ status === 'loading' ? 'Cargando…' : 'Actualizar' }}
        </button>
      </div>
      <small>Elegí el patrón y el estilo por separado: cualquier combinación funciona.</small>
    </div>
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
  </div>
</template>

<style scoped>
/* Bloque embebido dentro del paso "Estilo y portada": sin card propia, para
   que todo el diseño viva en un solo contenedor. */
.dpicks { display: flex; flex-direction: column; gap: 14px; min-width: 0; height: 100%; container-type: inline-size; }
.dpicks-head { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.dpicks-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; }
.dpicks-refresh {
  display: inline-flex; align-items: center; gap: 5px; flex: none;
  padding: 4px 9px; border: 1px solid var(--line, #e5e7eb); border-radius: 8px;
  background: transparent; color: var(--muted); font-size: 11.5px; font-weight: 600; cursor: pointer;
}
.dpicks-refresh:hover:not(:disabled) { color: var(--ink); border-color: var(--line-2, #cbd5e1); }
.dpicks-refresh:disabled { opacity: .6; cursor: default; }
.dpicks-head strong { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; color: var(--ink); }
.dpicks-head strong .icon { color: var(--brand-600); flex: none; }
.dpicks-head small { font-size: 12.5px; line-height: 1.4; color: var(--muted); }
/* Una columna por defecto (mobile) y dos recién cuando hay ancho real. */
.dpicks-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: stretch; min-width: 0; }
@container (min-width: 520px) { .dpicks-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 20px; } }
.dpicks .field { display: grid; grid-template-rows: auto auto auto auto; gap: 8px; min-width: 0; margin: 0; align-content: start; }
.dpicks .field label { font-size: 13px; font-weight: 600; line-height: 1.3; color: var(--ink-2); }
.dpicks .select { width: 100%; min-width: 0; min-height: 54px; padding: 0 14px; font-size: 16px; text-overflow: ellipsis; }
.dpicks .hint { margin: 0; font-size: 12.5px; line-height: 1.4; color: var(--muted); }
@container (max-width: 380px) {
  .dpicks .select { min-height: 48px; }
}
.dpicks-current { display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; font-weight: 600; color: var(--ink-2); min-width: 0; overflow-wrap: anywhere; }
.dpicks-dot { flex: none; width: 7px; height: 7px; border-radius: 999px; background: var(--brand-500); }
.dpicks-alert { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 0; font-size: 12px; color: var(--danger, #b91c1c); }
.dpicks-alert code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
