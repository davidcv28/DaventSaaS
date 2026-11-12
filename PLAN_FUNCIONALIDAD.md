# Plan — Funcionalidad del sistema de tiendas (orquestación por agentes)

Pedido del usuario: dejar funcional el sistema de webs de tiendas en cada diseño,
con un grupo de subagentes. Superficies: navbar, autenticación, panel de
comprador, tarjetas de producto del catálogo, filtros de eventos, seguimiento
de pedido y datos de prueba (descuentos) en la tienda `david28`.

Repo: Django+DRF en la raíz, Vue 3 en `frontend/`. 26 hojas de diseño
(`frontend/src/assets/store-design-<slug>.css`), 8 motores de plantilla
(`frontend/src/views/store/<tpl>/` + `store-<tpl>.css`), 23 documentos de
patrón (`StoreApp/domains/design/sources/*.html` + `seed_data.json`).

## 0. Definición de "funcional" (medible, no opinable)

| Superficie | Criterio verificable |
|---|---|
| Navbar | En 360/768/1024/1440 px ningún control del header se monta ni colisiona; máximo de acciones visibles por breakpoint definido en §4.i; burger/drawer/tab bar abren y cierran; cero scroll horizontal |
| Auth | `/ingresar` y el modal se ven minimalistas y profesionales en los 26 diseños: un solo CTA primario, campos con label/error/foco visible, contraste AA, estados loading/error/éxito completos |
| Cuenta | `/cuenta` se entiende sin manual: secciones claras, vacíos con CTA, cada pedido enlaza a su seguimiento |
| Tarjeta | Cero botones dentro de la tarjeta (la tarjeta entera es el link); muestra título, etiquetas, precio tachado + oferta + etiqueta de descuento especial en `position:absolute`, descripción mínima y stock; placeholder con icono |
| Catálogo | Filtro "Eventos" visible SOLO si hay descuentos/campañas vigentes (`event_count > 0`); `?event=1` filtra bien y viaja en la URL |
| Seguimiento | Stepper correcto + mini-explicación para el comprador (qué es el link, qué significa cada estado, qué hacer si no aparece el pedido) |
| Datos | La tienda `david28` tiene ≥4 `Discount` vigentes de alcances distintos + ofertas manuales y stocks variados para probar todos los estados de tarjeta |

## 1. Mapa de olas y propiedad de archivos

Nadie escribe en el archivo de otro. Un archivo compartido = un solo dueño.
Los cambios globales que un track necesite pero no pueda hacer se reportan
con snippet exacto y los aplica `track-x` (integrador) una sola vez.

| Track | Ola | Qué | Archivos permitidos |
|---|---|---|---|
| `track-i` | F1 | Navbar compartido | `frontend/src/views/StorePublicLayout.vue`, selectores de nav en `frontend/src/assets/store-page.css` y `store-style-menus.css` |
| `track-j` | F1 | Tarjeta de producto | `frontend/src/components/store/TplProductCard.vue`, `frontend/src/assets/store-tpl-card.css`, `OfferSeal.vue`, `StTag.vue` |
| `track-k` | F1 | Auth minimalista | `frontend/src/views/StoreAuthView.vue`, `frontend/src/components/ecommerce/StoreAuthModal.vue`, `StoreAuthForm.vue` |
| `track-l` | F1 | Cuenta + seguimiento | `frontend/src/views/StoreAccountView.vue`, `frontend/src/components/ecommerce/account/*.vue`, `frontend/src/views/StoreTrackingView.vue` |
| `track-m` | F2 | Catálogo + filtro de eventos | `StoreApp/domains/stores/views/viewset.py` (solo la vista catalog), `frontend/src/api/stores.api.js`, `frontend/src/api/catalog.api.js`, `frontend/src/composables/useStoreCatalog.js`, `catalogFiltersUi.js`, `frontend/src/views/StoreCatalogView.vue`, `frontend/src/views/store/*/CatalogoView.vue`, `frontend/src/assets/store-catalog*.css`, `store-raiz-catalog.css`, bloques `components/store/blocks/*` SOLO para quitar props de tarjeta |
| `track-n` | F2 | Seed de descuentos demo | `StoreApp/domains/catalog/management/commands/seed_demo_discounts.py` (nuevo), ejecución de `manage.py` contra la DB local |
| `track-ds1` | F3 | Diseños: portico, esencial, mercado, gimnasio, moderntec | `store-design-{portico,esencial,mercado,gimnasio,moderntec}*.css`, `store-{mercado,gimnasio,moderntec}*.css`, `StoreApp/domains/design/sources/{portico,esencial,mercado,moderntec}.html` |
| `track-ds2` | F3 | Diseños: ruta, aurum, brigada, indumentaria, impacto | `store-design-{ruta,aurum,brigada,indumentaria,impacto}*.css`, `store-indumentaria.css`, `store-impacto*.css`, `sources/{ruta,aurum,brigada,indumentaria}.html` (impacto no tiene source) |
| `track-ds3` | F3 | Diseños: calzado, moda, modista, topmodern, viajero | `store-design-{calzado,moda,modista,topmodern,viajero}*.css`, `store-design-calzado-auth.css`, `sources/{calzado,moda,modista,topmodern,viajero}.html` |
| `track-ds4` | F3 | Diseños: olivium, atelier-noir, guardia, expediente, silicio | `store-design-{olivium,atelier-noir,guardia,expediente,silicio}*.css`, `sources/{olivium,atelier-noir,guardia,expediente,silicio}.html` |
| `track-ds5` | F3 | Diseños: neon, showroom, sastreria, autoservicio, movimiento, umbral | `store-design-{neon,showroom,sastreria,autoservicio,movimiento,umbral}*.css`, `store-sastreria.css`, `store-movimiento.css`, `sources/{neon,showroom,sastreria,autoservicio,umbral}.html` (movimiento no tiene source) |
| `track-w` | F4 | Inspector visual (read-only) | solo escribe `docs/qa-funcionalidad.md` y screenshots de QA |
| `track-x` | F4 | Integración y cierre | cualquiera, con justificación: `store-page.css`, `store-tpl-card.css`, `store-raiz*.css`, `store-<tpl>.css` sin dueño ds, `views/store/raiz/**`, `views/store/<tpl>/{Inicio,Producto,Servicios}View.vue`, `pattern_bridge.js`/`pattern.js`, `seed_data.json`, `package.json` |

Globales para TODOS: `StorePublicLayout.vue` ya es de `track-i` — nadie más
lo toca (el CSS on-demand de `store-design-*` y `-auth/-account` ya existe;
no hace falta tocar el loader salvo caso justificado → reportar).
`seed_data.json` NO lo toca ningún ds: cada ds reporta los cambios de su
`source/*.html` y `track-x` sincroniza (comando `import_design_pattern` o
edición única del seed).

## 2. Reglas globales (van en todos los prompts)

Heredadas de `PLAN_WEB_PROFESIONAL.md` §2, más las de este plan:

1. **Ningún subagente hace `git`** (ni add/commit/push/checkout/stash).
   El orquestador commitea + pushea a `main` al volver cada track
   (mensaje conventional en inglés, co-autor Devin).
2. **MWG primero**: todo track de front invoca la skill
   `modern-web-guidance` ANTES de tocar HTML/CSS/JS (regla global, prioridad
   máxima sobre cualquier otra skill de UI).
3. **Responsive siempre**: cada track verifica 360 / 768 / 1024 / 1440 px
   antes de cerrar y reporta qué breakpoints tocó. Nada de layouts que
   solo funcionen en desktop.
4. **Contrato de tarjeta**: la tarjeta no contiene elementos interactivos
   propios (nada de `<button>`, `<a>` ni `role="button"` dentro). El
   `<article>/<component>` raíz sigue siendo el único link
   (`role="link"`, Enter/Espacio). Las props `addHref/addLabel/go/goLabel`
   quedan deprecadas: `track-j` las mantiene declaradas sin uso;
   `track-m` borra declaraciones y call sites.
5. **Especificidad CSS**: las hojas de diseño se scopean con
   `.store-page[data-design='<slug>']` (o el scope que ya usen). Prohibido
   `!important` nuevo sin justificación en el reporte. Tokens existentes:
   `--sp-*` (página), `--tpc-*` (tarjeta), `--ec-*`/`acc-*`/`ec-track-*`
   (comercio), `--ds-*` (patrones).
6. **Patrones**: markup de diseño jamás `allow-same-origin`,
   `unsafe-inline` en CSP, ni `fetch` nuevo dentro del documento (todo por
   el puente `davent:ds-api`).
7. **Imágenes**: todo upload pasa por `normalize_image` (WebP). El seed de
   descuentos no sube imágenes.
8. **Economía de tokens**: `grep`/`code_search` primero, `read` con
   `offset`/`limit`, sin volcados, sin subagentes propios.
9. Cada track cierra con: `git status --porcelain`, `git diff --stat`,
   verificación corrida con salida real truncada y riesgos/dependencias
   fuera de scope con snippet exacto.

## 3. Prompt maestro (orquestador)

```
Sos el orquestador del plan "funcionalidad del sistema de tiendas" de SaaS
DAVENT (Django+DRF raíz, Vue 3 en frontend/). El plan completo está en
PLAN_FUNCIONALIDAD.md: leelo una vez y no lo releas.

Secuencia OBLIGATORIA de olas (cada ola depende de la anterior commiteada):
1. ola4  → tracks i,j,k,l en paralelo (fundaciones compartidas).
   Al volver cada uno: verificar scope vs §1, correr su verificación mínima,
   commit conventional + push a main. Después lanzar ola5.
2. ola5  → tracks m,n en paralelo (catálogo+eventos, seed descuentos).
   Igual: scope → verificación → commit+push. Después ola6.
3. ola6  → tracks ds1..ds5 en paralelo (hojas de diseño).
   Cada ds reporta cambios que necesita en archivos globales (store-page.css,
   store-<tpl>.css de template compartido, seed_data.json, bridge): se
   ANOTAN, no se aplican. Después ola7.
4. ola7  → track-w (inspector, read-only) → commit del informe →
   track-x (integrador: aplica los cambios globales reportados, sincroniza
   seed_data.json, corre gates completos) → commit+push final.

Invariantes que ningún track puede romper: tarjeta sin botones internos,
contrato .ec-*/.tpc-* documentado, CSP del patrón intacto, normalize_image
en uploads, temas retrocompatibles (un diseño sin la clase nueva se ve
igual), cero scroll horizontal en 360px.

Si un track falla por permiso en background, relanzarlo con
is_background=false o resumirlo en foreground.
```

## 4. OLA F1 — fundaciones compartidas (4 en paralelo)

### track-i — Navbar

Archivos: `frontend/src/views/StorePublicLayout.vue` (header `.sp-top`,
`.sp-top-end`, `.sp-burger`, drawer `#sp-drawer`, tab bar móvil
`data-st-nav` bottom/top, `.sp-shop-nav`), selectores de nav en
`store-page.css`/`store-style-menus.css` solo si hace falta.

Hoy `.sp-top-end` acumula: cuenta, carrito (+badge), lupa, CTA, tema — y el
burger queda suelto a la izquierda. En móvil se montan/colisionan.

Tarea:
1. Definir y documentar (comentario CSS + variables) el contrato de
   prioridad del header por breakpoint: qué controles se muestran, cuáles
   se agrupan (p. ej. lupa+tema dentro del drawer en <768px), orden visual
   estable (burger → marca → links → buscador → acciones → CTA).
2. Implementar en markup+estilos scoped: contenedores con `min-width:0`,
   `flex-wrap` controlado, badge de carrito `position:absolute` (nunca
   empuja layout), tap targets ≥ 40px, `aria-label`/`aria-expanded`
   correctos, `:focus-visible` visible.
3. Verificar drawer y tab bar (`mobileNav` bottom/top): sin solapamiento
   con el contenido (`padding-bottom` del page-root cuando la tab bar es
   fixed), íconos del tab bar con label, "Más" abre el drawer con el resto
   de links.
4. NO tocar `store-design-*.css` ni `store-<tpl>.css`: los diseños que hoy
   pisan `.sp-top*` lo hacen con su scope; tu contrato debe ser
   sobre-escribible por ellos (clases estables, tokens).
5. Verificar 360/768/1024/1440 en una tienda local con
   `customer_auth_enabled` + `orders_enabled` + tema toggle + CTA, y una
   tienda mínima (sin catálogo) para el caso de pocos controles.

Cierre: tabla `breakpoint | controles visibles | problema encontrado | fix`,
`git diff --stat`, riesgos.

### track-j — Tarjeta de producto

Archivos: `frontend/src/components/store/TplProductCard.vue`,
`frontend/src/assets/store-tpl-card.css`, `OfferSeal.vue`, `StTag.vue`.

Tarea:
1. **Eliminar todo botón dentro de la tarjeta**: quitar del foot `.tpc-add`
   (botón carrito y link WhatsApp) y `.tpc-go` ("Ver producto"). El foot
   queda solo con el bloque de precio. Quitar `addToCart`, `adding`,
   `added`, `canBuy`, `stockExhausted` (queda solo el label de stock),
   `cartStore`, `storeCtx` si quedan huérfanos. Mantener declaradas (sin
   uso, con comentario `deprecado`) las props `addHref/addLabel/go/
   goLabel/ordersEnabled` para no romper call sites hasta track-m.
2. **Contrato de contenido** (en orden visual): etiquetas (eyebrow
   cat·brand + flags `-X%`/`Nuevo`), título clamp 2 líneas, estrellas,
   descripción mínima (clamp), tags (slot), **stock con icono** (package/
   box; "Agotado" en danger), precio: `<s>` tachado + precio oferta +
   **etiqueta de descuento especial en `position:absolute`** sobre la
   media (esquina, sin solapar el sello OfferSeal — regla de stacking:
   sello principal arriba-izq, etiqueta de campaña abajo-izq o la posición
   que el diseño ya use; documentarla en `store-tpl-card.css`).
3. **Placeholder con icono por categoría**: `phIcon` ya existe — mapear
   categoría→icono del set `AppIcon` (package, dumbbell, shirt, etc.) con
   fallback `package`. Íconos también en stock y en la etiqueta de evento.
4. Revisar `OfferSeal`/`StTag`: que el badge de campaña
   (`productDiscount(p)` → `{name, percent, ends_at}`) se muestre como
   etiqueta absoluta legible (nombre corto + %, ej. "HOT SALE −30%") sin
   depender de `label_url` (esa imagen es opcional y puede no existir).
5. Geometría intacta: `store-tpl-card.css` manda aspect-ratio/márgenes;
   los estados `:hover`/`:focus-visible` de la tarjeta como link completo.
6. Verificar visualmente la tarjeta en el catálogo de una tienda local con
   y sin oferta/descuento/stock agotado (puede usarse la API pública o
   mock; si necesita datos del seed de track-n, reportarlo como
   dependencia — NO crear descuentos).

Cierre: contrato documentado en comentario del SFC + `store-tpl-card.css`,
`git diff --stat`, riesgos.

### track-k — Auth minimalista

Archivos: `frontend/src/views/StoreAuthView.vue`,
`frontend/src/components/ecommerce/StoreAuthForm.vue`,
`frontend/src/components/ecommerce/StoreAuthModal.vue`.

Antes: invocar `modern-web-guidance` (forms, accesibilidad, focus). Referencia
de nivel: auth decompetidores (una columna, tarjeta centrada, un CTA).

Tarea:
1. Rediseñar la base scoped de `.ec-auth*` a **minimalista y profesional**:
   tarjeta única centrada (sin split forzado), jerarquía clara
   (kicker → título → sub → formulario), campos con label visible +
   `autocomplete`/`inputmode` correctos + error inline + `aria-describedby`,
   un solo botón primario, links secundarios (¿Olvidaste tu contraseña?,
   ¿Ya tenés cuenta? / Crear cuenta) como texto-subrayado, estados
   loading/error/success completos, `:focus-visible` visible, contraste AA.
2. Selector de modo (ingresar/registro/recuperar): control segmentado o
   tabs accesibles (`role="tab"` o radios), no links que recargan.
3. Los ornamentos (`.ec-auth-ambient`, `-hatch`, `-seal`, `-index`,
   `-trust`) siguen naciendo ocultos — el rediseño base NO depende de
   ellos; si el minimalismo los hace irrelevantes, dejar el mecanismo
   intacto (los diseños que los encienden deciden en F3).
4. `StoreAuthModal`: mismo lenguaje, centrado, `Esc` cierra, focus trap
   razonable, devuelve el foco al abrir.
5. Mantener el contrato de clases `.ec-auth*` que usan las hojas
   `store-design-*`: NO renombrar ni eliminar clases existentes; si el
   rediseño necesita markup nuevo, agregarlo sin romper a los diseños que
   los referencian (sus overrides pueden quedar desactualizados → anotarlo
   como lista de "revisar en F3" por diseño en el reporte).
6. Responsive 360→1440 + `prefers-reduced-motion`.

Cierre: capturas o descripción del antes/después, lista de hojas de diseño
que quedaron desalineadas para F3, `git diff --stat`, riesgos.

### track-l — Cuenta + seguimiento

Archivos: `frontend/src/views/StoreAccountView.vue`,
`frontend/src/components/ecommerce/account/AccountProfile.vue`,
`AccountOrders.vue`, `AccountAddresses.vue`,
`AccountSubscriptions.vue`, `frontend/src/views/StoreTrackingView.vue`.

Antes: invocar `modern-web-guidance`.

Tarea — Cuenta (`/cuenta`):
1. Más intuitiva: header de cuenta consistente (avatar/iniciales, nombre,
   email, estado de verificación), navegación de secciones clara (tabs o
   lista lateral según ancho), cada sección con título + descripción de una
   línea, estados vacíos con CTA ("Todavía no tenés pedidos → Ver
   catálogo"), errores con reintento.
2. Pedidos (`AccountOrders`): cada tarjeta de pedido muestra código,
   fecha, total, estado y **link directo a `/seguimiento?token=…`** si el
   payload lo trae (verificar campo; si no viaja, reportarlo — no inventar
   endpoints).
3. Sub-vistas `verificar`/`restablecer` (`acc-auth*`): mismo lenguaje que
   el nuevo auth de track-k (espaciado, tipografía, CTAs) sin importar
   archivos de track-k — replicar el patrón visual.

Tarea — Seguimiento (`StoreTrackingView.vue`):
1. **Mini-explicación para el comprador**: tarjeta/bloque "¿Cómo funciona
   el seguimiento?" (colapsable `<details>` o dismissible) que explique en
   3-4 líneas: el link que recibiste al comprar ES tu credencial (no lo
   compartas), cada estado del paso a paso, qué hacer si el pedido no
   aparece (ir a Mis pedidos), y que los tiempos los confirma el comercio.
2. Estados incompletos pulidos: `missing` (sin token), `error`
   (no encontrado), skeleton, terminal-bad — cada uno con CTA claro.
3. Stepper: labels legibles, estado actual destacado, fecha/hora del último
   cambio si el payload la trae.
4. Responsive 360→1440; las hojas `store-design-*` que pisan `.ec-track*`/
   `.acc-*` se revisan en F3 (reportar las clases nuevas que agregues).

Cierre: `git diff --stat`, riesgos, lista de hooks para F3.

## 5. OLA F2 — catálogo y datos (2 en paralelo)

### track-m — Catálogo + filtro de eventos

Archivos: `StoreApp/domains/stores/views/viewset.py` (SOLO la acción catalog
del viewset público), `frontend/src/api/stores.api.js`
(`normalizeCatalogParams` + `catalog()`), `frontend/src/api/catalog.api.js`,
`frontend/src/composables/useStoreCatalog.js`,
`frontend/src/composables/catalogFiltersUi.js`,
`frontend/src/views/StoreCatalogView.vue`,
`frontend/src/views/store/{raiz,mercado,gimnasio,movimiento,sastreria,
moderntec,indumentaria,impacto}/CatalogoView.vue`,
`frontend/src/assets/store-catalog.css`, `store-catalog-polish.css`,
`store-catalog-responsive.css`, `store-raiz-catalog.css`, y
`frontend/src/components/store/blocks/*` únicamente para quitar props de
tarjeta deprecadas donde se use `TplProductCard`.

Tarea:
1. **Backend**: nuevo param `?event=1` en el catálogo público. Semántica:
   producto alcanzado por algún `Discount` vigente (señal
   `product.effective_discount is not None` — NO confundir con
   `effective_offer`, que ya cubre `?offer=1`). Sumar `'event'` a
   `CATALOG_FINGERPRINT_PARAMS`, filtrar en el mismo loop, y exponer
   `event_count` en la respuesta (conteo global como `offer_count`/
   `new_count`). Test mínimo en `StoreApp/domains/catalog/tests.py` o el
   archivo de tests del dominio stores que ya cubra el catálogo.
2. **Front compartido**: `normalizeCatalogParams` acepta `event`; 
   `useStoreCatalog` suma `onlyEvent` (query `?event=1`, toggle, clear,
   hasFilters, activeTags "En evento", `eventTotal` desde `event_count`).
3. **Filtro "Eventos" condicional**: en cada `CatalogoView` el control de
   evento (chip o fila del rail, siguiendo el patrón visual de `onlyOffer`/
   `onlyNew` de esa plantilla) se renderiza SOLO si `eventTotal > 0` — sin
   eventos no aparece ni el botón ni espacio reservado. En móvil va al
   mismo sheet/bottom-sheet que el resto de filtros.
4. **Limpieza de tarjeta**: quitar props deprecadas (`addHref`, `addLabel`,
   `go`, `goLabel`, `ordersEnabled` si track-j las eliminó del render) de
   TODOS los call sites de `TplProductCard` (los 8 CatalogoView + bloques
   que lo usen — grepear `TplProductCard`).
5. Verificar con la API local: `GET /api/stores/public/<slug>/catalog/?event=1`
   filtra y `event_count` coincide. Si todavía no hay descuentos seed
   (track-n en paralelo), validar con un `Discount` creado a mano en shell
   y reportarlo.
6. Responsive 360→1440 del filtro en al menos 2 plantillas (una con rail
   desktop, una con bottom sheet).

Cierre: `git diff --stat`, salida del test nuevo, riesgos.

### track-n — Seed de descuentos demo (tienda david28)

Archivos: `StoreApp/domains/catalog/management/commands/seed_demo_discounts.py`
(archivo nuevo), ejecución de `venv/Scripts/python.exe manage.py ...`.

Tarea:
1. Comando idempotente `seed_demo_discounts --store <slug> [--dry-run]
   [--clear]`:
   - `--store` requerido (la tienda de pruebas del usuario; verificar slug
     real con `Store.objects.values_list('slug', flat=True)` — buscar el
     que corresponda a "david 28", p. ej. `david28`).
   - Crea ≥4 `Discount` vigentes HOY con `name` prefijado `DEMO ·` para
     poder borrarlos: scope `ALL` 15%, `CATEGORY` 25% (una categoría con
     productos), `BRAND` 30% (una marca con productos), `PRODUCTS` 40%
     (3-5 productos elegidos). `starts_at` = ayer, `ends_at` = +15 días,
     `is_active=True`.
   - `--clear` borra solo los `DEMO ·` de esa tienda.
   - Si existe una `SpecialOfferCampaign` vigente hoy, vincular UNO de los
     descuentos (`campaign=`) para probar la etiqueta de campaña; si no
     hay, dejarlo sin campaña y reportarlo (NO crear campañas globales).
   - Además, en la misma corrida y solo con `--store` explícito: dar
     `offer_price` manual al 20% de los productos que no tengan (para
     probar tachado+dto), dejar algunos `stock` en 0 / 3 / NULL variado, y
     asegurar ≥1 producto `is_active` con todo (oferta manual + descuento
     programado + stock) y ≥1 solo con descuento programado.
2. Verificar: `GET /api/stores/public/<slug>/catalog/` muestra
   `discount {name, percent, ends_at}` y `discount_offer`/`discount_names`
   en los productos correctos; `event_count`/`offer_count` > 0.
3. `--dry-run` primero, mostrar tabla de lo que crearía, luego aplicar.
4. Reportar slug real usado y conteos finales.

Cierre: `git diff --stat`, salidas de verify, riesgos.

## 6. OLA F3 — diseños (5 en paralelo, después de F2 commiteada)

Cada ds recibe sus slugs y aplica el checklist §6.1 sobre sus archivos.
Las plantillas sin `source/*.html` (gimnasio, impacto, movimiento) solo
tienen hoja CSS + vistas de template (compartidas → reportar).

### 6.1 Checklist por diseño (slug)

1. **Navbar móvil**: abrir la tienda del diseño (o su documento patrón) a
   360px y 768px: ningún botón del header montado/colisionado, drawer y tab
   bar (`data-st-nav` bottom/top/hamburguesa según el diseño — p. ej.
   sastreria tiene 3 menús móviles por estilo) abren bien, sin scroll
   horizontal. Corregir en `store-design-<slug>.css` (y `store-<tpl>.css`
   SOLO si el template es exclusivo del slug — si es compartido, reportar).
2. **Auth**: `/ingresar` y modal con la nueva base de track-k: la hoja del
   diseño aporta acento/tipografía/fondo sin romper jerarquía ni contraste
   AA; si la hoja vieja pelea con la base nueva, reescribir solo sus
   reglas `.ec-auth*`/`.ec-auth-card*` para que el resultado sea minimal +
   la firma del diseño (color, fuente, textura sutil — nada recargado).
3. **Cuenta + seguimiento**: `/cuenta` y `/seguimiento` heredan la base de
   track-l; la hoja ajusta acento/tipografía/bordes sin ocultar estados
   (vacío, error, skeleton) ni tap targets.
4. **Tarjetas de catálogo**: la sección catálogo (vista template o
   documento patrón) muestra el contrato de track-j: sin botones, etiqueta
   de descuento especial absoluta visible y sin solapar sello/foto,
   descripción mínima, stock con icono. En `source/<slug>.html` el markup
   `.ds-product` (si existe catálogo en el documento) se alinea al mismo
   contrato; si el render lo hace `pattern.js`/bridge, reportar el cambio
   necesario en vez de tocar el bridge.
5. **Filtro de eventos**: si el documento/vista tiene filtros, el control
   "Eventos" aparece solo con `event_count > 0` y con la estética del
   diseño; si el catálogo del patrón no tiene filtros, no inventarlos —
   reportar.
6. **Responsive**: 360/768/1024/1440 en home, catálogo, ficha, auth,
   cuenta, seguimiento. Cero scroll horizontal; imágenes sin CLS.

### 6.2 Reglas ds

- Solo los archivos de tu scope (§1). `seed_data.json`, `store-page.css`,
  `store-tpl-card.css`, `store-catalog*.css`, `store-raiz*.css`,
  `store-style-*.css`, `skin-*.css`, `views/store/<tpl>/**`,
  `pattern_bridge.js`/`pattern.js`, `templates/index.js` → PROHIBIDOS:
  reportar cambios necesarios con snippet.
- `sources/<slug>.html`: editar libre; NO regenerar `seed_data.json`.
- Cada fix verificado a 360px mínimo + un desktop.

Cierre por slug: tabla `superficie | fix | archivo:línea | nota para
integrador`, `git diff --stat`, riesgos.

## 7. OLA F4 — QA e integración

### track-w — Inspector visual (read-only sobre código)

Escribe SOLO `docs/qa-funcionalidad.md` (+ screenshots en carpeta de QA).
Recorre los 26 diseños × superficies (home, catálogo, ficha, auth, cuenta,
seguimiento) a 360 y 1440 usando `npm run visual:qa` y/o screenshots del
navegador. Por diseño reporta: colisiones de navbar móvil, auth que se ve
rota o recargada, cuenta/seguimiento confusos, tarjetas con botones o sin
contrato, filtro de eventos mal ubicado, scroll horizontal, CLS obvio.
Severidades: alta (roto/colisiona), media (desentona), baja (pulido).
NO arregla nada.

### track-x — Integración y cierre

Recibe el informe de track-w + la lista de cambios globales reportados por
todos los tracks. Aplica una sola vez: fixes en archivos globales,
sincronización de `seed_data.json` con los `sources/*.html` modificados
(vía `import_design_pattern` o edición del seed), hooks de plantilla
(compartidos) que los ds no pudieron tocar. Corre gates: `npm run lint`,
`npm test` (frontend), `python manage.py test` de los dominios tocados
(catalog/stores), `npm run visual:qa` si aplica. Cierra con tabla
`pendiente | resuelto por track-x | sigue abierto (con motivo)`.

## 8. Runbook — skills

| Skill | Lanza | Requisito previo |
|---|---|---|
| `ola4` | F1: track-i, track-j, track-k, track-l | — |
| `ola5` | F2: track-m, track-n | ola4 commiteada |
| `ola6` | F3: track-ds1 … track-ds5 | ola5 commiteada |
| `ola7` | F4: track-w → track-x | ola6 commiteada |

Perfiles en `.devin/agents/track-{i,j,k,l,m,n,ds1..ds5,w,x}.md`.
