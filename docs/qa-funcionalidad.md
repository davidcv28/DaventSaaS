# QA funcional — inspección visual track-w (ola7)

Fecha: 2026-11-12 · Alcance: PLAN_FUNCIONALIDAD.md §7 (track-w), read-only.

## Método y cobertura

- 26 tiendas QA (una por diseño) recorridas en home, catálogo, ficha,
  `/ingresar`, `/cuenta` y `/seguimiento`, a **360×800** y **1440×900**
  (300 páginas renderizadas + tienda `davent` parcial por crash — ver A-2).
- Motor: Playwright/Chromium headless sobre `http://localhost:5173`
  (Vite) + API `http://localhost:8000`. Las 25 tiendas con patrón
  documento renderizan la landing/catálogo/ficha dentro del iframe
  sandboxeado `/api/stores/public/<slug>/pattern/document/`; auth, cuenta
  y seguimiento son páginas Vue (`store-design-<slug>.css`).
  `impacto`, `indumentaria` y `gimnasio` NO tienen documento de patrón
  (`pattern/?meta=1` → `ready=false`) y usan las plantillas Vue
  (catálogo Raíz + `TplProductCard`).
- Por página se midió: scroll horizontal (host + iframe), errores de
  consola/página, solapamiento geométrico de controles del header,
  elementos interactivos dentro de tarjetas, presencia del filtro de
  eventos vs `event_count` real de la API, y CLS (PerformanceObserver
  layout-shift).
- Screenshots: `frontend/visual-qa/qa-func/<diseño>/<superficie>-<ancho>.png`
  (300 PNG; la carpeta está gitignored). Datos crudos:
  `frontend/visual-qa/qa-func/report-*.json` + `summary.txt`.
- Nota de método: las corridas masivas saturaron el throttle
  `public_read` (1000/h por IP, `NUM_PROXIES=1` → keyea por último
  `X-Forwarded-For`). La corrida definitiva rotó una IP única por
  contexto de navegador para no mezclar datos. Las visitas de las
  tiendas QA quedaron registradas con IPs sintéticas `10.x` (solo
  contadores de visitas; sin otro efecto).

## Resultado global

- **Scroll horizontal: 0** en las 300 páginas (host e iframe).
- **Colisiones de navbar: 0** solapamientos detectados entre controles
  del header en ninguna superficie ni viewport.
- **Botones dentro de tarjetas: solo `showroom`** (ver A-1); el resto de
  los documentos patrón y las tarjetas Vue (`TplProductCard`) cumplen
  "tarjeta = un solo link" (`buyVisible=0` en todas partes; el bridge
  sigue inyectando `.dsx-buy-wrap` pero los sources lo ocultan por CSS —
  pendiente conocido, `docs/global-changes-ola6.md` §1).
- **Contrato de tarjeta en documentos patrón**: todas las tarjetas
  `.ds-product` traen título, descripción (`.ds-product-desc`), tag de
  stock (`.ds-stock`) y precio con `<s>` tachado + badge `data-off`.
- **Filtro "Eventos"**: `event_count=0` en las 26 tiendas QA → el
  control correctamente NO aparece en ninguna (contrato §0 cumplido).
  En documentos patrón el filtro no existe en absoluto (gap conocido,
  `docs/global-changes-ola6.md` §2 — no se reporta como hallazgo nuevo).
- **CLS y fuentes web**: las primeras corridas marcaron CLS alto y
  errores CORS de `fonts.gstatic.com`, pero fueron **artefactos del
  entorno saturado** — re-medido en limpio: CLS=0 y las fuentes
  (`document.fonts` → `loaded`, también dentro del iframe) cargan bien.
  NO son hallazgos.

## Hallazgos ALTOS

### A-1 · showroom (`nomada`) — botón interactivo dentro del link de la tarjeta

Cada `.ds-product` del documento lleva `<button class="p-heart"
aria-label="Guardar en favoritos">` **dentro** de
`<a class="ds-product-link">` (anidado en `.ds-product-copy`). Medido:
22 botones visibles en home y catálogo a 360 y 1440 px (48 tarjetas en
ficha con 4 botones de relacionados). Viola el contrato "la tarjeta
entera es el link / cero interactivos dentro" y es HTML inválido
(interactivo dentro de anchor): el click en el corazón probablemente
navega a la ficha.

- `StoreApp/domains/design/sources/showroom.html` ~L1085-1095 ya tiene
  el fix correcto (`card.appendChild(b)` como hermano del link, con
  comentario explícito del contrato), pero el documento servido sigue
  saliendo de `seed_data.json` **sin resincronizar** → pendiente
  conocido de track-x (`docs/global-changes-ola6.md` §3). Mientras el
  seed no se regenere, el diseño servido está roto.
- Severidad: **alta** (contrato de tarjeta roto en producción).

### A-2 · mercado (`davent`) — `/davent/catalogo` crashea el navegador

`http://localhost:5173/davent/catalogo` a 360 px tumba el renderer de
Chromium (`Target crashed`) y en una corrida llegó a cerrar el browser
completo. Reproducido 3/3 veces. El documento patrón aislado
(`/api/stores/public/davent/pattern/document/?surface=catalog`) renderiza
bien (4 tarjetas, sin crash) → el fallo está en la integración
host↔iframe (`pattern.js`/`pattern_bridge.js`/`PatternSurface`) con este
payload concreto: tienda `david28` (slug real `davent`) con 2 productos,
4 descuentos `DEMO ·` vigentes y `event_count=1`.

- Hipótesis para track-x: el surface `catalog` del documento + datos de
  descuento/evento disparan un loop o excepción fatal en el puente
  (revisar `applyCatalog`/`injectCardBuys`/resize `davent:ds-frame`).
- Efecto colateral de QA: las superficies catálogo y ficha del diseño
  `mercado` con datos reales de descuentos quedan **sin verificar**
  (el resto del diseño sí está cubierto por `bazar-artemisa`).
- Severidad: **alta** (página pública que crashea el navegador del
  comprador).

### A-3 · tarjetas Vue (`TplProductCard`) — la descripción nunca se renderiza

El contrato §0 exige "descripción mínima" en la tarjeta. El prop `desc`
existe en `TplProductCard.vue` (L47, render en L176) pero **ningún call
site lo pasa** (verificado en `raiz/CatalogoView.vue` L241-250,
`BlkFeatured.vue`, `BlkOffers.vue`, `RhRecent.vue`, `RhOffers.vue`,
`ImpFeatured.vue`, `mercado/CatalogoView.vue` y bloques afines). Resultado
medido: `.tpc-desc` ausente en el 100% de las tarjetas Vue — en la
práctica afecta a los catálogos de `impacto`, `indumentaria` y
`gimnasio` (las 3 tiendas QA sin documento de patrón) y a todas las
plantillas Vue (`raiz`, `mercado`, `moderntec`, `movimiento`,
`sastreria`) cuando se usen sin patrón.

- Stock: se muestra solo cuando `available_stock` es numérico
  (`TplProductCard.vue` L105-111, null = ilimitado → oculto). En las
  tarjetas Vue relevadas no había stock trazado en esos productos —
  comportamiento por diseño, no bug; se deja asentado para track-n
  (sembrar stocks variados ya previsto).
- Severidad: **alta** (criterio de contrato incumplido de forma
  sistémica en el motor Vue).

## Hallazgos MEDIOS

### M-1 · `/seguimiento` sin piel de diseño en 11 diseños (+1 parcial)

Las hojas `store-design-*.css` no contienen **ninguna** regla `.ec-track`
en: `olivium`, `atelier-noir`, `guardia`, `expediente`, `silicio` (DS4) y
`neon`, `showroom`, `sastreria`, `autoservicio`, `movimiento`, `umbral`
(DS5). La página de seguimiento queda con el acento neutro base en esos
diseños (los tracks DS1-DS3 sí la tematizaron: portico, esencial, mercado,
gimnasio, moderntec, ruta, aurum, brigada, indumentaria, impacto, calzado,
moda, modista, topmodern; `viajero` tiene solo 7 reglas — cobertura
parcial).

- Verificado por grep sobre `frontend/src/assets/store-design-*.css`
  (0 ocurrencias de `ec-track`) + la raíz `.ec-track` en
  `store-page.css:478` y `StoreTrackingView.vue`.
- Severidad: **media** por diseño (desentona, no rompe).

### M-2 · carrito/checkout/recibo/legal sin piel de diseño (todas)

Mismo hueco que M-1 pero para `.ec-cartpg`, `.ec-checkout`,
`.ec-receiptpg`, `.ec-legal`: ninguna hoja `store-design-*` las re-tema.
Ya reportado como pendiente global en `docs/global-changes-ola6.md` §4 —
se cita, no es hallazgo nuevo; queda como media sistémica hasta que
track-x decida extender el `:is()`.

### M-3 · `calzado` — `.ds-stock` oculto con `!important` (bug latente)

`sources/calzado.html` tiene `.ds-stock{display:none!important}` en vista
lista; el puente fuerza `.is-out` con `!important` y pierde la cascada —
una tarjeta agotada puede mostrar "En stock". Reportado en
`global-changes-ola6.md` §5; se confirma como media para `calzado`
(`zancada`).

### M-4 · tienda `demo` renderiza `esencial`, no `movimiento`

El mapping de QA (`scripts/qa-store-designs.mjs`) asume `demo` =
movimiento, pero `/demo` resuelve `data-design="esencial"`
(`customization.template='raiz'`, `site_theme={}`). El diseño
`movimiento` quedó **sin cobertura real** en esta pasada (no tiene
`sources/*.html` propio — plan §6). Si la fallback a `esencial` es
silenciosa también en tiendas reales al elegir movimiento, revisar la
resolución patrón→estilo. Severidad: **media** (cobertura + posible
fallback silencioso).

### M-5 · tienda `ruta-sur` sin superficie catálogo/producto

`site_templates=['landing','services']` → `/ruta-sur/catalogo` y
`/ruta-sur/producto/:id` redirigen a home. El contrato de tarjeta y los
filtros del diseño `ruta` no pudieron verificarse en vivo (el documento
patrón puede renderizarse directo por
`/api/stores/public/ruta-sur/pattern/document/?surface=catalog` si se
quiere cobertura). Severidad: **media** (cobertura incompleta, no bug de
diseño confirmado).

## Hallazgos BAJOS / notas

- **B-1** `indumentaria` (`atelier-luma`): ruido de consola
  `maps.googleapis.com/.../csp_test` bloqueado por CORS — viene del embed
  de Google Maps, no del diseño; ignorable.
- **B-2** `seed_data.json` sin resincronizar con los `sources/*.html`
  modificados en ola6 → los fixes de tarjeta/auth/seguimiento de los ds
  NO están vivos en las tiendas publicadas hasta que track-x regenere el
  seed (`global-changes-ola6.md` §3). Es la causa raíz de A-1.
- **B-3** Documentos patrón: sin `data-event` ni control de eventos
  (`global-changes-ola6.md` §2) — las tarjetas sí muestran tachado+dto+
  badge cuando hay oferta/descuento vía `data-off`/`effective_offer`.
- **B-4** `.ds-stock` del fragmento emite "En stock" estático hasta que el
  puente lo repinta con stock real — si el puente tarda/falla, una tarjeta
  agotada puede mentir transitoriamente (depende del bridge, no de los
  designs).
- **B-5** Auth/cuenta/seguimiento se verificaron como páginas Vue
  temizadas (todas las hojas tienen reglas `.ec-auth`/`.ec-account`
  completas — 65-239 reglas por hoja); no se detectaron estados rotos en
  los datos medidos, pero la calidad estética fina queda para revisión
  visual de los screenshots adjuntos.

## Lo que NO se pudo verificar (limitaciones)

- Interacciones JS del navbar móvil (apertura de drawer/tab bar) — la
  auditoría fue estática/geométrica, no clicó controles.
- Contraste AA texto/fondo (el audit de `visual-qa.mjs` requiere
  credenciales QA que no estaban en `visual-qa.config.json`).
- Estado "con eventos" del filtro (ninguna tienda QA tiene
  `event_count>0`; `davent` sí pero su catálogo crashea — A-2).
- `movimiento` (sin cobertura real — M-4) y catálogo/ficha de `ruta`
  (M-5).
- Comprador logueado en `/cuenta` y `/seguimiento` con token real
  (se verificó el estado guest/missing).

## Conteo por severidad

| Severidad | Cantidad |
|---|---|
| Alta | 3 (A-1 showroom, A-2 mercado/davent crash, A-3 tarjetas Vue sin descripción) |
| Media | 5 (M-1…M-5) |
| Baja | 5 (B-1…B-5) |

## Los hallazgos altos, ordenados por diseño

1. **showroom** (`nomada`): `.p-heart` dentro del link de tarjeta — 22
   botones interactivos anidados por página de catálogo (A-1; fix ya en
   `sources/showroom.html`, falta resincronizar `seed_data.json`).
2. **mercado** (`davent`): `/catalogo` crashea el navegador del
   comprador, reproducible (A-2; sospecha en bridge/pattern.js con
   payload de descuentos).
3. **impacto / indumentaria / gimnasio** (+ todas las plantillas Vue):
   `TplProductCard` nunca recibe `desc` → cero descripciones en
   tarjetas, contrato §0 incumplido (A-3; fix = pasar `:desc="p.description"`
   en los call sites o repensar la prop).

Hallazgos altos adicionales por diseño: **ninguno más reproducible** —
las 23 tiendas restantes cumplieren navbar sin colisiones, cero scroll
horizontal, tarjetas sin botones (salvo showroom) y filtro de eventos
correctamente oculto.
