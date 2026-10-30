// Tema claro/oscuro de la web pública: resolución del tema efectivo y
// persistencia de la elección del visitante (una clave por tienda).
// El modo noche es universal: el interruptor está en todas las webs y solo
// define el tema con el que arranca un visitante nuevo.

export const STORE_THEME_KEY = (slug) => `davent:store-theme:${slug}`

export function readVisitorTheme(storage, slug) {
  try {
    const saved = storage?.getItem(STORE_THEME_KEY(slug))
    return saved === 'light' || saved === 'dark' ? saved : null
  } catch { return null }
}

export function persistVisitorTheme(storage, slug, theme) {
  try { storage?.setItem(STORE_THEME_KEY(slug), theme) } catch { /* modo privado */ }
}

// Tema efectivo: el del Studio (preview) > el elegido por el visitante > el
// default del negocio > prefers-color-scheme.
export function resolveStoreTheme({ studio, studioView, visitor, storeDefault, prefersDark }) {
  if (studio && studioView) return studio
  if (visitor === 'light' || visitor === 'dark') return visitor
  if (storeDefault === 'light' || storeDefault === 'dark') return storeDefault
  return prefersDark ? 'dark' : 'light'
}
