# PROMPT — Diseño no genérico (obligatorio para todo diseño nuevo)

> **Cómo usar:** pegar este bloque completo al inicio de cualquier pedido de diseño/plantilla/patrón (web pública, Studio, landing, catálogo, ficha, servicios, panel). Aplica a agentes y a humanos. Si una regla de este archivo choca con una preferencia estética, gana este archivo.

---

## 0. Regla madre

**Un diseño nuevo NO es un cambio de contenedores.** Si el resultado se puede describir como "la misma web con otros colores, otros radios y otras fuentes", el trabajo está **rechazado** y se vuelve a empezar. Cambiar el diseño significa cambiar la **composición, la jerarquía, el ritmo y los elementos** de la página.

## 1. Prohibido (lista negra)

1. Reutilizar el esqueleto de otra plantilla existente y sólo retocar `border-radius`, `padding`, `box-shadow`, `font-family`, `accent` o el orden de bloques de `layout_config`.
2. Copiar el mismo layout de hero + grilla de tarjetas + footer en todos los diseños.
3. Grillas uniformes de tarjetas idénticas (3×2, 4×2) como única forma de mostrar productos.
4. Fondos planos de un solo color en todas las secciones.
5. Botones, chips y tarjetas con el mismo radio y la misma sombra en todo el sitio.
6. Placeholders de imagen con texto ("Foto de…"), iconos genéricos de librería sin criterio, o `lorem ipsum`.
7. Duplicar un diseño existente cambiando sólo el nombre del slug.
8. Animaciones decorativas sin intención (fade-up en todo, parallax porque sí).

## 2. Obligatorio por diseño (checklist de entrega)

Marcar cada punto; si falta uno, el diseño no está terminado.

- [ ] **Composición distinta:** el layout de al menos 3 secciones principales (hero, destacados, cierre/CTA) es estructuralmente diferente al de cualquier otra plantilla del catálogo. No vale reordenar: tiene que cambiar la retícula (asimétrica, editorial, full-bleed, split, banda desplazada, columna lateral, etc.).
- [ ] **Sistema propio:** paleta (mínimo 6 tokens), escala tipográfica (display + cuerpo + eyebrow, con ratios definidos), radios, espaciado, densidad y estilo de borde/sombra propios. Documentar en el brief del diseño.
- [ ] **Elementos decorativos nuevos:** mínimo **4 piezas** que hoy no existan en la web — p. ej. cinta/marquee, líneas de retícula visibles, numeración editorial, sello/badge, marca de agua tipográfica, formas geométricas, textura de papel/grano, regla ornamental, bloque de color sangrado, sticker, franja diagonal, contador, divisor tipográfico, ornamento SVG propio.
- [ ] **Al menos 1 sección nueva:** un bloque de contenido que no exista en las otras plantillas (manifiesto, proceso, lookbook, comparativa, garantías, "cómo funciona", colección curada, editorial).
- [ ] **Tratamiento de imagen propio:** relación de aspecto, recorte, superposición, marco o composición de imágenes distinta (no todas las fotos en 4:3 con radio 20 px).
- [ ] **Microdetalle:** hover/focus/transición con carácter (subrayado que se dibuja, desplazamiento de letra, inversión de color, borde que crece), coherente con el sistema.
- [ ] **Móvil pensado, no encogido:** la versión 390 px tiene decisiones propias (barra inferior, scroll horizontal, tipografía recalibrada, secciones apiladas con intención).
- [ ] **Accesibilidad:** contraste AA en texto y sobre acento, foco visible, `prefers-reduced-motion`, targets ≥ 44 px, jerarquía de headings correcta.
- [ ] **Datos reales:** todo el copy y las imágenes salen de `StoreCustomization` / catálogo / servicios. Estados vacío, carga y error diseñados.

## 3. Nivel de profesionalismo (baremo de aceptación)

Un diseño se acepta sólo si pasa estas 8 pruebas:

1. **Test de la miniatura:** a 320 px de ancho se reconoce qué diseño es sin leer el nombre.
2. **Test del vecino:** puesto al lado de otra plantilla del catálogo, no parecen hermanos.
3. **Test de la captura:** la pantalla completa se ve como un sitio publicado por un estudio, no como un template de marketplace.
4. **Test de la tipografía:** hay al menos 3 tamaños claramente diferenciados y una decisión de tracking/leading visible.
5. **Test del aire:** el espaciado es intencional (no todo `gap: 24px`); hay secciones densas y secciones respirando.
6. **Test del detalle:** existe al menos un detalle que un usuario no nota conscientemente pero que se siente cuidado (borde de 1 px, guía, marca de esquina, ornamento, numeración).
7. **Test del color:** la paleta tiene jerarquía (fondo, superficie, superficie-2, línea, tinta, tinta-2, muted, acento, on-accent) y el acento se usa con disciplina, no en todo.
8. **Test de la honestidad:** si se quitan los colores y las fuentes, el layout sigue siendo distinto al de las otras plantillas.

## 4. Proceso obligatorio

1. **Brief antes de código:** escribir en 10 líneas la dirección visual (referencia, idea, paleta, tipografía, 4 elementos decorativos, 1 sección nueva, qué se rompe respecto de lo existente). Sin brief no se codea.
2. **Referencia real:** partir de un diseño/referencia concreta (HTML, captura o sitio). Prohibido diseñar "de memoria" reutilizando la plantilla anterior.
3. **Construcción desde la retícula:** definir primero grilla, ritmo vertical y escala tipográfica; después componentes.
4. **Autocrítica antes de entregar:** correr las 8 pruebas de §3 y el checklist de §2. Si falla una, iterar. No entregar "para que el usuario diga".
5. **Verificación visual real:** renderizar en 1360 px y 390 px y mirar la captura (no confiar en el código).
6. **Registro:** alta en el catálogo + `seed` + `sync_design_neon --slug <slug>` en el mismo paso, y commit/push según `AGENTS.md`.

## 5. Frases que invalidan la entrega

Si el agente escribe alguna de estas, se rechaza:

- "Reutilicé la estructura de la plantilla X y cambié los estilos."
- "Mantuve el mismo layout para no romper nada."
- "Es la misma composición pero con otra paleta."
- "Agregué un degradado para que se vea más moderno."
- "Los elementos decorativos quedan para otra iteración."

## 6. Salida esperada del agente

1. Brief visual (§4.1).
2. Checklist §2 completo, marcado.
3. Archivos tocados (plantilla Vue, piel CSS, registro en `templates/`, seed, Neon).
4. Capturas 1360 px y 390 px verificadas.
5. Confirmación de que ninguna otra plantilla comparte la composición.
