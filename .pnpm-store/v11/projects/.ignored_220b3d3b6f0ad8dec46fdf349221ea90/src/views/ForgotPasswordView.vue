<script setup>
import { ref } from 'vue'
import { authApi } from '../api/auth.api.js'
import { validateEmail } from '../validators/auth.validators.js'
import { extractApiError } from '../api/http.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'

const email = ref('')
const touched = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')

async function onSubmit() {
  touched.value = true
  error.value = ''
  success.value = ''
  const v = validateEmail(email.value)
  if (v) return
  loading.value = true
  try {
    const data = await authApi.requestPasswordReset(email.value.trim())
    success.value = data?.Exito || 'Si el correo está registrado, te va a llegar un enlace para restablecer tu contraseña.'
  } catch (e) {
    error.value = extractApiError(e).nonField || 'No se pudo procesar la solicitud. Reintentá en unos minutos.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="Recuperá tu acceso" subtitle="Te enviamos un enlace para restablecer tu contraseña.">
    <AlertMessage v-if="error" kind="error" :message="error" />
    <AlertMessage v-if="success" kind="success" :message="success" />

    <form v-if="!success" @submit.prevent="onSubmit" novalidate>
      <AppInput
        v-model="email"
        label="Correo electrónico"
        name="email"
        type="email"
        placeholder="tu@correo.com"
        autocomplete="email"
        required
        :error="touched && validateEmail(email) ? validateEmail(email) : ''"
        @blur="touched = true"
      />
      <AppButton :loading="loading">Enviar enlace</AppButton>
    </form>

    <AlertMessage v-if="!success" kind="info" message="El enlace vence a las 72 horas. Si no ves el correo, revisá la carpeta de spam." />

    <div class="auth-links">
      <RouterLink to="/login">Volver al login</RouterLink>
      <RouterLink to="/register">Crear cuenta</RouterLink>
    </div>
  </AuthLayout>
</template>
