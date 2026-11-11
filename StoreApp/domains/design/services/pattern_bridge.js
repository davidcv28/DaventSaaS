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
      if (!sec) return
      sec.hidden = true
      /* Los links del menú/footer comparten el data-flag de la sección pero
       * no son ancestros de la zona: quedaban visibles y clicables hacia
       * una sección escondida (clic sin efecto). Se ocultan los anchors
       * que apuntan al id de la sección hideout — inline !important porque
       * los links del diseño traen display propio que pisa al atributo
       * `hidden`. */
      if (sec.id) {
        ;[].forEach.call(document.querySelectorAll('a[href="#' + sec.id + '"]'), function (l) {
          l.style.setProperty('display', 'none', 'important')
        })
      }
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
      /* El alto es el MAYOR entre el pie y el último bloque en flujo: si
       * algo queda debajo del footer (banner, hoja, zona async), medir
       * solo el pie deja el iframe más bajo que el documento — scroll
       * interno + encadenamiento con la página = vibración al fondo. */
      if (document.body) {
        var kids = document.body.children
        for (var i = kids.length - 1; i >= 0; i--) {
          var el = kids[i]
          if (!el || el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'LINK') continue
          var cs = window.getComputedStyle(el)
          if (cs.position === 'fixed' || cs.position === 'absolute' || cs.display === 'none') continue
          var r = el.getBoundingClientRect()
          if (r.height > 0) {
            var rb = r.bottom + (window.scrollY || 0)
            if (rb > h) h = rb
            break
          }
        }
        if (!h) h = document.body.scrollHeight
      }
      if (!h) h = root.scrollHeight
      syncChatMetrics()
      parent.postMessage({ type: 'davent:ds-height', height: h }, '*')
    })
  }
  function go(route, id) {
    parent.postMessage({ type: 'davent:ds-route', route: route, id: id || '' }, '*')
  }
  /* Alto del chrome fijo del diseño (masthead + pestañas) para que el
   * host deje el destino debajo y no tapado. Opt-in: sin atributo, 72. */
  function scrollOffset() {
    var host = document.querySelector('[data-ds-offset]')
    var n = parseInt((host && host.getAttribute('data-ds-offset')) || '', 10)
    return n > 0 ? n : 72
  }
  /* Ancla pedida desde otra superficie (p. ej. "Nosotros" clicado en el
   * catálogo): el destino existe en el documento pero está display:none,
   * así que el click cae al data-ds-route y navega sin scroll. Se guarda
   * el hash y el handler de davent:ds-surface reintenta el scroll una vez
   * que la superficie destino queda visible. */
  var pendingAnchor = null
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
    /* Diseños de un solo modo (fotos = solo claro, neon = solo noche):
     * declaran data-ds-theme-lock en su markup y el toggle no se monta —
     * un botón que no cambia nada es peor que no tenerlo. El <html> del
     * documento lo genera pattern_document, así que el flag viaja en
     * cualquier elemento del fragmento. */
    if (root.hasAttribute('data-ds-theme-lock') || document.querySelector('[data-ds-theme-lock]')) return
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
      /* UI del propio puente (chatbot): no es chrome del diseño — su
       * posición la maneja syncChatMetrics, no el pin de barras. */
      if (el.hasAttribute && el.hasAttribute('data-ds-no-pin')) return
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
    syncChatMetrics()
  }
  /* Alto del chrome pegado abajo del diseño (tab bar móvil, FAB propio):
   * el chatbot del documento se levanta para no quedar debajo. El propio
   * `.ds-chat` se excluye — si no, se contaría a sí mismo como chrome. */
  function bottomChromePx() {
    var max = 0
    ;(pinned || []).forEach(function (p) {
      if (p.prop !== 'bottom' || !p.el.offsetHeight) return
      if (p.el.closest && p.el.closest('.ds-chat')) return
      /* Hojas cerradas (translateY(102%)) conservan layout: su rect queda
       * debajo del borde visible del marco y no son chrome real — contarlas
       * inflaba --ds-chat-lift y desplazaba el FAB a media pantalla. */
      if (frameBox) {
        var docBot = Math.min(frameBox.vh - frameBox.top, frameBox.bottom - frameBox.top)
        var r = p.el.getBoundingClientRect()
        if (r.top > docBot + 4) return
      }
      max = Math.max(max, p.el.offsetHeight + (p.base || 0))
    })
    return max
  }
  /* Posición del chatbot dentro del iframe estirado: `position:fixed`
   * anclaría al documento entero, así que el top se calcula contra el
   * borde inferior visible del marco (mismo criterio que pinFixed) y el
   * alto del panel sale del viewport real (`--ds-chat-vh`), no del alto
   * del documento. */
  function syncChatMetrics() {
    if (!chat || !chat.root || !frameBox) return
    var docBot = Math.min(frameBox.vh - frameBox.top, frameBox.bottom - frameBox.top)
    var lift = bottomChromePx()
    chat.root.style.setProperty('--ds-chat-lift', Math.round(lift) + 'px')
    chat.root.style.setProperty('--ds-chat-vh', Math.round(frameBox.vh) + 'px')
    chat.root.style.top = Math.max(0, docBot - chat.root.offsetHeight - 16 - lift) + 'px'
  }
  window.addEventListener('resize', function () { resetFixed(); pinFixed() })

  window.addEventListener('message', function (e) {
    /* Solo el host puede hablarle al documento: sin este chequeo cualquier
     * ventana/popup con la referencia podía inyectar `ds-studio-css` (CSS
     * arbitrario) o falsificar `ds-theme`/`ds-surface`. */
    if (e.source !== window.parent) return
    var d = e.data || {}
    if (d.type === 'davent:ds-theme') {
      root.setAttribute('data-ds-theme', d.theme)
      paintThemeToggle()
    }
    if (d.type === 'davent:ds-surface') {
      root.setAttribute('data-ds-surface', d.surface)
      /* Reintento de ancla cross-surface: el click navegó al tiempo que la
       * sección destino estaba oculta; ahora que la superficie quedó
       * visible se scrollea una sola vez y se descarta el pendiente. */
      if (pendingAnchor) {
        var pendHash = pendingAnchor
        pendingAnchor = null
        var pendEl = pendHash.charAt(0) === '#' ? document.getElementById(pendHash.slice(1)) : null
        if (pendEl && pendEl.getClientRects().length) {
          parent.postMessage({ type: 'davent:ds-scroll', top: pendEl.getBoundingClientRect().top + (window.scrollY || 0), offset: scrollOffset() }, '*')
        }
      }
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
      paintMissingProduct()
      window.scrollTo(0, 0)
      send()
      setTimeout(send, 120)
    }
    /* Sesión del comprador la empuja el host: solo cambia el rótulo del
     * botón ("Ingresar" ↔ "Mi cuenta"); la acción siempre es la misma. */
    if (d.type === 'davent:ds-account-state') {
      accountAuthed = d.authed === true
      paintAccount()
    }
    /* Contador del carrito: también lo empuja el host (la sesión del
     * comprador vive afuera — el documento es origen opaco). Solo pinta
     * el badge de `.dsx-cart`; sin botón montado (tienda sin venta
     * online) el mensaje se ignora. */
    if (d.type === 'davent:ds-cart-state') {
      var cartN = parseInt(d.count, 10)
      cartCount = isFinite(cartN) && cartN > 0 ? Math.floor(cartN) : 0
      paintCart()
    }
    if (d.type === 'davent:ds-measure') send()
    if (d.type === 'davent:ds-frame') {
      frameBox = { top: Number(d.top) || 0, bottom: Number(d.bottom) || 0, vh: Number(d.vh) || 0 }
      pinFixed()
    }
    /* Studio en vivo: el host manda el CSS de los editores finos
     * (surfaces/fotos/fondo/botones/roles) — se inlinea en un <style>
     * propio que gana por !important, igual que la hoja horneada. */
    if (d.type === 'davent:ds-studio-css') {
      var st = document.getElementById('ds-studio-css')
      if (!st) {
        st = document.createElement('style')
        st.id = 'ds-studio-css'
        document.head.appendChild(st)
      }
      st.textContent = typeof d.css === 'string' ? d.css : ''
    }
  })

  document.addEventListener('click', function (e) {
    var t = e.target
    if (!t || !t.closest) return
    /* CTA de carrito inyectado (tienda con venta online): el documento no
     * puede llamar a la API del carrito (origen opaco) — avisa al host, que
     * resuelve sesión/alta y abre el drawer. Va ANTES de data-ds-product:
     * el botón vive dentro de la tarjeta y sin este corte navegaría a la
     * ficha en vez de agregar. */
    var buyBtn = t.closest('[data-ds-buy]')
    if (buyBtn) {
      e.preventDefault()
      e.stopPropagation()
      parent.postMessage({ type: 'davent:ds-buy', id: buyBtn.getAttribute('data-ds-buy') || '' }, '*')
      return
    }
    /* "Comprar ahora" de la ficha (variante ghost junto al CTA de
     * carrito): compra directa — el host hace alta silenciosa y va al
     * checkout. Mismo contrato de id que ds-buy. */
    var buyNowBtn = t.closest('[data-ds-buy-now]')
    if (buyNowBtn) {
      e.preventDefault()
      e.stopPropagation()
      parent.postMessage({ type: 'davent:ds-buy-now', id: buyNowBtn.getAttribute('data-ds-buy-now') || '' }, '*')
      return
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
      /* El destino existe pero está oculto (otra superficie o flag
       * apagado): si el link además navega por data-ds-route, el scroll
       * se reintenta al activarse la superficie destino. */
      if (sectionEl && anchor.getAttribute('data-ds-route')) pendingAnchor = hash
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
    /* Categoría del escaparate -> catálogo filtrado: mismo contrato que
     * `data-ds-brand`, con el valor recortado a 40 chars como `data-cat`
     * de las tarjetas. */
    var catHit = t.closest('[data-ds-cat]')
    if (catHit) {
      state.cat = catHit.getAttribute('data-ds-cat') || ''
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
        /* Solo scrollea si el destino es visible: uno oculto (display:none
         * por superficie o flag) tiene rect en 0,0 y el host terminaría
         * arriba del documento en vez de en la sección. */
        if (targetEl && targetEl.getClientRects().length) {
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
    syncCardDock()
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
        /*Scrim del diseño (data-ds-filters-scrim): clic fuera de la hoja
         *la cierra igual que el botón "Aplicar"/"Cerrar".*/
        document.addEventListener('click', function (e) {
          var scrim = e.target && e.target.closest ? e.target.closest('[data-ds-filters-scrim]') : null
          if (scrim && panel.classList.contains('is-open')) closeSheet(true)
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
    panel.setAttribute('role', 'listbox')
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
  /* ==================================================================
   * CHATBOT DEL NEGOCIO (beneficio has_chatbot)
   *
   * El documento no puede pedir la API solo (origen opaco): la config
   * {greeting, qa} viaja en el payload público de la tienda y se pide por
   * el relay `ds-api` (mismo endpoint que ya usa el host). La piel la pone
   * el CSS de cada diseño sobre las clases `.ds-chat-*`; la base neutra
   * se inyecta acá con los tokens `--ds-*`/`--ink`/`--surface` del diseño.
   * Sin chatbot habilitado el payload llega con `chatbot: null` y no se
   * monta nada.
   * ================================================================== */
  var CHAT_FALLBACK = 'Todavía no tengo una respuesta para eso. Podés escribirnos desde la sección "Contáctanos" de esta página y te respondemos en persona.'
  var chat = null
  var CHAT_CSS = ''
    + '.ds-chat{position:fixed;right:16px;top:0;bottom:auto;z-index:70;display:flex;flex-direction:column;align-items:flex-end;gap:12px;font-family:inherit}'
    + '.ds-chat-fab{position:relative;width:56px;height:56px;flex:none;border:0;border-radius:50%;cursor:pointer;display:grid;place-items:center;background:var(--ds-accent,var(--accent,#4f46e5));color:var(--ds-accent-ink,#fff);box-shadow:0 10px 28px rgba(0,0,0,.28);transition:transform .15s,box-shadow .2s}'
    + '.ds-chat-fab:hover{transform:translateY(-2px)}'
    + '.ds-chat-fab:active{transform:scale(.94)}'
    + '.ds-chat-fab svg{width:26px;height:26px}'
    + '.ds-chat-panel{width:min(380px,calc(100vw - 32px));height:min(620px,calc(var(--ds-chat-vh,680px) - 140px - var(--ds-chat-lift,0px)));min-height:300px;display:flex;flex-direction:column;background:var(--surface,var(--ds-surface,#fff));color:var(--ink,var(--ds-text,#1a1a1a));border:1px solid var(--line,var(--ds-border,#e5e7eb));border-radius:var(--ds-radius,16px);box-shadow:0 24px 60px rgba(0,0,0,.3);overflow:hidden;font-family:inherit}'
    + '.ds-chat-head{display:flex;align-items:center;gap:10px;padding:13px 14px;background:var(--ds-accent,var(--accent,#4f46e5));color:var(--ds-accent-ink,#fff)}'
    + '.ds-chat-avatar{width:36px;height:36px;flex:none;border-radius:12px;display:grid;place-items:center;background:rgba(255,255,255,.16);font-weight:800;font-size:15px;overflow:hidden}'
    + '.ds-chat-avatar img{width:100%;height:100%;object-fit:cover}'
    + '.ds-chat-id{flex:1;min-width:0;display:grid}'
    + '.ds-chat-id strong{font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}'
    + '.ds-chat-id small{font-size:11.5px;opacity:.85;display:inline-flex;align-items:center;gap:4px}'
    + '.ds-chat-close{width:30px;height:30px;flex:none;border:0;border-radius:8px;background:transparent;color:inherit;display:grid;place-items:center;cursor:pointer}'
    + '.ds-chat-close:hover{background:rgba(255,255,255,.18)}'
    + '.ds-chat-log{flex:1;overflow-y:auto;padding:14px;display:grid;gap:10px;align-content:start;background:var(--bg,var(--ds-bg,#f6f7fb))}'
    + '.ds-chat-msg{max-width:92%;display:flex}'
    + '.ds-chat-msg p{margin:0;padding:9px 12px;border-radius:14px;font-size:13.5px;line-height:1.5;white-space:pre-line;overflow-wrap:anywhere}'
    + '.ds-chat-msg.bot p{background:var(--surface,var(--ds-surface,#fff));border:1px solid var(--line,var(--ds-border,#e5e7eb));color:var(--ink,var(--ds-text,#1a1a1a));border-bottom-left-radius:4px}'
    + '.ds-chat-msg.user{justify-self:end}'
    + '.ds-chat-msg.user p{background:var(--ds-accent,var(--accent,#4f46e5));color:var(--ds-accent-ink,#fff);border-bottom-right-radius:4px}'
    + '.ds-chat-typing{display:inline-flex;gap:4px;align-items:center;min-width:38px}'
    + '.ds-chat-typing i{width:6px;height:6px;border-radius:50%;background:var(--muted,var(--ds-muted,#6b7280));animation:ds-chat-dot 1s infinite}'
    + '.ds-chat-typing i:nth-child(2){animation-delay:.15s}'
    + '.ds-chat-typing i:nth-child(3){animation-delay:.3s}'
    + '@keyframes ds-chat-dot{0%,60%,100%{transform:translateY(0);opacity:.45}30%{transform:translateY(-4px);opacity:1}}'
    + '.ds-chat-sugg{display:flex;flex-direction:column;align-items:flex-end;gap:6px}'
    + '.ds-chat-chip{max-width:88%;border:1.5px solid var(--ds-accent,var(--accent,#4f46e5));border-radius:14px;border-bottom-right-radius:4px;background:var(--surface,var(--ds-surface,#fff));color:var(--ds-accent-text,var(--ds-accent,var(--accent,#4f46e5)));font:inherit;font-size:13px;font-weight:600;line-height:1.45;padding:9px 12px;cursor:pointer;text-align:left}'
    + '.ds-chat-chip:hover{background:color-mix(in srgb,var(--ds-accent,var(--accent,#4f46e5)) 10%,var(--surface,var(--ds-surface,#fff)))}'
    + '.ds-chat-bar{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--line,var(--ds-border,#e5e7eb));background:var(--surface,var(--ds-surface,#fff))}'
    + '.ds-chat-input{flex:1;min-width:0;border:1px solid var(--line,var(--ds-border,#e5e7eb));border-radius:99px;background:var(--bg,var(--ds-bg,#f6f7fb));color:var(--ink,var(--ds-text,#1a1a1a));font:inherit;font-size:13.5px;padding:8px 14px;outline:none}'
    + '.ds-chat-input:focus{border-color:var(--ds-accent,var(--accent,#4f46e5))}'
    + '.ds-chat-send{width:38px;height:38px;flex:none;border:0;border-radius:50%;background:var(--ds-accent,var(--accent,#4f46e5));color:var(--ds-accent-ink,#fff);display:grid;place-items:center;cursor:pointer}'
    + '.ds-chat-send:disabled{opacity:.45;cursor:default}'
    + '@media (prefers-reduced-motion:reduce){.ds-chat-typing i{animation:none}.ds-chat-fab,.ds-chat-send,.ds-chat-chip{transition:none}}'
  var CHAT_ICON_BOT = '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V4M8 13h.01M16 13h.01"/><path d="M9 17v2M15 17v2"/></svg>'
  var CHAT_ICON_SEND = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>'
  var CHAT_ICON_X = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>'
  var CHAT_ICON_BOT_SM = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V4M8 13h.01M16 13h.01"/></svg>'
  function chatNorm(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
  }
  /* Misma heurística que el StoreBot de la plantilla Vue: exacta >
   * contención > palabras de la pregunta en el texto (score >= 2). */
  function chatFindAnswer(text) {
    var t = chatNorm(text)
    if (!t || !chat) return null
    var best = null
    var score = 0
    ;(chat.qa || []).forEach(function (item) {
      var q = chatNorm(item.q)
      if (!q) return
      var s = 0
      if (t === q) s += 20
      else if (t.length > 3 && q.indexOf(t) >= 0) s += 6
      else if (q.length > 3 && t.indexOf(q) >= 0) s += 8
      q.split(/[^a-z0-9ñ]+/).forEach(function (w) {
        if (w.length > 3 && t.indexOf(w) >= 0) s += 2
      })
      if (s > score) { score = s; best = item }
    })
    return score >= 2 ? best.a : null
  }
  function mountChatbot(store, cfg) {
    var name = String(store.business_name || '').trim() || 'La tienda'
    var initial = (name.charAt(0) || 'T').toUpperCase()
    var cust = store.customization && typeof store.customization === 'object' ? store.customization : {}
    var logo = /^https?:\/\//.test(String(cust.logo || '')) ? cust.logo : ''
    var qa = (Array.isArray(cfg.qa) ? cfg.qa : []).filter(function (i) { return i && i.q && i.a })
    var greeting = String(cfg.greeting || '').trim() || ('¡Hola! Soy el asistente de ' + name + '. ¿En qué te puedo ayudar?')

    var st = document.createElement('style')
    st.textContent = CHAT_CSS
    /* Antes de la hoja del diseño: la base neutra queda DEBAJO de su CSS,
     * así las reglas `.ds-chat-*` de cada patrón (misma especificidad,
     * más abajo en el documento) la pisan sin !important. */
    document.head.insertBefore(st, document.querySelector('style') || null)

    var root = document.createElement('div')
    root.className = 'ds-chat'
    root.setAttribute('data-ds-no-pin', '')
    root.innerHTML =
      '<section class="ds-chat-panel" role="dialog" aria-label="Asistente de ' + esc(name) + '" hidden>' +
        '<header class="ds-chat-head">' +
          '<span class="ds-chat-avatar">' + (logo ? '<img src="' + esc(logo) + '" alt="">' : esc(initial)) + '</span>' +
          '<span class="ds-chat-id"><strong>' + esc(name) + '</strong><small>' + CHAT_ICON_BOT_SM + ' Asistente virtual</small></span>' +
          '<button type="button" class="ds-chat-close" aria-label="Cerrar">' + CHAT_ICON_X + '</button>' +
        '</header>' +
        '<div class="ds-chat-log" role="log" aria-live="polite"></div>' +
        '<form class="ds-chat-bar">' +
          '<input class="ds-chat-input" type="text" maxlength="200" placeholder="Escribí tu mensaje" autocomplete="off">' +
          '<button type="submit" class="ds-chat-send" aria-label="Enviar">' + CHAT_ICON_SEND + '</button>' +
        '</form>' +
      '</section>' +
      '<button type="button" class="ds-chat-fab" aria-label="Abrir asistente" aria-expanded="false">' + CHAT_ICON_BOT + '</button>'
    document.body.appendChild(root)

    chat = {
      root: root,
      qa: qa,
      asked: {},
      greeted: false,
      typing: false,
      log: root.querySelector('.ds-chat-log'),
      panel: root.querySelector('.ds-chat-panel'),
      input: root.querySelector('.ds-chat-input'),
      fab: root.querySelector('.ds-chat-fab')
    }

    function pushMsg(from, text) {
      var row = document.createElement('div')
      row.className = 'ds-chat-msg ' + from
      var p = document.createElement('p')
      p.textContent = text
      row.appendChild(p)
      chat.log.appendChild(row)
      chat.log.scrollTop = chat.log.scrollHeight
    }
    function clearTyping() {
      var t = chat.log.querySelector('.ds-chat-typing')
      if (t) t.remove()
    }
    function renderChips() {
      var old = chat.log.querySelector('.ds-chat-sugg')
      if (old) old.remove()
      var items = []
      ;(chat.qa || []).forEach(function (item, i) { if (!chat.asked[i]) items.push({ item: item, i: i }) })
      if (!items.length) return
      var box = document.createElement('div')
      box.className = 'ds-chat-sugg'
      items.slice(0, 4).forEach(function (x) {
        var b = document.createElement('button')
        b.type = 'button'
        b.className = 'ds-chat-chip'
        b.textContent = x.item.q
        b.addEventListener('click', function () { reply(x.item.q, x.i) })
        box.appendChild(b)
      })
      chat.log.appendChild(box)
      chat.log.scrollTop = chat.log.scrollHeight
    }
    function reply(text, idx) {
      pushMsg('user', text)
      if (idx != null) chat.asked[idx] = true
      chat.typing = true
      var t = document.createElement('div')
      t.className = 'ds-chat-msg bot ds-chat-typing'
      t.innerHTML = '<i></i><i></i><i></i>'
      chat.log.appendChild(t)
      chat.log.scrollTop = chat.log.scrollHeight
      setTimeout(function () {
        chat.typing = false
        clearTyping()
        var answer = idx != null ? chat.qa[idx].a : chatFindAnswer(text)
        pushMsg('bot', answer || CHAT_FALLBACK)
        renderChips()
        syncChatMetrics()
      }, 450)
    }
    function setOpen(open) {
      chat.panel.hidden = !open
      chat.fab.setAttribute('aria-expanded', open ? 'true' : 'false')
      if (open) {
        if (!chat.greeted) { chat.greeted = true; pushMsg('bot', greeting); renderChips() }
        chat.input.focus()
      }
      syncChatMetrics()
    }
    chat.fab.addEventListener('click', function () { setOpen(chat.panel.hidden) })
    root.querySelector('.ds-chat-close').addEventListener('click', function () { setOpen(false) })
    root.querySelector('.ds-chat-bar').addEventListener('submit', function (e) {
      e.preventDefault()
      var text = chat.input.value.trim()
      if (!text || chat.typing) return
      chat.input.value = ''
      reply(text.slice(0, 200))
    })
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && chat && !chat.panel.hidden) setOpen(false)
    })
    syncChatMetrics()
  }
  function initChatbot() {
    /* El slug sale de la propia URL del documento
     * (/api/stores/public/<slug>/pattern/document/): el payload público
     * ya filtra `chatbot` por beneficio + switch del dueño. */
    var m = /\/api\/stores\/public\/([a-z0-9-]+)\/pattern\//.exec(location.pathname || '')
    if (!m) return
    api('/api/stores/public/' + m[1] + '/').then(function (out) {
      var data = out && out.ok && out.data ? out.data : null
      var cfg = data && data.chatbot
      if (!cfg) return
      mountChatbot(data, cfg)
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
  /* ===== E-commerce: CTA "Agregar al carrito" + píldora de carrito =====
   * Solo cuando el documento declara data-ds-commerce (la tienda vende
   * online — orders_enabled del backend). El botón nunca habla con la API:
   * postMessage 'davent:ds-buy' al host, que tiene la sesión del comprador.
   * Se inyecta en las tarjetas .ds-product (marcado compartido del
   * fragmento de catálogo) y en la ficha [data-surface="product"] antes de
   * su CTA de WhatsApp — sin reescribir el HTML de ningún diseño.
   *
   * Anclaje del botón en tarjeta: va dentro de `.dsx-buy-wrap`, un flex
   * column propio. `.ds-product>.dsx-buy-wrap{margin-top:auto}` absorbe el
   * alto libre cuando la tarjeta es flex/grid (las tarjetas de una fila se
   * estiran a la altura de la más alta y el CTA queda al pie, alineado en
   * toda la fila); en flujo normal `auto` colapsa a 0 y el botón conserva
   * su margen mínimo de 10px — el margen vive en el botón, no en el wrap,
   * así que no hace falta flex forzado para que se vea bien. Cuando la
   * tarjeta es block el puente le agrega `.dsx-col` (display:flex column)
   * para que el auto-margin funcione: sin eso una card block con link
   * `height:100%` dejaba el botón fuera de la caja (clipeado por
   * overflow:hidden o desbordado sobre la fila siguiente). */
  var COMMERCE_CSS =
    '.ds-product>.dsx-buy-wrap{margin-top:auto}' +
    '.ds-product.dsx-col{display:flex;flex-direction:column}' +
    '.dsx-buy-wrap{display:flex;flex-direction:column;min-width:0}' +
    '.dsx-buy{box-sizing:border-box;display:block;width:calc(100% - 24px);margin:10px 12px 12px;padding:12px 14px;' +
    'border:0;border-radius:var(--ds-radius-btn,var(--ds-radius,10px));cursor:pointer;' +
    'background:var(--ds-accent,#111);color:var(--ds-accent-ink,#fff);' +
    'font:inherit;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;' +
    'box-shadow:0 1px 2px rgba(0,0,0,.10);' +
    'transition:transform .16s ease,box-shadow .22s ease,background-color .2s ease,filter .2s ease}' +
    '.dsx-buy:hover{transform:translateY(-1px);' +
    'box-shadow:0 10px 22px -10px color-mix(in srgb,var(--ds-accent,#111) 60%,transparent)}' +
    '.dsx-buy:active{transform:translateY(0) scale(.985);filter:brightness(.96)}' +
    '.dsx-buy:focus-visible{outline:2px solid var(--ds-accent,#111);outline-offset:2px}' +
    '.dsx-buy[disabled]{opacity:.55;cursor:default;transform:none;box-shadow:none;filter:none}' +
    '.dsx-buy.is-added{background:var(--ds-success,#0f9d58);' +
    'color:var(--ds-success-ink,var(--ds-accent-ink,#fff))}' +
    /* La regla ancha es SOLO para el CTA de la ficha: los .dsx-buy de las
     * tarjetas de relacionados (.pdp-rel) son .ds-product comunes y deben
     * conservar width:calc(100% - 24px) — un min-width:200px ahí desborda
     * la celda del grid en mobile (hscroll). max-width:100% blinda el CTA
     * de la ficha dentro de paneles angostos. */
    '[data-surface="product"] .dsx-buy[data-ds-buy-slot="pdp"]{width:auto;min-width:200px;max-width:100%;margin:0 0 12px}' +
    /* "Comprar ahora" de la ficha: acción SECUNDARIA liviana — enlace de
     * acento con flecha, no un segundo botón macizo (dos CTA gigantes
     * apilados se veían pegados e informales). Sin borde ni relleno: la
     * jerarquía la da el CTA del diseño; este se apoya debajo con aire y
     * se alinea al inicio del panel. `font:inherit` mantiene la voz
     * tipográfica de cada piel. */
    '.dsx-buy-now{box-sizing:border-box;display:inline-flex;align-items:center;gap:6px;' +
    'width:fit-content;max-width:100%;margin:12px 0 0;padding:6px 2px;' +
    'border:0;background:none;cursor:pointer;' +
    'color:var(--ds-accent-text,var(--ds-accent,#111));' +
    'font:inherit;font-size:13.5px;font-weight:700;letter-spacing:.01em;text-transform:none;' +
    'text-decoration:underline;text-underline-offset:4px;text-decoration-thickness:1px;' +
    'transition:opacity .18s ease,color .18s ease}' +
    '.dsx-buy-now::after{content:"→";font-size:1em;line-height:1;transition:transform .18s ease}' +
    '.dsx-buy-now:hover{opacity:.82}' +
    '.dsx-buy-now:hover::after{transform:translateX(3px)}' +
    '.dsx-buy-now:active{opacity:.7}' +
    '.dsx-buy-now:focus-visible{outline:2px solid var(--ds-accent,#111);outline-offset:3px;border-radius:2px}' +
    '.dsx-buy-now[disabled]{opacity:.5;cursor:default}' +
    /* En la ficha el enlace se apoya bajo el CTA con separación explícita
     * (los contenedores flex de los diseños traen gap propio; el margen
     * suma aire y evita que quede pegado al borde del botón). */
    '[data-surface="product"] .dsx-buy-now[data-ds-buy-slot="pdp"]{margin:12px 0 4px}' +
    /* Entrada de cuenta del comprador y acceso al carrito: píldoras
     * gemelas en el header/nav del diseño (mismo alto, radio, trazo de
     * icono y tipografía) o, sin slot, píldoras fijas abajo a la
     * izquierda — la cuenta apoya en bottom:16 y el carrito se apila
     * encima (bottom:64) para no pisarse; el anclaje al marco lo hace el
     * pin de barras (data-ds-pin="bottom"), igual que la tab bar de cada
     * diseño. Heredan color del header como .ds-theme-toggle: si una
     * banda fija pinta su propia tinta (toldo amarillo, cabecera crema
     * sobre papel), el diseño fija color/border-color sobre .dsx-account
     * / .dsx-cart dentro de su .top/.head — mismo gancho de override que
     * el toggle de tema. */
    '.dsx-account,.dsx-cart{box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;' +
    'gap:7px;min-height:36px;padding:8px 14px;border:1px solid currentColor;border-radius:999px;' +
    'background:transparent;color:inherit;font:inherit;font-size:12.5px;font-weight:600;letter-spacing:.04em;' +
    'cursor:pointer;opacity:.82;-webkit-tap-highlight-color:transparent;' +
    'transition:opacity .18s ease,transform .18s ease,background-color .18s ease,border-color .18s ease}' +
    '.dsx-account{margin-inline-start:auto}' +
    '.dsx-account:hover,.dsx-cart:hover{opacity:1;transform:translateY(-1px);' +
    'background:color-mix(in srgb,currentColor 10%,transparent)}' +
    '.dsx-account:active,.dsx-cart:active{transform:translateY(0) scale(.97)}' +
    '.dsx-account:focus-visible,.dsx-cart:focus-visible{outline:2px solid currentColor;outline-offset:2px}' +
    '.dsx-account svg,.dsx-cart svg{flex:none}' +
    '.dsx-cart{position:relative}' +
    /* Badge del contador: el par --ds-accent/--ds-accent-ink ya viene
     * pensado para contraste AA (es la tinta que el diseño usa sobre su
     * acento); el anillo de superficie lo despega del borde de la
     * píldora. */
    '.dsx-cart-badge{box-sizing:border-box;position:absolute;top:-7px;right:-7px;min-width:18px;height:18px;' +
    'padding:0 5px;border-radius:999px;pointer-events:none;' +
    'background:var(--ds-accent,#111);color:var(--ds-accent-ink,#fff);' +
    'font-size:10px;font-weight:800;line-height:18px;letter-spacing:0;text-align:center;' +
    'font-variant-numeric:tabular-nums;box-shadow:0 0 0 2px var(--ds-surface,var(--surface,#fff))}' +
    '.dsx-cart-badge[hidden]{display:none}' +
    '.dsx-cart-badge.is-bump{animation:dsx-cart-bump .32s cubic-bezier(.2,.9,.3,1.4)}' +
    '@keyframes dsx-cart-bump{0%{transform:scale(1)}45%{transform:scale(1.4)}100%{transform:scale(1)}}' +
    '.dsx-account--fab,.dsx-cart--fab{position:fixed;z-index:72;margin:0;opacity:1;' +
    'background:var(--ds-surface,var(--surface,#fff));color:var(--ds-text,var(--ink,#1a1a1a));' +
    'border:1px solid var(--ds-border,var(--line,#e5e7eb));box-shadow:0 10px 28px rgba(0,0,0,.22)}' +
    '.dsx-account--fab{left:16px;bottom:16px}' +
    '.dsx-cart--fab{left:16px;bottom:64px}' +
    /* Mobile: el cluster brand+acciones+píldoras+toggle no entra en
     * ~390px (la píldora de cuenta ya lo desbordaba antes del carrito).
     * Bajo 560px la píldora de cuenta pasa a solo-icono (el aria-label
     * y el title siguen anunciando "Ingresar"/"Mi cuenta") y ambas se
     * compactan — el carrito queda entero dentro del header. Los
     * diseños pueden revertirlo con reglas propias más específicas. */
    '@media (max-width:560px){' +
    '.dsx-account [data-dsx-account-label]{display:none}' +
    '.dsx-account,.dsx-cart{min-height:34px;padding:7px 11px;gap:5px;font-size:11.5px}' +
    '.dsx-account svg,.dsx-cart svg{width:14px;height:14px}}' +
    '@media (prefers-reduced-motion:reduce){' +
    '.dsx-buy,.dsx-buy-now,.dsx-account,.dsx-cart,.dsx-cart-badge{transition:none;animation:none}' +
    '.dsx-buy:hover,.dsx-buy-now:hover,.dsx-account:hover,.dsx-cart:hover{transform:none}' +
    '.dsx-buy-now:hover::after{transform:none}' +
    '.dsx-buy:active,.dsx-buy-now:active,.dsx-account:active,.dsx-cart:active{transform:none}}'
  function dsBuyButton(pid, slot) {
    var b = document.createElement('button')
    b.type = 'button'
    b.className = 'dsx-buy'
    b.setAttribute('data-ds-buy', String(pid))
    if (slot) b.setAttribute('data-ds-buy-slot', slot)
    b.textContent = 'Agregar al carrito'
    return b
  }
  /* "Comprar ahora" de la ficha: hermano del CTA de carrito, variante
   * ghost (.dsx-buy-now). NO lleva data-ds-buy — su click viaja por
   * 'davent:ds-buy-now' y el host hace alta silenciosa + checkout. */
  function dsBuyNowButton(pid, slot) {
    var b = document.createElement('button')
    b.type = 'button'
    b.className = 'dsx-buy-now'
    b.setAttribute('data-ds-buy-now', String(pid))
    if (slot) b.setAttribute('data-ds-buy-slot', slot)
    b.textContent = 'Comprar ahora'
    return b
  }
  function injectCardBuys() {
    var cards = document.querySelectorAll('.ds-product:not([data-ds-buy-done])')
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i]
      var link = card.querySelector('[data-ds-product]')
      var pid = link ? link.getAttribute('data-ds-product') : ''
      if (!pid) continue
      card.setAttribute('data-ds-buy-done', '1')
      /* El botón va en `.dsx-buy-wrap` (flex column propio): el
       * `margin-top:auto` del wrap lo ancla al pie cuando la tarjeta es
       * flex/grid — en flujo normal colapsa a 0 sin perder el margen
       * mínimo del botón. */
      var wrap = document.createElement('div')
      wrap.className = 'dsx-buy-wrap'
      wrap.appendChild(dsBuyButton(pid))
      card.appendChild(wrap)
    }
    syncCardDock()
  }
  /* `.ds-col` en la tarjeta: solo cuando su display computado NO es
   * flex ni grid (block, inline-block, flow-root…). Las tarjetas flex/grid
   * ya reparten el alto libre solas; forzarles flex/grid rompería su
   * propia estructura. Las ocultas (`display:none` por filtro) y las
   * `display:contents` se saltean: la clase queda como estaba y se
   * reevalúa en la próxima pasada (applyCatalog corre tras cada filtro). */
  function syncCardDock() {
    var wraps = document.querySelectorAll('.ds-product>.dsx-buy-wrap')
    for (var i = 0; i < wraps.length; i++) {
      var card = wraps[i].parentNode
      var disp = ''
      try { disp = String(window.getComputedStyle(card).display || '') } catch (e) {}
      if (!disp || disp === 'none' || disp === 'contents') continue
      card.classList.toggle('dsx-col', disp.indexOf('flex') < 0 && disp.indexOf('grid') < 0)
    }
  }
  /* El "Comprar ahora" hereda el `order` del CTA al que acompaña: varios
   * diseños ordenan los hijos del panel con `order` (mercado: título 1,
   * precio 3, CTA 4…) y un hijo nuevo sin order cae al principio del flex
   * (el enlace aparecía sobre el título). Con el mismo order + DOM
   * adyacente, queda siempre inmediatamente después del CTA. */
  function syncBuyNowOrder(nowBtn, ctaBtn) {
    if (!nowBtn || !ctaBtn) return
    try {
      var order = window.getComputedStyle(ctaBtn).order
      if (order && order !== '0') nowBtn.style.order = order
    } catch (e) {}
  }
  /* Si el contenedor de compra es flex/grid, el enlace queda EN FILA con el
   * CTA y el aire lo da el gap del diseño: el margen superior propio
   * desalineaba las líneas base (umbral). En flujo de bloque (paneles que
   * no ordenan sus hijos) se conserva el margen para separarlo del botón. */
  function relaxBuyNowMargin(nowBtn) {
    var parent = nowBtn && nowBtn.parentElement
    if (!parent) return
    try {
      var display = window.getComputedStyle(parent).display || ''
      if (display.indexOf('flex') >= 0 || display.indexOf('grid') >= 0) nowBtn.style.marginTop = '0'
    } catch (e) {}
  }
  /* Envío y medios de pago viven en el panel de la ficha, después del
   * precio. Los diseños que ordenan los hijos del panel con `order`
   * (mercado: título 1, precio 3, CTA 4…) dejaban estos dos nodos del host
   * al principio del flex (arriba del título): se les copia el order del
   * bloque de precio — con el mismo valor quedan justo después de él en
   * el orden del DOM, antes del CTA. Sin `order` en el diseño no se toca
   * nada (el orden natural ya es el correcto). */
  function syncPdpMetaOrder(pdp) {
    var price = pdp.querySelector('.pdp-price, [class*="price"]')
    if (!price) return
    var order = ''
    try { order = window.getComputedStyle(price).order || '' } catch (e) {}
    if (!order || order === '0') return
    var meta = pdp.querySelectorAll('.ds-ship, .ds-pay')
    for (var i = 0; i < meta.length; i++) meta[i].style.order = order
  }
  function injectPdpBuy() {
    var pdp = document.querySelector('[data-surface="product"]')
    //Ojo: la ficha también contiene tarjetas de relacionados ya inyectadas
    //— el guard busca el CTA de la ficha, no cualquier .dsx-buy.
    if (!pdp) return
    //?product= sin resolver: la superficie marcada no es una ficha real —
    //el aviso de "no disponible" la reemplaza (paintMissingProduct).
    if (pdp.hasAttribute('data-ds-pdp-missing')) return
    syncPdpMetaOrder(pdp)
    //El id del producto viaja en la URL del documento (?product=<pk>).
    var pid = ''
    try { pid = new URLSearchParams(window.location.search).get('product') || '' } catch (e) {}
    if (!pid) return
    var existing = pdp.querySelector('[data-ds-buy-slot="pdp"]')
    if (existing) {
      /* Ya hay CTA de ficha: si es el par inyectado (.dsx-buy) no hay nada
       * que hacer; si es un botón PROPIO del diseño (moderntec trae su
       * .pdp-buy con data-ds-buy — postea ds-buy solo) solo se le suma el
       * "Comprar ahora" al lado, sin duplicar el de carrito. */
      if (!existing.classList.contains('dsx-buy') && !pdp.querySelector('.dsx-buy-now')) {
        var ownNow = dsBuyNowButton(pid, 'pdp')
        existing.parentNode.insertBefore(ownNow, existing.nextSibling)
        syncBuyNowOrder(ownNow, existing)
        relaxBuyNowMargin(ownNow)
      }
      return
    }
    //Slot: antes del CTA de WhatsApp del diseño (clases/ hrefs conocidos
    //del fragmento compartido). Fallback: al inicio del panel de info.
    var wa = pdp.querySelector('a[href*="wa.me"], a[href*="whatsapp"], a[href*="/r/whatsapp"]')
    var slot = wa ? (wa.closest('.pdp-buy,.pdp-ctas,.pdp-actions,[class*="cta"],[class*="buy"]') || wa) : null
    /* Tienda sin WhatsApp: el anchor sale con href="" y `wa` no lo encuentra.
     * Si el diseño declara su grupo de acciones, el CTA cae ahí igual — el
     * fallback al h1 lo dejaba flotando arriba de la ref y del precio. */
    if (!slot) slot = pdp.querySelector('.pdp-actions,.pdp-ctas,.pdp-buy')
    if (!slot) {
      slot = pdp.querySelector('.pdp-info, aside, [class*="info"], [class*="panel"]')
      if (slot) {
        var h1 = slot.querySelector('h1')
        var anchor = h1 ? h1.nextSibling : slot.firstChild
        var fallbackBtn = dsBuyButton(pid, 'pdp')
        var fallbackNow = dsBuyNowButton(pid, 'pdp')
        slot.insertBefore(fallbackBtn, anchor)
        slot.insertBefore(fallbackNow, anchor)
        syncBuyNowOrder(fallbackNow, fallbackBtn)
        relaxBuyNowMargin(fallbackNow)
        return
      }
    }
    if (slot && slot.parentNode) {
      var pdpBtn = dsBuyButton(pid, 'pdp')
      /* Si el slot es el CONTENEDOR de CTAs del diseño (.pdp-actions,
       * .pdp-ctas — el anchor de WhatsApp vive adentro), el botón entra
       * como primer ítem del grupo (en un flex queda hermano del CTA).
       * Si el slot ES el anchor o un inline, va de hermano antes: un
       * <button> dentro de <a> es HTML inválido. El "Comprar ahora" queda
       * siempre como hermano inmediato del de carrito. */
      if (slot !== wa && /^(DIV|SECTION|NAV|ASIDE|FOOTER|HEADER|P|UL|LI)$/.test(slot.tagName)) {
        slot.insertBefore(pdpBtn, slot.firstChild)
      } else {
        slot.parentNode.insertBefore(pdpBtn, slot)
      }
      var nowBtn = dsBuyNowButton(pid, 'pdp')
      pdpBtn.parentNode.insertBefore(nowBtn, pdpBtn.nextSibling)
      /* El order se copia del CTA de la ficha (no del contenedor) y, si el
       * contenedor es un grupo flex con `order` propio en sus ítems, se
       * copia el del primer ítem para caer en el mismo bloque. */
      syncBuyNowOrder(nowBtn, pdpBtn)
      relaxBuyNowMargin(nowBtn)
      if (!nowBtn.style.order && slot !== wa) {
        var firstChild = slot.firstElementChild
        if (firstChild && firstChild !== pdpBtn && firstChild !== nowBtn) syncBuyNowOrder(nowBtn, firstChild)
      }
    }
  }
  /* Ficha de producto que no resuelve (?product= inexistente, inactivo o
   * ajeno): el servidor marca la superficie con `data-ds-pdp-missing` y
   * acá se reemplaza el contenido vacío ("· Ref. ·") por un aviso con
   * salida — fallback único para todos los diseños importados. Estilos
   * inline con tokens --ds-*: no depende de la hoja del diseño ni de los
   * flags de comercio/chat. */
  function paintMissingProduct() {
    var pdp = document.querySelector('[data-surface="product"][data-ds-pdp-missing]')
    if (!pdp || pdp.getAttribute('data-ds-missing-painted')) return
    pdp.setAttribute('data-ds-missing-painted', '1')
    var hasCatalog = !!document.querySelector('[data-surface="catalog"]')
    var box = document.createElement('div')
    box.setAttribute('data-ds-no-pin', '')
    box.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;min-height:46vh;padding:48px 20px;text-align:center;color:var(--ds-text,var(--ink,#1a1a1a));font-family:inherit;box-sizing:border-box'
    var msg = document.createElement('p')
    msg.textContent = 'Este producto ya no está disponible.'
    msg.style.cssText = 'margin:0;font-size:clamp(17px,2.4vw,22px);font-weight:700;line-height:1.3'
    var sub = document.createElement('p')
    sub.textContent = 'Puede que el comercio lo haya dado de baja del catálogo.'
    sub.style.cssText = 'margin:0;font-size:14px;line-height:1.5;opacity:.7;max-width:44ch'
    var btn = document.createElement('button')
    btn.type = 'button'
    btn.textContent = hasCatalog ? 'Ver el catálogo' : 'Volver al inicio'
    btn.style.cssText = 'margin-top:10px;min-height:44px;padding:0 24px;border:1px solid var(--ds-accent,var(--accent,#4f46e5));border-radius:var(--ds-radius,10px);background:var(--ds-accent,var(--accent,#4f46e5));color:var(--ds-accent-ink,#fff);font:inherit;font-size:14px;font-weight:700;cursor:pointer'
    btn.addEventListener('click', function () {
      go(hasCatalog ? 'catalog' : 'home')
    })
    box.appendChild(msg)
    box.appendChild(sub)
    box.appendChild(btn)
    pdp.innerHTML = ''
    pdp.appendChild(box)
  }
  /* Entrada "Mi cuenta" / "Ingresar": el documento no conoce la sesión
   * del comprador (origen opaco, sin cookies ni storage del host) — el
   * host la informa por `davent:ds-account-state` y el clic viaja por
   * `davent:ds-account`; el host abre el modal de auth o navega a
   * /cuenta. Se monta en el header/nav del diseño cuando hay slot
   * ([data-ds-account-slot] explícito, o el masthead como el toggle de
   * tema); si no, como píldora fija abajo-izquierda que el pin de barras
   * ancla al marco (bottomChromePx además levanta el chat por encima). */
  var accountBtn = null
  var accountAuthed = false
  var ACCOUNT_ICON = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="3.4"/><path d="M4.8 20.2a7.2 7.2 0 0 1 14.4 0"/></svg>'
  function paintAccount() {
    if (!accountBtn) return
    var label = accountAuthed ? 'Mi cuenta' : 'Ingresar'
    var span = accountBtn.querySelector('[data-dsx-account-label]')
    if (span) span.textContent = label
    accountBtn.setAttribute('aria-label', label)
    accountBtn.setAttribute('title', label)
  }
  function mountAccount() {
    if (accountBtn || document.querySelector('.dsx-account')) return
    var host =
      document.querySelector('[data-ds-account-slot]') ||
      document.querySelector('header.top .top-inner') ||
      document.querySelector('header.top .top-in') ||
      document.querySelector('header.top') ||
      document.querySelector('header')
    accountBtn = document.createElement('button')
    accountBtn.type = 'button'
    accountBtn.className = 'dsx-account'
    accountBtn.innerHTML = ACCOUNT_ICON + '<span data-dsx-account-label></span>'
    accountBtn.addEventListener('click', function () {
      parent.postMessage({ type: 'davent:ds-account' }, '*')
    })
    if (host) {
      var ref = host.querySelector('.ds-theme-toggle')
      if (ref) host.insertBefore(accountBtn, ref)
      else host.appendChild(accountBtn)
    } else {
      accountBtn.classList.add('dsx-account--fab')
      /* Anclaje declarado: collectFixed la clasifica 'bottom' y pinFixed
       * la apoya sobre el borde visible del marco (el iframe va estirado
       * y un fixed crudo quedaría al pie del documento entero). */
      accountBtn.setAttribute('data-ds-pin', 'bottom')
      document.body.appendChild(accountBtn)
      resetFixed()
      pinFixed()
    }
    paintAccount()
  }
  /* Píldora de carrito junto a la de cuenta: mismo slot del header (o
   * [data-ds-cart-slot] / [data-ds-account-slot] si el diseño declara
   * uno), mismo fallback de píldora fija apilada sobre la de cuenta. El
   * documento no conoce el carrito — el host empuja el contador por
   * `davent:ds-cart-state` y el clic vuelve por `davent:ds-cart` (el
   * host navega a la página /carrito de la tienda). */
  var cartBtn = null
  var cartCount = 0
  var CART_ICON = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="20" r="1.5"/><circle cx="17" cy="20" r="1.5"/><path d="M3.5 4h2.2l2.3 11.4a1.6 1.6 0 0 0 1.6 1.3h7.9a1.6 1.6 0 0 0 1.6-1.3L20.5 8H6.2"/></svg>'
  function paintCart() {
    if (!cartBtn) return
    var badge = cartBtn.querySelector('.dsx-cart-badge')
    if (badge) {
      var label = cartCount > 99 ? '99+' : String(cartCount)
      if (badge.textContent !== label) {
        badge.textContent = label
        /* Micro-feedback al sumar unidades: el badge "pega" un pulso.
         * Se rearma la animación forzando reflow (sin framework). */
        if (cartCount > 0) {
          badge.classList.remove('is-bump')
          void badge.offsetWidth
          badge.classList.add('is-bump')
        }
      }
      badge.hidden = cartCount <= 0
    }
    var text = cartCount > 0
      ? 'Carrito, ' + cartCount + (cartCount === 1 ? ' producto' : ' productos')
      : 'Carrito'
    cartBtn.setAttribute('aria-label', text)
    cartBtn.setAttribute('title', text)
  }
  function mountCart() {
    if (cartBtn || document.querySelector('.dsx-cart')) return
    var host =
      document.querySelector('[data-ds-cart-slot]') ||
      document.querySelector('[data-ds-account-slot]') ||
      document.querySelector('header.top .top-inner') ||
      document.querySelector('header.top .top-in') ||
      document.querySelector('header.top') ||
      document.querySelector('header')
    cartBtn = document.createElement('button')
    cartBtn.type = 'button'
    cartBtn.className = 'dsx-cart'
    cartBtn.innerHTML = CART_ICON + '<span class="dsx-cart-badge" hidden aria-hidden="true"></span>'
    cartBtn.addEventListener('click', function () {
      parent.postMessage({ type: 'davent:ds-cart' }, '*')
    })
    if (host) {
      /* Pegada a la píldora de cuenta: se inserta justo después de ella
       * (el toggle de tema se monta más tarde, al final del header). */
      var ref = host.querySelector('.dsx-account')
      if (ref) host.insertBefore(cartBtn, ref.nextSibling)
      else host.appendChild(cartBtn)
    } else {
      cartBtn.classList.add('dsx-cart--fab')
      /* Se apila sobre la píldora de cuenta (bottom:16): bottom:64 la
       * deja flotando encima sin pisarla. data-ds-pin="bottom" la ancla
       * al marco visible, igual que la cuenta y la tab bar. */
      cartBtn.setAttribute('data-ds-pin', 'bottom')
      document.body.appendChild(cartBtn)
      resetFixed()
      pinFixed()
    }
    paintCart()
  }
  function injectCommerceCss() {
    if (document.querySelector('style[data-dsx-css]')) return
    var st = document.createElement('style')
    st.setAttribute('data-dsx-css', '')
    st.textContent = COMMERCE_CSS
    /* Antes de la hoja del diseño (igual que CHAT_CSS): la base .dsx-*
     * queda DEBAJO — los diseños ganan con sus reglas más específicas
     * (p. ej. `.top .dsx-account` de mercado) sin !important. */
    document.head.insertBefore(st, document.querySelector('style') || null)
  }
  /* Entrada "Ingresar"/"Mi cuenta": NO depende de la venta online — el
   * comprador puede tener cuenta con el carrito apagado (el dueño todavía
   * no activó e-commerce). Antes vivía dentro de initCommerce y la píldora
   * desaparecía de toda la web hasta habilitar el checkout. En la vista
   * previa del Studio no se monta (el documento llega con ?preview=). */
  function initAccount() {
    if (/(?:\?|&)preview=/.test(location.search || '')) return
    injectCommerceCss()
    mountAccount()
  }
  function initCommerce() {
    if (root.getAttribute('data-ds-commerce') !== '1') return
    injectCommerceCss()
    injectCardBuys()
    injectPdpBuy()
    mountCart()
    /* El catálogo reordena tarjetas (applyCatalog mueve nodos, no los
     * recrea) y el buscador puede filtrar — los botones inyectados viajan
     * con su tarjeta. Por si un diseño monta tarjetas por JS después,
     * reinyecta en el próximo frame y al cargar. */
    requestAnimationFrame(function () { injectCardBuys(); injectPdpBuy() })
    window.addEventListener('load', function () { injectCardBuys(); injectPdpBuy() })
    /* La ficha puede montarse después del primer pintado (diseño que arma
     * el PDP por JS): observer liviano que reintenta solo mientras falte
     * el CTA de ficha — con el slot puesto el guard de injectPdpBuy sale
     * sin tocar el DOM. */
    if ('MutationObserver' in window && document.body) {
      var pdpObs = new MutationObserver(function () {
        var surf = document.querySelector('[data-surface="product"]')
        if (surf && !surf.querySelector('[data-ds-buy-slot="pdp"]')) injectPdpBuy()
      })
      pdpObs.observe(document.body, { childList: true, subtree: true })
    }
  }
  initAccount()
  initCommerce()
  buildFilters()
  initSearch()
  initFilters()
  initView()
  initReviews()
  initContact()
  initChatbot()
  /* Hoja modal abierta: los diseños marcan <html> con `m-lock` y la hoja
   * de filtros del catálogo usa `filters-open` en <body> — ambas frenan
   * el scroll DENTRO del iframe, pero el scroll real es de la página host
   * y la hoja quedaba con el fondo moviéndose detrás. Se avisa por
   * postMessage y el host bloquea su scroll mientras dure. */
  var lastLock = null
  function syncLock() {
    var locked = root.classList.contains('m-lock') ||
      !!(document.body && document.body.classList.contains('filters-open'))
    if (locked === lastLock) return
    lastLock = locked
    parent.postMessage({ type: 'davent:ds-lock', locked: locked }, '*')
  }
  if ('MutationObserver' in window) {
    var lockObs = new MutationObserver(syncLock)
    lockObs.observe(root, { attributes: true, attributeFilter: ['class'] })
    if (document.body) lockObs.observe(document.body, { attributes: true, attributeFilter: ['class'] })
  }
  syncLock()
  syncFilterUI()
  applyCatalog()
  paintMissingProduct()
  mountThemeToggle()
  window.addEventListener('load', function () { catalog(); mountThemeToggle(); send() })
  if ('ResizeObserver' in window) new ResizeObserver(send).observe(root)
  else setTimeout(send, 120)
  send()
})()
