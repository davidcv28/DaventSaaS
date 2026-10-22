// Aplica el tema antes del primer paint para evitar flash claro/oscuro.
// Vive como archivo externo (no inline) para que nginx pueda servir
// script-src 'self' sin 'unsafe-inline' en la CSP.
;(function () {
  var t = null
  try { t = localStorage.getItem('davent:theme') } catch (e) {}
  if (t !== 'dark' && t !== 'light') t = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  document.documentElement.dataset.theme = t
  if (t === 'dark') document.querySelector('meta[name="theme-color"]').setAttribute('content', '#0d1220')
})()
