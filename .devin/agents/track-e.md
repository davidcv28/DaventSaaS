---
name: track-e
description: Track E — tipografía curada (FONT_PAIRS por diseño) y paddings de pieles a tokens --st-*
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track E del plan de calidad de webs de SaaS DAVENT.

Tarea: abrí `PLAN_WEB_PROFESIONAL.md` y ejecutá literalmente la sección
`### Prompt E — Tipografía curada + tokens de pieles` (dentro de §4). Reglas globales: §2.

Scope de escritura (exclusivo): `frontend/src/components/studio/panels/TypographyPanel.vue`,
`frontend/src/components/studio/panels/panelShared.js`, `frontend/src/assets/store-page.css`,
`frontend/src/assets/store-*.css`.

Prohibido: `contract.js`, `DashboardView.vue`, `imaging.py`, `package.json`,
`StoreApp/domains/design/sources/**`, git.

Regla crítica: cero cambio visual por defecto. Cada token nuevo lleva fallback al valor
hardcodeado actual. Un tema ya guardado debe verse exactamente igual.

Cerrá con: tabla de pares/pesos bloqueados por diseño, tabla de valores tokenizados
(archivo:línea, antes → después), salida de `npm run verify:studio`, `npm run lint`, `npm run build`.
