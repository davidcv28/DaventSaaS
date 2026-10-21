<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { authApi } from '../api/auth.api.js'
import { validatePassword } from '../validators/auth.validators.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PasswordStrength from '../components/PasswordStrength.vue'

const route = useRoute()
const form = reactive({ token: '', new_password: '', confirm: '' })
const touched = reactive({})
const loading = ref(false)
const error = ref('')
const info = ref('')

onMounted(() => {
  form.token = route.query.token || route.query.uid || ''
})

const passError = computed(() => {
  if (!touched.new_password) return ''
  return validatePassword(form.new_password) || ''
})
const confirmError = computed(() => {
  if (!touched.confirm) return ''
  if (!form.confirm) return 'Este campo es obligatorio'
  return form.new_password === form.confirm ? '' : 'Las contraseñas no coinciden'
})

async function onSubmit() {
  touched.new_password = true
  touched.confirm = true
  error.value = ''
  info.value = ''
  if (passError.value || confirmError.value) return
  loading.value = true
  try {
    await authApi.confirmPasswordReset({ token: form.token, new_password: form.new_password })
  } catch (e) {
    if (e.code === 'PENDING_BACKEND') info.value = e.message
    else error.value = 'No se pudo restablecer la contraseña.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="Nueva contraseña" subtitle="Elegí una clave segura para tu cuenta DAVENT.">
    <AlertMessage v-if="error" kind="error" :message="error" />
    <AlertMessage v-if="info" kind="warn" :message="info" />

    <div class="alert info">
      <strong>Estado de la API:</strong> falta <span class="mono">POST /api/password-reset/confirm/</span>
      en Django. El formulario valida en cliente y quedará activo cuando el backend lo implemente.
    </div>

    <form @submit.prevent="onSubmit" novalidate>
      <AppInput
        v-model="form.token"
        label="Token de recuperación"
        name="token"
        placeholder="Pegá el token del email"
        hint="Normalmente llega como ?token=... en el enlace."
        :error="touched.token && !form.token ? 'Este campo es obligatorio' : ''"
        @blur="touched.token = true"
      />
      <AppInput
        v-model="form.new_password"
        label="Nueva contraseña"
        name="new_password"
        type="password"
        placeholder="Ej. Asdf@123"
        autocomplete="new-password"
        required
        :error="passError"
        @blur="touched.new_password = true"
      />
      <PasswordStrength :value="form.new_password" />
      <AppInput
        v-model="form.confirm"
        label="Confirmar contraseña"
        name="confirm"
        type="password"
        placeholder="Repetir contraseña"
        autocomplete="new-password"
        required
        :error="confirmError"
        @blur="touched.confirm = true"
      />
      <AppButton :loading="loading">Guardar nueva contraseña</AppButton>
    </form>

    <div class="auth-links">
      <RouterLink to="/login">Volver al login</RouterLink>
      <RouterLink to="/forgot-password">Pedir otro enlace</RouterLink>
    </div>
  </AuthLayout>
</template>
