// Único punto de lectura de variables de entorno (FRONTEND_RULES §1).
// Vite solo expone variables prefixed con VITE_.
const platformDomain = (import.meta.env.VITE_PLATFORM_DOMAIN || 'localhost').toLowerCase()
const { protocol, hostname, port } = window.location
// Host de la plataforma con su puerto (dev: localhost:5173, prod: davent.com).
const platformHost = `${platformDomain}${port ? `:${port}` : ''}`

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  appName: import.meta.env.VITE_APP_NAME || 'DAVENT',
  appTagline: import.meta.env.VITE_APP_TAGLINE || 'Gestión SaaS para e-commerce tecnológicos',
  platformDomain,
  platformHost,
  // Origen del sitio principal (login, dashboard, legales). Desde un
  // subdominio de tienda las rutas de plataforma viven acá, no en el host actual.
  appUrl: import.meta.env.VITE_APP_URL || `${protocol}//${platformHost}`
}

// Subdominios de infraestructura: nunca son una tienda (además el backend los
// tiene bloqueados como slug en RESERVED_SLUGS).
const PLATFORM_SUBDOMAINS = new Set(['www', 'app', 'api', 'admin', 'panel', 'mail'])

// Si la app se está visitando desde <slug>.<platformDomain> devuelve ese slug
// (la raíz es la web pública de la tienda); si no, null. En dev,
// mitienda.localhost:5173 resuelve a loopback en Chrome/Firefox sin configurar nada.
export const storeHostSlug = (() => {
  const host = hostname.toLowerCase()
  if (host === platformDomain || !host.endsWith(`.${platformDomain}`)) return null
  const sub = host.slice(0, -(platformDomain.length + 1))
  if (!sub || sub.includes('.') || PLATFORM_SUBDOMAINS.has(sub)) return null
  return sub
})()

// Render no enruta ni certifica subdominios wildcard en onrender.com (deploy
// de test): los links públicos usan el alias de path <appUrl>/<slug> hasta
// tener dominio propio con wildcard DNS+TLS en el VPS.
// VITE_STORE_SUBDOMAINS pisa la detección: '0'/'false' fuerza alias de path
// aunque el dominio ya no sea onrender (interim: dominio propio delegado a
// Render, que no soporta wildcard). Vacío/ausente = auto.
const storeSubdomainsEnv = (import.meta.env.VITE_STORE_SUBDOMAINS || '').toLowerCase()
export const storeSubdomains = storeSubdomainsEnv
  ? !['0', 'false', 'no'].includes(storeSubdomainsEnv)
  : !platformDomain.endsWith('onrender.com')

// Link público canónico de una tienda: subdominio propio (<slug>.<dominio>)
// cuando el hosting lo soporta; si no, alias de path sobre el dominio de plataforma.
export function storeUrl(slug) {
  if (!storeSubdomains) return `${env.appUrl}/${slug}`
  return `${protocol}//${slug}.${platformHost}`
}

export function apiUrl(path = '') {
  const base = env.apiBaseUrl.replace(/\/$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}
