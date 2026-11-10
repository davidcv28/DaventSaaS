# PROMPT — Push de cierre de sesión

```
Revisá el estado completo del repo y pusheá TODO el trabajo pendiente de esta sesión en la rama ECCOMMERCE-ADD:

1. `git status` + `git diff --stat` + `git log --oneline origin/ECCOMMERCE-ADD..HEAD` — verificá que no quede trabajo sin commitear ni commits sin pushear.
2. Para cada archivo modificado sin commit: agrupalo por tema y commitealo con mensaje conventional corto en inglés (feat/fix/chore/docs) explicando el porqué.
3. Ignorá (NO commitear): `.env`, `venv/`, `node_modules/`, `dist/`, `frontend/.tmp/`, scratch de QA (`_qa_*.mjs`, `*.png` de verificación) y los `_credits_*` de la raíz (son de otra tarea — dejalos untracked).
4. Verificación barata antes de pushear: `ruff check` en los dominios backend tocados y `vite build` si hay cambios de frontend (con TMP local en Windows). Si algo falla, arreglalo antes del push.
5. `git push` a `origin/ECCOMMERCE-ADD` y confirmá con `git log origin/ECCOMMERCE-ADD..HEAD` vacío + `git status` limpio.
6. Reportá en una tabla: commits nuevos, archivos por commit, checks corridos y resultado.
```
