# Attack report — Performance / N+1 (web pública + cuenta de comprador)

Fecha: 2026-11-13. Entorno local (Postgres local, `manage.py shell` + `django.test.Client` +
`CaptureQueriesContext`, host `localhost`). Tiendas medidas: `davent` (ecommerce, 12 productos
públicos, 1 review, reviews habilitadas), `vertice` (14 prod, sin plan reviews), `mi-qa`
(14 prod), `bench-store` (35 prod), `atelier-luma` (26 prod). Comprador autenticado con
`CustomerAccessToken` minteado en shell para el customer pk=1 (5 pedidos).
**Sin seeds ni sync; solo lectura.** El payload público/cache se busteó con `cache.clear()`
entre hits para medir el camino frío (el endpoint lo cachea con `public_cache_stamp`).

## Tabla de resultados

| Endpoint | Queries (frío / caliente) | N+1 | Tiempo frío | Causa | Severidad |
|---|---|---|---|---|---|
| `GET /api/stores/public/<slug>/` | 17–18 / 1–2 | No (plano: 12 prod → 18, 35 prod → 17) | ~40–50 ms | 17 queries fijas: store+suscription+plan+benefits+services+carousel+gallery×2+designpattern+chatbot+fiscal+payment+mp+exists(exclusive)+exists(membership)+visit. Es mucho pero constante; amortizado por cache de payload | baja |
| `GET /api/stores/public/<slug>/catalog/` (+`?q`,`?sort`) | 9–10 / 2 | **No** — idéntico con 12 y 35 productos | ~35–55 ms | Queryset anotado + prefetch de discounts (`_public_catalog_data`, `viewset.py:1031+`); rating anotado, no por fila | ok |
| `GET …/products/<id>/reviews/` | 3 / 3 | No | ~12 ms | `product.reviews.all()[:50]` una sola query (`viewset.py:1319`) | ok |
| `GET …/pattern/document/` | 11–21 base / 2 | **SÍ**: +1 `COUNT(*)` en `catalog_productreview` **por producto** cuando el plan tiene reviews (`can_rate`) — davent: 12 prod → 35 queries (12 COUNTs). Escala también con nº de productos que tienen votos (2º `COUNT` por `is_positive=True` por producto con votos) | ~60–140 ms (mi-qa ~700 ms por patrón pesado, no por queries) | `_rating_values()` (`StoreApp/domains/design/services/pattern_render.py:875-885`) llama `product.reviews.filter(is_positive__isnull=False).count()` y `.filter(is_positive=True).count()` — el `filter()` crea queryset nuevo y **pisa el `prefetch_related('reviews')`** de `_product_queryset` (`:291`). Fix: computar en Python sobre el prefetch o anotar el qs | **alta** en catálogos grandes con plan ecommerce |
| `GET …/pattern/document/?product=<id>` | base +4…+16 | **SÍ** (mismo bug, dos veces): +1 COUNT por cada **relacionado** — `_related_fragment` (`pattern_render.py:906-917`) arma su propio queryset **sin** `prefetch_related('reviews')`, y `_rating_values` vuelve a consultar por producto relacionado; +1 query extra de reviews del producto (`_reviews_fragment` :835, `reviews.all()[:50]` bypasea prefetch por el slice) | ~80–150 ms | mismo `_rating_values` (:1046 en ficha + :358 en tarjetas) | **alta** |
| `GET …/contact/captcha/` | 1 | No | ~10 ms | `issue_captcha` sin DB | ok |
| `GET /api/customer-auth/me/` | 1 | No | ~6 ms | — | ok |
| `GET /api/customer/profile/` | 1 | No | ~7 ms | — | ok |
| `GET /api/customer/orders/` | 4 | No | ~20 ms | `select_related('store','store__customization','store__user')` + `prefetch_related('items')` (`orders/views/customer.py:58-59`); `items_count` usa el prefetch (serializer :194) | ok |
| `GET /api/customer/addresses/` | 3 | No | ~15 ms | — | ok |
| `GET /api/customer/notifications/` | 6 | No | ~15 ms | — | ok |
| `GET /api/customer/memberships/` | 3 | No | ~15 ms | — | ok |
| `GET /api/cart/<slug>/` | 10–13 | No | ~40–55 ms | Plano: store+plan+benefits+cart+userprofile+discounts(prefetch)+membership×2+items con product join | ok |

## Hallazgo principal (único N+1 real)

**`pattern/document` recalcula el rating por producto.** En
`StoreApp/domains/design/services/pattern_render.py:880-884`:

```python
votes = product.reviews.filter(is_positive__isnull = False)
count = votes.count()                       # 1 query por producto
avg   = round(votes.filter(is_positive = True).count() / count * 5, 1)  # +1 si hay votos
```

Evidencia (davent, `can_rate=True`): 12× `SELECT COUNT(*) FROM catalog_productreview WHERE product_id=<cada id> AND is_positive IS NOT NULL` en un solo request de documento; +4 COUNTs más por los relacionados en `?product=`. En tiendas sin `store_has_reviews` el flag corta antes (`return '',''`) y no hay N+1 — por eso vertice/mi-qa no lo muestran. El `prefetch_related('reviews')` ya existe (`:291`); basta `sum(1 for r in product.reviews.all() if r.is_positive is not None)` en memoria, o anotar `Count`/`Avg` en el queryset. `_related_fragment` (:906-917) además necesita el prefetch que le falta.

## Latencia no-query

- `pattern/document` de `mi-qa` tarda ~700 ms en frío con solo 11 queries — el costo es render del patrón (impacto/moda: documentos grandes), no DB. Considerable pero cacheado (2 queries en caliente).
- `public/<slug>` cuesta 17 queries fijas en frío — candidato a `select_related` extra si se quisiera recortar, pero el cache de payload lo vuelve irrelevante en producción.

## Verificado sin N+1

Catálogo (filtros/sorts incluidos — `_params_fingerprint` bustea cache correctamente y el queryset es
anotado), reviews por producto, cuenta del comprador (orders/addresses/notifications/memberships),
carrito, captcha. Los descuentos NO se recalculan por fila en el catálogo: `catalog_discount` se
prefetchea una vez por request.
