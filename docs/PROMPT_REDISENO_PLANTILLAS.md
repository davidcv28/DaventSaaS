# PROMPT — Rediseño de plantillas de tienda (3 diseños por rubro)

> **Cómo usar:** pegar este archivo completo como prompt inicial del agente. Adjuntar (o dejar en el escritorio) el HTML y el ZIP de referencia. Trabajar por diseño en commits separados.

---

## 1. Rol

Sos un ingeniero frontend + diseñador de producto en el repo **SaaS DAVENT** (Django + DRF + Vue 3 + Vite). Conocés las reglas de `AGENTS.md` (economía de tokens, commits obligatorios, catálogos cerrados, gating por beneficios, fail-closed). No inventás arquitectura: extendés la existente.

## 2. Objetivo

Reemplazar **todos los estilos prediseñados** de la web pública del cliente (portada, catálogo, ficha de producto y servicios) por **3 diseños nuevos**, cada uno pensado para un **tipo de empresa (rubro)**. El catálogo de diseños pasa a organizarse por rubro, no por “estilo de autor”.

Los 3 diseños de esta fase, y únicos que se implementan:

| id | Nombre | Rubro | Nivel | Fuente de verdad visual |
|---|---|---|---|---|
| `raiz` | **Raíz** | Generalista / retail / servicios | `base` | `Inicio · escritorio.png`, `Inicio · móvil.png`, `Catálogo · escritorio.png`, `Servicios · escritorio.png` |
| `trama` | **Trama** | Indumentaria / moda | `plus` | `Estilo indumentaria · Inicio.png` |
| `circuito` | **Circuito** | Tecnología / electrónica | `advanced` | `Estilo tecnología · Inicio.png` |

Nada más. Comida, bebida, belleza, etc. quedan para fases siguientes: el sistema debe quedar preparado para sumar rubros sin tocar el render de estos 3.

## 3. Material de referencia (leer antes de codear)

- `C:\Users\David\OneDrive\Escritorio\Landing de tienda DAVENT.html` — bundle autocontenido con las 6 pantallas renderizadas. Al abrirlo se ven lado a lado (anchos 1360 / 390). **No** copiar su markup: es una exportación de design-components con estilos inline, `{{placeholders}}` y `<sc-for>`; sirve como referencia de medidas, jerarquía, color y copy.
- `C:\Users\David\OneDrive\Escritorio\Landing de tienda DAVENT-png.zip` — capturas @2x de cada pantalla: `Inicio · escritorio`, `Inicio · móvil`, `Catálogo · escritorio`, `Servicios · escritorio`, `Estilo indumentaria · Inicio`, `Estilo tecnología · Inicio`.
- Código actual: `frontend/src/templates/`, `frontend/src/views/StorePublic*.vue`, `frontend/src/assets/store-*.css`, `frontend/src/api/stores.api.js`, `StoreApp/domains/stores/`.

Reglas de fidelidad:
1. Reproducir la composición, tipografía, color, radios y densidad de la referencia en **1360 px** y **390 px**.
2. Los textos de la referencia son placeholders; en producción se reemplazan por datos reales de la tienda. No hardcodear copy de marketing.
3. Las imágenes de la referencia son bloques de color con rótulo; en producción usan logo/portada/galería/productos de R2. Sin imagen → bloque tonal + ícono, nunca texto de “Foto de…”.

## 4. Alcance

**Dentro:**
- Las 3 plantillas como *Template Definitions* completas: Inicio, Catálogo, Ficha de producto, Servicios, header, footer, barra inferior móvil, estados vacíos/carga/error.
- Selector del panel y previews agrupados por rubro.
- Retiro del catálogo viejo: `classic`, `duo`, `calma`, `vitrina`, `cobre`, `minimal`, los 20 diseños retirados y los patrones IA `ai_lumen` / `ai_pulse`.
- Migración de datos para que ninguna tienda existente pierda su web.
- Actualización de tests, whitelists, motor de IA (solo compatibilidad) y documentación.

**Fuera:**
- Panel admin, checkout/MP, facturas, emails, cupones, chat, chatbot (solo se re-skinea la burbuja si colisiona visualmente).
- Nuevos campos de datos. Todo el contenido sale de `StoreCustomization`, catálogo, servicios y reseñas ya existentes.
- Diseños de comida/bebida/belleza (solo se deja el registro preparado).
- Rediseño del folleto (`FlyerStudio`): solo verificar que herede acento/fuente correctamente.

## 5. Decisiones de producto (fijas)

- **Tiers:** un diseño por nivel (tabla §2) para conservar la escalera comercial: `base` va con cualquier `has_customization`; `plus` requiere `has_design_plus`; `advanced` requiere `has_design_advanced`. Si el negocio pidiera los 3 en un mismo nivel, se cambia solo `TEMPLATE_BASE/PLUS/ADVANCED` y la tabla `STORE_TEMPLATES`.
- **Fallback global = `raiz`.** Reemplaza a `classic` en TODO el código (backend y frontend): `resolveStoreTemplate`, `allowed_templates_of`, `pageTemplate`, defaults de modelos, migraciones, previews y tests. Grep obligatorio de `'classic'` al terminar.
- **Acento configurable:** cada diseño define su acento por defecto (Raíz `#0F766E`, Trama `#E4472B`, Circuito `#22D3EE`). El `accent` del dueño puede pisarlo, pero el render valida contraste AA y deriva tints (`--accent-soft`, `--accent-strong`, `--on-accent`) — nunca usa el hex crudo sobre fondos sin chequeo. El catálogo de 8 acentos existente se mantiene.
- **Sin edición de orden de bloques:** estos 3 son composiciones fijas. `layout_config` se ignora para ellos (no romper la API: se sigue aceptando y guardando para compatibilidad, pero el render aplica el orden canónico de §7). El Studio de bloques no se ofrece para estas plantillas.
- **`site_theme` / pieles:** en esta fase los 3 diseños **no** consumen pieles del Studio. El motor de IA queda limitado a proponer uno de los 3 templates + acento + copy; no compone pieles. Ver §9.4.
- **Tema claro/oscuro del visitante:** Raíz y Trama son claros; Circuito es oscuro por identidad. El toggle del nav solo aparece si el plan lo habilita hoy (`has_design_advanced`); Circuito no invierte a claro (su paleta oscura es el diseño).

## 6. Sistema de diseño

### 6.1 Raíz — generalista, claro, amable y comercial

```
--bg:#F5F6F3; --surface:#FFFFFF; --surface-2:#E9ECE6; --line:#DCE0DA;
--ink:#17211C; --ink-2:#3C4842; --muted:#5B6660;
--accent:#0F766E; --on-accent:#FFFFFF; --accent-soft:rgba(15,118,110,.12);
--danger:#B42318; --ok:#86EFAC;
```
- **Tipografía:** cuerpo `Manrope` 400/500/600; display `Bricolage Grotesque` 600/700. `h1` `clamp(38px,5vw,60px)/1.02`, tracking `-.02em`; `h2` 38/1.08; `h3` 20; eyebrow 13/700 mayúsculas `+.04em`; cuerpo 16/1.5; precio 22/700.
- **Formas:** pills 999 px (botones/inputs/chips), tarjetas 20 px, media 28 px, logo 10 px. Bordes 1 px `--line`, sombras casi nulas (solo hover).
- **Ritmo:** container 1200 px, gutter 32 px (20 px móvil), secciones 80 px arriba/abajo (48 px móvil), gap de grilla 24 px.
- **Detalle:** hero en banda de acento con texto blanco; cinta de anuncios oscura; botón primario blanco sobre acento y secundario outline blanco; foco visible 2 px `--accent` con offset 2.

### 6.2 Trama — indumentaria, editorial y filosa

```
--bg:#FFFFFF; --ink:#0B0B0B; --ink-2:#3A3A38; --muted:#5C5C5C;
--line:#D8D8D5; --surface-2:#D9D7D2; --accent:#E4472B; --on-accent:#FFFFFF;
```
- **Tipografía:** cuerpo `Archivo` 400/500/600; display `Anton` 400 mayúsculas. `h1` `clamp(56px,11vw,132px)/.86`, tracking `-.01em`; `h2` 52/.92 mayúsculas; títulos de sección 34; eyebrow 12/700 mayúsculas `+.14em`; cuerpo 15/1.55; nombre de producto 13 mayúsculas.
- **Formas:** radio 0 en todo (solo círculos del badge y el punto del logo). Bordes 1 px negro. Sin sombras.
- **Ritmo:** container 1200, gutter 28, secciones 80/44, gap 16–20.
- **Detalle:** header con logo centrado y líneas de 1 px; hero partido 55/45 con borde vertical; palabra acentuada en `--accent`; cinta marquee de acento con ítems separados por `·`; botones rectangulares mayúsculas.

### 6.3 Circuito — tecnología, oscuro y técnico

```
--bg:#0A0E14; --surface:#111823; --surface-2:#0E141D; --line:#1F2933;
--ink:#E6EDF3; --ink-2:#B6C2CF; --muted:#8FA1B3;
--accent:#22D3EE; --on-accent:#04141A; --accent-soft:rgba(34,211,238,.12);
--footer:#070A0F;
```
- **Tipografía:** cuerpo `Space Grotesk` 400/500/600; etiquetas `JetBrains Mono` 400/500. `h1` `clamp(44px,6.4vw,72px)/1.02` tracking `-.02em`; `h2` 40/1.1; labels 12 mono mayúsculas `+.08em`; cuerpo 16/1.55; radios 10 (chips 6, media 14).
- **Ritmo:** container 1200, gutter 32/20, secciones 80/48, gap 20.
- **Detalle:** barra superior de acento con texto tinta oscura; fondo con retícula/glow muy sutil (nunca sobre texto); tarjetas `--surface` con borde 1 px; acento solo en palabras clave, chips y CTA; iconografía lineal 1.5 px.

### 6.4 Primitivas compartidas (las 3)

- Escala de espacio 4/8/12/16/24/32/48/64/80/96.
- Botones: primario, secundario, ghost, icon-btn; altura 44 (48 en hero), `min-width 44`, estados hover/active/focus/disabled/loading.
- Inputs: 44 px, borde 1 px, label flotante o visible (nunca placeholder-only), error inline.
- Badges: `Nuevo`, `-N%`, `Promo`, `Agotado` — color y forma por diseño, mismo contenido.
- Tarjeta de producto: media, badges, categoría·marca, nombre, estrellas, precio (tachado si oferta), nombre de promo.
- Tabs/chips de filtro, `<details>` de FAQ, modal/lightbox de galería, toast, skeleton.
- Foco, `prefers-reduced-motion`, `scroll-margin-top` en secciones con ancla.

## 7. Páginas y secciones

### 7.1 Inicio — orden canónico

**Raíz (14):** header · cinta de anuncios · hero partido (badge, h1, subtítulo, CTA catálogo/servicios/contacto, compartir, meta abierto/ciudad/años, media 4:3) · franja de 4 garantías · categorías (4) · productos recientes (4) · “Lo que hacemos por vos” (3) · beneficios (4 íconos) · marcas (6) · galería (6) · testimonios (3) · FAQ · banda CTA · footer oscuro.

**Trama (12):** barra promo superior · header centrado · hero partido 55/45 · marquee de acento · categorías (4) · nueva temporada (4 productos) · banda lookbook oscura (imagen + copy) · franja de beneficios (4) · looks del mes · FAQ con líneas · banda CTA de acento · contacto + footer.

**Circuito (12):** barra de acento · header oscuro con buscador · hero partido con tarjeta de producto, chip de specs y badge `-N%` · franja de 4 garantías con íconos · categorías (6 en 3×2) · productos destacados (4) · banda de servicios (fondo `--surface-2`) · oferta + countdown · testimonios (3) · FAQ · contacto · footer minimal.

Regla: cada sección se oculta si no tiene contenido (salvo hero y footer). Los `show_*` existentes mandan; la franja de garantías usa `highlights` y el copy de `benefits`/`services` según corresponda.

### 7.2 Catálogo (referencia: Raíz; Trama/Circuito = misma estructura, piel propia)

1. Hero de acento: migas `Inicio / Catálogo`, `h1 Catálogo`, subtítulo, 3 contadores (productos, categorías, marcas).
2. `catalog_note` en tira si existe.
3. Franja de promociones vigentes (`promotions[]`) con chips `Nombre · -N%`.
4. Layout 3 columnas: sidebar 280 fijo con filtros (categoría, marca, precio, atributos con facetas y conteos, “Limpiar”), resultados + selector de orden, grilla de productos.
5. Grilla 3 col (2 en tablet, 1 en móvil); tarjeta con badges, estrellas, precio efectivo y promo.
6. Vacío: mensaje + “Limpiar filtros”. Carga: skeletons. Error: reintento.
7. Paginación/“Ver más” según el comportamiento actual; no cambiar la API.

Comportamiento obligatorio: `?q=`, `?category=`, `?brand=`, `?features=`, `?offer=`, `?new=`, `?min_price/`, `?max_price=`, `?sort=` — todo lo que ya resuelve el backend; la UI solo refleja. Filtros en drawer full-screen < 900 px. La búsqueda del header entra a `/catalogo?q=`.

### 7.3 Ficha de producto

No hay referencia: derivar del catálogo. Conservar la estructura marketplace actual (migas, galería + panel de compra, CTA WhatsApp con mensaje precargado, tabla de características ordenada por `feature_schema`, “También te puede interesar”, reseñas). Re-skinear con los tokens del diseño. La tarjeta entera navega; no reintroducir modal.

### 7.4 Servicios (referencia: Raíz)

Hero de acento (badge “Presupuesto orientativo”, h1, subtítulo) · cinta oscura con nombres de servicios · paso 1 “Elegí tus servicios” (lista con checkbox, precio, descripción) + tarjeta sticky “Tu presupuesto” (líneas, total orientativo, CTA WhatsApp) · “Cómo funciona” (4 pasos) · garantías (3) · trabajos y opiniones · zona y horarios (mapa solo con `show_location`) · FAQ · footer. En móvil el resumen se fija abajo (barra con total + CTA). Trama y Circuito: misma estructura, cambia la piel (Trama sin radios y mayúsculas; Circuito oscuro con mono).

### 7.5 Chrome

- **Header:** logo + nombre, nav (Inicio, Servicios, Catálogo, Nosotros, Galería, Contacto — ocultar los que no existen), buscador, toggle de tema si aplica, CTA “Catálogo”. Sticky solo en scroll hacia arriba, con sombra sutil al fijarse.
- **Footer:** nombre + ciudad, links legales, redes **solo acá y en Contacto**, `footer_text`, “Publicado con DAVENT”.
- **Barra inferior móvil (nueva, solo < 768 px):** Inicio · Servicios · Catálogo · Contacto · Más; safe-area, ícono + label 11 px, activo en acento. No duplicar con el header.

## 8. Datos, estados y reglas

| Contenido | Fuente |
|---|---|
| Nombre, logo, titular, descripción, ciudad/provincia, años | `Store` + `StoreCustomization` |
| Acento, fuente del nombre, tamaño | `accent`, `name_font`, `name_font_size` |
| Anuncios, highlights, stats, servicios, beneficios, marcas, galería, testimonios, FAQ, horarios, CTA, `catalog_note`, `footer_text` | campos existentes de `StoreCustomization` |
| Categorías, productos, ofertas, reseñas, facetas, promos | endpoints públicos del catálogo |
| WhatsApp / redes | `whatsapp`, `instagram`, `tiktok`, `facebook` |

- **Visibilidad:** respetar `show_about`, `show_gallery`, `show_catalog`, `show_contact`, `show_location`, `show_services`, `show_stats`, `show_highlights`, `show_offers`, `show_brands`, `show_countdown`, `show_testimonials`, `show_faq`, `show_hours`, `show_cta`, `show_announcements`, `show_reviews`, `show_comments`. Sin contenido → sección oculta, sin huecos.
- **Gating:** ruta pública 404 si no hay acceso vigente o la tienda está bloqueada; sin `has_customization` no hay web; `show_catalog=false` oculta link/CTA y `/catalogo` redirige.
- **Formularios:** contacto y reseñas con captcha firmado, honeypot y estados de error; nunca deshabilitar el fallback a WhatsApp.
- **Accesibilidad:** foco visible, `aria-label` en icon-buttons, contraste AA 4.5, `<details>` nativos, navegación por teclado en filtros/lightbox, `prefers-reduced-motion` respetado (sin marquees ni autoplay).
- **Performance:** fuentes on-demand (`ensureStoreFont`), imágenes `loading="lazy"` + `decoding="async"` con aspect-ratio fijo (sin CLS), sin JS extra por plantilla, CSS por diseño cargado solo cuando se usa.

## 9. Implementación

### 9.1 Backend (`StoreApp/domains/stores`)

1. `models.py`: `TEMPLATE_CHOICES = raiz/trama/circuito`; `TEMPLATE_BASE=('raiz',)`, `TEMPLATE_PLUS=('trama',)`, `TEMPLATE_ADVANCED=('circuito',)`; `TEMPLATE_AI=()`; `TEMPLATE_RETIRED_MAP` con **todos** los ids viejos (`classic, duo, calma, vitrina, cobre, minimal, perspective, bloque, riso, street, promo, atelier, circuit, arena, mercado, studio, lookbook, shop, boutique, signature, aurora, terminal, terra, lab, carta, proceso, ai_lumen, ai_pulse`) mapeados por afinidad: claros/neutros → `raiz`, editoriales/moda → `trama`, oscuros/técnicos → `circuito`. Default del campo y `template_draft` → `raiz`; `max_length` 12 alcanza.
2. Migración `0053` (siguiente a la 0052): `RunPython` que remapea `template` y `template_draft` de todas las filas + `AlterField`. Idempotente y con reverse no-op.
3. `services.allowed_templates_of`: fallback `('raiz',)`; el resto igual. `pageTemplate`/whitelist público heredan.
4. Serializers/validators: aceptar solo los 3; mensajes en español; `DESIGN_ADVANCED_FIELDS` sin cambios.
5. Tests: actualizar los que nombran templates (`test_template_outside_plan_never_returned`, catálogo cerrado, remap) y agregar: (a) un template viejo en DB se sirve como el nuevo mapeado; (b) plan base nunca recibe `trama`/`circuito`; (c) `allowed_templates` público coincide con el plan.
6. **No** tocar `StoreDailyVisit`, chat, reseñas, descuentos ni facturación.

### 9.2 Frontend

1. `src/templates/index.js`: registro con **3** defs (`raiz`, `trama`, `circuito`) y sus `surfaces`/`fonts`/`blocks`. Borrar los 26 imports viejos y `TEMPLATE_DEFS` heredados.
2. Nuevas vistas por diseño en `src/views/store/<id>/` (`InicioView`, `CatalogoView`, `ServiciosView`, `ProductoView`, `chrome/Header`, `chrome/Footer`, `chrome/MobileTabs`) reusando `storePage` (contexto de `StorePublicLayout`) y los composables/API existentes. Nada de fetching nuevo.
3. CSS por diseño: `src/assets/store-raiz.css`, `store-trama.css`, `store-circuito.css`, con raíz `[data-template="raiz"]` y variables `--rz-*`, `--tr-*`, `--ci-*`. Eliminar el CSS de pieles viejas (bloque “Diseños v2” de `store-page.css`, `store-page-v2.css`, `store-bloque.css`, `store-terra.css`, `store-riso.css`, `store-gamer.css`, `store-circuit.css`, `store-studio.css`, `store-mercado.css`, `store-atelier.css`, `store-ofertas.css`, `store-ai-*.css`, `store-belleza.css`, `store-lifestyle.css`, `store-hogar.css`, `store-tpl-card.css`) y las clases `.sp-cb-*`, `.sp-cm-*`, `.sp-vt-*`, `.sp-mn-*`, `.sp-du-*`. Conservar el CSS funcional (layout base, modales, bot, reseñas, catálogo, servicios) y migrarlo a las nuevas raíces.
4. `api/stores.api.js`: `STORE_TEMPLATES` con `{label, rubro, tier, desc, defaultAccent}`; `STORE_TEMPLATE_FAMILIES` pasa a grupos por rubro (`general`, `indumentaria`, `tecnologia`); `allowedTemplatesFor`/`resolveStoreTemplate` con fallback `raiz`; borrar `AI_LEGACY_TEMPLATES`/`AI_EXTRA_TEMPLATES` o dejarlos vacíos.
5. `StorePublicLayout.vue`: elimina `sp-top-links` y monta el chrome del diseño activo; resuelve `data-template`; `StoreHomeView` monta la vista del template (deja de usar `StorePublicView` genérico). Eliminar `StorePublicAltView.vue` y la ruta `/v2`.
6. Panel: `DesignLookTab` agrupa por rubro con tarjeta + miniatura + badge de nivel y candado; `DashboardView.openPreview` apunta a la URL pública real; textos “Diseño web” actualizados.
7. Imágenes: reusar `normalize_image`/R2 tal cual; el render nunca sube nada.

### 9.3 Limpieza

Borrar sin piedad todo lo que quede huérfano: carpetas `src/templates/<viejo>/`, `StorePublicView.vue` si ya no se usa, `StorePublicAltView.vue`, CSS listado, helpers de piel, tests/fixtures con ids viejos, y cualquier `'classic'` hardcodeado. `grep -rn "classic\|ai_lumen\|cobre"` debe volver vacío salvo el mapa de retiro y la migración.

### 9.4 Motor de IA y Studio (compatibilidad, no rediseño)

- `allowed_templates_of` solo devuelve los 3; `TEMPLATE_RETIRED_MAP` ya no se suma a la whitelist de IA.
- El motor puede seguir eligiendo template + acento + copy, pero **no** compone pieles: `_apply_skin_layout` y `SKINS` quedan desconectados del render público en esta fase (dejar el código detrás de un flag y documentarlo; no borrar los datos si se van a reusar).
- Actualizar `tests_ai_design*.py` al catálogo de 3 y verificar que nunca se propone un id retirado.
- `ENGINE_VERSION` sube (`ai-design/7`) porque cambia el contrato de templates.

### 9.5 Folletos

`flyerVars` debe seguir tomando `accent` y `name_font`; los 3 defaults de acento se reflejan. No tocar layouts de folleto.

## 10. QA y aceptación

**Visual**
- [ ] Capturas a 1360 y 390 de Inicio, Catálogo, Producto y Servicios de los 3 diseños, comparadas contra la referencia (layout, tipografía, color, densidad).
- [ ] Sin scroll horizontal en 360/390/768/1024/1360/1920.
- [ ] Nav, hero, grillas y footer correctos con 0, 1 y 12 productos; sin logo; sin portada; sin galería; sin testimonios.
- [ ] Contraste AA en texto normal y grande de las 3 paletas (incluido acento sobre fondo y texto sobre acento).
- [ ] `prefers-reduced-motion`: sin marquees ni autoplay; foco visible en todos los interactivos.

**Funcional**
- [ ] Filtros, orden, búsqueda, facetas, ofertas y promos del catálogo; deep-link `?q=`/`?category=`.
- [ ] WhatsApp con mensaje precargado en producto y servicios; compartir; formulario de contacto con captcha; reseñas con captcha.
- [ ] 404 con tienda bloqueada o sin acceso; `/catalogo` oculto con `show_catalog=false`.
- [ ] Plan base: solo `raiz` visible; `trama`/`circuito` con candado y sin poder guardarse (403 del backend).
- [ ] Tienda existente con `classic`/`cobre`/etc. abre con el diseño remapeado, sin 500.

**Técnico**
- [ ] `venv/Scripts/python.exe manage.py test` verde; `ruff` limpio; `pnpm build` sin warnings nuevos.
- [ ] Bundle: el CSS de un diseño no se carga en los otros dos (verificar en build).
- [ ] `grep` de ids retirados vacío (salvo mapa/migración).

## 11. Entrega

- 4 commits: (1) backend + migración + tests, (2) `raiz`, (3) `trama`, (4) `circuito` + limpieza final. Mensajes conventional en inglés.
- Actualizar la sección de plantillas de `AGENTS.md` (ids, tiers, rubros, fallback `raiz`) y `docs/AI_DESIGN_STYLES_PROMPT.md` si cambia el contrato del motor.
- En el PR: capturas antes/después de las 4 superficies × 3 diseños y checklist de §10 tildado.

---

### Anti-objetivos (si te tienta, no)

- No agregar dependencias (ni Tailwind, ni librerías de animación/iconos).
- No copiar el HTML de referencia con estilos inline ni `{{}}`.
- No dejar dos sistemas de plantillas conviviendo “por las dudas”.
- No tocar la API pública, los permisos ni el modelo de datos más allá del remapeo.
- No “mejorar” el diseño por gusto: la referencia manda; si algo no está especificado, se resuelve con los tokens de §6.
