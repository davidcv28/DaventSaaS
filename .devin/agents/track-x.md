---
name: track-x
description: Track X — integración final, cambios globales reportados y gates completos
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track X del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §7, "track-x — Integración y cierre"). Leé esa sección y ejecutala.

Recibís: `docs/qa-funcionalidad.md` (track-w) + los "cambios globales
necesarios" reportados por todos los tracks (snippets en sus informes).

Tarea:
1. Aplicar una sola vez los cambios en archivos globales:
   `frontend/src/assets/store-page.css`, `store-tpl-card.css`,
   `store-catalog*.css`, `store-raiz*.css`, `store-style-*.css`,
   `skin-*.css`, `frontend/src/views/store/raiz/**`,
   `frontend/src/views/store/<tpl>/{Inicio,Producto,Servicios}View.vue`,
   `frontend/src/components/store/pattern*.js`/bridge si existe,
   `StoreApp/domains/design/seed_data.json` (sincronizar con los
   `sources/*.html` que los ds modificaron — vía
   `manage.py import_design_pattern` o edición única del seed).
2. Correr gates: `cd frontend && npm run lint`, `npm test`,
   `venv/Scripts/python.exe manage.py test` de los dominios tocados
   (catalog, stores, design según corresponda), `npm run visual:qa` si
   aplica. Truncar salidas a lo relevante.
3. Resolver o justificar cada pendiente del informe de track-w que sea
   global; los que son por-diseño quedan listados para el usuario.

Prohibido: git, dependencias nuevas, rediseños fuera de lo reportado.

Cierre: tabla `pendiente | resuelto | sigue abierto (motivo)`, salidas de
gates reales, `git status --porcelain`, `git diff --stat`, riesgos.
