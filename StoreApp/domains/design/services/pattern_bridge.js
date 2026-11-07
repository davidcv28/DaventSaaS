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
  /* Sección cuya zona de datos quedó vacía: la regla
   * `[data-flag]:has(.ds-zone:empty)` del diseño la apaga, pero donde
   * `:has()` no llega la cáscara (título + paddings) quedaba visible y
   * varias seguidas dejaban un hueco enorme. Refuerzo por DOM: solo
   * apaga, nunca enciende (el toggle del dueño sigue mandando). */
  function hideEmptyZones() {
    ;[].forEach.call(document.querySelectorAll('.ds-zone'), function (z) {
      if (z.children.length || (z.textContent || '').trim()) return
      var sec = z.closest('[data-flag]')
      if (sec) sec.hidden = true
    })
  }
  function send() {
    hideEmptyZones()
    // Medir después del frame: al cambiar de superficie el display de los
    // bloques todavía no se recalculó y el alto queda viejo.
    requestAnimationFrame(function () {
      /* `scrollHeight` nunca baja del viewport del iframe: al pasar de una
       * superficie larga (landing) a una corta (catálogo) el alto quedaba
       * clavado en el anterior y el pie flotaba sobre un hueco enorme. Se
       * mide el borde inferior del pie (o del último bloque en flujo), que
       * sí es el alto real del contenido. */
      var h = 0
      var foot = document.querySelector('footer')
      if (foot && foot.getClientRects().length) {
        var fr = foot.getBoundingClientRect()
        if (fr.height) h = fr.bottom + (window.scrollY || 0)
      }
      if (!h && document.body) {
        var kids = document.body.children
        for (var i = kids.length - 1; i >= 0; i--) {
          var el = kids[i]
          if (!el || el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'LINK') continue
          var cs = window.getComputedStyle(el)
          if (cs.position === 'fixed' || cs.display === 'none') continue
          var r = el.getBoundingClientRect()
          if (r.height > 0) { h = r.bottom + (window.scrollY || 0); break }
        }
        if (!h) h = document.body.scrollHeight
      }
      if (!h) h = root.scrollHeight
      parent.postMessage({ type: 'davent:ds-height', height: h }, '*')
    })
  }
  function go(route, id) {
    parent.postMessage({ type: 'davent:ds-route', route: route, id: id || '' }, '*')
  }
  /* Datos de la API pública (captcha y opiniones del producto).
   *
   * El iframe va sandboxeado SIN `allow-same-origin`: el documento tiene
   * origen opaco y un `fetch` propio a la API de la tienda sería
   * cross-origin (bloqueado por CORS/CORP). El pedido viaja al host —que sí
   * es mismo origen— y vuelve por `davent:ds-api-result`. El host valida la
   * URL contra su propia tienda antes de pedirla: el documento nunca elige
   * a qué endpoint se le pega.
   *
   * `api(url, {method, body})` resuelve `{ok, data}` o `null` (sin host o
   * timeout). */
  var apiSeq = 0
  var apiPending = {}
  function api(url, options) {
    options = options || {}
    return new Promise(function (resolve) {
      if (!url || !window.parent || window.parent === window) { resolve(null); return }
      var id = 'ds' + (++apiSeq)
      apiPending[id] = resolve
      parent.postMessage({
        type: 'davent:ds-api',
        id: id,
        url: String(url),
        method: options.method === 'POST' ? 'POST' : 'GET',
        body: options.body || null
      }, '*')
      setTimeout(function () {
        if (apiPending[id]) { delete apiPending[id]; resolve(null) }
      }, 15000)
    })
  }
  window.addEventListener('message', function (e) {
    if (e.source !== window.parent) return
    var data = e.data || {}
    if (data.type !== 'davent:ds-api-result') return
    var done = apiPending[data.id]
    if (!done) return
    delete apiPending[data.id]
    done(data.result || null)
  })
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
      'width:44px;height:44px;padding:0;border-radius:999px;border:1px solid currentColor;' +
      'background:transparent;color:inherit;opacity:.72;cursor:pointer;' +
      'transition:opacity .18s,transform .18s,background .18s}' +
      '.ds-theme-toggle:hover{opacity:1;transform:translateY(-1px);' +
      'background:color-mix(in srgb,currentColor 10%,transparent)}' +
      '.ds-theme-toggle:focus-visible{outline:2px solid currentColor;outline-offset:2px}' +
      '@media (prefers-reduced-motion:reduce){.ds-theme-toggle{transition:none}' +
      '.ds-theme-toggle:hover{transform:none}}'
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
  /* Barras fijas dentro del iframe estirado: el host manda el rectángulo
   * del marco (`davent:ds-frame`) y acá se compensan con top/bottom — nunca
   * transform, para no romper las hojas que animan translateY (.m-sheet).
   * Se cachea la lista y se re-mide si el documento cambia de tamaño. */
  var frameBox = null
  var pinned = null
  var pinnedIh = 0
  function collectFixed() {
    /* Antes de medir hay que soltar los top/bottom aplicados por el pin:
     * el rect se toma de la posición NATURAL del CSS (abajo del documento
     * para la tab bar). Medir con el pin puesto devolvía un base gigante
     * y la barra quedaba clavada en top:0 para siempre. */
    if (pinned) pinned.forEach(function (p) { p.el.style.top = ''; p.el.style.bottom = '' })
    pinned = []
    if (!document.body || !window.getComputedStyle) return
    var ih = window.innerHeight || 1
    pinnedIh = ih
    ;[].forEach.call(document.body.querySelectorAll('*'), function (el) {
      var cs = getComputedStyle(el)
      if (cs.position !== 'fixed') return
      /* `top`/`bottom` computados siempre resuelven a píxeles para un
       * elemento fijo, así que no dicen a qué borde está anclado: una tab
       * bar con `bottom:12px` devuelve `top: ~4865px` (alto del documento)
       * y quedaba clavada al fondo de la página — invisible hasta el
       * final. El anclaje real sale del rectángulo: si el borde inferior
       * está cerca del borde inferior del viewport y el elemento no llega
       * a la mitad superior, es de abajo. */
      var r = el.getBoundingClientRect()
      /* El anclaje se puede declarar a mano (`data-ds-pin="top|bottom"`):
       * la heurística por rectángulo depende del viewport del momento y
       * una medición temprana (iframe sin estirar) salía invertida. La
       * `base` queda en null si el rect está vacío (display:none / aún
       * sin layout): se mide perezosa en pinFixed, nunca de un rect nulo. */
      var hint = (el.getAttribute('data-ds-pin') || '').toLowerCase()
      if (hint !== 'bottom' && ih - r.bottom < ih * 0.25 && r.top > ih * 0.5) hint = 'bottom'
      if (hint === 'bottom') {
        var ty = 0
        var m = /matrix\([^)]*,\s*(-?[\d.]+)\s*\)/.exec(cs.transform || '')
        if (m) ty = parseFloat(m[1]) || 0
        var base = (r.width || r.height) ? Math.max(0, ih - (r.bottom - ty)) : null
        pinned.push({ el: el, prop: 'bottom', base: base })
      } else {
        pinned.push({ el: el, prop: 'top', base: parseFloat(cs.top) || 0 })
      }
    })
  }
  /* Invalida la medición soltando ANTES los top/bottom aplicados: si se
   * nulea `pinned` sin limpiar, collectFixed re-mide con el pin puesto y
   * la base sale gigante — la barra queda clavada en top:0 para siempre. */
  function resetFixed() {
    ;(pinned || []).forEach(function (p) { p.el.style.top = ''; p.el.style.bottom = '' })
    pinned = null
  }
  function pinFixed() {
    if (!frameBox) return
    /* Si el iframe cambió de alto desde la medición (pasa de ~150px al
     * alto completo del documento), la clasificación anterior es inválida:
     * una tab bar medida con viewport chico puede salir como 'top' y quedar
     * clavada al tope del documento. Se limpian los estilos aplicados —
     * si no, el rect mediría la posición ya compensada — y se re-mide. */
    var ih = window.innerHeight || 1
    if (pinned && Math.abs(ih - pinnedIh) > 2) resetFixed()
    if (!pinned) collectFixed()
    var dyTop = Math.max(0, -frameBox.top)
    var dyBot = Math.max(0, frameBox.bottom - frameBox.vh)
    ;(pinned || []).forEach(function (p) {
      if (p.prop === 'bottom') {
        /* Posición directa por `top`: el borde visible inferior dentro del
         * documento del iframe es min(vh-top, bottom-top); el elemento se
         * apoya ahí respetando su margen original (base). La base se mide
         * acá si todavía no se pudo (display:none temprano): sin estilos
         * aplicados el rect vuelve a la posición natural del CSS. */
        if (p.base == null) {
          p.el.style.top = ''
          p.el.style.bottom = ''
          var cs2 = getComputedStyle(p.el)
          var r2 = p.el.getBoundingClientRect()
          if (!r2.width && !r2.height) return
          var ty2 = 0
          var m2 = /matrix\([^)]*,\s*(-?[\d.]+)\s*\)/.exec(cs2.transform || '')
          if (m2) ty2 = parseFloat(m2[1]) || 0
          var ih2 = window.innerHeight || 1
          p.base = Math.max(0, ih2 - (r2.bottom - ty2))
        }
        var docBot = Math.min(frameBox.vh - frameBox.top, frameBox.bottom - frameBox.top)
        /* `bottom` hay que neutralizarlo ('auto'), no limpiarlo (''): con
         * '' vuelve el bottom del CSS y top+bottom estiran el elemento a
         * todo el documento. El alto se mide DESPUÉS de soltar el bottom —
         * si no, offsetHeight informa el documento entero. */
        p.el.style.bottom = 'auto'
        p.el.style.top = Math.max(0, docBot - p.el.offsetHeight - p.base) + 'px'
      } else {
        p.el.style.bottom = ''
        p.el.style.top = (p.base + dyTop) + 'px'
      }
    })
  }
  window.addEventListener('resize', function () { resetFixed(); pinFixed() })

  window.addEventListener('message', function (e) {
    var d = e.data || {}
    if (d.type === 'davent:ds-theme') {
      root.setAttribute('data-ds-theme', d.theme)
      paintThemeToggle()
    }
    if (d.type === 'davent:ds-surface') {
      root.setAttribute('data-ds-surface', d.surface)
      var openPanel = document.querySelector('[data-ds-filters-panel].is-open')
      if (openPanel) {
        openPanel.classList.remove('is-open')
        var openToggle = document.querySelector('[data-ds-filters-toggle]')
        if (openToggle) openToggle.setAttribute('aria-expanded', 'false')
        document.body.classList.remove('filters-open')
      }
      catalog()
      resetFixed()
      pinFixed()
      window.scrollTo(0, 0)
      send()
      setTimeout(send, 120)
    }
    if (d.type === 'davent:ds-measure') send()
    if (d.type === 'davent:ds-frame') {
      frameBox = { top: Number(d.top) || 0, bottom: Number(d.bottom) || 0, vh: Number(d.vh) || 0 }
      pinFixed()
    }
  })

  document.addEventListener('click', function (e) {
    var t = e.target
    if (!t || !t.closest) return
    /* Alto del chrome fijo del diseño (masthead + pestañas) para que el
     * host deje el destino debajo y no tapado. Opt-in: sin atributo, 72. */
    var scrollOffset = function () {
      var host = document.querySelector('[data-ds-offset]')
      var n = parseInt((host && host.getAttribute('data-ds-offset')) || '', 10)
      return n > 0 ? n : 72
    }
    var card = t.closest('[data-ds-product]')
    if (card) { e.preventDefault(); go('product', card.getAttribute('data-ds-product')); return }
    /* Redirects de contacto (/r/whatsapp|instagram|…): el anchor viaja sin
     * target y el iframe navegaría él mismo al 302 — instagram/wa.me mandan
     * X-Frame-Options y el documento entero queda en "refused to connect".
     * El host lo abre en pestaña nueva (fuera del sandbox). */
    var anchor = t.closest('a[href]')
    if (anchor && /^\/api\/stores\/public\/[a-z0-9-]+\/r\/[a-z]+\/?/.test(anchor.getAttribute('href') || '')) {
      e.preventDefault()
      parent.postMessage({ type: 'davent:ds-open', url: anchor.getAttribute('href') }, '*')
      return
    }
    /* Enlaces de sección del chrome (Suscripciones, Contacto): si el
     * destino existe y se ve en la superficie actual, scrollean dentro del
     * documento. `data-ds-route` sigue mandando cuando la sección está en
     * otra superficie (p. ej. desde el catálogo se vuelve al inicio). */
    var section = t.closest('[data-ds-anchor]')
    if (section && anchor) {
      var hash = anchor.getAttribute('href') || ''
      var sectionEl = hash.charAt(0) === '#' ? document.getElementById(hash.slice(1)) : null
      if (sectionEl && sectionEl.getClientRects().length) {
        e.preventDefault()
        parent.postMessage({ type: 'davent:ds-scroll', top: sectionEl.getBoundingClientRect().top + (window.scrollY || 0), offset: scrollOffset() }, '*')
        return
      }
    }
    /* Marca del escaparate -> catálogo filtrado: el nombre viaja en
     * `data-ds-brand` (mismo valor que `data-brand` de las tarjetas) y se
     * fija ANTES de que `data-ds-route` navegue a la superficie catálogo,
     * que aplica los filtros al activarse. */
    var brandHit = t.closest('[data-ds-brand]')
    if (brandHit) {
      var brandName = brandHit.getAttribute('data-ds-brand') || ''
      state.brands = brandName ? [brandName] : []
      saveState()
      if (root.getAttribute('data-ds-surface') === 'catalog') {
        syncFilterUI()
        applyCatalog()
      }
    }
    var link = t.closest('[data-ds-route]')
    if (link) {
      e.preventDefault()
      go(link.getAttribute('data-ds-route'))
      return
    }
    /* Anchor interno (#contacto): el iframe se estira al alto del documento
     * y no scrollea por dentro — el scroll real es de la página host. Se
     * manda la posición del destino y el host hace scrollTo. */
    if (anchor) {
      var href = anchor.getAttribute('href') || ''
      if (href.charAt(0) === '#' && href.length > 1) {
        var targetEl = document.getElementById(href.slice(1))
        if (targetEl) {
          e.preventDefault()
          parent.postMessage({ type: 'davent:ds-scroll', top: targetEl.getBoundingClientRect().top + (window.scrollY || 0), offset: scrollOffset() }, '*')
        }
      }
    }
  })
  /* ------------------------------------------------------------------
   * Catálogo + búsqueda del marketplace.
   * El documento es estático: las tarjetas viajan con data-cat/data-price/
   * data-name y acá se filtran por texto, categoría, rango de precio y
   * ofertas, se ordenan y se resuelven las sugerencias del buscador.
   * ------------------------------------------------------------------ */
  var state = { q: '', cat: '', brands: [], min: '', max: '', offers: false }
  var cards = []
  var wrap = null
  var catNames = []
  var activeSuggest = -1
  var suggestItems = []
  var applyTimer = 0
  var STORE_KEY = 'davent:ds-search:' + (typeof location !== 'undefined' ? location.pathname : '')
  var VIEW_KEY = 'davent:ds-view:' + (typeof location !== 'undefined' ? location.pathname : '')

  function textOf(el) {
    return el ? String(el.textContent || '').trim() : ''
  }
  function norm(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
  }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
    })
  }
  function money(value) {
    var n = parseFloat(value)
    return isFinite(n) && n > 0 ? '$' + n.toLocaleString('es-AR') : 'Consultar'
  }
  function numOrNull(value) {
    if (value === '' || value == null) return null
    var n = parseFloat(value)
    return isFinite(n) ? n : null
  }
  /* Estado de la sesión del documento (filtros del catálogo y vista).
   * Con el iframe en origen opaco `sessionStorage` no existe y el acceso
   * lanza: la memoria del documento cubre el lapso mientras la pestaña
   * siga viva, sin romper nada cuando el storage sí está disponible. */
  var memoryStore = {}
  function storeGet(key) {
    try { return sessionStorage.getItem(key) } catch (e) { return memoryStore[key] || null }
  }
  function storeSet(key, value) {
    try { sessionStorage.setItem(key, value) } catch (e) { memoryStore[key] = value }
  }
  function saveState() {
    storeSet(STORE_KEY, JSON.stringify(state))
  }
  function restoreState() {
    try {
      var raw = storeGet(STORE_KEY)
      if (!raw) return
      var saved = JSON.parse(raw) || {}
      if (typeof saved.q === 'string') state.q = saved.q
      if (typeof saved.cat === 'string') state.cat = saved.cat
      if (Array.isArray(saved.brands)) state.brands = saved.brands.filter(function (b) { return typeof b === 'string' })
      if (typeof saved.min === 'string') state.min = saved.min
      if (typeof saved.max === 'string') state.max = saved.max
      state.offers = saved.offers === true
    } catch (e) {}
  }
  function matchesQuery(card, query) {
    var terms = norm(query).split(/\s+/).filter(Boolean)
    if (!terms.length) return true
    var hay = norm(card.textContent)
    for (var i = 0; i < terms.length; i++) {
      if (hay.indexOf(terms[i]) < 0) return false
    }
    return true
  }
  function matchesFilters(card) {
    if (state.cat && (card.getAttribute('data-cat') || '') !== state.cat) return false
    if (state.brands.length) {
      var brand = card.getAttribute('data-brand') || ''
      if (state.brands.indexOf(brand) < 0) return false
    }
    if (state.offers && !card.querySelector('.ds-product-old')) return false
    var price = parseFloat(card.getAttribute('data-price')) || 0
    var min = numOrNull(state.min)
    var max = numOrNull(state.max)
    if (min != null && price < min) return false
    if (max != null && price > max) return false
    return matchesQuery(card, state.q)
  }
  function filterCount() {
    return (state.cat ? 1 : 0) + state.brands.length + (state.offers ? 1 : 0) +
      (state.min !== '' || state.max !== '' ? 1 : 0) + (state.q.trim() ? 1 : 0)
  }
  function syncFilterUI() {
    var filters = document.querySelector('[data-ds-filters]')
    if (filters) {
      ;[].forEach.call(filters.querySelectorAll('button'), function (btn) {
        var on = btn.getAttribute('data-cat') === state.cat
        btn.setAttribute('aria-pressed', on ? 'true' : 'false')
        if (btn.classList.contains('f-cat')) btn.classList.toggle('is-active', on)
      })
    }
    var brands = document.querySelector('[data-ds-brands]')
    if (brands) {
      ;[].forEach.call(brands.querySelectorAll('input[type="checkbox"]'), function (input) {
        input.checked = state.brands.indexOf(input.value) >= 0
      })
    }
    var minInput = document.querySelector('[data-ds-price-min]')
    var maxInput = document.querySelector('[data-ds-price-max]')
    var offersInput = document.querySelector('[data-ds-offers]')
    // Con "Aplicar" el rango escrito queda pendiente hasta confirmarlo: no
    // se pisa al tocar otra sección del panel.
    if (!document.querySelector('[data-ds-price-apply]')) {
      if (minInput) minInput.value = state.min
      if (maxInput) maxInput.value = state.max
    }
    if (offersInput) offersInput.checked = !!state.offers
    var badge = document.querySelector('[data-ds-filter-count]')
    if (badge) {
      var n = filterCount()
      badge.textContent = String(n)
      badge.hidden = n === 0
    }
    var crumb = document.querySelector('[data-ds-crumb]')
    if (crumb) crumb.textContent = state.cat || (state.q.trim() ? '“' + state.q.trim() + '”' : 'Todos los productos')
    renderChips()
  }
  /* Chips de filtros activos: opt-in del diseño (`[data-ds-chips]`). Cada
   * chip quita su propio filtro; con dos o más aparece "Limpiar todo". */
  function removeChip(kind, value) {
    if (kind === 'all') { resetFilters(); return }
    if (kind === 'cat') state.cat = ''
    else if (kind === 'brand') {
      var i = state.brands.indexOf(value)
      if (i >= 0) state.brands.splice(i, 1)
    } else if (kind === 'offers') state.offers = false
    else if (kind === 'price') {
      state.min = ''
      state.max = ''
      var minInput = document.querySelector('[data-ds-price-min]')
      var maxInput = document.querySelector('[data-ds-price-max]')
      if (minInput) minInput.value = ''
      if (maxInput) maxInput.value = ''
    } else if (kind === 'q') {
      state.q = ''
      var search = document.querySelector('[data-ds-search-input]')
      if (search) search.value = ''
      var clear = document.querySelector('[data-ds-search-clear]')
      if (clear) clear.hidden = true
    }
    saveState()
    syncFilterUI()
    applyCatalog()
  }
  function renderChips() {
    var host = document.querySelector('[data-ds-chips]')
    if (!host) return
    var chips = []
    if (state.cat) chips.push({ kind: 'cat', value: '', tag: 'Categoría', label: state.cat })
    state.brands.forEach(function (brand) {
      chips.push({ kind: 'brand', value: brand, tag: 'Marca', label: brand })
    })
    if (state.offers) chips.push({ kind: 'offers', value: '', tag: 'Oferta', label: 'Solo ofertas' })
    if (state.min !== '' || state.max !== '') {
      chips.push({
        kind: 'price', value: '', tag: 'Precio',
        label: (state.min === '' ? '0' : state.min) + ' – ' + (state.max === '' ? '∞' : state.max)
      })
    }
    if (state.q.trim()) chips.push({ kind: 'q', value: '', tag: 'Búsqueda', label: '“' + state.q.trim() + '”' })
    host.textContent = ''
    host.hidden = chips.length === 0
    if (!chips.length) return
    chips.forEach(function (chip) {
      var btn = document.createElement('button')
      btn.type = 'button'
      btn.className = 'cat-chip'
      btn.innerHTML = '<b>' + esc(chip.tag) + '</b><span>' + esc(chip.label) + '</span><i aria-hidden="true">×</i>'
      btn.setAttribute('aria-label', 'Quitar filtro ' + chip.tag + ': ' + chip.label)
      btn.addEventListener('click', function () { removeChip(chip.kind, chip.value) })
      host.appendChild(btn)
    })
    if (chips.length > 1) {
      var clear = document.createElement('button')
      clear.type = 'button'
      clear.className = 'cat-chip-clear'
      clear.textContent = 'Limpiar todo'
      clear.addEventListener('click', function () { removeChip('all') })
      host.appendChild(clear)
    }
  }
  function setCategory(cat) {
    state.cat = cat || ''
    saveState()
    syncFilterUI()
    applyCatalog()
  }
  function buildFilters() {
    buildCategoryFilters()
    buildBrandFilters()
  }
  /* Categorías: píldoras horizontales (diseños de tarjeta) o lista vertical
   * con conteo (catálogo tipo marketplace, `data-ds-filters-mode="list"`). */
  function buildCategoryFilters() {
    var filters = document.querySelector('[data-ds-filters]')
    if (!filters) return
    if (!filters.getAttribute('data-built')) {
      var listMode = filters.getAttribute('data-ds-filters-mode') === 'list'
      var withCounts = !!document.querySelector('[data-ds-search]')
      var counts = {}
      cards.forEach(function (card) {
        var key = card.getAttribute('data-cat') || ''
        if (key) counts[key] = (counts[key] || 0) + 1
      })
      catNames = Object.keys(counts).sort(function (a, b) { return a.localeCompare(b, 'es') })
      ;[''].concat(catNames).forEach(function (cat) {
        var btn = document.createElement('button')
        btn.type = 'button'
        btn.className = listMode ? 'f-cat' : 'ds-cat'
        btn.setAttribute('data-cat', cat)
        if (listMode) {
          btn.innerHTML = '<span>' + esc(cat || 'Todas las categorías') + '</span>' +
            (cat ? '<em>' + counts[cat] + '</em>' : '')
        } else {
          btn.textContent = cat ? (withCounts ? cat + ' (' + counts[cat] + ')' : cat) : 'Todos'
        }
        btn.addEventListener('click', function () { setCategory(cat) })
        filters.appendChild(btn)
      })
      filters.setAttribute('data-built', '1')
    }
    if (state.cat && catNames.indexOf(state.cat) < 0) state.cat = ''
    syncFilterUI()
  }
  /* Marcas: lista de checkboxes armada con `data-brand` de las tarjetas.
   * Los diseños sin ese contenedor no muestran la sección. */
  function buildBrandFilters() {
    var host = document.querySelector('[data-ds-brands]')
    if (!host) return
    var group = host.closest('[data-ds-brands-group]') || host
    var counts = {}
    cards.forEach(function (card) {
      var key = card.getAttribute('data-brand') || ''
      if (key) counts[key] = (counts[key] || 0) + 1
    })
    var names = Object.keys(counts).sort(function (a, b) {
      return (counts[b] - counts[a]) || a.localeCompare(b, 'es')
    })
    state.brands = state.brands.filter(function (name) { return names.indexOf(name) >= 0 })
    if (!names.length) {
      group.hidden = true
      return
    }
    group.hidden = false
    if (!host.getAttribute('data-built')) {
      names.forEach(function (name) {
        var label = document.createElement('label')
        label.className = 'f-check'
        var input = document.createElement('input')
        input.type = 'checkbox'
        input.value = name
        input.addEventListener('change', function () {
          var i = state.brands.indexOf(name)
          if (input.checked && i < 0) state.brands.push(name)
          else if (!input.checked && i >= 0) state.brands.splice(i, 1)
          saveState()
          syncFilterUI()
          applyCatalog()
        })
        var span = document.createElement('span')
        span.textContent = name
        var em = document.createElement('em')
        em.textContent = counts[name]
        label.appendChild(input)
        label.appendChild(span)
        label.appendChild(em)
        host.appendChild(label)
      })
      host.setAttribute('data-built', '1')
      if (names.length > 6) host.setAttribute('data-collapsed', '')
      var moreBtn = document.querySelector('[data-ds-brands-more]')
      if (moreBtn) moreBtn.hidden = names.length <= 6
    }
    syncFilterUI()
  }
  function scoreCard(card, query) {
    var terms = norm(query).split(/\s+/).filter(Boolean)
    if (!terms.length) return 0
    var name = norm(textOf(card.querySelector('.ds-product-name')))
    var cat = norm(card.getAttribute('data-cat') || '')
    var desc = norm(textOf(card.querySelector('.ds-product-desc')))
    var score = 0
    terms.forEach(function (term) {
      if (name === term) score += 8
      else if (name.indexOf(term) >= 0) score += 4
      if (cat.indexOf(term) >= 0) score += 2
      if (desc.indexOf(term) >= 0) score += 1
    })
    return score
  }
  function applyCatalog() {
    if (!wrap) return
    var market = !!document.querySelector('[data-ds-crumb]')
    var shown = 0
    cards.forEach(function (card) {
      var ok = matchesFilters(card)
      card.hidden = !ok
      if (ok) shown++
    })
    var sortSel = document.querySelector('[data-ds-sort]')
    var order = sortSel ? (sortSel.value || 'relevance') : 'relevance'
    var sorted = cards.slice().sort(function (a, b) {
      if (order === 'price-asc' || order === 'price-desc') {
        var pa = parseFloat(a.getAttribute('data-price')) || 0
        var pb = parseFloat(b.getAttribute('data-price')) || 0
        return order === 'price-asc' ? pa - pb : pb - pa
      }
      if (order === 'name') {
        return (a.getAttribute('data-name') || '').localeCompare(b.getAttribute('data-name') || '')
      }
      if (order === 'recent') {
        return (parseInt(a.getAttribute('data-order'), 10) || 0) - (parseInt(b.getAttribute('data-order'), 10) || 0)
      }
      var diff = scoreCard(b, state.q) - scoreCard(a, state.q)
      if (diff) return diff
      return (parseInt(a.getAttribute('data-order'), 10) || 0) - (parseInt(b.getAttribute('data-order'), 10) || 0)
    })
    sorted.forEach(function (card) { wrap.appendChild(card) })
    var countEl = document.querySelector('[data-ds-count]')
    if (countEl) {
      var label = market
        ? shown + (shown === 1 ? ' resultado' : ' resultados')
        : shown + (shown === 1 ? ' producto' : ' productos')
      if (!market && state.q.trim()) label += ' · “' + state.q.trim() + '”'
      countEl.textContent = label
    }
    var crumb = document.querySelector('[data-ds-crumb]')
    if (crumb) crumb.textContent = state.cat || (state.q.trim() ? '“' + state.q.trim() + '”' : 'Todos los productos')
    var noRes = document.querySelector('[data-ds-noresults]')
    if (noRes) {
      noRes.hidden = shown > 0
      if (shown === 0) {
        var filtered = state.q.trim() || state.cat || state.offers || state.min !== '' || state.max !== '' || state.brands.length
        if (market) {
          noRes.textContent = filtered
            ? 'No hay publicaciones que coincidan con tu búsqueda. Probá con otras palabras o quitá algunos filtros.'
            : 'Todavía no hay productos publicados.'
        } else {
          noRes.textContent = filtered
            ? 'No encontramos productos con esos filtros. Probá con otra búsqueda o limpiá los filtros.'
            : 'No hay productos en esta categoría.'
        }
      }
    }
    /* Filtrar/ordenar cambia el alto del documento: sin re-medir, el iframe
     * queda con el alto anterior y el pie del diseño se despega del fondo
     * (queda un hueco grande debajo). */
    send()
  }
  function catalog() {
    wrap = document.querySelector('[data-ds-products]')
    if (!wrap) return
    cards = [].slice.call(wrap.querySelectorAll('.ds-product'))
    cards.forEach(function (card, i) {
      if (!card.hasAttribute('data-order')) card.setAttribute('data-order', i)
    })
    buildFilters()
    applyCatalog()
  }
  function scheduleApply() {
    if (applyTimer) clearTimeout(applyTimer)
    applyTimer = setTimeout(function () { applyTimer = 0; applyCatalog() }, 140)
  }
  function initFilters() {
    var toggle = document.querySelector('[data-ds-filters-toggle]')
    var panel = document.querySelector('[data-ds-filters-panel]')
    var minInput = document.querySelector('[data-ds-price-min]')
    var maxInput = document.querySelector('[data-ds-price-max]')
    var offersInput = document.querySelector('[data-ds-offers]')
    function readFilters() {
      state.min = minInput ? minInput.value.trim() : ''
      state.max = maxInput ? maxInput.value.trim() : ''
      state.offers = offersInput ? !!offersInput.checked : false
      saveState()
      syncFilterUI()
      scheduleApply()
    }
    /* Catálogo tipo marketplace: el panel de filtros es una hoja a pantalla
     * completa en móvil, con "Aplicar" al pie. Los diseños con panel
     * colapsable (sin botón de cierre) conservan el comportamiento previo. */
    var sheet = !!(panel && panel.querySelector('[data-ds-filters-close]'))
    function openSheet() {
      panel.classList.add('is-open')
      if (toggle) toggle.setAttribute('aria-expanded', 'true')
      document.body.classList.add('filters-open')
      var closeBtn = panel.querySelector('[data-ds-filters-close]')
      if (closeBtn) closeBtn.focus()
      send()
    }
    function closeSheet(refocus) {
      if (!panel.classList.contains('is-open')) return
      panel.classList.remove('is-open')
      if (toggle) toggle.setAttribute('aria-expanded', 'false')
      document.body.classList.remove('filters-open')
      readFilters()
      applyCatalog()
      if (refocus && toggle) toggle.focus()
      send()
    }
    if (toggle && panel) {
      toggle.addEventListener('click', function () {
        if (!sheet) {
          var open = panel.hasAttribute('data-open')
          if (open) panel.removeAttribute('data-open')
          else panel.setAttribute('data-open', '')
          toggle.setAttribute('aria-expanded', open ? 'false' : 'true')
          return
        }
        if (panel.classList.contains('is-open')) closeSheet(true)
        else openSheet()
      })
      if (sheet) {
        ;[].forEach.call(panel.querySelectorAll('[data-ds-filters-close]'), function (btn) {
          btn.addEventListener('click', function () { closeSheet(true) })
        })
        panel.addEventListener('keydown', function (e) {
          if (e.key === 'Escape') {
            e.stopPropagation()
            closeSheet(true)
          }
        })
      }
    }
    var applyBtn = document.querySelector('[data-ds-price-apply]')
    if (applyBtn) {
      /* Precio se aplica con el botón (como el marketplace), no en cada
       * tecla: el rango queda a la vista hasta confirmarlo. */
      applyBtn.addEventListener('click', function () { readFilters(); applyCatalog() })
      ;[minInput, maxInput].forEach(function (input) {
        if (!input) return
        input.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') {
            e.preventDefault()
            readFilters()
            applyCatalog()
          }
        })
      })
    } else {
      if (minInput) minInput.addEventListener('input', readFilters)
      if (maxInput) maxInput.addEventListener('input', readFilters)
    }
    if (offersInput) offersInput.addEventListener('change', readFilters)
    ;[].forEach.call(document.querySelectorAll('[data-ds-clear]'), function (btn) {
      btn.addEventListener('click', resetFilters)
    })
    var moreBtn = document.querySelector('[data-ds-brands-more]')
    var brandsHost = document.querySelector('[data-ds-brands]')
    if (moreBtn && brandsHost) {
      moreBtn.addEventListener('click', function () {
        var collapsed = brandsHost.hasAttribute('data-collapsed')
        if (collapsed) brandsHost.removeAttribute('data-collapsed')
        else brandsHost.setAttribute('data-collapsed', '')
        moreBtn.textContent = collapsed ? 'Ver menos' : 'Ver todas las marcas'
        send()
      })
    }
  }
  function resetFilters() {
    state.cat = ''
    state.brands = []
    state.min = ''
    state.max = ''
    state.offers = false
    state.q = ''
    var input = document.querySelector('[data-ds-search-input]')
    if (input) input.value = ''
    var clearBtn = document.querySelector('[data-ds-search-clear]')
    if (clearBtn) clearBtn.hidden = true
    var minInput = document.querySelector('[data-ds-price-min]')
    var maxInput = document.querySelector('[data-ds-price-max]')
    if (minInput) minInput.value = ''
    if (maxInput) maxInput.value = ''
    saveState()
    syncFilterUI()
    applyCatalog()
    closeSuggest()
  }
  /* Vista del catálogo: lista (filas tipo marketplace) o grilla de tarjetas.
   * La preferencia dura la sesión y el alto se re-mide al cambiar. */
  function initView() {
    var host = document.querySelector('[data-ds-products]')
    var buttons = [].slice.call(document.querySelectorAll('[data-ds-view]'))
    if (!host || !buttons.length) return
    var saved = storeGet(VIEW_KEY) || ''
    var modes = buttons.map(function (btn) { return btn.getAttribute('data-ds-view') })
    setView(modes.indexOf(saved) >= 0 ? saved : (host.getAttribute('data-ds-view-mode') || 'list'))
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () { setView(btn.getAttribute('data-ds-view')) })
    })
    function setView(mode) {
      host.setAttribute('data-ds-view-mode', mode)
      buttons.forEach(function (btn) {
        btn.setAttribute('aria-pressed', btn.getAttribute('data-ds-view') === mode ? 'true' : 'false')
      })
      storeSet(VIEW_KEY, mode)
      send()
    }
  }
  function setSuggestActive(index) {
    activeSuggest = index
    suggestItems.forEach(function (item, i) {
      item.classList.toggle('is-active', i === index)
      item.setAttribute('aria-selected', i === index ? 'true' : 'false')
    })
    var input = document.querySelector('[data-ds-search-input]')
    if (input) {
      if (index >= 0 && suggestItems[index]) input.setAttribute('aria-activedescendant', suggestItems[index].id)
      else input.removeAttribute('aria-activedescendant')
    }
  }
  function closeSuggest() {
    var panel = document.querySelector('[data-ds-suggest]')
    var input = document.querySelector('[data-ds-search-input]')
    if (panel) {
      panel.hidden = true
      panel.innerHTML = ''
    }
    suggestItems = []
    activeSuggest = -1
    if (input) input.setAttribute('aria-expanded', 'false')
  }
  function chooseSuggestion(item) {
    if (!item) return
    if (item.hasAttribute('data-suggest-all')) { submitSearch(); return }
    var productId = item.getAttribute('data-suggest-product')
    if (productId) {
      closeSuggest()
      go('product', productId)
      return
    }
    var cat = item.getAttribute('data-suggest-cat')
    if (cat != null) {
      setCategory(cat)
      closeSuggest()
      if (root.getAttribute('data-ds-surface') !== 'catalog') go('catalog')
    }
  }
  function renderSuggest() {
    var panel = document.querySelector('[data-ds-suggest]')
    var input = document.querySelector('[data-ds-search-input]')
    if (!panel || !input) return
    var query = input.value.trim()
    if (!query) { closeSuggest(); return }
    var matches = cards.filter(function (card) { return matchesQuery(card, query) })
    var counts = {}
    matches.forEach(function (card) {
      var key = card.getAttribute('data-cat') || ''
      if (key) counts[key] = (counts[key] || 0) + 1
    })
    var cats = Object.keys(counts).slice(0, 4)
    var products = matches.slice(0, 6)
    var html = ''
    if (products.length) {
      html += '<div class="suggest-head" role="presentation">Productos</div>'
      products.forEach(function (card, i) {
        var link = card.querySelector('[data-ds-product]')
        var id = link ? link.getAttribute('data-ds-product') : ''
        var name = textOf(card.querySelector('.ds-product-name'))
        var cat = card.getAttribute('data-cat') || ''
        var img = card.querySelector('.ds-product-img')
        var src = img ? (img.getAttribute('src') || '') : ''
        var meta = [cat, money(card.getAttribute('data-price'))].filter(Boolean).join(' · ')
        html += '<button type="button" class="suggest-item" role="option" aria-selected="false" id="ds-suggest-' + i + '" data-suggest-product="' + esc(id) + '">' +
          '<span class="suggest-thumb">' + (src ? '<img src="' + esc(src) + '" alt="">' : '▣') + '</span>' +
          '<span class="suggest-copy"><strong>' + esc(name) + '</strong><small>' + esc(meta) + '</small></span>' +
          '</button>'
      })
    }
    if (cats.length) {
      html += '<div class="suggest-head" role="presentation">Categorías</div>'
      cats.forEach(function (cat, i) {
        html += '<button type="button" class="suggest-item" role="option" aria-selected="false" id="ds-suggest-c' + i + '" data-suggest-cat="' + esc(cat) + '">' +
          '<span class="suggest-thumb">▤</span>' +
          '<span class="suggest-copy"><strong>' + esc(cat) + '</strong><small>' + counts[cat] + (counts[cat] === 1 ? ' producto' : ' productos') + '</small></span>' +
          '</button>'
      })
    }
    if (!products.length && !cats.length) {
      html += '<p class="suggest-empty">Sin resultados para “' + esc(query) + '”.</p>'
    }
    html += '<button type="button" class="suggest-more" role="option" aria-selected="false" data-suggest-all>Ver todos los resultados</button>'
    panel.innerHTML = html
    panel.hidden = false
    input.setAttribute('aria-expanded', 'true')
    suggestItems = [].slice.call(panel.querySelectorAll('[role="option"]'))
    suggestItems.forEach(function (item, i) {
      if (!item.id) item.id = 'ds-suggest-x' + i
      item.addEventListener('click', function () { chooseSuggestion(item) })
      item.addEventListener('mousemove', function () { setSuggestActive(i) })
    })
    var all = panel.querySelector('[data-suggest-all]')
    if (all) all.addEventListener('click', submitSearch)
    setSuggestActive(-1)
  }
  function submitSearch() {
    var input = document.querySelector('[data-ds-search-input]')
    state.q = input ? input.value.trim() : ''
    saveState()
    closeSuggest()
    if (root.getAttribute('data-ds-surface') !== 'catalog') go('catalog')
    applyCatalog()
  }
  function initSearch() {
    var form = document.querySelector('[data-ds-search]')
    var input = document.querySelector('[data-ds-search-input]')
    if (!form || !input) return
    var clearBtn = document.querySelector('[data-ds-search-clear]')
    function syncClear() {
      if (clearBtn) clearBtn.hidden = !input.value
    }
    input.value = state.q
    syncClear()
    input.setAttribute('role', 'combobox')
    input.setAttribute('aria-autocomplete', 'list')
    input.setAttribute('aria-expanded', 'false')
    input.setAttribute('aria-controls', 'ds-search-suggest')
    var panel = document.querySelector('[data-ds-suggest]')
    if (panel) panel.id = 'ds-search-suggest'
    form.addEventListener('submit', function (e) {
      e.preventDefault()
      submitSearch()
    })
    input.addEventListener('input', function () {
      state.q = input.value
      syncClear()
      renderSuggest()
      if (root.getAttribute('data-ds-surface') === 'catalog') scheduleApply()
      saveState()
    })
    input.addEventListener('focus', function () {
      if (input.value.trim()) renderSuggest()
    })
    input.addEventListener('search', function () {
      state.q = input.value
      syncClear()
      if (root.getAttribute('data-ds-surface') === 'catalog') applyCatalog()
      saveState()
    })
    input.addEventListener('keydown', function (e) {
      var panelEl = document.querySelector('[data-ds-suggest]')
      var open = panelEl && !panelEl.hidden
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        if (!open) renderSuggest()
        setSuggestActive(Math.min(activeSuggest + 1, suggestItems.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSuggestActive(Math.max(activeSuggest - 1, 0))
      } else if (e.key === 'Enter' && open && activeSuggest >= 0) {
        e.preventDefault()
        chooseSuggestion(suggestItems[activeSuggest])
      } else if (e.key === 'Escape') {
        closeSuggest()
      }
    })
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        input.value = ''
        state.q = ''
        syncClear()
        closeSuggest()
        saveState()
        if (root.getAttribute('data-ds-surface') === 'catalog') applyCatalog()
        input.focus()
      })
    }
    document.addEventListener('click', function (e) {
      if (!e.target.closest || !e.target.closest('[data-ds-search]')) closeSuggest()
    })
  }
  /* Opiniones de la ficha: el HTML del diseño ya trae `.ds-reviews` con
   * la lista renderizada + data-rate/data-comment (los toggles del dueño)
   * y las URLs de la API pública. El puente arma el formulario, carga el
   * captcha y publica por fetch — mismos endpoints que la vista Vue.
   * Cuando ambas opciones están apagadas el fragmento llega vacío y la
   * sección se oculta con CSS (:has/.ds-reviews ausente). */
  var REVIEW_THUMB = {
    up: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg>',
    down: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 14V2"/><path d="m9 18.12 1 4.88H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg>'
  }
  function initReviews() {
    var box = document.querySelector('.ds-reviews')
    var formHost = box ? box.querySelector('[data-ds-rev-form]') : null
    if (!box || !formHost || box.getAttribute('data-ds-rev-ready')) return
    box.setAttribute('data-ds-rev-ready', '1')
    var revUrl = box.getAttribute('data-rev-url') || ''
    var capUrl = box.getAttribute('data-cap-url') || ''
    var canRate = box.getAttribute('data-rate') === '1'
    var canComment = box.getAttribute('data-comment') === '1'
    var list = box.querySelector('[data-ds-rev-list]')
    var vote = null
    var challenge = null
    var busy = false
    var form = document.createElement('form')
    form.className = 'ds-rev-fields'
    form.setAttribute('novalidate', '')
    var html = ''
    if (canRate) {
      html += '<div class="ds-rev-votes" role="radiogroup" aria-label="¿Te gustó este producto?">' +
        '<button type="button" class="ds-rev-pick" data-v="up" role="radio" aria-checked="false">' + REVIEW_THUMB.up + '<span>Me gustó</span></button>' +
        '<button type="button" class="ds-rev-pick" data-v="down" role="radio" aria-checked="false">' + REVIEW_THUMB.down + '<span>No me gustó</span></button>' +
        '</div>'
    }
    html += '<div class="ds-rev-row">' +
      '<input class="ds-rev-input" name="name" maxlength="80" autocomplete="given-name" placeholder="Tu nombre" required>' +
      '<input class="ds-rev-input" name="surname" maxlength="80" autocomplete="family-name" placeholder="Tu apellido" required>' +
      '</div>' +
      '<input class="ds-rev-input" name="email" type="email" autocomplete="email" placeholder="nombre@correo.com" required>'
    if (canComment) {
      html += '<textarea class="ds-rev-input ds-rev-area" name="text" rows="3" maxlength="600" placeholder="Contale a otros qué te pareció este producto"></textarea>'
    }
    html += '<div class="ds-rev-cap">' +
      '<span class="ds-rev-q" data-rev-question>Cargando…</span>' +
      '<input class="ds-rev-input" name="captcha_answer" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required>' +
      '<button type="button" class="ds-rev-reload" data-rev-reload aria-label="Nueva pregunta" title="Nueva pregunta">↻</button>' +
      '</div>' +
      '<div class="ds-rev-hp" aria-hidden="true"><label>Website <input name="website" tabindex="-1" autocomplete="off"></label></div>' +
      '<p class="ds-rev-status" data-rev-status role="status" aria-live="polite"></p>' +
      '<button type="submit" class="ds-rev-send">Publicar opinión</button>'
    form.innerHTML = html
    formHost.appendChild(form)
    var status = form.querySelector('[data-rev-status]')
    var question = form.querySelector('[data-rev-question]')
    function say(msg, ok) {
      if (!status) return
      status.textContent = msg || ''
      status.setAttribute('data-ok', ok ? '1' : '0')
    }
    function loadCaptcha() {
      challenge = null
      if (question) question.textContent = 'Cargando…'
      if (!capUrl) { if (question) question.textContent = '—'; return }
      api(capUrl).then(function (out) {
        var data = out && out.ok ? out.data : null
        challenge = data || null
        if (question) question.textContent = (data && data.question) ? data.question : '—'
        var capInput = form.querySelector('[name="captcha_answer"]')
        if (capInput) capInput.value = ''
      })
    }
    function reviewItem(r) {
      var li = document.createElement('li')
      li.className = 'ds-rev-item'
      var voteHtml = ''
      if (r.is_positive === true || r.is_positive === false) {
        var cls = r.is_positive ? 'up' : 'down'
        voteHtml = '<span class="ds-rev-vote ds-rev-' + cls + '" title="' + (r.is_positive ? 'Le gustó' : 'No le gustó') + '">' + REVIEW_THUMB[cls] + '</span>'
      }
      var date = ''
      var d = new Date(r.created_at || '')
      if (!isNaN(d.getTime())) date = d.toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' })
      li.innerHTML = '<strong class="ds-rev-name">' + esc(r.name) + ' ' + esc(r.surname_initial || '') + '</strong>' +
        '<time class="ds-rev-date">' + esc(date) + '</time>' + voteHtml +
        (canComment && r.text ? '<p class="ds-rev-text">' + esc(r.text) + '</p>' : '') +
        (r.owner_reply ? '<p class="ds-rev-reply"><strong>Respuesta del comercio</strong><span>' + esc(r.owner_reply) + '</span></p>' : '')
      return li
    }
    function refreshList() {
      if (!revUrl || !list) return
      api(revUrl).then(function (out) {
        var rows = out && out.ok && Array.isArray(out.data) ? out.data : []
        list.innerHTML = ''
        rows.forEach(function (r) { list.appendChild(reviewItem(r)) })
        send()
      })
    }
    ;[].forEach.call(form.querySelectorAll('.ds-rev-pick'), function (btn) {
      btn.addEventListener('click', function () {
        vote = btn.getAttribute('data-v')
        ;[].forEach.call(form.querySelectorAll('.ds-rev-pick'), function (b) {
          var on = b.getAttribute('data-v') === vote
          b.setAttribute('aria-checked', on ? 'true' : 'false')
          b.classList.toggle('is-on', on)
        })
      })
    })
    var reloadBtn = form.querySelector('[data-rev-reload]')
    if (reloadBtn) reloadBtn.addEventListener('click', loadCaptcha)
    form.addEventListener('submit', function (e) {
      e.preventDefault()
      if (busy || !revUrl) return
      var fd = new FormData(form)
      var payload = {
        is_positive: canRate && vote ? (vote === 'up') : null,
        text: canComment ? String(fd.get('text') || '').trim() : '',
        name: String(fd.get('name') || '').trim(),
        surname: String(fd.get('surname') || '').trim(),
        email: String(fd.get('email') || '').trim(),
        website: String(fd.get('website') || ''),
        challenge_id: challenge ? challenge.challenge_id : '',
        captcha_answer: String(fd.get('captcha_answer') || '').trim()
      }
      if (canRate && payload.is_positive === null && !(canComment && payload.text)) { say('Elegí si te gustó o escribí un comentario.'); return }
      if (canComment && !canRate && !payload.text) { say('Escribí un comentario para publicar.'); return }
      busy = true
      say('')
      api(revUrl, { method: 'POST', body: payload })
        .then(function (out) {
          if (!out) { say('Sin conexión. Probá de nuevo.'); return }
          if (!out.ok) {
            var msg = ''
            var data = out.data || {}
            Object.keys(data).some(function (key) {
              var val = data[key]
              msg = Array.isArray(val) ? String(val[0]) : String(val)
              return !!msg
            })
            say(msg || 'No se pudo publicar. Probá de nuevo.')
            loadCaptcha()
            return
          }
          form.reset()
          vote = null
          ;[].forEach.call(form.querySelectorAll('.ds-rev-pick'), function (b) {
            b.setAttribute('aria-checked', 'false')
            b.classList.remove('is-on')
          })
          say('Tu opinión fue publicada. ¡Gracias!', true)
          loadCaptcha()
          refreshList()
        })
        .finally(function () { busy = false; send() })
    })
    loadCaptcha()
  }
  /* Formulario "Contáctanos": el diseño marca una zona con
   * `[data-ds-contact]` + data-url/data-cap-url (mismos endpoints que el
   * bloque Vue `contact`). El puente arma los campos, carga el captcha
   * firmado y publica por `ds-api`. Sin zona no se monta nada. */
  function initContact() {
    var box = document.querySelector('[data-ds-contact]')
    if (!box || box.getAttribute('data-ds-contact-ready')) return
    box.setAttribute('data-ds-contact-ready', '1')
    var url = box.getAttribute('data-url') || ''
    var capUrl = box.getAttribute('data-cap-url') || ''
    var challenge = null
    var busy = false
    var form = document.createElement('form')
    form.className = 'ds-contact-fields'
    form.setAttribute('novalidate', '')
    form.innerHTML =
      '<div class="ds-contact-row">' +
      '<input class="ds-contact-input" name="name" maxlength="80" autocomplete="name" placeholder="Tu nombre" required>' +
      '<input class="ds-contact-input" name="email" type="email" autocomplete="email" placeholder="nombre@correo.com" required>' +
      '</div>' +
      '<textarea class="ds-contact-input ds-contact-area" name="message" rows="4" maxlength="2000" placeholder="Escribí tu mensaje" required></textarea>' +
      '<div class="ds-contact-cap">' +
      '<span class="ds-contact-q" data-contact-question>Cargando…</span>' +
      '<input class="ds-contact-input" name="captcha_answer" inputmode="numeric" autocomplete="off" placeholder="Respuesta" required>' +
      '<button type="button" class="ds-contact-reload" data-contact-reload aria-label="Nueva pregunta" title="Nueva pregunta">↻</button>' +
      '</div>' +
      '<div class="ds-rev-hp" aria-hidden="true"><label>Website <input name="website" tabindex="-1" autocomplete="off"></label></div>' +
      '<p class="ds-contact-status" data-contact-status role="status" aria-live="polite"></p>' +
      '<button type="submit" class="ds-contact-send">Enviar mensaje</button>'
    box.appendChild(form)
    var status = form.querySelector('[data-contact-status]')
    var question = form.querySelector('[data-contact-question]')
    function say(msg, ok) {
      if (!status) return
      status.textContent = msg || ''
      status.setAttribute('data-ok', ok ? '1' : '0')
    }
    function loadCaptcha() {
      challenge = null
      if (question) question.textContent = 'Cargando…'
      if (!capUrl) { if (question) question.textContent = '—'; return }
      api(capUrl).then(function (out) {
        var data = out && out.ok ? out.data : null
        challenge = data || null
        if (question) question.textContent = (data && data.question) ? data.question : '—'
        var capInput = form.querySelector('[name="captcha_answer"]')
        if (capInput) capInput.value = ''
      })
    }
    var reloadBtn = form.querySelector('[data-contact-reload]')
    if (reloadBtn) reloadBtn.addEventListener('click', loadCaptcha)
    form.addEventListener('submit', function (e) {
      e.preventDefault()
      if (busy || !url) return
      var fd = new FormData(form)
      var payload = {
        name: String(fd.get('name') || '').trim(),
        email: String(fd.get('email') || '').trim(),
        message: String(fd.get('message') || '').trim(),
        website: String(fd.get('website') || ''),
        challenge_id: challenge ? challenge.challenge_id : '',
        captcha_answer: String(fd.get('captcha_answer') || '').trim()
      }
      busy = true
      say('')
      api(url, { method: 'POST', body: payload })
        .then(function (out) {
          if (!out) { say('Sin conexión. Probá de nuevo.'); return }
          var data = out.data || {}
          if (!out.ok) {
            var msg = ''
            Object.keys(data).some(function (key) {
              var val = data[key]
              msg = Array.isArray(val) ? String(val[0]) : String(val)
              return !!msg
            })
            say(msg || 'No pudimos enviar tu mensaje. Probá de nuevo.')
            loadCaptcha()
            return
          }
          form.reset()
          say(String(data['Exito'] || 'Tu mensaje fue enviado.'), true)
          loadCaptcha()
        })
        .finally(function () { busy = false; send() })
    })
    loadCaptcha()
  }
  var sortSel = document.querySelector('[data-ds-sort]')
  if (sortSel) sortSel.addEventListener('change', applyCatalog)
  catalog()
  restoreState()
  ;(function restorePriceInputs() {
    if (!document.querySelector('[data-ds-price-apply]')) return
    var minInput = document.querySelector('[data-ds-price-min]')
    var maxInput = document.querySelector('[data-ds-price-max]')
    if (minInput) minInput.value = state.min
    if (maxInput) maxInput.value = state.max
  })()
  buildFilters()
  initSearch()
  initFilters()
  initView()
  initReviews()
  initContact()
  syncFilterUI()
  applyCatalog()
  mountThemeToggle()
  window.addEventListener('load', function () { catalog(); mountThemeToggle(); send() })
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root)
  else setTimeout(send, 120)
  send()
})()
