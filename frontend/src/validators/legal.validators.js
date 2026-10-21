// Espejo de validadores Django (legal/serializers/validators.py).
// Si backend cambia, cambiar aquí también (FRONTEND_RULES §4).

export const REPORT_KINDS = [
  { value: 'COPYRIGHT', label: 'Derechos de autor / copyright' },
  { value: 'TRADEMARK', label: 'Uso de marca registrada' },
  { value: 'ILLEGAL', label: 'Contenido ilegal' },
  { value: 'OTHER', label: 'Otro' }
]

const LETTERS_RE = /^[a-zA-Z\sñÑáéíóúÁÉÍÓÚ]+$/

// La obra/derecho original solo es obligatoria en denuncias de copyright y marca.
export function needsOriginalWork(kind) {
  return kind === 'COPYRIGHT' || kind === 'TRADEMARK'
}

export function validateReporterName(v = '') {
  const s = v.trim()
  if (!s) return 'Este campo es obligatorio'
  if (s.length < 3) return 'Nombre demasiado corto'
  if (s.length > 150) return 'Nombre demasiado largo'
  if (!LETTERS_RE.test(s)) return 'En este campo solo se aceptan letras'
  return null
}

export function validateReporterEmail(v = '') {
  const s = v.trim()
  if (!s) return 'Este campo es obligatorio'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return 'Ingresa un correo válido'
  return null
}

export function validateReportedUrl(v = '') {
  const s = v.trim()
  if (!s) return 'Este campo es obligatorio'
  if (s.length > 500) return 'La URL es demasiado larga'
  if (!/^https?:\/\/\S+$/.test(s)) return 'La URL del contenido debe comenzar con http:// o https://'
  return null
}

export function validateOriginalWork(v = '', kind = 'COPYRIGHT') {
  const s = (v || '').trim()
  if (!needsOriginalWork(kind)) return null
  if (!s) return 'Identificá la obra, imagen, texto o marca afectada'
  if (s.length > 255) return 'El texto es demasiado largo'
  return null
}

export function validateReportDescription(v = '') {
  const s = (v || '').trim()
  if (!s) return 'Este campo es obligatorio'
  if (s.length < 20) return 'La descripción debe tener al menos 20 caracteres'
  return null
}

export function validateGoodFaith(v) {
  return v === true ? null : 'Debés declarar de buena fe que la información de la denuncia es veraz'
}
