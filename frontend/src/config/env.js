// Único punto de lectura de variables de entorno (FRONTEND_RULES §1).
// Vite solo expone variables prefixed con VITE_.
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  appName: import.meta.env.VITE_APP_NAME || 'DAVENT',
  appTagline: import.meta.env.VITE_APP_TAGLINE || 'Gestión SaaS para e-commerce tecnológicos'
}

export function apiUrl(path = '') {
  const base = env.apiBaseUrl.replace(/\/$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}
