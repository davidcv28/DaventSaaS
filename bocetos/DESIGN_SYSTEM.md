# DESIGN_SYSTEM — Tienda Objeto (boceto neon)

Fuente: `awesome-design-skills/skills/neon` (SKILL.md + DESIGN.md). Migración del
boceto `page-is-the-object` (papel/blueprint) al sistema **Neon**: alto contraste,
glow eléctrico, neón ácido + cian sobre tinta.

## Tokens

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#0A0C10` | fondo de página (tinta) |
| `--bg2` / `--card` | `#0E1218` / `#12161F` | paneles y tarjetas |
| `--line` | `#1F2632` | bordes hairline |
| `--primary` | `#BBF351` | lima ácido — acento principal, CTAs |
| `--secondary` | `#00BCFF` | cian — acento secundario, datos |
| `--ink` | `#F2F5EC` | texto principal |
| `--mut` | `#8B95A7` | texto secundario (≥ AA sobre `--bg`) |
| success/warning/danger | `#16A34A` / `#D97706` / `#DC2626` | solo estados |

## Tipografía

- Display: **STIX Two Text** (serif de alto contraste) — titulares hero/sección.
- Cuerpo: **Roboto** 400/500/700 — párrafos, UI.
- Mono/etiquetas: **Source Code Pro** 400/500 — kickers, precios, tags, captions.
- Escala fluid: display `clamp(3rem,9vw,7rem)`, h2 `clamp(2rem,4vw,3.5rem)`,
  lead `clamp(1.1rem,1.4vw,1.375rem)`, body 1rem/1.5, small .875rem.

## Componentes

- **Tarjeta de producto**: media SVG line-art (el producto se dibuja, las fotos
  son contexto), tag mono, nombre, descripción 1 línea, fila precio + CTA con
  icono. Hover: lift 4px + borde lima + glow. Foco visible cian.
- **Cintas (marquee)**: loop CSS `translateX(-50%)`, contenido duplicado,
  pausa con `prefers-reduced-motion`.
- **Botones**: lima sobre tinta, texto negro; hover con sweep de brillo y glow.
- **Fotos de material**: grid con caption mono inferior, hover zoom suave.
- **Video**: loop muted playsinline con poster; se pausa con
  `prefers-reduced-motion`.

## Reglas

- Debe: tokens semánticos, estados hover/focus/active explícitos, contraste AA.
- No debe: texto < 14px salvo tags mono con tracking, sombras de color
  arbitrarias fuera de la pareja lima/cian, más de 2 acentos por bloque.
- Motion: solo transform/opacity; reveals por IntersectionObserver; todo loop
  respeta `prefers-reduced-motion`.
