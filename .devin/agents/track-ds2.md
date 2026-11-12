---
name: track-ds2
description: Track DS2 — diseños ruta, aurum, brigada, indumentaria, impacto
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track DS2 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §6).
Leé §6.1 (checklist por diseño) y §6.2 (reglas ds) y ejecutalos con tus slugs.

Tus diseños: `ruta`, `aurum`, `brigada`, `indumentaria`, `impacto`.

Scope de escritura (exclusivo): `frontend/src/assets/store-design-ruta.css`,
`store-design-aurum.css`, `store-design-brigada.css`,
`store-design-indumentaria.css`, `store-design-impacto.css`,
`store-indumentaria.css`, `store-impacto.css`, `store-impacto-auth.css`, y
`StoreApp/domains/design/sources/{ruta,aurum,brigada,indumentaria}.html`
(impacto no tiene source — es template puro).

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

Prohibido: `seed_data.json`, `store-page.css`, `store-tpl-card.css`,
`store-catalog*.css`, `store-raiz*.css`, `store-style-*.css`, `skin-*.css`,
`views/store/**`, `pattern_bridge.js`/`pattern.js`, `templates/index.js`,
git, archivos de otros grupos. Necesitás un cambio ahí → reportalo con
snippet para track-x.

Cierre por slug: tabla `superficie | fix | archivo:línea | nota para
integrador`, `git status --porcelain`, `git diff --stat`, verificación a
360px + desktop, riesgos.
