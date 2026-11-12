---
name: ola5
description: Lanza en paralelo los 2 tracks de catálogo+eventos y seed de descuentos (requiere ola4 commiteada)
allowed-tools:
  - read
  - grep
  - glob
---

Lanzá la ola F2 del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §5).

Requisito previo: ola4 (tracks i,j,k,l) commiteada y pusheada — track-m
limpia los call sites que track-j deprecó.

1. Lanzá 2 subagentes EN PARALELO con `run_subagent`, `is_background: true`:

   | profile | title |
   |---------|-------|
   | `track-m` | Track M — catálogo + filtro Eventos |
   | `track-n` | Track N — seed descuentos david28 |

   Task de cada uno: "Ejecutá tu rol tal como está definido en
   PLAN_FUNCIONALIDAD.md §5. No hagas git. Reportá archivos escritos,
   verificación corrida con salida real, y dependencias fuera de scope
   con snippet exacto."
2. Scopes disjuntos (§1): track-m = front catálogo + vista catalog del
   backend; track-n = comando management nuevo + manage.py.
3. Al volver cada track: `git status --porcelain` + `git diff --stat`,
   comparar contra §1, verificación mínima, commit conventional + push.
4. Verificar especialmente: `?event=1` filtra y `event_count` viaja en la
   respuesta; el seed corrió `--dry-run` antes de aplicar y usó el slug
   real de la tienda david28.
5. Tabla final: `track | archivos | ¿en scope? | verificación | pendientes`.

Al terminar los 2 commiteados, avisá que se puede lanzar `ola6`.
