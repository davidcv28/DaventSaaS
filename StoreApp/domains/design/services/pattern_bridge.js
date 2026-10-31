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
  /* ------------------------------------------------------------------
   * Catálogo + búsqueda del marketplace.
   * El documento es estático: las tarjetas viajan con data-cat/data-price/
   * data-name y acá se filtran por texto, categoría, rango de precio y
   * ofertas, se ordenan y se resuelven las sugerencias del buscador.
   * ------------------------------------------------------------------ */
  var state = { q: '', cat: '', min: '', max: '', offers: false }
  var cards = []
  var wrap = null
  var catNames = []
  var activeSuggest = -1
  var suggestItems = []
  var applyTimer = 0
  var STORE_KEY = 'davent:ds-search:' + (typeof location !== 'undefined' ? location.pathname : '')

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
  function saveState() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(state)) } catch (e) {}
  }
  function restoreState() {
    try {
      var raw = sessionStorage.getItem(STORE_KEY)
      if (!raw) return
      var saved = JSON.parse(raw) || {}
      if (typeof saved.q === 'string') state.q = saved.q
      if (typeof saved.cat === 'string') state.cat = saved.cat
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
    if (state.offers && !card.querySelector('.ds-product-old')) return false
    var price = parseFloat(card.getAttribute('data-price')) || 0
    var min = numOrNull(state.min)
    var max = numOrNull(state.max)
    if (min != null && price < min) return false
    if (max != null && price > max) return false
    return matchesQuery(card, state.q)
  }
  function syncFilterUI() {
    var filters = document.querySelector('[data-ds-filters]')
    if (filters) {
      ;[].forEach.call(filters.querySelectorAll('button'), function (btn) {
        btn.setAttribute('aria-pressed', btn.getAttribute('data-cat') === state.cat ? 'true' : 'false')
      })
    }
    var minInput = document.querySelector('[data-ds-price-min]')
    var maxInput = document.querySelector('[data-ds-price-max]')
    var offersInput = document.querySelector('[data-ds-offers]')
    if (minInput) minInput.value = state.min
    if (maxInput) maxInput.value = state.max
    if (offersInput) offersInput.checked = !!state.offers
  }
  function setCategory(cat) {
    state.cat = cat || ''
    saveState()
    syncFilterUI()
    applyCatalog()
  }
  function buildFilters() {
    var filters = document.querySelector('[data-ds-filters]')
    if (!filters) return
    if (!filters.getAttribute('data-built')) {
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
        btn.className = 'ds-cat'
        btn.setAttribute('data-cat', cat)
        btn.textContent = cat ? (withCounts ? cat + ' (' + counts[cat] + ')' : cat) : 'Todos'
        btn.addEventListener('click', function () { setCategory(cat) })
        filters.appendChild(btn)
      })
      filters.setAttribute('data-built', '1')
    }
    if (state.cat && catNames.indexOf(state.cat) < 0) state.cat = ''
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
      var diff = scoreCard(b, state.q) - scoreCard(a, state.q)
      if (diff) return diff
      return (parseInt(a.getAttribute('data-order'), 10) || 0) - (parseInt(b.getAttribute('data-order'), 10) || 0)
    })
    sorted.forEach(function (card) { wrap.appendChild(card) })
    var countEl = document.querySelector('[data-ds-count]')
    if (countEl) {
      var label = shown + (shown === 1 ? ' producto' : ' productos')
      if (state.q.trim()) label += ' · “' + state.q.trim() + '”'
      countEl.textContent = label
    }
    var noRes = document.querySelector('[data-ds-noresults]')
    if (noRes) {
      noRes.hidden = shown > 0
      if (shown === 0) {
        var filtered = state.q.trim() || state.cat || state.offers || state.min !== '' || state.max !== ''
        noRes.textContent = filtered
          ? 'No encontramos productos con esos filtros. Probá con otra búsqueda o limpiá los filtros.'
          : 'No hay productos en esta categoría.'
      }
    }
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
    if (toggle && panel) {
      toggle.addEventListener('click', function () {
        var open = panel.hasAttribute('data-open')
        if (open) panel.removeAttribute('data-open')
        else panel.setAttribute('data-open', '')
        toggle.setAttribute('aria-expanded', open ? 'false' : 'true')
      })
    }
    var minInput = document.querySelector('[data-ds-price-min]')
    var maxInput = document.querySelector('[data-ds-price-max]')
    var offersInput = document.querySelector('[data-ds-offers]')
    function readFilters() {
      state.min = minInput ? minInput.value.trim() : ''
      state.max = maxInput ? maxInput.value.trim() : ''
      state.offers = offersInput ? !!offersInput.checked : false
      saveState()
      scheduleApply()
    }
    if (minInput) minInput.addEventListener('input', readFilters)
    if (maxInput) maxInput.addEventListener('input', readFilters)
    if (offersInput) offersInput.addEventListener('change', readFilters)
    var clearBtn = document.querySelector('[data-ds-clear]')
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        state.cat = ''
        state.min = ''
        state.max = ''
        state.offers = false
        saveState()
        syncFilterUI()
        applyCatalog()
      })
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
  var sortSel = document.querySelector('[data-ds-sort]')
  if (sortSel) sortSel.addEventListener('change', applyCatalog)
  catalog()
  restoreState()
  buildFilters()
  initSearch()
  initFilters()
  syncFilterUI()
  applyCatalog()
  mountThemeToggle()
  window.addEventListener('load', function () { catalog(); mountThemeToggle(); send() })
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root)
  else setTimeout(send, 120)
  send()
})()
