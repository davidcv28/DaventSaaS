import { firebase } from '../config/env.js'

// Verificación de celular por SMS con Firebase Phone Auth (plan Spark gratis).
// El SDK pesa ~100KB: se importa lazy solo cuando el usuario pide verificar —
// no infla el chunk principal de la app.
async function getFirebaseAuth() {
  const { initializeApp, getApps } = await import('firebase/app')
  const { getAuth } = await import('firebase/auth')
  const app = getApps().length ? getApps()[0] : initializeApp(firebase)
  return getAuth(app)
}

// Un solo reCAPTCHA por flujo: crear uno nuevo por click sin limpiar el
// anterior deja iframes huérfanos y el segundo render puede fallar con
// auth/argument-error ("reCAPTCHA has already been rendered").
let verifier = null

function resetVerifier() {
  try { verifier?.clear() } catch { /* ya destruido */ }
  verifier = null
}

// Firebase exige E.164 (+<pais><numero>). El perfil ya guarda +549..., pero si
// algún dato viejo quedó sin el + se normaliza acá en vez de fallar feo.
function e164(phone) {
  const digits = (phone || '').replace(/\D/g, '')
  return digits ? `+${digits}` : ''
}

// Dispara el SMS al número del perfil. Devuelve el confirmationResult que hay
// que guardar para confirmar el código después (no es serializable).
// containerEl: div donde Firebase monta el reCAPTCHA invisible (obligatorio).
export async function sendVerificationSms(phoneNumber, containerEl) {
  const auth = await getFirebaseAuth()
  const { RecaptchaVerifier, signInWithPhoneNumber } = await import('firebase/auth')
  resetVerifier()
  verifier = new RecaptchaVerifier(auth, containerEl, { size: 'invisible' })
  try {
    return await signInWithPhoneNumber(auth, e164(phoneNumber), verifier)
  } catch (e) {
    // Un verifier que falló (captcha expirado, widget roto) no se reusa.
    resetVerifier()
    throw e
  }
}

// Confirma el código del SMS y devuelve el idToken para validar en backend
// (POST /api/verify-phone/ lo coteja con el phoneNumber verificado por Google).
export async function confirmSmsCode(confirmationResult, code) {
  try {
    const credential = await confirmationResult.confirm(code)
    return credential.user.getIdToken()
  } finally {
    // Confirmó o falló: el flujo terminó, el widget se descarta.
    resetVerifier()
  }
}
