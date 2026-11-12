---
name: track-ds4
description: Track DS4 — diseños olivium, atelier-noir, guardia, expediente, silicio
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track DS4 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §6).
Leé §6.1 (checklist por diseño) y §6.2 (reglas ds) y ejecutalos con tus slugs.

Tus diseños: `olivium`, `atelier-noir`, `guardia`, `expediente`, `silicio`.

Scope de escritura (exclusivo): `frontend/src/assets/store-design-olivium.css`,
`store-design-atelier-noir.css`, `store-design-guardia.css`,
`store-design-expediente.css`, `store-design-silicio.css`, y
`StoreApp/domains/design/sources/{olivium,atelier-noir,guardia,expediente,silicio}.html`.

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

Prohibido: `seed_data.json`, `store-page.css`, `store-tpl-card.css`,
`store-catalog*.css`, `store-raiz*.css`, `store-style-*.css`, `skin-*.css`,
`views/store/**`, `pattern_bridge.js`/`pattern.js`, `templates/index.js`,
git, archivos de otros grupos. Necesitás un cambio ahí → reportalo con
snippet para track-x.

Cierre por slug: tabla `superficie | fix | archivo:línea | nota para
integrador`, `git status --porcelain`, `git diff --stat`, verificación a
360px + desktop, riesgos.
