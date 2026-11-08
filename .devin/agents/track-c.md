---
name: track-c
description: Track C — checklist "Calidad de tu web" (endpoint de score + tarjeta en el dashboard)
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track C del plan de calidad de webs de SaaS DAVENT.

Tarea: abrí `PLAN_WEB_PROFESIONAL.md` y ejecutá literalmente la sección
`### Prompt C — Checklist "Calidad de tu web"` (dentro de §4). Reglas globales: §2.

Scope de escritura (exclusivo): `frontend/src/views/DashboardView.vue`,
`frontend/src/components/design/WebQualityCard.vue` (nuevo),
`frontend/src/composables/useWebQuality.js` (nuevo), `frontend/src/api/quality.api.js` (nuevo),
`StoreApp/domains/stores/**` (servicio + vista + ruta nuevos),
`StoreApp/domains/stores/tests_quality.py` (nuevo).

Prohibido: `store-*.css`, `store-page.css`, `package.json`, `imaging.py`,
`TypographyPanel.vue`, el contrato de tema, git.

Cerrá con: contrato del endpoint (request/response + ejemplo real), pesos que suman 100,
archivos escritos, salida de `manage.py test StoreApp.domains.stores.tests_quality` y `npm run lint`.
