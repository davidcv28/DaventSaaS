import { http } from './http.js'

// Dominio design (StoreApp): catálogo de patrones y estilos en la base.
// El front no guarda presets: pide el catálogo y aplica lo que devuelve.
//
// GET /design/catalog/          público -> {pattern, style, patterns, styles}
//     pattern/style = predeterminados de la plataforma (los aplica la web
//     del cliente cuando la tienda no eligió nada).
// GET /design/styles/           Bearer -> paginado (filtros categoria, tag, q)
// GET /design/styles/<slug>/    Bearer -> detalle (tokens, layout, template)
// GET /design/styles/default/   público -> estilo base
// GET /design/patterns/         Bearer -> paginado (sin html/css/js)
// GET /design/patterns/<slug>/  Bearer -> detalle (html, css, js, layout)
// GET /design/patterns/default/ público -> patrón base
// GET /design/icon-styles/      Bearer -> sets de iconos de controles
// GET /design/icon-styles/default/ público -> set base

function unwrap(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export const designApi = {
  async catalog() {
    const { data } = await http.get('/design/catalog/')
    return data
  },
  async listStyles(params = {}) {
    const { data } = await http.get('/design/styles/', { params: { page_size: 200, ...params } })
    return unwrap(data)
  },
  async listPatterns(params = {}) {
    const { data } = await http.get('/design/patterns/', { params: { page_size: 200, ...params } })
    return unwrap(data)
  },
  async style(slug) {
    const { data } = await http.get(`/design/styles/${slug}/`)
    return data
  },
  async pattern(slug) {
    const { data } = await http.get(`/design/patterns/${slug}/`)
    return data
  },
  // Diseño fuente con datos de ejemplo (sin placeholders {{variable}}).
  async patternPreview(slug) {
    const { data } = await http.get(`/design/patterns/${slug}/preview/`)
    return data
  },
  async defaultStyle() {
    const { data } = await http.get('/design/styles/default/')
    return data
  },
  async defaultPattern() {
    const { data } = await http.get('/design/patterns/default/')
    return data
  },
  async listIconStyles(params = {}) {
    const { data } = await http.get('/design/icon-styles/', { params: { page_size: 200, ...params } })
    return unwrap(data)
  },
  async iconStyle(slug) {
    const { data } = await http.get(`/design/icon-styles/${slug}/`)
    return data
  },
  async defaultIconStyle() {
    const { data } = await http.get('/design/icon-styles/default/')
    return data
  }
}
