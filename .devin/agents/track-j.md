---
name: track-j
description: Track J — tarjeta de producto del catálogo (sin botones, contrato de contenido)
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track J del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §4, "track-j — Tarjeta de producto"). Leé esa sección y ejecutala completa.

Scope de escritura (exclusivo): `frontend/src/components/store/TplProductCard.vue`,
`frontend/src/assets/store-tpl-card.css`, `frontend/src/components/store/OfferSeal.vue`,
`frontend/src/components/store/StTag.vue`.

Antes de tocar markup/CSS invocá la skill `modern-web-guidance`.

Prohibido: call sites de la tarjeta (`views/store/*/CatalogoView.vue`,
`components/store/blocks/*` — los limpia track-m), `catalog.api.js`,
`useStoreCatalog.js`, cualquier `store-*.css` de diseño, git.

Cierre: contrato documentado, `git status --porcelain`, `git diff --stat`,
verificación real truncada, lista de call sites que track-m debe limpiar.
