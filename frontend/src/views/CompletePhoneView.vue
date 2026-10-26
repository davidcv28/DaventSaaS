<script setup>
// Último paso del alta social: el celular no viaja en los datos de Google/
// Facebook, pero es el ancla anti-abuso (único por cuenta) que el registro
// por formulario exige y que el claim de la web necesita. El router fuerza
// esta pantalla a todo usuario sin profile.phone; al guardar, el guard lo
// lleva a /bienvenida (elegir el link de su tienda).
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { validatePhone } from '../validators/auth.validators.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ phone: '' })
const touched = ref(false)
const busy = ref(false)
const localError = ref('')

onMounted(async () => {
  if (!auth.user) await auth.fetchMe().catch(() => {})
  // Con celular ya cargado no hay nada que completar acá.
  if (auth.user?.profile?.phone) router.replace('/dashboard')
})

async function submit() {
  touched.value = true
  localError.value = ''
  if (validatePhone(form.phone)) return
  busy.value = true
  try {
    const res = await auth.updateAccount({
      email: auth.user?.email,
      profile: { phone: form.phone.trim() }
    })
    if (!res.ok) {
      // La unicidad del número la valida el backend (ancla anti-abuso).
      localError.value = auth.fieldErrors?.phone || auth.lastError || 'No pudimos guardar tu celular.'
      return
    }
    router.push('/dashboard')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthLayout title="Un último paso" subtitle="Tu cuenta está lista. Solo falta tu número de celular para cuidar las cuentas de prueba: un número, una cuenta.">
    <AlertMessage v-if="localError" kind="error" :message="localError" />
    <AlertMessage kind="info" message="Entraste con Google o Facebook: esos servicios no comparten tu celular, por eso te lo pedimos acá una sola vez." />

    <form @submit.prevent="submit" novalidate>
      <AppInput
        v-model="form.phone"
        label="Número de celular"
        name="phone"
        placeholder="+5493871551234"
        hint="Formato internacional. Ej. +5493871551234"
        autocomplete="tel"
        required
        :error="(touched && validatePhone(form.phone)) || auth.fieldErrors?.phone || ''"
        @blur="touched = true"
      />
      <div class="btn-row">
        <AppButton :loading="busy || auth.status === 'loading'">Continuar</AppButton>
      </div>
    </form>
  </AuthLayout>
</template>
