# PROMPT — NUEVO DISEÑO "MOVIMIENTO" (gimnasios, tier advanced / Plan Premium)

> Se aplica junto con `AGENTS.md`, `prompt.md` (REGLA — ALTA DE UN NUEVO DISEÑO WEB)
> y `rediseño_prompt.md`. Cada checkbox de `prompt.md` sigue siendo obligatorio.
> Referencia de inspiración: https://www.movementlab.lt — NO es una copia: se toma
> la dirección editorial (tipografía gigante, numeración de pasos, narrativa de
> "no es un gym más") y se construye una composición propia.

## 1. Identidad y nombre

- Slug sugerido: `movimiento` (verificar unicidad contra `DesignPattern`,
  `DesignStyle`, `seed_data.json`, `TEMPLATE_RETIRED_MAP` y la plantilla `gimnasio`
  ya existente — ésta es oscura/lima tipo pista; el nuevo NO puede parecerse).
- Nombre legible: "Movimiento". Familia/rubro: `deporte`.
- Tier: **`advanced`** (disponible a partir de Plan Premium). Registrar el slug en
  el set de templates premium (`TEMPLATE_PLUS`/choices que correspondan a advanced)
  y en `SECTION_BENEFITS`/guards del plan premium.

## 2. Dirección visual (inspiración MovementLab, reinterpretada)

- Editorial claro: fondo hueso/blanco roto, tinta casi negra, UN acento (elegir,
  p. ej. naranja señal o verde cancha) reservado a CTA y datos.
- Titulares display en mayúsculas, condensados y de gran cuerpo, con la última
  palabra o una palabra clave en acento o outline — NO la misma grilla que
  `GyHero` (éste usa cinta de disciplinas; éste usa composición partida).
- Pasos numerados `01 / 02 / 03` como columna vertebral del scroll (MovementLab
  los usa para "Cómo empezar"); acá se reusan como índice editorial en secciones
  distintas (método, servicios, planes).
- Marquesina tipográfica secundaria (fuerza / movimiento / progreso) — distinta
  de la cinta de disciplinas de `gimnasio`.
- Nada de estética "hardcore oscura": este diseño es luminoso, limpio y humano
  (entrenamiento personalizado en grupos chicos), contraste directo con `gimnasio`.

## 3. Superficies obligatorias (las 4, con composición propia)

- **Portada**: hero partido — mitad titular gigante + chips de disciplinas,
  mitad foto de portada con índice `01` y medidor (años, alumnos, sesiones);
  manifiesto "No es una clase grupal. No es un gimnasio."; método en 3 pasos
  numerados; entrenadores (fila editorial con rol); CTA a suscripciones.
- **Servicios**: lista editorial numerada (no cards genéricas) — cada servicio
  como fila con índice, nombre grande, duración/precio y CTA; expande a detalle.
- **Catálogo**: grilla asimétrica tipo revista con filtros en riel superior,
  badges de oferta con ahorro; si el diseño va como patrón HTML, replicar la
  anatomía del documento (migas, filtros, orden).
- **Ficha de producto** (`data-surface="product"`): composición de publicación —
  migas, media grande con índice, precio con oferta tachada + badge, tabla
  `{{product_features}}`, `{{product_related}}`, `{{product_reviews}}` con
  envoltorio `:not(:has(.ds-reviews))` y apagados `:empty`/`:has()` según `prompt.md`.
- **Suscripciones/membresías** (sección propia del diseño, la firma MovementLab):
  tarjetas de planes con sesiones/precio por sesión/periodicidad, precio tachado
  + precio final ("€160 ~~160~~"), plan destacado con borde en acento, bullet
  list y CTA "Select". Debe mapear los servicios/planes que el dueño cargue.

## 4. Menú (debe ser distinto a todos los existentes)

- Propuesta: header partido en dos filas — fila superior fina con contacto
  (teléfono/dirección, mono) y fila principal con marca a la izquierda, links
  centrados y CTA sólido a la derecha; en móvil: hamburguesa + menú a pantalla
  completa con índice numerado (no la tab bar de `sastreria` ni el drawer de `gimnasio`).

## 5. Tipografía y tokens

- Heading/subheading: una condensada display moderna de la lista permitida
  (p. ej. Bricolage Grotesque o Space Grotesk en 700); body: Instrument Sans /
  Inter; mono opcional para índices y datos (JetBrains Mono).
- Declarar `typography.{heading,subheading,body,name_font}` en contrato y tokens;
  `--st-font-*` con `!important` según la regla de `store-page.css`.
- `site_theme` saneado con `clean_site_theme`; `layout_config` completo con todas
  las secciones del contrato (`_SECTION_SPECS` + `contract.js`), saneado con
  `clean_layout_config`.

## 6. Estilos (mínimo 3, identidades propias)

1. `movimiento` — claro, papel + acento señal (default del patrón).
2. `movimiento-noche` — grafito cálido + acento, no invertir con filter.
3. `movimiento-pista` — versión deportiva intensa (bloques de acento grandes,
   numeración gigante de fondo).
- Cada estilo con `categoria`, `layout`, `page_theme` y `tokens` distintos; un
  solo `is_default` global; los 3 deben verse distintos en las 4 superficies.

## 7. Modo noche, móvil, vacíos, animaciones

- Toggle real (header + menú móvil, `aria-pressed`, `localStorage` +
  `prefers-color-scheme`), AA en ambos modos, sin romper el iframe del Studio.
- Móvil: breakpoints ≤480/≤768/≤1024, 1 columna, imágenes centradas, targets ≥44px;
  el hero partido colapsa titular sobre foto (no lado a lado achicado).
- Huecos: rellenar con numeración editorial, líneas guía, marquesina, citas.
- **Preguntar al usuario** por animaciones de fondo/cintas loop antes de cerrar
  (marquesina de disciplinas es candidata natural acá).

## 8. Persistencia

1. `import_design_pattern --file <html> --slug movimiento --nombre "Movimiento" [--style movimiento]`
   o entrada en `seed_data.json` + `seed_design_catalog`.
2. `sync_design_neon --slug movimiento` (solo éste; `NEON_DATABASE_URL` desde `.env`).
3. Verificar `/api/design/catalog/` y las 4 superficies.
4. Commit + push: `feat: add movimiento design`.
