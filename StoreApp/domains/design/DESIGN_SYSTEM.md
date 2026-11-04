# Design System — Patrón `calzado`

Basado en las reglas de `awesome-design-skills` (minimal/editorial/premium):
tokens semánticos antes que valores crudos, estados explícitos, jerarquía
consistente, responsive por defecto, motion reducido respetado, y nada de
contenido inventado — solo datos reales de la tienda.

## Tokens

- **Roles del tema** (`--ds-*` del panel; fallback propio): `--bg`, `--surface`,
  `--ink/--ink-2`, `--muted`, `--line`, `--accent`, `--accent-ink`.
- **Piel propia**: papel `#FFFFFF`, tinta `#1A1A1A`, señal `#EE2D45`,
  noche `#161616/#1E1E1E` + acento al 70%.
- **Tipografía**: Montserrat (display: 200 billboard, 600 secciones, 700
  labels en caja alta espaciada) + Lato (lectura 300/400).
- **Radios**: 0 (diseño cuadrado); `--ds-radius`/`--ds-radius-btn` sobreescriben.
- **Espaciado**: secciones `clamp(46px,7vw,80px)`, grilla 4 col → 2 → 1.

## Componentes

- **Header** transparente sobre el billboard; logo = caja blanca (inicial/foto)
  + caja oscura bordeada (nombre). Iconos 38×38 glass (WhatsApp, catálogo,
  hamburguesa). `a[href=""]` oculto (placeholder vacío = sin elemento).
- **Hero**: foto a sangre completa + Ken Burns 22s, titular thin centrado,
  sub en letter-spacing, iconos sociales circulares, dots con pulse escalonado
  y cue de scroll flotante.
- **Cinta marquee** (`ribbon`): loop 26s con nombre, tagline, localidad y
  horario reales; duplicada para scroll infinito.
- **Mosaico**: grilla 4 col con tile 2×2 + paneles rojo/negro con CTA negra;
  galería (`{{gallery}}`) fluye como tiles. Móvil: 2 col.
- **Cards**: foto 1:1, categoría en acento, nombre caps, precio + `›` negro;
  `-N%` flotante con `data-off`. Hover: borde + sombra suave.
- **Catálogo**: sidebar (búsqueda, precio, categorías, marcas, ofertas) +
  promo (cover + nombre sólido) + barra de orden/vista + chips. En móvil el
  riel se abre como hoja lateral con scrim.
- **Ficha**: galería + 3 thumbs (crops distintos de la misma foto), precio,
  tabs rojos (Descripción/Opiniones/Información), relacionados.
- **Footer**: claro, 4 columnas, base oscura con "volver arriba".

## Reglas

- Solo datos de la tienda: prohibido texto inventado ("40% off", "NEW").
- Sin `<link>` externo: `@font-face` directo (CSP `font-src https:`).
- `prefers-reduced-motion` desactiva loops/transitions; `.reveal` con
  `animation-timeline` + fallback IO.
- Sin inline handlers, sin `javascript:` URLs, `inert` con menú abierto.
- Touch targets ≥ 34px, `:focus-visible` con outline de acento.
