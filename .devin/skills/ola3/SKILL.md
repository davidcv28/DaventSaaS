---
name: ola3
description: Lanza en paralelo los 4 tracks de fixes por grupo de patrones (G1-G4)
allowed-tools:
  - read
  - grep
  - glob
---

Lanzá la ola 3 del plan (`PLAN_WEB_PROFESIONAL.md` §6): fixes de auditoría por grupo de patrones.

Requisitos antes de lanzar:
- `docs/audit-design-slop.md` existe y tiene pendientes de severidad media o alta.
- La ola 2 (track F) ya corrió y los gates están verdes.

1. Lanzá 4 subagentes EN PARALELO con `run_subagent`, `is_background: true`, profiles
   `track-g1`, `track-g2`, `track-g3`, `track-g4`. Task: "Ejecutá tu rol tal como está definido.
   No hagas git. Reportá por patrón: fix, archivo:línea y salida de visual:qa --only=<slug>."
2. Los scopes son disjuntos por slug, así que no hay conflictos de escritura.
3. Al volver, tabla: `grupo | patrones | fixes aplicados | fixes que requieren cambio global`.
4. Los fixes que pidan `store-page.css` o `seed_data.json` NO los apliques vos sin pedirlo:
   listalos para una pasada final única (un solo archivo compartido = un solo agente).

No hagas git.
