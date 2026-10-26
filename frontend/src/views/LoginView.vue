<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppInput from '../components/AppInput.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import SocialAuthButtons from '../components/SocialAuthButtons.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const form = reactive({ username: '', password: '', remember: true })
const touched = reactive({ username: false, password: false })
const cooldown = ref(0)
const socialError = ref('')
let timer = null

onMounted(() => {
  if (route.query.expired) {
    auth.lastError = 'Tu sesión expiró. Iniciá sesión nuevamente.'
  }
})

function startCooldown() {
  cooldown.value = 60
  clearInterval(timer)
  timer = setInterval(() => {
    cooldown.value -= 1
    if (cooldown.value <= 0) clearInterval(timer)
  }, 1000)
}

async function onSubmit() {
  touched.username = true
  touched.password = true
  if (!form.username.trim() || !form.password) return
  const ok = await auth.login(form)
  if (ok) {
    // El staff aterriza en su panel de administración; los clientes en el suyo.
    const next = route.query.next || (auth.user?.is_staff ? '/admin' : '/dashboard')
    router.push(String(next))
  } else if (auth.lastError.includes('Demasiados intentos')) {
    startCooldown()
  }
}

// Login social OK: el guard del router ya deriva a /completar-celular si el
// alta vino sin celular (requires_phone), y a /bienvenida si falta la tienda.
function onSocialDone() {
  socialError.value = ''
  const next = route.query.next || (auth.user?.is_staff ? '/admin' : '/dashboard')
  router.push(String(next))
}
</script>

<template>
  <AuthLayout title="Bienvenido de nuevo" subtitle="Ingresá con tu usuario DAVENT para gestionar tus tiendas.">
    <AlertMessage v-if="auth.lastError" kind="error" :message="auth.lastError" />
    <AlertMessage v-if="socialError" kind="error" :message="socialError" />
    <AlertMessage v-if="route.query.registered" kind="success" message="Cuenta creada. Te enviamos un correo para verificar tu email: revisá tu casilla (y el spam). Después podés iniciar sesión." />

    <form @submit.prevent="onSubmit" novalidate>
      <AppInput
        v-model="form.username"
        label="Nombre de usuario"
        name="username"
        placeholder="Ej. alfredo27"
        autocomplete="username"
        required
        :error="touched.username && !form.username.trim() ? 'Este campo es obligatorio' : (auth.fieldErrors.username || '')"
        @blur="touched.username = true"
      />
      <AppInput
        v-model="form.password"
        label="Contraseña"
        name="password"
        type="password"
        placeholder="Tu contraseña"
        autocomplete="current-password"
        required
        :error="touched.password && !form.password ? 'Este campo es obligatorio' : ''"
        @blur="touched.password = true"
      />

      <div class="field">
        <label class="check">
          <input v-model="form.remember" type="checkbox" />
          <span>Mantener sesión iniciada en este dispositivo (hasta 30 días)</span>
        </label>
      </div>

      <AppButton :loading="auth.status === 'loading'" :disabled="cooldown > 0">
        {{ cooldown > 0 ? `Reintentar en ${cooldown}s` : 'Iniciar sesión' }}
      </AppButton>
    </form>

    <SocialAuthButtons mode="login" @done="onSocialDone" @error="(m) => { socialError = m }" />

    <div class="auth-links">
      <RouterLink to="/forgot-password">¿Olvidaste tu contraseña?</RouterLink>
      <RouterLink to="/register">Crear cuenta</RouterLink>
    </div>

    <AlertMessage kind="info" message="La API limita el login a 5 intentos por minuto. El token se renueva automáticamente." />
  </AuthLayout>
</template>
