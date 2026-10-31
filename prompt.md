# REGLA — ALTA DE UN NUEVO DISEÑO WEB

> Obligatorio en CADA registro de diseño/patrón nuevo. Se aplica junto con `AGENTS.md`
> y `rediseño_prompt.md`. Si un punto no se cumple, el diseño no se considera entregado.

---

## 1. Nombre

- Lo elige el agente, no el usuario.
- Legible en español, 1-2 palabras, sin marcas registradas, sin nombres de empresas
  reales, sin personajes ni franquicias, sin términos de terceros (Google, Apple,
  Nike…), sin ofensas ni ambigüedades.
- `slug` en kebab-case, único, ASCII (`atelier-otono`, no `AtelierOtoño`).
- Verificar antes de crear: `DesignPattern.objects.filter(slug=...)` y
  `DesignStyle.objects.filter(slug=...)` deben devolver vacío; también revisar
  `seed_data.json` y `TEMPLATE_RETIRED_MAP`.

## 2. Compatibilidad con Studio, Diseño y Diseño asistido

- `template` registrado en `frontend/src/templates/index.js` + `TEMPLATE_CSS`
  (y `_shared`/`<tpl>.js` si es plantilla real).
- `layout_config` completo: todas las secciones que el contrato expone
  (`_SECTION_SPECS` en backend + `contract.js` en frontend) con claves válidas;
  saneado con `clean_layout_config`.
- `site_theme` saneado con `clean_site_theme`, incluyendo `palette.{accent,primary,secondary}`,
  `typography.{heading,subheading,body,name_font}` y `--st-font-*`.
- Tokens con nombres del contrato (`--ds-*` / `--st-*`), sin valores hardcodeados fuera del tema.
- Debe funcionar en: Studio (elegir/editar/publicar/versiones), sección Diseño
  (`designTabs`) y Diseño asistido (`POST /api/stores/ai-design/mcp/` debe poder
  aplicar el patrón con `apply_design_overlay` sin perder el overlay).
- Tier declarado (`base`/`plus`/`advanced`); si es premium, el saneo recorta paleta
  igual que un diseño elegido a mano.
- `preview` con imagen o `has_markup` + `iframe srcdoc` sandbox en "Ver este diseño".
- **Alcance obligatorio**: el diseño se implementa siempre para las **tres superficies
  del usuario**: landing page, catálogo y servicios. No se entrega con una sola vista
  resuelta ni se reusa la vista de otro diseño sin adaptarla; las tres salen del mismo
  `layout_config` y comparten piel, pero con composición propia en cada una.

## 2.1 Anti-repetición (obligatorio)

- Prohibido repetir patrones de diseño entre plantillas: si dos diseños comparten
  estructura de secciones, grilla o hero, uno se rehace.
- **El menú debe ser distinto en cada diseño**: no se repite el mismo header/nav
  (posición, alto, alineación, tipografía, CTA, comportamiento en móvil). Alternar
  entre: barra superior clásica, header partido en dos filas, nav lateral fija,
  menú flotante tipo píldora, header centrado editorial, barra inferior en móvil,
  menú a pantalla completa, nav con índice numerado, etc.
- Prohibido generar plantillas genéricas o "de plantilla": nada de hero centrado +
  3 cards + testimonios + footer idéntico al anterior. Cada diseño necesita una idea
  visual reconocible (editorial, técnica, brutalista, catálogo tipo revista, tienda
  inmersiva…).
- Antes de crear: revisar los diseños existentes (`/api/design/patterns/`,
  `StoreApp/domains/design/sources/`) y anotar en qué se diferencia el nuevo.

## 3. Modo noche

- Botón/toggle visible y funcional en la web pública (header y menú móvil),
  con `aria-pressed` y persistencia (`localStorage`) además de `prefers-color-scheme`.
- Variables de tema oscuras reales (no `filter: invert`), contraste AA en ambos modos.
- El toggle no debe romper el iframe de previsualización del Studio.

## 4. Estilos (mínimo 3)

- Crear **al menos 3 `DesignStyle`** sobre el patrón, cada uno con identidad propia:
  distinto `categoria`, `layout`, `page_theme` y `tokens`; sin clones con un color cambiado.
- Al menos uno `is_default` a nivel global (solo uno) y uno por categoría si aplica.
- Los 3 estilos deben verse distintos en portada, catálogo y ficha de producto.

## 5. Móvil

- Breakpoints reales (`≤480`, `≤768`, `≤1024`) con grillas a 1 columna.
- **Toda imagen en columna móvil centrada**: `margin-inline: auto`, `object-fit: cover`,
  `max-width: 100%`, sin `float` ni anchos fijos.
- Sin scroll horizontal, sin texto cortado, targets táctiles ≥44px, menú hamburguesa
  accesible (foco, `Esc`, `aria-expanded`).
- Probar a 375px, 390px y 768px antes de dar por cerrado.

## 6. Estilos únicos

- Paleta propia y coherente (no la del preset por defecto), iconos del set elegido,
  radios/sombras propios y al menos una animación de entrada con `IntersectionObserver`
  o CSS, respetando `prefers-reduced-motion`.
- Nada de gradientes genéricos ni cards idénticas: cada sección con tratamiento propio.

## 7. Tipografías

- Solo familias de uso masivo y actuales, cargadas por `@font-face`/Google Fonts con
  `display=swap` y fallback de sistema: Inter, Manrope, DM Sans, Plus Jakarta Sans,
  Sora, Space Grotesk, Outfit, Bricolage Grotesque, Hanken Grotesk, Instrument Sans,
  Fraunces, Playfair Display, Lora, Source Serif 4, JetBrains Mono.
- Máximo 2 familias + 1 mono opcional; pesos 400/500/600/700.
- Declarar `heading`/`subheading`/`body` en el contrato y en `DesignStyle.tokens`.

## 8. Espacios vacíos

- Revisar cada sección a 1440px y 375px: ningún hueco muerto mayor a un bloque.
- Rellenar con decoración del propio diseño: líneas guía, numeración `01/02`, patrones
  SVG, marquesina, cita editorial, chips, divisores, textura o bloque CTA secundario.
- La decoración nunca tapa contenido ni reduce contraste.

## 8.1 Animaciones de fondo / cintas loop (preguntar siempre)

- **Obligatorio preguntar al usuario antes de cerrar el diseño**: "¿querés animaciones
  detrás del fondo o cintas en loop para decorar?" Se espera respuesta explícita; no se
  asume ni se omite la pregunta.
- Si acepta, implementar con `IntersectionObserver` (pausa fuera de viewport), `transform`
  y `opacity` solamente, `will-change` acotado, `pointer-events: none`, `aria-hidden="true"`,
  y apagado total con `prefers-reduced-motion`.
- Opciones válidas: gradiente malla animado, campo de partículas sutil, cinta marquesina
  (texto o logos), línea/láser en movimiento, grano o dither animado, blobs orgánicos,
  patrón SVG en loop. Elegir la que corresponda a la identidad del diseño, no una por defecto.
- Nunca animar el fondo completo con JS por frame si alcanza CSS; nunca superponer la
  animación sobre texto sin capa de contraste.

## 9. Persistencia (obligatorio, mismo paso)

1. `venv/Scripts/python.exe manage.py import_design_pattern --file <html> --slug <slug> --nombre "Nombre" [--style <slug>] [--accent #hex] [--fonts cuerpo,cabecera]`
   (o seed en `StoreApp/domains/design/seed_data.json` + `seed_design_catalog`).
2. `venv/Scripts/python.exe manage.py sync_design_neon --slug <slug>` — **solo el diseño
   actual**, nunca `--all`. `NEON_DATABASE_URL` desde `.env`, jamás hardcodeada.
3. Verificar el upsert (patrón + estilo de la FK) y que `/api/design/catalog/` lo devuelva.
4. `git commit` + `git push` a `main` con mensaje `feat: add <slug> design`.

---

## Checklist de cierre

- [ ] Landing, catálogo y servicios implementados
- [ ] Menú distinto al de las demás plantillas (sin patrones repetidos)
- [ ] Preguntado al usuario por animaciones de fondo / cintas loop
- [ ] Nombre y slug legales y únicos
- [ ] Studio + Diseño + Diseño asistido funcionando
- [ ] Toggle de modo noche real
- [ ] ≥3 estilos diferenciados
- [ ] Móvil sin scroll horizontal, imágenes centradas
- [ ] Animaciones + iconos + paleta propios
- [ ] Fuentes modernas declaradas
- [ ] Huecos rellenados con decoración
- [ ] `sync_design_neon --slug <slug>` ejecutado y verificado
- [ ] Commit + push
