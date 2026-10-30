# Superficie de plantillas del frontend + Studio — recon para una familia nueva

> Recon de solo lectura (task-3). Complementa `docs/PLANTILLAS_INTERFAZ.md` (contrato
> para agentes de diseño) con el mapa de archivos, el coste de agregar una familia
> espejo de un landing de referencia y el de editarla visualmente.
> Convención: `archivo:línea`. Todas las rutas son relativas a `frontend/src/` salvo
> las de backend.

---

## 1. Router, `pageTemplate` y `allowed_templates_of`

**Rutas** (`router/index.js`)
- `storeChildren` (`:33-62`): `store-public` (`/`), `store-catalog` (`/catalogo`),
  `store-services` (`/servicios`), `store-product` (`/producto/:productId(\\d+)`).
- Sin subdominio: `/:slug([a-z0-9-]+)` con `StorePublicLayout` como padre (`:194-198`)
  y alias legacy `/tienda/:slug/*` que redirigen a los names (`:178-193`).
- Con subdominio (`storeHostSlug`): la web se monta en `/` (`:175-176`) y **cualquier
  ruta de plataforma** rebota a `env.appUrl + path` en el guard (`:236-239`).
- `storeHostSlug` sale de `location.hostname` (`config/env.js:30`), excluye
  `www/app/api/admin/panel/mail`. El layout toma el slug del host si no hay param
  (`views/StorePublicLayout.vue:41`). Los links internos se arman con
  `storeHostSlug ? '/x' : '/<slug>/x'` (p.ej. `views/store/circuito/InicioView.vue:26`).
- Catch-all (`:200`): `storeHostSlug ? '/' : '/login'`.

**Resolución de la plantilla** (`views/StorePublicLayout.vue`)
- `pageTemplate = resolveStoreTemplate(custom.template, store.allowed_templates)`
  (`:159-164`); en modo Studio resuelve contra el catálogo completo (`:160-162`).
- `allowed_templates` viene en el payload público y es la whitelist del plan
  (`api/stores.api.js:17-20`). Fallback global `raiz`.
- `DESIGN_SKIN_FREE = ['raiz','trama','circuito']` (`:123-124`): estas 3 ignoran
  `site_theme`/`layout_config` en el render; `publishedThemeVars` queda `{}` (`:125-128`).
- CSS del diseño on-demand por mapa `TEMPLATE_CSS` (`:172-177`).
- `provide('storePage', …)` (`:453-457`): `slug, store, status, custom, shopName,
  nameFont, initial, location, hasDesignAdvanced, pageTemplate, hasAbout, showGallery,
  showContact, showCatalog, showServices, siteTemplates, ui, loadPublicCatalog`.
- `surfaceComponent(pageTemplate, 'landing'|'catalog'|'services'|'product')` en
  `StoreHomeView.vue:12`, `StoreCatalogView.vue:21`, `StoreServicesView.vue:9`,
  `StoreProductView.vue:10`.

**Catálogo de plantillas (3 espejos que cambian juntos)**
| Capa | Archivo |
|---|---|
| Backend (fuente) | `StoreApp/domains/stores/models/models.py:129-157` (`TEMPLATE_BASE/PLUS/ADVANCED`, `TEMPLATE_CHOICES`, `TEMPLATE_RETIRED_MAP`, default `raiz`) |
| Backend gating | `stores/services/services.py:77-94` (`allowed_templates_of`); `views/viewset.py:806, 938, 1028` |
| Frontend catálogo | `api/stores.api.js:692-696` (`STORE_TEMPLATES`), `:701-706` (familias), `:711-720` (retired map), `:735-751` (`allowedTemplatesFor`/`resolveStoreTemplate`) |
| Frontend registro | `templates/index.js:30` (`TEMPLATE_DEFS`), `templates/_shared.js:13-35` (loaders), `views/StorePublicLayout.vue:172-177` (`TEMPLATE_CSS`) |

---

## 2. Anatomía de una plantilla (referencia: `raiz`)

**Archivos de un `<id>/`**
- `templates/<id>/index.js` → Template Definition (`templates/raiz/index.js:5-19`):
  `usesSectionOrder`, `fonts` (slugs de `STORE_FONTS`, carga on-demand),
  `surfaces {landing,catalog,product,services}`, `blocks {landing,catalog,services}`
  (whitelist del Studio + layout default, **no** el orden real del render).
- `views/store/<id>/`: `InicioView.vue`, `CatalogoView.vue`, `ProductoView.vue`,
  `ServiciosView.vue` (+ piezas propias: `TrHero/TrMarquee/TrCategories/TrFeatured/
  TrLookbook` en trama; `CiHero/CiGuarantees/CiServicesBand` en circuito).
- `assets/store-<id>.css` (piel completa, raíz `[data-template="<id>"]`).
- Reuso: `trama/ProductoView.vue:7-11` y `trama/ServiciosView.vue:7-11` son wrappers
  de `raiz` que solo agregan una clase de scope (`.tr-product`, `.tr-services`); la
  piel llega por CSS. La ficha de circuito sí es propia (13 KB).

**Tamaño de las piezas** (coste real de una familia): `raiz` 4 archivos + 395 líneas
de CSS; `trama` 9 archivos + 1038 líneas; `circuito` 7 archivos + 1666 líneas;
`raiz/ServiciosView.vue` 43 KB (embudo de presupuesto propio);
`CatalogoView` ≈ 9,7 KB por diseño (tres copias casi iguales).

**Qué recibe cada sección**
- Las secciones son componentes de `components/store/blocks/Blk*.vue`; reciben
  `:block="{ id, variant, props }"` desde la vista
  (p.ej. `views/store/raiz/InicioView.vue:28-44`).
- Datos: `inject('storePage')` + `useFeaturedCatalog()` / `useStoreCatalog()`; **no
  hay fetching nuevo**.
- `BlockRenderer.vue:29-58` existe para montar el layout efectivo desde
  `layout_config`, pero **ninguna vista pública lo usa hoy** (solo lo mencionan
  comentarios): es infraestructura huérfana, lista para reutilizar.

**Secciones que monta cada inicio (orden canónico = la vista, no `layout_config`)**
- `raiz`: 17 secciones (`raiz/InicioView.vue:26-45`): announcements, hero(split),
  highlights, categories(row), featured(grid, “Productos recientes”), about, stats,
  services, benefits, countdown(card), offers(grid), brands, gallery,
  testimonials, faq, cta, contact.
- `trama`: 12 (`trama/InicioView.vue:22-35`): announcements, TrHero, TrMarquee,
  TrCategories, TrFeatured, TrLookbook, benefits, gallery(“Looks del mes”), faq,
  cta, contact.
- `circuito`: 12 (`circuito/InicioView.vue:35-68`): announcements, CiHero,
  CiGuarantees, categorías en sección propia (solo si hay categorías con productos,
  `:29-32,44-53`), featured, CiServicesBand, countdown(band), brands,
  testimonials, faq, contact.

**Activación / ocultamiento de cada bloque**
- Doble filtro: el bloque se auto-oculta sin datos (`v-if` propio) y además respeta
  el flag del dueño: p.ej. `BlkHighlights.vue:51` (`show_highlights !== false`),
  `BlkOffers.vue:23` (`show_offers`). Cada bloque consulta `useLayout('landing')`
  (`composables/useLayout.js:16-29`) para saber si está habilitado en el layout.
- Flags `show_*` del modelo (`models/models.py:173-190` y bloques de marketing):
  `show_about`, `show_contact`, `show_gallery`, `show_highlights`, `show_offers`,
  `show_brands`, `show_countdown`, `show_services`, `show_stats`,
  `show_testimonials`, `show_faq`, `show_cta`, `show_announcements`, `show_video`,
  `show_location`, `show_catalog`, `show_reviews`, `show_comments`.
- Límites de plan: el viewset **descarta del PATCH** campos fuera de nivel
  (`views/viewset.py:56-62` `DESIGN_ADVANCED_FIELDS/LOCATION_FIELDS/REVIEW_FIELDS`;
  `:791-795`; template vía `allowed_templates_of`, `:806`).

**Referencia de landing pedida vs. piezas existentes** — todas ya existen:
categorías `BlkCategories` (row/rail) · recientes `BlkFeatured` (grid, `props.title`) ·
sobre nosotros `BlkAbout` · servicios `BlkServices` · garantías `BlkBenefits` ·
oferta+contador `BlkCountdown` + `BlkOffers` · marcas `BlkBrands` · galería
`BlkGallery` · testimonios `BlkTestimonials` · FAQ `BlkFaq` · CTA `BlkCta` ·
contacto `BlkContact` · footer/chrome = `StorePublicLayout` compartido
(re-skineado por CSS, `docs/PLANTILLAS_INTERFAZ.md` §3).
Registro de componentes: `components/store/blocks/index.js:11-41`.

---

## 3. CSS

- **Compartido**: `assets/store-page.css` (4.195 líneas, ≈270 KB) = chrome (barra
  `:50`, footer `:335`, dark `:351`, responsive `:364`), identidad `:94`, botones
  `:105`, hero `:126` (`.sp-hero-band`), catálogo `:165-280`, sobre nosotros `:281`,
  contacto `:307,562,584`, movimiento `:419`, galería `:729`, y **bloques de
  marketing de portada desde `:1379`**. Contiene además bloques de plantillas
  retiradas (`:1023-1120`, “Perspectiva/Publicidad”): CSS muerto a no tocar.
- **Por familia**: `assets/store-<id>.css`, raíz `.store-page[data-template='<id>']`.
  `store-raiz.css:8-50` declara tokens `--rz-*` y **reescribe `--sp-*`**
  (`:35-47`) para que los bloques compartidos hereden la piel sin duplicar CSS
  (trama/circuito usan `--tr-*` / `--ci-*` y el mismo patrón).
- **Acento**: `--store-accent` / `--store-accent-ink` emitidos por
  `storeThemeVars()` (`api/stores.api.js:880`; catálogo cerrado `:666`
  `STORE_ACCENTS`). Regla: nunca hex crudo sin AA (`docs/PLANTILLAS_INTERFAZ.md` §5).
- **Tipografías on-demand**: `ensureStoreFont` (`api/stores.api.js:839`),
  `storeFontFamily` (`:806`); la plantilla declara sus `fonts` y el layout las carga
  (`StorePublicLayout.vue:558` con `templateFonts`, `templates/index.js:51-53`).
- **Animación**: directiva `vReveal` (`directives/reveal.js:22-32`, clase `.sp-rv`,
  observer tras doble `requestAnimationFrame`; `--rv-d` para delay). Capa de
  movimiento al final de `store-page.css` (`:419-560`).
- **Tarjetas**: geometría uniforme en `assets/store-tpl-card.css` (contrato duro,
  `:1-10`) importado por el layout (`StorePublicLayout.vue:26`); la estética por
  tokens `--tpc-*` desde la piel.
- **Catálogo**: `store-catalog.css` (65 KB) + `store-catalog-responsive.css` +
  `store-catalog-polish.css`, importados en `StoreCatalogView.vue:11-13`.

---

## 4. Catálogo público, filtros y facetas (reutilizable tal cual)

- `StoreCatalogView.vue:19-33`: envuelve la superficie en `.cv-outer` con
  `data-cv-grid` / `data-cv-filters` (variantes de `useLayout('catalog')`), monta la
  tira `catalog_note` (`.cv-note`) y el `<component>` del diseño.
- `views/store/raiz/CatalogoView.vue`: `useStoreCatalog({pageSize:12})` (`:18`),
  panel de filtros (`:77-133`: categorías, marcas, oferta/nuevo, precio, facetas
  dinámicas `facet.name/values`, `activeTags`, `clearFilters`), `TplProductCard`
  (`:166`), tira de promos inline (`:65-72`) y promo por tarjeta (`:172`).
  Las otras dos plantillas **duplican** ese bloque de promos
  (`trama/CatalogoView.vue:63-68`, `circuito/CatalogoView.vue:69-74`): no hay
  componente compartido, sólo CSS `.cv-promo*` (`store-catalog.css:35-43`).
- Estado/derivados compartidos: `composables/useStoreCatalog.js` (filtros, `facets`,
  `sort`, `visibleProducts`, `showMore`; `:63-67` expone `catalog, facets, …`).
- Piezas reutilizables para el modelo nuevo: `TplProductCard.vue`, `ProductStars.vue`
  (`.ico` por plantilla en `public/ratings/`), `ProductReviews.vue`,
  `SwipeGallery.vue`, `StickyBuyBar.vue`, `TrustBar.vue`, `OfferSeal.vue`,
  `ScheduleCard.vue`, `StepRail.vue`, `SpecStrip.vue`, `BottomSheet.vue`,
  `MarqueeBand.vue`, `BentoGrid.vue`, `AiGlyph.vue`, `StTag.vue`.
- Helpers de precio/oferta/nuevo: `api/catalog.api.js` (`effectivePrice`,
  `productOffer`, `offerPct`, `isNewProduct`, `productDiscount`, `offerEndsLabel`);
  precios con `formatARS` (`api/billing.api.js`).

---

## 5. Preview del dashboard y Studio

Hoy hay **tres** superficies de preview, con distinto grado de espejo:

1. **Mini overview** `.design-preview` (clases `dp-*`), inline en
   `views/DashboardView.vue:3261-3278`: nav + hero + CTA + catálogo/mapa. Es
   genérico, no cambia por plantilla.
2. **`components/design/DesignPreview.vue`** (bloque “Vista previa” del diseño):
   recibe `template` (`:8`) y emite `data-store-template` (`:131`), pero el markup
   es también nav+hero+carrusel (`:132-166`): **no espeja la composición** de las 3
   plantillas; el `data-*` sólo permite re-skinear el mockup por CSS.
   Se usa en Dashboard (`:4421`), `AiDevicePreview.vue:269`, `AiLiveThumb.vue:156`.
3. **Studio real**: `previewUrl = /<slug>?studio=1` (`DashboardView.vue:1723`) en
   iframe (`StudioShell` → `StudioCanvas`, `installPreviewBridge` en
   `components/studio/previewBridge.js:397`). El borrador viaja por `postMessage`:
   `StorePublicLayout.vue:45-57` aplica `layoutOverride` y `studioTheme`;
   `StudioShell.vue:251-277` emite `{layout_config, template}`; `contract.js:718-742`
   define `STUDIO_MSG`/`studioUpdate`/`studioFocus`/`studioReady`. El layout real se
   sigue pintando con la vista fija → **el iframe muestra la plantilla verdadera**
   (no hay espejo que mantener) salvo que la plantilla nueva no lea el override.

**Dónde se elige el diseño y dónde se editan textos/secciones**
- Selector de diseño: `components/design/DesignLookTab.vue:298-309`
  (`pickTemplate`, gate `allowedTemplates`) con miniaturas `.tpl-thumb`
  `:data-tpl="<id>"` (`:725-738`), montado dentro del Studio
  (`studio/panels/EstilosPanel.vue:25`). Pestañas del diseño:
  `DashboardView.vue:1276-1281` (`Mis datos`, `Studio`, `Fotos`, `Qué mostrar`).
- Secciones: pestaña “Qué mostrar” (`DashboardView.vue:4330-4400`): páginas
  (`site_templates`) + check-list `show_highlights/about/gallery/contact/offers/
  brands/countdown/location`; se guardan con `saveDesign` (`:1776-1848`, payload en
  `:1785-1838`).
- Textos y bloques de marketing: sección **“Mi empresa”** con una tarjeta por bloque
  (`mkNav` `:1406-1418`, markup `:4495-4950`) y un `save*` por tarjeta:
  `saveCompany` `:1424`, `saveServices` `:1440`, `saveStats` `:1456`,
  `saveTestimonials` `:1470`, `saveFaqs` `:1486`, `saveBenefits` `:1502`,
  `saveTimeline` `:1516`, `saveTeam` `:1530`, `saveHours` `:1544`, `saveCta` `:1558`,
  `saveAnnouncements` `:1574`, `saveVideo` `:1588` (PATCH parcial cada uno).
- Catálogo (banners, aviso, página): tarjeta “Tu página de catálogo” en Mis catálogos
  (`siteTemplateKeys` `:1865-1882`, `toggleSiteTemplate`).
- **Studio (fase de datos)**: `studio/contract.js` (32 KB, sin imports) define
  `STUDIO_SURFACES` `:35`, `SITE_THEME_DEFAULTS` `:83`, `resolveSiteTheme` `:191`,
  contraste `:277-324`, `themeToCssVars` `:460`; paneles `studio/panels/*`
  (`Colors`, `Typography`, `Containers`, `Background`, `Motion`, `Mobile`, `Health`,
  `Publish`). Lo que produce se guarda en `site_theme`/`layout_config`(_draft) y
  **no pinta las 3 plantillas** (`DESIGN_SKIN_FREE`).
- Qué falta para editar visualmente el modelo nuevo: (a) que la plantilla lea el
  layout/theme del borrador (o usar `BlockRenderer`), (b) un panel con
  secciones/textos del modelo, (c) un preview que espeje esa composición, (d) el
  `save*` + saneador backend por lista nueva si se agregan campos.

---

## 6. CHANGE-MAP

### (a) Nueva plantilla + espejo de preview + selector
Crear:
- `frontend/src/views/store/<id>/{InicioView,CatalogoView,ProductoView,ServiciosView}.vue`
  (los 2 últimos pueden ser wrappers de `raiz`, como `trama`).
- `frontend/src/templates/<id>/index.js` (copiar `templates/raiz/index.js`).
- `frontend/src/assets/store-<id>.css` (raíz `[data-template='<id>']`, tokens
  `--<xx>-*` + override de `--sp-*`).

Tocar:
- `templates/_shared.js:13-35` (4 loaders) · `templates/index.js:26-30`
  (import + `TEMPLATE_DEFS`) · `views/StorePublicLayout.vue:172-177` (`TEMPLATE_CSS`).
- `api/stores.api.js:692-706` (`STORE_TEMPLATES` + familia) y `:711-720` si se
  retira algún id.
- Backend `models/models.py:129-157` (`TEMPLATE_CHOICES`, `TEMPLATE_*`, default) +
  **migración** (choices) y `allowed_templates_of` si el tier es nuevo.
- Selector: `DesignLookTab.vue:725-738` (miniatura/`data-tpl` + CSS del thumb) y
  `DesignPreview.vue` si se quiere espejo real de la composición.
- Tests: `StoreApp/domains/stores/tests.py:404-434` (catálogo/premium/retired) y
  `tests_ai_design_contract.py:401` + suite `tests_ai_design*` (el motor reparte
  plantillas por estilo/plan: una familia nueva entra en la matriz).
- Verificación: `cd frontend && pnpm build` (chunk async por plantilla) +
  `venv/Scripts/python.exe manage.py test`.

Coste estimado: 1 vista de inicio (≈50-120 líneas, composición de bloques
existentes) + 1 CSS (≈400-1.500 líneas, comparable a raíz/trama/circuito) + 2
wrappers + 1 registro + 1 migración. **Sin backend de datos**: todas las secciones
del modelo de referencia ya existen.

### (b) Edición visual de sus secciones
Camino barato (recomendado): conservar composición fija y reutilizar
`show_*` + las tarjetas de “Mi empresa” (ya hay editor por bloque) ⇒ sólo se agrega
la entrada en `mkNav` (`DashboardView.vue:1406-1418`) y, si hace falta un texto
nuevo, campo+serializer+migración.
Camino caro: hacer que la plantilla nueva (o las 3) lean `layout_config` con
`BlockRenderer.vue`/`useLayout` ⇒ habilita orden/variantes/`props.title` por bloque
(ya validado por `layout_blocks.py` y el Studio), pero cambia el render de las
plantillas actuales y exige espejo 1:1 entre `templates/blocks.js` (frontend) y
`StoreApp/domains/stores/layout_blocks.py:83-116` (backend) para cualquier id
nuevo. Además: preview `.dp-*` por plantilla, thumbnail del selector y,
si se quieren textos por sección, campos nuevos + saneadores
(`serializers/serializers.py:319-334`, `site_theme.py:420`).

### (c) Esfuerzo y riesgos
- **Tres espejos + 2 registros**: `models.py`, `stores.api.js`, `templates/index.js`,
  `_shared.js`, `TEMPLATE_CSS`. Olvidar uno deja la web en `raiz` en silencio
  (`resolveStoreTemplate`).
- **`template` es `CharField(max_length=12)`** (`models.py:191,368`): un id más largo
  exige migración de columna.
- **Catálogos cerrados**: `layout_blocks.py` (backend) y `templates/blocks.js`
  (frontend) deben coincidir; `store-page.css` tiene CSS muerto de plantillas
  retiradas (`:1023-1120`).
- **`DESIGN_SKIN_FREE`**: mientras el id nuevo esté en esa lista, el Studio
  (`site_theme`/`layout_config`) no lo pinta; si se lo saca, hereda pieles viejas y
  puede romper AA (`tests_ai_design_contract` verifica contraste del tema emitido).
- **Geometría de tarjeta**: `store-tpl-card.css` fija el tamaño de
  `TplProductCard` en todas las plantillas — la piel nueva no puede tocar
  `--tpc-*` de geometría.
- **Duplicación en catálogo**: las 3 `CatalogoView` copian panel de filtros y tira de
  promos (9,7 KB c/u). Una familia nueva multiplica esa copia salvo que se extraiga
  un componente compartido.
- **Preview**: el mockup `.design-preview`/`dp-*` es genérico; para que “se vea como
  la referencia” hay que escribirlo (2 lugares: `DashboardView.vue:3261` y
  `DesignPreview.vue:132-166`) o apoyarse sólo en el iframe `?studio=1`.
- **Build**: `pnpm build` obligatorio; las pieles entran por `import()` dinámico,
  así que una hoja nueva no engorda el bundle inicial — pero un import estático por
  error sí.
- **Tests del motor IA**: agregar/quitar plantillas mueve la matriz de
  `_style_candidates`/cobertura de estilos; correr `tests_ai_design*` completo.

### Bloqueantes / decisiones previas
1. **Tier y plan** de la familia nueva (`TEMPLATE_BASE/PLUS/ADVANCED`) y si reemplaza
   o convive con las 3 (afecta `allowed_templates_of`, selector y tests).
2. **Nombre corto ≤12 caracteres** para `template` (o migración de columna).
3. **Alcance de edición**: composición fija + `show_*` (barato) vs. layout dinámico
   real (toca las 3 plantillas y el contrato backend↔frontend de bloques).
4. **Espejo de preview**: ¿basta el iframe del Studio o se exige mockup `.dp-*`
   fiel por plantilla?
