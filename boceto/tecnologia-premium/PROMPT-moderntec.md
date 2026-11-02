# PROMPT — Implementar plantilla `moderntec` (rubro tecnología)

Implementar el diseño `moderntec` (nombre visible: **ModernTec**) como plantilla nueva del catálogo, portando el boceto `boceto/tecnologia-premium/index.html` al sistema de plantillas DAVENT. Es el **segundo** diseño del catálogo (hoy solo existe `raiz`).

## Dirección visual (del boceto, ver index.html)
- Oscuro tecnológico: fondo `#07090d`, panel `#0e141e`, líneas `rgba(255,255,255,.08)`.
- Acento dual: cyan `#3dd6ff` + violeta `#7c5cff`; ink sobre acento `#04121a`; ok `#34e0a1`.
- Tipografía: `Space Grotesk` (display) + `Inter` (cuerpo) + `JetBrains Mono` (etiquetas/specs/chips).
- Rasgos: grilla de fondo con máscara radial, chips mono uppercase, specs en filas mono, tarjetas con borde fino y glow sutil, botones píldora con glow en el primario.

## Backend — `StoreApp/domains/stores/models/models.py`
- `TEMPLATE_MODERNTEC = 'moderntec'`; agregar a `TEMPLATE_CHOICES`: `('moderntec', 'ModernTec')`.
- Nivel: `tier: 'plus'` → sumar `'moderntec'` a `TEMPLATE_PLUS` (requiere `has_design_plus`, Estándar). Ajustar el comentario del bloque (ya no es "UN solo diseño").
- Migración: `makemigrations` + `migrate`.

## Frontend — registro (espejo del backend)
- `frontend/src/api/stores.api.js`:
  - `STORE_TEMPLATES.moderntec = { label: 'ModernTec', rubro: 'tecnologia', tier: 'plus', defaultAccent: '#3dd6ff', desc: 'ModernTec: oscuro tecnológico, acento cyan/violeta — tiendas de tecnología, electrónica y gaming.' }`
  - `STORE_TEMPLATE_FAMILIES`: agregar `{ key: 'tecnologia', label: 'Tecnología', caption: 'Electrónica y gaming', templates: ['moderntec'] }` o sumar `moderntec` a una familia existente.
  - `STORE_TEMPLATE_SKIN.moderntec = 'moderntec'`.
- `frontend/src/views/StorePublicLayout.vue`: `TEMPLATE_CSS.moderntec = () => import('../assets/store-moderntec.css')`.
- `frontend/src/templates/_shared.js`: loaders `landingViews/catalogViews/productViews/servicesViews` → `views/store/moderntec/{InicioView,CatalogoView,ProductoView,ServiciosView}.vue`.
- `frontend/src/templates/moderntec/index.js`: `fonts: ['space-grotesk', 'jetbrains-mono']` (verificar slugs del catálogo de fuentes / FONT_CHOICES; Inter ya va en index.html); `blocks.landing` canónico; catalog `CATALOG_BLOCKS`; services `SERVICES_BLOCKS`.
- `frontend/src/templates/index.js`: `import moderntec from './moderntec/index.js'` + `TEMPLATE_DEFS.moderntec`.

## Vistas — `frontend/src/views/store/moderntec/`
- `InicioView.vue`: portada propia estilo boceto — hero con chip mono, título con gradiente cyan→violeta en la palabra clave, CTAs (catálogo / asesoría), meta-stats mono, y tarjeta "device" lateral con specs del producto destacado (o specs de la tienda) + badge STOCK.
- `CatalogoView.vue` / `ProductoView.vue` / `ServiciosView.vue`: reutilizar las vistas de `raiz` bajo la clase de piel `.mt-skin` (como hace `sastreria`/`atelier` en el esquema documentado) o portarlas si hace falta markup propio para la estética marketplace-tech (tarjetas producto con tag mono + precio + ● EN STOCK).

## Piel — `frontend/src/assets/store-moderntec.css`
- Tokens `--st-*` del contrato (paleta oscura, acento cyan, `--st-accent-ink`, fuentes heading/body).
- Chrome (header/nav/footer/drawer/tabbar) eskinado a dark + línea fina + blur.
- Prefijos propios `mt-*`; respetar scoping `[data-template='moderntec']` / `data-skin`; reglas `[data-st-font-*]` con `!important` según el patrón de `store-raiz.css`.
- `prefers-reduced-motion`: apagar el conic-spin del device y glows animados.

## Dominio Design (catálogo en base)
- `StoreApp/domains/design/seed_data.json`: `DesignPattern` `moderntec` (tags: tecnologia/electronica/gaming, `template: 'moderntec'`, `tier: 'plus'`, layout por superficie) + `DesignStyle`(s) `moderntec` (y variante `moderntec-lumen` clara si aplica) con `tokens` del contrato y FK `style`.
- `manage.py seed_design_catalog --patterns-only` (o completo).
- **Neon obligatorio**: `manage.py sync_design_neon --slug moderntec` (patrón y estilos).

## Verificación
- `venv/Scripts/python.exe manage.py check` y test del dominio stores/design.
- `npm run build` en `frontend/` y preview visual de la tienda con `template=moderntec`.
- Commit + push: `feat: add moderntec template (tech)`.
