---
name: track-d
description: Track D — fotos (1600px, aviso de baja resolución, hint por slot, normalize_image intacto)
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track D del plan de calidad de webs de SaaS DAVENT.

Tarea: abrí `PLAN_WEB_PROFESIONAL.md` y ejecutá literalmente la sección
`### Prompt D — Fotos` (dentro de §4). Reglas globales: §2.

Scope de escritura (exclusivo): `StoreApp/domains/stores/services/imaging.py`,
`StoreApp/domains/stores/services/media_quality.py` (nuevo),
`StoreApp/domains/stores/tests_media_quality.py` (nuevo),
`frontend/src/components/design/DesignLookTab.vue`,
`frontend/src/components/design/MediaQualityHint.vue` (nuevo).

Prohibido: `DashboardView.vue`, `package.json`, `store-*.css`, contrato de tema, git.
Toda imagen sigue pasando por `normalize_image` (WebP, EXIF corregido). Nunca rechaces un
archivo por calidad: solo avisás.

Cerrá con: tabla de slots y umbrales, respuesta de upload con `quality`, archivos escritos,
salida de `manage.py test StoreApp.domains.stores.tests_media_quality` y `npm run lint`.
