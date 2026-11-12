# Cambios globales reportados por los tracks ds (ola6)

Anexo para `track-x` (integrador). Cada entrada viene del informe del
track indicado; aplicar una sola vez en archivos globales.

## 1. `pattern_bridge.js` — CTA dentro de tarjeta (reportan DS1, DS5, DS4)

`initCommerce`/`injectCardBuys` (~L1825) inserta `.dsx-buy-wrap >
button.dsx-buy` dentro de `.ds-product` cuando `data-ds-commerce="1"`.
Contradice el contrato tarjeta=un solo link (track-j). Los docs ya lo
tapan por CSS (`display:none`), pero el fix definitivo es global:

```js
// Contrato de tarjeta: la tarjeta es un solo link; el CTA vive en la ficha.
function injectCardBuys() { syncCardDock() }  // ya no montar .dsx-buy-wrap en .ds-product
```

Ojo: silicio (DS4) corrigió su selector CSS asumiendo que el bridge
sigue inyectando `.dsx-buy-wrap > .dsx-buy` — si se quita la inyección,
esas reglas quedan inertes (inofensivas).

## 2. Filtro "Eventos" en documentos patrón (reportan DS1, DS3, DS4, DS5)

`?event=1` + `event_count` existe solo en la vista Vue (ola5). Los docs
patrón tienen `data-ds-filters` pero el fragmento no emite marcador de
descuento programado ni el panel un control de eventos. Gap de feature:

- `pattern_render.py` (~L339-355, `_product_fragment`): emitir
  `data-event="1"` en `<article class="ds-product">` cuando el producto
  tiene `effective_discount` y exponer `event_count` en el payload del
  documento (conteo global como `offer_count`/`new_count`).
- `pattern_bridge.js`: `state` (~L526) sin flag `event`; `applyCatalog()`
  filtra `{q,cat,brands,min,max,offers}` — agregar el flag y el control
  en el panel de filtros solo si `event_count>0`.
- `PatternSurface.vue` (~L112-119): pasar `event` si el documento lo
  expone.

## 3. `seed_data.json` — resincronizar sources modificados (todos los ds)

Los tracks modificaron `StoreApp/domains/design/sources/*.html`; hay que
regenerar el seed vía `manage.py import_design_pattern` (o edición única
del seed) para que las tiendas publicadas sirvan el documento nuevo.
Archivos tocados (commits ola6):

- calzado, moda, modista, viajero (DS3)
- portico, esencial, mercado, moderntec (DS1)
- sastreria, showroom (DS5)
- atelier-noir, expediente, guardia, olivium, silicio (DS4)
- (DS2: ruta/aurum/brigada si los toca — pendiente de su informe)

## 4. `.ec-cartpg`, `.ec-checkout`, `.ec-receiptpg`, `.ec-legal` — mismo
   hueco de piel neutra que tenía `.ec-track` (reporta DS1)

Los sheets `store-design-*.css` re-teman `:is(.ec-auth, .ec-account)`
(los tracks agregaron `.ec-track`), pero carrito/checkout/recibo/páginas
legales siguen con acento neutro en todos los diseños. Decisión global:
extender el `:is()` a esas clases o aceptarlo como neutro.

## 5. Verificado-sin-cambios relevantes (contexto, no acción)

- `sources/moda|modista|viajero|showroom|olivium|atelier-noir|guardia|silicio|sastreria.html`:
  `.ds-stock`/desc/cat visibles solo donde el contrato lo pide; showroom
  `.p-heart` reubicado fuera del `<a class="ds-product-link">` (overlay).
- `sources/calzado.html`: `.ds-stock{display:none!important}` en vista
  lista (bug latente: el puente fuerza `.is-out` con `!important`).
- Auth sheets de DS5 (sastreria/autoservicio/movimiento/showroom):
  split editorial → tarjeta única 680-760px.
