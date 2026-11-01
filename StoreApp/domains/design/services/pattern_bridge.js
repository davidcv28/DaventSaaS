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
      var openPanel = document.querySelector('[data-ds-filters-panel].is-open')
      if (openPanel) {
        openPanel.classList.remove('is-open')
        var openToggle = document.querySelector('[data-ds-filters-toggle]')
        if (openToggle) openToggle.setAttribute('aria-expanded', 'false')
        document.body.classList.remove('filters-open')
      }
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
    var saved = ''
    try { saved = sessionStorage.getItem(VIEW_KEY) || '' } catch (e) {}
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
      try { sessionStorage.setItem(VIEW_KEY, mode) } catch (e) {}
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
  syncFilterUI()
  applyCatalog()
  mountThemeToggle()
  window.addEventListener('load', function () { catalog(); mountThemeToggle(); send() })
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root)
  else setTimeout(send, 120)
  send()
})()
