# Inventario del motor determinista "Diseñar con IA" (engine `ai-design/7`)

> Recon de solo lectura. Objetivo: change-map para (a) una 4ª familia de plantilla
> "genérica" y (b) que el motor pueda MODIFICAR una propuesta existente.
> Toda referencia es `archivo:línea` (ruta relativa a la raíz del repo).

---

## 0. Resumen ejecutivo

- El motor es **una función pura determinista** (`generate`) sin llamadas de red ni IA
  externa: `store + entrevista + seed` → 2-3 propuestas. `apply` **recalcula** la
  propuesta (nunca acepta un layout del cliente) y publica en un solo paso.
- El **contrato de propuesta** es un dict plano sin serializer (solo se sanea al
  persistir con `clean_layout_config` / `clean_site_theme`).
- Hay **tres catálogos cerrados** que hay que tocar en sincronía: plantillas
  (`TEMPLATE_CHOICES` + `PUBLIC_TEMPLATES` + `STORE_TEMPLATES`), pieles
  (`SKIN_FAMILIES`/`SKINS` + `skin-*.css`) y estilos (`STYLE_FAMILIES`).
- **Las pieles y el `layout_config` no pintan la web pública** de los 3 diseños:
  `DESIGN_SKIN_FREE` los ignora; cada diseño es una composición fija en
  `frontend/src/views/store/<id>/`. Esto es la restricción de diseño más importante
  para (a) y (b).
- No existe hoy ningún camino de "modificar una propuesta": `apply` siempre parte de
  cero (con el borrador actual como fuente del copy, solo para campos vacíos).

---

## 1. Flujo request → propuesta

### 1.1 Endpoints (todos `POST`, Bearer, scope por tienda del dueño)

| Ruta | Vista | Qué hace |
|---|---|---|
| `/api/stores/ai-design/` | `StoreApp/domains/stores/views/viewset.py:826-842` | Genera 2-3 propuestas |
| `/api/stores/ai-design/apply/` | `viewset.py:844-884` | Recalcula la propuesta y **publica** |
| `/api/stores/ai-design/image/` | `viewset.py:886-917` | Sube foto del pedido → galería (WebP) |

- Throttles: `AiDesignThrottle` scope `ai_design` (`viewset.py:253-257`) y
  `AiDesignImageThrottle` scope `ai_design_image` (`viewset.py:261-264`).
- Gates (fail-closed, 403 con `detail`): `has_customization` y `has_ai_design`
  (`viewset.py:832-841` y `849-858`; imagen `892-901`). Nunca hay serializer de
  entrada: `request.data` se pasa crudo a `generate_ai_design` (`viewset.py:842`).
- `apply` acepta `seed`, `proposal_id`, `autofill`, `extras` (lista de ids o
  `{applied, offered}`), `skip_extras`; `_flag` normaliza booleanos
  (`viewset.py:859-872`). `AiDesignError` → 400 (`874`).

### 1.2 Función generadora

`StoreApp/domains/stores/services/ai_design.py`:

- `generate(store, payload)` → `ai_design.py:2170-2179`.
  - `_prepare` (`2159-2167`): `StoreCustomization.get_or_create`, `_facts`, `_answers`,
    `allowed_templates_of`, `has_design_advanced`, `has_ai_design`.
  - `seed = _base_seed(store, answers) + _request_seed(payload)` (`2174`);
    `_base_seed` = sha256(store.pk, respuestas normalizadas, `ENGINE_VERSION`)
    (`433-440`); `_request_seed` = entero del payload (`443-447`).
  - `_build(...)` (`2010-2156`) devuelve `{engine, seed, missing[], proposals[]}`.
  - Guarda las respuestas normalizadas en cache 1 h con clave
    `ai_design:{store.pk}:{seed}` (`CACHE_TTL` `43`, `_cache_key` `2182-2183`,
    `cache.set` `2178`) para que `apply` recalcule idéntico.
- Entrevista normalizada en `_answers` (`374-430`): `rubro`, `tone`, `goals[:2]`,
  `must_have` (solo ids de `TEMPLATE_BLOCKS['landing']`), `styles[:3]`, `audience[:120]`,
  `brand_color` (hex o se ignora), `night_mode{enabled,default}`, `cover_choice`,
  `use_icons`, `accept_extras`, `extras[:AI_ELEMENT_MAX]`, `content_hint[:160]`.
  Valores inválidos **nunca** dan 400: se descartan o se deducen
  (`_guess_rubro` `161-174`, `_guess_goals` `175-191`).

### 1.3 UI de la entrevista

- `frontend/src/views/design/AiDesignView.vue`: 6 pasos (`STEP_TITLES` `79`),
  estado `phase` `ask|loading|results|error` (`89`), persistencia del borrador de
  respuestas en localStorage `davent:ai-design:<storeId>` (`119`, `185-207`),
  armado del payload `275-288`, `generate` `291-334` (timeout 15 s), "otra
  propuesta" = `seed+1` `346-348`, `apply` `379-403`.
- Cliente API: `frontend/src/api/stores.api.js:229-240`
  (`aiDesign`, `aiDesignApply`); contrato comentado en `102-118`.
- Tarjeta: `frontend/src/components/ai/AiProposalCard.vue` (chips de extras, look,
  score); estilos en `frontend/src/assets/ai-design.css:398+`.

### 1.4 Dónde se persiste lo aceptado

`apply` (`ai_design.py:2376-2442`) escribe **borrador + publicado**:

1. Recalcula con `_build` (`2406`) y localiza `proposal_id` (`2407-2409`; desconocido
   → `AiDesignError` "no existe o venció").
2. Resuelve extras (`_resolve_extras` `2315-2373`, llamada `2415-2422`) y títulos
   (`_apply_titles` `2423`, `2186-2204`).
3. Guarda en `StoreCustomization`:
   - `layout_config_draft` ← `clean_layout_config(layout, …)` (`2427-2428`)
   - `site_theme_draft` ← `proposal['site_theme']` (`2429`)
   - `template_draft` (solo si está en `allowed`) (`2430`, `2425`)
   - `theme` / `theme_toggle` (`2431-2432`)
   - `copy` **solo en campos vacíos** (`2433-2437`); con `autofill=True` suma
     `_apply_draft` (`2438-2439`, `2255-2269`, `_DRAFT_FIELDS` `2248-2253`).
4. `_publish(customization, store)` (`2272-2295`): copia draft→publicado
   (`layout_config`, `site_theme`, `template`), crea `StudioVersion` con
   `{template, layout_config, site_theme}` + `note='Diseño con IA'` y poda a
   `MAX_PER_STORE=10` (`models/models.py:462-472`).

Endpoints de Studio que comparten ese estado: publish/discard/versions/restore
(`viewset.py:921-1041`). El serializer copia publicado→borrador cuando solo llega
el publicado (`serializers/serializers.py:416-419`).

---

## 2. Contrato de propuesta (estructura exacta)

### 2.1 Respuesta de `generate`

```text
{
  engine: 'ai-design/7',        # R.ENGINE_VERSION (ai_design_recipes.py:12)
  seed: int,
  missing: [ {code,label,hint,action} ],   # máx 6, MISSING_ORDER (ai_design.py:47-83)
  proposals: [ proposal, ... ]             # 2 o 3
}
```

### 2.2 `proposal` (claves exactas, `ai_design.py:2088-2142`)

| Clave | Contenido / invariante |
|---|---|
| `id` | `p1`/`p2`/`p3`, único en la generación (`2089`) |
| `label` | ≤32 chars, distinto por propuesta (`2090`) |
| `why` | texto legible de la elección (`_why` `1829-1840`) |
| `template` | **siempre** ∈ `allowed_templates_of(store.user)` (`575`, `2425`) |
| `style_source` | `'plan'` (`R.style_source_of`, `ai_design_recipes.py:256-262`) |
| `skin` | `{id, family, label}` (`2094`) |
| `site_theme` | tema **parcial** ya saneado con `clean_site_theme` (`2081-2087`) |
| `typography_roles` | 13 roles (`2096`, `ai_design_typography.py:99-105`) |
| `layout` | `site_theme.layout` (grid/hero/density/gutter/measure) (`2097`) |
| `look` | `{style_label, skin_label, fonts{heading,body,pair}, accent, mode, structure{landing[]}, changed[≤5]}` (`1916-1947`) |
| `score` | `{contrast, harmony, hierarchy, fit, total, issues[]}` — contraste real de los 5 pares + `styleColors` (`1962-1999`) |
| `extras` | `{offered[], applied[], skipped[]}` (`_extras_payload` `1489-1497`, `2107`) |
| `extras_items` | alias deprecado de `extras.offered` (`2110`) |
| `offered_blocks` | `{kind: block}` de **todos** los extras ofrecidos (`2114`) |
| `extras_accept` | bool (`2115`) |
| `variety` | `{family, style, style_label, differs_by[template,skin,type-pair]}` (`2116-2123`) |
| `redesign` | `{surfaces[landing,catalog,services], changed:true, summary, skin, style, layout}` (`2124-2131`) |
| `layout_config` | `{landing|catalog|services: {blocks:[{id,enabled,order,variant?,props?}]}}` saneado (`2132`) |
| `theme_choice` | `{source:'ai'|'user', accent}` (`2133`, `1658-1671`) |
| `night_mode` | `{enabled, default, toggle?}` (`_resolve_night` `1714-1737`) |
| `cover` | `{mode:'photo'|'logo', reason≤120, …}` (`_cover_for` `1738-1751`) |
| `theme` | `'light'|'dark'` (`2136`) |
| `theme_toggle` | bool (`2137`) |
| `copy` | campos de negocio (`ai_design_copy.build` `213-248`) |
| `notes` | lista de sugerencias (`_notes` `1841-1859`) |
| `copy_draft` | borrador ampliado para autofill (`ai_design_copy.draft_business_fields` `339+`) |
| `image_requests` | pedidos de fotos (`_image_requests` `1860-1900`) |

### 2.3 `site_theme` parcial que emite el motor (`_theme`, `1615-1697`)

`palette` (10 claves, `_calm_palette` corrige tinta/superficie y
`_legible_on` garantiza AA 4.5 sobre bg **y** surface), `containers`, `buttons`,
`background`, `motion`, `layout`, `skin{id,family}`, `typography{heading, body,
scale, weightHeading, letterSpacing, roles}`, `style{id,palette}` (solo si el
plan admite el preset, `1693-1696`/`1700-1711`), `styleColors{light,dark}`
(`_style_colors` `356-372`), y opcional `blocks` con overrides por contenedor
(`_block_styles` `1794-1828`, `2076-2078`).

### 2.4 Invariantes y validaciones

- 2-3 propuestas: `_proposal_count` (`2002-2007`) — 3 solo con ≥3 plantillas
  permitidas y ≥6 hechos de negocio.
- Diversidad obligatoria: plantilla **nunca** repetida salvo plan de una sola
  plantilla; piel, par y **estilo** distintos (`_select_styles` `733-783`).
- Firma de composición única: `_layout_signature(template, layout)` con hasta 4
  intentos (`2055-2058`, `1901-1911`).
- Nada fuera de catálogo sobrevive al guardado:
  `clean_layout_config` (`layout_blocks.py:311-335`) descarta ids/variantes/props
  desconocidos, bloques `premium` sin `has_design_advanced` y `ai_only` sin
  `has_ai_design`; `clean_site_theme` (`site_theme.py:445-548`) descarta
  secciones/claves fuera del plan y valida enums/hex/roles.
- `style.id` jamás `None`: si ningún preset entra en el plan se omite la sección
  (`ai_design.py:2065-2068`, `site_theme.py:533-547`).
- Límites de tamaño: `LAYOUT_MAX_BYTES=8192`, `LAYOUT_MAX_BLOCKS=24`
  (`layout_blocks.py:35-36`); `SITE_THEME_MAX_BYTES=12288` (`site_theme.py:48`).
- Determinismo byte a byte para mismo `store+answers+seed`
  (`tests_ai_design.py:116`, `tests_ai_design_contract.py:1095-1112`).

---

## 3. Catálogos y tablas de datos

### 3.1 Plantillas (catálogo cerrado de 3)

- `StoreCustomization.TEMPLATE_CHOICES` = `raiz|trama|circuito`
  (`models/models.py:137-141`); tiers `TEMPLATE_BASE=('raiz',)`,
  `TEMPLATE_PLUS=('trama',)`, `TEMPLATE_ADVANCED=('circuito',)`
  (`models.py:129-136`); `TEMPLATE_AI=()` (ya no hay plantillas exclusivas de IA).
- `TEMPLATE_RETIRED_MAP` (`models.py:145-157`): 28 ids viejos → nuevo, espejo
  `PUBLIC_TEMPLATE_MAP` (`ai_design_recipes.py:798-807`) y
  `STORE_TEMPLATE_RETIRED_MAP` (`frontend/src/api/stores.api.js:711-720`).
- `PUBLIC_TEMPLATES=('raiz','trama','circuito')` (`ai_design_recipes.py:797`).
  Las recetas por rubro y la matriz firma se remapean al importar
  (`ai_design_recipes.py:818-831`) y **se completan con los 3** (`824-827`).
- Bloques por superficie: `TEMPLATE_BLOCKS` (`layout_blocks.py:83-134`) con
  `variants`, `props` tipadas, `premium`, `locked`, `ai_only`. Es **global por
  superficie**, no por plantilla: qué bloques soporta cada plantilla vive en el
  frontend (`frontend/src/templates/<id>/index.js`).

### 3.2 Pieles y estilos

`StoreApp/domains/stores/services/ai_design_skins.py`:

- `SKIN_FAMILIES` (26) `30-36`; `STYLE_FAMILIES` (8) `48-50`; `STYLE_LABELS` `52-61`.
- Cada familia define `variants`, `palette`, `containers`, `buttons`, `background`,
  `motion`, `typography`, `layout`, `rubros`, `tones`, `accents`, `style`; `_build_skins`
  aplana a `SKINS` con id `<family>-<variant>` (52) `575-608`.
- `SKIN_FAMILY_OF` `611`, `SKIN_STYLE_PRESET` `621-651`,
  `STYLE_PRESET_TEMPLATES` `652-676` (preset del Studio → plantilla),
  `SKIN_TYPE_PAIR` `679-706` (par por familia), `SKIN_LAYOUT_ALT` `711-738`
  (2ª composición por familia), `skins_for/skin_of/style_preset_of/
  style_preset_for_plan/type_pair_of` `741-782`.
- Espejo frontend obligatorio: `SKIN_FAMILIES` en
  `frontend/src/components/studio/previewBridge.js:67` y una hoja por familia
  `frontend/src/assets/skin-<familia>.css` (import dinámico
  `StorePublicLayout.vue:185-187`).

### 3.3 Recetas por rubro/tono/objetivo

`StoreApp/domains/stores/services/ai_design_recipes.py`:

- `TONES` (4) `14`, `DEFAULT_TONE=moderno` `15`, `GOALS` (5) `17`, `ACCENTS` `156`,
  `TONE_TWEAKS` `176`, `TEMPLATE_TONE_AFFINITY` `184` (+ update `834-838`),
  `TEMPLATE_GOAL_AFFINITY` `232` (+ update `840-848`), `TEMPLATE_LABELS` `216`
  (+ update `839`).
- `RUBROS` (13: comercio, gastronomia, indumentaria, servicios_profesionales,
  salud, belleza, construccion, tecnologia, educacion, turismo, mascotas, arte,
  otro) `438-598` — cada uno con `templates` (orden de afinidad), `emoji`,
  `keywords`, `hints`.
- `RUBRO_STYLES` (matriz "firma": 3 ternas plantilla+piel+par por rubro) `271-337`;
  `GOAL_RECIPES` `624-678` (orden de bloques + labels por objetivo);
  `AI_PATTERNS` `389`; `BLOCK_GATES` `700`; `BLOCK_FALLBACKS` `745`;
  `HIERARCHY_RULES` `757`; `BLOCK_TITLES` `773`; `SOCIAL_BLOCKS`/`IMAGE_BLOCKS`
  `679-685`; `TONE_DENSITY` `687`.
- Extras: `AI_ELEMENT_ORDER` (8 ids) `367`, `AI_ELEMENT_ANCHORS` `369`,
  `AI_ELEMENT_MAX=4` `379`.

### 3.4 Tipografías

`StoreApp/domains/stores/services/ai_design_typography.py`: `FONT_FAMILIES` (24)
`25-56`, `FONT_WEIGHTS` `62`, 13 `TYPOGRAPHY_ROLES` `99-105` (8 body + 4 display +
`price`), enums de tamaño/tracking/leading/case `107-110`, `TYPE_PAIRS` `115-151`,
`TYPE_VOICES`/`PAIR_VOICES`/`SKIN_TYPE_VOICES` `162-238`, `SKIN_ROLE_OVERRIDES`
`294`, `roles_for` `331-366`, `type_pair_signature` `367`, `resolve_pair` `406-423`.
Espejo del catálogo de fuentes del modelo: `StoreCustomization.FONT_CHOICES`
(`models/models.py:77-120`).

### 3.5 Copy

`StoreApp/domains/stores/services/ai_design_copy.py`: `RUBRO_COPY` `31-126`,
`TONE_COPY` `127-150`, `GENERIC_TITLES` `151`, `build` `213-248`,
`title_for` `249-261`, `DRAFT_MISSIONS` `262`, `DRAFT_FIRST_FAQ` `279`,
`draft_business_fields` `339+`.

### 3.6 Cómo extender sin romper catálogos cerrados

- **Receta (rubro)**: agregar a `RUBROS` (`ai_design_recipes.py:438`) con
  `templates` (ids del catálogo público), `emoji`, `keywords`; sumar la terna
  firma a `RUBRO_STYLES` (`271`). El post-proceso `818-831` remapea y completa.
- **Piel**: familia nueva → `SKIN_FAMILIES` (`ai_design_skins.py:30`), entrada en
  `_FAMILIES` (con `style` obligatorio ∈ `STYLE_FAMILIES`), `SKIN_STYLE_PRESET`,
  `SKIN_TYPE_PAIR`, `SKIN_LAYOUT_ALT`; hoja `frontend/src/assets/skin-<familia>.css`;
  espejo `previewBridge.js:67`. Test que lo garantiza:
  `test_skin_catalog_is_closed_and_composed` (`tests_ai_design.py:1018`) y
  `test_every_style_of_the_training_has_skins`
  (`tests_ai_design_contract.py:630`).
- **Plantilla**: ver §7(a) — 5 puntos backend + 5 frontend + 2 migraciones/espejos.

---

## 4. Selección: `_style_candidates` / `_select_styles` y plan

### 4.1 Entradas

`_skin_pool(answers, seed)` `486-509` (pieles afines a rubro/tono, rotadas por
semilla), `_style_pool(style, rubro, tone)` `510-517`, `_style_order` `518-547`
(prioriza estilos pedidos y luego cobertura).

### 4.2 `_style_candidates(facts, stats, answers, allowed, seed)` — `548-726`

Construye candidatas `{template, skin, pair, style, source, score}` con `add()`
(`571-607`) y **4 bloques**:

0. **Estilos pedidos** (`styles[]`): entran antes de la matriz con base 80
   (`622-628`); nunca se imponen, pero un estilo pedido debe verse en la ganadora.
1. **Matriz firma del rubro** (`RUBRO_STYLES`): base `40 - index*5` (`630-631`).
2. **Resto de plantillas permitidas** con piel rotada, priorizando estilos pedidos
   y sin repetir estilo si hay de sobra (`638-656`); si el plan tiene **una sola
   plantilla** agrega variantes de piel/par (`660-669`).
3. **Cobertura de estilos**: cada estilo estrena plantilla propia (base 40 si fue
   pedido, 6 si no) (`674-693`); si no hay plantilla libre, clona la mejor
   candidata del estilo **filtrando por `allowed_set`** (`694-713`) — el bug del
   plan Básico con `ai_lumen` ya pagado (AGENTS).

Cierre: orden por `(-score, template, skin)` (`717`) y rotación de semilla **solo**
en la cabeza de 3 y **suspendida** si hay un estilo pedido ahí (`721-725`).

Puntaje (`589-599`): base + `70` si estilo pedido + `2×TEMPLATE_TONE_AFFINITY` +
`4` si objetivo afín + `3` si tono de la piel + `2` si rubro de la piel +
`min(densidad,6)` + `_data_signal` (`462-485`: fotos/texto/catálogo/vacío).

### 4.3 `_select_styles(candidates, count, allow_repeat_template=False)` — `733-783`

Tres pases que relajan en este orden:
1. **estilo** distinto (la plantilla tampoco se repite salvo `repeat_template`);
2. **piel + par** nuevos (estricto);
3. **solo plantilla** nueva (relajado).
Devuelve `chosen[:count]`. `allow_repeat_template` = `len(set(allowed)) < count`
(`2023`), es decir Básico con una plantilla.

### 4.4 Plan gating

- `allowed_templates_of(profile)` (`services/services.py:77-93`): sin
  `has_customization` → `('raiz',)`; base siempre; `has_design_plus` suma `trama`;
  `has_design_advanced` suma `circuito`.
- El PATCH de customization **descarta** `template`/`template_draft` fuera de la
  whitelist (`viewset.py:806-811`); el serializer remapea ids retirados
  (`serializers.py:430-439`); el render fuerza `raiz` (`stores.api.js:746-751`,
  `StorePublicLayout.vue:159-164`).
- `has_ai_design` es flag de plan (`SuscriptionApp/domains/benefits/management/
  commands/seeds.py:33`; trial/premium true, básico false `62/100/141/184`).
  `has_customization` es el piso para generar; `has_ai_design` habilita además
  bloques `ai_only` y extras.
- Presets del Studio por plan: `style_preset_for_plan`
  (`ai_design_skins.py:759-776`).

---

## 5. Persistencia y aplicación: quién consume qué

### 5.1 Campos en `StoreCustomization` (`models/models.py`)

| Campo | Línea | Escrito por | Leído por |
|---|---|---|---|
| `template` | `191` | PATCH, `_publish` | `pageTemplate` público |
| `template_draft` | `368` | PATCH, `apply` | Studio/preview |
| `layout_config` | `359` | PATCH, publish, restore | Studio (`StudioShell`), `LayoutEditor`, `BlockRenderer` (preview) |
| `layout_config_draft` | `366` | PATCH, `apply`, discard | Studio, `has_unpublished` |
| `site_theme` | `362` | PATCH, publish, restore | Studio, folleto (`FlyerStudio`), `StorePublicLayout` **solo si el diseño no es free-skin** |
| `site_theme_draft` | `367` | PATCH, `apply`, discard | Studio |
| `theme` / `theme_toggle` | `187`, `190` | PATCH, `apply` | web pública |
| `copy` / `copy_draft` fields | `2248-2253` | `apply` (solo vacíos), autofill | web pública / “Mi empresa” |

- `has_unpublished` se **deriva** comparando drafts vs publicados
  (`serializers.py:336-342`).
- Serializer del dueño: `StoreCustomizationSerializer` (`serializers.py:116-154`);
  público: `StoreCustomizationPublicSerializer` (`serializers.py:476-510`) con
  `site_theme` filtrado por `filter_site_theme` (`site_theme.py:568-593`), sin
  drafts ni `contact_email`.

### 5.2 Consumidores reales en el render

- `frontend/src/views/StorePublicLayout.vue:123-128` — **`DESIGN_SKIN_FREE =
  ['raiz','trama','circuito']`**: con esos templates `consumesSiteTheme=false` y
  **no se emiten** `site_theme` attrs. `pageTemplate` `159-164`; hojas por diseño
  `TEMPLATE_CSS` `172-177`; `data-template` en el root `598`.
- Composiciones fijas: `frontend/src/views/store/raiz/InicioView.vue:1-46`
  (14 secciones, "no layout_config"), `trama/InicioView.vue`, `circuito/InicioView.vue`,
  `views/store/<id>/{Catalogo,Producto,Servicios}View.vue`.
- `layout_config` **solo** se consume en el Studio/editor:
  `components/LayoutEditor.vue:112-115`, `components/store/BlockRenderer.vue:30-40`
  (usado por el editor, no por la portada pública), y la variante del `picker` en
  `views/store/raiz/ServiciosView.vue:131`.
- `site_theme` también alimenta: folleto (`components/FlyerStudio.vue:157-160`),
  `PresetGallery` (`studio/presets/PresetGallery.vue:29`), `storeSiteThemeAttrs`
  (`previewBridge.js:338-350`).

---

## 6. Tests existentes (325)

| Módulo | Tests | Foco |
|---|---|---|
| `tests_ai_design.py` | 85 | Generación/gates/apply v2-v6, pieles+contraste (`AiDesignSkinAndContrastTests` `221`), extras (`AiDesignExtrasTests` `1172`), imágenes |
| `tests_ai_design_contract.py` | 122 | Contrato HTTP y catálogos cerrados: `Diversidad` `288`, `FuentesDeEstilo` `375`, `ThemeV2` `430`, `RolesTipograficos` `539`, `Layout` `620`, `BloquesV4` `704`, `Apply` `878`, `Regresiones` `993` |
| `tests_ai_design_selection.py` | 68 | Selección pura: `SkinPoolTests` `106`, `StylePoolTests` `146`, `StyleOrderTests` `189`, `StyleCandidates*` `239/319/364`, `SelectStylesTests` `460`, `CandidatesToSelectionTests` `532` |
| `tests_ai_design_composition.py` | 26 | Ritmo/portada/jerarquía/densidad/variantes/anti-repetición `84-400` |
| `tests_ai_design_typography.py` | 24 | Pares, roles, coherencia de aire, tracking publicado `40-332` |

Garantías clave: determinismo, 2-3 propuestas diversas, plantilla siempre en el
plan (`test_template_outside_plan_never_returned` `tests_ai_design.py:169`),
catálogo de pieles cerrado y compuesto (`1018`), AA real, contrato de roles de 13,
`apply` idempotente y sin pisar copy (`tests_ai_design_contract.py:939-997`),
extras solo con `has_ai_design` (`tests_ai_design.py:1247`).

Comandos (desde la raíz):

```powershell
venv\Scripts\python.exe manage.py test StoreApp.domains.stores.tests_ai_design StoreApp.domains.stores.tests_ai_design_contract StoreApp.domains.stores.tests_ai_design_composition StoreApp.domains.stores.tests_ai_design_selection StoreApp.domains.stores.tests_ai_design_typography
npx vite build            # en frontend/
venv\Scripts\python.exe qa_ai_design_v6.py
```

Ojo fuga de cache entre `TestCase`: `cache.clear()` en `setUp` (AGENTS §15.4).

---

## 7. CHANGE-MAP

### (a) 4ª familia de plantilla "genérica"

Supuesto: la familia nueva es una **composición fija** como las 3 actuales (no una
plantilla configurable por `layout_config`). Si el modelo de referencia exige
secciones nuevas, ver el punto 6 de esta sección.

**Backend (5 archivos + 1 migración)**

1. `StoreApp/domains/stores/models/models.py:129-141` — sumar `generica` a
   `TEMPLATE_CHOICES` y al tier que corresponda (`TEMPLATE_BASE/PLUS/ADVANCED`).
   `max_length=12` alcanza (`generica` = 8). **Migración** nueva (solo `choices`,
   sin cambio de columna ni de datos; idempotente sobre filas existentes).
2. `StoreApp/domains/stores/services/services.py:77-93` — `allowed_templates_of`
   ya suma por tier: no requiere código si se usa el tier existente; sí si se
   agrega un 4º tier/flag.
3. `StoreApp/domains/stores/services/ai_design_recipes.py`:
   - `PUBLIC_TEMPLATES` `797` (+ `PUBLIC_TEMPLATE_MAP` si hay ids retirados nuevos).
   - `RUBROS[...]['templates']` `438-598`: el post-proceso `818-827` **auto-completa**
     cualquier plantilla faltante, así que no hace falta tocar los 13 rubros.
   - `RUBRO_STYLES` `271-337` + loop `830-831`: agregar una 4ª terna firma si se
     quiere que la matriz la abra; si no, queda como candidata de cobertura.
   - `TEMPLATE_TONE_AFFINITY` `834-838`, `TEMPLATE_GOAL_AFFINITY` `840-848`,
     `TEMPLATE_LABELS` `839`.
4. `StoreApp/domains/stores/services/ai_design_skins.py`:
   - `STYLE_PRESET_TEMPLATES` `652-676` — al menos un preset mapeado a la plantilla
     nueva, o `style_preset_for_plan` (`759-776`) cae a otro preset y
     `site_theme.style` pierde coherencia.
   - Si se estrena familia de piel: `SKIN_FAMILIES`, `_FAMILIES`, `SKIN_STYLE_PRESET`,
     `SKIN_TYPE_PAIR`, `SKIN_LAYOUT_ALT`.
5. `StoreApp/domains/stores/layout_blocks.py:83-134` — **solo** si la composición
   nueva usa ids de bloque que no existen; todo id nuevo debe entrar a
   `TEMPLATE_BLOCKS[superficie]` con `variants`/`props`/`ai_only` declarados.
6. **Secciones nuevas del modelo de referencia** (si las hay): id nuevo en
   `TEMPLATE_BLOCKS` + componente `frontend/src/components/store/blocks/Blk*.vue`
   + rama en `BlockRenderer`/vista del diseño + (si aplica) variante en
   `_VARIANTS_BY_LAYOUT` (`ai_design.py:1169-1218`) y `TEMPLATE_BLOCKS` props
   tipadas. Sin esto el bloque se descarta en silencio al guardar.

**Frontend (5 puntos + SFCs/CSS)**

7. `frontend/src/api/stores.api.js:692-706` — `STORE_TEMPLATES` (+ `tier`,
   `label`, `rubro`, `defaultAccent`, `desc`), `STORE_TEMPLATE_FAMILIES`,
   `CUSTOMIZATION_DEFAULTS.template` `442`, `allowedTemplatesFor` `735-741`,
   `resolveStoreTemplate` `746-751`. Y `STORE_TEMPLATE_RETIRED_MAP` `711-720` si
   se retira algo.
8. `frontend/src/templates/index.js:26-30` — import + `TEMPLATE_DEFS`;
   `frontend/src/templates/generica/index.js` (superficies y `blocks` soportados).
9. `frontend/src/views/store/generica/{Inicio,Catalogo,Producto,Servicios}View.vue`
   + registro en `components/store/BlockRenderer` si se usan bloques dinámicos.
10. `frontend/src/assets/store-generica.css` + `StorePublicLayout.vue:172-177`
    (`TEMPLATE_CSS`) + **`DESIGN_SKIN_FREE` `123`** (si no se agrega, el
    `site_theme` guardado empieza a pintar la web nueva y no hay hoja de piel
    cargada → regresión visual) + `pageTemplate` `159-164`.
11. Selector de diseño del dashboard y preview (consumen
    `STORE_TEMPLATE_FAMILIES`) + `docs/PLANTILLAS_INTERFAZ.md`.

**Tests que rompen (esperado, hay que actualizarlos)**

- `tests.py:424` (`known == {'raiz','trama','circuito'}`), `:389`, `:406`, `:466`.
- `tests_ai_design_contract.py:78` (`STYLE_TEMPLATES`), `:380-381`, `:386`,
  `:392-394` (tiers exactos), `:405`, `:412`; `test_every_rubro_declares_three_
  distinct_signature_styles` `:343` si `RUBRO_STYLES` pasa a 4.
- `tests_ai_design.py:581`, `:606`, `:955`, `:977`, `:988`, `:990`.
- `tests_ai_design_selection.py:21` (`PLAN_ADVANCED`).
- Si la 4ª entra en **tier base**: `test_plan_basico_gets_two_proposals_inside_the_plan`
  (`tests_ai_design_selection.py:543`) y `_proposal_count` (`2002-2007`) cambian de
  comportamiento. **Recomendación:** estrenarla en `TEMPLATE_ADVANCED` (Premium)
  para no tocar el piso del plan Básico; el Premium pasa a 4 permitidas y sigue
  devolviendo 3 propuestas.

**Esfuerzo:** 3-5 días (backend 1-1.5, frontend SFC+CSS 2-3, tests/docs 0.5).
**Riesgos:** composición fija nueva = trabajo de diseño/CSS real, no solo datos;
`TEMPLATE_BLOCKS` es catálogo cerrado (un id sin declarar se descarta y la sección
desaparece en silencio); `DESIGN_SKIN_FREE` y `STORE_TEMPLATES` son espejos manuales.

### (b) Modificar una propuesta existente (re-tematizar / recomponer / cambiar estilo)

Hoy **no existe**: `apply` (`ai_design.py:2376-2442`) siempre recalcula desde la
entrevista y publica; el copy solo rellena vacíos; no hay endpoint de ajuste
parcial. Las piezas reutilizables ya están: `_theme`, `_style_colors`,
`_block_styles`, `_apply_skin_layout`, `_resolve_extras`, `_publish`,
`clean_site_theme`, `clean_layout_config`, y los endpoints publish/discard/restore
del Studio (`viewset.py:921-1041`).

**Backend**

1. `StoreApp/domains/stores/services/ai_design.py` — nueva función
   `adjust(store, payload)` (junto a `apply`, ~`2376`):
   - Base **autoritativa del servidor**: `customization.layout_config_draft` +
     `site_theme_draft` + `template_draft` (nunca un layout del cliente).
   - Ejes: `template`, `skin`/`style`, `accent`/`brand_color`, `sections`
     (enable/order/variant), `copy` (solo campos explícitos), `seed`.
   - Reusar `_theme`/`_style_colors` para el eje tema y `_apply_skin_layout`
     (`1244-1283`) + `_build_surface` (`905-962`) para recomponer secciones.
   - Devolver un **patch** (o aplicar a draft con `publish=False`) para que la UI
     previsualice antes de publicar; publicar con `_publish` (`2272-2295`).
2. `ai_design.py` — extraer de `_build` (`2010-2156`) la composición de layout para
   aceptar un `base_layout` opcional (`_layout` `1135-1146` + `_build_surface`
   construyen de cero). Alternativa de menor riesgo: post-procesar el layout
   existente (mover/apagar/re-variar bloques existentes) sin reordenar todo.
3. `viewset.py` — nuevo action `@action(url_path='ai-design/adjust')` copiando el
   patrón de gates/throttle de `ai_design` (`826-842`); validar que `template` y
   `skin` estén en catálogo/plan; 400 con `AiDesignError`.
4. `stores.api.js` — método `aiDesignAdjust` junto a `234-240`.

**Frontend**

5. `AiDesignView.vue` — estado "ajustar propuesta publicada": reusar
   `publishedSnapshot` (`96`, `394-395`) y los controles de `AiProposalCard`;
   publicar con el endpoint nuevo o con `saveDesign` (`DashboardView.vue:1829-1836`).
6. Previsualización: `StorePublicLayout` ya soporta `?studio=1` + `studio:update`
   por postMessage (`45-100`), así que el preview del ajuste no necesita iframe
   nuevo.

**Esfuerzo:** 2-4 días (servicio+recomposición 1-1.5, endpoint 0.5, UI 1-1.5,
tests 0.5).
**Riesgos:** (i) no pisar el copy ni los datos del dueño (hoy `apply` solo llena
vacíos; un "ajuste" que reescriba campos rompe `test_apply_never_overwrites_the_
owners_published_content`, `tests_ai_design_contract.py:973`); (ii) los extras
`ai_only` se filtran sin `has_ai_design` (`layout_blocks.py:295-296`); (iii)
`site_theme` descarta en silencio lo que el plan no banca (`site_theme.py:478-487`)
— el ajuste debe reportar qué se descartó; (iv) determinismo e idempotencia:
mismo `base + eje + seed` debe dar el mismo resultado (guardar la semilla del
ajuste, no confiar en el cliente); (v) `apply` publica en un paso y crea
`StudioVersion`: si el ajuste también publica, duplicar versiones por cada
tanteo llena el historial (máx 10).

### (c) Riesgos de compatibilidad transversales

- **Migración**: cambiar `choices` en `template`/`template_draft` no altera datos
  ni constraints en Postgres; las filas viejas ya están remapeadas por la mig.
  `0053` (`migrations/0053_redesign_template_catalog.py`). No borrar ids de
  `TEMPLATE_RETIRED_MAP` sin migración de reescritura.
- **Ids retirados**: hay 6 espejos del mapa (modelo, recipes, stores.api.js,
  migración 0049/0053, `resolveStoreTemplate`, serializer). Un id nuevo debe
  agregarse a `TEMPLATE_CHOICES` **y** a `STORE_TEMPLATES`, o el PATCH lo descarta
  y el render cae a `raiz`.
- **Catálogos cerrados**: `test_skin_catalog_is_closed_and_composed`,
  `test_every_style_of_the_training_has_skins`, `test_engine_has_no_exclusive_or_
  legacy_designs` (`tests_ai_design_contract.py:396`). Agregar una piel sin
  `style` o un estilo sin pieles rompe la suite.
- **Tests que fallan por conteos**: los listados en (a) — son aserciones de
  "exactamente 3", no bugs.
- **Render**: cualquier plantilla nueva DEBE entrar en `DESIGN_SKIN_FREE`
  (`StorePublicLayout.vue:123`) o el `site_theme` guardado empieza a aplicarse
  sobre una hoja que no existe (`skin-<family>.css` no cargada).
- **API**: `generate`/`apply` son contrato público del frontend; agregar claves es
  seguro (aditivo), quitarlas no. `apply` debe seguir rechazando `proposal_id`
  desconocido (`2407-2409`) y seguir siendo idempotente para el mismo `seed+id`.

---

## 8. Bloqueantes / vacíos de información

- **No hay screenshots ni especificación del "modelo de referencia" en el
  workspace** (solo capturas de QA de las plantillas actuales en `qa/`). El
  change-map (a) asume una composición fija con los bloques existentes; la lista
  exacta de secciones nuevas hay que confirmarla contra las capturas.
- **No existe tool `team_task_get`** en esta sesión (tools disponibles: fs/pwsh/
  web/subagentes), así que no se pudo hacer claim de `task-2` ni consultar su
  revisión; el trabajo se entregó igual sobre el objetivo declarado.
- El render público de los 3 diseños **ignora `layout_config`**: "recomponer
  secciones" en (b) solo tiene efecto visible si (1) se toca el `layout_config`
  que consume el Studio, o (2) se modifican los datos de contenido del modelo
  (`services`, `stats`, etc.) que la composición fija sí lee. Decidir cuál de las
  dos semánticas se quiere antes de estimar (b).
