# Entrenamiento de estilos — "Diseñar con IA" (motor v5)

Este documento es el **prompt canónico** que define los estilos del motor de
diseño automático y el registro de cómo se implementaron. Si cambia el
entrenamiento, se cambian acá y en `ai_design_skins.py` en el mismo commit.

## Prompt

```
ACTÚA COMO: designer lead del motor "Diseñar con IA" de DAVENT.
TAREA: incorporar 8 familias de estilos como presupuestos visuales
composibles, SIN romper ningún invariante del proyecto.

CONTEXTO OBLIGATORIO DEL SISTEMA (respetar al pie de la letra)
- El motor NO llama a ninguna IA externa: es determinista y offline. La
  entrada es store + rubro + tono (calido|serio|moderno|audaz) + objetivos
  + semilla; la salida son 2-3 propuestas de JSON reproducibles byte a byte.
- Una "piel" (skin) NO es una plantilla: es un presupuesto de piel (paleta +
  containers + buttons + background + motion + typography.pair + layout)
  que se COMPONE con la plantilla y el rubro.
- Catálogo cerrado y validado server-side. Nada inventado puede viajar:
  skin.id contra SKIN_IDS, plantilla contra allowed_templates_of, layout
  contra clean_layout_config, theme contra clean_site_theme.
- Toda web resultante debe cumplir: contraste AA (4.5:1), TplProductCard
  uniforme en el catálogo, landing = negocio + ofertas, cero emojis,
  mobile 320-768 sin scroll horizontal, prefers-reduced-motion.
- Si un estilo pide algo imposible se degrada al equivalente válido más
  cercano y se registra en el `notes` de la propuesta.

POR CADA ESTILO: enética (1 frase), palette (8 hex + variante oscura),
containers, buttons, background, motion, typography.pair, layout, rubros[],
tones[], plantillas compatibles, blocks.landing recomendado, catalog
(grid + filters), anti-ejemplos.
```

## Las 8 familias y su mapeo real

| Estilo (`style`) | Label | Pieles | Origen |
|---|---|---|---|
| `minimal` | Minimalistas y limpios | `minimal-*`, `swiss-*`, `soft-*`, `mono-*` | Swiss Grid, Whitespace Editorial, Mono Clean, Soft Minimal → nuevas `swiss` |
| `editorial` | Editoriales y de revista | `editorial-*`, `magazine-*`, `prestige-*` | Magazine Layout, Lookbook, Type-Driven, Serif Elegante → nueva `magazine` |
| `bold` | Atrevidos y expresivos | `brutal-*`, `pop-*`, `kinetic-*`, `playful-*` | Neobrutalismo, Brutalismo web, Maximalismo, Memphis, Bold Pop, Cartel → nueva `pop` |
| `tech` | Modernos y tecnológicos | `tech-*`, `glass-*`, `gradient-*`, `aurora-*`, `corporate-*` | Glassmorphism, Bento, Dark Mode Tech, Gradientes Aurora, Neumorfismo, Futurismo SaaS → nueva `aurora` |
| `craft` | Cálidos y artesanales | `organic-*`, `warm-*`, `paper-*`, `craft-*` | Orgánico, Boho, Rústico Moderno, Tierra y Papel, Handcrafted → nueva `craft` |
| `retro` | Retro y nostálgicos | `retro-*`, `neon-*`, `nostalgia-*`, `cinematic-*` | 70s, Y2K, Vaporwave, Art Déco, Mid-Century, Vintage Print → nueva `nostalgia` |
| `luxury` | Lujo y premium | `luxury-*`, `prestige-*`, `mono-*` | Luxury Dark & Gold, Boutique, Monocromo Premium, Galería → nueva `prestige` |
| `catalog` | Ideales para catálogos | `showcase-*` + las que resuelven vitrina | Grid limpio, Catálogo Editorial, Spec Sheet, Showroom, Temporadas, Mosaico → nueva `showcase` |

## Reglas de selección (lo que hace que el entrenamiento se note)

1. `_style_order` pone primero los estilos afines al rubro/tono y los
   **pedidos** por el dueño (`styles[]`); la semilla rota solo los no afines.
2. `_style_candidates` arma tres bloques: matriz "firma" del rubro,
   plantillas permitidas con piel rotada, y **cobertura de estilos** (una
   plantilla libre por estilo, con base 40 si el estilo fue pedido).
3. `_select_styles` elige en tres pases: primero **estilo** (dos propuestas
   nunca comparten aire), después piel+par, y al final solo plantilla.
   La plantilla NUNCA se repite.
4. La rotación de semilla de la cabeza se suspende si hay un estilo pedido
   adelante: lo pedido se ve, "otra propuesta" no se lo come.
5. El clon de respaldo (estilo sin plantilla libre) solo usa plantillas de
   la whitelist del plan — nunca `ai_lumen` en un plan Básico.

## Invariantes verificados

- `test_skin_catalog_is_closed_and_composed`: 26 familias, 8 estilos con pieles.
- `test_skin_palettes_pass_aa`: contraste AA en toda paleta.
- `test_proposals_declare_their_design_style`: estilos distintos por generación.
- `test_requested_styles_are_prioritized_but_never_imposed`: pedido respetado,
  inventado ignorado. Verificado a 1200 combinaciones rubro × seed: 0 fallos.
- `test_template_outside_plan_never_returned`: la whitelist del plan manda.
