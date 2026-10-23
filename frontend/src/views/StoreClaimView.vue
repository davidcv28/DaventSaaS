<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useStoreStore } from '../stores/store.store.js'
import { useSlugCheck } from '../composables/useSlugCheck.js'
import { normalizeSlug, validateSlugFormat } from '../api/stores.api.js'
import { authApi } from '../api/auth.api.js'
import { env, storeSubdomains } from '../config/env.js'
import AuthLayout from '../components/AuthLayout.vue'
import AppButton from '../components/AppButton.vue'
import AlertMessage from '../components/AlertMessage.vue'
import AppIcon from '../components/AppIcon.vue'

// Onboarding: el usuario elige su link público la primera vez que ingresa.
// El guard del router manda acá a todo perfil sin tienda.
const router = useRouter()
const auth = useAuthStore()
const stores = useStoreStore()

const slug = ref('')
const touched = ref(false)
const busy = ref(false)
const { state: checkState, isAvailable, message: checkMessage, kind: checkKind, requestCheck } = useSlugCheck()

const platformHost = env.platformHost
const scheme = `${window.location.protocol}//`
// Sin wildcard (Render test) el link es path: https://host/[slug]; con dominio
// propio el slug va de subdominio: https://[slug].host
const slugPrefix = storeSubdomains ? scheme : `${scheme}${platformHost}/`
const normalized = computed(() => normalizeSlug(slug.value))
const formatError = computed(() => (touched.value ? validateSlugFormat(normalized.value) : ''))
const fieldError = computed(() => formatError.value || stores.fieldErrors.slug || '')

// Anti-abuso trial: el backend exige email verificado para el claim (403).
// Se anticipa la misma regla acá con banner + reenvío.
const needsEmailVerification = computed(() => {
  const p = auth.user?.profile
  return Boolean(p) && p.email_verified === false
})
const verifyBusy = ref(false)
const verifyMsg = ref('')
const verifyErr = ref('')

const canSubmit = computed(() => Boolean(normalized.value) && isAvailable.value && !busy.value && !needsEmailVerification.value)

async function resendVerification() {
  verifyBusy.value = true
  verifyMsg.value = ''
  verifyErr.value = ''
  try {
    const data = await authApi.resendVerificationEmail()
    verifyMsg.value = data?.Exito || 'Te reenviamos el correo de verificación.'
  } catch (e) {
    verifyErr.value = e.response?.status === 429
      ? 'Ya pediste varios reenvíos. Esperá un rato y revisá también el spam.'
      : 'No se pudo reenviar el correo. Reintentá en unos minutos.'
  } finally {
    verifyBusy.value = false
  }
}

onMounted(() => {
  if (stores.status === 'idle') stores.loadMine()
})

function onInput(event) {
  slug.value = event.target.value
  requestCheck(slug.value)
}

async function onSubmit() {
  touched.value = true
  if (!canSubmit.value) return
  busy.value = true
  const ok = await stores.claim(normalized.value)
  busy.value = false
  if (ok) router.push({ name: 'dashboard' })
}

async function logout() {
  stores.reset()
  // Esperar al logout: si el push corre con el request en vuelo, la cookie
  // de refresh sigue viva y ensureSession puede revivir la sesión.
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <AuthLayout
    title="Elegí el link de tu tienda"
    subtitle="Es la dirección pública que vas a compartir con tus clientes. Podés cambiarla cuando quieras."
  >
    <AlertMessage v-if="stores.lastError" kind="error" :message="stores.lastError" />

    <template v-if="needsEmailVerification">
      <AlertMessage kind="warn" :message="`Antes de crear tu link tenés que verificar tu correo (${auth.user?.email}). Revisá tu casilla y el spam.`" />
      <AlertMessage v-if="verifyMsg" kind="success" :message="verifyMsg" />
      <AlertMessage v-if="verifyErr" kind="error" :message="verifyErr" />
      <AppButton variant="ghost" :loading="verifyBusy" @click="resendVerification">Reenviar correo de verificación</AppButton>
    </template>

    <form v-else @submit.prevent="onSubmit" novalidate>
      <div class="field">
        <label for="slug">Tu link público <span aria-hidden="true">*</span></label>
        <div class="slug-box" :class="{ invalid: !!fieldError }">
          <span class="slug-prefix">{{ slugPrefix }}</span>
          <input
            id="slug"
            name="slug"
            type="text"
            class="input slug-input"
            :class="{ invalid: !!fieldError }"
            :value="slug"
            placeholder="mi-negocio"
            maxlength="60"
            autocomplete="off"
            :aria-invalid="!!fieldError"
            @input="onInput"
            @blur="touched = true"
          />
          <span v-if="storeSubdomains" class="slug-suffix">.{{ platformHost }}</span>
        </div>
        <p class="hint">Entre 3 y 60 caracteres: letras minúsculas, números y guiones.</p>
        <p v-if="fieldError" class="field-error" role="alert">{{ fieldError }}</p>
        <p v-else-if="checkMessage" class="slug-check" :class="checkKind" role="status">
          <AppIcon v-if="checkState === 'available'" name="circle-check" :size="14" />
          <span v-else-if="checkState === 'checking'" class="spinner spinner-brand" aria-hidden="true"></span>
          {{ checkMessage }}
        </p>
      </div>

      <AppButton :loading="busy" :disabled="!canSubmit">Crear mi link</AppButton>
    </form>

    <AlertMessage v-if="!needsEmailVerification" kind="info" message="Tu link queda activo de inmediato. Todavía no muestra productos: el catálogo se habilita con tu plan." />

    <div class="auth-links">
      <a href="#" @click.prevent="logout">Cerrar sesión</a>
    </div>
  </AuthLayout>
</template>
