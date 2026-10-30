# Interfaz de plantillas — contrato para los agentes de diseño

> Entregable de la fase fundacional (agente A). Todo agente que agregue o
> modifique un diseño de la web pública lo lee antes de tocar código.
> Spec maestra: `docs/PROMPT_REDISENO_PLANTILLAS.md`.

## 1. Catálogo de diseños

| id | Nombre | Rubro | Nivel (`tier`) | Lo habilita | Acento por defecto |
|---|---|---|---|---|---|
| `raiz` | Raíz | general / retail / servicios | `base` | `has_customization` | `#0F766E` |
| `alimentos` | Alimentos | gastronomía / almacén | `base` | `has_customization` | `#C8321D` |
| `trama` | Trama | indumentaria / moda | `plus` | `has_design_plus` | `#1F3A5F` |
| `indumentaria` | Indumentaria | indumentaria / moda profesional | `plus` | `has_design_plus` | `#1F3A5F` |
| `boutique` | Boutique | moda premium / deco | `plus` | `has_design_plus` | `#6B2D4F` |
| `clasico` | Clásico | comercio y servicios con oficio | `plus` | `has_design_plus` | `#1F4D43` |
| `circuito` | Circuito | tecnología / electrónica | `advanced` | `has_design_advanced` | `#22D3EE` |
| `seguridad` | Seguridad | seguridad / bomberos / industrial | `advanced` | `has_design_advanced` | `#C8200E` |

- **Piel compartida (`data-skin`)**: la hoja de un diseño se resuelve por
  `storeSkinOf(template)` (`STORE_TEMPLATE_SKIN` en `stores.api.js`) y el
  layout la pinta en `.store-page` como `data-skin="<piel>"`. `trama` e
  `indumentaria` comparten piel (`indumentaria` → `store-trama.css` +
  `store-trama-catalog.css`, un solo chunk) y se diferencian por la
  COMPOSICIÓN de su `InicioView`; el resto de los diseños tiene piel propia.
  Los CSS de trama se scopan por `[data-skin='indumentaria']`, **no** por
  `[data-template]`. `indumentaria` además reusa las vistas de catálogo, ficha
  y servicios de trama (`templates/_shared.js`); `clasico` tiene las suyas.

- **Fallback global: `raiz`.** Cualquier id desconocido o fuera del plan se
  resuelve a `raiz`.
- **Retiro**: `STORE_TEMPLATE_RETIRED_MAP` (`frontend/src/api/stores.api.js`) y
  `StoreCustomization.TEMPLATE_RETIRED_MAP` (backend, fuente única) remapean los
  ids viejos por afinidad de rubro. Una tienda vieja nunca pierde su web.
- El catálogo vive en 3 lugares espejo que **deben cambiar juntos**:
  1. `StoreApp/domains/stores/models/models.py` → `TEMPLATE_CHOICES`,
     `TEMPLATE_BASE/PLUS/ADVANCED`, `TEMPLATE_RETIRED_MAP`, defaults.
  2. `frontend/src/api/stores.api.js` → `STORE_TEMPLATES`,
     `STORE_TEMPLATE_FAMILIES`, `STORE_TEMPLATE_SKIN`/`storeSkinOf`,
     `STORE_TEMPLATE_RETIRED_MAP`, `allowedTemplatesFor`,
     `resolveStoreTemplate`.
  3. `frontend/src/templates/index.js` → `TEMPLATE_DEFS`.
- **Familias del selector** (`STORE_TEMPLATE_FAMILIES`): una opción por
  familia (el select usa `templates[0]`). `indumentaria` (Trama) y `moda-pro`
  (Indumentaria) son dos opciones de la misma familia de rubro; `clasico` es
  su propia familia, después de boutique.

## 2. Mapa de archivos de un diseño

```
frontend/src/
├─ templates/<id>/index.js          # Template Definition (registro)
├─ views/store/<id>/
│  ├─ InicioView.vue                # superficie 'landing'
│  ├─ CatalogoView.vue              # superficie 'catalog'
│  ├─ ProductoView.vue              # superficie 'product'
│  └─ ServiciosView.vue             # superficie 'services'
└─ assets/store-<id>.css            # piel completa (raíz [data-skin="<id>"])
```

Un diseño puede **compartir piel** con otro (declara la misma clave en
`STORE_TEMPLATE_SKIN`) y reusar sus vistas de catálogo/ficha/servicios desde
`templates/_shared.js`; solo `InicioView` es obligatoriamente propio porque la
composición es lo que distingue la opción. Hoy: `indumentaria` → piel y vistas
de trama; `clasico` → piel y vistas propias.

Nada más se toca: el resto es compartido (`StorePublicLayout`, bloques de
`components/store/blocks`, `TplProductCard`, `ProductStars`, `ProductReviews`,
`StoreBot`, composables y API).

### 2.1 Template Definition

```js
// frontend/src/templates/<id>/index.js
import { landingViews, catalogViews, productViews, servicesViews, CATALOG_BLOCKS, SERVICES_BLOCKS } from '../_shared.js'

export default {
  usesSectionOrder: false,      // orden canónico propio (la vista lo monta con useLayout)
  fonts: ['manrope', 'bricolage-grotesque'],   // slugs de STORE_FONTS (carga on-demand)
  surfaces: {
    landing:  landingViews.<id>,   // () => import('...')
    catalog:  catalogViews.<id>,
    product:  productViews.<id>,
    services: servicesViews.<id>
  },
  blocks: { landing: [...], catalog: ['note','promo', ...CATALOG_BLOCKS], services: SERVICES_BLOCKS }
}
```

- Para registrar un diseño nuevo: 1 carpeta en `templates/`, 1 carpeta en
  `views/store/`, 1 CSS, y sumar los 4 loaders en `templates/_shared.js` +
  la entrada en `TEMPLATE_DEFS`, `STORE_TEMPLATES` y el backend.
- `blocks` es la whitelist para el Studio de bloques (`LayoutEditor`) **y el
  orden canónico por defecto** de la portada: el render público monta el layout
  efectivo (`layout_config` ∪ default) con `useLayout('landing')`, así la IA
  puede recomponer orden / on-off / variante / props por cliente. `contact`
  queda siempre al final (`resolveLayout`).

### 2.2 Rutas (no cambian)

| superficie | ruta | componente |
|---|---|---|
| landing | `/<slug>` o `/` (subdominio) | `StoreHomeView` → `surfaceComponent(pageTemplate, 'landing')` |
| catalog | `/<slug>/catalogo` | `StoreCatalogView` → `surfaceComponent(..., 'catalog')` |
| servicios | `/<slug>/servicios` | `StoreServicesView` → `surfaceComponent(..., 'services')` |
| producto | `/<slug>/producto/<id>` | `StoreProductView` → `surfaceComponent(..., 'product')` |

`pageTemplate` ya viene resuelto (remapeo + whitelist del plan) en
`StorePublicLayout`.

## 3. Contexto `storePage` (lo que provee `StorePublicLayout`)

```js
const ctx = inject('storePage')
// slug, store (payload público completo), status, custom (StoreCustomization),
// shopName, nameFont, initial, location, hasDesignAdvanced, pageTemplate,
// hasAbout, showGallery, showContact, showCatalog, showServices, siteTemplates,
// ui {search, menuOpen, searchOpen, moreOpen},
// loadPublicCatalog(params) → Promise<payload del catálogo>
```

- **Datos reales siempre.** No hay fetching nuevo: el catálogo sale de
  `useStoreCatalog()` (que usa `loadPublicCatalog`) y los servicios de
  `store.service_items` del payload público.
- **Gating**: no reintroducir reglas. `show_*` manda; sin contenido la sección
  se oculta; las rutas públicas ya devuelven 404 sin acceso.
- El chrome (header, footer, barra móvil, drawer) es **compartido** y se
  re-skinea desde el CSS del diseño con `[data-template="<id>"] .sp-top`,
  `.sp-foot`, `.sp-tabbar`, etc. No hay `chrome/` por diseño: cualquier
  cambio estructural en la barra es un cambio compartido y debe reportarse.

## 4. Primitivas compartidas (no duplicar)

| Necesidad | Pieza |
|---|---|
| Tarjeta de producto | `components/store/TplProductCard.vue` (props `p, cat, brand, stars, starsIcon, quick, goLabel`; emit `open`) + `assets/store-tpl-card.css` |
| Estrellas de valoración | `components/ProductStars.vue` (`avg, count, size, showValue, icon`) |
| Reseñas (lista + form con captcha) | `components/ProductReviews.vue` (`slug, productId, canRate, canComment, avg, count, icon`) |
| Bloques del inicio | `components/store/blocks/Blk*.vue` (reciben `:block="{ id, variant, props }"` y se auto-ocultan) |
| Secciones del inicio | `<BlkHero>`, `BlkAnnouncements`, `BlkHighlights`, `BlkCategories`, `BlkFeatured`, `BlkAbout`, `BlkStats`, `BlkServices`, `BlkBenefits`, `BlkOffers`, `BlkCountdown`, `BlkBrands`, `BlkGallery`, `BlkTestimonials`, `BlkFaq`, `BlkCta`, `BlkContact` |
| Botones / iconos | `AppIcon.vue` (catálogo cerrado de iconos), clases `.sp-btn` / `.sp-icon-btn` como base |
| Catálogo (estado) | `composables/useStoreCatalog.js` — expone `catalog`, `catalogStatus`, filtros (`activeCategories`, `activeBrands`, `featureFilters`, `onlyOffer`, `onlyNew`, `priceMin/Max`, `sort`), `facets`, `activeTags`, `visibleProducts`, `showMore`, `openProduct`, helpers de nombres |
| Catálogo (API helpers) | `api/catalog.api.js` → `effectivePrice`, `productOffer`, `offerPct`, `isNewProduct`, `productDiscount`, `offerEndsLabel`; precios con `formatARS` de `api/billing.api.js` |
| Tipografías | `ensureStoreFont` / `STORE_FONTS` (`api/stores.api.js`); declarar las del diseño en `fonts` de la Template Definition |
| Reveal on scroll | directiva `vReveal` (`directives/reveal.js`) |

## 5. Variables CSS y raíz de la piel

- La raíz de todo el CSS del diseño es **`[data-skin="<piel>"]`** (pintada por
  `StorePublicLayout` en `.store-page` desde `storeSkinOf(pageTemplate)`); el
  `data-template="<id>"` sigue disponible para diferencias puntuales entre dos
  diseños que comparten piel. Un diseño nuevo declara su piel en
  `STORE_TEMPLATE_SKIN` y, si reusa una existente, no agrega hoja.
- Cada diseño declara su propio prefijo de tokens: `--rz-*` (Raíz), `--tr-*`
  (Trama e Indumentaria, piel compartida), `--ci-*` (Circuito), `--cl-*`
  (Clásico).
- El layout base expone variables `--sp-*` (`--sp-bg`, `--sp-card`,
  `--sp-surface`, `--sp-ink`, `--sp-ink-2`, `--sp-muted`, `--sp-line`,
  `--sp-radius`, `--sp-shadow-sm/md`, `--sp-on-band*`, `--sp-band-*`,
  `--sp-top-h`). Un diseño puede reescribirlas en su raíz para que los bloques
  compartidos hereden la piel sin duplicar CSS (así lo hace Raíz).
- Acento: siempre `var(--store-accent)` (lo emite `storeThemeVars`) o el
  default del diseño; **nunca** un hex crudo sobre fondo sin chequeo AA.
- El CSS de cada diseño se carga **on-demand** (`TEMPLATE_CSS` en
  `StorePublicLayout`, indexado por diseño): un diseño no viaja en el bundle de
  otro. `indumentaria` importa `store-trama.css` (mismo chunk que trama, el
  bundler lo cachea) y `clasico` importa `store-clasico.css`.
- `prefers-reduced-motion` y `:focus-visible` son obligatorios.

## 6. Qué NO puede tocar un agente de diseño

- Backend (`StoreApp/**`) — el catálogo y la migración son de la fundación.
- `frontend/src/api/stores.api.js`, `frontend/src/templates/index.js`,
  `frontend/src/templates/_shared.js`, salvo que el contrato lo pida.
- `StorePublicLayout.vue`, `StoreHomeView.vue`, `StoreCatalogView.vue`,
  `StoreServicesView.vue`, `StoreProductView.vue`, `components/store/**`,
  `components/Product*.vue`, `package.json`, `vite.config.js`.
- Otras carpetas `views/store/<otro-id>/` y `assets/store-<otro-id>.css`.
- El contenido/datos: no se agregan campos ni endpoints.

## 7. Data hook del diseño Raíz (referencia)

`views/store/raiz/InicioView.vue` monta los bloques en el orden canónico de la
referencia (cinta, hero split, garantías, categorías, recientes, nosotros,
cifras, servicios, garantías oscuras, cuenta regresiva, ofertas, marcas,
galería, testimonios, FAQ, CTA, contacto). `CatalogoView.vue` usa
`useStoreCatalog` + `TplProductCard`; `ProductoView.vue` es la ficha
marketplace (galería, panel de compra con WhatsApp, specs, relacionados,
reseñas); `ServiciosView.vue` es el embudo de presupuesto por WhatsApp
(selección, total orientativo, pasos, garantías, trabajos, zona/horarios,
formulario y FAQ).

## 8. Verificación mínima antes de commitear

```bash
cd frontend && pnpm build        # sin errores nuevos
venv/Scripts/python.exe manage.py test --pattern "tests_ai_design*.py"
grep -rn "classic\|ai_lumen\|cobre" frontend/src --include=*.js --include=*.vue
```
