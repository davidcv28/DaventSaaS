---
name: track-m
description: Track M — catálogo público + filtro "Eventos" condicional + limpieza de props de tarjeta
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track M del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §5, "track-m — Catálogo + filtro de eventos"). Leé esa sección y ejecutala completa.

Scope de escritura (exclusivo): `StoreApp/domains/stores/views/viewset.py`
(solo la acción catalog del viewset público), `frontend/src/api/stores.api.js`,
`frontend/src/api/catalog.api.js`, `frontend/src/composables/useStoreCatalog.js`,
`frontend/src/composables/catalogFiltersUi.js`, `frontend/src/views/StoreCatalogView.vue`,
`frontend/src/views/store/*/CatalogoView.vue`, `frontend/src/assets/store-catalog*.css`,
`frontend/src/assets/store-raiz-catalog.css`, y `frontend/src/components/store/blocks/*`
únicamente para quitar props deprecadas de `TplProductCard`.

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

El filtro "Eventos" aparece SOLO si `event_count > 0`. Semántica backend:
`product.effective_discount is not None` (descuento programado vigente),
no `effective_offer`. Agregar test del param `event`.

Prohibido: modelos/migraciones del catálogo, `StorePublicLayout.vue`,
`TplProductCard.vue`, `store-design-*.css`, `store-<tpl>.css`, git.

Cierre: test corrido con salida real, `git status --porcelain`,
`git diff --stat`, verificación del endpoint `?event=1`, riesgos.
