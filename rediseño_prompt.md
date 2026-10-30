# REDISEÑO PROFUNDO — PLANTILLAS, CATÁLOGO DE DISEÑO Y STUDIO

> Archivo de trabajo obligatorio. Cada tarea terminada se marca con **(TERMINADO)** al lado.
> El próximo agente continúa desde la primera tarea sin marcar. No borrar el historial.
> Este documento **rompe** las reglas anteriores del sistema de bloques y del catálogo de pieles.

---

## 0. Reglas nuevas (rompen las viejas)

1. **El diseño es HTML + CSS + JS con variables.** `DesignPattern` guarda tres campos:
   `html`, `css`, `js`. El markup trae placeholders (`{{store_name}}`, `{{hero_title}}`,
   `{{products}}`, etc.) y el CSS trae custom properties (`--ds-accent`, `--ds-radius`,
   `--ds-surface`, `--ds-ink`…). Nada de "bloques" ni de `layout_config` como fuente de
   composición.
2. **`DesignStyle` ya NO define layout ni composición.** Solo puede tocar:
   bordes (radio, grosor, estilo), colores (paleta/tokens de color) y detalles básicos
   (sombra, densidad de espacio, tratamiento tipográfico de acento). Nunca estructura,
   nunca HTML, nunca orden de secciones. Un estilo que intente algo fuera de eso se recorta.
3. **Cada diseño organiza los datos de la empresa de forma única** (no genérica):
   portada, catálogo y servicios propios, responsive real, sin bloques intercambiables.
4. **Todas las webs tienen modo noche** (toggle visible siempre + `prefers-color-scheme`),
   con contraste AA en ambos modos.
5. **Los iconos del menú/controles son un catálogo aparte** (`DesignIconStyle`): el diseño
   trae un set por defecto y el usuario puede cambiarlo sin tocar el diseño.
6. **El Studio se rediseña** para operar sobre el nuevo contrato (elegir diseño, estilo,
   iconos, modo noche, previsualizar y publicar) y se cubre con tests.
7. Prohibido documentar patrones nuevos en `.md` sueltos: la única fuente de verdad de
   este rediseño es este archivo + el código.

---

## 1. Estado actual / mapa del código

- Backend diseño: `StoreApp/domains/design/` (`models/models.py`, `serializers/`,
  `views/`, `urls/`, `seed_data.json`, `management/commands/`).
- Backend tienda: `StoreApp/domains/stores/` (`models/models.py`,
  `layout_blocks.py`, `site_theme.py`, `services/`).
- Frontend público: `frontend/src/views/StorePublicLayout.vue`,
  `frontend/src/templates/`, `frontend/src/views/store/<diseño>/`,
  `frontend/src/components/store/blocks/`, `frontend/src/assets/store-*.css`.
- Studio: `frontend/src/components/studio/StudioShell.vue`,
  `frontend/src/composables/useStudioDesign.js`,
  `frontend/src/views/DesignStudioView.vue`,
  `frontend/src/components/design/*`.
- Comandos: `venv/Scripts/python.exe manage.py <cmd>` desde la raíz.

---

## 2. Tareas

### FASE 0 — Limpieza y contrato escrito

- [x] Borrar los `.md` que fijaban los patrones de diseño viejos (`docs/AI_DESIGN_STYLES_PROMPT.md`,
  `docs/PLANTILLAS_GENERATIVAS.md`, `docs/PLANTILLAS_INTERFAZ.md`,
  `docs/PROMPT_DISENO_IA_V6_BRIEF.md`, `docs/PROMPT_DISENO_NO_GENERICO.md`,
  `docs/PROMPT_REDISENO_PLANTILLAS.md`, `docs/PROMPT_FIX_DISENO_IA.md`,
  `docs/PROMPT_RAIZ_CORRECCION_PROFUNDA.md`, `docs/REPARTO_AGENTES_V6.md`,
  `docs/ref/FRONTEND_PLANTILLAS.md`, `docs/ref/MOTOR_IA_INVENTARIO.md`,
  `docs/ORQUESTACION_MEJORA_DISENO_IA.md`, `docs/IDEAS_MEJORA_DISENO_IA.md`,
  `docs/PROMPT_AGENTES.md`, `qa_studio_inventory.md`). **(TERMINADO)**

### FASE 1 — Contrato de datos (backend)

- [x] `DesignPattern`: `html`/`css`/`js` como plantillas con variables + declaración
  `variables` (JSON) + `supports_dark_mode` + `icon_style` (FK opcional).
  **(TERMINADO)** — `clean_pattern_variables` + `DesignPattern.render()` (escapa todo,
  descarta variables no declaradas y nombres reservados).
- [x] `DesignStyle`: campo `effects` (JSON) limitado a bordes/colores/básicos + saneador
  `clean_style_effects` (recorta cualquier clave estructural). **(TERMINADO)**
- [x] Nuevo modelo `DesignIconStyle`: set de iconos de controles de menú
  (`home`, `catalog`, `services`, `contact`, `search`, `cart`, `menu`, `close`,
  `theme`, `whatsapp`, `phone`, `instagram`, `facebook`, `tiktok`), con `svg`/`paths`,
  `stroke_width`, `preview`, `is_default`, `is_active`, `position`.
  **(TERMINADO)** — `clean_icon_set` solo acepta path data SVG; seed `seed_icon_styles`
  con 4 sets (lineal/grueso/minimal/relleno).
- [x] `StoreCustomization.icon_style` (slug, vacío = hereda el del diseño). **(TERMINADO)**
- [x] Migraciones + serializers + viewsets + endpoints (`/api/design/icon-styles/`,
  `default`, catálogo) + seed. **(TERMINADO)** — `/api/design/catalog/` ahora devuelve
  `icon_styles` y `default_icon_style`; `sync_design_neon` replica el set.
- [x] Tests de contrato (variables, efectos recortados, icon styles). **(TERMINADO)**
  `DesignContractTests` (7 tests) + `test_icon_style_is_a_catalog_choice`.

### FASE 2 — Modo noche universal

- [x] Toggle visible en TODAS las webs (sin depender de `has_design_advanced`).
  **(TERMINADO)** — `showThemeToggle` ya no depende del plan; `theme_toggle` default True.
- [x] Persistencia por tienda + respeto de `prefers-color-scheme` + `color-scheme`.
  **(TERMINADO)** — la infraestructura ya existía (`davent:store-theme:<slug>`).
- [x] Revisar contraste AA de las pieles activas en oscuro. **(TERMINADO)** —
  auditoría real en navegador de las 32 familias (`qa_skin_dark.py`, payload de
  bench-store servido por `route()` para no gastar el throttle `store_visit`)
  a 1360 y 390: 0 fallas tras corregir (a) las placas amarillas de `seguridad`
  —`.sg-btn--yellow`, `.sp-captcha-q`, `.sg-cats .sp-shop-dept-count`,
  `.sg-card-specs li`, `.sp-form-badge`, `.sg-cat-note`, `.sg-cat-summary`,
  `.sp-hl-icon`, sellos `.rz-pdp-seal`, pasos `.rz-sv-item-num`, hover de
  `.sg-btn--ghost`/`.sp-icon-btn`/`.sp-burger`, `::selection`, que quedaban a
  1.42 por la tinta clara del modo noche—, (b) el texto del CTA y
  `.sg-eyebrow--light` sobre la banda de acento (usaban tinta fija #151515 /
  amarillo y quedaban a 3.5 y 4.02: ahora `--sp-on-band`), y (c) el chip
  `.sp-eyebrow`/`.sp-badge` de la piel `pop` (1.07 por la tinta de banda del
  tema publicado: recupera su par ink/bg).
- [x] Test de render (clase/tema y persistencia). **(TERMINADO)** —
  `frontend/tests/store-theme.test.js` (6 tests) sobre `utils/storeTheme.js`
  (`resolveStoreTheme`, `readVisitorTheme`, `persistVisitorTheme`), que ahora
  usa `StorePublicLayout`.

### FASE 3 — Retiro del sistema de bloques

- [x] `layout_config` deja de componer la web: se ignora en el render público
  (se sigue aceptando por compatibilidad, sin efecto). **(TERMINADO)** —
  `resolveLayout()` devuelve la composición canónica de la plantilla.
- [x] Cada `views/store/<diseño>/InicioView|CatalogoView|ServiciosView` compone sus
  secciones fijas (sin `useLayout`, sin `blocks.js`). **(TERMINADO)** —
  `templates/index.js` expone `templateBlocks(id, surface)` / `templateBlock(id,
  surface, id)`; las 9 portadas, `StoreCatalogView`, `raiz/ServiciosView`,
  `alimentos/AlHistory` y `BlkHighlights` leen la composición de la plantilla.
  `composables/useLayout.js` eliminado. Tests: `tests/store-layout.test.js`.
- [x] Retirar `TEMPLATE_BLOCKS`/`clean_layout_config` del camino crítico y el editor de
  bloques del Studio. **(TERMINADO en UI)** — se quitó la sección "Bloques" del panel,
  el panel Distribución del Studio y su entrada del buscador; el backend sigue
  aceptando `layout_config` sin aplicarlo.
- [x] Limpiar tests y referencias. **(TERMINADO)** — `resolveLayout` ya no acepta
  config (delega en `templateBlocks`), `useLayout.js`, `LayoutEditor.vue` y
  `DistribucionPanel.vue` eliminados (código muerto); `blocks.js` queda solo
  como catálogo de ids/etiquetas del panel.

### FASE 4 — Rediseño de plantillas (landing, catálogo, servicios)

- [x] Nuevo render por diseño a partir de `DesignPattern.html/css/js` con variables
  resueltas contra los datos de la tienda. **(TERMINADO)** — server-side:
  `StoreApp/domains/design/services/pattern_render.py` (`build_store_context`,
  `theme_css`, `pattern_for_template`, `render_store_pattern`) +
  `GET /api/stores/public/<slug>/pattern/` (AllowAny, `has_public_link`, cache
  por `public_cache_stamp`, honra `?preview=`). `DesignPattern.render(ctx, raw)`
  acepta fragmentos de lista ya escapados; el texto se sigue escapando.
  Frontend: `api/stores.api.js#publicPattern`, `components/store/PatternSurface.vue`
  (iframe `srcdoc` sin `allow-same-origin`, alto por postMessage, tema por
  postMessage) montado en `StorePublicLayout` cuando el patrón declara
  `variables` (`ready`), con toggle de modo noche flotante; en el Studio y para
  patrones sin contrato se sigue usando la plantilla Vue. QA headless a
  1360/390 en claro y oscuro: 0 scroll horizontal, 0 errores de consola.
- [x] Convertir `raiz` al contrato de variables (referencia). **(TERMINADO)** —
  fuente editable en `StoreApp/domains/design/sources/raiz.html` (doc completo,
  `{{store_*}}` + `{{products}}`/`{{categories}}`, `--ds-accent`/`--ds-radius`,
  modo noche por `prefers-color-scheme` + `html[data-ds-theme]`); el seed se
  regenera con `seed_design_catalog --patterns-only` y `variables` viaja en
  `seed_data.json`. Fragmentos con clases `ds-*` (producto, categoría, servicio,
  galería, vacío).
- [x] Convertir los 8 patrones restantes (`alimentos`, `trama`, `indumentaria`,
  `boutique`, `atelier`, `clasico`, `circuito`, `seguridad`) al mismo contrato.
  **(TERMINADO)** — fuente editable `sources/<slug>.html` para los 9 patrones;
  `seed_design_catalog` parte la fuente (`services/source_document.py`) y
  **deriva `variables` de los placeholders reales** (solo claves del contrato),
  así el seed no puede declarar lo que el diseño no pinta. Cada diseño trae
  composición propia (pizarra/editorial/vitrina/boutique/arco/ledger/consola/
  protocolo), fragmentos `ds-*` estilados, `--ds-accent`/`--ds-radius`, modo
  noche por `prefers-color-scheme` + `html[data-ds-theme]` y responsive
  360→1920. `usePattern` ahora solo pinta la portada (`store-public`): catálogo,
  ficha y servicios siguen con la plantilla Vue. QA `qa_patterns.py` (9 × 2
  temas × 6 anchos): 0 scroll horizontal, 0 errores de consola; `manage.py test
  StoreApp.domains.design` 37 OK; `vitest` 25 OK; `sync_design_neon` de los 9.
- [ ] Landing única por rubro (composición propia, no genérica).
- [ ] Catálogo único por rubro (filtros, orden, vacíos, responsive).
- [ ] Servicios único por rubro (selector, presupuesto, CTA).
- [ ] Responsive 360/390/768/1024/1360/1920 sin scroll horizontal.
- [ ] QA visual y de estados vacíos.

### FASE 5 — Catálogo de estilos de iconos

- [x] Endpoint público del catálogo + selector en el panel/Studio. **(TERMINADO)**
  Select "Iconos del menú" en `DesignStylesTab`; `useDesignCatalog` expone `iconStyles`.
- [x] Aplicación en el chrome (menú superior, barra móvil, botones de control).
  **(TERMINADO)** — `provide('storeIconSet')` + `AppIcon` pinta el path del set con alias
  semánticos (`x→close`, `moon→theme`, `package→catalog`…).
- [x] El usuario puede cambiar el set sin tocar el diseño; fallback al del diseño.
  **(TERMINADO)** — `storeIconSet` usa `custom.icon_style` y, si está vacío, el
  `icon_style` del patrón base.

### FASE 6 — Studio

- [ ] Rediseño del Studio sobre el nuevo contrato: diseño, estilo (bordes/colores),
  iconos, modo noche, preview real, guardar/publicar.
- [ ] Quitar paneles del sistema de bloques.
- [ ] Tests de guardado/publicación y de gating por plan.

### FASE 7 — Verificación

- [x] `venv/Scripts/python.exe manage.py test StoreApp.domains.design StoreApp.domains.stores`
  **(TERMINADO)** — design: 20 tests OK; stores: 164 tests OK.
- [x] `venv/Scripts/python.exe manage.py check` **(TERMINADO)** — 0 issues.
- [x] `npm run verify:studio` + `npx vitest run` en `frontend/` **(TERMINADO)** — 15 tests OK.
- [ ] QA visual con navegador headless (consola limpia, sin 404 de assets). **PENDIENTE**
  (el build de Vite solo compila con `TMP` local por el temp de esbuild en Windows).

---

## 2.b Estado para el próximo agente

**Hecho y verificado:** contrato de datos (Fase 1), modo noche universal
(Fase 2 completa), catálogo + aplicación de iconos (Fase 5 completa), retiro
del sistema de bloques del render, del Studio y de las vistas (Fase 3
completa), documentación vieja borrada (Fase 0).

**Falta lo pesado:** Fase 4 (rediseñar landing/catálogo/servicios de cada diseño
sobre `DesignPattern.html/css/js` con variables: el pipeline ya está y `raiz` es
la referencia; faltan los otros 8 patrones) y Fase 6 (rediseño profundo del
Studio). Antes de tocar el render, leer `StoreApp/domains/design/models/models.py`
(`DesignPattern.render`), `frontend/src/templates/index.js` (`resolveLayout`) y
`frontend/src/views/StorePublicLayout.vue` (`provide('storeIconSet')`).

## 3. Bitácora

- (2026-10-30) Se crea este archivo. Arranca Fase 0 y Fase 1.
- (2026-10-30) Fase 0 completa. Fase 1 completa (modelos, migraciones 0004 design /
  0059 stores, API, seed, tests). Fase 2: toggle universal. Fase 5: catálogo y
  aplicación de iconos en el chrome. `vite build` falla en esta máquina por
  `Acceso denegado` de esbuild sobre el temp de Windows (no por el código).
- (2026-10-30) Fase 3 (UI + render): `resolveLayout` ignora `layout_config`; sin
  sección "Bloques" ni panel "Distribución" en el Studio. `vite build` OK con
  `TMP` local (el temp de Windows de esbuild da "Acceso denegado").
- (2026-10-30) Contraste AA en oscuro: auditoría de las 32 pieles con
  `qa_skin_dark.py` (bench-store, payload interceptado) → placas amarillas de
  `seguridad`, CTA/eyebrow sobre la banda y chip de `pop` corregidos; 0 fallas
  a 1360 y 390.
- (2026-10-30) Fase 3 cerrada: `templateBlocks`/`templateBlock` reemplazan
  `useLayout` en todas las vistas públicas; `useLayout.js`, `LayoutEditor.vue` y
  `DistribucionPanel.vue` eliminados. Fase 2: test de tema/persistencia
  (`utils/storeTheme.js`). Fase 5 cerrada (fallback de iconos verificado).
  Vitest 25 tests OK, `verify:studio` OK, `vite build` OK con `TMP` local.
- (2026-10-30) Fase 4 arranca por el render: `services/pattern_render.py` +
  `GET /api/stores/public/<slug>/pattern/` + `PatternSurface.vue` montado en
  `StorePublicLayout` (solo patrones con `variables`, o sea `raiz` por ahora;
  el resto sigue con la plantilla Vue). `DesignPattern.render(ctx, raw)` ahora
  recibe los fragmentos de lista (`products`/`categories`/`services`/`gallery`)
  ya escapados; `seed_design_catalog` persiste `variables` y
  `supports_dark_mode`. `raiz` reescrito en
  `StoreApp/domains/design/sources/raiz.html` (variables + `--ds-*` + modo
  noche). QA: `manage.py test StoreApp.domains.design` 33 OK; stores 607 con
  2 fallas PREEXISTENTES de `ai_design` (verificadas con `git stash`);
  `vite build` OK; `npx vitest run` 25 OK; navegador headless sobre `/demo`
  (payload interceptado por el throttle `store_visit`) en 1360/390, claro y
  oscuro. `sync_design_neon --slug raiz` OK.
- (2026-10-30) Fase 4: los 9 patrones convertidos al contrato de variables con
  fuente editable en `sources/` y variables derivadas del markup. Portada
  propia por rubro; el documento del patrón queda limitado a la portada
  (catálogo/ficha/servicios siguen en la plantilla Vue). QA headless 9×2×6.
- Próximo paso: catálogo y servicios propios por rubro sobre el patrón
  (hoy esas superficies siguen en Vue) y Fase 6 (rediseño del Studio).
