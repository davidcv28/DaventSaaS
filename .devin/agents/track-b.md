---
name: track-b
description: Track B — gate visual en CI (screenshots, scroll horizontal, consola, contraste AA)
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track B del plan de calidad de webs de SaaS DAVENT.

Tarea: abrí `PLAN_WEB_PROFESIONAL.md` y ejecutá literalmente la sección
`### Prompt B — Gate visual en CI` (dentro de §4). Reglas globales: §2.

Scope de escritura (exclusivo): `frontend/scripts/visual-qa.mjs`,
`frontend/visual-qa.config.json`, `frontend/scripts/lib/**` y UNA línea de script en
`frontend/package.json`.

Prohibido: componentes, CSS (`store-*.css`, `store-page.css`), backend, contrato de tema,
instalar dependencias sin pedir aprobación, git. Si detectás defectos de CSS, anotalos en el
reporte: no los arregles (pertenecen al track E).

Cerrá con: salida real del script contra 3 patrones (claro, oscuro, advanced), archivos
escritos, dependencias pedidas y defectos observados que no te corresponden.
