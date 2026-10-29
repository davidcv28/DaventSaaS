# Prompts de delegación — Rediseño de plantillas

**Orden obligatorio:** A solo → (B1 ∥ B2) → C. B no arranca hasta que A commiteó. Cada bloque es autocontenido: se pega tal cual en un agente nuevo.

**Material de referencia ya preparado** (recortes legibles, 1200 px de ancho):
`.qa-tmp/design-refs/` → `inicio-raiz-1..4.jpg`, `movil-raiz-1..2.jpg`, `catalogo-raiz-1..2.jpg`, `servicios-raiz-1..2.jpg`, `trama-1..3.jpg`, `circuito-1..3.jpg` (más los PNG originales). El bundle completo: `C:\Users\David\OneDrive\Escritorio\Landing de tienda DAVENT.html`.

---

## AGENTE A — Fundación + diseño Raíz

```
Sos el agente A de un rediseño de plantillas en el repo SaaS DAVENT.
Workspace: C:\Users\David\OneDrive\Escritorio\SaaS DAVENT
Stack: Django + DRF (raíz) y Vue 3 + Vite (frontend/).

ANTES DE TOCAR NADA, leé completo y obedecé:
1) docs/PROMPT_REDISENO_PLANTILLAS.md  (spec maestra: tokens, secciones, alcance, anti-objetivos)
2) AGENTS.md, sólo las secciones de plantillas, gating y reglas de commits.
3) Mirá las referencias visuales en .qa-tmp/design-refs/: inicio-raiz-1..4.jpg,
   movil-raiz-1..2.jpg, catalogo-raiz-1..2.jpg, servicios-raiz-1..2.jpg.
   (Son recortes del bundle; el HTML completo, si lo necesitás, está en
   C:\Users\David\OneDrive\Escritorio\Landing de tienda DAVENT.html)

TU MISIÓN (fase fundacional, secuencial, sin paralelizar):
A.1 Backend (spec §9.1): TEMPLATE_CHOICES = raiz/trama/circuito; TEMPLATE_BASE/PLUS/ADVANCED
    de a uno; TEMPLATE_RETIRED_MAP con TODOS los ids viejos mapeados por afinidad;
    default y template_draft = 'raiz'; migración 0053 (siguiente a 0052) con RunPython
    de remapeo idempotente + AlterField; allowed_templates_of con fallback ('raiz',);
    serializers/validators; tests actualizados + los 3 tests nuevos de la spec.
A.2 Frontend base: registro en src/templates/index.js con los 3 ids y stubs mínimos que
    compilen (cada uno con su carpeta src/views/store/<id>/ y su CSS vacío);
    stores.api.js (STORE_TEMPLATES con rubro/tier/defaultAccent, familias por rubro,
    fallback raiz, borrar AI_LEGACY/AI_EXTRA); StorePublicLayout resolviendo el chrome
    por diseño; chrome/ + primitivas compartidas (botones, cards, badges, inputs, focus).
A.3 Diseño Raíz COMPLETO: Inicio (14 secciones), Catálogo, Ficha de producto, Servicios,
    header/footer/barra móvil, estados vacío/carga/error, responsive 360/768/1024/1360.
    Fidelidad contra los recortes: medidas, tipografía, color y densidad.
A.4 Limpieza de la spec §9.3: borrar carpetas de templates viejos, StorePublicAltView,
    la ruta /v2, CSS de pieles listado y clases .sp-cb/.sp-cm/.sp-vt/.sp-mn/.sp-du.
    grep de 'classic', 'ai_lumen', 'cobre', 'caliber' debe quedar vacío salvo
    RETIRED_MAP y la migración.
A.5 Publicá el contrato para los agentes B en docs/PLANTILLAS_INTERFAZ.md:
    mapa de archivos, props/slots del chrome y las primitivas, variables CSS por diseño,
    cómo se registra un template, nombres de rutas y selector de datos, y qué NO puede
    tocar un agente de diseño. Este archivo es un entregable, no un extra.

REGLAS:
- No agregues dependencias. No toques panel admin, checkout, emails, chat, folletos.
- No implementes Trama ni Circuito: sólo stubs que compilen.
- Commits conventional en inglés, con `git add` acotado a tus rutas, y push a main.
  Sugeridos: (1) feat(store): replace template catalog with raiz/trama/circuito,
  (2) feat(store): raiz public design, (3) chore(store): drop legacy template skins.
- Verificación mínima antes de cerrar: `venv/Scripts/python.exe manage.py test`
  (truncá salida), `cd frontend; pnpm build`, y capturas 1360/390 de las 4 superficies
  de Raíz comparadas con la referencia.

REPORTE FINAL (máx. 15 líneas): commits + hashes, archivos clave, tests/build OK,
desvíos respecto de la spec y cualquier decisión que los agentes B deban respetar.
```

---

## AGENTE B1 — Diseño Trama (indumentaria)

```
Sos el agente B1 de un rediseño de plantillas en el repo SaaS DAVENT.
Workspace: C:\Users\David\OneDrive\Escritorio\SaaS DAVENT
Stack: Vue 3 + Vite.

PRERREQUISITO: el agente A ya commiteó la fundación. Verificá con `git log --oneline -5`
que existe el commit del catálogo raiz/trama/circuito y que existe
docs/PLANTILLAS_INTERFAZ.md. Si no existe, DETENETE y reportalo; no improvises la base.

LEÉ PRIMERO:
1) docs/PROMPT_REDISENO_PLANTILLAS.md (completo)
2) docs/PLANTILLAS_INTERFAZ.md (contrato de A: primitivas, chrome, CSS vars)
3) Referencias: .qa-tmp/design-refs/trama-1.jpg, trama-2.jpg, trama-3.jpg
   (y el PNG original trama.png si necesitás zoom).

TU MISIÓN: implementar el diseño TRAMA (indumentaria) en las 4 superficies:
Inicio (12 secciones de la spec §7.1), Catálogo, Ficha de producto y Servicios,
más su header/footer/barra móvil.

Spec visual (resumen; el detalle manda por la referencia):
- Paleta: bg #FFFFFF, ink #0B0B0B, muted #5C5C5C, line #D8D8D5, surface-2 #D9D7D2,
  accent #E4472B, on-accent #FFFFFF. Radio 0 en todo (excepto círculos/puntos).
  Sin sombras; bordes de 1 px negro.
- Tipografía: Archivo (cuerpo) + Anton (display, mayúsculas). h1 clamp(56px,11vw,132px)/.86,
  h2 52/.92, títulos 34, eyebrow 12/700 +.14em, cuerpo 15/1.55, producto 13 mayúsculas.
- Composición: header con logo centrado y líneas; hero partido 55/45 con borde vertical;
  palabra acentuada en accent; cinta marquee de accent con separador ·; categorías 4;
  nueva temporada 4; banda lookbook oscura; beneficios 4; looks del mes; FAQ con líneas;
  banda CTA accent; contacto + footer.
- Mobile: barra inferior de 5 ítems, hero apilado, grillas a 1–2 columnas.

ARCHIVOS QUE PODÉS TOCAR (exclusivamente):
- frontend/src/views/store/trama/** (todo el diseño)
- frontend/src/assets/store-trama.css
- frontend/src/templates/trama/index.js (def del template: fuentes/superficies/bloques)
PROHIBIDO tocar: backend, stores.api.js, templates/index.js (salvo que el contrato lo pida),
primitivas compartidas, chrome/ compartido, carpetas de raiz o circuito, package.json.

REGLAS:
- Reutilizá las primitivas y el contrato de A; no dupliques botones/cards.
- Datos reales siempre; respetá los show_* y el gating; sin contenido la sección se oculta.
- Accesibilidad: foco visible, AA 4.5, keyboard, prefers-reduced-motion (sin marquee).
- Sin dependencias nuevas ni estilos inline.
- Verificación: `pnpm build`; si podés levantar `pnpm dev --port 5175` y sacar capturas
  con Edge/Chrome headless (`msedge --headless --screenshot=... --window-size=1360,4000 URL`)
  contra la referencia. Si no hay backend/datos, dejá constancia y checklist manual.
- Commit conventional en inglés con `git add` sólo de tus rutas + push a main.
  Si el index está lockeado por el otro agente B, esperá y reintentá; no hagas reset.

REPORTE FINAL (máx. 12 líneas): commit/hash, archivos, capturas o checklist, desvíos
de la referencia, y cualquier cambio que el agente C deba conocer.
```

---

## AGENTE B2 — Diseño Circuito (tecnología)

```
Sos el agente B2 de un rediseño de plantillas en el repo SaaS DAVENT.
Workspace: C:\Users\David\OneDrive\Escritorio\SaaS DAVENT

PRERREQUISITO: A ya commiteó la fundación. Verificá `git log` y docs/PLANTILLAS_INTERFAZ.md.
Si falta, DETENETE y reportalo.

LEÉ PRIMERO:
1) docs/PROMPT_REDISENO_PLANTILLAS.md (completo)
2) docs/PLANTILLAS_INTERFAZ.md
3) Referencias: .qa-tmp/design-refs/circuito-1.jpg, circuito-2.jpg, circuito-3.jpg
   (y circuito.png para zoom).

TU MISIÓN: implementar el diseño CIRCUITO (tecnología) en Inicio (12 secciones §7.1),
Catálogo, Ficha de producto y Servicios, más su header/footer/barra móvil.

Spec visual (resumen; manda la referencia):
- Paleta oscura: bg #0A0E14, surface #111823, surface-2 #0E141D, line #1F2933,
  ink #E6EDF3, ink-2 #B6C2CF, muted #8FA1B3, accent #22D3EE, on-accent #04141A,
  footer #070A0F. Radios 10 (chips 6, media 14). Bordes 1 px; retícula/glow muy sutil.
- Tipografía: Space Grotesk + JetBrains Mono para etiquetas (12 mayúsculas +.08em).
  h1 clamp(44px,6.4vw,72px)/1.02, h2 40/1.1, cuerpo 16/1.55.
- Composición: barra superior accent; header oscuro con buscador; hero partido con tarjeta
  de producto, chips de specs y badge -N%; franja de 4 garantías con íconos; categorías 6
  en 3×2; destacados 4; banda de servicios; oferta+countdown; testimonios; FAQ; contacto;
  footer minimal. Etiquetas tipo "// categorías".
- Mobile: tab bar inferior, hero apilado, grillas 1–2 columnas.

ARCHIVOS QUE PODÉS TOCAR (exclusivamente):
- frontend/src/views/store/circuito/**
- frontend/src/assets/store-circuito.css
- frontend/src/templates/circuito/index.js
PROHIBIDO: backend, stores.api.js, primitivas/chrome compartido, otras carpetas de diseño,
package.json.

REGLAS: (idénticas a B1) datos reales, show_*, gating, a11y AA, foco, reduced-motion,
sin dependencias ni inline styles, build verde, commit acotado + push, reintento ante
index.lock.

REPORTE FINAL (máx. 12 líneas): commit/hash, archivos, capturas o checklist, desvíos,
notas para C.
```

---

## AGENTE C — Integración y QA final

```
Sos el agente C de un rediseño de plantillas en el repo SaaS DAVENT.
Workspace: C:\Users\David\OneDrive\Escritorio\SaaS DAVENT

PRERREQUISITO: A, B1 y B2 commiteados. Revisá `git log --oneline -10`.

LEÉ: docs/PROMPT_REDISENO_PLANTILLAS.md (sobre todo §10), docs/PLANTILLAS_INTERFAZ.md,
y las referencias .qa-tmp/design-refs/*.jpg.

TU MISIÓN: cerrar el proyecto.
C.1 Correr la matriz de QA de §10 completa: tests Django, build, bundle por diseño,
    grep de ids/clases retiradas ('classic', 'ai_lumen', 'cobre', '.sp-cb-', etc.),
    contraste AA de las 3 paletas, responsive 360/390/768/1024/1360/1920, estados vacíos
    y gating (base sólo raiz; trama/circuito con flag; tienda vieja remapeada).
C.2 Revisar fidelidad visual de los 3 diseños contra la referencia y corregir SOLO
    desviaciones concretas (no rediseñar por gusto). Si algo requiere rehacer una
    superficie entera, reportalo en vez de reescribirlo.
C.3 Limpieza final: archivos huérfanos, CSS muerto, imports sin uso, textos viejos en el
    panel ("Clásico", "Dúo"…), previews y selector agrupados por rubro con candado.
C.4 Actualizar AGENTS.md (sección de plantillas: ids, tiers, rubros, fallback raiz) y
    docs/AI_DESIGN_STYLES_PROMPT.md si cambió el contrato del motor. Dejar el registro
    preparado para sumar rubros futuros (comida, bebida, etc.).
C.5 Capturas finales 1360/390 de Inicio, Catálogo, Producto y Servicios × 3 diseños,
    y checklist de §10 tildado en el reporte.

REGLAS:
- Sos el único que corre build/tests completos y el que hace el commit final de limpieza.
- No cambies decisiones de producto (tiers, nombres, fallback) sin reportarlo.
- Commit conventional en inglés + push. Si tocás docs y código, separá en dos commits.

REPORTE FINAL (máx. 20 líneas): estado de la matriz, hallazgos y fixes, deuda que queda
(fase 2: pieles/IA, rubros nuevos), commits con hash, y link a las capturas.
```

---

### Notas de coordinación

- **A** numera el commit y deja `docs/PLANTILLAS_INTERFAZ.md`; sin eso B no arranca.
- **B1 y B2** corren en paralelo: carpetas disjuntas, `git add` acotado, sin `reset`/`checkout` global.
- El backend compartido se levanta una vez (A); los B usan su propio puerto Vite (5175/5176).
- **C** es el único que ejecuta la suite completa, el build final y las capturas definitivas.
- Si un agente se desvía de la spec, C lo corrige o lo reporta; no se re-delega.
