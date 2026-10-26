// Folleto a medida: el diseño (layout) lo arma DAVENT y el cliente rellena
// los textos y elige una foto de su galería. El borrador vive en localStorage
// por tienda: el diseñador lo guarda y la vista de impresión (/folleto?custom=1)
// lo lee, sin tocar el backend.

export const FLYER_LAYOUTS = [
  { id: 'impacto', label: 'Impacto', icon: 'zap', desc: 'Foto grande arriba, titular fuerte y sello de oferta.' },
  { id: 'oferta', label: 'Oferta', icon: 'percent', desc: 'Fondo a todo color con el descuento como protagonista.' },
  { id: 'editorial', label: 'Editorial', icon: 'sparkles', desc: 'Elegante y sobrio, con foto en arco sobre fondo claro.' }
]

export const FLYER_LIMITS = { title: 42, subtitle: 110, badge: 14, cta: 60, bullet: 46, contact: 40 }

export function defaultFlyerDraft(contact = '') {
  return {
    layout: 'impacto',
    title: '',
    subtitle: '',
    badge: '',
    bullets: ['', '', ''],
    cta: 'Escaneá y mirá todo el catálogo',
    contact,
    photo: '',
    showQr: true,
    showLogo: true
  }
}

const keyOf = (slug) => `davent:flyer-draft:${slug || 'tienda'}`

export function loadFlyerDraft(slug, contact = '') {
  const base = defaultFlyerDraft(contact)
  try {
    const raw = JSON.parse(localStorage.getItem(keyOf(slug)) || 'null')
    if (!raw || typeof raw !== 'object') return base
    const bullets = Array.isArray(raw.bullets) ? raw.bullets.slice(0, 3).map(String) : base.bullets
    while (bullets.length < 3) bullets.push('')
    return { ...base, ...raw, bullets }
  } catch {
    return base
  }
}

export function saveFlyerDraft(slug, draft) {
  try {
    localStorage.setItem(keyOf(slug), JSON.stringify(draft))
  } catch { /* cuota llena o modo privado: el borrador simplemente no persiste */ }
}

export function clearFlyerDraft(slug) {
  try { localStorage.removeItem(keyOf(slug)) } catch { /* noop */ }
}
