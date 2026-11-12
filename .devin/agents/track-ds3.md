---
name: track-ds3
description: Track DS3 — diseños calzado, moda, modista, topmodern, viajero
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track DS3 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §6).
Leé §6.1 (checklist por diseño) y §6.2 (reglas ds) y ejecutalos con tus slugs.

Tus diseños: `calzado`, `moda`, `modista`, `topmodern`, `viajero`.

Scope de escritura (exclusivo): `frontend/src/assets/store-design-calzado.css`,
`store-design-calzado-auth.css`, `store-design-moda.css`,
`store-design-modista.css`, `store-design-topmodern.css`,
`store-design-viajero.css`, y
`StoreApp/domains/design/sources/{calzado,moda,modista,topmodern,viajero}.html`.

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

Prohibido: `seed_data.json`, `store-page.css`, `store-tpl-card.css`,
`store-catalog*.css`, `store-raiz*.css`, `store-style-*.css`, `skin-*.css`,
`views/store/**`, `pattern_bridge.js`/`pattern.js`, `templates/index.js`,
git, archivos de otros grupos. Necesitás un cambio ahí → reportalo con
snippet para track-x.

Cierre por slug: tabla `superficie | fix | archivo:línea | nota para
integrador`, `git status --porcelain`, `git diff --stat`, verificación a
360px + desktop, riesgos.
