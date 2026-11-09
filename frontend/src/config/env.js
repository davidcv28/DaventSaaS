// Único punto de lectura de variables de entorno (FRONTEND_RULES §1).
// Vite solo expone variables prefixed con VITE_.
const platformDomain = (import.meta.env.VITE_PLATFORM_DOMAIN || 'localhost').toLowerCase()
const { protocol, hostname, port } = window.location
// Host de la plataforma con su puerto (dev: localhost:5173, prod: davent.com).
const platformHost = `${platformDomain}${port ? `:${port}` : ''}`
// Host base de los subdominios de tienda: platformDomain sin 'www.' inicial
// (dev: localhost:5173 → mitienda.localhost:5173).
const subdomainHost = platformHost.replace(/^www\./, '')

export const env = {
  //Fallback relativo: si un build olvida VITE_API_BASE_URL, la SPA le pega
  //al mismo origen (nginx/Render proxya /api) en vez de a localhost.
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  appName: import.meta.env.VITE_APP_NAME || 'DAVENT',
  appTagline: import.meta.env.VITE_APP_TAGLINE || 'Gestión SaaS para e-commerce tecnológicos',
  platformDomain,
  platformHost,
  // Origen del sitio principal (login, dashboard, legales). Desde un
  // subdominio de tienda las rutas de plataforma viven acá, no en el host actual.
  appUrl: import.meta.env.VITE_APP_URL || `${protocol}//${platformHost}`,
  // URL estable de descarga de la APK (distribución web directa). El server
  // publica la vigente vía GET /api/config/ (bloque 'app') — este valor es el
  // fallback cuando todavía no hay metadata o el endpoint no responde.
  appApkUrl: import.meta.env.VITE_APP_APK_URL || 'https://pub-7d2a1621ac1a4e648ff0c8756f2781b9.r2.dev/apk/davent-latest.apk'
}

// Subdominios de infraestructura: nunca son una tienda (además el backend los
// tiene bloqueados como slug en RESERVED_SLUGS).
const PLATFORM_SUBDOMAINS = new Set(['www', 'app', 'api', 'admin', 'panel', 'mail'])

// Si la app se está visitando desde <slug>.<platformDomain> devuelve ese slug
// (la raíz es la web pública de la tienda); si no, null. En dev,
// mitienda.localhost:5173 resuelve a loopback en Chrome/Firefox sin configurar nada.
// `let` + setter: un dominio propio (ver abajo) resuelve su slug contra la
// API después del boot — los import leen el binding en vivo.
export let storeHostSlug = (() => {
  const host = hostname.toLowerCase()
  if (host === platformDomain || !host.endsWith(`.${platformDomain}`)) return null
  const sub = host.slice(0, -(platformDomain.length + 1))
  if (!sub || sub.includes('.') || PLATFORM_SUBDOMAINS.has(sub)) return null
  return sub
})()

// Dominio propio del cliente (mitienda.com CNAME -> plataforma): el host no
// es la plataforma ni un subdominio de ella. El slug lo confirma la API
// (/stores/domain/resolve/) recién en StorePublicLayout — hasta entonces la
// web solo sabe que el host ES candidato a tienda.
export const customDomainHost = (() => {
  if (storeHostSlug) return null
  const host = hostname.toLowerCase()
  if (!host || host === 'localhost') return null
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return null // IPv4 literal
  if (host === platformDomain || host.endsWith(`.${platformDomain}`)) return null
  // Con platformDomain 'localhost' (dev), solo un host con TLD real o
  // *.localhost califica — evita tratar la IP o '127.0.0.1' como tienda.
  if (!host.includes('.')) return null
  return host
})()

// ¿Este host sirve la web pública de una tienda? (subdominio o dominio propio).
// Lo leen el router (árbol de rutas) y el guard que redirige a appUrl.
export const isStoreHost = Boolean(storeHostSlug || customDomainHost)

export function setStoreHostSlug(slug) {
  storeHostSlug = slug || null
}

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

// Link público canónico de una tienda: subdominio <slug>.<dominio> cuando
// storeSubdomains está activo; si no (Render/interino), alias de path
// <appUrl>/<slug>. Los subdominios ya emitidos siguen resolviendo vía
// storeHostSlug.
export function storeUrl(slug) {
  if (!storeSubdomains) return `${env.appUrl}/${slug}`
  return `${protocol}//${slug}.${subdomainHost}`
}

// Prefijo/sufijo del input de slug según el modo de link público: en
// subdominio el slug va entre 'https://' y '.<dominio>'; en alias de path,
// entre '<appUrl>/' y nada.
export function storeSlugAffixes() {
  return storeSubdomains
    ? { prefix: `${protocol}//`, suffix: `.${subdomainHost}` }
    : { prefix: `${env.appUrl}/`, suffix: '' }
}

export function apiUrl(path = '') {
  const base = env.apiBaseUrl.replace(/\/$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}
