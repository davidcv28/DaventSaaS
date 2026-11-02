# Prompt — Rediseño sección "Mi página" del dashboard

Implementá el boceto `docs/prototype/MiPagina-Redesign.html` (referencia visual/UX) dentro de `DashboardView.vue`, reemplazando la sección "Mi página" actual (`tabGroups.web`: `design` + `pages` + `company`) por un único flujo guiado por pasos.

## Estructura

La sección "Mi página" pasa a ser un editor guiado de **4 pasos** con vista previa en vivo siempre visible a la derecha (iframe real de la web del usuario, como `DesignLivePreview`).

### Menú por pasos (reemplaza `SectionTabs` interno)
1. **Diseño** — "Cómo se ve"
2. **Qué muestra** — "Sus secciones"
3. **Mi negocio** — "Tus datos"
4. **Contenido** — "Textos y páginas"

Cada paso completado muestra check; barra sticky inferior con estado de autoguardado y botón "Siguiente paso".

## Paso 1 — Diseño (simplificado)

- Eliminar por completo la sección "Plantillas" (`pages`) y los tabs `designTabs` (look/assisted/studio) de esta vista. La ruta `design-studio` y `DesignStudioView` quedan solo para planes con `has_design_advanced` vía CTA externo, fuera del flujo.
- El usuario solo elige:
  - **Diseño** → tarjetas de `DesignPattern` (nombre, descripción corta, thumbnail). Escribe `template` + `layout_config`.
  - **Estilo** → swatches de los `DesignStyle` asociados al diseño (FK `style` del patrón + hermanos activos). Escribe `site_theme` completo (paleta + tipografía + contenedores + modo, como hoy aplica un tema entero).
- Sin selectores de tipografía sueltos, sin uploads: logo/portada van al paso 3. `typography.subheading` y los demás controles finos quedan solo en Studio.
- Misma savebar/autoguardado que hoy (`PATCH /api/stores/customization/` con `clean_site_theme` + `clean_layout_config`).

## Paso 2 — Qué muestra

- Las secciones disponibles **las define el diseño elegido**: se leen los bloques de `layout.landing.blocks` del `DesignPattern` (ids canónicos). Ej.: `destacados`, `catalogo`, `servicios`, `info` (ubicación+horarios), `contacto`, `suscripciones`, `faq`.
- Toggles para activar/desactivar cada bloque visible. **Regla dura: al menos 1 siempre activa** — si intenta apagar la última, aviso inline ("Tu web necesita al menos una sección visible") y no se aplica.
- Escribir en `layout_config` (bloques `enabled`) vía el PATCH de customization; la preview refleja al instante.

## Paso 3 — Mi negocio (datos ampliados)

Sub-pestañas internas (chips), cada una un form corto. Reusar endpoints existentes: customization (`display_name`, `whatsapp`, `hours`, `description`, logo/cover) + perfil (`business_name`, `province`, `city`):

- **Identidad**: nombre del negocio, rubro (catálogo `R.RUBROS`), descripción corta (≤160), logo, foto de portada (upload con compresión client-side, handlers `onLogoPicked`/`onCoverPicked`).
- **Contacto**: WhatsApp (botón principal), teléfono fijo opcional, email público + toggle "mostrar en la web".
- **Ubicación**: provincia, ciudad, dirección, toggle "mostrar mapa", zona de entrega (texto libre).
- **Horarios**: texto de atención, toggle feriados, aviso especial (ej. vacaciones).
- **Pagos y envíos** (nuevo): medios de pago aceptados (chips multi: efectivo, Mercado Pago, transferencia, tarjetas, Cuenta DNI), toggle "hace envíos", costo/condición de envío.
- **Redes y links**: Instagram, Facebook, TikTok, link externo.

Los campos nuevos (email público, teléfono fijo, dirección+mapa, zona de entrega, feriados, aviso, medios de pago, envío, redes) se agregan al contrato de customization/perfil — definir keys nuevas en `_SECTION_SPECS` + `contract.js` y exponerlas en la web pública (sección "info"/contacto/footer).

## Paso 4 — Contenido (unificado)

Un solo acordeón que agrupa lo que hoy está disperso en landing/servicios/catálogo/suscripciones:

- **Portada**: título de bienvenida, texto, texto del botón CTA.
- **Catálogo**: título de sección, orden (más vendidos/nuevos/precio), toggles mostrar precios y ofertas + botón "Administrar" → navega a `catalogs`.
- **Servicios**: título, texto del botón de consulta + "Administrar" → `services`.
- **Suscripciones/membresías**: título + descripción + "Administrar".
- **Preguntas frecuentes** (opcional).

## Reglas

- Preview = iframe real de la web pública (no mock). Autoguardado con feedback "Guardando… / Guardado".
- Gates por plan igual que hoy: sin `has_customization` se muestra la tarjeta bloqueada (`LOCKED_FEATURES`).
- Los `show_*`/`site_templates` existentes se mapean a los bloques del paso 2/4; la pestaña vieja "Qué mostrar" desaparece absorbida.
- Copy en voseo argentino, tono simple (usuario no técnico), estilo `dashboard.css` existente.
- Tests: ajustar `StoreApp/domains/stores` tests de customization si cambia el contrato; `manage.py test StoreApp.domains.design` debe seguir verde.
