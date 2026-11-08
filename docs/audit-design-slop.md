# Auditoría visual — design slop (track A, read-only)

> Inventario priorizado de defectos visuales en los diseños que se sirven a
> clientes. Criterio: `DESIGN_SYSTEM.md` §1–§7 y la tabla §0 de
> `PLAN_WEB_PROFESIONAL.md`. Cada hallazgo cita `archivo:línea` real.
>
> **Alcance leído**: `StoreApp/domains/design/sources/*.html` (20 documentos
> de patrón + `fotos.html` wireframe), `frontend/src/assets/store-*.css`,
> `frontend/src/assets/store-page.css`, `DESIGN_SYSTEM.md` §1–§7,
> `frontend/src/templates/index.js`.
>
> **Caveat de medición**: los tokens `--ds-*` del host pueden pisar las
> fallbacks medidas aquí; los ratios del anexo corresponden a las paletas por
> defecto que se sirven cuando la tienda no personaliza el tema.
>
> **Nota de cobertura**: los patrones `gimnasio`, `indumentaria` e `impacto`
> no tienen `sources/<slug>.html`; su superficie real son las vistas Vue +
> las pieles `store-gimnasio.css`, `store-indumentaria.css` y
> `store-impacto.css` (sección B). `moderntec.html` es un documento demo
> estático (sin `{{variables}}`): la web real usa la plantilla Vue
> `moderntec`, pero el archivo igual se sirve como documento de patrón.
> `fotos.html` no es patrón (no está en `seed_data.json`): es un wireframe
> boceto huérfano en `sources/`.

---

## 1. Tabla de hallazgos

### A. Documentos de patrón (`StoreApp/domains/design/sources/*.html`)

| Patrón | Severidad | Defecto | Archivo:línea | Fix propuesto |
|--------|-----------|---------|---------------|----------------|
| showroom | **alta** | Contraste AA roto en tema claro: `--muted:#8A8A8A` sobre `--bg:#FFF` = **3.45** y sobre `--surface:#F4F4F4` = **3.14** (usado en `.about-lead` 16px, `.sec-head p`, descripciones — 45 usos de `var(--muted)`). Además: sin `focus-visible` y `outline:0` en inputs con indicador de solo `border-color`; 13 hex `#fff`/`#0d0d0d`/`#111`/`#B3261E` fuera de token | `showroom.html:31` (token), `:85`,`:322`,`:356`, `:124-171`,`:332` | Oscurecer `--muted` a ~`#767676`; anillo `outline:2px solid var(--ink)` en `:focus-visible`; hex → tokens |
| expediente | **alta** | Contraste AA roto en tema claro: `--muted:#7D7460` sobre `--paper:#E9E1CB` = **3.55** / `--surface` = **3.92** (`.sec-note`, `.ds-product-desc`, `.about-spec` — texto real de 11–12px). Además: `@keyframes gridPan` anima `background-position`; transitions de `width` (`:128`), `right` (`:156`), `box-shadow` (`:333`,`:370`,`:490`), `padding-left` (`:436`,`:570`,`:611`,`:955`) | `expediente.html:45` (token), usos `:306-307`,`:405`,`:462`; `:128`,`:156` | Subir `--muted` a ~`#6B6250`; pan de grilla → `transform`; `right` → `translateX` |
| atelier-noir | **alta** | Contraste AA roto en tema claro: `--muted:#8A7F70` sobre `--paper:#F4EFE6` = **3.43** / `--surface:#EAE2D3` = **3.05** (`.sec-note`, `.about-lead`, `.mission p` — cuerpo 13–16px). Además: `backdrop-filter` en `.head.is-scrolled` (barra **fixed** `:124`); transitions `filter` (`:221`,`:327`,`:429`), `padding` (`:205`,`:480`,`:613`), `max-height` (`:137`), `min-height` (`:148`); dingbats `✦` (`:147`,`:267`) | `atelier-noir.html:34` (token), usos `:288`,`:302`,`:394-401`; `:131`,`:221` | Oscurecer muted ~`#7A6E5C`; fondo `color-mix` sin blur en `.head`; props → `transform`/`opacity` |
| viajero | **alta** | Contraste AA roto en CTA: `--on-accent:#FFF` sobre `--accent:#E0522B` = **3.88** en tema claro (botón primario ~14px). Además: `@keyframes pulse` infinito anima `box-shadow` (`:264`); `route-dash` `stroke-dashoffset` (`:302`); ~10 transitions de `box-shadow`, `width` (`:188`), `filter` (`:433`); hex `#fff`/`#170B05`/`#B3261E` (`:156`,`:631`,`:652`,`:891`) | `viajero.html:52` (`--on-accent`),`:50` (`--accent`); `:264`,`:302`,`:188` | Botón primario → `--accent-deep:#8E2A10` o ink `#1A1009`; glow → `transform:scale`+`opacity` |
| moderntec | **alta** | `<link>` a Google Fonts muerto por CSP: `style-src 'unsafe-inline'` no admite hojas externas → Space Grotesk/Inter/JetBrains Mono nunca cargan en el documento servido (cae a system-ui). Además (doc demo): sin `prefers-reduced-motion` (0), sin `:focus` (0), sin `:empty`/`:has` (0), `backdrop-filter` en `.nav` fixed (`:60`), `transition:box-shadow` (`:81`), gradientes con hex (`:107`,`:118`,`:158`,`:162`), contenido demo hardcodeado (NEXA, precios) | `moderntec.html:7-8`; `:60`,`:81`,`:113`,`:230-240` | `@font-face` a `fonts.gstatic.com` (patrón del resto de docs); bloque rm global; focus ring; si no se usa, excluir del seed de documentos |
| neon | media | `backdrop-filter` en `.top` fixed (`:168`), `.mmenu` fixed (`:190`), `.wo-bar` sticky bottom (`:812`); `@keyframes dash`/`draw` `stroke-dashoffset` (`:116`,`:145`), `footline` `background-position-x` (`:831`); ~12 transitions de `box-shadow`, `filter` (`:296`,`:399`); sin `focus-visible` global ni `@media (hover)` | `neon.html:168`,`:116`,`:831`,`:152`,`:296` | Fondo `color-mix` sin blur en barras; dash → `opacity`; anillo focus global; gate hover |
| ruta | media | `backdrop-filter` en `.top` fixed (`:114`) y `.m-tabs` fixed móvil (`:707`); `@keyframes drift` anima `left` (`:188`) y `sunPulse` `box-shadow` (`:177`); ~10 transitions de `box-shadow` (`:97`,`:223`,`:371`,`:448`,`:532`,`:573`,`:591`,`:598`,`:791`); hex `#fff`/`#1b2a23`/`#f8cd70` (`:106`,`:173`,`:232`,`:352`); sin `@media (hover)` | `ruta.html:114`,`:188`,`:177`,`:791` | Quitar blur; `drift` → `transform:translateX`; `sunPulse` → `transform`/`opacity` |
| sastreria | media | `backdrop-filter` en `.top` (fixed cuando `data-ds-style` presente, `:311`) y `.m-tabs` fixed (`:340`); swatch chips con hex literales `#D8CBB4`/`#8C9A86`/`#6E4A2F` (`:122-124` — intencional: son las muestras); error `#8a4b3a` (`:269`); 4 transitions no compuestas | `sastreria.html:60`,`:311`,`:340`,`:122-124`,`:269` | Ídem neon; `#8a4b3a` → token `--danger` |
| silicio | media | `backdrop-filter` en `.top` **fixed** (`:194`) y la transición anima la propia `backdrop-filter` (`:194`) — doble violación §2+§5; 4 keyframes infinitos animan `box-shadow` (`eybPulse`, `eybPulseV`, `btnBreath`, `livePulse`); 19 hex fuera de token (`border #fff`/`#0A0D12` check `:1516-1521`, `background:#000` `:1603`, scrims `:386`,`:640`,`:734`,`:1229`); `:empty`/`:has` casi ausentes (3 reglas — el host `SURFACE_CSS` cubre lo genérico) | `silicio.html:194`,`:1516`,`:1603` | Fondo translúcido sin blur; glow por `transform`/`opacity`; check → `var(--on-accent)` |
| olivium | media | Contraste claro `--muted` sobre `--paper` = **4.30** (borde); `.tabbar` fixed + `backdrop-filter` (`:259`); `@keyframes pulse` `box-shadow` infinito (`:306`); `route-dash` `stroke-dashoffset` (`:338`); `transition:width` (`:226`), `filter` (`:500`), `box-shadow` ×10; hex `#fff`/`#241A05`/`#B3261E` (`:187`,`:540`,`:742`,`:1016`) | `olivium.html:78` (token),`:259`,`:306`,`:226`,`:1016` | Muted → `#6E7A4A` aprox.; ídem neon/silicio |
| modista | media | Contraste claro `--muted` sobre `--surface` = **4.34** (borde); `@keyframes thread-sew` `stroke-dashoffset` (`:161`) y `wipe` `clip-path` (`:1107`); ~8 transitions `box-shadow`/`padding`/`outline-offset` (`:491`,`:592`,`:609`,`:704`,`:987`); hex `#FFF6FB` (`:362`) | `modista.html:76` (token),`:161`,`:1107`,`:491` | Muted → `#8F84A0`; dash → `opacity`; wipe → `transform` de máscara |
| moda | media | Contraste claro `--muted` sobre `--surface` = **4.33** (borde); `@keyframes wipe` `clip-path` (`:806`); transitions `box-shadow` (`:128`), `padding` (`:206`,`:394`,`:474`,`:612`), `max-height` (`:135`), `min-height` (`:146`); hex `#FFF8F2` (`:267`) | `moda.html:61` (token),`:806`,`:128`,`:206` | Ídem modista; `max/min-height` acordeón → `grid-template-rows` |
| mercado | media | `@keyframes bz-pulse` infinito anima `box-shadow` (`:936`); `transition:left` (`:200`); ~5 transitions de `box-shadow` (`:88`,`:191`,`:311`,`:339`,`:418`); **hardcodes fuera de token en tema oscuro**: search input con grises Tailwind sueltos | `mercado.html:936`,`:200`,`:777-781`,`:707` (`#c00`) | Pulse → `transform`/`opacity`; search dark → tokens `--soft/--ink/--muted` |
| portico | media | `@keyframes ds-drop` anima `top` (`:338`) — layout por frame; transitions de `box-shadow` (`:149`,`:188`,`:562`,`:701`), `filter` (`:345`,`:566`,`:614`,`:633`,`:837`), `width` (`:479`,`:577`), `right`/`inset`/`padding-left` (`:214`,`:227`,`:275`,`:525`,`:860`,`:964`,`:1107`); hex `#fff` gradiente (`:153`) | `portico.html:338`,`:479`,`:214`,`:227`,`:153` | `ds-drop` → `transform:translateY`; `width` de barras → `transform:scaleX` |
| esencial | media | `@keyframes sheen` anima `background-position` (`:1032`) + `transition:background-position` (`:165`); ~10 transitions de `box-shadow`; hex `#241a05`/`#b3402e`/`#fff` (`:397`,`:895`,`:931`) | `esencial.html:1032`,`:165`,`:397`,`:895`,`:931` | Sheen → `transform` de pseudo-elemento; hex → `color-mix`/tokens |
| calzado | media | `transition:filter` (`:568`), `padding` (`:130`,`:213`); ~15 `color:#fff`/`#111` hardcodeados fuera de token (sobre paneles oscuros — contraste correcto pero fuera de contrato); **oscuro**: `--accent-ink/acento` = **4.44** (borde AA) | `calzado.html:568`,`:226-905`, tokens oscuros `:59-66` | Acento oscuro → mix con `#F2F0EC` hasta ≥4.5; hex → `var(--panel-ink)`/`var(--btn-ink)` |
| aurum | media | ~6 transitions de `box-shadow` (`:182`,`:788`,`:956`,`:1055`,`:1153`,`:1275`); **12 hex fuera de token**: paradas de gradiente (`:388`,`:723`,`:736`,`:743`,`:745`,`:1072`) y colores de texto (`:405`,`:423`,`:428`,`:967`,`:969`,`:1166`); **claro (aurum-dia)**: `--muted`/bg = **4.43**, `--gold-text`/bg = **4.55** (límite) | `aurum.html:182`,`:388`,`:405`, tokens light `:48-61` | Gradientes → `color-mix` con tokens; muted dia → `#6E6350` |
| brigada | media | ~15+ transitions de `box-shadow` en hovers (`:172`,`:196`,`:207`,`:248`,`:306`,`:315`,`:341`,`:392`,`:411`,`:421`,`:451`,`:476`,`:482`,`:668`,`:720`) + `width` (`:177`), `min-height` (`:175`); sin `@media (hover)` | `brigada.html:172-720` | Shadow hover → `translateY`+`border-color`; gate `@media (hover:hover)` |
| guardia | media | Tema claro: `--on-accent:#FFF7F2` sobre `--accent:#D63A17` = **4.43** (borde AA en botones); 15 hex fuera de token (hero overlay `:111-112`, paneles `:215-309`, scrims `:425`,`:813`); `transition:filter` (`:407`,`:531`), `padding` (`:201`,`:352`); sin `@media (hover)` | `guardia.html:63` (tokens light `:50-65`),`:111`,`:215`,`:407` | Accent claro → `#B3300E` (`--accent-text`) en fondos de botón o ink `#12171F` |
| topmodern | media | `@keyframes pulse-dot` anima `box-shadow` (`:208`); ~8 transitions `box-shadow`, `padding-left` (`:232`,`:412`,`:429`), `filter` (`:336`); hex `#000` ticker (`:175`), `#2F6B4F`/`#4CC38A` stock dot (`:208-209`); sin `focus-visible` global (solo inputs con ring `:390-518`; links/botones caen al outline default) | `topmodern.html:208`,`:175`,`:232`,`:390` | Dot → `var(--ok)`; `a/button:focus-visible` con anillo accent |
| gimnasio / indumentaria / impacto | — | Sin documento HTML: superficie = vistas Vue + pieles (sección B) | `frontend/src/assets/store-{gimnasio,indumentaria,impacto}.css` | Ver sección B |
| fotos | baja | Wireframe boceto (no es patrón): sin rm, sin focus, grises deliberados. Archivo huérfano en `sources/` — `load_source` nunca lo pide | `fotos.html` completo | Candidato a borrado (track Z) o mover a `bocetos/` |

### B. Pieles Vue (`frontend/src/assets/store-<tpl>.css` y compartidas)

| Patrón/hoja | Severidad | Defecto | Archivo:línea | Fix propuesto |
|-------------|-----------|---------|---------------|----------------|
| page (compartida) | media | 33 transitions no compuestas (`width` `:168`, `box-shadow` ×8, `height` `:472`, `filter` ×4) + 13 keyframes no compuestos (`sp-shimmer`, `sp-aurora`, `sp-pulse`, `sp-badge-glow`, `sp-ava-pulse`, `sp-shop-chip-bob` `margin-top`, etc.); **rm blanket `.store-page *` `:430` los cubre**; `content-visibility` solo en `:455`; 123 `:hover` sin `@media (hover)` | `store-page.css:430`,`:492`,`:693`,`:813`,`:1876`,`:455` | Props no compuestas repintan en hover/focus aun con rm; priorizar `box-shadow`→`transform` en cards |
| catalog | media | 12 transitions no compuestas (`width` `:53`, `filter` `:54`,`:256`,`:296`, `box-shadow` ×6, `padding` `:284`, `background-size` `:302`); keyframes `cv-shimmer`/`cv-pe-drift` `background-position`; **rm blanket `.cv *` `:57` lo cubre** | `store-catalog.css:53-415`,`:57` | Ídem |
| catalog-polish | baja | `transition: box-shadow`+`filter` (`:16`,`:19`) — la hoja existe justo para hovers de card | `store-catalog-polish.css:16`,`:19` | Aceptable como hover-only o mover a `transform` |
| catalog-responsive | — | solo layout/responsive, sin animación — no requiere rm | `store-catalog-responsive.css` | Sano |
| motion | media | 5 keyframes no compuestos: `mo-pulse-ring`/`mo-glow`/`mo-halo` `box-shadow`, `mo-drift`/`mo-shimmer` `background-position`; 23 usos `infinite`; transitions `filter` (`:235`), `padding-left` (`:271`); gated por `no-preference` (`:97`,`:363`,`:483`) + rm `:536` | `store-motion.css` (buscar `@keyframes mo-glow`),`:235` | Ídem box-shadow→transform |
| services | media | 8 transitions `box-shadow`/`filter` (`:110`,`:198`,`:209`,`:274`,`:811`,`:890`,`:923`,`:966`); `sv-ping` `box-shadow` keyframe; `sv-bob` infinite (cubierto por blanket de store-page) | `store-services.css:110`,`:198`, keyframes `sv-ping` | Ídem |
| services-base | baja | 1 transition `box-shadow` (`:190`); rm `:958` | `store-services-base.css:190` | Ídem |
| style-menus | media | **`backdrop-filter` en `.sp-top` (sticky) para estilo `vidrio-nocturno`** (`:43`) — viola §5 en la barra fija de TODAS las tiendas con ese estilo; 187 hex = paleta por estilo (aceptable); 30 hovers sin hover-media | `store-style-menus.css:40-44` | Quitar `backdrop-filter` o fondo `color-mix` ~92% |
| style-motion | baja | 8 hovers sin hover-media; rm blanket propio | `store-style-motion.css` | Sano |
| tpl-card | baja | `transition:filter` (`:305`); `tpc-sk-pulse` infinite (cubierto por rm `:346`); 5 bloques `@media(hover)` — ejemplar | `store-tpl-card.css:305`,`:346` | Ídem filter |
| gimnasio | media | `gy-pulse` anima `box-shadow` (infinito, `:2231`, aplicado `.gy-live-dot` `:527` — cubierto por rm `:2357`); 6 transitions no compuestas: `left` ×2 (`:208`,`:595`), `filter` ×4 (`:639`,`:991`,`:1589`,`:1670`); 12 hex en bloques de piel oscuros (`:669`,`:2043-2222`) | `store-gimnasio.css:2231`,`:208`,`:639` | `left` de indicador → `transform:translateX`; `filter` hover → `opacity`/`transform` |
| indumentaria | baja | 23 hex en bloques `.in-skin`/variantes (`:861-915+`) — paleta de piel, aceptable; 21 `:hover` sin `@media (hover)`; transitions limpias; rm blanket `:1155` | `store-indumentaria.css:861`,`:1155` | Gate hover opcional |
| impacto | baja | 5 transitions no compuestas: `padding` (`:563`), `filter` ×3 (`:827`,`:1041`,`:1891`), `box-shadow` (`:917`); error colors `#B3261E`/`#FF8A7A` ×2 (`:2180-2181`,`:2462-2463`); rm `:2837` | `store-impacto.css:563`,`:827`,`:2180` | `filter` → `transform`; error → token |
| mercado (piel) | baja | 2 transitions `box-shadow` (`:376`,`:530`); sin `@media (hover)` (31 hovers) | `store-mercado.css:376`,`:530` | Ídem |
| moderntec (piel) | media | `mt-shift` anima `background-position`, `mt-pulse` anima `box-shadow` (keyframes); transitions `filter` (`:809`), `box-shadow` (`:941`); rm `:1485` | `store-moderntec.css` (buscar `@keyframes mt-pulse`),`:809` | Ídem |
| movimiento | baja | `mv-pulse` `box-shadow` keyframe; `transition:padding` (`:797`); rm `:1800` | `store-movimiento.css:797` | Ídem |
| raiz | media | 6 transitions no compuestas: `box-shadow` ×4 (`:547`,`:619`,`:657`,`:1199`), `height` (`:628` — acordeón), `transition-property` con `box-shadow`+`filter` (`:1232`); rm `:1360` | `store-raiz.css:628`,`:1232`,`:547` | `height` → `grid-template-rows`/`transform`; limpiar transition-property |
| raiz-catalog | baja | `transition:width` (`:394` — probablemente barra de scroll); `rz-cat-skel` `background-position` keyframe | `store-raiz-catalog.css:394` | `width` → `transform:scaleX` |
| raiz-home | baja | limpio en transiciones; rm `:1265` cubre marquee; 17 hovers sin hover-media | `store-raiz-home.css:1265` | Gate hover opcional |
| sastreria (piel) | baja | 0 transitions no compuestas; rm blanket `:768`; 28 hex en bloques de variante de estilo (paleta propia) | `store-sastreria.css:436-625`,`:768` | Sano; hex = paleta de piel |
| index.js (templates) | — | registro puro de definiciones; `ruta` reusa `raiz` correctamente; sin hallazgos | `frontend/src/templates/index.js` | Sano |

### C. Hallazgos sistémicos transversales

| # | Defecto | Severidad | Evidencia | Fix |
|---|---------|-----------|-----------|-----|
| X1 | **`@media (hover)` casi ausente en skins y documentos**: 11 de 20 documentos y ~10 hojas `store-*.css` tienen reglas `:hover` (algunas 30–120) sin gate `hover:hover`/`hover:none` → estados pegados tras tap en táctil (§2). Documentos sin: `brigada`, `calzado`, `expediente`, `guardia`, `mercado`, `neon`, `ruta`, `sastreria`, `showroom`, `topmodern`, `moderntec`. CSS sin: `store-page.css` (123 hovers), `store-raiz.css` (50), `store-mercado.css` (31), `store-style-menus.css` (30), `store-moderntec.css` (24), `store-indumentaria.css` (21), `store-raiz-catalog.css` (18), `store-raiz-home.css` (17), `store-sastreria.css` (16), `store-services-base.css` (15), `store-style-motion.css` (8) | media | líneas citadas | Envolver hovers decorativos en `@media (hover:hover)` o neutralizar `:hover` bajo `(hover:none)` por archivo |
| X2 | **`box-shadow`/`filter`/`padding`/`width`/`height`/`top`/`left`/`background-position`/`clip-path`/`stroke-dashoffset` animados por transition o keyframes** — violación sistémica de §2 "solo transform/opacity". Peor en keyframes **infinos** (repaint perpetuo): `bz-pulse`, `pulse` (olivium/viajero/topmodern), `sunPulse`, `eybPulse`×2, `btnBreath`, `livePulse`, `gy-pulse`, `mt-pulse`, `mv-pulse`, `mo-glow`, `mo-halo`, `mo-pulse-ring`, `sp-pulse`, `sp-badge-glow`, `sp-ava-pulse`, `sv-ping`, `tpc-sk-pulse`, `cv-shimmer`, `cv-pe-drift`, `mt-shift`, `rz-cat-skel`, `sheen`, `gridPan`, `footline`, `ds-drop`, `drift` | media | ver filas por archivo | Migrar a `transform`/`opacity` sobre pseudo-elementos; los `stroke-dashoffset` de rutas → trazo estático con `opacity` |
| X3 | **`backdrop-filter` en barras fijas/sticky** — recompone cada frame durante el scroll (§5): docs `neon` (`:168`,`:190`,`:812`), `ruta` (`:114`,`:707`), `sastreria` (`:60`+`:340`), `silicio` (`:194`, además anima `backdrop-filter`), `olivium` (`:259`), `atelier-noir` (`:131`), `moderntec` (`:60`); CSS `store-style-menus.css:43` (`.sp-top` sticky → todas las tiendas con estilo `vidrio-nocturno`) | media | líneas citadas | `background: color-mix(in srgb, var(--bg) 92%, transparent)` sin blur; blur solo en overlays que no siguen al scroll |
| X4 | **Contraste AA < 4.5 en texto real** (calculado, anexo §4): fallas → `showroom` muted 3.45/3.14, `expediente` muted 3.55/3.92, `atelier-noir` muted 3.43/3.05, `viajero` on-accent/acento 3.88 (tema claro); bordes 4.30–4.49 → `olivium` 4.30, `moda` 4.33, `modista` 4.34, `aurum-dia` muted 4.43, `guardia` on-accent 4.43, `calzado-noche` acc-ink 4.44 | alta/media | anexo §4 | Oscurecer `--muted`/ajustar acento por tema; valores sugeridos en cada fila |
| X5 | **Hardcodes de color fuera de tokens** en reglas de componente (no en definiciones `--*:` ni fallbacks `var()`): clusters en docs `mercado` `:777-781`, `guardia` `:111-813`, `silicio` `:1516-1603`, `showroom` `:124-332`, `calzado` `:226-905`, `aurum` `:388-1166`, `olivium` `:187-1016`, `viajero` `:156-1074`, `esencial` `:397-931`, `moderntec` `:107-162`, `topmodern` `:175-209`; en CSS: `store-page.css` (~73 hits, mayoría `#fff` on-accent), `store-catalog.css` (32), `store-sastreria.css` (28), `store-indumentaria.css` (23), `store-movimiento.css` (13), `store-gimnasio.css` (12), `store-impacto.css` (4), `store-mercado.css` (2). Exentos: hex dentro de bloques `--*:` (tokens/skins) y fallbacks `var()` — son la paleta propia del diseño | baja/media | líneas citadas | `#fff`/`#111` on-accent → `--on-accent`/`--accent-ink`; grises de sección → `color-mix` con tokens |
| X6 | **`focus-visible`/indicador de foco incompleto**: `moderntec.html` sin ningún estilo de foco; `showroom`/`topmodern`/`neon` solo inputs (links/botones caen al outline default del browser — visible pero no diseñado); inputs con `outline:0` + border sutil | baja | `moderntec.html` (sin `:focus`), `showroom.html:85`,`:322`,`:356`, `topmodern.html:390-518`, `neon.html:578-770` | Regla global `a:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:3px}` por documento (patrón ya usado en `portico:90`, `sastreria:473`, `store-page.css:52`) |
| X7 | **`prefers-reduced-motion` ausente** en `moderntec.html` (doc completo animado: `spin` infinito `:113`) y `fotos.html`; `store-catalog-responsive.css` sin bloque (no anima — OK) | media/baja | `moderntec.html` (0 ocurrencias), `fotos.html` | Bloque `@media (prefers-reduced-motion:reduce){*{animation:none;transition:none}}` |
| X8 | **Google Fonts `<link>` muerto por CSP** — solo `moderntec.html:7-8`; los otros 19 docs usan `@font-face` a `fonts.gstatic.com` correctamente (`pattern_document.py:48-58`: `style-src 'unsafe-inline'` no admite hojas externas) | alta (para ese doc) | `moderntec.html:7-8` | `@font-face` gstatic como el resto, o quitar los links |
| X9 | **Dingbats como iconos/separadores** (`✦`, `✂`, `✓`): uso decorativo borderline §6 "emojis como iconos" — `✦` separador en ribbons/tickers de ~10 docs, `✂` como icono de estado vacío en `sastreria` (`:145`,`:218`), `✓`/`✦` en `store-services.css:169`,`:228`,`:587` | baja | líneas citadas | Aceptable como ornamento tipográfico; `✂` de empty-state → SVG inline del set del diseño |
| X10 | **`content-visibility` casi ausente** en documentos (solo `aurum`, `esencial`, `topmodern`) — §3 lo pide en secciones para saltar render | baja | grep `content-visibility` en sources | `content-visibility:auto` + `contain-intrinsic-size` en `section`/`[data-surface]` |
| X11 | **`transition` de propiedades no compuestas en hover es sistémico pero de bajo impacto** (una repaint por hover, no por frame): concentrado en `box-shadow` de tarjetas/botones | baja | ver X2 | No bloqueante; cubrir con el gate visual de B |
| X12 | **JS sano**: scroll listeners todos `{passive:true}` + rAF-throttle; sin `fetch`/`script src` externos; rAF loops son one-shot/count-up con `prefers-reduced-motion` respetado (`atelier-noir:1431`); 0 `cancelAnimationFrame` necesario (no hay loops perpetuos) | — | grep en sources | Sano — no tocar |

---

## 2. Top 10 fixes de mayor impacto y riesgo bajo (ordenados)

| # | Fix | Archivo:línea | Impacto | Riesgo |
|---|-----|---------------|---------|--------|
| 1 | Oscurecer `--muted` del tema claro de `showroom` a ≥`#767676` | `sources/showroom.html:31` | Alto (AA en 45 usos de texto real) | Bajo — solo token fallback; `--ds-muted` del host sigue ganando |
| 2 | Subir `--muted` claro de `expediente` a ≥`#6B6250` | `sources/expediente.html:45` | Alto (AA en descripciones/notas) | Bajo |
| 3 | Subir `--muted` claro de `atelier-noir` a ≥`#7A6E5C` | `sources/atelier-noir.html:34` | Alto (AA en leads/misiones) | Bajo |
| 4 | CTA de `viajero` claro: fondo `--accent-deep` o ink oscuro sobre `#E0522B` | `sources/viajero.html:50-52` | Alto (3.88 → ≥4.5 en botón primario) | Bajo |
| 5 | Reemplazar `<link>` Google Fonts por `@font-face` gstatic (o quitar) | `sources/moderntec.html:7-8` | Alto (la tipografía del doc nunca carga) | Bajo — copiable de cualquier otro source |
| 6 | Quitar `backdrop-filter` de `.sp-top` en estilo `vidrio-nocturno` → `color-mix` 92% | `store-style-menus.css:40-44` | Medio-alto (todas las tiendas con ese estilo, cada frame de scroll) | Bajo — un declaration block |
| 7 | Scroll search dark de `mercado` a tokens (`--soft/--ink/--muted`) | `sources/mercado.html:777-781` | Medio (hardcodes visibles en dark) | Bajo |
| 8 | Bloque `prefers-reduced-motion` global en `moderntec.html` | `sources/moderntec.html` (agregar antes de `</style>` ~`:195`) | Medio (doc animado sin salida) | Bajo — copiar bloque de `sastreria.html:469` |
| 9 | Focus ring global en `showroom`/`topmodern`/`neon`: `a:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:3px}` | `showroom.html` (~`:60`), `topmodern.html` (~`:60`), `neon.html` (~`:60`) | Medio (accesibilidad teclado) | Bajo — una regla por doc, patrón ya existente |
| 10 | `backdrop-filter` → fondo translúcido en barras fijas de `neon`/`ruta`/`sastreria`/`silicio`/`olivium`/`atelier-noir` | líneas en X3 | Medio (jank de scroll en móvil) | Bajo-medio — un `background` por barra, sin tocar layout |

Bonus (mayor impacto, riesgo medio — para ola 3): migrar los keyframes
`box-shadow` infinitos (`bz-pulse`, `pulse`×3, `sunPulse`, `eybPulse`×2,
`btnBreath`, `livePulse`, `gy-pulse`, `mt-pulse`, `mv-pulse`, `mo-glow`,
`mo-halo`, `mo-pulse-ring`, `sp-pulse`, `sp-badge-glow`, `sp-ava-pulse`,
`sv-ping`, `tpc-sk-pulse`) a `transform`/`opacity` — son repaint perpetuo en
páginas reales.

---

## 3. Patrones que están bien (no tocar)

| Patrón/hoja | Por qué está sano |
|-------------|-------------------|
| `store-indumentaria.css` | 0 transitions no compuestas; rm blanket `:1155`; hex = paleta de piel |
| `store-sastreria.css` | 0 transitions no compuestas; rm blanket `:768`; hex = variantes de estilo |
| `store-raiz-home.css` | 0 transitions no compuestas; rm `:1265` bien scopeado; tokens `--rz-*` |
| `store-catalog-responsive.css` | solo layout; sin animación que apagar |
| `store-style-motion.css` | rm blanket; capa decorativa gated |
| `frontend/src/templates/index.js` | registro declarativo puro; fallback `raiz` correcto; `ruta` reusa surfaces bien |
| `store-page.css` (en lo estructural) | tokens `--st-*`/`--sp-*` con fallback, `focus-visible` global `:52`, rm blanket `:430`, `content-visibility` `:455`, aspect-ratio + object-fit en cards (`store-tpl-card.css:49,59`) |
| `portico.html`, `sastreria.html` (en foco) | `:focus-visible` global con anillo accent (`portico:90`, `sastreria:473`) — patrón a copiar |
| `esencial.html` (en header) | comentario explícito evitando `backdrop-filter` en barra fija `:187` — criterio correcto |
| `aurum.html` (en estados) | 4 `@media(hover)`, 5 rm, 2 focus-visible, `content-visibility` ×3 — el más completo del set |
| `silicio.html` (en rm) | 6 bloques `prefers-reduced-motion`, 3 `focus-visible`, 50 `@media` — cobertura ejemplar (sus defectos son otros) |
| `mercado.html` (en foco) | 5 `focus-visible` — el doc con mejor cobertura de foco |
| `calzado.html` (en estructura) | aspect-ratio/object-fit completos, breakpoints densos (32 `@media`), `animation-timeline` ×3 |
| JS de los 20 docs | listeners `passive:true`, rAF-throttle, `matchMedia('(prefers-reduced-motion)')` respetado, 0 `fetch`/`script src` externo, 0 emojis pictográficos (solo dingbats) |

---

## 4. Anexo — contraste calculado (WCAG 2.x, sRGB)

Método: tokens `--bg/--paper`, `--surface/--card/--panel`, `--ink/--text`,
`--ink-2`, `--muted/--mut`, `--accent`, `--accent-ink/--on-accent`,
`--accent-text` resueltos por scope (`:root` = tema claro salvo que se
indique; `html[data-ds-theme="dark"]` = oscuro; `aurum`/`guardia`/`showroom`
usan `:root` claro + bloque dark; `calzado`/`ruta`/`topmodern`/`silicio`/
`expediente`/`moda`/`modista`/`olivium`/`portico`/`viajero`/`esencial`/
`atelier-noir`/`brigada`/`mercado` tienen `:root` claro + bloque dark).
`color-mix` resuelto por interpolación sRGB; `var(--ds-*,fallback)` usa el
fallback del documento. Pares con ratio < 4.5 marcados.

### Pares que FALLAN AA (texto normal < 4.5)

| Patrón | Tema | Par | Ratio | Tokens (archivo:línea aprox.) |
|--------|------|-----|-------|------------------------------|
| showroom | claro | muted / bg `#FFFFFF` | **3.45** | `showroom.html:31` (`--muted:#8A8A8A`), `:26` (`--bg`) |
| showroom | claro | muted / surface `#F4F4F4` | **3.14** | `showroom.html:31`,`:27` |
| expediente | claro | muted / paper `#E9E1CB` | **3.55** | `expediente.html:45` (`--muted:#7D7460`),`:40` |
| expediente | claro | muted / surface `#F2ECDC` | **3.92** | `expediente.html:45` |
| atelier-noir | claro | muted / paper `#F4EFE6` | **3.43** | `atelier-noir.html:34` (`--muted:#8A7F70`) |
| atelier-noir | claro | muted / surface `#EAE2D3` | **3.05** | `atelier-noir.html:34` |
| viajero | claro | on-accent `#FFF` / accent `#E0522B` | **3.88** | `viajero.html:52` (`--on-accent`),`:50` (`--accent`) |
| aurum (día) | claro | muted `#776E5B` / bg `#F5F0E3` | **4.43** | bloque light `aurum.html:48-61` |
| guardia | claro | on-accent `#FFF7F2` / accent `#D63A17` | **4.43** | `guardia.html:63`,`:61` (tokens light `:50-65`) |
| calzado (noche) | oscuro | accent-ink `#121212` / accent `#E33A4E` | **4.44** | `calzado.html:59-66` |
| olivium | claro | muted / paper `#F3EFDF` | **4.30** | `olivium.html:78` (`--muted`),`:73` |
| moda | claro | muted / surface | **4.33** | `moda.html:61` (token), surface `:58` |
| modista | claro | muted / surface | **4.34** | `modista.html:76` (token), surface `:72` |

### Pares en el límite (4.5–4.6, revisar si el texto es normal)

| Patrón | Par | Ratio |
|--------|-----|-------|
| aurum día | gold-text / bg `#F5F0E3` | 4.55 |
| brigada | muted / bg (claro) | 4.71 |
| calzado | accent-ink / accent (claro `#E0122B`) | 4.89 |

### Pares verificados OK (muestra representativa)

| Patrón | Par destacado | Ratio |
|--------|---------------|-------|
| atelier-noir | texto/bg oscuro | 16.41 |
| aurum | texto/bg ambos temas | 15.45–17.07 |
| brigada | texto/bg ambos | 15.46–16.00 |
| calzado | muted/bg ambos | 5.32–6.76 |
| esencial | acc-ink/acento ambos | 6.08–8.10 |
| expediente | texto/bg oscuro | 14.44 |
| guardia | texto/bg ambos | 14.53–16.21 |
| moda | texto/bg ambos | 15.73–16.47 |
| modista | texto/bg ambos | 13.84–16.25 |
| neon | texto/bg (oscuro) | 17.75 |
| olivium | texto/bg ambos | 13.01–15.15 |
| portico | texto/bg ambos | 15.36–15.74 |
| ruta | texto/bg ambos | 11.40–13.57 |
| showroom | texto/bg ambos | 17.17–18.88 |
| silicio | texto/bg ambos | 15.81–16.68 |
| topmodern | texto/bg ambos | 15.72–19.80 |
| viajero | texto/bg ambos | 15.44–15.96 |

**Lectura**: todos los temas oscuros pasan AA en texto y muted; las fallas se
concentran en **temas claros** (`--muted` grisáceo sobre papel hueso) y en
**tres acentos cálidos** usados como fondo de CTA (`viajero`, `guardia` claro,
`calzado` noche). Patrón de fix único: `color-mix(in srgb, var(--muted)
72%, var(--ink))` o darkening ~8–12% del token.

---

## 5. Notas para track F

- Los fixes de severidad **alta** aplicables sin riesgo: filas 1–5 del top 10
  (4 tokens `--muted`/`--on-accent` en sources + 1 `@font-face` en
  `moderntec.html`). Los tokens son fallbacks: un `--ds-*` del host sigue
  ganando, así que son retrocompatibles por construcción.
- `store-style-menus.css:43` (backdrop-filter en `.sp-top`) afecta a TODOS
  los templates con estilo `vidrio-nocturno` — es el fix CSS de mayor
  alcance del audit.
- `fotos.html` es archivo huérfano (no patrón): decidir en track Z.
- `moderntec.html` es demo estático sin variables: el seed lo carga como
  `pattern.html` pero `pattern_render` cae a la plantilla Vue por no tener
  `{{variables}}`. Si se quiere un documento real, hay que reescribirlo con
  placeholders; mientras tanto, el fix mínimo es fuentes + rm + foco.
- No se encontró: `fetch`/XHR en patrones, `script src` externo, emojis
  pictográficos, `allow-same-origin`, `unsafe-inline`, scroll listeners sin
  `passive`, ni layouts de 3-cards-genéricas (cada doc tiene estructura
  propia: ficha de expediente, cinta de mercado, dossier de aurum, etc.).

**Archivos escritos por este track**: `docs/audit-design-slop.md` (este).
