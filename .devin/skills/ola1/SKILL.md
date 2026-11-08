---
name: ola1
description: Lanza en paralelo los 5 tracks de la ola 1 (auditoría, gate CI, calidad, fotos, tipografía)
allowed-tools:
  - read
  - grep
  - glob
---

Lanzá la ola 1 del plan de webs profesionales (`PLAN_WEB_PROFESIONAL.md`).

1. Leé una sola vez la tabla de scopes de `PLAN_WEB_PROFESIONAL.md` §1. No releas el resto.
2. Lanzá los 5 subagentes EN PARALELO con `run_subagent`, todos con `is_background: true`:

   | profile | title |
   |---------|-------|
   | `track-a` | Track A — auditoría visual |
   | `track-b` | Track B — gate visual CI |
   | `track-c` | Track C — calidad de contenido |
   | `track-d` | Track D — fotos |
   | `track-e` | Track E — tipografía y tokens |

   Task de cada uno: "Ejecutá tu rol tal como está definido. No hagas git. Al terminar reportá:
   archivos escritos, verificación corrida con su salida real, y riesgos o dependencias fuera de scope."
3. Mientras corren no commitees ni arregles nada.
4. Al volver cada uno, tabla: `track | archivos tocados | ¿en scope? | verificación | pendientes`.
   Compará los archivos contra la lista permitida de §1.
5. Los subagentes en background heredan solo los permisos ya aprobados en la sesión. Si un track
   falla por permiso denegado, relanzalo con `is_background: false` para poder aprobar, o resumilo
   en foreground con `read_subagent`.

No hagas `git add`/`commit`/`push`: el usuario decide qué se commitea.
