/* Puente del documento de diseño (PatternSurface).
 * Se carga desde el documento servido por
 * /api/stores/public/<slug>/pattern/document/ como <script src> (el CSP de
 * producción solo permite script-src 'self'; un script inline no corre).
 *
 * - Mide el documento y avisa el alto al host (el iframe no puede medir el
 *   documento que embebe).
 * - Escucha el tema (claro/oscuro) y la superficie (landing/catalog/services).
 * - Traduce los enlaces del diseño ([data-ds-route]) y las fichas
 *   ([data-ds-product]) a rutas del host.
 * - Resuelve el catálogo en el navegador: filtro por categoría + orden, con
 *   los datos de cada tarjeta en atributos (data-cat/data-price/data-name).
 */
(function () {
  var root = document.documentElement
  function send() {
    // Medir después del frame: al cambiar de superficie el display de los
    // bloques todavía no se recalculó y el alto queda viejo.
    requestAnimationFrame(function () {
      var h = Math.max(root.scrollHeight, document.body ? document.body.scrollHeight : 0)
      parent.postMessage({ type: 'davent:ds-height', height: h }, '*')
    })
  }
  function go(route, id) {
    parent.postMessage({ type: 'davent:ds-route', route: route, id: id || '' }, '*')
  }
  /* Modo noche dentro de la barra de navegación: el interruptor vive en el
   * header del diseño (no flotando sobre la página) y avisa al host para
   * que el tema quede guardado para el visitante. */
  var SUN = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
  var MOON = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z"/></svg>'
  var themeToggle = null
  function currentTheme() {
    return root.getAttribute('data-ds-theme') === 'dark' ? 'dark' : 'light'
  }
  function paintThemeToggle() {
    if (!themeToggle) return
    var dark = currentTheme() === 'dark'
    themeToggle.innerHTML = dark ? SUN : MOON
    themeToggle.setAttribute('aria-label', dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro')
    themeToggle.setAttribute('title', dark ? 'Modo claro' : 'Modo oscuro')
    themeToggle.setAttribute('aria-pressed', dark ? 'true' : 'false')
  }
  function mountThemeToggle() {
    if (themeToggle || document.querySelector('.ds-theme-toggle')) return
    var host =
      document.querySelector('header.top .top-inner') ||
      document.querySelector('header.top .top-in') ||
      document.querySelector('header.top') ||
      document.querySelector('header')
    if (!host) return
    var st = document.createElement('style')
    st.textContent =
      '.ds-theme-toggle{margin-inline-start:auto;display:inline-grid;place-items:center;flex:none;' +
      'width:38px;height:38px;padding:0;border-radius:999px;border:1px solid currentColor;' +
      'background:transparent;color:inherit;opacity:.72;cursor:pointer;' +
      'transition:opacity .18s,transform .18s,background .18s}' +
      '.ds-theme-toggle:hover{opacity:1;transform:translateY(-1px);' +
      'background:color-mix(in srgb,currentColor 10%,transparent)}' +
      '.ds-theme-toggle:focus-visible{outline:2px solid currentColor;outline-offset:2px}'
    document.head.appendChild(st)
    themeToggle = document.createElement('button')
    themeToggle.type = 'button'
    themeToggle.className = 'ds-theme-toggle'
    themeToggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark'
      root.setAttribute('data-ds-theme', next)
      paintThemeToggle()
      parent.postMessage({ type: 'davent:ds-theme-toggle', theme: next }, '*')
      send()
    })
    host.appendChild(themeToggle)
    paintThemeToggle()
  }
  window.addEventListener('message', function (e) {
    var d = e.data || {}
    if (d.type === 'davent:ds-theme') {
      root.setAttribute('data-ds-theme', d.theme)
      paintThemeToggle()
    }
    if (d.type === 'davent:ds-surface') {
      root.setAttribute('data-ds-surface', d.surface)
      catalog()
      window.scrollTo(0, 0)
      send()
      setTimeout(send, 120)
    }
    if (d.type === 'davent:ds-measure') send()
  })

  document.addEventListener('click', function (e) {
    var t = e.target
    if (!t || !t.closest) return
    var card = t.closest('[data-ds-product]')
    if (card) { e.preventDefault(); go('product', card.getAttribute('data-ds-product')); return }
    var link = t.closest('[data-ds-route]')
    if (!link) return
    e.preventDefault()
    go(link.getAttribute('data-ds-route'))
  })
  function catalog() {
    var wrap = document.querySelector('[data-ds-products]')
    if (!wrap) return
    var cards = [].slice.call(wrap.querySelectorAll('.ds-product'))
    var filters = document.querySelector('[data-ds-filters]')
    var sortSel = document.querySelector('[data-ds-sort]')
    var countEl = document.querySelector('[data-ds-count]')
    var noRes = document.querySelector('[data-ds-noresults]')
    var active = filters ? (filters.getAttribute('data-active') || '') : ''
    if (filters && !filters.getAttribute('data-built')) {
      var cats = []
      cards.forEach(function (c) {
        var k = c.getAttribute('data-cat') || ''
        if (k && cats.indexOf(k) < 0) cats.push(k)
      })
      var all = [''].concat(cats)
      all.forEach(function (cat) {
        var b = document.createElement('button')
        b.type = 'button'
        b.className = 'ds-cat'
        b.textContent = cat || 'Todos'
        b.setAttribute('data-cat', cat)
        b.setAttribute('aria-pressed', cat === active ? 'true' : 'false')
        b.addEventListener('click', function () {
          filters.setAttribute('data-active', cat)
          ;[].forEach.call(filters.querySelectorAll('button'), function (o) {
            o.setAttribute('aria-pressed', o.getAttribute('data-cat') === cat ? 'true' : 'false')
          })
          catalog()
        })
        filters.appendChild(b)
      })
      filters.setAttribute('data-built', '1')
    }
    var shown = 0
    cards.forEach(function (c) {
      var ok = !active || (c.getAttribute('data-cat') || '') === active
      c.hidden = !ok
      if (ok) shown++
    })
    if (sortSel) {
      var v = sortSel.value || 'relevance'
      var sorted = cards.slice().sort(function (a, b) {
        if (v === 'price-asc' || v === 'price-desc') {
          var pa = parseFloat(a.getAttribute('data-price')) || 0
          var pb = parseFloat(b.getAttribute('data-price')) || 0
          return v === 'price-asc' ? pa - pb : pb - pa
        }
        if (v === 'name') {
          return (a.getAttribute('data-name') || '').localeCompare(b.getAttribute('data-name') || '')
        }
        return 0
      })
      sorted.forEach(function (c) { wrap.appendChild(c) })
    }
    if (countEl) countEl.textContent = shown + (shown === 1 ? ' producto' : ' productos')
    if (noRes) noRes.hidden = shown > 0
  }
  var sortSel = document.querySelector('[data-ds-sort]')
  if (sortSel) sortSel.addEventListener('change', catalog)
  catalog()
  mountThemeToggle()
  window.addEventListener('load', function () { catalog(); mountThemeToggle(); send() })
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root)
  else setTimeout(send, 120)
  send()
})()
