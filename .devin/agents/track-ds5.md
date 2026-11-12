---
name: track-ds5
description: Track DS5 — diseños neon, showroom, sastreria, autoservicio, movimiento, umbral
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track DS5 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §6).
Leé §6.1 (checklist por diseño) y §6.2 (reglas ds) y ejecutalos con tus slugs.

Tus diseños: `neon`, `showroom`, `sastreria`, `autoservicio`, `movimiento`,
`umbral`.

Scope de escritura (exclusivo): `frontend/src/assets/store-design-neon.css`,
`store-design-showroom.css`, `store-design-sastreria.css`,
`store-design-autoservicio.css`, `store-design-movimiento.css`,
`store-design-umbral.css`, `store-sastreria.css`, `store-movimiento.css`, y
`StoreApp/domains/design/sources/{neon,showroom,sastreria,autoservicio,umbral}.html`
(movimiento no tiene source — es template puro; sastreria tiene 3 variantes
de menú móvil por estilo, verificarlas).

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

Prohibido: `seed_data.json`, `store-page.css`, `store-tpl-card.css`,
`store-catalog*.css`, `store-raiz*.css`, `store-style-*.css`, `skin-*.css`,
`views/store/**`, `pattern_bridge.js`/`pattern.js`, `templates/index.js`,
git, archivos de otros grupos. Necesitás un cambio ahí → reportalo con
snippet para track-x.

Cierre por slug: tabla `superficie | fix | archivo:línea | nota para
integrador`, `git status --porcelain`, `git diff --stat`, verificación a
360px + desktop, riesgos.
