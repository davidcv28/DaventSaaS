import { computed, reactive, ref } from 'vue'
import { designApi } from '../api/design.api.js'

// Catálogo de diseño (patrones + estilos) servido por la API.
// Una sola descarga por sesión, compartida por la web pública y el Studio:
// ni los presets ni los layouts viven ya en el front.
const catalog = reactive({
  status: 'idle', // idle | loading | success | error
  pattern: null,
  style: null,
  patterns: [],
  styles: [],
  iconStyles: [],
  defaultIconStyle: null
})

// Presets del Studio: misma forma que la galería espera, armada desde la base.
const presets = reactive([])
const loaded = ref(false)
let inflight = null

export function styleToPreset(style) {
  if (!style) return null
  return {
    id: style.slug,
    name: style.nombre,
    style: style.categoria,
    desc: style.descripcion || '',
    tier: style.tier || 'base',
    template: style.template || '',
    pattern: style.pattern || '',
    pageTheme: style.page_theme || 'light',
    theme: style.tokens || {},
    layout: style.layout || {},
    layoutSpec: style.layout_spec || {},
    rubros: style.tags || []
  }
}

function fillPresets(styles) {
  presets.splice(0, presets.length, ...styles.map(styleToPreset).filter(Boolean))
}

export function useDesignCatalog() {
  async function load(force = false) {
    if (loaded.value && !force) return catalog
    if (inflight) return inflight
    catalog.status = 'loading'
    inflight = designApi.catalog()
      .then((data) => {
        catalog.pattern = data?.pattern || null
        catalog.style = data?.style || null
        catalog.patterns = data?.patterns || []
        catalog.styles = data?.styles || []
        catalog.iconStyles = data?.icon_styles || []
        catalog.defaultIconStyle = data?.default_icon_style || null
        catalog.status = 'success'
        loaded.value = true
        fillPresets(catalog.styles)
        return catalog
      })
      .catch(() => {
        catalog.status = 'error'
        return catalog
      })
      .finally(() => { inflight = null })
    return inflight
  }

  return {
    catalog,
    presets,
    load,
    status: computed(() => catalog.status),
    defaultPattern: computed(() => catalog.pattern),
    defaultStyle: computed(() => catalog.style),
    styles: computed(() => catalog.styles),
    patterns: computed(() => catalog.patterns),
    iconStyles: computed(() => catalog.iconStyles),
    defaultIconStyle: computed(() => catalog.defaultIconStyle),
    // Estilos propios de un diseño (FK DesignStyle.pattern): sin diseño
    // devuelve el catálogo completo.
    stylesForPattern: (slug) => (
      slug ? catalog.styles.filter((row) => !row.pattern || row.pattern === slug) : catalog.styles
    ),
    iconStyleBySlug: (slug) => catalog.iconStyles.find((row) => row.slug === slug) || null
  }
}
