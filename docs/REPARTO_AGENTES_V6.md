# Reparto de tareas — "Diseñar con IA" v6

> Anexo operativo de `docs/PROMPT_DISENO_IA_V6_BRIEF.md`. El brief define **qué** hay que
> construir; este documento define **quién lo construye, en qué orden y con qué evidencia**.
> Todo lo acá escrito se pega tal cual en la sesión de cada agente.

---

## 0. Regla de oro del reparto

| Regla | Por qué |
|---|---|
| **Un agente = un dueño de archivo.** Si dos agentes pueden editar el mismo archivo, no es paralelo: es conflicto garantizado. | El brief asigna funciones concretas, no archivos sueltos. |
| **El contrato (§2 del brief) se congela antes de repartir.** | La gente de fase no decide el payload; solo lo consume. |
| **Nadie toca `ENGINE_VERSION`.** Lo sube K, una sola vez, al integrar. | Si cada fase lo sube, la semilla cambia a mitad del trabajo y se pierde el determinismo. |
| **Se integra en orden A → B → C → D → E**, nunca todo junto. | A y C escriben en `_theme`; B depende de que A haya fijado el contrato de color. |
| **Un agente no avanza si su criterio de aceptación no está en verde.** | Evita "casi terminado" acumulado. |

---

## 1. Orden real de ejecución (no todos arrancan juntos)

```
Día 0   K  cierra el contrato (§2) y abre las ramas
Día 1   A (color)  ──┐
        C (tipografía) ─┤  pueden ir en paralelo: A toca palette/styleColors,
        E (frontend)  ──┘  C toca typography/roles, E no toca backend
        D (extras)  ──┐  puede ir en paralelo: solo _add_elements/_element_props
        B (composición) ┘  arranca cuando A entregó (necesita el color estable para medir)
Día 2   K  integra A → C → B → D → E y corre §9
Día 3   K  aplica a 3 tiendas reales, adjunta capturas, ajusta la fase que falle
```

**Por qué B va después de A:** la composición se evalúa mirando capturas de la propuesta;
si el color todavía cambia, se compone a ciegas y se rehace.

**Por qué E puede ir en paralelo:** E solo consume el `site_theme` publicado y los
`data-st-*`. Trabaja contra fixtures (un JSON de propuesta de ejemplo), no contra el motor.

---

## 2. Fichas por agente (pegar una por sesión)

### Agente A — Color y contraste

```
ROL: senior frontend/design-systems engineer especializado en color, contraste y accesibilidad.
CONTEXTO: leer docs/PROMPT_DISENO_IA_V6_BRIEF.md §2 (contrato) y §4 (tu fase). No explores
  el repo entero: usa grep para ubicar las funciones nombradas.
ARCHIVOS TUYOS (solo estos):
  - StoreApp/domains/stores/services/ai_design.py  → _palette_from_brand, _calm_palette,
    _style_set, _style_colors, _band_tone, _theme
  - StoreApp/domains/stores/services/ai_design_skins.py → palets y variantes de las 26 familias
  - StoreApp/domains/stores/site_theme.py → filter_site_theme, SITE_THEME_PLUS_KEYS,
    SITE_THEME_STYLE_KEYS
NO TOQUES: reglas de selección (_select_styles, _style_candidates), _build_surface,
  _apply_skin_layout, _add_elements, engine version, frontend.
ENTREGAR:
  1. _theme emite style {id, palette} + styleColors {light, dark} + typography.roles.
  2. filter_site_theme conserva skin/styleColors en plan Básico.
  3. Tests: 5 pares de contraste × 2 modos × 52 pieles = verde; y tienda sin site_theme
     se ve idéntica (regresión).
EVidencia: los tests + un JSON de propuesta de ejemplo guardado en el PR.
ACEPTA CUANDO: §4.4 del brief completo.
```

### Agente B — Composición y rediseño

```
ROL: senior frontend/designer que sabe traducir un brief de negocio a jerarquía de landing.
CONTEXTO: docs/PROMPT_DISENO_IA_V6_BRIEF.md §5. Esperá a que A haya entregado (color estable).
ARCHIVOS TUYOS: _order_for, _build_surface, _enforce_hierarchy, _apply_skin_layout,
  _VARIANTS_BY_LAYOUT, _block_styles (ai_design.py); GOAL_RECIPES, RUBRO_STYLES,
  AI_PATTERNS, HIERARCHY_RULES, BLOCK_GATES, BLOCK_FALLBACKS (ai_design_recipes.py).
NO TOQUES: paletas, tipografía, extras, viewset, frontend.
ENTREGAR:
  1. Ritmo alternado foto/texto (post-proceso determinista).
  2. Recetas de apertura por objetivo afinadas (§5.2-2).
  3. Firme anti-repetición: dos propuestas nunca comparten firma de layout.
  4. Variantes reales para catálogo y servicios.
ACEPTA CUANDO: §5.4 completo (incluye el script de 1200 combinaciones).
TRAMPA: solo ids de variante de TEMPLATE_BLOCKS; uno inventado se descarta en silencio.
```

### Agente C — Tipografía

```
ROL: senior frontend/type designer. Dueño de la voz tipográfica del producto.
CONTEXTO: docs/PROMPT_DISENO_IA_V6_BRIEF.md §6.
ARCHIVOS TUYOS: services/ai_design_typography.py completo; en _theme SOLO el bloque
  typography/roles (coordina el merge por clave con A).
NO TOQUES: paleta, layout, extras, frontend.
ENTREGAR:
  1. Reglas de par (display+cuerpo), escala con ratio, pesos reales, tracking por rol.
  2. SKIN_TYPE_PAIR respetado: la piel manda el aire, el par rota dentro del aire.
  3. Tests: firmas únicas, roles dentro de rango, 52 pieles × 4 tonos.
ACEPTA CUANDO: §6.2 completo.
```

### Agente D — Extras (la IA propone, el dueño acepta)

```
ROL: product engineer backend + frontend del flujo de "elementos extra".
CONTEXTO: docs/PROMPT_DISENO_IA_V6_BRIEF.md §2.2/§2.3/§2.4 y §7.
ARCHIVOS TUYOS: _add_elements, _element_props, _V4_ELEMENTS (ai_design.py); AI_ELEMENT_ORDER,
  AI_ELEMENT_ANCHORS, AI_ELEMENT_MAX (recipes); payload extras/score en _build; vista
  ai_design_generate/ai_design_apply (lectura de accept_extras, extras, skip_extras);
  componentes de UI de la entrevista y de la tarjeta (AiDesignView, AiProposalCard).
NO TOQUES: selección de estilo, paleta, _order_for.
ENTREGAR:
  1. Campo extras.offered/applied/skipped + score en cada propuesta.
  2. Endpoints que respetan accept_extras/extras/skip_extras.
  3. UI: switch de la entrevista + chips con Quitar/Sumar en la tarjeta.
  4. Tests de gating por has_ai_design y por datos reales.
ACEPTA CUANDO: §7.3 completo + E2E visual en 390/768/1280.
```

### Agente E — Frontend y publicación

```
ROL: senior frontend (Vue 3 + CSS token systems). El que hace que el diseño se VEA publicado.
CONTEXTO: docs/PROMPT_DISENO_IA_V6_BRIEF.md §8 + docs/PROMPT_FIX_DISENO_IA.md §F/§G/§H.
ARCHIVOS TUYOS: views/StorePublicLayout.vue, components/studio/previewBridge.js,
  assets/store-page.css, assets/skin-*.css, stores/api.js (storeThemeVars),
  views/design/AiDesignView.vue, components/ai/AiProposalCard.vue.
  studio/contract.js es SOLO LECTURA (si falta un campo, lo pedís a K).
NO TOQUES: backend, ENGINE_VERSION.
ENTREGAR:
  1. pageAttrs (data-st-*) + piel aplicados siempre, no solo en ?studio=1.
  2. Tokens --sp-on-band* en vez de #fff hardcodeado en hero/bandas.
  3. Tarjeta con look.changed + chips de extras + score legible.
  4. Regresión: tienda sin tema idéntica.
ACEPTA CUANDO: §8 "Aceptación E" + qa_a11y + qa_overflow + vite build.
```

### Agente K — Coordinador

```
ROL: tech lead. No implementa fases: integra, verifica y decide.
RESPONSABILIDADES:
  1. Congelar el contrato §2 y publicarlo antes de abrir ramas.
  2. Subir ENGINE_VERSION a 'ai-design/6' UNA vez, en el commit de integración.
  3. Integrar en orden A → C → B → D → E (merge por clave en _theme entre A y C).
  4. Correr §9 completo + el escenario de 3 tiendas reales.
  5. Actualizar AGENTS.md, ARCHITECTURE.md, docs/AI_DESIGN_STYLES_PROMPT.md.
  6. Si una fase se cuelga 2 iteraciones en el mismo criterio: la pausa, la reasigna o
     reduce el alcance; nunca entrega a medias.
```

---

## 3. Qué le pasás a cada agente (paquete mínimo)

Cada sesión arranca con **exactamente** esto, nada más:

1. `AGENTS.md` §"Diseñar con IA", §"Studio", §"Capa de movimiento de la web pública".
2. `docs/PROMPT_DISENO_IA_V6_BRIEF.md` → §2 (contrato) + su §4–§8.
3. `docs/REPARTO_AGENTES_V6.md` → su ficha (§2).
4. La salida de lo que entregó el agente anterior **solo si su fase depende de eso** (ej.: B
   recibe el JSON de propuesta que dejó A).

**No** le pases el repo entero, ni el brief de otro agente, ni `PROMPT_FIX_DISENO_IA.md`
completo (E sí lo necesita; A–D no).

---

## 4. Tabla de conflictos posibles (resolución anticipada)

| Zona | Quién | Conflicto | Resolución |
|---|---|
| `_theme()` | A (secciones palette/styleColors) y C (typography/roles) | dos edits al mismo dict | cada uno toca su clave; K mergea por clave, nunca reescribe la función |
| `ai_design.py` | A, B, D | tres fases, un archivo | funciones distintas; si una fase necesita cambiar firma de otra, lo escala a K |
| `ai_design_recipes.py` | B y D | B toca `GOAL_RECIPES`, D toca `AI_ELEMENT_*` | bloques separados del archivo; D no cambia recetas |
| `site_theme.py` | A | `filter_site_theme` se comparte con el Studio | A solo agrega claves al keep-set; no cambia la lógica del Studio |
| `previewBridge.js` | E | lo comparte el Studio | E agrega funciones, no cambia las que usa el iframe del Studio |
| `contract.js` | E (lectura) y K | nadie es dueño en esta fase | si falta un campo, E lo pide a K y K decide si entra al contrato |

---

## 5. Definición de "terminado" (igual para los cinco)

Un agente terminó cuando, en su rama:

- [ ] los tests de su fase pasan **y** los de la fase anterior siguen pasando;
- [ ] `manage.py check` + `ruff check` verdes (o `npx vite build` si es frontend);
- [ ] el PR explica en 5 líneas **qué cambió en el usuario final** (no en el código);
- [ ] adjunta 1 captura (o JSON) de evidencia por criterio de aceptación;
- [ ] no tocó ningún archivo fuera de su lista de dueño.

---

## 6. Ejemplo de mensaje de arranque (copiar y adaptar)

```
Vas a trabajar en la fase <A|B|C|D|E> del motor "Diseñar con IA" v6.
Leé, en este orden y sin explorar el resto del repo:
  1. docs/REPARTO_AGENTES_V6.md → tu ficha.
  2. docs/PROMPT_DISENO_IA_V6_BRIEF.md → §2 y §<de tu fase>.
  3. AGENTS.md → §"Diseñar con IA".
Rama: feat/ai-design-v6-<letra>. Dueño de archivos: los de tu ficha, ningún otro.
No toques ENGINE_VERSION.
Entregá: implementación + tests de fase + PR de 5 líneas con evidencia.
Si el contrato §2 no alcanza, detenete y escalate a K con (campo, tipo, default, consumidor).
```
