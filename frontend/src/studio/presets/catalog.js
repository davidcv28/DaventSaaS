// Catálogo de presets premium del Studio — "un look completo en un click".
// Cada preset combina: siteTheme del contrato + plantilla existente +
// layout por superficie (misma forma que customization.layout_config) +
// tier del plan que lo cubre por completo.
//
// El `theme` es PARCIAL: resolveSiteTheme lo mergea sobre los defaults
// (identidad neutra). Los valores usan solo enums/hex/fontes del catálogo
// cerrado — el backend (clean_site_theme) valida el mismo contrato y
// descarta en silencio lo que el plan no cubre.
//
// Layout: spec compacto por superficie — `on` = bloques activos en orden,
// `var` = variantes del catálogo de blocks.js; el resto queda apagado al
// final. buildLayout lo expande contra la whitelist real de la plantilla
// (defaultLayout), así un preset jamás envía ids no soportados.
import { defaultLayout } from '../../templates/index.js'
import { blockSpec } from '../../templates/blocks.js'
import { STORE_FONTS, STORE_TEMPLATES } from '../../api/stores.api.js'
import { deriveAccent } from '../../utils/colorTools.js'
import { STUDIO_SURFACES, resolveStudioPreset, styleColorsBlock } from '../contract.js'

// ---------------------------------------------------------------------------
// Spec compacto -> layout_config del contrato.
// ---------------------------------------------------------------------------
export function buildLayout(templateId, spec = {}) {
  const out = {}
  for (const surface of STUDIO_SURFACES) {
    const base = defaultLayout(templateId, surface)
    const s = spec[surface] || {}
    const byId = new Map(base.map((b) => [b.id, b]))
    const ordered = []
    const seen = new Set()
    for (const id of Array.isArray(s.on) ? s.on : base.map((b) => b.id)) {
      const b = byId.get(id)
      if (b && !seen.has(id)) { seen.add(id); ordered.push(b) }
    }
    for (const b of base) if (!seen.has(b.id)) ordered.push(b)
    const off = new Set(s.off || [])
    const variants = s.var || {}
    const listed = Array.isArray(s.on)
    out[surface] = {
      blocks: ordered.map((b, i) => {
        const meta = blockSpec(surface, b.id)
        const enabled = meta?.locked ? true : (listed ? seen.has(b.id) : true) && !off.has(b.id)
        const block = { id: b.id, enabled, order: i }
        const v = variants[b.id]
        if (v && meta?.variants?.[v]) block.variant = v
        return block
      })
    }
  }
  return out
}

// Paleta coherente: accent manda, primary lo espeja y secondary es su tinta
// derivada — la misma convención que setPalette del panel (sin ella el
// watcher form->theme reescribe secondary al tocar accent_custom).
function pal(accent, over = {}) {
  return {
    primary: accent,
    secondary: deriveAccent(accent).ink,
    accent,
    bg: '#f4f6fb', surface: '#ffffff', text: '#0f172a', muted: '#5b6678',
    border: '#e2e6f0', success: '#059669', danger: '#dc2626',
    ...over
  }
}

function theme(t) {
  const palette = pal(t.accent, t.pal)
  return {
    palette,
    // Juego de colores del estilo (fuentes + contenedores) en claro y
    // oscuro, derivado del palette y con AA garantizado por el contrato.
    styleColors: styleColorsBlock(palette),
    containers: t.containers || {},
    typography: {
      heading: t.heading || t.font || 'inter',
      body: t.body || t.font || 'inter',
      scale: t.scale || 'balanced',
      weightHeading: t.weight || 800,
      letterSpacing: t.tracking || '-0.02em'
    },
    buttons: t.buttons || {},
    // Fondo estándar del look: sólido con el color de página de la paleta
    // (los presets que quieren malla/patrón/degradado lo pisan).
    background: t.background || { type: 'solid', value: null, overlay: 'none' },
    motion: t.motion || {},
    mobile: t.mobile || {}
  }
}

// ---------------------------------------------------------------------------
// Los 18 looks. `style` = dirección visual (filtro "Estilo"); `rubros` =
// categorías de RUBRO_LABELS donde se recomienda; `pageTheme` =
// modo claro/oscuro que pide (se aplica a la página y al visor).
// ---------------------------------------------------------------------------
const PRESETS = [
  {
    id: 'editorial-minima', name: 'Editorial mínima', style: 'Minimal editorial',
    desc: 'Papel, tinta y aire: la foto y la palabra mandan.',
    tier: 'advanced', template: 'minimal', pageTheme: 'light',
    rubros: ['moda', 'lifestyle', 'services', 'general'],
    theme: theme({
      accent: '#1c1917',
      pal: { bg: '#fafaf9', surface: '#ffffff', text: '#1c1917', muted: '#78716c', border: '#e7e5e4' },
      containers: { radius: 'none', shadow: 'none', border: 'thin', density: 'spacious', surface: 'outlined' },
      heading: 'fraunces', body: 'work-sans', scale: 'editorial', weight: 500, tracking: '-0.02em',
      buttons: { shape: 'square', style: 'outline', size: 'md' },
      motion: { reveal: 'fade', hover: 'none', intensity: 'subtle' },
      mobile: { cardStyle: 'standard', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'featured', 'about', 'gallery', 'testimonials', 'faq', 'contact'], var: { hero: 'compact' } },
      catalog: { on: ['note', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'vidrio-nocturno', name: 'Vidrio nocturno', style: 'Glass oscuro',
    desc: 'Noche profunda con placas de vidrio esmerilado.',
    tier: 'advanced', template: 'cobre', pageTheme: 'dark',
    rubros: ['tech', 'gamer', 'general'],
    theme: theme({
      accent: '#38bdf8',
      pal: { bg: '#070b16', surface: '#0d1424', text: '#e6ecf7', muted: '#8b96ad', border: '#1c2a44' },
      containers: { radius: 'xl', shadow: 'deep', border: 'thin', density: 'comfortable', surface: 'glass' },
      heading: 'sora', body: 'space-grotesk', weight: 700, tracking: '-0.02em',
      buttons: { shape: 'pill', style: 'gradient', size: 'md' },
      background: { type: 'mesh', value: 'radial-gradient(60% 50% at 18% 0%, rgba(56,189,248,.28), transparent 70%), radial-gradient(55% 45% at 85% 8%, rgba(139,92,246,.26), transparent 72%), #070b16' },
      motion: { reveal: 'rise', hover: 'glow', intensity: 'medium' },
      mobile: { nav: 'bottom', cardStyle: 'overlay', stickyCta: true, heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'stats', 'featured', 'benefits', 'offers', 'gallery', 'testimonials', 'cta', 'contact'], var: { stats: 'cards' } },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'bento', name: 'Bento', style: 'Bento',
    desc: 'Tarjetas redondas que ordenan todo en módulos.',
    tier: 'plus', template: 'vitrina', pageTheme: 'light',
    rubros: ['tech', 'general'],
    theme: theme({
      accent: '#0ea5e9',
      pal: { bg: '#eef2f7', surface: '#ffffff', text: '#0f172a', muted: '#64748b', border: '#e2e8f0' },
      containers: { radius: 'xl', shadow: 'soft', border: 'none', density: 'compact', surface: 'elevated' },
      heading: 'space-grotesk', body: 'manrope', scale: 'balanced', weight: 700, tracking: '-0.02em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'subtle' },
      mobile: { nav: 'bottom', gridCols: 2, cardStyle: 'compact', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'stats', 'featured', 'benefits', 'offers', 'gallery', 'faq', 'cta', 'contact'], var: { hero: 'compact', stats: 'cards' } },
      catalog: { on: ['filters', 'sort', 'grid', 'promo'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'faq'] }
    }
  },
  {
    id: 'neo-brutalista', name: 'Neo-brutal', style: 'Neo-brutalista',
    desc: 'Bordes duros, tinta plana y tipografía que grita.',
    tier: 'base', template: 'duo', pageTheme: 'light',
    rubros: ['moda', 'gamer', 'lifestyle'],
    theme: theme({
      accent: '#e11d48',
      pal: { bg: '#f4f1ea', surface: '#ffffff', text: '#0b0b0b', muted: '#55504a', border: '#0b0b0b' },
      containers: { radius: 'none', shadow: 'none', border: 'bold', density: 'compact', surface: 'outlined' },
      heading: 'archivo-black', body: 'archivo', scale: 'editorial', weight: 900, tracking: '-0.03em',
      buttons: { shape: 'square', style: 'solid', size: 'sm' },
      motion: { reveal: 'none', hover: 'none', intensity: 'subtle' },
      mobile: { cardStyle: 'compact', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'announcements', 'highlights', 'featured', 'stats', 'benefits', 'offers', 'brands', 'gallery', 'faq', 'cta', 'contact'], var: { announcements: 'static', stats: 'band' } },
      catalog: { on: ['note', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'lujo-serif', name: 'Lujo serif', style: 'Luxury serif',
    desc: 'Noche de espresso, dorado y grabados de autor.',
    tier: 'advanced', template: 'cobre', pageTheme: 'dark',
    rubros: ['belleza', 'lifestyle', 'food'],
    theme: theme({
      accent: '#c9a24b',
      pal: { bg: '#0e0b08', surface: '#171310', text: '#ede4d3', muted: '#a89a84', border: '#2e2620' },
      containers: { radius: 'sm', shadow: 'medium', border: 'thin', density: 'spacious', surface: 'outlined' },
      heading: 'cinzel', body: 'lora', scale: 'editorial', weight: 500, tracking: '0.03em',
      buttons: { shape: 'square', style: 'outline', size: 'md' },
      motion: { reveal: 'fade', hover: 'glow', intensity: 'subtle' },
      mobile: { cardStyle: 'standard', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'featured', 'about', 'stats', 'gallery', 'testimonials', 'faq', 'contact'], var: { stats: 'band' } },
      catalog: { on: ['note', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'pastel-suave', name: 'Pastel suave', style: 'Soft pastel',
    desc: 'Lavanda, rosa y aire: calma que vende.',
    tier: 'plus', template: 'calma', pageTheme: 'light',
    rubros: ['belleza', 'hogar', 'services'],
    theme: theme({
      accent: '#d16ba5',
      pal: { bg: '#f7f3fb', surface: '#ffffff', text: '#54475e', muted: '#8b7f99', border: '#e9dfeb' },
      containers: { radius: 'xl', shadow: 'soft', border: 'none', density: 'spacious', surface: 'elevated' },
      heading: 'lora', body: 'nunito', weight: 600, tracking: '0em',
      buttons: { shape: 'pill', style: 'solid', size: 'md' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'subtle' },
      mobile: { nav: 'bottom', cardStyle: 'standard', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'featured', 'about', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'] },
      catalog: { on: ['filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'neon-tech', name: 'Neón tech', style: 'Neón tech',
    desc: 'Verde fósforo sobre negro: energía de arena.',
    tier: 'plus', template: 'vitrina', pageTheme: 'dark',
    rubros: ['gamer', 'tech'],
    theme: theme({
      accent: '#00e67a',
      pal: { bg: '#05060a', surface: '#0b0f14', text: '#e8fff2', muted: '#7d8a8f', border: '#1d2a24' },
      containers: { radius: 'sm', shadow: 'none', border: 'thin', density: 'compact', surface: 'outlined' },
      heading: 'orbitron', body: 'space-grotesk', scale: 'compact', weight: 700, tracking: '0.02em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      background: { type: 'mesh', value: 'radial-gradient(55% 40% at 80% 0%, rgba(0,230,122,.18), transparent 70%), #05060a' },
      motion: { reveal: 'rise', hover: 'glow', intensity: 'medium' },
      mobile: { nav: 'bottom', cardStyle: 'compact', stickyCta: true, heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'announcements', 'stats', 'featured', 'offers', 'brands', 'countdown', 'gallery', 'faq', 'cta', 'contact'], var: { announcements: 'marquee', stats: 'cards' } },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'form', 'faq'] }
    }
  },
  {
    id: 'terracota', name: 'Terracota', style: 'Terracota artesanal',
    desc: 'Barro, papel crudo y serif cálida de taller.',
    tier: 'advanced', template: 'minimal', pageTheme: 'light',
    rubros: ['hogar', 'food', 'general'],
    theme: theme({
      accent: '#b7512e',
      pal: { bg: '#f5ede3', surface: '#fffaf2', text: '#3a2c22', muted: '#8a7461', border: '#e3d5c2' },
      containers: { radius: 'md', shadow: 'soft', border: 'thin', density: 'comfortable', surface: 'elevated' },
      heading: 'fraunces', body: 'nunito', weight: 600, tracking: '-0.01em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'subtle' },
      mobile: { cardStyle: 'standard', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'about', 'featured', 'stats', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'], var: { stats: 'band' } },
      catalog: { on: ['note', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'monocromo', name: 'Monocromo', style: 'Monocromo fotográfico',
    desc: 'Blanco y negro puro: la foto hace todo el trabajo.',
    tier: 'advanced', template: 'minimal', pageTheme: 'light',
    rubros: ['moda', 'lifestyle', 'general'],
    theme: theme({
      accent: '#18181b',
      pal: { bg: '#f4f4f5', surface: '#ffffff', text: '#18181b', muted: '#71717a', border: '#d4d4d8' },
      containers: { radius: 'none', shadow: 'none', border: 'thin', density: 'spacious', surface: 'flat' },
      heading: 'playfair-display', body: 'inter', scale: 'editorial', weight: 500, tracking: '-0.02em',
      buttons: { shape: 'square', style: 'solid', size: 'md' },
      motion: { reveal: 'fade', hover: 'none', intensity: 'subtle' },
      mobile: { cardStyle: 'overlay', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'featured', 'about', 'gallery', 'testimonials', 'faq', 'contact'] },
      catalog: { on: ['sort', 'grid'] },
      services: { on: ['hero', 'picker', 'form', 'faq'] }
    }
  },
  {
    id: 'retail-vibrante', name: 'Retail vibrante', style: 'Retail vibrante',
    desc: 'Góndola cargada: oferta primero, compra rápida.',
    tier: 'advanced', template: 'cobre', pageTheme: 'light',
    rubros: ['ofertas', 'general'],
    theme: theme({
      accent: '#dc2626',
      pal: { bg: '#fef9ec', surface: '#ffffff', text: '#1c1917', muted: '#78716c', border: '#e7e5e4' },
      containers: { radius: 'md', shadow: 'medium', border: 'none', density: 'compact', surface: 'elevated' },
      heading: 'archivo', body: 'dm-sans', scale: 'compact', weight: 800, tracking: '-0.02em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'medium' },
      mobile: { nav: 'bottom', gridCols: 2, cardStyle: 'compact', stickyCta: true, heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'announcements', 'highlights', 'offers', 'featured', 'categories', 'countdown', 'benefits', 'brands', 'gallery', 'faq', 'cta', 'contact'], var: { announcements: 'marquee' } },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'aurora-degradada', name: 'Aurora', style: 'Gradiente aurora',
    desc: 'Cortinas de color suave sobre papel claro.',
    tier: 'base', template: 'duo', pageTheme: 'light',
    rubros: ['tech', 'general', 'belleza'],
    theme: theme({
      accent: '#7c3aed',
      pal: { bg: '#f3f5fd', surface: '#ffffff', text: '#1e1b4b', muted: '#6b7280', border: '#e3e6f5' },
      containers: { radius: 'xl', shadow: 'soft', border: 'none', density: 'comfortable', surface: 'elevated' },
      heading: 'sora', body: 'dm-sans', weight: 700, tracking: '-0.02em',
      buttons: { shape: 'pill', style: 'gradient', size: 'md' },
      background: { type: 'mesh', value: 'radial-gradient(60% 45% at 15% 0%, rgba(124,58,237,.16), transparent 70%), radial-gradient(55% 45% at 88% 12%, rgba(34,211,238,.18), transparent 72%), radial-gradient(45% 40% at 55% 0%, rgba(244,114,182,.12), transparent 70%), #f3f5fd' },
      motion: { reveal: 'rise', hover: 'glow', intensity: 'subtle' },
      mobile: { cardStyle: 'overlay', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'featured', 'benefits', 'offers', 'gallery', 'testimonials', 'cta', 'contact'] },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'papel-riso', name: 'Papel riso', style: 'Papel/Riso',
    desc: 'Risografía: crema punteado y tintas que se solapan.',
    tier: 'base', template: 'duo', pageTheme: 'light',
    rubros: ['hogar', 'food', 'general'],
    theme: theme({
      accent: '#3550f5',
      pal: { bg: '#fff5e6', surface: '#fffdf8', text: '#1e1a33', muted: '#6e6883', border: '#1e1a33' },
      containers: { radius: 'md', shadow: 'none', border: 'bold', density: 'comfortable', surface: 'outlined' },
      heading: 'bricolage-grotesque', body: 'figtree', weight: 800, tracking: '-0.02em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      background: { type: 'pattern', value: 'repeating-linear-gradient(45deg, rgba(30,26,51,.05) 0 2px, transparent 2px 9px), #fff5e6' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'medium' },
      mobile: { cardStyle: 'standard', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'featured', 'stats', 'benefits', 'offers', 'about', 'gallery', 'testimonials', 'faq', 'cta', 'contact'], var: { stats: 'cards' } },
      catalog: { on: ['note', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'corporativo', name: 'Corporativo sobrio', style: 'Corporativo sobrio',
    desc: 'Azul institucional, orden y confianza.',
    tier: 'base', template: 'classic', pageTheme: 'light',
    rubros: ['services', 'general', 'ofertas'],
    theme: theme({
      accent: '#1e40af',
      pal: { bg: '#f3f6fa', surface: '#ffffff', text: '#0f172a', muted: '#52617a', border: '#d8e0ec' },
      containers: { radius: 'md', shadow: 'soft', border: 'thin', density: 'comfortable', surface: 'elevated' },
      heading: 'montserrat', body: 'open-sans', weight: 600, tracking: '0em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      motion: { reveal: 'fade', hover: 'none', intensity: 'subtle' },
      mobile: { cardStyle: 'standard', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'about', 'services', 'stats', 'benefits', 'featured', 'brands', 'testimonials', 'faq', 'cta', 'contact'], var: { stats: 'band' } },
      catalog: { on: ['note', 'banner', 'promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'gourmet-calido', name: 'Gourmet cálido', style: 'Gourmet cálido',
    desc: 'Menú de autor: madera, crema y apetito.',
    tier: 'advanced', template: 'minimal', pageTheme: 'light',
    rubros: ['food'],
    theme: theme({
      accent: '#9a3412',
      pal: { bg: '#faf6ef', surface: '#fffdf7', text: '#292018', muted: '#7c6a56', border: '#e5d9c6' },
      containers: { radius: 'sm', shadow: 'soft', border: 'thin', density: 'spacious', surface: 'elevated' },
      heading: 'playfair-display', body: 'lora', weight: 600, tracking: '-0.01em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      motion: { reveal: 'fade', hover: 'none', intensity: 'subtle' },
      mobile: { cardStyle: 'compact', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'featured', 'about', 'offers', 'stats', 'gallery', 'testimonials', 'faq', 'cta', 'contact'], var: { stats: 'band' } },
      catalog: { on: ['note', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'belleza-rosa', name: 'Belleza rosa', style: 'Beauty rosado',
    desc: 'Vidriera rosa empolvada con serif de revista.',
    tier: 'plus', template: 'vitrina', pageTheme: 'light',
    rubros: ['belleza', 'moda', 'lifestyle'],
    theme: theme({
      accent: '#db2777',
      pal: { bg: '#fdf4f8', surface: '#ffffff', text: '#4a1d33', muted: '#9a6b82', border: '#f3d3e2' },
      containers: { radius: 'xl', shadow: 'soft', border: 'none', density: 'spacious', surface: 'elevated' },
      heading: 'playfair-display', body: 'nunito', weight: 600, tracking: '-0.01em',
      buttons: { shape: 'pill', style: 'solid', size: 'md' },
      background: { type: 'gradient', value: 'linear-gradient(160deg, #fdf4f8, #fbe8f0 60%, #f6dcea)' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'subtle' },
      mobile: { nav: 'bottom', cardStyle: 'overlay', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'featured', 'about', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'] },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'kids-ludico', name: 'Kids lúdico', style: 'Kids lúdico',
    desc: 'Colores redondos y alegres para chicos y grandes.',
    tier: 'base', template: 'duo', pageTheme: 'light',
    rubros: ['general', 'ofertas'],
    theme: theme({
      accent: '#7c3aed',
      pal: { bg: '#fefce8', surface: '#ffffff', text: '#27272a', muted: '#6b7280', border: '#e9d5ff' },
      containers: { radius: 'xl', shadow: 'soft', border: 'thin', density: 'comfortable', surface: 'elevated' },
      heading: 'comfortaa', body: 'nunito', weight: 700, tracking: '0em',
      buttons: { shape: 'pill', style: 'solid', size: 'lg' },
      background: { type: 'pattern', value: 'repeating-linear-gradient(45deg, rgba(124,58,237,.06) 0 2px, transparent 2px 10px), #fefce8' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'bold' },
      mobile: { nav: 'bottom', gridCols: 2, cardStyle: 'standard', stickyCta: true, heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'featured', 'about', 'benefits', 'gallery', 'testimonials', 'faq', 'cta', 'contact'] },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'band', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'urbano-sticker', name: 'Urbano sticker', style: 'Urbano sticker',
    desc: 'Streetwear: titulares XXL y amarillo señal.',
    tier: 'plus', template: 'vitrina', pageTheme: 'light',
    rubros: ['moda', 'gamer'],
    theme: theme({
      accent: '#eab308',
      pal: { bg: '#ffffff', surface: '#ffffff', text: '#111827', muted: '#6b7280', border: '#111827' },
      containers: { radius: 'sm', shadow: 'none', border: 'bold', density: 'compact', surface: 'outlined' },
      heading: 'archivo-black', body: 'space-grotesk', scale: 'editorial', weight: 900, tracking: '-0.03em',
      buttons: { shape: 'square', style: 'solid', size: 'md' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'bold' },
      mobile: { nav: 'bottom', cardStyle: 'compact', stickyCta: true, heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'announcements', 'highlights', 'featured', 'offers', 'brands', 'countdown', 'gallery', 'cta', 'contact'], var: { announcements: 'marquee' } },
      catalog: { on: ['promo', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'form', 'faq'] }
    }
  },
  {
    id: 'consola-retro', name: 'Consola retro', style: 'Consola retro',
    desc: 'Fósforo verde y scanlines: terminal viva.',
    tier: 'advanced', template: 'minimal', pageTheme: 'dark',
    rubros: ['gamer', 'tech'],
    theme: theme({
      accent: '#4ade80',
      pal: { bg: '#070b08', surface: '#0b120d', text: '#b8f0c6', muted: '#5d7a66', border: '#1c2a21' },
      containers: { radius: 'none', shadow: 'none', border: 'thin', density: 'compact', surface: 'flat' },
      heading: 'jetbrains-mono', body: 'space-mono', scale: 'compact', weight: 700, tracking: '0em',
      buttons: { shape: 'square', style: 'outline', size: 'sm' },
      background: { type: 'pattern', value: 'repeating-linear-gradient(0deg, rgba(0,0,0,.22) 0, rgba(0,0,0,.22) 1px, transparent 1px, transparent 3px), #070b08' },
      motion: { reveal: 'none', hover: 'glow', intensity: 'subtle' },
      mobile: { cardStyle: 'compact', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'announcements', 'stats', 'featured', 'about', 'benefits', 'offers', 'gallery', 'faq', 'cta', 'contact'], var: { announcements: 'static', stats: 'cards' } },
      catalog: { on: ['note', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'denim-urbano', name: 'Denim urbano', style: 'Denim urbano',
    desc: 'Jeans, calle y tipografía condensada: ropa de todos los días.',
    tier: 'base', template: 'duo', pageTheme: 'light',
    rubros: ['moda', 'lifestyle'],
    theme: theme({
      accent: '#1e3a5f',
      pal: { bg: '#f2f4f7', surface: '#ffffff', text: '#101828', muted: '#5d6b7f', border: '#d7dde6' },
      containers: { radius: 'sm', shadow: 'soft', border: 'thin', density: 'compact', surface: 'elevated' },
      heading: 'oswald', body: 'work-sans', scale: 'compact', weight: 600, tracking: '0.01em',
      buttons: { shape: 'rounded', style: 'solid', size: 'md' },
      motion: { reveal: 'rise', hover: 'lift', intensity: 'subtle' },
      mobile: { gridCols: 2, cardStyle: 'compact', heroHeight: 'compact' }
    }),
    layout: {
      landing: { on: ['hero', 'announcements', 'highlights', 'featured', 'stats', 'offers', 'gallery', 'faq', 'cta', 'contact'], var: { announcements: 'static', stats: 'cards' } },
      catalog: { on: ['filters', 'sort', 'grid', 'promo'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  },
  {
    id: 'atelier-moda', name: 'Atelier de moda', style: 'Atelier editorial',
    desc: 'Editorial de pasarela: serif fina, aire y fotos grandes.',
    tier: 'plus', template: 'vitrina', pageTheme: 'light',
    rubros: ['moda', 'belleza', 'lifestyle'],
    theme: theme({
      accent: '#8c1d3f',
      pal: { bg: '#faf7f5', surface: '#ffffff', text: '#1c1714', muted: '#7c7069', border: '#e7dfd9' },
      containers: { radius: 'none', shadow: 'none', border: 'thin', density: 'spacious', surface: 'flat' },
      heading: 'fraunces', body: 'figtree', scale: 'editorial', weight: 500, tracking: '0.01em',
      buttons: { shape: 'square', style: 'outline', size: 'md' },
      motion: { reveal: 'fade', hover: 'lift', intensity: 'subtle' },
      mobile: { cardStyle: 'standard', heroHeight: 'tall' }
    }),
    layout: {
      landing: { on: ['hero', 'highlights', 'featured', 'about', 'gallery', 'testimonials', 'faq', 'contact'], var: { hero: 'compact' } },
      catalog: { on: ['note', 'filters', 'sort', 'grid'] },
      services: { on: ['hero', 'picker', 'steps', 'form', 'faq'] }
    }
  }
]

// ---------------------------------------------------------------------------
// Taxonomía de rubros de la tienda (filtro de la galería — es propia, no
// son las familias de diseño) + detección por palabras del nombre del
// negocio y las categorías del catálogo.
// ---------------------------------------------------------------------------
export const RUBRO_LABELS = {
  ofertas: 'Ofertas', gamer: 'Gamer', general: 'Generalista', belleza: 'Belleza',
  hogar: 'Hogar', lifestyle: 'Lifestyle', moda: 'Indumentaria', tech: 'Tecnología',
  food: 'Comestibles', services: 'Servicios'
}

const RUBRO_KEYWORDS = {
  tech:     ['tecno', 'electro', 'celular', 'comput', 'notebook', 'audio', 'cable', 'cargador', 'smart', 'tablet', 'impresor', 'software', 'hardware', 'informat'],
  gamer:    ['gamer', 'gaming', 'consola', 'videojuego', 'esport', 'playstation', 'xbox', 'nintendo', 'joystick', 'pc ', 'setup'],
  moda:     ['ropa', 'indumentaria', 'remera', 'zapatilla', 'calzado', 'vestido', 'jean', 'moda', 'accesorio', 'cartera', 'zapato', 'buzo', 'campera', 'lenceria'],
  belleza:  ['belleza', 'cosmet', 'peluquer', 'unas', 'maquill', 'estet', 'skin', 'perfume', 'cabello', 'barber', 'spa', 'nails', 'pestan'],
  food:     ['comida', 'alimento', 'gourmet', 'dulce', 'panific', 'cafe', 'resto', 'bebida', 'vino', 'queso', 'pizza', 'empanada', 'helado', 'pasteler', 'gastron', 'cerveza', 'te ', 'mate'],
  hogar:    ['hogar', 'deco', 'mueble', 'ilumin', 'jardin', 'textil', 'vajilla', 'aroma', 'vela', 'cocina', 'blanqueria', 'cortina'],
  services: ['servicio', 'reparac', 'consultor', 'diseno', 'gestion', 'asesor', 'estudio', 'abogad', 'contad', 'taller', 'electric', 'plomer', 'flete', 'limpieza'],
  ofertas:  ['oferta', 'outlet', 'liquidac', 'mayor', 'descuent', 'regal', 'bazaar', 'bazar', 'variedades'],
  lifestyle:['libreria', 'regal', 'joya', 'reloj', 'arte', 'foto', 'mascota', 'plantas', 'deporte', 'fitness', 'gym', 'yoga']
}

// Un solo paso sobre todo el texto disponible (sin rubro explícito en el
// modelo, así que se infiere del negocio + categorías del catálogo).
export function detectRubro({ name = '', headline = '', categories = [] } = {}) {
  const text = [name, headline, ...categories]
    .join(' ').toLowerCase().normalize('NFD').replace(/\p{M}/gu, '')
  let best = null
  let bestScore = 0
  for (const [key, kws] of Object.entries(RUBRO_KEYWORDS)) {
    let score = 0
    for (const kw of kws) if (text.includes(kw)) score += kw.length > 5 ? 2 : 1
    if (score > bestScore) { best = key; bestScore = score }
  }
  return bestScore >= 2 ? best : null
}

// ---------------------------------------------------------------------------
// Catálogo resuelto: cada preset pasa por el normalizador del contrato
// (ids, enums y layout saneados) y conserva su metadata de catálogo.
// ---------------------------------------------------------------------------
export const STUDIO_PRESETS = PRESETS.map((raw) => {
  const resolved = resolveStudioPreset({ ...raw, layout: buildLayout(raw.template, raw.layout) })
  return {
    ...resolved,
    style: raw.style,
    desc: raw.desc,
    rubros: raw.rubros,
    pageTheme: raw.pageTheme,
    layoutSpec: raw.layout
  }
})

// Subconjunto curado que lista el select del panel "Estilos" (2 base, 2 plus,
// 2 advanced). El catálogo completo sigue disponible para guardar/aplicar.
export const PRESET_PICKER_IDS = [
  'neo-brutalista', 'corporativo', 'denim-urbano',
  'bento', 'pastel-suave', 'atelier-moda',
  'editorial-minima', 'lujo-serif'
]

export function presetById(id) {
  return STUDIO_PRESETS.find((p) => p.id === id) || null
}

// Layout del preset re-expandido contra OTRA plantilla (para "Combinar →
// solo la distribución" sobre el diseño que ya tiene la tienda).
export function layoutForTemplate(preset, templateId) {
  return buildLayout(templateId, preset?.layoutSpec || {})
}

// null = persiste completo; 'plan' = la plantilla está por encima del nivel;
// 'theme' = la plantilla alcanza pero el tema completo pide Premium (con
// Plus solo viajan radius/density de containers y nada del resto).
const TIER_BENEFIT = { base: null, plus: 'has_design_plus', advanced: 'has_design_advanced' }
export function presetLock(preset, benefits = {}) {
  const need = TIER_BENEFIT[STORE_TEMPLATES[preset?.template]?.tier || 'base']
  if (need && !benefits[need]) return 'plan'
  if (!benefits.has_design_advanced) return 'theme'
  return null
}

// Fuentes del catálogo entero en UN link (mismo patrón que
// ensureStoreFontPicker): las tarjetas se renderizan con su tipografía real.
let presetFontsDone = false
export function ensurePresetFonts() {
  if (presetFontsDone) return
  presetFontsDone = true
  const googles = new Set()
  for (const p of STUDIO_PRESETS) {
    for (const slug of [p.theme?.typography?.heading, p.theme?.typography?.body]) {
      const g = STORE_FONTS[slug]?.google
      if (g) googles.add(g)
    }
  }
  if (!googles.size || typeof document === 'undefined') return
  const link = document.createElement('link')
  link.id = 'preset-fonts'
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?${[...googles].sort().map((g) => `family=${g}`).join('&')}&display=swap`
  document.head.appendChild(link)
}

// Filtros de la galería: texto libre (nombre/estilo/rubro), rubro de la
// tienda, dirección de estilo, tier del plan y favoritos.
export function filterPresets(list, { q = '', rubro = '', style = '', tier = '', favs = null, usable = false, benefits = {} } = {}) {
  const needle = q.trim().toLowerCase()
  return (list || []).filter((p) => {
    if (favs && !favs.has(p.id)) return false
    if (tier && p.tier !== tier) return false
    if (style && p.style !== style) return false
    if (rubro && !p.rubros.includes(rubro)) return false
    if (usable && presetLock(p, benefits) !== null) return false
    if (!needle) return true
    const hay = `${p.name} ${p.style} ${p.desc} ${p.rubros.map((r) => RUBRO_LABELS[r] || r).join(' ')}`.toLowerCase()
    return hay.includes(needle)
  })
}
