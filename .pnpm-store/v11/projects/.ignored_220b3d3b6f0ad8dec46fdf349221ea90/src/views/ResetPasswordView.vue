<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { authApi } from '../api/auth.api.js'
import { validatePassword } from '../validators/auth.validators.js'
import { extractApiError } from '../api/http.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import PasswordStrength from '../components/PasswordStrength.vue'

const route = useRoute()
// El link del correo llega como /reset-password?uid=...&token=...
const form = reactive({ uid: '', token: '', new_password: '', confirm: '' })
const touched = reactive({})
const loading = ref(false)
const error = ref('')
const fieldErrors = ref({})
const success = ref('')

const linkInvalid = ref(false)

onMounted(() => {
  form.uid = String(route.query.uid || '')
  form.token = String(route.query.token || '')
  linkInvalid.value = !form.uid || !form.token
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
  fieldErrors.value = {}
  success.value = ''
  if (passError.value || confirmError.value) return
  loading.value = true
  try {
    const data = await authApi.confirmPasswordReset({
      uid: form.uid,
      token: form.token,
      new_password: form.new_password,
      confirm_password: form.confirm
    })
    success.value = data?.Exito || 'Tu contraseña se actualizó. Ya podés iniciar sesión.'
  } catch (e) {
    const { nonField, status: _s, ...fields } = extractApiError(e)
    fieldErrors.value = fields
    error.value = nonField || ''
    // Token inválido/vencido viaja en el campo token del serializer.
    if (fields.token) error.value = fields.token
    if (!error.value) error.value = 'No se pudo restablecer la contraseña. Pedí un enlace nuevo.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthLayout title="Nueva contraseña" subtitle="Elegí una clave segura para tu cuenta DAVENT.">
    <AlertMessage v-if="error" kind="error" :message="error" />
    <AlertMessage v-if="success" kind="success" :message="success" />

    <AlertMessage
      v-if="linkInvalid && !success"
      kind="error"
      message="El enlace está incompleto o es inválido. Pedí uno nuevo desde la recuperación de acceso."
    />

    <form v-if="!linkInvalid && !success" @submit.prevent="onSubmit" novalidate>
      <AppInput
        v-model="form.new_password"
        label="Nueva contraseña"
        name="new_password"
        type="password"
        placeholder="Ej. Asdf@123"
        autocomplete="new-password"
        required
        :error="passError || fieldErrors.new_password || ''"
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
        :error="confirmError || fieldErrors.confirm_password || ''"
        @blur="touched.confirm = true"
      />
      <AppButton :loading="loading">Guardar nueva contraseña</AppButton>
    </form>

    <AlertMessage
      v-if="!linkInvalid && !success"
      kind="info"
      message="Al cambiar la contraseña se cierran todas tus sesiones abiertas en otros dispositivos."
    />

    <div class="auth-links">
      <RouterLink to="/login">Volver al login</RouterLink>
      <RouterLink to="/forgot-password">Pedir otro enlace</RouterLink>
    </div>
  </AuthLayout>
</template>
