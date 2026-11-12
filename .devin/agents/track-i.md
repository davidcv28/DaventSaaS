---
name: track-i
description: Track I — navbar compartido de las webs de tienda (colisiones móvil)
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track I del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §4, "track-i — Navbar"). Leé esa sección y ejecutala completa.

Scope de escritura (exclusivo): `frontend/src/views/StorePublicLayout.vue`,
y solo selectores de navegación dentro de `frontend/src/assets/store-page.css`
y `store-style-menus.css`.

Antes de tocar CSS/JS de cliente invocá la skill `modern-web-guidance`.

Prohibido: `store-design-*.css`, `store-<tpl>.css`, `store-tpl-card.css`,
vistas de catálogo/cuenta/auth, `seed_data.json`, git, dependencias nuevas.

Cierre: tabla `breakpoint | controles visibles | problema | fix`,
`git status --porcelain`, `git diff --stat`, verificación real truncada,
riesgos y cambios globales necesarios (con snippet) para track-x.
