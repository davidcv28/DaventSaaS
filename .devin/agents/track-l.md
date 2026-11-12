---
name: track-l
description: Track L — panel de comprador (/cuenta) y seguimiento de pedido intuitivos
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track L del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §4, "track-l — Cuenta + seguimiento"). Leé esa sección y ejecutala completa.

Scope de escritura (exclusivo): `frontend/src/views/StoreAccountView.vue`,
`frontend/src/components/ecommerce/account/*.vue`,
`frontend/src/views/StoreTrackingView.vue`.

OBLIGATORIO antes de empezar: invocar la skill `modern-web-guidance`.

Incluye la mini-explicación "¿Cómo funciona el seguimiento?" para el
comprador (ver §4 track-l). No inventes endpoints: si el link de
seguimiento no viaja en el payload de pedidos, reportalo.

Prohibido: `store-design-*.css`, `StoreAuthView.vue`, `StorePublicLayout.vue`,
git, dependencias nuevas.

Cierre: `git status --porcelain`, `git diff --stat`, verificación real,
clases nuevas agregadas (para F3), riesgos.
