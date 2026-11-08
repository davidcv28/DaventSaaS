# DESIGN_SYSTEM.md — Reglas de diseño y componentes (SaaS DAVENT)

> Destilado de `awesome-design-skills/` (typeui.sh) + el contrato de patrones
> del repo (`pattern_document.py`). Aplica a los
> documentos de `StoreApp/domains/design/sources/*.html` y a la UI del panel.

## 1. Tokens y fundamentos

- Todo valor visual sale de tokens: `--ds-bg`, `--ds-surface`, `--ds-text`,
  `--ds-muted`, `--ds-border`, `--ds-accent`, `--ds-accent-ink`,
  `--ds-secondary`, `--ds-radius`, `--ds-radius-btn`, `--ds-shadow`. Prohibido
  hardcodear colores fuera de la paleta propia del diseño (fallbacks sí).
- Una sola escala de easing (`--ease:cubic-bezier(.2,.7,.2,1)`) y una familia
  tipográfica display + body por diseño. `text-wrap:balance` en títulos,
  `font-variant-numeric:tabular-nums` en precios y contadores.
- Jerarquía antes que ornamento: eyebrow → titular clamp → lead → CTA.

## 2. Movimiento

- Animar solo `transform`/`opacity` (propiedades compuestas). Prohibido animar
  `box-shadow`, `filter`, `width/height` por frame — usar pseudo-elementos.
- Entradas: fade+translate con stagger por `--d` (0→300ms). Reveals al scroll
  con `animation-timeline:view()` + fallback `IntersectionObserver`.
- Loops: marquesinas con pista duplicada al 50%, `will-change:transform`,
  pausa en `:hover`. Drift/parallax por `animation-timeline:scroll()` gratis.
- `prefers-reduced-motion` apaga todo el movimiento. `@media (hover:none)`
  elimina estados pegados en táctil.

## 3. Imágenes

- `aspect-ratio` fijo + `object-fit:cover` siempre; nunca colapsos de layout.
- Hover: zoom interno (`scale(1.04-1.06)`) dentro de contenedor
  `overflow:hidden`, nunca cambio de tamaño de la tarjeta.
- Estado vacío con motivo propio del diseño (forma/glyph), fondo
  `color-mix(accent 10%, bg)`. `decoding="async"`, `fetchpriority="high"`
  solo en la imagen LCP (hero/portada).
- `content-visibility:auto` + `contain-intrinsic-size` en secciones para
  saltar el render de lo que no está en pantalla.

## 4. Componentes y estados

- Todo interactivo declara: default, hover, focus-visible (anillo de acento
  2px, offset 3px), active (scale .98), disabled/loading (spinner por
  pseudo-elemento), vacío (`:empty{display:none}`).
- Botones: min-height 46px (44+ táctil), filo o brillo que viaja al hover,
  flecha que se desplaza (`translateX`) nunca aparece de golpe.
- Tarjetas: borde `--line`, radio del token, elevación por sombra difusa al
  hover + micro-lift (translateY -4px). Línea de acento superior que se
  despliega (`scaleX`) como firma del sistema.
- Links vacíos (`href=""`) se apagan solos: `pointer-events:none`/`display:none`.

## 5. Rendimiento

- Sin `backdrop-filter` en barras fijas (recompone cada frame): fondo
  `color-mix(bg 96%,transparent)`.
- Sombras grandes solo en `:hover`; sombra estática barata el resto del tiempo.
- Un solo listener de scroll `{passive:true}` con rAF para progreso/estado.
- Sin frameworks ni requests externos dentro del documento del patrón.

## 6. Anti-patrones prohibidos

- Layouts genéricos (misma grilla de 3 cards en todos los diseños).
- Colores sueltos sin token, bordes sin radio del sistema, iconos de
  librerías externas.
- Sombras negras duras, gradientes arcoíris, emojis como iconos.
- `allow-same-origin` en el iframe del documento, `unsafe-inline` en CSP,
  `fetch` nuevo dentro del patrón (todo pasa por el puente `davent:ds-api`).

## 7. QA (por diseño, antes de commit)

- 360/390/768/1024/1360/1920: 0 scroll horizontal, 0 errores de consola.
- Claro y oscuro: contraste AA en texto y estados.
- Estados vacíos: sin huecos (secciones/CTA/filas se apagan con `:has`/`:empty`).
- `prefers-reduced-motion`: página estática y completa.

## 8. ModernTec — lenguaje "instrumento de laboratorio"

Grafito profundo (`#06080c`), grilla técnica enmascarada, reglas de 1px,
telemetría en JetBrains Mono y display Outfit con tracking negativo. El
acento de la tienda es la única señal de color (se aclara un 22% en oscuro
para pasar AA sobre grafito). Composición:

- **Hero**: rail `01 · nombre` + titular con la última palabra en gradiente +
  telemetría (datos reales: productos, años, base) + ficha técnica del
  destacado (foto, specs con línea de puntos guía, medidor). Regla de
  medición al pie como firma.
- **Departamentos** (`MtCategories`): celdas de 1px con índice, miniatura
  cuadrada en escala de grises que se colorea al hover y conteo mono; en
  ≤900px pasan a riel con snap.
- **Sobre nosotros** (`MtAbout`): relato + "registro" (gauge de años y filas
  con datos reales) + misión como nota técnica.
- **Tarjetas**: marco de 1px, filo de acento que aparece al hover, nombre en
  display, precio mono tabular y "Nuevo" en contorno / descuento en acento.

Trampas del sistema que esta piel resuelve explícitamente (no repetirlas):

- `styles.css` define `.mono` como chip del panel → `store-page.css` lo
  resetea; si no, cada etiqueta mono sale como pastilla blanca.
- `store-page.css` pinta `::before/::after` de `.store-page` como orbes con
  `border-radius:50%` → la piel los desarma (`border-radius:0`,
  `animation:none`) o el lienzo se recorta en un disco.
- El tema publicado escribe `--sp-*` **inline** en `.store-page` y fija
  `color`/`background-color` con `[data-st-palette]`/`[data-st-bgrole]`:
  la piel remapea esos tokens y colores en los contenedores hijos y con
  `[data-store-template]` para ganar especificidad.

## 9. Brigada — lenguaje "cuartel / placa de inspección"

Papel hueso, banda de cuartel y franja de riesgo: la identidad sale de la
señalética industrial, no de una grilla de tarjetas. Composición:

- **Franja de riesgo** (`repeating-linear-gradient(-45deg, accent, band)`):
  borde del header, subrayado de titular, tapas del CTA y del pie. Nunca
  detrás de texto.
- **Placa de verificación**: marco duro + sombra sólida, sello circular que
  respira (`@keyframes stamp`), filas `span/b` y código de barras de `i`.
  Es el objeto firma del hero; el resto de la página lo cita en pequeño.
- **Registro**: las secciones se numeran con contador (`counter-increment` en
  `.sec`, `::before` del `.idx`) y cada grilla lleva su propio índice
  (categorías, protocolo, equipo, hitos). Los índices no se escriben a mano.
- **Hitos**: filas de ancho completo (`150px` + texto) con año en display;
  no una línea de tiempo en una columna angosta.
- **Tinta y señal**: `--primary` (rojo) para acción, `--hazard` (acento) para
  señalización, `--band` para superficies institucionales. En noche
  `--frame`/`--hard` se derivan de `--band-ink` y del acento para que los
  marcos y las sombras duras sigan leyéndose sobre negro.
- **Formularios inyectados por el puente** (`.ds-contact-*`, `.ds-rev-*`):
  la piel es responsable de sus clases; sin `grid` en `.ds-contact-row` los
  dos inputs salen desalineados y el captcha se apila mal.

Trampas propias de esta piel:

- `.ds-service` es un grid de 2 columnas: sin `grid-column:2` explícito en
  nombre y descripción, la descripción cae en la columna del número (56px).
- Los filtros del catálogo en modo lista los arma el puente como
  `button.f-cat` (no `.ds-cat`): hay que pintar `.f-cat` o quedan botones
  con el borde del navegador.
- `h2[data-fallback]:empty::before{content:attr(data-fallback)}` es
  obligatorio: los títulos opcionales viajan vacíos y sin la regla queda un
  hueco en el encabezado (y una sección fantasma si además falta el bloque).
- La portada muestra 8 productos (`.sec .grid > :nth-child(n+9)` oculta);
  el catálogo completo vive en su ruta.


## 9. Bazar — lenguaje "feria de barrio, edición moderna"

Vive en dos capas que deben leerse igual: el documento publicado
(`StoreApp/domains/design/sources/mercado.html`, servido como patrón) y la
piel Vue de respaldo (`frontend/src/assets/store-mercado.css`). Paleta del
tema (`--ds-*` / `--st-*`) con caída a amarillo toldo `#FFE600`, tinta
`#2B2B2B`, azul `#2563EB`, verde ahorro `#007A3D` y gris papel `#EDEDE9`.

- **Toldo**: el masthead es fijo (el puente lo ancla al marco real) con
  rayas de lona al 7% de tinta, borde inferior dentado y buscador blanco.
  El `padding-top` del body se **mide** con JS, nunca se estima.
- **Ticket**: precios, índices, conteos y etiquetas usan
  `--mono` (`ui-monospace`) con `tabular-nums`; los títulos usan Inter con
  tracking `-.04em`. Es la firma tipográfica del diseño.
- **Sticker**: descuentos y sellos son etiquetas rotadas 3–9°, con sombra
  corta y borde punteado. Nunca un badge plano.
- **Feria**: categorías y beneficios son celdas numeradas (`01`, `02`…) con
  contador CSS; el número se reserva aunque el dato falte para no romper la
  grilla. Los productos llevan índice en la esquina, filo amarillo→azul que
  se despliega al hover y sticker de ahorro anclado a la tarjeta.
- **Movimiento**: entrada del hero con stagger (solo `transform/opacity`),
  cinta de marca en loop de 30 s con pausa al hover, sello flotante,
  brillo del CTA al hover. **Sin reveals por scroll**: el iframe se estira
  al alto del documento y el `IntersectionObserver` dispararía todo al
  cargar. `prefers-reduced-motion` apaga todo.
- **Estados**: sin foto = marco punteado + glifo + rayas diagonales; sin
  filtros = chips ocultos; sin resultados = panel punteado con glifo.
- **Móvil**: grilla de 2 columnas (no una), tab bar inferior con
  `data-ds-pin="bottom"`, hoja "Más" y chips de filtros visibles al
  aplicar. El catálogo conserva filas densas y el toggle lista/grilla se
  oculta.
- **Noche**: el toldo conserva el acento; kicker, sello y "Destacado"
  pasan a acento pleno con tinta oscura. La cinta y el pie tienen fondo
  propio (`--ribbon-bg`, `--footer-bg`) para no invertirse.
- **Chips de filtros**: opt-in por `[data-ds-chips]` en el documento y
  `.mc-cat-chips` en Vue. Cada chip quita su filtro; con dos o más aparece
  "Limpiar todo". Nunca dejar un filtro aplicado invisible en móvil.


## 10. Indumentaria — lenguaje "lookbook / runway" (`indumentaria`, plus)

Destilado de `awesome-design-skills/skills/{editorial,terracotta,dramatic}` +
convenciones `store-sastreria.css`/`store-moderntec.css`. Aplica a
`views/store/indumentaria/`, `components/store/blocks/indumentaria/` y
`assets/store-indumentaria.css` (tokens `--in-*` + puente `--sp-*`, como
`--ss-*`/`--mt-*`).

- **Editorial (skill `editorial`)**: grilla estructurada con índices,
  serif display para titulares, jerarquía eyebrow→titular→lead→CTA,
  nunca una grilla de cards idénticas. Se traduce a: rail lateral
  "COLECCIÓN / 01", numeración LOOK 01/02… en grillas, titular con palabra
  destacada en itálica/acento.
- **Neutros tela (skill `terracotta`)**: una sola superficie cálida
  (crudo `#F4F0EA`-ish), tinta carbón, un único acento de temporada
  fuerte — nunca dos acentos peleando. `indumentaria-noche` invierte a
  carbón/negro runway (skill `dramatic`: contraste teatral, hero
  inmersivo); `indumentaria-street` mantiene tinta pero sube el acento
  (naranja/rojo señal) con radios 0 y bordes duros.
- **Tipografía**: display serif/sans fashion (`fraunces`/`dm-serif-display`
  o sans geométrica para street) + sans limpia de cuerpo + mono para
  etiquetas, talles, precios y fichas (`jetbrains-mono`,
  `tabular-nums`). Escala `editorial`.
- **Motivos propios del rubro** (firma, no ornamento genérico):
  hilván/costura (`border-top:1px dashed`, puntadas `repeating-linear`),
  etiqueta colgante (badge rotado con piquete, nunca pill plano),
  cinta/marquee de temporada ("Nueva temporada · Envíos · Sale"),
  tickets de precio en mono, trama de tejido sutil (2 líneas cruzadas a
  <6% de tinta) como textura de fondo.
- **Catálogo**: card con imagen dominante `aspect-ratio 3/4`, hover con
  zoom interno `scale(1.04)` o reveal de segunda foto, badge "NUEVO"/
  "SALE" como etiqueta, precio mono. Chips de categoría con subrayado
  animado (`scaleX`), igual que `.mc-cat-chips`.
- **Motion**: marquee infinito con pista duplicada (pausa en hover),
  reveal on-scroll con stagger (`v-reveal`, doble rAF ya resuelto por
  la directiva), parallax leve en hero, parpadeo sutil de etiquetas.
  Solo `transform`/`opacity`; `prefers-reduced-motion` lo apaga todo.
- **Móvil por estilo** (`data-style`/`data-ds-style`, como sastreria):
  `indumentaria` → tab bar inferior + hoja; `indumentaria-noche` →
  píldora flotante; `indumentaria-street` → hamburguesa + drawer.
- **Registro**: template `indumentaria` (12 chars, límite del campo),
  tier `plus`, `TEMPLATE_PLUS`, `TEMPLATE_CHOICES`, `STORE_TEMPLATES`
  (rubro `indumentaria`), `STORE_TEMPLATE_SKIN` → `indumentaria`,
  `TEMPLATE_CSS` → `store-indumentaria.css`, loaders en `_shared.js`,
  def en `templates/indumentaria/index.js`. Sacar `'indumentaria':
  'sastreria'` de ambos `*_RETIRED_MAP` (backend `models.py` +
  `stores.api.js`) — el id pasa a ser diseño real.
- **Iconos**: `AppIcon` (el set del repo), nunca librerías nuevas.


## 11. Gimnasio — lenguaje "sala de fuerza" (`gimnasio`, plus)

Aplica a `views/store/gimnasio/` (`GyHero`, `GyStats`, `GyPlans`, `GyTeam`,
`GyFeatured`), `assets/store-gimnasio.css` y a la página genérica
`PlanesView` cuando la piel activa es `gimnasio`.

- **Paleta**: tinta oliva `#0A0B08`, panel `#10120D`, tarjeta `#151711`,
  hueso `#F4F1E8` y el acento del dueño como única señal. En noche el acento
  se mezcla `78%` con hueso (`color-mix`) para que los presets oscuros (lima
  `#65a30d` del plan Estándar, índigo, violeta) lean AA sobre tinta. En día
  se usa `--sp-band-c1` (tono de banda del acento) con texto blanco: un
  acento claro como `#C8F169` no desaparece sobre papel.
- **Tipografía**: Barlow Condensed 800 en titulares (uppercase, `line-height
  .86–.96`), Inter en cuerpo y JetBrains Mono en datos (índices, horarios,
  precios, cifras). `text-wrap:balance`, `tabular-nums` en precios/cifras.
- **Portada**: rail `01 · CENTRO DE ENTRENAMIENTO` + chip de estado en vivo,
  titular gigante con la última frase en acento y subrayado sesgado, ficha
  de imagen con esquina cortada, código `GY/26`, texto vertical, línea de
  escaneo, panel de horarios reales y sello circular giratorio. Sin foto, la
  placa se resuelve con monograma, medidor de barras y "Sala principal".
  Debajo: ficha de datos derivados (años, disciplinas, membresías, sede) y
  cinta de disciplinas en loop.
- **Secciones firma**: `GyStats` (cifras con count-up al entrar en viewport,
  barra proporcional al valor real), `GyPlans` (tarjetas de precio, la
  central en placa lima, CTA por WhatsApp/contacto), `GyTeam` (fichas de
  coach con iniciales en contorno y rol), `GyFeatured` (tarjetas de pista
  con imagen, índice, precio y oferta). Galería en bento 4 columnas
  (primera 2×2, cuarta 2×1), FAQ numerada con `+`/`−`, CTA en banda de
  señal con franjas de riesgo.
- **Movimiento**: cinta con pista duplicada al 50% (pausa al hover), sello
  girando 34 s, scan de la placa, barras del medidor, count-up y micro-lift
  de tarjetas. Solo `transform`/`opacity`; `prefers-reduced-motion` apaga
  todo y `hover:none` elimina los lifts en táctil.
- **Responsive**: ≤960 la portada apila, planes 1 columna (destacado
  primero), stats 2, equipo 2 y FAQ 1; ≤620 todo a 1 columna, CTAs full
  width, anuncios como cinta de una línea y el CTA "Catálogo" del header se
  apaga (vive en la tab bar). En catálogo (≥1101) el buscador va en una
  segunda fila del header: el nombre del club no compite con siete links.
- **Trampas resueltas**: (1) `*/` dentro de un comentario CSS cierra el
  comentario antes de tiempo y **descarta el bloque de tokens completo** —
  nunca escribir `--sp-*/--rz-*` en un comentario; (2) `StorePublicLayout`
  no aplica el layout ni la paleta del patrón base a los diseños con piel
  propia (`SKIN_TEMPLATES`): les pisaba el hero `centered` y el acento;
  (3) la galería necesita `aspect-ratio:auto` en las celdas para que el
  bento no desborde la sección; (4) el header de catálogo con buscador usa
  grid de dos filas y `--sp-top-h:128px` también en `.scrolled`.
- **Registro**: `fonts: ['barlow-condensed','inter','jetbrains-mono']`,
  `blocks.landing` suma `team`, `TEMPLATE_CSS` → `store-gimnasio.css`,
  tier `plus` (Estándar y Premium). Catálogo/ficha/servicios siguen en Raíz
  bajo `.gy-skin`. Migración del catálogo: `manage.py sync_design_neon
  --slug gimnasio` (upsert del patrón + estilos `gimnasio`/`gimnasio-dia`).

## 12. Movimiento — editorial luminoso de entrenamiento (`movimiento`, advanced)

Aplica a `views/store/movimiento/` (`MvHero`, `MvMarquee`, `MvMethod`,
`MvServices`, `MvPlans`, `MvTeam`, `MvFeatured`), `assets/store-movimiento.css`
y a los subárboles Raíz bajo `.mv-skin` (catálogo, ficha y servicios).

- **Identidad**: editorial LUMINOSO (contraste directo con `gimnasio`,
  que es la sala oscura): papel hueso `#F5F2EA`, tinta casi negra
  `#16150F` y UN acento señal (`#E4572E` base) reservado a CTA y datos.
- **Tipografía**: Bricolage Grotesque 700 en titulares condensados en
  mayúsculas (`line-height .88–.94`), Instrument Sans en cuerpo y
  JetBrains Mono en índices, datos y CTAs. `text-wrap:balance`.
- **Portada**: composición PARTIDA (no la grilla de `GyHero`) — mitad
  titular gigante con la última palabra en acento + chips de disciplinas,
  mitad ficha de imagen con índice `01`, código `MV/26` y medidor de
  datos reales (años, disciplinas, membresías en barras). Debajo corre el
  manifiesto (`about_mission` o la línea editorial) y la marquesina
  tipográfica `MvMarquee` (palabras del rubro, pista ×4 al 50%, pausa al
  hover, `prefers-reduced-motion` la apaga).
- **Secciones firma**: `MvMethod` (timeline → 3 pasos numerados 01/02/03),
  `MvServices` (lista editorial numerada, no cards: índice, icono circular,
  nombre condensado y flecha), `MvPlans` (membresías — precio grande,
  nota de sesiones, bullets, CTA "Elegir" por WhatsApp; destacada con
  borde de acento, en `pista` va en placa llena de acento), `MvTeam`
  (fila editorial con iniciales en contorno) y `MvFeatured` (vitrina
  revista: lead 2×2, índices, badge de ahorro, precio tachado).
- **Menú propio**: header partido en dos filas — `.sp-top-utility` fina
  en mono (ubicación + horarios) sobre la fila principal con marca
  izquierda, links centrados y CTA sólido; en móvil, hamburguesa + menú
  a pantalla completa con índice numerado por CSS counter (ni tab bar
  de `sastreria` ni drawer de `gimnasio`). La fila utilitaria se apaga
  ≤1024px.
- **Estilos** (3, identidad propia): `movimiento` (claro, papel + naranja
  señal), `movimiento-noche` (grafito cálido + acento aclarado, sin
  `filter:invert`) y `movimiento-pista` (azul pista, palabra del titular
  en outline `-webkit-text-stroke`, índices gigantes y plan destacado en
  placa de acento — reglas `[data-style='movimiento-pista']`). El modo
  noche real viaja por `[data-store-theme='dark']` y remapea las
  `--mv-*`; el subárbol `.mv-skin` hereda las mismas vars, así que se
  invierte solo.
- **Trampas resueltas**: (1) el icono `activity` no existe en `AppIcon`
  — fallback `zap`; (2) `mv-media-meter` usa `transform:translateY(100%)`
  para colgar del marco de la ficha — en móvil vuelve a flujo
  (`position:static`); (3) el header de dos filas necesita el div
  `.sp-top-utility` condicional en `StorePublicLayout` (solo
  `pageTemplate==='movimiento'`), el resto es CSS.
- **Registro**: `fonts: ['bricolage-grotesque','instrument-sans','jetbrains-mono']`,
  `blocks.landing` suma `about/services/timeline/plans/team`,
  `surfaces.services`, `TEMPLATE_CSS` → `store-movimiento.css`,
  `SKIN_TEMPLATES`, tier `advanced` (`TEMPLATE_ADVANCED` +
  `has_design_advanced`, Premium), familia `deporte` suma `movimiento`.
  Patrón `movimiento` + 3 estilos en `seed_data.json`; migración
  `stores.0073`; sync: `manage.py sync_design_neon --slug movimiento`.

## 13. Indumentaria ModernImpact — lenguaje "revista suiza de moda" (`impacto`, plus)

Aplica a `views/store/impacto/` (envoltorios de Raíz), a las piezas propias
`components/store/blocks/impacto/` (`ImpHero`, `ImpCategories`, `ImpFeatured`,
`ImpAbout`) y a `assets/store-impacto.css` (tokens `--mi-*` + puente `--sp-*`).
Destilado de `awesome-design-skills/skills/{editorial,dramatic,terracotta}`:
una sola superficie de papel crudo, tinta de imprenta y UN acento de
temporada; display Anton en caja alta, cuerpo Space Grotesk y datos en
JetBrains Mono. Reglas de 2px, retícula visible y numeración de pliego.

- **Pliego de tapa** (`ImpHero`): cabecera marca · temporada · Nº, rail
  vertical de temporada (desktop), kicker con punto vivo, titular con la
  última palabra en acento y raya que se dibuja, cifras reales del catálogo
  (`Piezas / Líneas / Años`), ficha de canales (web, Instagram, showroom,
  horario) y foto de campaña con marcas de corte, sello girado y ficha de la
  pieza destacada (nombre, rubro y precio reales). Cierra con **dos cintas**
  en loop (tinta hacia un lado, acento al revés) y una marca de scroll.
- **Índice de colección** (`ImpCategories`): retícula de 3 columnas que
  siempre cierra. Las celdas anchas (`is-wide`, span 2) se calculan para que
  las unidades sumen múltiplos de 3; su media usa `16/10` para igualar el
  alto de la celda `4/5`. "Ver todo" es una banda a todo el ancho, no una
  celda suelta. Etiqueta "Ver línea" sobre la foto y flecha **en flujo**
  dentro del pie (la versión absoluta se montaba sobre el conteo).
- **Vitrina** (`ImpFeatured`): grilla de 4 celdas con reglas, índice de
  pliego en acento, flags al pie de la foto, rango de precios y marcas en la
  cabecera, y pie `Pliego 04 / 14 · edición`. La tarjeta no se eleva al
  hover: el lift rompía las líneas de la celda.
- **Dossier de marca** (`ImpAbout`): relato con filete de acento, chips de
  líneas, firma de la casa con tijera y "Edición {año}" (nunca "Est."), y
  ficha con años en Anton, filas de puntos guía, horario real, misión como
  letra chica, perforación de archivo y código de barras + `ARCHIVO / año`.
- **Secciones compartidas re-eskínadas**: cifras, garantías numeradas,
  ofertas, galería con índice por contador, testimonios, FAQ con filete de
  acento al abrir, CTA en banda de tinta con "TEMPORADA" en contorno y
  contacto como ficha de showroom (columna no sticky: el mapa la tapaba).
- **Movimiento**: revelado `v-reveal` con stagger, titular por línea,
  cintas con pista duplicada al 50% (pausa al hover), sello flotante con
  anillo punteado girando, punto vivo, marca de scroll y barrido de tinta en
  botones. Solo `transform/opacity`; `prefers-reduced-motion` apaga todo y
  `hover:none` deja visibles las pistas de acción.
- **Contraste**: el acento puro se reserva a superficies y filetes. Para
  texto chico sobre papel existe `--mi-accent-text` (acento mezclado con
  tinta) porque `#FF4B1F` sobre `#EDEBE4` no llega a AA a 9–10px; para
  display (≥24px) `--mi-accent-display` conserva la vibración con 3:1. En
  noche ambas mezclas se aclaran solas contra la tinta clara.
- **Trampas resueltas**: (1) `.mi-skin` es un `.store-page` anidado y **no
  hereda** `data-store-theme`: sin el remapeo oscuro el catálogo, la ficha y
  servicios quedaban en papel claro dentro de la edición noche; (2)
  `store-raiz.css` se inyecta después de esta hoja y empata en
  especificidad — los overrides del sub-árbol usan
  `.store-page.mi-skin[data-template='raiz']`; (3) `input.rz-field` lleva la
  clase en el propio input (no un contenedor), y el `<select>` de orden vive
  sin clase dentro de `.rz-cat-sort`: sin reglas propias el navegador pinta
  fondo blanco con texto claro (ilegible en noche); (4) `store-motion.css`
  aplica `mo-halo` a todo `.sp-btn:not(.ghost)`: en esta piel se apaga
  (la imprenta no brilla); (5) `store-page.css` fija `border-radius` en
  iconos, chips, modales y captcha: se normalizan a 0; (6) con tema
  publicado, `.store-page[data-st-brand]` pinta todo `.sp-btn` con
  `--sp-btn-bg`/`--st-on-primary` desde una regla de especificidad (0,7,0):
  el CTA y los botones del sub-árbol reescriben esos tokens en el propio
  elemento (no pelean con selectores); (7) el reset `[data-template] a`
  (0,2,1) gana a una clase sola: los estados de tinta de celdas-enlace
  (`.mi-dept`, `.mi-dept-all`, `.mi-featured-all`) llevan el prefijo del
  diseño; (8) el motor publica `--st-bg`/`--sp-bg` **inline** y pinta el
  lienzo con `[data-st-bgrole][data-store-template]` (0,3,0): la piel declara
  `background: var(--mi-paper)` con la misma especificidad o los estilos
  claros se quedan con el papel base.
- **Estilos** (4): `impacto` (papel crudo + naranja señal), `impacto-noche`
  (grafito + ácido), `impacto-arena` (lino cálido + cobalto, reglas de 1px y
  sello cuadrado) e `impacto-blanco` (galería + magenta, cinta principal en
  acento y sombra rosada). El sub-árbol `.mi-skin` ya **no redeclara**
  `--mi-*`: hereda la paleta del estilo activo (incluida la noche).
- **Registro**: `tier: 'plus'` (Estándar y superiores), `TEMPLATE_PLUS`,
  `TEMPLATE_CSS` → `store-impacto.css`, `SKIN_TEMPLATES`, `fonts:
  ['anton','space-grotesk','jetbrains-mono']`, patrón `impacto` + estilos
  `impacto`/`impacto-noche`/`impacto-arena`/`impacto-blanco` en
  `seed_data.json`. QA: `/mi-qa` (papel) y `/mi-qa-noche` (grafito); sync del
  catálogo: `manage.py sync_design_neon --slug impacto`.

## 14. Moda — lenguaje "fashion club editorial" (`moda`, plus)

Aplica a `StoreApp/domains/design/sources/moda.html` (patrón `moda`) y a los
estilos `moda` / `moda-noche` de `seed_data.json`. Es un documento de patrón
completo: landing, catálogo, ficha y servicios salen del mismo HTML/CSS/JS.

- **Dirección**: revista de moda de quiosco, no e-commerce genérico. Papel
  hueso (`#F2EDE3`), tinta (`#171410`) y **un solo acento de temporada**
  (`#C93218`; noche `#FF8A3C` sobre grafito `#121110`). DM Serif Display para
  la voz de marca (titulares, wordmark, precios de ficha), Instrument Sans para
  lectura y JetBrains Mono para datos, etiquetas, precios y numeración. El
  acento puro se reserva a display, fondos y filetes; el texto chico usa
  `--accent-text` (acento mezclado con la tinta) y sobre bandas de tinta
  `--accent-on-ink`, para no romper AA con el acento de temporada.
- **Firma visual**: retícula con filetes de 1px, numeración de edición
  `01 / Líneas`…, cinta de anuncios en loop, cinta de categorías, sello
  circular giratorio con el nombre real, cinta vertical "Colección {año}",
  marcas de corte en la portada, fondo de trama de puntos, índice de líneas
  numerado, fichas de producto con badge de ahorro real. Nada de tiles de "Sale hasta 75%" ni marcas inventadas: las
  ofertas salen de `data-off` del descuento vigente y las líneas de
  `{{categories}}`.
- **Secciones**: portada editorial → cinta de líneas → índice → vitrina con
  tabs por categoría real → atelier (años, relato, misión, especialidades,
  cifras) → garantías → membresías → testimonios → FAQ → CTA en
  banda de tinta → contacto con formulario del puente → pie. Cada bloque
  dinámico vive en `data-flag` y se apaga solo si su fragmento viene vacío
  (`data-hide-if-empty`, `:has()`, `.ds-zone`).
- **Catálogo**: masthead "Catálogo {tienda}" con `ARCHIVO` en contorno, buscador
  con sugerencias, riel de filtros (líneas, marcas, precio, ofertas), contador
  del puente, vista grilla/lista y orden. En móvil el riel es hoja lateral
  (`data-ds-filters-panel` + `is-open`); no usar `position:fixed` para nada que
  no sea chrome declarado con `data-ds-pin`.
- **Ficha**: media 1/1 (la imagen de origen es cuadrada), ficha `Nº`, precio
  mono, ficha técnica real, vendedor, opiniones con formulario del puente y
  relacionados. Si no hay opiniones, el estado vacío lo escribe la hoja
  (`.ds-rev-list:empty::before`), nunca un bloque inventado.
- **Movimiento**: entrada de portada por líneas + `clip-path`, revelado por
  scroll alimentado por `davent:ds-frame` (el iframe va estirado y el scroll es
  del host), parallax de portada con puntero, marquesinas con pista duplicada
  al 50% (pausa al hover), sello giratorio, contadores de cifras y barra de
  progreso de lectura. Solo `transform`/`opacity`; `prefers-reduced-motion`
  apaga todo y deja la página completa.
- **Trampas resueltas**: (1) el CSP del documento solo permite
  `style-src 'unsafe-inline'`, así que un `<link>` a Google Fonts se bloquea:
  las familias viajan como `@font-face` desde `fonts.gstatic.com` (`font-src
  https:`); (2) `DesignPattern.render` interpola **solo el HTML**, no el CSS:
  nunca poner `{{variable}}` en una hoja — el monograma del hero es un
  `.hero-ghost` real detrás de la imagen; (3) en oscuro las superficies se
  fijan a la piel noche porque `--ds-bg` conserva la paleta clara publicada
  (el acento sí viaja desde `--ds-accent`); (4) un `.ds-zone` vacío dentro de
  una página hace que el puente oculte el `[data-flag]` completo — no marcar
  `.offerings` como `.ds-zone` o la página Servicios desaparece; (5) el
  `theme_toggle` lo inyecta el puente en `.top-inner`: el orden móvil se
  resuelve con `order` (tema antes que hamburguesa); (6) los enlaces con
  `href=""` se apagan con `a[href=""]{display:none}` para no dejar iconos
  huérfanos cuando la tienda no cargó ese canal.
- **QA**: `http://localhost:5173/moda-qa` (tienda local de prueba; landing,
  catálogo, ficha, servicios y modo noche). Tras editar la fuente:
  `manage.py seed_design_catalog --patterns-only` y
  `manage.py sync_design_neon --slug moda` (el comando arrastra también el
  estilo `moda-noche` por la FK `DesignStyle.pattern`).

## 10. Calzado — lenguaje "vitrina deportiva"

Vive en `StoreApp/domains/design/sources/calzado.html` (patrón `calzado`,
estilos `calzado` y `calzado-noche`). Papel blanco, tinta `#141414`, rojo
señal `#EE2D45` y paneles duros; Montserrat 200/600 para titulares y
etiquetas, Lato para lectura. La identidad sale de la señalética deportiva,
no de una grilla de tarjetas.

- **Dorsales y reglas de pista**: todo se numera con contadores CSS
  (`01`, `02`…) — categorías, servicios, planes, tarjetas, ficha del
  producto. Las secciones se separan con `repeating-linear-gradient` de 1px
  (carriles) y los índices nunca se escriben a mano.
- **Portada**: foto a sangre con kenburns, velo en dos capas (tinta + acento),
  titular fino a la izquierda, CTA doble, sello circular giratorio con datos
  reales (`textPath`) y **marcador al pie** con horarios / showroom / WhatsApp
  (tres datos reales; cada celda se apaga si el dato falta).
- **Collage**: 12 columnas con portada 2×2, panel de relato en acento, panel
  oscuro de showroom y galería. Los paneles sin dato se apagan y el resto se
  recoloca (las reglas de recolocación repiten la condición porque `:has()` ve
  el DOM, no el `display`).
- **Cintas**: tres loops (datos de la tienda bajo la portada, anuncios en el
  pie y wordmark). El script arma dos mitades idénticas y **repite el grupo
  hasta cubrir el ancho** (una sola foto de galería dejaba medio lienzo
  vacío); la duración se calcula a ~42 px/s.
- **Chrome**: header fijo (`data-ds-pin="top"`, `data-ds-offset="76"`) que se
  condensa al scrollear y pinta el progreso de lectura desde
  `davent:ds-frame`; el interruptor de tema lo inyecta el puente en
  `.top-inner` y se estiliza cuadrado.
- **Catálogo**: barra de marca, riel de filtros (buscador con sugerencias
  `[data-ds-suggest]`, categorías en lista `button.f-cat`, marcas con conteo,
  precio con "Aplicar", ofertas), contador, vista lista/grilla y chips.
- **Ficha**: pestañas **reales** (antes eran `span` decorativos) con
  `role="tab"`; el panel de opiniones se apaga si no hay lista ni formulario.
- **Trampas resueltas**: (1) en una celda de alto fijo un hijo con
  `overflow:hidden` se encoge a 0 — el panel lleva `>*{flex:none}`; (2) las
  rejillas de filo dibujan la línea con **cada celda** (`border-right/bottom`
  + `box-shadow` interior en el contenedor): con `gap` + fondo, una última
  fila incompleta dejaba bloques grises; (3) `:empty` no matchea nodos con
  espacios, así que los datos van pegados a la etiqueta
  (`<h2>{{…}}</h2>`) y las uniones de dos variables se separan en spans
  propios; (4) `vh` dentro del iframe estirado equivale al alto del
  documento — la portada usa `clamp()` en px, nunca `vh`; (5) en oscuro los
  botones y paneles salen de `--btn`/`--panel` (el `#111` fijo desaparecía);
  (6) el puente arma `button.f-cat`, `.cat-chip` y `.cat-chip-clear`: hay que
  pintarlos o quedan con el estilo del navegador.
- **QA**: renderizar `render_store_pattern` con una tienda (claro/oscuro,
  1440 y 390) y revisar landing, catálogo lista/grilla y ficha. Tras editar la
  fuente: `manage.py seed_design_catalog --patterns-only` y
  `manage.py sync_design_neon --slug calzado` (arrastra `calzado-noche` por la
  FK `DesignStyle.pattern`).

## 15. Viajero — lenguaje "diario de viaje" (`viajero`, plus)

Vive en `StoreApp/domains/design/sources/viajero.html` (patrón `viajero`,
estilos `viajero` y `viajero-noche`). Papel arena `#F5EFE3`, tinta náutica
`#0D1A22`, coral de señalización `#E0522B` y verde mar `#1C5D57`; Fraunces
(titulares, ejes SOFT/WONK), Instrument Sans (lectura) y JetBrains Mono
(datos). La identidad sale del cuaderno de viaje impreso, no de una grilla
genérica de tarjetas.

- **Portada**: foto a sangre con velo en dos direcciones, riel vertical de
  temporada, ruta punteada animada con plano, pase de abordar con los años de
  ruta (dato real) y **ficha de agencia tipo ticket** (base / atención /
  contacto + reservar) con muescas y marea de papel.
- **Estructura editorial**: cada sección abre con índice `01…` en mono
  (contador CSS), eyebrow, titular clamp y nota con filete. Cinta de destinos
  en banda de tinta, índice numerado de categorías que se invierte al hover,
  itinerarios con tabs reales y número de pliego en la esquina, postal de
  bitácora con sello giratorio, cifras con filetes, garantías numeradas,
  membresías tipo ticket, bitácora de viajeros, FAQ y CTA con marquesina.
- **Movimiento**: marquesinas con pista duplicada (pausa en hover), reveal
  con stagger por `--d`, progreso de lectura desde `davent:ds-frame`, hover
  de tarjeta `translateY(-4px)` + zoom interno de foto, `prefers-reduced-motion`
  apaga todo. Nunca se anima el alto de la portada.
- **Trampas resueltas**: (1) **zoom infinito** — `.head-inner` tomaba su
  mínimo de `--head-h` mientras `syncHead()` medía `head.offsetHeight`: cada
  medición sumaba el padding y la cabecera crecía sin fin dentro del iframe
  estirado; el mínimo ahora es `--head-base` y el token medido solo se
  reescribe si cambió; (2) en oscuro `--band`/`--band-ink` mantienen cintas,
  footer, hojas, tarjetas de tinta y ofertas en grafito con texto claro (usar
  `--ink` como fondo lo invertía a bloque claro); (3) el puente inyecta el
  toggle de tema en `.top-inner`, así que el header expone esa clase y el
  botón se integra al final del chrome; (4) el puente arma `button.f-cat`
  (no `.f-item`): hay que pintar ambos o el riel de filtros sale con el
  estilo del navegador; (5) con tarjetas `.ds-offer` la lista numerada
  repetiría el mismo contenido — se apaga con `:has`; (6) el formulario de
  opiniones (`.ds-rev-*`) lo arma el puente y se viste en la hoja; (7) fuera
  de la portada el header recupera papel (`html:not([data-surface="landing"])`)
  porque el chrome blanco quedaba ilegible sobre la crema.
- **QA**: `http://localhost:5173/viajero-qa` (tienda local, plan premium;
  landing, catálogo, ficha y experiencias, claro/oscuro, 390 y 1280). Tras
  editar la fuente: `manage.py seed_design_catalog` y
  `manage.py sync_design_neon --slug viajero` (arrastra `viajero-noche`).

## 16. Atelier Noir — lenguaje "atelier de costura" (`atelier-noir`, plus)

Vive en `StoreApp/domains/design/sources/atelier-noir.html` (patrón
`atelier-noir`) y en los estilos `atelier-noir`, `atelier-noir-noche`,
`atelier-noir-ocre` y `atelier-noir-oliva`. Es un documento completo:
landing, catálogo, ficha y servicios salen del mismo HTML/CSS/JS.

- **Dirección**: taller de costura editorial, no e-commerce genérico.
  Papel hueso `#F5F0E7`, tinta `#14110E`, superficie `#EBE3D6` y un solo
  acento teja `#B0502F` (noche: grafito `#12100D` + arcilla `#D98A63`).
  Fraunces para la voz de marca, Instrument Sans para lectura y JetBrains
  Mono para índices, precios, etiquetas y datos.
- **Contraste**: `--muted` (`#6E6455`) y `--accent-text` (acento mezclado
  con tinta) son los únicos tonos para texto chico; el acento puro queda
  para display (≥24px), fondos y filetes. Sobre banda de tinta se usa
  `--band-ink`/`--accent-on-ink`. Los estilos claros no bajan de 4.5:1.
- **Firma**: cinta métrica (`repeating-linear-gradient` de 1px) al pie de
  la portada y del footer, hilván punteado en los encabezados de sección,
  fichas `Nº 01`, sello circular giratorio, riel vertical "Colección
  {año}", marcas de corte en la portada, pliegos numerados en el lookbook
  y maniquí de línea como marca de agua del dossier.
- **Portada partida**: columna editorial sobre tinta (índice `01`, kicker
  con punto vivo, titular gigante en Fraunces, filete de acento, tagline
  itálica, datos reales de sede/horario/Instagram) + ficha de portada
  4/5 con esquinas de acento, sello y caption. Sin foto, el monograma
  gigante (`--accent` al 24%) resuelve el marco; nunca queda un hueco.
- **Secciones**: cinta de líneas en banda de tinta → índice numerado que
  se invierte al hover → vitrina de 8 piezas desalineadas (tabs reales) →
  dossier (años en contorno, especialidades, relato, misión, cifras) →
  lookbook en tira oscura con `scroll-snap` y pliegos → garantías
  numeradas → membresías → voces → FAQ con índice → CTA con marquesina
  de contorno y sello → contacto tipo ficha de taller.
- **Catálogo**: masthead de tinta con "ARCHIVO" en contorno, chips de
  datos reales, riel de filtros, buscador con sugerencias, contador,
  vista grilla/lista y orden. En móvil el riel es hoja lateral y la barra
  se reordena en grid (buscador full width; conteo, vista y orden en una
  fila). La ficha mantiene media 1/1 con esquinas, precio mono, ficha
  técnica, vendedor, opiniones del puente y relacionados.
- **Movimiento**: entrada de portada por capas (`rise` + `wipe`), sello y
  anillos girando, parallax de portada con puntero, cintas con pista
  duplicada al 50% (pausa al hover), reveals con stagger por `--d`,
  contadores de cifras y progreso de lectura desde `davent:ds-frame`.
  Solo `transform/opacity`; `prefers-reduced-motion` apaga todo y
  `hover:none` elimina los lifts y la pista de "Ver pieza".
- **Trampas resueltas**: (1) `padding` shorthand en `.hero-grid` pisaba el
  `padding-inline` de `.wrap` y la portada se pegaba al borde — usar
  `padding-block`; (2) el badge de ahorro vive en `.ds-product-price`
  (no en la tarjeta): va inline con `order:-1`, nunca absoluto sobre el
  nombre; (3) el desalineado de la vitrina no depende de
  `data-ds-view-mode` (la landing no lo lleva) y se corta en 8 piezas
  salvo que un tab active `data-filtered`; (4) el toggle de tema lo
  inyecta el puente con `margin-inline-start:auto` — se anula con
  `!important` para que quede junto al CTA; (5) `--head-h` se mide y solo
  se reescribe si cambió (sin lazos); (6) `.ds-zone` vacío apaga el
  `[data-flag]` completo — no marcar `.offerings`; (7) `a[href=""]` se
  apaga para no dejar iconos huérfanos sin canal.
- **QA**: `http://localhost:5173/moda-qa` (tienda local, plan premium:
  landing, catálogo grilla/lista, ficha y servicios; claro/oscuro;
  390/1440). Tras editar la fuente: `manage.py seed_design_catalog` y
  `manage.py sync_design_neon --slug atelier-noir` (arrastra los cuatro
  estilos por la FK `DesignStyle.pattern`).

## 17. Guardia — "consola de seguridad" (`guardia`, plus)

Vive en `StoreApp/domains/design/sources/guardia.html` (patrón `guardia` con
los estilos `guardia` y `guardia-claro`). Grafito `#0C1016`, panel `#151D28`,
tinta `#E8EDF4` y rojo fuego (`--ds-accent`, fallback `#E8481F`); el claro es
la misma consola en concreto (`#E9E7E0` / `#F5F3EC`). Archivo 900 estirada al
112 % en titulares y JetBrains Mono en todos los datos.

- **Firmas**: franjas de riesgo (`repeating-linear-gradient -45°`) bajo el
  hero, en la banda de números y sobre el pie; esquinas marcadas
  (`.framed::before/::after`) en la ficha de portada, la media de la ficha y
  el formulario; registro numerado con contadores CSS (categorías, servicios,
  garantías, FAQ); línea de escaneo que barre el hero; sello con anillo
  punteado girando (el monograma queda quieto); cinta de anuncios y ribbon
  del nombre al pie, ambas con pista duplicada al 50 % y pausa al hover.
- **Navegación**: `header.top` transparente sobre el hero usa tokens propios
  (`--hdr-ink/--hdr-mut` claros) y pasa a `--bg` sólido al scrollear **o** en
  cuanto la superficie no es `landing` (`html:not([data-ds-surface="landing"])`).
  Sin eso, en tema claro la nav quedaba tinta sobre tinta y desaparecía.
  El toggle de tema se monta en `.top-inner` (si no existe, el puente lo
  cuelga del header y flota fuera de la fila); en móvil va antes del burger
  con `order`.
- **Portada**: kicker con punto vivo + Nº de año, titular con el nombre en
  contorno y la tagline en acento (line-clamp 3: la tagline puede caer en la
  descripción completa), y ficha de guardia con filas reales (base, horario,
  canal, catálogo) que se apagan solas cuando el dato falta.
- **Tarjetas**: la imagen **es** `.ds-product-img` (no un contenedor): lleva
  `width:100%`, `aspect-ratio:4/5` y `object-fit:cover` directo. El enlace es
  un grid con áreas `img / cat / copy / stock+price`, así el precio nunca
  pisa el nombre. Etiquetas: sticker de campaña arriba a la izquierda,
  bandera `OFERTA` arriba a la derecha (solo con `:has([data-off])`) y chip
  `−N %` inline con el precio viejo en el pie de la tarjeta.
- **Estados vacíos**: las secciones de la landing se apagan con
  `[data-surface="landing"] section:has(.grid|.clients|.extra-grid|.quotes|
  .faqs|.shots|.service-list|.cats:empty)`; **nunca** aplicar esa regla a la
  página de servicios (se comía el estado vacío y el CTA). En la ficha, el
  bloque de opiniones se apaga sin `.ds-reviews` y los relacionados con
  `.grid:empty`.
- **Formularios del puente**: `.ds-contact-fields` y `.ds-rev-fields` son
  grids; el captcha usa `grid-template-columns:1fr 44px` con la pregunta en
  su propia fila (`grid-column:1/-1`) — con flex la pregunta se aplastaba
  contra el input. Las opiniones usan `.ds-rev-item/.ds-rev-list` (no
  `.ds-rev`), y la lista vacía escribe su estado con `:empty::before`.
- **Trampas resueltas**: (1) `padding` shorthand en `.hero-inner` pisaba el
  `padding-inline` de `.wrap` (usar `padding-block`); (2) el bloque
  responsive apuntaba a `.cat`/`.prod`, clases que no existen — son
  `.ds-cat`/`.ds-product`; (3) `form{display:flex;flex-direction:column}` en
  la hoja rompía el buscador del catálogo (`.cat-search` necesita `row`);
  (4) `.rv` se revela con `davent:ds-frame` comparando contra `-frame.top`
  (el rect del iframe es negativo al scrollear); (5) `public_cache_stamp`
  cachea el documento 120 s en locmem: tras `seed_design_catalog` hay que
  esperar el TTL o reiniciar el server antes de mirar el render.
- **QA**: `http://localhost:5173/qa-tpl-seguridad` (tienda local de seguridad
  con `customization.template='guardia'`; landing, catálogo con
  buscador/filtros, ficha y servicios; claro/oscuro; 390/768/1360).
  Migración: `manage.py seed_design_catalog --patterns-only` y
  `manage.py sync_design_neon --slug guardia` (arrastra `guardia-claro`).

## 18. Silicio — "laboratorio de hardware" (`silicio`, plus)

Vive en `StoreApp/domains/design/sources/silicio.html` (patrón `silicio`,
estilos `silicio` dark y `silicio-claro` light). Grafito `#0A0D12`, volt
`#C8FF3D` como señal y acero `#7FA8E8` secundario; el claro es papel de
plano `#F2F3EE` con acento derivado. Anton (display, solo weight 400) +
Space Grotesk + JetBrains Mono por `@font-face` TTF de gstatic (el CSP
bloquea `<link>` de Google Fonts).

- **Firmas**: sello de instrumento giratorio (`.hero-badge`, SVG con
  `textPath` circular + chip), deck del hero con esquineros de instrumento,
  scanline que barre el slide activo (Ken Burns en el `is-on`), osciloscopio
  `.wave` entre hero y cinta (pista duplicada 1200 px en loop, pausa al
  hover), cinta de categorías `data-marquee` con duplicados `aria-hidden`,
  rieles de productos/testimonios con fades de borde y contador, plano de
  circuito vivo `.pcb-bg` (`<pattern>` + `animateMotion` SMIL), titular
  `.hero-title` partido en `.ht-w` por JS con cursor `::after` parpadeante.
- **Acente por tema**: `--ds-accent` llega único del estilo (volt) — en
  claro se deriva con `color-mix(in srgb,var(--ds-accent) 50%,#14171C)`
  (oliva legible sobre papel) y en oscuro se usa directo; `--on-accent`
  sigue a `--ds-accent-ink`. Sin la mezcla el volt sobre `#F2F3EE` queda
  invisible (~1.1:1).
- **Buscador del catálogo**: el puente genera `.suggest-head/.suggest-item/
  .suggest-thumb/.suggest-copy/.suggest-more/.suggest-empty` dentro de
  `[data-ds-suggest]`; el formulario lleva `[data-ds-search-input]`,
  botón submit y `data-ds-search-clear` (el puente lo busca explícito).
  Las reglas de control del form van con hijo directo (`.cat-search >
  button`) — un `.cat-search button` genérico posiciona los botones de las
  sugerencias y las apila.
- **Grilla del hero**: `grid-template-columns:1fr` equivale a
  `minmax(auto,1fr)` — el mínimo `auto` toma el min-content del ítem más
  ancho (los dots del deck, `flex:none` de 22 px) y estira la columna a
  ~433 px en móvil. Regla: `minmax(0,1fr)` + `.hero-grid>*{min-width:0}`.
- **Reveal**: `.reveal` usa `animation`, no `transition` — una `transition`
  ahí pisa los hovers de `.ds-plan/.ds-offer/.ds-service` y los deja sin
  transición rápida.
- **Servicios**: orden de trabajo propia (`setupServices()` arma ticket
  `.svc-ico/.svc-body/.svc-price/.svc-check` desde `data-price/-label/
  -duration/-icon` que emite `_service_fragment`); la barra `.wo-bar`
  arma total + mensaje WhatsApp lista por líneas. No poner `.ds-zone` en
  `.offerings` (el puente oculta la página entera).
- **Trampas del sistema**: `padding` shorthand pisa `padding-inline` de
  `.wrap`; `scroll-margin-top` en anclas por el header fijo
  `data-ds-pin="top"`; el iframe va estirado → reveal/progreso se alimentan
  de `davent:ds-frame`, no del viewport; los duplicados del marquee van
  `aria-hidden` + fuera del tab order.
- **QA**: tienda local `viajero-qa` con `customization.template='silicio'`
  (documento directo: `/api/stores/public/viajero-qa/pattern/document/
  ?surface={landing,catalog,product,services}&theme={light,dark}`;
  390/768/1360, sugerencias de búsqueda, filtro móvil, orden de trabajo).
  Migración: `manage.py seed_design_catalog --patterns-only` y
  `manage.py sync_design_neon --slug silicio` (arrastra `silicio-claro`).

## 19. Pórtico — "galería editorial, día y noche" (`portico`, plus)

Aplica a `StoreApp/domains/design/sources/portico.html` (documento único:
landing, catálogo, ficha y servicios) y a los estilos `portico` (día) y
`portico-noche` (noche). Piedra caliza, tinta verde-negra y cobre; Italiana
+ Manrope + Spline Sans Mono; retícula de museo con índices 01–13.

- **Portada**: titular palabra por palabra, foto 4/5 con marco desplazado,
  sello giratorio sobre papel, estampa de años, cédula bajo la foto, tres
  miniaturas del carrusel y **ticket** de datos reales (dirección, horarios,
  WhatsApp, sala). La luz de sala sigue al puntero solo con `transform`.
- **Cintas**: anuncios arriba, especialidades del negocio en serif sobre
  tinta (cobre en noche), firmas en marquesina full-bleed, pie en mono y
  palabra gigante detrás del CTA. Todas duplican tramos idénticos hasta
  cubrir el doble del ancho visible; los clones van `aria-hidden`.
- **Secciones firma**: ofrecemos 2×2, cifras con count-up, ficha de la casa,
  garantías en filas, vitrina con la primera pieza destacada, bento de
  galería, trayectoria sobre riel, equipo, opiniones con la primera cita
  grande, membresías, video, FAQ numerada y contacto con formulario.
- **Noche**: `[data-ds-theme="dark"]` fija la paleta oscura del estilo (no
  hereda `--ds-bg` claro) y el acento viaja; cinta y pie cambian de tinta a
  cobre. El toggle del puente no recarga: el tema tiene que leerse solo con
  CSS.
- **Trampas resueltas**: (1) el `SURFACE_CSS` del host pinta `.head > span`
  y su `::before` — el índice necesita `.head > span.head-no` y resetear
  `width/height/background/opacity` del pseudo o el número desaparece;
  (2) `background` shorthand en `.hero-media`/`.ds-product-img` borra el
  degradado del estado vacío del host: usar `background-color`;
  (3) `getComputedStyle(::before).content` devuelve `counter(...)`, no el
  número: el índice de cabecera usa el orden de los `.head-no`;
  (4) `display:contents` en `.hero-copy` (≤900) reordena la portada, pero el
  `gap` del grid separa cada hijo: resetear márgenes; (5) el catálogo sin
  productos muestra un panel `.ds-empty` a ancho completo y oculta el aside
  y la barra con `html:has([data-ds-products] > .ds-empty)`.
- **Navegación**: el chrome (header, hoja móvil, tab bar, pie) lleva
  `data-ds-anchor` y cada acceso de sección suma `data-ds-route="home"`:
  con la sección visible el puente scrollea y, si vive en otra superficie,
  navega al inicio. El `data-ds-offset` del header se re-mide con la
  cabecera real (alto + 12) o los anclajes caen bajo la barra.
- **Registro**: tier `plus` (Estándar) en `seed_data.json` (patrón y ambos
  estilos) y en `STORE_TEMPLATES` de `stores.api.js`; QA con
  `qa-devin-store` (`?theme=dark&surface=…`) + `seed_design_catalog` +
  `sync_design_neon --slug portico`.
