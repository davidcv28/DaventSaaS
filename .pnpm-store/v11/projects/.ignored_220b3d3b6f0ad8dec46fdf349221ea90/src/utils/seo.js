// Meta tags de la web pública: se aplican sobre el <head> y se restauran al
// salir de la tienda (la SPA comparte el mismo index.html con el dashboard).
const JSONLD_ID = 'store-jsonld'

function upsert(attr, key, content, created, restore) {
  let el = document.head.querySelector(`meta[${attr}="${key}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
    created.push(el)
  } else if (!restore.has(el)) {
    restore.set(el, el.getAttribute('content'))
  }
  el.setAttribute('content', content)
}

export function applySeo({ title, description, image, url, type = 'business.business', themeColor, jsonLd }) {
  const created = []
  const restore = new Map()
  const set = (attr, key, value) => { if (value) upsert(attr, key, value, created, restore) }
  const abs = (u) => (u ? new URL(u, window.location.origin).href : '')
  const img = abs(image)
  set('name', 'description', description)
  set('property', 'og:type', type)
  set('property', 'og:site_name', title)
  set('property', 'og:title', title)
  set('property', 'og:description', description)
  set('property', 'og:url', url)
  set('property', 'og:locale', 'es_AR')
  set('property', 'og:image', img)
  set('name', 'twitter:card', img ? 'summary_large_image' : 'summary')
  set('name', 'twitter:title', title)
  set('name', 'twitter:description', description)
  set('name', 'twitter:image', img)
  set('name', 'theme-color', themeColor)
  let script = null
  if (jsonLd) {
    script = document.createElement('script')
    script.type = 'application/ld+json'
    script.id = JSONLD_ID
    script.textContent = JSON.stringify(jsonLd).replace(/</g, '\\u003c')
    document.head.appendChild(script)
  }
  return () => {
    created.forEach((el) => el.remove())
    restore.forEach((content, el) => (content == null ? el.removeAttribute('content') : el.setAttribute('content', content)))
    script?.remove()
  }
}
