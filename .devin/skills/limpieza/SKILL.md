---
name: limpieza
description: Track Z — diagnóstico de basura, aprobación explícita y borrado seguro
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
---

Ejecutá el track Z (`PLAN_WEB_PROFESIONAL.md` §7) **inline, no como subagente**: necesitás
`ask_user_question` para la aprobación, y los subagentes no pueden preguntar.

1. Fase 1 — diagnóstico, sin borrar nada:
   - `git status --porcelain --untracked-files=all`, `git check-ignore -v <ruta>`, `du -sh`.
   - Tabla: `ruta | tamaño | tracked? | qué es | veredicto (borrar / conservar / preguntar)`.
2. Fase 2 — aprobación: mostrá la tabla y usá `ask_user_question` con opciones
   (borrar solo lo seguro / borrar seguro + los dudosos que marque / no borrar nada).
   Sin respuesta explícita no se borra nada.
3. Fase 3 — ejecución de lo aprobado, una ruta por vez. Prohibido `git clean`, comodines
   amplios y borrar `media/`, `.env*`, `db.sqlite3`, `venv/`, `node_modules/`, `.git/`,
   `awesome-design-skills/`.
   Los archivos tracked se van con `git rm` + commit `chore: remove <qué>`.
4. Actualizá `.gitignore` con los patrones que falten (`pip-*/`, `.tmp_*`, `_tmp_*/`).
5. Verificá: `git status --porcelain`, `npm run build` (desde `frontend/`), `manage.py check`.
   Commit + push de `.gitignore` y de los `git rm`.

Cerrá con: tabla de lo borrado, total liberado, salida de las 3 verificaciones y pendientes.
