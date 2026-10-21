// Espejo de validadores Django (users/serializers/{validators,mixins,operations}.py).
// Si backend cambia, cambiar aquí también (FRONTEND_RULES §4).

export const ALLOWED_EMAIL_DOMAINS = ['@gmail.com', '@hotmail.com', '@outlook.com', '@yahoo.com', '@live.com']
export const CUIT_PREFIXES = ['20', '23', '24', '27', '30', '33', '34']
export const TAX_CONDITIONS = [
  { value: 'CF', label: 'Consumidor Final' },
  { value: 'MO', label: 'Monotributista' },
  { value: 'RI', label: 'Responsable Inscripto' },
  { value: 'EX', label: 'Exento' }
]

const LETTERS_RE = /^[a-zA-Z\sñÑáéíóúÁÉÍÓÚ]+$/

export function validateUsername(v = '') {
  const s = v.trim()
  if (!s) return 'Este campo es obligatorio'
  if (s.length < 6) return 'Nombre de usuario demasiado corto (mínimo 6)'
  if (s.length > 150) return 'Nombre de usuario demasiado largo'
  return null
}

export function validateEmail(v = '') {
  const s = v.trim()
  if (!s) return 'Este campo es obligatorio'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return 'Ingresa un correo válido'
  if (!ALLOWED_EMAIL_DOMAINS.some((d) => s.toLowerCase().endsWith(d))) {
    return 'El dominio del correo ingresado no es válido (usa gmail, hotmail, outlook, yahoo o live)'
  }
  return null
}

export function passwordChecks(v = '') {
  return [
    { ok: v.length >= 8, label: 'Mínimo 8 caracteres' },
    { ok: /[a-z]/.test(v), label: 'Una letra minúscula' },
    { ok: /[A-Z]/.test(v), label: 'Una letra mayúscula' },
    { ok: /[0-9]/.test(v), label: 'Un número' },
    { ok: /[^a-zA-Z0-9]/.test(v), label: 'Un carácter especial (@, #, $, %, &, *)' }
  ]
}

export function validatePassword(v = '') {
  if (!v) return 'Este campo es obligatorio'
  if (v.length < 8) return 'La contraseña es demasiado corta (mínimo 8)'
  if (v.length > 125) return 'La contraseña es demasiado larga'
  const missing = passwordChecks(v).filter((c) => !c.ok)
  if (missing.length) return `La contraseña debe contener: ${missing.map((m) => m.label.toLowerCase()).join(', ')}`
  return null
}

export function validateName(v = '', field = 'Este campo') {
  const s = v.trim()
  if (!s) return 'Este campo es obligatorio'
  if (s.length < 3) return `${field} demasiado corto`
  if (s.length > 150) return `${field} demasiado largo`
  if (!LETTERS_RE.test(s)) return 'En este campo solo se aceptan letras'
  return null
}

export function documentKindFor(tax) {
  return tax === 'CF' ? 'DNI' : 'CUIT'
}

// Checksum CUIT/CUIL idéntico a operations.DocumentFormat
export function isValidCuit(cuit = '') {
  if (!/^\d{11}$/.test(cuit)) return false
  if (!CUIT_PREFIXES.some((p) => cuit.startsWith(p))) return false
  const coef = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
  const digits = cuit.split('').map(Number)
  const total = coef.reduce((acc, c, i) => acc + c * digits[i], 0)
  const rem = total % 11
  if (rem === 1) return false
  const expected = rem === 0 ? 0 : 11 - rem
  return digits[10] === expected
}

export function validateDocument(document = '', tax = 'CF') {
  const s = (document || '').trim()
  if (!s) return 'Este campo es obligatorio'
  if (/[^0-9]/.test(s)) return 'En este campo solo se aceptan números'
  if (documentKindFor(tax) === 'DNI') {
    if (s.length < 7 || s.length > 8) return 'El DNI debe tener entre 7 y 8 dígitos'
    return null
  }
  if (s.length !== 11) return 'El CUIT/CUIL debe tener exactamente 11 dígitos'
  if (!isValidCuit(s)) return 'El CUIT/CUIL ingresado no es válido'
  return null
}

export function validateBusinessName(v = '', tax = 'CF') {
  const s = (v || '').trim()
  if (tax !== 'CF' && !s) return 'Este campo es obligatorio para tu condición fiscal'
  if (!s) return null
  if (s.length < 3) return 'Nombre comercial demasiado corto'
  if (s.length > 255) return 'Nombre comercial demasiado largo'
  if (!/^[a-zA-Z0-9\s,.\-&ñÑáéíóúÁÉÍÓÚ]+$/.test(s.toUpperCase())) return 'El nombre comercial contiene caracteres no válidos'
  return null
}

export function validatePhone(v = '') {
  const s = (v || '').trim()
  if (!s) return null // opcional en backend (allow_null)
  if (!/^\+54\d{10,13}$/.test(s)) return 'Ingresa un número válido en formato internacional. Ej. +5493871551234'
  return null
}

export function validateAddress(v = '') {
  const s = (v || '').trim()
  if (!s) return null // opcional
  if (s.length < 4) return 'El domicilio debe tener al menos 4 caracteres'
  if (s.length > 500) return 'Domicilio demasiado largo'
  return null
}

// Espejo de UserValidators['accept_terms'] (users/serializers/validators.py)
export function validateAcceptTerms(v) {
  return v === true ? null : 'Debés aceptar los Términos y condiciones para crear tu cuenta'
}

export function passwordScore(v = '') {
  return passwordChecks(v).filter((c) => c.ok).length // 0..5
}
