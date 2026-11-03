# PROMPT — Diseño premium generalista "Áurea" (slug `aurum`)

> Convertir el boceto `boceto/premium/index.html` en un diseño del catálogo,
> nivel **advanced** (Premium), apto para todo rubro, con TODAS las secciones
> habilitadas. Seguir el contrato de `StoreApp/domains/design/sources/` y
> `pattern_render.py`.

## Pasos

1. **Fuente** `StoreApp/domains/design/sources/aurum.html`
   - Mismo lenguaje visual del boceto (tinta + champagne/dorado, Fraunces +
     Inter + JetBrains Mono, índices numerados, grano, reveal).
   - Placeholders `{{…}}` del contrato (store_*, offerings, stats, benefits,
     categories, products, gallery, timeline, team, testimonials, plans, faqs,
     video_url, cta_*, footer_text, year, product_*, services, announcements).
   - Zonas `.ds-zone` + regla `[data-flag]:has(.ds-zone:empty){display:none}`.
   - `data-flag` con los nombres de `_page_flags` (catalog, services, plans,
     contact, gallery, hours, benefits, stats, testimonials, faq, timeline,
     team, cta, announcements, video, about, location).
   - Superficies `data-surface`: landing / catalog / services / product.
   - Catálogo con hooks del puente (`data-ds-filters`, `data-ds-brands`,
     `data-ds-price-*`, `data-ds-offers`, `data-ds-sort`, `data-ds-view`,
     `data-ds-count`, `data-ds-products`, `data-ds-noresults`,
     `data-ds-crumb`, `data-ds-clear`, `data-ds-filters-*`).
   - PDP con `{{product_*}}` + `{{product_reviews}}` + `{{product_related}}`.
   - Menú móvil: tab bar + hoja (`m-tabs`, `m-sheet`, `data-m-open/close`,
     `data-ds-route`, `m-lock`).
   - Tokens del tema: `--ds-accent`, `--ds-radius`, `--ds-bg/surface/text/
     muted/border`; modo claro/oscuro con `html[data-ds-theme]` y
     `html[data-ds-style="aurum-dia"]` (variante clara).

2. **Backend** `StoreApp/domains/stores/models/models.py`
   - `TEMPLATE_ADVANCED = ('aurum',)` + entrada en `TEMPLATE_CHOICES`
     (label "Áurea"). `makemigrations` + `migrate`.

3. **Seed** `StoreApp/domains/design/seed_data.json`
   - Patrón `aurum` (nombre "Áurea", categoria `premium`, tier `advanced`,
     template `aurum`, style `aurum`, tags generalistas).
   - Estilos `aurum` (oscuro/dorado) y `aurum-dia` (hueso/dorado), ambos
     `pattern: "aurum"`, tier `advanced`.
   - `manage.py seed_design_catalog`.

4. **Frontend** `frontend/src/api/stores.api.js`
   - `STORE_TEMPLATES.aurum` (tier `advanced`, rubro `general`).
   - Familia `premium` en `STORE_TEMPLATE_FAMILIES`.
   - `STORE_TEMPLATE_SKIN.aurum = 'raiz'` y `STORE_TEMPLATE_RENDER.aurum =
     'raiz'` (el chrome Vue cae a Raíz; el documento del patrón manda).

5. **Verificación**
   - Asignar `template='aurum'` a `bench-store`, levantar `runserver` y abrir
     `/api/stores/public/bench-store/pattern/document/` en el preview.
   - `manage.py check`.
