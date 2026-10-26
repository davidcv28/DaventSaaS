<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PasswordStrength from '../components/PasswordStrength.vue'
import {
  validateUsername, validateEmail, validatePassword,
  validatePhone, validateAcceptTerms
} from '../validators/auth.validators.js'

const router = useRouter()
const auth = useAuthStore()
const successMsg = ref('')

// Alta minimal: solo cuenta + celular (ancla anti-abuso) + TyC.
// Los datos fiscales/de facturación se piden recién al contratar un plan.
const form = reactive({
  username: '', email: '', password: '', confirm_password: '',
  phone: '', accept_terms: false
})
const touched = reactive({})

function err(name, validator) {
  if (!touched[name]) return ''
  return validator || auth.fieldErrors[name] || ''
}

function validateForm() {
  const e = {}
  const u = validateUsername(form.username)
  const m = validateEmail(form.email)
  const p = validatePassword(form.password)
  const ph = validatePhone(form.phone)
  const ty = validateAcceptTerms(form.accept_terms)
  if (u) e.username = u
  if (m) e.email = m
  if (p) e.password = p
  if (!form.confirm_password) e.confirm_password = 'Este campo es obligatorio'
  else if (form.password !== form.confirm_password) e.confirm_password = 'Las contraseñas no coinciden'
  if (ph) e.phone = ph
  if (ty) e.accept_terms = ty
  return e
}

async function onSubmit() {
  Object.keys(form).forEach((k) => { touched[k] = true })
  if (Object.keys(validateForm()).length) return
  const res = await auth.register(form)
  if (res.ok) {
    successMsg.value = res.message
    setTimeout(() => router.push({ name: 'login', query: { registered: '1' } }), 1400)
  }
}

const formErrors = computed(() => validateForm())
</script>
<template>
  <AuthLayout title="Creá tu cuenta" subtitle="Solo usuario, correo, contraseña y celular. Los datos de facturación te los pedimos recién al contratar un plan.">
    <AlertMessage v-if="auth.lastError" kind="error" :message="auth.lastError" />
    <AlertMessage v-if="successMsg" kind="success" :message="`${successMsg} Redirigiendo al login…`" />
    <AlertMessage kind="info" message="Usamos tu celular para cuidar las cuentas de prueba: un número, una cuenta." />

    <form @submit.prevent="onSubmit" novalidate>
      <AppInput v-model="form.username" label="Nombre de usuario" name="username" placeholder="Ej. alfredo27" required :error="err('username', formErrors.username)" @blur="touched.username = true" />
      <AppInput v-model="form.email" label="Correo electrónico" name="email" type="email" placeholder="Ej. alfredito2026@outlook.com" hint="Usá un correo real: te llega el link de verificación." required :error="err('email', formErrors.email)" @blur="touched.email = true" />
      <AppInput v-model="form.password" label="Contraseña" name="password" type="password" placeholder="Ej. Asdf@123" hint="Mínimo 8: minúscula, mayúscula, número y especial." required :error="err('password', formErrors.password)" @blur="touched.password = true" />
      <PasswordStrength :value="form.password" />
      <AppInput v-model="form.confirm_password" label="Confirmar contraseña" name="confirm_password" type="password" placeholder="Repetir contraseña" required :error="err('confirm_password', formErrors.confirm_password)" @blur="touched.confirm_password = true" />
      <AppInput v-model="form.phone" label="Número de celular" name="phone" placeholder="+5493871551234" hint="Formato internacional. Ej. +5493871551234" required :error="err('phone', formErrors.phone)" @blur="touched.phone = true" />
      <div class="field">
        <label class="check">
          <input
            v-model="form.accept_terms"
            type="checkbox"
            :aria-invalid="!!err('accept_terms', formErrors.accept_terms)"
            @change="touched.accept_terms = true"
          />
          <span>
            Leí y acepto los <RouterLink to="/terminos" target="_blank">Términos y condiciones</RouterLink>,
            incluida la política de copyright y contenido prohibido. Declaro que el contenido que suba a mi
            catálogo es propio o cuenta con autorización.
          </span>
        </label>
        <p v-if="err('accept_terms', formErrors.accept_terms)" class="field-error" role="alert">{{ err('accept_terms', formErrors.accept_terms) }}</p>
      </div>

      <div class="btn-row">
        <AppButton :loading="auth.status === 'loading'">Crear cuenta</AppButton>
      </div>
    </form>

    <div class="auth-links">
      <RouterLink to="/login">Ya tengo cuenta</RouterLink>
    </div>
  </AuthLayout>
</template>
