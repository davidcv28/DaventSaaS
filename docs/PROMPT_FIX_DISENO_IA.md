# Prompt — Arreglar "Diseñar con IA": colores de texto legibles + rediseño real (no plantillas prefabricadas)

> Uso: pegar el bloque de **Prompt** en la sesión del agente. El diagnóstico y el
> checklist de aceptación de abajo son el respaldo verificable del pedido — no son
> opcionales para quien implemente. Al cerrar, actualizar `AGENTS.md` §"Diseñar con IA"
> y este archivo en el mismo commit.

## Estado (2026-10-29) — implementado, motor `ai-design/5`

| # | Causa raíz | Resolución |
|---|---|---|
| 1 | `_theme` no emitía `styleColors`/`style` | `_theme` emite `style {id, palette}` (`SKIN.SKIN_STYLE_PRESET`, mapeo explícito familia→preset del Studio), `styleColors.light/dark` (`_style_set`, AA 4.5 sobre bg **y** surface) y `typography.roles` (ya viajaba). |
| 2 | La piel no llegaba al CSS publicado | `('skin','id')`/`('skin','family')` entran a `SITE_THEME_STYLE_KEYS` → `clean_site_theme`/`filter_site_theme` la publican también en plan Básico; `StorePublicLayout` la lee siempre y hace el `import()` de `skin-<familia>.css`. |
| 3 | Sin `data-st-*` en la publicación | `storeSiteThemeAttrs` agrega a mano `skin`/`styleColors`/`roles`/`layout` a las claves explícitas y fija `data-st-style` por modo; `pageAttrs` ya se aplicaba a `.store-page`. |
| 4 | Texto ilegible en banda/hero | `palette.secondary` = tinta de la banda (`_band_tone`, blanco ≥4.5 sobre acento) y bloque "TEMA PUBLICADO" en `store-page.css` mapea `--st-style-*` → `--sp-ink/-ink-2/-muted/-accent-text/-card/-surface/-line` + `--sp-on-band*`. |
| 5 | "Otra propuesta" repetía composición | `_VARIANTS_BY_LAYOUT` extiende la firma a 12 bloques de landing + catálogo (filters/picker/steps), `SKIN_LAYOUT_ALT` da una segunda composición por familia en las propuestas alternativas y `_layout_signature` (hash plantilla + orden/variantes de las 3 superficies) descarta candidatas repetidas. |

Tests: `AiDesignSkinAndContrastTests` (10) en `tests_ai_design.py` — skin/style/styleColors con AA en 5 pares por modo, banda y botón con acento claro del dueño, plan Básico, apply→público y firmas de layout distintas. `manage.py test` completo: 778 OK. Pendiente verificación visual: `qa_a11y.py` / 3 tiendas de rubros distintos con la misma entrevista.

## Diagnóstico del bug (por qué el motor "arma las mismas plantillas")

El motor v5 (`StoreApp/domains/stores/services/ai_design.py` + `ai_design_skins.py`) sí
compone plantilla + piel + par tipográfico, pero **lo que llega a la web publicada pierde
justo la parte que define la identidad visual**:

| # | Causa raíz | Dónde |
|---|---|---|
| 1 | `_theme()` nunca emite `styleColors` (el juego de colores de fuentes/contenedores por modo, que es lo que pinta `--sp-ink/-ink-2/-muted/-card/-bg` en la web pública) ni `style.id`. Una tienda del plan Básico solo persiste `style.id` + `styleColors`: con el motor no recibe NINGUNO → queda con el look por defecto del componente, aunque el motor haya elegido otra piel. | `ai_design.py::_theme` (~L976-1034), `clean_site_theme` filtra a `SITE_THEME_STYLE_KEYS` |
| 2 | La piel no llega al CSS. El motor emite `site_theme.skin = {id, family}`, pero `skin` **no está en `filter_site_theme`** (se descarta en la publicación salvo Premium) y `StorePublicLayout` solo la lee cuando `studioMode` está activo (iframe del editor): la hoja `skin-<familia>.css` nunca se importa en la web real. En el Studio la tienda se ve diseñada; publicada vuelve a la piel base. | `site_theme.py::filter_site_theme`; `frontend/src/views/StorePublicLayout.vue` (`effectiveSkin`, L180-186); `components/studio/previewBridge.js::studioPreviewAttrs` (L295-305) |
| 3 | El generador no emite `themeDataAttrs` equivalentes. `studioPreviewAttrs` (que sí pinta `data-st-skin`, `data-st-surface`, `data-st-btn-style`, `data-st-bgtype`, `data-st-reveal`, `data-st-hover`…) **no tiene espejo en la publicación**: `storeSiteThemeAttrs` no se aplica en `StorePublicLayout` y aun si se aplicara, el `site_theme` filtrado perdió esas secciones. Sin `data-st-*`, el bloque "paleta/botones/contenedores" de `store-page.css` (~L11250-11400) no se activa aunque las vars existan. | `previewBridge.js::storeSiteThemeAttrs`, `store-page.css` gates `[data-st-*]` |
| 4 | Los colores de texto quedan en el fallback de la hoja, no del diseño. Como el hero es una banda de acento con `color: #fff` hardcodeado (`.sp-hero-band`, `.sp-hero-title` hereda, `.sp-hero-sub` con `rgba(255,255,255,.88)`) y `--sp-ink`/`--sp-ink-2`/`--sp-muted` nunca se reciben, ciertas pieles con `bg` oscuro o acento claro producen texto de bajo contraste (subtítulos, eyebrows, meta, "Sobre nosotros", pies). Además `_contrast_ratio(accent, bg) >= 4.5` **no implica** que el blanco sobre los botones (`--store-accent-ink` derivado) pase AA: hoy nada lo garantiza desde el motor. | `store-page.css` L119-137 y L559; `ai_design.py::_theme` (contraste del acento) |
| 5 | "Otra propuesta" repite composición. `_apply_skin_layout` solo cambia `hero`, `featured` y `grid` y `_variant_for` rota variantes, pero dos pieles de la misma familia comparten `layout` heredado: la estructura (`layout_config` y variantes de bloque) sale casi idéntica entre propuestas de plantilla distinta con la misma firma de rubro. | `ai_design.py::_apply_skin_layout` (L788-807), `_build_surface` (L707-743) |

Consecuencia de negocio: el dueño pide "quiero la web cálida, tipo taller artesanal, con
verde salvia", el motor le ofrece dos tarjetas casi iguales y — al aplicar — la web queda
con los colores por defecto y la piel base. Parece que "la IA no rediseñó nada".

## Prompt (copiar tal cual en la sesión)

```
ACTÚA COMO: designer lead + backend lead del motor "Diseñar con IA" de DAVENT (v5).

PROBLEMA REPORTADO
1. La IA no elige bien los colores de los textos: hay títulos/subtítulos/eyebrows que
   quedan ilegibles (bajo contraste sobre la banda del hero, sobre cards o sobre el
   fondo oscuro de la piel).
2. La IA no rediseña la web como la pidió el cliente: devuelve/asigna siempre las mismas
   composiciones y la web publicada termina viéndose como la plantilla prefabricada.
3. Pedido explícito: rediseñar de verdad — CSS y HTML/estructura (bloques, variantes,
   tokens), no solo recolorar.

OBJETIVO
Que aplicar una propuesta del motor produzca una web VISIBLEMENTE elegida por el motor:
piel propia aplicada en la web pública, colores de texto con AA en todos los roles,
composición de bloques distinta entre propuestas y fiel al pedido de la entrevista
(rubro + tono + estilos + objetivos + color de marca + portada + modo noche).

CONTEXTO OBLIGATORIO DEL SISTEMA (respetar al pie de la letra)
- Motor determinista y offline: no llama a ninguna IA externa. Salida reproducible byte
  a byte (store + answers + ENGINE_VERSION). Si cambia el layout/theme emitido, subir
  ENGINE_VERSION (invalida caché y semilla base).
- Catálogo cerrado y validado server-side: skin.id ∈ SKIN_IDS, plantilla ∈
  allowed_templates_of, layout ∈ clean_layout_config (TEMPLATE_BLOCKS), theme ∈
  clean_site_theme. Nada inventado puede viajar; lo que el plan no permite se degrada al
  equivalente válido más cercano y se anota en `notes` de la propuesta.
- Invariantes que NO se rompen: contraste AA 4.5 en texto; TplProductCard uniforme en
  catálogo; landing = negocio + ofertas (sin grillas de catálogo embebidas); cero emojis;
  320-768px sin scroll horizontal; prefers-reduced-motion; base de diseño = Cobre (todos
  los bloques son los de StorePublicView, la plantilla cambia ORDEN/piel, no el DOM).
- No se escribe CSS libre desde el backend: solo tokens del contrato site_theme,
  variantes del catálogo de bloques y hojas de piel del frontend.

QUÉ HAY QUE HACER — BACKEND (StoreApp/domains/stores/)
A. COMPLETAR EL TEMA QUE EMITE EL MOTOR
   - `ai_design.py::_theme`: además de palette/containers/buttons/background/motion/layout/
     skin, emitir `style = {id, palette}` del preset del Studio más cercano a la piel
     (mapeo explícito piel→preset en ai_design_skins.py, mismo criterio que
     `_STYLE_PRESET_TEMPLATES` de site_theme.py) y `styleColors` con el set claro y oscuro
     {fonts {heading, body, muted, link}, containers {bg, surface, border, onSurface}},
     derivados del palette y con AA garantizado POR EL MOTOR (no confiar en que el
     frontend lo corrija). Emitir también `typography.roles`.
   - El set de `styleColors` debe respetar el modo (claro sobre fondo claro, oscuro sobre
     fondo oscuro) y sobrevivir a los tres pisos de plan: Básico (style.id + styleColors),
     Estándar (+ containers.radius/density) y Premium (todo).
   - `ai_design_skins.py`: sumar a cada familia (o a cada variante) el `styleColors`
     coherente con su paleta y su fondo; una familia con `palette` oscura debe traer el
     set oscuro correcto (nada de gris sobre negro ni tinta clara sobre papel).
B. CONTRASTE DEL TEXTO — REGLA FIJA, NO ESTADÍSTICA
   - Garantizar AA en CINCO pares, en claro y en oscuro, y testearlos:
     (1) text sobre bg, (2) muted sobre bg, (3) text/muted sobre surface (cards),
     (4) blanco sobre el color del botón sólido (--store-accent-ink o el primary
     efectivo), (5) texto sobre la banda del hero (acento/acento-ink).
   - El acento del dueño y el derivado de la semilla pasan por `_calm_palette` +
     `_ensure_contrast`; añadir la garantía (4) y (5) también al color de marca.
   - Si una piel no puede sostener AA tras 20 pasos de mezcla, sustituir el tono por el
     neutro equivalente y registrar la degradación en `notes`.
C. PUBLICAR LA PIEL Y LOS ATRIBUTOS, NO SOLO EL DRAFT
   - `site_theme.py::filter_site_theme`: incluir la sección `skin` en el subconjunto que
     sobrevive a un plan sin `has_design_advanced` cuando la familia sea del nivel del
     plan (una tienda Básica que recibe un diseño del motor no debe quedar con la piel
     base), y `style`/`styleColors` (ya contemplados).
   - Verificar que `clean_site_theme` + `apply()` publiquen la piel en la web (`apply` usa
     `site_theme_draft` → `site_theme`; revisar que `_publish` no la descarte).
D. REDISEÑO REAL: COMPOSICIÓN DISTINTA POR PROPUESTA Y FIEL AL PEDIDO
   - `_apply_skin_layout` solo toca hero/featured/grid: extenderlo a más variantes
     (stats, benefits, offers, testimonials, faq, gallery, contact, categories, cta) y a
     `catalog`/`services` (filters, sort, grid, picker, steps, form), usando SIEMPRE ids
     de variante existentes en TEMPLATE_BLOCKS.
   - Dos propuestas no deben diferir solo por color: distinto ORDEN de bloques por
     superficie, distinta terna (plantilla, piel, par tipográfico) y distinta firma de
     variantes. Medir la diferencia (hash de layout_config + template) y descartar la
     candidata si repite firma.
   - Los pedidos de la entrevista (`styles`, `must_have`, `goals`, `tone`, `audience`,
     `brand_color`, `cover_choice`, `night_mode`) deben verse en la propuesta ganadora:
     el estilo pedido primero, el bloque pedido arriba (después del hero), el tono
     ajustando densidad/movimiento/curvas, la audiencia reflejada en el copy.
   - Si la plantilla de la firma del rubro es la que menos cambia, ofrecer como segunda
     propuesta una plantilla de OTRA familia que el plan permita.
E. TESTS (obligatorios, en tests_ai_design.py / tests_ai_design_contract.py)
   - Toda propuesta trae `styleColors` válido, con AA en los 5 pares, claro y oscuro.
   - Publicar (apply) → el `site_theme` de la tienda contiene `skin` y `styleColors`, y el
     payload público (`GET /api/stores/public/<slug>/`) los expone.
   - Dos propuestas de la misma generación difieren en layout (hash) además de color.
   - Estilo pedido → aparece en la propuesta; estilo inventado → se ignora sin 400.
   - Plan Básico nunca recibe plantilla/piel fuera de `allowed_templates_of`.
   - Regresión: 1200 combinaciones rubro × seed sin fallos.

QUÉ HAY QUE HACER — FRONTEND (frontend/src/)
F. APLICAR EL TEMA PUBLICADO (no solo en modo Studio)
   - `StorePublicLayout.vue`: `effectiveSkin` debe mirar `customization.site_theme.skin`
     SIEMPRE (no solo con `?studio=1`) e importar `skin-<familia>.css` on-demand; hoy
     `publishedThemeAttrs = studioMode ? {} : storeSiteThemeAttrs(...)` y esos attrs
     nunca llegan al elemento `.store-page`. Aplicar `pageAttrs` a la raíz de la web.
   - `previewBridge.js::storeSiteThemeAttrs`: devolver el set completo de `data-st-*`
     cuando el tema lo fija (skin, surface, btn-style, btn-shape, bgtype, reveal, hover,
     nav, card, hero, sticky-cta) — espejo exacto de lo que ya consume el iframe del
     Studio, para que "lo que se ve al diseñar" sea "lo que se publica".
   - `stores.api.js` / `storeThemeVars`: exponer `--sp-ink`, `--sp-ink-2`, `--sp-muted`,
     `--sp-bg`, `--sp-card`, `--sp-line`, `--sp-accent-text` desde `styleColors` del
     `site_theme` PUBLICADO (hoy solo en la preview del Studio).
G. COLORES DE TEXTO EN EL CSS
   - `store-page.css`: donde hoy hay `#fff`/`rgba(255,255,255,…)` hardcodeados sobre la
     banda del hero, derivar de tokens (`--sp-on-band`, `--sp-on-band-2`,
     `--sp-on-band-muted`) con fallback a los valores actuales — una tienda sin tema se
     ve idéntica. Revisar también `.sp-eyebrow`, `.sp-hero-meta`, `.sp-hero-badge`,
     `.sp-about-text`, `.sp-foot-*`, `.tpc-*` y las bandas `.sp-stats`, `.sp-cta`.
   - La hoja de cada piel (`skin-*.css`) no puede re-introducir colores de texto crudos:
     solo tokens (`var(--sp-ink-2)`, `color-mix(...)` de tokens).
H. QUE SE VEA EL REDISEÑO
   - `AiDesignView.vue` / `AiProposalCard.vue`: la tarjeta debe mostrar el estilo
     (`variety.style_label`), la piel (`skin.label`) y qué cambió ("Portada, catálogo y
     servicios reorganizados"), no solo el punto de color.
   - La preview de la propuesta debe usar los MISMOS atributos/vars que la web publicada
     (F) para que lo que se elige sea lo que queda.
I. QA
   - `qa_a11y.py` sobre home/catálogo/servicios de cada plantilla aplicada por el motor:
     contraste estimado de títulos/subtítulos/eyebrows en claro y oscuro.
   - `qa_studio_premium.py` / `qa_variants.py` verdes; `npx vite build` verde.
   - Probar 3 tiendas de rubros distintos con la misma entrevista: las 3 webs deben verse
     claramente distintas (color, tipografía, composición, piel).

ENTREGABLE
- Diff mínimo por causa raíz (sin refactors de arrastre).
- Tests nuevos verdes + suite `manage.py test` completa verde (con `cache.clear()` en
  setUp donde toque por la fuga entre TestCase con SQLite).
- Actualizar docs/AI_DESIGN_STYLES_PROMPT.md, AGENTS.md (§ Diseñar con IA + § capa de
  atributos del tema) y ARCHITECTURE.md si cambia el flujo de publicación.
- Commit único en inglés (`fix: apply ai design skin and legible text colors`).
```

## Checklist de aceptación (verificable, no negociable)

1. `POST /api/stores/ai-design/` devuelve, por propuesta: `site_theme.skin`,
   `site_theme.style`, `site_theme.styleColors` (light + dark) y `typography.roles`.
2. `POST .../ai-design/apply/` deja esos valores en `customization.site_theme`
   **publicado**, también en plan Básico (al menos `skin` + `styleColors`).
3. `GET /api/stores/public/<slug>/` expone el `site_theme` efectivo con lo anterior y
   `GET` a la web filtra `<link>`/import de `skin-<familia>.css` y aplica `data-st-*` en
   `.store-page`.
4. En la web publicada, medido con `qa_a11y.py`: títulos, subtítulos, eyebrows, meta,
   cards y pie ≥ 4.5:1 en claro y en oscuro, en las 6 plantillas activas.
5. Dos propuestas de la misma generación ≠ mismo `template` y ≠ mismo hash de
   `layout_config` (se comparan ambos elementos, no el color).
6. Pedido explícito de estilo aparece en la propuesta ganadora; pedido inválido se ignora
   (nunca 400).
7. Sin regresiones: `manage.py test`, `ruff check`, `npx vite build` verdes; 1200
   combinaciones rubro × seed sin fallos.

## Trampas conocidas (no repetir)

- El conector `storeSiteThemeVars` siembra `palette` con `effectiveAccent()`: si `merge`
  se hace mal, el acento del dueño pisa el `styleColors` del motor y la web vuelve a los
  colores por defecto. Los `styleColors` del tema **mandan** sobre `palette` para
  texto/contenedores (`previewBridge.js`, bloque `if (on('styleColors'))`).
- `filter_site_theme` sin `has_design_plus`/`has_design_advanced` devuelve `{}`: cualquier
  campo nuevo tiene que agregarse a `SITE_THEME_STYLE_KEYS` o quedar en el subconjunto
  Plus, o la web pública nunca lo verá.
- `clean_site_theme` valida `_v_style_set` con AA duplicado: si el motor emite un set que
  no pasa, el PATCH devuelve 400 y la propuesta no se aplica. El motor debe emitir sets
  que ya pasen.
- `apply()` recorre `_prepare(... cache.get(cache_key) or {})`: si cambia la forma de
  `answers` o de la semilla, la propuesta cacheada deja de coincidir con el `proposal_id`
  y el apply devuelve "la propuesta no existe". Subir `ENGINE_VERSION` en el mismo commit.
- `StorePublicLayout` ya carga las hojas de piel con `import()` dinámico: no agregar
  imports estáticos de las 26 hojas (chunk inicial).
- Los tests con SQLite reutilizan PKs: `cache.clear()` en `setUp` de toda clase que toque
  beneficios, throttles o el cache del motor (§15.4 de `SECURITY_AUDIT.md`).
