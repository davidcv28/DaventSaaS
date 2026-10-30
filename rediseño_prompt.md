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
- [ ] Revisar contraste AA de las pieles activas en oscuro.
- [ ] Test de render (clase/tema y persistencia).

### FASE 3 — Retiro del sistema de bloques

- [x] `layout_config` deja de componer la web: se ignora en el render público
  (se sigue aceptando por compatibilidad, sin efecto). **(TERMINADO)** —
  `resolveLayout()` devuelve la composición canónica de la plantilla.
- [ ] Cada `views/store/<diseño>/InicioView|CatalogoView|ServiciosView` compone sus
  secciones fijas (sin `useLayout`, sin `blocks.js`). **PENDIENTE**: hoy `useLayout`
  sigue leyendo `blocks.<superficie>` de la plantilla (composición fija, sin config).
- [x] Retirar `TEMPLATE_BLOCKS`/`clean_layout_config` del camino crítico y el editor de
  bloques del Studio. **(TERMINADO en UI)** — se quitó la sección "Bloques" del panel,
  el panel Distribución del Studio y su entrada del buscador; el backend sigue
  aceptando `layout_config` sin aplicarlo.
- [ ] Limpiar tests y referencias.

### FASE 4 — Rediseño de plantillas (landing, catálogo, servicios)

- [ ] Nuevo render por diseño a partir de `DesignPattern.html/css/js` con variables
  resueltas contra los datos de la tienda (server-side o cliente, según contrato de Fase 1).
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
- [ ] El usuario puede cambiar el set sin tocar el diseño; fallback al del diseño.

### FASE 6 — Studio

- [ ] Rediseño del Studio sobre el nuevo contrato: diseño, estilo (bordes/colores),
  iconos, modo noche, preview real, guardar/publicar.
- [ ] Quitar paneles del sistema de bloques.
- [ ] Tests de guardado/publicación y de gating por plan.

### FASE 7 — Verificación

- [ ] `venv/Scripts/python.exe manage.py test StoreApp.domains.design StoreApp.domains.stores`
- [ ] `venv/Scripts/python.exe manage.py check`
- [ ] QA visual con navegador headless (consola limpia, sin 404 de assets).

---

## 3. Bitácora

- (2026-10-30) Se crea este archivo. Arranca Fase 0 y Fase 1.
- (2026-10-30) Fase 0 completa. Fase 1 completa (modelos, migraciones 0004 design /
  0059 stores, API, seed, tests). Fase 2: toggle universal. Fase 5: catálogo y
  aplicación de iconos en el chrome. `vite build` falla en esta máquina por
  `Acceso denegado` de esbuild sobre el temp de Windows (no por el código).
- (2026-10-30) Fase 3 (UI + render): `resolveLayout` ignora `layout_config`; sin
  sección "Bloques" ni panel "Distribución" en el Studio. `vite build` OK con
  `TMP` local (el temp de Windows de esbuild da "Acceso denegado").
- Próximo paso: Fase 3 (limpieza de `useLayout`/`blocks.js` en las vistas) y Fase 4
  (render por `DesignPattern.html/css/js` con variables).
