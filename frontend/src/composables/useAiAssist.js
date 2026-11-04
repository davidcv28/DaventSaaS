// Catálogo de opciones y helpers compartidos por el asistente de diseño
// "Asistencia con IA" (AiAssistModal). Los ids son
// canónicos del motor: RUBROS/GOALS/TONES/MUST_HAVE_BLOCKS de ai_design_recipes.

export const RUBROS = [
  { id: 'comercio', label: 'Comercio o tienda', icon: 'tag', desc: 'Local, kiosco, mayorista' },
  { id: 'gastronomia', label: 'Comida y bebida', icon: 'coffee', desc: 'Restó, bar, panadería, delivery' },
  { id: 'indumentaria', label: 'Indumentaria y moda', icon: 'tag', desc: 'Ropa, calzado, accesorios' },
  { id: 'belleza', label: 'Belleza y estética', icon: 'flower', desc: 'Peluquería, uñas, maquillaje' },
  { id: 'salud', label: 'Salud y bienestar', icon: 'heart', desc: 'Consultorios, terapias, gym' },
  { id: 'construccion', label: 'Construcción y oficios', icon: 'wrench', desc: 'Obra, plomería, electricidad' },
  { id: 'seguridad', label: 'Seguridad y bomberos', icon: 'shield-check', desc: 'Seguridad industrial, EPP' },
  { id: 'tecnologia', label: 'Tecnología', icon: 'monitor', desc: 'Equipos, reparaciones, software' },
  { id: 'educacion', label: 'Educación', icon: 'graduation-cap', desc: 'Clases, cursos, talleres' },
  { id: 'turismo', label: 'Turismo y viajes', icon: 'map-pin', desc: 'Alojamiento, excursiones' },
  { id: 'mascotas', label: 'Mascotas', icon: 'paw-print', desc: 'Veterinaria, peluquería, alimento' },
  { id: 'arte', label: 'Arte y diseño', icon: 'palette', desc: 'Muebles, deco, regalos, talleres' },
  { id: 'servicios_profesionales', label: 'Servicios profesionales', icon: 'file-text', desc: 'Estudios, consultoría, oficios' },
  { id: 'otro', label: 'Otra cosa', icon: 'sparkles', desc: 'Te lo armamos igual' }
]

export const GOALS = [
  { id: 'vender_online', label: 'Vender online', icon: 'credit-card', desc: 'Que puedan comprar desde la web' },
  { id: 'mostrar_servicios', label: 'Mostrar mis servicios', icon: 'wrench', desc: 'Explicar qué hacés y cuánto sale' },
  { id: 'conseguir_consultas', label: 'Recibir consultas', icon: 'message-circle', desc: 'Que te escriban o te llamen' },
  { id: 'dar_confianza', label: 'Dar confianza', icon: 'shield-check', desc: 'Que vean que sos un negocio serio' },
  { id: 'mostrar_trabajos', label: 'Mostrar mis trabajos', icon: 'images', desc: 'Fotos de lo que hacés' }
]

export const TONES = [
  { id: 'calido', label: 'Cálido y cercano', icon: 'heart', desc: 'Como una charla entre conocidos' },
  { id: 'serio', label: 'Serio y confiable', icon: 'building-2', desc: 'Ordenado, sobrio, profesional' },
  { id: 'moderno', label: 'Moderno y simple', icon: 'zap', desc: 'Limpio, actual, directo' },
  { id: 'audaz', label: 'Audaz y con personalidad', icon: 'flame', desc: 'Colores fuertes y letras grandes' }
]

export const AUDIENCES = [
  { id: 'particulares', label: 'Personas', icon: 'users', desc: 'Clientes que compran para ellos' },
  { id: 'empresas', label: 'Empresas', icon: 'building-2', desc: 'Negocios que te contratan' },
  { id: 'ambas', label: 'Las dos', icon: 'users', desc: 'Personas y empresas' }
]

export const STYLE_HINTS = [
  { id: 'elegancia', label: 'Elegancia', icon: 'gem', tone: 'serio' },
  { id: 'energia', label: 'Energía', icon: 'flame', tone: 'audaz' },
  { id: 'cercania', label: 'Cercanía', icon: 'heart', tone: 'calido' },
  { id: 'tecnologia', label: 'Tecnología', icon: 'monitor', tone: 'moderno' },
  { id: 'tradicion', label: 'Tradición', icon: 'award', tone: 'serio' },
  { id: 'lujo', label: 'Lujo', icon: 'crown', tone: 'serio' }
]

export const HINT_TONE_ORDER = ['audaz', 'calido', 'moderno', 'serio']

// Secciones que el dueño elige mostrar. Cada una escribe flags reales de la
// customization (show_*/site_templates) Y aporta su must_have al pedido.
export const SECTIONS = [
  { id: 'catalog', label: 'Catálogo', icon: 'tag', desc: 'Tus productos con foto y precio', must: 'prices', flag: 'show_catalog', site: 'catalog' },
  { id: 'services', label: 'Servicios', icon: 'wrench', desc: 'Lo que hacés, con pedido por WhatsApp', site: 'services', flag: 'show_services', needs: 'has_services_site' },
  { id: 'gallery', label: 'Galería de fotos', icon: 'images', desc: 'Fotos de tu local y tus trabajos', flag: 'show_gallery' },
  { id: 'testimonials', label: 'Opiniones de clientes', icon: 'quote', desc: 'Lo que dicen de vos', must: 'testimonials', flag: 'show_testimonials' },
  { id: 'map', label: 'Mapa y horarios', icon: 'map-pin', desc: 'Cómo llegar y cuándo abrís', must: 'map', flag: 'show_location', also: 'show_hours' },
  { id: 'contact', label: 'Contacto y WhatsApp', icon: 'whatsapp', desc: 'Que te escriban al toque', must: 'whatsapp', flag: 'show_contact' },
  { id: 'faqs', label: 'Preguntas frecuentes', icon: 'circle-help', desc: 'Las dudas que te preguntan siempre', must: 'faqs', flag: 'show_faq' },
  { id: 'hours', label: 'Horarios de atención', icon: 'clock', desc: 'Cuándo estás abierto', must: 'hours', flag: 'show_hours' }
]

// Tipografías que el motor sabe aplicar (ids de TYPE_PAIRS en el backend).
export const PAIR_OPTIONS = [
  { id: 'grotesk-clean', label: 'Grotesk limpio', icon: 'type', desc: 'Neutra y actual' },
  { id: 'serif-editorial', label: 'Serif editorial', icon: 'type', desc: 'Con carácter, tipo revista' },
  { id: 'serif-classic', label: 'Serif clásico', icon: 'type', desc: 'Sobria y elegante' },
  { id: 'display-heavy', label: 'Peso máximo', icon: 'type', desc: 'Títulos que se imponen' },
  { id: 'geometric', label: 'Geométrica', icon: 'type', desc: 'Moderna y limpia' },
  { id: 'warm-serif', label: 'Serif cálida', icon: 'type', desc: 'Cercana, con detalle' }
]

export const emptyAssistAnswers = () => ({
  name: '', rubro: '', province: '', city: '', whatsapp: '', hours_label: '', hours_value: '',
  description: '', highlights: '',
  sections: ['catalog', 'contact', 'hours'],
  goals: [], tone: '', style_hint: [], audience: '',
  content_hint: ''
})

// Las secciones elegidas se traducen a los must_have del motor.
export function mustFromSections(answers) {
  const list = []
  SECTIONS.forEach((s) => {
    if (answers.sections.includes(s.id) && s.must && !list.includes(s.must)) list.push(s.must)
  })
  return list
}

// El estilo elegido a mano manda; si no eligió, deciden los "me importa más".
export function resolvedTone(answers) {
  if (answers.tone) return answers.tone
  const votes = {}
  answers.style_hint.forEach((h) => {
    const tone = STYLE_HINTS.find((o) => o.id === h)?.tone
    if (tone) votes[tone] = (votes[tone] || 0) + 1
  })
  const keys = Object.keys(votes)
  if (!keys.length) return ''
  return keys.sort((a, b) => (votes[b] - votes[a]) || (HINT_TONE_ORDER.indexOf(a) - HINT_TONE_ORDER.indexOf(b)))[0]
}

// Pedido estructurado que viaja a POST /stores/ai-design/.
export function buildPrompt(answers) {
  const p = {}
  if (answers.rubro) p.rubro = answers.rubro
  if (answers.goals.length) p.goals = [...answers.goals]
  const tone = resolvedTone(answers)
  if (tone) p.tone = tone
  if (answers.audience) p.audience = answers.audience
  const must = mustFromSections(answers)
  if (must.length) p.must_have = must
  const notes = String(answers.content_hint || answers.description || '').trim()
  if (notes) p.notes = notes.slice(0, 160)
  return p
}

// Descripción sugerida en local (sin backend): mismo texto que usa el
// asistente de diseño para el paso "Qué vendés".
export function suggestDescription({ name, rubro, city }) {
  const rubroLabel = (RUBROS.find((r) => r.id === rubro)?.label || 'negocio').toLowerCase()
  return `${name || 'Tu negocio'} es tu ${rubroLabel} de confianza${city ? ` en ${city}` : ''}. Escribinos por WhatsApp y te asesoramos sin compromiso.`
}

export function toggleId(list, id, max = 0) {
  const i = list.indexOf(id)
  if (i >= 0) { list.splice(i, 1); return }
  if (max && list.length >= max) list.shift()
  list.push(id)
}
