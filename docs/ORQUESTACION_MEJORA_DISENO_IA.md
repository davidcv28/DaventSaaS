# Orquestación — mejoras de "Diseñar con IA"

> Anexo operativo de `docs/IDEAS_MEJORA_DISENO_IA.md`. El documento de ideas define **qué**
> mejorar y por qué; este define **quién lo construye, en qué orden, con qué contrato y con
> qué evidencia se acepta**. Cubre las 4 fases del roadmap de ideas (credibilidad, decisión,
> retención, opcional).
>
> Motor actual: `ai-design/8`, determinista y offline, en
> `StoreApp/domains/stores/services/ai_design.py` (2744 líneas) + `ai_design_recipes.py`
> (871) + `ai_design_skins.py` (924) + `ai_design_copy.py` (370) +
> `ai_design_typography.py` (433). API en `StoreApp/domains/stores/views/viewset.py`
> (`ai_design`, `ai_design_apply`, `ai_design_image`). UI en
> `frontend/src/views/design/AiDesignView.vue` + `frontend/src/api/stores.api.js`.

---

## 0. Reglas del reparto

| Regla | Por qué |
|---|---|
| **Un carril = un dueño de archivo.** Dos agentes nunca editan el mismo archivo en paralelo; si pasa, el trabajo no es paralelo, es conflicto. | `ai_design.py` concentra 30+ funciones: es el cuello de botella real. |
| **El contrato (§2) se congela antes de repartir.** Nadie de fase inventa payload nuevo. | Los carriles de UI y API consumen; el motor produce. |
| **Nadie toca `ENGINE_VERSION` salvo K**, una vez por integración. | La semilla depende de la versión; si cada carril la sube, se pierde el determinismo y los snapshots. |
| **Se integra en orden K → 1 → 2 → 3 → 4**, y dentro de cada fase en el orden de §3. | Hay dependencias reales (score necesita secciones honestas; comparador necesita propuestas persistidas). |
| **Sin criterio de aceptación en verde no se avanza.** | Evita "casi terminado" acumulado. |
| **Toda feature nueva del motor trae test de contrato + snapshot de propuesta.** | `tests_ai_design_contract.py` ya es la red de seguridad; se extiende, no se reemplaza. |

**Carriles (ownership fijo):**

| Carril | Agente | Archivos propios | No toca |
|---|---|---|---|
| **K** | Integrador / contrato | `ai_design_recipes.py` (solo `ENGINE_VERSION` y tablas de §2), `docs/ORQUESTACION_*` | lógica de cada carril |
| **M** | Motor (secuencial) | `services/ai_design.py` | frontend, viewset, skins |
| **C** | Copy | `services/ai_design_copy.py` | `ai_design.py` (solo recibe llamadas) |
| **S** | Pieles y tipografía | `services/ai_design_skins.py`, `services/ai_design_typography.py` | `ai_design.py` |
| **B** | API y datos | `views/viewset.py`, `serializers/`, `models/models.py`, `migrations/` | motor, frontend |
| **F** | Frontend IA | `frontend/src/views/design/AiDesignView.vue`, `frontend/src/api/stores.api.js` | backend |
| **T** | Telemetría | `models/models.py` (solo modelos nuevos), `services/ai_design_telemetry.py` (nuevo), `views/viewset.py` (solo actions nuevas, coordinado con B) | motor |
| **W** | Web publicada / SEO | `frontend/src/utils/seo.js`, `StoreHomeView.vue`, `deploy/nginx*`, `public_cache.py` | motor, UI de IA |
| **Q** | QA y regresión | `tests_ai_design*.py`, `tests/snapshots/` | código de producción |

**Colisión conocida `models.py`:** B y T comparten archivo. Se resuelve con ventana: T entrega
solo modelos nuevos al final de la fase 1 y B los migra en la integración; nunca en simultáneo.

---

## 1. Dependencias entre fases y carriles

```
K  contrato §2 ───────────────────────────────────────────────┐
                                                              │
FASE 1 (credibilidad)                                         │
  M  0.1 must_have real  ─┐                                   │
  C  0.2 audience/copy    ├─ secuencial en ai_design.py        │
  M  0.3 score honesto   ─┘                                   │
  M  2.5 secciones honestas ── depende de 0.1 (mismo mapa)     │
  T  5.1 telemetría ─────────── depende de 0.1/0.3 (eventos)   │
  F  consume contrato nuevo                                   │
  Q  snapshots de la tanda "aprobada" antes de cerrar         │
                                                              ▼
FASE 2 (decisión)
  B  2.3 persistir tanda + ?seed=&proposal=  ── base de 3.1/3.4
  M  1.1 prefill (reusa _guess_rubro/_guess_goals)
  C  1.2 parser de brief (content_hint)  ── depende de 1.1
  S  1.3 análisis de fotos (Pillow)      ── depende de 2.3
  M  2.1 playbooks de conversión         ── depende de 0.3 (score por tesis)
  F  3.1 comparador                       ── depende de 2.3
  M  3.2 refine (constraints parciales)   ── depende de 2.3 + 2.1
  B  3.4 preview privada con token        ── depende de 2.3
                                                              ▼
FASE 3 (retención)
  W  4.1 OG para bots (nginx)  4.2 SEO/JSON-LD por tienda
  M  4.3 auto-fix desde health.js  ── depende de 2.5
  C  4.4 copy assist offline
  M  4.5 modo campaña
  M  1.4 paleta desde logo · 1.5 arte sin fotos
  M  2.2 diversidad entre tandas ── depende de 2.3
  M  2.4 plan-aware opt-in
  B  3.3 historial/diff (StudioVersion)
  F  3.5 checklist de publicación
  T  5.2 feedback por propuesta · 5.3 eventos de conversión
  Q  5.4 golden set
                                                              ▼
FASE 4 (opcional)
  6.1 LLM acotado — solo si 5.1/5.3 tienen datos que lo justifiquen
```

**Por qué 0.3 antes de 2.1:** un playbook sin score medible no se puede evaluar; el score
honesto es el instrumento de medida de la tesis.
**Por qué 2.3 antes de 3.1/3.2/3.4:** sin tanda persistida no hay comparador, ni refine, ni
preview privada: las tres son la misma tanda con otra vista.

---

## 2. Contrato congelado (lo cierra K el día 0)

Todo lo de abajo se define en `ai_design_recipes.py` (tablas) + docstring de `generate`, y no
se cambia dentro de una fase.

### 2.1 `must_have`: opción de UI → bloque/ajuste real

| UI (`AiDesignView.vue:74-79`) | Bloque(s) | Ajuste |
|---|---|---|
| `whatsapp` | `contact` + `cta` | `show_whatsapp` |
| `hours` | `contact` | variante `hours` con horarios del perfil |
| `map` | `contact` | variante `map` + `show_location` |
| `prices` | `offers` (o `aipricing` si hay catálogo) | — |
| `testimonials` | `testimonials` | — |
| `faqs` | `faq` | — |

`notes` solo afirma lo aplicado; si el dato no existe (`hours` sin horarios), se aplica el
bloque pero la nota dice qué falta (regla 2.5).

### 2.2 Score (`_score`, hoy `ai_design.py:2100`)

```json
{"total": 0-100, "label": "string", "parts": {"data": 0-100, "density": 0-100,
 "copy": 0-100, "assets": 0-100}, "todo": ["string"]}
```

- Sin señal nueva no se muestra número: si `parts` es todo neutro, `total: null`.
- `todo` es la lista accionable ("falta foto de portada", "3 productos sin precio").

### 2.3 Entradas vivas

`audience` (`AUDIENCES` en la UI) y `content_hint` (texto libre, hoy no enviado) se consumen
en layout (densidad/orden) y copy (`ai_design_copy`). Si un campo no se consume, se saca del
contrato en vez de dejarlo viajar muerto.

### 2.4 Endpoints nuevos (B)

| Endpoint | Payload | Respuesta |
|---|---|---|
| `GET /api/stores/ai-design/prefill/` | — | `{rubro, goals, counts:{products, photos, categories}, missing:[]}` |
| `POST /api/stores/ai-design/refine/` | `{seed, proposal_id, constraints}` | propuesta completa + `delta` |
| `POST /api/stores/ai-design/persist/` | `{seed, proposals}` | `{token, expires_at}` |
| `GET /api/stores/ai-design/preview/<token>/` | — (AllowAny, `noindex`) | HTML/JSON de la propuesta |
| `POST /api/stores/ai-design/feedback/` | `{proposal_id, verdict, reason?}` | `{ok}` |

Throttles nuevos (mismos scopes que `ai_design`): `ai_design_refine`, `ai_design_preview`,
`ai_design_feedback`.

### 2.5 Telemetría (T)

`AiDesignEvent(store, session, step, action, proposal_id?, meta JSON, created_at)`.
Acciones mínimas: `step_done`, `step_abandon`, `generate`, `explore`, `apply`, `extras`,
`refine`, `feedback`, `publish`.

---

## 3. Fichas por carril (pegar una por sesión)

### Fase 1 — Credibilidad (1-2 semanas)

#### Agente M1 — `must_have` real + secciones honestas (0.1 + 2.5)

```
ROL: senior backend Python/Django, motor determinista sin LLM.
CONTEXTO: docs/IDEAS_MEJORA_DISENO_IA.md §0.1 y §2.5. No explores el repo: usá grep por
  función. Leé solo los rangos citados.
ARCHIVOS TUYOS: StoreApp/domains/stores/services/ai_design.py
  (_answers 388, _element_candidates 1557, _element_props 1448, _element_needs 1535,
   _add_elements 1651, _variant_for 984, _notes 1978).
  StoreApp/domains/stores/services/ai_design_recipes.py: solo las tablas nuevas de §2.1.
NO TOQUES: _score, frontend, viewset, skins, ENGINE_VERSION.
ENTREGAR:
  1. Mapa UI→bloque/ajuste de §2.1 aplicado en _element_candidates/_element_props.
  2. Gate de contenido derivado: aipricing con <2 productos, stats sin cifras, about sin
     texto, hours sin horarios → bloque apagado o variante sin promesa.
  3. Hero centered con nombre > 32 chars → cambia de variante, no recorta.
  4. notes afirma solo lo aplicado y lista lo que falta.
EVIDENCIA: tests en tests_ai_design.py para las 6 opciones × con/sin dato; 1 JSON de
  propuesta por caso guardado en docs/qa/.
ACEPTA CUANDO: las 6 opciones cambian el layout; ningún bloque promete dato inexistente.
```

#### Agente C1 — `audience` + `content_hint` (0.2)

```
ROL: senior copywriter técnico + Python.
ARCHIVOS TUYOS: StoreApp/domains/stores/services/ai_design_copy.py
NO TOQUES: ai_design.py (pedí a M1 la firma de llamada; se integra K).
ENTREGAR:
  1. Copy por audiencia (AUDIENCES de la UI) en hero/about/cta.
  2. content_hint: variante de titular/subtítulo cuando llega texto; sin inventar datos.
  3. Si un campo no se puede consumir, documentar y proponer sacarlo del contrato.
EVIDENCIA: tests de copy por audiencia; diff de 3 propuestas (rubro gastronomía, servicios,
  retail) antes/después.
ACEPTA CUANDO: cambiar audience cambia al menos 2 textos por propuesta.
```

#### Agente M2 — score honesto (0.3)

```
ROL: senior backend con criterio de producto.
ARCHIVOS TUYOS: StoreApp/domains/stores/services/ai_design.py → _score (2100),
  _contrast_notes (2140), _why (1966), _notes (1978).
NO TOQUES: layout, selección, frontend.
ENTREGAR: contrato §2.2 (parts + todo + total null cuando no hay señal), sin número fijo.
  parts: data (completitud de perfil/catálogo), density (bloques vs contenido real),
  copy (largo/CTA/repetición), assets (fotos faltantes o pobres).
EVIDENCIA: 5 tiendas fixture → 5 totales distintos; una sin fotos da assets bajo y todo
  accionable; ninguna propuesta vuelve a dar 95-97 siempre.
ACEPTA CUANDO: dos propuestas distintas difieren ≥8 puntos y el label deja de ser fijo.
```

#### Agente T1 — telemetría del funnel (5.1)

```
ROL: backend Django + analítica de producto.
ARCHIVOS TUYOS: services/ai_design_telemetry.py (nuevo), modelos nuevos en models/models.py
  (coordinado con B: solo al final), action nueva en views/viewset.py (coordinado con B).
NO TOQUES: motor, frontend (F1 consume el endpoint).
ENTREGAR: modelo §2.5 + POST /api/stores/ai-design/event/ (IsAuthenticated, throttle
  ai_design) + retención 365 días + comando prune_ai_design_events.
EVIDENCIA: test de alta/lectura por tienda y de que no se guarda PII (solo ids y meta corta).
ACEPTA CUANDO: se puede responder "abandono por paso" con una query.
```

#### Agente F1 — UI del contrato nuevo

```
ROL: senior Vue 3.
ARCHIVOS TUYOS: frontend/src/views/design/AiDesignView.vue, frontend/src/api/stores.api.js
NO TOQUES: backend.
ENTREGAR: score con parts/todo, must_have con las 6 opciones reales, envío de audience,
  content_hint (solo si C1 lo consume), eventos de telemetría por paso, sin romper
  localStorage de respuestas.
EVIDENCIA: build + captura de la sección con una propuesta real.
ACEPTA CUANDO: ninguna opción de la UI queda sin efecto visible.
```

#### Agente Q1 — red de seguridad

```
ARCHIVOS TUYOS: tests_ai_design*.py, docs/qa/snapshots/
ENTREGAR: snapshot (seed + payload + JSON de propuesta + captura) de 6 combinaciones
  aprobadas antes de la fase 1, y un runner que falle si cambia la composición.
ACEPTA CUANDO: el runner detecta un cambio de orden de bloques inyectado a propósito.
```

### Fase 2 — Decisión (4-6 semanas)

| Carril | Ítem | Entregable | Depende de |
|---|---|---|---|
| B2 | 2.3 | Persistir tanda (`AiDesignRun` o cache con TTL), `?seed=&proposal=`, retomar | Fase 1 |
| M3 | 1.1 | `prefill` que expone `_guess_rubro`/`_guess_goals` + conteos reales | B2 (endpoint) |
| C2 | 1.2 | Parser offline de brief → `content_hint` normalizado (diccionario de rubro + `_fold`) | M3 |
| S1 | 1.3 | Upload en entrevista + análisis Pillow (ratio, luminancia, nitidez) → variante de hero y desbloqueo de `gallery`/`aimosaic`/`featured` | B2 |
| M4 | 2.1 | 3 playbooks de conversión (catálogo, servicios/presupuesto, confianza/local) atados a `why` | 0.3 |
| F2 | 3.1 | Comparador 2-3 columnas + tabla de diferencias | B2 |
| M5 | 3.2 | `refine` con constraints parciales, devuelve delta no tanda | B2 + M4 |
| B3 | 3.4 | Preview privada con token, `noindex`, TTL | B2 |
| K2 | — | Subir `ENGINE_VERSION` a `ai-design/9` y regenerar snapshots | todo lo anterior |

**Ficha resumen para pegar (carril M, fase 2):**

```
ROL: senior backend del motor determinista.
ARCHIVOS TUYOS: services/ai_design.py (generate 2411, apply 2617, _answers 388,
  _style_candidates 575, _explore_styles 779, _order_for 919, _build_surface 1011).
NO TOQUES: copy, skins, viewset, frontend, ENGINE_VERSION (lo sube K2).
ENTREGAR: prefill, playbooks con tesis, refine por constraints sobre la misma seed.
REGLAS: refine reusa seed + overrides y devuelve delta; nunca genera una web fuera del plan;
  nunca inventa datos del negocio.
ACEPTA CUANDO: refine "solo cambiá la tipografía" cambia tipografía y nada más (diff de
  layout vacío) y "menos secciones" baja densidad sin romper gates de 2.5.
```

### Fase 3 — Retención (6-8 semanas)

| Carril | Ítem | Entregable | Depende de |
|---|---|---|---|
| W1 | 4.1 | Detección de bots de preview en nginx (`$http_user_agent`) → HTML mínimo con OG + JSON-LD | — |
| W2 | 4.2 | title/description/OG por rubro+ciudad, JSON-LD `Product`/`Offer`/`FAQPage`/`AggregateRating`, sitemap por tienda | W1 |
| M6 | 4.3 | Auto-fix desde `components/studio/health.js`: bajar densidad, cambiar variante de hero, acortar titular, pedir foto | 2.5 |
| C3 | 4.4 | Copy assist offline (largo, repetición, CTA, jerga) sobre el editor de "Mi empresa" | C1 |
| M7 | 4.5 | Modo campaña AR (Hot Sale, Navidad, Día del Padre, vuelta a clases) con vencimiento | 2.3 |
| S2 | 1.4 | Paleta desde logo (Pillow + clustering) dentro del catálogo cerrado de acento | — |
| S3 | 1.5 | Arte determinista por rubro/piel para portadas sin foto | — |
| M8 | 2.2 | Diversidad entre tandas (historial de ternas por tienda) | 2.3 |
| M9 | 2.4 | Propuesta opt-in "cómo se vería con Premium", secciones bloqueadas marcadas | 2.1 |
| B4 | 3.3 | Historial y diff contra `StudioVersion` (models.py:480) | 2.3 |
| F3 | 3.5 | Checklist persistente de publicación con auto-fix donde el motor pueda | M6 |
| T2 | 5.2 | Feedback por propuesta + afinidad local (prior simple, sin LLM) | T1 |
| T3 | 5.3 | Eventos outbound (WhatsApp/contacto/catálogo) + ranking por conversión en `_style_candidates` | T1 |
| Q2 | 5.4 | Golden set con snapshots de las propuestas aprobadas | Q1 |

### Fase 4 — Opcional (6.1, LLM acotado)

Prerrequisitos **todos** en verde antes de abrir la puerta: 5.1 y 5.3 con ≥4 semanas de datos,
coste por generación medido, y parser offline (1.2) + copy assist (4.4) ya en producción.
Alcance máximo: `brief → respuestas normalizadas` y `texto → copy`. **Nunca `layout_config`.**
Guardas: validación contra contrato, cache por hash, tope por cuenta, timeout, fallback al
motor local, y ningún texto generado se publica sin pasar por el gate de datos reales.

---

## 4. Gates de integración (los corre K)

| Gate | Qué corre | Verde si |
|---|---|---|
| G1 | `venv/Scripts/python.exe manage.py test StoreApp.domains.stores.tests_ai_design*` | 0 fallos |
| G2 | `manage.py check` + `ruff check` del área tocada | sin errores nuevos |
| G3 | Q: snapshots de 6 combinaciones | diff solo donde la fase lo declara |
| G4 | 3 tiendas reales (gastronomía, servicios, retail) con captura antes/después | composición no rota, contraste ≥4.5 |
| G5 | `frontend`: build + captura de `AiDesignView` | sin errores de consola |
| G6 | Plan Básico y Premium | el motor nunca propone lo que el plan no publica |

**Cierre de fase:** `ENGINE_VERSION` +1 solo si cambió la composición; commit
`feat(ai-design): fase N ...` con capturas y snapshots; push a `main`.

---

## 5. Riesgos y decisiones ya tomadas

| Riesgo | Mitigación |
|---|---|
| `ai_design.py` es cuello de botella (30+ funciones) | Un solo carril M, secuencial; el resto de carriles no lo toca. |
| Score nuevo vuelve a ser cosmético | Gate: 5 fixtures con totales distintos y ≥8 puntos de diferencia. |
| `must_have` que promete horarios/mapa sin dato | Regla 2.5: bloque apagado o variante sin promesa + `todo`. |
| Persistir tandas infla la DB | TTL (7 días) + prune; token opaco, sin PII. |
| Preview privada filtrada | Token de un solo uso con TTL, `noindex`, throttle dedicado. |
| Playbooks se vuelven "otro color" | Cada propuesta declara tesis + CTA + prueba social; G3 falla si dos comparten firma de layout. |
| LLM rompe el determinismo | Fase 4 con alcance acotado y fallback; `layout_config` prohibido. |

**Qué no hacer (heredado de ideas §"Qué NO hacer"):** datos inventados, score que no
discrimina, cambios automáticos sin deshacer, layout generado por LLM.

---

## 6. Calendario

| Fase | Contenido | Duración | Gate de salida |
|---|---|---|---|
| 0 | Contrato §2 + snapshots Q1 | 2-3 días | contrato congelado, `ENGINE_VERSION` intacto |
| 1 | 0.1, 0.2, 0.3, 2.5, 5.1 | 1-2 semanas | G1-G6 + telemetría respondiendo abandono por paso |
| 2 | 1.1, 1.2, 1.3, 2.1, 2.3, 3.1, 3.2, 3.4 | 4-6 semanas | `ai-design/9`, refine con delta verificado |
| 3 | 4.1-4.5, 5.2-5.4, 1.4, 1.5, 2.2, 2.4, 3.3, 3.5 | 6-8 semanas | conversión por estilo medible |
| 4 | 6.1 si y solo si los datos lo justifican | — | coste/beneficio documentado |

---

## 7. Estado de ejecución

| Fase | Ítem | Estado | Evidencia |
|---|---|---|---|
| 0 | Contrato §2 | Hecho | `MUST_HAVE_BLOCKS`/`MUST_HAVE_DATA`/`STEP_LABELS` en `ai_design_recipes.py` |
| 1 | 0.1 must_have real | Hecho | `_answers` + `_must_have_has_data` + `_apply_must_have_variants`; tests `MustHaveTests` |
| 1 | 0.2 audience/content_hint | Hecho | `ai_design_copy.AUDIENCE_COPY`/`_clean_hint`; tests `CopyInputTests` |
| 1 | 0.3 score honesto | Hecho | `_score` con `parts`/`todo`/`label` y `total: null` sin señal; tests `ScoreTests` |
| 1 | 2.5 secciones honestas | Hecho | gates de `stats` con filas reales, hero `centered`→`compact`, notas con lo que falta; tests `HonestSectionsTests` |
| 1 | 5.1 telemetría | Hecho | `AiDesignEvent` (mig. 0056) + `POST /api/stores/ai-design/event/` + `prune_ai_design_events`; tests `TelemetryTests` |
| 1 | Q1 snapshots | Parcial | invariantes de layout + `snapshot_ai_design` para el golden set operativo |
| 2-4 | restantes | Pendiente | — |
