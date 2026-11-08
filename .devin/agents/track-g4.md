---
name: track-g4
description: Track G4 — fixes de auditoría en expediente, silicio, neon, showroom, sastreria
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track G4 del plan de calidad de webs de SaaS DAVENT.

Tus patrones: `expediente, silicio, neon, showroom, sastreria`.

Tarea: abrí `PLAN_WEB_PROFESIONAL.md`, sección `## 6. OLA 3 — Fixes por grupo de patrones`,
y ejecutá ese prompt con tu lista de patrones. La fuente de los fixes es
`docs/audit-design-slop.md`: arreglá solo lo que la auditoría lista para tus patrones.

Scope de escritura (exclusivo): `StoreApp/domains/design/sources/<slug>.html`,
`frontend/src/assets/store-<slug>.css`, `frontend/src/templates/**/views/store/<slug>/**`.

Prohibido: `store-page.css`, `seed_data.json`, `templates/index.js`, `package.json`, archivos
de otro grupo, backend, git. Si un fix necesita un cambio global, anotalo con el snippet exacto.

Cerrá con: por patrón, tabla `fix | archivo:línea | qué cambió` y salida de
`npm run visual:qa -- --only=<slug>` para cada uno.
