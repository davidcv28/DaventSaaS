<script setup>
import { ref } from 'vue'
import { authApi } from '../api/auth.api.js'
import { validateEmail } from '../validators/auth.validators.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'

const email = ref('')
const touched = ref(false)
const loading = ref(false)
const error = ref('')
const info = ref('')

async function onSubmit() {
  touched.value = true
  error.value = ''
  info.value = ''
  const v = validateEmail(email.value)
  if (v) return
  loading.value = true
  try {
    await authApi.requestPasswordReset(email.value.trim())
  } catch (e) {
    // Modo pending-backend (FRONTEND_RULES §3.6): el backend aún no tiene endpoint.
    // Mostramos panel informativo en lugar de fingir éxito.
    if (e.code === 'PENDING_BACKEND') {
      info.value = e.message
    } else {
      error.value = e.response?.data?.detail || 'No se pudo procesar la solicitud.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="Recuperá tu acceso" subtitle="Te enviamos un enlace para restablecer tu contraseña.">
    <AlertMessage v-if="error" kind="error" :message="error" />
    <AlertMessage v-if="info" kind="warn" :message="info" />

    <div class="alert info">
      <strong>Estado de la API:</strong> el backend Django aún no expone un endpoint de
      recuperación (<span class="mono">POST /api/password-reset/</span>). Este formulario ya está
      cableado: cuando el backend lo implemente, se activará sin cambios visuales.
      Mientras tanto, si tenés acceso, cambiá tu clave desde el panel autenticado.
    </div>

    <form @submit.prevent="onSubmit" novalidate>
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

    <div class="auth-links">
      <RouterLink to="/login">Volver al login</RouterLink>
      <RouterLink to="/register">Crear cuenta</RouterLink>
    </div>
  </AuthLayout>
</template>
