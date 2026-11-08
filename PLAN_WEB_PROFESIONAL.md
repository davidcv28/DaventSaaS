# Plan — Webs profesionales para clientes (orquestación por agentes)

> Documento operativo. Cada sección de prompt está lista para copiar y pegar en una
> sesión de agente nueva. Los prompts son autocontenidos: el agente no ve esta
> conversación, así que todo el contexto necesario está dentro de cada bloque.

---

## 0. Definición de "profesional" (medible, no opinable)

Un diseño se considera apto para clientes cuando cumple **todo** esto:

| # | Criterio | Cómo se mide |
|---|----------|--------------|
| 1 | Sin scroll horizontal | `scrollWidth <= clientWidth + 1` a 390 / 768 / 1360 |
| 2 | Sin errores de consola | 0 `console.error` y 0 `pageerror` |
| 3 | Contraste AA | ratio >= 4.5 en texto normal, >= 3.0 en >= 24px o bold >= 19px |
| 4 | Sin hardcodes fuera de tokens | 0 hex/px de color, radio o sombra sueltos en `store-*.css` y patrones |
| 5 | Sin pares tipográficos inválidos | `FONT_PAIRS` marcados por diseño, bloqueados en el panel |
| 6 | Sin huecos por contenido faltante | secciones vacías apagadas con `:has` / `:empty` |
| 7 | Sin CLS perceptible | `aspect-ratio` + `width/height` en toda imagen, CLS < 0.1 |
| 8 | Movimiento compuesto | solo `transform` / `opacity` animados, `prefers-reduced-motion` apaga todo |
| 9 | Seguridad del markup intacta | iframe sandbox sin `allow-same-origin`, CSP sin `unsafe-inline` |

---

## 1. Mapa de olas y propiedad de archivos

Nadie escribe en el archivo de otro. Si un track necesita un cambio fuera de su
scope, **lo reporta**; no lo hace.

| Ola | Agente | Objetivo | Escritura permitida (exclusiva) |
|-----|--------|----------|---------------------------------|
| 1 | **A** | Auditoría visual (read-only) | `docs/audit-design-slop.md` (nuevo) |
| 1 | **B** | Gate visual en CI | `frontend/scripts/visual-qa.mjs`, `frontend/visual-qa.config.json`, `frontend/scripts/lib/**`, 1 línea en `frontend/package.json` |
| 1 | **C** | Checklist "Calidad de tu web" | `frontend/src/views/DashboardView.vue`, `frontend/src/components/design/WebQualityCard.vue`, `frontend/src/composables/useWebQuality.js`, `frontend/src/api/quality.api.js`, `StoreApp/domains/stores/**` (módulo nuevo + ruta), `StoreApp/domains/stores/tests_quality.py` |
| 1 | **D** | Fotos | `StoreApp/domains/stores/services/imaging.py`, `.../services/media_quality.py`, `.../tests_media_quality.py`, `frontend/src/components/design/DesignLookTab.vue`, `frontend/src/components/design/MediaQualityHint.vue` |
| 1 | **E** | Tipografía curada + tokens de pieles | `frontend/src/components/studio/panels/TypographyPanel.vue`, `.../panels/panelShared.js`, `frontend/src/assets/store-page.css`, `frontend/src/assets/store-*.css` |
| 2 | **F** | Integración y QA | cualquiera, con justificación por hunks |
| 3 | **G1-G4** | Fixes por grupo de patrones (opcional) | solo su grupo: `sources/<slug>.html`, `assets/store-<slug>.css`, `templates/.../views/store/<slug>/**` |
| 4 | **Z** | Limpieza final de basura | borrado de untracked listados + `.gitignore` |

Archivos **compartidos y bloqueados** en ola 1: `frontend/package.json` (solo B),
`frontend/src/assets/store-*.css` y `store-page.css` (solo E),
`frontend/src/views/DashboardView.vue` (solo C), `imaging.py` (solo D),
`StoreApp/domains/design/seed_data.json` (nadie en ola 1; lo aplica F),
`frontend/src/templates/index.js` (nadie; lo aplica F si hace falta).

---

## 2. Reglas globales (van en todos los prompts)

1. **Ningún agente hace `git`**: ni add, ni commit, ni push, ni checkout, ni stash.
   El orquestador commitea al volver cada track.
2. **No instalar dependencias** sin aprobación explícita. Preferir lo que ya está en el árbol.
3. **No tocar** `.env*`, `media/`, `db.sqlite3`, `venv/`, `node_modules/`, `.git/`.
4. **No `git clean`** de ningún tipo (borra `media/`, `.env`, node_modules).
5. Toda imagen que se suba pasa por `normalize_image` (WebP, EXIF corregido). Nunca PNG/JPG original.
6. Markup de diseño: jamás `allow-same-origin`, `unsafe-inline` en CSP, ni `fetch` nuevo
   dentro de un patrón (todo por el puente `davent:ds-api`).
7. Contrato de tema **retrocompatible**: un tema sin la clave nueva debe verse exactamente igual.
8. Economía de tokens: `grep`/`code_search` primero, `read` con `offset`/`limit`. No releer
   `AGENTS.md`, `ARCHITECTURE.md` ni volcar archivos enteros. Nada de subagentes.
9. El agente termina con: `git status --porcelain`, `git diff --stat`, comandos de
   verificación corridos y su salida real (truncada a lo relevante), y riesgos abiertos.

---

## 3. Prompt maestro (orquestador)

```
Sos el orquestador del plan "web profesional" de SaaS DAVENT (Django+DRF en la raíz,
Vue 3 en frontend/, 23 patrones × 63 estilos). El plan completo está en
PLAN_WEB_PROFESIONAL.md: leelo una vez y no lo releas.

Reglas de orquestación:
1. Lanzá los tracks A-E en paralelo con su prompt completo y su lista de archivos
   permitidos. Antes de lanzar, verificá que no haya solapamiento de escritura.
2. Ningún subagente hace git. Al volver cada track: git status --porcelain, comparar
   contra la lista permitida, correr su verificación mínima, y recién ahí commit
   conventional en inglés + push a main.
3. Cambios fuera de scope: se rechazan (revertir esos hunks) y se anotan como
   dependencia para el track F.
4. "Profesional" se mide con la tabla §0 del plan, no con opinión.
5. Invariantes que ningún track puede romper: contrato de tema retrocompatible,
   sin allow-same-origin, sin unsafe-inline, todo upload por normalize_image,
   patrones sin requests externos.
6. Al terminar A-E, lanzá F. Al terminar F, lanzá Z (limpieza) con dry-run y
   confirmación del usuario antes de borrar.
```

---

## 4. OLA 1 — cinco agentes en paralelo

### Prompt A — Auditoría visual (read-only)

```
Rol: auditor de diseño senior. NO escribís código. Único archivo que creás:
docs/audit-design-slop.md (creá la carpeta docs/ si no existe).

Objetivo: inventario priorizado de defectos visuales en los diseños que servimos a clientes.

Alcance de lectura: StoreApp/domains/design/sources/*.html (23 patrones),
frontend/src/assets/store-*.css, frontend/src/assets/store-page.css,
DESIGN_SYSTEM.md §1-§7 (ese es el criterio), frontend/src/templates/index.js.

Para cada patrón evaluá y anotá con archivo:línea:
- Hardcodes fuera de tokens: colores hex sueltos, paddings/gaps fijos, radios, sombras negras duras.
- Anti-patrones de DESIGN_SYSTEM.md §6 (grilla de 3 cards repetida, gradientes arcoíris, emojis-icono).
- Jerarquía: ¿eyebrow → titular clamp → lead → CTA? ¿más de 3 niveles compitiendo?
- Tipografía: ¿una display + una body? ¿tracking negativo en cuerpos? ¿line-height < 1.4 en párrafos?
- Contraste AA calculado (no estimado) en texto, muted y estados sobre bg y surface, claro y oscuro.
- Estados: focus-visible, hover en táctil (@media hover:none), vacíos (:has/:empty), loading.
- Responsive: qué se rompe o se ve pobre a 390 y a 768 (no solo si hay scroll horizontal).
- Movimiento: propiedades no compuestas animadas, loops sin pausa, reduced-motion.

Entregable en docs/audit-design-slop.md:
1. Tabla: patrón | severidad (alta/media/baja) | defecto | archivo:línea | fix propuesto (1 línea).
2. Top 10 fixes de mayor impacto y riesgo bajo, ordenados.
3. Lista de patrones que están bien (no tocar).
4. Anexo: ratio de contraste calculado por par texto/fondo problemático.

Sin prosa decorativa, sin cambios de código, sin git.
Verificación: cada hallazgo cita archivo:línea real y verificable.
```

### Prompt B — Gate visual en CI

```
Rol: ingeniero de QA frontend.

Objetivo: convertir "se ve profesional" en un test que falla el build.

Scope de escritura (exclusivo): frontend/scripts/visual-qa.mjs,
frontend/visual-qa.config.json, frontend/scripts/lib/** (nuevo) y UNA línea de script
en frontend/package.json. NO toques componentes, CSS, backend ni el contrato.
NO instales dependencias sin pedir aprobación (revisá primero si puppeteer/playwright
ya está en el árbol; si no está, pedila antes de instalar).

Qué hace el script, por cada patrón × estilo activo del catálogo
(GET /api/design/catalog/ + estilos de StoreApp/domains/design/seed_data.json):
1. Levanta la tienda de QA con patrón+estilo forzado (mirá cómo lo hacen /mi-qa y /moda-qa).
2. Renderiza a 390x844, 768x1024 y 1360x900.
3. Falla con exit 1 si: scrollWidth > clientWidth + 1; hay console.error o pageerror;
   algún texto desborda su contenedor (scrollWidth > clientWidth + 2 con overflow visible);
   el contraste de un nodo de texto contra su fondo efectivo da < 4.5 (o < 3.0 si >=24px
   o bold >=19px).
4. Screenshot por combinación en frontend/visual-qa/current/ y comparación contra
   baseline/ con tolerancia configurable. Si no hay baseline, lo crea y avisa (no falla).
5. Salida: tabla resumen + JSON de fallos. Flags: --only=<slug>, --update-baseline, --headed.
6. Timeout por página, cierre limpio del navegador, corre sin GPU en CI.
7. Agregá "visual:qa": "node scripts/visual-qa.mjs" a package.json.

Verificación: corré el script contra 3 patrones (uno claro, uno oscuro, uno advanced)
y mostrá la salida real. No commitees. Si detectás defectos de CSS, anotalos en el
reporte final: NO los arregles (store-*.css pertenece a otro track).
```

### Prompt C — Checklist "Calidad de tu web"

```
Rol: full-stack Django+DRF / Vue 3.

Objetivo: que el dueño de la tienda vea qué le falta para que su web se vea profesional,
con acción directa a la pestaña correspondiente.

Scope de escritura (exclusivo): frontend/src/views/DashboardView.vue,
frontend/src/components/design/WebQualityCard.vue (nuevo),
frontend/src/composables/useWebQuality.js (nuevo), frontend/src/api/quality.api.js (nuevo),
StoreApp/domains/stores/** (servicio nuevo + vista + ruta), StoreApp/domains/stores/tests_quality.py (nuevo).
NO toques store-*.css, store-page.css, package.json, imaging.py, TypographyPanel.vue
ni el contrato de tema.

Backend: GET /api/stores/<slug>/web-quality/ (IsAuthenticated; dueño o staff, con la misma
pauta de permisos que el resto del dominio). Respuesta: score 0-100 y checks
[{id, weight, ok, label, action, tab}]:
logo cargado, foto de portada, >=8 productos activos, >=80% de productos con foto,
>=80% con descripción >=120 caracteres, "sobre nosotros" >=200 caracteres, horarios,
dirección/mapa, teléfono o WhatsApp, al menos una red social, diseño elegido (no default),
tema publicado. Pesos explícitos que sumen 100; score = suma de los ok.
Sin N+1: select_related/prefetch + agregados.

Frontend: tarjeta compacta en el dashboard con score, barra, los 3 checks fallidos de mayor
peso y un botón por check que navegue a la pestaña correspondiente (reusá el mapa de tabs
que ya existe en DashboardView). Se oculta si score = 100. Usá los tokens del panel,
no inventes paleta.

Tests: sin productos; sin logo; todo completo (=100); tienda ajena (403).
Verificación: venv/Scripts/python.exe manage.py test StoreApp.domains.stores.tests_quality
y npm run lint (desde frontend/). No commitees.
```

### Prompt D — Fotos

```
Rol: ingeniero backend (Pillow) + Vue.

Objetivo: que ninguna web se vea amateur por culpa de la fotografía.

Scope de escritura (exclusivo): StoreApp/domains/stores/services/imaging.py,
StoreApp/domains/stores/services/media_quality.py (nuevo),
StoreApp/domains/stores/tests_media_quality.py (nuevo),
frontend/src/components/design/DesignLookTab.vue,
frontend/src/components/design/MediaQualityHint.vue (nuevo).
NO toques DashboardView.vue, package.json, store-*.css ni el contrato de tema.

1. Subí MAX_SIDE_PRODUCT de 1200 a 1600 (retina y ficha) manteniendo el target de bytes
   y el bucle de calidad. No toques los demás máximos. Verificá que el tiempo de encode
   siga razonable.
2. media_quality.py: inspect(upload) -> {width, height, soft, ratio}, donde soft = el lado
   útil para su slot queda por debajo de 1.5x el tamaño de render. Tabla de slots:
   portada 2200, producto 1200, logo 800, galería 1600. Devolvelo en la respuesta del upload
   como quality: {ok, soft, hint}. Nunca rechaces el archivo: solo avisá.
3. DesignLookTab: al elegir portada/logo, si soft mostrá MediaQualityHint ("esta foto se verá
   borrosa en pantalla grande, subí una de al menos N px"); si el ratio se aleja del slot,
   sugerí recorte. Nunca bloquees el guardado.
4. Toda imagen sigue pasando por normalize_image (WebP, EXIF corregido). No agregues rutas
   alternativas ni otros formatos.

Tests: imagen 400px -> soft=true; 3000px -> soft=false; PNG con EXIF rotado sale WebP derecho.
Verificación: manage.py test StoreApp.domains.stores.tests_media_quality y npm run lint.
No commitees.
```

### Prompt E — Tipografía curada + tokens de pieles

```
Rol: frontend / design-system.

Objetivo: que el cliente no pueda elegir combinaciones que arruinen el diseño, y que las
pieles dejen de hardcodear ritmo vertical.

Scope de escritura (exclusivo): frontend/src/components/studio/panels/TypographyPanel.vue,
frontend/src/components/studio/panels/panelShared.js,
frontend/src/assets/store-page.css, frontend/src/assets/store-*.css.
NO toques contract.js, DashboardView, imaging.py, package.json ni los patrones de
StoreApp/domains/design/sources/.

1. FONT_PAIRS ya existe en panelShared.js: marcá cada par como allowed por diseño/estilo y en
   TypographyPanel deshabilitá (con motivo visible) los pares y pesos que la piel no soporta
   (ej.: display script como cuerpo, peso 100-200 en títulos de pieles de bloque). No elimines
   opciones del catálogo global: solo bloqueá donde rompen. Retrocompatible: un tema ya
   guardado se sigue viendo exactamente igual.
2. Auditá paddings/gaps/anchos de contenedor hardcodeados en store-*.css y store-page.css y
   pasalos a variables --st-* con fallback al valor actual (cero cambio visual para temas
   existentes). Priorizá padding-block de secciones y gap de grillas; no reescribas el archivo
   entero.
3. Nada de cambios visuales por defecto: el diff debe ser equivalente a ojo. Si un valor cambia,
   justificalo y anotalo.

Verificación: npm run verify:studio, npm run lint, npm run build (desde frontend/). Compará 2
diseños antes/después (screenshots si el gate de B ya existe). No commitees.
```

---

## 5. OLA 2 — Integración

### Prompt F — Integración y QA

```
Rol: integrador. Recibís los reportes de los tracks A-E.

1. git status --porcelain y git diff --stat global. Detectá solapamientos o cambios fuera de
   scope y revertí esos hunks (git checkout -- <archivo> solo si el archivo entero es ajeno;
   si es parcial, editá a mano).
2. Corré y pegá la salida real:
   - cd frontend && npm run lint
   - cd frontend && npm run build
   - cd frontend && npm run verify:studio
   - cd frontend && npm run visual:qa
   - venv/Scripts/python.exe manage.py check
   - venv/Scripts/python.exe manage.py test StoreApp.domains.design StoreApp.domains.stores
3. Arreglá regresiones respetando los invariantes: contrato retrocompatible, sin
   allow-same-origin, sin unsafe-inline, todo upload por normalize_image, patrones sin
   requests externos.
4. Aplicá de docs/audit-design-slop.md solo los fixes de severidad alta y riesgo bajo,
   en commits separados por área. Los que toquen seed_data.json o templates/index.js se
   aplican acá y se recargan con:
   manage.py seed_design_catalog --patterns-only  (o sync_design_neon --slug <x> si aplica).
5. Actualizá AGENTS.md (script visual:qa, endpoint web-quality, media_quality, FONT_PAIRS
   bloqueados) y DESIGN_SYSTEM.md con las reglas nuevas. Sin duplicar lo que ya está.
6. Commits conventional por área + push a main.

Entregable final: tabla de gates (comando | resultado) + lista de pendientes con dueño.
```

---

## 6. OLA 3 — Fixes por grupo de patrones (opcional, 4 en paralelo)

Solo si `docs/audit-design-slop.md` deja pendientes de severidad media. Grupos disjuntos:

| Agente | Patrones |
|--------|----------|
| G1 | portico, esencial, mercado, gimnasio, moderntec, ruta |
| G2 | aurum, brigada, indumentaria, impacto, calzado, moda |
| G3 | modista, topmodern, viajero, olivium, atelier-noir, guardia |
| G4 | expediente, silicio, neon, showroom, sastreria |

```
Rol: frontend/design.

Objetivo: cerrar los pendientes de docs/audit-design-slop.md para TU grupo de patrones:
<LISTA>.

Scope de escritura (exclusivo): StoreApp/domains/design/sources/<slug>.html,
frontend/src/assets/store-<slug>.css, frontend/src/templates/**/views/store/<slug>/**.
PROHIBIDO: store-page.css, seed_data.json, templates/index.js, package.json, cualquier
archivo de otro grupo, backend, git.

Reglas:
- Arreglá solo lo listado en la auditoría para tus patrones. No rediseñes.
- Sin cambios de markup estructural salvo que el fix lo exija; si lo exige, mantené las
  clases y el puente davent:ds-api intactos.
- Tokens antes que valores: si falta un token, usá --ds-* / --st-* con fallback.
- Cada fix debe quedar verificado a 390 y 1360 (sin scroll horizontal, sin consola).
- Si un fix necesita un cambio global (store-page.css o seed_data.json), NO lo hagas:
  anotalo en el reporte con el snippet exacto.

Entregable: por patrón, tabla fix | archivo:línea | antes/después en una línea.
Verificación: npm run lint + npm run build + npm run visual:qa -- --only=<slug> por cada
patrón del grupo. No commitees.
```

---

## 7. OLA 4 — Limpieza final (último agente)

> **Este agente borra archivos. Protocolo obligatorio: dry-run primero, confirmación
> del usuario, después borrado. Nunca `git clean`.**

### Prompt Z — Limpieza

```
Rol: housekeeping del repo. Sos el último agente del plan: todo lo demás ya está commiteado
y los gates pasan.

Objetivo: eliminar basura que ya no sirve, sin tocar nada que el proyecto necesite.

FASE 1 — DIAGNÓSTICO (no borres nada todavía)
1. git status --porcelain --untracked-files=all (truncado) y git check-ignore -v <ruta>
   para separar: tracked / untracked / ignorado.
2. Clasificá cada candidato y mostrá una tabla: ruta | tamaño (du -sh) | tracked? |
   qué es | veredicto (borrar / conservar / preguntar).

Candidatos ya detectados en la raíz (verificá antes de proponer):
- Borrar: pip-unpack-*/, pip-install-*/, pip-metadata-*/, pip-ephem-wheel-cache-*/,
  pip-build-tracker-*/, .tmp_build/, .tmp_preview/, _tmp_pw/, nul (artefacto de Windows).
- Borrar solo si el usuario confirma: _tmp_gif/ (está TRACKED en git, 16K),
  bocetos/ (untracked, 56K, pueden ser bocetos válidos), .pnpm-store/ (22M, se regenera).
- NUNCA borrar: media/ (uploads reales), .env*, db.sqlite3, venv/, node_modules/,
  awesome-design-skills/ (22M, es la fuente de DESIGN_SYSTEM.md), .git/, frontend/dist/
  salvo pedido explícito, y cualquier archivo TRACKED sin confirmación explícita.
- __pycache__/ y *.pyc: solo dentro del repo y con el usuario avisado.

FASE 2 — CONFIRMACIÓN
Mostrá la lista final de borrado y esperá un "sí" explícito. No interpretes silencio
como aprobación. Si el usuario no responde, no borres.

FASE 3 — EJECUCIÓN (solo lo confirmado)
1. Untracked/ignorado: rm -rf de cada ruta confirmada, una por una (nunca comodines
   amplios, nunca git clean).
2. Tracked: git rm -r <ruta> y commit "chore: remove <qué>".
3. Actualizá .gitignore con los patrones que falten (pip-*/, .tmp_*/, _tmp_*/) para que
   no vuelvan a aparecer.
4. Verificá que el repo sigue sano: git status --porcelain, npm run build (frontend/),
   venv/Scripts/python.exe manage.py check.
5. Commit + push de .gitignore y de los git rm, con mensaje conventional.

Entregable: tabla borrado | tamaño liberado | motivo, + total liberado, + salida de las
3 verificaciones. Si algo dudoso quedó, listalo como "pendiente de decisión del usuario".
```

---

## 8. Runbook — cómo darle las tareas a los agentes

### Modo fácil (sin copiar y pegar)

Los roles están versionados en `.devin/agents/track-*.md` (uno por track, con su
`allowed-tools` restringido). Hay tres formas de usarlos, de menos fricción a más:

**1. Un comando, cinco pestañas** — recomendado:

```powershell
.\tools\ola.ps1 -Wave 1          # abre 5 pestañas de Windows Terminal, cada una ya con su rol
.\tools\ola.ps1 -Wave 2          # track F (integración)
.\tools\ola.ps1 -Wave 3          # G1-G4 (fixes por patrón)
.\tools\ola.ps1 -Wave 4          # track Z (limpieza)
.\tools\ola.ps1 -Wave 1 -Only a,b        # solo algunos tracks
.\tools\ola.ps1 -Wave 1 -Mode batch      # sin ventanas, logs en .devin/logs/
.\tools\ola.ps1 -Wave 1 -DryRun          # muestra qué haría, no lanza nada
```

El script lee el rol, le quita el frontmatter y arranca `devin --prompt-file`. No hay
nada que pegar: la tarea ya viaja en el archivo.

**2. Skills desde una sesión** — `/ola1`, `/ola2`, `/ola3`, `/limpieza`.
`/ola1` lanza los 5 tracks como subagentes en paralelo desde un solo chat.
`/limpieza` corre inline porque necesita `ask_user_question` para aprobar borrados.
Ojo: los subagentes en background heredan solo los permisos ya aprobados en la sesión;
si uno falla por permiso denegado, relanzalo en foreground.

**3. Rol por nombre en cualquier sesión** — "usá el subagente `track-d` para las fotos".
Editar `.devin/agents/track-d.md` cambia todos los lanzamientos futuros de ese rol.

| Rol | Track | Scope de escritura |
|-----|-------|--------------------|
| `track-a` | Auditoría visual (read-only) | `docs/audit-design-slop.md` |
| `track-b` | Gate visual CI | `frontend/scripts/visual-qa.*`, `frontend/package.json` (1 línea) |
| `track-c` | Calidad de contenido | `DashboardView.vue`, `WebQualityCard.vue`, endpoint `web-quality` |
| `track-d` | Fotos | `imaging.py`, `media_quality.py`, `DesignLookTab.vue` |
| `track-e` | Tipografía + tokens | `TypographyPanel.vue`, `panelShared.js`, `store-*.css` |
| `track-f` | Integración | cualquiera, con justificación |
| `track-g1..g4` | Fixes por patrón | solo su grupo de slugs |
| `track-z` | Limpieza | borrado confirmado + `.gitignore` |

### Paso 0 — Preparación (una vez)

```bash
cd "C:\Users\David\OneDrive\Escritorio\SaaS DAVENT"
git status --porcelain          # debe estar limpio o solo con cambios tuyos conocidos
git log --oneline -3            # anotá el HEAD de partida
```

Si hay cambios sin commitear que no son tuyos (por ejemplo `M StoreApp/domains/design/sources/portico.html`),
decidí antes de arrancar: commitear o descartar. Si no, contamina los diffs de los agentes.

### Paso 1 — Ola 1: cinco sesiones en paralelo

Para cada track (A, B, C, D, E):

1. Abrí una sesión de agente **nueva y vacía** (contexto limpio = menos tokens y menos contaminación).
2. Pegá **el bloque de prompt completo** de la sección correspondiente, sin editarlo.
   Si querés, agregá una línea al final con el alcance extra que decidas.
3. Dejalo trabajar. No interrumpas con preguntas: los prompts ya traen las decisiones.
4. Al terminar, en **tu** terminal:

```bash
git status --porcelain          # ¿tocó solo lo permitido?
git diff --stat                 # magnitud del cambio
```

5. Si respetó el scope y la verificación pasó:

```bash
git add -A -- <rutas permitidas del track>
git commit -m "feat: <resumen del track>"    # conventional, inglés
git push origin main
```

6. Si se salió del scope: `git checkout -- <archivo ajeno>` (o editá a mano si el cambio es
   parcial) y volvé a pedirle al agente que entregue solo lo suyo.

**Orden de lanzamiento:** los cinco a la vez. A no escribe código, así que puede ir con
cualquiera. Si tu máquina sufre con cinco agentes simultáneos, corré A+B y después C+D+E.

### Paso 1-bis — Si usaste `tools/ola.ps1` (o `/ola1`)

Ya no hay que pegar nada, pero **sí hay que revisar y commitear**:

```powershell
git status --porcelain                 # ¿cada track tocó solo lo suyo?
git diff --stat
```

Por cada track, verificá contra la tabla de scopes de §1:

```powershell
git add -A -- <rutas permitidas del track>
git commit -m "feat: <resumen del track>"    # conventional, inglés
git push origin main
```

Si un track se salió del scope: `git checkout -- <archivo ajeno>` (o editá a mano si el cambio
es parcial) y volvé a pedirle solo lo suyo. Si dos tracks tocaron el mismo archivo, el
conflicto se resuelve en la ola 2 (track F), no acá.

### Paso 2 — Ola 2: integración

Sesión nueva, pegá el prompt **F**. Le pasás como contexto los 5 reportes finales (pegalos
al principio del mensaje, sin archivos enteros). F puede tardar: corre todos los gates.
Al volver, revisá su tabla de gates y commiteá lo que haya quedado sin commit.

### Paso 3 — Ola 3 (opcional): fixes por grupo

Solo si la auditoría dejó pendientes medios. Cuatro sesiones en paralelo, una por grupo,
con el prompt de §6 y la lista de patrones del grupo sustituida. Scopes disjuntos por
construcción (un archivo por slug), así que no hay conflictos.

### Paso 4 — Ola 4: limpieza

Sesión nueva con el prompt **Z**. **No le des vía libre:** exigí la Fase 1 (tabla de
diagnóstico) y aprobá vos la lista antes de la Fase 3. Es el único agente que borra.

### Paso 5 — Cierre

```bash
git status --porcelain          # limpio
git log --oneline -10           # un commit por track
```

Marcá el progreso en §10 y actualizá `AGENTS.md` si algún comando nuevo quedó estable.

### Reglas de convivencia (para no romper nada)

- Un agente por archivo. Si dos tracks necesitan el mismo archivo, ese cambio va a F.
- Nada de dos agentes con `git` a la vez.
- Si un agente falla dos veces en el mismo punto, cortalo: lo resuelve F con el contexto completo.
- Si un track tarda demasiado, no lo dupliques: esperá o cancelalo y reencolá en la ola 2.

---

## 9. Criterios de aceptación final

- [ ] `npm run visual:qa` pasa en los 23 patrones × estilos activos (o baseline aceptado).
- [ ] `manage.py test StoreApp.domains.design StoreApp.domains.stores` verde.
- [ ] `npm run lint`, `npm run build`, `npm run verify:studio` verdes.
- [ ] `manage.py check` sin warnings nuevos.
- [ ] `docs/audit-design-slop.md` sin pendientes de severidad alta.
- [ ] Checklist de calidad visible en el dashboard y navegando a la pestaña correcta.
- [ ] Ninguna imagen servida fuera de WebP y ningún upload sin `normalize_image`.
- [ ] `git status` limpio, un commit por track, `main` pusheado.
- [ ] Basura borrada y `.gitignore` actualizado.

---

## 10. Registro de ejecución

| Track | Agente | Estado | Commit | Notas |
|-------|--------|--------|--------|-------|
| A | Auditoría visual | pendiente | — | |
| B | Gate visual CI | pendiente | — | |
| C | Calidad de contenido | pendiente | — | |
| D | Fotos | pendiente | — | |
| E | Tipografía + tokens | pendiente | — | |
| F | Integración | pendiente | — | depende de A-E |
| G1-G4 | Fixes por patrón | opcional | — | depende de A y F |
| Z | Limpieza | pendiente | — | último, requiere confirmación |
