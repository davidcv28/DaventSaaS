// Elección de diseño en el Studio (contrato nuevo: DesignPattern = HTML/CSS/JS
// con variables; DesignStyle = solo bordes, colores y detalles básicos).
//
// Funciones puras: el panel decide con ellas si el plan alcanza y qué escribir
// en el borrador; los tests las cubren sin montar componentes ni tocar la API.
// El layout llega crudo y se devuelve igual: quien aplica lo normaliza con
// normalizeLayoutConfig (templates/index.js, que arrastra componentes Vue).

export function isTemplateAllowed(template, allowed = []) {
  return Boolean(template) && Array.isArray(allowed) && allowed.includes(template)
}

// El diseño manda la estructura (template + layout_config). Su piel (tokens:
// fuentes y acento) solo se aplica cuando la tienda todavía no eligió estilo:
// un estilo aplicado pisa el tema, no la composición.
export function patternChoice(pattern, { allowed = [], hasStyle = false } = {}) {
  if (!pattern?.template) return null
  if (!isTemplateAllowed(pattern.template, allowed)) {
    return { locked: true, template: pattern.template }
  }
  const choice = {
    locked: false,
    template: pattern.template,
    layout_config: pattern.layout || {}
  }
  if (hasStyle) return choice
  const tokens = pattern.tokens || {}
  const theme = {}
  const fonts = Array.isArray(tokens.fonts) ? tokens.fonts.filter(Boolean) : []
  if (fonts.length) theme.typography = { body: fonts[0], heading: fonts[1] || fonts[0] }
  const palette = { ...(tokens.palette || {}) }
  if (tokens.accent) palette.accent = tokens.accent
  if (Object.keys(palette).length) theme.palette = palette
  if (Object.keys(theme).length) choice.site_theme = theme
  return choice
}

// El estilo es un tema: colores, bordes, sombras, densidad, tipografía y
// botones. Nunca toca template ni layout (eso es del diseño).
export function styleChoice(style, { allowed = [] } = {}) {
  if (!style?.slug) return null
  if (style.template && !isTemplateAllowed(style.template, allowed)) {
    return { locked: true, template: style.template }
  }
  return {
    locked: false,
    style_id: style.slug,
    page_theme: style.page_theme === 'dark' ? 'dark' : 'light',
    site_theme: { ...(style.tokens || {}), style: { id: style.slug } }
  }
}

// Set de iconos de los controles: vacío = hereda el del diseño. Un slug que
// ya no existe en el catálogo vuelve a heredar en vez de romper el chrome.
export function iconChoice(slug, { options = [] } = {}) {
  const value = String(slug || '').trim()
  if (!value) return { icon_style: '' }
  return { icon_style: Array.isArray(options) && options.includes(value) ? value : '' }
}

// Payload del guardado: borrador (*_draft) vs publicado. `template` solo
// viaja como borrador cuando cambió respecto de lo guardado.
export function savePayloadPlan({
  asDraft = false,
  formTemplate = '',
  savedTemplate = '',
  trialTemplate = '',
  siteTheme = null,
  layoutConfig = null
} = {}) {
  const plan = {}
  const changed = Boolean(trialTemplate) || (formTemplate !== savedTemplate && Boolean(formTemplate))
  if (asDraft) {
    if (changed) plan.template_draft = trialTemplate || formTemplate
  } else {
    plan.template = trialTemplate || formTemplate
  }
  if (siteTheme && typeof siteTheme === 'object' && Object.keys(siteTheme).length) {
    plan[asDraft ? 'site_theme_draft' : 'site_theme'] = siteTheme
  }
  if (layoutConfig && typeof layoutConfig === 'object' && Object.keys(layoutConfig).length) {
    plan[asDraft ? 'layout_config_draft' : 'layout_config'] = layoutConfig
  }
  return plan
}
