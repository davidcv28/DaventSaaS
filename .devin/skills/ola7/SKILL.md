---
name: ola7
description: Lanza la ola F4 del plan de funcionalidad — inspector visual y luego integración (requiere ola6 commiteada)
allowed-tools:
  - read
  - grep
  - glob
---

Lanzá la ola F4 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §7).

Requisito previo: ola6 commiteada — se inspecciona el sistema ya integrado.

1. Lanzá `track-w` (inspector visual, read-only salvo
   `docs/qa-funcionalidad.md` + screenshots) con `is_background: false`
   si tarda mucho o `true` y esperá. Task: "Ejecutá tu rol tal como está
   definido en PLAN_FUNCIONALIDAD.md §7. No hagas git."
2. Al terminar w: commiteá el informe (`docs:` conventional) + push.
3. Lanzá `track-x` (integrador) con el informe de w + la lista consolidada
   de cambios globales de ola6. Task: "Ejecutá tu rol tal como está
   definido en PLAN_FUNCIONALIDAD.md §7. No hagas git."
4. Al volver x: `git status --porcelain` + `git diff --stat`, verificar
   scope (archivos globales + seed_data.json), correr los gates que
   reportó, commit conventional + push.
5. Cierre: tabla `pendiente | resuelto por track-x | sigue abierto (motivo)`
   y gates con salida real.

Si track-w encuentra hallazgos ALTOS por diseño específico (no globales),
listalos para el usuario — se pueden retomar los tracks ds con `resume`
de `run_subagent` en una ola correctiva.
