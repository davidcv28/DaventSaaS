import { inject, computed, unref } from 'vue'

// Matriz diseño → arquetipos visuales de navbar / panel de cuenta /
// seguimiento (docs/_tmp-nav-catalog.md). El chrome compartido
// (StorePublicLayout / StoreAccountView / StoreTrackingView) expone estos
// slugs como data-nav / data-account / data-tracking en .store-page; el
// look por arquetipo vive en CSS keyed en esos atributos — las vistas no
// se modifican.

export const NAV_ARCHETYPES = [
  'left-logo-standard', 'center-logo-split', 'utility-plus-primary',
  'mega-menu', 'floating-pill', 'sticky-condensed', 'hide-on-scroll',
  'sidebar-rail', 'search-first-command', 'hamburger-overlay',
  'bottom-tabbar', 'side-drawer-right', 'fullscreen-sheet', 'dock',
  'editorial-index', 'ticket-menu', 'breadcrumb-bar', 'announcement-rotator',
  'icon-rail-top', 'card-menu-flyout', 'contextual-sticky', 'swipe-tabs',
  'glassmorphism-overlay', 'command-palette-nav', 'statement-bar',
  'index-rail', 'minimal-floating'
]

export const ACCOUNT_ARCHETYPES = [
  'account-sidebar', 'account-rail', 'account-topbar', 'account-tabs-only',
  'account-split', 'account-card', 'account-stack', 'account-bento'
]

export const TRACKING_ARCHETYPES = [
  'tracking-stepper', 'tracking-timeline', 'tracking-ticket',
  'tracking-status-hero', 'tracking-feed', 'tracking-bento',
  'tracking-minimal', 'tracking-stepcard'
]

const NAV_SET = new Set(NAV_ARCHETYPES)
const ACCOUNT_SET = new Set(ACCOUNT_ARCHETYPES)
const TRACKING_SET = new Set(TRACKING_ARCHETYPES)

export const DEFAULT_ARCHETYPES = {
  nav: 'left-logo-standard',
  account: 'account-sidebar',
  tracking: 'tracking-stepper'
}

// designId (slug del catálogo) → arquetipos. navbar 100% único por diseño;
// el par (cuenta, seguimiento) también es único por diseño.
export const DESIGN_ARCHETYPES = {
  portico:       { nav: 'editorial-index',        account: 'account-sidebar', tracking: 'tracking-ticket' },
  esencial:      { nav: 'left-logo-standard',     account: 'account-tabs-only', tracking: 'tracking-stepper' },
  mercado:       { nav: 'mega-menu',              account: 'account-stack',   tracking: 'tracking-bento' },
  autoservicio:  { nav: 'swipe-tabs',             account: 'account-rail',    tracking: 'tracking-feed' },
  gimnasio:      { nav: 'bottom-tabbar',          account: 'account-bento',   tracking: 'tracking-status-hero' },
  movimiento:    { nav: 'utility-plus-primary',   account: 'account-topbar',  tracking: 'tracking-timeline' },
  sastreria:     { nav: 'ticket-menu',            account: 'account-card',    tracking: 'tracking-stepcard' },
  moderntec:     { nav: 'command-palette-nav',    account: 'account-sidebar', tracking: 'tracking-minimal' },
  indumentaria:  { nav: 'card-menu-flyout',       account: 'account-split',   tracking: 'tracking-timeline' },
  impacto:       { nav: 'announcement-rotator',   account: 'account-tabs-only', tracking: 'tracking-feed' },
  showroom:      { nav: 'sticky-condensed',       account: 'account-stack',   tracking: 'tracking-ticket' },
  ruta:          { nav: 'breadcrumb-bar',         account: 'account-card',    tracking: 'tracking-stepper' },
  aurum:         { nav: 'floating-pill',          account: 'account-rail',    tracking: 'tracking-status-hero' },
  brigada:       { nav: 'side-drawer-right',      account: 'account-bento',   tracking: 'tracking-minimal' },
  neon:          { nav: 'dock',                   account: 'account-topbar',  tracking: 'tracking-feed' },
  calzado:       { nav: 'hide-on-scroll',         account: 'account-split',   tracking: 'tracking-bento' },
  moda:          { nav: 'hamburger-overlay',      account: 'account-card',    tracking: 'tracking-timeline' },
  modista:       { nav: 'fullscreen-sheet',       account: 'account-tabs-only', tracking: 'tracking-status-hero' },
  topmodern:     { nav: 'search-first-command',   account: 'account-stack',   tracking: 'tracking-stepcard' },
  viajero:       { nav: 'sidebar-rail',           account: 'account-rail',    tracking: 'tracking-ticket' },
  olivium:       { nav: 'glassmorphism-overlay',  account: 'account-bento',   tracking: 'tracking-ticket' },
  'atelier-noir': { nav: 'index-rail',            account: 'account-split',   tracking: 'tracking-feed' },
  guardia:       { nav: 'contextual-sticky',      account: 'account-topbar',  tracking: 'tracking-bento' },
  expediente:    { nav: 'icon-rail-top',         account: 'account-card',    tracking: 'tracking-bento' },
  silicio:       { nav: 'statement-bar',          account: 'account-tabs-only', tracking: 'tracking-timeline' },
  umbral:        { nav: 'minimal-floating',       account: 'account-stack',   tracking: 'tracking-status-hero' }
}

// Lookup con fallback: un diseño sin fila en la matriz (o vacío) cae en los
// defaults de plataforma. Los slugs desconocidos no rompen nada.
export function archetypeForDesign(designId) {
  const key = String(designId || '').trim().toLowerCase()
  const entry = DESIGN_ARCHETYPES[key]
  if (!entry) return { ...DEFAULT_ARCHETYPES, design: key || 'esencial' }
  return {
    nav: NAV_SET.has(entry.nav) ? entry.nav : DEFAULT_ARCHETYPES.nav,
    account: ACCOUNT_SET.has(entry.account) ? entry.account : DEFAULT_ARCHETYPES.account,
    tracking: TRACKING_SET.has(entry.tracking) ? entry.tracking : DEFAULT_ARCHETYPES.tracking,
    design: key
  }
}

// Composable para las vistas hijas (cuenta/seguimiento): mismo designId
// que StorePublicLayout — custom.template || site_theme.style.id, con
// 'raiz'/vacío → 'esencial'. Devuelve computed { nav, account, tracking, design }.
export function useStoreArchetypes() {
  const ctx = inject('storePage', null)
  const custom = computed(() => unref(ctx?.custom) || {})
  const designId = computed(() => {
    const raw = String(custom.value.template || custom.value?.site_theme?.style?.id || '').trim().toLowerCase()
    if (!raw || raw === 'raiz') return 'esencial'
    return raw
  })
  return computed(() => archetypeForDesign(designId.value))
}
