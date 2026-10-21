<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store.js'
import { useStoreStore } from '../stores/store.store.js'
import { useSlugCheck } from '../composables/useSlugCheck.js'
import { normalizeSlug, validateSlugFormat } from '../api/stores.api.js'
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

const host = window.location.host
const normalized = computed(() => normalizeSlug(slug.value))
const formatError = computed(() => (touched.value ? validateSlugFormat(normalized.value) : ''))
const fieldError = computed(() => formatError.value || stores.fieldErrors.slug || '')
const canSubmit = computed(() => Boolean(normalized.value) && isAvailable.value && !busy.value)

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

function logout() {
  stores.reset()
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <AuthLayout
    title="Elegí el link de tu tienda"
    subtitle="Es la dirección pública que vas a compartir con tus clientes. Podés cambiarla cuando quieras."
  >
    <AlertMessage v-if="stores.lastError" kind="error" :message="stores.lastError" />

    <form @submit.prevent="onSubmit" novalidate>
      <div class="field">
        <label for="slug">Tu link público <span aria-hidden="true">*</span></label>
        <div class="slug-box" :class="{ invalid: !!fieldError }">
          <span class="slug-prefix">{{ host }}/</span>
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

    <AlertMessage kind="info" message="Tu link queda activo de inmediato. Todavía no muestra productos: el catálogo se habilita con tu plan." />

    <div class="auth-links">
      <a href="#" @click.prevent="logout">Cerrar sesión</a>
    </div>
  </AuthLayout>
</template>
