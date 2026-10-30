# Ideas para mejorar "Diseñar con IA"

> Estado actual: motor v8 (`ai-design/8`), determinista y offline (`StoreApp/domains/stores/services/ai_design.py`),
> entrevista de 6 pasos + 2-4 propuestas → aplicar publica. No hay LLM ni llamadas de red.
> Las ideas están ordenadas por relación impacto/esfuerzo y ancladas a lo que hoy existe.

## 0. Antes de sumar features: arreglar la promesa

La sección funciona, pero hay tres cosas que le mienten al dueño. Cada una es un quick win de 1-2 días.

| # | Problema | Dónde | Arreglo |
|---|----------|-------|---------|
| 0.1 | **"¿Qué no puede faltar?" no hace nada.** La UI manda `whatsapp`, `hours`, `map`, `prices`, `testimonials`, `faqs`; el motor filtra contra ids de bloque (`hero`, `offers`, `faq`…) y descarta 5 de 6. Solo `testimonials` pasa, y no se consulta en ningún lado. | `AiDesignView.vue:73` → `ai_design.py:400`, `_element_candidates` 1569 | Traducir opción de UI → bloque/ajuste real (`whatsapp`→`contact`+`cta`, `hours`→`contact` con horarios, `map`→`contact` variante `map` + `show_location`, `prices`→`offers`, `faqs`→`faq`) y que `notes` solo afirme lo que el motor aplicó. |
| 0.2 | **`audience` y `content_hint` son entradas muertas.** Se normalizan y viajan, pero no las usa ni el layout ni el copy. | `ai_design.py:444,455` | O se consumen (copy por audiencia, parser de brief) o se sacan del contrato. `audience` lo manda la UI en el paso 3; `content_hint` hoy no lo manda nadie. |
| 0.3 | **El score es cosmético.** `contrast` sale 100 (las propuestas ya vienen corregidas), `hierarchy`/`harmony` derivan de eso y `fit` es fijo 95/88 → todas dan 95-97 y la etiqueta siempre es "Excelente". | `ai_design.py:2100` | Reemplazarlo por un score con información: completitud de datos, densidad real, calidad de copy, assets faltantes y "qué falta para subir". Si no hay señal nueva, es mejor no mostrar número. |

## 1. Brief: menos preguntas, más contexto

**1.1 · Brief precargado (impacto alto, esfuerzo M).**
`_guess_rubro`/`_guess_goals` ya deducen rubro y objetivo del perfil, catálogo y textos. Exponerlos en un endpoint de `prefill` y abrir la sección con "Ya sabemos: gastronomía, 34 productos, 6 fotos, 2 categorías" — preguntar solo lo que falta (tono, color, portada). Objetivo: de 6 pasos a 2 y media.
Éxito: % de sesiones que llegan a propuestas sin tocar "Prefiero que decidas vos".

**1.2 · Un campo de texto libre, con parser offline (alto, M).**
"Contame tu negocio en dos líneas". Parser por diccionario de sinónimos (ya existen `_fold` y las tablas de rubro): detecta rubro, tono, objetivos, colores por nombre ("bordó", "verde"), y palabras que piden bloques ("precios", "turnos", "catálogo"). Sin inventar datos y sin LLM. `content_hint` ya está reservado para esto.

**1.3 · Fotos en el paso 4, no después (alto, M).**
Hoy el pedido de fotos aparece en la tarjeta, cuando ya decidió. Sumar un upload en la entrevista y analizar con Pillow (ya es dependencia): ratio, luminancia, nitidez, orientación. Con eso la IA elige variante de hero (cinema vs split), avisa "esta foto es vertical, la recorto" y desbloquea `gallery`/`aimosaic`/`featured` desde la primera propuesta.

**1.4 · Paleta desde el logo (medio, S).**
Color dominante del logo (Pillow + clustering simple) como opción "usar los colores de mi logo", corregido con `_ensure_contrast` y dentro del catálogo cerrado de acento. Nunca color libre.

**1.5 · Nada de fotos, pero que no se vea vacío (medio, S).**
Portada sin foto hoy depende del theme. Generar arte determinista por rubro/piel (SVG/CSS: tramas, degradados, patrones de seguridad, papel de alimentos) elegido por semilla, para que la web sin fotos se vea intencional en vez de incompleta.

## 2. Motor: propuestas con tesis, no solo estética

**2.1 · Cada propuesta defiende un objetivo (alto, M).**
Hoy la diversidad es plantilla + piel + par; los objetivos cambian el orden de bloques, pero dos propuestas pueden ser la misma tesis con otro color. Definir 3 playbooks de conversión (catálogo/venta, servicios/presupuesto, confianza/local) y atar cada propuesta a uno, con su CTA y su prueba social. La tarjeta ya tiene `why`; pasaría a decir "esta está armada para que te escriban" y no una frase de rubro.
Éxito: aumento de "aplicar tras ver las propuestas" y de clics a WhatsApp en la web publicada.

**2.2 · Diversidad entre tandas, no solo dentro (medio, S).**
"Ver otro estilo" cambia la semilla, pero puede volver a la misma familia. Guardar las últimas N ternas vistas por tienda (DB o cache) y excluirlas al explorar. `_explore_styles` ya recibe `signature`; solo hay que pasarle el historial.

**2.3 · Reproducible y compartible (alto, S).**
La semilla + respuestas determinan la tanda, pero hoy muere al recargar (localStorage guarda respuestas, no propuestas). Persistir la última tanda en el backend y aceptar `?seed=&proposal=` para retomar, mandarle el link al socio o que el staff la vea. Es la base de 3.3 y 3.4.

**2.4 · Plan-aware honesto (medio, M).**
El motor solo propone dentro del plan (correcto), pero el dueño Básico ve 2 propuestas parecidas y no sabe qué se está perdiendo. Propuesta opt-in "cómo se vería con Premium" con las secciones bloqueadas marcadas y un botón de upgrade. Transparencia, no bloqueo: el motor actual nunca genera una web que no pueda publicar.

**2.5 · Nunca una sección que mienta (alto, S).**
Ya se apagan bloques sin datos (`facts`). Extender la regla a contenido derivado: `aipricing` con 1 producto, `stats` sin cifras, `about` sin texto, `hours` sin horarios del perfil. Y longitudes: nombre de 40 caracteres rompe el hero `centered`; el motor debería cambiar de variante, no recortar el nombre.

## 3. Decidir y refinar: de "elegir una tarjeta" a "llegar a mi web"

**3.1 · Comparador lado a lado (alto, M).**
Hoy son tarjetas independientes con preview por dispositivo. Un modo comparar (2 o 3 columnas, misma sección sincronizada) + tabla de diferencias: portada, tipografía, orden, qué datos usa cada una. Convierte la decisión estética en una decisión informada.

**3.2 · Refinar una propuesta (alto, L).**
`POST /ai-design/refine/` con constraints parciales sobre la terna elegida: "solo cambiá la tipografía", "portada más limpia", "menos secciones", "más cálido". Reusa seed + overrides (`styles`, `selection`, `must_have`, `tone`) y devuelve el delta, no una tanda nueva. Hoy la única salida es "Ver otro estilo", que tira todo.

**3.3 · Historial y diff contra lo publicado (medio, M).**
`StudioVersion` ya existe; el flujo IA no lo usa. "Volver a lo que tenía antes de la IA" y ver qué cambió (secciones, colores, copy) con un diff legible. Reduce el miedo a aplicar.

**3.4 · Preview privada para decidir con otro (medio, M).**
Link temporal con token, `noindex`, que muestra la propuesta renderizada sin publicar. Hoy el dueño decide solo; en comercios chicos decide con el socio o el diseñador.

**3.5 · Publicar guiado, con progreso (medio, S).**
`missing` ya viaja y abre la sección que falta, pero es un aviso. Volverlo checklist persistente (0-100 %) en Resumen, con "faltan 3 cosas para que tu web venda mejor" y auto-fix del motor donde se pueda.

## 4. La web que arma la IA tiene que nacer bien

**4.1 · Preview al compartir por WhatsApp (alto, S).**
Hoy `seo.js` setea metas en el cliente; WhatsApp/Facebook no ejecutan JS, así que el link de la tienda se comparte con el `og:title` de DAVENT. Detectar bots de preview en nginx (`$http_user_agent`) y responder un HTML mínimo con las metas + JSON-LD de la tienda (o prerender por host). Es el canal de distribución real de estas webs.
Éxito: CTR de links compartidos.

**4.2 · SEO generado por tienda (alto, M).**
`title`/`description`/OG derivados de rubro + ciudad + especialidades (datos que ya existen) y, cuando haya catálogo, JSON-LD `Product`/`Offer`, `FAQPage` (el dueño ya carga FAQs) y `AggregateRating` (ya hay reseñas y estrellas). Sitemap por tienda y `robots` correcto para subdominios.

**4.3 · Auditoría con "arreglar" (alto, M).**
`frontend/src/components/studio/health.js` ya detecta contraste, bloques vacíos, textos largos y assets pesados, pero vive en el Studio. Reusarlo en el dash post-aplicación y ofrecer auto-fix: el motor puede bajar densidad, cambiar variante de hero, acortar titular o pedir la foto que falta. Mismo diagnóstico, acción concreta.

**4.4 · Copy assist offline (medio, M).**
"Mejorá este texto" sin LLM: detectar largo, repetición, falta de CTA, jerga; proponer variantes con las plantillas de `ai_design_copy` y el diccionario del rubro. Aplicar en el editor de "Mi empresa", no solo en el autofill inicial.

**4.5 · Modo campaña (medio, M).**
Calendario AR (Hot Sale, Navidad, Día del Padre, vuelta a clases): recompone hero + announcements + countdown con datos reales y vencimiento. Es la feature que hace que el dueño vuelva a la IA cada mes en vez de una vez.

## 5. Aprendizaje: que el motor sepa qué funciona

**5.1 · Telemetría del funnel (alto, M).**
Hoy no hay una sola métrica de la sección. Instrumentar: pasos completados, abandono por paso, generaciones por sesión, "ver otro estilo", aplicar, elegir/probar/quitar extras, tiempo hasta publicar. Sin datos no se puede mejorar el motor con evidencia.

**5.2 · Feedback por propuesta (alto, M).**
Botón "me gusta / no me gusta" por tarjeta + motivo corto. Guardado por tienda y por features (plantilla, familia, par, objetivo), ajusta la afinidad local con un prior simple. El motor es determinista; esto lo vuelve adaptativo sin LLM.

**5.3 · Qué estilo convierte (alto, L).**
`StoreDailyVisit` y `/stats/` ya miden visitas, pero no el clic que importa (WhatsApp, contacto, catálogo). Eventos outbound por tienda + agregado por rubro: con eso el ranking de `_style_candidates` puede priorizar lo que convierte y no solo la afinidad declarada. Círculo: diseño → datos → mejores propuestas.

**5.4 · Golden set y regresión visual (medio, M).**
Ya hay una suite fuerte de contrato. Sumar snapshots de las propuestas aprobadas (seed + JSON + captura) para detectar regresiones de composición entre versiones del motor, como se hace con las plantillas.

## 6. La apuesta de fondo (decisión de negocio, no técnica)

**6.1 · LLM acotado, si y solo si se justifica.**
El motor actual es un sistema experto: barato, privado y reproducible. Un LLM no mejora el layout (el contrato cerrado es una ventaja), pero sí el brief y el copy. Si se abre la puerta: solo `brief → respuestas normalizadas` y `texto → copy`, nunca el `layout_config`; validación contra el contrato, cache por hash, tope de coste por cuenta, timeout y fallback al motor local. Riesgos a cubrir antes: prompt injection en el brief, PII del negocio, latencia, coste por generación y que un texto inventado no llegue a la web publicada. Alternativa sin coste: parser offline (1.2) + copy assist (4.4), que cubren el 80 % sin salir del determinismo.

## Roadmap sugerido

| Fase | Contenido | Duración |
|------|-----------|----------|
| 1 · Credibilidad | 0.1, 0.2, 0.3, 2.3, 2.5, 5.1 | 1-2 semanas |
| 2 · Decisión | 1.1, 1.3, 2.1, 3.1, 3.2, 3.4 | 4-6 semanas |
| 3 · Retención | 4.1, 4.2, 4.3, 4.5, 5.2, 5.3 | 6-8 semanas |
| 4 · Opcional | 6.1 (LLM acotado) tras validar coste/beneficio con datos de la fase 3 | — |

## Qué NO hacer

- IA que prometa datos del negocio (precios, horarios, envíos) sin dato real: el motor ya es estricto acá, no aflojarlo por "llenar" la web.
- Mostrar un score numérico que no discrimina (0.3): peor que no mostrar nada.
- Dueño que no entiende qué cambió: toda propuesta tiene que explicar su tesis en una línea y todo cambio automático tiene que poder deshacerse.
- Generar layout con LLM: el contrato cerrado (`layout_blocks.py`, `clean_layout_config`, whitelist de plantillas) es lo que evita webs rotas y planes violados.
