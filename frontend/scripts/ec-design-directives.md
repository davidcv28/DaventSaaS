# Directivas de composición por diseño

Una sola regla manda: **dos diseños no pueden compartir la misma estructura**.
La columna "Auth" describe la composición de `/ingresar`; "Cuenta" la de
`/cuenta` (shell + secciones). Los colores/fuentes salen del propio diseño
(`:root` del source HTML); acá van solo la idea y los motivos.

## A1 — editorial / galería / retail serio
| Diseño | Tienda QA | Auth | Cuenta |
|---|---|---|---|
| `portico` | `vertice` | Portada de museo: panel de marca a sangre con arco de medio punto, índice 01–05 y sello; formulario sobre papel con doble filete. Nada de tarjeta redondeada. | Sala de catálogo: sidebar como lápida de piedra con numerales, paneles con doble filete, mucho aire, sin sombras. |
| `esencial` | `vivero-esencia` | Hoja centrada: sin tarjeta ni sombra, filetes horizontales, formulario sobre el papel, marca como cabecera con regla y bajada. | Ledger: filas separadas por hairlines, sin cards; sidebar = índice de líneas con números; verde bosque solo en acciones. |
| `showroom` | `nomada` | Tres bandas: cabecera tipográfica enorme en versalitas, formulario en columna izquierda, ficha técnica del negocio a la derecha (borde 1px, radio 0, sin sombra, sin animación). | Índice de catálogo: tabs cuadradas, tablas con filetes 1px, mono para metadatos, cero radio/animación. |
| `umbral` | `limen` | Umbral: hendidura de luz vertical, panel de marca como fachada con arco, formulario al otro lado del “marco”. | Índice de ambientes: sidebar con arcos numerados, fichas técnicas en mono, líneas de plano de fondo. |

## A2 — retail / comercio
| Diseño | Tienda QA | Auth | Cuenta |
|---|---|---|---|
| `mercado` | `bazar-artemisa` | Góndola: banda amarilla superior con “precio” de la cuenta, tarjeta con etiqueta de oferta y borde troquelado. | Mesa de operaciones: grilla densa, badges verdes de estado, números tabulares, sidebar con conteos. |
| `autoservicio` | `el-trebol` | Ticket: hoja con muescas (mask radial), encabezado “caja”, líneas punteadas, mono para importes. | Lista de compra/ledger: filas de ticket, subtotales, sidebar como índice de departamentos. |
| `calzado` | `zancada` | Billboard a sangre: titular fino gigante + dots, panel de marca como collage de paneles rojo/negro. | Ficha de talla: chips de estado, tarjetas con esquina marcada, sidebar como riel de producto. |
| `topmodern` | `voga` | Hero tipográfico ultra-bold: nombre del diseño a 64–96px a la izquierda, formulario minimal a la derecha sin tarjeta. | Grilla modular con stats, secciones con títulos en mayúscula tracking ancho, tabs como botones rectangulares. |

## A3 — energía / industria / consola
| Diseño | Tienda QA | Auth | Cuenta |
|---|---|---|---|
| `gimnasio` | `forja` | Banda diagonal lima/negro, titular condensado 800, formulario sobre panel claro con esquina cortada. | Panel de socio: header oscuro con avatar y stats, secciones como circuitos, acento lima. |
| `brigada` | `vigia` | Placa de verificación: franjas de riesgo (repeating-linear-gradient), código de barras, tipografía condensada, sello. | Parte de novedades: formulario oficial, sellos, tablas de turnos, sidebar como pizarra. |
| `guardia` | `centinela` | Credencial de acceso: tarjeta oscura con scanlines, foto/monograma, mono, rojo señal. | Consola de turnos: tablas mono, estados con glifo+texto, sidebar como barra de guardia. |
| `silicio` | `nucleo` | Boot de sistema: fondo claro técnico con prompt `>`, líneas mono, verde ácido; formulario como entrada de comandos. | Consola con tablas de specs, sidebar como árbol de sistema, foco con subrayado ácido. |
| `movimiento` | `mv-qa` | Hoja luminosa: numeración 01/02/03, filetes, titular editorial; formulario con aire. | Índice de secciones con números grandes, secciones como capítulos, acento señal. |

## A4 — costura / moda de autor
| Diseño | Tienda QA | Auth | Cuenta |
|---|---|---|---|
| `sastreria` | `telar` | Orden de confección: líneas de medida, marcas de corte, Fraunces; formulario como ficha con campos alineados a la regla. | Fichero: sidebar con pestañas, filas tipo fichero, numeración de pliegos. |
| `atelier-noir` | `atelier-bruma` | Hoja de corte: cinta métrica (repeating-linear-gradient), sello giratorio, papel hueso, marcas de tijera. | Dossier: pliegos numerados, separadores, sidebar como lomo con costura. |
| `modista` | `atelier-serena` | Patrón de costura: líneas de seda, sello de bobina, papel cálido; formulario con etiquetas cosidas. | Hoja de medidas: tabla con filas alternas, fichas de prenda, sidebar como carrete. |
| `indumentaria` | `atelier-luma` | Lookbook: spread con rail COLECCIÓN vertical, etiqueta colgante, numeración LOOK. | Índice de looks: filas LOOK 01…, sidebar como rail de colección. |

## A5 — revista / viaje
| Diseño | Tienda QA | Auth | Cuenta |
|---|---|---|---|
| `moda` | `maison-vela` | Portada de revista: cabecera con running head, cintas, sello, titular DM Serif; formulario como sumario. | Club: tarjeta de membresía + índice editorial; secciones como páginas de revista. |
| `impacto` | `piel-pulso` | Revista suiza: retícula con celdas, numeración 01/02, Anton, reglas de 2px, acento señal. | Pliego de diario: columnas, titulares Anton, cifras grandes, sidebar como índice de pliego. |
| `viajero` | `viajero-andino` | Ticket de viaje: ficha con talón perforado, papel arena, tinta náutica, código de reserva. | Bitácora: sellos, líneas de ruta, sidebar como itinerario. |
| `ruta` | `ruta-sur` | Postal: marco blanco, sello, verde pino y ámbar; formulario como reverso de postal. | Itinerario: línea punteada, paradas numeradas, sidebar como mapa. |

## A6 — premium / bodega / noche / archivo
| Diseño | Tienda QA | Auth | Cuenta |
|---|---|---|---|
| `aurum` | `casa-aurea` | Invitación grabada: simetría centrada, filetes dorados, monograma, serif; sin tarjeta. | Folio de socio: placa con filete dorado, secciones como hojas de libro. |
| `olivium` | `olivium-qa` | Etiqueta de almazara: óvalo/filete, verde oliva, DM Serif; formulario como ficha de cata. | Libro de bodega: filas de inventario, sellos de cosecha, sidebar como índice de añadas. |
| `neon` | `nocturna` | Letrero nocturno: panel oscuro, glow contenido, scanlines, lima/cian; formulario como teclado de local. | Dashboard nocturno: tarjetas oscuras, glow solo en foco/estado, sidebar como menú de local. |
| `expediente` | `bufete-vega` | Carpeta manila: pestaña, sello CONFIDENCIAL, mono, formulario como carátula. | Dossier: separadores F-1xx, tablas, sidebar como lomo de carpeta. |

## Dueño (dashboard de la plataforma) — una sola identidad
No es un diseño de tienda: es la herramienta de trabajo DAVENT. Identidad
"mesa de control editorial": papel neutro, tinta, un acento teal/indigo
contenido, mono para datos y navegación, serif/sans para títulos, densidad
media, cero glow. No puede parecerse a ninguna piel de tienda.
