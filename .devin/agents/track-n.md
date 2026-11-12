---
name: track-n
description: Track N — seed de descuentos de prueba en la tienda david28
allowed-tools:
  - read
  - grep
  - glob
  - edit
  - write
  - exec
---

Sos el track N del plan de funcionalidad (`PLAN_FUNCIONALIDAD.md` §5, "track-n — Seed de descuentos demo"). Leé esa sección y ejecutala completa.

Scope de escritura (exclusivo): `StoreApp/domains/catalog/management/commands/seed_demo_discounts.py`
(archivo nuevo) y ejecución de `venv/Scripts/python.exe manage.py` contra la
DB local.

Tarea: comando idempotente `seed_demo_discounts --store <slug> [--dry-run]
[--clear]` que crea ≥4 `Discount` vigentes con alcances distintos
(ALL/CATEGORY/BRAND/PRODUCTS), nombre prefijado `DEMO ·`, más variación de
`offer_price`/`stock` para probar la tarjeta. Primero `--dry-run`, mostrar
la tabla, luego aplicar. Verificar el slug real de la tienda "david 28"
con `Store.objects.values_list('slug', flat=True)` antes de escribir nada.

Prohibido: editar modelos, migraciones, views, fixtures, `seed_data.json`,
git, tocar OTRAS tiendas.

Cierre: slug usado, tabla de descuentos creados, salida del GET catálogo
con `discount`/`discount_offer`/`event_count`, `git status --porcelain`,
`git diff --stat`, riesgos.
