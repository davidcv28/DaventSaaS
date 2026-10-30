// Familia de iconos por estilo de diseño.
// Cada estilo del catálogo (`DesignStyle`) define su familia: un grosor de
// trazo propio y un mapa de alias que cambia los iconos semánticos de la web
// pública (flechas, checks, carrito, pin, estrella…) por otro icono del set.
// El alias apunta a nombres ya existentes en AppIcon: no se agregan SVG.
//
// La familia la resuelve la web pública a partir del estilo elegido
// (`site_theme.style.id`) y, si la tienda no eligió estilo, de su plantilla.
// AppIcon la consume por provide/inject ('storeIconFamily'): las ~300
// llamadas existentes no cambian y sin familia el icono queda igual que hoy.

export const ICON_FAMILIES = {
  // Revistas y papel: trazo fino, flechas de esquina, menú como índice.
  editorial: {
    stroke: 1.3,
    alias: {
      'arrow-right': 'arrow-up-right',
      'chevron-right': 'arrow-up-right',
      'menu': 'list-ordered',
      'shield-check': 'badge-check',
      'clock': 'timer',
      'store': 'building-2',
      'filter': 'filter',
      'sliders': 'filter'
    }
  },
  // Vidrio y nocturnos: trazo medio, esquinas ascendentes.
  glass: {
    stroke: 1.45,
    alias: {
      'arrow-right': 'arrow-up-right',
      'chevron-right': 'arrow-up-right',
      'store': 'layout-grid',
      'filter': 'sliders'
    }
  },
  // Bento/corporativo: módulos, menú como filas.
  bento: {
    stroke: 1.8,
    alias: {
      'check': 'circle-check',
      'store': 'layout-grid',
      'menu': 'rows-3',
      'info': 'circle-help',
      'filter': 'sliders',
      'layout-grid': 'columns-2'
    }
  },
  // Neo-brutalismo: trazo grueso, todo recto.
  brutal: {
    stroke: 2.6,
    alias: {
      'sparkles': 'zap',
      'circle-alert': 'triangle-alert',
      'sliders': 'filter'
    }
  },
  // Pastel, belleza y kids: redondeado y amable.
  soft: {
    stroke: 1.95,
    alias: {
      'check': 'circle-check',
      'package': 'gift',
      'shield-check': 'badge-check',
      'info': 'circle-help',
      'sparkles': 'heart'
    }
  },
  // Neón, consola y cobalto: trazo fino, chevrons, terminal.
  tech: {
    stroke: 1.45,
    alias: {
      'arrow-right': 'chevron-right',
      'store': 'terminal',
      'clock': 'timer',
      'sliders': 'filter',
      'circle-alert': 'triangle-alert'
    }
  },
  // Artesanal y gastronomía: trazo medio, sellos y oficio.
  craft: {
    stroke: 1.6,
    alias: {
      'shield-check': 'badge-check',
      'sparkles': 'flame',
      'filter': 'sliders'
    }
  },
  // Monocromo y suizo: trazo mínimo, flechas de esquina, índice.
  mono: {
    stroke: 1.05,
    alias: {
      'arrow-right': 'arrow-up-right',
      'chevron-right': 'arrow-up-right',
      'menu': 'list-ordered',
      'store': 'building-2',
      'sparkles': 'hexagon',
      'sliders': 'filter'
    }
  },
  // Retail vibrante y aurora: trazo grueso, signos de oferta.
  vibrant: {
    stroke: 2.15,
    alias: {
      'check': 'circle-check',
      'tag': 'percent',
      'package': 'gift',
      'shield-check': 'badge-check',
      'circle-alert': 'triangle-alert',
      'filter': 'sliders'
    }
  },
  // Lujo y atelier: trazo fino, joya y corona.
  luxury: {
    stroke: 1.2,
    alias: {
      'sparkles': 'diamond',
      'gem': 'diamond',
      'store': 'gem',
      'filter': 'filter'
    }
  }
}

// Estilo del catálogo -> familia.
export const STYLE_FAMILY = {
  'editorial-minima': 'editorial',
  'vidrio-nocturno': 'glass',
  'bento': 'bento',
  'neo-brutalista': 'brutal',
  'lujo-serif': 'luxury',
  'pastel-suave': 'soft',
  'neon-tech': 'tech',
  'terracota': 'craft',
  'monocromo': 'mono',
  'retail-vibrante': 'vibrant',
  'aurora-degradada': 'vibrant',
  'papel-riso': 'craft',
  'corporativo': 'bento',
  'gourmet-calido': 'craft',
  'belleza-rosa': 'luxury',
  'kids-ludico': 'soft',
  'urbano-sticker': 'vibrant',
  'consola-retro': 'tech',
  'denim-urbano': 'editorial',
  'atelier-moda': 'luxury',
  'suizo-editorial': 'mono',
  'cobalto-nocturno': 'glass',
  'daven-indumentaria': 'editorial'
}

// Plantilla -> familia por defecto (tienda sin estilo elegido).
export const TEMPLATE_FAMILY = {
  raiz: 'editorial',
  trama: 'editorial',
  indumentaria: 'editorial',
  boutique: 'luxury',
  clasico: 'craft',
  alimentos: 'craft',
  circuito: 'tech',
  seguridad: 'brutal'
}

export function familyOf({ styleId = '', template = '' } = {}) {
  return STYLE_FAMILY[styleId] || TEMPLATE_FAMILY[template] || 'editorial'
}

export function familyStroke(family) {
  return ICON_FAMILIES[family]?.stroke ?? null
}

// Nombre real del icono dentro de la familia (sin familia: el mismo).
export function familyIcon(name, family) {
  const alias = ICON_FAMILIES[family]?.alias
  return (alias && alias[name]) || name
}
