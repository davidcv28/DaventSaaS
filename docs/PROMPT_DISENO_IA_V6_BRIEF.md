# Brief de ingeniería → "Diseñar con IA" v6

> **Uso:** este documento es el encargo completo (contrato + trabajo por agente + criterios de
> aceptación). Se le entrega al agente coordinador (backend) y a los 5 agentes de fase. Es
> **ejecutable**: cada punto nombra archivo, función y línea donde vive la decisión, y cada
> requisito tiene un criterio de aceptación verificable. Ordenar la lectura: §1 contexto del
> producto → §2 contrato → §3 plan de agentes → §4–§8 trabajo por fase → §9 aceptación → §10
> trampas → §11 protocolo de entrega.
>
> Precede y complementa a `docs/PROMPT_FIX_DISENO_IA.md` (diagnóstico del bug de colores y de
> piel publicada) y a `docs/AI_DESIGN_STYLES_PROMPT.md` (catálogo de estilos). Si algo cambia
> acá, se actualizan los tres en el mismo commit.

---

## 1. Marco de producto (lo que el dueño espera ver)

El dueño de una tienda entra a **Diseñar con IA → Nuevo diseño**, responde 8 preguntas
(rubro, tono, objetivos, público, estilos, color de marca, portada, modo noche) y marca qué
debe tener sí o sí. Al generar, espera **2–3 webs distintas entre sí y distintas de lo que
tenía**, con:

1. **Una landing que le hable a SU negocio** — portada con el mensaje correcto para su
   objetivo (vender, mostrar trabajos, conseguir consultas, dar confianza), prueba social
   antes del cierre y el contacto al final.
2. **Diseño profesional de nivel agencia**: jerarquía tipográfica de 2 familias que
   *conversan* (display + cuerpo) con escala y pesos reales, mucho aire, acento usado con
   moderación (una tinta de marca, no seis colores), contraste AA en **todo** texto, y fondos
   que no compiten con el contenido.
3. **Rediseño, no recoloreado**: los mismos bloques del sistema (base Cobre) **reubicados**
   en otro orden, con otras variantes y otro ritmo vertical — la portada, el catálogo y
   servicios se sienten armados para ese negocio.
4. **Elementos extra** que la IA propone explícitamente ("puedo sumarte una banda de sellos,
   una comparativa de tamaños, un mosaico de fotos, una pregunta frecuente más") y el dueño
   **acepta o rechaza** antes de aplicar.

Lo que hoy rompe la promesa (detalle en `PROMPT_FIX_DISENO_IA.md`): el motor no emite
`styleColors`/`style.id`, la piel no se publica, los `data-st-*` no se aplican fuera del
Studio, y dos propuestas de la misma plantilla comparten composición.

---

## 2. Contrato v6 (cerrado — nada de esto se inventa fuera del catálogo)

### 2.1 Incrementos de versión
| Constante | De | A | Motivo |
|---|---|---|---|
| `ai_design_recipes.ENGINE_VERSION` / `ai_design.ENGINE_VERSION` | `ai-design/5` | `ai-design/6` | cambia la forma del payload (extras, look, score) → invalida caché y semilla base |
| `docs/AI_DESIGN_STYLES_PROMPT.md` | v5 | v6 | se suman campos de calidad y el flujo de extras |

La forma del `layout_config`, `site_theme` y de las variantes **no cambia** (el contrato
`clean_layout_config` / `clean_site_theme` queda igual); v6 **agrega** información al payload
y **usa mejor** lo que ya existe.

### 2.2 Payload de propuesta — campos nuevos (aditivos, nunca obligatorios para el front)
```jsonc
{
  "id": "p1",
  "template": "cobre",
  "skin": { "id": "editorial-ink", "family": "editorial", "label": "Editorial tinta" },
  "site_theme": { /* palette, containers, buttons, background, motion, layout, skin,
                     style: {id, palette}, styleColors: {light, dark}, typography.roles */ },
  "look": {                                   // NUEVO — resumen legible para la tarjeta
    "style_label": "Editoriales y de revista",
    "skin_label": "Editorial tinta",
    "fonts": { "heading": "Fraunces", "body": "Inter", "pair": "serif-editorial" },
    "accent": "#b45309",
    "mode": "light",                          // "light" | "dark"
    "structure": { "landing": ["hero","about","gallery","..."] },   // orden efectivo
    "changed": ["Orden reescrito", "Portada a dos columnas", "Tipografía serif editorial",
                "Catálogo en grilla editorial", "Servicios en pasos"]
  },
  "extras": {                                 // NUEVO — elementos que la IA propone sumar
    "offered": [                              // lo que se puede agregar sin tocar datos
      { "id": "extra-stamps", "kind": "aistrip", "label": "Banda de sellos",
        "why": "Tu público busca confianza antes de comprar.",
        "block": { "id": "aistrip", "enabled": true, "order": 3, "variant": "band" },
        "needs": "Nada — se arma con tu información." },
      { "id": "extra-gallery-mosaic", "kind": "aimosaic", "label": "Mosaico de fotos",
        "why": "Tenés 7 fotos cargadas y ninguna en portada.",
        "block": { "id": "aimosaic", "enabled": true, "order": 9, "variant": "mosaic" },
        "needs": "Tus fotos de la galería." }
    ],
    "applied": ["extra-stamps"],              // las que viajan en layout_config de la propuesta
    "skipped": [{ "id": "extra-pricing", "reason": "Tu plan no incluye bloques de IA." }]
  },
  "score": {                                  // NUEVO — calidad medible de la propuesta
    "contrast": 100, "harmony": 92, "hierarchy": 88, "fit": 95, "total": 93,
    "issues": []                              // 0+ frases cortas, es-AR, sin jerga
  }
}
```

**Regla de oro del payload:** todo campo nuevo es aditivo y tolerado por el front viejo. Si
el agente no puede completar un campo, se omite — nunca se envía `null` explícito ni un id
fuera de catálogo.

### 2.3 Entrada de la entrevista (normalizada en `_answers`, ampliada)
| Campo | Tipo | Regla |
|---|---|---|
| `accept_extras` | `bool` \| ausente | pregunta "¿sumar extras?": `true` = aplicarlas en el layout, `false` = solo ofrecerlas, ausente = `true` (comportamiento actual, no rompe clientes viejos) |
| `extras` | `string[]` | ids de `extras.offered` que el dueño ya eligió (máx 4, se intersectan con `AI_ELEMENT_ORDER`) |
| `content_hint` | `str` ≤ 160 | qué más quiere contar (se usa en el copy y en la elección de bloques; nunca se mete crudo en HTML) |
| resto | igual v5 | valores inválidos se ignoran en silencio (nunca 400) |

### 2.4 Catálogo cerrado de extras
Solo los 8 bloques `aiOnly` de `TEMPLATE_BLOCKS.landing`
(`aiquote`, `aistrip`, `aicheck`, `aigrid`, `aiband`, `aiprocess`, `aipricing`, `aimosaic`)
más re-variantes de bloques existentes (`featured: quick`, `stats: cards`, `testimonials:
carousel`, `faq: cols`…). Un extra **nunca** crea un id nuevo, un prop nuevo ni un bloque
fuera de `has_ai_design`; sin `has_ai_design` el motor los pone en `extras.skipped` con motivo.

---

## 3. Plan de agentes (paralelo, sin choques)

Cinco agentes de fase + coordinador. Cada uno es dueño de **una lista cerrada de archivos**;
nadie toca los de otro. El coordinador integra en orden y corre la suite completa.

| # | Agente | Dueño (archivos) | No toca |
|---|---|---|---|
| **A** | **Color & contraste** | `services/ai_design.py` (`_palette_from_brand`, `_calm_palette`, `_style_colors`, `_band_tone`, `_theme`), `services/ai_design_skins.py` (palets/variantes), `site_theme.py` (solo `filter_site_theme`/`SITE_THEME_*_KEYS`) | reglas de selección, layout |
| **B** | **Composición / rediseño** | `services/ai_design.py` (`_order_for`, `_build_surface`, `_apply_skin_layout`, `_VARIANTS_BY_LAYOUT`, `_block_styles`), `services/ai_design_recipes.py` (`GOAL_RECIPES`, `RUBRO_STYLES`, `AI_PATTERNS`) | tema/color, extras, frontend |
| **C** | **Tipografía** | `services/ai_design_typography.py`, `_theme` **solo** el bloque `typography`/`roles` | paleta, layout |
| **D** | **Extras ("elementos de diseño extra")** | `_add_elements`, `_element_props`, `_V4_ELEMENTS`, `AI_ELEMENT_*` en recipes, vista `ai_design_generate`/`ai_design_apply` (lectura de `accept_extras`) | selección de estilo, tema |
| **E** | **Frontend & publicación** | `frontend/src/views/StorePublicLayout.vue`, `components/studio/previewBridge.js`, `assets/store-page.css` + `skin-*.css`, `stores/api.js` (`storeThemeVars`), `views/design/AiDesignView.vue`, `components/ai/AiProposalCard.vue`, `studio/contract.js` (solo lectura del contrato) | backend |
| **K** | **Coordinador** | `tests_ai_design*.py` (integración), `ENGINE_VERSION`, docs, QA scripts | implementación de fases |

**Protocolo entre agentes**
1. Antes de empezar: leer `AGENTS.md` §"Diseñar con IA", §"Studio", §"Capa de movimiento" y
   este documento. No explorar el repo entero (regla de economía de tokens).
2. Cada agente entrega **un commit** con su fase + sus tests de fase; no toca
   `ENGINE_VERSION` (lo sube K una sola vez, al integrar).
3. Compartición: si una fase necesita un dato de otra, se acuerda en el contrato §2 y se
   implementa **con fallback** (si el campo falta, la fase funciona igual). Nunca dos fases
   editan la misma función "un poquito".
4. K integra en el orden A → B → C → D → E, resuelve conflictos en `_theme` (A y C tocan
   secciones distintas del mismo dict, se mergea por clave) y corre §9 completo.
5. Si una fase descubre que el contrato §2 no alcanza, **se detiene y lo escala a K** con la
   propuesta concreta (campo, tipo, default, consumidor). No se improvisa en el payload.

---

## 4. Fase A — Color: paletas que combinan y texto que se lee

### A.1 Sistema de color (reglas, no gustos)
1. **Un solo acento.** `palette.accent` es la tinta de marca; `primary` lo espeja; `secondary`
   es la tinta de la banda (`_band_tone`). Prohibido derivar más acentos.
2. **Neutros cálidos o fríos, nunca tintados de marca.** `text`/`muted` salen de
   `_desaturate(..., 0.7)` + `_ensure_contrast` (ya existe): conservarlo y **aplicarlo también
   a `styleColors`** (hoy `_style_set` lo hace; garantizar que no se duplique con otro
   criterio).
3. **Fondo y superficie con relación fija**: `surface` a ≤ 8 % de diferencia tonal respecto
   de `bg` en claro y en oscuro (un card blanco puro sobre papel crema se ve "pegado").
   Fórmula: `_mix(bg, text, 0.04–0.06)` si la piel no define surface propio.
4. **Armonía del par acento/fondo**: el acento debe estar a ≥ 4.5 de `bg` y de `surface`
   (enlaces y textos de acento) y el blanco sobre el acento (o sobre `_band_tone`) también
   ≥ 4.5. Añadir al test de paletas.
5. **Modo nocturno coherente**: el set oscuro no es el claro invertido; conserva el acento y
   baja la luminosidad del bg a < 0.1, con surface ≥ 1.08× más clara que bg.

### A.2 Lo que hay que emitir (backend)
- `_theme()` debe incluir en el `site_theme`:
  - `style = {id, palette}` — id del preset del Studio que representa la piel, resuelto con
    `ai_design_skins.SKIN_STYLE_PRESET` / `style_preset_of(skin_id)` (mapeo explícito
    familia → preset; **no** introducir un mapa paralelo), validado contra
    `_STYLE_PRESET_TEMPLATES` de `site_theme.py` y contra `allowed_templates_of(store.user)`.
  - `styleColors = {light, dark}` derivado de `_style_colors(palette, accent)` (ya existe en
    el archivo — reusarlo, no reescribirlo).
  - `typography.roles` con los 13 roles del par (ya lo emite `_theme`; no duplicar lógica).
- `filter_site_theme`: `skin` y `style`/`styleColors` sobreviven al plan Básico (ver
  `PROMPT_FIX_DISENO_IA.md` §C). Un Básico con diseño del motor conserva su piel.
- `_block_styles`: extender la firma por contenido con las claves ya permitidas
  (`radius|shadow|border|density|surface|align|accent`) para que los bloques clave (hero,
  stats, cta, offers, gallery) no queden todos con el mismo contenedor.

### A.3 Contraste — 5 pares x 2 modos
Test obligatorio (parametrizado por las 52 pieles × 8 estilos):
| Par | Mínimo |
|---|---|
| `text` sobre `bg` | 4.5 |
| `muted` sobre `bg` | 4.5 |
| `text` y `muted` sobre `surface` | 4.5 |
| `#fff` sobre botón sólido (`primary` o `_band_tone`) | 4.5 |
| texto del hero (blanco o tinta) sobre banda | 4.5 |

Si una piel no llega en 20 pasos de mezcla: degradar al neutro del modo y anotarlo en
`notes` de la propuesta + `score.issues`.

### A.4 Aceptación A
- Toda propuesta trae `style.colors`, `style` y `skin` aún en plan Básico.
- `test_skin_palettes_pass_aa` ampliado a los 5 pares × 2 modos × 52 pieles: verde.
- Sin cambios visibles en tiendas **sin** `site_theme` (0 regresiones de look).

---

## 5. Fase B — Composición: rediseño real y landing a la medida

### B.1 Principio
La IA **no inventa bloques**: reordena y re-viste el sistema existente (base Cobre). El
rediseño se nota en **orden, agrupación, ritmo vertical y variantes**, y en qué bloques
quedan prendidos según los datos reales.

### B.2 Reglas de composición (implementar en `_build_surface` / `_order_for`)
1. **Ritmo alternado**: nunca dos bloques de "foto grande" seguidos (`featured`, `gallery`,
   `aimosaic`); entre ellos va un bloque de texto o de datos (`about`, `stats`, `benefits`).
   Post-proceso determinista sobre el orden, no aleatorio.
2. **Apertura según objetivo** (ya existe `GOAL_RECIPES`): afinarlo —
   - `vender_online`: hero `search`/`split` → `categories`/`offers` → `featured` →
     `benefits` → `gallery` → `testimonials` → `contact`.
   - `mostrar_trabajos`: hero `cinema`/`editorial` → `gallery` → `about` → `services` →
     `testimonials` → `faq` → `contact`.
   - `conseguir_consultas`: hero `split` → `services` → `benefits` → `steps` → `faq` →
     `cta` → `contact`.
   - `dar_confianza`: hero `centered` → `stats` → `about` → `timeline`/`team` → `brands`
     → `testimonials` → `contact`.
3. **Cierre fijo**: prueba social (`testimonials`/`brands`) antes de `cta`; `contact` siempre
   último (`_enforce_hierarchy` ya lo hace: conservar y testear).
4. **`must_have` manda** (ya existe): los bloques pedidos van en el primer tercio, después
   del hero — y si uno no tiene datos, se avisa en `notes` en vez de mostrarlo vacío.
5. **Densidad por tono**: `serio` → gaps grandes y menos bloques encendidos; `audaz` →
   bloques apilados y compactos; `moderno` → alternancia; `calido` → más aire lateral
   (`gutter: lg`, ya existe en `TONE_TWEAKS`).
6. **Anti-repetición entre propuestas**: la firma `(template, ids de landing, variantes clave
   de las 3 superficies)` debe ser distinta en cada propuesta; si colisiona, **rotar el
   orden** (mover un bloque del grupo medio) hasta 4 intentos (ya hay bucle en `generate`);
   si no alcanza, cambiar de plantilla candidata.
7. **Variantes**: `_VARIANTS_BY_LAYOUT` cubre el resto de bloques (ya está); extender con 2–3
   firmas nuevas ("magazine", "showcase") para que dos pieles del mismo `grid` no coincidan.
8. **Catálogo y servicios también se diseñan**: `filters` (panel/chips), `grid`
   (auto/lead/quick/masonry), `picker` (cards/list/bento/tabs/timeline/packages), `steps`
   (pasos/riel) — todos por id real de `TEMPLATE_BLOCKS`.

### B.3 Landing a la medida (contenido, no invención)
- El motor **usa** lo que hay (`_facts`): nombre, titular, descripción, años, rubro inferido,
  productos con foto/oferta, galería, testimonios, FAQ, servicios, pasos.
- Textos de bloques vacíos: `ai_design_copy` (determinista). Regla nueva: máx 2 bloques
  "textuales inventados" (`aiquote`, `aiband`) por propuesta, y ambos referidos a datos reales
  (años, rubro, número de clientes si existe). Nunca afirmaciones falsas ("N°1 del país").
- `content_hint` (nuevo, §2.3) guía el copy y suma el bloque que lo soporta (`video`,
  `timeline`, `team`, `compare` desde `must_have`).

### B.4 Aceptación B
- `test_proposals_compose_different_structures`: dos propuestas de una generación ≠ firma de
  layout.
- `test_goal_recipe_respected`: el primer bloque (tras hero) es del grupo del objetivo en
  ≥ 90 % de las combinaciones rubro × seed (script de 1200 combinaciones).
- `test_no_image_blocks_adjacent`, `test_contact_last`, `test_must_have_first_third`.
- Ningún orden nuevo cambia el DOM: todas las variantes ya existen en `TEMPLATE_BLOCKS`.

---

## 6. Fase C — Tipografía: 2 familias que conversan

### C.1 Reglas duras
1. **Par = display + cuerpo**, nunca dos displays ni dos serifs de cuerpo
   (`TYPE_PAIRS` ya lo respeta: mantener la invariante en test).
2. **Cuerpo siempre legible**: sans humanista/geométrica a 15–17 px equivalente, `leading`
   1.55–1.75; mono **solo** como display o etiqueta.
3. **Escala con ratio**: `display` 4.8–6 %, `h1` 3–4.5 %, `h2` 2.2–2.8 %, `body` 1, `small`
   .875 — verificar los roles de `roles_for` contra esos rangos en test.
4. **Pesos reales**: usar solo los pesos que la familia tiene (ya hay tabla); nunca inventar
   900 en una 400.
5. **Tracking**: display grande → negativo (−.02/−.03em); etiquetas y mayúsculas → positivo
   (.1–.2em). Prohibido tracking negativo en cuerpo.
6. **Coherencia con la piel**: `ai_design_skins.SKIN_TYPE_PAIR` (por familia) manda; el par
   solo rota entre familias del mismo aire (si la piel es `editorial`, no puede caer un
   `condensed-bold`). `type_pair_of(skin_id)` ya resuelve esto: reusarlo.
7. **Elegancia**: máx 2 familias por web (display + cuerpo). La cita y el precio usan una de
   las dos, nunca una tercera.

### C.2 Aceptación C
- `test_type_pairs_are_distinct_and_valid`: 23 pares de `TYPE_PAIRS` con firmas (display,
  body) únicas y display ≠ body.
- `test_typography_roles_within_scale`: rangos de §C.1-3 para las 52 pieles × 4 tonos.
- `typography.roles` viaja en la propuesta y `styleColors.fonts` coincide con el modo.

---

## 7. Fase D — Extras: la IA propone, el dueño acepta

### D.1 Flujo de producto (obligatorio)
1. **Entrevista**: debajo de "¿Qué debe tener sí o sí?" agregar un bloque
   **"Elementos extra que puedo sumar"** con un switch principal *"Que la IA agregue estos
   elementos"* (default ON) → `accept_extras` (§2.3).
2. **Generar** (`POST /api/stores/ai-design/`): el motor devuelve `extras.offered` ya
   evaluados contra datos, plan y `accept_extras`:
   - `accept_extras:true` (o ausente) → hasta `AI_ELEMENT_MAX` (4) ya incluidos en
     `layout_config` (`applied`) y el resto ofrecidos.
   - `false` → nada se aplica; los 2–4 candidatos quedan en `offered` para que el dueño
     los prenda a mano.
   - `extras: [ids]` → esos ids ganan la prioridad, nunca superan 4 y deben existir en
     `AI_ELEMENT_ORDER`.
3. **Aplicar** (`.../ai-design/apply/`): acepta `extras: [ids]` **y** `skip_extras: bool`;
   recalcula la propuesta (misma semilla) y, antes de publicar, fuerza
   `enabled:false` en los bloques de los extras rechazados (sin borrarlos del layout:
   quedan apagados para que el dueño los prenda después) y `enabled:true` en los aceptados
   si sus props tienen datos reales.
4. **Tarjeta de propuesta** (`AiProposalCard.vue`): chips con los extras aplicados
   (nombre + para qué), botón "Quitar" por extra y "Sumar" en los ofrecidos; el contador
   "N de 4".

### D.2 Reglas de contenido (nunca inventa datos)
- Se ofrece un extra **solo si** tiene datos reales: `aiprocess`/`aipricing`/`aimosaic` ya lo
  exigen (`_element_props`); `aistrip`/`aicheck` usan beneficios/servicios reales;
  `aigrid` usa servicios u horarios; `aiband`/`aiquote` usan datos del negocio.
- `needs` en el payload explica en es-AR qué usa ("Tus 7 fotos de la galería") o "Nada — se
  arma con tu información".
- Gating: sin `has_ai_design` → `offered:[], skipped:[{id, reason:'Tu plan no incluye
  bloques de IA.'}]` y el layout no los incluye (comportamiento v5, que no se rompe).
- Los extras respetan el orden del sistema: se insertan con `AI_ELEMENT_ANCHORS`, nunca
  pasan delante del hero ni después de `contact`, y no rompen la regla de "no dos bloques de
  foto seguidos".

### D.3 Aceptación D
- `test_extras_require_ai_flag` y `test_extras_respect_data_gates` (verdes desde v4: no
  regresionar).
- `test_accept_extras_false_offers_but_does_not_apply`.
- `test_apply_with_rejected_extra_disables_block` (aplicando con `skip_extras`).
- `GET` del payload: `extras.offered[].block.id ∈ TEMPLATE_BLOCKS.landing` y `aiOnly`.
- E2E: generar con extras ON, aplicar, y en la web pública el bloque aparece y se ve bien en
  390/768/1280.

---

## 8. Fase E — Frontend: que el diseño se vea publicado

> Implementa el §F/§G/§H de `PROMPT_FIX_DISENO_IA.md`. Resumen accionable:

1. `StorePublicLayout.vue`: aplicar `pageAttrs` (= `storeSiteThemeAttrs` + skin) al
   `.store-page` **siempre**, importar `skin-<familia>.css` cuando el `site_theme` publicado
   tenga `skin`, y exponer `--sp-on-band*` para textos sobre la banda.
2. `previewBridge.js::storeSiteThemeAttrs`: devolver el set completo de `data-st-*` cuando el
   tema lo fija (mismo mapa que usa el iframe del Studio).
3. `store-page.css`: reemplazar los `#fff`/`rgba(255,255,255,…)` del hero y de las bandas por
   tokens con fallback idéntico al actual; ninguna `skin-*.css` puede declarar colores de
   texto crudos (solo tokens).
4. `AiProposalCard.vue` / `AiDesignView.vue`: mostrar `look.changed` ("Qué cambió"), los
   chips de extras (§7.1-4), `score` como "Se ve así de bien" (sin número frío: 3 barras o
   etiqueta "Excelente/Bueno") y previsualizar la propuesta con **las mismas** vars/attrs de
   la web publicada.
5. Sin tema guardado, la web queda **idéntica** (test visual de regresión con `qa_shots.py`).

### Aceptación E
- `qa_a11y.py` ≥ 4.5:1 en home/catálogo/servicios, claro y oscuro, 6 plantillas activas.
- `qa_overflow.py` 320/360/390/430/768 sin scroll horizontal.
- `npx vite build` verde; sin imports estáticos de las 26 hojas de piel.
- Capturas antes/después de una tienda real aplicando una propuesta del motor (adjuntar).

---

## 9. Aceptación global (K la corre antes de cada push)

1. `manage.py test` completo verde (con `cache.clear()` en `setUp` donde toque, §15.4 de
   `SECURITY_AUDIT.md`).
2. `manage.py check` + `check --deploy` + `ruff check` verdes.
3. `npx vite build` + `pip-audit`/`npm audit --omit=dev` verdes si cambian deps.
4. **Escenario de usuario** (script `qa_ai_design_v6.py`): 3 tiendas de rubros distintos
   (comercio, servicios, gastronomía), misma entrevista → 3 generaciones:
   - cada una con ≥ 2 propuestas; plantillas y firmas de layout distintas;
   - `look.changed` con ≥ 3 cambios reales por propuesta;
   - `score.contrast == 100`;
   - aplicar la propuesta ganadora → web pública con piel (import de `skin-*.css`), acento,
     fuentes y `data-st-*` correctos en `.store-page`;
   - `qa_a11y` sobre la web aplicada: 0 fallas de contraste.
5. Revisión humana de 6 capturas (mobile + desktop) del antes/después: ¿parece una web
   hecha por una agencia? Si no, no se entrega: se ajusta la fase correspondiente.
6. Docs actualizados en el mismo commit (`AGENTS.md` §Diseñar con IA, `ARCHITECTURE.md` flujo
   de publicación, `docs/AI_DESIGN_STYLES_PROMPT.md`, este documento).

---

## 10. Trampas conocidas (ya pagadas — no repetir)

- **`styleColors` manda sobre `palette`** en `previewBridge` para texto/contenedores: si una
  fase emite `palette.text` distinto de `styleColors.fonts.heading`, gana el segundo y el
  primero no se ve. Emitir ambos coherentes.
- **`filter_site_theme` devuelve `{}`** sin `has_design_plus`/`has_design_advanced`: todo campo
  nuevo tiene que entrar en `SITE_THEME_STYLE_KEYS`/`SITE_THEME_PLUS_KEYS` o la web no lo ve.
- **`_v_style_set` valida AA en el PATCH**: un set que no pase da 400 y la propuesta no se
  aplica. El motor debe emitir sets que ya pasen.
- **Cambiar `answers` o el payload exige subir `ENGINE_VERSION`**: si no, la propuesta
  cacheada no coincide con el `proposal_id` y `apply()` responde "la propuesta no existe".
- **El frente de variantes debe usar ids reales**: `TEMPLATE_BLOCKS` es la única fuente; un
  `variant` inventado lo descarta `clean_layout_config` en silencio y la propuesta "no
  rediseña" sin error visible.
- **`_skin_layout_config` + `layout_alt`** (segunda composición por familia): si dos pieles
  de la misma familia caen en la misma propuesta, la firma se repite — usar `layout_alt` para
  las alternativas.
- **Base de facturación**: `billing`/planes del motor usan `allowed_templates_of(store.user)`;
  nunca `allowed_templates_of(store)`.
- **Regla mobile (Regla 0)**: cualquier bloque/variante que toque el frente se prueba a
  320/360/390/430/768; `prefers-reduced-motion`; inputs ≥16px; targets ≥44px.
- **Caché entre `TestCase` con SQLite** (PKs reutilizadas): beneficios y throttles se
  contaminan si falta `cache.clear()`.

---

## 11. Protocolo de entrega

- Rama por fase `feat/ai-design-v6-<letra>`, PR a `main` con: resumen de 5 líneas, diff
  (sin volcados), tests nuevos, capturas y checklist de la fase.
- Mensajes en inglés, conventional: `feat(ai-design): ...`, `fix(ai-design): ...`.
- **Nada de "funciona en mi máquina"**: la evidencia son los tests + el script de escenario
  §9.4 + capturas.
- Si una fase no puede cumplir un criterio de §9, se entrega igual **con el criterio marcado
  como pendiente y el riesgo escrito** en el PR; K decide si bloquea el release.
- Commit final de integración: `feat(ai-design): engine v6 — colors, composition, extras`
  con `ENGINE_VERSION='ai-design/6'`.
