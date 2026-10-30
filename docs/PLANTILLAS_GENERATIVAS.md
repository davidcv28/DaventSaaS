# Plantillas generativas — contrato del rediseño (6 diseños + portada compuesta por la IA)

> Fase "motor generativo". Objetivo: que **Diseñar con IA** deje de estar atado a
> composiciones fijas. El motor ya genera `layout_config` por superficie; ahora la
> portada pública lo **obedece**: cada diseño monta sus secciones desde el layout
> efectivo (orden + on/off + variante + props) y la IA puede recomponer la página
> para cada cliente. Se suman 3 diseños profesionales nuevos (boutique, alimentos,
> seguridad) portados de las referencias reales, y el motor queda entrenado para
> proponer los 5 estilos de negocio.

## 1. Catálogo (6 diseños, 3 niveles)

| id (≤12) | tier (`TEMPLATE_BASE/PLUS/ADVANCED`) | Rubro firma | Fuentes (`STORE_FONTS`) | Acento por defecto |
|---|---|---|---|---|
| `raiz` | base | generalista / retail | manrope + bricolage-grotesque | `#0F766E` |
| `alimentos` | base | gastronomía / almacén | dm-sans + dm-serif-display | `#C8321D` |
| `trama` | plus | indumentaria / moda | inter-tight + inter | `#1F3A5F` |
| `boutique` | plus | moda premium / deco / joyería | jost + cormorant-garamond | `#6B2D4F` |
| `circuito` | advanced | tecnología / electrónica | space-grotesk + jetbrains-mono | `#22D3EE` |
| `seguridad` | advanced | seguridad / bomberos / industrial | barlow + barlow-condensed | `#C8200E` |

- **`boutique` deja de ser un id retirado**: sacarlo de `TEMPLATE_RETIRED_MAP`
  (backend `models.py` y espejo `stores.api.js`). `alimentos` y `seguridad` son
  ids nuevos (no existían).
- Fuentes nuevas del catálogo cerrado: `jost`, `barlow`, `barlow-condensed`
  (Google Fonts). Sumarlas a `STORE_FONTS` (frontend) y a `FONT_CHOICES`
  (backend, `models.py`) — el catálogo se usa también para `name_font`.
- Los 3 diseños nuevos entran a `DESIGN_SKIN_FREE` (el render los pinta con su
  propia hoja, no con `site_theme`/pieles) y a `TEMPLATE_CSS`.

## 2. Referencias (fuente de verdad visual)

Paquete en `.qa-tmp/design-refs/estilos/`:

| Diseño | Captura | Markup portado (estilos inline legibles) | Valores/loops |
|---|---|---|---|
| boutique | `Estilo boutique · Inicio.png` | `estilo-boutique-inicio.markup.html` | `estilo-boutique-inicio.js` |
| alimentos | `Estilo alimentos · Inicio.png` | `estilo-alimentos-inicio.markup.html` | `estilo-alimentos-inicio.js` |
| seguridad | `Estilo seguridad y bomberos · Inicio.png` | `estilo-seguridad-y-bomberos-inicio.markup.html` | `estilo-seguridad-y-bomberos-inicio.js` |
| base (raiz v2) | `Inicio · escritorio.png`, `Inicio · móvil.png` | `inicio-escritorio.markup.html` | `inicio-escritorio.js` |
| catálogo | `Catálogo · escritorio.png` | `cat-logo-escritorio.markup.html` | — |
| servicios | `Servicios · escritorio.png` | `servicios-escritorio.markup.html` | — |
| indumentaria (trama) | `Estilo indumentaria · Inicio.png` | `estilo-indumentaria-inicio.markup.html` | — |
| tecnología (circuito) | `Estilo tecnología · Inicio.png` | `estilo-tecnolog-a-inicio.markup.html` | — |

El markup usa estilos inline y `{{vars}}`; **no se copia tal cual**: se traduce a
componentes Vue con clases + CSS del diseño. Los textos son placeholders: en el
render salen los datos reales de la tienda.

## 3. Render generativo (el cambio de patrón)

Contrato para **todos** los `InicioView.vue` (nuevos y existentes):

```js
// 1) mapa id de bloque -> componente del diseño (o compartido)
const MAP = { hero: BqHero, categories: BlkCategories, featured: BlkFeatured, /* … */ }
// 2) layout efectivo: default de la plantilla ∪ layout_config guardado
const { blocks } = useLayout('landing')
// 3) se montan los habilitados con componente, en el orden del layout
//    <component v-for="b in blocks" :key="b.id" :is="MAP[b.id]" :block="b" />
```

- `templates/<id>/index.js` declara `blocks.landing` = **orden canónico por
  defecto** de ese diseño (la lista es whitelist y default a la vez).
- `resolveLayout` ya fuerza `contact` al final; no duplicar esa regla.
- Un bloque sin componente en el MAP se **descarta** (el diseño no lo soporta);
  un bloque sin datos se auto-oculta en su propio `v-if`.
- Los bloques compartidos `components/store/blocks/Blk*.vue` se reutilizan
  siempre que el markup sirva; el diseño los skinea por CSS con raíz
  `[data-template='<id>']`. Los `Blk*` reciben `:block="{id, variant, props}"`.
- **Piezas firma** propias por diseño (hero, banda de pasos, grilla A/B/C/K,
  etc.) van en `views/store/<id>/<Pieza>.vue` con clases namespaceadas
  (`bq-`, `al-`, `sg-`) y estilos en `assets/store-<id>.css`.
- El chrome (header/footer/tabbar/drawer) sigue siendo compartido y se re-skinea
  desde la hoja del diseño (mismo patrón que trama/circuito).
- Mobile 320–768 sin scroll horizontal; foco visible; AA 4.5; `prefers-reduced-motion`.
- Sin estilos inline salvo variables CSS dinámicas; sin dependencias nuevas.

### Variantes mínimas por bloque (para que la IA recomponga de verdad)
Cada diseño debe soportar al menos: `hero` (su composición firma + 1 alternativa
simple), `featured` (grid/rail), `categories` (row/rail), `benefits`
(cards/lista), `faq` (accordion). Si la variante no existe, cae a la firma.

## 4. Los 3 diseños nuevos (spec resumida; manda la referencia)

### `boutique` — moda premium / deco / joyería (tier plus)
- Paleta: bg `#F8F4F5`, ink `#2A1F27`, muted `#6F5B66`, line `#E2D6DB`, surface
  `#FFFFFF`, acento `#6B2D4F`; tonos suaves `#E4D8DD`/`#D8C8CF`/`#EFE6E9`.
- Tipografía: display `Cormorant Garamond` (serif, itálica para la palabra
  acentuada), cuerpo `Jost`. h1 serif 56–68, tracking normal; labels 11–12 con
  `.18em`.
- Formas: radios 0–2, líneas hairline, foto con arco (border-radius superior
  `50%`), marco desplazado en "Sobre nosotros". Aire muy generoso.
- Portada: strip aviso; header centrado (logo serif, nav centrada); hero 50/50
  texto + imagen arco; highlights 4 en tira con líneas; categorías 3 con nombre
  serif debajo; "Recién llegado" 4 tarjetas; Sobre nosotros (marco + texto +
  stats en línea); beneficios 3 centrados con ✦; testimonio único centrado;
  galería 5; FAQ líneas; CTA banda acento con botón claro; contacto 2 col;
  footer centrado.
- El acento del dueño pinta botones/banda/subrayados (nunca el fondo completo).

### `alimentos` — gastronomía / almacén / panadería (tier base)
- Paleta: bg `#FFF9F0`, ink `#2B1D14`, muted `#5B4636`, line `#E7D8C4`, surface
  `#FFFFFF`, acento `#C8321D`, amarillo `#FCD34D`, soft `#F0E3D2`.
- Tipografía: display `DM Serif Display` (titular con palabra en acento),
  cuerpo `DM Sans`. Radios 12–20 en tarjetas, pills en chips.
- Portada: strip promo; header con logo, nav, chip "Abierto" y CTA "Hacer
  pedido"; hero partido (chips, titular serif grande, texto, CTA WhatsApp +
  ver menú, meta) + imagen con badge flotante "Hecho hoy"; chips de categorías;
  "Lo más pedido" 4 tarjetas con botón WhatsApp por producto; banda oscura
  "Cómo pedir" con 3 pasos numerados; promo + countdown en banda amarilla;
  beneficios 3; historia + stats serif; testimonios 3 con estrellas; FAQ;
  banda CTA + contacto en rojo con formulario; footer.
- Detalle firma: la tarjeta de producto lleva precio + CTA WhatsApp; badge
  Nuevo/-N%.

### `seguridad` — seguridad / bomberos / industrial (tier advanced)
- Paleta: bg `#F3F3F1`, ink `#121212`, muted `#4A4A46`, line `#D8D8D3`, surface
  `#FFFFFF`, acento `#C8200E`, amarillo `#FFC400`, dark `#121212`.
- Tipografía: display `Barlow Condensed` (mayúsculas, 700/800), cuerpo `Barlow`;
  labels 11–12 `+.14em`. Bordes 1–2 px, radios 0, stripes hazard
  (amarillo/negro) como firma.
- Portada: strip hazard; header rojo + nav condensada + buscador + CTA;
  hero partido (eyebrow, h1 condensado gigante con palabra amarilla, texto, 2
  CTA) + imagen enmarcada con badge "Nueva vente"; franja 4 checks amarillos;
  categorías 2×3 con badge de conteo; destacados 4 con precio + "Consultar por
  WhatsApp" + badges de clase; banda roja de servicios (texto + 2×2 tarjetas);
  grilla A/B/C/K "¿Qué extintor necesito?"; stats dark 4 + marcas; galería;
  testimonios con borde; FAQ; CTA amarilla; contacto; footer hazard.

## 5. Entrenamiento del motor (5 estilos de negocio)

`StoreApp/domains/stores/services/ai_design_recipes.py` + `ai_design_skins.py`:

- `PUBLIC_TEMPLATES` = los 6 ids; `TEMPLATE_LABELS` con los 6.
- `RUBROS`: sumar `seguridad` (seguridad industrial, bomberos, EPP) con
  `keywords`/`hints`; afinidades de plantilla por rubro:
  gastronomia→alimentos; indumentaria→trama,boutique; belleza→boutique,trama;
  tecnologia→circuito; construccion→seguridad,raiz; seguridad→seguridad;
  comercio→raiz,alimentos; arte→boutique,trama; etc.
- `RUBRO_STYLES`: cada rubro sigue declarando **3 ternas firma** distintas
  (plantilla+piel+par) usando las plantillas permitidas; los 3 diseños nuevos
  deben aparecer en la matriz de su rubro.
- `TEMPLATE_TONE_AFFINITY` / `TEMPLATE_GOAL_AFFINITY` / `STYLE_PRESET_TEMPLATES`:
  agregar los 3 ids (boutique→`luxury`, alimentos→`craft`, seguridad→`bold`).
- Los estilos (8 familias) NO cambian; el mapeo diseño→estilo es el de arriba.
- `has_ai_design` (Premium/trial) habilita la IA; en Premium los 6 diseños están
  permitidos. Básico: raiz+alimentos; Estándar: +trama+boutique; Premium: +circuito+seguridad.
- El motor sigue siendo determinista/offline (sin IA externa) y sus propuestas
  deben componer `layout_config` con orden/variantes distintas por cliente.

## 6. Registro frontend (espejos obligatorios)

1. `frontend/src/api/stores.api.js`: `STORE_TEMPLATES` (6), `STORE_TEMPLATE_FAMILIES`
   (general, alimentos, indumentaria, boutique, tecnología, seguridad),
   `STORE_TEMPLATE_RETIRED_MAP` sin `boutique`, `STORE_FONTS` (+3), gating por tier.
2. `frontend/src/templates/index.js`: imports + `TEMPLATE_DEFS`.
3. `frontend/src/templates/_shared.js`: loaders de las 4 superficies de cada id.
4. `frontend/src/views/StorePublicLayout.vue`: `DESIGN_SKIN_FREE` + `TEMPLATE_CSS`.
5. `frontend/src/components/design/DesignLookTab.vue` + `assets/template-thumbs.css`:
   miniaturas/etiquetas de los 6.
6. `frontend/src/views/design/AiDesignView.vue`: lista `RUBROS` con `seguridad`.
7. Migración backend de `TEMPLATE_CHOICES` (choices + default sin cambios).

## 7. Reparto de archivos (no pisar fuera de alcance)

| Agente | Escribe |
|---|---|
| backend/engine | `StoreApp/domains/stores/{models,services,serializers,views,tests*,migrations}` |
| frontend foundation | `frontend/src/{api,templates,views/StorePublicLayout.vue,views/store/{raiz,trama,circuito}/InicioView.vue,components/design,assets/template-thumbs.css,views/design/AiDesignView.vue}` |
| boutique | `frontend/src/views/store/boutique/**`, `frontend/src/assets/store-boutique.css`, `frontend/src/templates/boutique/index.js` |
| alimentos | `frontend/src/views/store/alimentos/**`, `frontend/src/assets/store-alimentos.css`, `frontend/src/templates/alimentos/index.js` |
| seguridad | `frontend/src/views/store/seguridad/**`, `frontend/src/assets/store-seguridad.css`, `frontend/src/templates/seguridad/index.js` |

Reglas: no commits (los hace el Lead), no dependencias nuevas, no tocar otras
carpetas de diseño, no reescribir CSS compartido salvo el propio.

## 8. Verificación

```powershell
# frontend (desde frontend/)
npx vite build
# backend
venv\Scripts\python.exe manage.py test StoreApp.domains.stores
# capturas (con backend+frontend levantados y una tienda seed)
venv\Scripts\python.exe qa_shots.py   # o el script QA que corresponda
```

Criterios: build verde; tests verdes; 6 diseños se pueden elegir y publicar;
la portada respeta el orden/on-off de `layout_config`; sin regresiones en
raiz/trama/circuito; fidelidad visual contra las capturas (1360 y 390).
