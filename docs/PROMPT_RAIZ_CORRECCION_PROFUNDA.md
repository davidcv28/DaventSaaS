# PROMPT — Corrección profunda del diseño Raíz (v2)

> **Uso:** pegar el bloque completo (§1 en adelante) a un agente de código con acceso a este
> repo. Reemplaza, para el diseño **Raíz**, lo que dice `docs/PROMPT_REDISENO_PLANTILLAS.md`
> §6.1 y el contrato de diseño de `docs/PLANTILLAS_INTERFAZ.md` §5–§6. Una sola pasada, un
> solo agente, sin subagentes.

---

## 1. Rol

Sos **frontend senior + director de arte digital**. No sos un ejecutor de tickets: tenés
criterio visual, oficio de CSS, y sabés distinguir una web que *parece* una plantilla de una
web que parece hecha por un estudio. Tu trabajo en esta tarea no es "mejorar un poco": es
**rehacer la capa visual del diseño Raíz** hasta que se vea caro, específico y memorable.

Stack: Vue 3 + CSS plano (sin Tailwind), Django/DRF solo como fuente de datos. El diseño vive
en:

| Archivo | Rol | Tamaño actual |
|---|---|---|
| `frontend/src/assets/store-raiz.css` | piel completa del diseño | 395 líneas |
| `frontend/src/views/store/raiz/InicioView.vue` | composición de la portada (17 bloques) | 46 líneas |
| `frontend/src/views/store/raiz/CatalogoView.vue` | catálogo | 9,7 KB |
| `frontend/src/views/store/raiz/ProductoView.vue` | ficha de producto | 13 KB |
| `frontend/src/views/store/raiz/ServiciosView.vue` | embudo de presupuesto | 43 KB |

Contexto de producto: **Raíz es el diseño del plan Básico** (y el fallback global de cualquier
tienda sin diseño avanzado). Lo ven la mayor cantidad de clientes y la mayor cantidad de
visitantes. Hoy es, literalmente, la cara de DAVENT.

---

## 2. Veredicto

El diseño Raíz actual está **aprobado funcionalmente y reprobado visualmente**. Cinco
síntomas, todos verificables:

1. **El modo noche no existe.** Salvo el color de algunos botones que pinta el CSS compartido,
   la web no cambia nada al tocar el interruptor de tema.
2. **La ubicación de los elementos está rota o es irrelevante**: hero 50/50 acotado por `ch`,
   imagen que desaparece en móvil, secciones cuya separación depende de qué bloques cargó el
   dueño, FAQ centrada a 860 px dentro de una grilla de 1200, dos bandas idénticas "card dentro
   del container", grillas que cambian de columnas sin criterio editorial.
3. **Falta profesionalismo y animaciones.** Hay un solo gesto (`v-reveal` en cada bloque, sin
   escalonado) y hovers de 2 px. El "polish" del CSS compartido (shimmer, spotlight, sombras)
   lo apaga Raíz con `box-shadow: none`.
4. **Hay texto que no contrasta**: el acento del dueño se usa como color de texto sobre fondos
   claros y, con 5 de los 8 acentos del catálogo, no llega ni a 3:1.
5. **Parece genérico**: píldoras en todo, radios 20/28 uniformes, banda de acento idéntica para
   hero, beneficios y CTA, todo centrado, cero detalle editorial (reglas, numeración, pies de
   foto, jerarquía tipográfica real).

---

## 3. Autorización explícita: rompé las reglas de diseño del sistema

**Esta sección deroga, para Raíz, las reglas de diseño vigentes.** No pidas permiso para
romperlas, no las cites como bloqueantes, no las "respetes por consistencia". Quedan
**suspendidas**:

- `docs/PROMPT_REDISENO_PLANTILLAS.md` §6.1 (paleta, tipografía, formas y ritmo de Raíz) y la
  sección "Anti-objetivos (si te tienta, no)". La referencia anterior manda menos que el
  resultado. Este prompt la sustituye.
- `docs/PLANTILLAS_INTERFAZ.md` §5 (tokens `--rz-*`, `--sp-*` como contrato) y **§6 completo
  ("Qué NO puede tocar un agente de diseño")**: como director de arte de Raíz podés tocar
  `components/store/**`, `StorePublicLayout.vue`, el CSS compartido y los bloques, siempre que
  otras plantillas no cambien de aspecto (ver §4).
- "Los 3 diseños son composiciones fijas" / "orden canónico de secciones": **podés cambiar el
  orden, fusionar, partir o inventar secciones de Raíz**. Si el orden nuevo se ve mejor, gana
  el orden nuevo.
- "Un diseño no duplica CSS de otro" / "no agregar primitivas": podés crear primitivas propias
  de Raíz (`rz-*`) y duplicar lo que haga falta si el resultado es más limpio.
- "Radios 20/28 + píldoras en todo" y cualquier escala de formas heredada: se reemplaza por la
  escala nueva de §6.
- "No agregar dependencias": podés crear módulos internos (composable, directiva, CSS propio),
  **pero** antes de agregar una dependencia externa al `package.json` o un recurso de CDN,
  justificá por qué CSS + Web Animations API no alcanzan. La CSP es cerrada: nada de hosts
  nuevos.
- "El sitio no puede verse distinto según el acento": sí puede y debe. El acento es un
  parámetro de diseño, no un color pegado encima.
- Cualquier guideline de estilo que te estorbe: **tenés autonomía**. Si te desviás de este
  documento, documentá la desviación y por qué es mejor.

Lo que sí es innegociable está en §4. Todo lo demás —estructura, paleta, tipografía, ritmo,
movimiento, orden de secciones, HTML de los bloques— está en juego.

---

## 4. Lo único que no se rompe

Esto es contrato funcional y legal, no "regla de diseño":

1. **Datos y API**: no se agregan ni cambian campos, endpoints, permisos, gating por plan ni el
   modelo de datos. Raíz se pinta con lo que ya viaja en `GET /api/stores/public/<slug>/` y
   `/catalog`.
2. **Otras plantillas intactas**: Trama y Circuito deben verse **byte a byte iguales**. Si
   tocás CSS compartido o bloques, encapsulá con `[data-template='raiz']` (o `data-store-template`),
   y verificá que no cambie nada fuera de Raíz.
3. **Accesibilidad real**: contraste AA (4.5:1 texto / 3:1 texto grande y UI), foco visible,
   navegación por teclado, `prefers-reduced-motion` respetado, sin movimiento que impida leer.
4. **Estados y datos vacíos**: los bloques se auto-ocultan sin contenido; la web tiene que
   verse bien con 0 productos, 0 galería, 0 testimonios, sin logo, sin titular, con nombre
   larguísimo, con producto sin imagen, con imágenes verticales/horizontales mezcladas.
5. **Responsive sin scroll horizontal** en 320/360/390/414, y sin romper en 1920.
6. **Sin FOUC ni saltos de tema**: el tema (claro/oscuro) se aplica antes de pintar; nada de
   flash blanco al cargar en modo noche.
7. **Rendimiento**: CSS + JS livianos, sin librerías de animación nuevas, sin imágenes extra,
   sin layout thrash. La web pública es la primera impresión del cliente.
8. **Build y tests**: `cd frontend && pnpm build` sin errores nuevos; no romper la suite de
   plantillas ni las verificaciones del CI.
9. **Fuente del dueño**: `--store-font` (fuente elegida en "Diseño web") debe seguir
   aplicándose al texto de la web. Hoy Raíz la pisa con Manrope: **eso es un bug a corregir**,
   no una decisión válida.

---

## 5. Diagnóstico técnico verificado

No "creas" este diagnóstico: **confirmalo leyendo el código y midiendo en el navegador** antes
de tocar nada. Los archivos y líneas son el punto de partida.

### 5.1 Modo noche muerto (causa raíz)

- `store-page.css:39-45` define los únicos tokens oscuros del sistema (`--sp-bg`, `--sp-card`,
  `--sp-ink`, …) bajo `.store-page[data-store-theme='dark']`.
- `store-raiz.css:34-51` **remapea `--sp-*` a `--rz-*`**, y `--rz-*` está hardcodeado en modo
  claro (`:8-32`: `--rz-bg:#F5F6F3`, `--rz-surface:#FFFFFF`, `--rz-ink:#17211C`, …).
- Resultado: el tema oscuro define variables que Raíz vuelve a pisar con valores claros. Y en
  las 395 líneas de `store-raiz.css` **no hay ni un solo selector `[data-store-theme='dark']`**
  (verificalo: `grep -c "store-theme" store-raiz.css` → 0).
- El interruptor **sí existe** y está visible por defecto en planes base:
  `StorePublicLayout.vue:212-216` → `showThemeToggle = custom.theme_toggle ?? !hasDesignAdvanced`.
  Un visitante toca la luna y solo ve cambiar el color de un par de botones que pinta el CSS
  compartido. Eso es peor que no tener modo noche: parece roto.

### 5.2 Composición

- `store-raiz.css:124-142`: hero `split` con `--rz-container:1200`, título `max-width:24ch`,
  subtítulo `54ch`, gap 48. Es un layout de landing genérica 50/50.
- `store-raiz.css:384`: en ≤640 px `.sp-hal-media{display:none}` → el hero queda como texto
  suelto sin composición.
- Ritmo inconsistente: algunas secciones usan `padding-top: var(--rz-section)` (`:175, :183,
  :203, :213, :217, :221, :226`), otras `56px` (`:208`), otras `0` (`:190`). Como los bloques
  se auto-ocultan, el espacio entre secciones **depende de qué cargó el dueño**.
- Dos bandas idénticas "caja de color dentro del container": `.sp-benefits .sp-container`
  (`:191`) y `.sp-cta .sp-container` (`:227`), la misma receta dos veces en el mismo scroll.
- `.sp-faq-wrap{max-width:860px; margin-inline:auto}` (`:223`) centrado dentro de una grilla
  alineada a la izquierda de 1200 → eje de lectura quebrado.
- Todo centrado: hero centrado, section-head centrada, CTA centrada, contacto centrado. Cero
  asimetría, cero tensión, cero jerarquía espacial.

### 5.3 Contraste (medido, no estimado)

El dueño elige uno de 8 acentos (`stores.api.js:666-675`). Raíz los usa como **color de texto**
en eyebrow, cifras, tags y en `accent-text` sobre `accent-soft`, y como fondo de bandas.
Ratios reales (WCAG 2.1, texto normal = 4.5 / grande y UI = 3.0):

| Acento | texto acento sobre `#F5F6F3` | sobre `#E9ECE6` | `accent-text` sobre `accent-soft` | blanco sobre acento |
|---|---|---|---|---|
| Índigo | 5.80 | 5.27 | 6.92 | 6.29 |
| Violeta | 5.25 | 4.78 | 6.33 | 5.70 |
| Esmeralda | **3.47** | **3.16** | 4.56 | **3.77** |
| Ámbar | **2.94** | **2.67** | **3.98** | **3.19** |
| Rosa | 4.33 | **3.94** | 5.38 | 4.70 |
| Celeste | **3.78** | **3.43** | 4.90 | **4.10** |
| Naranja | **3.28** | **2.98** | **4.34** | **3.56** |
| Lima | **2.85** | **2.59** | **3.90** | **3.09** |

Conclusión: **5 de 8 acentos no alcanzan AA como texto, y 3 no alcanzan ni el 3:1 de texto
grande**. Los casos concretos en código: `.sp-eyebrow` (`:158`), `.sp-about-list li` (`:177`),
`.sp-stat strong` (`:180`), `.sp-linkbtn`, `.rz-promos-label`, `.sp-top .sp-icon-btn:hover`.
Además: los tokens claros están al límite (muted 5.01 sobre `surface-2`), y en modo oscuro el
`--sp-accent-text: var(--store-accent)` compartido deja acentos oscuros sobre superficie oscura
por debajo de 3:1.

### 5.4 Movimiento

- `frontend/src/directives/reveal.js:22-31`: `v-reveal` acepta un delay (`--rv-d`) que **nadie
  pasa**. Todos los bloques entran a la vez, con la misma curva y el mismo desplazamiento: el
  gesto más "plantilla" que existe.
- `store-page.css:441-447` define `.sp-rv`; `:486-500` tiene shimmer/spotlight/hover. Raíz lo
  aplana con `box-shadow:none`, bordes repetidos y `translate: 0 -2px` (`:168`).
- No hay entrada del hero, ni estado de header al scrollear, ni contadores, ni parallax
  contenido, ni transición de tema, ni micro-interacción en precios/badges.

### 5.5 Por qué se ve genérico (lista franca)

- Píldoras (`999px`) en botones, chips, tags, inputs, contadores, filtros; radio 20 en todas las
  tarjetas, 28 en media. Una sola forma para todo = cero jerarquía.
- Una única banda de acento (gradiente radial + grano) usada como recurso para hero, benefits
  y CTA.
- Tipografía: `--rz-display` declarado pero usado casi solo en h1/h2; el resto es Manrope
  genérico; sin escala tipográfica real, sin versalitas, sin numeración tabular en precios.
- Sin elementos de firma: no hay reglas hairline, ni numeración de secciones, ni sellos, ni
  pies de foto, ni etiquetas tipo ficha técnica. Nada que diga "esta marca tiene criterio".
- El chrome (header/footer) es el compartido con overrides de color: se nota que es un tema
  encima de un layout base.

---

## 6. Dirección de arte v2 — "Raíz: mostrador de barrio con criterio editorial"

El concepto: **comercio real, curado con ojo editorial**. Papel cálido, tinta verde-negra,
acento del dueño usado como *marca* (subrayados, sellos, numeración, un plato de color), no como
pintura de fondo. Densidad alta en información, aire generoso en los márgenes. Sobriedad tipo
revista de negocios + calidez de local de barrio. **Nada de "SaaS moderno"**: cero glassmorphism
generalizado, cero blobs, cero gradientes violeta.

### 6.1 Paleta dual (claro / oscuro)

Tema claro — papel cálido, no gris frío:

```
--rz-bg:        #F4F3EE   /* papel */
--rz-surface:   #FFFFFF   /* tarjeta */
--rz-surface-2: #EBEAE2   /* bloque secundario */
--rz-surface-3: #E1DFD4   /* hundido / inputs */
--rz-line:      #D8D6CA
--rz-line-strong:#B4B1A2
--rz-ink:       #101A16
--rz-ink-2:     #2F3B35
--rz-muted:     #59655E
--rz-accent:    var(--store-accent)                 /* del dueño */
--rz-accent-text: color-mix(in srgb, var(--store-accent) 66%, var(--rz-ink))  /* texto AA */
--rz-accent-soft: color-mix(in srgb, var(--store-accent) 9%, #fff)
--rz-band-1:    var(--sp-band-base1)
--rz-band-2:    var(--sp-band-base2)
--rz-ok:        #146C43
--rz-danger:    #A3221A
```

Tema oscuro — tinta verde, **no** negro puro ni inversión del claro:

```
--rz-bg:        #0B1210
--rz-surface:   #111A16
--rz-surface-2: #16211C
--rz-surface-3: #1C2A23
--rz-line:      #27352E
--rz-line-strong:#3B4C43
--rz-ink:       #EDF2EE
--rz-ink-2:     #C4CFC8
--rz-muted:     #93A29A
--rz-accent-text: color-mix(in srgb, var(--store-accent) 42%, #fff)  /* texto AA en oscuro */
--rz-accent-soft: color-mix(in srgb, var(--store-accent) 16%, transparent)
--rz-ok:        #6EE7A8
--rz-danger:    #FF8A7A
```

Reglas de la paleta:

- **Ajustá los hex si al medir no dan los ratios.** Los valores son una propuesta de dirección,
  no una verdad revelada. Lo que no se negocia son los ratios de §10.
- `--rz-accent-text` es un **token separado del acento**: el acento crudo nunca se usa como
  color de texto sobre fondo claro. El acento crudo se usa como fondo, borde, marca gráfica o
  detalle.
- El tema oscuro tiene **escalera de elevación** (bg → surface → surface-2 → surface-3) y
  bordes que se aclaran, no sombras enormes. Las sombras en oscuro son profundas y de bajo
  spread (`0 18px 40px -24px rgb(0 0 0 / .85)`).
- En oscuro, **las fotos de producto no se filtran** (el comercio vive de que el color sea
  real); solo las decorativas pueden bajar un 8-12 % de brillo.

### 6.2 Tipografía

- Display: la fuente del **dueño** si es display (`--store-font` ya la aplica), si no una sans
  de sistema con peso 700/800 y tracking negativo, o una display del catálogo ya cargada por la
  plantilla. **No agregues familias nuevas.**
- Cuerpo: `var(--store-font)`. Fix del bug actual: la raíz de Raíz **no** debe fijar Manrope;
  debe heredar `--store-font` y usar familia propia solo para display/labels.
- Escala (clamp, móvil→desktop): `h1` 44→84, `h2` 32→48, `h3` 22→26, lead 18→21, cuerpo 16,
  pequeño 14, label 11–12 uppercase `+.12em`. Precios y cifras con
  `font-variant-numeric: tabular-nums`.
- Jerarquía por **contraste de escala y color**, no por poner todo en bold.
- Numeración editorial de secciones: `01 — Categorías`, `02 — Recientes`… en label mono/uppercase
  con regla hairline al lado. Es la firma de la plantilla.

### 6.3 Grid y ritmo

- Contenedor 1240 px, gutter 32 (20 en móvil), grilla de 12 columnas con gap 24.
- Escala de espacio: 4/8/12/16/24/32/48/64/96/128. Ritmo vertical **uniforme**: cada sección
  tiene `padding-block` de la misma escala (96/96 desktop, 64/64 móvil) y la sección que abre
  porta su propio ritmo. Eliminá el patchwork de `padding-top` por sección.
- Asimetría permitida y deseada: 7/5, 5/7, 8/4. Nada de todo centrado.
- Reglas hairline (`1px var(--rz-line)`) como separadores entre filas de listas y bajo el
  header; úsalas como lenguaje, no como decoración.

### 6.4 Firma visual (2-3 recursos, no más)

1. **Regla + numeración** en cada sección (label uppercase + línea que se completa al revelar).
2. **Sello/placa de acento**: un rectángulo de acento rotado −2° (o etiqueta de ficha) con
   datos del negocio (años, ubicación, "desde 2019"). Un solo uso por página.
3. **Precio tabular con guía**: precio grande, oferta con tachado fino y badge `-N%` en placa
   de acento (no píldora).

### 6.5 Composición por sección (portada)

El orden es una propuesta fuerte: **si al implementar encontrás uno mejor, cambiá el orden y
justificá**. Pero no vuelvas al orden actual por inercia.

1. **Cinta de anuncios** — franja de tinta, marquee hairline, label 11px, separadores `·`.
2. **Hero editorial asimétrico** — sin banda de acento a sangre. Papel de fondo, copy en
   columnas 1-7 (eyebrow con regla, h1 enorme en 2-3 líneas, lead, 2 CTAs, meta), visual en
   columnas 8-12 (imagen 4:5 + placa de acento superpuesta con el sello). En móvil: el visual
   **no desaparece**, pasa a una franja 3:2 después del h1 y antes de los CTAs.
3. **Franja de garantías** — fila hairline de 4 ítems con icono lineal 16px, sin tarjetas, sin
   fondo.
4. **Categorías** — grilla editorial asimétrica (2 grandes 7/5 + 3 chicas), imagen con caption
   y número; hover: zoom suave + flecha.
5. **Recientes / destacados** — 4-up uniforme 4:5, tarjeta sin borde (solo media + texto), precio
   tabular, hover con elevación mínima y subrayado del nombre.
6. **Nosotros** — 2 columnas con imagen que se solapa al bloque de texto, cifras inline con
   hairlines, especialidades como lista con guiones (no chips).
7. **Cifras** — banda de papel con numerales gigantes y label; **sin tarjetas**.
8. **Servicios** — lista numerada de filas (01…06) con regla y flecha, no grilla de tarjetas con
   icono.
9. **Beneficios** — **banda a sangre** de tinta (rompe el contenedor), numerales grandes,
   columnas con regla vertical de acento.
10. **Cuenta regresiva** — placa de tinta con números tabulares gigantes; solo si hay oferta
    vigente.
11. **Ofertas** — 3-up con acento en precio y `-N%`; regla bajo el título.
12. **Marcas** — fila hairline, logos en gris, color en hover.
13. **Galería** — composición tipo revista (2 filas asimétricas), caption al hover, lightbox
    accesible ya existente.
14. **Testimonios** — un testimonio destacado grande + fila de 3; no 3 tarjetas iguales.
15. **FAQ** — dos columnas: título sticky a la izquierda, `<details>` a la derecha. **Nunca**
    centrado a 860.
16. **CTA final** — banda de acento **distinta** de la de beneficios (full-bleed, tipografía
    display, botón de tinta), no la misma caja repetida.
17. **Contacto** — split 5/7: datos + redes a la izquierda, formulario en superficie elevada a
    la derecha; mapa dentro del bloque si existe.
18. **Pie** — wordmark grande, 4 columnas, hairline superior, nota final.

Catálogo / ficha / servicios: misma dirección — encabezado con breadcrumb + h1 + contadores
integrados en una fila (no tarjetas flotantes), filtros en riel sticky de 280 con secciones
hairline, grilla 3-up 4:5, ficha con galería 7/5 y panel de compra sticky, servicios con la
misma numeración y reglas.

---

## 7. Modo oscuro: especificación completa

No alcanza con "cambiar los tokens". Tiene que ser un **tema real**:

1. **Raíz del tema**: definir el bloque oscuro en `store-raiz.css` con
   `.store-page[data-template='raiz'][data-store-theme='dark']` (mayor especificidad que el
   alias `--sp-*`) y volver a mapear `--sp-*` a los `--rz-*` oscuros. Verificá que el bloque
   compartido `store-page.css:39` no quede pisado.
2. **Superficies**: bg, surface, surface-2, surface-3, líneas, bandas. Cada contenedor tiene que
   leerse como una capa distinta sin bordes chillones.
3. **Todas las piezas**, no solo el fondo: header (que hoy es de acento), drawer, buscador,
   bottom-bar móvil, tarjetas, filtros, inputs, selects, `<details>`, modales, lightbox,
   toasts, skeletons (`rz-skel`), empty states, paginación, contadores, estrellas de rating,
   badges `Nuevo/-N%/Promo/Agotado`, chip de "soporte en línea", widget de chatbot, mapa,
   scrollbar, `::selection`, autofill de Chrome.
4. **Imágenes**: producto sin filtro; decorativas con brillo contenido; cualquier texto sobre
   imagen necesita scrim ≥ 55 % o placa sólida.
5. **Sombras y foco**: sombras profundas, foco con contraste ≥ 3:1 contra la superficie
   (no `outline` del acento crudo si no llega).
6. **Transición de tema**: cambio de fondo/color/borde de 180 ms `ease-out` en los contenedores
   principales (no en `*`), y **cero transición** con `prefers-reduced-motion`.
7. **Persistencia y preferencia**: respetá `theme_toggle` del dueño, el default por
   `prefers-color-scheme` y la elección guardada del visitante
   (`localStorage davent:store-theme:<slug>`, ya implementado en `StorePublicLayout.vue:195-216`).
   No cambies esa lógica; hacé que el CSS la honre.
8. **Sin flash**: `color-scheme` correcto y `meta[name=theme-color]` sincronizado con el tema
   (`StorePublicLayout.vue:~518` hoy usa siempre el acento oscuro).
9. **QA de tema**: cada página (inicio, catálogo, producto, servicios) en claro y oscuro, con
   los 8 acentos, con y sin imágenes. Todo contenedor con texto tiene que pasar §10.

---

## 8. Movimiento: sistema, no adornos

Tokens (definilos en `store-raiz.css` y usalos en todo):

```
--rz-e-out:   cubic-bezier(.16, 1, .3, 1)
--rz-e-inout: cubic-bezier(.65, 0, .35, 1)
--rz-d-1: 120ms   /* press, hover de control */
--rz-d-2: 200ms   /* hover de tarjeta, header */
--rz-d-3: 380ms   /* reveal de bloque */
--rz-d-4: 700ms   /* entrada de hero / media */
```

Dirección:

- **Entrada de hero**: escalonada real (eyebrow 0, h1 60 ms, lead 120, CTAs 180, visual 240)
  usando los valores que `v-reveal` ya soporta (`v-reveal="60 * i"`); una sola vez, al montar.
- **Reveals de sección**: escalonado de 60–80 ms por hijo, máximo ~300 ms total, desplazamiento
  24 px, opacidad. Usá la directiva existente; no reimplementes el `IntersectionObserver`.
- **Header**: al scrollear >8 px baja a 56 px, hairline + blur; vuelve al tope. `passive` +
  `requestAnimationFrame`, sin jank.
- **Tarjetas**: `translateY(-4px)` + sombra + `scale(1.03)` de la imagen (400 ms), subrayado del
  nombre que se dibuja; el mismo estado en `:focus-visible`.
- **Botones**: press `scale(.985)`, flecha que se desplaza 2 px; sin rebotes elásticos.
- **Marcas/giros**: marquee pausa al hover/foco; contadores de cifras animan al entrar (valor
  final si `prefers-reduced-motion`).
- **Transición entre páginas**: mantener `sp-page-*` y sumar un fade/translate corto coherente.
- **Prohibido**: animar `filter: blur()` en superficies grandes, `box-shadow` en scroll,
  parallax sobre texto, autoplays infinitos que no se pueden parar, cualquier cosa que ignore
  `prefers-reduced-motion` (`store-page.css:416` y el bloque final de `store-raiz.css` deben
  cubrir pseudos también).
- **Performance**: solo `transform`/`opacity`, `will-change` en ≤ 4 elementos, nada de JS por
  frame salvo header y contadores.

---

## 9. Contraste y accesibilidad (criterio de aceptación, no sugerencia)

1. Texto normal ≥ **4.5:1** contra su fondo real (incluido el fondo de un contenedor, no el de
   la página). Texto grande (≥24 px o ≥19 px bold) ≥ **3.0:1**. Bordes/íconos/foco ≥ **3.0:1**.
2. **Medí, no estimes.** Calculá los ratios con un script rápido (uno temporal en `.qa-tmp/`,
   no commitear) sobre los pares reales: para cada uno de los 8 acentos, en claro y oscuro,
   sobre bg, surface, surface-2, accent-soft, band. Reportá la matriz en la entrega.
3. Reglas de composición de color:
   - Acento crudo = fondo/marca, **nunca** texto sobre claro (usá `--rz-accent-text`).
   - Blanco sobre acento solo cuando el acento pase 4.5:1 (la banda ya lo garantiza vía
     `--sp-band-base1/2` de `colorTools.js:187-189`; el resto de usos no).
   - Texto sobre imagen: scrim sólido o placa; prohibido texto directo sobre foto clara.
   - `--rz-muted` ≥ 4.5:1 sobre bg **y** surface-2 (hoy 5.01, margen fino: no lo empeores).
   - Estados (`hover/active/disabled/error/ok`) también medidos; `disabled` puede bajar de 4.5
     pero no puede quedar ilegible.
4. Foco: anillo de 2 px con offset 2 y contraste propio; visible en fondo claro, oscuro y sobre
   bandas de acento.
5. Teclado: tab order lógico, skip a contenido si el header lo justifica, `<details>` de FAQ
   nativos, foco atrapado en modales/lightbox (ya existente: no lo rompas).
6. Semántica intacta: `h1` único por página, jerarquía de headings, `aria-label` en icon-buttons,
   `alt` de imágenes reales.

---

## 10. Alcance de archivos

**Podés tocar:**

- `frontend/src/assets/store-raiz.css` — podés reescribirlo de cero.
- `frontend/src/views/store/raiz/**` — composición, orden de bloques, markup de las vistas.
- `frontend/src/components/store/blocks/*.vue` y `frontend/src/components/store/**` — con
  cuidado: cambios **aditivos** (nuevas variantes, nuevas clases, nuevos bloques
  `Blk*Raiz.vue`). Si modificás markup compartido, encapsulá el cambio por template y verificá
  que Trama/Circuito no cambien.
- `frontend/src/assets/store-page.css`, `store-catalog*.css`, `store-services.css` — solo con
  reglas bajo `[data-template='raiz']` (o creando hojas nuevas importadas por Raíz).
- `frontend/src/views/StorePublicLayout.vue` — solo cambios aditivos justificados (clase de
  scroll, `theme-color`, hook de tema). Nada que afecte a otros diseños.
- Nuevos archivos internos: composable de header, utilidad de contraste, hoja extra de Raíz.

**No toques:** backend (`StoreApp/**`), `stores.api.js` (salvo nada), `templates/index.js`,
datos/permisos/gating, `views/store/trama/**`, `views/store/circuito/**`, sus CSS,
`package.json` (sin justificación), configuración de build, `.env`.

---

## 11. Plan de trabajo

| Fase | Entregable | Checkpoint |
|---|---|---|
| 0. Auditoría | ratios medidos, capturas de las 4 páginas en claro/oscuro con 8 acentos, lista de defectos concretos | diagnóstico escrito de 10 líneas |
| 1. Tokens duales | paleta clara/oscura, escala tipográfica, radios, sombras, spacing | `pnpm build` ok, contraste medido |
| 2. Composición | nueva portada (orden y layout), catálogo, ficha, servicios, chrome, footer | review visual en 360/768/1280 |
| 3. Modo noche | todos los componentes del §7 en oscuro | capturas claro/oscuro de las 4 páginas |
| 4. Movimiento | sistema del §8, reduced-motion verificado | sin CLS, sin jank |
| 5. QA | matriz de contraste, responsive, estados vacíos, otras plantillas intactas | checklist §12 completo |

Trabajá en ese orden. No entregues "fase 1 y vemos": la tarea termina cuando el diseño está
completo.

---

## 12. QA y aceptación

Comandos:

```bash
cd frontend && pnpm build
grep -c "data-store-theme" src/assets/store-raiz.css      # > 0 obligatorio
grep -rn "max-width: *860\|padding-top: *var(--rz-section)" src/assets/store-raiz.css
node .qa-tmp/raiz-contrast.mjs                            # script temporal, no se commitea
```

Matriz mínima de revisión visual (capturas):

- Páginas: inicio, catálogo, ficha de producto, servicios, contacto (ancla).
- Temas: claro y oscuro.
- Acentos: #0F766E (default), ámbar `#d97706`, lima `#65a30d` (los peores casos).
- Anchos: 360, 390, 768, 1024, 1280, 1440, 1920.
- Estados: tienda vacía, sin logo, sin titular, nombre de 60 caracteres, producto sin imagen,
  galería con imágenes verticales y horizontales.

Definición de terminado:

- [ ] El interruptor de tema produce **cambios visibles y coherentes en toda la página** (no solo
      botones): fondo, superficies, texto, bordes, header, footer, bandas, inputs, tarjetas,
      skeletons, badges y modales.
- [ ] Contraste medido: 0 fallas AA en texto normal; 0 fallas 3:1 en texto grande/UI, en los 8
      acentos y ambos temas.
- [ ] Sin texto centrado a media columna; ejes de lectura alineados; ritmo vertical uniforme.
- [ ] Hero móvil con composición (el visual no desaparece).
- [ ] Cada sección se ve distinta de la anterior (no tres bandas iguales).
- [ ] Animaciones: entrada escalonada real, hover/foco consistentes, `prefers-reduced-motion`
      respetado, sin CLS ni scroll horizontal en 320–1920.
- [ ] `--store-font` del dueño aplicada en toda la web (bug de Manrope corregido).
- [ ] Trama y Circuito siguen idénticas (diff visual o capturas comparadas).
- [ ] `pnpm build` sin errores nuevos; sin dependencias ni recursos externos añadidos.
- [ ] Accesibilidad: foco visible en ambos temas, teclado completo, headings correctos.

---

## 13. Entrega

- Reporte corto: qué cambió por fase, la matriz de contraste medida, y las desviaciones de este
  prompt con su motivo.
- Commits en inglés, conventional (`feat(raiz): …`, `fix(raiz): …`), uno por unidad lógica;
  push a `main` al terminar (regla del repo).
- No tocar `.env`, `venv/`, `node_modules/`, `dist/`.

---

## 14. Anti-metas (esto es lo que hace que se vea IA/genérico)

- No "modernices" con glassmorphism, blobs, gradientes violeta, ni dashboards.
- No uses emojis como iconografía; los iconos son SVG lineales del set existente.
- No inventes datos ni secciones de relleno ("+10k clientes"). Solo lo que existe.
- No pongas animación en todo: si todo se mueve, nada se destaca.
- No dejes dos sistemas visuales conviviendo (media plantilla vieja + media nueva).
- No sacrifiques legibilidad por estética: primero AA, después estilo.
- No conviertas todo en tarjeta. La mayoría de las secciones se leen mejor con reglas y tipografía.
- No uses negro puro ni blanco puro como tema oscuro/claro.
- No repitas la misma forma (radio, banda, degradado) en tres lugares distintos.

---

## 15. Cierre

Tenés permiso para romper el sistema de diseño anterior y obligación de que el resultado sea
mejor, no distinto. El estándar es simple: **si un diseñador senior de producto abriera esta web
en la calle, no debería poder adivinar que es una plantilla**. Cuando termines, mostrá capturas
en claro y oscuro y la matriz de contraste; el resto es opinión.
