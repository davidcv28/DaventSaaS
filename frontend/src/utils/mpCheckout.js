// Validación compartida de URLs de checkout de Mercado Pago: la URL
// viene del backend pero se revalida en el cliente — solo hosts
// oficiales de MP pueden recibir el redirect (defensa en profundidad
// ante un upstream comprometido). Usada por el checkout de pedidos
// (PaymentInstructions) y por todos los sinks de facturación del
// dashboard (planes, débito automático).
const MP_HOST_RE = /(^|\.)(mercadopago|mercadolibre)\.[a-z]{2,63}(\.[a-z]{2,63})?$|(^|\.)mpago\.la$/

export function isMpCheckoutUrl(url) {
  try {
    const u = new URL(url)
    return u.protocol === 'https:' && MP_HOST_RE.test(u.hostname.toLowerCase())
  } catch {
    return false
  }
}

// URL de checkout desde la respuesta de MP: prefiere checkout_url y
// cae a init_point (init_point es el nombre que usa la API de
// preapproval; checkout_url el de payments). sandbox_init_point SOLO en
// builds de desarrollo: un checkout de testing jamás debe recibir un
// redirect en producción.
export function mpCheckoutUrl(data) {
  const live = data?.checkout_url || data?.init_point || null
  if (live) return live
  return import.meta.env?.PROD ? null : (data?.sandbox_init_point || null)
}
