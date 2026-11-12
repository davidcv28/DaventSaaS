# Arquetipos navbar / cuenta / seguimiento — catálogo + matriz (tmp, se borra al final)

## Arquitectura

- Chrome compartido: `StorePublicLayout.vue` → `.store-page` ya expone
  `data-design` (slug del diseño), `data-template`, `data-skin`.
  Navbar = `.sp-top` + `.sp-drawer` + `.sp-tabbar` + `.sp-shop-nav`.
- Cuenta = `StoreAccountView.vue` (`.ec-account` → `.acc-shell` =
  `.acc-side` sidebar + `.acc-main`(`.acc-mhead` + `.acc-tabs` + `.acc-body`)).
- Seguimiento = `StoreTrackingView.vue` (`.ec-track`: head, help details,
  status card con `.ec-stepper`, cards de pago/prueba/items/recibo/timeline).
- Páginas de comercio (ingresar/cuenta/carrito/checkout/seguimiento) se
  tiñen con `assets/store-design-<slug>.css` (y `store-<tpl>.css` en
  páginas públicas de plantillas Vue). Los patrones HTML tienen su propio
  `<header>` dentro de `StoreApp/domains/design/sources/<slug>.html`
  (iframe sandbox; JS solo por nonce; nada de fetch/storage — postMessage).
- FASE 3 agrega `data-nav`/`data-account`/`data-tracking` en `.store-page`
  desde `composables/storeArchetypes.js` (matriz diseño → arquetipo).
  Las vistas NO se tocan: todo el look por arquetipo es CSS keyed en
  `.store-page[data-nav='…']` / `[data-account='…']` / `[data-tracking='…']`.

## Catálogo de arquetipos (selección 2024-26: shadcn, Aceternity, Magic UI,
## HyperUI, Flowbite, DaisyUI, Baymard, Mobbin, Awwwards)

### Navbar (26 asignados, todos distintos)
- `left-logo-standard` — logo izq, menú, íconos der; mobile drawer der.
- `center-logo-split` — grid 3 col: links izq, logo centro, acciones der; mobile panel bajo barra.
- `utility-plus-primary` — doble barra (utility fina + principal); mobile colapsa.
- `mega-menu` — items abren panel full-width con columnas/ofertas; mobile lista indentada en drawer.
- `floating-pill` — píldora centrada con blur que flota/sombreada; mobile pill reducida o bottom.
- `sticky-condensed` — header sticky que se compacta al scroll (ya hay `.scrolled`).
- `hide-on-scroll` — header se oculta al bajar y vuelve al subir (JS mínimo en layout, gated por data-nav).
- `sidebar-rail` — rail vertical izq de íconos en desktop; mobile bottom tabs.
- `search-first-command` — buscador protagonista casi fullscreen; mobile overlay con autofocus.
- `hamburger-overlay` — sin menú desktop: overlay fullscreen tipográfico; mobile igual.
- `bottom-tabbar` — barra inferior 4-5 tabs (ya existe `.sp-tabbar`); header mínimo.
- `side-drawer-right` — drawer lateral derecho con acordeones + mini-carrito.
- `fullscreen-sheet` — sheet/bottom-sheet casi total como "modal de navegación".
- `dock` — píldora flotante inferior tipo macOS dock con acciones clave.
- `editorial-index` — índice numerado 01-05 con subtexto editorial; mobile índice vertical.
- `ticket-menu` — menú como ticket/ficha: bordes dashed, mono, perforaciones; mobile sheet.
- `breadcrumb-bar` — barra contextual ruta+acciones bajo el navbar (fusión en páginas internas).
- `announcement-rotator` — barra superior que rota mensajes/marquee; mobile una línea.
- `icon-rail-top` — solo íconos verticales izq sin labels; mobile bottom tabs.
- `card-menu-flyout` — dropdowns como cards con imagen+título+sublinks.
- `contextual-sticky` — barra que cambia contenido por página (home/catálogo/PDP).
- `swipe-tabs` — tabs subrayados/swipeables centrados (segmented); mobile scroll+snap.
- `glassmorphism-overlay` — transparente sobre hero → blur sólido al scroll (`.is-scrolled` ya existe).
- `command-palette-nav` — nav mínimo logo+⌘K palette+íconos; palette = sheet fullscreen.
- `statement-bar` — barra tipográfica oversized de una línea (statement), menú en drawer.
- `index-rail` — índice vertical numerado fijo a un costado (distinto de editorial-index horizontal).
- `minimal-floating` — marca mínima centrada + acciones dispersas, mucho aire.

### Panel de cuenta (8 modos CSS sobre `.acc-shell`)
- `account-sidebar` — sidebar izq fijo + contenido (actual).
- `account-rail` — sidebar colapsa a rail de íconos (labels ocultos).
- `account-topbar` — identidad en barra superior + tabs debajo (side oculto).
- `account-tabs-only` — sin side: tabs horizontales primarias en desktop.
- `account-split` — side a la derecha (column-reverse) + contenido izq.
- `account-card` — shell como tarjeta centrada con tabs internas.
- `account-stack` — mhead + tabs + panel apilados full-width (side → fila de chips arriba).
- `account-bento` — stats chips como tiles + tabs compactas (home orientada a acciones).

### Seguimiento (8 modos CSS sobre `.ec-track`)
- `tracking-stepper` — stepper horizontal actual.
- `tracking-timeline` — línea temporal vertical protagonista (timeline card primero).
- `tracking-ticket` — recibo/ticket con perforaciones y código; stepper compacto.
- `tracking-status-hero` — card de estado gigante (ETA/estado) + stepper segmento.
- `tracking-feed` — feed de eventos cronológico primero, stepper abajo.
- `tracking-bento` — grid de cards asimétrico (estado ancho, items lateral).
- `tracking-minimal` — sin cards: secciones con hairlines y stepper línea.
- `tracking-stepcard` — cada paso como card con fecha/estado (stepper→grid de pasos).

## Matriz diseño → arquetipo

Regla: navbar 100% único (26/26). Cuenta: 8 modos × variantes responsive;
seguimiento: 8 modos. Se exige par (cuenta, seguimiento) único por diseño;
la plantilla móvil de cuenta/track se define dentro del CSS de cada diseño.

| diseño        | navbar                  | cuenta              | seguimiento        |
|---------------|-------------------------|---------------------|--------------------|
| portico       | editorial-index         | account-sidebar     | tracking-ticket    |
| esencial      | left-logo-standard      | account-tabs-only   | tracking-stepper   |
| mercado       | mega-menu               | account-stack       | tracking-bento     |
| autoservicio  | swipe-tabs              | account-rail        | tracking-feed      |
| gimnasio      | bottom-tabbar           | account-bento       | tracking-status-hero|
| movimiento    | utility-plus-primary    | account-topbar      | tracking-timeline  |
| sastreria     | ticket-menu             | account-card        | tracking-stepcard  |
| moderntec     | command-palette-nav     | account-sidebar     | tracking-minimal   |
| indumentaria  | card-menu-flyout        | account-split       | tracking-timeline  |
| impacto       | announcement-rotator    | account-tabs-only   | tracking-feed      |
| showroom      | sticky-condensed        | account-stack       | tracking-ticket    |
| ruta          | breadcrumb-bar          | account-card        | tracking-stepper   |
| aurum         | floating-pill           | account-rail        | tracking-status-hero|
| brigada       | side-drawer-right       | account-bento       | tracking-minimal   |
| neon          | dock                    | account-topbar      | tracking-feed      |
| calzado       | hide-on-scroll          | account-split       | tracking-bento     |
| moda          | hamburger-overlay       | account-card        | tracking-timeline  |
| modista       | fullscreen-sheet        | account-tabs-only   | tracking-status-hero|
| topmodern     | search-first-command    | account-stack       | tracking-stepcard  |
| viajero       | sidebar-rail            | account-rail        | tracking-ticket    |
| olivium       | glassmorphism-overlay   | account-bento       | tracking-ticket    |
| atelier-noir  | index-rail              | account-split       | tracking-feed      |
| guardia       | contextual-sticky       | account-topbar      | tracking-bento     |
| expediente    | icon-rail-top           | account-card        | tracking-bento     |
| silicio       | statement-bar           | account-tabs-only   | tracking-timeline  |
| umbral        | minimal-floating        | account-stack       | tracking-status-hero|

Pares (cuenta, seguimiento): 26/26 únicos tras reasignar
expediente→tracking-bento y olivium→tracking-ticket.

## Notas de implementación por agente (FASE 4)

- Solo archivos del propio diseño: `assets/store-<tpl>.css`,
  `assets/store-design-<slug>.css` (+ `-auth`/`-account` variantes),
  `StoreApp/domains/design/sources/<slug>.html` si es patrón.
- PROHIBIDO tocar: `StorePublicLayout.vue`, `StoreAccountView.vue`,
  `StoreTrackingView.vue`, `storeArchetypes.js`, `pattern_bridge.js`,
  `pattern_render.py`, `pattern_document.py`, `seed_data.json`,
  cualquier archivo de otro diseño.
- Selectores: `.store-page[data-design='<slug>']` ya existe — usarlo;
  también `.store-page[data-nav='…']` etc. tras FASE 3.
- Patrón HTML: navbar propio dentro del doc; CSP sin unsafe-inline, JS
  solo nonce, sin fetch/storage — menú móvil con `<details>`/checkbox o
  el JS propio del doc. NO editar `pattern_bridge.js`.
- Reglas `[data-st-font-*]` llevan `!important`: redeclarar
  `typography.*` del estilo o usar selectores más específicos.
- Táctil ≥44px, sin scroll horizontal 320–1440, contraste AA, foco
  visible, `prefers-reduced-motion`, tokens `--st-*`/`--sp-*` de la piel.
