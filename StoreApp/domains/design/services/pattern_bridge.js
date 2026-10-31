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
  window.addEventListener('message', function (e) {
    var d = e.data || {}
    if (d.type === 'davent:ds-theme') root.setAttribute('data-ds-theme', d.theme)
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
  window.addEventListener('load', function () { catalog(); send() })
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root)
  else setTimeout(send, 120)
  send()
})()
