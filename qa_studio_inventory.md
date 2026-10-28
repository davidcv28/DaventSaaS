# PASO 0 — Inventario Studio → Preview / Web pública (NO commitear)

Verificado en navegador (Playwright, chromium) contra `bench-store` + lectura de
`contract.js`, paneles, `previewBridge.js`, `store-page.css`, `store-services.css`.

Leyenda:
- ✅ = se refleja visible (confirmado midiendo estilos computados)
- ⚠️ = parcial: funciona solo en parte de las plantillas/superficies o roto
- ❌ = no se refleja: sin consumidor o el tema nunca llega

## Estado global

| | Preview (`?studio=1` + postMessage) | Web pública |
|---|---|---|
| Vars en `.store-page` | 56 (`--st-*` + `--store-*` + `--sp-*`) | 8 (solo `--store-*` legacy de `storeThemeVars`) |
| Atributos `data-st-*` | 10 puestos | ninguno |
| Causa | `studioVars/studioAttrs` se calculan solo si `studioMode && studioTheme` (postMessage) | `custom.site_theme` nunca se traduce a vars/attrs |

`StorePublicLayout.vue:94-99` — el hueco central.

## Bugs encontrados (pre-existentes, no de la prueba)

1. **`--sv-bg` nunca aplica** — `store-services.css:12-15`: el comentario
   `... caen a los --sp-*/--store-* ...` contiene `*/` dentro de `--sp-*/`
   → cierra el comentario antes de tiempo → el resto `--store-* ... */`
   se come la declaración `--sv-bg` hasta el próximo `;`. Resultado:
   `var(--sv-bg)` = guaranteed-invalid → el shorthand
   `background: var(--st-bg-layer, none), var(--sv-bg)` (línea 71) se
   descarta ENTERO → `.sv-page` nunca tiene fondo propio (hoy se ve el
   `.store-page` detrás, por eso no se nota).
2. **Fuentes `--st-font-*` viajan como slug crudo** — `previewBridge.js` llama
   `themeToCssVars(t)` SIN `resolveFont` → `--st-font-heading: 'playfair-display'`
   (literal, sin stack) → nombre de fuente inválido donde se consume
   (`--sv-display`/`--sv-body` en servicios) → tipografía de títulos/cuerpo
   NO aplica en servicios. `--store-font` sí viaja resuelto (fontFamilyOf)
   → el cuerpo sí aplica en landing/catálogo.
3. **Typo enum**: contrato/backend emiten `outlined`; `store-services.css:2070`
   selecciona `data-st-surface='bordered'` → `outlined` no matchea nada.
4. **`background.type:'image'` roto en preview** — el traductor pone
   `--sp-bg = value` (URL cruda `https://...`) → `background:` inválido →
   se descarta. Solo se vería bien si fuera `url("...")` (como sí hace
   `--st-bg-layer`, que a su vez nadie consume por el bug 1).
5. **`.sp-btn` radius solo en preview** — el único consumidor de
   `--sp-btn-radius` está en `BRIDGE_CSS` (inyectado solo dentro del iframe).
   En la hoja pública no hay regla → aunque llegue la var, no se aplica.
6. **`prefers-reduced-motion`**: ya respetado por `v-reveal` (reveal.js:26
   agrega `is-in` directo) y por `store-services.css:1563` + `:309`.

## Tabla opción por opción

| Opción | Preview | Pública | Superficies donde SÍ | Implementación |
|---|---|---|---|---|
| `palette.primary` | ⚠️ | ❌ | services (sv-acc), hero-alt, CTA band | `--st-primary` → `store-services.css:21`; `store-page.css:10262,10310,10437`. En landing los `.sp-btn` usan `--store-accent-ink` (viene de `accent`, no de `primary`) → medido: sin cambio |
| `palette.secondary` | ❌ | ❌ | ninguna | `--st-secondary`/`--st-on-secondary`: NINGUNO |
| `palette.accent` | ✅ | ❌ | landing, catálogo, services | traductor → `--store-accent/-ink/-soft` (consumido por ~todo) + `--st-accent`→`--sv-pop/--sv-focus` (services) |
| `palette.bg` | ⚠️ | ❌ | landing, catálogo | traductor → `--sp-bg` (`.store-page` bg, `store-page.css:25`). Services: `--st-bg`→`--sv-bg` ROTO por bug 1 |
| `palette.surface` | ⚠️ | ❌ | landing (genéricos `.sp-card`/`.sp-modal`/`.sp-form`), services (`--sv-card`) | `--sp-card/-solid/--sp-surface` + `--st-surface`→`--sv-card` (`store-services.css:18`). Plantillas con `--tpc-*` propios la ignoran |
| `palette.text` | ✅ | ❌ | landing, catálogo, services | `--sp-ink/--sp-ink-2` + `--st-text`→`--sv-fg` (`sv:16`) |
| `palette.muted` | ✅ | ❌ | landing, catálogo, services | `--sp-muted` + `--st-muted`→`--sv-mute` (`sv:17`) |
| `palette.border` | ✅ | ❌ | landing (consumidores `--sp-line`), services (`--sv-line`) | `store-page.css:11` + `sv:20` |
| `palette.success` | ⚠️ | ❌ | services solamente | `--st-success`→`--sv-ok` (`sv:26`: ticks/pills). Landing/catálogo: NINGUNO |
| `palette.danger` | ❌ | ❌ | ninguna | `--st-danger`: NINGUNO |
| `containers.radius` | ⚠️ | ❌ | landing genéricos (`.sp-card`,`.sp-drawer`,`.sp-modal`,`.sp-form`,`.sp-empty`,`.sp-about`,`.sp-map`), services | `--sp-radius` (`store-page.css:222` y cía) + `--st-radius`→`--sv-r-*` (`sv:35-38`). NO lo siguen: `.tpc`/`--tpc-*` propios, aurora y ~14 templates que fijan `--sv-r-*`/`--sv-btn-radius` literal |
| `containers.shadow` | ⚠️ | ❌ | mismos genéricos + services | `--sp-shadow-sm/md` + `--st-shadow`→`--sv-sh-pop/panel/form`,`--shadow-2`,`elevated` (`sv:41-43,70,2071`) |
| `containers.border` | ⚠️ | ❌ | services solamente | `--st-border-w`→`--sv-bw` (`sv:40`). Landing/catálogo: NINGUNO |
| `containers.density` | ⚠️ | ❌ | services solamente | `--st-card-pad` (`sv:196,232,251,266,1830,1842,1850`), `--st-section-gap` (`sv:91`). Landing/catálogo: NINGUNO (medido `.tpc` pad 0→0) |
| `containers.surface` | ⚠️ | ❌ | services solamente | `data-st-surface` → `sv:2069-2071`: `flat`✓, `elevated`✓, `'bordered'`TYPO (enum real: `outlined` → no matchea), `glass` NINGUNO. Landing/catálogo: NINGUNO |
| `typography.heading` | ❌ | ❌ | ninguna | `--st-font-heading`→`--sv-display` (`sv:63`) pero llega el SLUG sin resolver (bug 2) → inválido. Landing h1 usa `--sp-display` de plantilla: NINGUNO |
| `typography.body` | ⚠️ | ❌ | landing, catálogo (`--store-font` resuelto ✓); services ROTO (slug en `--sv-body`, cae a sans-serif) | traductor `--store-font` (`previewBridge:37`) + `--st-font-body`→`--sv-body` (`sv:64`, bug 2) |
| `typography.scale` | ⚠️ | ❌ | services (`--fs-hero/h2/body`) + `.sp-hal-title` | `--st-h1/h2/text-size` (`sv:67`, `store-page.css:10258`). Landing/catálogo h1/p de plantillas: NINGUNO (medido 58.9px→58.9px) |
| `typography.weightHeading` | ⚠️ | ❌ | services (`.sv-page h1,h2`) + `.sp-hal-title` | `--st-weight-heading` (`sv:88`, `store-page.css:10258`). Landing: NINGUNO |
| `typography.letterSpacing` | ⚠️ | ❌ | services (`--sv-head-ls`) + `.sp-hal-title` | `--st-tracking` (`sv:58`, `10258`). Landing: NINGUNO |
| `buttons.shape` | ⚠️ | ❌ | landing/catálogo SOLO en preview (bridge CSS inyectado); services (cuando la plantilla no pisa `--sv-btn-radius`) | `BRIDGE_CSS` (`previewBridge:103-104`, solo iframe) + `--st-btn-radius`→`--sv-btn-radius` (`sv:39`, pisado por ~14 tpls). Hoja pública: NINGUNO consumidor de `--sp-btn-radius` (bug 5) |
| `buttons.style` | ⚠️ | ❌ | services solamente | `data-st-btn-style` → `sv:2067-2068`: `outline`✓, `ghost`✓; `solid`=base; `gradient` NINGUNO. `.sp-btn`/`.sp-hal-btn`: NINGUNO |
| `buttons.size` | ⚠️ | ❌ | services (`.sv-btn`) + `.sp-hal-btn` | `--st-btn-h/px/fs` (`sv:106-108`, `10262,10307,10310`). `.sp-btn` landing: NINGUNO (44px fijo) |
| `background.type`+`value` | ⚠️ | ❌ | landing, catálogo: solid/gradient/mesh/pattern ✓ (vía `--sp-bg`); `image` ROTO (bug 4). Services: todo ROTO (bug 1) | traductor `previewBridge:40,53-55`; `--st-bg-layer` sin consumidor vivo |
| `background.overlay` | ⚠️ | ❌ | solo `.sp-hal-veil` (hero-alt) | `--st-bg-overlay` (`store-page.css:10250`). Para el fondo de página y services: NINGUNO |
| `motion.reveal` | ⚠️ | ❌ | services solamente | `data-st-reveal` → `sv:2058-2060`: `none`✓, `fade`✓; `rise`=comportamiento base; `stagger` NINGUNO. Landing/catálogo (`.sp-rv`): NINGUNO |
| `motion.hover` | ⚠️ | ❌ | services solamente | `data-st-hover` → `sv:2061-2066`: `none`✓, `glow`✓; `lift`=base. Landing/catálogo: NINGUNO (`.tpc:hover` fijo por plantilla) |
| `motion.intensity` | ❌ | ❌ | ninguna | `--st-motion-dur`: NINGUNO |
| `mobile.nav` | ❌ | ❌ | ninguna | `data-st-nav`: NINGUNO (`.sp-dock` existe pero lo manda `showDock`, no el tema) |
| `mobile.gridCols` | ⚠️ | ❌ | services solamente (`.sv-list` ≤479px) | `--st-grid-cols` (`sv:2073` bajo `@media ≤479px`). Grillas de catálogo: NINGUNO |
| `mobile.cardStyle` | ❌ | ❌ | ninguna | `data-st-card`: NINGUNO |
| `mobile.stickyCta` | ⚠️ | ⚠️ | services solamente (`.sv-bar`, ≤1023px, z-42) | `StoreServicesView.vue:288-291` lee `site_theme` directo + `sv:1463-1484`. **Ojo**: es la única opción que ya aplica EN LA PÚBLICA (lee `custom.site_theme` sin vars/attrs). Landing/catálogo: NINGUNO |
| `mobile.heroHeight` | ❌ | ❌ | ninguna | `data-st-hero`: NINGUNO |

## Lo que YA existe (no hay que construir)

- Token `?preview=` completo: `publicStore(slug,{preview})` (`stores.api.js:162`),
  `keep.preview` en navegación interna (`StorePublicLayout:440-446`), badge
  `.sp-preview-badge` (`:473`), backend firmado/expira/foráneo→publicado.
- Backend: `site_theme` validado + filtrado por plan + draft/publish/versiones.
- `vReveal` con reduced-motion; `.sv-bar` sticky con su reserva de espacio.
- El traductor `studioPreviewVars` ya produce `--store-*`/`--sp-*` equivalentes:
  es la base para la función compartida del paso 1.

## Hallazgo medido (preview vs tema vacío, aurora 1280)

Cambia: `palette.bg` (vía bg-image), `text`, `border`, `accent→--store-*`,
`body font`, `radius`/`shadow` en genéricos `.sp-card`, `density`/`shadow`/
`surface`/`btnSize`/`weightHeading`/`tracking`/`scale` en servicios.
No cambia en ningún lado: `secondary`, `danger`, `borderW` (landing),
`density`/`surface` (landing), `btnStyle`/`btnSize` (`.sp-btn`), `reveal`/`hover`
(landing), `intensity`, `nav`, `cardStyle`, `stickyCta` (fuera de services),
`heroHeight`, `overlay` (fuera de hero-alt), `image` bg.
