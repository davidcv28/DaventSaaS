---
name: ola4
description: Lanza en paralelo los 4 tracks de fundaciones del plan de funcionalidad (navbar, tarjeta, auth, cuenta+seguimiento)
allowed-tools:
  - read
  - grep
  - glob
---

Lanzá la ola F1 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §4).

Requisitos: ninguno (es la primera ola). El plan completo está en
`PLAN_FUNCIONALIDAD.md` — leelo una vez, no lo releas.

1. Lanzá 4 subagentes EN PARALELO con `run_subagent`, `is_background: true`:

   | profile | title |
   |---------|-------|
   | `track-i` | Track I — navbar compartido |
   | `track-j` | Track J — tarjeta de producto |
   | `track-k` | Track K — auth minimalista |
   | `track-l` | Track L — cuenta + seguimiento |

   Task de cada uno: "Ejecutá tu rol tal como está definido en
   PLAN_FUNCIONALIDAD.md. No hagas git. Reportá archivos escritos,
   verificación corrida con salida real, y dependencias fuera de scope
   con snippet exacto."
2. Los scopes son disjuntos (§1 del plan) — no debería haber conflictos.
   Si dos tracks tocan el mismo archivo, ganá el que lo tiene en §1 y
   pedile al otro que reporte el cambio.
3. Al volver cada track: `git status --porcelain` + `git diff --stat`,
   comparar contra la lista permitida, correr la verificación mínima,
   y recién ahí `git add` + commit conventional en inglés + `git push`
   a `main` (regla AGENTS.md: nunca dejar trabajo sin commitear).
4. Tabla final: `track | archivos | ¿en scope? | verificación | pendientes`.
5. Subagentes en background heredan solo permisos ya aprobados; si uno
   falla por permiso, relanzalo `is_background: false` o resumilo.

Al terminar los 4 commiteados, avisá que se puede lanzar `ola5`.
