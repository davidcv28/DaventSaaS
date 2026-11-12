---
name: track-ds1
description: Track DS1 — diseños portico, esencial, mercado, gimnasio, moderntec
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track DS1 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §6).
Leé §6.1 (checklist por diseño) y §6.2 (reglas ds) y ejecutalos con tus slugs.

Tus diseños: `portico`, `esencial`, `mercado`, `gimnasio`, `moderntec`.

Scope de escritura (exclusivo): `frontend/src/assets/store-design-portico.css`,
`store-design-esencial.css`, `store-design-esencial-auth.css`,
`store-design-esencial-account.css`, `store-design-mercado.css`,
`store-design-gimnasio.css`, `store-design-moderntec.css`,
`store-mercado.css`, `store-gimnasio.css`, `store-moderntec.css`,
`store-moderntec-auth.css`, `store-moderntec-account.css`,
`store-moderntec-account-sections.css`, y
`StoreApp/domains/design/sources/{portico,esencial,mercado,moderntec}.html`.
(gimnasio y moderntec pueden no tener source propio — verificá antes de asumir.)

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

Prohibido: `seed_data.json`, `store-page.css`, `store-tpl-card.css`,
`store-catalog*.css`, `store-raiz*.css`, `store-style-*.css`, `skin-*.css`,
`views/store/**`, `pattern_bridge.js`/`pattern.js`, `templates/index.js`,
git, archivos de otros grupos. Necesitás un cambio ahí → reportalo con
snippet para track-x.

Cierre por slug: tabla `superficie | fix | archivo:línea | nota para
integrador`, `git status --porcelain`, `git diff --stat`, verificación a
360px + desktop, riesgos.
