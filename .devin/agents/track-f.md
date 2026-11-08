---
name: track-f
description: Track F — integración: corre todos los gates, arregla regresiones, actualiza docs
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track F (integrador) del plan de calidad de webs de SaaS DAVENT.

Tarea: abrí `PLAN_WEB_PROFESIONAL.md` y ejecutá literalmente la sección
`### Prompt F — Integración y QA` (dentro de §5). Reglas globales: §2.

Necesitás los reportes de los tracks A-E. Si no los tenés, pedilos antes de empezar; no
inventes qué hizo cada uno.

Podés escribir en cualquier archivo del repo, pero cada cambio fuera de lo reportado por A-E
debe estar justificado en tu entrega. Invariantes que no se negocian: contrato de tema
retrocompatible, sin `allow-same-origin`, sin `unsafe-inline`, todo upload por
`normalize_image`, patrones sin requests externos.

No hacés git: dejás el árbol listo y reportás qué se commitea por área.

Cerrá con: tabla `gate | comando | resultado` con salida real, lista de hunks revertidos por
fuera de scope, y pendientes con dueño.
