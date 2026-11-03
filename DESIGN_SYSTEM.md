# DESIGN_SYSTEM.md — Reglas de diseño y componentes (SaaS DAVENT)

> Destilado de `awesome-design-skills/` (typeui.sh) + el contrato de patrones
> del repo (`rediseño_prompt.md`, `pattern_document.py`). Aplica a los
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
