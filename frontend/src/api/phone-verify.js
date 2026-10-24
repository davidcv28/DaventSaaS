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

// Dispara el SMS al número del perfil. Devuelve el confirmationResult que hay
// que guardar para confirmar el código después (no es serializable).
// containerEl: div donde Firebase monta el reCAPTCHA invisible (obligatorio).
export async function sendVerificationSms(phoneNumber, containerEl) {
  const auth = await getFirebaseAuth()
  const { RecaptchaVerifier, signInWithPhoneNumber } = await import('firebase/auth')
  const verifier = new RecaptchaVerifier(auth, containerEl, { size: 'invisible' })
  return signInWithPhoneNumber(auth, phoneNumber, verifier)
}

// Confirma el código del SMS y devuelve el idToken para validar en backend
// (POST /api/verify-phone/ lo coteja con el phoneNumber verificado por Google).
export async function confirmSmsCode(confirmationResult, code) {
  const credential = await confirmationResult.confirm(code)
  return credential.user.getIdToken()
}
