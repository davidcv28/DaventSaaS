// Aplica el tema antes del primer paint para evitar flash claro/oscuro.
// Vive como archivo externo (no inline) para que nginx pueda servir
// script-src 'self' sin 'unsafe-inline' en la CSP.
// Solo el panel de administración (/admin) es siempre oscuro; el panel de
// cliente (/dashboard) respeta la elección guardada y, si no hay, la del SO.
;(function () {
  var admin = /^\/admin(\/|$)/.test(location.pathname)
  var t = null
  try { t = localStorage.getItem('davent:theme') } catch (e) {}
  if (t !== 'dark' && t !== 'light') t = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  if (admin) t = 'dark'
  document.documentElement.dataset.theme = t
  if (t === 'dark') document.querySelector('meta[name="theme-color"]').setAttribute('content', '#0d1220')
})()
