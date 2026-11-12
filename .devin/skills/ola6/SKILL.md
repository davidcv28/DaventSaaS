---
name: ola6
description: Lanza en paralelo los 5 tracks de diseños del plan de funcionalidad (requiere ola5 commiteada)
allowed-tools:
  - read
  - grep
  - glob
---

Lanzá la ola F3 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §6).

Requisito previo: ola5 commiteada — los diseños se verifican contra el
navbar, la tarjeta, el auth, la cuenta/seguimiento y el filtro de eventos
YA mergeados.

1. Lanzá 5 subagentes EN PARALELO con `run_subagent`, `is_background: true`:

   | profile | title | slugs |
   |---------|-------|-------|
   | `track-ds1` | DS1 | portico, esencial, mercado, gimnasio, moderntec |
   | `track-ds2` | DS2 | ruta, aurum, brigada, indumentaria, impacto |
   | `track-ds3` | DS3 | calzado, moda, modista, topmodern, viajero |
   | `track-ds4` | DS4 | olivium, atelier-noir, guardia, expediente, silicio |
   | `track-ds5` | DS5 | neon, showroom, sastreria, autoservicio, movimiento, umbral |

   Task de cada uno: "Ejecutá tu rol tal como está definido en
   PLAN_FUNCIONALIDAD.md §6 con tus slugs. No hagas git. Reportá por
   slug: fixes aplicados y cambios globales necesarios con snippet."
2. Scopes disjuntos por slug (§1). `seed_data.json` y todo archivo global
   están PROHIBIDOS: se reportan para track-x.
3. Al volver cada track: `git status --porcelain` + `git diff --stat`,
   comparar contra §1, verificación mínima, commit conventional + push.
4. Consolidá la lista de "cambios globales necesarios" de los 5 informes
   en un único anexo (va para track-x en ola7).
5. Tabla final: `grupo | slugs | fixes | pendientes globales`.

Al terminar los 5 commiteados, avisá que se puede lanzar `ola7`.
